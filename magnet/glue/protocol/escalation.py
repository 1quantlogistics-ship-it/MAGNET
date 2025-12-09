"""
glue/protocol/escalation.py - Escalation system for unresolved validation issues

ALPHA OWNS THIS FILE.

Module 41: Agent-Validator Protocol
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid
import logging

from .schemas import Proposal, ValidationResult, ValidationFinding

logger = logging.getLogger(__name__)


class EscalationLevel(Enum):
    """Escalation severity levels."""
    INFO = "info"           # Informational, no action required
    LOW = "low"             # Minor issue, can be deferred
    MEDIUM = "medium"       # Requires attention within cycle
    HIGH = "high"           # Requires immediate resolution
    CRITICAL = "critical"   # Blocks design progress


class EscalationStatus(Enum):
    """Status of an escalation."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DEFERRED = "deferred"
    DISMISSED = "dismissed"


@dataclass
class EscalationRequest:
    """Request for escalation of an unresolved issue."""

    escalation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    proposal_id: str = ""
    agent_id: str = ""
    phase: str = ""

    level: EscalationLevel = EscalationLevel.MEDIUM
    status: EscalationStatus = EscalationStatus.OPEN

    reason: str = ""
    description: str = ""

    # Related validation findings
    findings: List[ValidationFinding] = field(default_factory=list)

    # Attempted iterations before escalation
    iterations_attempted: int = 0

    # Context for resolution
    context: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "escalation_id": self.escalation_id,
            "proposal_id": self.proposal_id,
            "agent_id": self.agent_id,
            "phase": self.phase,
            "level": self.level.value,
            "status": self.status.value,
            "reason": self.reason,
            "description": self.description,
            "findings": [f.to_dict() for f in self.findings],
            "iterations_attempted": self.iterations_attempted,
            "context": self.context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "resolution_notes": self.resolution_notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EscalationRequest":
        findings = [ValidationFinding.from_dict(f) for f in data.get("findings", [])]
        return cls(
            escalation_id=data.get("escalation_id", ""),
            proposal_id=data.get("proposal_id", ""),
            agent_id=data.get("agent_id", ""),
            phase=data.get("phase", ""),
            level=EscalationLevel(data.get("level", "medium")),
            status=EscalationStatus(data.get("status", "open")),
            reason=data.get("reason", ""),
            description=data.get("description", ""),
            findings=findings,
            iterations_attempted=data.get("iterations_attempted", 0),
            context=data.get("context", {}),
            resolution_notes=data.get("resolution_notes", ""),
        )

    def resolve(self, resolved_by: str, notes: str = "") -> None:
        """Mark escalation as resolved."""
        self.status = EscalationStatus.RESOLVED
        self.resolved_at = datetime.now(timezone.utc)
        self.resolved_by = resolved_by
        self.resolution_notes = notes

    def defer(self, notes: str = "") -> None:
        """Defer escalation for later."""
        self.status = EscalationStatus.DEFERRED
        self.resolution_notes = notes

    def dismiss(self, notes: str = "") -> None:
        """Dismiss escalation as not requiring action."""
        self.status = EscalationStatus.DISMISSED
        self.resolution_notes = notes


@dataclass
class EscalationResponse:
    """Response to an escalation request."""

    escalation_id: str = ""
    handler_id: str = ""

    action: str = ""  # "resolved", "deferred", "dismissed", "forwarded"
    resolution: str = ""

    # Suggested changes if resolved
    suggested_changes: List[Dict[str, Any]] = field(default_factory=list)

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "escalation_id": self.escalation_id,
            "handler_id": self.handler_id,
            "action": self.action,
            "resolution": self.resolution,
            "suggested_changes": self.suggested_changes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Type for escalation handler callbacks
EscalationCallback = Callable[[EscalationRequest], Optional[EscalationResponse]]


