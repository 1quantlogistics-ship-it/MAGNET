"""
weight/summary.py - Complete weight summary
ALPHA OWNS THIS FILE.

Section 36: Weight Summary & Centers
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .items import WeightItem, SWBSGroup, SWBS_GROUP_NAMES
from .loading import LoadingCondition


@dataclass
class WeightGroup:
    """SWBS weight group summary."""

    group_id: str = ""
    group_name: str = ""

    items: List[WeightItem] = field(default_factory=list)

    @property
    def total_weight_kg(self) -> float:
        return sum(item.weight_kg for item in self.items)

    @property
    def lcg_m(self) -> float:
        total = self.total_weight_kg
        if total <= 0:
            return 0.0
        return sum(item.weight_kg * item.lcg_m for item in self.items) / total

    @property
    def vcg_m(self) -> float:
        total = self.total_weight_kg
        if total <= 0:
            return 0.0
        return sum(item.weight_kg * item.vcg_m for item in self.items) / total

    @property
    def tcg_m(self) -> float:
        total = self.total_weight_kg
        if total <= 0:
            return 0.0
        return sum(item.weight_kg * item.tcg_m for item in self.items) / total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "group_name": self.group_name,
            "total_weight_kg": round(self.total_weight_kg, 0),
            "lcg_m": round(self.lcg_m, 3),
            "vcg_m": round(self.vcg_m, 3),
            "item_count": len(self.items),
        }


# SWBS Group Definitions for summary
SWBS_DEFINITIONS: Dict[str, str] = {
    "100": "Hull Structure",
    "200": "Propulsion Plant",
    "300": "Electric Plant",
    "400": "Command & Surveillance",
    "500": "Auxiliary Systems",
    "600": "Outfit & Furnishings",
    "700": "Armament (N/A)",
}


@dataclass
class WeightMargins:
    """Design and growth margins."""

    design_margin_percent: float = 5.0
    growth_margin_percent: float = 10.0
    contract_margin_percent: float = 3.0

    def apply_to_lightship(self, base_kg: float) -> float:
        return base_kg * (1 + self.design_margin_percent / 100)


@dataclass
class WeightSummary:
    """Complete weight summary."""

    summary_id: str = ""

    groups: Dict[str, WeightGroup] = field(default_factory=dict)
    margins: WeightMargins = field(default_factory=WeightMargins)

    lightship_base_kg: float = 0.0
    lightship_with_margin_kg: float = 0.0
    lightship_lcg_m: float = 0.0
    lightship_vcg_m: float = 0.0
    lightship_tcg_m: float = 0.0

    conditions: List[LoadingCondition] = field(default_factory=list)

    target_displacement_kg: float = 0.0
    weight_difference_kg: float = 0.0
    weight_difference_percent: float = 0.0

    def calculate_lightship(self) -> None:
        """Calculate lightship weight and centers from groups."""
        lightship_groups = ["100", "200", "300", "400", "500", "600", "700"]

        total_weight = 0.0
        total_moment_long = 0.0
        total_moment_vert = 0.0
        total_moment_trans = 0.0

        for gid in lightship_groups:
            if gid in self.groups:
                g = self.groups[gid]
                total_weight += g.total_weight_kg
                total_moment_long += g.total_weight_kg * g.lcg_m
                total_moment_vert += g.total_weight_kg * g.vcg_m
                total_moment_trans += g.total_weight_kg * g.tcg_m

        self.lightship_base_kg = total_weight
        self.lightship_with_margin_kg = self.margins.apply_to_lightship(total_weight)

        if total_weight > 0:
            self.lightship_lcg_m = total_moment_long / total_weight
            self.lightship_vcg_m = total_moment_vert / total_weight
            self.lightship_tcg_m = total_moment_trans / total_weight

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_id": self.summary_id,
            "groups": {k: v.to_dict() for k, v in self.groups.items()},
            "lightship_base_kg": round(self.lightship_base_kg, 0),
            "lightship_with_margin_kg": round(self.lightship_with_margin_kg, 0),
            "lightship_lcg_m": round(self.lightship_lcg_m, 3),
            "lightship_vcg_m": round(self.lightship_vcg_m, 3),
            "conditions": [c.to_dict() for c in self.conditions],
            "weight_difference_percent": round(self.weight_difference_percent, 1),
        }
