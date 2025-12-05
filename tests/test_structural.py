"""
Tests for structural scantlings module.

Tests:
- Material properties and HAZ factors
- Design pressure calculations
- Plate thickness calculations
- Stiffener section modulus
- M48 baseline validation
"""

import pytest
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physics.structural.materials import (
    AluminumAlloy,
    MaterialProperties,
    ALLOWED_ALLOYS,
    PROHIBITED_ALLOYS,
    get_alloy_properties,
    get_haz_factor,
    validate_material_for_location,
    calculate_allowable_stress,
    generate_material_report,
)
from physics.structural.pressure import (
    PressureZone,
    PressureResult,
    calculate_hydrostatic_pressure,
    calculate_vertical_acceleration,
    calculate_deadrise_factor,
    calculate_slamming_pressure,
    calculate_design_pressure,
    calculate_all_zone_pressures,
    generate_pressure_report,
)
from physics.structural.plating import (
    PlatingResult,
    PlatingSchedule,
    BoundaryCondition,
    calculate_minimum_thickness,
    calculate_plate_thickness,
    quantize_to_commercial,
    generate_plating_result,
    generate_plating_schedule,
    generate_plating_report,
)
from physics.structural.stiffeners import (
    StiffenerType,
    StiffenerProfile,
    StiffenerResult,
    STANDARD_PROFILES,
    calculate_frame_spacing,
    calculate_stiffener_section_modulus,
    select_stiffener_profile,
    calculate_stiffener_result,
    calculate_all_stiffeners,
    generate_stiffener_report,
)


# ============================================================================
# M48 Vessel Baseline Parameters
# ============================================================================
M48_LENGTH_WL = 45.0        # m
M48_BEAM = 12.8             # m
M48_DEPTH = 4.5             # m
M48_DRAFT = 2.1             # m
M48_DISPLACEMENT = 420.0    # tonnes
M48_SPEED = 28.0            # knots
M48_DEADRISE = 20.0         # degrees (semi-displacement)


class TestMaterials:
    """Tests for material properties."""

    def test_allowed_alloys_exist(self):
        """Test that allowed alloys have properties."""
        for alloy in ALLOWED_ALLOYS:
            props = get_alloy_properties(alloy)
            assert props is not None
            assert props.yield_strength > 0
            assert props.primary_structure_allowed or props.secondary_structure_allowed

    def test_prohibited_alloys_flagged(self):
        """Test that prohibited alloys are flagged."""
        for alloy in PROHIBITED_ALLOYS:
            props = get_alloy_properties(alloy)
            assert not props.primary_structure_allowed
            assert not props.secondary_structure_allowed

    def test_haz_factor_range(self):
        """Test HAZ factors are in valid range."""
        for alloy in AluminumAlloy:
            haz = get_haz_factor(alloy)
            assert 0.0 < haz <= 1.0

    def test_5083_h116_properties(self):
        """Test 5083-H116 properties match ABS data."""
        props = get_alloy_properties(AluminumAlloy.AL_5083_H116)

        # ABS HSNC values
        assert abs(props.yield_strength - 215.0) < 5.0
        assert abs(props.tensile_strength - 303.0) < 10.0
        assert props.primary_structure_allowed
        assert 0.70 < props.haz_factor < 0.85

    def test_6061_prohibited(self):
        """Test 6061-T6 is properly prohibited."""
        props = get_alloy_properties(AluminumAlloy.AL_6061_T6)

        assert not props.primary_structure_allowed
        assert not props.secondary_structure_allowed
        assert props.haz_factor < 0.35  # Severe HAZ degradation

    def test_material_validation(self):
        """Test material validation logic."""
        # Should pass - 5083 for primary
        valid, msg = validate_material_for_location(
            AluminumAlloy.AL_5083_H116,
            is_primary_structure=True
        )
        assert valid

        # Should fail - 6061 prohibited
        valid, msg = validate_material_for_location(
            AluminumAlloy.AL_6061_T6,
            is_primary_structure=True
        )
        assert not valid
        assert "PROHIBITED" in msg

    def test_allowable_stress_calculation(self):
        """Test allowable stress calculation."""
        # Parent metal
        sigma_parent = calculate_allowable_stress(
            AluminumAlloy.AL_5083_H116,
            in_haz=False
        )
        # 0.6 × 215 = 129 MPa
        assert 125 < sigma_parent < 135

        # HAZ
        sigma_haz = calculate_allowable_stress(
            AluminumAlloy.AL_5083_H116,
            in_haz=True
        )
        assert sigma_haz < sigma_parent

    def test_material_report_generation(self):
        """Test material report generation."""
        report = generate_material_report(AluminumAlloy.AL_5083_H116)

        assert "5083-H116" in report
        assert "APPROVED" in report
        assert "HAZ" in report


