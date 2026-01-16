# MAGNET Golden Path Technical Specification

## Executive Summary

This document is a **codebase audit** of MAGNET’s current “golden path” — the end-to-end flow from **user intent** (UI v2) to **validated, exportable hull geometry** (GLB) — with explicit mapping to the repository’s **intended architecture** as defined in `Pelorus Plugin/Run1 /SPEC.md` and `Pelorus Plugin/Run1 /CONSTRAINTS.md` (authoritative YAML mirror at `.control-plane/docs/constraints.yaml`).

**Repo note (path mismatch vs prompt):** This audit was performed in `/Users/bengibson/MAGNETV1` (not `/Users/bengibson/MAGNET-Pelorus`). In this repo, the requested spec set (`SPEC.md`, `ROADMAP.md`, `CONSTRAINTS.md`) is located under `Pelorus Plugin/Run1 /`, while `.control-plane/docs/` currently contains `constraints.yaml` only.

Key findings:
- **Two parallel control planes exist today**: the **Spiral endpoints** (`/api/v1/designs/{id}/spiral/*`) are the default UI v2 authority, while the **legacy Intent→Action endpoints** (`/intent/preview`, `/actions`) are **feature-flagged off by default** (`MAGNET_LEGACY_INTENT_PROTOCOL_ENABLED=false`) (`magnet/deployment/api.py:L999-L1006`, `magnet/deployment/api.py:L1896-L1922`, `magnet/deployment/api.py:L1647-L1670`).
- The **GLB export path** is well-formed: it returns `X-Design-Id`, `X-Design-Version`, `X-Geometry-Mode`, and `Cache-Control: no-store` (`magnet/webgl/api_endpoints.py:L478-L578`) and UI v2 actively checks these headers (`magnet/ui_v2/js/scene-manager.js:L96-L134`).
- The **hull capping implementation lives in the WebGL tessellator**, not in the compiler: `_triangulate_end_cap(...)` builds bow/stern caps (`magnet/webgl/geometry_pipeline.py:L475-L592`, `magnet/webgl/geometry_pipeline.py:L933-L1047`). This logic is the primary place to diagnose the “wings” / “missing stern” artifact.
- **Silent transforms exist**: design-language polygon sections are **resampled to 32 points by default** (clamped 10–64) in `compile_section()` (`magnet/kernel/stdlib/section_compiler.py:L157-L205`). This violates the “NO_SILENT_TRANSFORMS” spirit and is explicitly called out as a known issue.
- **Enumeration leakage is present in kernel + physics** (hard violation): `HullFamily` priors in kernel (`magnet/kernel/priors/hull_families.py:L21-L27`, `magnet/kernel/priors/hull_families.py:L120-L207`) and family-based feature defaults in synthesis (`magnet/kernel/synthesis.py:L1147-L1262`) are decision logic that encodes “vessel family → parameter defaults”.
- **Coordinate conventions are inconsistent across schema vs code**: `geometry_schema.json` states `x: 0=bow, LOA=stern` (`magnet/agents/geometry_schema.json:L76-L79`), but section compilation and WebGL treat **x=0 at stern/AP and x=LOA at bow** (`magnet/kernel/stdlib/section_compiler.py:L62-L65`, `magnet/webgl/interfaces.py:L187-L195`). This mismatch is a reliability hazard for ordering, capping, and any “station” reasoning.

## 0. North Star Alignment Check

### 0.1 The Equation

North Star: \( \text{NOVELTY} = \text{continuous parameters} \times \text{compositional operators} \times \text{physics validation} \).

**Observed alignment (partial):**
- **Compositional operators exist** via design-language primitives (`geometry.*`) and the Spiral execution path (`magnet/deployment/spiral_endpoints.py:L360-L823`).
- **Physics validation exists** but currently mixes “gate vs grades” with **type-based** physics heuristics (see enumeration leakage in `magnet/physics/hydrostatics.py:L317-L530`).
- **Novelty without new code** is the stated direction in the Spiral + design-language compiler, but kernel synthesis currently contains **family priors and style defaults** (violating the “no enumeration/presets” North Star).

### 0.2 Enumeration Audit (Summary)

**Summary:** Enumeration leakage is material and widespread. The worst offenders are:
- **ENUM-KERNEL:** `magnet/kernel/priors/hull_families.py`, `magnet/kernel/synthesis.py`, `magnet/kernel/conductor.py` (family selection + priors + default feature selection).
- **ENUM-PHYSICS:** `magnet/physics/hydrostatics.py` and `magnet/physics/validators.py` (type maps and conditionals).
- **ENUM-LEGACY/TOOLS:** `magnet/hull_gen/enums.py` and mappings around it (legacy generator vocabulary).
- **ENUM-PROMPT (soft):** UI v2 and agent prompts contain vessel-type language; even when framed as “geometric, not a type”, it is still a form of enumeration leakage.

Full inventory is in **Section 6**.

### 0.3 Gate vs Grades

Intended: **Hydrostatics is the only gate**; everything else is a grade (warn/advise) unless explicitly configured as REQUIRED by taxonomy (`Pelorus Plugin/Run1 /SPEC.md:L20-L24`, `Pelorus Plugin/Run1 /CONSTRAINTS.md:L111-L120`).

**Observed:**
- Phase validation endpoint uses pipeline executor + contract check + gate aggregator (`magnet/deployment/api.py:L2074-L2148`).
- Hydrostatics implementation currently uses **type-based heuristics** (e.g., `"deep_v"`, `"catamaran"`) that bake in categorical assumptions (`magnet/physics/hydrostatics.py:L317-L530`).

