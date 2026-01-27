### Diagnosis + Implementation Plan: “Deep‑V Viking Hull Detail” (No Priors Library, Contract-Driven)

This document responds to the observed outcome:
- The new **binding table + observation targets** fix is working (hulls are no longer trivially prismatic wedges).
- The produced hull is still missing **classic deep‑V sportfisher (Viking-like) character** and has “a degree or two” missing in **fore/aft slope** and other hallmark details.

The intent here is to fix this **the same way we fixed split-brain DOFs**:
**tighten contracts** and **expand measurable observables**—not add a library of canned priors or a new agent.

---

## What worked last time (and why we should repeat it)

The previous “split-brain DOF” issue was not solved by better prompting alone; it was solved by **making claims mechanically bind to measurable outputs**:

- **Closed vocabulary of observables (kernel-computable)**: a shared language between “what the model claims” and “what the kernel can measure”.
- **Binding table**: the model must state where each verified DOF “touches” geometry via observables.
- **Observation targets**: the model must state measurable minima (e.g., span thresholds) that the server checks.
- **Fail-closed + one retry**: if geometry doesn’t match claims, the system retries once with a targeted patch; otherwise it refuses to execute.

Result (confirmed in UI): we no longer need to mention DOFs explicitly, and the system produces **real longitudinal variation** instead of a trivial prismatic wedge.

This new “missing Viking deep‑V character” problem is the same class of failure, just at a higher fidelity layer:
we need **more/stronger observables**, not a priors library.

---

## Executive summary (what’s wrong, in one page)

### What improved (confirmed)
- The system no longer needs the user to mention DOFs explicitly.
- Geometry now shows real longitudinal variation (the “wedge escape hatch” is materially closed).

### What’s still missing (high-level)
The hull lacks *characteristic* deep‑V sportfisher traits that are not guaranteed by “beam varies / sheer varies / rocker varies” alone:

- **Fore/aft rocker/slope tuning** (the “degree or two”): the keel/forefoot rocker and/or trim line progression is underconstrained.
- **Deadrise distribution**: deep‑V isn’t just “a V”; it’s a specific *longitudinal schedule* (typically higher forward, lower aft) and often a warped bottom.
- **Chine + spray rail semantics**: classic sportfish forms have strong chine definition and topside flare progression that affects volume distribution.
- **Transom + aft run geometry**: sportfish planing performance depends on aft buttock fairness, planing flats, and a crisp transom/run.

### Root cause (contract issue, not “LLM inability”)
Our current verification vocabulary is too small:

- v0.1 observables cover only:
  - `section_metric:max_half_beam_m`
  - `section_metric:keel_z_m`
  - `section_metric:sheer_z_m`
  - `section_metric:chine_z_m`
  (see `magnet/agents/geometry_observables.py`)

These are necessary but not sufficient to force “deep‑V sportfisher” character.
So the model can satisfy today’s “non-wedge” contract while still producing a hull missing critical *shape laws*.

---

## Principles (non-negotiable constraints)

- **No priors library**: do not add “Viking template”, “sportfish family”, or a hidden set of hull-type rules.
- **LLM = dynamic prior generator**: it can propose DOFs and intended targets.
- **Kernel = decision engine**: only kernel-computable observables can be used for PASS/FAIL verification.
- **Open DOFs, closed observables**: DOFs remain freely named; verifiable claims must bind to known observables.
- **One retry** remains the rule.

---

## Diagnosis detail: what measurements we’re missing (prioritized)

To close the “missing slope / missing deep‑V character” gap, we need observables that directly measure the missing geometry laws.

However, the observable registry is a real maintenance surface (algorithm + edge cases + tests), so we should **prioritize v0.2** and defer the rest to v0.3+.

### A) Rocker / forefoot / aft run
We currently have `keel_z_m` but not the **slope/curvature** metrics that correspond to “degree or two forward/aft”.

