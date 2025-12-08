"""
tests/unit/test_structural_advanced.py - Tests for advanced structural modules.

BRAVO OWNS THIS FILE.

Tests for Modules 23-25: Stiffeners, Welds, Scantlings.
"""

import pytest
from unittest.mock import MagicMock

from magnet.structural.enums import (
    StiffenerType,
    ProfileType,
    MaterialGrade,
    WeldType,
    WeldClass,
    WeldPosition,
    StructuralZone,
)
from magnet.structural.stiffeners import (
    ProfileSection,
    Stiffener,
    StiffenerSummary,
)
from magnet.structural.stiffener_generator import StiffenerGenerator
from magnet.structural.welds import (
    WeldProcess,
    WeldParameters,
    WeldJoint,
    WeldSeam,
    WeldSummary,
)
from magnet.structural.weld_generator import WeldGenerator
from magnet.structural.scantlings import (
    MaterialProperties,
    DesignPressure,
    ScantlingResult,
    ScantlingCalculator,
    ScantlingSummary,
)
from magnet.structural.grid import StructuralGrid, Frame, Bulkhead
from magnet.structural.plates import Plate, PlateExtent


# === MODULE 23: STIFFENERS ===

class TestProfileSection:
    """Tests for ProfileSection dataclass."""

    def test_create_flat_bar(self):
        """Test creating flat bar profile."""
        profile = ProfileSection.flat_bar(100, 8)
        assert profile.profile_type == ProfileType.FLAT_BAR
        assert profile.height_mm == 100
        assert profile.web_thickness_mm == 8
        assert profile.designation == "100x8"

    def test_flat_bar_area(self):
        """Test flat bar area calculation."""
        profile = ProfileSection.flat_bar(100, 10)
        assert profile.area_mm2 == 1000  # 100 * 10

    def test_flat_bar_inertia(self):
        """Test flat bar moment of inertia."""
        profile = ProfileSection.flat_bar(100, 10)
        # I = b*h^3/12 = 10*100^3/12 = 833333 mm^4 = 83.33 cm^4
        assert abs(profile.moment_of_inertia_cm4 - 83.33) < 1

    def test_create_angle(self):
        """Test creating angle profile."""
        profile = ProfileSection.angle(75, 50, 6)
        assert profile.profile_type == ProfileType.ANGLE
        assert profile.designation == "L75x50x6"
        assert profile.height_mm == 75
        assert profile.width_mm == 50

    def test_create_tee(self):
        """Test creating tee profile."""
        profile = ProfileSection.tee(100, 80, 6, 8)
        assert profile.profile_type == ProfileType.TEE
        assert profile.height_mm == 100
        assert profile.flange_thickness_mm == 8

    def test_create_bulb_flat(self):
        """Test creating bulb flat profile."""
        profile = ProfileSection.bulb_flat(120, 12)
        assert profile.profile_type == ProfileType.BULB_FLAT
        assert "HP" in profile.designation

    def test_weight_per_meter(self):
        """Test weight per meter calculation."""
        profile = ProfileSection.flat_bar(100, 10)
        # 1000 mm^2 = 0.001 m^2, * 2700 kg/m^3 = 2.7 kg/m
        assert abs(profile.weight_per_meter_kg - 2.7) < 0.1

    def test_profile_to_dict(self):
        """Test profile serialization."""
        profile = ProfileSection.flat_bar(80, 6)
        data = profile.to_dict()
        assert data["profile_type"] == "flat_bar"
        assert data["height_mm"] == 80
        assert "weight_per_meter_kg" in data


class TestStiffener:
    """Tests for Stiffener dataclass."""

    def test_create_stiffener(self):
        """Test creating a stiffener."""
        profile = ProfileSection.flat_bar(80, 6)
        stiff = Stiffener(
            stiffener_id="L-001",
            stiffener_type=StiffenerType.LONGITUDINAL,
            zone="bottom",
            material=MaterialGrade.AL_6061_T6,
            profile=profile,
            length_m=5.0,
        )
        assert stiff.stiffener_id == "L-001"
        assert stiff.stiffener_type == StiffenerType.LONGITUDINAL
        assert stiff.length_m == 5.0

    def test_stiffener_weight(self):
        """Test stiffener weight calculation."""
        profile = ProfileSection.flat_bar(100, 10)  # ~2.7 kg/m
        stiff = Stiffener(profile=profile, length_m=10.0)
        # 2.7 kg/m * 10m = 27 kg
        assert abs(stiff.weight_kg - 27) < 1

    def test_stiffener_to_dict(self):
        """Test stiffener serialization."""
        stiff = Stiffener(
            stiffener_id="FR-001",
            stiffener_type=StiffenerType.TRANSVERSE_FRAME,
            zone="side",
            length_m=3.0,
        )
        data = stiff.to_dict()
        assert data["stiffener_id"] == "FR-001"
        assert data["stiffener_type"] == "transverse_frame"
        assert "weight_kg" in data


