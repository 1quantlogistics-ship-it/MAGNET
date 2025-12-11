"""
magnet/routing/contracts - Contract Definitions

Defines protocols and input contracts that decouple routing components
from external dependencies like DesignState.
"""

from .routing_input import (
    SpaceInfo,
    RoutingInputContract,
)
from .protocols import (
    GraphBuilderProtocol,
    RouterProtocol,
    ZoneValidatorProtocol,
    RoutingResultProtocol,
    CapacityCalculatorProtocol,
)
from .routing_lineage import (
    RoutingLineage,
    LineageStatus,
    quantize_coordinate,
    quantize_point,
    compute_geometry_hash,
    compute_arrangement_hash,
)

__all__ = [
    # Input contract
    'SpaceInfo',
    'RoutingInputContract',
    # Lineage tracking
    'RoutingLineage',
    'LineageStatus',
    'quantize_coordinate',
    'quantize_point',
    'compute_geometry_hash',
    'compute_arrangement_hash',
    # Protocols
    'GraphBuilderProtocol',
    'RouterProtocol',
    'ZoneValidatorProtocol',
    'RoutingResultProtocol',
    'CapacityCalculatorProtocol',
]