**v0.2 (ship now):**
- `longitudinal_metric:keel_slope_deg_p95` (or deg/m)

**v0.3+ (optional later):**
- `longitudinal_metric:keel_curvature_p95`
- `longitudinal_metric:buttock_slope_deg_p95` (proxy: slope of a few fixed‑y buttocks)

### B) Deadrise schedule (deep‑V / warped bottom)
Deep‑V needs a measurable deadrise proxy per station.

**v0.2 (ship now):**
- `section_metric:deadrise_deg_at_chine` (proxy from section points)
- `longitudinal_metric:deadrise_drop_deg` (fwd_mean − aft_mean)

**v0.3+ (optional later):**
- `longitudinal_metric:deadrise_deg_fwd_mean`
- `longitudinal_metric:deadrise_deg_aft_mean`

### C) Flare / topside progression
“Strong forward flare” needs a measurable angle/proxy:
**v0.3+ (optional later):**
- `section_metric:flare_deg_above_chine` (proxy from segment angle above chine)
- `longitudinal_metric:flare_fwd_mean`
- `longitudinal_metric:flare_aft_mean`

### D) Chine continuity + definition
We currently have `chine_z_m` but not:
- chine “run” longitudinally (how chine height changes along x),
- whether the chine is actually present/continuous.

Needed observables:
**v0.3+ (optional later):**
- `longitudinal_metric:chine_present_coverage` (fraction of stations where a chine proxy is measurable)
- `longitudinal_metric:chine_z_span_m`

### E) Transom / aft planing surface proxies
We need at least a simple proxy for “broad planing flats aft”:
**v0.3+ (optional later):**
- `section_metric:bottom_panel_width_m` (proxy: y span of low-z region)
- `longitudinal_metric:bottom_panel_width_aft_mean`

These are still **enum-free**: they are measurable quantities, not boat families.

---

## Implementation plan (agent-executable)

## v0.2 scope and dependency ordering (blocking dependencies)

**Scope (v0.2)**
- Add exactly **3** new observables (no more):
  - `section_metric:deadrise_deg_at_chine`
  - `longitudinal_metric:deadrise_drop_deg`
  - `longitudinal_metric:keel_slope_deg_p95`

**Dependency ordering**
1. **Step 0** proxy algorithms (write spec → deterministic coding)
2. **Step 1** implement observables in registry (`magnet/agents/geometry_observables.py`) **(blocking)**
3. **Step 3** enforce observation targets for longitudinal metrics (`magnet/agents/vessel_thinking_validator.py`)
4. **Step 4** prompt diff (system prompt hardening; no priors)
5. **Step 5** tests (pass/fail numeric contracts)
6. Run focused suite: `pytest -q tests/agents/test_hull_character_observables_v02.py`

**Blocking dependencies**
- Step 3 cannot be completed until Step 1 exposes computed values for the new observable ids.
- Step 5 cannot be completed until Step 1 + Step 3 are implemented.

---

### Step 0 — Proxy algorithm specification (write before coding)

This section is the “no surprises” contract: define the proxy math and edge cases up front so implementation and tests are deterministic.

#### Proxy: `section_metric:deadrise_deg_at_chine` (v0.2)

**Goal**
Provide a stable deadrise proxy from section points without mesh topology.

**Inputs**
- Compiled geometry section points in (y,z), ordered keel→sheer, baseline-up.
  - Source: compiled `HullGeometry` from `magnet.kernel.program_executor.execute_program(... dry_run=True ...)` via `magnet/agents/geometry_observables.compute_observables_via_dry_run(...)`.
  - Point access pattern: `point.position.y`, `point.position.z`, `point.edge_type` (same pattern already used by `section_metric:chine_z_m`).

**Algorithm (deterministic)**
1. Identify keel point \(P_k\): point with minimum z.
2. Identify chine point \(P_c\):
   - Choose the HARD point with max y (most outboard HARD point).
