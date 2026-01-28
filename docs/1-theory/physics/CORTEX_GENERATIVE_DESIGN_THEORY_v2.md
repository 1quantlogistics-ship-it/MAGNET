# CORTEX: Generative Design Theory v2.0

**Subtitle:** How LLMs Create Complete Physical Artifacts Through Recursive Decomposition

**Version:** 2.0
**Status:** Working Theory
**Author:** Ben / MAGNET Project
**Date:** January 2026
**Changelog:** Incorporates architectural critique (Observable Discovery, Inter-System Negotiation, Compound Operations, Validation Tiers, Manufacturability)

---

## First-Principles Summary

Generative design is constraint satisfaction through recursive decomposition.

- **High-level intent decomposes into sub-problems**
- **Sub-problems decompose until you reach placeable atoms**
- **Atoms are placed, validated, and committed**
- **Validation propagates back up the hierarchy**
- **NEW: Systems must negotiate for shared space**
- **NEW: Intent and constraints can be coordinated, not just sequential**

The LLM is the architect — it reasons about what and why.
The kernel is the engineer — it computes how and validates.
The loop continues until the design is complete and valid.

**This is not different from agentic web design. It's the same pattern in 3D with physics.**

---

## Part I: What Is Design?

### 1.1 The Universal Design Process

Every design problem follows the same structure:

```
Intent
  → Decompose into sub-problems
    → Decompose further
      → Until you hit atoms you can place
        → Place atoms
        → Validate locally
      → Validate sub-assembly
    → Validate system
  → Validate whole
Complete
```

This is true for:
- Web pages (intent → sections → components → elements)
- Vessels (intent → systems → components → fittings)
- Buildings (intent → floors → rooms → elements)
- Circuits (intent → subsystems → components → traces)
- Molecules (intent → scaffolds → fragments → atoms)

### 1.2 Web Design as Existence Proof

Web design agents work today. They:

```
"Build me a landing page for a SaaS product"
    ↓
Decompose: Hero, features, pricing, testimonials, CTA, footer
    ↓
Each section: What components? What layout?
    ↓
Hero: Headline (48px, bold), subhead (18px), image (16:9), button (primary)
    ↓
Place elements, apply styles
    ↓
Validate: Contrast ok? Hierarchy clear? Mobile works?
    ↓
Iterate until done
```

**Why this works:**
1. Atoms are well-defined (div, span, img, button)
2. Composition rules are known (flexbox, grid)
3. Validation is fast (render and check)
4. Undo is trivial (regenerate)

### 1.3 Physical Design Has the Same Structure

```
"Build me a 72-foot sportfisher, 400nm range, 6 passengers"
    ↓
Decompose: Hull, propulsion, fuel, electrical, accommodations
    ↓
Fuel system: What components? What routing?
    ↓
Components: Tank (400gal, frame 12-18), fill (gunwale, station 15), filter, lines
    ↓
Place components, route connections
    ↓
Validate: Capacity ok? No air locks? Accessible? No clashes?
    ↓
Iterate until done
```

**Same pattern. Different atoms. Different validation.**

### 1.4 What's Different About Physical Design (UPDATED)

Physical design adds complexity that web design doesn't have:

| Challenge | Web Design | Physical Design |
|-----------|------------|-----------------|
| **Space is shared** | Z-index handles overlap | Systems compete for volume |
| **Constraints couple** | CSS is mostly independent | Beam affects stability, stability affects weight, weight affects beam |
| **Validation is slow** | Render in ms | Physics in seconds |
| **Failure is permanent** | Refresh the page | Ship sinks |
| **Manufacturing matters** | Deploy to server | Cut steel, weld, assemble |

**NEW insight:** These challenges require architectural solutions, not just better prompts:

1. **Shared space** → Spatial claim registry + conflict resolver
2. **Coupled constraints** → Compound intent (COORDINATE verb)
3. **Slow validation** → Structured queries parallel to vision
4. **Permanent failure** → Three-tier validation (hard gate / soft gate / grade)
5. **Manufacturing** → Realizability validators distinct from design validity

---

## Part II: The Recursive Agent Architecture

### 2.1 Design Levels

Physical design naturally stratifies into levels:

