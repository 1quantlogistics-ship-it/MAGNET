"""
Unit tests for SWBS weight estimators.

Tests all six SWBS group estimators.
"""

import pytest
from magnet.weight.items import SWBSGroup, WeightConfidence
from magnet.weight.estimators import (
    HullStructureEstimator,
    PropulsionPlantEstimator,
    ElectricPlantEstimator,
    CommandSurveillanceEstimator,
    AuxiliarySystemsEstimator,
    OutfitFurnishingsEstimator,
)


class TestHullStructureEstimator:
    """Tests for Group 100 Hull Structure estimator."""

    def test_basic_estimate(self):
        """Test basic hull estimation."""
        estimator = HullStructureEstimator()
        items = estimator.estimate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            cb=0.55,
            material="aluminum_5083",
            hull_type="monohull",
        )
        assert len(items) > 0
        total_weight = sum(item.weight_kg for item in items)
        assert total_weight > 0

        # All items should be Group 100
        for item in items:
            assert item.group == SWBSGroup.GROUP_100

    def test_hull_weight_scales_with_size(self):
        """Test hull weight increases with vessel size."""
        estimator = HullStructureEstimator()

        # Small vessel
        small_items = estimator.estimate(
            lwl=30.0, beam=6.0, depth=2.5, cb=0.50,
        )
        small_weight = sum(item.weight_kg for item in small_items)

        # Large vessel
        large_items = estimator.estimate(
            lwl=60.0, beam=12.0, depth=5.0, cb=0.55,
        )
        large_weight = sum(item.weight_kg for item in large_items)

        assert large_weight > small_weight * 2  # Should scale significantly

    def test_material_affects_weight(self):
        """Test different materials produce different weights."""
        estimator = HullStructureEstimator()

        # Steel hull
        steel_items = estimator.estimate(
            lwl=50.0, beam=10.0, depth=4.0, cb=0.55,
            material="mild_steel",
        )
        steel_weight = sum(item.weight_kg for item in steel_items)

        # Aluminum hull
        aluminum_items = estimator.estimate(
            lwl=50.0, beam=10.0, depth=4.0, cb=0.55,
            material="aluminum_5083",
        )
        aluminum_weight = sum(item.weight_kg for item in aluminum_items)

        # Aluminum should be lighter
        assert aluminum_weight < steel_weight

    def test_catamaran_heavier_than_monohull(self):
        """Test catamaran has more structure than monohull."""
        estimator = HullStructureEstimator()

        mono_items = estimator.estimate(
            lwl=50.0, beam=10.0, depth=4.0, cb=0.55,
            hull_type="monohull",
        )
        mono_weight = sum(item.weight_kg for item in mono_items)

        cat_items = estimator.estimate(
            lwl=50.0, beam=10.0, depth=4.0, cb=0.55,
            hull_type="catamaran",
        )
        cat_weight = sum(item.weight_kg for item in cat_items)

        assert cat_weight > mono_weight


class TestPropulsionPlantEstimator:
    """Tests for Group 200 Propulsion Plant estimator."""

    def test_basic_estimate(self):
        """Test basic propulsion estimation."""
        estimator = PropulsionPlantEstimator()
        items = estimator.estimate(
            installed_power_kw=2000.0,
            num_engines=2,
            engine_type="high_speed_diesel",
            lwl=50.0,
        )
        assert len(items) > 0
        total_weight = sum(item.weight_kg for item in items)
        assert total_weight > 0

        # All items should be Group 200
        for item in items:
            assert item.group == SWBSGroup.GROUP_200

    def test_weight_scales_with_power(self):
        """Test propulsion weight increases with power."""
        estimator = PropulsionPlantEstimator()

        # Low power
        low_items = estimator.estimate(
            installed_power_kw=1000.0, num_engines=2, lwl=40.0,
        )
        low_weight = sum(item.weight_kg for item in low_items)

        # High power
        high_items = estimator.estimate(
            installed_power_kw=4000.0, num_engines=2, lwl=40.0,
        )
        high_weight = sum(item.weight_kg for item in high_items)

        assert high_weight > low_weight

    def test_gas_turbine_lighter_per_kw(self):
        """Test gas turbines are lighter per kW than diesels."""
        estimator = PropulsionPlantEstimator()

        diesel_items = estimator.estimate(
            installed_power_kw=2000.0, num_engines=2,
            engine_type="high_speed_diesel", lwl=50.0,
        )
        diesel_weight = sum(item.weight_kg for item in diesel_items)

        gt_items = estimator.estimate(
            installed_power_kw=2000.0, num_engines=2,
            engine_type="gas_turbine", lwl=50.0,
        )
        gt_weight = sum(item.weight_kg for item in gt_items)

        # GT should be lighter for same power
        assert gt_weight < diesel_weight


class TestElectricPlantEstimator:
    """Tests for Group 300 Electrical Plant estimator."""

    def test_basic_estimate(self):
        """Test basic electrical estimation."""
        estimator = ElectricPlantEstimator()
        items = estimator.estimate(
            installed_power_kw=2000.0,
            lwl=50.0,
            depth=4.0,
        )
        assert len(items) > 0
        total_weight = sum(item.weight_kg for item in items)
        assert total_weight > 0

        # All items should be Group 300
        for item in items:
            assert item.group == SWBSGroup.GROUP_300

    def test_weight_scales_with_power(self):
        """Test electrical weight scales with propulsion power."""
        estimator = ElectricPlantEstimator()

        low_items = estimator.estimate(
            installed_power_kw=1000.0, lwl=40.0, depth=3.0,
        )
        low_weight = sum(item.weight_kg for item in low_items)

        high_items = estimator.estimate(
            installed_power_kw=5000.0, lwl=60.0, depth=5.0,
        )
        high_weight = sum(item.weight_kg for item in high_items)

        assert high_weight > low_weight


