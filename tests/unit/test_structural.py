"""
tests/unit/test_structural.py - Tests for structural module.

BRAVO OWNS THIS FILE.

Tests for Modules 21-24: Structural Detailing.
"""

import pytest
from unittest.mock import MagicMock

from magnet.structural.enums import (
    StructuralZone,
    PlateType,
    FrameType,
    StiffenerType,
    ProfileType,
    WeldType,
    WeldClass,
    WeldPosition,
    MaterialGrade,
)
from magnet.structural.grid import Frame, Bulkhead, StructuralGrid
from magnet.structural.plates import PlateExtent, Plate
from magnet.structural.grid_generator import StructuralGridGenerator
from magnet.structural.plate_generator import PlateGenerator
from magnet.structural.nesting import NestSheet, NestingResult, NestingEngine


class TestEnums:
    """Tests for structural enums."""

    def test_structural_zone_values(self):
        """Test StructuralZone enum values."""
        assert StructuralZone.BOTTOM.value == "bottom"
        assert StructuralZone.SIDE.value == "side"
        assert StructuralZone.DECK.value == "deck"
        assert StructuralZone.TRANSOM.value == "transom"
        assert StructuralZone.BULKHEAD.value == "bulkhead"

    def test_plate_type_values(self):
        """Test PlateType enum values."""
        assert PlateType.SHELL.value == "shell"
        assert PlateType.DECK.value == "deck"
        assert PlateType.BULKHEAD.value == "bulkhead"
        assert PlateType.TANK_TOP.value == "tank_top"

    def test_frame_type_values(self):
        """Test FrameType enum values."""
        assert FrameType.ORDINARY.value == "ordinary"
        assert FrameType.WEB_FRAME.value == "web_frame"
        assert FrameType.BULKHEAD.value == "bulkhead"
        assert FrameType.COLLISION.value == "collision"

    def test_stiffener_type_values(self):
        """Test StiffenerType enum values."""
        assert StiffenerType.LONGITUDINAL.value == "longitudinal"
        assert StiffenerType.TRANSVERSE_FRAME.value == "transverse_frame"
        assert StiffenerType.WEB_FRAME.value == "web_frame"
        assert StiffenerType.DECK_BEAM.value == "deck_beam"

    def test_profile_type_values(self):
        """Test ProfileType enum values."""
        assert ProfileType.FLAT_BAR.value == "flat_bar"
        assert ProfileType.ANGLE.value == "angle"
        assert ProfileType.TEE.value == "tee"
        assert ProfileType.BULB_FLAT.value == "bulb_flat"

    def test_weld_type_values(self):
        """Test WeldType enum values."""
        assert WeldType.FILLET.value == "fillet"
        assert WeldType.BUTT.value == "butt"
        assert WeldType.PLUG.value == "plug"
        assert WeldType.SEAM.value == "seam"

    def test_weld_class_values(self):
        """Test WeldClass enum values."""
        assert WeldClass.CLASS_1.value == "class_1"
        assert WeldClass.CLASS_2.value == "class_2"
        assert WeldClass.CLASS_3.value == "class_3"

    def test_weld_position_values(self):
        """Test WeldPosition enum values."""
        assert WeldPosition.FLAT_1F.value == "1F"
        assert WeldPosition.HORIZONTAL_2F.value == "2F"
        assert WeldPosition.VERTICAL_3F.value == "3F"
        assert WeldPosition.OVERHEAD_4F.value == "4F"

    def test_material_grade_values(self):
        """Test MaterialGrade enum values."""
        assert MaterialGrade.AL_5083_H116.value == "5083-H116"
        assert MaterialGrade.AL_6061_T6.value == "6061-T6"


