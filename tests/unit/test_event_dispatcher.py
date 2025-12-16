"""
Unit tests for EventDispatcher.

Tests event subscription, emission, and history.
"""

import pytest
from unittest.mock import Mock, call

from magnet.kernel.event_dispatcher import EventDispatcher
from magnet.kernel.events import (
    KernelEventType,
    KernelEvent,
    StateMutatedEvent,
    PhaseCompletedEvent,
    ActionExecutedEvent,
)


class TestEventDispatcherBasics:
    """Tests for basic EventDispatcher functionality."""

    def test_creation(self):
        """Can create an EventDispatcher."""
        dispatcher = EventDispatcher(design_id="test_design")
        assert dispatcher.design_id == "test_design"
        assert dispatcher.handler_count == 0
        assert dispatcher.event_count == 0

    def test_creation_with_history_limit(self):
        """Can create dispatcher with custom history limit."""
        dispatcher = EventDispatcher(design_id="test", max_history=50)
        assert dispatcher._max_history == 50


class TestSubscription:
    """Tests for event subscription."""

    def test_subscribe_to_event_type(self):
        """Can subscribe to specific event type."""
        dispatcher = EventDispatcher()
        handler = Mock()

        sub_id = dispatcher.subscribe(KernelEventType.STATE_MUTATED, handler)

        assert sub_id != ""
        assert dispatcher.handler_count == 1

    def test_subscribe_all(self):
        """Can subscribe to all events."""
        dispatcher = EventDispatcher()
        handler = Mock()

        sub_id = dispatcher.subscribe_all(handler)

        assert sub_id != ""
        assert dispatcher.handler_count == 1

    def test_unsubscribe(self):
        """Can unsubscribe from event type."""
        dispatcher = EventDispatcher()
        handler = Mock()
        dispatcher.subscribe(KernelEventType.STATE_MUTATED, handler)

        result = dispatcher.unsubscribe(KernelEventType.STATE_MUTATED, handler)

        assert result is True
        assert dispatcher.handler_count == 0

    def test_unsubscribe_nonexistent(self):
        """Unsubscribing nonexistent handler returns False."""
        dispatcher = EventDispatcher()
        handler = Mock()

        result = dispatcher.unsubscribe(KernelEventType.STATE_MUTATED, handler)

        assert result is False

    def test_unsubscribe_all(self):
        """Can unsubscribe from wildcard."""
        dispatcher = EventDispatcher()
        handler = Mock()
        dispatcher.subscribe_all(handler)

        result = dispatcher.unsubscribe_all(handler)

        assert result is True
        assert dispatcher.handler_count == 0

    def test_no_duplicate_subscriptions(self):
        """Same handler is not subscribed twice."""
        dispatcher = EventDispatcher()
        handler = Mock()

        dispatcher.subscribe(KernelEventType.STATE_MUTATED, handler)
        sub_id = dispatcher.subscribe(KernelEventType.STATE_MUTATED, handler)

        assert sub_id == ""  # Second subscribe returns empty
        assert dispatcher.handler_count == 1


class TestEmission:
    """Tests for event emission."""

    def test_emit_to_type_subscriber(self):
        """Events are delivered to type-specific subscribers."""
        dispatcher = EventDispatcher()
        handler = Mock()
        dispatcher.subscribe(KernelEventType.STATE_MUTATED, handler)

        event = StateMutatedEvent(
            design_id="test",
            design_version=1,
            path="hull.loa",
            old_value=30,
            new_value=35,
        )
        dispatcher.emit(event)

        handler.assert_called_once_with(event)

    def test_emit_to_wildcard_subscriber(self):
        """Events are delivered to wildcard subscribers."""
        dispatcher = EventDispatcher()
        handler = Mock()
        dispatcher.subscribe_all(handler)

        event = StateMutatedEvent(design_id="test", design_version=1)
        dispatcher.emit(event)

        handler.assert_called_once_with(event)

    def test_emit_to_both_subscribers(self):
        """Events are delivered to both type and wildcard subscribers."""
        dispatcher = EventDispatcher()
        type_handler = Mock()
        wildcard_handler = Mock()

        dispatcher.subscribe(KernelEventType.STATE_MUTATED, type_handler)
        dispatcher.subscribe_all(wildcard_handler)

        event = StateMutatedEvent(design_id="test", design_version=1)
        dispatcher.emit(event)

        type_handler.assert_called_once_with(event)
        wildcard_handler.assert_called_once_with(event)

    def test_emit_wrong_type_not_delivered(self):
        """Events of wrong type are not delivered to type subscribers."""
        dispatcher = EventDispatcher()
        handler = Mock()
        dispatcher.subscribe(KernelEventType.PHASE_COMPLETED, handler)

        event = StateMutatedEvent(design_id="test", design_version=1)
        dispatcher.emit(event)

        handler.assert_not_called()

    def test_emit_many(self):
        """Can emit multiple events."""
        dispatcher = EventDispatcher()
        handler = Mock()
        dispatcher.subscribe_all(handler)

        events = [
            StateMutatedEvent(design_id="test", design_version=1),
            PhaseCompletedEvent(design_id="test", design_version=2, phase="hull"),
        ]
        dispatcher.emit_many(events)

        assert handler.call_count == 2

    def test_handler_exception_doesnt_break_emission(self):
        """Handler exception doesn't prevent other handlers from running."""
        dispatcher = EventDispatcher()
        failing_handler = Mock(side_effect=Exception("Handler failed"))
        success_handler = Mock()

        dispatcher.subscribe(KernelEventType.STATE_MUTATED, failing_handler)
        dispatcher.subscribe(KernelEventType.STATE_MUTATED, success_handler)

        event = StateMutatedEvent(design_id="test", design_version=1)
        dispatcher.emit(event)  # Should not raise

        success_handler.assert_called_once()


