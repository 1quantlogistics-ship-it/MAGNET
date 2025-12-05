"""
Tests for geometry module.

Tests coordinate system, frame numbering, zone definitions,
and structural member placement.
"""

import pytest
from geometry.reference import (
    CoordinateSystem,
    Station,
    ReferencePoint,
    get_stations,
    get_station_at_x,
    get_reference_point_x,
)
from geometry.frames import (
    Frame,
    FrameType,
    FrameSystem,
    calculate_frame_spacing,
    get_frame_locations,
    get_frame_at_x,
    get_frames_in_zone,
    generate_frame_system,
    get_standard_bulkhead_positions,
)
from geometry.zones import (
    StructuralZone,
    ZoneType,
    LongitudinalZone,
    VerticalZone,
    PressureZone,
    get_zone_for_position,
    get_zone_boundaries,
    get_all_zones,
    get_zones_by_type,
    get_slamming_zones,
    get_immersed_zones,
    get_longitudinal_zone,
    get_vertical_zone,
)
from geometry.members import (
    StructuralMember,
    MemberType,
    MemberOrientation,
    StructuralLayout,
    get_stiffener_positions,
    get_frame_members,
    get_girder_positions,
    generate_structural_layout,
    summarize_layout,
)


# M48 baseline vessel parameters
M48_LENGTH_BP = 45.0   # m
M48_BEAM = 12.8        # m
M48_DEPTH = 4.5        # m
M48_DRAFT = 1.8        # m
M48_SPEED = 28.0       # knots
M48_FRAME_SPACING = 600.0   # mm
M48_STIFFENER_SPACING = 300.0  # mm


class TestCoordinateSystem:
    """Tests for coordinate system and reference points."""

    def test_coordinate_system_creation(self):
        """Test CoordinateSystem creation."""
        cs = CoordinateSystem(
            length_bp=M48_LENGTH_BP,
            beam=M48_BEAM,
            depth=M48_DEPTH,
            draft=M48_DRAFT,
        )

        assert cs.length_bp == M48_LENGTH_BP
        assert cs.beam == M48_BEAM
        assert cs.depth == M48_DEPTH
        assert cs.draft == M48_DRAFT

    def test_reference_points(self):
        """Test reference point calculations."""
        cs = CoordinateSystem(
            length_bp=M48_LENGTH_BP,
            beam=M48_BEAM,
            depth=M48_DEPTH,
            draft=M48_DRAFT,
        )

        assert cs.x_ap == 0.0
        assert cs.x_fp == M48_LENGTH_BP
        assert cs.x_midship == M48_LENGTH_BP / 2
        assert cs.y_centerline == 0.0
        assert cs.y_port == M48_BEAM / 2
        assert cs.y_starboard == -M48_BEAM / 2
        assert cs.z_baseline == 0.0
        assert cs.z_waterline == M48_DRAFT
        assert cs.z_deck == M48_DEPTH

    def test_normalize_x(self):
        """Test x coordinate normalization."""
        cs = CoordinateSystem(
            length_bp=M48_LENGTH_BP,
            beam=M48_BEAM,
            depth=M48_DEPTH,
            draft=M48_DRAFT,
        )

        assert cs.normalize_x(0.0) == 0.0
        assert cs.normalize_x(M48_LENGTH_BP) == 1.0
        assert cs.normalize_x(M48_LENGTH_BP / 2) == 0.5

    def test_position_checks(self):
        """Test forward/midship/aft position checks."""
        cs = CoordinateSystem(
            length_bp=M48_LENGTH_BP,
            beam=M48_BEAM,
            depth=M48_DEPTH,
            draft=M48_DRAFT,
        )

        # Forward region (>0.67 LBP)
        assert cs.is_forward(M48_LENGTH_BP * 0.8)
        assert not cs.is_forward(M48_LENGTH_BP * 0.5)

        # Midship region (0.33-0.67 LBP)
        assert cs.is_midship(M48_LENGTH_BP * 0.5)
        assert not cs.is_midship(M48_LENGTH_BP * 0.1)

        # Aft region (<0.33 LBP)
        assert cs.is_aft(M48_LENGTH_BP * 0.2)
        assert not cs.is_aft(M48_LENGTH_BP * 0.8)


