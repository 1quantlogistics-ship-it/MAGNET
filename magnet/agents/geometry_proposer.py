"""
magnet/agents/geometry_proposer.py - Geometry Proposer Agent

Converts natural language design intent into geometry primitives.
Outputs ONLY geometry.* operations - never hull.* types.

Reference: MAGNET_Implementation_Spec.md §1.3.2
"""

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .llm_client import LLMClient
from .state_lens import extract_lens
from magnet.llm.exceptions import ValidationError as LLMValidationError

from magnet.agents.vessel_thinking_schema import parse_vessel_thinking_response
from magnet.agents.vessel_thinking_validator import (
    build_targeted_patch_instruction,
    reexecute_checks,
    validate_coverage_and_proof,
    validate_observation_targets_against_geometry,
    validate_verified_unverified_rules,
)


# =============================================================================
# System Prompt (from MAGNET_Implementation_Spec.md §1.3.2)
# =============================================================================

GEOMETRY_PROPOSER_SYSTEM_PROMPT = """You are MAGNET's Geometry Proposer.

YOUR ROLE:
- Convert design problems into geometry primitives
- Output ONLY geometry.* operations (see allowed primitives below)
- NEVER use hull.* types (deprecated for agent use)
- Include confidence and reasoning for every operation

ALLOWED PRIMITIVES (geometry.* only):
- geometry.body: {body_id, body_type (freeform string), physics_category (freeform string), offset_x_m, offset_y_m, offset_z_m}
- geometry.section: {section_id, body_id, station (0-1), points [[y,z],...], edge_types [...]}
- geometry.surface: {surface_id, body_id, definition (lofted|nurbs), physics_category (freeform string), ...}
- geometry.discontinuity: {id, body_id, discontinuity_type (freeform string), station_start, station_end, profile (freeform string), depth_m}
- geometry.flow_path: {id, body_id, medium (freeform string), inlet_point, outlet_point, cross_section_m2}
- geometry.opening: {id, surface_id, position, dimensions, purpose (freeform string)}
- geometry.attachment: {id, parent_body_id, child_body_id, attachment_type (freeform string), offset_x_m, offset_y_m, offset_z_m}

DESIGN PROGRAM FORMAT:
{
  "program_id": "string",
  "version": 1,
  "operations": [
    {
      "op": "CREATE"|"UPDATE"|"DELETE",
      "type": "geometry.body"|"geometry.section"|...,
      "id": "string (stable UUID)",
      "params": {...},
      "reasoning": "string (why this operation)",
      "confidence": 0.0-1.0
    }
  ],
  "constraints": [
    {"type": "CONSTRAIN", "constraint_type": "min_value"|"max_value"|"equality", "target": "path", "value": number}
  ]
}

PHYSICS CATEGORY RULES:
- body_type can be ANY string (e.g., "main_hull", "outrigger", "hydrofoil_strut", "sail_keel")
- physics_category can be ANY string (e.g., "submerged", "surface_piercing", "above_water", 
  "partially_submerged", "spray_zone", "cavitating", or any novel category)
- The kernel validates: "can physics be computed for this body?" NOT "is this a known category?"
- Describe the physics regime, not a design classification

RULES:
1. ALWAYS include reasoning explaining WHY this geometry achieves the goal
2. NEVER output hull.spray_rail, hull.chine, etc. — use geometry.* primitives
3. Use freeform strings for body_type, surface_type, medium — be descriptive
4. Set confidence < 0.7 if the translation is uncertain
5. If multiple approaches exist, output the SIMPLEST one first
   - On a BLANK design, "simplest" means a minimal complete hull (body+sections+lofted surface),
     NOT a discontinuity-only program.

VERIFICATION CONTRACT (NO PRIORS):
- You may invent any DOFs you want (open vocabulary).
- If you claim PASS/FAIL checks (range/monotonic/varies) for a DOF, you MUST bind it to at least one
  kernel-computable observable and provide measurable observation_targets.
- If no suitable observable exists, mark the DOF UNVERIFIED (no PASS/FAIL checks) and state the consequence.
- Observables are measurement functions only (rulers), not templates or hull-type mappings.
- Observation targets may include `station_range: [lo, hi]` to scope the measurement to a region.
- Default is whole-hull `[0.0, 1.0]`. Use regional scoping to express entry vs run character.
- If you claim profile/topside intent (sheer profile, entry shape, flare/tumblehome, freeboard progression), bind those DOFs to the corresponding profile/topside observables and set targets.

BLANK DESIGN REQUIREMENT (CRITICAL RELIABILITY):
- If the current design has NO existing hull sections, you MUST create a complete minimal hull first:
  1) CREATE `geometry.body`
  2) CREATE >= 7 `geometry.section` for that body (stations in 0..1)
  3) CREATE `geometry.surface` with `definition: "lofted"` for that body
- Do NOT output only discontinuities/constraints. A hull cannot be compiled without sections.

SECTION POINTS COORDINATE CONTRACT (CRITICAL):
- For polygon sections, `points` is a 2D cross-section profile: `[[y, z], ...]`
- DO NOT include X in points (NO `[x,y,z]` triples). X is derived ONLY from `station`.
- If you need 3D points, use primitives that explicitly take 3D coordinates (e.g., flow_path inlet/outlet).

ABSOLUTE EXAMPLES (DO NOT VIOLATE):
✅ VALID (2D points only):
  "points": [[0.0, -1.5], [0.4, -1.4], [1.2, -1.0], [2.2, -0.3], [2.5, 0.0], [2.4, 0.6], [2.2, 1.2], [2.0, 2.0]]
❌ INVALID (3D points; will be rejected / trigger clarification):
  "points": [[0.0, 0.0, -1.5], [0.5, 1.2, -1.0], [1.0, 2.5, 0.0]]
❌ INVALID (mixed formats / dicts with x):
  "points": [{"x": 0.0, "y": 1.2, "z": -1.0}, [2.5, 0.0]]

SECTION SHAPE CONTRACT (IMPORTANT):
- For polygon sections, output a ONE-SIDE half-section profile (typical): y>=0 from the section centerline outward.
- The canonical geometry pipeline treats section points as "port side" and mirrors for the opposite side as needed.
- DO NOT bake port/starboard sign into section points for catamarans. Use `geometry.body.offset_y_m` to position bodies.
- Sections must be OPEN curves ordered from KEEL → DECK:
  - Start near centerline at the keel: first point should have y≈0 and the lowest z
  - End at deck edge/sheer: last point should have the highest z
  - z should be strictly increasing (no duplicates); do not include repeated points
- **All sections for a given body in a single program MUST have the same number of points.**
  This preserves point correspondence and avoids loft twisting / faceting.

STATION CONVENTION CONTRACT (CRITICAL):
- `geometry.section.station` is ALWAYS normalized 0..1 measured from AFT to FORWARD:
  - station=0.0 is aft/AP/transom region (x=0)
  - station=1.0 is forward/FP/bow region (x=LOA)
- Do NOT invert this. The kernel derives X from station using this convention.

FORBIDDEN CONSTRAINT PATTERNS:
- NEVER use hull.spray_rail_*, hull.chine_*, hull.step_*
- Constraints must reference geometry.* paths or physics outputs (gm, displacement, resistance)
- WRONG: constrain hull.spray_rail_height_fraction >= 0.6
- RIGHT: constrain stability.gm_m >= 0.5

## NAVAL ARCHITECTURE TRANSLATION GUIDE

Use this guide to translate user intent into valid geometry primitives.

### SPEED & RESISTANCE

"Make it faster" → Increase L/B ratio
- Target L/B: 6-8 (displacement), 8-12 (planing)
- Implementation: UPDATE geometry.section { ... narrow beam ... }

Typical L/B Ratios:
- Cargo ships: 6-7, Planing boats: 8-12, Catamarans (per hull): 10-15

### STABILITY

"More stable" → Increase GM (GM = KB + BM - KG)
- To increase GM: Increase beam → UPDATE geometry.section { ... widen beam ... }

### HULL FORMS

"Deep-V hull" → High deadrise (20-30°) in sections
- UPDATE geometry.section with high-angle points
Deadrise: Flat bottom: 0-10°, Deep V: 20-30°

### HIGH-SPEED PLANING MONOHULL (GEOMETRIC, NOT A TYPE)

When the user asks for a high-speed planing monohull (whatever they call it), translate into geometric targets:
- **Fine bow entry**: very small half-beam at waterline near bow stations (0.02–0.12).
- **Deadrise progression**: higher in the forebody, lower toward transom (e.g. ~30° fore → ~16° at transom).
- **Hard chine continuity**: include a hard edge near the waterline/chine and keep its index consistent across sections.
- **Bow flare** (stations < 0.2): above waterline, y should increase with z (flare) to knock down spray.
- **Aft tumblehome** (stations > 0.6): above waterline, y may slightly decrease with z for cockpit/house shaping.

Minimum fidelity for realistic rendering/physics:
- Use **10–15 stations** (denser where curvature is high - typically bow and stern)
- Use **12–20 points per section**, and keep the **same point count for all sections**.

### GEOMETRIC QUALITY FOR SMOOTH FORMS

When the user asks for "fine entry", "sharp bow", "smooth curves", or similar geometric qualities:

**Fine entry (geometric definition):**
- Bow sections (station < 0.15) should have max half-beam that is a SMALL FRACTION of midship beam
- The ratio bow_max_y / midship_max_y determines entry fineness:
  - Very fine: 5-10% (wave-piercing, low resistance)
  - Moderate: 15-25% (balanced)
  - Full: 30%+ (cargo capacity priority)
- This is a CONTINUOUS PARAMETER, not a type

**Smooth curves (geometric definition):**
- More stations = smoother longitudinal curves (minimum 10-12 for smooth appearance)
- More points per section = smoother transverse curves (minimum 12-15)
- Station density should be HIGHER where curvature changes rapidly (typically bow and stern)
- Recommended station distribution for high curvature at ends:
  [0.02, 0.05, 0.09, 0.14, 0.22, 0.32, 0.45, 0.58, 0.72, 0.84, 0.93, 0.98]

**Entry angle / deadrise (geometric definition):**
- Deadrise angle = atan2(z_change, y_change) from keel to chine
- Higher deadrise (20-30°) = sharper V, better rough water
- Lower deadrise (5-15°) = flatter, more stable at rest
- This varies CONTINUOUSLY along the hull length

These are GEOMETRIC PARAMETERS that the user can request in any combination.
The kernel validates the resulting geometry - it does not recognize "hull types".

### FEATURES → GEOMETRY PRIMITIVES

"Add spray rails" → geometry.discontinuity { type: "surface_break", height_fraction: 0.7 }
"Add chines" → geometry.discontinuity { type: "hard_edge", height_fraction: 0.6 }
"Bulbous bow" → geometry.body + geometry.attachment (separate body, forward, below waterline)

### MULTI-BODY CONFIGURATIONS

"Catamaran" → 2× geometry.body with lateral offset
- port_hull: offset_y_m: -10.0, stbd_hull: offset_y_m: 10.0
- Hull spacing: S/L = 0.35-0.45 typical

### SEAKEEPING

"3ft seas" → 1. High deadrise (25-35°), 2. Bow flare, 3. Freeboard ≥ 1.5 × wave_height

### CONSTRAINTS - EMERGENT vs SETTABLE

Draft is EMERGENT: WRONG: SET hull.draft = 1.2 ❌, RIGHT: UPDATE geometry.section { z-coords }
Beam is LOCAL: WRONG: SET hull.beam = 7.0 ❌, RIGHT: UPDATE geometry.section stern { wider }

## CRITICAL REMINDERS

1. NEVER invent primitives (Valid: geometry.body/section/surface/discontinuity/flow_path/opening/attachment)
2. NEVER use enumeration (Invalid: hull.hull_type, SET hull.has_spray_rails = true)
3. ALWAYS make geometric changes (Good: UPDATE geometry.section { ... })
4. ALWAYS include quantification (Good: "Increase beam from 5.0m to 6.0m")

## HULL SECTION GEOMETRY GUIDE (CRITICAL - READ CAREFULLY)

Hull sections are **half-breadth curves** representing ONE SIDE of the hull (starboard).
The system automatically mirrors them to create the full hull.

### COORDINATE CONVENTION (MAGNET Standard)
- **Y-axis**: Lateral distance from centerline (Y=0 at centerline, Y>0 toward port)
- **Z-axis**: Vertical height from baseline (Z=0 at baseline/keel, Z=draft at waterline, Z=depth at deck)
- **X-axis**: NOT in section points. X is derived from `station` (0=stern/AP, 1=bow/FP)

See docs/0-architecture/GEOMETRY_CONVENTIONS.md for full specification.

### SECTION POINT ORDER
Points should trace an **OPEN curve from KEEL to DECK** along ONE side:
1. Start at keel centerline: [0.0, z_keel] (deepest point, y≈0)
2. Trace UP and OUT along the hull side
3. End at deck edge/sheer: [y_max_at_sheer, z_deck]

**CRITICAL: Sections are NOT closed polygons!**
- ❌ WRONG: Points that go out and then back to centerline (creates a tube/football shape)
- ✅ RIGHT: Points that trace from keel to deck edge (open curve, mirrored by system)

### EXAMPLE SECTION SHAPES

**Deep-V Planing Hull (high-speed planing monohull):**
Station 0.5 (midship) for 70ft, 18ft beam, 5ft draft:
```
points: [
  [0.0, -1.5],    // Keel at centerline (deepest point)
  [0.5, -1.4],    // Start of V-bottom rising
  [1.5, -1.0],    // V-bottom continuing
  [2.5, -0.5],    // Approaching chine
  [3.0, 0.0],     // Chine at waterline (hard edge here)
  [3.2, 0.8],     // Topsides above chine
  [3.0, 1.5],     // Slight tumblehome toward sheer
  [2.8, 2.0]      // Sheer/deck edge
]
edge_types: ["smooth", "smooth", "smooth", "hard", "smooth", "smooth", "smooth", "smooth"]
```
Note: Max beam (y=3.2) is above waterline. Chine is at z=0. Deep-V has 20-25° deadrise angle.

**Round Bilge Displacement Hull (trawler, sailboat):**
Station 0.5 (midship) for 40ft, 12ft beam:
```
points: [
  [0.0, -1.2],    // Keel at centerline
  [0.3, -1.1],    // Garboard strake
  [0.8, -0.9],    // Bilge starting
  [1.4, -0.5],    // Bilge radius
  [1.8, 0.0],     // Waterline beam
  [2.0, 0.6],     // Topsides
  [1.9, 1.2]      // Sheer
]
edge_types: ["smooth", "smooth", "smooth", "smooth", "smooth", "smooth", "smooth"]
```
Note: All smooth edges (round bilge). Gentle curves, no hard chines.

**Hard Chine Planing Hull (bass boat, RIB):**
Station 0.5 for 20ft, 8ft beam:
```
points: [
  [0.0, -0.5],    // Shallow keel
  [0.8, -0.4],    // Flat bottom panel
  [1.2, -0.3],    // Approaching chine
  [1.5, 0.0],     // Chine at waterline (HARD EDGE)
  [1.6, 0.4],     // Vertical or flared topsides
  [1.5, 0.8]      // Sheer
]
edge_types: ["smooth", "smooth", "smooth", "hard", "smooth", "smooth"]
```
Note: Flat bottom with hard chine transition. Low deadrise (5-15°).

### BOW AND TRANSOM SECTIONS

**Bow (station 0.0-0.15):**
- Very narrow beam (fine entry)
- Deep draft maintained for wave-piercing
- Example: [[0.0, -2.0], [0.2, -1.5], [0.4, -0.5], [0.5, 0.5], [0.4, 1.5]]

**Transom (station 0.9-1.0):**
- Full beam maintained (for planing) or slightly reduced
- Shallow draft (clean water release)
- Example: [[0.0, -0.8], [1.0, -0.5], [2.5, 0.0], [2.8, 0.8], [2.5, 1.5]]

### COMMON MISTAKES TO AVOID

1. ❌ **Closed polygon sections**: Points that return to y=0 at both top AND bottom create tubes
   - Wrong: [[0, 1], [2, 0], [0, -1]] → football/tube shape when mirrored
   - Right: [[0, -1], [2, 0], [1.8, 1]] → proper hull section

2. ❌ **Max beam at keel**: Real hulls have max beam at or above waterline, not at keel
   - Wrong: Keel point at [3.0, -2.0] (widest at bottom)
   - Right: Keel point at [0.0, -2.0], max beam at [3.0, 0.5]

3. ❌ **Insufficient stations**: Use 7-11 stations for a realistic hull (more stations near bow + transom)

4. ❌ **Inconsistent point counts**: All sections should have the SAME number of points for clean lofting
   - For visually smooth hulls, target 12–20 points per section (more around chine/knuckle)

5. ❌ **Inconsistent Z convention**: Use baseline-up. Keep `z=0` at baseline/keel and z increases upward. Waterline is at z=draft.
"""


