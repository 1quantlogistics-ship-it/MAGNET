### Bidirectional Observables (ADJUST/TARGET) — Implementation Plan (v0)

> **Superseded:** Consolidated into `CORTEX_V2_IMPLEMENTATION_GUIDE.md` (project root).

**Goal**: make “model knowledge accountable geometry” by shifting edit operations from raw point clouds to **two fixed DSL verbs** that operate on **open (string) observable IDs**, with kernel-owned control mappings.

---

### 0) Problem statement (why)
The model is unreliable at editing hulls by emitting raw `geometry.section.points`; it frequently:
- breaks topology/identity (section count, station plan drift)
- produces degenerate geometry (“taco”)
- destroys correspondence (HARD indices / point counts)

We need an edit interface where:
- **Model declares intent + values**
- **Kernel executes mechanically with invariants**
- **Failures are explicit and audited**

---

### 1) Core principle (architecture boundary)
**Grammar: FIXED forever (2 verbs).**  
**Observable namespace: OPEN (strings).**  
**Control capability: OPEN (registry entries), no grammar changes.**

New capability = add a registry entry (measurable/controllable + mapping), **no parser changes** beyond the two verbs.

**2026-01-21 extension (CORTEX v2 alignment):**
- The same ADJUST/TARGET contract should extend beyond “hull-only” to **system-tagged artifacts** once systems are represented as `geometry.*` resources:
  - component bodies (e.g. tanks, generators) become controllable via position/clearance/access observables
  - routes (e.g. fuel lines) become measurable/optimizable via routing-length / clearance observables
- Treat any “ArtifactGraph” as a **view/adapter over `DesignState.resources`** (no second SSOT).
- Gap audit reference: `CORTEX_V2_IMPLEMENTATION_GAP_AUDIT.md`

---

### 2) Two new DSL verbs (forever)
Add two statement types:
- `ADJUST <observable_id> AT <scope> BY <delta>`
- `TARGET <observable_id> AT <scope> = <value>`

**Scope** must be generic and non-enum:
- `AT station_range=(0.8, 1.0)` (normalized 0..1)
- `AT station=0.5`
- optional: `AT body_id="main_hull"` (multi-body)

**Notes**
- Observable IDs are strings. Unknown IDs are rejected by registry lookup.
- In EDIT mode, these become the *only* allowed shape edits (identity-preserving).

---

### 3) Observable registry extension (measurable + controllable)

#### 3.1 Registry location in this repo (current)
Today the measurable observables used by thinking-pass live in:
- `magnet/agents/geometry_observables.py` (registry: `VALID_OBSERVABLE_IDS`, measurers)

For bidirectional control we need a kernel-owned registry. Implementation choices:
- **Option A (preferred)**: create `magnet/kernel/geometry_observables.py` as the canonical registry (measurable + controllable), and have `magnet/agents/geometry_observables.py` import from it.
- **Option B**: extend the existing `magnet/agents/geometry_observables.py` and treat it as canonical (less clean separation).

This plan assumes **Option A**.

#### 3.1.1 Observable schema packaging (LLM contract)
In addition to the registry itself, we need a runtime-generated **ObservableSchema summary** that is passed to the LLM each turn:
- list of *known observable_ids* (registry keys)
- list of *current instance targets* (e.g. bodies/components present, by `body_id` / `system_id`)
- sample query strings (bounded set for context)

This prevents the LLM from inventing observables or targeting non-existent artifacts.

#### 3.2 Schema
Represented as Python dataclasses or dicts; persisted only as code (not user state).

```python
ObservableSpec = {
  "observable_id": str,
  "measurable": True,
  "controllable": bool,
  "control_mode": "DIRECT" | "COMPILED" | "OPTIMIZED",
  "knobs": list[str],              # names of geometric knobs used by mapping
  "constraints": list[str],        # invariants to preserve (identity/topology)
  "side_effects": list[str],       # other observables that may move
  "reason": str | None,            # if not controllable, why + alternatives
  "alternatives": list[str],       # suggested observable_ids that are controllable
}
```

