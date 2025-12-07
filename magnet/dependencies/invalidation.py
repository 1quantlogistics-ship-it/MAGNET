"""
MAGNET Invalidation Engine

Module 03 v1.1 - Production-Ready

Handles cascade invalidation when parameters change.
Marks downstream computed values as stale.

v1.1 Fixes Applied:
- FIX #5: Invalidation reasons enumerated
- FIX #6: Scoped invalidation (parameter vs phase vs all)
- FIX #7: Integration with Phase State Machine
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, TYPE_CHECKING
import logging
import uuid

if TYPE_CHECKING:
    from .graph import DependencyGraph
    from magnet.core.state_manager import StateManager
    from magnet.core.phase_states import PhaseStateMachine

logger = logging.getLogger(__name__)


# =============================================================================
# INVALIDATION TYPES (FIX #5)
# =============================================================================

class InvalidationReason(Enum):
    """Why invalidation occurred."""
    PARAMETER_CHANGED = "parameter_changed"       # Upstream value changed
    MANUAL_INVALIDATION = "manual_invalidation"   # User/system forced invalidation
    PHASE_UNLOCKED = "phase_unlocked"            # Phase was unlocked for editing
    DEPENDENCY_INVALIDATED = "dependency_invalidated"  # Upstream was invalidated
    SCHEMA_MIGRATION = "schema_migration"         # Schema changed
    CACHE_EXPIRED = "cache_expired"              # Cached value expired
    VALIDATION_FAILED = "validation_failed"       # Validation failure triggered recalc


class InvalidationScope(Enum):
    """Scope of invalidation."""
    PARAMETER = "parameter"    # Single parameter
    PHASE = "phase"           # All parameters in a phase
    DOWNSTREAM = "downstream"  # All downstream of a parameter
    ALL = "all"               # Everything


# =============================================================================
# INVALIDATION EVENT
# =============================================================================

@dataclass
class InvalidationEvent:
    """Record of an invalidation occurrence."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # What triggered invalidation
    trigger_parameter: Optional[str] = None
    trigger_phase: Optional[str] = None
    reason: InvalidationReason = InvalidationReason.PARAMETER_CHANGED
    scope: InvalidationScope = InvalidationScope.DOWNSTREAM

    # What was affected
    invalidated_parameters: List[str] = field(default_factory=list)
    invalidated_phases: List[str] = field(default_factory=list)

    # Context
    triggered_by: str = "system"
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for persistence/logging."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "trigger_parameter": self.trigger_parameter,
            "trigger_phase": self.trigger_phase,
            "reason": self.reason.value,
            "scope": self.scope.value,
            "invalidated_parameters": self.invalidated_parameters,
            "invalidated_phases": self.invalidated_phases,
            "triggered_by": self.triggered_by,
            "old_value": str(self.old_value) if self.old_value is not None else None,
            "new_value": str(self.new_value) if self.new_value is not None else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvalidationEvent":
        """Load from serialized data."""
        return cls(
            event_id=data.get("event_id", str(uuid.uuid4())[:8]),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.utcnow(),
            trigger_parameter=data.get("trigger_parameter"),
            trigger_phase=data.get("trigger_phase"),
            reason=InvalidationReason(data.get("reason", "parameter_changed")),
            scope=InvalidationScope(data.get("scope", "downstream")),
            invalidated_parameters=data.get("invalidated_parameters", []),
            invalidated_phases=data.get("invalidated_phases", []),
            triggered_by=data.get("triggered_by", "system"),
            metadata=data.get("metadata", {}),
        )


# =============================================================================
# INVALIDATION ENGINE
# =============================================================================

