"""
MAGNET Arrangement Module Tests

Tests for Module 08: General Arrangement Framework (v1.1)
"""

import pytest
from datetime import datetime, timezone

from magnet.arrangement.models import (
    FluidType, SpaceType, DeckType, BulkheadType,
    FLUID_DENSITIES, STANDARD_PERMEABILITIES,
    Tank, DeckDefinition, BulkheadDefinition, Compartment,
    GeneralArrangement, determinize_dict
)
from magnet.arrangement.generator import (
    VesselServiceProfile, ArrangementGenerator
)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def sample_tank():
    """Sample fuel tank for testing."""
    return Tank(
        tank_id="TK-FO-01P",
        name="Fuel Oil Tank #1 Port",
        fluid_type=FluidType.FUEL_MGO,
        length_m=5.0,
        breadth_m=2.0,
        height_m=1.0,
        lcg_m=15.0,
        vcg_m=0.5,
        tcg_m=-1.5,
        fill_percent=0.8,
    )


@pytest.fixture
def sample_compartment():
    """Sample compartment for testing."""
    return Compartment(
        compartment_id="COMP-01",
        name="Engine Room",
        space_type=SpaceType.ENGINE_ROOM,
        fwd_bulkhead_m=15.0,
        aft_bulkhead_m=25.0,
        bottom_m=0.0,
        top_m=4.0,
        port_m=-3.5,
        starboard_m=3.5,
        permeability=0.85,
    )


@pytest.fixture
def sample_hull_params():
    """Standard hull parameters for testing."""
    return {
        "lwl": 30.0,
        "beam": 8.0,
        "depth": 4.0,
        "draft": 2.0,
    }


# =============================================================================
# FLUID TYPE TESTS
# =============================================================================

class TestFluidType:
    """Tests for FluidType enumeration."""

    def test_fluid_types_defined(self):
        """All fluid types should be defined."""
        assert FluidType.SEAWATER.value == "seawater"
        assert FluidType.FRESHWATER.value == "freshwater"
        assert FluidType.FUEL_MGO.value == "fuel_mgo"
        assert FluidType.FUEL_MDO.value == "fuel_mdo"
        assert FluidType.FUEL_HFO.value == "fuel_hfo"
        assert FluidType.LUBE_OIL.value == "lube_oil"
        assert FluidType.HYDRAULIC_OIL.value == "hydraulic_oil"
        assert FluidType.SEWAGE.value == "sewage"

    def test_fluid_densities_complete(self):
        """All fluid types should have densities defined."""
        for fluid_type in FluidType:
            assert fluid_type in FLUID_DENSITIES
            assert FLUID_DENSITIES[fluid_type] > 0

    def test_seawater_density(self):
        """Seawater density should be 1025 kg/m³."""
        assert FLUID_DENSITIES[FluidType.SEAWATER] == 1025.0

    def test_freshwater_density(self):
        """Freshwater density should be 1000 kg/m³."""
        assert FLUID_DENSITIES[FluidType.FRESHWATER] == 1000.0

    def test_mgo_density(self):
        """MGO density should be ~850 kg/m³."""
        assert 800 < FLUID_DENSITIES[FluidType.FUEL_MGO] < 900


# =============================================================================
# SPACE TYPE TESTS
# =============================================================================

class TestSpaceType:
    """Tests for SpaceType enumeration."""

    def test_space_types_defined(self):
        """All space types should be defined."""
        assert SpaceType.VOID.value == "void"
        assert SpaceType.ENGINE_ROOM.value == "engine_room"
        assert SpaceType.CHAIN_LOCKER.value == "chain_locker"

    def test_permeabilities_complete(self):
        """All space types should have permeabilities defined."""
        for space_type in STANDARD_PERMEABILITIES:
            perm = STANDARD_PERMEABILITIES[space_type]
            assert 0.0 <= perm <= 1.0

    def test_engine_room_permeability(self):
        """Engine room permeability should be ~0.85."""
        assert STANDARD_PERMEABILITIES[SpaceType.ENGINE_ROOM] == 0.85


# =============================================================================
# TANK TESTS
# =============================================================================

