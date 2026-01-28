## MAGNET Prompt Architecture Implementation Guide (Production-Grade)

### Objective
Make MAGNET’s agent prompting **structurally reliable** and aligned with:
- geometry contracts (2D `[y,z]`, open keel→deck curves, consistent point counts)
- lofting station requirements (≥7 sections per lofted body)
- canonical schema keys (`hull.loa`, not `hull.length`)
- the current reality that some downstream modules still depend on `mission.vessel_type`

This guide implements the “right way” improvements identified in `PROMPT_ARCHITECTURE_AUDIT.md`.

---

## 1) Replace “manufactured densification” with a station distribution contract

### 1.1 What to change
**File**: `magnet/agents/geometry_proposer.py`  
**Prompt**: `GEOMETRY_PROPOSER_SYSTEM_PROMPT`

Add a **hard contract**:
- If creating a `geometry.surface` with `definition="lofted"` for `body_id=B`, the program MUST include:
  - ≥7 `geometry.section` for that `body_id`
  - at explicit stations (denser near bow/transom)

Recommended canonical station set:
- 7 stations (minimum): `[0.00, 0.05, 0.15, 0.35, 0.50, 0.70, 0.90]`
- 9 stations (better): `[0.00, 0.05, 0.10, 0.30, 0.50, 0.70, 0.90, 0.95, 1.00]`
- 11 stations (best demo): `[0.00, 0.03, 0.07, 0.15, 0.30, 0.45, 0.55, 0.70, 0.85, 0.93, 1.00]`

### 1.2 What NOT to do
- Do not rely on linear interpolation as the primary mechanism for hull fairness.
- Compiler/mesher may resample for render quality, but it must not invent missing intent.

### 1.3 Validation enforcement
**File**: `magnet/agents/geometry_proposer.py`  
**Function**: `_validate_program()`

Strengthen the validator so it checks:
- when a lofted surface exists:
  - ≥7 sections for that body
  - station distribution is sufficiently “end-dense” (at least one station ≤0.10 and ≥0.90)
  - (optional) no station gaps larger than a threshold (e.g. max Δstation ≤0.35)

---

## 2) Scrub canonical drift at the source (display names + templates)

### 2.1 Remove legacy aliases that teach the LLM wrong keys
**File**: `magnet/llm/prompts/explanation.py`

Actions:
- Remove `PARAMETER_DISPLAY_NAMES["hull.length"]`.
- Use `hull.loa` and/or `hull.lwl` exclusively.
- Update `create_next_steps_prompt()` to reference canonical keys only.

### 2.2 Fix “fallback next steps” phase tokens
**File**: `magnet/llm/services/explanation_service.py`

Actions:
- Replace legacy phase IDs like `hull_form` with canonical `hull`

---

## 3) Bridge the “vessel type paradox” with a Mission Interpreter

### 3.1 Why this is required
Even if MAGNET is geometry-first, some downstream modules still branch on a label:
- weight margins
- cost estimation
- rule applicability

Removing vessel type prompts without providing a mapping will degrade correctness.

### 3.2 Implementation
Create a deterministic mapping layer:
- **New file (recommended)**: `magnet/mission/interpreter.py`
- Input: mission constraints (speed, range, payload, crew, operating profile)
- Output:
  - canonical parameter suggestions
  - a legacy-compatible `mission.vessel_type` label (until refactors remove it)

### 3.3 Usage
Call Mission Interpreter when:
- spiral chat applies a new design with missing `mission.vessel_type`
- or clarification resolves mission goals but doesn’t set a label

Constraint:
- The mapping must be explicit, logged, and overrideable (human-in-the-loop).

---

## 4) Replace prompt string tests with output-based regression (CI)

### 4.1 Add golden-path tests for agent outputs
**New tests directory (recommended)**: `tests/prompts/`

Add tests that run the agent (or deterministic fallback) and assert invariants on the resulting `DesignProgram`:
- ≥7 sections per lofted body
- consistent per-body point counts
- points are 2D `[y,z]`
- z strictly increasing
- no forbidden keys (`hull.length`, hull.* feature-like paths)
- station distribution rule passes (end-dense)

### 4.2 Test set (minimum)
Create ~5 prompt fixtures like:
- “Design a 25m fast ferry…”
- “Design a 12m planing patrol craft…”
- “Design a catamaran with S/L=0.6…”
- “Add spray rails…”
- “Make it more stable…”

### 4.3 Determinism strategy
For CI reliability:
- Prefer running the agent in “offline” mode when network is unavailable, OR
- Record golden `DesignProgram` artifacts and validate the invariants directly, OR
- Run LLM-backed tests only in a gated pipeline with keys present.

---

## 5) Audit “dormant” prompts now to prevent future drift

Even if not currently wired in UI:
- `magnet/llm/prompts/compliance.py`
- `magnet/llm/prompts/routing.py`

Actions:
- scan for non-canonical keys and legacy phase names
- remove taxonomy-heavy language where possible
- add parameter-driven language and canonical keys

---

## 6) Definition of Done
- Geometry proposer prompt enforces ≥7 station distribution for lofted bodies.
- `_validate_program()` rejects “lofted surface + too few sections” deterministically.
- Explanation prompts/services contain **no** `hull.length` aliasing.
- A Mission Interpreter exists and is used to populate `mission.vessel_type` when required.
- CI has output-based regression tests enforcing `DesignProgram` invariants.

