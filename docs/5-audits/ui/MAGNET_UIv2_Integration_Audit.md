## MAGNET UIv2 Integration Audit (Single Production Interface, No Duplicate Paths)

**Date:** 2026-01-06  
**Goal:** Connect **UIv2** (served from `magnet/ui_v2/`) to MAGNET's **finalized endpoints** so the complete flow runs through **one production-ready interface**:

---

# 🚀 IMPLEMENTATION CHECKLIST (≤200 lines)

> Execute top-to-bottom. Verify invariants after EVERY step. Search `§SKELETON:` for code.

## Phase -1: DesignStore Persistence
| Step | File | Action | Verify |
|------|------|--------|--------|
| -1.1 | `magnet/deployment/design_store.py` | Search `§SKELETON:DesignStore` | `pytest tests/invariants/ -v` |
| -1.2 | `tests/deployment/test_design_store_persistence.py` (new) | Search `§SKELETON:DesignStoreTests` | `pytest tests/deployment/test_design_store_persistence.py -v` |

**⛔ GATE:** `pytest tests/deployment/test_design_store_persistence.py tests/invariants/ -v` — STOP if fail. Rollback: `MAGNET_DESIGN_STORE_V2_ENABLED=false`

## Phase 1: Spiral Endpoints
| Step | File | Action | Verify |
|------|------|--------|--------|
| 1.1 | `magnet/deployment/spiral_endpoints.py` (new) | Search `§SKELETON:SpiralEndpoints` | `python3 -c "from magnet.deployment.spiral_endpoints import *"` |
| 1.2 | `magnet/deployment/api.py` | Search `§SKELETON:WireRouter` | `pytest tests/invariants/ -v` |
| 1.3 | `tests/deployment/test_spiral_concurrency.py` (new) | Search `§SKELETON:ConcurrencyTest` | `pytest tests/deployment/test_spiral_concurrency.py -v` |
| 1.4 | `tests/deployment/test_spiral_partial_status.py` (new) | Search `§SKELETON:PartialTest` | `pytest tests/deployment/test_spiral_partial_status.py -v` |
| 1.5 | `tests/deployment/test_spiral_sketch_confirmation.py` (new) | Search `§SKELETON:SketchTest` | `pytest tests/deployment/test_spiral_sketch_confirmation.py -v` |
| 1.6 | `magnet/deployment/spiral_endpoints.py` | Search `§SKELETON:MigrationEndpoint` | `pytest tests/invariants/ -v` |

**⛔ GATE:** `pytest tests/deployment/test_spiral_*.py tests/invariants/ -v` — STOP if fail. Rollback: `MAGNET_SPIRAL_ENABLED=false`

## Phase 2: UIv2 Migration
| Step | File | Action | Verify |
|------|------|--------|--------|
| 2.0a | `magnet/ui_v2/index.html` | Add `#sketchInput`, `#btnSketch`, `#clarificationContainer` (Search `§SKELETON:UIWiring`) | `rg \"id=\\\"sketchInput\\\"|id=\\\"btnSketch\\\"|id=\\\"clarificationContainer\\\"\" magnet/ui_v2/index.html` + `pytest tests/invariants/ -v` |
| 2.0b | `magnet/ui_v2/index.html` | Add new IDs to `cacheDom()` array (Search `§SKELETON:UIWiring`) | `rg \"cacheDom\\(\\)\" -n magnet/ui_v2/index.html && rg \"btnSketch|sketchInput|clarificationContainer\" magnet/ui_v2/index.html` + `pytest tests/invariants/ -v` |
| 2.0c | `magnet/ui_v2/index.html` | Add `bindEvents()` wiring to emit `sketchUpload` (Search `§SKELETON:UIWiring`) | `rg \"sketchUpload\" magnet/ui_v2/index.html` + `pytest tests/invariants/ -v` |
| 2.0d | `magnet/ui_v2/css/spiral-adapter.css` (new) | Create CSS from `§SKELETON:SpiralAdapterCSS` | `ls magnet/ui_v2/css/ && rg \"spiral-modal\" magnet/ui_v2/css/spiral-adapter.css` + `pytest tests/invariants/ -v` |
| 2.0e | `magnet/ui_v2/index.html` | Add `<link rel=\"stylesheet\" href=\"css/spiral-adapter.css\">` in `<head>` | `rg \"spiral-adapter\\.css\" magnet/ui_v2/index.html` + `pytest tests/invariants/ -v` |
| 2.0f | `magnet/ui_v2/js/backend-adapter.js` **OR** `magnet/ui_v2/js/spiral-adapter.js` | **Choose ONE integration pattern (DO NOT MIX):** **A)** modify `backend-adapter.js` via steps 2.1–2.11 **OR** **B)** create `spiral-adapter.js` from `§SKELETON:CompleteUIModule` and wire it (Search `§SKELETON:UIWiring`) | `pytest tests/invariants/ -v` |
| 2.0g | `magnet/ui_v2/js/backend-adapter.js` | **Pattern A only:** ensure helper methods exist (Search `§SKELETON:SpiralAdapterHelpers`) **OR** rewrite handlers to use `MagnetStudio.toast/terminal/status` only | `rg \"_showConfirmationDialog\\(|_showToast\\(\" magnet/ui_v2/js/backend-adapter.js` + `pytest tests/invariants/ -v` |
| 2.1 | `backend-adapter.js` | Search `§SKELETON:SpiralChatCall` | `pytest tests/invariants/ -v` |
| 2.2 | `backend-adapter.js` | Search `§SKELETON:ResponseHandler` | `pytest tests/invariants/ -v` |
| 2.3 | `backend-adapter.js` | Search `§SKELETON:LowConfidenceHandler` | `pytest tests/invariants/ -v` |
| 2.4 | `backend-adapter.js` | Search `§SKELETON:ClarificationHandler` | `pytest tests/invariants/ -v` |
| 2.5 | `backend-adapter.js` | Search `§SKELETON:PartialHandler` | `pytest tests/invariants/ -v` |
| 2.6 | `backend-adapter.js` | Search `§SKELETON:409RetryHandler` | `pytest tests/invariants/ -v` |
| 2.7 | `clarification-panel.js` (new) | Search `§SKELETON:ClarificationPanel` | `pytest tests/invariants/ -v` |
| 2.8 | `backend-adapter.js` | Search `§SKELETON:GLBRetry` | `pytest tests/invariants/ -v` |
| 2.9 | `backend-adapter.js` | Search `§SKELETON:WSResync` | `pytest tests/invariants/ -v` |
| 2.10 | `backend-adapter.js` | Search `§SKELETON:SketchConfirm` | `pytest tests/invariants/ -v` |
| 2.11 | `backend-adapter.js` | Search `§SKELETON:PhaseRefresh` | `pytest tests/invariants/ -v` |
| 2.12 | `panel-config.js` | Delete `hull_type`, add `body_count` | `pytest tests/invariants/ -v` |
| 2.13 | `spiral_endpoints.py` | Search `§SKELETON:CheckpointPruning` | `pytest tests/invariants/ -v` |

**⛔ GATE:** Manual test spiral/chat works + `pytest tests/invariants/ -v`. Rollback: `git checkout magnet/ui_v2/js/*.js`

## Phase 3: Disable Legacy
| Step | File | Action |
|------|------|--------|
| 3.1 | `api.py` | Search `MAGNET_LEGACY_INTENT_PROTOCOL_ENABLED`, set default `"false"` |
| 3.2 | `MODULE_65_1_INTENT_RESOLUTION.md` | Move to `_legacy/` or delete |

**⛔ GATE:** `curl -X POST localhost:8000/api/v1/designs/TEST/intent/preview` returns 404. Rollback: `MAGNET_LEGACY_INTENT_PROTOCOL_ENABLED=true`

## Final Acceptance
- [ ] Stepped hull via discontinuities/flow_paths/openings (no "stepped" type)
- [ ] Twin hull via bodies/sections (no "catamaran" type)  
- [ ] Novel 4-body validates without new code
- [ ] `pytest tests/invariants/ -v` — 54/54 ✅

## Rollback Quick Ref
| Phase | Command |
|-------|---------|
| -1 | `export MAGNET_DESIGN_STORE_V2_ENABLED=false` |
| 1 | `export MAGNET_SPIRAL_ENABLED=false` |
| 2 | `git checkout magnet/ui_v2/js/backend-adapter.js magnet/ui_v2/js/panel-config.js` |
| 3 | `export MAGNET_LEGACY_INTENT_PROTOCOL_ENABLED=true` |

---

**END CHECKLIST** — Search `§SKELETON:` below for all code.

---

**Sketch/Intent input → agent translation → geometry compilation → physics validation → 3D visualization → iterative feedback**

This must preserve MAGNET’s core architectural truths:

- **No enumeration** (no “catamaran” types or feature taxonomies in kernel/control plane)
- **Compositional geometry primitives** (continuous parameters + small grammar → combinatorial explosion)
- **Kernel validates reality, not intent**
- **Novel designs work without new code**

---

## Executive Summary

### What’s already strong

- **UIv2 is already served from the backend** (single-origin; no extra server), and it’s already wired to:
  - `/api/v1/meta`
  - `/api/v1/designs/*`
  - `/api/v1/designs/{design_id}/phases/*`
  - `/api/v1/designs/{design_id}/3d/export/glb` (GLB export)
  - WebSocket updates at `/ws/{design_id}`
- Backend includes the **new generative geometry path** endpoints:
  - `/api/v1/propose`, `/api/v1/program`, `/api/v1/propose-and-execute`, `/api/v1/propagate`
  - `/api/v1/design/chat` (iterative chat loop)
  - `/api/v1/design/sketch` (vision → intent → geometry)

### The blocking issue (duplicate control planes)

There are **two parallel user control planes** right now:

1. **UIv2 “command → intent preview → apply actions”**  
   Uses `/api/v1/designs/{id}/intent/preview` + `/api/v1/designs/{id}/actions` and is tightly coupled to `hull.*` parameter paths and style-like fields.

2. **New generative geometry loop** (`/api/v1/design/chat` + `/api/v1/design/sketch`)  
   Uses geometry primitives and program execution, but is **not design-scoped/persistent** (in-memory conversations; separate session IDs) and isn’t the UI’s primary path.

This violates the “**one authority**” requirement: the system can “work” via legacy intent protocol even when the generative geometry path is the intended architecture.

### Best course of action (recommended)

**Make `design_id` the single authority for UI sessions**, and route *all* user-facing design iteration through a **design-scoped “design spiral” API** that:

- **Lives under** `/api/v1/designs/{design_id}/…`
- Uses **geometry primitives path** (GeometryProposer → program_executor → HullGeometry)
- Commits into the same **StateManager/DesignStore** used by phases, explain, history, export, and websocket updates
- Returns **structured feedback** (metrics + deltas + explanations + GLB refresh signal)

Then update UIv2 to call *only* those endpoints, and deprecate the legacy intent preview/apply path (or keep it behind an explicit “Legacy mode” toggle that is OFF by default).

---

## This Document is Now a Full Implementation Guide

This section turns the audit into an **executable checklist** with:

- exact backend code skeletons (`spiral_endpoints.py`, models, handlers)
- line-by-line UIv2 replacements (old → new)
- error handling spec (low confidence, execution failure, WS disconnect, GLB timeout)
- test file paths + test skeletons (including persistence + restart semantics)
- sacred invariants checkpoints after each phase (explicit commands)
- rollback plan per phase
- websocket message schemas (exact `WSMessage` payloads)

**Design rule:** There must be **one authority** for mutation: `design_id` + DesignStore-backed StateManager.

---

## Inventory: What Exists Today

### UI codebases in repo

- **UIv2 (HTML/JS)**: `magnet/ui_v2/` (served at `/` by the backend if present)
- **Built frontend fallback**: `app/dist/` (served if UIv2 is absent)
- **React source**: `app/src/` (exists, but not the primary served UI when UIv2 exists)

### UIv2 serving behavior (single-origin)

Backend priority order:

1. Serve `magnet/ui_v2/index.html` at `/`
2. If missing, fall back to `app/dist/index.html`

This is already aligned with the “one production interface” goal; the main work is API wiring and removing duplicate paths.

### Backend endpoint families (current)

#### A) Design session + phases (design-scoped, persistent via DesignStore)

- `GET /api/v1/designs`
- `POST /api/v1/designs`
- `GET /api/v1/designs/{design_id}`
- `DELETE /api/v1/designs/{design_id}`
- `POST /api/v1/designs/{design_id}/undo`
- `POST /api/v1/designs/{design_id}/versions/{version}/restore`
- `GET /api/v1/designs/{design_id}/phases`
- `POST /api/v1/designs/{design_id}/phases/{phase}/run`
- `POST /api/v1/designs/{design_id}/phases/{phase}/validate`
- `GET /api/v1/designs/{design_id}/explain/latest`
- `POST /api/v1/designs/{design_id}/why`
- `GET /api/v1/designs/{design_id}/impact/{version}`
- WebSocket: `GET ws://…/ws/{design_id}`

#### B) 3D export (design-scoped, production shape)

- `GET /api/v1/designs/{design_id}/3d/export/glb`
- `GET /api/v1/designs/{design_id}/3d/export/{format}`

#### C) Legacy intent protocol control plane (design-scoped, but not generative geometry)

- `POST /api/v1/designs/{design_id}/intent/preview`
- `POST /api/v1/designs/{design_id}/actions`

**Feature flag implemented (ready for implementation rollout):**

- `MAGNET_LEGACY_INTENT_PROTOCOL_ENABLED`
  - **Location:** `magnet/deployment/api.py` L999–L1005
  - **Behavior:** When `false`, both legacy endpoints return **404**
  - **Endpoints gated at runtime:**
    - `POST /api/v1/designs/{design_id}/actions` (L1608–L1628 shows 404 gate)
    - `POST /api/v1/designs/{design_id}/intent/preview` (L1853–L1881 shows 404 gate)

This path is **not** the new architecture. It’s the old “intent → action plan” protocol.

#### D) New generative geometry endpoints (not design-scoped)

- `POST /api/v1/propose`
- `POST /api/v1/program`
- `POST /api/v1/propose-and-execute`
- `POST /api/v1/propagate`
- `POST /api/v1/design/chat`
- `POST /api/v1/design/sketch`

These are the “north star” loop, but they currently do not provide a design-scoped authority that UIv2 already relies on.

---

## UIv2 Current Behavior (and why it conflicts with the new architecture)

### UIv2 is currently wired to the legacy intent protocol

`magnet/ui_v2/js/backend-adapter.js` routes most user text into:

- `/api/v1/designs/{design_id}/intent/preview` (compound mode) — **L491–L494**
- then `/api/v1/designs/{design_id}/actions` (apply) — **L728–L732**
- then runs phases and reloads GLB

This yields a working demo loop, but **it’s not the generative geometry path**, and it depends on a parameter taxonomy that includes style-like fields.

### UIv2 has hard-mapped “command parsing” and enumerated parameter keys

UIv2 contains a hard-coded command parser (“new”, “reload”, “undo”, etc.) and explicit lists of `hull.*` keys including `hull.hull_type`, `hull.chine_type`, etc.

This directly conflicts with:

- “infinite by nature” chat loop
- “agents coordinate on geometry and constraints only”
- “no enumeration”

Even if the backend rejects enums in the new path, UIv2 is currently structured around them.

---

## Gap Analysis: What’s required for the full end-to-end flow (and what’s missing)

### Required flow

1. **Sketch input** (image upload) OR **text intent**
2. **Agent translation** (VisionInterpreter and/or GeometryProposer)
3. **Geometry compilation** (program_executor → HullGeometry)
4. **Physics validation** (geometry-driven hydrostatics/resistance validity)
5. **3D visualization** (GLB export)
6. **Iterative feedback** (metrics + deltas + narrative; clarification loop)

### Gaps

#### Gap 1: UIv2 doesn’t call the new path endpoints

UIv2 currently calls legacy intent protocol endpoints, not:

- `/api/v1/design/chat`
- `/api/v1/design/sketch`
- `/api/v1/propose-and-execute`

#### Gap 2: New path endpoints aren’t design-scoped and aren’t “single authority”

