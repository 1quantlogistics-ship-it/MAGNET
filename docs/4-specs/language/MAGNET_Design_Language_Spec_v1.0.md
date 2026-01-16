# MAGNET Design Language Specification v1.0

## What MAGNET Is

```
┌─────────────────────────────────────────────────────────────────┐
│                         ENGINEER                                │
│     (infinite creativity, domain knowledge, quality judgment)   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
                    "Make the bow finer"
                    "Try a stepped configuration"
                    "What if we added outriggers?"
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT SWARM                                │
│          (translates intent → geometry primitives)              │
│          (proposes options, not decisions)                      │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         KERNEL                                  │
│              (validates physics, returns feedback)              │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
                    Results + tradeoffs
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         ENGINEER                                │
│                   (judges, refines, iterates)                   │
└─────────────────────────────────────────────────────────────────┘
```

**MAGNET is not:** AI that designs boats autonomously

**MAGNET is:** A design environment where engineers express creative intent, agents translate to geometry, the kernel validates physics instantly, and the loop iterates as fast as the engineer can think

### The Core Equation

```
ENGINEER PRODUCTIVITY = creative expression × instant feedback × no artificial limits
```

| Term | What Enables It | What Blocks It |
|:-----|:----------------|:---------------|
| **Creative expression** | Compositional primitives | Enumerated hull types |
| **Instant feedback** | Fast kernel validation | Batch processing, slow physics |
| **No artificial limits** | Geometry-first design | Preset families, style catalogs |

---

## Core Invariants (Sacred)

| Invariant | Meaning |
|:----------|:--------|
| **Engineer is in the loop** | Engineers express intent, judge quality, decide convergence |
| **Programs are proposals** | The language proposes; it never mutates directly |
| **Kernel is sole arbiter** | All semantics live in kernel functions + validators |
| **Compilation is deterministic** | Same program + same state → same ActionPlan |
| **Validator is the only firewall** | Every action passes through existing validation |
| **Kernel knows geometry, not design** | Kernel exposes primitives (surfaces, cuts, paths); design concepts emerge from composition |
| **No enumerated designs** | The kernel never hears "stepped hull" or "patrol boat" — only geometric operations |
| **No second geometry engine** | Language compiles INTO existing `HullGeometry` / `NURBSSurface` / `HullSection` — never around them |
| **One canonical geometry model** | All surfaces, sections, bodies compile to the same objects consumed by tessellation/hydrostatics |

---

## 0. The Fundamental Principle

> **The kernel should expose only universal geometric and physical operations; the LLM composes them into designs the kernel has never seen, and the kernel's only role is to validate reality, not recognize intent.**

This is not "AI CAD with better presets."

This is a **geometric/physical execution engine** that accepts unconstrained design programs and refuses to lie.

### What the Kernel Knows (Primitives)

| Category | Primitives |
|:---------|:-----------|
| **Bodies** | Distinct solid volumes (demihulls, tunnel structures, pontoons) |
| **Surfaces** | NURBS patches, lofted surfaces from sections, ruled surfaces, continuity (G0/G1/G2) |
| **Sections** | Transverse cross-sections defined by points, curves, or parametric shapes |
| **Edges** | Sharp, blended, filleted, with tangency constraints |
| **Discontinuities** | Cuts, steps, breaks in surface continuity |
| **Paths** | Flow paths, structural paths, routing between points |
| **Intersections** | Surface-surface, surface-plane, trimming |
| **Offsets** | Parallel surfaces, shell thickness |
| **Constraints** | Geometric (tangent, perpendicular, coincident), physical (pressure, stress, buoyancy) |
| **Attachments** | How bodies connect (rigid, hinged, offset) |

### What the Kernel Does NOT Know (Design Concepts)

The kernel has no concept of:
- "Stepped hull"
- "Ventilated planing surface"  
- "Spray rail"
- "Patrol boat"
- "Racing yacht"
- "Aggressive style"

These are **compositions** that emerge from programs. The kernel validates geometry and physics. It does not recognize intent.

### The Test

If you can express a design that **no engineer anticipated**, and the kernel can validate it without new code, the system works.

If every new design concept requires a new resource type, the system has failed.

> **Any hull form that requires a new language primitive is a failure of the language.**

### Agent Coordination Rule

Agents never coordinate on "features" — they coordinate on **geometry and constraints only**.

❌ **Wrong:** Agents debate "should we add a spray rail?"

✅ **Right:** Agents debate "this surface edge should introduce a discontinuity here to reduce wetted area"

The difference: the first is enumeration (agents speak in named features). The second is geometry (agents speak in primitives with physics justification).

Agents differ only in:
- What constraints they care about
- What failures they react to  
- What they propose next

They share ONE geometric language.

---

## 0.1 Canonical Geometry Model (No Second Engine)

**CRITICAL:** The design language does NOT create a new geometry engine. It compiles INTO the existing canonical geometry classes that are already consumed by tessellation, hydrostatics, and export.

### What Already Exists in MAGNET

```
magnet/hull_gen/
├── geometry.py      # HullSection, SectionPoint, HullGeometry, Point3D
├── nurbs.py         # NURBSCurve, NURBSSurface (FULL IMPLEMENTATION EXISTS)
├── generator.py     # HullGenerator (sections → geometry)
└── parameters.py    # HullDefinition, MainDimensions, FormCoefficients
```

### The Canonical Object Model

| Class | Location | Purpose | Already Consumed By |
|:------|:---------|:--------|:--------------------|
| `HullSection` | `hull_gen/geometry.py` | Transverse cross-section | Generator, Tessellation, Hydrostatics |
| `SectionPoint` | `hull_gen/geometry.py` | Point on section curve | Generator, Tessellation |
| `HullGeometry` | `hull_gen/geometry.py` | Complete hull (sections, waterlines, curves) | WebGL, Export, Analysis |
| `NURBSCurve` | `hull_gen/nurbs.py` | B-spline curve | Surface fitting, Fairing |
| `NURBSSurface` | `hull_gen/nurbs.py` | B-spline surface | Surface representation |
| `Point3D` | `hull_gen/geometry.py` | 3D point | Everything |

### The Contract: Language → Canonical Model → Downstream

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    THE "NO SECOND ENGINE" CONTRACT                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Design Language Program                                                    │
│       │                                                                     │
│       │  "CREATE geometry.section {...}"                                    │
│       │  "LOFT [...] INTO surface"                                          │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  SEMANTIC EXPANDER                                                  │   │
│  │  • Calls kernel/stdlib/geometry.py                                  │   │
│  │  • Creates instances of EXISTING classes:                           │   │
│  │    - HullSection (from hull_gen/geometry.py)                        │   │
│  │    - NURBSSurface (from hull_gen/nurbs.py)                          │   │
│  │    - HullGeometry (from hull_gen/geometry.py)                       │   │
│  │  • DOES NOT define new geometry representations                     │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       │  Returns: HullGeometry containing HullSections                      │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  DOWNSTREAM PIPELINE (multi-body extensions required)               │   │
│  │                                                                     │   │
│  │  HullGeometry                                                       │   │
│  │       │                                                             │   │
│  │       ├──▶ HullGeometryPipeline.tessellate() → WebGL mesh           │   │
│  │       ├──▶ compute_hydrostatics() → displacement, GM, LCB           │   │
│  │       ├──▶ STLExporter.export() → STL file                          │   │
│  │       └──▶ IGESExporter.export() → IGES file                        │   │
│  │                                                                     │   │
│  │  ALL EXISTING CODE PATHS CONTINUE TO WORK                           │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### What This Means for Implementation

**DO:**
- `geometry.section` compiles to `HullSection` instance
- `geometry.surface` compiles to `NURBSSurface` instance
- `LOFT` operation produces `HullGeometry` with populated `sections` list
- Store canonical objects in state, feed to pipeline (see `MAGNET_Physics_Gaps_And_Solutions.md` for multi-body extensions)

**DO NOT:**
- Create new geometry classes that duplicate existing functionality
- Bypass `HullGeometryPipeline` for tessellation
- Implement new hydrostatics that don't use `HullGeometry`
- Create a "language geometry" vs "real geometry" distinction

### Validation Gates for Surfaces

A surface is "legal" if and only if:

| Gate | Check | Implementation |
|:-----|:------|:---------------|
| **Closure** | Surface forms closed loop at each section | `HullSection.is_closed()` |
| **Non-self-intersecting** | No self-intersection | `NURBSSurface.check_self_intersection()` |
| **Continuity** | Meets specified G0/G1/G2 | `NURBSSurface.check_continuity()` |
| **Orientation** | Normals point outward | `HullGeometry.validate_normals()` |
| **Watertight** | Volume can be computed | `HullGeometry.compute_volume() > 0` |

These are **existing validations** in the codebase. The language does not add new validation — it uses the existing validators.

---

## 0.2 Agent-Facing Types vs Internal Sugar (CRITICAL)

**Agents should speak ONLY in geometric primitives.** Named naval-architecture features are internal sugar.

### Types Agents MAY Use (Compositional Primitives)

These types enable **infinite novelty** — any geometry expressible from their combination is valid:

| Type | What It Represents | Why It's Primitive |
|:-----|:-------------------|:-------------------|
| `geometry.body` | A distinct solid volume | Physical entity, position/orientation only |
| `geometry.section` | A transverse cross-section | Shape definition, no design semantics |
| `geometry.surface` | A parametric surface | Mathematical surface, no design semantics |
| `geometry.discontinuity` | A break in surface continuity | Pure geometry — could be step, chine, anything |
| `geometry.opening` | A cutout in a surface | Pure geometry — could be vent, window, anything |
| `geometry.flow_path` | A path between points | Pure topology — could be air, water, exhaust, novel |
| `geometry.attachment` | How two bodies connect | Pure mechanics — rigid, hinged, offset |
| `geometry.edge_treatment` | How an edge is shaped | Pure geometry — sharp, fillet, chamfer, novel blend |

### Types Agents Should NOT Use (Internal Sugar)

These types exist for **backwards compatibility** and **human ergonomics**. They are NOT compositional primitives. If agents use them, novelty is bounded by this vocabulary:

| Type | What It Really Is | Why It's NOT Primitive |
|:-----|:------------------|:-----------------------|
| `hull.spray_rail` | A surface modification + edge treatment | Named concept from naval architecture |
| `hull.chine` | An edge treatment + continuity constraint | Named concept — agent should compose from `geometry.edge_treatment` |
| `hull.knuckle` | An edge treatment (blend) | Named concept |
| `hull.transom_cutout` | An opening + edge treatments | Named concept — agent should use `geometry.opening` |
| `hull.transom_extension` | A surface extension | Named concept |

**Internal Sugar Expansion:**
When these types are used, the kernel INTERNALLY expands them to primitives:
```
hull.spray_rail → geometry.surface_modification + geometry.edge_treatment
hull.chine → geometry.edge_treatment + geometry.continuity_constraint
hull.transom_cutout → geometry.opening + geometry.edge_treatment[]
```

### Why This Matters

**With primitives:** Agent can invent "triple-rail whisker" (never seen before) by composing:
```
CREATE geometry.surface_modification { type: "ridge", profile: [...], count: 3 }
```

**With sugar:** Agent can only use `hull.spray_rail` — limited to what humans named.

### The Rule

> **Agents MUST compose from `geometry.*` types. Named features (`hull.*`) are deprecated for agent use and exist only for legacy compatibility and human ergonomics.**

### Enum Flexibility in Primitives

To maximize novelty, enums in `geometry.*` types are **physics categories**, not design semantics:

| Field | OLD (Design-bound) | NEW (Physics-bound) |
|:------|:-------------------|:--------------------|
| `geometry.body.body_type` | `hull`, `pontoon`, `outrigger` | `submerged`, `surface_piercing`, `above_water`, or **freeform string** |
| `geometry.surface.surface_type` | `hull_shell`, `deck`, `bulkhead` | `watertight`, `non_watertight`, `structural`, or **freeform string** |
| `geometry.flow_path.medium` | `air`, `water`, `exhaust` | `gas`, `liquid`, `mixed`, or **freeform string** |

The kernel validates **physics**, not **names**. A novel body type "stabilizer_whisker" is valid if it has physical properties (volume, mass, position).

### DERIVE is Optional

`DERIVE` policies (like `lb_ratio`) encode **design heuristics**, not physics. They are conveniences for users who want automatic synthesis.

**Agents are NOT required to use DERIVE.**

- Agents MAY `SET hull.beam = 4.5` directly — the kernel validates physics, not whether it matches any ratio
- Agents MAY `DERIVE hull.beam FROM lb_ratio(loa=hull.loa, target_ratio=5.5)` for convenience
- Novel L/B ratios (15:1, 2:1, anything) are VALID if they pass physics validation

```
# VALID: Agent sets a novel ratio directly
SET hull.beam = 0.8  # L/B = 15:1, very narrow
SET hull.loa = 12

# ALSO VALID: Agent uses synthesis convenience (agent specifies ratio, not hull type)
DERIVE hull.beam FROM lb_ratio(loa=hull.loa, target_ratio=5.5)
```

### Physics Validation is Compositional

Physics constraints are evaluated on the **resulting geometry**, not assumed forms:

```
# Kernel does NOT assume "this is a planing hull, so..."
# Kernel computes: given this geometry, what is the stress distribution?

physics.hull_stress_ratio = compute_stress(geometry) / material.yield_strength
```

- Novel hull forms are NOT rejected because they're "unconventional"
- Novel hull forms ARE rejected if they physically fail (stress > yield, negative GM, etc.)
- The kernel has NO "conventional hull" assumption

---

## 1. Language Architecture

### 1.1 The Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DESIGN LANGUAGE COMPILATION PIPELINE                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Program (DSL)                                                              │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PARSER (deployment/program_parser.py)                              │   │
│  │  • Syntax validation only                                           │   │
│  │  • Shape + presence checks                                          │   │
│  │  • May cache type schemas from kernel                               │   │
│  │  • NO semantic validation                                           │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│  AST (Abstract Syntax Tree)                                                │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  TYPE CHECKER / HSV (control_plane/hsv.py)                          │   │
│  │  • Virtual IDs for CREATEs                                          │   │
│  │  • Preview expanded state                                           │   │
│  │  • Detect ALIGN to non-existent ID                                  │   │
│  │  • Validates against kernel type schemas                            │   │
│  │  • Evaluates program constraints (ephemeral)                        │   │
│  │  • NO mutation, NO physics                                          │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  SEMANTIC EXPANDER (kernel/semantic_expander.py)                    │   │
│  │  • Expands ops by calling KERNEL FUNCTIONS                          │   │
│  │  • ALIGN → compute position via kernel.align()                      │   │
│  │  • DERIVE → call kernel.synthesis_policy()                          │   │
│  │  • CONSTRAIN → validate (ephemeral) or PIN (persistent)             │   │
│  │  • Outputs: List[Action]                                            │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│  ActionPlan                                                                │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  VALIDATOR (kernel/action_validator.py) — THE FIREWALL              │   │
│  │  • Path whitelist                                                   │   │
│  │  • Bounds checking                                                  │   │
│  │  • Lock checking                                                    │   │
│  │  • Compatibility checking                                           │   │
│  │  • Physics constraints                                              │   │
│  │  • Persistent constraints (PINned)                                  │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  EXECUTOR (kernel/action_executor.py)                               │   │
│  │  • Mutates state                                                    │   │
│  │  • Creates ExplainRecord                                            │   │
│  │  • Triggers geometry regeneration                                   │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│  Committed State + ExplainRecord                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 What Lives Where

| Component | Location | Responsibility | Does NOT Do |
|:----------|:---------|:---------------|:------------|
| **Parser** | deployment | Syntax validation, AST construction | Semantic checks, own type definitions |
| **Type Registry** | kernel/stdlib | Canonical type schemas for all resources | — |
| **HSV** | control_plane | Type checking, preview, virtual IDs | Mutation, physics |
| **Expander** | kernel | Call kernel functions, emit Actions | Define semantics |
| **Kernel Functions** | kernel/stdlib | Define all semantic operations | Execute directly |
| **Validator** | kernel | Enforce all constraints (incl. pinned) | Trust compiler |
| **Executor** | kernel | Mutate state | Skip validation |

