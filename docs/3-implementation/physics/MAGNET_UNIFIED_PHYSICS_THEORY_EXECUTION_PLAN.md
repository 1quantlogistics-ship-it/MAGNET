# MAGNET Unified Physics Theory (v2.5) — Codebase Audit + Execution Plan

**Authority Spec:** `docs/1-theory/physics/MAGNET_UNIFIED_PHYSICS_THEORY.md`  
**This doc:** Engineering plan to achieve the spec with minimal rework (blocker-first ordering).  
**Scope:** Backend kernel + physics + compiler + minimal API/UI surfaces needed for the “Human Decision Point”.  

---

## Agent Execution Guardrails (Prevent Drift)

### Single Source of Truth (SSOT) — LOCKED
**Hydrostatics truth MUST be computed from section polygons, not mesh and not hull families/types.**

Authoritative pipeline (LOCKED):
1. **Input authority:** `DesignState.resources` (`geometry.section` polygons; plus `geometry.body` offsets for multi-body)
2. **Compiler:** `magnet/kernel/stdlib/compiler.py::compile_to_geometry()` → `HullGeometry` (sections + body attribution)
3. **Hydrostatics truth:** `magnet/physics/geometry_hydrostatics.py::compute_hydrostatics_from_geometry()`
4. **State outputs:** write canonical paths (e.g., `hull.displacement_mt`, `hull.kb_m`, `hull.bm_m`, …) regardless of internal method.

**Explicit non-authorities (allowed only as compatibility fallback during transition):**
- `magnet.hull_gen.generator.HullGenerator` and any `HullType` mapping (`hull_type` strings) are **NOT** the theory path.

### Locked Decisions Table (Reduce Choice Surface)

| Decision | Locked choice | Where enforced |
|---------|---------------|----------------|
| **Hydrostatics on demo path** | `GeometryHydrostaticsCalculator.calculate()` MUST call `compute_hydrostatics_from_geometry()` | `magnet/physics/geometry_hydrostatics.py` |
| **Waterline datum** | baseline `z=0`; waterline at `z=draft` | `magnet/physics/geometry_hydrostatics.py` + tests |
| **Half-section convention** | Y+ = port; author port half; mirror to starboard | `magnet/hull_gen/geometry.py` + docs |
| **Human Decision Point enforcement** | HALT is enforced at orchestration boundary and persisted in state | Choose ONE: `magnet/kernel/conductor.py` (preferred) |
| **Approval mechanism** | One endpoint that accepts “Human Approval Token” and clears halt | `magnet/deployment/spiral_endpoints.py` |
| **Resistance continuity** | No discrete regime switch without weights + uncertainty | `magnet/physics/resistance.py` |
| **Uncertainty schema** | One shared `uncertainty` object shape across validators | physics outputs + Appendix D compliance tests |

### Non-Goals (Do Not Drift Into These)
- Do NOT rename existing canonical output paths used by the system (`hull.kb_m`, `hull.bm_m`, `hull.displacement_mt`, etc.). Change computation behind them only.
- Do NOT build a second “geometry engine” parallel to `HullGeometry`. Use compiler → `HullGeometry` as the bridge.
- Do NOT attempt full primitive physical semantics in one pass; Phase 3 is explicitly staged.
- Do NOT “fix” agent prompts/UI copy as part of physics rigor unless required for the Human Decision Point UX.

### Definition of Done Rule (Per Phase)
For each phase below, **stop only when**:
- The listed code changes are implemented,
- The listed tests are added/updated,
- The verification commands pass,
- And the SSOT statement above is still true.

---

## Current-State Audit (What’s Blocking Full Theory Compliance)

### 1) Numerical Rigor (Hydrostatics)
**Spec requirement (high-level):**
- Section-level properties via **Green’s Theorem** on each station polygon.
- Longitudinal integration via **Simpson’s 1/3 Rule** (or trapezoid + Richardson extrapolation).
- Correct handling of **partially submerged sections** via **waterline clipping**.

