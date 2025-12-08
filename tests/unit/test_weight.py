"""
Unit tests for MAGNET Weight Estimation Framework (Module 07).

Tests cover:
- WeightItem and GroupSummary dataclasses
- SWBSGroup enum and SWBS_GROUP_NAMES
- All 6 SWBS group estimators (100-600)
- WeightAggregator and LightshipSummary
- determinize_dict utility
- Weight validators (WeightEstimationValidator, WeightStabilityValidator)

Total: 45+ tests
"""

import pytest
from unittest.mock import Mock, MagicMock
import json
from datetime import datetime

from magnet.weight import (
    # Data structures
    SWBSGroup,
    WeightItem,
    GroupSummary,
    SWBS_GROUP_NAMES,
    # Aggregator
    WeightAggregator,
    LightshipSummary,
    # Estimators
    HullStructureEstimator,
    PropulsionPlantEstimator,
    ElectricPlantEstimator,
    CommandSurveillanceEstimator,
    AuxiliarySystemsEstimator,
    OutfitFurnishingsEstimator,
    # Utilities
    determinize_dict,
    # Validators
    WeightEstimationValidator,
    WeightStabilityValidator,
    get_weight_estimation_definition,
    get_weight_stability_definition,
)
from magnet.weight.items import WeightConfidence, create_weight_item
from magnet.validators.taxonomy import ValidatorState, ResultSeverity


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def sample_hull_params():
    """Standard hull parameters for testing (for estimators that don't need draft)."""
    return {
        "lwl": 30.0,
        "beam": 8.0,
        "depth": 4.0,
        "cb": 0.55,
    }


@pytest.fixture
def full_hull_params():
    """Full hull parameters including draft (for validators/state)."""
    return {
        "lwl": 30.0,
        "beam": 8.0,
        "depth": 4.0,
        "draft": 2.0,
        "cb": 0.55,
    }


@pytest.fixture
def sample_propulsion_params():
    """Standard propulsion parameters for testing."""
    return {
        "installed_power_kw": 2000.0,
        "num_engines": 2,
        "engine_type": "high_speed_diesel",
        "propulsion_type": "propeller",
    }


@pytest.fixture
def mock_state_manager():
    """Create a mock StateManager for validator testing."""
    state = {
        "hull.lwl": 30.0,
        "hull.beam": 8.0,
        "hull.depth": 4.0,
        "hull.draft": 2.0,
        "hull.cb": 0.55,
        "hull.displacement_mt": 100.0,
        "hull.kb_m": 1.2,
        "hull.bm_m": 3.5,
        "propulsion.installed_power_kw": 2000.0,
        "propulsion.number_of_engines": 2,
        "propulsion.engine_type": "high_speed_diesel",
        "mission.crew_size": 6,
        "mission.passengers": 0,
        "mission.vessel_type": "patrol",
    }

    manager = Mock()
    manager.get = Mock(side_effect=lambda key, default=None: state.get(key, default))
    manager.set = Mock()
    return manager


# =============================================================================
# WEIGHT ITEM TESTS
# =============================================================================

