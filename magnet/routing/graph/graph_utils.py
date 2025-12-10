"""
magnet/routing/graph/graph_utils.py - Graph Utilities

Utility functions for graph operations in routing.
"""

from typing import Dict, List, Optional, Tuple, Set, Any
import math

try:
    import networkx as nx
except ImportError:
    nx = None

__all__ = [
    'find_shortest_path',
    'find_all_paths',
    'calculate_path_length',
    'get_path_zone_crossings',
    'find_alternative_path',
    'get_connected_components',
    'is_graph_connected',
]


def find_shortest_path(
    graph: 'nx.Graph',
    source: str,
    target: str,
    weight: str = 'cost',
) -> Optional[List[str]]:
    """
    Find shortest path between two nodes.

    Args:
        graph: NetworkX graph
        source: Source node ID
        target: Target node ID
        weight: Edge attribute to use as weight

    Returns:
        List of node IDs in path, or None if no path exists
    """
    if graph is None:
        return None

    try:
        return nx.shortest_path(graph, source, target, weight=weight)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None


def find_all_paths(
    graph: 'nx.Graph',
    source: str,
    target: str,
    weight: str = 'cost',
    max_paths: int = 10,
) -> List[List[str]]:
    """
    Find multiple shortest paths between two nodes.

    Args:
        graph: NetworkX graph
        source: Source node ID
        target: Target node ID
        weight: Edge attribute to use as weight
        max_paths: Maximum number of paths to return

    Returns:
        List of paths (each path is a list of node IDs)
    """
    if graph is None:
        return []

    try:
        gen = nx.shortest_simple_paths(graph, source, target, weight=weight)
        paths = []
        for i, path in enumerate(gen):
            if i >= max_paths:
                break
            paths.append(path)
        return paths
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []


def calculate_path_length(
    graph: 'nx.Graph',
    path: List[str],
    weight: str = 'distance',
) -> float:
    """
    Calculate total length of a path.

    Args:
        graph: NetworkX graph
        path: List of node IDs
        weight: Edge attribute to sum

    Returns:
        Total path length
    """
    if not path or len(path) < 2:
        return 0.0

    total = 0.0
    for i in range(len(path) - 1):
        edge_data = graph.get_edge_data(path[i], path[i + 1])
        if edge_data:
            total += edge_data.get(weight, 0.0)

    return total


def get_path_zone_crossings(
    graph: 'nx.Graph',
    path: List[str],
) -> List[Tuple[str, str]]:
    """
    Get zone crossings along a path.

    Args:
        graph: NetworkX graph with zone_boundary edge attribute
        path: List of node IDs

    Returns:
        List of (from_space, to_space) tuples at zone boundaries
    """
    if not path or len(path) < 2:
        return []

    crossings = []
    for i in range(len(path) - 1):
        edge_data = graph.get_edge_data(path[i], path[i + 1])
        if edge_data and edge_data.get('zone_boundary'):
            crossings.append((path[i], path[i + 1]))

    return crossings


def find_alternative_path(
    graph: 'nx.Graph',
    source: str,
    target: str,
    exclude_edges: List[Tuple[str, str]],
    weight: str = 'cost',
) -> Optional[List[str]]:
    """
    Find path avoiding specified edges.

    Useful for finding redundant paths that don't share edges
    with the primary path.

    Args:
        graph: NetworkX graph
        source: Source node ID
        target: Target node ID
        exclude_edges: Edges to avoid (list of (from, to) tuples)
        weight: Edge attribute to use as weight

    Returns:
        Alternative path, or None if not found
    """
    if graph is None:
        return None

    # Create graph copy without excluded edges
    temp_graph = graph.copy()
    for edge in exclude_edges:
        if temp_graph.has_edge(edge[0], edge[1]):
            temp_graph.remove_edge(edge[0], edge[1])

    return find_shortest_path(temp_graph, source, target, weight)


def get_connected_components(
    graph: 'nx.Graph',
) -> List[Set[str]]:
    """
    Get connected components of the graph.

    Args:
        graph: NetworkX graph

    Returns:
        List of sets, each containing node IDs in a component
    """
    if graph is None:
        return []

    return [set(c) for c in nx.connected_components(graph)]


