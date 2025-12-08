"""
Unit tests for dependencies/revalidation.py

Tests the RevalidationScheduler that bridges Module 03 (Dependency Engine)
with Module 04 (Validation Pipeline).
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from magnet.dependencies.revalidation import (
    RevalidationTask,
    RevalidationScheduler,
)


class TestRevalidationTask:
    """Test RevalidationTask dataclass."""

    def test_create_task(self):
        """Test creating a revalidation task."""
        task = RevalidationTask(
            validator_id="hull/volume",
            priority=1,
        )
        assert task.validator_id == "hull/volume"
        assert task.priority == 1
        assert task.triggered_by == ""

    def test_create_task_with_metadata(self):
        """Test creating task with full metadata."""
        task = RevalidationTask(
            validator_id="hull/volume",
            priority=2,
            triggered_by="LOA",
            triggered_by_user="designer",
            reason="Parameter changed",
        )
        assert task.triggered_by == "LOA"
        assert task.triggered_by_user == "designer"
        assert task.reason == "Parameter changed"

    def test_task_ordering_by_priority(self):
        """Test tasks ordered by priority (lower = higher priority)."""
        task_high = RevalidationTask(validator_id="a", priority=1)
        task_low = RevalidationTask(validator_id="b", priority=5)

        assert task_high < task_low

    def test_task_ordering_by_time_same_priority(self):
        """Test tasks with same priority ordered by queue time."""
        task_early = RevalidationTask(
            validator_id="a",
            priority=1,
            queued_at=datetime(2024, 1, 1, 12, 0, 0),
        )
        task_late = RevalidationTask(
            validator_id="b",
            priority=1,
            queued_at=datetime(2024, 1, 1, 13, 0, 0),
        )

        assert task_early < task_late

    def test_to_dict(self):
        """Test serialization."""
        task = RevalidationTask(
            validator_id="hull/volume",
            priority=2,
            triggered_by="LOA",
        )

        data = task.to_dict()
        assert data["validator_id"] == "hull/volume"
        assert data["priority"] == 2
        assert data["triggered_by"] == "LOA"
        assert "queued_at" in data

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "validator_id": "hull/volume",
            "priority": 3,
            "queued_at": "2024-01-01T12:00:00",
            "triggered_by": "beam",
            "triggered_by_user": "engineer",
            "reason": "Value updated",
        }

        task = RevalidationTask.from_dict(data)
        assert task.validator_id == "hull/volume"
        assert task.priority == 3
        assert task.triggered_by == "beam"
        assert task.reason == "Value updated"

    def test_from_dict_defaults(self):
        """Test deserialization with minimal data."""
        data = {"validator_id": "test/v"}

        task = RevalidationTask.from_dict(data)
        assert task.validator_id == "test/v"
        assert task.priority == 1  # Default


class TestRevalidationScheduler:
    """Test RevalidationScheduler class."""

    def test_create_scheduler(self):
        """Test creating scheduler."""
        scheduler = RevalidationScheduler()
        assert scheduler.is_empty == True
        assert scheduler.processed_count == 0

    def test_create_scheduler_with_executor(self):
        """Test creating scheduler with executor."""
        executor = Mock()
        scheduler = RevalidationScheduler(executor=executor)
        assert scheduler._executor == executor

    def test_set_executor(self):
        """Test setting executor after creation."""
        scheduler = RevalidationScheduler()
        executor = Mock()
        scheduler.set_executor(executor)
        assert scheduler._executor == executor

    def test_queue_validator(self):
        """Test queuing a single validator."""
        scheduler = RevalidationScheduler()

        result = scheduler.queue_validator("hull/volume", triggered_by="LOA")
        assert result == True
        assert scheduler.get_pending_count() == 1
        assert scheduler.is_empty == False

    def test_queue_validator_duplicate(self):
        """Test duplicate validator not re-queued."""
        scheduler = RevalidationScheduler()

        scheduler.queue_validator("hull/volume")
        result = scheduler.queue_validator("hull/volume")

        assert result == False
        assert scheduler.get_pending_count() == 1

    def test_queue_validators(self):
        """Test queuing multiple validators."""
        scheduler = RevalidationScheduler()

        count = scheduler.queue_validators(
            ["hull/volume", "hull/wetted", "hull/stability"],
            triggered_by="LOA",
        )

        assert count == 3
        assert scheduler.get_pending_count() == 3

    def test_queue_validators_with_duplicates(self):
        """Test queuing multiple validators with duplicates."""
        scheduler = RevalidationScheduler()
        scheduler.queue_validator("hull/volume")

        count = scheduler.queue_validators(
            ["hull/volume", "hull/wetted"],
            triggered_by="beam",
        )

        assert count == 1  # Only hull/wetted queued
        assert scheduler.get_pending_count() == 2

    def test_get_pending(self):
        """Test getting pending tasks."""
        scheduler = RevalidationScheduler()
        scheduler.queue_validator("hull/volume", priority=2)
        scheduler.queue_validator("hull/wetted", priority=1)

        pending = scheduler.get_pending()
        assert len(pending) == 2

    def test_peek_next(self):
        """Test peeking at next task."""
        scheduler = RevalidationScheduler()
        scheduler.queue_validator("hull/volume", priority=2)
        scheduler.queue_validator("hull/wetted", priority=1)

        task = scheduler.peek_next()
        assert task.validator_id == "hull/wetted"  # Higher priority
        # Should not remove from queue
        assert scheduler.get_pending_count() == 2

    def test_peek_next_empty(self):
        """Test peeking at empty queue."""
        scheduler = RevalidationScheduler()
        assert scheduler.peek_next() is None

    def test_pop_next(self):
        """Test popping next task."""
        scheduler = RevalidationScheduler()
        scheduler.queue_validator("hull/volume", priority=2)
        scheduler.queue_validator("hull/wetted", priority=1)

        task = scheduler.pop_next()
        assert task.validator_id == "hull/wetted"
        assert scheduler.get_pending_count() == 1

    def test_pop_next_empty(self):
        """Test popping from empty queue."""
        scheduler = RevalidationScheduler()
        assert scheduler.pop_next() is None

    def test_priority_ordering(self):
        """Test tasks processed in priority order."""
        scheduler = RevalidationScheduler()

        # Queue in wrong order
        scheduler.queue_validator("low", priority=3)
        scheduler.queue_validator("high", priority=1)
        scheduler.queue_validator("medium", priority=2)

        # Should come out in priority order
        assert scheduler.pop_next().validator_id == "high"
        assert scheduler.pop_next().validator_id == "medium"
        assert scheduler.pop_next().validator_id == "low"

    def test_clear_queue(self):
        """Test clearing the queue."""
        scheduler = RevalidationScheduler()
        scheduler.queue_validators(["a", "b", "c"])

        count = scheduler.clear_queue()
        assert count == 3
        assert scheduler.is_empty == True

    def test_remove_validator(self):
        """Test removing specific validator."""
        scheduler = RevalidationScheduler()
        scheduler.queue_validators(["a", "b", "c"])

        result = scheduler.remove_validator("b")
        assert result == True
        assert scheduler.get_pending_count() == 2

        # Verify b is gone
        ids = [t.validator_id for t in scheduler.get_pending()]
        assert "b" not in ids

    def test_remove_validator_not_found(self):
        """Test removing validator not in queue."""
        scheduler = RevalidationScheduler()
        scheduler.queue_validator("a")

        result = scheduler.remove_validator("not_there")
        assert result == False

    def test_process_next_no_executor(self):
        """Test processing without executor set."""
        scheduler = RevalidationScheduler()
        scheduler.queue_validator("test")

        result = scheduler.process_next()
        assert result is None  # Can't process without executor

    def test_process_next_empty(self):
        """Test processing empty queue."""
        executor = Mock()
        scheduler = RevalidationScheduler(executor=executor)

        result = scheduler.process_next()
        assert result is None

    def test_process_pending_limit(self):
        """Test processing with limit."""
        executor = Mock()
        executor.execute_validators = Mock(return_value=Mock())

        scheduler = RevalidationScheduler(executor=executor)
        scheduler.queue_validators(["a", "b", "c", "d", "e"])

        processed = scheduler.process_pending(max_count=2)
        assert len(processed) == 2
        assert scheduler.get_pending_count() == 3

    def test_process_all(self):
        """Test processing all pending validators."""
        executor = Mock()
        executor.execute_validators = Mock(return_value=Mock())

        scheduler = RevalidationScheduler(executor=executor)
        scheduler.queue_validators(["a", "b", "c"])

        processed = scheduler.process_all()
        assert len(processed) == 3
        assert scheduler.is_empty == True

    def test_processed_count(self):
        """Test processed count tracking."""
        executor = Mock()
        executor.execute_validators = Mock(return_value=Mock())

        scheduler = RevalidationScheduler(executor=executor)
        scheduler.queue_validators(["a", "b"])

        scheduler.process_all()
        assert scheduler.processed_count == 2

    def test_add_callback(self):
        """Test adding callback."""
        executor = Mock()
        executor.execute_validators = Mock(return_value=Mock())

        scheduler = RevalidationScheduler(executor=executor)

        callback_results = []
        def callback(vid):
            callback_results.append(vid)

        scheduler.add_callback(callback)
        scheduler.queue_validator("test")
        scheduler.process_next()

        assert "test" in callback_results

    def test_remove_callback(self):
        """Test removing callback."""
        scheduler = RevalidationScheduler()

        callback = Mock()
        scheduler.add_callback(callback)
        scheduler.remove_callback(callback)

        assert callback not in scheduler._callbacks

    def test_get_stats(self):
        """Test getting scheduler stats."""
        scheduler = RevalidationScheduler()
        scheduler.queue_validators(["a", "b", "c"])

        stats = scheduler.get_stats()
        assert stats["pending_count"] == 3
        assert stats["processed_count"] == 0
        assert "a" in stats["queued_validator_ids"]

    def test_to_dict(self):
        """Test serialization."""
        scheduler = RevalidationScheduler()
        scheduler.queue_validator("hull/volume", priority=2, triggered_by="LOA")
        scheduler._processed_count = 5

        data = scheduler.to_dict()
        assert len(data["queue"]) == 1
        assert data["processed_count"] == 5

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "queue": [
                {"validator_id": "hull/volume", "priority": 2, "queued_at": "2024-01-01T12:00:00"},
                {"validator_id": "hull/wetted", "priority": 1, "queued_at": "2024-01-01T12:01:00"},
            ],
            "processed_count": 10,
        }

        scheduler = RevalidationScheduler.from_dict(data)
        assert scheduler.get_pending_count() == 2
        assert scheduler.processed_count == 10

        # Check priority ordering is maintained
        task = scheduler.peek_next()
        assert task.validator_id == "hull/wetted"  # Lower priority value = higher priority

    def test_round_trip_serialization(self):
        """Test serialize/deserialize round trip."""
        scheduler = RevalidationScheduler()
        scheduler.queue_validator("a", priority=3)
        scheduler.queue_validator("b", priority=1)
        scheduler.queue_validator("c", priority=2)
        scheduler._processed_count = 100

        data = scheduler.to_dict()
        loaded = RevalidationScheduler.from_dict(data)

        assert loaded.get_pending_count() == 3
        assert loaded.processed_count == 100
        # Priority ordering maintained
        assert loaded.pop_next().validator_id == "b"


class TestRevalidationSchedulerIntegration:
    """Integration tests for scheduler with executor."""

    def test_full_workflow(self):
        """Test complete workflow from queue to process."""
        # Mock executor
        executor = Mock()
        executor.execute_validators = Mock(return_value=Mock())

        scheduler = RevalidationScheduler(executor=executor)

        # Queue validators triggered by parameter change
        scheduler.queue_validators(
            ["hull/volume", "hull/wetted", "stability/gm"],
            triggered_by="LOA",
            priority=1,
            reason="LOA changed from 100m to 105m",
        )

        # Process all
        processed = scheduler.process_all()

        assert len(processed) == 3
        assert scheduler.is_empty == True
        assert scheduler.processed_count == 3

        # Verify executor was called
        assert executor.execute_validators.call_count == 3

    def test_priority_respects_dependencies(self):
        """Test that high priority validators process first."""
        executor = Mock()
        executor.execute_validators = Mock(return_value=Mock())

        scheduler = RevalidationScheduler(executor=executor)

        # Queue with different priorities
        scheduler.queue_validator("less_critical", priority=3)
        scheduler.queue_validator("critical", priority=1)
        scheduler.queue_validator("normal", priority=2)

        processed = scheduler.process_all()

        # Should process in priority order
        assert processed == ["critical", "normal", "less_critical"]

    def test_callback_integration(self):
        """Test callbacks fire during processing."""
        executor = Mock()
        executor.execute_validators = Mock(return_value=Mock())

        scheduler = RevalidationScheduler(executor=executor)

        processed_order = []
        def track_order(vid):
            processed_order.append(vid)

        scheduler.add_callback(track_order)
        scheduler.queue_validators(["a", "b", "c"], priority=1)
        scheduler.process_all()

        assert len(processed_order) == 3
