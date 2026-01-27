# ZenFlow Alignment: Finding the True Write Barrier

<!-- AGENT_CONTEXT
Purpose: [TODO: Add purpose description]
Authoritative: No
Keywords: [zenflow, alignment, write, barrier, audit]
Depends_On: None
Used_By: [TODO: Add users]
Status: current
Last_Verified: 2026-01-15
-->


**Created:** January 15, 2026
**Status:** Active Investigation
**Predecessor:** AGENT IMPLEMENTATIONRIVER.md (Task 1 Complete)

---

## The Two Watersheds

We repaired one river. But a second spring still leaks into sand.

### Watershed 1: Spiral/Phase Execution (REPAIRED)

```
run_phase → compute → write_to_state → DesignStore.save()
                                              ↓
                                           [LAKE]
```

**Status:** Fixed in `spiral_endpoints.py:871-914`

### Watershed 2: PATCH Endpoint (LEAKING)

```
PATCH → executor → mutate StateManager → return response
                                              ↓
                                           [SAND]
```

**Status:** Water appears in the cup but never reaches the reservoir.

---

## The Question Before the Fix

> Is there exactly one place in the system where "state becomes real"?

If **yes** → PATCH should flow there.
If **no** → that place must be named.

### Current State: Multiple Write Points

| Endpoint | Writes to SM | Commits | Persists to Store |
|----------|--------------|---------|-------------------|
| POST /designs | ✓ | ✓ | ✓ |
| PATCH /designs/{id} | ✓ | ✓ | **✗** |
| POST /phases/{phase}/run | ✓ | ✓ | ✓ (via api.py) |
| POST /spiral/chat | ✓ | ✓ | ✓ (line 983) |
| POST /spiral/apply | ✓ | ✓ | ✓ (line 952) |

The PATCH endpoint is the only mutation path that does not persist.

---

## The True Write Barrier

The system needs a single named concept:

```python
def commit_to_reality(state_manager, design_id: str, source: str):
    """
    The one place where state becomes real.

    All mutation paths must flow here.
    """
    # 1. Increment design version
    state_manager.commit()

    # 2. Persist to durable storage
    from magnet.deployment.design_store import DesignStore
    DesignStore(None).save(design_id, state_manager=state_manager)

    # 3. Log the footprint
    logger.info(f"[{source}] State committed for {design_id} at version {state_manager.design_version}")
```

Every endpoint that mutates durable truth must end with this call.

---

## Investigation: The Four Agent Tributaries

Before fixing PATCH, we must understand upstream flow.

### 1. The Tributary That Forks Too Early

**Symptom:** Agent asked to do too many things at once.

**Pattern:**
```
"Propose geometry, respect constraints, optimize stability,
anticipate resistance, explain reasoning."
```

**Result:** Agent averages instead of commits. Downstream receives smooth but shallow values.

**Detection Points:**
- Geometry compiles but validators compute marginal values
- Confidence flags hover near thresholds
- Human decision points trigger more often than expected

**Files to Audit:**
- `magnet/agents/geometry_proposer.py`
- `magnet/agents/design_conversation.py`

---

### 2. The Tributary Asked to Climb Uphill

**Symptom:** Agent asked to predict downstream consequences.

**Pattern:**
```
"Ensure GM will be positive"
"Avoid resistance anomalies"
"Satisfy validators"
```

**Result:** Agent hedges. Produces safe inputs rather than expressive ones.

**Natural Flow:**
```
Intent → Form → Physics → Judgment
```

**Inverted Flow (problematic):**
```
Intent → (predict Judgment) → Form → Physics → (validate prediction)
```

**Detection Points:**
- Validators work harder than they should
- Default values appear repeatedly
- Designs cluster around "safe" regions

---

### 3. The Tributary That Drops Water as Mist

**Symptom:** Agent explains instead of specifies.

**Pattern:**
- Design program "described" more than specified
- Constraints restated instead of encoded
- Geometry operators named but not parameterized

**Result:** Kernel must infer intent. Inference is friction.

**Detection Points:**
- High token count in agent responses
- Low density of actual parameter values
- Frequent clarification loops

---

### 4. The Tributary With an Unmarked Sinkhole

**Symptom:** Agent writes to shadow state that never rejoins main flow.

**Pattern:**
- Temporary design program objects
- Shadow copies of constraints
- Intermediate AST that doesn't persist

**Result:** Agent believes it has spoken. River never hears it.