class TestFrame:
    """Tests for Frame dataclass."""

    def test_create_frame(self):
        """Test creating a frame."""
        frame = Frame(
            frame_number=10,
            x_position=5.0,
            frame_type=FrameType.ORDINARY,
            spacing_fwd=500.0,
        )
        assert frame.frame_number == 10
        assert frame.x_position == 5.0
        assert frame.frame_type == FrameType.ORDINARY
        assert frame.spacing_fwd == 500.0

    def test_frame_web_frame(self):
        """Test web frame creation."""
        frame = Frame(
            frame_number=12,
            x_position=6.0,
            frame_type=FrameType.WEB_FRAME,
            is_web_frame=True,
        )
        assert frame.is_web_frame is True
        assert frame.frame_type == FrameType.WEB_FRAME

    def test_frame_to_dict(self):
        """Test frame serialization."""
        frame = Frame(
            frame_number=5,
            x_position=2.5,
            frame_type=FrameType.ORDINARY,
            is_web_frame=False,
            spacing_fwd=500.0,
        )
        data = frame.to_dict()
        assert data["frame_number"] == 5
        assert data["x_position"] == 2.5
        assert data["frame_type"] == "ordinary"
        assert data["is_web_frame"] is False


class TestBulkhead:
    """Tests for Bulkhead dataclass."""

    def test_create_bulkhead(self):
        """Test creating a bulkhead."""
        bh = Bulkhead(
            bulkhead_id="BH-001",
            frame_number=20,
            x_position=10.0,
            bulkhead_type="watertight",
            height_m=3.0,
            width_m=6.0,
        )
        assert bh.bulkhead_id == "BH-001"
        assert bh.frame_number == 20
        assert bh.x_position == 10.0
        assert bh.height_m == 3.0

    def test_collision_bulkhead(self):
        """Test collision bulkhead."""
        bh = Bulkhead(
            bulkhead_id="BH-COLLISION",
            is_collision_bulkhead=True,
            compartment_fwd="forepeak",
            compartment_aft="forward_hold",
        )
        assert bh.is_collision_bulkhead is True
        assert bh.compartment_fwd == "forepeak"

    def test_bulkhead_to_dict(self):
        """Test bulkhead serialization."""
        bh = Bulkhead(
            bulkhead_id="BH-002",
            frame_number=15,
            x_position=7.5,
            bulkhead_type="watertight",
            height_m=3.0,
            width_m=6.0,
        )
        data = bh.to_dict()
        assert data["bulkhead_id"] == "BH-002"
        assert data["frame_number"] == 15
        assert data["bulkhead_type"] == "watertight"


class TestStructuralGrid:
    """Tests for StructuralGrid dataclass."""

    def test_create_grid(self):
        """Test creating a structural grid."""
        grid = StructuralGrid(
            loa=26.0,
            lwl=24.0,
            beam=6.0,
            depth=3.0,
            frame_spacing_mm=500.0,
        )
        assert grid.loa == 26.0
        assert grid.lwl == 24.0
        assert grid.frame_spacing_mm == 500.0

    def test_grid_get_bulkheads(self):
        """Test getting bulkheads."""
        grid = StructuralGrid()
        grid.bulkheads = [
            Bulkhead(bulkhead_id="BH-1"),
            Bulkhead(bulkhead_id="BH-2"),
        ]
        bhs = grid.get_bulkheads()
        assert len(bhs) == 2

    def test_grid_get_web_frames(self):
        """Test getting web frames."""
        grid = StructuralGrid()
        grid.frames = [
            Frame(frame_number=0, is_web_frame=False),
            Frame(frame_number=4, is_web_frame=True),
            Frame(frame_number=8, is_web_frame=True),
        ]
        webs = grid.get_web_frames()
        assert len(webs) == 2
        assert all(f.is_web_frame for f in webs)

    def test_grid_get_frame_at_x(self):
        """Test getting frame at x position."""
        grid = StructuralGrid()
        grid.frames = [
            Frame(frame_number=0, x_position=0.0),
            Frame(frame_number=1, x_position=0.5),
            Frame(frame_number=2, x_position=1.0),
        ]
        frame = grid.get_frame_at_x(0.51, tolerance=0.1)
        assert frame is not None
        assert frame.frame_number == 1

    def test_grid_get_frame_at_x_not_found(self):
        """Test getting frame at x when not found."""
        grid = StructuralGrid()
        grid.frames = [
            Frame(frame_number=0, x_position=0.0),
            Frame(frame_number=1, x_position=0.5),
        ]
        frame = grid.get_frame_at_x(5.0, tolerance=0.1)
        assert frame is None

    def test_grid_get_frames_in_range(self):
        """Test getting frames in range."""
        grid = StructuralGrid()
        grid.frames = [
            Frame(frame_number=i, x_position=i * 0.5) for i in range(10)
        ]
        frames = grid.get_frames_in_range(1.0, 2.5)
        assert len(frames) == 4  # Frames at 1.0, 1.5, 2.0, 2.5

    def test_grid_to_dict(self):
        """Test grid serialization."""
        grid = StructuralGrid(loa=26.0, lwl=24.0, beam=6.0, depth=3.0)
        data = grid.to_dict()
        assert data["loa"] == 26.0
        assert data["lwl"] == 24.0
        assert "frames" in data
        assert "bulkheads" in data