class InvalidationEngine:
    """
    Handles cascade invalidation of computed values.

    v1.1 Fixes:
    - FIX #5: Tracks invalidation reasons
    - FIX #6: Supports scoped invalidation
    - FIX #7: Integrates with Phase State Machine
    """

    def __init__(
        self,
        dependency_graph: "DependencyGraph",
        state_manager: Optional["StateManager"] = None,
        phase_machine: Optional["PhaseStateMachine"] = None,
    ):
        self._graph = dependency_graph
        self._state_manager = state_manager
        self._phase_machine = phase_machine

        # Invalidation state
        self._stale_parameters: Set[str] = set()
        self._stale_phases: Set[str] = set()

        # Event history
        self._events: List[InvalidationEvent] = []
        self._max_events: int = 1000

        # Callbacks
        self._on_invalidate_callbacks: List[Callable[[InvalidationEvent], None]] = []

    def invalidate_parameter(
        self,
        param: str,
        reason: InvalidationReason = InvalidationReason.PARAMETER_CHANGED,
        triggered_by: str = "system",
        old_value: Any = None,
        new_value: Any = None,
        cascade: bool = True,
    ) -> InvalidationEvent:
        """
        Invalidate a parameter and optionally cascade to dependents.

        Args:
            param: Parameter path to invalidate
            reason: Why invalidation is happening
            triggered_by: Who/what triggered this
            old_value: Previous value (for logging)
            new_value: New value (for logging)
            cascade: Whether to invalidate downstream parameters

        Returns:
            InvalidationEvent describing what was invalidated
        """
        event = InvalidationEvent(
            trigger_parameter=param,
            reason=reason,
            scope=InvalidationScope.DOWNSTREAM if cascade else InvalidationScope.PARAMETER,
            triggered_by=triggered_by,
            old_value=old_value,
            new_value=new_value,
        )

        # Mark this parameter as stale
        self._stale_parameters.add(param)
        event.invalidated_parameters.append(param)

        # Get phase for this parameter
        from .graph import get_phase_for_parameter
        param_phase = get_phase_for_parameter(param)
        if param_phase:
            event.trigger_phase = param_phase
            self._stale_phases.add(param_phase)
            event.invalidated_phases.append(param_phase)

        # Cascade to downstream parameters
        if cascade:
            downstream = self._graph.get_all_downstream(param)
            for downstream_param in downstream:
                self._stale_parameters.add(downstream_param)
                event.invalidated_parameters.append(downstream_param)

            # Also mark downstream phases
            downstream_phases = self._graph.get_downstream_phases(param)
            for phase in downstream_phases:
                self._stale_phases.add(phase)
                if phase not in event.invalidated_phases:
                    event.invalidated_phases.append(phase)

        # FIX #7: Update phase state machine if connected
        if self._phase_machine and event.invalidated_phases:
            self._update_phase_states(event.invalidated_phases, reason)

        # Record event
        self._record_event(event)

        # Notify callbacks
        self._notify_callbacks(event)

        logger.info(
            f"Invalidated {len(event.invalidated_parameters)} parameters, "
            f"{len(event.invalidated_phases)} phases due to {param} change"
        )

        return event

    def invalidate_phase(
        self,
        phase: str,
        reason: InvalidationReason = InvalidationReason.PHASE_UNLOCKED,
        triggered_by: str = "system",
    ) -> InvalidationEvent:
        """
        Invalidate all parameters in a phase and its downstream phases.

        Args:
            phase: Phase name to invalidate
            reason: Why invalidation is happening
            triggered_by: Who/what triggered this

        Returns:
            InvalidationEvent describing what was invalidated
        """
        event = InvalidationEvent(
            trigger_phase=phase,
            reason=reason,
            scope=InvalidationScope.PHASE,
            triggered_by=triggered_by,
        )

        # Get all parameters in this phase
        phase_params = self._graph.get_parameters_for_phase(phase)

        for param in phase_params:
            self._stale_parameters.add(param)
            event.invalidated_parameters.append(param)

        self._stale_phases.add(phase)
        event.invalidated_phases.append(phase)

        # Get downstream phases
        from .graph import DOWNSTREAM_PHASES
        downstream_phases = DOWNSTREAM_PHASES.get(phase, [])

        for downstream_phase in downstream_phases:
            downstream_params = self._graph.get_parameters_for_phase(downstream_phase)
            for param in downstream_params:
                self._stale_parameters.add(param)
                event.invalidated_parameters.append(param)
            self._stale_phases.add(downstream_phase)
            event.invalidated_phases.append(downstream_phase)

        # FIX #7: Update phase state machine
        if self._phase_machine:
            self._update_phase_states(event.invalidated_phases, reason)

        # Record and notify
        self._record_event(event)
        self._notify_callbacks(event)

        logger.info(
            f"Phase invalidation: {phase} -> "
            f"{len(event.invalidated_parameters)} parameters, "
            f"{len(event.invalidated_phases)} phases"
        )

        return event

    def invalidate_all(
        self,
        reason: InvalidationReason = InvalidationReason.SCHEMA_MIGRATION,
        triggered_by: str = "system",
    ) -> InvalidationEvent:
        """Invalidate all parameters and phases."""
        event = InvalidationEvent(
            reason=reason,
            scope=InvalidationScope.ALL,
            triggered_by=triggered_by,
        )

        # Invalidate all parameters
        all_params = self._graph.get_all_parameters()
        for param in all_params:
            self._stale_parameters.add(param)
            event.invalidated_parameters.append(param)

        # Invalidate all phases
        from .graph import PHASE_OWNERSHIP
        for phase in PHASE_OWNERSHIP.keys():
            self._stale_phases.add(phase)
            event.invalidated_phases.append(phase)

        # FIX #7: Update phase state machine
        if self._phase_machine:
            self._update_phase_states(event.invalidated_phases, reason)

        self._record_event(event)
        self._notify_callbacks(event)

        logger.warning(
            f"Full invalidation: {len(event.invalidated_parameters)} parameters, "
            f"{len(event.invalidated_phases)} phases"
        )

        return event

    def mark_valid(self, param: str) -> None:
        """Mark a parameter as no longer stale (after recalculation)."""
        self._stale_parameters.discard(param)

        # Check if phase is now clean
        from .graph import get_phase_for_parameter
        phase = get_phase_for_parameter(param)
        if phase:
            phase_params = self._graph.get_parameters_for_phase(phase)
            if not any(p in self._stale_parameters for p in phase_params):
                self._stale_phases.discard(phase)

    def mark_phase_valid(self, phase: str) -> None:
        """Mark all parameters in a phase as valid."""
        phase_params = self._graph.get_parameters_for_phase(phase)
        for param in phase_params:
            self._stale_parameters.discard(param)
        self._stale_phases.discard(phase)

    def is_stale(self, param: str) -> bool:
        """Check if a parameter is stale."""
        return param in self._stale_parameters

    def is_phase_stale(self, phase: str) -> bool:
        """Check if any parameter in a phase is stale."""
        return phase in self._stale_phases

    def get_stale_parameters(self) -> Set[str]:
        """Get all stale parameters."""
        return self._stale_parameters.copy()

    def get_stale_phases(self) -> Set[str]:
        """Get all stale phases."""
        return self._stale_phases.copy()

    def get_stale_parameters_for_phase(self, phase: str) -> List[str]:
        """Get stale parameters in a specific phase."""
        phase_params = self._graph.get_parameters_for_phase(phase)
        return [p for p in phase_params if p in self._stale_parameters]

    def get_recalculation_order(self) -> List[str]:
        """Get stale parameters in order for recalculation."""
        return self._graph.get_computation_order(self._stale_parameters)

    def _update_phase_states(
        self,
        phases: List[str],
        reason: InvalidationReason
    ) -> None:
        """
        FIX #7: Update phase state machine after invalidation.

        Transitions phases to INVALIDATED state where appropriate.
        """
        if not self._phase_machine:
            return

        from magnet.core.enums import PhaseState

        for phase in phases:
            current_state = self._phase_machine.get_phase_status(phase)

            # Only invalidate locked/approved/completed phases
            if current_state in [
                PhaseState.LOCKED,
                PhaseState.APPROVED,
                PhaseState.COMPLETED
            ]:
                try:
                    self._phase_machine.transition_phase(
                        phase,
                        PhaseState.INVALIDATED,
                        triggered_by="InvalidationEngine",
                        reason=f"Invalidated due to {reason.value}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not transition {phase} to INVALIDATED: {e}"
                    )

    def _record_event(self, event: InvalidationEvent) -> None:
        """Record an invalidation event."""
        self._events.append(event)

        # Trim old events
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]

    def _notify_callbacks(self, event: InvalidationEvent) -> None:
        """Notify registered callbacks of invalidation."""
        for callback in self._on_invalidate_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Invalidation callback error: {e}")

    def on_invalidate(self, callback: Callable[[InvalidationEvent], None]) -> None:
        """Register a callback for invalidation events."""
        self._on_invalidate_callbacks.append(callback)

    def get_events(
        self,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[InvalidationEvent]:
        """Get invalidation events, optionally filtered."""
        events = self._events
        if since:
            events = [e for e in events if e.timestamp >= since]
        return events[-limit:]

    def clear_stale(self) -> None:
        """Clear all stale markers (use after full recalculation)."""
        self._stale_parameters.clear()
        self._stale_phases.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize invalidation state."""
        return {
            "stale_parameters": list(self._stale_parameters),
            "stale_phases": list(self._stale_phases),
            "recent_events": [e.to_dict() for e in self._events[-100:]],
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load invalidation state from serialized data."""
        self._stale_parameters = set(data.get("stale_parameters", []))
        self._stale_phases = set(data.get("stale_phases", []))
        self._events = [
            InvalidationEvent.from_dict(e)
            for e in data.get("recent_events", [])
        ]
