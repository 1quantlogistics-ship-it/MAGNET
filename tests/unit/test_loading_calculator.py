"""
Unit tests for loading calculator.

Tests LoadingCalculator with v1.1 fixes.
"""

import pytest
from magnet.loading.calculator import LoadingCalculator
from magnet.loading.models import LoadingConditionType, DeadweightItem
from magnet.arrangement.models import Tank, FluidType


class TestLoadingCalculator:
    """Tests for LoadingCalculator."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return LoadingCalculator()

    @pytest.fixture
    def sample_tanks(self):
        """Create sample tanks for testing."""
        return [
            Tank(
                tank_id="TK-FO-01",
                name="Fuel Tank 1",
                fluid_type=FluidType.FUEL_MGO,
                length_m=5.0,
                breadth_m=3.0,
                height_m=1.5,
                lcg_m=25.0,
                vcg_m=0.75,
                tcg_m=-2.0,
                fill_percent=1.0,
            ),
            Tank(
                tank_id="TK-FO-02",
                name="Fuel Tank 2",
                fluid_type=FluidType.FUEL_MGO,
                length_m=5.0,
                breadth_m=3.0,
                height_m=1.5,
                lcg_m=25.0,
                vcg_m=0.75,
                tcg_m=2.0,
                fill_percent=1.0,
            ),
            Tank(
                tank_id="TK-FW-01",
                name="Freshwater Tank",
                fluid_type=FluidType.FRESHWATER,
                length_m=2.0,
                breadth_m=1.5,
                height_m=1.0,
                lcg_m=20.0,
                vcg_m=2.0,
                tcg_m=0.0,
                fill_percent=1.0,
            ),
        ]

    def test_basic_calculation(self, calculator, sample_tanks):
        """Test basic loading condition calculation."""
        result = calculator.calculate_condition(
            condition_name="Test Condition",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            lightship_mt=100.0,
            lightship_lcg_m=25.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            tank_fills={"TK-FO-01": 1.0, "TK-FO-02": 1.0, "TK-FW-01": 1.0},
            deadweight_items=[],
            depth_m=4.0,
            tpc=5.0,
            mct=200.0,
            lcf_m=25.0,
            km_m=5.0,
            design_draft_m=2.5,
            design_displacement_mt=150.0,
            lwl_m=50.0,
        )

        assert result.condition_name == "Test Condition"
        assert result.lightship_mt == 100.0
        assert result.displacement_mt > 100.0  # Should include tank weights

    def test_deadweight_items_added(self, calculator, sample_tanks):
        """Test deadweight items are included."""
        crew = DeadweightItem(
            item_id="DW-CREW",
            name="Crew",
            category="crew",
            weight_mt=0.5,
            lcg_m=20.0,
            vcg_m=3.5,
        )
        stores = DeadweightItem(
            item_id="DW-STORES",
            name="Stores",
            category="stores",
            weight_mt=1.5,
            lcg_m=22.0,
            vcg_m=2.5,
        )

        result = calculator.calculate_condition(
            condition_name="Test",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            lightship_mt=100.0,
            lightship_lcg_m=25.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            tank_fills={},
            deadweight_items=[crew, stores],
            depth_m=4.0,
            tpc=5.0,
            mct=200.0,
            lcf_m=25.0,
            km_m=5.0,
            design_draft_m=2.5,
            design_displacement_mt=150.0,
            lwl_m=50.0,
        )

        assert len(result.deadweight_items) == 2
        assert result.deadweight_mt >= 2.0  # Crew + stores

    def test_free_surface_correction(self, calculator):
        """Test free surface correction applied."""
        # Create tanks with free surface (partially filled)
        tanks = [
            Tank(
                tank_id="TK-01",
                name="Tank 1",
                fluid_type=FluidType.SEAWATER,
                length_m=6.0,
                breadth_m=4.0,
                height_m=2.0,
                lcg_m=25.0,
                vcg_m=1.0,
                fill_percent=0.5,  # Partial fill = free surface
            ),
        ]

        result = calculator.calculate_condition(
            condition_name="Test",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            lightship_mt=100.0,
            lightship_lcg_m=25.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=tanks,
            tank_fills={"TK-01": 0.5},
            deadweight_items=[],
            depth_m=4.0,
            tpc=5.0,
            mct=200.0,
            lcf_m=25.0,
            km_m=5.0,
            design_draft_m=2.5,
            design_displacement_mt=150.0,
            lwl_m=50.0,
        )

        # FSC should be positive (GM_solid - GM_fluid = FSC)
        assert result.fsc_m > 0
        assert result.gm_fluid_m < result.gm_solid_m

    def test_gm_calculation(self, calculator, sample_tanks):
        """Test GM calculation."""
        result = calculator.calculate_condition(
            condition_name="Test",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            lightship_mt=100.0,
            lightship_lcg_m=25.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            tank_fills={"TK-FO-01": 1.0, "TK-FO-02": 1.0, "TK-FW-01": 1.0},
            deadweight_items=[],
            depth_m=4.0,
            tpc=5.0,
            mct=200.0,
            lcf_m=25.0,
            km_m=5.0,  # KM = 5.0m
            design_draft_m=2.5,
            design_displacement_mt=150.0,
            lwl_m=50.0,
        )

        # GM_solid = KM - KG
        assert result.km_m == 5.0
        expected_gm_solid = 5.0 - result.vcg_m
        assert abs(result.gm_solid_m - expected_gm_solid) < 0.01

    def test_draft_calculation_v11(self, calculator, sample_tanks):
        """Test v1.1: draft calculation using design displacement."""
        depth_m = 4.0
        result = calculator.calculate_condition(
            condition_name="Test",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            lightship_mt=100.0,
            lightship_lcg_m=25.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            tank_fills={"TK-FO-01": 1.0, "TK-FO-02": 1.0, "TK-FW-01": 1.0},
            deadweight_items=[],
            depth_m=depth_m,
            tpc=5.0,
            mct=200.0,
            lcf_m=25.0,
            km_m=5.0,
            design_draft_m=2.5,
            design_displacement_mt=150.0,  # v1.1: uses this for draft calc
            lwl_m=50.0,
        )

        # Draft should be calculated using cube root scaling
        # If displacement_mt > design_displacement, draft > design_draft
        assert result.draft_m > 0
        assert result.draft_m < depth_m * 0.95  # Reasonable range

    def test_negative_gm_error(self, calculator):
        """Test negative GM produces error."""
        # Use no tanks, so only lightship VCG matters
        result = calculator.calculate_condition(
            condition_name="Test",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            lightship_mt=100.0,
            lightship_lcg_m=25.0,
            lightship_vcg_m=6.0,  # Very high VCG above KM
            lightship_tcg_m=0.0,
            tanks=[],  # No tanks
            tank_fills={},
            deadweight_items=[],
            depth_m=4.0,
            tpc=5.0,
            mct=200.0,
            lcf_m=25.0,
            km_m=5.0,  # KM below VCG = negative GM
            design_draft_m=2.5,
            design_displacement_mt=150.0,
            lwl_m=50.0,
        )

        assert result.gm_fluid_m < 0
        assert result.passes_all_criteria is False
        assert any("Negative GM" in e for e in result.errors)

    def test_low_gm_warning(self, calculator):
        """Test low GM produces warning."""
        # Use no tanks, so only lightship VCG matters
        result = calculator.calculate_condition(
            condition_name="Test",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            lightship_mt=100.0,
            lightship_lcg_m=25.0,
            lightship_vcg_m=4.9,  # VCG just below KM
            lightship_tcg_m=0.0,
            tanks=[],  # No tanks to keep VCG at 4.9
            tank_fills={},
            deadweight_items=[],
            depth_m=4.0,
            tpc=5.0,
            mct=200.0,
            lcf_m=25.0,
            km_m=5.0,  # GM = 5.0 - 4.9 = 0.1m (< 0.15)
            design_draft_m=2.5,
            design_displacement_mt=150.0,
            lwl_m=50.0,
        )

        assert result.gm_fluid_m < 0.15
        assert any("0.15" in w for w in result.warnings)

    def test_trim_calculation(self, calculator, sample_tanks):
        """Test trim is calculated."""
        result = calculator.calculate_condition(
            condition_name="Test",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            lightship_mt=100.0,
            lightship_lcg_m=25.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            tank_fills={},
            deadweight_items=[],
            depth_m=4.0,
            tpc=5.0,
            mct=200.0,
            lcf_m=25.0,
            km_m=5.0,
            design_draft_m=2.5,
            design_displacement_mt=150.0,
            lwl_m=50.0,
        )

        # Trim should be calculated
        assert result.trim_m is not None
        # Draft fwd/aft should be set
        assert result.draft_fwd_m is not None
        assert result.draft_aft_m is not None

    def test_freeboard_calculation(self, calculator, sample_tanks):
        """Test freeboard is calculated."""
        result = calculator.calculate_condition(
            condition_name="Test",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            lightship_mt=100.0,
            lightship_lcg_m=25.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            tank_fills={},
            deadweight_items=[],
            depth_m=4.0,  # Depth
            tpc=5.0,
            mct=200.0,
            lcf_m=25.0,
            km_m=5.0,
            design_draft_m=2.5,  # Draft
            design_displacement_mt=150.0,
            lwl_m=50.0,
        )

        # Freeboard = depth - draft
        assert result.freeboard_m > 0
        assert abs(result.freeboard_m - (4.0 - result.draft_m)) < 0.01


class TestStandardConditions:
    """Tests for standard loading conditions."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return LoadingCalculator()

    @pytest.fixture
    def sample_tanks(self):
        """Create sample tanks."""
        return [
            Tank(
                tank_id="TK-FO-01",
                name="Fuel",
                fluid_type=FluidType.FUEL_MGO,
                length_m=5.0,
                breadth_m=3.0,
                height_m=1.5,
                lcg_m=25.0,
                vcg_m=0.75,
                fill_percent=1.0,
            ),
            Tank(
                tank_id="TK-FW-01",
                name="Freshwater",
                fluid_type=FluidType.FRESHWATER,
                length_m=2.0,
                breadth_m=1.5,
                height_m=1.0,
                lcg_m=20.0,
                vcg_m=2.0,
                fill_percent=1.0,
            ),
        ]

    def test_creates_standard_conditions(self, calculator, sample_tanks):
        """Test standard conditions are created."""
        conditions = calculator.create_standard_conditions(
            lightship_mt=100.0,
            lightship_lcg_m=25.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            crew_weight_mt=0.5,
            stores_weight_mt=1.0,
            lcg_crew_m=20.0,
            lcg_stores_m=22.0,
            vcg_crew_m=3.5,
            vcg_stores_m=2.5,
            depth_m=4.0,
            tpc=5.0,
            mct=200.0,
            lcf_m=25.0,
            km_m=5.0,
            design_draft_m=2.5,
            design_displacement_mt=150.0,
            lwl_m=50.0,
        )

        assert "full_load_departure" in conditions
        assert "full_load_arrival" in conditions
        assert "minimum_operating" in conditions
        assert "lightship" in conditions

    def test_full_load_departure_heaviest(self, calculator, sample_tanks):
        """Test full load departure is heaviest condition."""
        conditions = calculator.create_standard_conditions(
            lightship_mt=100.0,
            lightship_lcg_m=25.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            crew_weight_mt=0.5,
            stores_weight_mt=1.0,
            lcg_crew_m=20.0,
            lcg_stores_m=22.0,
            vcg_crew_m=3.5,
            vcg_stores_m=2.5,
            depth_m=4.0,
            tpc=5.0,
            mct=200.0,
            lcf_m=25.0,
            km_m=5.0,
            design_draft_m=2.5,
            design_displacement_mt=150.0,
            lwl_m=50.0,
        )

        fld = conditions["full_load_departure"]
        fla = conditions["full_load_arrival"]
        moc = conditions["minimum_operating"]
        ls = conditions["lightship"]

        assert fld.displacement_mt >= fla.displacement_mt
        assert fla.displacement_mt >= moc.displacement_mt
        assert moc.displacement_mt >= ls.displacement_mt

    def test_lightship_condition(self, calculator, sample_tanks):
        """Test lightship condition has no deadweight."""
        conditions = calculator.create_standard_conditions(
            lightship_mt=100.0,
            lightship_lcg_m=25.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=sample_tanks,
            crew_weight_mt=0.5,
            stores_weight_mt=1.0,
            lcg_crew_m=20.0,
            lcg_stores_m=22.0,
            vcg_crew_m=3.5,
            vcg_stores_m=2.5,
            depth_m=4.0,
            tpc=5.0,
            mct=200.0,
            lcf_m=25.0,
            km_m=5.0,
            design_draft_m=2.5,
            design_displacement_mt=150.0,
            lwl_m=50.0,
        )

        ls = conditions["lightship"]
        assert ls.displacement_mt == 100.0  # Just lightship
        assert len(ls.deadweight_items) == 0
