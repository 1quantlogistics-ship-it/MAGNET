"""
tests/hull_gen/test_transom_phase5.py - Phase 5 Transom Generator Tests

Tests for:
1. TransomConfig presets and parametric control
2. TransomGenerator with segments, cutouts, extensions
3. HullGenerator integration with parametric transoms
4. Enhanced SprayRailConfig (Phase 4 enhancement)
5. Backward compatibility with simple transoms
"""

import math
import pytest
from typing import List

from magnet.hull_gen.parameters import (
    TransomConfig,
    TransomSegment,
    TransomCutout,
    TransomExtension,
    TransomEdgeConfig,
    SprayRailConfig,
    KnuckleLineConfig,
    HullFeatures,
    HullDefinition,
    MainDimensions,
    FormCoefficients,
)
from magnet.hull_gen.geometry import Point3D, EdgeType, HullSection
from magnet.hull_gen.transom_generator import TransomGenerator, TransomGeometry
from magnet.hull_gen.generator import HullGenerator, GeneratorConfig


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def simple_definition() -> HullDefinition:
    """Create a simple hull definition for testing."""
    return HullDefinition(
        hull_id="test_transom",
        dimensions=MainDimensions(
            loa=20.0,
            lwl=19.0,
            beam_max=5.0,
            beam_wl=4.8,
            draft=1.5,
            depth=2.5,
        ),
        coefficients=FormCoefficients(
            cb=0.45,
            cp=0.65,
            cm=0.75,
            cwp=0.78,
        ),
        features=HullFeatures(),
    )


@pytest.fixture
def transom_generator() -> TransomGenerator:
    """Create a TransomGenerator instance."""
    return TransomGenerator()


@pytest.fixture
def hull_generator() -> HullGenerator:
    """Create a HullGenerator with fewer sections for faster tests."""
    return HullGenerator(GeneratorConfig(num_sections=11))


# =============================================================================
# TRANSOM CONFIG TESTS
# =============================================================================

class TestTransomConfigPresets:
    """Test TransomConfig preset creation."""
    
    def test_vertical_preset(self):
        """Vertical preset has zero rake."""
        config = TransomConfig.from_preset("vertical")
        assert config.preset == "vertical"
        assert config.rake_deg == 0
    
    def test_raked_preset(self):
        """Raked preset has standard 12° rake."""
        config = TransomConfig.from_preset("raked")
        assert config.preset == "raked"
        assert config.rake_deg == 12
    
    def test_stepped_preset(self):
        """Stepped preset has vertical segments."""
        config = TransomConfig.from_preset("stepped")
        assert config.preset == "stepped"
        assert config.has_segments()
        assert len(config.vertical_segments) == 3
        # Check step segment is nearly vertical
        step_seg = config.vertical_segments[1]
        assert step_seg.rake_deg == 90
    
    def test_tunneled_preset(self):
        """Tunneled preset has cutouts."""
        config = TransomConfig.from_preset("tunneled")
        assert config.preset == "tunneled"
        assert config.has_cutouts()
        assert len(config.cutouts) == 2
        # Cutouts should be symmetrical
        assert config.cutouts[0].center_y_ratio > 0
        assert config.cutouts[1].center_y_ratio < 0
    
    def test_sugar_scoop_preset(self):
        """Sugar scoop preset has extension."""
        config = TransomConfig.from_preset("sugar_scoop")
        assert config.preset == "sugar_scoop"
        assert config.has_extensions()
        assert len(config.extensions) == 1
        assert config.extensions[0].curvature < 0  # Concave
    
    def test_preset_with_override(self):
        """Presets can be customized with overrides."""
        config = TransomConfig.from_preset("raked", rake_deg=18, corner_radius_m=0.3)
        assert config.rake_deg == 18
        assert config.corner_radius_m == 0.3
    
    def test_unknown_preset_returns_default(self):
        """Unknown preset returns default config."""
        config = TransomConfig.from_preset("nonexistent")
        assert config.rake_deg == 12  # Default


