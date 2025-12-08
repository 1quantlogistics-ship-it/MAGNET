"""
Integration tests for arrangement and loading pipeline.

Tests full flow from arrangement generation through loading calculations.
"""

import pytest
from magnet.arrangement.generator import ArrangementGenerator, VesselServiceProfile
from magnet.arrangement.models import FluidType, GeneralArrangement
from magnet.loading.calculator import LoadingCalculator
from magnet.loading.models import LoadingConditionType, DeadweightItem


class TestArrangementLoadingPipeline:
    """Test full arrangement to loading pipeline."""

    def test_full_pipeline_execution(self):
        """Test complete pipeline from arrangement to loading."""
        # Step 1: Generate arrangement
        gen = ArrangementGenerator()
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
            vessel_type="patrol",
            crew_size=6,
            range_nm=500,
            installed_power_kw=2000,
        )

        assert arr.lwl_m == 50.0
        assert len(arr.tanks) > 0

        # Step 2: Calculate loading condition
        calc = LoadingCalculator()
        result = calc.calculate_condition(
            condition_name="Full Load Departure",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            lightship_mt=150.0,
            lightship_lcg_m=25.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=arr.tanks,
            tank_fills={t.tank_id: 1.0 for t in arr.tanks},
            deadweight_items=[
                DeadweightItem("DW-CREW", "Crew", "crew", 0.6, 20.0, 3.5),
                DeadweightItem("DW-STORES", "Stores", "stores", 1.5, 22.0, 2.5),
            ],
            depth_m=arr.depth_m,
            tpc=5.0,
            mct=200.0,
            lcf_m=25.0,
            km_m=5.0,
            design_draft_m=2.5,
            design_displacement_mt=200.0,
            lwl_m=arr.lwl_m,
        )

        assert result.displacement_mt > 150.0
        assert result.gm_fluid_m > 0

    def test_pipeline_with_service_profile(self):
        """Test pipeline respects service profile."""
        # Generate with minimal services (like a RIB)
        gen = ArrangementGenerator()
        services = VesselServiceProfile(
            fuel=True,
            freshwater=False,
            sewage=False,
            lube_oil=False,
            ballast=False,
        )
        arr = gen.generate(
            lwl=8.0,
            beam=2.5,
            depth=1.0,
            draft=0.4,
            services=services,
        )

        # Should only have fuel tanks
        fuel_tanks = arr.get_tanks_by_type(FluidType.FUEL_MGO)
        fw_tanks = arr.get_tanks_by_type(FluidType.FRESHWATER)

        assert len(fuel_tanks) > 0
        assert len(fw_tanks) == 0

    def test_standard_conditions_pipeline(self):
        """Test standard conditions creation through pipeline."""
        # Generate arrangement
        gen = ArrangementGenerator()
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
        )

        # Create standard loading conditions
        calc = LoadingCalculator()
        conditions = calc.create_standard_conditions(
            lightship_mt=150.0,
            lightship_lcg_m=25.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=arr.tanks,
            crew_weight_mt=0.6,
            stores_weight_mt=1.5,
            lcg_crew_m=20.0,
            lcg_stores_m=22.0,
            vcg_crew_m=3.5,
            vcg_stores_m=2.5,
            depth_m=arr.depth_m,
            tpc=5.0,
            mct=200.0,
            lcf_m=25.0,
            km_m=5.0,
            design_draft_m=2.5,
            design_displacement_mt=200.0,
            lwl_m=arr.lwl_m,
        )

        # Verify all standard conditions created
        assert "full_load_departure" in conditions
        assert "full_load_arrival" in conditions
        assert "minimum_operating" in conditions
        assert "lightship" in conditions

        # FLD should have highest displacement
        fld = conditions["full_load_departure"]
        fla = conditions["full_load_arrival"]

        assert fld.displacement_mt > fla.displacement_mt

    def test_tank_fill_affects_loading(self):
        """Test tank fill levels affect loading results."""
        gen = ArrangementGenerator()
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
        )

        calc = LoadingCalculator()

        # Full tanks
        full_result = calc.calculate_condition(
            condition_name="Full Tanks",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            lightship_mt=150.0,
            lightship_lcg_m=25.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=arr.tanks,
            tank_fills={t.tank_id: 1.0 for t in arr.tanks},
            deadweight_items=[],
            depth_m=4.0,
            tpc=5.0,
            mct=200.0,
            lcf_m=25.0,
            km_m=5.0,
            design_draft_m=2.5,
            design_displacement_mt=200.0,
            lwl_m=50.0,
        )

        # Empty tanks
        empty_result = calc.calculate_condition(
            condition_name="Empty Tanks",
            condition_type=LoadingConditionType.LIGHTSHIP,
            lightship_mt=150.0,
            lightship_lcg_m=25.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=arr.tanks,
            tank_fills={t.tank_id: 0.0 for t in arr.tanks},
            deadweight_items=[],
            depth_m=4.0,
            tpc=5.0,
            mct=200.0,
            lcf_m=25.0,
            km_m=5.0,
            design_draft_m=2.5,
            design_displacement_mt=200.0,
            lwl_m=50.0,
        )

        # Full should be heavier
        assert full_result.displacement_mt > empty_result.displacement_mt
        assert full_result.draft_m > empty_result.draft_m


