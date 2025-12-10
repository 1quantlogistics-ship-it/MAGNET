"""
magnet/routing/schema/__init__.py - Routing Schema Exports

Schema definitions for systems routing including:
- SystemType enum with 18 naval system types
- SystemNode for routing endpoints
- TrunkSegment for routing paths
- SystemTopology and RoutingLayout aggregates
"""

from .system_type import (
    SystemType,
    Criticality,
    SystemProperties,
    SYSTEM_PROPERTIES,
    get_system_properties,
)

from .system_node import (
    NodeType,
    SystemNode,
    generate_node_id,
)

from .trunk_segment import (
    TrunkSegment,
    TrunkSize,
    generate_trunk_id,
)

from .system_topology import (
    SystemTopology,
)

from .routing_layout import (
    RoutingLayout,
)

# BRAVO files
from .zone_definition import (
    ZoneType,
    ZoneDefinition,
    ZoneBoundary,
    CrossingRequirement,
    ZONE_CROSSING_RULES,
)
from .separation_rule import (
    SeparationType,
    SeparationRule,
    SeparationRuleSet,
    DEFAULT_SEPARATION_RULES,
    get_separation_requirement,
)

__all__ = [
    # system_type
    'SystemType',
    'Criticality',
    'SystemProperties',
    'SYSTEM_PROPERTIES',
    'get_system_properties',
    # system_node
    'NodeType',
    'SystemNode',
    'generate_node_id',
    # trunk_segment
    'TrunkSegment',
    'TrunkSize',
    'generate_trunk_id',
    # system_topology
    'SystemTopology',
    # routing_layout
    'RoutingLayout',
    # BRAVO - zone_definition
    'ZoneType',
    'ZoneDefinition',
    'ZoneBoundary',
    'CrossingRequirement',
    'ZONE_CROSSING_RULES',
    # BRAVO - separation_rule
    'SeparationType',
    'SeparationRule',
    'SeparationRuleSet',
    'DEFAULT_SEPARATION_RULES',
    'get_separation_requirement',
]
