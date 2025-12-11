"""
magnet/routing/visualization - Routing Visualization Tools

Provides tools for generating visualization data from routing results.
"""

from .polyline_generator import (
    PolylineGenerator,
    TrunkPolyline,
    CrossingMarker,
    CrossingType,
    VisualizationData,
    SYSTEM_COLORS,
)

__all__ = [
    'PolylineGenerator',
    'TrunkPolyline',
    'CrossingMarker',
    'CrossingType',
    'VisualizationData',
    'SYSTEM_COLORS',
]
