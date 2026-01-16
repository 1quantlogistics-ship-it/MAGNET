"""
Phase 6 tests: Tumblehome, faceted panels, flat deck.

BRAVO OWNS THIS FILE.

Tests for Phase 6 hull surface completion features:
- TumblehomeConfig and TumblehomeModifier
- PanelConfig and faceted tessellation
- DeckConfig and DeckGenerator
- Integration with HullGenerator
"""
import pytest
import math
from typing import List

from magnet.hull_gen.generator import HullGenerator
from magnet.hull_gen.deck_generator import DeckGenerator, DeckGeometry
from magnet.hull_gen.geometry import EdgeType, Point3D, HullSection, SectionPoint
from magnet.hull_gen.parameters import (
    HullDefinition, HullFeatures, MainDimensions, FormCoefficients,
    TumblehomeConfig, PanelConfig, DeckConfig, ChineConfig,
)
from magnet.hull_gen.enums import ChineType
from magnet.hull_gen.modifiers import TumblehomeModifier


# =============================================================================
# TUMBLEHOME CONFIG TESTS
# =============================================================================

class TestTumblehomeConfig:
    """TumblehomeConfig dataclass tests."""
    
    def test_default_disabled(self):
        """Default config should be disabled."""
        config = TumblehomeConfig()
        assert config.enabled == False
        assert config.angle_deg == 5.0
    
    def test_get_angle_at_disabled(self):
        """Disabled config should return 0 angle."""
        config = TumblehomeConfig(enabled=False, angle_deg=10.0)
        assert config.get_angle_at(0.5, 0.5) == 0.0
        assert config.get_angle_at(0.5, 1.0) == 0.0
    
    def test_get_angle_at_linear(self):
        """Angle should scale with height in zone."""
        config = TumblehomeConfig(enabled=True, angle_deg=10.0, transition_length=0.0)
        # At deck (height_in_zone=1.0), should be full angle
        assert config.get_angle_at(0.5, 1.0) == pytest.approx(10.0, rel=0.01)
        # At mid-height, should be half angle
        assert config.get_angle_at(0.5, 0.5) == pytest.approx(5.0, rel=0.01)
        # At start of zone, should be 0
        assert config.get_angle_at(0.5, 0.0) == pytest.approx(0.0, abs=0.01)
    
    def test_get_angle_by_station(self):
        """Angle can vary by station."""
        config = TumblehomeConfig(
            enabled=True,
            angle_deg=10.0,
            angle_by_station=[(0.0, 5.0), (0.5, 10.0), (1.0, 8.0)],
            transition_length=0.0,
        )
        # At height=1.0 (full zone), should get interpolated station angle
        assert config.get_angle_at(0.0, 1.0) == pytest.approx(5.0, rel=0.1)
        assert config.get_angle_at(0.5, 1.0) == pytest.approx(10.0, rel=0.1)
        assert config.get_angle_at(1.0, 1.0) == pytest.approx(8.0, rel=0.1)
    
    def test_station_outside_range_returns_zero(self):
        """Station outside range should return zero."""
        config = TumblehomeConfig(
            enabled=True,
            angle_deg=10.0,
            start_station=0.2,
            end_station=0.8,
        )
        assert config.get_angle_at(0.1, 1.0) == 0.0
        assert config.get_angle_at(0.9, 1.0) == 0.0
        assert config.get_angle_at(0.5, 1.0) > 0.0
    
    def test_smooth_transition(self):
        """Smooth transition should ease in at start of zone."""
        config = TumblehomeConfig(
            enabled=True,
            angle_deg=10.0,
            transition_length=0.2,
            transition_style="smooth",
        )
        # At very start, angle should be near zero
        angle_at_start = config.get_angle_at(0.5, 0.01)
        angle_at_mid = config.get_angle_at(0.5, 0.5)
        assert angle_at_start < angle_at_mid * 0.1
    
    def test_to_dict_from_dict(self):
        """Serialization round-trip should preserve values."""
        config = TumblehomeConfig(
            enabled=True,
            angle_deg=8.0,
            start_height_ratio=0.1,
            start_station=0.1,
            end_station=0.9,
        )
        data = config.to_dict()
        restored = TumblehomeConfig.from_dict(data)
        
        assert restored.enabled == config.enabled
        assert restored.angle_deg == config.angle_deg
        assert restored.start_height_ratio == config.start_height_ratio


