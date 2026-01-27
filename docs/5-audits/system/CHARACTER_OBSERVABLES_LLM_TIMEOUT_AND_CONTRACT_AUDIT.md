## LLM CREATE Timeout + Contract Failures — Prompt Capture & Audit
Generated: `2026-01-20T04:01:10.369877+00:00`

### Summary
This file captures the **exact prompts** used by the Geometry Proposer for a representative CREATE request, and documents why CREATE can still fail even after increasing time budgets.

### Environment assumptions
- **UI request timeout**: `magnet/ui_v2/js/spiral-adapter.js` abort window
- **Server LLM timeout**: `MAGNET_GEOMETRY_PROPOSER_TIMEOUT_SECONDS` (default now 180)
- **Server max tokens**: `MAGNET_GEOMETRY_PROPOSER_MAX_TOKENS` (default now 3500)

### Prompt 1 — System Prompt (full)
```text
You are MAGNET's Geometry Proposer.

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

```

### Prompt 2 — User Prompt Injection (full)
```text
## Design Request

Create a 72-foot Viking sportfisher with aggressive deadrise and sharp entry

## Current Design State

### Geometry
```json
{
  "bodies": {},
  "sections": [],
  "surfaces": []
}
```

### Hull Parameters
- LOA: 21.95m
- Beam: 5.8m
- Draft: 1.6m

### Coordinate conventions (do not violate)
- Global X is derived from `geometry.section.station` (0..1) and LOA. Do NOT put X into section points.
- For polygon sections: `points` is strictly `[[y, z], ...]` where **z=0 is baseline** and **waterline is z=draft**.
- Sections are HALF-BREADTH (one side only, y>=0). Start at keel (y≈0), end at deck edge.
- NOT closed polygons! Points trace an open curve from keel to sheer, system mirrors.

### Recent Physics Validation
(No recent validation - propose initial geometry)


## Current Geometry State

BLANK GEOMETRY: There are currently 0 hull sections and no hull surface.
You must create the hull first (body + sections + lofted surface).


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



BLANK DESIGN (YOU MUST BUILD THE HULL FIRST):
- This design currently has no hull sections.
- You MUST output a complete minimal hull program:
  - CREATE 1 geometry.body (body_id like "main_hull")
  - CREATE 12 geometry.section (or at least 7) for that body with stations spanning 0..1
  - CREATE 1 geometry.surface with definition "lofted" for that body
- Do NOT output only discontinuities/constraints. That will fail compilation with: "No sections defined".



IMPORTANT: GEOMETRY_PROGRAM must be valid JSON matching this schema:
{
  "program_id": "string",
  "version": 1,
  "operations": [...],
  "constraints": [...]
}

```

### Retry Prompt Template A — Output Contract Failure (full template)
```text
## Design Request

Create a 72-foot Viking sportfisher with aggressive deadrise and sharp entry

## Current Design State

### Geometry
```json
{
  "bodies": {},
  "sections": [],
  "surfaces": []
}
```

### Hull Parameters
- LOA: 21.95m
- Beam: 5.8m
- Draft: 1.6m

### Coordinate conventions (do not violate)
- Global X is derived from `geometry.section.station` (0..1) and LOA. Do NOT put X into section points.
- For polygon sections: `points` is strictly `[[y, z], ...]` where **z=0 is baseline** and **waterline is z=draft**.
- Sections are HALF-BREADTH (one side only, y>=0). Start at keel (y≈0), end at deck edge.
- NOT closed polygons! Points trace an open curve from keel to sheer, system mirrors.

### Recent Physics Validation
(No recent validation - propose initial geometry)


## Current Geometry State

BLANK GEOMETRY: There are currently 0 hull sections and no hull surface.
You must create the hull first (body + sections + lofted surface).


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



BLANK DESIGN (YOU MUST BUILD THE HULL FIRST):
- This design currently has no hull sections.
- You MUST output a complete minimal hull program:
  - CREATE 1 geometry.body (body_id like "main_hull")
  - CREATE 12 geometry.section (or at least 7) for that body with stations spanning 0..1
  - CREATE 1 geometry.surface with definition "lofted" for that body
- Do NOT output only discontinuities/constraints. That will fail compilation with: "No sections defined".



IMPORTANT: GEOMETRY_PROGRAM must be valid JSON matching this schema:
{
  "program_id": "string",
  "version": 1,
  "operations": [...],
  "constraints": [...]
}


### STRICT RETRY: OUTPUT CONTRACT FAILURE
Your previous response did not include the required TWO JSON artifacts.
You MUST output BOTH markers with JSON blocks:
- VESSEL_THINKING_PASS
- GEOMETRY_PROGRAM

Failure: <type>: <message>

```

