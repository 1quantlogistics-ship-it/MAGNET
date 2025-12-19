# MAGNET Module 65.1: Broad-First Intent Resolution (v6)

## Implementation Status: COMPLETE ✓

**All phases implemented and tested (2025-12-19):**

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | HypotheticalStateView class | ✅ Complete |
| 2 | check_gates_on_hypothetical() | ✅ Complete |
| 3 | extract_compound_intent() | ✅ Complete |
| 4 | Compound preview endpoint | ✅ Complete |
| 5 | Mandatory gate reuse tests (13/13 pass) | ✅ Complete |
| 5b | Enum type support (hull_type, material, vessel_type) | ✅ Complete |
| 6 | UI compound display | ✅ Complete |

**Files Modified:**
- `magnet/deployment/api.py` - HypotheticalStateView, check_gates_on_hypothetical(), compound preview
- `magnet/deployment/intent_parser.py` - extract_compound_intent(), enum mappings, unsupported detection
- `magnet/core/refinable_schema.py` - enum type support, 3 new enum fields
- `magnet/kernel/action_validator.py` - enum validation
- `magnet/ui_v2/js/backend-adapter.js` - compound mode display
- `tests/unit/test_compound_intent.py` - 13 tests for gate reuse + extraction

**Terminal Output Example:**
```
> 60m aluminum catamaran ferry for 160 pods

MAGNET understood:
  hull.loa: 60 m
  hull.hull_type: catamaran
  structural_design.hull_material: aluminum
  mission.vessel_type: ferry

MAGNET needs:
  ○ hull.beam: Beam must be positive
  ○ hull.draft: Draft must be positive

MAGNET can't yet model:
  "160 pods" → ext.payload.pods

Type "apply" to execute, or add missing fields
```

---

## Design Philosophy

> "No-friction, broad-first, chat-based design that narrows toward precision."

The current v5 plan was **correct scaffolding** — deterministic, auditable, kernel-safe. This evolution preserves those guarantees while unlocking a UX where users can speak naturally and receive coherent proposals.

**Key insight**: The parser can remain single-action internally while the *interpretation layer* bundles multiple extractions into a compound preview. Kernel integrity is preserved because all mutation still flows through ActionExecutor after explicit user confirmation.

---

## Control Plane Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INPUT                                         │
│              "60m aluminum catamaran cargo ferry for 160 pods"               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    INTERPRETATION PHASE (Broad, Permissive)                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Multi-Pass Extraction                                                    ││
│  │  • Run parser multiple times with text fragments                        ││
│  │  • Extract: 60m → hull.loa, catamaran → hull.hull_type, etc.           ││
│  │  • Collect: all recognized patterns, all enum matches                   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Feasibility Check (Read-Only Kernel Query)                              ││
│  │  • Create hypothetical state copy                                       ││
│  │  • Apply proposed actions to copy                                       ││
│  │  • Run gate checks: what's still missing?                               ││
│  │  • No mutation, no physics run                                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Unsupported Concept Detection                                           ││
│  │  • Detect mentions with no schema path (e.g., "pods")                   ││
│  │  • Flag for user awareness, not silent drop                             ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COMPOUND PREVIEW RESPONSE                            │
│                                                                              │
│  proposed_actions: [{hull.loa: 60}, {hull.hull_type: catamaran}, ...]       │
│  missing_required: [{hull.beam}, {hull.draft}]                              │
│  unsupported_mentions: [{pods: no_field}]                                   │
│  intent_status: partial                                                      │
│  apply_payload: {...}                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
            ┌──────────────┐               ┌──────────────┐
            │ User Edits   │               │ User Applies │
            │ (Optional)   │               │ (Confirm)    │
            └──────────────┘               └──────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    EXECUTION PHASE (Strict, Authoritative)                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ ActionValidator                                                          ││
