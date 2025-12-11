"""
magnet/routing/analysis - Routing Analysis Tools

Provides tools for analyzing and comparing routing results.
"""

from .routing_diff import (
    RoutingDiff,
    DiffType,
    DiffEntry,
    TopologyDiff,
)

__all__ = [
    'RoutingDiff',
    'DiffType',
    'DiffEntry',
    'TopologyDiff',
]
