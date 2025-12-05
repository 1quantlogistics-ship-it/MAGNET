"""
MAGNET V1 Physics Module Tests (ALPHA)

Tests for hydrostatics, stability, and resistance calculations.
Includes validation against M48 vessel baseline.
"""

import pytest
import math
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physics.hydrostatics.displacement import (
    calculate_displacement,
    calculate_volume,
    calculate_wetted_surface_holtrop,
    calculate_wetted_surface_simple,
    calculate_waterplane_area,
    calculate_midship_area,
    calculate_tons_per_cm_immersion,
    SEAWATER_DENSITY,
)

from physics.hydrostatics.stability import (
    calculate_stability,
    calculate_GM,
    calculate_KB_morrish,
    calculate_BM_transverse,
    calculate_GZ_curve,
    check_IMO_A749_criteria,
    StabilityResult,
)

from physics.resistance.holtrop import (
    calculate_total_resistance,
    calculate_frictional_resistance,
    calculate_froude_number,
    calculate_reynolds_number,
    estimate_speed_power_curve,
    knots_to_ms,
    ResistanceResult,
)


# =============================================================================
# M48 BASELINE DATA
# =============================================================================

# M48 vessel parameters (48m semi-displacement catamaran)
M48_PARAMS = {
    "length_overall": 48.0,
    "length_waterline": 45.0,
    "beam": 12.8,  # Overall beam
    "draft": 2.1,
    "depth": 4.5,
    "block_coefficient": 0.45,
    "prismatic_coefficient": 0.65,
    "midship_coefficient": 0.85,
    "waterplane_coefficient": 0.78,
    "hull_type": "semi_displacement",
}

# Expected M48 values (approximate)
M48_EXPECTED = {
    "displacement_tonnes": 550,  # Approximate
    "wetted_surface_m2": 600,    # Approximate
    "speed_design_kts": 28,
}


# =============================================================================
# DISPLACEMENT TESTS
# =============================================================================

class TestDisplacement:
    """Tests for displacement calculations."""

    def test_calculate_volume(self):
        """Test volume calculation."""
        volume = calculate_volume(
            length_wl=45.0,
            beam=12.8,
            draft=2.1,
            block_coefficient=0.45
        )
        # V = L × B × T × Cb = 45 × 12.8 × 2.1 × 0.45 ≈ 544 m³
        assert 500 < volume < 600
        assert abs(volume - 544.32) < 1.0

    def test_calculate_displacement(self):
        """Test displacement calculation."""
        displacement = calculate_displacement(
            length_wl=45.0,
            beam=12.8,
            draft=2.1,
            block_coefficient=0.45
        )
        # Δ = ρ × V ≈ 1.025 × 544 ≈ 558 tonnes
        assert 500 < displacement < 650
        assert abs(displacement - 557.93) < 5.0

    def test_displacement_scales_with_draft(self):
        """Test that displacement scales linearly with draft."""
        base = calculate_displacement(45, 12.8, 2.0, 0.45)
        double = calculate_displacement(45, 12.8, 4.0, 0.45)
        assert abs(double / base - 2.0) < 0.01

    def test_wetted_surface_holtrop(self):
        """Test wetted surface using Holtrop method."""
        S = calculate_wetted_surface_holtrop(
            length_wl=45.0,
            beam=12.8,
            draft=2.1,
            block_coefficient=0.45,
            midship_coefficient=0.85,
            waterplane_coefficient=0.78
        )
        # S should be reasonable for a 45m vessel (400-800 m²)
        assert 400 < S < 800

    def test_wetted_surface_simple(self):
        """Test simplified wetted surface calculation."""
        S = calculate_wetted_surface_simple(
            length_wl=45.0,
            beam=12.8,
            draft=2.1,
            block_coefficient=0.45,
            midship_coefficient=0.85
        )
        # Simple method gives lower estimate; should be positive and reasonable
        assert 200 < S < 800

    def test_waterplane_area(self):
        """Test waterplane area calculation."""
        Awp = calculate_waterplane_area(45.0, 12.8, 0.78)
        # Awp = L × B × Cwp = 45 × 12.8 × 0.78 ≈ 449 m²
        assert abs(Awp - 449.28) < 1.0

    def test_midship_area(self):
        """Test midship section area calculation."""
        Am = calculate_midship_area(12.8, 2.1, 0.85)
        # Am = B × T × Cm = 12.8 × 2.1 × 0.85 ≈ 22.85 m²
        assert abs(Am - 22.848) < 0.1

    def test_tons_per_cm_immersion(self):
        """Test TPC calculation."""
        TPC = calculate_tons_per_cm_immersion(45.0, 12.8, 0.78)
        # TPC = Awp × ρ / 100 ≈ 449 × 1.025 / 100 ≈ 4.6 t/cm
        assert 4.0 < TPC < 5.0