class TestTank:
    """Tests for Tank dataclass."""

    def test_tank_creation(self, sample_tank):
        """Tank should be created with correct attributes."""
        assert sample_tank.tank_id == "TK-FO-01P"
        assert sample_tank.fluid_type == FluidType.FUEL_MGO
        assert sample_tank.length_m == 5.0
        assert sample_tank.breadth_m == 2.0
        assert sample_tank.height_m == 1.0

    def test_fluid_density(self, sample_tank):
        """Fluid density should match fluid type."""
        assert sample_tank.fluid_density_kg_m3 == FLUID_DENSITIES[FluidType.FUEL_MGO]

    def test_total_capacity(self, sample_tank):
        """Total capacity should be L*B*H."""
        expected = 5.0 * 2.0 * 1.0  # 10 m³
        assert sample_tank.total_capacity_m3 == expected

    def test_total_capacity_override(self):
        """Custom capacity should override geometry calculation."""
        tank = Tank(
            tank_id="TK-01",
            name="Test Tank",
            fluid_type=FluidType.FRESHWATER,
            length_m=2.0,
            breadth_m=1.5,
            height_m=1.0,
            lcg_m=10.0,
            vcg_m=0.5,
            capacity_m3=5.0,  # Override
        )
        assert tank.total_capacity_m3 == 5.0

    def test_current_volume(self, sample_tank):
        """Current volume should be capacity * fill percent."""
        expected = 10.0 * 0.8  # 8 m³
        assert sample_tank.current_volume_m3 == expected

    def test_current_weight_mt(self, sample_tank):
        """Current weight should be volume * density / 1000."""
        density = FLUID_DENSITIES[FluidType.FUEL_MGO]
        expected = (10.0 * 0.8 * density) / 1000.0
        assert abs(sample_tank.current_weight_mt - expected) < 0.001

    def test_current_weight_kg(self, sample_tank):
        """Current weight in kg should be volume * density."""
        density = FLUID_DENSITIES[FluidType.FUEL_MGO]
        expected = 10.0 * 0.8 * density
        assert abs(sample_tank.current_weight_kg - expected) < 0.001

    def test_inertia_calculation(self, sample_tank):
        """Inertia should be (1/12) * L * B³."""
        expected = (1.0 / 12.0) * 5.0 * (2.0 ** 3)
        assert abs(sample_tank.inertia_m4 - expected) < 0.001

    def test_has_free_surface_partial(self, sample_tank):
        """Partial fill should have free surface."""
        sample_tank.fill_percent = 0.5
        assert sample_tank.has_free_surface is True

    def test_has_free_surface_full(self, sample_tank):
        """Full tank should not have free surface."""
        sample_tank.fill_percent = 1.0
        assert sample_tank.has_free_surface is False

    def test_has_free_surface_empty(self, sample_tank):
        """Empty tank should not have free surface."""
        sample_tank.fill_percent = 0.0
        assert sample_tank.has_free_surface is False

    def test_free_surface_moment_partial(self, sample_tank):
        """Partial fill should have FSM."""
        sample_tank.fill_percent = 0.5
        fsm = sample_tank.free_surface_moment_t_m
        assert fsm > 0

    def test_free_surface_moment_full(self, sample_tank):
        """Full tank should have zero FSM."""
        sample_tank.fill_percent = 1.0
        assert sample_tank.free_surface_moment_t_m == 0.0

    def test_vcg_at_fill(self, sample_tank):
        """VCG should vary with fill level."""
        vcg_empty = sample_tank.get_vcg_at_fill(0.0)
        vcg_full = sample_tank.get_vcg_at_fill(1.0)
        vcg_half = sample_tank.get_vcg_at_fill(0.5)

        # VCG should increase with fill
        assert vcg_empty < vcg_half < vcg_full

    def test_to_dict_includes_geometry(self, sample_tank):
        """FIX v1.1 CI#3: to_dict should include geometry for reconstruction."""
        data = sample_tank.to_dict()

        # Required geometry fields
        assert "length_m" in data
        assert "breadth_m" in data
        assert "height_m" in data

        # Values should match
        assert data["length_m"] == 5.0
        assert data["breadth_m"] == 2.0
        assert data["height_m"] == 1.0

    def test_to_dict_complete(self, sample_tank):
        """to_dict should include all required fields."""
        data = sample_tank.to_dict()

        required_fields = [
            "tank_id", "name", "fluid_type",
            "length_m", "breadth_m", "height_m",
            "lcg_m", "vcg_m", "tcg_m",
            "capacity_m3", "current_fill_percent", "current_weight_mt",
            "has_free_surface", "fsm_t_m"
        ]

        for field in required_fields:
            assert field in data


