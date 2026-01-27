"""
Test fixtures for geometry proposals.

These fixtures use ONLY geometry primitives — no hull types.
They are used to verify THE TEST from the MAGNET Mission Statement.

THE TEST:
1. Create "stepped ventilated planing hull" using only discontinuities, flow paths, openings
2. Create "catamaran" using only bodies, sections, surfaces
3. Create novel configuration that validates without new code

Reference: MAGNET_Merge_Implementation_Plan.md Phase 1
"""

from magnet.glue.protocol.schemas import GeometryProposal


# =============================================================================
# VALID PROPOSALS — These MUST work without new code
# =============================================================================

VALID_SINGLE_HULL = GeometryProposal.from_program(
    program_text="""
        CREATE geometry.section bow {
            station: 0.0,
            points: [[0, 0], [1, -0.5], [1, 0.5]]
        }
        CREATE geometry.section mid {
            station: 0.5,
            points: [[0, 0], [2, -1], [2, 1]]
        }
        CREATE geometry.section stern {
            station: 1.0,
            points: [[0, 0], [1.5, -0.7], [1.5, 0.7]]
        }
        CREATE geometry.body main {
            section_ids: ["bow", "mid", "stern"],
            physics_category: "surface_piercing"
        }
    """,
    reasoning="Single hull vessel — basic geometry test",
)


VALID_TWIN_HULL = GeometryProposal.from_program(
    program_text="""
        CREATE geometry.section bow {
            station: 0.0,
            points: [[0, 0], [0.5, -0.3], [0.5, 0.3]]
        }
        CREATE geometry.section stern {
            station: 1.0,
            points: [[0, 0], [0.5, -0.3], [0.5, 0.3]]
        }
        CREATE geometry.body port {
            section_ids: ["bow", "stern"],
            offset_y_m: -4.0,
            physics_category: "surface_piercing"
        }
        CREATE geometry.body stbd {
            section_ids: ["bow", "stern"],
            offset_y_m: 4.0,
            physics_category: "surface_piercing"
        }
    """,
    reasoning="Twin hull vessel — NO 'catamaran' type anywhere",
)


VALID_STEPPED_HULL = GeometryProposal.from_program(
    program_text="""
        CREATE geometry.section bow {
            station: 0.0,
            points: [[0, 0], [1, -0.5], [1, 0.5]]
        }
        CREATE geometry.section mid {
            station: 0.5,
            points: [[0, 0], [2, -1], [2, 1]]
        }
        CREATE geometry.section step_start {
            station: 0.6,
            points: [[0, 0], [2, -1], [2, 1]]
        }
        CREATE geometry.section step_end {
            station: 0.7,
            points: [[0, 0], [1.8, -0.9], [1.8, 0.9]]
        }
        CREATE geometry.section stern {
            station: 1.0,
            points: [[0, 0], [1.5, -0.7], [1.5, 0.7]]
        }
        
        CREATE geometry.body main {
            section_ids: ["bow", "mid", "step_start", "step_end", "stern"],
            physics_category: "planing"
        }
        
        CREATE geometry.discontinuity step_1 {
            type: "surface_break",
            body_id: "main",
            x_position: 0.65,
            z_offset_m: -0.2,
            length_m: 1.0
        }
        
        CREATE geometry.flow_path ventilation_channel {
            medium: "air",
            inlet_point: [0.6, 0.0, -0.1],
            outlet_point: [0.7, 0.0, -0.1],
            cross_section_m2: 0.1
        }
    """,
    reasoning="Stepped ventilated planing hull — NO 'stepped hull' type anywhere",
)


VALID_NOVEL_FORM = GeometryProposal.from_program(
    program_text="""
        CREATE geometry.section main_bow {
            station: 0.0,
            points: [[0, 0], [1, -0.5], [1, 0.5]]
        }
        CREATE geometry.section main_mid {
            station: 0.5,
            points: [[0, 0], [2, -1], [2, 1]]
        }
        CREATE geometry.section main_stern {
            station: 1.0,
            points: [[0, 0], [1.5, -0.7], [1.5, 0.7]]
        }
        CREATE geometry.body main {
            section_ids: ["main_bow", "main_mid", "main_stern"],
            physics_category: "surface_piercing"
        }

        CREATE geometry.section outrigger_section {
            station: 0.0,
            points: [[0, 0], [0.3, -0.1], [0.3, 0.1]]
        }
        CREATE geometry.body outrigger_port {
            section_ids: ["outrigger_section"],
            offset_x_m: 0.5,
            offset_y_m: -3.0,
            offset_z_m: 0.5,
            physics_category: "above_water"
        }
        CREATE geometry.body outrigger_stbd {
            section_ids: ["outrigger_section"],
            offset_x_m: 0.5,
            offset_y_m: 3.0,
            offset_z_m: 0.5,
            physics_category: "above_water"
        }

        CREATE geometry.attachment aka_port {
            attachment_type: "rigid_beam",
            parent_body_id: "main",
            child_body_id: "outrigger_port",
            connection_points: [
                [0.4, -1.0, 1.0],
                [0.6, -2.5, 1.0]
            ]
        }
        CREATE geometry.attachment aka_stbd {
            attachment_type: "rigid_beam",
            parent_body_id: "main",
            child_body_id: "outrigger_stbd",
            connection_points: [
                [0.4, 1.0, 1.0],
                [0.6, 2.5, 1.0]
            ]
        }
    """,
    reasoning="Novel form — validates without new code (main hull with above-water outriggers)",
)