│  │  • Validate each action against REFINABLE_SCHEMA                        ││
│  │  • Clamp values, reject invalid                                         ││
│  │  • Return approved/rejected split                                        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ ActionExecutor                                                           ││
│  │  • Begin transaction                                                     ││
│  │  • Execute approved actions atomically                                  ││
│  │  • Increment design_version                                              ││
│  │  • Commit                                                                ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Phase Execution (Optional, User-Triggered)                               ││
│  │  • Run hull_form, structure, etc.                                       ││
│  │  • Generate physics outputs                                              ││
│  │  • Create snapshot, export geometry                                      ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Broad-First → Narrow-Later Flow

### Phase 1: Broad Interpretation

User says anything. System extracts everything it can.

```
Input: "60m aluminum catamaran cargo ferry for 160 pods"

Extraction:
  ✓ hull.loa = 60.0 (from "60m")
  ✓ hull.hull_type = "catamaran" (from "catamaran")
  ✓ structural_design.hull_material = "aluminum" (from "aluminum")
  ✓ mission.vessel_type = "ferry" (from "ferry")
  ? mission.cargo_capacity_mt = ??? (from "cargo" - needs value)
  ✗ pods = 160 (no schema field exists)
```

### Phase 2: Feasibility Check

Query kernel truth sources (read-only):

```
Hypothetical state after proposed actions:
  hull.loa = 60.0 ✓
  hull.hull_type = "catamaran" ✓
  hull.beam = None ✗ (required for hull_form)
  hull.draft = None ✗ (required for hull_form)
  structural_design.hull_material = "aluminum" ✓

Gate check (hull_form):
  - loa_set: PASS
  - beam_set: FAIL → "Beam must be specified"
  - draft_set: FAIL → "Draft must be specified"
```

### Phase 3: Compound Preview

Return one coherent proposal:

```json
{
  "intent_mode": "compound",
  "proposed_actions": [
    {"path": "hull.loa", "value": 60.0, "unit": "m", "source": "extracted"},
    {"path": "hull.hull_type", "value": "catamaran", "source": "extracted"},
    {"path": "structural_design.hull_material", "value": "aluminum", "source": "extracted"},
    {"path": "mission.vessel_type", "value": "ferry", "source": "extracted"}
  ],
  "missing_required": [
    {"path": "hull.beam", "phase": "hull_form", "reason": "Beam must be specified", "suggestion": "typical: 8-15m for 60m vessel"},
    {"path": "hull.draft", "phase": "hull_form", "reason": "Draft must be specified", "suggestion": "typical: 2-4m"}
  ],
  "unsupported_mentions": [
    {"text": "160 pods", "concept": "pod_count", "status": "no_schema_field", "future": "ext.payload.pods"}
  ],
  "intent_status": "partial",
  "apply_payload": {
    "actions": [
      {"action_type": "set", "path": "hull.loa", "value": 60.0},
      {"action_type": "set", "path": "hull.hull_type", "value": "catamaran"},
      {"action_type": "set", "path": "structural_design.hull_material", "value": "aluminum"},
      {"action_type": "set", "path": "mission.vessel_type", "value": "ferry"}
    ]
  }
}
```

### Phase 4: User Confirms

UI shows:
```
┌─────────────────────────────────────────────────────────────────┐
│ I found 4 parameters in your description:                       │
│                                                                  │
│   ✓ Length: 60m                                                 │
│   ✓ Hull type: catamaran                                        │
│   ✓ Material: aluminum                                          │
│   ✓ Vessel type: ferry                                          │
│                                                                  │
│ To run hull_form, I also need:                                  │
│   ○ Beam: [________] m  (typical: 8-15m)                        │
│   ○ Draft: [________] m  (typical: 2-4m)                        │
│                                                                  │
│ Note: "160 pods" recognized but not yet supported (ext.*)       │
│                                                                  │
│              [Apply 4 Parameters]  [Edit Values]                │
└─────────────────────────────────────────────────────────────────┘
```

User can:
1. **Apply now** → 4 actions executed, still need beam/draft before phase runs
2. **Fill missing** → Add beam=12m, draft=3m, then apply 6 actions
3. **Edit** → Change any proposed value before applying

### Phase 5: Single Apply

User clicks Apply. One POST to /actions with all approved actions.

