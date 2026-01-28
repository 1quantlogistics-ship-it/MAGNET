## MAGNET Prompt Architecture Audit (Active vs. Dormant Prompts)

### Why this audit
You’re right to be cautious: MAGNET contains multiple prompt templates, and **not all of them are on the hot path** for Studio UI v2. This audit distinguishes:
- **Active/runtime prompts**: referenced by the actual request paths the UI/agents call.
- **Dormant/library prompts**: present in repo but not currently invoked by UI v2 (or only used in legacy/optional endpoints).

### Method (how “active” was determined)
I did *not* assume prompts are used just because they exist. I:
- searched for `system_prompt=` call sites and traced them to concrete services/endpoints
- cross-referenced with the UI v2 integration paths (`/api/v1/designs/{id}/spiral/*`, `/why`, `/explain`)
- identified legacy endpoints / modules that are present but not used by UI v2 by default

---

## 1) Active prompts (confirmed in-service)

### 1.1 Geometry proposal (Spiral chat → geometry program)
- **File**: `magnet/agents/geometry_proposer.py`
- **Prompt**: `GEOMETRY_PROPOSER_SYSTEM_PROMPT`
- **Call site**: `GeometryProposer.propose()` calls `llm.complete_json(..., system_prompt=GEOMETRY_PROPOSER_SYSTEM_PROMPT, response_model=DesignProgram)`
- **Status**: **ACTIVE** (this is the primary LLM prompt behind UI v2 spiral chat)

#### Contract coverage in prompt (already good)
The system prompt already encodes the key geometry contracts:
- polygon section points are strictly `[[y,z],...]` (no `[x,y,z]`)
- sections are OPEN curves keel→deck, strictly increasing z
- half-breadth only; no signed port/starboard in points
- per-body consistent point counts
- explicitly warns about insufficient stations (7–11, recommended station distribution)

#### Gap discovered via real failure
Despite the above, we saw the runtime error:
> “Too few sections for lofted surface… got 5. Use 7–11 stations…”

This proves that **prompt guidance alone is not sufficient** under real model behavior.

✅ Production mitigation now exists: the proposer now **auto-densifies sections** to ≥7 when a lofted surface exists (repair-and-continue).

#### Critical hole: “auto-densification” is not a structural solution
The densification repair is useful as a **safety net**, but it is not sufficient as the primary quality mechanism:
- If the LLM emits only bow + stern sections, linear interpolation manufactures a “boxy” hull and loses longitudinal curvature intent.
- If the LLM emits <2 sections, densification cannot interpolate at all (and the system must still fail/clarify).

**Structural fix (recommended)**:
- Make **station distribution** a first-class contract in the geometry proposer:
  - If a lofted surface is created, the agent must provide ≥7 sections at a prescribed station set
    (e.g. `[0.0, 0.05, 0.10, 0.30, 0.50, 0.70, 0.90, 0.95, 1.0]`)
  - The compiler/kernel is responsible for **high-fidelity meshing** between those stations (resampling for render quality),
    but it must not invent missing geometric intent.

#### Prompt updates required (not optional)
Update `GEOMETRY_PROPOSER_SYSTEM_PROMPT` to include:
- A hard validation-aware rule:
  - “If you CREATE a `geometry.surface` with `definition='lofted'`, you MUST emit ≥7 `geometry.section` for that `body_id`
     at explicit stations (denser near bow/transom) or the program will be rejected.”
- A canonical station set example (7–11 stations).
- A recommendation to include `section_ids` in the surface definition for determinism.

---

### 1.2 Sketch interpretation (Spiral sketch → extracted geometry intent)
- **File**: `magnet/agents/vision_interpreter.py`
- **Prompt**: `VISION_INTERPRETER_SYSTEM_PROMPT`
- **Call site**: `VisionInterpreter.interpret_sketch()` calls `complete_with_image(..., system_prompt=VISION_INTERPRETER_SYSTEM_PROMPT)`
- **Status**: **ACTIVE** when sketch upload is used in UI v2.

#### Contract alignment
This prompt is deliberately “geometry-only” and forbids type-enums (catamaran/monohull/etc.). That is consistent with the “no hidden enums” doctrine.

---

## 2) Prompts that exist and are used by services, but are not on the core UI v2 spiral path by default

These are “in service” in the codebase, but **not necessarily exercised in your current Studio UI v2 workflow** unless you hit specific endpoints/features.

### 2.1 Clarification prompts
- **Files**:
  - `magnet/llm/prompts/clarification.py`
  - `magnet/llm/services/clarification_service.py`
- **Prompts**:
  - `CLARIFICATION_SYSTEM_PROMPT`
  - `INTENT_PARSING_SYSTEM_PROMPT`
