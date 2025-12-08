"""
MAGNET Loading Calculator (v1.1)

Loading condition calculator with fixes.

Version 1.1 Fixes:
- Fixed draft calculation using design displacement (CI#6)
- Fixed lcf_m handling with fallback (CI#7)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging

from .models import (
    LoadingConditionType, LoadingConditionResult,
    TankLoad, DeadweightItem
)
from ..arrangement.models import Tank, FluidType, FLUID_DENSITIES

if TYPE_CHECKING:
    from ..core.state_manager import StateManager

logger = logging.getLogger(__name__)


class LoadingCalculator:
    """
    Calculates loading conditions.

    Version 1.1 Fixes:
    - Fixed draft calculation using design displacement (CI#6)
    - Fixed lcf_m handling (CI#7)
    """

    def calculate_condition(
        self,
        condition_name: str,
        condition_type: LoadingConditionType,
        lightship_mt: float,
        lightship_lcg_m: float,
        lightship_vcg_m: float,
        lightship_tcg_m: float,
        tanks: List[Tank],
        tank_fills: Dict[str, float],
        deadweight_items: List[DeadweightItem],
        # Hydrostatic data
        depth_m: float,
        tpc: float,
        mct: float,
        lcf_m: float,
        km_m: float,
        design_draft_m: float,
        design_displacement_mt: float,  # FIX v1.1: Added (CI#6)
        lwl_m: float,
    ) -> LoadingConditionResult:
        """
        Calculate complete loading condition.

        FIX v1.1: Uses design_displacement_mt for accurate draft calc (CI#6).
        """
        result = LoadingConditionResult(
            condition_name=condition_name,
            condition_type=condition_type,
        )

        # Start with lightship
        total_weight = lightship_mt
        moment_x = lightship_mt * lightship_lcg_m
        moment_y = lightship_mt * lightship_tcg_m
        moment_z = lightship_mt * lightship_vcg_m

        result.lightship_mt = lightship_mt

        # Add tank contents
        total_fsm = 0.0
        tank_weight = 0.0

        for tank in tanks:
            fill = tank_fills.get(tank.tank_id, tank.fill_percent)
            tank.fill_percent = fill

            weight = tank.current_weight_mt
            vcg = tank.get_current_vcg_m()

            tank_load = TankLoad(
                tank_id=tank.tank_id,
                fill_percent=fill,
                weight_mt=weight,
                lcg_m=tank.lcg_m,
                vcg_m=vcg,
                tcg_m=tank.tcg_m,
                fsm_t_m=tank.free_surface_moment_t_m,
            )
            result.tank_loads.append(tank_load)

            total_weight += weight
            moment_x += weight * tank.lcg_m
            moment_y += weight * tank.tcg_m
            moment_z += weight * vcg
            tank_weight += weight

            if tank.has_free_surface:
                total_fsm += tank.free_surface_moment_t_m

        # Add deadweight items
        dw_weight = 0.0
        for item in deadweight_items:
            result.deadweight_items.append(item)

            total_weight += item.weight_mt
            moment_x += item.weight_mt * item.lcg_m
            moment_y += item.weight_mt * item.tcg_m
            moment_z += item.weight_mt * item.vcg_m
            dw_weight += item.weight_mt

        result.deadweight_mt = tank_weight + dw_weight
        result.displacement_mt = total_weight

        if total_weight > 0:
            result.lcg_m = moment_x / total_weight
            result.tcg_m = moment_y / total_weight
            result.vcg_m = moment_z / total_weight

        # FIX v1.1: Improved draft calculation (CI#6)
        # Use design displacement for ratio, then cube root scaling
        if design_displacement_mt > 0:
            disp_ratio = result.displacement_mt / design_displacement_mt
            # Cube root gives reasonable draft scaling for most hull forms
            result.draft_m = design_draft_m * (disp_ratio ** (1.0 / 3.0))
        else:
            # Fallback: TPC method
            draft_change_cm = (result.displacement_mt - lightship_mt) / tpc if tpc > 0 else 0
            result.draft_m = design_draft_m + draft_change_cm / 100.0

        # Calculate trim
        lcb_m = lwl_m * 0.52  # Approximate LCB
        trim_moment = (result.lcg_m - lcb_m) * result.displacement_mt
        if mct > 0:
            result.trim_m = trim_moment / mct / 100
        else:
            result.trim_m = 0.0

        # Draft fwd/aft using lcf_m (FIX v1.1 - CI#7)
        if lwl_m > 0:
            lcf_ratio = lcf_m / lwl_m
            result.draft_fwd_m = result.draft_m - result.trim_m * lcf_ratio
            result.draft_aft_m = result.draft_m + result.trim_m * (1 - lcf_ratio)
        else:
            result.draft_fwd_m = result.draft_m
            result.draft_aft_m = result.draft_m

        # Freeboard
        result.freeboard_m = depth_m - result.draft_m

        # Stability
        result.km_m = km_m
        result.gm_solid_m = km_m - result.vcg_m

        # Free surface correction
        if result.displacement_mt > 0:
            result.fsc_m = total_fsm / result.displacement_mt
        else:
            result.fsc_m = 0.0

        result.gm_fluid_m = result.gm_solid_m - result.fsc_m

        # Limit checks
        result.passes_all_criteria = True

        # GM check
        if result.gm_fluid_m < 0:
            result.errors.append(f"Negative GM: {result.gm_fluid_m:.3f}m - UNSTABLE")
            result.passes_all_criteria = False
        elif result.gm_fluid_m < 0.15:
            result.warnings.append(f"GM {result.gm_fluid_m:.3f}m below IMO minimum 0.15m")

        # Draft check
        max_draft = depth_m * 0.85
        if result.draft_m > max_draft:
            result.errors.append(f"Draft {result.draft_m:.2f}m exceeds maximum {max_draft:.2f}m")
            result.passes_all_criteria = False

        # Freeboard check
        min_freeboard = 0.3
        if result.freeboard_m < min_freeboard:
            result.warnings.append(f"Freeboard {result.freeboard_m:.2f}m below minimum {min_freeboard:.2f}m")

        # Trim check
        max_trim = lwl_m * 0.02
        if abs(result.trim_m) > max_trim:
            result.warnings.append(f"Trim {result.trim_m:.2f}m exceeds recommended {max_trim:.2f}m")

        # Heel check
        if abs(result.tcg_m) > 0.05:
            result.warnings.append(f"TCG offset {result.tcg_m:.3f}m - vessel has initial heel")

        logger.debug(
            f"Calculated {condition_name}: {result.displacement_mt:.1f}MT, "
            f"GM={result.gm_fluid_m:.3f}m, draft={result.draft_m:.2f}m"
        )

        return result

    def create_standard_conditions(
        self,
        lightship_mt: float,
        lightship_lcg_m: float,
        lightship_vcg_m: float,
        lightship_tcg_m: float,
        tanks: List[Tank],
        crew_weight_mt: float,
        stores_weight_mt: float,
        lcg_crew_m: float,
        lcg_stores_m: float,
        vcg_crew_m: float,
        vcg_stores_m: float,
        depth_m: float,
        tpc: float,
        mct: float,
        lcf_m: float,
        km_m: float,
        design_draft_m: float,
        design_displacement_mt: float,  # FIX v1.1: Added (CI#6)
        lwl_m: float,
    ) -> Dict[str, LoadingConditionResult]:
        """Create standard loading conditions."""
        conditions = {}

        # Create deadweight items
        crew_item = DeadweightItem(
            item_id="DW-CREW",
            name="Crew & Effects",
            category="crew",
            weight_mt=crew_weight_mt,
            lcg_m=lcg_crew_m,
            vcg_m=vcg_crew_m,
        )

        stores_item = DeadweightItem(
            item_id="DW-STORES",
            name="Provisions & Stores",
            category="stores",
            weight_mt=stores_weight_mt,
            lcg_m=lcg_stores_m,
            vcg_m=vcg_stores_m,
        )

        # === Full Load Departure ===
        full_fills = {t.tank_id: 1.0 for t in tanks}
        conditions["full_load_departure"] = self.calculate_condition(
            condition_name="Full Load Departure",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            lightship_mt=lightship_mt,
            lightship_lcg_m=lightship_lcg_m,
            lightship_vcg_m=lightship_vcg_m,
            lightship_tcg_m=lightship_tcg_m,
            tanks=tanks,
            tank_fills=full_fills,
            deadweight_items=[crew_item, stores_item],
            depth_m=depth_m,
            tpc=tpc,
            mct=mct,
            lcf_m=lcf_m,
            km_m=km_m,
            design_draft_m=design_draft_m,
            design_displacement_mt=design_displacement_mt,
            lwl_m=lwl_m,
        )

        # === Full Load Arrival ===
        # Consumables depleted
        arrival_fills = {}
        for t in tanks:
            if t.fluid_type in [FluidType.FUEL_MGO, FluidType.FUEL_MDO, FluidType.FRESHWATER]:
                arrival_fills[t.tank_id] = 0.10  # 10% remaining
            elif t.fluid_type == FluidType.SEWAGE:
                arrival_fills[t.tank_id] = 0.80  # Sewage accumulated
            else:
                arrival_fills[t.tank_id] = t.fill_percent

        conditions["full_load_arrival"] = self.calculate_condition(
            condition_name="Full Load Arrival",
            condition_type=LoadingConditionType.FULL_LOAD_ARRIVAL,
            lightship_mt=lightship_mt,
            lightship_lcg_m=lightship_lcg_m,
            lightship_vcg_m=lightship_vcg_m,
            lightship_tcg_m=lightship_tcg_m,
            tanks=tanks,
            tank_fills=arrival_fills,
            deadweight_items=[crew_item, stores_item],
            depth_m=depth_m,
            tpc=tpc,
            mct=mct,
            lcf_m=lcf_m,
            km_m=km_m,
            design_draft_m=design_draft_m,
            design_displacement_mt=design_displacement_mt,
            lwl_m=lwl_m,
        )

        # === Minimum Operating ===
        min_stores = DeadweightItem(
            item_id="DW-STORES",
            name="Provisions & Stores (Minimum)",
            category="stores",
            weight_mt=stores_weight_mt * 0.1,
            lcg_m=lcg_stores_m,
            vcg_m=vcg_stores_m,
        )

        conditions["minimum_operating"] = self.calculate_condition(
            condition_name="Minimum Operating Condition",
            condition_type=LoadingConditionType.MINIMUM_OPERATING,
            lightship_mt=lightship_mt,
            lightship_lcg_m=lightship_lcg_m,
            lightship_vcg_m=lightship_vcg_m,
            lightship_tcg_m=lightship_tcg_m,
            tanks=tanks,
            tank_fills=arrival_fills,
            deadweight_items=[crew_item, min_stores],
            depth_m=depth_m,
            tpc=tpc,
            mct=mct,
            lcf_m=lcf_m,
            km_m=km_m,
            design_draft_m=design_draft_m,
            design_displacement_mt=design_displacement_mt,
            lwl_m=lwl_m,
        )

        # === Lightship (for reference) ===
        conditions["lightship"] = self.calculate_condition(
            condition_name="Lightship",
            condition_type=LoadingConditionType.LIGHTSHIP,
            lightship_mt=lightship_mt,
            lightship_lcg_m=lightship_lcg_m,
            lightship_vcg_m=lightship_vcg_m,
            lightship_tcg_m=lightship_tcg_m,
            tanks=tanks,
            tank_fills={t.tank_id: 0.0 for t in tanks},  # All tanks empty
            deadweight_items=[],  # No deadweight
            depth_m=depth_m,
            tpc=tpc,
            mct=mct,
            lcf_m=lcf_m,
            km_m=km_m,
            design_draft_m=design_draft_m,
            design_displacement_mt=design_displacement_mt,
            lwl_m=lwl_m,
        )

        return conditions