```
POST /actions
{
  "actions": [
    {"action_type": "set", "path": "hull.loa", "value": 60.0},
    {"action_type": "set", "path": "hull.hull_type", "value": "catamaran"},
    {"action_type": "set", "path": "structural_design.hull_material", "value": "aluminum"},
    {"action_type": "set", "path": "mission.vessel_type", "value": "ferry"},
    {"action_type": "set", "path": "hull.beam", "value": 12.0},
    {"action_type": "set", "path": "hull.draft", "value": 3.0}
  ]
}
```

Kernel validates. Kernel executes. One transaction. One version bump.

---

## Two-Phase Interpretation Model

| Aspect | Interpretation Phase | Execution Phase |
|--------|---------------------|-----------------|
| **Purpose** | Extract, propose, clarify | Validate, mutate, commit |
| **Permissiveness** | Broad, over-proposes | Strict, prunes invalid |
| **Kernel Access** | Read-only (state copy, gate checks) | Read-write (transaction, commit) |
| **Physics** | Feasibility reasoning only | Authoritative outputs |
| **User Action** | Review, edit, confirm | None (atomic) |
| **Failure Mode** | "I couldn't parse X" | "Action rejected: reason" |

**Key principle**: Interpretation can be wrong. Execution cannot be.

---

## Multi-Pass Extraction Strategy

The parser remains single-action internally. The interpretation layer runs it multiple times:

```python
def extract_compound_intent(text: str) -> CompoundIntent:
    """
    Extract all recognizable parameters from broad user input.
    Parser is single-action; we run it on fragments.
    """
    proposed = []
    remaining_text = text.lower()

    # Pass 1: Explicit patterns ("set X to Y")
    while True:
        action = _try_set_pattern(remaining_text)
        if not action:
            break
        proposed.append(action)
        remaining_text = remove_matched_fragment(remaining_text, action)

    # Pass 2: Implicit numeric patterns ("60m", "12 meters")
    for match in find_all_numeric_patterns(remaining_text):
        action = _try_implicit_set(match)
        if action and action not in proposed:
            proposed.append(action)

    # Pass 3: Enum values ("catamaran", "aluminum")
    for enum_value in find_all_enum_mentions(remaining_text):
        action = create_enum_action(enum_value)
        if action and action not in proposed:
            proposed.append(action)

    # Detect unsupported concepts
    unsupported = detect_unsupported_mentions(remaining_text, proposed)

    return CompoundIntent(
        proposed_actions=proposed,
        unsupported_mentions=unsupported,
    )
```

**This preserves single-action parser internals** while enabling compound extraction at the interpretation layer.

---

## Compound Preview Response Schema

```python
@dataclass
class CompoundPreviewResponse:
    """Response from /intent/preview in compound mode."""

    # Mode indicator
    intent_mode: Literal["single", "compound"] = "compound"

    # What we extracted and can set
    proposed_actions: List[ProposedAction]

    # What's required but not provided
    missing_required: List[MissingField]

    # What we detected but can't handle yet
    unsupported_mentions: List[UnsupportedMention]

    # Overall status
    intent_status: Literal["complete", "partial", "blocked"]

    # Payload for Apply (only approved actions)
    apply_payload: Optional[ApplyPayload]

    # Legacy fields for backward compatibility
    approved: List[Action]  # = proposed_actions that passed validation
    rejected: List[RejectedAction]
    warnings: List[str]
    guidance: Optional[str]


@dataclass
class ProposedAction:
    path: str
    value: Any
    unit: Optional[str] = None
    source: Literal["extracted", "user_provided", "default"] = "extracted"
    confidence: Literal["high", "medium", "low"] = "high"


@dataclass
class MissingField:
    path: str
    phase: str
    reason: str
    suggestion: Optional[str] = None  # e.g., "typical: 8-15m"
    required: bool = True


@dataclass
class UnsupportedMention:
    text: str
    concept: str
    status: Literal["no_schema_field", "not_refinable", "ambiguous"]
    future: Optional[str] = None  # e.g., "ext.payload.pods"
```

---

## Why This Does NOT Violate Kernel Integrity

