"""
Integration tests for physics calculation pipeline.

Tests the full flow of physics validators with the validation pipeline.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from magnet.physics import (
    HydrostaticsCalculator,
    ResistanceCalculator,
    HydrostaticsValidator,
    ResistanceValidator,
    HydrostaticsResults,
    ResistanceResults,
)
from magnet.validators.taxonomy import ValidatorState


class MockStateManager:
    """Mock StateManager for integration testing."""

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


class TestPhysicsPipeline:
    """Test physics calculation pipeline."""

    def test_full_pipeline_execution(self):
        """Test executing both validators in order."""
        # Set up initial state
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.depth": 4.0,
            "hull.cb": 0.55,
            "mission.max_speed_kts": 20.0,
        })

        # Execute hydrostatics
        hydro_validator = HydrostaticsValidator()
        hydro_result = hydro_validator.validate(state_manager, {})

        assert hydro_result.passed
        assert "hull.displacement_mt" in state_manager._values
        assert "hull.wetted_surface_m2" in state_manager._values
        assert state_manager._values["hull.displacement_mt"] > 0

        # Execute resistance (depends on hydrostatics outputs)
        resist_validator = ResistanceValidator()
        resist_result = resist_validator.validate(state_manager, {})

        assert resist_result.passed
        assert "resistance.total_kn" in state_manager._values
        assert "resistance.effective_power_kw" in state_manager._values

        # Verify physics consistency
        displacement_mt = state_manager._values["hull.displacement_mt"]
        total_resistance = state_manager._values["resistance.total_kn"]
        effective_power = state_manager._values["resistance.effective_power_kw"]

        assert displacement_mt > 500  # Should be around 700t
        assert total_resistance > 0
        assert effective_power > 0

    def test_implicit_dependency_hydrostatics_to_resistance(self):
        """Test resistance depends on hydrostatics outputs."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "mission.max_speed_kts": 20.0,
            # NOT running hydrostatics first
        })

        # Resistance should fail without hydrostatics
        resist_validator = ResistanceValidator()
        resist_result = resist_validator.validate(state_manager, {})

        assert resist_result.state == ValidatorState.FAILED
        assert any("displacement" in f.message.lower() or "wetted" in f.message.lower()
                  for f in resist_result.findings)

    def test_execution_order_matters(self):
        """Test that execution order affects results."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.depth": 4.0,
            "hull.cb": 0.55,
            "mission.max_speed_kts": 20.0,
        })

        # Wrong order: resistance before hydrostatics
        resist_validator = ResistanceValidator()
        resist_result = resist_validator.validate(state_manager, {})
        assert resist_result.state == ValidatorState.FAILED

        # Correct order: hydrostatics first
        hydro_validator = HydrostaticsValidator()
        hydro_result = hydro_validator.validate(state_manager, {})
        assert hydro_result.passed

        # Now resistance should work
        resist_result = resist_validator.validate(state_manager, {})
        assert resist_result.passed

    def test_all_outputs_written_to_state(self):
        """Test all expected outputs are written to state."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.depth": 4.0,
            "hull.cb": 0.55,
            "mission.max_speed_kts": 15.0,
        })

        # Run both validators
        HydrostaticsValidator().validate(state_manager, {})
        ResistanceValidator().validate(state_manager, {})

        # Check hydrostatics outputs (v1.2)
        hydro_outputs = [
            "hull.displacement_m3",
            "hull.displacement_mt",
            "hull.kb_m",
            "hull.bm_m",
            "hull.tpc",
            "hull.mct",
            "hull.lcf_from_ap_m",
            "hull.waterplane_area_m2",
            "hull.wetted_surface_m2",
            "hull.freeboard",
        ]
        for key in hydro_outputs:
            assert key in state_manager._values, f"Missing hydro output: {key}"

        # Check resistance outputs
        resist_outputs = [
            "resistance.total_kn",
            "resistance.frictional_kn",
            "resistance.residuary_kn",
            "resistance.effective_power_kw",
            "resistance.froude_number",
            "resistance.reynolds_number",
        ]
        for key in resist_outputs:
            assert key in state_manager._values, f"Missing resist output: {key}"

    def test_parameter_change_triggers_revalidation_need(self):
        """Test that parameter changes make results stale."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.depth": 4.0,
            "hull.cb": 0.55,
            "mission.max_speed_kts": 15.0,
        })

        # Initial run
        HydrostaticsValidator().validate(state_manager, {})
        initial_displacement = state_manager._values["hull.displacement_mt"]

        # Change parameter
        state_manager.set("hull.beam", 12.0)

        # Re-run hydrostatics
        HydrostaticsValidator().validate(state_manager, {})
        new_displacement = state_manager._values["hull.displacement_mt"]

        # Displacement should increase with beam
        assert new_displacement > initial_displacement

    def test_consistency_between_validators(self):
        """Test physical consistency between hydrostatics and resistance."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.depth": 4.0,
            "hull.cb": 0.55,
            "mission.max_speed_kts": 15.0,
        })

        HydrostaticsValidator().validate(state_manager, {})
        ResistanceValidator().validate(state_manager, {})

        # Verify physical relationships
        # Power should be proportional to resistance * speed
        total_resistance_n = state_manager._values["resistance.total_kn"] * 1000
        speed_ms = 15.0 * 0.514444
        expected_power_kw = total_resistance_n * speed_ms / 1000

        actual_power_kw = state_manager._values["resistance.effective_power_kw"]

        # Allow 1% tolerance
        assert abs(actual_power_kw - expected_power_kw) / expected_power_kw < 0.01


