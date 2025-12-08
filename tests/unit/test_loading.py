"""
MAGNET Loading Module Tests

Tests for Module 09: Loading Computer (v1.1)
"""

import pytest
from datetime import datetime, timezone

from magnet.loading.models import (
    LoadingConditionType, TankLoad, DeadweightItem, LoadingConditionResult
)
from magnet.loading.calculator import LoadingCalculator
from magnet.arrangement.models import Tank, FluidType


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def sample_tanks():
    """Sample tanks for testing."""
    return [
        Tank(
            tank_id="TK-FO-01P",
            name="Fuel Tank Port",
            fluid_type=FluidType.FUEL_MGO,
            length_m=4.0,
            breadth_m=1.5,
            height_m=0.8,
            lcg_m=16.0,
            vcg_m=0.4,
            tcg_m=-1.2,
            fill_percent=1.0,
        ),
        Tank(
            tank_id="TK-FO-01S",
            name="Fuel Tank Stbd",
            fluid_type=FluidType.FUEL_MGO,
            length_m=4.0,
            breadth_m=1.5,
            height_m=0.8,
            lcg_m=16.0,
            vcg_m=0.4,
            tcg_m=1.2,
            fill_percent=1.0,
        ),
        Tank(
            tank_id="TK-FW-01",
            name="Freshwater Tank",
            fluid_type=FluidType.FRESHWATER,
            length_m=2.0,
            breadth_m=1.0,
            height_m=0.8,
            lcg_m=12.0,
            vcg_m=1.0,
            tcg_m=0.0,
            fill_percent=1.0,
        ),
    ]


@pytest.fixture
def sample_deadweight_items():
    """Sample deadweight items."""
    return [
        DeadweightItem(
            item_id="DW-CREW",
            name="Crew & Effects",
            category="crew",
            weight_mt=0.5,
            lcg_m=10.0,
            vcg_m=3.5,
            tcg_m=0.0,
        ),
        DeadweightItem(
            item_id="DW-STORES",
            name="Stores",
            category="stores",
            weight_mt=0.3,
            lcg_m=12.0,
            vcg_m=2.0,
            tcg_m=0.0,
        ),
    ]


@pytest.fixture
def sample_hydrostatics():
    """Sample hydrostatic data."""
    return {
        "depth_m": 4.0,
        "tpc": 2.5,
        "mct": 15.0,
        "lcf_m": 15.0,
        "km_m": 3.5,
        "design_draft_m": 2.0,
        "design_displacement_mt": 100.0,
        "lwl_m": 30.0,
    }


# =============================================================================
# LOADING CONDITION TYPE TESTS
# =============================================================================

class TestLoadingConditionType:
    """Tests for LoadingConditionType enumeration."""

    def test_condition_types_defined(self):
        """All condition types should be defined."""
        assert LoadingConditionType.LIGHTSHIP.value == "lightship"
        assert LoadingConditionType.FULL_LOAD_DEPARTURE.value == "full_load_departure"
        assert LoadingConditionType.FULL_LOAD_ARRIVAL.value == "full_load_arrival"
        assert LoadingConditionType.MINIMUM_OPERATING.value == "minimum_operating"
        assert LoadingConditionType.BALLAST.value == "ballast"
        assert LoadingConditionType.CUSTOM.value == "custom"


# =============================================================================
# TANK LOAD TESTS
# =============================================================================

class TestTankLoad:
    """Tests for TankLoad dataclass."""

    def test_tank_load_creation(self):
        """TankLoad should be created correctly."""
        load = TankLoad(
            tank_id="TK-FO-01",
            fill_percent=0.8,
            weight_mt=4.08,
            lcg_m=16.0,
            vcg_m=0.32,
            tcg_m=-1.2,
            fsm_t_m=0.15,
        )

        assert load.tank_id == "TK-FO-01"
        assert load.fill_percent == 0.8
        assert load.fsm_t_m == 0.15

    def test_to_dict(self):
        """to_dict should serialize correctly."""
        load = TankLoad(
            tank_id="TK-FO-01",
            fill_percent=0.8,
            weight_mt=4.08,
            lcg_m=16.0,
            vcg_m=0.32,
            tcg_m=-1.2,
            fsm_t_m=0.15,
        )
        data = load.to_dict()

        assert data["tank_id"] == "TK-FO-01"
        assert data["fill_percent"] == 80.0  # Percentage
        assert "weight_mt" in data
        assert "fsm_t_m" in data


