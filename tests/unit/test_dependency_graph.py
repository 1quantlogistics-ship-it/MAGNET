"""
Unit tests for MAGNET Dependency Graph.

Tests Module 03 v1.1 dependency graph and invalidation engine.
"""

import pytest
from datetime import datetime

from magnet.dependencies import (
    DependencyGraph,
    DependencyNode,
    EdgeType,
    InvalidationEngine,
    InvalidationReason,
    InvalidationScope,
    CascadeExecutor,
    TriggerLog,
    TriggerType,
    get_phase_for_parameter,
    get_parameters_for_phase,
    PHASE_OWNERSHIP,
)


class TestDependencyGraph:
    """Test DependencyGraph class."""

    def test_create_empty_graph(self):
        """Test creating an empty graph."""
        graph = DependencyGraph()
        assert not graph._is_built
        assert len(graph._nodes) == 0

    def test_add_parameter(self):
        """Test adding a parameter."""
        graph = DependencyGraph()
        node = graph.add_parameter("hull.loa", "hull_form")

        assert node.parameter_path == "hull.loa"
        assert node.phase == "hull_form"
        assert graph.has_parameter("hull.loa")

    def test_add_dependency(self):
        """Test adding a dependency between parameters."""
        graph = DependencyGraph()
        edge = graph.add_dependency("hull.displacement_m3", "hull.loa")

        assert graph.has_parameter("hull.displacement_m3")
        assert graph.has_parameter("hull.loa")
        assert "hull.loa" in graph.get_direct_dependencies("hull.displacement_m3")
        assert "hull.displacement_m3" in graph.get_direct_dependents("hull.loa")

    def test_build_from_definitions(self):
        """Test building graph from definitions."""
        graph = DependencyGraph()
        graph.build_from_definitions()

        assert graph._is_built
        assert len(graph._nodes) > 0
        assert graph._build_timestamp is not None

    def test_get_all_downstream(self):
        """Test getting all downstream dependents."""
        graph = DependencyGraph()
        graph.build_from_definitions()

        downstream = graph.get_all_downstream("hull.loa")
        assert len(downstream) > 0
        # Displacement depends on LOA
        assert "hull.displacement_m3" in downstream

    def test_get_computation_order(self):
        """Test getting parameters in computation order."""
        graph = DependencyGraph()
        graph.build_from_definitions()

        order = graph.get_computation_order({"hull.loa", "hull.displacement_m3"})
        # LOA should come before displacement (it's a dependency)
        if "hull.loa" in order and "hull.displacement_m3" in order:
            assert order.index("hull.loa") < order.index("hull.displacement_m3")

    def test_serialization(self):
        """Test graph serialization."""
        graph = DependencyGraph()
        graph.build_from_definitions()

        data = graph.to_dict()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) > 0


class TestPhaseOwnership:
    """Test phase ownership mappings."""

    def test_get_phase_for_parameter(self):
        """Test getting phase for a parameter."""
        assert get_phase_for_parameter("hull.loa") == "hull_form"
        assert get_phase_for_parameter("mission.max_speed_kts") == "mission"
        assert get_phase_for_parameter("stability.gm_transverse_m") == "stability"

    def test_get_parameters_for_phase(self):
        """Test getting parameters for a phase."""
        hull_params = get_parameters_for_phase("hull_form")
        assert "hull.loa" in hull_params
        assert "hull.beam" in hull_params

    def test_phase_ownership_complete(self):
        """Test all phases have parameters defined."""
        expected_phases = [
            "mission", "hull_form", "structure", "arrangement",
            "propulsion", "weight", "stability", "compliance", "production"
        ]
        for phase in expected_phases:
            assert phase in PHASE_OWNERSHIP
            assert len(PHASE_OWNERSHIP[phase]) > 0


class TestInvalidationEngine:
    """Test InvalidationEngine class."""

    def test_create_engine(self):
        """Test creating an invalidation engine."""
        graph = DependencyGraph()
        graph.build_from_definitions()
        engine = InvalidationEngine(graph)

        assert len(engine.get_stale_parameters()) == 0
        assert len(engine.get_stale_phases()) == 0

    def test_invalidate_parameter(self):
        """Test invalidating a single parameter."""
        graph = DependencyGraph()
        graph.build_from_definitions()
        engine = InvalidationEngine(graph)

        event = engine.invalidate_parameter("hull.loa")

        assert engine.is_stale("hull.loa")
        assert len(event.invalidated_parameters) > 0
        assert event.trigger_parameter == "hull.loa"
        assert event.reason == InvalidationReason.PARAMETER_CHANGED

    def test_cascade_invalidation(self):
        """Test cascade invalidation to downstream parameters."""
        graph = DependencyGraph()
        graph.build_from_definitions()
        engine = InvalidationEngine(graph)

        event = engine.invalidate_parameter("hull.loa", cascade=True)

        # Downstream parameters should be stale
        if "hull.displacement_m3" in graph.get_all_downstream("hull.loa"):
            assert engine.is_stale("hull.displacement_m3")

    def test_invalidate_phase(self):
        """Test invalidating an entire phase."""
        graph = DependencyGraph()
        graph.build_from_definitions()
        engine = InvalidationEngine(graph)

        event = engine.invalidate_phase("hull_form")

        assert engine.is_phase_stale("hull_form")
        assert len(event.invalidated_parameters) > 0

    def test_mark_valid(self):
        """Test marking a parameter as valid."""
        graph = DependencyGraph()
        graph.build_from_definitions()
        engine = InvalidationEngine(graph)

        engine.invalidate_parameter("hull.loa", cascade=False)
        assert engine.is_stale("hull.loa")

        engine.mark_valid("hull.loa")
        assert not engine.is_stale("hull.loa")


class TestTriggerLog:
    """Test TriggerLog class."""

    def test_create_log(self):
        """Test creating a trigger log."""
        log = TriggerLog()
        assert len(log) == 0

    def test_log_value_set(self):
        """Test logging a value set."""
        log = TriggerLog()
        entry_id = log.log_value_set(
            parameter="hull.loa",
            old_value=20.0,
            new_value=25.0,
            source="test"
        )

        assert len(log) == 1
        entries = log.get_for_parameter("hull.loa")
        assert len(entries) == 1
        assert entries[0].new_value == 25.0

    def test_log_invalidation(self):
        """Test logging an invalidation."""
        log = TriggerLog()
        entry_id = log.log_invalidation(
            parameter="hull.displacement_m3",
            source="InvalidationEngine",
        )

        entries = log.query(trigger_types={TriggerType.INVALIDATION})
        assert len(entries) == 1

    def test_query_by_time(self):
        """Test querying by time range."""
        log = TriggerLog()
        before = datetime.utcnow()

        log.log_value_set("hull.loa", 20.0, 25.0)

        after = datetime.utcnow()

        entries = log.query(since=before, until=after)
        assert len(entries) == 1

    def test_query_by_phase(self):
        """Test querying by phase."""
        log = TriggerLog()
        log.log_phase_transition("hull_form", "DRAFT", "ACTIVE")

        entries = log.get_for_phase("hull_form")
        assert len(entries) == 1


class TestCascadeExecutor:
    """Test CascadeExecutor class."""

    def test_get_recalculation_order_empty(self):
        """Test getting recalculation order with no stale params."""
        from magnet.core.state_manager import StateManager

        graph = DependencyGraph()
        graph.build_from_definitions()
        engine = InvalidationEngine(graph)
        manager = StateManager()

        executor = CascadeExecutor(graph, engine, manager)
        order = executor.get_recalculation_order()

        # No stale parameters, so empty order
        assert len(order.parameters) == 0