## 1. Intended Architecture (per SPEC.md)

### 1.1 Design Spiral Model

From `Pelorus Plugin/Run1 /SPEC.md`:
- Human intent → agent proposal (optional) → kernel validation/execution → transactional state update → derived regeneration (geometry/physics) (`Pelorus Plugin/Run1 /SPEC.md:L29-L36`).

### 1.2 Authority Boundaries

From `Pelorus Plugin/Run1 /SPEC.md`:
- **Agents propose; kernel decides**. Agents must not directly mutate canonical state (`Pelorus Plugin/Run1 /SPEC.md:L47-L60`).
- Kernel must be deterministic computation + validation and must not embed intent recognition or presets (`Pelorus Plugin/Run1 /SPEC.md:L20-L23`, `Pelorus Plugin/Run1 /SPEC.md:L67-L69`).

### 1.3 Intent→Action Protocol

Specified as the firewall: ActionPlan → Validator → Executor → transactional commit, with stale-plan and locks enforced (`Pelorus Plugin/Run1 /SPEC.md:L194-L213`, `docs/INTENT_ACTION_PROTOCOL.md:L25-L266`).

### 1.4 Gate vs Grades

Hydrostatics is REQUIRED gate for hull validity; other validators are grades (unless taxonomy marks REQUIRED); NOT_IMPLEMENTED never blocks (`Pelorus Plugin/Run1 /SPEC.md:L326-L340`).

## 2. Current Implementation Analysis

### 2.1 Entry Points

**Backend (FastAPI):** `magnet/deployment/api.py`
- UI v2 hosting at `/ui/v2/` (and `/` redirects) (`magnet/deployment/api.py:L3265-L3318`).
- WebSocket endpoint at `/ws/{design_id}` (`magnet/deployment/api.py:L2535-L2549`), backed by `magnet/deployment/websocket.py`.
- Spiral router mounted (`magnet/deployment/api.py:L1136-L1156`).
- Geometry router mounted (`magnet/deployment/api.py:L1038-L1061`).

**UI v2:** `magnet/ui_v2/`
- Uses same-origin by default and connects to `ws(s)://.../ws/{design_id}` (`magnet/ui_v2/js/backend-adapter.js:L69-L105`, `magnet/ui_v2/js/backend-adapter.js:L141-L158`).
- Submits user commands via Spiral chat endpoint (`magnet/ui_v2/js/backend-adapter.js:L569-L589`, `magnet/ui_v2/js/spiral-adapter.js:L154-L187`).
- Loads GLB from `/api/v1/designs/{design_id}/3d/export/glb` and verifies response headers (`magnet/ui_v2/js/backend-adapter.js:L870-L896`, `magnet/ui_v2/js/scene-manager.js:L96-L134`).

### 2.2 Component Map (Current)

| Component | Location | Status | Constraint Compliance | Notes |
|----------|----------|--------|-----------------------|------|
| Backend API (FastAPI) | `magnet/deployment/api.py` | active | mixed | Hosts UI v2; mounts spiral + webgl routers |
| WS manager | `magnet/deployment/websocket.py` | active | ✅ | Typed messages + queue/broadcast |
| Spiral endpoints | `magnet/deployment/spiral_endpoints.py` | active (default) | mixed | Implements preview/apply semantics internally |
| Design store (persistence) | `magnet/deployment/design_store.py` | active | ✅ | JSON per design, atomic replace |
| Legacy Intent preview/apply | `magnet/deployment/api.py` | present but disabled by default | ✅ (when disabled) | feature-flagged routes; still present code |
| Program executor (design language) | `magnet/kernel/program_executor.py` | active | mixed | Bypasses ActionPlanValidator; uses DSL parser/compiler |
| Design-language compiler | `magnet/kernel/stdlib/compiler.py` | active | mixed | Enforces point conventions and compiles resources |
| Section compiler | `magnet/kernel/stdlib/section_compiler.py` | active | ❌ (silent transform) | Auto-resamples to 32 points unless specified |
| Geometry service | `magnet/webgl/geometry_service.py` | active | mostly ✅ | Fail-closed unless allow_visual_only |
| Geometry pipeline (tessellation) | `magnet/webgl/geometry_pipeline.py` | active | mixed | End caps implemented here; capping bug likely here |
| GLB export | `magnet/webgl/api_endpoints.py` | active | ✅ | Required headers + no-store |
| Kernel synthesis | `magnet/kernel/synthesis.py` | active | ❌ | Family priors + style defaults (ENUM-KERNEL) |
| Hull family priors | `magnet/kernel/priors/hull_families.py` | active | ❌ | Preset priors (ENUM-KERNEL) |
| Physics (hydrostatics) | `magnet/physics/hydrostatics.py` | active | ❌ | Type branches (ENUM-PHYSICS) |

### 2.3 Data Flow Diagram (Narrative)

