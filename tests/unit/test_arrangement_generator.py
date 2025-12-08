"""
Unit tests for arrangement generator.

Tests ArrangementGenerator and VesselServiceProfile.
"""

import pytest
from magnet.arrangement.generator import (
    ArrangementGenerator,
    VesselServiceProfile,
)
from magnet.arrangement.models import (
    FluidType,
    SpaceType,
    DeckType,
    BulkheadType,
)


class TestVesselServiceProfile:
    """Tests for VesselServiceProfile."""

    def test_default_profile(self):
        """Test default profile has common services."""
        profile = VesselServiceProfile()
        assert profile.fuel is True
        assert profile.freshwater is True
        assert profile.sewage is True
        assert profile.lube_oil is True
        assert profile.hydraulic_oil is False
        assert profile.ballast is False

    def test_from_dict(self):
        """Test creating profile from dictionary."""
        data = {
            "fuel": True,
            "freshwater": False,
            "sewage": False,
            "lube_oil": True,
            "hydraulic_oil": True,
            "ballast": True,
        }
        profile = VesselServiceProfile.from_dict(data)
        assert profile.fuel is True
        assert profile.freshwater is False
        assert profile.hydraulic_oil is True
        assert profile.ballast is True

    def test_to_dict(self):
        """Test converting profile to dictionary."""
        profile = VesselServiceProfile(
            fuel=True,
            freshwater=False,
            ballast=True,
        )
        d = profile.to_dict()
        assert d["fuel"] is True
        assert d["freshwater"] is False
        assert d["ballast"] is True

    def test_from_vessel_type_rib(self):
        """Test RIB has minimal services."""
        profile = VesselServiceProfile.from_vessel_type("rib")
        assert profile.fuel is True
        assert profile.freshwater is False
        assert profile.sewage is False
        assert profile.lube_oil is False

    def test_from_vessel_type_drone(self):
        """Test drone/unmanned has minimal services."""
        profile = VesselServiceProfile.from_vessel_type("drone")
        assert profile.freshwater is False
        assert profile.sewage is False

    def test_from_vessel_type_military(self):
        """Test military vessels have ballast."""
        profile = VesselServiceProfile.from_vessel_type("military")
        assert profile.ballast is True

    def test_from_vessel_type_naval(self):
        """Test naval vessels have ballast."""
        profile = VesselServiceProfile.from_vessel_type("naval")
        assert profile.ballast is True

    def test_short_endurance_no_freshwater(self):
        """Test short endurance (<1 day) has no freshwater."""
        profile = VesselServiceProfile.from_vessel_type("patrol", endurance_days=0.5)
        assert profile.freshwater is False
        assert profile.sewage is False

    def test_medium_endurance_no_sewage(self):
        """Test medium endurance (<2 days) has no sewage."""
        profile = VesselServiceProfile.from_vessel_type("patrol", endurance_days=1.5)
        assert profile.freshwater is True
        assert profile.sewage is False

    def test_long_endurance_full_services(self):
        """Test long endurance has all services."""
        profile = VesselServiceProfile.from_vessel_type("patrol", endurance_days=5.0)
        assert profile.freshwater is True
        assert profile.sewage is True


