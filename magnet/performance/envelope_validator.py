"""
performance/envelope_validator.py - Operational envelope validator
BRAVO OWNS THIS FILE.

Section 40: Operational Envelope - v1.1
"""

from typing import Dict, Any, TYPE_CHECKING

from .envelope_generator import EnvelopeGenerator

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class EnvelopeValidator:
    """Validator for operational envelope - v1.1."""

    validator_id = "performance/envelope"
    phase = "analysis"
    priority = 400

    reads = [
        "mission.cruise_speed_kts",
        "mission.max_speed_kts",
        "mission.cruise_speed_knots",
        "mission.max_speed_knots",
        "propulsion.fuel_rate_cruise_l_hr",
        "fuel.usable_fuel_m3",
        "fuel.range_at_cruise_nm",
        "analysis.max_sea_state",
    ]

    writes = [
        "performance.operational_envelope",
        "performance.max_operational_speed_kts",
        "performance.max_operational_sea_state",
        "performance.range_nm",
        "performance.endurance_hr",
    ]

    def validate(self, state: 'StateManager') -> Dict[str, Any]:
        errors = []
        warnings = []

        generator = EnvelopeGenerator(state)
        envelope = generator.generate()

        required_range = state.get("mission.required_range_nm", 300) or 300
        if envelope.range_at_cruise_nm < required_range:
            warnings.append(f"Range {envelope.range_at_cruise_nm:.0f} nm < required {required_range:.0f} nm")

        state.set("performance.operational_envelope", envelope.to_dict())
        state.set("performance.max_operational_speed_kts", envelope.design_speed_kts)
        state.set("performance.max_operational_sea_state", envelope.max_operational_sea_state)
        state.set("performance.range_nm", envelope.range_at_cruise_nm)
        state.set("performance.endurance_hr", envelope.endurance_at_cruise_hr)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "range_nm": envelope.range_at_cruise_nm,
                "endurance_hr": envelope.endurance_at_cruise_hr,
                "max_sea_state": envelope.max_operational_sea_state,
            },
        }
