## MAGNET Production-Grade Implementation Guide (UI v2 + Kernel Single-Authority)

### Goal
Ship a **fully working, production-grade** MAGNET where:
- The **UI is a thin client**.
- The **backend is the single authority** (DesignStore → StateManager → Conductor/PhaseMachine → ValidatorTopology).
- Spiral prompting reliably produces **geometry + hydrostatics gate**, and only then runs downstream “grades”.
- The UI never shows **stale geometry** or misleading “failed phases” banners for expected grade failures.

---

## 0) Current observed failure (what your screenshot means)
The UI warning **“Applied with warnings. Failed phases: hull, weight, stability”** is emitted by `magnet/ui_v2/js/spiral-adapter.js` when the backend returns:
- `status: "partial"`
- `failed_phases: ["hull", "weight", "stability"]`

This is not inherently a physics-theory mismatch; it is primarily a **control-flow mismatch**:
- Spiral is currently configured to run a **multi-phase cascade** after applying changes.
- The cascade includes phases that are **not gates** and can fail for expected reasons (missing inputs/geometry resources).
- The UI treats those failures as a big warning banner, even when the design is valid and geometry exists.

This guide fixes that by aligning the spiral “post-apply” behavior with the authoritative physics doctrine in:
`docs/1-theory/physics/MAGNET_UNIFIED_PHYSICS_THEORY.md` (Gate vs Grade).

---

## 1) Production architecture invariants (non-negotiable)

### 1.1 Single authority chain
\[
\text{UI} \rightarrow \text{API/WS} \rightarrow \text{DesignStore} \rightarrow \text{StateManager} \rightarrow \text{Conductor/PhaseMachine} \rightarrow \text{ValidatorTopology}
\]

- **DesignStore** is the only persistence authority (versioned).
- **StateManager** is the only mutator (transaction enforcement).
- **Conductor/PhaseMachine** is the only phase authority.
- **ValidatorTopology** is the source of truth for which validators belong to a phase.

### 1.2 Canonical identifiers
- UI must send **canonical kernel phases**: `mission`, `hull`, `weight`, `stability`, …
- Backend may accept legacy names, but must normalize them to canonical in:
  - HTTP responses (`kernel_phase`)
  - WS payloads (`kernel_phase`)

---

## 2) Physics doctrine alignment (production semantics)

### 2.1 Gate vs Grade (from Unified Physics Theory)
- **Only gates**:
  - geometry validity (pre-gate)
  - hydrostatics (primary gate)
- **Grades (never invalidate design)**:
  - stability (GM/GZ)
  - resistance
  - others

### 2.2 Spiral post-apply execution policy (production)
After applying spiral changes:
- Always run **hull phase** (hydrostatics gate).
- Do **not** auto-run downstream phases unless explicitly requested.
- If downstream grades are run, their failures must be surfaced as:
  - structured findings / warnings
  - never as “design failed” unless a gate failed.

**Production default**:
- `run_critical_phases = false` (UI)
- backend “critical phases” default = `["hull"]` only (server)

### 2.3 Resolve doctrine split-brain (required)
`docs/0-architecture/core/PHASE_MACHINE.md` historically described Stability as a gate.
This conflicts with the authoritative doctrine in `docs/1-theory/physics/MAGNET_UNIFIED_PHYSICS_THEORY.md`.

**Production rule**: Hydrostatics is the only gate. Stability is a grade with a Human Decision Point.
Keep documentation and code consistent so operators/agents do not implement conflicting behaviors.

---

## 3) Required implementation changes (to reach production-grade)

### 3.1 SpiralAdapter: stop running multi-phase cascade by default
File: `magnet/ui_v2/js/spiral-adapter.js`
- Change request body default:
  - `run_critical_phases: false`
- Optionally allow a user toggle (explicit) to run downstream grades.

Backend: `magnet/deployment/spiral_endpoints.py`
- If `run_critical_phases` is true and `critical_phases` is absent:
  - default to `["hull"]` (not `["hull","structure","propulsion","weight","stability"]`)
- Return phase outcomes with **gate/grade classification**, not a flat “failed_phases” list.

#### Bridge logic placement (required clarity)
The “bridge” that infers `hull.*` scalars from geometry primitives must run during **Apply** (spiral execution),
because it is what makes later phase runs succeed. It must not depend on “run_critical_phases”.

### 3.2 Spiral response schema: add structured phase outcomes
Backend response should include (additive):
- `gate_status`:
  - `gate_passed: bool`
  - `blocking_validators: [...]`
  - `missing_inputs: [...]` (if any)
