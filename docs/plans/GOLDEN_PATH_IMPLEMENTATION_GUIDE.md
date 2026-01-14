# Golden Path Implementation Guide

**Source:** `Golden Path AUDIT 1 copy.md`  
**Generated:** 2026-01-13  
**Purpose:** Step-by-step implementation guide for autonomous agent execution

---

## Constraints (Must Preserve)

| Constraint ID | Rule |
|---------------|------|
| `FIREWALL_NO_DIRECT_STATE_MUTATION` | Agents never directly mutate state; must go through kernel protocol |
| `NO_NEW_KERNEL_PRESETS_OR_STYLE_CATALOGS` | No enumeration; no vessel type → parameter defaults |
| `GATE_VS_GRADES` | Hydrostatics is only gate; everything else is advisory grade |
| `KERNEL_PURITY_NO_LLM_DEPS` | Kernel cannot import from agents |
| `STATE_IS_PRODUCT` | DesignState is truth; exports are derived |

---

## Anti-Patterns (Must Avoid)

- Do NOT create parallel subsystems — extend existing code
- Do NOT add new enums or type catalogs
- Do NOT modify kernel to import from agents
- Do NOT make tasks that require human judgment to verify
- Do NOT introduce vessel-family conditionals

---

# P0 — Blocking Tasks

---

## TASK-001: Fix Hull End-Cap Triangulation

**Goal:** Eliminate "wings" at bow and "missing back" at stern by correcting the end-cap triangulation algorithm.

**Files:**
- `magnet/webgl/geometry_pipeline.py` (L933-L1047)

**Problem Analysis:**
- Bow cap creates large triangles when terminal section has wide sheer (L955-L983)
- Stern cap skips triangles when indices repeat due to centerline epsilon (L950-L997)
- No explicit terminal closure sections exist in compiler output

**Acceptance Criteria:**
1. `grep -c "wings\|plate" magnet/webgl/geometry_pipeline.py` returns 0 (artifact comments removed after fix)
2. Unit test: Export GLB for a 25m monohull; mesh is manifold below sheer line
3. Visual: Bow converges to centerline without horizontal "plate" artifact
4. Visual: Stern cap fully closes the transom plane

**Dependencies:** None

**Scope:** Large

<!-- AGENT:START -->
Files: [magnet/webgl/geometry_pipeline.py]
Search: `_triangulate_end_cap`
Pattern: Function at L933-L1047 builds cap as two strips toward centerline
Replace: 
1. Add explicit terminal closure logic: if terminal section sheer width > threshold, insert synthetic converging section
2. Cap only up to "watertight top" (highest point below open deck boundary)
3. Fix degenerate triangle skipping: use proper tolerance for near-centerline points
Verify:
- `python3 -c "from magnet.webgl.geometry_pipeline import _triangulate_end_cap; print('import ok')"`
- Run: `pytest tests/webgl/test_geometry_pipeline.py -k cap -v`
- Export GLB and inspect in 3D viewer for watertight hull below sheer
<!-- AGENT:END -->

---

## TASK-002: Remove HullFamily Enumeration from Kernel Priors

**Goal:** Delete vessel-family priors from kernel to comply with `NO_NEW_KERNEL_PRESETS_OR_STYLE_CATALOGS`.

**Files:**
- `magnet/kernel/priors/hull_families.py` (L21-L27, L120-L207)
- `magnet/kernel/priors/__init__.py`

**Problem Analysis:**
- `HullFamily(Enum)` defines categorical types: PATROL, WORKBOAT, FERRY, PLANING, CATAMARAN
- `FAMILY_PRIORS` provides default ratios/coefficients per type
- This is enumeration leakage that violates North Star

**Acceptance Criteria:**
1. `grep -r "HullFamily" magnet/kernel/` returns 0 matches
2. `grep -r "FAMILY_PRIORS" magnet/kernel/` returns 0 matches
3. File `magnet/kernel/priors/hull_families.py` does not exist
4. All imports of `HullFamily` from kernel are removed or migrated

**Dependencies:** TASK-003

**Scope:** Medium

<!-- AGENT:START -->
Files: [magnet/kernel/priors/hull_families.py, magnet/kernel/priors/__init__.py]
Search: `HullFamily`, `FAMILY_PRIORS`
Pattern: Enum class + dictionary lookup table for vessel-family defaults
Replace:
1. Delete `magnet/kernel/priors/hull_families.py` entirely
2. Update `magnet/kernel/priors/__init__.py` to remove exports
3. Search callers: `grep -r "from magnet.kernel.priors import" magnet/`
4. Migrate callers to use geometry-derived values or move logic to agent layer
Verify:
- `grep -r "HullFamily" magnet/kernel/` returns empty
- `python3 -c "from magnet.kernel import priors; print(dir(priors))"` shows no HullFamily
<!-- AGENT:END -->