- **Status**: **POTENTIALLY ACTIVE** depending on which components call `ClarificationService`.

#### Audit finding (possible doctrinal drift)
`create_vessel_type_clarification()` enumerates vessel categories (patrol/workboat/ferry…).
That’s fine for a UI question, but it **can re-introduce taxonomy** into an architecture that’s trying to be geometry-first.

#### Critical hole: “vessel type” paradox in downstream modules
Multiple downstream modules still branch on a `vessel_type` label (margins, cost models, rule applicability). Removing “vessel type”
from clarifications without a translation layer can cause incorrect defaults (“unknown/commercial”) and wrong margins.

**Right-way recommendation (transitional architecture)**:
- Keep the UI surface “mission + constraints” oriented, but implement a **Mission Interpreter** that derives:
  - the legacy `mission.vessel_type` label needed by downstream modules **from mission goals**
  - and eventually migrates those modules toward parameter-driven behavior.

This avoids “hidden enums” in agent prompts while still satisfying current downstream expectations.

---

### 2.2 Explanation prompts
- **Files**:
  - `magnet/llm/prompts/explanation.py`
  - `magnet/llm/services/explanation_service.py`
- **Prompts**:
  - `EXPLANATION_SYSTEM_PROMPT`
  - `NARRATIVE_SYSTEM_PROMPT`
- **Status**: **POTENTIALLY ACTIVE** (used by explanation/report-style features).

#### Audit finding (outdated path/phase tokens)
In `create_next_steps_prompt()`:
- references `mission.vessel_type` (may be fine)
- references `hull.length` (likely **non-canonical**; MAGNET uses `hull.loa`/`hull.lwl`)

In `ExplanationService._fallback_next_steps()`:
- uses legacy phase ids: `["mission", "hull_form", "arrangement", "stability", "compliance"]`

**Recommendation**:
This drift is likely **caused by display-name aliasing**, not just prompt text.

**Required fixes**:
- Scrub `PARAMETER_DISPLAY_NAMES` in `magnet/llm/prompts/explanation.py`:
  - remove `hull.length`
  - use only canonical keys (`hull.loa`, `hull.lwl`)
- Update `create_next_steps_prompt()` to reference canonical keys only.
- Update `ExplanationService._fallback_next_steps()` to use canonical phase IDs (e.g. `hull`, not `hull_form`).

---

### 2.3 Compliance prompts
- **Files**:
  - `magnet/llm/prompts/compliance.py`
  - `magnet/llm/services/compliance_service.py`
- **Status**: **FEATURE-DEPENDENT**

#### Scope expansion (recommended)
Even if compliance is “feature-dependent”, the prompt assets are technical debt and can drift.
Audit now prevents a second drift event when compliance is activated in UI.

---

### 2.4 Routing prompts
- **Files**:
  - `magnet/llm/prompts/routing.py`
  - `magnet/llm/services/routing_service.py`
- **Status**: **FEATURE-DEPENDENT** (systems routing module)

#### Scope expansion (recommended)
Same rationale as compliance: audit now to prevent drift later.

---

## 3) Known “in-code but likely not used by UI v2” prompts

### Translator prompt in `magnet/deployment/api.py`
There is a dynamic translator system prompt builder used in the API layer (search hit: `_build_translator_system_prompt()`).

**Status**: likely **legacy / optional** (UI v2’s current “authority path” goes through `/spiral/chat`).

Recommendation:
- keep it, but treat it as “non-primary” unless you re-enable an intent-preview workflow.

---

## 4) Production prompt hardening plan (what to change)

### MUST-do prompt changes (high impact)
1) **Geometry proposer**: add a hard validation-aware rule for lofted station counts (≥7).
2) **Explanation next-steps**: update canonical path and phase names (`hull.loa`, `hull` not `hull_form`).
3) **Clarification “vessel type”**: shift to mission/constraints instead of taxonomy labels.

### Replace brittle prompt string tests with output-based regression
String matching on prompts is brittle and does not ensure model behavior.

**Right-way test strategy**: Golden-path, output-based regression tests that assert invariants on the produced `DesignProgram`:
- For each lofted body: ≥7 sections
- Station distribution matches a minimum set (or passes a spacing validator)
- No non-canonical keys appear (e.g. `hull.length`)
- Consistent point count across sections per body

These tests should run in CI and fail on regressions (prompt drift or LLM/provider changes).

---

## 5) Bottom line
- The **core spiral prompts are active** and already have strong contracts.
- The real-world “5 sections” failure shows prompt text alone is insufficient; production requires **deterministic repair** (now implemented) plus **explicit prompt reinforcement**.
- Several non-spiral prompt templates include **legacy phase names** and **non-canonical paths**; these won’t necessarily break your current UI v2 flow, but they are real drift risks for production-grade behavior.

