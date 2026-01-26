### Viking v2 → v3 Iteration Audit (Edit vs Rewrite) + Implementation Fix Plan

**Design**: `storage/designs/MAGNET-20260118-8D2F7D5D.json`  
**Evidence sources**:
- v2 `program_text`: `phase_states.hull_form.spiral.checkpoints[0]` (design_version=1)
- v3 `program_text`: `phase_states.hull_form.spiral.checkpoints[1]` (design_version=3)
- Turn ledger: `storage/designs/MAGNET-20260118-8D2F7D5D/turns.jsonl`

---

### 0) Executive summary
- **This was a REWRITE, not an EDIT.**
- v3 re-authored the hull shell as a new program (re-`CREATE` body, added/removed section IDs, changed station plan density), which breaks “preserve identity, mutate deltas”.
- At the time this design was created, **the enforcement artifact (`metadata.vessel_thinking_pass`) was not persisted**, so we cannot audit v2 vs v3 bindings/targets from state.
- Even if thinking-pass validation existed, **there was no server-side “edit boundary” gate** to prevent a rewrite-shaped program from being applied to an existing hull.

---

### 0.1) Recovery (do this first — keep the working hull)
**Goal**: do not lose the v2 hull while fixing the pipeline.

- **Rollback to v2** by restoring checkpoint 1 program_text (design_version=1) as the active hull-form program for this design.
- Only after the design is stable again, proceed with the enforcement fixes below.

---

### 1) Diagnostic Q1 — Was v3 an EDIT or REWRITE?
**Answer: REWRITE.**

**Why (mechanically):**
- v3 uses **`CREATE` for `geometry.body` and all `geometry.section` resources**, even though the design already contained those IDs from v2.
- Our DSL expander currently treats `CREATE` as a **set/overwrite** into `resources.{id}` (no “resource already exists” error), so `CREATE` functions as an **upsert rewrite** in practice.
- v3 **changes identity anchors**:
  - Section ID set changes (adds/removes IDs)
  - Section count changes
  - Section station distribution changes (inserts new stations)

**Identity deltas (v2 → v3):**
- **Section count**: v2 = **10**, v3 = **11**
- **Section ID set**:
  - **Removed**: `section_forward`, `section_transom_forward`
  - **Added**: `section_forward_1`, `section_forward_2`, `section_forward_mid`
- **Common IDs**: 8

---

### 2) Diagnostic Q2 — Pull both thinking passes (v2 and v3)
**Answer: Not available for this design.**

For `MAGNET-20260118-8D2F7D5D`:
- `metadata.vessel_thinking_pass`: **missing**
- `metadata.vessel_thinking_pass_hash`: **missing**
- `turns.jsonl`: contains turn summaries + program_text only; **no thinking pass artifact**

**Implication**: we cannot prove v2/v3 bindings/targets were enforced for this run; the only “audit” we can do is program diffs and geometry measurements.

**Note**: the codebase now includes a fix to fail-closed if `vessel_thinking_pass` is missing and to persist the artifact atomically, but it landed **after** this design was created.

---

### 3) Diagnostic Q3 — Compare program_text between v2 and v3
**High-level diff summary**
- v3 modifies nearly every section’s `points` and `edge_types`, and also redefines the surface and adds a discontinuity.
- v3 also changes section naming + adds intermediate stations forward.

**Minimal excerpt (unified diff head)**:
- v3 redefines body_type and reauthors bow + forward sections; this is not a “delta patch”.

---

### 4) Station convention: why signs/“forward vs aft” can flip
**Canonical kernel contract** (see `magnet/kernel/stdlib/section_compiler.py`):
- `station=0.0` is **aft/AP** → `x=0`
- `station=1.0` is **forward/FP** → `x=LOA`

**Observed in these programs**:
- Both v2 and v3 label small station values (e.g. `station: 0.02`) as `section_bow`.
- That implies the model is still thinking “station 0=bow”, which is inverted relative to kernel truth.

**Impact**:
- Any longitudinal observable (e.g., “deadrise drop forward→aft”) becomes ambiguous or wrong if we don’t normalize stations, and `station_range` scoping becomes meaningless.

**Mitigation already implemented (post-hoc)**:
- Proposer-side deterministic normalization that inverts stations when it detects swapped bow/transom naming.
- Prompt + schema descriptions updated to make station 0=aft explicit.

---

### 5) What enforcement *should* have caught before rendering (and didn’t)
There are two distinct enforcement layers:

1) **Thinking-pass enforcement** (bindings/targets):
   - Requires a persisted `VESSEL_THINKING_PASS` artifact so we can audit and re-check commitments.
   - This design has **no persisted artifact**, so auditability fails.

2) **Edit-vs-rewrite boundary** (identity preservation):
   - Even with perfect observables, the system needs a policy that decides:
     - “This is an edit: preserve identity anchors” vs
     - “This is a rewrite: new hull; allow identity reset”
   - That boundary is currently not enforced, so v3 can silently rewrite v2.

---

## Implementation Fix Plan (Minimal, fail-closed)

### A) Make EDIT the default; require explicit REWRITE to break identity
**Goal**: iterations refine the same boat; “rewrite the hull” is an explicit, high-friction action.

**Rule**
- If the design already contains a hull shell (>= 1 `geometry.surface` + >= 7 `geometry.section` for the same body), default to **EDIT mode**.
- A **REWRITE** is allowed **only** if the user explicitly requests it (or confirms it in a clarification prompt).