3. Compute vector \(\vec{v} = P_c - P_k\) in the y–z plane.
4. Deadrise proxy \( \beta = \arctan2(|\Delta z|, |\Delta y|) \) in degrees.

**Predicate: `is_hard(edge_type)` (must match codebase semantics)**
- Use the same semantics already used in the current code for chine detection:
  - Implementation pattern: `str(edge_type).lower() == "hard"` **or** `str(edge_type).lower().endswith("hard")`
  - Citation (existing): `magnet/agents/geometry_observables.py` → `_metric_for_section(..., "section_metric:chine_z_m")`
- This intentionally supports both:
  - Enum-like `EdgeType.HARD`
  - String `"HARD"` / `"hard"`

**Edge cases**
- **No chine (round bilge / no HARD points)**: return `None` (unmeasurable). **No fallback in v0.2**.
- **Multiple chines**: pick most outboard HARD point (max y) for v0.
- **Chine above “waterline”**: still measurable; this is a geometric proxy, not a hydrostatic waterline-dependent quantity.
- **Degenerate** (\(\Delta y \approx 0\)): return `None`.

**Output**
- Type: `float | None`
- Units: degrees

**Pseudocode**
```text
function deadrise_deg_at_chine(section):
  pts = section.points
  if pts empty: return None

  Pk = argmin_z(pts)
  hard = [p for p in pts if is_hard(p.edge_type)]
  if hard empty: return None
  Pc = argmax_y(hard)

  dy = Pc.y - Pk.y
  dz = Pc.z - Pk.z
  if abs(dy) < eps: return None
  beta = atan2(abs(dz), abs(dy)) * 180/pi
  return beta
```

#### Proxy: `longitudinal_metric:deadrise_drop_deg` (v0.2)

**Algorithm**
- Compute `section_metric:deadrise_deg_at_chine` per station where measurable.
- Define “forward” subset = lowest 30% of stations by x, “aft” subset = highest 30%.
- Take `fwd_mean` and `aft_mean` over measurable stations in each subset.
- Return `deadrise_drop_deg = fwd_mean - aft_mean`.

**Note on “30%”**
- 30% is a deterministic proxy split for “entry region” vs “run region” and is not sacred.
- The purpose is robustness across station counts without encoding hull-type heuristics.
- If this proves too sensitive, tuning can be driven by observed distributions (v0.3+), but v0.2 should ship a single fixed rule.

**Edge cases**
- If either subset has <2 measurable samples: return `None` (unmeasurable).

**Output**
- Type: `float | None`
- Units: degrees

**Pseudocode**
```text
function deadrise_drop_deg(sections):
  pairs = [(x_i, beta_i) for each section_i if beta_i != None]
  if len(pairs) < 4: return None
  sort pairs by x

  n = len(pairs)
  fwd = first ceil(0.3*n)
  aft = last  ceil(0.3*n)
  if len(fwd) < 2 or len(aft) < 2: return None

  return mean(beta in fwd) - mean(beta in aft)
```

#### Proxy: `longitudinal_metric:keel_slope_deg_p95` (v0.2)

**Algorithm**
- Compute `section_metric:keel_z_m` per station (minimum z).
- For each adjacent station pair, compute slope magnitude:
  - \( s_i = |\Delta z| / \Delta x \) (m/m), convert to degrees: \( \theta_i = \arctan(s_i) \cdot 180/\pi \)
- Return `p95` of \(\theta_i\).

**Edge cases**
- If <3 stations: return `None`.
- If \(\Delta x \approx 0\): skip pair.

**Output**
- Type: `float | None`
- Units: degrees

**Pseudocode**
```text
function keel_slope_deg_p95(sections):
  series = [(x_i, keel_z_i)] for each section_i where keel_z_i != None
  sort by x
  if len(series) < 3: return None

  slopes = []
  for i in 0..len(series)-2:
    dx = x[i+1]-x[i]
    dz = z[i+1]-z[i]
    if abs(dx) < eps: continue
    theta = atan(abs(dz/dx)) * 180/pi
    slopes.append(theta)
  if slopes empty: return None
  return percentile(slopes, 95)
```

