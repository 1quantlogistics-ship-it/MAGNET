"""
MAGNET Electrical Plant Estimator (Group 300)

Module 07 v1.1 - Production-Ready

Estimates electrical system weight using parametric ratios.
"""

from __future__ import annotations
from typing import List
import logging

from ..items import SWBSGroup, WeightItem, WeightConfidence

logger = logging.getLogger(__name__)


# =============================================================================
# ELECTRICAL PLANT ESTIMATOR
# =============================================================================

class ElectricPlantEstimator:
    """
    Group 300 - Electrical Plant weight estimator.

    Uses parametric ratios based on installed power and vessel size.

    Produces weight items for:
    - Generators
    - Switchboards
    - Cabling/wiring
    - Lighting
    - Power conversion
    """

    def estimate(
        self,
        installed_power_kw: float,
        lwl: float,
        depth: float,
        generator_count: int = 2,
    ) -> List[WeightItem]:
        """
        Estimate electrical plant weight.

        Args:
            installed_power_kw: Total installed propulsion power (kW)
            lwl: Waterline length (m)
            depth: Vessel depth (m)
            generator_count: Number of generators

        Returns:
            List of WeightItem for Group 300 components
        """
        # Estimate electrical load as fraction of installed power
        # Typical: 15-25% of installed power
        electrical_load_kw = installed_power_kw * 0.20

        items = []

        # Generators (diesel gensets)
        # Specific weight ~15 kg/kW for marine gensets
        genset_power = electrical_load_kw / max(generator_count, 1)
        genset_weight_kg = genset_power * 15.0

        for i in range(generator_count):
            tcg = 0.0 if generator_count == 1 else (1.0 if i % 2 == 0 else -1.0)

            items.append(WeightItem(
                name=f"Generator Set {i+1}",
                weight_kg=genset_weight_kg,
                lcg_m=lwl * 0.55,       # Near engine room
                vcg_m=depth * 0.30,
                tcg_m=tcg,
                group=SWBSGroup.GROUP_300,
                subgroup=310,
                confidence=WeightConfidence.HIGH,
                notes=f"{genset_power:.0f}kW diesel genset (parametric)",
            ))

        # Main switchboard
        switchboard_weight_kg = electrical_load_kw * 0.5  # ~0.5 kg/kW
        items.append(WeightItem(
            name="Main Switchboard",
            weight_kg=switchboard_weight_kg,
            lcg_m=lwl * 0.50,
            vcg_m=depth * 0.50,
            tcg_m=0.0,
            group=SWBSGroup.GROUP_300,
            subgroup=320,
            confidence=WeightConfidence.HIGH,
            notes="Main electrical distribution (parametric)",
        ))

        # Cabling and wiring
        # ~1.5 kg per meter of vessel length per kW (rough estimate)
        cable_weight_kg = lwl * 2.0 + electrical_load_kw * 0.3
        items.append(WeightItem(
            name="Electrical Cabling",
            weight_kg=cable_weight_kg,
            lcg_m=lwl * 0.50,           # Distributed
            vcg_m=depth * 0.60,
            tcg_m=0.0,
            group=SWBSGroup.GROUP_300,
            subgroup=330,
            confidence=WeightConfidence.LOW,
            notes="Power and signal cabling (parametric)",
        ))

        # Lighting systems
        lighting_weight_kg = lwl * depth * 0.8  # ~0.8 kg per m² of deck area
        items.append(WeightItem(
            name="Lighting Systems",
            weight_kg=lighting_weight_kg,
            lcg_m=lwl * 0.45,
            vcg_m=depth * 0.85,        # Overhead
            tcg_m=0.0,
            group=SWBSGroup.GROUP_300,
            subgroup=340,
            confidence=WeightConfidence.MEDIUM,
            notes="Interior and exterior lighting (parametric)",
        ))

        # Power conversion (inverters, transformers)
        conversion_weight_kg = electrical_load_kw * 0.2
        items.append(WeightItem(
            name="Power Conversion Equipment",
            weight_kg=conversion_weight_kg,
            lcg_m=lwl * 0.52,
            vcg_m=depth * 0.35,
            tcg_m=0.0,
            group=SWBSGroup.GROUP_300,
            subgroup=350,
            confidence=WeightConfidence.LOW,
            notes="Inverters, transformers, UPS (parametric)",
        ))

        logger.debug(
            f"Electrical estimate: {sum(i.weight_kg for i in items)/1000:.2f} MT "
            f"({electrical_load_kw:.0f}kW load)"
        )

        return items