---

## TASK-003: Remove Family-Based Defaults from Kernel Synthesis

**Goal:** Eliminate family→parameter mapping logic from synthesis module.

**Files:**
- `magnet/kernel/synthesis.py` (L1147-L1262, L449-L465)
- `magnet/kernel/conductor.py` (L701-L727)

**Problem Analysis:**
- `_create_initial_proposal()` uses `FAMILY_CHINE_DEFAULTS`, `FAMILY_TRANSOM_DEFAULTS`, etc.
- `_infer_hull_type()` maps family + Froude number to schema hull type
- `conductor.py` picks `HullFamily` from `hull.hull_type` or `mission.vessel_type`

**Acceptance Criteria:**
1. `grep -c "FAMILY_.*_DEFAULTS" magnet/kernel/synthesis.py` returns 0
2. `grep -c "HullFamily" magnet/kernel/synthesis.py` returns 0
3. `grep -c "HullFamily" magnet/kernel/conductor.py` returns 0
4. `grep -c "_infer_hull_type" magnet/kernel/synthesis.py` returns 0

**Dependencies:** None (but should coordinate with TASK-002)

**Scope:** Large

<!-- AGENT:START -->
Files: [magnet/kernel/synthesis.py, magnet/kernel/conductor.py]
Search: `FAMILY_CHINE_DEFAULTS`, `FAMILY_TRANSOM_DEFAULTS`, `HullFamily`, `_infer_hull_type`
Pattern: Dictionary lookups that map vessel family → default feature parameters
Replace:
1. Remove all `FAMILY_*_DEFAULTS` dictionaries
2. Replace family-based lookups with:
   - Physics-derived defaults (e.g., Froude number → chine decision via continuous function)
   - Or: require explicit geometry specification from agent
3. Delete `_infer_hull_type()` function
4. In conductor.py L701-L727: remove HullFamily lookup; use geometry directly
Verify:
- `grep -E "FAMILY_|HullFamily|_infer_hull_type" magnet/kernel/synthesis.py magnet/kernel/conductor.py` returns empty
- `pytest tests/kernel/test_synthesis.py -v`
<!-- AGENT:END -->

---

## TASK-004: Remove Type Branches from Hydrostatics

**Goal:** Refactor hydrostatics to use geometry-derived calculations instead of `hull_type` conditionals.

**Files:**
- `magnet/physics/hydrostatics.py` (L317-L530)
- `magnet/physics/validators.py` (L476-L496)

**Problem Analysis:**
- `_estimate_cm()` branches on `hull_type == "deep_v"`, `"catamaran"` (L317-L457)
- `validators.py` maps strings "patrol", "workboat" → `HullType` enums
- This violates gate purity: hydrostatics should compute from geometry, not types

**Acceptance Criteria:**
1. `grep -c 'hull_type ==' magnet/physics/hydrostatics.py` returns 0
2. `grep -c '"deep_v"\|"catamaran"' magnet/physics/hydrostatics.py` returns 0
3. `grep -c 'type_map' magnet/physics/validators.py` returns 0
4. Hydrostatics computes from actual hull geometry (displacement, waterplane area, etc.)

**Dependencies:** None

**Scope:** Large

<!-- AGENT:START -->
Files: [magnet/physics/hydrostatics.py, magnet/physics/validators.py]
Search: `hull_type ==`, `"deep_v"`, `"catamaran"`, `type_map`
Pattern: Conditional branches that select coefficients based on vessel type strings
Replace:
1. In `_estimate_cm()`: compute midship coefficient from actual geometry:
   - Use numerical integration of section area
   - Or derive from block coefficient + prismatic coefficient (both geometry-derived)
2. Remove all `if hull_type == "..."` branches
3. In validators.py: remove `type_map` dictionary; validate geometry directly
Verify:
- `grep -E 'hull_type.*==|"deep_v"|"catamaran"|type_map' magnet/physics/hydrostatics.py magnet/physics/validators.py` returns empty
- `pytest tests/physics/test_hydrostatics.py -v`
<!-- AGENT:END -->

---

# P1 — Critical Tasks

---

## TASK-005: Fix Coordinate Convention Mismatch

