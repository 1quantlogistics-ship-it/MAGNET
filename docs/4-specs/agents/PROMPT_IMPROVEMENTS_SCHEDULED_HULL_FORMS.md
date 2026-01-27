### Implementation Plan: Grammar‑First “Vessel Thinking Pass” (No Enums, No DOF Candidates)

Goal: Make the LLM reliably “think about the vessel” and avoid generic constant-shape outputs **without** introducing hull-type enums and without requiring users to specify point-by-point geometry.

Core idea (North Star aligned): require a machine-parseable **thinking artifact** where the model:
1) invents the applicable DOFs using a tiny **grammar** (no candidate menu),
2) defines computable checks for its own DOFs,
3) generates geometry via the existing geometry DSL,
4) produces a closure proof that can be re-executed server-side.

---

## Diagnosis (current failure modes we must close)

This guide is intended to read as both a **diagnosis** and an **implementation plan** an agent can execute.

### Failure mode A — “Split brain” DOFs (proof passes, geometry stays generic)
- The model can emit a valid `VESSEL_THINKING_PASS` (DOFs + checks + proof) **without** implementing those DOFs in `GEOMETRY_PROGRAM`.
- Result: “PASS” proof but a **prismatic wedge** (minimal section-to-section variation).
- Root cause: v0 re-exec checks operate on the thinking payload (DOF anchor points), not on **geometry-derived observables**.

### Failure mode B — Prompt Z-axis contradiction (ambiguous coordinate frame)
- The GeometryProposer prompt currently asserts both:
  - baseline convention (“z=0 baseline; waterline is z=draft”), and
  - “z should be negative below waterline”.
- This ambiguity makes DOF binding and observation targets unreliable.

Note: A standalone audit doc is helpful, but the diagnosis above is intentionally self-contained so the plan stays executable even if audits move/are deleted.

---

## Why this approach (vs. templates or hidden structural enums)

The failure mode we’re fighting is not “the model can’t generate points,” it’s “it silently defaults key shape laws to constants,” and then produces a hull that is technically valid but visually generic.

Instead of hardcoding “Viking means X,” we enforce a mechanically checkable loop:
1) **Thinking Grammar**: model invents DOFs (scalar/schedule/track/body)
2) **Verification Grammar**: model defines checks (range/monotonic/varies/coverage/uniform/correspondence)
3) **Geometry Program**: model emits existing geometry DSL (CREATE/UPDATE/LOFT/SET)
4) **Closure Proof**: model reports PASS/FAIL for every check it promised (and we can re-run them server-side)

This stays enum-free because the system never hardcodes “what a chine is” or “what a sportfisher is”:
- the model chooses DOFs freely
- the system only understands the grammar primitives and generic checks

---

## Design constraints (North Star alignment)

- **No enum contracts**: no `hull_type="viking"` or “template selection”.
- **Truth spine preserved**: output is explicit `geometry.*` primitives; no visual-only hacks.
- **Fail-closed remains**: kernel must continue to reject missing intent; proposer must make intent explicit.
- **No silent defaults**: any invented DOF not set explicitly must be labeled DEFAULTED with consequences.
- **One-regeneration rule**: allow a single targeted patch pass if proof fails (no infinite loops).
- **Geometry DSL unchanged**: we add a “thinking layer” alongside the existing geometry DSL, not replace it.
- **LLM = dynamic prior generator, not decision engine**: the model may *propose* DOFs/relationships, but the kernel must enforce, execute, and verify deterministically.

---

## Repo map (what exists today, where to hook)

### Existing Geometry Program DSL pipeline (unchanged)

- **User → spiral endpoint**: `magnet/deployment/spiral_endpoints.py` (`spiral_chat`)
- **NL → program generation**: `magnet/agents/geometry_proposer.py` (`GeometryProposer.propose`)
- **Geometry DSL execution**: `magnet/kernel/program_executor.py` (`execute_program`)
- **DSL parse → AST**: `magnet/kernel/stdlib/parser.py`, node types in `magnet/kernel/stdlib/ast_nodes.py`
- **AST expand → actions**: `magnet/kernel/stdlib/expander.py` (`expand`)
- **Compile to HullGeometry**: `magnet/kernel/stdlib/compiler.py` (`compile_to_geometry`)  
  (This is where `MissingSurfaceIntentError` is raised if intent is missing.)

### Existing “Vault” receipt plumbing (keep aligned)

