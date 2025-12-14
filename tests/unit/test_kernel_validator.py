"""
tests/unit/test_kernel_validator.py - Tests for kernel validator.

BRAVO OWNS THIS FILE.

Tests for Module 15 v1.1 - KernelValidator.
"""

import pytest
from magnet.kernel import KernelValidator, SessionStatus
from magnet.kernel.validator import KERNEL_DEFINITION
from magnet.validators.taxonomy import ValidatorState


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


class TestKernelDefinition:
    """Tests for kernel validator definition."""

    def test_definition_exists(self):
        """Test KERNEL_DEFINITION is properly defined."""
        assert KERNEL_DEFINITION is not None
        assert KERNEL_DEFINITION.validator_id == "kernel/orchestrator"
        assert KERNEL_DEFINITION.name == "Kernel Orchestrator"

    def test_definition_produces_parameters(self):
        """Test definition produces expected parameters."""
        assert len(KERNEL_DEFINITION.produces_parameters) > 0
        assert "kernel.status" in KERNEL_DEFINITION.produces_parameters

    def test_definition_has_phase(self):
        """Test definition has kernel phase."""
        assert KERNEL_DEFINITION.phase == "kernel"


class TestKernelValidatorCreation:
    """Tests for KernelValidator creation."""

    def test_create_validator(self):
        """Test creating kernel validator."""
        validator = KernelValidator()

        assert validator is not None
        assert validator.definition == KERNEL_DEFINITION

    def test_validator_id(self):
        """Test validator ID."""
        validator = KernelValidator()

        assert validator.definition.validator_id == "kernel/orchestrator"


class TestKernelValidation:
    """Tests for kernel validation."""

    def test_validate_no_kernel_status(self):
        """Test validation with no kernel status warns."""
        state = MockStateManager()
        validator = KernelValidator()

        result = validator.validate(state, {})

        # Should warn about no kernel status
        assert result.state == ValidatorState.WARNING
        assert result.warning_count > 0

    def test_validate_incomplete_phases(self):
        """Test validation with incomplete phases."""
        state = MockStateManager()
        state._data["kernel.status"] = "active"
        state._data["kernel.phase_history"] = ["mission", "hull"]

        validator = KernelValidator()
        result = validator.validate(state, {})

        # Should have info finding about incomplete pipeline
        assert len(result.findings) > 0

    def test_validate_failed_gates(self):
        """Test validation with failed gates."""
        state = MockStateManager()
        state._data["kernel.status"] = "active"
        state._data["kernel.phase_history"] = ["mission"]
        state._data["kernel.gate_status"] = {"compliance_gate": False}

        validator = KernelValidator()
        result = validator.validate(state, {})

        # Should fail due to failed gates
        assert result.state == ValidatorState.FAILED
        assert result.error_count > 0

    def test_validate_all_phases_complete(self):
        """Test validation with all phases complete."""
        state = MockStateManager()
        state._data["kernel.status"] = "completed"
        state._data["kernel.phase_history"] = [
            "mission", "hull", "structure", "propulsion",
            "weight", "stability", "loading", "arrangement",
            "compliance", "production", "cost", "optimization", "reporting"
        ]
        state._data["kernel.gate_status"] = {"compliance_gate": True}

        validator = KernelValidator()
        result = validator.validate(state, {})

        assert result.state == ValidatorState.PASSED

    def test_validate_writes_summary(self):
        """Test validation writes summary to state."""
        state = MockStateManager()
        state._data["kernel.status"] = "completed"
        state._data["kernel.phase_history"] = [
            "mission", "hull", "structure", "propulsion",
            "weight", "stability", "loading", "arrangement",
            "compliance", "production", "cost", "optimization", "reporting"
        ]
        state._data["kernel.gate_status"] = {}

        validator = KernelValidator()
        validator.validate(state, {})

        # Should write validation summary
        assert "kernel.validation_summary" in state._data
        assert "kernel.validation_complete" in state._data

    def test_validate_missing_critical_phase(self):
        """Test validation warns about missing critical phases."""
        state = MockStateManager()
        state._data["kernel.status"] = "active"
        state._data["kernel.phase_history"] = ["mission", "hull"]  # Missing compliance/stability

        validator = KernelValidator()
        result = validator.validate(state, {})

        # Should warn about missing critical phases
        assert result.warning_count > 0


class TestKernelValidatorErrorHandling:
    """Tests for error handling."""

    def test_validate_handles_exception(self):
        """Test validation handles exceptions gracefully."""
        state = MockStateManager()
        # Create state that will cause an issue
        state._data["kernel.gate_status"] = "invalid"  # Should be dict

        validator = KernelValidator()
        result = validator.validate(state, {})

        # Should handle error gracefully
        assert result.state == ValidatorState.ERROR
        assert result.error_message is not None

