"""
cost/models/equipment.py - Equipment cost estimation.

ALPHA OWNS THIS FILE.

Module 12 v1.1 - Equipment and systems cost estimation model.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from ..enums import CostCategory
from ..schema import CostItem, CostBreakdown

if TYPE_CHECKING:
    from ...core.state_manager import StateManager


class EquipmentCostModel:
    """Equipment and systems cost estimation."""

    def estimate(self, state: "StateManager") -> CostBreakdown:
        """
        Estimate equipment costs.

        Reads:
        - propulsion.installed_power_kw
        - propulsion.number_of_engines
        - mission.vessel_type
        - mission.crew_size
        - mission.passengers
        """
        breakdown = CostBreakdown(category=CostCategory.PROPULSION)

        # Propulsion
        self._add_propulsion(breakdown, state)

        # Electrical
        self._add_electrical(breakdown, state)

        # Navigation
        self._add_navigation(breakdown, state)

        # Safety
        self._add_safety(breakdown, state)

        return breakdown

    def _add_propulsion(self, breakdown: CostBreakdown, state: "StateManager") -> None:
        """Add propulsion equipment costs."""
        power_kw = state.get("propulsion.installed_power_kw", 0)
        num_engines = state.get("propulsion.number_of_engines", 2)

        if power_kw <= 0:
            return

        # Engine cost estimation ($200-400/kW for marine diesel)
        engine_rate = 350.0  # USD/kW
        engine_cost = power_kw * engine_rate

        breakdown.add_item(CostItem(
            item_id="EQP-ENG-001",
            name="Main Engines",
            category=CostCategory.PROPULSION,
            description=f"{num_engines}x marine diesel engines",
            quantity=num_engines,
            unit="ea",
            unit_cost=engine_cost / num_engines,
            material_cost=engine_cost,
        ))

        # Gearbox (~15% of engine cost)
        gearbox_cost = engine_cost * 0.15
        breakdown.add_item(CostItem(
            item_id="EQP-GBX-001",
            name="Gearboxes",
            category=CostCategory.PROPULSION,
            description="Marine reduction gearboxes",
            quantity=num_engines,
            material_cost=gearbox_cost,
        ))

        # Propellers (~10% of engine cost)
        prop_cost = engine_cost * 0.10
        breakdown.add_item(CostItem(
            item_id="EQP-PRP-001",
            name="Propellers",
            category=CostCategory.PROPULSION,
            description="Fixed pitch propellers",
            quantity=num_engines,
            material_cost=prop_cost,
        ))

        # Shafting (~5% of engine cost)
        shaft_cost = engine_cost * 0.05
        breakdown.add_item(CostItem(
            item_id="EQP-SHF-001",
            name="Shafting System",
            category=CostCategory.PROPULSION,
            quantity=num_engines,
            material_cost=shaft_cost,
        ))

    def _add_electrical(self, breakdown: CostBreakdown, state: "StateManager") -> None:
        """Add electrical system costs."""
        power_kw = state.get("propulsion.installed_power_kw", 0)

        # Generator sizing (~10-15% of main engine power)
        gen_power = power_kw * 0.12
        gen_cost = gen_power * 500  # $500/kW for marine genset

        if gen_cost > 0:
            breakdown.add_item(CostItem(
                item_id="EQP-GEN-001",
                name="Generator Sets",
                category=CostCategory.ELECTRICAL,
                description="Ship service generators",
                quantity=2,
                unit_cost=gen_cost / 2,
                material_cost=gen_cost,
            ))

        # Electrical distribution (estimated)
        dist_cost = gen_cost * 0.3 + 15000  # Base + scaling
        breakdown.add_item(CostItem(
            item_id="EQP-DST-001",
            name="Electrical Distribution",
            category=CostCategory.ELECTRICAL,
            description="Switchboards, cables, panels",
            material_cost=dist_cost,
        ))

    def _add_navigation(self, breakdown: CostBreakdown, state: "StateManager") -> None:
        """Add navigation equipment costs."""
        vessel_type = state.get("mission.vessel_type", "commercial")
        lwl = state.get("hull.lwl", 0)

        # Base navigation package
        nav_cost = 25000  # Basic radar, GPS, VHF

        if lwl > 20:
            nav_cost += 15000  # Larger vessels need more equipment

        if vessel_type in ["military", "naval", "patrol"]:
            nav_cost *= 2.0  # Military-grade equipment

        breakdown.add_item(CostItem(
            item_id="EQP-NAV-001",
            name="Navigation Package",
            category=CostCategory.NAVIGATION,
            description="Radar, GPS, AIS, VHF, charts",
            material_cost=nav_cost,
        ))

    def _add_safety(self, breakdown: CostBreakdown, state: "StateManager") -> None:
        """Add safety equipment costs."""
        crew_size = state.get("mission.crew_size", 4)
        passengers = state.get("mission.passengers", 0)
        total_persons = crew_size + passengers

        # Life saving equipment
        lsa_cost = total_persons * 500 + 5000  # Per person + base
        breakdown.add_item(CostItem(
            item_id="EQP-LSA-001",
            name="Life Saving Appliances",
            category=CostCategory.SAFETY,
            description="Life rafts, jackets, EPIRB, etc.",
            quantity=total_persons,
            material_cost=lsa_cost,
        ))

        # Fire fighting
        ff_cost = 8000 + (state.get("hull.lwl", 0) * 200)
        breakdown.add_item(CostItem(
            item_id="EQP-FFE-001",
            name="Fire Fighting Equipment",
            category=CostCategory.SAFETY,
            description="Extinguishers, detection, suppression",
            material_cost=ff_cost,
        ))