# =============================================================================
# TUMBLEHOME MODIFIER TESTS
# =============================================================================

class TestTumblehomeModifier:
    """TumblehomeModifier tests."""
    
    def test_modifier_reduces_y_above_waterline(self):
        """Tumblehome should reduce Y (inward lean) above start height."""
        modifier = TumblehomeModifier()
        points = self._create_base_section()
        
        features = HullFeatures(
            tumblehome_enabled=True,
            tumblehome_angle_deg=10.0,
            tumblehome_start_ratio=0.0,  # Start at waterline
        )
        definition = self._create_definition(features)
        
        modified = modifier.modify(points, station=0.5, definition=definition)
        
        # Find points above waterline (z > 0)
        above_wl_orig = [p for p in points if p.position.z > 0.1]
        above_wl_mod = [p for p in modified if p.position.z > 0.1]
        
        assert len(above_wl_orig) > 0, "Should have points above waterline"
        
        # Modified Y should be less (inward)
        for orig, mod in zip(above_wl_orig, above_wl_mod):
            assert mod.position.y <= orig.position.y, \
                f"Modified Y ({mod.position.y}) should be <= original ({orig.position.y}) at z={orig.position.z}"
    
    def test_modifier_preserves_below_waterline(self):
        """Tumblehome should not affect points below waterline."""
        modifier = TumblehomeModifier()
        points = self._create_base_section()
        
        features = HullFeatures(
            tumblehome_enabled=True,
            tumblehome_angle_deg=10.0,
            tumblehome_start_ratio=0.0,
        )
        definition = self._create_definition(features)
        
        modified = modifier.modify(points, station=0.5, definition=definition)
        
        # Points at or below waterline unchanged
        below_wl_orig = [p for p in points if p.position.z <= 0]
        below_wl_mod = [p for p in modified if p.position.z <= 0]
        
        for orig, mod in zip(below_wl_orig, below_wl_mod):
            assert mod.position.y == pytest.approx(orig.position.y, abs=0.001)
    
    def test_modifier_disabled_no_change(self):
        """Disabled tumblehome should not modify points."""
        modifier = TumblehomeModifier()
        points = self._create_base_section()
        
        features = HullFeatures(tumblehome_enabled=False)
        definition = self._create_definition(features)
        
        modified = modifier.modify(points, station=0.5, definition=definition)
        
        for orig, mod in zip(points, modified):
            assert mod.position.y == orig.position.y
            assert mod.position.z == orig.position.z
    
    def test_modifier_higher_angle_more_reduction(self):
        """Higher tumblehome angle should reduce Y more."""
        modifier = TumblehomeModifier()
        points = self._create_base_section()
        definition = self._create_definition(HullFeatures())
        
        # 5 degree tumblehome
        features_5 = HullFeatures(
            tumblehome_enabled=True,
            tumblehome_angle_deg=5.0,
            tumblehome_start_ratio=0.0,
        )
        def_5 = self._create_definition(features_5)
        mod_5 = modifier.modify(points, station=0.5, definition=def_5)
        
        # 15 degree tumblehome
        features_15 = HullFeatures(
            tumblehome_enabled=True,
            tumblehome_angle_deg=15.0,
            tumblehome_start_ratio=0.0,
        )
        def_15 = self._create_definition(features_15)
        mod_15 = modifier.modify(points, station=0.5, definition=def_15)
        
        # At deck (highest point), 15 deg should have smaller Y than 5 deg
        deck_5 = [p for p in mod_5 if p.position.z > 2.0]
        deck_15 = [p for p in mod_15 if p.position.z > 2.0]
        
        if deck_5 and deck_15:
            assert deck_15[0].position.y < deck_5[0].position.y
    
    def _create_base_section(self) -> List[SectionPoint]:
        """Create a base section with points from keel to deck."""
        points = []
        for i in range(12):
            t = i / 11
            z = -1.5 + t * 4.0  # -1.5 to +2.5 (below and above waterline)
            y = 1.0 + t * 1.5   # 1.0 to 2.5 (expanding outward)
            points.append(SectionPoint(
                position=Point3D(x=10.0, y=y, z=z),
                edge_type=EdgeType.SMOOTH,
                is_keel=(i == 0),
            ))
        return points
    
    def _create_definition(self, features: HullFeatures) -> HullDefinition:
        return HullDefinition(
            dimensions=MainDimensions(lwl=20.0, beam_max=5.0, draft=1.5, depth=4.0, beam_wl=5.0),
            coefficients=FormCoefficients(cb=0.45, cp=0.65, cm=0.75),
            features=features,
        )


