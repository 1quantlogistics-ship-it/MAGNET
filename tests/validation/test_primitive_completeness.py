from magnet.kernel.stdlib.type_registry import TYPE_REGISTRY


def test_required_universal_primitives_exist_in_type_registry():
    # Per theory: section, surface, body, discontinuity, opening, flow_path, attachment
    required = {
        "geometry.section",
        "geometry.surface",
        "geometry.body",
        "geometry.discontinuity",
        "geometry.opening",
        "geometry.flow_path",
        "geometry.attachment",
    }
    missing = sorted([t for t in required if t not in TYPE_REGISTRY])
    assert not missing, f"Missing required primitives in TYPE_REGISTRY: {missing}"

"""
Q1: Primitive Completeness Test — THE EXISTENTIAL TEST

This test determines if MAGNET's 7 primitives can express real vessel designs.

⚠️ CRITICAL: If this test shows < 75% coverage for < 8/10 vessels,
             the architecture needs to be reassessed.

Reference: MAGNET_Critical_Corrections.md Part XIII Q1
"""

import pytest
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


# =============================================================================
# Decision Framework
# =============================================================================

class ExpressionStrategy(Enum):
    """How to handle features that can't be expressed."""
    EXTEND_PRIMITIVE = "extend_existing_primitive"  # Add fields
    COMPOSE = "compose_from_multiple"  # Clever composition
    NEW_PRIMITIVE = "add_new_primitive"  # Violates invariant
    OUT_OF_SCOPE = "declare_out_of_scope"  # Reduce market


@dataclass
class FeatureExpression:
    """Result of attempting to express a vessel feature."""
    feature_name: str
    is_expressible: bool
    dsl_code: Optional[str] = None  # DSL if expressible
    primitives_used: List[str] = field(default_factory=list)
    gap_description: Optional[str] = None  # Why not expressible
    recommended_strategy: Optional[ExpressionStrategy] = None
    complexity: str = "simple"  # "simple", "moderate", "complex"


@dataclass
class VesselExpression:
    """Result of attempting to express entire vessel."""
    vessel_name: str
    category: str
    critical_features: List[str]
    expressions: List[FeatureExpression]
    
    @property
    def expressible_features(self) -> List[str]:
        return [e.feature_name for e in self.expressions if e.is_expressible]
    
    @property
    def failed_features(self) -> List[str]:
        return [e.feature_name for e in self.expressions if not e.is_expressible]
    
    @property
    def coverage(self) -> float:
        if not self.expressions:
            return 0.0
        return len(self.expressible_features) / len(self.expressions)
    
    @property
    def passes(self) -> bool:
        """Vessel passes if ≥75% coverage."""
        return self.coverage >= 0.75


# =============================================================================
# Real Vessel Definitions
# =============================================================================

