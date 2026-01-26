## Character Observables Activation — Audit & Fix Guide

### Scope

This document audits the **current activation wiring** for Character Observables + Shape Document and provides an **implementation guide** for fixes to:

- **Enum creep** in profile selection
- **CREATE-mode gate** that prevents target profiles from applying
- **Debug endpoint not visible** due to server lifecycle
- **EDIT-mode glitches** caused by unsafe control mappings

This is deliberately written as an **agent-executable plan** with concrete ownership, file targets, and acceptance tests.

---

## Confirmed Problems (Receipts)

### 1) Enum creep — YES (Law 3 violation)

The current profile selection uses a closed mapping:

```python
mapping = {
  "sportfisher": "viking_sportfisher",
  "viking": "viking_sportfisher",
  ...
}
```

This is functionally an enum: **new vessel type ⇒ code change**.

#### Where it lives

- `magnet/kernel/shape_document.py` contains both:
  - a hardcoded `TARGET_PROFILES` dict (code-owned, not data-owned)
  - `infer_profile_from_vessel_type()` mapping (closed set)

---

### 2) CREATE is broken — wrong gate (and wrong concept)

CREATE tries to infer the profile from state:

```python
vessel_type = state.get("hull", {}).get("hull_type", "")  # empty on CREATE
target_profile_id = infer_profile_from_vessel_type(vessel_type)  # None
```

On CREATE there is typically no `hull.hull_type` yet, so **no target constraints are injected**.

More fundamentally (North Star): even if this gate worked, **looking up a "Viking profile" is still enumeration**. The kernel should not encode “Viking-like” as a type or a preset; style knowledge lives in the LLM.

---

### 3) `/debug/last-edit` endpoint 404

If the endpoint was added in code but returns router-level 404, the running server is serving an **older process** / not restarted.

Root cause: server lifecycle / restart command.

---

### 4) EDIT glitches after first iteration

Symptoms observed:

- first ADJUST works (e.g. forward beam scaling for sharper entry)
- later ADJUSTes (sheer / transom) produce geometry glitches (degenerate mesh, kinks, collapse)

Likely causes:

- **single-point moves** on polylines create sharp kinks
- **witness indices** become stale after earlier edits
- **no min-distance / monotonicity enforcement** post-edit
- no “fail closed” rollback when edits create invalid sections

---

## Implementation Guide (Proposed Fixes)

### Goal State (North Star alignment)

This must satisfy **MAGNET North Star**: "Viking-like is not a type" and **Law 3: Non‑Enumeration**.

- **Kernel has no vessel-type presets**:
  - remove any closed mapping (enum, keyword matching, "brand list")
  - new vessel styles require **zero code**
- **LLM expresses style knowledge as observable targets**:
  - model emits `TARGET ...` statements for observables it believes define the request
  - kernel executes targets mechanically and validates
- **Profiles are optional examples, not a registry**:
  - keep "example profiles" only as prompt reference docs (and optionally as user-provided targets)
  - kernel must not "select a profile" based on vessel name/type
- **Control mappings are general, not per-profile**:
  - system prompt contains universal "how to hit observable X" guidance
  - not "Viking needs 11° entry," but "to reduce entry_half_angle_deg, narrow forward half‑beam"
- **EDIT is safe and reversible**:
  - distributed edits (not single-point spikes)
  - witness re-validation
  - strict post-edit validation + rollback
  - explicit REWRITE escape hatch (Law 1/8)

### Responsibility Split (Critical)

| Component | Responsibility |
|-----------|----------------|
| **Shape Document (kernel)** | Computes what's wrong, suggests fixes with **computed deltas**, predicts outcomes |
| **LLM (proposer)** | Reads suggestions, decides to accept/modify/reject, emits final ADJUST/TARGET |
| **Kernel (expander)** | Executes emitted statements mechanically, validates, rolls back if invalid |
| **Prompt mappings** | Training wheels for CREATE (no geometry yet) or novel requests |

