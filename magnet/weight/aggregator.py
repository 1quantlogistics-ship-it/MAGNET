"""
MAGNET Weight Aggregator

Module 07 v1.1 - Production-Ready

Aggregates weight items from all SWBS groups and calculates lightship summary.

v1.1 FIX #5: Uniform margin approach documented (group-specific in V2).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

from .groups import SWBSGroup, WeightItem, GroupSummary, SWBS_GROUP_NAMES
from .utils import determinize_dict

logger = logging.getLogger(__name__)


# =============================================================================
# MARGIN CONSTANTS
# =============================================================================

# v1.1 FIX #5: Uniform margin approach
# Current implementation uses a single margin percentage for all groups.
# Group-specific margins will be introduced in V2.
DEFAULT_MARGIN_PERCENT = 0.10  # 10% of base weight
DEFAULT_MARGIN_VCG_FACTOR = 1.05  # Margin weight at elevated VCG

# Vessel-type margin adjustments
VESSEL_TYPE_MARGINS = {
    "patrol": 0.08,      # Well-defined requirements
    "crew_boat": 0.10,   # Standard commercial
    "ferry": 0.10,       # Standard commercial
    "research": 0.12,    # Variable mission equipment
    "yacht": 0.15,       # Custom fit-out variability
    "workboat": 0.10,    # Standard commercial
    "pilot_boat": 0.08,  # Well-defined requirements
}


# =============================================================================
# LIGHTSHIP SUMMARY DATACLASS
# =============================================================================

@dataclass
class LightshipSummary:
    """
    Complete lightship weight summary with SWBS breakdown.

    All weights in metric tons (MT), distances in meters (m).

    LCG Convention: From forward perpendicular (FP), positive aft
    VCG Convention: From baseline, positive up
    TCG Convention: From centerline, positive starboard
    """
    # Total lightship values (including margins)
    lightship_weight_mt: float
    lightship_lcg_m: float
    lightship_vcg_m: float
    lightship_tcg_m: float

    # Margin details
    margin_weight_mt: float
    margin_vcg_m: float
    margin_percent: float

    # Base weight (before margins)
    base_weight_mt: float
    base_lcg_m: float
    base_vcg_m: float
    base_tcg_m: float

    # Group summaries
    group_summaries: Dict[SWBSGroup, GroupSummary]

    # All weight items
    items: List[WeightItem]

    # Statistics
    average_confidence: float
    total_item_count: int

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for state storage.

        v1.1 FIX #6: Uses determinize_dict for hash-stable output.
        """
        group_data = {}
        for group, summary in self.group_summaries.items():
            group_data[f"group_{group.value}"] = {
                "name": summary.name,
                "weight_mt": summary.total_weight_mt,
                "lcg_m": summary.lcg_m,
                "vcg_m": summary.vcg_m,
                "tcg_m": summary.tcg_m,
                "item_count": summary.item_count,
                "confidence": summary.average_confidence,
            }

        result = {
            "lightship": {
                "weight_mt": self.lightship_weight_mt,
                "lcg_m": self.lightship_lcg_m,
                "vcg_m": self.lightship_vcg_m,
                "tcg_m": self.lightship_tcg_m,
            },
            "base": {
                "weight_mt": self.base_weight_mt,
                "lcg_m": self.base_lcg_m,
                "vcg_m": self.base_vcg_m,
                "tcg_m": self.base_tcg_m,
            },
            "margin": {
                "weight_mt": self.margin_weight_mt,
                "vcg_m": self.margin_vcg_m,
                "percent": self.margin_percent,
            },
            "groups": group_data,
            "statistics": {
                "average_confidence": self.average_confidence,
                "total_item_count": self.total_item_count,
            },
        }

        return determinize_dict(result)

    def get_group_weight_mt(self, group: SWBSGroup) -> float:
        """Get weight for a specific SWBS group."""
        if group in self.group_summaries:
            return self.group_summaries[group].total_weight_mt
        return 0.0

    def get_group_percentage(self, group: SWBSGroup) -> float:
        """Get percentage contribution of a group to base weight."""
        if self.base_weight_mt <= 0:
            return 0.0
        return self.get_group_weight_mt(group) / self.base_weight_mt * 100


# =============================================================================
# WEIGHT AGGREGATOR
# =============================================================================