class EscalationHandler:
    """
    Handles escalations from the propose-validate-revise cycle.

    Provides a registry for escalation handlers by level/phase.
    """

    def __init__(self):
        self._handlers: Dict[str, EscalationCallback] = {}
        self._default_handler: Optional[EscalationCallback] = None
        self._escalation_log: List[EscalationRequest] = []

    def register_handler(
        self,
        handler: EscalationCallback,
        level: Optional[EscalationLevel] = None,
        phase: Optional[str] = None,
    ) -> None:
        """
        Register a handler for escalations.

        Args:
            handler: Callback function for handling escalations
            level: Optional level filter (None = all levels)
            phase: Optional phase filter (None = all phases)
        """
        key = self._make_key(level, phase)
        self._handlers[key] = handler

    def set_default_handler(self, handler: EscalationCallback) -> None:
        """Set the default handler for unmatched escalations."""
        self._default_handler = handler

    def handle(self, request: EscalationRequest) -> Optional[EscalationResponse]:
        """
        Handle an escalation request.

        Finds the most specific handler and invokes it.

        Args:
            request: Escalation to handle

        Returns:
            Response from handler, or None if no handler found
        """
        self._escalation_log.append(request)

        # Try specific handler first
        handler = self._find_handler(request)

        if handler:
            try:
                response = handler(request)
                if response:
                    self._apply_response(request, response)
                return response
            except Exception as e:
                logger.error(f"Escalation handler error: {e}")

        # Fall back to default
        if self._default_handler:
            try:
                response = self._default_handler(request)
                if response:
                    self._apply_response(request, response)
                return response
            except Exception as e:
                logger.error(f"Default escalation handler error: {e}")

        logger.warning(f"No handler for escalation {request.escalation_id}")
        return None

    def _find_handler(self, request: EscalationRequest) -> Optional[EscalationCallback]:
        """Find the most specific handler for a request."""
        # Try level + phase
        key = self._make_key(request.level, request.phase)
        if key in self._handlers:
            return self._handlers[key]

        # Try level only
        key = self._make_key(request.level, None)
        if key in self._handlers:
            return self._handlers[key]

        # Try phase only
        key = self._make_key(None, request.phase)
        if key in self._handlers:
            return self._handlers[key]

        # Try catch-all
        key = self._make_key(None, None)
        if key in self._handlers:
            return self._handlers[key]

        return None

    def _make_key(self, level: Optional[EscalationLevel], phase: Optional[str]) -> str:
        """Create handler lookup key."""
        level_str = level.value if level else "*"
        phase_str = phase or "*"
        return f"{level_str}:{phase_str}"

    def _apply_response(self, request: EscalationRequest, response: EscalationResponse) -> None:
        """Apply response to escalation request."""
        if response.action == "resolved":
            request.resolve(response.handler_id, response.resolution)
        elif response.action == "deferred":
            request.defer(response.resolution)
        elif response.action == "dismissed":
            request.dismiss(response.resolution)

    def get_open_escalations(self) -> List[EscalationRequest]:
        """Get all open escalations."""
        return [e for e in self._escalation_log if e.status == EscalationStatus.OPEN]

    def get_escalations_by_level(self, level: EscalationLevel) -> List[EscalationRequest]:
        """Get escalations by level."""
        return [e for e in self._escalation_log if e.level == level]

    def get_escalations_by_phase(self, phase: str) -> List[EscalationRequest]:
        """Get escalations by phase."""
        return [e for e in self._escalation_log if e.phase == phase]

    def get_escalation_summary(self) -> Dict[str, Any]:
        """Get summary of all escalations."""
        open_count = len([e for e in self._escalation_log if e.status == EscalationStatus.OPEN])
        resolved_count = len([e for e in self._escalation_log if e.status == EscalationStatus.RESOLVED])
        deferred_count = len([e for e in self._escalation_log if e.status == EscalationStatus.DEFERRED])

        by_level = {}
        for level in EscalationLevel:
            by_level[level.value] = len([e for e in self._escalation_log if e.level == level])

        return {
            "total": len(self._escalation_log),
            "open": open_count,
            "resolved": resolved_count,
            "deferred": deferred_count,
            "by_level": by_level,
        }


def create_escalation_from_cycle(
    proposal: Proposal,
    result: ValidationResult,
    reason: str,
    iterations: int,
) -> EscalationRequest:
    """
    Create an escalation request from a failed cycle.

    Args:
        proposal: The proposal that failed
        result: Final validation result
        reason: Reason for escalation
        iterations: Number of iterations attempted

    Returns:
        EscalationRequest ready for handling
    """
    # Determine level based on error count
    if result.error_count >= 5:
        level = EscalationLevel.HIGH
    elif result.error_count >= 2:
        level = EscalationLevel.MEDIUM
    else:
        level = EscalationLevel.LOW

    return EscalationRequest(
        proposal_id=proposal.proposal_id,
        agent_id=proposal.agent_id,
        phase=proposal.phase,
        level=level,
        reason=reason,
        description=f"Proposal {proposal.proposal_id} failed after {iterations} iterations",
        findings=result.findings,
        iterations_attempted=iterations,
        context={
            "proposal": proposal.to_dict(),
            "validation_result": result.to_dict(),
        },
    )