class TestStations:
    """Tests for station generation."""

    def test_generate_10_stations(self):
        """Test generating 10 station intervals."""
        stations = get_stations(M48_LENGTH_BP, num_stations=10)

        assert len(stations) == 11  # 0 to 10 inclusive
        assert stations[0].number == 0
        assert stations[0].name == "AP"
        assert stations[10].number == 10
        assert stations[10].name == "FP"
        assert stations[5].name == "midship"

    def test_station_spacing(self):
        """Test station spacing is uniform."""
        stations = get_stations(M48_LENGTH_BP, num_stations=10)

        expected_spacing = M48_LENGTH_BP / 10
        for i in range(1, len(stations)):
            actual_spacing = stations[i].x - stations[i-1].x
            assert abs(actual_spacing - expected_spacing) < 0.001

    def test_station_at_x(self):
        """Test getting station at arbitrary x position."""
        x = M48_LENGTH_BP * 0.35
        station = get_station_at_x(x, M48_LENGTH_BP, num_stations=10)

        assert station.x == x
        assert abs(station.x_normalized - 0.35) < 0.001
        # Station number should be approximately 3.5
        assert abs(station.number - 3.5) < 0.1

    def test_reference_points(self):
        """Test named reference point positions."""
        assert get_reference_point_x(ReferencePoint.AP, M48_LENGTH_BP) == 0.0
        assert get_reference_point_x(ReferencePoint.FP, M48_LENGTH_BP) == M48_LENGTH_BP
        assert get_reference_point_x(ReferencePoint.MIDSHIP, M48_LENGTH_BP) == M48_LENGTH_BP / 2


class TestFrames:
    """Tests for frame system."""

    def test_calculate_frame_spacing(self):
        """Test frame spacing calculation."""
        spacing = calculate_frame_spacing(
            length_bp=M48_LENGTH_BP,
            speed_kts=M48_SPEED,
            hull_type="semi_displacement",
        )

        # For ~45m vessel at 28kts, expect 500-600mm range
        assert 400 <= spacing <= 700

    def test_frame_locations(self):
        """Test frame location generation."""
        locations = get_frame_locations(M48_LENGTH_BP, M48_FRAME_SPACING)

        # Should have frames from 0 to ~45m
        assert len(locations) > 0
        assert locations[0] == 0.0
        assert locations[-1] <= M48_LENGTH_BP + 0.001

        # Check spacing
        spacing_m = M48_FRAME_SPACING / 1000.0
        for i in range(1, len(locations)):
            actual_spacing = locations[i] - locations[i-1]
            assert abs(actual_spacing - spacing_m) < 0.001

    def test_frame_at_x(self):
        """Test finding nearest frame."""
        frame_num, distance = get_frame_at_x(
            x=10.5,
            length_bp=M48_LENGTH_BP,
            frame_spacing=M48_FRAME_SPACING,
        )

        # Frame spacing is 0.6m, so frame 17 or 18 (10.2 or 10.8m)
        assert 17 <= frame_num <= 18
        assert distance <= M48_FRAME_SPACING / 1000.0 / 2

    def test_frames_in_zone(self):
        """Test getting frames in a zone."""
        forward_frames = get_frames_in_zone("forward", M48_LENGTH_BP, M48_FRAME_SPACING)
        midship_frames = get_frames_in_zone("midship", M48_LENGTH_BP, M48_FRAME_SPACING)
        aft_frames = get_frames_in_zone("aft", M48_LENGTH_BP, M48_FRAME_SPACING)

        # All zones should have frames
        assert len(forward_frames) > 0
        assert len(midship_frames) > 0
        assert len(aft_frames) > 0

        # Forward frames should be in 0.67-1.0 LBP
        for frame in forward_frames:
            assert frame.x >= 0.67 * M48_LENGTH_BP - 0.001

    def test_generate_frame_system(self):
        """Test complete frame system generation."""
        system = generate_frame_system(
            length_bp=M48_LENGTH_BP,
            frame_spacing=M48_FRAME_SPACING,
            web_frame_interval=4,
        )

        assert system.length_bp == M48_LENGTH_BP
        assert system.frame_spacing == M48_FRAME_SPACING
        assert len(system.frames) > 0

        # Should have web frames
        web_frames = system.get_web_frames()
        assert len(web_frames) > 0

    def test_bulkhead_positions(self):
        """Test standard bulkhead position generation."""
        positions = get_standard_bulkhead_positions(M48_LENGTH_BP, num_watertight_compartments=5)

        # Should have 4 bulkheads for 5 compartments
        assert len(positions) == 4

        # Should be evenly spaced
        expected_spacing = M48_LENGTH_BP / 5
        for i, pos in enumerate(positions):
            expected_pos = (i + 1) * expected_spacing
            assert abs(pos - expected_pos) < 0.1