# =============================================================================
# DEADWEIGHT ITEM TESTS
# =============================================================================

class TestDeadweightItem:
    """Tests for DeadweightItem dataclass."""

    def test_deadweight_creation(self):
        """DeadweightItem should be created correctly."""
        item = DeadweightItem(
            item_id="DW-CREW",
            name="Crew & Effects",
            category="crew",
            weight_mt=0.5,
            lcg_m=10.0,
            vcg_m=3.5,
            tcg_m=0.0,
        )

        assert item.item_id == "DW-CREW"
        assert item.category == "crew"
        assert item.weight_mt == 0.5

    def test_to_dict(self):
        """to_dict should serialize correctly."""
        item = DeadweightItem(
            item_id="DW-CREW",
            name="Crew",
            category="crew",
            weight_mt=0.5,
            lcg_m=10.0,
            vcg_m=3.5,
        )
        data = item.to_dict()

        assert data["item_id"] == "DW-CREW"
        assert data["category"] == "crew"


# =============================================================================
# LOADING CONDITION RESULT TESTS
# =============================================================================

class TestLoadingConditionResult:
    """Tests for LoadingConditionResult dataclass."""

    def test_result_creation(self):
        """LoadingConditionResult should be created correctly."""
        result = LoadingConditionResult(
            condition_name="Full Load Departure",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
        )

        assert result.condition_name == "Full Load Departure"
        assert result.passes_all_criteria is True
        assert len(result.tank_loads) == 0
        assert len(result.deadweight_items) == 0

    def test_total_fsm(self):
        """total_fsm should sum all tank FSMs."""
        result = LoadingConditionResult(
            condition_name="Test",
            condition_type=LoadingConditionType.CUSTOM,
        )
        result.tank_loads = [
            TankLoad("TK-1", 0.5, 1.0, 10.0, 0.5, 0.0, fsm_t_m=0.1),
            TankLoad("TK-2", 0.6, 1.2, 12.0, 0.6, 0.0, fsm_t_m=0.15),
        ]

        assert abs(result.total_fsm - 0.25) < 0.001

    def test_is_stable_positive_gm(self):
        """Should be stable with positive GM."""
        result = LoadingConditionResult(
            condition_name="Test",
            condition_type=LoadingConditionType.CUSTOM,
        )
        result.gm_fluid_m = 0.5

        assert result.is_stable is True

    def test_is_stable_negative_gm(self):
        """Should be unstable with negative GM."""
        result = LoadingConditionResult(
            condition_name="Test",
            condition_type=LoadingConditionType.CUSTOM,
        )
        result.gm_fluid_m = -0.1

        assert result.is_stable is False

    def test_meets_imo_gm(self):
        """Should check IMO minimum GM (0.15m)."""
        result = LoadingConditionResult(
            condition_name="Test",
            condition_type=LoadingConditionType.CUSTOM,
        )

        result.gm_fluid_m = 0.20
        assert result.meets_imo_gm is True

        result.gm_fluid_m = 0.10
        assert result.meets_imo_gm is False

    def test_to_dict(self):
        """to_dict should include all fields."""
        result = LoadingConditionResult(
            condition_name="Test",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
        )
        result.displacement_mt = 100.0
        result.gm_fluid_m = 0.5

        data = result.to_dict()

        assert data["condition_name"] == "Test"
        assert data["condition_type"] == "full_load_departure"
        assert data["displacement_mt"] == 100.0
        assert "is_stable" in data
        assert "meets_imo_gm" in data


# =============================================================================
# LOADING CALCULATOR TESTS
# =============================================================================