class TestPressure:
    """Tests for pressure calculations."""

    def test_hydrostatic_pressure(self):
        """Test hydrostatic pressure at draft."""
        # At waterline (z = draft), pressure = 0
        p_wl = calculate_hydrostatic_pressure(draft=2.1, position_z=2.1)
        assert p_wl == 0.0

        # At baseline (z = 0)
        p_baseline = calculate_hydrostatic_pressure(draft=2.1, position_z=0.0)
        # ρgh = 1.025 × 9.81 × 2.1 ≈ 21.1 kN/m²
        assert 20 < p_baseline < 22

    def test_vertical_acceleration(self):
        """Test vertical acceleration calculation."""
        n_cg = calculate_vertical_acceleration(
            length_wl=M48_LENGTH_WL,
            beam=M48_BEAM,
            draft=M48_DRAFT,
            speed_kts=M48_SPEED,
            displacement=M48_DISPLACEMENT,
        )

        # Should be positive and reasonable for high-speed craft
        assert 1.0 <= n_cg <= 5.0

    def test_deadrise_factor(self):
        """Test deadrise angle factor."""
        # Low deadrise (flat bottom) = higher slamming
        k_flat = calculate_deadrise_factor(5.0)
        assert k_flat == 1.0

        # High deadrise = lower slamming
        k_vee = calculate_deadrise_factor(25.0)
        assert k_vee < 0.7

        # Very high deadrise (deep V)
        k_deep = calculate_deadrise_factor(50.0)
        assert k_deep < 0.4

    def test_slamming_pressure(self):
        """Test slamming pressure calculation."""
        p_slam, factors = calculate_slamming_pressure(
            displacement=M48_DISPLACEMENT,
            length_wl=M48_LENGTH_WL,
            beam=M48_BEAM,
            draft=M48_DRAFT,
            speed_kts=M48_SPEED,
            position_x=0.1 * M48_LENGTH_WL,  # Forward
            deadrise_angle=M48_DEADRISE,
        )

        # Forward bottom should have minimum slamming per ABS
        assert p_slam >= 25  # kN/m² minimum per ABS HSNC

        # Factors should be positive
        assert factors["n1"] > 0
        assert factors["n_cg"] >= 1.0

    def test_design_pressure_by_zone(self):
        """Test design pressure varies by zone."""
        pressure_fwd = calculate_design_pressure(
            zone=PressureZone.BOTTOM_FORWARD,
            displacement=M48_DISPLACEMENT,
            length_wl=M48_LENGTH_WL,
            beam=M48_BEAM,
            draft=M48_DRAFT,
            depth=M48_DEPTH,
            speed_kts=M48_SPEED,
            deadrise_angle=M48_DEADRISE,
        )

        pressure_aft = calculate_design_pressure(
            zone=PressureZone.BOTTOM_AFT,
            displacement=M48_DISPLACEMENT,
            length_wl=M48_LENGTH_WL,
            beam=M48_BEAM,
            draft=M48_DRAFT,
            depth=M48_DEPTH,
            speed_kts=M48_SPEED,
            deadrise_angle=M48_DEADRISE,
        )

        # Forward should have higher pressure than aft
        assert pressure_fwd.design_pressure > pressure_aft.design_pressure

    def test_all_zone_pressures(self):
        """Test calculating pressures for all zones."""
        results = calculate_all_zone_pressures(
            displacement=M48_DISPLACEMENT,
            length_wl=M48_LENGTH_WL,
            beam=M48_BEAM,
            draft=M48_DRAFT,
            depth=M48_DEPTH,
            speed_kts=M48_SPEED,
            deadrise_angle=M48_DEADRISE,
        )

        # Should have results for multiple zones
        assert len(results) >= 6

        # All pressures should be positive
        for zone, result in results.items():
            assert result.design_pressure > 0

    def test_pressure_report_generation(self):
        """Test pressure report generation."""
        results = calculate_all_zone_pressures(
            displacement=M48_DISPLACEMENT,
            length_wl=M48_LENGTH_WL,
            beam=M48_BEAM,
            draft=M48_DRAFT,
            depth=M48_DEPTH,
            speed_kts=M48_SPEED,
        )

        report = generate_pressure_report(results)
        assert "DESIGN PRESSURE" in report
        assert "bottom" in report.lower()