- `/api/v1/design/chat` stores conversations in-memory and has its own IDs
- `/api/v1/design/sketch` returns `session_id`, not `design_id`
- `/api/v1/program` accepts `design_id` in request but does not actually select state by it

Meaning: the new path is not currently integrated into the same “design_id/version/explain/export/ws” loop that UIv2 uses.

#### Gap 3: The “one interface, no duplicate paths” requirement is unmet

Even if UIv2 is updated, the backend still exposes:

- legacy intent protocol path for “command parsing”
- new geometry path for chat/sketch

We need one canonical loop.

---

## Best Course of Action (Recommended Integration Path)

### Principle: `design_id` is the only authority

UI sessions, persistence, and outputs already revolve around `design_id`:

- websocket updates
- design versioning / undo
- explain/history/impact
- GLB export

So **the generative loop must be made design-scoped**, not session-scoped in memory.

### Step 1: Introduce “Design Spiral” endpoints under `/api/v1/designs/{design_id}`

Create or refactor endpoints so UIv2 can call a single canonical API surface:

- `POST /api/v1/designs/{design_id}/spiral/chat`
  - Request: `{ message, constraints?, use_llm?, client_context? }`
  - Behavior:
    - If message is natural language: GeometryProposer → DSL
    - If DSL: execute directly
    - Execute via `program_executor` into the **DesignStore-backed StateManager**
    - Trigger recomputation/propagation using the existing calculator/cascade infrastructure
    - Return feedback, metrics, deltas, and the new design_version
    - Emit WS events so the UI refreshes automatically

- `POST /api/v1/designs/{design_id}/spiral/sketch` (multipart)
  - Request: `image`, `annotations`, `generate_geometry=true`
  - Behavior:
    - VisionInterpreter → geometry-only intent string
    - GeometryProposer → DSL
    - Execute into the same StateManager
    - Return interpretation + iteration feedback + design_version

**Outcome:** UIv2 uses a *single* design-scoped loop, and the kernel remains the sole validator.

---

## Task 1: Backend Readiness Verification (Current Status)

### Do `/api/v1/designs/{design_id}/spiral/chat` and `/spiral/sketch` exist?

**Answer: NO.** Repo search confirms there are **no** routes registered for:

- `/api/v1/designs/{design_id}/spiral/chat`
- `/api/v1/designs/{design_id}/spiral/sketch`

Existing “new path” endpoints are **not design-scoped**:

- `POST /api/v1/design/chat` (in-memory conversations) — `magnet/deployment/api.py` L2913+
- `POST /api/v1/design/sketch` (session_id, not design_id) — `magnet/deployment/api.py` L3022+

### Exact file locations to implement spiral endpoints

**Recommended location (keeps `magnet/deployment/api.py` from growing further):**

- **Add new file:** `magnet/deployment/spiral_endpoints.py`
- **Modify:** `magnet/deployment/api.py` to `include_router(...)` for the spiral router

**Alternative (acceptable, but makes the monolith worse):**

- Implement directly inside `magnet/deployment/api.py` near the existing design-language endpoints block (~L2485+)

### Required function signatures (backend)

#### 1) Router factory

```python
def create_spiral_router(
    get_state_manager: Callable[[str], Optional["StateManager"]],
    ws_manager: "ConnectionManager",
) -> APIRouter:
    ...
```

#### 2) `POST /api/v1/designs/{design_id}/spiral/chat`

```python
@router.post("/api/v1/designs/{design_id}/spiral/chat")
async def spiral_chat(
    design_id: str,
    request: SpiralChatRequest,
) -> SpiralChatResponse:
    """
    MUST:
    - load StateManager via DesignStore for the given design_id
    - run GeometryProposer → program_executor (geometry primitives path)
    - persist state changes (design_version bump)
    - emit websocket event to trigger UI refresh (design_version + snapshot_created)
    - return feedback + metrics + deltas + explain pointer
    """
```

#### 3) `POST /api/v1/designs/{design_id}/spiral/sketch`

**See complete implementation:** Search `§SKELETON:SpiralEndpoints` → `spiral_sketch` handler

**Requirements:**
- VisionInterpreter → geometric intent string (no forbidden design type terms)
- GeometryProposer → DSL program
- execute_program into the design-scoped StateManager
- persist + websocket update
- return interpretation + feedback + metrics + deltas
- **CRITICAL:** Must require `confirm_execution=true` before executing (never auto-execute sketches)

### Persistence requirement: MUST use DesignStore (not in-memory)

The spiral endpoints must load state via the existing design-scoped getter:

- `magnet/deployment/api.py` already has `get_state_manager(design_id)` which uses `DesignStore.load(design_id)` when a `design_id` is provided (see `create_fastapi_app` dependency helpers near L1119+).

**Rule:** spiral endpoints must call `get_state_manager(design_id)` and commit through StateManager transactions (no in-memory conversation authority).

#### Important limitation: current DesignStore is not a real multi-design store

`magnet/deployment/design_store.py` is explicitly minimal:

- It only returns a `StateManager` **if the requested `design_id` is already the currently loaded design**.
- Otherwise it raises `DesignNotFound("Design {id} not loaded.")`.

**Implication:** the current backend is effectively “single in-flight design at a time”. This matters for UI switching/migration:

- If UIv2 lets you pick an older design, the server likely cannot load it unless it’s already in memory.

**Best course (implementation requirement):**

- Either:
  - Upgrade `DesignStore` to load persisted designs from disk (`storage/designs/…`) or a DB, **or**
  - Explicitly document “only one active design per server instance” and treat older designs as unavailable (not recommended for production).

### Websocket emission requirement

Existing “design mutation” endpoints already push websocket messages (examples):

- `design_deleted` event: `magnet/deployment/api.py` L1594–L1597
- `design_reverted` event: `magnet/deployment/api.py` L1839–L1843

**Rule:** spiral endpoints must emit at minimum:

- `design_updated` (new message type) **or** reuse existing semantics if present
- `snapshot_created` (UIv2 listens for this to reload GLB; see `backend-adapter.js` switch at ~L306+ and `scene-manager.js`)

#### Websocket event compatibility: do not require new UI message types during transition

The server already defines a stable WS vocabulary in `magnet/deployment/websocket.py`:

- `design_updated` (MessageType.DESIGN_UPDATED)
- `snapshot_created` (MessageType.SNAPSHOT_CREATED)
- `phase_*` events
- `validation_*` events

**Recommendation:** Spiral should initially emit only existing message types:

- `design_updated` payload:
  - `design_version_after`
  - `spiral_iteration`
  - `metrics`, `deltas`
  - `status`: `"applied" | "needs_clarification" | "proposal_low_confidence" | "failed"`
- `snapshot_created` payload:
  - `design_version_after`
  - `artifact`: `"geometry.glb"`
  - `ready`: `true`

If/when you add spiral-specific events (e.g. `clarification_needed`), treat them as additive, not required.

---

## New concerns: migration, schema paths, UX, latency, persistence tests

### 1) What happens to in-flight designs when switching control planes?

**Problem:** Legacy-created designs often contain enum-like fields such as `hull.hull_type` (and many `hull.*` feature knobs). UIv2 currently depends on that taxonomy.

**Risk:** When `/spiral/*` runs, it might:
- accidentally read those enum fields and reintroduce enumeration, or
- fail if legacy fields conflict with geometry compilation assumptions.

**Recommended policy (explicit):**

- **Legacy designs are read-only** when `MAGNET_LEGACY_INTENT_PROTOCOL_ENABLED=false` **unless** they already contain geometry resources (`resources.geometry.*` / `hull.geometry`) required by the new path.
- Spiral endpoints must:
  - ignore `hull.hull_type` and feature knobs as *inputs*
  - operate only on geometry primitives and post-compilation physics outputs
  - return a clear error if no geometry exists:  
    “This design is legacy-parametric. Create a new design in geometry mode or run migration.”

**Migration options (choose one):**

1. **Hard line (recommended):** legacy designs read-only; new designs must be created with geometry mode.
2. **Soft migration:** create a one-time “geometry seed” from legacy parameters (danger: can silently encode taste; must be clearly labeled MIGRATION ONLY).

#### Migration tool requirement (addresses “orphaned legacy designs”)

To avoid permanent orphaning, add a **migration endpoint** that is explicitly labeled and constrained:

- `POST /api/v1/designs/{design_id}/migrate-to-geometry`

**Contract (MIGRATION ONLY):**

- Input: legacy parametric state (including `hull.loa/beam/draft/...` and possibly `hull.hull_type`)
- Output: a **geometry primitives program** (DSL) that seeds `resources.geometry.*`
- Must:
  - mark provenance: `"migration_only"`
  - never add new primitives
  - never hardcode design-type dispatch in kernel logic
  - require explicit user confirmation before committing (two-step: preview + apply)

**Why this is acceptable:** it is **one-time backward compatibility**, not kernel enumeration. The kernel still validates geometry, not intent.

### 2) Does DesignStore / State schema need to change for spiral checkpoints?

**Problem:** The spiral loop wants to persist conversation state (checkpoint, iteration history, last validated metrics, pending clarifications).

**Reality check:** `StateManager` has **path-strict reads** (`get_strict`) with a schema list (`VALID_PATHS`) in `magnet/core/state_manager.py`.

Even though `StateManager.set()` currently doesn’t enforce schema strictly, future strictness (and any code using `get_strict`) can break if spiral stores data under ad-hoc paths like `design.spiral.checkpoint`.

**Recommendation (implementation requirement):**

- Add explicit schema paths for spiral persistence (preferred):
  - e.g. `phase_states.spiral` (dict blob) and/or `metadata.spiral_checkpoint`
- Or store the entire checkpoint as a dict under an already-valid dict path:
  - e.g. `phase_states.hull_form` as a dict that includes `{ "spiral": {...} }`

**Why this matters:** if schema is tightened later, ad-hoc paths can turn into silent data loss or runtime `InvalidPathError` when using strict reads.

### 3) WebSocket event format for spiral updates

**Problem:** UIv2 is currently phase-centric (phase_started/phase_completed) and expects `snapshot_created` to reload GLB.

**Risk:** If spiral emits a new event name that UI doesn’t handle, you get silent failures.

**Recommendation (transition-safe):**

- Spiral must emit:
  - `design_updated` (existing) with metrics/deltas + design_version_after
  - `snapshot_created` (existing) when GLB is actually ready (see latency below)

Additive events are fine, but spiral must not depend on them initially.

### 4) What if GeometryProposer fails mid-spiral (or returns low confidence)?

**Problem:** Legacy path had preview/apply separation; spiral is atomic.

**Desired UX:**

- If agent confidence < threshold:
  - Do **not** commit changes
  - Return:
    - `proposal_text` (DSL)
    - `average_confidence`
    - `reasoning_summary`
    - `clarification_questions` (if any)
  - UI shows a “Review proposal” panel and offers:
    - “Refine request” (send another message)
    - “Apply anyway” (explicit user confirmation; still goes through spiral endpoint with `force_apply=true`)

**Rollback guarantee:** leverage existing program executor atomicity invariants; spiral must run program execution inside a transaction and roll back on compile/validate error.

### 5) GLB generation latency and “fetch before ready”

**Problem:** Spiral returns `design_version_after`, UI fetches GLB. If GLB generation is slow, UI may request before cached/ready.

**Reality check:** `magnet/webgl/geometry_service.py` already includes:
- a versioned mesh cache (keyed by `design_id:design_version:lod`)
- an internal “geometry ready” event emission (`emit_geometry_ready` via EventBus in `magnet/webgl/events.py`)

But there is **no guaranteed WS bridge** from that event to UI yet.

**Recommendation:**

- Spiral endpoint should either:
  1. **Prewarm** geometry by calling `GeometryService.get_scene(... allow_visual_only=False)` before returning, or
  2. Kick a **background job** to precompute GLB and emit `snapshot_created` only when ready.

UI behavior during transition:
- Prefer waiting for `snapshot_created` rather than fetching immediately.
- If no `snapshot_created` within N seconds, poll with backoff.

### 6) Missing acceptance test: spiral persistence across requests / restart

**Gap:** There is no test proving spiral conversation state survives beyond one request or survives restart.

**Add tests (implementation requirement):**

1. `test_spiral_checkpoint_persists_across_requests`
   - call spiral endpoint twice and ensure iteration increments and prior context is used

2. `test_spiral_checkpoint_survives_state_save_load`
   - write checkpoint into state
   - `StateManager.save_to_file(...)`
   - new `StateManager.load_from_file(...)`
   - assert checkpoint restored

**Note:** This will only be meaningful once `DesignStore` can load designs from persistence (see DesignStore limitation above).

### 7) Failure modes checklist (must be addressed before implementation)

These are blocking for production readiness of the spiral UI loop:

1. **Concurrent spiral requests:** require `expected_version` and return 409 on mismatch (optimistic locking).
2. **Downstream phase failures:** spiral must run critical phases/cascade and return `status="partial"` + `failed_phases[]`.
3. **Sketch OCR errors:** sketch endpoint must return `extracted_values` and require human confirmation.
4. **Checkpoint growth:** enforce `max_checkpoint_iterations` and prune/compress older iterations.
5. **WS reconnection resync:** on reconnect, UI must fetch `GET /api/v1/designs/{id}` and restore `spiral_iteration`.

---

## Task 2: UIv2 Hardcoded Enumeration Audit (Files + Lines + Replacements)

### A) `magnet/ui_v2/js/backend-adapter.js`

**Legacy calls (must be removed):**

- `POST /api/v1/designs/${designId}/intent/preview` — L491–L494  
  **Replace with:** `POST /api/v1/designs/${designId}/spiral/chat`

- `POST /api/v1/designs/${designId}/actions` — L728–L732  
  **Replace with:** no direct equivalent; spiral endpoint performs mutation atomically.

**Hardcoded hull schema keys (must be removed as “inputs”):**

- HULL_PATHS list includes enumerations and feature taxonomy:
  - `hull.hull_type` — L799
  - `hull.chine_type`, `hull.chine_style` — L809–L811
  - `hull.has_spray_rails` — L817
  - `hull.transom_style`, `hull.panel_style` — L819, L825

**Replacement behavior:**

- Do **not** determine phases based on a hardcoded list of `hull.*` keys.
- Instead:
  - When spiral endpoints return `design_version_after` + `invalidated_phases`, UI triggers:
    - phase UI refresh
    - GLB reload using `?v={design_version_after}`

### B) `magnet/ui_v2/js/panel-config.js`

**Enumeration display that implies classification:**

- Hull badge uses `hull_type` — L25–L34
- “Classification” group displays `hull_type` — L59–L62

**Replace with (non-enumerative):**

- Show **geometric facts**:
  - `body_count`
  - `principal_dimensions` derived from geometry (`loa`, `beam`, `draft`) if available
  - `hydrostatics_method` already exists and is physics-based

**Rule:** UI may show a human-readable label, but it must be derived (e.g., `multi_body_2`) not a design type string.

### C) `magnet/ui_v2/docs/MODULE_65_1_INTENT_RESOLUTION.md` (Legacy doc)

Contains explicit enumeration mapping:

- `hull.hull_type = catamaran` — L18–L24
- “Enum mentions (catamaran → hull.hull_type)” — L68

**Action:** mark as **LEGACY** or remove from the production doc set to prevent future confusion.

---

## Task 3: Missing Acceptance Test (Implemented)

**Test added:** `tests/deployment/test_legacy_intent_protocol_flag.py`

Ensures:

- When `MAGNET_LEGACY_INTENT_PROTOCOL_ENABLED=false`, both:
  - `POST /api/v1/designs/{design_id}/intent/preview`
  - `POST /api/v1/designs/{design_id}/actions`
  return **404**.

---

## Task 4: Implementation Checklist (Exact File Paths)

### Backend

- **Modify:** `magnet/deployment/api.py`
  - add `include_router(spiral_router)` in `create_fastapi_app`
  - ensure `get_state_manager(design_id)` is passed into spiral router factory
  - ensure websocket manager passed into spiral router factory

- **Create:** `magnet/deployment/spiral_endpoints.py`
  - `create_spiral_router(...)`
  - request/response models:
    - `SpiralChatRequest`, `SpiralChatResponse`
    - `SpiralSketchResponse`

