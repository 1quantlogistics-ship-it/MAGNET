"""
Unit tests for magnet/physics/resistance.py

Tests ResistanceCalculator and ResistanceResults.
"""

import pytest
import math
from magnet.physics.resistance import (
    ResistanceCalculator,
    ResistanceResults,
    RESISTANCE_INPUTS,
    RESISTANCE_OUTPUTS,
    RHO_SEAWATER,
    NU_SEAWATER,
    GRAVITY,
    calculate_resistance,
)


class TestResistanceResults:
    """Test ResistanceResults dataclass."""

    def test_create_results(self):
        """Test creating results with all fields."""
        results = ResistanceResults(
            total_kn=100.0,
            total_n=100000.0,
            frictional_kn=60.0,
            residuary_kn=35.0,
            appendage_kn=3.0,
            air_kn=2.0,
            effective_power_kw=1000.0,
            effective_power_hp=1341.0,
            froude_number=0.35,
            reynolds_number=1e8,
            cf=0.002,
            cr=0.001,
            ct=0.003,
            form_factor=1.15,
            speed_kts=20.0,
            speed_ms=10.29,
        )
        assert results.total_kn == 100.0
        assert results.froude_number == 0.35

    def test_to_dict(self):
        """Test serialization to dictionary."""
        results = ResistanceResults(
            total_kn=100.0,
            total_n=100000.0,
            frictional_kn=60.0,
            residuary_kn=35.0,
            appendage_kn=3.0,
            air_kn=2.0,
            effective_power_kw=1000.0,
            effective_power_hp=1341.0,
            froude_number=0.35,
            reynolds_number=1e8,
            cf=0.002,
            cr=0.001,
            ct=0.003,
            form_factor=1.15,
            speed_kts=20.0,
            speed_ms=10.29,
        )
        data = results.to_dict()
        assert data["total_kn"] == 100.0
        assert "warnings" in data

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "total_kn": 150.0,
            "total_n": 150000.0,
            "frictional_kn": 90.0,
            "residuary_kn": 50.0,
            "appendage_kn": 5.0,
            "air_kn": 5.0,
            "effective_power_kw": 1500.0,
            "effective_power_hp": 2011.0,
            "froude_number": 0.40,
            "reynolds_number": 2e8,
            "cf": 0.0018,
            "cr": 0.0012,
            "ct": 0.0035,
            "form_factor": 1.20,
            "speed_kts": 25.0,
            "speed_ms": 12.86,
        }
        results = ResistanceResults.from_dict(data)
        assert results.total_kn == 150.0
        assert results.froude_number == 0.40