#### 3.3 Control-mode meaning
- **DIRECT**: single deterministic mapping (no solver); bounded, predictable; can report exact applied delta.
- **COMPILED**: kernel selects a deterministic sequence of DIRECT knobs for a requested target (still no iterative solver).
- **OPTIMIZED**: iterative; must include convergence bounds, max iterations, and honest “residual” reporting.

---

### 4) Parser + AST changes (two verbs, then stable)

#### 4.1 Files
- `magnet/kernel/stdlib/ast_nodes.py`
  - add `AdjustStatement`, `TargetStatement`
- `magnet/kernel/stdlib/parser.py`
  - parse `ADJUST ...` and `TARGET ...` into AST nodes

#### 4.2 AST shapes (suggested)
```python
@dataclass
class AdjustStatement(Statement):
    observable_id: str
    scope: Dict[str, Any]  # station_range, station, body_id
    delta: float

@dataclass
class TargetStatement(Statement):
    observable_id: str
    scope: Dict[str, Any]
    value: float
```

Parser grammar examples:
- `ADJUST section_metric:deadrise_deg_at_chine AT station_range=(0.8,1.0) BY +5`
- `TARGET longitudinal_metric:entry_fineness_p95 AT station_range=(0.0,0.25) = 0.25`

---

### 5) Kernel execution path (expander + control engine)

#### 5.1 Files
- `magnet/kernel/stdlib/expander.py`
  - add `_expand_adjust(stmt, state)` and `_expand_target(stmt, state)`
- `magnet/kernel/program_executor.py`
  - unchanged; it already uses parser + expander + compile; we just add new statement handlers.
- `magnet/kernel/stdlib/compiler.py` / `section_compiler.py`
  - must preserve existing invariants (point count, hard edges, station convention).

#### 5.2 Execution semantics
For each ADJUST/TARGET:
1. **Parse + validate** statement (scope shape)
2. **Look up** `observable_id` in registry
3. If **unknown** → error (`unknown_observable`)
4. If measurable but **not controllable** → reject (`not_controllable`) + alternatives from registry
5. If controllable:
   - measure current value under scope (measurer)
   - for TARGET compute delta = `target - current`
   - execute control mapping for that observable under scope
   - re-measure, compute residual error
6. Return structured receipt (see §8)

**Non-negotiable invariants during control**
- Preserve resource identity: do not change existing `geometry.section` IDs or counts in EDIT mode.
- Preserve correspondence: do not change point count per body; preserve hard-edge indices (existing contracts).
- Preserve section ordering: station convention is canonical (0=aft/AP, 1=forward/FP).

---

### 6) Control mappings (Phase 1 targets)
Phase 1 is **DIRECT-only** mappings for highest-value edit controls.

#### 6.1 Mapping interface
```python
def apply_control(
  *,
  state_dict: Dict[str, Any],
  observable_id: str,
  scope: Dict[str, Any],
  delta: float,
) -> Dict[str, Any]:
  """
  Returns: updated_state_dict (resources mutated deterministically)
  Must preserve identity + topology invariants.
  """
```

#### 6.2 Phase 1: controllable observables (examples)
These align with existing measurable observables:
- `section_metric:deadrise_deg_at_chine` (**DIRECT**)
- `section_metric:topside_angle_deg_above_chine` (**DIRECT**)
- `longitudinal_metric:sheer_rise_m` (**DIRECT**, implemented as scoped “raise sheer z” within station_range)
- `section_metric:max_half_beam_m` (**DIRECT**, adjust beam by scaling y within scope)

#### 6.3 DIRECT mapping examples (deterministic)

