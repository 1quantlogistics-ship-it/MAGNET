# MAGNET v1.2 Implementation (Theory): Lens Pack + Diff‑Only DSL + Deterministic Lenses + Dependency Graph

<!-- AGENT_CONTEXT
Purpose: [TODO: Add purpose description]
Authoritative: No
Keywords: [magnet, v1.2, implementation, theory, lenspack]
Depends_On: None
Used_By: [TODO: Add users]
Status: current
Last_Verified: 2026-01-15
-->


**Purpose**: Describe what a constitution-aligned v1.2 “actually working” runtime would look like *in theory*, with an emphasis on **token efficiency** and **scalability**:

> **Lens Pack (dictionary‑coded compact JSON text) + diff‑only DSL edits + deterministic lens builder + dependency graph**

This design assumes the MAGNET core principle:
- **State is the product** (persistent, versioned, queryable)
- Agents propose **pure geometric constructions** (declarative, diff‑only)
- The kernel **compiles** into canonical geometry and **validates reality post‑compile**

---

## 1) Why “Lens Pack” exists (the scaling problem)

As vessel context expands (more bodies, more constraints, more domains, longer history), naive prompting fails because:
- you can’t send the whole DesignState every turn (token blowup),
- LLMs don’t “remember” reliably (they reconstruct),
- implicit conventions multiply (drift),
- repeated full-state prompts cause accidental inconsistencies.

**The goal**: Keep the agent’s context **small, deterministic, and sufficient**, while keeping the authoritative truth in **DesignState**.

---

## 2) The v1.2 golden loop (single end‑to‑end spiral)

One design “pass” is always the same shape:

1) **Intent classify**: EDIT vs REWRITE vs EXPLORE vs QUERY  
2) **Build WorkOrder** (deterministic guard + budgets + allowed writes)  
3) **Build lens pack** (deterministic lens builder, token-budgeted)  
4) **Agent proposes diff** (diff-only DSL patch + constraints + confidence/provenance)  
5) **Kernel validates proposal** (syntax/type/schema + lens safety + authority)  
6) **Apply patch atomically** (commit + explain record + dependency invalidation)  
7) **Compile geometry artifacts** (canonical geometry pipeline)  
8) **Validate reality** (physics + constraints → envelope-typed results)  
9) **Convergence guard** (stall/thrash budgets) or **escalate to human**

Crucially:
- **The agent never receives the whole state.**
- **The agent never writes state directly.**
- **The agent never resends the whole design program.**

---

## 3) Lens Pack: a compact, deterministic state slice

### 3.1 Lens Pack definition

A **Lens Pack** is a compact payload containing:
- the **minimal state slice** required for the current WorkOrder task,
- explicit **allowed operations** / safe write surface,
- explicit **staleness** markers (what derived results are out-of-date),
- an **encoding dictionary** so the slice can be extremely token-efficient.

### 3.2 Why JSON (and why not “more efficient file types”)

LLM inputs are text tokens. You *can* embed binary as base64, but it usually **increases tokens** and decreases reliability because:
- base64 is token-expensive,
- it becomes opaque to the model,
- it’s harder to debug and to keep deterministic.

So the best practical compression is:
- **compact JSON text** (minified, stable ordering),
- **dictionary-coded keys** (short codes instead of long paths),
- **diff-only payloads** (no repetition),
- **rounding / quantization** for floats when appropriate.

### 3.3 Dictionary-coded compact JSON (format)

Lens Pack v1.2 (example shape):