class TestStiffenerSummary:
    """Tests for StiffenerSummary dataclass."""

    def test_create_summary(self):
        """Test creating stiffener summary."""
        summary = StiffenerSummary(
            total_count=100,
            total_length_m=500.0,
            total_weight_kg=1500.0,
        )
        assert summary.total_count == 100
        assert summary.total_weight_kg == 1500.0

    def test_summary_to_dict(self):
        """Test summary serialization."""
        summary = StiffenerSummary(total_count=50)
        data = summary.to_dict()
        assert data["total_count"] == 50


class TestStiffenerGenerator:
    """Tests for StiffenerGenerator."""

    def _create_mock_state(self, **overrides):
        """Create mock state manager."""
        defaults = {
            "hull.lwl": 24.0,
            "hull.beam": 6.0,
            "hull.depth": 3.0,
            "hull.draft": 1.5,
        }
        defaults.update(overrides)
        state = MagicMock()
        state.get = lambda key, default=None: defaults.get(key, default)
        return state

    def _create_test_grid(self):
        """Create test structural grid."""
        grid = StructuralGrid(
            loa=26.0, lwl=24.0, beam=6.0, depth=3.0,
            frame_spacing_mm=500.0,
            bottom_long_spacing_mm=300.0,
            side_long_spacing_mm=400.0,
            deck_long_spacing_mm=500.0,
        )
        grid.frames = [Frame(frame_number=i, x_position=i*0.5, is_web_frame=(i%4==0)) for i in range(53)]
        return grid

    def _create_test_plates(self):
        """Create test plates."""
        return [
            Plate(plate_id="PL-BOT-001", zone="bottom", thickness_mm=6.0,
                  extent=PlateExtent(frame_start=0, frame_end=10, y_start=0, y_end=1.5)),
            Plate(plate_id="PL-SIDE-001", zone="side", thickness_mm=5.0,
                  extent=PlateExtent(frame_start=0, frame_end=10, y_start=0, y_end=1.5)),
        ]

    def test_create_generator(self):
        """Test creating stiffener generator."""
        state = self._create_mock_state()
        generator = StiffenerGenerator(state)
        assert generator.lwl == 24.0

    def test_generate_longitudinals(self):
        """Test generating longitudinal stiffeners."""
        state = self._create_mock_state()
        generator = StiffenerGenerator(state)
        grid = self._create_test_grid()
        plates = self._create_test_plates()

        stiffeners = generator.generate_longitudinals(grid, plates)

        assert len(stiffeners) > 0
        assert all(s.stiffener_type == StiffenerType.LONGITUDINAL for s in stiffeners)

    def test_generate_transverse_frames(self):
        """Test generating transverse frame stiffeners."""
        state = self._create_mock_state()
        generator = StiffenerGenerator(state)
        grid = self._create_test_grid()
        plates = self._create_test_plates()

        stiffeners = generator.generate_transverse_frames(grid, plates)

        assert len(stiffeners) > 0
        frame_types = {s.stiffener_type for s in stiffeners}
        assert StiffenerType.TRANSVERSE_FRAME in frame_types or StiffenerType.WEB_FRAME in frame_types

    def test_generate_deck_beams(self):
        """Test generating deck beams."""
        state = self._create_mock_state()
        generator = StiffenerGenerator(state)
        grid = self._create_test_grid()

        beams = generator.generate_deck_beams(grid)

        assert len(beams) > 0
        assert all(b.stiffener_type == StiffenerType.DECK_BEAM for b in beams)

    def test_generate_girders(self):
        """Test generating girders."""
        state = self._create_mock_state()
        generator = StiffenerGenerator(state)
        grid = self._create_test_grid()

        girders = generator.generate_girders(grid)

        assert len(girders) >= 3  # CL + P + S
        assert all(g.stiffener_type == StiffenerType.GIRDER for g in girders)

    def test_generate_all_stiffeners(self):
        """Test generating all stiffeners."""
        state = self._create_mock_state()
        generator = StiffenerGenerator(state)
        grid = self._create_test_grid()
        plates = self._create_test_plates()

        stiffeners = generator.generate_all_stiffeners(grid, plates)

        assert len(stiffeners) > 0
        types = {s.stiffener_type for s in stiffeners}
        assert len(types) >= 3  # Multiple types

    def test_calculate_summary(self):
        """Test calculating stiffener summary."""
        state = self._create_mock_state()
        generator = StiffenerGenerator(state)
        grid = self._create_test_grid()
        plates = self._create_test_plates()

        stiffeners = generator.generate_all_stiffeners(grid, plates)
        summary = generator.calculate_summary(stiffeners)

        assert summary.total_count == len(stiffeners)
        assert summary.total_length_m > 0
        assert summary.total_weight_kg > 0