**The kernel does the math. The LLM is editorial. The prompt mappings are backup education.**

---

## Fix 1 — Remove enum creep: delete vessel-type inference in kernel

### Design

1) **Delete** `infer_profile_from_vessel_type()` (and any equivalent keyword mapping) from kernel-owned logic paths.
2) Remove any CREATE/EDIT branch that tries to pick a profile based on:
   - `hull.hull_type`
   - prompt keyword matching (“viking”, “trawler”, “bertram”, etc.)
3) If “profiles” exist at all:
   - treat them as **reference examples** the model can read
   - do not treat them as an executable registry used by code to classify vessels

### File-level changes

- `magnet/kernel/shape_document.py`
  - Remove `infer_profile_from_vessel_type()`
  - (Optional) keep `TARGET_PROFILES` only if it is used strictly as:
    - a convenience for explicit `target_profile_id` supplied by user/UI, OR
    - reference examples injected into prompts (not used for inference)

### Acceptance criteria

- “Bertram”, “Hatteras”, “custom racing hull”, etc. require **no new code**
- No code path attempts to map vessel strings → profiles
- All style targeting happens through **LLM-emitted observable TARGETs**

---

## Fix 2 — CREATE/EDIT: model generates targets (no lookup)

### Design

Instead of: user prompt → code lookup → injected profile targets,
use: user prompt → **LLM reasoning** → emitted `TARGET` statements.

**Required behavior:**

1) If the user describes character (“more Viking-like”, “more trawler-ish”, “race-bred”), the **LLM must translate character into measurable targets**:
   - `TARGET longitudinal_metric:entry_half_angle_deg = ... deg`
   - `TARGET profile_metric:transom_beam_ratio = ...`
   - `TARGET longitudinal_metric:sheer_peak_station = ...`
   - etc.
2) If the user provides explicit targets (numbers), the LLM should emit those directly as `TARGET`.
3) If the user doesn’t specify character (pure dimensioning), the LLM may omit targets and focus on geometry creation.

### Profiles become examples, not registry

If you want “Viking-ish defaults,” they should be injected into the **system prompt as optional reference** (“examples of targets for sportfishers”), not selected by code.

### Shape Document computes suggestions; LLM is editorial

**Critical architecture point:** The shape document **MUST keep computing `suggested_adjustments`** with kernel-derived math. The LLM's role is **editorial** (accept/modify/reject), not computational.

```
Shape Document computes:
  - What's wrong (critique_hints)
  - How to fix it (suggested ADJUST with computed delta)
  - Expected outcome (predicted observable change)

LLM decides:
  - Accept suggestion as-is
  - Modify delta/scope ("that's too aggressive, try -0.4m")
  - Reject and try different approach
  - Ask for clarification

Kernel executes:
  - Whatever LLM emits
  - Validates result
  - Rolls back if broken
```

**Example shape document (keep this structure):**

```json
{
  "critique_hints": ["Entry too blunt (18° vs 11° target)"],
  "suggested_adjustments": [
    {
      "observable_id": "section_metric:max_half_beam_m",
      "scope": {"station_range": [0.85, 1.0]},
      "operation": "ADJUST",
      "delta": -0.6,
      "unit": "m",
      "rationale": "Reduces forward beam to sharpen entry",
      "expected_effect": "entry_half_angle_deg: -5° to -7°"
    }
  ]
}
```

**The kernel computes the delta magnitude** (based on current observable value, target, and control sensitivity). The LLM does NOT guess "-0.6m" — it reads the suggestion and decides whether to apply it.

### Prompt mappings are training wheels (backup education)

The system prompt mappings (observable → control knob) are **backup education** for cases where:
- Shape document doesn't have a suggestion (e.g., CREATE mode with no geometry yet)
- LLM needs to reason about a novel request not covered by suggestions

They are NOT the primary mechanism. Shape document suggestions are.