class TestWeightItem:
    """Tests for WeightItem dataclass."""

    def test_create_basic(self):
        """Test basic WeightItem creation."""
        item = WeightItem(
            name="Test Item",
            weight_kg=1000.0,
            lcg_m=15.0,
            vcg_m=2.0,
        )
        assert item.name == "Test Item"
        assert item.weight_kg == 1000.0
        assert item.lcg_m == 15.0
        assert item.vcg_m == 2.0
        assert item.tcg_m == 0.0  # Default

    def test_create_with_group(self):
        """Test WeightItem with SWBS group."""
        item = WeightItem(
            name="Hull Plating",
            weight_kg=5000.0,
            lcg_m=15.0,
            vcg_m=1.8,
            group=SWBSGroup.GROUP_100,
            subgroup=110,
        )
        assert item.group == SWBSGroup.GROUP_100
        assert item.subgroup == 110
        assert item.group_number == 100

    def test_weight_mt_property(self):
        """Test weight_mt conversion property."""
        item = WeightItem(
            name="Test",
            weight_kg=1500.0,
            lcg_m=10.0,
            vcg_m=1.0,
        )
        assert item.weight_mt == 1.5

    def test_moment_properties(self):
        """Test moment calculation properties."""
        item = WeightItem(
            name="Test",
            weight_kg=1000.0,
            lcg_m=10.0,
            vcg_m=2.0,
            tcg_m=0.5,
        )
        assert item.lcg_moment_kg_m == 10000.0
        assert item.vcg_moment_kg_m == 2000.0
        assert item.tcg_moment_kg_m == 500.0

    def test_confidence_value(self):
        """Test confidence_value property."""
        item = WeightItem(
            name="Test",
            weight_kg=1000.0,
            lcg_m=10.0,
            vcg_m=2.0,
            confidence=WeightConfidence.HIGH,
        )
        assert item.confidence_value == 0.85

    def test_to_dict(self):
        """Test serialization to dictionary."""
        item = WeightItem(
            name="Test Item",
            weight_kg=1000.0,
            lcg_m=15.0,
            vcg_m=2.0,
            group=SWBSGroup.GROUP_200,
            subgroup=210,
            confidence=WeightConfidence.MEDIUM,
            notes="Test notes",
        )
        d = item.to_dict()
        assert d["name"] == "Test Item"
        assert d["weight_kg"] == 1000.0
        assert d["weight_mt"] == 1.0
        assert d["group"] == 200
        assert d["confidence"] == 0.7

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        d = {
            "name": "Restored Item",
            "weight_kg": 2000.0,
            "lcg_m": 20.0,
            "vcg_m": 3.0,
            "group": 300,
            "confidence": 0.85,
        }
        item = WeightItem.from_dict(d)
        assert item.name == "Restored Item"
        assert item.weight_kg == 2000.0
        assert item.group == SWBSGroup.GROUP_300


class TestCreateWeightItem:
    """Tests for create_weight_item factory function."""

    def test_create_valid(self):
        """Test creating valid weight item."""
        item = create_weight_item(
            name="Test",
            weight_kg=100.0,
            lcg_m=10.0,
            vcg_m=1.0,
            group=SWBSGroup.GROUP_100,
        )
        assert item.name == "Test"
        assert item.weight_kg == 100.0

    def test_reject_negative_weight(self):
        """Test rejection of negative weight."""
        with pytest.raises(ValueError, match="Weight cannot be negative"):
            create_weight_item(
                name="Invalid",
                weight_kg=-100.0,
                lcg_m=10.0,
                vcg_m=1.0,
                group=SWBSGroup.GROUP_100,
            )


# =============================================================================
# GROUP SUMMARY TESTS
# =============================================================================

class TestGroupSummary:
    """Tests for GroupSummary dataclass."""

    def test_from_items_empty(self):
        """Test GroupSummary from empty items list."""
        summary = GroupSummary.from_items(SWBSGroup.GROUP_100, [])
        assert summary.total_weight_mt == 0.0
        assert summary.item_count == 0

    def test_from_items_single(self):
        """Test GroupSummary from single item."""
        items = [
            WeightItem(
                name="Item 1",
                weight_kg=1000.0,
                lcg_m=15.0,
                vcg_m=2.0,
                group=SWBSGroup.GROUP_100,
            )
        ]
        summary = GroupSummary.from_items(SWBSGroup.GROUP_100, items)
        assert summary.total_weight_mt == 1.0
        assert summary.lcg_m == 15.0
        assert summary.vcg_m == 2.0
        assert summary.item_count == 1

    def test_from_items_multiple_weighted_average(self):
        """Test weighted average calculation."""
        items = [
            WeightItem(name="Heavy", weight_kg=2000.0, lcg_m=10.0, vcg_m=1.0, group=SWBSGroup.GROUP_100),
            WeightItem(name="Light", weight_kg=1000.0, lcg_m=20.0, vcg_m=2.0, group=SWBSGroup.GROUP_100),
        ]
        summary = GroupSummary.from_items(SWBSGroup.GROUP_100, items)
        # LCG = (2000*10 + 1000*20) / 3000 = 40000/3000 = 13.33
        assert abs(summary.lcg_m - 13.333) < 0.01
        assert summary.total_weight_mt == 3.0

    def test_to_dict(self):
        """Test serialization."""
        summary = GroupSummary(
            group=SWBSGroup.GROUP_200,
            name="Propulsion Plant",
            total_weight_mt=15.5,
            lcg_m=18.0,
            vcg_m=1.2,
            tcg_m=0.0,
            item_count=5,
            average_confidence=0.75,
        )
        d = summary.to_dict()
        assert d["group"] == 200
        assert d["total_weight_mt"] == 15.5