**Default UI v2 flow today (Spiral authority path):**
1. UI v2 loads from `/ui/v2/` (`magnet/deployment/api.py:L3265-L3318`).
2. UI creates a design via `POST /api/v1/designs` (`magnet/deployment/api.py:L1399-L1475`), persisted in `DesignStore` (`magnet/deployment/design_store.py:L40-L90`).
3. UI connects WebSocket to `/ws/{design_id}` (`magnet/deployment/api.py:L2535-L2549`) and listens for `design_updated`, `snapshot_created`, etc. (`magnet/deployment/websocket.py:L26-L59`).
4. User submits a command → UI calls `POST /api/v1/designs/{design_id}/spiral/chat` (`magnet/ui_v2/js/spiral-adapter.js:L154-L187`).
5. Spiral endpoint produces or accepts a DesignProgram and executes it via `execute_program(...)` (`magnet/deployment/spiral_endpoints.py:L605-L823`, `magnet/kernel/program_executor.py:L58-L210`).
6. State changes are written via `StateManager.set(...)` and committed via `StateManager.commit()` (`magnet/kernel/program_executor.py:L166-L209`, `magnet/core/state_manager.py:L846-L934`), then persisted via `DesignStore.save(...)` (`magnet/deployment/spiral_endpoints.py:L748-L764`, `magnet/deployment/design_store.py:L64-L75`).
7. UI reloads geometry via `GET /api/v1/designs/{design_id}/3d/export/glb` and validates headers (`magnet/webgl/api_endpoints.py:L478-L578`, `magnet/ui_v2/js/scene-manager.js:L96-L134`).

### 2.4 State Mutation Points (Observed)

| Mutation Site | Code Path | What Mutates | Notes |
|---|---|---|---|
| Spiral chat commit | `spiral_chat` → `execute_program` | `resources.*`, `hull.*`, etc | bypasses ActionPlanValidator; uses DSL validation instead |
| Program executor commit | `execute_program` | `StateManager.set(...)` + `commit()` | commit increments `design_version` (`magnet/core/state_manager.py:L906-L934`) |
| Phase machine invalidation | `PATCH /designs/{id}` | phase invalidation | uses PhaseMachine.invalidate_dependents (`magnet/deployment/api.py:L1589-L1598`) |
| Legacy ActionPlan apply | `POST /designs/{id}/actions` | refinables only | feature-flagged off by default (`magnet/deployment/api.py:L1668-L1670`) |

## 3. Blocking Issues

### 3.1 Hull Capping Bug

#### 3.1.1 Where capping happens (actual code)

**Capping is not in the compiler**; it is in the WebGL tessellator:
- End caps are added after generating port/starboard surfaces (`magnet/webgl/geometry_pipeline.py:L475-L592`).
- The end-cap algorithm is `_triangulate_end_cap(...)` (`magnet/webgl/geometry_pipeline.py:L933-L1047`).

#### 3.1.2 The current behavior (mechanism)

In monohull mode, tessellation:
- builds **port** and **starboard** vertex grids (mirroring y) (`magnet/webgl/geometry_pipeline.py:L422-L474`);
- triangulates both sides (`magnet/webgl/geometry_pipeline.py:L468-L473`);
- then creates:
  - **“stern cap”** at the first section (`reverse_winding=False`) and
  - **“bow cap”** at the last section (`reverse_winding=True`) (`magnet/webgl/geometry_pipeline.py:L475-L483`).

In `_triangulate_end_cap(...)`, the cap is built as **two strips** that triangulate toward **a constructed centerline curve** (y=0) (`magnet/webgl/geometry_pipeline.py:L973-L1047`).

#### 3.1.3 Why “wings” can appear at the bow (root-cause mechanism)

**What the code does:** The bow cap is a surface in the plane \(x = \text{constant}\) at the final section, spanning from the section’s sheer point(s) down to the keel, triangulated toward centerline (`magnet/webgl/geometry_pipeline.py:L933-L1047`).

**Why that produces “wings”:** If the terminal bow section (the last section) still has a wide sheer (i.e., its top point has a large \(|y|\)), then the cap necessarily contains large triangles near the top edge. This is visually perceived as a “plate/wing” because MAGNET hull sections are **open keel→deck curves** (not closed polygons), and there is no true “bow tip” section where the curve collapses to centerline.

This is consistent with the code comment itself: it calls out the “wing/plate” artifact risk for bow capping when end-capping an open curve (`magnet/webgl/geometry_pipeline.py:L955-L983`).

#### 3.1.4 Why the stern can appear “missing”

Two concrete failure mechanisms exist in the current implementation:
- **Degenerate-triangle skipping in end caps:** `_add(...)` refuses triangles where any indices repeat (`magnet/webgl/geometry_pipeline.py:L950-L997`). If the stern section has many points within the centerline epsilon (shared vertices), large parts of the cap can be skipped, leaving gaps.
- **Terminal section placement:** The cap is created at the **first/last available section**. If the section set does not include a section at the true transom plane, the “transom” the user expects (a closure at the actual aftmost extent) may not exist as geometry — the cap closes only at the aftmost defined section.

#### 3.1.5 Fix approach (canonical, no new kernel “types”)

The cleanest correction that preserves the North Star (“resolution, not enumeration”):
- **Add explicit terminal closure sections in the compiler output** (or a deterministic tessellation pre-pass) so the bow converges to centerline without introducing a wide end-wall. This is a geometric resolution strategy, not a preset.
- **Make cap logic watertight below the sheer** by capping only up to a defined “watertight top” (e.g., the highest point below the open deck boundary), and never generating end-cap triangles that span the open deck boundary at the bow.

Both approaches can be implemented without adding vessel-family conditionals. They are geometry-only transforms and should be **reported** (see §3.3).

### 3.2 Token Bloat