# =============================================================================
# COMPARTMENT TESTS
# =============================================================================

class TestCompartment:
    """Tests for Compartment dataclass."""

    def test_compartment_creation(self, sample_compartment):
        """Compartment should be created with correct attributes."""
        assert sample_compartment.compartment_id == "COMP-01"
        assert sample_compartment.space_type == SpaceType.ENGINE_ROOM
        assert sample_compartment.permeability == 0.85

    def test_length_calculation(self, sample_compartment):
        """Length should be |fwd - aft|."""
        assert sample_compartment.length_m == 10.0

    def test_height_calculation(self, sample_compartment):
        """Height should be top - bottom."""
        assert sample_compartment.height_m == 4.0

    def test_breadth_calculation(self, sample_compartment):
        """Breadth should be |stbd - port|."""
        assert sample_compartment.breadth_m == 7.0

    def test_volume_calculation(self, sample_compartment):
        """Volume should be L*B*H."""
        expected = 10.0 * 7.0 * 4.0  # 280 m³
        assert sample_compartment.compute_volume() == expected

    def test_centroid_calculation(self, sample_compartment):
        """Centroid should be midpoint of boundaries."""
        lcg, vcg, tcg = sample_compartment.compute_centroid()

        assert lcg == (15.0 + 25.0) / 2  # 20.0
        assert vcg == (0.0 + 4.0) / 2     # 2.0
        assert tcg == (-3.5 + 3.5) / 2    # 0.0

    def test_to_dict(self, sample_compartment):
        """to_dict should serialize correctly."""
        data = sample_compartment.to_dict()

        assert data["compartment_id"] == "COMP-01"
        assert data["space_type"] == "engine_room"
        assert data["permeability"] == 0.85


# =============================================================================
# GENERAL ARRANGEMENT TESTS
# =============================================================================