# =============================================================================
# STABILITY TESTS
# =============================================================================

class TestStability:
    """Tests for stability calculations."""

    def test_calculate_KB_morrish(self):
        """Test KB calculation using Morrish formula."""
        KB = calculate_KB_morrish(
            draft=2.1,
            block_coefficient=0.45,
            waterplane_coefficient=0.78
        )
        # KB should be less than draft
        assert 0 < KB < 2.1
        # Typical KB/T ratio is 0.5-0.7
        assert 0.5 < KB / 2.1 < 0.7

    def test_calculate_BM_transverse(self):
        """Test BM calculation."""
        BM = calculate_BM_transverse(
            length_wl=45.0,
            beam=12.8,
            draft=2.1,
            block_coefficient=0.45,
            waterplane_coefficient=0.78
        )
        # BM should be positive and reasonable
        assert BM > 0
        # For wide beamy vessels, BM can be large
        assert BM < 50

    def test_calculate_GM_positive(self):
        """Test GM calculation for stable vessel."""
        KB = 1.0
        BM = 5.0
        KG = 3.0
        GM = calculate_GM(KB, BM, KG)
        # GM = KB + BM - KG = 1 + 5 - 3 = 3
        assert GM == 3.0

    def test_calculate_GM_negative(self):
        """Test GM calculation for unstable vessel."""
        KB = 1.0
        BM = 2.0
        KG = 4.0
        GM = calculate_GM(KB, BM, KG)
        # GM = KB + BM - KG = 1 + 2 - 4 = -1
        assert GM == -1.0

    def test_calculate_GZ_curve(self):
        """Test GZ curve generation."""
        angles, gz_values = calculate_GZ_curve(GM=2.0, beam=12.8, max_angle=60)

        # Should have multiple points
        assert len(angles) > 5
        assert len(angles) == len(gz_values)

        # GZ at 0 should be 0
        assert abs(gz_values[0]) < 0.01

        # GZ should increase with angle (for stable vessel)
        assert gz_values[1] > gz_values[0]

    def test_calculate_stability_result(self):
        """Test comprehensive stability calculation."""
        result = calculate_stability(
            length_wl=45.0,
            beam=12.8,
            draft=2.1,
            depth=4.5,
            block_coefficient=0.45,
            waterplane_coefficient=0.78,
            hull_type="semi_displacement"
        )

        assert isinstance(result, StabilityResult)
        assert result.GM > 0  # Should be stable
        assert result.displacement > 0
        assert len(result.heel_angles) > 0
        assert len(result.gz_values) > 0
        assert result.max_gz > 0

    def test_imo_criteria_check(self):
        """Test IMO A.749 criteria checking."""
        # Create a stable vessel GZ curve
        GM = 2.0
        angles, gz_values = calculate_GZ_curve(GM, beam=12.8, max_angle=90)

        passed, details = check_IMO_A749_criteria(GM, gz_values, angles)

        # GM should pass (>= 0.15 m)
        assert "gm" in details
        assert details["gm"]["passed"]

        # Should have all criteria checked
        assert "area_0_30" in details
        assert "area_0_40" in details
        assert "gz_at_30" in details

    def test_stability_is_stable_method(self):
        """Test is_stable() method."""
        result = calculate_stability(
            length_wl=45.0,
            beam=12.8,
            draft=2.1,
            depth=4.5,
            block_coefficient=0.45,
            waterplane_coefficient=0.78
        )

        # Wide beam vessel should be stable
        assert result.is_stable()


