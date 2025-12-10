"""
path_utils.py - Path manipulation utilities v1.1
BRAVO OWNS THIS FILE.

Module 60: Systems Routing
Utility functions for path manipulation and analysis.
"""

from typing import List, Dict, Set, Optional, Tuple, Any
import logging
import math

__all__ = [
    'merge_paths',
    'split_path',
    'find_intersections',
    'calculate_path_length',
    'simplify_path',
    'get_path_segments',
    'paths_overlap',
    'find_common_subpath',
]

logger = logging.getLogger(__name__)


# =============================================================================
# PATH MERGING
# =============================================================================

def merge_paths(
    paths: List[List[str]],
    allow_cycles: bool = False,
) -> List[str]:
    """
    Merge multiple paths into a single path.

    Attempts to connect paths end-to-end where possible.

    Args:
        paths: List of paths to merge
        allow_cycles: Whether to allow cycles in result

    Returns:
        Merged path or empty list if not possible
    """
    if not paths:
        return []

    if len(paths) == 1:
        return paths[0].copy()

    # Build endpoint map
    endpoint_to_path: Dict[str, List[int]] = {}
    for i, path in enumerate(paths):
        if not path:
            continue
        start, end = path[0], path[-1]
        endpoint_to_path.setdefault(start, []).append(i)
        endpoint_to_path.setdefault(end, []).append(i)

    # Start from first path
    result = paths[0].copy()
    used_paths = {0}

    # Try to extend in both directions
    changed = True
    while changed:
        changed = False

        # Try to extend from end
        current_end = result[-1]
        for path_idx in endpoint_to_path.get(current_end, []):
            if path_idx in used_paths:
                continue

            path = paths[path_idx]
            if path[0] == current_end:
                # Append path (skip first element)
                result.extend(path[1:])
                used_paths.add(path_idx)
                changed = True
                break
            elif path[-1] == current_end:
                # Append reversed path (skip first element)
                result.extend(reversed(path[:-1]))
                used_paths.add(path_idx)
                changed = True
                break

        # Try to extend from start
        current_start = result[0]
        for path_idx in endpoint_to_path.get(current_start, []):
            if path_idx in used_paths:
                continue

            path = paths[path_idx]
            if path[-1] == current_start:
                # Prepend path (skip last element)
                result = path[:-1] + result
                used_paths.add(path_idx)
                changed = True
                break
            elif path[0] == current_start:
                # Prepend reversed path (skip last element)
                result = list(reversed(path[1:])) + result
                used_paths.add(path_idx)
                changed = True
                break

    # Check for cycles
    if not allow_cycles:
        seen = set()
        for node in result:
            if node in seen:
                # Remove cycle
                idx = result.index(node)
                result = result[:idx] + result[result.index(node, idx + 1):]
            seen.add(node)

    return result


def split_path(
    path: List[str],
    split_point: str,
) -> Tuple[List[str], List[str]]:
    """
    Split path at a given point.

    Args:
        path: Path to split
        split_point: Node to split at

    Returns:
        Tuple of (first_half, second_half), split point in both
    """
    if split_point not in path:
        return path.copy(), []

    idx = path.index(split_point)
    return path[:idx + 1], path[idx:]


# =============================================================================
# INTERSECTION DETECTION
# =============================================================================

def find_intersections(
    path_a: List[str],
    path_b: List[str],
) -> List[str]:
    """
    Find nodes where two paths intersect.

    Args:
        path_a: First path
        path_b: Second path

    Returns:
        List of common nodes (in order of appearance in path_a)
    """
    set_b = set(path_b)
    return [node for node in path_a if node in set_b]


def find_edge_intersections(
    path_a: List[str],
    path_b: List[str],
) -> List[Tuple[str, str]]:
    """
    Find edges (node pairs) common to both paths.

    Args:
        path_a: First path
        path_b: Second path

    Returns:
        List of common edges as (from, to) tuples
    """
    def get_edges(path: List[str]) -> Set[Tuple[str, str]]:
        edges = set()
        for i in range(len(path) - 1):
            # Normalize edge direction
            edge = tuple(sorted([path[i], path[i + 1]]))
            edges.add(edge)
        return edges

    edges_a = get_edges(path_a)
    edges_b = get_edges(path_b)

    return list(edges_a & edges_b)


