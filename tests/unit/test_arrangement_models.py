"""
Unit tests for arrangement models.

Tests Tank, GeneralArrangement, and related data structures.
"""

import pytest
from magnet.arrangement.models import (
    Tank,
    DeckDefinition,
    BulkheadDefinition,
    Compartment,
    GeneralArrangement,
    FluidType,
    SpaceType,
    DeckType,
    BulkheadType,
    FLUID_DENSITIES,
    STANDARD_PERMEABILITIES,
    determinize_dict,
)


class TestFluidType:
    """Tests for FluidType enum."""

    def test_all_fluid_types_exist(self):
        """Test all expected fluid types are defined."""
        assert FluidType.SEAWATER.value == "seawater"
        assert FluidType.FRESHWATER.value == "freshwater"
        assert FluidType.FUEL_MGO.value == "fuel_mgo"
        assert FluidType.FUEL_MDO.value == "fuel_mdo"
        assert FluidType.FUEL_HFO.value == "fuel_hfo"
        assert FluidType.LUBE_OIL.value == "lube_oil"
        assert FluidType.HYDRAULIC_OIL.value == "hydraulic_oil"
        assert FluidType.SEWAGE.value == "sewage"

    def test_fluid_densities_defined(self):
        """Test all fluid types have densities."""
        for fluid_type in FluidType:
            assert fluid_type in FLUID_DENSITIES
            assert FLUID_DENSITIES[fluid_type] > 0

    def test_seawater_denser_than_freshwater(self):
        """Test seawater is denser than freshwater."""
        assert FLUID_DENSITIES[FluidType.SEAWATER] > FLUID_DENSITIES[FluidType.FRESHWATER]


class TestSpaceType:
    """Tests for SpaceType enum."""

    def test_all_space_types_exist(self):
        """Test all expected space types are defined."""
        assert SpaceType.VOID.value == "void"
        assert SpaceType.BALLAST_TANK.value == "ballast_tank"
        assert SpaceType.FUEL_TANK.value == "fuel_tank"
        assert SpaceType.ENGINE_ROOM.value == "engine_room"
        assert SpaceType.ACCOMMODATION.value == "accommodation"

    def test_standard_permeabilities(self):
        """Test standard permeabilities are defined."""
        assert STANDARD_PERMEABILITIES[SpaceType.ENGINE_ROOM] == 0.85
        assert STANDARD_PERMEABILITIES[SpaceType.BALLAST_TANK] == 0.95
        assert STANDARD_PERMEABILITIES[SpaceType.CARGO_HOLD] == 0.70