| Concern | How It's Addressed |
|---------|-------------------|
| **Mutation without ActionExecutor** | All writes still flow through ActionExecutor. Interpretation only proposes. |
| **Server-side conversation memory** | None. Each preview is stateless. User session is client-side only. |
| **Silent inference** | All proposed values are shown to user. Nothing applied without explicit confirm. |
| **Guessing missing values** | We show "missing_required" with suggestions, never auto-fill. |
| **Preview mutating state** | Preview works on a deep copy. design_version unchanged. |
| **Bypassing validation** | Execution phase runs full ActionValidator before any commit. |
| **Auto-executing phases** | Phases only run when user explicitly triggers them. |

**The interpretation phase is a presentation layer.** It can over-propose, be wrong, show suggestions. But it never writes.

**The execution phase is the kernel.** It validates, prunes, rejects, and commits atomically.

---

## ext.* Forward Compatibility (Design-Only)

Module 65.1 does NOT implement ext.*, but the design must not dead-end it.

### Future ext.* Namespaces

| Namespace | Purpose | Example |
|-----------|---------|---------|
| `ext.payload.pods` | Cargo container tracking | `{count: 160, type: "TEU", weight_each_mt: 25}` |
| `ext.arrangement.deck_modules` | Modular deck layouts | `{module: "crew_cabin", position: "deck_2_aft"}` |
| `ext.cargo.units` | Generic cargo units | `{type: "vehicle", count: 40, lane_meters: 800}` |

### How ext.* Will Connect to Physics

```
ext.payload.pods
    ↓ (translator)
weight.cargo_mt += pods.count * pods.weight_each_mt
arrangement.cargo_deck_area_m2 += pods.count * pods.footprint_m2
    ↓ (phase execution)
stability.gm_transverse_m recalculated
```

### What 65.1 Does Today

When "160 pods" is detected:

```json
{
  "unsupported_mentions": [
    {
      "text": "160 pods",
      "concept": "pod_count",
      "status": "no_schema_field",
      "future": "ext.payload.pods"
    }
  ]
}
```

**User sees**: "160 pods recognized but not yet supported. Coming in Module 66."

**Nothing silent. Nothing lost. Nothing broken.**

---

## Tradeoff Discussion

### What We Gain

1. **Natural language input** - Users can speak broadly on first message
2. **Single confirmation** - One Apply instead of 5-10 micro-confirms
3. **Coherent proposals** - System shows one plan, not piecemeal corrections
4. **Transparency** - Missing fields, unsupported concepts all visible
5. **Future-proof** - ext.* path is designed, not retrofitted

### What We Accept

1. **Interpretation complexity** - Multi-pass extraction is more code
2. **Over-proposal risk** - System may propose actions user didn't intend (mitigated by confirm step)
3. **UI work** - Need affordances for edit, fill-in, apply
4. **Parsing ambiguity** - "aluminum catamaran" could be parsed differently; we document precedence

### What We Preserve

1. **Kernel safety** - All mutation through ActionExecutor
2. **Determinism** - Same input, same extraction (given schema)
3. **Auditability** - Every action logged with source
4. **Statelessness** - No server conversation memory
5. **Validation authority** - Kernel can reject any proposed action

---

## Migration Path: v5 → Broad-First

### Step 1: Add Compound Extraction (No Breaking Changes)

```python
# New function in intent_parser.py
def extract_compound_intent(text: str) -> CompoundIntent:
    """Multi-pass extraction for compound mode."""
    ...

# Existing function unchanged
def parse_intent_to_actions(text: str) -> List[Action]:
    """Single-action extraction (legacy, still works)."""
    ...
```

### Step 2: Extend Preview Response

```python
# api.py preview_intent()
if request.mode == "compound":
    compound = extract_compound_intent(text)
    # ... feasibility check, gate analysis
    return CompoundPreviewResponse(...)
else:
    # Legacy single-action mode
    return SinglePreviewResponse(...)
```

### Step 3: Update UI

```javascript
// backend-adapter.js
if (response.intent_mode === 'compound') {
    displayCompoundProposal(response);
} else {
    displaySingleAction(response);  // Legacy
}
```

### Step 4: Deprecate Single Mode (Optional, Later)

Once compound mode is stable, single mode can become internal-only.

