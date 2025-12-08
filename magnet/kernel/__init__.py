"""
kernel/__init__.py - Module 15 Integration Kernel.

BRAVO OWNS THIS FILE.

Module 15 v1.1 - Integration Kernel exports.

Provides phase orchestration, session management, and pipeline control
for the MAGNET design process.
"""

from .enums import (
    PhaseStatus,
    GateCondition,
    SessionStatus,
    PhaseType,
)

from .schema import (
    PhaseResult,
    GateResult,
    SessionState,
)

from .registry import (
    PhaseDefinition,
    PhaseRegistry,
    PHASE_DEFINITIONS,
)

from .conductor import Conductor

from .orchestrator import ValidationOrchestrator

from .session import DesignSession

from .validator import (
    KernelValidator,
    KERNEL_DEFINITION,
    get_kernel_definition,
    register_kernel_validators,
)


__all__ = [
    # Enums
    "PhaseStatus",
    "GateCondition",
    "SessionStatus",
    "PhaseType",
    # Schema
    "PhaseResult",
    "GateResult",
    "SessionState",
    # Registry
    "PhaseDefinition",
    "PhaseRegistry",
    "PHASE_DEFINITIONS",
    # Core
    "Conductor",
    "ValidationOrchestrator",
    "DesignSession",
    # Validator
    "KernelValidator",
    "KERNEL_DEFINITION",
    "get_kernel_definition",
    "register_kernel_validators",
]
