"""
tests/unit/test_hull_gen.py - Tests for hull generation module.

BRAVO OWNS THIS FILE.

Tests for Module 16-20 v1.0 - Hull Form Generation.
"""

import pytest
import math
from magnet.hull_gen import (
    HullType,
    ChineType,
    StemProfile,
    SternProfile,
    TransomType,
    KeelType,
    MainDimensions,
    FormCoefficients,
    DeadriseProfile,
    HullFeatures,
    HullDefinition,
    Point3D,
    SectionPoint,
    HullSection,
    Waterline,
    HullGeometry,
    ParentHullLibrary,
    HullGenerator,
    GeneratorConfig,
    generate_hull_from_parameters,
)


class TestEnums:
    """Tests for hull generation enums."""

    def test_hull_type_values(self):
        """Test HullType enum values."""
        assert HullType.DEEP_V_PLANING.value == "deep_v_planing"
        assert HullType.SEMI_DISPLACEMENT.value == "semi_displacement"
        assert HullType.ROUND_BILGE.value == "round_bilge"
        assert HullType.HARD_CHINE.value == "hard_chine"
        assert HullType.CATAMARAN.value == "catamaran"

    def test_chine_type_values(self):
        """Test ChineType enum values."""
        assert ChineType.NONE.value == "none"
        assert ChineType.SINGLE.value == "single"
        assert ChineType.HARD.value == "hard"

    def test_stem_profile_values(self):
        """Test StemProfile enum values."""
        assert StemProfile.VERTICAL.value == "vertical"
        assert StemProfile.RAKED.value == "raked"
        assert StemProfile.WAVE_PIERCING.value == "wave_piercing"


class TestMainDimensions:
    """Tests for MainDimensions dataclass."""

    def test_create_dimensions(self):
        """Test creating dimensions."""
        dims = MainDimensions(
            loa=26.0,
            lwl=24.0,
            beam_max=6.2,
            depth=3.2,
            draft=1.4,
        )
        assert dims.loa == 26.0
        assert dims.lwl == 24.0
        assert dims.beam_max == 6.2
        assert dims.draft == 1.4

    def test_validate_valid_dimensions(self):
        """Test validation passes for valid dimensions."""
        dims = MainDimensions(
            loa=26.0,
            lwl=24.0,
            beam_max=6.0,
            depth=3.2,
            draft=1.4,
        )
        errors = dims.validate()
        assert len(errors) == 0

    def test_validate_invalid_lwl(self):
        """Test validation fails for invalid LWL."""
        dims = MainDimensions(lwl=0, beam_max=6.0, draft=1.4)
        errors = dims.validate()
        assert any("LWL" in e for e in errors)

    def test_validate_loa_less_than_lwl(self):
        """Test validation fails if LOA < LWL."""
        dims = MainDimensions(loa=20.0, lwl=24.0, beam_max=6.0, depth=3.0, draft=1.4)
        errors = dims.validate()
        assert any("LOA" in e for e in errors)

    def test_to_dict(self):
        """Test dictionary serialization."""
        dims = MainDimensions(loa=26.0, lwl=24.0, beam_max=6.0, draft=1.4)
        data = dims.to_dict()
        assert data["loa"] == 26.0
        assert data["lwl"] == 24.0

    def test_from_dict(self):
        """Test dictionary deserialization."""
        data = {"loa": 26.0, "lwl": 24.0, "beam_max": 6.0, "draft": 1.4}
        dims = MainDimensions.from_dict(data)
        assert dims.loa == 26.0
        assert dims.lwl == 24.0