**Measured fixed system prompt:** `GEOMETRY_PROPOSER_SYSTEM_PROMPT` is ~11,979 characters ≈ **~2,994 tokens** (rule-of-thumb: chars/4) (`magnet/agents/geometry_proposer.py:L24-L259`; measurement performed via `python3` in this environment).

**Total triple-quoted prompt-like text in `geometry_proposer.py`:** ~15,868 characters ≈ **~3,967 tokens** (includes the system prompt plus embedded templates like state injection and task framing).

**Static prompt breakdown (triple-quoted blocks in `geometry_proposer.py`):**

| Component | Location | Chars | Est. tokens |
|---|---:|---:|---:|
| System prompt | `magnet/agents/geometry_proposer.py:L24-L259` | ~11,979 | ~2,994 |
| State injection template (“Current Design State”) | `magnet/agents/geometry_proposer.py:L374-L398` | ~866 | ~216 |
| Task framing (“Your Task”) | `magnet/agents/geometry_proposer.py:L544-L562` | ~492 | ~123 |
| Other embedded blocks (docstrings/templates) | `magnet/agents/geometry_proposer.py` | ~2,531 (remainder) | ~632 |

**Major contributors (static):**
- **System prompt**: long translation guide + multiple examples (`magnet/agents/geometry_proposer.py:L24-L259`).
- **State injection block**: embeds JSON summaries of resources and repeats coordinate rules (`magnet/agents/geometry_proposer.py:L324-L398`).

**Recommendation (aligned with ROADMAP ITEM-001):**
- Replace the long narrative prompt with:
  - a **versioned JSON schema** (already exists: `magnet/agents/geometry_schema.json`) and
  - a **bounded State Lens** for LLM context (instead of dumping large state blobs).

### 3.3 Silent Transforms

**Observed transform:** `compile_section()` resamples polygon sections to **32 points by default** when fewer than 32 points are provided, unless `resample_points` is explicitly set (`magnet/kernel/stdlib/section_compiler.py:L157-L205`).

**Why this matters:** This is exactly the “Silent transforms” known issue — the compiler changes geometry resolution without producing a transform report back to model/UI.

**Recommendation:** Emit a deterministic **transform report** (before/after point counts, resample rule, and whether hard edges were snapped) and persist it in state history/decisions (ROADMAP ITEM-004).

### 3.4 Coordinate Convention Drift (Schema vs Code)

**Observed mismatch:** `magnet/agents/geometry_schema.json` documents:
- `x`: “0=bow, LOA=stern” (`magnet/agents/geometry_schema.json:L76-L79`)

But the codepath used by the design-language compiler and WebGL pipeline uses:
- `geometry.section.station`: 0=bow, 1=stern (normalized)
- derived \(x\) in meters such that **station 0 → x=LOA** and **station 1 → x=0** (`magnet/kernel/stdlib/section_compiler.py:L62-L65`)
- WebGL `HullSection.station` is defined as “X position from AP” (`magnet/webgl/interfaces.py:L187-L195`)

This is a high-risk inconsistency because it directly affects:
- section ordering (bow↔stern),
- densification near ends, and
- end-capping behavior.

**Required action:** Pick one canonical coordinate convention and update **all** docs (`geometry_schema.json`, agent prompt copy) and all implementations to match; then add a runtime assertion that rejects incompatible inputs.

## 4. Golden Path: Step by Step (Actual Current Flow)

### 4.1 UI Load and Connection

- UI v2 served by backend at `/ui/v2/` (`magnet/deployment/api.py:L3265-L3318`).
- UI connects WebSocket at `/ws/{design_id}` (`magnet/ui_v2/js/backend-adapter.js:L141-L158`, `magnet/deployment/api.py:L2535-L2549`).

### 4.2 Intent Preview (Spiral path)

There is no separate “preview” endpoint in the Spiral path; instead:
- Spiral endpoint can return `proposal_low_confidence` and requires explicit `force_apply=true` to proceed (`magnet/ui_v2/js/spiral-adapter.js:L252-L295`, `magnet/deployment/spiral_endpoints.py:L590-L604`).

Legacy preview exists but is disabled by default:
- `POST /api/v1/designs/{id}/intent/preview` (`magnet/deployment/api.py:L1896-L1955`) behind `MAGNET_LEGACY_INTENT_PROTOCOL_ENABLED`.

### 4.3 Intent Apply (Spiral path)

“Apply” is performed inside `spiral_chat`:
- It executes program text via `execute_program(...)` (`magnet/deployment/spiral_endpoints.py:L605-L823`).
- It enforces optimistic locking via `expected_version` → 409 (`magnet/deployment/spiral_endpoints.py:L389-L399`).
- It persists to `DesignStore.save(...)` (`magnet/deployment/spiral_endpoints.py:L748-L764`).

Legacy apply exists but is disabled by default:
- `POST /api/v1/designs/{id}/actions` (`magnet/deployment/api.py:L1654-L1799`) behind `MAGNET_LEGACY_INTENT_PROTOCOL_ENABLED`.

### 4.4 Phase Execution

Two phase mechanisms exist:
- **Spiral endpoint “critical phases”** calls `Conductor.run_phase(...)` for `["hull_form","weight_stability","structure"]` (`magnet/deployment/spiral_endpoints.py:L700-L717`). (Note: the public phase API maps `hull_form → hull` for kernel canonical phase IDs (`magnet/deployment/api.py:L2000-L2009`).)
- **Explicit phase endpoint**: `POST /api/v1/designs/{id}/phases/{phase}/run` calls `conductor.run_phase(kernel_phase)` (`magnet/deployment/api.py:L2011-L2067`).