def paths_overlap(
    path_a: List[str],
    path_b: List[str],
    min_overlap: int = 1,
) -> bool:
    """
    Check if two paths overlap.

    Args:
        path_a: First path
        path_b: Second path
        min_overlap: Minimum number of common nodes to count as overlap

    Returns:
        True if paths overlap by at least min_overlap nodes
    """
    common = find_intersections(path_a, path_b)
    return len(common) >= min_overlap


# =============================================================================
# PATH LENGTH CALCULATION
# =============================================================================

def calculate_path_length(
    path: List[str],
    node_positions: Dict[str, Tuple[float, float, float]],
) -> float:
    """
    Calculate total length of a path using node positions.

    Args:
        path: List of node IDs
        node_positions: node_id -> (x, y, z) position

    Returns:
        Total path length in meters
    """
    if len(path) < 2:
        return 0.0

    total = 0.0
    for i in range(len(path) - 1):
        pos_a = node_positions.get(path[i])
        pos_b = node_positions.get(path[i + 1])

        if pos_a and pos_b:
            dx = pos_b[0] - pos_a[0]
            dy = pos_b[1] - pos_a[1]
            dz = pos_b[2] - pos_a[2]
            total += math.sqrt(dx * dx + dy * dy + dz * dz)
        else:
            # Assume default distance if positions unknown
            total += 1.0

    return total


def calculate_path_length_from_graph(
    path: List[str],
    graph: Any,
    weight: str = 'distance',
) -> float:
    """
    Calculate path length using graph edge weights.

    Args:
        path: List of node IDs
        graph: NetworkX graph with edge weights
        weight: Edge attribute to use for distance

    Returns:
        Total path length
    """
    if len(path) < 2:
        return 0.0

    total = 0.0
    for i in range(len(path) - 1):
        if graph.has_edge(path[i], path[i + 1]):
            total += graph.edges[path[i], path[i + 1]].get(weight, 1.0)
        else:
            total += 10.0  # Penalty for missing edge

    return total


# =============================================================================
# PATH SIMPLIFICATION
# =============================================================================

def simplify_path(
    path: List[str],
    graph: Any,
) -> List[str]:
    """
    Simplify path by removing unnecessary waypoints.

    Removes intermediate nodes that don't affect routing
    (i.e., nodes where path could go direct).

    Args:
        path: Path to simplify
        graph: Graph for checking direct connections

    Returns:
        Simplified path
    """
    if len(path) <= 2:
        return path.copy()

    simplified = [path[0]]

    i = 0
    while i < len(path) - 1:
        # Look for farthest reachable node
        farthest = i + 1
        for j in range(i + 2, len(path)):
            if graph.has_edge(path[i], path[j]):
                farthest = j

        simplified.append(path[farthest])
        i = farthest

    return simplified


def expand_path(
    path: List[str],
    graph: Any,
) -> List[str]:
    """
    Expand path by finding actual route between non-adjacent nodes.

    Args:
        path: Simplified path
        graph: Graph for pathfinding

    Returns:
        Expanded path with all intermediate nodes
    """
    try:
        import networkx as nx
    except ImportError:
        return path

    if len(path) <= 1:
        return path.copy()

    expanded = [path[0]]

    for i in range(len(path) - 1):
        if graph.has_edge(path[i], path[i + 1]):
            # Direct connection
            expanded.append(path[i + 1])
        else:
            # Find path between nodes
            try:
                subpath = nx.shortest_path(graph, path[i], path[i + 1])
                expanded.extend(subpath[1:])
            except (nx.NetworkXNoPath, nx.NetworkXError):
                # Can't find path, just add destination
                expanded.append(path[i + 1])

    return expanded


# =============================================================================
# PATH SEGMENTS
# =============================================================================

