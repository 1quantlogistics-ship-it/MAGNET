## v0.4 — Profile/Topside Observables Plan (Vessel-Neutral)

### Why (brief)
v0.2/v0.3 enforced **bottom character** (deadrise/warp/rocker) because those were the only measurable “rulers” in the observable registry. The system is fail-closed, so it naturally optimizes what is measured.

v0.4 adds a minimal set of **profile/topside rulers** so the generator can be held accountable for overall silhouette intent (sheer rise, entry narrowing, topside angle), without introducing any hull-type priors.

Viking sportfisher is a **test case**, not the purpose: these observables apply to any vessel with the relevant geometry.

---

## Why the hull form itself won’t be valid (until we fix these three things)

This section is explicitly **hull-form-only** (no superstructure), and it explains why a generated hull can “pass” yet still be invalid/unconvincing.

### 1) Chine anchoring is broken (bottom)
The bottom observables rely on a chine anchor. If the generator can place a HARD marker anywhere, then:
- `deadrise_deg_at_chine` becomes “keel → arbitrary point angle”
- downstream aggregates like `deadrise_drop_deg` become gameable (e.g., absurd values like ~24°)

**Result:** bottom geometry is effectively unconstrained despite “passing”.

### 2) No magnitude calibration (profile/topside)
Without magnitude bounds, rulers can pass with visually negligible variation:
- `sheer_rise_m` can be non-zero but still read flat
- `entry_fineness_p95` can be non-zero but still read blunt
- `topside_angle_deg_*` can be non-zero but still read unflared

**Result:** silhouette/topside can “technically vary” but still look generic.

### 3) Thinking pass may not be binding both dimensions
If the thinking pass doesn’t bind and target both bottom + profile observables, nothing is enforced in that dimension.
Without persistence, we cannot confirm whether DOFs were VERIFIED vs DEFAULTED, or what targets were claimed.

**Result:** fail-closed may not trigger because nothing was claimed/bound.

---

## Pre-step (Correctness) — Resolve station convention contradiction (must do first; vessel-agnostic)

### Problem
There are conflicting definitions of `geometry.section.station` across the system:
- Persisted programs commonly treat `station=0.0` as **aft/transom** and `station=1.0` as **forward/bow**.
- `magnet/kernel/stdlib/section_compiler.py` currently comments and computes the opposite.
- `magnet/hull_gen/geometry.py` documents `HullSection.station` as “0 = AP (aft), 1 = FP (forward)”.

### Minimal fix
Choose the canonical meaning: **0 = AP (aft), 1 = FP (forward)** (matches `HullSection.station` docstring).

Update `magnet/kernel/stdlib/section_compiler.py`:
- **Change** station→x mapping to: `station_m = station_ratio * loa`
- **Update** the surrounding comments/docstring to match.

### Done when
- `station=0.0` compiles to `x_position≈0` (aft) and `station=1.0` compiles to `x_position≈loa` (forward).
- Any “forward vs aft” splits used by observables/targets align with actual bow/stern consistently.

### Estimated time
30–60 minutes (+ quick regression run).

---

## Pre-step (Truthfulness Hotfix) — Close HARD-chine proxy gaming (must do before trusting bottom observables)

### Problem
The bottom observables (notably `section_metric:deadrise_deg_at_chine` and derived `longitudinal_metric:deadrise_drop_deg`) currently anchor on:
- chine = most outboard **HARD** point.

In practice, the generator can place a single HARD marker at an arbitrary point (not the chine knee), and the observable will measure **keel → arbitrary point**. This can produce absurd values (e.g. `deadrise_drop_deg ≈ 24°`) that “pass” thresholds while violating the intent.

This is **proxy gaming**, not a station-mapping problem.

### Fix A1 (hotfix; measurement-time anchoring)
Interpret “chine” using a consistent **geometric anchor** rather than trusting HARD placement:

**Heuristic (v0.4.x)**
- For each section:
  1) Identify a band near `z=0` (baseline/waterline proxy): \(|z - 0.0| <= z_band\)
  2) Choose the max-y point within that band as `P_chine_like`
  3) Use `P_chine_like` (instead of HARD) for deadrise measurement

**Parameters**
- `z_band`: start with something conservative (e.g. 0.25m) and tune from distributions.

### Truth-spine note (explicit)
Yes: this shifts from “measure what the model said” toward “measure what we think it meant.”  
Acceptable as a hotfix because it restores a stable ruler. The long-term cleaner variant is A2 (explicit chine track primitive/indices), but that is out of v0.4 scope.

### Fix B (debugging; not sufficient alone)
Persist `metadata.vessel_thinking_pass` + hash so each run is auditable (binding_table, DEFAULTED vs VERIFIED DOFs).

