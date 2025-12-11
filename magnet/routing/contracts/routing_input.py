"""
magnet/routing/contracts/routing_input.py - Routing Input Contract

Defines immutable input contract that decouples the router from
DesignState internals, enabling independent testing and reuse.
"""

from dataclasses import dataclass, field
from typing import Dict, Set, List, Tuple, Optional, FrozenSet, Any
import hashlib

from magnet.routing.schema.system_type import SystemType
from magnet.routing.schema.system_node import SystemNode

__all__ = ['SpaceInfo', 'RoutingInputContract']


@dataclass(frozen=True)
class SpaceInfo:
    """
    Immutable space information for routing.

    Contains only the data needed for routing decisions,
    decoupled from the full space model.

    Attributes:
        space_id: Unique identifier for the space
        space_type: Type of space (machinery, corridor, accommodation, etc.)
        center: Center point coordinates (x, y, z) in meters
        is_routable: Whether systems can route through this space
        deck_id: Optional deck identifier for vertical organization
        zone_ids: Set of zone IDs this space belongs to
    """
    space_id: str
    space_type: str
    center: Tuple[float, float, float]
    is_routable: bool = True
    deck_id: Optional[str] = None
    zone_ids: FrozenSet[str] = field(default_factory=frozenset)

    def __hash__(self) -> int:
        return hash((self.space_id, self.space_type, self.center, self.is_routable))


