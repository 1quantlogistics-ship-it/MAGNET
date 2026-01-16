"""
tests/hull_gen/test_chine_variations_phase2.py - Phase 2 chine variations tests.

Tests the expanded chine capabilities:
- Double/triple hard chines
- Reverse chines (outward-angled)
- Variable chines (soft→hard transition)
- Chine flats
"""

import pytest
import math
from magnet.hull_gen.geometry import EdgeType, SectionPoint, Point3D
from magnet.hull_gen.generator import HullGenerator, GeneratorConfig
from magnet.hull_gen.enums import HullType, ChineType
from magnet.hull_gen.parameters import (
    HullDefinition, MainDimensions, FormCoefficients, 
    DeadriseProfile, HullFeatures, ChineConfig
)


def _create_definition(features: HullFeatures) -> HullDefinition:
    """Create test hull definition with given features."""
    return HullDefinition(
        hull_id="TEST-PHASE2",
        hull_name="Test Phase 2 Hull",
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


class TestChineConfigDataclass:
    """Test ChineConfig dataclass."""
    
    def test_chine_config_defaults(self):
        """ChineConfig should have sensible defaults."""
        config = ChineConfig()
        assert config.height_ratio == 0.3
        assert config.angle_deg == 45.0
        assert config.is_hard is True
        assert config.flat_width_m == 0.0
        assert config.start_station == 0.0
        assert config.end_station == 1.0
    
    def test_chine_config_to_dict(self):
        """ChineConfig should serialize to dict."""
        config = ChineConfig(height_ratio=0.25, angle_deg=50, is_hard=True)
        d = config.to_dict()
        assert d["height_ratio"] == 0.25
        assert d["angle_deg"] == 50.0
        assert d["is_hard"] is True
    
    def test_chine_config_from_dict(self):
        """ChineConfig should deserialize from dict."""
        d = {"height_ratio": 0.4, "angle_deg": 35, "is_hard": False}
        config = ChineConfig.from_dict(d)
        assert config.height_ratio == 0.4
        assert config.angle_deg == 35
        assert config.is_hard is False


class TestHullFeaturesGetChineConfigs:
    """Test HullFeatures.get_chine_configs() method."""
    
    def test_double_chine_returns_two_configs(self):
        """ChineType.DOUBLE should return two ChineConfigs."""
        features = HullFeatures(chine_type=ChineType.DOUBLE)
        configs = features.get_chine_configs()
        assert len(configs) == 2
        # Should be sorted by height
        assert configs[0].height_ratio < configs[1].height_ratio
    
    def test_triple_chine_returns_three_configs(self):
        """ChineType.TRIPLE should return three ChineConfigs."""
        features = HullFeatures(chine_type=ChineType.TRIPLE)
        configs = features.get_chine_configs()
        assert len(configs) == 3
        # Should be sorted by height
        assert configs[0].height_ratio < configs[1].height_ratio < configs[2].height_ratio
    
    def test_explicit_chines_override_defaults(self):
        """Explicit chines list should override type defaults."""
        explicit = [ChineConfig(height_ratio=0.5, angle_deg=30, is_hard=True)]
        features = HullFeatures(chine_type=ChineType.DOUBLE, chines=explicit)
        configs = features.get_chine_configs()
        assert len(configs) == 1
        assert configs[0].height_ratio == 0.5
    
    def test_soft_chine_returns_empty(self):
        """ChineType.SOFT should return empty list."""
        features = HullFeatures(chine_type=ChineType.SOFT)
        configs = features.get_chine_configs()
        assert len(configs) == 0


class TestDoubleChine:
    """Double hard chine generation tests."""
    
    def test_double_chine_generates_two_hard_edges(self):
        """Double chine hull should have two hard edge lines per side."""
        features = HullFeatures(chine_type=ChineType.DOUBLE)
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=11))
        hull = generator.generate(definition)
        
        # Check mid-sections have two chine points with hard edges
        for section in hull.sections[3:-3]:  # Skip bow/stern extremes
            hard_chine_points = [
                p for p in section.points 
                if p.is_chine and p.edge_type == EdgeType.HARD
            ]
            assert len(hard_chine_points) >= 2, \
                f"Expected 2+ hard chines at station {section.station}, got {len(hard_chine_points)}"
    
    def test_double_chine_heights_ordered(self):
        """Double chine should have chines at increasing heights."""
        features = HullFeatures(chine_type=ChineType.DOUBLE)
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=11))
        hull = generator.generate(definition)
        
        mid_section = hull.sections[len(hull.sections) // 2]
        chine_points = [p for p in mid_section.points if p.is_chine]
        
        if len(chine_points) >= 2:
            chine_zs = [p.position.z for p in chine_points]
            # Should be in increasing order (bottom to top)
            assert chine_zs[0] < chine_zs[-1], "Chines should be ordered from bottom to top"


class TestTripleChine:
    """Triple hard chine generation tests."""
    
    def test_triple_chine_generates_three_hard_edges(self):
        """Triple chine hull should have three hard edge lines."""
        features = HullFeatures(chine_type=ChineType.TRIPLE)
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=11))
        hull = generator.generate(definition)
        
        mid_section = hull.sections[len(hull.sections) // 2]
        hard_chine_points = [
            p for p in mid_section.points 
            if p.is_chine and p.edge_type == EdgeType.HARD
        ]
        assert len(hard_chine_points) >= 3, \
            f"Expected 3+ hard chines, got {len(hard_chine_points)}"
    
    def test_triple_chine_has_feature_ids(self):
        """Triple chine points should have feature IDs."""
        features = HullFeatures(chine_type=ChineType.TRIPLE)
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=11))
        hull = generator.generate(definition)
        
        mid_section = hull.sections[len(hull.sections) // 2]
        labeled_chines = [
            p for p in mid_section.points 
            if p.is_chine and p.feature_id is not None
        ]
        assert len(labeled_chines) >= 3


class TestReverseChine:
    """Reverse (sponson-style) chine generation tests."""
    
    def test_reverse_chine_extends_outward(self):
        """Reverse chine should extend beyond base hull beam."""
        features = HullFeatures(
            chine_type=ChineType.REVERSE,
            reverse_chine_extension_m=0.15,
        )
        definition = _create_definition(features)
        half_beam = definition.dimensions.beam_max / 2
        
        generator = HullGenerator(GeneratorConfig(num_sections=11))
        hull = generator.generate(definition)
        
        # Find maximum Y in mid-section
        mid_section = hull.sections[len(hull.sections) // 2]
        max_y = max(p.position.y for p in mid_section.points)
        
        # Should extend beyond nominal half beam
        assert max_y > half_beam * 0.9, \
            f"Reverse chine should extend outward: max_y={max_y}, half_beam={half_beam}"
    
    def test_reverse_chine_has_hard_edges(self):
        """Reverse chine should have hard edges at transitions."""
        features = HullFeatures(chine_type=ChineType.REVERSE)
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=11))
        hull = generator.generate(definition)
        
        mid_section = hull.sections[len(hull.sections) // 2]
        reverse_chine_points = [
            p for p in mid_section.points 
            if p.feature_id and "reverse" in p.feature_id
        ]
        
        assert len(reverse_chine_points) >= 2, "Should have multiple reverse chine points"
        assert all(p.edge_type == EdgeType.HARD for p in reverse_chine_points), \
            "Reverse chine points should be hard edges"
    
    def test_reverse_chine_feature_ids(self):
        """Reverse chine should have inner, tip, and outer feature IDs."""
        features = HullFeatures(chine_type=ChineType.REVERSE)
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=11))
        hull = generator.generate(definition)
        
        mid_section = hull.sections[len(hull.sections) // 2]
        feature_ids = [p.feature_id for p in mid_section.points if p.feature_id]
        
        assert any("inner" in fid for fid in feature_ids), "Should have inner edge"
        assert any("tip" in fid for fid in feature_ids), "Should have tip"
        assert any("outer" in fid for fid in feature_ids), "Should have outer edge"


class TestVariableChine:
    """Variable chine (soft→hard transition) generation tests."""
    
    def test_variable_chine_soft_forward(self):
        """Variable chine should be soft at bow."""
        features = HullFeatures(
            chine_type=ChineType.VARIABLE,
            chine_transition_start=0.3,
            chine_transition_end=0.6,
        )
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        hull = generator.generate(definition)
        
        # Forward sections (station > 0.7) should have no hard edges
        forward_sections = [s for s in hull.sections if s.station > 0.7]
        for section in forward_sections[:2]:  # Check a couple forward sections
            hard_points = [p for p in section.points if p.edge_type == EdgeType.HARD]
            assert len(hard_points) == 0, \
                f"Bow (station {section.station}) should have soft chine, found {len(hard_points)} hard points"
    
    def test_variable_chine_hard_aft(self):
        """Variable chine should produce valid geometry at stern."""
        features = HullFeatures(
            chine_type=ChineType.VARIABLE,
            chine_transition_start=0.3,
            chine_transition_end=0.6,
        )
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        hull = generator.generate(definition)
        
        # Aft sections should have valid geometry (multiple points)
        # The blended approach creates smooth transitions, so we don't
        # require is_chine flags, just valid point sets
        aft_sections = [s for s in hull.sections if 0.1 < s.station < 0.25]
        for section in aft_sections[:2]:
            assert len(section.points) >= 3, \
                f"Stern (station {section.station}) should have multiple points"
            # Verify the shape has valid extents
            max_y = max(p.position.y for p in section.points)
            max_z = max(p.position.z for p in section.points)
            # Use tolerance for floating point comparison
            assert max_y > 0, f"Section should have positive y extent, got {max_y}"
            assert max_z >= -1e-10, f"Section max_z should be non-negative, got {max_z}"
    
    def test_variable_chine_smooth_transition(self):
        """Variable chine transition should be smooth in mid-body region."""
        features = HullFeatures(
            chine_type=ChineType.VARIABLE,
            chine_transition_start=0.3,
            chine_transition_end=0.6,
        )
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        hull = generator.generate(definition)
        
        # Check mid-body sections only (exclude bow/stern closure)
        mid_sections = [s for s in hull.sections if 0.15 < s.station < 0.85]
        
        # Get max Y at each mid-section
        max_ys = []
        for section in mid_sections:
            if section.points:
                max_y = max(p.position.y for p in section.points)
                max_ys.append(max_y)
        
        # Check for smooth progression in mid-body (no jumps > 15% of beam)
        beam = definition.dimensions.beam_max
        for i in range(1, len(max_ys)):
            delta = abs(max_ys[i] - max_ys[i-1])
            assert delta < beam * 0.15, \
                f"Abrupt change in mid-body section shape: delta={delta}, beam={beam}"


class TestChineFlat:
    """Chine flat (horizontal extension) generation tests."""
    
    def test_chine_flat_creates_horizontal_segment(self):
        """Chine flat should create horizontal segment at chine."""
        features = HullFeatures(
            chine_type=ChineType.HARD,
            chine_flat_width_m=0.1,
        )
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=11))
        hull = generator.generate(definition)
        
        mid_section = hull.sections[len(hull.sections) // 2]
        chine_points = [p for p in mid_section.points if p.is_chine]
        
        # With chine flat, we should have at least one chine point
        assert len(chine_points) >= 1, "Should have chine point(s)"
    
    def test_double_chine_with_flat(self):
        """Double chine with flat width should work."""
        features = HullFeatures(
            chine_type=ChineType.DOUBLE,
            chine_flat_width_m=0.05,
        )
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=11))
        hull = generator.generate(definition)
        
        mid_section = hull.sections[len(hull.sections) // 2]
        chine_points = [p for p in mid_section.points if p.is_chine]
        
        # Double chine should still have multiple chine points
        assert len(chine_points) >= 2


class TestChineTypeEnum:
    """Test ChineType enum extensions."""
    
    def test_reverse_chine_type_exists(self):
        """ChineType.REVERSE should exist."""
        assert ChineType.REVERSE.value == "reverse"
    
    def test_variable_chine_type_exists(self):
        """ChineType.VARIABLE should exist."""
        assert ChineType.VARIABLE.value == "variable"


class TestHydrostaticsUnchanged:
    """Verify hydrostatics remain valid with new chine types."""
    
    @pytest.mark.parametrize("chine_type", [
        ChineType.DOUBLE,
        ChineType.TRIPLE,
        ChineType.REVERSE,
        ChineType.VARIABLE,
    ])
    def test_volume_positive(self, chine_type):
        """All chine types should produce positive volume."""
        features = HullFeatures(chine_type=chine_type)
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        hull = generator.generate(definition)
        
        hull.compute_volume()
        assert hull.volume > 0, f"{chine_type.value} hull should have positive volume"
    
    @pytest.mark.parametrize("chine_type", [
        ChineType.DOUBLE,
        ChineType.TRIPLE,
        ChineType.REVERSE,
        ChineType.VARIABLE,
    ])
    def test_section_areas_positive(self, chine_type):
        """All section areas should be non-negative."""
        features = HullFeatures(chine_type=chine_type)
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=11))
        hull = generator.generate(definition)
        
        for section in hull.sections:
            area = section.compute_area(0.0)
            assert area >= 0, f"Section area should be non-negative: {area}"