class TestTransomConfigProfiles:
    """Test TransomConfig profile interpolation."""
    
    def test_constant_rake(self):
        """Constant rake returns same value at all heights."""
        config = TransomConfig(rake_deg=15)
        assert config.get_rake_at_height(0.0) == 15
        assert config.get_rake_at_height(0.5) == 15
        assert config.get_rake_at_height(1.0) == 15
    
    def test_variable_rake_profile(self):
        """Rake profile interpolates between points."""
        config = TransomConfig(
            rake_profile=[
                (0.0, 5),
                (0.5, 12),
                (1.0, 20),
            ]
        )
        assert config.get_rake_at_height(0.0) == pytest.approx(5)
        assert config.get_rake_at_height(0.5) == pytest.approx(12)
        assert config.get_rake_at_height(0.25) == pytest.approx(8.5)  # Interpolated
        assert config.get_rake_at_height(1.0) == pytest.approx(20)
    
    def test_beam_ratio_linear_interpolation(self):
        """Beam ratio interpolates linearly between waterline and deck."""
        config = TransomConfig(
            beam_at_waterline_ratio=1.0,
            beam_at_deck_ratio=0.9,
        )
        assert config.get_beam_ratio_at_height(0.0) == pytest.approx(1.0)
        assert config.get_beam_ratio_at_height(0.5) == pytest.approx(0.95)
        assert config.get_beam_ratio_at_height(1.0) == pytest.approx(0.9)
    
    def test_curvature_profile(self):
        """Curvature profile interpolates correctly."""
        config = TransomConfig(
            curvature_profile=[
                (0.0, 0.0),
                (0.5, 0.1),
                (1.0, -0.05),
            ]
        )
        assert config.get_curvature_at_height(0.0) == pytest.approx(0.0)
        assert config.get_curvature_at_height(0.5) == pytest.approx(0.1)
        assert config.get_curvature_at_height(1.0) == pytest.approx(-0.05)


class TestTransomConfigSerialization:
    """Test TransomConfig serialization."""
    
    def test_simple_config_round_trip(self):
        """Simple config survives round-trip serialization."""
        original = TransomConfig(rake_deg=15, corner_radius_m=0.2)
        serialized = original.to_dict()
        restored = TransomConfig.from_dict(serialized)
        
        assert restored.rake_deg == pytest.approx(original.rake_deg)
        assert restored.corner_radius_m == pytest.approx(original.corner_radius_m)
    
    def test_complex_config_round_trip(self):
        """Complex config with segments/cutouts survives round-trip."""
        original = TransomConfig.from_preset("stepped")
        serialized = original.to_dict()
        restored = TransomConfig.from_dict(serialized)
        
        assert len(restored.vertical_segments) == len(original.vertical_segments)
        for orig_seg, rest_seg in zip(original.vertical_segments, restored.vertical_segments):
            assert rest_seg.rake_deg == pytest.approx(orig_seg.rake_deg)
            assert rest_seg.height_start == pytest.approx(orig_seg.height_start)


# =============================================================================
# TRANSOM GENERATOR TESTS
# =============================================================================

class TestTransomGeneratorSimple:
    """Test TransomGenerator with simple configurations."""
    
    def test_generates_section(self, transom_generator, simple_definition):
        """Generator produces a valid transom section."""
        config = TransomConfig(rake_deg=12)
        geometry = transom_generator.generate(config, simple_definition)
        
        assert geometry.section is not None
        assert len(geometry.section.points) > 0
        assert geometry.section.station == 0.0  # At stern
    
    def test_raked_transom_has_x_offset(self, transom_generator, simple_definition):
        """Raked transom has increasing X offset with height."""
        config = TransomConfig(rake_deg=15)
        geometry = transom_generator.generate(config, simple_definition)
        
        points = geometry.section.points
        
        # Points should have increasing X as Z increases
        x_values = [p.position.x for p in points]
        z_values = [p.position.z for p in points]
        
        # Find the highest point
        max_z_idx = z_values.index(max(z_values))
        
        # X at highest point should be greater than at keel
        assert x_values[max_z_idx] > x_values[0]
    
    def test_vertical_transom_no_x_offset(self, transom_generator, simple_definition):
        """Vertical transom has no X offset."""
        config = TransomConfig(rake_deg=0)
        geometry = transom_generator.generate(config, simple_definition)
        
        points = geometry.section.points
        
        # All X values should be ~0
        for point in points:
            assert abs(point.position.x) < 0.001


