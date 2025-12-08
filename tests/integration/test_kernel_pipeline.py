"""
tests/integration/test_kernel_pipeline.py - Integration tests for kernel pipeline.

BRAVO OWNS THIS FILE.

Tests for Module 15 v1.1 - Full kernel pipeline integration.
"""

import pytest
from unittest.mock import Mock
from magnet.kernel import (
    Conductor,
    PhaseRegistry,
    ValidationOrchestrator,
    DesignSession,
    KernelValidator,
    PhaseStatus,
    GateCondition,
    SessionStatus,
)
from magnet.kernel.registry import PhaseDefinition, PhaseType, PHASE_DEFINITIONS
from magnet.validators.taxonomy import ValidatorState


class MockStateManager:
    """Mock state manager for integration testing."""

    def __init__(self):
        self._data = {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def write(self, key, value, agent, description):
        self._data[key] = value

    def set(self, key, value):
        self._data[key] = value


class MockPassingValidator:
    """Mock validator that always passes."""

    def validate(self, state, context):
        result = Mock()
        result.state = Mock()
        result.state.value = "passed"
        result.error_message = None
        return result


class MockFailingValidator:
    """Mock validator that always fails."""

    def validate(self, state, context):
        result = Mock()
        result.state = Mock()
        result.state.value = "failed"
        result.error_message = "Validation failed"
        return result


class TestPhaseDefinitionsIntegrity:
    """Test standard phase definitions integrity."""

    def test_all_phases_have_required_fields(self):
        """Test all phases have required fields."""
        for name, phase in PHASE_DEFINITIONS.items():
            assert phase.name == name
            assert phase.description
            assert phase.phase_type is not None
            assert phase.order > 0

    def test_dependency_chain_is_valid(self):
        """Test dependency chain forms valid DAG."""
        registry = PhaseRegistry()

        for name, phase in PHASE_DEFINITIONS.items():
            for dep in phase.depends_on:
                dep_phase = registry.get_phase(dep)
                assert dep_phase is not None, f"{name} depends on non-existent {dep}"
                assert dep_phase.order < phase.order, \
                    f"{name} (order {phase.order}) depends on {dep} (order {dep_phase.order})"

    def test_mission_has_no_dependencies(self):
        """Test mission phase has no dependencies."""
        mission = PHASE_DEFINITIONS["mission"]
        assert mission.depends_on == []
        assert mission.order == 1

    def test_compliance_is_gate(self):
        """Test compliance phase is properly configured as gate."""
        compliance = PHASE_DEFINITIONS["compliance"]
        assert compliance.is_gate == True
        assert compliance.gate_condition == GateCondition.CRITICAL_PASS


class TestConductorPipeline:
    """Test conductor phase pipeline."""

    def test_run_mission_phase(self):
        """Test running first phase (mission)."""
        state = MockStateManager()
        conductor = Conductor(state)
        conductor.create_session("design-001")

        # Register passing validator
        conductor.register_validator("mission/requirements", MockPassingValidator())

        result = conductor.run_phase("mission")

        assert result.status == PhaseStatus.COMPLETED
        assert result.validators_passed >= 1

    def test_run_dependent_phases_in_order(self):
        """Test running phases respects dependencies."""
        state = MockStateManager()
        conductor = Conductor(state)
        conductor.create_session("design-001")

        # Register validators for mission and hull
        conductor.register_validator("mission/requirements", MockPassingValidator())
        conductor.register_validator("hull/form", MockPassingValidator())
        conductor.register_validator("physics/hydrostatics", MockPassingValidator())

        # Run mission first
        mission_result = conductor.run_phase("mission")
        assert mission_result.status == PhaseStatus.COMPLETED

        # Now hull should work
        hull_result = conductor.run_phase("hull")
        assert hull_result.status == PhaseStatus.COMPLETED

    def test_phase_blocked_without_dependency(self):
        """Test phase is blocked if dependency not run."""
        state = MockStateManager()
        conductor = Conductor(state)
        conductor.create_session("design-001")

        # Try to run hull without mission
        result = conductor.run_phase("hull")

        assert result.status == PhaseStatus.BLOCKED

    def test_session_tracks_completed_phases(self):
        """Test session tracks completed phases."""
        state = MockStateManager()
        conductor = Conductor(state)
        conductor.create_session("design-001")
        conductor.register_validator("mission/requirements", MockPassingValidator())

        conductor.run_phase("mission")

        session = conductor.get_session()
        assert "mission" in session.completed_phases


class TestOrchestratorIntegration:
    """Test orchestrator integration."""

    def test_orchestrator_runs_pipeline(self):
        """Test orchestrator can run full pipeline."""
        state = MockStateManager()

        # ValidationOrchestrator creates its own registry
        orchestrator = ValidationOrchestrator(state)

        # Register all validators as passing
        for phase in orchestrator.registry.get_phases_in_order():
            for vid in phase.validators:
                orchestrator.register_validator(vid, MockPassingValidator())

        # Set compliance.fail_count to 0 for gate
        state._data["compliance.fail_count"] = 0

        summary = orchestrator.run_full_pipeline("design-001")

        # Returns summary dict, not list of results
        assert isinstance(summary, dict)
        assert summary["phases_completed"] == len(orchestrator.registry.get_phases_in_order())

    def test_orchestrator_stops_on_gate_failure(self):
        """Test orchestrator stops when gate fails."""
        state = MockStateManager()

        orchestrator = ValidationOrchestrator(state)

        # Register all validators as passing
        for phase in orchestrator.registry.get_phases_in_order():
            for vid in phase.validators:
                orchestrator.register_validator(vid, MockPassingValidator())

        # Set compliance.fail_count > 0 to fail gate
        state._data["compliance.fail_count"] = 5

        summary = orchestrator.run_full_pipeline("design-001")

        # Returns summary dict
        assert isinstance(summary, dict)
        # Compliance should have failed
        assert summary["phase_results"]["compliance"] == "failed"


class TestSessionPersistence:
    """Test session state persistence."""

    def test_session_written_to_state(self):
        """Test session is written to state."""
        state = MockStateManager()
        session_mgr = DesignSession(state)

        session = session_mgr.create("design-001")

        assert f"sessions.{session.session_id}" in state._data
        assert state._data["kernel.current_session"] == session.session_id

    def test_session_can_be_loaded(self):
        """Test session can be loaded from state."""
        state = MockStateManager()
        session_mgr = DesignSession(state)
        original = session_mgr.create("design-001")

        # Create new manager and load
        new_mgr = DesignSession(state)
        loaded = new_mgr.load(original.session_id)

        assert loaded.session_id == original.session_id
        assert loaded.design_id == original.design_id

    def test_conductor_writes_state(self):
        """Test conductor writes state properly."""
        state = MockStateManager()
        conductor = Conductor(state)
        conductor.create_session("design-001")
        conductor.register_validator("mission/requirements", MockPassingValidator())
        conductor.run_phase("mission")

        conductor.write_to_state()

        assert "kernel.session" in state._data
        assert "kernel.status" in state._data
        assert state._data["kernel.status"] == "active"


class TestKernelValidatorIntegration:
    """Test kernel validator integration."""

    def test_validator_passes_completed_pipeline(self):
        """Test validator passes with completed pipeline."""
        state = MockStateManager()
        state._data["kernel.status"] = "completed"
        state._data["kernel.phase_history"] = list(PHASE_DEFINITIONS.keys())
        state._data["kernel.gate_status"] = {"compliance_gate": True}

        validator = KernelValidator()
        result = validator.validate(state, {})

        assert result.state == ValidatorState.PASSED
        assert state._data["kernel.validation_complete"] == True

    def test_validator_warns_incomplete_pipeline(self):
        """Test validator warns with incomplete pipeline."""
        state = MockStateManager()
        state._data["kernel.status"] = "active"
        state._data["kernel.phase_history"] = ["mission", "hull"]
        state._data["kernel.gate_status"] = {}

        validator = KernelValidator()
        result = validator.validate(state, {})

        # Warns about missing critical phases and incomplete pipeline
        assert result.state == ValidatorState.WARNING
        assert result.warning_count > 0


class TestFullPipelineRun:
    """Test complete pipeline execution."""

    def test_full_pipeline_with_all_validators(self):
        """Test running complete pipeline with all validators."""
        state = MockStateManager()
        state._data["compliance.fail_count"] = 0

        conductor = Conductor(state)
        conductor.create_session("integration-test")

        # Register passing validators for all phases
        for phase in conductor.registry.get_phases_in_order():
            for vid in phase.validators:
                conductor.register_validator(vid, MockPassingValidator())

        # Run all phases
        results = conductor.run_all_phases(stop_on_failure=False)

        # Verify all completed
        completed = [r for r in results if r.status == PhaseStatus.COMPLETED]
        assert len(completed) == len(PHASE_DEFINITIONS)

        # Verify session status
        session = conductor.get_session()
        assert session.status == SessionStatus.COMPLETED
        assert len(session.completed_phases) == len(PHASE_DEFINITIONS)

    def test_pipeline_state_written(self):
        """Test pipeline writes all necessary state."""
        state = MockStateManager()
        state._data["compliance.fail_count"] = 0

        conductor = Conductor(state)
        conductor.create_session("state-test")

        for phase in conductor.registry.get_phases_in_order():
            for vid in phase.validators:
                conductor.register_validator(vid, MockPassingValidator())

        conductor.run_all_phases()
        conductor.write_to_state()

        # Verify state
        assert "kernel.session" in state._data
        assert "kernel.status" in state._data
        assert "kernel.phase_history" in state._data
        assert "kernel.gate_status" in state._data

    def test_run_to_specific_phase(self):
        """Test running up to a specific phase."""
        state = MockStateManager()
        conductor = Conductor(state)
        conductor.create_session("partial-test")

        for phase in conductor.registry.get_phases_in_order():
            for vid in phase.validators:
                conductor.register_validator(vid, MockPassingValidator())

        # Run up to weight phase
        results = conductor.run_to_phase("weight")

        phase_names = [r.phase_name for r in results]
        assert "mission" in phase_names
        assert "hull" in phase_names
        assert "weight" in phase_names
        # Phases after weight should not be run
        assert "stability" not in phase_names
        assert "compliance" not in phase_names

    def test_run_from_specific_phase(self):
        """Test running from a specific phase."""
        state = MockStateManager()
        state._data["compliance.fail_count"] = 0
        conductor = Conductor(state)
        conductor.create_session("partial-test")

        # First complete prerequisites
        for phase in conductor.registry.get_phases_in_order():
            for vid in phase.validators:
                conductor.register_validator(vid, MockPassingValidator())

        # Run to stability first
        conductor.run_to_phase("stability")

        # Now run from loading
        results = conductor.run_from_phase("loading")

        phase_names = [r.phase_name for r in results]
        assert "loading" in phase_names
        assert "mission" not in phase_names  # Already completed