---

## Implementation Plan

### NON-NEGOTIABLE: Gate Reuse with Hypothetical State

**Approval Condition**: `missing_for_phases` MUST be produced by the existing gate system:
- Same `GATE_CONDITIONS` dict
- Same `GateCondition.evaluate()` method
- Same `PhaseMachine.check_gate_conditions()` logic
- Evaluated against a **hypothetical post-apply state view**
- **Zero mutation**: no `set()`, no `begin_transaction()`, no `commit()`

If we can't reuse the gate engine, we stop and report.

### Implementation Strategy: HypotheticalStateView

The gate system only needs a `.get(path)` method. We create a wrapper that overlays proposed values:

```python
class HypotheticalStateView:
    """
    Read-only view that overlays proposed actions on real state.
    Implements same get(path) interface as StateManager.
    """
    def __init__(self, real_state_manager, proposed_actions: List[Action]):
        self._real = real_state_manager
        # Build overlay: {path: value}
        self._overlay = {}
        for action in proposed_actions:
            if action.action_type == ActionType.SET:
                self._overlay[action.path] = action.value

    def get(self, path: str, default=None):
        """Return proposed value if exists, else real state."""
        if path in self._overlay:
            return self._overlay[path]
        return self._real.get(path, default)
```

Then we can call `gate.evaluate(hypothetical_view)` with zero mutation.

---

### Phase 1: HypotheticalStateView (~25 lines)

```
File: magnet/deployment/api.py
Add: HypotheticalStateView class
  - __init__(self, real_state_manager, proposed_actions)
  - get(self, path, default=None) -> overlays proposed values
  - No set(), no mutation methods
```

### Phase 2: Gate Check on Hypothetical (~30 lines)

```
File: magnet/deployment/api.py
Add: check_gates_on_hypothetical(phase, hypothetical_view) -> List[MissingField]
  - Get gates from GATE_CONDITIONS[phase]
  - For each gate: gate.evaluate(hypothetical_view)
  - Map failed gates to {path, reason, suggestion}
  - Return list of MissingField objects
```

### Phase 3: Multi-Pass Extraction (~50 lines)

```
File: magnet/deployment/intent_parser.py
Add: extract_compound_intent()
Add: find_all_numeric_patterns()
Add: find_all_enum_mentions()
Add: detect_unsupported_mentions()
```

### Phase 4: Compound Preview Endpoint (~40 lines)

```
File: magnet/deployment/api.py
Modify: preview_intent() to support mode="compound"
  1. Parse text → List[Action] via extract_compound_intent()
  2. Validate each action via ActionPlanValidator (read-only)
  3. Create HypotheticalStateView with approved actions
  4. For each target phase: check_gates_on_hypothetical()
  5. Build CompoundPreviewResponse with missing_for_phases

NO state_manager.set(), begin_transaction(), or commit() in this path.
```

### Phase 4: UI Compound Display (~60 lines)

```
File: magnet/ui_v2/js/backend-adapter.js
Add: displayCompoundProposal()
Add: renderMissingFields()
Add: handleBulkApply()
```

### Phase 5: Tests (~100 lines)

```
File: tests/unit/test_compound_intent.py
Test: Multi-pass extraction
Test: Numeric precedence preserved
Test: Unsupported mention detection
Test: Hypothetical gate check
Test: No state mutation on preview
```

**Total: ~280 lines of changes**

---

## Files to Modify

| File | Change | Lines |
|------|--------|-------|
| `magnet/core/refinable_schema.py` | Add enum support, 3 new fields | ~45 |
| `magnet/deployment/intent_parser.py` | Add extract_compound_intent(), helpers | ~80 |
| `magnet/deployment/api.py` | Add compound preview mode, hypothetical check | ~70 |
| `magnet/ui_v2/js/backend-adapter.js` | Add compound display, bulk apply | ~60 |
| `tests/unit/test_compound_intent.py` | New test file | ~100 |

**Total: ~355 lines**

---

## Done Criteria

