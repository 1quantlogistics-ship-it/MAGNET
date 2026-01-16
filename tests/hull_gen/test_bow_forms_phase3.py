"""
tests/hull_gen/test_bow_forms_phase3.py - Phase 3 bow form tests.

Tests the expanded bow form capabilities:
- Wedge bow (two planar panels)
- Axe bow (vertical stem, fine entry)
- Faceted bow (N panels per side)
- Wave-piercing bow (fine entry, tumblehome)
- Traditional bow (backward compatibility)
"""

import pytest
import math
from magnet.hull_gen.geometry import EdgeType, SectionPoint, Point3D, HullSection
from magnet.hull_gen.generator import HullGenerator, GeneratorConfig
from magnet.hull_gen.bow_generator import BowGenerator, BowGeometry, BowPanelEdge
from magnet.hull_gen.enums import HullType, ChineType, BowStyle, StemProfile
from magnet.hull_gen.parameters import (
    HullDefinition, MainDimensions, FormCoefficients, 
    DeadriseProfile, HullFeatures, BowConfig
)


def _create_definition(bow_style: BowStyle = BowStyle.TRADITIONAL) -> HullDefinition:
    """Create test hull definition with given bow style."""
    return HullDefinition(
        hull_id="TEST-PHASE3",
        hull_name="Test Phase 3 Hull",
        hull_type=HullType.HARD_CHINE,
        dimensions=MainDimensions(
            loa=20.0,
            lwl=19.0,
            lpp=18.5,
            beam_max=5.0,
            beam_wl=4.8,
            beam_chine=4.5,
            depth=3.0,
            draft=1.5,
        ),
        coefficients=FormCoefficients(
            cb=0.45,
            cp=0.65,
            cm=0.80,
            cwp=0.75,
            lcb=0.52,
        ),
        deadrise=DeadriseProfile.warped(18.0, 20.0, 35.0),
        features=HullFeatures(
            bow_style=bow_style,
            chine_type=ChineType.HARD,
        ),
    )


def _create_definition_with_features(features: HullFeatures) -> HullDefinition:
    """Create test hull definition with given features."""
    return HullDefinition(
        hull_id="TEST-PHASE3",
        hull_name="Test Phase 3 Hull",
        hull_type=HullType.HARD_CHINE,
        dimensions=MainDimensions(
            loa=20.0,
            lwl=19.0,
            lpp=18.5,
            beam_max=5.0,
            beam_wl=4.8,
            beam_chine=4.5,
            depth=3.0,
            draft=1.5,
        ),
        coefficients=FormCoefficients(
            cb=0.45,
            cp=0.65,
            cm=0.80,
            cwp=0.75,
            lcb=0.52,
        ),
        deadrise=DeadriseProfile.warped(18.0, 20.0, 35.0),
        features=features,
    )


class TestBowStyleEnum:
    """BowStyle enum tests."""
    
    def test_bow_styles_exist(self):
        """All bow styles should be defined."""
        assert BowStyle.TRADITIONAL.value == "traditional"
        assert BowStyle.WEDGE.value == "wedge"
        assert BowStyle.AXE.value == "axe"
        assert BowStyle.FACETED.value == "faceted"
        assert BowStyle.WAVE_PIERCING.value == "wave_piercing"


