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

SECTION POINTS COORDINATE CONTRACT (CRITICAL):
- For polygon sections, `points` is a 2D cross-section profile: `[[y, z], ...]`
- DO NOT include X in points (NO `[x,y,z]` triples). X is derived ONLY from `station`.
- If you need 3D points, use primitives that explicitly take 3D coordinates (e.g., flow_path inlet/outlet).

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

See docs/architecture/GEOMETRY_CONVENTIONS.md for full specification.

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

5. ❌ **Z increasing downward**: Z should be NEGATIVE below waterline, POSITIVE above
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
- For polygon sections: `points` is strictly `[[y, z], ...]` where z=0 is waterline and z<0 is below waterline.
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
    ) -> ProposerResult:
        """
        Convert design intent to geometry program.
        
        Args:
            intent: Natural language design request
            current_state: Current design state (optional)
            constraints: Additional constraints (optional)
            validation_history: List of previous validation attempts (last 5)
            
        Returns:
            ProposerResult with DesignProgram if successful
        """
        # Build prompt with validation history
        prompt = self._build_prompt(intent, current_state, constraints, validation_history)
        
        try:
            # Call LLM with structured output
            # Use longer timeout (45s) for geometry proposals - they're complex prompts
            # that need time to generate detailed section coordinates.
            from magnet.llm.protocol import LLMOptions
            options = LLMOptions(timeout_seconds=45)
            
            program = await self._llm.complete_json(
                prompt,
                response_model=DesignProgram,
                system_prompt=GEOMETRY_PROPOSER_SYSTEM_PROMPT,
                options=options,
            )
            
            # Validate output
            validation_error = self._validate_program(program)
            if validation_error:
                return ProposerResult(
                    success=False,
                    error=validation_error,
                    raw_response=str(program),
                )

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
            
            return ProposerResult(
                success=True,
                program=program,
                program_text=program_text,
            )
            
        except Exception as e:
            error_msg = str(e).lower()
            if "timeout" in error_msg or "timed out" in error_msg:
                return ProposerResult(
                    success=False,
                    error="LLM_TIMEOUT: The AI model took too long to respond. This can happen with complex requests. Try a simpler request or try again.",
                )
            return ProposerResult(
                success=False,
                error=f"LLM error: {str(e)}",
            )

    def _build_prompt(
        self,
        intent: str,
        current_state: Optional[Dict[str, Any]],
        constraints: Optional[List[str]],
        validation_history: Optional[List[Dict[str, Any]]],
    ) -> str:
        """Build the prompt for the LLM."""
        parts = [f"## Design Request\n\n{intent}\n"]
        
        if current_state:
            parts.append(format_state_for_injection(current_state))
        
        if constraints:
            parts.append("## Additional Constraints\n")
            for c in constraints:
                parts.append(f"- {c}\n")
        
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
## Your Task

Generate a DesignProgram with geometry.* operations to achieve this design.

Requirements:
1. Use ONLY geometry.* primitives (geometry.body, geometry.section, etc.)
2. Include reasoning for each operation
3. Set confidence based on how certain the translation is
4. Output valid JSON matching the DesignProgram schema

IMPORTANT: Your response must be valid JSON matching this schema:
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
                lines.append(f'UPDATE {op.id} {{ {params_str} }}')
                lines.append(f'# Reasoning: {op.reasoning}')
                lines.append('')
            
            elif op.op == "DELETE":
                lines.append(f'DELETE {op.id}')
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


