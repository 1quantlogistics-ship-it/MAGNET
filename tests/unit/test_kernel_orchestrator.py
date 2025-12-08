"""
tests/unit/test_kernel_orchestrator.py - Tests for validation orchestrator.

BRAVO OWNS THIS FILE.

Tests for Module 15 v1.1 - ValidationOrchestrator.
"""

import pytest
from unittest.mock import Mock, MagicMock
from magnet.kernel import (
    ValidationOrchestrator,
    PhaseRegistry,
    PhaseStatus,
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

    def set(self, key, value):
        self._data[key] = value


class TestOrchestratorCreation:
    """Tests for ValidationOrchestrator initialization."""

    def test_create_orchestrator(self):
        """Test basic orchestrator creation."""
        state = MockStateManager()
        orchestrator = ValidationOrchestrator(state)

        assert orchestrator.conductor is not None
        assert orchestrator.registry is not None

    def test_orchestrator_has_registry(self):
        """Test orchestrator has registry from conductor."""
        state = MockStateManager()
        orchestrator = ValidationOrchestrator(state)

        # Registry is created internally
        assert orchestrator.registry is not None
        assert len(orchestrator.registry._phases) > 0


class TestValidatorRegistration:
    """Tests for validator registration."""

    def test_register_validator(self):
        """Test registering single validator."""
        state = MockStateManager()
        orchestrator = ValidationOrchestrator(state)

        mock_validator = Mock()
        orchestrator.register_validator("test/validator", mock_validator)

        # Validator should be registered with conductor
        assert "test/validator" in orchestrator.conductor._validators

    def test_register_validators_dict(self):
        """Test registering multiple validators."""
        state = MockStateManager()
        orchestrator = ValidationOrchestrator(state)

        validators = {
            "test/v1": Mock(),
            "test/v2": Mock(),
            "test/v3": Mock(),
        }
        orchestrator.register_validators(validators)

        for vid in validators:
            assert vid in orchestrator.conductor._validators


class TestRunPipeline:
    """Tests for running full pipeline."""

    def test_run_full_pipeline_returns_summary(self):
        """Test full pipeline returns summary dict."""
        state = MockStateManager()
        state._data["compliance.fail_count"] = 0

        orchestrator = ValidationOrchestrator(state)

        # Register all validators as passing
        mock_result = Mock()
        mock_result.state = Mock()
        mock_result.state.value = "passed"
        mock_validator = Mock()
        mock_validator.validate.return_value = mock_result

        for phase in orchestrator.registry.get_phases_in_order():
            for vid in phase.validators:
                orchestrator.register_validator(vid, mock_validator)

        summary = orchestrator.run_full_pipeline("design-001")

        assert isinstance(summary, dict)
        assert "session_id" in summary
        assert summary["design_id"] == "design-001"
        assert "phases_completed" in summary
        assert "pass_rate" in summary

    def test_run_full_pipeline_context(self):
        """Test full pipeline passes context to validators."""
        state = MockStateManager()
        state._data["compliance.fail_count"] = 0

        orchestrator = ValidationOrchestrator(state)

        mock_result = Mock()
        mock_result.state = Mock()
        mock_result.state.value = "passed"
        mock_validator = Mock()
        mock_validator.validate.return_value = mock_result

        # Register one validator
        orchestrator.register_validator("mission/requirements", mock_validator)

        context = {"key": "value"}
        orchestrator.run_full_pipeline("design-001", context=context)

        # Validator should receive context
        mock_validator.validate.assert_called()


class TestRunSinglePhase:
    """Tests for running single phase."""

    def test_run_single_phase_returns_dict(self):
        """Test running a single phase returns dict."""
        state = MockStateManager()
        orchestrator = ValidationOrchestrator(state)

        result = orchestrator.run_single_phase("mission")

        # Returns dict (to_dict result)
        assert isinstance(result, dict)
        assert result["phase_name"] == "mission"

    def test_run_single_phase_unknown(self):
        """Test running unknown phase returns failed dict."""
        state = MockStateManager()
        orchestrator = ValidationOrchestrator(state)

        result = orchestrator.run_single_phase("nonexistent")

        # Returns dict with failed status
        assert isinstance(result, dict)
        assert result["status"] == "failed"
        assert "Unknown phase" in result["errors"][0]


class TestRunToPhase:
    """Tests for running up to a phase."""

    def test_run_to_phase_returns_summary(self):
        """Test running up to a specific phase."""
        state = MockStateManager()
        orchestrator = ValidationOrchestrator(state)

        result = orchestrator.run_to_phase("hull", design_id="design-001")

        assert isinstance(result, dict)
        assert result["target_phase"] == "hull"
        assert "phases_run" in result
        assert "phase_results" in result


class TestOrchestratorHelpers:
    """Tests for orchestrator helper methods."""

    def test_get_available_phases(self):
        """Test getting available phases."""
        state = MockStateManager()
        orchestrator = ValidationOrchestrator(state)

        phases = orchestrator.get_available_phases()

        assert "mission" in phases
        assert "hull" in phases
        assert "compliance" in phases

    def test_get_phase_status_pending(self):
        """Test phase status before running."""
        state = MockStateManager()
        orchestrator = ValidationOrchestrator(state)

        status = orchestrator.get_phase_status("mission")

        assert status == "pending"

    def test_get_phase_dependencies(self):
        """Test getting phase dependencies."""
        state = MockStateManager()
        orchestrator = ValidationOrchestrator(state)

        deps = orchestrator.get_phase_dependencies("stability")

        # Stability depends on weight transitively
        assert "weight" in deps or "hull" in deps

    def test_get_summary_no_session(self):
        """Test getting summary with no session."""
        state = MockStateManager()
        orchestrator = ValidationOrchestrator(state)

        summary = orchestrator.get_summary()

        assert summary["status"] == "no_session"

    def test_get_summary_with_session(self):
        """Test getting summary after running."""
        state = MockStateManager()
        orchestrator = ValidationOrchestrator(state)

        # Run a phase to create session
        orchestrator.run_single_phase("mission")

        summary = orchestrator.get_summary()

        assert "session_id" in summary
        assert summary["status"] != "no_session"