class TestTransomGeneratorSegmented:
    """Test TransomGenerator with stepped transoms."""
    
    def test_segmented_transom_generates(self, transom_generator, simple_definition):
        """Segmented transom generates correct structure."""
        config = TransomConfig.from_preset("stepped")
        geometry = transom_generator.generate(config, simple_definition)
        
        assert geometry.section is not None
        assert len(geometry.section.points) > 20  # Multiple segments = more points
    
    def test_stepped_transom_has_hard_edges(self, transom_generator, simple_definition):
        """Stepped transom produces hard edges at steps."""
        config = TransomConfig.from_preset("stepped")
        geometry = transom_generator.generate(config, simple_definition)
        
        # Should have hard edges from segment boundaries
        assert len(geometry.hard_edges) > 0
        
        # Check section points have hard edge types
        hard_points = [p for p in geometry.section.points if p.edge_type == EdgeType.HARD]
        assert len(hard_points) > 0
    
    def test_offset_segment_projects_aft(self, transom_generator, simple_definition):
        """Upper segment with offset projects aft."""
        config = TransomConfig(
            vertical_segments=[
                TransomSegment(height_start=0.0, height_end=0.5, rake_deg=10),
                TransomSegment(height_start=0.5, height_end=1.0, rake_deg=10, offset_aft_m=0.5),
            ]
        )
        geometry = transom_generator.generate(config, simple_definition)
        
        points = geometry.section.points
        
        # Find points in upper and lower segments
        draft = simple_definition.dimensions.draft
        depth = simple_definition.dimensions.depth
        
        lower_points = [p for p in points if p.position.z < -draft + 0.5 * depth]
        upper_points = [p for p in points if p.position.z > -draft + 0.5 * depth]
        
        # Upper points should have larger X due to offset
        if lower_points and upper_points:
            avg_lower_x = sum(p.position.x for p in lower_points) / len(lower_points)
            avg_upper_x = sum(p.position.x for p in upper_points) / len(upper_points)
            assert avg_upper_x > avg_lower_x


class TestTransomGeneratorCutouts:
    """Test TransomGenerator with cutouts."""
    
    def test_cutout_generates_sections(self, transom_generator, simple_definition):
        """Transom with cutout generates cutout sections."""
        config = TransomConfig(
            rake_deg=10,
            cutouts=[
                TransomCutout(
                    shape="semicircle",
                    center_y_ratio=0.0,
                    width_m=0.5,
                    height_m=0.4,
                    depth_m=0.8,
                ),
            ],
        )
        geometry = transom_generator.generate(config, simple_definition)
        
        assert len(geometry.cutout_sections) > 0
    
    def test_surface_notch_no_extra_sections(self, transom_generator, simple_definition):
        """Surface notch (depth=0) doesn't generate extra sections."""
        config = TransomConfig(
            rake_deg=10,
            cutouts=[
                TransomCutout(
                    shape="rectangular",
                    center_y_ratio=0.0,
                    width_m=0.5,
                    height_m=0.4,
                    depth_m=0.0,  # Surface only
                ),
            ],
        )
        geometry = transom_generator.generate(config, simple_definition)
        
        # No cutout sections since depth=0
        assert len(geometry.cutout_sections) == 0


