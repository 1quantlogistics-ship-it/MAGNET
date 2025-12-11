"""
magnet/routing/service - Routing Service Layer

Provides the RoutingService façade that enforces RoutingInputContract
as the mandatory entry point for all routing operations.
"""

from .routing_service import (
    RoutingService,
    RoutingServiceResult,
)

__all__ = [
    'RoutingService',
    'RoutingServiceResult',
]
