"""
MAGNET Hull Structure Estimator (Group 100)

Module 07 v1.1 - Production-Ready

Estimates hull structural weight using Watson-Gilfillan method modified for aluminum.

Reference: Watson & Gilfillan, "Some Ship Design Methods" RINA 1976
"""

from __future__ import annotations
from typing import List, Dict, Any
import math
import logging

from ..items import SWBSGroup, WeightItem, WeightConfidence

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Watson-Gilfillan base coefficient
HULL_WEIGHT_K_BASE = 0.034

# Material density factors (relative to mild steel = 1.0)
MATERIAL_FACTORS = {
    "mild_steel": 1.0,
    "high_tensile_steel": 0.95,
    "aluminum_5083": 0.65,
    "aluminum_5086": 0.65,
    "aluminum_6061": 0.60,
    "frp": 0.50,
    "carbon_fiber": 0.35,
}

# Hull type modification factors
HULL_TYPE_FACTORS = {
    "monohull": 1.0,
    "catamaran": 1.15,      # ~15% more structure for two hulls
    "trimaran": 1.25,       # ~25% more for three hulls + crossdeck
    "swath": 1.30,          # Complex struts and pods
    "planing": 0.90,        # Lighter bottom structure at speed
    "displacement": 1.05,   # Heavier scantlings for seakeeping
}

# Service type factors (structural reinforcement)
SERVICE_FACTORS = {
    "commercial": 1.0,
    "military": 1.10,       # Higher design margins
    "patrol": 1.05,         # Moderate reinforcement
    "passenger": 1.05,      # Safety margins
    "workboat": 1.15,       # Heavy duty operations
    "yacht": 0.90,          # Optimized weight
}

# Deadrise angle correction (higher deadrise = more bottom structure)
DEADRISE_FACTOR_PER_DEGREE = 0.005  # +0.5% per degree above 10


# =============================================================================
# HULL STRUCTURE ESTIMATOR
# =============================================================================

class HullStructureEstimator:
    """
    Group 100 - Hull Structure weight estimator.

    Uses Watson-Gilfillan method modified for aluminum craft:
        W_hull = K × L^1.5 × B × D × (Cb + 0.5) × material_factor × modifiers

    Where:
    - K = base coefficient (0.034)
    - L = waterline length (m)
    - B = beam (m)
    - D = depth (m)
    - Cb = block coefficient

    Produces weight items for:
    - Shell plating
    - Internal framing
    - Deck structure
    - Bulkheads
    - Foundations
    - Appendages (keel, rudder, etc.)
    """

    def estimate(
        self,
        lwl: float,
        beam: float,
        depth: float,
        cb: float,
        material: str = "aluminum_5083",
        hull_type: str = "monohull",
        service_type: str = "commercial",
        deadrise_deg: float = 0.0,
    ) -> List[WeightItem]:
        """
        Estimate hull structure weight.

        Args:
            lwl: Waterline length (m)
            beam: Beam (m)
            depth: Depth (m)
            cb: Block coefficient
            material: Hull material type
            hull_type: Hull configuration
            service_type: Vessel service type
            deadrise_deg: Bottom deadrise angle (degrees)

        Returns:
            List of WeightItem for Group 100 components
        """
        # Validate inputs
        if lwl <= 0 or beam <= 0 or depth <= 0:
            raise ValueError(f"Invalid dimensions: L={lwl}, B={beam}, D={depth}")
        if cb <= 0 or cb > 1:
            cb = 0.55  # Default for medium-speed craft

        # Get factors
        material_factor = MATERIAL_FACTORS.get(material, 0.65)
        hull_factor = HULL_TYPE_FACTORS.get(hull_type, 1.0)
        service_factor = SERVICE_FACTORS.get(service_type, 1.0)

        # Deadrise correction (above 10 degrees)
        deadrise_correction = 1.0
        if deadrise_deg > 10:
            deadrise_correction = 1.0 + DEADRISE_FACTOR_PER_DEGREE * (deadrise_deg - 10)

        # Calculate base hull weight using Watson-Gilfillan
        # W = K × L^1.5 × B × D × (Cb + 0.5)
        base_weight_kg = (
            HULL_WEIGHT_K_BASE *
            (lwl ** 1.5) *
            beam *
            depth *
            (cb + 0.5) *
            material_factor *
            hull_factor *
            service_factor *
            deadrise_correction *
            1000  # Convert to kg
        )

        # Distribute weight among components
        items = self._distribute_weight(
            total_weight_kg=base_weight_kg,
            lwl=lwl,
            beam=beam,
            depth=depth,
            material=material,
        )

        logger.debug(
            f"Hull structure estimate: {sum(i.weight_kg for i in items)/1000:.2f} MT "
            f"(material={material}, type={hull_type})"
        )

        return items

    def _distribute_weight(
        self,
        total_weight_kg: float,
        lwl: float,
        beam: float,
        depth: float,
        material: str,
    ) -> List[WeightItem]:
        """
        Distribute total hull weight among structural components.

        Typical distribution for aluminum craft:
        - Shell plating: 35%
        - Internal framing: 25%
        - Deck structure: 20%
        - Bulkheads: 10%
        - Foundations: 5%
        - Appendages: 5%
        """
        # Weight distribution percentages
        distribution = {
            "shell_plating": (0.35, 110),
            "internal_framing": (0.25, 120),
            "deck_structure": (0.20, 130),
            "bulkheads": (0.10, 140),
            "foundations": (0.05, 150),
            "appendages": (0.05, 160),
        }

        # Center of gravity estimates (as fractions of dimensions)
        # LCG from FP, VCG from baseline
        cg_estimates = {
            "shell_plating": {"lcg": 0.50, "vcg": 0.45},
            "internal_framing": {"lcg": 0.50, "vcg": 0.40},
            "deck_structure": {"lcg": 0.48, "vcg": 0.85},
            "bulkheads": {"lcg": 0.50, "vcg": 0.50},
            "foundations": {"lcg": 0.55, "vcg": 0.15},  # Engine room area
            "appendages": {"lcg": 0.80, "vcg": 0.10},   # Stern area, below waterline
        }

        # Confidence levels
        confidence = {
            "shell_plating": WeightConfidence.HIGH,
            "internal_framing": WeightConfidence.HIGH,
            "deck_structure": WeightConfidence.HIGH,
            "bulkheads": WeightConfidence.MEDIUM,
            "foundations": WeightConfidence.LOW,
            "appendages": WeightConfidence.VERY_LOW,
        }

        items = []
        for component, (fraction, subgroup) in distribution.items():
            weight_kg = total_weight_kg * fraction
            cg = cg_estimates[component]

            items.append(WeightItem(
                name=component.replace("_", " ").title(),
                weight_kg=weight_kg,
                lcg_m=cg["lcg"] * lwl,
                vcg_m=cg["vcg"] * depth,
                tcg_m=0.0,  # Symmetric
                group=SWBSGroup.GROUP_100,
                subgroup=subgroup,
                confidence=confidence[component],
                notes=f"{material} {component.replace('_', ' ')} (Watson-Gilfillan)",
            ))

        return items
