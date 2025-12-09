"""
weight/loading.py - Loading condition definitions
ALPHA OWNS THIS FILE.

Section 36: Weight Summary & Centers
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class LoadingCondition:
    """Loading condition for stability analysis."""

    condition_id: str = ""
    condition_name: str = ""

    # Lightship
    lightship_kg: float = 0.0
    lightship_lcg_m: float = 0.0
    lightship_vcg_m: float = 0.0

    # Fuel
    fuel_kg: float = 0.0
    fuel_lcg_m: float = 0.0
    fuel_vcg_m: float = 0.0

    # Fresh water
    fresh_water_kg: float = 0.0
    fw_lcg_m: float = 0.0
    fw_vcg_m: float = 0.0

    # Stores
    stores_kg: float = 0.0
    stores_lcg_m: float = 0.0
    stores_vcg_m: float = 0.0

    # Crew
    crew_kg: float = 0.0
    crew_lcg_m: float = 0.0
    crew_vcg_m: float = 0.0

    # Passengers
    passengers_kg: float = 0.0
    pax_lcg_m: float = 0.0
    pax_vcg_m: float = 0.0

    # Cargo
    cargo_kg: float = 0.0
    cargo_lcg_m: float = 0.0
    cargo_vcg_m: float = 0.0

    # Internal tracking
    _full_fuel: float = 0.0

    @property
    def deadweight_kg(self) -> float:
        """Total deadweight (fuel + consumables + personnel + cargo)."""
        return (
            self.fuel_kg +
            self.fresh_water_kg +
            self.stores_kg +
            self.crew_kg +
            self.passengers_kg +
            self.cargo_kg
        )

    @property
    def displacement_kg(self) -> float:
        """Total displacement (lightship + deadweight)."""
        return self.lightship_kg + self.deadweight_kg

    @property
    def displacement_mt(self) -> float:
        """Displacement in metric tonnes."""
        return self.displacement_kg / 1000

    @property
    def lcg_m(self) -> float:
        """Combined longitudinal center of gravity."""
        total = self.displacement_kg
        if total <= 0:
            return 0.0
        moment = (
            self.lightship_kg * self.lightship_lcg_m +
            self.fuel_kg * self.fuel_lcg_m +
            self.fresh_water_kg * self.fw_lcg_m +
            self.stores_kg * self.stores_lcg_m +
            self.crew_kg * self.crew_lcg_m +
            self.passengers_kg * self.pax_lcg_m +
            self.cargo_kg * self.cargo_lcg_m
        )
        return moment / total

    @property
    def vcg_m(self) -> float:
        """Combined vertical center of gravity (KG)."""
        total = self.displacement_kg
        if total <= 0:
            return 0.0
        moment = (
            self.lightship_kg * self.lightship_vcg_m +
            self.fuel_kg * self.fuel_vcg_m +
            self.fresh_water_kg * self.fw_vcg_m +
            self.stores_kg * self.stores_vcg_m +
            self.crew_kg * self.crew_vcg_m +
            self.passengers_kg * self.pax_vcg_m +
            self.cargo_kg * self.cargo_vcg_m
        )
        return moment / total

    def to_dict(self) -> Dict[str, Any]:
        fuel_percent = 100
        if self._full_fuel > 0:
            fuel_percent = round(self.fuel_kg / self._full_fuel * 100, 0)
        return {
            "condition_id": self.condition_id,
            "condition_name": self.condition_name,
            "lightship_kg": round(self.lightship_kg, 0),
            "deadweight_kg": round(self.deadweight_kg, 0),
            "displacement_kg": round(self.displacement_kg, 0),
            "displacement_mt": round(self.displacement_mt, 2),
            "lcg_m": round(self.lcg_m, 3),
            "vcg_m": round(self.vcg_m, 3),
            "fuel_percent": fuel_percent,
        }


# Standard Loading Conditions
STANDARD_CONDITIONS: List[Dict[str, Any]] = [
    {"id": "FULL", "name": "Full Load Departure", "fuel": 1.0, "fw": 1.0, "stores": 1.0, "pax": 1.0},
    {"id": "HALF", "name": "Half Consumables", "fuel": 0.5, "fw": 0.5, "stores": 0.5, "pax": 1.0},
    {"id": "MIN", "name": "Minimum Operating", "fuel": 0.1, "fw": 0.1, "stores": 0.1, "pax": 0.0},
    {"id": "ARR", "name": "Arrival", "fuel": 0.1, "fw": 0.1, "stores": 0.1, "pax": 1.0},
    {"id": "LIGHT", "name": "Lightship", "fuel": 0.0, "fw": 0.0, "stores": 0.0, "pax": 0.0},
]