1. **Broad input works**: "60m aluminum catamaran cargo ferry" → 4 proposed actions
2. **Missing fields shown**: beam, draft displayed with suggestions
3. **Unsupported flagged**: "160 pods" → unsupported_mentions with future path
4. **Single apply**: User confirms once, 4+ actions execute atomically
5. **No mutation on preview**: design_version unchanged until Apply
6. **Kernel untouched**: ActionExecutor, Validator, MutationEnforcement unchanged
7. **Backward compatible**: Single-action mode still works

---

## Tests Required

### MANDATORY Gate Reuse Tests (Approval Condition)

These three tests are **required** to prove the implementation uses the gate engine correctly:

```python
class TestGateReuseWithHypotheticalState:
    """
    APPROVAL CONDITION TESTS
    Prove: gate reuse + hypothetical state, not a new engine.
    """

    def test_preview_does_not_bump_design_version(self, test_client, empty_design):
        """
        (a) Preview doesn't mutate state.
        design_version must be unchanged after preview.
        """
        # Get version before
        state_resp = test_client.get(f"/api/v1/designs/{empty_design}/state")
        version_before = state_resp.json()["design_version"]

        # Call preview
        test_client.post(
            f"/api/v1/designs/{empty_design}/intent/preview",
            json={"text": "set hull length to 60 meters", "mode": "compound"}
        )

        # Get version after
        state_resp = test_client.get(f"/api/v1/designs/{empty_design}/state")
        version_after = state_resp.json()["design_version"]

        assert version_before == version_after, "Preview must not bump design_version"

    def test_loa_not_missing_after_preview_set_loa(self, test_client, empty_design):
        """
        (b) loa_set is NOT listed as missing after previewing SET hull.loa.
        Proves hypothetical state overlay works.
        """
        response = test_client.post(
            f"/api/v1/designs/{empty_design}/intent/preview",
            json={"text": "set hull length to 60 meters", "mode": "compound"}
        )
        data = response.json()

        # hull.loa should be in approved actions
        approved_paths = [a["path"] for a in data.get("proposed_actions", data.get("approved", []))]
        assert "hull.loa" in approved_paths

        # loa_set should NOT be in missing gates
        missing_paths = [m["path"] for m in data.get("missing_required", data.get("missing_for_phases", {}).get("hull_form", []))]
        assert "hull.loa" not in missing_paths, "loa should not be missing after proposing to set it"

    def test_beam_draft_remain_missing_after_set_loa(self, test_client, empty_design):
        """
        (c) beam/draft remain in missing_for_phases after SET hull.loa.
        Proves gate check runs on hypothetical state.
        """
        response = test_client.post(
            f"/api/v1/designs/{empty_design}/intent/preview",
            json={"text": "set hull length to 60 meters", "mode": "compound"}
        )
        data = response.json()

        # beam and draft should still be missing
        missing = data.get("missing_required", data.get("missing_for_phases", {}).get("hull_form", []))
        missing_paths = [m["path"] for m in missing]

        assert "hull.beam" in missing_paths, "beam should still be missing"
        assert "hull.draft" in missing_paths, "draft should still be missing"
```

### Additional Compound Intent Tests

```python
class TestCompoundIntentExtraction:
    def test_extracts_multiple_actions(self):
        """Broad input yields multiple proposed actions."""
        result = extract_compound_intent("60m aluminum catamaran ferry")
        assert len(result.proposed_actions) >= 3
        paths = [a.path for a in result.proposed_actions]
        assert "hull.loa" in paths
        assert "hull.hull_type" in paths
        assert "structural_design.hull_material" in paths

    def test_numeric_precedence_preserved(self):
        """Numeric extraction happens before enum in each pass."""
        result = extract_compound_intent("60m catamaran")
        # Both should be extracted, not just first match
        assert len(result.proposed_actions) == 2

    def test_unsupported_mentions_detected(self):
        """Concepts without schema fields are flagged."""
        result = extract_compound_intent("ferry for 160 pods")
        assert len(result.unsupported_mentions) == 1
        assert result.unsupported_mentions[0].text == "160 pods"

    def test_apply_executes_atomically(self, state_manager):
        """Bulk apply creates single transaction."""
        apply_payload = {
            "actions": [
                {"action_type": "set", "path": "hull.loa", "value": 60.0},
                {"action_type": "set", "path": "hull.hull_type", "value": "catamaran"},
            ]
        }
        result = execute_actions(apply_payload)
        # Single version bump, not two
        assert result.design_version_after == result.design_version_before + 1
```

