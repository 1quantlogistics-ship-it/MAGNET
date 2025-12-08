"""
Unit tests for loading models.

Tests LoadingConditionType, TankLoad, DeadweightItem, LoadingConditionResult.
"""

import pytest
from magnet.loading.models import (
    LoadingConditionType,
    TankLoad,
    DeadweightItem,
    LoadingConditionResult,
)


class TestLoadingConditionType:
    """Tests for LoadingConditionType enum."""

    def test_all_types_exist(self):
        """Test all expected condition types are defined."""
        assert LoadingConditionType.LIGHTSHIP.value == "lightship"
        assert LoadingConditionType.FULL_LOAD_DEPARTURE.value == "full_load_departure"
        assert LoadingConditionType.FULL_LOAD_ARRIVAL.value == "full_load_arrival"
        assert LoadingConditionType.MINIMUM_OPERATING.value == "minimum_operating"
        assert LoadingConditionType.BALLAST.value == "ballast"
        assert LoadingConditionType.CUSTOM.value == "custom"


class TestTankLoad:
    """Tests for TankLoad dataclass."""

    def test_basic_creation(self):
        """Test basic tank load creation."""
        load = TankLoad(
            tank_id="TK-01",
            fill_percent=0.8,
            weight_mt=25.0,
            lcg_m=25.0,
            vcg_m=1.5,
            tcg_m=0.0,
            fsm_t_m=5.2,
        )
        assert load.tank_id == "TK-01"
        assert load.fill_percent == 0.8
        assert load.weight_mt == 25.0
        assert load.fsm_t_m == 5.2

    def test_to_dict(self):
        """Test tank load serialization."""
        load = TankLoad(
            tank_id="TK-01",
            fill_percent=0.8,
            weight_mt=25.123,
            lcg_m=25.456,
            vcg_m=1.789,
            tcg_m=0.0,
            fsm_t_m=5.234,
        )
        d = load.to_dict()
        assert d["tank_id"] == "TK-01"
        assert d["fill_percent"] == 80.0  # Converted to percentage
        assert d["weight_mt"] == 25.123
        assert d["lcg_m"] == 25.456
        assert d["vcg_m"] == 1.789
        assert d["fsm_t_m"] == 5.234


class TestDeadweightItem:
    """Tests for DeadweightItem dataclass."""

    def test_basic_creation(self):
        """Test basic deadweight item creation."""
        item = DeadweightItem(
            item_id="DW-01",
            name="Crew & Effects",
            category="crew",
            weight_mt=0.6,
            lcg_m=20.0,
            vcg_m=3.5,
        )
        assert item.item_id == "DW-01"
        assert item.name == "Crew & Effects"
        assert item.category == "crew"
        assert item.weight_mt == 0.6

    def test_to_dict(self):
        """Test deadweight item serialization."""
        item = DeadweightItem(
            item_id="DW-01",
            name="Stores",
            category="stores",
            weight_mt=2.5,
            lcg_m=22.0,
            vcg_m=2.0,
            tcg_m=0.5,
        )
        d = item.to_dict()
        assert d["item_id"] == "DW-01"
        assert d["name"] == "Stores"
        assert d["category"] == "stores"
        assert d["weight_mt"] == 2.5
        assert d["tcg_m"] == 0.5


class TestLoadingConditionResult:
    """Tests for LoadingConditionResult dataclass."""

    def test_basic_creation(self):
        """Test basic result creation."""
        result = LoadingConditionResult(
            condition_name="Full Load Departure",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
        )
        assert result.condition_name == "Full Load Departure"
        assert result.condition_type == LoadingConditionType.FULL_LOAD_DEPARTURE

    def test_default_values(self):
        """Test default values are set."""
        result = LoadingConditionResult(
            condition_name="Test",
            condition_type=LoadingConditionType.CUSTOM,
        )
        assert result.lightship_mt == 0.0
        assert result.deadweight_mt == 0.0
        assert result.displacement_mt == 0.0
        assert result.passes_all_criteria is True
        assert result.warnings == []
        assert result.errors == []

    def test_total_fsm(self):
        """Test total free surface moment calculation."""
        result = LoadingConditionResult(
            condition_name="Test",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            tank_loads=[
                TankLoad("TK-01", 0.5, 10.0, 20.0, 1.5, 0.0, 5.0),
                TankLoad("TK-02", 0.5, 8.0, 25.0, 1.5, 0.0, 3.5),
                TankLoad("TK-03", 1.0, 12.0, 30.0, 1.5, 0.0, 0.0),  # Full tank
            ],
        )
        assert result.total_fsm == 8.5  # 5.0 + 3.5 + 0.0

    def test_is_stable_positive_gm(self):
        """Test stability check with positive GM."""
        result = LoadingConditionResult(
            condition_name="Test",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            gm_fluid_m=1.5,
        )
        assert result.is_stable is True

    def test_is_stable_negative_gm(self):
        """Test stability check with negative GM."""
        result = LoadingConditionResult(
            condition_name="Test",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            gm_fluid_m=-0.5,
        )
        assert result.is_stable is False

    def test_meets_imo_gm_above_minimum(self):
        """Test IMO GM check above minimum."""
        result = LoadingConditionResult(
            condition_name="Test",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            gm_fluid_m=0.25,
        )
        assert result.meets_imo_gm is True

    def test_meets_imo_gm_below_minimum(self):
        """Test IMO GM check below minimum (0.15m)."""
        result = LoadingConditionResult(
            condition_name="Test",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            gm_fluid_m=0.10,
        )
        assert result.meets_imo_gm is False

    def test_to_dict(self):
        """Test result serialization."""
        result = LoadingConditionResult(
            condition_name="Full Load Departure",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            lightship_mt=150.0,
            deadweight_mt=50.0,
            displacement_mt=200.0,
            lcg_m=25.0,
            vcg_m=2.5,
            draft_m=2.0,
            gm_solid_m=2.0,
            gm_fluid_m=1.8,
        )
        d = result.to_dict()
        assert d["condition_name"] == "Full Load Departure"
        assert d["condition_type"] == "full_load_departure"
        assert d["lightship_mt"] == 150.0
        assert d["displacement_mt"] == 200.0
        assert d["gm_fluid_m"] == 1.8

    def test_to_dict_includes_status(self):
        """Test serialization includes status flags."""
        result = LoadingConditionResult(
            condition_name="Test",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            gm_fluid_m=1.5,
            passes_all_criteria=True,
        )
        d = result.to_dict()
        assert d["is_stable"] is True
        assert d["meets_imo_gm"] is True
        assert d["passes_all_criteria"] is True

    def test_to_dict_includes_warnings_errors(self):
        """Test serialization includes warnings and errors."""
        result = LoadingConditionResult(
            condition_name="Test",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            warnings=["Low freeboard"],
            errors=["Negative GM"],
        )
        d = result.to_dict()
        assert "Low freeboard" in d["warnings"]
        assert "Negative GM" in d["errors"]
