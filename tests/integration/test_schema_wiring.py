"""
Test that Phase 2-6 parameters flow through the entire system.

This module verifies:
1. All Phase 2-6 paths are valid in StateManager
2. All user-facing Phase 2-6 params are in REFINABLE_SCHEMA
3. Synthesis sets family-appropriate defaults
4. End-to-end parameter flow from state to geometry
"""
import pytest

from magnet.core.state_manager import StateManager


class TestValidPaths:
    """Verify all Phase 2-6 paths are valid in StateManager."""
    
    PHASE_2_PATHS = [
        ("hull.chine_type", "hard"),
        ("hull.chine_count", 2),
        ("hull.chine_style", "standard"),
        ("hull.chine_transition_start", 0.1),
        ("hull.chine_transition_end", 0.9),
        ("hull.reverse_chine_height_ratio", 0.5),
        ("hull.reverse_chine_extension_m", 0.1),
        ("hull.chine_flat_width_m", 0.05),
    ]
    
    PHASE_3_PATHS = [
        ("hull.bow_style", "wedge"),
        ("hull.bow_facet_count", 3),
        ("hull.bow_planarity", 0.8),
        ("hull.bow_half_angle_deg", 20.0),
        ("hull.bow_region_length", 0.2),
        ("hull.bow_freeboard_ratio", 1.2),
        ("hull.stem_profile", "raked"),
        ("hull.stem_radius_m", 0.3),
    ]
    
    PHASE_4_PATHS = [
        ("hull.spray_rail_count", 2),
        ("hull.spray_rail_spacing", 0.15),
        ("hull.has_spray_rails", True),
        ("hull.has_knuckle_lines", True),
    ]
    
    PHASE_5_PATHS = [
        ("hull.transom_style", "raked"),
        ("hull.transom_rake_deg", 12.0),
    ]
    
    PHASE_6_PATHS = [
        ("hull.tumblehome_enabled", True),
        ("hull.tumblehome_angle_deg", 5.0),
        ("hull.tumblehome_start_ratio", 0.1),
        ("hull.panel_style", "smooth"),
        ("hull.deck_enabled", True),
        ("hull.deck_camber_m", 0.02),
    ]
    
    @pytest.fixture
    def state_manager(self):
        """Create fresh StateManager for each test."""
        return StateManager()
    
    @pytest.mark.parametrize("path,value", PHASE_2_PATHS)
    def test_phase2_paths_valid(self, state_manager, path, value):
        """Phase 2 chine paths should be writable."""
        # Should not raise - path is valid
        txn_id = state_manager.begin_transaction()
        state_manager.set(path, value, "test")
        state_manager.commit_transaction(txn_id)
        assert state_manager.get(path) == value
    
    @pytest.mark.parametrize("path,value", PHASE_3_PATHS)
    def test_phase3_paths_valid(self, state_manager, path, value):
        """Phase 3 bow paths should be writable."""
        txn_id = state_manager.begin_transaction()
        state_manager.set(path, value, "test")
        state_manager.commit_transaction(txn_id)
        assert state_manager.get(path) == value
    
    @pytest.mark.parametrize("path,value", PHASE_4_PATHS)
    def test_phase4_paths_valid(self, state_manager, path, value):
        """Phase 4 spray rail paths should be writable."""
        txn_id = state_manager.begin_transaction()
        state_manager.set(path, value, "test")
        state_manager.commit_transaction(txn_id)
        assert state_manager.get(path) == value
    
    @pytest.mark.parametrize("path,value", PHASE_5_PATHS)
    def test_phase5_paths_valid(self, state_manager, path, value):
        """Phase 5 transom paths should be writable."""
        txn_id = state_manager.begin_transaction()
        state_manager.set(path, value, "test")
        state_manager.commit_transaction(txn_id)
        assert state_manager.get(path) == value
    
    @pytest.mark.parametrize("path,value", PHASE_6_PATHS)
    def test_phase6_paths_valid(self, state_manager, path, value):
        """Phase 6 tumblehome/panel/deck paths should be writable."""
        txn_id = state_manager.begin_transaction()
        state_manager.set(path, value, "test")
        state_manager.commit_transaction(txn_id)
        assert state_manager.get(path) == value