| Level | Name | Input | Output | Validates |
|-------|------|-------|--------|-----------|
| 0 | **Mission** | User intent, requirements | System requirements, space allocation | Feasibility |
| 1 | **Systems** | Requirements from L0 | System specs, major component zones | Systems don't conflict |
| 2 | **Components** | System specs from L1 | Component instances, positions | Clearances, access, support |
| 3 | **Routing** | Components from L2 | Paths, fittings, penetrations | No collisions, valid geometry |
| 4 | **Details** | Routes from L3 | Hangers, supports, labels, panels | Installable, serviceable |

### 2.2 Level Interactions (UPDATED)

```
┌─────────────────────────────────────────────────────────────────┐
│                         LEVEL 0: MISSION                         │
│  "72-foot sportfisher, 400nm range, 6 passengers, 30kt cruise"  │
│                                                                  │
│  Outputs:                                                        │
│  - Fuel requirement: ~800 gal                                    │
│  - Accommodation: 3 cabins                                       │
│  - Engine: ~1500hp total                                         │
│  - Space budget: {engine_room: 15%, tanks: 12%, accom: 40%...}  │
│  - Observable Schema: [NEW] Valid queries for this vessel       │
│  - Character Signature: [NEW] Baseline for drift detection      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        LEVEL 1: SYSTEMS                          │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │   Hull   │ │Propulsion│ │   Fuel   │ │Electrical│ ...       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                  │
│  Each system receives:                                           │
│  - Space allocation                                              │
│  - Performance requirements                                      │
│  - Interface points to other systems                            │
│                                                                  │
│  Each system outputs:                                            │
│  - Component list with rough positions                          │
│  - Connection requirements                                       │
│  - Spatial claims [NEW] for conflict detection                  │
│  - Weight and power budgets                                      │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ CONFLICT RESOLUTION [NEW]                                │    │
│  │ After all systems submit spatial claims:                 │    │
│  │ - Detect overlaps                                        │    │
│  │ - Prioritize by criticality                              │    │
│  │ - Relocate or escalate                                   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      LEVEL 2: COMPONENTS                         │
│                                                                  │
│  Fuel System Components:                                         │
│  - Tank 1: 400gal, frames 12-18, centerline                     │
│  - Tank 2: 400gal, frames 12-18, centerline (split)             │
│  - Fill port (stbd): gunwale, station 15                        │
│  - Fill port (port): gunwale, station 15                        │
│  - Vent fitting: hull side, above WL                            │
│  - Fuel filter: engine room, accessible                         │
│  - Fuel shutoff: engine room, near tanks                        │
│                                                                  │
│  Validates: Clearances, structural support, access              │
│  NEW: Manufacturability pre-check (can these parts be made?)    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       LEVEL 3: ROUTING                           │
│                                                                  │
│  Fuel lines:                                                     │
│  - Fill (stbd) → Tank 1: 1.5" ID, 2.3m, 3 fittings             │
│  - Fill (port) → Tank 2: 1.5" ID, 2.1m, 2 fittings             │
│  - Tank 1 → Filter: 0.5" ID, 3.7m, anti-siphon valve           │
│  - Filter → Engine 1: 0.5" ID, 1.2m                             │
│  - Vent loop: 0.75" ID, rises 300mm above tank top             │
│                                                                  │
│  Validates: No collisions, bend radii, proper slope             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        LEVEL 4: DETAILS                          │
│                                                                  │
│  - Hanger at frame 14 (fuel supply)                             │
│  - Hanger at frame 16 (fuel supply)                             │
│  - P-clamp at filter mount                                       │
│  - Label: "FUEL SUPPLY - GASOLINE"                              │
│  - Access panel: 12"x12" at filter location                     │
│                                                                  │
│  Validates: Installable sequence, serviceable, labeled          │
│  NEW: Assembly sequence validity (can this be built?)           │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Validation Propagation (UPDATED)

Validation flows both down and up:

**Downward (constraints):**
- Level 0 constrains Level 1 (space budgets, weight limits)
- Level 1 constrains Level 2 (component zones, interface points)
- Level 2 constrains Level 3 (endpoints, keep-out zones)
- Level 3 constrains Level 4 (support points, access requirements)

**Upward (verification):**
- Level 4 confirms: "This is installable"
- Level 3 confirms: "Routes don't clash"
- Level 2 confirms: "Components fit and are accessible"
- Level 1 confirms: "System meets requirements"
- Level 0 confirms: "Mission achieved"

**NEW: Validation Tiers**

Not all validation failures are equal:

| Tier | Name | Example | Consequence |
|------|------|---------|-------------|
| **Hard Gate** | Design invalid | Doesn't float | Blocks all progress |
| **Soft Gate** | Design valid, phase blocked | Can't manufacture | Blocks production, allows iteration |
| **Grade** | Informational | Suboptimal efficiency | Never blocks, informs |

### 2.4 Iteration Within and Across Levels (UPDATED)

When validation fails, iteration occurs:

**Within level:** Adjust placement, try alternative routing

**Across levels:** Escalate constraint violation, request more space/budget

**NEW: Coordinated iteration**

When constraints are coupled, simple iteration fails:

```
PROBLEM: "Increase beam while maintaining GM ≥ 0.5m"

