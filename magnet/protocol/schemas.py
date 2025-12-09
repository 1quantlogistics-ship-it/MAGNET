"""
protocol/schemas.py - Message schemas for agent-validator communication
BRAVO OWNS THIS FILE.

Section 41: Agent ↔ Validator Protocol
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import uuid


class ProposalStatus(Enum):
    """Status of a proposal through the cycle."""
    PENDING = "pending"
    VALIDATING = "validating"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISED = "revised"
    ESCALATED = "escalated"


class DecisionType(Enum):
    """Agent decision after validation."""
    APPROVE = "approve"
    REVISE = "revise"
    ESCALATE = "escalate"
    ABORT = "abort"


@dataclass
class ParameterChange:
    """Single parameter change in a proposal."""

    path: str = ""
    """Dot-notation path (e.g., 'hull.beam')"""

    old_value: Any = None
    new_value: Any = None

    unit: str = ""
    reasoning: str = ""

    # Metadata
    confidence: float = 0.8
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "unit": self.unit,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
        }


@dataclass
class Proposal:
    """Agent proposal containing parameter changes."""

    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_id: str = ""

    created_at: datetime = field(default_factory=datetime.utcnow)

    phase: str = ""
    iteration: int = 1

    changes: List[ParameterChange] = field(default_factory=list)

    status: ProposalStatus = ProposalStatus.PENDING

    reasoning: str = ""
    confidence: float = 0.7

    # Parent proposal (if revision)
    parent_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "agent_id": self.agent_id,
            "created_at": self.created_at.isoformat(),
            "phase": self.phase,
            "iteration": self.iteration,
            "changes": [c.to_dict() for c in self.changes],
            "status": self.status.value,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
        }


@dataclass
class ValidationFinding:
    """Single finding from validation."""

    validator_name: str = "unknown"  # v1.1: Made optional with default
    severity: str = "warning"  # error, warning, info
    code: str = ""
    message: str = ""

    path: Optional[str] = None
    actual_value: Any = None
    expected_value: Any = None

    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validator": self.validator_name,
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationRequest:
    """Request to validate a proposal."""

    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    proposal: Optional[Proposal] = None

    validators_to_run: List[str] = field(default_factory=list)
    """Empty = run all applicable validators"""

    phase: str = ""
    strict_mode: bool = False

    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ValidationResult:
    """Result of validation."""

    request_id: str = ""
    proposal_id: str = ""

    passed: bool = False

    findings: List[ValidationFinding] = field(default_factory=list)

    validators_run: List[str] = field(default_factory=list)

    duration_ms: float = 0.0
    completed_at: datetime = field(default_factory=datetime.utcnow)

    # Summary counts
    error_count: int = 0
    warning_count: int = 0

    def __post_init__(self):
        self.error_count = sum(1 for f in self.findings if f.severity == "error")
        self.warning_count = sum(1 for f in self.findings if f.severity == "warning")

    @property
    def errors(self) -> List[str]:
        """Get error messages (compatibility property)."""
        return [f.message for f in self.findings if f.severity == "error"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "proposal_id": self.proposal_id,
            "passed": self.passed,
            "findings": [f.to_dict() for f in self.findings],
            "validators_run": self.validators_run,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
        }


@dataclass
class AgentDecision:
    """Agent's decision after receiving validation results."""

    decision_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_id: str = ""

    decision: DecisionType = DecisionType.REVISE

    reasoning: str = ""
    confidence: float = 0.7

    # For REVISE
    revision_plan: str = ""

    # For ESCALATE
    escalation_reason: str = ""
    escalation_context: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "agent_id": self.agent_id,
            "decision": self.decision.value,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
        }