---

## 2. Core Language

### 2.1 Statements

```
// Resource Operations
CREATE <type> { <params> } AS <id>
UPDATE <id> { <params> }
DELETE <id>

// Geometric Operations (kernel-owned)
ALIGN <id> TO <target_id> ON <axis> OFFSET <value>
MIRROR <id> ABOUT <plane> AS <new_id>
SCALE <selector> BY <factor> ON <fields>
LOFT <section_ids> INTO <surface_id>  // Section-to-surface lofting
OFFSET <surface_id> BY <distance_m> AS <new_surface_id>

// Reference Operations (primitives reference each other)
// Relationships are IMPLICIT in how primitives reference each other:
//   - flow_path.inlet_point references an opening or surface_point
//   - discontinuity.surface_id references a surface
// No explicit RELATE needed — topology emerges from references

// Constraint Operations
DERIVE <path> USING <policy>
CONSTRAIN <path> <op> <value>           // Ephemeral (this program only)
PIN CONSTRAINT <path> <op> <value>      // Persistent (attached to design)
PREFER <path> TOWARD <target> WEIGHT <w>
UNPIN CONSTRAINT <constraint_id>        // Remove persistent constraint

// Control Flow (optional, for patterns)
IF <condition> THEN <statements> END
FOR <var> IN <range> DO <statements> END

// Modules (controlled stdlib only)
IMPORT <module>
```

### 2.2 Example Program

```
// Aggressive patrol hull with twin jet tunnels

IMPORT hull.planing

// Create primary chine
CREATE hull.chine {
  height_ratio: 0.30,
  angle_deg: 50,
  is_hard: true
} AS main_chine

// Create spray rail aligned to chine
CREATE hull.spray_rail {
  profile: "triangular",
  width_m: 0.06
} AS lower_rail

ALIGN lower_rail TO main_chine ON height_ratio OFFSET -0.05

// Create and mirror jet tunnel (port-side resource only)
CREATE hull.transom_cutout {
  shape: "semicircle",
  center_y_ratio: 0.3,
  width_m: 0.5,
  depth_m: 0.8
} AS jet_tunnel_port

MIRROR jet_tunnel_port ABOUT centerline AS jet_tunnel_stbd

// Derive beam from synthesis policy — agent specifies ratio, not hull type
DERIVE hull.beam FROM lb_ratio(loa=hull.loa, target_ratio=4.5)

// Ephemeral constraint (validated this program only)
CONSTRAIN stability.gm_m >= 0.8

// Persistent constraint (stays with design, checked on future changes)
PIN CONSTRAINT hull.beam >= 2.5

// Soft preference for speed
PREFER resistance.fn_design TOWARD 0.9 WEIGHT 0.6
```

### 2.3 Example: High-Performance Hull (The Kernel Knows Geometry, Not "Stepped Hull")

This example demonstrates a hull that designers would call "triple-stepped ventilated planing hull."

**But the kernel never hears those words.**

The kernel sees: discontinuities, flow paths, openings, and constraints. The design concept emerges from composition.

```
// ═══════════════════════════════════════════════════════════════════════════
// This program creates what designers call a "stepped ventilated hull"
// But the kernel only sees: surfaces, discontinuities, flow paths, openings
// 
// The kernel has NO concept of "stepped hull" — only geometry and physics
// ═══════════════════════════════════════════════════════════════════════════

// ───────────────────────────────────────────────────────────────────────────
// DISCONTINUITIES — What designers call "steps" are just surface breaks
// ───────────────────────────────────────────────────────────────────────────

// Forward discontinuity in bottom surface
CREATE geometry.discontinuity {
  surface_id: "hull.bottom",
  station: 0.65,
  depth_m: 0.08,
  profile: "transverse",
  continuity: "G0",
  aft_face_angle_deg: 86.5
} AS disc_fwd

// Middle discontinuity
CREATE geometry.discontinuity {
  surface_id: "hull.bottom",
  station: 0.42,
  depth_m: 0.10,
  profile: "transverse",
  continuity: "G0",
  aft_face_angle_deg: 86.0
} AS disc_mid

// Aft discontinuity
CREATE geometry.discontinuity {
  surface_id: "hull.bottom",
  station: 0.22,
  depth_m: 0.12,
  profile: "transverse",
  continuity: "G0",
  aft_face_angle_deg: 85.5
} AS disc_aft

// ───────────────────────────────────────────────────────────────────────────
// OPENINGS — Air inlets (kernel sees holes, not "ventilation scoops")
// ───────────────────────────────────────────────────────────────────────────

// Port side inlet for forward discontinuity
CREATE geometry.opening {
  surface_id: "hull.topsides",
  center_u: 0.67,              // Just forward of disc_fwd
  center_v: 0.70,              // Port side (positive V)
  shape: "naca",
  width_m: 0.08,
  height_m: 0.04,
  rotation_deg: 0
} AS inlet_fwd_port

MIRROR inlet_fwd_port ABOUT centerline AS inlet_fwd_stbd

// Port inlet for middle discontinuity
CREATE geometry.opening {
  surface_id: "hull.topsides",
  center_u: 0.44,
  center_v: 0.75,
  shape: "naca",
  width_m: 0.10,
  height_m: 0.05
} AS inlet_mid_port

MIRROR inlet_mid_port ABOUT centerline AS inlet_mid_stbd

// Port inlet for aft discontinuity
CREATE geometry.opening {
  surface_id: "hull.topsides",
  center_u: 0.24,
  center_v: 0.80,
  shape: "naca",
  width_m: 0.12,
  height_m: 0.06
} AS inlet_aft_port

MIRROR inlet_aft_port ABOUT centerline AS inlet_aft_stbd

// ───────────────────────────────────────────────────────────────────────────
// OUTLET POINTS — Where air exits (at discontinuity aft faces)
// ───────────────────────────────────────────────────────────────────────────

CREATE geometry.surface_point {
  surface_id: "disc_fwd.aft_face",
  u: 0.5,
  v: 0.70
} AS outlet_fwd_port

MIRROR outlet_fwd_port ABOUT centerline AS outlet_fwd_stbd

CREATE geometry.surface_point {
  surface_id: "disc_mid.aft_face",
  u: 0.5,
  v: 0.75
} AS outlet_mid_port

MIRROR outlet_mid_port ABOUT centerline AS outlet_mid_stbd

CREATE geometry.surface_point {
  surface_id: "disc_aft.aft_face",
  u: 0.5,
  v: 0.80
} AS outlet_aft_port

MIRROR outlet_aft_port ABOUT centerline AS outlet_aft_stbd

// ───────────────────────────────────────────────────────────────────────────
// FLOW PATHS — Kernel validates: does air get from inlet to outlet?
// ───────────────────────────────────────────────────────────────────────────

CREATE geometry.flow_path {
  inlet_surface: "hull.topsides",
  inlet_point: "inlet_fwd_port",
  outlet_surface: "disc_fwd.aft_face",
  outlet_point: "outlet_fwd_port",
  cross_section_area_m2: 0.0032,
  medium: "air"
} AS flow_fwd_port

MIRROR flow_fwd_port ABOUT centerline AS flow_fwd_stbd

CREATE geometry.flow_path {
  inlet_surface: "hull.topsides",
  inlet_point: "inlet_mid_port",
  outlet_surface: "disc_mid.aft_face",
  outlet_point: "outlet_mid_port",
  cross_section_area_m2: 0.0050,
  medium: "air"
} AS flow_mid_port

MIRROR flow_mid_port ABOUT centerline AS flow_mid_stbd

CREATE geometry.flow_path {
  inlet_surface: "hull.topsides",
  inlet_point: "inlet_aft_port",
  outlet_surface: "disc_aft.aft_face",
  outlet_point: "outlet_aft_port",
  cross_section_area_m2: 0.0072,
  medium: "air"
} AS flow_aft_port

MIRROR flow_aft_port ABOUT centerline AS flow_aft_stbd

// ───────────────────────────────────────────────────────────────────────────
// EDGE TREATMENTS — Sharp edges at discontinuities for flow separation
// ───────────────────────────────────────────────────────────────────────────

CREATE geometry.edge_treatment {
  edge_id: "disc_fwd.leading_edge",
  treatment: "sharp"
} AS edge_fwd

CREATE geometry.edge_treatment {
  edge_id: "disc_mid.leading_edge",
  treatment: "sharp"
} AS edge_mid

CREATE geometry.edge_treatment {
  edge_id: "disc_aft.leading_edge",
  treatment: "sharp"
} AS edge_aft

// ───────────────────────────────────────────────────────────────────────────
// CONSTRAINTS — Kernel validates physics (not design intent)
// ───────────────────────────────────────────────────────────────────────────

// Flow paths must not intersect structure
CONSTRAIN geometry.flow_path_clearance >= 0.01

// Discontinuity depth must be manufacturable
CONSTRAIN geometry.min_surface_thickness >= 0.005

// Flow area must support pressure differential at speed
CONSTRAIN physics.flow_area_adequacy >= 1.0

// Overall structural integrity
CONSTRAIN physics.hull_stress_ratio <= 0.8
```

**Why this works:**

| What Designer Says | What Kernel Sees | Why It's Composable |
|:-------------------|:-----------------|:--------------------|
| "Three steps" | Three `geometry.discontinuity` | Any number, any position |
| "Ventilation ducts" | `geometry.flow_path` from opening to face | Any inlet, any outlet, any routing |
| "Air scoops" | `geometry.opening` with shape="naca" | Any shape, any position |
| "Step depth progression" | Different `depth_m` per discontinuity | Any pattern, not hardcoded |
| "Ventilated planing" | Flow paths to discontinuity aft faces | Emergent, not enumerated |

**The kernel never heard "stepped hull."** It validated geometry and physics.

A completely novel hull configuration — one no engineer anticipated — would compile and validate identically, because the kernel knows **primitives**, not **designs**.

---

## 3. Constraint Persistence Contract

### 3.1 Constraint Lifecycle

| Type | Syntax | Persistence | Evaluated By | Use Case |
|:-----|:-------|:------------|:-------------|:---------|
| **Ephemeral** | `CONSTRAIN` | This compilation cycle only | HSV + Validator | "For this change, ensure GM ≥ 0.8" |
| **Persistent** | `PIN CONSTRAINT` | Attached to design permanently | Validator on all future changes | "This design must always have beam ≥ 2.5m" |
| **Soft** | `PREFER` | This compilation cycle only | Optimizer (if running) | "Try to maximize Froude number" |

### 3.2 Storage Model

```python
# In design state
@dataclass
class DesignState:
    # ... other fields ...
    
    # Persistent constraints (survive across programs)
    pinned_constraints: Dict[str, PinnedConstraint] = field(default_factory=dict)

@dataclass(frozen=True)
class PinnedConstraint:
    constraint_id: str          # Unique ID for removal
    path: str                   # e.g., "hull.beam"
    operator: str               # ">=", "<=", "==", "in_range"
    value: Any                  # Threshold or range
    created_by_program: str     # Traceability
    created_at: datetime
    reason: Optional[str]       # Human explanation
```

### 3.3 Constraint Evaluation Order

1. **HSV** evaluates ephemeral CONSTRAIN statements during preview
2. **Validator** checks:
   - All pinned constraints (from `pinned_constraints`)
   - Ephemeral constraints (passed through ActionPlan)
   - Built-in physics constraints (always active)
3. **Failure** on any constraint = entire ActionPlan rejected

### 3.4 Removing Persistent Constraints

```
// In program
UNPIN CONSTRAINT c_beam_min_001  // Removes by ID

// Or via API
DELETE /api/v1/designs/{id}/constraints/{constraint_id}
```

---

## 4. Type Registry (Kernel-Owned)

### 4.1 Architecture

**Critical Rule:** The kernel owns all type schemas. The parser may cache them but never defines them.

```
kernel/
├── stdlib/
│   ├── type_registry.py      # CANONICAL type definitions
│   ├── geometry.py           # ALIGN, MIRROR, SCALE implementations
│   ├── synthesis.py          # DERIVE policies
│   └── ...
```

### 4.2 Type Schema Definition

