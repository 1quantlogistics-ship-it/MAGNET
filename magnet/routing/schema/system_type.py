"""
magnet/routing/schema/system_type.py - System Type Definitions

Defines all 18 system types that can be routed through a vessel,
including their properties, criticality levels, and default sizing.

System Categories:
- Fluid: FUEL, FRESHWATER, SEAWATER, GREY_WATER, BLACK_WATER, LUBE_OIL, HYDRAULIC
- HVAC: HVAC_SUPPLY, HVAC_RETURN, HVAC_EXHAUST
- Electrical: ELECTRICAL_HV, ELECTRICAL_LV, ELECTRICAL_DC
- Safety: FIREFIGHTING, FIRE_DETECTION, BILGE
- Other: COMPRESSED_AIR, STEAM
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, FrozenSet

__all__ = [
    'SystemType',
    'Criticality',
    'SystemProperties',
    'SYSTEM_PROPERTIES',
    'get_system_properties',
]


class Criticality(Enum):
    """Criticality level for systems affecting redundancy requirements."""
    CRITICAL = "critical"   # Must have redundancy (safety-critical)
    HIGH = "high"           # Should have redundancy (mission-critical)
    MEDIUM = "medium"       # Single path acceptable
    LOW = "low"             # Best effort routing


class SystemType(Enum):
    """
    Types of systems that can be routed through the vessel.

    Each system type has associated properties for routing,
    zone compliance, and capacity calculation.
    """
    # Fluid Systems
    FUEL = "fuel"
    FRESHWATER = "freshwater"
    SEAWATER = "seawater"
    GREY_WATER = "grey_water"
    BLACK_WATER = "black_water"
    LUBE_OIL = "lube_oil"
    HYDRAULIC = "hydraulic"

    # HVAC Systems
    HVAC_SUPPLY = "hvac_supply"
    HVAC_RETURN = "hvac_return"
    HVAC_EXHAUST = "hvac_exhaust"

    # Electrical Systems
    ELECTRICAL_HV = "electrical_hv"    # 440V+
    ELECTRICAL_LV = "electrical_lv"    # 120V
    ELECTRICAL_DC = "electrical_dc"    # 24V DC

    # Safety Systems
    FIREFIGHTING = "firefighting"
    FIRE_DETECTION = "fire_detection"
    BILGE = "bilge"

    # Other Systems
    COMPRESSED_AIR = "compressed_air"
    STEAM = "steam"


@dataclass(frozen=True)
class SystemProperties:
    """
    Properties for a system type used in routing decisions.

    Attributes:
        system_type: The system type this describes
        name: Human-readable name
        description: Brief description

        criticality: How critical the system is
        requires_redundancy: Whether redundant paths are required

        allowed_zones: Zones where system can route (empty = all)
        prohibited_zones: Zones where system cannot route
        can_cross_fire_zone: Can trunk cross fire zone boundary
        can_cross_watertight: Can trunk cross watertight boundary

        prohibited_adjacent: Systems that cannot route alongside
        min_separation_m: Minimum distance from other systems

        is_fluid: True for liquid/gas systems
        is_electrical: True for electrical systems
        is_hazardous: True for hazardous materials

        default_trunk_diameter_mm: Default diameter for fluid systems
        default_trunk_rating_a: Default amperage for electrical systems

        prefer_vertical: Prefer vertical routing (exhausts)
        prefer_shortest: Optimize for shortest path
        avoid_crew_spaces: Route around crew areas
    """
    # Identity
    system_type: SystemType
    name: str
    description: str

    # Criticality
    criticality: Criticality
    requires_redundancy: bool

    # Zone rules
    allowed_zones: FrozenSet[str]
    prohibited_zones: FrozenSet[str]
    can_cross_fire_zone: bool
    can_cross_watertight: bool

    # Separation rules
    prohibited_adjacent: FrozenSet['SystemType']
    min_separation_m: float

    # Physical properties
    is_fluid: bool
    is_electrical: bool
    is_hazardous: bool

    # Default sizing
    default_trunk_diameter_mm: float
    default_trunk_rating_a: float

    # Routing preferences
    prefer_vertical: bool = False
    prefer_shortest: bool = True
    avoid_crew_spaces: bool = False


# Complete system property definitions for all 18 system types
SYSTEM_PROPERTIES: Dict[SystemType, SystemProperties] = {

    # =========================================================================
    # FLUID SYSTEMS
    # =========================================================================

    SystemType.FUEL: SystemProperties(
        system_type=SystemType.FUEL,
        name="Fuel",
        description="Diesel/fuel oil distribution",
        criticality=Criticality.CRITICAL,
        requires_redundancy=True,
        allowed_zones=frozenset(),
        prohibited_zones=frozenset({'accommodation', 'galley'}),
        can_cross_fire_zone=False,
        can_cross_watertight=True,
        prohibited_adjacent=frozenset({SystemType.ELECTRICAL_HV, SystemType.STEAM}),
        min_separation_m=0.3,
        is_fluid=True,
        is_electrical=False,
        is_hazardous=True,
        default_trunk_diameter_mm=50.0,
        default_trunk_rating_a=0.0,
        avoid_crew_spaces=True,
    ),

    SystemType.FRESHWATER: SystemProperties(
        system_type=SystemType.FRESHWATER,
        name="Fresh Water",
        description="Potable water distribution",
        criticality=Criticality.HIGH,
        requires_redundancy=False,
        allowed_zones=frozenset(),
        prohibited_zones=frozenset(),
        can_cross_fire_zone=True,
        can_cross_watertight=True,
        prohibited_adjacent=frozenset({SystemType.BLACK_WATER, SystemType.GREY_WATER}),
        min_separation_m=0.15,
        is_fluid=True,
        is_electrical=False,
        is_hazardous=False,
        default_trunk_diameter_mm=40.0,
        default_trunk_rating_a=0.0,
    ),

    SystemType.SEAWATER: SystemProperties(
        system_type=SystemType.SEAWATER,
        name="Seawater",
        description="Seawater cooling and service",
        criticality=Criticality.HIGH,
        requires_redundancy=True,
        allowed_zones=frozenset(),
        prohibited_zones=frozenset(),
        can_cross_fire_zone=True,
        can_cross_watertight=True,
        prohibited_adjacent=frozenset(),
        min_separation_m=0.1,
        is_fluid=True,
        is_electrical=False,
        is_hazardous=False,
        default_trunk_diameter_mm=80.0,
        default_trunk_rating_a=0.0,
    ),

    SystemType.GREY_WATER: SystemProperties(
        system_type=SystemType.GREY_WATER,
        name="Grey Water",
        description="Sink/shower drainage",
        criticality=Criticality.LOW,
        requires_redundancy=False,
        allowed_zones=frozenset(),
        prohibited_zones=frozenset({'galley', 'food_storage'}),
        can_cross_fire_zone=True,
        can_cross_watertight=True,
        prohibited_adjacent=frozenset({SystemType.FRESHWATER}),
        min_separation_m=0.15,
        is_fluid=True,
        is_electrical=False,
        is_hazardous=False,
        default_trunk_diameter_mm=50.0,
        default_trunk_rating_a=0.0,
    ),

    SystemType.BLACK_WATER: SystemProperties(
        system_type=SystemType.BLACK_WATER,
        name="Black Water",
        description="Sewage collection",
        criticality=Criticality.MEDIUM,
        requires_redundancy=False,
        allowed_zones=frozenset(),
        prohibited_zones=frozenset({'galley', 'food_storage', 'freshwater_tank'}),
        can_cross_fire_zone=True,
        can_cross_watertight=True,
        prohibited_adjacent=frozenset({SystemType.FRESHWATER, SystemType.HVAC_SUPPLY}),
        min_separation_m=0.2,
        is_fluid=True,
        is_electrical=False,
        is_hazardous=True,
        default_trunk_diameter_mm=75.0,
        default_trunk_rating_a=0.0,
    ),

    SystemType.LUBE_OIL: SystemProperties(
        system_type=SystemType.LUBE_OIL,
        name="Lube Oil",
        description="Engine lubrication",
        criticality=Criticality.HIGH,
        requires_redundancy=False,
        allowed_zones=frozenset({'machinery'}),
        prohibited_zones=frozenset({'accommodation'}),
        can_cross_fire_zone=False,
        can_cross_watertight=True,
        prohibited_adjacent=frozenset({SystemType.ELECTRICAL_HV}),
        min_separation_m=0.2,
        is_fluid=True,
        is_electrical=False,
        is_hazardous=True,
        default_trunk_diameter_mm=25.0,
        default_trunk_rating_a=0.0,
    ),

    SystemType.HYDRAULIC: SystemProperties(
        system_type=SystemType.HYDRAULIC,
        name="Hydraulic",
        description="Hydraulic power distribution",
        criticality=Criticality.HIGH,
        requires_redundancy=True,
        allowed_zones=frozenset(),
        prohibited_zones=frozenset(),
        can_cross_fire_zone=False,
        can_cross_watertight=True,
        prohibited_adjacent=frozenset({SystemType.ELECTRICAL_HV}),
        min_separation_m=0.15,
        is_fluid=True,
        is_electrical=False,
        is_hazardous=True,
        default_trunk_diameter_mm=20.0,
        default_trunk_rating_a=0.0,
    ),

    # =========================================================================
    # HVAC SYSTEMS
    # =========================================================================

    SystemType.HVAC_SUPPLY: SystemProperties(
        system_type=SystemType.HVAC_SUPPLY,
        name="HVAC Supply",
        description="Conditioned air supply",
        criticality=Criticality.MEDIUM,
        requires_redundancy=False,
        allowed_zones=frozenset(),
        prohibited_zones=frozenset(),
        can_cross_fire_zone=False,  # Fire dampers required at crossing
        can_cross_watertight=True,
        prohibited_adjacent=frozenset({SystemType.BLACK_WATER, SystemType.HVAC_EXHAUST}),
        min_separation_m=0.1,
        is_fluid=False,
        is_electrical=False,
        is_hazardous=False,
        default_trunk_diameter_mm=300.0,  # Duct equivalent diameter
        default_trunk_rating_a=0.0,
    ),

    SystemType.HVAC_RETURN: SystemProperties(
        system_type=SystemType.HVAC_RETURN,
        name="HVAC Return",
        description="Return air ducting",
        criticality=Criticality.LOW,
        requires_redundancy=False,
        allowed_zones=frozenset(),
        prohibited_zones=frozenset(),
        can_cross_fire_zone=False,
        can_cross_watertight=True,
        prohibited_adjacent=frozenset({SystemType.HVAC_EXHAUST}),
        min_separation_m=0.1,
        is_fluid=False,
        is_electrical=False,
        is_hazardous=False,
        default_trunk_diameter_mm=250.0,
        default_trunk_rating_a=0.0,
    ),

    SystemType.HVAC_EXHAUST: SystemProperties(
        system_type=SystemType.HVAC_EXHAUST,
        name="HVAC Exhaust",
        description="Exhaust ventilation",
        criticality=Criticality.MEDIUM,
        requires_redundancy=False,
        allowed_zones=frozenset(),
        prohibited_zones=frozenset(),
        can_cross_fire_zone=False,
        can_cross_watertight=True,
        prohibited_adjacent=frozenset({SystemType.HVAC_SUPPLY}),
        min_separation_m=0.3,
        is_fluid=False,
        is_electrical=False,
        is_hazardous=False,
        default_trunk_diameter_mm=200.0,
        default_trunk_rating_a=0.0,
        prefer_vertical=True,  # Exhausts naturally rise
    ),

    # =========================================================================
    # ELECTRICAL SYSTEMS
    # =========================================================================

    SystemType.ELECTRICAL_HV: SystemProperties(
        system_type=SystemType.ELECTRICAL_HV,
        name="High Voltage",
        description="440V+ power distribution",
        criticality=Criticality.CRITICAL,
        requires_redundancy=True,
        allowed_zones=frozenset(),
        prohibited_zones=frozenset(),
        can_cross_fire_zone=True,  # In proper conduit
        can_cross_watertight=True,
        prohibited_adjacent=frozenset({SystemType.FUEL, SystemType.HYDRAULIC, SystemType.LUBE_OIL}),
        min_separation_m=0.3,
        is_fluid=False,
        is_electrical=True,
        is_hazardous=True,
        default_trunk_diameter_mm=0.0,
        default_trunk_rating_a=400.0,
    ),

    SystemType.ELECTRICAL_LV: SystemProperties(
        system_type=SystemType.ELECTRICAL_LV,
        name="Low Voltage",
        description="120V power distribution",
        criticality=Criticality.HIGH,
        requires_redundancy=False,
        allowed_zones=frozenset(),
        prohibited_zones=frozenset(),
        can_cross_fire_zone=True,
        can_cross_watertight=True,
        prohibited_adjacent=frozenset(),
        min_separation_m=0.1,
        is_fluid=False,
        is_electrical=True,
        is_hazardous=False,
        default_trunk_diameter_mm=0.0,
        default_trunk_rating_a=100.0,
    ),

    SystemType.ELECTRICAL_DC: SystemProperties(
        system_type=SystemType.ELECTRICAL_DC,
        name="DC Power",
        description="24V DC distribution",
        criticality=Criticality.HIGH,
        requires_redundancy=True,  # Critical systems backup
        allowed_zones=frozenset(),
        prohibited_zones=frozenset(),
        can_cross_fire_zone=True,
        can_cross_watertight=True,
        prohibited_adjacent=frozenset(),
        min_separation_m=0.05,
        is_fluid=False,
        is_electrical=True,
        is_hazardous=False,
        default_trunk_diameter_mm=0.0,
        default_trunk_rating_a=50.0,
    ),

    # =========================================================================
    # SAFETY SYSTEMS
    # =========================================================================

    SystemType.FIREFIGHTING: SystemProperties(
        system_type=SystemType.FIREFIGHTING,
        name="Firefighting",
        description="Fire main and sprinklers",
        criticality=Criticality.CRITICAL,
        requires_redundancy=True,
        allowed_zones=frozenset(),
        prohibited_zones=frozenset(),
        can_cross_fire_zone=True,  # Essential for firefighting
        can_cross_watertight=True,
        prohibited_adjacent=frozenset(),
        min_separation_m=0.1,
        is_fluid=True,
        is_electrical=False,
        is_hazardous=False,
        default_trunk_diameter_mm=65.0,
        default_trunk_rating_a=0.0,
    ),

    SystemType.FIRE_DETECTION: SystemProperties(
        system_type=SystemType.FIRE_DETECTION,
        name="Fire Detection",
        description="Smoke and heat detection",
        criticality=Criticality.CRITICAL,
        requires_redundancy=True,
        allowed_zones=frozenset(),
        prohibited_zones=frozenset(),
        can_cross_fire_zone=True,
        can_cross_watertight=True,
        prohibited_adjacent=frozenset(),
        min_separation_m=0.05,
        is_fluid=False,
        is_electrical=True,
        is_hazardous=False,
        default_trunk_diameter_mm=0.0,
        default_trunk_rating_a=5.0,
    ),

    SystemType.BILGE: SystemProperties(
        system_type=SystemType.BILGE,
        name="Bilge",
        description="Bilge pumping system",
        criticality=Criticality.CRITICAL,
        requires_redundancy=True,
        allowed_zones=frozenset(),
        prohibited_zones=frozenset(),
        can_cross_fire_zone=True,
        can_cross_watertight=True,
        prohibited_adjacent=frozenset({SystemType.FRESHWATER}),
        min_separation_m=0.15,
        is_fluid=True,
        is_electrical=False,
        is_hazardous=False,
        default_trunk_diameter_mm=50.0,
        default_trunk_rating_a=0.0,
    ),

    # =========================================================================
    # OTHER SYSTEMS
    # =========================================================================

    SystemType.COMPRESSED_AIR: SystemProperties(
        system_type=SystemType.COMPRESSED_AIR,
        name="Compressed Air",
        description="Service and control air",
        criticality=Criticality.MEDIUM,
        requires_redundancy=False,
        allowed_zones=frozenset(),
        prohibited_zones=frozenset(),
        can_cross_fire_zone=True,
        can_cross_watertight=True,
        prohibited_adjacent=frozenset(),
        min_separation_m=0.1,
        is_fluid=False,  # Gas
        is_electrical=False,
        is_hazardous=False,
        default_trunk_diameter_mm=25.0,
        default_trunk_rating_a=0.0,
    ),

    SystemType.STEAM: SystemProperties(
        system_type=SystemType.STEAM,
        name="Steam",
        description="Steam heating and service",
        criticality=Criticality.MEDIUM,
        requires_redundancy=False,
        allowed_zones=frozenset({'machinery'}),
        prohibited_zones=frozenset({'accommodation'}),
        can_cross_fire_zone=False,
        can_cross_watertight=True,
        prohibited_adjacent=frozenset({SystemType.FUEL, SystemType.ELECTRICAL_HV}),
        min_separation_m=0.3,
        is_fluid=False,  # Gas
        is_electrical=False,
        is_hazardous=True,
        default_trunk_diameter_mm=40.0,
        default_trunk_rating_a=0.0,
        avoid_crew_spaces=True,
    ),
}


def get_system_properties(system_type: SystemType) -> SystemProperties:
    """
    Get properties for a system type.

    Args:
        system_type: The system type to get properties for

    Returns:
        SystemProperties for the given system type

    Raises:
        KeyError: If system type not found (should never happen)
    """
    return SYSTEM_PROPERTIES[system_type]


# Convenience functions for filtering systems

def get_critical_systems() -> list[SystemType]:
    """Get all systems with CRITICAL criticality."""
    return [
        st for st, props in SYSTEM_PROPERTIES.items()
        if props.criticality == Criticality.CRITICAL
    ]


def get_systems_requiring_redundancy() -> list[SystemType]:
    """Get all systems that require redundant routing."""
    return [
        st for st, props in SYSTEM_PROPERTIES.items()
        if props.requires_redundancy
    ]


def get_fluid_systems() -> list[SystemType]:
    """Get all fluid (liquid/gas) systems."""
    return [
        st for st, props in SYSTEM_PROPERTIES.items()
        if props.is_fluid
    ]


def get_electrical_systems() -> list[SystemType]:
    """Get all electrical systems."""
    return [
        st for st, props in SYSTEM_PROPERTIES.items()
        if props.is_electrical
    ]


def get_hazardous_systems() -> list[SystemType]:
    """Get all hazardous systems."""
    return [
        st for st, props in SYSTEM_PROPERTIES.items()
        if props.is_hazardous
    ]