class TestPlateExtent:
    """Tests for PlateExtent dataclass."""

    def test_create_extent(self):
        """Test creating plate extent."""
        extent = PlateExtent(
            frame_start=0,
            frame_end=10,
            y_start=0.0,
            y_end=1.5,
            z_start=0.0,
            z_end=1.0,
        )
        assert extent.frame_start == 0
        assert extent.frame_end == 10
        assert extent.y_end == 1.5

    def test_extent_length(self):
        """Test extent length property."""
        extent = PlateExtent(y_start=0.0, y_end=2.0)
        assert extent.length_m == 2.0

    def test_extent_width(self):
        """Test extent width property."""
        extent = PlateExtent(z_start=0.0, z_end=1.5)
        assert extent.width_m == 1.5

    def test_extent_width_horizontal(self):
        """Test extent width for horizontal plate."""
        extent = PlateExtent(
            y_start=0.0, y_end=2.0, z_start=1.0, z_end=1.0
        )
        assert extent.width_m == 2.0

    def test_extent_area(self):
        """Test extent area property."""
        extent = PlateExtent(
            y_start=0.0, y_end=2.0, z_start=0.0, z_end=1.5
        )
        assert extent.area_m2 == 3.0

    def test_extent_to_dict(self):
        """Test extent serialization."""
        extent = PlateExtent(
            frame_start=0, frame_end=5,
            y_start=0.0, y_end=1.0,
            z_start=0.0, z_end=0.5,
        )
        data = extent.to_dict()
        assert data["frame_start"] == 0
        assert data["frame_end"] == 5
        assert "area_m2" in data


class TestPlate:
    """Tests for Plate dataclass."""

    def test_create_plate(self):
        """Test creating a plate."""
        plate = Plate(
            plate_id="PL-001",
            plate_type=PlateType.SHELL,
            zone="bottom",
            material=MaterialGrade.AL_5083_H116,
            thickness_mm=6.0,
        )
        assert plate.plate_id == "PL-001"
        assert plate.plate_type == PlateType.SHELL
        assert plate.zone == "bottom"
        assert plate.thickness_mm == 6.0

    def test_plate_weight(self):
        """Test plate weight calculation."""
        extent = PlateExtent(
            y_start=0.0, y_end=2.0, z_start=0.0, z_end=1.0
        )  # 2 m^2
        plate = Plate(
            plate_id="PL-002",
            thickness_mm=6.0,  # 6mm
            extent=extent,
        )
        # Weight = 2 m^2 * 0.006m * 2700 kg/m^3 = 32.4 kg
        assert abs(plate.weight_kg - 32.4) < 0.1

    def test_plate_to_dict(self):
        """Test plate serialization."""
        plate = Plate(
            plate_id="PL-003",
            plate_type=PlateType.DECK,
            zone="deck",
            thickness_mm=5.0,
            is_developed=True,
        )
        data = plate.to_dict()
        assert data["plate_id"] == "PL-003"
        assert data["plate_type"] == "deck"
        assert data["is_developed"] is True
        assert "weight_kg" in data


