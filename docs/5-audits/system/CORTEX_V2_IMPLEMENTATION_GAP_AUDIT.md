# CORTEX v2 Implementation Gap Audit (vs MAGNETV1)

> **Superseded:** This content is now consolidated into `CORTEX_V2_IMPLEMENTATION_GUIDE.md` (project root).
> Keep this file only as historical context / long-form background.

**Date:** 2026-01-21  
**Scope:** What is missing / must change to achieve the “Claude builds a website” equivalent for vessels: **create-from-nothing** + **edit-existing** with the same loop (tools → kernel → vision → validation → iterate).

This audit is grounded in:
- `CORTEX_GENERATIVE_DESIGN_IMPLEMENTATION_v2.md` (spec)
- Existing MAGNET architecture and contracts (see `docs/0-architecture/system/DETAILED_ARCHITECTURE_DIAGRAM.md`)
- MAGNET North Star principles (`docs/1-theory/physics/MAGNET_North_Star.md`)

---

## Executive Summary

### What you already have in MAGNET (high leverage)
- **A persistent, versioned canonical state** (`StateManager`, DesignStore) and atomic execution semantics.
- **A deterministic execution firewall** (Intent→Action protocol, ActionPlanValidator/Executor).
- **A design-language geometry pipeline** (stdlib parser/compiler + `geometry.*` primitives) that already supports **EDIT vs REWRITE gating** (see `deployment/spiral_endpoints.py`).
- **A phase orchestrator with gate behavior** (`kernel/conductor.py`) and invalidation wiring.
- **A kernel-owned observable registry + measurement code** (`kernel/geometry_observables.py`, `agents/geometry_observables.py`), plus “thinking pass” validation binding.
- **Routing infrastructure** (`magnet/routing/*`) with zone management, topology, and an agent-oriented routing pipeline.
- **Some systems generators/validators** (e.g. `systems/fuel/generator.py`, `systems/fuel/validator.py`) that compute system sizing and store derived values in state.

### What’s missing (blocking the “real target”)
The CORTEX spec assumes an `ArtifactGraph` with components, placements, routes, and conflicts. MAGNET currently has:
- **Hull geometry as `geometry.*` resources** (great)
- But **systems are not represented as editable geometry artifacts** (they’re mostly computed numbers + validators).

So the hard gap is:
> You need a **unified artifact layer** where “fuel tanks / lines / generator / duct runs” are first-class, placeable/routable, visible in WebGL, and causally tied into validation + invalidation + edit operations.

---

## 1) Major Mismatch: `ArtifactGraph` (CORTEX) vs `DesignState/resources` (MAGNET)

### CORTEX expectation
`ArtifactGraph` stores:
- components (instances by type)
- zones / bounds
- placement state
- routing state
- queryable observables tied to those components

### MAGNET reality
MAGNET has a strong SSOT:
- `DesignState` + `StateManager`
- `resources` dict holding `geometry.*` primitives (already graph-like)

### What must change
- **Do not build a parallel “ArtifactGraph” SSOT.** It will fork truth from `DesignState`.
- Instead, implement an **ArtifactGraph View/Adapter** over `DesignState.resources`:
  - `magnet/artifacts/graph_view.py` (new)
  - Responsibilities:
    - index resources by `_type`, `body_id`, `system_id`, etc.
    - expose “component instances” (for LLM + tooling)
    - provide lightweight spatial proxies (AABB/OBB) for conflict detection
    - provide component→route connectivity (IDs + endpoints)

**Acceptance criteria:**
- Single source of truth remains `StateManager`.
- All “graph” operations are deterministic projections from state (no duplicate storage).

---

## 2) Dual-Mode Agent: “Create from nothing” exists for hull; not for full vessel

### What exists today
- **Create hull from nothing**:
  - Hull synthesis hook in `kernel/conductor.py` (program path + legacy synthesis)
  - Spiral chat endpoints detect existing hull shell and enforce EDIT vs REWRITE boundaries (`deployment/spiral_endpoints.py`)