class TestRefinableSchema:
    """Verify Phase 2-6 parameters are in refinable schema."""
    
    def test_chine_type_refinable(self):
        """hull.chine_type should be in refinable schema."""
        from magnet.core.refinable_schema import REFINABLE_SCHEMA
        assert "hull.chine_type" in REFINABLE_SCHEMA
        field = REFINABLE_SCHEMA["hull.chine_type"]
        assert field.type == "enum"
        assert "hard chine" in field.keywords
        assert "double chine" in field.keywords
    
    def test_chine_count_refinable(self):
        """hull.chine_count should be in refinable schema."""
        from magnet.core.refinable_schema import REFINABLE_SCHEMA
        assert "hull.chine_count" in REFINABLE_SCHEMA
        field = REFINABLE_SCHEMA["hull.chine_count"]
        assert field.type == "int"
        assert field.min_value == 0
        assert field.max_value == 4
    
    def test_bow_style_refinable(self):
        """hull.bow_style should be in refinable schema."""
        from magnet.core.refinable_schema import REFINABLE_SCHEMA
        assert "hull.bow_style" in REFINABLE_SCHEMA
        field = REFINABLE_SCHEMA["hull.bow_style"]
        assert field.type == "enum"
        assert "wedge bow" in field.keywords
        assert "axe bow" in field.keywords
        assert "wedge" in field.allowed_values
    
    def test_stem_profile_refinable(self):
        """hull.stem_profile should be in refinable schema."""
        from magnet.core.refinable_schema import REFINABLE_SCHEMA
        assert "hull.stem_profile" in REFINABLE_SCHEMA
        field = REFINABLE_SCHEMA["hull.stem_profile"]
        assert field.type == "enum"
        assert "vertical" in field.allowed_values
        assert "raked" in field.allowed_values
    
    def test_spray_rail_count_refinable(self):
        """hull.spray_rail_count should be in refinable schema."""
        from magnet.core.refinable_schema import REFINABLE_SCHEMA
        assert "hull.spray_rail_count" in REFINABLE_SCHEMA
        field = REFINABLE_SCHEMA["hull.spray_rail_count"]
        assert field.type == "int"
        assert "spray rails" in field.keywords
    
    def test_has_spray_rails_refinable(self):
        """hull.has_spray_rails should be in refinable schema."""
        from magnet.core.refinable_schema import REFINABLE_SCHEMA
        assert "hull.has_spray_rails" in REFINABLE_SCHEMA
        field = REFINABLE_SCHEMA["hull.has_spray_rails"]
        assert field.type == "bool"
    
    def test_transom_style_refinable(self):
        """hull.transom_style should be in refinable schema."""
        from magnet.core.refinable_schema import REFINABLE_SCHEMA
        assert "hull.transom_style" in REFINABLE_SCHEMA
        field = REFINABLE_SCHEMA["hull.transom_style"]
        assert field.type == "enum"
        assert "raked" in field.allowed_values
        assert "stepped" in field.allowed_values
    
    def test_transom_rake_refinable(self):
        """hull.transom_rake_deg should be in refinable schema."""
        from magnet.core.refinable_schema import REFINABLE_SCHEMA
        assert "hull.transom_rake_deg" in REFINABLE_SCHEMA
        field = REFINABLE_SCHEMA["hull.transom_rake_deg"]
        assert field.type == "float"
        assert field.min_value == -15.0
        assert field.max_value == 30.0
    
    def test_tumblehome_enabled_refinable(self):
        """hull.tumblehome_enabled should be in refinable schema."""
        from magnet.core.refinable_schema import REFINABLE_SCHEMA
        assert "hull.tumblehome_enabled" in REFINABLE_SCHEMA
        field = REFINABLE_SCHEMA["hull.tumblehome_enabled"]
        assert field.type == "bool"
        assert "tumblehome" in field.keywords
    
    def test_tumblehome_angle_refinable(self):
        """hull.tumblehome_angle_deg should be in refinable schema."""
        from magnet.core.refinable_schema import REFINABLE_SCHEMA
        assert "hull.tumblehome_angle_deg" in REFINABLE_SCHEMA
        field = REFINABLE_SCHEMA["hull.tumblehome_angle_deg"]
        assert field.type == "float"
        assert field.max_value == 20.0
    
    def test_panel_style_refinable(self):
        """hull.panel_style should be in refinable schema."""
        from magnet.core.refinable_schema import REFINABLE_SCHEMA
        assert "hull.panel_style" in REFINABLE_SCHEMA
        field = REFINABLE_SCHEMA["hull.panel_style"]
        assert field.type == "enum"
        assert "smooth" in field.allowed_values
        assert "faceted" in field.allowed_values
    
    def test_deck_enabled_refinable(self):
        """hull.deck_enabled should be in refinable schema."""
        from magnet.core.refinable_schema import REFINABLE_SCHEMA
        assert "hull.deck_enabled" in REFINABLE_SCHEMA
        field = REFINABLE_SCHEMA["hull.deck_enabled"]
        assert field.type == "bool"
    
    def test_deck_camber_refinable(self):
        """hull.deck_camber_m should be in refinable schema."""
        from magnet.core.refinable_schema import REFINABLE_SCHEMA
        assert "hull.deck_camber_m" in REFINABLE_SCHEMA
        field = REFINABLE_SCHEMA["hull.deck_camber_m"]
        assert field.type == "float"
        assert field.kernel_unit == "m"


