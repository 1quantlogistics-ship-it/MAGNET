"""
Unit tests for ActionExecutor.

Tests action execution against StateManager.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from magnet.kernel.action_executor import ActionExecutor, ExecutionResult
from magnet.kernel.intent_protocol import Action, ActionPlan, ActionType
from magnet.kernel.event_dispatcher import EventDispatcher
from magnet.kernel.events import KernelEventType


class MockStateManager:
    """Mock StateManager for testing."""

    def __init__(self):
        self._state = Mock()
        self._state.design_id = "test_design"
        self._state.design_version = 0
        self._data = {}
        self._locked = set()
        self._in_transaction = False
        self._active_txn = None
        self._snapshot = {}
        self.rollback_called = False
        self.last_source = None

    @property
    def design_version(self):
        return self._state.design_version

    def begin_transaction(self):
        self._in_transaction = True
        self._snapshot = dict(self._data)
        self._active_txn = "txn_001"
        return self._active_txn

    def commit(self):
        self._in_transaction = False
        self._state.design_version += 1
        self._active_txn = None
        self._snapshot = {}
        return self._state.design_version

    def rollback_transaction(self, txn_id=None):
        self._in_transaction = False
        self.rollback_called = True
        # Restore snapshot to simulate atomic rollback
        self._data = dict(self._snapshot)
        self._active_txn = None

    def get(self, path):
        return self._data.get(path)

    def set(self, path, value, source=None):
        self._data[path] = value
        self.last_source = source

    def is_locked(self, path):
        return path in self._locked

    def lock_parameter(self, path):
        self._locked.add(path)

    def unlock_parameter(self, path):
        self._locked.discard(path)


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_creation(self):
        """Can create ExecutionResult."""
        result = ExecutionResult(
            success=True,
            actions_executed=3,
            design_version_before=5,
            design_version_after=6,
        )
        assert result.success is True
        assert result.actions_executed == 3

    def test_with_warnings(self):
        """ExecutionResult can contain warnings."""
        result = ExecutionResult(
            success=True,
            actions_executed=1,
            design_version_before=0,
            design_version_after=1,
            warnings=["Value was clamped"],
        )
        assert len(result.warnings) == 1


class TestActionExecutorBasics:
    """Tests for basic ActionExecutor functionality."""

    def test_creation(self):
        """Can create ActionExecutor."""
        sm = MockStateManager()
        executor = ActionExecutor(sm)
        assert executor._state_manager == sm

    def test_creation_with_dispatcher(self):
        """Can create ActionExecutor with EventDispatcher."""
        sm = MockStateManager()
        dispatcher = EventDispatcher()
        executor = ActionExecutor(sm, dispatcher)
        assert executor._events == dispatcher


class TestExecuteSet:
    """Tests for executing SET actions."""

    def test_execute_set_action(self):
        """Can execute SET action."""
        sm = MockStateManager()
        executor = ActionExecutor(sm)

        actions = [
            Action(action_type=ActionType.SET, path="hull.loa", value=100.0),
        ]

        result = executor.execute(actions)

        assert result.success is True
        assert result.actions_executed == 1
        assert sm._data["hull.loa"] == 100.0

    def test_execute_multiple_set_actions(self):
        """Can execute multiple SET actions."""
        sm = MockStateManager()
        executor = ActionExecutor(sm)

        actions = [
            Action(action_type=ActionType.SET, path="hull.loa", value=100.0),
            Action(action_type=ActionType.SET, path="hull.beam", value=15.0),
            Action(action_type=ActionType.SET, path="hull.draft", value=3.0),
        ]

        result = executor.execute(actions)

        assert result.success is True
        assert result.actions_executed == 3
        assert sm._data["hull.loa"] == 100.0
        assert sm._data["hull.beam"] == 15.0

    def test_set_emits_events(self):
        """SET action emits events."""
        sm = MockStateManager()
        dispatcher = EventDispatcher(design_id="test")
        executor = ActionExecutor(sm, dispatcher)

        handler = Mock()
        dispatcher.subscribe(KernelEventType.STATE_MUTATED, handler)

        actions = [
            Action(action_type=ActionType.SET, path="hull.loa", value=100.0),
        ]

        executor.execute(actions)

        handler.assert_called()


class TestExecuteLock:
    """Tests for executing LOCK actions."""

    def test_execute_lock_action(self):
        """Can execute LOCK action."""
        sm = MockStateManager()
        executor = ActionExecutor(sm)

        actions = [
            Action(action_type=ActionType.LOCK, path="hull.loa"),
        ]

        result = executor.execute(actions)

        assert result.success is True
        assert result.actions_executed == 1
        assert sm.is_locked("hull.loa")

    def test_lock_emits_event(self):
        """LOCK action emits ParameterLockedEvent."""
        sm = MockStateManager()
        dispatcher = EventDispatcher()
        executor = ActionExecutor(sm, dispatcher)

        handler = Mock()
        dispatcher.subscribe(KernelEventType.PARAMETER_LOCKED, handler)

        actions = [
            Action(action_type=ActionType.LOCK, path="hull.loa"),
        ]

        executor.execute(actions)

        handler.assert_called_once()


class TestExecuteUnlock:
    """Tests for executing UNLOCK actions."""

    def test_execute_unlock_action(self):
        """Can execute UNLOCK action."""
        sm = MockStateManager()
        sm.lock_parameter("hull.loa")
        executor = ActionExecutor(sm)

        actions = [
            Action(action_type=ActionType.UNLOCK, path="hull.loa"),
        ]

        result = executor.execute(actions)

        assert result.success is True
        assert result.actions_executed == 1
        assert not sm.is_locked("hull.loa")

    def test_unlock_emits_event(self):
        """UNLOCK action emits ParameterUnlockedEvent."""
        sm = MockStateManager()
        dispatcher = EventDispatcher()
        executor = ActionExecutor(sm, dispatcher)

        handler = Mock()
        dispatcher.subscribe(KernelEventType.PARAMETER_UNLOCKED, handler)

        actions = [
            Action(action_type=ActionType.UNLOCK, path="hull.loa"),
        ]

        executor.execute(actions)

        handler.assert_called_once()


class TestExecuteRunPhases:
    """Tests for executing RUN_PHASES actions."""

    def test_execute_run_phases_action(self):
        """Can execute RUN_PHASES action."""
        sm = MockStateManager()
        executor = ActionExecutor(sm)

        actions = [
            Action(action_type=ActionType.RUN_PHASES, phases=["hull", "weight"]),
        ]

        result = executor.execute(actions)

        assert result.success is True
        assert result.actions_executed == 1
        assert any("delegated to Conductor" in w for w in result.warnings)

    def test_run_phases_emits_phase_started_events(self):
        """RUN_PHASES emits PhaseStartedEvent for each phase."""
        sm = MockStateManager()
        dispatcher = EventDispatcher()
        executor = ActionExecutor(sm, dispatcher)

        handler = Mock()
        dispatcher.subscribe(KernelEventType.PHASE_STARTED, handler)

        actions = [
            Action(action_type=ActionType.RUN_PHASES, phases=["hull", "weight", "stability"]),
        ]

        executor.execute(actions)

        assert handler.call_count == 3


class TestExecuteExport:
    """Tests for executing EXPORT actions."""

    def test_execute_export_action(self):
        """Can execute EXPORT action."""
        sm = MockStateManager()
        executor = ActionExecutor(sm)

        actions = [
            Action(action_type=ActionType.EXPORT, format="json"),
        ]

        result = executor.execute(actions)

        assert result.success is True
        assert any("EXPORT" in w for w in result.warnings)


class TestExecuteClarification:
    """Tests for executing REQUEST_CLARIFICATION actions."""

    def test_execute_clarification_action(self):
        """Can execute REQUEST_CLARIFICATION action."""
        sm = MockStateManager()
        executor = ActionExecutor(sm)

        actions = [
            Action(
                action_type=ActionType.REQUEST_CLARIFICATION,
                message="What units for speed?",
            ),
        ]

        result = executor.execute(actions)

        assert result.success is True
        assert any("Clarification" in w for w in result.warnings)


class TestExecuteNoop:
    """Tests for executing NOOP actions."""

    def test_execute_noop_action(self):
        """Can execute NOOP action."""
        sm = MockStateManager()
        executor = ActionExecutor(sm)

        actions = [
            Action(action_type=ActionType.NOOP),
        ]

        result = executor.execute(actions)

        assert result.success is True
        assert result.actions_executed == 1


class TestVersionTracking:
    """Tests for design_version tracking."""

    def test_version_increments_on_execute(self):
        """design_version increments after execution."""
        sm = MockStateManager()
        sm._state.design_version = 5
        executor = ActionExecutor(sm)

        actions = [
            Action(action_type=ActionType.SET, path="hull.loa", value=100.0),
        ]

        result = executor.execute(actions)

        assert result.design_version_before == 5
        assert result.design_version_after == 6

    def test_version_increment_event_emitted(self):
        """DesignVersionIncrementedEvent is emitted."""
        sm = MockStateManager()
        dispatcher = EventDispatcher()
        executor = ActionExecutor(sm, dispatcher)

        handler = Mock()
        dispatcher.subscribe(KernelEventType.DESIGN_VERSION_INCREMENTED, handler)

        actions = [
            Action(action_type=ActionType.SET, path="hull.loa", value=100.0),
        ]

        executor.execute(actions)

        handler.assert_called_once()


class TestEmptyActions:
    """Tests for executing empty action list."""

    def test_execute_empty_actions(self):
        """Executing empty list succeeds with no changes."""
        sm = MockStateManager()
        sm._state.design_version = 5
        executor = ActionExecutor(sm)

        result = executor.execute([])

        assert result.success is True
        assert result.actions_executed == 0
        assert result.design_version_before == 5
        assert result.design_version_after == 5


class TestPlanContext:
    """Tests for ActionPlan context in execution."""

    def test_plan_executed_event_emitted(self):
        """PlanExecutedEvent is emitted with plan context."""
        sm = MockStateManager()
        dispatcher = EventDispatcher()
        executor = ActionExecutor(sm, dispatcher)

        events_received = []
        def capture_event(event):
            events_received.append(event)

        dispatcher.subscribe(KernelEventType.PLAN_EXECUTED, capture_event)

        plan = ActionPlan(
            plan_id="plan_001",
            intent_id="intent_001",
            design_id="test_design",
            design_version_before=0,
            actions=[
                Action(action_type=ActionType.SET, path="hull.loa", value=100.0),
            ],
            proposed_at=datetime.now(timezone.utc),
        )

        actions = [
            Action(action_type=ActionType.SET, path="hull.loa", value=100.0),
        ]

        executor.execute(actions, plan)

        assert len(events_received) == 1
        assert events_received[0].plan_id == "plan_001"

    def test_executor_sets_source_includes_provenance_plan_and_intent(self):
        """Source string includes provenance, plan_id, and intent_id."""
        sm = MockStateManager()
        executor = ActionExecutor(sm)

        plan = ActionPlan(
            plan_id="det_plan_123",
            intent_id="intent_abc",
            design_id="test_design",
            design_version_before=0,
            actions=[
                Action(action_type=ActionType.SET, path="hull.loa", value=100.0),
            ],
            proposed_at=datetime.now(timezone.utc),
        )

        actions = [
            Action(action_type=ActionType.SET, path="hull.loa", value=100.0),
        ]

        executor.execute(actions, plan)

        assert sm.last_source is not None
        assert "prov=deterministic" in sm.last_source
        assert "plan=det_plan_123" in sm.last_source
        assert "intent=intent_abc" in sm.last_source


class TestTransactionHandling:
    """Tests for transaction handling."""

    def test_transaction_started_and_committed(self):
        """Transaction is started and committed."""
        sm = MockStateManager()
        executor = ActionExecutor(sm)

        actions = [
            Action(action_type=ActionType.SET, path="hull.loa", value=100.0),
        ]

        executor.execute(actions)

        # Transaction should be complete
        assert sm._in_transaction is False

    def test_execute_is_atomic_rolls_back_on_action_error(self):
        """Any action error triggers rollback and no partial commit."""
        sm = MockStateManager()

        # Make set raise an exception
        sm.set = Mock(side_effect=Exception("Set failed"))

        executor = ActionExecutor(sm)

        actions = [
            Action(action_type=ActionType.SET, path="hull.loa", value=100.0),
        ]

        result = executor.execute(actions)

        assert result.success is False
        assert result.actions_executed == 0
        assert sm.rollback_called is True
        assert sm.design_version == 0  # no version bump
        assert "Set failed" in result.errors[0]

    def test_transaction_rolled_back_on_commit_error(self):
        """Transaction is rolled back if commit fails."""
        sm = MockStateManager()
        sm.commit = Mock(side_effect=Exception("Commit failed"))

        executor = ActionExecutor(sm)

        actions = [
            Action(action_type=ActionType.SET, path="hull.loa", value=100.0),
        ]

        result = executor.execute(actions)

        assert result.success is False
        assert sm.rollback_called is True
        assert "Commit failed" in result.errors[0] or "Execution failed" in result.errors[0]