class TestGeneralArrangement:
    """Tests for GeneralArrangement dataclass."""

    def test_empty_arrangement(self):
        """Empty arrangement should have no components."""
        arr = GeneralArrangement(lwl_m=30.0, beam_m=8.0, depth_m=4.0)

        assert len(arr.tanks) == 0
        assert len(arr.compartments) == 0
        assert len(arr.bulkheads) == 0
        assert len(arr.decks) == 0

    def test_get_tank_by_id_found(self, sample_tank):
        """FIX v1.1 CI#5: Should find tank by ID."""
        arr = GeneralArrangement(lwl_m=30.0, beam_m=8.0, depth_m=4.0)
        arr.tanks.append(sample_tank)

        found = arr.get_tank_by_id("TK-FO-01P")
        assert found is not None
        assert found.tank_id == "TK-FO-01P"

    def test_get_tank_by_id_not_found(self, sample_tank):
        """Should return None for non-existent tank."""
        arr = GeneralArrangement(lwl_m=30.0, beam_m=8.0, depth_m=4.0)
        arr.tanks.append(sample_tank)

        found = arr.get_tank_by_id("TK-NONEXISTENT")
        assert found is None

    def test_get_compartment_by_id_found(self, sample_compartment):
        """FIX v1.1 CI#5: Should find compartment by ID."""
        arr = GeneralArrangement(lwl_m=30.0, beam_m=8.0, depth_m=4.0)
        arr.compartments.append(sample_compartment)

        found = arr.get_compartment_by_id("COMP-01")
        assert found is not None
        assert found.compartment_id == "COMP-01"

    def test_get_tanks_by_type(self):
        """Should filter tanks by fluid type."""
        arr = GeneralArrangement(lwl_m=30.0, beam_m=8.0, depth_m=4.0)

        fuel_tank = Tank(
            tank_id="TK-FO", name="Fuel", fluid_type=FluidType.FUEL_MGO,
            length_m=2.0, breadth_m=1.0, height_m=1.0, lcg_m=15.0, vcg_m=0.5
        )
        fw_tank = Tank(
            tank_id="TK-FW", name="Freshwater", fluid_type=FluidType.FRESHWATER,
            length_m=2.0, breadth_m=1.0, height_m=1.0, lcg_m=10.0, vcg_m=0.5
        )
        arr.tanks.extend([fuel_tank, fw_tank])

        fuel_tanks = arr.get_tanks_by_type(FluidType.FUEL_MGO)
        assert len(fuel_tanks) == 1
        assert fuel_tanks[0].tank_id == "TK-FO"

    def test_get_total_capacity(self):
        """Should sum capacity by fluid type."""
        arr = GeneralArrangement(lwl_m=30.0, beam_m=8.0, depth_m=4.0)

        tank1 = Tank(
            tank_id="TK-FO-1", name="Fuel 1", fluid_type=FluidType.FUEL_MGO,
            length_m=2.0, breadth_m=2.0, height_m=1.0, lcg_m=15.0, vcg_m=0.5
        )
        tank2 = Tank(
            tank_id="TK-FO-2", name="Fuel 2", fluid_type=FluidType.FUEL_MGO,
            length_m=3.0, breadth_m=2.0, height_m=1.0, lcg_m=20.0, vcg_m=0.5
        )
        arr.tanks.extend([tank1, tank2])

        total = arr.get_total_capacity(FluidType.FUEL_MGO)
        assert total == (2.0 * 2.0 * 1.0) + (3.0 * 2.0 * 1.0)  # 10 m³

    def test_get_collision_bulkhead(self):
        """Should find collision bulkhead."""
        arr = GeneralArrangement(lwl_m=30.0, beam_m=8.0, depth_m=4.0)

        normal_bhd = BulkheadDefinition(
            bulkhead_id="BHD-01", name="Normal",
            bulkhead_type=BulkheadType.WATERTIGHT, position_m=10.0,
            is_collision_bulkhead=False
        )
        collision_bhd = BulkheadDefinition(
            bulkhead_id="BHD-02", name="Collision",
            bulkhead_type=BulkheadType.COLLISION, position_m=2.0,
            is_collision_bulkhead=True
        )
        arr.bulkheads.extend([normal_bhd, collision_bhd])

        found = arr.get_collision_bulkhead()
        assert found is not None
        assert found.is_collision_bulkhead is True
        assert found.position_m == 2.0

    def test_to_dict_determinized(self):
        """to_dict should be determinized for hashing."""
        arr = GeneralArrangement(lwl_m=30.0, beam_m=8.0, depth_m=4.0)
        data = arr.to_dict()

        # Should be valid JSON (determinization uses JSON)
        import json
        json_str = json.dumps(data, sort_keys=True)
        assert len(json_str) > 0


# =============================================================================
# DETERMINIZE DICT TESTS
# =============================================================================

class TestDeterminizeDict:
    """Tests for determinize_dict utility."""

    def test_float_rounding(self):
        """Should round floats to consistent precision."""
        data = {"value": 1.23456789}
        result = determinize_dict(data, precision=3)
        assert result["value"] == 1.235

    def test_key_sorting(self):
        """Should sort keys alphabetically."""
        data = {"z": 1, "a": 2, "m": 3}
        result = determinize_dict(data)

        keys = list(result.keys())
        assert keys == sorted(keys)

    def test_nested_dict(self):
        """Should handle nested dicts."""
        data = {"outer": {"z": 1, "a": 2}}
        result = determinize_dict(data)

        inner_keys = list(result["outer"].keys())
        assert inner_keys == sorted(inner_keys)

    def test_list_processing(self):
        """Should process lists recursively."""
        data = {"items": [{"b": 2, "a": 1}, {"d": 4, "c": 3}]}
        result = determinize_dict(data)

        for item in result["items"]:
            assert list(item.keys()) == sorted(item.keys())

    def test_enum_conversion(self):
        """Should convert enums to values."""
        data = {"type": FluidType.FUEL_MGO}
        result = determinize_dict(data)
        assert result["type"] == "fuel_mgo"

    def test_deterministic_output(self):
        """Same input should produce identical output."""
        data = {"b": 2.123456, "a": 1.654321}

        result1 = determinize_dict(data)
        result2 = determinize_dict(data)

        import json
        assert json.dumps(result1, sort_keys=True) == json.dumps(result2, sort_keys=True)