**Observed implementation gaps:**
- `magnet/physics/geometry_hydrostatics.py`
  - **Additional gap (demo path / wiring):**
    - `GeometryHydrostaticsCalculator.calculate()` is a stub that raises `NotImplementedError`.
    - This is currently used on the “prefer geometry” path and causes fallback to parametric hydrostatics.
  - Uses **trapezoidal rule** for longitudinal integration (`# Segment volume (trapezoidal rule)`).
  - Uses a **partial/incorrect “shoelace” implementation** for submerged area and a non-area-weighted centroid:
    - `_compute_section_area_below_waterline()` only accumulates edges where **both vertices are below** the draft (drops crossing edges).
    - `_compute_section_centroid()` is a simple average of below-water vertices (not polygon centroid).
  - Waterline beam logic is inconsistent with draft:
    - `_compute_waterline_beam()` has a hardcoded “near z=0” check and interpolation around `z=0` rather than `z=draft`.
  - Type mismatch risk:
    - Functions assume points have `p.y/p.z`, but canonical sections are `HullSection.points: List[SectionPoint]` where coordinates are `p.position.y/p.position.z`.

**Blocker summary:**
- The current “geometry hydrostatics” module is not spec-compliant and is likely not safe as the authoritative hydrostatic gate without refactor + tests.

### 2) Canonical Truth: Sections vs Mesh (Authority / Wiring)
**Spec requirement:**
- **Sections are authoritative** for hydrostatics/stability/volume calculations; mesh is for rendering/export.
- No “hidden category” branches (no `hull_type == catamaran` logic as a truth source).

**Observed implementation gaps:**
- `magnet/physics/validators.py` hydrostatics path:
  - “Geometry-based” path currently calls `magnet.hull_gen.generator.HullGenerator` and still relies on `HullType` mapping and `hull_type` strings (legacy bridging).
  - It does **not** compute hydrostatics from design-language **section polygons**.

**Blocker summary:**
- The validator “geometry integration” path is not the theory’s “sections win” implementation; it is still a parametric/hull_gen-driven fallback that violates the doctrine intent.

### 3) Polygon Integrity (Waterline Clipping)
**Spec requirement:**
- Robust clipping of section polygon(s) at the waterline so partially submerged shapes are integrated correctly.

**Observed implementation gaps:**
- No robust polygon clipping is implemented in `geometry_hydrostatics.py` (only a comment “clip to waterline first”).

### 4) Universal Primitives (opening / flow_path / attachment)
**Spec requirement:**
- The 7 primitives must exist and be usable end-to-end:
  - `section`, `surface`, `body`, `discontinuity`, `opening`, `flow_path`, `attachment`

**Observed implementation gaps:**
- The DSL/type system recognizes these primitives:
  - `magnet/kernel/stdlib/type_registry.py` defines schemas for `geometry.opening`, `geometry.flow_path`, `geometry.attachment`.
  - `magnet/kernel/stdlib/expander.py` enforces referential integrity for `geometry.attachment` (delete checks).
- The compiler does **not** consume them:
  - `magnet/kernel/stdlib/compiler.py` extracts/compiles: `geometry.section`, `geometry.surface`, `geometry.body`, `geometry.discontinuity` only.
  - No integration in WebGL geometry pipeline for these primitives.

**Blocker summary:**
- Primitives exist at the schema layer but are not compiled/rendered/valued in physics yet.

### 5) Gate vs Grade Doctrine + Human Decision Point (Mandatory Halt)
**Spec requirement:**
- **Only hydrostatics** can invalidate a design’s physical existence.
- Stability/resistance/etc are **grades** (can warn, can trigger halt of automation, but not “INVALID”).
- A mandatory **Human Decision Point** after hydrostatics: if severe grade (e.g., GM < 0), set `awaiting_human_decision: true` and halt downstream phases until explicit approval token.

**Observed implementation gaps:**
- Several downstream validators are marked as gate conditions today:
  - `magnet/physics/validators.py`: `physics/resistance` has `is_gate_condition=True`.
  - `magnet/stability/validators.py`: stability validators (`stability/intact_gm`, `stability/gz_curve`, etc.) have `is_gate_condition=True`.
- There is no state-level `awaiting_human_decision` flag, no approval token mechanism, and no orchestration-level halt based on “severe grades”:
  - No code references to `awaiting_human_decision` found in `magnet/`.

**Blocker summary:**
- The platform currently has a “gates” concept beyond hydrostatics; to match the theory, we must separate “phase advancement” from “design validity” and implement the explicit halt/approval mechanism.

### 6) Coordinate / Waterline Convention Conflicts (Spec vs Code)
**Spec text (noted):**
- The theory document’s section domain language references half-sections with a specific side convention.