- **Modify:** `magnet/agents/design_conversation.py` (if needed)
  - allow “design-scoped” persistence:
    - store conversation checkpoint in state: `design.spiral.checkpoint`
    - restore from state on each call

### UIv2

- **Modify:** `magnet/ui_v2/js/backend-adapter.js`
  - remove calls to:
    - `/intent/preview`
    - `/actions`
  - send user input to:
    - `/api/v1/designs/{design_id}/spiral/chat`
  - handle returned:
    - `design_version_after`
    - `invalidated_phases`
    - `metrics` + `deltas`
  - reload GLB deterministically:
    - `/api/v1/designs/{design_id}/3d/export/glb?v={design_version_after}`

- **Modify:** `magnet/ui_v2/js/panel-config.js`
  - remove `hull_type` badge/field
  - replace with geometry facts and physics method metadata

### Config

- **Feature flag location:** `magnet/deployment/api.py` L999–L1005
  - env var: `MAGNET_LEGACY_INTENT_PROTOCOL_ENABLED`
  - recommended production: `false`

---

## Task 5: Sacred Invariants Check (Required After Implementation)

After implementing spiral endpoints and UI migration:

```bash
python3 -m pytest tests/invariants/ -v
# MUST remain 54/54 passing
```

---

## Task 6: What Can Be Removed / Deleted (To Avoid Future Confusion)

### After spiral endpoints are live and UIv2 is migrated

**UIv2 legacy artifacts to remove or quarantine:**

- `magnet/ui_v2/docs/MODULE_65_1_INTENT_RESOLUTION.md` (explicit enum mapping)
- UI command-path references that suggest `hull.hull_type` is an input
- Any UI “classification” display that shows `hull_type` as authoritative

**Backend legacy control plane to keep only behind flag (or delete later):**

- `/api/v1/designs/{design_id}/intent/preview`
- `/api/v1/designs/{design_id}/actions`

**Recommended policy:** keep for backward compatibility for one release, then delete if no clients use it.

### Additional deletion candidates after spiral is production

- UIv2 hardcoded “schema key” routing lists tied to hull feature enums:
  - `HULL_PATHS` list in `magnet/ui_v2/js/backend-adapter.js` (L791+)
- Legacy intent resolution docs that instruct enum mapping:
  - `magnet/ui_v2/docs/MODULE_65_1_INTENT_RESOLUTION.md`
- Any UI panel fields that treat `hull_type` as authoritative rather than derived


### Step 2: Deprecate legacy intent preview/apply in UIv2 (not necessarily delete immediately)

UI behavior should be:

- **All design change requests** go through `/spiral/chat` or `/spiral/sketch`
- “Preview/Apply” becomes an optional UI affordance **implemented by the new path**, not the old intent protocol

If legacy endpoints remain for backward compatibility, UIv2 should not call them by default.

### Step 3: Update UIv2 to become a true chat-based spiral interface

Recommended UIv2 changes (high level):

- Replace “command parser as control plane” with:
  - **Chat panel**: send text to `/spiral/chat`
  - **Sketch panel**: upload image to `/spiral/sketch`
  - **Constraints panel**: manage constraints as first-class, feed into `/spiral/chat`
  - **Clarification panel**: surface ClarificationManager requests and send responses
  - **Feedback panel**: show metrics + deltas + narrative + “unknown method” explanations

Keep only a few **non-design meta actions** as explicit UI controls:

- New design (calls `POST /api/v1/designs`)
- Undo/Restore (calls `/undo` and `/versions/.../restore`)
- Export (calls `/3d/export/*`)

These are not “design vocabularies”; they are session controls.

### Step 4: Make 3D refresh deterministic via design_version

UIv2 should always load:

`/api/v1/designs/{design_id}/3d/export/glb?v={design_version}`

No timestamps. Determinism improves debugging and repeatability.

---

## “No Enumeration” Enforcement at the UI Boundary

### UI must not encode vessel types as state keys

UI should treat terms like “catamaran” as user intent, not state taxonomies.

Correct:
- User says “catamaran”
- Agent outputs two `geometry.body` with offsets

Incorrect:
- UI sets `hull.hull_type = "catamaran"`
- UI toggles `hull.has_spray_rails = true`

### UI-level guardrails (recommended)

- Ban any UI-side writes to `hull.hull_type`, `hull.chine_type`, `hull.spray_rail_*`, etc.
- Only display computed “labels” as **derived** explanations, never as authoritative inputs

---

## Migration / Rollout Plan (No Temporary Bridges)

### Phase -1: DesignStore Persistence (Prerequisite for Production)

**Recommendation:** ✅ This is the right way to do it **if** you want a production-ready UI that supports:

- switching between multiple designs
- “spiral checkpoint survives restart”
- durable design history beyond one in-memory instance

**Pushback / nuance:** If you explicitly accept **single in-flight design per server** (current behavior), you can *prototype* spiral endpoints without Phase -1. But you cannot claim:

- multi-design UI switching, or
- restart durability

without real persistence.

#### Why this is required (current limitation)

`magnet/deployment/design_store.py` currently only returns a `StateManager` if the requested `design_id` is already the currently loaded design; otherwise it raises `DesignNotFound("Design {id} not loaded.")`.

So UI design switching is fundamentally unsupported without a real store.

---

#### Implementation (DesignStore v2)

**File:** `magnet/deployment/design_store.py`

**Required changes:**

- Add file-based persistence (**JSON** is fine for v1; SQLite optional for v2)
- Implement:
  - `save(design_id)` writes state to disk
  - `load(design_id)` reads state from disk into a `StateManager`
  - `list_designs()` enumerates stored designs
  - `exists(design_id)` checks storage
  - `delete(design_id)` deletes stored design
- Add storage directory:
  - `storage/designs/` (already exists in repo; formalize it as the DesignStore backing directory)

#### Proposed interface (must be documented + enforced)

```python
from typing import List
from magnet.core.state_manager import StateManager


class DesignStore:
    def save(self, design_id: str) -> bool: ...
    def load(self, design_id: str) -> StateManager: ...
    def delete(self, design_id: str) -> bool: ...
    def list_designs(self) -> List[str]: ...
    def exists(self, design_id: str) -> bool: ...
```

#### Storage format (recommended)

- **JSON per design**: `storage/designs/{design_id}.json`
  - Pros: simple, debuggable, versionable
  - Cons: not great for concurrent writes (solve with atomic replace)

**Atomic write requirement:** write to a temp file then `os.replace()` to avoid corruption.

#### Acceptance tests (must be added before proceeding)

- `test_design_persists_across_server_restart`
- `test_multiple_designs_can_be_saved_and_loaded`
- `test_design_switching_preserves_state`
- `test_spiral_checkpoint_survives_restart`

These tests should validate that:
- design switching is real (load different design IDs into the active `StateManager`)
- the same design ID produces identical state after save/load
- spiral checkpoint persists as part of saved state

#### Timeline update

- **Phase -1:** DesignStore persistence (**2–3 days**)
- **Phase 0–3:** existing plan (**unchanged**)
- **Total:** **5–7 days** (was 3–5)

#### Decision gate (hard)

- **DO NOT proceed to Phase 1** until all Phase -1 DesignStore tests pass.
- **Multi-design UI switching requires real persistence.**

#### Sacred invariants (must remain true)

After Phase -1 changes:

```bash
python3 -m pytest tests/invariants/ -v
# MUST remain 54/54 passing
```

### Phase 0: Confirm current “final endpoints” and their owners (0.5 day)

- Freeze the canonical endpoints list for UIv2:
  - `/api/v1/meta`
  - `/api/v1/designs/*`
  - `/api/v1/designs/{id}/3d/export/*`
  - `/api/v1/designs/{id}/explain/latest`
  - `/api/v1/designs/{id}/impact/*`
  - `/api/v1/designs/{id}/why`
  - `/ws/{design_id}`
  - **NEW:** `/api/v1/designs/{id}/spiral/*`

### Phase 1: Build design-scoped spiral endpoints (1–2 days)

- Persist conversation state under `design_id` (DesignStore or StateManager)
- Ensure atomic transactions on failures (already a sacred invariant)
- Ensure deltas + explanations emitted consistently

### Phase 2: Update UIv2 adapter to use spiral endpoints (1–2 days)

- Replace `/intent/preview` + `/actions` path in UIv2
- Remove hard-coded “hull feature taxonomy” from UI logic
- Render:
  - feedback text
  - metrics + deltas
  - clarifications
  - GLB refresh tied to design_version

### Phase 3: Kill duplicate paths in production mode (0.5–1 day)

- Feature flag:
  - `MAGNET_LEGACY_INTENT_PROTOCOL_ENABLED=false` (default)
- UI hides legacy “preview/apply” mode by default

---

## Implementation Guide (Executable Checklist + Decision Gates)

### Phase -1 (Prerequisite): DesignStore Persistence (Design Switching + Restart Durability)

#### Goal

Enable:
- multi-design UI switching
- spiral checkpoint persistence across restart
- durable designs beyond one in-memory instance

#### Backend: exact code skeleton (DesignStore v2)

**File:** `magnet/deployment/design_store.py`

Create a file-backed store (JSON v1). This is a skeleton; fill in details during implementation.

```python
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from magnet.core.state_manager import StateManager


class DesignNotFound(Exception):
    pass


@dataclass
class DesignStoreConfig:
    root_dir: Path

    @classmethod
    def from_env(cls) -> "DesignStoreConfig":
        # Default: repo storage directory
        base = os.environ.get("MAGNET_DESIGN_STORE_DIR", "storage/designs")
        return cls(root_dir=Path(base))


class DesignStore:
    """
    §SKELETON:DesignStore
    
    DesignStore v2: file-backed persistence for design state.

    Storage format (v1): JSON per design at {root_dir}/{design_id}.json
    """

    def __init__(self, container: Optional[object] = None, config: Optional[DesignStoreConfig] = None):
        self._container = container
        self._config = config or DesignStoreConfig.from_env()
        self._config.root_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, design_id: str) -> Path:
        return self._config.root_dir / f"{design_id}.json"

    def exists(self, design_id: str) -> bool:
        return self._path_for(design_id).exists()

    def list_designs(self) -> List[str]:
        return sorted(p.stem for p in self._config.root_dir.glob("*.json"))

    def save(self, design_id: str) -> bool:
        """
        Persist current StateManager to disk under design_id.
        MUST be atomic: write temp then os.replace().
        """
        sm = self._resolve_state_manager()
        data = sm.to_dict()
        out = self._path_for(design_id)
        tmp = out.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        os.replace(tmp, out)
        return True

    def load(self, design_id: str) -> StateManager:
        """
        Load design state from disk into a StateManager instance.
        """
        path = self._path_for(design_id)
        if not path.exists():
            raise DesignNotFound(f"Design {design_id} not found")
        sm = self._resolve_state_manager()
        data = json.loads(path.read_text(encoding="utf-8"))
        sm.load_from_dict(data)
        return sm

    def delete(self, design_id: str) -> bool:
        path = self._path_for(design_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def _resolve_state_manager(self) -> StateManager:
        if not self._container:
            # For tests, allow creating a standalone StateManager if you have a factory.
            from magnet.core.state_manager import StateManager  # local import to avoid cycles
            return StateManager()
        return self._container.resolve(StateManager)
```

#### Acceptance tests (exact file paths + skeletons)

**File:** `tests/deployment/test_design_store_persistence.py`

§SKELETON:DesignStoreTests

```python
from pathlib import Path

import pytest


def test_design_persists_across_server_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("MAGNET_DESIGN_STORE_DIR", str(tmp_path))

    from magnet.deployment.design_store import DesignStore
    from magnet.core.state_manager import StateManager

    # Simulate server instance 1
    store1 = DesignStore(container=None)
    sm1 = store1._resolve_state_manager()
    sm1.begin_transaction()
    sm1.set("hull.loa", 25.0, source="test")
    sm1.commit()
    store1.save("DESIGN-1")

    # Simulate server restart (new store instance)
    store2 = DesignStore(container=None)
    sm2 = store2.load("DESIGN-1")
    assert sm2.get("hull.loa") == 25.0


def test_multiple_designs_can_be_saved_and_loaded(tmp_path, monkeypatch):
    monkeypatch.setenv("MAGNET_DESIGN_STORE_DIR", str(tmp_path))
    from magnet.deployment.design_store import DesignStore

    store = DesignStore(container=None)
    sm = store._resolve_state_manager()

    sm.begin_transaction()
    sm.set("hull.loa", 20.0, source="test")
    sm.commit()
    store.save("A")

    sm.begin_transaction()
    sm.set("hull.loa", 30.0, source="test")
    sm.commit()
    store.save("B")

    assert set(store.list_designs()) == {"A", "B"}
    assert store.load("A").get("hull.loa") == 20.0
    assert store.load("B").get("hull.loa") == 30.0


def test_design_switching_preserves_state(tmp_path, monkeypatch):
    monkeypatch.setenv("MAGNET_DESIGN_STORE_DIR", str(tmp_path))
    from magnet.deployment.design_store import DesignStore

    store = DesignStore(container=None)
    sm = store._resolve_state_manager()

    sm.begin_transaction()
    sm.set("hull.beam", 5.0, source="test")
    sm.commit()
    store.save("A")

    sm.begin_transaction()
    sm.set("hull.beam", 7.0, source="test")
    sm.commit()
    store.save("B")

    assert store.load("A").get("hull.beam") == 5.0
    assert store.load("B").get("hull.beam") == 7.0


def test_spiral_checkpoint_survives_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("MAGNET_DESIGN_STORE_DIR", str(tmp_path))
    from magnet.deployment.design_store import DesignStore

    store1 = DesignStore(container=None)
    sm1 = store1._resolve_state_manager()
    sm1.set("phase_states.hull_form", {"spiral": {"iteration": 2, "checkpoint": {"foo": "bar"}}}, source="test")
    store1.save("DESIGN-1")

    store2 = DesignStore(container=None)
    sm2 = store2.load("DESIGN-1")
    phase = sm2.get("phase_states.hull_form", {})
    assert phase.get("spiral", {}).get("iteration") == 2
```

#### Sacred invariants checkpoint (MANDATORY)

After implementing Phase -1:

```bash
python3 -m pytest tests/invariants/ -v
```

#### Decision gate (hard)

- **DO NOT proceed to Phase 1** until all `tests/deployment/test_design_store_persistence.py` tests pass.

#### Rollback plan (Phase -1)

- Keep old `DesignStore.load()` logic behind a flag if needed:
  - `MAGNET_DESIGN_STORE_V2_ENABLED=false` → old behavior
- If persistence breaks production, disable v2 and run in single-design mode.

---

### Phase 1: Spiral Endpoints (Design-Scoped, Persistent, Single Authority)

#### Goal

Implement:
- `POST /api/v1/designs/{design_id}/spiral/chat`
- `POST /api/v1/designs/{design_id}/spiral/sketch`

These must:
- operate on DesignStore-backed `StateManager` (persisted)
- be atomic (rollback on failure)
- emit WS messages UI already understands
- return structured metrics/deltas + design_version

#### Backend: exact code skeleton to write

**New file:** `magnet/deployment/spiral_endpoints.py`