class TestCommandSurveillanceEstimator:
    """Tests for Group 400 Command & Surveillance estimator."""

    def test_basic_estimate(self):
        """Test basic command/surveillance estimation."""
        estimator = CommandSurveillanceEstimator()
        items = estimator.estimate(
            lwl=50.0,
            depth=4.0,
            vessel_type="commercial",
        )
        assert len(items) > 0

        # All items should be Group 400
        for item in items:
            assert item.group == SWBSGroup.GROUP_400

    def test_military_heavier(self):
        """Test military vessels have more C&S equipment."""
        estimator = CommandSurveillanceEstimator()

        commercial_items = estimator.estimate(
            lwl=50.0, depth=4.0, vessel_type="commercial",
        )
        commercial_weight = sum(item.weight_kg for item in commercial_items)

        military_items = estimator.estimate(
            lwl=50.0, depth=4.0, vessel_type="military",
        )
        military_weight = sum(item.weight_kg for item in military_items)

        assert military_weight > commercial_weight


class TestAuxiliarySystemsEstimator:
    """Tests for Group 500 Auxiliary Systems estimator."""

    def test_basic_estimate(self):
        """Test basic auxiliary estimation."""
        estimator = AuxiliarySystemsEstimator()
        items = estimator.estimate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            displacement_mt=500.0,
        )
        assert len(items) > 0

        # All items should be Group 500
        for item in items:
            assert item.group == SWBSGroup.GROUP_500

    def test_weight_scales_with_displacement(self):
        """Test auxiliary weight scales with displacement."""
        estimator = AuxiliarySystemsEstimator()

        small_items = estimator.estimate(
            lwl=30.0, beam=6.0, depth=2.5, displacement_mt=200.0,
        )
        small_weight = sum(item.weight_kg for item in small_items)

        large_items = estimator.estimate(
            lwl=60.0, beam=12.0, depth=5.0, displacement_mt=1000.0,
        )
        large_weight = sum(item.weight_kg for item in large_items)

        assert large_weight > small_weight


class TestOutfitFurnishingsEstimator:
    """Tests for Group 600 Outfit & Furnishings estimator."""

    def test_basic_estimate(self):
        """Test basic outfit estimation."""
        estimator = OutfitFurnishingsEstimator()
        items = estimator.estimate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            crew_size=6,
            passenger_count=0,
        )
        assert len(items) > 0

        # All items should be Group 600
        for item in items:
            assert item.group == SWBSGroup.GROUP_600

    def test_weight_scales_with_crew(self):
        """Test outfit weight scales with crew size."""
        estimator = OutfitFurnishingsEstimator()

        small_crew_items = estimator.estimate(
            lwl=50.0, beam=10.0, depth=4.0,
            crew_size=4, passenger_count=0,
        )
        small_weight = sum(item.weight_kg for item in small_crew_items)

        large_crew_items = estimator.estimate(
            lwl=50.0, beam=10.0, depth=4.0,
            crew_size=20, passenger_count=0,
        )
        large_weight = sum(item.weight_kg for item in large_crew_items)

        assert large_weight > small_weight

    def test_passenger_vessel_heavier(self):
        """Test passenger vessels have more outfit weight."""
        estimator = OutfitFurnishingsEstimator()

        no_pax_items = estimator.estimate(
            lwl=50.0, beam=10.0, depth=4.0,
            crew_size=6, passenger_count=0,
        )
        no_pax_weight = sum(item.weight_kg for item in no_pax_items)

        with_pax_items = estimator.estimate(
            lwl=50.0, beam=10.0, depth=4.0,
            crew_size=6, passenger_count=50,
        )
        with_pax_weight = sum(item.weight_kg for item in with_pax_items)

        assert with_pax_weight > no_pax_weight


class TestEstimatorVCGPositioning:
    """Tests for VCG positioning across estimators."""

    def test_hull_vcg_below_depth_half(self):
        """Test hull VCG is below half depth."""
        estimator = HullStructureEstimator()
        items = estimator.estimate(
            lwl=50.0, beam=10.0, depth=4.0, cb=0.55,
        )
        total_weight = sum(item.weight_kg for item in items)
        weighted_vcg = sum(item.weight_kg * item.vcg_m for item in items) / total_weight

        # Hull structure VCG typically around 40-50% of depth
        assert weighted_vcg < 4.0 * 0.55  # Less than 55% of depth

    def test_propulsion_vcg_low(self):
        """Test propulsion VCG is low in vessel."""
        estimator = PropulsionPlantEstimator()
        items = estimator.estimate(
            installed_power_kw=2000.0, num_engines=2, lwl=50.0,
        )
        total_weight = sum(item.weight_kg for item in items)
        weighted_vcg = sum(item.weight_kg * item.vcg_m for item in items) / total_weight

        # Propulsion typically in lower 30% of depth
        assert weighted_vcg < 4.0 * 0.4  # Less than 40% of assumed depth

    def test_command_vcg_high(self):
        """Test command/surveillance VCG is high (bridge level)."""
        estimator = CommandSurveillanceEstimator()
        items = estimator.estimate(
            lwl=50.0, depth=4.0, vessel_type="commercial",
        )
        total_weight = sum(item.weight_kg for item in items)
        weighted_vcg = sum(item.weight_kg * item.vcg_m for item in items) / total_weight

        # Command typically in upper portion
        assert weighted_vcg > 4.0 * 0.6  # Above 60% of depth