### Fix C (defense in depth)
Add a `longitudinal_metric:chine_presence_coverage` observable (fraction of stations where the chine-like anchor is measurable) and allow prompts claiming “crisp chine” to require coverage.

### Done when
- `deadrise_deg_at_chine` produces plausible values on real runs (no 60°+ spikes from arbitrary anchors unless geometry truly implies it).
- `deadrise_drop_deg` falls into a plausible band for typical planing hulls (not tens of degrees).

### Estimated time
- Fix A1: 1–2 hours
- Fix B: ~30 minutes
- Fix C: ~1 hour

---

## Pre-step (Contract completeness) — Enforce magnitude, not just “existence”

### Problem
Even with profile/topside observables available, you can still get visually “flat” results if:
- targets are set too low (non-zero but negligible)
- we only check “varies” rather than “varies enough”
- the thinking pass isn’t persisted, so we can’t confirm bindings/DEFAULTED DOFs

### Fix D (medium-term, minimal schema): add value bounds to `ObservationTarget`
Add optional fields (backward compatible):
- `threshold_min: Optional[float] = None`
- `threshold_max: Optional[float] = None`

Validation semantics:
- For `longitudinal_metric:*` (single-valued): enforce bounds on `value`
  - `threshold_min <= value <= threshold_max` (when provided)
- For `section_metric:*` (series): keep `span_min` for “variation exists”; future v0.5 can add an `aggregate` selector if needed.

### Fix E (scale invariance): add LOA-normalized ratio observables
Add ratio observables so “dramatic vs subtle” scales with vessel size:
- `longitudinal_metric:sheer_rise_ratio = sheer_rise_m / loa`
- `longitudinal_metric:entry_fineness_ratio = entry_fineness_p95 * loa` (dimensionless proxy)

### Fix F (required for audit): persist thinking pass artifacts
Make persistence of:
- `metadata.vessel_thinking_pass`
- `metadata.vessel_thinking_pass_hash`
non-optional so we can confirm what was actually bound and what was DEFAULTED.

### Done when
- Prompts claiming “dramatic sheer” or “fine entry” cannot pass with negligible magnitude.
- Bounds/ratios prevent absurdly small (or absurdly large) values from satisfying targets.
- Every run is auditable via persisted thinking pass artifacts.

### Estimated time
- Fix D: 1–2 hours (schema + validator + tests)
- Fix E: 1–2 hours (observables + tests)
- Fix F: 30–60 minutes (persistence wiring + test)

## v0.4 Observable additions (keep scope minimal: 3 rulers)

### Non-negotiable constraints
- **No hull-type priors** (no “Viking signature” language; no templates)
- **Open DOFs, closed observables** (`VALID_OBSERVABLE_IDS`)
- **Station-range scoping** uses v0.3 `ObservationTarget.station_range` (regional intent without templates)

### Observable 1 — `longitudinal_metric:sheer_rise_m`
**What it measures**: deck-edge rise along length (proxy via `section_metric:sheer_z_m`).

**Definition**
- Per section: `sheer_z_m` already exists.
- Over stations (optionally scoped): `sheer_rise_m = max(sheer_z) - min(sheer_z)`.

**Applies to**
- Any vessel with a meaningful sheer/deck-edge profile.

### Observable 2 — `longitudinal_metric:entry_fineness_p95`
**What it measures**: bow-region narrowing rate (proxy for “entry shape” without waterline solving).

**Definition (proxy)**
- Use `section_metric:max_half_beam_m` (existing) as a breadth proxy.
- In the selected station_range (usually forward), compute \(p95(|d(half\_beam)/dx|)\).
- Higher values indicate faster narrowing (finer entry in that region).

**Applies to**
- Any vessel with a bow and a varying breadth profile.

### Observable 3 — `section_metric:topside_angle_deg_above_chine` (renamed from flare-specific framing)
**What it measures**: topside angle above a breakline (proxy for flare/tumblehome depending on sign/convention).

**Definition (proxy; hard‑chine v0.4)**
- Find chine point using existing HARD semantics (most outboard HARD point).
- Select a point above chine (e.g., at the 80th percentile of z range).
- Compute the local topside segment direction in y–z; convert to an angle vs vertical (or vs horizontal) consistently.
- Return angle in degrees.

**Notes**
- If chine is not measurable (no HARD points), return `None` (unmeasurable in v0.4).
- Round-bilge variant can be a later v0.5 extension; do not add now.

**Applies to**
- Any hull where a breakline is explicitly modeled as HARD (not just sportfishers).

---

## Execution steps (agent-executable; sequential)