```python
# kernel/stdlib/type_registry.py

"""
TYPE REGISTRY — KERNEL AUTHORITY

All resource types and their schemas are defined here.
Parser and HSV read from here. They do NOT define types.
"""

from dataclasses import dataclass
from typing import Dict, List, Set, Optional, Any
from enum import Enum

@dataclass(frozen=True)
class FieldSchema:
    """Schema for a single field."""
    name: str
    field_type: str            # "float", "int", "str", "bool", "enum"
    required: bool = True
    default: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    enum_values: Optional[tuple] = None
    description: str = ""

@dataclass(frozen=True)
class TypeSchema:
    """Schema for a resource type."""
    type_name: str                          # e.g., "geometry.body"
    fields: tuple                           # Tuple[FieldSchema, ...]
    mirrorable: bool = False                # Can this type be MIRRORed?
    mirror_fields: tuple = ()               # Fields to negate on MIRROR
    mirror_behavior: str = "create_copy"    # "create_copy", "error", "no_op"
    alignable_axes: tuple = ()              # Valid axes for ALIGN
    description: str = ""
    deprecated: bool = False                # True = agents should NOT use this type
    expands_to: str = ""                    # For deprecated types: what primitives it becomes


# ═══════════════════════════════════════════════════════════════════════════
# CANONICAL TYPE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

TYPE_SCHEMAS: Dict[str, TypeSchema] = {
    
    # ═══════════════════════════════════════════════════════════════════════
    # 🔴 DEPRECATED: NAMED FEATURE TYPES (hull.*)
    # ═══════════════════════════════════════════════════════════════════════
    #
    # ⚠️ AGENTS MUST NEVER CREATE THESE TYPES ⚠️
    #
    # These exist ONLY for:
    # 1. Backwards compatibility with legacy designs
    # 2. Human CLI ergonomics (not agent use)
    # 3. Internal expansion to geometry.* primitives
    #
    # If an agent outputs hull.spray_rail instead of geometry.discontinuity,
    # it is enumerating design concepts and limiting novelty.
    #
    # ANY NEW DESIGN CONCEPT THAT NEEDS A NEW hull.* TYPE = ARCHITECTURE FAILURE
    #
    # Agents MUST compose from geometry.* primitives instead.
    # ═══════════════════════════════════════════════════════════════════════
    
    "hull.spray_rail": TypeSchema(
        type_name="hull.spray_rail",
        deprecated=True,  # AGENTS: Use geometry.surface_modification instead
        fields=(
            FieldSchema("height_ratio", "float", min_value=0.0, max_value=1.0,
                       description="Vertical position as fraction of depth"),
            FieldSchema("start_station", "float", default=0.0, min_value=0.0, max_value=1.0),
            FieldSchema("end_station", "float", default=1.0, min_value=0.0, max_value=1.0),
            FieldSchema("profile", "enum", enum_values=("triangular", "rounded", "flat")),
            FieldSchema("width_m", "float", min_value=0.01, max_value=0.5),
            FieldSchema("depth_m", "float", required=False, default=None),
        ),
        mirrorable=False,
        mirror_behavior="error",
        alignable_axes=("height_ratio", "start_station", "end_station"),
        description="[DEPRECATED] Use geometry.surface_modification + geometry.edge_treatment",
    ),
    
    "hull.chine": TypeSchema(
        type_name="hull.chine",
        deprecated=True,  # AGENTS: Use geometry.edge_treatment instead
        fields=(
            FieldSchema("height_ratio", "float", min_value=0.0, max_value=1.0),
            FieldSchema("angle_deg", "float", min_value=0.0, max_value=90.0),
            FieldSchema("is_hard", "bool", default=True),
            FieldSchema("start_station", "float", default=0.0),
            FieldSchema("end_station", "float", default=1.0),
        ),
        mirrorable=False,
        mirror_behavior="error",
        alignable_axes=("height_ratio", "start_station", "end_station"),
        description="[DEPRECATED] Use geometry.edge_treatment",
    ),
    
    "hull.transom_cutout": TypeSchema(
        type_name="hull.transom_cutout",
        deprecated=True,  # AGENTS: Use geometry.opening instead
        fields=(
            FieldSchema("shape", "enum", enum_values=("semicircle", "rectangle", "trapezoid")),
            FieldSchema("center_y_ratio", "float", min_value=-1.0, max_value=1.0,
                       description="Y position: negative=stbd, positive=port, 0=centerline"),
            FieldSchema("width_m", "float", min_value=0.1),
            FieldSchema("depth_m", "float", min_value=0.1),
            FieldSchema("height_start_ratio", "float", default=0.0, min_value=0.0, max_value=1.0),
        ),
        mirrorable=True,
        mirror_fields=("center_y_ratio",),
        mirror_behavior="create_copy",
        alignable_axes=("height_start_ratio",),
        description="[DEPRECATED] Use geometry.opening",
    ),
    
    "hull.transom_extension": TypeSchema(
        type_name="hull.transom_extension",
        deprecated=True,  # AGENTS: Use geometry.surface + geometry.attachment
        fields=(
            FieldSchema("depth_m", "float", min_value=0.0),
            FieldSchema("height_start", "float", default=0.0),
            FieldSchema("angle_deg", "float", default=0.0, min_value=-45.0, max_value=45.0),
        ),
        mirrorable=False,
        mirror_behavior="no_op",
        alignable_axes=("height_start",),
        description="[DEPRECATED] Use geometry.surface + geometry.attachment",
    ),
    
    "hull.knuckle": TypeSchema(
        type_name="hull.knuckle",
        deprecated=True,  # AGENTS: Use geometry.edge_treatment
        fields=(
            FieldSchema("height_ratio", "float", min_value=0.0, max_value=1.0),
            FieldSchema("start_station", "float", default=0.0),
            FieldSchema("end_station", "float", default=1.0),
            FieldSchema("radius_m", "float", required=False, default=None),
        ),
        mirrorable=False,
        mirror_behavior="error",
        alignable_axes=("height_ratio", "start_station", "end_station"),
        description="[DEPRECATED] Use geometry.edge_treatment",
    ),
    
    # ═══════════════════════════════════════════════════════════════════════
    # GEOMETRIC PRIMITIVES — What agents SHOULD use
    # ═══════════════════════════════════════════════════════════════════════
    #
    # These are UNIVERSAL GEOMETRIC OPERATIONS that can compose into anything.
    # The kernel knows ONLY these primitives. Design concepts emerge from
    # their composition.
    #
    # Enums are PHYSICS CATEGORIES, not design semantics.
    # Freeform strings are accepted where novelty requires it.
    # ═══════════════════════════════════════════════════════════════════════
    
    "geometry.discontinuity": TypeSchema(
        type_name="geometry.discontinuity",
        fields=(
            FieldSchema("surface_id", "str", description="Surface to cut"),
            FieldSchema("station", "float", min_value=0.0, max_value=1.0,
                       description="Longitudinal position of discontinuity"),
            FieldSchema("depth_m", "float", min_value=0.0,
                       description="Vertical offset at discontinuity"),
            # Profile is freeform — agents can invent novel profiles
            FieldSchema("profile", "str", default="transverse",
                       description="Shape of discontinuity line (transverse, diagonal, curved, or novel)"),
            FieldSchema("continuity", "enum", default="G0",
                       enum_values=("G0", "G1", "G2"),
                       description="Mathematical continuity at edge"),
            FieldSchema("aft_face_angle_deg", "float", default=90.0,
                       description="Angle of aft-facing surface"),
        ),
        mirrorable=False,
        mirror_behavior="no_op",
        alignable_axes=("station",),
        description="Surface discontinuity — a break in surface continuity",
    ),
    
    "geometry.flow_path": TypeSchema(
        type_name="geometry.flow_path",
        fields=(
            FieldSchema("inlet_surface", "str", description="Surface where flow enters"),
            FieldSchema("inlet_point", "str", description="Point or region ID on inlet surface"),
            FieldSchema("outlet_surface", "str", description="Surface where flow exits"),
            FieldSchema("outlet_point", "str", description="Point or region ID on outlet surface"),
            FieldSchema("cross_section_area_m2", "float", min_value=0.0001,
                       description="Flow cross-sectional area"),
            # Medium is freeform — agents can specify novel fluids
            FieldSchema("medium", "str", default="air",
                       description="What flows through (air, water, exhaust, coolant, or novel)"),
        ),
        mirrorable=True,
        mirror_fields=(),
        mirror_behavior="create_copy",
        alignable_axes=(),
        description="Path for fluid flow between two surfaces/points",
    ),
    
    "geometry.surface_point": TypeSchema(
        type_name="geometry.surface_point",
        fields=(
            FieldSchema("surface_id", "str", description="Parent surface"),
            FieldSchema("u", "float", min_value=0.0, max_value=1.0,
                       description="Parametric U coordinate on surface"),
            FieldSchema("v", "float", min_value=0.0, max_value=1.0,
                       description="Parametric V coordinate on surface"),
            FieldSchema("offset_normal_m", "float", default=0.0,
                       description="Offset along surface normal"),
        ),
        mirrorable=True,
        mirror_fields=("v",),  # V often corresponds to transverse
        mirror_behavior="create_copy",
        alignable_axes=("u", "v"),
        description="A point defined relative to a surface",
    ),
    
    "geometry.opening": TypeSchema(
        type_name="geometry.opening",
        fields=(
            FieldSchema("surface_id", "str", description="Surface to cut opening in"),
            FieldSchema("center_u", "float", min_value=0.0, max_value=1.0),
            FieldSchema("center_v", "float", min_value=0.0, max_value=1.0),
            FieldSchema("shape", "enum", enum_values=("circle", "rectangle", "ellipse", "naca")),
            FieldSchema("width_m", "float", min_value=0.01),
            FieldSchema("height_m", "float", min_value=0.01),
            FieldSchema("rotation_deg", "float", default=0.0),
        ),
        mirrorable=True,
        mirror_fields=("center_v",),
        mirror_behavior="create_copy",
        alignable_axes=("center_u", "center_v"),
        description="An opening/cutout in a surface",
    ),
    
    "geometry.edge_treatment": TypeSchema(
        type_name="geometry.edge_treatment",
        fields=(
            FieldSchema("edge_id", "str", description="Edge to modify"),
            FieldSchema("treatment", "enum", 
                       enum_values=("sharp", "fillet", "chamfer", "blend")),
            FieldSchema("radius_m", "float", required=False, default=None,
                       description="Radius for fillet/blend"),
            FieldSchema("angle_deg", "float", required=False, default=None,
                       description="Angle for chamfer"),
        ),
        mirrorable=False,
        mirror_behavior="no_op",
        alignable_axes=(),
        description="Treatment applied to an edge",
    ),
    
    # ═══════════════════════════════════════════════════════════════════════
    # BODY PRIMITIVE — For multi-hull vessels (catamarans, trimarans, etc.)
    # ═══════════════════════════════════════════════════════════════════════
    #
    # A "catamaran" is NOT a resource type — it's a program that creates
    # two hull bodies with an attachment relationship. The kernel never
    # hears the word "catamaran."
    
    "geometry.body": TypeSchema(
        type_name="geometry.body",
        fields=(
            # body_type is FREEFORM STRING — agents can invent novel body types
            # The kernel validates physics (mass, volume, position), not naming
            # Common values: "hull", "pontoon", "outrigger", "stabilizer_fin", "hydrofoil"
            # Novel values: VALID if they have physical properties
            FieldSchema("body_type", "str", default="hull",
                       description="Body type identifier (freeform for novelty)"),
            # Physics category for hydrostatics calculation
            FieldSchema("physics_category", "enum",
                       enum_values=("submerged", "surface_piercing", "above_water"),
                       description="Physics category determines hydrostatic treatment"),
            FieldSchema("parent_body_id", "str", required=False, default=None,
                       description="Parent body if this is a secondary body"),
            FieldSchema("offset_x_m", "float", default=0.0,
                       description="Longitudinal offset from parent origin"),
            FieldSchema("offset_y_m", "float", default=0.0,
                       description="Transverse offset from parent centerline"),
            FieldSchema("offset_z_m", "float", default=0.0,
                       description="Vertical offset from parent baseline"),
            FieldSchema("surface_id", "str", required=False,
                       description="Reference to the surface defining this body's shell"),
        ),
        mirrorable=True,
        mirror_fields=("offset_y_m",),
        mirror_behavior="create_copy",
        alignable_axes=("offset_x_m", "offset_y_m", "offset_z_m"),
        description="A distinct solid volume — novel types allowed",
    ),
    
    # ═══════════════════════════════════════════════════════════════════════
    # SECTION PRIMITIVE — Cross-sections for lofting into surfaces
    # ═══════════════════════════════════════════════════════════════════════
    #
    # Sections define transverse cross-sections. LOFT operation combines
    # sections into a surface. This is the traditional naval architecture
    # approach: define stations, loft to surface.
    
    "geometry.section": TypeSchema(
        type_name="geometry.section",
        fields=(
            FieldSchema("station", "float", min_value=0.0, max_value=1.0,
                       description="Longitudinal position (0=AP, 1=FP)"),
            FieldSchema("x_position_m", "float",
                       description="Absolute X position in meters"),
            FieldSchema("definition_type", "enum",
                       enum_values=("points", "parametric", "nurbs_curve"),
                       description="How section shape is defined"),
            # For points definition
            FieldSchema("points", "array", required=False,
                       description="Array of {y, z} points from keel outward"),
            # For parametric definition
            FieldSchema("half_beam_m", "float", required=False,
                       description="Half-beam at this section"),
            FieldSchema("draft_m", "float", required=False,
                       description="Draft at this section"),
            FieldSchema("deadrise_deg", "float", required=False,
                       description="Deadrise angle at this section"),
            FieldSchema("fullness", "float", required=False, min_value=0.0, max_value=1.0,
                       description="Section fullness (0=fine, 1=full)"),
            # For NURBS curve definition
            FieldSchema("nurbs_control_points", "array", required=False,
                       description="NURBS control points for section curve"),
            FieldSchema("nurbs_degree", "int", required=False, default=3),
            FieldSchema("nurbs_weights", "array", required=False),
            FieldSchema("nurbs_knots", "array", required=False),
            # Metadata
            FieldSchema("is_midship", "bool", default=False),
            FieldSchema("is_transom", "bool", default=False),
        ),
        mirrorable=False,  # Sections are inherently half-hull (port side)
        mirror_behavior="no_op",
        alignable_axes=("station", "x_position_m"),
        description="A transverse cross-section for surface lofting",
    ),
    
    # ═══════════════════════════════════════════════════════════════════════
    # SURFACE PRIMITIVE — NURBS surfaces or lofted from sections
    # ═══════════════════════════════════════════════════════════════════════
    #
    # Surfaces can be defined two ways:
    # 1. Directly via NURBS control point net
    # 2. Implicitly via LOFT operation on sections
    
    "geometry.surface": TypeSchema(
        type_name="geometry.surface",
        fields=(
            # surface_type is FREEFORM STRING — agents can invent novel surface types
            # Common values: "hull_shell", "deck", "bulkhead", "appendage"
            # Novel values: VALID if they define a continuous surface
            FieldSchema("surface_type", "str", default="hull_shell",
                       description="Surface type identifier (freeform for novelty)"),
            # Physics category for structural/hydrostatic treatment
            FieldSchema("physics_category", "enum",
                       enum_values=("watertight", "non_watertight", "structural"),
                       description="Physics category determines hydrostatic treatment"),
            FieldSchema("definition_type", "enum",
                       enum_values=("nurbs", "lofted", "ruled", "developable"),
                       description="How surface is defined mathematically"),
            FieldSchema("body_id", "str", required=False,
                       description="Parent body this surface belongs to"),
            # For NURBS direct definition
            FieldSchema("nurbs_control_points", "array", required=False,
                       description="2D grid of control points [u][v]"),
            FieldSchema("nurbs_degree_u", "int", required=False, default=3),
            FieldSchema("nurbs_degree_v", "int", required=False, default=3),
            FieldSchema("nurbs_weights", "array", required=False),
            FieldSchema("nurbs_knots_u", "array", required=False),
            FieldSchema("nurbs_knots_v", "array", required=False),
            # For lofted surfaces (sections referenced separately)
            FieldSchema("section_ids", "array", required=False,
                       description="Ordered list of section IDs to loft through"),
            FieldSchema("loft_tension", "float", required=False, default=0.5,
                       min_value=0.0, max_value=1.0,
                       description="Lofting tension (0=loose, 1=tight)"),
            # Boundary conditions (mathematical, not design)
            FieldSchema("continuity_bow", "enum", default="G1",
                       enum_values=("G0", "G1", "G2"),
                       description="Mathematical continuity at bow boundary"),
            FieldSchema("continuity_stern", "enum", default="G1",
                       enum_values=("G0", "G1", "G2"),
                       description="Mathematical continuity at stern boundary"),
        ),
        mirrorable=False,
        mirror_behavior="no_op",
        alignable_axes=(),
        description="A parametric surface — novel types allowed",
    ),
    
    # ═══════════════════════════════════════════════════════════════════════
    # ATTACHMENT PRIMITIVE — How bodies connect
    # ═══════════════════════════════════════════════════════════════════════
    
    "geometry.attachment": TypeSchema(
        type_name="geometry.attachment",
        fields=(
            FieldSchema("parent_body_id", "str",
                       description="Body that serves as the attachment base"),
            FieldSchema("child_body_id", "str",
                       description="Body being attached"),
            FieldSchema("attachment_type", "enum",
                       enum_values=("rigid", "hinged", "sliding"),
                       description="Type of mechanical connection"),
            FieldSchema("parent_point", "str", required=False,
                       description="Point ID on parent body for attachment"),
            FieldSchema("child_point", "str", required=False,
                       description="Point ID on child body for attachment"),
            FieldSchema("offset_x_m", "float", default=0.0),
            FieldSchema("offset_y_m", "float", default=0.0),
            FieldSchema("offset_z_m", "float", default=0.0),
        ),
        mirrorable=True,
        mirror_fields=("offset_y_m",),
        mirror_behavior="create_copy",
        alignable_axes=("offset_x_m", "offset_y_m", "offset_z_m"),
        description="Connection between two bodies",
    ),
}


def get_type_schema(type_name: str) -> TypeSchema:
    """Get canonical schema for a type. Raises if unknown."""
    if type_name not in TYPE_SCHEMAS:
        raise UnknownTypeError(f"Unknown resource type: {type_name}")
    return TYPE_SCHEMAS[type_name]


def validate_resource_params(type_name: str, params: Dict[str, Any]) -> List[str]:
    """Validate params against type schema. Returns list of errors."""
    schema = get_type_schema(type_name)
    errors = []
    
    # Check required fields
    for field in schema.fields:
        if field.required and field.name not in params:
            errors.append(f"Missing required field: {field.name}")
    
    # Check field values
    for name, value in params.items():
        field = next((f for f in schema.fields if f.name == name), None)
        if field is None:
            errors.append(f"Unknown field: {name}")
            continue
        
        # Type check
        if field.field_type == "float" and not isinstance(value, (int, float)):
            errors.append(f"{name}: expected float, got {type(value).__name__}")
        
        # Range check
        if field.min_value is not None and value < field.min_value:
            errors.append(f"{name}: {value} < min {field.min_value}")
        if field.max_value is not None and value > field.max_value:
            errors.append(f"{name}: {value} > max {field.max_value}")
        
        # Enum check
        if field.enum_values and value not in field.enum_values:
            errors.append(f"{name}: {value} not in {field.enum_values}")
    
    return errors
```

### 4.3 Parser Uses Registry (Does Not Define)

```python
# deployment/program_parser.py

from kernel.stdlib.type_registry import get_type_schema, validate_resource_params

class ProgramParser:
    def parse_create(self, tokens) -> CreateNode:
        type_name = tokens.consume_type()
        params = tokens.consume_params()
        alias = tokens.consume_alias()
        
        # Validate against kernel schema (does not define schema)
        schema = get_type_schema(type_name)  # Calls kernel
        errors = validate_resource_params(type_name, params)
        
        if errors:
            raise ParseError(f"Invalid CREATE: {errors}")
        
        return CreateNode(type_name, params, alias)
```

### 4.4 Multi-Body Model (Catamarans, Trimarans, Multi-Hull)