### 4.5 Geometry Export

- Export endpoint: `GET /api/v1/designs/{design_id}/3d/export/{format}` (`magnet/webgl/api_endpoints.py:L478-L603`).
- Required headers are present (compliance with EXPORT_HEADERS_REQUIRED):
  - `X-Design-Id`, `X-Design-Version`, `X-Geometry-Mode`, `Cache-Control: no-store` (`magnet/webgl/api_endpoints.py:L564-L578`).

### 4.6 UI Render

UI v2:
- fetches the GLB URL with cache-busting query param `v=` (`magnet/ui_v2/js/backend-adapter.js:L870-L878`);
- verifies headers before rendering (`magnet/ui_v2/js/scene-manager.js:L102-L134`).

### 4.7 Canonical Path (Clean, Correct Flow to Preserve)

This is the canonical end-to-end spiral consistent with SPEC + constraints, written as a “golden flow” contract (compare to the current observed flow in §§4.1–4.6):

1. UI v2 loads at `/ui/v2/` (same-origin).
2. WebSocket connects to `/ws/{design_id}`.
3. User submits natural language intent.
4. **Preview** step (no mutation): backend produces a proposed program/ActionPlan *without committing*.
5. Human explicitly clicks **Apply**.
6. Kernel validates stale-version + locks + schema/units/bounds, then commits transactionally; `design_version` increments; WS emits `actions_executed` / `design_updated`.
7. Phase executor runs the requested phase(s); hydrostatics is the only gate; other validators are grades; WS emits `phase_completed`.
8. `GET /api/v1/designs/{id}/3d/export/glb` returns GLB with required headers and `Cache-Control: no-store`.
9. UI cache-busts using `design_version`, validates headers, renders geometry.
10. Loop repeats with downstream→upstream feedback surfaced and human decision recorded.

## 5. Sequence Diagram

```mermaid
sequenceDiagram
  autonumber
  participant UI as UI v2 (browser)
  participant API as FastAPI (`deployment/api.py`)
  participant WS as WebSocket (`/ws/{design_id}`)
  participant Spiral as Spiral endpoints (`spiral_endpoints.py`)
  participant Kernel as Program executor (`kernel/program_executor.py`)
  participant SM as StateManager + DesignStore
  participant WebGL as WebGL export (`webgl/api_endpoints.py`)

  UI->>API: GET /ui/v2/
  UI->>API: POST /api/v1/designs {name,...}
  API->>SM: DesignStore.save(design_id, state)
  UI->>WS: WS connect /ws/{design_id}
  UI->>Spiral: POST /api/v1/designs/{id}/spiral/chat {message, expected_version}
  Spiral->>Kernel: execute_program(program_text, state_manager)
  Kernel->>SM: begin_transaction(); set(...); commit()
  Spiral->>SM: DesignStore.save(design_id, state_manager)
  Spiral-->>WS: enqueue design_updated + snapshot_created
  UI->>WebGL: GET /api/v1/designs/{id}/3d/export/glb?v={design_version}
  WebGL-->>UI: GLB bytes + headers (X-Design-Id/Version/Mode, no-store)
  UI->>UI: Render GLB (verify headers)
```

## 6. Enumeration Inventory

### 6.1 ENUM-KERNEL (Violations)

- **`magnet/kernel/priors/hull_families.py`**
  - `HullFamily(Enum)` and `FAMILY_PRIORS` lookup tables (`magnet/kernel/priors/hull_families.py:L21-L27`, `magnet/kernel/priors/hull_families.py:L120-L207`).
  - **Classification**: ENUM-KERNEL (violates `NO_NEW_KERNEL_PRESETS_OR_STYLE_CATALOGS`).

- **`magnet/kernel/synthesis.py`**
  - Family-based defaults for chines/bow/transom/tumblehome/deck (`magnet/kernel/synthesis.py:L1147-L1262`).
  - `_infer_hull_type(...)` maps family + Fn to a schema hull type (`magnet/kernel/synthesis.py:L449-L465`).
  - **Classification**: ENUM-KERNEL.

- **`magnet/kernel/conductor.py`**
  - Uses `hull.hull_type` / `mission.vessel_type` to pick `HullFamily` and apply priors (`magnet/kernel/conductor.py:L701-L727` from semantic search results).
  - **Classification**: ENUM-KERNEL.

### 6.2 ENUM-PHYSICS (Violations)

- **`magnet/physics/hydrostatics.py`**
  - Branches on `hull_type == "deep_v"` / `"catamaran"` in coefficient estimation and stability calculations (`magnet/physics/hydrostatics.py:L317-L457`, `magnet/physics/hydrostatics.py:L371-L421`).
  - **Classification**: ENUM-KERNEL (physics is within kernel authority boundary).

- **`magnet/physics/validators.py`**
  - Maps vessel strings (“patrol”, “workboat”, etc.) to `HullType` enums (`magnet/physics/validators.py:L476-L496`).
  - **Classification**: ENUM-KERNEL.

### 6.3 ENUM-KERNEL (Additional Instances Found)

- **`magnet/kernel/analysis.py`**
  - `REGIME_FAMILY_PREFERENCE` and `type_map` from strings → `HullFamily` (`magnet/kernel/analysis.py:L28-L33`, `magnet/kernel/analysis.py:L48-L66`).
  - **Classification**: ENUM-KERNEL.