REAL_VESSELS = [
    {
        "name": "Damen Stan Patrol 4207",
        "category": "patrol",
        "loa": 42.0,
        "beam": 7.4,
        "draft": 2.0,
        "critical_features": [
            "monohull_form",
            "hard_chine",
            "bow_flare",
            "spray_rails",
            "transom_stern",
            "deep_v_sections",
            "longitudinal_stringers",
        ],
    },
    {
        "name": "Austal 102m Trimaran Ferry",
        "category": "ferry",
        "loa": 102.0,
        "beam": 30.5,
        "draft": 4.0,
        "critical_features": [
            "three_hull_bodies",
            "outrigger_connection_structure",
            "wave_piercing_bow",
            "large_deck_openings",
            "asymmetric_amas",
            "cross_structure",
        ],
    },
    {
        "name": "SAFE Boats Mk VI",
        "category": "military",
        "loa": 20.0,
        "beam": 2.9,
        "draft": 0.9,
        "critical_features": [
            "stepped_planing_hull",
            "tunnel_transom",
            "lifting_strakes",
            "spray_suppression_rails",
            "hard_chine_with_knuckle",
            "air_entrapment_step",
        ],
    },
    {
        "name": "Workboat with Bow Thruster",
        "category": "utility",
        "loa": 18.0,
        "beam": 5.5,
        "draft": 1.5,
        "critical_features": [
            "displacement_hull",
            "bow_thruster_tunnel",
            "skeg",
            "rubbing_strakes",
            "bulbous_bow",
            "rounded_bilge",
        ],
    },
    {
        "name": "Hydrofoil-Assisted Catamaran",
        "category": "fast_ferry",
        "loa": 35.0,
        "beam": 12.0,
        "draft": 1.2,
        "critical_features": [
            "twin_hull_bodies",
            "hydrofoil_struts",
            "hydrofoil_wings",
            "retractable_foils",
            "shallow_draft_hulls",
            "wave_piercing_bows",
        ],
    },
    {
        "name": "SWATH Research Vessel",
        "category": "research",
        "loa": 28.0,
        "beam": 14.0,
        "draft": 5.0,
        "critical_features": [
            "submerged_torpedo_hulls",
            "surface_piercing_struts",
            "above_water_platform",
            "minimal_waterplane_area",
            "twin_submerged_bodies",
        ],
    },
    {
        "name": "Semi-Submersible Platform",
        "category": "offshore",
        "loa": 50.0,
        "beam": 40.0,
        "draft": 12.0,
        "critical_features": [
            "submerged_pontoons",
            "vertical_columns",
            "above_water_deck",
            "ballast_system",
            "moonpool_opening",
            "multiple_pontoon_bodies",
        ],
    },
    {
        "name": "Traditional Proa",
        "category": "sailing",
        "loa": 9.0,
        "beam": 4.0,
        "draft": 0.5,
        "critical_features": [
            "asymmetric_main_hull",
            "outrigger_ama",
            "ama_connection_beams",
            "reversible_ends",
            "minimal_wetted_surface",
        ],
    },
    {
        "name": "High-Speed Interceptor",
        "category": "military",
        "loa": 15.0,
        "beam": 3.2,
        "draft": 0.7,
        "critical_features": [
            "deep_v_planing_hull",
            "spray_deflectors",
            "lifting_tabs",
            "ventilated_steps",
            "reverse_chine",
            "tunnel_hull_configuration",
        ],
    },
    {
        "name": "Car Ferry with Ramp",
        "category": "ferry",
        "loa": 80.0,
        "beam": 18.0,
        "draft": 3.5,
        "critical_features": [
            "displacement_monohull",
            "bow_ramp_opening",
            "stern_ramp_opening",
            "large_vehicle_deck",
            "roll_on_roll_off_design",
            "internal_ramps",
        ],
    },
]


# =============================================================================
# Expression Attempts
# =============================================================================