class TestPlating:
    """Tests for plate thickness calculations."""

    def test_minimum_thickness(self):
        """Test minimum thickness calculation."""
        t_min = calculate_minimum_thickness(
            zone=PressureZone.BOTTOM_FORWARD,
            length_wl=M48_LENGTH_WL,
        )

        # Should be at least 4mm (ABS absolute minimum)
        assert t_min >= 4.0

        # Forward bottom should be thicker than deck
        t_min_deck = calculate_minimum_thickness(
            zone=PressureZone.DECK_WEATHER,
            length_wl=M48_LENGTH_WL,
        )
        assert t_min > t_min_deck

    def test_plate_thickness_calculation(self):
        """Test plate thickness formula."""
        t_required, formula, notes = calculate_plate_thickness(
            design_pressure=60.0,  # kN/m²
            stiffener_spacing=400.0,  # mm
            alloy=AluminumAlloy.AL_5083_H116,
        )

        # Should be reasonable thickness
        assert 4.0 < t_required < 15.0

        # Formula should contain key terms
        assert "σ_a" in formula

    def test_commercial_quantization(self):
        """Test rounding to commercial sizes."""
        assert quantize_to_commercial(5.2) == 5.5
        assert quantize_to_commercial(6.1) == 6.5
        assert quantize_to_commercial(8.0) == 8.0
        assert quantize_to_commercial(7.5) == 8.0

    def test_plating_result_compliance(self):
        """Test plating result compliance checking."""
        pressure_result = PressureResult(
            zone="bottom_forward",
            hydrostatic_pressure=20.0,
            slamming_pressure=80.0,
            design_pressure=80.0,
            service_factor_n1=0.85,
            acceleration_factor_ncg=2.0,
            deadrise_factor=0.7,
            area_factor=1.0,
            velocity_factor=3.0,
            position_x=0.1,
            position_z=0.0,
            rule_reference="ABS HSNC",
        )

        result = generate_plating_result(
            zone=PressureZone.BOTTOM_FORWARD,
            pressure_result=pressure_result,
            stiffener_spacing=400.0,
            length_wl=M48_LENGTH_WL,
        )

        # Should be compliant with commercial size
        assert result.is_compliant
        assert result.proposed_thickness >= result.required_thickness
        assert result.proposed_thickness >= result.minimum_thickness

    def test_plating_schedule_generation(self):
        """Test complete plating schedule."""
        pressures = calculate_all_zone_pressures(
            displacement=M48_DISPLACEMENT,
            length_wl=M48_LENGTH_WL,
            beam=M48_BEAM,
            draft=M48_DRAFT,
            depth=M48_DEPTH,
            speed_kts=M48_SPEED,
        )

        schedule = generate_plating_schedule(
            pressure_results=pressures,
            stiffener_spacing=400.0,
            frame_spacing=500.0,
            length_wl=M48_LENGTH_WL,
            beam=M48_BEAM,
            depth=M48_DEPTH,
        )

        # Should have zone results
        assert len(schedule.zones) > 0

        # Bottom should be thicker than deck
        assert schedule.bottom_thickness >= schedule.deck_thickness

        # Weight should be positive
        assert schedule.total_plate_weight > 0

    def test_plating_report_generation(self):
        """Test plating report generation."""
        pressures = calculate_all_zone_pressures(
            displacement=M48_DISPLACEMENT,
            length_wl=M48_LENGTH_WL,
            beam=M48_BEAM,
            draft=M48_DRAFT,
            depth=M48_DEPTH,
            speed_kts=M48_SPEED,
        )

        schedule = generate_plating_schedule(
            pressure_results=pressures,
            stiffener_spacing=400.0,
            frame_spacing=500.0,
            length_wl=M48_LENGTH_WL,
            beam=M48_BEAM,
            depth=M48_DEPTH,
        )

        report = generate_plating_report(schedule)
        assert "PLATING SCHEDULE" in report
        assert "PASS" in report or "FAIL" in report