### 6.4 ENUM-WEBGL / ENUM-LEGACY (Mixed)

- **`magnet/webgl/interfaces.py`**
  - Maps string hull feature fields to hull-gen enums and uses `inputs.hull_type == "catamaran"` (`magnet/webgl/interfaces.py:L840-L901`).
  - **Classification**: ENUM-KERNEL (WebGL is inside the kernel subsystem boundary).

- **`magnet/hull_gen/enums.py`**
  - Defines hull taxonomy enums (`HullType`, `ChineType`, `BowStyle`, `TransomType`, etc.) (`magnet/hull_gen/enums.py:L12-L120`).
  - **Classification**: ENUM-LEGACY (allowed only behind explicit fallback boundaries; must not drive kernel decisions).

### 6.5 ENUM-CONTROL_PLANE and ENUM-SUBSYSTEMS (Soft but documented)

- **`magnet/deployment/intent_parser.py`**
  - `ENUM_TO_PATH` maps enumerated hull/material/vessel concepts to state paths (`magnet/deployment/intent_parser.py:L245-L285`).
  - **Classification**: ENUM-CONTROL_PLANE.

- **`magnet/deployment/spiral_endpoints.py`**
  - Migration-only endpoint derives body count from legacy `hull.hull_type` and checks for `"catamaran"` substring (`magnet/deployment/spiral_endpoints.py:L990-L1005`).
  - **Classification**: ENUM-CONTROL_PLANE (explicitly marked MIGRATION ONLY; still an enumeration branch).

- **`magnet/ui_v2/js/backend-adapter.js`**
  - Heuristic “HULL_PATHS” includes style/type fields like `hull.hull_type`, `hull.bow_style`, `hull.chine_type`, etc. (`magnet/ui_v2/js/backend-adapter.js:L803-L842`).
  - **Classification**: ENUM-CONTROL_PLANE.

- **`magnet/weight/estimators/hull.py`**
  - `SERVICE_FACTORS` keyed by `patrol`, `workboat`, `yacht`, etc. (`magnet/weight/estimators/hull.py:L114-L122`).
  - **Classification**: ENUM-SUBSYSTEM (weight).

- **`magnet/cost/estimator.py`**
  - Branches on `vessel_type in ["military","naval","patrol"]` (`magnet/cost/estimator.py:L119-L127`).
  - **Classification**: ENUM-SUBSYSTEM (cost).

- **`magnet/cost/models/equipment.py`**
  - Branches on `vessel_type in ["military","naval","patrol"]` for equipment assumptions (`magnet/cost/models/equipment.py:L133-L146`).
  - **Classification**: ENUM-SUBSYSTEM (cost).

- **`magnet/compliance/validators.py`**
  - Defaults `mission.vessel_type` to `"patrol"` and uses a regulatory framework enum (`magnet/compliance/validators.py:L108-L117`).
  - **Classification**: ENUM-SUBSYSTEM (compliance).

- **`magnet/arrangement/validators.py`**
  - Defaults `vessel_type` to `"patrol"` and derives services from it (`magnet/arrangement/validators.py:L78-L94`).
  - **Classification**: ENUM-SUBSYSTEM (arrangement).

- **`magnet/arrangement/generator.py`**
  - `vessel_type: str = "patrol"` default in arrangement generation API (`magnet/arrangement/generator.py:L116-L128`).
  - **Classification**: ENUM-SUBSYSTEM (arrangement).

- **`magnet/compliance/engine.py`**
  - Compliance engine explicitly treats `vessel_type` as a rule applicability key (`magnet/compliance/engine.py:L112-L147`).
  - **Classification**: ENUM-SUBSYSTEM (compliance).

- **`magnet/stability/damage.py`**
  - Defines a `VesselType(Enum)` for damage stability criteria (`magnet/stability/damage.py:L46-L52`).
  - **Classification**: ENUM-SUBSYSTEM (stability).

- **`magnet/systems/hvac/generator.py`**
  - Defaults `mission.vessel_type` to `"patrol"` and selects zones “based on vessel type” (`magnet/systems/hvac/generator.py:L47-L60`).
  - **Classification**: ENUM-SUBSYSTEM (systems).

- **`magnet/weight/estimators/command.py`**
  - `VESSEL_TYPE_FACTORS` keyed by `patrol`, `military`, `workboat`, etc. (`magnet/weight/estimators/command.py:L22-L32`).
  - **Classification**: ENUM-SUBSYSTEM (weight).

- **`magnet/weight/aggregator.py`**
  - `VESSEL_TYPE_MARGINS` keyed by `patrol`, `ferry`, `workboat`, etc. (`magnet/weight/aggregator.py:L32-L41`).
  - **Classification**: ENUM-SUBSYSTEM (weight).

- **`magnet/ui/chat.py`**
  - Maps keywords `patrol/workboat/ferry/planing/catamaran/tug` to `mission.vessel_type` (`magnet/ui/chat.py:L492-L501`).
  - **Classification**: ENUM-CONTROL_PLANE (UI/interaction layer).

- **`magnet/cli/commands/design.py`**
  - CLI “templates” encode `patrol/ferry/workboat` starting states (`magnet/cli/commands/design.py:L64-L89`).
  - **Classification**: ENUM-TOOLS (CLI).