NAIVE APPROACH (fails):
  ADJUST beam BY +0.2m    → GM drops to 0.4m
  ADJUST draft BY +0.1m   → GM back to 0.5m
  ADJUST beam BY +0.1m    → GM drops to 0.45m
  ... oscillates forever

COORDINATED APPROACH (succeeds):
  COORDINATE {
    TARGET beam = 5.5m
    MAINTAIN gm >= 0.5m
    ALLOW ADJUST draft, ballast_position
  }
  → Kernel runs optimizer
  → Returns: beam=5.5m, draft=1.3m, ballast_position=adjusted
  → Or: "Infeasible: cannot achieve beam=5.5m with gm>=0.5m"
```

### 2.5 Observable Discovery (NEW)

**The Problem:** The theory document (v1.0) claimed observables are an "open vocabulary" — new components automatically create new observables. But the LLM needs to know what observables exist.

**The Solution:** Observable Schema

When geometry is imported or changes significantly:
1. Kernel generates `ObservableSchema` from artifact graph
2. Schema lists: component types, component instances, metric types, sample queries
3. Schema is passed to LLM as structured context
4. LLM can only query observables that exist in schema

```python
# Observable Schema (passed to LLM)
{
  "component_types": ["fuel_tank", "fuel_fill", "fuel_filter", ...],
  "components_by_type": {
    "fuel_tank": ["tank_001", "tank_002"],
    "fuel_fill": ["fill_stbd", "fill_port"],
    ...
  },
  "metric_definitions": [
    {"name": "distance", "arity": 2, "unit": "m"},
    {"name": "clearance", "arity": 2, "unit": "m"},
    {"name": "volume", "arity": 1, "unit": "m³"},
    ...
  ],
  "sample_queries": [
    "distance:tank_001:tank_002",
    "clearance:tank_001:bulkhead_aft",
    "volume:tank_001",
    ...
  ]
}
```

**Key insight:** The vocabulary is "open" at the kernel level (can compute any metric for any component), but "discoverable" at the LLM level (LLM knows what exists).

---

## Part III: The LLM's Role at Each Level

### 3.1 What LLMs Are Good At

| Capability | Application in Design |
|------------|----------------------|
| **Pattern recognition** | "This looks like a center console layout" |
| **Requirements interpretation** | "400nm range at 30kt means ~800gal fuel" |
| **Trade-off reasoning** | "More tankage means less accommodation" |
| **Constraint specification** | "Filter must be accessible and before engine" |
| **Review and critique** | "This routing passes too close to exhaust" |
| **Natural language interface** | "Move the fill port closer to the dock side" |
| **Conflict prioritization** | "Fuel system is more constrained, move HVAC" |

### 3.2 What LLMs Cannot Do

| Limitation | Implication |
|------------|-------------|
| **3D spatial reasoning from coordinates** | Cannot generate valid paths from numbers |
| **Precise geometric computation** | Cannot compute clearances, volumes, angles |
| **Collision detection** | Cannot verify non-intersection |
| **Physics simulation** | Cannot verify flow, structural, thermal |
| **Optimization** | Cannot search large solution spaces efficiently |
| **Manufacturing assessment** | Cannot determine if geometry is buildable |

### 3.3 The Division of Labor (UPDATED)

| Task | LLM | Kernel |
|------|-----|--------|
| Interpret requirements | ✅ | |
| Decompose into systems | ✅ | |
| Select patterns/templates | ✅ | |
| Specify constraints | ✅ | |
| Generate placement | | ✅ (constraint solver) |
| Generate routing | | ✅ (pathfinding) |
| Validate geometry | | ✅ (clash detection) |
| Validate physics | | ✅ (domain solvers) |
| Validate manufacturability [NEW] | | ✅ (realizability check) |
| Review results | ✅ (via vision) | |
| Accept/reject/modify | ✅ | |
| Explain decisions | ✅ | |
| Prioritize conflicts [NEW] | ✅ | |
| Execute coordinated intent [NEW] | | ✅ (optimizer) |

---

## Part IV: The Kernel's Algorithms

The kernel provides the computational capabilities the LLM lacks.

### 4.1 Space Allocation (Level 0-1)

**Problem:** Divide available volume among competing systems

**Algorithms:**
- Bin packing (3D)
- Constraint satisfaction (CSP)
- Linear programming (for optimization)

**LLM role:** Specify requirements, priorities, accept/reject allocation

### 4.2 Component Placement (Level 2)

**Problem:** Position components within allocated zones

**Algorithms:**
- Constraint satisfaction
- Physics simulation (for settling)
- Genetic algorithms (for optimization)

**LLM role:** Specify components, constraints, preferences

### 4.3 Routing (Level 3)

**Problem:** Connect components with valid paths

**Algorithms:**
- A* (grid-based pathfinding)
- RRT/RRT* (sampling-based, handles complex constraints)
- PRM (probabilistic roadmap, good for repeated queries)
- Visibility graphs (for 2.5D routing)

**LLM role:** Specify endpoints, preferences, review results

### 4.4 Clash Detection (Continuous)

**Problem:** Ensure no geometry intersects

**Algorithms:**
- Bounding Volume Hierarchy (BVH)
- Spatial hashing
- GJK/EPA (for precise collision)

**LLM role:** None — kernel does this automatically

### 4.5 Conflict Resolution (NEW)

**Problem:** Multiple systems compete for the same space

**Architecture:**

```python
class ConflictResolver:
    def register_claim(self, claim: SpatialClaim) -> List[Conflict]:
        """
        When a system places components, register spatial claim.
        Returns any conflicts with existing claims.
        """

    def resolve_conflicts(self) -> ResolutionResult:
        """
        Attempt automatic resolution:
        1. Sort conflicts by severity
        2. Move lower-priority system if flexible
        3. Stack vertically if possible
        4. Escalate if unresolvable
        """