# =============================================================================
# SWBS GROUP TESTS
# =============================================================================

class TestSWBSGroup:
    """Tests for SWBSGroup enum."""

    def test_all_groups_defined(self):
        """Test all expected SWBS groups exist."""
        assert SWBSGroup.GROUP_100.value == 100
        assert SWBSGroup.GROUP_200.value == 200
        assert SWBSGroup.GROUP_300.value == 300
        assert SWBSGroup.GROUP_400.value == 400
        assert SWBSGroup.GROUP_500.value == 500
        assert SWBSGroup.GROUP_600.value == 600
        assert SWBSGroup.GROUP_700.value == 700  # Armament
        assert SWBSGroup.MARGIN.value == 999

    def test_group_names(self):
        """Test SWBS_GROUP_NAMES mapping."""
        assert SWBS_GROUP_NAMES[SWBSGroup.GROUP_100] == "Hull Structure"
        assert SWBS_GROUP_NAMES[SWBSGroup.GROUP_200] == "Propulsion Plant"
        assert SWBS_GROUP_NAMES[SWBSGroup.GROUP_600] == "Outfit & Furnishings"


# =============================================================================
# HULL STRUCTURE ESTIMATOR TESTS
# =============================================================================

class TestHullStructureEstimator:
    """Tests for Group 100 Hull Structure estimator."""

    def test_basic_estimate(self, sample_hull_params):
        """Test basic hull weight estimation."""
        estimator = HullStructureEstimator()
        items = estimator.estimate(**sample_hull_params)

        assert len(items) > 0
        assert all(item.group == SWBSGroup.GROUP_100 for item in items)
        total_weight = sum(item.weight_kg for item in items)
        assert total_weight > 0

    def test_aluminum_lighter_than_steel(self, sample_hull_params):
        """Test aluminum produces lighter hull than steel."""
        estimator = HullStructureEstimator()

        aluminum_items = estimator.estimate(**sample_hull_params, material="aluminum_5083")
        steel_items = estimator.estimate(**sample_hull_params, material="mild_steel")

        aluminum_weight = sum(item.weight_kg for item in aluminum_items)
        steel_weight = sum(item.weight_kg for item in steel_items)

        assert aluminum_weight < steel_weight

    def test_catamaran_heavier_than_monohull(self, sample_hull_params):
        """Test catamaran produces heavier structure."""
        estimator = HullStructureEstimator()

        mono_items = estimator.estimate(**sample_hull_params, hull_type="monohull")
        cat_items = estimator.estimate(**sample_hull_params, hull_type="catamaran")

        mono_weight = sum(item.weight_kg for item in mono_items)
        cat_weight = sum(item.weight_kg for item in cat_items)

        assert cat_weight > mono_weight

    def test_watson_gilfillan_scaling(self):
        """Test weight scales with L^1.5."""
        estimator = HullStructureEstimator()

        small = estimator.estimate(lwl=20.0, beam=6.0, depth=3.0, cb=0.55)
        large = estimator.estimate(lwl=40.0, beam=6.0, depth=3.0, cb=0.55)

        small_weight = sum(item.weight_kg for item in small)
        large_weight = sum(item.weight_kg for item in large)

        # Ratio should be approximately (40/20)^1.5 = 2.83
        ratio = large_weight / small_weight
        assert 2.5 < ratio < 3.2

    def test_invalid_dimensions_raises(self):
        """Test invalid dimensions raise ValueError."""
        estimator = HullStructureEstimator()
        with pytest.raises(ValueError):
            estimator.estimate(lwl=-10.0, beam=8.0, depth=4.0, cb=0.55)


# =============================================================================
# PROPULSION PLANT ESTIMATOR TESTS
# =============================================================================

