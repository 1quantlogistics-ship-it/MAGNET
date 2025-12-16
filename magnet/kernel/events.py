"""
MAGNET Kernel Events v1.0

Typed event schemas for kernel-level operations.

These events are emitted by the kernel (not UI) and represent
authoritative state transitions. They are distinct from ui/events.py
which handles UI-specific events.

INVARIANT: Kernel events are the source of truth for state changes.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


# =============================================================================
# EVENT TYPES
# =============================================================================

class KernelEventType(str, Enum):
    """Types of kernel events."""

    # Action events
    ACTION_EXECUTED = "action_executed"
    ACTION_REJECTED = "action_rejected"
    PLAN_VALIDATED = "plan_validated"
    PLAN_EXECUTED = "plan_executed"

    # State events
    STATE_MUTATED = "state_mutated"
    PARAMETER_LOCKED = "parameter_locked"
    PARAMETER_UNLOCKED = "parameter_unlocked"
    DESIGN_VERSION_INCREMENTED = "design_version_incremented"

    # Phase events
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    PHASE_FAILED = "phase_failed"
    PHASE_INVALIDATED = "phase_invalidated"

    # Pipeline events
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_COMPLETED = "pipeline_completed"

    # Transaction events
    TRANSACTION_STARTED = "transaction_started"
    TRANSACTION_COMMITTED = "transaction_committed"
    TRANSACTION_ROLLED_BACK = "transaction_rolled_back"

    # Validation events
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"

    # Geometry events
    GEOMETRY_INVALIDATED = "geometry_invalidated"
    GEOMETRY_REGENERATED = "geometry_regenerated"


# =============================================================================
# BASE EVENT
# =============================================================================

@dataclass
class KernelEvent:
    """
    Base class for kernel events.

    All kernel events have:
    - event_id: Unique identifier
    - event_type: Type classification
    - design_id: Associated design
    - timestamp: When the event occurred
    - design_version: State version at time of event
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    event_type: KernelEventType = KernelEventType.STATE_MUTATED
    design_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    design_version: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "design_id": self.design_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "design_version": self.design_version,
        }


# =============================================================================
# ACTION EVENTS
# =============================================================================

@dataclass
class ActionExecutedEvent(KernelEvent):
    """
    Emitted when an action is successfully executed.

    Contains the action details and resulting state change.
    """
    event_type: KernelEventType = field(default=KernelEventType.ACTION_EXECUTED)
    action_type: str = ""
    path: Optional[str] = None
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    unit: Optional[str] = None
    was_clamped: bool = False

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "action_type": self.action_type,
            "path": self.path,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "unit": self.unit,
            "was_clamped": self.was_clamped,
        })
        return base


@dataclass
class ActionRejectedEvent(KernelEvent):
    """
    Emitted when an action is rejected by the validator.

    Contains the rejection reason for debugging/audit.
    """
    event_type: KernelEventType = field(default=KernelEventType.ACTION_REJECTED)
    action_type: str = ""
    path: Optional[str] = None
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "action_type": self.action_type,
            "path": self.path,
            "reason": self.reason,
        })
        return base


@dataclass
class PlanValidatedEvent(KernelEvent):
    """
    Emitted when an ActionPlan is validated.

    Contains summary of approved/rejected actions.
    """
    event_type: KernelEventType = field(default=KernelEventType.PLAN_VALIDATED)
    plan_id: str = ""
    intent_id: str = ""
    approved_count: int = 0
    rejected_count: int = 0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "plan_id": self.plan_id,
            "intent_id": self.intent_id,
            "approved_count": self.approved_count,
            "rejected_count": self.rejected_count,
            "warnings": self.warnings,
        })
        return base


@dataclass
class PlanExecutedEvent(KernelEvent):
    """
    Emitted when an ActionPlan is fully executed.

    Contains execution summary.
    """
    event_type: KernelEventType = field(default=KernelEventType.PLAN_EXECUTED)
    plan_id: str = ""
    intent_id: str = ""
    actions_executed: int = 0
    design_version_before: int = 0
    design_version_after: int = 0

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "plan_id": self.plan_id,
            "intent_id": self.intent_id,
            "actions_executed": self.actions_executed,
            "design_version_before": self.design_version_before,
            "design_version_after": self.design_version_after,
        })
        return base


# =============================================================================
# STATE EVENTS
# =============================================================================

@dataclass
class StateMutatedEvent(KernelEvent):
    """
    Emitted when state is mutated.

    This is the authoritative record of a state change.
    """
    event_type: KernelEventType = field(default=KernelEventType.STATE_MUTATED)
    path: str = ""
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "path": self.path,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "source": self.source,
        })
        return base


@dataclass
class ParameterLockedEvent(KernelEvent):
    """Emitted when a parameter is locked."""
    event_type: KernelEventType = field(default=KernelEventType.PARAMETER_LOCKED)
    path: str = ""
    locked_by: str = ""

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "path": self.path,
            "locked_by": self.locked_by,
        })
        return base


