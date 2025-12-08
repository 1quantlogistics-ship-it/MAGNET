"""
Unit tests for dependencies/graph.py

Tests the DependencyGraph, parameter dependencies, and phase ownership.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from magnet.dependencies.graph import (
    DependencyGraph,
    DependencyNode,
    DependencyEdge,
    DependencyGraphError,
    CyclicDependencyError,
    EdgeType,
    PHASE_OWNERSHIP,
    PARAMETER_TO_PHASE,
    PARAMETER_DEPENDENCIES,
    PHASE_DEPENDENCIES,
    DOWNSTREAM_PHASES,
    get_phase_for_parameter,
    get_parameters_for_phase,
    get_default_graph,
)


class TestEdgeType:
    """Test EdgeType enum."""

    def test_edge_type_values(self):
        """Test edge type enum values."""
        assert EdgeType.DATA_FLOW.value == "data_flow"
        assert EdgeType.SEMANTIC.value == "semantic"
        assert EdgeType.VALIDATION.value == "validation"
        assert EdgeType.DERIVED.value == "derived"

    def test_edge_type_members(self):
        """Test all expected edge types exist."""
        types = [e for e in EdgeType]
        assert len(types) == 4


class TestPhaseOwnership:
    """Test PHASE_OWNERSHIP and related mappings."""

    def test_phase_ownership_has_required_phases(self):
        """Test that all required phases exist."""
        required_phases = [
            "mission", "hull_form", "structure", "arrangement",
            "propulsion", "weight", "stability", "compliance", "production"
        ]
        for phase in required_phases:
            assert phase in PHASE_OWNERSHIP, f"Missing phase: {phase}"

    def test_parameter_to_phase_mapping(self):
        """Test reverse mapping is consistent."""
        for phase, params in PHASE_OWNERSHIP.items():
            for param in params:
                assert param in PARAMETER_TO_PHASE
                assert PARAMETER_TO_PHASE[param] == phase

    def test_get_phase_for_parameter_exact(self):
        """Test exact parameter lookup."""
        assert get_phase_for_parameter("hull.loa") == "hull_form"
        assert get_phase_for_parameter("mission.vessel_type") == "mission"
        assert get_phase_for_parameter("weight.lightship_weight_mt") == "weight"

    def test_get_phase_for_parameter_prefix(self):
        """Test prefix-based parameter lookup."""
        # Unknown parameter but known prefix
        assert get_phase_for_parameter("hull.unknown_field") == "hull_form"
        assert get_phase_for_parameter("propulsion.custom_field") == "propulsion"
        assert get_phase_for_parameter("stability.new_param") == "stability"

    def test_get_phase_for_parameter_unknown(self):
        """Test unknown parameter returns None."""
        result = get_phase_for_parameter("totally_unknown")
        assert result is None

    def test_get_parameters_for_phase(self):
        """Test getting parameters for a phase."""
        hull_params = get_parameters_for_phase("hull_form")
        assert len(hull_params) > 0
        assert "hull.loa" in hull_params
        assert "hull.beam" in hull_params

    def test_get_parameters_for_unknown_phase(self):
        """Test getting parameters for unknown phase returns empty."""
        params = get_parameters_for_phase("not_a_phase")
        assert params == []


class TestPhaseDependencies:
    """Test phase-level dependencies."""

    def test_phase_dependencies_structure(self):
        """Test PHASE_DEPENDENCIES is properly structured."""
        # Mission has no dependencies
        assert PHASE_DEPENDENCIES["mission"] == []

        # Hull depends on mission
        assert "mission" in PHASE_DEPENDENCIES["hull_form"]

        # Production depends on compliance
        assert "compliance" in PHASE_DEPENDENCIES["production"]

    def test_downstream_phases_structure(self):
        """Test DOWNSTREAM_PHASES is properly structured."""
        # Mission affects everything downstream
        mission_downstream = DOWNSTREAM_PHASES["mission"]
        assert "hull_form" in mission_downstream
        assert "production" in mission_downstream

        # Production has no downstream
        assert DOWNSTREAM_PHASES["production"] == []


class TestParameterDependencies:
    """Test parameter-level dependencies."""

    def test_parameter_dependencies_exist(self):
        """Test PARAMETER_DEPENDENCIES has expected entries."""
        assert "hull.displacement_m3" in PARAMETER_DEPENDENCIES
        assert "resistance.total_resistance_kn" in PARAMETER_DEPENDENCIES
        assert "stability.gm_transverse_m" in PARAMETER_DEPENDENCIES

    def test_displacement_dependencies(self):
        """Test hull displacement depends on correct parameters."""
        deps = PARAMETER_DEPENDENCIES["hull.displacement_m3"]
        assert "hull.loa" in deps
        assert "hull.beam" in deps
        assert "hull.draft" in deps
        assert "hull.cb" in deps


class TestDependencyNode:
    """Test DependencyNode dataclass."""

    def test_create_node(self):
        """Test creating a dependency node."""
        node = DependencyNode(
            parameter_path="hull.loa",
            phase="hull_form",
        )
        assert node.parameter_path == "hull.loa"
        assert node.phase == "hull_form"
        assert len(node.depends_on) == 0
        assert len(node.depended_by) == 0

    def test_node_hashable(self):
        """Test nodes can be used in sets."""
        node1 = DependencyNode(parameter_path="hull.loa", phase="hull_form")
        node2 = DependencyNode(parameter_path="hull.beam", phase="hull_form")

        nodes = {node1, node2}
        assert len(nodes) == 2


class TestDependencyEdge:
    """Test DependencyEdge dataclass."""

    def test_create_edge(self):
        """Test creating a dependency edge."""
        edge = DependencyEdge(
            source="hull.loa",
            target="hull.displacement_m3",
        )
        assert edge.source == "hull.loa"
        assert edge.target == "hull.displacement_m3"
        assert edge.edge_type == EdgeType.DATA_FLOW
        assert edge.weight == 1.0

    def test_edge_with_type(self):
        """Test creating edge with specific type."""
        edge = DependencyEdge(
            source="hull.loa",
            target="vision.geometry_generated",
            edge_type=EdgeType.SEMANTIC,
        )
        assert edge.edge_type == EdgeType.SEMANTIC

    def test_edge_hashable(self):
        """Test edges can be used in sets."""
        edge1 = DependencyEdge(source="a", target="b")
        edge2 = DependencyEdge(source="a", target="c")

        edges = {edge1, edge2}
        assert len(edges) == 2


class TestDependencyGraph:
    """Test DependencyGraph class."""

    def test_create_graph(self):
        """Test creating empty graph."""
        graph = DependencyGraph()
        assert graph._is_built == False
        assert len(graph._nodes) == 0

    def test_add_parameter(self):
        """Test adding parameter to graph."""
        graph = DependencyGraph()
        node = graph.add_parameter("hull.loa", "hull_form")

        assert node.parameter_path == "hull.loa"
        assert node.phase == "hull_form"
        assert graph.has_parameter("hull.loa")

    def test_add_parameter_auto_phase(self):
        """Test adding parameter with auto-detected phase."""
        graph = DependencyGraph()
        node = graph.add_parameter("mission.vessel_type")

        assert node.phase == "mission"

    def test_add_parameter_duplicate(self):
        """Test adding duplicate parameter returns existing."""
        graph = DependencyGraph()
        node1 = graph.add_parameter("hull.loa", "hull_form")
        node2 = graph.add_parameter("hull.loa", "hull_form")

        assert node1 is node2

    def test_add_dependency(self):
        """Test adding dependency between parameters."""
        graph = DependencyGraph()
        edge = graph.add_dependency("hull.displacement_m3", "hull.loa")

        assert graph.has_parameter("hull.displacement_m3")
        assert graph.has_parameter("hull.loa")
        assert "hull.loa" in graph.get_direct_dependencies("hull.displacement_m3")
        assert "hull.displacement_m3" in graph.get_direct_dependents("hull.loa")

    def test_add_dependency_with_type(self):
        """Test adding dependency with edge type."""
        graph = DependencyGraph()
        edge = graph.add_dependency(
            "hull.displacement_m3",
            "hull.loa",
            edge_type=EdgeType.DATA_FLOW
        )

        assert edge.edge_type == EdgeType.DATA_FLOW

    def test_build_from_definitions(self):
        """Test building graph from predefined definitions."""
        graph = DependencyGraph()
        graph.build_from_definitions()

        assert graph._is_built == True
        assert graph._build_timestamp is not None
        assert len(graph._nodes) > 0
        assert len(graph._edges) > 0

    def test_get_direct_dependencies(self):
        """Test getting direct dependencies."""
        graph = DependencyGraph()
        graph.add_dependency("c", "b")
        graph.add_dependency("b", "a")

        deps = graph.get_direct_dependencies("c")
        assert "b" in deps
        assert "a" not in deps  # Not direct

    def test_get_direct_dependents(self):
        """Test getting direct dependents."""
        graph = DependencyGraph()
        graph.add_dependency("c", "b")
        graph.add_dependency("b", "a")

        deps = graph.get_direct_dependents("a")
        assert "b" in deps
        assert "c" not in deps  # Not direct

    def test_get_all_dependencies(self):
        """Test getting transitive dependencies."""
        graph = DependencyGraph()
        graph.add_dependency("c", "b")
        graph.add_dependency("b", "a")

        all_deps = graph.get_all_dependencies("c")
        assert "a" in all_deps
        assert "b" in all_deps

    def test_get_all_downstream(self):
        """Test getting all downstream dependents."""
        graph = DependencyGraph()
        graph.add_dependency("c", "b")
        graph.add_dependency("b", "a")

        downstream = graph.get_all_downstream("a")
        assert "b" in downstream
        assert "c" in downstream

    def test_get_downstream_phases(self):
        """Test getting downstream phases."""
        graph = DependencyGraph()
        graph.build_from_definitions()

        phases = graph.get_downstream_phases("hull.loa")
        # hull.loa changes should affect many phases
        assert len(phases) > 0

    def test_computation_order(self):
        """Test parameters ordered for computation."""
        graph = DependencyGraph()
        graph.add_dependency("c", "b")
        graph.add_dependency("b", "a")
        graph.build_from_definitions()  # This computes order

        # Create simple graph to test order
        graph2 = DependencyGraph()
        graph2.add_dependency("c", "b")
        graph2.add_dependency("b", "a")
        graph2._compute_order()

        order = graph2.get_computation_order({"a", "b", "c"})
        a_idx = order.index("a")
        b_idx = order.index("b")
        c_idx = order.index("c")

        assert a_idx < b_idx < c_idx

    def test_recalculation_order(self):
        """Test getting recalculation order after changes."""
        graph = DependencyGraph()
        graph.add_dependency("c", "b")
        graph.add_dependency("b", "a")
        graph._compute_order()

        order = graph.get_recalculation_order({"a"})
        # Changing 'a' should require recalculating b and c
        assert "b" in order
        assert "c" in order

    def test_get_parameters_for_phase(self):
        """Test getting parameters for a phase."""
        graph = DependencyGraph()
        graph.build_from_definitions()

        hull_params = graph.get_parameters_for_phase("hull_form")
        assert len(hull_params) > 0

    def test_to_dict_serialization(self):
        """Test graph serialization."""
        graph = DependencyGraph()
        graph.add_dependency("b", "a")
        graph._compute_order()
        graph._is_built = True
        graph._build_timestamp = datetime.utcnow()

        data = graph.to_dict()
        assert "nodes" in data
        assert "edges" in data
        assert "a" in data["nodes"]
        assert "b" in data["nodes"]

    def test_from_dict_deserialization(self):
        """Test graph deserialization."""
        data = {
            "nodes": {
                "a": {"phase": "test", "depends_on": [], "depended_by": ["b"]},
                "b": {"phase": "test", "depends_on": ["a"], "depended_by": []},
            },
            "edges": [
                {"source": "a", "target": "b", "edge_type": "data_flow", "weight": 1.0}
            ],
            "build_timestamp": "2024-01-01T12:00:00",
        }

        graph = DependencyGraph.from_dict(data)
        assert graph.has_parameter("a")
        assert graph.has_parameter("b")
        assert graph._is_built == True


class TestCycleDetection:
    """Test cycle detection in dependency graph."""

    def test_no_cycle(self):
        """Test graph without cycles builds successfully."""
        graph = DependencyGraph()
        graph.add_dependency("c", "b")
        graph.add_dependency("b", "a")

        cycles = graph._detect_cycles()
        assert len(cycles) == 0

    def test_detect_simple_cycle(self):
        """Test detection of simple cycle."""
        graph = DependencyGraph()
        graph.add_dependency("b", "a")
        graph.add_dependency("a", "b")  # Creates cycle

        cycles = graph._detect_cycles()
        assert len(cycles) > 0

    def test_detect_complex_cycle(self):
        """Test detection of longer cycle."""
        graph = DependencyGraph()
        graph.add_dependency("b", "a")
        graph.add_dependency("c", "b")
        graph.add_dependency("a", "c")  # Creates A -> B -> C -> A

        cycles = graph._detect_cycles()
        assert len(cycles) > 0

    def test_build_raises_on_cycle(self):
        """Test build raises error when cycle detected."""
        graph = DependencyGraph()
        graph.add_dependency("b", "a")
        graph.add_dependency("a", "b")

        with pytest.raises(CyclicDependencyError):
            graph.build_from_definitions()


class TestDefaultGraph:
    """Test default graph singleton."""

    def test_get_default_graph(self):
        """Test getting default graph."""
        graph = get_default_graph()
        assert graph._is_built == True
        assert len(graph._nodes) > 0

    def test_default_graph_singleton(self):
        """Test default graph returns same instance."""
        graph1 = get_default_graph()
        graph2 = get_default_graph()
        assert graph1 is graph2