@dataclass(frozen=True)
class RoutingInputContract:
    """
    Immutable contract defining all inputs needed for routing.

    This decouples the router from DesignState internals, enabling:
    - Independent testing with synthetic data
    - Caching based on contract hash
    - Clear documentation of routing requirements

    Attributes:
        spaces: Dictionary of space_id -> SpaceInfo
        adjacency: Dictionary of space_id -> set of adjacent space_ids
        fire_zones: Dictionary of zone_id -> set of space_ids in zone
        watertight_boundaries: Set of (space_a, space_b) watertight pairs
        system_nodes: Dictionary of SystemType -> list of nodes to route
        excluded_spaces: Spaces to avoid during routing
        max_zone_crossings: Maximum allowed zone crossings per trunk
    """

    # Spaces (converted to tuple for immutability)
    spaces: Tuple[Tuple[str, SpaceInfo], ...]

    # Adjacency (converted to tuple for immutability)
    adjacency: Tuple[Tuple[str, FrozenSet[str]], ...]

    # Zone boundaries
    fire_zones: Tuple[Tuple[str, FrozenSet[str]], ...]
    watertight_boundaries: FrozenSet[Tuple[str, str]]

    # System requirements (converted to tuple for immutability)
    system_nodes: Tuple[Tuple[str, Tuple[SystemNode, ...]], ...]

    # Constraints
    excluded_spaces: FrozenSet[str] = field(default_factory=frozenset)
    max_zone_crossings: int = 2

    @classmethod
    def create(
        cls,
        spaces: Dict[str, SpaceInfo],
        adjacency: Dict[str, Set[str]],
        fire_zones: Optional[Dict[str, Set[str]]] = None,
        watertight_boundaries: Optional[Set[Tuple[str, str]]] = None,
        system_nodes: Optional[Dict[SystemType, List[SystemNode]]] = None,
        excluded_spaces: Optional[Set[str]] = None,
        max_zone_crossings: int = 2,
    ) -> 'RoutingInputContract':
        """
        Create a RoutingInputContract from mutable inputs.

        This factory method converts mutable collections to immutable
        structures suitable for the frozen dataclass.

        Args:
            spaces: Dictionary of space_id -> SpaceInfo
            adjacency: Dictionary of space_id -> set of adjacent space_ids
            fire_zones: Optional dictionary of zone_id -> set of space_ids
            watertight_boundaries: Optional set of watertight boundary pairs
            system_nodes: Optional dictionary of SystemType -> list of nodes
            excluded_spaces: Optional set of spaces to exclude
            max_zone_crossings: Maximum zone crossings allowed

        Returns:
            Immutable RoutingInputContract
        """
        # Convert spaces
        spaces_tuple = tuple(sorted(spaces.items(), key=lambda x: x[0]))

        # Convert adjacency
        adjacency_tuple = tuple(
            (space_id, frozenset(neighbors))
            for space_id, neighbors in sorted(adjacency.items())
        )

        # Convert fire zones
        if fire_zones:
            fire_zones_tuple = tuple(
                (zone_id, frozenset(space_ids))
                for zone_id, space_ids in sorted(fire_zones.items())
            )
        else:
            fire_zones_tuple = ()

        # Convert watertight boundaries (normalize ordering)
        if watertight_boundaries:
            wt_normalized = frozenset(
                tuple(sorted([a, b])) for a, b in watertight_boundaries
            )
        else:
            wt_normalized = frozenset()

        # Convert system nodes
        if system_nodes:
            nodes_tuple = tuple(
                (st.value, tuple(nodes))
                for st, nodes in sorted(system_nodes.items(), key=lambda x: x[0].value)
            )
        else:
            nodes_tuple = ()

        return cls(
            spaces=spaces_tuple,
            adjacency=adjacency_tuple,
            fire_zones=fire_zones_tuple,
            watertight_boundaries=wt_normalized,
            system_nodes=nodes_tuple,
            excluded_spaces=frozenset(excluded_spaces or set()),
            max_zone_crossings=max_zone_crossings,
        )

    def __hash__(self) -> int:
        """
        Hash based on content for caching.

        Enables using the contract as a cache key.
        """
        return hash((
            self.spaces,
            self.adjacency,
            self.fire_zones,
            self.watertight_boundaries,
            len(self.system_nodes),
            self.max_zone_crossings,
        ))

    def content_hash(self) -> str:
        """
        Compute deterministic content hash string.

        Returns:
            SHA-256 hash of contract content (first 32 chars)
        """
        hasher = hashlib.sha256()

        # Hash spaces
        for space_id, space_info in self.spaces:
            hasher.update(f"space:{space_id}:{space_info.space_type}\n".encode())

        # Hash adjacency
        for space_id, neighbors in self.adjacency:
            neighbors_str = ','.join(sorted(neighbors))
            hasher.update(f"adj:{space_id}:{neighbors_str}\n".encode())

        # Hash fire zones
        for zone_id, space_ids in self.fire_zones:
            spaces_str = ','.join(sorted(space_ids))
            hasher.update(f"zone:{zone_id}:{spaces_str}\n".encode())

        # Hash system nodes
        for system_type, nodes in self.system_nodes:
            hasher.update(f"system:{system_type}:{len(nodes)}\n".encode())

        return hasher.hexdigest()[:32]

    # =========================================================================
    # Accessor Methods (convert back to mutable for convenience)
    # =========================================================================

    def get_spaces(self) -> Dict[str, SpaceInfo]:
        """Get spaces as mutable dictionary."""
        return dict(self.spaces)

    def get_adjacency(self) -> Dict[str, Set[str]]:
        """Get adjacency as mutable dictionary."""
        return {
            space_id: set(neighbors)
            for space_id, neighbors in self.adjacency
        }

    def get_fire_zones(self) -> Dict[str, Set[str]]:
        """Get fire zones as mutable dictionary."""
        return {
            zone_id: set(space_ids)
            for zone_id, space_ids in self.fire_zones
        }

    def get_watertight_boundaries(self) -> Set[Tuple[str, str]]:
        """Get watertight boundaries as mutable set."""
        return set(self.watertight_boundaries)

    def get_system_nodes(self) -> Dict[SystemType, List[SystemNode]]:
        """Get system nodes as mutable dictionary."""
        return {
            SystemType(st_value): list(nodes)
            for st_value, nodes in self.system_nodes
        }

    def get_nodes_for_system(self, system_type: SystemType) -> List[SystemNode]:
        """Get nodes for a specific system type."""
        for st_value, nodes in self.system_nodes:
            if st_value == system_type.value:
                return list(nodes)
        return []

    # =========================================================================
    # Query Methods
    # =========================================================================

    def is_adjacent(self, space_a: str, space_b: str) -> bool:
        """Check if two spaces are adjacent."""
        for space_id, neighbors in self.adjacency:
            if space_id == space_a:
                return space_b in neighbors
        return False

    def get_space_zone(self, space_id: str) -> Optional[str]:
        """Get the fire zone containing a space."""
        for zone_id, space_ids in self.fire_zones:
            if space_id in space_ids:
                return zone_id
        return None

    def is_watertight_boundary(self, space_a: str, space_b: str) -> bool:
        """Check if boundary between spaces is watertight."""
        normalized = tuple(sorted([space_a, space_b]))
        return normalized in self.watertight_boundaries

    def crosses_fire_zone(self, space_a: str, space_b: str) -> bool:
        """Check if transition between spaces crosses a fire zone boundary."""
        zone_a = self.get_space_zone(space_a)
        zone_b = self.get_space_zone(space_b)
        if zone_a is None or zone_b is None:
            return False
        return zone_a != zone_b
