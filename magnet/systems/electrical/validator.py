"""
systems/electrical/validator.py - Electrical system validator
ALPHA OWNS THIS FILE.

Section 27: Electrical System
"""

from typing import Dict, Any

from magnet.core.state_manager import StateManager
from .generator import ElectricalSystemGenerator


class ElectricalValidator:
    """Validator for electrical system."""

    validator_id = "systems/electrical"
    phase = "systems"
    priority = 270

    reads = [
        "hull.loa",
        "mission.crew_berthed",
        "mission.passengers",
        "hvac.total_power_kw",
    ]

    writes = [
        "electrical.system",
        "electrical.total_connected_kw",
        "electrical.total_demand_kw",
        "electrical.total_generation_kw",
        "electrical.num_generators",
        "electrical.total_battery_kwh",
        "electrical.shore_power_kw",
        "electrical.total_weight_kg",
    ]

    def validate(self, state: StateManager) -> Dict[str, Any]:
        errors = []
        warnings = []

        generator = ElectricalSystemGenerator(state)
        system = generator.generate()

        if system.total_generation_kw < system.total_demand_load_kw:
            errors.append("Generation capacity less than demand load")
        elif system.total_generation_kw < system.total_demand_load_kw * 1.1:
            warnings.append("Low generation margin (<10%)")

        state.write("electrical.system", system.to_dict(), self.validator_id, "Electrical system")
        state.write("electrical.total_connected_kw", system.total_connected_load_kw, self.validator_id, "Connected load")
        state.write("electrical.total_demand_kw", system.total_demand_load_kw, self.validator_id, "Demand load")
        state.write("electrical.total_generation_kw", system.total_generation_kw, self.validator_id, "Total generation")
        state.write("electrical.num_generators", len(system.generators), self.validator_id, "Number of generators")
        state.write("electrical.total_battery_kwh", system.total_battery_kwh, self.validator_id, "Battery capacity")
        state.write("electrical.shore_power_kw", system.shore_power_kw, self.validator_id, "Shore power")
        state.write("electrical.total_weight_kg", system.total_weight_kg, self.validator_id, "Electrical weight")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "num_generators": len(system.generators),
                "total_generation_kw": system.total_generation_kw,
                "total_demand_kw": system.total_demand_load_kw,
                "total_battery_kwh": system.total_battery_kwh,
            },
        }
