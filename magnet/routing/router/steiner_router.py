"""
magnet/routing/router/steiner_router.py - Steiner Tree Router

Enhanced routing using Steiner tree algorithms for optimal
multi-source routing with shared path segments.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any
from datetime import datetime
import logging
import heapq

try:
    import networkx as nx
except ImportError:
    nx = None

from ..schema.system_type import SystemType, get_system_properties
from ..schema.system_node import SystemNode, NodeType
from ..schema.trunk_segment import TrunkSegment, generate_trunk_id
from ..schema.system_topology import SystemTopology, TopologyStatus

__all__ = ['SteinerRouter', 'SteinerResult', 'SteinerNode']

logger = logging.getLogger(__name__)


@dataclass
class SteinerNode:
    """
    A node in the Steiner tree.

    Can be either a terminal (actual system node) or a
    Steiner point (intermediate junction).
    """
    node_id: str
    space_id: str
    is_terminal: bool = True  # False for Steiner points
    parent_id: Optional[str] = None
    depth: int = 0
    accumulated_demand: float = 0.0


@dataclass
class SteinerResult:
    """Result from Steiner tree routing."""
    success: bool
    topology: Optional[SystemTopology] = None
    steiner_points: List[SteinerNode] = field(default_factory=list)
    trunk_count: int = 0
    total_length_m: float = 0.0
    shared_segments: int = 0  # Number of trunk segments serving multiple consumers
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class SteinerRouter:
    """
    Steiner tree-based router for optimal multi-source routing.

    Unlike simple MST, Steiner trees can introduce intermediate
    junction points (Steiner points) to minimize total cable/pipe
    length when connecting multiple sources to multiple consumers.

    Features:
    - Multiple source support with load balancing
    - Steiner point insertion for path optimization
    - Hierarchical trunk sizing based on accumulated demand
    - Zone-aware routing with configurable costs

    Usage:
        router = SteinerRouter()
        result = router.route_system(
            system_type=SystemType.ELECTRICAL_LV,
            nodes=electrical_nodes,
            compartment_graph=graph,
            sources=['main_swbd', 'emergency_swbd'],
        )
    """

    def __init__(
        self,
        zone_manager: Optional['ZoneManager'] = None,
        allow_steiner_points: bool = True,
        max_steiner_points: int = 10,
        steiner_point_cost: float = 0.5,  # Extra cost for adding Steiner point
    ):
        """
        Initialize Steiner router.

        Args:
            zone_manager: Zone crossing validator
            allow_steiner_points: Whether to insert Steiner points
            max_steiner_points: Maximum Steiner points to add
            steiner_point_cost: Cost multiplier for Steiner points
        """
        if nx is None:
            raise ImportError("networkx is required for SteinerRouter")

        self._zone_manager = zone_manager
        self._allow_steiner = allow_steiner_points
        self._max_steiner = max_steiner_points
        self._steiner_cost = steiner_point_cost

    def route_system(
        self,
        system_type: SystemType,
        nodes: List[SystemNode],
        compartment_graph: 'nx.Graph',
        sources: Optional[List[str]] = None,
        zone_boundaries: Optional[Dict[str, Set[str]]] = None,
        space_centers: Optional[Dict[str, Tuple[float, float, float]]] = None,
    ) -> SteinerResult:
        """
        Route system using Steiner tree algorithm.

        Args:
            system_type: Type of system to route
            nodes: List of SystemNodes to connect
            compartment_graph: Compartment adjacency graph
            sources: Optional list of source node IDs (if None, auto-detect)
            zone_boundaries: Zone definitions
            space_centers: Space center coordinates

        Returns:
            SteinerResult with topology
        """
        result = SteinerResult(success=False)

        # Filter nodes for this system
        system_nodes = [n for n in nodes if n.system_type == system_type]

        if len(system_nodes) < 2:
            result.errors.append(f"Need at least 2 nodes, got {len(system_nodes)}")
            return result

        # Identify sources
        if sources:
            source_nodes = [n for n in system_nodes if n.node_id in sources]
        else:
            source_nodes = [n for n in system_nodes if n.node_type == NodeType.SOURCE]

        if not source_nodes:
            result.errors.append("No source nodes found")
            return result

        # Identify consumers
        consumer_nodes = [
            n for n in system_nodes
            if n.node_type == NodeType.CONSUMER or n.node_type == NodeType.DISTRIBUTION
        ]

        if not consumer_nodes:
            result.errors.append("No consumer nodes found")
            return result

        # Create topology
        topology = SystemTopology(system_type=system_type)
        for node in system_nodes:
            topology.add_node(node)

        # Build terminal set
        terminals = set(n.node_id for n in system_nodes)

        # Compute Steiner tree
        try:
            steiner_tree, steiner_points = self._compute_steiner_tree(
                compartment_graph,
                terminals,
                [n.node_id for n in source_nodes],
                space_centers or {},
            )
        except Exception as e:
            result.errors.append(f"Steiner tree computation failed: {e}")
            return result

        result.steiner_points = steiner_points

        # Convert Steiner tree to trunks
        trunks = self._convert_to_trunks(
            steiner_tree,
            system_type,
            topology,
            compartment_graph,
            space_centers,
        )

        for trunk in trunks:
            topology.add_trunk(trunk)

        # Calculate shared segments
        result.shared_segments = sum(
            1 for t in trunks if t.capacity > 0  # Trunk serves multiple consumers
        )

        # Validate topology
        topology.validate()

        # Build result
        result.success = topology.status != TopologyStatus.FAILED
        result.topology = topology
        result.trunk_count = topology.trunk_count
        result.total_length_m = topology.total_length_m

        return result

    def _compute_steiner_tree(
        self,
        graph: 'nx.Graph',
        terminals: Set[str],
        sources: List[str],
        space_centers: Dict[str, Tuple[float, float, float]],
    ) -> Tuple['nx.Graph', List[SteinerNode]]:
        """
        Compute approximate Steiner tree connecting terminals.

        Uses the metric closure heuristic:
        1. Compute shortest paths between all terminal pairs
        2. Build MST of metric closure
        3. Expand MST edges back to actual paths
        4. Remove redundant edges

        Args:
            graph: Base compartment graph
            terminals: Set of terminal node IDs
            sources: List of source node IDs
            space_centers: Space center coordinates

        Returns:
            Tuple of (Steiner tree graph, list of Steiner points)
        """
        # Step 1: Compute metric closure (shortest paths between all terminals)
        metric_closure = nx.Graph()
        terminal_list = list(terminals)

        for i, t1 in enumerate(terminal_list):
            if t1 not in graph:
                continue
            for t2 in terminal_list[i + 1:]:
                if t2 not in graph:
                    continue
                try:
                    path = nx.shortest_path(graph, t1, t2, weight='cost')
                    length = nx.shortest_path_length(graph, t1, t2, weight='cost')
                    metric_closure.add_edge(t1, t2, weight=length, path=path)
                except nx.NetworkXNoPath:
                    pass

        if metric_closure.number_of_edges() == 0:
            raise ValueError("No paths found between terminals")

        # Step 2: Build MST of metric closure with deterministic tie-breaking
        mst_closure = self._build_deterministic_mst(metric_closure)

        # Step 3: Expand MST edges to actual paths
        steiner_tree = nx.Graph()
        for u, v, data in mst_closure.edges(data=True):
            path = data.get('path', [u, v])
            for i in range(len(path) - 1):
                if not steiner_tree.has_edge(path[i], path[i + 1]):
                    # Get original edge data
                    orig_data = graph.get_edge_data(path[i], path[i + 1]) or {}
                    steiner_tree.add_edge(path[i], path[i + 1], **orig_data)

        # Step 4: Identify Steiner points (non-terminal nodes)
        steiner_points = []
        for node in steiner_tree.nodes():
            if node not in terminals:
                space_id = node  # In our graph, node IDs are space IDs
                sp = SteinerNode(
                    node_id=f"steiner_{node}",
                    space_id=space_id,
                    is_terminal=False,
                )
                steiner_points.append(sp)

        # Step 5: Prune degree-1 non-terminals (optional optimization)
        pruned = True
        while pruned:
            pruned = False
            for node in list(steiner_tree.nodes()):
                if node not in terminals and steiner_tree.degree(node) == 1:
                    steiner_tree.remove_node(node)
                    pruned = True

        return steiner_tree, steiner_points

    def _build_deterministic_mst(self, graph: 'nx.Graph') -> 'nx.Graph':
        """Build MST with deterministic tie-breaking."""
        edges = []
        for u, v, data in graph.edges(data=True):
            weight = data.get('weight', 1.0)
            tiebreaker = tuple(sorted([u, v]))
            edges.append((weight, tiebreaker, u, v, data))

        edges.sort(key=lambda x: (x[0], x[1]))

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

        mst = nx.Graph()
        for node in graph.nodes():
            mst.add_node(node)

        for weight, tiebreaker, u, v, data in edges:
            if union(u, v):
                mst.add_edge(u, v, **data)

        return mst

    def _convert_to_trunks(
        self,
        steiner_tree: 'nx.Graph',
        system_type: SystemType,
        topology: SystemTopology,
        compartment_graph: 'nx.Graph',
        space_centers: Optional[Dict[str, Tuple[float, float, float]]],
    ) -> List[TrunkSegment]:
        """
        Convert Steiner tree edges to trunk segments.

        Attempts to merge sequential edges into longer trunks
        where possible for cleaner routing.

        Args:
            steiner_tree: The Steiner tree
            system_type: System type
            topology: Topology with nodes
            compartment_graph: Original compartment graph
            space_centers: Space centers for length calculation

        Returns:
            List of trunk segments
        """
        trunks = []

        # Find terminal nodes in tree
        terminal_nodes = set(topology.nodes.keys())

        # Track visited edges
        visited_edges = set()

        # For each pair of terminals, find path and create trunk
        terminals_in_tree = [n for n in steiner_tree.nodes() if n in terminal_nodes]

        # Use spanning tree from first source to create hierarchical trunks
        sources = [
            n.node_id for n in topology.nodes.values()
            if n.node_type == NodeType.SOURCE
        ]

        if sources and sources[0] in steiner_tree:
            root = sources[0]
        else:
            root = terminals_in_tree[0] if terminals_in_tree else None

        if root is None:
            return trunks

        # BFS from root to create directed tree
        parent_map = {root: None}
        queue = [root]
        while queue:
            current = queue.pop(0)
            for neighbor in steiner_tree.neighbors(current):
                if neighbor not in parent_map:
                    parent_map[neighbor] = current
                    queue.append(neighbor)

        # Create trunk for each terminal (except root)
        for terminal in terminals_in_tree:
            if terminal == root:
                continue

            # Find path back to nearest branch point or terminal
            path = [terminal]
            current = terminal
            while parent_map.get(current) is not None:
                parent = parent_map[current]
                path.append(parent)
                # Stop at next terminal or branch point
                if parent in terminal_nodes or steiner_tree.degree(parent) > 2:
                    break
                current = parent

            if len(path) < 2:
                continue

            # Create trunk
            from_node = path[-1]  # Closer to root
            to_node = path[0]     # Terminal

            # Get path spaces
            path_spaces = list(path)

            trunk = TrunkSegment(
                trunk_id=generate_trunk_id(
                    system_type=system_type.value,
                    from_node_id=from_node,
                    to_node_id=to_node,
                    path_spaces=path_spaces,
                ),
                system_type=system_type,
                from_node_id=from_node,
                to_node_id=to_node,
            )

            trunk.set_path(path_spaces)

            # Calculate length
            if space_centers:
                trunk.calculate_length(space_centers)

            trunks.append(trunk)

        return trunks

    def route_multi_source(
        self,
        system_type: SystemType,
        nodes: List[SystemNode],
        compartment_graph: 'nx.Graph',
        sources: List[str],
        load_balance: bool = True,
        zone_boundaries: Optional[Dict[str, Set[str]]] = None,
        space_centers: Optional[Dict[str, Tuple[float, float, float]]] = None,
    ) -> SteinerResult:
        """
        Route with multiple sources and optional load balancing.

        Creates a forest of Steiner trees, one rooted at each source,
        with consumers assigned to minimize total cable length while
        optionally balancing load across sources.

        Args:
            system_type: Type of system
            nodes: All system nodes
            compartment_graph: Compartment graph
            sources: List of source node IDs
            load_balance: Whether to balance load across sources
            zone_boundaries: Zone definitions
            space_centers: Space centers

        Returns:
            SteinerResult with combined topology
        """
        result = SteinerResult(success=False)

        system_nodes = [n for n in nodes if n.system_type == system_type]
        source_nodes = [n for n in system_nodes if n.node_id in sources]
        consumer_nodes = [
            n for n in system_nodes
            if n.node_id not in sources
        ]

        if len(source_nodes) < 1:
            result.errors.append("No source nodes specified")
            return result

        if len(consumer_nodes) < 1:
            result.errors.append("No consumer nodes found")
            return result

        # Assign consumers to nearest source
        consumer_assignments: Dict[str, List[SystemNode]] = {s: [] for s in sources}
        source_loads: Dict[str, float] = {s: 0.0 for s in sources}

        for consumer in consumer_nodes:
            # Find nearest source
            best_source = None
            best_distance = float('inf')

            for source_id in sources:
                if source_id not in compartment_graph:
                    continue
                consumer_space = consumer.space_id
                if consumer_space not in compartment_graph:
                    continue

                try:
                    distance = nx.shortest_path_length(
                        compartment_graph, source_id, consumer_space, weight='cost'
                    )
                    # Adjust for load balancing
                    if load_balance:
                        distance *= (1 + source_loads[source_id] * 0.1)

                    if distance < best_distance:
                        best_distance = distance
                        best_source = source_id
                except nx.NetworkXNoPath:
                    pass

            if best_source:
                consumer_assignments[best_source].append(consumer)
                source_loads[best_source] += consumer.demand_units

        # Create topology
        topology = SystemTopology(system_type=system_type)
        for node in system_nodes:
            topology.add_node(node)

        # Route from each source to its assigned consumers
        all_steiner_points = []

        for source_id in sources:
            assigned = consumer_assignments[source_id]
            if not assigned:
                result.warnings.append(f"Source {source_id} has no assigned consumers")
                continue

            # Build terminal set for this source's tree
            terminals = {source_id} | {c.node_id for c in assigned}

            try:
                steiner_tree, steiner_points = self._compute_steiner_tree(
                    compartment_graph,
                    terminals,
                    [source_id],
                    space_centers or {},
                )
                all_steiner_points.extend(steiner_points)

                # Convert to trunks
                # Create a mini-topology for trunk conversion
                mini_topo = SystemTopology(system_type=system_type)
                source_node = next((n for n in source_nodes if n.node_id == source_id), None)
                if source_node:
                    mini_topo.add_node(source_node)
                for consumer in assigned:
                    mini_topo.add_node(consumer)

                trunks = self._convert_to_trunks(
                    steiner_tree,
                    system_type,
                    mini_topo,
                    compartment_graph,
                    space_centers,
                )

                for trunk in trunks:
                    topology.add_trunk(trunk)

            except Exception as e:
                result.warnings.append(f"Failed to route from {source_id}: {e}")

        result.steiner_points = all_steiner_points

        # Validate
        topology.validate()

        result.success = topology.trunk_count > 0
        result.topology = topology
        result.trunk_count = topology.trunk_count
        result.total_length_m = topology.total_length_m

        return result