**Observed:**
- Codebase convention: `Point3D.y` is positive **port** and hull sections are “port side, mirrored for starboard” (`magnet/hull_gen/geometry.py`).
- Hydrostatics code currently hardcodes some `z=0` assumptions in waterline beam logic.

**Blocker summary:**
- Before “physics-as-authority”, we need a single coherent convention for:
  - baseline vs waterline datum (`z=0` baseline, waterline at `z=draft`)
  - half-section mirroring convention

---

## Execution Plan (Blocker-First)

## Phase 0–1 Exact File Edit Checklist (Agent-Executable)

This section removes ambiguity by enumerating the **exact files, functions, and deliverables** for Phase 0 and Phase 1. If a task is not listed here, it is out of scope for Phase 0–1.

### Phase 0 Checklist — Wiring + Doctrine Locks

- **`magnet/physics/geometry_hydrostatics.py`**
  - **Edit**: `class GeometryHydrostaticsCalculator`
    - **Change**: implement `calculate(...)` so it does **not** raise `NotImplementedError`.
    - **Required behavior**: `calculate(...)` becomes a thin wrapper around `compute_hydrostatics_from_geometry(...)` (argument mapping only; no new logic).
  - **No other changes** required in Phase 0 (math upgrades belong to Phase 1).

- **`magnet/physics/validators.py`**
  - **Edit**: `HydrostaticsValidator.validate(...)` (the “prefer geometry” path)
    - **Change**: ensure the code path uses `GeometryHydrostaticsCalculator.calculate()` (now wired) *or* calls `compute_hydrostatics_from_geometry()` directly.
    - **Constraint**: do **not** introduce a third pathway. The “geometry” path must be the SSOT path.
  - **Edit**: `_try_geometry_hydrostatics(...)`
    - **Change**: mark as **compatibility fallback only** and ensure it cannot silently become the preferred path.

- **Doctrine lock points (no feature work yet)**
  - **`magnet/validators/taxonomy.py` / `magnet/validators/aggregator.py`**
    - **Deliverable**: a documented decision (code comment + plan note) on whether `is_gate_condition` means “existential validity” or “phase advancement”.
    - **Constraint**: do not refactor gating in Phase 0; only lock definitions so Phase 2 doesn’t drift.

**Phase 0 Deliverables:**
- `GeometryHydrostaticsCalculator.calculate()` no longer raises.
- The demo “prefer geometry” path no longer falls back due to `NotImplementedError`.

**Phase 0 New/Updated Tests (minimal):**
- Add: `tests/physics/test_geometry_hydrostatics_calculator_wiring.py`
  - Assert `GeometryHydrostaticsCalculator.calculate()` executes without raising.

---

### Phase 1 Checklist — Polygon Ops + Simpson + Correct Datum

- **Add new module:** `magnet/physics/polygon_ops.py`
  - **Add functions (exact):**
    - `normalize_polygon(vertices: list[tuple[float,float]]) -> list[tuple[float,float]]`
      - closure normalization (first==last) policy documented
      - deterministic winding normalization (CCW)
    - `clip_polygon_z_le(vertices: list[tuple[float,float]], z_max: float) -> list[tuple[float,float]]`
      - implements clipping against the half-plane \(z \le z_{max}\)
    - `polygon_area_centroid(vertices: list[tuple[float,float]]) -> tuple[float, float, float]`
      - returns `(area, cy, cz)` using Green’s theorem conventions
    - `polygon_second_moments(vertices: list[tuple[float,float]]) -> tuple[float, float, float]`
      - returns second moments needed for waterplane inertias (document axes and units)

- **`magnet/physics/geometry_hydrostatics.py`**
  - **Edit**: section extraction to a consistent vertex list
    - Convert `HullSection.points` to `(y,z)` from `SectionPoint.position` (no mixed types).
  - **Replace implementations (exact targets):**
    - `_compute_section_area_below_waterline(...)`
      - must clip polygon to `z=draft` then compute area via Green’s theorem
    - `_compute_section_centroid(...)`
      - must use clipped polygon + Green centroid, not vertex averaging
    - `_compute_waterline_beam(...)`
      - must compute beam at `z=draft` (remove implicit `z=0` assumptions)
    - `_integrate_displacement_and_centers(...)`
      - must use Simpson’s 1/3 longitudinal integration (or explicit Simpson+trap/Richardson fallback)
    - `_integrate_waterplane_properties(...)`
      - must be consistent with new waterline beam calculation and moment definitions
  - **Edit**: any “near z=0” checks must be removed or replaced with `abs(p.z - draft)` logic.