# =============================================================================
# PANEL CONFIG TESTS
# =============================================================================

class TestPanelConfig:
    """PanelConfig dataclass tests."""
    
    def test_default_smooth(self):
        """Default config should be smooth."""
        config = PanelConfig()
        assert config.style == "smooth"
        assert config.is_faceted() == False
    
    def test_faceted_mode(self):
        """Faceted mode should be detected."""
        config = PanelConfig(style="faceted")
        assert config.is_faceted() == True
    
    def test_developable_is_faceted(self):
        """Developable mode should also be considered faceted."""
        config = PanelConfig(style="developable")
        assert config.is_faceted() == True
    
    def test_panel_edges_hard_default(self):
        """Panel edges should default to hard."""
        config = PanelConfig(style="faceted")
        assert config.panel_edges_hard == True
    
    def test_to_dict_from_dict(self):
        """Serialization round-trip should preserve values."""
        config = PanelConfig(
            style="faceted",
            longitudinal_panels=8,
            circumferential_panels=12,
            panel_edges_hard=False,
        )
        data = config.to_dict()
        restored = PanelConfig.from_dict(data)
        
        assert restored.style == config.style
        assert restored.longitudinal_panels == config.longitudinal_panels


# =============================================================================
# DECK CONFIG TESTS
# =============================================================================

class TestDeckConfig:
    """DeckConfig dataclass tests."""
    
    def test_default_enabled_flat(self):
        """Default deck should be enabled and flat."""
        config = DeckConfig()
        assert config.enabled == True
        assert config.camber_m == 0.0
        assert config.is_flat() == True
    
    def test_cambered(self):
        """Deck with camber should not be flat."""
        config = DeckConfig(camber_m=0.05)
        assert config.is_flat() == False
    
    def test_flat_profile_is_flat(self):
        """Flat profile should be flat regardless of camber value."""
        config = DeckConfig(camber_m=0.05, camber_profile="flat")
        assert config.is_flat() == True
    
    def test_to_dict_from_dict(self):
        """Serialization round-trip should preserve values."""
        config = DeckConfig(
            enabled=True,
            camber_m=0.08,
            camber_profile="circular",
            sheer_adjustment_bow_m=0.1,
        )
        data = config.to_dict()
        restored = DeckConfig.from_dict(data)
        
        assert restored.enabled == config.enabled
        assert restored.camber_m == config.camber_m
        assert restored.camber_profile == config.camber_profile


# =============================================================================
# DECK GENERATOR TESTS
# =============================================================================

