"""
Geometry-Derived Defaults for Hull Synthesis

TASK-003: This module provides geometry-derived defaults to replace
family-based enumeration in synthesis.

The key insight: hull form parameters can be derived from physics
(Froude number, L/B ratio, displacement) rather than categorical
vessel types.

Reference: GOLDEN_PATH_IMPLEMENTATION_GUIDE.md
"""

from typing import Any, Dict, Optional, Tuple
import math

from magnet.core.constants import (
    FN_DISPLACEMENT_MAX,
    FN_SEMI_DISPLACEMENT_MAX,
    SEAWATER_DENSITY_KG_M3,
)


# =============================================================================
# PHYSICS-DERIVED DEFAULTS
# =============================================================================

def get_defaults_from_froude(froude_number: float) -> Dict[str, Any]:
    """
    Get hull form defaults based on Froude number.
    
    This is the GENERATIVE approach: continuous functions of physics,
    not categorical lookups.
    
    Args:
        froude_number: Design Froude number (V / sqrt(g * L))
    
    Returns:
        Dictionary of hull form parameters
    """
    fn = max(0.0, float(froude_number))
    
    # Continuous interpolation based on Froude number
    # These are empirical relationships, not categorical lookups
    
    if fn < FN_DISPLACEMENT_MAX:
        # Displacement regime: fuller forms, lower deadrise
        t = fn / FN_DISPLACEMENT_MAX  # 0 to 1 within regime
        cb = 0.55 + (1 - t) * 0.15  # 0.55 to 0.70
        deadrise = 5.0 + t * 10.0   # 5 to 15 degrees
        lb_ratio = 5.0 + t * 1.0    # 5.0 to 6.0
        
    elif fn < FN_SEMI_DISPLACEMENT_MAX:
        # Semi-displacement: transitional
        t = (fn - FN_DISPLACEMENT_MAX) / (FN_SEMI_DISPLACEMENT_MAX - FN_DISPLACEMENT_MAX)
        cb = 0.55 - t * 0.10  # 0.55 to 0.45
        deadrise = 15.0 + t * 5.0  # 15 to 20 degrees
        lb_ratio = 5.5 + t * 0.5   # 5.5 to 6.0
        
    else:
        # Planing regime: finer forms, higher deadrise
        t = min(1.0, (fn - FN_SEMI_DISPLACEMENT_MAX) / 0.5)  # Saturates at Fn=1.2
        cb = 0.45 - t * 0.10  # 0.45 to 0.35
        deadrise = 20.0 + t * 5.0  # 20 to 25 degrees
        lb_ratio = 5.5 + t * 1.0   # 5.5 to 6.5
    
    return {
        "cb": round(cb, 3),
        "cp": round(cb + 0.15, 3),  # Cp typically ~Cb + 0.15
        "cm": round(0.85 - fn * 0.1, 3),  # Cm decreases with speed
        "cwp": round(0.70 + fn * 0.05, 3),  # Cwp increases slightly
        "deadrise_deg": round(deadrise, 1),
        "lwl_beam": round(lb_ratio, 2),
        "beam_draft": round(3.0 + fn * 0.5, 2),  # B/T increases with speed
        "depth_draft_ratio": round(1.4 + fn * 0.2, 2),
    }


