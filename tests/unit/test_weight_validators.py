"""
Unit tests for weight validators.

Tests WeightEstimationValidator and WeightStabilityValidator.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from magnet.weight.validators import (
    WeightEstimationValidator,
    WeightStabilityValidator,
    get_weight_estimation_definition,
    get_weight_stability_definition,
)
from magnet.validators.taxonomy import ValidatorState


class MockStateManager:
    """Mock StateManager for unit testing."""

    def __init__(self, initial_values=None):
        self._values = initial_values or {}
        self._modified = {}

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value, source=None):
        self._values[key] = value
        self._modified[key] = datetime.utcnow()

    def get_field_metadata(self, key):
        if key in self._modified:
            mock = Mock()
            mock.last_modified = self._modified[key]
            return mock
        return None


class TestWeightEstimationValidator:
    """Tests for WeightEstimationValidator."""

    def test_successful_estimation(self):
        """Test successful weight estimation with all inputs."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.depth": 4.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "hull.hull_type": "monohull",
            "hull.material": "aluminum_5083",
            "hull.displacement_mt": 700.0,
            "propulsion.installed_power_kw": 2000.0,
            "propulsion.number_of_engines": 2,
            "propulsion.engine_type": "high_speed_diesel",
            "mission.crew_size": 6,
            "mission.passengers": 0,
            "mission.vessel_type": "commercial",
        })

        validator = WeightEstimationValidator()
        result = validator.validate(state_manager, {})

        assert result.passed
        assert "weight.lightship_mt" in state_manager._values
        assert "weight.lightship_vcg_m" in state_manager._values
        assert state_manager._values["weight.lightship_mt"] > 0

    def test_missing_hull_parameters_fails(self):
        """Test that missing hull parameters causes failure."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            # Missing beam, depth, cb
        })

        validator = WeightEstimationValidator()
        result = validator.validate(state_manager, {})

        assert result.state == ValidatorState.FAILED
        assert any("Missing required" in f.message for f in result.findings)

    def test_propulsion_fallback_v11(self):
        """Test v1.1 propulsion field fallback."""
        # Use total_installed_power_kw instead of installed_power_kw
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.depth": 4.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "propulsion.total_installed_power_kw": 3000.0,  # Fallback field
            "propulsion.number_of_engines": 2,
            "mission.crew_size": 6,
        })

        validator = WeightEstimationValidator()
        result = validator.validate(state_manager, {})

        assert result.passed
        assert "weight.lightship_mt" in state_manager._values

    def test_group_weights_written(self):
        """Test that group weights are written to state."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.depth": 4.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "propulsion.installed_power_kw": 2000.0,
        })

        validator = WeightEstimationValidator()
        result = validator.validate(state_manager, {})

        assert result.passed
        # Check that group weights were written
        assert "weight.group_100_mt" in state_manager._values
        assert "weight.group_200_mt" in state_manager._values
        assert state_manager._values["weight.group_100_mt"] > 0

    def test_summary_data_written(self):
        """Test that determinized summary data is written."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.depth": 4.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "propulsion.installed_power_kw": 2000.0,
        })

        validator = WeightEstimationValidator()
        result = validator.validate(state_manager, {})

        assert result.passed
        assert "weight.summary_data" in state_manager._values
        summary_data = state_manager._values["weight.summary_data"]
        assert isinstance(summary_data, dict)
        assert "lightship" in summary_data


class TestWeightStabilityValidator:
    """Tests for WeightStabilityValidator."""

    def test_successful_stability_check(self):
        """Test successful weight-stability bridge."""
        state_manager = MockStateManager({
            "weight.lightship_vcg_m": 2.5,
            "weight.lightship_mt": 100.0,
            "hull.displacement_mt": 150.0,
            "hull.kb_m": 1.5,
            "hull.bm_m": 3.0,
        })

        validator = WeightStabilityValidator()
        result = validator.validate(state_manager, {})

        assert result.passed
        # v1.1: stability.kg_m should be written
        assert "stability.kg_m" in state_manager._values
        assert state_manager._values["stability.kg_m"] == 2.5

    def test_kg_written_to_stability(self):
        """Test v1.1: KG is correctly written to stability namespace."""
        vcg_value = 3.2
        state_manager = MockStateManager({
            "weight.lightship_vcg_m": vcg_value,
            "weight.lightship_mt": 100.0,
            "hull.kb_m": 1.5,
            "hull.bm_m": 3.0,
        })

        validator = WeightStabilityValidator()
        result = validator.validate(state_manager, {})

        assert result.passed
        assert state_manager._values["stability.kg_m"] == vcg_value

    def test_gm_calculation(self):
        """Test estimated GM calculation."""
        state_manager = MockStateManager({
            "weight.lightship_vcg_m": 2.5,  # KG
            "weight.lightship_mt": 100.0,
            "hull.kb_m": 1.5,               # KB
            "hull.bm_m": 3.0,               # BM
        })

        validator = WeightStabilityValidator()
        result = validator.validate(state_manager, {})

        assert result.passed
        # GM = KB + BM - KG = 1.5 + 3.0 - 2.5 = 2.0
        assert "weight.estimated_gm_m" in state_manager._values
        assert abs(state_manager._values["weight.estimated_gm_m"] - 2.0) < 0.01

    def test_negative_gm_warning(self):
        """Test negative GM produces warning."""
        state_manager = MockStateManager({
            "weight.lightship_vcg_m": 5.0,  # Very high KG
            "weight.lightship_mt": 100.0,
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.0,
            # KM = 3.5, KG = 5.0, GM = -1.5
        })

        validator = WeightStabilityValidator()
        result = validator.validate(state_manager, {})

        # Should warn about negative GM
        assert result.state == ValidatorState.WARNING
        assert any("Negative GM" in f.message or "unstable" in f.message.lower()
                  for f in result.findings)

    def test_low_gm_warning(self):
        """Test low GM produces warning."""
        state_manager = MockStateManager({
            "weight.lightship_vcg_m": 4.4,  # High KG
            "weight.lightship_mt": 100.0,
            "hull.kb_m": 1.5,
            "hull.bm_m": 3.0,
            # KM = 4.5, KG = 4.4, GM = 0.1 (< 0.15 minimum)
        })

        validator = WeightStabilityValidator()
        result = validator.validate(state_manager, {})

        # Should warn about low GM
        assert result.state == ValidatorState.WARNING
        assert any("Low GM" in f.message or "< 0.15" in f.message
                  for f in result.findings)

    def test_missing_vcg_fails(self):
        """Test missing VCG causes failure."""
        state_manager = MockStateManager({
            # Missing weight.lightship_vcg_m
            "weight.lightship_mt": 100.0,
            "hull.kb_m": 1.5,
            "hull.bm_m": 3.0,
        })

        validator = WeightStabilityValidator()
        result = validator.validate(state_manager, {})

        assert result.state == ValidatorState.FAILED
        assert any("Missing required" in f.message for f in result.findings)

    def test_missing_hydrostatics_fails(self):
        """Test missing KB/BM causes failure."""
        state_manager = MockStateManager({
            "weight.lightship_vcg_m": 2.5,
            "weight.lightship_mt": 100.0,
            # Missing hull.kb_m and hull.bm_m
        })

        validator = WeightStabilityValidator()
        result = validator.validate(state_manager, {})

        assert result.state == ValidatorState.FAILED


class TestValidatorDefinitions:
    """Tests for validator definitions."""

    def test_weight_estimation_definition(self):
        """Test weight estimation validator definition."""
        definition = get_weight_estimation_definition()
        assert definition.validator_id == "weight/estimation"
        assert "hull.lwl" in definition.depends_on_parameters
        assert "weight.lightship_mt" in definition.produces_parameters
        assert definition.is_gate_condition

    def test_weight_stability_definition(self):
        """Test weight stability validator definition."""
        definition = get_weight_stability_definition()
        assert definition.validator_id == "weight/stability_check"
        assert "weight/estimation" in definition.depends_on_validators
        assert "stability.kg_m" in definition.produces_parameters
        assert definition.is_gate_condition
