"""
cost/estimator.py - Main cost estimation engine.

ALPHA OWNS THIS FILE.

Module 12 v1.1 - Cost Estimation Framework engine.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from .enums import CostCategory, CostConfidence
from .schema import CostEstimate, CostBreakdown, CostItem
from .models import (
    MaterialCostModel,
    LaborCostModel,
    EquipmentCostModel,
    LifecycleCostModel,
)

if TYPE_CHECKING:
    from ..core.state_manager import StateManager


class CostEstimator:
    """
    Main cost estimation engine.

    Combines material, labor, equipment, and lifecycle models
    to produce a complete cost estimate.
    """

    def __init__(
        self,
        markup_percent: float = 15.0,
        contingency_percent: float = 10.0,
    ):
        self.markup_percent = markup_percent
        self.contingency_percent = contingency_percent

        # Initialize models
        self.material_model = MaterialCostModel()
        self.labor_model = LaborCostModel()
        self.equipment_model = EquipmentCostModel()
        self.lifecycle_model = LifecycleCostModel()

    def estimate(self, state: "StateManager") -> CostEstimate:
        """
        Generate complete cost estimate from design state.

        Reads from state:
        - design_id, design_name
        - hull.*, structure.*, propulsion.*, mission.*
        - production.* (if available)
        - weight.* (if available)

        Returns:
            CostEstimate with all breakdowns and totals
        """
        # Create estimate
        estimate = CostEstimate(
            design_id=state.get("design_id", "unknown"),
            design_name=state.get("design_name", "Unnamed Design"),
            estimate_date=datetime.now(timezone.utc),
            confidence=self._determine_confidence(state),
            markup_percent=self.markup_percent,
            contingency_percent=self.contingency_percent,
        )

        # Material costs
        material_breakdown = self.material_model.estimate(state)
        estimate.add_breakdown(material_breakdown)

        # Labor costs
        labor_breakdown = self.labor_model.estimate(state)
        estimate.add_breakdown(labor_breakdown)

        # Equipment costs
        equipment_breakdown = self.equipment_model.estimate(state)
        estimate.add_breakdown(equipment_breakdown)
        estimate.subtotal_equipment = equipment_breakdown.material_total

        # Engineering costs
        engineering_breakdown = self._estimate_engineering(state)
        estimate.add_breakdown(engineering_breakdown)

        # Management and testing
        management_breakdown = self._estimate_management(state, estimate.subtotal)
        estimate.add_breakdown(management_breakdown)

        # Lifecycle costs
        estimate.lifecycle = self.lifecycle_model.estimate(
            state, estimate.acquisition_cost
        )

        return estimate

    def _determine_confidence(self, state: "StateManager") -> CostConfidence:
        """Determine estimate confidence based on available data."""
        # Check data completeness
        has_production = state.get("production.materials") is not None
        has_weight = state.get("weight.lightship_mt") is not None
        has_propulsion = state.get("propulsion.installed_power_kw") is not None

        complete_fields = sum([has_production, has_weight, has_propulsion])

        if complete_fields >= 3:
            return CostConfidence.BUDGETARY
        elif complete_fields >= 1:
            return CostConfidence.ROM
        else:
            return CostConfidence.ROM

    def _estimate_engineering(self, state: "StateManager") -> CostBreakdown:
        """Estimate engineering/design costs."""
        breakdown = CostBreakdown(category=CostCategory.ENGINEERING)

        lwl = state.get("hull.lwl", 0)
        # TASK-018: Organizational intent is the ONLY categorical branch.
        # Prefer explicit mission.organization; fall back ONLY if vessel_type is explicitly military.
        organization = (state.get("mission.organization") or "").strip().lower()
        vessel_type = (state.get("mission.vessel_type") or "").strip().lower()
        if not organization and vessel_type in ("military", "naval"):
            organization = "military"

        # Base engineering hours
        base_hours = 200 + lwl * 15  # Base + scaling

        # Complexity scaling from geometry + configuration (continuous).
        body_count = state.get("hull.body_count") or state.get("hull.num_hulls") or 1
        try:
            body_count = int(body_count)
        except Exception:
            body_count = 1
        body_count = max(1, body_count)

        compartment_count = state.get("interior.compartment_count") or 0
        try:
            compartment_count = int(compartment_count)
        except Exception:
            compartment_count = 0
        compartment_count = max(0, compartment_count)

        weld_length_m = state.get("production.weld_length_m")
        if weld_length_m is None:
            # Deterministic proxy if not provided (NOT geometric form branching).
            # Scales with size + body_count only.
            weld_length_m = max(0.0, float(lwl) * 4.0 * float(body_count))

        complexity = (1.0 + 0.1 * body_count) * (1.0 + 0.05 * compartment_count) * (1.0 + 0.0005 * float(weld_length_m))
        base_hours *= complexity

        if organization == "military":
            base_hours *= 1.5  # More engineering for military org intent

        rate = 125.0  # Engineering rate

        breakdown.add_item(CostItem(
            item_id="ENG-DES-001",
            name="Naval Architecture & Design",
            category=CostCategory.ENGINEERING,
            quantity=base_hours,
            unit="hr",
            labor_cost=base_hours * rate,
            labor_hours=base_hours,
        ))
        breakdown.engineering_hours = base_hours

        # Classification society fees
        class_fee = 15000 + lwl * 500
        breakdown.add_item(CostItem(
            item_id="ENG-CLS-001",
            name="Classification Society Fees",
            category=CostCategory.ENGINEERING,
            material_cost=class_fee,
        ))

        return breakdown

    def _estimate_management(
        self,
        state: "StateManager",
        subtotal: float,
    ) -> CostBreakdown:
        """Estimate project management costs."""
        breakdown = CostBreakdown(category=CostCategory.MANAGEMENT)

        # Project management (~5% of subtotal)
        pm_cost = subtotal * 0.05
        pm_hours = pm_cost / 110.0  # Management rate

        breakdown.add_item(CostItem(
            item_id="MGT-PM-001",
            name="Project Management",
            category=CostCategory.MANAGEMENT,
            quantity=pm_hours,
            unit="hr",
            labor_cost=pm_cost,
            labor_hours=pm_hours,
        ))

        return breakdown
