"""
glue/protocol/ - Agent-Validator Protocol (Module 41)

ALPHA OWNS THIS FILE.

Defines the propose→validate→revise communication pattern
between agents and the validation pipeline.
"""

from .schemas import (
    ProposalStatus,
    DecisionType,
    ParameterChange,
    Proposal,
    ValidationFinding,
    ValidationRequest,
    ValidationResult,
    AgentDecision,
)

from .executor import CycleExecutor

from .escalation import (
    EscalationLevel,
    EscalationRequest,
    EscalationHandler,
)


__all__ = [
    # Enums
    "ProposalStatus",
    "DecisionType",
    # Schemas
    "ParameterChange",
    "Proposal",
    "ValidationFinding",
    "ValidationRequest",
    "ValidationResult",
    "AgentDecision",
    # Executor
    "CycleExecutor",
    # Escalation
    "EscalationLevel",
    "EscalationRequest",
    "EscalationHandler",
]