class TestStructuralGridGenerator:
    """Tests for StructuralGridGenerator."""

    def _create_mock_state(self, **overrides):
        """Create mock state manager."""
        defaults = {
            "hull.loa": 26.0,
            "hull.lwl": 24.0,
            "hull.beam": 6.0,
            "hull.depth": 3.0,
            "hull.draft": 1.5,
            "mission.max_speed_kts": 30,
        }
        defaults.update(overrides)

        state = MagicMock()
        state.get = lambda key, default=None: defaults.get(key, default)
        return state

    def test_create_generator(self):
        """Test creating grid generator."""
        state = self._create_mock_state()
        generator = StructuralGridGenerator(state)
        assert generator.lwl == 24.0
        assert generator.beam == 6.0

    def test_generate_grid(self):
        """Test generating structural grid."""
        state = self._create_mock_state()
        generator = StructuralGridGenerator(state)
        grid = generator.generate()

        assert grid.loa == 26.0
        assert grid.lwl == 24.0
        assert len(grid.frames) > 0
        assert len(grid.bulkheads) > 0

    def test_generate_frames_spacing(self):
        """Test frame spacing calculation."""
        state = self._create_mock_state(**{"hull.lwl": 24.0})
        generator = StructuralGridGenerator(state)
        grid = generator.generate()

        # 24m vessel should have 500mm spacing
        assert grid.frame_spacing_mm == 500.0

    def test_generate_frames_small_vessel(self):
        """Test frame spacing for small vessel."""
        state = self._create_mock_state(**{"hull.lwl": 12.0, "hull.loa": 13.0})
        generator = StructuralGridGenerator(state)
        grid = generator.generate()

        # < 15m vessel should have 400mm spacing
        assert grid.frame_spacing_mm == 400.0

    def test_generate_frames_large_vessel(self):
        """Test frame spacing for large vessel."""
        state = self._create_mock_state(**{"hull.lwl": 35.0, "hull.loa": 38.0})
        generator = StructuralGridGenerator(state)
        grid = generator.generate()

        # 25-40m vessel should have 600mm spacing
        assert grid.frame_spacing_mm == 600.0

    def test_generate_web_frames_high_speed(self):
        """Test web frame spacing for high-speed vessel."""
        state = self._create_mock_state(**{"mission.max_speed_kts": 40})
        generator = StructuralGridGenerator(state)
        grid = generator.generate()

        # High-speed: web every 3rd frame
        assert grid.web_frame_spacing == 3

    def test_generate_web_frames_low_speed(self):
        """Test web frame spacing for low-speed vessel."""
        state = self._create_mock_state(**{"mission.max_speed_kts": 20})
        generator = StructuralGridGenerator(state)
        grid = generator.generate()

        # Low-speed: web every 5th frame
        assert grid.web_frame_spacing == 5

    def test_generate_collision_bulkhead(self):
        """Test collision bulkhead generation."""
        state = self._create_mock_state()
        generator = StructuralGridGenerator(state)
        grid = generator.generate()

        collision_bhs = [b for b in grid.bulkheads if b.is_collision_bulkhead]
        assert len(collision_bhs) == 1
        assert collision_bhs[0].bulkhead_id == "BH-COLLISION"

    def test_generate_engine_room_bulkheads(self):
        """Test engine room bulkhead generation."""
        state = self._create_mock_state()
        generator = StructuralGridGenerator(state)
        grid = generator.generate()

        er_bhs = [b for b in grid.bulkheads if "ER" in b.bulkhead_id]
        assert len(er_bhs) == 2  # ER-AFT and ER-FWD

    def test_generate_mid_bulkhead_large_vessel(self):
        """Test mid bulkhead for large vessel."""
        state = self._create_mock_state(**{"hull.lwl": 35.0, "hull.loa": 38.0})
        generator = StructuralGridGenerator(state)
        grid = generator.generate()

        mid_bhs = [b for b in grid.bulkheads if "MID" in b.bulkhead_id]
        assert len(mid_bhs) == 1  # Mid bulkhead added for > 30m

    def test_generate_no_mid_bulkhead_small_vessel(self):
        """Test no mid bulkhead for small vessel."""
        state = self._create_mock_state(**{"hull.lwl": 24.0})
        generator = StructuralGridGenerator(state)
        grid = generator.generate()

        mid_bhs = [b for b in grid.bulkheads if "MID" in b.bulkhead_id]
        assert len(mid_bhs) == 0  # No mid bulkhead for < 30m