```

**LLM role:** Prioritize systems, choose resolution strategy when escalated

### 4.6 Coordinated Intent Execution (NEW)

**Problem:** Achieve a target while maintaining constraints

**Algorithm:**

```python
def execute_coordinate(intent: CoordinatedIntent) -> Result:
    """
    Find values for allowed variables that:
    - Achieve target observables
    - Maintain constraint observables
    - Minimize/maximize preference observables

    Uses gradient descent with constraint projection.
    Reports infeasibility if no solution exists.
    """
```

**LLM role:** Specify targets, constraints, and allowed adjustments

### 4.7 Manufacturability Validation (NEW)

**Problem:** Geometry may be valid but unbuildable

**Checks:**

| Check | What It Validates | Blocks |
|-------|-------------------|--------|
| Minimum thickness | Plates can be formed | Production export |
| Bend radius | Corners can be bent | Production export |
| Weld accessibility | Welds can be made | Production export |
| Panel developability | Surfaces can be cut from flat sheet | Nesting |
| Assembly sequence | Parts can be installed in order | Production planning |

**LLM role:** None — kernel validates automatically

---

## Part V: Domain Libraries

### 5.1 The Pattern Library Concept

LLMs don't invent from scratch. They select and instantiate patterns.

**Web design analogy:**
- Component libraries (shadcn, Radix)
- Layout patterns (hero, grid, sidebar)
- Style systems (Tailwind)

**Physical design equivalent:**
- System templates
- Routing rules
- Component catalogs
- Assembly patterns

### 5.2 Pattern Versioning (NEW)

**The Problem:** Regulations change. ABYC H-33 2024 differs from ABYC H-33 2020. Patterns must track which regulatory version they implement.

**The Solution:**

```python
@dataclass
class SystemPattern:
    id: str
    name: str

    # Version tracking
    version: str = "1.0.0"
    version_date: str  # When this version was created

    # Regulatory references
    regulatory_refs: List[str]  # ["ABYC H-33:2024", "CFR 183.510"]

    # Deprecation
    deprecated: bool = False
    deprecated_reason: Optional[str] = None
    replacement_pattern_id: Optional[str] = None
