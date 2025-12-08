"""
systems/propulsion/system.py - Complete propulsion system definition
ALPHA OWNS THIS FILE.

Section 26: Propulsion System
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List
import math

from .engines import EngineSpecification
from .propulsors import PropellerSpecification, WaterjetSpecification


@dataclass
class GearboxSpecification:
    """Reduction gearbox specification."""

    gearbox_id: str = ""
    manufacturer: str = ""
    model: str = ""

    ratio: float = 1.0
    max_input_power_kw: float = 0.0
    max_input_rpm: float = 0.0

    weight_kg: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gearbox_id": self.gearbox_id,
            "ratio": round(self.ratio, 2),
            "max_input_power_kw": self.max_input_power_kw,
            "weight_kg": round(self.weight_kg, 0),
        }


@dataclass
class ShaftLine:
    """Shaft line specification."""

    shaft_id: str = ""

    diameter_mm: float = 0.0
    length_mm: float = 0.0
    material: str = "ss316"

    num_bearings: int = 2
    stern_tube_length_mm: float = 0.0

    weight_kg: float = 0.0

    @classmethod
    def estimate_from_power(
        cls,
        power_kw: float,
        rpm: float,
        length_m: float,
    ) -> 'ShaftLine':
        """Estimate shaft dimensions from power."""

        torque_nm = power_kw * 1000 * 60 / (2 * math.pi * rpm) if rpm > 0 else 0

        tau_allow = 50e6  # Allowable shear stress Pa for SS316
        d_m = 1.72 * (torque_nm / tau_allow) ** (1/3) if torque_nm > 0 else 0.08
        d_mm = d_m * 1000
        d_mm = max(60, min(d_mm, 300))

        volume_m3 = math.pi * (d_mm / 2000) ** 2 * length_m
        weight = volume_m3 * 7900

        return cls(
            shaft_id=f"SHAFT-{int(power_kw)}KW",
            diameter_mm=d_mm,
            length_mm=length_m * 1000,
            material="ss316",
            num_bearings=max(2, int(length_m / 2)),
            stern_tube_length_mm=d_mm * 8,
            weight_kg=weight,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shaft_id": self.shaft_id,
            "diameter_mm": round(self.diameter_mm, 0),
            "length_mm": round(self.length_mm, 0),
            "material": self.material,
            "weight_kg": round(self.weight_kg, 1),
        }


@dataclass
class PropulsionSystem:
    """Complete propulsion system definition."""

    system_id: str = ""

    num_engines: int = 2
    num_shafts: int = 2
    propulsor_type: str = "fpp"

    engines: List[EngineSpecification] = field(default_factory=list)
    gearboxes: List[GearboxSpecification] = field(default_factory=list)
    shafts: List[ShaftLine] = field(default_factory=list)
    propellers: List[PropellerSpecification] = field(default_factory=list)
    waterjets: List[WaterjetSpecification] = field(default_factory=list)

    total_installed_power_kw: float = 0.0
    total_service_power_kw: float = 0.0
    total_propulsion_weight_kg: float = 0.0

    fuel_rate_max_l_hr: float = 0.0
    fuel_rate_cruise_l_hr: float = 0.0

    def calculate_totals(self) -> None:
        """Calculate system totals."""
        self.total_installed_power_kw = sum(e.mcr_kw for e in self.engines)
        self.total_service_power_kw = sum(e.service_power_kw for e in self.engines)

        self.total_propulsion_weight_kg = (
            sum(e.wet_weight_kg for e in self.engines) +
            sum(g.weight_kg for g in self.gearboxes) +
            sum(s.weight_kg for s in self.shafts) +
            sum(p.weight_kg for p in self.propellers) +
            sum(w.dry_weight_kg for w in self.waterjets)
        )

        # v1.1 FIX: Write BOTH fuel rates
        self.fuel_rate_max_l_hr = sum(e.calculate_fuel_rate(e.mcr_kw) for e in self.engines)
        self.fuel_rate_cruise_l_hr = sum(e.calculate_fuel_rate(e.service_power_kw) for e in self.engines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_id": self.system_id,
            "num_engines": self.num_engines,
            "num_shafts": self.num_shafts,
            "propulsor_type": self.propulsor_type,
            "engines": [e.to_dict() for e in self.engines],
            "gearboxes": [g.to_dict() for g in self.gearboxes],
            "shafts": [s.to_dict() for s in self.shafts],
            "propellers": [p.to_dict() for p in self.propellers],
            "waterjets": [w.to_dict() for w in self.waterjets],
            "total_installed_power_kw": round(self.total_installed_power_kw, 0),
            "total_service_power_kw": round(self.total_service_power_kw, 0),
            "total_propulsion_weight_kg": round(self.total_propulsion_weight_kg, 0),
            "fuel_rate_max_l_hr": round(self.fuel_rate_max_l_hr, 1),
            "fuel_rate_cruise_l_hr": round(self.fuel_rate_cruise_l_hr, 1),
        }
