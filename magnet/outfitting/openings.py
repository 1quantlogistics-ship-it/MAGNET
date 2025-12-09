"""
outfitting/openings.py - Door and window definitions
ALPHA OWNS THIS FILE.

Section 31: Outfitting & Accommodation
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Door:
    """Door specification."""

    door_id: str = ""
    door_type: str = "standard"

    width_mm: float = 700.0
    height_mm: float = 1900.0

    fire_rating_min: int = 0
    weight_kg: float = 0.0

    @classmethod
    def create(cls, door_type: str, door_id: str = "") -> 'Door':
        """Create door from type."""
        specs = {
            "watertight": {"width": 600, "height": 1800, "weight": 85},
            "weathertight": {"width": 700, "height": 1900, "weight": 45},
            "fire_rated": {"width": 800, "height": 2000, "weight": 55, "fire": 30},
            "standard": {"width": 700, "height": 1900, "weight": 25},
            "sliding": {"width": 900, "height": 2000, "weight": 35},
        }
        spec = specs.get(door_type, specs["standard"])
        return cls(
            door_id=door_id,
            door_type=door_type,
            width_mm=spec["width"],
            height_mm=spec["height"],
            fire_rating_min=spec.get("fire", 0),
            weight_kg=spec["weight"],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "door_id": self.door_id,
            "door_type": self.door_type,
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "fire_rating_min": self.fire_rating_min,
            "weight_kg": self.weight_kg,
        }


@dataclass
class Window:
    """Window specification."""

    window_id: str = ""
    window_type: str = "fixed"

    width_mm: float = 600.0
    height_mm: float = 400.0

    glass_type: str = "tempered"
    thickness_mm: float = 10.0

    weight_kg: float = 0.0

    @classmethod
    def create(cls, window_type: str, width: float, height: float, window_id: str = "") -> 'Window':
        """Create window with calculated properties."""
        area_m2 = (width / 1000) * (height / 1000)
        thickness = 10 if width < 800 else 12
        weight = area_m2 * thickness * 2.5 + 5

        return cls(
            window_id=window_id,
            window_type=window_type,
            width_mm=width,
            height_mm=height,
            thickness_mm=thickness,
            weight_kg=weight,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_id": self.window_id,
            "window_type": self.window_type,
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "thickness_mm": self.thickness_mm,
            "weight_kg": round(self.weight_kg, 1),
        }
