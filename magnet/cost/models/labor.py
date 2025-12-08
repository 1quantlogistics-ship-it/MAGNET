"""
cost/models/labor.py - Labor cost estimation.

ALPHA OWNS THIS FILE.

Module 12 v1.1 - Labor cost estimation model.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from ..enums import CostCategory
from ..schema import CostItem, CostBreakdown

if TYPE_CHECKING:
    from ...core.state_manager import StateManager


# Labor rates (USD/hour)
LABOR_RATES = {
    "engineering": 125.0,
    "fabrication": 75.0,
    "welding": 85.0,
    "outfitting": 70.0,
    "electrical": 80.0,
    "painting": 55.0,
    "testing": 90.0,
    "management": 110.0,
}


class LaborCostModel:
    """Labor cost estimation model."""

    def estimate(self, state: "StateManager") -> CostBreakdown:
        """
        Estimate labor costs from state.

        Reads:
        - production.assembly (if available)
        - hull.lwl, hull.beam
        """
        breakdown = CostBreakdown(category=CostCategory.HULL_STRUCTURE)

        # Try to use production assembly data
        assembly = state.get("production.assembly", {})
        if assembly:
            return self._from_assembly_sequence(assembly)

        # Fallback to parametric estimate
        return self._parametric_estimate(state)

    def _from_assembly_sequence(self, assembly: dict) -> CostBreakdown:
        """Create breakdown from assembly sequence."""
        breakdown = CostBreakdown(category=CostCategory.HULL_STRUCTURE)

        summary = assembly.get("summary", {})

        # Map assembly hours to labor categories
        hour_mapping = {
            "fabrication_hours": ("fabrication", LABOR_RATES["fabrication"]),
            "welding_hours": ("welding", LABOR_RATES["welding"]),
            "outfitting_hours": ("outfitting", LABOR_RATES["outfitting"]),
            "painting_hours": ("painting", LABOR_RATES["painting"]),
            "testing_hours": ("testing", LABOR_RATES["testing"]),
        }

        for key, (labor_type, rate) in hour_mapping.items():
            hours = summary.get(key, 0)
            if hours > 0:
                labor_cost = hours * rate

                breakdown.add_item(CostItem(
                    item_id=f"LAB-{labor_type.upper()[:3]}",
                    name=f"{labor_type.title()} Labor",
                    category=CostCategory.HULL_STRUCTURE,
                    description=f"{labor_type.title()} work hours",
                    quantity=hours,
                    unit="hr",
                    labor_cost=labor_cost,
                    labor_hours=hours,
                ))

                # Update breakdown hours
                if labor_type == "fabrication":
                    breakdown.fabrication_hours = hours
                elif labor_type == "outfitting":
                    breakdown.outfitting_hours = hours
                elif labor_type == "testing":
                    breakdown.testing_hours = hours

        return breakdown

    def _parametric_estimate(self, state: "StateManager") -> CostBreakdown:
        """Parametric labor estimate from hull dimensions."""
        breakdown = CostBreakdown(category=CostCategory.HULL_STRUCTURE)

        lwl = state.get("hull.lwl", 0)
        beam = state.get("hull.beam", 0)

        if lwl <= 0 or beam <= 0:
            return breakdown

        # Estimate hours based on hull size
        base_hours = lwl * 40  # Base hours per meter of length

        # Distribute across labor types
        labor_distribution = {
            "engineering": (0.15, LABOR_RATES["engineering"]),
            "fabrication": (0.35, LABOR_RATES["fabrication"]),
            "welding": (0.20, LABOR_RATES["welding"]),
            "outfitting": (0.15, LABOR_RATES["outfitting"]),
            "testing": (0.10, LABOR_RATES["testing"]),
            "management": (0.05, LABOR_RATES["management"]),
        }

        for labor_type, (fraction, rate) in labor_distribution.items():
            hours = base_hours * fraction * (beam / 5.0)  # Scale by beam
            labor_cost = hours * rate

            breakdown.add_item(CostItem(
                item_id=f"LAB-{labor_type.upper()[:3]}",
                name=f"{labor_type.title()} Labor (Parametric)",
                category=CostCategory.HULL_STRUCTURE,
                quantity=hours,
                unit="hr",
                labor_cost=labor_cost,
                labor_hours=hours,
            ))

            # Update breakdown hours
            if labor_type == "engineering":
                breakdown.engineering_hours = hours
            elif labor_type == "fabrication":
                breakdown.fabrication_hours = hours
            elif labor_type == "outfitting":
                breakdown.outfitting_hours = hours
            elif labor_type == "testing":
                breakdown.testing_hours = hours

        return breakdown