class TestLoadingCalculator:
    """Tests for LoadingCalculator."""

    def test_calculate_condition_basic(
        self, sample_tanks, sample_deadweight_items, sample_hydrostatics
    ):
        """Should calculate basic loading condition."""
        calc = LoadingCalculator()

        result = calc.calculate_condition(
            condition_name="Test Condition",
            condition_type=LoadingConditionType.CUSTOM,
            lightship_mt=50.0,
            lightship_lcg_m=14.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            tank_fills={"TK-FO-01P": 1.0, "TK-FO-01S": 1.0, "TK-FW-01": 1.0},
            deadweight_items=sample_deadweight_items,
            **sample_hydrostatics,
        )

        assert result.condition_name == "Test Condition"
        assert result.lightship_mt == 50.0
        assert result.displacement_mt > 50.0  # Includes DW
        assert len(result.tank_loads) == 3
        assert len(result.deadweight_items) == 2

    def test_displacement_calculation(
        self, sample_tanks, sample_deadweight_items, sample_hydrostatics
    ):
        """Displacement should be sum of all weights."""
        calc = LoadingCalculator()

        result = calc.calculate_condition(
            condition_name="Test",
            condition_type=LoadingConditionType.CUSTOM,
            lightship_mt=50.0,
            lightship_lcg_m=14.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            tank_fills={"TK-FO-01P": 1.0, "TK-FO-01S": 1.0, "TK-FW-01": 1.0},
            deadweight_items=sample_deadweight_items,
            **sample_hydrostatics,
        )

        # Calculate expected
        tank_weight = sum(t.current_weight_mt for t in sample_tanks)
        dw_weight = sum(d.weight_mt for d in sample_deadweight_items)
        expected = 50.0 + tank_weight + dw_weight

        assert abs(result.displacement_mt - expected) < 0.1

    def test_vcg_calculation(
        self, sample_tanks, sample_deadweight_items, sample_hydrostatics
    ):
        """VCG should be weighted average."""
        calc = LoadingCalculator()

        result = calc.calculate_condition(
            condition_name="Test",
            condition_type=LoadingConditionType.CUSTOM,
            lightship_mt=50.0,
            lightship_lcg_m=14.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            tank_fills={"TK-FO-01P": 1.0, "TK-FO-01S": 1.0, "TK-FW-01": 1.0},
            deadweight_items=sample_deadweight_items,
            **sample_hydrostatics,
        )

        # VCG should be positive and reasonable
        assert 0 < result.vcg_m < sample_hydrostatics["depth_m"]

    def test_gm_calculation(
        self, sample_tanks, sample_deadweight_items, sample_hydrostatics
    ):
        """GM should be KM - KG - FSC."""
        calc = LoadingCalculator()

        result = calc.calculate_condition(
            condition_name="Test",
            condition_type=LoadingConditionType.CUSTOM,
            lightship_mt=50.0,
            lightship_lcg_m=14.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            tank_fills={"TK-FO-01P": 0.5, "TK-FO-01S": 0.5, "TK-FW-01": 0.5},  # Partial fill for FSM
            deadweight_items=sample_deadweight_items,
            **sample_hydrostatics,
        )

        # Check GM calculation
        expected_gm_solid = sample_hydrostatics["km_m"] - result.vcg_m
        assert abs(result.gm_solid_m - expected_gm_solid) < 0.01

        # GM fluid should be less than solid due to FSC
        assert result.gm_fluid_m <= result.gm_solid_m

    def test_free_surface_correction(
        self, sample_tanks, sample_hydrostatics
    ):
        """FSC should be calculated for partial fills."""
        calc = LoadingCalculator()

        # Partial fill to activate free surface
        result = calc.calculate_condition(
            condition_name="Test",
            condition_type=LoadingConditionType.CUSTOM,
            lightship_mt=50.0,
            lightship_lcg_m=14.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            tank_fills={"TK-FO-01P": 0.5, "TK-FO-01S": 0.5, "TK-FW-01": 0.5},
            deadweight_items=[],
            **sample_hydrostatics,
        )

        # FSC should be positive with partial fills
        assert result.fsc_m >= 0
        assert result.total_fsm > 0

    def test_no_fsc_full_tanks(
        self, sample_tanks, sample_hydrostatics
    ):
        """Full tanks should have no FSC."""
        calc = LoadingCalculator()

        result = calc.calculate_condition(
            condition_name="Test",
            condition_type=LoadingConditionType.CUSTOM,
            lightship_mt=50.0,
            lightship_lcg_m=14.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            tank_fills={"TK-FO-01P": 1.0, "TK-FO-01S": 1.0, "TK-FW-01": 1.0},
            deadweight_items=[],
            **sample_hydrostatics,
        )

        assert result.total_fsm == 0
        assert result.fsc_m == 0

    def test_draft_calculation_v11(
        self, sample_tanks, sample_hydrostatics
    ):
        """FIX v1.1 CI#6: Draft should use design displacement scaling."""
        calc = LoadingCalculator()

        result = calc.calculate_condition(
            condition_name="Test",
            condition_type=LoadingConditionType.CUSTOM,
            lightship_mt=50.0,
            lightship_lcg_m=14.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            tank_fills={"TK-FO-01P": 1.0, "TK-FO-01S": 1.0, "TK-FW-01": 1.0},
            deadweight_items=[],
            **sample_hydrostatics,
        )

        # Draft should be calculated (cube root scaling)
        assert result.draft_m > 0
        assert result.draft_m < sample_hydrostatics["depth_m"]

    def test_trim_calculation(
        self, sample_tanks, sample_hydrostatics
    ):
        """Trim should be calculated from LCG vs LCB."""
        calc = LoadingCalculator()

        result = calc.calculate_condition(
            condition_name="Test",
            condition_type=LoadingConditionType.CUSTOM,
            lightship_mt=50.0,
            lightship_lcg_m=14.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            tank_fills={"TK-FO-01P": 1.0, "TK-FO-01S": 1.0, "TK-FW-01": 1.0},
            deadweight_items=[],
            **sample_hydrostatics,
        )

        # Trim should be small for balanced loading
        assert abs(result.trim_m) < sample_hydrostatics["lwl_m"] * 0.1

    def test_freeboard_calculation(
        self, sample_tanks, sample_hydrostatics
    ):
        """Freeboard should be depth - draft."""
        calc = LoadingCalculator()

        result = calc.calculate_condition(
            condition_name="Test",
            condition_type=LoadingConditionType.CUSTOM,
            lightship_mt=50.0,
            lightship_lcg_m=14.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            tank_fills={"TK-FO-01P": 1.0, "TK-FO-01S": 1.0, "TK-FW-01": 1.0},
            deadweight_items=[],
            **sample_hydrostatics,
        )

        expected = sample_hydrostatics["depth_m"] - result.draft_m
        assert abs(result.freeboard_m - expected) < 0.001

    def test_negative_gm_error(self, sample_tanks, sample_hydrostatics):
        """Negative GM should trigger error."""
        calc = LoadingCalculator()

        # High VCG to force negative GM
        result = calc.calculate_condition(
            condition_name="Test",
            condition_type=LoadingConditionType.CUSTOM,
            lightship_mt=50.0,
            lightship_lcg_m=14.0,
            lightship_vcg_m=5.0,  # Very high VCG
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            tank_fills={"TK-FO-01P": 1.0, "TK-FO-01S": 1.0, "TK-FW-01": 1.0},
            deadweight_items=[],
            **sample_hydrostatics,
        )

        if result.gm_fluid_m < 0:
            assert result.passes_all_criteria is False
            assert len(result.errors) > 0

    def test_create_standard_conditions(
        self, sample_tanks, sample_hydrostatics
    ):
        """Should create all standard conditions."""
        calc = LoadingCalculator()

        conditions = calc.create_standard_conditions(
            lightship_mt=50.0,
            lightship_lcg_m=14.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            crew_weight_mt=0.5,
            stores_weight_mt=0.3,
            lcg_crew_m=10.0,
            lcg_stores_m=12.0,
            vcg_crew_m=3.5,
            vcg_stores_m=2.0,
            **sample_hydrostatics,
        )

        # Should have all standard conditions
        assert "full_load_departure" in conditions
        assert "full_load_arrival" in conditions
        assert "minimum_operating" in conditions
        assert "lightship" in conditions

    def test_full_load_departure_has_full_tanks(
        self, sample_tanks, sample_hydrostatics
    ):
        """Full load departure should have full consumables."""
        calc = LoadingCalculator()

        conditions = calc.create_standard_conditions(
            lightship_mt=50.0,
            lightship_lcg_m=14.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            crew_weight_mt=0.5,
            stores_weight_mt=0.3,
            lcg_crew_m=10.0,
            lcg_stores_m=12.0,
            vcg_crew_m=3.5,
            vcg_stores_m=2.0,
            **sample_hydrostatics,
        )

        fld = conditions["full_load_departure"]

        # Tanks should be at 100%
        for tank_load in fld.tank_loads:
            assert tank_load.fill_percent == 1.0

    def test_arrival_has_depleted_consumables(
        self, sample_tanks, sample_hydrostatics
    ):
        """Arrival condition should have depleted consumables."""
        calc = LoadingCalculator()

        conditions = calc.create_standard_conditions(
            lightship_mt=50.0,
            lightship_lcg_m=14.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            crew_weight_mt=0.5,
            stores_weight_mt=0.3,
            lcg_crew_m=10.0,
            lcg_stores_m=12.0,
            vcg_crew_m=3.5,
            vcg_stores_m=2.0,
            **sample_hydrostatics,
        )

        fla = conditions["full_load_arrival"]

        # Fuel and freshwater should be depleted
        for tank_load in fla.tank_loads:
            if "FO" in tank_load.tank_id or "FW" in tank_load.tank_id:
                assert tank_load.fill_percent < 0.2

    def test_lightship_has_no_deadweight(
        self, sample_tanks, sample_hydrostatics
    ):
        """Lightship condition should have no deadweight."""
        calc = LoadingCalculator()

        conditions = calc.create_standard_conditions(
            lightship_mt=50.0,
            lightship_lcg_m=14.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            crew_weight_mt=0.5,
            stores_weight_mt=0.3,
            lcg_crew_m=10.0,
            lcg_stores_m=12.0,
            vcg_crew_m=3.5,
            vcg_stores_m=2.0,
            **sample_hydrostatics,
        )

        ls = conditions["lightship"]

        # No deadweight items
        assert len(ls.deadweight_items) == 0

        # All tanks empty
        for tank_load in ls.tank_loads:
            assert tank_load.fill_percent == 0.0


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestLoadingIntegration:
    """Integration tests for loading calculations."""

    def test_all_conditions_consistent(
        self, sample_tanks, sample_hydrostatics
    ):
        """All conditions should have consistent physics."""
        calc = LoadingCalculator()

        conditions = calc.create_standard_conditions(
            lightship_mt=50.0,
            lightship_lcg_m=14.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            crew_weight_mt=0.5,
            stores_weight_mt=0.3,
            lcg_crew_m=10.0,
            lcg_stores_m=12.0,
            vcg_crew_m=3.5,
            vcg_stores_m=2.0,
            **sample_hydrostatics,
        )

        for name, cond in conditions.items():
            # Displacement should be positive
            assert cond.displacement_mt > 0, f"{name}: invalid displacement"

            # VCG should be positive
            assert cond.vcg_m > 0, f"{name}: invalid VCG"

            # KM should be from input
            assert cond.km_m == sample_hydrostatics["km_m"], f"{name}: invalid KM"

    def test_departure_heavier_than_arrival(
        self, sample_tanks, sample_hydrostatics
    ):
        """Departure should be heavier than arrival."""
        calc = LoadingCalculator()

        conditions = calc.create_standard_conditions(
            lightship_mt=50.0,
            lightship_lcg_m=14.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            crew_weight_mt=0.5,
            stores_weight_mt=0.3,
            lcg_crew_m=10.0,
            lcg_stores_m=12.0,
            vcg_crew_m=3.5,
            vcg_stores_m=2.0,
            **sample_hydrostatics,
        )

        fld = conditions["full_load_departure"]
        fla = conditions["full_load_arrival"]

        assert fld.displacement_mt > fla.displacement_mt

    def test_lightship_lightest(
        self, sample_tanks, sample_hydrostatics
    ):
        """Lightship should be lightest condition."""
        calc = LoadingCalculator()

        conditions = calc.create_standard_conditions(
            lightship_mt=50.0,
            lightship_lcg_m=14.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            crew_weight_mt=0.5,
            stores_weight_mt=0.3,
            lcg_crew_m=10.0,
            lcg_stores_m=12.0,
            vcg_crew_m=3.5,
            vcg_stores_m=2.0,
            **sample_hydrostatics,
        )

        ls = conditions["lightship"]

        for name, cond in conditions.items():
            if name != "lightship":
                assert ls.displacement_mt <= cond.displacement_mt