class TestPause:
    """Tests for pause/resume functionality."""

    def test_pause_stops_emission(self):
        """Paused dispatcher drops events."""
        dispatcher = EventDispatcher()
        handler = Mock()
        dispatcher.subscribe_all(handler)

        dispatcher.pause()
        event = StateMutatedEvent(design_id="test", design_version=1)
        dispatcher.emit(event)

        handler.assert_not_called()
        assert dispatcher.is_paused is True

    def test_resume_restores_emission(self):
        """Resumed dispatcher delivers events."""
        dispatcher = EventDispatcher()
        handler = Mock()
        dispatcher.subscribe_all(handler)

        dispatcher.pause()
        dispatcher.resume()

        event = StateMutatedEvent(design_id="test", design_version=1)
        dispatcher.emit(event)

        handler.assert_called_once()
        assert dispatcher.is_paused is False


class TestHistory:
    """Tests for event history."""

    def test_events_stored_in_history(self):
        """Emitted events are stored in history."""
        dispatcher = EventDispatcher()

        event = StateMutatedEvent(design_id="test", design_version=1)
        dispatcher.emit(event)

        assert dispatcher.event_count == 1
        history = dispatcher.get_history()
        assert len(history) == 1
        assert history[0] == event

    def test_history_limit(self):
        """History respects max_history limit."""
        dispatcher = EventDispatcher(max_history=3)

        for i in range(5):
            event = StateMutatedEvent(design_id="test", design_version=i)
            dispatcher.emit(event)

        assert dispatcher.event_count == 3
        history = dispatcher.get_history()
        assert history[0].design_version == 2  # Oldest remaining
        assert history[-1].design_version == 4  # Newest

    def test_history_filter_by_type(self):
        """Can filter history by event type."""
        dispatcher = EventDispatcher()

        dispatcher.emit(StateMutatedEvent(design_id="test", design_version=1))
        dispatcher.emit(PhaseCompletedEvent(design_id="test", design_version=2, phase="hull"))
        dispatcher.emit(StateMutatedEvent(design_id="test", design_version=3))

        history = dispatcher.get_history(event_type=KernelEventType.STATE_MUTATED)
        assert len(history) == 2

    def test_history_limit_parameter(self):
        """Can limit history results."""
        dispatcher = EventDispatcher()

        for i in range(10):
            dispatcher.emit(StateMutatedEvent(design_id="test", design_version=i))

        history = dispatcher.get_history(limit=3)
        assert len(history) == 3
        assert history[-1].design_version == 9  # Most recent

    def test_clear_history(self):
        """Can clear history."""
        dispatcher = EventDispatcher()
        dispatcher.emit(StateMutatedEvent(design_id="test", design_version=1))

        dispatcher.clear_history()

        assert dispatcher.event_count == 0


class TestClearHandlers:
    """Tests for clearing handlers."""

    def test_clear_handlers_by_type(self):
        """Can clear handlers for specific type."""
        dispatcher = EventDispatcher()
        handler1 = Mock()
        handler2 = Mock()

        dispatcher.subscribe(KernelEventType.STATE_MUTATED, handler1)
        dispatcher.subscribe(KernelEventType.PHASE_COMPLETED, handler2)

        dispatcher.clear_handlers(KernelEventType.STATE_MUTATED)

        assert dispatcher.handler_count == 1

    def test_clear_all_handlers(self):
        """Can clear all handlers."""
        dispatcher = EventDispatcher()
        handler1 = Mock()
        handler2 = Mock()
        handler3 = Mock()

        dispatcher.subscribe(KernelEventType.STATE_MUTATED, handler1)
        dispatcher.subscribe(KernelEventType.PHASE_COMPLETED, handler2)
        dispatcher.subscribe_all(handler3)

        dispatcher.clear_handlers()

        assert dispatcher.handler_count == 0


class TestHandlerSummary:
    """Tests for handler summary."""

    def test_get_handler_summary(self):
        """Can get summary of registered handlers."""
        dispatcher = EventDispatcher()

        dispatcher.subscribe(KernelEventType.STATE_MUTATED, Mock())
        dispatcher.subscribe(KernelEventType.STATE_MUTATED, Mock())
        dispatcher.subscribe(KernelEventType.PHASE_COMPLETED, Mock())
        dispatcher.subscribe_all(Mock())

        summary = dispatcher.get_handler_summary()

        assert summary["state_mutated"] == 2
        assert summary["phase_completed"] == 1
        assert summary["wildcard"] == 1


class TestMultipleDispatchers:
    """Tests for multiple dispatcher instances."""

    def test_dispatchers_are_independent(self):
        """Multiple dispatchers are independent."""
        dispatcher1 = EventDispatcher(design_id="design1")
        dispatcher2 = EventDispatcher(design_id="design2")

        handler1 = Mock()
        handler2 = Mock()

        dispatcher1.subscribe_all(handler1)
        dispatcher2.subscribe_all(handler2)

        event = StateMutatedEvent(design_id="design1", design_version=1)
        dispatcher1.emit(event)

        handler1.assert_called_once()
        handler2.assert_not_called()
