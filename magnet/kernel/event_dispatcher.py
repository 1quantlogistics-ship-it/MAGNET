"""
MAGNET EventDispatcher v1.0

Instance-scoped event dispatcher for kernel operations.

Unlike the UI's singleton EventBus (ui/events.py), this dispatcher
is instance-scoped and injected into kernel components. This allows:
- Testing with isolated dispatchers
- Multiple designs with separate event streams
- Clear ownership (kernel owns truth, events follow)

INVARIANT: Each design session has its own EventDispatcher instance.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Type
import logging
import weakref

from magnet.kernel.events import KernelEvent, KernelEventType


logger = logging.getLogger("kernel.event_dispatcher")


# Type alias for event handlers
EventHandler = Callable[[KernelEvent], None]


@dataclass
class Subscription:
    """
    Represents an event subscription.

    Tracks the handler and event type for management.
    """
    handler: EventHandler
    event_type: Optional[KernelEventType]  # None = wildcard
    subscription_id: str = field(default_factory=lambda: "")


class EventDispatcher:
    """
    Instance-scoped event dispatcher for kernel operations.

    Features:
    - Type-specific subscriptions
    - Wildcard subscriptions (receive all events)
    - Event history (configurable depth)
    - Async-ready (handlers can be async-wrapped externally)
    - WebSocket bridge support via subscribe_all

    Usage:
        dispatcher = EventDispatcher(design_id="patrol_32ft")

        # Subscribe to specific event type
        dispatcher.subscribe(KernelEventType.STATE_MUTATED, handler)

        # Subscribe to all events (e.g., for WebSocket broadcast)
        dispatcher.subscribe_all(ws_broadcast_handler)

        # Emit an event
        dispatcher.emit(StateMutatedEvent(...))
    """

    def __init__(
        self,
        design_id: str = "",
        max_history: int = 100,
    ):
        """
        Initialize the event dispatcher.

        Args:
            design_id: Associated design (for context in events)
            max_history: Maximum events to retain in history
        """
        self._design_id = design_id
        self._max_history = max_history

        # Type-specific handlers: event_type -> list of handlers
        self._handlers: Dict[KernelEventType, List[EventHandler]] = {}

        # Wildcard handlers (receive all events)
        self._wildcard_handlers: List[EventHandler] = []

        # Event history for debugging/audit
        self._history: List[KernelEvent] = []

        # Subscription counter for IDs
        self._subscription_counter = 0

        # Paused state
        self._paused = False

        logger.debug(f"EventDispatcher created for design_id={design_id}")

    @property
    def design_id(self) -> str:
        """Get the associated design ID."""
        return self._design_id

    def subscribe(
        self,
        event_type: KernelEventType,
        handler: EventHandler,
    ) -> str:
        """
        Subscribe to events of a specific type.

        Args:
            event_type: Type of events to receive
            handler: Callback function(event) -> None

        Returns:
            Subscription ID for unsubscribing
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            self._subscription_counter += 1
            sub_id = f"sub_{self._subscription_counter}"
            logger.debug(f"Subscribed {sub_id} to {event_type.value}")
            return sub_id

        return ""

    def subscribe_all(self, handler: EventHandler) -> str:
        """
        Subscribe to all events (wildcard).

        Use this for WebSocket broadcast or logging.

        Args:
            handler: Callback function(event) -> None

        Returns:
            Subscription ID for unsubscribing
        """
        if handler not in self._wildcard_handlers:
            self._wildcard_handlers.append(handler)
            self._subscription_counter += 1
            sub_id = f"sub_all_{self._subscription_counter}"
            logger.debug(f"Subscribed {sub_id} as wildcard")
            return sub_id

        return ""

    def unsubscribe(
        self,
        event_type: KernelEventType,
        handler: EventHandler,
    ) -> bool:
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
        Unsubscribe from wildcard events.

        Args:
            handler: Handler to remove

        Returns:
            True if handler was removed
        """
        try:
            self._wildcard_handlers.remove(handler)
            logger.debug("Unsubscribed wildcard handler")
            return True
        except ValueError:
            return False

    def emit(self, event: KernelEvent) -> None:
        """
        Emit an event to all subscribers.

        Args:
            event: Event to emit
        """
        if self._paused:
            logger.debug(f"Dispatcher paused, dropping: {event.event_type.value}")
            return

        # Ensure design_id is set
        if not event.design_id and self._design_id:
            # Events are frozen, so we need to work around this
            # In practice, events should be created with design_id
            pass

        # Add to history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        logger.debug(
            f"Emitting {event.event_type.value} "
            f"(design={event.design_id}, version={event.design_version})"
        )

        # Notify type-specific handlers
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler failed for {event.event_type.value}: {e}")

        # Notify wildcard handlers
        for handler in self._wildcard_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Wildcard handler failed: {e}")

    def emit_many(self, events: List[KernelEvent]) -> None:
        """
        Emit multiple events in order.

        Args:
            events: Events to emit
        """
        for event in events:
            self.emit(event)

    def pause(self) -> None:
        """Pause event emission (events are dropped)."""
        self._paused = True
        logger.debug("EventDispatcher paused")

    def resume(self) -> None:
        """Resume event emission."""
        self._paused = False
        logger.debug("EventDispatcher resumed")

    @property
    def is_paused(self) -> bool:
        """Check if dispatcher is paused."""
        return self._paused

    def clear_handlers(self, event_type: Optional[KernelEventType] = None) -> None:
        """
        Clear event handlers.

        Args:
            event_type: Specific type to clear, or None for all
        """
        if event_type:
            self._handlers.pop(event_type, None)
            logger.debug(f"Cleared handlers for {event_type.value}")
        else:
            self._handlers.clear()
            self._wildcard_handlers.clear()
            logger.debug("Cleared all handlers")

    def get_history(
        self,
        limit: int = 20,
        event_type: Optional[KernelEventType] = None,
    ) -> List[KernelEvent]:
        """
        Get event history.

        Args:
            limit: Maximum events to return
            event_type: Filter by type (optional)

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
        logger.debug("Cleared event history")

    @property
    def handler_count(self) -> int:
        """Get total number of registered handlers."""
        count = sum(len(handlers) for handlers in self._handlers.values())
        count += len(self._wildcard_handlers)
        return count

    @property
    def event_count(self) -> int:
        """Get number of events in history."""
        return len(self._history)

    def get_handler_summary(self) -> Dict[str, int]:
        """
        Get summary of registered handlers by type.

        Returns:
            Dict mapping event type name to handler count
        """
        summary = {}
        for event_type, handlers in self._handlers.items():
            summary[event_type.value] = len(handlers)
        summary["wildcard"] = len(self._wildcard_handlers)
        return summary
