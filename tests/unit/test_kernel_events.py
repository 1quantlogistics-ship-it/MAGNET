"""
Unit tests for kernel events.

Tests typed event schemas and serialization.
"""

import pytest
from datetime import datetime, timezone

from magnet.kernel.events import (
    KernelEventType,
    KernelEvent,
    ActionExecutedEvent,
    ActionRejectedEvent,
    PlanValidatedEvent,
    PlanExecutedEvent,
    StateMutatedEvent,
    ParameterLockedEvent,
    ParameterUnlockedEvent,
    DesignVersionIncrementedEvent,
    PhaseStartedEvent,
    PhaseCompletedEvent,
    PhaseFailedEvent,
    PhaseInvalidatedEvent,
    PipelineStartedEvent,
    PipelineCompletedEvent,
    TransactionStartedEvent,
    TransactionCommittedEvent,
    TransactionRolledBackEvent,
    GeometryInvalidatedEvent,
    GeometryRegeneratedEvent,
)


class TestKernelEventType:
    """Tests for KernelEventType enum."""

    def test_event_types_are_strings(self):
        """Event types inherit from str."""
        assert isinstance(KernelEventType.ACTION_EXECUTED.value, str)
        assert KernelEventType.STATE_MUTATED.value == "state_mutated"

    def test_all_event_types_exist(self):
        """All expected event types exist."""
        expected = [
            "action_executed", "action_rejected", "plan_validated", "plan_executed",
            "state_mutated", "parameter_locked", "parameter_unlocked",
            "design_version_incremented", "phase_started", "phase_completed",
            "phase_failed", "phase_invalidated", "pipeline_started", "pipeline_completed",
            "transaction_started", "transaction_committed", "transaction_rolled_back",
            "validation_started", "validation_completed",
            "geometry_invalidated", "geometry_regenerated",
        ]
        actual = [e.value for e in KernelEventType]
        for exp in expected:
            assert exp in actual, f"Missing event type: {exp}"


class TestKernelEvent:
    """Tests for base KernelEvent."""

    def test_event_creation(self):
        """Can create a base event."""
        event = KernelEvent(
            design_id="test_design",
            design_version=5,
        )
        assert event.design_id == "test_design"
        assert event.design_version == 5
        assert event.event_id is not None
        assert event.timestamp is not None

    def test_event_to_dict(self):
        """Event serializes to dict."""
        event = KernelEvent(
            design_id="test_design",
            design_version=5,
        )
        d = event.to_dict()
        assert d["design_id"] == "test_design"
        assert d["design_version"] == 5
        assert d["event_type"] == "state_mutated"  # default
        assert "event_id" in d
        assert "timestamp" in d


class TestActionEvents:
    """Tests for action-related events."""

    def test_action_executed_event(self):
        """ActionExecutedEvent contains action details."""
        event = ActionExecutedEvent(
            design_id="patrol_32ft",
            design_version=10,
            action_type="set",
            path="hull.loa",
            old_value=30.0,
            new_value=35.0,
            unit="m",
            was_clamped=False,
        )
        assert event.event_type == KernelEventType.ACTION_EXECUTED
        assert event.path == "hull.loa"
        assert event.old_value == 30.0
        assert event.new_value == 35.0

        d = event.to_dict()
        assert d["action_type"] == "set"
        assert d["path"] == "hull.loa"
        assert d["was_clamped"] is False

    def test_action_rejected_event(self):
        """ActionRejectedEvent contains rejection reason."""
        event = ActionRejectedEvent(
            design_id="patrol_32ft",
            design_version=10,
            action_type="set",
            path="invalid.path",
            reason="Path not refinable",
        )
        assert event.event_type == KernelEventType.ACTION_REJECTED
        assert event.reason == "Path not refinable"

        d = event.to_dict()
        assert d["reason"] == "Path not refinable"

    def test_plan_validated_event(self):
        """PlanValidatedEvent contains validation summary."""
        event = PlanValidatedEvent(
            design_id="patrol_32ft",
            design_version=10,
            plan_id="plan_001",
            intent_id="intent_001",
            approved_count=5,
            rejected_count=2,
            warnings=["Value clamped for hull.loa"],
        )
        assert event.event_type == KernelEventType.PLAN_VALIDATED
        assert event.approved_count == 5
        assert event.rejected_count == 2

        d = event.to_dict()
        assert d["warnings"] == ["Value clamped for hull.loa"]

    def test_plan_executed_event(self):
        """PlanExecutedEvent contains execution summary."""
        event = PlanExecutedEvent(
            design_id="patrol_32ft",
            design_version=15,
            plan_id="plan_001",
            intent_id="intent_001",
            actions_executed=5,
            design_version_before=10,
            design_version_after=15,
        )
        assert event.event_type == KernelEventType.PLAN_EXECUTED
        assert event.design_version_before == 10
        assert event.design_version_after == 15