class TestTank:
    """Tests for Tank dataclass."""

    def test_basic_creation(self):
        """Test basic tank creation."""
        tank = Tank(
            tank_id="TK-01",
            name="Test Tank",
            fluid_type=FluidType.FUEL_MGO,
            length_m=5.0,
            breadth_m=3.0,
            height_m=2.0,
            lcg_m=25.0,
            vcg_m=1.5,
        )
        assert tank.tank_id == "TK-01"
        assert tank.name == "Test Tank"
        assert tank.fluid_type == FluidType.FUEL_MGO
        assert tank.length_m == 5.0
        assert tank.breadth_m == 3.0
        assert tank.height_m == 2.0

    def test_total_capacity(self):
        """Test total capacity calculation."""
        tank = Tank(
            tank_id="TK-01",
            name="Test Tank",
            fluid_type=FluidType.FUEL_MGO,
            length_m=5.0,
            breadth_m=3.0,
            height_m=2.0,
            lcg_m=25.0,
            vcg_m=1.5,
        )
        # Volume = 5 * 3 * 2 = 30 m³
        assert tank.total_capacity_m3 == 30.0

    def test_capacity_override(self):
        """Test capacity can be overridden."""
        tank = Tank(
            tank_id="TK-01",
            name="Test Tank",
            fluid_type=FluidType.FUEL_MGO,
            length_m=5.0,
            breadth_m=3.0,
            height_m=2.0,
            lcg_m=25.0,
            vcg_m=1.5,
            capacity_m3=25.0,  # Override
        )
        assert tank.total_capacity_m3 == 25.0

    def test_fluid_density(self):
        """Test fluid density property."""
        tank = Tank(
            tank_id="TK-01",
            name="Test Tank",
            fluid_type=FluidType.SEAWATER,
            length_m=5.0,
            breadth_m=3.0,
            height_m=2.0,
            lcg_m=25.0,
            vcg_m=1.5,
        )
        assert tank.fluid_density_kg_m3 == 1025.0

    def test_current_volume_empty(self):
        """Test current volume when empty."""
        tank = Tank(
            tank_id="TK-01",
            name="Test Tank",
            fluid_type=FluidType.FUEL_MGO,
            length_m=5.0,
            breadth_m=3.0,
            height_m=2.0,
            lcg_m=25.0,
            vcg_m=1.5,
            fill_percent=0.0,
        )
        assert tank.current_volume_m3 == 0.0

    def test_current_volume_full(self):
        """Test current volume when full."""
        tank = Tank(
            tank_id="TK-01",
            name="Test Tank",
            fluid_type=FluidType.FUEL_MGO,
            length_m=5.0,
            breadth_m=3.0,
            height_m=2.0,
            lcg_m=25.0,
            vcg_m=1.5,
            fill_percent=1.0,
        )
        assert tank.current_volume_m3 == 30.0

    def test_current_volume_partial(self):
        """Test current volume when partially filled."""
        tank = Tank(
            tank_id="TK-01",
            name="Test Tank",
            fluid_type=FluidType.FUEL_MGO,
            length_m=5.0,
            breadth_m=3.0,
            height_m=2.0,
            lcg_m=25.0,
            vcg_m=1.5,
            fill_percent=0.5,
        )
        assert tank.current_volume_m3 == 15.0

    def test_current_weight(self):
        """Test current weight calculation."""
        tank = Tank(
            tank_id="TK-01",
            name="Test Tank",
            fluid_type=FluidType.FUEL_MGO,
            length_m=5.0,
            breadth_m=3.0,
            height_m=2.0,
            lcg_m=25.0,
            vcg_m=1.5,
            fill_percent=1.0,
        )
        # Volume = 30 m³, density = 850 kg/m³
        # Weight = 30 * 850 = 25500 kg = 25.5 MT
        assert tank.current_weight_kg == 30.0 * 850.0
        assert tank.current_weight_mt == 25.5

    def test_has_free_surface_full(self):
        """Test full tank has no free surface."""
        tank = Tank(
            tank_id="TK-01",
            name="Test Tank",
            fluid_type=FluidType.FUEL_MGO,
            length_m=5.0,
            breadth_m=3.0,
            height_m=2.0,
            lcg_m=25.0,
            vcg_m=1.5,
            fill_percent=0.98,
        )
        assert tank.has_free_surface is False

    def test_has_free_surface_empty(self):
        """Test nearly empty tank has no free surface."""
        tank = Tank(
            tank_id="TK-01",
            name="Test Tank",
            fluid_type=FluidType.FUEL_MGO,
            length_m=5.0,
            breadth_m=3.0,
            height_m=2.0,
            lcg_m=25.0,
            vcg_m=1.5,
            fill_percent=0.02,
        )
        assert tank.has_free_surface is False

    def test_has_free_surface_partial(self):
        """Test partially filled tank has free surface."""
        tank = Tank(
            tank_id="TK-01",
            name="Test Tank",
            fluid_type=FluidType.FUEL_MGO,
            length_m=5.0,
            breadth_m=3.0,
            height_m=2.0,
            lcg_m=25.0,
            vcg_m=1.5,
            fill_percent=0.5,
        )
        assert tank.has_free_surface is True

    def test_inertia_calculation(self):
        """Test inertia calculation: i = (1/12) * L * B³"""
        tank = Tank(
            tank_id="TK-01",
            name="Test Tank",
            fluid_type=FluidType.FUEL_MGO,
            length_m=6.0,
            breadth_m=4.0,
            height_m=2.0,
            lcg_m=25.0,
            vcg_m=1.5,
        )
        # i = (1/12) * 6 * 4³ = (1/12) * 6 * 64 = 32 m⁴
        assert tank.inertia_m4 == 32.0

    def test_free_surface_moment(self):
        """Test free surface moment: FSM = ρ * i / 1000"""
        tank = Tank(
            tank_id="TK-01",
            name="Test Tank",
            fluid_type=FluidType.SEAWATER,
            length_m=6.0,
            breadth_m=4.0,
            height_m=2.0,
            lcg_m=25.0,
            vcg_m=1.5,
            fill_percent=0.5,
        )
        # FSM = 1025 * 32 / 1000 = 32.8 t-m
        assert abs(tank.free_surface_moment_t_m - 32.8) < 0.01

    def test_free_surface_moment_full_tank(self):
        """Test free surface moment is zero for full tank."""
        tank = Tank(
            tank_id="TK-01",
            name="Test Tank",
            fluid_type=FluidType.SEAWATER,
            length_m=6.0,
            breadth_m=4.0,
            height_m=2.0,
            lcg_m=25.0,
            vcg_m=1.5,
            fill_percent=0.98,
        )
        assert tank.free_surface_moment_t_m == 0.0

    def test_vcg_at_fill(self):
        """Test VCG at different fill levels."""
        tank = Tank(
            tank_id="TK-01",
            name="Test Tank",
            fluid_type=FluidType.FUEL_MGO,
            length_m=5.0,
            breadth_m=3.0,
            height_m=2.0,
            lcg_m=25.0,
            vcg_m=2.0,  # Tank center at 2.0m
        )
        # Tank bottom at 2.0 - 1.0 = 1.0m
        # Full: VCG at center of fluid = 1.0 + 1.0 = 2.0m
        # Half: VCG at center of fluid = 1.0 + 0.5 = 1.5m
        assert tank.get_vcg_at_fill(1.0) == 2.0
        assert tank.get_vcg_at_fill(0.5) == 1.5

    def test_to_dict_includes_geometry(self):
        """Test v1.1: to_dict includes geometry for reconstruction."""
        tank = Tank(
            tank_id="TK-01",
            name="Test Tank",
            fluid_type=FluidType.FUEL_MGO,
            length_m=5.0,
            breadth_m=3.0,
            height_m=2.0,
            lcg_m=25.0,
            vcg_m=1.5,
            fill_percent=0.5,
        )
        d = tank.to_dict()
        # v1.1 fix: geometry fields must be present
        assert "length_m" in d
        assert "breadth_m" in d
        assert "height_m" in d
        assert d["length_m"] == 5.0
        assert d["breadth_m"] == 3.0
        assert d["height_m"] == 2.0