- `grade_status`:
  - `warnings: [...]`
  - `human_decision_required: bool`
- `phase_results` (map):
  - `{ "hull": {status, errors, warnings}, ... }`

UI should render:
- **Gate failure** → clear blocking banner (actionable)
- **Grade warning** → “Applied, review warnings” (not scary “failed phases”)

### 3.3 Geometry lifecycle correctness (no stale hulls)
Files:
- `magnet/ui_v2/js/scene-manager.js`
- `magnet/ui_v2/js/backend-adapter.js`
- `magnet/ui_v2/js/spiral-adapter.js`

Requirements:
- If GLB fetch returns **404/GeometryUnavailable** (definitively no geometry for this design):
  - the scene must **clear the previous model** and show an explicit placeholder state.
- If geometry is **in-progress** (202/retry loop), do **not** clear immediately (avoid flicker); keep the prior model until replacement succeeds.
- When design changes:
  - always cache-bust GLB via `?v=design_version`

### 3.4 Phase runner and topology wiring hardening
File: `magnet/deployment/api.py`
- Ensure topology build order is correct:
  - `ValidatorRegistry.init` → `topology.add_all_validators()` → `topology.build()`
- Never silently succeed with an empty topology.

#### Production note: build topology once at boot
When bootstrapped via `MAGNETApp().build()`, the validator registry + topology should be built once and registered in DI.
Per-request rebuild is only acceptable in context-less fallback mode.

### 3.5 UI data binding must use `design.state` flat map
Files:
- `magnet/ui_v2/js/panel-renderer.js`
- `magnet/ui_v2/js/panel-config.js`

Requirements:
- Panels read from `design.state` only (flat map).
- Allow config ergonomics via `sourcePrefix` (e.g. `hull.`) so fields can stay short (`lwl`, `beam`, …).

### 3.6 Validator clicks must target the intended kernel check
File: `magnet/ui_v2/js/backend-adapter.js`
Requirement:
- Clicking “Stability” validates/runs kernel `stability` (not “current phase”).
- Class-rule validators route to kernel `compliance`.

---

## 4) Production acceptance criteria (DoD)

### 4.1 Blank design behavior
- `new blank` creates a persisted design with **no geometry**.
- UI viewport shows **no model** (or placeholder), never an old hull.
- “No geometry yet” message matches viewport state.

### 4.2 Prompt → geometry → hydrostatics gate
For a prompt like “Generate a 12m planing monohull, beam 4m, draft 1.2m”:
- Spiral returns `status: applied`
- GLB loads for the new design version
- Hull phase runs and writes:
  - `hull.displacement_m3`
  - `hull.vcb_m`
  - `hull.bm_m` (or canonical hydro outputs)

### 4.3 Downstream grades are non-blocking
- Stability failures produce warnings/findings, not “failed design”.
- UI shows warnings with “View details”, not “Failed phases”.

### 4.4 Phase reachability
UI can run:
- `hull`
- `weight`
- `stability`
individually and in order (dependency errors are clear).

---

## 5) Test plan (must be automated)

### 5.1 API-level integration tests (required)
Create/extend tests to cover:
- create design → spiral apply → run hull → export glb (200)
- ensure `POST /phases/hull/run` executes validators (non-empty topology)
- stability can be run after weight, and returns structured results even if severe

### 5.2 UI contract tests (lightweight)
- `design.state` exists and contains expected keys after phases
- WS payloads include `kernel_phase`

---

## 6) Observability (production)

### Backend logging
Add structured logs (design_id + version + request_id):
- spiral apply start/end + status
- phase run start/end + kernel_phase
- topology build + validator count
- GLB export timing (and “not ready” outcomes)

### Metrics (optional but recommended)
- request duration histograms: spiral/chat, phases/run, export/glb
- counts: gate failures vs grade warnings

---

## 7) Rollout sequence (safe path)
1) **Stop spiral multi-phase cascade by default** (UI + backend default).
2) **Fix geometry clearing** on 404/GeometryUnavailable so viewport is trustworthy.
3) **Normalize spiral responses** (gate vs grade) and update UI banner semantics.
4) Add/lock **integration tests**.
5) Deploy with increased logging; verify on a known prompt set.

---

## 8) Operator quick check (manual)
1) Start backend, open `http://127.0.0.1:8000/ui/v2/`
2) Run: `new blank` → confirm viewport clears
3) Prompt: “Generate a 12m planing monohull, beam 4m, draft 1.2m”
4) Run: `show hydrostatics` → verify displacement/VCB/BM printed
5) Click **Stability** validator → verify it validates stability phase (not hull)