- **Edit hull**:
  - design language supports ADJUST/TARGET and is gated in edit mode
  - observables/verification infrastructure exists

### What’s missing
- **Create full vessel** (systems + placement + routing + validation) is not wired:
  - Fuel generator produces dataclasses and writes a few scalar results (`fuel.total_capacity_m3`, etc.)
  - No representation of: tanks as geometry, pipes as routes, electrical runs, equipment placement, etc.
  - Routing agent expects an interior layout + equipment nodes; the “generative loop” doesn’t produce those artifacts.

### Required changes
- Add a **Vessel Assembly Orchestrator** (new) that runs:
  - hull generation (existing)
  - system instantiation → placement → routing → validators → iterate
  - and can also run in “edit mode” based on a user request

**Proposed module:**
- `magnet/agents/vessel_designer.py` (new)
  - Wraps existing spiral + kernel tools rather than inventing a separate CORTEX runtime.

**Acceptance criteria:**
- A single entrypoint can:
  - create a vessel from a mission string
  - modify an existing design (move/replace components, re-route, revalidate)

---

## 3) Domain Libraries / Patterns: partially exist, not versioned, not tool-exposed

### What exists today
- “Patterns” exist implicitly in deterministic generators (e.g., `FuelSystemGenerator`) but:
  - not represented as a registry
  - not versioned/deprecated
  - not auditable (“which pattern version did this design use?”)

### What’s missing
From CORTEX §2.5 (pattern registry with versioning + regulatory refs):
- pattern IDs + versions
- usage logging per design/version
- deprecation workflow + affected design listing

### Required changes
- Create a pattern registry in MAGNET that records:
  - `pattern_id`, `version`, `regulatory_refs`, `parameters`, `applied_to_design_version`

**Proposed modules:**
- `magnet/systems/patterns/schema.py` (new)
- `magnet/systems/patterns/registry.py` (new)
- Refactor `systems/*/generator.py` to:
  - declare pattern metadata
  - record usage into state (`systems.pattern_usage[]` or `metadata.pattern_usage[]`)

**Acceptance criteria:**
- You can answer: “Which designs used ABYC H-33:2024 fuel pattern v2.1.0?”

---

## 4) Systems as editable artifacts (the real blocker)

### Current state (example: fuel)
- Fuel system logic:
  - generates tanks/pumps with approximate positions (centroids)
  - validates capacity/redundancy
  - writes scalar outputs to state
- Missing:
  - tanks/pumps are not **placeable objects** in the hull geometry space
  - no routing primitives representing fuel lines/vents/fills
  - no conflict detection against other systems

### What must change
Represent system components and routes as **geometry resources** (to preserve “universal primitives” / non-enumeration):
- Tanks/pumps/generators → `geometry.body` (with tags/metadata describing component type/system)
- Lines/ducts/cables → `geometry.flow_path` (with medium + cross-section + endpoints)
- Penetrations/openings → `geometry.opening` (with purpose tags)
- Mounting/attachments → `geometry.attachment`

This avoids inventing new “system.*” primitives and stays aligned with North Star law: compositional primitives, not templates.

**Required refactors (fuel as first system):**
- `systems/fuel/generator.py`:
  - output both:
    - engineering model (as today) **and**
    - a generated **design program** (CREATE geometry bodies + flow_paths + openings)
- Add a deterministic “system-to-geometry compiler”:
  - `magnet/systems/compiler.py` (new)

**Acceptance criteria:**
- A generated design shows:
  - fuel tank bodies in WebGL
  - fuel line flow_paths in WebGL
- User can say: “Move port fuel tank forward 0.5m”
  - system updates and routing is re-run (or incrementally repaired)

---

## 5) Observable Schema (CORTEX) vs MAGNET Observable Registry (exists, not packaged for LLM)

