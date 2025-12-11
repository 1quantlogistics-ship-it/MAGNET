"""
space.py - Space definition schema v1.0
BRAVO OWNS THIS FILE.

Module 59: Interior Layout
Defines space types, boundaries, and connections for interior arrangement.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any, Tuple
from enum import Enum
import hashlib
import json
import logging
import uuid

__all__ = [
    'SpaceType',
    'SpaceCategory',
    'SpaceDefinition',
    'SpaceBoundary',
    'SpaceConnection',
    'DEFAULT_SPACE_CAPACITIES',
]

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class SpaceCategory(Enum):
    """High-level categories of ship spaces."""

    SAFETY = "safety"           # Fire zones, watertight compartments
    OPERATIONAL = "operational" # Machinery, control, navigation
    LIVING = "living"           # Accommodation, recreation
    CARGO = "cargo"             # Cargo holds, storage
    SERVICE = "service"         # Galley, laundry, stores
    CIRCULATION = "circulation" # Corridors, stairways, lobbies


class SpaceType(Enum):
    """Specific types of ship spaces."""

    # Machinery Spaces (Operational)
    ENGINE_ROOM = "engine_room"
    GENERATOR_ROOM = "generator_room"
    PUMP_ROOM = "pump_room"
    STEERING_GEAR = "steering_gear"
    BOW_THRUSTER = "bow_thruster"
    SWITCHBOARD_ROOM = "switchboard_room"
    WORKSHOP = "workshop"

    # Control Spaces (Operational)
    BRIDGE = "bridge"
    CHART_ROOM = "chart_room"
    RADIO_ROOM = "radio_room"
    SAFETY_CENTER = "safety_center"
    CARGO_CONTROL = "cargo_control"
    ENGINE_CONTROL = "engine_control"

    # Accommodation (Living)
    CABIN_CREW = "cabin_crew"
    CABIN_OFFICER = "cabin_officer"
    CABIN_PASSENGER = "cabin_passenger"
    MESS_CREW = "mess_crew"
    MESS_OFFICER = "mess_officer"
    LOUNGE = "lounge"
    RECREATION = "recreation"
    GYM = "gym"
    HOSPITAL = "hospital"

    # Service Spaces
    GALLEY = "galley"
    PANTRY = "pantry"
    PROVISION_STORE = "provision_store"
    COLD_STORE = "cold_store"
    LAUNDRY = "laundry"
    STORE_GENERAL = "store_general"
    STORE_DECK = "store_deck"
    STORE_ENGINE = "store_engine"

    # Cargo Spaces
    CARGO_HOLD = "cargo_hold"
    CARGO_TANK = "cargo_tank"
    BALLAST_TANK = "ballast_tank"
    FUEL_TANK = "fuel_tank"
    FRESHWATER_TANK = "freshwater_tank"
    SLOP_TANK = "slop_tank"
    VOID_SPACE = "void_space"

    # Circulation
    CORRIDOR = "corridor"
    STAIRWAY = "stairway"
    LOBBY = "lobby"
    ELEVATOR_TRUNK = "elevator_trunk"
    ESCAPE_TRUNK = "escape_trunk"

    # Safety Spaces
    LIFEBOAT_STATION = "lifeboat_station"
    FIRE_STATION = "fire_station"
    EMERGENCY_EXIT = "emergency_exit"
    MUSTER_STATION = "muster_station"

    # Sanitary
    TOILET = "toilet"
    BATHROOM = "bathroom"
    SEWAGE_TREATMENT = "sewage_treatment"

    # Other
    CHAIN_LOCKER = "chain_locker"
    PAINT_LOCKER = "paint_locker"
    BATTERY_ROOM = "battery_room"
    CO2_ROOM = "co2_room"
    INCINERATOR = "incinerator"


# =============================================================================
# SPACE CAPACITIES
# =============================================================================

# Default minimum areas (m²) and heights (m) for space types
DEFAULT_SPACE_CAPACITIES: Dict[SpaceType, Dict[str, float]] = {
    # Machinery
    SpaceType.ENGINE_ROOM: {"min_area": 50.0, "min_height": 4.0, "max_occupancy": 10},
    SpaceType.GENERATOR_ROOM: {"min_area": 20.0, "min_height": 3.0, "max_occupancy": 5},
    SpaceType.PUMP_ROOM: {"min_area": 15.0, "min_height": 3.0, "max_occupancy": 3},
    SpaceType.SWITCHBOARD_ROOM: {"min_area": 12.0, "min_height": 2.5, "max_occupancy": 4},

    # Control
    SpaceType.BRIDGE: {"min_area": 25.0, "min_height": 2.5, "max_occupancy": 8},
    SpaceType.ENGINE_CONTROL: {"min_area": 15.0, "min_height": 2.5, "max_occupancy": 4},

    # Accommodation
    SpaceType.CABIN_CREW: {"min_area": 4.5, "min_height": 2.1, "max_occupancy": 2},
    SpaceType.CABIN_OFFICER: {"min_area": 7.5, "min_height": 2.1, "max_occupancy": 1},
    SpaceType.CABIN_PASSENGER: {"min_area": 10.0, "min_height": 2.3, "max_occupancy": 2},
    SpaceType.MESS_CREW: {"min_area": 1.0, "min_height": 2.3, "max_occupancy": 20},  # per person
    SpaceType.MESS_OFFICER: {"min_area": 1.5, "min_height": 2.3, "max_occupancy": 10},
    SpaceType.LOUNGE: {"min_area": 20.0, "min_height": 2.5, "max_occupancy": 30},
    SpaceType.HOSPITAL: {"min_area": 12.0, "min_height": 2.3, "max_occupancy": 4},

    # Service
    SpaceType.GALLEY: {"min_area": 15.0, "min_height": 2.3, "max_occupancy": 6},
    SpaceType.LAUNDRY: {"min_area": 8.0, "min_height": 2.3, "max_occupancy": 2},

    # Circulation
    SpaceType.CORRIDOR: {"min_area": 2.0, "min_height": 2.1, "min_width": 0.9},
    SpaceType.STAIRWAY: {"min_area": 3.0, "min_height": 2.1, "min_width": 0.8},
}


# =============================================================================
# SPACE BOUNDARY
# =============================================================================

@dataclass
class SpaceBoundary:
    """
    Defines the geometric boundary of a space.

    Attributes:
        points: List of (x, y) coordinates defining the boundary polygon
        deck_id: Deck identifier this boundary is on
        z_min: Minimum Z coordinate (bottom of space)
        z_max: Maximum Z coordinate (top of space)
        is_closed: Whether the boundary forms a closed polygon
    """

    points: List[Tuple[float, float]]  # (x, y) coordinates
    deck_id: str
    z_min: float = 0.0
    z_max: float = 2.5  # Default deck height
    is_closed: bool = True

    def area(self) -> float:
        """Calculate area using shoelace formula."""
        if len(self.points) < 3:
            return 0.0

        n = len(self.points)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += self.points[i][0] * self.points[j][1]
            area -= self.points[j][0] * self.points[i][1]
        return abs(area) / 2.0

    def volume(self) -> float:
        """Calculate volume of the space."""
        return self.area() * (self.z_max - self.z_min)

    def height(self) -> float:
        """Get height of the space."""
        return self.z_max - self.z_min

    def centroid(self) -> Tuple[float, float]:
        """Calculate centroid of the boundary polygon."""
        if len(self.points) < 3:
            return (0.0, 0.0)

        cx, cy = 0.0, 0.0
        area = self.area()
        if area == 0:
            return (0.0, 0.0)

        n = len(self.points)
        for i in range(n):
            j = (i + 1) % n
            factor = (self.points[i][0] * self.points[j][1] -
                     self.points[j][0] * self.points[i][1])
            cx += (self.points[i][0] + self.points[j][0]) * factor
            cy += (self.points[i][1] + self.points[j][1]) * factor

        cx /= (6.0 * area)
        cy /= (6.0 * area)
        return (abs(cx), abs(cy))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "points": self.points,
            "deck_id": self.deck_id,
            "z_min": self.z_min,
            "z_max": self.z_max,
            "is_closed": self.is_closed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpaceBoundary":
        """Deserialize from dictionary."""
        return cls(
            points=[tuple(p) for p in data["points"]],
            deck_id=data["deck_id"],
            z_min=data.get("z_min", 0.0),
            z_max=data.get("z_max", 2.5),
            is_closed=data.get("is_closed", True),
        )


# =============================================================================
# SPACE CONNECTION
# =============================================================================

@dataclass
class SpaceConnection:
    """
    Defines a connection between two spaces (door, hatch, etc.).

    Attributes:
        connection_id: Unique identifier
        from_space_id: Source space
        to_space_id: Target space
        connection_type: Type of connection (door, hatch, opening)
        position: (x, y, z) location of connection
        width: Opening width in meters
        height: Opening height in meters
        is_watertight: Whether connection has watertight closure
        is_fireproof: Whether connection has fire rating
        fire_rating: Fire rating if applicable (A-60, B-15, etc.)
    """

    connection_id: str
    from_space_id: str
    to_space_id: str
    connection_type: str = "door"  # door, hatch, opening, ladder

    # Position
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    # Dimensions
    width: float = 0.8  # meters
    height: float = 2.0  # meters

    # Safety properties
    is_watertight: bool = False
    is_fireproof: bool = False
    fire_rating: Optional[str] = None

    # Accessibility
    is_emergency_exit: bool = False
    is_accessible: bool = True  # wheelchair/mobility accessible

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "connection_id": self.connection_id,
            "from_space_id": self.from_space_id,
            "to_space_id": self.to_space_id,
            "connection_type": self.connection_type,
            "position": list(self.position),
            "width": self.width,
            "height": self.height,
            "is_watertight": self.is_watertight,
            "is_fireproof": self.is_fireproof,
            "fire_rating": self.fire_rating,
            "is_emergency_exit": self.is_emergency_exit,
            "is_accessible": self.is_accessible,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpaceConnection":
        """Deserialize from dictionary."""
        return cls(
            connection_id=data["connection_id"],
            from_space_id=data["from_space_id"],
            to_space_id=data["to_space_id"],
            connection_type=data.get("connection_type", "door"),
            position=tuple(data.get("position", [0, 0, 0])),
            width=data.get("width", 0.8),
            height=data.get("height", 2.0),
            is_watertight=data.get("is_watertight", False),
            is_fireproof=data.get("is_fireproof", False),
            fire_rating=data.get("fire_rating"),
            is_emergency_exit=data.get("is_emergency_exit", False),
            is_accessible=data.get("is_accessible", True),
        )


# =============================================================================
# SPACE DEFINITION
# =============================================================================

@dataclass
class SpaceDefinition:
    """
    Complete definition of a ship space.

    Attributes:
        space_id: Unique identifier
        name: Human-readable name
        space_type: Type of space
        category: Category of space
        boundary: Geometric boundary
        deck_id: Primary deck
        zone_id: Zone this space belongs to
        frame_start: Starting frame number
        frame_end: Ending frame number
        connected_spaces: IDs of adjacent spaces
        connections: Door/hatch connections
        max_occupancy: Maximum people allowed
        is_manned: Whether space is normally occupied
        ventilation_required: CFM required
        lighting_required: Lux required
    """

    space_id: str
    name: str
    space_type: SpaceType
    category: SpaceCategory

    # Geometry
    boundary: SpaceBoundary

    # Location
    deck_id: str
    zone_id: Optional[str] = None
    frame_start: Optional[float] = None
    frame_end: Optional[float] = None

    # Connectivity
    connected_spaces: Set[str] = field(default_factory=set)
    connections: List[SpaceConnection] = field(default_factory=list)

    # Capacity
    max_occupancy: int = 0
    is_manned: bool = False

    # Requirements
    ventilation_required: float = 0.0  # CFM
    lighting_required: float = 0.0  # Lux

    # Safety
    fire_zone_id: Optional[str] = None
    watertight_compartment_id: Optional[str] = None

    # Metadata
    notes: str = ""
    tags: Set[str] = field(default_factory=set)

    def __post_init__(self):
        """Generate ID if not provided."""
        if not self.space_id:
            self.space_id = f"SPACE-{uuid.uuid4().hex[:8].upper()}"

    @property
    def area(self) -> float:
        """Get area in m²."""
        return self.boundary.area()

    @property
    def volume(self) -> float:
        """Get volume in m³."""
        return self.boundary.volume()

    @property
    def height(self) -> float:
        """Get height in m."""
        return self.boundary.height()

    def get_centroid_3d(self) -> Tuple[float, float, float]:
        """Get 3D centroid of the space."""
        cx, cy = self.boundary.centroid()
        cz = (self.boundary.z_min + self.boundary.z_max) / 2
        return (cx, cy, cz)

    def add_connection(self, connection: SpaceConnection) -> None:
        """Add a connection to this space."""
        self.connections.append(connection)
        self.connected_spaces.add(connection.to_space_id)

    def compute_hash(self) -> str:
        """Compute content hash for this space."""
        data = {
            "space_id": self.space_id,
            "name": self.name,
            "space_type": self.space_type.value,
            "boundary": self.boundary.to_dict(),
            "deck_id": self.deck_id,
            "zone_id": self.zone_id,
            "connected_spaces": sorted(self.connected_spaces),
        }
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "space_id": self.space_id,
            "name": self.name,
            "space_type": self.space_type.value,
            "category": self.category.value,
            "boundary": self.boundary.to_dict(),
            "deck_id": self.deck_id,
            "zone_id": self.zone_id,
            "frame_start": self.frame_start,
            "frame_end": self.frame_end,
            "connected_spaces": list(self.connected_spaces),
            "connections": [c.to_dict() for c in self.connections],
            "max_occupancy": self.max_occupancy,
            "is_manned": self.is_manned,
            "ventilation_required": self.ventilation_required,
            "lighting_required": self.lighting_required,
            "fire_zone_id": self.fire_zone_id,
            "watertight_compartment_id": self.watertight_compartment_id,
            "notes": self.notes,
            "tags": list(self.tags),
            "area_m2": self.area,
            "volume_m3": self.volume,
            "height_m": self.height,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpaceDefinition":
        """Deserialize from dictionary."""
        return cls(
            space_id=data["space_id"],
            name=data["name"],
            space_type=SpaceType(data["space_type"]),
            category=SpaceCategory(data["category"]),
            boundary=SpaceBoundary.from_dict(data["boundary"]),
            deck_id=data["deck_id"],
            zone_id=data.get("zone_id"),
            frame_start=data.get("frame_start"),
            frame_end=data.get("frame_end"),
            connected_spaces=set(data.get("connected_spaces", [])),
            connections=[SpaceConnection.from_dict(c) for c in data.get("connections", [])],
            max_occupancy=data.get("max_occupancy", 0),
            is_manned=data.get("is_manned", False),
            ventilation_required=data.get("ventilation_required", 0.0),
            lighting_required=data.get("lighting_required", 0.0),
            fire_zone_id=data.get("fire_zone_id"),
            watertight_compartment_id=data.get("watertight_compartment_id"),
            notes=data.get("notes", ""),
            tags=set(data.get("tags", [])),
        )

    @classmethod
    def create_cabin(
        cls,
        space_id: str,
        name: str,
        deck_id: str,
        points: List[Tuple[float, float]],
        z_min: float,
        z_max: float,
        cabin_type: str = "crew",
    ) -> "SpaceDefinition":
        """Factory method for creating cabin spaces."""
        space_type = {
            "crew": SpaceType.CABIN_CREW,
            "officer": SpaceType.CABIN_OFFICER,
            "passenger": SpaceType.CABIN_PASSENGER,
        }.get(cabin_type, SpaceType.CABIN_CREW)

        return cls(
            space_id=space_id,
            name=name,
            space_type=space_type,
            category=SpaceCategory.LIVING,
            boundary=SpaceBoundary(
                points=points,
                deck_id=deck_id,
                z_min=z_min,
                z_max=z_max,
            ),
            deck_id=deck_id,
            is_manned=True,
            max_occupancy=2 if cabin_type == "crew" else 1,
        )

    @classmethod
    def create_machinery_space(
        cls,
        space_id: str,
        name: str,
        deck_id: str,
        points: List[Tuple[float, float]],
        z_min: float,
        z_max: float,
        machinery_type: SpaceType = SpaceType.ENGINE_ROOM,
    ) -> "SpaceDefinition":
        """Factory method for creating machinery spaces."""
        return cls(
            space_id=space_id,
            name=name,
            space_type=machinery_type,
            category=SpaceCategory.OPERATIONAL,
            boundary=SpaceBoundary(
                points=points,
                deck_id=deck_id,
                z_min=z_min,
                z_max=z_max,
            ),
            deck_id=deck_id,
            is_manned=True,
        )