class TestZones:
    """Tests for zone definitions."""

    def test_zone_for_position_bottom(self):
        """Test zone detection for bottom positions."""
        # Bottom midship position
        zone = get_zone_for_position(
            x=M48_LENGTH_BP * 0.5,  # Midship
            z=M48_DEPTH * 0.1,      # Near bottom
            length_bp=M48_LENGTH_BP,
            depth=M48_DEPTH,
            draft=M48_DRAFT,
        )
        assert zone == PressureZone.BOTTOM_MIDSHIP

    def test_zone_for_position_side(self):
        """Test zone detection for side positions."""
        # Side forward position
        zone = get_zone_for_position(
            x=M48_LENGTH_BP * 0.8,  # Forward
            z=M48_DEPTH * 0.5,      # Mid-height
            length_bp=M48_LENGTH_BP,
            depth=M48_DEPTH,
            draft=M48_DRAFT,
        )
        assert zone == PressureZone.SIDE_FORWARD

    def test_zone_for_position_deck(self):
        """Test zone detection for deck positions."""
        zone = get_zone_for_position(
            x=M48_LENGTH_BP * 0.5,
            z=M48_DEPTH * 0.9,      # Near deck
            length_bp=M48_LENGTH_BP,
            depth=M48_DEPTH,
            draft=M48_DRAFT,
        )
        assert zone == PressureZone.DECK_WEATHER

    def test_zone_boundaries(self):
        """Test zone boundary calculations."""
        bounds = get_zone_boundaries(
            PressureZone.BOTTOM_MIDSHIP,
            length_bp=M48_LENGTH_BP,
            beam=M48_BEAM,
            depth=M48_DEPTH,
        )

        assert "x" in bounds
        assert "y" in bounds
        assert "z" in bounds

        # X should be in midship region
        assert bounds["x"][0] >= 0.3 * M48_LENGTH_BP - 0.1
        assert bounds["x"][1] <= 0.7 * M48_LENGTH_BP + 0.1

    def test_all_zones(self):
        """Test getting all zones."""
        zones = get_all_zones()

        assert len(zones) > 0
        # Should have at least bottom, side, deck zones
        zone_types = {z.zone_type for z in zones}
        assert ZoneType.BOTTOM in zone_types
        assert ZoneType.SIDE in zone_types
        assert ZoneType.DECK in zone_types

    def test_zones_by_type(self):
        """Test filtering zones by type."""
        bottom_zones = get_zones_by_type(ZoneType.BOTTOM)

        assert len(bottom_zones) > 0
        # All bottom zones should include typical bottom areas
        # (wetdeck is classified as bottom for structural purposes)
        expected_bottom = {PressureZone.BOTTOM_FORWARD, PressureZone.BOTTOM_MIDSHIP,
                          PressureZone.BOTTOM_AFT, PressureZone.WETDECK}
        for zone in bottom_zones:
            assert zone in expected_bottom

    def test_slamming_zones(self):
        """Test getting slamming zones."""
        slamming = get_slamming_zones()

        assert len(slamming) > 0
        # Forward bottom should be in slamming zones
        assert PressureZone.BOTTOM_FORWARD in slamming

    def test_immersed_zones(self):
        """Test getting immersed zones."""
        immersed = get_immersed_zones()

        assert len(immersed) > 0
        # All bottom zones should be immersed
        assert PressureZone.BOTTOM_FORWARD in immersed
        assert PressureZone.BOTTOM_MIDSHIP in immersed
        assert PressureZone.BOTTOM_AFT in immersed

    def test_longitudinal_zone(self):
        """Test longitudinal zone detection."""
        assert get_longitudinal_zone(M48_LENGTH_BP * 0.1, M48_LENGTH_BP) == LongitudinalZone.AFT
        assert get_longitudinal_zone(M48_LENGTH_BP * 0.5, M48_LENGTH_BP) == LongitudinalZone.MIDSHIP
        assert get_longitudinal_zone(M48_LENGTH_BP * 0.8, M48_LENGTH_BP) == LongitudinalZone.FORWARD

    def test_vertical_zone(self):
        """Test vertical zone detection."""
        assert get_vertical_zone(M48_DRAFT * 0.3, M48_DRAFT, M48_DEPTH) == VerticalZone.BOTTOM
        assert get_vertical_zone(M48_DRAFT * 0.7, M48_DRAFT, M48_DEPTH) == VerticalZone.BILGE
        assert get_vertical_zone(M48_DEPTH * 0.5, M48_DRAFT, M48_DEPTH) == VerticalZone.SIDE
        assert get_vertical_zone(M48_DEPTH, M48_DRAFT, M48_DEPTH) == VerticalZone.DECK


