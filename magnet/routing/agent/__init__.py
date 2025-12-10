"""
routing/agent - Agent package

Contains routing agent and multi-system coordination.
"""

# ALPHA exports
try:
    from magnet.routing.agent.routing_agent import (
        RoutingAgent,
        RoutingConfig,
        RoutingStatus,
        AgentResult,
    )
    _HAS_ALPHA = True
except ImportError:
    _HAS_ALPHA = False
    RoutingAgent = None
    RoutingConfig = None
    RoutingStatus = None
    AgentResult = None

# BRAVO exports
from magnet.routing.agent.multi_system import (
    MultiSystemCoordinator,
    ConflictType,
    SystemConflict,
    CoordinationResult,
)
from magnet.routing.agent.validators import (
    RoutingValidator,
    ValidationSeverity,
    ValidationViolation,
    ValidationResult,
)

__all__ = [
    # ALPHA - RoutingAgent
    'RoutingAgent',
    'RoutingConfig',
    'RoutingStatus',
    'AgentResult',
    # BRAVO - Multi-system
    'MultiSystemCoordinator',
    'ConflictType',
    'SystemConflict',
    'CoordinationResult',
    # BRAVO - Validators
    'RoutingValidator',
    'ValidationSeverity',
    'ValidationViolation',
    'ValidationResult',
]