**Phase 1 Deliverables:**
- Waterline clipping is correct for partially submerged sections.
- Simpson integration is implemented and used in the longitudinal integrators.
- Datum usage is explicit and consistent (baseline vs draft).

**Phase 1 New/Updated Tests (required):**
- Add: `tests/physics/test_polygon_ops.py`
  - Rectangle fully below WL and partially clipped area/centroid matches analytic values.
  - Deterministic output under different input windings/closure.
- Add: `tests/physics/test_geometry_hydrostatics_rigor.py`
  - Known prism/lofted-by-sections volume test.
  - “Crossing waterline” case (polygon with edges crossing `z=draft`) must not lose area.

---

### Phase 0 — Doctrine & Wiring Baseline (Stop Rework)
**Goal:** Ensure the physics kernel is wired so the later numerical upgrades actually become authoritative, and doctrine doesn’t fight the platform’s gate system.

**Tasks:**
1. **Define “Validity vs Automation” semantics**
   - **Validity (existence):** geometry validity + hydrostatics only.
   - **Automation controls:** severe grades can halt downstream work but never delete/invalid the design object.
   - Files to inspect/change later:
     - `magnet/validators/taxonomy.py`, `magnet/validators/aggregator.py`
     - `magnet/physics/validators.py`, `magnet/stability/validators.py`
     - `magnet/kernel/conductor.py`, `magnet/deployment/spiral_endpoints.py`

2. **Wire hydrostatics to “sections win” path**
   - Define a canonical path: `DesignState.resources (geometry.section...) → compiler → HullGeometry → hydrostatics integration`.
   - Keep legacy `HullGenerator` path as temporary fallback only (explicitly labeled).
   - Wire `GeometryHydrostaticsCalculator.calculate()` to call `compute_hydrostatics_from_geometry()` so the “prefer geometry” path does not immediately fall back.

**Acceptance checks:**
- A design with valid sections can produce hydrostatics without requiring `hull_type` mapping.
- Downstream validators can still run, but they cannot mark design “invalid”; only “severe grade / halt automation”.

**Definition of Done (Phase 0):**
- **Wiring is unambiguous**: there is exactly one “preferred” hydrostatics path on the demo spiral path, and it does not throw `NotImplementedError`.
- **No hidden enum dependency**: the “preferred” path does not require `hull_type` → `HullType` mapping to succeed.
- **No contract breakage**: canonical output paths are still written.

**Verification commands (Phase 0):**
- `python -c "from magnet.physics.geometry_hydrostatics import GeometryHydrostaticsCalculator; import inspect; print('NotImplementedError' in inspect.getsource(GeometryHydrostaticsCalculator.calculate))"`
  - Expected: `False` once wired.
- `pytest -q tests/unit/test_physics_validators.py tests/unit/test_hydrostatics.py`

**Estimated agent-hours:** 12–18

---

### Phase 1 — Hydrostatics Numerical Rigor (Simpson + Green + Clipping)
**Goal:** Implement spec-compliant hydrostatics from station polygons.

**Tasks:**
1. **Create polygon utility module (pure, deterministic)**
   - Implement:
     - polygon closure normalization
     - winding normalization (CCW)
     - clipping against half-plane \(z \le draft\) (Sutherland–Hodgman for a single clip edge)
     - Green’s theorem:
       - area
       - centroid
       - second moments (for waterplane inertia and BM)
   - Likely new file:
     - `magnet/physics/polygon_ops.py` (or similar)

2. **Refactor `magnet/physics/geometry_hydrostatics.py` to use polygon ops**
   - Convert `HullSection.points` → list of `(y,z)` vertices consistently (via `SectionPoint.position`).
   - Replace:
     - `_compute_section_area_below_waterline`
     - `_compute_section_centroid`
     - `_compute_waterline_beam`
     - `_integrate_displacement_and_centers`
     - `_integrate_waterplane_properties`
   - Implement longitudinal Simpson’s 1/3:
     - Prefer odd N stations; otherwise use mixed Simpson+trap or Richardson.