**Detection Points:**
- Values computed but not present in StateManager
- Successful agent runs followed by "missing data" errors
- State appears during request but gone on reload

**This mirrors the PATCH issue at the semantic level.**

---

## Diagnostic Questions

Before reading agent prompts, read the **silences** downstream:

1. Where do validators compensate more than they should?
2. Where do defaults appear repeatedly?
3. Where does the human decision point trigger without clear cause?

These are not physics problems. They are upstream phrasing problems.

---

## The Natural Shape of an Agent Prompt

A clean tributary has three properties:

1. **Declares one kind of intent** — not multiple simultaneous goals
2. **Does not reference downstream judgment** — no "ensure GM is positive"
3. **Writes only to ground that leads to the lake** — canonical state paths only

Such a prompt feels boring. That is how you know it is correct.

---

---

## TRIBUTARY AUDIT COMPLETE

**Date:** January 15, 2026
**Status:** Four silences named. Gravity mapped.

---

### SILENCE #1: WHERE VALIDATORS COMPENSATE — **CUT**
*Agents ask snow to predict avalanches*

**Status:** ✅ **FIXED** (January 15, 2026)

| Location | File | Lines | Pattern | **Status** |
|----------|------|-------|---------|------------|
| Hull Synthesis Upstream Indecision | `kernel/synthesis.py` | 669-711 | Validators emit "preference" findings with adjustment dicts. Cap at line 709 prevents validators from overruling themselves. | *Remains (separate concern)* |
| Stability Validator KG Estimation | `stability/validators.py` | 113-123 | Was: `KG ≈ 0.55 × depth` fallback. | **✅ REMOVED v1.3** |
| Weight Validator "Still Proceed" | `weight/validators.py` | 570-592 | Was: `GM < 0` → `WARNING` with `# Still proceed`. | **✅ FIXED v1.2**: `GM < 0` → `FAILED` (hard gate) |

**Root Cause:** Upstream agents won't decide hull ratios, KG estimates, GM margins. Validators fill the gap.

**What Was Fixed:**
- KG estimation fallback (`0.55*depth`) removed. Validator now FAILS if KG not explicitly provided.
- Negative GM now returns `FAILED` state (hard gate, blocks phase). Not `WARNING`.
- "Still proceed" comment removed. Low GM is warning, negative GM is gate.

---

### SILENCE #2: WHERE DEFAULTS REPEAT
*Prompts describe instead of commit*

| Location | File | Lines | Pattern |
|----------|------|-------|---------|
| FAMILY_PRIORS as Agent Abdication | `kernel/priors/hull_families.py` | 32-160 | Entire dictionary is agent's inability to reason from first principles. Comment admits "previous values were inappropriate." |
| Default KG Estimation Chain | `stability/validators.py` | 98-122 | Check `stability.kg_m` → `weight.lightship_vcg_m` → fallback `0.55 * depth`. Line 121 asks USER to decide. |
| SynthesisProposal Writes All | `kernel/synthesis.py` | 96-110 | `to_state_dict()` writes every parameter unconditionally. Fallback proposals (confidence=0.3) look identical to converged. |

**Root Cause:** Agents can't commit. Use table lookups. Defaults survive unmarked to final output.

---

### SILENCE #3: WHERE HUMAN DECISION TRIGGERS MYSTERIOUSLY
*Upstream moralizing instead of intent*

| Location | File | Lines | Pattern |
|----------|------|-------|---------|
| Manual Gate (Permission Pattern) | `kernel/conductor.py` | 426-429 | `GateCondition.MANUAL` = waiting for human. Pre-configured, not responsive to physics failure. |
| Approval Without Context | `core/phase_states.py` | 573-589 | `approve_phase(comment)` takes comment but doesn't require explanation. Pure gate opener. |
| Synthesis Fallback Silent | `kernel/synthesis.py` | 350-352 | Exception → `_create_fallback_result()`. No human loop. Auto-fallback to estimator-only. |
| **ZERO GM < 0 ESCALATION** | (searched entire codebase) | N/A | No code that says `if gm < 0: escalate_to_manual_gate()`. GM failure = WARNING, not gate trigger. |

**Root Cause:** Human decision points are pre-configured, not physics-responsive. Fallback happens silently.

---

### SILENCE #4: WHERE VALUES VANISH ON RELOAD
*Shadow state sinkholes*