---

### Step 1 — Expand observable registry (v0.2, minimal set)

**Why**
We cannot verify “deep‑V sportfisher character” without measuring deadrise/flare/run/slope.

**Files**
- Update: `magnet/agents/geometry_observables.py`
  - **Touchpoints (existing patterns)**
    - `VALID_OBSERVABLE_IDS` (module constant)
    - `_metric_for_section(section, observable_id)` (function; extend for `section_metric:deadrise_deg_at_chine`)
    - `compute_observable_series_from_geometry(geometry)` (function; add support for `longitudinal_metric:*`)
    - `compute_observables_via_dry_run(program_text, current_state)` (function; unchanged contract)

**Change**
Add a **minimal v0.2 set** (ship fewer, ship sooner):
- `section_metric:deadrise_deg_at_chine`
- `longitudinal_metric:deadrise_drop_deg`
- `longitudinal_metric:keel_slope_deg_p95`

**Definition notes (v0 proxies, deterministic)**
Use the pseudocode + edge cases defined in **Step 0**.

**Done when**
- `VALID_OBSERVABLE_IDS` includes the new ids and computation returns non-empty series for typical hulls.

---

### Step 2 — Extend binding-table semantics to allow longitudinal metrics

**Why**
Some missing traits (slope/deadrise drop) are longitudinal aggregates, not single-station values.

**Files**
- Update: `magnet/agents/vessel_thinking_schema.py`
  - **Touchpoints**
    - `ObservationTarget.observable_id` accepts the new ids (no other schema change required)

**Change**
- Allow `binding_table.binds_to` to reference both:
  - `section_metric:*`
  - `longitudinal_metric:*`
- Keep registry closed; only add what `geometry_observables.py` can compute.

**Done when**
- Schema accepts the new observable ids.

---

### Step 3 — Enforce observation targets against the expanded observables

**Why**
We want “deep‑V sportfisher” character without writing a template; the contract must force measurable outcomes.

**Files**
- Update: `magnet/agents/vessel_thinking_validator.py`
- Update: `magnet/agents/geometry_proposer.py` (prompt wrapper text only if needed)

**Touchpoints**
- `magnet/agents/vessel_thinking_validator.py`
  - `validate_observation_targets_against_geometry(thinking, program_text, current_state)`:
    - must accept that some observables are **single-valued longitudinal metrics** (not series spans)
- `magnet/agents/geometry_proposer.py`
  - `GeometryProposer.propose(...)`:
    - already calls `validate_observation_targets_against_geometry(...)`
    - must treat any non-empty returned `issues` as fail-closed + one targeted retry

**Change**
- In `validate_observation_targets_against_geometry(...)`, add support for:
  - `longitudinal_metric:*` being validated as **thresholds** (v0.2), not `span_min`:
    - Example: `deadrise_drop_deg >= 6`
    - Example: `keel_slope_deg_p95 >= 2`

**v0.2 observation target shape**
- Reuse existing `ObservationTarget.span_min` as a generic “minimum required value” for longitudinal metrics.
  - (Do not introduce a new schema field in v0.2; keep the contract minimal.)
  - v0.3 note: this is semantically overloaded (`span_min` as “series span” vs “scalar threshold”); consider introducing `threshold_min` in v0.3 for clarity.

**Done when**
- The system fail-closes when deadrise drop/slope/flare requirements are claimed but not met by geometry.

---

### Step 4 — Prompt guidance (strengthen general rules; no type-specific checklists)

**Why**
You observed we didn’t need to mention DOFs; we should codify this by changing the model instruction style:
- user provides intent in plain language,
- model invents DOFs + binds them to observables + sets observation targets.

**Files**
- Update: `magnet/agents/geometry_proposer.py` (system prompt text)