The kernel supports **multi-body vessels** through composition of `geometry.body` primitives. The kernel has no concept of "catamaran" or "trimaran" — these are programs that compose bodies.

#### 4.4.1 Body Hierarchy

```
┌─────────────────────────────────────────────────────────────────────┐
│                     MULTI-BODY VESSEL MODEL                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PRIMARY BODY (hull)                                                │
│  ├── surface_id → geometry.surface (the shell)                      │
│  ├── sections[] → geometry.section (cross-sections for lofting)     │
│  │                                                                  │
│  ├── SECONDARY BODY (port demihull)                                 │
│  │   ├── offset_y_m: +hull_spacing/2                                │
│  │   ├── surface_id → geometry.surface                              │
│  │   └── attachment → geometry.attachment (to primary)              │
│  │                                                                  │
│  └── SECONDARY BODY (starboard demihull)                            │
│      ├── offset_y_m: -hull_spacing/2  (or MIRRORed)                 │
│      ├── surface_id → geometry.surface                              │
│      └── attachment → geometry.attachment (to primary)              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.4.2 Example: Catamaran (Kernel Sees Bodies, Not "Catamaran")

```
// ═══════════════════════════════════════════════════════════════════
// This program creates what designers call a "catamaran"
// But the kernel only sees: bodies, surfaces, sections, attachments
// 
// The kernel has NO concept of "catamaran" — only geometry
// ═══════════════════════════════════════════════════════════════════

// Create port demihull body
CREATE geometry.body {
  body_type: "hull",
  offset_y_m: 3.0   // 3m to port of global centerline
} AS demihull_port

// Create sections for port demihull (parametric definition)
CREATE geometry.section {
  station: 0.0,
  x_position_m: 0.0,
  definition_type: "parametric",
  half_beam_m: 0.8,
  draft_m: 1.2,
  deadrise_deg: 20,
  fullness: 0.4,
  is_transom: true
} AS section_port_00

CREATE geometry.section {
  station: 0.5,
  x_position_m: 6.0,
  definition_type: "parametric",
  half_beam_m: 1.0,
  draft_m: 1.0,
  deadrise_deg: 15,
  fullness: 0.5,
  is_midship: true
} AS section_port_05

CREATE geometry.section {
  station: 1.0,
  x_position_m: 12.0,
  definition_type: "parametric",
  half_beam_m: 0.3,
  draft_m: 0.6,
  deadrise_deg: 25,
  fullness: 0.2
} AS section_port_10

// Loft sections into surface for port demihull
CREATE geometry.surface {
  surface_type: "hull_shell",
  definition_type: "lofted",
  body_id: "demihull_port",
  section_ids: ["section_port_00", "section_port_05", "section_port_10"],
  loft_tension: 0.6,
  continuity_bow: "G2",
  continuity_stern: "G1"
} AS surface_port

// Mirror port body to create starboard
MIRROR demihull_port ABOUT centerline AS demihull_stbd

// Create cross-deck structure connecting the demihulls
CREATE geometry.body {
  body_type: "tunnel_structure",
  parent_body_id: "demihull_port",
  offset_z_m: 1.5   // 1.5m above baseline
} AS cross_deck

// Attach cross-deck to both demihulls
CREATE geometry.attachment {
  parent_body_id: "demihull_port",
  child_body_id: "cross_deck",
  attachment_type: "rigid"
} AS attach_port

CREATE geometry.attachment {
  parent_body_id: "demihull_stbd",
  child_body_id: "cross_deck",
  attachment_type: "rigid"
} AS attach_stbd

// Constraints (the kernel validates these, not "catamaran rules")
CONSTRAIN stability.gm_m >= 1.5
CONSTRAIN structure.cross_deck_clearance_m >= 0.8
```

#### 4.4.3 Example: Trimaran (Novel Configuration, No New Code)

The kernel has never heard "trimaran." Same primitives, different composition:

```
// Central main hull
CREATE geometry.body {
  body_type: "hull",
  offset_y_m: 0.0   // On centerline
} AS main_hull

// Port outrigger (smaller, further out)
CREATE geometry.body {
  body_type: "outrigger",
  offset_y_m: 5.0,    // 5m to port
  offset_x_m: 2.0     // 2m forward of main hull origin
} AS outrigger_port

// Mirror to starboard
MIRROR outrigger_port ABOUT centerline AS outrigger_stbd

// Sections for main hull (larger)
CREATE geometry.section { station: 0.0, definition_type: "parametric", half_beam_m: 2.0, draft_m: 1.5, deadrise_deg: 15 } AS main_sec_00
CREATE geometry.section { station: 0.5, definition_type: "parametric", half_beam_m: 2.5, draft_m: 1.3, deadrise_deg: 12 } AS main_sec_05
CREATE geometry.section { station: 1.0, definition_type: "parametric", half_beam_m: 0.8, draft_m: 0.8, deadrise_deg: 20 } AS main_sec_10

// Sections for outrigger (slender)
CREATE geometry.section { station: 0.0, definition_type: "parametric", half_beam_m: 0.4, draft_m: 0.6, deadrise_deg: 25 } AS out_sec_00
CREATE geometry.section { station: 0.5, definition_type: "parametric", half_beam_m: 0.5, draft_m: 0.5, deadrise_deg: 20 } AS out_sec_05
CREATE geometry.section { station: 1.0, definition_type: "parametric", half_beam_m: 0.2, draft_m: 0.3, deadrise_deg: 30 } AS out_sec_10

// Loft all surfaces
LOFT [main_sec_00, main_sec_05, main_sec_10] INTO main_surface
LOFT [out_sec_00, out_sec_05, out_sec_10] INTO outrigger_surface

// Cross-arms connecting outriggers to main hull
CREATE geometry.body { body_type: "tunnel_structure", parent_body_id: "main_hull" } AS crossarm_port
CREATE geometry.attachment { parent_body_id: "main_hull", child_body_id: "outrigger_port", attachment_type: "rigid" } AS arm_attach_port
MIRROR crossarm_port ABOUT centerline AS crossarm_stbd

// Validate as trimaran (kernel doesn't know "trimaran" — just physics)
CONSTRAIN stability.gm_m >= 2.0
CONSTRAIN structure.arm_stress_ratio <= 0.8
```

**The kernel validated a trimaran without knowing the word "trimaran."** The same primitives that made a catamaran made a trimaran. Tomorrow, an agent could compose a pentamaran or an asymmetric outrigger — no new code required.

### 4.5 Surface Definition (NURBS and Section Lofting)

The kernel supports two methods for defining surfaces:

#### 4.5.1 Method 1: Section Lofting (Traditional Naval Architecture)

Define cross-sections at stations, then LOFT them into a surface.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SECTION-TO-SURFACE LOFTING                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│    Section @ Station 0.0 (Transom)                                  │
│         │                                                           │
│         ├── half_beam: 2.5m                                         │
│         ├── draft: 1.0m                                             │
│         └── deadrise: 18°                                           │
│                    ↓                                                │
│    Section @ Station 0.3                                            │
│         │          ↓                                                │
│    Section @ Station 0.5 (Midship)                                  │
│         │          ↓                                                │
│    Section @ Station 0.8                                            │
│         │          ↓                                                │
│    Section @ Station 1.0 (FP)                                       │
│                    ↓                                                │
│              LOFT OPERATION                                         │
│                    ↓                                                │
│    ┌─────────────────────────────────────────────┐                  │
│    │         NURBS SURFACE                       │                  │
│    │  (control points interpolated from sections)│                  │
│    └─────────────────────────────────────────────┘                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Section Definition Options:**

| Method | Use Case | Fields |
|:-------|:---------|:-------|
| `parametric` | Quick definition using naval architecture parameters | `half_beam_m`, `draft_m`, `deadrise_deg`, `fullness` |
| `points` | Explicit point cloud | `points: [{y: 0, z: -1.0}, {y: 0.5, z: -0.8}, ...]` |
| `nurbs_curve` | Precise NURBS curve | `nurbs_control_points`, `nurbs_degree`, `nurbs_weights`, `nurbs_knots` |

#### 4.5.2 Method 2: Direct NURBS Definition

For imported or externally-defined surfaces.

```
CREATE geometry.surface {
  surface_type: "hull_shell",
  definition_type: "nurbs",
  body_id: "main_hull",
  nurbs_degree_u: 3,
  nurbs_degree_v: 3,
  nurbs_control_points: [
    // U=0 (stern)
    [
      {x: 0, y: 0, z: -1.0},      // V=0 (keel)
      {x: 0, y: 1.5, z: -0.8},    // V=0.5
      {x: 0, y: 2.5, z: 0.5}      // V=1 (deck edge)
    ],
    // U=0.5 (midship)
    [
      {x: 6, y: 0, z: -1.2},
      {x: 6, y: 2.0, z: -0.9},
      {x: 6, y: 3.0, z: 0.8}
    ],
    // U=1 (bow)
    [
      {x: 12, y: 0, z: -0.5},
      {x: 12, y: 0.8, z: -0.3},
      {x: 12, y: 1.0, z: 1.2}
    ]
  ]
} AS hull_surface
```

#### 4.5.3 LOFT Operation

The `LOFT` operation converts sections to a surface:

```
// Create sections first
CREATE geometry.section { ... } AS sec_00
CREATE geometry.section { ... } AS sec_05
CREATE geometry.section { ... } AS sec_10

// Loft into surface
LOFT [sec_00, sec_05, sec_10] INTO main_hull_surface
```

**LOFT Kernel Implementation Contract:**

```python
# kernel/stdlib/geometry.py

def loft_sections_to_surface(
    section_ids: List[str],
    state: DesignState,
    tension: float = 0.5,
    continuity_bow: str = "G1",
    continuity_stern: str = "G1",
) -> NURBSSurface:
    """
    Loft sections into NURBS surface.
    
    Contract:
    - Sections must be ordered by station (ascending)
    - All sections must be for the same body
    - Returns NURBSSurface with control points interpolated from sections
    - Tension controls how tightly surface passes through sections
    - Continuity controls boundary behavior (G0=position, G1=tangent, G2=curvature)
    """
    sections = [state.get_section(sid) for sid in section_ids]
    
    # Validate ordering
    stations = [s.station for s in sections]
    if stations != sorted(stations):
        raise LoftError("Sections must be in station order")
    
    # Convert sections to control point columns
    control_net = []
    for section in sections:
        if section.definition_type == "parametric":
            column = _parametric_to_points(section)
        elif section.definition_type == "points":
            column = section.points
        elif section.definition_type == "nurbs_curve":
            column = _nurbs_curve_to_points(section)
        control_net.append(column)
    
    # Interpolate NURBS surface through control net
    surface = NURBSSurface.fit_through_sections(
        control_net,
        tension=tension,
        boundary_conditions={
            "u_start": continuity_stern,  # Stern
            "u_end": continuity_bow,      # Bow
        }
    )
    
    return surface
```

---

## 5. Canonical Resource Storage Path

### 5.1 The Decision: `hull.features.<type>[id]`

**Canonical storage model:** Resources are stored in typed collections under `hull.features`.

```python
# Canonical paths — organized by PRIMITIVE TYPE, not design concept:

# Geometric primitives
geometry.discontinuities["disc_fwd"]
geometry.flow_paths["flow_fwd_port"]
geometry.openings["inlet_fwd_port"]
geometry.surface_points["outlet_fwd_port"]
geometry.edge_treatments["edge_fwd"]

# Legacy feature types (compositions of primitives)
hull.features.spray_rails["rail_001"]
hull.features.chines["chine_001"]
hull.features.transom_cutouts["jet_tunnel_port"]
hull.features.knuckle_lines["knuckle_001"]
```

**Note:** The "legacy feature types" (spray_rail, chine, etc.) are **convenience wrappers** that expand into geometric primitives. They exist for ergonomics, but internally compile down to discontinuities, edge treatments, and surface modifications.

**NOT this (rejected alternative):**
```python
# REJECTED: global resource map
hull.resources["rail_001"]  # No type information in path
```

### 5.2 Storage Implementation

```python
# kernel/state/hull_features.py

@dataclass
class GeometryState:
    """
    Storage for GEOMETRIC PRIMITIVES — not design concepts.
    
    The kernel stores universal geometric operations.
    "Stepped hull" is not a thing here — only discontinuities, paths, etc.
    """
    
    # ═══════════════════════════════════════════════════════════════════════
    # GEOMETRIC PRIMITIVES — Universal, composable
    # ═══════════════════════════════════════════════════════════════════════
    
    discontinuities: Dict[str, DiscontinuityConfig] = field(default_factory=dict)
    flow_paths: Dict[str, FlowPathConfig] = field(default_factory=dict)
    openings: Dict[str, OpeningConfig] = field(default_factory=dict)
    surface_points: Dict[str, SurfacePointConfig] = field(default_factory=dict)
    edge_treatments: Dict[str, EdgeTreatmentConfig] = field(default_factory=dict)
    
    # Surfaces (NURBS patches, ruled surfaces, etc.)
    surfaces: Dict[str, SurfaceConfig] = field(default_factory=dict)
    
    # Constraints (geometric and physical)
    constraints: Dict[str, ConstraintConfig] = field(default_factory=dict)


@dataclass
class HullFeatures:
    """
    CONVENIENCE WRAPPERS — These compile down to geometric primitives.
    
    A spray_rail is really: surface modification + edge treatment
    A chine is really: edge treatment + continuity constraint
    A transom_cutout is really: opening + edge treatments
    
    These exist for ergonomics. The kernel sees the underlying geometry.
    """
    
    spray_rails: Dict[str, SprayRailConfig] = field(default_factory=dict)
    chines: Dict[str, ChineConfig] = field(default_factory=dict)
    knuckle_lines: Dict[str, KnuckleConfig] = field(default_factory=dict)
    transom_cutouts: Dict[str, TransomCutoutConfig] = field(default_factory=dict)
    transom_extensions: Dict[str, TransomExtensionConfig] = field(default_factory=dict)


# Path resolution — PRIMITIVES FIRST, then convenience wrappers
PRIMITIVE_COLLECTIONS = {
    "geometry.discontinuity": "discontinuities",
    "geometry.flow_path": "flow_paths",
    "geometry.opening": "openings",
    "geometry.surface_point": "surface_points",
    "geometry.edge_treatment": "edge_treatments",
    "geometry.surface": "surfaces",
    "geometry.constraint": "constraints",
}

FEATURE_COLLECTIONS = {
    "hull.spray_rail": "spray_rails",
    "hull.chine": "chines",
    "hull.knuckle": "knuckle_lines",
    "hull.transom_cutout": "transom_cutouts",
    "hull.transom_extension": "transom_extensions",
}

def resolve_resource_path(type_name: str, resource_id: str) -> str:
    """Convert type + ID to canonical storage path."""
    collection = FEATURE_COLLECTIONS.get(type_name)
    if collection is None:
        raise UnknownTypeError(f"No collection for type: {type_name}")
    return f"hull.features.{collection}.{resource_id}"
```

### 5.3 Consistent Path Usage

All code MUST use the canonical path format:

```python
# kernel/stdlib/geometry.py

def align(source_id: str, target_id: str, axis: str, offset: float, state: StateManager):
    # CORRECT: Use canonical path
    source_type = state.get_resource_type(source_id)
    source_path = resolve_resource_path(source_type, source_id)
    target_path = resolve_resource_path(target_type, target_id)
    
    target = state.get(target_path)
    # ...
    
    return [Action(
        action_type=ActionType.SET,
        path=f"{source_path}.{axis}",  # e.g., "hull.features.spray_rails.rail_001.height_ratio"
        value=aligned_value,
    )]
```

---

## 6. MIRROR Semantics (Per-Type Rules)

### 6.1 Mirrorability Matrix

| Type | Mirrorable | Mirror Fields | Behavior | Rationale |
|:-----|:-----------|:--------------|:---------|:----------|
| `hull.spray_rail` | ❌ No | — | Error | Spray rails are symmetric by definition |
| `hull.chine` | ❌ No | — | Error | Chines run along centerline |
| `hull.knuckle` | ❌ No | — | Error | Knuckles are symmetric features |
| `hull.transom_cutout` | ✅ Yes | `center_y_ratio` | Create copy | Creates port/stbd pairs |
| `hull.transom_extension` | ❌ No | — | No-op | Full-width feature |

### 6.2 MIRROR Implementation with Type Checks

```python
# kernel/stdlib/geometry.py

