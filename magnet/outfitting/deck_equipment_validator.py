"""
outfitting/deck_equipment_validator.py - Deck equipment validator
ALPHA OWNS THIS FILE.

Section 32: Deck Equipment
"""

from typing import Dict, Any
from ..core.state_manager import StateManager
from .deck_equipment_generator import DeckEquipmentGenerator


class DeckEquipmentValidator:
    """Validator for deck equipment - v1.1."""

    validator_id = "outfitting/deck_equipment"
    phase = "outfitting"
    priority = 320

    reads = [
        "hull.loa",
        "hull.displacement_mt",
        "mission.max_anchoring_depth_m",
        "mission.passengers",
    ]

    writes = [
        "deck_equipment.system",
        "deck_equipment.anchor_weight_kg",
        "deck_equipment.chain_length_m",
        "deck_equipment.windlass_pull_kg",
        "deck_equipment.total_weight_kg",
    ]

    def validate(self, state: StateManager) -> Dict[str, Any]:
        errors = []
        warnings = []

        generator = DeckEquipmentGenerator(state)
        system = generator.generate()

        # Validate anchor sizing
        loa = state.get("hull.loa", 25)
        min_anchor_weight = 2.0 * loa  # Minimum rule
        if system.anchor.weight_kg < min_anchor_weight:
            warnings.append(
                f"Anchor weight {system.anchor.weight_kg} kg may be undersized "
                f"(min {min_anchor_weight} kg for {loa}m LOA)"
            )

        # Validate chain length for depth
        max_depth = state.get("mission.max_anchoring_depth_m", 50)
        min_chain_length = 5 * max_depth
        if system.chain.length_m < min_chain_length:
            warnings.append(
                f"Chain length {system.chain.length_m}m may be short "
                f"(recommended {min_chain_length}m for {max_depth}m depth)"
            )

        # Write to state
        state.set("deck_equipment.system", system.to_dict(), self.validator_id)
        state.set("deck_equipment.anchor_weight_kg", system.anchor.weight_kg, self.validator_id)
        state.set("deck_equipment.chain_length_m", system.chain.length_m, self.validator_id)
        state.set("deck_equipment.windlass_pull_kg", system.windlass.rated_pull_kg, self.validator_id)
        state.set("deck_equipment.total_weight_kg", system.total_weight_kg, self.validator_id)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "anchor_weight_kg": system.anchor.weight_kg,
                "chain_length_m": system.chain.length_m,
                "windlass_pull_kg": system.windlass.rated_pull_kg,
                "total_weight_kg": system.total_weight_kg,
            },
        }
