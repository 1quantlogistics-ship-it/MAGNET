"""
systems/fuel/schema.py - Fuel system data structures.

BRAVO OWNS THIS FILE.

Module 29 v1.1 - Fuel Schema.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class TankType(Enum):
    """Tank types."""
    FUEL_SERVICE = "fuel_service"
    FUEL_STORAGE = "fuel_storage"
    FUEL_DAY = "fuel_day"
    LUBE_OIL = "lube_oil"
    FRESH_WATER = "fresh_water"
    GREY_WATER = "grey_water"
    BLACK_WATER = "black_water"
    BILGE = "bilge"
    BALLAST = "ballast"
    HYDRAULIC = "hydraulic"


class FluidType(Enum):
    """Fluid types."""
    MGO = "mgo"              # Marine Gas Oil
    MDO = "mdo"              # Marine Diesel Oil
    HFO = "hfo"              # Heavy Fuel Oil
    LUBE_OIL = "lube_oil"
    HYDRAULIC_OIL = "hydraulic_oil"
    FRESH_WATER = "fresh_water"
    SEA_WATER = "sea_water"
    GREY_WATER = "grey_water"
    BLACK_WATER = "black_water"


@dataclass
class Tank:
    """Tank definition."""

    tank_id: str = ""
    """Unique tank identifier."""

    tank_type: TankType = TankType.FUEL_STORAGE
    """Tank type classification."""

    tank_name: str = ""
    """Human-readable tank name."""

    fluid_type: FluidType = FluidType.MGO
    """Type of fluid stored."""

    # === GEOMETRY ===
    capacity_m3: float = 0.0
    """Total tank capacity (m^3)."""

    usable_capacity_m3: float = 0.0
    """Usable capacity accounting for sounding pipes, etc. (m^3)."""

    # === POSITION ===
    x_position: float = 0.0
    """Longitudinal position of centroid (m from AP)."""

    y_position: float = 0.0
    """Transverse position of centroid (m from CL)."""

    z_position: float = 0.0
    """Vertical position of centroid (m from baseline)."""

    # === STRUCTURAL ===
    frame_start: int = 0
    """Starting frame."""

    frame_end: int = 0
    """Ending frame."""

    is_integral: bool = True
    """Whether tank is integral (part of hull) or independent."""

    # === OPERATIONAL ===
    fill_level_pct: float = 100.0
    """Current fill level (%)."""

    @property
    def current_volume_m3(self) -> float:
        """Current fluid volume."""
        return self.usable_capacity_m3 * self.fill_level_pct / 100

    @property
    def weight_kg(self) -> float:
        """Current fluid weight (approximate)."""
        # Density varies by fluid type
        densities = {
            FluidType.MGO: 850,
            FluidType.MDO: 870,
            FluidType.HFO: 980,
            FluidType.LUBE_OIL: 900,
            FluidType.HYDRAULIC_OIL: 870,
            FluidType.FRESH_WATER: 1000,
            FluidType.SEA_WATER: 1025,
            FluidType.GREY_WATER: 1000,
            FluidType.BLACK_WATER: 1020,
        }
        density = densities.get(self.fluid_type, 850)
        return self.current_volume_m3 * density

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tank_id": self.tank_id,
            "tank_type": self.tank_type.value,
            "tank_name": self.tank_name,
            "fluid_type": self.fluid_type.value,
            "capacity_m3": round(self.capacity_m3, 2),
            "usable_capacity_m3": round(self.usable_capacity_m3, 2),
            "x_position": round(self.x_position, 2),
            "y_position": round(self.y_position, 2),
            "z_position": round(self.z_position, 2),
            "fill_level_pct": round(self.fill_level_pct, 1),
            "weight_kg": round(self.weight_kg, 0),
        }


@dataclass
class Pump:
    """Pump definition."""

    pump_id: str = ""
    """Unique pump identifier."""

    pump_type: str = "transfer"
    """Pump type: transfer, service, emergency, stripping."""

    fluid_type: FluidType = FluidType.MGO
    """Fluid handled."""

    # === PERFORMANCE ===
    flow_rate_m3h: float = 0.0
    """Flow rate (m^3/h)."""

    head_m: float = 20.0
    """Discharge head (m)."""

    power_kw: float = 0.0
    """Motor power (kW)."""

    # === SOURCE/DESTINATION ===
    source_tanks: List[str] = field(default_factory=list)
    """Source tank IDs."""

    destination_tanks: List[str] = field(default_factory=list)
    """Destination tank IDs."""

    is_redundant: bool = False
    """Whether this is a backup pump."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pump_id": self.pump_id,
            "pump_type": self.pump_type,
            "fluid_type": self.fluid_type.value,
            "flow_rate_m3h": round(self.flow_rate_m3h, 2),
            "head_m": self.head_m,
            "power_kw": round(self.power_kw, 2),
            "source_tanks": self.source_tanks,
            "destination_tanks": self.destination_tanks,
        }


@dataclass
class FuelSystem:
    """Complete fuel system definition."""

    system_id: str = ""
    """System identifier."""

    tanks: List[Tank] = field(default_factory=list)
    """All tanks."""

    pumps: List[Pump] = field(default_factory=list)
    """All pumps."""

    # === CAPACITIES ===
    total_fuel_capacity_m3: float = 0.0
    """Total fuel storage capacity."""

    total_fresh_water_m3: float = 0.0
    """Total fresh water capacity."""

    total_lube_oil_m3: float = 0.0
    """Total lube oil capacity."""

    # === CONSUMPTION ===
    fuel_consumption_rate_lph: float = 0.0
    """Design fuel consumption rate (L/h)."""

    endurance_hours: float = 0.0
    """Endurance at design consumption."""

    def calculate_totals(self) -> None:
        """Calculate system totals."""
        self.total_fuel_capacity_m3 = sum(
            t.usable_capacity_m3 for t in self.tanks
            if t.tank_type in [TankType.FUEL_SERVICE, TankType.FUEL_STORAGE, TankType.FUEL_DAY]
        )
        self.total_fresh_water_m3 = sum(
            t.usable_capacity_m3 for t in self.tanks
            if t.tank_type == TankType.FRESH_WATER
        )
        self.total_lube_oil_m3 = sum(
            t.usable_capacity_m3 for t in self.tanks
            if t.tank_type == TankType.LUBE_OIL
        )

        if self.fuel_consumption_rate_lph > 0:
            self.endurance_hours = (self.total_fuel_capacity_m3 * 1000) / self.fuel_consumption_rate_lph

    def get_tanks_by_type(self, tank_type: TankType) -> List[Tank]:
        """Get all tanks of a specific type."""
        return [t for t in self.tanks if t.tank_type == tank_type]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_id": self.system_id,
            "tanks": [t.to_dict() for t in self.tanks],
            "pumps": [p.to_dict() for p in self.pumps],
            "total_fuel_capacity_m3": round(self.total_fuel_capacity_m3, 2),
            "total_fresh_water_m3": round(self.total_fresh_water_m3, 2),
            "total_lube_oil_m3": round(self.total_lube_oil_m3, 2),
            "endurance_hours": round(self.endurance_hours, 1),
        }
