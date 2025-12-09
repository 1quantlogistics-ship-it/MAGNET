"""
performance/predictor_validator.py - Performance validator
BRAVO OWNS THIS FILE.

Section 39: Performance Prediction - v1.1
"""

from typing import Dict, Any, TYPE_CHECKING

from .predictor import PerformancePredictor

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class PerformanceValidator:
    """Validator for performance prediction - v1.1."""

    validator_id = "performance/prediction"
    phase = "propulsion"
    priority = 390

    reads = [
        "hull.loa", "hull.lwl", "hull.beam", "hull.draft",
        "hull.wetted_surface_m2",
        "weight.full_load_displacement_mt",
        "weight.displacement_mt",
        "mission.cruise_speed_kts",    # v1.1: canonical
        "mission.max_speed_kts",        # v1.1: canonical
        "mission.cruise_speed_knots",   # v1.1: alias fallback
        "mission.max_speed_knots",      # v1.1: alias fallback
        "propulsion.propulsion_type",
        "propulsion.installed_power_kw",  # v1.1 FIX: standardized
    ]

    writes = [
        "performance.speed_power_curve",
        "performance.cruise_power_kw",
        "performance.max_power_kw",
        "performance.propulsive_efficiency",
        "performance.power_margin_percent",
    ]

    def validate(self, state: 'StateManager') -> Dict[str, Any]:
        errors = []
        warnings = []

        predictor = PerformancePredictor(state)
        results = predictor.predict()

        # v1.1 FIX: Use standardized field name
        installed = state.get("propulsion.installed_power_kw", 0)
        if installed is None:
            installed = 0
        required = results["max_power_with_margin_kw"]

        if installed > 0 and installed < required:
            errors.append(f"Installed power {installed:.0f} kW < required {required:.0f} kW")

        margin = (installed - required) / required * 100 if required > 0 else 0

        state.set("performance.speed_power_curve", results["curve"])
        state.set("performance.cruise_power_kw", results["cruise_power_kw"])
        state.set("performance.max_power_kw", results["max_power_kw"])
        state.set("performance.propulsive_efficiency", results["efficiency"])
        state.set("performance.power_margin_percent", margin)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "cruise_power_kw": results["cruise_power_kw"],
                "max_power_kw": results["max_power_kw"],
                "installed_kw": installed,
                "margin_percent": margin,
            },
        }
