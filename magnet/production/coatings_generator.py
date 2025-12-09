"""
production/coatings_generator.py - Coating plan generation
ALPHA OWNS THIS FILE.

Section 33: Coatings & Corrosion Protection
"""

from typing import List
from ..core.state_manager import StateManager
from .coatings import (
    CoatingZone, ALUMINUM_COATING_SYSTEMS,
    CoatingArea, CathodicProtection, CoatingPlan,
)


class CoatingPlanGenerator:
    """Generate coating plan from requirements."""

    def __init__(self, state: StateManager):
        self.state = state

    def generate(self) -> CoatingPlan:
        """Generate complete coating plan."""

        # v1.1 FIX: Use metadata.design_id
        plan = CoatingPlan(
            plan_id=f"COAT-{self.state.get('metadata.design_id', 'UNKNOWN')}",
        )

        # v1.1 FIX: Estimate areas from hull dimensions if not in state
        areas = self._get_or_estimate_areas()
        plan.areas = self._generate_coating_areas(areas)

        # Design cathodic protection
        wetted_area = areas.get("underwater", 0) + areas.get("waterline", 0)
        plan.cathodic_protection = CathodicProtection.design_for_vessel(
            wetted_area_m2=wetted_area,
            design_life_years=3.0,
        )

        return plan

    def _get_or_estimate_areas(self) -> dict:
        """Get areas from state or estimate from hull dimensions."""

        # Try to get from state first
        underwater = self.state.get("hull.wetted_surface_m2", None)

        if underwater is None:
            # v1.1 FIX: Estimate from hull dimensions
            loa = self.state.get("hull.loa", 25)
            beam = self.state.get("hull.beam", 6)
            draft = self.state.get("hull.draft", 1.5)
            depth = self.state.get("hull.depth", 3.0)

            # Approximate surface areas
            underwater = 2 * loa * draft + loa * beam * 0.8  # Bottom + sides
            waterline = loa * 0.6 * 2  # Waterline band (0.6m high)
            topsides = 2 * loa * (depth - draft)  # Freeboard sides
            deck = loa * beam * 0.7  # Weather deck
            superstructure = loa * beam * 0.3 * 2  # Approx superstructure
            interior = loa * beam * 1.5  # Interior spaces
            tanks = loa * beam * 0.5  # Tank surfaces
        else:
            loa = self.state.get("hull.loa", 25)
            beam = self.state.get("hull.beam", 6)
            draft = self.state.get("hull.draft", 1.5)
            depth = self.state.get("hull.depth", 3.0)

            waterline = loa * 0.6 * 2
            topsides = 2 * loa * (depth - draft)
            deck = loa * beam * 0.7
            superstructure = loa * beam * 0.3 * 2
            interior = loa * beam * 1.5
            tanks = loa * beam * 0.5

        return {
            "underwater": underwater,
            "waterline": waterline,
            "topsides": topsides,
            "deck": deck,
            "superstructure": superstructure,
            "interior": interior,
            "tanks": tanks,
        }

    def _generate_coating_areas(self, areas: dict) -> List[CoatingArea]:
        """Generate coating areas with systems."""

        coating_areas = []
        zone_map = {
            "underwater": CoatingZone.UNDERWATER,
            "waterline": CoatingZone.WATERLINE,
            "topsides": CoatingZone.TOPSIDES,
            "deck": CoatingZone.DECK,
            "superstructure": CoatingZone.SUPERSTRUCTURE,
            "interior": CoatingZone.INTERIOR,
            "tanks": CoatingZone.TANKS,
        }

        for name, zone in zone_map.items():
            area_m2 = areas.get(name, 0)
            if area_m2 > 0:
                system = ALUMINUM_COATING_SYSTEMS.get(zone, {})
                coating_areas.append(CoatingArea(
                    area_id=f"AREA-{zone.value.upper()}",
                    zone=zone,
                    area_m2=area_m2,
                    system=system,
                    total_dft_um=system.get("total_dft_um", 200),
                ))

        return coating_areas