# === MODULE 24: WELDS ===

class TestWeldParameters:
    """Tests for WeldParameters dataclass."""

    def test_create_parameters(self):
        """Test creating weld parameters."""
        params = WeldParameters(
            process=WeldProcess.GMAW,
            filler_wire="ER5356",
            current_amps=180.0,
        )
        assert params.process == WeldProcess.GMAW
        assert params.filler_wire == "ER5356"
        assert params.current_amps == 180.0

    def test_parameters_to_dict(self):
        """Test parameters serialization."""
        params = WeldParameters()
        data = params.to_dict()
        assert data["process"] == "gmaw"
        assert "filler_wire" in data


class TestWeldJoint:
    """Tests for WeldJoint dataclass."""

    def test_create_fillet_weld(self):
        """Test creating fillet weld."""
        weld = WeldJoint(
            weld_id="W-001",
            weld_type=WeldType.FILLET,
            weld_class=WeldClass.CLASS_2,
            leg_size_mm=5.0,
            length_mm=1000.0,
        )
        assert weld.weld_id == "W-001"
        assert weld.weld_type == WeldType.FILLET
        assert weld.leg_size_mm == 5.0

    def test_throat_calculation(self):
        """Test throat is calculated from leg size."""
        weld = WeldJoint(leg_size_mm=5.0)
        # throat = 0.707 * leg
        assert abs(weld.throat_mm - 3.535) < 0.01

    def test_weld_volume(self):
        """Test weld volume calculation."""
        weld = WeldJoint(
            weld_type=WeldType.FILLET,
            leg_size_mm=5.0,
            length_mm=1000.0,
        )
        # Area = 0.5 * 5 * 5 = 12.5 mm^2
        # Volume = 12.5 * 1000 = 12500 mm^3
        assert abs(weld.volume_mm3 - 12500) < 1

    def test_weld_weight(self):
        """Test weld weight calculation."""
        weld = WeldJoint(
            weld_type=WeldType.FILLET,
            leg_size_mm=5.0,
            length_mm=1000.0,
        )
        # Volume = 12500 mm^3 = 1.25e-5 m^3
        # Weight = 1.25e-5 * 2700 = 0.034 kg
        assert weld.weight_kg > 0
        assert weld.weight_kg < 0.1

    def test_weld_time(self):
        """Test weld time estimation."""
        weld = WeldJoint(
            length_mm=400.0,
            parameters=WeldParameters(travel_speed_mmpm=400.0),
        )
        # Time = 400 / 400 = 1 minute
        assert abs(weld.weld_time_minutes - 1.0) < 0.01

    def test_weld_to_dict(self):
        """Test weld serialization."""
        weld = WeldJoint(weld_id="W-002", weld_type=WeldType.BUTT)
        data = weld.to_dict()
        assert data["weld_id"] == "W-002"
        assert data["weld_type"] == "butt"


class TestWeldSeam:
    """Tests for WeldSeam dataclass."""

    def test_create_seam(self):
        """Test creating weld seam."""
        seam = WeldSeam(seam_id="SEAM-001", seam_type="plate_to_plate")
        assert seam.seam_id == "SEAM-001"

    def test_seam_totals(self):
        """Test seam total calculations."""
        seam = WeldSeam()
        seam.welds = [
            WeldJoint(leg_size_mm=5.0, length_mm=500.0),
            WeldJoint(leg_size_mm=5.0, length_mm=500.0),
        ]
        assert seam.total_length_mm == 1000.0
        assert seam.total_weight_kg > 0


class TestWeldSummary:
    """Tests for WeldSummary dataclass."""

    def test_create_summary(self):
        """Test creating weld summary."""
        summary = WeldSummary(
            total_welds=500,
            total_length_m=250.0,
            total_time_hours=12.0,
        )
        assert summary.total_welds == 500
        assert summary.total_length_m == 250.0