- Turn contracts + typed receipts: `magnet/core/dataclasses.py` (`TurnContract`, `PhaseReceipt`, `ValidatorReceipt`, `SceneReceipt`)
- Signing on phase completion: `magnet/kernel/conductor.py` (`Conductor.run_phase`)
- AUTHORITATIVE gating: `magnet/webgl/geometry_service.py` (contract gating + scene receipt)

### New code to add (thinking layer)

- **Typed schema**: `magnet/agents/vessel_thinking_schema.py`
- **Validator / check executor**: `magnet/agents/vessel_thinking_validator.py`
- **Observable registry + computation**: `magnet/agents/geometry_observables.py` (new)

---

## Implementation steps

### Step 1 — Add a “Thinking DSL” alongside the existing geometry DSL

**Files**
- `magnet/agents/geometry_proposer.py` (`GEOMETRY_PROPOSER_SYSTEM_PROMPT`)

**Change**
Wrap the existing prompt with a non-negotiable output structure of **two artifacts**:

- (A) `VESSEL_THINKING_PASS` (JSON, validated)
- (B) `GEOMETRY_PROGRAM` (existing DSL, unchanged)

This is not a capability map; it is a required, typed reasoning artifact.

**Acceptance**
- If (A) JSON doesn’t parse, the request fails fast (retry once).
- If (A) parses but has missing coverage, it fails fast (retry once).
- Geometry is not executed unless (A) is valid.

**Reality check (current gap discovered in live UI)**
- A “valid” thinking pass can still produce a **prismatic wedge** if the geometry program does not implement the DOFs.
- This happens because v0 re-exec checks operate on DOF anchor points inside the thinking payload, not on geometry-derived observables.

---

### Step 2 — Define the grammar (no DOF candidates, no examples in code)

**Files**
- `magnet/agents/geometry_proposer.py` (system prompt wrapper text)
- Add: `magnet/agents/vessel_thinking_schema.py` (Pydantic models)

**Change**
Define a minimal grammar for:

**DOF_SCHEMA primitives**
- `scalar(name, units, value, defaulted?, consequence?)`
- `schedule(name, domain=[0,1], anchor_points=[{x,value}], interpolation, defaulted?, consequence?)`
- `track(name, anchor_rule, body_coverage, defaulted?, consequence?)`
- `body(name, station_count, point_count_per_station)`

**VERIFICATION_SCHEMA checks**
- `range(target, min, max)`
- `monotonic(target, direction=increasing|decreasing|either)`
- `varies(target)` (not constant)
- `coverage(track, expected_stations)`
- `uniform(body, attribute)`
- `correspondence(body_a, body_b, rule)`

We do **not** encode any domain-specific DOFs in code (no “sheer_z” list).
The model invents DOFs, but must express them in this grammar.

**Refinement (1) — Typed params (prevent arbitrary shapes)**
Implement the “grammar” as a **typed union** of Pydantic models instead of a freeform `params: {}` blob.
This prevents the model from inventing param shapes the validator cannot execute.

Recommended models (illustrative):
- `ScalarDOF`: `name, units, value, defaulted, consequence`
- `ScheduleDOF`: `name, domain, anchor_points[{x,value}], interpolation, defaulted, consequence`
- `TrackDOF`: `name, anchor_rule, body_coverage, defaulted, consequence`
- `BodyDOF`: `name, station_count, point_count_per_station`

Checks should also be typed unions (e.g., `RangeCheck`, `MonotonicCheck`, etc.) so `target` + `params` are consistently shaped.

---

### Step 3 — Require a machine-checkable `VESSEL_THINKING_PASS` JSON payload

**Files**
- `magnet/agents/geometry_proposer.py` (system prompt)
- Add: `magnet/agents/vessel_thinking_schema.py`

**Change**
Require `VESSEL_THINKING_PASS` JSON with:
- **Refinement (5) — station_plan is mandatory metadata (not a DOF)**:
  - `station_plan: { count, distribution | explicit_xs, rationale }`
  - Rationale: station plan affects *every* schedule and is a common source of “generic” results.
- `dof_schema: list[DOFEntry]` (typed union)
- `verification_schema: list[CheckEntry]` (typed union)
- `closure_proof: list[ProofEntry]`
- optional: `realism_audit: str` (2 sentences, human review only)

Coverage rules enforced server-side:
- Every **non-defaulted** DOF must have ≥1 check
- Every check must have a proof entry
- Proof must cover exactly the check set (no omissions)

**Acceptance**
- Invalid/missing JSON blocks are caught before any geometry executes.