class TestPlateGenerator:
    """Tests for PlateGenerator."""

    def _create_mock_state(self, **overrides):
        """Create mock state manager."""
        defaults = {
            "hull.lwl": 24.0,
            "hull.beam": 6.0,
            "hull.depth": 3.0,
            "hull.draft": 1.5,
            "structure.bottom_plate_thickness_mm": 6.0,
            "structure.side_plate_thickness_mm": 5.0,
            "structure.deck_plate_thickness_mm": 5.0,
            "structure.transom_plate_thickness_mm": 6.0,
        }
        defaults.update(overrides)

        state = MagicMock()
        state.get = lambda key, default=None: defaults.get(key, default)
        return state

    def _create_test_grid(self):
        """Create test structural grid."""
        grid = StructuralGrid(
            loa=26.0,
            lwl=24.0,
            beam=6.0,
            depth=3.0,
            frame_spacing_mm=500.0,
        )
        grid.frames = [
            Frame(frame_number=i, x_position=i * 0.5) for i in range(53)
        ]
        grid.bulkheads = [
            Bulkhead(bulkhead_id="BH-1", x_position=6.0, height_m=3.0, width_m=6.0),
            Bulkhead(bulkhead_id="BH-2", x_position=12.0, height_m=3.0, width_m=6.0),
            Bulkhead(bulkhead_id="BH-3", x_position=22.0, height_m=3.0, width_m=6.0),
        ]
        return grid

    def test_create_plate_generator(self):
        """Test creating plate generator."""
        state = self._create_mock_state()
        generator = PlateGenerator(state)
        assert generator.lwl == 24.0
        assert generator.beam == 6.0

    def test_generate_shell_plates(self):
        """Test generating shell plates."""
        state = self._create_mock_state()
        generator = PlateGenerator(state)
        grid = self._create_test_grid()

        plates = generator.generate_shell_plates(grid)

        assert len(plates) > 0
        bottom_plates = [p for p in plates if p.zone == "bottom"]
        side_plates = [p for p in plates if p.zone == "side"]
        transom_plates = [p for p in plates if p.zone == "transom"]

        assert len(bottom_plates) > 0
        assert len(side_plates) > 0
        assert len(transom_plates) == 1

    def test_generate_deck_plates(self):
        """Test generating deck plates."""
        state = self._create_mock_state()
        generator = PlateGenerator(state)
        grid = self._create_test_grid()

        plates = generator.generate_deck_plates(grid)

        assert len(plates) > 0
        assert all(p.plate_type == PlateType.DECK for p in plates)

    def test_generate_bulkhead_plates(self):
        """Test generating bulkhead plates."""
        state = self._create_mock_state()
        generator = PlateGenerator(state)
        grid = self._create_test_grid()

        plates = generator.generate_bulkhead_plates(grid)

        assert len(plates) == 3  # One per bulkhead
        assert all(p.plate_type == PlateType.BULKHEAD for p in plates)

    def test_generate_all_plates(self):
        """Test generating all plates."""
        state = self._create_mock_state()
        generator = PlateGenerator(state)
        grid = self._create_test_grid()

        plates = generator.generate_all_plates(grid)

        assert len(plates) > 0

        # Should have plates of each type
        types = {p.plate_type for p in plates}
        assert PlateType.SHELL in types
        assert PlateType.DECK in types
        assert PlateType.BULKHEAD in types


class TestNestSheet:
    """Tests for NestSheet dataclass."""

    def test_create_nest_sheet(self):
        """Test creating nest sheet."""
        sheet = NestSheet(
            sheet_id="SHEET-001",
            thickness_mm=6.0,
            length_mm=6000.0,
            width_mm=2000.0,
        )
        assert sheet.sheet_id == "SHEET-001"
        assert sheet.thickness_mm == 6.0
        assert sheet.length_mm == 6000.0

    def test_nest_sheet_to_dict(self):
        """Test nest sheet serialization."""
        sheet = NestSheet(
            sheet_id="SHEET-002",
            thickness_mm=5.0,
            utilization_percent=75.5,
        )
        data = sheet.to_dict()
        assert data["sheet_id"] == "SHEET-002"
        assert data["utilization_percent"] == 75.5


class TestNestingResult:
    """Tests for NestingResult dataclass."""

    def test_create_nesting_result(self):
        """Test creating nesting result."""
        result = NestingResult(
            total_sheets=10,
            total_plate_area_mm2=1e8,
            average_utilization_percent=80.0,
        )
        assert result.total_sheets == 10
        assert result.average_utilization_percent == 80.0

    def test_nesting_result_to_dict(self):
        """Test nesting result serialization."""
        result = NestingResult(
            total_sheets=5,
            average_utilization_percent=75.0,
        )
        data = result.to_dict()
        assert data["total_sheets"] == 5
        assert "sheets" in data