class TestMembers:
    """Tests for structural member placement."""

    def test_stiffener_positions_bottom(self):
        """Test stiffener generation for bottom zone."""
        stiffeners = get_stiffener_positions(
            zone=PressureZone.BOTTOM_MIDSHIP,
            stiffener_spacing=M48_STIFFENER_SPACING,
            length_bp=M48_LENGTH_BP,
            beam=M48_BEAM,
            depth=M48_DEPTH,
            draft=M48_DRAFT,
        )

        assert len(stiffeners) > 0
        # All should be longitudinal stiffeners
        for s in stiffeners:
            assert s.member_type == MemberType.STIFFENER
            assert s.orientation == MemberOrientation.LONGITUDINAL

    def test_stiffener_positions_side(self):
        """Test stiffener generation for side zone."""
        stiffeners = get_stiffener_positions(
            zone=PressureZone.SIDE_MIDSHIP,
            stiffener_spacing=M48_STIFFENER_SPACING,
            length_bp=M48_LENGTH_BP,
            beam=M48_BEAM,
            depth=M48_DEPTH,
            draft=M48_DRAFT,
        )

        assert len(stiffeners) > 0
        # Side stiffeners on both port and starboard
        y_positions = {s.y_position for s in stiffeners}
        assert M48_BEAM / 2 in y_positions or any(y > 0 for y in y_positions)
        assert -M48_BEAM / 2 in y_positions or any(y < 0 for y in y_positions)

    def test_frame_members(self):
        """Test frame member generation."""
        members = get_frame_members(
            frame_number=10,
            frame_x=6.0,
            beam=M48_BEAM,
            depth=M48_DEPTH,
            draft=M48_DRAFT,
            length_bp=M48_LENGTH_BP,
            is_web_frame=False,
        )

        assert len(members) > 0
        # Should include floor, side frames, deck beam
        member_types = {m.member_type for m in members}
        assert MemberType.FLOOR in member_types
        assert MemberType.FRAME in member_types
        assert MemberType.DECK_BEAM in member_types

    def test_girder_positions(self):
        """Test girder position generation."""
        girders = get_girder_positions(
            length_bp=M48_LENGTH_BP,
            beam=M48_BEAM,
            depth=M48_DEPTH,
            num_side_girders=2,
        )

        assert len(girders) > 0
        # Should include center keel
        keels = [g for g in girders if g.member_type == MemberType.KEEL]
        assert len(keels) == 1
        assert keels[0].y_position == 0.0

    def test_structural_layout(self):
        """Test complete structural layout generation."""
        layout = generate_structural_layout(
            length_bp=M48_LENGTH_BP,
            beam=M48_BEAM,
            depth=M48_DEPTH,
            draft=M48_DRAFT,
            stiffener_spacing=M48_STIFFENER_SPACING,
            frame_spacing=M48_FRAME_SPACING,
        )

        assert layout.length_bp == M48_LENGTH_BP
        assert len(layout.members) > 0
        assert layout.total_stiffeners > 0
        assert layout.total_frames > 0

    def test_layout_summary(self):
        """Test layout summary generation."""
        layout = generate_structural_layout(
            length_bp=M48_LENGTH_BP,
            beam=M48_BEAM,
            depth=M48_DEPTH,
            draft=M48_DRAFT,
            stiffener_spacing=M48_STIFFENER_SPACING,
            frame_spacing=M48_FRAME_SPACING,
        )

        summary = summarize_layout(layout)

        assert "stiffener" in summary
        assert "floor" in summary
        assert summary["stiffener"] > 0