```text
When the user requests a character change, you MUST express it as measurable TARGETs on observables.

General control mappings (how to hit targets — use when shape document lacks suggestions):
- To decrease `entry_half_angle_deg`: decrease `section_metric:max_half_beam_m` in station_range [0.85, 1.0]
- To increase `transom_beam_ratio`: increase `section_metric:max_half_beam_m` in station_range [0.0, 0.15]
- To shift `sheer_peak_station` forward: increase `section_metric:sheer_z_m` in station_range [0.6, 0.8] relative to bow/stern
```

This is **style-agnostic**: it applies to "Viking", "Bertram", "Hatteras", "custom racing hull", etc.

### File-level changes

- `magnet/deployment/spiral_endpoints.py`
  - Remove any attempt to infer profiles from state or prompt
  - Pass shape_document (if available) to proposer in EDIT mode
  - Ensure proposer constraints explicitly request `TARGET` emission when character language is present
- `magnet/agents/geometry_proposer.py`
  - Update system prompt:
    - “When user expresses vessel character, emit TARGET statements for observables that define that character.”
    - Include the general control-mapping guidance (observable → control knob)

### Acceptance criteria

- Run CREATE prompt “72-foot Viking sportfisher…”:
  - model emits TARGETs (visible in program/receipts)
  - geometry trends toward those targets without any kernel lookup
- Run “Bertram-like” / “Hatteras-like”:
  - still generates TARGETs (no keyword mapping needed)

---

## Fix 3 — Debug endpoint visibility: server lifecycle

### Operational steps

The debug endpoint will 404 if the running server was started before the route existed.

Recommended restart (FastAPI/uvicorn path depends on your entrypoint):

```bash
pkill -f "magnet.bootstrap.entrypoints api" || true
pkill -f "uvicorn" || true

# Start (example; adjust to your runbook/entrypoint)
export MAGNET_SPIRAL_ENABLED=true
export MAGNET_LEGACY_INTENT_PROTOCOL_ENABLED=false
export MAGNET_DESIGN_STORE_DIR="storage/designs"
python3 -m magnet.bootstrap.entrypoints api --port 8000 --host 127.0.0.1
```

Verify:

```bash
curl -i "http://127.0.0.1:8000/api/v1/designs/{DESIGN_ID}/debug/last-edit"
```

Expected:
- 200 with `success: true|false` (handler ran)
- not a router-level 404

---

## Fix 4 — EDIT robustness: specify safe control mappings + validation + rollback

### Current risk profile

- `section_metric:max_half_beam_m` scaling is relatively stable (uniform scaling of y)
- `section_metric:sheer_z_m` and transom-related moves are high-risk:
  - moving a single vertex changes local curvature abruptly
  - can create a kink that loft/tessellation amplifies

### Required safeguards

#### 0) Minimum control-theory contracts (v1 blockers)

These are **minimum additions required for v1**. Without them, the system can “work” but will predictably fail in live use (thrash, oscillate forever, or corrupt state).

| Gap | Why it breaks | Fix |
|-----|---------------|-----|
| **Convergence tolerance** | System oscillates forever on coupled observables | Define `tolerance` per observable; stop when within tolerance |
| **Rollback semantics** | Partial failure = corrupted state | Make each ADJUST/TARGET **atomic**: commit all affected sections or none |
| **CREATE gate** | EDIT on placeholder geometry gives garbage signals | Require minimum resolution + hydrostatics gate before EDIT allowed |
| **Sensitivity bounds** | Wild deltas on novel hulls | Clamp computed delta and bound sensitivity impact |

##### Convergence contract (stop condition)

Add this policy to the implementation (used by suggestion loop / “edit-until-converged” orchestration):