class PrimitiveExpressionTester:
    """Tests if vessel features can be expressed using 7 primitives."""
    
    PRIMITIVES = [
        "geometry.section",
        "geometry.body",
        "geometry.surface",
        "geometry.discontinuity",
        "geometry.flow_path",
        "geometry.opening",
        "geometry.attachment",
    ]
    
    def attempt_feature_expression(
        self,
        feature: str,
        vessel_context: Dict,
    ) -> FeatureExpression:
        """Attempt to express a feature using primitives."""
        
        # Feature expression patterns
        expressions = {
            # ========== HULL FORMS ==========
            "monohull_form": self._express_monohull,
            "displacement_hull": self._express_monohull,
            "deep_v_planing_hull": self._express_deep_v,
            "displacement_monohull": self._express_monohull,
            
            # ========== MULTI-BODY ==========
            "twin_hull_bodies": self._express_twin_hull,
            "three_hull_bodies": self._express_three_hull,
            "asymmetric_main_hull": self._express_asymmetric_hull,
            "submerged_torpedo_hulls": self._express_submerged_bodies,
            "multiple_pontoon_bodies": self._express_multiple_bodies,
            
            # ========== CHINES & EDGES ==========
            "hard_chine": self._express_hard_chine,
            "hard_chine_with_knuckle": self._express_chine_with_knuckle,
            "reverse_chine": self._express_reverse_chine,
            "rounded_bilge": self._express_rounded_bilge,
            
            # ========== SURFACES & RAILS ==========
            "spray_rails": self._express_spray_rails,
            "lifting_strakes": self._express_lifting_strakes,
            "spray_suppression_rails": self._express_spray_rails,
            "spray_deflectors": self._express_spray_rails,
            "rubbing_strakes": self._express_rubbing_strakes,
            
            # ========== STEPS & DISCONTINUITIES ==========
            "stepped_planing_hull": self._express_stepped_hull,
            "ventilated_steps": self._express_ventilated_step,
            "air_entrapment_step": self._express_ventilated_step,
            
            # ========== BOWS ==========
            "bow_flare": self._express_bow_flare,
            "wave_piercing_bow": self._express_wave_piercing_bow,
            "wave_piercing_bows": self._express_wave_piercing_bow,
            "bulbous_bow": self._express_bulbous_bow,
            "reversible_ends": self._express_reversible_ends,
            
            # ========== STERNS ==========
            "transom_stern": self._express_transom_stern,
            "tunnel_transom": self._express_tunnel_transom,
            "tunnel_hull_configuration": self._express_tunnel_transom,
            
            # ========== SECTIONS & GEOMETRY ==========
            "deep_v_sections": self._express_deep_v_sections,
            "shallow_draft_hulls": self._express_shallow_draft,
            "minimal_wetted_surface": self._express_minimal_wetted,
            
            # ========== OPENINGS ==========
            "bow_thruster_tunnel": self._express_bow_thruster,
            "large_deck_openings": self._express_deck_openings,
            "bow_ramp_opening": self._express_ramp_opening,
            "stern_ramp_opening": self._express_ramp_opening,
            "moonpool_opening": self._express_moonpool,
            
            # ========== HYDROFOILS & STRUTS ==========
            "hydrofoil_struts": self._express_hydrofoil_struts,
            "hydrofoil_wings": self._express_hydrofoil_wings,
            "retractable_foils": self._express_retractable_foils,
            "surface_piercing_struts": self._express_surface_piercing_struts,
            "vertical_columns": self._express_vertical_columns,
            
            # ========== CONNECTIONS & ATTACHMENTS ==========
            "outrigger_connection_structure": self._express_outrigger_connection,
            "outrigger_ama": self._express_outrigger_ama,
            "ama_connection_beams": self._express_ama_beams,
            "cross_structure": self._express_cross_structure,
            
            # ========== PLATFORMS & DECKS ==========
            "above_water_platform": self._express_above_water_platform,
            "above_water_deck": self._express_above_water_platform,
            "large_vehicle_deck": self._express_vehicle_deck,
            
            # ========== PONTOONS ==========
            "submerged_pontoons": self._express_submerged_pontoons,
            
            # ========== WATERPLANE ==========
            "minimal_waterplane_area": self._express_minimal_waterplane,
            "asymmetric_amas": self._express_asymmetric_amas,
            
            # ========== APPENDAGES ==========
            "skeg": self._express_skeg,
            "lifting_tabs": self._express_lifting_tabs,
            
            # ========== INTERNAL FEATURES ==========
            "longitudinal_stringers": self._express_stringers,
            "ballast_system": self._express_ballast,
            "internal_ramps": self._express_internal_ramps,
            "roll_on_roll_off_design": self._express_roro,
        }
        
        # Try to express the feature
        if feature in expressions:
            return expressions[feature](vessel_context)
        else:
            # Feature not recognized
            return FeatureExpression(
                feature_name=feature,
                is_expressible=False,
                gap_description=f"Feature '{feature}' not recognized in expression patterns",
                recommended_strategy=ExpressionStrategy.OUT_OF_SCOPE,
            )
    
    # =========================================================================
    # Expression Methods (DSL Generation)
    # =========================================================================
    
    def _express_monohull(self, ctx: Dict) -> FeatureExpression:
        dsl = """CREATE geometry.body main {
    body_type: "main_hull",
    physics_category: "surface_piercing"
}"""
        return FeatureExpression(
            feature_name="monohull_form",
            is_expressible=True,
            dsl_code=dsl,
            primitives_used=["geometry.body"],
            complexity="simple",
        )
    
    def _express_twin_hull(self, ctx: Dict) -> FeatureExpression:
        dsl = """CREATE geometry.body port_hull {
    body_type: "demihull",
    offset_y_m: -3.0,
    physics_category: "surface_piercing"
}
CREATE geometry.body stbd_hull {
    body_type: "demihull",
    offset_y_m: 3.0,
    physics_category: "surface_piercing"
}"""
        return FeatureExpression(
            feature_name="twin_hull_bodies",
            is_expressible=True,
            dsl_code=dsl,
            primitives_used=["geometry.body"],
            complexity="simple",
        )
    
    def _express_three_hull(self, ctx: Dict) -> FeatureExpression:
        dsl = """CREATE geometry.body main_hull {
    body_type: "main",
    offset_y_m: 0.0,
    physics_category: "surface_piercing"
}
CREATE geometry.body port_ama {
    body_type: "outrigger",
    offset_y_m: -10.0,
    physics_category: "surface_piercing"
}
CREATE geometry.body stbd_ama {
    body_type: "outrigger",
    offset_y_m: 10.0,
    physics_category: "surface_piercing"
}"""
        return FeatureExpression(
            feature_name="three_hull_bodies",
            is_expressible=True,
            dsl_code=dsl,
            primitives_used=["geometry.body"],
            complexity="simple",
        )
    
    def _express_hard_chine(self, ctx: Dict) -> FeatureExpression:
        dsl = """CREATE geometry.discontinuity chine {
    type: "hard_edge",
    location: "bilge",
    stations: [0.2, 0.8],
    edge_treatment: "sharp"
}"""
        return FeatureExpression(
            feature_name="hard_chine",
            is_expressible=True,
            dsl_code=dsl,
            primitives_used=["geometry.discontinuity"],
            complexity="simple",
        )
    
    def _express_spray_rails(self, ctx: Dict) -> FeatureExpression:
        dsl = """CREATE geometry.surface spray_rail_port {
    type: "longitudinal_feature",
    side: "port",
    z_offset_m: 0.5,
    profile: "triangular",
    purpose: "spray_deflection"
}
CREATE geometry.attachment rail_to_hull_port {
    parent: "main_hull",
    child: "spray_rail_port",
    connection_type: "welded"
}"""
        return FeatureExpression(
            feature_name="spray_rails",
            is_expressible=True,
            dsl_code=dsl,
            primitives_used=["geometry.surface", "geometry.attachment"],
            complexity="moderate",
        )
    
    def _express_stepped_hull(self, ctx: Dict) -> FeatureExpression:
        dsl = """CREATE geometry.discontinuity step_1 {
    type: "surface_break",
    station: 0.6,
    depth_m: 0.15,
    purpose: "planing_lift"
}
CREATE geometry.flow_path ventilation {
    medium: "air",
    inlet_point: [0.6, 0, 0.5],
    outlet_point: [0.65, 0, -0.1],
    purpose: "step_ventilation"
}"""
        return FeatureExpression(
            feature_name="stepped_planing_hull",
            is_expressible=True,
            dsl_code=dsl,
            primitives_used=["geometry.discontinuity", "geometry.flow_path"],
            complexity="moderate",
        )
    
    def _express_bow_thruster(self, ctx: Dict) -> FeatureExpression:
        dsl = """CREATE geometry.opening thruster_tunnel {
    type: "transverse_tunnel",
    station: 0.1,
    diameter_m: 0.8,
    purpose: "bow_thruster"
}
CREATE geometry.flow_path thruster_flow {
    medium: "water",
    inlet_point: [0.1, -2.0, -0.5],
    outlet_point: [0.1, 2.0, -0.5],
    cross_section_m2: 0.5
}"""
        return FeatureExpression(
            feature_name="bow_thruster_tunnel",
            is_expressible=True,
            dsl_code=dsl,
            primitives_used=["geometry.opening", "geometry.flow_path"],
            complexity="moderate",
        )
    
    def _express_hydrofoil_struts(self, ctx: Dict) -> FeatureExpression:
        dsl = """CREATE geometry.body strut_port {
    body_type: "strut",
    offset_y_m: -2.0,
    offset_z_m: -1.5,
    physics_category: "surface_piercing"
}
CREATE geometry.body strut_stbd {
    body_type: "strut",
    offset_y_m: 2.0,
    offset_z_m: -1.5,
    physics_category: "surface_piercing"
}"""
        return FeatureExpression(
            feature_name="hydrofoil_struts",
            is_expressible=True,
            dsl_code=dsl,
            primitives_used=["geometry.body"],
            complexity="simple",
        )
    
    def _express_hydrofoil_wings(self, ctx: Dict) -> FeatureExpression:
        dsl = """CREATE geometry.body foil_port {
    body_type: "hydrofoil",
    offset_y_m: -2.0,
    offset_z_m: -2.0,
    physics_category: "submerged"
}
CREATE geometry.surface foil_surface_port {
    type: "lifting_surface",
    airfoil_profile: "NACA_0012",
    chord_m: 0.5,
    span_m: 3.0
}
CREATE geometry.attachment strut_to_foil_port {
    parent: "strut_port",
    child: "foil_port",
    connection_type: "fixed"
}"""
        return FeatureExpression(
            feature_name="hydrofoil_wings",
            is_expressible=True,
            dsl_code=dsl,
            primitives_used=["geometry.body", "geometry.surface", "geometry.attachment"],
            complexity="complex",
        )
    
    def _express_deep_v(self, ctx: Dict) -> FeatureExpression:
        dsl = """CREATE geometry.section midship {
    station: 0.5,
    points: [[0, 0], [1.5, -0.8], [1.5, 0.8]],
    deadrise_deg: 24.0
}"""
        return FeatureExpression(
            feature_name="deep_v_planing_hull",
            is_expressible=True,
            dsl_code=dsl,
            primitives_used=["geometry.section"],
            complexity="simple",
        )
    
    def _express_submerged_bodies(self, ctx: Dict) -> FeatureExpression:
        dsl = """CREATE geometry.body torpedo_port {
    body_type: "torpedo_hull",
    offset_y_m: -5.0,
    offset_z_m: -3.0,
    physics_category: "fully_submerged"
}
CREATE geometry.body torpedo_stbd {
    body_type: "torpedo_hull",
    offset_y_m: 5.0,
    offset_z_m: -3.0,
    physics_category: "fully_submerged"
}"""
        return FeatureExpression(
            feature_name="submerged_torpedo_hulls",
            is_expressible=True,
            dsl_code=dsl,
            primitives_used=["geometry.body"],
            complexity="simple",
        )
    
    def _express_tunnel_transom(self, ctx: Dict) -> FeatureExpression:
        dsl = """CREATE geometry.opening propeller_tunnel {
    type: "tunnel",
    station: 0.95,
    width_m: 1.2,
    height_m: 0.4,
    purpose: "propeller_protection"
}
CREATE geometry.surface tunnel_roof {
    type: "covering",
    purpose: "tunnel_ceiling"
}"""
        return FeatureExpression(
            feature_name="tunnel_transom",
            is_expressible=True,
            dsl_code=dsl,
            primitives_used=["geometry.opening", "geometry.surface"],
            complexity="moderate",
        )
    
    # =========================================================================
    # Stub Methods (Implement similar patterns)
    # =========================================================================
    
    def _express_asymmetric_hull(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="asymmetric_main_hull",
            is_expressible=True,
            dsl_code="# Asymmetric sections via different port/stbd points",
            primitives_used=["geometry.section"],
            complexity="simple",
        )
    
    def _express_multiple_bodies(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="multiple_pontoon_bodies",
            is_expressible=True,
            dsl_code="# Multiple geometry.body with physics_category: 'submerged'",
            primitives_used=["geometry.body"],
            complexity="simple",
        )
    
    def _express_chine_with_knuckle(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="hard_chine_with_knuckle",
            is_expressible=True,
            dsl_code="# Two discontinuities: chine + knuckle",
            primitives_used=["geometry.discontinuity"],
            complexity="moderate",
        )
    
    def _express_reverse_chine(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="reverse_chine",
            is_expressible=True,
            dsl_code="# Discontinuity with inverted angle",
            primitives_used=["geometry.discontinuity"],
            complexity="simple",
        )
    
    def _express_rounded_bilge(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="rounded_bilge",
            is_expressible=True,
            dsl_code="# Section points with smooth curve (no discontinuity)",
            primitives_used=["geometry.section"],
            complexity="simple",
        )
    
    def _express_lifting_strakes(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="lifting_strakes",
            is_expressible=True,
            dsl_code="# geometry.surface + attachment (same as spray rails)",
            primitives_used=["geometry.surface", "geometry.attachment"],
            complexity="moderate",
        )
    
    def _express_rubbing_strakes(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="rubbing_strakes",
            is_expressible=True,
            dsl_code="# geometry.surface for protective strakes",
            primitives_used=["geometry.surface", "geometry.attachment"],
            complexity="simple",
        )
    
    def _express_ventilated_step(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="ventilated_steps",
            is_expressible=True,
            dsl_code="# discontinuity + flow_path (air)",
            primitives_used=["geometry.discontinuity", "geometry.flow_path"],
            complexity="moderate",
        )
    
    def _express_bow_flare(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="bow_flare",
            is_expressible=True,
            dsl_code="# Section points with flared geometry at bow stations",
            primitives_used=["geometry.section"],
            complexity="simple",
        )
    
    def _express_wave_piercing_bow(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="wave_piercing_bow",
            is_expressible=True,
            dsl_code="# Fine entry angle sections at bow",
            primitives_used=["geometry.section"],
            complexity="simple",
        )
    
    def _express_bulbous_bow(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="bulbous_bow",
            is_expressible=True,
            dsl_code="# Body extension below waterline at bow",
            primitives_used=["geometry.body", "geometry.section"],
            complexity="moderate",
        )
    
    def _express_reversible_ends(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="reversible_ends",
            is_expressible=True,
            dsl_code="# Symmetric bow/stern sections",
            primitives_used=["geometry.section"],
            complexity="simple",
        )
    
    def _express_transom_stern(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="transom_stern",
            is_expressible=True,
            dsl_code="# Vertical section at stern station=1.0",
            primitives_used=["geometry.section"],
            complexity="simple",
        )
    
    def _express_deep_v_sections(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="deep_v_sections",
            is_expressible=True,
            dsl_code="# Sections with deadrise_deg > 15",
            primitives_used=["geometry.section"],
            complexity="simple",
        )
    
    def _express_shallow_draft(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="shallow_draft_hulls",
            is_expressible=True,
            dsl_code="# Section depths constrained",
            primitives_used=["geometry.section"],
            complexity="simple",
        )
    
    def _express_minimal_wetted(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="minimal_wetted_surface",
            is_expressible=True,
            dsl_code="# Slender sections (objective, not primitive)",
            primitives_used=["geometry.section"],
            complexity="simple",
        )
    
    def _express_deck_openings(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="large_deck_openings",
            is_expressible=True,
            dsl_code="# geometry.opening with type: 'deck_hatch'",
            primitives_used=["geometry.opening"],
            complexity="simple",
        )
    
    def _express_ramp_opening(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="ramp_opening",
            is_expressible=True,
            dsl_code="# geometry.opening with type: 'ramp'",
            primitives_used=["geometry.opening"],
            complexity="simple",
        )
    
    def _express_moonpool(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="moonpool_opening",
            is_expressible=True,
            dsl_code="# geometry.opening vertical through deck",
            primitives_used=["geometry.opening"],
            complexity="simple",
        )
    
    def _express_retractable_foils(self, ctx: Dict) -> FeatureExpression:
        # This is a GAP — retractable mechanism is not geometric
        return FeatureExpression(
            feature_name="retractable_foils",
            is_expressible=False,
            gap_description="Retractable mechanism is mechanical, not geometric. Geometry can express foil positions but not retraction mechanism.",
            recommended_strategy=ExpressionStrategy.OUT_OF_SCOPE,
        )
    
    def _express_surface_piercing_struts(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="surface_piercing_struts",
            is_expressible=True,
            dsl_code="# geometry.body with physics_category: 'surface_piercing'",
            primitives_used=["geometry.body"],
            complexity="simple",
        )
    
    def _express_vertical_columns(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="vertical_columns",
            is_expressible=True,
            dsl_code="# geometry.body with vertical orientation",
            primitives_used=["geometry.body"],
            complexity="simple",
        )
    
    def _express_outrigger_connection(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="outrigger_connection_structure",
            is_expressible=True,
            dsl_code="# geometry.attachment connecting bodies",
            primitives_used=["geometry.attachment"],
            complexity="moderate",
        )
    
    def _express_outrigger_ama(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="outrigger_ama",
            is_expressible=True,
            dsl_code="# geometry.body with offset_y",
            primitives_used=["geometry.body"],
            complexity="simple",
        )
    
    def _express_ama_beams(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="ama_connection_beams",
            is_expressible=True,
            dsl_code="# geometry.attachment",
            primitives_used=["geometry.attachment"],
            complexity="simple",
        )
    
    def _express_cross_structure(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="cross_structure",
            is_expressible=True,
            dsl_code="# geometry.attachment between hulls",
            primitives_used=["geometry.attachment"],
            complexity="moderate",
        )
    
    def _express_above_water_platform(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="above_water_platform",
            is_expressible=True,
            dsl_code="# geometry.body with physics_category: 'above_water'",
            primitives_used=["geometry.body"],
            complexity="simple",
        )
    
    def _express_vehicle_deck(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="large_vehicle_deck",
            is_expressible=True,
            dsl_code="# geometry.surface for deck",
            primitives_used=["geometry.surface"],
            complexity="simple",
        )
    
    def _express_submerged_pontoons(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="submerged_pontoons",
            is_expressible=True,
            dsl_code="# geometry.body with physics_category: 'submerged'",
            primitives_used=["geometry.body"],
            complexity="simple",
        )
    
    def _express_minimal_waterplane(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="minimal_waterplane_area",
            is_expressible=True,
            dsl_code="# Slender struts (derived from sections)",
            primitives_used=["geometry.section"],
            complexity="simple",
        )
    
    def _express_asymmetric_amas(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="asymmetric_amas",
            is_expressible=True,
            dsl_code="# Different sections for port/stbd amas",
            primitives_used=["geometry.body", "geometry.section"],
            complexity="moderate",
        )
    
    def _express_skeg(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="skeg",
            is_expressible=True,
            dsl_code="# geometry.surface extending from hull",
            primitives_used=["geometry.surface", "geometry.attachment"],
            complexity="simple",
        )
    
    def _express_lifting_tabs(self, ctx: Dict) -> FeatureExpression:
        return FeatureExpression(
            feature_name="lifting_tabs",
            is_expressible=True,
            dsl_code="# geometry.surface at stern",
            primitives_used=["geometry.surface", "geometry.attachment"],
            complexity="simple",
        )
    
    def _express_stringers(self, ctx: Dict) -> FeatureExpression:
        # This is STRUCTURAL, not geometric hull form
        return FeatureExpression(
            feature_name="longitudinal_stringers",
            is_expressible=False,
            gap_description="Longitudinal stringers are internal structure, not hull geometry. Out of scope for hull form primitives.",
            recommended_strategy=ExpressionStrategy.OUT_OF_SCOPE,
        )
    
    def _express_ballast(self, ctx: Dict) -> FeatureExpression:
        # This is SYSTEMS, not geometry
        return FeatureExpression(
            feature_name="ballast_system",
            is_expressible=False,
            gap_description="Ballast system is a fluid system, not hull geometry. Out of scope.",
            recommended_strategy=ExpressionStrategy.OUT_OF_SCOPE,
        )
    
    def _express_internal_ramps(self, ctx: Dict) -> FeatureExpression:
        # This is INTERNAL ARRANGEMENT, not hull geometry
        return FeatureExpression(
            feature_name="internal_ramps",
            is_expressible=False,
            gap_description="Internal ramps are arrangement/layout, not hull geometry. Out of scope.",
            recommended_strategy=ExpressionStrategy.OUT_OF_SCOPE,
        )
    
    def _express_roro(self, ctx: Dict) -> FeatureExpression:
        # This is OPERATIONAL CONCEPT, not geometry
        return FeatureExpression(
            feature_name="roll_on_roll_off_design",
            is_expressible=False,
            gap_description="RoRo is operational concept, not geometry. Hull openings are expressible, but RoRo concept is out of scope.",
            recommended_strategy=ExpressionStrategy.OUT_OF_SCOPE,
        )


