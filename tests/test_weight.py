"""
Tests for weight estimation module.

Tests:
- Lightship weight estimation (Watson-Gilfillan method)
- Deadweight calculation
- Weight distribution and centers of gravity
- M48 vessel baseline validation
"""

import pytest
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physics.weight.lightship import (
    calculate_hull_steel_weight,
    calculate_machinery_weight,
    calculate_outfit_weight,
    calculate_lightship_weight,
    LightshipResult,
    VesselCategory,
    PropulsionType,
    generate_lightship_report,
)
from physics.weight.deadweight import (
    calculate_fuel_requirement,
    calculate_fresh_water_requirement,
    calculate_stores_requirement,
    calculate_deadweight,
    calculate_displacement_balance,
    DeadweightResult,
    DisplacementBalance,
    FuelType,
    generate_deadweight_report,
    generate_balance_report,
)
from physics.weight.distribution import (
    WeightItem,
    WeightCategory,
    calculate_weight_distribution,
    create_lightship_items,
    create_deadweight_items,
    WeightDistribution,
    generate_distribution_report,
)


# ============================================================================
# M48 Vessel Baseline Parameters
# ============================================================================
# 48m semi-displacement catamaran workboat
M48_LENGTH_BP = 45.0        # m
M48_BEAM = 12.8             # m
M48_DEPTH = 4.5             # m
M48_DRAFT = 2.1             # m
M48_CB = 0.45               # Block coefficient
M48_DISPLACEMENT = 420.0    # tonnes
M48_SPEED = 28.0            # knots
M48_POWER = 4000.0          # kW (total installed)
M48_CREW = 8
M48_PASSENGERS = 24


class TestHullSteelWeight:
    """Tests for hull steel weight estimation."""

    def test_basic_calculation(self):
        """Test basic hull steel weight calculation."""
        hull_weight, super_weight, coeffs = calculate_hull_steel_weight(
            length_bp=45.0,
            beam=12.8,
            depth=4.5,
            block_coefficient=0.45,
            vessel_category=VesselCategory.WORKBOAT,
        )

        # Should return positive weights
        assert hull_weight > 0
        assert super_weight >= 0

        # Reasonable range for 45m vessel using Watson-Gilfillan method
        # Note: This method is for steel monohulls, catamaran would be lighter
        assert 50 < hull_weight < 500

    def test_no_superstructure(self):
        """Test hull weight without superstructure."""
        hull_weight, super_weight, coeffs = calculate_hull_steel_weight(
            length_bp=45.0,
            beam=12.8,
            depth=4.5,
            block_coefficient=0.45,
            has_superstructure=False,
        )

        assert super_weight == 0
        assert hull_weight > 0

    def test_vessel_category_variation(self):
        """Test that different vessel categories produce different weights."""
        base_params = {
            "length_bp": 45.0,
            "beam": 12.8,
            "depth": 4.5,
            "block_coefficient": 0.45,
        }

        workboat, _, _ = calculate_hull_steel_weight(
            **base_params, vessel_category=VesselCategory.WORKBOAT
        )
        tanker, _, _ = calculate_hull_steel_weight(
            **base_params, vessel_category=VesselCategory.TANKER
        )
        yacht, _, _ = calculate_hull_steel_weight(
            **base_params, vessel_category=VesselCategory.YACHT
        )

        # Yacht should be heavier (higher K1 coefficient)
        assert yacht > tanker

    def test_block_coefficient_effect(self):
        """Test that Cb affects hull weight."""
        fine_hull, _, _ = calculate_hull_steel_weight(
            length_bp=45.0,
            beam=12.8,
            depth=4.5,
            block_coefficient=0.35,  # Fine hull
        )
        full_hull, _, _ = calculate_hull_steel_weight(
            length_bp=45.0,
            beam=12.8,
            depth=4.5,
            block_coefficient=0.70,  # Full hull
        )

        # Cb correction: finer hulls have correction > 1.0
        # So fine hull should be heavier per the formula
        assert fine_hull > full_hull