class TestNestingEngine:
    """Tests for NestingEngine."""

    def _create_test_plates(self):
        """Create test plates."""
        plates = []
        for i in range(10):
            plate = Plate(
                plate_id=f"PL-{i:03d}",
                thickness_mm=6.0,
                extent=PlateExtent(
                    y_start=0, y_end=1.5,
                    z_start=0, z_end=1.0,
                ),  # 1.5 m^2 each
            )
            plates.append(plate)
        return plates

    def test_create_nesting_engine(self):
        """Test creating nesting engine."""
        engine = NestingEngine()
        assert engine.sheets == []

    def test_nest_plates_basic(self):
        """Test basic plate nesting."""
        engine = NestingEngine()
        plates = self._create_test_plates()

        sheets = engine.nest_plates(plates)

        assert len(sheets) > 0
        # All plates should be placed
        total_placed = sum(len(s.plates) for s in sheets)
        assert total_placed == len(plates)

    def test_nest_plates_by_thickness(self):
        """Test nesting groups plates by thickness."""
        engine = NestingEngine()
        plates = [
            Plate(plate_id="PL-1", thickness_mm=6.0, extent=PlateExtent(y_end=1.0, z_end=0.5)),
            Plate(plate_id="PL-2", thickness_mm=6.0, extent=PlateExtent(y_end=1.0, z_end=0.5)),
            Plate(plate_id="PL-3", thickness_mm=5.0, extent=PlateExtent(y_end=1.0, z_end=0.5)),
        ]

        sheets = engine.nest_plates(plates)

        # Should have separate sheets for different thicknesses
        thicknesses = {s.thickness_mm for s in sheets}
        assert 6.0 in thicknesses
        assert 5.0 in thicknesses

    def test_nest_plates_utilization(self):
        """Test plate nesting calculates utilization."""
        engine = NestingEngine()
        plates = self._create_test_plates()

        sheets = engine.nest_plates(plates)

        for sheet in sheets:
            assert sheet.utilization_percent >= 0
            assert sheet.utilization_percent <= 100
            assert sheet.scrap_area_mm2 >= 0

    def test_get_nesting_result(self):
        """Test getting nesting result."""
        engine = NestingEngine()
        plates = self._create_test_plates()

        engine.nest_plates(plates)
        result = engine.get_nesting_result()

        assert result.total_sheets > 0
        assert result.total_plate_area_mm2 > 0
        assert result.average_utilization_percent > 0

    def test_calculate_material_summary(self):
        """Test material summary calculation."""
        engine = NestingEngine()
        plates = self._create_test_plates()

        sheets = engine.nest_plates(plates)
        summary = engine.calculate_material_summary(sheets)

        assert "total_sheets" in summary
        assert "total_plate_area_m2" in summary
        assert "average_utilization_percent" in summary
        assert "weight_by_thickness_kg" in summary


class TestIntegrationGridToPlates:
    """Integration tests for grid to plate generation."""

    def test_full_pipeline(self):
        """Test full structural pipeline."""
        # Create mock state
        state = MagicMock()
        state.get = lambda key, default=None: {
            "hull.loa": 26.0,
            "hull.lwl": 24.0,
            "hull.beam": 6.0,
            "hull.depth": 3.0,
            "hull.draft": 1.5,
            "mission.max_speed_kts": 30,
            "structure.bottom_plate_thickness_mm": 6.0,
            "structure.side_plate_thickness_mm": 5.0,
            "structure.deck_plate_thickness_mm": 5.0,
            "structure.transom_plate_thickness_mm": 6.0,
        }.get(key, default)

        # Generate grid
        grid_gen = StructuralGridGenerator(state)
        grid = grid_gen.generate()

        assert len(grid.frames) > 0
        assert len(grid.bulkheads) > 0

        # Generate plates
        plate_gen = PlateGenerator(state)
        plates = plate_gen.generate_all_plates(grid)

        assert len(plates) > 0

        # Nest plates
        engine = NestingEngine()
        sheets = engine.nest_plates(plates)

        assert len(sheets) > 0

        # Get summary
        result = engine.get_nesting_result()
        assert result.total_sheets > 0
        assert result.average_utilization_percent > 0