```json
{
  "v": "LP1.2",
  "did": "c9f3…",              // design_id
  "cid": "b17a…",              // commit_id (or design_version)
  "lid": "HULL_FORM@1",        // lens identifier
  "dict": {
    "p": {                     // path dictionary (canonical → code)
      "hull.loa": "a",
      "hull.lwl": "b",
      "hull.beam": "c",
      "hull.draft": "d",
      "hull.cb": "e",
      "kernel.design_version": "v",
      "resources.summary": "rs"
    },
    "r": {                     // resource type dictionary (optional)
      "geometry.body": "B",
      "geometry.section": "S",
      "geometry.discontinuity": "D"
    }
  },
  "data": {
    "a": 25.0,
    "b": 23.8,
    "c": 6.2,
    "d": 1.4,
    "e": 0.38,
    "v": 128,
    "rs": {
      "B": 2,
      "S": 21,
      "D": 3
    }
  },
  "writes": {
    "allow_paths": ["resources.*", "hull.*", "constraints.*"],
    "deny_paths": ["mission.vessel_type", "kernel.*"],
    "max_actions": 20
  },
  "stale": {
    "geometry": false,
    "hydrostatics": true,
    "resistance": true
  },
  "budgets": {
    "max_passes": 10,
    "pass": 3,
    "max_tokens_agent": 3500
  }
}
```

**Key properties**:
- **Deterministic ordering** (canonicalized JSON): stable key order, stable float formatting.
- **Dictionary versioning**: the dictionary itself can be cached by the agent across turns; later lens packs can transmit only a `dict_id` if unchanged.
- **Explicit write surface**: the pack includes what the agent may change (lens safety).

### 3.4 Deterministic lens builder

A lens is **not retrieval**. A lens is a deterministic query plan:

- It always pulls the same fields in the same order for a given `(lens_type, state_version)`.
- It has a target **token budget** and a deterministic “drop policy” (what gets omitted first).
- It includes **IDs first**, then summaries, then details as budget allows.

Implementation model:
- `LensSpec`: a static list of fields + computed summaries.
- `LensBuilder(state, lens_spec, budget) -> LensPack`.

**Drop policy example**:
1) Keep: IDs, versions, active constraints, last failures, resource counts
2) Keep: top-K violations, top-K objectives, last-K commit summaries
3) Drop: long lists (e.g., all sections) → replace with hashes + counts
4) Drop: numeric arrays → replace with min/max/mean + checksum

---

## 4) Diff‑only DSL edits (patch protocol)

### 4.1 Principle

The agent should **never resend the full program or full state**.

Instead it returns a **patch**:
- only CREATE/UPDATE/DELETE operations for the resources being changed,
- SET operations only for paths it intends to change,
- CONSTRAIN only for constraints being added/modified.

This is already close to the existing DSL semantics: CREATE/UPDATE/DELETE are diffs.

### 4.2 Patch message shape

Agent output should be a typed object (conceptually):

```json
{
  "v": "AO1.2",
  "confidence": "MEDIUM",
  "provenance": {
    "user": ["mission.max_speed_kts"],
    "inferred": ["hull.cb"],
    "defaults": ["constraints.gm_min"]
  },
  "questions": [],
  "base_commit": "b17a…",
  "dsl_patch": [
    "UPDATE bow { \"points\": [[0,0],[...]] }",
    "CREATE geometry.discontinuity step_1 { \"discontinuity_type\":\"step\", \"station_start\":0.6, \"station_end\":0.6, \"depth_m\":0.05 }",
    "SET hull.beam = 6.4",
    "CONSTRAIN stability.gm_transverse_m >= 0.5"
  ],
  "expected": {
    "geometry_change_class": "EDIT",
    "risk": ["resistance_outside_envelope"]
  }
}
```

### 4.3 Deterministic patch application

Patch application must be:
- **validated** (type_registry + schema + referential integrity),
- **atomic** (transactional commit),
- **attributed** (ExplainRecord / provenance),
- **replayable** (patch stored as first-class history artifact).

Kernel responsibilities:
- reject invalid resource updates (e.g., wrong section point format),
- reject deletes that break referential integrity,
- reject patches that write outside lens safety.

### 4.4 Exploration mode (branch + dry-run)

For exploration mode:
- patches run as **dry-run** on a branch state,
- compiled + validated,
- ranked,
- only the selected patch is committed to the mainline.

This is the “trillions of forms” unlock: exploration is cheap because each candidate is diff-only and validated against real geometry.

---

## 5) Dependency graph: invalidation, caching, and token efficiency

### 5.1 What the graph models

We need a dependency graph across:
- **inputs**: state paths and `resources.*` primitives
- **artifacts**: compiled geometry, GLB meshes, hydrostatics, resistance curves, stability metrics
- **validators**: which computations depend on which inputs
- **lenses**: which lens fields depend on which artifacts