class TestStateEvents:
    """Tests for state-related events."""

    def test_state_mutated_event(self):
        """StateMutatedEvent contains mutation details."""
        event = StateMutatedEvent(
            design_id="patrol_32ft",
            design_version=11,
            path="hull.beam",
            old_value=8.0,
            new_value=9.5,
            source="user",
        )
        assert event.event_type == KernelEventType.STATE_MUTATED
        assert event.source == "user"

        d = event.to_dict()
        assert d["path"] == "hull.beam"
        assert d["source"] == "user"

    def test_parameter_locked_event(self):
        """ParameterLockedEvent contains lock details."""
        event = ParameterLockedEvent(
            design_id="patrol_32ft",
            design_version=11,
            path="hull.loa",
            locked_by="user_request",
        )
        assert event.event_type == KernelEventType.PARAMETER_LOCKED
        assert event.locked_by == "user_request"

    def test_parameter_unlocked_event(self):
        """ParameterUnlockedEvent contains path."""
        event = ParameterUnlockedEvent(
            design_id="patrol_32ft",
            design_version=12,
            path="hull.loa",
        )
        assert event.event_type == KernelEventType.PARAMETER_UNLOCKED
        assert event.path == "hull.loa"

    def test_design_version_incremented_event(self):
        """DesignVersionIncrementedEvent contains version info."""
        event = DesignVersionIncrementedEvent(
            design_id="patrol_32ft",
            design_version=11,
            old_version=10,
            new_version=11,
        )
        assert event.event_type == KernelEventType.DESIGN_VERSION_INCREMENTED
        assert event.old_version == 10
        assert event.new_version == 11


class TestPhaseEvents:
    """Tests for phase-related events."""

    def test_phase_started_event(self):
        """PhaseStartedEvent contains phase name."""
        event = PhaseStartedEvent(
            design_id="patrol_32ft",
            design_version=5,
            phase="hull",
        )
        assert event.event_type == KernelEventType.PHASE_STARTED
        assert event.phase == "hull"

    def test_phase_completed_event(self):
        """PhaseCompletedEvent contains duration and outputs."""
        event = PhaseCompletedEvent(
            design_id="patrol_32ft",
            design_version=6,
            phase="hull",
            duration_ms=1234.5,
            outputs={"hull_hash": "abc123"},
        )
        assert event.event_type == KernelEventType.PHASE_COMPLETED
        assert event.duration_ms == 1234.5
        assert event.outputs["hull_hash"] == "abc123"

    def test_phase_failed_event(self):
        """PhaseFailedEvent contains error details."""
        event = PhaseFailedEvent(
            design_id="patrol_32ft",
            design_version=5,
            phase="hull",
            error="Division by zero",
            error_type="ZeroDivisionError",
        )
        assert event.event_type == KernelEventType.PHASE_FAILED
        assert event.error == "Division by zero"
        assert event.error_type == "ZeroDivisionError"

    def test_phase_invalidated_event(self):
        """PhaseInvalidatedEvent contains invalidation reason."""
        event = PhaseInvalidatedEvent(
            design_id="patrol_32ft",
            design_version=7,
            phase="stability",
            reason="Upstream parameter changed",
            triggered_by="hull.loa",
        )
        assert event.event_type == KernelEventType.PHASE_INVALIDATED
        assert event.triggered_by == "hull.loa"


class TestPipelineEvents:
    """Tests for pipeline-related events."""

    def test_pipeline_started_event(self):
        """PipelineStartedEvent contains phase list."""
        event = PipelineStartedEvent(
            design_id="patrol_32ft",
            design_version=5,
            phases=["hull", "weight", "stability"],
        )
        assert event.event_type == KernelEventType.PIPELINE_STARTED
        assert event.phases == ["hull", "weight", "stability"]

    def test_pipeline_completed_event(self):
        """PipelineCompletedEvent contains completion summary."""
        event = PipelineCompletedEvent(
            design_id="patrol_32ft",
            design_version=8,
            phases_completed=["hull", "weight"],
            phases_failed=["stability"],
            total_duration_ms=5000.0,
        )
        assert event.event_type == KernelEventType.PIPELINE_COMPLETED
        assert "stability" in event.phases_failed


class TestTransactionEvents:
    """Tests for transaction-related events."""

    def test_transaction_started_event(self):
        """TransactionStartedEvent contains transaction ID."""
        event = TransactionStartedEvent(
            design_id="patrol_32ft",
            design_version=5,
            transaction_id="txn_001",
        )
        assert event.event_type == KernelEventType.TRANSACTION_STARTED
        assert event.transaction_id == "txn_001"

    def test_transaction_committed_event(self):
        """TransactionCommittedEvent contains commit summary."""
        event = TransactionCommittedEvent(
            design_id="patrol_32ft",
            design_version=6,
            transaction_id="txn_001",
            changes_count=3,
        )
        assert event.event_type == KernelEventType.TRANSACTION_COMMITTED
        assert event.changes_count == 3

    def test_transaction_rolled_back_event(self):
        """TransactionRolledBackEvent contains rollback reason."""
        event = TransactionRolledBackEvent(
            design_id="patrol_32ft",
            design_version=5,
            transaction_id="txn_001",
            reason="Validation failed",
        )
        assert event.event_type == KernelEventType.TRANSACTION_ROLLED_BACK
        assert event.reason == "Validation failed"


class TestGeometryEvents:
    """Tests for geometry-related events."""

    def test_geometry_invalidated_event(self):
        """GeometryInvalidatedEvent contains invalidation details."""
        event = GeometryInvalidatedEvent(
            design_id="patrol_32ft",
            design_version=7,
            geometry_type="hull",
            invalidated_by="hull.loa",
        )
        assert event.event_type == KernelEventType.GEOMETRY_INVALIDATED
        assert event.invalidated_by == "hull.loa"

    def test_geometry_regenerated_event(self):
        """GeometryRegeneratedEvent contains geometry details."""
        event = GeometryRegeneratedEvent(
            design_id="patrol_32ft",
            design_version=8,
            geometry_type="hull",
            hull_hash="abc123def456",
            vertex_count=15000,
        )
        assert event.event_type == KernelEventType.GEOMETRY_REGENERATED
        assert event.hull_hash == "abc123def456"
        assert event.vertex_count == 15000
