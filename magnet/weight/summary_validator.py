"""
weight/summary_validator.py - Weight summary validator
ALPHA OWNS THIS FILE.

Section 36: Weight Summary & Centers - v1.1
"""

from typing import Dict, Any
from ..core.state_manager import StateManager
from .summary_generator import WeightSummaryGenerator


class WeightSummaryValidator:
    """Validator for weight summary - v1.1."""

    validator_id = "weight/summary"
    phase = "weight_stability"
    priority = 360

    reads = [
        "hull.loa", "hull.lwl",
        "hull.lcb_percent_lwl",  # v1.1 FIX
        "structure.hull_weight_kg",
        "propulsion.total_weight_kg",
        "electrical.total_weight_kg",
        "hvac.total_weight_kg",
        "fuel.system_weight_kg",
        "fuel.fuel_weight_full_kg",  # v1.1 FIX
        "fuel.total_fuel_m3",
        "safety.total_weight_kg",
        "outfitting.total_weight_kg",
        "deck_equipment.total_weight_kg",
        "coatings.total_weight_kg",
        "mission.crew_berthed",
        "mission.passengers",
    ]

    writes = [
        "weight.summary",
        "weight.lightship_kg",
        "weight.lightship_lcg_m",
        "weight.lightship_vcg_m",
        "weight.full_load_displacement_kg",
        "weight.full_load_displacement_mt",
        "weight.loading_conditions",
        "weight.weight_margin_applied_percent",
    ]

    def validate(self, state: StateManager) -> Dict[str, Any]:
        errors = []
        warnings = []

        generator = WeightSummaryGenerator(state)
        summary = generator.generate()

        if abs(summary.weight_difference_percent) > 5:
            warnings.append(f"Weight differs from target by {summary.weight_difference_percent:.1f}%")

        if abs(summary.weight_difference_percent) > 15:
            errors.append(f"Weight differs from target by {summary.weight_difference_percent:.1f}% - exceeds 15% tolerance")

        state.set("weight.summary", summary.to_dict(), self.validator_id)
        state.set("weight.lightship_kg", summary.lightship_with_margin_kg, self.validator_id)
        state.set("weight.lightship_lcg_m", summary.lightship_lcg_m, self.validator_id)
        state.set("weight.lightship_vcg_m", summary.lightship_vcg_m, self.validator_id)

        full_cond = next((c for c in summary.conditions if c.condition_id == "FULL"), None)
        if full_cond:
            state.set("weight.full_load_displacement_kg", full_cond.displacement_kg, self.validator_id)
            state.set("weight.full_load_displacement_mt", full_cond.displacement_mt, self.validator_id)

        state.set("weight.loading_conditions", [c.to_dict() for c in summary.conditions], self.validator_id)
        state.set("weight.weight_margin_applied_percent", summary.margins.design_margin_percent, self.validator_id)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "lightship_kg": summary.lightship_with_margin_kg,
                "num_conditions": len(summary.conditions),
                "weight_difference_percent": summary.weight_difference_percent,
            },
        }