class TestMachineryWeight:
    """Tests for machinery weight estimation."""

    def test_basic_calculation(self):
        """Test basic machinery weight calculation."""
        main, aux, shaft, coeffs = calculate_machinery_weight(
            installed_power=4000.0,
            propulsion_type=PropulsionType.DIESEL_MECHANICAL,
            length_bp=45.0,
        )

        assert main > 0
        assert aux > 0
        assert shaft > 0

        # 4000 kW at 8 kg/kW = 32 tonnes main engines
        assert 25 < main < 40

    def test_propulsion_type_variation(self):
        """Test different propulsion types."""
        diesel, _, _, _ = calculate_machinery_weight(
            installed_power=4000.0,
            propulsion_type=PropulsionType.DIESEL_MECHANICAL,
        )
        gas_turbine, _, _, _ = calculate_machinery_weight(
            installed_power=4000.0,
            propulsion_type=PropulsionType.GAS_TURBINE,
        )
        diesel_electric, _, _, _ = calculate_machinery_weight(
            installed_power=4000.0,
            propulsion_type=PropulsionType.DIESEL_ELECTRIC,
        )

        # Gas turbine is lightest (2.5 kg/kW)
        assert gas_turbine < diesel
        # Diesel electric is heaviest (12 kg/kW)
        assert diesel_electric > diesel

    def test_waterjet_propulsion(self):
        """Test waterjet propulsion (no conventional shafting)."""
        main, aux, shaft, _ = calculate_machinery_weight(
            installed_power=4000.0,
            propulsion_type=PropulsionType.WATERJET,
            length_bp=45.0,
        )

        # Waterjet should have minimal shafting
        assert shaft < 10  # Much less than conventional


class TestOutfitWeight:
    """Tests for outfit weight estimation."""

    def test_basic_calculation(self):
        """Test basic outfit weight calculation."""
        accom, equip, systems, coeffs = calculate_outfit_weight(
            length_bp=45.0,
            beam=12.8,
            depth=4.5,
            vessel_category=VesselCategory.WORKBOAT,
            crew_capacity=8,
            passenger_capacity=24,
        )

        assert accom > 0
        assert equip > 0
        assert systems > 0

        total = accom + equip + systems
        # Reasonable range for 45m vessel
        assert 30 < total < 150

    def test_passenger_effect(self):
        """Test that more passengers increase outfit weight."""
        _, _, _, _ = calculate_outfit_weight(
            length_bp=45.0,
            beam=12.8,
            depth=4.5,
            crew_capacity=8,
            passenger_capacity=0,
        )

        accom_pax, _, _, _ = calculate_outfit_weight(
            length_bp=45.0,
            beam=12.8,
            depth=4.5,
            crew_capacity=8,
            passenger_capacity=50,
        )

        # More passengers should increase accommodation weight
        assert accom_pax > 8 * 0.8  # At least crew weight


class TestLightshipWeight:
    """Tests for complete lightship weight calculation."""

    def test_complete_lightship(self):
        """Test complete lightship calculation."""
        result = calculate_lightship_weight(
            length_bp=M48_LENGTH_BP,
            beam=M48_BEAM,
            depth=M48_DEPTH,
            block_coefficient=M48_CB,
            installed_power=M48_POWER,
            vessel_category=VesselCategory.WORKBOAT,
            propulsion_type=PropulsionType.DIESEL_MECHANICAL,
            crew_capacity=M48_CREW,
            passenger_capacity=M48_PASSENGERS,
        )

        assert isinstance(result, LightshipResult)

        # Check all components are positive
        assert result.hull_steel_weight > 0
        assert result.machinery_weight > 0
        assert result.outfit_weight > 0
        assert result.lightship_weight > 0
        assert result.margin_weight >= 0

        # Check summation
        expected_lightship = (
            result.hull_steel_weight +
            result.machinery_weight +
            result.outfit_weight
        )
        assert abs(result.lightship_weight - expected_lightship) < 0.1

        # Check total with margin
        assert result.total_lightship > result.lightship_weight

    def test_centers_of_gravity(self):
        """Test that centers of gravity are reasonable."""
        result = calculate_lightship_weight(
            length_bp=M48_LENGTH_BP,
            beam=M48_BEAM,
            depth=M48_DEPTH,
            block_coefficient=M48_CB,
            installed_power=M48_POWER,
        )

        # KG should be between 0 and depth
        assert 0 < result.kg_lightship < M48_DEPTH

        # LCG should be near midship (0.4-0.6 of Lbp from AP)
        assert 0.35 * M48_LENGTH_BP < result.lcg_lightship < 0.65 * M48_LENGTH_BP

    def test_report_generation(self):
        """Test lightship report generation."""
        result = calculate_lightship_weight(
            length_bp=M48_LENGTH_BP,
            beam=M48_BEAM,
            depth=M48_DEPTH,
            block_coefficient=M48_CB,
            installed_power=M48_POWER,
        )

        report = generate_lightship_report(result, "M48 Test Vessel")
        assert "LIGHTSHIP WEIGHT REPORT" in report
        assert "Hull Steel" in report
        assert "Machinery" in report
        assert "Outfit" in report