**Refinement (4) — NEEDS_CLARIFICATION is a first-class JSON variant**
Define a valid alternative response shape:
- `{ "status": "NEEDS_CLARIFICATION", "question": "..." }` (exactly one question)

And make the response type a union:
- `Union[VesselThinkingPass, NeedsClarification]`

This prevents “half a schema + a question” outputs and makes the workflow mechanically enforceable.

---

### Step 4 — Implement thin validation + optional server-side re-execution of checks

**Files**
- `magnet/agents/geometry_proposer.py` (parsing the JSON block + retry once)
- Add: `magnet/agents/vessel_thinking_validator.py` (generic check executor)
- `magnet/deployment/spiral_endpoints.py` (surface actionable feedback on proof failure)

**Change**
Validation stages:
1) Parse and validate `VESSEL_THINKING_PASS` with Pydantic (reject malformed)
2) Coverage checks (DOFs ↔ checks ↔ proof entries)
3) (Optional but recommended) Re-execute verification checks server-side against the generated geometry summary and compare to reported proof to catch hallucinated proofs.

One targeted regenerate:
- if proof fails (either by model’s own report or server-side re-exec), retry once with targeted patch instruction.

**Refinement (3) — Specify retry instruction shape**
When retrying, the system should feed back a structured patch instruction:

- `failed_check_names`: list of check ids
- `computed`: the computed values
- `expected`: the expected criteria from the check params
- instruction: “Regenerate ONLY the affected DOFs and the minimal geometry edits needed; do not restart from scratch.”

This keeps the one retry focused and avoids “full reset” behavior.

**Where to implement this concretely**

- **Prompting + parsing**: in `magnet/agents/geometry_proposer.py` inside `GeometryProposer.propose`:
  - switch from “return only DesignProgram JSON” to returning **two artifacts**:
    - a `VESSEL_THINKING_PASS` JSON block
    - a `GEOMETRY_PROGRAM` text block
  - parse the thinking pass with Pydantic (`vessel_thinking_schema.py`)
  - if valid, extract the geometry program text and continue existing flow (`execute_program`)

- **Failure surfacing**: in `magnet/deployment/spiral_endpoints.py` in `spiral_chat`:
  - map thinking-pass failures to `status="needs_clarification"` with one actionable question
  - never execute the geometry program when thinking pass fails

- **Optional server-side re-exec**:
  - compute geometry summaries from the program text (preferred) or from compiled geometry (authoritative)
  - run checks in `vessel_thinking_validator.py` and compare to model-reported `closure_proof`

---

### Step 4.5 (v0.1) — Add a DOF→Geometry Binding Table + Observation Targets (no priors, no new agents)

**Why**
Right now the model can “say” schedules vary without binding them to the actual `geometry.section.points` it emits.  
We need a small structural addition that forces *accountable linkage*:

- **Binding Table**: “This DOF controls these concrete geometry outputs.”
- **Observation Targets**: “These are the measurable geometry-derived values the kernel will compute to verify the DOF is implemented.”

Think “label stickers + ruler marks”: no stickers → no building; no ruler marks → no proof.

**Files**
- Update: `magnet/agents/vessel_thinking_schema.py`
- Update: `magnet/agents/vessel_thinking_validator.py`
- Update: `magnet/agents/geometry_proposer.py` (prompt wrapper + parsing)
- Add: `magnet/agents/geometry_observables.py` (observable registry + computation)

**Data shape (v0.1 proposal)**
- Add to `VESSEL_THINKING_PASS`:
  - `binding_table: [{ dof_name, binds_to: [...], observation_targets: [...] }]`
  - Where:
    - `binds_to` is a list of **observable ids** from the kernel-computable registry (see `magnet/agents/geometry_observables.py`), e.g.:
      - `section_metric:max_half_beam_m`
      - `section_metric:keel_z_m`
      - `section_metric:sheer_z_m`
      - `section_metric:chine_z_m` (only if a hard edge is present)
    - `observation_targets` describe how to measure:
      - `span_min`: minimum expected span across stations
      - optional station subset, body scope

**Important: this is NOT a hull-type enum**
- DOFs remain **open**: the model may invent any DOF names/types.
- Observables are **closed (for v0.1)**: the model may only claim *verification* against observables the kernel can compute.
- This is the minimum shared language required for deterministic verification.

