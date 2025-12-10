"""
zone_definition.py - Zone definition schema v1.1
BRAVO OWNS THIS FILE.

Module 60: Systems Routing
Defines zone types and boundaries for routing compliance.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any, FrozenSet
from enum import Enum
import logging

__all__ = [
    'ZoneType',
    'ZoneDefinition',
    'ZoneBoundary',
    'CrossingRequirement',
    'ZONE_CROSSING_RULES',
]

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ZoneType(Enum):
    """Types of zones that affect routing decisions."""

    # Safety Zones
    FIRE = "fire"                     # Fire zone (A-class division)
    WATERTIGHT = "watertight"         # Watertight compartment
    HAZARDOUS = "hazardous"           # Hazardous area (fuel, battery)

    # Functional Zones
    ACCOMMODATION = "accommodation"   # Crew/passenger areas
    MACHINERY = "machinery"           # Engine room, pump rooms
    CARGO = "cargo"                   # Cargo holds
    NAVIGATION = "navigation"         # Bridge, chart room

    # Special Zones
    CLEAN = "clean"                   # Clean spaces (medical, food)
    CONTROL = "control"               # Control stations
    EMERGENCY = "emergency"           # Emergency equipment areas


class CrossingRequirement(Enum):
    """Requirements for crossing zone boundaries."""

    PROHIBITED = "prohibited"         # Cannot cross
    PENETRATION = "penetration"       # Requires approved penetration
    DAMPER = "damper"                 # Requires fire damper (HVAC)
    VALVE = "valve"                   # Requires isolation valve (fluid)
    BREAKER = "breaker"               # Requires circuit breaker (electrical)
    UNRESTRICTED = "unrestricted"     # No special requirements


# =============================================================================
# ZONE CROSSING RULES
# =============================================================================

# Default rules for crossing different zone types
ZONE_CROSSING_RULES: Dict[ZoneType, Dict[str, CrossingRequirement]] = {
    ZoneType.FIRE: {
        "fuel": CrossingRequirement.PROHIBITED,
        "hvac_supply": CrossingRequirement.DAMPER,
        "hvac_return": CrossingRequirement.DAMPER,
        "hvac_exhaust": CrossingRequirement.DAMPER,
        "electrical_hv": CrossingRequirement.PENETRATION,
        "electrical_lv": CrossingRequirement.PENETRATION,
        "firefighting": CrossingRequirement.UNRESTRICTED,
        "fire_detection": CrossingRequirement.UNRESTRICTED,
        "default": CrossingRequirement.PENETRATION,
    },
    ZoneType.WATERTIGHT: {
        "fuel": CrossingRequirement.VALVE,
        "freshwater": CrossingRequirement.VALVE,
        "seawater": CrossingRequirement.VALVE,
        "bilge": CrossingRequirement.VALVE,
        "electrical_hv": CrossingRequirement.PENETRATION,
        "electrical_lv": CrossingRequirement.PENETRATION,
        "hvac_supply": CrossingRequirement.DAMPER,
        "default": CrossingRequirement.PENETRATION,
    },
    ZoneType.HAZARDOUS: {
        "electrical_hv": CrossingRequirement.PROHIBITED,
        "electrical_lv": CrossingRequirement.PROHIBITED,
        "hvac_supply": CrossingRequirement.PROHIBITED,
        "default": CrossingRequirement.PENETRATION,
    },
    ZoneType.ACCOMMODATION: {
        "fuel": CrossingRequirement.PROHIBITED,
        "black_water": CrossingRequirement.PROHIBITED,
        "bilge": CrossingRequirement.PROHIBITED,
        "steam": CrossingRequirement.PROHIBITED,
        "default": CrossingRequirement.UNRESTRICTED,
    },
    ZoneType.CLEAN: {
        "grey_water": CrossingRequirement.PROHIBITED,
        "black_water": CrossingRequirement.PROHIBITED,
        "bilge": CrossingRequirement.PROHIBITED,
        "fuel": CrossingRequirement.PROHIBITED,
        "lube_oil": CrossingRequirement.PROHIBITED,
        "default": CrossingRequirement.PENETRATION,
    },
}


# =============================================================================
# ZONE BOUNDARY
# =============================================================================

@dataclass
class ZoneBoundary:
    """
    Boundary between two zones or spaces.

    Attributes:
        boundary_id: Unique identifier
        from_space: Space ID on one side
        to_space: Space ID on other side
        zone_type: Type of zone boundary
        division_class: Fire division class (A, B, C) if applicable
        is_watertight: Whether boundary is watertight
        penetrations_allowed: Whether penetrations can be made
        max_penetrations: Maximum number of penetrations allowed
        existing_penetrations: Current penetration count
    """

    boundary_id: str
    from_space: str
    to_space: str
    zone_type: ZoneType

    # Division properties
    division_class: Optional[str] = None  # "A-60", "A-30", "B-15", etc.
    is_watertight: bool = False
    is_weathertight: bool = False

    # Penetration control
    penetrations_allowed: bool = True
    max_penetrations: int = -1  # -1 = unlimited
    existing_penetrations: int = 0

    # Metadata
    deck_id: Optional[str] = None
    frame_number: Optional[float] = None
    notes: str = ""

    def can_add_penetration(self) -> bool:
        """Check if another penetration can be added."""
        if not self.penetrations_allowed:
            return False
        if self.max_penetrations < 0:
            return True
        return self.existing_penetrations < self.max_penetrations

    def get_crossing_requirement(self, system_type: str) -> CrossingRequirement:
        """Get crossing requirement for a system type."""
        rules = ZONE_CROSSING_RULES.get(self.zone_type, {})
        return rules.get(system_type, rules.get("default", CrossingRequirement.PENETRATION))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "boundary_id": self.boundary_id,
            "from_space": self.from_space,
            "to_space": self.to_space,
            "zone_type": self.zone_type.value,
            "division_class": self.division_class,
            "is_watertight": self.is_watertight,
            "is_weathertight": self.is_weathertight,
            "penetrations_allowed": self.penetrations_allowed,
            "max_penetrations": self.max_penetrations,
            "existing_penetrations": self.existing_penetrations,
            "deck_id": self.deck_id,
            "frame_number": self.frame_number,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ZoneBoundary":
        """Deserialize from dictionary."""
        return cls(
            boundary_id=data["boundary_id"],
            from_space=data["from_space"],
            to_space=data["to_space"],
            zone_type=ZoneType(data["zone_type"]),
            division_class=data.get("division_class"),
            is_watertight=data.get("is_watertight", False),
            is_weathertight=data.get("is_weathertight", False),
            penetrations_allowed=data.get("penetrations_allowed", True),
            max_penetrations=data.get("max_penetrations", -1),
            existing_penetrations=data.get("existing_penetrations", 0),
            deck_id=data.get("deck_id"),
            frame_number=data.get("frame_number"),
            notes=data.get("notes", ""),
        )


# =============================================================================
# ZONE DEFINITION
# =============================================================================

@dataclass
class ZoneDefinition:
    """
    Definition of a zone for routing compliance.

    A zone is a collection of spaces with specific routing rules
    for system crossing and separation.

    Attributes:
        zone_id: Unique identifier
        zone_type: Type of zone
        name: Human-readable name
        spaces: Set of space IDs in this zone
        boundaries: Boundaries with adjacent zones
        prohibited_systems: Systems that cannot route through
        restricted_systems: Systems that need special handling
        required_systems: Systems that must service this zone
    """

    zone_id: str
    zone_type: ZoneType
    name: str = ""

    # Space membership
    spaces: Set[str] = field(default_factory=set)

    # Boundaries
    boundaries: List[ZoneBoundary] = field(default_factory=list)

    # System restrictions
    prohibited_systems: FrozenSet[str] = field(default_factory=frozenset)
    restricted_systems: FrozenSet[str] = field(default_factory=frozenset)
    required_systems: FrozenSet[str] = field(default_factory=frozenset)

    # Properties
    is_main_vertical_zone: bool = False
    fire_division_class: Optional[str] = None
    deck_ids: Set[str] = field(default_factory=set)

    # Metadata
    description: str = ""
    regulations: List[str] = field(default_factory=list)

    def contains_space(self, space_id: str) -> bool:
        """Check if zone contains a space."""
        return space_id in self.spaces

    def is_system_prohibited(self, system_type: str) -> bool:
        """Check if a system type is prohibited in this zone."""
        return system_type in self.prohibited_systems

    def is_system_restricted(self, system_type: str) -> bool:
        """Check if a system type is restricted in this zone."""
        return system_type in self.restricted_systems

    def get_boundary_to(self, other_space: str) -> Optional[ZoneBoundary]:
        """Get boundary to a space if it exists."""
        for boundary in self.boundaries:
            if boundary.to_space == other_space or boundary.from_space == other_space:
                return boundary
        return None

    def add_space(self, space_id: str) -> None:
        """Add a space to this zone."""
        self.spaces.add(space_id)

    def remove_space(self, space_id: str) -> None:
        """Remove a space from this zone."""
        self.spaces.discard(space_id)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "zone_id": self.zone_id,
            "zone_type": self.zone_type.value,
            "name": self.name,
            "spaces": list(self.spaces),
            "boundaries": [b.to_dict() for b in self.boundaries],
            "prohibited_systems": list(self.prohibited_systems),
            "restricted_systems": list(self.restricted_systems),
            "required_systems": list(self.required_systems),
            "is_main_vertical_zone": self.is_main_vertical_zone,
            "fire_division_class": self.fire_division_class,
            "deck_ids": list(self.deck_ids),
            "description": self.description,
            "regulations": self.regulations,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ZoneDefinition":
        """Deserialize from dictionary."""
        return cls(
            zone_id=data["zone_id"],
            zone_type=ZoneType(data["zone_type"]),
            name=data.get("name", ""),
            spaces=set(data.get("spaces", [])),
            boundaries=[ZoneBoundary.from_dict(b) for b in data.get("boundaries", [])],
            prohibited_systems=frozenset(data.get("prohibited_systems", [])),
            restricted_systems=frozenset(data.get("restricted_systems", [])),
            required_systems=frozenset(data.get("required_systems", [])),
            is_main_vertical_zone=data.get("is_main_vertical_zone", False),
            fire_division_class=data.get("fire_division_class"),
            deck_ids=set(data.get("deck_ids", [])),
            description=data.get("description", ""),
            regulations=data.get("regulations", []),
        )

    @classmethod
    def create_fire_zone(
        cls,
        zone_id: str,
        name: str,
        spaces: Set[str],
        division_class: str = "A-60",
    ) -> "ZoneDefinition":
        """Factory method for fire zones."""
        return cls(
            zone_id=zone_id,
            zone_type=ZoneType.FIRE,
            name=name,
            spaces=spaces,
            is_main_vertical_zone=True,
            fire_division_class=division_class,
            prohibited_systems=frozenset({"fuel"}),
            restricted_systems=frozenset({"hvac_supply", "hvac_return", "electrical_hv"}),
        )

    @classmethod
    def create_watertight_compartment(
        cls,
        zone_id: str,
        name: str,
        spaces: Set[str],
    ) -> "ZoneDefinition":
        """Factory method for watertight compartments."""
        return cls(
            zone_id=zone_id,
            zone_type=ZoneType.WATERTIGHT,
            name=name,
            spaces=spaces,
            restricted_systems=frozenset({"fuel", "freshwater", "seawater", "bilge"}),
        )