# =============================================================================
# RESISTANCE TESTS
# =============================================================================

class TestResistance:
    """Tests for resistance calculations."""

    def test_knots_to_ms(self):
        """Test speed conversion."""
        assert abs(knots_to_ms(10) - 5.144) < 0.01
        assert abs(knots_to_ms(20) - 10.288) < 0.01

    def test_froude_number(self):
        """Test Froude number calculation."""
        Fn = calculate_froude_number(speed_ms=10.0, length_wl=45.0)
        # Fn = V / sqrt(g × L) = 10 / sqrt(9.81 × 45) ≈ 0.476
        assert abs(Fn - 0.476) < 0.01

    def test_reynolds_number(self):
        """Test Reynolds number calculation."""
        Rn = calculate_reynolds_number(speed_ms=10.0, length_wl=45.0)
        # Rn = V × L / ν ≈ 10 × 45 / 1.19e-6 ≈ 3.78e8
        assert 3e8 < Rn < 4e8

    def test_frictional_resistance(self):
        """Test frictional resistance calculation."""
        RF, Cf = calculate_frictional_resistance(
            speed_ms=10.0,
            length_wl=45.0,
            wetted_surface=600.0
        )

        # RF should be positive
        assert RF > 0

        # Cf should be in typical range (0.001 - 0.005)
        assert 0.001 < Cf < 0.005

    def test_total_resistance(self):
        """Test total resistance calculation."""
        result = calculate_total_resistance(
            speed_kts=20.0,
            length_wl=45.0,
            beam=12.8,
            draft=2.1,
            block_coefficient=0.45,
            prismatic_coefficient=0.65,
            waterplane_coefficient=0.78,
            wetted_surface=600.0
        )

        assert isinstance(result, ResistanceResult)
        assert result.total_resistance > 0
        assert result.effective_power > 0
        assert result.delivered_power > result.effective_power

    def test_resistance_increases_with_speed(self):
        """Test that resistance increases with speed."""
        r1 = calculate_total_resistance(15, 45, 12.8, 2.1, 0.45, 0.65, 0.78, 600)
        r2 = calculate_total_resistance(25, 45, 12.8, 2.1, 0.45, 0.65, 0.78, 600)

        assert r2.total_resistance > r1.total_resistance
        assert r2.effective_power > r1.effective_power

    def test_speed_power_curve(self):
        """Test speed-power curve generation."""
        curve = estimate_speed_power_curve(
            length_wl=45.0,
            beam=12.8,
            draft=2.1,
            block_coefficient=0.45,
            prismatic_coefficient=0.65,
            waterplane_coefficient=0.78,
            wetted_surface=600.0,
            min_speed_kts=10,
            max_speed_kts=30,
            speed_step_kts=5
        )

        # Should have multiple points
        assert len(curve) >= 4

        # Power should increase with speed
        powers = [r.delivered_power for r in curve]
        assert all(p1 < p2 for p1, p2 in zip(powers[:-1], powers[1:]))


# =============================================================================
# M48 BASELINE VALIDATION
# =============================================================================