**VERIFIED vs UNVERIFIED DOFs (v0.1 rule)**
- A DOF **with** a binding_table entry is **VERIFIED**.
- A DOF **without** a binding_table entry is **UNVERIFIED** and is permitted, but:
  - UNVERIFIED DOFs may not have `range` / `monotonic` / `varies` checks.
  - UNVERIFIED DOFs must be either:
    - `defaulted=true` (with `consequence`), or
    - explicit but recorded-only (no checks, no proof claims).

**Handling (fail-closed)**
- If a DOF is **non-defaulted** and has checks, but has **no binding_table entry** → reject + retry once.
- If binding exists but observation targets are not measurable (e.g., references unknown metric) → reject + retry once.

**Multiple DOFs binding to the same metric**
- Allowed with **no special handling**.
- The geometry-derived observable is the arbiter; each DOF’s checks run against the same computed values.

**Done when**
- The system cannot accept a thinking pass that claims variation unless it explicitly declares:
  - where that variation appears in geometry, and
  - how the server will measure it.

---

### Step 5 — Persistence + observability (ties into TurnContract Vault)

Prompt-only changes help, but the most reliable enforcement is:
- parse the three blocks
- accept only if blocks exist

**Files**
- `magnet/core/dataclasses.py` (extend `TurnContract` receipts or reuse existing `details`)
- `magnet/kernel/conductor.py` (store thinking artifact reference in receipt bundle)

**Change**
Store the raw `VESSEL_THINKING_PASS` JSON (or a hash/ref) as part of the turn receipt bundle.
This makes “why is this generic?” auditable:
- the DOFs it chose
- what it defaulted
- what it claimed to verify

**Acceptance**
- If the model emits only the geometry program without the thinking pass JSON, reject and retry once with the strict wrapper.

**Concrete persistence locations**
- Store the raw JSON in `TurnContract.phase_receipt.details` (v0) or add a dedicated field (v1) in `magnet/core/dataclasses.py`.
- Ensure it is excluded from deterministic snapshot hashing (hash helpers live in `magnet/core/turn_contracts.py`).

---

### Step 6 — Add acceptance tests (black-box, enum-free)

**Files**
- Add: `tests/agents/test_vessel_thinking_pass_validation.py`

**Test strategy**
Mock the LLM output and assert:
- JSON parses and coverage rules hold
- server-side re-exec catches mismatched proofs
- geometry is not executed if thinking pass fails (no state mutation)

**Concrete test harness suggestions**
- Add unit tests around the new parser in `magnet/agents/geometry_proposer.py` using a FakeLLM pattern (see `tests/agents/test_geometry_proposer_invalid_json.py`).
- Add one integration-ish test against `magnet/kernel/program_executor.execute_program` to prove:
  - thinking-pass failure prevents execution (no design_version bump)

---

### Step 6.1 — Test suite additions required for v0.1 binding + observation targets

These tests are the line between “demo-ready” and “professional”: the system must be unable to claim varied DOFs while building a wedge.

**Add tests**
- Add: `tests/agents/test_vessel_thinking_binding_table.py`
  - **unbound DOF fails closed**:
    - thinking pass contains a non-defaulted schedule DOF + `varies` check
    - but `binding_table` has no entry for that DOF
    - expect proposer returns `THINKING_PASS_INVALID` (after one retry)
  - **unknown observation target fails closed**:
    - `binding_table.binds_to` contains an unknown metric id (e.g., `section_metric:unknown_metric`)
    - expect fail-closed (after one retry)
  - **geometry observation mismatch fails closed**:
    - thinking pass claims `span_min > 0` for an observation target
    - program emits identical sections so computed span is ~0
    - expect fail-closed (after one retry)

**Receipt persistence test**
- Add: `tests/contract/test_thinking_pass_receipt_persistence.py`
  - run a phase after a spiral apply (`run_critical_phases=true`)
  - assert TurnContract contains thinking-pass receipt info in:
    - `TurnContract.phase_receipt.details.vessel_thinking_pass_hash`
    - `TurnContract.phase_receipt.details.vessel_thinking_pass_summary`
    - and (if small enough) the raw thinking payload

---

### Step 6.5 — Coordinate contract consistency (prompt hygiene; prevents DOF confusion)

**Why**
If the coordinate conventions are inconsistent, the model can’t reliably bind DOFs to geometry, and “observation targets” become ambiguous.

**Evidence**
`magnet/agents/geometry_proposer.py` currently contains a contradictory Z convention:
- “Z=0 baseline; waterline is z=draft”
- also “Z should be NEGATIVE below waterline”

**Decision (v0.1)**
- **Option A (baseline-up)**: `z=0` at baseline/keel, positive up. Waterline at `z=draft`.