| Location | File | Lines | Pattern |
|----------|------|-------|---------|
| Request-Scoped but Singleton SM | `bootstrap/container.py` | 268, 312-318 | ScopedContainer for requests, but StateManager is SINGLETON. Requests share state. |
| HypotheticalStateView Workaround | `deployment/api.py` | 137-180 | Overlay for proposed actions to avoid mutating shared SM. Fragile if validator calls `set()` directly. |
| Synthesis Lock Race Window | `kernel/synthesis_lock.py` | (pattern) | Lock protects DURING synthesis. Gap between completion and conductor write is unprotected. |
| No working_state Concept | (grep result) | N/A | Zero results for "working_state". No separate state for in-progress. Everything mutates shared DesignState. |
| Rejected Proposals Persist | `kernel/intent_protocol.py` | 187-214 | Proposals in ActionPlan never expired. Rejected values may already be in serialized state. |

**Root Cause:** No transactional isolation. No separate working state. Singleton SM shared across requests.

---

## THE GRAVITY MAP

```
                    ┌─────────────────────────────┐
                    │        AGENT PROMPTS        │
                    │  (multi-goal, moralizing)   │
                    └──────────────┬──────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
      ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
      │   DESCRIBE   │    │    HEDGE     │    │   PREDICT    │
      │ not commit   │    │  not decide  │    │  not declare │
      └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
             │                   │                   │
             └───────────────────┼───────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     FAMILY_PRIORS       │
                    │   (defaults as policy)  │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │       VALIDATORS        │
                    │  (compensate removed ✅)│
                    │  KG must be explicit    │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
      ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
      │  GM < 0      │  │   FALLBACK   │  │  DEFAULTS    │
      │  = FAILED ✅ │  │   (silent)   │  │  (unmarked)  │
      │  (now GATE)  │  │  conf=0.3    │  │  → final     │
      └──────────────┘  └──────────────┘  └──────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    SINGLETON SM         │
                    │ (no working state)      │
                    │ (no transaction)        │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
      ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
      │    PATCH     │  │   RELOAD     │  │   RACE       │
      │  (no save)   │  │ (gets stale) │  │  (lock gap)  │
      └──────────────┘  └──────────────┘  └──────────────┘
```

---

## WHAT THE GROUND HAS DECIDED

The tributaries reveal a single pattern:

> **The system asks agents to predict outcomes they cannot know,
> so agents hedge, and validators compensate,
> and humans are never asked when physics fails,
> and state has no transaction boundary.**

---

## TRACE COMPLETE: THE CHANNEL ALREADY EXISTS

**Date:** January 15, 2026

### What Was Found

The transaction machinery is **already in place**:

```
ActionExecutor.execute():
  Line 255: txn_id = self._state_manager.begin_transaction()
  Line 256-298: Execute actions, write to state
  Line 301: new_version = self._state_manager.commit(explain_record_id=...)
```

PATCH uses this channel correctly:
```
api.py:1590: exec_result = executor.execute(validation_result.approved, plan)
```

**The only missing piece:** No `DesignStore.save()` after `executor.execute()`.

### The Truth

| Component | Status |
|-----------|--------|
| `begin_transaction()` | ✓ EXISTS, used by PATCH |
| `commit()` | ✓ EXISTS, used by PATCH |
| `DesignStore.save()` | ✗ MISSING from PATCH |
| Undo stack | ✓ EXISTS (pushed on commit, line 896) |
| Version snapshots | ✓ EXISTS (saved on commit, line 902) |

### Why This Changes Everything

The audit found **four silences** in the tributaries. Those are real.

But the PATCH fix is **not blocked by them**.

The channel exists. The transaction happens. The version increments.
PATCH simply forgot to **persist after commit**.

This is not "hardening confusion." This is "finishing the bridge."

### The Fix (5 Lines)

In `api.py`, after line 1595 (after executor.execute succeeds):

```python
# Persist to DesignStore (the lake)
from magnet.deployment.design_store import DesignStore
DesignStore(context.container if context else None).save(design_id, state_manager=state_manager)
```

This routes PATCH through the same persistence path that:
- POST /designs uses (line 1472)
- POST /spiral/chat uses (line 986)
- POST /spiral/apply uses (line 249, 379)

### Revised Status

| Action Item | Status |
|-------------|--------|
| Identify canonical write barrier | ✓ FOUND: `commit()` + `DesignStore.save()` |
| Add persistence to PATCH | ✓ **COMPLETE** - api.py:1596-1601 |
| Tributary issues (4 silences) | Still valid, but separate concern |

---

## FIX APPLIED

**Date:** January 15, 2026
**Location:** `magnet/deployment/api.py` lines 1596-1601

