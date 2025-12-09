"""
production/coatings_validator.py - Coating plan validator
ALPHA OWNS THIS FILE.

Section 33: Coatings & Corrosion Protection
"""

from typing import Dict, Any
from ..core.state_manager import StateManager
from .coatings_generator import CoatingPlanGenerator


class CoatingsValidator:
    """Validator for coating system - v1.1."""

    validator_id = "production/coatings"
    phase = "production"
    priority = 330

    reads = [
        "hull.loa",
        "hull.beam",
        "hull.draft",
        "hull.depth",
        "hull.wetted_surface_m2",
    ]

    writes = [
        "coatings.plan",
        "coatings.total_area_m2",
        "coatings.total_paint_volume_l",
        "coatings.num_anodes",
        "coatings.total_anode_weight_kg",
    ]

    def validate(self, state: StateManager) -> Dict[str, Any]:
        errors = []
        warnings = []

        generator = CoatingPlanGenerator(state)
        plan = generator.generate()

        # Validate paint coverage
        total_area = plan.total_area_m2
        if total_area < 100:
            warnings.append(f"Total coating area {total_area} m² seems low")

        # Validate anode weight
        wetted_area = sum(
            a.area_m2 for a in plan.areas
            if a.zone.value in ["underwater", "waterline"]
        )
        min_anode_weight = wetted_area * 0.3 * 3  # 3-year life
        if plan.cathodic_protection.total_anode_weight_kg < min_anode_weight * 0.9:
            warnings.append(
                f"Anode weight {plan.cathodic_protection.total_anode_weight_kg} kg "
                f"may be insufficient (recommended {min_anode_weight:.0f} kg)"
            )

        # Write to state
        state.set("coatings.plan", plan.to_dict(), self.validator_id)
        state.set("coatings.total_area_m2", plan.total_area_m2, self.validator_id)
        state.set("coatings.total_paint_volume_l", plan.total_paint_volume_l, self.validator_id)
        state.set("coatings.num_anodes", len(plan.cathodic_protection.anodes), self.validator_id)
        state.set("coatings.total_anode_weight_kg", plan.cathodic_protection.total_anode_weight_kg, self.validator_id)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "total_area_m2": plan.total_area_m2,
                "total_paint_volume_l": plan.total_paint_volume_l,
                "num_anodes": len(plan.cathodic_protection.anodes),
                "total_anode_weight_kg": plan.cathodic_protection.total_anode_weight_kg,
            },
        }