# =============================================================================
# SERVICE PROFILE TESTS
# =============================================================================

class TestVesselServiceProfile:
    """Tests for VesselServiceProfile."""

    def test_default_profile(self):
        """Default profile should have standard services."""
        profile = VesselServiceProfile()

        assert profile.fuel is True
        assert profile.freshwater is True
        assert profile.sewage is True
        assert profile.lube_oil is True
        assert profile.hydraulic_oil is False
        assert profile.ballast is False

    def test_from_dict(self):
        """Should create profile from dictionary."""
        data = {"fuel": True, "sewage": False, "ballast": True}
        profile = VesselServiceProfile.from_dict(data)

        assert profile.fuel is True
        assert profile.sewage is False
        assert profile.ballast is True
        assert profile.freshwater is True  # Default

    def test_from_vessel_type_rib(self):
        """RIB should have minimal services."""
        profile = VesselServiceProfile.from_vessel_type("rib", endurance_days=0.5)

        assert profile.fuel is True
        assert profile.freshwater is False
        assert profile.sewage is False
        assert profile.lube_oil is False

    def test_from_vessel_type_military(self):
        """Military vessels should have ballast."""
        profile = VesselServiceProfile.from_vessel_type("military", endurance_days=5.0)

        assert profile.ballast is True

    def test_from_vessel_type_short_endurance(self):
        """Short endurance should reduce services."""
        profile = VesselServiceProfile.from_vessel_type("patrol", endurance_days=0.5)

        assert profile.freshwater is False
        assert profile.sewage is False

    def test_to_dict(self):
        """Should convert to dictionary."""
        profile = VesselServiceProfile(fuel=True, ballast=True)
        data = profile.to_dict()

        assert data["fuel"] is True
        assert data["ballast"] is True


# =============================================================================
# ARRANGEMENT GENERATOR TESTS
# =============================================================================