class TestDeckDefinition:
    """Tests for DeckDefinition dataclass."""

    def test_basic_creation(self):
        """Test basic deck definition creation."""
        deck = DeckDefinition(
            deck_id="DK-01",
            name="Main Deck",
            deck_type=DeckType.MAIN_DECK,
            height_above_baseline_m=4.0,
            fwd_extent_m=0.0,
            aft_extent_m=50.0,
            is_freeboard_deck=True,
        )
        assert deck.deck_id == "DK-01"
        assert deck.name == "Main Deck"
        assert deck.height_above_baseline_m == 4.0

    def test_to_dict(self):
        """Test deck serialization."""
        deck = DeckDefinition(
            deck_id="DK-01",
            name="Main Deck",
            deck_type=DeckType.MAIN_DECK,
            height_above_baseline_m=4.0,
            fwd_extent_m=0.0,
            aft_extent_m=50.0,
        )
        d = deck.to_dict()
        assert d["deck_id"] == "DK-01"
        assert d["deck_type"] == "main_deck"


class TestBulkheadDefinition:
    """Tests for BulkheadDefinition dataclass."""

    def test_basic_creation(self):
        """Test basic bulkhead creation."""
        bhd = BulkheadDefinition(
            bulkhead_id="BHD-01",
            name="Collision Bulkhead",
            bulkhead_type=BulkheadType.COLLISION,
            position_m=2.5,
            is_collision_bulkhead=True,
        )
        assert bhd.bulkhead_id == "BHD-01"
        assert bhd.position_m == 2.5
        assert bhd.is_collision_bulkhead is True


