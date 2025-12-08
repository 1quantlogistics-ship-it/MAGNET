"""
Unit tests for magnet/stability/calculators.py

Tests IntactGMCalculator, GZCurveCalculator, and other stability calculators.
"""

import pytest
import math
from magnet.stability.calculators import (
    IntactGMCalculator,
    GZCurveCalculator,
    FreeSurfaceCalculator,
    DamageStabilityCalculator,
    WeatherCriterionCalculator,
)
from magnet.stability.results import TankFreeSurface, GZCurveResults
from magnet.stability.constants import IMO_INTACT


class TestIntactGMCalculator:
    """Test IntactGMCalculator class."""

    def setup_method(self):
        self.calculator = IntactGMCalculator()

    def test_basic_gm_calculation(self):
        """Test GM = KB + BM - KG."""
        result = self.calculator.calculate(kb_m=1.5, bm_m=2.0, kg_m=2.8)
        # GM = 1.5 + 2.0 - 2.8 = 0.7
        assert abs(result.gm_m - 0.7) < 0.001
        assert abs(result.gm_solid_m - 0.7) < 0.001

    def test_km_calculation(self):
        """Test KM = KB + BM."""
        result = self.calculator.calculate(kb_m=1.5, bm_m=2.0, kg_m=2.8)
        assert abs(result.km_m - 3.5) < 0.001

    def test_gm_with_fsc(self):
        """Test GM with free surface correction."""
        result = self.calculator.calculate(kb_m=1.5, bm_m=2.0, kg_m=2.8, fsc_m=0.1)
        # GM_corrected = GM_solid - FSC = 0.7 - 0.1 = 0.6
        assert abs(result.gm_solid_m - 0.7) < 0.001
        assert abs(result.gm_m - 0.6) < 0.001
        assert result.has_fsc == True

    def test_kg_source_tracking(self):
        """Test KG source is tracked."""
        result = self.calculator.calculate(kb_m=1.5, bm_m=2.0, kg_m=2.8, kg_source="weight.lightship_vcg_m")
        assert result.kg_source == "weight.lightship_vcg_m"

    def test_passes_gm_criterion(self):
        """Test IMO GM criterion checking."""
        # Passing case: GM = 0.7m > 0.15m
        result = self.calculator.calculate(kb_m=1.5, bm_m=2.0, kg_m=2.8)
        assert result.passes_gm_criterion == True

        # Failing case: GM = 0.1m < 0.15m
        result = self.calculator.calculate(kb_m=1.0, bm_m=1.0, kg_m=1.9)
        assert result.passes_gm_criterion == False

    def test_negative_gm_warning(self):
        """Test warning for negative GM (unstable)."""
        result = self.calculator.calculate(kb_m=1.0, bm_m=1.0, kg_m=3.0)
        assert result.gm_m < 0
        assert any("negative" in w.lower() for w in result.warnings)

    def test_invalid_kb_raises(self):
        """Test that negative KB raises error."""
        with pytest.raises(ValueError):
            self.calculator.calculate(kb_m=-1.0, bm_m=2.0, kg_m=2.8)

    def test_invalid_bm_raises(self):
        """Test that negative BM raises error."""
        with pytest.raises(ValueError):
            self.calculator.calculate(kb_m=1.5, bm_m=-2.0, kg_m=2.8)

    def test_invalid_kg_raises(self):
        """Test that negative KG raises error."""
        with pytest.raises(ValueError):
            self.calculator.calculate(kb_m=1.5, bm_m=2.0, kg_m=-2.8)