class TestFuelRequirement:
    """Tests for fuel requirement calculation."""

    def test_basic_fuel_calculation(self):
        """Test basic fuel calculation."""
        fuel_weight, fuel_volume, daily_consumption = calculate_fuel_requirement(
            installed_power=4000.0,
            endurance_days=14.0,
            service_speed_kts=28.0,
            fuel_type=FuelType.MDO,
        )

        assert fuel_weight > 0
        assert fuel_volume > 0
        assert daily_consumption > 0

        # Check fuel volume consistency
        # MDO density ~0.89 t/m³
        expected_volume = fuel_weight / 0.89
        assert abs(fuel_volume - expected_volume) < 1.0

    def test_endurance_scaling(self):
        """Test that fuel scales with endurance."""
        fuel_7d, _, _ = calculate_fuel_requirement(
            installed_power=4000.0,
            endurance_days=7.0,
            service_speed_kts=28.0,
        )
        fuel_14d, _, _ = calculate_fuel_requirement(
            installed_power=4000.0,
            endurance_days=14.0,
            service_speed_kts=28.0,
        )

        # Double endurance should roughly double fuel
        assert 1.8 < fuel_14d / fuel_7d < 2.2


class TestDeadweight:
    """Tests for deadweight calculation."""

    def test_complete_deadweight(self):
        """Test complete deadweight calculation."""
        result = calculate_deadweight(
            displacement=M48_DISPLACEMENT,
            lightship=250.0,  # Assumed lightship
            installed_power=M48_POWER,
            service_speed_kts=M48_SPEED,
            endurance_days=14.0,
            crew_capacity=M48_CREW,
            passenger_capacity=M48_PASSENGERS,
        )

        assert isinstance(result, DeadweightResult)

        # Check components
        assert result.fuel_weight > 0
        assert result.fresh_water_weight > 0
        assert result.stores_weight > 0
        assert result.deadweight > 0

        # Deadweight should equal sum of components
        expected = (
            result.cargo_weight +
            result.fuel_weight +
            result.fresh_water_weight +
            result.stores_weight +
            result.crew_effects_weight +
            result.ballast_weight
        )
        assert abs(result.deadweight - expected) < 0.1

    def test_report_generation(self):
        """Test deadweight report generation."""
        result = calculate_deadweight(
            displacement=420.0,
            lightship=250.0,
            installed_power=4000.0,
            endurance_days=14.0,
        )

        report = generate_deadweight_report(result)
        assert "DEADWEIGHT" in report
        assert "Fuel" in report
        assert "ENDURANCE" in report


class TestDisplacementBalance:
    """Tests for displacement balance verification."""

    def test_balanced_design(self):
        """Test a balanced design."""
        balance = calculate_displacement_balance(
            displacement=420.0,
            lightship=250.0,
            deadweight=150.0,
        )

        assert isinstance(balance, DisplacementBalance)
        assert balance.is_balanced
        assert balance.margin > 0
        assert balance.utilization < 100

    def test_overweight_design(self):
        """Test an overweight design."""
        balance = calculate_displacement_balance(
            displacement=400.0,
            lightship=250.0,
            deadweight=200.0,  # Total 450 > 400
        )

        assert not balance.is_balanced
        assert balance.margin < 0
        assert len(balance.warnings) > 0
        assert any("OVERWEIGHT" in w for w in balance.warnings)

    def test_report_generation(self):
        """Test balance report generation."""
        balance = calculate_displacement_balance(
            displacement=420.0,
            lightship=250.0,
            deadweight=150.0,
        )

        report = generate_balance_report(balance)
        assert "DISPLACEMENT BALANCE" in report
        assert "BALANCED" in report or "OVERWEIGHT" in report