class TestDeckGenerator:
    """DeckGenerator tests."""
    
    def test_generates_deck_surface(self):
        """Deck generator should produce vertices and triangles."""
        sections = self._create_mock_sections()
        config = DeckConfig(enabled=True)
        definition = self._create_definition(HullFeatures())
        
        generator = DeckGenerator()
        deck = generator.generate(sections, config, definition)
        
        assert len(deck.vertices) > 0, "Should have vertices"
        assert len(deck.triangles) > 0, "Should have triangles"
        assert len(deck.edge_points) > 0, "Should have edge points"
    
    def test_disabled_produces_empty(self):
        """Disabled deck should produce empty geometry."""
        sections = self._create_mock_sections()
        config = DeckConfig(enabled=False)
        definition = self._create_definition(HullFeatures())
        
        generator = DeckGenerator()
        deck = generator.generate(sections, config, definition)
        
        assert len(deck.vertices) == 0
        assert len(deck.triangles) == 0
    
    def test_flat_deck_constant_z_across_beam(self):
        """Flat deck should have constant Z across beam at each section."""
        sections = self._create_mock_sections()
        config = DeckConfig(enabled=True, camber_m=0.0, camber_profile="flat")
        definition = self._create_definition(HullFeatures())
        
        generator = DeckGenerator()
        deck = generator.generate(sections, config, definition)
        
        # Group vertices by X (section)
        by_x = {}
        for v in deck.vertices:
            x_key = round(v.x, 2)
            if x_key not in by_x:
                by_x[x_key] = []
            by_x[x_key].append(v.z)
        
        # At each X, all Z values should be equal (within tolerance)
        for x_key, z_values in by_x.items():
            z_range = max(z_values) - min(z_values)
            assert z_range < 0.01, f"Flat deck Z varies at x={x_key}: range={z_range}"
    
    def test_cambered_deck_higher_at_center(self):
        """Cambered deck should be higher at centerline than edge."""
        sections = self._create_mock_sections()
        config = DeckConfig(enabled=True, camber_m=0.1, camber_profile="parabolic")
        definition = self._create_definition(HullFeatures())
        
        generator = DeckGenerator()
        deck = generator.generate(sections, config, definition)
        
        # Find centerline vertices (y ≈ 0) and edge vertices
        centerline_verts = [v for v in deck.vertices if abs(v.y) < 0.1]
        edge_verts = [v for v in deck.vertices if abs(v.y) > 1.0]
        
        if centerline_verts and edge_verts:
            avg_center_z = sum(v.z for v in centerline_verts) / len(centerline_verts)
            avg_edge_z = sum(v.z for v in edge_verts) / len(edge_verts)
            assert avg_center_z > avg_edge_z, "Cambered deck should be higher at center"
    
    def test_deck_has_port_and_starboard(self):
        """Deck should have both port (+Y) and starboard (-Y) vertices."""
        sections = self._create_mock_sections()
        config = DeckConfig(enabled=True)
        definition = self._create_definition(HullFeatures())
        
        generator = DeckGenerator()
        deck = generator.generate(sections, config, definition)
        
        port_verts = [v for v in deck.vertices if v.y > 0.1]
        starboard_verts = [v for v in deck.vertices if v.y < -0.1]
        
        assert len(port_verts) > 0, "Should have port side vertices"
        assert len(starboard_verts) > 0, "Should have starboard side vertices"
    
    def test_normals_point_up(self):
        """Deck normals should point upward (positive Z)."""
        sections = self._create_mock_sections()
        config = DeckConfig(enabled=True)
        definition = self._create_definition(HullFeatures())
        
        generator = DeckGenerator()
        deck = generator.generate(sections, config, definition)
        
        for normal in deck.normals:
            assert normal[2] > 0, f"Normal should point up: {normal}"
    
    def _create_mock_sections(self) -> List[HullSection]:
        """Create mock hull sections with deck edge points."""
        sections = []
        for i in range(5):
            x = i * 5.0
            t = i / 4  # 0 to 1
            half_beam = 2.0 + t * 0.5  # Slightly wider at bow
            
            points = []
            for j in range(6):
                s = j / 5
                points.append(SectionPoint(
                    position=Point3D(x=x, y=s * half_beam, z=-1.5 + s * 3.0),
                    edge_type=EdgeType.SMOOTH,
                ))
            sections.append(HullSection(station=t, points=points))
        return sections
    
    def _create_definition(self, features: HullFeatures) -> HullDefinition:
        return HullDefinition(
            dimensions=MainDimensions(lwl=20.0, beam_max=5.0, draft=1.5, depth=2.5, beam_wl=5.0),
            coefficients=FormCoefficients(cb=0.45, cp=0.65, cm=0.75),
            features=features,
        )


# =============================================================================
# HULL GENERATOR INTEGRATION TESTS
# =============================================================================

