"""
cost/models/lifecycle.py - Lifecycle cost estimation.

ALPHA OWNS THIS FILE.

Module 12 v1.1 - Lifecycle cost estimation model.
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

from ..enums import LifecyclePhase
from ..schema import LifecycleCost

if TYPE_CHECKING:
    from ...core.state_manager import StateManager


class LifecycleCostModel:
    """Lifecycle cost estimation model."""

    def __init__(
        self,
        operational_years: int = 25,
        discount_rate: float = 0.05,
    ):
        """
        Initialize lifecycle model.

        Args:
            operational_years: Expected operational life
            discount_rate: Discount rate for NPV
        """
        self.operational_years = operational_years
        self.discount_rate = discount_rate

    def estimate(
        self,
        state: "StateManager",
        acquisition_cost: float,
    ) -> List[LifecycleCost]:
        """
        Estimate lifecycle costs.

        Args:
            state: StateManager with design data
            acquisition_cost: Initial acquisition cost
        """
        lifecycle = []

        # Acquisition (year 0)
        lifecycle.append(LifecycleCost(
            phase=LifecyclePhase.ACQUISITION,
            annual_cost=acquisition_cost,
            years=1,
            discount_rate=0,  # Already in present value
        ))

        # Operations
        ops_cost = self._estimate_operations(state, acquisition_cost)
        lifecycle.append(LifecycleCost(
            phase=LifecyclePhase.OPERATIONS,
            annual_cost=ops_cost,
            years=self.operational_years,
            discount_rate=self.discount_rate,
        ))

        # Maintenance
        maint_cost = self._estimate_maintenance(acquisition_cost)
        lifecycle.append(LifecycleCost(
            phase=LifecyclePhase.MAINTENANCE,
            annual_cost=maint_cost,
            years=self.operational_years,
            discount_rate=self.discount_rate,
        ))

        # Disposal
        disposal_cost = self._estimate_disposal(acquisition_cost)
        lifecycle.append(LifecycleCost(
            phase=LifecyclePhase.DISPOSAL,
            annual_cost=disposal_cost,
            years=1,
            discount_rate=self.discount_rate,
        ))

        return lifecycle

    def _estimate_operations(
        self,
        state: "StateManager",
        acquisition_cost: float,
    ) -> float:
        """Estimate annual operations cost."""
        # Fuel consumption
        fuel_rate = state.get("propulsion.fuel_consumption_lph", 50)
        operating_hours = 2000  # Assumed annual hours
        fuel_cost_per_liter = 1.50
        annual_fuel = fuel_rate * operating_hours * fuel_cost_per_liter

        # Crew costs
        crew_size = state.get("mission.crew_size", 4)
        annual_crew = crew_size * 75000  # Average crew cost

        # Insurance (~2% of acquisition)
        insurance = acquisition_cost * 0.02

        # Port fees and consumables
        other = 25000

        return annual_fuel + annual_crew + insurance + other

    def _estimate_maintenance(self, acquisition_cost: float) -> float:
        """Estimate annual maintenance cost (~3-5% of acquisition)."""
        return acquisition_cost * 0.04

    def _estimate_disposal(self, acquisition_cost: float) -> float:
        """Estimate disposal cost (net of scrap value)."""
        # Typically disposal ~5% of acquisition, offset by scrap
        return acquisition_cost * 0.02  # Net cost
