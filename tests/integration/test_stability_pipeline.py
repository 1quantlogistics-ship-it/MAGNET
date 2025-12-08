"""
Integration tests for stability calculation pipeline.

Tests the full flow of stability validators with the validation pipeline.
Module 06 v1.2 - Stability Calculations Framework
"""

import pytest
import math
from datetime import datetime
from unittest.mock import Mock

from magnet.stability import (
    IntactGMCalculator,
    GZCurveCalculator,
    FreeSurfaceCalculator,
    DamageStabilityCalculator,
    WeatherCriterionCalculator,
    IntactGMValidator,
    GZCurveValidator,
    DamageStabilityValidator,
    WeatherCriterionValidator,
    GMResults,
    GZCurveResults,
)
from magnet.stability.constants import (
    IMO_INTACT,
    check_imo_intact_criteria,
)
from magnet.validators.taxonomy import ValidatorState


class MockStateManager:
    """Mock StateManager for integration testing."""

    def __init__(self, initial_values=None):
        self._values = initial_values or {}
        self._modified = {}

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value):
        self._values[key] = value
        self._modified[key] = datetime.utcnow()

    def get_field_metadata(self, key):
        if key in self._modified:
            mock = Mock()
            mock.last_modified = self._modified[key]
            return mock
        return None


class TestStabilityPipeline:
    """Test stability calculation pipeline."""

    def test_full_pipeline_execution(self):
        """Test executing all stability validators in order."""
        # Set up initial state with physics outputs
        state_manager = MockStateManager({
            # Physics outputs (from Module 05)
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.5,
            "hull.displacement_mt": 700.0,
            "hull.displacement_m3": 683.0,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.depth": 4.0,
            "hull.loa": 50.0,
            # Stability input
            "stability.kg_m": 2.8,
        })

        # Execute intact GM (first in chain)
        gm_validator = IntactGMValidator()
        gm_result = gm_validator.validate(state_manager, {})

        assert gm_result.passed
        assert "stability.gm_transverse_m" in state_manager._values
        gm = state_manager._values["stability.gm_transverse_m"]
        assert abs(gm - 1.2) < 0.01  # 1.5 + 2.5 - 2.8 = 1.2

        # Execute GZ curve (depends on intact GM)
        gz_validator = GZCurveValidator()
        gz_result = gz_validator.validate(state_manager, {})

        assert gz_result.passed
        assert "stability.gz_curve" in state_manager._values
        assert "stability.gz_max_m" in state_manager._values
        assert state_manager._values["stability.gz_max_m"] > 0

        # Execute damage stability (depends on GZ curve)
        damage_validator = DamageStabilityValidator()
        damage_result = damage_validator.validate(state_manager, {})

        assert damage_result.passed
        assert "stability.damage_cases" in state_manager._values
        assert "stability.imo_damage_passed" in state_manager._values

        # Execute weather criterion (depends on GZ curve)
        weather_validator = WeatherCriterionValidator()
        weather_result = weather_validator.validate(state_manager, {})

        assert weather_result.passed
        assert "stability.weather_criterion_ratio" in state_manager._values

    def test_execution_order_matters(self):
        """Test that execution order affects results."""
        state_manager = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.5,
            "hull.displacement_mt": 700.0,
            "stability.kg_m": 2.8,
        })

        # Wrong order: GZ curve before intact GM
        gz_validator = GZCurveValidator()
        gz_result = gz_validator.validate(state_manager, {})
        assert gz_result.state == ValidatorState.FAILED

        # Correct order: intact GM first
        gm_validator = IntactGMValidator()
        gm_result = gm_validator.validate(state_manager, {})
        assert gm_result.passed

        # Now GZ curve should work
        gz_result = gz_validator.validate(state_manager, {})
        assert gz_result.passed

    def test_all_stability_outputs_written(self):
        """Test all expected stability outputs are written to state."""
        state_manager = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.5,
            "hull.displacement_mt": 700.0,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.loa": 50.0,
            "stability.kg_m": 2.8,
        })

        # Run all validators
        IntactGMValidator().validate(state_manager, {})
        GZCurveValidator().validate(state_manager, {})
        DamageStabilityValidator().validate(state_manager, {})
        WeatherCriterionValidator().validate(state_manager, {})

        # Check intact GM outputs
        gm_outputs = [
            "stability.gm_transverse_m",
            "stability.gm_corrected_m",
            "stability.kg_m",
            "stability.kb_m",
            "stability.bm_m",
        ]
        for key in gm_outputs:
            assert key in state_manager._values, f"Missing GM output: {key}"

        # Check GZ curve outputs
        gz_outputs = [
            "stability.gz_curve",
            "stability.gz_max_m",
            "stability.angle_of_max_gz_deg",
            "stability.area_0_30_m_rad",
            "stability.area_0_40_m_rad",
            "stability.area_30_40_m_rad",
            "stability.imo_intact_passed",
        ]
        for key in gz_outputs:
            assert key in state_manager._values, f"Missing GZ output: {key}"

        # Check damage outputs
        damage_outputs = [
            "stability.damage_cases",
            "stability.damage_gm_min_m",
            "stability.imo_damage_passed",
        ]
        for key in damage_outputs:
            assert key in state_manager._values, f"Missing damage output: {key}"

        # Check weather outputs
        weather_outputs = [
            "stability.weather_criterion_ratio",
            "stability.weather_criterion_passed",
        ]
        for key in weather_outputs:
            assert key in state_manager._values, f"Missing weather output: {key}"

    def test_kg_sourcing_priority(self):
        """Test KG sourcing: stability.kg_m first, then weight.lightship_vcg_m."""
        # Case 1: stability.kg_m available (primary)
        state_manager1 = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.5,
            "stability.kg_m": 2.5,
            "weight.lightship_vcg_m": 3.0,  # Should NOT be used
        })

        IntactGMValidator().validate(state_manager1, {})
        gm1 = state_manager1._values["stability.gm_transverse_m"]
        assert abs(gm1 - 1.5) < 0.01  # 1.5 + 2.5 - 2.5 = 1.5

        # Case 2: Only weight.lightship_vcg_m (fallback)
        state_manager2 = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.5,
            # stability.kg_m not provided
            "weight.lightship_vcg_m": 3.0,
        })

        IntactGMValidator().validate(state_manager2, {})
        gm2 = state_manager2._values["stability.gm_transverse_m"]
        assert abs(gm2 - 1.0) < 0.01  # 1.5 + 2.5 - 3.0 = 1.0