from kernel.stdlib.type_registry import get_type_schema

def mirror(
    source_id: str,
    plane: str,
    new_id: str,
    state: StateManager,
) -> List[Action]:
    """
    Mirror a resource about a plane.
    
    Type-aware implementation:
    1. Check if type supports MIRROR
    2. Apply only to declared mirror_fields
    3. Generate appropriate actions
    """
    # Get source resource and type
    source_type = state.get_resource_type(source_id)
    source_path = resolve_resource_path(source_type, source_id)
    source = state.get(source_path)
    
    if source is None:
        raise SemanticError(f"MIRROR source not found: {source_id}")
    
    if source.get("_deleted"):
        raise SemanticError(f"Cannot MIRROR deleted resource: {source_id}")
    
    # Check type schema for mirrorability
    schema = get_type_schema(source_type)
    
    if not schema.mirrorable:
        if schema.mirror_behavior == "error":
            raise SemanticError(
                f"Type {source_type} does not support MIRROR. "
                f"Reason: {schema.description or 'centerline-symmetric feature'}"
            )
        elif schema.mirror_behavior == "no_op":
            # Return empty actions (silent no-op for full-width features)
            return []
    
    # Only centerline mirror supported currently
    if plane != "centerline":
        raise SemanticError(f"Unsupported mirror plane: {plane}. Only 'centerline' supported.")
    
    # Create mirrored copy
    mirrored_params = dict(source)
    
    # Remove lifecycle fields
    mirrored_params.pop("_id", None)
    mirrored_params.pop("_deleted", None)
    mirrored_params.pop("_deleted_at", None)
    
    # Negate only declared mirror fields
    for field_name in schema.mirror_fields:
        if field_name in mirrored_params:
            mirrored_params[field_name] = -mirrored_params[field_name]
    
    # Generate CREATE action for mirrored resource
    new_path = resolve_resource_path(source_type, new_id)
    
    return [
        Action(
            action_type=ActionType.CREATE,
            path=new_path,
            value=mirrored_params,
            _semantic_trace=SemanticTrace(
                operation="MIRROR",
                inputs={
                    "source_id": source_id,
                    "plane": plane,
                    "new_id": new_id,
                    "mirror_fields": schema.mirror_fields,
                },
                computation=f"Mirrored {source_id} about {plane}, negated fields: {schema.mirror_fields}",
            ),
        )
    ]
```

### 6.3 "Both Sides" Resources

For resources that inherently represent both sides (e.g., a symmetric spray rail pattern):

```python
# Type schema declares this
"hull.symmetric_feature": TypeSchema(
    type_name="hull.symmetric_feature",
    fields=(...),
    mirrorable=False,
    mirror_behavior="error",
    description="Already represents both port and starboard",
)
```

User attempting `MIRROR symmetric_rail ABOUT centerline AS ...` receives:
```
SemanticError: Type hull.symmetric_feature does not support MIRROR.
Reason: Already represents both port and starboard
```

---

## 7. DERIVE Policy Contract

### 7.0 DERIVE is OPTIONAL

> **CRITICAL: Agents are NOT required to use DERIVE.**

DERIVE policies encode **design heuristics**, not physics laws. They provide convenient starting points for users who want automatic synthesis, but they do NOT represent physical truth.

**What agents CAN do:**

```
# OPTION A: Set values directly (full novelty)
SET hull.loa = 12
SET hull.beam = 0.8      # Novel L/B ratio of 15:1

# OPTION B: Use DERIVE for convenience — agent specifies ratio directly
SET hull.loa = 12
DERIVE hull.beam FROM lb_ratio(loa=hull.loa, target_ratio=3.5)  # Agent chose 3.5:1
```

**Both are valid.** The kernel validates PHYSICS, not whether the result matches a "planing ratio."

A 15:1 L/B ratio is valid if:
- The geometry closes (watertight)
- Hydrostatics compute (positive volume)
- Structural stress is acceptable

A 15:1 L/B ratio may be unconventional, but it's not physically impossible. The kernel accepts it.

**When DERIVE policies MAY reject:**
- Input out of defined range (e.g., LOA < 3m)
- Unknown hull type for type-specific policies
- Iterative solver doesn't converge

These are policy limitations, not physics laws. Agents can bypass them by using SET directly.

### 7.1 Policy Declaration Requirements

**IF you implement a DERIVE policy, it MUST declare:**

```python
@dataclass(frozen=True)
class PolicyContract:
    """Mandatory contract for all DERIVE policies."""
    
    # Identity
    policy_name: str            # e.g., "lb_ratio"
    version: str                # e.g., "1.0.0"
    
    # I/O contract
    required_inputs: tuple      # Paths that MUST exist
    optional_inputs: tuple      # Paths that MAY be used
    output_path: str            # Single path written
    auxiliary_outputs: tuple    # Additional paths written (if any)
    
    # Behavior
    computation_type: str       # "heuristic", "iterative_solve", "lookup"
    deterministic: bool         # Same inputs → same output?
    max_iterations: Optional[int]  # For iterative solvers
    
    # Failure modes
    failure_modes: tuple        # List of possible failure reasons
    fallback_behavior: str      # "error", "use_default", "skip"
```

### 7.2 Example Policy with Full Contract

```python
# kernel/stdlib/synthesis.py

class LBRatioPolicy:
    """
    Derive beam from LOA using agent-specified target L/B ratio.
    
    NOTE: This policy does NOT lookup by hull type. The agent specifies
    the desired L/B ratio directly. This prevents design enumeration
    from creeping into kernel synthesis policies.
    """
    
    contract = PolicyContract(
        policy_name="lb_ratio",
        version="2.0.0",
        
        # Agent specifies target ratio, NOT hull type
        required_inputs=("hull.loa", "target_lb_ratio"),
        optional_inputs=(),
        output_path="hull.beam",
        auxiliary_outputs=(),
        
        computation_type="formula",  # Simple division, not lookup
        deterministic=True,
        max_iterations=None,
        
        failure_modes=(
            "loa_out_of_range",
            "lb_ratio_out_of_range",
        ),
        fallback_behavior="error",
    )
    
    def compute(self, state: StateManager) -> float:
        loa = state.get("hull.loa")
        target_lb = state.get("target_lb_ratio")
        
        # Validate inputs (physics bounds, not design types)
        if loa <= 0:
            raise PolicyError(
                policy=self.contract.policy_name,
                failure_mode="loa_out_of_range",
                message=f"LOA must be positive, got {loa}",
            )
        
        if not (3.0 <= loa <= 100.0):
            raise PolicyError(
                policy=self.contract.policy_name,
                failure_mode="loa_out_of_range",
                message=f"LOA {loa}m outside valid range [3, 100]m",
            )
        
        if not (2.0 <= target_lb <= 20.0):
            raise PolicyError(
                policy=self.contract.policy_name,
                failure_mode="lb_ratio_out_of_range",
                message=f"L/B ratio {target_lb} outside valid range [2, 20]",
            )
        
        # Simple formula: beam = loa / target_lb_ratio
        # Agent decides the ratio, kernel just computes
        return loa / target_lb
    
    def explain(self) -> str:
        return f"beam = loa / target_lb_ratio = {self._loa} / {self._target_lb} = {self._result}"


class GMBeamPolicy:
    """
    Derive beam from GM requirement.
    
    This is an ITERATIVE SOLVER - treat with care.
    """
    
    contract = PolicyContract(
        policy_name="gm_beam",
        version="1.0.0",
        
        required_inputs=("stability.gm_required_m", "hull.draft", "hull.displacement_m3"),
        optional_inputs=("hull.vcg_m",),
        output_path="hull.beam",
        auxiliary_outputs=("hull._gm_iteration_count",),  # Debug output
        
        computation_type="iterative_solve",
        deterministic=True,
        max_iterations=50,
        
        failure_modes=(
            "no_convergence",
            "gm_impossible",
            "inputs_inconsistent",
        ),
        fallback_behavior="error",
    )
    
    def compute(self, state: StateManager) -> float:
        # Iterative solver logic
        for i in range(self.contract.max_iterations):
            # ... solver steps ...
            if converged:
                return beam
        
        raise PolicyError(
            policy=self.contract.policy_name,
            failure_mode="no_convergence",
            message=f"Failed to converge after {self.contract.max_iterations} iterations",
        )
```

### 7.3 Policy Registry with Validation

```python
# kernel/stdlib/synthesis.py

SYNTHESIS_POLICIES: Dict[str, SynthesisPolicy] = {}

def register_policy(policy: SynthesisPolicy) -> None:
    """Register a policy, validating its contract."""
    contract = policy.contract
    
    # Validate contract completeness
    assert contract.policy_name, "Policy must have a name"
    assert contract.required_inputs, "Policy must declare required inputs"
    assert contract.output_path, "Policy must declare output path"
    assert contract.computation_type in ("heuristic", "iterative_solve", "lookup")
    
    if contract.computation_type == "iterative_solve":
        assert contract.max_iterations is not None, "Iterative solvers must declare max_iterations"
    
    SYNTHESIS_POLICIES[contract.policy_name] = policy


# Register all policies
register_policy(PlaningLBRatioPolicy())
register_policy(DisplacementBeamPolicy())
register_policy(GMBeamPolicy())
register_policy(FroudeDraftPolicy())
register_policy(SprayRailLayoutPolicy())
```

---

## 8. Coordinate Frame Contract

### 8.1 The Standard Frame

```
                        +X (forward, bow)
                            ↑
                            │
                            │
              ┌─────────────┼─────────────┐
              │             │             │
              │             │             │
    +Y (port) ←─────────────O─────────────→ -Y (starboard)
              │             │             │
              │             │             │
              └─────────────┼─────────────┘
                            │
                            │
                            ↓
                        -X (aft, stern)
                        
                        +Z (up)
                            ↑
                            │
              ─────────────WL────────────── (Z = 0 at waterline)
                            │
                            ↓
                        -Z (down, keel)
```

### 8.2 Plane Definitions

| Plane Name | Definition | Use Case |
|:-----------|:-----------|:---------|
| `centerline` | Y = 0 plane | MIRROR port ↔ starboard |
| `midship` | X = LWL/2 plane | MIRROR fore ↔ aft (rare) |
| `waterline` | Z = 0 plane | Reference for heights |

### 8.3 Normalized Coordinates

| Coordinate | Range | Meaning |
|:-----------|:------|:--------|
| `station` | 0.0 - 1.0 | Fraction of LWL (0 = stern, 1 = bow) |
| `height_ratio` | 0.0 - 1.0 | Fraction of depth (0 = keel, 1 = deck) |
| `beam_ratio` | 0.0 - 1.0 | Fraction of half-beam (0 = CL, 1 = max beam) |

---

## 9. Ordering Contract (Centralized)

### 9.1 Single Source of Truth

```python
# kernel/resource_ordering.py

"""
RESOURCE ORDERING CONTRACT

All resource ordering is defined here. No other module may define
its own ordering logic. Geometry generators, validators, and exporters
all use these functions.
"""

from typing import List, Dict, TypeVar
from dataclasses import dataclass

T = TypeVar('T')

@dataclass(frozen=True)
class OrderingSpec:
    """Specification for deterministic ordering of a resource type."""
    primary_key: str       # First sort field
    secondary_key: str     # Tiebreaker field
    tertiary_key: str = "_id"  # Final tiebreaker (always ID)

# Ordering specifications per resource type
ORDERING_SPECS: Dict[str, OrderingSpec] = {
    "hull.spray_rail": OrderingSpec(
        primary_key="height_ratio",
        secondary_key="start_station",
    ),
    "hull.chine": OrderingSpec(
        primary_key="height_ratio",
        secondary_key="start_station",
    ),
    "hull.knuckle": OrderingSpec(
        primary_key="height_ratio",
        secondary_key="start_station",
    ),
    "hull.transom_cutout": OrderingSpec(
        primary_key="height_start_ratio",
        secondary_key="center_y_ratio",
    ),
    "hull.transom_extension": OrderingSpec(
        primary_key="height_start",
        secondary_key="depth_m",
    ),
}

def get_ordered(
    resources: Dict[str, T],
    resource_type: str,
    include_deleted: bool = False,
) -> List[T]:
    """
    Return resources in deterministic order.
    
    This is THE ONLY function that should be used to iterate resources.
    Do not iterate dict.values() directly anywhere else.
    """
    spec = ORDERING_SPECS.get(resource_type)
    if spec is None:
        # Default: sort by ID only
        items = list(resources.values())
        if not include_deleted:
            items = [r for r in items if not getattr(r, '_deleted', False)]
        return sorted(items, key=lambda r: r._id)
    
    # Filter deleted if needed
    items = list(resources.values())
    if not include_deleted:
        items = [r for r in items if not getattr(r, '_deleted', False)]
    
    # Sort by spec
    def sort_key(r):
        return (
            getattr(r, spec.primary_key, 0),
            getattr(r, spec.secondary_key, 0),
            getattr(r, spec.tertiary_key, ""),
        )
    
    return sorted(items, key=sort_key)
```

### 9.2 Usage Enforcement

```python
# kernel/hull_gen/generator.py

from kernel.resource_ordering import get_ordered

class HullGenerator:
    def _apply_spray_rails(self, features: HullFeatures, sections: List):
        # CORRECT: Use centralized ordering
        rails = get_ordered(features.spray_rails, "hull.spray_rail")
        
        for rail in rails:
            self._apply_spray_rail(rail, sections)
    
    # FORBIDDEN: Do not do this
    # for rail in features.spray_rails.values():  # Non-deterministic!
```

---

## 10. Tombstone Contract (Explicit)

### 10.1 Deletion Fields

```python
@dataclass
class ResourceConfig:
    # ... existing fields ...
    
    # Lifecycle
    _id: str = ""
    _deleted: bool = False
    _deleted_at: Optional[datetime] = None
    _deleted_by: Optional[str] = None  # program_id that deleted
```

### 10.2 Exclusion Matrix

| Context | Deleted Resources | Reason |
|:--------|:------------------|:-------|
| `get_ordered()` default | **Excluded** | Generators shouldn't see them |
| `get_ordered(include_deleted=True)` | **Included** | For audit/debug |
| HSV preview | **Excluded** | User shouldn't see deleted |
| Validator compatibility | **Excluded** | Don't check against ghosts |
| ExplainRecord | **Included** | Audit trail must be complete |
| Undo/Restore | **Included** | Can un-delete |
| GLB/STEP export | **Excluded** | Not part of geometry |
| Digest to LLM | **Excluded** | LLM shouldn't reference |
| ALIGN target | **Error** | Cannot align to deleted |
| MIRROR source | **Error** | Cannot mirror deleted |

### 10.3 Undelete Operation

```
// In program
UNDELETE <id>  // Reverses DELETE, clears _deleted flag
```

---

## 11. Semantic Trace for ExplainRecord

### 11.1 Trace Schema

```python
@dataclass(frozen=True)
class SemanticTrace:
    """
    Attached to each Action to explain how it was derived.
    """
    # What operation produced this action
    operation: str  # "CREATE", "ALIGN", "DERIVE", etc.
    
    # Inputs to the operation
    inputs: Dict[str, Any]
    
    # Computation performed (human-readable)
    computation: str
    
    # Policy used (for DERIVE)
    policy: Optional[str] = None
    policy_version: Optional[str] = None
    
    # Kernel function called
    kernel_function: Optional[str] = None
    
    def to_explain_string(self) -> str:
        """Generate human-readable explanation."""
        if self.operation == "ALIGN":
            return (
                f"ALIGN: {self.inputs['source_id']}.{self.inputs['axis']} = "
                f"{self.inputs['target_id']}.{self.inputs['axis']} + {self.inputs['offset']} = "
                f"{self.computation}"
            )
        elif self.operation == "DERIVE":
            return (
                f"DERIVE: Used policy '{self.policy}' v{self.policy_version} → {self.computation}"
            )
        elif self.operation == "MIRROR":
            return (
                f"MIRROR: Created {self.inputs['new_id']} from {self.inputs['source_id']} "
                f"about {self.inputs['plane']}, negated fields: {self.inputs.get('mirror_fields', [])}"
            )
        else:
            return f"{self.operation}: {self.computation}"