class TestFormCoefficients:
    """Tests for FormCoefficients dataclass."""

    def test_create_coefficients(self):
        """Test creating coefficients."""
        coeffs = FormCoefficients(cb=0.45, cp=0.62, cm=0.72, cwp=0.75)
        assert coeffs.cb == 0.45
        assert coeffs.cp == 0.62

    def test_for_hull_type_deep_v(self):
        """Test generating coefficients for deep-V hull."""
        coeffs = FormCoefficients.for_hull_type(HullType.DEEP_V_PLANING)
        assert 0.30 <= coeffs.cb <= 0.45
        assert coeffs.lcb < 0.5  # Forward LCB for planing

    def test_for_hull_type_round_bilge(self):
        """Test generating coefficients for round bilge hull."""
        coeffs = FormCoefficients.for_hull_type(HullType.ROUND_BILGE)
        assert coeffs.cb > 0.5  # Fuller hull
        assert coeffs.cm > 0.75

    def test_validate_valid_coefficients(self):
        """Test validation passes for valid coefficients."""
        coeffs = FormCoefficients(cb=0.45, cp=0.62, cm=0.72, cwp=0.75)
        errors = coeffs.validate()
        assert len(errors) == 0

    def test_validate_cb_out_of_range(self):
        """Test validation fails for Cb out of range."""
        coeffs = FormCoefficients(cb=0.1, cp=0.62, cm=0.72)
        errors = coeffs.validate()
        assert any("Cb" in e for e in errors)


class TestDeadriseProfile:
    """Tests for DeadriseProfile dataclass."""

    def test_constant_profile(self):
        """Test constant deadrise profile."""
        profile = DeadriseProfile.constant(20.0)
        assert profile.deadrise_transom == 20.0
        assert profile.deadrise_midship == 20.0
        assert profile.deadrise_bow == 20.0

    def test_warped_profile(self):
        """Test warped deadrise profile."""
        profile = DeadriseProfile.warped(18.0, 20.0, 45.0)
        assert profile.deadrise_transom == 18.0
        assert profile.deadrise_midship == 20.0
        assert profile.deadrise_bow == 45.0

    def test_get_deadrise_at_transom(self):
        """Test getting deadrise at transom."""
        profile = DeadriseProfile.warped(18.0, 20.0, 45.0)
        angle = profile.get_deadrise_at(0.0)
        assert angle == 18.0

    def test_get_deadrise_at_midship(self):
        """Test getting deadrise at midship."""
        profile = DeadriseProfile.warped(18.0, 20.0, 45.0)
        angle = profile.get_deadrise_at(0.5)
        assert angle == 20.0

    def test_get_deadrise_interpolated(self):
        """Test interpolated deadrise."""
        profile = DeadriseProfile.warped(18.0, 20.0, 45.0)
        angle = profile.get_deadrise_at(0.25)
        assert 18.0 < angle < 20.0


class TestHullDefinition:
    """Tests for HullDefinition dataclass."""

    def test_create_definition(self):
        """Test creating hull definition."""
        defn = HullDefinition(
            hull_id="TEST-001",
            hull_name="Test Hull",
            hull_type=HullType.HARD_CHINE,
        )
        assert defn.hull_id == "TEST-001"
        assert defn.hull_type == HullType.HARD_CHINE

    def test_compute_displacement(self):
        """Test displacement computation."""
        defn = HullDefinition(
            hull_type=HullType.HARD_CHINE,
            dimensions=MainDimensions(lwl=24.0, beam_wl=5.8, draft=1.4),
            coefficients=FormCoefficients(cb=0.38),
        )
        disp = defn.compute_displacement()
        expected = 0.38 * 24.0 * 5.8 * 1.4
        assert abs(disp - expected) < 0.01

    def test_validate(self):
        """Test definition validation."""
        defn = HullDefinition(
            dimensions=MainDimensions(loa=26.0, lwl=24.0, beam_max=6.0, depth=3.0, draft=1.4),
            coefficients=FormCoefficients(cb=0.38, cp=0.58, cm=0.66, cwp=0.72),
        )
        errors = defn.validate()
        assert len(errors) == 0

    def test_to_dict(self):
        """Test dictionary serialization."""
        defn = HullDefinition(hull_id="TEST-001", hull_type=HullType.DEEP_V_PLANING)
        data = defn.to_dict()
        assert data["hull_id"] == "TEST-001"
        assert data["hull_type"] == "deep_v_planing"


