"""
Weight Item Data Structures

Module 07 v1.1 - Weight Estimation Framework

Core data structures for SWBS-based weight estimation:
- SWBSGroup: Ship Work Breakdown Structure group enumeration
- WeightConfidence: Confidence level for weight estimates
- WeightItem: Individual weight item with position and metadata
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class SWBSGroup(Enum):
    """
    Ship Work Breakdown Structure (SWBS) weight groups.

    Standard SWBS groups for naval and commercial vessel weight estimation.
    """
    GROUP_100 = 100  # Hull Structure
    GROUP_200 = 200  # Propulsion Plant
    GROUP_300 = 300  # Electrical Plant
    GROUP_400 = 400  # Command & Surveillance
    GROUP_500 = 500  # Auxiliary Systems
    GROUP_600 = 600  # Outfit & Furnishings
    GROUP_700 = 700  # Armament (if applicable)
    MARGIN = 999     # Design and growth margins


# Human-readable names for SWBS groups
SWBS_GROUP_NAMES: Dict[SWBSGroup, str] = {
    SWBSGroup.GROUP_100: "Hull Structure",
    SWBSGroup.GROUP_200: "Propulsion Plant",
    SWBSGroup.GROUP_300: "Electrical Plant",
    SWBSGroup.GROUP_400: "Command & Surveillance",
    SWBSGroup.GROUP_500: "Auxiliary Systems",
    SWBSGroup.GROUP_600: "Outfit & Furnishings",
    SWBSGroup.GROUP_700: "Armament",
    SWBSGroup.MARGIN: "Design/Growth Margin",
}


class WeightConfidence(Enum):
    """
    Confidence level for weight estimates.

    Higher values indicate more reliable estimates (e.g., from vendor data).
    Lower values indicate parametric estimates with more uncertainty.
    """
    VERY_LOW = 0.3   # Rough parametric estimate
    LOW = 0.5        # Parametric estimate
    MEDIUM = 0.7     # Based on similar vessels
    HIGH = 0.85      # Vendor quote or calculation
    VERY_HIGH = 0.95 # Measured or confirmed


@dataclass
class WeightItem:
    """
    Individual weight item with position and metadata.

    All weights in kilograms, positions in meters.
    Positions are from standard reference points:
    - LCG: from forward perpendicular (FP), positive aft
    - VCG: from baseline (keel), positive up
    - TCG: from centerline, positive to starboard

    Attributes:
        name: Descriptive name for the item
        weight_kg: Weight in kilograms
        lcg_m: Longitudinal center of gravity from FP (meters)
        vcg_m: Vertical center of gravity from baseline (meters)
        tcg_m: Transverse center of gravity from centerline (meters)
        group: SWBS group this item belongs to
        subgroup: Subgroup number within the SWBS group (e.g., 110, 120)
        confidence: Confidence level of the estimate
        notes: Optional notes or source information
    """
    name: str
    weight_kg: float
    lcg_m: float
    vcg_m: float
    tcg_m: float = 0.0  # Default to centerline
    group: SWBSGroup = SWBSGroup.GROUP_100
    subgroup: Optional[int] = None
    confidence: WeightConfidence = WeightConfidence.MEDIUM
    notes: Optional[str] = None

    @property
    def weight_mt(self) -> float:
        """Weight in metric tons."""
        return self.weight_kg / 1000.0

    @property
    def lcg_moment_kg_m(self) -> float:
        """LCG moment (weight × LCG) in kg-m."""
        return self.weight_kg * self.lcg_m

    @property
    def vcg_moment_kg_m(self) -> float:
        """VCG moment (weight × VCG) in kg-m."""
        return self.weight_kg * self.vcg_m

    @property
    def tcg_moment_kg_m(self) -> float:
        """TCG moment (weight × TCG) in kg-m."""
        return self.weight_kg * self.tcg_m

    @property
    def group_number(self) -> int:
        """SWBS group number."""
        return self.group.value

    @property
    def confidence_value(self) -> float:
        """Numeric confidence value (0-1)."""
        return self.confidence.value

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "weight_kg": self.weight_kg,
            "weight_mt": self.weight_mt,
            "lcg_m": self.lcg_m,
            "vcg_m": self.vcg_m,
            "tcg_m": self.tcg_m,
            "group": self.group.value,
            "group_name": SWBS_GROUP_NAMES.get(self.group, "Unknown"),
            "subgroup": self.subgroup,
            "confidence": self.confidence.value,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeightItem":
        """Deserialize from dictionary."""
        # Handle group as int or enum
        group_val = data.get("group", 100)
        if isinstance(group_val, int):
            group = SWBSGroup(group_val)
        elif isinstance(group_val, SWBSGroup):
            group = group_val
        else:
            group = SWBSGroup.GROUP_100

        # Handle confidence as float or enum
        conf_val = data.get("confidence", 0.7)
        if isinstance(conf_val, float):
            # Find closest confidence level
            confidence = min(
                WeightConfidence,
                key=lambda c: abs(c.value - conf_val)
            )
        elif isinstance(conf_val, WeightConfidence):
            confidence = conf_val
        else:
            confidence = WeightConfidence.MEDIUM

        return cls(
            name=data.get("name", "Unknown"),
            weight_kg=data.get("weight_kg", 0.0),
            lcg_m=data.get("lcg_m", 0.0),
            vcg_m=data.get("vcg_m", 0.0),
            tcg_m=data.get("tcg_m", 0.0),
            group=group,
            subgroup=data.get("subgroup"),
            confidence=confidence,
            notes=data.get("notes"),
        )


def create_weight_item(
    name: str,
    weight_kg: float,
    lcg_m: float,
    vcg_m: float,
    group: SWBSGroup,
    subgroup: Optional[int] = None,
    tcg_m: float = 0.0,
    confidence: WeightConfidence = WeightConfidence.MEDIUM,
    notes: Optional[str] = None,
) -> WeightItem:
    """
    Factory function to create a WeightItem.

    Provides validation and default handling.
    """
    if weight_kg < 0:
        raise ValueError(f"Weight cannot be negative: {weight_kg}")

    return WeightItem(
        name=name,
        weight_kg=weight_kg,
        lcg_m=lcg_m,
        vcg_m=vcg_m,
        tcg_m=tcg_m,
        group=group,
        subgroup=subgroup,
        confidence=confidence,
        notes=notes,
    )


@dataclass
class GroupSummary:
    """
    Summary for one SWBS weight group.

    Aggregates all items in a group into total weight and average centers.
    """
    group: SWBSGroup
    name: str
    total_weight_mt: float
    lcg_m: float
    vcg_m: float
    tcg_m: float
    item_count: int
    average_confidence: float

    @classmethod
    def from_items(cls, group: SWBSGroup, items: List[WeightItem]) -> "GroupSummary":
        """
        Create GroupSummary from list of WeightItems.

        Args:
            group: SWBS group
            items: List of WeightItem belonging to this group

        Returns:
            GroupSummary with aggregated values
        """
        if not items:
            return cls(
                group=group,
                name=SWBS_GROUP_NAMES.get(group, f"Group {group.value}"),
                total_weight_mt=0.0,
                lcg_m=0.0,
                vcg_m=0.0,
                tcg_m=0.0,
                item_count=0,
                average_confidence=0.0,
            )

        total_weight_kg = sum(item.weight_kg for item in items)
        total_weight_mt = total_weight_kg / 1000.0

        # Weight-averaged centers
        if total_weight_kg > 0:
            lcg_m = sum(item.weight_kg * item.lcg_m for item in items) / total_weight_kg
            vcg_m = sum(item.weight_kg * item.vcg_m for item in items) / total_weight_kg
            tcg_m = sum(item.weight_kg * item.tcg_m for item in items) / total_weight_kg
        else:
            lcg_m = 0.0
            vcg_m = 0.0
            tcg_m = 0.0

        # Average confidence
        confidences = [item.confidence_value for item in items]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return cls(
            group=group,
            name=SWBS_GROUP_NAMES.get(group, f"Group {group.value}"),
            total_weight_mt=total_weight_mt,
            lcg_m=lcg_m,
            vcg_m=vcg_m,
            tcg_m=tcg_m,
            item_count=len(items),
            average_confidence=avg_confidence,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "group": self.group.value,
            "name": self.name,
            "total_weight_mt": self.total_weight_mt,
            "lcg_m": self.lcg_m,
            "vcg_m": self.vcg_m,
            "tcg_m": self.tcg_m,
            "item_count": self.item_count,
            "average_confidence": self.average_confidence,
        }
