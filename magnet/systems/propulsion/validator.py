"""
systems/propulsion/validator.py - Propulsion system validator
ALPHA OWNS THIS FILE.

Section 26: Propulsion System
"""

from typing import Dict, Any

from magnet.core.state_manager import StateManager
from .generator import PropulsionSystemGenerator


class PropulsionValidator:
    """Validator for propulsion system."""

    validator_id = "systems/propulsion"
    phase = "propulsion"
    priority = 260

    reads = [
        "propulsion.required_power_kw",
        "propulsion.propulsion_type",
        "propulsion.num_engines",
        "mission.max_speed_kts",
        "weight.displacement_mt",
        "hull.lwl",
    ]

    writes = [
        "propulsion.system",
        "propulsion.propulsion_type",
        "propulsion.num_engines",
        "propulsion.num_shafts",
        "propulsion.installed_power_kw",
        "propulsion.service_power_kw",
        "propulsion.fuel_rate_max_l_hr",      # v1.1 added
        "propulsion.fuel_rate_cruise_l_hr",
        "propulsion.total_weight_kg",
    ]

    def validate(self, state: StateManager) -> Dict[str, Any]:
        errors = []
        warnings = []

        generator = PropulsionSystemGenerator(state)
        system = generator.generate()

        # Validate engines selected
        if len(system.engines) == 0:
            errors.append("No engines selected")

        # Validate power margin
        required = state.get("propulsion.required_power_kw", 0)
        if required > 0:
            margin = (system.total_installed_power_kw - required) / required
            if margin < 0.10:
                warnings.append(f"Low power margin: {margin*100:.1f}%")
            elif margin > 0.50:
                warnings.append(f"High power margin: {margin*100:.1f}% - may be oversized")

        # Write ALL fields to state (v1.1 expanded) - Hole #7 Fix: Use .set()
        source = "systems/propulsion"
        state.set("propulsion.system", system.to_dict(), source)
        state.set("propulsion.propulsion_type", system.propulsor_type, source)
        state.set("propulsion.num_engines", system.num_engines, source)
        state.set("propulsion.num_shafts", system.num_shafts, source)
        state.set("propulsion.installed_power_kw", system.total_installed_power_kw, source)
        state.set("propulsion.service_power_kw", system.total_service_power_kw, source)

        # v1.1 FIX: Write BOTH fuel rates
        state.set("propulsion.fuel_rate_max_l_hr", system.fuel_rate_max_l_hr, source)
        state.set("propulsion.fuel_rate_cruise_l_hr", system.fuel_rate_cruise_l_hr, source)

        state.set("propulsion.total_weight_kg", system.total_propulsion_weight_kg, source)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "num_engines": system.num_engines,
                "total_power_kw": system.total_installed_power_kw,
                "propulsor_type": system.propulsor_type,
                "fuel_rate_max_l_hr": system.fuel_rate_max_l_hr,
                "fuel_rate_cruise_l_hr": system.fuel_rate_cruise_l_hr,
            },
        }