class TestStiffeners:
    """Tests for stiffener calculations."""

    def test_frame_spacing_calculation(self):
        """Test frame spacing recommendation."""
        spacing = calculate_frame_spacing(
            length_wl=M48_LENGTH_WL,
            beam=M48_BEAM,
            draft=M48_DRAFT,
            speed_kts=M48_SPEED,
        )

        # Should be in reasonable range
        assert 300 <= spacing <= 800

    def test_section_modulus_calculation(self):
        """Test section modulus formula."""
        sm_required, formula, notes = calculate_stiffener_section_modulus(
            design_pressure=60.0,
            stiffener_spacing=400.0,
            frame_spacing=500.0,
        )

        # Should be positive
        assert sm_required > 0

        # Formula should contain key terms
        assert "SM" in formula

    def test_profile_selection(self):
        """Test profile selection logic."""
        # Small requirement - should select small profile
        profile_small = select_stiffener_profile(required_sm=5.0)
        assert profile_small is not None
        assert profile_small.section_modulus >= 5.0

        # Large requirement - should select larger profile
        profile_large = select_stiffener_profile(required_sm=50.0)
        assert profile_large is not None
        assert profile_large.section_modulus >= 50.0

        # Check larger is actually larger
        assert profile_large.section_modulus > profile_small.section_modulus

    def test_standard_profiles_valid(self):
        """Test standard profile database validity."""
        for profile in STANDARD_PROFILES:
            assert profile.section_modulus > 0
            assert profile.moment_of_inertia > 0
            assert profile.weight_per_meter > 0
            assert profile.height > 0

    def test_stiffener_result_compliance(self):
        """Test stiffener result compliance."""
        pressure_result = PressureResult(
            zone="bottom_forward",
            hydrostatic_pressure=20.0,
            slamming_pressure=80.0,
            design_pressure=80.0,
            service_factor_n1=0.85,
            acceleration_factor_ncg=2.0,
            deadrise_factor=0.7,
            area_factor=1.0,
            velocity_factor=3.0,
            position_x=0.1,
            position_z=0.0,
            rule_reference="ABS HSNC",
        )

        result = calculate_stiffener_result(
            zone=PressureZone.BOTTOM_FORWARD,
            pressure_result=pressure_result,
            stiffener_spacing=400.0,
            frame_spacing=500.0,
        )

        # Should select a profile
        assert result.selected_profile is not None

        # Should be compliant
        assert result.is_compliant
        assert result.actual_section_modulus >= result.required_section_modulus

    def test_stiffener_report_generation(self):
        """Test stiffener report generation."""
        pressures = calculate_all_zone_pressures(
            displacement=M48_DISPLACEMENT,
            length_wl=M48_LENGTH_WL,
            beam=M48_BEAM,
            draft=M48_DRAFT,
            depth=M48_DEPTH,
            speed_kts=M48_SPEED,
        )

        stiffeners = calculate_all_stiffeners(
            pressure_results=pressures,
            stiffener_spacing=400.0,
            frame_spacing=500.0,
        )

        report = generate_stiffener_report(stiffeners)
        assert "STIFFENER" in report
        assert "Section" in report or "SM" in report