class TestBowConfigDataclass:
    """BowConfig dataclass tests."""
    
    def test_default_config(self):
        """BowConfig should have sensible defaults."""
        config = BowConfig()
        assert config.style == BowStyle.TRADITIONAL
        assert config.facet_count == 2
        assert config.half_angle_deg == 25.0
        assert config.region_length == 0.20
    
    def test_wedge_is_angular(self):
        """Wedge bow should be classified as angular."""
        config = BowConfig(style=BowStyle.WEDGE)
        assert config.is_angular() is True
    
    def test_axe_is_angular(self):
        """Axe bow should be classified as angular."""
        config = BowConfig(style=BowStyle.AXE)
        assert config.is_angular() is True
    
    def test_faceted_is_angular(self):
        """Faceted bow should be classified as angular."""
        config = BowConfig(style=BowStyle.FACETED)
        assert config.is_angular() is True
    
    def test_traditional_not_angular(self):
        """Traditional bow should not be classified as angular."""
        config = BowConfig(style=BowStyle.TRADITIONAL)
        assert config.is_angular() is False
    
    def test_wave_piercing_not_angular(self):
        """Wave-piercing bow should not be classified as angular."""
        config = BowConfig(style=BowStyle.WAVE_PIERCING)
        assert config.is_angular() is False
    
    def test_to_dict_from_dict(self):
        """BowConfig should serialize and deserialize correctly."""
        config = BowConfig(
            style=BowStyle.WEDGE,
            facet_count=3,
            half_angle_deg=22.0,
        )
        d = config.to_dict()
        restored = BowConfig.from_dict(d)
        assert restored.style == config.style
        assert restored.facet_count == config.facet_count
        assert restored.half_angle_deg == config.half_angle_deg


class TestHullFeaturesGetBowConfig:
    """Test HullFeatures.get_bow_config() method."""
    
    def test_traditional_bow_config(self):
        """Traditional bow style should return traditional config."""
        features = HullFeatures(bow_style=BowStyle.TRADITIONAL)
        config = features.get_bow_config()
        assert config.style == BowStyle.TRADITIONAL
    
    def test_wedge_bow_config(self):
        """Wedge bow style should return appropriate config."""
        features = HullFeatures(bow_style=BowStyle.WEDGE)
        config = features.get_bow_config()
        assert config.style == BowStyle.WEDGE
        assert config.facet_count == 1  # Single panel per side = wedge
        assert config.planarity == 1.0  # Fully planar
    
    def test_axe_bow_config(self):
        """Axe bow style should return appropriate config."""
        features = HullFeatures(bow_style=BowStyle.AXE)
        config = features.get_bow_config()
        assert config.style == BowStyle.AXE
        assert config.stem_profile == StemProfile.VERTICAL
        assert config.stem_rake_deg == 0.0
    
    def test_faceted_bow_config(self):
        """Faceted bow style should return appropriate config."""
        features = HullFeatures(bow_style=BowStyle.FACETED, bow_facet_count=4)
        config = features.get_bow_config()
        assert config.style == BowStyle.FACETED
        assert config.facet_count == 4
    
    def test_wave_piercing_bow_config(self):
        """Wave-piercing bow style should return appropriate config."""
        features = HullFeatures(bow_style=BowStyle.WAVE_PIERCING)
        config = features.get_bow_config()
        assert config.style == BowStyle.WAVE_PIERCING
        assert config.half_angle_deg < 20  # Fine entry
        assert config.stem_rake_deg < 0  # Forward rake
    
    def test_explicit_config_overrides_style(self):
        """Explicit bow_config should override bow_style defaults."""
        explicit = BowConfig(style=BowStyle.FACETED, facet_count=5)
        features = HullFeatures(bow_style=BowStyle.WEDGE, bow_config=explicit)
        config = features.get_bow_config()
        assert config.style == BowStyle.FACETED
        assert config.facet_count == 5


class TestBowGenerator:
    """BowGenerator class tests."""
    
    def test_generator_creates_bow_geometry(self):
        """BowGenerator should create BowGeometry object."""
        definition = _create_definition(BowStyle.WEDGE)
        config = BowConfig(style=BowStyle.WEDGE)
        generator = BowGenerator()
        
        bow = generator.generate(definition, config)
        
        assert isinstance(bow, BowGeometry)
        assert len(bow.sections) > 0
        assert len(bow.stem_curve) > 0
    
    def test_traditional_bow_no_panel_edges(self):
        """Traditional bow should have no panel edges."""
        definition = _create_definition(BowStyle.TRADITIONAL)
        config = BowConfig(style=BowStyle.TRADITIONAL)
        generator = BowGenerator()
        
        bow = generator.generate(definition, config)
        
        assert len(bow.panel_edges) == 0