class TestArrangementGenerator:
    """Tests for ArrangementGenerator."""

    def test_generate_basic(self):
        """Test basic arrangement generation."""
        gen = ArrangementGenerator()
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
        )
        assert arr.lwl_m == 50.0
        assert arr.beam_m == 10.0
        assert arr.depth_m == 4.0

    def test_generate_creates_decks(self):
        """Test generator creates decks."""
        gen = ArrangementGenerator()
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
        )
        assert len(arr.decks) > 0
        # Should have at least main deck and tank top
        assert any(d.deck_type == DeckType.MAIN_DECK for d in arr.decks)
        assert any(d.deck_type == DeckType.TANK_TOP for d in arr.decks)

    def test_generate_creates_bulkheads(self):
        """Test generator creates bulkheads."""
        gen = ArrangementGenerator()
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
        )
        assert len(arr.bulkheads) > 0
        # Should have collision bulkhead
        collision = arr.get_collision_bulkhead()
        assert collision is not None

    def test_generate_creates_compartments(self):
        """Test generator creates compartments."""
        gen = ArrangementGenerator()
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
        )
        assert len(arr.compartments) > 0
        # Should have engine room
        engine_rooms = [c for c in arr.compartments if c.space_type == SpaceType.ENGINE_ROOM]
        assert len(engine_rooms) > 0

    def test_generate_creates_tanks(self):
        """Test generator creates tanks."""
        gen = ArrangementGenerator()
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
        )
        assert len(arr.tanks) > 0

    def test_generate_fuel_tanks(self):
        """Test generator creates fuel tanks."""
        gen = ArrangementGenerator()
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
        )
        fuel_tanks = arr.get_tanks_by_type(FluidType.FUEL_MGO)
        assert len(fuel_tanks) > 0

    def test_generate_freshwater_tank(self):
        """Test generator creates freshwater tank with services."""
        gen = ArrangementGenerator()
        services = VesselServiceProfile(freshwater=True)
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
            services=services,
        )
        fw_tanks = arr.get_tanks_by_type(FluidType.FRESHWATER)
        assert len(fw_tanks) > 0

    def test_generate_no_freshwater_tank(self):
        """Test v1.1: service profile controls freshwater tank."""
        gen = ArrangementGenerator()
        services = VesselServiceProfile(freshwater=False)
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
            services=services,
        )
        fw_tanks = arr.get_tanks_by_type(FluidType.FRESHWATER)
        assert len(fw_tanks) == 0

    def test_generate_ballast_for_military(self):
        """Test v1.1: military vessels get ballast tanks."""
        gen = ArrangementGenerator()
        services = VesselServiceProfile(ballast=True)
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
            services=services,
        )
        ballast_tanks = arr.get_tanks_by_type(FluidType.SEAWATER)
        assert len(ballast_tanks) > 0

    def test_generate_no_ballast_by_default(self):
        """Test default services have no ballast tanks."""
        gen = ArrangementGenerator()
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
        )
        ballast_tanks = arr.get_tanks_by_type(FluidType.SEAWATER)
        assert len(ballast_tanks) == 0

    def test_collision_bulkhead_position(self):
        """Test collision bulkhead is near bow."""
        gen = ArrangementGenerator()
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
        )
        collision = arr.get_collision_bulkhead()
        assert collision is not None
        # Should be at least 5% of LWL or 2m from bow
        assert collision.position_m >= 2.0
        assert collision.position_m <= 50.0 * 0.15  # Not too far aft

    def test_wheelhouse_deck_for_large_vessel(self):
        """Test large vessels get wheelhouse deck."""
        gen = ArrangementGenerator()
        arr = gen.generate(
            lwl=50.0,  # > 15m
            beam=10.0,
            depth=4.0,
            draft=2.5,
        )
        # Should have wheelhouse/superstructure deck
        superstructure = [d for d in arr.decks if d.deck_type == DeckType.SUPERSTRUCTURE]
        assert len(superstructure) > 0

    def test_no_wheelhouse_for_small_vessel(self):
        """Test small vessels don't get wheelhouse deck."""
        gen = ArrangementGenerator()
        arr = gen.generate(
            lwl=10.0,  # <= 15m
            beam=3.0,
            depth=1.5,
            draft=0.8,
        )
        superstructure = [d for d in arr.decks if d.deck_type == DeckType.SUPERSTRUCTURE]
        assert len(superstructure) == 0

    def test_tank_positions_reasonable(self):
        """Test tank positions are within vessel bounds."""
        gen = ArrangementGenerator()
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
        )
        for tank in arr.tanks:
            # LCG should be within LWL
            assert 0 <= tank.lcg_m <= 50.0
            # VCG should be below depth
            assert tank.vcg_m <= 4.0
            # TCG should be within beam
            assert abs(tank.tcg_m) <= 5.0

    def test_service_profile_from_vessel_type(self):
        """Test service profile derived from vessel type."""
        gen = ArrangementGenerator()
        # RIB should have minimal tanks
        arr = gen.generate(
            lwl=8.0,
            beam=2.5,
            depth=1.0,
            draft=0.4,
            vessel_type="rib",
        )
        # Should only have fuel tanks (no freshwater, sewage, lube)
        fw_tanks = arr.get_tanks_by_type(FluidType.FRESHWATER)
        assert len(fw_tanks) == 0

    def test_generate_sewage_tank(self):
        """Test sewage tank generation with services."""
        gen = ArrangementGenerator()
        services = VesselServiceProfile(sewage=True)
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
            services=services,
        )
        sewage_tanks = arr.get_tanks_by_type(FluidType.SEWAGE)
        assert len(sewage_tanks) > 0

    def test_generate_lube_oil_tank(self):
        """Test lube oil tank generation."""
        gen = ArrangementGenerator()
        services = VesselServiceProfile(lube_oil=True)
        arr = gen.generate(
            lwl=50.0,
            beam=10.0,
            depth=4.0,
            draft=2.5,
            services=services,
        )
        lube_tanks = arr.get_tanks_by_type(FluidType.LUBE_OIL)
        assert len(lube_tanks) > 0