class TestWeldGenerator:
    """Tests for WeldGenerator."""

    def _create_mock_state(self):
        """Create mock state manager."""
        state = MagicMock()
        state.get = lambda key, default=None: {
            "hull.lwl": 24.0,
            "hull.beam": 6.0,
            "hull.depth": 3.0,
            "hull.draft": 1.5,
        }.get(key, default)
        return state

    def _create_test_grid(self):
        """Create test structural grid."""
        grid = StructuralGrid(loa=26.0, frame_spacing_mm=500.0)
        grid.frames = [Frame(frame_number=i, x_position=i*0.5) for i in range(53)]
        grid.bulkheads = [Bulkhead(bulkhead_id="BH-1", x_position=12.0, height_m=3.0, width_m=6.0)]
        return grid

    def _create_test_plates(self):
        """Create test plates."""
        return [
            Plate(plate_id="PL-001", zone="bottom", thickness_mm=6.0,
                  extent=PlateExtent(frame_start=0, frame_end=10, y_start=0, y_end=1.5)),
            Plate(plate_id="PL-002", zone="bottom", thickness_mm=6.0,
                  extent=PlateExtent(frame_start=10, frame_end=20, y_start=0, y_end=1.5)),
            Plate(plate_id="PL-BH", zone="bulkhead", thickness_mm=5.0,
                  extent=PlateExtent(y_start=-3, y_end=3, z_start=0, z_end=3)),
        ]

    def _create_test_stiffeners(self):
        """Create test stiffeners."""
        return [
            Stiffener(stiffener_id="L-001", stiffener_type=StiffenerType.LONGITUDINAL,
                      zone="bottom", length_m=5.0, attached_to_plate="PL-001",
                      profile=ProfileSection.flat_bar(80, 6)),
        ]

    def test_create_generator(self):
        """Test creating weld generator."""
        state = self._create_mock_state()
        generator = WeldGenerator(state)
        assert generator.weld_counter == 0

    def test_generate_stiffener_welds(self):
        """Test generating stiffener attachment welds."""
        state = self._create_mock_state()
        generator = WeldGenerator(state)
        stiffeners = self._create_test_stiffeners()
        plates = self._create_test_plates()

        welds = generator.generate_stiffener_welds(stiffeners, plates)

        assert len(welds) >= 2  # Two fillet welds per stiffener
        assert all(w.weld_type == WeldType.FILLET for w in welds)

    def test_generate_bulkhead_welds(self):
        """Test generating bulkhead connection welds."""
        state = self._create_mock_state()
        generator = WeldGenerator(state)
        grid = self._create_test_grid()
        plates = self._create_test_plates()

        welds = generator.generate_bulkhead_welds(grid, plates)

        assert len(welds) > 0
        assert all(w.weld_class == WeldClass.CLASS_1 for w in welds)

    def test_generate_all_welds(self):
        """Test generating all welds."""
        state = self._create_mock_state()
        generator = WeldGenerator(state)
        grid = self._create_test_grid()
        plates = self._create_test_plates()
        stiffeners = self._create_test_stiffeners()

        welds = generator.generate_all_welds(grid, plates, stiffeners)

        assert len(welds) > 0

    def test_calculate_summary(self):
        """Test calculating weld summary."""
        state = self._create_mock_state()
        generator = WeldGenerator(state)
        grid = self._create_test_grid()
        plates = self._create_test_plates()
        stiffeners = self._create_test_stiffeners()

        welds = generator.generate_all_welds(grid, plates, stiffeners)
        summary = generator.calculate_summary(welds)

        assert summary.total_welds == len(welds)
        assert summary.total_length_m > 0


# === MODULE 25: SCANTLINGS ===

class TestMaterialProperties:
    """Tests for MaterialProperties dataclass."""

    def test_create_properties(self):
        """Test creating material properties."""
        props = MaterialProperties(
            grade=MaterialGrade.AL_5083_H116,
            yield_strength_mpa=215.0,
        )
        assert props.yield_strength_mpa == 215.0

    def test_for_grade_5083(self):
        """Test getting properties for 5083-H116."""
        props = MaterialProperties.for_grade(MaterialGrade.AL_5083_H116)
        assert props.yield_strength_mpa == 215.0
        assert props.weld_zone_factor == 0.67

    def test_for_grade_6061(self):
        """Test getting properties for 6061-T6."""
        props = MaterialProperties.for_grade(MaterialGrade.AL_6061_T6)
        assert props.yield_strength_mpa == 240.0
        assert props.weld_zone_factor == 0.50  # More HAZ reduction


