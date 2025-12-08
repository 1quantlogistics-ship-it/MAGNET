"""
systems/electrical/schema.py - Electrical system definitions
ALPHA OWNS THIS FILE.

Section 27: Electrical System
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List
from enum import Enum


class LoadCategory(Enum):
    """Electrical load categories."""
    PROPULSION = "propulsion"
    NAVIGATION = "navigation"
    COMMUNICATION = "communication"
    LIGHTING = "lighting"
    HVAC = "hvac"
    GALLEY = "galley"
    HOTEL = "hotel"
    SAFETY = "safety"
    AUXILIARY = "auxiliary"


class VoltageLevel(Enum):
    """Voltage levels."""
    LOW_24V = "24vdc"
    LOW_48V = "48vdc"
    MEDIUM_120V = "120vac"
    MEDIUM_230V = "230vac"
    HIGH_400V = "400vac"
    HIGH_690V = "690vac"


@dataclass
class ElectricalLoad:
    """Individual electrical load."""

    load_id: str = ""
    load_name: str = ""
    category: str = "auxiliary"

    rated_power_kw: float = 0.0
    running_power_kw: float = 0.0
    starting_power_kw: float = 0.0

    diversity_factor: float = 1.0
    demand_factor: float = 1.0

    voltage: str = "230vac"
    quantity: int = 1

    @property
    def connected_load_kw(self) -> float:
        return self.rated_power_kw * self.quantity

    @property
    def demand_load_kw(self) -> float:
        return self.running_power_kw * self.quantity * self.diversity_factor * self.demand_factor

    def to_dict(self) -> Dict[str, Any]:
        return {
            "load_id": self.load_id,
            "load_name": self.load_name,
            "category": self.category,
            "rated_power_kw": self.rated_power_kw,
            "running_power_kw": self.running_power_kw,
            "quantity": self.quantity,
            "connected_load_kw": round(self.connected_load_kw, 2),
            "demand_load_kw": round(self.demand_load_kw, 2),
        }


@dataclass
class GeneratorSet:
    """Generator set specification."""

    genset_id: str = ""
    manufacturer: str = ""
    model: str = ""

    prime_power_kw: float = 0.0
    standby_power_kw: float = 0.0
    power_factor: float = 0.8

    voltage_v: float = 400.0
    frequency_hz: float = 50.0
    phases: int = 3

    engine_power_kw: float = 0.0
    fuel_consumption_l_hr: float = 0.0

    weight_kg: float = 0.0
    length_mm: float = 0.0
    width_mm: float = 0.0
    height_mm: float = 0.0

    @classmethod
    def estimate_from_power(cls, required_kw: float) -> 'GeneratorSet':
        """Estimate generator from power requirement."""

        standard_sizes = [20, 30, 50, 75, 100, 150, 200, 300, 400, 500]
        prime_power = required_kw * 1.15

        selected_size = standard_sizes[0]
        for size in standard_sizes:
            if size >= prime_power:
                selected_size = size
                break
        else:
            selected_size = prime_power * 1.1

        fuel_rate = selected_size * 0.75 * 0.25
        weight = selected_size * 10 + 200

        return cls(
            genset_id=f"GEN-{int(selected_size)}KW",
            prime_power_kw=selected_size,
            standby_power_kw=selected_size * 1.1,
            power_factor=0.8,
            engine_power_kw=selected_size * 1.25,
            fuel_consumption_l_hr=fuel_rate,
            weight_kg=weight,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "genset_id": self.genset_id,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "prime_power_kw": self.prime_power_kw,
            "standby_power_kw": self.standby_power_kw,
            "voltage_v": self.voltage_v,
            "frequency_hz": self.frequency_hz,
            "fuel_consumption_l_hr": round(self.fuel_consumption_l_hr, 2),
            "weight_kg": round(self.weight_kg, 0),
        }


@dataclass
class BatteryBank:
    """Battery bank specification."""

    bank_id: str = ""
    battery_type: str = "agm"

    nominal_voltage_v: float = 24.0
    capacity_ah: float = 200.0

    @property
    def energy_kwh(self) -> float:
        return self.nominal_voltage_v * self.capacity_ah / 1000

    num_batteries: int = 1
    weight_per_battery_kg: float = 60.0

    @property
    def total_weight_kg(self) -> float:
        return self.num_batteries * self.weight_per_battery_kg

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bank_id": self.bank_id,
            "battery_type": self.battery_type,
            "nominal_voltage_v": self.nominal_voltage_v,
            "capacity_ah": self.capacity_ah,
            "energy_kwh": round(self.energy_kwh, 2),
            "num_batteries": self.num_batteries,
            "total_weight_kg": round(self.total_weight_kg, 1),
        }


@dataclass
class ElectricalSystem:
    """Complete electrical system definition."""

    system_id: str = ""

    loads: List[ElectricalLoad] = field(default_factory=list)
    generators: List[GeneratorSet] = field(default_factory=list)
    batteries: List[BatteryBank] = field(default_factory=list)

    shore_power_kw: float = 0.0
    shore_voltage_v: float = 400.0

    total_connected_load_kw: float = 0.0
    total_demand_load_kw: float = 0.0
    total_generation_kw: float = 0.0
    total_battery_kwh: float = 0.0
    total_weight_kg: float = 0.0

    def calculate_totals(self) -> None:
        """Calculate system totals."""
        self.total_connected_load_kw = sum(l.connected_load_kw for l in self.loads)
        self.total_demand_load_kw = sum(l.demand_load_kw for l in self.loads)
        self.total_generation_kw = sum(g.prime_power_kw for g in self.generators)
        self.total_battery_kwh = sum(b.energy_kwh for b in self.batteries)
        self.total_weight_kg = (
            sum(g.weight_kg for g in self.generators) +
            sum(b.total_weight_kg for b in self.batteries)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_id": self.system_id,
            "loads": [l.to_dict() for l in self.loads],
            "generators": [g.to_dict() for g in self.generators],
            "batteries": [b.to_dict() for b in self.batteries],
            "shore_power_kw": self.shore_power_kw,
            "total_connected_load_kw": round(self.total_connected_load_kw, 1),
            "total_demand_load_kw": round(self.total_demand_load_kw, 1),
            "total_generation_kw": round(self.total_generation_kw, 1),
            "total_battery_kwh": round(self.total_battery_kwh, 2),
            "total_weight_kg": round(self.total_weight_kg, 0),
        }
