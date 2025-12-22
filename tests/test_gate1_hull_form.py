"""
Gate 1 Hull Form Tests

These tests validate that the hull form system meets Gate 1 requirements:
1. Authoritative geometry is used by default
2. Visual-only is opt-in only
3. Hull type is correctly passed through
4. Catamaran generates correct topology
5. GeometryMode is tracked and reported

Module 67.2: Hull Form Authoritative Path Implementation
"""

import pytest
import math
from unittest.mock import MagicMock, patch


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def mock_state_manager():
    """Create a mock StateManager with hull parameters."""
    mock_sm = MagicMock()
    mock_sm.state = MagicMock()
    mock_sm.state.hull = MagicMock()

    # Default hull values
    mock_sm.state.hull.loa = 25.0
    mock_sm.state.hull.lwl = 23.0
    mock_sm.state.hull.beam = 6.0
    mock_sm.state.hull.draft = 1.5
    mock_sm.state.hull.depth = 3.0
    mock_sm.state.hull.cb = 0.45
    mock_sm.state.hull.cp = 0.65
    mock_sm.state.hull.cwp = 0.75
    mock_sm.state.hull.cm = 0.70
    mock_sm.state.hull.deadrise_deg = 15.0
    mock_sm.state.hull.transom_width_ratio = 0.85
    mock_sm.state.hull.bow_angle_deg = 25.0
    mock_sm.state.hull.hull_type = "hard_chine"
    mock_sm.state.hull.hull_spacing_m = 0.0

    return mock_sm


def create_test_inputs(**overrides):
    """Create GeometryInputProvider-like object with defaults."""
    defaults = {
        "loa": 25.0,
        "lwl": 23.0,
        "beam": 6.0,
        "draft": 1.5,
        "depth": 3.0,
        "cb": 0.45,
        "cp": 0.65,
        "cwp": 0.75,
        "cm": 0.70,
        "deadrise_deg": 15.0,
        "transom_width_ratio": 0.85,
        "bow_angle_deg": 25.0,
        "hull_type": "hard_chine",
        "hull_spacing": 0.0,
        "design_id": "test-design",
    }
    defaults.update(overrides)

    mock = MagicMock()
    for key, value in defaults.items():
        setattr(mock, key, value)
    mock.get_parameter = lambda path, default=None: default
    return mock


# =============================================================================
# GATE 1: AUTHORITATIVE PATH
# =============================================================================

class TestGate1AuthoritativePath:
    """Gate 1 Requirement: Authoritative geometry by default."""

    def test_hull_generator_returns_geometry(self):
        """HullGenerator produces valid geometry from HullDefinition."""
        from magnet.hull_gen.generator import HullGenerator
        from magnet.hull_gen.parameters import (
            HullDefinition,
            MainDimensions,
            FormCoefficients,
            DeadriseProfile,
            HullFeatures,
        )
        from magnet.hull_gen.enums import HullType

        definition = HullDefinition(
            hull_id="test-hull",
            hull_name="Test Hull",
            hull_type=HullType.HARD_CHINE,
            dimensions=MainDimensions(
                loa=25.0,
                lwl=23.0,
                lpp=22.5,
                beam_max=6.0,
                beam_wl=5.7,
                beam_chine=5.4,
                depth=3.0,
                draft=1.5,
                draft_fwd=1.5,
                draft_aft=1.5,
            ),
            coefficients=FormCoefficients(
                cb=0.45,
                cp=0.65,
                cm=0.70,
                cwp=0.75,
                lcb=0.52,
                lcf=0.50,
            ),
            deadrise=DeadriseProfile.warped(15.0, 17.0, 40.0),
            features=HullFeatures(
                transom_width_fraction=0.85,
                bow_flare_deg=25.0,
            ),
        )

        definition.compute_displacement()

        generator = HullGenerator()
        geometry = generator.generate(definition)

        assert geometry is not None
        assert len(geometry.sections) > 0
        assert geometry.volume > 0

    def test_adapter_builds_hull_definition(self):
        """HullGeneratorAdapter correctly builds HullDefinition."""
        from magnet.webgl.interfaces import HullGeneratorAdapter, StateGeometryAdapter

        mock_sm = MagicMock()
        mock_sm.state = MagicMock()
        mock_sm.state.hull = MagicMock()
        mock_sm.state.hull.loa = 25.0
        mock_sm.state.hull.lwl = 23.0
        mock_sm.state.hull.beam = 6.0
        mock_sm.state.hull.draft = 1.5
        mock_sm.state.hull.depth = 3.0
        mock_sm.state.hull.cb = 0.45
        mock_sm.state.hull.cp = 0.65
        mock_sm.state.hull.cwp = 0.75
        mock_sm.state.hull.cm = 0.70
        mock_sm.state.hull.deadrise_deg = 15.0
        mock_sm.state.hull.transom_width_ratio = 0.85
        mock_sm.state.hull.bow_angle_deg = 25.0
        mock_sm.state.hull.hull_type = "hard_chine"
        mock_sm.state.hull.hull_spacing_m = 0.0

        adapter = HullGeneratorAdapter(mock_sm)

        # Should NOT raise
        geom = adapter.get_hull_geometry("test-design")

        assert geom is not None
        assert len(geom.sections) > 0


