"""
Unit tests for magnet/stability/validators.py

Tests IntactGMValidator, GZCurveValidator, and other stability validators.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from magnet.stability.validators import (
    IntactGMValidator,
    GZCurveValidator,
    DamageStabilityValidator,
    WeatherCriterionValidator,
    get_intact_gm_definition,
    get_gz_curve_definition,
)
from magnet.validators.taxonomy import ValidatorState, ResultSeverity


class MockStateManager:
    """Mock StateManager for testing validators."""

    def __init__(self, values=None):
        self._values = values or {}

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value):
        self._values[key] = value

    def get_field_metadata(self, key):
        return None


class TestIntactGMValidator:
    """Test IntactGMValidator class."""

    def test_create_validator(self):
        """Test creating validator."""
        validator = IntactGMValidator()
        assert validator.definition.validator_id == "stability/intact_gm"

    def test_passed_with_valid_inputs(self):
        """Test PASSED state with valid inputs."""
        state_manager = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.0,
            "stability.kg_m": 2.8,
        })

        validator = IntactGMValidator()
        result = validator.validate(state_manager, {})

        assert result.state in (ValidatorState.PASSED, ValidatorState.WARNING)
        assert "stability.gm_transverse_m" in state_manager._values

    def test_kg_sourcing_priority(self):
        """Test KG is sourced from stability.kg_m first."""
        state_manager = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.0,
            "stability.kg_m": 2.5,  # Primary source
            "weight.lightship_vcg_m": 3.0,  # Should NOT be used
        })

        validator = IntactGMValidator()
        result = validator.validate(state_manager, {})

        # GM should be calculated using KG = 2.5, not 3.0
        gm = state_manager._values["stability.gm_transverse_m"]
        expected_gm = 1.5 + 2.0 - 2.5  # = 1.0
        assert abs(gm - expected_gm) < 0.01

    def test_kg_fallback_to_weight(self):
        """Test KG fallback to weight.lightship_vcg_m."""
        state_manager = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.0,
            # stability.kg_m not provided
            "weight.lightship_vcg_m": 2.8,
        })

        validator = IntactGMValidator()
        result = validator.validate(state_manager, {})

        # Should use weight fallback
        assert result.passed
        gm = state_manager._values["stability.gm_transverse_m"]
        expected_gm = 1.5 + 2.0 - 2.8  # = 0.7
        assert abs(gm - expected_gm) < 0.01

    def test_kg_estimation_from_depth(self):
        """Test KG estimation when neither source available."""
        state_manager = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.0,
            "hull.depth": 4.0,  # KG estimated as 0.55 * depth = 2.2
        })

        validator = IntactGMValidator()
        result = validator.validate(state_manager, {})

        # Result is PASSED but with a warning finding about estimation
        assert result.passed  # Still passes since GM is calculated
        assert result.warning_count > 0  # But has warning about estimated KG
        assert "stability.gm_transverse_m" in state_manager._values

    def test_failed_missing_inputs(self):
        """Test FAILED when required inputs missing."""
        state_manager = MockStateManager({
            # Missing hull.kb_m, hull.bm_m
            "stability.kg_m": 2.8,
        })

        validator = IntactGMValidator()
        result = validator.validate(state_manager, {})

        assert result.state == ValidatorState.FAILED

    def test_writes_all_outputs(self):
        """Test all outputs are written to state."""
        state_manager = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.0,
            "stability.kg_m": 2.8,
        })

        validator = IntactGMValidator()
        validator.validate(state_manager, {})

        expected_outputs = [
            "stability.gm_transverse_m",
            "stability.gm_corrected_m",
            "stability.kg_m",
            "stability.kb_m",
            "stability.bm_m",
        ]
        for output in expected_outputs:
            assert output in state_manager._values

    def test_uses_vcb_alias(self):
        """Test uses hull.vcb_m as alias for hull.kb_m."""
        state_manager = MockStateManager({
            "hull.vcb_m": 1.5,  # Alias
            "hull.bm_m": 2.0,
            "stability.kg_m": 2.8,
        })

        validator = IntactGMValidator()
        result = validator.validate(state_manager, {})

        assert result.passed
        assert state_manager._values["stability.kb_m"] == 1.5


class TestGZCurveValidator:
    """Test GZCurveValidator class."""

    def test_create_validator(self):
        """Test creating validator."""
        validator = GZCurveValidator()
        assert validator.definition.validator_id == "stability/gz_curve"

    def test_passed_with_valid_inputs(self):
        """Test PASSED state with valid inputs."""
        state_manager = MockStateManager({
            "stability.gm_transverse_m": 0.7,
            "stability.bm_m": 2.0,
        })

        validator = GZCurveValidator()
        result = validator.validate(state_manager, {})

        assert result.state in (ValidatorState.PASSED, ValidatorState.WARNING)
        assert "stability.gz_curve" in state_manager._values

    def test_failed_missing_gm(self):
        """Test FAILED when GM missing."""
        state_manager = MockStateManager({
            # Missing stability.gm_transverse_m
            "stability.bm_m": 2.0,
        })

        validator = GZCurveValidator()
        result = validator.validate(state_manager, {})

        assert result.state == ValidatorState.FAILED

    def test_writes_gz_outputs(self):
        """Test GZ outputs are written."""
        state_manager = MockStateManager({
            "stability.gm_transverse_m": 0.7,
            "stability.bm_m": 2.0,
        })

        validator = GZCurveValidator()
        validator.validate(state_manager, {})

        expected_outputs = [
            "stability.gz_curve",
            "stability.gz_max_m",
            "stability.angle_of_max_gz_deg",
            "stability.area_0_30_m_rad",
            "stability.area_0_40_m_rad",
            "stability.area_30_40_m_rad",
            "stability.imo_intact_passed",
        ]
        for output in expected_outputs:
            assert output in state_manager._values

    def test_gz_curve_is_list(self):
        """Test GZ curve is stored as list."""
        state_manager = MockStateManager({
            "stability.gm_transverse_m": 0.7,
            "stability.bm_m": 2.0,
        })

        validator = GZCurveValidator()
        validator.validate(state_manager, {})

        gz_curve = state_manager._values["stability.gz_curve"]
        assert isinstance(gz_curve, list)
        assert len(gz_curve) > 0
        assert "heel_deg" in gz_curve[0]
        assert "gz_m" in gz_curve[0]


class TestDamageStabilityValidator:
    """Test DamageStabilityValidator class."""

    def test_create_validator(self):
        """Test creating validator."""
        validator = DamageStabilityValidator()
        assert validator.definition.validator_id == "stability/damage"

    def test_passed_with_valid_inputs(self):
        """Test PASSED with valid inputs."""
        state_manager = MockStateManager({
            "stability.gm_transverse_m": 1.0,
            "stability.gz_max_m": 0.5,
            "hull.displacement_mt": 1000.0,
        })

        validator = DamageStabilityValidator()
        result = validator.validate(state_manager, {})

        assert result.state in (ValidatorState.PASSED, ValidatorState.WARNING)

    def test_writes_damage_outputs(self):
        """Test damage outputs are written."""
        state_manager = MockStateManager({
            "stability.gm_transverse_m": 1.0,
            "stability.gz_max_m": 0.5,
            "hull.displacement_mt": 1000.0,
        })

        validator = DamageStabilityValidator()
        validator.validate(state_manager, {})

        assert "stability.damage_cases" in state_manager._values
        assert "stability.damage_gm_min_m" in state_manager._values
        assert "stability.imo_damage_passed" in state_manager._values


class TestWeatherCriterionValidator:
    """Test WeatherCriterionValidator class."""

    def test_create_validator(self):
        """Test creating validator."""
        validator = WeatherCriterionValidator()
        assert validator.definition.validator_id == "stability/weather_criterion"

    def test_passed_with_valid_inputs(self):
        """Test PASSED with valid inputs."""
        # First need GZ curve data
        state_manager = MockStateManager({
            "stability.gm_transverse_m": 0.7,
            "stability.bm_m": 2.0,
            "stability.area_0_30_m_rad": 0.06,
            "hull.displacement_mt": 1000.0,
            "hull.beam": 10.0,
            "hull.draft": 3.0,
            "hull.loa": 50.0,
        })

        # Generate GZ curve first
        from magnet.stability.validators import GZCurveValidator
        GZCurveValidator().validate(state_manager, {})

        # Now run weather criterion
        validator = WeatherCriterionValidator()
        result = validator.validate(state_manager, {})

        assert result.state in (ValidatorState.PASSED, ValidatorState.WARNING)

    def test_failed_missing_gz_curve(self):
        """Test FAILED when GZ curve missing."""
        state_manager = MockStateManager({
            "stability.gm_transverse_m": 0.7,
            # Missing stability.gz_curve
        })

        validator = WeatherCriterionValidator()
        result = validator.validate(state_manager, {})

        assert result.state == ValidatorState.FAILED


class TestValidatorDefinitions:
    """Test validator definition functions."""

    def test_intact_gm_definition(self):
        """Test intact GM definition."""
        defn = get_intact_gm_definition()
        assert defn.validator_id == "stability/intact_gm"
        assert defn.is_gate_condition == True
        assert "physics/hydrostatics" in defn.depends_on_validators

    def test_gz_curve_definition(self):
        """Test GZ curve definition."""
        defn = get_gz_curve_definition()
        assert defn.validator_id == "stability/gz_curve"
        assert "stability/intact_gm" in defn.depends_on_validators


class TestValidatorIntegration:
    """Test integration between stability validators."""

    def test_intact_gm_then_gz_curve(self):
        """Test running intact GM then GZ curve."""
        state_manager = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.0,
            "stability.kg_m": 2.5,
        })

        # Run intact GM first
        gm_validator = IntactGMValidator()
        gm_result = gm_validator.validate(state_manager, {})
        assert gm_result.passed

        # Now GZ curve should have its dependencies
        gz_validator = GZCurveValidator()
        gz_result = gz_validator.validate(state_manager, {})
        assert gz_result.passed

        # Verify outputs
        assert state_manager._values["stability.gz_max_m"] > 0

    def test_gz_curve_without_gm_fails(self):
        """Test GZ curve fails without GM."""
        state_manager = MockStateManager({
            "stability.bm_m": 2.0,
            # Missing stability.gm_transverse_m
        })

        validator = GZCurveValidator()
        result = validator.validate(state_manager, {})

        assert result.state == ValidatorState.FAILED