class TestDesignPressure:
    """Tests for DesignPressure dataclass."""

    def test_create_pressure(self):
        """Test creating design pressure."""
        pressure = DesignPressure(
            zone=StructuralZone.BOTTOM,
            static_pressure_kpa=15.0,
            slamming_pressure_kpa=50.0,
        )
        assert pressure.zone == StructuralZone.BOTTOM
        assert pressure.slamming_pressure_kpa == 50.0


class TestScantlingResult:
    """Tests for ScantlingResult dataclass."""

    def test_create_result(self):
        """Test creating scantling result."""
        result = ScantlingResult(
            element_id="PL-001",
            zone=StructuralZone.BOTTOM,
            required_thickness_mm=5.5,
            actual_thickness_mm=6.0,
        )
        assert result.element_id == "PL-001"
        assert result.actual_thickness_mm == 6.0

    def test_utilization(self):
        """Test utilization calculation."""
        result = ScantlingResult(
            required_thickness_mm=5.0,
            actual_thickness_mm=6.0,
            utilization=5.0/6.0,
        )
        assert abs(result.utilization - 0.833) < 0.01

    def test_is_adequate(self):
        """Test adequacy check."""
        adequate = ScantlingResult(utilization=0.8, is_adequate=True)
        inadequate = ScantlingResult(utilization=1.2, is_adequate=False)
        assert adequate.is_adequate is True
        assert inadequate.is_adequate is False


class TestScantlingCalculator:
    """Tests for ScantlingCalculator."""

    def _create_mock_state(self, **overrides):
        """Create mock state manager."""
        defaults = {
            "hull.lwl": 24.0,
            "hull.beam": 6.0,
            "hull.depth": 3.0,
            "hull.draft": 1.5,
            "mission.max_speed_kts": 30,
            "hull.displacement_mt": 80,
            "hull.deadrise_deg": 20,
        }
        defaults.update(overrides)
        state = MagicMock()
        state.get = lambda key, default=None: defaults.get(key, default)
        return state

    def test_create_calculator(self):
        """Test creating scantling calculator."""
        state = self._create_mock_state()
        calc = ScantlingCalculator(state)
        assert calc.lwl == 24.0
        assert calc.speed_kts == 30

    def test_calculate_design_pressure_bottom(self):
        """Test design pressure for bottom."""
        state = self._create_mock_state()
        calc = ScantlingCalculator(state)

        pressure = calc.calculate_design_pressure(StructuralZone.BOTTOM)

        assert pressure.zone == StructuralZone.BOTTOM
        assert pressure.static_pressure_kpa > 0
        assert pressure.slamming_pressure_kpa > 0
        assert pressure.combined_pressure_kpa > 0

    def test_calculate_design_pressure_deck(self):
        """Test design pressure for deck (no hydrostatic)."""
        state = self._create_mock_state()
        calc = ScantlingCalculator(state)

        pressure = calc.calculate_design_pressure(StructuralZone.DECK)

        assert pressure.static_pressure_kpa == 0
        assert pressure.slamming_pressure_kpa == 0

    def test_slamming_increases_at_bow(self):
        """Test slamming pressure increases toward bow."""
        state = self._create_mock_state()
        calc = ScantlingCalculator(state)

        p_aft = calc.calculate_design_pressure(StructuralZone.BOTTOM, x_position=5.0)
        p_fwd = calc.calculate_design_pressure(StructuralZone.BOTTOM, x_position=20.0)

        assert p_fwd.slamming_pressure_kpa > p_aft.slamming_pressure_kpa

    def test_calculate_plate_thickness(self):
        """Test plate thickness calculation."""
        state = self._create_mock_state()
        calc = ScantlingCalculator(state)

        thickness = calc.calculate_plate_thickness(
            zone=StructuralZone.BOTTOM,
            span_mm=500.0,
            pressure_kpa=50.0,
        )

        assert thickness >= 4.0  # At least minimum
        assert thickness < 20.0  # Reasonable maximum

    def test_minimum_thickness_enforced(self):
        """Test minimum thickness is enforced."""
        state = self._create_mock_state()
        calc = ScantlingCalculator(state)

        # Very low pressure should still give minimum
        thickness = calc.calculate_plate_thickness(
            zone=StructuralZone.BOTTOM,
            span_mm=100.0,
            pressure_kpa=1.0,
        )

        assert thickness >= 4.0  # Minimum for bottom

    def test_calculate_stiffener_modulus(self):
        """Test stiffener section modulus calculation."""
        state = self._create_mock_state()
        calc = ScantlingCalculator(state)

        sm = calc.calculate_stiffener_modulus(
            zone=StructuralZone.BOTTOM,
            span_mm=500.0,
            spacing_mm=300.0,
            pressure_kpa=50.0,
        )

        assert sm > 0

    def test_check_scantling_adequate(self):
        """Test scantling check passes for adequate thickness."""
        state = self._create_mock_state()
        calc = ScantlingCalculator(state)

        result = calc.check_scantling(
            element_id="PL-001",
            zone=StructuralZone.BOTTOM,
            actual_thickness_mm=20.0,  # Very generous for high-speed slamming
            span_mm=500.0,
        )

        assert result.is_adequate is True
        assert result.utilization < 1.0

    def test_check_scantling_inadequate(self):
        """Test scantling check fails for thin plate."""
        state = self._create_mock_state()
        calc = ScantlingCalculator(state)

        result = calc.check_scantling(
            element_id="PL-002",
            zone=StructuralZone.BOTTOM,
            actual_thickness_mm=2.0,  # Too thin
            span_mm=500.0,
        )

        assert result.is_adequate is False
        assert result.utilization > 1.0


