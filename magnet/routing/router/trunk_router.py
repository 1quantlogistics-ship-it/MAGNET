"""
magnet/routing/router/trunk_router.py - Trunk Router

MST-based routing algorithm for system trunks.
Connects system nodes through compartment graph with zone compliance.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any
from datetime import datetime
import logging

try:
    import networkx as nx
except ImportError:
    nx = None

from ..schema.system_type import SystemType, get_system_properties
from ..schema.system_node import SystemNode, NodeType
from ..schema.trunk_segment import TrunkSegment, TrunkSize, generate_trunk_id
from ..schema.system_topology import SystemTopology, TopologyStatus
from ..graph.compartment_graph import CompartmentGraph
from ..graph.node_graph import NodeGraph

__all__ = ['TrunkRouter', 'RoutingResult']

logger = logging.getLogger(__name__)


@dataclass
class RoutingResult:
    """Result of a routing operation."""
    success: bool
    topology: Optional[SystemTopology] = None
    trunk_count: int = 0
    total_length_m: float = 0.0
    zone_crossings: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    routing_time_ms: float = 0.0


class TrunkRouter:
    """
    MST-based trunk router for system networks.

    Routes system nodes by:
    1. Building a node graph from compartment adjacencies
    2. Finding minimum spanning tree to connect all nodes
    3. Converting MST edges to trunk segments
    4. Validating zone compliance
    5. Calculating trunk capacities

    Usage:
        router = TrunkRouter()
        result = router.route_system(
            system_type=SystemType.FUEL,
            nodes=fuel_nodes,
            compartment_graph=comp_graph,
        )
    """

    def __init__(
        self,
        zone_manager: Optional['ZoneManager'] = None,
        capacity_calculator: Optional['CapacityCalculator'] = None,
        allow_zone_violations: bool = False,
        max_reroute_attempts: int = 3,
    ):
        """
        Initialize trunk router.

        Args:
            zone_manager: Zone crossing validator (optional)
            capacity_calculator: Trunk sizing calculator (optional)
            allow_zone_violations: Whether to allow non-compliant routes
            max_reroute_attempts: Max attempts to find compliant route
        """
        if nx is None:
            raise ImportError("networkx is required for TrunkRouter")

        self._zone_manager = zone_manager
        self._capacity_calc = capacity_calculator
        self._allow_violations = allow_zone_violations
        self._max_reroute = max_reroute_attempts

    def route_system(
        self,
        system_type: SystemType,
        nodes: List[SystemNode],
        compartment_graph: 'nx.Graph',
        zone_boundaries: Optional[Dict[str, Set[str]]] = None,
        space_centers: Optional[Dict[str, Tuple[float, float, float]]] = None,
    ) -> RoutingResult:
        """
        Route a system by connecting all nodes.

        Args:
            system_type: Type of system to route
            nodes: List of SystemNodes to connect
            compartment_graph: Graph of compartment adjacencies
            zone_boundaries: zone_id -> set of space IDs
            space_centers: space_id -> center coordinates

        Returns:
            RoutingResult with topology and status
        """
        start_time = datetime.utcnow()
        result = RoutingResult(success=False)

        # Filter nodes for this system
        system_nodes = [n for n in nodes if n.system_type == system_type]

        if len(system_nodes) < 2:
            result.errors.append(
                f"Need at least 2 nodes to route, got {len(system_nodes)}"
            )
            return result

        # Check for sources
        sources = [n for n in system_nodes if n.node_type == NodeType.SOURCE]
        if not sources:
            result.errors.append("No source nodes found")
            return result

        # Create topology
        topology = SystemTopology(system_type=system_type)

        # Add nodes to topology
        for node in system_nodes:
            topology.add_node(node)

        # Build node graph
        try:
            node_graph = NodeGraph(system_type)
            G = node_graph.build(system_nodes, compartment_graph, zone_boundaries)
        except Exception as e:
            result.errors.append(f"Failed to build node graph: {e}")
            return result

        # Check connectivity
        if not nx.is_connected(G):
            result.warnings.append("Node graph is not fully connected")
            # Try to connect components
            components = list(nx.connected_components(G))
            if len(components) > 1:
                result.errors.append(
                    f"Cannot connect all nodes: {len(components)} disconnected groups"
                )
                return result

        # Build MST with deterministic tie-breaking
        try:
            mst = self._build_deterministic_mst(G)
        except Exception as e:
            result.errors.append(f"Failed to build MST: {e}")
            return result

        # Convert MST edges to trunks
        for from_node, to_node, edge_data in mst.edges(data=True):
            trunk = self._create_trunk(
                system_type=system_type,
                from_node_id=from_node,
                to_node_id=to_node,
                edge_data=edge_data,
                space_centers=space_centers,
            )

            # Validate zone compliance
            if self._zone_manager and not edge_data.get('is_valid', True):
                trunk.mark_zone_violation(
                    edge_data.get('violation_reason', 'Zone crossing not allowed')
                )

                if not self._allow_violations:
                    # Try to find alternative path
                    alt_trunk = self._find_alternative_route(
                        system_type, from_node, to_node,
                        G, compartment_graph, zone_boundaries,
                        space_centers,
                    )
                    if alt_trunk:
                        trunk = alt_trunk
                        result.warnings.append(
                            f"Rerouted trunk {trunk.trunk_id} to avoid zone violation"
                        )

            # Calculate capacity/sizing
            if self._capacity_calc:
                downstream_demand = self._calculate_downstream_demand(
                    trunk.to_node_id, topology, mst
                )
                trunk.size = self._capacity_calc.calculate_trunk_size(
                    system_type, downstream_demand
                )
                trunk.capacity = downstream_demand

            topology.add_trunk(trunk)

        # Calculate lengths
        if space_centers:
            for trunk in topology.trunks.values():
                trunk.calculate_length(space_centers)

        # Validate topology
        topology.validate()

        # Build result
        result.success = topology.status in (
            TopologyStatus.ROUTED, TopologyStatus.VALIDATED
        )
        result.topology = topology
        result.trunk_count = topology.trunk_count
        result.total_length_m = topology.total_length_m
        result.zone_crossings = sum(
            len(t.zone_crossings) for t in topology.trunks.values()
        )
        result.errors.extend(topology.validation_errors)
        result.warnings.extend(topology.validation_warnings)

        end_time = datetime.utcnow()
        result.routing_time_ms = (end_time - start_time).total_seconds() * 1000

        logger.info(
            f"Routed {system_type.value}: {result.trunk_count} trunks, "
            f"{result.total_length_m:.1f}m, {result.routing_time_ms:.1f}ms"
        )

        return result

    def _build_deterministic_mst(self, graph: 'nx.Graph') -> 'nx.Graph':
        """
        Build MST with deterministic tie-breaking.

        Uses Kruskal's algorithm with explicit edge sorting to ensure
        same inputs always produce same MST, even with equal-weight edges.

        Args:
            graph: NetworkX graph with 'cost' edge weights

        Returns:
            MST as NetworkX graph
        """
        # Get all edges with weights
        edges = []
        for u, v, data in graph.edges(data=True):
            cost = data.get('cost', data.get('weight', 1.0))
            # Tiebreaker: sorted node IDs
            tiebreaker = tuple(sorted([u, v]))
            edges.append((cost, tiebreaker, u, v, data))

        # Sort by (cost, tiebreaker) for determinism
        edges.sort(key=lambda x: (x[0], x[1]))

        # Kruskal's algorithm with union-find
        parent = {node: node for node in graph.nodes()}
        rank = {node: 0 for node in graph.nodes()}

        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            px, py = find(x), find(y)
            if px == py:
                return False
            if rank[px] < rank[py]:
                px, py = py, px
            parent[py] = px
            if rank[px] == rank[py]:
                rank[px] += 1
            return True

        # Build MST
        mst = nx.Graph()
        mst.add_nodes_from(graph.nodes(data=True))

        for cost, tiebreaker, u, v, data in edges:
            if union(u, v):
                mst.add_edge(u, v, **data)

        return mst

    def _create_trunk(
        self,
        system_type: SystemType,
        from_node_id: str,
        to_node_id: str,
        edge_data: Dict[str, Any],
        space_centers: Optional[Dict[str, Tuple[float, float, float]]],
    ) -> TrunkSegment:
        """Create trunk segment from edge data."""
        path_spaces = edge_data.get('path_spaces', [])
        path_length = edge_data.get('path_length', 0.0)

        # Generate deterministic trunk ID from content
        trunk = TrunkSegment(
            trunk_id=generate_trunk_id(
                system_type=system_type.value,
                from_node_id=from_node_id,
                to_node_id=to_node_id,
                path_spaces=path_spaces,
            ),
            system_type=system_type,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
        )

        trunk.set_path(path_spaces)
        trunk.length_m = path_length

        # Record zone crossings
        zone_crossings = edge_data.get('zone_crossings', 0)
        # Would need actual zone IDs from edge data
        for i in range(zone_crossings):
            trunk.add_zone_crossing(f"zone_{i}")

        return trunk

    def _find_alternative_route(
        self,
        system_type: SystemType,
        from_node: str,
        to_node: str,
        node_graph: 'nx.Graph',
        compartment_graph: 'nx.Graph',
        zone_boundaries: Optional[Dict[str, Set[str]]],
        space_centers: Optional[Dict[str, Tuple[float, float, float]]],
    ) -> Optional[TrunkSegment]:
        """
        Find alternative route avoiding zone violations.

        Args:
            system_type: System type
            from_node: Starting node ID
            to_node: Ending node ID
            node_graph: Node routing graph
            compartment_graph: Compartment adjacency graph
            zone_boundaries: Zone definitions
            space_centers: Space center coordinates

        Returns:
            Alternative trunk segment, or None if no valid route found
        """
        # Get multiple paths and check each
        try:
            gen = nx.shortest_simple_paths(
                node_graph, from_node, to_node, weight='cost'
            )

            for i, path in enumerate(gen):
                if i >= self._max_reroute:
                    break

                # Check if this path has valid edges
                all_valid = True
                for j in range(len(path) - 1):
                    edge = node_graph.get_edge_data(path[j], path[j + 1])
                    if edge and not edge.get('is_valid', True):
                        all_valid = False
                        break

                if all_valid:
                    # Build trunk from this path
                    # Combine path spaces from each edge
                    combined_spaces = []
                    total_length = 0.0

                    for j in range(len(path) - 1):
                        edge = node_graph.get_edge_data(path[j], path[j + 1])
                        if edge:
                            spaces = edge.get('path_spaces', [])
                            if j == 0:
                                combined_spaces.extend(spaces)
                            else:
                                combined_spaces.extend(spaces[1:])  # Skip duplicate
                            total_length += edge.get('path_length', 0.0)

                    trunk = TrunkSegment(
                        trunk_id=generate_trunk_id(
                            system_type=system_type.value,
                            from_node_id=from_node,
                            to_node_id=to_node,
                            path_spaces=combined_spaces,
                        ),
                        system_type=system_type,
                        from_node_id=from_node,
                        to_node_id=to_node,
                    )
                    trunk.set_path(combined_spaces)
                    trunk.length_m = total_length
                    trunk.routing_notes = f"Alternative route #{i+1}"

                    return trunk

        except Exception as e:
            logger.debug(f"Failed to find alternative route: {e}")

        return None

    def _calculate_downstream_demand(
        self,
        node_id: str,
        topology: SystemTopology,
        mst: 'nx.Graph',
    ) -> float:
        """
        Calculate total downstream demand for capacity sizing.

        Traverses MST from node toward leaves, summing consumer demands.

        Args:
            node_id: Node to calculate downstream demand for
            topology: System topology with node data
            mst: Minimum spanning tree

        Returns:
            Total downstream demand in system units
        """
        # Use BFS from node to find downstream consumers
        # In a tree, "downstream" depends on direction from sources

        node = topology.get_node(node_id)
        if not node:
            return 0.0

        # If this is a consumer, return its demand
        if node.node_type == NodeType.CONSUMER:
            return node.demand_units

        # Sum demand of all connected nodes (simplified)
        total_demand = 0.0
        visited = {node_id}
        queue = list(mst.neighbors(node_id))

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            current_node = topology.get_node(current)
            if current_node and current_node.node_type == NodeType.CONSUMER:
                total_demand += current_node.demand_units

            for neighbor in mst.neighbors(current):
                if neighbor not in visited:
                    queue.append(neighbor)

        return total_demand

    def route_with_redundancy(
        self,
        system_type: SystemType,
        nodes: List[SystemNode],
        compartment_graph: 'nx.Graph',
        zone_boundaries: Optional[Dict[str, Set[str]]] = None,
        space_centers: Optional[Dict[str, Tuple[float, float, float]]] = None,
    ) -> RoutingResult:
        """
        Route system with redundant paths for critical consumers.

        First routes with MST, then adds redundant paths for nodes
        that require redundant feeds.

        Args:
            system_type: Type of system to route
            nodes: List of SystemNodes to connect
            compartment_graph: Graph of compartment adjacencies
            zone_boundaries: zone_id -> set of space IDs
            space_centers: space_id -> center coordinates

        Returns:
            RoutingResult with topology including redundant paths
        """
        # First do primary routing
        result = self.route_system(
            system_type, nodes, compartment_graph,
            zone_boundaries, space_centers
        )

        if not result.success or not result.topology:
            return result

        topology = result.topology
        props = get_system_properties(system_type)

        # Check if redundancy is required
        if not props.requires_redundancy:
            return result

        # Find nodes requiring redundant feeds
        redundant_nodes = [
            n for n in nodes
            if n.system_type == system_type and n.requires_redundant_feed
        ]

        if not redundant_nodes:
            # No explicit redundancy requirements
            return result

        # Build node graph for finding alternative paths
        node_graph = NodeGraph(system_type)
        G = node_graph.build(
            [n for n in nodes if n.system_type == system_type],
            compartment_graph, zone_boundaries
        )

        # Find sources
        sources = [n.node_id for n in nodes
                   if n.system_type == system_type and n.node_type == NodeType.SOURCE]

        # Add redundant paths
        for node in redundant_nodes:
            # Find existing trunk to this node
            existing_trunks = [
                t for t in topology.trunks.values()
                if t.to_node_id == node.node_id or t.from_node_id == node.node_id
            ]

            if not existing_trunks:
                continue

            # Try to find alternative path from a source
            for source_id in sources:
                # Get existing path edges to exclude
                exclude_edges = []
                for trunk in existing_trunks:
                    exclude_edges.append((trunk.from_node_id, trunk.to_node_id))

                # Find alternative
                alt_path = self._find_alternative_path_avoiding_edges(
                    G, source_id, node.node_id, exclude_edges
                )

                if alt_path and len(alt_path) >= 2:
                    # Get path through spaces first for deterministic ID
                    combined_spaces = self._get_combined_path_spaces(
                        G, alt_path
                    )

                    # Create redundant trunk with deterministic ID
                    trunk = TrunkSegment(
                        trunk_id=generate_trunk_id(
                            system_type=system_type.value,
                            from_node_id=source_id,
                            to_node_id=node.node_id,
                            path_spaces=combined_spaces,
                        ),
                        system_type=system_type,
                        from_node_id=source_id,
                        to_node_id=node.node_id,
                        is_redundant_path=True,
                    )

                    trunk.set_path(combined_spaces)

                    if space_centers:
                        trunk.calculate_length(space_centers)

                    # Link to primary trunk
                    if existing_trunks:
                        trunk.parallel_trunk_id = existing_trunks[0].trunk_id
                        existing_trunks[0].parallel_trunk_id = trunk.trunk_id

                    topology.add_trunk(trunk)
                    topology.has_redundancy = True

                    result.warnings.append(
                        f"Added redundant path to {node.node_id}"
                    )
                    break

        # Re-validate
        topology.validate()
        result.trunk_count = topology.trunk_count
        result.total_length_m = topology.total_length_m

        return result

    def _find_alternative_path_avoiding_edges(
        self,
        graph: 'nx.Graph',
        source: str,
        target: str,
        exclude_edges: List[Tuple[str, str]],
    ) -> Optional[List[str]]:
        """Find path avoiding specified edges."""
        temp_graph = graph.copy()

        for edge in exclude_edges:
            if temp_graph.has_edge(edge[0], edge[1]):
                temp_graph.remove_edge(edge[0], edge[1])
            if temp_graph.has_edge(edge[1], edge[0]):
                temp_graph.remove_edge(edge[1], edge[0])

        try:
            return nx.shortest_path(temp_graph, source, target, weight='cost')
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def _get_combined_path_spaces(
        self,
        graph: 'nx.Graph',
        node_path: List[str],
    ) -> List[str]:
        """Get combined space path from node path."""
        if len(node_path) < 2:
            return []

        combined = []
        for i in range(len(node_path) - 1):
            edge = graph.get_edge_data(node_path[i], node_path[i + 1])
            if edge:
                spaces = edge.get('path_spaces', [])
                if i == 0:
                    combined.extend(spaces)
                elif spaces:
                    combined.extend(spaces[1:])

        return combined
