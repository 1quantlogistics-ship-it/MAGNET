# UI v2 ↔ Backend Adaptation & Implementation Guide

<!-- AGENT_CONTEXT
Purpose: Integration guide for UI v2 with backend single-authority architecture and phase mapping
Authoritative: Yes
Keywords: ui, ui_v2, backend, integration, adapter, phases, mapping, websocket
Depends_On: 0-architecture/system/SYSTEM_ARCHITECTURE.md
Used_By: developers, ui_team
Status: current
Last_Verified: 2026-01-15
-->

## Single-Authority Architecture

### Purpose
This guide defines the complete adaptation needed for **MAGNET Studio UI v2** (`magnet/ui_v2/`) to integrate with the MAGNET backend and kernel **without parallel systems**.

The goal is: **UI is a thin client** over the backend’s canonical flow:

\[
\text{UI} \rightarrow \text{API/WS} \rightarrow \text{DesignStore} \rightarrow \text{StateManager} \rightarrow \text{Conductor/PhaseMachine} \rightarrow \text{ValidatorTopology} \rightarrow \text{outputs} \rightarrow \text{UI}
\]

---

## Architecture: Authorities and Non-Goals

### Single authorities (must not be duplicated)
- **Design persistence/versioning**: `DesignStore` (the “lake”)
- **Design state mutation rules**: `StateManager` (transactions for refinable paths)
- **Phase orchestration**: `PhaseMachine` + `Conductor`
- **Validator scheduling/dependencies**: `ValidatorTopology` + `PipelineExecutor`
- **Truth of validator membership per phase**: validator definitions (`builtin.py`) + topology by `ValidatorDefinition.phase`

### UI responsibilities (allowed)
- Rendering (3D + panels)
- Requesting actions (spiral chat, phase run, validation, export)
- Displaying state + provenance + findings

### UI responsibilities (not allowed)
- Running physics/validation logic client-side
- Creating a second phase taxonomy inconsistent with kernel phases
- Creating a separate persistence scheme
- Treating “validator ids” as phases (or vice versa)

---

## Canonical Naming and Mapping

### Kernel canonical phases (source: `magnet/kernel/registry.py`)
Canonical phases include (non-exhaustive): `mission`, `hull`, `structure`, `propulsion`, `weight`, `stability`, `arrangement`, `compliance`, `production`, `cost`, `optimization`, `reporting`.

### UI labels vs backend phase runner
UI v2 currently shows steps like “Hydrostatics” and “Resistance”. These are **validators / sub-results**, not canonical phases.

**Rule**:
- UI “tabs” may exist for UX, but **`POST /phases/{phase}/run` must always receive a canonical kernel phase**.
- Sub-steps (“Hydrostatics”, “Resistance”) should be:
  - **views** of outputs, and/or
  - **phase validate** operations (not phase run with fake phase names), and/or
  - single-validator runs (optional advanced feature; see below).

### Critical invariant: stability must be reachable
UI must be able to trigger kernel `stability` (run/validate) without mapping through `weight` or any combined “weight_stability” legacy name.
If stability is presented as a “validator” in the UI (IMO criteria), the adapter must route that click to the kernel `stability` phase.

### Mapping strategy
Implement a single mapping table used consistently by:
- UI “phaseChange”
- UI “validatorClick” (if it triggers phase validate)
- WS message normalization

**Recommended mapping** (example):
- UI `mission` → kernel `mission`
- UI `hull` → kernel `hull`
- UI `hydrostatics` → kernel `hull` (view into `physics/hydrostatics` outputs)
- UI `resistance` → kernel `hull` (view into `physics/resistance` outputs)
- UI `structure` → kernel `structure`
- UI `propulsion` → kernel `propulsion`
- UI `weight` → kernel `weight`
- UI `stability` → kernel `stability`
- UI `arrangement` → kernel `arrangement`

Implementation locations:
- UI: `magnet/ui_v2/js/backend-adapter.js` (`PhaseIdMapper`)
- Backend: `magnet/deployment/api.py` (keep `_map_phase_id` as a compatibility layer for legacy callers, but prefer UI sending canonical)

### Legacy compatibility (backend only)
Legacy phase strings may exist in older clients/tests (e.g. `hull_form`, `weight_stability`). If supported, they must be mapped server-side to canonical kernel phases, and responses/WS payloads must expose the canonical identifier to prevent UI drift.

---

## API Contract (HTTP)

### 1) UI bootstrap / metadata
- **GET** `/api/v1/meta`
  - Returns backend version, and useful endpoint pointers.
  - Used to show “Backend vX detected”.

