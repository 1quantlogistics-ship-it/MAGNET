"""
outfitting/deck_equipment_generator.py - Deck equipment generation
ALPHA OWNS THIS FILE.

Section 32: Deck Equipment
"""

from typing import List
from ..core.state_manager import StateManager
from .deck_equipment import (
    Anchor, Chain, Windlass, MooringEquipment, Davit,
    DeckEquipmentSystem,
)


class DeckEquipmentGenerator:
    """Generate deck equipment from requirements."""

    def __init__(self, state: StateManager):
        self.state = state

    def generate(self) -> DeckEquipmentSystem:
        """Generate complete deck equipment system."""

        loa = self.state.get("hull.loa", 25)
        displacement_mt = self.state.get("hull.displacement_mt", 100)
        max_depth = self.state.get("mission.max_anchoring_depth_m", 50)
        passengers = self.state.get("mission.passengers", 0)

        # v1.1 FIX: Use metadata.design_id
        system = DeckEquipmentSystem(
            system_id=f"DECK-{self.state.get('metadata.design_id', 'UNKNOWN')}",
        )

        # Size anchor using Lloyd's rule
        system.anchor = Anchor.size_for_vessel(loa, displacement_mt)

        # Size chain for anchor
        system.chain = Chain.size_for_anchor(system.anchor.weight_kg, max_depth)

        # Size windlass for anchor + 30m chain
        chain_30m_weight = system.chain.weight_per_m_kg * 30
        system.windlass = Windlass.size_for_anchor(
            system.anchor.weight_kg,
            system.chain.diameter_mm,
            chain_30m_weight,
        )

        # Generate mooring equipment
        system.mooring = MooringEquipment.generate_for_vessel(loa, displacement_mt)

        # Generate davits
        system.davits = self._generate_davits(passengers)

        return system

    def _generate_davits(self, passengers: int) -> List[Davit]:
        """Generate davits based on requirements."""
        davits = []

        # Stores davit always required
        davits.append(Davit.for_stores())

        # Rescue boat davit if passengers > 12
        if passengers > 12:
            davits.append(Davit.for_rescue_boat())

        return davits