## The fix (for hull form only)
If you only care about a valid hull shell (no superstructure), the minimal required stack is:
1. **Fix A1**: robust chine anchoring for bottom measurements (closes proxy gaming)
2. **Fix D/E**: magnitude calibration (`threshold_min/max` and LOA-normalized ratios)
3. **Fix F**: persist thinking pass so you can verify binding coverage (bottom + profile)

### Step 0 — Fix A1: close HARD-chine proxy gaming (do first; restores bottom truthfulness)
- **Files to modify**: `magnet/agents/geometry_observables.py`
- **Exact change**:
  - Update `section_metric:deadrise_deg_at_chine` to use a chine-like geometric anchor near `z=0` (band + max-y), not `edge_type==HARD`.
  - Keep HARD-based logic as a fallback only if desired (documented), but the default should be geometric anchoring for robustness.
- **Done-when**: the `deadrise_drop_deg` values in real runs are plausible and no longer trivially gamed by HARD placement.
- **Estimated time**: 60–120m

### Step 1 — Fix station mapping (do after Step 0; correctness)
- **Files to modify**: `magnet/kernel/stdlib/section_compiler.py`
- **Exact change**: station→x mapping and comments/docstring alignment.
- **Done-when**: `station` meaning matches `HullSection.station` docstring end-to-end.
- **Estimated time**: 30–60m

### Step 2 — Add observable ids + implementations
- **Files to modify**: `magnet/agents/geometry_observables.py`
- **Exact change**
  - Add to `VALID_OBSERVABLE_IDS`:
    - `longitudinal_metric:sheer_rise_m`
    - `longitudinal_metric:entry_fineness_p95`
    - `section_metric:topside_angle_deg_above_chine`
  - Implement:
    - `section_metric:topside_angle_deg_above_chine` in `_metric_for_section`
    - the two longitudinal metrics in `_longitudinal_metric_for_body`
- **Done-when**: observables compute deterministically in dry-run for typical hulls.
- **Estimated time**: 60–120m

### Step 3 — Validator / station_range
- **Files to modify**: none required structurally (v0.3 station_range scoping is already implemented).
- **Optional**: update minimum-sample requirements if needed for new longitudinal metrics.
- **Done-when**: new observables can be used in `binding_table` + `observation_targets` (including `station_range`).
- **Estimated time**: 0–30m

### Step 4 — Prompt guidance (vessel-neutral)
- **Files to modify**: `magnet/agents/geometry_proposer.py` (system prompt text)
- **Exact change (guidance language)**
  - Replace sportfisher-coded phrasing with vessel-neutral rule:
    - “Profile and topside DOFs (sheer, entry shape, flare/tumblehome, freeboard progression) should bind to corresponding observables when claimed.”
  - Keep the existing “NO PRIORS” contract and `station_range` capability note.
- **Done-when**: normal user language about silhouette/entry/topside naturally yields bindings/targets (no user DOF talk).
- **Estimated time**: 15–30m

### Step 5 — Fix D/E/F (magnitude bounds + ratios + persistence)
- **Fix D (bounds)**:
  - Extend `ObservationTarget` with `threshold_min` / `threshold_max`
  - Update validator to enforce bounds for `longitudinal_metric:*`
- **Fix E (ratios)**:
  - Add LOA-normalized ratio observables for scale invariance (e.g., `sheer_rise_ratio`)
- **Fix F (persistence)**:
  - Persist thinking-pass artifacts so binding coverage is always inspectable
- **Done-when**:
  - “dramatic sheer / fine entry / strong flare” prompts cannot pass with negligible magnitudes
  - runs are auditable: you can confirm bottom + profile bindings and targets post-hoc
- **Estimated time**: 3–5 hours total (bounded work; can be split)

---

## Test Plan (v0.4)

### New tests to add
- `tests/agents/test_profile_topside_observables_v04.py`
  - **PASS/FAIL** for `sheer_rise_m`
  - **PASS/FAIL** for `entry_fineness_p95` (forward-scoped)
  - **PASS/FAIL** for `topside_angle_deg_above_chine` (section-level, forward-scoped)

### Must-pass regressions
- `tests/agents/test_hull_character_observables_v02.py`
- `tests/agents/test_hull_character_flow_v02.py`
- `tests/agents/test_hull_character_observables_v03_station_range.py`
- `tests/agents/test_vessel_thinking_binding_table.py`
- `tests/agents/test_vessel_thinking_pass_validation.py`

---

## Acceptance (UI behavior)
Given a normal user prompt that mentions overall silhouette/topside intent (without DOF talk), the model should:
- bind those claims to measurable **profile/topside observables**
- optionally scope them with `station_range` (e.g., “forward region”)
- fail-closed (one retry) if the generated geometry does not actually satisfy the claimed targets.