```

### 11.2 ExplainRecord Extension

```python
@dataclass(frozen=True)
class ExplainRecord:
    # ... existing fields ...
    
    # NEW: Full program and expansion
    source_program: Optional[str] = None  # Original DSL program text
    semantic_traces: tuple = ()  # Tuple[SemanticTrace, ...] for each action
    
    def explain_action(self, action_index: int) -> str:
        """Get human-readable explanation for a specific action."""
        if action_index < len(self.semantic_traces):
            return self.semantic_traces[action_index].to_explain_string()
        return "No semantic trace available"
```

---

## 12. Safety Guarantees

### 12.1 No Arbitrary Code Execution

```python
# kernel/program_executor.py

class ProgramExecutor:
    """
    Executes design programs safely.
    
    FORBIDDEN:
    - eval()
    - exec()
    - __import__()
    - open()
    - Any filesystem/network access
    
    ALLOWED:
    - Calling kernel stdlib functions
    - Basic arithmetic
    - String operations on IDs
    """
    
    FORBIDDEN_BUILTINS = {
        'eval', 'exec', 'compile', '__import__', 'open',
        'input', 'breakpoint', 'globals', 'locals', 'vars',
    }
    
    def execute(self, ast: ProgramAST, state: StateManager) -> ExecutionResult:
        # Create restricted execution environment
        env = RestrictedEnvironment(
            allowed_functions=KERNEL_STDLIB,
            state=state,
        )
        
        # Execute AST nodes
        for node in ast.statements:
            self._execute_statement(node, env)
```

### 12.2 Deterministic ID Generation

```python
# kernel/id_generator.py

def generate_resource_id(
    resource_type: str,
    design_id: str,
    sequence: int,
    hint: Optional[str] = None,
) -> str:
    """
    Generate deterministic resource ID.
    
    Format: <type>_<design_suffix>_<sequence>_<hint?>
    
    Determinism: Same inputs → same output.
    No randomness (UUID) in production paths.
    """
    type_prefix = resource_type.split(".")[-1][:4]
    design_suffix = design_id.split("-")[-1][:4].upper()
    
    base = f"{type_prefix}_{design_suffix}_{sequence:03d}"
    
    if hint:
        # Sanitize hint
        safe_hint = "".join(c for c in hint if c.isalnum() or c == "_")[:8]
        return f"{base}_{safe_hint}"
    
    return base
```

### 12.3 Total Failure (No Silent Fallback)

```python
# kernel/semantic_expander.py

class SemanticExpander:
    def expand(self, ast: ProgramAST, state: StateManager) -> ExpansionResult:
        actions = []
        errors = []
        
        for stmt in ast.statements:
            try:
                expanded = self._expand_statement(stmt, state)
                actions.extend(expanded)
            except SemanticError as e:
                errors.append(ExpansionError(
                    statement_index=stmt.index,
                    line_number=stmt.line,
                    error=str(e),
                    statement_text=stmt.source,
                ))
                # DO NOT continue silently
                # DO NOT use fallback
        
        if errors:
            # Return ALL errors, not just first
            return ExpansionResult(
                success=False,
                errors=errors,
                partial_actions=[],  # No partial execution
            )
        
        return ExpansionResult(success=True, actions=actions, errors=[])
```

---

## 13. Implementation Phases

### Phase 1: Type Registry + Storage Migration (Days 1-4)

**New files:**
- `kernel/stdlib/__init__.py`
- `kernel/stdlib/type_registry.py` — Canonical type schemas
- `kernel/resource_ordering.py` — Centralized ordering

**Changes:**
- Add `_id`, `_deleted`, `_deleted_at` to all config dataclasses
- `HullFeatures.spray_rails: List[...]` → `Dict[str, ...]`
- All geometry code calls `get_ordered()`
- Tests verify deterministic output

---

### Phase 2: Kernel stdlib Foundation (Days 5-7)

**New files:**
- `kernel/stdlib/geometry.py` — ALIGN, MIRROR, SCALE (with type checks)
- `kernel/stdlib/resources.py` — CREATE, UPDATE, DELETE
- `kernel/stdlib/synthesis.py` — DERIVE policies with full contracts
- `kernel/stdlib/constraints.py` — CONSTRAIN/PIN registration

**Changes:**
- Add `SemanticTrace` to `Action`
- Add `pinned_constraints` to design state

---

### Phase 3: Parser + Expander (Days 8-10)

**New files:**
- `deployment/program_parser.py` — Syntax only (uses type registry)
- `kernel/semantic_expander.py` — Calls stdlib, emits Actions

**Contract:**
- Parser outputs AST
- Expander calls stdlib functions
- stdlib functions emit Actions
- Actions go through existing Validator → Executor

---

### Phase 4: HSV Integration (Days 11-12)

**Changes:**
- HSV can "dry run" programs with virtual IDs
- HSV detects ALIGN to non-existent target
- HSV evaluates ephemeral constraints
- HSV returns preview of expanded state

---

### Phase 5: ExplainRecord + API (Days 13-14)

**Changes:**
- ExplainRecord stores `source_program` and `semantic_traces`
- New endpoint: `POST /api/v1/designs/{id}/program`
- Query mode: "why is rail at 0.25?" → returns SemanticTrace

---

## 14. Operator Reference

### 14.1 Resource Operations

| Operator | Syntax | Semantics |
|:---------|:-------|:----------|
| `CREATE` | `CREATE <type> { <params> } AS <id>` | Instantiate typed resource with stable ID |
| `UPDATE` | `UPDATE <id> { <params> }` | Merge params into existing resource |
| `DELETE` | `DELETE <id>` | Tombstone resource (excluded from generation) |
| `UNDELETE` | `UNDELETE <id>` | Restore tombstoned resource |

### 14.2 Geometric Operations

| Operator | Syntax | Semantics |
|:---------|:-------|:----------|
| `ALIGN` | `ALIGN <id> TO <target> ON <axis> OFFSET <value>` | Position relative to another resource |
| `MIRROR` | `MIRROR <id> ABOUT <plane> AS <new_id>` | Create mirrored copy (type must support) |
| `SCALE` | `SCALE <selector> BY <factor> ON <fields>` | Scale matching resources |
| `LOFT` | `LOFT [<section_ids>] INTO <surface_id>` | Create surface from sections |
| `OFFSET` | `OFFSET <surface_id> BY <dist_m> AS <new_id>` | Create parallel surface (shell thickness) |

### 14.3 Constraint Operations

| Operator | Syntax | Semantics |
|:---------|:-------|:----------|
| `DERIVE` | `DERIVE <path> USING <policy>` | Compute value via named synthesis policy |
| `CONSTRAIN` | `CONSTRAIN <path> <op> <value>` | Ephemeral validation (this program only) |
| `PIN CONSTRAINT` | `PIN CONSTRAINT <path> <op> <value>` | Persistent constraint (attached to design) |
| `UNPIN CONSTRAINT` | `UNPIN CONSTRAINT <id>` | Remove persistent constraint |
| `PREFER` | `PREFER <path> TOWARD <target> WEIGHT <w>` | Soft optimization target |

### 14.4 Available DERIVE Policies

**⚠️ CRITICAL: All DERIVE policies are OPTIONAL convenience heuristics. Agents can SET values directly. These policies encode design taste, not physics — the kernel validates outcomes, not ratios.**

**Core Hull Policies (ALL OPTIONAL):**

| Policy Name | Inputs | Output | Type | Description |
|:------------|:-------|:-------|:-----|:------------|
| `lb_ratio` | `hull.loa`, `target_ratio` (agent-provided) | `hull.beam` | arithmetic | Beam = LOA / ratio — **agent specifies ratio, not hull type** |
| `displacement_beam` | `hull.displacement_m3`, `hull.lwl` | `hull.beam` | heuristic | Beam from displacement target |
| `gm_beam` | `stability.gm_required_m`, `hull.draft`, `hull.displacement_m3` | `hull.beam` | iterative_solve | Beam from GM requirement |
| `froude_draft` | `hull.loa`, `mission.speed_kts` | `hull.draft` | heuristic | Draft for target Froude number |

**Usage example:**
```
# Agent decides ratio directly — no hull_type lookup
DERIVE hull.beam FROM lb_ratio(loa=hull.loa, target_ratio=5.5)

# Or agent just SETs the value directly
SET hull.beam = 4.5
```

**NOTE:** All DERIVE policies are OPTIONAL. Agents can SET values directly. The kernel validates the resulting physics, not the ratios used.

**Physics & Geometry Validation Policies (NOT design heuristics):**

| Policy Name | Inputs | Output | Type | Description |
|:------------|:-------|:-------|:-----|:------------|
| `flow_area_adequacy` | `geometry.flow_paths.*`, `mission.speed_kts` | adequacy ratio | heuristic | Is flow area sufficient for conditions? |
| `discontinuity_interference` | `geometry.discontinuities.*` | boolean | geometric | Do discontinuities interfere with each other? |
| `surface_continuity` | surfaces, edge treatments | continuity map | geometric | Validate G0/G1/G2 continuity |
| `structural_stress` | geometry, materials, loads | stress ratio | iterative_solve | Hull structural analysis |

**These are NOT design-concept policies.** There is no "stepped_hull_spacing" policy because the kernel doesn't know "stepped hull." The kernel validates geometry and physics.

### 14.5 Geometric Primitives (What the Kernel Actually Knows)

| Primitive | Mirrorable | Key Fields | What It Is |
|:----------|:-----------|:-----------|:-----------|
| `geometry.body` | ✅ | `body_type`, `offset_y_m`, `surface_id` | Distinct solid volume (demihull, pontoon) |
| `geometry.section` | ❌ | `station`, `definition_type`, params | Cross-section for surface lofting |
| `geometry.surface` | ❌ | `definition_type`, `section_ids` or NURBS | Parametric surface (NURBS or lofted) |
| `geometry.attachment` | ✅ | `parent_body_id`, `child_body_id`, `type` | Connection between bodies |
| `geometry.discontinuity` | ❌ | `surface_id`, `station`, `depth_m` | Break in surface continuity |
| `geometry.flow_path` | ✅ | `inlet_point`, `outlet_point`, `area_m2` | Path for fluid flow |
| `geometry.opening` | ✅ | `center_u`, `center_v`, `shape`, `width_m` | Cutout in a surface |
| `geometry.surface_point` | ✅ | `surface_id`, `u`, `v` | Point defined on a surface |
| `geometry.edge_treatment` | ❌ | `edge_id`, `treatment`, `radius_m` | Edge modification (sharp/fillet/etc.) |

### 14.6 Convenience Wrappers (DEPRECATED for Agent Use)

These exist for **backwards compatibility and human ergonomics only**. 

> **AGENTS SHOULD NOT USE THESE.** They compile down to geometric primitives, but using them directly limits novelty to this vocabulary.

| Wrapper | Deprecated | Use Instead |
|:--------|:-----------|:------------|
| `hull.spray_rail` | ✅ | `geometry.surface_modification` + `geometry.edge_treatment` |
| `hull.chine` | ✅ | `geometry.edge_treatment` |
| `hull.knuckle` | ✅ | `geometry.edge_treatment` |
| `hull.transom_cutout` | ✅ | `geometry.opening` |
| `hull.transom_extension` | ✅ | `geometry.surface` + `geometry.attachment` |

**Design concepts are NOT primitives:**

There is no `hull.step` type. A "step" is a `geometry.discontinuity`.
There is no `hull.ventilation_duct` type. A "vent" is a `geometry.flow_path` + `geometry.opening`.
There is no `hull.catamaran` type. A catamaran is two `geometry.body` primitives with offset.

**The kernel knows geometry. Design emerges from composition.**

**Novelty principle:** An agent using `geometry.surface_modification` can invent "triple-rail whisker" (never seen before). An agent using `hull.spray_rail` can only create spray rails.

---

## 15. Codebase Implementation Plan

This section details **exactly what files need to change** to implement the design language spec.

### 15.1 Overview: What Exists vs. What Needs Implementation

| Component | Exists? | Location | Status |
|:----------|:--------|:---------|:-------|
| NURBS Curve/Surface | ✅ Yes | `magnet/hull_gen/nurbs.py` | Full implementation exists |
| Section generation | ✅ Yes | `magnet/hull_gen/generator.py` | Sections generated programmatically |
| Catamaran support | ✅ Partial | `generator.py` + `synthesis.py` | Via `HullType.CATAMARAN` + `hull_spacing_m` |
| Section as first-class primitive | ❌ No | — | Need `geometry.section` type |
| Surface as first-class primitive | ❌ No | — | Need `geometry.surface` type |
| Body as first-class primitive | ❌ No | — | Need `geometry.body` type |
| LOFT operation | ❌ No | — | Need `kernel/stdlib/geometry.py` |
| Type Registry | ❌ No | — | Need `kernel/stdlib/type_registry.py` |
| Design Language Parser | ❌ No | — | Need `deployment/program_parser.py` |
| Semantic Expander | ❌ No | — | Need `kernel/semantic_expander.py` |

### 15.2 Phase 1: Type Registry + Primitive Storage (Days 1-5)

**New Files:**

```
kernel/stdlib/
├── __init__.py
├── type_registry.py    # TYPE_SCHEMAS dict (from §4)
├── geometry.py         # ALIGN, MIRROR, SCALE, LOFT implementations
├── resources.py        # CREATE, UPDATE, DELETE handlers
└── synthesis.py        # DERIVE policies with PolicyContract
```

**File: `kernel/stdlib/type_registry.py`**

Implement the full `TYPE_SCHEMAS` dictionary from §4.2, including:
- `geometry.body`
- `geometry.section`
- `geometry.surface`
- `geometry.attachment`
- All existing feature types

**File: `magnet/core/state_manager.py` — Changes:**

```python
# Add new state collections for geometric primitives
STATE_PATHS.update([
    # Bodies
    "geometry.bodies",
    "geometry.bodies.<id>",
    "geometry.bodies.<id>.body_type",
    "geometry.bodies.<id>.offset_y_m",
    "geometry.bodies.<id>.surface_id",
    
    # Sections
    "geometry.sections",
    "geometry.sections.<id>",
    "geometry.sections.<id>.station",
    "geometry.sections.<id>.definition_type",
    # ... all section fields
    
    # Surfaces
    "geometry.surfaces",
    "geometry.surfaces.<id>",
    "geometry.surfaces.<id>.definition_type",
    "geometry.surfaces.<id>.section_ids",
    # ... all surface fields
    
    # Attachments
    "geometry.attachments",
])
```

**File: `magnet/hull_gen/geometry.py` — Changes:**

**CRITICAL: These are NOT new geometry engines.** They are wrappers/factories that:
1. Store language-level parameters
2. Convert to EXISTING canonical classes (`HullSection`, `NURBSSurface`)
3. Feed the EXISTING downstream pipeline

```python
@dataclass
class GeometryBody:
    """
    First-class body primitive — WRAPS existing geometry, does not replace.
    
    When geometry is generated, this becomes part of the existing
    HullGeometry structure via HullGenerator.
    """
    _id: str
    body_type: str  # "hull", "pontoon", "outrigger", "tunnel_structure"
    parent_body_id: Optional[str] = None
    offset_x_m: float = 0.0
    offset_y_m: float = 0.0
    offset_z_m: float = 0.0
    surface_id: Optional[str] = None
    _deleted: bool = False
    