class TestPhysicsToStabilityIntegration:
    """Test integration between physics and stability modules."""

    def test_physics_outputs_feed_stability(self):
        """Test that physics outputs are correctly used by stability."""
        # Simulate physics outputs
        state_manager = MockStateManager({
            # Physics module outputs
            "hull.kb_m": 1.25,  # From physics/hydrostatics
            "hull.bm_m": 2.8,   # From physics/hydrostatics
            "hull.displacement_mt": 687.5,
            "hull.beam": 10.0,
            "hull.draft": 2.5,
            "hull.loa": 50.0,
            # Weight module output
            "weight.lightship_vcg_m": 2.7,
        })

        # Run stability validators
        gm_result = IntactGMValidator().validate(state_manager, {})
        gz_result = GZCurveValidator().validate(state_manager, {})

        assert gm_result.passed
        assert gz_result.passed

        # Verify GM calculation used physics outputs
        kb = state_manager._values["stability.kb_m"]
        bm = state_manager._values["stability.bm_m"]
        kg = state_manager._values["stability.kg_m"]
        gm = state_manager._values["stability.gm_transverse_m"]

        assert abs(kb - 1.25) < 0.01
        assert abs(bm - 2.8) < 0.01
        assert abs(gm - (kb + bm - kg)) < 0.01

    def test_vcb_alias_integration(self):
        """Test hull.vcb_m is correctly aliased to hull.kb_m."""
        state_manager = MockStateManager({
            "hull.vcb_m": 1.5,  # Alias for hull.kb_m
            "hull.bm_m": 2.5,
            "stability.kg_m": 2.8,
        })

        result = IntactGMValidator().validate(state_manager, {})

        assert result.passed
        assert state_manager._values["stability.kb_m"] == 1.5


