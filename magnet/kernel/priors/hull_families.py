"""
MAGNET Hull Family Priors

Defines hull family priors for synthesis starting points.
Each family has characteristic ratios and coefficients.

v1.0: Initial implementation
v1.1: Fixed Froude numbers - previous values were for large displacement vessels,
      not appropriate for patrol/workboat/planing hulls. Reference regimes:
      - Displacement: Fn < 0.35 (tankers, cargo ships)
      - Semi-displacement: Fn 0.35-0.55 (tugs, slow workboats)
      - Semi-planing: Fn 0.55-1.0 (fast ferries, patrol boats)
      - Planing: Fn > 1.0 (high-speed craft, RIBs)
"""

from enum import Enum
from typing import Any, Dict, Optional, Tuple

from magnet.core.constants import FN_DISPLACEMENT_MAX, FN_SEMI_DISPLACEMENT_MAX

class HullFamily(Enum):
    """Hull type families for synthesis priors."""
    PATROL = "patrol"
    WORKBOAT = "workboat"
    FERRY = "ferry"
    PLANING = "planing"
    CATAMARAN = "catamaran"


# =============================================================================
# FROUDE / REGIME HELPERS (v1.5)
# =============================================================================

def calculate_froude(speed_kts: float, lwl_m: float) -> float:
    """
    Calculate Froude number: Fn = V / sqrt(g * L).

    Args:
        speed_kts: Speed in knots
        lwl_m: Waterline length in meters

    Returns:
        Froude number (dimensionless)
    """
    if not speed_kts or not lwl_m or lwl_m <= 0:
        return 0.0
    speed_ms = float(speed_kts) * 0.514444
    g = 9.81
    return float(speed_ms / (g * float(lwl_m)) ** 0.5)


def classify_regime(froude: float) -> str:
    """
    Classify operating regime from Froude number.

    Note: This is a coarse regime map used for prior biasing (not class rules).
    """
    fn = float(froude or 0.0)
    if fn < FN_DISPLACEMENT_MAX:
        return "displacement"
    if fn < FN_SEMI_DISPLACEMENT_MAX:
        return "semi_displacement"
    return "planing"


# Regime-level biasing for selected priors (v1.5)
# Keys must match f"{param}_bias" used by get_regime_adjusted_prior().
REGIME_ADJUSTMENTS: Dict[str, Dict[str, float]] = {
    "displacement": {
        "deadrise_deg_bias": -5.0,
        "deadrise_transom_deg_bias": -3.0,
        "transom_beam_ratio_bias": -0.10,
        "cb_bias": +0.03,
    },
    "semi_displacement": {
        "deadrise_deg_bias": 0.0,
        "deadrise_transom_deg_bias": 0.0,
        "transom_beam_ratio_bias": 0.0,
        "cb_bias": 0.0,
    },
    "planing": {
        "deadrise_deg_bias": +5.0,
        "deadrise_transom_deg_bias": +3.0,
        "transom_beam_ratio_bias": +0.05,
        "cb_bias": -0.03,
    },
}


def get_regime_adjusted_prior(
    family: HullFamily,
    param: str,
    froude: float,
) -> Optional[Any]:
    """
    Get a prior value/range adjusted for coarse Froude regime.

    If the base prior is a tuple(range), the bias is applied to both endpoints.
    If the base prior is a float/int, the bias is applied to the value.
    If the base prior is None or missing, returns None.
    """
    base = FAMILY_PRIORS.get(family, {}).get(param)
    if base is None:
        return None

    regime = classify_regime(froude)
    bias = REGIME_ADJUSTMENTS.get(regime, {}).get(f"{param}_bias", 0.0)

    if isinstance(base, tuple) and len(base) == 2:
        lo, hi = base
        return (lo + bias, hi + bias)
    if isinstance(base, (int, float)):
        return base + bias
    return base