**EDIT-mode gate (server-side, before execution)**
- Parse the program AST and reject if it:
  - `CREATE geometry.body` with an existing body_id
  - `CREATE geometry.section` with an existing section_id
  - `CREATE geometry.surface` with an existing surface_id
  - changes `geometry.surface.section_ids` ordering/identity (unless explicitly requested)
- Allow only:
  - `UPDATE` to existing IDs
  - optional `CREATE geometry.discontinuity` (if it doesn’t invalidate topological correspondence), or require explicit confirmation

**User-visible failure contract**
- Return `needs_clarification` with:
  - `reason`: `edit_rewrite_boundary_violation`
  - summary of offending operations (first 3)
  - prompt: “Did you mean to rewrite from scratch? yes/no”

---

### A.1) Integration points (“how to wire it”)
This section answers the missing implementation details for A + B1 in terms of MAGNET’s *actual* data/layout.

#### 1) Detect “design has hull”
**State layout** (persisted JSON and `StateManager.to_dict()`):
- **Resources live here**: `state_dict["resources"]` (flat dict keyed by resource_id)
- Each resource dict has `"_type": "geometry.section" | "geometry.surface" | ...` and may have `_deleted: true`.

**Recommended predicate (EDIT default)**:
- `has_surface = any(r["_type"]=="geometry.surface" and not r.get("_deleted") for r in resources.values())`
- `section_body_counts = count live geometry.section grouped by body_id`
- `has_hull_shell = has_surface and any(count>=7 for count in section_body_counts.values())`

#### 2) Parse CREATE statements from `program_text`
Do **not** regex—use the kernel parser:
- `from magnet.kernel.stdlib.parser import parse`
- `ast = parse(program_text)`
- Walk `ast.statements` and inspect `CreateStatement(resource_type, resource_id, properties)`

AST types live in `magnet/kernel/stdlib/ast_nodes.py` (`CreateStatement`, `UpdateStatement`, `SetStatement`, etc.).

#### 3) Get existing resource IDs (and types)
Existing IDs come directly from the resources dict:
- `resources = sm.get("resources", {})` (or `sm.to_dict()["resources"]`)
- `existing_live_ids = {rid for rid,r in resources.items() if isinstance(r,dict) and not r.get("_deleted")}`
- Type lookup: `rtype = resources[rid].get("_type")`

There is **no** `resources["geometry.section.*"]` structure; it’s a flat ID→dict mapping.

#### 4) `needs_clarification` response format
Return `SpiralChatResponse` as defined in `magnet/deployment/spiral_endpoints.py`:
- `status="needs_clarification"`
- `feedback="..."` (human text)
- `clarification_questions=[{id, question, type, options}]`
- `requires_confirmation=True`
- `errors=[...]` (machine text)

#### 5) How REWRITE confirmation flows back
The request already supports a response channel:
- `SpiralChatRequest.clarification_response: Optional[Dict[str,Any]]`

Implementation contract for the edit/rewrite gate:
- On violation: return `needs_clarification` with question id like `edit_rewrite_boundary`.
- On retry: UI sends `clarification_response` containing that id + decision.
- Server bypasses EDIT gate **only if** `clarification_response` explicitly indicates rewrite approval.

#### 6) Proposer prompt changes for EDIT mode
In EDIT mode, the prompt must be explicit:
- “Existing hull resources (EDIT mode): body_id=…, section_ids=[…], surface_ids=[…].”
- “Emit **UPDATE** statements only for existing IDs.”
- “If you believe a rewrite is required, emit ASK requesting rewrite approval; do not CREATE new bodies/sections/surfaces.”

#### 7) Where to inject existing IDs into proposer context
The proposer already accepts `current_state` (`GeometryProposer.propose(..., current_state=...)`).
So we inject IDs by **augmenting the prompt text** in the proposer prompt builder with a small “EDIT MODE” header listing existing IDs.

---

### B) Make CREATE-on-existing illegal (or illegal in EDIT mode)
**Goal**: prevent CREATE from being used as an upsert rewrite accidentally.

**Option B1 (localized / safer)**:
- Only enforce this in spiral EDIT mode (recommended).

**Option B2 (global)**:
- In `magnet/kernel/stdlib/expander.py::_expand_create`, if `resources.{id}` already exists and not `_deleted`, raise `ExpansionError`.
  - This is a broader behavioral change; it may break existing flows relying on CREATE-upsert.

---

### C) Persist thinking pass per iteration (not just “latest”)
**Goal**: make v2→v3 audits possible even after multiple edits.

**Mechanics**
- When spiral commits a turn, append a **turn record field**:
  - `thinking_pass_hash`
  - optionally a bounded `thinking_pass_summary` (counts only)
  - store full thinking pass in state metadata, but also stamp hash into `turns.jsonl`

This makes “pull both thinking passes” always possible from the per-turn ledger.

---

### E) Tests (contracts)
1) **Edit boundary regression**
   - Given existing design with sections, submit “more aggressive …” and assert the system rejects any program that tries to `CREATE geometry.section` for existing IDs.
2) **Thinking-pass per-turn persistence**
   - Assert `turns.jsonl` includes `thinking_pass_hash` for each committed spiral turn.
3) **Station inversion detection**
   - Assert inverted station naming gets normalized (unit test already exists post-fix).

---

### Priority order (updated)
1) **Rollback to v2** (now, keep the working hull)
2) **Implement A + B1** — default EDIT mode + reject CREATE-on-existing in EDIT mode
3) **Implement C** — per-turn thinking pass hash (ledger-ready auditability)
4) **Skip D** — station inversion is already handled by deterministic normalization + docs + tests
5) **Add tests from E**