### Retry Prompt Template B — Thinking Pass Validation Failure (full template)
```text
## Design Request

Create a 72-foot Viking sportfisher with aggressive deadrise and sharp entry

## Current Design State

### Geometry
```json
{
  "bodies": {},
  "sections": [],
  "surfaces": []
}
```

### Hull Parameters
- LOA: 21.95m
- Beam: 5.8m
- Draft: 1.6m

### Coordinate conventions (do not violate)
- Global X is derived from `geometry.section.station` (0..1) and LOA. Do NOT put X into section points.
- For polygon sections: `points` is strictly `[[y, z], ...]` where **z=0 is baseline** and **waterline is z=draft**.
- Sections are HALF-BREADTH (one side only, y>=0). Start at keel (y≈0), end at deck edge.
- NOT closed polygons! Points trace an open curve from keel to sheer, system mirrors.

### Recent Physics Validation
(No recent validation - propose initial geometry)


## Current Geometry State

BLANK GEOMETRY: There are currently 0 hull sections and no hull surface.
You must create the hull first (body + sections + lofted surface).


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



BLANK DESIGN (YOU MUST BUILD THE HULL FIRST):
- This design currently has no hull sections.
- You MUST output a complete minimal hull program:
  - CREATE 1 geometry.body (body_id like "main_hull")
  - CREATE 12 geometry.section (or at least 7) for that body with stations spanning 0..1
  - CREATE 1 geometry.surface with definition "lofted" for that body
- Do NOT output only discontinuities/constraints. That will fail compilation with: "No sections defined".



IMPORTANT: GEOMETRY_PROGRAM must be valid JSON matching this schema:
{
  "program_id": "string",
  "version": 1,
  "operations": [...],
  "constraints": [...]
}


### STRICT RETRY: VESSEL_THINKING_PASS FAILED VALIDATION
Your previous response failed deterministic server-side validation.
You MUST output TWO JSON artifacts again (VESSEL_THINKING_PASS + GEOMETRY_PROGRAM).

Targeted patch instruction (JSON):
<patch_json>

```

### Audit: Why CREATE can still fail (most likely causes)
- **Two-artifact output is brittle**: the model must emit *two* correctly marked JSON blocks (VESSEL_THINKING_PASS + GEOMETRY_PROGRAM). Any truncation, mis-ordering, missing marker, or extra wrapper text can cause `THINKING_PASS_MISSING` / `GEOMETRY_PROGRAM_MISSING`.
- **Token budget pressure**: the system prompt is ~3.5k tokens by itself; CREATE also asks for a full design program. If `max_tokens` is too low relative to the combined artifacts, responses may truncate before the second block.
- **Model chooses NEEDS_CLARIFICATION path**: the spec allows returning `NEEDS_CLARIFICATION`, which can lead to returning only one artifact or returning an incomplete pair if the model is uncertain.
- **Prompt contract conflicts**: if the thinking pass schema is strict and the model produces a near-miss shape (wrong types for lists/dicts), the retry path may still not converge, especially under constrained tokens.

### Audit: Why the 60s UI timeout happened
- The UI aborts fetch after 60s (`AbortController`). CREATE routinely takes >60s due to LLM latency + retries + compilation + physics.
- Even when the server is still working, the browser cancels the request and the user experiences a 'hang'.

### Recommended next steps (debug-first)
1. **Log raw LLM response length + markers** server-side for CREATE failures (did it include both markers?).
2. **Temporarily raise max tokens** for CREATE only (e.g., 5000–7000) to rule out truncation.
3. **Split into two calls** (thinking pass call, then program call) to reduce brittleness.
4. Add a **contract-hardening post-processor**: if one block is present, ask for only the missing block in retry (not both again).