class TestPropulsionPlantEstimator:
    """Tests for Group 200 Propulsion Plant estimator."""

    def test_basic_estimate(self, sample_propulsion_params, sample_hull_params):
        """Test basic propulsion weight estimation."""
        estimator = PropulsionPlantEstimator()
        items = estimator.estimate(**sample_propulsion_params, lwl=sample_hull_params["lwl"])

        assert len(items) > 0
        assert all(item.group == SWBSGroup.GROUP_200 for item in items)

    def test_gas_turbine_lighter(self, sample_hull_params):
        """Test gas turbine produces lighter plant."""
        estimator = PropulsionPlantEstimator()

        diesel_items = estimator.estimate(
            installed_power_kw=2000.0,
            num_engines=2,
            engine_type="high_speed_diesel",
            lwl=sample_hull_params["lwl"],
        )
        turbine_items = estimator.estimate(
            installed_power_kw=2000.0,
            num_engines=2,
            engine_type="gas_turbine",
            lwl=sample_hull_params["lwl"],
        )

        diesel_weight = sum(item.weight_kg for item in diesel_items)
        turbine_weight = sum(item.weight_kg for item in turbine_items)

        assert turbine_weight < diesel_weight

    def test_power_scaling(self, sample_hull_params):
        """Test weight scales with power."""
        estimator = PropulsionPlantEstimator()

        low_power = estimator.estimate(
            installed_power_kw=1000.0,
            num_engines=2,
            lwl=sample_hull_params["lwl"],
        )
        high_power = estimator.estimate(
            installed_power_kw=4000.0,
            num_engines=2,
            lwl=sample_hull_params["lwl"],
        )

        low_weight = sum(item.weight_kg for item in low_power)
        high_weight = sum(item.weight_kg for item in high_power)

        # Should roughly scale with power
        assert 3.0 < (high_weight / low_weight) < 5.0

    def test_zero_power_returns_empty(self):
        """Test zero power returns empty list."""
        estimator = PropulsionPlantEstimator()
        items = estimator.estimate(installed_power_kw=0, num_engines=2, lwl=30.0)
        assert items == []


# =============================================================================
# ELECTRICAL PLANT ESTIMATOR TESTS
# =============================================================================

class TestElectricPlantEstimator:
    """Tests for Group 300 Electrical Plant estimator."""

    def test_basic_estimate(self, sample_hull_params):
        """Test basic electrical weight estimation."""
        estimator = ElectricPlantEstimator()
        items = estimator.estimate(
            installed_power_kw=2000.0,
            lwl=sample_hull_params["lwl"],
            depth=sample_hull_params["depth"],
        )

        assert len(items) > 0
        assert all(item.group == SWBSGroup.GROUP_300 for item in items)

    def test_generator_count_affects_weight(self, sample_hull_params):
        """Test more generators = more weight."""
        estimator = ElectricPlantEstimator()

        two_gen = estimator.estimate(
            installed_power_kw=2000.0,
            lwl=sample_hull_params["lwl"],
            depth=sample_hull_params["depth"],
            generator_count=2,
        )
        three_gen = estimator.estimate(
            installed_power_kw=2000.0,
            lwl=sample_hull_params["lwl"],
            depth=sample_hull_params["depth"],
            generator_count=3,
        )

        two_weight = sum(item.weight_kg for item in two_gen)
        three_weight = sum(item.weight_kg for item in three_gen)

        # Three generators should be heavier
        assert three_weight > two_weight


# =============================================================================
# COMMAND & SURVEILLANCE ESTIMATOR TESTS
# =============================================================================

class TestCommandSurveillanceEstimator:
    """Tests for Group 400 Command & Surveillance estimator."""

    def test_basic_estimate(self, sample_hull_params):
        """Test basic C&S weight estimation."""
        estimator = CommandSurveillanceEstimator()
        items = estimator.estimate(
            lwl=sample_hull_params["lwl"],
            depth=sample_hull_params["depth"],
        )

        assert len(items) > 0
        assert all(item.group == SWBSGroup.GROUP_400 for item in items)

    def test_military_heavier_than_commercial(self, sample_hull_params):
        """Test military vessel has heavier electronics."""
        estimator = CommandSurveillanceEstimator()

        commercial = estimator.estimate(
            lwl=sample_hull_params["lwl"],
            depth=sample_hull_params["depth"],
            vessel_type="commercial",
        )
        military = estimator.estimate(
            lwl=sample_hull_params["lwl"],
            depth=sample_hull_params["depth"],
            vessel_type="military",
        )

        commercial_weight = sum(item.weight_kg for item in commercial)
        military_weight = sum(item.weight_kg for item in military)

        assert military_weight > commercial_weight


