"""
Unit tests for magnet/physics/validators.py

Tests HydrostaticsValidator and ResistanceValidator implementations.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from magnet.physics.validators import (
    HydrostaticsValidator,
    ResistanceValidator,
    get_hydrostatics_definition,
    get_resistance_definition,
)
from magnet.validators.taxonomy import (
    ValidatorState,
    ResultSeverity,
    ValidatorCategory,
)


class MockStateManager:
    """Mock StateManager for testing validators."""

    def __init__(self, values=None):
        self._values = values or {}

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value, source=None):
        self._values[key] = value

    def get_field_metadata(self, key):
        return None


class TestHydrostaticsValidator:
    """Test HydrostaticsValidator class."""

    def test_create_validator(self):
        """Test creating validator."""
        validator = HydrostaticsValidator()
        assert validator.definition.validator_id == "physics/hydrostatics"

    def test_passed_with_valid_inputs(self):
        """Test PASSED state with valid inputs."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.depth": 4.0,
            "hull.cb": 0.55,
        })

        validator = HydrostaticsValidator()
        result = validator.validate(state_manager, {})

        assert result.state in (ValidatorState.PASSED, ValidatorState.WARNING)
        assert result.passed == True

    def test_failed_with_missing_inputs(self):
        """Test FAILED state with missing required inputs."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            # Missing beam, draft, cb
        })

        validator = HydrostaticsValidator()
        result = validator.validate(state_manager, {})

        assert result.state == ValidatorState.FAILED
        assert result.passed == False
        assert result.error_count > 0

    def test_failed_with_zero_inputs(self):
        """Test FAILED state with zero values."""
        state_manager = MockStateManager({
            "hull.lwl": 0,  # Invalid
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.depth": 4.0,
            "hull.cb": 0.55,
        })

        validator = HydrostaticsValidator()
        result = validator.validate(state_manager, {})

        assert result.state == ValidatorState.FAILED

    def test_failed_with_negative_inputs(self):
        """Test FAILED state with negative values."""
        state_manager = MockStateManager({
            "hull.lwl": -50.0,  # Invalid
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.depth": 4.0,
            "hull.cb": 0.55,
        })

        validator = HydrostaticsValidator()
        result = validator.validate(state_manager, {})

        assert result.state == ValidatorState.FAILED

    def test_writes_all_outputs(self):
        """Test validator writes all v1.2 outputs."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.depth": 4.0,
            "hull.cb": 0.55,
        })

        validator = HydrostaticsValidator()
        result = validator.validate(state_manager, {})

        # Check v1.2 outputs are written
        assert "hull.displacement_m3" in state_manager._values
        assert "hull.kb_m" in state_manager._values
        assert "hull.bm_m" in state_manager._values
        assert "hull.tpc" in state_manager._values
        assert "hull.mct" in state_manager._values
        assert "hull.lcf_from_ap_m" in state_manager._values
        assert "hull.waterplane_area_m2" in state_manager._values
        assert "hull.wetted_surface_m2" in state_manager._values
        assert "hull.freeboard" in state_manager._values
        assert "hull.displacement_mt" in state_manager._values

    def test_warning_for_negative_freeboard(self):
        """Test WARNING state for negative freeboard."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.draft": 4.0,  # Draft > depth
            "hull.depth": 3.0,
            "hull.cb": 0.55,
        })

        validator = HydrostaticsValidator()
        result = validator.validate(state_manager, {})

        # Should still compute but with warning
        assert result.state == ValidatorState.WARNING
        assert result.warning_count > 0
        assert any("freeboard" in f.message.lower() for f in result.findings)

    def test_default_depth(self):
        """Test default depth when not provided."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.depth": 0,  # Will default
            "hull.cb": 0.55,
        })

        validator = HydrostaticsValidator()
        result = validator.validate(state_manager, {})

        assert result.passed
        # Default freeboard should be 1.5m
        assert abs(state_manager._values["hull.freeboard"] - 1.5) < 0.1

    def test_fix5_validation_failure_not_retry(self):
        """Test FIX #5: Validation failure returns FAILED, not exception."""
        state_manager = MockStateManager({
            "hull.lwl": -50.0,  # Invalid
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
        })

        validator = HydrostaticsValidator()
        # Should NOT raise exception
        result = validator.validate(state_manager, {})
        assert result.state == ValidatorState.FAILED
        assert not result.is_execution_error