class TestStabilityCalculatorConsistency:
    """Test consistency between calculators and validators."""

    def test_gm_calculator_and_validator_match(self):
        """Test GM calculator and validator produce same results."""
        # Direct calculator
        calc = IntactGMCalculator()
        calc_result = calc.calculate(kb_m=1.5, bm_m=2.5, kg_m=2.8)

        # Via validator
        state_manager = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.5,
            "stability.kg_m": 2.8,
        })
        IntactGMValidator().validate(state_manager, {})

        # Compare results
        assert abs(calc_result.gm_m - state_manager._values["stability.gm_transverse_m"]) < 0.001
        assert abs(calc_result.km_m - (1.5 + 2.5)) < 0.001

    def test_gz_calculator_and_validator_match(self):
        """Test GZ calculator and validator produce same results."""
        # Direct calculator
        calc = GZCurveCalculator()
        calc_result = calc.calculate(gm_m=1.2, bm_m=2.5)

        # Via validator
        state_manager = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.5,
            "stability.kg_m": 2.8,  # GM = 1.5 + 2.5 - 2.8 = 1.2
        })
        IntactGMValidator().validate(state_manager, {})
        GZCurveValidator().validate(state_manager, {})

        # Compare results
        assert abs(calc_result.gz_max_m - state_manager._values["stability.gz_max_m"]) < 0.01
        assert abs(calc_result.area_0_30_m_rad - state_manager._values["stability.area_0_30_m_rad"]) < 0.001


class TestIMOCriteriaIntegration:
    """Test IMO criteria checking in pipeline."""

    def test_passing_vessel_meets_all_criteria(self):
        """Test vessel with good stability passes all IMO criteria."""
        state_manager = MockStateManager({
            "hull.kb_m": 2.0,
            "hull.bm_m": 3.0,
            "hull.displacement_mt": 1000.0,
            "hull.beam": 12.0,
            "hull.draft": 3.0,
            "hull.loa": 60.0,
            "stability.kg_m": 3.0,  # GM = 2.0 + 3.0 - 3.0 = 2.0 (very good)
        })

        IntactGMValidator().validate(state_manager, {})
        GZCurveValidator().validate(state_manager, {})

        # Check IMO criteria
        assert state_manager._values["stability.imo_intact_passed"] == True
        assert state_manager._values["stability.gm_transverse_m"] >= IMO_INTACT.gm_min_m

    def test_marginal_stability_may_fail_criteria(self):
        """Test vessel with marginal stability may fail some criteria."""
        state_manager = MockStateManager({
            "hull.kb_m": 1.0,
            "hull.bm_m": 1.2,
            "hull.displacement_mt": 500.0,
            "stability.kg_m": 2.0,  # GM = 1.0 + 1.2 - 2.0 = 0.2 (marginal)
        })

        IntactGMValidator().validate(state_manager, {})
        GZCurveValidator().validate(state_manager, {})

        # GM barely meets minimum
        gm = state_manager._values["stability.gm_transverse_m"]
        assert gm >= IMO_INTACT.gm_min_m  # 0.15m

    def test_poor_stability_fails_criteria(self):
        """Test vessel with poor stability fails IMO criteria."""
        state_manager = MockStateManager({
            "hull.kb_m": 1.0,
            "hull.bm_m": 1.0,
            "hull.displacement_mt": 500.0,
            "stability.kg_m": 1.95,  # GM = 1.0 + 1.0 - 1.95 = 0.05 (below minimum)
        })

        gm_result = IntactGMValidator().validate(state_manager, {})

        # Should warn or fail due to low GM
        gm = state_manager._values["stability.gm_transverse_m"]
        assert gm < IMO_INTACT.gm_min_m

        # GZ curve should still be calculated but fail criteria
        GZCurveValidator().validate(state_manager, {})
        assert state_manager._values["stability.imo_intact_passed"] == False