3. **Fix datum usage**
   - Ensure the following invariants are implemented and tested:
     - **Baseline datum:** `z=0` is baseline (not the waterline).
     - **Waterline elevation:** waterline is at `z=draft` during hydrostatics computations.
     - **Half-section convention:** document and enforce which side is authored vs mirrored (the codebase currently uses Y+ = port and “port side, mirrored to starboard”).
     - **No hidden `z=0` waterline assumptions:** remove any “near waterline” checks that implicitly treat `z=0` as the waterline.

**Acceptance tests (must add later):**
- Polygon tests:
  - rectangle fully submerged vs partially clipped gives correct area/centroid.
  - triangle / concave polygon stability.
- Integration tests:
  - known prism volume and centroid within tolerance.
  - Simpson vs trapezoid regression: Simpson should reduce error for curved area distributions.

**Estimated agent-hours:** 30–45

**Definition of Done (Phase 1):**
- Section polygons are clipped correctly at `z=draft` (partial submergence is accurate).
- Section area/centroid use Green’s theorem (not vertex averaging, not “below-only edges”).
- Longitudinal integration uses Simpson’s 1/3 (or documented trap+Richardson fallback).
- No `z=0` waterline assumptions remain in hydrostatics computations.

**Verification commands (Phase 1):**
- `pytest -q tests/physics/test_negative_stability.py`
- `pytest -q tests/unit/test_hydrostatics.py`
- Add and run: `pytest -q tests/physics/test_polygon_ops.py tests/physics/test_geometry_hydrostatics_rigor.py`

---

### Phase 2 — Human Decision Point (Mandatory Halt)
**Goal:** Implement the theory’s explicit halt after hydrostatics when severe grades occur.

**Tasks:**
1. **Define the decision artifact in state**
   - Proposed minimal canonical keys (names TBD):
     - `kernel.awaiting_human_decision: bool`
     - `kernel.human_decision_request: { reason, options, computed_values_snapshot, timestamp }`
     - `kernel.human_decision_token: {...}` once approved

2. **Add orchestration halt**
   - Where to halt:
     - after hydrostatics succeeds and stability grade is computed (or after first severe-grade check)
   - Candidate integration point:
     - `magnet/kernel/conductor.py` (phase runner) or `magnet/deployment/spiral_endpoints.py` (API surface controlling progression)

3. **Add approval endpoint**
   - API endpoint accepts “Human Approval Token” (per spec) and clears the halt.

**Acceptance tests:**
- If GM < 0 (severe), system:
  - returns structured result
  - sets `awaiting_human_decision=true`
  - does not run resistance/propulsion/arrangement until approved
- Approval token resumes pipeline.

**Definition of Done (Phase 2):**
- A severe grade triggers a HALT that is:
  - persisted in design state,
  - returned to UI/API in a structured payload,
  - and prevents downstream phases from executing.
- A human approval token clears the HALT and allows downstream phases to run.

**Verification commands (Phase 2):**
- Add and run: `pytest -q tests/integration/test_human_decision_point.py`
- Add and run: `pytest -q tests/integration/test_persistence.py` (ensure halt state persists)

**Estimated agent-hours:** 14–22

---

### Phase 2.5 — Resistance Method Blending (Optional for v1)
**Goal:** Replace discrete regime selection with continuous method blending + explicit uncertainty disclosure (per theory).

**Observed current mismatch:**
- `magnet/physics/resistance.py` uses discrete regime thresholds based on Froude number (Holtrop valid / approximate / Savitsky required).

**Tasks:**
1. Replace `if Fn < threshold` branching in resistance estimation with **continuous weighting** across parameter space (Fn, Cp, deadrise, etc.).
2. Implement smooth blending (e.g., Holtrop ↔ Savitsky) and ensure weights + reasoning are recorded.
3. Add uncertainty outputs:
   - `validity_envelope`
   - `uncertainty_level`
   - `uncertainty_pct`
   - `extrapolation_flag` / `outside_envelope` markers

**Acceptance tests:**
- No discrete switch without recorded weights.
- Transition zone produces blended results and higher uncertainty (per theory examples).

**Definition of Done (Phase 2.5):**
- Resistance output includes:
  - method weights (or equivalent trace),
  - validity envelope,
  - uncertainty level + pct,
  - explicit extrapolation flags.
- No hard `if Fn < threshold` gate decides the method without emitting weights and uncertainty rationale.

**Verification commands (Phase 2.5):**
- Add and run: `pytest -q tests/physics/test_resistance_blending.py`

**Estimated agent-hours:** 20–30

---