# =============================================================================
# AUXILIARY SYSTEMS ESTIMATOR TESTS
# =============================================================================

class TestAuxiliarySystemsEstimator:
    """Tests for Group 500 Auxiliary Systems estimator."""

    def test_basic_estimate(self, sample_hull_params):
        """Test basic auxiliary weight estimation."""
        estimator = AuxiliarySystemsEstimator()
        items = estimator.estimate(
            lwl=sample_hull_params["lwl"],
            beam=sample_hull_params["beam"],
            depth=sample_hull_params["depth"],
            displacement_mt=100.0,
        )

        assert len(items) > 0
        assert all(item.group == SWBSGroup.GROUP_500 for item in items)

    def test_crew_size_affects_freshwater(self, sample_hull_params):
        """Test crew size affects freshwater system weight."""
        estimator = AuxiliarySystemsEstimator()

        small_crew = estimator.estimate(
            lwl=sample_hull_params["lwl"],
            beam=sample_hull_params["beam"],
            depth=sample_hull_params["depth"],
            displacement_mt=100.0,
            crew_size=4,
        )
        large_crew = estimator.estimate(
            lwl=sample_hull_params["lwl"],
            beam=sample_hull_params["beam"],
            depth=sample_hull_params["depth"],
            displacement_mt=100.0,
            crew_size=20,
        )

        small_weight = sum(item.weight_kg for item in small_crew)
        large_weight = sum(item.weight_kg for item in large_crew)

        assert large_weight > small_weight


# =============================================================================
# OUTFIT & FURNISHINGS ESTIMATOR TESTS
# =============================================================================

class TestOutfitFurnishingsEstimator:
    """Tests for Group 600 Outfit & Furnishings estimator."""

    def test_basic_estimate(self, sample_hull_params):
        """Test basic outfit weight estimation."""
        estimator = OutfitFurnishingsEstimator()
        items = estimator.estimate(
            lwl=sample_hull_params["lwl"],
            beam=sample_hull_params["beam"],
            depth=sample_hull_params["depth"],
        )

        assert len(items) > 0
        assert all(item.group == SWBSGroup.GROUP_600 for item in items)

    def test_passengers_add_weight(self, sample_hull_params):
        """Test passengers add accommodation weight."""
        estimator = OutfitFurnishingsEstimator()

        crew_only = estimator.estimate(
            lwl=sample_hull_params["lwl"],
            beam=sample_hull_params["beam"],
            depth=sample_hull_params["depth"],
            crew_size=6,
            passenger_count=0,
        )
        with_passengers = estimator.estimate(
            lwl=sample_hull_params["lwl"],
            beam=sample_hull_params["beam"],
            depth=sample_hull_params["depth"],
            crew_size=6,
            passenger_count=50,
        )

        crew_weight = sum(item.weight_kg for item in crew_only)
        passenger_weight = sum(item.weight_kg for item in with_passengers)

        assert passenger_weight > crew_weight


# =============================================================================
# WEIGHT AGGREGATOR TESTS
# =============================================================================