class TestScantlingSummary:
    """Tests for ScantlingSummary dataclass."""

    def test_create_summary(self):
        """Test creating scantling summary."""
        summary = ScantlingSummary(
            total_elements=100,
            adequate_count=95,
            inadequate_count=5,
        )
        assert summary.total_elements == 100
        assert summary.adequate_count == 95

    def test_from_results(self):
        """Test creating summary from results."""
        results = [
            ScantlingResult(element_id="PL-1", zone=StructuralZone.BOTTOM,
                          utilization=0.8, is_adequate=True),
            ScantlingResult(element_id="PL-2", zone=StructuralZone.BOTTOM,
                          utilization=0.9, is_adequate=True),
            ScantlingResult(element_id="PL-3", zone=StructuralZone.SIDE,
                          utilization=1.1, is_adequate=False),
        ]

        summary = ScantlingSummary.from_results(results)

        assert summary.total_elements == 3
        assert summary.adequate_count == 2
        assert summary.inadequate_count == 1
        assert summary.max_utilization == 1.1
        assert summary.max_utilization_element == "PL-3"


# === INTEGRATION TESTS ===

class TestStructuralPipelineIntegration:
    """Integration tests for full structural pipeline."""

    def _create_mock_state(self):
        """Create mock state manager."""
        state = MagicMock()
        state.get = lambda key, default=None: {
            "hull.loa": 26.0,
            "hull.lwl": 24.0,
            "hull.beam": 6.0,
            "hull.depth": 3.0,
            "hull.draft": 1.5,
            "mission.max_speed_kts": 30,
            "hull.displacement_mt": 80,
            "hull.deadrise_deg": 20,
            "structure.bottom_plate_thickness_mm": 6.0,
            "structure.side_plate_thickness_mm": 5.0,
            "structure.deck_plate_thickness_mm": 5.0,
        }.get(key, default)
        return state

    def test_full_structural_pipeline(self):
        """Test complete structural generation pipeline."""
        from magnet.structural.grid_generator import StructuralGridGenerator
        from magnet.structural.plate_generator import PlateGenerator

        state = self._create_mock_state()

        # Generate grid
        grid_gen = StructuralGridGenerator(state)
        grid = grid_gen.generate()
        assert len(grid.frames) > 0

        # Generate plates
        plate_gen = PlateGenerator(state)
        plates = plate_gen.generate_all_plates(grid)
        assert len(plates) > 0

        # Generate stiffeners
        stiff_gen = StiffenerGenerator(state)
        stiffeners = stiff_gen.generate_all_stiffeners(grid, plates)
        assert len(stiffeners) > 0

        # Generate welds
        weld_gen = WeldGenerator(state)
        welds = weld_gen.generate_all_welds(grid, plates, stiffeners)
        assert len(welds) > 0

        # Check scantlings
        scant_calc = ScantlingCalculator(state)
        results = scant_calc.check_all_plates(plates, grid)
        summary = ScantlingSummary.from_results(results)

        assert summary.total_elements == len(plates)
        assert summary.adequate_count > 0