### 2) Design lifecycle (DesignStore authority)
- **GET** `/api/v1/designs`
  - Returns list of designs (most recent first).
  - In “context-less / unit-test” mode, may return empty list.
- **POST** `/api/v1/designs`
  - Creates a new blank persisted design.
  - Returns `design_id` and `design_version`.
- **GET** `/api/v1/designs/{design_id}`
  - Returns:
    - design metadata
    - phase states (if available)
    - **canonical `state` flat map** (required)
    - optional `provenance` map
- **PATCH** `/api/v1/designs/{design_id}`
  - Applies a single state update (`{path, value, design_version_before}` pattern if used)
  - Persists to DesignStore and increments design version
  - Must return `design_version_after`

### 3) Spiral (LLM intent → program → apply) (DesignStore authority)
- **POST** `/api/v1/designs/{id}/spiral/chat`
  - The only place where freeform user prompting should go.
  - Must return clear outcomes:
    - applied vs not applied
    - `design_version_after` when applied
    - clarification payload when blocked

### 4) Phase execution (kernel authority)
- **POST** `/api/v1/designs/{id}/phases/{phase}/run`
  - `phase` is kernel canonical phase id (or mapped server-side for compatibility).
  - Must wire pipeline executor correctly (topology must be built with validators added before build).
  - Must update phase status + return a structured result.

### 5) Phase validation (topology + contracts authority)
- **POST** `/api/v1/designs/{id}/phases/{phase}/validate`
  - Validates phase outputs and returns:
    - contract satisfied
    - findings (validator findings)
    - suggested fixes (optional)
    - gate/grade envelope (see below)

### 6) Geometry export
- **GET** `/api/v1/designs/{id}/3d/export/glb?...`
  - Used for rendering and export
  - UI should cache-bust using `design_version` query param

---

## API Contract: Error/Status Envelopes (no parallel semantics)

### Gate vs grade model
The backend should distinguish:
- **Missing inputs** (client needs to supply prerequisites) → 400
- **Gate failed** (required validator blocks progression) → 422
- **Grade warning** (severe advisory; human decision required but can proceed) → 200 with `human_decision_required=true`

The UI should:
- show missing inputs as actionable guidance
- show gate failure as “blocked”
- show grade warning as “needs approval”

---

## WebSocket Contract (events are kernel-driven)

### WS endpoint
- `/ws/{design_id}` (same-origin preferred)

### Required message types (examples)
- `phase_started`, `phase_completed`, `phase_failed`
- `validation_started`, `validation_completed`
- `snapshot_created` (geometry refresh signal)
- `design_updated` (optional)

### Naming rule
Phase identifiers in WS payloads must be either:
- canonical kernel phase ids, or
- consistently mappable by the same PhaseIdMapper used by HTTP paths.

Avoid: WS speaking “hull_form” while HTTP speaks “hull” unless the payload also includes the canonical kernel identifier.

**Recommendation**: include both in payload:
- `phase` (requested route param, for debugging)
- `kernel_phase` (canonical, used by UI)

---

## UI Command Routing Rules (prevent accidental LLM calls)

### Rule 1: Operational commands must never hit LLM
Commands like:
- “show hydrostatics”
- “run stability check”
- “export report”
- “reload”
- “undo”
- “restore version N”
- “clear geometry cache”

…must be explicitly intercepted in `backend-adapter.js` and routed to deterministic endpoints.

#### Same rule applies to UI buttons
Anything that is a “button” (not natural language intent) must never flow through spiral chat.

### Rule 2: Only natural language “design intent” goes to spiral chat
All other strings should either:
- map to an operational action, or
- display “unknown command” help text.

### Implementation point
`magnet/ui_v2/js/backend-adapter.js` inside `MagnetStudio.on('command', ...)`

---

## UI Panels: State + Provenance + Findings (single data model)

### Canonical state shape
`GET /api/v1/designs/{id}` must include:
- `state`: `{ "hull.lwl": 12.0, "weight.lightship_weight_mt": 35.8, ... }`
- optionally `provenance`: `{ "hull.lwl": { explain_ref, validator_id, design_version, ... }, ... }`

UI panel renderer should depend on `design.state` only (flat map), not nested ad-hoc structures.

#### Panel config ergonomics (allowed)
To keep configs readable, panel configs may specify a `sourcePrefix` (e.g. `hull.`) and then use **relative keys** (e.g. `lwl`, `beam`) which are resolved against the flat map at render-time.

This preserves the single-authority state model while avoiding repetitive fully-qualified keys in every field.

### Findings and suggested fixes
Phase validation responses should include:
- `findings`: list of items with severity/message/path/validator_id
- `suggested_fixes`: optional structured actions