- **`magnet/core/enums.py`**
  - Defines `VesselType` and `HullType` enumerations used across system (`magnet/core/enums.py:L43-L79`).
  - **Classification**: ENUM-FOUNDATIONAL (risk: these enums become “design catalogs” if used for kernel decisions).

- **`magnet/vision/hull_forms.py`**
  - Declares `HullType(Enum)` and “specialized hull form generators for different vessel types” with `SAFE_DEFAULTS` (`magnet/vision/hull_forms.py:L6-L57`).
  - **Classification**: ENUM-SUBSYSTEM (vision; also a style catalog).

- **`magnet/agents/vision_interpreter.py`**
  - Maintains an explicit forbidden-term list containing vessel types (“patrol boat”, “workboat”, etc.) to prevent type names in vision output (`magnet/agents/vision_interpreter.py:L34-L41`).
  - **Classification**: ENUM-CONTROL_PLANE (anti-enum enforcement; this is “negative enumeration” used for safety).

### 6.6 ENUM-PROMPT (Soft violations)

- **Geometry proposer system prompt** uses vessel-family language (“cargo ships”, “planing boats”, etc.) even when describing them as geometric targets (`magnet/agents/geometry_proposer.py:L100-L158`).

### 6.7 ENUM-UNUSED (Removal candidates)

Not fully audited in this pass; treat any enum definitions that are not referenced outside legacy generator code as candidates once usage is confirmed. (Follow-up: run a repo-wide reference check per enum class.)

## 7. Constraint Compliance Matrix

| Constraint | Enforced? | Enforcement Location | Gap |
|------------|-----------|----------------------|-----|
| UI_V2_ONLY | ✅ | `/ui/v2/` mounting + `/` redirect (`magnet/deployment/api.py:L3265-L3318`) | None |
| FIREWALL_NO_DIRECT_STATE_MUTATION | ⚠️ partial | Legacy path uses ActionPlanValidator/Executor (`magnet/deployment/api.py:L1499-L1617`, `magnet/deployment/api.py:L1654-L1799`) | Spiral path uses `execute_program` (DSL) instead of ActionPlan pipeline; confirm if this is considered “kernel mutation protocol” or a bypass |
| STALE_PLAN_REJECTION_REQUIRED | ✅ (spiral) / ✅ (legacy when enabled) | Spiral: `expected_version` check → 409 (`magnet/deployment/spiral_endpoints.py:L389-L399`); Legacy: `design_version_before` check (`magnet/deployment/api.py:L1728-L1739`) | None |
| LOCKS_ENFORCED | unknown in spiral path | StateManager lock APIs exist (`magnet/core/state_manager.py:L1047-L1076`) | Need explicit evidence that `execute_program` respects locks (not confirmed in this audit) |
| GATE_VS_GRADES | mixed | Pipeline gate check exists (`magnet/deployment/api.py:L2105-L2143`) | Physics/hydrostatics uses hull_type branches (`magnet/physics/hydrostatics.py:L317-L457`) |
| VALIDATOR_HONESTY_FAIL_CLOSED | mixed | Contract check exists (`magnet/deployment/api.py:L2101-L2148`) | Type-based fallbacks in physics may return “valid-looking” numbers outside envelope |
| NO_SILENT_GEOMETRY_FALLBACK | mostly ✅ | `GeometryService.get_hull_geometry(...allow_visual_only=False)` fails closed (`magnet/webgl/geometry_service.py:L152-L187`) | `GET /3d/binary` forces `allow_visual_only=True` (`magnet/webgl/api_endpoints.py:L297-L335`) — should be clearly labeled/segregated |
| EXPORT_HEADERS_REQUIRED | ✅ | Export response headers include required set (`magnet/webgl/api_endpoints.py:L564-L578`) | None |
| NO_NEW_KERNEL_PRESETS_OR_STYLE_CATALOGS | ❌ | — | `HullFamily` priors + synthesis defaults (`magnet/kernel/priors/hull_families.py`, `magnet/kernel/synthesis.py`) |
| KERNEL_PURITY_NO_LLM_DEPS | ✅ (import boundaries) | No `magnet/kernel/**` or `magnet/webgl/**` imports from `magnet/agents/**` found in this audit | Recheck periodically |
| STATE_IS_PRODUCT | ✅ | `DesignStore` persists state; exports are derived (`magnet/deployment/design_store.py:L40-L90`, `magnet/webgl/api_endpoints.py:L478-L603`) | None |
| NO_SILENT_TRANSFORMS | ❌ (soft constraint) | — | Section resampling to 32 is silent (`magnet/kernel/stdlib/section_compiler.py:L157-L205`) |

## 8. Legacy Code Inventory

### 8.1 LEGACY-REMOVE

- `app/` and `frontend/` are explicitly non-authoritative per SPEC; any routing or behavior that treats them as authoritative UI is forbidden (SPEC §4.12 and constraints `UI_V2_ONLY`). (This audit did not propose deletions; it flags drift risk.)

### 8.2 LEGACY-MIGRATE

- Legacy Intent→Action endpoints exist but are disabled by default; decide whether to:
  - remove them, or
  - reintroduce them as the single mutation protocol and adapt Spiral to use them.

### 8.3 LEGACY-UNUSED

Not determined in this pass.

### 8.4 LEGACY-DUPLICATE

- Two separate state-mutation protocols exist (Spiral DSL execution vs ActionPlan pipeline). This is a “parallel subsystem” risk relative to `NO_PARALLEL_SUBSYSTEMS`.

