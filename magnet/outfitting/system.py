"""
outfitting/system.py - Complete outfitting system definition
ALPHA OWNS THIS FILE.

Section 31: Outfitting & Accommodation
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .spaces import AccommodationSpace
from .openings import Door, Window


@dataclass
class OutfittingSystem:
    """Complete outfitting system."""

    system_id: str = ""

    spaces: List[AccommodationSpace] = field(default_factory=list)
    furniture: List[Dict[str, Any]] = field(default_factory=list)
    fixtures: List[Dict[str, Any]] = field(default_factory=list)
    doors: List[Door] = field(default_factory=list)
    windows: List[Window] = field(default_factory=list)

    total_area_m2: float = 0.0
    total_berths: int = 0
    total_heads: int = 0
    furniture_weight_kg: float = 0.0
    fixture_weight_kg: float = 0.0
    door_weight_kg: float = 0.0
    window_weight_kg: float = 0.0

    @property
    def total_weight_kg(self) -> float:
        return (self.furniture_weight_kg + self.fixture_weight_kg +
                self.door_weight_kg + self.window_weight_kg)

    def calculate_totals(self) -> None:
        """Calculate system totals."""
        self.total_area_m2 = sum(s.area_m2 for s in self.spaces)
        self.total_berths = sum(s.berths for s in self.spaces)
        self.total_heads = sum(1 for s in self.spaces if s.space_type == "head")

        self.door_weight_kg = sum(d.weight_kg for d in self.doors)
        self.window_weight_kg = sum(w.weight_kg for w in self.windows)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_id": self.system_id,
            "spaces": [s.to_dict() for s in self.spaces],
            "furniture": self.furniture,
            "fixtures": self.fixtures,
            "doors": [d.to_dict() for d in self.doors],
            "windows": [w.to_dict() for w in self.windows],
            "total_area_m2": round(self.total_area_m2, 1),
            "total_berths": self.total_berths,
            "total_heads": self.total_heads,
            "total_weight_kg": round(self.total_weight_kg, 0),
        }
