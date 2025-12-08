"""
cost/models/material.py - Material cost estimation.

ALPHA OWNS THIS FILE.

Module 12 v1.1 - Material cost estimation model.
"""

from __future__ import annotations
from typing import Any, Dict, TYPE_CHECKING

from ..enums import CostCategory
from ..schema import CostItem, CostBreakdown

if TYPE_CHECKING:
    from ...core.state_manager import StateManager


# Material prices per kg (USD)
MATERIAL_PRICES = {
    "aluminum_5083": 8.50,
    "aluminum_5086": 8.75,
    "aluminum_6061": 7.50,
    "steel_mild": 2.50,
    "steel_hts": 3.50,
    "steel_stainless": 12.00,
    "fiberglass": 15.00,
    "carbon_fiber": 85.00,
}


class MaterialCostModel:
    """Material cost estimation model."""

    def __init__(self, scrap_factor: float = 1.15):
        """
        Initialize material cost model.

        Args:
            scrap_factor: Material waste factor (default 15%)
        """
        self.scrap_factor = scrap_factor

    def estimate(self, state: "StateManager") -> CostBreakdown:
        """
        Estimate material costs from state.

        Reads:
        - structure.material
        - production.materials (if available)
        - hull.lwl, hull.beam, hull.depth
        """
        breakdown = CostBreakdown(category=CostCategory.HULL_STRUCTURE)

        # Get material type and price
        material = state.get("structure.material", "aluminum_5083")
        price_per_kg = MATERIAL_PRICES.get(material, 8.50)

        # Try to use production material takeoff
        prod_materials = state.get("production.materials", {})
        if prod_materials:
            return self._from_production_takeoff(prod_materials, material, price_per_kg)

        # Fallback to parametric estimate
        return self._parametric_estimate(state, material, price_per_kg)

    def _from_production_takeoff(
        self,
        prod_materials: Dict[str, Any],
        material: str,
        price_per_kg: float,
    ) -> CostBreakdown:
        """Create breakdown from production takeoff."""
        breakdown = CostBreakdown(category=CostCategory.HULL_STRUCTURE)

        summary = prod_materials.get("summary", {})
        total_weight = summary.get("total_weight_kg", 0)

        if total_weight > 0:
            material_cost = total_weight * price_per_kg * self.scrap_factor

            breakdown.add_item(CostItem(
                item_id="MAT-001",
                name="Hull Structure Material",
                category=CostCategory.HULL_STRUCTURE,
                description=f"{material} plate and profiles",
                quantity=total_weight,
                unit="kg",
                unit_cost=price_per_kg * self.scrap_factor,
                material_cost=material_cost,
            ))

        return breakdown

    def _parametric_estimate(
        self,
        state: "StateManager",
        material: str,
        price_per_kg: float,
    ) -> CostBreakdown:
        """Parametric material estimate from hull dimensions."""
        breakdown = CostBreakdown(category=CostCategory.HULL_STRUCTURE)

        lwl = state.get("hull.lwl", 0)
        beam = state.get("hull.beam", 0)
        depth = state.get("hull.depth", 0)

        if lwl <= 0 or beam <= 0 or depth <= 0:
            return breakdown

        # Material density (kg/m³)
        density = 2660 if "aluminum" in material else 7850

        # Estimate surface areas
        bottom_area = lwl * beam * 1.1
        side_area = 2 * lwl * depth * 0.85
        deck_area = lwl * beam * 0.9

        total_area = bottom_area + side_area + deck_area

        # Estimate average thickness (mm)
        avg_thickness = 5.0 if "aluminum" in material else 6.0

        # Calculate weight
        plate_weight = total_area * (avg_thickness / 1000) * density
        profile_weight = plate_weight * 0.3  # Profiles ~30% of plate

        total_weight = (plate_weight + profile_weight) * self.scrap_factor
        material_cost = total_weight * price_per_kg

        breakdown.add_item(CostItem(
            item_id="MAT-001",
            name="Hull Structure Material (Parametric)",
            category=CostCategory.HULL_STRUCTURE,
            description=f"{material} estimated from hull dimensions",
            quantity=total_weight,
            unit="kg",
            unit_cost=price_per_kg,
            material_cost=material_cost,
        ))

        return breakdown