class TestWedgeBow:
    """Wedge bow generation tests."""
    
    def test_wedge_generates_stem_curve(self):
        """Wedge bow should generate stem curve."""
        definition = _create_definition(BowStyle.WEDGE)
        config = BowConfig(style=BowStyle.WEDGE)
        generator = BowGenerator()
        
        bow = generator.generate(definition, config)
        
        assert len(bow.stem_curve) >= 2
    
    def test_wedge_has_panel_edges(self):
        """Wedge bow should have panel edges."""
        definition = _create_definition(BowStyle.WEDGE)
        config = BowConfig(style=BowStyle.WEDGE)
        generator = BowGenerator()
        
        bow = generator.generate(definition, config)
        
        assert len(bow.panel_edges) > 0
    
    def test_wedge_panel_edges_are_hard(self):
        """Wedge bow panel edges should be hard."""
        definition = _create_definition(BowStyle.WEDGE)
        config = BowConfig(style=BowStyle.WEDGE)
        generator = BowGenerator()
        
        bow = generator.generate(definition, config)
        
        for edge in bow.panel_edges:
            assert edge.is_hard, f"Edge {edge.feature_id} should be hard"
    
    def test_wedge_stem_edge_exists(self):
        """Wedge bow should have a stem edge."""
        definition = _create_definition(BowStyle.WEDGE)
        config = BowConfig(style=BowStyle.WEDGE)
        generator = BowGenerator()
        
        bow = generator.generate(definition, config)
        
        stem_edges = [e for e in bow.panel_edges if "stem" in e.feature_id]
        assert len(stem_edges) > 0
    
    def test_wedge_sections_narrow_at_stem(self):
        """Wedge sections should be very narrow at stem."""
        definition = _create_definition(BowStyle.WEDGE)
        config = BowConfig(style=BowStyle.WEDGE)
        generator = BowGenerator()
        
        bow = generator.generate(definition, config)
        
        # First section (stem) should be very narrow
        stem_section = bow.sections[0]
        max_y = max(p.position.y for p in stem_section.points) if stem_section.points else 0
        assert max_y < 0.5, f"Stem should be narrow, got max_y={max_y}"


class TestAxeBow:
    """Axe bow generation tests."""
    
    def test_axe_has_vertical_stem(self):
        """Axe bow should have vertical stem profile."""
        definition = _create_definition(BowStyle.AXE)
        config = BowConfig(style=BowStyle.AXE, stem_profile=StemProfile.VERTICAL)
        generator = BowGenerator()
        
        bow = generator.generate(definition, config)
        
        # Stem curve X should be constant (vertical)
        x_values = [p.x for p in bow.stem_curve]
        x_range = max(x_values) - min(x_values)
        assert x_range < 0.5, f"Axe stem should be vertical, got x_range={x_range}"
    
    def test_axe_has_hard_stem_edge(self):
        """Axe bow should have hard stem edge."""
        definition = _create_definition(BowStyle.AXE)
        config = BowConfig(style=BowStyle.AXE)
        generator = BowGenerator()
        
        bow = generator.generate(definition, config)
        
        stem_edges = [e for e in bow.panel_edges if "stem" in e.feature_id or "axe" in e.feature_id]
        assert len(stem_edges) > 0
        assert all(e.is_hard for e in stem_edges)
    
    def test_axe_has_fine_entry(self):
        """Axe bow should have fine entry (gradual beam growth)."""
        definition = _create_definition(BowStyle.AXE)
        config = BowConfig(style=BowStyle.AXE)
        generator = BowGenerator()
        
        bow = generator.generate(definition, config)
        
        # Waterline entry should show gradual beam growth
        waterline = bow.waterline_entry
        if len(waterline) > 2:
            # Check that beam grows monotonically
            y_values = [p.y for p in waterline]
            for i in range(1, len(y_values)):
                assert y_values[i] >= y_values[i-1] - 0.01, "Beam should grow monotonically"