def get_defaults_from_dimensions(
    loa_m: float,
    speed_kts: float,
) -> Dict[str, Any]:
    """
    Get hull form defaults from principal dimensions and speed.
    
    Args:
        loa_m: Length overall in meters
        speed_kts: Design speed in knots
    
    Returns:
        Dictionary of hull form parameters
    """
    # Estimate LWL from LOA
    lwl_m = loa_m * 0.95
    
    # Calculate Froude number
    speed_ms = speed_kts * 0.514444
    g = 9.81
    fn = speed_ms / math.sqrt(g * lwl_m) if lwl_m > 0 else 0.0
    
    # Get Froude-based defaults
    defaults = get_defaults_from_froude(fn)
    
    # Add dimension-derived values
    defaults["lwl_m"] = round(lwl_m, 2)
    defaults["froude_number"] = round(fn, 3)
    
    # Estimate beam from L/B ratio
    lb_ratio = defaults["lwl_beam"]
    beam_m = lwl_m / lb_ratio
    defaults["beam_m"] = round(beam_m, 2)
    
    # Estimate draft from B/T ratio
    bt_ratio = defaults["beam_draft"]
    draft_m = beam_m / bt_ratio
    defaults["draft_m"] = round(draft_m, 2)
    
    # Estimate depth from depth/draft ratio
    depth_draft = defaults["depth_draft_ratio"]
    depth_m = draft_m * depth_draft
    defaults["depth_m"] = round(depth_m, 2)
    
    return defaults


def estimate_lightship_kg(loa_m: float, froude_number: float = 0.5) -> float:
    """
    Estimate lightship weight from LOA using physics-based scaling.
    
    Uses an empirical power law: lightship ∝ LOA^2.7
    The coefficient varies with Froude number (lighter for faster vessels).
    
    Args:
        loa_m: Length overall in meters
        froude_number: Design Froude number (affects structural weight)
    
    Returns:
        Lightship weight in kg
    """
    if loa_m <= 0:
        return 0.0
    
    # Base coefficient varies with Froude (lighter structures for faster boats)
    # This replaces the family-based LIGHTSHIP_K_TONNES dictionary
    fn = max(0.0, min(1.5, float(froude_number)))
    k_tonnes = 0.020 - fn * 0.005  # 0.020 at Fn=0, 0.0125 at Fn=1.5
    k_tonnes = max(0.010, k_tonnes)  # Floor at 0.010
    
    exponent = 2.7
    lightship_tonnes = k_tonnes * (loa_m ** exponent)
    
    return max(0.0, lightship_tonnes * 1000.0)


def get_displacement_bounds(loa_m: float, froude_number: float = 0.5) -> Tuple[float, float]:
    """
    Get reasonable displacement bounds from LOA and Froude number.
    
    Args:
        loa_m: Length overall in meters
        froude_number: Design Froude number
    
    Returns:
        (min_displacement_m3, max_displacement_m3)
    """
    if loa_m <= 0:
        return (5.0, 100.0)
    
    # Reference displacement scales with LOA^3
    ref_disp = 0.1 * (loa_m ** 3)  # Very rough approximation
    
    # Faster vessels are lighter relative to size
    fn = max(0.0, min(1.5, float(froude_number)))
    scale = 1.0 - fn * 0.3  # 1.0 at Fn=0, 0.55 at Fn=1.5
    
    center = ref_disp * scale
    
    # Bounds are ±50% of center estimate
    return (max(5.0, center * 0.5), center * 1.5)


# =============================================================================
# MIGRATION HELPERS
# =============================================================================

def migrate_from_family(family_name: str, speed_kts: float, loa_m: Optional[float] = None) -> Dict[str, Any]:
    """
    Migration helper: convert legacy request to geometry-based.
    
    This exists only to support older call sites; new code should call
    physics-derived defaults directly.
    
    Args:
        family_name: Legacy family name (e.g., "patrol", "workboat")
        speed_kts: Design speed in knots
        loa_m: Optional LOA (if not provided, estimated from speed)
    
    Returns:
        Dictionary of hull form parameters (geometry-derived)
    """
    # If LOA not provided, estimate from speed using typical L/V relationship
    if loa_m is None:
        # Rough estimate: LOA ≈ (speed_kts / 2)^2 for typical fast craft
        loa_m = max(10.0, (speed_kts / 2.0) ** 2)
        loa_m = min(100.0, loa_m)  # Cap at 100m
    
    return get_defaults_from_dimensions(loa_m, speed_kts)