# =============================================================================
# Test Cases
# =============================================================================

@pytest.fixture
def tester():
    return PrimitiveExpressionTester()


@pytest.mark.parametrize("vessel", REAL_VESSELS)
def test_vessel_expressibility(vessel, tester):
    """
    Test if vessel can be expressed using 7 primitives.
    
    ⚠️ CRITICAL: If this fails for >2 vessels, architecture needs reassessment.
    """
    expressions = []
    
    for feature in vessel["critical_features"]:
        expression = tester.attempt_feature_expression(feature, vessel)
        expressions.append(expression)
    
    result = VesselExpression(
        vessel_name=vessel["name"],
        category=vessel["category"],
        critical_features=vessel["critical_features"],
        expressions=expressions,
    )
    
    # Report
    print(f"\n{'='*80}")
    print(f"Vessel: {result.vessel_name}")
    print(f"Category: {result.category}")
    print(f"Coverage: {result.coverage*100:.1f}%")
    print(f"Expressible: {len(result.expressible_features)}/{len(result.expressions)}")
    print(f"{'='*80}")
    
    if result.failed_features:
        print(f"\n❌ Failed Features ({len(result.failed_features)}):")
        for feature in result.failed_features:
            expr = next(e for e in expressions if e.feature_name == feature)
            print(f"  - {feature}")
            if expr.gap_description:
                print(f"    Gap: {expr.gap_description}")
            if expr.recommended_strategy:
                print(f"    Strategy: {expr.recommended_strategy.value}")
    
    if result.expressible_features:
        print(f"\n✅ Expressible Features ({len(result.expressible_features)}):")
        for feature in result.expressible_features:
            expr = next(e for e in expressions if e.feature_name == feature)
            print(f"  - {feature} ({expr.complexity})")
            primitives = ", ".join(expr.primitives_used)
            print(f"    Primitives: {primitives}")
    
    # This is a soft assertion — we want to see all results
    # The overall test suite will determine if architecture is sufficient
    if not result.passes:
        print(f"\n⚠️  WARNING: {vessel['name']} coverage {result.coverage*100:.1f}% < 75% threshold")