class TestM48Baseline:
    """Integration tests using M48 baseline vessel."""

    def test_m48_coordinate_system(self):
        """Test M48 coordinate system setup."""
        cs = CoordinateSystem(
            length_bp=M48_LENGTH_BP,
            beam=M48_BEAM,
            depth=M48_DEPTH,
            draft=M48_DRAFT,
        )

        # Validate key reference points
        assert cs.x_fp == 45.0
        assert cs.y_port == 6.4
        assert cs.z_deck == 4.5

    def test_m48_frame_system(self):
        """Test M48 frame system."""
        system = generate_frame_system(
            length_bp=M48_LENGTH_BP,
            frame_spacing=M48_FRAME_SPACING,
            web_frame_interval=4,
            bulkhead_positions=get_standard_bulkhead_positions(M48_LENGTH_BP, 5),
        )

        # Should have ~75 frames (45m / 0.6m spacing)
        assert 70 <= system.total_frames <= 80

        # Should have bulkheads
        bulkheads = system.get_bulkheads()
        assert len(bulkheads) >= 4

    def test_m48_full_structural_layout(self):
        """Test complete M48 structural layout."""
        layout = generate_structural_layout(
            length_bp=M48_LENGTH_BP,
            beam=M48_BEAM,
            depth=M48_DEPTH,
            draft=M48_DRAFT,
            stiffener_spacing=M48_STIFFENER_SPACING,
            frame_spacing=M48_FRAME_SPACING,
        )

        # Reasonable number of members
        assert len(layout.members) > 100  # Substantial layout

        # Summary should show variety of member types
        summary = summarize_layout(layout)
        assert len(summary) >= 4  # Multiple member types


class TestEdgeCases:
    """Edge case tests."""

    def test_zero_length(self):
        """Test handling of zero length."""
        locations = get_frame_locations(0.0, 600.0)
        assert len(locations) == 1  # Just origin

    def test_small_vessel(self):
        """Test small vessel (10m)."""
        layout = generate_structural_layout(
            length_bp=10.0,
            beam=3.0,
            depth=2.0,
            draft=0.8,
            stiffener_spacing=200.0,
            frame_spacing=400.0,
        )

        assert len(layout.members) > 0

    def test_large_vessel(self):
        """Test large vessel (100m)."""
        spacing = calculate_frame_spacing(100.0, 20.0, "displacement")
        assert 700 <= spacing <= 900

    def test_empty_zone(self):
        """Test zone with no stiffeners."""
        stiffeners = get_stiffener_positions(
            zone=PressureZone.SUPERSTRUCTURE_FRONT,  # May not generate stiffeners
            stiffener_spacing=300.0,
            length_bp=45.0,
            beam=12.8,
            depth=4.5,
            draft=1.8,
        )
        # Should handle gracefully (may be empty or have some members)
        assert isinstance(stiffeners, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