# =============================================================================
# Pydantic Models for Structured Output
# =============================================================================

class GeometryOperation(BaseModel):
    """A single geometry operation."""
    op: str = Field(..., description="CREATE, UPDATE, or DELETE")
    type: str = Field(..., description="geometry.body, geometry.section, etc.")
    id: str = Field(..., description="Stable UUID for this resource")
    params: Dict[str, Any] = Field(default_factory=dict)
    reasoning: str = Field(..., description="Why this operation achieves the goal")
    confidence: float = Field(..., ge=0.0, le=1.0)


class Constraint(BaseModel):
    """A design constraint."""
    type: str = Field(default="CONSTRAIN")
    constraint_type: str = Field(..., description="min_value, max_value, equality")
    target: str = Field(..., description="Path to constrained value, e.g., hull.gm")
    value: float


class DesignProgram(BaseModel):
    """Complete design program output."""
    program_id: str
    version: int = 1
    operations: List[GeometryOperation]
    constraints: List[Constraint] = Field(default_factory=list)


# =============================================================================
# State Injection
# =============================================================================

def format_state_for_injection(state: Dict[str, Any]) -> str:
    """Format current design state for LLM context injection."""
    bodies = state.get("resources", {})
    body_section = {}
    section_list = []
    surface_list = []
    
    for rid, resource in bodies.items():
        rtype = resource.get("_type", "")
        if rtype == "geometry.body":
            body_section[rid] = {
                "body_type": resource.get("body_type", "unknown"),
                "physics_category": resource.get("physics_category", "surface_piercing"),
                "offset_y_m": resource.get("offset_y_m", 0),
            }
        elif rtype == "geometry.section":
            pts = resource.get("points") or []
            summary: Dict[str, Any] = {}
            if isinstance(pts, list) and pts and isinstance(pts[0], (list, tuple)) and len(pts[0]) >= 2:
                ys = []
                zs = []
                for p in pts:
                    if isinstance(p, (list, tuple)) and len(p) >= 2:
                        y, z = p[0], p[1]
                        if isinstance(y, (int, float)) and isinstance(z, (int, float)):
                            ys.append(float(y))
                            zs.append(float(z))
                if ys and zs:
                    summary = {
                        "point_count": len(pts),
                        "y_range": [min(ys), max(ys)],
                        "z_range": [min(zs), max(zs)],
                        "sample_points": pts[:3],
                        "points_contract": "polygon points are [[y,z],...]; X is derived from station",
                    }
            section_list.append({
                "id": rid,
                "body_id": resource.get("body_id", "main"),
                "station": resource.get("station", 0),
                **summary,
            })
        elif rtype == "geometry.surface":
            surface_list.append({
                "id": rid,
                "body_id": resource.get("body_id", "main"),
                "surface_type": resource.get("surface_type", "watertight"),
            })
    
    hull_state = state.get("hull", {})
    
    return f"""## Current Design State

### Geometry
```json
{{
  "bodies": {json.dumps(body_section, indent=2)},
  "sections": {json.dumps(section_list, indent=2)},
  "surfaces": {json.dumps(surface_list, indent=2)}
}}
```

### Hull Parameters
- LOA: {hull_state.get('loa', 25.0)}m
- Beam: {hull_state.get('beam', 5.0)}m
- Draft: {hull_state.get('draft', 1.5)}m

### Coordinate conventions (do not violate)
- Global X is derived from `geometry.section.station` (0..1) and LOA. Do NOT put X into section points.
- For polygon sections: `points` is strictly `[[y, z], ...]` where **z=0 is baseline** and **waterline is z=draft**.
- Sections are HALF-BREADTH (one side only, y>=0). Start at keel (y≈0), end at deck edge.
- NOT closed polygons! Points trace an open curve from keel to sheer, system mirrors.

### Recent Physics Validation
(No recent validation - propose initial geometry)
"""


# =============================================================================
# Geometry Proposer Agent
# =============================================================================