class TestResistanceCalculator:
    """Test ResistanceCalculator class."""

    def setup_method(self):
        """Set up calculator for tests."""
        self.calculator = ResistanceCalculator()
        # Standard test parameters (50m workboat)
        self.params = {
            "lwl": 50.0,
            "beam": 10.0,
            "draft": 2.5,
            "displacement_mt": 700.0,
            "wetted_surface": 600.0,
            "speed_kts": 15.0,
            "cb": 0.55,
        }

    def test_froude_number_calculation(self):
        """Test Froude number calculation."""
        # Fn = V / sqrt(g * L)
        speed_ms = 15.0 * 0.514444
        expected_fn = speed_ms / math.sqrt(GRAVITY * 50.0)

        results = self.calculator.calculate(**self.params)
        assert abs(results.froude_number - expected_fn) < 0.001

    def test_reynolds_number_calculation(self):
        """Test Reynolds number calculation."""
        # Rn = V * L / nu
        speed_ms = 15.0 * 0.514444
        expected_rn = (speed_ms * 50.0) / NU_SEAWATER

        results = self.calculator.calculate(**self.params)
        assert abs(results.reynolds_number - expected_rn) / expected_rn < 0.01

    def test_frictional_resistance_positive(self):
        """Test frictional resistance is positive."""
        results = self.calculator.calculate(**self.params)
        assert results.frictional_kn > 0

    def test_residuary_resistance_positive(self):
        """Test residuary resistance is positive."""
        results = self.calculator.calculate(**self.params)
        assert results.residuary_kn >= 0

    def test_total_resistance_positive(self):
        """Test total resistance is positive."""
        results = self.calculator.calculate(**self.params)
        assert results.total_kn > 0

    def test_total_equals_sum_of_components(self):
        """Test total resistance equals sum of components."""
        results = self.calculator.calculate(**self.params)
        component_sum = (
            results.frictional_kn +
            results.residuary_kn +
            results.appendage_kn +
            results.air_kn
        )
        assert abs(results.total_kn - component_sum) < 0.1

    def test_effective_power_calculation(self):
        """Test effective power calculation."""
        # Pe = Rt * V
        results = self.calculator.calculate(**self.params)
        expected_pe_kw = results.total_n * results.speed_ms / 1000.0
        assert abs(results.effective_power_kw - expected_pe_kw) < 0.1

    def test_effective_power_hp_conversion(self):
        """Test HP conversion."""
        results = self.calculator.calculate(**self.params)
        expected_hp = results.effective_power_kw * 1.34102
        assert abs(results.effective_power_hp - expected_hp) < 0.1

    def test_high_froude_warning(self):
        """Test warning for high Froude number (Fn > 0.5)."""
        params = self.params.copy()
        params["speed_kts"] = 30.0  # High speed
        results = self.calculator.calculate(**params)
        if results.froude_number > 0.5:
            assert any("froude" in w.lower() for w in results.warnings)

    def test_very_high_froude_warning(self):
        """Test warning for very high Froude number (Fn > 0.7)."""
        params = self.params.copy()
        params["speed_kts"] = 40.0  # Very high speed
        results = self.calculator.calculate(**params)
        if results.froude_number > 0.7:
            assert any("planing" in w.lower() for w in results.warnings)

    def test_cf_ittc57_formula(self):
        """Test ITTC-57 friction coefficient."""
        results = self.calculator.calculate(**self.params)
        # Cf should be small positive number
        assert 0.001 < results.cf < 0.01

    def test_form_factor_reasonable(self):
        """Test form factor is in reasonable range."""
        results = self.calculator.calculate(**self.params)
        # Typical range is 1.0 to 1.6
        assert 1.0 <= results.form_factor <= 1.6

    def test_invalid_dimensions_raises(self):
        """Test invalid dimensions raise ValueError."""
        with pytest.raises(ValueError):
            self.calculator.calculate(
                lwl=-50.0, beam=10.0, draft=2.5,
                displacement_mt=700.0, wetted_surface=600.0,
                speed_kts=15.0, cb=0.55
            )
        with pytest.raises(ValueError):
            self.calculator.calculate(
                lwl=50.0, beam=0, draft=2.5,
                displacement_mt=700.0, wetted_surface=600.0,
                speed_kts=15.0, cb=0.55
            )

    def test_invalid_hydrostatics_raises(self):
        """Test invalid hydrostatics values raise ValueError."""
        with pytest.raises(ValueError):
            self.calculator.calculate(
                lwl=50.0, beam=10.0, draft=2.5,
                displacement_mt=-100, wetted_surface=600.0,
                speed_kts=15.0, cb=0.55
            )
        with pytest.raises(ValueError):
            self.calculator.calculate(
                lwl=50.0, beam=10.0, draft=2.5,
                displacement_mt=700.0, wetted_surface=0,
                speed_kts=15.0, cb=0.55
            )

    def test_invalid_speed_raises(self):
        """Test invalid speed raises ValueError."""
        with pytest.raises(ValueError):
            self.calculator.calculate(
                lwl=50.0, beam=10.0, draft=2.5,
                displacement_mt=700.0, wetted_surface=600.0,
                speed_kts=0, cb=0.55
            )

    def test_invalid_cb_raises(self):
        """Test invalid block coefficient raises ValueError."""
        with pytest.raises(ValueError):
            self.calculator.calculate(
                lwl=50.0, beam=10.0, draft=2.5,
                displacement_mt=700.0, wetted_surface=600.0,
                speed_kts=15.0, cb=1.5  # Invalid Cb > 1
            )

    def test_speed_conversion(self):
        """Test speed conversion from knots to m/s."""
        results = self.calculator.calculate(**self.params)
        expected_ms = 15.0 * 0.514444
        assert abs(results.speed_ms - expected_ms) < 0.001

    def test_resistance_increases_with_speed(self):
        """Test resistance increases with speed."""
        slow = self.calculator.calculate(**{**self.params, "speed_kts": 10.0})
        fast = self.calculator.calculate(**{**self.params, "speed_kts": 20.0})
        assert fast.total_kn > slow.total_kn

    def test_resistance_increases_with_displacement(self):
        """Test resistance generally increases with displacement."""
        light = self.calculator.calculate(**{**self.params, "displacement_mt": 500.0})
        heavy = self.calculator.calculate(**{**self.params, "displacement_mt": 900.0})
        # Residuary resistance should increase (wave-making depends on displacement)
        assert heavy.residuary_kn >= light.residuary_kn * 0.8  # Some tolerance


class TestResistanceHelperFunction:
    """Test helper function."""

    def test_calculate_resistance_function(self):
        """Test convenience function."""
        results = calculate_resistance(
            lwl=50.0, beam=10.0, draft=2.5,
            displacement_mt=700.0, wetted_surface=600.0,
            speed_kts=15.0, cb=0.55
        )
        assert results.total_kn > 0
        assert isinstance(results, ResistanceResults)


class TestResistanceConstants:
    """Test module constants."""

    def test_inputs_defined(self):
        """Test RESISTANCE_INPUTS is defined."""
        assert len(RESISTANCE_INPUTS) > 0
        assert "hull.lwl" in RESISTANCE_INPUTS

    def test_outputs_defined(self):
        """Test RESISTANCE_OUTPUTS is defined."""
        assert len(RESISTANCE_OUTPUTS) > 0
        assert "resistance.total_kn" in RESISTANCE_OUTPUTS

    def test_physical_constants(self):
        """Test physical constants."""
        assert RHO_SEAWATER == 1025.0
        assert abs(NU_SEAWATER - 1.19e-6) < 1e-8
        assert GRAVITY == 9.81