class TestCompartment:
    """Tests for Compartment dataclass."""

    def test_basic_creation(self):
        """Test basic compartment creation."""
        comp = Compartment(
            compartment_id="COMP-01",
            name="Engine Room",
            space_type=SpaceType.ENGINE_ROOM,
            fwd_bulkhead_m=25.0,
            aft_bulkhead_m=40.0,
            bottom_m=0.0,
            top_m=4.0,
            port_m=-4.0,
            starboard_m=4.0,
        )
        assert comp.compartment_id == "COMP-01"
        assert comp.space_type == SpaceType.ENGINE_ROOM

    def test_length_calculation(self):
        """Test compartment length calculation."""
        comp = Compartment(
            compartment_id="COMP-01",
            name="Engine Room",
            space_type=SpaceType.ENGINE_ROOM,
            fwd_bulkhead_m=25.0,
            aft_bulkhead_m=40.0,
            bottom_m=0.0,
            top_m=4.0,
        )
        assert comp.length_m == 15.0

    def test_height_calculation(self):
        """Test compartment height calculation."""
        comp = Compartment(
            compartment_id="COMP-01",
            name="Engine Room",
            space_type=SpaceType.ENGINE_ROOM,
            fwd_bulkhead_m=25.0,
            aft_bulkhead_m=40.0,
            bottom_m=0.0,
            top_m=4.0,
        )
        assert comp.height_m == 4.0

    def test_volume_calculation(self):
        """Test compartment volume calculation."""
        comp = Compartment(
            compartment_id="COMP-01",
            name="Engine Room",
            space_type=SpaceType.ENGINE_ROOM,
            fwd_bulkhead_m=25.0,
            aft_bulkhead_m=40.0,  # Length = 15m
            bottom_m=0.0,
            top_m=4.0,  # Height = 4m
            port_m=-4.0,
            starboard_m=4.0,  # Breadth = 8m
        )
        # Volume = 15 * 8 * 4 = 480 m³
        assert comp.compute_volume() == 480.0

    def test_centroid_calculation(self):
        """Test compartment centroid calculation."""
        comp = Compartment(
            compartment_id="COMP-01",
            name="Test",
            space_type=SpaceType.ENGINE_ROOM,
            fwd_bulkhead_m=20.0,
            aft_bulkhead_m=30.0,
            bottom_m=0.0,
            top_m=4.0,
            port_m=-3.0,
            starboard_m=3.0,
        )
        lcg, vcg, tcg = comp.compute_centroid()
        assert lcg == 25.0  # (20 + 30) / 2
        assert vcg == 2.0   # (0 + 4) / 2
        assert tcg == 0.0   # (-3 + 3) / 2


