"""
MAGNET Outfit & Furnishings Estimator (Group 600)

Module 07 v1.1 - Production-Ready

Estimates outfit and furnishing weight using crew/passenger parametric ratios.
"""

from __future__ import annotations
from typing import List
import logging

from ..items import SWBSGroup, WeightItem, WeightConfidence

logger = logging.getLogger(__name__)


# =============================================================================
# OUTFIT & FURNISHINGS ESTIMATOR
# =============================================================================

class OutfitFurnishingsEstimator:
    """
    Group 600 - Outfit & Furnishings weight estimator.

    Uses crew and passenger count parametric ratios.

    Produces weight items for:
    - Accommodations (berths, furniture)
    - Galley/mess
    - Sanitary spaces
    - Paint and coatings
    - Deck fittings
    - Safety equipment
    """

    def estimate(
        self,
        lwl: float,
        beam: float,
        depth: float,
        crew_size: int = 6,
        passenger_count: int = 0,
    ) -> List[WeightItem]:
        """
        Estimate outfit and furnishings weight.

        Args:
            lwl: Waterline length (m)
            beam: Beam (m)
            depth: Vessel depth (m)
            crew_size: Number of crew
            passenger_count: Number of passengers

        Returns:
            List of WeightItem for Group 600 components
        """
        total_persons = crew_size + passenger_count
        deck_area = lwl * beam * 0.85  # Approximate deck area

        items = []

        # Crew accommodations
        # ~150 kg per crew berth (bed, storage, furniture)
        crew_accom_weight_kg = crew_size * 150
        items.append(WeightItem(
            name="Crew Accommodations",
            weight_kg=crew_accom_weight_kg,
            lcg_m=lwl * 0.35,           # Forward of midship
            vcg_m=depth * 0.65,
            tcg_m=0.0,
            group=SWBSGroup.GROUP_600,
            subgroup=610,
            confidence=WeightConfidence.MEDIUM,
            notes=f"{crew_size} crew berths with furniture (parametric)",
        ))

        # Passenger accommodations (if any)
        if passenger_count > 0:
            # ~100 kg per passenger (lighter than crew quarters)
            pax_accom_weight_kg = passenger_count * 100
            items.append(WeightItem(
                name="Passenger Accommodations",
                weight_kg=pax_accom_weight_kg,
                lcg_m=lwl * 0.40,
                vcg_m=depth * 0.70,
                tcg_m=0.0,
                group=SWBSGroup.GROUP_600,
                subgroup=620,
                confidence=WeightConfidence.LOW,
                notes=f"{passenger_count} passenger seats/cabins (parametric)",
            ))

        # Galley and mess
        # Scale by total persons: ~50 kg base + 20 kg per person
        galley_weight_kg = 50 + total_persons * 20
        items.append(WeightItem(
            name="Galley & Mess",
            weight_kg=galley_weight_kg,
            lcg_m=lwl * 0.38,
            vcg_m=depth * 0.60,
            tcg_m=0.0,
            group=SWBSGroup.GROUP_600,
            subgroup=630,
            confidence=WeightConfidence.MEDIUM,
            notes="Galley equipment, tables, seating (parametric)",
        ))

        # Sanitary spaces
        # ~80 kg per head compartment
        num_heads = max(1, total_persons // 4)
        sanitary_weight_kg = num_heads * 80
        items.append(WeightItem(
            name="Sanitary Spaces",
            weight_kg=sanitary_weight_kg,
            lcg_m=lwl * 0.40,
            vcg_m=depth * 0.50,
            tcg_m=0.0,
            group=SWBSGroup.GROUP_600,
            subgroup=640,
            confidence=WeightConfidence.MEDIUM,
            notes=f"{num_heads} head compartments (parametric)",
        ))

        # Paint and coatings
        # ~3 kg/m² of surface area
        surface_area = 2 * (lwl * beam + lwl * depth + beam * depth)
        paint_weight_kg = surface_area * 3.0
        items.append(WeightItem(
            name="Paint & Coatings",
            weight_kg=paint_weight_kg,
            lcg_m=lwl * 0.50,           # Distributed
            vcg_m=depth * 0.50,
            tcg_m=0.0,
            group=SWBSGroup.GROUP_600,
            subgroup=650,
            confidence=WeightConfidence.HIGH,
            notes="Hull paint, antifouling, interior (parametric)",
        ))

        # Deck fittings
        # Scale by deck area: ~2 kg/m²
        deck_fittings_weight_kg = deck_area * 2.0
        items.append(WeightItem(
            name="Deck Fittings",
            weight_kg=deck_fittings_weight_kg,
            lcg_m=lwl * 0.50,
            vcg_m=depth * 0.90,         # On deck
            tcg_m=0.0,
            group=SWBSGroup.GROUP_600,
            subgroup=660,
            confidence=WeightConfidence.LOW,
            notes="Cleats, fairleads, rails, hatches (parametric)",
        ))

        # Safety equipment (lifejackets, rafts, extinguishers)
        # ~15 kg per person + base equipment
        safety_weight_kg = 100 + total_persons * 15
        items.append(WeightItem(
            name="Safety Equipment",
            weight_kg=safety_weight_kg,
            lcg_m=lwl * 0.45,
            vcg_m=depth * 0.85,
            tcg_m=0.0,
            group=SWBSGroup.GROUP_600,
            subgroup=670,
            confidence=WeightConfidence.HIGH,
            notes="Lifejackets, rafts, extinguishers, first aid (parametric)",
        ))

        # Insulation
        insulation_weight_kg = deck_area * 1.5
        items.append(WeightItem(
            name="Insulation",
            weight_kg=insulation_weight_kg,
            lcg_m=lwl * 0.50,
            vcg_m=depth * 0.60,
            tcg_m=0.0,
            group=SWBSGroup.GROUP_600,
            subgroup=680,
            confidence=WeightConfidence.LOW,
            notes="Thermal and acoustic insulation (parametric)",
        ))

        logger.debug(
            f"Outfit estimate: {sum(i.weight_kg for i in items)/1000:.2f} MT "
            f"({crew_size} crew, {passenger_count} passengers)"
        )

        return items