### 5.2 Why it’s required

Without it:
- you recompute everything each pass (slow),
- you can’t mark results stale accurately,
- you can’t send minimal lens packs (you don’t know what matters),
- you can’t reason about reversibility/replay in a principled way.

### 5.3 Invalidation flow

On commit:
1) compute `changed_paths` (including resource IDs touched)
2) traverse dependency graph → mark dependent artifacts **STALE**
3) lens builder uses staleness flags to:
   - include last known value + “stale” marker, or
   - exclude stale values and request recomputation.

### 5.4 Cache keys

Artifacts must be keyed by:
- `commit_id` (or design_version),
- and optionally by a content hash of the relevant subtree (e.g., resources hash).

This guarantees replayability and prevents UI drift (“why did the picture change?”).

---

## 6) Token efficiency strategy (practical rules)

### 6.1 Keep the model in “numbers + IDs”, not prose

- Prefer compact JSON, not English summaries.
- Use stable IDs and small arrays.

### 6.2 Reduce repeated strings

- Dictionary-code long paths and resource types.
- Use dictionary IDs across turns.

### 6.3 Quantize floats when safe

- Store high precision in state.
- Send lens pack values rounded (e.g., 3 decimals) unless precision matters.
- Always include units implicitly via schema (don’t repeat “m”, “deg” everywhere).

### 6.4 Replace large geometry payloads with hashes + summaries

Never send full section point clouds to the LLM unless the task is explicitly editing them.
Instead send:
- count + station distribution
- min/max beam/draft envelopes
- checksum hash for determinism

### 6.5 “Ask for more lens” is part of the protocol

The agent should be able to request:
- `REQUEST_LENS_EXPANSION(reason, fields_needed)`

That’s how you remain token-bounded while still enabling complex designs.

---

## 7) What v1.2 would implement first (ordered plan)

### Step A — Deterministic lens builder + Lens Pack
- Define `LensSpec` registry (`HULL_FORM`, `STABILITY`, `RESISTANCE`, `STRUCTURE`, etc.)
- Implement canonical JSON encoder + dictionary coding
- Add token budgeting + deterministic drop policy

### Step B — Diff-only patch protocol (DSL patch)
- Define `PatchRequest` / `PatchReceipt`
- Store patch as a first-class history artifact
- Enforce lens safety: patch writes must be subset of allowed write surface

### Step C — Dependency graph + invalidation
- Build dependency graph for:
  - validators/artifacts
  - compiled geometry
  - UI render artifacts
- Mark stale on commit; ensure caches are version-keyed

### Step D — Orchestrator loop + convergence guard
- Implement WorkOrder + router guard (deterministic)
- Implement convergence tracking (thrash/stall budgets)
- Implement human escalation contract

### Step E — Physics envelope contract
- Standardize physics result structure: validity + envelope + alternatives
- Replace “exceptions as gate” with “graded results”

---

## 8) Key design invariants (what must never regress)

- **All mutation is atomic and attributed** (commit carries provenance + explain record)
- **Agent outputs diffs only** (no full state, no full program)
- **Lenses are deterministic query plans** (no “retrieve whatever seems relevant”)
- **Kernel compiles geometry; validation grades reality post-compile**
- **Dependency graph drives invalidation and caching**

---

## 9) Answer to the question: “Could we condense context as vessel context expands?”

Yes. The practical recipe for token efficiency is exactly:

**Lens Pack (dictionary-coded compact JSON text)**  
→ minimal deterministic slice of state + staleness + safe write surface  

**Diff-only DSL edits**  
→ agent returns only changes (CREATE/UPDATE/DELETE/SET/CONSTRAIN)  

**Deterministic lens builder**  
→ stable, budgeted, repeatable retrieval (no drift)  

**Dependency graph**  
→ invalidation + caching + minimal lens selection  

Binary “file types” don’t help unless you also have a reliable tool protocol for the LLM to fetch/decode them; the most effective approach inside LLM token constraints is compact JSON + dictionary coding + deterministic lensing.