**Prompt diff (exact text; no paraphrasing)**

Apply to: `magnet/agents/geometry_proposer.py` → `GEOMETRY_PROPOSER_SYSTEM_PROMPT`

```diff
@@
 RULES:
 1. ALWAYS include reasoning explaining WHY this geometry achieves the goal
 2. NEVER output hull.spray_rail, hull.chine, etc. — use geometry.* primitives
 3. Use freeform strings for body_type, surface_type, medium — be descriptive
 4. Set confidence < 0.7 if the translation is uncertain
 5. If multiple approaches exist, output the SIMPLEST one first
    - On a BLANK design, "simplest" means a minimal complete hull (body+sections+lofted surface),
      NOT a discontinuity-only program.
+
+VERIFICATION CONTRACT (NO PRIORS):
+- You may invent any DOFs you want (open vocabulary).
+- If you claim PASS/FAIL checks (range/monotonic/varies) for a DOF, you MUST bind it to at least one
+  kernel-computable observable and provide measurable observation_targets.
+- If no suitable observable exists, mark the DOF UNVERIFIED (no PASS/FAIL checks) and state the consequence.
+- Observables are measurement functions only (rulers), not templates or hull-type mappings.
```

**Change**
Strengthen the **general binding rule** (no hull-type → required-observable mapping):

- For any DOF that claims to affect hull shape character (e.g., deadrise, flare, rocker/run, chine definition), the model MUST:
  - bind that DOF to at least one kernel-computable observable, and
  - set at least one observation target that can be checked (span/threshold/range).
- If no suitable observable exists, mark the DOF UNVERIFIED and state the consequence; do not claim PASS/FAIL.

**Done when**
- Plain-language "Viking-like deep‑V sportfisher" requests produce binding tables referencing deadrise/slope observables **because the model claimed those traits**, not because a checklist required them.

---

### Step 5 — Tests (the new torture harness for “missing character”)

**Files**
- Add: `tests/agents/test_hull_character_observables_v02.py`

**Test harness pattern**
- Follow the FakeLLM pattern used in:
  - `tests/agents/test_geometry_proposer_invalid_json.py`
  - `tests/agents/test_vessel_thinking_binding_table.py`

**Test contracts (numerical; pass + fail per observable)**

All tests should validate via the existing enforcement path:
- proposer parses thinking pass + program,
- computes observables via dry-run compile,
- fails closed (one retry) if observation targets are not met.

#### Observable A — `section_metric:deadrise_deg_at_chine`

**Should PASS case (expected numeric output)**
- Single section points (baseline-up) with a HARD chine:
  - Keel: `[0.0, 0.0]`
  - Chine HARD: `[2.0, 1.1547]`  (tan(30°)=0.57735 → dz=1.1547 for dy=2.0)
- Expected: `deadrise_deg_at_chine ≈ 30.0° ± 0.5°`

**Should FAIL case**
- Same section but no HARD points (`edge_types` all `"smooth"`)
- Expected: `deadrise_deg_at_chine == None` (unmeasurable)

#### Observable B — `longitudinal_metric:deadrise_drop_deg`

**Should PASS case**
- 7 sections with HARD chine such that:
  - Forward third mean ≈ 24–26°
  - Aft third mean ≈ 16–18°
- Expected: `deadrise_drop_deg >= 6.0°`

**Should FAIL case**
- 7 sections with constant deadrise ≈ 18°
- Expected: `deadrise_drop_deg ≈ 0.0°` and a target `>= 6°` fails

#### Observable C — `longitudinal_metric:keel_slope_deg_p95`

**Should PASS case**
- 7 sections with keel_z varying along x so adjacent slopes yield p95 ≥ 2°
- Expected: `keel_slope_deg_p95 >= 2.0°`

**Should FAIL case**
- Constant keel_z across all stations
- Expected: `keel_slope_deg_p95 ≈ 0.0°` and a target `>= 2°` fails

