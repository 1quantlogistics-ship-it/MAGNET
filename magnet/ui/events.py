"""
ui/events.py - UI Event System

Module 54: UI Components

Provides event bus for UI component communication.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime, timezone
from enum import Enum
import uuid
import logging
import weakref

logger = logging.getLogger("ui.events")


class EventType(Enum):
    """Types of UI events."""

    # State events
    STATE_CHANGED = "state_changed"
    STATE_LOADED = "state_loaded"
    STATE_SAVED = "state_saved"

    # Phase events
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    PHASE_FAILED = "phase_failed"
    PHASE_APPROVED = "phase_approved"

    # Validation events
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    VALIDATION_ERROR = "validation_error"

    # Design events
    DESIGN_CREATED = "design_created"
    DESIGN_LOADED = "design_loaded"
    DESIGN_SAVED = "design_saved"

    # Vision events
    SNAPSHOT_CREATED = "snapshot_created"
    GEOMETRY_GENERATED = "geometry_generated"
    RENDER_COMPLETED = "render_completed"

    # Report events
    REPORT_STARTED = "report_started"
    REPORT_COMPLETED = "report_completed"

    # UI events
    DASHBOARD_REFRESH = "dashboard_refresh"
    PANEL_UPDATED = "panel_updated"
    NAVIGATION_CHANGED = "navigation_changed"

    # Agent events
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_MESSAGE = "agent_message"

    # Generic
    CUSTOM = "custom"


@dataclass
class UIEvent:
    """A UI event with payload."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    event_type: EventType = EventType.CUSTOM
    source: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Dict[str, Any] = field(default_factory=dict)
    propagate: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "type": self.event_type.value,
            "source": self.source,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "payload": self.payload,
        }

    @classmethod
    def state_changed(cls, path: str, old_value: Any, new_value: Any, source: str = "unknown") -> "UIEvent":
        """Create a state changed event."""
        return cls(
            event_type=EventType.STATE_CHANGED,
            source=source,
            payload={
                "path": path,
                "old_value": old_value,
                "new_value": new_value,
            },
        )

    @classmethod
    def phase_completed(cls, phase: str, status: str, source: str = "conductor") -> "UIEvent":
        """Create a phase completed event."""
        return cls(
            event_type=EventType.PHASE_COMPLETED,
            source=source,
            payload={
                "phase": phase,
                "status": status,
            },
        )

    @classmethod
    def validation_completed(cls, passed: bool, errors: int, warnings: int, source: str = "validator") -> "UIEvent":
        """Create a validation completed event."""
        return cls(
            event_type=EventType.VALIDATION_COMPLETED,
            source=source,
            payload={
                "passed": passed,
                "error_count": errors,
                "warning_count": warnings,
            },
        )

    @classmethod
    def snapshot_created(cls, snapshot_id: str, path: str, phase: str = "", source: str = "vision") -> "UIEvent":
        """Create a snapshot created event."""
        return cls(
            event_type=EventType.SNAPSHOT_CREATED,
            source=source,
            payload={
                "snapshot_id": snapshot_id,
                "path": path,
                "phase": phase,
            },
        )


# Type alias for event handlers
EventHandler = Callable[[UIEvent], None]