# Triple hull with asymmetric configuration
VALID_THREE_BODY = GeometryProposal.from_program(
    program_text="""
        CREATE geometry.section main_bow {
            station: 0.0,
            points: [[0, 0], [1.5, -0.7], [1.5, 0.7]]
        }
        CREATE geometry.section main_stern {
            station: 1.0,
            points: [[0, 0], [1.2, -0.5], [1.2, 0.5]]
        }
        CREATE geometry.body main {
            section_ids: ["main_bow", "main_stern"],
            physics_category: "surface_piercing"
        }
        
        CREATE geometry.section outrigger_bow {
            station: 0.0,
            points: [[0, 0], [0.4, -0.2], [0.4, 0.2]]
        }
        CREATE geometry.section outrigger_stern {
            station: 1.0,
            points: [[0, 0], [0.3, -0.15], [0.3, 0.15]]
        }
        
        CREATE geometry.body outrigger_port {
            section_ids: ["outrigger_bow", "outrigger_stern"],
            offset_y_m: -4.0,
            physics_category: "surface_piercing"
        }
        CREATE geometry.body outrigger_stbd {
            section_ids: ["outrigger_bow", "outrigger_stern"],
            offset_y_m: 4.0,
            physics_category: "surface_piercing"
        }
    """,
    reasoning="Three-body configuration — NO 'trimaran' type anywhere",
)


# Hull with multiple discontinuities and openings
VALID_COMPLEX_SURFACES = GeometryProposal.from_program(
    program_text="""
        CREATE geometry.section bow {
            station: 0.0,
            points: [[0, 0], [1, -0.5], [1, 0.5]]
        }
        CREATE geometry.section mid {
            station: 0.5,
            points: [[0, 0], [2, -1], [2, 1]]
        }
        CREATE geometry.section stern {
            station: 1.0,
            points: [[0, 0], [1.5, -0.7], [1.5, 0.7]]
        }
        
        CREATE geometry.body main {
            section_ids: ["bow", "mid", "stern"],
            physics_category: "surface_piercing"
        }
        
        CREATE geometry.discontinuity chine_port {
            type: "chine",
            body_id: "main",
            start_station: 0.2,
            end_station: 0.9
        }
        CREATE geometry.discontinuity chine_stbd {
            type: "chine",
            body_id: "main",
            start_station: 0.2,
            end_station: 0.9
        }
        
        CREATE geometry.opening sea_chest {
            surface_id: "main_bottom",
            position: [0.6, 0.0, -0.8],
            dimensions: [0.3, 0.2],
            purpose: "sea_water_intake"
        }
        
        CREATE geometry.flow_path cooling_water {
            medium: "water",
            inlet_point: [0.6, 0.0, -0.8],
            outlet_point: [0.9, 0.0, 0.0],
            cross_section_m2: 0.05
        }
    """,
    reasoning="Complex surface features — discontinuities, openings, flow paths",
)


# =============================================================================
# INVALID PROPOSALS — These should fail validation
# =============================================================================

INVALID_EMPTY_BODY = GeometryProposal.from_program(
    program_text="""
        CREATE geometry.body main {
            section_ids: []
        }
    """,
    reasoning="Invalid: body with no sections",
)


INVALID_MISSING_SECTION = GeometryProposal.from_program(
    program_text="""
        CREATE geometry.body main {
            section_ids: ["nonexistent_section"]
        }
    """,
    reasoning="Invalid: body references nonexistent section",
)


INVALID_SYNTAX = GeometryProposal.from_program(
    program_text="""THIS IS NOT VALID DSL SYNTAX { }""",
    reasoning="Invalid: syntax error",
)


INVALID_CIRCULAR_ATTACHMENT = GeometryProposal.from_program(
    program_text="""
        CREATE geometry.body main {
            section_ids: ["bow"]
        }
        CREATE geometry.attachment self_ref {
            parent_body_id: "main",
            child_body_id: "main"
        }
    """,
    reasoning="Invalid: self-referential attachment",
)


# =============================================================================
# FIXTURE COLLECTIONS
# =============================================================================

VALID_FIXTURES = [
    VALID_SINGLE_HULL,
    VALID_TWIN_HULL,
    VALID_STEPPED_HULL,
    VALID_NOVEL_FORM,
    VALID_THREE_BODY,
    VALID_COMPLEX_SURFACES,
]

INVALID_FIXTURES = [
    INVALID_EMPTY_BODY,
    INVALID_MISSING_SECTION,
    INVALID_SYNTAX,
    INVALID_CIRCULAR_ATTACHMENT,
]

# THE TEST fixtures (from MAGNET Mission Statement)
THE_TEST_FIXTURES = {
    "stepped_ventilated_planing": VALID_STEPPED_HULL,
    "twin_hull": VALID_TWIN_HULL,
    "novel_form": VALID_NOVEL_FORM,
}


# =============================================================================
# FORBIDDEN TERMS — These MUST NOT appear in any fixture
# =============================================================================

FORBIDDEN_TERMS = [
    "catamaran", "trimaran", "monohull",
    "stepped_hull", "stepped hull", "planing_hull",
    "patrol_boat", "patrol boat", "workboat",
    "ferry", "yacht", "tanker",
]


def verify_no_forbidden_terms():
    """
    Verify no fixtures contain forbidden design type names in program_text.
    
    Note: reasoning field may contain these terms for human documentation,
    but the actual DSL program must not.
    """
    violations = []
    
    for fixture in VALID_FIXTURES + INVALID_FIXTURES:
        program_lower = fixture.program_text.lower()
        
        for term in FORBIDDEN_TERMS:
            if term in program_lower:
                violations.append(f"program_text contains '{term}'")
    
    return violations


# Run verification on module load
_violations = verify_no_forbidden_terms()
if _violations:
    import warnings
    warnings.warn(f"Fixture violations: {_violations}")

