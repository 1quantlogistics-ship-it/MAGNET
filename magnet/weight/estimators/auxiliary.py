"""
MAGNET Auxiliary Systems Estimator (Group 500)

Module 07 v1.1 - Production-Ready

Estimates auxiliary systems weight using displacement-based scaling.

v1.1 FIX #4: Documents that displacement is used as size proxy,
not for physical calculations. This is acceptable for early-stage design.
"""

from __future__ import annotations
from typing import List
import logging

from ..items import SWBSGroup, WeightItem, WeightConfidence

logger = logging.getLogger(__name__)


# =============================================================================
# AUXILIARY SYSTEMS ESTIMATOR
# =============================================================================

class AuxiliarySystemsEstimator:
    """
    Group 500 - Auxiliary Systems weight estimator.

    Uses displacement-based scaling for auxiliary equipment.

    LIMITATION (v1.1 FIX #4):
    Current implementation uses displacement for scaling some auxiliary
    weights. This is a simplification acceptable for early-stage design.

    More accurate methods for detailed design (V2):
    - HVAC: Scale by enclosed volume and crew count
    - Freshwater: Scale by crew × days × consumption rate
    - Fuel system: Scale by tank capacity
    - Steering: Scale by rudder area and speed

    Produces weight items for:
    - HVAC systems
    - Freshwater systems
    - Sewage/gray water
    - Fuel system
    - Steering gear
    - Anchor/mooring
    """

    def estimate(
        self,
        lwl: float,
        beam: float,
        depth: float,
        displacement_mt: float,
        crew_size: int = 6,
    ) -> List[WeightItem]:
        """
        Estimate auxiliary systems weight.

        Args:
            lwl: Waterline length (m)
            beam: Beam (m)
            depth: Vessel depth (m)
            displacement_mt: Displacement (metric tons) - used as size proxy
            crew_size: Number of crew

        Returns:
            List of WeightItem for Group 500 components

        Note:
            displacement_mt is used as a size proxy for scaling,
            not for physical calculations (v1.1 FIX #4 documented).
        """
        items = []

        # Volume estimate for HVAC sizing
        enclosed_volume = lwl * beam * depth * 0.6  # ~60% of bounding box

        # HVAC systems
        # Scale by enclosed volume: ~2 kg/m³
        hvac_weight_kg = enclosed_volume * 2.0 + crew_size * 15
        items.append(WeightItem(
            name="HVAC Systems",
            weight_kg=hvac_weight_kg,
            lcg_m=lwl * 0.45,           # Distributed
            vcg_m=depth * 0.70,
            tcg_m=0.0,
            group=SWBSGroup.GROUP_500,
            subgroup=510,
            confidence=WeightConfidence.LOW,
            notes="Heating, ventilation, air conditioning (parametric)",
        ))

        # Freshwater system
        # ~50 liters/person/day, 7 day capacity, plus tankage
        fw_capacity_liters = crew_size * 50 * 7
        fw_weight_kg = fw_capacity_liters * 1.1 + 200  # Water + tankage + pumps
        items.append(WeightItem(
            name="Freshwater System",
            weight_kg=fw_weight_kg,
            lcg_m=lwl * 0.40,
            vcg_m=depth * 0.25,         # Low in hull
            tcg_m=0.0,
            group=SWBSGroup.GROUP_500,
            subgroup=520,
            confidence=WeightConfidence.MEDIUM,
            notes=f"Tanks, pumps, watermaker ({fw_capacity_liters}L) (parametric)",
        ))

        # Sewage/gray water system
        sewage_weight_kg = crew_size * 30 + 150  # Holding tank + treatment
        items.append(WeightItem(
            name="Sewage/Gray Water System",
            weight_kg=sewage_weight_kg,
            lcg_m=lwl * 0.60,
            vcg_m=depth * 0.20,
            tcg_m=0.0,
            group=SWBSGroup.GROUP_500,
            subgroup=530,
            confidence=WeightConfidence.VERY_LOW,
            notes="Holding tanks, MSD, pumps (parametric)",
        ))

        # Fuel system (excluding fuel weight)
        # Scale by displacement proxy: ~0.5% of displacement for system weight
        fuel_system_weight_kg = displacement_mt * 5.0 + 100  # Tanks, piping, filters
        items.append(WeightItem(
            name="Fuel System",
            weight_kg=fuel_system_weight_kg,
            lcg_m=lwl * 0.55,
            vcg_m=depth * 0.30,
            tcg_m=0.0,
            group=SWBSGroup.GROUP_500,
            subgroup=540,
            confidence=WeightConfidence.LOW,
            notes="Fuel tanks, piping, filtration (empty) (parametric)",
        ))

        # Steering gear
        # Scale by displacement: heavier vessels need larger steering
        steering_weight_kg = displacement_mt * 0.5 + 100
        items.append(WeightItem(
            name="Steering Gear",
            weight_kg=steering_weight_kg,
            lcg_m=lwl * 0.90,           # Stern
            vcg_m=depth * 0.20,
            tcg_m=0.0,
            group=SWBSGroup.GROUP_500,
            subgroup=550,
            confidence=WeightConfidence.MEDIUM,
            notes="Hydraulic steering system (parametric)",
        ))

        # Anchor and mooring
        # Scale by vessel size
        anchor_weight_kg = lwl * 3.0 + beam * 2.0 + 100
        items.append(WeightItem(
            name="Anchor & Mooring",
            weight_kg=anchor_weight_kg,
            lcg_m=lwl * 0.05,           # Bow
            vcg_m=depth * 0.60,
            tcg_m=0.0,
            group=SWBSGroup.GROUP_500,
            subgroup=560,
            confidence=WeightConfidence.HIGH,
            notes="Anchor, chain, windlass, mooring equipment (parametric)",
        ))

        # Bilge system
        bilge_weight_kg = lwl * 1.5 + 50
        items.append(WeightItem(
            name="Bilge System",
            weight_kg=bilge_weight_kg,
            lcg_m=lwl * 0.50,
            vcg_m=depth * 0.10,         # Bottom of hull
            tcg_m=0.0,
            group=SWBSGroup.GROUP_500,
            subgroup=570,
            confidence=WeightConfidence.MEDIUM,
            notes="Bilge pumps, piping, oily water separator (parametric)",
        ))

        logger.debug(
            f"Auxiliary systems estimate: {sum(i.weight_kg for i in items)/1000:.2f} MT "
            f"(displacement_mt={displacement_mt:.0f})"
        )

        return items