class EventBus:
    """
    Central event bus for UI component communication.

    Supports:
    - Event subscription by type
    - Wildcard subscriptions (receive all events)
    - Weak references to prevent memory leaks
    - Event history for debugging
    """

    _instance: Optional["EventBus"] = None

    def __new__(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._wildcard_handlers: List[EventHandler] = []
        self._history: List[UIEvent] = []
        self._max_history: int = 100
        self._paused: bool = False
        self._initialized = True

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """
        Subscribe to events of a specific type.

        Args:
            event_type: Type of events to receive
            handler: Callback function(event) -> None
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            logger.debug(f"Subscribed handler to {event_type.value}")

    def subscribe_all(self, handler: EventHandler) -> None:
        """
        Subscribe to all events.

        Args:
            handler: Callback function(event) -> None
        """
        if handler not in self._wildcard_handlers:
            self._wildcard_handlers.append(handler)
            logger.debug("Subscribed wildcard handler")

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> bool:
        """
        Unsubscribe from events of a specific type.

        Args:
            event_type: Type of events
            handler: Handler to remove

        Returns:
            True if handler was removed
        """
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                logger.debug(f"Unsubscribed handler from {event_type.value}")
                return True
            except ValueError:
                pass
        return False

    def unsubscribe_all(self, handler: EventHandler) -> bool:
        """
        Unsubscribe from all events.

        Args:
            handler: Handler to remove

        Returns:
            True if handler was removed
        """
        try:
            self._wildcard_handlers.remove(handler)
            return True
        except ValueError:
            return False

    def emit(self, event: UIEvent) -> None:
        """
        Emit an event to all subscribers.

        Args:
            event: Event to emit
        """
        if self._paused:
            logger.debug(f"Event bus paused, dropping event: {event.event_type.value}")
            return

        # Add to history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        logger.debug(f"Emitting event: {event.event_type.value} from {event.source}")

        # Notify type-specific handlers
        for handler in self._handlers.get(event.event_type, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler failed: {e}")

        # Notify wildcard handlers
        if event.propagate:
            for handler in self._wildcard_handlers:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Wildcard handler failed: {e}")

    def emit_simple(
        self,
        event_type: EventType,
        source: str = "",
        **payload,
    ) -> UIEvent:
        """
        Emit a simple event with payload.

        Args:
            event_type: Type of event
            source: Event source identifier
            **payload: Event payload data

        Returns:
            The emitted event
        """
        event = UIEvent(
            event_type=event_type,
            source=source,
            payload=payload,
        )
        self.emit(event)
        return event

    def pause(self) -> None:
        """Pause event emission."""
        self._paused = True
        logger.debug("Event bus paused")

    def resume(self) -> None:
        """Resume event emission."""
        self._paused = False
        logger.debug("Event bus resumed")

    def clear_handlers(self, event_type: Optional[EventType] = None) -> None:
        """
        Clear event handlers.

        Args:
            event_type: Specific type to clear, or None for all
        """
        if event_type:
            self._handlers.pop(event_type, None)
        else:
            self._handlers.clear()
            self._wildcard_handlers.clear()

    def get_history(self, limit: int = 20, event_type: Optional[EventType] = None) -> List[UIEvent]:
        """
        Get event history.

        Args:
            limit: Maximum events to return
            event_type: Filter by type

        Returns:
            List of recent events
        """
        history = self._history
        if event_type:
            history = [e for e in history if e.event_type == event_type]
        return history[-limit:]

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()

    @property
    def handler_count(self) -> int:
        """Get total number of registered handlers."""
        count = sum(len(handlers) for handlers in self._handlers.values())
        count += len(self._wildcard_handlers)
        return count


# Global singleton instance
event_bus = EventBus()


def emit_state_changed(path: str, old_value: Any, new_value: Any, source: str = "unknown") -> None:
    """Convenience function to emit state changed event."""
    event = UIEvent.state_changed(path, old_value, new_value, source)
    event_bus.emit(event)


def emit_phase_completed(phase: str, status: str, source: str = "conductor") -> None:
    """Convenience function to emit phase completed event."""
    event = UIEvent.phase_completed(phase, status, source)
    event_bus.emit(event)


def emit_validation_completed(passed: bool, errors: int = 0, warnings: int = 0, source: str = "validator") -> None:
    """Convenience function to emit validation completed event."""
    event = UIEvent.validation_completed(passed, errors, warnings, source)
    event_bus.emit(event)


def emit_snapshot_created(snapshot_id: str, path: str, phase: str = "", source: str = "vision") -> None:
    """Convenience function to emit snapshot created event."""
    event = UIEvent.snapshot_created(snapshot_id, path, phase, source)
    event_bus.emit(event)