This must be unified so the “binding table + observation targets” has a single reference frame.

**Files**
- Update: `magnet/agents/geometry_proposer.py` prompt text + examples
- (Optionally) align the referenced doc: `docs/0-architecture/GEOMETRY_CONVENTIONS.md`

**Done when**
- There is exactly one authoritative Z convention across prompt text + examples.

---

### Terminal failure contract (v0.1, after the single retry)

The system allows exactly **one** targeted retry. If the retry still fails, the behavior must be explicit and fail-closed.

**If retry fails**
- Return a terminal status indicating generation failure (e.g., `status="generation_failed"` or `status="needs_clarification"` with an explicit “cannot satisfy checks” message; pick one for UI contract consistency).
- Include:
  - `failed_checks`
  - `last_computed_values`
  - `expected` criteria
- Do **not** execute geometry.
- UI message: “I couldn’t generate geometry that meets the constraints. [Show details] or [Try simpler request].”

## Recommended “drop-in” prompt wrapper (for `GEOMETRY_PROPOSER_SYSTEM_PROMPT`)

You are designing a vessel via geometry primitives.
You must FIRST perform a “Vessel Thinking Pass” before generating points.

NON-NEGOTIABLE: Output TWO artifacts:
1) VESSEL_THINKING_PASS (JSON, will be validated)
2) GEOMETRY_PROGRAM (existing DSL)

VESSEL_THINKING_PASS (JSON):
{
  "station_plan": {
    "count": 21,
    "distribution": "end-dense",
    "explicit_xs": null,
    "rationale": "..."
  },
  "dof_schema": [
    {"name": "...", "type": "scalar|schedule|track|body", "params": {...}, "defaulted": false, "consequence": null}
  ],
  "verification_schema": [
    {"name": "...", "type": "range|monotonic|varies|coverage|uniform|correspondence", "target": "dof_name", "params": {...}}
  ],
  "closure_proof": [
    {"check_name": "...", "computed": {...}, "result": "PASS|FAIL"}
  ],
  "realism_audit": "Two sentences: why these DOFs are sufficient to avoid generic extruded shapes."
}

Rules:
- You choose what DOFs exist. There is no required list and no domain-specific menu.
- Every DOF is EXPLICIT or DEFAULTED (DEFAULTED requires consequence).
- Every non-defaulted DOF has ≥1 check.
- Every check must appear in closure_proof.
- If you cannot determine enough DOFs, return NEEDS_CLARIFICATION with a single question; do not generate geometry.

GEOMETRY_PROGRAM (existing DSL):
- Generate geometry that implements your DOF_SCHEMA.
- Preserve point correspondence per body and explicit station ordering via surface.section_ids.

If any check FAILs: regenerate once with a targeted patch. Do not restart from scratch.

---

## What good looks like (user experience)

User can type:
> “Create a 72ft planing sportfisher hull with fine entry, strong forward flare, warped-V bottom, crisp transom.”

And the system:
- derives the missing schedules automatically (or declares defaults + consequences)
- proves it actually varied the right longitudinal laws
- produces geometry that is both valid and non-generic

---

## Agent execution checklist (what to implement, in order)

1) **Add typed Pydantic models**
   - Create `magnet/agents/vessel_thinking_schema.py` with typed unions for:
     - DOFs: scalar/schedule/track/body
     - checks: range/monotonic/varies/coverage/uniform/correspondence
     - proof entries, and NeedsClarification union variant

2) **Update `GeometryProposer` prompting**
   - Modify `magnet/agents/geometry_proposer.py` to request:
     - `VESSEL_THINKING_PASS` JSON
     - `GEOMETRY_PROGRAM` DSL text
   - Implement parsing + one retry before returning failure.

3) **Implement generic check re-execution**
   - Create `magnet/agents/vessel_thinking_validator.py`
   - v0: implement only the checks you can compute deterministically from:
     - `station_plan` + section definitions in the DSL program
     - and/or compiled HullGeometry when needed

4) **Wire failures into spiral UX**
   - In `magnet/deployment/spiral_endpoints.py`, map:
     - needs clarification → `status="needs_clarification"`
     - proof failure → one retry instruction (server-generated), else needs_clarification

5) **Persist artifact into TurnContract**
   - Add to receipt bundle (details) without changing integrity policy.

6) **Tests**
   - Add `tests/agents/test_vessel_thinking_pass_validation.py`
   - Ensure existing contract/invariant suites stay green.