class WeightAggregator:
    """
    Aggregates weight items and calculates lightship.

    Usage:
        aggregator = WeightAggregator()
        aggregator.add_items(hull_items)
        aggregator.add_items(propulsion_items)
        # ... add items from all estimators
        aggregator.set_margins(vessel_type="patrol")
        summary = aggregator.calculate_lightship()

    v1.1 FIX #5:
        Current implementation applies uniform margins (group-specific in V2).
        The margin percentage is based on vessel type.
    """

    def __init__(self):
        """Initialize empty aggregator."""
        self._items: List[WeightItem] = []
        self._margin_percent: float = DEFAULT_MARGIN_PERCENT
        self._margin_vcg_factor: float = DEFAULT_MARGIN_VCG_FACTOR
        self._vessel_type: Optional[str] = None

    def add_item(self, item: WeightItem) -> None:
        """
        Add a single weight item.

        Args:
            item: WeightItem to add
        """
        self._items.append(item)

    def add_items(self, items: List[WeightItem]) -> None:
        """
        Add multiple weight items.

        Args:
            items: List of WeightItem to add
        """
        self._items.extend(items)

    def clear(self) -> None:
        """Clear all items."""
        self._items.clear()

    def set_margins(
        self,
        vessel_type: Optional[str] = None,
        margin_percent: Optional[float] = None,
        vcg_factor: Optional[float] = None,
    ) -> None:
        """
        Set margin parameters.

        Args:
            vessel_type: Vessel type for automatic margin selection
            margin_percent: Override margin percentage (0.0 to 1.0)
            vcg_factor: Override VCG factor for margin weight placement

        v1.1 FIX #5: Documents uniform margin approach.
        """
        self._vessel_type = vessel_type

        if margin_percent is not None:
            self._margin_percent = margin_percent
        elif vessel_type and vessel_type.lower() in VESSEL_TYPE_MARGINS:
            self._margin_percent = VESSEL_TYPE_MARGINS[vessel_type.lower()]
        else:
            self._margin_percent = DEFAULT_MARGIN_PERCENT

        if vcg_factor is not None:
            self._margin_vcg_factor = vcg_factor

        logger.debug(
            f"Margins set: {self._margin_percent*100:.1f}% "
            f"(vessel_type={vessel_type})"
        )

    def get_items_by_group(self, group: SWBSGroup) -> List[WeightItem]:
        """Get all items for a specific SWBS group."""
        return [item for item in self._items if item.group == group]

    def calculate_lightship(self) -> LightshipSummary:
        """
        Calculate complete lightship summary.

        Returns:
            LightshipSummary with all weights, centers, and statistics.

        Raises:
            ValueError: If no weight items have been added.
        """
        if not self._items:
            raise ValueError("No weight items added. Cannot calculate lightship.")

        # Calculate group summaries
        group_summaries: Dict[SWBSGroup, GroupSummary] = {}
        for group in SWBSGroup:
            group_items = self.get_items_by_group(group)
            if group_items:
                group_summaries[group] = GroupSummary.from_items(group, group_items)

        # Calculate base weight totals (before margins)
        base_weight_kg = sum(item.weight_kg for item in self._items)
        base_weight_mt = base_weight_kg / 1000.0

        # Calculate weighted centers for base weight
        if base_weight_kg > 0:
            base_lcg_m = sum(
                item.weight_kg * item.lcg_m for item in self._items
            ) / base_weight_kg
            base_vcg_m = sum(
                item.weight_kg * item.vcg_m for item in self._items
            ) / base_weight_kg
            base_tcg_m = sum(
                item.weight_kg * item.tcg_m for item in self._items
            ) / base_weight_kg
        else:
            base_lcg_m = 0.0
            base_vcg_m = 0.0
            base_tcg_m = 0.0

        # Calculate margins
        margin_weight_kg = base_weight_kg * self._margin_percent
        margin_weight_mt = margin_weight_kg / 1000.0

        # Margin VCG is elevated above base VCG
        margin_vcg_m = base_vcg_m * self._margin_vcg_factor

        # Calculate total lightship with margins
        lightship_weight_kg = base_weight_kg + margin_weight_kg
        lightship_weight_mt = lightship_weight_kg / 1000.0

        # Recalculate centers including margin
        if lightship_weight_kg > 0:
            # LCG: margin at same LCG as base
            lightship_lcg_m = (
                base_weight_kg * base_lcg_m + margin_weight_kg * base_lcg_m
            ) / lightship_weight_kg

            # VCG: margin at elevated VCG
            lightship_vcg_m = (
                base_weight_kg * base_vcg_m + margin_weight_kg * margin_vcg_m
            ) / lightship_weight_kg

            # TCG: margin at same TCG as base (should be ~0)
            lightship_tcg_m = (
                base_weight_kg * base_tcg_m + margin_weight_kg * base_tcg_m
            ) / lightship_weight_kg
        else:
            lightship_lcg_m = 0.0
            lightship_vcg_m = 0.0
            lightship_tcg_m = 0.0

        # Calculate statistics
        confidences = [item.confidence_value for item in self._items]
        average_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        summary = LightshipSummary(
            lightship_weight_mt=lightship_weight_mt,
            lightship_lcg_m=lightship_lcg_m,
            lightship_vcg_m=lightship_vcg_m,
            lightship_tcg_m=lightship_tcg_m,
            margin_weight_mt=margin_weight_mt,
            margin_vcg_m=margin_vcg_m,
            margin_percent=self._margin_percent,
            base_weight_mt=base_weight_mt,
            base_lcg_m=base_lcg_m,
            base_vcg_m=base_vcg_m,
            base_tcg_m=base_tcg_m,
            group_summaries=group_summaries,
            items=list(self._items),  # Copy to prevent modification
            average_confidence=average_confidence,
            total_item_count=len(self._items),
        )

        logger.info(
            f"Lightship calculated: {lightship_weight_mt:.2f} MT "
            f"(base: {base_weight_mt:.2f} MT + margin: {margin_weight_mt:.2f} MT)"
        )
        logger.debug(
            f"Centers: LCG={lightship_lcg_m:.2f}m, "
            f"VCG={lightship_vcg_m:.2f}m, TCG={lightship_tcg_m:.3f}m"
        )

        return summary

    @property
    def item_count(self) -> int:
        """Get total number of items."""
        return len(self._items)

    @property
    def total_weight_kg(self) -> float:
        """Get total weight in kg (base only, no margin)."""
        return sum(item.weight_kg for item in self._items)

    @property
    def total_weight_mt(self) -> float:
        """Get total weight in MT (base only, no margin)."""
        return self.total_weight_kg / 1000.0