**Done when**
- The tests fail on “generic wedge / missing deep‑V character” programs even if the thinking pass claims otherwise.

---

### Step 5.1 — Full-flow integration test (optional but recommended)

This is not a live LLM test; it is an integration test of the *contract pipeline* using the existing FakeLLM pattern.

**Why**
- Unit tests prove math. This test proves the **end-to-end enforcement loop**:
  1) prompt → thinking pass + program
  2) dry-run compile → compute observables
  3) verify targets
  4) accept vs fail-closed

**Files**
- Add: `tests/agents/test_hull_character_flow_v02.py`

**Pattern**
- Follow FakeLLM approach from:
  - `tests/agents/test_geometry_proposer_invalid_json.py`
  - `tests/agents/test_vessel_thinking_binding_table.py`

**Test**
- Input intent string: “72 ft deep‑V sportfisher with warped bottom”
- FakeLLM returns:
  - `VESSEL_THINKING_PASS` that binds to:
    - `longitudinal_metric:deadrise_drop_deg` with `span_min >= 6`
    - `longitudinal_metric:keel_slope_deg_p95` with `span_min >= 2`
  - `GEOMETRY_PROGRAM` whose sections actually satisfy those targets.
- Assertions:
  - proposer returns `success=True` with `program != None`
  - binding table contains those observable ids
  - no fail-closed clarification path is taken

---

## Operational note: why this is “similar to the previous issue”

The previous fix worked because we:
- created a shared, kernel-computable language (observables),
- forced binding,
- enforced observation targets fail-closed.

This next fix is the same pattern, just with a richer measurement vocabulary so “Viking-like deep‑V” can’t be satisfied by generic variation alone.

---

## Immediate UI test prompt (post-fix, for acceptance)

After implementing v0.2 observables + enforcement (use absolute thresholds; no “generic baseline”):

“Create a 72 ft offshore sportfisher planing monohull with deep‑V character. Requirements: higher deadrise forward and lower deadrise aft (warped bottom) with deadrise_drop_deg ≥ 6°, and a keel rocker/run with keel_slope_deg_p95 ≥ 2°. Use smooth surface_definition.”

---

## Failure contract (user-visible; fail-closed, one retry)

This section specifies the **exact** behavior the user sees when geometry fails verification.

### Where the contract is enforced (citations)
- **Geometry proposer**: `magnet/agents/geometry_proposer.py`
  - Class: `GeometryProposer`
  - Method: `GeometryProposer.propose(...)`
  - Behavior: on observation mismatch → one strict retry → if still failing returns:
    - `success=False`
    - `error` starts with `THINKING_PASS_INVALID:...`
    - `thinking_pass_failure` contains a targeted patch instruction (see below)
- **User-facing API response**: `magnet/deployment/spiral_endpoints.py`
  - Function: `create_spiral_router(...)` → endpoint `spiral_chat`
  - Behavior: on `thinking_pass_invalid` / `thinking_pass_missing` → return `SpiralChatResponse`:
    - `status="needs_clarification"`
    - `feedback` explains it is a contract failure (not physics/kernel)
    - `errors` includes the details JSON (truncated)
    - `clarification_questions` offers `["retry_same", "simplify_request"]`

### Retry instruction (exact shape)
Produced by: `magnet/agents/vessel_thinking_validator.py` → `build_targeted_patch_instruction(...)`

```json
{
  "failed_check_names": ["..."],
  "computed": { "...": "..." },
  "expected": { "...": "..." },
  "instruction": "Regenerate ONLY the affected DOFs and the minimal geometry edits needed to satisfy the failed checks. Do NOT restart from scratch. Preserve stable ids for existing resources."
}
```

### Terminal outcome (after the single retry fails)
- **No silent degradation**: geometry is **not executed/committed**.
- **No rendering of invalid geometry**: the UI should continue showing the prior valid scene (or blank on new design) and surface the failure in the chat panel.

