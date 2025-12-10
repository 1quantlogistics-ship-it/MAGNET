"""
magnet/routing/__init__.py - Systems Routing Package

Module 60: Systems Routing Engine
Routes vessel systems (fuel, electrical, HVAC, etc.) through interior spaces.

This module provides:
- SystemType definitions for 18 naval system types
- Compartment graph construction from interior layout
- MST-based trunk routing algorithm
- Zone compliance validation
- Capacity sizing calculations
- RoutingAgent for multi-system coordination
"""

from .schema import (
    # Enums
    SystemType,
    Criticality,
    NodeType,
    # Dataclasses
    SystemProperties,
    SystemNode,
    TrunkSegment,
    TrunkSize,
    SystemTopology,
    RoutingLayout,
    # Functions
    get_system_properties,
    generate_node_id,
    generate_trunk_id,
)

from .graph import (
    CompartmentGraph,
    CompartmentNode,
    CompartmentEdge,
    NodeGraph,
)

# Alpha router components (may not exist yet)
try:
    from .router.trunk_router import TrunkRouter
    from .router.zone_manager import ZoneManager
    from .router.capacity_calc import CapacityCalculator
    _HAS_ALPHA_ROUTER = True
except ImportError:
    _HAS_ALPHA_ROUTER = False
    TrunkRouter = None
    ZoneManager = None
    CapacityCalculator = None

# Alpha agent (may not exist yet)
try:
    from .agent.routing_agent import RoutingAgent
    _HAS_ROUTING_AGENT = True
except ImportError:
    _HAS_ROUTING_AGENT = False
    RoutingAgent = None

# BRAVO imports
from .schema.zone_definition import (
    ZoneType,
    ZoneDefinition,
    ZoneBoundary,
    CrossingRequirement,
    ZONE_CROSSING_RULES,
)
from .schema.separation_rule import (
    SeparationType,
    SeparationRule,
    SeparationRuleSet,
    DEFAULT_SEPARATION_RULES,
    get_separation_requirement,
)
from .router.redundancy import (
    RedundancyChecker,
    RedundancyResult,
    PathDiversity,
    RedundancyRequirement,
)
from .router.path_optimizer import (
    PathOptimizer,
    OptimizationObjective,
    OptimizationResult,
)
from .router.path_utils import (
    merge_paths,
    split_path,
    find_intersections,
    calculate_path_length,
    simplify_path,
    get_path_segments,
    paths_overlap,
    find_common_subpath,
)
from .agent.multi_system import (
    MultiSystemCoordinator,
    ConflictType,
    SystemConflict,
    CoordinationResult,
)
from .agent.validators import (
    RoutingValidator,
    ValidationSeverity,
    ValidationViolation,
    ValidationResult,
)
from .integration.state_integration import (
    StateIntegrator,
    RoutingStateKeys,
)
from .integration.config import (
    RoutingConfig,
    DEFAULT_CONFIG,
)
from .integration.api_endpoints import (
    create_routing_router,
    RouteRequest,
    RouteResponse,
    ValidationResponse,
)

__all__ = [
    # Schema - Enums
    'SystemType',
    'Criticality',
    'NodeType',
    # Schema - Dataclasses
    'SystemProperties',
    'SystemNode',
    'TrunkSegment',
    'TrunkSize',
    'SystemTopology',
    'RoutingLayout',
    # Schema - Functions
    'get_system_properties',
    'generate_node_id',
    'generate_trunk_id',
    # Graph
    'CompartmentGraph',
    'CompartmentNode',
    'CompartmentEdge',
    'NodeGraph',
    # Router
    'TrunkRouter',
    'ZoneManager',
    'CapacityCalculator',
    # Agent
    'RoutingAgent',
    # BRAVO - Schema Zone
    'ZoneType',
    'ZoneDefinition',
    'ZoneBoundary',
    'CrossingRequirement',
    'ZONE_CROSSING_RULES',
    # BRAVO - Schema Separation
    'SeparationType',
    'SeparationRule',
    'SeparationRuleSet',
    'DEFAULT_SEPARATION_RULES',
    'get_separation_requirement',
    # BRAVO - Router Redundancy
    'RedundancyChecker',
    'RedundancyResult',
    'PathDiversity',
    'RedundancyRequirement',
    # BRAVO - Router Optimizer
    'PathOptimizer',
    'OptimizationObjective',
    'OptimizationResult',
    # BRAVO - Router Utils
    'merge_paths',
    'split_path',
    'find_intersections',
    'calculate_path_length',
    'simplify_path',
    'get_path_segments',
    'paths_overlap',
    'find_common_subpath',
    # BRAVO - Agent Multi-system
    'MultiSystemCoordinator',
    'ConflictType',
    'SystemConflict',
    'CoordinationResult',
    # BRAVO - Agent Validators
    'RoutingValidator',
    'ValidationSeverity',
    'ValidationViolation',
    'ValidationResult',
    # BRAVO - Integration
    'StateIntegrator',
    'RoutingStateKeys',
    'RoutingConfig',
    'DEFAULT_CONFIG',
    'create_routing_router',
    'RouteRequest',
    'RouteResponse',
    'ValidationResponse',
]

__version__ = '1.0.0'
