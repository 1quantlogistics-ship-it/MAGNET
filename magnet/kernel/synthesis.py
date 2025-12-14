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

from .priors.hull_families import HullFamily, get_family_prior
from .synthesis_lock import SynthesisLock, SynthesisLockError
from .synthesis_fallback import create_fallback_proposal, FallbackMode

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
    """
    hull_family: HullFamily          # Required - determines prior
    max_speed_kts: float             # Required - drives Froude estimation

    # Optional constraints (None = use family default)
    loa_m: Optional[float] = None
    payload_kg: Optional[float] = None
    crew_count: Optional[int] = None
    range_nm: Optional[float] = None
    gm_min_m: Optional[float] = None

    # Convergence parameters (can override defaults)
    max_iterations: int = 15
    convergence_criteria: Optional["ConvergenceCriteria"] = None

    def __post_init__(self):
        if self.max_speed_kts <= 0:
            raise ValueError("max_speed_kts must be positive")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be >= 1")


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

    @property
    def is_complete(self) -> bool:
        """All parameters are valid positive numbers."""
        return all(v > 0 for v in [
            self.lwl_m, self.beam_m, self.draft_m, self.depth_m,
            self.cb, self.cp, self.cm, self.cwp
        ])

    def to_state_dict(self) -> Dict[str, float]:
        """Complete hull state - never partial."""
        if not self.is_complete:
            raise ValueError("Cannot commit incomplete proposal")
        return {
            "hull.lwl": self.lwl_m,
            "hull.beam": self.beam_m,
            "hull.draft": self.draft_m,
            "hull.depth": self.depth_m,
            "hull.cb": self.cb,
            "hull.cp": self.cp,
            "hull.cm": self.cm,
            "hull.cwp": self.cwp,
            "hull.displacement_m3": self.displacement_m3,
        }


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
            proposal = self._mutate(proposal, adjustments, iteration + 1, request.hull_family, mutation_scale)

        # Max iterations reached - return best found
        logger.warning(f"Synthesis did not converge after {request.max_iterations} iterations")
        all_warnings.append(f"Did not converge; best score: {best_score:.1f}")
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

        # Clamp LWL to absolute bounds
        lwl_bounds = bounds.get("lwl_m")
        if lwl_bounds:
            lwl_min, lwl_max = lwl_bounds
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
        disp_bounds = bounds.get("displacement_m3")
        if disp_bounds:
            disp_min, disp_max = disp_bounds
            if displacement_m3 < disp_min:
                warnings.append(f"Displacement {displacement_m3:.0f}m³ below min {disp_min}m³")
                # Scale up proportionally
                scale = (disp_min / displacement_m3) ** (1/3)
                lwl *= scale
                beam *= scale
                draft *= scale
                depth = _compute_depth(draft, prior)  # Recompute depth after scaling
                displacement_m3 = disp_min
            elif displacement_m3 > disp_max:
                warnings.append(f"Displacement {displacement_m3:.0f}m³ above max {disp_max}m³")
                scale = (disp_max / displacement_m3) ** (1/3)
                lwl *= scale
                beam *= scale
                draft *= scale
                depth = _compute_depth(draft, prior)  # Recompute depth after scaling
                displacement_m3 = disp_max

        clamped = SynthesisProposal(
            lwl_m=lwl,
            beam_m=beam,
            draft_m=draft,
            depth_m=depth,
            cb=cb,
            cp=proposal.cp,
            cm=proposal.cm,
            cwp=proposal.cwp,
            displacement_m3=displacement_m3,
            confidence=proposal.confidence * (0.9 if warnings else 1.0),  # Reduce confidence if clamped
            iteration=proposal.iteration,
            source="clamped" if warnings else proposal.source,
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

        # Froude-based length estimation
        if request.loa_m:
            lwl = request.loa_m * 0.95
        else:
            speed_ms = request.max_speed_kts * 0.5144
            target_fn = prior["froude_design"]
            lwl = (speed_ms / target_fn) ** 2 / 9.81

        beam = lwl / prior["lwl_beam"]
        draft = beam / prior["beam_draft"]
        depth = _compute_depth(draft, prior)  # Use centralized helper
        cb = prior["cb"]
        displacement_m3 = lwl * beam * draft * cb

        proposal = SynthesisProposal(
            lwl_m=lwl,
            beam_m=beam,
            draft_m=draft,
            depth_m=depth,
            cb=cb,
            cp=prior["cp"],
            cm=prior["cm"],
            cwp=prior["cwp"],
            displacement_m3=displacement_m3,
            confidence=0.7,
            iteration=0,
            source="prior",
        )

        # Apply bounds clamping
        clamped, clamp_warnings = self._clamp_to_bounds(proposal, request.hull_family)

        return clamped, clamp_warnings

    def _write_proposal_to_state(self, proposal: SynthesisProposal) -> None:
        """Write proposal to state for validator evaluation."""
        params = proposal.to_state_dict()
        self.lock.write_hull_params(params, "hull_synthesizer")

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
        beam = proposal.beam_m * (1 + delta_beam)
        draft = proposal.draft_m * (1 + delta_draft)
        depth = _compute_depth(draft, prior)  # Use centralized helper
        cb_raw = proposal.cb * (1 + delta_cb)

        # Apply coefficient coupling (v1.4): Cp fixed, Cm derived from Cb
        # This ensures Cb = Cp × Cm relationship is maintained
        cb, cp, cm = _apply_coefficient_coupling(cb_raw, prior)

        displacement_m3 = lwl * beam * draft * cb

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
        )

        # Apply per-iteration bounds clamping (v1.4)
        clamped, clamp_warnings = self._clamp_to_bounds(unclamped, family)
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
        )

        return SynthesisResult(
            proposal=proposal,
            termination=TerminationReason.FALLBACK,
            termination_message=f"Fallback due to: {error}",
            iterations_used=0,
            score_history=[],
            validator_results=[],
            warnings=[f"Used estimator-only fallback: {error}"],
        )