**Goal:** Align coordinate convention between schema documentation and code implementation.

**Files:**
- `magnet/agents/geometry_schema.json` (L76-L79)
- `magnet/kernel/stdlib/section_compiler.py` (L62-L65)
- `magnet/webgl/interfaces.py` (L187-L195)
- `magnet/agents/geometry_proposer.py` (prompt text)

**Problem Analysis:**
- Schema says: `x: 0=bow, LOA=stern`
- Code implements: `station 0 → x=LOA (bow)`, `station 1 → x=0 (stern)`
- This is inverted and causes confusion in section ordering and capping

**Acceptance Criteria:**
1. All files use same convention: either `x=0 at AP (stern)` or `x=0 at FP (bow)`
2. `geometry_schema.json` documentation matches code behavior
3. Runtime assertion added that rejects incompatible inputs
4. `grep "x.*bow\|x.*stern\|0.*bow\|0.*stern" magnet/agents/geometry_schema.json` shows consistent single convention

**Dependencies:** None

**Scope:** Medium

<!-- AGENT:START -->
Files: [magnet/agents/geometry_schema.json, magnet/kernel/stdlib/section_compiler.py, magnet/webgl/interfaces.py, magnet/agents/geometry_proposer.py]
Search: `x: 0`, `station`, `bow`, `stern`, `AP`, `FP`
Pattern: Documentation says x=0 at bow; code computes x=0 at stern (AP)
Replace:
1. Choose canonical convention: **x=0 at AP (stern), x=LOA at FP (bow)** (matches naval architecture standard)
2. Update `geometry_schema.json` L76-L79: change to `"x": "0=stern (AP), LOA=bow (FP)"`
3. Update agent prompts to match
4. Add assertion in section_compiler.py: `assert station >= 0 and station <= 1, "station must be normalized 0-1"`
Verify:
- `grep -A2 '"x":' magnet/agents/geometry_schema.json` shows updated description
- `python3 -c "from magnet.kernel.stdlib.section_compiler import compile_section; print('ok')"`
<!-- AGENT:END -->

---

## TASK-006: Add Transform Reporting to Section Compiler

**Goal:** Emit explicit transform reports when sections are resampled, eliminating silent transforms.

**Files:**
- `magnet/kernel/stdlib/section_compiler.py` (L157-L205)

**Problem Analysis:**
- `compile_section()` resamples to 32 points by default when `< 32` points provided
- This transform is silent — no report to model/UI
- Violates `NO_SILENT_TRANSFORMS` constraint

**Acceptance Criteria:**
1. `compile_section()` returns a transform report dict alongside `HullSection`
2. Report contains: `{"original_points": N, "resampled_points": M, "rule": "default_32", "hard_edges_snapped": [...]}`
3. Caller logs or persists transform report
4. `grep "transform_report" magnet/kernel/stdlib/section_compiler.py` returns >= 1 match

**Dependencies:** None

**Scope:** Small

<!-- AGENT:START -->
Files: [magnet/kernel/stdlib/section_compiler.py]
Search: `target_n = 32`, `resample_points`
Pattern: Resampling happens at L157-L205 without reporting
Replace:
1. Create return type: `Tuple[HullSection, TransformReport]` or dataclass
2. After resampling, build report:
```python
transform_report = {
    "original_points": len(points_raw),
    "resampled_points": target_n,
    "rule": "default_32" if not resource.get("resample_points") else "explicit",
    "hard_edges_snapped": snapped_edges,
}
```
3. Return tuple or add report to HullSection metadata
4. Update all callers to handle new return type
Verify:
- `grep "transform_report" magnet/kernel/stdlib/section_compiler.py` returns match
- `pytest tests/kernel/test_section_compiler.py -v`
<!-- AGENT:END -->

---

## TASK-007: Resolve Dual Control Plane Architecture

**Goal:** Consolidate to single mutation protocol (Spiral is authority; legacy Intent→Action removed or unified).

**Files:**
- `magnet/deployment/api.py` (L999-L1006, L1647-L1670, L1896-L1922)
- `magnet/deployment/spiral_endpoints.py`

**Problem Analysis:**
- Spiral endpoints are default authority (`MAGNET_LEGACY_INTENT_PROTOCOL_ENABLED=false`)
- Legacy Intent→Action endpoints still exist in code
- Two parallel mutation paths = potential drift and confusion

**Acceptance Criteria:**
1. Legacy endpoints either:
   - Fully removed (preferred), OR
   - Unified to call Spiral internally