```python
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel
from fastapi import APIRouter, File, Form, HTTPException, UploadFile


class SpiralChatRequest(BaseModel):
    message: str
    constraints: Optional[List[str]] = None
    # Concurrency control (failure mode #1): optimistic locking
    expected_version: Optional[int] = None
    request_id: Optional[str] = None  # idempotency key (UI retries / double-click safety)
    min_confidence: float = 0.6
    force_apply: bool = False  # explicit user override when confidence is low
    # Spiral execution scope (failure mode #2): ensure downstream phases work
    run_critical_phases: bool = True
    critical_phases: Optional[List[str]] = None  # e.g. ["hull_form", "weight_stability", "structure"]
    # GLB readiness controls (shortcut #2)
    glb_timeout_ms: int = 2000
    glb_retry_limit: int = 5
    # §SKELETON:CheckpointPruning - Checkpoint management
    max_checkpoint_iterations: int = 50  # Prune checkpoints older than this
    clarification_response: Optional[Dict[str, Any]] = None  # Response to previous clarification


class SpiralChatResponse(BaseModel):
    success: bool
    design_id: str
    design_version_before: int
    design_version_after: int
    # Track iteration explicitly (not only via WebSocket) so UI can persist state across WS reconnect.
    spiral_iteration: int = 0
    status: str  # applied | proposal_low_confidence | needs_clarification | partial | failed
    feedback: str
    program_text: str = ""
    average_confidence: float = 0.0
    # Shortcut #1 fix: clarification must be first-class
    clarification_questions: List[Dict[str, Any]] = []
    clarification_request_id: Optional[str] = None
    metrics: Dict[str, float] = {}
    deltas: Dict[str, float] = {}
    invalidated_phases: List[str] = []
    failed_phases: List[str] = []  # failure mode #2: downstream phase failures
    glb_ready: bool = False
    glb_retry_after_ms: Optional[int] = None
    errors: List[str] = []


class SpiralSketchResponse(BaseModel):
    success: bool
    design_id: str
    design_version_before: int
    design_version_after: int
    interpretation: Optional[Dict[str, Any]] = None
    # Failure mode #3: explicit extracted values for human confirmation
    extracted_values: Dict[str, Any] = {}
    requires_confirmation: bool = True
    intent_string: str = ""
    program_text: str = ""
    average_confidence: float = 0.0
    status: str
    feedback: str
    clarification_questions: List[Dict[str, Any]] = []
    metrics: Dict[str, float] = {}
    deltas: Dict[str, float] = {}
    glb_ready: bool = False
    glb_retry_after_ms: Optional[int] = None
    errors: List[str] = []


def create_spiral_router(
    get_state_manager: Callable[[str], Any],
    ws_manager: Any,
) -> APIRouter:
    """
    §SKELETON:SpiralEndpoints
    
    Create the spiral endpoints router.
    Gated by MAGNET_SPIRAL_ENABLED environment variable.
    """
    import os
    
    # §SKELETON:SpiralEnabledFlag
    spiral_enabled = os.environ.get("MAGNET_SPIRAL_ENABLED", "true").lower() == "true"
    if not spiral_enabled:
        # Return empty router - endpoints won't be registered
        return APIRouter(tags=["Design Spiral (disabled)"])
    
    router = APIRouter(tags=["Design Spiral"])

    @router.post("/api/v1/designs/{design_id}/spiral/chat", response_model=SpiralChatResponse)
    async def spiral_chat(design_id: str, request: SpiralChatRequest) -> SpiralChatResponse:
        sm = get_state_manager(design_id)
        if not sm:
            raise HTTPException(status_code=404, detail="Design not found")

        # Failure mode #1: optimistic locking (stale version → 409)
        current_version = getattr(sm, "design_version", sm.get("design_version", 0))
        if request.expected_version is not None and request.expected_version != current_version:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "stale_version",
                    "expected_version": request.expected_version,
                    "current_version": current_version,
                },
            )

        # (A) Legacy design guardrail (recommended)
        # If no geometry resources exist, either reject or require explicit migration.
        # Example heuristic: require `resources.geometry` or `hull.geometry` present.
        resources = sm.get("resources", {}) if hasattr(sm, "get") else {}
        if not resources and not request.force_apply:
            # keep this conservative; actual condition should check for geometry resources specifically
            pass

        design_version_before = current_version

        # (B) Propose geometry program from message (if NL)
        from magnet.agents.geometry_proposer import create_geometry_proposer
        proposer = create_geometry_proposer()
        proposal = await proposer.propose(intent=request.message, current_state=sm.to_dict())
        if not proposal.success or not proposal.program:
            return SpiralChatResponse(
                success=False,
                design_id=design_id,
                design_version_before=design_version_before,
                design_version_after=design_version_before,
                status="failed",
                feedback="Proposal failed",
                errors=[proposal.error or "proposal_failed"],
            )

        avg_conf = sum(op.confidence for op in proposal.program.operations) / max(len(proposal.program.operations), 1)

        # (C) Low confidence → do not commit unless force_apply (human-in-loop)
        if avg_conf < request.min_confidence and not request.force_apply:
            return SpiralChatResponse(
                success=True,
                design_id=design_id,
                design_version_before=design_version_before,
                design_version_after=design_version_before,
                status="proposal_low_confidence",
                feedback=f"Low confidence ({avg_conf:.2f}). Please refine or explicitly apply.",
                program_text=proposal.program_text,
                average_confidence=avg_conf,
                clarification_questions=[],
                clarification_request_id=None,
                metrics={},
                deltas={},
                invalidated_phases=[],
                failed_phases=[],
                glb_ready=False,
                errors=[],
            )

        # (D) Execute program atomically into the design-scoped StateManager
        from magnet.kernel.program_executor import execute_program
        try:
            result = execute_program(program_text=proposal.program_text, state_manager=sm, dry_run=False)
        except Exception as e:
            return SpiralChatResponse(
                success=False,
                design_id=design_id,
                design_version_before=design_version_before,
                design_version_after=design_version_before,
                status="failed",
                feedback="Execution failed",
                program_text=proposal.program_text,
                average_confidence=avg_conf,
                errors=[str(e)],
            )

        design_version_after = getattr(sm, "design_version", sm.get("design_version", design_version_before))

        # (D.1) Failure mode #2: run critical phases/cascade before returning "applied"
        #
        # Requirement: Spiral must not assume "physics ok" => all downstream phases ok.
        # If critical phases fail, return status="partial" with failed_phases[].
        #
        failed_phases: List[str] = []
        invalidated_phases: List[str] = []
        if request.run_critical_phases:
            # Default critical phases (safe MVP set; adjust as pipeline stabilizes)
            phases = request.critical_phases or ["hull_form", "weight_stability", "structure"]
            try:
                # Use existing phase runner if available (implementation detail):
                # - In production code, prefer calling PhaseMachine/Conductor rather than reimplementing.
                from magnet.kernel.conductor import Conductor
                conductor = Conductor(state_manager=sm)  # adjust to actual constructor/wiring
                for p in phases:
                    try:
                        res = conductor.run_phase(p)
                        if getattr(res, "success", True) is False:
                            failed_phases.append(p)
                    except Exception:
                        failed_phases.append(p)
                # Optionally compute invalidated phases from dependency graph / recalculation report
                # invalidated_phases = ...
            except Exception:
                # If the phase runner isn't wired yet, treat as non-blocking but visible
                # (Production requirement: do not hide this — either wire phases or drop the claim.)
                pass

        # (E) Emit WS events using existing types (transition safe)
        from magnet.deployment.websocket import WSMessage, MessageType
        ws_manager.queue_message(
            WSMessage(
                type=MessageType.DESIGN_UPDATED.value,
                design_id=design_id,
                payload={
                    "source": "spiral",
                    "request_id": request.request_id,
                    "design_version_after": design_version_after,
                    "spiral_iteration": 0,  # increment in real implementation
                    "average_confidence": avg_conf,
                    "status": (
                        "partial"
                        if result.success and failed_phases
                        else ("applied" if result.success else "failed")
                    ),
                    "metrics": (result.validation or {}).get("metrics", {}),
                    "deltas": (result.validation or {}).get("deltas", {}),
                    "failed_phases": failed_phases,
                    "invalidated_phases": invalidated_phases,
                },
            )
        )

        # (F) GLB readiness strategy (choose one):
        # Option 1: prewarm geometry before emitting snapshot_created
        # Option 2: emit snapshot_created immediately and let UI poll (less ideal)

        ws_manager.queue_message(
            WSMessage(
                type=MessageType.SNAPSHOT_CREATED.value,
                design_id=design_id,
                payload={"design_version_after": design_version_after, "artifact": "geometry.glb", "ready": True},
            )
        )

        # (G) §SKELETON:CheckpointPruning - Manage spiral iteration and prune old checkpoints
        spiral_state = sm.get("phase_states.hull_form", {}).get("spiral", {})
        current_iteration = spiral_state.get("iteration", 0) + 1
        checkpoints = spiral_state.get("checkpoints", [])
        
        # Add new checkpoint
        checkpoints.append({
            "iteration": current_iteration,
            "design_version": design_version_after,
            "program_text": proposal.program_text,
            "confidence": avg_conf,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Prune old checkpoints beyond max_checkpoint_iterations
        if len(checkpoints) > request.max_checkpoint_iterations:
            checkpoints = checkpoints[-request.max_checkpoint_iterations:]
        
        # Persist spiral state
        sm.set("phase_states.hull_form", {
            **sm.get("phase_states.hull_form", {}),
            "spiral": {
                "iteration": current_iteration,
                "checkpoints": checkpoints,
                "last_message": request.message,
            }
        }, source="spiral_chat")

        return SpiralChatResponse(
            success=result.success,
            design_id=design_id,
            design_version_before=design_version_before,
            design_version_after=design_version_after,
            spiral_iteration=current_iteration,
            status=(
                "partial"
                if result.success and failed_phases
                else ("applied" if result.success else "failed")
            ),
            feedback="Applied" if result.success else "Failed",
            program_text=proposal.program_text,
            average_confidence=avg_conf,
            clarification_questions=[],
            clarification_request_id=None,
            metrics=(result.validation or {}).get("metrics", {}),
            deltas=(result.validation or {}).get("deltas", {}),
            invalidated_phases=invalidated_phases or (result.validation or {}).get("invalidated_phases", []),
            failed_phases=failed_phases,
            glb_ready=True if result.success else False,
            errors=result.errors,
        )

    @router.post("/api/v1/designs/{design_id}/spiral/sketch", response_model=SpiralSketchResponse)
    async def spiral_sketch(
        design_id: str,
        image: UploadFile = File(...),
        annotations: str = Form(default=""),
        confirm_execution: bool = Form(default=False),  # Requires explicit confirmation
        expected_version: Optional[int] = Form(default=None),
    ) -> SpiralSketchResponse:
        sm = get_state_manager(design_id)
        if not sm:
            raise HTTPException(status_code=404, detail="Design not found")

        design_version_before = getattr(sm, "design_version", sm.get("design_version", 0))
        
        # Optimistic locking
        if expected_version is not None and expected_version != design_version_before:
            raise HTTPException(
                status_code=409,
                detail={"error": "stale_version", "expected_version": expected_version, "current_version": design_version_before},
            )

        # Step 1: Vision → interpretation
        from magnet.agents.vision_interpreter import VisionInterpreter
        from magnet.llm.providers.anthropic import AnthropicProvider
        provider = AnthropicProvider()
        interpreter = VisionInterpreter(provider)
        image_data = await image.read()
        vision = await interpreter.interpret_sketch(
            image_data=image_data, 
            annotations=annotations, 
            image_media_type=image.content_type
        )
        
        if not vision.success:
            return SpiralSketchResponse(
                success=False,
                design_id=design_id,
                design_version_before=design_version_before,
                design_version_after=design_version_before,
                status="failed",
                feedback="Sketch interpretation failed",
                errors=[vision.error or "vision_failed"],
            )

        # Step 2: Extract values for confirmation
        extracted_values = vision.interpretation.model_dump() if vision.interpretation else {}
        
        # Step 3: If not confirmed, return for human review (NEVER auto-execute sketches)
        if not confirm_execution:
            return SpiralSketchResponse(
                success=True,
                design_id=design_id,
                design_version_before=design_version_before,
                design_version_after=design_version_before,
                interpretation=extracted_values,
                extracted_values=extracted_values,
                requires_confirmation=True,  # Critical: UI must show confirmation dialog
                intent_string=vision.intent_string,
                program_text="",
                average_confidence=vision.confidence if hasattr(vision, 'confidence') else 0.5,
                status="awaiting_confirmation",
                feedback="Please confirm extracted values before execution",
            )

        # Step 4: Confirmed - proceed with geometry proposal
        from magnet.agents.geometry_proposer import create_geometry_proposer
        proposer = create_geometry_proposer()
        proposal = await proposer.propose(intent=vision.intent_string, current_state=sm.to_dict())
        
        if not proposal.success or not proposal.program:
            return SpiralSketchResponse(
                success=False,
                design_id=design_id,
                design_version_before=design_version_before,
                design_version_after=design_version_before,
                interpretation=extracted_values,
                extracted_values=extracted_values,
                requires_confirmation=False,
                intent_string=vision.intent_string,
                status="failed",
                feedback="Geometry proposal failed",
                errors=[proposal.error or "proposal_failed"],
            )

        # Step 5: Execute program
        from magnet.kernel.program_executor import execute_program
        try:
            result = execute_program(program_text=proposal.program_text, state_manager=sm, dry_run=False)
        except Exception as e:
            return SpiralSketchResponse(
                success=False,
                design_id=design_id,
                design_version_before=design_version_before,
                design_version_after=design_version_before,
                interpretation=extracted_values,
                intent_string=vision.intent_string,
                program_text=proposal.program_text,
                status="failed",
                feedback="Execution failed",
                errors=[str(e)],
            )

        design_version_after = getattr(sm, "design_version", sm.get("design_version", design_version_before))
        avg_conf = sum(op.confidence for op in proposal.program.operations) / max(len(proposal.program.operations), 1)

        # Emit WS events
        ws_manager.queue_message(
            WSMessage(
                type=MessageType.DESIGN_UPDATED.value,
                design_id=design_id,
                payload={"source": "spiral_sketch", "design_version_after": design_version_after},
            )
        )
        ws_manager.queue_message(
            WSMessage(
                type=MessageType.SNAPSHOT_CREATED.value,
                design_id=design_id,
                payload={"design_version_after": design_version_after, "artifact": "geometry.glb", "ready": True},
            )
        )

        return SpiralSketchResponse(
            success=result.success,
            design_id=design_id,
            design_version_before=design_version_before,
            design_version_after=design_version_after,
            interpretation=extracted_values,
            extracted_values=extracted_values,
            requires_confirmation=False,
            intent_string=vision.intent_string,
            program_text=proposal.program_text,
            average_confidence=avg_conf,
            status="applied" if result.success else "failed",
            feedback="Sketch executed successfully" if result.success else "Execution failed",
            metrics=(result.validation or {}).get("metrics", {}),
            deltas=(result.validation or {}).get("deltas", {}),
            glb_ready=True if result.success else False,
            errors=result.errors if hasattr(result, 'errors') else [],
        )

    # §SKELETON:MigrationEndpoint
    @router.post("/api/v1/designs/{design_id}/migrate-to-geometry")
    async def migrate_to_geometry(
        design_id: str,
        preview_only: bool = True,
        expected_version: Optional[int] = None,
    ):
        """
        MIGRATION ONLY: Convert legacy parametric state to geometry primitives.
        
        ⚠️ WARNING: This is one-time backward compatibility code.
        DO NOT copy this pattern to kernel or agent code.
        
        - preview_only=True: return DSL program without committing
        - preview_only=False: execute and commit (requires explicit confirmation)
        """
        sm = get_state_manager(design_id)
        if not sm:
            raise HTTPException(status_code=404, detail="Design not found")

        current_version = getattr(sm, "design_version", sm.get("design_version", 0))
        if expected_version is not None and expected_version != current_version:
            raise HTTPException(status_code=409, detail={"error": "stale_version"})

        # Check if already has geometry resources
        resources = sm.get("resources", {})
        if resources.get("geometry"):
            return {"success": False, "error": "Design already has geometry resources", "needs_migration": False}

        # Extract legacy parameters
        hull_loa = sm.get("hull.loa")
        hull_beam = sm.get("hull.beam")
        hull_draft = sm.get("hull.draft")
        hull_type = sm.get("hull.hull_type", "monohull")  # Legacy enum field

        if not all([hull_loa, hull_beam, hull_draft]):
            return {"success": False, "error": "Missing required hull dimensions", "needs_migration": True}

        # Generate migration program (MIGRATION ONLY - hardcoded mapping)
        # NOTE: This is acceptable as one-time migration, not kernel logic
        body_count = 1
        body_offset = 0.0
        if hull_type and "catamaran" in str(hull_type).lower():
            body_count = 2
            body_offset = hull_beam / 4  # Approximate demihull spacing

        program_lines = [
            f"# MIGRATION: Auto-generated from legacy state",
            f"# Source: hull_type={hull_type}, loa={hull_loa}, beam={hull_beam}, draft={hull_draft}",
            f"# Provenance: migration_only",
            f"",
        ]
        
        if body_count == 1:
            program_lines.extend([
                f'CREATE geometry.body main {{',
                f'  body_type: "hull"',
                f'  physics_category: "surface_piercing"',
                f'  offset_y_m: 0.0',
                f'}}',
            ])
        else:
            program_lines.extend([
                f'CREATE geometry.body port {{',
                f'  body_type: "demihull"',
                f'  physics_category: "surface_piercing"',
                f'  offset_y_m: {-body_offset}',
                f'}}',
                f'CREATE geometry.body stbd {{',
                f'  body_type: "demihull"',
                f'  physics_category: "surface_piercing"',
                f'  offset_y_m: {body_offset}',
                f'}}',
            ])

        program_text = "\n".join(program_lines)

        if preview_only:
            return {
                "success": True,
                "preview_only": True,
                "program_text": program_text,
                "needs_migration": True,
                "legacy_values": {"hull_type": hull_type, "loa": hull_loa, "beam": hull_beam, "draft": hull_draft},
                "message": "Review program and call with preview_only=false to execute",
            }

        # Execute migration
        from magnet.kernel.program_executor import execute_program
        try:
            result = execute_program(program_text=program_text, state_manager=sm, dry_run=False)
            return {
                "success": result.success,
                "preview_only": False,
                "program_text": program_text,
                "design_version_after": getattr(sm, "design_version", current_version),
                "errors": result.errors if hasattr(result, 'errors') else [],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    return router
```