class TestGate1HullType:
    """Gate 1 Requirement: Hull type passthrough."""

    def test_hull_type_mapping(self):
        """_get_hull_type maps string to enum correctly."""
        from magnet.webgl.interfaces import HullGeneratorAdapter
        from magnet.hull_gen.enums import HullType

        mock_sm = MagicMock()
        adapter = HullGeneratorAdapter(mock_sm)

        inputs = create_test_inputs(hull_type="hard_chine")
        assert adapter._get_hull_type(inputs) == HullType.HARD_CHINE

        inputs = create_test_inputs(hull_type="round_bilge")
        assert adapter._get_hull_type(inputs) == HullType.ROUND_BILGE

        inputs = create_test_inputs(hull_type="catamaran")
        assert adapter._get_hull_type(inputs) == HullType.CATAMARAN

    def test_unknown_hull_type_defaults_with_warning(self, caplog):
        """Unknown hull type produces warning and defaults to HARD_CHINE."""
        from magnet.webgl.interfaces import HullGeneratorAdapter
        from magnet.hull_gen.enums import HullType
        import logging

        mock_sm = MagicMock()
        adapter = HullGeneratorAdapter(mock_sm)

        inputs = create_test_inputs(hull_type="unknown_fantasy_type")

        with caplog.at_level(logging.WARNING):
            result = adapter._get_hull_type(inputs)

        assert result == HullType.HARD_CHINE
        assert "Unknown hull_type" in caplog.text


# =============================================================================
# GATE 1: CATAMARAN
# =============================================================================

class TestGate1Catamaran:
    """Gate 1 Requirement: Catamaran generates twin hulls."""

    def test_catamaran_generates_offset_sections(self):
        """Catamaran sections are offset from centerline."""
        from magnet.hull_gen.generator import HullGenerator
        from magnet.hull_gen.parameters import (
            HullDefinition,
            MainDimensions,
            FormCoefficients,
            DeadriseProfile,
            HullFeatures,
        )
        from magnet.hull_gen.enums import HullType

        definition = HullDefinition(
            hull_id="test-cat",
            hull_name="Test Catamaran",
            hull_type=HullType.CATAMARAN,
            dimensions=MainDimensions(
                loa=30.0,
                lwl=28.0,
                lpp=27.0,
                beam_max=12.0,
                beam_wl=11.0,
                beam_chine=10.0,
                depth=3.5,
                draft=1.8,
            ),
            coefficients=FormCoefficients(
                cb=0.45,
                cp=0.65,
                cm=0.70,
                cwp=0.75,
                lcb=0.52,
                lcf=0.50,
            ),
            deadrise=DeadriseProfile.warped(15.0, 17.0, 40.0),
            features=HullFeatures(
                transom_width_fraction=0.85,
                bow_flare_deg=25.0,
                hull_spacing=8.0,
                num_hulls=2,
            ),
        )

        generator = HullGenerator()
        geometry = generator.generate(definition)

        # Check that sections exist
        assert len(geometry.sections) > 0

        # Check that section points are offset (y > 0 for port demihull)
        for section in geometry.sections:
            if section.points:
                y_values = [pt.position.y for pt in section.points]
                # All points should be on port side (y > 0)
                assert all(y >= 0 for y in y_values), f"Section at {section.station} has starboard points"
                # Keel should be at offset, not centerline
                min_y = min(y_values)
                assert min_y > 2.0, f"Demihull keel at y={min_y} should be offset from centerline"

    def test_catamaran_default_spacing(self):
        """Catamaran with no spacing uses default (LOA * 0.25)."""
        from magnet.hull_gen.generator import HullGenerator
        from magnet.hull_gen.parameters import (
            HullDefinition,
            MainDimensions,
            FormCoefficients,
            DeadriseProfile,
            HullFeatures,
        )
        from magnet.hull_gen.enums import HullType

        definition = HullDefinition(
            hull_id="test-cat-default",
            hull_name="Test Catamaran Default Spacing",
            hull_type=HullType.CATAMARAN,
            dimensions=MainDimensions(
                loa=25.0,
                lwl=23.0,
                lpp=22.5,
                beam_max=10.0,
                beam_wl=9.5,
                beam_chine=9.0,
                depth=3.0,
                draft=1.5,
            ),
            coefficients=FormCoefficients.for_hull_type(HullType.CATAMARAN),
            deadrise=DeadriseProfile.constant(15.0),
            features=HullFeatures(
                hull_spacing=0.0,  # No explicit spacing
                num_hulls=2,
            ),
        )

        generator = HullGenerator()
        geometry = generator.generate(definition)

        # Should still generate valid geometry
        assert len(geometry.sections) > 0

        # Sections should be offset (default spacing = lwl * 0.25)
        expected_offset = 23.0 * 0.25 / 2  # ~2.875
        for section in geometry.sections:
            if section.points:
                keel_y = section.points[0].position.y
                assert keel_y > 2.0, f"Keel at y={keel_y} should be at ~{expected_offset}"