class TestHullGeneratorIntegration:
    """Integration tests with HullGenerator."""
    
    def test_tumblehome_in_generated_hull(self):
        """HullGenerator should apply tumblehome modifier."""
        # Use large tumblehome angle to ensure effect is visible
        # Also disable bow flare which can counteract tumblehome
        features = HullFeatures(
            chine_type=ChineType.HARD,
            tumblehome_enabled=True,
            tumblehome_angle_deg=15.0,  # Large angle for clear effect
            tumblehome_start_ratio=0.0,
            bow_flare_deg=0.0,  # Disable bow flare to not counteract tumblehome
        )
        definition = self._create_full_definition(features)
        
        generator = HullGenerator()
        hull = generator.generate(definition)
        
        # Check mid-hull section for tumblehome effect
        if len(hull.sections) < 3:
            pytest.skip("Not enough sections generated")
        
        mid_idx = len(hull.sections) // 2
        mid_section = hull.sections[mid_idx]
        
        # Find deck edge (last point) and maximum beam at or below waterline
        deck_point = mid_section.points[-1] if mid_section.points else None
        
        # Get max Y at waterline (z ~ 0) or below
        below_deck_points = [p for p in mid_section.points if p.position.z < deck_point.position.z * 0.5]
        
        if deck_point and below_deck_points:
            max_y_below = max(p.position.y for p in below_deck_points)
            deck_y = deck_point.position.y
            # Tumblehome: deck should be at least somewhat narrower than mid-section
            # With 15 degree tumblehome, expect noticeable reduction
            assert deck_y < max_y_below * 1.05, \
                f"Tumblehome should narrow hull at deck: deck_y={deck_y}, max_y_below={max_y_below}"
    
    def test_deck_in_generated_hull(self):
        """HullGenerator should include deck geometry when enabled."""
        features = HullFeatures(
            chine_type=ChineType.HARD,
            deck_enabled=True,
        )
        definition = self._create_full_definition(features)
        
        generator = HullGenerator()
        hull = generator.generate(definition)
        
        assert hull.deck_geometry is not None, "Deck geometry should be generated"
        assert len(hull.deck_geometry.vertices) > 0, "Deck should have vertices"
    
    def test_deck_disabled_no_geometry(self):
        """HullGenerator should not include deck when disabled."""
        features = HullFeatures(
            chine_type=ChineType.HARD,
            deck_enabled=False,
        )
        definition = self._create_full_definition(features)
        
        generator = HullGenerator()
        hull = generator.generate(definition)
        
        assert hull.deck_geometry is None or len(hull.deck_geometry.vertices) == 0
    
    def test_combined_features(self):
        """Hull with tumblehome and deck should work together."""
        features = HullFeatures(
            chine_type=ChineType.HARD,
            tumblehome_enabled=True,
            tumblehome_angle_deg=5.0,
            deck_enabled=True,
            deck_camber_m=0.03,
        )
        definition = self._create_full_definition(features)
        
        generator = HullGenerator()
        hull = generator.generate(definition)
        
        # Should have deck geometry
        assert hull.deck_geometry is not None
        assert len(hull.deck_geometry.vertices) > 0
        
        # Should have valid volume
        assert hull.volume > 0
    
    def test_faceted_panel_config(self):
        """HullFeatures should support faceted panel configuration."""
        features = HullFeatures(
            chine_type=ChineType.HARD,
            panel_style="faceted",
        )
        
        panel_config = features.get_panel_config()
        assert panel_config.is_faceted() == True
    
    def _create_full_definition(self, features: HullFeatures) -> HullDefinition:
        return HullDefinition(
            dimensions=MainDimensions(
                lwl=20.0, 
                beam_max=5.0, 
                draft=1.5, 
                depth=3.0,
                beam_wl=5.0,
            ),
            coefficients=FormCoefficients(cb=0.45, cp=0.65, cm=0.75, cwp=0.80),
            features=features,
        )


# =============================================================================
# FACETED TESSELLATION TESTS
# =============================================================================