class TestM48Baseline:
    """Validation tests against M48 vessel baseline."""

    def test_m48_displacement(self):
        """Test M48 displacement calculation."""
        displacement = calculate_displacement(
            M48_PARAMS["length_waterline"],
            M48_PARAMS["beam"],
            M48_PARAMS["draft"],
            M48_PARAMS["block_coefficient"]
        )

        # Should be within 20% of expected
        expected = M48_EXPECTED["displacement_tonnes"]
        assert abs(displacement - expected) / expected < 0.20

    def test_m48_stability(self):
        """Test M48 stability is positive."""
        result = calculate_stability(
            length_wl=M48_PARAMS["length_waterline"],
            beam=M48_PARAMS["beam"],
            draft=M48_PARAMS["draft"],
            depth=M48_PARAMS["depth"],
            block_coefficient=M48_PARAMS["block_coefficient"],
            waterplane_coefficient=M48_PARAMS["waterplane_coefficient"],
            hull_type=M48_PARAMS["hull_type"]
        )

        # M48 should be stable
        assert result.GM > 0.15  # IMO minimum
        assert result.is_stable()

    def test_m48_resistance_at_design_speed(self):
        """Test M48 resistance at design speed."""
        # Calculate wetted surface first
        S = calculate_wetted_surface_holtrop(
            M48_PARAMS["length_waterline"],
            M48_PARAMS["beam"],
            M48_PARAMS["draft"],
            M48_PARAMS["block_coefficient"],
            M48_PARAMS["midship_coefficient"],
            M48_PARAMS["waterplane_coefficient"]
        )

        result = calculate_total_resistance(
            speed_kts=M48_EXPECTED["speed_design_kts"],
            length_wl=M48_PARAMS["length_waterline"],
            beam=M48_PARAMS["beam"],
            draft=M48_PARAMS["draft"],
            block_coefficient=M48_PARAMS["block_coefficient"],
            prismatic_coefficient=M48_PARAMS["prismatic_coefficient"],
            waterplane_coefficient=M48_PARAMS["waterplane_coefficient"],
            wetted_surface=S
        )

        # M48 at 28 kts is a fast semi-displacement vessel
        # Froude number Fn = V/sqrt(gL) = 14.4/sqrt(9.81*45) ≈ 0.69
        # This is in the high-speed regime (Fn > 0.4)
        assert 0.5 < result.froude_number < 0.8

        # Power should be in reasonable range for a 500-600 tonne vessel at 28 kts
        # For high-speed vessels, expect 2000-8000 kW
        power_kw = result.delivered_power / 1000
        assert 1000 < power_kw < 15000

    def test_m48_froude_number(self):
        """Test M48 Froude number at design speed."""
        speed_ms = knots_to_ms(28)
        Fn = calculate_froude_number(speed_ms, M48_PARAMS["length_waterline"])

        # M48 at 28 kts is high-speed semi-displacement
        # Fn = 14.4 / sqrt(9.81 * 45) ≈ 0.69
        assert 0.60 < Fn < 0.75


# =============================================================================
# EDGE CASES AND ERROR HANDLING
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_zero_speed(self):
        """Test resistance at zero speed."""
        result = calculate_total_resistance(0, 45, 12.8, 2.1, 0.45, 0.65, 0.78, 600)
        assert result.total_resistance == 0 or result.total_resistance < 1  # Numerical precision

    def test_very_low_speed(self):
        """Test resistance at very low speed."""
        result = calculate_total_resistance(1, 45, 12.8, 2.1, 0.45, 0.65, 0.78, 600)
        assert result.total_resistance >= 0

    def test_minimum_vessel(self):
        """Test calculations for minimum size vessel."""
        result = calculate_stability(
            length_wl=10.0,
            beam=3.0,
            draft=1.0,
            depth=2.0,
            block_coefficient=0.45,
            waterplane_coefficient=0.78
        )
        assert result.displacement > 0
        assert result.GM > 0  # Should still be stable

    def test_large_vessel(self):
        """Test calculations for large vessel."""
        result = calculate_stability(
            length_wl=200.0,
            beam=30.0,
            draft=10.0,
            depth=18.0,
            block_coefficient=0.75,
            waterplane_coefficient=0.85
        )
        assert result.displacement > 10000  # Should be substantial
        assert result.GM > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