def is_graph_connected(graph: 'nx.Graph') -> bool:
    """
    Check if graph is fully connected.

    Args:
        graph: NetworkX graph

    Returns:
        True if all nodes are in one connected component
    """
    if graph is None or graph.number_of_nodes() == 0:
        return True

    return nx.is_connected(graph)


def get_graph_statistics(graph: 'nx.Graph') -> Dict[str, Any]:
    """
    Get statistics about a graph.

    Args:
        graph: NetworkX graph

    Returns:
        Dictionary of statistics
    """
    if graph is None:
        return {}

    stats = {
        'node_count': graph.number_of_nodes(),
        'edge_count': graph.number_of_edges(),
        'is_connected': nx.is_connected(graph) if graph.number_of_nodes() > 0 else True,
        'component_count': nx.number_connected_components(graph) if graph.number_of_nodes() > 0 else 0,
    }

    if graph.number_of_nodes() > 0:
        degrees = dict(graph.degree())
        stats['avg_degree'] = sum(degrees.values()) / len(degrees)
        stats['max_degree'] = max(degrees.values())
        stats['min_degree'] = min(degrees.values())

    return stats


def find_bridges(graph: 'nx.Graph') -> List[Tuple[str, str]]:
    """
    Find bridge edges (edges whose removal disconnects the graph).

    Args:
        graph: NetworkX graph

    Returns:
        List of bridge edges as (from, to) tuples
    """
    if graph is None or graph.number_of_nodes() == 0:
        return []

    return list(nx.bridges(graph))


def find_articulation_points(graph: 'nx.Graph') -> List[str]:
    """
    Find articulation points (nodes whose removal disconnects the graph).

    Args:
        graph: NetworkX graph

    Returns:
        List of articulation point node IDs
    """
    if graph is None or graph.number_of_nodes() == 0:
        return []

    return list(nx.articulation_points(graph))


def get_subgraph(
    graph: 'nx.Graph',
    nodes: List[str],
) -> 'nx.Graph':
    """
    Get subgraph containing only specified nodes.

    Args:
        graph: NetworkX graph
        nodes: Node IDs to include

    Returns:
        Subgraph
    """
    if graph is None:
        return nx.Graph()

    return graph.subgraph(nodes).copy()


def merge_graphs(
    graph_a: 'nx.Graph',
    graph_b: 'nx.Graph',
) -> 'nx.Graph':
    """
    Merge two graphs.

    Args:
        graph_a: First graph
        graph_b: Second graph

    Returns:
        Merged graph
    """
    result = nx.Graph()

    if graph_a:
        result.add_nodes_from(graph_a.nodes(data=True))
        result.add_edges_from(graph_a.edges(data=True))

    if graph_b:
        result.add_nodes_from(graph_b.nodes(data=True))
        result.add_edges_from(graph_b.edges(data=True))

    return result


def calculate_path_diversity(
    path_a: List[str],
    path_b: List[str],
) -> float:
    """
    Calculate diversity between two paths.

    Higher value means more diverse (less overlap).

    Args:
        path_a: First path
        path_b: Second path

    Returns:
        Diversity score (0.0 = identical, 1.0 = no overlap)
    """
    if not path_a or not path_b:
        return 1.0

    set_a = set(path_a)
    set_b = set(path_b)

    intersection = len(set_a & set_b)
    union = len(set_a | set_b)

    if union == 0:
        return 1.0

    # Jaccard distance
    return 1.0 - (intersection / union)


def find_path_through_waypoints(
    graph: 'nx.Graph',
    waypoints: List[str],
    weight: str = 'cost',
) -> Optional[List[str]]:
    """
    Find path that passes through all waypoints in order.

    Args:
        graph: NetworkX graph
        waypoints: Ordered list of waypoints to pass through
        weight: Edge attribute to use as weight

    Returns:
        Complete path through all waypoints, or None if impossible
    """
    if not waypoints or len(waypoints) < 2:
        return waypoints if waypoints else None

    complete_path = []

    for i in range(len(waypoints) - 1):
        segment = find_shortest_path(
            graph, waypoints[i], waypoints[i + 1], weight
        )

        if segment is None:
            return None

        # Add segment (skip first node after first segment to avoid duplicates)
        if i == 0:
            complete_path.extend(segment)
        else:
            complete_path.extend(segment[1:])

    return complete_path