UI should render these as:
- Issues list in the phase panel
- “Apply fix” buttons that call PATCH/actions endpoints (single authority)

---

## Persistence & Versioning (DesignStore is the lake)

### Rule
Any mutation that changes the design must:
- update `StateManager`
- persist to `DesignStore.save(...)`
- return `design_version_after`

UI must:
- cache-bust GLB loads with `?v=design_version_after`
- prevent stale writes (use expected_version where supported)
- display the current version in terminal/status bar

---

## Offline / No-LLM mode (optional; keep architecture clean)

If the environment cannot reach the LLM provider:
- Spiral should return a clear “LLM unavailable” response **or**
- Use a deterministic fallback generator (if present) that still produces valid programs.

**Constraint**: fallback must still flow through the same pipeline:
`spiral/chat` → program → apply → persist → emit snapshot_created

No “client-side demo mode” that bypasses DesignStore should be used unless explicitly requested (`?demo=true`).

---

## Implementation Workplan (Complete, not just minimum)

### A) Fix canonical phase mapping end-to-end
- Update UI `PhaseIdMapper` to map UI tabs to canonical kernel phases.
- Remove/avoid legacy phase ids like `mission_requirements`, `structural_scantlings`, `general_arrangement` unless the backend explicitly supports them.
- Ensure backend `_map_phase_id` remains as a compatibility layer.

### B) Define explicit operational command table in UI
Implement a command router table:
- command → handler → endpoint(s) → output formatting

Required handlers:
- `new blank` (POST /designs)
- `show hydrostatics` (POST /phases/hull/run, then read hull outputs)
- `run stability check` (POST /phases/stability/run or validate)
- `export report` (POST /reports)
- `undo` (POST /undo)
- `restore version N` (POST /versions/{N}/restore)
- `reload` (reload geometry)
- `clear geometry cache` (DELETE /3d/cache then reload)

### C) Unify “validatorClick” semantics
The UI has two distinct concepts:
- **Phases** (kernel phases): `mission`, `hull`, `weight`, `stability`, …
- **Validators** (checks/rules): IMO, class rules, etc.

Do not conflate these.

Implementation options (choose one and keep it consistent):
- **Option A (phase-scoped)**: clicking a validator runs/validates a corresponding **kernel phase** (`stability` or `compliance`) regardless of current phase tab.
- **Option B (validator-scoped)**: add `POST /api/v1/designs/{id}/validators/{validator_id}/run` and wire clicks to individual validators (advanced).

This project should prefer Option A unless validator-level runs are required.

### D) Normalize backend responses for UI consumption
Ensure consistent presence of:
- `design_version_after`
- `state` flat map
- structured findings
- stable error envelope across endpoints

### E) WebSocket normalization
Ensure WS payloads emit canonical phases or provide robust mapping in adapter.

### F) Geometry refresh lifecycle
After any mutation that changes geometry:
- backend emits `snapshot_created`
- UI calls `_loadHullGeometry()` with cache bust

### G) Tests (must cover the real flow)
Add/maintain:
- UI integration tests (API-level) that run:
  - create design → spiral chat apply → run hull phase → export GLB
- phase runner tests that ensure topology includes validators (add_all_validators before build)
- regression: “show hydrostatics” must not call spiral

---

## Acceptance Criteria (Definition of Done)

### UI behavior
- Clicking “Hydrostatics” or running `show hydrostatics`:
  - never invokes spiral/LLM
  - runs the appropriate kernel phase
  - prints a hydro summary in terminal and updates the panel

### Backend behavior
- `POST /phases/{phase}/run` executes validators (topology built correctly)
- Contracts for the phase pass when outputs are present
- `GET /designs/{id}` returns `state` flat map

### No parallel systems
- No client-side “phase engine”
- No second persistence path
- No alternate phase taxonomy used for execution

---

## File/Module Index

### UI
- `magnet/ui_v2/index.html`: UI shell + event emission
- `magnet/ui_v2/js/backend-adapter.js`: UI↔API/WS adapter (command routing + phase mapping)
- `magnet/ui_v2/js/spiral-adapter.js`: spiral chat/sketch client (LLM path only)
- `magnet/ui_v2/js/scene-manager.js`: GLB loading + scene controls
- `magnet/ui_v2/js/panel-renderer.js`: panel rendering from `design.state`

### Backend
- `magnet/deployment/api.py`: FastAPI app, endpoints, UI serving, phase runner wiring
- `magnet/deployment/design_store.py`: persistence + versioning
- `magnet/core/state_manager.py`: transactional mutation rules
- `magnet/kernel/conductor.py`: phase execution
- `magnet/validators/topology.py`: validator membership by phase + dependency graph

