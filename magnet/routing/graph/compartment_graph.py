"""
magnet/routing/graph/compartment_graph.py - Compartment Graph Builder

Builds a graph representation of the vessel interior for trunk routing.
Nodes represent spaces/compartments, edges represent adjacencies.

Integrates with Module 59 (Interior Layout) SpaceInstance data.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any, Protocol
import math
import logging

# NetworkX for graph operations
try:
    import networkx as nx
except ImportError:
    nx = None  # Handle gracefully in code

__all__ = ['CompartmentGraph', 'CompartmentNode', 'CompartmentEdge', 'SpaceProvider']

logger = logging.getLogger(__name__)


# =========================================================================
# Protocol for Space Data
# =========================================================================

class SpaceProvider(Protocol):
    """Protocol for space data providers (M59 integration)."""

    @property
    def instance_id(self) -> str:
        """Unique space identifier."""
        ...

    @property
    def space_type(self) -> str:
        """Type of space (e.g., 'engine_room', 'corridor')."""
        ...

    @property
    def deck_id(self) -> str:
        """Deck this space is on."""
        ...

    @property
    def connected_spaces(self) -> List[str]:
        """List of connected space IDs."""
        ...

    def get_center(self) -> Tuple[float, float, float]:
        """Get space center coordinates."""
        ...

    def get_bounds(self) -> Tuple[
        Tuple[float, float, float],  # min (x, y, z)
        Tuple[float, float, float],  # max (x, y, z)
    ]:
        """Get space bounding box."""
        ...


# =========================================================================
# Data Classes
# =========================================================================

@dataclass
class CompartmentNode:
    """
    Node data for compartment graph.

    Represents a space/compartment in the routing graph.
    """
    space_id: str
    space_type: str
    deck_id: str
    center: Tuple[float, float, float]
    is_routable: bool = True
    zone_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'space_id': self.space_id,
            'space_type': self.space_type,
            'deck_id': self.deck_id,
            'center': list(self.center),
            'is_routable': self.is_routable,
            'zone_id': self.zone_id,
            'metadata': self.metadata,
        }


@dataclass
class CompartmentEdge:
    """
    Edge data for compartment graph.

    Represents adjacency between two spaces.
    """
    from_space: str
    to_space: str
    distance: float
    crossing_type: str  # "adjacent", "door", "penetration", "stair", "hatch"
    zone_boundary: bool = False
    watertight_boundary: bool = False
    cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'from_space': self.from_space,
            'to_space': self.to_space,
            'distance': self.distance,
            'crossing_type': self.crossing_type,
            'zone_boundary': self.zone_boundary,
            'watertight_boundary': self.watertight_boundary,
            'cost': self.cost,
        }


# =========================================================================
# Compartment Graph Builder
# =========================================================================

class CompartmentGraph:
    """
    Builds compartment adjacency graph for routing.

    Creates a graph where:
    - Nodes are spaces (from M59 InteriorLayout)
    - Edges are adjacencies between spaces
    - Edge weights include distance and crossing costs

    Usage:
        graph_builder = CompartmentGraph()
        G = graph_builder.build(spaces_dict)

        # Find shortest path
        path = nx.shortest_path(G, source, target, weight='cost')
    """

    def __init__(
        self,
        adjacency_tolerance_m: float = 0.5,
        base_crossing_cost: float = 1.0,
        zone_crossing_cost: float = 10.0,
        watertight_crossing_cost: float = 5.0,
        deck_crossing_cost: float = 3.0,
    ):
        """
        Initialize compartment graph builder.

        Args:
            adjacency_tolerance_m: Max gap to consider spaces adjacent
            base_crossing_cost: Base cost for any space transition
            zone_crossing_cost: Additional cost for zone boundary crossing
            watertight_crossing_cost: Additional cost for WT boundary
            deck_crossing_cost: Additional cost for vertical crossing
        """
        if nx is None:
            raise ImportError("networkx is required for CompartmentGraph")

        self._tolerance = adjacency_tolerance_m
        self._base_cost = base_crossing_cost
        self._zone_cost = zone_crossing_cost
        self._wt_cost = watertight_crossing_cost
        self._deck_cost = deck_crossing_cost

        self._graph: Optional[nx.Graph] = None
        self._nodes: Dict[str, CompartmentNode] = {}
        self._edges: Dict[Tuple[str, str], CompartmentEdge] = {}

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def graph(self) -> 'nx.Graph':
        """Get the underlying networkx graph."""
        if self._graph is None:
            self._graph = nx.Graph()
        return self._graph

    @property
    def node_count(self) -> int:
        """Number of nodes in graph."""
        return self._graph.number_of_nodes() if self._graph else 0

    @property
    def edge_count(self) -> int:
        """Number of edges in graph."""
        return self._graph.number_of_edges() if self._graph else 0

    def get_node(self, space_id: str) -> Optional[CompartmentNode]:
        """Get node data by space ID."""
        return self._nodes.get(space_id)

    def get_edge(
        self,
        from_space: str,
        to_space: str,
    ) -> Optional[CompartmentEdge]:
        """Get edge data between two spaces."""
        key = (from_space, to_space)
        if key in self._edges:
            return self._edges[key]
        # Try reverse
        return self._edges.get((to_space, from_space))

    # =========================================================================
    # Build Graph
    # =========================================================================

    def build(
        self,
        spaces: Dict[str, Any],
        zone_boundaries: Optional[Dict[str, Set[str]]] = None,
        watertight_boundaries: Optional[Set[Tuple[str, str]]] = None,
    ) -> 'nx.Graph':
        """
        Build compartment graph from spaces.

        Args:
            spaces: Dictionary of space_id -> space object (SpaceInstance or dict)
            zone_boundaries: zone_id -> set of space IDs in that zone
            watertight_boundaries: Set of (space1, space2) at WT boundaries

        Returns:
            NetworkX graph for routing pathfinding
        """
        self._graph = nx.Graph()
        self._nodes.clear()
        self._edges.clear()

        zone_boundaries = zone_boundaries or {}
        watertight_boundaries = watertight_boundaries or set()

        # Build zone lookup
        space_to_zone: Dict[str, str] = {}
        for zone_id, space_ids in zone_boundaries.items():
            for space_id in space_ids:
                space_to_zone[space_id] = zone_id

        # Add nodes for each space
        for space_id, space in spaces.items():
            self._add_space_node(space, space_to_zone.get(space_id))

        # Add edges from explicit connections
        for space_id, space in spaces.items():
            connected = self._get_connected_spaces(space)
            for connected_id in connected:
                if connected_id in spaces:
                    self._add_edge_from_connection(
                        space, spaces[connected_id],
                        space_to_zone, watertight_boundaries
                    )

        # Detect additional adjacencies from geometry
        self._detect_adjacencies(spaces, space_to_zone, watertight_boundaries)

        logger.info(
            f"Built compartment graph: {self.node_count} nodes, "
            f"{self.edge_count} edges"
        )

        return self._graph

    def _add_space_node(
        self,
        space: Any,
        zone_id: Optional[str] = None,
    ) -> None:
        """Add a node for a space."""
        space_id = self._get_space_id(space)
        space_type = self._get_space_type(space)
        deck_id = self._get_deck_id(space)
        center = self._get_center(space)

        # Determine if space is routable for system trunks
        is_routable = self._is_routable_space(space_type)

        node = CompartmentNode(
            space_id=space_id,
            space_type=space_type,
            deck_id=deck_id,
            center=center,
            is_routable=is_routable,
            zone_id=zone_id,
        )

        self._nodes[space_id] = node

        self._graph.add_node(
            space_id,
            space_type=space_type,
            deck_id=deck_id,
            center=center,
            is_routable=is_routable,
            zone_id=zone_id,
        )

    def _is_routable_space(self, space_type: str) -> bool:
        """Determine if systems can route through this space type."""
        space_type_lower = space_type.lower()

        # Typically routable space types
        routable_keywords = [
            'corridor', 'passage', 'trunk', 'duct', 'pipe',
            'machinery', 'engine', 'pump', 'hvac', 'electrical',
            'void', 'cofferdam', 'utility', 'service', 'technical',
            'store', 'locker', 'access'
        ]

        # Typically NOT routable for main trunks (consumer endpoints only)
        non_routable_keywords = [
            'cabin', 'berth', 'stateroom', 'mess', 'galley',
            'cic', 'bridge', 'head', 'shower', 'toilet', 'bathroom',
            'office', 'conference', 'lounge', 'recreation'
        ]

        # Check non-routable first (more restrictive)
        for kw in non_routable_keywords:
            if kw in space_type_lower:
                return False

        for kw in routable_keywords:
            if kw in space_type_lower:
                return True

        # Default: routable (can always be excluded later)
        return True

    def _add_edge_from_connection(
        self,
        space_a: Any,
        space_b: Any,
        space_to_zone: Dict[str, str],
        watertight_boundaries: Set[Tuple[str, str]],
    ) -> None:
        """Add edge from explicit connection."""
        id_a = self._get_space_id(space_a)
        id_b = self._get_space_id(space_b)

        if self._graph.has_edge(id_a, id_b):
            return

        # Calculate distance
        center_a = self._get_center(space_a)
        center_b = self._get_center(space_b)
        distance = self._calculate_distance(center_a, center_b)

        # Check boundaries
        zone_a = space_to_zone.get(id_a, "")
        zone_b = space_to_zone.get(id_b, "")
        is_zone_boundary = zone_a != zone_b and zone_a and zone_b

        is_wt_boundary = (
            (id_a, id_b) in watertight_boundaries or
            (id_b, id_a) in watertight_boundaries
        )

        # Check deck crossing
        deck_a = self._get_deck_id(space_a)
        deck_b = self._get_deck_id(space_b)
        is_deck_crossing = deck_a != deck_b

        # Calculate cost
        cost = self._base_cost + distance
        if is_zone_boundary:
            cost += self._zone_cost
        if is_wt_boundary:
            cost += self._wt_cost
        if is_deck_crossing:
            cost += self._deck_cost

        # Determine crossing type
        crossing_type = self._determine_crossing_type(
            center_a, center_b, is_wt_boundary, is_deck_crossing
        )

        edge = CompartmentEdge(
            from_space=id_a,
            to_space=id_b,
            distance=distance,
            crossing_type=crossing_type,
            zone_boundary=is_zone_boundary,
            watertight_boundary=is_wt_boundary,
            cost=cost,
        )

        self._edges[(id_a, id_b)] = edge

        self._graph.add_edge(
            id_a, id_b,
            distance=distance,
            cost=cost,
            crossing_type=crossing_type,
            zone_boundary=is_zone_boundary,
            watertight_boundary=is_wt_boundary,
        )

    def _detect_adjacencies(
        self,
        spaces: Dict[str, Any],
        space_to_zone: Dict[str, str],
        watertight_boundaries: Set[Tuple[str, str]],
    ) -> None:
        """Detect adjacencies not already in explicit connections."""
        space_list = list(spaces.values())

        for i, space_a in enumerate(space_list):
            for space_b in space_list[i + 1:]:
                id_a = self._get_space_id(space_a)
                id_b = self._get_space_id(space_b)

                # Skip if already connected
                if self._graph.has_edge(id_a, id_b):
                    continue

                # Check if spaces are adjacent based on geometry
                if self._are_adjacent(space_a, space_b):
                    self._add_edge_from_connection(
                        space_a, space_b,
                        space_to_zone, watertight_boundaries
                    )

    def _are_adjacent(self, space_a: Any, space_b: Any) -> bool:
        """Check if two spaces are geometrically adjacent."""
        bounds_a = self._get_bounds(space_a)
        bounds_b = self._get_bounds(space_b)

        if not bounds_a or not bounds_b:
            return False

        min_a, max_a = bounds_a
        min_b, max_b = bounds_b

        # Check overlap with tolerance in each dimension
        overlap_x = (
            min_a[0] - self._tolerance <= max_b[0] and
            max_a[0] + self._tolerance >= min_b[0]
        )
        overlap_y = (
            min_a[1] - self._tolerance <= max_b[1] and
            max_a[1] + self._tolerance >= min_b[1]
        )
        overlap_z = (
            min_a[2] - self._tolerance <= max_b[2] and
            max_a[2] + self._tolerance >= min_b[2]
        )

        # Adjacent if overlapping in 2 dimensions and touching in third
        if overlap_x and overlap_y:
            # Check if touching in Z (stacked)
            gap_z = max(min_a[2], min_b[2]) - min(max_a[2], max_b[2])
            if abs(gap_z) <= self._tolerance:
                return True

        if overlap_x and overlap_z:
            # Check if touching in Y (side by side port/starboard)
            gap_y = max(min_a[1], min_b[1]) - min(max_a[1], max_b[1])
            if abs(gap_y) <= self._tolerance:
                return True

        if overlap_y and overlap_z:
            # Check if touching in X (fore/aft)
            gap_x = max(min_a[0], min_b[0]) - min(max_a[0], max_b[0])
            if abs(gap_x) <= self._tolerance:
                return True

        return False

    def _determine_crossing_type(
        self,
        center_a: Tuple[float, float, float],
        center_b: Tuple[float, float, float],
        is_wt_boundary: bool,
        is_deck_crossing: bool,
    ) -> str:
        """Determine the type of crossing between spaces."""
        z_diff = abs(center_a[2] - center_b[2])

        if is_deck_crossing or z_diff > 1.0:
            # Significant vertical difference
            if z_diff > 2.5:
                return "stair"  # Full deck height
            else:
                return "hatch"  # Small vertical opening
        elif is_wt_boundary:
            return "penetration"  # WT bulkhead penetration
        else:
            return "door"  # Standard door/opening

    # =========================================================================
    # Space Data Accessors
    # =========================================================================

    def _get_space_id(self, space: Any) -> str:
        """Get space ID from space object or dict."""
        if isinstance(space, dict):
            return space.get('instance_id', space.get('space_id', ''))
        return getattr(space, 'instance_id', getattr(space, 'space_id', ''))

    def _get_space_type(self, space: Any) -> str:
        """Get space type from space object or dict."""
        if isinstance(space, dict):
            return space.get('space_type', 'unknown')
        return getattr(space, 'space_type', 'unknown')

    def _get_deck_id(self, space: Any) -> str:
        """Get deck ID from space object or dict."""
        if isinstance(space, dict):
            return space.get('deck_id', '')
        return getattr(space, 'deck_id', '')

    def _get_center(self, space: Any) -> Tuple[float, float, float]:
        """Get center coordinates from space object or dict."""
        if isinstance(space, dict):
            center = space.get('center')
            if center:
                return tuple(center)
            bounds = space.get('bounds')
            if bounds:
                min_pt = bounds.get('min', (0, 0, 0))
                max_pt = bounds.get('max', (0, 0, 0))
                return (
                    (min_pt[0] + max_pt[0]) / 2,
                    (min_pt[1] + max_pt[1]) / 2,
                    (min_pt[2] + max_pt[2]) / 2,
                )
            return (0.0, 0.0, 0.0)

        # Object with methods
        if hasattr(space, 'get_center'):
            return space.get_center()
        if hasattr(space, 'center'):
            return space.center
        if hasattr(space, 'bounds'):
            bounds = space.bounds
            if hasattr(bounds, 'center'):
                return bounds.center
            if hasattr(bounds, 'min') and hasattr(bounds, 'max'):
                return (
                    (bounds.min[0] + bounds.max[0]) / 2,
                    (bounds.min[1] + bounds.max[1]) / 2,
                    (bounds.min[2] + bounds.max[2]) / 2,
                )
        return (0.0, 0.0, 0.0)

    def _get_bounds(
        self,
        space: Any,
    ) -> Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float]]]:
        """Get bounding box from space object or dict."""
        if isinstance(space, dict):
            bounds = space.get('bounds')
            if bounds:
                min_pt = tuple(bounds.get('min', (0, 0, 0)))
                max_pt = tuple(bounds.get('max', (0, 0, 0)))
                return (min_pt, max_pt)
            return None

        if hasattr(space, 'get_bounds'):
            return space.get_bounds()
        if hasattr(space, 'bounds'):
            bounds = space.bounds
            if hasattr(bounds, 'min') and hasattr(bounds, 'max'):
                return (tuple(bounds.min), tuple(bounds.max))
        return None

    def _get_connected_spaces(self, space: Any) -> List[str]:
        """Get connected space IDs from space object or dict."""
        if isinstance(space, dict):
            return space.get('connected_spaces', [])
        return getattr(space, 'connected_spaces', [])

    def _calculate_distance(
        self,
        point_a: Tuple[float, float, float],
        point_b: Tuple[float, float, float],
    ) -> float:
        """Calculate Euclidean distance between two points."""
        return math.sqrt(
            (point_a[0] - point_b[0])**2 +
            (point_a[1] - point_b[1])**2 +
            (point_a[2] - point_b[2])**2
        )

    # =========================================================================
    # Graph Queries
    # =========================================================================

    def get_neighbors(self, space_id: str) -> List[str]:
        """Get adjacent spaces."""
        if self._graph is None or space_id not in self._graph:
            return []
        return list(self._graph.neighbors(space_id))

    def get_shortest_path(
        self,
        from_space: str,
        to_space: str,
        weight: str = 'cost',
    ) -> Optional[List[str]]:
        """
        Find shortest path between two spaces.

        Args:
            from_space: Starting space ID
            to_space: Ending space ID
            weight: Edge attribute to use as weight

        Returns:
            List of space IDs in path, or None if no path exists
        """
        if self._graph is None:
            return None

        try:
            return nx.shortest_path(
                self._graph, from_space, to_space, weight=weight
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def get_path_cost(self, path: List[str]) -> float:
        """Calculate total cost of a path."""
        if not path or len(path) < 2:
            return 0.0

        total = 0.0
        for i in range(len(path) - 1):
            edge_data = self._graph.get_edge_data(path[i], path[i + 1])
            if edge_data:
                total += edge_data.get('cost', 0.0)
        return total

    def get_routable_spaces(self) -> List[str]:
        """Get all routable space IDs."""
        return [
            nid for nid, node in self._nodes.items()
            if node.is_routable
        ]

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to dictionary."""
        return {
            'nodes': {nid: n.to_dict() for nid, n in self._nodes.items()},
            'edges': [e.to_dict() for e in self._edges.values()],
            'config': {
                'adjacency_tolerance_m': self._tolerance,
                'base_crossing_cost': self._base_cost,
                'zone_crossing_cost': self._zone_cost,
                'watertight_crossing_cost': self._wt_cost,
                'deck_crossing_cost': self._deck_cost,
            },
        }