```python
# Convergence contract
OBSERVABLE_TOLERANCES = {
    "longitudinal_metric:entry_half_angle_deg": 1.0,  # ±1° is close enough
    "profile_metric:transom_beam_ratio": 0.02,        # ±2% is close enough
    "longitudinal_metric:sheer_peak_station": 0.03,   # ±3% LOA is close enough
}

def is_target_satisfied(observable_id: str, current: float, target: float) -> bool:
    tolerance = OBSERVABLE_TOLERANCES.get(observable_id, 0.05)
    return abs(current - target) <= tolerance
```

Rules:
- Once `is_target_satisfied(...)` is true, stop recommending further edits for that observable.
- If edits push the value past the target and then bounce back (sign-flip in delta), treat as oscillation and trigger:
  - smaller step sizes, or
  - REWRITE offer if persistent.

##### Rollback semantics (atomic ADJUST/TARGET)

Contract:
- **ADJUST is atomic**: all affected sections commit together or all revert.
- **No partial success** within a single ADJUST operation.

Implementation requirements:
- Use a transaction snapshot for all affected resources.
- If any post-edit invariant fails on any affected section, revert the entire group and return an error/receipt.

##### CREATE gate (EDIT mode eligibility)

Do not enter EDIT mode until geometry is sufficiently real for observables to be meaningful.

```python
def can_enter_edit_mode(geometry: HullGeometry) -> tuple[bool, str]:
    if len(geometry.sections) < 5:
        return False, "Need ≥5 sections for EDIT mode"
    if not geometry.hydrostatics_valid:
        return False, "Hydrostatics gate must pass before EDIT"
    return True, ""
```

Rules:
- If `can_enter_edit_mode()` is false, treat “edits” as CREATE/REWRITE with explicit user confirmation if rewriting an existing design.

##### Sensitivity bounds (safety rails)

Sensitivity values are empirical starting points and must be bounded.

Rules:
- Clamp computed control delta to `ObservableSpec.max_delta`.
- Additionally bound sensitivity influence:
  - clamp **effective sensitivity** to within \([0.1x, 10x]\) of the empirical value when computing deltas
  - if observed response deviates beyond bounds, reduce step sizes and/or require clarification.

---

#### A) Replace single-point moves with distributed edits (spec)

**A.1 `section_metric:sheer_z_m` (distributed top-band move — concrete v0 spec)**

Use this exact mapping to avoid implementer “guessing”:

```python
# Points affected: top 3 points by z-index per section
# Weight: linear falloff [1.0, 0.6, 0.3] from top
# Constraint: maintain min 5mm between adjacent points
# Constraint: preserve z-monotonicity in topside region
#
# Implementation sketch:
# - Sort point indices by z descending → pick top3 indices
# - Apply dz * weights to those points' z values
# - Validate:
#   - for all adjacent pairs: distance(yz[i], yz[i+1]) >= 0.005
#   - for "topside region" (the moved points sorted by z): z must remain strictly decreasing
```

**A.2 `section_metric:max_half_beam_m` (uniform y-scale — concrete v0 spec)**

```python
# Points affected: all points in section (uniform y-scale)
# Weight: uniform (scale factor = (current + delta) / current)
# Constraint: no point y < 0
# Constraint: chine witness index preserved
#
# Implementation sketch:
# - Measure current max_half_beam_m = max(y)
# - scale = (current + delta) / current   (fail if current <= eps)
# - For each point: y' = max(0, y * scale)
# - Witness stability:
#   - chine witness index must remain the chine-like index; if it shifts, update cache
```

**A.3 Transom widening (via `section_metric:max_half_beam_m`)**

- Apply over a station range [0.0, 0.15] but with **longitudinal smoothing**:
  - for each affected section j (ordered aft→forward), compute weight:
    - station_norm \(s \in [0,1]\)
    - \(w(s) = \cos^2(\frac{\pi}{2} \cdot \mathrm{clamp}((s-0.0)/0.15, 0, 1))\)
  - effective delta for section = requested_delta * w(s)

#### B) Witness re-validation

After each edit:
- re-measure the section metric
- if witness_index invalid or re-measure selects different region, update cache