class TestWeightAggregator:
    """Tests for WeightAggregator."""

    def test_empty_raises(self):
        """Test calculating with no items raises error."""
        aggregator = WeightAggregator()
        with pytest.raises(ValueError, match="No weight items"):
            aggregator.calculate_lightship()

    def test_single_item(self):
        """Test aggregation with single item."""
        aggregator = WeightAggregator()
        aggregator.add_item(WeightItem(
            name="Test",
            weight_kg=1000.0,
            lcg_m=15.0,
            vcg_m=2.0,
            group=SWBSGroup.GROUP_100,
        ))
        aggregator.set_margins(margin_percent=0.10)
        summary = aggregator.calculate_lightship()

        assert summary.base_weight_mt == 1.0
        assert summary.lightship_weight_mt == 1.1  # Base + 10% margin
        assert summary.margin_percent == 0.10

    def test_margin_by_vessel_type(self):
        """Test margin selection by vessel type."""
        aggregator = WeightAggregator()
        aggregator.add_item(WeightItem(
            name="Test",
            weight_kg=10000.0,
            lcg_m=15.0,
            vcg_m=2.0,
            group=SWBSGroup.GROUP_100,
        ))

        aggregator.set_margins(vessel_type="patrol")
        summary = aggregator.calculate_lightship()

        # Patrol has 8% margin
        assert summary.margin_percent == 0.08

    def test_weighted_average_centers(self):
        """Test weighted average center calculation."""
        aggregator = WeightAggregator()
        # Heavy item forward
        aggregator.add_item(WeightItem(
            name="Heavy Forward",
            weight_kg=2000.0,
            lcg_m=10.0,
            vcg_m=1.0,
            group=SWBSGroup.GROUP_100,
        ))
        # Light item aft
        aggregator.add_item(WeightItem(
            name="Light Aft",
            weight_kg=1000.0,
            lcg_m=20.0,
            vcg_m=2.0,
            group=SWBSGroup.GROUP_100,
        ))

        aggregator.set_margins(margin_percent=0.0)  # No margin for cleaner test
        summary = aggregator.calculate_lightship()

        # LCG = (2000*10 + 1000*20) / 3000 = 13.33
        assert abs(summary.lightship_lcg_m - 13.333) < 0.01

    def test_group_summaries(self):
        """Test group summaries are calculated."""
        aggregator = WeightAggregator()
        aggregator.add_item(WeightItem(
            name="Hull",
            weight_kg=5000.0,
            lcg_m=15.0,
            vcg_m=1.5,
            group=SWBSGroup.GROUP_100,
        ))
        aggregator.add_item(WeightItem(
            name="Engine",
            weight_kg=3000.0,
            lcg_m=18.0,
            vcg_m=1.0,
            group=SWBSGroup.GROUP_200,
        ))

        aggregator.set_margins(margin_percent=0.0)
        summary = aggregator.calculate_lightship()

        assert SWBSGroup.GROUP_100 in summary.group_summaries
        assert SWBSGroup.GROUP_200 in summary.group_summaries
        assert summary.group_summaries[SWBSGroup.GROUP_100].total_weight_mt == 5.0
        assert summary.group_summaries[SWBSGroup.GROUP_200].total_weight_mt == 3.0


class TestLightshipSummary:
    """Tests for LightshipSummary."""

    def test_to_dict_deterministic(self):
        """Test to_dict produces deterministic output."""
        summary = LightshipSummary(
            lightship_weight_mt=50.0,
            lightship_lcg_m=15.5,
            lightship_vcg_m=2.1,
            lightship_tcg_m=0.0,
            margin_weight_mt=5.0,
            margin_vcg_m=2.2,
            margin_percent=0.10,
            base_weight_mt=45.0,
            base_lcg_m=15.5,
            base_vcg_m=2.0,
            base_tcg_m=0.0,
            group_summaries={},
            items=[],
            average_confidence=0.75,
            total_item_count=10,
        )

        d1 = summary.to_dict()
        d2 = summary.to_dict()

        # Should be identical (deterministic)
        assert json.dumps(d1, sort_keys=True) == json.dumps(d2, sort_keys=True)

    def test_get_group_percentage(self):
        """Test group percentage calculation."""
        summary = LightshipSummary(
            lightship_weight_mt=110.0,
            lightship_lcg_m=15.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            margin_weight_mt=10.0,
            margin_vcg_m=2.1,
            margin_percent=0.10,
            base_weight_mt=100.0,
            base_lcg_m=15.0,
            base_vcg_m=2.0,
            base_tcg_m=0.0,
            group_summaries={
                SWBSGroup.GROUP_100: GroupSummary(
                    group=SWBSGroup.GROUP_100,
                    name="Hull",
                    total_weight_mt=40.0,
                    lcg_m=15.0,
                    vcg_m=1.5,
                    tcg_m=0.0,
                    item_count=5,
                    average_confidence=0.8,
                ),
            },
            items=[],
            average_confidence=0.75,
            total_item_count=20,
        )

        # Hull is 40 MT of 100 MT base = 40%
        assert summary.get_group_percentage(SWBSGroup.GROUP_100) == 40.0


# =============================================================================
# DETERMINIZE_DICT TESTS
# =============================================================================

