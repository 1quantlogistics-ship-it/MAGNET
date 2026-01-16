"""
MAGNET Hull Analysis

Read-only kernel analysis for hull proportions and regime classification.

v1.2: TASK-002 - Refactored to use geometry-derived analysis
v1.1: Deprecated family-based usage (TASK-003)
v1.0: Initial implementation (Phase 5)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
import logging
import math
import warnings

from .priors.geometry_defaults import (
    get_defaults_from_froude,
    get_defaults_from_dimensions,
)

from magnet.core.constants import (
    FN_DISPLACEMENT_MAX,
    FN_SEMI_DISPLACEMENT_MAX,
    GRAVITY_M_S2,
    KNOTS_TO_MS,
)

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger(__name__)


# =============================================================================
# GEOMETRY-DERIVED ANALYSIS (TASK-002 COMPLIANT)
# =============================================================================

def calculate_froude_geometry(speed_kts: float, lwl_m: float) -> float:
    """Calculate Froude number from speed and waterline length."""
    if lwl_m <= 0:
        return 0.0
    speed_ms = speed_kts * KNOTS_TO_MS
    return speed_ms / math.sqrt(GRAVITY_M_S2 * lwl_m)


def classify_regime_geometry(froude: float) -> str:
    """Classify operating regime from Froude number."""
    if froude < FN_DISPLACEMENT_MAX:
        return "displacement"
    if froude < FN_SEMI_DISPLACEMENT_MAX:
        return "semi_displacement"
    return "planing"


def recommend_regime_defaults(speed_kts: float, lwl_m: float) -> Tuple[Dict[str, Any], str]:
    """
    Recommend hull parameters based on physics (geometry-derived).
    
    Returns (defaults_dict, rationale_string).
    """
    froude = calculate_froude_geometry(speed_kts, lwl_m)
    regime = classify_regime_geometry(froude)
    defaults = get_defaults_from_froude(froude)
    
    rationale = f"Fn={froude:.2f} → {regime} regime"
    return defaults, rationale


def recommend_family(
    speed_kts: float,
    lwl_estimate: float = 30.0,
    vessel_type: Optional[str] = None,
) -> Tuple["HullFamily", str]:
    """
    DEPRECATED: Recommend HullFamily based on Froude number.
    
    This is a compatibility shim for legacy code. New code should use
    recommend_regime_defaults() instead.
    
    Returns (HullFamily, rationale_string).
    """
    warnings.warn(
        "recommend_family() is deprecated. Use recommend_regime_defaults() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    
    from .priors.hull_families import HullFamily
    
    froude = calculate_froude_geometry(speed_kts, lwl_estimate)
    regime = classify_regime_geometry(froude)
    
    # Map regime to HullFamily for backward compatibility
    family_map = {
        "displacement": HullFamily.DISPLACEMENT,
        "semi_displacement": HullFamily.SEMI_DISPLACEMENT,
        "planing": HullFamily.PLANING,
    }
    
    hull_family = family_map.get(regime, HullFamily.SEMI_DISPLACEMENT)
    rationale = f"Fn={froude:.2f} → {regime} → {hull_family.value}"
    
    return hull_family, rationale


class HullAnalyzer:
    """
    Read-only hull analysis (geometry-derived).
    
    Provides structured proportion checks and regime classification
    for QUERY actions. Does NOT mutate state.
    """

    def __init__(self, state_manager: "StateManager"):
        self._sm = state_manager

    def analyze_proportions_geometry(self) -> Dict[str, Any]:
        """
        TASK-002: Check current hull against geometry-derived optimal values.
        
        This is the PREFERRED analysis method - uses physics instead of categorical types.
        
        Returns structured issues and suggested fixes that can be
        converted to SET/INCREASE/DECREASE actions by the LLM.
        """
        # Get current values
        loa = float(self._sm.get("hull.loa") or self._sm.get("hull.lwl") or 30)
        lwl = float(self._sm.get("hull.lwl") or loa * 0.95)
        beam = float(self._sm.get("hull.beam") or 8)
        draft = float(self._sm.get("hull.draft") or 2)
        depth = float(self._sm.get("hull.depth") or 4)
        speed = float(self._sm.get("mission.max_speed_kts") or 25)

        cb = self._sm.get("hull.cb")
        cp = self._sm.get("hull.cp")
        cm = self._sm.get("hull.cm")

        # Get physics-derived optimal values
        froude = calculate_froude_geometry(speed, lwl)
        regime = classify_regime_geometry(froude)
        optimal = get_defaults_from_froude(froude)

        # Calculate actual ratios
        lb_ratio = lwl / beam if beam > 0 else 0
        bt_ratio = beam / draft if draft > 0 else 0
        dd_ratio = depth / draft if draft > 0 else 0

        # Get optimal bounds from physics (±20% of optimal)
        optimal_lb = optimal.get("lwl_beam", 5.0)
        optimal_bt = optimal.get("beam_draft", 2.5)
        optimal_cb = optimal.get("cb", 0.5)
        optimal_dd = optimal.get("depth_draft_ratio", 1.5)

        issues: List[Dict[str, Any]] = []
        suggested_fixes: List[Dict[str, Any]] = []

        # Check L/B ratio
        lb_min, lb_max = optimal_lb * 0.8, optimal_lb * 1.2
        if lb_ratio < lb_min:
            issues.append({
                "parameter": "L/B ratio",
                "current": round(lb_ratio, 2),
                "optimal_range": (round(lb_min, 2), round(lb_max, 2)),
                "severity": "warning",
                "message": f"L/B ratio {lb_ratio:.2f} is low for {regime} regime (optimal: {optimal_lb:.1f})",
            })
            suggested_fixes.append({
                "action": "INCREASE",
                "parameter": "hull.lwl",
                "rationale": "Increase length for better L/B ratio",
            })
        elif lb_ratio > lb_max:
            issues.append({
                "parameter": "L/B ratio",
                "current": round(lb_ratio, 2),
                "optimal_range": (round(lb_min, 2), round(lb_max, 2)),
                "severity": "warning",
                "message": f"L/B ratio {lb_ratio:.2f} is high for {regime} regime (optimal: {optimal_lb:.1f})",
            })
            suggested_fixes.append({
                "action": "INCREASE",
                "parameter": "hull.beam",
                "rationale": "Increase beam for better L/B ratio",
            })

        # Check B/T ratio
        bt_min, bt_max = optimal_bt * 0.8, optimal_bt * 1.2
        if bt_ratio < bt_min:
            issues.append({
                "parameter": "B/T ratio",
                "current": round(bt_ratio, 2),
                "optimal_range": (round(bt_min, 2), round(bt_max, 2)),
                "severity": "warning",
                "message": f"B/T ratio {bt_ratio:.2f} is low for {regime} regime",
            })
        elif bt_ratio > bt_max:
            issues.append({
                "parameter": "B/T ratio",
                "current": round(bt_ratio, 2),
                "optimal_range": (round(bt_min, 2), round(bt_max, 2)),
                "severity": "warning",
                "message": f"B/T ratio {bt_ratio:.2f} is high for {regime} regime",
            })

        # Check Cb
        if cb is not None:
            cb_min, cb_max = optimal_cb * 0.85, optimal_cb * 1.15
            if cb < cb_min:
                issues.append({
                    "parameter": "Cb",
                    "current": round(cb, 3),
                    "optimal_range": (round(cb_min, 3), round(cb_max, 3)),
                    "severity": "info",
                    "message": f"Cb {cb:.3f} is fine for {regime} regime",
                })
            elif cb > cb_max:
                issues.append({
                    "parameter": "Cb",
                    "current": round(cb, 3),
                    "optimal_range": (round(cb_min, 3), round(cb_max, 3)),
                    "severity": "warning",
                    "message": f"Cb {cb:.3f} is high for {regime} regime",
                })

        return {
            "froude_number": round(froude, 3),
            "regime": regime,
            "optimal_values": optimal,
            "current_ratios": {
                "L/B": round(lb_ratio, 2),
                "B/T": round(bt_ratio, 2),
                "D/T": round(dd_ratio, 2),
            },
            "issues": issues,
            "suggested_fixes": suggested_fixes,
            "analysis_method": "geometry_derived",
        }

    def analyze_proportions(self) -> Dict[str, Any]:
        """Backward-compatible wrapper for analyze_proportions_geometry()."""
        warnings.warn(
            "analyze_proportions() is deprecated. Use analyze_proportions_geometry().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.analyze_proportions_geometry()

    def analyze_regime(self) -> Dict[str, Any]:
        """
        Geometry-derived regime analysis (no enumeration).

        Returns regime classification and physics-derived defaults.
        """
        speed = float(self._sm.get("mission.max_speed_kts") or 25)
        loa = float(self._sm.get("hull.loa") or self._sm.get("hull.lwl") or 30)
        lwl = float(self._sm.get("hull.lwl") or loa * 0.95)

        froude = calculate_froude_geometry(speed, lwl)
        regime = classify_regime_geometry(froude)
        defaults = get_defaults_from_froude(froude)

        return {
            "speed_kts": speed,
            "lwl_m": round(lwl, 2),
            "froude": round(froude, 3),
            "regime": regime,
            "regime_description": {
                "displacement": "Fn < 0.4 — buoyancy-dominant",
                "semi_displacement": "0.4 ≤ Fn < 0.7 — transition, partial dynamic lift",
                "planing": "Fn ≥ 0.7 — dynamic lift dominant",
            }.get(regime, "unknown"),
            "recommended_defaults": defaults,
        }