class TestPoint3D:
    """Tests for Point3D dataclass."""

    def test_create_point(self):
        """Test creating a point."""
        p = Point3D(x=10.0, y=2.5, z=-1.4)
        assert p.x == 10.0
        assert p.y == 2.5
        assert p.z == -1.4

    def test_add_points(self):
        """Test adding points."""
        p1 = Point3D(1, 2, 3)
        p2 = Point3D(4, 5, 6)
        result = p1 + p2
        assert result.x == 5
        assert result.y == 7
        assert result.z == 9

    def test_subtract_points(self):
        """Test subtracting points."""
        p1 = Point3D(4, 5, 6)
        p2 = Point3D(1, 2, 3)
        result = p1 - p2
        assert result.x == 3
        assert result.y == 3
        assert result.z == 3

    def test_scalar_multiply(self):
        """Test scalar multiplication."""
        p = Point3D(1, 2, 3)
        result = p * 2
        assert result.x == 2
        assert result.y == 4
        assert result.z == 6

    def test_distance_to(self):
        """Test distance calculation."""
        p1 = Point3D(0, 0, 0)
        p2 = Point3D(3, 4, 0)
        dist = p1.distance_to(p2)
        assert abs(dist - 5.0) < 0.001

    def test_length(self):
        """Test vector length."""
        p = Point3D(3, 4, 0)
        assert abs(p.length() - 5.0) < 0.001

    def test_normalize(self):
        """Test vector normalization."""
        p = Point3D(3, 4, 0)
        n = p.normalize()
        assert abs(n.length() - 1.0) < 0.001

    def test_dot_product(self):
        """Test dot product."""
        p1 = Point3D(1, 0, 0)
        p2 = Point3D(0, 1, 0)
        assert p1.dot(p2) == 0

    def test_cross_product(self):
        """Test cross product."""
        p1 = Point3D(1, 0, 0)
        p2 = Point3D(0, 1, 0)
        result = p1.cross(p2)
        assert result.z == 1


class TestHullSection:
    """Tests for HullSection dataclass."""

    def test_create_section(self):
        """Test creating a section."""
        section = HullSection(station=0.5, x_position=12.0)
        assert section.station == 0.5
        assert section.x_position == 12.0

    def test_compute_area(self):
        """Test section area computation."""
        section = HullSection()
        # Create simple rectangular section
        section.points = [
            SectionPoint(position=Point3D(0, 0, -1)),
            SectionPoint(position=Point3D(0, 2, -1)),
            SectionPoint(position=Point3D(0, 2, 0)),
            SectionPoint(position=Point3D(0, 0, 0)),
        ]
        area = section.compute_area(0)
        # Full section = 2 * half = 2 * 2 = 4
        assert area > 0


class TestParentHullLibrary:
    """Tests for ParentHullLibrary."""

    def test_defaults_initialized(self):
        """Test default hulls are initialized."""
        hulls = ParentHullLibrary.list_all()
        assert len(hulls) > 0

    def test_get_patrol_hull(self):
        """Test getting patrol boat hull."""
        hull = ParentHullLibrary.get("PATROL-25M-V")
        assert hull is not None
        assert hull.hull_type == HullType.DEEP_V_PLANING

    def test_get_by_type(self):
        """Test getting hulls by type."""
        deep_v_hulls = ParentHullLibrary.get_by_type(HullType.DEEP_V_PLANING)
        assert len(deep_v_hulls) >= 1

    def test_get_nonexistent(self):
        """Test getting non-existent hull returns None."""
        hull = ParentHullLibrary.get("NONEXISTENT")
        assert hull is None