class TestDeterminizeDict:
    """Tests for determinize_dict utility (v1.1 FIX #6)."""

    def test_sorts_keys(self):
        """Test keys are sorted."""
        d = {"z": 1, "a": 2, "m": 3}
        result = determinize_dict(d)
        keys = list(result.keys())
        assert keys == sorted(keys)

    def test_rounds_floats(self):
        """Test floats are rounded."""
        d = {"value": 3.141592653589793}
        result = determinize_dict(d, precision=3)
        assert result["value"] == 3.142

    def test_nested_dict(self):
        """Test nested dictionaries are processed."""
        d = {"outer": {"z": 1, "a": 2}}
        result = determinize_dict(d)
        inner_keys = list(result["outer"].keys())
        assert inner_keys == sorted(inner_keys)

    def test_list_processing(self):
        """Test lists are processed."""
        d = {"values": [3.14159, 2.71828]}
        result = determinize_dict(d, precision=2)
        assert result["values"] == [3.14, 2.72]

    def test_deterministic_output(self):
        """Test output is deterministic."""
        d = {"z": 1.111111, "a": {"y": 2.222222, "x": 3.333333}}

        result1 = determinize_dict(d)
        result2 = determinize_dict(d)

        assert json.dumps(result1) == json.dumps(result2)


# =============================================================================
# WEIGHT ESTIMATION VALIDATOR TESTS
# =============================================================================

class TestWeightEstimationValidator:
    """Tests for WeightEstimationValidator."""

    def test_get_definition(self):
        """Test getting validator definition."""
        definition = get_weight_estimation_definition()
        assert definition.validator_id == "weight/estimation"
        assert "weight.lightship_mt" in definition.produces_parameters

    def test_validate_success(self, mock_state_manager):
        """Test successful validation."""
        validator = WeightEstimationValidator()
        result = validator.validate(mock_state_manager, {})

        assert result.state in [ValidatorState.PASSED, ValidatorState.WARNING]
        # Should have written lightship weight
        mock_state_manager.set.assert_any_call("weight.lightship_mt", pytest.approx(mock_state_manager.set.call_args_list[0][0][1], rel=0.1))

    def test_validate_missing_params(self):
        """Test validation with missing parameters."""
        manager = Mock()
        manager.get = Mock(return_value=None)
        manager.set = Mock()

        validator = WeightEstimationValidator()
        result = validator.validate(manager, {})

        assert result.state == ValidatorState.FAILED
        assert any("Missing required" in f.message for f in result.findings)


# =============================================================================
# WEIGHT STABILITY VALIDATOR TESTS
# =============================================================================

