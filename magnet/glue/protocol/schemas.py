"""
glue/protocol/schemas.py - Message schemas for agent-validator communication

ALPHA OWNS THIS FILE.

Module 41: Agent-Validator Protocol
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
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
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParameterChange":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Proposal:
    """Agent proposal containing parameter changes."""

    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_id: str = ""

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "phase": self.phase,
            "iteration": self.iteration,
            "changes": [c.to_dict() for c in self.changes],
            "status": self.status.value,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "parent_id": self.parent_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Proposal":
        changes = [ParameterChange.from_dict(c) for c in data.get("changes", [])]
        status = ProposalStatus(data.get("status", "pending"))
        return cls(
            proposal_id=data.get("proposal_id", ""),
            agent_id=data.get("agent_id", ""),
            phase=data.get("phase", ""),
            iteration=data.get("iteration", 1),
            changes=changes,
            status=status,
            reasoning=data.get("reasoning", ""),
            confidence=data.get("confidence", 0.7),
            parent_id=data.get("parent_id"),
        )


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
            "actual_value": self.actual_value,
            "expected_value": self.expected_value,
            "suggestion": self.suggestion,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationFinding":
        return cls(
            validator_name=data.get("validator", "unknown"),
            severity=data.get("severity", "warning"),
            code=data.get("code", ""),
            message=data.get("message", ""),
            path=data.get("path"),
            actual_value=data.get("actual_value"),
            expected_value=data.get("expected_value"),
            suggestion=data.get("suggestion", ""),
        )


@dataclass
class ValidationRequest:
    """Request to validate a proposal."""

    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    proposal: Optional[Proposal] = None

    validators_to_run: List[str] = field(default_factory=list)
    """Empty = run all applicable validators"""

    phase: str = ""
    strict_mode: bool = False

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "proposal": self.proposal.to_dict() if self.proposal else None,
            "validators_to_run": self.validators_to_run,
            "phase": self.phase,
            "strict_mode": self.strict_mode,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class ValidationResult:
    """Result of validation."""

    request_id: str = ""
    proposal_id: str = ""

    passed: bool = False

    findings: List[ValidationFinding] = field(default_factory=list)

    error_count: int = 0
    warning_count: int = 0

    validators_run: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "proposal_id": self.proposal_id,
            "passed": self.passed,
            "findings": [f.to_dict() for f in self.findings],
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "validators_run": self.validators_run,
            "duration_ms": self.duration_ms,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationResult":
        findings = [ValidationFinding.from_dict(f) for f in data.get("findings", [])]
        return cls(
            request_id=data.get("request_id", ""),
            proposal_id=data.get("proposal_id", ""),
            passed=data.get("passed", False),
            findings=findings,
            error_count=data.get("error_count", 0),
            warning_count=data.get("warning_count", 0),
            validators_run=data.get("validators_run", []),
            duration_ms=data.get("duration_ms", 0.0),
        )

    @property
    def has_errors(self) -> bool:
        return self.error_count > 0

    @property
    def has_warnings(self) -> bool:
        return self.warning_count > 0


@dataclass
class AgentDecision:
    """Agent's decision after seeing validation results."""

    decision_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    proposal_id: str = ""
    agent_id: str = ""

    decision: DecisionType = DecisionType.APPROVE

    reasoning: str = ""
    confidence: float = 0.8

    # For revisions
    revision_changes: List[ParameterChange] = field(default_factory=list)

    # For escalations
    escalation_reason: str = ""

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "proposal_id": self.proposal_id,
            "agent_id": self.agent_id,
            "decision": self.decision.value,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "revision_changes": [c.to_dict() for c in self.revision_changes],
            "escalation_reason": self.escalation_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
