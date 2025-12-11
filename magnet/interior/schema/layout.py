"""
layout.py - Interior layout schema v1.0
BRAVO OWNS THIS FILE.

Module 59: Interior Layout
Defines layout structures for ship interior arrangement.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any
from datetime import datetime
import hashlib
import json
import logging
import uuid

from magnet.interior.schema.space import SpaceDefinition, SpaceConnection

__all__ = [
    'InteriorLayout',
    'LayoutVersion',
    'DeckLayout',
    'LayoutMetadata',
]

logger = logging.getLogger(__name__)


# =============================================================================
# LAYOUT VERSION
# =============================================================================

@dataclass
class LayoutVersion:
    """
    Version tracking for interior layouts.

    Attributes:
        version: Version number (monotonically increasing)
        update_id: Unique ID for this update
        prev_update_id: Previous update ID for chain tracking
        timestamp: When this version was created
        author: Who made the change
        description: What changed
    """

    version: int
    update_id: str
    prev_update_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    author: str = "system"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "version": self.version,
            "update_id": self.update_id,
            "prev_update_id": self.prev_update_id,
            "timestamp": self.timestamp.isoformat(),
            "author": self.author,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LayoutVersion":
        """Deserialize from dictionary."""
        return cls(
            version=data["version"],
            update_id=data["update_id"],
            prev_update_id=data.get("prev_update_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if isinstance(data["timestamp"], str) else data["timestamp"],
            author=data.get("author", "system"),
            description=data.get("description", ""),
        )

    @classmethod
    def create_initial(cls) -> "LayoutVersion":
        """Create initial version."""
        return cls(
            version=1,
            update_id=f"UPD-{uuid.uuid4().hex[:8].upper()}",
            prev_update_id=None,
            description="Initial layout",
        )

    def create_next(self, description: str = "", author: str = "system") -> "LayoutVersion":
        """Create next version in chain."""
        return LayoutVersion(
            version=self.version + 1,
            update_id=f"UPD-{uuid.uuid4().hex[:8].upper()}",
            prev_update_id=self.update_id,
            author=author,
            description=description,
        )


# =============================================================================
# LAYOUT METADATA
# =============================================================================

@dataclass
class LayoutMetadata:
    """
    Metadata for an interior layout.

    Attributes:
        design_id: Associated design ID
        ship_name: Name of the ship
        ship_type: Type of vessel
        loa: Length overall (m)
        beam: Beam (m)
        depth: Depth (m)
        num_decks: Number of decks
        total_area: Total interior area (m²)
        total_volume: Total interior volume (m³)
    """

    design_id: str
    ship_name: str = ""
    ship_type: str = ""

    # Principal dimensions
    loa: float = 0.0
    beam: float = 0.0
    depth: float = 0.0

    # Statistics
    num_decks: int = 0
    total_area: float = 0.0
    total_volume: float = 0.0
    total_spaces: int = 0

    # Capacity
    crew_capacity: int = 0
    passenger_capacity: int = 0

    # Regulatory
    class_society: str = ""
    flag_state: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "design_id": self.design_id,
            "ship_name": self.ship_name,
            "ship_type": self.ship_type,
            "loa": self.loa,
            "beam": self.beam,
            "depth": self.depth,
            "num_decks": self.num_decks,
            "total_area": self.total_area,
            "total_volume": self.total_volume,
            "total_spaces": self.total_spaces,
            "crew_capacity": self.crew_capacity,
            "passenger_capacity": self.passenger_capacity,
            "class_society": self.class_society,
            "flag_state": self.flag_state,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LayoutMetadata":
        """Deserialize from dictionary."""
        return cls(
            design_id=data["design_id"],
            ship_name=data.get("ship_name", ""),
            ship_type=data.get("ship_type", ""),
            loa=data.get("loa", 0.0),
            beam=data.get("beam", 0.0),
            depth=data.get("depth", 0.0),
            num_decks=data.get("num_decks", 0),
            total_area=data.get("total_area", 0.0),
            total_volume=data.get("total_volume", 0.0),
            total_spaces=data.get("total_spaces", 0),
            crew_capacity=data.get("crew_capacity", 0),
            passenger_capacity=data.get("passenger_capacity", 0),
            class_society=data.get("class_society", ""),
            flag_state=data.get("flag_state", ""),
        )


# =============================================================================
# DECK LAYOUT
# =============================================================================

@dataclass
class DeckLayout:
    """
    Layout for a single deck.

    Attributes:
        deck_id: Unique deck identifier
        deck_name: Human-readable name (e.g., "Main Deck", "Deck 3")
        deck_number: Numeric deck number (higher = upper)
        z_level: Z coordinate of deck floor
        height: Deck height (floor to ceiling)
        spaces: Spaces on this deck
        frame_start: Starting frame number
        frame_end: Ending frame number
        is_weather_deck: Whether exposed to weather
    """

    deck_id: str
    deck_name: str
    deck_number: int
    z_level: float
    height: float = 2.5

    # Spaces
    spaces: Dict[str, SpaceDefinition] = field(default_factory=dict)

    # Extent
    frame_start: Optional[float] = None
    frame_end: Optional[float] = None

    # Properties
    is_weather_deck: bool = False
    is_continuous: bool = True

    def __post_init__(self):
        """Generate ID if not provided."""
        if not self.deck_id:
            self.deck_id = f"DECK-{self.deck_number:02d}"

    @property
    def space_count(self) -> int:
        """Get number of spaces on this deck."""
        return len(self.spaces)

    @property
    def total_area(self) -> float:
        """Get total area of spaces on this deck."""
        return sum(s.area for s in self.spaces.values())

    def add_space(self, space: SpaceDefinition) -> None:
        """Add a space to this deck."""
        self.spaces[space.space_id] = space

    def remove_space(self, space_id: str) -> Optional[SpaceDefinition]:
        """Remove a space from this deck."""
        return self.spaces.pop(space_id, None)

    def get_space(self, space_id: str) -> Optional[SpaceDefinition]:
        """Get a space by ID."""
        return self.spaces.get(space_id)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "deck_id": self.deck_id,
            "deck_name": self.deck_name,
            "deck_number": self.deck_number,
            "z_level": self.z_level,
            "height": self.height,
            "spaces": {sid: s.to_dict() for sid, s in self.spaces.items()},
            "frame_start": self.frame_start,
            "frame_end": self.frame_end,
            "is_weather_deck": self.is_weather_deck,
            "is_continuous": self.is_continuous,
            "space_count": self.space_count,
            "total_area": self.total_area,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeckLayout":
        """Deserialize from dictionary."""
        deck = cls(
            deck_id=data["deck_id"],
            deck_name=data["deck_name"],
            deck_number=data["deck_number"],
            z_level=data["z_level"],
            height=data.get("height", 2.5),
            frame_start=data.get("frame_start"),
            frame_end=data.get("frame_end"),
            is_weather_deck=data.get("is_weather_deck", False),
            is_continuous=data.get("is_continuous", True),
        )

        for sid, sdata in data.get("spaces", {}).items():
            deck.spaces[sid] = SpaceDefinition.from_dict(sdata)

        return deck


# =============================================================================
# INTERIOR LAYOUT
# =============================================================================

@dataclass
class InteriorLayout:
    """
    Complete interior layout for a ship design.

    This is the main data structure for Module 59 (Interior Layout).
    It contains all spaces, decks, and their relationships.

    Attributes:
        layout_id: Unique identifier
        design_id: Associated design ID
        version_info: Version tracking
        metadata: Layout metadata
        decks: All deck layouts
        connections: Inter-space connections
        zones: Zone assignments
        arrangement_hash: Content hash for staleness detection
    """

    layout_id: str
    design_id: str
    version_info: LayoutVersion
    metadata: LayoutMetadata

    # Content
    decks: Dict[str, DeckLayout] = field(default_factory=dict)
    connections: List[SpaceConnection] = field(default_factory=list)
    zones: Dict[str, Set[str]] = field(default_factory=dict)  # zone_id -> space_ids

    # Hash for domain staleness (FIX #2 from V1.4)
    _arrangement_hash: Optional[str] = field(default=None, repr=False)

    def __post_init__(self):
        """Initialize defaults."""
        if not self.layout_id:
            self.layout_id = f"LAYOUT-{uuid.uuid4().hex[:8].upper()}"

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def arrangement_hash(self) -> str:
        """Get or compute arrangement hash for domain staleness."""
        if self._arrangement_hash is None:
            self._arrangement_hash = self._compute_hash()
        return self._arrangement_hash

    @property
    def space_count(self) -> int:
        """Get total number of spaces."""
        return sum(d.space_count for d in self.decks.values())

    @property
    def deck_count(self) -> int:
        """Get number of decks."""
        return len(self.decks)

    @property
    def total_area(self) -> float:
        """Get total interior area (m²)."""
        return sum(d.total_area for d in self.decks.values())

    @property
    def total_volume(self) -> float:
        """Get total interior volume (m³)."""
        return sum(
            s.volume for d in self.decks.values() for s in d.spaces.values()
        )

    # -------------------------------------------------------------------------
    # Hash Computation (FIX #2 - Domain Hashes)
    # -------------------------------------------------------------------------

    def _compute_hash(self) -> str:
        """Compute content hash of the layout."""
        data = {
            "layout_id": self.layout_id,
            "design_id": self.design_id,
            "version": self.version_info.version,
            "deck_count": self.deck_count,
            "space_count": self.space_count,
            "spaces": sorted([
                s.compute_hash()
                for d in self.decks.values()
                for s in d.spaces.values()
            ]),
        }
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def invalidate_hash(self) -> None:
        """Invalidate cached hash (call after modifications)."""
        self._arrangement_hash = None

    # -------------------------------------------------------------------------
    # Space Operations
    # -------------------------------------------------------------------------

    def get_space(self, space_id: str) -> Optional[SpaceDefinition]:
        """Get a space by ID from any deck."""
        for deck in self.decks.values():
            space = deck.get_space(space_id)
            if space:
                return space
        return None

    def get_all_spaces(self) -> List[SpaceDefinition]:
        """Get all spaces across all decks."""
        return [
            space
            for deck in self.decks.values()
            for space in deck.spaces.values()
        ]

    def add_space(self, space: SpaceDefinition) -> bool:
        """Add a space to the layout."""
        deck = self.decks.get(space.deck_id)
        if deck is None:
            logger.warning(f"Deck {space.deck_id} not found")
            return False

        deck.add_space(space)
        self.invalidate_hash()
        return True

    def update_space(self, space: SpaceDefinition) -> bool:
        """Update an existing space."""
        deck = self.decks.get(space.deck_id)
        if deck is None:
            return False

        if space.space_id not in deck.spaces:
            return False

        deck.spaces[space.space_id] = space
        self.invalidate_hash()
        return True

    def remove_space(self, space_id: str) -> Optional[SpaceDefinition]:
        """Remove a space from the layout."""
        for deck in self.decks.values():
            space = deck.remove_space(space_id)
            if space:
                self.invalidate_hash()
                # Remove from zones
                for zone_spaces in self.zones.values():
                    zone_spaces.discard(space_id)
                # Remove connections
                self.connections = [
                    c for c in self.connections
                    if c.from_space_id != space_id and c.to_space_id != space_id
                ]
                return space
        return None

    # -------------------------------------------------------------------------
    # Deck Operations
    # -------------------------------------------------------------------------

    def add_deck(self, deck: DeckLayout) -> None:
        """Add a deck to the layout."""
        self.decks[deck.deck_id] = deck
        self.invalidate_hash()

    def get_deck(self, deck_id: str) -> Optional[DeckLayout]:
        """Get a deck by ID."""
        return self.decks.get(deck_id)

    def get_decks_sorted(self) -> List[DeckLayout]:
        """Get decks sorted by deck number (ascending)."""
        return sorted(self.decks.values(), key=lambda d: d.deck_number)

    # -------------------------------------------------------------------------
    # Connection Operations
    # -------------------------------------------------------------------------

    def add_connection(self, connection: SpaceConnection) -> None:
        """Add a connection between spaces."""
        self.connections.append(connection)

        # Update connected_spaces in both spaces
        from_space = self.get_space(connection.from_space_id)
        to_space = self.get_space(connection.to_space_id)

        if from_space:
            from_space.connected_spaces.add(connection.to_space_id)
        if to_space:
            to_space.connected_spaces.add(connection.from_space_id)

        self.invalidate_hash()

    def get_connections_for_space(self, space_id: str) -> List[SpaceConnection]:
        """Get all connections involving a space."""
        return [
            c for c in self.connections
            if c.from_space_id == space_id or c.to_space_id == space_id
        ]

    # -------------------------------------------------------------------------
    # Zone Operations
    # -------------------------------------------------------------------------

    def assign_to_zone(self, zone_id: str, space_id: str) -> None:
        """Assign a space to a zone."""
        if zone_id not in self.zones:
            self.zones[zone_id] = set()
        self.zones[zone_id].add(space_id)

        space = self.get_space(space_id)
        if space:
            space.zone_id = zone_id

        self.invalidate_hash()

    def get_spaces_in_zone(self, zone_id: str) -> List[SpaceDefinition]:
        """Get all spaces in a zone."""
        space_ids = self.zones.get(zone_id, set())
        return [s for s in self.get_all_spaces() if s.space_id in space_ids]

    # -------------------------------------------------------------------------
    # Version Operations
    # -------------------------------------------------------------------------

    def create_new_version(self, description: str = "", author: str = "system") -> None:
        """Create a new version of the layout."""
        self.version_info = self.version_info.create_next(description, author)
        self.invalidate_hash()

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "layout_id": self.layout_id,
            "design_id": self.design_id,
            "version_info": self.version_info.to_dict(),
            "metadata": self.metadata.to_dict(),
            "decks": {did: d.to_dict() for did, d in self.decks.items()},
            "connections": [c.to_dict() for c in self.connections],
            "zones": {zid: list(sids) for zid, sids in self.zones.items()},
            "arrangement_hash": self.arrangement_hash,
            "space_count": self.space_count,
            "deck_count": self.deck_count,
            "total_area_m2": self.total_area,
            "total_volume_m3": self.total_volume,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InteriorLayout":
        """Deserialize from dictionary."""
        layout = cls(
            layout_id=data["layout_id"],
            design_id=data["design_id"],
            version_info=LayoutVersion.from_dict(data["version_info"]),
            metadata=LayoutMetadata.from_dict(data["metadata"]),
        )

        for did, ddata in data.get("decks", {}).items():
            layout.decks[did] = DeckLayout.from_dict(ddata)

        for cdata in data.get("connections", []):
            layout.connections.append(SpaceConnection.from_dict(cdata))

        for zid, sids in data.get("zones", {}).items():
            layout.zones[zid] = set(sids)

        layout._arrangement_hash = data.get("arrangement_hash")

        return layout

    @classmethod
    def create_empty(cls, design_id: str) -> "InteriorLayout":
        """Create an empty layout for a design."""
        return cls(
            layout_id=f"LAYOUT-{uuid.uuid4().hex[:8].upper()}",
            design_id=design_id,
            version_info=LayoutVersion.create_initial(),
            metadata=LayoutMetadata(design_id=design_id),
        )