2. `grep -c "MAGNET_LEGACY_INTENT_PROTOCOL_ENABLED" magnet/deployment/api.py` returns 0 (if removed)
3. Single documented mutation path in API
4. No duplicate state mutation code paths

**Dependencies:** None

**Scope:** Medium

<!-- AGENT:START -->
Files: [magnet/deployment/api.py, magnet/deployment/spiral_endpoints.py]
Search: `MAGNET_LEGACY_INTENT_PROTOCOL_ENABLED`, `/intent/preview`, `/actions`
Pattern: Feature flag guards legacy endpoints; both paths mutate state differently
Replace:
Option A (Remove legacy):
1. Delete legacy endpoint functions: `intent_preview`, `submit_actions`
2. Remove feature flag and routing logic
3. Update any clients that might use legacy paths

Option B (Unify):
1. Refactor legacy endpoints to call Spiral internally
2. Deprecate direct legacy access
Verify:
- `grep -E "intent_preview|submit_actions|LEGACY_INTENT" magnet/deployment/api.py` returns empty (if Option A)
- `curl -X POST localhost:8000/api/v1/designs/test/intent/preview` returns 404 (if removed)
<!-- AGENT:END -->

---

## TASK-008: Verify Lock Enforcement in Spiral Path

**Goal:** Confirm that `execute_program` respects StateManager locks; add enforcement if missing.

**Files:**
- `magnet/kernel/program_executor.py` (L58-L210)
- `magnet/core/state_manager.py` (L1047-L1076)

**Problem Analysis:**
- StateManager has lock APIs (`lock_parameter`, `is_locked`)
- Audit could not confirm `execute_program` checks locks before mutation
- Locked parameters must be rejected, not silently overwritten

**Acceptance Criteria:**
1. `execute_program` calls `state_manager.is_locked(path)` before any `set(path, value)`
2. Locked path mutation raises `LockedParameterError` or similar
3. Unit test: attempt to modify locked parameter via program → expect failure
4. `grep "is_locked" magnet/kernel/program_executor.py` returns >= 1 match

**Dependencies:** None

**Scope:** Small

<!-- AGENT:START -->
Files: [magnet/kernel/program_executor.py, magnet/core/state_manager.py]
Search: `is_locked`, `lock_parameter`, `set(`
Pattern: State mutations via `set()` without lock checks
Replace:
1. In action application loop, before `state_manager.set(path, value)`:
```python
if state_manager.is_locked(path):
    raise LockedParameterError(f"Cannot modify locked parameter: {path}")
```
2. Import or define `LockedParameterError`
3. Add to `ExecutionResult.errors` if lock violation detected
Verify:
- `grep "is_locked" magnet/kernel/program_executor.py` returns match
- `pytest tests/kernel/test_program_executor.py -k lock -v`
<!-- AGENT:END -->

---

# P2 — Important Tasks

---

## TASK-009: Audit and Remove app/ Directory

**Goal:** Verify `app/` is non-authoritative; remove or clearly mark as deprecated.

**Files:**
- `app/` (entire directory)

**Problem Analysis:**
- SPEC declares `UI_V2_ONLY` constraint
- `app/` appears to be legacy React frontend
- Any routing treating `app/` as authoritative violates spec

**Acceptance Criteria:**
1. No imports from `app/` in `magnet/` codebase
2. No API routes serve content from `app/`
3. Either: `app/` deleted, OR: `app/README.md` exists with "DEPRECATED - DO NOT USE"
4. `grep -r "app/" magnet/deployment/api.py` returns 0 matches for app routing

**Dependencies:** None

**Scope:** Small

<!-- AGENT:START -->
Files: [app/]
Search: `from app`, `app/dist`, `app/src`
Pattern: Any imports or routing to legacy app directory
Replace:
1. Verify no references: `grep -r "app/" magnet/`
2. Check API routing: `grep -r "app" magnet/deployment/api.py`
3. If unreferenced: delete `app/` directory
4. If referenced: trace and remove references first
Verify:
- `ls app/` returns "No such file or directory" OR file contains DEPRECATED notice
- `grep -r "from app" magnet/` returns empty
<!-- AGENT:END -->

---

## TASK-010: Audit and Remove frontend/ Directory

**Goal:** Verify `frontend/` is non-authoritative; remove or clearly mark as deprecated.

**Files:**
- `frontend/` (entire directory)

**Problem Analysis:**
- SPEC declares `UI_V2_ONLY` constraint
- `frontend/` contains TypeScript components outside ui_v2
- May be duplicate or legacy code