```

**Registry capabilities:**

```python
# When regulation changes
affected_designs = registry.get_designs_using_regulatory_ref("ABYC H-33:2020")
# Returns list of design IDs that need review

# When pattern is deprecated
registry.deprecate(
    pattern_id="fuel_single_gasoline_v1",
    reason="ABYC H-33:2024 requires additional vent loop height",
    replacement_id="fuel_single_gasoline_v2"
)
```

### 5.3 System Templates

```python
FUEL_SYSTEM_TEMPLATES = {
    "single_engine_gasoline": {
        "description": "Simple gasoline system for single outboard/sterndrive",
        "version": "2.0.0",
        "regulatory_refs": ["ABYC H-33:2024"],
        "components": [
            {"type": "fuel_tank", "quantity": 1},
            {"type": "fuel_fill", "quantity": 1},
            {"type": "fuel_vent", "quantity": 1},
            {"type": "fuel_pickup", "quantity": 1},
            {"type": "water_separator", "quantity": 1},
            {"type": "fuel_line", "subtype": "supply"},
            {"type": "fuel_line", "subtype": "return"},
        ],
        "topology": """
            fill --> tank
            tank --> pickup --> water_sep --> engine
            engine --> return --> tank
            tank --> vent --> hull_fitting
        """,
        "rules": [
            "tank_below_fill",
            "vent_highest_point",
            "antisiphon_required",
            "return_above_pickup",
            "vent_loop_300mm_above_tank",  # NEW in 2024
        ]
    },
}
```

---

## Part VI: The Agent Loop for Generative Design

### 6.1 Tools for Generative Design (UPDATED)

```python
GENERATIVE_DESIGN_TOOLS = [
    # Level 0-1: Mission & Systems
    {
        "name": "decompose_requirements",
        "description": "Break down mission into system requirements",
    },
    {
        "name": "allocate_spaces",
        "description": "Allocate zones for systems",
    },

    # Level 2: Components
    {
        "name": "select_template",
        "description": "Select a system template",
    },
    {
        "name": "request_placement",
        "description": "Place a component in the design",
    },

    # Level 3: Routing
    {
        "name": "request_routing",
        "description": "Route a connection between components",
    },

    # Level 4: Details
    {
        "name": "add_supports",
        "description": "Add hangers/supports to routes",
    },

    # Vision
    {
        "name": "request_view",
        "description": "Render current state",
    },

    # Structured queries (NEW - parallel to vision)
    {
        "name": "query_observable",
        "description": "Query a specific observable value",
    },
    {
        "name": "query_collisions",
        "description": "Get list of colliding components",
    },
    {
        "name": "query_clearance_map",
        "description": "Get clearances in all directions for a component",
    },

    # Conflict resolution (NEW)
    {
        "name": "request_conflict_resolution",
        "description": "Request resolution of a spatial conflict",
        "inputs": ["conflict_id", "preferred_resolution"],
    },

    # Coordinated intent (NEW)
    {
        "name": "execute_coordinate",
        "description": "Execute a coordinated multi-observable operation",
        "inputs": ["targets", "maintains", "allow_adjust"],
    },

    # Validation
    {
        "name": "validate_system",
        "description": "Run full validation on a system",
    },
    {
        "name": "check_manufacturability",
        "description": "Check if design can be manufactured",  # NEW
    },

    # Commit
    {
        "name": "commit_design",
        "description": "Commit current state to design history",
    },
]
```

### 6.2 The Generative Loop (UPDATED)

```python
def generative_design_agent(
    mission: str,
    hull_geometry: ArtifactGraph,
    max_iterations: int = 100
) -> DesignResult:

    # NEW: Generate observable schema
    schema = ObservableSchemaGenerator(hull_geometry).generate()

    # NEW: Capture initial character signature
    character_analyzer = CharacterAnalyzer(kernel)
    initial_character = character_analyzer.extract_signature(hull_geometry)

    messages = [{"role": "user", "content": f"""
Design a complete vessel based on this mission:
{mission}

OBSERVABLE SCHEMA:
{schema.to_llm_summary()}

The hull geometry is provided. Design all systems...
"""}]

    for iteration in range(max_iterations):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            system=GENERATIVE_DESIGN_SYSTEM_PROMPT,
            tools=GENERATIVE_DESIGN_TOOLS,
            messages=messages
        )

        if response.stop_reason == "tool_use":
            results = execute_tools(response.tool_calls, hull_geometry)
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": results})

        elif response.stop_reason == "end_turn":
            if "DESIGN COMPLETE" in response.content[0].text:
                # NEW: Check character drift
                final_character = character_analyzer.extract_signature(hull_geometry)
                drift = character_analyzer.compute_drift(initial_character, final_character)

                if drift > 0.05:
                    return DesignResult(
                        status="character_drift_warning",
                        drift=drift,
                        partial=hull_geometry
                    )

                return extract_design_result(hull_geometry)

    return DesignResult(status="max_iterations", partial=hull_geometry)
