"""
magnet/routing/graph/__init__.py - Graph Package Exports

Graph construction for systems routing including:
- CompartmentGraph: Adjacency graph from interior spaces
- NodeGraph: Node-to-node routing graph
- Graph utilities for pathfinding
"""

from .compartment_graph import (
    CompartmentGraph,
    CompartmentNode,
    CompartmentEdge,
)

from .node_graph import (
    NodeGraph,
)

# graph_utils may not exist yet (Alpha file)
try:
    from .graph_utils import (
        find_shortest_path,
        find_all_paths,
        calculate_path_length,
        get_path_zone_crossings,
    )
    _HAS_GRAPH_UTILS = True
except ImportError:
    _HAS_GRAPH_UTILS = False
    find_shortest_path = None
    find_all_paths = None
    calculate_path_length = None
    get_path_zone_crossings = None

__all__ = [
    # compartment_graph
    'CompartmentGraph',
    'CompartmentNode',
    'CompartmentEdge',
    # node_graph
    'NodeGraph',
]

if _HAS_GRAPH_UTILS:
    __all__.extend([
        'find_shortest_path',
        'find_all_paths',
        'calculate_path_length',
        'get_path_zone_crossings',
    ])