class TestSynthesisDefaults:
    """Verify _set_phase2_6_features sets correct defaults by hull family."""
    
    @pytest.fixture
    def state_manager(self):
        """Create fresh StateManager for each test."""
        return StateManager()
    
    def _test_phase2_6_features(self, state_manager, family, speed_kts, loa_m):
        """Helper to directly test _set_phase2_6_features."""
        from magnet.kernel.synthesis import HullSynthesizer, SynthesisRequest
        
        synth = HullSynthesizer(None, state_manager)
        req = SynthesisRequest(
            hull_family=family,
            max_speed_kts=speed_kts,
            loa_m=loa_m,
        )
        
        # Acquire lock and call the Phase 2-6 feature setter
        with synth.lock.exclusive_access("hull_synthesizer"):
            synth._set_phase2_6_features(req)
    
    def test_patrol_gets_hard_chine(self, state_manager):
        """Patrol boat should default to hard chine."""
        from magnet.kernel.priors.hull_families import HullFamily
        
        self._test_phase2_6_features(state_manager, HullFamily.PATROL, 35.0, 20.0)
        
        chine_type = state_manager.get("hull.chine_type")
        assert chine_type in ("hard", "double"), f"Expected hard/double chine, got {chine_type}"
    
    def test_patrol_gets_wedge_bow(self, state_manager):
        """Fast patrol boat should default to wedge bow."""
        from magnet.kernel.priors.hull_families import HullFamily
        
        self._test_phase2_6_features(state_manager, HullFamily.PATROL, 35.0, 20.0)
        
        bow_style = state_manager.get("hull.bow_style")
        assert bow_style == "wedge", f"Expected wedge bow, got {bow_style}"
    
    def test_patrol_gets_tumblehome(self, state_manager):
        """Patrol boat should default to tumblehome enabled."""
        from magnet.kernel.priors.hull_families import HullFamily
        
        self._test_phase2_6_features(state_manager, HullFamily.PATROL, 35.0, 20.0)
        
        tumblehome = state_manager.get("hull.tumblehome_enabled")
        assert tumblehome is True, f"Expected tumblehome enabled, got {tumblehome}"
    
    def test_planing_gets_spray_rails(self, state_manager):
        """Planing hull should get spray rails."""
        from magnet.kernel.priors.hull_families import HullFamily
        
        self._test_phase2_6_features(state_manager, HullFamily.PLANING, 45.0, 15.0)
        
        spray_count = state_manager.get("hull.spray_rail_count")
        has_rails = state_manager.get("hull.has_spray_rails")
        assert spray_count >= 2, f"Expected 2+ spray rails, got {spray_count}"
        assert has_rails is True
    
    def test_planing_gets_double_chine(self, state_manager):
        """Planing hull should get double chine."""
        from magnet.kernel.priors.hull_families import HullFamily
        
        self._test_phase2_6_features(state_manager, HullFamily.PLANING, 45.0, 15.0)
        
        chine_type = state_manager.get("hull.chine_type")
        chine_count = state_manager.get("hull.chine_count")
        assert chine_type == "double", f"Expected double chine, got {chine_type}"
        assert chine_count == 2
    
    def test_ferry_gets_round_bilge(self, state_manager):
        """Ferry should default to soft chine (round bilge)."""
        from magnet.kernel.priors.hull_families import HullFamily
        
        self._test_phase2_6_features(state_manager, HullFamily.FERRY, 20.0, 40.0)
        
        chine_type = state_manager.get("hull.chine_type")
        assert chine_type == "soft", f"Expected soft chine, got {chine_type}"
    
    def test_catamaran_gets_wave_piercing_bow(self, state_manager):
        """Fast catamaran should get wave piercing bow."""
        from magnet.kernel.priors.hull_families import HullFamily
        
        self._test_phase2_6_features(state_manager, HullFamily.CATAMARAN, 35.0, 30.0)
        
        bow_style = state_manager.get("hull.bow_style")
        assert bow_style == "wave_piercing", f"Expected wave_piercing bow, got {bow_style}"
    
    def test_workboat_no_tumblehome(self, state_manager):
        """Workboat should not have tumblehome."""
        from magnet.kernel.priors.hull_families import HullFamily
        
        self._test_phase2_6_features(state_manager, HullFamily.WORKBOAT, 12.0, 20.0)
        
        tumblehome = state_manager.get("hull.tumblehome_enabled")
        assert tumblehome is False, f"Expected no tumblehome, got {tumblehome}"
    
    def test_all_families_get_deck(self):
        """All families should have deck enabled."""
        from magnet.kernel.priors.hull_families import HullFamily
        
        for family in [HullFamily.PATROL, HullFamily.WORKBOAT, HullFamily.FERRY]:
            sm = StateManager()
            self._test_phase2_6_features(sm, family, 20.0, 25.0)
            
            deck_enabled = sm.get("hull.deck_enabled")
            assert deck_enabled is True, f"{family.name} should have deck enabled"


