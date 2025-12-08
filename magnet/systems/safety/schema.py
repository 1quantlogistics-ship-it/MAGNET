"""
systems/safety/schema.py - Safety system data structures.

BRAVO OWNS THIS FILE.

Module 30 v1.0 - Safety Schema.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class FireZone(Enum):
    """Fire zone types per SOLAS."""
    ENGINE_ROOM = "engine_room"
    ACCOMMODATION = "accommodation"
    CARGO = "cargo"
    GALLEY = "galley"
    MACHINERY = "machinery"
    CONTROL = "control"
    SERVICE = "service"


class FirefightingAgent(Enum):
    """Firefighting agents."""
    WATER = "water"
    FOAM = "foam"
    CO2 = "co2"
    DRY_CHEMICAL = "dry_chemical"
    CLEAN_AGENT = "clean_agent"  # FM200, Novec, etc.


@dataclass
class FireZoneDefinition:
    """Fire zone definition."""

    zone_id: str = ""
    """Unique zone identifier."""

    zone_type: FireZone = FireZone.ACCOMMODATION
    """Fire zone classification."""

    zone_name: str = ""
    """Human-readable zone name."""

    # === DIMENSIONS ===
    volume_m3: float = 0.0
    """Zone volume (m^3)."""

    floor_area_m2: float = 0.0
    """Zone floor area (m^2)."""

    # === FIRE RATING ===
    fire_rating_minutes: int = 60
    """Fire rating of boundaries (minutes)."""

    has_a60_boundaries: bool = False
    """Whether zone has A-60 rated boundaries."""

    # === DETECTION ===
    has_smoke_detection: bool = True
    """Whether zone has smoke detectors."""

    has_heat_detection: bool = False
    """Whether zone has heat detectors."""

    detector_count: int = 0
    """Number of detectors."""

    # === SUPPRESSION ===
    suppression_agent: FirefightingAgent = FirefightingAgent.WATER
    """Primary suppression agent."""

    has_sprinklers: bool = False
    """Whether zone has automatic sprinklers."""

    has_fixed_system: bool = False
    """Whether zone has fixed firefighting system."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "zone_type": self.zone_type.value,
            "zone_name": self.zone_name,
            "volume_m3": round(self.volume_m3, 1),
            "fire_rating_minutes": self.fire_rating_minutes,
            "has_smoke_detection": self.has_smoke_detection,
            "has_sprinklers": self.has_sprinklers,
            "suppression_agent": self.suppression_agent.value,
        }


@dataclass
class FirePump:
    """Fire pump specification."""

    pump_id: str = ""
    """Unique pump identifier."""

    pump_type: str = "main"
    """Pump type: main, emergency, portable."""

    # === PERFORMANCE ===
    capacity_m3h: float = 0.0
    """Pump capacity (m^3/h)."""

    pressure_bar: float = 7.0
    """Discharge pressure (bar)."""

    power_kw: float = 0.0
    """Motor power (kW)."""

    # === LOCATION ===
    location: str = ""
    """Pump location."""

    is_emergency: bool = False
    """Whether this is emergency fire pump."""

    is_portable: bool = False
    """Whether pump is portable."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pump_id": self.pump_id,
            "pump_type": self.pump_type,
            "capacity_m3h": round(self.capacity_m3h, 1),
            "pressure_bar": self.pressure_bar,
            "power_kw": round(self.power_kw, 2),
            "location": self.location,
            "is_emergency": self.is_emergency,
        }


@dataclass
class LifeSavingAppliance:
    """Life saving appliance."""

    appliance_id: str = ""
    """Unique identifier."""

    appliance_type: str = "liferaft"
    """Type: liferaft, lifebuoy, lifejacket, immersion_suit, EPIRB, etc."""

    capacity: int = 0
    """Capacity (persons) or count."""

    location: str = ""
    """Stowage location."""

    # === COMPLIANCE ===
    solas_compliant: bool = True
    """Whether SOLAS compliant."""

    msc_circular: str = ""
    """Applicable MSC circular."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "appliance_id": self.appliance_id,
            "appliance_type": self.appliance_type,
            "capacity": self.capacity,
            "location": self.location,
            "solas_compliant": self.solas_compliant,
        }