# =============================================================================
# GATE 1: GEOMETRY MODE
# =============================================================================

class TestGate1GeometryMode:
    """Gate 1 Requirement: GeometryMode tracking."""

    def test_geometry_mode_enum_exists(self):
        """GeometryMode enum has correct values."""
        from magnet.webgl.schema import GeometryMode

        assert hasattr(GeometryMode, "AUTHORITATIVE")
        assert hasattr(GeometryMode, "VISUAL_ONLY")
        assert GeometryMode.AUTHORITATIVE.value == "authoritative"
        assert GeometryMode.VISUAL_ONLY.value == "visual_only"


# =============================================================================
# GATE 1: MESH QUALITY
# =============================================================================

class TestGate1MeshQuality:
    """Gate 1 Requirement: Mesh integrity."""

    def test_hull_generator_no_nan_values(self):
        """Generated geometry has no NaN values."""
        from magnet.hull_gen.generator import HullGenerator
        from magnet.hull_gen.parameters import (
            HullDefinition,
            MainDimensions,
            FormCoefficients,
            DeadriseProfile,
        )
        from magnet.hull_gen.enums import HullType

        definition = HullDefinition(
            hull_id="test-nan",
            hull_name="Test NaN Check",
            hull_type=HullType.HARD_CHINE,
            dimensions=MainDimensions(
                loa=25.0,
                lwl=23.0,
                lpp=22.5,
                beam_max=6.0,
                beam_wl=5.7,
                beam_chine=5.4,
                depth=3.0,
                draft=1.5,
            ),
            coefficients=FormCoefficients.for_hull_type(HullType.HARD_CHINE),
            deadrise=DeadriseProfile.warped(15.0, 17.0, 40.0),
        )

        generator = HullGenerator()
        geometry = generator.generate(definition)

        # Check all section points for NaN
        for section in geometry.sections:
            for pt in section.points:
                pos = pt.position
                assert not math.isnan(pos.x), f"NaN in x at section {section.station}"
                assert not math.isnan(pos.y), f"NaN in y at section {section.station}"
                assert not math.isnan(pos.z), f"NaN in z at section {section.station}"


# =============================================================================
# GATE 1: DETERMINISM
# =============================================================================