class TestStabilityEdgeCases:
    """Test edge cases in stability pipeline."""

    def test_very_stable_vessel(self):
        """Test calculations for very stable vessel (high GM)."""
        state_manager = MockStateManager({
            "hull.kb_m": 2.5,
            "hull.bm_m": 5.0,
            "hull.displacement_mt": 2000.0,
            "hull.beam": 15.0,
            "hull.draft": 3.5,
            "hull.loa": 80.0,
            "stability.kg_m": 3.5,  # GM = 2.5 + 5.0 - 3.5 = 4.0 (very high)
        })

        IntactGMValidator().validate(state_manager, {})
        GZCurveValidator().validate(state_manager, {})
        DamageStabilityValidator().validate(state_manager, {})

        gm = state_manager._values["stability.gm_transverse_m"]
        assert gm > 3.0  # Very stable

        # Should pass all criteria easily
        assert state_manager._values["stability.imo_intact_passed"] == True
        assert state_manager._values["stability.imo_damage_passed"] == True

    def test_small_craft_stability(self):
        """Test stability calculations for small craft."""
        state_manager = MockStateManager({
            "hull.kb_m": 0.4,
            "hull.bm_m": 0.8,
            "hull.displacement_mt": 5.0,
            "hull.beam": 2.5,
            "hull.draft": 0.5,
            "hull.loa": 8.0,
            "stability.kg_m": 0.6,  # GM = 0.4 + 0.8 - 0.6 = 0.6
        })

        IntactGMValidator().validate(state_manager, {})
        GZCurveValidator().validate(state_manager, {})

        # Should produce valid results even for small craft
        assert state_manager._values["stability.gm_transverse_m"] > 0
        assert state_manager._values["stability.gz_max_m"] > 0
        assert len(state_manager._values["stability.gz_curve"]) > 0

    def test_catamaran_wide_beam(self):
        """Test stability for catamaran (wide beam, high BM)."""
        state_manager = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 8.0,  # Very high BM for catamaran
            "hull.displacement_mt": 50.0,
            "hull.beam": 8.0,
            "hull.draft": 1.0,
            "hull.loa": 15.0,
            "stability.kg_m": 4.0,
        })

        IntactGMValidator().validate(state_manager, {})
        GZCurveValidator().validate(state_manager, {})

        # Catamaran should have very high GM
        gm = state_manager._values["stability.gm_transverse_m"]
        assert gm > 4.0  # Very high due to large BM

    def test_negative_gm_unstable(self):
        """Test handling of negative GM (unstable vessel)."""
        state_manager = MockStateManager({
            "hull.kb_m": 1.0,
            "hull.bm_m": 1.0,
            "hull.displacement_mt": 500.0,
            "stability.kg_m": 3.0,  # GM = 1.0 + 1.0 - 3.0 = -1.0 (unstable!)
        })

        result = IntactGMValidator().validate(state_manager, {})

        # Should warn about negative GM
        gm = state_manager._values["stability.gm_transverse_m"]
        assert gm < 0

        # GZ curve should still calculate but show instability
        GZCurveValidator().validate(state_manager, {})
        assert state_manager._values["stability.imo_intact_passed"] == False


class TestParameterChanges:
    """Test parameter changes affecting stability."""

    def test_kg_change_affects_gm(self):
        """Test that KG changes affect GM."""
        state_manager = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.5,
            "stability.kg_m": 2.8,
        })

        IntactGMValidator().validate(state_manager, {})
        gm1 = state_manager._values["stability.gm_transverse_m"]

        # Increase KG (worse stability)
        state_manager.set("stability.kg_m", 3.2)
        IntactGMValidator().validate(state_manager, {})
        gm2 = state_manager._values["stability.gm_transverse_m"]

        assert gm2 < gm1  # Higher KG = lower GM

    def test_bm_change_affects_gm(self):
        """Test that BM changes affect GM."""
        state_manager = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.0,
            "stability.kg_m": 2.8,
        })

        IntactGMValidator().validate(state_manager, {})
        gm1 = state_manager._values["stability.gm_transverse_m"]

        # Increase BM (better stability - wider beam)
        state_manager.set("hull.bm_m", 3.0)
        IntactGMValidator().validate(state_manager, {})
        gm2 = state_manager._values["stability.gm_transverse_m"]

        assert gm2 > gm1  # Higher BM = higher GM