class TestPhysicsCalculatorConsistency:
    """Test consistency between calculators and validators."""

    def test_calculator_and_validator_match(self):
        """Test calculator and validator produce same results."""
        # Direct calculator
        calc = HydrostaticsCalculator()
        calc_result = calc.calculate(
            lwl=50.0, beam=10.0, draft=2.5, depth=4.0, cb=0.55
        )

        # Via validator
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.depth": 4.0,
            "hull.cb": 0.55,
        })
        HydrostaticsValidator().validate(state_manager, {})

        # Compare results
        assert abs(calc_result.displacement_mt -
                  state_manager._values["hull.displacement_mt"]) < 0.01
        assert abs(calc_result.kb_m - state_manager._values["hull.kb_m"]) < 0.001
        assert abs(calc_result.bm_m - state_manager._values["hull.bm_m"]) < 0.001

    def test_resistance_calculator_and_validator_match(self):
        """Test resistance calculator and validator produce same results."""
        # First get hydrostatics
        hydro_calc = HydrostaticsCalculator()
        hydro = hydro_calc.calculate(
            lwl=50.0, beam=10.0, draft=2.5, depth=4.0, cb=0.55
        )

        # Direct resistance calculation
        resist_calc = ResistanceCalculator()
        resist_result = resist_calc.calculate(
            lwl=50.0, beam=10.0, draft=2.5,
            displacement_mt=hydro.displacement_mt,
            wetted_surface=hydro.wetted_surface_m2,
            speed_kts=15.0, cb=0.55
        )

        # Via validators
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.depth": 4.0,
            "hull.cb": 0.55,
            "mission.max_speed_kts": 15.0,
        })
        HydrostaticsValidator().validate(state_manager, {})
        ResistanceValidator().validate(state_manager, {})

        # Compare results
        assert abs(resist_result.total_kn -
                  state_manager._values["resistance.total_kn"]) < 0.01
        assert abs(resist_result.froude_number -
                  state_manager._values["resistance.froude_number"]) < 0.0001


class TestPhysicsEdgeCases:
    """Test edge cases in physics pipeline."""

    def test_very_small_vessel(self):
        """Test calculations for very small vessel."""
        state_manager = MockStateManager({
            "hull.lwl": 8.0,  # 8m boat
            "hull.beam": 2.5,
            "hull.draft": 0.6,
            "hull.depth": 1.2,
            "hull.cb": 0.45,
            "mission.max_speed_kts": 25.0,  # Fast small boat
        })

        HydrostaticsValidator().validate(state_manager, {})
        ResistanceValidator().validate(state_manager, {})

        # Should still produce valid results
        assert state_manager._values["hull.displacement_mt"] > 0
        assert state_manager._values["resistance.total_kn"] > 0

    def test_very_large_vessel(self):
        """Test calculations for large vessel."""
        state_manager = MockStateManager({
            "hull.lwl": 150.0,  # 150m ship
            "hull.beam": 25.0,
            "hull.draft": 8.0,
            "hull.depth": 12.0,
            "hull.cb": 0.70,
            "mission.max_speed_kts": 18.0,
        })

        HydrostaticsValidator().validate(state_manager, {})
        ResistanceValidator().validate(state_manager, {})

        # Verify large vessel results are reasonable
        displacement = state_manager._values["hull.displacement_mt"]
        assert displacement > 10000  # Should be tens of thousands of tonnes

    def test_high_speed_planing_regime(self):
        """Test high-speed vessel in planing regime."""
        state_manager = MockStateManager({
            "hull.lwl": 20.0,
            "hull.beam": 5.0,
            "hull.draft": 1.0,
            "hull.depth": 2.0,
            "hull.cb": 0.40,  # Planing hull
            "mission.max_speed_kts": 40.0,  # High speed
        })

        HydrostaticsValidator().validate(state_manager, {})
        result = ResistanceValidator().validate(state_manager, {})

        # Should have warning about high Froude number
        fn = state_manager._values["resistance.froude_number"]
        if fn > 0.5:
            assert result.state == ValidatorState.WARNING

    def test_low_speed_displacement_regime(self):
        """Test low-speed displacement vessel."""
        state_manager = MockStateManager({
            "hull.lwl": 100.0,
            "hull.beam": 18.0,
            "hull.draft": 6.0,
            "hull.depth": 10.0,
            "hull.cb": 0.75,  # Full form
            "mission.max_speed_kts": 12.0,  # Slow
        })

        HydrostaticsValidator().validate(state_manager, {})
        result = ResistanceValidator().validate(state_manager, {})

        # Low speed should pass without warnings
        fn = state_manager._values["resistance.froude_number"]
        assert fn < 0.3  # Clearly displacement regime