@dataclass
class ParameterUnlockedEvent(KernelEvent):
    """Emitted when a parameter is unlocked."""
    event_type: KernelEventType = field(default=KernelEventType.PARAMETER_UNLOCKED)
    path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "path": self.path,
        })
        return base


@dataclass
class DesignVersionIncrementedEvent(KernelEvent):
    """Emitted when design_version increments (on commit)."""
    event_type: KernelEventType = field(default=KernelEventType.DESIGN_VERSION_INCREMENTED)
    old_version: int = 0
    new_version: int = 0

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "old_version": self.old_version,
            "new_version": self.new_version,
        })
        return base


# =============================================================================
# PHASE EVENTS
# =============================================================================

@dataclass
class PhaseStartedEvent(KernelEvent):
    """Emitted when a phase begins execution."""
    event_type: KernelEventType = field(default=KernelEventType.PHASE_STARTED)
    phase: str = ""

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({"phase": self.phase})
        return base


@dataclass
class PhaseCompletedEvent(KernelEvent):
    """Emitted when a phase completes successfully."""
    event_type: KernelEventType = field(default=KernelEventType.PHASE_COMPLETED)
    phase: str = ""
    duration_ms: float = 0.0
    outputs: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "phase": self.phase,
            "duration_ms": self.duration_ms,
            "outputs": self.outputs,
        })
        return base


@dataclass
class PhaseFailedEvent(KernelEvent):
    """Emitted when a phase fails."""
    event_type: KernelEventType = field(default=KernelEventType.PHASE_FAILED)
    phase: str = ""
    error: str = ""
    error_type: str = ""

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "phase": self.phase,
            "error": self.error,
            "error_type": self.error_type,
        })
        return base


@dataclass
class PhaseInvalidatedEvent(KernelEvent):
    """Emitted when a phase is invalidated due to upstream changes."""
    event_type: KernelEventType = field(default=KernelEventType.PHASE_INVALIDATED)
    phase: str = ""
    reason: str = ""
    triggered_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "phase": self.phase,
            "reason": self.reason,
            "triggered_by": self.triggered_by,
        })
        return base


# =============================================================================
# PIPELINE EVENTS
# =============================================================================

@dataclass
class PipelineStartedEvent(KernelEvent):
    """Emitted when a pipeline begins."""
    event_type: KernelEventType = field(default=KernelEventType.PIPELINE_STARTED)
    phases: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({"phases": self.phases})
        return base


@dataclass
class PipelineCompletedEvent(KernelEvent):
    """Emitted when a pipeline completes."""
    event_type: KernelEventType = field(default=KernelEventType.PIPELINE_COMPLETED)
    phases_completed: List[str] = field(default_factory=list)
    phases_failed: List[str] = field(default_factory=list)
    total_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "phases_completed": self.phases_completed,
            "phases_failed": self.phases_failed,
            "total_duration_ms": self.total_duration_ms,
        })
        return base


# =============================================================================
# TRANSACTION EVENTS
# =============================================================================

@dataclass
class TransactionStartedEvent(KernelEvent):
    """Emitted when a transaction begins."""
    event_type: KernelEventType = field(default=KernelEventType.TRANSACTION_STARTED)
    transaction_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({"transaction_id": self.transaction_id})
        return base


@dataclass
class TransactionCommittedEvent(KernelEvent):
    """Emitted when a transaction is committed."""
    event_type: KernelEventType = field(default=KernelEventType.TRANSACTION_COMMITTED)
    transaction_id: str = ""
    changes_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "transaction_id": self.transaction_id,
            "changes_count": self.changes_count,
        })
        return base


@dataclass
class TransactionRolledBackEvent(KernelEvent):
    """Emitted when a transaction is rolled back."""
    event_type: KernelEventType = field(default=KernelEventType.TRANSACTION_ROLLED_BACK)
    transaction_id: str = ""
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "transaction_id": self.transaction_id,
            "reason": self.reason,
        })
        return base


# =============================================================================
# GEOMETRY EVENTS
# =============================================================================

@dataclass
class GeometryInvalidatedEvent(KernelEvent):
    """Emitted when geometry becomes stale due to parameter changes."""
    event_type: KernelEventType = field(default=KernelEventType.GEOMETRY_INVALIDATED)
    geometry_type: str = ""
    invalidated_by: str = ""

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "geometry_type": self.geometry_type,
            "invalidated_by": self.invalidated_by,
        })
        return base


@dataclass
class GeometryRegeneratedEvent(KernelEvent):
    """Emitted when geometry is regenerated."""
    event_type: KernelEventType = field(default=KernelEventType.GEOMETRY_REGENERATED)
    geometry_type: str = ""
    hull_hash: str = ""
    vertex_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "geometry_type": self.geometry_type,
            "hull_hash": self.hull_hash,
            "vertex_count": self.vertex_count,
        })
        return base
