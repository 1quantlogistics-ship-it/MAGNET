"""
cost/schema.py - Cost data structures.

ALPHA OWNS THIS FILE.

Module 12 v1.1 - Cost Estimation Framework data structures.

v1.1 PATCH P1: CostBreakdown.to_dict() includes all hour fields
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .enums import CostCategory, CostConfidence, LifecyclePhase


@dataclass
class CostItem:
    """Individual cost line item."""
    item_id: str
    name: str
    category: CostCategory
    description: str = ""

    quantity: float = 1.0
    unit: str = "ea"
    unit_cost: float = 0.0

    material_cost: float = 0.0
    labor_cost: float = 0.0
    labor_hours: float = 0.0

    def __post_init__(self):
        if self.unit_cost > 0 and self.material_cost == 0:
            self.material_cost = self.quantity * self.unit_cost

    @property
    def total_cost(self) -> float:
        return self.material_cost + self.labor_cost

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "quantity": round(self.quantity, 2),
            "unit": self.unit,
            "unit_cost": round(self.unit_cost, 2),
            "material_cost": round(self.material_cost, 2),
            "labor_cost": round(self.labor_cost, 2),
            "labor_hours": round(self.labor_hours, 1),
            "total_cost": round(self.total_cost, 2),
        }


@dataclass
class CostBreakdown:
    """Cost breakdown by category."""
    category: CostCategory
    items: List[CostItem] = field(default_factory=list)

    # Totals
    material_total: float = 0.0
    labor_total: float = 0.0

    # Hours by type
    engineering_hours: float = 0.0
    fabrication_hours: float = 0.0
    outfitting_hours: float = 0.0
    testing_hours: float = 0.0

    @property
    def total_cost(self) -> float:
        return self.material_total + self.labor_total

    @property
    def total_hours(self) -> float:
        return (self.engineering_hours + self.fabrication_hours +
                self.outfitting_hours + self.testing_hours)

    def add_item(self, item: CostItem) -> None:
        """Add item and update totals."""
        self.items.append(item)
        self.material_total += item.material_cost
        self.labor_total += item.labor_cost

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary.

        v1.1 PATCH P1: Includes all hour fields (outfitting_hours, testing_hours)
        """
        return {
            "category": self.category.value,
            "material_total": round(self.material_total, 2),
            "labor_total": round(self.labor_total, 2),
            "total_cost": round(self.total_cost, 2),
            "item_count": len(self.items),
            "engineering_hours": round(self.engineering_hours, 1),
            "fabrication_hours": round(self.fabrication_hours, 1),
            "outfitting_hours": round(self.outfitting_hours, 1),   # P1 FIX
            "testing_hours": round(self.testing_hours, 1),         # P1 FIX
            "items": [i.to_dict() for i in self.items],
        }


@dataclass
class LifecycleCost:
    """Lifecycle cost analysis."""
    phase: LifecyclePhase
    annual_cost: float = 0.0
    years: int = 1
    discount_rate: float = 0.05

    @property
    def total_cost(self) -> float:
        return self.annual_cost * self.years

    @property
    def npv(self) -> float:
        """Net present value of lifecycle phase."""
        if self.discount_rate == 0:
            return self.total_cost

        # Sum discounted annual costs
        npv = 0.0
        for year in range(self.years):
            npv += self.annual_cost / ((1 + self.discount_rate) ** year)
        return npv

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase.value,
            "annual_cost": round(self.annual_cost, 2),
            "years": self.years,
            "total_cost": round(self.total_cost, 2),
            "npv": round(self.npv, 2),
        }


@dataclass
class CostEstimate:
    """Complete cost estimate."""
    design_id: str
    design_name: str
    estimate_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: CostConfidence = CostConfidence.ROM

    # Breakdowns by category
    breakdowns: Dict[CostCategory, CostBreakdown] = field(default_factory=dict)

    # Lifecycle costs
    lifecycle: List[LifecycleCost] = field(default_factory=list)

    # Summary totals
    subtotal_material: float = 0.0
    subtotal_labor: float = 0.0
    subtotal_equipment: float = 0.0

    markup_percent: float = 15.0
    contingency_percent: float = 10.0

    # Currency
    currency: str = "USD"

    @property
    def subtotal(self) -> float:
        return self.subtotal_material + self.subtotal_labor + self.subtotal_equipment

    @property
    def markup(self) -> float:
        return self.subtotal * (self.markup_percent / 100)

    @property
    def contingency(self) -> float:
        return self.subtotal * (self.contingency_percent / 100)

    @property
    def acquisition_cost(self) -> float:
        return self.subtotal + self.markup + self.contingency

    @property
    def total_price(self) -> float:
        """Total price including all costs."""
        return self.acquisition_cost

    @property
    def lifecycle_npv(self) -> float:
        """Total lifecycle NPV."""
        return sum(lc.npv for lc in self.lifecycle) + self.acquisition_cost

    def add_breakdown(self, breakdown: CostBreakdown) -> None:
        """Add category breakdown and update subtotals."""
        self.breakdowns[breakdown.category] = breakdown
        self._recalculate_subtotals()

    def _recalculate_subtotals(self) -> None:
        """Recalculate subtotals from breakdowns."""
        self.subtotal_material = sum(b.material_total for b in self.breakdowns.values())
        self.subtotal_labor = sum(b.labor_total for b in self.breakdowns.values())

    def get_total_hours(self) -> Dict[str, float]:
        """Get total hours by type."""
        hours = {
            "engineering": 0.0,
            "fabrication": 0.0,
            "outfitting": 0.0,
            "testing": 0.0,
        }
        for breakdown in self.breakdowns.values():
            hours["engineering"] += breakdown.engineering_hours
            hours["fabrication"] += breakdown.fabrication_hours
            hours["outfitting"] += breakdown.outfitting_hours
            hours["testing"] += breakdown.testing_hours
        return hours

    def to_dict(self) -> Dict[str, Any]:
        return {
            "design_id": self.design_id,
            "design_name": self.design_name,
            "estimate_date": self.estimate_date.isoformat(),
            "confidence": self.confidence.value,
            "currency": self.currency,
            "breakdowns": {k.value: v.to_dict() for k, v in self.breakdowns.items()},
            "lifecycle": [lc.to_dict() for lc in self.lifecycle],
            "subtotals": {
                "material": round(self.subtotal_material, 2),
                "labor": round(self.subtotal_labor, 2),
                "equipment": round(self.subtotal_equipment, 2),
            },
            "markup_percent": self.markup_percent,
            "contingency_percent": self.contingency_percent,
            "acquisition_cost": round(self.acquisition_cost, 2),
            "total_price": round(self.total_price, 2),
            "lifecycle_npv": round(self.lifecycle_npv, 2),
            "hours": self.get_total_hours(),
        }