```

---

## Part VII: Handling Complexity

### 7.1 Hierarchical Scoping

Large artifacts (cruise ships, buildings) have too many components to show at once.

**Solution:** Hierarchical scope in all queries and views.

### 7.2 Parallel System Design (UPDATED)

Systems can be designed in parallel if they don't conflict:

```
Phase 1 (sequential): Space allocation - establishes zones
Phase 2 (parallel):
  - Fuel system design (in fuel zone)
  - Electrical design (throughout, but non-conflicting)
  - Fresh water design (in utility zones)
Phase 3 (sequential): Integration - resolve conflicts [CRITICAL]
Phase 4 (parallel): Details for each system
```

**NEW: Phase 3 is not optional**

The original theory assumed Phase 3 "just works." It doesn't. Explicit conflict resolution is required:

1. Each system submits spatial claims
2. Kernel detects overlaps
3. Conflicts are surfaced to LLM with options
4. LLM chooses resolution (relocate, stack, escalate)
5. Kernel executes resolution
6. Repeat until no conflicts remain

### 7.3 Conflict Resolution (NEW)

When systems conflict:

```
Kernel detects: "Fuel line clashes with HVAC duct at frame 12"

Conflict surfaced to LLM:
{
  "conflict_id": "conflict_042",
  "type": "spatial_overlap",
  "system_a": "fuel_supply",
  "system_b": "hvac_main",
  "zone": "engine_room",
  "options": [
    "Relocate fuel (lower priority)",
    "Relocate HVAC (higher priority but flexible)",
    "Stack vertically (+30cm offset)",
    "Escalate: request zone expansion"
  ]
}

LLM decides:
"request_conflict_resolution": {
  "conflict_id": "conflict_042",
  "preferred_resolution": "stack"
}