**Acceptance Criteria:**
1. No imports from `frontend/` in `magnet/` codebase
2. Either: `frontend/` deleted, OR: `frontend/README.md` exists with "DEPRECATED"
3. `grep -r "frontend/" magnet/` returns 0 matches

**Dependencies:** None

**Scope:** Small

<!-- AGENT:START -->
Files: [frontend/]
Search: `from frontend`, `frontend/components`
Pattern: Any imports or references to legacy frontend directory
Replace:
1. Verify no references: `grep -r "frontend/" magnet/`
2. If unreferenced: delete `frontend/` directory
3. If referenced: trace and remove references first
Verify:
- `ls frontend/` returns "No such file or directory" OR file contains DEPRECATED notice
- `grep -r "from frontend\|frontend/" magnet/` returns empty
<!-- AGENT:END -->

---

## TASK-011: Remove Enumeration from Kernel Analysis

**Goal:** Remove `REGIME_FAMILY_PREFERENCE` and `type_map` from kernel analysis.

**Files:**
- `magnet/kernel/analysis.py` (L28-L33, L48-L66)

**Problem Analysis:**
- `REGIME_FAMILY_PREFERENCE` maps speed regimes to preferred HullFamily lists
- `type_map` converts strings to HullFamily enum
- This is enumeration in kernel (violation)

**Acceptance Criteria:**
1. `grep -c "REGIME_FAMILY_PREFERENCE" magnet/kernel/analysis.py` returns 0
2. `grep -c "HullFamily" magnet/kernel/analysis.py` returns 0
3. Analysis uses geometry-derived characteristics only

**Dependencies:** TASK-002, TASK-003

**Scope:** Medium

<!-- AGENT:START -->
Files: [magnet/kernel/analysis.py]
Search: `REGIME_FAMILY_PREFERENCE`, `type_map`, `HullFamily`
Pattern: Dictionary mapping regimes/strings to vessel families
Replace:
1. Delete `REGIME_FAMILY_PREFERENCE` dictionary
2. Delete `type_map` dictionary
3. Replace family-based analysis with geometry-derived metrics:
   - Use L/B ratio, Cb, deadrise angle directly
   - Classify by continuous parameters, not categorical types
Verify:
- `grep -E "REGIME_FAMILY|type_map|HullFamily" magnet/kernel/analysis.py` returns empty
- `pytest tests/kernel/test_analysis.py -v`
<!-- AGENT:END -->

---

## TASK-012: Remove Enumeration from WebGL Interfaces

**Goal:** Remove `hull_type == "catamaran"` conditional from WebGL adapter.

**Files:**
- `magnet/webgl/interfaces.py` (L840-L901)

**Problem Analysis:**
- `HullGeneratorAdapter._build_hull_features()` uses `inputs.hull_type == "catamaran"` to set `num_hulls=2`
- This is type-based logic in kernel subsystem

**Acceptance Criteria:**
1. `grep -c 'hull_type ==' magnet/webgl/interfaces.py` returns 0
2. `grep -c '"catamaran"' magnet/webgl/interfaces.py` returns 0
3. Multi-hull detection uses geometry (body count) not type string

**Dependencies:** None

**Scope:** Small

<!-- AGENT:START -->
Files: [magnet/webgl/interfaces.py]
Search: `hull_type == "catamaran"`, `num_hulls`
Pattern: Conditional sets num_hulls based on type string
Replace:
1. Replace type check with geometry query:
```python
# Before: num_hulls=2 if inputs.hull_type == "catamaran" else 1
# After: num_hulls = len(inputs.body_ids) if hasattr(inputs, 'body_ids') else 1
```
2. Or derive from actual geometry body count in state
Verify:
- `grep -E 'hull_type.*==|"catamaran"' magnet/webgl/interfaces.py` returns empty
- `pytest tests/webgl/test_interfaces.py -v`
<!-- AGENT:END -->

---

## TASK-013: Remove Enumeration from Migration Endpoint

**Goal:** Remove `"catamaran"` substring check from migration endpoint.

**Files:**
- `magnet/deployment/spiral_endpoints.py` (L990-L1005)

**Problem Analysis:**
- `migrate_to_geometry()` checks `"catamaran" in str(hull_type).lower()` to set body count
- This is type-based logic (acceptable only during migration, but should be replaced)

**Acceptance Criteria:**
1. `grep -c '"catamaran"' magnet/deployment/spiral_endpoints.py` returns 0
2. Migration uses existing geometry body count or explicit parameter

**Dependencies:** None