class TestGeneralArrangement:
    """Tests for GeneralArrangement dataclass."""

    def test_basic_creation(self):
        """Test basic arrangement creation."""
        arr = GeneralArrangement(
            lwl_m=50.0,
            beam_m=10.0,
            depth_m=4.0,
        )
        assert arr.lwl_m == 50.0
        assert arr.beam_m == 10.0
        assert arr.depth_m == 4.0

    def test_get_tank_by_id(self):
        """Test v1.1: get_tank_by_id returns correct tank."""
        tank1 = Tank(
            tank_id="TK-01",
            name="Tank 1",
            fluid_type=FluidType.FUEL_MGO,
            length_m=5.0,
            breadth_m=3.0,
            height_m=2.0,
            lcg_m=25.0,
            vcg_m=1.5,
        )
        tank2 = Tank(
            tank_id="TK-02",
            name="Tank 2",
            fluid_type=FluidType.FRESHWATER,
            length_m=3.0,
            breadth_m=2.0,
            height_m=1.5,
            lcg_m=30.0,
            vcg_m=2.0,
        )
        arr = GeneralArrangement(
            lwl_m=50.0,
            beam_m=10.0,
            depth_m=4.0,
            tanks=[tank1, tank2],
        )

        found = arr.get_tank_by_id("TK-02")
        assert found is not None
        assert found.tank_id == "TK-02"
        assert found.name == "Tank 2"

    def test_get_tank_by_id_not_found(self):
        """Test v1.1: get_tank_by_id returns None if not found."""
        arr = GeneralArrangement(
            lwl_m=50.0,
            beam_m=10.0,
            depth_m=4.0,
            tanks=[],
        )
        assert arr.get_tank_by_id("TK-NONEXISTENT") is None

    def test_get_compartment_by_id(self):
        """Test v1.1: get_compartment_by_id returns correct compartment."""
        comp = Compartment(
            compartment_id="COMP-01",
            name="Engine Room",
            space_type=SpaceType.ENGINE_ROOM,
            fwd_bulkhead_m=25.0,
            aft_bulkhead_m=40.0,
            bottom_m=0.0,
            top_m=4.0,
        )
        arr = GeneralArrangement(
            lwl_m=50.0,
            beam_m=10.0,
            depth_m=4.0,
            compartments=[comp],
        )

        found = arr.get_compartment_by_id("COMP-01")
        assert found is not None
        assert found.name == "Engine Room"

    def test_get_tanks_by_type(self):
        """Test getting tanks by fluid type."""
        tank1 = Tank(
            tank_id="TK-FO-01",
            name="Fuel 1",
            fluid_type=FluidType.FUEL_MGO,
            length_m=5.0,
            breadth_m=3.0,
            height_m=2.0,
            lcg_m=25.0,
            vcg_m=1.5,
        )
        tank2 = Tank(
            tank_id="TK-FO-02",
            name="Fuel 2",
            fluid_type=FluidType.FUEL_MGO,
            length_m=5.0,
            breadth_m=3.0,
            height_m=2.0,
            lcg_m=30.0,
            vcg_m=1.5,
        )
        tank3 = Tank(
            tank_id="TK-FW-01",
            name="Freshwater",
            fluid_type=FluidType.FRESHWATER,
            length_m=3.0,
            breadth_m=2.0,
            height_m=1.5,
            lcg_m=20.0,
            vcg_m=2.0,
        )
        arr = GeneralArrangement(
            lwl_m=50.0,
            beam_m=10.0,
            depth_m=4.0,
            tanks=[tank1, tank2, tank3],
        )

        fuel_tanks = arr.get_tanks_by_type(FluidType.FUEL_MGO)
        assert len(fuel_tanks) == 2

        fw_tanks = arr.get_tanks_by_type(FluidType.FRESHWATER)
        assert len(fw_tanks) == 1

    def test_get_total_capacity(self):
        """Test total capacity by fluid type."""
        tank1 = Tank(
            tank_id="TK-FO-01",
            name="Fuel 1",
            fluid_type=FluidType.FUEL_MGO,
            length_m=5.0,
            breadth_m=3.0,
            height_m=2.0,  # 30 m³
            lcg_m=25.0,
            vcg_m=1.5,
        )
        tank2 = Tank(
            tank_id="TK-FO-02",
            name="Fuel 2",
            fluid_type=FluidType.FUEL_MGO,
            length_m=4.0,
            breadth_m=2.0,
            height_m=2.0,  # 16 m³
            lcg_m=30.0,
            vcg_m=1.5,
        )
        arr = GeneralArrangement(
            lwl_m=50.0,
            beam_m=10.0,
            depth_m=4.0,
            tanks=[tank1, tank2],
        )

        assert arr.get_total_capacity(FluidType.FUEL_MGO) == 46.0

    def test_get_collision_bulkhead(self):
        """Test getting collision bulkhead."""
        bhd1 = BulkheadDefinition(
            bulkhead_id="BHD-01",
            name="Collision",
            bulkhead_type=BulkheadType.COLLISION,
            position_m=2.5,
            is_collision_bulkhead=True,
        )
        bhd2 = BulkheadDefinition(
            bulkhead_id="BHD-02",
            name="ER FWD",
            bulkhead_type=BulkheadType.WATERTIGHT,
            position_m=25.0,
            is_collision_bulkhead=False,
        )
        arr = GeneralArrangement(
            lwl_m=50.0,
            beam_m=10.0,
            depth_m=4.0,
            bulkheads=[bhd1, bhd2],
        )

        collision = arr.get_collision_bulkhead()
        assert collision is not None
        assert collision.bulkhead_id == "BHD-01"

    def test_to_dict_determinized(self):
        """Test arrangement serialization is determinized."""
        arr = GeneralArrangement(
            lwl_m=50.123456789,
            beam_m=10.0,
            depth_m=4.0,
        )
        d = arr.to_dict()
        # Should be rounded
        assert d["lwl_m"] == 50.123457  # 6 decimal places


class TestDeterminizeDict:
    """Tests for determinize_dict utility."""

    def test_sorts_keys(self):
        """Test keys are sorted."""
        data = {"z": 1, "a": 2, "m": 3}
        result = determinize_dict(data)
        keys = list(result.keys())
        assert keys == ["a", "m", "z"]

    def test_rounds_floats(self):
        """Test floats are rounded to precision."""
        data = {"value": 3.141592653589793}
        result = determinize_dict(data, precision=4)
        assert result["value"] == 3.1416

    def test_handles_nested_dicts(self):
        """Test nested dictionaries are processed."""
        data = {
            "outer": {
                "inner": 1.23456789
            }
        }
        result = determinize_dict(data, precision=3)
        assert result["outer"]["inner"] == 1.235

    def test_handles_lists(self):
        """Test lists are processed."""
        data = {
            "items": [1.111111, 2.222222, 3.333333]
        }
        result = determinize_dict(data, precision=2)
        assert result["items"] == [1.11, 2.22, 3.33]

    def test_consistent_output(self):
        """Test output is consistent across runs."""
        import json
        data = {"b": 1.5, "a": 2.5, "c": {"z": 0.1, "y": 0.2}}
        result1 = json.dumps(determinize_dict(data))
        result2 = json.dumps(determinize_dict(data))
        assert result1 == result2
