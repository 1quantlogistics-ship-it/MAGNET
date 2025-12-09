"""
weight/summary_generator.py - Weight summary generation
ALPHA OWNS THIS FILE.

Section 36: Weight Summary & Centers - v1.1 with fixed field paths
"""

from typing import Dict, Any, List
from ..core.state_manager import StateManager
from .items import WeightItem
from .loading import LoadingCondition, STANDARD_CONDITIONS
from .summary import WeightSummary, WeightGroup, WeightMargins, SWBS_DEFINITIONS


class WeightSummaryGenerator:
    """Generate complete weight summary - v1.1."""

    # v1.1 FIX: All systems use <s>.total_weight_kg
    SYSTEM_TO_SWBS = {
        "structure": "100",
        "coatings": "100",
        "propulsion": "200",
        "electrical": "300",
        "hvac": "500",
        "fuel": "200",
        "safety": "600",
        "outfitting": "600",
        "deck_equipment": "600",
    }

    def __init__(self, state: StateManager):
        self.state = state

    def generate(self) -> WeightSummary:
        """Generate complete weight summary."""
        summary = WeightSummary(
            summary_id=f"WT-{self.state.get('metadata.design_id', 'UNKNOWN')}",
        )

        for gid, gname in SWBS_DEFINITIONS.items():
            summary.groups[gid] = WeightGroup(group_id=gid, group_name=gname)

        self._collect_structure_weights(summary)
        self._collect_system_weights(summary)
        self._collect_outfitting_weights(summary)

        summary.calculate_lightship()
        summary.conditions = self._generate_conditions(summary)

        target = self.state.get("weight.displacement_kg", 0)
        if target > 0:
            full_condition = next((c for c in summary.conditions if c.condition_id == "FULL"), None)
            if full_condition:
                summary.target_displacement_kg = target
                summary.weight_difference_kg = full_condition.displacement_kg - target
                summary.weight_difference_percent = (summary.weight_difference_kg / target) * 100

        return summary

    def _collect_structure_weights(self, summary: WeightSummary) -> None:
        """Collect structure-related weights into Group 100."""
        loa = self.state.get("hull.loa", 25)
        lwl = self.state.get("hull.lwl", 23)

        # v1.1 FIX: Use correct field path for LCB
        lcb_percent = self.state.get("hull.lcb_percent_lwl", 45)
        lcb = lcb_percent / 100 * lwl

        hull_weight = self.state.get("structure.hull_weight_kg", 0)
        if hull_weight <= 0:
            hull_weight = self.state.get("weight.hull_weight_kg", 0)
        if hull_weight <= 0:
            # Try to get from lightship calculation
            hull_weight = self.state.get("weight.group_100_mt", 0) * 1000

        if hull_weight > 0:
            summary.groups["100"].items.append(WeightItem(
                item_id="STR-HULL",
                name="Hull Structure",
                group=SWBSGroup.GROUP_100 if hasattr(WeightItem, 'group') else None,
                weight_kg=hull_weight,
                lcg_m=lcb,
                vcg_m=1.5,
            ))

        super_weight = self.state.get("structure.superstructure_weight_kg", 0)
        if super_weight > 0:
            summary.groups["100"].items.append(WeightItem(
                item_id="STR-SUPER",
                name="Superstructure",
                group=SWBSGroup.GROUP_100 if hasattr(WeightItem, 'group') else None,
                weight_kg=super_weight,
                lcg_m=loa * 0.6,
                vcg_m=4.0,
            ))

        coat_weight = self.state.get("coatings.total_weight_kg", 0)
        if coat_weight <= 0:
            coat_weight = self.state.get("coatings.total_anode_weight_kg", 0)
        if coat_weight > 0:
            summary.groups["100"].items.append(WeightItem(
                item_id="STR-COAT",
                name="Coatings & Protection",
                group=SWBSGroup.GROUP_100 if hasattr(WeightItem, 'group') else None,
                weight_kg=coat_weight,
                lcg_m=lcb,
                vcg_m=1.0,
            ))

    def _collect_system_weights(self, summary: WeightSummary) -> None:
        """Collect system weights into appropriate SWBS groups."""
        loa = self.state.get("hull.loa", 25)

        # v1.1 FIX: All systems use <s>.total_weight_kg
        prop_weight = self.state.get("propulsion.total_weight_kg", 0)
        if prop_weight <= 0:
            prop_weight = self.state.get("weight.group_200_mt", 0) * 1000
        if prop_weight > 0:
            summary.groups["200"].items.append(WeightItem(
                item_id="SYS-PROP",
                name="Propulsion System",
                weight_kg=prop_weight,
                lcg_m=loa * 0.25,
                vcg_m=1.0,
            ))

        elec_weight = self.state.get("electrical.total_weight_kg", 0)
        if elec_weight <= 0:
            elec_weight = self.state.get("weight.group_300_mt", 0) * 1000
        if elec_weight > 0:
            summary.groups["300"].items.append(WeightItem(
                item_id="SYS-ELEC",
                name="Electrical System",
                weight_kg=elec_weight,
                lcg_m=loa * 0.35,
                vcg_m=1.5,
            ))

        hvac_weight = self.state.get("hvac.total_weight_kg", 0)
        if hvac_weight > 0:
            summary.groups["500"].items.append(WeightItem(
                item_id="SYS-HVAC",
                name="HVAC System",
                weight_kg=hvac_weight,
                lcg_m=loa * 0.5,
                vcg_m=3.0,
            ))

        fuel_sys_weight = self.state.get("fuel.system_weight_kg", 0)
        if fuel_sys_weight > 0:
            summary.groups["200"].items.append(WeightItem(
                item_id="SYS-FUEL",
                name="Fuel System",
                weight_kg=fuel_sys_weight,
                lcg_m=loa * 0.4,
                vcg_m=0.8,
            ))

        safety_weight = self.state.get("safety.total_weight_kg", 0)
        if safety_weight > 0:
            summary.groups["600"].items.append(WeightItem(
                item_id="SYS-SAFE",
                name="Safety Systems",
                weight_kg=safety_weight,
                lcg_m=loa * 0.5,
                vcg_m=3.5,
            ))

    def _collect_outfitting_weights(self, summary: WeightSummary) -> None:
        """Collect outfitting weights into Group 600."""
        loa = self.state.get("hull.loa", 25)

        outfit_weight = self.state.get("outfitting.total_weight_kg", 0)
        if outfit_weight > 0:
            summary.groups["600"].items.append(WeightItem(
                item_id="OUT-ACCOM",
                name="Accommodation & Furnishings",
                weight_kg=outfit_weight,
                lcg_m=loa * 0.55,
                vcg_m=2.5,
            ))

        deck_weight = self.state.get("deck_equipment.total_weight_kg", 0)
        if deck_weight > 0:
            summary.groups["600"].items.append(WeightItem(
                item_id="OUT-DECK",
                name="Deck Equipment",
                weight_kg=deck_weight,
                lcg_m=loa * 0.9,
                vcg_m=3.0,
            ))

    def _generate_conditions(self, summary: WeightSummary) -> List[LoadingCondition]:
        """Generate standard loading conditions."""
        conditions = []
        loa = self.state.get("hull.loa", 25)

        # v1.1 FIX: Get fuel weight from correct field
        full_fuel_kg = self.state.get("fuel.fuel_weight_full_kg", 0)
        if full_fuel_kg <= 0:
            fuel_m3 = self.state.get("fuel.total_fuel_m3", 5)
            full_fuel_kg = fuel_m3 * 850

        fuel_lcg = loa * 0.4
        fuel_vcg = 0.8

        fw_capacity_l = self.state.get("mission.fresh_water_capacity_l", 500)
        if fw_capacity_l <= 0:
            crew = self.state.get("mission.crew_berthed", 5)
            endurance = self.state.get("mission.endurance_days", 3)
            fw_capacity_l = crew * 100 * endurance
        full_fw_kg = fw_capacity_l
        fw_lcg = loa * 0.45
        fw_vcg = 1.0

        crew = self.state.get("mission.crew_berthed", 5)
        passengers = self.state.get("mission.passengers", 0)
        crew_kg = crew * 82
        pax_kg = passengers * 82
        stores_kg = (crew + passengers) * 10

        for spec in STANDARD_CONDITIONS:
            cond = LoadingCondition(
                condition_id=spec["id"],
                condition_name=spec["name"],
                lightship_kg=summary.lightship_with_margin_kg,
                lightship_lcg_m=summary.lightship_lcg_m,
                lightship_vcg_m=summary.lightship_vcg_m,
                fuel_kg=full_fuel_kg * spec["fuel"],
                fuel_lcg_m=fuel_lcg,
                fuel_vcg_m=fuel_vcg,
                fresh_water_kg=full_fw_kg * spec["fw"],
                fw_lcg_m=fw_lcg,
                fw_vcg_m=fw_vcg,
                stores_kg=stores_kg * spec["stores"],
                stores_lcg_m=loa * 0.5,
                stores_vcg_m=1.5,
                crew_kg=crew_kg,
                crew_lcg_m=loa * 0.6,
                crew_vcg_m=3.0,
                passengers_kg=pax_kg * spec["pax"],
                pax_lcg_m=loa * 0.55,
                pax_vcg_m=2.5,
            )
            cond._full_fuel = full_fuel_kg
            conditions.append(cond)

        return conditions
