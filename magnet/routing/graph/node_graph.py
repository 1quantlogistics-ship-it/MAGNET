"""
magnet/routing/graph/node_graph.py - Node Routing Graph

Builds a routing graph specifically for system nodes,
layered on top of the compartment graph.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any
import math
import logging

try:
    import networkx as nx
except ImportError:
    nx = None

from ..schema.system_type import SystemType, get_system_properties
from ..schema.system_node import SystemNode, NodeType

__all__ = ['NodeGraph', 'NodeGraphEdge']

logger = logging.getLogger(__name__)


@dataclass
class NodeGraphEdge:
    """Edge data for node routing graph."""
    from_node: str
    to_node: str
    path_spaces: List[str]  # Spaces along the path
    path_length: float
    zone_crossings: int
    cost: float
    is_valid: bool = True
    violation_reason: str = ""


class NodeGraph:
    """
    Node-to-node routing graph for a specific system type.

    Builds on top of CompartmentGraph to create a graph where:
    - Nodes are SystemNodes (sources, junctions, consumers)
    - Edges represent potential routing paths through spaces
    - Edge weights incorporate system-specific constraints

    Usage:
        node_graph = NodeGraph(system_type)
        G = node_graph.build(system_nodes, compartment_graph)

        # Find minimum spanning tree for routing
        mst = nx.minimum_spanning_tree(G, weight='cost')
    """

    def __init__(
        self,
        system_type: SystemType,
        zone_crossing_penalty: float = 10.0,
        non_routable_penalty: float = 50.0,
    ):
        """
        Initialize node graph builder.

        Args:
            system_type: The system type this graph is for
            zone_crossing_penalty: Additional cost per zone crossing
            non_routable_penalty: Additional cost for non-routable spaces
        """
        if nx is None:
            raise ImportError("networkx is required for NodeGraph")

        self._system_type = system_type
        self._properties = get_system_properties(system_type)
        self._zone_penalty = zone_crossing_penalty
        self._non_routable_penalty = non_routable_penalty

        self._graph: Optional[nx.Graph] = None
        self._edges: Dict[Tuple[str, str], NodeGraphEdge] = {}
        self._node_spaces: Dict[str, str] = {}  # node_id -> space_id

    @property
    def graph(self) -> 'nx.Graph':
        """Get the underlying networkx graph."""
        if self._graph is None:
            self._graph = nx.Graph()
        return self._graph

    @property
    def system_type(self) -> SystemType:
        """Get the system type for this graph."""
        return self._system_type

    def build(
        self,
        nodes: List[SystemNode],
        compartment_graph: 'nx.Graph',
        zone_boundaries: Optional[Dict[str, Set[str]]] = None,
    ) -> 'nx.Graph':
        """
        Build node routing graph.

        Args:
            nodes: List of SystemNodes to connect
            compartment_graph: Compartment adjacency graph
            zone_boundaries: zone_id -> set of space IDs

        Returns:
            NetworkX graph for node-to-node routing
        """
        self._graph = nx.Graph()
        self._edges.clear()
        self._node_spaces.clear()

        zone_boundaries = zone_boundaries or {}

        # Build space-to-zone lookup
        space_to_zone: Dict[str, str] = {}
        for zone_id, space_ids in zone_boundaries.items():
            for space_id in space_ids:
                space_to_zone[space_id] = zone_id

        # Filter nodes for this system type
        system_nodes = [n for n in nodes if n.system_type == self._system_type]

        if not system_nodes:
            logger.warning(f"No nodes found for system type {self._system_type}")
            return self._graph

        # Add nodes to graph
        for node in system_nodes:
            self._node_spaces[node.node_id] = node.space_id
            self._graph.add_node(
                node.node_id,
                space_id=node.space_id,
                node_type=node.node_type.value,
                is_critical=node.is_critical,
            )

        # Calculate edges between all node pairs
        for i, node_a in enumerate(system_nodes):
            for node_b in system_nodes[i + 1:]:
                self._add_node_edge(
                    node_a, node_b,
                    compartment_graph,
                    space_to_zone,
                )

        logger.info(
            f"Built node graph for {self._system_type.value}: "
            f"{self._graph.number_of_nodes()} nodes, "
            f"{self._graph.number_of_edges()} edges"
        )

        return self._graph

    def _add_node_edge(
        self,
        node_a: SystemNode,
        node_b: SystemNode,
        compartment_graph: 'nx.Graph',
        space_to_zone: Dict[str, str],
    ) -> None:
        """Add edge between two nodes based on compartment path."""
        space_a = node_a.space_id
        space_b = node_b.space_id

        # Check if spaces are in the compartment graph
        if space_a not in compartment_graph or space_b not in compartment_graph:
            logger.warning(
                f"Spaces {space_a} or {space_b} not in compartment graph"
            )
            return

        # Find shortest path through compartments
        try:
            path_spaces = nx.shortest_path(
                compartment_graph, space_a, space_b, weight='cost'
            )
        except nx.NetworkXNoPath:
            logger.debug(
                f"No path between {space_a} and {space_b} in compartment graph"
            )
            return

        # Calculate path metrics
        path_length = self._calculate_path_length(path_spaces, compartment_graph)
        zone_crossings = self._count_zone_crossings(path_spaces, space_to_zone)

        # Check for system-specific violations
        is_valid, violation = self._check_path_validity(
            path_spaces, compartment_graph, space_to_zone
        )

        # Calculate cost
        cost = path_length
        cost += zone_crossings * self._zone_penalty

        # Add penalty for non-routable spaces
        non_routable_count = self._count_non_routable_spaces(
            path_spaces, compartment_graph
        )
        cost += non_routable_count * self._non_routable_penalty

        # Add large penalty if invalid
        if not is_valid:
            cost += 1000.0

        edge = NodeGraphEdge(
            from_node=node_a.node_id,
            to_node=node_b.node_id,
            path_spaces=path_spaces,
            path_length=path_length,
            zone_crossings=zone_crossings,
            cost=cost,
            is_valid=is_valid,
            violation_reason=violation,
        )

        self._edges[(node_a.node_id, node_b.node_id)] = edge

        self._graph.add_edge(
            node_a.node_id,
            node_b.node_id,
            path_spaces=path_spaces,
            path_length=path_length,
            zone_crossings=zone_crossings,
            cost=cost,
            is_valid=is_valid,
            violation_reason=violation,
        )

    def _calculate_path_length(
        self,
        path_spaces: List[str],
        compartment_graph: 'nx.Graph',
    ) -> float:
        """Calculate total path length through spaces."""
        if len(path_spaces) < 2:
            return 0.0

        total = 0.0
        for i in range(len(path_spaces) - 1):
            edge_data = compartment_graph.get_edge_data(
                path_spaces[i], path_spaces[i + 1]
            )
            if edge_data:
                total += edge_data.get('distance', 0.0)

        return total

    def _count_zone_crossings(
        self,
        path_spaces: List[str],
        space_to_zone: Dict[str, str],
    ) -> int:
        """Count number of zone boundary crossings."""
        if len(path_spaces) < 2:
            return 0

        crossings = 0
        prev_zone = space_to_zone.get(path_spaces[0], "")

        for space_id in path_spaces[1:]:
            curr_zone = space_to_zone.get(space_id, "")
            if curr_zone != prev_zone and prev_zone and curr_zone:
                crossings += 1
            prev_zone = curr_zone

        return crossings

    def _count_non_routable_spaces(
        self,
        path_spaces: List[str],
        compartment_graph: 'nx.Graph',
    ) -> int:
        """Count non-routable spaces in path."""
        count = 0
        for space_id in path_spaces:
            node_data = compartment_graph.nodes.get(space_id, {})
            if not node_data.get('is_routable', True):
                count += 1
        return count

    def _check_path_validity(
        self,
        path_spaces: List[str],
        compartment_graph: 'nx.Graph',
        space_to_zone: Dict[str, str],
    ) -> Tuple[bool, str]:
        """
        Check if path is valid for this system type.

        Returns:
            Tuple of (is_valid, violation_reason)
        """
        # Check prohibited zones
        for space_id in path_spaces:
            node_data = compartment_graph.nodes.get(space_id, {})
            space_type = node_data.get('space_type', '')

            # Check if space type is prohibited
            for prohibited in self._properties.prohibited_zones:
                if prohibited.lower() in space_type.lower():
                    return False, f"Path passes through prohibited zone: {prohibited}"

        # Check zone crossing rules
        if not self._properties.can_cross_fire_zone:
            # Check for fire zone crossings
            for i in range(len(path_spaces) - 1):
                edge_data = compartment_graph.get_edge_data(
                    path_spaces[i], path_spaces[i + 1]
                )
                if edge_data and edge_data.get('zone_boundary'):
                    zone_a = space_to_zone.get(path_spaces[i], "")
                    zone_b = space_to_zone.get(path_spaces[i + 1], "")
                    # Simplified check - would need zone type info
                    if 'fire' in zone_a.lower() or 'fire' in zone_b.lower():
                        return False, "Cannot cross fire zone boundary"

        # Check watertight crossing rules
        if not self._properties.can_cross_watertight:
            for i in range(len(path_spaces) - 1):
                edge_data = compartment_graph.get_edge_data(
                    path_spaces[i], path_spaces[i + 1]
                )
                if edge_data and edge_data.get('watertight_boundary'):
                    return False, "Cannot cross watertight boundary"

        return True, ""

    def get_edge(
        self,
        from_node: str,
        to_node: str,
    ) -> Optional[NodeGraphEdge]:
        """Get edge data between two nodes."""
        key = (from_node, to_node)
        if key in self._edges:
            return self._edges[key]
        return self._edges.get((to_node, from_node))

    def get_minimum_spanning_tree(self) -> 'nx.Graph':
        """
        Get minimum spanning tree for connecting all nodes.

        Returns:
            MST as NetworkX graph
        """
        if self._graph is None or self._graph.number_of_nodes() == 0:
            return nx.Graph()

        return nx.minimum_spanning_tree(self._graph, weight='cost')

    def get_all_paths(
        self,
        from_node: str,
        to_node: str,
        max_paths: int = 5,
    ) -> List[List[str]]:
        """
        Get multiple shortest paths between nodes.

        Args:
            from_node: Starting node ID
            to_node: Ending node ID
            max_paths: Maximum number of paths to return

        Returns:
            List of paths (each path is list of node IDs)
        """
        if self._graph is None:
            return []

        try:
            gen = nx.shortest_simple_paths(
                self._graph, from_node, to_node, weight='cost'
            )
            paths = []
            for i, path in enumerate(gen):
                if i >= max_paths:
                    break
                paths.append(path)
            return paths
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