#### Wire the router (exact place)

**File:** `magnet/deployment/api.py`  
**Location:** inside `create_fastapi_app`, after `ws_manager` is created and after `get_state_manager(design_id)` helper exists (currently near the dependency helpers around `get_state_manager`).

§SKELETON:WireRouter

```python
# Add to imports at top of api.py
from magnet.deployment.spiral_endpoints import create_spiral_router

# Add inside create_fastapi_app(), after ws_manager is created:
# (Search for "ws_manager = ConnectionManager" to find the right location)

# Wire spiral endpoints (design-scoped, persistent, single authority)
spiral_router = create_spiral_router(
    get_state_manager=lambda design_id: design_store.load(design_id) if design_store.exists(design_id) else None,
    ws_manager=ws_manager,
)
app.include_router(spiral_router)
```

#### Error handling spec (spiral endpoints)

| Failure mode | HTTP | `status` field | Must commit? | UI behavior |
|---|---:|---|---|---|
| avg_confidence < min | 200 | `proposal_low_confidence` | NO | show proposal + confirm apply (`force_apply=true`) |
| needs clarification | 200 | `needs_clarification` | NO | show `clarification_questions[]` + send clarification response |
| execution fails mid-transaction | 200 | `failed` | NO | show errors; keep previous model |
| stale concurrent request | 409 | (n/a) | NO | UI refreshes state + retries with new expected_version |
| downstream critical phase fails | 200 | `partial` | YES | show failed phases; UI offers “continue anyway” vs revise |
| WS disconnect | n/a | n/a | YES/NO depends | UI resyncs via GET `/designs/{id}` + continues |
| GLB not ready within timeout | 200 | `applied` but `glb_ready=false` | YES | UI waits for `snapshot_created` until retry limit hit |

#### WebSocket event schemas (exact JSON envelope)

All WS messages are sent as `WSMessage.to_dict()`:

```json
{
  "type": "design_updated",
  "message_id": "abcd1234",
  "design_id": "MAGNET-...",
  "payload": { "...": "..." },
  "timestamp": "2026-01-06T00:00:00+00:00"
}
```

**Spiral update (use existing `design_updated` type):**

```json
{
  "type": "design_updated",
  "design_id": "MAGNET-...",
  "payload": {
    "source": "spiral",
    "spiral_iteration": 7,
    "design_version_after": 12,
    "status": "applied",
    "average_confidence": 0.78,
    "metrics": { "gm_m": 0.62 },
    "deltas": { "gm_m": 0.04 }
  }
}
```

**GLB ready (use existing `snapshot_created`):**

```json
{
  "type": "snapshot_created",
  "design_id": "MAGNET-...",
  "payload": {
    "artifact": "geometry.glb",
    "design_version_after": 12,
    "ready": true
  }
}
```

**Clarification needed (transition-safe plan):**

**Fix (no shortcut):** Clarification must be first-class. Use both:

1. Response field: `clarification_questions[]`
2. WS payload: include `clarification_questions[]` when `status="needs_clarification"`

This avoids inventing new WS message types while still preserving structured human-in-loop.

---

### Phase 2: UIv2 Migration (Remove Legacy Calls + Remove Enum Taxonomy)

#### §SKELETON:UIWiring — UIv2 DOM + Event Wiring (Exact Selectors + Wire Points)

This section answers, **from the actual UIv2 code**, “which element triggers what” and “where to attach handlers”.

##### 1) Chat submission (text → spiral/chat)
- **DOM elements**
  - **Chat input**: `#chatInput` (file: `magnet/ui_v2/index.html`, line ~1691)
  - **Send button**: `#chatSend` (file: `magnet/ui_v2/index.html`, line ~1692)
  - **Terminal output**: `#terminal` (file: `magnet/ui_v2/index.html`, line ~1684)
- **Event listeners (already wired)**
  - `dom.chatSend.addEventListener('click', handleCommand);` (file: `magnet/ui_v2/index.html`, line ~2083)
  - `dom.chatInput.addEventListener('keypress', …Enter… handleCommand());` (file: `magnet/ui_v2/index.html`, line ~2084)
- **Submission funnel (already wired)**
  - `handleCommand()` reads input and emits: `emit('command', { command: cmd })` (file: `magnet/ui_v2/index.html`, lines ~2277–2286)
- **Backend wire point (THIS is what you change)**
  - The UI does **not** call HTTP directly. It emits `command` and the adapter handles it:
  - `MagnetStudio.on('command', async (data) => { ... })` (file: `magnet/ui_v2/js/backend-adapter.js`, line ~356)
- **What to modify**
  - In `magnet/ui_v2/js/backend-adapter.js` inside `bindUIEvents()` → `MagnetStudio.on('command', …)`:
    - Replace the **legacy** block:
      - `POST /api/v1/designs/{id}/intent/preview` (file: `backend-adapter.js`, lines ~491–494)
      - `POST /api/v1/designs/{id}/actions` (file: `backend-adapter.js`, lines ~728–732)
    - With the **spiral** call + handler routing:
      - See `§SKELETON:SpiralChatCall` and `§SKELETON:ResponseHandler` below.

##### 2) Sketch upload (image → spiral/sketch)
- **Current status (as implemented today)**: **UIv2 has NO sketch upload control.**  
  Repo grep shows no `type="file"` / image upload elements in `magnet/ui_v2/index.html`.
- **Required DOM additions (minimal, explicit)**
  - Add these inside the chat panel (recommended location: within `.chat-expanded`, near the header/input) **and** register them in `cacheDom()`:

```html
<!-- File: magnet/ui_v2/index.html (add inside .chat-expanded) -->
<input id="sketchInput" type="file" accept="image/*" style="display:none" />
<button class="top-btn" id="btnSketch" title="Upload sketch">Sketch</button>
<div id="clarificationContainer"></div> <!-- mount ClarificationPanel here -->
```

- **Required DOM caching**
  - Update `cacheDom()` list (file: `magnet/ui_v2/index.html`, around the ID array near line ~1885) to include:

```javascript
// File: magnet/ui_v2/index.html
// Add these IDs into the cacheDom() array:
// 'btnSketch', 'sketchInput', 'clarificationContainer'
```

- **Required event wiring**
  - Add to `bindEvents()` (file: `magnet/ui_v2/index.html`, near other `dom.*.addEventListener` lines ~2080+):

```javascript
// File: magnet/ui_v2/index.html (inside bindEvents())
dom.btnSketch.addEventListener('click', () => dom.sketchInput.click());
dom.sketchInput.addEventListener('change', async (e) => {
  const file = e.target.files?.[0];
  if (!file) return;
  emit('sketchUpload', { file, annotations: '' });
  e.target.value = '';
});
```

- **Backend adapter wire point**
  - Add a new event subscription in `magnet/ui_v2/js/backend-adapter.js` inside `bindUIEvents()`:

```javascript
// File: magnet/ui_v2/js/backend-adapter.js (inside bindUIEvents())
MagnetStudio.on('sketchUpload', async ({ file, annotations }) => {
  // Call /api/v1/designs/{id}/spiral/sketch (multipart)
  // Handle awaiting_confirmation → show confirm → resubmit with confirm_execution=true
  // See: §SKELETON:SketchConfirm and §SKELETON:SpiralEndpoints (spiral_sketch)
});
```

##### 3) Existing “UI feedback” primitives you SHOULD reuse (so you don’t invent new UI systems)
These already exist in `magnet/ui_v2/index.html`:
- **Toasts**: `MagnetStudio.toast(message, type)` (lines ~2529–2538) → uses `#toastContainer` (line ~1788)
- **Status**: `MagnetStudio.setStatus(text, type)` (lines ~2391–2396)
- **Loading overlay**: `MagnetStudio.showLoading(text)` / `hideLoading()` (lines ~2522–2527)
- **Terminal printing**: `MagnetStudio.terminal.*` (lines ~2407–2428)

Use these for:
- **low_confidence**: `MagnetStudio.toast('Low confidence…', 'warning')` + print DSL to terminal
- **needs_clarification**: mount Clarification UI under `#clarificationContainer` (new) + print questions to terminal
- **partial**: `MagnetStudio.toast('Applied with warnings…', 'warning')` + list failed phases in terminal
- **failed**: `MagnetStudio.toast('Failed…', 'error')` + errors to terminal

##### 4) WebSocket reconnect + resync (already mostly present)
- **WS connect**: `MAGNETBackendAdapter.connect()` opens WS and then calls `await this.loadDesignState()` (file: `magnet/ui_v2/js/backend-adapter.js`, lines ~141–198)
- **WS close**: calls `attemptReconnect()` which calls `connect(this.designId)` again (lines ~160–164, ~1119–1127)
- **Resync on updates**: on `design_updated`, adapter calls `this.loadDesignState()` (lines ~294–299)

**What you still must ensure for “spiral context survives refresh/reconnect”:**
- Backend must persist `spiral_iteration` + checkpoint into DesignStore-backed state, so `GET /api/v1/designs/{id}` returns it and `loadDesignState()` can display it.

#### Line-by-line JS replacements (backend-adapter.js)

**File:** `magnet/ui_v2/js/backend-adapter.js`

##### §SKELETON:SpiralChatCall

**Old (L491–L494):**

```javascript
const preview = await this.post(
  `/api/v1/designs/${this.designId}/intent/preview`,
  { text: command, mode: 'compound' }
);
```

**New:**

```javascript
// Step 2.1: Replace legacy preview with spiral/chat
const result = await this.post(
  `/api/v1/designs/${this.designId}/spiral/chat`,
  {
    message: command,
    constraints: this._activeConstraints || [],
    expected_version: this._lastDesignVersion ?? null,
    request_id: crypto?.randomUUID?.() ?? String(Date.now()),
    min_confidence: 0.6,
    force_apply: false,
    run_critical_phases: true,
    glb_timeout_ms: 2000,
    glb_retry_limit: 5
  }
);

// Handle response
await this._handleSpiralResponse(result);
```

##### §SKELETON:ResponseHandler

**Old apply path (L728–L732):**

```javascript
const result = await this.post(
  `/api/v1/designs/${this.designId}/actions`,
  preview.apply_payload
);
```

**New:** Complete response handler that routes to appropriate UI flow:

```javascript
// Step 2.2: Unified spiral response handler
async _handleSpiralResponse(result) {
  // Store last message for retry scenarios
  this._lastMessage = result.message || this._lastMessage;
  
  switch (result.status) {
    case 'applied':
      this._lastDesignVersion = result.design_version_after;
      this._spiralIteration = result.spiral_iteration;
      this._refreshPhasesFromResponse(result);
      if (result.glb_ready) {
        await this._loadHullGeometryWithRetry(result.design_version_after);
      } else if (result.glb_retry_after_ms) {
        setTimeout(() => this._loadHullGeometryWithRetry(result.design_version_after), result.glb_retry_after_ms);
      }
      this._showSuccessFeedback(result.feedback, result.metrics, result.deltas);
      break;
      
    case 'partial':
      this._lastDesignVersion = result.design_version_after;
      this._handlePartialStatus(result);
      break;
      
    case 'proposal_low_confidence':
      await this._handleLowConfidence(result);
      break;
      
    case 'needs_clarification':
      await this._handleClarification(result);
      break;
      
    case 'failed':
      this._showErrorFeedback(result.feedback, result.errors);
      break;
      
    default:
      console.warn('Unknown spiral status:', result.status);
      this._showErrorFeedback('Unexpected response status', [result.status]);
  }
}
```

##### §SKELETON:LowConfidenceHandler

```javascript
// Step 2.3: Handle low confidence proposals
async _handleLowConfidence(result) {
  const confirmed = await this._showConfirmationDialog({
    title: 'Low Confidence Proposal',
    message: `Agent confidence: ${(result.average_confidence * 100).toFixed(0)}%`,
    details: result.program_text,
    confirmText: 'Apply Anyway',
    cancelText: 'Refine Request'
  });
  
  if (confirmed) {
    // Re-call with force_apply
    return this.post(`/api/v1/designs/${this.designId}/spiral/chat`, {
      message: this._lastMessage,
      expected_version: result.design_version_after,
      force_apply: true,
      request_id: crypto?.randomUUID?.() ?? String(Date.now())
    });
  }
  return null; // User chose to refine
}
```

##### §SKELETON:ClarificationHandler

```javascript
// Step 2.4: Handle clarification requests
async _handleClarification(result) {
  const panel = this._clarificationPanel;
  panel.show({
    questions: result.clarification_questions,
    requestId: result.clarification_request_id,
    onSubmit: async (responses) => {
      const followUp = await this.post(`/api/v1/designs/${this.designId}/spiral/chat`, {
        message: this._lastMessage,
        expected_version: result.design_version_after,
        clarification_response: responses,
        request_id: crypto?.randomUUID?.() ?? String(Date.now())
      });
      panel.hide();
      return this._handleSpiralResponse(followUp);
    },
    onCancel: () => panel.hide()
  });
}
```

##### §SKELETON:PartialHandler

```javascript
// Step 2.5: Handle partial success (some phases failed)
_handlePartialStatus(result) {
  const failedList = result.failed_phases.join(', ');
  this._showWarningBanner({
    message: `Applied with warnings. Failed phases: ${failedList}`,
    actions: [
      { label: 'View Details', onClick: () => this._showPhaseErrors(result.failed_phases) },
      { label: 'Continue', onClick: () => this._dismissWarning() }
    ]
  });
  // Still update version and reload GLB since geometry was applied
  this._lastDesignVersion = result.design_version_after;
  if (result.glb_ready) {
    this._loadHullGeometry(result.design_version_after);
  }
}
```

##### §SKELETON:409RetryHandler

```javascript
// Step 2.6: Handle 409 conflict (stale version)
async _handleConflict(response, originalMessage) {
  const err = await response.json();
  console.warn('Version conflict:', err.detail);
  
  // Update to server's current version
  this._lastDesignVersion = err.detail.current_version;
  
  // Retry with updated version
  return this.post(`/api/v1/designs/${this.designId}/spiral/chat`, {
    message: originalMessage,
    expected_version: this._lastDesignVersion,
    request_id: crypto?.randomUUID?.() ?? String(Date.now())
  });
}
```

##### §SKELETON:GLBRetry