### Phase 3 — Universal Primitives: `opening`, `flow_path`, `attachment`
**Goal:** Make primitives real end-to-end (schema → compiler → rendering/export → physics implications).

**Tasks:**
1. **Compiler support**
   - Extend `magnet/kernel/stdlib/compiler.py` to extract:
     - `geometry.opening`
     - `geometry.flow_path`
     - `geometry.attachment`
   - Decide canonical representation in `HullGeometry.metadata` (short-term) vs new geometry objects (long-term).

2. **Rendering / Export support (minimal viable)**
   - Update WebGL pipeline to:
     - not crash on these primitives
     - display them (even as debug geometry) with traceability

3. **Physics semantics (staged)**
   - Stage A: non-physical/diagnostic-only (present, validated, rendered).
   - Stage B: incorporate into hydrostatics (e.g., subtract submerged volume for openings that penetrate hull).

**Acceptance tests:**
- Round-trip compile and export with these primitives present.
- Primitive completeness test can mark more “real vessel” features as expressible without “out of scope”.

**Definition of Done (Phase 3):**
- Compiler accepts these primitives and produces deterministic geometry metadata or objects (no crashes, no silent drops).
- WebGL/export path can render/export them (at minimum as debug geometry) with traceability.
- If physics semantics are not implemented yet, outputs explicitly label them as **diagnostic-only** (no implied buoyancy impact).

**Verification commands (Phase 3):**
- Add and run: `pytest -q tests/validation/test_primitive_completeness.py`
- Add and run: `pytest -q tests/kernel/test_opening_flowpath_attachment_compile.py`

**Estimated agent-hours:** 40–70 (depends on how physically-real these must be in v1)

---

### Phase 4 — Honest Output Contract (Post-v1 but required for full theory compliance)
**Goal:** Ensure all computed outputs carry explicit uncertainty quantification and novelty impact statements per Appendix D.

**Tasks:**
1. Define a shared uncertainty schema used across validators (hydrostatics, stability, resistance, weight):
   - `uncertainty.value_pct`
   - `uncertainty.level` (LOW/MED/HIGH/EXTREME)
   - `uncertainty.basis` (what model / what assumptions)
   - `uncertainty.validity_envelope`
   - `uncertainty.novelty_impact`
2. Implement uncertainty blocks for:
   - hydrostatics outputs (geometry-derived: novelty impact “none”; numeric error budget)
   - resistance outputs (empirical/regression: envelope + extrapolation penalties)
3. Add system-level “never silently extrapolate” enforcement (flag + raise uncertainty).

**Acceptance tests:**
- Every physics output payload includes an `uncertainty` block.
- Extrapolated conditions are explicitly labeled and increase uncertainty.

**Definition of Done (Phase 4):**
- All physics validators that produce user-facing outputs attach an `uncertainty` object (same schema).
- No silent extrapolation remains (any extrapolation is flagged and increases uncertainty).

**Verification commands (Phase 4):**
- Add and run: `pytest -q tests/invariants/test_honest_output_contract.py`

**Estimated agent-hours:** 15–25

---

## Ordering / Dependencies (Why This Order)
1. **Phase 0 first**: if hydrostatics isn’t wired to be authoritative, numerical upgrades won’t matter.
2. **Phase 1 next**: clipping + Simpson + Green is the core truth engine.
3. **Phase 2 after**: the halt logic depends on reliable grade outputs (GM/freeboard/convergence) computed from the authoritative hydrostatics/stability pipeline.
4. **Phase 3 last**: primitives are expensive to implement; doing them before the hydrostatics kernel is correct leads to repeated rework.

---

## Blast Radius (What Else Will Break / Need Adjustment)

This section lists likely ripple effects once we make the theory real (section-authoritative hydrostatics + clipping + Simpson + Human Decision Point + gate/grade alignment).

### A) Unit/Integration Tests that will need updates
- **Hydrostatics method expectations**
  - There are tests that assert a particular `hull.hydrostatics_method` value or assume parametric hydrostatics dominates.
  - Any test asserting `"parametric"` will need to be updated to accept the new section-authoritative method marker (or a dual-mode assertion).
- **Numerical tolerances**
  - Switching to Simpson + proper clipping will change numeric outputs (usually “more correct”), so tests using tight equality or old tolerances will need recalibration.
  - Expect changes in:
    - `hull.displacement_m3`, `hull.displacement_mt`
    - waterplane area and inertias (`hull.waterplane_area_m2`, `hull.it_m4`, `hull.il_m4`)
    - derived stability values if they’re computed from these fields downstream