class TestHullGenerator:
    """Tests for HullGenerator."""

    def test_create_generator(self):
        """Test creating generator with default config."""
        generator = HullGenerator()
        assert generator.config.num_sections == 21

    def test_create_with_custom_config(self):
        """Test creating generator with custom config."""
        config = GeneratorConfig(num_sections=11, points_per_section=15)
        generator = HullGenerator(config)
        assert generator.config.num_sections == 11

    def test_generate_from_definition(self):
        """Test generating geometry from definition."""
        defn = HullDefinition(
            hull_id="TEST-GEN",
            hull_type=HullType.HARD_CHINE,
            dimensions=MainDimensions(
                loa=26.0, lwl=24.0, beam_max=6.0, beam_wl=5.8, depth=3.0, draft=1.4
            ),
            coefficients=FormCoefficients.for_hull_type(HullType.HARD_CHINE),
            deadrise=DeadriseProfile.warped(18.0, 20.0, 45.0),
        )
        defn.compute_displacement()

        generator = HullGenerator()
        geometry = generator.generate(defn)

        assert geometry.hull_id == "TEST-GEN"
        assert len(geometry.sections) > 0
        assert geometry.volume > 0

    def test_generate_has_sections(self):
        """Test generated geometry has sections."""
        defn = HullDefinition(
            hull_type=HullType.DEEP_V_PLANING,
            dimensions=MainDimensions(lwl=24.0, beam_max=6.0, beam_wl=5.8, depth=3.0, draft=1.4),
            coefficients=FormCoefficients.for_hull_type(HullType.DEEP_V_PLANING),
        )

        generator = HullGenerator(GeneratorConfig(num_sections=11))
        geometry = generator.generate(defn)

        assert len(geometry.sections) == 11

    def test_generate_has_waterlines(self):
        """Test generated geometry has waterlines."""
        defn = HullDefinition(
            hull_type=HullType.HARD_CHINE,
            dimensions=MainDimensions(lwl=24.0, beam_max=6.0, beam_wl=5.8, depth=3.0, draft=1.4),
            coefficients=FormCoefficients.for_hull_type(HullType.HARD_CHINE),
        )

        generator = HullGenerator(GeneratorConfig(num_waterlines=5))
        geometry = generator.generate(defn)

        assert len(geometry.waterlines) > 0


class TestConvenienceFunction:
    """Tests for generate_hull_from_parameters function."""

    def test_generate_simple_hull(self):
        """Test generating hull with convenience function."""
        geometry = generate_hull_from_parameters(
            lwl=24.0,
            beam=6.0,
            draft=1.4,
            hull_type=HullType.HARD_CHINE,
            deadrise_deg=18.0,
        )

        assert geometry is not None
        assert len(geometry.sections) > 0
        assert geometry.volume > 0

    def test_generate_different_hull_types(self):
        """Test generating different hull types."""
        for hull_type in [HullType.DEEP_V_PLANING, HullType.ROUND_BILGE, HullType.HARD_CHINE]:
            geometry = generate_hull_from_parameters(
                lwl=20.0,
                beam=5.0,
                draft=1.2,
                hull_type=hull_type,
            )
            assert geometry is not None
            assert geometry.volume > 0


class TestHullGeometry:
    """Tests for HullGeometry dataclass."""

    def test_compute_volume(self):
        """Test volume computation from sections."""
        geometry = HullGeometry()

        # Create simple sections with known areas
        for i in range(5):
            section = HullSection(
                station=i / 4,
                x_position=i * 5.0,
                area=10.0,  # 10 m^2 each
            )
            geometry.sections.append(section)

        volume = geometry.compute_volume()
        # Trapezoidal: 4 intervals * 5m spacing * avg 10 m^2 = 200 m^3
        assert volume > 0

    def test_to_dict(self):
        """Test geometry serialization."""
        geometry = HullGeometry(hull_id="TEST")
        geometry.volume = 100.0
        geometry.wetted_surface = 200.0

        data = geometry.to_dict()
        assert data["hull_id"] == "TEST"
        assert data["volume"] == 100.0