**A) Deadrise at chine (DIRECT)**
- **Knob**: adjust bottom geometry while preserving a chosen pivot (either **preserve chine** or **preserve keel**; must be explicit).
- **Scope**: filter sections by station_range, then adjust each section
- **Transform** (sketch, must be explicit about pivot):
  - identify chine-like point index via existing `_chine_like_point` logic (or reuse the anchored metric)
  - compute current deadrise angle \( \beta = \arctan(|\Delta z| / |\Delta y|) \)
  - choose **pivot policy** (Phase 1 default should be “preserve chine point” to preserve topside/freeboard continuity):
    - **Preserve chine (recommended default)**:
      - keep \( (y_c, z_c) \) fixed
      - keep \( y_k \) fixed at the keel anchor (usually ~0)
      - set new keel z so the angle matches:
        \[
        z_{k,new} = z_c - \Delta y \cdot \tan(\beta + \delta)
        \]
        where \( \Delta y = |y_c - y_k| \)
      - then smoothly distribute the resulting \( \Delta z_k = z_{k,new} - z_k \) across “bottom” points (keel→chine) to avoid kinks.
    - **Preserve keel (alternate)**:
      - keep \( (y_k, z_k) \) fixed
      - set chine z:
        \[
        z_{c,new} = z_k + \Delta y \cdot \tan(\beta + \delta)
        \]
      - note: this will change freeboard/draft unless compensated elsewhere.
  - re-enforce strictly increasing z and re-run validity checks (self-intersection, min spacing, etc.)

**Side effects are expected and must be measured (even in DIRECT mode):**
- Deadrise changes will generally affect displacement, wetted surface, and stability metrics.
- Phase 1 requirement: record a small **local Jacobian estimate** via re-measurements:
  - \( \partial gm/\partial \beta \), \( \partial \nabla/\partial \beta \), \( \partial S/\partial \beta \) (measured numerically from the kernel, not predicted).
  - Store these as `side_effects_measured` in the receipt (see §8). This is not an optimizer—just an honest sensitivity report.

**B) Sheer rise (DIRECT)**
- **Knob**: translate top N points in z (near sheer) within station_range by +dz (bounded)
- **Scope**: station_range filter
- **Transform**:
  - for each section in scope, find top-of-section (max z) and points above chine; add +dz tapering to 0 at chine point to avoid discontinuity

**C) Max half beam (DIRECT)**
- **Knob**: scale y coordinates about centerline for points above keel (or whole section) within scope
- **Transform**:
  - compute current max_y; desired max_y = max_y + delta
  - scale factor = desired / current (clamped)
  - apply y := y * scale for points in controlled region; preserve y≥0

**D) Topside angle above chine (DIRECT)**
- **Knob**: increase flare by expanding y for points above chine as a function of z distance above chine
- **Transform**:
  - for points above chine: y := y + k*(z - z_chine) (k derived from delta angle)

All transforms must re-run a local sanity:
- enforce strict z monotonic
- dedupe consecutive points
- preserve point count
- (optional) preserve HARD indices by moving the value at those indices, not reindexing

---

### 7) Failure modes + reporting contract (no silent success)
Return structured errors/receipts for:
- **unknown observable**: `unknown_observable` (+ list of known IDs or search hint)
- **not controllable**: `not_controllable` (+ reason + `alternatives`)
- **scope invalid**: `invalid_scope` (e.g., bad station_range)
- **constraint violation**: `constraint_violation` (would break z-monotone / point-count / self-intersection guard)
- **cannot converge** (Phase 2 only): `not_converged` (+ residual + iterations)
- **residual tolerance rules (DIRECT mode)**:
  - DIRECT mappings MUST define `tolerance` per observable (see §15.2).
  - If residual > tolerance:
    - **Phase 1 default**: fail-closed with `not_within_tolerance` (state unchanged).
    - Optional “clamp ok” user override can allow `applied_with_residual` *only if* geometry validity holds and the user explicitly accepts.
  - This resolves the Phase 1 inconsistency: tolerance exists, but partial success is opt-in and never silent.

---

### 8) Turn record / audit trail (receipt)
Each ADJUST/TARGET yields a per-statement receipt:
- `observable_id`
- `scope`
- `requested` (delta or target)
- `measured_before`
- `measured_after`
- `achieved_delta`
- `residual`
- `knobs_used`
- `side_effects_measured` (optional Phase 2)

Plumb into:
- `storage/designs/{id}/turns.jsonl` (append-only)
- and/or `TurnContract` receipts later (Vault integration)

---

### 8.1 SSOT + write paths (systemic consistency)
This plan introduces receipts (TurnRecord) but **does not introduce a new state store**.

**Rule: all writes must flow through one of:**
- the design language execution path (program → expander → actions → `StateManager`)
- or ActionPlan execution (Intent→Action firewall)

**TurnRecord / receipts are derived artifacts:**
- written atomically alongside the state commit
- never used as a source of truth for geometry

