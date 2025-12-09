"""
outfitting/validator.py - Outfitting system validator
ALPHA OWNS THIS FILE.

Section 31: Outfitting & Accommodation
"""

from typing import Dict, Any
from ..core.state_manager import StateManager
from .generator import OutfittingGenerator


class OutfittingValidator:
    """Validator for outfitting system - v1.1."""

    validator_id = "outfitting/accommodation"
    phase = "outfitting"
    priority = 310

    reads = [
        "hull.loa",
        "hull.beam",
        "mission.crew_berthed",
        "mission.passengers",
    ]

    writes = [
        "outfitting.system",
        "outfitting.total_accommodation_area_m2",
        "outfitting.total_berths",
        "outfitting.total_heads",
        "outfitting.num_spaces",
        "outfitting.furniture_weight_kg",
        "outfitting.fixture_weight_kg",
        "outfitting.total_weight_kg",
    ]

    def validate(self, state: StateManager) -> Dict[str, Any]:
        errors = []
        warnings = []

        generator = OutfittingGenerator(state)
        system = generator.generate()

        crew = state.get("mission.crew_berthed", 5)
        if system.total_berths < crew:
            errors.append(f"Berths {system.total_berths} < crew {crew}")

        total_persons = crew + state.get("mission.passengers", 0)
        min_heads = max(1, total_persons // 8)
        if system.total_heads < min_heads:
            warnings.append(f"Heads {system.total_heads} < recommended {min_heads}")

        state.set("outfitting.system", system.to_dict(), self.validator_id)
        state.set("outfitting.total_accommodation_area_m2", system.total_area_m2, self.validator_id)
        state.set("outfitting.total_berths", system.total_berths, self.validator_id)
        state.set("outfitting.total_heads", system.total_heads, self.validator_id)
        state.set("outfitting.num_spaces", len(system.spaces), self.validator_id)
        state.set("outfitting.furniture_weight_kg", system.furniture_weight_kg, self.validator_id)
        state.set("outfitting.fixture_weight_kg", system.fixture_weight_kg, self.validator_id)
        state.set("outfitting.total_weight_kg", system.total_weight_kg, self.validator_id)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "spaces": len(system.spaces),
                "total_area_m2": system.total_area_m2,
                "total_berths": system.total_berths,
                "total_weight_kg": system.total_weight_kg,
            },
        }
