"""
glue/lifecycle/ - Design Lifecycle & Export (Module 45)

ALPHA OWNS THIS FILE.

Provides design phase management and export functionality.
"""

from .manager import (
    DesignPhase,
    LifecycleState,
    PhaseTransition,
    LifecycleManager,
)

from .exporter import (
    ExportFormat,
    DesignExporter,
)


__all__ = [
    # Manager
    "DesignPhase",
    "LifecycleState",
    "PhaseTransition",
    "LifecycleManager",
    # Exporter
    "ExportFormat",
    "DesignExporter",
]