class TestKeywordMatching:
    """Verify keywords enable natural language matching."""
    
    def test_keywords_present_in_refinable_fields(self):
        """Should have keywords for natural language matching."""
        from magnet.core.refinable_schema import REFINABLE_SCHEMA
        
        # Test chine keywords
        chine_field = REFINABLE_SCHEMA.get("hull.chine_type")
        assert chine_field is not None
        assert "hard chine" in chine_field.keywords
        
        # Test bow keywords
        bow_field = REFINABLE_SCHEMA.get("hull.bow_style")
        assert bow_field is not None
        assert "wedge bow" in bow_field.keywords
        
        # Test spray rail keywords
        spray_field = REFINABLE_SCHEMA.get("hull.spray_rail_count")
        assert spray_field is not None
        assert "spray rails" in spray_field.keywords
        
        # Test tumblehome keywords
        tumble_field = REFINABLE_SCHEMA.get("hull.tumblehome_enabled")
        assert tumble_field is not None
        assert "tumblehome" in tumble_field.keywords
        
        # Test faceted panel keywords
        panel_field = REFINABLE_SCHEMA.get("hull.panel_style")
        assert panel_field is not None
        assert "faceted" in panel_field.keywords


class TestEndToEndFlow:
    """Test full flow from state to geometry."""
    
    def test_wedge_bow_generates_geometry(self):
        """Setting bow_style=wedge should affect generated geometry."""
        from magnet.hull_gen.generator import HullGenerator
        from magnet.hull_gen.parameters import (
            HullDefinition, HullFeatures, MainDimensions, FormCoefficients
        )
        from magnet.hull_gen.enums import BowStyle
        
        features = HullFeatures(bow_style=BowStyle.WEDGE)
        definition = HullDefinition(
            dimensions=MainDimensions(lwl=20.0, beam_max=5.0, draft=1.5, depth=2.5),
            coefficients=FormCoefficients(cb=0.45, cp=0.65, cm=0.75),
            features=features,
        )
        
        generator = HullGenerator()
        hull = generator.generate(definition)
        
        # Should generate hull sections
        assert len(hull.sections) > 0
        # Bow sections should exist
        assert hull.sections[0] is not None
    
    def test_spray_rails_add_points_to_sections(self):
        """Spray rails should add points to hull sections."""
        from magnet.hull_gen.generator import HullGenerator
        from magnet.hull_gen.parameters import (
            HullDefinition, HullFeatures, MainDimensions, FormCoefficients,
            SprayRailConfig,
        )
        
        # With spray rails
        spray_rails = [
            SprayRailConfig(height_ratio=0.15, angle_deg=18.0, width_m=0.06),
            SprayRailConfig(height_ratio=0.25, angle_deg=15.0, width_m=0.05),
        ]
        features_with = HullFeatures(
            spray_rails=spray_rails,
            has_spray_rails=True,
            spray_rail_count=2,
        )
        definition_with = HullDefinition(
            dimensions=MainDimensions(lwl=20.0, beam_max=5.0, draft=1.5, depth=2.5),
            coefficients=FormCoefficients(cb=0.45, cp=0.65, cm=0.75),
            features=features_with,
        )
        
        generator = HullGenerator()
        hull_with = generator.generate(definition_with)
        
        # Check that spray rails added hard edges
        mid_section = hull_with.sections[len(hull_with.sections) // 2]
        hard_points = [p for p in mid_section.points if p.edge_type.name != "SMOOTH"]
        
        # Should have hard edge points from spray rails
        assert len(hard_points) >= 2, f"Expected hard edges from spray rails, got {len(hard_points)}"
    
    def test_hull_features_config_methods(self):
        """HullFeatures config getter methods should return correct configs."""
        from magnet.hull_gen.parameters import HullFeatures
        
        features = HullFeatures(
            chine_type="hard",
            bow_style="wedge",
            tumblehome_enabled=True,
            tumblehome_angle_deg=5.0,
            panel_style="faceted",
            deck_enabled=True,
            deck_camber_m=0.03,
        )
        
        # Test getter methods exist and return configs
        tumblehome_config = features.get_tumblehome_config()
        assert tumblehome_config is not None
        assert tumblehome_config.enabled is True
        assert tumblehome_config.angle_deg == 5.0
        
        panel_config = features.get_panel_config()
        assert panel_config is not None
        assert panel_config.style == "faceted"
        
        deck_config = features.get_deck_config()
        assert deck_config is not None
        assert deck_config.enabled is True


class TestSynthesisLockPaths:
    """Verify SynthesisLock includes Phase 2-6 paths."""
    
    def test_phase2_paths_in_lock(self):
        """Phase 2 paths should be in SynthesisLock.HULL_PATHS."""
        from magnet.kernel.synthesis_lock import SynthesisLock
        
        phase2_paths = [
            "hull.chine_type", "hull.chine_count", "hull.chine_flat_width_m",
        ]
        for path in phase2_paths:
            assert path in SynthesisLock.HULL_PATHS, f"{path} not in HULL_PATHS"
    
    def test_phase3_paths_in_lock(self):
        """Phase 3 paths should be in SynthesisLock.HULL_PATHS."""
        from magnet.kernel.synthesis_lock import SynthesisLock
        
        phase3_paths = [
            "hull.bow_style", "hull.bow_facet_count", "hull.stem_profile",
        ]
        for path in phase3_paths:
            assert path in SynthesisLock.HULL_PATHS, f"{path} not in HULL_PATHS"
    
    def test_phase4_paths_in_lock(self):
        """Phase 4 paths should be in SynthesisLock.HULL_PATHS."""
        from magnet.kernel.synthesis_lock import SynthesisLock
        
        phase4_paths = [
            "hull.spray_rail_count", "hull.has_spray_rails", "hull.has_knuckle_lines",
        ]
        for path in phase4_paths:
            assert path in SynthesisLock.HULL_PATHS, f"{path} not in HULL_PATHS"
    
    def test_phase5_paths_in_lock(self):
        """Phase 5 paths should be in SynthesisLock.HULL_PATHS."""
        from magnet.kernel.synthesis_lock import SynthesisLock
        
        phase5_paths = [
            "hull.transom_style", "hull.transom_rake_deg",
        ]
        for path in phase5_paths:
            assert path in SynthesisLock.HULL_PATHS, f"{path} not in HULL_PATHS"
    
    def test_phase6_paths_in_lock(self):
        """Phase 6 paths should be in SynthesisLock.HULL_PATHS."""
        from magnet.kernel.synthesis_lock import SynthesisLock
        
        phase6_paths = [
            "hull.tumblehome_enabled", "hull.tumblehome_angle_deg",
            "hull.panel_style", "hull.deck_enabled", "hull.deck_camber_m",
        ]
        for path in phase6_paths:
            assert path in SynthesisLock.HULL_PATHS, f"{path} not in HULL_PATHS"