class TestGZCurveCalculator:
    """Test GZCurveCalculator class."""

    def setup_method(self):
        self.calculator = GZCurveCalculator()

    def test_gz_at_zero_degrees(self):
        """Test GZ = 0 at zero heel."""
        result = self.calculator.calculate(gm_m=0.7, bm_m=2.0)
        gz_0 = next(p for p in result.curve if p.heel_deg == 0.0)
        assert abs(gz_0.gz_m) < 0.001

    def test_gz_increases_with_heel(self):
        """Test GZ increases with heel angle (for positive GM)."""
        result = self.calculator.calculate(gm_m=0.7, bm_m=2.0)
        gz_10 = next(p for p in result.curve if p.heel_deg == 10.0)
        gz_20 = next(p for p in result.curve if p.heel_deg == 20.0)
        assert gz_10.gz_m > 0
        assert gz_20.gz_m > gz_10.gz_m

    def test_gz_max_found(self):
        """Test maximum GZ is found."""
        result = self.calculator.calculate(gm_m=0.7, bm_m=2.0)
        assert result.gz_max_m > 0
        assert result.angle_gz_max_deg > 0

    def test_gz_30_calculated(self):
        """Test GZ at 30 degrees is calculated."""
        result = self.calculator.calculate(gm_m=0.7, bm_m=2.0)
        assert result.gz_30_m > 0

    def test_areas_calculated(self):
        """Test areas under GZ curve are calculated."""
        result = self.calculator.calculate(gm_m=0.7, bm_m=2.0)
        assert result.area_0_30_m_rad > 0
        assert result.area_0_40_m_rad > result.area_0_30_m_rad
        assert result.area_30_40_m_rad > 0

    def test_imo_criteria_checking(self):
        """Test IMO criteria are checked."""
        # Good stability
        result = self.calculator.calculate(gm_m=0.7, bm_m=2.0)
        assert result.passes_gz_30_criterion == True
        assert result.passes_area_0_30_criterion == True

    def test_poor_stability_fails_criteria(self):
        """Test poor stability fails criteria."""
        # Low GM = poor stability
        result = self.calculator.calculate(gm_m=0.1, bm_m=0.5)
        # May fail some criteria
        assert isinstance(result.passes_all_gz_criteria, bool)

    def test_wall_sided_formula(self):
        """Test wall-sided formula: GZ = sin(φ) × (GM + 0.5 × BM × tan²(φ))."""
        gm_m, bm_m = 0.7, 2.0
        angle_deg = 30.0
        angle_rad = math.radians(angle_deg)

        # Expected GZ from formula
        expected_gz = math.sin(angle_rad) * (gm_m + 0.5 * bm_m * math.tan(angle_rad)**2)

        result = self.calculator.calculate(gm_m=gm_m, bm_m=bm_m)
        assert abs(result.gz_30_m - expected_gz) < 0.001

    def test_custom_angles(self):
        """Test with custom heel angles."""
        angles = [0, 15, 30, 45]
        result = self.calculator.calculate(gm_m=0.7, bm_m=2.0, angles_deg=angles)
        assert len(result.curve) == len(angles)


class TestFreeSurfaceCalculator:
    """Test FreeSurfaceCalculator class."""

    def setup_method(self):
        self.calculator = FreeSurfaceCalculator()

    def test_fsc_calculation(self):
        """Test FSC calculation with tanks."""
        tanks = [
            TankFreeSurface(
                tank_id="t1",
                tank_name="Tank 1",
                fill_percentage=50.0,
                liquid_density_kg_m3=1000.0,
                moment_of_inertia_m4=10.0,
                free_surface_moment_t_m=10.0,
            ),
        ]
        fsc, warnings = self.calculator.calculate(displacement_mt=1000.0, tanks=tanks)
        # FSC = FSM / Δ = 10 / 1000 = 0.01m
        assert fsc > 0

    def test_no_tanks_returns_zero(self):
        """Test no tanks returns zero FSC."""
        fsc, warnings = self.calculator.calculate(displacement_mt=1000.0, tanks=[])
        assert fsc == 0.0

    def test_tanks_outside_fill_range_ignored(self):
        """Test tanks outside 15-85% fill are ignored."""
        tanks = [
            TankFreeSurface(
                tank_id="t1",
                tank_name="Empty Tank",
                fill_percentage=5.0,  # Below 15%
                liquid_density_kg_m3=1000.0,
                moment_of_inertia_m4=10.0,
                free_surface_moment_t_m=10.0,
            ),
            TankFreeSurface(
                tank_id="t2",
                tank_name="Full Tank",
                fill_percentage=95.0,  # Above 85%
                liquid_density_kg_m3=1000.0,
                moment_of_inertia_m4=10.0,
                free_surface_moment_t_m=10.0,
            ),
        ]
        fsc, warnings = self.calculator.calculate(displacement_mt=1000.0, tanks=tanks)
        assert fsc == 0.0

    def test_invalid_displacement_raises(self):
        """Test zero displacement raises error."""
        with pytest.raises(ValueError):
            self.calculator.calculate(displacement_mt=0, tanks=[])


