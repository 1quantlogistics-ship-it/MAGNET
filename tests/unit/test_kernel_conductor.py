"""
tests/unit/test_kernel_conductor.py - Tests for kernel conductor.

BRAVO OWNS THIS FILE.

Tests for Module 15 v1.1 - Conductor phase orchestration.
"""

import pytest
from unittest.mock import Mock, MagicMock
from magnet.kernel import (
    Conductor,
    PhaseRegistry,
    PhaseStatus,
    GateCondition,
    SessionStatus,
)
from magnet.kernel.registry import PhaseDefinition, PhaseType


class MockStateManager:
    """Mock state manager for testing."""

    def __init__(self):
        self._data = {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def write(self, key, value, agent, description):
        self._data[key] = value

    def set(self, key, value, source=None):
        self._data[key] = value


class TestConductorCreation:
    """Tests for Conductor initialization."""

    def test_create_conductor(self):
        """Test basic conductor creation."""
        state = MockStateManager()
        conductor = Conductor(state)

        assert conductor.state == state
        assert conductor.registry is not None
        assert conductor._session is None

    def test_create_with_custom_registry(self):
        """Test conductor with custom registry."""
        state = MockStateManager()
        registry = PhaseRegistry()
        conductor = Conductor(state, registry=registry)

        assert conductor.registry is registry


class TestConductorSession:
    """Tests for session management."""

    def test_create_session(self):
        """Test creating a new session."""
        state = MockStateManager()
        conductor = Conductor(state)

        session = conductor.create_session("design-001")

        assert session is not None
        assert session.design_id == "design-001"
        assert session.status == SessionStatus.ACTIVE
        assert session.session_id is not None

    def test_get_session(self):
        """Test getting current session."""
        state = MockStateManager()
        conductor = Conductor(state)

        assert conductor.get_session() is None

        conductor.create_session("design-001")
        session = conductor.get_session()

        assert session is not None
        assert session.design_id == "design-001"


class TestConductorValidators:
    """Tests for validator registration."""

    def test_register_validator(self):
        """Test registering a validator."""
        state = MockStateManager()
        conductor = Conductor(state)

        mock_validator = Mock()
        conductor.register_validator("test/validator", mock_validator)

        assert "test/validator" in conductor._validators
        assert conductor._validators["test/validator"] == mock_validator


class TestRunPhase:
    """Tests for running individual phases."""

    def test_run_unknown_phase(self):
        """Test running unknown phase fails."""
        state = MockStateManager()
        conductor = Conductor(state)

        result = conductor.run_phase("nonexistent")

        assert result.status == PhaseStatus.FAILED
        assert "Unknown phase" in result.errors[0]

    def test_run_phase_blocked_by_dependency(self):
        """Test phase blocked by unmet dependency."""
        state = MockStateManager()
        conductor = Conductor(state)
        conductor.create_session("design-001")

        # Hull depends on mission, try to run hull first
        result = conductor.run_phase("hull")

        assert result.status == PhaseStatus.BLOCKED
        assert "Dependency not completed" in result.errors[0]

    def test_run_phase_no_validators(self):
        """Test running phase with no registered validators."""
        state = MockStateManager()
        registry = PhaseRegistry()

        # Add a simple test phase with no dependencies
        test_phase = PhaseDefinition(
            name="test_phase",
            description="Test phase",
            phase_type=PhaseType.DEFINITION,
            order=0,
            validators=["test/validator"],
        )
        registry.register_phase(test_phase)

        conductor = Conductor(state, registry=registry)
        conductor.create_session("design-001")

        result = conductor.run_phase("test_phase")

        # Should complete with warning about missing validator
        assert result.status == PhaseStatus.COMPLETED
        assert len(result.warnings) > 0
        assert "not registered" in result.warnings[0]

    def test_run_phase_with_validator(self):
        """Test running phase with registered validator."""
        state = MockStateManager()
        registry = PhaseRegistry()

        test_phase = PhaseDefinition(
            name="test_phase",
            description="Test phase",
            phase_type=PhaseType.DEFINITION,
            order=0,
            validators=["test/validator"],
        )
        registry.register_phase(test_phase)

        conductor = Conductor(state, registry=registry)
        conductor.create_session("design-001")

        # Create mock validator
        mock_result = Mock()
        mock_result.state.value = "passed"
        mock_validator = Mock()
        mock_validator.validate.return_value = mock_result

        conductor.register_validator("test/validator", mock_validator)

        result = conductor.run_phase("test_phase")

        assert result.status == PhaseStatus.COMPLETED
        assert result.validators_run == 1
        assert result.validators_passed == 1

    def test_run_phase_validator_fails(self):
        """Test phase fails when validator fails."""
        state = MockStateManager()
        registry = PhaseRegistry()

        test_phase = PhaseDefinition(
            name="test_phase",
            description="Test phase",
            phase_type=PhaseType.DEFINITION,
            order=0,
            validators=["test/validator"],
        )
        registry.register_phase(test_phase)

        conductor = Conductor(state, registry=registry)
        conductor.create_session("design-001")

        # Create failing mock validator
        mock_result = Mock()
        mock_result.state.value = "failed"
        mock_result.error_message = "Validation failed"
        mock_validator = Mock()
        mock_validator.validate.return_value = mock_result

        conductor.register_validator("test/validator", mock_validator)

        result = conductor.run_phase("test_phase")

        assert result.status == PhaseStatus.FAILED
        assert result.validators_failed == 1

    def test_run_phase_validator_exception(self):
        """Test phase handles validator exception."""
        state = MockStateManager()
        registry = PhaseRegistry()

        test_phase = PhaseDefinition(
            name="test_phase",
            description="Test phase",
            phase_type=PhaseType.DEFINITION,
            order=0,
            validators=["test/validator"],
        )
        registry.register_phase(test_phase)

        conductor = Conductor(state, registry=registry)
        conductor.create_session("design-001")

        # Create validator that raises exception
        mock_validator = Mock()
        mock_validator.validate.side_effect = Exception("Test error")

        conductor.register_validator("test/validator", mock_validator)

        result = conductor.run_phase("test_phase")

        assert result.status == PhaseStatus.FAILED
        assert result.validators_failed == 1
        assert "Test error" in result.errors[0]


class TestGateEvaluation:
    """Tests for gate evaluation."""

    def test_gate_all_pass_succeeds(self):
        """Test ALL_PASS gate with all validators passing."""
        state = MockStateManager()
        registry = PhaseRegistry()

        gate_phase = PhaseDefinition(
            name="gate_phase",
            description="Gate phase",
            phase_type=PhaseType.VERIFICATION,
            order=0,
            is_gate=True,
            gate_condition=GateCondition.ALL_PASS,
            validators=["test/validator"],
        )
        registry.register_phase(gate_phase)

        conductor = Conductor(state, registry=registry)
        conductor.create_session("design-001")

        mock_result = Mock()
        mock_result.state.value = "passed"
        mock_validator = Mock()
        mock_validator.validate.return_value = mock_result
        conductor.register_validator("test/validator", mock_validator)

        result = conductor.run_phase("gate_phase")

        assert result.status == PhaseStatus.COMPLETED
        session = conductor.get_session()
        assert "gate_phase_gate" in session.gate_results
        assert session.gate_results["gate_phase_gate"].passed

    def test_gate_critical_pass_checks_fail_count(self):
        """Test CRITICAL_PASS gate checks compliance.fail_count."""
        state = MockStateManager()
        state._data["compliance.fail_count"] = 0

        registry = PhaseRegistry()
        gate_phase = PhaseDefinition(
            name="compliance_test",
            description="Compliance gate",
            phase_type=PhaseType.VERIFICATION,
            order=0,
            is_gate=True,
            gate_condition=GateCondition.CRITICAL_PASS,
            validators=[],
        )
        registry.register_phase(gate_phase)

        conductor = Conductor(state, registry=registry)
        conductor.create_session("design-001")

        result = conductor.run_phase("compliance_test")

        assert result.status == PhaseStatus.COMPLETED
        session = conductor.get_session()
        assert session.gate_results["compliance_test_gate"].passed

    def test_gate_critical_pass_fails_with_failures(self):
        """Test CRITICAL_PASS gate fails with fail_count > 0."""
        state = MockStateManager()
        state._data["compliance.fail_count"] = 2

        registry = PhaseRegistry()
        gate_phase = PhaseDefinition(
            name="compliance_test",
            description="Compliance gate",
            phase_type=PhaseType.VERIFICATION,
            order=0,
            is_gate=True,
            gate_condition=GateCondition.CRITICAL_PASS,
            validators=[],
        )
        registry.register_phase(gate_phase)

        conductor = Conductor(state, registry=registry)
        conductor.create_session("design-001")

        result = conductor.run_phase("compliance_test")

        # Gate failure causes phase to fail
        assert result.status == PhaseStatus.FAILED
        session = conductor.get_session()
        assert not session.gate_results["compliance_test_gate"].passed

    def test_gate_threshold(self):
        """Test THRESHOLD gate evaluation."""
        state = MockStateManager()
        registry = PhaseRegistry()

        gate_phase = PhaseDefinition(
            name="threshold_gate",
            description="Threshold gate",
            phase_type=PhaseType.VERIFICATION,
            order=0,
            is_gate=True,
            gate_condition=GateCondition.THRESHOLD,
            gate_threshold=0.8,
            validators=["test/v1", "test/v2"],
        )
        registry.register_phase(gate_phase)

        conductor = Conductor(state, registry=registry)
        conductor.create_session("design-001")

        # 2 validators, both pass = 100% > 80%
        mock_result = Mock()
        mock_result.state.value = "passed"
        mock_validator = Mock()
        mock_validator.validate.return_value = mock_result
        conductor.register_validator("test/v1", mock_validator)
        conductor.register_validator("test/v2", mock_validator)

        result = conductor.run_phase("threshold_gate")

        assert result.status == PhaseStatus.COMPLETED
        session = conductor.get_session()
        assert session.gate_results["threshold_gate_gate"].passed

    def test_gate_manual_requires_approval(self):
        """Test MANUAL gate requires explicit approval."""
        state = MockStateManager()
        registry = PhaseRegistry()

        gate_phase = PhaseDefinition(
            name="manual_gate",
            description="Manual gate",
            phase_type=PhaseType.VERIFICATION,
            order=0,
            is_gate=True,
            gate_condition=GateCondition.MANUAL,
            validators=[],
        )
        registry.register_phase(gate_phase)

        conductor = Conductor(state, registry=registry)
        conductor.create_session("design-001")

        result = conductor.run_phase("manual_gate")

        # Manual gates fail until approved
        assert result.status == PhaseStatus.FAILED
        session = conductor.get_session()
        assert not session.gate_results["manual_gate_gate"].passed

    def test_approve_gate(self):
        """Test manual gate approval."""
        state = MockStateManager()
        registry = PhaseRegistry()

        gate_phase = PhaseDefinition(
            name="manual_gate",
            description="Manual gate",
            phase_type=PhaseType.VERIFICATION,
            order=0,
            is_gate=True,
            gate_condition=GateCondition.MANUAL,
            validators=[],
        )
        registry.register_phase(gate_phase)

        conductor = Conductor(state, registry=registry)
        conductor.create_session("design-001")
        conductor.run_phase("manual_gate")

        # Approve the gate
        result = conductor.approve_gate("manual_gate_gate")

        assert result == True
        session = conductor.get_session()
        assert session.gate_results["manual_gate_gate"].passed


class TestRunAllPhases:
    """Tests for running all phases."""

    def test_run_all_stops_on_failure(self):
        """Test run_all_phases stops on first failure."""
        state = MockStateManager()
        registry = PhaseRegistry(load_defaults=False)

        phase1 = PhaseDefinition(
            name="phase1",
            description="Phase 1",
            phase_type=PhaseType.DEFINITION,
            order=1,
            validators=["fail/validator"],
        )
        phase2 = PhaseDefinition(
            name="phase2",
            description="Phase 2",
            phase_type=PhaseType.DEFINITION,
            order=2,
            depends_on=["phase1"],
            validators=[],
        )
        registry.register_phase(phase1)
        registry.register_phase(phase2)

        conductor = Conductor(state, registry=registry)
        conductor.create_session("design-001")

        # Failing validator
        mock_result = Mock()
        mock_result.state.value = "failed"
        mock_result.error_message = "Failed"
        mock_validator = Mock()
        mock_validator.validate.return_value = mock_result
        conductor.register_validator("fail/validator", mock_validator)

        results = conductor.run_all_phases()

        # Should stop after first phase fails
        assert len(results) == 1
        assert results[0].status == PhaseStatus.FAILED


class TestStateWriting:
    """Tests for state writing."""

    def test_write_to_state(self):
        """Test writing conductor state."""
        state = MockStateManager()
        conductor = Conductor(state)
        conductor.create_session("design-001")

        conductor.write_to_state()

        assert "kernel.session" in state._data
        assert "kernel.status" in state._data
        assert state._data["kernel.status"] == "active"

    def test_get_status_summary_no_session(self):
        """Test status summary with no session."""
        state = MockStateManager()
        conductor = Conductor(state)

        summary = conductor.get_status_summary()

        assert summary["status"] == "no_session"

    def test_get_status_summary(self):
        """Test status summary with session."""
        state = MockStateManager()
        conductor = Conductor(state)
        session = conductor.create_session("design-001")

        summary = conductor.get_status_summary()

        assert summary["session_id"] == session.session_id
        assert summary["design_id"] == "design-001"
        assert summary["status"] == "active"