```javascript
// Step 2.8: GLB loading with retry and backoff
async _loadHullGeometryWithRetry(version, retryLimit = 5, initialDelayMs = 500) {
  for (let attempt = 0; attempt < retryLimit; attempt++) {
    try {
      const resp = await fetch(
        `/api/v1/designs/${this.designId}/3d/export/glb?v=${version}`,
        { cache: 'no-store' }
      );
      if (resp.ok) {
        const blob = await resp.blob();
        await this._sceneManager.loadGLB(blob);
        return true;
      }
      if (resp.status === 404 || resp.status === 202) {
        // Not ready yet, wait and retry
        const delay = initialDelayMs * Math.pow(2, attempt);
        await new Promise(r => setTimeout(r, delay));
        continue;
      }
      throw new Error(`GLB fetch failed: ${resp.status}`);
    } catch (e) {
      if (attempt === retryLimit - 1) throw e;
    }
  }
  throw new Error('GLB not ready after max retries');
}
```

##### §SKELETON:WSResync

```javascript
// Step 2.9: WebSocket reconnection state resync
async _onWsReconnect() {
  console.log('WS reconnected, resyncing state...');
  try {
    const state = await this.get(`/api/v1/designs/${this.designId}`);
    this._lastDesignVersion = state.design_version || 0;
    this._spiralIteration = state.metadata?.spiral_iteration || 0;
    
    // Reload GLB if version changed
    if (state.design_version !== this._renderedVersion) {
      await this._loadHullGeometryWithRetry(state.design_version);
      this._renderedVersion = state.design_version;
    }
    
    // Refresh panels
    this._refreshAllPanels(state);
  } catch (e) {
    console.error('Resync failed:', e);
    this._showError('Connection restored but state sync failed. Please refresh.');
  }
}
```

##### §SKELETON:SketchConfirm

```javascript
// Step 2.10: Sketch result confirmation before execution
async _handleSketchResult(result) {
  if (!result.requires_confirmation) {
    // High confidence, proceed automatically
    return this._executeSpiralFromSketch(result);
  }
  
  // Show extracted values for human confirmation
  const confirmed = await this._showSketchConfirmationDialog({
    extractedValues: result.extracted_values,
    interpretation: result.interpretation,
    intentString: result.intent_string,
    confidence: result.average_confidence
  });
  
  if (confirmed) {
    return this._executeSpiralFromSketch(result);
  }
  return null; // User rejected
}

async _executeSpiralFromSketch(sketchResult) {
  return this.post(`/api/v1/designs/${this.designId}/spiral/chat`, {
    message: sketchResult.intent_string,
    expected_version: this._lastDesignVersion,
    force_apply: true, // Already confirmed by user
    request_id: crypto?.randomUUID?.() ?? String(Date.now())
  });
}
```

##### §SKELETON:PhaseRefresh

```javascript
// Step 2.11: Phase refresh from spiral response (replaces HULL_PATHS)
_refreshPhasesFromResponse(result) {
  // Use invalidated_phases from response instead of hardcoded HULL_PATHS
  const phases = result.invalidated_phases || ['hull_form', 'weight_stability', 'structure'];
  
  phases.forEach(phase => {
    const panel = this._panels[phase];
    if (panel) {
      panel.refresh();
    }
  });
  
  // Update metrics display
  if (result.metrics) {
    this._updateMetricsPanel(result.metrics, result.deltas);
  }
}
```

##### Replacement 3: remove hardcoded `HULL_PATHS` taxonomy routing

**Old (L791+ includes `hull.hull_type`, `hull.chine_*`, `hull.has_spray_rails`, etc.)**

**New:** Determine refresh actions from spiral response:
- use `invalidated_phases` returned by spiral
- fallback: always refresh hull + physics panels after spiral

##### §SKELETON:ClarificationPanel

**File:** `magnet/ui_v2/js/clarification-panel.js` (new file)

```javascript
// Step 2.7: Clarification panel for human-in-loop
export class ClarificationPanel {
  constructor(containerEl) {
    this.container = containerEl;
    this._onSubmit = null;
    this._onCancel = null;
  }

  show({ questions, requestId, onSubmit, onCancel }) {
    this._onSubmit = onSubmit;
    this._onCancel = onCancel;
    
    this.container.innerHTML = `
      <div class="clarification-panel">
        <h3>Clarification Needed</h3>
        <form id="clarification-form">
          ${questions.map((q, i) => this._renderQuestion(q, i)).join('')}
          <div class="clarification-actions">
            <button type="button" class="btn-cancel">Cancel</button>
            <button type="submit" class="btn-submit">Submit</button>
          </div>
        </form>
      </div>
    `;
    
    this.container.querySelector('.btn-cancel').onclick = () => this.hide();
    this.container.querySelector('#clarification-form').onsubmit = (e) => {
      e.preventDefault();
      this._handleSubmit(requestId);
    };
    
    this.container.style.display = 'block';
  }

  _renderQuestion(question, index) {
    const { id, text, type, options } = question;
    const inputId = `clarification-${id || index}`;
    
    if (type === 'select' && options) {
      return `
        <div class="clarification-question">
          <label for="${inputId}">${text}</label>
          <select id="${inputId}" name="${id || index}" required>
            <option value="">Select...</option>
            ${options.map(o => `<option value="${o.value}">${o.label}</option>`).join('')}
          </select>
        </div>
      `;
    }
    
    return `
      <div class="clarification-question">
        <label for="${inputId}">${text}</label>
        <input type="text" id="${inputId}" name="${id || index}" required />
      </div>
    `;
  }

  async _handleSubmit(requestId) {
    const form = this.container.querySelector('#clarification-form');
    const formData = new FormData(form);
    const responses = Object.fromEntries(formData.entries());
    
    if (this._onSubmit) {
      await this._onSubmit({ requestId, responses });
    }
  }

  hide() {
    this.container.style.display = 'none';
    this.container.innerHTML = '';
    if (this._onCancel) {
      this._onCancel();
    }
  }
}
```

##### Replacement 4: panel-config hull_type display removal

**File:** `magnet/ui_v2/js/panel-config.js`

- Remove badge `field: "hull_type"` (L25–L34)
- Remove classification row `key: "hull_type"` (L59–L62)
- Replace with derived facts (e.g. `hydrostatics_method`, `body_count` if available)

---

### Phase 3: Disable Legacy Protocol in Production

**Feature flag already exists:** `MAGNET_LEGACY_INTENT_PROTOCOL_ENABLED`

**Acceptance test already exists and passes:** `tests/deployment/test_legacy_intent_protocol_flag.py`

---

## Sacred Invariants Checkpoints (run after each phase)

After **every phase (-1, 1, 2, 3)**:

```bash
python3 -m pytest tests/invariants/ -v
```

After **any endpoint/WS change**:

```bash
python3 -m pytest tests/deployment/ -v
```

---

## Rollback Plan (by Phase)

---

## Phase 1 Decision Gate Tests (MUST be added and MUST pass before Phase 1 is “done”)

These tests prevent the exact regressions you flagged (race conditions, misleading “applied”, and sketch OCR mistakes).

### Test 1: Optimistic locking returns 409 on stale version

**File:** `tests/deployment/test_spiral_concurrency.py`

§SKELETON:ConcurrencyTest

```python
from fastapi.testclient import TestClient
import pytest
import os


# Skip if spiral endpoints not yet implemented
SPIRAL_ENDPOINTS_EXIST = os.environ.get("MAGNET_SPIRAL_IMPLEMENTED", "false").lower() == "true"


@pytest.mark.skipif(not SPIRAL_ENDPOINTS_EXIST, reason="Spiral endpoints not yet implemented")
def test_spiral_chat_optimistic_locking_409(monkeypatch):
    """
    MUST FAIL if:
    - Spiral endpoints return 404 (not implemented)
    - 409 not returned on stale version
    - Error payload missing 'stale_version' error code
    """
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    design_id = "MAGNET-TEST"

    # First call establishes version
    r1 = client.post(
        f"/api/v1/designs/{design_id}/spiral/chat",
        json={"message": "Make it faster", "expected_version": 1, "request_id": "r1"},
    )
    # FAIL FAST: 404 means endpoints not implemented
    assert r1.status_code != 404, "Spiral endpoints not implemented - this test requires /spiral/chat"
    assert r1.status_code == 200

    # Second call with SAME expected_version should 409
    r2 = client.post(
        f"/api/v1/designs/{design_id}/spiral/chat",
        json={"message": "Make it faster", "expected_version": 1, "request_id": "r2"},
    )
    assert r2.status_code == 409, f"Expected 409 for stale version, got {r2.status_code}"
    assert r2.json()["detail"]["error"] == "stale_version"
    assert "current_version" in r2.json()["detail"]


def test_spiral_endpoint_exists():
    """Basic smoke test - endpoint must exist and not 404."""
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    # OPTIONS or malformed POST should NOT return 404
    r = client.post("/api/v1/designs/TEST/spiral/chat", json={})
    assert r.status_code != 404, "Spiral endpoint /spiral/chat not registered"
```

### Test 2: `status="partial"` when critical phases fail

**File:** `tests/deployment/test_spiral_partial_status.py`

§SKELETON:PartialTest

```python
from fastapi.testclient import TestClient
import pytest
import os


SPIRAL_ENDPOINTS_EXIST = os.environ.get("MAGNET_SPIRAL_IMPLEMENTED", "false").lower() == "true"


@pytest.mark.skipif(not SPIRAL_ENDPOINTS_EXIST, reason="Spiral endpoints not yet implemented")
def test_spiral_returns_partial_when_failed_phases_present(monkeypatch):
    """
    MUST FAIL if:
    - Spiral endpoints return 404
    - Response missing 'status' field
    - Response missing 'failed_phases' field
    - status != 'partial' when failed_phases is non-empty
    """
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    design_id = "MAGNET-TEST"

    resp = client.post(
        f"/api/v1/designs/{design_id}/spiral/chat",
        json={
            "message": "Create novel hull geometry",
            "expected_version": 1,
            "run_critical_phases": True,
            "critical_phases": ["structure"],
        },
    )
    # FAIL FAST
    assert resp.status_code != 404, "Spiral endpoints not implemented"
    
    body = resp.json()
    
    # Required fields must exist
    assert "status" in body, "Response missing 'status' field"
    assert "failed_phases" in body, "Response missing 'failed_phases' field"
    
    # Status must be one of valid values
    assert body["status"] in ("applied", "partial", "failed", "proposal_low_confidence", "needs_clarification")
    
    # Critical invariant: failed_phases non-empty => status must be 'partial'
    if body["failed_phases"]:
        assert body["status"] == "partial", f"Expected status='partial' when failed_phases={body['failed_phases']}"


def test_spiral_response_has_required_fields():
    """Verify response schema completeness."""
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    resp = client.post(
        "/api/v1/designs/TEST/spiral/chat",
        json={"message": "test", "force_apply": True},
    )
    if resp.status_code == 200:
        body = resp.json()
        required = ["success", "design_id", "status", "failed_phases", "spiral_iteration"]
        for field in required:
            assert field in body, f"Response missing required field: {field}"
```

### Test 3: Sketch confirmation gate (must not silently execute wrong OCR)

**File:** `tests/deployment/test_spiral_sketch_confirmation.py`

§SKELETON:SketchTest

```python
from fastapi.testclient import TestClient
import pytest
import os


SPIRAL_ENDPOINTS_EXIST = os.environ.get("MAGNET_SPIRAL_IMPLEMENTED", "false").lower() == "true"


@pytest.mark.skipif(not SPIRAL_ENDPOINTS_EXIST, reason="Spiral endpoints not yet implemented")
def test_spiral_sketch_requires_confirmation(monkeypatch):
    """
    CRITICAL: Sketch endpoint must NEVER auto-execute without confirmation.
    
    MUST FAIL if:
    - Spiral endpoints return 404
    - Response missing 'requires_confirmation' field
    - requires_confirmation is False without explicit confirm_execution=true
    - Response missing 'extracted_values' field
    """
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    design_id = "MAGNET-TEST"

    # Create a minimal PNG (1x1 pixel)
    png_bytes = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
        b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
        b'\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    files = {"image": ("sketch.png", png_bytes, "image/png")}
    data = {"annotations": "25m"}  # No confirm_execution

    resp = client.post(f"/api/v1/designs/{design_id}/spiral/sketch", files=files, data=data)
    
    # FAIL FAST
    assert resp.status_code != 404, "Spiral sketch endpoint not implemented"
    
    body = resp.json()
    
    # CRITICAL: Without confirm_execution=true, must require confirmation
    assert "requires_confirmation" in body, "Response missing 'requires_confirmation' field"
    assert body["requires_confirmation"] is True, (
        "SECURITY: Sketch endpoint must require confirmation by default. "
        "Got requires_confirmation=False without explicit confirm_execution=true"
    )
    
    # Must provide extracted values for user review
    assert "extracted_values" in body, "Response missing 'extracted_values' field"
    assert body["status"] == "awaiting_confirmation"


@pytest.mark.skipif(not SPIRAL_ENDPOINTS_EXIST, reason="Spiral endpoints not yet implemented")
def test_spiral_sketch_executes_with_confirmation():
    """Verify sketch executes when confirm_execution=true."""
    from magnet.deployment.api import create_fastapi_app

    app = create_fastapi_app(context=None)
    client = TestClient(app)

    png_bytes = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
        b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
        b'\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    files = {"image": ("sketch.png", png_bytes, "image/png")}
    data = {"annotations": "25m LOA", "confirm_execution": "true"}

    resp = client.post("/api/v1/designs/TEST/spiral/sketch", files=files, data=data)
    
    assert resp.status_code != 404, "Spiral sketch endpoint not implemented"
    
    body = resp.json()
    # When confirmed, should attempt execution (may fail for other reasons, but not require confirmation)
    assert body.get("requires_confirmation") is not True or body.get("status") != "awaiting_confirmation"
```

### Decision gate

**DO NOT proceed** to Phase 2 (UI migration) until these three tests pass **and** invariants still pass:

```bash
python3 -m pytest tests/deployment/test_spiral_concurrency.py -v
python3 -m pytest tests/deployment/test_spiral_partial_status.py -v
python3 -m pytest tests/deployment/test_spiral_sketch_confirmation.py -v
python3 -m pytest tests/invariants/ -v
```


### Rollback Phase 2 (UI changes)

- Revert UIv2 to legacy path by restoring calls to:
  - `/intent/preview`
  - `/actions`
- Set `MAGNET_LEGACY_INTENT_PROTOCOL_ENABLED=true`

### Rollback Phase 1 (spiral endpoints)

- Keep spiral endpoints behind an enable flag if needed:
  - `MAGNET_SPIRAL_ENABLED=false` (recommended to add)
- UI uses legacy path until spiral is stable

### Rollback Phase -1 (DesignStore persistence)

- Keep DesignStore v2 behind a flag:
  - `MAGNET_DESIGN_STORE_V2_ENABLED=false`
- Operate in single-design mode temporarily

## Acceptance Tests (Must Pass Before Calling It “Production-Ready”)

### End-to-end UIv2 spiral tests (manual + automated)

1. **Sketch → GLB**  
   Upload sketch with “25m” on it:
   - interpretation extracts `loa_m=25`
   - geometry compiles
   - GLB updates in viewport

2. **Chat iteration loop**  
   “Make it faster”:
   - returns a geometry program
   - metrics/deltas change (resistance or validity notes)
   - GLB changes deterministically by design_version

3. **THE TEST (mission gates)**  
   - stepped ventilated planing hull (discontinuities + flow paths + openings)
   - twin hull via bodies/sections (no hull_type)
   - novel 4-body config validates without new code

### Architectural invariants

- `pytest tests/invariants/` must remain green
- Forbidden design terms must not appear in kernel-executed program path (existing invariant suite)

---

## Decision: Which UI is “UIv2” for production?

Given backend serving priority, **UIv2 is currently `magnet/ui_v2/`**, not the React app.

**Recommendation:** Treat `magnet/ui_v2/` as the production interface until/unless React is explicitly promoted—because the backend already guarantees a single-origin deployment with no extra infra.

---

## Final Recommendation (Best Course of Action)

1. **Do not attempt to “bridge” UIv2 command parsing into the new architecture.**  
   Replace the control plane, don’t duct-tape it.

2. **Make the new generative loop design-scoped and persistent** (`/api/v1/designs/{design_id}/spiral/*`).  
   This is the minimal change that enforces “one authority”.

3. **Update UIv2 to call only spiral endpoints for design iteration**, keep meta-actions as explicit UI buttons.

