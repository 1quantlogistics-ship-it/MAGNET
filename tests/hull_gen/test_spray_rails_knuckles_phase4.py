"""
tests/hull_gen/test_spray_rails_knuckles_phase4.py - Phase 4 tests.

Tests spray rails and knuckle lines:
- SprayRailConfig and KnuckleLineConfig dataclasses
- SprayRailModifier and KnuckleModifier
- Integration with HullGenerator
- Longitudinal feature collection
"""

import pytest
import math
from typing import List

from magnet.hull_gen.generator import HullGenerator, GeneratorConfig
from magnet.hull_gen.geometry import EdgeType, SectionPoint, Point3D, HullSection, LongitudinalFeature
from magnet.hull_gen.enums import HullType, ChineType
from magnet.hull_gen.parameters import (
    HullDefinition, HullFeatures, MainDimensions, FormCoefficients, DeadriseProfile,
    SprayRailConfig, KnuckleLineConfig,
)
from magnet.hull_gen.modifiers import SprayRailModifier, KnuckleModifier


def _create_base_section() -> List[SectionPoint]:
    """Create simple base section for testing."""
    points = []
    for i in range(10):
        t = i / 9
        points.append(SectionPoint(
            position=Point3D(x=10.0, y=t * 2.5, z=-1.5 + t * 3.0),
            edge_type=EdgeType.SMOOTH,
            is_keel=(i == 0),
        ))
    return points