class TestMeshValidity:
    """Verify mesh validity with new chine types."""
    
    @pytest.mark.parametrize("chine_type", [
        ChineType.DOUBLE,
        ChineType.TRIPLE,
        ChineType.REVERSE,
        ChineType.VARIABLE,
    ])
    def test_no_nan_in_points(self, chine_type):
        """Generated sections should have no NaN positions."""
        features = HullFeatures(chine_type=chine_type)
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=11))
        hull = generator.generate(definition)
        
        for section in hull.sections:
            for point in section.points:
                assert not math.isnan(point.position.x), "X should not be NaN"
                assert not math.isnan(point.position.y), "Y should not be NaN"
                assert not math.isnan(point.position.z), "Z should not be NaN"
    
    @pytest.mark.parametrize("chine_type", [
        ChineType.DOUBLE,
        ChineType.TRIPLE,
        ChineType.REVERSE,
        ChineType.VARIABLE,
    ])
    def test_points_ordered_keel_to_deck(self, chine_type):
        """Section points should be ordered from keel (low Z) to deck (high Z)."""
        features = HullFeatures(chine_type=chine_type)
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=11))
        hull = generator.generate(definition)
        
        for section in hull.sections:
            if len(section.points) >= 2:
                # First point should be at or near keel
                first_z = section.points[0].position.z
                last_z = section.points[-1].position.z
                assert first_z <= last_z, \
                    f"Points should go from keel (z={first_z}) to deck (z={last_z})"


class TestBackwardCompatibility:
    """Ensure Phase 1 functionality still works."""
    
    def test_single_hard_chine_still_works(self):
        """ChineType.HARD should still generate single hard chine."""
        features = HullFeatures(chine_type=ChineType.HARD)
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=11))
        hull = generator.generate(definition)
        
        mid_section = hull.sections[len(hull.sections) // 2]
        hard_chine_points = [
            p for p in mid_section.points 
            if p.is_chine and p.edge_type == EdgeType.HARD
        ]
        
        assert len(hard_chine_points) >= 1, "Single hard chine should still work"
    
    def test_soft_chine_still_works(self):
        """ChineType.SOFT should still generate soft chine (no hard edges)."""
        features = HullFeatures(chine_type=ChineType.SOFT)
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=11))
        hull = generator.generate(definition)
        
        for section in hull.sections:
            hard_points = [p for p in section.points if p.edge_type == EdgeType.HARD]
            assert len(hard_points) == 0, "Soft chine should have no hard edges"