# Family priors with characteristic ratios and coefficients
# These provide starting points for synthesis iteration
# v1.2: Added hard bounds to prevent unbounded Froude backsolve results
FAMILY_PRIORS: Dict[HullFamily, Dict[str, Any]] = {
    HullFamily.PATROL: {
        # Fast patrol boats: semi-planing to planing regime
        # Typical: 20-40m, 25-35 kts, hard chine or round bilge
        "lwl_beam": 5.5,           # L/B ratio
        "beam_draft": 3.0,         # B/T ratio
        "cb": 0.45,                # Block coefficient (lower for speed)
        "cp": 0.62,                # Prismatic coefficient
        "cm": 0.82,                # Midship coefficient
        "cwp": 0.72,               # Waterplane coefficient
        "froude_design": 0.90,     # Semi-planing regime (was 0.45 - wrong!)
        "gm_min_m": 0.5,           # Minimum GM requirement
        "depth_draft_ratio": 1.35, # Low freeboard for boarding ops, silhouette
        # --- Hull form (ranges) ---
        "deadrise_deg": (15.0, 25.0),
        "deadrise_transom_deg": (10.0, 18.0),
        "bow_entrance_deg": (15.0, 30.0),
        "bow_flare_deg": (10.0, 25.0),
        "stem_rake_deg": (5.0, 15.0),
        "transom_beam_ratio": (0.60, 0.90),
        "freeboard_ratio": (0.25, 0.40),   # (depth - draft) / depth
        "lcb_fraction": (0.48, 0.54),      # from FP (0=FP/bow, 1=AP/stern)
        "hull_spacing_ratio": None,        # not applicable
        # Hard bounds to prevent unbounded synthesis results
        "bounds": {
            "lwl_m": (15.0, 50.0),       # Patrol boats typically 15-50m
            "lwl_beam": (4.5, 7.0),       # L/B ratio range
            "beam_draft": (2.0, 4.0),     # B/T ratio range
            "cb": (0.35, 0.55),           # Block coefficient range
            "cp": (0.55, 0.70),           # Prismatic coefficient range
            "displacement_m3": (30.0, 500.0),  # Reasonable displacement
            # Hull form bounds (broad, family-specific tightening happens via priors above)
            "deadrise_deg": (0.0, 45.0),
            "deadrise_transom_deg": (0.0, 30.0),
            "bow_entrance_deg": (5.0, 45.0),
            "bow_flare_deg": (0.0, 45.0),
            "stem_rake_deg": (0.0, 30.0),
            "transom_beam_ratio": (0.0, 1.0),
            "lcb_fraction": (0.45, 0.58),
        },
        # Coefficient coupling constraints (v1.4)
        "coefficient_constraints": {
            "cm_min": 0.70,
            "cm_max": 0.95,
        },
    },
    HullFamily.WORKBOAT: {
        # General workboats: semi-displacement regime
        # Typical: 15-30m, 10-18 kts, round bilge, sturdy construction
        "lwl_beam": 4.5,
        "beam_draft": 2.8,
        "cb": 0.55,
        "cp": 0.68,
        "cm": 0.88,
        "cwp": 0.78,
        "froude_design": 0.45,     # Semi-displacement (was 0.30 - too slow)
        "gm_min_m": 0.5,
        "depth_draft_ratio": 1.55, # Moderate freeboard for cargo access
        # --- Hull form (ranges) ---
        "deadrise_deg": (3.0, 12.0),
        "deadrise_transom_deg": (0.0, 8.0),
        "bow_entrance_deg": (25.0, 40.0),
        "bow_flare_deg": (0.0, 15.0),
        "stem_rake_deg": (0.0, 12.0),
        "transom_beam_ratio": (0.45, 0.80),
        "freeboard_ratio": (0.25, 0.45),
        "lcb_fraction": (0.50, 0.56),
        "hull_spacing_ratio": None,
        "bounds": {
            "lwl_m": (10.0, 40.0),        # Workboats typically 10-40m
            "lwl_beam": (3.5, 5.5),
            "beam_draft": (2.0, 4.0),
            "cb": (0.45, 0.65),
            "cp": (0.60, 0.75),
            "displacement_m3": (20.0, 400.0),
            "deadrise_deg": (0.0, 30.0),
            "deadrise_transom_deg": (0.0, 25.0),
            "bow_entrance_deg": (5.0, 45.0),
            "bow_flare_deg": (0.0, 45.0),
            "stem_rake_deg": (0.0, 30.0),
            "transom_beam_ratio": (0.0, 1.0),
            "lcb_fraction": (0.45, 0.58),
        },
        "coefficient_constraints": {
            "cm_min": 0.75,
            "cm_max": 0.98,
        },
    },
    HullFamily.FERRY: {
        # Fast ferries: semi-planing regime
        # Typical: 30-80m, 25-40 kts, wave-piercing or catamaran
        "lwl_beam": 5.0,
        "beam_draft": 3.2,
        "cb": 0.55,                # Slightly higher Cb for capacity
        "cp": 0.70,
        "cm": 0.92,
        "cwp": 0.80,
        "froude_design": 0.65,     # Fast ferry regime (was 0.28 - wrong!)
        "gm_min_m": 0.75,
        "depth_draft_ratio": 1.90, # High decks for passenger headroom (2.1m min)
        # --- Hull form (ranges) ---
        "deadrise_deg": (5.0, 15.0),
        "deadrise_transom_deg": (0.0, 10.0),
        "bow_entrance_deg": (15.0, 30.0),
        "bow_flare_deg": (5.0, 20.0),
        "stem_rake_deg": (5.0, 20.0),
        "transom_beam_ratio": (0.70, 0.95),
        "freeboard_ratio": (0.30, 0.45),
        "lcb_fraction": (0.50, 0.56),
        "hull_spacing_ratio": None,
        "bounds": {
            "lwl_m": (25.0, 100.0),       # Fast ferries 25-100m
            "lwl_beam": (4.0, 7.0),
            "beam_draft": (2.5, 4.5),
            "cb": (0.45, 0.65),
            "cp": (0.60, 0.78),
            "displacement_m3": (100.0, 3000.0),
            "deadrise_deg": (0.0, 30.0),
            "deadrise_transom_deg": (0.0, 25.0),
            "bow_entrance_deg": (5.0, 45.0),
            "bow_flare_deg": (0.0, 45.0),
            "stem_rake_deg": (0.0, 30.0),
            "transom_beam_ratio": (0.0, 1.0),
            "lcb_fraction": (0.45, 0.58),
        },
        "coefficient_constraints": {
            "cm_min": 0.80,
            "cm_max": 0.98,
        },
    },
    HullFamily.PLANING: {
        # High-speed planing craft: RIBs, speedboats
        # Typical: 8-20m, 35-50+ kts, deep-V hull
        "lwl_beam": 4.0,
        "beam_draft": 5.0,
        "cb": 0.42,
        "cp": 0.60,
        "cm": 0.75,
        "cwp": 0.70,
        "froude_design": 1.2,      # Full planing regime (was 0.80 - too slow)
        "gm_min_m": 0.35,
        "depth_draft_ratio": 1.40, # Low freeboard for speed, spray deflection
        # --- Hull form (ranges) ---
        "deadrise_deg": (18.0, 30.0),
        "deadrise_transom_deg": (8.0, 18.0),
        "bow_entrance_deg": (12.0, 25.0),
        "bow_flare_deg": (10.0, 25.0),
        "stem_rake_deg": (5.0, 20.0),
        "transom_beam_ratio": (0.85, 1.00),
        "freeboard_ratio": (0.20, 0.35),
        "lcb_fraction": (0.45, 0.52),
        "hull_spacing_ratio": None,
        "bounds": {
            "lwl_m": (6.0, 25.0),         # Planing craft 6-25m
            "lwl_beam": (3.0, 5.0),
            "beam_draft": (3.5, 7.0),
            "cb": (0.30, 0.50),
            "cp": (0.50, 0.68),
            "displacement_m3": (5.0, 100.0),
            "deadrise_deg": (0.0, 45.0),
            "deadrise_transom_deg": (0.0, 30.0),
            "bow_entrance_deg": (5.0, 45.0),
            "bow_flare_deg": (0.0, 45.0),
            "stem_rake_deg": (0.0, 30.0),
            "transom_beam_ratio": (0.0, 1.0),
            "lcb_fraction": (0.40, 0.58),
        },
        "coefficient_constraints": {
            "cm_min": 0.65,
            "cm_max": 0.90,
        },
    },
    HullFamily.CATAMARAN: {
        # High-speed catamarans: fast ferries, patrol
        # Typical: 25-100m, 30-45 kts, wave-piercing demihulls
        "lwl_beam": 3.5,  # Overall L/B ratio (overall beam, not per demihull)
        "beam_draft": 3.0,
        "cb": 0.42,
        "cp": 0.62,
        "cm": 0.78,
        "cwp": 0.72,
        "froude_design": 0.75,     # High semi-planing (was 0.55 - reasonable but slow)
        "gm_min_m": 0.5,
        "depth_draft_ratio": 1.70, # Bridging structure clearance
        # --- Hull form (ranges) ---
        "deadrise_deg": (5.0, 18.0),
        "deadrise_transom_deg": (0.0, 10.0),
        "bow_entrance_deg": (10.0, 22.0),
        "bow_flare_deg": (0.0, 15.0),
        "stem_rake_deg": (5.0, 20.0),
        "transom_beam_ratio": (0.60, 0.95),
        "freeboard_ratio": (0.25, 0.45),
        "lcb_fraction": (0.48, 0.54),
        "hull_spacing_ratio": (0.80, 1.60),  # spacing / overall beam
        "bounds": {
            "lwl_m": (20.0, 120.0),       # Catamarans 20-120m
            "lwl_beam": (2.5, 5.0),        # Overall L/B ratio bounds
            "beam_draft": (2.0, 5.0),
            "cb": (0.35, 0.55),
            "cp": (0.55, 0.70),
            "displacement_m3": (50.0, 2000.0),
            "deadrise_deg": (0.0, 45.0),
            "deadrise_transom_deg": (0.0, 30.0),
            "bow_entrance_deg": (5.0, 45.0),
            "bow_flare_deg": (0.0, 45.0),
            "stem_rake_deg": (0.0, 30.0),
            "transom_beam_ratio": (0.0, 1.0),
            "lcb_fraction": (0.45, 0.58),
        },
        "coefficient_constraints": {
            "cm_min": 0.70,
            "cm_max": 0.92,
        },
    },
}


def get_family_prior(family: HullFamily) -> Dict[str, Any]:
    """
    Get prior parameters for hull family.

    Args:
        family: The hull family type

    Returns:
        Dictionary of prior parameters

    Raises:
        ValueError: If family is unknown
    """
    if family not in FAMILY_PRIORS:
        raise ValueError(f"Unknown hull family: {family}")
    return FAMILY_PRIORS[family]


def get_family_from_string(family_str: str) -> HullFamily:
    """
    Convert string to HullFamily enum.

    Args:
        family_str: Family name string (e.g., "patrol", "workboat")

    Returns:
        HullFamily enum value

    Raises:
        ValueError: If string doesn't match any family
    """
    family_str_lower = family_str.lower()
    for family in HullFamily:
        if family.value == family_str_lower:
            return family
    raise ValueError(f"Unknown hull family string: {family_str}")
