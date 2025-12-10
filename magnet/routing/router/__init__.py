"""
routing/router - Router package

Contains routing algorithms, zone management, and capacity calculations.
"""

# ALPHA exports (may not exist yet)
try:
    from magnet.routing.router.trunk_router import (
        TrunkRouter,
        RoutingResult,
    )
    from magnet.routing.router.zone_manager import (
        ZoneManager,
        ZoneCrossingResult,
    )
    from magnet.routing.router.capacity_calc import (
        CapacityCalculator,
        calculate_pipe_diameter,
        calculate_cable_size,
        calculate_duct_size,
    )
    _HAS_ALPHA = True
except ImportError:
    _HAS_ALPHA = False
    TrunkRouter = None
    RoutingResult = None
    ZoneManager = None
    ZoneCrossingResult = None
    CapacityCalculator = None
    calculate_pipe_diameter = None
    calculate_cable_size = None
    calculate_duct_size = None

# BRAVO exports
from magnet.routing.router.redundancy import (
    RedundancyChecker,
    RedundancyResult,
    PathDiversity,
    RedundancyRequirement,
)
from magnet.routing.router.path_optimizer import (
    PathOptimizer,
    OptimizationObjective,
    OptimizationResult,
)
from magnet.routing.router.path_utils import (
    merge_paths,
    split_path,
    find_intersections,
    calculate_path_length,
    simplify_path,
    get_path_segments,
    paths_overlap,
    find_common_subpath,
)

__all__ = [
    # ALPHA - TrunkRouter
    'TrunkRouter',
    'RoutingResult',
    # ALPHA - ZoneManager
    'ZoneManager',
    'ZoneCrossingResult',
    # ALPHA - CapacityCalculator
    'CapacityCalculator',
    'calculate_pipe_diameter',
    'calculate_cable_size',
    'calculate_duct_size',
    # BRAVO - Redundancy
    'RedundancyChecker',
    'RedundancyResult',
    'PathDiversity',
    'RedundancyRequirement',
    # Optimizer
    'PathOptimizer',
    'OptimizationObjective',
    'OptimizationResult',
    # Utils
    'merge_paths',
    'split_path',
    'find_intersections',
    'calculate_path_length',
    'simplify_path',
    'get_path_segments',
    'paths_overlap',
    'find_common_subpath',
]