@dataclass
class BilgeSystem:
    """Bilge system definition."""

    # === PUMPS ===
    main_pump_capacity_m3h: float = 0.0
    """Main bilge pump capacity."""

    emergency_pump_capacity_m3h: float = 0.0
    """Emergency bilge pump capacity."""

    pump_count: int = 2
    """Number of bilge pumps."""

    # === PIPING ===
    main_diameter_mm: int = 50
    """Main suction pipe diameter (mm)."""

    branch_diameter_mm: int = 40
    """Branch pipe diameter (mm)."""

    # === ALARMS ===
    has_high_level_alarm: bool = True
    """Whether high bilge level alarm fitted."""

    alarm_locations: List[str] = field(default_factory=list)
    """Compartments with bilge alarms."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "main_pump_capacity_m3h": round(self.main_pump_capacity_m3h, 1),
            "emergency_pump_capacity_m3h": round(self.emergency_pump_capacity_m3h, 1),
            "pump_count": self.pump_count,
            "main_diameter_mm": self.main_diameter_mm,
            "has_high_level_alarm": self.has_high_level_alarm,
        }


@dataclass
class SafetySystem:
    """Complete safety system definition."""

    system_id: str = ""
    """System identifier."""

    # === FIRE SAFETY ===
    fire_zones: List[FireZoneDefinition] = field(default_factory=list)
    """All fire zones."""

    fire_pumps: List[FirePump] = field(default_factory=list)
    """Fire pumps."""

    fire_extinguisher_count: int = 0
    """Portable fire extinguisher count."""

    # === LIFE SAVING ===
    life_saving_appliances: List[LifeSavingAppliance] = field(default_factory=list)
    """Life saving appliances."""

    liferaft_capacity: int = 0
    """Total liferaft capacity (persons)."""

    lifejacket_count: int = 0
    """Total lifejacket count."""

    lifebuoy_count: int = 0
    """Total lifebuoy count."""

    # === BILGE ===
    bilge_system: BilgeSystem = field(default_factory=BilgeSystem)
    """Bilge system."""

    # === NAVIGATION SAFETY ===
    has_ais: bool = True
    """Automatic Identification System."""

    has_epirb: bool = True
    """Emergency Position Indicating Radio Beacon."""

    has_sart: bool = True
    """Search and Rescue Transponder."""

    def calculate_totals(self) -> None:
        """Calculate system totals."""
        # Liferaft capacity
        liferafts = [a for a in self.life_saving_appliances if a.appliance_type == "liferaft"]
        self.liferaft_capacity = sum(a.capacity for a in liferafts)

        # Lifejacket count
        jackets = [a for a in self.life_saving_appliances if a.appliance_type == "lifejacket"]
        self.lifejacket_count = sum(a.capacity for a in jackets)

        # Lifebuoy count
        buoys = [a for a in self.life_saving_appliances if a.appliance_type == "lifebuoy"]
        self.lifebuoy_count = sum(a.capacity for a in buoys)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_id": self.system_id,
            "fire_zones": [z.to_dict() for z in self.fire_zones],
            "fire_pumps": [p.to_dict() for p in self.fire_pumps],
            "fire_extinguisher_count": self.fire_extinguisher_count,
            "life_saving_appliances": [a.to_dict() for a in self.life_saving_appliances],
            "liferaft_capacity": self.liferaft_capacity,
            "lifejacket_count": self.lifejacket_count,
            "lifebuoy_count": self.lifebuoy_count,
            "bilge_system": self.bilge_system.to_dict(),
            "has_ais": self.has_ais,
            "has_epirb": self.has_epirb,
        }