class TestM48Baseline:
    """Integration tests using M48 baseline vessel."""

    def test_m48_full_scantling_schedule(self):
        """Test complete scantling schedule for M48."""
        # Calculate pressures
        pressures = calculate_all_zone_pressures(
            displacement=M48_DISPLACEMENT,
            length_wl=M48_LENGTH_WL,
            beam=M48_BEAM,
            draft=M48_DRAFT,
            depth=M48_DEPTH,
            speed_kts=M48_SPEED,
            deadrise_angle=M48_DEADRISE,
        )

        # Calculate plating
        plating = generate_plating_schedule(
            pressure_results=pressures,
            stiffener_spacing=400.0,
            frame_spacing=500.0,
            length_wl=M48_LENGTH_WL,
            beam=M48_BEAM,
            depth=M48_DEPTH,
        )

        # Calculate stiffeners
        stiffeners = calculate_all_stiffeners(
            pressure_results=pressures,
            stiffener_spacing=400.0,
            frame_spacing=500.0,
        )

        # Verify plating
        assert plating.bottom_thickness >= 6.0  # Reasonable for 45m high-speed
        assert plating.side_thickness >= 5.0
        assert all(z.is_compliant for z in plating.zones.values())

        # Verify stiffeners
        assert all(s.is_compliant for s in stiffeners.values())

    def test_m48_material_selection(self):
        """Test material selection for M48."""
        # 5083-H116 should be approved
        valid, msg = validate_material_for_location(
            AluminumAlloy.AL_5083_H116,
            is_primary_structure=True
        )
        assert valid

        # 6061-T6 should be rejected
        valid, msg = validate_material_for_location(
            AluminumAlloy.AL_6061_T6,
            is_primary_structure=True
        )
        assert not valid

    def test_m48_forward_bottom_critical(self):
        """Test forward bottom is critical area."""
        pressures = calculate_all_zone_pressures(
            displacement=M48_DISPLACEMENT,
            length_wl=M48_LENGTH_WL,
            beam=M48_BEAM,
            draft=M48_DRAFT,
            depth=M48_DEPTH,
            speed_kts=M48_SPEED,
        )

        # Forward bottom should have highest pressure
        p_fwd = pressures.get(PressureZone.BOTTOM_FORWARD)
        p_mid = pressures.get(PressureZone.BOTTOM_MIDSHIP)
        p_deck = pressures.get(PressureZone.DECK_WEATHER)

        assert p_fwd.design_pressure > p_mid.design_pressure
        assert p_fwd.design_pressure > p_deck.design_pressure


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_zero_pressure(self):
        """Test handling of zero pressure."""
        t_required, formula, notes = calculate_plate_thickness(
            design_pressure=0.0,
            stiffener_spacing=400.0,
        )

        # Should not crash, return minimal thickness
        assert t_required >= 0.5  # Corrosion allowance

    def test_small_vessel(self):
        """Test calculations for small vessel."""
        pressures = calculate_all_zone_pressures(
            displacement=50.0,
            length_wl=15.0,
            beam=4.0,
            draft=1.0,
            depth=2.0,
            speed_kts=25.0,
        )

        # Should produce valid results
        assert len(pressures) > 0
        for zone, result in pressures.items():
            assert result.design_pressure > 0

    def test_large_vessel(self):
        """Test calculations for larger vessel."""
        pressures = calculate_all_zone_pressures(
            displacement=2000.0,
            length_wl=80.0,
            beam=15.0,
            draft=3.5,
            depth=6.0,
            speed_kts=20.0,
        )

        # Should produce valid results
        assert len(pressures) > 0

    def test_high_speed_effect(self):
        """Test that higher speed increases slamming pressure."""
        pressures_slow = calculate_all_zone_pressures(
            displacement=M48_DISPLACEMENT,
            length_wl=M48_LENGTH_WL,
            beam=M48_BEAM,
            draft=M48_DRAFT,
            depth=M48_DEPTH,
            speed_kts=15.0,  # Slow
        )

        pressures_fast = calculate_all_zone_pressures(
            displacement=M48_DISPLACEMENT,
            length_wl=M48_LENGTH_WL,
            beam=M48_BEAM,
            draft=M48_DRAFT,
            depth=M48_DEPTH,
            speed_kts=35.0,  # Fast
        )

        # Forward bottom slamming should be higher at higher speed
        # (design pressure may be capped by minimum)
        p_slow_slam = pressures_slow[PressureZone.BOTTOM_FORWARD].slamming_pressure
        p_fast_slam = pressures_fast[PressureZone.BOTTOM_FORWARD].slamming_pressure

        assert p_fast_slam >= p_slow_slam


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
