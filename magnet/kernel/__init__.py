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

# v1.1: Hull Synthesis Engine
from .synthesis import (
    HullSynthesizer,
    SynthesisRequest,
    SynthesisProposal,
    SynthesisResult,
    ConvergenceCriteria,
    TerminationReason,
)
from .synthesis_lock import SynthesisLock, SynthesisLockError
from .synthesis_fallback import (
    FallbackProposal,
    FallbackMode,
    create_fallback_proposal,
)

# TASK-002: Import geometry-based synthesis (PREFERRED)
from .synthesis import GeometrySynthesisRequest

# TASK-002: Import geometry-based analysis (PREFERRED)
from .analysis import (
    calculate_froude_geometry,
    classify_regime_geometry,
    recommend_regime_defaults,
)

# DEPRECATED: HullFamily imports (will be removed in Phase 2)
# Lazy import to allow removal - access via magnet.kernel.priors.hull_families if needed


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
    # Synthesis (v1.1)
    "HullSynthesizer",
    "SynthesisRequest",  # DEPRECATED - use GeometrySynthesisRequest
    "GeometrySynthesisRequest",  # PREFERRED (TASK-002)
    "SynthesisProposal",
    "SynthesisResult",
    "ConvergenceCriteria",
    "TerminationReason",
    "SynthesisLock",
    "SynthesisLockError",
    "FallbackProposal",
    "FallbackMode",
    "create_fallback_proposal",
    # Analysis (TASK-002)
    "calculate_froude_geometry",
    "classify_regime_geometry",
    "recommend_regime_defaults",
]
