"""
MAGNET Dependency & Invalidation Engine

Module 03 v1.1 - Production-Ready

Provides:
- DependencyGraph: DAG of parameter dependencies
- InvalidationEngine: Cascade invalidation on changes
- CascadeExecutor: Ordered recalculation
- TriggerLog: Audit trail for changes
"""

from .graph import (
    DependencyGraph,
    DependencyNode,
    DependencyEdge,
    EdgeType,
    PHASE_OWNERSHIP,
    PARAMETER_TO_PHASE,
    get_phase_for_parameter,
    get_parameters_for_phase,
)
from .invalidation import (
    InvalidationEngine,
    InvalidationEvent,
    InvalidationReason,
    InvalidationScope,
)
from .cascade import (
    CascadeExecutor,
    CascadeResult,
    RecalculationOrder,
)
from .trigger_log import (
    TriggerLog,
    TriggerEntry,
    TriggerType,
)
from .revalidation import (
    RevalidationScheduler,
    RevalidationTask,
)

__all__ = [
    # Graph
    "DependencyGraph",
    "DependencyNode",
    "DependencyEdge",
    "EdgeType",
    "PHASE_OWNERSHIP",
    "PARAMETER_TO_PHASE",
    "get_phase_for_parameter",
    "get_parameters_for_phase",
    # Invalidation
    "InvalidationEngine",
    "InvalidationEvent",
    "InvalidationReason",
    "InvalidationScope",
    # Cascade
    "CascadeExecutor",
    "CascadeResult",
    "RecalculationOrder",
    # Trigger Log
    "TriggerLog",
    "TriggerEntry",
    "TriggerType",
    # Revalidation
    "RevalidationScheduler",
    "RevalidationTask",
]