#### C) Post-edit invariants (fail closed)

At minimum, validate per edited section:
- no duplicate/near-duplicate consecutive points (min distance)
- no self-intersection in section polyline (if applicable)
- monotonic z ordering expectations preserved (if required by compiler/tessellation)

If failed:
- do not commit state changes
- return a structured error that triggers `needs_clarification` or auto-retry with reduced delta

#### D) Cap deltas dynamically

If requested delta is large:
- subdivide into multiple smaller ADJUST steps
- stop early if validation error appears

#### E) Explicit REWRITE escape hatch (Law 1)

If an observable target is repeatedly unreachable via EDIT (e.g., after N=3 attempts with decreasing deltas) or if edits repeatedly fail validation:

- return `status="needs_clarification"` with:
  - explanation: “Target appears unreachable with identity-preserving ADJUST without corrupting geometry.”
  - options: “Try smaller delta”, “Change scope”, “Approve REWRITE”
- If user approves REWRITE:
  - allow CREATE/LOFT path explicitly
  - preserve only explicitly chosen anchors (IDs/metadata) per policy

**Concrete trigger condition**

Use this exact predicate to decide when to offer REWRITE:

```python
def should_offer_rewrite(edit_attempts: List[EditResult]) -> bool:
    """Offer REWRITE if ADJUST can't converge."""
    if len(edit_attempts) >= 3:
        deltas = [a.remaining_delta for a in edit_attempts[-3:]]
        if all(d > 0.5 * edit_attempts[-3].remaining_delta for d in deltas):
            # Not converging — delta not shrinking
            return True
    if any(a.validation_failed for a in edit_attempts):
        return True
    return False
```

### Logging / receipts (diagnostics contract)

After each ADJUST/TARGET, store:

```json
{
  "op": "ADJUST",
  "observable_id": "section_metric:sheer_z_m",
  "scope": {"station_range":[0.6,0.8]},
  "requested_delta": 0.4,
  "affected_sections": ["sec5","sec6","sec7"],
  "diagnostics": {
    "points_before": {...},
    "points_after": {...},
    "validation_errors": [...]
  }
}
```

This receipt should be retrievable via:
- `GET /api/v1/designs/{design_id}/debug/last-edit`

### Acceptance criteria

Run:
- v2 CREATE Viking
- v3 “Make entry sharper”
- v4 “Widen transom”
- v5 “Raise sheer mid-forward”

Expected:
- no mesh collapse/glitches
- if an edit fails validation, the system returns a clear error and preserves last-good geometry (no corrupted state)

---

## Live Test Protocol (Operator Checklist)

1) Restart server (Fix 3)
2) Create design in UI
3) After each prompt, collect:
   - `/shape-document?target_profile_id=viking_sportfisher`
   - `/debug/last-edit`
4) When a glitch occurs:
   - capture last-edit receipt and compare `points_before`/`points_after`
   - check which operator caused it (`max_half_beam_m` vs `sheer_z_m` etc.)

---

## Open Questions / Decisions (must be resolved before implementing)

- **Profile storage location**: `storage/target_profiles/` vs `docs/target_profiles/` vs both
- **Profile override precedence**:
  - request inline profile should override file profile?
- **Prompt inference policy**:
  - LLM emits TARGETs directly (no profile inference)
- **Validation strictness**:
  - which invariants are hard gates vs soft warnings

---

## System Prompt Addendum (Required)

Add this block verbatim to the geometry proposer system prompt:

```text
OBSERVABLE → CONTROL MAPPINGS (use these for any vessel type):

To decrease entry_half_angle_deg:
  → ADJUST max_half_beam_m AT station_range=(0.85,1.0) BY negative delta

To increase transom_beam_ratio:
  → ADJUST max_half_beam_m AT station_range=(0.0,0.15) BY positive delta

To shift sheer_peak_station aft:
  → ADJUST sheer_z_m AT station_range=(0.5,0.7) BY positive delta

To increase deadrise_progression_shape (more warp):
  → ADJUST deadrise_deg_at_chine AT station_range=(0.7,1.0) BY positive delta

These mappings apply regardless of vessel type. You decide the targets based on what the user describes.
```

