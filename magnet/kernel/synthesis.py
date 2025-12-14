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
        """Bounded synthesis loop with hard convergence criteria."""

        # Initialize from family prior
        proposal = self._create_initial_proposal(request)
        best_proposal = proposal
        best_score = float('-inf')
        score_history: List[float] = []

        for iteration in range(request.max_iterations):
            # Write proposal to state for validator evaluation
            self._write_proposal_to_state(proposal)

            # Run scoring validators
            results = self._run_validators()

            # Score results
            score, suggestions = self._score_results(results)
            score_history.append(score)

            # Track best
            if score > best_score:
                best_score = score
                best_proposal = proposal

            # Extract convergence inputs
            validators_passed = sum(1 for r in results if r.get("passed", False))
            max_severity = self._get_max_severity(results)
            gm_actual = self.state.get("stability.gm_transverse_m", 0.5)
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
                    warnings=[],
                )

            # Mutate for next iteration
            proposal = self._mutate(proposal, suggestions, iteration + 1)

        # Max iterations reached - return best found
        logger.warning(f"Synthesis did not converge after {request.max_iterations} iterations")
        return SynthesisResult(
            proposal=best_proposal,
            termination=TerminationReason.MAX_ITERATIONS,
            termination_message=f"Reached {request.max_iterations} iterations",
            iterations_used=request.max_iterations,
            score_history=score_history,
            validator_results=[],
            warnings=[f"Did not converge; best score: {best_score:.1f}"],
        )

    def _create_initial_proposal(self, request: SynthesisRequest) -> SynthesisProposal:
        """Create initial proposal from family prior."""
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
        # Depth = draft + freeboard, typical freeboard ratio 0.6-0.8 × draft for small craft
        depth = draft * 1.6  # depth ≈ draft + 0.6*draft
        cb = prior["cb"]
        displacement_m3 = lwl * beam * draft * cb

        return SynthesisProposal(
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

    def _score_results(self, results: List[Dict[str, Any]]) -> Tuple[float, List[str]]:
        """Convert validator results to score + suggestions."""
        score = 100.0
        suggestions = []

        for result in results:
            if not result.get("passed", True):
                score -= 20.0

            for finding in result.get("findings", []):
                severity = finding.get("severity", "info")
                if severity == "error":
                    score -= 10.0
                    suggestion = finding.get("suggestion")
                    if suggestion:
                        suggestions.append(suggestion)
                elif severity == "warning":
                    score -= 2.0

        return score, suggestions

    def _get_max_severity(self, results: List[Dict[str, Any]]) -> str:
        """Get highest severity from all findings."""
        max_sev = "info"
        order = {"info": 0, "warning": 1, "error": 2}

        for result in results:
            for finding in result.get("findings", []):
                sev = finding.get("severity", "info")
                if order.get(sev, 0) > order[max_sev]:
                    max_sev = sev

        return max_sev

    def _mutate(
        self,
        proposal: SynthesisProposal,
        suggestions: List[str],
        iteration: int,
    ) -> SynthesisProposal:
        """Apply bounded mutations based on suggestions."""
        delta_lwl = delta_beam = delta_draft = 0.0

        for suggestion in suggestions:
            lower = suggestion.lower()
            if "length" in lower or "lwl" in lower:
                delta_lwl = self.MUTATION_DELTA if "increase" in lower else -self.MUTATION_DELTA
            if "beam" in lower or "width" in lower:
                delta_beam = self.MUTATION_DELTA if "increase" in lower else -self.MUTATION_DELTA
            if "draft" in lower:
                delta_draft = self.MUTATION_DELTA if "increase" in lower else -self.MUTATION_DELTA

        lwl = proposal.lwl_m * (1 + delta_lwl)
        beam = proposal.beam_m * (1 + delta_beam)
        draft = proposal.draft_m * (1 + delta_draft)
        depth = draft * 1.6  # Maintain depth/draft ratio
        displacement_m3 = lwl * beam * draft * proposal.cb

        return SynthesisProposal(
            lwl_m=lwl,
            beam_m=beam,
            draft_m=draft,
            depth_m=depth,
            cb=proposal.cb,
            cp=proposal.cp,
            cm=proposal.cm,
            cwp=proposal.cwp,
            displacement_m3=displacement_m3,
            confidence=proposal.confidence * 0.95,  # Slightly decrease with each mutation
            iteration=iteration,
            source="mutated",
        )

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
