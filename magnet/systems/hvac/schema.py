"""
systems/hvac/schema.py - HVAC system data structures.

BRAVO OWNS THIS FILE.

Module 28 v1.0 - HVAC Schema.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class HVACZoneType(Enum):
    """HVAC zone types."""
    BRIDGE = "bridge"
    ACCOMMODATION = "accommodation"
    ENGINE_ROOM = "engine_room"
    CARGO = "cargo"
    GALLEY = "galley"
    MACHINERY = "machinery"
    ELECTRONICS = "electronics"
    PASSENGER = "passenger"


@dataclass
class HVACZone:
    """HVAC zone definition."""

    zone_id: str = ""
    """Unique zone identifier."""

    zone_type: HVACZoneType = HVACZoneType.ACCOMMODATION
    """Zone type classification."""

    zone_name: str = ""
    """Human-readable zone name."""

    # === DIMENSIONS ===
    volume_m3: float = 0.0
    """Zone volume (m^3)."""

    floor_area_m2: float = 0.0
    """Zone floor area (m^2)."""

    # === DESIGN CONDITIONS ===
    design_temp_c: float = 22.0
    """Design temperature (C)."""

    design_humidity_pct: float = 50.0
    """Design relative humidity (%)."""

    occupancy: int = 0
    """Design occupancy (persons)."""

    # === AIR CHANGES ===
    min_air_changes_per_hour: float = 6.0
    """Minimum air changes per hour."""

    # === CALCULATED LOADS ===
    sensible_load_kw: float = 0.0
    """Sensible heat load (kW)."""

    latent_load_kw: float = 0.0
    """Latent heat load (kW)."""

    @property
    def total_load_kw(self) -> float:
        """Total cooling/heating load."""
        return self.sensible_load_kw + self.latent_load_kw

    @property
    def required_airflow_m3h(self) -> float:
        """Required airflow based on air changes."""
        return self.volume_m3 * self.min_air_changes_per_hour

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "zone_type": self.zone_type.value,
            "zone_name": self.zone_name,
            "volume_m3": round(self.volume_m3, 1),
            "floor_area_m2": round(self.floor_area_m2, 1),
            "design_temp_c": self.design_temp_c,
            "occupancy": self.occupancy,
            "total_load_kw": round(self.total_load_kw, 2),
            "required_airflow_m3h": round(self.required_airflow_m3h, 0),
        }


@dataclass
class ACUnit:
    """Air conditioning unit specification."""

    unit_id: str = ""
    """Unique unit identifier."""

    unit_type: str = "split"
    """Unit type: split, packaged, chiller."""

    cooling_capacity_kw: float = 0.0
    """Cooling capacity (kW)."""

    heating_capacity_kw: float = 0.0
    """Heating capacity (kW)."""

    airflow_m3h: float = 0.0
    """Airflow rate (m^3/h)."""

    power_consumption_kw: float = 0.0
    """Electrical power consumption (kW)."""

    refrigerant: str = "R410A"
    """Refrigerant type."""

    zones_served: List[str] = field(default_factory=list)
    """List of zone IDs served."""

    @property
    def cop(self) -> float:
        """Coefficient of performance."""
        if self.power_consumption_kw > 0:
            return self.cooling_capacity_kw / self.power_consumption_kw
        return 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "unit_type": self.unit_type,
            "cooling_capacity_kw": round(self.cooling_capacity_kw, 2),
            "heating_capacity_kw": round(self.heating_capacity_kw, 2),
            "airflow_m3h": round(self.airflow_m3h, 0),
            "power_consumption_kw": round(self.power_consumption_kw, 2),
            "cop": round(self.cop, 2),
            "zones_served": self.zones_served,
        }


@dataclass
class VentilationFan:
    """Ventilation fan specification."""

    fan_id: str = ""
    """Unique fan identifier."""

    fan_type: str = "supply"
    """Fan type: supply, exhaust, recirculation."""

    airflow_m3h: float = 0.0
    """Airflow rate (m^3/h)."""

    static_pressure_pa: float = 250.0
    """Static pressure (Pa)."""

    power_kw: float = 0.0
    """Motor power (kW)."""

    zone_id: str = ""
    """Zone served."""

    is_explosion_proof: bool = False
    """Whether fan is explosion-proof (for machinery spaces)."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fan_id": self.fan_id,
            "fan_type": self.fan_type,
            "airflow_m3h": round(self.airflow_m3h, 0),
            "static_pressure_pa": self.static_pressure_pa,
            "power_kw": round(self.power_kw, 2),
            "zone_id": self.zone_id,
            "is_explosion_proof": self.is_explosion_proof,
        }


@dataclass
class HVACSystem:
    """Complete HVAC system definition."""

    system_id: str = ""
    """System identifier."""

    zones: List[HVACZone] = field(default_factory=list)
    """All HVAC zones."""

    ac_units: List[ACUnit] = field(default_factory=list)
    """Air conditioning units."""

    fans: List[VentilationFan] = field(default_factory=list)
    """Ventilation fans."""

    # === TOTALS ===
    total_cooling_capacity_kw: float = 0.0
    """Total installed cooling capacity."""

    total_heating_capacity_kw: float = 0.0
    """Total installed heating capacity."""

    total_power_kw: float = 0.0
    """Total HVAC electrical load."""

    def calculate_totals(self) -> None:
        """Calculate system totals."""
        self.total_cooling_capacity_kw = sum(u.cooling_capacity_kw for u in self.ac_units)
        self.total_heating_capacity_kw = sum(u.heating_capacity_kw for u in self.ac_units)
        self.total_power_kw = (
            sum(u.power_consumption_kw for u in self.ac_units) +
            sum(f.power_kw for f in self.fans)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_id": self.system_id,
            "zones": [z.to_dict() for z in self.zones],
            "ac_units": [u.to_dict() for u in self.ac_units],
            "fans": [f.to_dict() for f in self.fans],
            "total_cooling_capacity_kw": round(self.total_cooling_capacity_kw, 1),
            "total_heating_capacity_kw": round(self.total_heating_capacity_kw, 1),
            "total_power_kw": round(self.total_power_kw, 2),
        }
