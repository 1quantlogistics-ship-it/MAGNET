# Module 65.1: Broad-First Intent Resolution

**Status**: Complete
**Branch**: `module-65-intent-preview-endpoint`
**Commits**: `c773b8a`, `fdcfcd0`, `59c6fe7`

---

## 1. What Module 65.1 Enables

### Broad-First Natural Language Input
Users can describe a vessel in one sentence:
```
60m aluminum catamaran ferry beam 12m draft 3m 25 knots
```

The system extracts **7 parameters** from this single input:
- `hull.loa = 60.0 m`
- `hull.beam = 12.0 m`
- `hull.draft = 3.0 m`
- `mission.max_speed_kts = 25.0 kts`
- `hull.hull_type = catamaran`
- `structural_design.hull_material = aluminum`
- `mission.vessel_type = ferry`

### Compound Preview Response
The `/intent/preview` endpoint returns:
- `proposed_actions` — All extracted parameters
- `approved` — Actions that passed validation
- `missing_required` — Gate dependencies not yet satisfied
- `unsupported_mentions` — Recognized concepts without schema fields (e.g., "pods")
- `intent_status` — `complete` | `partial` | `blocked`
- `apply_payload` — Ready-to-submit payload for `/actions`

### Hypothetical Gate Evaluation
Gate checks run against a **read-only overlay** of proposed values:
- No mutation occurs during preview
- Existing `GATE_CONDITIONS` and `GateCondition.evaluate()` are reused
- `design_version` is unchanged until explicit apply

### Single Atomic Apply
User confirms with `apply` → one POST to `/actions` → atomic transaction.

---

## 2. What Changed (Technical)

### Backend (`magnet/deployment/api.py`)

**HypotheticalStateView** (lines 132-170)
```python
class HypotheticalStateView:
    """Read-only overlay for gate checking without mutation."""
    def __init__(self, real_state_manager, proposed_actions):
        self._overlay = {a.path: a.value for a in proposed_actions if a.action_type == ActionType.SET}

    def get(self, path, default=None):
        return self._overlay.get(path) or self._real.get(path, default)
```

**check_gates_on_hypothetical()** — Reuses existing gate engine with overlay state.

### Parser (`magnet/deployment/intent_parser.py`)

**extract_compound_intent()** — Multi-pass extraction:
1. Explicit patterns (`set X to Y`)
2. Numeric patterns with keyword disambiguation (`beam 12m` → `hull.beam`)
3. Enum mentions (`catamaran` → `hull.hull_type`)

**Numeric Disambiguation Fix** (commit `59c6fe7`):
```
"60m beam 12m draft 3m"
→ hull.loa = 60.0 (no keyword → default)
→ hull.beam = 12.0 (keyword: "beam")
→ hull.draft = 3.0 (keyword: "draft")
```

Keyword matches are prioritized over context-based fallbacks.

### Schema (`magnet/core/refinable_schema.py`)

**Enum Fields Added**:
- `hull.hull_type` — monohull, catamaran, trimaran, swath, etc.
- `structural_design.hull_material` — aluminum, steel, composite, frp, etc.
- `mission.vessel_type` — ferry, patrol, workboat, yacht, etc.

### UI (`magnet/ui_v2/js/backend-adapter.js`)

**Compound Display** (lines 374-434):
```
MAGNET understood:
  hull.loa: 60 m
  hull.hull_type: catamaran
  ...

MAGNET needs:
  ○ hull.beam: Beam must be positive
  ...

MAGNET can't yet model:
  "160 pods" → ext.payload.pods

Type "apply" to execute, or add missing fields
```

---

## 3. What Did NOT Change

| Component | Status |
|-----------|--------|
| Kernel execution path | Unchanged |
| ActionExecutor | Unchanged |
| ActionPlanValidator | Unchanged (used for preview validation) |
| PhaseMachine | Unchanged |
| GateCondition logic | Reused via HypotheticalStateView |
| Mutation rules | Unchanged (preview is read-only) |
| WebSocket protocol | Unchanged |
| GLB export | Unchanged |

**Invariant**: Preview is read-only. Execution is atomic and kernel-owned.

---

## 4. Running the API (Required)

> **The MAGNET API MUST be started via the DI bootstrap.**
> Running with uvicorn directly will fail due to missing StateManager.

### Correct

```bash
python3 -m magnet.bootstrap.app run-api
```

### Incorrect (DO NOT USE)

```bash
# This will NOT work - StateManager unavailable
uvicorn magnet.deployment.api:app --port 8000
```

### Serving the UI

```bash
cd magnet/ui_v2
python3 -m http.server 8080
```

Open: `http://localhost:8080/?design=<DESIGN_ID>&debug=true`

---

## 5. Demo Loop (Verified)

### Golden Path

```
1. Type: "60m aluminum catamaran ferry beam 12m draft 3m 25 knots"

2. Preview response shows:
   - MAGNET understood: 7 parameters
   - MAGNET needs: (any missing gates)
   - MAGNET can't model: (unsupported concepts)

3. Type: "apply"

4. Actions execute atomically, design_version increments

5. Hull phase auto-runs (if hull params changed)

6. GLB geometry loads in 3D viewport
```

### curl Verification

```bash
# Create design
DESIGN_ID=$(curl -s -X POST http://localhost:8000/api/v1/designs \
  -H "Content-Type: application/json" \
  -d '{"name": "Demo Ferry"}' | jq -r '.design_id')

# Preview compound intent
curl -s -X POST "http://localhost:8000/api/v1/designs/${DESIGN_ID}/intent/preview" \
  -H "Content-Type: application/json" \
  -d '{"text": "60m aluminum catamaran ferry beam 12m draft 3m 25 knots", "mode": "compound"}' \
  | jq '.proposed_actions | length'
# Expected: 7
```

---

## 6. Files Modified

| File | Change |
|------|--------|
| `magnet/deployment/api.py` | HypotheticalStateView, check_gates_on_hypothetical(), compound preview |
| `magnet/deployment/intent_parser.py` | extract_compound_intent(), keyword disambiguation |
| `magnet/core/refinable_schema.py` | Enum fields (hull_type, material, vessel_type) |
| `magnet/kernel/action_validator.py` | Enum validation support |
| `magnet/ui_v2/js/backend-adapter.js` | Compound mode display |
| `tests/unit/test_compound_intent.py` | 13 gate reuse + extraction tests |

---

## 7. Commits

| Hash | Description |
|------|-------------|
| `8edadf6` | Base /intent/preview endpoint |
| `c773b8a` | Module 65.1 compound intent with HypotheticalStateView |
| `fdcfcd0` | UI compound display + TypeScript types |
| `59c6fe7` | Numeric extraction disambiguation fix |

---

## 8. Known Limitations

1. **Unsupported concepts** (pods, containers, vehicles) are detected but not actionable until ext.* namespaces are implemented.

2. **Numeric fallback** defaults to `hull.loa` when no keyword is present. Users should use keywords for clarity: `"beam 12m"` not just `"12m"`.

3. **Phase auto-run** only triggers for hull and propulsion paths. Other phases require manual execution.

---

**Author**: Claude
**Date**: 2025-12-19
**Module Status**: Complete