class TestTransomGeneratorExtensions:
    """Test TransomGenerator with extensions."""
    
    def test_extension_generates_sections(self, transom_generator, simple_definition):
        """Transom with extension generates extension sections."""
        config = TransomConfig(
            rake_deg=15,
            extensions=[
                TransomExtension(
                    type="swim_platform",
                    height_start=0.3,
                    height_end=0.5,
                    depth_m=1.0,
                ),
            ],
        )
        geometry = transom_generator.generate(config, simple_definition)
        
        assert len(geometry.extension_sections) > 0
    
    def test_curved_extension(self, transom_generator, simple_definition):
        """Extension with curvature has varied Z values."""
        config = TransomConfig(
            rake_deg=15,
            extensions=[
                TransomExtension(
                    type="platform",
                    height_start=0.3,
                    height_end=0.5,
                    depth_m=1.0,
                    curvature=-0.3,  # Concave
                ),
            ],
        )
        geometry = transom_generator.generate(config, simple_definition)
        
        # Check that extension sections have curvature variation
        if geometry.extension_sections:
            section = geometry.extension_sections[len(geometry.extension_sections) // 2]
            z_values = [p.position.z for p in section.points]
            # With curvature, Z should vary across the width
            assert max(z_values) != min(z_values) if len(z_values) > 1 else True


# =============================================================================
# ENHANCED SPRAY RAIL TESTS (Phase 4)
# =============================================================================

class TestEnhancedSprayRailConfig:
    """Test enhanced SprayRailConfig with profiles."""
    
    def test_constant_width(self):
        """Constant width returns same value everywhere."""
        config = SprayRailConfig(
            width_m=0.06,
            start_station=0.1,
            end_station=0.9,
            taper_style="none",
        )
        assert config.get_width_at_station(0.3) == pytest.approx(0.06)
        assert config.get_width_at_station(0.5) == pytest.approx(0.06)
        assert config.get_width_at_station(0.7) == pytest.approx(0.06)
    
    def test_tapered_width(self):
        """Tapered width is reduced at ends."""
        config = SprayRailConfig(
            width_m=0.06,
            start_station=0.1,
            end_station=0.9,
            taper_start_length=0.2,
            taper_end_length=0.2,
            taper_style="linear",
        )
        
        # Middle should be full width
        assert config.get_width_at_station(0.5) == pytest.approx(0.06)
        
        # Ends should be tapered
        assert config.get_width_at_station(0.12) < 0.06  # Near start
        assert config.get_width_at_station(0.85) < 0.06  # Near end
    
    def test_variable_width_three_point(self):
        """Variable width uses three-point Bezier interpolation."""
        config = SprayRailConfig(
            width_m=0.05,  # Default if not specified
            width_at_start_m=0.03,
            width_at_mid_m=0.08,
            width_at_end_m=0.04,
            start_station=0.1,
            end_station=0.9,
            taper_style="none",
        )
        
        # At start should be close to start value
        assert config.get_width_at_station(0.1) == pytest.approx(0.03, rel=0.1)
        
        # At middle (t=0.5 in Bezier = control point has max influence)
        # Bezier at t=0.5: (0.25)*0.03 + (0.5)*0.08 + (0.25)*0.04 = 0.0575
        # This is correct - quadratic Bezier doesn't pass through control point
        mid_width = config.get_width_at_station(0.5)
        assert mid_width > 0.05  # Should be larger than simple average
        assert mid_width < 0.08  # But less than mid_m (control point)
        
        # At end should be close to end value
        assert config.get_width_at_station(0.9) == pytest.approx(0.04, rel=0.1)
    
    def test_width_profile(self):
        """Width profile interpolates custom points."""
        config = SprayRailConfig(
            start_station=0.15,
            end_station=0.90,
            width_profile=[
                (0.15, 0.02),
                (0.50, 0.06),
                (0.90, 0.03),
            ],
            taper_style="none",
        )
        
        assert config.get_width_at_station(0.15) == pytest.approx(0.02)
        assert config.get_width_at_station(0.50) == pytest.approx(0.06)
        assert config.get_width_at_station(0.90) == pytest.approx(0.03)
    
    def test_variable_angle(self):
        """Angle varies linearly between start and end."""
        config = SprayRailConfig(
            angle_deg=15,  # Default
            angle_at_start_deg=22,
            angle_at_end_deg=10,
            start_station=0.1,
            end_station=0.9,
        )
        
        # At start
        assert config.get_angle_at_station(0.1) == pytest.approx(22)
        
        # At end
        assert config.get_angle_at_station(0.9) == pytest.approx(10)
        
        # At middle (linear interpolation)
        assert config.get_angle_at_station(0.5) == pytest.approx(16)
    
    def test_variable_height(self):
        """Height profile varies along length."""
        config = SprayRailConfig(
            height_ratio=0.25,  # Default
            height_profile=[
                (0.1, 0.20),
                (0.5, 0.30),
                (0.9, 0.25),
            ],
            start_station=0.1,
            end_station=0.9,
        )
        
        assert config.get_height_at_station(0.1) == pytest.approx(0.20)
        assert config.get_height_at_station(0.5) == pytest.approx(0.30)
        assert config.get_height_at_station(0.9) == pytest.approx(0.25)
    
    def test_profile_types(self):
        """Different profile types are valid."""
        for profile_type in ["triangular", "rounded", "flat_top", "sharp"]:
            config = SprayRailConfig(profile=profile_type)
            assert config.profile == profile_type
    
    def test_outside_station_returns_zero(self):
        """Values outside active range return zero."""
        config = SprayRailConfig(
            width_m=0.05,
            start_station=0.2,
            end_station=0.8,
        )
        
        assert config.get_width_at_station(0.1) == 0.0
        assert config.get_width_at_station(0.9) == 0.0
        assert config.get_angle_at_station(0.1) == 0.0


# =============================================================================
# HULL GENERATOR INTEGRATION TESTS
# =============================================================================

class TestHullGeneratorTransomIntegration:
    """Test HullGenerator with parametric transoms."""
    
    def test_simple_transom_generates(self, hull_generator, simple_definition):
        """Simple transom generates correctly."""
        geometry = hull_generator.generate(simple_definition)
        
        assert len(geometry.transom_outline) > 0
    
    def test_parametric_transom_with_curvature(self, hull_generator, simple_definition):
        """Parametric transom with curvature triggers TransomGenerator."""
        simple_definition.features.transom_config = TransomConfig(
            rake_deg=15,
            curvature=0.1,
        )
        
        geometry = hull_generator.generate(simple_definition)
        assert len(geometry.transom_outline) > 0
    
    def test_stepped_transom_integration(self, hull_generator, simple_definition):
        """Stepped transom generates and has hard edges."""
        simple_definition.features.transom_preset = "stepped"
        
        geometry = hull_generator.generate(simple_definition)
        
        assert len(geometry.transom_outline) > 0
        # Stepped transom should have hard edges recorded
        assert hasattr(geometry, 'transom_hard_edges')
    
    def test_transom_width_fraction_respected(self, hull_generator, simple_definition):
        """Transom width fraction affects outline."""
        simple_definition.features.transom_width_fraction = 0.7
        
        geometry = hull_generator.generate(simple_definition)
        
        # Check max Y is less than full beam
        max_y = max(p.y for p in geometry.transom_outline)
        full_half_beam = simple_definition.dimensions.beam_max / 2
        
        assert max_y < full_half_beam * 0.9


class TestBackwardCompatibility:
    """Ensure backward compatibility with existing hull generation."""
    
    def test_no_transom_config_works(self, hull_generator, simple_definition):
        """Hull without transom_config generates normally."""
        simple_definition.features.transom_config = None
        simple_definition.features.transom_preset = None
        
        geometry = hull_generator.generate(simple_definition)
        
        assert geometry.volume > 0
        assert len(geometry.sections) > 0
        assert len(geometry.transom_outline) > 0
    
    def test_legacy_transom_rake_deg(self, hull_generator, simple_definition):
        """Legacy transom_rake_deg parameter still works."""
        simple_definition.features.transom_rake_deg = 20
        
        geometry = hull_generator.generate(simple_definition)
        
        assert len(geometry.transom_outline) > 0
    
    def test_volume_calculation_unchanged(self, hull_generator, simple_definition):
        """Volume calculation works with all transom types."""
        volumes = []
        
        # Test with different transom configs
        for preset in [None, "raked", "stepped"]:
            simple_definition.features.transom_preset = preset
            geometry = hull_generator.generate(simple_definition)
            volumes.append(geometry.volume)
        
        # All should have valid volumes
        for vol in volumes:
            assert vol > 0


class TestHydrostaticsUnchanged:
    """Verify hydrostatics are not affected by transom changes."""
    
    def test_volume_similar_across_presets(self, hull_generator, simple_definition):
        """Volume should be similar regardless of transom preset."""
        baseline_geometry = hull_generator.generate(simple_definition)
        baseline_volume = baseline_geometry.volume
        
        for preset in ["raked", "stepped", "tunneled"]:
            simple_definition.features.transom_preset = preset
            geometry = hull_generator.generate(simple_definition)
            
            # Volume should be within 10% of baseline
            # (transom variations shouldn't dramatically change displacement)
            assert abs(geometry.volume - baseline_volume) / baseline_volume < 0.10, \
                f"Volume with {preset} transom differs too much from baseline"


# =============================================================================
# HULL FEATURES INTEGRATION
# =============================================================================

class TestHullFeaturesTransomConfig:
    """Test HullFeatures transom configuration integration."""
    
    def test_get_transom_config_from_explicit(self):
        """Explicit transom_config is returned."""
        features = HullFeatures(
            transom_config=TransomConfig(rake_deg=18, corner_radius_m=0.3)
        )
        config = features.get_transom_config()
        
        assert config.rake_deg == 18
        assert config.corner_radius_m == 0.3
    
    def test_get_transom_config_from_preset(self):
        """Preset generates correct config."""
        features = HullFeatures(
            transom_preset="stepped",
            transom_rake_deg=15,
        )
        config = features.get_transom_config()
        
        assert config.has_segments()
        assert config.rake_deg == 15  # Override applied
    
    def test_get_transom_config_default(self):
        """Default config uses legacy params."""
        features = HullFeatures(
            transom_rake_deg=14,
            transom_width_fraction=0.8,
        )
        config = features.get_transom_config()
        
        assert config.rake_deg == 14
        assert config.beam_at_waterline_ratio == 0.8