class TestResistanceValidator:
    """Test ResistanceValidator class."""

    def test_create_validator(self):
        """Test creating validator."""
        validator = ResistanceValidator()
        assert validator.definition.validator_id == "physics/resistance"

    def test_passed_with_valid_inputs(self):
        """Test PASSED state with valid inputs."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "hull.displacement_mt": 700.0,
            "hull.wetted_surface_m2": 600.0,
            "mission.max_speed_kts": 15.0,
        })

        validator = ResistanceValidator()
        result = validator.validate(state_manager, {})

        assert result.state in (ValidatorState.PASSED, ValidatorState.WARNING)

    def test_failed_missing_hydrostatics(self):
        """Test FAILED when hydrostatics outputs missing."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            # Missing hull.displacement_mt, hull.wetted_surface_m2
            "mission.max_speed_kts": 15.0,
        })

        validator = ResistanceValidator()
        result = validator.validate(state_manager, {})

        assert result.state == ValidatorState.FAILED
        assert any("hydrostatics" in f.message.lower() for f in result.findings)

    def test_failed_missing_speed(self):
        """Test FAILED when speed missing."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "hull.displacement_mt": 700.0,
            "hull.wetted_surface_m2": 600.0,
            # Missing mission.max_speed_kts
        })

        validator = ResistanceValidator()
        result = validator.validate(state_manager, {})

        assert result.state == ValidatorState.FAILED

    def test_writes_all_outputs(self):
        """Test validator writes all outputs."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "hull.displacement_mt": 700.0,
            "hull.wetted_surface_m2": 600.0,
            "mission.max_speed_kts": 15.0,
        })

        validator = ResistanceValidator()
        result = validator.validate(state_manager, {})

        # Check outputs are written
        assert "resistance.total_kn" in state_manager._values
        assert "resistance.frictional_kn" in state_manager._values
        assert "resistance.residuary_kn" in state_manager._values
        assert "resistance.effective_power_kw" in state_manager._values
        assert "resistance.froude_number" in state_manager._values
        assert "resistance.reynolds_number" in state_manager._values

    def test_high_froude_warning(self):
        """Test WARNING for high Froude number."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "hull.displacement_mt": 700.0,
            "hull.wetted_surface_m2": 600.0,
            "mission.max_speed_kts": 30.0,  # High speed
        })

        validator = ResistanceValidator()
        result = validator.validate(state_manager, {})

        # Check if Fn > 0.5, should have warning
        fn = state_manager._values.get("resistance.froude_number", 0)
        if fn > 0.5:
            assert result.state == ValidatorState.WARNING
            assert any("froude" in f.message.lower() for f in result.findings)

    def test_depends_on_hydrostatics(self):
        """Test explicit dependency on hydrostatics validator."""
        validator = ResistanceValidator()
        assert "physics/hydrostatics" in validator.definition.depends_on_validators


class TestValidatorDefinitions:
    """Test validator definition functions."""

    def test_hydrostatics_definition(self):
        """Test hydrostatics definition."""
        defn = get_hydrostatics_definition()
        assert defn.validator_id == "physics/hydrostatics"
        assert defn.category == ValidatorCategory.PHYSICS
        assert defn.is_gate_condition == True
        assert len(defn.produces_parameters) == 11  # v1.2

    def test_resistance_definition(self):
        """Test resistance definition."""
        defn = get_resistance_definition()
        assert defn.validator_id == "physics/resistance"
        assert defn.category == ValidatorCategory.PHYSICS
        assert defn.is_gate_condition == True
        assert "physics/hydrostatics" in defn.depends_on_validators

    def test_hydrostatics_v12_outputs(self):
        """Test v1.2 outputs are defined."""
        defn = get_hydrostatics_definition()
        v12_outputs = [
            "hull.kb_m",
            "hull.bm_m",
            "hull.tpc",
            "hull.mct",
            "hull.lcf_from_ap_m",
            "hull.freeboard",
        ]
        for out in v12_outputs:
            assert out in defn.produces_parameters


class TestValidatorIntegration:
    """Integration tests between validators."""

    def test_hydrostatics_then_resistance(self):
        """Test running hydrostatics then resistance."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.depth": 4.0,
            "hull.cb": 0.55,
            "mission.max_speed_kts": 15.0,
        })

        # Run hydrostatics first
        hydro_validator = HydrostaticsValidator()
        hydro_result = hydro_validator.validate(state_manager, {})
        assert hydro_result.passed

        # Now resistance should have its dependencies
        resist_validator = ResistanceValidator()
        resist_result = resist_validator.validate(state_manager, {})
        assert resist_result.passed

        # Verify outputs
        assert state_manager._values["resistance.total_kn"] > 0
        assert state_manager._values["resistance.effective_power_kw"] > 0

    def test_resistance_without_hydrostatics_fails(self):
        """Test resistance fails without hydrostatics."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            # No hydrostatics outputs
            "mission.max_speed_kts": 15.0,
        })

        resist_validator = ResistanceValidator()
        resist_result = resist_validator.validate(state_manager, {})
        assert not resist_result.passed
