"""
MAGNET Synthesis Fallback

Fallback hull generation when synthesis fails.
ALWAYS produces a usable hull (with low confidence).

v1.0: Initial implementation
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict

from .priors.hull_families import HullFamily, get_family_prior


class FallbackMode(Enum):
    """Fallback mode used when synthesis fails."""
    ESTIMATOR_ONLY = "estimator_only"   # Use prior without validation
    REDUCED_PARAMS = "reduced_params"   # Fewer parameters, higher confidence
    MANUAL_REQUIRED = "manual_required" # Cannot proceed automatically


@dataclass
class FallbackProposal:
    """A hull proposal generated via fallback path."""
    # Principal dimensions
    lwl_m: float
    beam_m: float
    draft_m: float
    depth_m: float  # Moulded depth to main deck

    # Form coefficients
    cb: float
    cp: float
    cm: float
    cwp: float

    # Derived
    displacement_m3: float

    # Metadata
    confidence: float
    mode: FallbackMode
    reason: str

    @property
    def is_complete(self) -> bool:
        """All parameters are valid positive numbers."""
        return all(v > 0 for v in [
            self.lwl_m, self.beam_m, self.draft_m, self.depth_m,
            self.cb, self.cp, self.cm, self.cwp
        ])

    def to_state_dict(self) -> Dict[str, float]:
        """Convert to state paths for writing."""
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


def create_fallback_proposal(
    hull_family: HullFamily,
    max_speed_kts: float,
    loa_m: float = None,
    reason: str = "Synthesis failed",
) -> FallbackProposal:
    """
    Create estimator-only hull when synthesis fails.

    ALWAYS returns a usable hull (with low confidence).

    Args:
        hull_family: Target hull family
        max_speed_kts: Design speed in knots
        loa_m: Optional LOA constraint
        reason: Why fallback was triggered

    Returns:
        FallbackProposal with complete hull parameters
    """
    prior = get_family_prior(hull_family)

    # Use simple Froude-based length estimation
    speed_ms = max_speed_kts * 0.5144  # Convert to m/s
    target_fn = prior["froude_design"]

    # Fn = V / sqrt(g * L) -> L = V^2 / (Fn^2 * g)
    if loa_m:
        lwl = loa_m * 0.95  # LWL typically ~95% of LOA
    else:
        lwl = (speed_ms / target_fn) ** 2 / 9.81

    # Scale other dimensions from ratios
    beam = lwl / prior["lwl_beam"]
    draft = beam / prior["beam_draft"]
    depth = draft * 1.6  # depth ≈ draft + 0.6*draft (typical freeboard ratio)

    # Get coefficients from prior
    cb = prior["cb"]
    cp = prior["cp"]
    cm = prior["cm"]
    cwp = prior["cwp"]

    # Calculate displacement
    displacement_m3 = lwl * beam * draft * cb

    return FallbackProposal(
        lwl_m=lwl,
        beam_m=beam,
        draft_m=draft,
        depth_m=depth,
        cb=cb,
        cp=cp,
        cm=cm,
        cwp=cwp,
        displacement_m3=displacement_m3,
        confidence=0.3,  # Low confidence - estimator only
        mode=FallbackMode.ESTIMATOR_ONLY,
        reason=reason,
    )
