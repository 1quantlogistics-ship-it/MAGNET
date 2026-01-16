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

#
# NOTE (TASK-017):
# Do NOT add hull_type-based multipliers here. Weight factors must derive from geometry.
#


def get_hull_factor_from_geometry(
    body_count: int,
    lb_ratio: float,
    froude_number: float = 0.3,
) -> float:
    """
    Derive hull weight factor from GEOMETRY, not hull_type.
    
    This fixes Issue 2.2: Novel geometries created via primitives get
    appropriate weight factors without hull_type lookup.
    
    Args:
        body_count: Number of hull bodies (derived from geometry)
        lb_ratio: Length/beam ratio (derived from geometry)
        froude_number: Froude number (Fn = V/sqrt(g*L))
    
    Returns:
        Hull weight modification factor
    
    Logic:
        - body_count=1: Base factor 1.0
        - body_count=2: +15% for dual hulls + crossdeck
        - body_count=3: +25% for triple hulls + complex crossdeck
        - body_count>3: +10% per additional body
        - Slender hulls (L/B > 8): -5% (less structure)
        - Planing speed (Fn > 0.5): -10% (lighter scantlings)
    
    CRITICAL: body_count is a GEOMETRIC FACT, not a design classification.
    - body_count=2 could be catamaran, proa, SWATH, or novel form
    - We compute weight from actual geometry, not from what it's "called"
    
    Reference: MAGNET_Critical_Corrections.md Part II Issue 2.2
    """
    # Base factor
    factor = 1.0
    
    # Multi-body factor
    # NOTE: This is NOT "catamaran" vs "trimaran" — it's the physical fact
    # that more bodies = more structure + more crossdeck weight
    if body_count == 2:
        factor *= 1.15  # Dual-body: two hulls + connecting structure
    elif body_count == 3:
        factor *= 1.25  # Triple-body: three hulls + complex crossdeck
    elif body_count > 3:
        # Novel configuration: extrapolate based on body count
        factor *= 1.15 + 0.10 * (body_count - 2)
    
    # Slenderness factor (L/B ratio)
    # Slender hulls have less wetted surface per unit volume → less structure
    if lb_ratio > 8.0:
        factor *= 0.95  # 5% reduction for slender hulls
    elif lb_ratio < 4.0:
        factor *= 1.05  # 5% increase for beamy hulls (more stiffening needed)
    
    # Speed regime factor (Froude number)
    # High-speed planing hulls have lighter bottom structure
    if froude_number > 0.5:
        factor *= 0.90  # 10% reduction for planing speeds
    elif froude_number < 0.25:
        factor *= 1.05  # 5% increase for displacement speeds (heavier scantlings)
    
    return factor

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

    def estimate_from_geometry(
        self,
        lwl: float,
        beam: float,
        depth: float,
        cb: float,
        body_count: int = 1,
        froude_number: float = 0.3,
        material: str = "aluminum_5083",
        service_type: str = "commercial",
        deadrise_deg: float = 0.0,
    ) -> List[WeightItem]:
        """
        Estimate hull structure weight from GEOMETRY (Issue 2.2).
        
        This is the NEW PATH that works with arbitrary geometry created
        via design language primitives.
        
        Args:
            lwl: Waterline length (m)
            beam: Beam (m)
            depth: Depth (m)
            cb: Block coefficient
            body_count: Number of hull bodies (derived from geometry)
            froude_number: Speed regime indicator
            material: Hull material type
            service_type: Vessel service type
            deadrise_deg: Bottom deadrise angle (degrees)
        
        Returns:
            List of WeightItem for Group 100 components
        
        CRITICAL: body_count is geometric fact, not design type.
        - body_count=2 could be catamaran, proa, SWATH, or novel form
        - We compute weight from actual geometry dimensions
        
        Reference: MAGNET_Critical_Corrections.md Part II Issue 2.2
        """
        # Validate inputs
        if lwl <= 0 or beam <= 0 or depth <= 0:
            raise ValueError(f"Invalid dimensions: L={lwl}, B={beam}, D={depth}")
        if cb <= 0 or cb > 1:
            cb = 0.55  # Default for medium-speed craft
        
        # Get factors
        material_factor = MATERIAL_FACTORS.get(material, 0.65)
        service_factor = SERVICE_FACTORS.get(service_type, 1.0)
        
        # Derive hull factor from geometry (NOT from hull_type lookup)
        lb_ratio = lwl / beam if beam > 0 else 5.0
        hull_factor = get_hull_factor_from_geometry(body_count, lb_ratio, froude_number)
        
        # Deadrise correction
        deadrise_correction = 1.0
        if deadrise_deg > 10:
            deadrise_correction = 1.0 + DEADRISE_FACTOR_PER_DEGREE * (deadrise_deg - 10)
        
        # Calculate base hull weight using Watson-Gilfillan
        base_weight_mt = (
            HULL_WEIGHT_K_BASE
            * (lwl ** 1.5)
            * beam
            * depth
            * (cb + 0.5)
            * material_factor
            * hull_factor
            * service_factor
            * deadrise_correction
        )
        
        # Create weight items
        items = [
            WeightItem(
                name=f"Hull Shell & Framing ({body_count} body)",
                weight_kg=base_weight_mt * 1000 * 0.75,
                lcg_m=lwl * 0.48,
                vcg_m=depth * 0.45,
                group=SWBSGroup.GROUP_100,
                subgroup=110,
                confidence=WeightConfidence.MEDIUM,
                notes=f"Watson-Gilfillan (geometry-based): body_count={body_count}, L/B={lb_ratio:.1f}, Fn={froude_number:.2f}",
            ),
            WeightItem(
                name="Bulkheads",
                weight_kg=base_weight_mt * 1000 * 0.15,
                lcg_m=lwl * 0.50,
                vcg_m=depth * 0.50,
                group=SWBSGroup.GROUP_100,
                subgroup=140,
                confidence=WeightConfidence.LOW,
                notes="Parametric estimate",
            ),
            WeightItem(
                name="Foundations & Supports",
                weight_kg=base_weight_mt * 1000 * 0.10,
                lcg_m=lwl * 0.55,
                vcg_m=depth * 0.30,
                group=SWBSGroup.GROUP_100,
                subgroup=150,
                confidence=WeightConfidence.LOW,
                notes="Parametric estimate",
            ),
        ]
        
        logger.debug(
            f"Hull structure estimate (geometry): {base_weight_mt:.2f} MT "
            f"(body_count={body_count}, L/B={lb_ratio:.1f}, Fn={froude_number:.2f})"
        )
        
        return items
    
    def estimate(
        self,
        lwl: float,
        beam: float,
        depth: float,
        cb: float,
        material: str = "aluminum_5083",
        body_count: int = 1,
        froude_number: float = 0.3,
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
            body_count: Number of hull bodies (geometry-derived)
            froude_number: Speed regime indicator (Fn)
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

        # TASK-017: canonical path is geometry-derived
        return self.estimate_from_geometry(
            lwl=lwl,
            beam=beam,
            depth=depth,
            cb=cb,
            body_count=body_count,
            froude_number=froude_number,
            material=material,
            service_type=service_type,
            deadrise_deg=deadrise_deg,
        )

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