Kernel executes:
- ADJUST position:z AT hvac_main_duct_7 BY +0.30m
- Revalidate clearances
- Return result
```

### 7.4 Iteration Bounds

Prevent infinite loops:

```python
ITERATION_LIMITS = {
    "placement_attempts": 5,      # Tries to place one component
    "routing_attempts": 3,        # Tries to route one connection
    "system_iterations": 10,      # Total iterations on one system
    "integration_passes": 3,      # Cross-system conflict resolution
    "coordinate_iterations": 20,  # NEW: Optimizer iterations
}
```

---

## Part VIII: Validation Throughout (UPDATED)

### 8.1 Three-Tier Validation Model

| Tier | Gate Type | What It Validates | Consequence of Failure |
|------|-----------|-------------------|------------------------|
| 1 | **Hard Gate** | Design validity | Blocks all progress |
| 2 | **Soft Gate** | Phase readiness | Blocks specific phases |
| 3 | **Grade** | Quality metrics | Informs, never blocks |

### 8.2 Hard Gates (Block All Progress)

| Validator | What It Checks | Example Failure |
|-----------|---------------|-----------------|
| Hydrostatics | Vessel floats | Displacement ≤ 0 |
| Geometry Manifold | Mesh is watertight | Holes in hull |
| Physics | No impossible states | Negative mass |

### 8.3 Soft Gates (Block Specific Phases)

| Validator | What It Checks | Blocked Phases |
|-----------|---------------|----------------|
| Structural | Safety factor ≥ 1.5 | production_export, bom |
| Stability | IMO criteria met | regulatory_submission |
| Manufacturability | Geometry buildable | production_export, nesting |
| Assembly | Valid build sequence | production_planning |

### 8.4 Grades (Never Block)

| Grade | What It Measures | Range |
|-------|------------------|-------|
| Efficiency | Resistance / displacement | 0-1 |
| Accessibility | Service access score | 0-1 |
| Aesthetics | Proportion harmony | 0-1 |
| Optimization | Pareto optimality | 0-1 |

### 8.5 Validation Pipeline (UPDATED)

```python
def full_validation(design: ArtifactGraph) -> ValidationReport:
    report = ValidationReport()

    # Tier 1: Hard gates (fast, always run)
    for gate in HARD_GATES:
        result = gate.validate(design)
        report.add(result)
        if not result.passed:
            return report  # Stop early - design invalid

    # Tier 2: Soft gates
    for gate in SOFT_GATES:
        result = gate.validate(design)
        report.add(result)
        # Don't stop - record blocked phases

    # Tier 3: Grades
    for grade in GRADES:
        result = grade.evaluate(design)
        report.add(result)

    return report

# Usage
report = full_validation(design)

if not report.hard_gates_passed:
    return "Design invalid - cannot proceed"

if "production_export" in report.blocked_phases:
    return "Can iterate design, cannot export to production"

print(f"Design valid. Grades: {report.grade_summary}")
```

---

## Part IX: Character Preservation (NEW)

### 9.1 The Problem

Iterative refinement can drift from original intent:

```
Initial: "Viking-inspired, aggressive bow flare"
After 10 iterations: Generic displacement hull
```

This happens because:
- Each change is locally reasonable
- No global constraint preserves "character"
- LLM doesn't track cumulative drift

### 9.2 The Solution: Character Signatures

Capture character-defining observables at first valid state:

```python
CharacterSignature = {
    "sheer_curvature": 0.003,      # Second derivative of sheer
    "entry_half_angle": 22.5,      # Bow sharpness
    "bow_flare_deg": 18.0,         # Flare at bow
    "deadrise_progression": "increasing_aft",
    "chine_count": 2,              # Structural - high weight
    ...
}
```

Compare against current state after each level:

```python
drift = character_analyzer.compute_drift(initial_signature, current_signature)

if drift > 0.05:  # 5% threshold
    warn("Character drift detected. Design may have strayed from original intent.")