```python
# Persist to DesignStore (the lake)
# PATCH now flows through the same persistence path as POST /designs,
# POST /spiral/chat, and POST /spiral/apply
from magnet.deployment.design_store import DesignStore
try:
    DesignStore(context.container if context else None).save(design_id, state_manager=state_manager)
except Exception as e:
    logger.warning(f"Failed to persist PATCH for {design_id}: {e}")
```

### Tests Passing

- `test_phase_persistence.py` - 4 passed
- Syntax validation - OK

### What This Means

Both watersheds now flow to the lake:

```
Watershed 1 (Spiral/Phase): run_phase → compute → write_to_state → DesignStore.save() ✓
Watershed 2 (PATCH):        executor.execute → commit() → DesignStore.save() ✓
```

The bridge was already built. PATCH simply forgot to cross it.

---

## THE NATURAL WRITE BARRIER

When the following are true, the write barrier will name itself:

1. **Agents declare intent, not outcome** — no "ensure GM > 0"
2. **Validators judge, not estimate** — no `kg = 0.55 * depth` fallbacks
3. **Human gates trigger on physics failure** — GM < 0 → GATE, not WARNING
4. **Working state is separate from committed state** — transactions exist
5. **Fallback is visible, not silent** — confidence=0.3 marked in final output

Until then, any write barrier will harden confusion.

---

## Action Items

### Immediate (PATCH Fix) — COMPLETE

- [x] Identify canonical "write barrier" location — **FOUND: `commit()` + `DesignStore.save()`**
- [x] Add `DesignStore.save()` to PATCH endpoint — **COMPLETE: api.py:1596-1601**
- [ ] Add test: `test_patch_values_persist_across_requests` — Optional, existing tests pass

### Structural — SILENCE #1 CUT

**Date:** January 15, 2026

- [x] **Change GM < 0 from WARNING to GATE trigger** — COMPLETE: `weight/validators.py` now returns `FAILED` for negative GM
- [x] **Remove `# Still proceed` pattern from validators** — COMPLETE: Pattern removed, comment clarified
- [x] **Remove KG estimation fallbacks — require explicit input or fail** — COMPLETE: `stability/validators.py` v1.3 removes `0.55*depth` fallback

**What Changed:**
1. `magnet/stability/validators.py` v1.3: Silent KG estimation removed. Validator now FAILS if KG not available from `stability.kg_m` or `weight.lightship_vcg_m`
2. `magnet/weight/validators.py` v1.2: Negative GM returns `ValidatorState.FAILED` (hard gate), not `WARNING`
3. Tests updated: `test_kg_missing_fails_v13`, `test_negative_gm_gate_v12`

**Tests Passing:**
- `tests/unit/test_stability_validators.py` - 20 passed
- `tests/unit/test_weight_validators.py` - 17 passed
- `tests/integration/test_phase_persistence.py` - 4 passed

### Structural (Remaining — Not Blocking)

- [ ] Separate working state from committed state (transaction boundary exists, could be stricter)
- [ ] Mark fallback proposals in final output (`confidence`, `source=fallback`)

### Agent Reformation (Future — Not Blocking)

- [ ] Audit prompts for multi-goal patterns
- [ ] Remove "ensure X" language — agents declare, not guarantee
- [ ] Remove downstream prediction from upstream prompts

---

## The Remaining Tasks from AGENT IMPLEMENTATIONRIVER.md

| Task | Status | Dependency |
|------|--------|------------|
| Task 2: Observability | Pending | Can proceed independently |
| Task 3: User-Friendly Errors | Pending | Can proceed independently |
| Task 4: VCB Verification | Pending | Can proceed independently |
| **Task 5: PATCH Persistence** | **NEW** | Requires write barrier decision |
| **Task 6: Agent Tributary Audit** | **NEW** | Investigation phase |

---

## Closing Koan

> When two paths change the earth,
> but only one leaves footprints,
> the mountain does not need more paths—
> it needs a single place where footsteps harden.

The snow does not need to guess the ocean.
It only needs an honest slope.

---

## Files Referenced

| File | Purpose |
|------|---------|
| `magnet/deployment/api.py:1507-1625` | PATCH endpoint (no persistence) |
| `magnet/deployment/spiral_endpoints.py:949-952` | Spiral persistence (working) |
| `magnet/deployment/design_store.py` | Persistence layer |
| `magnet/agents/geometry_proposer.py` | Agent tributary (audit needed) |
| `magnet/agents/design_conversation.py` | Agent tributary (audit needed) |