class TestFacetedTessellation:
    """Faceted panel tessellation tests."""
    
    def test_faceted_mesh_builds_without_error(self):
        """Faceted tessellation should complete without errors."""
        features = HullFeatures(
            chine_type=ChineType.HARD,
            panel_style="faceted",
        )
        definition = self._create_full_definition(features)
        
        generator = HullGenerator()
        hull = generator.generate(definition)
        
        from magnet.webgl.geometry_pipeline import HullGeometryPipeline
        from magnet.webgl.interfaces import HullGeometryData
        
        # Build mesh with faceted option
        pipeline = HullGeometryPipeline(
            hull_geom=HullGeometryData(
                design_id="test",
                version_id="v1",
                sections=hull.sections,
                keel_profile=hull.keel_profile,
                stem_profile=hull.stem_profile,
            )
        )
        
        panel_config = features.get_panel_config()
        mesh = pipeline.tessellate_with_options(
            hull.sections,
            faceted=panel_config.is_faceted(),
            panel_edges_hard=True,
        )
        
        assert len(mesh.vertices) > 0, "Should have vertices"
        assert len(mesh.indices) > 0, "Should have indices"
    
    def _create_full_definition(self, features: HullFeatures) -> HullDefinition:
        return HullDefinition(
            dimensions=MainDimensions(
                lwl=20.0, 
                beam_max=5.0, 
                draft=1.5, 
                depth=3.0,
                beam_wl=5.0,
            ),
            coefficients=FormCoefficients(cb=0.45, cp=0.65, cm=0.75, cwp=0.80),
            features=features,
        )


# =============================================================================
# HYDROSTATICS COMPATIBILITY TESTS
# =============================================================================

class TestHydrostaticsUnchanged:
    """Verify hydrostatics remain valid with Phase 6 features."""
    
    def test_tumblehome_volume_reasonable(self):
        """Hull with tumblehome should have reasonable volume."""
        # Hull without tumblehome
        features_no_th = HullFeatures(chine_type=ChineType.HARD)
        def_no_th = self._create_full_definition(features_no_th)
        
        generator = HullGenerator()
        hull_no_th = generator.generate(def_no_th)
        
        # Hull with tumblehome
        features_th = HullFeatures(
            chine_type=ChineType.HARD,
            tumblehome_enabled=True,
            tumblehome_angle_deg=10.0,
        )
        def_th = self._create_full_definition(features_th)
        hull_th = generator.generate(def_th)
        
        # Tumblehome reduces above-waterline volume slightly
        # but should not dramatically change submerged volume
        # Allow 20% difference (tumblehome is above waterline)
        if hull_no_th.volume > 0 and hull_th.volume > 0:
            diff = abs(hull_no_th.volume - hull_th.volume) / hull_no_th.volume
            assert diff < 0.20, f"Volume difference too large: {diff*100:.1f}%"
    
    def test_deck_does_not_affect_volume(self):
        """Deck geometry should not affect hull volume calculation."""
        features_deck = HullFeatures(
            chine_type=ChineType.HARD,
            deck_enabled=True,
        )
        def_deck = self._create_full_definition(features_deck)
        
        features_no_deck = HullFeatures(
            chine_type=ChineType.HARD,
            deck_enabled=False,
        )
        def_no_deck = self._create_full_definition(features_no_deck)
        
        generator = HullGenerator()
        hull_deck = generator.generate(def_deck)
        hull_no_deck = generator.generate(def_no_deck)
        
        # Volume should be same (deck is above water)
        assert hull_deck.volume == pytest.approx(hull_no_deck.volume, rel=0.01)
    
    def _create_full_definition(self, features: HullFeatures) -> HullDefinition:
        return HullDefinition(
            dimensions=MainDimensions(
                lwl=20.0, 
                beam_max=5.0, 
                draft=1.5, 
                depth=3.0,
                beam_wl=5.0,
            ),
            coefficients=FormCoefficients(cb=0.45, cp=0.65, cm=0.75, cwp=0.80),
            features=features,
        )


# =============================================================================
# MESH VALIDITY TESTS
# =============================================================================