class TestArrangementGenerator:
    """Tests for ArrangementGenerator."""

    def test_generate_basic(self, sample_hull_params):
        """Should generate complete arrangement."""
        gen = ArrangementGenerator()
        arr = gen.generate(
            lwl=sample_hull_params["lwl"],
            beam=sample_hull_params["beam"],
            depth=sample_hull_params["depth"],
            draft=sample_hull_params["draft"],
        )

        assert arr.lwl_m == 30.0
        assert arr.beam_m == 8.0
        assert arr.depth_m == 4.0
        assert len(arr.decks) > 0
        assert len(arr.bulkheads) > 0
        assert len(arr.compartments) > 0
        assert len(arr.tanks) > 0

    def test_generate_decks(self, sample_hull_params):
        """Should generate main deck and tank top."""
        gen = ArrangementGenerator()
        arr = gen.generate(**sample_hull_params)

        deck_types = [d.deck_type for d in arr.decks]
        assert DeckType.MAIN_DECK in deck_types
        assert DeckType.TANK_TOP in deck_types

    def test_generate_collision_bulkhead(self, sample_hull_params):
        """Should generate collision bulkhead."""
        gen = ArrangementGenerator()
        arr = gen.generate(**sample_hull_params)

        collision = arr.get_collision_bulkhead()
        assert collision is not None
        assert collision.is_collision_bulkhead is True
        assert 0 < collision.position_m < sample_hull_params["lwl"] * 0.15

    def test_generate_engine_room(self, sample_hull_params):
        """Should generate engine room compartment."""
        gen = ArrangementGenerator()
        arr = gen.generate(**sample_hull_params)

        er = None
        for comp in arr.compartments:
            if comp.space_type == SpaceType.ENGINE_ROOM:
                er = comp
                break

        assert er is not None

    def test_generate_fuel_tanks(self, sample_hull_params):
        """Should generate fuel tanks."""
        gen = ArrangementGenerator()
        arr = gen.generate(**sample_hull_params, range_nm=500)

        fuel_tanks = arr.get_tanks_by_type(FluidType.FUEL_MGO)
        assert len(fuel_tanks) >= 2  # Port and starboard

    def test_generate_with_service_profile(self, sample_hull_params):
        """Should respect service profile."""
        gen = ArrangementGenerator()

        # No sewage service
        services = VesselServiceProfile(sewage=False)
        arr = gen.generate(**sample_hull_params, services=services)

        sewage_tanks = arr.get_tanks_by_type(FluidType.SEWAGE)
        assert len(sewage_tanks) == 0

    def test_generate_with_ballast(self, sample_hull_params):
        """Should generate ballast tanks if enabled."""
        gen = ArrangementGenerator()

        services = VesselServiceProfile(ballast=True)
        arr = gen.generate(**sample_hull_params, services=services)

        ballast_tanks = arr.get_tanks_by_type(FluidType.SEAWATER)
        assert len(ballast_tanks) >= 2  # Fwd and aft

    def test_generate_no_ballast_by_default(self, sample_hull_params):
        """Should not generate ballast by default."""
        gen = ArrangementGenerator()
        arr = gen.generate(**sample_hull_params)

        ballast_tanks = arr.get_tanks_by_type(FluidType.SEAWATER)
        assert len(ballast_tanks) == 0

    def test_wheelhouse_deck_large_vessel(self):
        """Large vessels should have wheelhouse deck."""
        gen = ArrangementGenerator()
        arr = gen.generate(lwl=35.0, beam=9.0, depth=4.5, draft=2.5)

        deck_types = [d.deck_type for d in arr.decks]
        assert DeckType.SUPERSTRUCTURE in deck_types

    def test_no_wheelhouse_small_vessel(self):
        """Small vessels should not have wheelhouse deck."""
        gen = ArrangementGenerator()
        arr = gen.generate(lwl=10.0, beam=3.0, depth=1.5, draft=0.8)

        deck_types = [d.deck_type for d in arr.decks]
        assert DeckType.SUPERSTRUCTURE not in deck_types


# =============================================================================
# DECK DEFINITION TESTS
# =============================================================================

class TestDeckDefinition:
    """Tests for DeckDefinition."""

    def test_deck_creation(self):
        """Deck should be created correctly."""
        deck = DeckDefinition(
            deck_id="DK-01",
            name="Main Deck",
            deck_type=DeckType.MAIN_DECK,
            height_above_baseline_m=4.0,
            fwd_extent_m=0.0,
            aft_extent_m=30.0,
            is_freeboard_deck=True,
        )

        assert deck.deck_id == "DK-01"
        assert deck.is_freeboard_deck is True

    def test_to_dict(self):
        """to_dict should serialize correctly."""
        deck = DeckDefinition(
            deck_id="DK-01",
            name="Main Deck",
            deck_type=DeckType.MAIN_DECK,
            height_above_baseline_m=4.0,
            fwd_extent_m=0.0,
            aft_extent_m=30.0,
        )
        data = deck.to_dict()

        assert data["deck_type"] == "main_deck"
        assert data["height_m"] == 4.0


# =============================================================================
# BULKHEAD DEFINITION TESTS
# =============================================================================

class TestBulkheadDefinition:
    """Tests for BulkheadDefinition."""

    def test_bulkhead_creation(self):
        """Bulkhead should be created correctly."""
        bhd = BulkheadDefinition(
            bulkhead_id="BHD-01",
            name="Collision Bulkhead",
            bulkhead_type=BulkheadType.COLLISION,
            position_m=2.0,
            is_collision_bulkhead=True,
        )

        assert bhd.bulkhead_id == "BHD-01"
        assert bhd.is_collision_bulkhead is True

    def test_to_dict(self):
        """to_dict should serialize correctly."""
        bhd = BulkheadDefinition(
            bulkhead_id="BHD-01",
            name="Collision Bulkhead",
            bulkhead_type=BulkheadType.COLLISION,
            position_m=2.0,
            is_watertight=True,
        )
        data = bhd.to_dict()

        assert data["type"] == "collision"
        assert data["is_watertight"] is True
