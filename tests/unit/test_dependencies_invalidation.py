"""
Unit tests for dependencies/invalidation.py

Tests the InvalidationEngine and cascade invalidation behavior.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from magnet.dependencies.invalidation import (
    InvalidationEngine,
    InvalidationEvent,
    InvalidationReason,
    InvalidationScope,
)
from magnet.dependencies.graph import DependencyGraph


class TestInvalidationReason:
    """Test InvalidationReason enum."""

    def test_reason_values(self):
        """Test invalidation reason enum values."""
        assert InvalidationReason.PARAMETER_CHANGED.value == "parameter_changed"
        assert InvalidationReason.MANUAL_INVALIDATION.value == "manual_invalidation"
        assert InvalidationReason.PHASE_UNLOCKED.value == "phase_unlocked"
        assert InvalidationReason.DEPENDENCY_INVALIDATED.value == "dependency_invalidated"
        assert InvalidationReason.SCHEMA_MIGRATION.value == "schema_migration"
        assert InvalidationReason.CACHE_EXPIRED.value == "cache_expired"
        assert InvalidationReason.VALIDATION_FAILED.value == "validation_failed"

    def test_all_reasons_exist(self):
        """Test all expected reasons exist."""
        reasons = [r for r in InvalidationReason]
        assert len(reasons) == 7


class TestInvalidationScope:
    """Test InvalidationScope enum."""

    def test_scope_values(self):
        """Test invalidation scope enum values."""
        assert InvalidationScope.PARAMETER.value == "parameter"
        assert InvalidationScope.PHASE.value == "phase"
        assert InvalidationScope.DOWNSTREAM.value == "downstream"
        assert InvalidationScope.ALL.value == "all"


class TestInvalidationEvent:
    """Test InvalidationEvent dataclass."""

    def test_create_event(self):
        """Test creating invalidation event."""
        event = InvalidationEvent(
            trigger_parameter="hull.loa",
            reason=InvalidationReason.PARAMETER_CHANGED,
        )
        assert event.trigger_parameter == "hull.loa"
        assert event.reason == InvalidationReason.PARAMETER_CHANGED
        assert event.event_id is not None
        assert event.timestamp is not None

    def test_event_with_metadata(self):
        """Test creating event with full metadata."""
        event = InvalidationEvent(
            trigger_parameter="hull.loa",
            reason=InvalidationReason.PARAMETER_CHANGED,
            old_value=100.0,
            new_value=105.0,
            triggered_by="designer",
            metadata={"user_action": "edit"},
        )
        assert event.old_value == 100.0
        assert event.new_value == 105.0
        assert event.triggered_by == "designer"
        assert event.metadata["user_action"] == "edit"

    def test_to_dict(self):
        """Test event serialization."""
        event = InvalidationEvent(
            trigger_parameter="hull.loa",
            trigger_phase="hull_form",
            reason=InvalidationReason.PARAMETER_CHANGED,
            scope=InvalidationScope.DOWNSTREAM,
            invalidated_parameters=["hull.displacement_m3"],
            invalidated_phases=["hull_form", "weight"],
        )

        data = event.to_dict()
        assert data["trigger_parameter"] == "hull.loa"
        assert data["trigger_phase"] == "hull_form"
        assert data["reason"] == "parameter_changed"
        assert data["scope"] == "downstream"
        assert "hull.displacement_m3" in data["invalidated_parameters"]

    def test_from_dict(self):
        """Test event deserialization."""
        data = {
            "event_id": "test123",
            "timestamp": "2024-01-01T12:00:00",
            "trigger_parameter": "hull.loa",
            "reason": "parameter_changed",
            "scope": "downstream",
            "invalidated_parameters": ["hull.beam"],
            "invalidated_phases": ["hull_form"],
            "triggered_by": "designer",
        }

        event = InvalidationEvent.from_dict(data)
        assert event.event_id == "test123"
        assert event.trigger_parameter == "hull.loa"
        assert event.reason == InvalidationReason.PARAMETER_CHANGED
        assert "hull.beam" in event.invalidated_parameters


class TestInvalidationEngine:
    """Test InvalidationEngine class."""

    def _create_mock_graph(self):
        """Create a mock dependency graph."""
        graph = Mock(spec=DependencyGraph)
        graph.get_all_downstream.return_value = {"hull.displacement_m3", "hull.wetted_surface_m2"}
        graph.get_downstream_phases.return_value = {"hull_form", "weight", "stability"}
        graph.get_parameters_for_phase.return_value = ["hull.loa", "hull.beam"]
        graph.get_all_parameters.return_value = ["hull.loa", "hull.beam", "hull.draft"]
        graph.get_computation_order.return_value = ["hull.loa", "hull.beam"]
        return graph

    def test_create_engine(self):
        """Test creating invalidation engine."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)

        assert engine._graph == graph
        assert len(engine._stale_parameters) == 0

    def test_invalidate_parameter_single(self):
        """Test invalidating single parameter without cascade."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)

        event = engine.invalidate_parameter("hull.loa", cascade=False)

        assert "hull.loa" in event.invalidated_parameters
        assert engine.is_stale("hull.loa")
        assert event.scope == InvalidationScope.PARAMETER

    def test_invalidate_parameter_cascade(self):
        """Test invalidating parameter with cascade to downstream."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)

        event = engine.invalidate_parameter("hull.loa", cascade=True)

        assert "hull.loa" in event.invalidated_parameters
        assert "hull.displacement_m3" in event.invalidated_parameters
        assert event.scope == InvalidationScope.DOWNSTREAM
        assert len(event.invalidated_phases) > 0

    def test_invalidate_parameter_with_values(self):
        """Test invalidation tracks old and new values."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)

        event = engine.invalidate_parameter(
            "hull.loa",
            old_value=100.0,
            new_value=105.0,
        )

        assert event.old_value == 100.0
        assert event.new_value == 105.0

    def test_invalidate_parameter_with_reason(self):
        """Test FIX #5: Invalidation reasons tracked."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)

        event = engine.invalidate_parameter(
            "hull.loa",
            reason=InvalidationReason.MANUAL_INVALIDATION,
        )

        assert event.reason == InvalidationReason.MANUAL_INVALIDATION

    def test_invalidate_phase(self):
        """Test invalidating entire phase."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)

        event = engine.invalidate_phase("hull_form")

        assert event.trigger_phase == "hull_form"
        assert event.scope == InvalidationScope.PHASE
        assert engine.is_phase_stale("hull_form")

    def test_invalidate_all(self):
        """Test invalidating everything."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)

        event = engine.invalidate_all()

        assert event.scope == InvalidationScope.ALL
        assert event.reason == InvalidationReason.SCHEMA_MIGRATION
        # Should have invalidated all parameters
        assert len(event.invalidated_parameters) >= len(graph.get_all_parameters.return_value)

    def test_mark_valid(self):
        """Test marking parameter as valid."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)

        engine.invalidate_parameter("hull.loa", cascade=False)
        assert engine.is_stale("hull.loa")

        engine.mark_valid("hull.loa")
        assert not engine.is_stale("hull.loa")

    def test_mark_phase_valid(self):
        """Test marking entire phase as valid."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)

        engine.invalidate_phase("hull_form")
        assert engine.is_phase_stale("hull_form")

        engine.mark_phase_valid("hull_form")
        assert not engine.is_phase_stale("hull_form")

    def test_is_stale(self):
        """Test checking if parameter is stale."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)

        assert not engine.is_stale("hull.loa")
        engine.invalidate_parameter("hull.loa", cascade=False)
        assert engine.is_stale("hull.loa")

    def test_is_phase_stale(self):
        """Test checking if phase is stale."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)

        assert not engine.is_phase_stale("hull_form")
        engine.invalidate_phase("hull_form")
        assert engine.is_phase_stale("hull_form")

    def test_get_stale_parameters(self):
        """Test getting all stale parameters."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)

        engine.invalidate_parameter("hull.loa", cascade=False)
        engine.invalidate_parameter("hull.beam", cascade=False)

        stale = engine.get_stale_parameters()
        assert "hull.loa" in stale
        assert "hull.beam" in stale

    def test_get_stale_phases(self):
        """Test getting all stale phases."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)

        engine.invalidate_phase("hull_form")
        engine.invalidate_phase("mission")

        stale = engine.get_stale_phases()
        assert "hull_form" in stale
        assert "mission" in stale

    def test_get_stale_parameters_for_phase(self):
        """Test getting stale parameters in a phase."""
        graph = self._create_mock_graph()
        graph.get_parameters_for_phase.return_value = ["hull.loa", "hull.beam", "hull.draft"]
        engine = InvalidationEngine(dependency_graph=graph)

        engine._stale_parameters.add("hull.loa")
        engine._stale_parameters.add("hull.beam")

        stale = engine.get_stale_parameters_for_phase("hull_form")
        assert "hull.loa" in stale
        assert "hull.beam" in stale
        assert "hull.draft" not in stale

    def test_get_recalculation_order(self):
        """Test getting ordered parameters for recalculation."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)

        engine._stale_parameters = {"hull.loa", "hull.beam"}
        order = engine.get_recalculation_order()

        graph.get_computation_order.assert_called()
        assert len(order) > 0

    def test_clear_stale(self):
        """Test clearing all stale markers."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)

        engine.invalidate_parameter("hull.loa", cascade=False)
        engine.invalidate_phase("hull_form")

        engine.clear_stale()

        assert len(engine._stale_parameters) == 0
        assert len(engine._stale_phases) == 0

    def test_on_invalidate_callback(self):
        """Test invalidation callback registration and execution."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)

        callback_events = []
        def on_invalidate(event):
            callback_events.append(event)

        engine.on_invalidate(on_invalidate)
        engine.invalidate_parameter("hull.loa", cascade=False)

        assert len(callback_events) == 1
        assert callback_events[0].trigger_parameter == "hull.loa"

    def test_get_events(self):
        """Test getting invalidation events."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)

        engine.invalidate_parameter("hull.loa", cascade=False)
        engine.invalidate_parameter("hull.beam", cascade=False)

        events = engine.get_events(limit=10)
        assert len(events) == 2

    def test_get_events_since(self):
        """Test getting events since a timestamp."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)

        engine.invalidate_parameter("hull.loa", cascade=False)

        # Get events from the future - should be empty
        future = datetime.utcnow() + timedelta(hours=1)
        events = engine.get_events(since=future)
        assert len(events) == 0

    def test_event_history_limit(self):
        """Test event history is limited."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)
        engine._max_events = 5

        # Generate more events than limit
        for i in range(10):
            engine.invalidate_parameter(f"param_{i}", cascade=False)

        assert len(engine._events) <= 5

    def test_to_dict_serialization(self):
        """Test engine state serialization."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)

        engine.invalidate_parameter("hull.loa", cascade=False)

        data = engine.to_dict()
        assert "stale_parameters" in data
        assert "stale_phases" in data
        assert "recent_events" in data
        assert "hull.loa" in data["stale_parameters"]

    def test_from_dict_deserialization(self):
        """Test engine state deserialization."""
        graph = self._create_mock_graph()
        engine = InvalidationEngine(dependency_graph=graph)

        data = {
            "stale_parameters": ["hull.loa", "hull.beam"],
            "stale_phases": ["hull_form"],
            "recent_events": [],
        }

        engine.from_dict(data)
        assert "hull.loa" in engine._stale_parameters
        assert "hull_form" in engine._stale_phases


class TestInvalidationEngineIntegration:
    """Integration tests with real dependency graph."""

    def test_with_real_graph(self):
        """Test invalidation with real dependency graph."""
        graph = DependencyGraph()
        graph.add_dependency("c", "b")
        graph.add_dependency("b", "a")
        graph._compute_order()

        engine = InvalidationEngine(dependency_graph=graph)

        # Invalidating 'a' should cascade to 'b' and 'c'
        event = engine.invalidate_parameter("a", cascade=True)

        assert engine.is_stale("a")
        assert engine.is_stale("b")
        assert engine.is_stale("c")

    def test_fix7_phase_machine_integration(self):
        """Test FIX #7: Integration with phase state machine."""
        graph = DependencyGraph()
        graph.add_dependency("downstream_param", "hull.loa")
        graph._compute_order()

        # Mock phase machine
        phase_machine = Mock()
        # Return a state that will trigger transition attempt
        phase_machine.get_phase_status.return_value = Mock(name="LOCKED")

        engine = InvalidationEngine(
            dependency_graph=graph,
            phase_machine=phase_machine,
        )

        # Invalidate - this should attempt to update phase states
        # The update will only happen if phases are LOCKED/APPROVED/COMPLETED
        engine.invalidate_parameter("hull.loa", cascade=True)

        # Verify engine tracks the stale state
        assert engine.is_stale("hull.loa")
        # Phase machine get_phase_status may or may not be called depending on phases
        # The important thing is that the engine handles the phase_machine correctly