```

### 9.3 Character Weights

Not all features are equally important:

| Feature | Weight | Rationale |
|---------|--------|-----------|
| Chine count | 3.0 | Topology change = major drift |
| Entry angle | 2.0 | Defines "look" of bow |
| Sheer curvature | 2.0 | Highly visible profile |
| Deadrise | 1.0 | Performance, less visible |
| Bilge radius | 1.0 | Subtle aesthetic |

---

## Part X: The Comparison (UPDATED)

### 10.1 Web Design vs Physical Design

| Aspect | Web Design Agent | Physical Design Agent |
|--------|------------------|----------------------|
| **Atoms** | DOM elements | Physical components |
| **Composition** | CSS layout | 3D spatial + routing |
| **Validation** | Render + screenshot | Physics + clash detection |
| **Iteration speed** | Milliseconds | Seconds |
| **Failure mode** | Ugly but functional | Non-functional or dangerous |
| **Libraries** | shadcn, Tailwind | System templates, routing rules |
| **LLM strength** | Aesthetic judgment | System architecture |
| **Kernel strength** | DOM manipulation | Pathfinding, physics |
| **Space conflicts** | Z-index | Spatial claim negotiation [NEW] |
| **Coupled constraints** | Rare | Common [NEW] |
| **Manufacturing** | N/A (deploy) | Critical [NEW] |

### 10.2 What Makes Physical Design Harder

1. **3D pathfinding with constraints** — Not a capability LLMs have
2. **Physics validation** — Requires domain solvers
3. **Manufacturing constraints** — Bend radii, weld access, install sequence
4. **Regulatory compliance** — Complex rule sets
5. **Consequence severity** — Bad CSS looks ugly; bad piping sinks boats
6. **Space is shared** — Systems compete for the same volume [NEW]
7. **Constraints couple** — Changing one affects others [NEW]

### 10.3 What Makes It Tractable

1. **Decomposition works** — Same pattern as web design
2. **Patterns exist** — System templates, routing rules
3. **Validation is computable** — Algorithms exist
4. **LLM strengths apply** — Requirements interpretation, trade-offs, review
5. **Kernel handles the hard parts** — Pathfinding, physics, optimization
6. **Conflict resolution is algorithmic** — LLM chooses, kernel executes [NEW]
7. **Coupled constraints have optimizers** — COORDINATE verb [NEW]

---

## Part XI: Implementation Roadmap (UPDATED)

### Phase 1: Observable Schema + Basic Loop ← CURRENT
- Observable schema generation from artifact graph
- Schema passed to LLM context
- Query validation against schema
- Basic agent loop with tools
- **Proves:** LLM can query valid observables

### Phase 2: Conflict Resolution
- Spatial claim registry
- Conflict detection algorithm
- Resolution strategies (relocate, stack, escalate)
- LLM tool for conflict resolution
- **Proves:** Multiple systems can coexist

### Phase 3: Coordinated Intent
- COORDINATE verb implementation
- Optimizer integration
- Feasibility detection and reporting
- Constraint visualization
- **Proves:** Coupled constraints can be handled

### Phase 4: Three-Tier Validation
- Refactor validators with gate_type
- Soft gate phase blocking
- Manufacturability validators
- Validation report UI
- **Proves:** Design can proceed to production safely

### Phase 5: Character Preservation
- Signature extraction
- Drift computation with weighted features
- Drift warnings in UI
- Character lock feature (preserve specific features)
- **Proves:** Designs maintain intent through iteration

### Phase 6: Pattern Versioning
- Version tracking in registry
- Deprecation workflow
- Affected design queries
- Regulatory update alerts
- **Proves:** Regulatory compliance is maintainable

### Phase 7: Full Vessel
- All systems including HVAC, accommodations
- Hierarchical scoping for complexity
- Full regulatory validation
- **Proves:** Complete designs possible

### Phase 8: Generalization
- Abstract system templates
- Pluggable validators
- Other domains (buildings, appliances)
- **Proves:** Pattern is general

---

## Conclusion (UPDATED)

Generative design by LLMs is not impossible. It's the same pattern as web design:

**Decompose → Pattern-match → Instantiate → Validate → Iterate**

The differences are:
- Different atoms (components vs DOM)
- Different composition (3D routing vs CSS)
- Different validation (physics vs render)
- **Shared space requires negotiation** [NEW]
- **Coupled constraints require coordination** [NEW]
- **Manufacturing requires realizability checking** [NEW]

But the agent architecture is identical:
- LLM reasons about **what** and **why**
- Kernel computes **how** and validates
- Vision + structured queries close the loop
- Libraries provide patterns
- Iteration handles errors
- **Conflict resolver handles competition** [NEW]
- **Optimizer handles coordination** [NEW]

**You're not doing something new. You're doing web design in 3D with physics and manufacturing.**

The kernel needs:
- Pathfinding algorithms
- Clash detection
- Domain solvers
- Pattern libraries
- Conflict resolver [NEW]
- Coordinated intent optimizer [NEW]
- Manufacturability validators [NEW]

The LLM needs:
- Vision (to see results)
- Structured queries (to get facts without rendering)
- Tools (to request operations)
- Domain knowledge (in prompts and libraries)
- Observable schema (to know what can be queried)
- Conflict resolution tools (to handle competition)

When you have both, you can generate complete physical artifacts.

---

*End of document.*
