"""
outfitting/spaces.py - Accommodation space definitions
ALPHA OWNS THIS FILE.

Section 31: Outfitting & Accommodation
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class AccommodationSpace:
    """Accommodation space definition."""

    space_id: str = ""
    space_name: str = ""
    space_type: str = "crew_cabin"

    length_m: float = 0.0
    width_m: float = 0.0
    height_m: float = 2.1

    @property
    def area_m2(self) -> float:
        return self.length_m * self.width_m

    @property
    def volume_m3(self) -> float:
        return self.area_m2 * self.height_m

    deck: str = "main"
    frame_start: int = 0
    frame_end: int = 0

    design_occupancy: int = 0
    berths: int = 0

    min_area_per_person_m2: float = 3.5
    min_headroom_m: float = 1.98

    @property
    def compliant(self) -> bool:
        if self.design_occupancy <= 0:
            return True
        area_per_person = self.area_m2 / self.design_occupancy
        return (area_per_person >= self.min_area_per_person_m2 and
                self.height_m >= self.min_headroom_m)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "space_id": self.space_id,
            "space_name": self.space_name,
            "space_type": self.space_type,
            "area_m2": round(self.area_m2, 2),
            "volume_m3": round(self.volume_m3, 2),
            "deck": self.deck,
            "design_occupancy": self.design_occupancy,
            "berths": self.berths,
            "compliant": self.compliant,
        }


# HSC Code Space Requirements
SPACE_REQUIREMENTS = {
    "crew_cabin": {"min_area_pp": 3.5, "min_headroom": 1.98},
    "officer_cabin": {"min_area_pp": 5.5, "min_headroom": 1.98},
    "passenger_cabin": {"min_area_pp": 2.5, "min_headroom": 1.98},
    "passenger_saloon": {"seat_pitch_mm": 750, "min_headroom": 2.0},
    "mess": {"min_area_pp": 1.0, "min_headroom": 2.0},
    "galley": {"min_area": 4.0, "min_headroom": 2.0},
    "head": {"min_area": 1.5, "min_headroom": 1.98},
    "wheelhouse": {"min_headroom": 2.1},
}