@dataclass
class GeometrySection:
    """
    First-class section primitive — CONVERTS TO HullSection.
    
    The to_hull_section() method produces the EXISTING HullSection class
    that is already consumed by tessellation and hydrostatics.
    """
    _id: str
    station: float
    x_position_m: float
    definition_type: str  # "parametric", "points", "nurbs_curve"
    # Parametric fields
    half_beam_m: Optional[float] = None
    draft_m: Optional[float] = None
    deadrise_deg: Optional[float] = None
    fullness: Optional[float] = None
    # Points field
    points: Optional[List[Dict[str, float]]] = None
    # NURBS curve fields
    nurbs_control_points: Optional[List[Dict]] = None
    nurbs_degree: int = 3
    nurbs_weights: Optional[List[float]] = None
    nurbs_knots: Optional[List[float]] = None
    # Metadata
    is_midship: bool = False
    is_transom: bool = False
    _deleted: bool = False
    
    def to_hull_section(self) -> "HullSection":
        """
        Convert to CANONICAL HullSection (from hull_gen/geometry.py).
        
        This is the critical bridge — language primitives compile to
        existing geometry classes consumed by the downstream pipeline.
        """
        from magnet.hull_gen.geometry import HullSection, SectionPoint, Point3D
        
        section = HullSection(
            station=self.station,
            x_position=self.x_position_m,
        )
        
        if self.definition_type == "parametric":
            section.points = self._parametric_to_points()
        elif self.definition_type == "points":
            section.points = self._dict_points_to_section_points()
        elif self.definition_type == "nurbs_curve":
            section.points = self._nurbs_to_points()
        
        section.half_beam = self.half_beam_m or 0.0
        section.draft_local = self.draft_m or 0.0
        section.deadrise_deg = self.deadrise_deg or 0.0
        
        return section

@dataclass
class GeometrySurface:
    """
    First-class surface primitive — CONVERTS TO NURBSSurface.
    
    The to_nurbs_surface() method produces the EXISTING NURBSSurface class
    from hull_gen/nurbs.py.
    """
    _id: str
    surface_type: str  # "hull_shell", "deck", "bulkhead", "appendage"
    definition_type: str  # "nurbs", "lofted", "ruled", "developable"
    body_id: Optional[str] = None
    # NURBS fields (if definition_type == "nurbs")
    nurbs_control_points: Optional[List[List[Dict]]] = None
    nurbs_degree_u: int = 3
    nurbs_degree_v: int = 3
    nurbs_weights: Optional[List[List[float]]] = None
    nurbs_knots_u: Optional[List[float]] = None
    nurbs_knots_v: Optional[List[float]] = None
    # Lofting fields (if definition_type == "lofted")
    section_ids: Optional[List[str]] = None
    loft_tension: float = 0.5
    continuity_bow: str = "G1"
    continuity_stern: str = "G1"
    # Cached canonical surface (populated after lofting/conversion)
    _canonical_surface: Optional["NURBSSurface"] = None
    _deleted: bool = False
    
    def to_nurbs_surface(self) -> "NURBSSurface":
        """
        Convert to CANONICAL NURBSSurface (from hull_gen/nurbs.py).
        
        This is the critical bridge — language surfaces compile to
        existing NURBS representation consumed by tessellation/export.
        """
        from magnet.hull_gen.nurbs import NURBSSurface
        from magnet.hull_gen.geometry import Point3D
        
        if self._canonical_surface is not None:
            return self._canonical_surface
        
        surface = NURBSSurface(
            degree_u=self.nurbs_degree_u,
            degree_v=self.nurbs_degree_v,
        )
        
        if self.nurbs_control_points:
            surface.control_points = [
                [Point3D(p["x"], p["y"], p["z"]) for p in row]
                for row in self.nurbs_control_points
            ]
        
        if self.nurbs_weights:
            surface.weights = self.nurbs_weights
        if self.nurbs_knots_u:
            surface.knot_vector_u = self.nurbs_knots_u
        if self.nurbs_knots_v:
            surface.knot_vector_v = self.nurbs_knots_v
        
        if not surface.knot_vector_u:
            surface.generate_uniform_knots()
        
        self._canonical_surface = surface
        return surface
```

### 15.2.1 The Bridge: Language → Canonical → Downstream

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 LANGUAGE PRIMITIVES → CANONICAL CLASSES                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Language Primitive          Method              Canonical Class            │
│  ─────────────────           ──────              ───────────────            │
│  GeometrySection      →  to_hull_section()  →   HullSection                 │
│  GeometrySurface      →  to_nurbs_surface() →   NURBSSurface                │
│  GeometryBody         →  (applies offset)   →   HullGeometry.sections       │
│                                                                             │
│  The downstream pipeline ONLY sees canonical classes:                       │
│                                                                             │
│  HullSection          →  HullGeometryPipeline  →  WebGL Mesh                │
│  NURBSSurface         →  HullGeometryPipeline  →  WebGL Mesh                │
│  HullGeometry         →  compute_hydrostatics  →  Displacement, GM, LCB     │
│  HullGeometry         →  STLExporter           →  STL File                  │
│                                                                             │
│  NO NEW GEOMETRY CLASSES ARE CONSUMED BY DOWNSTREAM CODE                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 15.3 Phase 2: LOFT Operation (Days 6-8)

**File: `kernel/stdlib/geometry.py`**

```python
def loft_sections_to_surface(
    section_ids: List[str],
    state: "DesignState",
    target_surface_id: str,
    tension: float = 0.5,
    continuity_bow: str = "G1",
    continuity_stern: str = "G1",
) -> List[Action]:
    """
    LOFT operation: Create surface from sections.
    
    This is a KERNEL FUNCTION — called by the semantic expander.
    Returns Actions to be validated and executed.
    """
    from magnet.hull_gen.nurbs import NURBSSurface
    
    # 1. Load sections from state
    sections = []
    for sid in section_ids:
        section = state.get(f"geometry.sections.{sid}")
        if section is None:
            raise LoftError(f"Section not found: {sid}")
        sections.append(section)
    
    # 2. Validate section ordering
    stations = [s["station"] for s in sections]
    if stations != sorted(stations):
        raise LoftError("Sections must be in ascending station order")
    
    # 3. Convert sections to control point columns
    control_net = []
    for section in sections:
        column = _section_to_control_points(section)
        control_net.append(column)
    
    # 4. Fit NURBS surface through sections
    surface = NURBSSurface()
    surface.control_points = control_net
    surface.degree_u = 3
    surface.degree_v = 3
    surface.generate_uniform_knots()
    
    # 5. Return Actions (not direct mutation)
    return [
        Action(
            action_id=generate_action_id(),
            action_type="create",
            path=f"geometry.surfaces.{target_surface_id}",
            value={
                "_id": target_surface_id,
                "surface_type": "hull_shell",
                "definition_type": "lofted",
                "section_ids": section_ids,
                "loft_tension": tension,
                "continuity_bow": continuity_bow,
                "continuity_stern": continuity_stern,
                "nurbs_control_points": _control_net_to_json(control_net),
                "nurbs_degree_u": 3,
                "nurbs_degree_v": 3,
            },
            semantic_trace=SemanticTrace(
                operation="LOFT",
                source_statement=f"LOFT {section_ids} INTO {target_surface_id}",
                computation=f"Fitted NURBS surface through {len(sections)} sections",
            ),
        )
    ]

def _section_to_control_points(section: Dict) -> List[Dict]:
    """Convert section definition to control points."""
    if section["definition_type"] == "parametric":
        return _parametric_section_to_points(section)
    elif section["definition_type"] == "points":
        return section["points"]
    elif section["definition_type"] == "nurbs_curve":
        return section["nurbs_control_points"]
    else:
        raise ValueError(f"Unknown section type: {section['definition_type']}")
```

### 15.4 Phase 3: Multi-Body Support (Days 9-11)

**File: `magnet/hull_gen/generator.py` — Changes:**

Update `HullGenerator.generate()` to:
1. Check for `geometry.bodies` in state
2. If bodies exist, generate geometry per-body
3. Transform sections by body offset

```python
def generate(self, definition: HullDefinition, state: Optional[Dict] = None) -> HullGeometry:
    """
    Generate hull geometry.
    
    If state contains geometry.bodies, use multi-body mode.
    Otherwise, use legacy single-hull mode.
    """
    bodies = state.get("geometry.bodies", {}) if state else {}
    
    if bodies:
        return self._generate_multi_body(definition, bodies, state)
    else:
        return self._generate_single_hull(definition)

def _generate_multi_body(
    self, 
    definition: HullDefinition,
    bodies: Dict[str, Dict],
    state: Dict,
) -> HullGeometry:
    """Generate geometry for multi-body vessel."""
    combined_geometry = HullGeometry(hull_id=definition.hull_id)
    
    for body_id, body in bodies.items():
        if body.get("_deleted"):
            continue
            
        # Get surface for this body
        surface_id = body.get("surface_id")
        if not surface_id:
            continue
            
        surface = state.get(f"geometry.surfaces.{surface_id}")
        if not surface:
            continue
        
        # Generate sections for this body
        if surface.get("definition_type") == "lofted":
            sections = self._load_sections(surface["section_ids"], state)
        else:
            sections = self._nurbs_surface_to_sections(surface)
        
        # Apply body offset transformation
        offset_y = body.get("offset_y_m", 0.0)
        offset_z = body.get("offset_z_m", 0.0)
        
        transformed_sections = self._offset_sections(sections, offset_y, offset_z)
        combined_geometry.sections.extend(transformed_sections)
    
    # Compute combined volume
    combined_geometry.compute_volume()
    
    return combined_geometry
```

**File: `magnet/webgl/geometry_pipeline.py` — Changes:**

Update tessellation to handle multi-body:

```python
def tessellate_hull(self, geometry: HullGeometry, state: Dict) -> MeshData:
    """Tessellate hull geometry, handling multi-body."""
    bodies = state.get("geometry.bodies", {})
    
    if not bodies:
        # Legacy single-hull path
        return self._tessellate_single_hull(geometry)
    
    # Multi-body: tessellate each body, combine
    meshes = []
    for body_id, body in bodies.items():
        if body.get("_deleted"):
            continue
        
        body_sections = self._get_body_sections(geometry, body_id)
        mesh = self._tessellate_body(body_sections, body)
        meshes.append(mesh)
    
    return self._combine_meshes(meshes)
```

### 15.5 Phase 4: Parser + Expander (Days 12-15)

**New File: `deployment/program_parser.py`**

```python
"""
Program Parser — Syntax validation only.

CRITICAL: Parser does NOT define types. It reads from kernel type registry.
"""

from kernel.stdlib.type_registry import get_type_schema, validate_resource_params

class ProgramParser:
    """Parse design language programs to AST."""
    
    def parse(self, program_text: str) -> AST:
        """Parse program text to AST."""
        tokens = self._tokenize(program_text)
        statements = []
        
        while tokens:
            stmt = self._parse_statement(tokens)
            statements.append(stmt)
        
        return AST(statements=statements)
    
    def _parse_statement(self, tokens: Tokens) -> ASTNode:
        keyword = tokens.consume()
        
        if keyword == "CREATE":
            return self._parse_create(tokens)
        elif keyword == "UPDATE":
            return self._parse_update(tokens)
        elif keyword == "DELETE":
            return self._parse_delete(tokens)
        elif keyword == "ALIGN":
            return self._parse_align(tokens)
        elif keyword == "MIRROR":
            return self._parse_mirror(tokens)
        elif keyword == "LOFT":
            return self._parse_loft(tokens)
        elif keyword == "DERIVE":
            return self._parse_derive(tokens)
        elif keyword == "CONSTRAIN":
            return self._parse_constrain(tokens)
        elif keyword == "PIN":
            return self._parse_pin_constraint(tokens)
        else:
            raise ParseError(f"Unknown keyword: {keyword}")
    
    def _parse_create(self, tokens: Tokens) -> CreateNode:
        type_name = tokens.consume_type()
        params = tokens.consume_params()
        tokens.expect("AS")
        alias = tokens.consume_identifier()
        
        # Validate against kernel schema (does not define schema)
        schema = get_type_schema(type_name)  # Calls kernel
        errors = validate_resource_params(type_name, params)
        
        if errors:
            raise ParseError(f"Invalid CREATE: {errors}")
        
        return CreateNode(type_name=type_name, params=params, alias=alias)
    
    def _parse_loft(self, tokens: Tokens) -> LoftNode:
        section_ids = tokens.consume_list()
        tokens.expect("INTO")
        surface_id = tokens.consume_identifier()
        return LoftNode(section_ids=section_ids, surface_id=surface_id)
```

**New File: `kernel/semantic_expander.py`**

```python
"""
Semantic Expander — Expands AST to Actions by calling kernel stdlib.

CRITICAL: Expander ONLY calls kernel functions. It does NOT define semantics.
"""

from kernel.stdlib import geometry, resources, synthesis, constraints

class SemanticExpander:
    """Expand AST nodes to Actions."""
    
    def __init__(self, state: DesignState):
        self.state = state
        self.actions: List[Action] = []
    
    def expand(self, ast: AST) -> List[Action]:
        """Expand full AST to action list."""
        for node in ast.statements:
            self._expand_node(node)
        return self.actions
    
    def _expand_node(self, node: ASTNode) -> None:
        if isinstance(node, CreateNode):
            actions = resources.create_resource(
                node.type_name, node.params, node.alias, self.state
            )
            self.actions.extend(actions)
        
        elif isinstance(node, AlignNode):
            actions = geometry.align_resource(
                node.source_id, node.target_id, 
                node.axis, node.offset, self.state
            )
            self.actions.extend(actions)
        
        elif isinstance(node, MirrorNode):
            actions = geometry.mirror_resource(
                node.source_id, node.plane, node.new_id, self.state
            )
            self.actions.extend(actions)
        
        elif isinstance(node, LoftNode):
            actions = geometry.loft_sections_to_surface(
                node.section_ids, self.state, node.surface_id
            )
            self.actions.extend(actions)
        
        elif isinstance(node, DeriveNode):
            actions = synthesis.derive_value(
                node.target_path, node.policy_name, self.state
            )
            self.actions.extend(actions)
        
        elif isinstance(node, ConstrainNode):
            if node.persistent:
                actions = constraints.pin_constraint(
                    node.path, node.operator, node.value, self.state
                )
            else:
                actions = constraints.ephemeral_constraint(
                    node.path, node.operator, node.value, self.state
                )
            self.actions.extend(actions)
```

### 15.6 Phase 5: Hydrostatics for Multi-Body (Days 16-18)

**File: `magnet/kernel/analysis.py` — Changes:**

```python
def compute_hydrostatics(state: Dict, geometry: HullGeometry) -> Dict:
    """
    Compute hydrostatics, handling multi-body.
    
    For multi-body vessels:
    - Compute per-body displacement and buoyancy
    - Sum for total displacement
    - Compute combined LCB, VCB, GM
    """
    bodies = state.get("geometry.bodies", {})
    
    if not bodies:
        return _compute_single_hull_hydrostatics(geometry)
    
    body_results = []
    total_displacement = 0.0
    weighted_lcb = 0.0
    weighted_vcb = 0.0
    
    for body_id, body in bodies.items():
        if body.get("_deleted"):
            continue
        
        body_geometry = _extract_body_geometry(geometry, body_id)
        result = _compute_single_hull_hydrostatics(body_geometry)
        
        total_displacement += result["displacement_m3"]
        weighted_lcb += result["displacement_m3"] * result["lcb_m"]
        weighted_vcb += result["displacement_m3"] * result["vcb_m"]
        
        body_results.append({
            "body_id": body_id,
            **result
        })
    
    return {
        "displacement_m3": total_displacement,
        "lcb_m": weighted_lcb / total_displacement if total_displacement > 0 else 0,
        "vcb_m": weighted_vcb / total_displacement if total_displacement > 0 else 0,
        "body_results": body_results,
    }