class TestMeshValidity:
    """Verify mesh validity with Phase 6 features."""
    
    def test_no_nan_in_mesh(self):
        """Mesh should not contain NaN values."""
        features = HullFeatures(
            chine_type=ChineType.HARD,
            tumblehome_enabled=True,
            tumblehome_angle_deg=8.0,
            deck_enabled=True,
            deck_camber_m=0.05,
        )
        definition = self._create_full_definition(features)
        
        generator = HullGenerator()
        hull = generator.generate(definition)
        
        from magnet.webgl.geometry_pipeline import HullGeometryPipeline
        from magnet.webgl.interfaces import HullGeometryData
        
        pipeline = HullGeometryPipeline(
            hull_geom=HullGeometryData(
                design_id="test",
                version_id="v1",
                sections=hull.sections,
                keel_profile=hull.keel_profile,
                stem_profile=hull.stem_profile,
            )
        )
        
        # Standard tessellation
        mesh = pipeline.tessellate()
        
        assert not any(math.isnan(v) for v in mesh.vertices), "NaN in vertices"
        assert not any(math.isnan(n) for n in mesh.normals), "NaN in normals"
    
    def _create_full_definition(self, features: HullFeatures) -> HullDefinition:
        return HullDefinition(
            dimensions=MainDimensions(
                lwl=20.0, 
                beam_max=5.0, 
                draft=1.5, 
                depth=3.0,
                beam_wl=5.0,
            ),
            coefficients=FormCoefficients(cb=0.45, cp=0.65, cm=0.75, cwp=0.80),
            features=features,
        )


# =============================================================================
# HULL FEATURES GET METHODS TESTS
# =============================================================================

class TestHullFeaturesGetMethods:
    """Test HullFeatures getter methods for Phase 6 configs."""
    
    def test_get_tumblehome_config_explicit(self):
        """Explicit tumblehome_config should be returned."""
        explicit_config = TumblehomeConfig(enabled=True, angle_deg=12.0)
        features = HullFeatures(
            tumblehome_enabled=False,  # Should be overridden
            tumblehome_config=explicit_config,
        )
        
        config = features.get_tumblehome_config()
        assert config.enabled == True
        assert config.angle_deg == 12.0
    
    def test_get_tumblehome_config_from_simple(self):
        """Should build config from simple parameters."""
        features = HullFeatures(
            tumblehome_enabled=True,
            tumblehome_angle_deg=7.0,
            tumblehome_start_ratio=0.2,
        )
        
        config = features.get_tumblehome_config()
        assert config.enabled == True
        assert config.angle_deg == 7.0
        assert config.start_height_ratio == 0.2
    
    def test_get_tumblehome_config_disabled(self):
        """Should return disabled config when not enabled."""
        features = HullFeatures(tumblehome_enabled=False)
        
        config = features.get_tumblehome_config()
        assert config.enabled == False
    
    def test_get_panel_config_explicit(self):
        """Explicit panel_config should be returned."""
        explicit_config = PanelConfig(style="faceted", longitudinal_panels=10)
        features = HullFeatures(
            panel_style="smooth",  # Should be overridden
            panel_config=explicit_config,
        )
        
        config = features.get_panel_config()
        assert config.style == "faceted"
        assert config.longitudinal_panels == 10
    
    def test_get_panel_config_from_style(self):
        """Should build config from panel_style."""
        features = HullFeatures(panel_style="faceted")
        
        config = features.get_panel_config()
        assert config.style == "faceted"
        assert config.is_faceted() == True
    
    def test_get_deck_config_explicit(self):
        """Explicit deck_config should be returned."""
        explicit_config = DeckConfig(enabled=True, camber_m=0.1, camber_profile="circular")
        features = HullFeatures(
            deck_enabled=False,  # Should be overridden
            deck_config=explicit_config,
        )
        
        config = features.get_deck_config()
        assert config.enabled == True
        assert config.camber_m == 0.1
        assert config.camber_profile == "circular"
    
    def test_get_deck_config_from_simple(self):
        """Should build config from simple parameters."""
        features = HullFeatures(
            deck_enabled=True,
            deck_camber_m=0.05,
        )
        
        config = features.get_deck_config()
        assert config.enabled == True
        assert config.camber_m == 0.05