class TestFreeSurfaceIntegration:
    """Test free surface effects through pipeline."""

    def test_partial_fill_creates_fsm(self):
        """Test partial fill creates free surface moment."""
        gen = ArrangementGenerator()
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
        )

        calc = LoadingCalculator()

        # Partial fill for free surface
        partial_fills = {t.tank_id: 0.5 for t in arr.tanks}

        result = calc.calculate_condition(
            condition_name="Partial Fill",
            condition_type=LoadingConditionType.CUSTOM,
            lightship_mt=150.0,
            lightship_lcg_m=25.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=arr.tanks,
            tank_fills=partial_fills,
            deadweight_items=[],
            depth_m=4.0,
            tpc=5.0,
            mct=200.0,
            lcf_m=25.0,
            km_m=5.0,
            design_draft_m=2.5,
            design_displacement_mt=200.0,
            lwl_m=50.0,
        )

        # Should have free surface correction
        assert result.fsc_m > 0
        assert result.gm_fluid_m < result.gm_solid_m

    def test_full_tanks_no_fsm(self):
        """Test full tanks have no free surface moment."""
        gen = ArrangementGenerator()
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
        )

        calc = LoadingCalculator()

        # Full fill = no free surface
        full_fills = {t.tank_id: 1.0 for t in arr.tanks}

        result = calc.calculate_condition(
            condition_name="Full Fill",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            lightship_mt=150.0,
            lightship_lcg_m=25.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=arr.tanks,
            tank_fills=full_fills,
            deadweight_items=[],
            depth_m=4.0,
            tpc=5.0,
            mct=200.0,
            lcf_m=25.0,
            km_m=5.0,
            design_draft_m=2.5,
            design_displacement_mt=200.0,
            lwl_m=50.0,
        )

        # FSC should be zero or very small
        assert result.fsc_m < 0.01


class TestArrangementSerialization:
    """Test arrangement serialization through pipeline."""

    def test_arrangement_roundtrip(self):
        """Test arrangement can be serialized and key data preserved."""
        gen = ArrangementGenerator()
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
        )

        # Serialize
        arr_dict = arr.to_dict()

        # Check key fields preserved
        assert arr_dict["lwl_m"] == 50.0
        assert arr_dict["beam_m"] == 10.0
        assert arr_dict["depth_m"] == 4.0
        assert len(arr_dict["tanks"]) == len(arr.tanks)
        assert len(arr_dict["decks"]) == len(arr.decks)

    def test_tank_geometry_preserved(self):
        """Test v1.1: tank geometry preserved in serialization."""
        gen = ArrangementGenerator()
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
        )

        for tank in arr.tanks:
            tank_dict = tank.to_dict()
            # v1.1 fix: geometry must be present
            assert "length_m" in tank_dict
            assert "breadth_m" in tank_dict
            assert "height_m" in tank_dict
            assert tank_dict["length_m"] > 0
            assert tank_dict["breadth_m"] > 0
            assert tank_dict["height_m"] > 0


class TestDeterministicOutput:
    """Test deterministic output for caching."""

    def test_arrangement_deterministic(self):
        """Test arrangement output is deterministic."""
        import json

        gen = ArrangementGenerator()

        # Generate twice with same inputs
        arr1 = gen.generate(lwl=50.0, beam=10.0, depth=4.0, draft=2.5)
        arr2 = gen.generate(lwl=50.0, beam=10.0, depth=4.0, draft=2.5)

        # Serialize
        dict1 = arr1.to_dict()
        dict2 = arr2.to_dict()

        # Should be identical
        json1 = json.dumps(dict1, sort_keys=True)
        json2 = json.dumps(dict2, sort_keys=True)

        assert json1 == json2

    def test_loading_result_deterministic(self):
        """Test loading result is deterministic."""
        import json

        gen = ArrangementGenerator()
        arr = gen.generate(lwl=50.0, beam=10.0, depth=4.0, draft=2.5)

        calc = LoadingCalculator()

        result1 = calc.calculate_condition(
            condition_name="Test",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            lightship_mt=150.0,
            lightship_lcg_m=25.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=arr.tanks,
            tank_fills={t.tank_id: 1.0 for t in arr.tanks},
            deadweight_items=[],
            depth_m=4.0,
            tpc=5.0,
            mct=200.0,
            lcf_m=25.0,
            km_m=5.0,
            design_draft_m=2.5,
            design_displacement_mt=200.0,
            lwl_m=50.0,
        )

        result2 = calc.calculate_condition(
            condition_name="Test",
            condition_type=LoadingConditionType.FULL_LOAD_DEPARTURE,
            lightship_mt=150.0,
            lightship_lcg_m=25.0,
            lightship_vcg_m=2.0,
            lightship_tcg_m=0.0,
            tanks=arr.tanks,
            tank_fills={t.tank_id: 1.0 for t in arr.tanks},
            deadweight_items=[],
            depth_m=4.0,
            tpc=5.0,
            mct=200.0,
            lcf_m=25.0,
            km_m=5.0,
            design_draft_m=2.5,
            design_displacement_mt=200.0,
            lwl_m=50.0,
        )

        # Key values should match
        assert result1.displacement_mt == result2.displacement_mt
        assert result1.gm_fluid_m == result2.gm_fluid_m
        assert result1.draft_m == result2.draft_m