```

### 15.7 File Change Summary

| File | Change Type | Description |
|:-----|:------------|:------------|
| `kernel/stdlib/__init__.py` | **NEW** | Package init |
| `kernel/stdlib/type_registry.py` | **NEW** | All type schemas |
| `kernel/stdlib/geometry.py` | **NEW** | ALIGN, MIRROR, LOFT, OFFSET |
| `kernel/stdlib/resources.py` | **NEW** | CREATE, UPDATE, DELETE |
| `kernel/stdlib/synthesis.py` | **NEW** | DERIVE policies |
| `kernel/stdlib/constraints.py` | **NEW** | CONSTRAIN, PIN handling |
| `kernel/semantic_expander.py` | **NEW** | AST → Actions |
| `deployment/program_parser.py` | **NEW** | Program → AST |
| `magnet/core/state_manager.py` | **MODIFY** | Add geometry.* paths |
| `magnet/hull_gen/geometry.py` | **MODIFY** | Add GeometryBody, Section, Surface |
| `magnet/hull_gen/generator.py` | **MODIFY** | Multi-body generation |
| `magnet/webgl/geometry_pipeline.py` | **MODIFY** | Multi-body tessellation |
| `magnet/kernel/analysis.py` | **MODIFY** | Multi-body hydrostatics |
| `magnet/control_plane/hsv.py` | **MODIFY** | Preview with virtual bodies |
| `magnet/kernel/action_validator.py` | **MODIFY** | Validate geometry.* paths |

### 15.8 Downstream Pipeline Contract

**CRITICAL:** This section documents how language-generated geometry feeds into every downstream phase. There is ONE path — the existing path.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DOWNSTREAM PIPELINE CONTRACT                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Language Program                                                           │
│       │                                                                     │
│       ▼                                                                     │
│  GeometrySection.to_hull_section() → HullSection (canonical)                │
│  GeometrySurface.to_nurbs_surface() → NURBSSurface (canonical)              │
│       │                                                                     │
│       ▼                                                                     │
│  HullGenerator.generate() → HullGeometry (canonical)                        │
│       │                                                                     │
│       ├──────────────────────────────────────────────────────────────────┐  │
│       │  EXISTING DOWNSTREAM CONSUMERS (NO CHANGES NEEDED)               │  │
│       │                                                                  │  │
│       │  ┌─────────────────────────────────────────────────────────────┐│  │
│       │  │  HullGeometryPipeline.tessellate()                          ││  │
│       │  │  → Input: HullGeometry.sections (List[HullSection])         ││  │
│       │  │  → Output: WebGL mesh (vertices, faces, normals)            ││  │
│       │  │  → Location: magnet/webgl/geometry_pipeline.py              ││  │
│       │  └─────────────────────────────────────────────────────────────┘│  │
│       │                                                                  │  │
│       │  ┌─────────────────────────────────────────────────────────────┐│  │
│       │  │  compute_hydrostatics()                                     ││  │
│       │  │  → Input: HullGeometry                                      ││  │
│       │  │  → Output: displacement, LCB, VCB, GM, waterplane area      ││  │
│       │  │  → Location: magnet/kernel/analysis.py                      ││  │
│       │  └─────────────────────────────────────────────────────────────┘│  │
│       │                                                                  │  │
│       │  ┌─────────────────────────────────────────────────────────────┐│  │
│       │  │  compute_resistance()                                       ││  │
│       │  │  → Input: HullGeometry + speed                              ││  │
│       │  │  → Output: resistance components, power                     ││  │
│       │  │  → Location: magnet/kernel/analysis.py                      ││  │
│       │  └─────────────────────────────────────────────────────────────┘│  │
│       │                                                                  │  │
│       │  ┌─────────────────────────────────────────────────────────────┐│  │
│       │  │  STLExporter / IGESExporter                                 ││  │
│       │  │  → Input: HullGeometry                                      ││  │
│       │  │  → Output: STL/IGES file                                    ││  │
│       │  │  → Location: magnet/export/                                 ││  │
│       │  └─────────────────────────────────────────────────────────────┘│  │
│       │                                                                  │  │
│       └──────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  THE LANGUAGE DOES NOT BYPASS ANY OF THESE.                                 │
│  IT FEEDS INTO THE SAME CANONICAL HullGeometry THAT EVERYTHING CONSUMES.    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 15.9 Determinism Requirements

| Requirement | Enforcement | Location |
|:------------|:------------|:---------|
| Same program + same state = same HullGeometry | No random/time-based logic in expansion | `semantic_expander.py` |
| Section ordering is deterministic | Ordered by station ascending | `loft_sections_to_surface()` |
| NURBS fitting is deterministic | No random initialization | `NURBSSurface.fit_through_sections()` |
| Tessellation is deterministic | Fixed vertex ordering | `HullGeometryPipeline` |
| Hydrostatics is deterministic | No sampling variation | `compute_hydrostatics()` |

### 15.10 Migration Path (Backwards Compatibility)

**Critical:** Existing designs must continue to work.

```python
# In HullGenerator.generate():

def generate(self, definition: HullDefinition, state: Optional[Dict] = None) -> HullGeometry:
    """
    Generate hull geometry.
    
    BACKWARDS COMPATIBILITY:
    - If no geometry.bodies in state → use legacy single-hull mode
    - Check for geometry.bodies in state for multi-body generation
    
    NOTE: Generator does NOT dispatch on hull type enum.
    Multi-body vessels are created via geometry.body primitives, 
    NOT by checking for "catamaran" or "trimaran" types.
    """
    bodies = state.get("geometry.bodies", {}) if state else {}
    
    # Multi-body generation is driven by geometry.body primitives, not hull_type
    # If bodies exist in state, use multi-body generation
    # If no bodies, generate single hull from sections
    if bodies:
        return self._generate_multi_body(definition, bodies, state)
    else:
        return self._generate_single_hull(definition)


# NOTE: _create_legacy_catamaran_bodies() has been REMOVED.
# Multi-body vessels MUST be defined via geometry.body primitives.
# The kernel does not contain design knowledge about what "catamaran" means.
# See MAGNET_Implementation_Spec.md §4 for migration of legacy designs.


def _generate_multi_body(
    self,
    definition: HullDefinition,
    bodies: Dict[str, Dict],
    state: Optional[StateManager] = None,
) -> HullGeometry:
    """
    Generate geometry for multi-body vessel from body primitives.
    
    This method is body-count agnostic — works for 2, 3, or N bodies.
    No special-casing for "catamaran" vs "trimaran".
    """
    return {
        "demihull_port": {
            "_id": "demihull_port",
            "body_type": "hull",
            "offset_y_m": hull_spacing / 2,
        },
        "demihull_stbd": {
            "_id": "demihull_stbd",
            "body_type": "hull",
            "offset_y_m": -hull_spacing / 2,
        },
    }
```

---

## 16. Summary: What This Achieves

| Goal | How Achieved |
|:-----|:-------------|
| **Infinite designs** | Compose geometric primitives; kernel never enumerates designs |
| **Multi-hull vessels** | Bodies + surfaces + sections compose into catamaran, trimaran, etc. |
| **No design catalog** | Kernel knows geometry/physics, not "stepped hull" or "catamaran" |
| **True composability** | Discontinuity + flow path + opening = anything |
| **Section-based definition** | Traditional naval architecture workflow supported natively |
| **NURBS surfaces** | Direct NURBS or section lofting — same underlying representation |
| **No second geometry engine** | Language compiles INTO existing `HullSection`, `NURBSSurface`, `HullGeometry` |
| **One downstream pipeline** | All geometry feeds tessellation/hydrostatics/export (multi-body requires extensions per `MAGNET_Physics_Gaps_And_Solutions.md`) |
| **No second kernel** | Compiler calls stdlib; stdlib doesn't define physics |
| **Deterministic** | Policies not formulas; centralized ordering; no randomness |
| **Auditable** | SemanticTrace on every action; full program in ExplainRecord |
| **Safe** | Sandboxed DSL; no eval; forbidden builtins |
| **Predictable failure** | No silent fallback; all errors returned |
| **Agent-friendly** | Agents propose programs; kernel validates geometry/physics |
| **Explainable** | "Created discontinuity at station 0.65 with depth 0.08m" |
| **Novel designs work** | Designs no engineer anticipated compile without new code |
| **Kernel validates reality** | Physics and geometry, not design intent |

### The Acid Test

> **Test 1:** Create a stepped, ventilated, multi-stage planing hull using only discontinuities, flow paths, and openings. No "stepped hull" type.
>
> **Test 2:** Create a catamaran using only bodies, surfaces, and sections. No "catamaran" type.
>
> **Test 3:** Create a novel hull configuration — one no naval architect has ever drawn — and validate it without adding new code.
>
> If any of these tests require new resource types or new code, the system has failed.

---

## 17. Appendix: JSON Program Format

For API transmission, programs can be represented as JSON:

> **NOTE:** This example uses ONLY `geometry.*` primitives, as required by Section 0.2.
> Legacy `hull.*` types are deprecated for agent use.

```json
{
  "program_id": "high_performance_catamaran_v1",
  "version": "1.0",
  "statements": [
    {
      "op": "CREATE",
      "type": "geometry.body",
      "params": {
        "body_type": "demihull",
        "physics_category": "surface_piercing",
        "offset_y_m": -3.0
      },
      "as": "port_hull"
    },
    {
      "op": "CREATE",
      "type": "geometry.body",
      "params": {
        "body_type": "demihull",
        "physics_category": "surface_piercing",
        "offset_y_m": 3.0
      },
      "as": "stbd_hull"
    },
    {
      "op": "CREATE",
      "type": "geometry.section",
      "params": {
        "station": 0.0,
        "x_position_m": 0.0,
        "definition_type": "parametric",
        "half_beam_m": 0.8,
        "draft_m": 0.6,
        "deadrise_deg": 45
      },
      "as": "bow_section"
    },
    {
      "op": "CREATE",
      "type": "geometry.section",
      "params": {
        "station": 1.0,
        "x_position_m": 12.0,
        "definition_type": "parametric",
        "half_beam_m": 1.0,
        "draft_m": 0.4,
        "deadrise_deg": 20
      },
      "as": "transom_section"
    },
    {
      "op": "CREATE",
      "type": "geometry.surface",
      "params": {
        "surface_type": "hull_shell",
        "physics_category": "watertight",
        "definition_type": "lofted",
        "body_id": "port_hull",
        "section_ids": ["bow_section", "transom_section"]
      },
      "as": "port_surface"
    },
    {
      "op": "CREATE",
      "type": "geometry.discontinuity",
      "params": {
        "surface_id": "port_surface",
        "station": 0.5,
        "depth_m": 0.04,
        "profile": "transverse"
      },
      "as": "step_1"
    },
    {
      "op": "CREATE",
      "type": "geometry.opening",
      "params": {
        "surface_id": "port_surface",
        "center_u": 1.0,
        "center_v": 0.3,
        "shape": "semicircle",
        "width_m": 0.5,
        "height_m": 0.8
      },
      "as": "jet_tunnel_port"
    },
    {
      "op": "MIRROR",
      "source": "port_surface",
      "plane": "centerline",
      "as": "stbd_surface"
    },
    {
      "op": "CONSTRAIN",
      "path": "stability.gm_m",
      "rule": ">=",
      "value": 0.8,
      "persistent": false
    },
    {
      "op": "PIN_CONSTRAINT",
      "path": "hull.beam",
      "rule": ">=",
      "value": 2.5,
      "reason": "Minimum beam for stability"
    }
  ]
}
```

---

## 18. Related Documents

| Document | Purpose |
|:---------|:--------|
| `MAGNET_Unified_Implementation_Plan.md` | Multi-agent swarm architecture and implementation roadmap |
| `MAGNET_Failure_Modes_And_Mitigations.md` | Implementation plan prioritized for engineer-in-loop workflow |
| `MAGNET_Audit_Prompts.md` | **Completed audit** with verified file locations and implementation plan |
| `MAGNET_Implementation_Spec.md` | **Unified spec:** Agent prompts, API contracts, test plan, migration |
| `MAGNET_Physics_Gaps_And_Solutions.md` | **CRITICAL:** Physics engine limitations for novel forms, multi-body hydrostatics, resistance method selection |
| `MAGNET_Hard_Questions_Answers.md` | Reality check: codebase verification, LLM config, first milestone, validation data |
| `MAGNET_Implementation_Guide.md` | **START HERE:** Step-by-step implementation roadmap with code |

---

## Canonical Geometry Model Verification

The following codebase locations have been verified per the audit in `MAGNET_Audit_Prompts.md`:

| Canonical Class | Location | Status |
|:----------------|:---------|:-------|
| `Point3D` | `magnet/hull_gen/geometry.py` lines 40-108 | ✅ Verified |
| `SectionPoint` | `magnet/hull_gen/geometry.py` lines 110-154 | ✅ Verified |
| `HullSection` | `magnet/hull_gen/geometry.py` lines 157-261 | ✅ Verified |
| `HullGeometry` | `magnet/hull_gen/geometry.py` lines 372-491 | ✅ Verified |
| `NURBSCurve` | `magnet/hull_gen/nurbs.py` lines 17-282 | ✅ Verified |
| `NURBSSurface` | `magnet/hull_gen/nurbs.py` lines 285-514 | ✅ Verified |

All design language primitives (`geometry.section`, `geometry.surface`, `geometry.body`) MUST compile to these canonical classes.

---

## 19. Version History

| Version | Date | Changes |
|:--------|:-----|:--------|
| 1.0 | 2026-01-04 | Initial specification |
| 1.1 | 2026-01-04 | Added: Constraint persistence contract (§3), Type registry (§4), Canonical storage path (§5), Per-type MIRROR rules (§6), DERIVE policy contracts (§7) |
| 1.2 | 2026-01-04 | ~~Added stepped hull types~~ **REVERTED** — wrong mental model |
| 2.0 | 2026-01-04 | **FUNDAMENTAL CORRECTION**: Kernel knows geometry, not design concepts. Replaced enumerated "hull.step" types with universal geometric primitives (`geometry.discontinuity`, `geometry.flow_path`, `geometry.opening`). Added §0 (Fundamental Principle). "Stepped hull" is not a resource — it's a composition of primitives. |
| 3.0 | 2026-01-04 | **MULTI-BODY & SURFACE PRIMITIVES**: Added `geometry.body` for multi-hull vessels (catamarans, trimarans). Added `geometry.section` for cross-section definition. Added `geometry.surface` for NURBS/lofted surfaces. Added `geometry.attachment` for body connections. Added `LOFT` and `OFFSET` operations. Added §4.4 (Multi-Body Model), §4.5 (Surface Definition), §15 (Codebase Implementation Plan). Updated primitive table and examples. Kernel now supports any hull configuration through body/section/surface composition — no "catamaran" type needed. |
| 3.1 | 2026-01-04 | **NO SECOND GEOMETRY ENGINE CONTRACT**: Added core invariants "No second geometry engine" and "One canonical geometry model". Added §0.1 (Canonical Geometry Model) documenting existing classes (`HullSection`, `NURBSSurface`, `HullGeometry`) that language compiles INTO. Added `to_hull_section()` and `to_nurbs_surface()` bridge methods. Added §15.8 (Downstream Pipeline Contract) showing how language-generated geometry feeds existing tessellation/hydrostatics/export. Added §15.9 (Determinism Requirements). Added validation gates for surfaces. Strengthened "no new geometry classes consumed by downstream" principle. |
| 3.2 | 2026-01-05 | **APPENDIX ALIGNMENT**: Updated §17 (JSON Program Format) to use ONLY `geometry.*` primitives instead of deprecated `hull.*` types. Example now demonstrates catamaran construction with `geometry.body`, `geometry.section`, `geometry.surface`, `geometry.discontinuity`, and `geometry.opening`. Added explicit note about deprecated types. |
| 4.0 | 2026-01-05 | **ENGINEER CREATIVITY AMPLIFIER**: Added "What MAGNET Is" section at top, establishing that MAGNET is an engineer creativity amplifier, not autonomous design. Added "Engineer is in the loop" to core invariants. Added "Core Equation" (creativity × feedback × no limits). Architecture now shows engineer at both ends of the loop. Aligned with `MAGNET_Failure_Modes_And_Mitigations.md` v4.0. |
| 4.1 | 2026-01-05 | Added reference to `MAGNET_Audit_Prompts.md` in Related Documents. |
| 4.2 | 2026-01-05 | Aligned with completed codebase audit. Added verification of canonical geometry model locations. |
| 4.3 | 2026-01-05 | Added references to new implementation documents: Agent Prompt Spec, API Contract, Test Plan, Migration Spec. |
| 4.4 | 2026-01-05 | **CRITICAL ENUM REMOVAL**: Removed `hull_type` from DERIVE policies — `LBRatioPolicy` now takes `target_lb_ratio` as agent input. Removed `HullType.CATAMARAN` dispatch from `HullGenerator` — multi-body generation is now purely body-count based. Deleted `_create_legacy_catamaran_bodies()`. Added reference to `MAGNET_Physics_Gaps_And_Solutions.md`. |
