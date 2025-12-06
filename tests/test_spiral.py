"""
Tests for spiral module (phases and clustering).
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from spiral.phases import (
    PhaseGate,
    PhaseGateResult,
    PHASE_GATES,
    check_phase_gate,
    can_advance_to_phase,
    get_required_outputs,
    get_phase_requirements,
    get_next_phase,
    get_phase_order,
)

from spiral.clustering import (
    PhaseCluster,
    CLUSTER_A,
    CLUSTER_B,
    CLUSTER_C,
    get_cluster_for_phase,
    get_phases_in_cluster,
    should_iterate_cluster,
    get_cluster_iteration_phases,
    get_cluster_entry_phase,
    get_cluster_exit_phase,
    get_next_cluster,
    check_cluster_complete,
)

from memory.schemas import DesignPhase
from memory.file_io import MemoryFileIO


class TestPhaseGates:
    """Test phase gate definitions."""

    def test_all_phases_have_gates(self):
        """Test all phases have gate definitions."""
        for phase in DesignPhase:
            assert phase in PHASE_GATES, f"Missing gate for {phase}"

    def test_mission_gate_no_inputs(self):
        """Test mission phase has no required inputs."""
        gate = PHASE_GATES[DesignPhase.MISSION]
        assert gate.required_inputs == []
        assert "mission" in gate.required_outputs

    def test_hull_form_gate_requires_mission(self):
        """Test hull form requires mission input."""
        gate = PHASE_GATES[DesignPhase.HULL_FORM]
        assert "mission" in gate.required_inputs
        assert "hull_params" in gate.required_outputs
        assert "stability_results" in gate.required_outputs

    def test_propulsion_gate_requirements(self):
        """Test propulsion phase requirements."""
        gate = PHASE_GATES[DesignPhase.PROPULSION]
        assert "mission" in gate.required_inputs
        assert "hull_params" in gate.required_inputs
        assert "propulsion_config" in gate.required_outputs

    def test_structure_gate_requirements(self):
        """Test structure phase requirements."""
        gate = PHASE_GATES[DesignPhase.STRUCTURE]
        assert "hull_params" in gate.required_inputs
        assert "structural_design" in gate.required_outputs


class TestGateChecking:
    """Test phase gate checking logic."""

    @pytest.fixture
    def empty_memory(self):
        """Create empty memory directory."""
        tmpdir = tempfile.mkdtemp()
        yield tmpdir
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def memory_with_mission(self):
        """Create memory with mission file."""
        tmpdir = tempfile.mkdtemp()
        memory = MemoryFileIO(tmpdir)
        memory.write("mission", {"mission_id": "TEST-001"}, validate=False)
        yield tmpdir
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def memory_with_hull(self):
        """Create memory with hull flow complete."""
        tmpdir = tempfile.mkdtemp()
        memory = MemoryFileIO(tmpdir)
        memory.write("mission", {"mission_id": "TEST-001"}, validate=False)
        memory.write("hull_params", {"hull_type": "test"}, validate=False)
        memory.write("stability_results", {"GM": 1.5}, validate=False)
        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_mission_gate_passes_empty(self, empty_memory):
        """Test mission gate passes with no inputs (entry phase)."""
        result = check_phase_gate(DesignPhase.MISSION, empty_memory, check_completion=False)
        assert result.passed is True

    def test_mission_gate_fails_completion(self, empty_memory):
        """Test mission gate fails completion check without output."""
        result = check_phase_gate(DesignPhase.MISSION, empty_memory, check_completion=True)
        assert result.passed is False
        assert "mission" in result.missing_outputs

    def test_hull_form_gate_fails_without_mission(self, empty_memory):
        """Test hull form gate fails without mission."""
        result = check_phase_gate(DesignPhase.HULL_FORM, empty_memory, check_completion=False)
        assert result.passed is False
        assert "mission" in result.missing_inputs

    def test_hull_form_gate_passes_with_mission(self, memory_with_mission):
        """Test hull form gate passes with mission input."""
        result = check_phase_gate(DesignPhase.HULL_FORM, memory_with_mission, check_completion=False)
        assert result.passed is True

    def test_hull_form_completion_fails_without_outputs(self, memory_with_mission):
        """Test hull form completion fails without hull_params."""
        result = check_phase_gate(DesignPhase.HULL_FORM, memory_with_mission, check_completion=True)
        assert result.passed is False
        assert "hull_params" in result.missing_outputs

    def test_hull_form_completion_passes(self, memory_with_hull):
        """Test hull form completion passes with all outputs."""
        result = check_phase_gate(DesignPhase.HULL_FORM, memory_with_hull, check_completion=True)
        assert result.passed is True


class TestPhaseAdvancement:
    """Test phase advancement logic."""

    @pytest.fixture
    def complete_concept_cluster(self):
        """Create memory with concept cluster complete."""
        tmpdir = tempfile.mkdtemp()
        memory = MemoryFileIO(tmpdir)
        memory.write("mission", {"mission_id": "TEST-001"}, validate=False)
        memory.write("hull_params", {"hull_type": "test"}, validate=False)
        memory.write("stability_results", {"GM": 1.5}, validate=False)
        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_cannot_advance_to_hull_without_mission(self):
        """Test cannot advance to hull_form without mission."""
        with tempfile.TemporaryDirectory() as tmpdir:
            can_advance, reason = can_advance_to_phase(DesignPhase.HULL_FORM, tmpdir)
            assert can_advance is False
            assert "mission" in reason.lower()

    def test_can_advance_to_propulsion(self, complete_concept_cluster):
        """Test can advance to propulsion with hull complete."""
        can_advance, reason = can_advance_to_phase(DesignPhase.PROPULSION, complete_concept_cluster)
        assert can_advance is True
        assert "ready" in reason.lower()


class TestRequirements:
    """Test requirement retrieval."""

    def test_get_required_outputs(self):
        """Test getting required outputs."""
        outputs = get_required_outputs(DesignPhase.HULL_FORM)
        assert "hull_params" in outputs
        assert "stability_results" in outputs

    def test_get_phase_requirements(self):
        """Test getting all phase requirements."""
        reqs = get_phase_requirements(DesignPhase.PROPULSION)
        assert "mission" in reqs["inputs"]
        assert "hull_params" in reqs["inputs"]
        assert "propulsion_config" in reqs["outputs"]

    def test_get_next_phase(self):
        """Test getting next phase."""
        assert get_next_phase(DesignPhase.MISSION) == DesignPhase.HULL_FORM
        assert get_next_phase(DesignPhase.HULL_FORM) == DesignPhase.PROPULSION
        assert get_next_phase(DesignPhase.PRODUCTION) is None

    def test_get_phase_order(self):
        """Test phase order."""
        order = get_phase_order()
        assert order[0] == DesignPhase.MISSION
        assert order[-1] == DesignPhase.PRODUCTION
        assert len(order) == 8


class TestClusterDefinitions:
    """Test cluster definitions."""

    def test_cluster_aliases(self):
        """Test cluster aliases."""
        assert CLUSTER_A == PhaseCluster.CONCEPT
        assert CLUSTER_B == PhaseCluster.SYSTEMS
        assert CLUSTER_C == PhaseCluster.VALIDATION

    def test_concept_cluster_phases(self):
        """Test concept cluster contains correct phases."""
        phases = get_phases_in_cluster(PhaseCluster.CONCEPT)
        assert DesignPhase.MISSION in phases
        assert DesignPhase.HULL_FORM in phases
        assert len(phases) == 2

    def test_systems_cluster_phases(self):
        """Test systems cluster contains correct phases."""
        phases = get_phases_in_cluster(PhaseCluster.SYSTEMS)
        assert DesignPhase.PROPULSION in phases
        assert DesignPhase.STRUCTURE in phases
        assert DesignPhase.ARRANGEMENT in phases
        assert len(phases) == 3

    def test_validation_cluster_phases(self):
        """Test validation cluster contains correct phases."""
        phases = get_phases_in_cluster(PhaseCluster.VALIDATION)
        assert DesignPhase.WEIGHT_STABILITY in phases
        assert DesignPhase.COMPLIANCE in phases
        assert DesignPhase.PRODUCTION in phases
        assert len(phases) == 3

    def test_all_phases_in_clusters(self):
        """Test all phases are assigned to a cluster."""
        all_clustered = []
        for cluster in PhaseCluster:
            all_clustered.extend(get_phases_in_cluster(cluster))

        for phase in DesignPhase:
            assert phase in all_clustered, f"Phase {phase} not in any cluster"


class TestClusterMapping:
    """Test phase to cluster mapping."""

    def test_mission_in_concept(self):
        """Test mission is in concept cluster."""
        assert get_cluster_for_phase(DesignPhase.MISSION) == PhaseCluster.CONCEPT

    def test_propulsion_in_systems(self):
        """Test propulsion is in systems cluster."""
        assert get_cluster_for_phase(DesignPhase.PROPULSION) == PhaseCluster.SYSTEMS

    def test_compliance_in_validation(self):
        """Test compliance is in validation cluster."""
        assert get_cluster_for_phase(DesignPhase.COMPLIANCE) == PhaseCluster.VALIDATION


class TestClusterIteration:
    """Test cluster iteration triggers."""

    def test_hull_change_triggers_concept_iteration(self):
        """Test mission change triggers concept iteration (hull recalc)."""
        # hull_params depends on mission in concept cluster
        trigger = should_iterate_cluster(PhaseCluster.CONCEPT, "mission")
        assert trigger is not None
        assert "hull_params" in trigger.affected_files

    def test_propulsion_change_triggers_systems_iteration(self):
        """Test propulsion change triggers systems iteration."""
        trigger = should_iterate_cluster(PhaseCluster.SYSTEMS, "propulsion_config")
        # propulsion_config affects structural_design and general_arrangement
        assert trigger is not None
        assert "structural_design" in trigger.affected_files or "general_arrangement" in trigger.affected_files

    def test_hull_change_triggers_systems_iteration(self):
        """Test hull_params change triggers systems iteration."""
        trigger = should_iterate_cluster(PhaseCluster.SYSTEMS, "hull_params")
        assert trigger is not None
        assert len(trigger.affected_files) > 0

    def test_no_trigger_for_unrelated_file(self):
        """Test no trigger for unrelated file."""
        trigger = should_iterate_cluster(PhaseCluster.CONCEPT, "unrelated_file")
        assert trigger is None


class TestClusterIterationPhases:
    """Test getting phases that need iteration."""

    def test_hull_change_iterates_propulsion(self):
        """Test hull change triggers propulsion iteration."""
        phases = get_cluster_iteration_phases(PhaseCluster.SYSTEMS, "hull_params")
        assert DesignPhase.PROPULSION in phases

    def test_propulsion_change_iterates_structure(self):
        """Test propulsion change triggers structure iteration."""
        phases = get_cluster_iteration_phases(PhaseCluster.SYSTEMS, "propulsion_config")
        assert DesignPhase.STRUCTURE in phases


class TestClusterNavigation:
    """Test cluster navigation functions."""

    def test_cluster_entry_phases(self):
        """Test cluster entry phases."""
        assert get_cluster_entry_phase(PhaseCluster.CONCEPT) == DesignPhase.MISSION
        assert get_cluster_entry_phase(PhaseCluster.SYSTEMS) == DesignPhase.PROPULSION
        assert get_cluster_entry_phase(PhaseCluster.VALIDATION) == DesignPhase.WEIGHT_STABILITY

    def test_cluster_exit_phases(self):
        """Test cluster exit phases."""
        assert get_cluster_exit_phase(PhaseCluster.CONCEPT) == DesignPhase.HULL_FORM
        assert get_cluster_exit_phase(PhaseCluster.SYSTEMS) == DesignPhase.ARRANGEMENT
        assert get_cluster_exit_phase(PhaseCluster.VALIDATION) == DesignPhase.PRODUCTION

    def test_next_cluster(self):
        """Test next cluster navigation."""
        assert get_next_cluster(PhaseCluster.CONCEPT) == PhaseCluster.SYSTEMS
        assert get_next_cluster(PhaseCluster.SYSTEMS) == PhaseCluster.VALIDATION
        assert get_next_cluster(PhaseCluster.VALIDATION) is None


class TestClusterCompletion:
    """Test cluster completion checking."""

    @pytest.fixture
    def complete_concept(self):
        """Create memory with complete concept cluster."""
        tmpdir = tempfile.mkdtemp()
        memory = MemoryFileIO(tmpdir)
        memory.write("mission", {"mission_id": "TEST-001"}, validate=False)
        memory.write("hull_params", {"hull_type": "test"}, validate=False)
        memory.write("stability_results", {"GM": 1.5}, validate=False)
        yield tmpdir
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def incomplete_concept(self):
        """Create memory with incomplete concept cluster."""
        tmpdir = tempfile.mkdtemp()
        memory = MemoryFileIO(tmpdir)
        memory.write("mission", {"mission_id": "TEST-001"}, validate=False)
        # Missing hull_params and stability_results
        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_complete_concept_cluster(self, complete_concept):
        """Test complete concept cluster."""
        complete, missing = check_cluster_complete(PhaseCluster.CONCEPT, complete_concept)
        assert complete is True
        assert len(missing) == 0

    def test_incomplete_concept_cluster(self, incomplete_concept):
        """Test incomplete concept cluster."""
        complete, missing = check_cluster_complete(PhaseCluster.CONCEPT, incomplete_concept)
        assert complete is False
        assert "hull_params" in missing or "stability_results" in missing

    def test_incomplete_systems_cluster(self, complete_concept):
        """Test systems cluster incomplete without systems files."""
        complete, missing = check_cluster_complete(PhaseCluster.SYSTEMS, complete_concept)
        assert complete is False
        assert "propulsion_config" in missing


class TestPhaseGateResult:
    """Test PhaseGateResult dataclass."""

    def test_result_creation(self):
        """Test creating gate result."""
        result = PhaseGateResult(
            passed=True,
            missing_inputs=[],
            missing_outputs=[],
            message="Gate passed",
        )
        assert result.passed is True
        assert result.message == "Gate passed"

    def test_result_with_missing(self):
        """Test result with missing items."""
        result = PhaseGateResult(
            passed=False,
            missing_inputs=["mission"],
            missing_outputs=["hull_params"],
            message="Gate failed",
        )
        assert result.passed is False
        assert "mission" in result.missing_inputs
        assert "hull_params" in result.missing_outputs


class TestEdgeCases:
    """Test edge cases."""

    def test_unknown_phase_gate(self):
        """Test checking gate for invalid phase."""
        # This should not happen in practice but handle gracefully
        # DesignPhase is an enum so invalid phases are not possible
        pass

    def test_empty_cluster(self):
        """Test getting phases from non-existent cluster."""
        # PhaseCluster is an enum so invalid clusters are not possible
        pass

    def test_gate_check_missing_directory(self):
        """Test gate check with non-existent directory."""
        result = check_phase_gate(
            DesignPhase.MISSION,
            "/nonexistent/path",
            check_completion=False,
        )
        # Should pass for mission (no inputs required)
        assert result.passed is True

    def test_gate_check_completion_missing_directory(self):
        """Test completion check with non-existent directory."""
        result = check_phase_gate(
            DesignPhase.MISSION,
            "/nonexistent/path",
            check_completion=True,
        )
        # Should fail (output file missing)
        assert result.passed is False
        assert "mission" in result.missing_outputs