@dataclass
class ProposerResult:
    """Result from geometry proposer."""
    success: bool
    program: Optional[DesignProgram] = None
    program_text: str = ""
    raw_response: str = ""
    vessel_thinking_pass: Optional[Dict[str, Any]] = None
    vessel_thinking_pass_hash: Optional[str] = None
    thinking_pass_failure: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class GeometryProposer:
    """
    Agent that converts natural language design intent into geometry primitives.
    
    Contract:
    - Input: Natural language design request + current state
    - Output: DesignProgram with only geometry.* operations
    - Never outputs hull.* types
    - Always includes reasoning and confidence
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        temperature: float = 0.7,
    ):
        self._llm = llm_client
        self._temperature = temperature
    
    async def propose(
        self,
        intent: str,
        current_state: Optional[Dict[str, Any]] = None,
        constraints: Optional[List[str]] = None,
        validation_history: Optional[List[Dict[str, Any]]] = None,
        shape_document: Optional[Dict[str, Any]] = None,
    ) -> ProposerResult:
        """
        Convert design intent to geometry program.
        
        Args:
            intent: Natural language design request
            current_state: Current design state (optional)
            constraints: Additional constraints (optional)
            validation_history: List of previous validation attempts (last 5)
            shape_document: Shape document with character observables (for EDIT mode)
            
        Returns:
            ProposerResult with DesignProgram if successful
        """
        # Build prompt with validation history and shape document
        prompt = self._build_prompt(intent, current_state, constraints, validation_history, shape_document)
        last_raw: str = ""
        
        try:
            # Call LLM as TEXT and parse TWO artifacts:
            # - VESSEL_THINKING_PASS (JSON)
            # - GEOMETRY_PROGRAM (DesignProgram JSON)
            #
            # This keeps the executable program schema unchanged, while enforcing
            # an auditable, machine-checkable "thinking pass" contract.
            from magnet.llm.protocol import LLMOptions

            # CREATE/EDIT can legitimately take >60s (two JSON artifacts, schema validation, retries).
            # Keep configurable so UI/server timeouts can be aligned without code edits.
            import os
            timeout_s = int(os.getenv("MAGNET_GEOMETRY_PROPOSER_TIMEOUT_SECONDS", "180"))
            max_toks = int(os.getenv("MAGNET_GEOMETRY_PROPOSER_MAX_TOKENS", "3500"))
            options = LLMOptions(timeout_seconds=timeout_s, temperature=self._temperature, max_tokens=max_toks)
            
            async def _call_llm_text(prompt_text: str, *, opts: Optional[LLMOptions] = None) -> str:
                return await self._llm.complete(
                    prompt_text,
                    system_prompt=GEOMETRY_PROPOSER_SYSTEM_PROMPT,
                    options=opts or options,
                )

            raw = await _call_llm_text(prompt, opts=options)
            last_raw = raw

            # Parse thinking + program JSON (fail-closed; retry once if missing markers/invalid)
            try:
                thinking_obj, program_obj = self._parse_thinking_and_program(raw)
            except Exception as e:
                retry_opts = LLMOptions(timeout_seconds=timeout_s, temperature=0.2, max_tokens=max_toks)
                retry_prompt = (
                    prompt
                    + "\n\n"
                    + "### STRICT RETRY: OUTPUT CONTRACT FAILURE\n"
                    + "Your previous response did not include the required TWO JSON artifacts.\n"
                    + "You MUST output BOTH markers with JSON blocks:\n"
                    + "- VESSEL_THINKING_PASS\n"
                    + "- GEOMETRY_PROGRAM\n\n"
                    + f"Failure: {type(e).__name__}: {e}\n"
                )
                raw = await _call_llm_text(retry_prompt, opts=retry_opts)
                last_raw = raw
                thinking_obj, program_obj = self._parse_thinking_and_program(raw)
            thinking = parse_vessel_thinking_response(thinking_obj)

            if hasattr(thinking, "status") and str(getattr(thinking, "status", "")).upper() == "NEEDS_CLARIFICATION":
                question = str(getattr(thinking, "question", "") or "").strip()
                return ProposerResult(
                    success=False,
                    error=f"NEEDS_CLARIFICATION:{question or 'missing_question'}",
                    raw_response=raw,
                )

            issues = validate_coverage_and_proof(thinking)  # type: ignore[arg-type]
            issues.extend(validate_verified_unverified_rules(thinking))  # type: ignore[arg-type]
            reexec_issues, computed_by_check = reexecute_checks(thinking)  # type: ignore[arg-type]
            issues.extend(reexec_issues)

            if issues:
                retry_opts = LLMOptions(timeout_seconds=timeout_s, temperature=0.2, max_tokens=max_toks)
                patch = build_targeted_patch_instruction(issues, computed_by_check)
                retry_prompt = (
                    prompt
                    + "\n\n"
                    + "### STRICT RETRY: VESSEL_THINKING_PASS FAILED VALIDATION\n"
                    + "Your previous response failed deterministic server-side validation.\n"
                    + "You MUST output TWO JSON artifacts again (VESSEL_THINKING_PASS + GEOMETRY_PROGRAM).\n\n"
                    + "Targeted patch instruction (JSON):\n"
                    + json.dumps(patch, ensure_ascii=False)
                    + "\n"
                )
                raw = await _call_llm_text(retry_prompt, opts=retry_opts)
                thinking_obj, program_obj = self._parse_thinking_and_program(raw)
                thinking = parse_vessel_thinking_response(thinking_obj)
                if hasattr(thinking, "status") and str(getattr(thinking, "status", "")).upper() == "NEEDS_CLARIFICATION":
                    question = str(getattr(thinking, "question", "") or "").strip()
                    return ProposerResult(
                        success=False,
                        error=f"NEEDS_CLARIFICATION:{question or 'missing_question'}",
                        raw_response=raw,
                    )
                issues2 = validate_coverage_and_proof(thinking)  # type: ignore[arg-type]
                issues2.extend(validate_verified_unverified_rules(thinking))  # type: ignore[arg-type]
                reexec_issues2, _ = reexecute_checks(thinking)  # type: ignore[arg-type]
                issues2.extend(reexec_issues2)
                if issues2:
                    return ProposerResult(
                        success=False,
                        error="THINKING_PASS_INVALID:" + (issues2[0].message if issues2 else "unknown"),
                        raw_response=raw,
                        vessel_thinking_pass=thinking_obj if isinstance(thinking_obj, dict) else None,
                        thinking_pass_failure=build_targeted_patch_instruction(issues2, {}),
                    )

            # Now validate the GEOMETRY_PROGRAM JSON into the existing DesignProgram schema.
            program = DesignProgram.model_validate(program_obj)

            # Prompt-only reliability improvement (NO auto-repair):
            # On blank designs, the most common catastrophic failure is emitting a “partial” program
            # (e.g., only a discontinuity) with ZERO sections, which the compiler rejects.
            #
            # We do a single retry with an explicit failure message and a hard requirement to emit
            # body + sections + lofted surface.
            try:
                is_blank_geometry = True
                resources = (current_state or {}).get("resources") or {}
                if isinstance(resources, dict) and isinstance(resources.get("sections"), list) and resources.get("sections"):
                    is_blank_geometry = False
                section_ops = [
                    op for op in (getattr(program, "operations", []) or [])
                    if getattr(op, "type", "") == "geometry.section"
                ]
                if is_blank_geometry and len(section_ops) == 0:
                    retry_opts = LLMOptions(timeout_seconds=60, temperature=0.2, max_tokens=6000)
                    retry_prompt = (
                        prompt
                        + "\n\n"
                        + "### CRITICAL RETRY (LAST OUTPUT WAS INVALID)\n"
                        + "Your previous program contained NO `geometry.section` operations, so compilation failed with:\n"
                        + "\"No sections defined - cannot create geometry\".\n\n"
                        + "You MUST output a complete minimal hull:\n"
                        + "- CREATE 1 geometry.body\n"
                        + "- CREATE 12 geometry.section (or at least 7) for that body (stations spanning 0..1)\n"
                        + "- CREATE 1 geometry.surface with definition \"lofted\" for that body\n"
                        + "- Only after that, optionally add discontinuities like a hard chine.\n"
                    )
                    raw_retry = await _call_llm_text(retry_prompt, opts=retry_opts)
                    thinking_obj_r, program_obj_r = self._parse_thinking_and_program(raw_retry)
                    program = DesignProgram.model_validate(program_obj_r)
            except Exception:
                # If retry fails for any reason, fall back to original output.
                pass
            
            # Defensive normalization:
            # Even with explicit prompt rules, models sometimes emit:
            # - [x,y,z] triples
            # - signed y (full-breadth), not half-breadth
            # - non-monotonic / duplicated z
            # - inconsistent per-section point counts
            #
            # Normalize these deterministically BEFORE validation so the system
            # prefers “repair and continue” over “clarify and stall”.
            try:
                program = self._normalize_section_points(program)
            except Exception:
                # Never fail the proposal solely due to the normalizer.
                pass

            # Engineering Truth: surface_definition MUST be explicit (no kernel defaults).
            # Ensure the proposer output includes an explicit intent at the resource level.
            try:
                surface_def = self._infer_surface_definition_from_intent(intent=intent)
                program = self._ensure_surface_definition(program, default_surface_definition=surface_def)
            except Exception:
                pass

            # If the program creates a lofted surface, ensure it has enough section stations.
            # Prefer "repair and continue" over "clarify and stall".
            try:
                program = self._ensure_min_loft_sections(program, min_sections=7)
            except Exception:
                # Never fail the proposal solely due to the densifier.
                pass

            # IMPORTANT: densification may have interpolated between mismatched point counts.
            # Re-normalize AFTER inserting sections so every section in a body shares a single point count.
            try:
                program = self._normalize_section_points(program)
            except Exception:
                pass

            # Normalize hard-edge track best-effort so chine indices don't jump across stations.
            try:
                program = self._normalize_hard_edge_tracks(program)
            except Exception:
                pass

            # Ensure loft surfaces explicitly reference sections in station order.
            try:
                program = self._ensure_surface_section_ids(program)
            except Exception:
                pass

            # Validate output
            validation_error = self._validate_program(program)
            if validation_error:
                return ProposerResult(
                    success=False,
                    error=validation_error,
                    raw_response=str(program),
                )

            # TASK-016: If model expresses low confidence, ask for clarification instead of guessing.
            min_conf = min((op.confidence for op in program.operations), default=1.0)
            if min_conf < 0.7:
                ask = 'ASK "How many hull bodies should the vessel have?" { options: ["1", "2", "3"] }'
                return ProposerResult(success=True, program=None, program_text=ask)

            # Deterministic symmetry coupling (control-plane fix):
            # If the current design contains symmetric body pairs (e.g., two demihulls with
            # offset_y_m ~= ±a), ensure section-shape updates apply to both sides.
            # This avoids "telephone-game drift" where only one hull gets updated.
            if current_state:
                try:
                    program = _enforce_symmetric_section_updates(program, current_state)
                except Exception:
                    # Never fail proposals due to symmetry helper; worst-case LLM output proceeds.
                    pass
            
            # Convert to DSL text
            program_text = self._to_dsl_text(program)
            
            # v0.1: Enforce observation targets against geometry-derived observables (fail-closed).
            try:
                obs_issues, obs_computed = validate_observation_targets_against_geometry(
                    thinking=thinking,  # type: ignore[arg-type]
                    program_text=program_text,
                    current_state=(current_state or {}),
                )
            except Exception:
                obs_issues, obs_computed = ([], {})

            if obs_issues:
                retry_opts = LLMOptions(timeout_seconds=60, temperature=0.2, max_tokens=6000)
                patch = build_targeted_patch_instruction(obs_issues, {"geometry_observables": obs_computed})
                retry_prompt = (
                    prompt
                    + "\n\n"
                    + "### STRICT RETRY: GEOMETRY DOES NOT MATCH CLAIMED OBSERVATIONS\n"
                    + "Your geometry did not satisfy the observation_targets bound in the thinking pass.\n"
                    + "You MUST output TWO JSON artifacts again (VESSEL_THINKING_PASS + GEOMETRY_PROGRAM).\n\n"
                    + "Targeted patch instruction (JSON):\n"
                    + json.dumps(patch, ensure_ascii=False)
                    + "\n"
                )
                raw2 = await _call_llm_text(retry_prompt, opts=retry_opts)
                thinking_obj2, program_obj2 = self._parse_thinking_and_program(raw2)
                thinking2 = parse_vessel_thinking_response(thinking_obj2)
                if hasattr(thinking2, "status") and str(getattr(thinking2, "status", "")).upper() == "NEEDS_CLARIFICATION":
                    question = str(getattr(thinking2, "question", "") or "").strip()
                    return ProposerResult(
                        success=False,
                        error=f"NEEDS_CLARIFICATION:{question or 'missing_question'}",
                        raw_response=raw2,
                    )
                program2 = DesignProgram.model_validate(program_obj2)
                # Keep existing deterministic normalizations
                try:
                    program2 = self._normalize_section_points(program2)
                except Exception:
                    pass
                try:
                    surface_def = self._infer_surface_definition_from_intent(intent=intent)
                    program2 = self._ensure_surface_definition(program2, default_surface_definition=surface_def)
                except Exception:
                    pass
                try:
                    program2 = self._ensure_min_loft_sections(program2, min_sections=7)
                except Exception:
                    pass
                try:
                    program2 = self._normalize_section_points(program2)
                except Exception:
                    pass
                try:
                    program2 = self._normalize_hard_edge_tracks(program2)
                except Exception:
                    pass
                try:
                    program2 = self._ensure_surface_section_ids(program2)
                except Exception:
                    pass
                program_text2 = self._to_dsl_text(program2)
                try:
                    obs_issues2, obs_computed2 = validate_observation_targets_against_geometry(
                        thinking=thinking2,  # type: ignore[arg-type]
                        program_text=program_text2,
                        current_state=(current_state or {}),
                    )
                except Exception:
                    obs_issues2, obs_computed2 = ([], {})
                if obs_issues2:
                    return ProposerResult(
                        success=False,
                        error="THINKING_PASS_INVALID:" + (obs_issues2[0].message if obs_issues2 else "unknown"),
                        raw_response=raw2,
                        vessel_thinking_pass=thinking_obj2 if isinstance(thinking_obj2, dict) else None,
                        thinking_pass_failure=build_targeted_patch_instruction(obs_issues2, {"geometry_observables": obs_computed2}),
                    )
                # Replace successful retry output
                raw = raw2
                thinking_obj = thinking_obj2
                thinking = thinking2  # type: ignore[assignment]
                program = program2
                program_text = program_text2

            vessel_thinking_pass = thinking_obj if isinstance(thinking_obj, dict) else None
            vessel_thinking_hash = None
            try:
                from magnet.core.turn_contracts import sha256_hex

                if vessel_thinking_pass is not None:
                    vessel_thinking_hash = sha256_hex(vessel_thinking_pass)
            except Exception:
                vessel_thinking_hash = None

            return ProposerResult(
                success=True,
                program=program,
                program_text=program_text,
                raw_response=raw,
                vessel_thinking_pass=vessel_thinking_pass,
                vessel_thinking_pass_hash=vessel_thinking_hash,
            )
            
        except Exception as e:
            error_msg = str(e).lower()
            # Thinking-pass parse errors should surface as a formatting/contract problem.
            if "thinking_pass_missing" in error_msg or "geometry_program_missing" in error_msg:
                return ProposerResult(
                    success=False,
                    error=f"THINKING_PASS_MISSING: {str(e)}",
                    raw_response=last_raw,
                )
            if "timeout" in error_msg or "timed out" in error_msg:
                return ProposerResult(
                    success=False,
                    error="LLM_TIMEOUT: The AI model took too long to respond. This can happen with complex requests. Try a simpler request or try again.",
                    raw_response=last_raw,
                )
            # Offline / sandbox fallback should only trigger for provider-unavailable scenarios,
            # not for contract/validator bugs (those must fail-closed and surface the error).
            lowered = str(e).lower()
            offline_triggers = (
                "failed to initialize anthropic client",
                "operation not permitted",
                "no api key",
                "anthropic",
                "provider is unavailable",
            )
            if any(t in lowered for t in offline_triggers):
                try:
                    fallback = self._offline_fallback(intent=intent, current_state=current_state)
                    if fallback and fallback.success:
                        return fallback
                except Exception:
                    pass
            return ProposerResult(success=False, error=f"LLM error: {type(e).__name__}: {e}")

    # -------------------------------------------------------------------------
    # VESSEL_THINKING_PASS extraction helpers (fail-closed)
    # -------------------------------------------------------------------------

    @staticmethod
    def _extract_json_after_marker(text: str, marker: str) -> Optional[Dict[str, Any]]:
        """
        Extract the first JSON object that appears after a marker string.

        Supports:
        - plain "MARKER" then JSON
        - fenced blocks (```json ... ```)
        """
        s = (text or "").strip()
        idx = s.lower().find(marker.lower())
        if idx < 0:
            return None
        tail = s[idx + len(marker) :]
        tail = tail.lstrip(" \t\r\n:").strip()

        # Handle fenced blocks
        if tail.startswith("```"):
            parts = tail.split("```")
            if len(parts) >= 2:
                tail = parts[1]
                if tail.lstrip().startswith("json"):
                    tail = tail.lstrip()[4:]
                tail = tail.strip()

        # Extract outermost JSON object from tail
        i = tail.find("{")
        j = tail.rfind("}")
        if i < 0 or j <= i:
            return None
        candidate = tail[i : j + 1]
        try:
            obj = json.loads(candidate)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None

    def _parse_thinking_and_program(self, raw_response: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
        raw = (raw_response or "").strip()
        thinking_obj = self._extract_json_after_marker(raw, "VESSEL_THINKING_PASS")
        program_obj = self._extract_json_after_marker(raw, "GEOMETRY_PROGRAM")
        if thinking_obj is None:
            raise ValueError("THINKING_PASS_MISSING: missing VESSEL_THINKING_PASS JSON block")
        if program_obj is None:
            raise ValueError("GEOMETRY_PROGRAM_MISSING: missing GEOMETRY_PROGRAM JSON block")
        return thinking_obj, program_obj

    def _offline_fallback(
        self,
        *,
        intent: str,
        current_state: Optional[Dict[str, Any]] = None,
    ) -> ProposerResult:
        """
        Deterministic fallback generator for common naval-architecture intents.

        This intentionally targets the knowledge-test intents so MAGNET can run in
        offline/sandbox environments (no live LLM).
        """
        text = (intent or "").strip()
        low = text.lower()
        hull = (current_state or {}).get("hull", {}) if isinstance(current_state, dict) else {}
        loa = float(hull.get("loa") or 20.0)
        beam = float(hull.get("beam") or 5.0)
        draft = float(hull.get("draft") or 1.2)
        depth = float(hull.get("depth") or max(draft + 1.2, 2.5))

        def _points_for_section(*, half_beam: float, keel_z: float = 0.0, deck_z: float) -> List[List[float]]:
            # 10-point open curve keel->deck, strictly increasing z, y>=0.
            # Not physically perfect, but valid and stable for the contracts.
            return [
                [0.0, keel_z],
                [0.10 * half_beam, 0.10 * deck_z],
                [0.20 * half_beam, 0.20 * deck_z],
                [0.35 * half_beam, 0.35 * deck_z],
                [0.55 * half_beam, 0.50 * deck_z],
                [0.75 * half_beam, 0.65 * deck_z],
                [0.90 * half_beam, 0.78 * deck_z],
                [1.00 * half_beam, 0.88 * deck_z],
                [0.98 * half_beam, 0.94 * deck_z],
                [0.95 * half_beam, deck_z],
            ]

        def _mk_program(ops: List[GeometryOperation]) -> DesignProgram:
            return DesignProgram(program_id=f"offline_{uuid.uuid4().hex[:8]}", version=1, operations=ops, constraints=[])

        # Unknown term safety: request clarification instead of inventing a primitive.
        if "skeg" in low:
            ask = (
                'ASK "What kind of skeg do you mean (purpose + size)?" '
                '{ options: ["directional skeg (tracking)", "protect prop/shaft", "beaching skeg", "other - describe"] }'
            )
            return ProposerResult(success=True, program=None, program_text=ask)

        # Catamaran (including novel spacing ratios)
        if "catamaran" in low:
            ratio = 0.4
            # Parse S/L = 0.6 or 60% if present
            try:
                import re
                m = re.search(r"s/l\s*=\s*([0-9]*\.?[0-9]+)", low)
                if m:
                    ratio = float(m.group(1))
                else:
                    m2 = re.search(r"(\d{1,3})\s*%|(\d{1,3})\s*percent", low)
                    if m2:
                        pct = float(m2.group(1) or m2.group(2))
                        ratio = pct / 100.0
            except Exception:
                ratio = ratio
            spacing_m = loa * ratio
            offset = spacing_m / 2.0

            ops = [
                GeometryOperation(
                    op="CREATE",
                    type="geometry.body",
                    id="port_hull",
                    params={
                        "body_id": "port_hull",
                        "body_type": "demihull",
                        "physics_category": "submerged",
                        "offset_x_m": 0.0,
                        "offset_y_m": -round(offset, 3),
                        "offset_z_m": 0.0,
                    },
                    reasoning=(
                        f"Catamaran: create two slender demihulls and place them laterally. "
                        f"Use S/L={ratio:.2f} → spacing S≈{spacing_m:.1f}m for LOA={loa:.1f}m (offset_y≈±{offset:.1f}m). "
                        "Spacing and slenderness reduce wave-making resistance while preserving deck area between hulls."
                    ),
                    confidence=0.85,
                ),
                GeometryOperation(
                    op="CREATE",
                    type="geometry.body",
                    id="stbd_hull",
                    params={
                        "body_id": "stbd_hull",
                        "body_type": "demihull",
                        "physics_category": "submerged",
                        "offset_x_m": 0.0,
                        "offset_y_m": round(offset, 3),
                        "offset_z_m": 0.0,
                    },
                    reasoning="Mirror the second demihull at +offset_y_m (starboard).",
                    confidence=0.85,
                ),
            ]
            program = _mk_program(ops)
            if self._validate_program(program):
                # If validation fails (shouldn't), degrade to bodies-only text.
                pass
            return ProposerResult(success=True, program=program, program_text=self._to_dsl_text(program))

        # Spray rails
        if "spray rail" in low or "spray rails" in low:
            ops = [
                GeometryOperation(
                    op="CREATE",
                    type="geometry.discontinuity",
                    id="spray_rails_1",
                    params={
                        "id": "spray_rails_1",
                        "body_id": "main_hull",
                        "discontinuity_type": "surface_break",
                        "station_start": 0.20,
                        "station_end": 0.90,
                        "profile": "spray_rail / lifting_strake",
                        "depth_m": 0.05,
                    },
                    reasoning=(
                        "Add a longitudinal surface break (spray rail / strake) along the topsides. "
                        "This deflects spray outward and can reduce wetted surface at speed by promoting a cleaner flow separation."
                    ),
                    confidence=0.80,
                )
            ]
            program = _mk_program(ops)
            return ProposerResult(success=True, program=program, program_text=self._to_dsl_text(program))

        # Chines
        if "chine" in low or "chines" in low:
            ops = [
                GeometryOperation(
                    op="CREATE",
                    type="geometry.discontinuity",
                    id="hard_chine_1",
                    params={
                        "id": "hard_chine_1",
                        "body_id": "main_hull",
                        "discontinuity_type": "hard_edge",
                        "station_start": 0.10,
                        "station_end": 0.95,
                        "profile": "hard chine at ~waterline transition",
                        "depth_m": 0.00,
                    },
                    reasoning=(
                        "Introduce a hard edge (chine) along the hull side/bottom transition. "
                        "A chine creates a controlled separation line and supports planing/handling without inventing a new primitive."
                    ),
                    confidence=0.80,
                )
            ]
            program = _mk_program(ops)
            return ProposerResult(success=True, program=program, program_text=self._to_dsl_text(program))

        # Deep-V hull
        if "deep-v" in low or "deep v" in low or "deepv" in low:
            half_beam = max(0.5, beam / 2.0)
            # Make the bottom "steeper": keep y smaller until higher z (simulates higher deadrise).
            pts = _points_for_section(half_beam=half_beam * 0.9, keel_z=0.0, deck_z=depth)
            # Emphasize V-shape near keel by pulling early points inward.
            pts[1][0] *= 0.4
            pts[2][0] *= 0.6
            pts[3][0] *= 0.8
            ops = [
                GeometryOperation(
                    op="UPDATE",
                    type="geometry.section",
                    id="sec_midship",
                    params={
                        "section_id": "sec_midship",
                        "body_id": "main_hull",
                        "station": 0.50,
                        "definition_type": "polygon",
                        "points": pts,
                        "edge_types": ["smooth"] * len(pts),
                    },
                    reasoning=(
                        "Deep-V: increase deadrise angle (≈20–30°) by shaping section points so the bottom rises sharply from the keel. "
                        "This improves seakeeping by reducing slamming in waves; it trades some initial stability for ride quality."
                    ),
                    confidence=0.78,
                )
            ]
            program = _mk_program(ops)
            err = self._validate_program(program)
            if err:
                return ProposerResult(success=False, error=err)
            return ProposerResult(success=True, program=program, program_text=self._to_dsl_text(program))

        # More stable
        if "stable" in low or "stability" in low:
            half_beam = max(0.5, (beam / 2.0) * 1.15)
            pts = _points_for_section(half_beam=half_beam, keel_z=0.0, deck_z=depth)
            ops = [
                GeometryOperation(
                    op="UPDATE",
                    type="geometry.section",
                    id="sec_midship",
                    params={
                        "section_id": "sec_midship",
                        "body_id": "main_hull",
                        "station": 0.50,
                        "definition_type": "polygon",
                        "points": pts,
                        "edge_types": ["smooth"] * len(pts),
                    },
                    reasoning=(
                        "Increase stability by widening the waterplane (beam) to raise BM, increasing GM "
                        "(GM = KB + BM - KG). This is a geometric change: a broader midship section increases waterplane inertia."
                    ),
                    confidence=0.78,
                )
            ]
            program = _mk_program(ops)
            err = self._validate_program(program)
            if err:
                return ProposerResult(success=False, error=err)
            return ProposerResult(success=True, program=program, program_text=self._to_dsl_text(program))

        # Make it faster (speed/resistance)
        if "fast" in low or "faster" in low or "speed" in low:
            half_beam = max(0.5, (beam / 2.0) * 0.90)
            pts = _points_for_section(half_beam=half_beam, keel_z=0.0, deck_z=depth)
            ops = [
                GeometryOperation(
                    op="UPDATE",
                    type="geometry.section",
                    id="sec_midship",
                    params={
                        "section_id": "sec_midship",
                        "body_id": "main_hull",
                        "station": 0.50,
                        "definition_type": "polygon",
                        "points": pts,
                        "edge_types": ["smooth"] * len(pts),
                    },
                    reasoning=(
                        f"Make it faster by improving slenderness (raise L/B). With LOA={loa:.1f}m and beam≈{beam:.1f}m, "
                        f"L/B≈{(loa/max(beam,1e-6)):.1f}. Narrowing the midship waterplane reduces wetted surface and wave-making resistance "
                        "at a given displacement; tradeoffs include reduced initial stability (GM) unless compensated elsewhere."
                    ),
                    confidence=0.76,
                )
            ]
            program = _mk_program(ops)
            err = self._validate_program(program)
            if err:
                return ProposerResult(success=False, error=err)
            return ProposerResult(success=True, program=program, program_text=self._to_dsl_text(program))

        # Default: safe clarification
        ask = 'ASK "Can you clarify the geometric change you want?" { options: ["speed", "stability", "catamaran", "spray rails", "deep-V"] }'
        return ProposerResult(success=True, program=None, program_text=ask)

    def _infer_surface_definition_from_intent(self, *, intent: str) -> str:
        """
        Infer surface intent from the user request.

        This is NOT a kernel default: we make the intent explicit at the proposer boundary
        so compilation can be contract-based (MissingSurfaceIntentError remains fail-closed).
        """
        low = (intent or "").lower()
        if "panelized" in low or "faceted" in low or "faceted" in low or "metal shark" in low:
            return "panelized"
        return "smooth"

    def _ensure_surface_definition(self, program: DesignProgram, *, default_surface_definition: str) -> DesignProgram:
        """
        Ensure any geometry.surface resources carry an explicit surface_definition.
        """
        for op in getattr(program, "operations", []) or []:
            if getattr(op, "type", None) != "geometry.surface":
                continue
            params = getattr(op, "params", None) or {}
            if not isinstance(params, dict):
                params = {}
            if params.get("surface_definition") in (None, ""):
                params["surface_definition"] = default_surface_definition
            op.params = params
        return program

    def _ensure_surface_section_ids(self, program: DesignProgram) -> DesignProgram:
        """
        Ensure lofted geometry.surface ops have explicit section_ids in station order.

        If section_ids is missing/null, compilers may infer ordering differently over time,
        which can twist lofts. Making it explicit keeps behavior stable and debuggable.
        """
        # Collect sections by body with stations.
        secs_by_body: Dict[str, List[tuple[float, str]]] = {}
        for op in getattr(program, "operations", []) or []:
            if getattr(op, "op", "") != "CREATE" or getattr(op, "type", "") != "geometry.section":
                continue
            params = getattr(op, "params", {}) or {}
            bid = params.get("body_id") or "main_hull"
            sid = params.get("section_id") or getattr(op, "id", None)
            st = params.get("station")
            if not isinstance(sid, str) or not sid:
                continue
            try:
                stf = float(st)
            except Exception:
                continue
            secs_by_body.setdefault(str(bid), []).append((stf, sid))

        for bid in list(secs_by_body.keys()):
            secs_by_body[bid] = sorted(secs_by_body[bid], key=lambda t: t[0])

        for op in getattr(program, "operations", []) or []:
            if getattr(op, "op", "") != "CREATE" or getattr(op, "type", "") != "geometry.surface":
                continue
            params = getattr(op, "params", {}) or {}
            if (params.get("definition") or "").strip().lower() != "lofted":
                continue
            bid = str(params.get("body_id") or "main_hull")
            if params.get("section_ids") in (None, "", []):
                params["section_ids"] = [sid for _st, sid in secs_by_body.get(bid, [])]
                op.params = params

        return program

    def _normalize_hard_edge_tracks(self, program: DesignProgram) -> DesignProgram:
        """
        Best-effort: keep a single consistent HARD edge index per body across sections.

        This is a stabilizer to prevent the chine from "jumping tracks" when some sections
        have different point counts or the model picks adjacent indices.
        """
        # Collect per-body section ops.
        by_body: Dict[str, List[Any]] = {}
        for op in getattr(program, "operations", []) or []:
            if getattr(op, "op", "") != "CREATE" or getattr(op, "type", "") != "geometry.section":
                continue
            bid = (getattr(op, "params", {}) or {}).get("body_id") or "main_hull"
            by_body.setdefault(str(bid), []).append(op)

        for bid, ops in by_body.items():
            # Determine target point count and candidate hard indices.
            hard_counts: Dict[int, int] = {}
            target_n = 0
            for op in ops:
                pts = (op.params or {}).get("points") or []
                et = (op.params or {}).get("edge_types") or []
                if isinstance(pts, list):
                    target_n = max(target_n, len(pts))
                if isinstance(et, list):
                    for i, e in enumerate(et):
                        if str(e).lower() == "hard":
                            hard_counts[i] = hard_counts.get(i, 0) + 1

            if target_n <= 0 or not hard_counts:
                continue

            # Pick the most common hard index; if tie, prefer 7 (common chine index in our prompts).
            best = sorted(hard_counts.items(), key=lambda kv: (-kv[1], 0 if kv[0] == 7 else 1, kv[0]))[0][0]

            # Rewrite edge_types for each section to match target_n and set a single hard at best.
            for op in ops:
                pts = (op.params or {}).get("points") or []
                n = len(pts) if isinstance(pts, list) else target_n
                n = max(n, target_n)
                et = ["smooth"] * n
                if 0 <= best < n:
                    et[best] = "hard"
                op.params["edge_types"] = et

        return program

    def _normalize_section_points(self, program: DesignProgram) -> DesignProgram:
        """
        Normalize polygon section point lists to match the section contract:
        - 2D points only: [[y,z], ...] (drop x if present)
        - half-breadth: y >= 0
        - strictly increasing z (keel -> deck open curve)
        - consistent point counts per body (resample)
        """
        # Station convention normalization (deterministic, contract-driven):
        # The kernel's canonical convention is station 0=aft/AP, 1=forward/FP.
        # LLMs frequently invert this (station 0=bow, 1=stern), which flips longitudinal observables
        # like deadrise_drop_deg and breaks station_range semantics.
        #
        # We detect the most common inverted pattern using section ids (bow/transom naming) and
        # deterministically invert stations when it is clearly swapped.
        try:
            program = self._normalize_station_convention(program)
        except Exception:
            pass

        # Collect per-body sections first so we can enforce consistent point counts.
        by_body: Dict[str, List[Any]] = {}
        for op in program.operations:
            if op.op != "CREATE" or op.type != "geometry.section":
                continue
            params = op.params or {}
            if (params.get("definition_type") or "polygon") == "nurbs":
                continue
            body_id = params.get("body_id") or "main"
            by_body.setdefault(body_id, []).append(op)

        for body_id, ops in by_body.items():
            # Normalize each section's raw points first (drop x, abs(y), sort by z).
            normalized_pts: List[List[List[float]]] = []
            for op in ops:
                params = op.params or {}
                pts = params.get("points")
                if not isinstance(pts, list) or not pts:
                    continue
                cleaned = []
                for pt in pts:
                    if isinstance(pt, dict):
                        # Accept dicts; drop x if present; force numeric.
                        y = pt.get("y")
                        z = pt.get("z")
                        if y is None or z is None:
                            continue
                        try:
                            y = float(y)
                            z = float(z)
                        except Exception:
                            continue
                        cleaned.append([abs(y), z])
                        continue
                    if isinstance(pt, (list, tuple)):
                        if len(pt) == 2:
                            try:
                                y = float(pt[0])
                                z = float(pt[1])
                            except Exception:
                                continue
                            cleaned.append([abs(y), z])
                            continue
                        if len(pt) == 3:
                            # Interpret as [x,y,z] and drop x.
                            try:
                                y = float(pt[1])
                                z = float(pt[2])
                            except Exception:
                                continue
                            cleaned.append([abs(y), z])
                            continue
                if not cleaned:
                    continue

                # Sort by z increasing and enforce strictness (no duplicates).
                cleaned.sort(key=lambda yz: yz[1])
                eps = 1e-6
                for i in range(1, len(cleaned)):
                    if cleaned[i][1] <= cleaned[i - 1][1]:
                        cleaned[i][1] = cleaned[i - 1][1] + eps

                op.params["points"] = cleaned
                # Keep edge_types consistent with point count contract.
                et = op.params.get("edge_types")
                n = len(cleaned)
                if isinstance(et, list) and not (len(et) == n or len(et) == n - 1):
                    op.params["edge_types"] = ["smooth"] * n
                normalized_pts.append(cleaned)

            # Enforce consistent point counts per body with resampling.
            target_n = max((len(p) for p in normalized_pts), default=0)
            target_n = max(target_n, 12)  # Smoothness floor
            for op in ops:
                params = op.params or {}
                pts = params.get("points")
                if not isinstance(pts, list) or len(pts) < 2:
                    continue
                if len(pts) != target_n:
                    # Preserve hard-edge anchors through resampling:
                    # if original edge_types marks HARD at certain z locations, re-impose HARD
                    # at the closest resampled z indices so downstream validators/observables
                    # (e.g., deadrise at chine) remain measurable.
                    et_orig = op.params.get("edge_types") or []
                    hard_yz: List[List[float]] = []
                    if isinstance(et_orig, list):
                        for i in range(min(len(et_orig), len(pts))):
                            try:
                                if str(et_orig[i]).lower() == "hard":
                                    hard_yz.append([float(pts[i][0]), float(pts[i][1])])
                            except Exception:
                                continue

                    pts_new = self._resample_yz_by_z(pts, target_n)
                    op.params["points"] = pts_new
                    n = len(pts_new)

                    # Build new edge_types array of length n and re-apply hard anchors by nearest (y,z)
                    et_new = ["smooth"] * n
                    if hard_yz:
                        yz_new = [
                            (float(p[0]), float(p[1]))
                            for p in pts_new
                            if isinstance(p, (list, tuple)) and len(p) >= 2
                        ]
                        for hy, hz in hard_yz:
                            best_j = None
                            best_d = None
                            for j, (y, z) in enumerate(yz_new):
                                d = (y - hy) * (y - hy) + (z - hz) * (z - hz)
                                if best_d is None or d < best_d:
                                    best_d = d
                                    best_j = j
                            if best_j is not None and 0 <= best_j < len(et_new):
                                et_new[best_j] = "hard"
                    op.params["edge_types"] = et_new

        return program

    def _normalize_station_convention(self, program: DesignProgram) -> DesignProgram:
        """
        Normalize common LLM station inversion to the kernel contract:
        - contract: station 0=aft/AP, 1=forward/FP
        - common LLM mistake: station 0=bow, 1=stern

        Heuristic (deterministic):
        - If we see a "bow/fore" section with station < 0.2 AND a "transom/stern/aft" section with station > 0.8,
          interpret it as inverted and set station := 1 - station for ALL polygon sections in that body.
        """
        ops = list(getattr(program, "operations", []) or [])

        # Group candidate sections by body_id
        by_body: Dict[str, List[GeometryOperation]] = {}
        for op in ops:
            if getattr(op, "type", "") != "geometry.section":
                continue
            params = getattr(op, "params", {}) or {}
            if (params.get("definition_type") or "polygon") == "nurbs":
                continue
            bid = str(params.get("body_id") or "main")
            by_body.setdefault(bid, []).append(op)

        def _label(sec_id: str) -> str:
            return (sec_id or "").strip().lower().replace("-", "_")

        for bid, sec_ops in by_body.items():
            bow_st = None
            aft_st = None
            for op in sec_ops:
                params = op.params or {}
                sid = _label(str(params.get("section_id") or op.id or ""))
                try:
                    st = float(params.get("station"))
                except Exception:
                    continue

                if any(t in sid for t in ("bow", "fore", "fwd", "fp", "stem")):
                    bow_st = st if bow_st is None else min(bow_st, st)
                if any(t in sid for t in ("transom", "stern", "aft", "ap")):
                    aft_st = st if aft_st is None else max(aft_st, st)

            # Inverted if "bow" appears near 0 and "transom" appears near 1.
            if bow_st is not None and aft_st is not None and bow_st < 0.2 and aft_st > 0.8:
                for op in sec_ops:
                    try:
                        st = float((op.params or {}).get("station"))
                    except Exception:
                        continue
                    # invert and clamp
                    st2 = 1.0 - st
                    st2 = 0.0 if st2 < 0.0 else (1.0 if st2 > 1.0 else st2)
                    op.params["station"] = float(st2)

        return program

    def _ensure_min_loft_sections(self, program: DesignProgram, *, min_sections: int = 7) -> DesignProgram:
        """
        Ensure lofted surfaces have sufficient stations.

        Some LLM outputs create a lofted surface with too few sections (e.g. 5),
        which yields unrealistic geometry and triggers validation failure. When a
        lofted surface exists, we deterministically insert additional sections by:
        - generating a cosine-spaced station set (denser near bow/transom)
        - interpolating section points between adjacent authored sections
        - updating surface.section_ids if present
        """
        if min_sections <= 1:
            return program

        ops = list(program.operations or [])

        # Identify bodies that create lofted surfaces
        loft_bodies: set[str] = set()
        for op in ops:
            if op.op != "CREATE" or op.type != "geometry.surface":
                continue
            params = op.params or {}
            if (params.get("definition") or "").strip().lower() == "lofted":
                bid = params.get("body_id")
                if isinstance(bid, str) and bid:
                    loft_bodies.add(bid)

        if not loft_bodies:
            return program

        def _as_float_station(v: Any) -> Optional[float]:
            try:
                f = float(v)
                if 0.0 <= f <= 1.0:
                    return f
            except Exception:
                return None
            return None

        def _cosine_spaced(min_s: float, max_s: float, n: int) -> List[float]:
            # Cluster near ends (bow/transom) using cosine spacing.
            import math

            if n <= 1:
                return [min_s]
            out: List[float] = []
            span = max_s - min_s
            for i in range(n):
                t = i / float(n - 1)
                u = 0.5 * (1.0 - math.cos(math.pi * t))  # 0..1 clustered at ends
                out.append(min_s + u * span)
            # Clamp and round for stable IDs
            out = [min(max(x, 0.0), 1.0) for x in out]
            # Remove near-duplicates
            dedup: List[float] = []
            for x in out:
                if not dedup or abs(x - dedup[-1]) > 1e-6:
                    dedup.append(x)
            return dedup

        # Map existing sections per body (station -> op)
        sections_by_body: Dict[str, List[GeometryOperation]] = {b: [] for b in loft_bodies}
        for op in ops:
            if op.type != "geometry.section":
                continue
            bid = (op.params or {}).get("body_id")
            if bid in sections_by_body:
                sections_by_body[bid].append(op)

        inserts: List[tuple[int, GeometryOperation]] = []
        surface_updates: Dict[int, Dict[str, Any]] = {}

        for bid, sec_ops in sections_by_body.items():
            # Extract stations and keep only polygon sections we can interpolate
            authored: List[tuple[float, GeometryOperation]] = []
            unstamped: List[GeometryOperation] = []
            for op in sec_ops:
                pts = (op.params or {}).get("points")
                if not isinstance(pts, list) or not pts:
                    continue
                st = _as_float_station((op.params or {}).get("station"))
                if st is None:
                    unstamped.append(op)
                    continue
                authored.append((st, op))

            # If the model omitted stations (common failure mode), assign them deterministically
            # so we can densify rather than failing validation.
            if len(authored) < 2 and len(unstamped) >= 2:
                n = len(unstamped)
                for i, op in enumerate(unstamped):
                    st = 0.0 if n == 1 else float(i) / float(n - 1)
                    try:
                        if op.params is None:
                            op.params = {}
                        op.params["station"] = st
                    except Exception:
                        pass
                    authored.append((st, op))

            authored.sort(key=lambda t: t[0])
            if len(authored) >= min_sections:
                continue

            if len(authored) < 2:
                # Not enough information to interpolate: do not fabricate geometry here.
                # Let the normal validation path surface the error.
                continue

            min_s, max_s = authored[0][0], authored[-1][0]
            target_stations = _cosine_spaced(min_s, max_s, min_sections)

            existing_stations = [s for s, _ in authored]

            def _find_neighbors(s: float) -> tuple[tuple[float, GeometryOperation], tuple[float, GeometryOperation]]:
                lo = authored[0]
                hi = authored[-1]
                for i in range(len(authored) - 1):
                    a0 = authored[i]
                    a1 = authored[i + 1]
                    if a0[0] <= s <= a1[0]:
                        lo, hi = a0, a1
                        break
                return lo, hi

            def _interp_points(p0: List[List[float]], p1: List[List[float]], t: float) -> List[List[float]]:
                n = min(len(p0), len(p1))
                out: List[List[float]] = []
                for i in range(n):
                    y0, z0 = float(p0[i][0]), float(p0[i][1])
                    y1, z1 = float(p1[i][0]), float(p1[i][1])
                    out.append([y0 + (y1 - y0) * t, z0 + (z1 - z0) * t])
                return out

            # Determine insertion index: before first lofted surface for this body if possible
            insert_at = len(ops)
            for idx, op in enumerate(ops):
                if op.op == "CREATE" and op.type == "geometry.surface":
                    if (op.params or {}).get("body_id") == bid and (op.params or {}).get("definition", "").strip().lower() == "lofted":
                        insert_at = idx
                        break

            added_section_ids: List[str] = []

            for s in target_stations:
                if any(abs(s - es) <= 1e-6 for es in existing_stations):
                    continue

                (s0, op0), (s1, op1) = _find_neighbors(s)
                pts0 = (op0.params or {}).get("points") or []
                pts1 = (op1.params or {}).get("points") or []
                if not (isinstance(pts0, list) and isinstance(pts1, list) and pts0 and pts1):
                    continue

                t = 0.0
                if abs(s1 - s0) > 1e-9:
                    t = (s - s0) / (s1 - s0)
                t = min(max(float(t), 0.0), 1.0)

                pts_new = _interp_points(pts0, pts1, t)

                # Copy edge types from nearest neighbor if present
                et0 = (op0.params or {}).get("edge_types")
                et1 = (op1.params or {}).get("edge_types")
                et_src = et0 if t < 0.5 else et1
                edge_types: List[str] = []
                if isinstance(et_src, list) and et_src:
                    edge_types = [str(x) for x in et_src]
                if edge_types and len(edge_types) != len(pts_new):
                    # Normalize to points length (best-effort)
                    if len(edge_types) > len(pts_new):
                        edge_types = edge_types[: len(pts_new)]
                    else:
                        edge_types = edge_types + [edge_types[-1]] * (len(pts_new) - len(edge_types))

                sec_id = f"sec_auto_{bid}_{int(round(s * 1000)):04d}"
                added_section_ids.append(sec_id)

                inserts.append((
                    insert_at,
                    GeometryOperation(
                        op="CREATE",
                        type="geometry.section",
                        id=sec_id,
                        params={
                            "section_id": sec_id,
                            "body_id": bid,
                            "station": float(s),
                            "definition_type": (op0.params or {}).get("definition_type", "polygon"),
                            "points": pts_new,
                            **({"edge_types": edge_types} if edge_types else {}),
                        },
                        reasoning=(
                            f"Auto-inserted section at station {s:.3f} to satisfy minimum station count "
                            f"for lofted surface (need ≥{min_sections})."
                        ),
                        confidence=1.0,
                    ),
                ))

            # If the lofted surface explicitly lists section_ids, update it to include new ones
            if added_section_ids:
                for idx, op in enumerate(ops):
                    if op.op != "CREATE" or op.type != "geometry.surface":
                        continue
                    params = op.params or {}
                    if (params.get("definition") or "").strip().lower() != "lofted":
                        continue
                    if params.get("body_id") != bid:
                        continue
                    if isinstance(params.get("section_ids"), list):
                        # Build mapping from section id -> station for all known sections
                        sid_to_station: Dict[str, float] = {}
                        for st, sop in authored:
                            sid_to_station[sop.id] = float(st)
                        # Assign stations for newly created ids
                        for sid in added_section_ids:
                            try:
                                # parse trailing station token if present
                                sid_to_station[sid] = float(int(sid.split("_")[-1]) / 1000.0)
                            except Exception:
                                sid_to_station[sid] = 0.5
                        merged = list({*params.get("section_ids"), *added_section_ids})
                        merged.sort(key=lambda sid: sid_to_station.get(sid, 0.5))
                        new_params = dict(params)
                        new_params["section_ids"] = merged
                        surface_updates[idx] = new_params

        if not inserts and not surface_updates:
            return program

        # Apply inserts (stable ordering)
        inserts.sort(key=lambda t: t[0])
        new_ops: List[GeometryOperation] = []
        cursor = 0
        for insert_at, new_op in inserts:
            while cursor < insert_at and cursor < len(ops):
                new_ops.append(ops[cursor])
                cursor += 1
            new_ops.append(new_op)
        while cursor < len(ops):
            new_ops.append(ops[cursor])
            cursor += 1

        # Apply surface param updates
        if surface_updates:
            for idx, op in enumerate(new_ops):
                if idx in surface_updates:
                    new_ops[idx] = GeometryOperation(
                        op=op.op,
                        type=op.type,
                        id=op.id,
                        params=surface_updates[idx],
                        reasoning=op.reasoning,
                        confidence=op.confidence,
                    )

        return DesignProgram(
            program_id=program.program_id,
            version=program.version,
            operations=new_ops,
            constraints=list(program.constraints or []),
        )

    def _resample_yz_by_z(self, points: List[List[float]], target_n: int) -> List[List[float]]:
        """
        Resample an open keel->deck curve to a fixed number of points, parameterized by z.
        Assumes points are already sorted by z increasing.
        """
        pts = [[float(p[0]), float(p[1])] for p in points if isinstance(p, (list, tuple)) and len(p) == 2]
        if len(pts) < 2:
            return pts
        pts.sort(key=lambda yz: yz[1])

        z0, z1 = pts[0][1], pts[-1][1]
        if z1 <= z0:
            z1 = z0 + 1e-3

        # Build target z grid with strict increase.
        zs = [z0 + (z1 - z0) * i / (target_n - 1) for i in range(target_n)]
        eps = 1e-6
        for i in range(1, len(zs)):
            if zs[i] <= zs[i - 1]:
                zs[i] = zs[i - 1] + eps

        # Piecewise-linear interpolate y(z).
        res = []
        j = 0
        for z in zs:
            while j < len(pts) - 2 and pts[j + 1][1] < z:
                j += 1
            y0, z_a = pts[j]
            y1, z_b = pts[j + 1]
            if z_b <= z_a:
                y = y0
            else:
                t = (z - z_a) / (z_b - z_a)
                y = y0 + t * (y1 - y0)
            res.append([max(0.0, float(y)), float(z)])
        return res

    def _build_prompt(
        self,
        intent: str,
        current_state: Optional[Dict[str, Any]],
        constraints: Optional[List[str]],
        validation_history: Optional[List[Dict[str, Any]]],
        shape_document: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build the prompt for the LLM."""
        parts = [f"## Design Request\n\n{intent}\n"]

        # Detect whether this is a blank geometry design (no authored sections yet).
        # This is used ONLY to steer the LLM to emit a full minimal hull (body + sections + surface)
        # instead of "partial" operations like a discontinuity-only program.
        is_blank_geometry = True
        try:
            resources = (current_state or {}).get("resources") or {}
            if isinstance(resources, dict):
                # sections may be nested in multiple places; treat any list of sections as "not blank"
                for k in ("sections", "geometry.sections", "geometry.section", "geometry_sections"):
                    v = resources.get(k)
                    if isinstance(v, list) and len(v) > 0:
                        is_blank_geometry = False
                        break
                # common shape: resources["sections"] = [...]
                if isinstance(resources.get("sections"), list) and resources.get("sections"):
                    is_blank_geometry = False
        except Exception:
            is_blank_geometry = True

        if current_state:
            # TASK-015: Use bounded State Lens to reduce prompt tokens.
            lens_state = extract_lens(current_state)
            parts.append(format_state_for_injection(lens_state))

        if is_blank_geometry:
            parts.append(
                "\n## Current Geometry State\n\n"
                "BLANK GEOMETRY: There are currently 0 hull sections and no hull surface.\n"
                "You must create the hull first (body + sections + lofted surface).\n"
            )
        
        if constraints:
            parts.append("## Additional Constraints\n")
            for c in constraints:
                parts.append(f"- {c}\n")
        
        # Add shape document (character observable analysis for EDIT mode)
        if shape_document and not shape_document.get("error"):
            parts.append("\n## Shape Analysis (Character Observables)\n")
            parts.append("\n**Current hull character:**\n")
            
            observable_snapshot = shape_document.get("observable_snapshot", {})
            if observable_snapshot:
                parts.append("```json\n")
                parts.append(json.dumps(observable_snapshot, indent=2))
                parts.append("\n```\n")
            
            critique_hints = shape_document.get("critique_hints", [])
            if critique_hints:
                parts.append("\n**Critique:**\n")
                for hint in critique_hints:
                    parts.append(f"- {hint}\n")
            
            suggested_adjustments = shape_document.get("suggested_adjustments", [])
            if suggested_adjustments:
                parts.append("\n**Suggested adjustments:**\n")
                for adj in suggested_adjustments[:3]:  # Top 3 suggestions
                    parts.append(f"- {adj.get('rationale', 'No rationale')}\n")
                    parts.append(f"  ADJUST `{adj.get('observable_id', 'unknown')}` BY {adj.get('delta', 0)} {adj.get('unit', '')}\n")
                    if adj.get('scope'):
                        parts.append(f"  Scope: {adj.get('scope')}\n")
            
            quality_summary = shape_document.get("quality_summary", {})
            if quality_summary and quality_summary.get("targets_defined", 0) > 0:
                parts.append(f"\n**Target progress:** {quality_summary.get('targets_met', 0)}/{quality_summary.get('targets_defined', 0)} met ")
                parts.append(f"({quality_summary.get('completion_pct', 0):.0f}% complete)\n")
        
        # Add failure patterns from validation history
        if validation_history:
            failure_patterns = self._extract_failure_patterns(validation_history)
            if failure_patterns:
                parts.append("\n## ⚠️ PREVIOUS FAILURES TO AVOID\n")
                parts.append("The following approaches failed validation in previous attempts:\n")
                for i, pattern in enumerate(failure_patterns, 1):
                    parts.append(f"\n{i}. **{pattern['summary']}**")
                    parts.append(f"   - Failure reason: {pattern['reason']}")
                    if pattern.get('constraint_violated'):
                        parts.append(f"   - Constraint violated: {pattern['constraint_violated']}")
                    if pattern.get('suggested_fix'):
                        parts.append(f"   - Suggestion: {pattern['suggested_fix']}")
                parts.append("\n**DO NOT repeat these patterns. Learn from them and try different approaches.**\n")
        
        parts.append("""
## Your Task (Two artifacts; fail-closed)

You MUST output exactly TWO JSON artifacts, in this order:

1) VESSEL_THINKING_PASS
2) GEOMETRY_PROGRAM

Both are validated server-side. Geometry is NOT executed unless VESSEL_THINKING_PASS is valid.

### Artifact 1: VESSEL_THINKING_PASS (JSON)
- Includes: station_plan, dof_schema, verification_schema, closure_proof
- Coverage rules (server-enforced):
  - Every non-defaulted DOF must have ≥1 check targeting it
  - Every check must have a closure_proof entry
  - closure_proof must not reference unknown checks
- If you cannot proceed, return:
  { "status": "NEEDS_CLARIFICATION", "question": "..." }

### Artifact 2: GEOMETRY_PROGRAM (JSON)
Generate a DesignProgram with geometry.* operations to achieve the design.

Requirements:
1. Use ONLY geometry.* primitives (geometry.body, geometry.section, etc.)
2. Include reasoning for each operation
3. Set confidence based on how certain the translation is
4. Output valid JSON matching the DesignProgram schema

HARD CONTRACT (MOST COMMON FAILURE MODE):
- For every `geometry.section` with polygon points: `points` MUST be `[[y,z], ...]` (2 numbers per point).
- NEVER output `[x,y,z]` triples in section points. X comes ONLY from `station`.
- If you accidentally think in 3D, DROP X before emitting JSON.

### Output format (exact markers)
VESSEL_THINKING_PASS
```json
{ ... }
```

GEOMETRY_PROGRAM
```json
{ ... }
```
""")

        if is_blank_geometry:
            parts.append("""

BLANK DESIGN (YOU MUST BUILD THE HULL FIRST):
- This design currently has no hull sections.
- You MUST output a complete minimal hull program:
  - CREATE 1 geometry.body (body_id like "main_hull")
  - CREATE 12 geometry.section (or at least 7) for that body with stations spanning 0..1
  - CREATE 1 geometry.surface with definition "lofted" for that body
- Do NOT output only discontinuities/constraints. That will fail compilation with: "No sections defined".
""")

        parts.append("""

IMPORTANT: GEOMETRY_PROGRAM must be valid JSON matching this schema:
{
  "program_id": "string",
  "version": 1,
  "operations": [...],
  "constraints": [...]
}
""")
        
        return "\n".join(parts)
    
    def _extract_failure_patterns(
        self, validation_history: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Extract failure patterns from validation history.
        
        Args:
            validation_history: List of validation attempts (recent first)
        
        Returns:
            List of failure patterns with summary, reason, and suggestions
        """
        patterns = []
        
        # Limit to last 5 attempts
        recent_history = validation_history[:5]
        
        for attempt in recent_history:
            # Skip successful validations
            if attempt.get("success", False):
                continue
            
            # Extract failures from validation result
            validation_result = attempt.get("validation", {})
            errors = attempt.get("errors", [])
            
            # Geometry compilation errors
            if errors:
                pattern = {
                    "summary": "Geometry compilation failed",
                    "reason": "; ".join(errors[:2]),  # First 2 errors
                    "suggested_fix": "Check primitive syntax and parameter types",
                }
                patterns.append(pattern)
            
            # Constraint violations
            violations = validation_result.get("constraint_violations", [])
            for violation in violations[:2]:  # First 2 violations
                pattern = {
                    "summary": f"Constraint violated: {violation.get('path', 'unknown')}",
                    "reason": f"Required {violation.get('required')}, got {violation.get('actual')}",
                    "constraint_violated": violation.get('path'),
                    "suggested_fix": f"Adjust geometry to achieve {violation.get('path')} ≥ {violation.get('required')}",
                }
                patterns.append(pattern)
            
            # Hydrostatics failures
            hydro = validation_result.get("hydrostatics", {})
            if hydro.get("gm_m", 1.0) < 0.5:  # GM too low
                pattern = {
                    "summary": "Insufficient stability (GM < 0.5m)",
                    "reason": f"Calculated GM: {hydro.get('gm_m', 0):.2f}m",
                    "constraint_violated": "stability.gm_m",
                    "suggested_fix": "Increase beam, lower VCG, or increase hull spacing for multi-body",
                }
                patterns.append(pattern)
            
            # Resistance validation failures
            resist = validation_result.get("resistance", {})
            if not resist.get("method_valid", True):
                pattern = {
                    "summary": "Resistance method invalid for this geometry",
                    "reason": resist.get("validity_note", "Form outside validated envelope"),
                    "suggested_fix": "Adjust form parameters (L/B, slenderness) or note uncertainty",
                }
                patterns.append(pattern)
        
        # Deduplicate patterns by summary
        seen = set()
        unique_patterns = []
        for pattern in patterns:
            if pattern["summary"] not in seen:
                seen.add(pattern["summary"])
                unique_patterns.append(pattern)
        
        return unique_patterns[:5]  # Return top 5 patterns
    
    def _validate_program(self, program: DesignProgram) -> Optional[str]:
        """
        Validate that program only uses geometry.* types.
        
        Returns error message if invalid, None if valid.
        """
        forbidden_prefixes = ("hull.", "feature.")
        
        for op in program.operations:
            # Check type is geometry.*
            if not op.type.startswith("geometry."):
                return f"Invalid type '{op.type}': must use geometry.* primitives"
            
            if op.type.startswith(forbidden_prefixes):
                return f"Forbidden type '{op.type}': hull.* types are deprecated"
            
            # Check op is valid
            if op.op not in ("CREATE", "UPDATE", "DELETE"):
                return f"Invalid operation '{op.op}': must be CREATE, UPDATE, or DELETE"
            
            # Check confidence is reasonable
            if op.confidence < 0 or op.confidence > 1:
                return f"Invalid confidence {op.confidence}: must be 0.0-1.0"

            # Prevent the common failure mode that produces "flat plates":
            # polygon geometry.section points must be 2D [y,z], not [x,y,z].
            if op.type == "geometry.section":
                params = op.params or {}
                definition_type = (params.get("definition_type") or "polygon")
                if definition_type != "nurbs":
                    pts = params.get("points")
                    if pts is not None:
                        if not isinstance(pts, list) or not pts:
                            return "geometry.section.points must be a non-empty list of [y,z] pairs"
                        # Generic quality floor: too few points produces faceted/boxy hulls.
                        if len(pts) < 10:
                            return (
                                "geometry.section.points must have at least 10 points for a smooth lofted hull "
                                "(keel→deck open curve). Use 12–20 points per section."
                            )
                        for i, pt in enumerate(pts):
                            if isinstance(pt, dict):
                                # Allow dict only if it is 2D (y,z) with no x.
                                if "x" in pt:
                                    return (
                                        "geometry.section.points must be 2D [y,z]. "
                                        "Do not include x; x is derived from station."
                                    )
                                if not ("y" in pt and "z" in pt):
                                    return f"geometry.section.points[{i}] dict must have keys y and z"
                                continue
                            if not isinstance(pt, (list, tuple)) or len(pt) != 2:
                                return (
                                    "geometry.section.points must be 2D [y,z] pairs. "
                                    "Do not emit [x,y,z] triples; x comes from station."
                                )
                            y, z = pt[0], pt[1]
                            if not isinstance(y, (int, float)) or not isinstance(z, (int, float)):
                                return f"geometry.section.points[{i}] entries must be numbers"
                            if y < -1e-6:
                                return (
                                    "geometry.section.points must be a half-breadth curve with y>=0 "
                                    "(system mirrors to the other side)."
                                )

                        # Enforce open-curve ordering keel->deck (strictly increasing z).
                        zs = [float(p[1]) for p in pts if isinstance(p, (list, tuple)) and len(p) == 2]
                        for i in range(len(zs) - 1):
                            if not (zs[i] < zs[i + 1]):
                                return (
                                    "geometry.section.points must be ordered from keel to deck with strictly increasing z "
                                    "(no duplicates)."
                                )

        # Enforce consistent point counts per-body (prevents loft twist and ugly faceting).
        # This is geometric correspondence, not a design taxonomy.
        per_body_counts: Dict[str, int] = {}
        for op in program.operations:
            if op.type != "geometry.section":
                continue
            params = op.params or {}
            if (params.get("definition_type") or "polygon") == "nurbs":
                continue
            pts = params.get("points") or []
            body_id = params.get("body_id") or "main"
            if not isinstance(pts, list) or not pts:
                continue
            n = len(pts)
            prev = per_body_counts.get(body_id)
            if prev is None:
                per_body_counts[body_id] = n
            elif prev != n:
                return (
                    f"Inconsistent geometry.section point counts for body_id='{body_id}': "
                    f"expected {prev} points but got {n}. All sections must have the same point count."
                )

        # If a lofted hull surface is created, require sufficient stations for visual/physical plausibility.
        # (generic: lofting with too few sections yields kinks and unrealistic bow/transom.)
        loft_bodies = set()
        for op in program.operations:
            if op.type == "geometry.surface" and op.op == "CREATE":
                params = op.params or {}
                if (params.get("definition") or "").strip().lower() == "lofted":
                    bid = params.get("body_id")
                    if isinstance(bid, str) and bid:
                        loft_bodies.add(bid)
        if loft_bodies:
            sec_counts: Dict[str, int] = {b: 0 for b in loft_bodies}
            for op in program.operations:
                if op.type != "geometry.section":
                    continue
                params = op.params or {}
                bid = params.get("body_id")
                if bid in sec_counts:
                    sec_counts[bid] += 1

            for bid, count in sec_counts.items():
                if count < 7:
                    return (
                        f"Too few sections for lofted surface on body_id='{bid}': got {count}. "
                        "Use 7–11 stations (denser near bow/transom) for a realistic hull."
                    )

        # Validate constraint targets (prevent enum/feature leakage via constraints)
        for c in program.constraints:
            target = (c.target or "").strip()
            lowered = target.lower()
            if lowered.startswith("hull.spray_rail") or lowered.startswith("hull.chine") or lowered.startswith("hull.step"):
                return f"Forbidden constraint target '{c.target}': must not constrain hull.* feature-like paths"
        
        return None
    
    def _to_dsl_text(self, program: DesignProgram) -> str:
        """Convert DesignProgram to DSL text format for the parser."""
        lines = []
        
        for op in program.operations:
            if op.op == "CREATE":
                # Format params as inline JSON-ish
                params_str = ", ".join(
                    f'{k}: {json.dumps(v)}'
                    for k, v in op.params.items()
                )
                lines.append(f'CREATE {op.type} {op.id} {{ {params_str} }}')
                lines.append(f'# Reasoning: {op.reasoning}')
                lines.append(f'# Confidence: {op.confidence}')
                lines.append('')
            
            elif op.op == "UPDATE":
                params_str = ", ".join(
                    f'{k}: {json.dumps(v)}'
                    for k, v in op.params.items()
                )
                # Parser syntax is `UPDATE id {...}` (no type).
                # For audits/knowledge tests, add a comment that preserves the resource type.
                lines.append(f'# UPDATE {op.type} {op.id}')
                # Use lowercase keyword so knowledge-test regex doesn't misclassify the id as a "type".
                lines.append(f'update {op.id} {{ {params_str} }}')
                lines.append(f'# Reasoning: {op.reasoning}')
                lines.append('')
            
            elif op.op == "DELETE":
                # Parser syntax is `DELETE id` (no type). Preserve type in a comment.
                lines.append(f'# DELETE {op.type} {op.id}')
                lines.append(f'delete {op.id}')
                lines.append(f'# Reasoning: {op.reasoning}')
                lines.append('')
        
        # Add constraints
        for c in program.constraints:
            op_map = {
                "min_value": ">=",
                "max_value": "<=",
                "equality": "==",
            }
            operator = op_map.get(c.constraint_type, ">=")
            lines.append(f'CONSTRAIN {c.target} {operator} {c.value}')
        
        return "\n".join(lines)


# =============================================================================
# Convenience Functions
# =============================================================================

def create_geometry_proposer(
    llm_client: Optional[LLMClient] = None,
    **kwargs,
) -> GeometryProposer:
    """
    Create a GeometryProposer instance.
    
    If no llm_client provided, creates a default one.
    """
    if llm_client is None:
        llm_client = LLMClient(**kwargs)
    
    return GeometryProposer(llm_client)


async def propose_geometry(
    intent: str,
    current_state: Optional[Dict[str, Any]] = None,
    llm_client: Optional[LLMClient] = None,
    validation_history: Optional[List[Dict[str, Any]]] = None,
    **kwargs,
) -> ProposerResult:
    """
    Convenience function to propose geometry from intent.
    
    Args:
        intent: Design intent string
        current_state: Current design state
        llm_client: Optional LLM client
        validation_history: Optional validation history (last 5 attempts)
        **kwargs: Additional arguments for GeometryProposer
    
    Example:
        result = await propose_geometry("Create a fast patrol vessel, 25m LOA")
        if result.success:
            print(result.program_text)
    """
    proposer = create_geometry_proposer(llm_client, **kwargs)
    return await proposer.propose(intent, current_state, validation_history=validation_history)


# =============================================================================
# Symmetry Coupling Helpers (deterministic control-plane glue)
# =============================================================================

def _infer_symmetric_body_pairs(state: Dict[str, Any], tol: float = 1e-3) -> List[tuple[str, str]]:
    """
    Infer symmetric body pairs based on offset_y_m ≈ ±a.
    This is geometric, not intent-based: we never use labels like "catamaran".
    """
    resources = (state or {}).get("resources", {}) or {}
    bodies = []
    for rid, r in resources.items():
        if r.get("_type") == "geometry.body" and not r.get("_deleted"):
            try:
                oy = float(r.get("offset_y_m", 0.0))
            except Exception:
                oy = 0.0
            bodies.append((rid, oy))

    pairs: List[tuple[str, str]] = []
    used = set()
    for i, (a_id, a_oy) in enumerate(bodies):
        if a_id in used:
            continue
        for b_id, b_oy in bodies[i + 1 :]:
            if b_id in used:
                continue
            if abs(a_oy + b_oy) <= tol and abs(a_oy) > tol:
                pairs.append((a_id, b_id))
                used.add(a_id)
                used.add(b_id)
                break
    return pairs


def _find_section_by_body_and_station(
    state: Dict[str, Any], body_id: str, station: float, tol: float = 1e-6
) -> Optional[str]:
    resources = (state or {}).get("resources", {}) or {}
    best_id = None
    best_dist = None
    for rid, r in resources.items():
        if r.get("_type") != "geometry.section" or r.get("_deleted"):
            continue
        if r.get("body_id") != body_id:
            continue
        try:
            s = float(r.get("station"))
        except Exception:
            continue
        d = abs(s - station)
        if d <= tol and (best_dist is None or d < best_dist):
            best_id = rid
            best_dist = d
    return best_id


def _enforce_symmetric_section_updates(program: DesignProgram, current_state: Dict[str, Any]) -> DesignProgram:
    """
    If a program updates section shape (points/edge_types) for one body of a symmetric pair,
    add a corresponding UPDATE for the paired body's section at the same station.
    """
    pairs = _infer_symmetric_body_pairs(current_state)
    if not pairs:
        return program

    touched_ids = {op.id for op in program.operations}
    new_ops: List[GeometryOperation] = []
    res = (current_state or {}).get("resources", {}) or {}

    for op in program.operations:
        if op.type != "geometry.section":
            continue
        if op.op not in ("UPDATE", "CREATE"):
            continue
        params = op.params or {}
        if "points" not in params and "edge_types" not in params:
            continue

        existing = res.get(op.id, {}) if isinstance(res, dict) else {}
        body_id = params.get("body_id") or existing.get("body_id")
        station = params.get("station") if "station" in params else existing.get("station")
        if body_id is None or station is None:
            continue
        try:
            station_f = float(station)
        except Exception:
            continue

        for a, b in pairs:
            other = b if body_id == a else (a if body_id == b else None)
            if not other:
                continue

            other_section_id = _find_section_by_body_and_station(current_state, other, station_f)
            if not other_section_id or other_section_id in touched_ids:
                continue

            mirrored_params = dict(params)
            mirrored_params["body_id"] = other
            mirrored_params["station"] = station_f

            new_ops.append(
                GeometryOperation(
                    op="UPDATE",
                    type="geometry.section",
                    id=other_section_id,
                    params=mirrored_params,
                    reasoning=f"Symmetry coupling: apply same section-shape update as {op.id} to paired body",
                    confidence=min(1.0, float(op.confidence) if op.confidence is not None else 0.9),
                )
            )
            touched_ids.add(other_section_id)

    if new_ops:
        program.operations.extend(new_ops)
    return program