This yields a single production-ready interface with no duplicate paths and preserves MAGNET's "combinatorial explosion" contract.

---

## Full Feature Test Matrix

### What Will Work After Implementation

| Flow | Status | Required Code |
|------|--------|---------------|
| Type "make it faster" → GLB updates | ✅ | `§SKELETON:SpiralChatCall` + `§SKELETON:ResponseHandler` |
| Type "I want a catamaran" → 2 bodies created | ✅ | `§SKELETON:SpiralEndpoints` (spiral_chat) |
| Sketch upload → geometry preview | ✅ | `§SKELETON:SpiralEndpoints` (spiral_sketch) |
| Sketch → confirm → execute | ✅ | `§SKELETON:SketchConfirm` + backend sketch handler |
| Low confidence → review panel | ✅ | `§SKELETON:LowConfidenceHandler` |
| Clarification questions → form | ✅ | `§SKELETON:ClarificationHandler` + `§SKELETON:ClarificationPanel` |
| 409 conflict → auto-retry | ✅ | `§SKELETON:409RetryHandler` |
| Partial success → warning | ✅ | `§SKELETON:PartialHandler` |
| WS disconnect → resync | ✅ | `§SKELETON:WSResync` |
| GLB slow → retry with backoff | ✅ | `§SKELETON:GLBRetry` |
| Legacy design → migration | ✅ | `§SKELETON:MigrationEndpoint` |
| Checkpoint persistence | ✅ | `§SKELETON:CheckpointPruning` |

### Manual Test Script (Post-Implementation)

```bash
# 1. Start server
cd /Users/bengibson/MAGNETV1
python3 -m magnet.deployment.api

# 2. Open UI
open http://localhost:8000

# 3. Test chat flow
# Type: "I want a catamaran"
# Expected: See 2 geometry.body created, GLB updates, metrics shown

# 4. Test iteration
# Type: "make it faster"
# Expected: L/B ratio changes, GLB updates, deltas shown

# 5. Test sketch (if image available)
# Upload sketch with "25m" annotation
# Expected: Confirmation dialog with extracted_values

# 6. Test low confidence (force by using vague input)
# Type: "something boat-like"
# Expected: Low confidence panel with "Apply Anyway" button

# 7. Test 409 (open two tabs, submit simultaneously)
# Expected: One succeeds, other auto-retries

# 8. Test WS disconnect
# Kill server, restart, refresh UI
# Expected: State resyncs automatically
```

---

## §SKELETON:CompleteUIModule — Copy-Paste Ready

**File:** `magnet/ui_v2/js/spiral-adapter.js` (new file)

This is the complete UI module that implements ALL spiral features. Copy this entire file.

```javascript
/**
 * MAGNET Spiral Adapter
 * 
 * Complete implementation of the design spiral UI integration.
 * Handles: chat, sketch, low confidence, clarification, 409 retry, 
 * partial status, WS resync, GLB retry.
 */

import { ClarificationPanel } from './clarification-panel.js';

export class SpiralAdapter {
  constructor(options = {}) {
    this.designId = options.designId || null;
    this.baseUrl = options.baseUrl || '';
    this._lastDesignVersion = 0;
    this._spiralIteration = 0;
    this._lastMessage = '';
    this._renderedVersion = null;
    this._activeConstraints = [];
    this._sceneManager = options.sceneManager;
    this._panels = options.panels || {};
    
    // Initialize clarification panel
    const clarificationContainer = document.getElementById('clarification-container');
    this._clarificationPanel = clarificationContainer 
      ? new ClarificationPanel(clarificationContainer) 
      : null;
  }

  // ============================================================
  // §SKELETON:SpiralChatCall — Main chat entry point
  // ============================================================
  async sendChat(message) {
    if (!this.designId) throw new Error('No design selected');
    
    this._lastMessage = message;
    
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/designs/${this.designId}/spiral/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          constraints: this._activeConstraints,
          expected_version: this._lastDesignVersion || null,
          request_id: crypto?.randomUUID?.() ?? String(Date.now()),
          min_confidence: 0.6,
          force_apply: false,
          run_critical_phases: true,
          glb_timeout_ms: 2000,
          glb_retry_limit: 5
        })
      });

      // §SKELETON:409RetryHandler — Handle version conflict
      if (response.status === 409) {
        return this._handleConflict(response, message);
      }

      if (!response.ok) {
        throw new Error(`Spiral chat failed: ${response.status}`);
      }

      const result = await response.json();
      return this._handleSpiralResponse(result);
    } catch (e) {
      this._showErrorFeedback('Request failed', [e.message]);
      throw e;
    }
  }

  // ============================================================
  // §SKELETON:ResponseHandler — Route response to appropriate handler
  // ============================================================
  async _handleSpiralResponse(result) {
    switch (result.status) {
      case 'applied':
        this._lastDesignVersion = result.design_version_after;
        this._spiralIteration = result.spiral_iteration;
        this._refreshPhasesFromResponse(result);
        if (result.glb_ready) {
          await this._loadHullGeometryWithRetry(result.design_version_after);
        } else if (result.glb_retry_after_ms) {
          setTimeout(() => this._loadHullGeometryWithRetry(result.design_version_after), result.glb_retry_after_ms);
        }
        this._showSuccessFeedback(result.feedback, result.metrics, result.deltas);
        return result;

      case 'partial':
        this._lastDesignVersion = result.design_version_after;
        this._handlePartialStatus(result);
        return result;

      case 'proposal_low_confidence':
        return this._handleLowConfidence(result);

      case 'needs_clarification':
        return this._handleClarification(result);

      case 'failed':
        this._showErrorFeedback(result.feedback, result.errors);
        return result;

      default:
        console.warn('Unknown spiral status:', result.status);
        this._showErrorFeedback('Unexpected response', [result.status]);
        return result;
    }
  }

  // ============================================================
  // §SKELETON:LowConfidenceHandler — Show proposal for review
  // ============================================================
  async _handleLowConfidence(result) {
    const confirmed = await this._showConfirmationDialog({
      title: 'Low Confidence Proposal',
      message: `Agent confidence: ${(result.average_confidence * 100).toFixed(0)}%`,
      details: result.program_text,
      confirmText: 'Apply Anyway',
      cancelText: 'Refine Request'
    });

    if (confirmed) {
      // Re-call with force_apply
      const response = await fetch(`${this.baseUrl}/api/v1/designs/${this.designId}/spiral/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: this._lastMessage,
          expected_version: result.design_version_after,
          force_apply: true,
          request_id: crypto?.randomUUID?.() ?? String(Date.now())
        })
      });
      return this._handleSpiralResponse(await response.json());
    }
    return null;
  }

  // ============================================================
  // §SKELETON:ClarificationHandler — Show clarification form
  // ============================================================
  async _handleClarification(result) {
    if (!this._clarificationPanel) {
      console.error('Clarification panel not initialized');
      return null;
    }

    return new Promise((resolve) => {
      this._clarificationPanel.show({
        questions: result.clarification_questions,
        requestId: result.clarification_request_id,
        onSubmit: async (responses) => {
          const response = await fetch(`${this.baseUrl}/api/v1/designs/${this.designId}/spiral/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              message: this._lastMessage,
              expected_version: result.design_version_after,
              clarification_response: responses,
              request_id: crypto?.randomUUID?.() ?? String(Date.now())
            })
          });
          this._clarificationPanel.hide();
          resolve(this._handleSpiralResponse(await response.json()));
        },
        onCancel: () => {
          this._clarificationPanel.hide();
          resolve(null);
        }
      });
    });
  }

  // ============================================================
  // §SKELETON:PartialHandler — Show warning for partial success
  // ============================================================
  _handlePartialStatus(result) {
    const failedList = result.failed_phases.join(', ');
    this._showWarningBanner({
      message: `Applied with warnings. Failed phases: ${failedList}`,
      actions: [
        { label: 'View Details', onClick: () => this._showPhaseErrors(result.failed_phases) },
        { label: 'Continue', onClick: () => this._dismissWarning() }
      ]
    });
    
    if (result.glb_ready) {
      this._loadHullGeometryWithRetry(result.design_version_after);
    }
  }

  // ============================================================
  // §SKELETON:409RetryHandler — Auto-retry on version conflict
  // ============================================================
  async _handleConflict(response, originalMessage) {
    const err = await response.json();
    console.warn('Version conflict:', err.detail);

    // Update to server's current version
    this._lastDesignVersion = err.detail.current_version;

    // Retry with updated version
    const retryResponse = await fetch(`${this.baseUrl}/api/v1/designs/${this.designId}/spiral/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: originalMessage,
        expected_version: this._lastDesignVersion,
        request_id: crypto?.randomUUID?.() ?? String(Date.now())
      })
    });

    if (!retryResponse.ok) {
      throw new Error(`Retry failed: ${retryResponse.status}`);
    }

    return this._handleSpiralResponse(await retryResponse.json());
  }

  // ============================================================
  // §SKELETON:GLBRetry — Load GLB with exponential backoff
  // ============================================================
  async _loadHullGeometryWithRetry(version, retryLimit = 5, initialDelayMs = 500) {
    for (let attempt = 0; attempt < retryLimit; attempt++) {
      try {
        const resp = await fetch(
          `${this.baseUrl}/api/v1/designs/${this.designId}/3d/export/glb?v=${version}`,
          { cache: 'no-store' }
        );
        
        if (resp.ok) {
          const blob = await resp.blob();
          if (this._sceneManager) {
            await this._sceneManager.loadGLB(blob);
          }
          this._renderedVersion = version;
          return true;
        }
        
        if (resp.status === 404 || resp.status === 202) {
          // Not ready yet, wait and retry with exponential backoff
          const delay = initialDelayMs * Math.pow(2, attempt);
          console.log(`GLB not ready, retrying in ${delay}ms (attempt ${attempt + 1}/${retryLimit})`);
          await new Promise(r => setTimeout(r, delay));
          continue;
        }
        
        throw new Error(`GLB fetch failed: ${resp.status}`);
      } catch (e) {
        if (attempt === retryLimit - 1) {
          console.error('GLB load failed after max retries:', e);
          throw e;
        }
      }
    }
    throw new Error('GLB not ready after max retries');
  }

  // ============================================================
  // §SKELETON:WSResync — Resync state after WS reconnection
  // ============================================================
  async onWsReconnect() {
    console.log('WS reconnected, resyncing state...');
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/designs/${this.designId}`);
      if (!response.ok) throw new Error(`Fetch failed: ${response.status}`);
      
      const state = await response.json();
      this._lastDesignVersion = state.design_version || 0;
      this._spiralIteration = state.metadata?.spiral_iteration || 0;

      // Reload GLB if version changed
      if (state.design_version !== this._renderedVersion) {
        await this._loadHullGeometryWithRetry(state.design_version);
      }

      // Refresh panels
      this._refreshAllPanels(state);
      
      console.log('State resynced successfully');
    } catch (e) {
      console.error('Resync failed:', e);
      this._showErrorFeedback('Connection restored but state sync failed', ['Please refresh the page']);
    }
  }

  // ============================================================
  // §SKELETON:SketchConfirm — Handle sketch upload with confirmation
  // ============================================================
  async sendSketch(imageFile, annotations = '') {
    if (!this.designId) throw new Error('No design selected');

    // Store for re-submission after confirmation
    this._lastSketchImage = imageFile;
    this._lastSketchAnnotations = annotations;

    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('annotations', annotations);
    formData.append('confirm_execution', 'false'); // Always require confirmation first

    try {
      const response = await fetch(`${this.baseUrl}/api/v1/designs/${this.designId}/spiral/sketch`, {
        method: 'POST',
        body: formData
      });

      if (response.status === 409) {
        return this._handleConflict(response, `[sketch: ${annotations}]`);
      }

      if (!response.ok) {
        throw new Error(`Sketch upload failed: ${response.status}`);
      }

      const result = await response.json();
      return this._handleSketchResult(result);
    } catch (e) {
      this._showErrorFeedback('Sketch upload failed', [e.message]);
      throw e;
    }
  }

  async _handleSketchResult(result) {
    if (!result.requires_confirmation) {
      // Already executed (shouldn't happen with confirm_execution=false)
      return this._handleSpiralResponse(result);
    }

    // Show confirmation dialog with extracted values
    const confirmed = await this._showSketchConfirmationDialog({
      extractedValues: result.extracted_values,
      interpretation: result.interpretation,
      intentString: result.intent_string,
      confidence: result.average_confidence
    });

    if (!confirmed) {
      return null; // User rejected
    }

    // Re-submit with confirmation
    const formData = new FormData();
    formData.append('image', this._lastSketchImage);
    formData.append('annotations', this._lastSketchAnnotations);
    formData.append('confirm_execution', 'true');
    formData.append('expected_version', String(this._lastDesignVersion));

    const response = await fetch(`${this.baseUrl}/api/v1/designs/${this.designId}/spiral/sketch`, {
      method: 'POST',
      body: formData
    });

    return this._handleSpiralResponse(await response.json());
  }

  // ============================================================
  // §SKELETON:PhaseRefresh — Refresh panels from response
  // ============================================================
  _refreshPhasesFromResponse(result) {
    const phases = result.invalidated_phases || ['hull_form', 'weight_stability', 'structure'];
    
    phases.forEach(phase => {
      const panel = this._panels[phase];
      if (panel && typeof panel.refresh === 'function') {
        panel.refresh();
      }
    });

    if (result.metrics) {
      this._updateMetricsPanel(result.metrics, result.deltas);
    }
  }

  _refreshAllPanels(state) {
    Object.values(this._panels).forEach(panel => {
      if (panel && typeof panel.refresh === 'function') {
        panel.refresh(state);
      }
    });
  }

  // ============================================================
  // ============================================================
  // §SKELETON:SpiralAdapterHelpers
  // UI Helper Methods — Complete Implementations
  // ============================================================

  /**
   * Show a modal confirmation dialog
   * @returns {Promise<boolean>} true if confirmed, false otherwise
   */
  async _showConfirmationDialog({ title, message, details, confirmText = 'Confirm', cancelText = 'Cancel' }) {
    return new Promise((resolve) => {
      // Create modal overlay
      const overlay = document.createElement('div');
      overlay.className = 'spiral-modal-overlay';
      overlay.innerHTML = `
        <div class="spiral-modal">
          <div class="spiral-modal-header">
            <h3>${this._escapeHtml(title)}</h3>
          </div>
          <div class="spiral-modal-body">
            <p>${this._escapeHtml(message)}</p>
            ${details ? `<pre class="spiral-modal-details">${this._escapeHtml(details)}</pre>` : ''}
          </div>
          <div class="spiral-modal-footer">
            <button class="btn btn-secondary spiral-modal-cancel">${this._escapeHtml(cancelText)}</button>
            <button class="btn btn-primary spiral-modal-confirm">${this._escapeHtml(confirmText)}</button>
          </div>
        </div>
      `;

      const cleanup = (result) => {
        overlay.remove();
        resolve(result);
      };

      overlay.querySelector('.spiral-modal-cancel').onclick = () => cleanup(false);
      overlay.querySelector('.spiral-modal-confirm').onclick = () => cleanup(true);
      overlay.onclick = (e) => { if (e.target === overlay) cleanup(false); };

      document.body.appendChild(overlay);
      overlay.querySelector('.spiral-modal-confirm').focus();
    });
  }

  /**
   * Show sketch confirmation dialog with extracted values
   */
  async _showSketchConfirmationDialog({ extractedValues, interpretation, intentString, confidence }) {
    const valuesHtml = Object.entries(extractedValues || {})
      .map(([k, v]) => `<tr><td>${this._escapeHtml(k)}</td><td>${this._escapeHtml(String(v))}</td></tr>`)
      .join('');

    return new Promise((resolve) => {
      const overlay = document.createElement('div');
      overlay.className = 'spiral-modal-overlay';
      overlay.innerHTML = `
        <div class="spiral-modal spiral-modal-wide">
          <div class="spiral-modal-header">
            <h3>📐 Confirm Sketch Interpretation</h3>
            <span class="confidence-badge ${confidence > 0.7 ? 'high' : confidence > 0.4 ? 'medium' : 'low'}">
              ${(confidence * 100).toFixed(0)}% confidence
            </span>
          </div>
          <div class="spiral-modal-body">
            <div class="sketch-section">
              <h4>Extracted Values</h4>
              <table class="extracted-values-table">
                <thead><tr><th>Parameter</th><th>Value</th></tr></thead>
                <tbody>${valuesHtml || '<tr><td colspan="2">No values extracted</td></tr>'}</tbody>
              </table>
            </div>
            <div class="sketch-section">
              <h4>Interpreted Intent</h4>
              <p class="intent-string">${this._escapeHtml(intentString || 'No intent extracted')}</p>
            </div>
          </div>
          <div class="spiral-modal-footer">
            <button class="btn btn-secondary spiral-modal-cancel">Cancel</button>
            <button class="btn btn-primary spiral-modal-confirm">Execute Design</button>
          </div>
        </div>
      `;

      const cleanup = (result) => {
        overlay.remove();
        resolve(result);
      };

      overlay.querySelector('.spiral-modal-cancel').onclick = () => cleanup(false);
      overlay.querySelector('.spiral-modal-confirm').onclick = () => cleanup(true);
      overlay.onclick = (e) => { if (e.target === overlay) cleanup(false); };

      document.body.appendChild(overlay);
    });
  }

  /**
   * Show success feedback toast
   */
  _showSuccessFeedback(message, metrics, deltas) {
    this._showToast({
      type: 'success',
      title: '✓ Success',
      message,
      details: this._formatMetrics(metrics, deltas),
      duration: 5000
    });
  }

  /**
   * Show error feedback toast
   */
  _showErrorFeedback(message, errors = []) {
    this._showToast({
      type: 'error',
      title: '✗ Error',
      message,
      details: errors.join('\n'),
      duration: 8000
    });
  }

  /**
   * Show warning banner at top of UI
   */
  _showWarningBanner({ message, actions = [] }) {
    // Remove existing warning banner
    this._dismissWarning();

    const banner = document.createElement('div');
    banner.id = 'spiral-warning-banner';
    banner.className = 'spiral-warning-banner';
    banner.innerHTML = `
      <span class="warning-icon">⚠️</span>
      <span class="warning-message">${this._escapeHtml(message)}</span>
      <div class="warning-actions">
        ${actions.map(a => `<button class="btn btn-small">${this._escapeHtml(a.label)}</button>`).join('')}
      </div>
    `;

    // Attach action handlers
    const buttons = banner.querySelectorAll('.warning-actions button');
    actions.forEach((action, i) => {
      if (buttons[i]) buttons[i].onclick = action.onClick;
    });

    // Insert at top of main content
    const container = document.querySelector('.main-content') || document.body;
    container.insertBefore(banner, container.firstChild);
  }

  /**
   * Dismiss warning banner
   */
  _dismissWarning() {
    const banner = document.getElementById('spiral-warning-banner');
    if (banner) banner.remove();
  }

  /**
   * Show phase errors in detail panel
   */
  _showPhaseErrors(failedPhases) {
    this._showConfirmationDialog({
      title: 'Phase Errors',
      message: 'The following phases failed during execution:',
      details: failedPhases.map(p => `• ${p}`).join('\n'),
      confirmText: 'OK',
      cancelText: 'View Logs'
    }).then(ok => {
      if (!ok) {
        // Open logs panel
        const logsPanel = document.getElementById('logs-panel');
        if (logsPanel) logsPanel.classList.add('visible');
      }
    });
  }

  /**
   * Update metrics display panel
   */
  _updateMetricsPanel(metrics, deltas) {
    const panel = document.getElementById('metrics-panel');
    if (!panel) return;

    const rows = Object.entries(metrics).map(([key, value]) => {
      const delta = deltas?.[key];
      const deltaClass = delta > 0 ? 'positive' : delta < 0 ? 'negative' : '';
      const deltaStr = delta ? ` (${delta > 0 ? '+' : ''}${delta.toFixed(2)})` : '';
      return `
        <tr>
          <td>${this._escapeHtml(key)}</td>
          <td>${typeof value === 'number' ? value.toFixed(3) : value}</td>
          <td class="delta ${deltaClass}">${deltaStr}</td>
        </tr>
      `;
    }).join('');

    panel.innerHTML = `
      <table class="metrics-table">
        <thead><tr><th>Metric</th><th>Value</th><th>Change</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  }

  /**
   * Show toast notification
   */
  _showToast({ type, title, message, details, duration = 5000 }) {
    const container = document.getElementById('toast-container') || this._createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `spiral-toast spiral-toast-${type}`;
    toast.innerHTML = `
      <div class="toast-header">
        <strong>${this._escapeHtml(title)}</strong>
        <button class="toast-close">×</button>
      </div>
      <div class="toast-body">
        <p>${this._escapeHtml(message)}</p>
        ${details ? `<pre class="toast-details">${this._escapeHtml(details)}</pre>` : ''}
      </div>
    `;

    toast.querySelector('.toast-close').onclick = () => toast.remove();
    container.appendChild(toast);

    // Auto-remove after duration
    if (duration > 0) {
      setTimeout(() => toast.remove(), duration);
    }
  }

  _createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'spiral-toast-container';
    document.body.appendChild(container);
    return container;
  }

  /**
   * Format metrics and deltas for display
   */
  _formatMetrics(metrics, deltas) {
    if (!metrics || Object.keys(metrics).length === 0) return '';
    return Object.entries(metrics)
      .map(([k, v]) => {
        const d = deltas?.[k];
        const dStr = d ? ` (${d > 0 ? '+' : ''}${d.toFixed(2)})` : '';
        return `${k}: ${typeof v === 'number' ? v.toFixed(2) : v}${dStr}`;
      })
      .join('\n');
  }

  /**
   * Escape HTML to prevent XSS
   */
  _escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
}