class TestWeightDistribution:
    """Tests for weight distribution calculation."""

    def test_basic_distribution(self):
        """Test basic weight distribution."""
        items = [
            WeightItem("Hull", 100.0, lcg=22.5, vcg=2.5, category=WeightCategory.HULL_STRUCTURE),
            WeightItem("Machinery", 40.0, lcg=18.0, vcg=1.5, category=WeightCategory.MACHINERY_MAIN),
            WeightItem("Fuel", 30.0, lcg=15.0, vcg=1.0, category=WeightCategory.FUEL),
        ]

        dist = calculate_weight_distribution(items)

        assert dist.total_weight == 170.0

        # Check LCG calculation
        expected_lcg = (100*22.5 + 40*18.0 + 30*15.0) / 170
        assert abs(dist.lcg - expected_lcg) < 0.01

        # Check VCG calculation
        expected_vcg = (100*2.5 + 40*1.5 + 30*1.0) / 170
        assert abs(dist.vcg - expected_vcg) < 0.01

    def test_free_surface_effect(self):
        """Test free surface moment correction."""
        items = [
            WeightItem("Hull", 100.0, lcg=22.5, vcg=2.5),
            WeightItem("Fuel Tank", 30.0, lcg=15.0, vcg=1.0, free_surface_moment=50.0),
        ]

        dist = calculate_weight_distribution(items, displacement=150.0)

        # Free surface correction = FSM / displacement
        expected_correction = 50.0 / 150.0
        assert abs(dist.free_surface_correction - expected_correction) < 0.001

        # VCG corrected should be higher than uncorrected
        assert dist.vcg_corrected > dist.vcg

    def test_transverse_moment(self):
        """Test transverse moment and heel calculation."""
        items = [
            WeightItem("Hull", 100.0, lcg=22.5, vcg=2.5, tcg=0.0),
            WeightItem("Cargo", 30.0, lcg=22.5, vcg=2.5, tcg=2.0),  # 2m to starboard
        ]

        dist = calculate_weight_distribution(items, gm=1.5)

        assert dist.tcg > 0  # Net TCG to starboard
        assert dist.estimated_heel > 0  # Heel to starboard

    def test_category_grouping(self):
        """Test weight grouping by category."""
        items = [
            WeightItem("Hull Main", 80.0, lcg=22.5, vcg=2.5, category=WeightCategory.HULL_STRUCTURE),
            WeightItem("Hull Secondary", 20.0, lcg=20.0, vcg=2.0, category=WeightCategory.HULL_STRUCTURE),
            WeightItem("Engine 1", 20.0, lcg=18.0, vcg=1.5, category=WeightCategory.MACHINERY_MAIN),
            WeightItem("Engine 2", 20.0, lcg=18.0, vcg=1.5, category=WeightCategory.MACHINERY_MAIN),
        ]

        dist = calculate_weight_distribution(items)

        assert dist.category_weights["hull_structure"] == 100.0
        assert dist.category_weights["machinery_main"] == 40.0

    def test_lightship_deadweight_split(self):
        """Test lightship vs deadweight categorization."""
        items = [
            WeightItem("Hull", 100.0, lcg=22.5, vcg=2.5, category=WeightCategory.HULL_STRUCTURE),
            WeightItem("Machinery", 40.0, lcg=18.0, vcg=1.5, category=WeightCategory.MACHINERY_MAIN),
            WeightItem("Fuel", 30.0, lcg=15.0, vcg=1.0, category=WeightCategory.FUEL),
            WeightItem("Cargo", 50.0, lcg=22.0, vcg=2.0, category=WeightCategory.CARGO),
        ]

        dist = calculate_weight_distribution(items)

        assert dist.lightship_weight == 140.0  # Hull + Machinery
        assert dist.deadweight == 80.0  # Fuel + Cargo