---

## Kernel Delta Computation (How `suggested_adjustments` Works)

The shape document's `suggested_adjustments` must include **kernel-computed deltas**, not placeholders. Here's the spec for how to compute them:

### Delta computation formula (per observable)

```python
def compute_suggested_delta(
    observable_id: str,
    current_value: float,
    target_value: float,
    control_sensitivity: float,  # empirical: how much control changes observable
) -> float:
    """
    Compute suggested ADJUST delta to move observable toward target.
    
    Args:
        observable_id: e.g. "longitudinal_metric:entry_half_angle_deg"
        current_value: measured value from geometry
        target_value: desired value
        control_sensitivity: empirical ratio (observable_delta / control_delta)
    
    Returns:
        Suggested delta for the control knob (e.g., -0.6m for max_half_beam_m)
    """
    observable_delta = target_value - current_value
    
    # Invert the sensitivity to get control delta
    # e.g., if reducing beam by 1m reduces entry angle by 10°,
    # then sensitivity = 10 deg/m, and control_delta = observable_delta / 10
    control_delta = observable_delta / control_sensitivity
    
    # Clamp to safe bounds (from ObservableSpec.max_delta)
    max_delta = get_observable_spec(observable_id).max_delta
    control_delta = max(-max_delta, min(max_delta, control_delta))
    
    return control_delta
```

### Sensitivity values (empirical, can be tuned)

| Observable | Control Knob | Sensitivity | Units |
|------------|--------------|-------------|-------|
| `entry_half_angle_deg` | `max_half_beam_m` (0.85-1.0) | ~12 deg/m | °/m |
| `transom_beam_ratio` | `max_half_beam_m` (0.0-0.15) | ~0.15 /m | ratio/m |
| `sheer_peak_station` | `sheer_z_m` (0.5-0.8) | ~0.1 /m | station/m |
| `deadrise_progression_shape` | `deadrise_deg_at_chine` (0.7-1.0) | ~0.05 /deg | warp/° |

These sensitivities are hull-dependent; the table provides starting values. The kernel can refine them per-hull based on geometry (e.g., LOA, beam).

### Expected effect estimation

```python
def estimate_effect(
    observable_id: str,
    suggested_delta: float,
    control_sensitivity: float,
) -> str:
    """Estimate observable change from suggested delta."""
    expected_change = suggested_delta * control_sensitivity
    sign = "+" if expected_change > 0 else ""
    return f"{sign}{expected_change:.1f}"
```

This populates `suggested_adjustments[].expected_effect` for LLM review.

---

## CRITICAL: Fix `_generate_suggested_adjustments()` — Currently Broken

**Audit finding:** The current implementation uses rough unit-based scaling (`* 0.1`, `* 10`) instead of a proper sensitivity table. This breaks "kernel does the math, LLM is editorial."

### Current (broken) — lines 403-409 in `shape_document.py`:

```python
# Estimate delta for controllable observable
# (simplified: use same delta magnitude, may need scaling)
ctrl_delta = comp.delta
if ctrl_spec.unit == "m" and spec.unit == "deg":
    ctrl_delta = comp.delta * 0.1  # Rough scaling  ← WRONG
elif ctrl_spec.unit == "deg" and spec.unit == "ratio":
    ctrl_delta = comp.delta * 10  # Rough scaling   ← WRONG
```

### Fix: Add sensitivity table + `compute_suggested_delta()`

Add this to `magnet/kernel/shape_document.py`:

```python
CONTROL_SENSITIVITIES = {
    # observable_id: (control_knob, sensitivity, unit_desc)
    "longitudinal_metric:entry_half_angle_deg": ("section_metric:max_half_beam_m", 12.0, "deg/m"),
    "profile_metric:transom_beam_ratio": ("section_metric:max_half_beam_m", 0.15, "ratio/m"),
    "longitudinal_metric:sheer_peak_station": ("section_metric:sheer_z_m", 0.1, "station/m"),
    "longitudinal_metric:deadrise_progression_shape": ("section_metric:deadrise_deg_at_chine", 0.05, "warp/deg"),
}

def compute_suggested_delta(
    observable_id: str,
    current_value: float,
    target_value: float,
    max_delta: float,
) -> tuple[float, str]:
    """
    Compute control delta from sensitivity table.
    Returns (delta, expected_effect_str).
    """
    if observable_id not in CONTROL_SENSITIVITIES:
        return (0.0, "unknown")
    
    _, sensitivity, unit_desc = CONTROL_SENSITIVITIES[observable_id]
    observable_delta = target_value - current_value
    control_delta = observable_delta / sensitivity
    
    # Clamp
    control_delta = max(-max_delta, min(max_delta, control_delta))
    
    # Expected effect
    expected_change = control_delta * sensitivity
    sign = "+" if expected_change > 0 else ""
    expected_effect = f"{sign}{expected_change:.1f}"
    
    return (control_delta, expected_effect)
```

### Fix: Update `_generate_suggested_adjustments()` to use it

Replace the rough scaling block with:

```python
# OLD (bad)
ctrl_delta = comp.delta
if ctrl_spec.unit == "m" and spec.unit == "deg":
    ctrl_delta = comp.delta * 0.1
elif ctrl_spec.unit == "deg" and spec.unit == "ratio":
    ctrl_delta = comp.delta * 10

# NEW (good)
ctrl_delta, expected_effect = compute_suggested_delta(
    observable_id=obs_id,
    current_value=comp.current,
    target_value=comp.target,
    max_delta=ctrl_spec.max_delta,
)
```

### Fix: Add `expected_effect` to `SuggestedAdjustment`

Update the dataclass:

```python
@dataclass
class SuggestedAdjustment:
    observable_id: str
    scope: Dict[str, Any]
    operation: str
    delta: Optional[float]
    value: Optional[float]
    unit: str
    rationale: str
    expected_effect: str = ""  # ← ADD THIS FIELD
```

And populate it when building suggestions:

```python
suggestions.append(SuggestedAdjustment(
    observable_id=ctrl_obs,
    scope=scope,
    operation="ADJUST",
    delta=round(ctrl_delta, 2) if ctrl_delta else None,
    value=None,
    unit=ctrl_spec.unit,
    rationale=rationale,
    expected_effect=expected_effect,  # ← ADD THIS
))
```

### Why this matters

| Before | After |
|--------|-------|
| LLM sees: "ADJUST max_half_beam BY -0.7m" (guessing) | LLM sees: "ADJUST max_half_beam BY -0.58m → expected: -7.0°" (actionable) |
| Kernel does rough scaling | Kernel does real math from sensitivity table |
| LLM must infer expected outcome | Expected outcome is computed and shown |

**This is ~30 lines and critical.** Without it, "kernel does the math, LLM is editorial" is a lie.

---

## Missing Control Mapping (Must Be Added)

The system also needs a concrete mapping for `section_metric:deadrise_deg_at_chine`:

```python
# Points affected: keel to chine (indices 0 to witness_index)
# Method: rotate bottom segment about keel point
# Constraint: chine point y preserved (pivot rotation)
# Constraint: no segment inversion
#
# Implementation sketch:
# - Identify keel index and chine witness index
# - Treat segment keel→chine as a vector; rotate in y–z plane about keel so that beta matches target
# - Keep chine.y constant; solve for chine.z consistent with tan(beta)=|dz|/|dy|
# - Apply rotation to intermediate points between keel and chine
# - Validate no inversion (z ordering and no self-crossing in the bottom region)
```