- **Geometry-hydrostatics API contract**
  - If `geometry_hydrostatics.py` is corrected to operate on `SectionPoint.position`, any tests/fixtures that currently pass raw `Point3D` objects will need to be normalized.

### B) Validator taxonomy and “gate” semantics
- **Today:** multiple validators are marked `is_gate_condition=True` (resistance + stability).
- **Theory:** hydrostatics is the only “validity gate”; others are grades and may halt automation but not invalidate existence.
- Adjustment required:
  - If the codebase uses `is_gate_condition` to mean “blocks phase advancement”, we must introduce a separate concept:
    - **validity_gate** (existential)
    - **phase_gate** (workflow)
  - Otherwise, flipping `is_gate_condition` will change phase progression and can break:
    - `magnet/validators/aggregator.py` bucketing
    - phase definitions and contracts that assume stability/resistance gating
    - UI displays that show “can_advance” based on gate results

### C) API / UI surfaces that will need adjustment
- **Human Decision Point status plumbing**
  - A halt needs to be representable in API responses and the UI:
    - new status field(s): e.g. `awaiting_human_decision`, `clarification_request`, etc.
  - The UI spiral adapter already supports `needs_clarification`; the halt should reuse that pattern or introduce a new explicit status that the UI understands.
- **Approval endpoint**
  - Adding a “human approval token” endpoint will require:
    - request/response schema
    - UI affordance (button + rationale capture) OR CLI path
    - persistence of the token/state so a refresh/restart doesn’t lose the halt

### D) Data model / state schema drift
- Adding new canonical state keys (e.g., `kernel.awaiting_human_decision`) requires:
  - schema expectations in any state serialization (design store)
  - migration handling for existing designs (default `False`)
  - test fixtures that build minimal states may need to include defaults

### E) Performance & determinism risks
- **Clipping + Green + Simpson** increases computation per section and per iteration:
  - may require caching of per-section clipped polygons or derived moments
  - may require constraining section resolution (theory has minimums; runtime needs maximums)
- Determinism:
  - ensure polygon normalization (closure/winding) is stable and does not depend on floating ordering or non-deterministic iteration.

### F) Downstream physics consumers of hydrostatics fields
- Changing hydrostatics outputs (and/or their meanings) will ripple into:
  - resistance selection regimes (Fn, method validity notes)
  - stability validators (GM, GZ confidence)
  - any reports/exports that read displacement/LCB/VCB
- The plan assumes we keep writing the existing canonical paths (e.g., `hull.kb_m`, `hull.bm_m`, `hull.displacement_mt`) to avoid breaking consumers, even if internal computation changes.

### G) Geometry primitives: partial implementation pitfalls
- If we add `opening/flow_path/attachment` to the compiler without physics semantics:
  - they must be clearly marked “diagnostic only” to avoid users assuming buoyancy/resistance incorporates them.
  - rendering must not imply watertight volume subtraction unless implemented.

---

## Quick “What To Change Later” File Map
**Spec source**
- `docs/1-theory/physics/MAGNET_UNIFIED_PHYSICS_THEORY.md`

**Primary physics refactors**
- `magnet/physics/geometry_hydrostatics.py` (Simpson + clipping + correct polygon math)
- `magnet/physics/validators.py` (stop HullType mapping in “geometry” path; wire to section-authoritative hydrostatics)
- `magnet/stability/validators.py` (grade semantics; integrate halt trigger)

**Compiler / primitives**
- `magnet/kernel/stdlib/type_registry.py` (already has schemas)
- `magnet/kernel/stdlib/compiler.py` (must compile new primitives)
- `magnet/webgl/*` (visualization/export integration)

**Human Decision Point**
- `magnet/kernel/conductor.py` and/or `magnet/deployment/spiral_endpoints.py`

---

## Estimated Total Effort (Agent Work Hours)
- **Phase 0:** 12–18  
- **Phase 1:** 30–45  
- **Phase 2:** 14–22  
- **Phase 2.5:** 20–30  
- **Phase 3:** 40–70  
- **Phase 4:** 15–25  
**Total (full theory compliance):** **131–210 agent-hours** (range depends mostly on how physically-real Phase 3 is in v1 and the depth of Phase 4 uncertainty propagation).