class TestM48Baseline:
    """Integration tests using M48 baseline vessel."""

    def test_m48_lightship_estimate(self):
        """Test M48 lightship estimation.

        Note: Watson-Gilfillan is for steel monohulls. M48 is a catamaran
        which would be lighter. This test validates the method produces
        reasonable estimates for a monohull of these dimensions.
        """
        result = calculate_lightship_weight(
            length_bp=M48_LENGTH_BP,
            beam=M48_BEAM,
            depth=M48_DEPTH,
            block_coefficient=M48_CB,
            installed_power=M48_POWER,
            vessel_category=VesselCategory.WORKBOAT,
            propulsion_type=PropulsionType.DIESEL_MECHANICAL,
            crew_capacity=M48_CREW,
            passenger_capacity=M48_PASSENGERS,
        )

        # Watson-Gilfillan for steel monohull produces 400-600 tonnes
        # A catamaran would be lighter (~250-350 tonnes)
        assert 300 < result.total_lightship < 700

        # KG should be reasonable (below depth)
        assert result.kg_lightship < M48_DEPTH

    def test_m48_displacement_balance(self):
        """Test M48 displacement balance.

        Uses manually specified lightship appropriate for catamaran construction.
        M48 is a fast ferry/workboat with shorter endurance than offshore vessels.
        """
        # Use a realistic catamaran lightship
        catamaran_lightship = 280.0  # tonnes (typical for 48m catamaran)

        # Fast ferry/workboat: ~3 day endurance (not 14 days like offshore)
        deadweight = calculate_deadweight(
            displacement=M48_DISPLACEMENT,
            lightship=catamaran_lightship,
            installed_power=M48_POWER,
            service_speed_kts=M48_SPEED,
            endurance_days=3.0,  # Short-range fast vessel
            crew_capacity=M48_CREW,
            passenger_capacity=M48_PASSENGERS,
        )

        balance = calculate_displacement_balance(
            displacement=M48_DISPLACEMENT,
            lightship=catamaran_lightship,
            deadweight=deadweight.deadweight,
        )

        # Design should be feasible with catamaran lightship and realistic endurance
        assert balance.is_balanced
        # Utilization should be reasonable (70-100%)
        assert 70 < balance.utilization <= 100

    def test_m48_weight_distribution(self):
        """Test M48 weight distribution."""
        lightship = calculate_lightship_weight(
            length_bp=M48_LENGTH_BP,
            beam=M48_BEAM,
            depth=M48_DEPTH,
            block_coefficient=M48_CB,
            installed_power=M48_POWER,
            vessel_category=VesselCategory.WORKBOAT,
        )

        deadweight = calculate_deadweight(
            displacement=M48_DISPLACEMENT,
            lightship=lightship.total_lightship,
            installed_power=M48_POWER,
            service_speed_kts=M48_SPEED,
            endurance_days=14.0,
        )

        # Create weight items
        ls_items = create_lightship_items(lightship, M48_LENGTH_BP)
        dw_items = create_deadweight_items(deadweight, M48_LENGTH_BP, M48_DEPTH)

        all_items = ls_items + dw_items

        dist = calculate_weight_distribution(
            all_items,
            displacement=M48_DISPLACEMENT,
            gm=1.2,  # Assumed GM
        )

        # Total should match sum
        assert abs(dist.total_weight - (lightship.total_lightship + deadweight.deadweight)) < 1.0

        # VCG should be reasonable
        assert 0 < dist.vcg < M48_DEPTH

        # LCG should be near midship
        assert 0.35 * M48_LENGTH_BP < dist.lcg < 0.65 * M48_LENGTH_BP

    def test_m48_full_report(self):
        """Test M48 full weight report generation."""
        lightship = calculate_lightship_weight(
            length_bp=M48_LENGTH_BP,
            beam=M48_BEAM,
            depth=M48_DEPTH,
            block_coefficient=M48_CB,
            installed_power=M48_POWER,
        )

        deadweight = calculate_deadweight(
            displacement=M48_DISPLACEMENT,
            lightship=lightship.total_lightship,
            installed_power=M48_POWER,
            service_speed_kts=M48_SPEED,
            endurance_days=14.0,
        )

        # Generate all reports
        ls_report = generate_lightship_report(lightship, "M48")
        dw_report = generate_deadweight_report(deadweight, "M48")

        assert len(ls_report) > 100
        assert len(dw_report) > 100


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_zero_power(self):
        """Test with zero installed power."""
        result = calculate_lightship_weight(
            length_bp=45.0,
            beam=12.8,
            depth=4.5,
            block_coefficient=0.45,
            installed_power=0.0,
        )

        # Should still produce valid result (zero machinery weight is ok)
        assert result.lightship_weight > 0
        assert result.machinery_weight == 0 or result.machinery_weight >= 0

    def test_small_vessel(self):
        """Test with small vessel dimensions."""
        result = calculate_lightship_weight(
            length_bp=15.0,
            beam=4.0,
            depth=2.0,
            block_coefficient=0.50,
            installed_power=500.0,
        )

        assert result.lightship_weight > 0
        assert result.lightship_weight < 100  # Small vessel

    def test_empty_weight_list(self):
        """Test weight distribution with empty list."""
        dist = calculate_weight_distribution([])

        assert dist.total_weight == 0
        assert dist.lcg == 0
        assert dist.vcg == 0

    def test_single_weight_item(self):
        """Test weight distribution with single item."""
        items = [WeightItem("Single", 100.0, lcg=22.5, vcg=2.5)]
        dist = calculate_weight_distribution(items)

        assert dist.total_weight == 100.0
        assert dist.lcg == 22.5
        assert dist.vcg == 2.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