class TestWeightStabilityValidator:
    """Tests for WeightStabilityValidator."""

    def test_get_definition(self):
        """Test getting validator definition."""
        definition = get_weight_stability_definition()
        assert definition.validator_id == "weight/stability_check"
        assert "stability.kg_m" in definition.produces_parameters

    def test_validate_success(self):
        """Test successful validation with good GM."""
        manager = Mock()
        manager.get = Mock(side_effect=lambda key, default=None: {
            "weight.lightship_vcg_m": 2.0,
            "weight.lightship_mt": 50.0,
            "hull.displacement_mt": 60.0,
            "hull.kb_m": 1.2,
            "hull.bm_m": 3.5,
        }.get(key, default))
        manager.set = Mock()

        validator = WeightStabilityValidator()
        result = validator.validate(manager, {})

        assert result.state in [ValidatorState.PASSED, ValidatorState.WARNING]
        # Should write stability.kg_m (v1.1 FIX #7)
        manager.set.assert_any_call("stability.kg_m", 2.0)

    def test_validate_negative_gm_warning(self):
        """Test warning for negative GM."""
        manager = Mock()
        manager.get = Mock(side_effect=lambda key, default=None: {
            "weight.lightship_vcg_m": 5.0,  # High VCG
            "weight.lightship_mt": 50.0,
            "hull.displacement_mt": 60.0,
            "hull.kb_m": 1.0,
            "hull.bm_m": 2.0,  # KM = 3.0, KG = 5.0, GM = -2.0
        }.get(key, default))
        manager.set = Mock()

        validator = WeightStabilityValidator()
        result = validator.validate(manager, {})

        assert result.state == ValidatorState.WARNING
        assert any("Negative GM" in f.message for f in result.findings)

    def test_validate_missing_weight_params(self):
        """Test validation with missing weight parameters."""
        manager = Mock()
        manager.get = Mock(return_value=None)
        manager.set = Mock()

        validator = WeightStabilityValidator()
        result = validator.validate(manager, {})

        assert result.state == ValidatorState.FAILED
        # Should set stability_ready to False
        manager.set.assert_any_call("weight.stability_ready", False)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestWeightModuleIntegration:
    """Integration tests for the complete weight module."""

    def test_full_estimation_pipeline(self, sample_hull_params):
        """Test running all estimators and aggregating."""
        # Run all estimators
        hull_est = HullStructureEstimator()
        prop_est = PropulsionPlantEstimator()
        elec_est = ElectricPlantEstimator()
        cmd_est = CommandSurveillanceEstimator()
        aux_est = AuxiliarySystemsEstimator()
        outfit_est = OutfitFurnishingsEstimator()

        aggregator = WeightAggregator()

        aggregator.add_items(hull_est.estimate(**sample_hull_params))
        aggregator.add_items(prop_est.estimate(
            installed_power_kw=2000.0,
            num_engines=2,
            lwl=sample_hull_params["lwl"],
        ))
        aggregator.add_items(elec_est.estimate(
            installed_power_kw=2000.0,
            lwl=sample_hull_params["lwl"],
            depth=sample_hull_params["depth"],
        ))
        aggregator.add_items(cmd_est.estimate(
            lwl=sample_hull_params["lwl"],
            depth=sample_hull_params["depth"],
        ))
        aggregator.add_items(aux_est.estimate(
            lwl=sample_hull_params["lwl"],
            beam=sample_hull_params["beam"],
            depth=sample_hull_params["depth"],
            displacement_mt=100.0,
        ))
        aggregator.add_items(outfit_est.estimate(
            lwl=sample_hull_params["lwl"],
            beam=sample_hull_params["beam"],
            depth=sample_hull_params["depth"],
        ))

        aggregator.set_margins(vessel_type="patrol")
        summary = aggregator.calculate_lightship()

        # Should have reasonable results
        assert summary.lightship_weight_mt > 0
        assert summary.lightship_lcg_m > 0
        assert summary.lightship_vcg_m > 0
        assert 0 <= summary.average_confidence <= 1
        assert summary.total_item_count > 20

    def test_all_groups_represented(self, sample_hull_params):
        """Test all SWBS groups are represented in output."""
        hull_est = HullStructureEstimator()
        prop_est = PropulsionPlantEstimator()
        elec_est = ElectricPlantEstimator()
        cmd_est = CommandSurveillanceEstimator()
        aux_est = AuxiliarySystemsEstimator()
        outfit_est = OutfitFurnishingsEstimator()

        aggregator = WeightAggregator()

        aggregator.add_items(hull_est.estimate(**sample_hull_params))
        aggregator.add_items(prop_est.estimate(
            installed_power_kw=2000.0,
            num_engines=2,
            lwl=sample_hull_params["lwl"],
        ))
        aggregator.add_items(elec_est.estimate(
            installed_power_kw=2000.0,
            lwl=sample_hull_params["lwl"],
            depth=sample_hull_params["depth"],
        ))
        aggregator.add_items(cmd_est.estimate(
            lwl=sample_hull_params["lwl"],
            depth=sample_hull_params["depth"],
        ))
        aggregator.add_items(aux_est.estimate(
            lwl=sample_hull_params["lwl"],
            beam=sample_hull_params["beam"],
            depth=sample_hull_params["depth"],
            displacement_mt=100.0,
        ))
        aggregator.add_items(outfit_est.estimate(
            lwl=sample_hull_params["lwl"],
            beam=sample_hull_params["beam"],
            depth=sample_hull_params["depth"],
        ))

        aggregator.set_margins(margin_percent=0.0)
        summary = aggregator.calculate_lightship()

        # Check all groups 100-600 are present
        for group in [SWBSGroup.GROUP_100, SWBSGroup.GROUP_200, SWBSGroup.GROUP_300,
                      SWBSGroup.GROUP_400, SWBSGroup.GROUP_500, SWBSGroup.GROUP_600]:
            assert group in summary.group_summaries
            assert summary.group_summaries[group].total_weight_mt > 0