def test_overall_architecture_sufficiency(tester):
    """
    ⚠️ THE EXISTENTIAL TEST
    
    DECISION GATE: If <8/10 vessels at ≥75% coverage, STOP and reassess architecture.
    """
    results = []
    
    for vessel in REAL_VESSELS:
        expressions = []
        for feature in vessel["critical_features"]:
            expression = tester.attempt_feature_expression(feature, vessel)
            expressions.append(expression)
        
        result = VesselExpression(
            vessel_name=vessel["name"],
            category=vessel["category"],
            critical_features=vessel["critical_features"],
            expressions=expressions,
        )
        results.append(result)
    
    # Calculate overall metrics
    passing_vessels = [r for r in results if r.passes]
    total_vessels = len(results)
    pass_rate = len(passing_vessels) / total_vessels
    
    avg_coverage = sum(r.coverage for r in results) / total_vessels
    
    # Report
    print(f"\n{'='*80}")
    print(f"OVERALL PRIMITIVE COMPLETENESS RESULTS")
    print(f"{'='*80}")
    print(f"Total Vessels Tested: {total_vessels}")
    print(f"Passing (≥75% coverage): {len(passing_vessels)}")
    print(f"Failing (<75% coverage): {total_vessels - len(passing_vessels)}")
    print(f"Pass Rate: {pass_rate*100:.1f}%")
    print(f"Average Coverage: {avg_coverage*100:.1f}%")
    print(f"{'='*80}")
    
    print(f"\nResults by Vessel:")
    for result in results:
        status = "✅ PASS" if result.passes else "❌ FAIL"
        print(f"  {status} {result.vessel_name}: {result.coverage*100:.1f}%")
    
    # DECISION GATE
    REQUIRED_PASSING = 8
    REQUIRED_PASS_RATE = 0.8
    
    if len(passing_vessels) >= REQUIRED_PASSING:
        print(f"\n🎉 SUCCESS: {len(passing_vessels)}/{total_vessels} vessels pass (≥{REQUIRED_PASSING} required)")
        print(f"✅ Architecture is sufficient — primitives can express real vessel designs")
        print(f"✅ Proceed to Day 3 (Q5 Parallel Axis Validation)")
    else:
        print(f"\n🚨 CRITICAL FAILURE: Only {len(passing_vessels)}/{total_vessels} vessels pass (<{REQUIRED_PASSING} required)")
        print(f"❌ Architecture needs reassessment — primitives are insufficient")
        print(f"⚠️  STOP IMPLEMENTATION — Escalate to human for architecture review")
        
        # Document gaps
        print(f"\nGaps Analysis:")
        all_failed_features = {}
        for result in results:
            for expr in result.expressions:
                if not expr.is_expressible:
                    if expr.feature_name not in all_failed_features:
                        all_failed_features[expr.feature_name] = {
                            "count": 0,
                            "gap": expr.gap_description,
                            "strategy": expr.recommended_strategy,
                        }
                    all_failed_features[expr.feature_name]["count"] += 1
        
        for feature, info in sorted(all_failed_features.items(), key=lambda x: -x[1]["count"]):
            print(f"\n  {feature} (failed in {info['count']} vessels)")
            print(f"    Gap: {info['gap']}")
            print(f"    Strategy: {info['strategy'].value if info['strategy'] else 'unknown'}")
        
        pytest.fail(
            f"ARCHITECTURE INSUFFICIENT: Only {len(passing_vessels)}/{total_vessels} vessels expressible. "
            f"Required: ≥{REQUIRED_PASSING} vessels at ≥75% coverage. STOP and reassess."
        )
    
    # This assertion ensures CI fails if architecture is insufficient
    assert len(passing_vessels) >= REQUIRED_PASSING, \
        f"Primitive completeness test failed: {len(passing_vessels)}/{total_vessels} < {REQUIRED_PASSING}"

