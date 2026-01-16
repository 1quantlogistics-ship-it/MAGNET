"""
MAGNET Hull Synthesis Engine

Kernel-level hull synthesis as a first-class primitive.
Uses validators as scoring functions in a bounded propose→validate→mutate loop.
Guaranteed termination with fallback path.

v1.0: Initial implementation
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
import logging
import math

from magnet.core.constants import FN_DISPLACEMENT_MAX, FN_SEMI_DISPLACEMENT_MAX

from .priors.hull_families import (
    HullFamily,
    get_family_prior,
    calculate_froude,
    get_regime_adjusted_prior,
)
from .priors.geometry_defaults import (
    get_defaults_from_froude,
    get_defaults_from_dimensions,
    estimate_lightship_kg as geometry_estimate_lightship,
    get_displacement_bounds as geometry_displacement_bounds,
)
from .synthesis_lock import SynthesisLock, SynthesisLockError
from .synthesis_fallback import create_fallback_proposal, FallbackMode

import warnings

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager
    from magnet.validators.executor import PipelineExecutor

logger = logging.getLogger(__name__)


# =============================================================================
# CONTRACTS
# =============================================================================

@dataclass(frozen=True)
class SynthesisRequest:
    """
    Immutable input contract for hull synthesis.

    All inputs validated at construction time.
    Missing optionals use family-appropriate defaults.
    
    DEPRECATED (TASK-003): Use GeometrySynthesisRequest instead.
    HullFamily-based synthesis will be removed in Phase 2.
    """
    hull_family: HullFamily          # Required - determines prior (DEPRECATED)
    max_speed_kts: float             # Required - drives Froude estimation

    # Optional constraints (None = use family default)
    loa_m: Optional[float] = None
    # Phase 3: Treat LOA as hard constraint (locks LWL to ~0.95×LOA during synthesis)
    loa_is_hard_constraint: bool = True
    payload_kg: Optional[float] = None
    crew_count: Optional[int] = None
    range_nm: Optional[float] = None
    gm_min_m: Optional[float] = None

    # Convergence parameters (can override defaults)
    max_iterations: int = 15
    convergence_criteria: Optional["ConvergenceCriteria"] = None

    def __post_init__(self):
        # Emit deprecation warning
        warnings.warn(
            "SynthesisRequest with HullFamily is deprecated. "
            "Use GeometrySynthesisRequest or design language path instead. "
            "See GOLDEN_PATH_IMPLEMENTATION_GUIDE.md TASK-003.",
            DeprecationWarning,
            stacklevel=2,
        )
        if self.max_speed_kts <= 0:
            raise ValueError("max_speed_kts must be positive")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be >= 1")
        if self.loa_m is not None and self.loa_m <= 0:
            raise ValueError("loa_m must be positive when provided")


@dataclass(frozen=True)
class GeometrySynthesisRequest:
    """
    Geometry-based synthesis request (TASK-003 compliant).
    
    Uses physics-derived defaults instead of HullFamily enumeration.
    This is the PREFERRED synthesis request type.
    """
    max_speed_kts: float             # Required - drives Froude estimation
    
    # Optional constraints (None = use physics-derived defaults)
    loa_m: Optional[float] = None
    beam_m: Optional[float] = None   # NEW: explicit beam constraint
    draft_m: Optional[float] = None  # NEW: explicit draft constraint
    
    loa_is_hard_constraint: bool = True
    payload_kg: Optional[float] = None
    crew_count: Optional[int] = None
    range_nm: Optional[float] = None
    gm_min_m: Optional[float] = None

    # Convergence parameters
    max_iterations: int = 15
    convergence_criteria: Optional["ConvergenceCriteria"] = None

    def __post_init__(self):
        if self.max_speed_kts <= 0:
            raise ValueError("max_speed_kts must be positive")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be >= 1")
        if self.loa_m is not None and self.loa_m <= 0:
            raise ValueError("loa_m must be positive when provided")
    
    def get_physics_defaults(self) -> Dict[str, Any]:
        """Get physics-derived defaults for this request."""
        if self.loa_m:
            return get_defaults_from_dimensions(self.loa_m, self.max_speed_kts)
        else:
            # Estimate LOA from speed
            estimated_loa = max(10.0, (self.max_speed_kts / 2.0) ** 2)
            estimated_loa = min(100.0, estimated_loa)
            return get_defaults_from_dimensions(estimated_loa, self.max_speed_kts)


@dataclass(frozen=True)
class SynthesisProposal:
    """
    Complete hull candidate with confidence and lineage.

    NEVER partial state - all hull parameters or none.
    """
    # Principal dimensions (ALL required)
    lwl_m: float
    beam_m: float
    draft_m: float
    depth_m: float  # Moulded depth to main deck

    # Form coefficients (ALL required)
    cb: float
    cp: float
    cm: float
    cwp: float

    # Derived (computed at construction)
    displacement_m3: float

    # Confidence and lineage
    confidence: float               # 0.0-1.0
    iteration: int                  # Which iteration produced this
    source: str                     # "prior" | "mutated" | "fallback"

    # -------------------------------------------------------------------------
    # Hull form completion (v1.5): populate all 21 refinable hull parameters
    # NOTE: kept Optional with defaults to preserve backwards compatibility of
    # tests/fixtures; synthesizer is responsible for filling these in.
    # -------------------------------------------------------------------------
    loa_m: Optional[float] = None
    draft_fwd_m: Optional[float] = None
    draft_aft_m: Optional[float] = None
    freeboard_m: Optional[float] = None
    hull_type: Optional[str] = None
    hull_spacing_m: Optional[float] = None
    transom_beam_ratio: Optional[float] = None
    bow_flare_deg: Optional[float] = None
    stem_rake_deg: Optional[float] = None
    bow_entrance_deg: Optional[float] = None
    lcb_fraction: Optional[float] = None
    deadrise_deg: Optional[float] = None
    deadrise_transom_deg: Optional[float] = None
    
    # TASK-003: Geometry-derived synthesis fields
    froude_number: Optional[float] = None  # Operating Froude number

    @property
    def is_complete(self) -> bool:
        """All parameters are valid positive numbers."""
        return all(v > 0 for v in [
            self.lwl_m, self.beam_m, self.draft_m, self.depth_m,
            self.cb, self.cp, self.cm, self.cwp
        ])

    def to_state_dict(self) -> Dict[str, Any]:
        """
        Convert proposal to state paths.

        v1.5: Includes all 21 hull refinable parameters (plus displacement_m3).
        """
        if not self.is_complete:
            raise ValueError("Cannot commit incomplete proposal")

        loa_m = float(self.loa_m) if (self.loa_m is not None and self.loa_m > 0) else float(self.lwl_m / 0.95)
        draft_fwd_m = float(self.draft_fwd_m) if (self.draft_fwd_m is not None and self.draft_fwd_m > 0) else float(self.draft_m)
        draft_aft_m = float(self.draft_aft_m) if (self.draft_aft_m is not None and self.draft_aft_m > 0) else float(self.draft_m)

        draft_ref = max(float(self.draft_m), draft_fwd_m, draft_aft_m)
        freeboard_m = (
            float(self.freeboard_m)
            if (self.freeboard_m is not None and self.freeboard_m >= 0)
            else max(0.0, float(self.depth_m) - draft_ref)
        )

        hull_type = (self.hull_type or "monohull").strip().lower()

        out: Dict[str, Any] = {
            # Principal
            "hull.loa": loa_m,
            "hull.lwl": float(self.lwl_m),
            "hull.beam": float(self.beam_m),
            "hull.draft": float(self.draft_m),
            "hull.draft_fwd_m": draft_fwd_m,
            "hull.draft_aft_m": draft_aft_m,
            "hull.depth": float(self.depth_m),
            "hull.freeboard_m": freeboard_m,
            "hull.hull_type": hull_type,

            # Form coefficients
            "hull.cb": float(self.cb),
            "hull.cp": float(self.cp),
            "hull.cm": float(self.cm),
            "hull.cwp": float(self.cwp),
            "hull.lcb_fraction": float(self.lcb_fraction) if self.lcb_fraction is not None else 0.52,

            # Hull form inputs
            "hull.transom_beam_ratio": float(self.transom_beam_ratio) if self.transom_beam_ratio is not None else 0.85,
            "hull.bow_entrance_deg": float(self.bow_entrance_deg) if self.bow_entrance_deg is not None else 25.0,
            "hull.bow_flare_deg": float(self.bow_flare_deg) if self.bow_flare_deg is not None else 0.0,
            "hull.stem_rake_deg": float(self.stem_rake_deg) if self.stem_rake_deg is not None else 10.0,
            "hull.deadrise_deg": float(self.deadrise_deg) if self.deadrise_deg is not None else 0.0,
            "hull.deadrise_transom_deg": float(self.deadrise_transom_deg) if self.deadrise_transom_deg is not None else 0.0,

            # Derived
            "hull.displacement_m3": float(self.displacement_m3),
        }

        # Multi-hull: only set when provided
        if self.hull_spacing_m is not None:
            out["hull.hull_spacing_m"] = float(self.hull_spacing_m)

        return out


@dataclass(frozen=True)
class ConvergenceCriteria:
    """
    Hard convergence criteria - synthesis MUST stop when met.

    Prevents endless refinement loops and brittle early exits.
    """
    # Validator-based criteria
    min_validators_passed: int = 2      # At least N validators must pass
    max_error_severity: str = "warning" # No findings above this level

    # Score-based criteria
    min_score: float = 85.0             # Minimum fitness score
    score_plateau_iterations: int = 3   # Stop if score unchanged for N iterations
    score_plateau_threshold: float = 0.5  # "Unchanged" = delta < threshold

    # Margin-based criteria (naval architecture)
    gm_margin_m: float = 0.1            # GM must exceed requirement by this margin
    displacement_tolerance: float = 0.05  # 5% displacement convergence

    def is_converged(
        self,
        score: float,
        validators_passed: int,
        max_finding_severity: str,
        gm_actual: float,
        gm_required: float,
        score_history: List[float],
    ) -> Tuple[bool, str]:
        """
        Check if convergence criteria are met.

        Returns:
            Tuple of (converged, reason)
        """
        # Check validator count
        if validators_passed < self.min_validators_passed:
            return False, f"Only {validators_passed}/{self.min_validators_passed} validators passed"

        # Check severity ceiling
        severity_order = {"info": 0, "warning": 1, "error": 2}
        if severity_order.get(max_finding_severity, 2) > severity_order[self.max_error_severity]:
            return False, f"Finding severity {max_finding_severity} exceeds {self.max_error_severity}"

        # Check minimum score
        if score < self.min_score:
            return False, f"Score {score:.1f} below minimum {self.min_score}"

        # Check GM margin
        if gm_actual < gm_required + self.gm_margin_m:
            return False, f"GM {gm_actual:.2f}m below required {gm_required + self.gm_margin_m:.2f}m"

        # Check score plateau (early termination if not improving)
        if len(score_history) >= self.score_plateau_iterations:
            recent = score_history[-self.score_plateau_iterations:]
            if max(recent) - min(recent) < self.score_plateau_threshold:
                return True, "Score plateaued - converged"

        return True, "All criteria met"


# Default convergence criteria
DEFAULT_CONVERGENCE = ConvergenceCriteria()


class TerminationReason(Enum):
    """Why synthesis stopped."""
    CONVERGED = "converged"           # Met all criteria
    MAX_ITERATIONS = "max_iterations" # Hit iteration cap
    FALLBACK = "fallback"             # Used estimator-only
    ERROR = "error"                   # Synthesis failed


@dataclass
class SynthesisResult:
    """
    Complete synthesis result with audit trail.

    ALWAYS produces a usable hull (via fallback if necessary).
    """
    # The hull
    proposal: SynthesisProposal

    # Termination info
    termination: TerminationReason
    termination_message: str

    # Audit trail
    iterations_used: int
    score_history: List[float]
    validator_results: List[str]       # Validator names that passed

    # Warnings and notes
    warnings: List[str] = field(default_factory=list)

    @property
    def is_converged(self) -> bool:
        return self.termination == TerminationReason.CONVERGED

    @property
    def is_fallback(self) -> bool:
        return self.termination == TerminationReason.FALLBACK

    @property
    def is_usable(self) -> bool:
        """Result can be committed to state (even if fallback)."""
        return self.proposal.is_complete


# =============================================================================
# HULL SYNTHESIZER
# =============================================================================

def _compute_depth(draft: float, prior: Dict[str, Any]) -> float:
    """
    Compute moulded depth from draft using family-specific ratio.

    Single source of truth for depth calculation. Never compute depth inline.

    Args:
        draft: Draft in meters
        prior: Family prior dict containing depth_draft_ratio

    Returns:
        Depth in meters
    """
    depth_draft_ratio = prior.get("depth_draft_ratio", 1.6)  # Default fallback
    return draft * depth_draft_ratio


def _apply_coefficient_coupling(
    cb_mutated: float,
    prior: Dict[str, Any],
) -> Tuple[float, float, float]:
    """
    Apply coefficient coupling constraints to maintain geometric consistency.

    Strategy: Cp is fixed (from family prior), Cm is derived from Cb/Cp.
    This ensures the fundamental relationship Cb = Cp × Cm is maintained.

    v1.4: Implements coefficient coupling per architectural audit.

    Args:
        cb_mutated: The mutated block coefficient value
        prior: Family prior dict containing cp and coefficient_constraints

    Returns:
        Tuple of (cb, cp, cm) with coupling constraints applied
    """
    # Cp is fixed from family prior
    cp = prior["cp"]

    # Get Cb bounds from family prior
    bounds = prior.get("bounds", {})
    cb_bounds = bounds.get("cb", (0.30, 0.70))
    cb_min, cb_max = cb_bounds

    # Get Cm constraints from family prior
    constraints = prior.get("coefficient_constraints", {})
    cm_min = constraints.get("cm_min", 0.70)
    cm_max = constraints.get("cm_max", 0.98)

    # First, clamp Cb to family-specific bounds
    cb = max(cb_min, min(cb_max, cb_mutated))

    # Derive Cm from the fundamental relationship: Cb = Cp × Cm → Cm = Cb / Cp
    cm_implied = cb / cp

    # Clamp Cm to physical bounds and back-adjust Cb if needed
    if cm_implied < cm_min:
        # Cm too low - increase Cb to meet minimum Cm
        cb = cp * cm_min
        cm = cm_min
        logger.debug(f"Coefficient coupling: Cm {cm_implied:.3f} below min {cm_min}, Cb adjusted to {cb:.3f}")
    elif cm_implied > cm_max:
        # Cm too high - decrease Cb to meet maximum Cm
        cb = cp * cm_max
        cm = cm_max
        logger.debug(f"Coefficient coupling: Cm {cm_implied:.3f} above max {cm_max}, Cb adjusted to {cb:.3f}")
    else:
        # Cm is valid, use implied value
        cm = cm_implied

    return cb, cp, cm


class HullSynthesizer:
    """
    Kernel-level hull synthesis engine.

    Uses validators as scoring functions in a bounded propose→validate→mutate loop.
    Guaranteed termination with fallback path.
    """

    # Validators used for scoring
    SCORING_VALIDATORS = [
        "physics/hydrostatics",
        "physics/resistance",
    ]

    MUTATION_DELTA = 0.05  # 5% max change per iteration

    # Mission→displacement heuristics (v1.5)
    WATER_DENSITY_KG_M3 = 1025.0
    CREW_WEIGHT_KG = 100.0
    FUEL_KG_PER_NM_AT_25KTS = 2.5
    LIGHTSHIP_RATIO = 0.55  # Deprecated (v1.6): replaced by LOA-based lightship scaling

    # LOA-based lightship scaling (v1.6)
    # Empirical cube-ish law fit: lightship_tonnes ≈ k × LOA^2.7
    LIGHTSHIP_EXPONENT = 2.7
    LIGHTSHIP_K_TONNES: Dict[HullFamily, float] = {
        HullFamily.PATROL: 0.015,      # Lighter, performance-focused
        HullFamily.WORKBOAT: 0.022,    # Heavier, robust construction
        HullFamily.FERRY: 0.025,       # Heavier, accommodation weight
        HullFamily.PLANING: 0.012,     # Lightest, minimal structure
        HullFamily.CATAMARAN: 0.020,   # Twin hulls + bridging structure
    }

    # LOA scaling reference for displacement bounds (v1.6)
    # Used only for displacement_m3 bounds; other bounds remain fixed family envelopes.
    DISP_BOUNDS_REF_LOA_M: Dict[HullFamily, float] = {
        HullFamily.PATROL: 30.0,
        HullFamily.WORKBOAT: 25.0,
        HullFamily.FERRY: 60.0,
        HullFamily.PLANING: 15.0,
        HullFamily.CATAMARAN: 40.0,
    }

    def __init__(
        self,
        executor: "PipelineExecutor",
        state_manager: "StateManager",
    ):
        """
        Initialize hull synthesizer.

        Args:
            executor: PipelineExecutor for running validators
            state_manager: StateManager for state access
        """
        self.executor = executor
        self.state = state_manager
        self.lock = SynthesisLock(state_manager)

    # -------------------------------------------------------------------------
    # Helpers (v1.5)
    # -------------------------------------------------------------------------

    @staticmethod
    def _mid(range_or_value: Any) -> Optional[float]:
        """Return midpoint of a (min,max) range, or cast numeric value to float."""
        if range_or_value is None:
            return None
        if isinstance(range_or_value, tuple) and len(range_or_value) == 2:
            lo, hi = range_or_value
            return 0.5 * (float(lo) + float(hi))
        if isinstance(range_or_value, (int, float)):
            return float(range_or_value)
        return None

    @staticmethod
    def _infer_hull_type(family: HullFamily, froude: float) -> str:
        """
        Map hull family + Fn to a schema hull.hull_type value.

        This is used for geometry selection (webgl/interfaces.py type_map).
        """
        if family == HullFamily.CATAMARAN:
            return "catamaran"
        if family == HullFamily.PLANING:
            return "planing"

        fn = float(froude or 0.0)
        if fn < FN_DISPLACEMENT_MAX:
            return "displacement"
        if fn < FN_SEMI_DISPLACEMENT_MAX:
            return "semi_displacement"
        return "planing"

    def _estimate_lightship_kg(self, loa_m: float, hull_family: HullFamily) -> float:
        """
        Estimate lightship weight from LOA using an empirical scaling law.

        This fixes the v1.5 ratio-model flaw where lightship collapsed toward 0
        for small deadweight missions (few crew, short range).
        """
        try:
            loa = float(loa_m)
        except Exception:
            return 0.0

        if loa <= 0:
            return 0.0

        k = float(self.LIGHTSHIP_K_TONNES.get(hull_family, 0.015))
        exponent = float(self.LIGHTSHIP_EXPONENT)
        lightship_tonnes = k * (loa ** exponent)
        return max(0.0, lightship_tonnes * 1000.0)

    def _get_loa_scaled_displacement_bounds_m3(
        self,
        family: HullFamily,
        loa_m: Optional[float],
    ) -> Optional[Tuple[float, float]]:
        """
        Scale family displacement bounds by LOA^3 to avoid pathological edge cases.

        v1.6: Only applies to displacement_m3 bounds. All other bounds remain the
        fixed family envelopes in priors.
        """
        if loa_m is None:
            return None
        try:
            loa = float(loa_m)
        except Exception:
            return None

        if loa <= 0:
            return None

        prior = get_family_prior(family)
        bounds = prior.get("bounds", {}) or {}
        disp_bounds = bounds.get("displacement_m3")
        if not disp_bounds:
            return None

        disp_min, disp_max = disp_bounds
        ref_loa = float(self.DISP_BOUNDS_REF_LOA_M.get(family, 30.0))
        if ref_loa <= 0:
            return float(disp_min), float(disp_max)

        scale = (loa / ref_loa) ** 3
        scaled_min = max(5.0, float(disp_min) * scale)
        scaled_max = float(disp_max) * scale
        if scaled_max < scaled_min:
            scaled_max = scaled_min
        return float(scaled_min), float(scaled_max)

    def _estimate_required_displacement_m3(
        self,
        request: SynthesisRequest,
    ) -> Tuple[Optional[float], List[str]]:
        """
        Estimate required displacement volume (m³) from mission-like inputs.

        Uses a coarse deadweight → displacement heuristic. This is intentionally
        simple; resistance/weight phases can later refine fuel/weight models.
        """
        warnings: List[str] = []
        crew = int(request.crew_count or 0)
        payload_kg = float(request.payload_kg or 0.0)
        range_nm = float(request.range_nm or 0.0)
        speed_kts = float(request.max_speed_kts or 0.0)

        crew_weight = crew * self.CREW_WEIGHT_KG

        fuel_kg = 0.0
        if range_nm > 0 and speed_kts > 0:
            # Speed scaling is a rough proxy for power scaling.
            fuel_kg = range_nm * self.FUEL_KG_PER_NM_AT_25KTS * (speed_kts / 25.0) ** 1.5

        deadweight_kg = crew_weight + payload_kg + fuel_kg

        # LOA drives lightship. If LOA is not explicitly provided, infer it from
        # the same family Fn backsolve used by _create_initial_proposal().
        loa_m = float(request.loa_m) if request.loa_m else None
        if loa_m is None:
            prior = get_family_prior(request.hull_family)
            speed_ms = speed_kts * 0.5144
            target_fn = float(prior.get("froude_design", 0.45) or 0.45)
            if speed_ms > 0 and target_fn > 0:
                lwl_est = (speed_ms / target_fn) ** 2 / 9.81
                loa_m = float(lwl_est / 0.95)
            else:
                loa_m = 20.0  # Defensive fallback (should be rare; max_speed_kts is required)

        lightship_kg = self._estimate_lightship_kg(float(loa_m), request.hull_family)
        displacement_kg = lightship_kg + deadweight_kg
        displacement_m3 = displacement_kg / self.WATER_DENSITY_KG_M3

        warnings.append(
            f"disp_estimate: loa_m={loa_m:.1f} family={request.hull_family.value} "
            f"lightship_kg={lightship_kg:.0f} deadweight_kg={deadweight_kg:.0f} "
            f"(crew={crew_weight:.0f}, payload={payload_kg:.0f}, fuel={fuel_kg:.0f}) "
            f"-> disp_m3={displacement_m3:.1f}"
        )

        return float(displacement_m3), warnings

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """
        Main synthesis entry point.

        Acquires exclusive hull lock.
        Returns usable hull (via fallback if necessary).
        Guaranteed termination.

        Args:
            request: SynthesisRequest with hull family and constraints

        Returns:
            SynthesisResult with complete hull proposal
        """
        criteria = request.convergence_criteria or DEFAULT_CONVERGENCE

        with self.lock.exclusive_access("hull_synthesizer"):
            try:
                return self._synthesis_loop(request, criteria)
            except Exception as e:
                logger.error(f"Synthesis failed: {e}")
                return self._create_fallback_result(request, str(e))

    def synthesize_from_geometry(self, request: GeometrySynthesisRequest) -> SynthesisResult:
        """
        TASK-003: Geometry-based synthesis entry point.
        
        Uses physics-derived defaults instead of HullFamily enumeration.
        This is the PREFERRED synthesis method.
        
        Args:
            request: GeometrySynthesisRequest with physics constraints
            
        Returns:
            SynthesisResult with complete hull proposal
        """
        criteria = request.convergence_criteria or DEFAULT_CONVERGENCE
        
        with self.lock.exclusive_access("hull_synthesizer"):
            try:
                return self._geometry_synthesis_loop(request, criteria)
            except Exception as e:
                logger.error(f"Geometry synthesis failed: {e}")
                return self._create_geometry_fallback_result(request, str(e))

    def _score_proposal(self, proposal: SynthesisProposal) -> Tuple[float, List[str]]:
        """
        Score a synthesis proposal using geometry-based heuristics.
        
        TASK-003: This is a simplified scoring for geometry-based synthesis.
        Returns (score, warnings) where score is 0-100.
        """
        warnings: List[str] = []
        score = 100.0
        
        # Check basic validity
        if not proposal.is_complete:
            return 0.0, ["Proposal is incomplete"]
        
        # Check proportions
        lb_ratio = proposal.lwl_m / proposal.beam_m if proposal.beam_m > 0 else 0
        bd_ratio = proposal.beam_m / proposal.draft_m if proposal.draft_m > 0 else 0
        
        # L/B ratio check (typical range 3-8)
        if lb_ratio < 3.0:
            score -= 10.0
            warnings.append(f"L/B ratio {lb_ratio:.1f} is low (typical: 3-8)")
        elif lb_ratio > 8.0:
            score -= 5.0
            warnings.append(f"L/B ratio {lb_ratio:.1f} is high (typical: 3-8)")
        
        # B/D ratio check (typical range 2-5)
        if bd_ratio < 2.0:
            score -= 5.0
            warnings.append(f"B/D ratio {bd_ratio:.1f} is low (typical: 2-5)")
        elif bd_ratio > 5.0:
            score -= 5.0
            warnings.append(f"B/D ratio {bd_ratio:.1f} is high (typical: 2-5)")
        
        # Block coefficient check
        if proposal.cb < 0.3 or proposal.cb > 0.8:
            score -= 10.0
            warnings.append(f"Block coefficient {proposal.cb:.2f} outside typical range (0.3-0.8)")
        
        # Depth/draft check
        if proposal.depth_m < proposal.draft_m:
            score -= 20.0
            warnings.append("Depth is less than draft")
        
        return max(0.0, score), warnings

    def _geometry_synthesis_loop(
        self,
        request: GeometrySynthesisRequest,
        criteria: ConvergenceCriteria,
    ) -> SynthesisResult:
        """
        TASK-003: Geometry-based synthesis loop.
        
        Uses physics-derived defaults instead of HullFamily priors.
        """
        # Get physics-derived defaults
        defaults = request.get_physics_defaults()
        
        # Create initial proposal from physics defaults
        proposal, clamp_warnings = self._create_initial_proposal_from_geometry(request, defaults)
        best_proposal = proposal
        best_score = float('-inf')
        score_history: List[float] = []
        all_warnings: List[str] = list(clamp_warnings)
        
        # Stagnation tracking
        stagnation_count = 0
        last_best_score = float('-inf')
        
        for iteration in range(request.max_iterations):
            # Score proposal
            score, score_warnings = self._score_proposal(proposal)
            all_warnings.extend(score_warnings)
            score_history.append(score)
            
            if score > best_score:
                best_score = score
                best_proposal = proposal
                stagnation_count = 0
            else:
                stagnation_count += 1
            
            # Check convergence
            if score >= criteria.target_score:
                logger.info(f"Geometry synthesis converged at iteration {iteration + 1}")
                break
            
            # Check stagnation
            if stagnation_count >= criteria.stagnation_limit:
                logger.warning(f"Geometry synthesis stagnated after {iteration + 1} iterations")
                break
            
            # Mutate proposal
            proposal = self._mutate_proposal_geometry_based(proposal, defaults, iteration)
            last_best_score = best_score
        
        # Build result
        converged = best_score >= criteria.target_score
        termination = TerminationReason.CONVERGED if converged else TerminationReason.MAX_ITERATIONS
        return SynthesisResult(
            proposal=best_proposal,
            termination=termination,
            termination_message="Geometry-based synthesis complete",
            iterations_used=len(score_history),
            score_history=score_history,
            validator_results=[],  # Geometry synthesis doesn't run validators
            warnings=all_warnings,
        )

    def _create_initial_proposal_from_geometry(
        self,
        request: GeometrySynthesisRequest,
        defaults: Dict[str, Any],
    ) -> Tuple[SynthesisProposal, List[str]]:
        """
        TASK-003: Create initial proposal from geometry-derived defaults.
        """
        warnings: List[str] = []
        
        # Extract defaults
        lwl_m = defaults.get("lwl_m", 30.0)
        beam_m = request.beam_m or defaults.get("beam_m", 6.0)
        draft_m = request.draft_m or defaults.get("draft_m", 2.0)
        depth_m = defaults.get("depth_m", draft_m * 1.5)
        cb = defaults.get("cb", 0.5)
        deadrise_deg = defaults.get("deadrise_deg", 15.0)
        froude_number = defaults.get("froude_number", 0.5)
        
        # Use request LOA if provided
        if request.loa_m:
            lwl_m = request.loa_m * 0.95
        
        # Estimate displacement
        displacement_m3 = lwl_m * beam_m * draft_m * cb
        
        # Create proposal
        proposal = SynthesisProposal(
            lwl_m=lwl_m,
            beam_m=beam_m,
            draft_m=draft_m,
            depth_m=depth_m,
            cb=cb,
            cp=defaults.get("cp", cb + 0.15),
            cm=defaults.get("cm", 0.85),
            cwp=defaults.get("cwp", 0.75),
            deadrise_deg=deadrise_deg,
            displacement_m3=displacement_m3,
            confidence=0.7,  # Lower initial confidence for geometry-based
            iteration=0,
            source="geometry_defaults",
            froude_number=froude_number,
        )
        
        return proposal, warnings

    def _mutate_proposal_geometry_based(
        self,
        proposal: SynthesisProposal,
        defaults: Dict[str, Any],
        iteration: int,
    ) -> SynthesisProposal:
        """
        TASK-003: Mutate proposal using geometry-derived constraints.
        """
        import random
        
        # Small random perturbations toward physics-optimal values
        scale = 0.1 / (1 + iteration * 0.1)  # Decrease with iteration
        
        new_lwl = proposal.lwl_m * (1 + random.gauss(0, scale))
        new_beam = proposal.beam_m * (1 + random.gauss(0, scale))
        new_draft = proposal.draft_m * (1 + random.gauss(0, scale))
        new_cb = max(0.3, min(0.8, proposal.cb + random.gauss(0, scale * 0.5)))
        
        new_displacement = new_lwl * new_beam * new_draft * new_cb
        
        return SynthesisProposal(
            lwl_m=new_lwl,
            beam_m=new_beam,
            draft_m=new_draft,
            depth_m=new_draft * defaults.get("depth_draft_ratio", 1.5),
            cb=new_cb,
            cp=new_cb + 0.15,
            cm=defaults.get("cm", 0.85),
            cwp=defaults.get("cwp", 0.75),
            deadrise_deg=defaults.get("deadrise_deg", 15.0),
            displacement_m3=new_displacement,
            confidence=proposal.confidence,
            iteration=iteration + 1,
            source="geometry_mutation",
            froude_number=defaults.get("froude_number", 0.5),
        )

    def _create_geometry_fallback_result(
        self,
        request: GeometrySynthesisRequest,
        error_message: str,
    ) -> SynthesisResult:
        """
        TASK-003: Create fallback result for geometry-based synthesis.
        """
        defaults = request.get_physics_defaults()
        
        lwl_m = request.loa_m * 0.95 if request.loa_m else 30.0
        beam_m = request.beam_m or defaults.get("beam_m", 6.0)
        draft_m = request.draft_m or defaults.get("draft_m", 2.0)
        
        fallback_proposal = SynthesisProposal(
            lwl_m=lwl_m,
            beam_m=beam_m,
            draft_m=draft_m,
            depth_m=draft_m * 1.5,
            cb=defaults.get("cb", 0.5),
            cp=defaults.get("cp", 0.65),
            cm=defaults.get("cm", 0.85),
            cwp=defaults.get("cwp", 0.75),
            deadrise_deg=defaults.get("deadrise_deg", 15.0),
            displacement_m3=lwl_m * beam_m * draft_m * 0.5,
            confidence=0.3,  # Low confidence for fallback
            iteration=0,
            source="geometry_fallback",
            froude_number=defaults.get("froude_number", 0.5),
        )
        
        return SynthesisResult(
            proposal=fallback_proposal,
            termination=TerminationReason.FALLBACK,
            termination_message=f"Fallback: {error_message}",
            iterations_used=0,
            score_history=[],
            validator_results=[],
            warnings=[f"Using fallback due to: {error_message}"],
        )

    def _synthesis_loop(
        self,
        request: SynthesisRequest,
        criteria: ConvergenceCriteria,
    ) -> SynthesisResult:
        """
        Bounded synthesis loop with hard convergence criteria.

        v1.4: Added mutation escalation to escape local optima when stagnating.
        """

        # Initialize from family prior (with bounds clamping)
        proposal, clamp_warnings = self._create_initial_proposal(request)
        best_proposal = proposal
        best_score = float('-inf')
        score_history: List[float] = []
        all_warnings: List[str] = list(clamp_warnings)  # Start with clamp warnings

        # v1.4: Stagnation tracking for mutation escalation
        stagnation_count = 0
        last_best_score = float('-inf')

        for iteration in range(request.max_iterations):
            # Write proposal to state for validator evaluation
            self._write_proposal_to_state(proposal)

            # Run scoring validators
            results = self._run_validators()

            # Score results (v1.3: now returns structured adjustments)
            score, adjustments = self._score_results(results)
            score_history.append(score)

            # Track best
            if score > best_score:
                best_score = score
                best_proposal = proposal

            # v1.4: Detect stagnation (score not improving and below min_score)
            score_improvement = best_score - last_best_score
            if score_improvement < 0.1 and best_score < criteria.min_score:
                stagnation_count += 1
            else:
                stagnation_count = 0
            last_best_score = best_score

            # Extract convergence inputs
            validators_passed = sum(1 for r in results if r.get("passed", False))
            max_severity = self._get_max_severity(results)

            # v1.4.2: Estimate GM from hydrostatics if stability not yet computed
            # During hull synthesis, stability phase hasn't run, so we estimate:
            # GM = KB + BM - KG, where KG ≈ 0.55 × depth (typical for small craft)
            gm_actual = self.state.get("stability.gm_transverse_m")
            if gm_actual is None:
                kb = self.state.get("hull.kb_m", 0.0)
                bm = self.state.get("hull.bmt", 0.0)
                depth = self.state.get("hull.depth", 0.0)
                kg_estimate = 0.55 * depth  # VCG ≈ 55% of depth for typical small craft
                gm_actual = kb + bm - kg_estimate if (kb > 0 and bm > 0) else 0.5
                logger.debug(f"Estimated GM: {gm_actual:.3f}m (KB={kb:.3f}, BM={bm:.3f}, KG_est={kg_estimate:.3f})")

            gm_required = request.gm_min_m or 0.5

            # Check convergence
            converged, reason = criteria.is_converged(
                score=score,
                validators_passed=validators_passed,
                max_finding_severity=max_severity,
                gm_actual=gm_actual,
                gm_required=gm_required,
                score_history=score_history,
            )

            if converged:
                logger.info(f"Synthesis converged at iteration {iteration + 1}: {reason}")
                # Set Phase 2-6 features based on hull family and speed
                self._set_phase2_6_features(request)
                return SynthesisResult(
                    proposal=best_proposal,
                    termination=TerminationReason.CONVERGED,
                    termination_message=reason,
                    iterations_used=iteration + 1,
                    score_history=score_history,
                    validator_results=[r.get("name", "") for r in results if r.get("passed", False)],
                    warnings=all_warnings,
                )

            # v1.4: Calculate mutation scale (escalate when stagnating)
            if stagnation_count >= 3:
                # Escalate: start at 2.0x, increase by 0.5x per additional stagnant iteration
                mutation_scale = 2.0 + (stagnation_count - 3) * 0.5
                mutation_scale = min(mutation_scale, 4.0)  # Cap at 4x
                logger.debug(f"Iteration {iteration + 1}: stagnation={stagnation_count}, mutation_scale={mutation_scale:.1f}x")
            else:
                mutation_scale = 1.0

            # Mutate for next iteration (v1.3: uses structured adjustments)
            # v1.4: Pass family for per-iteration bounds clamping, scale for escalation
            proposal = self._mutate(
                proposal=proposal,
                adjustments=adjustments,
                iteration=iteration + 1,
                family=request.hull_family,
                request=request,
                scale=mutation_scale,
            )

        # Max iterations reached - return best found
        logger.warning(f"Synthesis did not converge after {request.max_iterations} iterations")
        all_warnings.append(f"Did not converge; best score: {best_score:.1f}")
        # Set Phase 2-6 features even for max iterations (hull is still usable)
        self._set_phase2_6_features(request)
        return SynthesisResult(
            proposal=best_proposal,
            termination=TerminationReason.MAX_ITERATIONS,
            termination_message=f"Reached {request.max_iterations} iterations",
            iterations_used=request.max_iterations,
            score_history=score_history,
            validator_results=[],
            warnings=all_warnings,
        )

    def _clamp_to_bounds(
        self,
        proposal: SynthesisProposal,
        family: HullFamily,
        request: Optional[SynthesisRequest] = None,
    ) -> Tuple[SynthesisProposal, List[str]]:
        """
        Clamp proposal to family bounds while PRESERVING current ratios.

        v1.2: Added to prevent unbounded Froude backsolve results.
        v1.4: Fixed to preserve current L/B and B/T ratios instead of
              snapping back to prior defaults. Only clamps if ratio is
              outside bounds, otherwise keeps exploration intact.

        Args:
            proposal: The proposal to clamp
            family: Hull family (determines bounds)

        Returns:
            (clamped_proposal, warnings) - warnings list any clamped values
        """
        prior = get_family_prior(family)
        bounds = prior.get("bounds", {})
        warnings: List[str] = []

        if not bounds:
            return proposal, warnings

        lwl = proposal.lwl_m
        beam = proposal.beam_m
        draft = proposal.draft_m
        cb = proposal.cb

        # Clamp LWL to absolute bounds unless LOA is a hard constraint.
        lwl_bounds = bounds.get("lwl_m")
        loa_locked = bool(request and request.loa_m and getattr(request, "loa_is_hard_constraint", True))
        if lwl_bounds:
            lwl_min, lwl_max = lwl_bounds
            if (lwl < lwl_min) or (lwl > lwl_max):
                if loa_locked:
                    warnings.append(
                        f"LWL {lwl:.1f}m outside family bounds {lwl_min}-{lwl_max}m (loa_is_hard_constraint)"
                    )
                else:
                    if lwl < lwl_min:
                        warnings.append(f"LWL {lwl:.1f}m clamped to min {lwl_min}m")
                        lwl = lwl_min
                    elif lwl > lwl_max:
                        warnings.append(f"LWL {lwl:.1f}m clamped to max {lwl_max}m")
                        lwl = lwl_max

        # PRESERVE current L/B ratio, only clamp if outside bounds
        lb_bounds = bounds.get("lwl_beam")
        if lb_bounds:
            lb_ratio = lwl / beam
            lb_min, lb_max = lb_bounds
            if lb_ratio < lb_min:
                # L/B too low (beam too wide) - narrow beam to meet minimum L/B
                beam = lwl / lb_min
                warnings.append(f"L/B {lb_ratio:.2f} below min {lb_min}, beam adjusted to {beam:.2f}m")
            elif lb_ratio > lb_max:
                # L/B too high (beam too narrow) - widen beam to meet maximum L/B
                beam = lwl / lb_max
                warnings.append(f"L/B {lb_ratio:.2f} above max {lb_max}, beam adjusted to {beam:.2f}m")
            # ELSE: keep beam as-is (valid exploration within bounds)

        # PRESERVE current B/T ratio, only clamp if outside bounds
        bt_bounds = bounds.get("beam_draft")
        if bt_bounds:
            bt_ratio = beam / draft
            bt_min, bt_max = bt_bounds
            if bt_ratio < bt_min:
                # B/T too low (draft too deep) - reduce draft to meet minimum B/T
                draft = beam / bt_min
                warnings.append(f"B/T {bt_ratio:.2f} below min {bt_min}, draft adjusted to {draft:.2f}m")
            elif bt_ratio > bt_max:
                # B/T too high (draft too shallow) - increase draft to meet maximum B/T
                draft = beam / bt_max
                warnings.append(f"B/T {bt_ratio:.2f} above max {bt_max}, draft adjusted to {draft:.2f}m")
            # ELSE: keep draft as-is (valid exploration within bounds)

        # Compute depth using centralized helper (single source of truth)
        depth = _compute_depth(draft, prior)

        # Clamp coefficients
        cb_bounds = bounds.get("cb")
        if cb_bounds:
            cb_min, cb_max = cb_bounds
            if cb < cb_min:
                cb = cb_min
                warnings.append(f"Cb clamped to min {cb_min}")
            elif cb > cb_max:
                cb = cb_max
                warnings.append(f"Cb clamped to max {cb_max}")

        displacement_m3 = lwl * beam * draft * cb

        # Clamp displacement
        loa_for_disp_bounds: Optional[float] = None
        if request and request.loa_m:
            loa_for_disp_bounds = float(request.loa_m)
        elif proposal.loa_m:
            loa_for_disp_bounds = float(proposal.loa_m)
        elif lwl and lwl > 0:
            loa_for_disp_bounds = float(lwl / 0.95)

        disp_bounds = (
            self._get_loa_scaled_displacement_bounds_m3(family, loa_for_disp_bounds)
            or bounds.get("displacement_m3")
        )
        if disp_bounds:
            disp_min, disp_max = disp_bounds
            if displacement_m3 < disp_min:
                warnings.append(f"Displacement {displacement_m3:.0f}m³ below min {disp_min}m³")
                # Scale up proportionally.
                #
                # Critical: when LOA is a hard constraint, LWL must remain fixed at ~0.95×LOA.
                # In that case, only scale beam and draft (2D) to reach displacement bounds.
                if displacement_m3 > 0:
                    if loa_locked:
                        scale_2d = math.sqrt(disp_min / displacement_m3)
                        beam *= scale_2d
                        draft *= scale_2d
                    else:
                        scale = (disp_min / displacement_m3) ** (1/3)
                        lwl *= scale
                        beam *= scale
                        draft *= scale
                depth = _compute_depth(draft, prior)  # Recompute depth after scaling
                displacement_m3 = disp_min
            elif displacement_m3 > disp_max:
                warnings.append(f"Displacement {displacement_m3:.0f}m³ above max {disp_max}m³")
                if displacement_m3 > 0:
                    if loa_locked:
                        scale_2d = math.sqrt(disp_max / displacement_m3)
                        beam *= scale_2d
                        draft *= scale_2d
                    else:
                        scale = (disp_max / displacement_m3) ** (1/3)
                        lwl *= scale
                        beam *= scale
                        draft *= scale
                depth = _compute_depth(draft, prior)  # Recompute depth after scaling
                displacement_m3 = disp_max

        # Preserve derived/secondary fields while keeping them consistent with clamped dims.
        if loa_locked:
            loa_m = float(request.loa_m)
        else:
            loa_m = float(proposal.loa_m) if proposal.loa_m else float(lwl / 0.95)

        draft_fwd_m = float(draft)
        draft_aft_m = float(draft)
        freeboard_m = max(0.0, float(depth) - max(draft_fwd_m, draft_aft_m, float(draft)))

        # Maintain hull spacing ratio if present
        hull_spacing_m = proposal.hull_spacing_m
        if hull_spacing_m is not None and proposal.beam_m and proposal.beam_m > 0:
            spacing_ratio = float(hull_spacing_m) / float(proposal.beam_m)
            hull_spacing_m = max(1.0, float(beam) * spacing_ratio)

        hull_type = proposal.hull_type
        if request:
            hull_type = self._infer_hull_type(family, calculate_froude(request.max_speed_kts, lwl))

        clamped = SynthesisProposal(
            lwl_m=float(lwl),
            beam_m=float(beam),
            draft_m=float(draft),
            depth_m=float(depth),
            cb=float(cb),
            cp=float(proposal.cp),
            cm=float(proposal.cm),
            cwp=float(proposal.cwp),
            displacement_m3=float(displacement_m3),
            confidence=proposal.confidence * (0.9 if warnings else 1.0),  # Reduce confidence if clamped
            iteration=proposal.iteration,
            source="clamped" if warnings else proposal.source,
            loa_m=loa_m,
            draft_fwd_m=draft_fwd_m,
            draft_aft_m=draft_aft_m,
            freeboard_m=freeboard_m,
            hull_type=hull_type,
            hull_spacing_m=hull_spacing_m,
            transom_beam_ratio=proposal.transom_beam_ratio,
            bow_flare_deg=proposal.bow_flare_deg,
            stem_rake_deg=proposal.stem_rake_deg,
            bow_entrance_deg=proposal.bow_entrance_deg,
            lcb_fraction=proposal.lcb_fraction,
            deadrise_deg=proposal.deadrise_deg,
            deadrise_transom_deg=proposal.deadrise_transom_deg,
        )

        return clamped, warnings

    def _create_initial_proposal(self, request: SynthesisRequest) -> Tuple[SynthesisProposal, List[str]]:
        """
        Create initial proposal from family prior WITH bounds checking.

        v1.2: Now applies bounds clamping and returns warnings.
        v1.4: Uses centralized _compute_depth() helper.

        Returns:
            Tuple of (proposal, clamp_warnings)
        """
        prior = get_family_prior(request.hull_family)
        warnings: List[str] = []

        # ------------------------------------------------------------
        # 1) Length estimation (LOA hard constraint if provided)
        # ------------------------------------------------------------
        if request.loa_m:
            lwl = float(request.loa_m) * 0.95
        else:
            speed_ms = float(request.max_speed_kts) * 0.5144
            target_fn = float(prior["froude_design"])
            lwl = (speed_ms / target_fn) ** 2 / 9.81

        # Compute actual Fn for regime-adjusted priors
        froude_actual = calculate_froude(request.max_speed_kts, lwl)

        # ------------------------------------------------------------
        # 2) Mission-driven displacement estimate (optional)
        # ------------------------------------------------------------
        disp_target_m3, disp_warnings = self._estimate_required_displacement_m3(request)
        warnings.extend(disp_warnings)

        # Clamp displacement target to family bounds (if provided)
        bounds = prior.get("bounds", {}) or {}
        loa_for_disp_bounds = float(request.loa_m) if request.loa_m else float(lwl / 0.95)
        disp_bounds = (
            self._get_loa_scaled_displacement_bounds_m3(request.hull_family, loa_for_disp_bounds)
            or bounds.get("displacement_m3")
        )
        if disp_target_m3 is not None and disp_bounds:
            disp_min, disp_max = disp_bounds
            if disp_target_m3 < disp_min:
                warnings.append(f"disp_target {disp_target_m3:.1f}m³ below family min {disp_min}m³; clamped")
                disp_target_m3 = float(disp_min)
            elif disp_target_m3 > disp_max:
                warnings.append(f"disp_target {disp_target_m3:.1f}m³ above family max {disp_max}m³; clamped")
                disp_target_m3 = float(disp_max)

        # Start from regime-adjusted Cb prior (then couple Cp/Cm)
        cb_seed = get_regime_adjusted_prior(request.hull_family, "cb", froude_actual)
        cb_seed = float(cb_seed) if isinstance(cb_seed, (int, float)) else float(prior["cb"])

        # ------------------------------------------------------------
        # 3) Dimension solve (ratios + optional displacement target)
        # ------------------------------------------------------------
        if disp_target_m3 is not None and disp_target_m3 > 0:
            # Solve for beam/draft from displacement and a B/T ratio seed.
            bt_seed = float(prior["beam_draft"])
            denom = float(lwl) * float(cb_seed)
            if denom <= 0:
                denom = 1.0

            beam = math.sqrt(max(1e-6, (disp_target_m3 * bt_seed) / denom))
            draft = beam / bt_seed if bt_seed > 0 else beam / 3.0

            # Clamp L/B by adjusting beam; recompute draft to hit target displacement
            lb_bounds = bounds.get("lwl_beam")
            if lb_bounds:
                lb_min, lb_max = lb_bounds
                lb_actual = (lwl / beam) if beam > 0 else 0.0
                if lb_actual < lb_min:
                    beam = lwl / lb_min
                    draft = disp_target_m3 / (lwl * beam * cb_seed) if (lwl * beam * cb_seed) > 0 else draft
                elif lb_actual > lb_max:
                    beam = lwl / lb_max
                    draft = disp_target_m3 / (lwl * beam * cb_seed) if (lwl * beam * cb_seed) > 0 else draft

            # Clamp B/T by adjusting draft
            bt_bounds = bounds.get("beam_draft")
            if bt_bounds and draft > 0:
                bt_min, bt_max = bt_bounds
                bt_actual = beam / draft
                bt_clamped = max(bt_min, min(bt_max, bt_actual))
                if abs(bt_clamped - bt_actual) > 1e-6:
                    draft = beam / bt_clamped

            # Choose Cb to meet displacement (then couple Cp/Cm)
            cb_required = disp_target_m3 / (lwl * beam * draft) if (lwl * beam * draft) > 0 else cb_seed
            cb, cp, cm = _apply_coefficient_coupling(cb_required, prior)
        else:
            # Legacy ratio-only sizing (no mission displacement)
            beam = lwl / float(prior["lwl_beam"])
            draft = beam / float(prior["beam_draft"])
            cb, cp, cm = _apply_coefficient_coupling(cb_seed, prior)

        depth = _compute_depth(draft, prior)  # Use centralized helper
        cwp = float(prior["cwp"])

        displacement_m3 = float(lwl) * float(beam) * float(draft) * float(cb)

        # ------------------------------------------------------------
        # 4) Fill hull-form parameters from regime-adjusted priors
        # ------------------------------------------------------------
        deadrise_deg = self._mid(get_regime_adjusted_prior(request.hull_family, "deadrise_deg", froude_actual))
        deadrise_transom_deg = self._mid(get_regime_adjusted_prior(request.hull_family, "deadrise_transom_deg", froude_actual))
        if deadrise_deg is not None and deadrise_transom_deg is not None:
            deadrise_transom_deg = min(deadrise_transom_deg, deadrise_deg)

        bow_entrance_deg = self._mid(get_regime_adjusted_prior(request.hull_family, "bow_entrance_deg", froude_actual))
        bow_flare_deg = self._mid(get_regime_adjusted_prior(request.hull_family, "bow_flare_deg", froude_actual))
        stem_rake_deg = self._mid(get_regime_adjusted_prior(request.hull_family, "stem_rake_deg", froude_actual))
        transom_beam_ratio = self._mid(get_regime_adjusted_prior(request.hull_family, "transom_beam_ratio", froude_actual))
        lcb_fraction = self._mid(get_regime_adjusted_prior(request.hull_family, "lcb_fraction", froude_actual))

        hull_type = self._infer_hull_type(request.hull_family, froude_actual)

        hull_spacing_m = None
        if request.hull_family == HullFamily.CATAMARAN:
            spacing_ratio = self._mid(get_regime_adjusted_prior(request.hull_family, "hull_spacing_ratio", froude_actual))
            if spacing_ratio is not None:
                hull_spacing_m = max(1.0, float(beam) * float(spacing_ratio))

        loa_m = float(request.loa_m) if request.loa_m else float(lwl / 0.95)
        draft_fwd_m = float(draft)
        draft_aft_m = float(draft)
        freeboard_m = max(0.0, float(depth) - max(draft_fwd_m, draft_aft_m, float(draft)))

        proposal = SynthesisProposal(
            lwl_m=float(lwl),
            beam_m=float(beam),
            draft_m=float(draft),
            depth_m=float(depth),
            cb=float(cb),
            cp=float(cp),
            cm=float(cm),
            cwp=float(cwp),
            displacement_m3=float(displacement_m3),
            confidence=0.7,
            iteration=0,
            source="prior",
            loa_m=loa_m,
            draft_fwd_m=draft_fwd_m,
            draft_aft_m=draft_aft_m,
            freeboard_m=freeboard_m,
            hull_type=hull_type,
            hull_spacing_m=hull_spacing_m,
            transom_beam_ratio=transom_beam_ratio,
            bow_flare_deg=bow_flare_deg,
            stem_rake_deg=stem_rake_deg,
            bow_entrance_deg=bow_entrance_deg,
            lcb_fraction=lcb_fraction,
            deadrise_deg=deadrise_deg,
            deadrise_transom_deg=deadrise_transom_deg,
        )

        # Apply bounds clamping
        clamped, clamp_warnings = self._clamp_to_bounds(proposal, request.hull_family, request=request)
        warnings.extend(clamp_warnings)

        return clamped, warnings

    def _write_proposal_to_state(self, proposal: SynthesisProposal) -> None:
        """Write proposal to state for validator evaluation."""
        params = proposal.to_state_dict()
        self.lock.write_hull_params(params, "hull_synthesizer")

    def _set_phase2_6_features(self, request: SynthesisRequest) -> None:
        """
        Set Phase 2-6 hull features based on hull family and speed.
        
        This ensures each hull family gets appropriate defaults for:
        - Phase 2: Chine type and configuration
        - Phase 3: Bow style
        - Phase 4: Spray rails
        - Phase 5: Transom style
        - Phase 6: Tumblehome, panels, deck
        
        Called after synthesis converges to populate geometry features.
        
        LLM-Generated Hull Refinement v1.0:
        - If the LLM has already proposed a feature value, synthesis RESPECTS it.
        - Synthesis only fills in features that are still None/missing.
        - This allows the LLM to be a "feature-level design partner" while
          synthesis acts as a "senior reviewer" that fills gaps.
        """
        family = request.hull_family
        froude = self._calculate_design_froude(request)
        source = "hull_synthesizer"
        
        # LLM-Generated Hull Refinement v1.0: Check if feature was already set
        def _should_set_feature(path: str) -> bool:
            """
            Returns True if synthesis should set this feature.
            Returns False if LLM/user already proposed a value (respect their intent).
            
            Provenance hierarchy (high to low override authority):
            - USER: Highest - user explicitly set, never override
            - LLM_PROPOSED: High - LLM proposed as creative intent, don't override
            - SYNTHESIZED: Medium - previous synthesis, can be re-synthesized
            - PLACEHOLDER: Low - ship-scale defaults, should be replaced
            - None: Lowest - missing value, should be filled
            """
            current_value = self.state.get(path)
            # If value is None or missing, synthesis should fill it
            if current_value is None:
                logger.debug(f"[_should_set_feature] {path}: value=None, returning True")
                return True
            # If provenance tracking exists, check authority level
            if hasattr(self.state, 'get_provenance'):
                provenance = self.state.get_provenance(path)
                logger.debug(f"[_should_set_feature] {path}: value={current_value}, provenance={provenance!r}")
                # Respect user and LLM intent - these are authoritative
                if provenance in ("user", "llm_proposed"):
                    logger.info(f"[_should_set_feature] {path}: RESPECTING {provenance} intent (value={current_value})")
                    return False
                # Override placeholders and missing provenance
                if provenance in ("placeholder", None):
                    logger.debug(f"[_should_set_feature] {path}: overriding {provenance}")
                    return True
                # For synthesized: only re-synthesize if this is a new synthesis run
                # (for now, don't override prior synthesis - user can trigger re-synthesis)
                if provenance == "synthesized":
                    logger.debug(f"[_should_set_feature] {path}: keeping synthesized value")
                    return False
                return True
            # No provenance tracking - value exists, so don't override
            logger.debug(f"[_should_set_feature] {path}: no provenance tracking, value exists, not overriding")
            return False
        
        # Build params dict for Phase 2-6 features (only for paths that need defaults)
        params: Dict[str, Any] = {}
        
        # ======================================================================
        # PHASE 2: Chine Type by Family
        # ======================================================================
        FAMILY_CHINE_DEFAULTS = {
            HullFamily.PATROL: ("hard", 1),      # Single hard chine
            HullFamily.PLANING: ("double", 2),   # Double chine for planing
            HullFamily.WORKBOAT: ("hard", 1),    # Single hard chine
            HullFamily.FERRY: ("soft", 0),       # Round bilge
            HullFamily.CATAMARAN: ("hard", 1),   # Hard chine per demihull
        }
        
        chine_type, chine_count = FAMILY_CHINE_DEFAULTS.get(family, ("soft", 0))
        
        # Upgrade to double chine for high-speed planing
        if froude > 0.7 and chine_type == "hard":
            chine_type = "double"
            chine_count = 2
        
        params["hull.chine_type"] = chine_type
        params["hull.chine_count"] = chine_count
        
        # ======================================================================
        # PHASE 3: Bow Style by Family and Speed
        # ======================================================================
        if family == HullFamily.PATROL:
            bow_style = "wedge" if froude > 0.5 else "traditional"
        elif family == HullFamily.PLANING:
            bow_style = "wedge"
        elif family == HullFamily.CATAMARAN:
            bow_style = "wave_piercing" if froude > 0.5 else "traditional"
        elif family == HullFamily.WORKBOAT:
            bow_style = "traditional"
        elif family == HullFamily.FERRY:
            bow_style = "traditional"
        else:
            bow_style = "traditional"
        
        params["hull.bow_style"] = bow_style
        
        # Stem profile to match bow style
        if bow_style == "wedge":
            params["hull.stem_profile"] = "raked"
        elif bow_style == "axe":
            params["hull.stem_profile"] = "vertical"
        elif bow_style == "wave_piercing":
            params["hull.stem_profile"] = "wave_piercing"
        else:
            params["hull.stem_profile"] = "raked"
        
        # ======================================================================
        # PHASE 4: Spray Rails by Speed
        # ======================================================================
        if froude > 0.5 and family in (HullFamily.PATROL, HullFamily.PLANING, HullFamily.CATAMARAN):
            # Add spray rails for semi-planing and planing hulls
            if froude > 0.8:
                spray_rail_count = 3
            elif froude > 0.6:
                spray_rail_count = 2
            else:
                spray_rail_count = 1
            
            params["hull.has_spray_rails"] = True
            params["hull.spray_rail_count"] = spray_rail_count
        else:
            params["hull.has_spray_rails"] = False
            params["hull.spray_rail_count"] = 0
        
        # Knuckle lines for patrol boats (styling)
        if family == HullFamily.PATROL:
            params["hull.has_knuckle_lines"] = True
        else:
            params["hull.has_knuckle_lines"] = False
        
        # ======================================================================
        # PHASE 5: Transom Style by Family
        # ======================================================================
        FAMILY_TRANSOM_DEFAULTS = {
            HullFamily.PATROL: ("raked", 12.0),
            HullFamily.PLANING: ("raked", 14.0),
            HullFamily.WORKBOAT: ("raked", 10.0),
            HullFamily.FERRY: ("raked", 8.0),
            HullFamily.CATAMARAN: ("raked", 10.0),
        }
        
        transom_style, transom_rake = FAMILY_TRANSOM_DEFAULTS.get(family, ("raked", 12.0))
        params["hull.transom_style"] = transom_style
        params["hull.transom_rake_deg"] = transom_rake
        
        # ======================================================================
        # PHASE 6: Tumblehome, Panels, Deck
        # ======================================================================
        # Tumblehome for military/patrol vessels
        if family == HullFamily.PATROL:
            params["hull.tumblehome_enabled"] = True
            params["hull.tumblehome_angle_deg"] = 5.0
            params["hull.tumblehome_start_ratio"] = 0.1
        else:
            params["hull.tumblehome_enabled"] = False
            params["hull.tumblehome_angle_deg"] = 0.0
            params["hull.tumblehome_start_ratio"] = 0.0
        
        # Panel style (default smooth, user can request faceted)
        params["hull.panel_style"] = "smooth"
        
        # Deck always enabled
        params["hull.deck_enabled"] = True
        
        # Deck camber by family
        if family in (HullFamily.WORKBOAT, HullFamily.FERRY):
            params["hull.deck_camber_m"] = 0.05  # More camber for workboats
        else:
            params["hull.deck_camber_m"] = 0.02  # Slight camber for patrol
        
        # ======================================================================
        # LLM-Generated Hull Refinement v1.0: Filter params
        # Only write params where LLM/user hasn't already set a value
        # ======================================================================
        llm_respected = []
        synthesis_filled = []
        
        filtered_params = {}
        for path, value in params.items():
            if _should_set_feature(path):
                filtered_params[path] = value
                synthesis_filled.append(path)
            else:
                llm_respected.append(path)
        
        if llm_respected:
            logger.info(
                f"[hull_synthesizer] Respecting LLM/user intent for: {llm_respected}"
            )
        
        # Write Phase 2-6 parameters directly to state (these don't require base hull params)
        # Use transaction to satisfy mutation enforcement for refinable paths
        owns_transaction = not self.state.in_transaction()
        if owns_transaction:
            self.state.begin_transaction()
        try:
            for path, value in filtered_params.items():
                self.state.set(path, value, source)
            if owns_transaction:
                self.state.commit()
        except Exception:
            if owns_transaction:
                try:
                    self.state.rollback()
                except Exception:
                    pass  # Rollback may fail if not in transaction
            raise
        
        logger.info(
            f"Phase 2-6 features: synthesis filled {len(synthesis_filled)} features, "
            f"respected LLM intent for {len(llm_respected)} features. "
            f"chine={filtered_params.get('hull.chine_type', 'LLM')}, "
            f"bow={filtered_params.get('hull.bow_style', 'LLM')}, "
            f"spray_rails={filtered_params.get('hull.spray_rail_count', 'LLM')}, "
            f"tumblehome={filtered_params.get('hull.tumblehome_enabled', 'LLM')}"
        )

    def _calculate_design_froude(self, request: SynthesisRequest) -> float:
        """Calculate design Froude number from request."""
        speed_kts = request.max_speed_kts or 20.0
        loa = request.loa_m or 20.0
        lwl = loa * 0.95  # Approximate LWL
        
        speed_ms = speed_kts * 0.5144
        froude = speed_ms / (9.81 * lwl) ** 0.5
        return froude

    def _run_validators(self) -> List[Dict[str, Any]]:
        """Run scoring validators and return results."""
        results = []

        # Try to run through executor if available
        if self.executor:
            try:
                for validator_id in self.SCORING_VALIDATORS:
                    result = self.executor.execute_single(validator_id, self.state)
                    if result:
                        results.append({
                            "name": validator_id,
                            "passed": result.passed,
                            "findings": [f.to_dict() for f in result.findings] if hasattr(result, 'findings') else [],
                        })
            except Exception as e:
                logger.warning(f"Validator execution failed: {e}")

        # If no results, assume pass (validators may not be implemented)
        if not results:
            results = [{"name": v, "passed": True, "findings": []} for v in self.SCORING_VALIDATORS]

        return results

    def _score_results(self, results: List[Dict[str, Any]]) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Convert validator results to score + structured adjustments.

        v1.3: Now extracts structured `adjustment` hints from findings
        instead of parsing suggestion strings.
        v1.4: Added support for "preference" severity level.
        v1.4.1: Cap preference penalty at -2.0 to prevent convergence interference.

        Returns:
            Tuple of (score, adjustments) where adjustments is a list of
            {"path": str, "direction": str, "magnitude": float} dicts.
        """
        score = 100.0
        adjustments: List[Dict[str, Any]] = []
        preference_penalty = 0.0  # v1.4.1: Track separately to cap

        for result in results:
            if not result.get("passed", True):
                score -= 20.0

            for finding in result.get("findings", []):
                severity = finding.get("severity", "info")
                if severity == "error":
                    score -= 10.0
                elif severity == "warning":
                    score -= 2.0
                elif severity == "preference":
                    # v1.4.1: Accumulate preference penalty (capped below)
                    preference_penalty += 0.5

                # v1.3: Extract structured adjustment if present
                adjustment = finding.get("adjustment")
                if adjustment and isinstance(adjustment, dict):
                    # Validate adjustment has required fields
                    if "path" in adjustment and "direction" in adjustment:
                        adjustments.append(adjustment)

        # v1.4.1: Cap preference penalty at -2.0 to prevent convergence interference
        # Without cap, 20 preference findings = -10 points, blocking min_score
        score -= min(preference_penalty, 2.0)

        return score, adjustments

    def _get_max_severity(self, results: List[Dict[str, Any]]) -> str:
        """
        Get highest severity from all findings.

        v1.4: Updated to include "preference" severity level.
        Uses centralized SEVERITY_ORDER from taxonomy.
        """
        max_sev = "info"
        # v1.4: Severity order (higher = more severe)
        # Matches SEVERITY_ORDER in taxonomy.py
        order = {"passed": 0, "info": 1, "preference": 2, "warning": 3, "error": 4}

        for result in results:
            for finding in result.get("findings", []):
                sev = finding.get("severity", "info")
                if order.get(sev, 0) > order.get(max_sev, 0):
                    max_sev = sev

        return max_sev

    def _mutate(
        self,
        proposal: SynthesisProposal,
        adjustments: List[Dict[str, Any]],
        iteration: int,
        family: HullFamily,
        request: Optional[SynthesisRequest] = None,
        scale: float = 1.0,
    ) -> SynthesisProposal:
        """
        Apply bounded mutations based on structured adjustments.

        v1.3: Now consumes structured adjustments from validators
        instead of parsing suggestion strings.
        v1.4: Added family parameter for per-iteration bounds clamping.
              Added scale parameter for mutation escalation.

        Args:
            proposal: Current proposal to mutate
            adjustments: List of {"path": str, "direction": str, "magnitude": float} dicts
            iteration: Current iteration number
            family: Hull family (required for bounds clamping)
            scale: Mutation scale multiplier (default 1.0, increased during escalation)

        Returns:
            Mutated SynthesisProposal (clamped to bounds)
        """
        prior = get_family_prior(family)
        loa_locked = bool(request and request.loa_m and getattr(request, "loa_is_hard_constraint", True))
        delta_lwl = delta_beam = delta_draft = delta_cb = 0.0

        for adj in adjustments:
            path = adj.get("path", "")
            direction = adj.get("direction", "")
            magnitude = adj.get("magnitude", self.MUTATION_DELTA)

            # Clamp magnitude to prevent extreme changes (before scaling)
            magnitude = min(magnitude, 0.10)  # Max 10% change per adjustment

            # Apply scale multiplier for escalation
            magnitude *= scale

            # Determine sign based on direction
            sign = 1.0 if direction == "increase" else -1.0 if direction == "decrease" else 0.0

            # Map path to dimension delta
            if "lwl" in path or "length" in path:
                if loa_locked:
                    continue  # LOA hard constraint -> don't mutate length
                delta_lwl += sign * magnitude
            elif "beam" in path or "width" in path:
                delta_beam += sign * magnitude
            elif "draft" in path:
                delta_draft += sign * magnitude
            elif "cb" in path:
                delta_cb += sign * magnitude

        # Clamp total deltas to prevent runaway mutations (scaled limits)
        max_delta = 0.15 * scale
        max_cb_delta = 0.10 * scale
        delta_lwl = max(-max_delta, min(max_delta, delta_lwl))
        delta_beam = max(-max_delta, min(max_delta, delta_beam))
        delta_draft = max(-max_delta, min(max_delta, delta_draft))
        delta_cb = max(-max_cb_delta, min(max_cb_delta, delta_cb))

        lwl = proposal.lwl_m * (1 + delta_lwl)
        if loa_locked:
            lwl = float(request.loa_m) * 0.95
        beam = proposal.beam_m * (1 + delta_beam)
        draft = proposal.draft_m * (1 + delta_draft)
        depth = _compute_depth(draft, prior)  # Use centralized helper
        cb_raw = proposal.cb * (1 + delta_cb)

        # Apply coefficient coupling (v1.4): Cp fixed, Cm derived from Cb
        # This ensures Cb = Cp × Cm relationship is maintained
        cb, cp, cm = _apply_coefficient_coupling(cb_raw, prior)

        displacement_m3 = lwl * beam * draft * cb

        # Preserve/enrich secondary hull-form fields
        if loa_locked:
            loa_m = float(request.loa_m)
        else:
            loa_m = float(proposal.loa_m) if proposal.loa_m else float(lwl / 0.95)

        draft_fwd_m = float(draft)
        draft_aft_m = float(draft)
        freeboard_m = max(0.0, float(depth) - max(draft_fwd_m, draft_aft_m, float(draft)))

        hull_type = proposal.hull_type
        if request:
            hull_type = self._infer_hull_type(family, calculate_froude(request.max_speed_kts, lwl))

        hull_spacing_m = proposal.hull_spacing_m
        if hull_spacing_m is not None and proposal.beam_m and proposal.beam_m > 0:
            spacing_ratio = float(hull_spacing_m) / float(proposal.beam_m)
            hull_spacing_m = max(1.0, float(beam) * spacing_ratio)

        # Create unclamped proposal
        unclamped = SynthesisProposal(
            lwl_m=lwl,
            beam_m=beam,
            draft_m=draft,
            depth_m=depth,
            cb=cb,
            cp=cp,   # Now uses coupled value (fixed from prior)
            cm=cm,   # Now uses coupled value (derived from Cb/Cp)
            cwp=proposal.cwp,  # Cwp unchanged for v1.4
            displacement_m3=displacement_m3,
            confidence=proposal.confidence * 0.95,  # Slightly decrease with each mutation
            iteration=iteration,
            source="mutated",
            loa_m=loa_m,
            draft_fwd_m=draft_fwd_m,
            draft_aft_m=draft_aft_m,
            freeboard_m=freeboard_m,
            hull_type=hull_type,
            hull_spacing_m=hull_spacing_m,
            transom_beam_ratio=proposal.transom_beam_ratio,
            bow_flare_deg=proposal.bow_flare_deg,
            stem_rake_deg=proposal.stem_rake_deg,
            bow_entrance_deg=proposal.bow_entrance_deg,
            lcb_fraction=proposal.lcb_fraction,
            deadrise_deg=proposal.deadrise_deg,
            deadrise_transom_deg=proposal.deadrise_transom_deg,
        )

        # Apply per-iteration bounds clamping (v1.4)
        clamped, clamp_warnings = self._clamp_to_bounds(unclamped, family, request=request)
        if clamp_warnings:
            logger.debug(f"Iteration {iteration} clamping: {clamp_warnings}")

        return clamped

    def _create_fallback_result(
        self,
        request: SynthesisRequest,
        error: str,
    ) -> SynthesisResult:
        """Create fallback result when synthesis fails."""
        fallback = create_fallback_proposal(
            hull_family=request.hull_family,
            max_speed_kts=request.max_speed_kts,
            loa_m=request.loa_m,
            reason=error,
        )

        # Enrich fallback with hull-form priors so downstream geometry/validators have full inputs.
        froude_actual = calculate_froude(request.max_speed_kts, fallback.lwl_m)
        hull_type = self._infer_hull_type(request.hull_family, froude_actual)

        deadrise_deg = self._mid(get_regime_adjusted_prior(request.hull_family, "deadrise_deg", froude_actual))
        deadrise_transom_deg = self._mid(get_regime_adjusted_prior(request.hull_family, "deadrise_transom_deg", froude_actual))
        if deadrise_deg is not None and deadrise_transom_deg is not None:
            deadrise_transom_deg = min(deadrise_transom_deg, deadrise_deg)

        bow_entrance_deg = self._mid(get_regime_adjusted_prior(request.hull_family, "bow_entrance_deg", froude_actual))
        bow_flare_deg = self._mid(get_regime_adjusted_prior(request.hull_family, "bow_flare_deg", froude_actual))
        stem_rake_deg = self._mid(get_regime_adjusted_prior(request.hull_family, "stem_rake_deg", froude_actual))
        transom_beam_ratio = self._mid(get_regime_adjusted_prior(request.hull_family, "transom_beam_ratio", froude_actual))
        lcb_fraction = self._mid(get_regime_adjusted_prior(request.hull_family, "lcb_fraction", froude_actual))

        hull_spacing_m = None
        if request.hull_family == HullFamily.CATAMARAN:
            spacing_ratio = self._mid(get_regime_adjusted_prior(request.hull_family, "hull_spacing_ratio", froude_actual))
            if spacing_ratio is not None:
                hull_spacing_m = max(1.0, float(fallback.beam_m) * float(spacing_ratio))

        loa_m = float(request.loa_m) if request.loa_m else float(fallback.lwl_m / 0.95)
        draft_fwd_m = float(fallback.draft_m)
        draft_aft_m = float(fallback.draft_m)
        freeboard_m = max(0.0, float(fallback.depth_m) - max(draft_fwd_m, draft_aft_m))

        proposal = SynthesisProposal(
            lwl_m=fallback.lwl_m,
            beam_m=fallback.beam_m,
            draft_m=fallback.draft_m,
            depth_m=fallback.depth_m,
            cb=fallback.cb,
            cp=fallback.cp,
            cm=fallback.cm,
            cwp=fallback.cwp,
            displacement_m3=fallback.displacement_m3,
            confidence=fallback.confidence,
            iteration=0,
            source="fallback",
            loa_m=loa_m,
            draft_fwd_m=draft_fwd_m,
            draft_aft_m=draft_aft_m,
            freeboard_m=freeboard_m,
            hull_type=hull_type,
            hull_spacing_m=hull_spacing_m,
            transom_beam_ratio=transom_beam_ratio,
            bow_flare_deg=bow_flare_deg,
            stem_rake_deg=stem_rake_deg,
            bow_entrance_deg=bow_entrance_deg,
            lcb_fraction=lcb_fraction,
            deadrise_deg=deadrise_deg,
            deadrise_transom_deg=deadrise_transom_deg,
        )

        # Set Phase 2-6 features even in fallback
        try:
            self._set_phase2_6_features(request)
        except Exception as e:
            logger.warning(f"Failed to set Phase 2-6 features in fallback: {e}")

        return SynthesisResult(
            proposal=proposal,
            termination=TerminationReason.FALLBACK,
            termination_message=f"Fallback due to: {error}",
            iterations_used=0,
            score_history=[],
            validator_results=[],
            warnings=[f"Used estimator-only fallback: {error}"],
        )