This avoids SSOT confusion when other modules (conflict resolution, routing repair) propose edits: they must emit DSL/ActionPlans, not mutate `resources` directly.

### 8.2 Canonical observable taxonomy + aliases (avoid namespace collisions)
This repo currently has multiple naming conventions (e.g., `section_metric:...` vs `...:hull`).

**Required rule:**
- A single kernel-owned observable registry is canonical.
- Aliases must be explicit and versioned:
  - e.g. `deadrise_progression:hull` may be an alias for a derived longitudinal metric computed from section metrics.
- The schema passed to the LLM must include both:
  - canonical IDs
  - allowed aliases (optional), with deprecation warnings.

This prevents “observable namespace collision” across documents and tools.
---

### 9) Integration with EDIT vs REWRITE boundary
**Policy**:
- **EDIT mode**: only ADJUST/TARGET (and safe SET metadata). No CREATE/UPDATE for geometry resources.
- **REWRITE mode**: full CREATE/UPDATE allowed (existing flow), but emit a warning “deprecated: use ADJUST/TARGET for edits”.

This makes the boundary enforceable by **statement type**, not heuristics.

---

### 10) Proposer prompt update (Phase 1)
In EDIT mode:
- instruct: emit ADJUST/TARGET only
- include:
  - current measured values for relevant observables (so model can choose deltas)
  - available controllable observables (from registry) vs measurable-only observables
  - remind: kernel will reject unknown/non-controllable IDs and suggest alternatives

In REWRITE mode:
- keep existing two-artifact contract (thinking + program)

---

### 11) Tests (contracts)
Add tests in three layers:

#### 11.1 Parser/AST
- `test_parse_adjust_statement`
- `test_parse_target_statement`
- scope parsing: station_range, station, body_id

#### 11.2 Expander/execution
- Seed a simple hull and apply:
  - `ADJUST section_metric:max_half_beam_m AT station_range=(0.4,0.6) BY +0.5`
  - assert point count unchanged; section IDs unchanged; max_half_beam increases within tolerance

#### 11.3 Spiral EDIT enforcement
- In EDIT mode, reject any geometry resource CREATE/UPDATE (already implemented for CREATE; extend to UPDATE in Phase 1 once ADJUST/TARGET exist)
- Allow REWRITE only via explicit confirmation signal

#### 11.4 Identity Continuity (Viking regression)
- Load a known-good hull (v2 baseline fixture)
- Apply `ADJUST longitudinal_metric:sheer_rise_m AT station_range=(0.7,1.0) BY +0.2m`
- Assert:
  - same `geometry.section` IDs, same count, same ordering
  - geometry validity checks pass (see §15.3)
  - observable moved in expected direction (sheer_rise increased within tolerance)

---

### 12) Phase plan (scope control)

#### Phase 1 (unblocks Viking iteration)
- Parser supports ADJUST/TARGET
- Registry has 4–5 controllable observables in DIRECT mode
- Expander executes DIRECT transforms only
- Fail-closed on anything not controllable
- Minimal receipts (before/after/residual)

#### Phase 2 (full system)
- COMPILED mode (deterministic multi-knob sequences)
- OPTIMIZED mode (iterative solver with bounded runtime + honest nonconvergence)
- Side-effect measurement + constraint system integration
- Rich receipts + integration into TurnContract ledger

---

### 13) Files to touch (actual repo map)
**Parser/AST**
- `magnet/kernel/stdlib/ast_nodes.py`
- `magnet/kernel/stdlib/parser.py`

**Execution**
- `magnet/kernel/stdlib/expander.py`
- (new) `magnet/kernel/geometry_observables.py` (canonical registry + control mappings)
- `magnet/agents/geometry_observables.py` (import measurable registry from kernel)

**Agent**
- `magnet/agents/geometry_proposer.py` (EDIT-mode instructions to use ADJUST/TARGET)

**API**
- `magnet/deployment/spiral_endpoints.py` (EDIT mode: allow only ADJUST/TARGET; REWRITE confirmation)

---

### 14) Deprecation notice (v0 policy)
- `UPDATE geometry.section/body/surface`:
  - **Still parseable** (backward compatibility)
  - **Blocked in EDIT mode** once ADJUST/TARGET land
  - Allowed in REWRITE mode but emits a warning: “deprecated for edits; use ADJUST/TARGET”