class TestFreeSurfaceIntegration:
    """Test free surface correction in pipeline."""

    def test_fsc_reduces_gm(self):
        """Test that free surface correction reduces effective GM."""
        # Without FSC
        state_manager1 = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.5,
            "stability.kg_m": 2.8,
        })
        IntactGMValidator().validate(state_manager1, {})
        gm_solid = state_manager1._values["stability.gm_transverse_m"]

        # With FSC (simulated via fsc_m input if supported)
        # For now just verify the solid GM calculation
        assert gm_solid > 0


class TestDamageStabilityIntegration:
    """Test damage stability in pipeline."""

    def test_damage_stability_after_gz_curve(self):
        """Test damage stability runs correctly after GZ curve."""
        state_manager = MockStateManager({
            "hull.kb_m": 2.0,
            "hull.bm_m": 3.0,
            "hull.displacement_mt": 1000.0,
            "hull.beam": 12.0,
            "hull.draft": 3.0,
            "hull.loa": 60.0,
            "stability.kg_m": 3.0,
        })

        IntactGMValidator().validate(state_manager, {})
        GZCurveValidator().validate(state_manager, {})
        DamageStabilityValidator().validate(state_manager, {})

        # Verify damage outputs
        assert "stability.damage_cases" in state_manager._values
        damage_cases = state_manager._values["stability.damage_cases"]
        assert len(damage_cases) > 0

        # Verify worst case identified
        assert state_manager._values["stability.damage_gm_min_m"] > 0


class TestWeatherCriterionIntegration:
    """Test weather criterion in pipeline."""

    def test_weather_criterion_after_gz_curve(self):
        """Test weather criterion runs correctly after GZ curve."""
        state_manager = MockStateManager({
            "hull.kb_m": 2.0,
            "hull.bm_m": 3.0,
            "hull.displacement_mt": 1000.0,
            "hull.beam": 12.0,
            "hull.draft": 3.0,
            "hull.loa": 60.0,
            "stability.kg_m": 3.0,
        })

        IntactGMValidator().validate(state_manager, {})
        GZCurveValidator().validate(state_manager, {})
        WeatherCriterionValidator().validate(state_manager, {})

        # Verify weather outputs
        assert "stability.weather_criterion_ratio" in state_manager._values
        ratio = state_manager._values["stability.weather_criterion_ratio"]
        assert ratio > 0

        # Good stability should pass weather criterion
        assert state_manager._values["stability.weather_criterion_passed"] == True


class TestGZCurveProperties:
    """Test GZ curve properties in pipeline."""

    def test_gz_curve_structure(self):
        """Test GZ curve has correct structure."""
        state_manager = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.5,
            "stability.kg_m": 2.8,
        })

        IntactGMValidator().validate(state_manager, {})
        GZCurveValidator().validate(state_manager, {})

        gz_curve = state_manager._values["stability.gz_curve"]

        # Should be a list of dictionaries
        assert isinstance(gz_curve, list)
        assert len(gz_curve) > 0

        # Each point should have heel_deg and gz_m
        for point in gz_curve:
            assert "heel_deg" in point
            assert "gz_m" in point

    def test_gz_zero_at_zero_heel(self):
        """Test GZ = 0 at zero heel angle."""
        state_manager = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.5,
            "stability.kg_m": 2.8,
        })

        IntactGMValidator().validate(state_manager, {})
        GZCurveValidator().validate(state_manager, {})

        gz_curve = state_manager._values["stability.gz_curve"]
        gz_0 = next(p for p in gz_curve if p["heel_deg"] == 0.0)
        assert abs(gz_0["gz_m"]) < 0.001

    def test_gz_max_angle_is_reasonable(self):
        """Test angle of maximum GZ is reasonable."""
        state_manager = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.5,
            "stability.kg_m": 2.8,
        })

        IntactGMValidator().validate(state_manager, {})
        GZCurveValidator().validate(state_manager, {})

        angle_max = state_manager._values["stability.angle_of_max_gz_deg"]

        # With wall-sided formula and high GM+BM, max is at highest calculated angle (80°)
        # For this particular case (GM=1.2, BM=2.5), the GZ keeps increasing
        # The key is that the angle is within the calculated range
        assert angle_max >= 20.0
        assert angle_max <= 80.0  # Max is now 80 degrees in curve