**Scope:** Small

<!-- AGENT:START -->
Files: [magnet/deployment/spiral_endpoints.py]
Search: `"catamaran"`, `hull_type`, `body_count`
Pattern: Substring check for "catamaran" to determine body count
Replace:
1. Replace type check with geometry query:
```python
# Before: if hull_type and "catamaran" in str(hull_type).lower(): body_count = 2
# After: body_count = sm.get("geometry.body_count", 1) or len(sm.list_resources("geometry.body"))
```
2. Or require explicit body count in migration request
Verify:
- `grep '"catamaran"' magnet/deployment/spiral_endpoints.py` returns empty
- `curl -X POST localhost:8000/api/v1/designs/test/migrate-to-geometry` succeeds
<!-- AGENT:END -->

---

# Dependency Graph

```
TASK-001 (hull caps)
    └── None

TASK-002 (remove hull_families.py)
    └── TASK-003 (must remove synthesis usage first)

TASK-003 (synthesis enumeration)
    └── None

TASK-004 (hydrostatics)
    └── None

TASK-005 (coordinates)
    └── None

TASK-006 (transform reporting)
    └── None

TASK-007 (dual control plane)
    └── None

TASK-008 (lock enforcement)
    └── None

TASK-009 (app/ removal)
    └── None

TASK-010 (frontend/ removal)
    └── None

TASK-011 (kernel analysis)
    └── TASK-002, TASK-003

TASK-012 (webgl interfaces)
    └── None

TASK-013 (migration endpoint)
    └── None
```

---

# Execution Order (Recommended)

## Phase 1: P0 Blocking (execute in parallel where possible)

1. **TASK-001** — Fix hull end-cap (can run independently)
2. **TASK-003** — Remove synthesis enumeration (must complete before TASK-002)
3. **TASK-002** — Remove hull_families.py (after TASK-003)
4. **TASK-004** — Remove hydrostatics type branches (can run independently)

## Phase 2: P1 Critical

5. **TASK-005** — Fix coordinate convention
6. **TASK-006** — Add transform reporting
7. **TASK-007** — Resolve dual control plane
8. **TASK-008** — Verify lock enforcement

## Phase 3: P2 Cleanup

9. **TASK-009** — Remove app/
10. **TASK-010** — Remove frontend/
11. **TASK-011** — Remove kernel analysis enumeration (after TASK-002, TASK-003)
12. **TASK-012** — Remove webgl interfaces enumeration
13. **TASK-013** — Remove migration endpoint enumeration

---

# Success Criteria (Final Validation)

Run these checks after all tasks complete:

```bash
# 1. Hull renders as closed watertight shell (open top)
pytest tests/webgl/test_geometry_pipeline.py -v -k "cap or manifold"

# 2. No enumeration in kernel or physics
grep -rE "HullFamily|FAMILY_PRIORS|hull_type.*==" magnet/kernel/ magnet/physics/
# Expected: empty output

# 3. Coordinate conventions are consistent
grep -A2 '"x":' magnet/agents/geometry_schema.json
# Expected: matches code convention (x=0 at stern)

# 4. Transforms are reported, not silent
grep "transform_report" magnet/kernel/stdlib/section_compiler.py
# Expected: at least 1 match

# 5. All tests pass
pytest tests/ -v --ignore=tests/integration/
```

---

# File Index (Quick Reference)

| File | Tasks |
|------|-------|
| `magnet/webgl/geometry_pipeline.py` | TASK-001 |
| `magnet/kernel/priors/hull_families.py` | TASK-002 |
| `magnet/kernel/synthesis.py` | TASK-003 |
| `magnet/kernel/conductor.py` | TASK-003 |
| `magnet/physics/hydrostatics.py` | TASK-004 |
| `magnet/physics/validators.py` | TASK-004 |
| `magnet/agents/geometry_schema.json` | TASK-005 |
| `magnet/kernel/stdlib/section_compiler.py` | TASK-005, TASK-006 |
| `magnet/webgl/interfaces.py` | TASK-005, TASK-012 |
| `magnet/agents/geometry_proposer.py` | TASK-005 |
| `magnet/deployment/api.py` | TASK-007 |
| `magnet/deployment/spiral_endpoints.py` | TASK-007, TASK-013 |
| `magnet/kernel/program_executor.py` | TASK-008 |
| `magnet/core/state_manager.py` | TASK-008 |
| `app/` | TASK-009 |
| `frontend/` | TASK-010 |
| `magnet/kernel/analysis.py` | TASK-011 |