class TestGate1Determinism:
    """Gate 1 Requirement: Deterministic generation."""

    def test_monohull_deterministic(self):
        """Same inputs produce identical geometry."""
        from magnet.hull_gen.generator import HullGenerator
        from magnet.hull_gen.parameters import (
            HullDefinition,
            MainDimensions,
            FormCoefficients,
            DeadriseProfile,
        )
        from magnet.hull_gen.enums import HullType

        def create_definition():
            return HullDefinition(
                hull_id="test-det",
                hull_name="Test Determinism",
                hull_type=HullType.HARD_CHINE,
                dimensions=MainDimensions(
                    loa=25.0,
                    lwl=23.0,
                    lpp=22.5,
                    beam_max=6.0,
                    beam_wl=5.7,
                    beam_chine=5.4,
                    depth=3.0,
                    draft=1.5,
                ),
                coefficients=FormCoefficients.for_hull_type(HullType.HARD_CHINE),
                deadrise=DeadriseProfile.warped(15.0, 17.0, 40.0),
            )

        generator = HullGenerator()
        geom1 = generator.generate(create_definition())
        geom2 = generator.generate(create_definition())

        # Same number of sections
        assert len(geom1.sections) == len(geom2.sections)

        # Same points at each section
        for s1, s2 in zip(geom1.sections, geom2.sections):
            assert len(s1.points) == len(s2.points)
            for p1, p2 in zip(s1.points, s2.points):
                assert p1.position.x == p2.position.x
                assert p1.position.y == p2.position.y
                assert p1.position.z == p2.position.z


# =============================================================================
# GATE 1: REGRESSION
# =============================================================================

class TestGate1Regression:
    """Regression tests for fixed bugs."""

    def test_adapter_signature_regression(self):
        """Ensure adapter doesn't revert to kwargs signature."""
        from magnet.webgl.interfaces import HullGeneratorAdapter

        mock_sm = MagicMock()
        mock_sm.state = MagicMock()
        mock_sm.state.hull = MagicMock()
        mock_sm.state.hull.loa = 25.0
        mock_sm.state.hull.lwl = 23.0
        mock_sm.state.hull.beam = 6.0
        mock_sm.state.hull.draft = 1.5
        mock_sm.state.hull.depth = 3.0
        mock_sm.state.hull.cb = 0.45
        mock_sm.state.hull.cp = 0.65
        mock_sm.state.hull.cwp = 0.75
        mock_sm.state.hull.cm = 0.70
        mock_sm.state.hull.deadrise_deg = 15.0
        mock_sm.state.hull.transom_width_ratio = 0.85
        mock_sm.state.hull.bow_angle_deg = 25.0
        mock_sm.state.hull.hull_type = "hard_chine"
        mock_sm.state.hull.hull_spacing_m = 0.0

        adapter = HullGeneratorAdapter(mock_sm)

        with patch('magnet.hull_gen.generator.HullGenerator') as MockGenerator:
            mock_instance = MagicMock()
            MockGenerator.return_value = mock_instance
            mock_geom = MagicMock()
            mock_geom.sections = []
            mock_geom.keel_profile = []
            mock_geom.stem_profile = []
            mock_geom.chine_curve = []
            mock_geom.transom_outline = []
            mock_geom.volume = 100.0
            mock_geom.wetted_surface = 50.0
            mock_geom.waterplane_area = 30.0
            mock_instance.generate.return_value = mock_geom

            adapter.get_hull_geometry("test")

            # Verify generate() was called with HullDefinition, not kwargs
            mock_instance.generate.assert_called_once()
            args, kwargs = mock_instance.generate.call_args
            assert len(args) == 1, "generate() should be called with single positional arg"
            assert hasattr(args[0], 'hull_id'), "Argument should be HullDefinition"
            assert kwargs == {}, "generate() should not receive kwargs"

    def test_cache_key_includes_hull_type(self):
        """Cache key includes hull_type to prevent stale geometry."""
        from magnet.webgl.interfaces import HullGeneratorAdapter, StateGeometryAdapter

        mock_sm = MagicMock()
        adapter = HullGeneratorAdapter(mock_sm)

        inputs1 = create_test_inputs(hull_type="hard_chine")
        inputs2 = create_test_inputs(hull_type="round_bilge")

        key1 = adapter._build_cache_key("design-1", inputs1)
        key2 = adapter._build_cache_key("design-1", inputs2)

        # Different hull_type should produce different cache keys
        assert key1 != key2, "Cache key should include hull_type"

    def test_cache_key_includes_hull_spacing(self):
        """Cache key includes hull_spacing for catamarans."""
        from magnet.webgl.interfaces import HullGeneratorAdapter

        mock_sm = MagicMock()
        adapter = HullGeneratorAdapter(mock_sm)

        inputs1 = create_test_inputs(hull_spacing=6.0)
        inputs2 = create_test_inputs(hull_spacing=8.0)

        key1 = adapter._build_cache_key("design-1", inputs1)
        key2 = adapter._build_cache_key("design-1", inputs2)

        # Different hull_spacing should produce different cache keys
        assert key1 != key2, "Cache key should include hull_spacing"
