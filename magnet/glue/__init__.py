"""
glue/__init__.py - System Glue Layer

Modules 41-45: System Glue Layer
- Module 41: Agent-Validator Protocol
- Module 42: Explanation Engine
- Module 43: Error Taxonomy & Recovery
- Module 44: Transaction Model
- Module 45: Design Lifecycle & Export
"""

# Utilities (shared)
from .utils import (
    safe_get,
    safe_write,
    serialize_state,
    get_speed_field,
    SPEED_FIELD_ALIASES,
    compute_state_hash,
)

# Module 41: Protocol
from .protocol import (
    ProposalStatus,
    DecisionType,
    ParameterChange,
    Proposal,
    ValidationFinding,
    ValidationRequest,
    ValidationResult,
    AgentDecision,
    CycleExecutor,
    EscalationLevel,
    EscalationRequest,
    EscalationHandler,
)

# Module 42: Explanation
from .explanation import (
    ParameterDiff,
    ValidatorSummary,
    DesignExplanation,
    TraceCollector,
    NarrativeGenerator,
    MarkdownFormatter,
    HTMLFormatter,
)

# Module 43: Errors
from .errors import (
    ErrorCategory,
    ErrorSeverity,
    MAGNETError,
    ErrorContext,
    RecoveryStrategy,
    RecoveryResult,
    ErrorHandler,
    ERROR_CATALOG,
)

# Module 44: Transactions
from .transactions import (
    TransactionState,
    TransactionRecord,
    TransactionManager,
    IsolationLevel,
)

# Module 45: Lifecycle
from .lifecycle import (
    DesignPhase,
    LifecycleState,
    PhaseTransition,
    LifecycleManager,
    ExportFormat,
    DesignExporter,
)


__all__ = [
    # Utilities
    "safe_get",
    "safe_write",
    "serialize_state",
    "get_speed_field",
    "SPEED_FIELD_ALIASES",
    "compute_state_hash",
    # Protocol (41)
    "ProposalStatus",
    "DecisionType",
    "ParameterChange",
    "Proposal",
    "ValidationFinding",
    "ValidationRequest",
    "ValidationResult",
    "AgentDecision",
    "CycleExecutor",
    "EscalationLevel",
    "EscalationRequest",
    "EscalationHandler",
    # Explanation (42)
    "ParameterDiff",
    "ValidatorSummary",
    "DesignExplanation",
    "TraceCollector",
    "NarrativeGenerator",
    "MarkdownFormatter",
    "HTMLFormatter",
    # Errors (43)
    "ErrorCategory",
    "ErrorSeverity",
    "MAGNETError",
    "ErrorContext",
    "RecoveryStrategy",
    "RecoveryResult",
    "ErrorHandler",
    "ERROR_CATALOG",
    # Transactions (44)
    "TransactionState",
    "TransactionRecord",
    "TransactionManager",
    "IsolationLevel",
    # Lifecycle (45)
    "DesignPhase",
    "LifecycleState",
    "PhaseTransition",
    "LifecycleManager",
    "ExportFormat",
    "DesignExporter",
]