### What exists today
- `kernel/geometry_observables.py` defines:
  - `ObservableSpec` (including future control modes: DIRECT|COMPILED|OPTIMIZED)
  - measurers for key hull metrics
- `agents/geometry_observables.py` provides a closed set of IDs for thinking-pass binding.

### What’s missing vs CORTEX §1.4
- No auto-generated “schema summary” is being passed to the LLM as a formal contract.
- No “unknown observable” rejection mechanism at the tool layer for general queries (outside thinking pass).

### Required changes
- Implement `ObservableSchemaGenerator` *in MAGNET terms*:
  - component instances = bodies + system-tagged bodies/flow_paths/openings
  - metrics = keys from `OBSERVABLE_REGISTRY`
  - sample queries = auto-generated from current bodies + key station scopes

**Proposed module:**
- `magnet/kernel/observable_schema.py` (new)

**Acceptance criteria:**
- LLM receives a compact schema summary every turn in spiral chat.
- Any request to query a non-existent observable is rejected deterministically with a clear error.

---

## 6) Conflict Resolution (CORTEX) is not implemented in MAGNET

### What exists today
- Routing has a concept of zones and compliance (`routing/router/zone_manager.py`).

### What’s missing
- Cross-system spatial conflict detection:
  - overlap of component volumes
  - clearance violations
  - access blocked (needs an accessibility model)
- A “claim registry” and resolution strategies (relocate/stack/reroute/escalate)

### Required changes
Once systems are represented as geometry bodies/paths (Section 4), implement:
- `magnet/integration/conflicts/claim_registry.py` (new)
- `magnet/integration/conflicts/resolver.py` (new)
- Add a kernel tool endpoint for:
  - “request_conflict_resolution(conflict_id, preferred_resolution)”

**Acceptance criteria:**
- After “systems generation”, MAGNET can produce a list of conflicts with resolution options.

---

## 7) Compound Intent / COORDINATE: scaffolding exists; optimizer does not

### What exists today
- Design language supports ADJUST/TARGET.
- Observable registry already anticipates `control_mode="OPTIMIZED"` (but Phase 1 is DIRECT-only per header comments).
- API request model supports “compound” mode for intent preview, but this is not the same as coordinated optimization.

### What’s missing
- The **optimizer-backed coordination executor**:
  - choose knob deltas to satisfy constraints while hitting targets
  - report infeasibility clearly

### Required changes
- Implement a `CoordinateExecutor` in kernel space:
  - use finite difference gradients on measurers + apply candidate knob changes via design language actions
  - integrate with the ActionPlan firewall

**Proposed modules:**
- `magnet/kernel/coordinate_executor.py` (new)
- Extend stdlib AST/parser to add a `COORDINATE { ... }` statement (optional), or implement as an API-level compound action that expands to ADJUST/TARGET steps.

**Acceptance criteria:**
- User: “Increase beam to 5.5m while keeping GM ≥ 0.5m; you may adjust draft.”
- System returns either:
  - a converged set of edits (applied), or
  - “infeasible” with the constraint that blocks it.

---

## 8) Three-tier validation: MAGNET has “gate + grades” behavior, but not CORTEX’s phase-blocking model

### What exists today
- Conductor supports a “human decision point” that blocks downstream phases when `kernel.awaiting_human_decision` is true (`kernel/conductor.py`).

### What’s missing
- Formalized Soft Gates:
  - “valid but blocks specific downstream phases”
  - explicitly tracked as `blocked_phases` in validation results
- Manufacturability gates distinct from design validity

### Required changes
- Extend validator result schema (or aggregator) to include:
  - `gate_type`: hard|soft|grade
  - `blocked_phases`: list
- Update Conductor gate evaluation to:
  - block only the relevant phases (not a single global switch)

**Acceptance criteria:**
- A manufacturability failure blocks `production_export` but does not block hull iteration.

---

## 9) Character Preservation: partial capability exists; not wired as a first-class contract