---

## Summary

Module 65.1 v6 introduces **broad-first intent resolution** while preserving kernel integrity:

| Layer | Behavior | Safety |
|-------|----------|--------|
| **Interpretation** | Broad, permissive, over-proposes | Read-only, can be wrong |
| **Preview** | Shows proposal + missing + unsupported | No mutation |
| **Confirmation** | User reviews, edits, confirms once | Explicit consent |
| **Execution** | Strict, atomic, validated | Full kernel enforcement |

**The current v5 design was not wrong. It was necessary scaffolding.** This evolution preserves safety while unlocking the UX that makes MAGNET feel like a design partner, not a form-filling tool.

---

**Plan Author**: Claude
**Date**: 2025-12-18
**Version**: 6 (broad-first compound intent)
**Status**: Ready for implementation

---

## Appendix A: Control Plane Philosophy

> "You're building a control plane, not a chatbot."

This remains true. The difference is:

- **v5**: Control plane with single-action input
- **v6**: Control plane with compound-action input + explicit confirmation

The kernel doesn't change. The transaction model doesn't change. The validation doesn't change.

What changes: **the interpretation layer can now listen to a messy first sentence and turn it into a coherent proposal** — without lying, without guessing, without bypassing.

MAGNET can now accept:
> "60m aluminum catamaran cargo ferry for 160 pods"

And respond:
> "Here's what I can set (4 params). Here's what you need to add (beam, draft). Here's what I can't handle yet (pods). Apply when ready."

That's not a chatbot. That's a control plane with a good front-end.

---

## Appendix B: Strategic Rationale (Why v6 Is Correct)

### Gates and Interpretation Solve Different Problems

**Gates answer**: "Given a (hypothetical) state, what inputs are missing to legally run phase X?"

**Interpretation answers**: "From a messy sentence, which state fields should I propose setting?"

These are complementary, not competing. The interpretation layer doesn't replace gates — it feeds them.

### Why "Just Run Everything" Doesn't Work

Running all phases on every message only works if you already have complete, valid inputs. With broad-first chat, you usually don't — so you'd just repeatedly run into gate failures and the user gets "blocked" without being told exactly what to provide next.

The right move is:
1. Use **interpretation** to propose a candidate set of actions from the user's text
2. Use **gates** to compute missing inputs (on a hypothetical state)
3. Show both to user before any mutation

### Is v6 Accidentally Creating a Second Validation Pipeline?

**No**, as long as we enforce this boundary:

| Layer | Does | Doesn't Do |
|-------|------|------------|
| **Interpretation** | Extract actions, call existing `gate.evaluate(HypotheticalView)` | Custom validation, required-inputs tables, phase dependency logic |
| **Execution** | `ActionPlanValidator` → `ActionExecutor` (the only mutating path) | Nothing else mutates |

If the interpretation layer starts doing its own "required inputs tables" or "custom validation", then you've built a parallel engine. But v6, with the "gate reuse with hypothetical state" tests, stays clean.

### Tradeoffs to Accept

1. **Friction vs correctness risk**: Broad extraction will sometimes over-propose (mitigated by preview + explicit Apply)
2. **Complexity location**: Moving complexity to interpretation (good) instead of polluting kernel execution (very good)
3. **User expectation**: Broad-first implies the UI should suggest next missing fields strongly
4. **Performance**: Gate checks are cheap; full physics is not always worth auto-running until "intent_status=complete"

### The Two Locked Invariants

**Approve v6 if and only if these hold:**

1. **`missing_*` computed only via existing gates on HypotheticalStateView** — no new requirement logic
2. **No mutation until Apply** — no `state.set()`, `begin_transaction()`, `commit()` anywhere in preview path

Once that's true, you haven't abandoned a "good method" — you've finally built the missing control-plane layer that makes the kernel usable in chat form.