def get_path_segments(
    path: List[str],
    segment_boundaries: Set[str],
) -> List[List[str]]:
    """
    Split path into segments at boundary nodes.

    Args:
        path: Path to split
        segment_boundaries: Set of nodes that define segment boundaries

    Returns:
        List of path segments
    """
    if not path:
        return []

    segments = []
    current_segment = [path[0]]

    for node in path[1:]:
        current_segment.append(node)
        if node in segment_boundaries:
            segments.append(current_segment)
            current_segment = [node]

    if len(current_segment) > 1 or (segments and current_segment[0] != segments[-1][-1]):
        segments.append(current_segment)

    return segments


def get_segment_at_node(
    path: List[str],
    node: str,
    segment_length: int = 3,
) -> List[str]:
    """
    Get a segment of path centered on a node.

    Args:
        path: Full path
        node: Node to center on
        segment_length: Desired segment length

    Returns:
        Segment of path around node
    """
    if node not in path:
        return []

    idx = path.index(node)
    half = segment_length // 2

    start = max(0, idx - half)
    end = min(len(path), idx + half + 1)

    return path[start:end]


# =============================================================================
# COMMON SUBPATH DETECTION
# =============================================================================

def find_common_subpath(
    path_a: List[str],
    path_b: List[str],
    min_length: int = 2,
) -> List[List[str]]:
    """
    Find common contiguous subpaths between two paths.

    Args:
        path_a: First path
        path_b: Second path
        min_length: Minimum length of common subpath

    Returns:
        List of common subpaths
    """
    if not path_a or not path_b:
        return []

    # Find all common nodes
    common_nodes = set(path_a) & set(path_b)
    if len(common_nodes) < min_length:
        return []

    # Find contiguous sequences
    subpaths = []

    i = 0
    while i < len(path_a):
        if path_a[i] not in common_nodes:
            i += 1
            continue

        # Start of potential common subpath
        start_a = i

        # Find corresponding start in path_b
        if path_a[i] not in path_b:
            i += 1
            continue

        start_b = path_b.index(path_a[i])

        # Extend as far as possible
        j = 0
        while (start_a + j < len(path_a) and
               start_b + j < len(path_b) and
               path_a[start_a + j] == path_b[start_b + j]):
            j += 1

        if j >= min_length:
            subpaths.append(path_a[start_a:start_a + j])

        i += max(1, j)

    return subpaths


def find_longest_common_subpath(
    path_a: List[str],
    path_b: List[str],
) -> List[str]:
    """
    Find the longest common contiguous subpath.

    Args:
        path_a: First path
        path_b: Second path

    Returns:
        Longest common subpath
    """
    subpaths = find_common_subpath(path_a, path_b, min_length=1)
    if not subpaths:
        return []

    return max(subpaths, key=len)


# =============================================================================
# PATH VALIDATION
# =============================================================================

def validate_path_connectivity(
    path: List[str],
    graph: Any,
) -> Tuple[bool, List[str]]:
    """
    Validate that all path nodes are connected in graph.

    Args:
        path: Path to validate
        graph: Graph to check against

    Returns:
        (is_valid, list of disconnected pairs)
    """
    if len(path) < 2:
        return True, []

    disconnected = []

    for i in range(len(path) - 1):
        if not graph.has_node(path[i]):
            disconnected.append(f"Node {path[i]} not in graph")
        elif not graph.has_node(path[i + 1]):
            disconnected.append(f"Node {path[i + 1]} not in graph")
        elif not graph.has_edge(path[i], path[i + 1]):
            disconnected.append(f"No edge {path[i]} -> {path[i + 1]}")

    return len(disconnected) == 0, disconnected


def is_valid_path(
    path: List[str],
    start: str,
    end: str,
    graph: Optional[Any] = None,
) -> bool:
    """
    Check if path is valid between start and end.

    Args:
        path: Path to validate
        start: Expected start node
        end: Expected end node
        graph: Optional graph for connectivity check

    Returns:
        True if path is valid
    """
    if not path:
        return False

    if path[0] != start or path[-1] != end:
        return False

    if graph is not None:
        is_connected, _ = validate_path_connectivity(path, graph)
        return is_connected

    return True