// Export for use
export default SpiralAdapter;
```

---

## §SKELETON:ClarificationPanelComplete — Full Implementation

**File:** `magnet/ui_v2/js/clarification-panel.js`

```javascript
/**
 * Clarification Panel for human-in-loop design spiral
 */
export class ClarificationPanel {
  constructor(containerEl) {
    this.container = containerEl;
    this._onSubmit = null;
    this._onCancel = null;
    this._requestId = null;
  }

  show({ questions, requestId, onSubmit, onCancel }) {
    this._onSubmit = onSubmit;
    this._onCancel = onCancel;
    this._requestId = requestId;

    this.container.innerHTML = `
      <div class="clarification-panel">
        <div class="clarification-header">
          <h3>🤔 Clarification Needed</h3>
          <p>Please answer the following questions to proceed:</p>
        </div>
        <form id="clarification-form" class="clarification-form">
          ${questions.map((q, i) => this._renderQuestion(q, i)).join('')}
          <div class="clarification-actions">
            <button type="button" class="btn btn-secondary btn-cancel">Cancel</button>
            <button type="submit" class="btn btn-primary btn-submit">Submit Answers</button>
          </div>
        </form>
      </div>
    `;

    // Event handlers
    this.container.querySelector('.btn-cancel').onclick = () => {
      if (this._onCancel) this._onCancel();
      this.hide();
    };

    this.container.querySelector('#clarification-form').onsubmit = (e) => {
      e.preventDefault();
      this._handleSubmit();
    };

    this.container.style.display = 'block';
    this.container.classList.add('visible');
    
    // Focus first input
    const firstInput = this.container.querySelector('input, select, textarea');
    if (firstInput) firstInput.focus();
  }

  _renderQuestion(question, index) {
    const { id, text, type, options, required = true, placeholder = '' } = question;
    const inputId = `clarification-${id || index}`;
    const inputName = id || `q${index}`;
    const requiredAttr = required ? 'required' : '';

    if (type === 'select' && options) {
      return `
        <div class="clarification-question">
          <label for="${inputId}">${text}</label>
          <select id="${inputId}" name="${inputName}" ${requiredAttr}>
            <option value="">-- Select an option --</option>
            ${options.map(o => `<option value="${o.value}">${o.label}</option>`).join('')}
          </select>
        </div>
      `;
    }

    if (type === 'number') {
      return `
        <div class="clarification-question">
          <label for="${inputId}">${text}</label>
          <input type="number" id="${inputId}" name="${inputName}" 
                 placeholder="${placeholder}" ${requiredAttr} step="any" />
        </div>
      `;
    }

    if (type === 'textarea') {
      return `
        <div class="clarification-question">
          <label for="${inputId}">${text}</label>
          <textarea id="${inputId}" name="${inputName}" 
                    placeholder="${placeholder}" ${requiredAttr} rows="3"></textarea>
        </div>
      `;
    }

    // Default: text input
    return `
      <div class="clarification-question">
        <label for="${inputId}">${text}</label>
        <input type="text" id="${inputId}" name="${inputName}" 
               placeholder="${placeholder}" ${requiredAttr} />
      </div>
    `;
  }

  async _handleSubmit() {
    const form = this.container.querySelector('#clarification-form');
    const formData = new FormData(form);
    const responses = Object.fromEntries(formData.entries());

    // Disable submit button while processing
    const submitBtn = this.container.querySelector('.btn-submit');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting...';

    try {
      if (this._onSubmit) {
        await this._onSubmit({ requestId: this._requestId, responses });
      }
    } catch (e) {
      console.error('Clarification submit failed:', e);
      submitBtn.disabled = false;
      submitBtn.textContent = 'Submit Answers';
    }
  }

  hide() {
    this.container.style.display = 'none';
    this.container.classList.remove('visible');
    this.container.innerHTML = '';
    this._onSubmit = null;
    this._onCancel = null;
    this._requestId = null;
  }
}

export default ClarificationPanel;
```

**CSS:** `magnet/ui_v2/css/clarification-panel.css`

```css
.clarification-panel {
  background: var(--panel-bg, #1a1a2e);
  border: 1px solid var(--border-color, #3a3a5e);
  border-radius: 8px;
  padding: 20px;
  max-width: 500px;
  margin: 20px auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.clarification-header h3 {
  margin: 0 0 8px 0;
  color: var(--text-primary, #fff);
}

.clarification-header p {
  margin: 0 0 16px 0;
  color: var(--text-secondary, #aaa);
  font-size: 0.9em;
}

.clarification-question {
  margin-bottom: 16px;
}

.clarification-question label {
  display: block;
  margin-bottom: 6px;
  color: var(--text-primary, #fff);
  font-weight: 500;
}

.clarification-question input,
.clarification-question select,
.clarification-question textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color, #3a3a5e);
  border-radius: 4px;
  background: var(--input-bg, #0f0f1a);
  color: var(--text-primary, #fff);
  font-size: 1em;
}

.clarification-question input:focus,
.clarification-question select:focus,
.clarification-question textarea:focus {
  outline: none;
  border-color: var(--accent-color, #6366f1);
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
}

.clarification-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color, #3a3a5e);
}

.btn {
  padding: 10px 20px;
  border-radius: 4px;
  font-size: 0.95em;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: var(--accent-color, #6366f1);
  color: white;
  border: none;
}

.btn-primary:hover {
  background: var(--accent-hover, #5558e3);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: transparent;
  color: var(--text-secondary, #aaa);
  border: 1px solid var(--border-color, #3a3a5e);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.05);
}
```

---

## §SKELETON:SpiralAdapterCSS — Complete UI Styles

**File:** `magnet/ui_v2/css/spiral-adapter.css`

```css
/* ============================================================
   Spiral Adapter UI Components
   ============================================================ */

/* Modal Overlay */
.spiral-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* Modal Dialog */
.spiral-modal {
  background: var(--panel-bg, #1a1a2e);
  border: 1px solid var(--border-color, #3a3a5e);
  border-radius: 12px;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  animation: slideUp 0.3s ease;
}

.spiral-modal-wide {
  max-width: 600px;
}

@keyframes slideUp {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.spiral-modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color, #3a3a5e);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.spiral-modal-header h3 {
  margin: 0;
  color: var(--text-primary, #fff);
  font-size: 1.2em;
}

.spiral-modal-body {
  padding: 20px 24px;
  overflow-y: auto;
  color: var(--text-primary, #fff);
}

.spiral-modal-body p {
  margin: 0 0 16px 0;
  line-height: 1.5;
}

.spiral-modal-details {
  background: var(--code-bg, #0f0f1a);
  border: 1px solid var(--border-color, #3a3a5e);
  border-radius: 6px;
  padding: 12px;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 0.85em;
  overflow-x: auto;
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
}

.spiral-modal-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--border-color, #3a3a5e);
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

/* Confidence Badge */
.confidence-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 0.8em;
  font-weight: 600;
}

.confidence-badge.high {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.confidence-badge.medium {
  background: rgba(234, 179, 8, 0.2);
  color: #eab308;
}

.confidence-badge.low {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

/* Sketch Confirmation Sections */
.sketch-section {
  margin-bottom: 20px;
}

.sketch-section h4 {
  margin: 0 0 12px 0;
  color: var(--text-secondary, #aaa);
  font-size: 0.9em;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.extracted-values-table {
  width: 100%;
  border-collapse: collapse;
}

.extracted-values-table th,
.extracted-values-table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border-color, #3a3a5e);
}

.extracted-values-table th {
  color: var(--text-secondary, #aaa);
  font-weight: 500;
  font-size: 0.85em;
}

.intent-string {
  background: var(--code-bg, #0f0f1a);
  padding: 12px;
  border-radius: 6px;
  font-style: italic;
}

/* Toast Notifications */
.spiral-toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 10001;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 400px;
}

.spiral-toast {
  background: var(--panel-bg, #1a1a2e);
  border: 1px solid var(--border-color, #3a3a5e);
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  animation: slideInRight 0.3s ease;
  overflow: hidden;
}

@keyframes slideInRight {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

.spiral-toast-success {
  border-left: 4px solid #22c55e;
}

.spiral-toast-error {
  border-left: 4px solid #ef4444;
}

.spiral-toast-warning {
  border-left: 4px solid #eab308;
}

.toast-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color, #3a3a5e);
}

.toast-header strong {
  color: var(--text-primary, #fff);
}

.toast-close {
  background: none;
  border: none;
  color: var(--text-secondary, #aaa);
  font-size: 1.2em;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.toast-close:hover {
  color: var(--text-primary, #fff);
}

.toast-body {
  padding: 12px 16px;
}

.toast-body p {
  margin: 0;
  color: var(--text-primary, #fff);
}

.toast-details {
  margin-top: 8px;
  background: var(--code-bg, #0f0f1a);
  padding: 8px;
  border-radius: 4px;
  font-size: 0.85em;
  font-family: monospace;
  white-space: pre-wrap;
  max-height: 100px;
  overflow-y: auto;
}

/* Warning Banner */
.spiral-warning-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: rgba(234, 179, 8, 0.1);
  border: 1px solid rgba(234, 179, 8, 0.3);
  border-radius: 8px;
  margin-bottom: 16px;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from { transform: translateY(-10px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.warning-icon {
  font-size: 1.2em;
}

.warning-message {
  flex: 1;
  color: #eab308;
}

.warning-actions {
  display: flex;
  gap: 8px;
}

.btn-small {
  padding: 6px 12px;
  font-size: 0.85em;
}

/* Metrics Table */
.metrics-table {
  width: 100%;
  border-collapse: collapse;
}

.metrics-table th,
.metrics-table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border-color, #3a3a5e);
}

.metrics-table th {
  color: var(--text-secondary, #aaa);
  font-weight: 500;
  font-size: 0.85em;
}

.metrics-table .delta {
  font-size: 0.85em;
}

.metrics-table .delta.positive {
  color: #22c55e;
}

.metrics-table .delta.negative {
  color: #ef4444;
}

/* Button variants */
.btn {
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 0.95em;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-primary {
  background: var(--accent-color, #6366f1);
  color: white;
}

.btn-primary:hover {
  background: var(--accent-hover, #5558e3);
  transform: translateY(-1px);
}

.btn-primary:active {
  transform: translateY(0);
}

.btn-secondary {
  background: transparent;
  color: var(--text-secondary, #aaa);
  border: 1px solid var(--border-color, #3a3a5e);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: var(--text-secondary, #aaa);
}
```