class TestFacetedBow:
    """Faceted bow generation tests."""
    
    def test_faceted_generates_n_panel_edges(self):
        """Faceted bow should generate N panel edges."""
        definition = _create_definition(BowStyle.FACETED)
        config = BowConfig(style=BowStyle.FACETED, facet_count=4)
        generator = BowGenerator()
        
        bow = generator.generate(definition, config)
        
        facet_edges = [e for e in bow.panel_edges if "facet" in e.feature_id]
        assert len(facet_edges) == 4
    
    def test_faceted_edges_are_hard(self):
        """Faceted bow panel edges should be hard."""
        definition = _create_definition(BowStyle.FACETED)
        config = BowConfig(style=BowStyle.FACETED, facet_count=3)
        generator = BowGenerator()
        
        bow = generator.generate(definition, config)
        
        for edge in bow.panel_edges:
            assert edge.is_hard, f"Edge {edge.feature_id} should be hard"
    
    def test_faceted_sections_have_hard_points(self):
        """Faceted sections should have hard edge points at panel boundaries."""
        definition = _create_definition(BowStyle.FACETED)
        config = BowConfig(style=BowStyle.FACETED, facet_count=3)
        generator = BowGenerator()
        
        bow = generator.generate(definition, config)
        
        # Check mid-bow section for hard points
        if len(bow.sections) > 2:
            mid_section = bow.sections[len(bow.sections) // 2]
            hard_points = [p for p in mid_section.points if p.edge_type == EdgeType.HARD]
            # Should have hard points at facet boundaries (plus keel)
            assert len(hard_points) >= 2


class TestWavePiercingBow:
    """Wave-piercing bow generation tests."""
    
    def test_wave_piercing_has_stem_curve(self):
        """Wave-piercing bow should have stem curve."""
        definition = _create_definition(BowStyle.WAVE_PIERCING)
        config = BowConfig(style=BowStyle.WAVE_PIERCING, stem_rake_deg=-5)
        generator = BowGenerator()
        
        bow = generator.generate(definition, config)
        
        assert len(bow.stem_curve) >= 2
    
    def test_wave_piercing_very_fine_entry(self):
        """Wave-piercing bow should have very fine entry."""
        definition = _create_definition(BowStyle.WAVE_PIERCING)
        config = BowConfig(style=BowStyle.WAVE_PIERCING, half_angle_deg=12)
        generator = BowGenerator()
        
        bow = generator.generate(definition, config)
        
        # Entry should be finer (smaller beam growth in forward sections)
        if len(bow.sections) > 2:
            first_beam = max(p.position.y for p in bow.sections[1].points) if bow.sections[1].points else 0
            second_beam = max(p.position.y for p in bow.sections[2].points) if bow.sections[2].points else 0
            assert first_beam < second_beam, "Entry should be fine with gradual beam growth"


class TestTraditionalBow:
    """Traditional (smooth) bow generation tests."""
    
    def test_traditional_no_panel_edges(self):
        """Traditional bow should have no hard panel edges."""
        definition = _create_definition(BowStyle.TRADITIONAL)
        config = BowConfig(style=BowStyle.TRADITIONAL)
        generator = BowGenerator()
        
        bow = generator.generate(definition, config)
        
        assert len(bow.panel_edges) == 0
    
    def test_traditional_smooth_sections(self):
        """Traditional bow sections should be smooth (no hard edges except keel)."""
        definition = _create_definition(BowStyle.TRADITIONAL)
        config = BowConfig(style=BowStyle.TRADITIONAL)
        generator = BowGenerator()
        
        bow = generator.generate(definition, config)
        
        for section in bow.sections:
            for point in section.points:
                # Traditional bow should have smooth edges
                assert point.edge_type == EdgeType.SMOOTH


class TestHullGeneratorBowIntegration:
    """Integration tests: BowGenerator + HullGenerator."""
    
    def test_hull_generator_uses_bow_style(self):
        """HullGenerator should use bow style from features."""
        features = HullFeatures(bow_style=BowStyle.WEDGE, chine_type=ChineType.HARD)
        definition = _create_definition_with_features(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        hull = generator.generate(definition)
        
        # Should have bow panel edges stored
        assert len(hull.bow_panel_edges) > 0
    
    def test_hull_generator_traditional_no_bow_edges(self):
        """Traditional bow should not produce panel edges."""
        features = HullFeatures(bow_style=BowStyle.TRADITIONAL, chine_type=ChineType.HARD)
        definition = _create_definition_with_features(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        hull = generator.generate(definition)
        
        assert len(hull.bow_panel_edges) == 0
    
    @pytest.mark.parametrize("bow_style", [
        BowStyle.TRADITIONAL,
        BowStyle.WEDGE,
        BowStyle.AXE,
        BowStyle.FACETED,
        BowStyle.WAVE_PIERCING,
    ])
    def test_hull_generates_valid_sections(self, bow_style):
        """All bow styles should produce valid hull sections."""
        features = HullFeatures(bow_style=bow_style, chine_type=ChineType.HARD)
        definition = _create_definition_with_features(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        hull = generator.generate(definition)
        
        # Should have sections
        assert len(hull.sections) > 0
        
        # All sections should have points
        for section in hull.sections:
            assert len(section.points) > 0
    
    @pytest.mark.parametrize("bow_style", [
        BowStyle.TRADITIONAL,
        BowStyle.WEDGE,
        BowStyle.AXE,
        BowStyle.FACETED,
        BowStyle.WAVE_PIERCING,
    ])
    def test_hull_volume_positive(self, bow_style):
        """All bow styles should produce positive hull volume."""
        features = HullFeatures(bow_style=bow_style, chine_type=ChineType.HARD)
        definition = _create_definition_with_features(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        hull = generator.generate(definition)
        
        assert hull.volume > 0, f"{bow_style.value} hull should have positive volume"


class TestMeshValidity:
    """Verify mesh validity with new bow forms."""
    
    @pytest.mark.parametrize("bow_style", [
        BowStyle.WEDGE,
        BowStyle.AXE,
        BowStyle.FACETED,
        BowStyle.WAVE_PIERCING,
    ])
    def test_no_nan_in_points(self, bow_style):
        """Generated sections should have no NaN positions."""
        features = HullFeatures(bow_style=bow_style, chine_type=ChineType.HARD)
        definition = _create_definition_with_features(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        hull = generator.generate(definition)
        
        for section in hull.sections:
            for point in section.points:
                assert not math.isnan(point.position.x), "X should not be NaN"
                assert not math.isnan(point.position.y), "Y should not be NaN"
                assert not math.isnan(point.position.z), "Z should not be NaN"


class TestBackwardCompatibility:
    """Ensure existing functionality still works."""
    
    def test_default_features_use_traditional_bow(self):
        """Default HullFeatures should use traditional bow."""
        features = HullFeatures()
        assert features.bow_style == BowStyle.TRADITIONAL
    
    def test_existing_hull_generation_unchanged(self):
        """Existing hull generation (no bow_style set) should work as before."""
        definition = HullDefinition(
            hull_id="COMPAT-TEST",
            hull_type=HullType.HARD_CHINE,
            dimensions=MainDimensions(
                loa=20.0, lwl=19.0, beam_max=5.0, beam_wl=4.8, 
                beam_chine=4.5, draft=1.5, depth=3.0
            ),
            coefficients=FormCoefficients(cb=0.45, cp=0.65, cm=0.80, cwp=0.75, lcb=0.52),
            deadrise=DeadriseProfile.warped(18.0, 20.0, 35.0),
            features=HullFeatures(chine_type=ChineType.HARD),  # No bow_style
        )
        
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        hull = generator.generate(definition)
        
        assert len(hull.sections) == 21
        hull.compute_volume()  # Ensure volume is computed
        assert hull.volume > 0