---

### 15) Implementation Details (Agent Reference)

- **Observable ID format**: **`<namespace>:<metric_name>`** (string)
  - Examples: `section_metric:deadrise_deg_at_chine`, `longitudinal_metric:entry_fineness_p95`
  - The `namespace:` prefix is part of the ID and is required (so we can route semantics cleanly).

- **Canonical observable list (today)**: `magnet/agents/geometry_observables.py::VALID_OBSERVABLE_IDS`
  - Phase 1 of this plan creates a canonical kernel registry:
    - **`magnet/kernel/geometry_observables.py::OBSERVABLE_REGISTRY`** (measurable + controllable + bounds)
    - and makes `magnet/agents/geometry_observables.py` import from it (single source of truth).

- **Scope syntax (exact grammar)**:
  - `AT station_range=(<float>,<float>)`
  - `AT station=<float>`
  - `AT body_id="<string>"`
  - Combinations allowed (order-insensitive) as a scope map:
    - `AT body_id="main_hull" station_range=(0.8,1.0)`
  - **Canonical punctuation**:
    - `station_range=(a,b)` uses parentheses and a comma; optional whitespace after comma is allowed.

- **Units**
  - **Angles**: degrees
  - **Lengths**: meters
  - Rule of thumb: `_deg_` observables are degrees; `_m` observables are meters; otherwise define explicitly per observable spec.

- **Default `body_id`**
  - If `body_id` is omitted:
    - If there is exactly **one** live `geometry.body` referenced by live sections → use that body.
    - If there are **multiple** bodies → fail-closed with `invalid_scope` and request explicit `body_id`.

- **Delta sign convention**
  - **Positive delta means “increase the measured observable value”.**
  - Example: `ADJUST section_metric:deadrise_deg_at_chine ... BY +5` means *increase deadrise angle by +5°*.
  - Note: “better” may mean decreasing some observables (e.g., finer entry might be a lower slope); that is a design choice, but the sign rule stays consistent.

- **Transform bounds (clamping)**
  - Bounds are **configurable per observable** in the registry (`ObservableSpec`).
  - Default Phase 1 clamps (unless overridden by the observable):
    - **Angles**: max per op \(|\Delta|\) ≤ **15°**
    - **Lengths**: max per op \(|\Delta|\) ≤ **1.0 m**
  - If the request exceeds the clamp:
    - either clamp and report `applied_with_clamp`, **or** fail-closed (Phase 1 policy decision; recommend fail-closed unless user explicitly requests “clamp ok”).

- **Post-transform validation**
  - ADJUST/TARGET output is **not trusted**.
  - Minimum required checks (Phase 1):
    - section sanity: z-monotonic, dedupe consecutive points, y≥0, point-count preserved
    - full compile: run through existing `parse → expand → compile_to_geometry` path
  - Full downstream validator pipeline (physics/stability) remains optional and controlled by existing flags (`validate` / `run_critical_phases`); do **not** couple ADJUST/TARGET to vessel_thinking proof re-execution.

#### 15.1 Station Normalization (canonical)
- Canonical definition (single source of truth for all scope filtering):
  - \( station\_norm = (x - x\_{aft}) / LOA \)
- `x_aft` and `LOA` are derived once from the body’s bounding box at creation time and persisted on the body resource (e.g., `geometry.body.x_aft_m`, `geometry.body.loa_m`).
- `station_range` is **inclusive** `[a, b]` and clamped to `[0, 1]`.
- All station scoping (measure + control) uses this definition (never infer from section ids like “bow”/“stern”).

**Edge cases (scope boundaries not aligned to sections):**
- Phase 1 policy: scope selects *existing sections only* (no interpolation, no section creation in EDIT mode).
- If `station_range` selects zero sections:
  - return `invalid_scope` with a hint listing nearest available stations.
- If boundaries fall between sections:
  - selection is based on each section’s station_norm; no resampling occurs.
- Phase 2+ may add an interpolation-based measurement path (measurers can interpolate), but EDIT-mode geometry must not create/delete sections unless REWRITE is approved.