## 9. Gap Analysis

| SPEC Requirement | Current State | Gap | Priority | Remediation |
|---|---|---|---|---|
| Kernel validates reality, never intent/presets | Kernel has HullFamily priors + defaults | ENUM-KERNEL leakage | P0 | Remove family-based defaults from kernel; move to agent-side geometric proposals |
| Hydrostatics is the only gate | Hydrostatics implementation branches on hull_type | Gate depends on type assumptions | P0 | Refactor hydrostatics to be geometry-derived (no hull_type branches) |
| No silent transforms | Section compiler resamples to 32 by default | Transform not reported | P1 | Emit transform report + persist + surface in UI |
| Preview → apply separation | Spiral path has low-confidence confirmation; legacy preview/apply exists but disabled | Two semantics; unclear single source of truth | P1 | Decide canonical protocol; align UI + API + tests |
| Resolution = quality | Guidance exists in prompts; compiler enforces resampling | But resampling is silent and may shift hard edges | P1 | Make resolution policy explicit and auditable |

## 10. File Reference

| Purpose | File Path | Key Entry Points | Status |
|---|---|---|---|
| Backend entry + routing | `magnet/deployment/api.py` | `create_fastapi_app()` | active |
| WS manager | `magnet/deployment/websocket.py` | `ConnectionManager` | active |
| Spiral chat/sketch | `magnet/deployment/spiral_endpoints.py` | `spiral_chat`, `spiral_sketch` | active |
| Persistent state | `magnet/deployment/design_store.py` | `DesignStore.load/save` | active |
| Program execution | `magnet/kernel/program_executor.py` | `execute_program` | active |
| Design-language compilation | `magnet/kernel/stdlib/compiler.py` | `compile_to_geometry` | active |
| Section compilation (resampling) | `magnet/kernel/stdlib/section_compiler.py` | `compile_section` | active |
| Geometry service | `magnet/webgl/geometry_service.py` | `get_hull_geometry`, `get_scene` | active |
| Tessellation + caps | `magnet/webgl/geometry_pipeline.py` | `_tessellate_from_sections`, `_triangulate_end_cap` | active (buggy) |
| Export endpoints | `magnet/webgl/api_endpoints.py` | `export_geometry` | active |

## Appendix A: Key Data Structures

- **Design persistence**: JSON per design at `storage/designs/{design_id}.json` (`magnet/deployment/design_store.py:L40-L90`).
- **DesignProgram (Spiral / agent)**: JSON operations list (agent-side) compiled into DSL (see `magnet/agents/geometry_proposer.py:L312-L317`, `magnet/kernel/program_executor.py:L213-L244`).
- **HullGeometryData**: WebGL canonical geometry object (`magnet/webgl/interfaces.py:L197-L228`).

## Appendix B: API Endpoint Reference (Observed)

- `GET /ui/v2/` — UI v2 HTML (`magnet/deployment/api.py:L3283-L3318`)
- `POST /api/v1/designs` — create design (`magnet/deployment/api.py:L1399-L1475`)
- `GET /api/v1/designs/{design_id}` — load design (`magnet/deployment/api.py:L1477-L1498`)
- `POST /api/v1/designs/{design_id}/spiral/chat` — spiral chat mutation (`magnet/deployment/spiral_endpoints.py:L360-L823`)
- `POST /api/v1/designs/{design_id}/spiral/sketch` — sketch → confirm → execute (`magnet/deployment/spiral_endpoints.py:L825-L963`)
- `GET /api/v1/designs/{design_id}/3d/export/glb` — GLB export with required headers (`magnet/webgl/api_endpoints.py:L478-L603`)
- `DELETE /api/v1/designs/{design_id}/3d/cache` — clear geometry cache (`magnet/webgl/api_endpoints.py:L772-L799`)
- `WS /ws/{design_id}` — event stream (`magnet/deployment/api.py:L2535-L2549`)

## Appendix C: Geometry Pipeline Deep Dive

### Section compilation (resources → sections)

- `compile_section()` compiles `geometry.section` resources and computes X from station (station 0=bow, 1=stern; X derived from LOA) (`magnet/kernel/stdlib/section_compiler.py:L54-L65`).
- Polygon sections are forced keel→deck ordering and are resampled to 32 points by default (`magnet/kernel/stdlib/section_compiler.py:L110-L205`).
- Compiler then fills `pt.position.x = section.x_position` (`magnet/kernel/stdlib/compiler.py:L164-L168`).

### Lofting / Skinning (sections → triangles)

- `_tessellate_from_sections(...)` builds port/starboard grids and triangulates quads between adjacent sections (`magnet/webgl/geometry_pipeline.py:L382-L473`, `magnet/webgl/geometry_pipeline.py:L900-L921`).
- Sections are densified (cosine-distributed inserts near ends). A prior bug is explicitly documented: interpolating X using normalized station collapses near x≈0..1 and produces “wings”; the code now interpolates X from actual point coordinates (`magnet/webgl/geometry_pipeline.py:L712-L717`).

### Capping (bow/stern)

- End caps are always added after side triangulation (`magnet/webgl/geometry_pipeline.py:L475-L592`).
- `_triangulate_end_cap(...)` is the exact implementation to debug/fix (`magnet/webgl/geometry_pipeline.py:L933-L1047`).

### GLB export

- Export response includes required identity/version/mode headers and disables caching (`magnet/webgl/api_endpoints.py:L564-L578`).

