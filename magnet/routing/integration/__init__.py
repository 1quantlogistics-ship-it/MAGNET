"""
routing/integration - Integration package

Contains state integration, API endpoints, and configuration.
BRAVO OWNS THIS PACKAGE.
"""

from magnet.routing.integration.state_integration import (
    StateIntegrator,
    RoutingStateKeys,
)
from magnet.routing.integration.config import (
    RoutingConfig,
    DEFAULT_CONFIG,
)
from magnet.routing.integration.api_endpoints import (
    create_routing_router,
    RouteRequest,
    RouteResponse,
    ValidationResponse,
)

__all__ = [
    'StateIntegrator',
    'RoutingStateKeys',
    'RoutingConfig',
    'DEFAULT_CONFIG',
    'create_routing_router',
    'RouteRequest',
    'RouteResponse',
    'ValidationResponse',
]