#### 15.2 Units + Tolerances (per observable)
Extend `ObservableSpec` with:
- `unit`: `"deg" | "m" | "ratio"`
- `tolerance`: float (acceptable residual error after mapping)
- `max_delta`: float (clamp per operation)

Parser/statement validation:
- `BY` and `=` must accept explicit units:
  - examples: `BY +5deg`, `BY -0.2m`, `= 0.25ratio`
- The parser validates the unit suffix matches the observable’s `unit`.
- If the statement omits a unit suffix, treat it as invalid in Phase 1 (fail-closed; forces explicitness).

#### 15.3 Geometry Validity Checker (post-transform)
After every DIRECT mapping, run deterministic validity checks; fail-closed on any violation:
- **y(z) no self-intersection** in the yz-plane for each affected section
- **z strictly monotonic**: keel < chine < sheer (strictly increasing along point order)
- **no collapsed segments**: min spacing threshold between consecutive points
- **point count unchanged** for every affected section
- **hard-edge indices unchanged** (for any section that uses edge_types)

On failure, return `constraint_violation` with:
- which check failed
- which section_id(s)
- computed evidence (e.g., first violating segment indices, min spacing)

#### 15.4 Edit Surface Definition (authoritative representation)
- Edits apply to the **authoritative section representation** (pre-mesh, pre-tessellation).
- In EDIT mode compilation:
  - allow **count harmonization only**
  - do **not** smooth or reparameterize in ways that change vertex identity
  - require index-stable behavior (hard-edge indices preserved)

#### 15.5 Atomic Receipt
- TurnRecord must be written in the **same transaction** as the state mutation that applied ADJUST/TARGET.
- Receipt includes:
  - `design_version`
  - request summary (observable_id, scope, requested delta/target)
  - achieved delta + residual
  - failure reason (if failed)
- Failed edits are also logged (append-only), with `committed=false` but with the attempted statement + error.

#### 15.6 Stable Anchor Witness
- Measurement functions for anchor-based observables return:
  - `(value, witness)` where `witness` minimally contains `witness_index` (and optionally the anchor z/y used).
- Control mappings should **reuse witness_index when present** (instead of re-detecting anchors), so chine/sheer selection cannot “jump” between edits.
- If the witness becomes invalid due to geometry changes (index out of range, violates monotone z, etc.), fail-closed with `constraint_violation` and require a rewrite or explicit “re-anchor” step.

#### 15.7 Identity Continuity Enforcement
The control engine must enforce identity continuity programmatically (not by convention) for EDIT mode:
- Section IDs unchanged
- Section count unchanged
- Station ordering unchanged (monotone by station_norm; no re-stationing)

On violation: fail-closed with `constraint_violation` and include a before/after summary.

#### 15.8 Diff Budget (EDIT mode)
The current “>50% of stations” rule is too coarse. Replace it with **spatial extent**:
- Compute the union of affected station intervals \([lo, hi]\) across statements (after clamping).
- Define:
  \[
  extent = \frac{\text{measure}(\cup_i [lo_i, hi_i])}{1.0}
  \]
- Phase 1 default thresholds:
  - if `extent > 0.65` → `needs_clarification` (“This affects most of the hull. Rewrite?”)
  - if `extent` is fragmented across many disjoint intervals (e.g. > 4 segments), also escalate (this often indicates “global rewrite via sparse edits”).

This prevents the “every-other-station across the whole hull” loophole and ties the budget to physical span, not section count.

---

### 16) Observable orthogonality (Phase 1 sanity)
Phase 1 must explicitly track whether controllable observables are linearly independent *in effect*.

**Minimum required analysis (cheap, numeric):**
- For each controllable observable \(o_j\), apply a small canonical delta (within clamps) in dry-run.
- Measure the induced changes \(\Delta o_i\) for the other observables \(o_i\).
- Assemble a small sensitivity matrix \(J_{ij} \approx \partial o_i/\partial u_j\).
- If two controls are strongly collinear (e.g. correlation > 0.9), mark one as “redundant” and prefer the other, or require explicit user approval when both are used in one turn.

This prevents conflicting controls like `max_half_beam_m` and `topside_angle_deg_above_chine` fighting each other silently.