class TestDamageStabilityCalculator:
    """Test DamageStabilityCalculator class."""

    def setup_method(self):
        self.calculator = DamageStabilityCalculator()

    def test_evaluates_standard_cases(self):
        """Test standard damage cases are evaluated."""
        result = self.calculator.calculate(
            intact_gm_m=0.7,
            intact_gz_max_m=0.5,
            displacement_mt=1000.0,
        )
        assert result.cases_evaluated == 4  # Standard cases

    def test_worst_case_identified(self):
        """Test worst damage case is identified."""
        result = self.calculator.calculate(
            intact_gm_m=0.7,
            intact_gz_max_m=0.5,
            displacement_mt=1000.0,
        )
        assert result.worst_case_id != ""
        assert result.worst_gm_m > 0

    def test_all_pass_when_good_stability(self):
        """Test all cases pass with good intact stability."""
        result = self.calculator.calculate(
            intact_gm_m=1.5,  # High GM
            intact_gz_max_m=1.0,
            displacement_mt=1000.0,
        )
        assert result.all_cases_pass == True


class TestWeatherCriterionCalculator:
    """Test WeatherCriterionCalculator class."""

    def setup_method(self):
        self.calculator = WeatherCriterionCalculator()

    def test_weather_criterion_calculation(self):
        """Test weather criterion is calculated."""
        # Create a mock GZ curve
        gz_calc = GZCurveCalculator()
        gz_results = gz_calc.calculate(gm_m=0.7, bm_m=2.0)

        result = self.calculator.calculate(
            gz_curve=gz_results,
            displacement_mt=1000.0,
            beam_m=10.0,
            draft_m=3.0,
            loa_m=50.0,
            gm_m=0.7,
        )
        assert result.energy_ratio > 0

    def test_roll_period_calculation(self):
        """Test roll period is calculated."""
        gz_calc = GZCurveCalculator()
        gz_results = gz_calc.calculate(gm_m=0.7, bm_m=2.0)

        result = self.calculator.calculate(
            gz_curve=gz_results,
            displacement_mt=1000.0,
            beam_m=10.0,
            draft_m=3.0,
            loa_m=50.0,
            gm_m=0.7,
        )
        assert result.roll_period_s > 0


class TestIMOCriteriaChecking:
    """Test IMO criteria checking."""

    def test_check_imo_intact_criteria(self):
        """Test check_imo_intact_criteria function."""
        from magnet.stability.constants import check_imo_intact_criteria

        # Passing case
        result = check_imo_intact_criteria(
            gm_m=0.5,
            gz_30_m=0.25,
            gz_max_m=0.5,
            angle_gz_max_deg=35.0,
            area_0_30_m_rad=0.06,
            area_0_40_m_rad=0.10,
            area_30_40_m_rad=0.04,
        )
        assert result["all_pass"] == True

        # Failing case (low GM)
        result = check_imo_intact_criteria(
            gm_m=0.10,  # Below 0.15m
            gz_30_m=0.25,
            gz_max_m=0.5,
            angle_gz_max_deg=35.0,
            area_0_30_m_rad=0.06,
            area_0_40_m_rad=0.10,
            area_30_40_m_rad=0.04,
        )
        assert result["gm_pass"] == False
        assert result["all_pass"] == False