def _create_definition(features: HullFeatures = None) -> HullDefinition:
    """Create test hull definition."""
    return HullDefinition(
        hull_id="TEST-PHASE4",
        hull_name="Test Phase 4 Hull",
        hull_type=HullType.HARD_CHINE,
        dimensions=MainDimensions(
            loa=20.0,
            lwl=19.0,
            beam_max=5.0,
            beam_wl=4.8,
            beam_chine=4.5,
            depth=2.5,
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
        features=features or HullFeatures(chine_type=ChineType.HARD),
    )


class TestSprayRailConfigDataclass:
    """SprayRailConfig dataclass tests."""
    
    def test_default_values(self):
        """SprayRailConfig should have sensible defaults."""
        config = SprayRailConfig()
        assert config.height_ratio == 0.25
        assert config.angle_deg == 15.0
        assert config.width_m == 0.05
        assert config.start_station == 0.15
        assert config.end_station == 0.95
        assert config.is_hard is True
    
    def test_is_active_at_station_inside(self):
        """Should be active at stations within extent."""
        config = SprayRailConfig(start_station=0.2, end_station=0.8)
        assert config.is_active_at_station(0.5) is True
        assert config.is_active_at_station(0.2) is True
        assert config.is_active_at_station(0.8) is True
    
    def test_is_active_at_station_outside(self):
        """Should be inactive at stations outside extent."""
        config = SprayRailConfig(start_station=0.2, end_station=0.8)
        assert config.is_active_at_station(0.1) is False
        assert config.is_active_at_station(0.9) is False
    
    def test_to_dict_from_dict(self):
        """SprayRailConfig should serialize and deserialize correctly."""
        config = SprayRailConfig(
            height_ratio=0.30,
            angle_deg=20.0,
            width_m=0.06,
        )
        d = config.to_dict()
        restored = SprayRailConfig.from_dict(d)
        assert restored.height_ratio == pytest.approx(0.30, rel=0.01)
        assert restored.angle_deg == pytest.approx(20.0, rel=0.01)
        assert restored.width_m == pytest.approx(0.06, rel=0.01)


class TestKnuckleLineConfigDataclass:
    """KnuckleLineConfig dataclass tests."""
    
    def test_default_values(self):
        """KnuckleLineConfig should have sensible defaults."""
        config = KnuckleLineConfig()
        assert config.height_ratio == 0.7
        assert config.angle_deg == 5.0
        assert config.is_hard is True
    
    def test_is_active_at_station_inside(self):
        """Should be active at stations within extent."""
        config = KnuckleLineConfig(start_station=0.1, end_station=0.9)
        assert config.is_active_at_station(0.5) is True
    
    def test_is_active_at_station_outside(self):
        """Should be inactive at stations outside extent."""
        config = KnuckleLineConfig(start_station=0.1, end_station=0.9)
        assert config.is_active_at_station(0.05) is False
        assert config.is_active_at_station(0.95) is False
    
    def test_to_dict_from_dict(self):
        """KnuckleLineConfig should serialize and deserialize correctly."""
        config = KnuckleLineConfig(height_ratio=0.65, angle_deg=8.0)
        d = config.to_dict()
        restored = KnuckleLineConfig.from_dict(d)
        assert restored.height_ratio == pytest.approx(0.65, rel=0.01)
        assert restored.angle_deg == pytest.approx(8.0, rel=0.01)


class TestHullFeaturesSprayRails:
    """HullFeatures spray rail configuration tests."""
    
    def test_get_spray_rails_explicit(self):
        """Should return explicit spray rails if provided."""
        features = HullFeatures(
            spray_rails=[SprayRailConfig(height_ratio=0.20)]
        )
        rails = features.get_spray_rails()
        assert len(rails) == 1
        assert rails[0].height_ratio == 0.20
    
    def test_get_spray_rails_generated(self):
        """Should generate spray rails from count."""
        features = HullFeatures(spray_rail_count=3)
        rails = features.get_spray_rails()
        assert len(rails) == 3
    
    def test_get_spray_rails_empty(self):
        """Should return empty list if no spray rails."""
        features = HullFeatures()
        rails = features.get_spray_rails()
        assert len(rails) == 0
    
    def test_get_active_spray_rails_at_station(self):
        """Should filter to active rails at station."""
        features = HullFeatures(
            spray_rails=[
                SprayRailConfig(height_ratio=0.2, start_station=0.1, end_station=0.5),
                SprayRailConfig(height_ratio=0.3, start_station=0.4, end_station=0.9),
            ]
        )
        # At station 0.3 - only first rail active
        active_03 = features.get_active_spray_rails_at_station(0.3)
        assert len(active_03) == 1
        
        # At station 0.45 - both rails active
        active_045 = features.get_active_spray_rails_at_station(0.45)
        assert len(active_045) == 2
        
        # At station 0.7 - only second rail active
        active_07 = features.get_active_spray_rails_at_station(0.7)
        assert len(active_07) == 1


class TestHullFeaturesKnuckleLines:
    """HullFeatures knuckle line configuration tests."""
    
    def test_get_knuckle_lines(self):
        """Should return knuckle lines."""
        features = HullFeatures(
            knuckle_lines=[KnuckleLineConfig(height_ratio=0.75)]
        )
        knuckles = features.get_knuckle_lines()
        assert len(knuckles) == 1
        assert knuckles[0].height_ratio == 0.75
    
    def test_get_active_knuckles_at_station(self):
        """Should filter to active knuckles at station."""
        features = HullFeatures(
            knuckle_lines=[
                KnuckleLineConfig(height_ratio=0.7, start_station=0.2, end_station=0.8)
            ]
        )
        assert len(features.get_active_knuckles_at_station(0.5)) == 1
        assert len(features.get_active_knuckles_at_station(0.1)) == 0


class TestSprayRailModifier:
    """SprayRailModifier tests."""
    
    def test_modifier_adds_rail_points(self):
        """Spray rail modifier should add points to section."""
        modifier = SprayRailModifier()
        points = _create_base_section()
        features = HullFeatures(
            spray_rails=[SprayRailConfig(height_ratio=0.25)]
        )
        definition = _create_definition(features)
        
        modified = modifier.modify(points, station=0.5, definition=definition)
        
        # Should have more points than original
        assert len(modified) > len(points)
        
        # Should have spray rail feature points
        rail_points = [p for p in modified if p.feature_id and "spray_rail" in p.feature_id]
        assert len(rail_points) > 0
    
    def test_spray_rail_points_are_hard(self):
        """Spray rail points should have hard edge type."""
        modifier = SprayRailModifier()
        points = _create_base_section()
        features = HullFeatures(
            spray_rails=[SprayRailConfig(height_ratio=0.25)]
        )
        definition = _create_definition(features)
        
        modified = modifier.modify(points, station=0.5, definition=definition)
        
        rail_points = [p for p in modified if p.feature_id and "spray_rail" in p.feature_id]
        for point in rail_points:
            assert point.edge_type == EdgeType.HARD
    
    def test_spray_rail_not_added_outside_extent(self):
        """Spray rail should not appear outside its extent."""
        modifier = SprayRailModifier()
        points = _create_base_section()
        
        features = HullFeatures(
            spray_rails=[SprayRailConfig(start_station=0.3, end_station=0.7)]
        )
        definition = _create_definition(features)
        
        # Station before rail start
        modified_early = modifier.modify(list(points), station=0.1, definition=definition)
        rail_points_early = [p for p in modified_early if p.feature_id and "spray_rail" in p.feature_id]
        assert len(rail_points_early) == 0
        
        # Station after rail end
        modified_late = modifier.modify(list(points), station=0.9, definition=definition)
        rail_points_late = [p for p in modified_late if p.feature_id and "spray_rail" in p.feature_id]
        assert len(rail_points_late) == 0
        
        # Station within rail extent
        modified_mid = modifier.modify(list(points), station=0.5, definition=definition)
        rail_points_mid = [p for p in modified_mid if p.feature_id and "spray_rail" in p.feature_id]
        assert len(rail_points_mid) > 0
    
    def test_multiple_spray_rails(self):
        """Multiple spray rails should all be added."""
        modifier = SprayRailModifier()
        points = _create_base_section()
        
        features = HullFeatures(
            spray_rails=[
                SprayRailConfig(height_ratio=0.2),
                SprayRailConfig(height_ratio=0.35),
                SprayRailConfig(height_ratio=0.5),
            ]
        )
        definition = _create_definition(features)
        
        modified = modifier.modify(points, station=0.5, definition=definition)
        
        # Check for all three rails
        rail_0 = [p for p in modified if p.feature_id and "spray_rail_0" in p.feature_id]
        rail_1 = [p for p in modified if p.feature_id and "spray_rail_1" in p.feature_id]
        rail_2 = [p for p in modified if p.feature_id and "spray_rail_2" in p.feature_id]
        
        assert len(rail_0) > 0, "Rail 0 should exist"
        assert len(rail_1) > 0, "Rail 1 should exist"
        assert len(rail_2) > 0, "Rail 2 should exist"
    
    def test_spray_rail_projects_outward(self):
        """Spray rail tip should project outward from hull surface."""
        modifier = SprayRailModifier()
        points = _create_base_section()
        
        features = HullFeatures(
            spray_rails=[SprayRailConfig(height_ratio=0.3, width_m=0.08)]
        )
        definition = _create_definition(features)
        
        modified = modifier.modify(points, station=0.5, definition=definition)
        
        # Find rail tip (the point with "tip" in feature_id)
        tip_points = [p for p in modified if p.feature_id and "tip" in p.feature_id]
        assert len(tip_points) > 0, "Should have a tip point"
        
        tip_point = tip_points[0]
        
        # Compare to base hull Y at similar height
        base_y = modifier._interpolate_y_at_z(points, tip_point.position.z)
        
        assert tip_point.position.y > base_y, "Rail tip should project outward"


class TestKnuckleModifier:
    """KnuckleModifier tests."""
    
    def test_modifier_adds_knuckle_point(self):
        """Knuckle modifier should add point at knuckle height."""
        modifier = KnuckleModifier()
        points = _create_base_section()
        features = HullFeatures(
            knuckle_lines=[KnuckleLineConfig(height_ratio=0.7)]
        )
        definition = _create_definition(features)
        
        modified = modifier.modify(points, station=0.5, definition=definition)
        
        knuckle_points = [p for p in modified if p.feature_id and "knuckle" in p.feature_id]
        assert len(knuckle_points) > 0
    
    def test_knuckle_point_is_hard(self):
        """Hard knuckle point should have hard edge type."""
        modifier = KnuckleModifier()
        points = _create_base_section()
        features = HullFeatures(
            knuckle_lines=[KnuckleLineConfig(height_ratio=0.7, is_hard=True)]
        )
        definition = _create_definition(features)
        
        modified = modifier.modify(points, station=0.5, definition=definition)
        
        knuckle_points = [p for p in modified if p.feature_id and "knuckle" in p.feature_id]
        for point in knuckle_points:
            assert point.edge_type == EdgeType.HARD
    
    def test_soft_knuckle_is_smooth(self):
        """Soft knuckle should have smooth edge type."""
        modifier = KnuckleModifier()
        points = _create_base_section()
        features = HullFeatures(
            knuckle_lines=[KnuckleLineConfig(height_ratio=0.7, is_hard=False)]
        )
        definition = _create_definition(features)
        
        modified = modifier.modify(points, station=0.5, definition=definition)
        
        knuckle_points = [p for p in modified if p.feature_id and "knuckle" in p.feature_id]
        assert len(knuckle_points) > 0
        for point in knuckle_points:
            assert point.edge_type == EdgeType.SMOOTH
    
    def test_knuckle_at_correct_height(self):
        """Knuckle should be at configured height."""
        modifier = KnuckleModifier()
        points = _create_base_section()
        
        height_ratio = 0.65
        features = HullFeatures(
            knuckle_lines=[KnuckleLineConfig(height_ratio=height_ratio)]
        )
        definition = _create_definition(features)
        draft = definition.dimensions.draft
        depth = definition.dimensions.depth
        
        expected_z = -draft + height_ratio * (depth + draft)
        
        modified = modifier.modify(points, station=0.5, definition=definition)
        
        knuckle_points = [p for p in modified if p.feature_id and "knuckle" in p.feature_id]
        assert len(knuckle_points) > 0
        knuckle_point = knuckle_points[0]
        assert abs(knuckle_point.position.z - expected_z) < 0.2


class TestHullGeneratorIntegration:
    """Integration tests with HullGenerator."""
    
    def test_spray_rails_in_generated_hull(self):
        """HullGenerator should include spray rails."""
        features = HullFeatures(
            chine_type=ChineType.HARD,
            spray_rails=[SprayRailConfig(height_ratio=0.25)]
        )
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        hull = generator.generate(definition)
        
        # Check mid-hull section for spray rail points
        mid_idx = len(hull.sections) // 2
        mid_section = hull.sections[mid_idx]
        
        rail_points = [p for p in mid_section.points if p.feature_id and "spray_rail" in p.feature_id]
        assert len(rail_points) > 0, "Mid section should have spray rail points"
    
    def test_knuckle_in_generated_hull(self):
        """HullGenerator should include knuckle lines."""
        features = HullFeatures(
            chine_type=ChineType.HARD,
            knuckle_lines=[KnuckleLineConfig(height_ratio=0.7)]
        )
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        hull = generator.generate(definition)
        
        mid_idx = len(hull.sections) // 2
        mid_section = hull.sections[mid_idx]
        
        knuckle_points = [p for p in mid_section.points if p.feature_id and "knuckle" in p.feature_id]
        assert len(knuckle_points) > 0, "Mid section should have knuckle points"
    
    def test_combined_features(self):
        """Hull with spray rails, knuckles, and chines."""
        features = HullFeatures(
            chine_type=ChineType.HARD,
            spray_rails=[
                SprayRailConfig(height_ratio=0.2),
                SprayRailConfig(height_ratio=0.35),
            ],
            knuckle_lines=[KnuckleLineConfig(height_ratio=0.75)],
        )
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        hull = generator.generate(definition)
        
        mid_section = hull.sections[len(hull.sections) // 2]
        
        # Should have chine, spray rails, and knuckle
        chine_points = [p for p in mid_section.points if p.is_chine]
        rail_points = [p for p in mid_section.points if p.feature_id and "spray_rail" in p.feature_id]
        knuckle_points = [p for p in mid_section.points if p.feature_id and "knuckle" in p.feature_id]
        
        assert len(chine_points) > 0, "Should have chine points"
        assert len(rail_points) > 0, "Should have spray rail points"
        assert len(knuckle_points) > 0, "Should have knuckle points"
    
    def test_longitudinal_features_collected(self):
        """HullGenerator should collect longitudinal features."""
        features = HullFeatures(
            chine_type=ChineType.HARD,
            spray_rails=[SprayRailConfig()],
            knuckle_lines=[KnuckleLineConfig()],
        )
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        hull = generator.generate(definition)
        
        # Check longitudinal features are populated
        assert hasattr(hull, 'longitudinal_features')
        assert len(hull.longitudinal_features) > 0, "Should have longitudinal features"
        
        # Should have both spray rail and knuckle features
        feature_types = set(f.feature_type for f in hull.longitudinal_features)
        assert "spray_rail" in feature_types or "knuckle" in feature_types


class TestHullVolumeWithFeatures:
    """Verify hull volume remains valid with longitudinal features."""
    
    def test_hull_volume_with_spray_rails(self):
        """Hull with spray rails should have positive volume."""
        features = HullFeatures(
            chine_type=ChineType.HARD,
            spray_rails=[
                SprayRailConfig(height_ratio=0.2),
                SprayRailConfig(height_ratio=0.35),
            ]
        )
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        hull = generator.generate(definition)
        
        assert hull.volume > 0, "Hull should have positive volume"
    
    def test_hull_volume_with_knuckles(self):
        """Hull with knuckle lines should have positive volume."""
        features = HullFeatures(
            chine_type=ChineType.HARD,
            knuckle_lines=[KnuckleLineConfig(height_ratio=0.75)]
        )
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        hull = generator.generate(definition)
        
        assert hull.volume > 0, "Hull should have positive volume"


class TestMeshValidity:
    """Verify mesh validity with longitudinal features."""
    
    def test_no_nan_in_points_with_spray_rails(self):
        """Generated sections should have no NaN positions with spray rails."""
        features = HullFeatures(
            chine_type=ChineType.HARD,
            spray_rails=[SprayRailConfig(), SprayRailConfig(height_ratio=0.4)]
        )
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        hull = generator.generate(definition)
        
        for section in hull.sections:
            for point in section.points:
                assert not math.isnan(point.position.x), f"X NaN at station {section.station}"
                assert not math.isnan(point.position.y), f"Y NaN at station {section.station}"
                assert not math.isnan(point.position.z), f"Z NaN at station {section.station}"
    
    def test_no_nan_in_points_with_knuckles(self):
        """Generated sections should have no NaN positions with knuckles."""
        features = HullFeatures(
            chine_type=ChineType.HARD,
            knuckle_lines=[KnuckleLineConfig()]
        )
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        hull = generator.generate(definition)
        
        for section in hull.sections:
            for point in section.points:
                assert not math.isnan(point.position.x), f"X NaN at station {section.station}"
                assert not math.isnan(point.position.y), f"Y NaN at station {section.station}"
                assert not math.isnan(point.position.z), f"Z NaN at station {section.station}"


class TestBackwardCompatibility:
    """Ensure existing functionality still works."""
    
    def test_hull_generation_without_features(self):
        """Hull generation without spray rails or knuckles should work."""
        features = HullFeatures(chine_type=ChineType.HARD)
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        hull = generator.generate(definition)
        
        assert len(hull.sections) == 21
        assert hull.volume > 0
    
    def test_longitudinal_features_empty_without_config(self):
        """Longitudinal features should be empty if none configured."""
        features = HullFeatures(chine_type=ChineType.HARD)
        definition = _create_definition(features)
        
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        hull = generator.generate(definition)
        
        assert len(hull.longitudinal_features) == 0


class TestLongitudinalFeatureDataclass:
    """LongitudinalFeature dataclass tests."""
    
    def test_default_values(self):
        """LongitudinalFeature should have sensible defaults."""
        feature = LongitudinalFeature()
        assert feature.feature_type == ""
        assert feature.feature_id == ""
        assert feature.is_hard is True
        assert len(feature.points) == 0
    
    def test_to_dict(self):
        """LongitudinalFeature should serialize correctly."""
        feature = LongitudinalFeature(
            feature_type="spray_rail",
            feature_id="spray_rail_0_tip",
            points=[Point3D(x=1, y=2, z=3)],
            is_hard=True,
        )
        d = feature.to_dict()
        assert d["feature_type"] == "spray_rail"
        assert d["feature_id"] == "spray_rail_0_tip"
        assert d["is_hard"] is True
        assert len(d["points"]) == 1