### What exists today
- Character observables and audits/tests exist in repo (e.g. `tests/agents/test_hull_character_observables_v02.py`)
- Kernel has measurable character metrics in `geometry_observables.py`.

### What’s missing
- A stored baseline signature at “first valid hull” and an automatic drift check after subsequent edits/levels.
- UI surfacing (warnings + “character lock” controls).

### Required changes
- Persist a baseline character signature in state at first “hull valid” checkpoint.
- Compute drift each time geometry changes significantly (post-commit hook or post-phase hook).

**Acceptance criteria:**
- Significant drift triggers a warning with the top contributing metrics.

---

## 10) Non-enumeration consistency gaps (important for reliability)

### Observation
The North Star forbids “vessel type presets in kernel”, but the keyword intent parser includes enum mappings for `hull.hull_type` (see `deployment/intent_parser.py`).

### What must change
- For the generative+edit agent path, route “type-like” user requests into **geometry programs + observables**, not `hull.hull_type` enums.
- Keep enums for UI display if needed, but treat them as derived labels, not authoritative design drivers.

**Acceptance criteria:**
- “72’ sportfisher” does not become “HullType=PLANING” as a controlling input; it becomes a set of geometric targets + system requirements.

---

## Recommended Implementation Order (min-risk path to the demo)

### Phase A — Make systems visible + editable (fuel-first)
- Build ArtifactGraph view over `resources`.
- Extend fuel generation to emit geometry resources (tanks as bodies, lines as flow_paths).
- Add minimal validation hooks that can read those resources.

### Phase B — Observable schema + tool contracts
- Generate and pass schema summary to LLM every turn.
- Add strict query validation.

### Phase C — Dual-mode vessel designer
- Add a “vessel designer” orchestrator that:
  - for CREATE: hull → fuel → (optional electrical) → validate → iterate
  - for EDIT: identify impacted system artifacts → move/route/validate → iterate

### Phase D — Conflict resolver + COORDINATE
- Add spatial claims + conflict resolution.
- Implement optimized coordinated intent using the existing observable scaffolding.

---

## Concrete “Missing” List (CORTEX v2 spec → MAGNET work items)

### Core architecture
- **Missing:** `cortex/` runtime package  
  - **Replace with:** MAGNET-native modules (do not fork SSOT).

### Artifact graph
- **Missing:** `ArtifactGraph` implementation + CAD import integration for systems  
  - **Add:** `magnet/artifacts/graph_view.py` + import adapters.

### Domain patterns
- **Missing:** pattern registry (versioning, deprecation, usage logging)  
  - **Add:** `magnet/systems/patterns/*`.

### Tools (kernel)
- **Missing:** kernel tools for generate_system/place/move/route/delete at the artifact level  
  - **Add:** tool endpoints that compile to design-language or ActionPlan operations.

### Conflict resolver
- **Missing:** spatial claim registry + resolver  
  - **Add:** integration conflict modules + APIs.

### Compound intent
- **Missing:** OPTIMIZED control mode + coordinated optimizer  
  - **Add:** kernel coordinate executor + API/tool wrapper.

### Validation tiers
- **Missing:** formal soft gate model with blocked phases  
  - **Add:** blocked-phase propagation through validator results and conductor.

### Manufacturability
- **Missing:** explicit manufacturability validators tied to geometry/assembly  
  - **Add:** production/manufacturability validator suite (start simple).

### Character preservation
- **Missing:** baseline signature capture + drift enforcement in pipeline  
  - **Add:** state persistence + drift computation hook + UI surfacing.

---

## Definition of Done (what “Claude web design equivalent” means here)

### Demo 1 — Generative
User: “72 foot sportfisher”  
System produces:
- a hull shell
- a fuel system (tanks + lines) visible in WebGL
- validation report

### Demo 2 — Edit
User: “Make the engine room more accessible”  
System:
- identifies obstructing components (system artifacts)
- moves/relocates them
- reroutes affected flow_paths
- revalidates and reports changes

---

*End of audit.*

