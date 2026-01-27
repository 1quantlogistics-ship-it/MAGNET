# Golden Path Implementation Guide

**Source:** `Golden Path AUDIT 1 copy.md`  
**Generated:** 2026-01-13  
**Purpose:** Step-by-step implementation guide for autonomous agent execution

---

## 🏛️ Architectural Context: The Mid-Migration State

The MAGNET system is currently mid-migration.
Some modules speak the new language of **Geometry** (Generative).
Some modules still speak the old language of **Type** (Enumerative).

This guide does not propose enhancements; it tracks **debt repayment**. Every task listed hereafter is a step toward the "Validating Kernel" thesis. We are excising ghosts of categorical presets to reach a state of geometric purity.

---

## ⚖️ The Authority of Physics

In this mid-migration state, hierarchy is mandatory to prevent drift:

*   **Authoritative Path:** `magnet/physics/geometry_hydrostatics.py` is the sole source of truth for physical validation. It must derive all metrics purely from geometry primitives.
*   **Legacy Path:** `magnet/physics/hydrostatics.py` is marked as **Deprecated**. It is fenced, restricted, and scheduled for removal. Any call path that still branches on `hull_type` is transitional contamination and must be excised.
*   **The Firewall:** Froude Number (Fn) may influence *continuous outputs* (e.g., resistance magnitude), but it may never be used to select categorical regimes, methods, or models via branching.

---

## 📔 Enumeration Ledger

The following artifacts represent known architectural debt. Their existence is a failure of the generative thesis, preserved only as a temporary necessity for continuity:

| Offender | Symbol | Debt Reason | Excision Phase |
|----------|--------|-------------|----------------|
| `magnet/physics/hydrostatics.py` | `_estimate_cm()` | Type-based coefficient branching | P0 (TASK-004) |
| `magnet/physics/validators.py` | `is_catamaran` | Hardcoded type string check | P0 (TASK-004) |
| `magnet/weight/estimators/hull.py` | `HULL_TYPE_FACTORS` | Preset weight multipliers | P1 (TASK-017) |
| `magnet/cost/estimator.py` | `_estimate_engineering` | Categorical scaling (patrol/military) | P2 (TASK-018) |

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

## TASK-000: Resolve Y-Axis & Vertical Datum Conflicts (Pre-Requisite)

**Goal:** The codebase has conflicting coordinate conventions. Resolve before any geometry refactoring.

**Conflict Evidence:**

| Dimension | Conflicting Conventions | Evidence |
|-----------|-------------------------|----------|
| **Y-Axis** | Y+ = Port vs Y+ = Starboard | `hull_gen/__init__.py` (Port) vs `geometry.py` (Starboard) |
| **Z-Axis** | Z=0 is Baseline vs Waterline | `hull_gen/__init__.py` (Baseline) vs `geometry_proposer.py` (Waterline) |
| **X-Axis** | X=0 at Bow vs Stern | `geometry_schema.json` (Bow) vs `generator.py` (Stern) |

**Mandatory Convention (MAGNET Standard):**
1. **Y+ = Port** (Right-handed system: $X \times Y = Z$, where X=Forward, Z=Up).
2. **Z=0 = Baseline** (Static datum). Waterline is a variable state (`z = draft`).
3. **Station 0 = AP (Stern)**; **Station 1 = FP (Bow)**.
4. **X=0 at AP (Stern)**; **X=LOA at FP (Bow)**.

**Acceptance Criteria:**
1. `docs/architecture/GEOMETRY_CONVENTIONS.md` created with the above rules.
2. All modules (schema, code, agents) refactored to use MAGNET Standard.
3. `pytest tests/webgl/test_geometry_pipeline.py` passes with correct handedness (normals facing out).
4. `from magnet.hull_gen.geometry import mirror; assert mirror(mirror(Point3D(1, 2, 3))) == Point3D(1, 2, 3)` holds for bitwise identity.
5. `grep -A2 '"x":' magnet/agents/geometry_schema.json` shows `"0=stern (AP), LOA=bow (FP)"`.

**Dependencies:** None

**Scope:** Large (Refactors schema, code, and agent prompts)

**Rollback:**
```bash
git checkout HEAD~1 -- magnet/hull_gen/__init__.py magnet/hull_gen/geometry.py magnet/agents/geometry_schema.json
```

<!-- AGENT:START -->
Files: [magnet/agents/geometry_schema.json, magnet/kernel/stdlib/section_compiler.py, magnet/webgl/interfaces.py, magnet/agents/geometry_proposer.py, magnet/hull_gen/geometry.py]
Search: `x: 0`, `station`, `bow`, `stern`, `AP`, `FP`, `positive starboard`, `z=0 is waterline`
Pattern: Conflicting coordinate definitions across documentation and implementation.
Replace:
1. Update `geometry_schema.json` to define X=0 as Stern (AP).
2. Refactor `hull_gen/geometry.py` and weight/items to use Y+ as Port.
3. Update `geometry_proposer.py` prompts to use Baseline as Z=0.
4. Update `webgl/interfaces.py` and `section_compiler.py` to match MAGNET Standard.
Verify:
- `pytest tests/` passes.
- Symmetry checks in renders are correct.
<!-- AGENT:END -->

---

## TASK-000b: Centralize Numerical Tolerances

**Goal:** Eliminate "folklore" tolerances (1e-6, 1e-10) scattered as literals.

**Files:**
- `magnet/core/constants.py`
- All files containing `1e-` literals

**Acceptance Criteria:**
1. `magnet/core/constants.py` defines `EPSILON_MESH`, `EPSILON_GEOMETRY`, `EPSILON_CONVERGENCE`.
2. No `1e-` literals remain in `magnet/webgl/` or `magnet/hull_gen/`.
3. All geometry-derived quantities are idempotent (re-computing `hull.volume` twice returns identical bits).

<!-- AGENT:START -->
Files: [magnet/core/constants.py, magnet/webgl/*.py, magnet/hull_gen/*.py]
Search: `1e-6`, `1e-10`, `0.001`, `epsilon`
Pattern: Scattered tolerance literals
Replace:
1. Create or update `magnet/core/constants.py`:
```python
EPSILON_MESH = 1e-6       # Vertex deduplication
EPSILON_GEOMETRY = 1e-9   # Area/volume integration
EPSILON_CONVERGENCE = 1e-4  # Iterative solver
```
2. Replace all literals with constant imports
Verify:
- `grep -r "1e-" magnet/webgl/ magnet/hull_gen/` returns empty
- `pytest tests/` passes
<!-- AGENT:END -->

---

## TASK-000c: Unified Physical Ownership (Displacement/LCG)

**Goal:** Declare `geometry_hydrostatics.py` as the sole authority for physical properties (displacement, LCB, VCB). Remove dual-writing/overwriting in `weight` or `reporting`.

**Files:**
- `magnet/reporting/generators/design_summary.py`
- `magnet/weight/summary_generator.py`
- `magnet/core/design_state.py`

**Acceptance Criteria:**
1. `design_summary.py` fallback logic (L57-L60) is replaced with a single reference to `hull.displacement_mt`.
2. `weight` modules do not write to `hull.*` or `weight.displacement_mt`. Instead, they write to `weight.lightship_mt`.
3. Total Displacement is calculated ONLY as `lightship + payload + fuel` (which must match buoyancy) or derived purely from geometry.
4. No module overwrites a value written by another phase without a `STALE` invalidation.

**Dependencies:** TASK-000 (coordinate conventions must be locked first)

**Scope:** Medium

<!-- AGENT:START -->
Files: [magnet/reporting/generators/design_summary.py, magnet/weight/summary_generator.py, magnet/core/design_state.py]
Search: `displacement_mt`, `hull.displacement`, `weight.displacement`
Pattern: Multiple modules writing to same state path
Replace:
1. `design_summary.py`: Remove fallback; use single reference to `hull.displacement_mt`
2. `weight` modules: Write only to `weight.lightship_mt`
3. Add assertion: `displacement = lightship + payload + fuel`
Verify:
- `grep -r "displacement_mt.*=" magnet/` shows exactly one write location
- `pytest tests/physics/test_hydrostatics.py -v`
<!-- AGENT:END -->

---

## TASK-000d: Establish Documentation Structure

**Goal:** Create a unified documentation system that agents can navigate and reference.

**Files:**
- `docs/` (new directory structure)
- All existing `.md` files in project root

**Documentation Structure:**
```
docs/
├── README.md                        # Index of all documentation
├── architecture/
│   ├── NORTH_STAR.md                # Mission and equation
│   ├── CONSTITUTION.md              # Laws and constraints
│   ├── GEOMETRY_CONVENTIONS.md      # Point/coordinate standards
│   └── PHASE_MACHINE.md             # Phase dependencies
├── implementation/
│   ├── ROADMAP.md                   # High-level roadmap
│   └── GOLDEN_PATH.md               # This implementation guide
├── technical/
│   ├── HYDROSTATICS.md              # Physics computation docs
│   ├── RESISTANCE.md                # Resistance methods
│   └── STABILITY.md                 # Stability calculations
└── agents/
    ├── PROMPT_ARCHITECTURE.md       # LLM context design
    ├── STATE_LENS.md                # What agents see
    └── GEOMETRY_SCHEMA.md           # Primitive reference
```

**Agent-Readable Header Template:**
```markdown
<!-- AGENT_CONTEXT
Purpose: [One sentence]
Authoritative: [Yes/No]
Depends_On: [List of files]
Used_By: [Which modules/agents reference this]
Last_Verified: [Date]
-->
```

**Acceptance Criteria:**
1. `docs/README.md` exists with links to all subdirectories.
2. All existing root `.md` files migrated to appropriate `docs/` subdirectory.
3. Every doc has `<!-- AGENT_CONTEXT -->` header.
4. `grep -r "AGENT_CONTEXT" docs/` returns >= 10 matches.
5. No orphan `.md` files in project root (except `README.md`, `CHANGELOG.md`).

**Dependencies:** TASK-000 (GEOMETRY_CONVENTIONS.md created first)

**Scope:** Medium

<!-- AGENT:START -->
Files: [docs/, *.md in project root]
Search: `*.md` files scattered in root
Pattern: Documentation exists but is not organized or agent-readable
Replace:
1. Create `docs/` directory structure
2. Create `docs/README.md` index
3. Migrate existing docs to correct subdirectory
4. Add AGENT_CONTEXT headers to all docs
5. Delete or redirect orphan root `.md` files
Verify:
- `ls docs/` shows README.md, architecture/, implementation/, technical/, agents/
- `grep -r "AGENT_CONTEXT" docs/ | wc -l` >= 10
<!-- AGENT:END -->

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
1. `pytest tests/webgl/test_geometry_pipeline.py::test_bow_convergence -v` passes with `assert max_y_at_bow < 0.001` (1mm convergence to centerline).
2. `pytest tests/webgl/test_geometry_pipeline.py::test_stern_closure -v` passes with `assert len(degenerate_faces) == 0` using a vertex tolerance of `1e-6`.
3. `trimesh.load('test_hull.glb').is_watertight` returns `True` for the hull shell below the sheer boundary.
4. `pytest tests/webgl/test_geometry_pipeline.py::test_no_horizontal_plate -v` passes with `assert face_normal_z < 0.9` for all bow-cap triangles (no horizontal plates).
5. Numerical integration of hull volume matches within 0.5% after capping.

**Dependencies:** None

**Scope:** Large

**Rollback:**
```bash
# Detect breakage: bow convergence or watertight failure
python3 -m pytest tests/webgl/test_geometry_pipeline.py::test_bow_convergence -v
# Restore state
git checkout HEAD~1 -- magnet/webgl/geometry_pipeline.py
# Verify restoration
python3 -m pytest tests/webgl/test_geometry_pipeline.py::test_bow_convergence -v
```

<!-- AGENT:START -->
Files: [magnet/webgl/geometry_pipeline.py]
Search: `_triangulate_end_cap`
Pattern: Function at L933-L1047 builds cap as two strips toward centerline
Replace: 
1. Add explicit terminal closure logic: if terminal section sheer width > threshold, insert synthetic converging section
2. Cap only up to "watertight top" (highest point below open deck boundary)
3. Fix degenerate triangle skipping: use proper tolerance for near-centerline points
Test Stub:
```python
def test_bow_convergence():
    sections = [create_section(station=0.0, width=5.0), create_section(station=1.0, width=0.1)]
    hull = tessellate(sections)
    # Assert bow point is effectively on centerline
    assert abs(hull.vertices[hull.bow_index][1]) < 0.001
```
Verify:
- `python3 -c "from magnet.webgl.geometry_pipeline import _triangulate_end_cap; print('import ok')"`
- Run: `pytest tests/webgl/test_geometry_pipeline.py::test_bow_convergence tests/webgl/test_geometry_pipeline.py::test_stern_closure tests/webgl/test_geometry_pipeline.py::test_no_horizontal_plate -v`
- Export GLB and verify with: `python3 -c "import trimesh; m=trimesh.load('test_hull.glb'); print('watertight:', m.is_watertight)"`
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

**Rollback:**
```bash
# Detect breakage: import error or missing priors
python3 -c "from magnet.kernel import priors; print(priors.HullFamily)"
# Restore file and imports
git checkout HEAD~1 -- magnet/kernel/priors/hull_families.py
git checkout HEAD~1 -- magnet/kernel/priors/__init__.py
```

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

**Dependencies:** None

**Scope:** Large

**Rollback:**
```bash
# Detect breakage: synthesis failure or KeyError
pytest tests/kernel/test_synthesis.py -v
# Restore files
git checkout HEAD~1 -- magnet/kernel/synthesis.py magnet/kernel/conductor.py
```

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

**Goal:** Refactor hydrostatics to use geometry-derived calculations instead of `hull_type` conditionals. Declare `geometry_hydrostatics.py` as authoritative.

**Files:**
- `magnet/physics/hydrostatics.py` (L317-L530)
- `magnet/physics/geometry_hydrostatics.py`
- `magnet/physics/validators.py` (L476-L496)
- `magnet/physics/resistance.py`
- `magnet/physics/savitsky.py`

**Problem Analysis:**
- `_estimate_cm()` branches on `hull_type == "deep_v"`, `"catamaran"` (L317-L457)
- `validators.py` maps strings "patrol", "workboat" → `HullType` enums
- This violates gate purity: hydrostatics should compute from geometry, not types
- `savitsky.py` is currently an orphan; it must be wired as a consequence of physics, not a category.

**Acceptance Criteria:**
1. `grep -c 'hull_type ==' magnet/physics/hydrostatics.py` returns 0.
2. `grep -c '"deep_v"\|"catamaran"' magnet/physics/hydrostatics.py` returns 0.
3. `geometry_hydrostatics.py` is the only module imported for `hull` phase validation.
4. `resistance.py` invokes `savitsky.py` based on `Froude Number > 0.5` and deadrise geometry, not categorical "Planing" selection.
5. `pytest tests/physics/test_hydrostatics.py -v` passes for both mono and multi-body without type branches.

**Dependencies:** None

**Scope:** Large

**Rollback:**
```bash
# Detect breakage: physics calculation error or 0.0 values
pytest tests/physics/test_hydrostatics.py -v
# Restore files
git checkout HEAD~1 -- magnet/physics/hydrostatics.py magnet/physics/validators.py magnet/physics/resistance.py
```

<!-- AGENT:START -->
Files: [magnet/physics/hydrostatics.py, magnet/physics/validators.py, magnet/physics/resistance.py, magnet/physics/savitsky.py]
Search: `hull_type ==`, `"deep_v"`, `"catamaran"`, `type_map`
Pattern: Conditional branches that select coefficients based on vessel type strings
Replace:
1. Implement `_compute_cm_from_geometry()` in `geometry_hydrostatics.py` using numerical integration:
```python
def _compute_cm_from_geometry(geometry: HullGeometry, draft: float) -> float:
    """
    Compute midship coefficient (Cm) from actual geometry.
    Formula: Cm = Am / (B * T)
    Am = max area of submerged sections
    B = waterline beam at max section
    T = draft
    """
    submerged_areas = []
    for section in geometry.sections:
        area = section.get_submerged_area(draft)
        submerged_areas.append(area)

    am = max(submerged_areas) if submerged_areas else 0
    beam_at_am = geometry.get_beam_at_max_section(draft)

    if beam_at_am > 0 and draft > 0:
        return am / (beam_at_am * draft)
    return 0.8  # Defined fallback behavior for pathological cases
```
2. Refactor `compute_hydrostatics_from_geometry()` to handle multi-body via parallel axis theorem:
```python
def _compute_multi_body_hydrostatics(geometry, bodies, draft, vcg):
    """
    I_total = Σ(I_local + A_wp × d²)
    """
    I_combined = 0.0
    V_total = 0.0
    for body_id, body in bodies.items():
        offset_y = body.get('offset_y_m', 0)
        I_local = _compute_body_waterplane_inertia(geometry, body_id, draft)
        A_wp = _compute_body_waterplane_area(geometry, body_id, draft)
        V_body = _compute_body_volume(geometry, body_id, draft)
        I_combined += I_local + A_wp * (offset_y ** 2)
        V_total += V_body
    BM = I_combined / V_total if V_total > 0 else 0
    KB = draft * 0.53
    GM = KB + BM - vcg
    return HydrostaticsResults(volume=V_total, gm=GM, method="geometry_derived")
```
3. Wire `savitsky.py` into `resistance.py`:
   - If computed `Fn > 0.5` AND geometry shows deadrise > 10°, call `SavitskyCalculator.calculate()`.
   - Results must be merged into `ResistanceResults` without changing the "method" to a categorical type.
4. Remove all `if hull_type == "..."` branches in all physics modules.
5. In validators.py: remove `type_map` dictionary; validate geometry directly.
Verify:
- `grep -E 'hull_type.*==|"deep_v"|"catamaran"|type_map' magnet/physics/` returns empty.
- `pytest tests/physics/test_hydrostatics.py -v`
<!-- AGENT:END -->

---

# P1 — Critical Tasks

---

## TASK-005: End-to-End UI Verification (Human Testable)

**Goal:** Verify a human can use the system through the browser UI. This is the operational proof that the architecture works.

**Pre-Conditions:**
- TASK-000 complete (coordinates locked)
- TASK-001 complete (hull renders)
- TASK-004 complete (hydrostatics works)

**Manual Test Checklist:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | `python -m magnet.deployment.api` | Server starts on port 8000 |
| 2 | Open `http://localhost:8000/` | Redirects to `/ui/v2/` |
| 3 | UI loads | No console errors, 3D viewport visible |
| 4 | Click "New Design" | Design created, design_id assigned |
| 5 | Type: "Create a 12m monohull" | Intent preview appears |
| 6 | Click "Apply" | Geometry compiles, 3D updates |
| 7 | Rotate 3D view | Hull visible, no wings, stern closed |
| 8 | Type: "Increase beam to 4m" | Preview shows change |
| 9 | Click "Apply" | Hull updates, version increments |
| 10 | Check hydrostatics panel | GM, displacement values shown |

**Automated Integration Test:**

Create `tests/integration/test_ui_spiral.py`:

```python
def test_full_spiral_loop():
    """User can complete a design spiral through the UI."""
    from fastapi.testclient import TestClient
    from magnet.deployment.api import app
    
    client = TestClient(app)
    
    # 1. Create design
    resp = client.post("/api/v1/designs", json={"name": "test"})
    assert resp.status_code == 200
    design_id = resp.json()["design_id"]
    
    # 2. Submit intent
    resp = client.post(f"/api/v1/designs/{design_id}/spiral/chat", 
                       json={"message": "Create a 12m monohull with 3.5m beam"})
    assert resp.status_code == 200
    assert resp.json().get("actions") or resp.json().get("program")
    
    # 3. Apply changes
    resp = client.post(f"/api/v1/designs/{design_id}/spiral/apply")
    assert resp.status_code == 200
    version_1 = resp.json().get("design_version", 1)
    
    # 4. Export geometry
    resp = client.get(f"/api/v1/designs/{design_id}/3d/export/glb")
    assert resp.status_code == 200
    assert len(resp.content) > 1000  # GLB has content
    
    # 5. Verify hydrostatics computed
    resp = client.get(f"/api/v1/designs/{design_id}")
    state = resp.json()
    gm = state.get("physics", {}).get("hydrostatics", {}).get("gm_m", 0)
    assert gm > 0 or state.get("hull", {}).get("gm_m", 0) > 0
    
    # 6. Modify and verify version increment
    resp = client.post(f"/api/v1/designs/{design_id}/spiral/chat",
                       json={"message": "Increase beam to 4m"})
    resp = client.post(f"/api/v1/designs/{design_id}/spiral/apply")
    version_2 = resp.json().get("design_version", 2)
    assert version_2 >= version_1
```

**Acceptance Criteria:**
1. Manual checklist passes (human verified).
2. `pytest tests/integration/test_ui_spiral.py -v` passes.
3. WebSocket events fire: `design_created`, `actions_executed`, `phase_completed`.
4. No JavaScript console errors in browser.
5. 3D viewer shows geometry without artifacts (no "wings", no "missing stern").

**Dependencies:** TASK-000, TASK-001, TASK-004

**Scope:** Medium

**Rollback:**
```bash
# If UI broken, revert last API change
git checkout HEAD~1 -- magnet/deployment/api.py magnet/deployment/spiral_endpoints.py
```

<!-- AGENT:START -->
Files: [tests/integration/test_ui_spiral.py (new), magnet/deployment/api.py]
Search: `/spiral/chat`, `/spiral/apply`, `3d/export`
Pattern: API endpoints exist but no end-to-end test
Replace:
1. Create `tests/integration/test_ui_spiral.py` with the test above.
2. Verify all endpoints return correct status codes.
3. Add WebSocket event assertions if applicable.
Verify:
- `pytest tests/integration/test_ui_spiral.py -v` passes
- Manual checklist completed by human
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

## TASK-014: Hull Quality Gates (Resolution + Fairness)

**Goal:** Implement advisory quality gates for hull resolution and fairness without auto-fixing geometry.

**Files:**
- `magnet/kernel/stdlib/quality_gates.py` (new)
- `magnet/kernel/stdlib/compiler.py`

**Scope:** Medium

**Acceptance Criteria:**
1. `quality_gates.py` defines `check_resolution()` and `check_fairness()`.
2. Fairness check detects inflection points and curvature spikes in sections.
3. Resolution check flags sections with < 16 or > 128 points as "ADVISORY_WARN".
4. Compiler runs gates post-compilation and appends warnings to `HullGeometry.metadata`.
5. Warnings do NOT block export or validation (Grade, not Gate).

<!-- AGENT:START -->
Files: [magnet/kernel/stdlib/quality_gates.py (new), magnet/kernel/stdlib/compiler.py]
Search: `compile_to_geometry`, `HullGeometry`
Pattern: Compilation returns geometry without quality metadata
Replace:
1. Create `quality_gates.py`:
```python
def check_resolution(sections: List[HullSection]) -> List[Warning]:
    warnings = []
    for s in sections:
        if len(s.points) < 16:
            warnings.append(Warning(f"Section {s.station}: {len(s.points)} points < 16 minimum"))
    return warnings

def check_fairness(sections: List[HullSection]) -> List[Warning]:
    # Detect curvature spikes via second derivative
    ...
```
2. Call from `compiler.py` after geometry compilation
3. Append warnings to `HullGeometry.metadata.quality_warnings`
Verify:
- `pytest tests/kernel/test_quality_gates.py -v`
- Low-resolution hull triggers warning (not error)
<!-- AGENT:END -->

---

## TASK-015: Token Efficiency via State Lens

**Goal:** Reduce LLM token usage by implementing a bounded "State Lens" instead of dumping full JSON state.

**Files:**
- `magnet/agents/state_lens.py` (new)
- `magnet/agents/geometry_proposer.py`

**Scope:** Medium

**Acceptance Criteria:**
1. `StateLens.extract(state, focus_paths)` returns a minimal subset of JSON state.
2. `geometry_proposer.py` uses lens to extract only `resources.geometry.*` and relevant physics results.
3. System prompt character count reduced by >= 40% while maintaining pass rate on `tests/agents/test_proposer.py`.
4. Total prompt tokens per request verified < 2500 tokens for average design.

<!-- AGENT:START -->
Files: [magnet/agents/state_lens.py (new), magnet/agents/geometry_proposer.py]
Search: `state.to_dict()`, `json.dumps(state)`
Pattern: Full state dumped to LLM prompt
Replace:
1. Create `state_lens.py`:
```python
def extract_lens(state: DesignState, focus: List[str] = None) -> dict:
    focus = focus or ["resources.geometry.*", "params.*", "physics.hydrostatics"]
    return {k: state.get(k) for k in state.keys() if any(fnmatch(k, f) for f in focus)}
```
2. Update `geometry_proposer.py` to use `extract_lens()` instead of full state
Verify:
- `python3 -c "from magnet.agents.state_lens import extract_lens; print('ok')"`
- Prompt token count < 2500 for standard design
<!-- AGENT:END -->

---

## TASK-016: ASK Disambiguation Operation

**Goal:** Implement explicit ASK operation in DSL to handle ambiguous human intent without guessing.

**Files:**
- `magnet/kernel/stdlib/type_registry.py`
- `magnet/agents/geometry_proposer.py`
- `magnet/kernel/program_executor.py`

**Scope:** Small

**Acceptance Criteria:**
1. DSL supports `ASK "question text" { options: [...] }`.
2. `program_executor.py` intercepts `ASK` and returns `ExecutionResult(success=False, needs_clarification=True)`.
3. `geometry_proposer.py` emits `ASK` when LLM confidence is below threshold.
4. Unit test: `execute_program('ASK "How many hulls?" { options: ["1", "2"] }')` returns structured clarification request.

<!-- AGENT:START -->
Files: [magnet/kernel/stdlib/type_registry.py, magnet/kernel/program_executor.py, magnet/agents/geometry_proposer.py]
Search: `OperationType`, `execute_operation`
Pattern: No ASK operation type exists
Replace:
1. Add `ASK` to operation types in type_registry.py
2. In program_executor.py, handle ASK:
```python
if op.type == "ASK":
    return ExecutionResult(
        success=False,
        needs_clarification=True,
        clarification={"question": op.question, "options": op.options}
    )
```
3. In geometry_proposer.py, emit ASK when confidence < threshold
Verify:
- `pytest tests/kernel/test_program_executor.py -k ask -v`
<!-- AGENT:END -->

---

## TASK-017: Remove Type Factors from Weight Estimation

**Goal:** Derive weight factors from geometry (body count, L/B ratio) instead of `hull_type` enums.

**Files:**
- `magnet/weight/estimators/hull.py` (L39-L112)

**Acceptance Criteria:**
1. `grep -c "HULL_TYPE_FACTORS" magnet/weight/estimators/hull.py` returns 0.
2. `get_hull_factor_from_geometry()` is the sole provider of weight multipliers.
3. Unit test verifies that a multi-body configuration receives the correct structural weight penalty regardless of what it is named.

**Dependencies:** TASK-004 (Pattern reference)

**Scope:** Medium

**Rollback:**
```bash
# Detect breakage: weight estimation returns NaN or 0
pytest tests/weight/test_hull_weight.py -v
# Restore file
git checkout HEAD~1 -- magnet/weight/estimators/hull.py
```

<!-- AGENT:START -->
Files: [magnet/weight/estimators/hull.py]
Search: `HULL_TYPE_FACTORS`
Pattern: Dictionary mapping "monohull", "catamaran" etc. to weight factors.
Replace:
1. Delete `HULL_TYPE_FACTORS`.
2. Ensure `estimate()` calls `get_hull_factor_from_geometry()`.
3. Verify `body_count` and `lb_ratio` are correctly passed from the geometry resource.
<!-- AGENT:END -->

---

## TASK-018: Geometry-Pure Cost Scaling

**Goal:** Restrict cost branching to organizational intent (military/civilian) and derive effort from geometric complexity.

**Files:**
- `magnet/cost/estimator.py` (L115-L150)

**Acceptance Criteria:**
1. `_estimate_engineering()` does not branch on `vessel_type` strings like "patrol" or "workboat" for complexity scaling.
2. Scaling factor is derived from `compartment_count`, `body_count`, and `weld_length_m`.
3. "Organizational Intent" (military vs commercial) remains as the only categorical branch.

**Dependencies:** None

**Scope:** Medium

**Rollback:**
```bash
# Detect breakage: cost estimation failure
pytest tests/cost/test_estimator.py -v
# Restore file
git checkout HEAD~1 -- magnet/cost/estimator.py
```

<!-- AGENT:START -->
Files: [magnet/cost/estimator.py]
Search: `_estimate_engineering`
Pattern: Branching on vessel_type strings for complexity.
Replace:
1. Replace `if vessel_type in ["military", "naval", "patrol"]:` with `if mission.organization == "military":`.
2. Add complexity factor: `base_hours *= (1.0 + 0.1 * body_count) * (1.0 + 0.05 * compartment_count)`.
<!-- AGENT:END -->

---

## TASK-019: Integrated GZ Cross-Curves (Future Truth)

**Goal:** Acknowledge the wall-sided formula as a "temporary lie" and prepare for mesh-integrated stability.

**Files:**
- `magnet/stability/gz_curve.py` (L136-L262)

**Acceptance Criteria:**
1. `gz_curve.py` docstring explicitly names the wall-sided formula as an approximation.
2. Stability results include a `stability_confidence` metric based on heel angle.
3. `GZCurveCalculator` includes a stubbed `_calculate_gz_from_mesh()` to signal the intended path.
4. `pytest tests/stability/test_gz_curve.py::test_confidence_degrades_with_heel -v` passes.

**Dependencies:** TASK-004

**Scope:** Small

<!-- AGENT:START -->
Files: [magnet/stability/gz_curve.py]
Search: `class GZCurveCalculator`
Pattern: Documentation implying the wall-sided formula is absolute.
Replace:
1. Update docstring: "Implements wall-sided formula (approximation). Temporary lie until cross-curve integration is implemented."
2. Add `stability_confidence`: decreases as `heel_angle` approaches `downflooding_angle`.
3. Insert `_calculate_gz_from_mesh` stub.
<!-- AGENT:END -->

---

# P0-Production — Ship-Blocking Tasks

Without these, the product is **broken on first real use**.

---

## TASK-020: Persistence — Design Survives Restart

**Goal:** User's work is not lost when server restarts.

**Problem:** Currently, `StateManager` is in-memory. Server restart = all designs gone.

**Files:**
- `magnet/core/state_manager.py`
- `magnet/storage/design_store.py` (new)
- `magnet/deployment/api.py` (startup/shutdown hooks)

**Acceptance Criteria:**
1. `python -m magnet.deployment.api` → create design → restart server → design still exists.
2. `storage/designs/{design_id}/state.json` contains serialized `DesignState`.
3. Designs load on server startup from disk.
4. Concurrent writes don't corrupt state (file locking or atomic write).
5. `pytest tests/integration/test_persistence.py -v` passes.

**Test:**
```python
def test_design_survives_restart():
    client = TestClient(app)
    
    # Create design
    resp = client.post("/api/v1/designs", json={"name": "persist_test"})
    design_id = resp.json()["design_id"]
    
    # Modify it
    client.post(f"/api/v1/designs/{design_id}/spiral/chat", 
                json={"message": "Create 12m monohull"})
    client.post(f"/api/v1/designs/{design_id}/spiral/apply")
    
    # Simulate restart (reinitialize state manager)
    from magnet.core.state_manager import StateManager
    StateManager._instance = None  # Force reload
    
    # Verify design exists
    resp = client.get(f"/api/v1/designs/{design_id}")
    assert resp.status_code == 200
    assert resp.json()["hull"]["loa_m"] == 12.0
```

**Dependencies:** None (can run in parallel with Phase 1)

**Scope:** Large

**Rollback:**
```bash
git checkout HEAD~1 -- magnet/core/state_manager.py magnet/storage/
```

<!-- AGENT:START -->
Files: [magnet/core/state_manager.py, magnet/storage/design_store.py (new)]
Search: `class StateManager`, `_designs`, `self.designs`
Pattern: In-memory dictionary with no persistence
Replace:
1. Add `save_to_disk(design_id)` method that writes JSON to `storage/designs/{design_id}/state.json`
2. Add `load_from_disk(design_id)` method
3. Add `load_all_designs()` called on startup
4. Use atomic write (write to `.tmp`, then rename)
5. Add file locking for concurrent access
Verify:
- `ls storage/designs/` shows design folders after creation
- `pytest tests/integration/test_persistence.py -v`
<!-- AGENT:END -->

---

## TASK-021: Agent Guardrails — Reject Absurd Geometry

**Goal:** LLM proposals that are technically valid but physically absurd are rejected with explanation.

**Problem:** LLM can propose `beam: 500m`, `draft: -2m`, `LOA: 0.5m` — all compile but are nonsense.

**Files:**
- `magnet/kernel/validators/sanity.py` (new)
- `magnet/kernel/program_executor.py`

**Guardrail Rules:**

| Parameter | Sane Range | Error Message |
|-----------|------------|---------------|
| LOA | 3m - 500m | "LOA {value}m is outside realistic vessel range (3-500m)" |
| Beam | 0.1 × LOA - 0.5 × LOA | "Beam {value}m is {ratio}× LOA — typical range is 0.1-0.5× LOA" |
| Draft | 0.02 × LOA - 0.2 × LOA | "Draft {value}m is unrealistic for {loa}m vessel" |
| Draft | > 0 | "Draft cannot be negative" |
| Fn | 0 - 3.0 | "Froude number {value} exceeds hydrofoil range" |
| Deadrise | 0° - 45° | "Deadrise {value}° is outside typical range" |
| Section count | 7 - 200 | "Section count {value} is outside valid range" |
| Body count | 1 - 5 | "Body count {value} exceeds supported configurations" |

**Acceptance Criteria:**
1. `execute_program()` runs sanity check before applying changes.
2. Absurd proposals return `ExecutionResult(success=False, errors=["Beam 500m is 50× LOA..."])`.
3. User sees actionable message, not stack trace.
4. Guardrails are ADVISORY (warn) below threshold, GATE (reject) above hard limit.
5. `pytest tests/kernel/test_sanity_guardrails.py -v` passes.

**Dependencies:** TASK-004 (needs physics)

**Scope:** Medium

<!-- AGENT:START -->
Files: [magnet/kernel/validators/sanity.py (new), magnet/kernel/program_executor.py]
Search: `execute_program`, `apply_action`
Pattern: Actions applied without sanity check
Replace:
1. Create `magnet/kernel/validators/sanity.py` with HARD_LIMITS and SOFT_LIMITS
2. Call `check_sanity()` in `program_executor.py` before `state_manager.set()`
3. Accumulate warnings, reject on errors
Verify:
- `pytest tests/kernel/test_sanity_guardrails.py -v`
<!-- AGENT:END -->

---

## TASK-022: Error UX — Failures Show Actionable Messages

**Goal:** When anything fails, user sees a helpful message, not a stack trace or generic "Error".

**Files:**
- `magnet/deployment/api.py` (exception handlers)
- `magnet/deployment/error_handlers.py` (new)

**Error Categories:**

| Error Type | Current UX | Required UX |
|------------|------------|-------------|
| Negative GM | `ValueError: math domain error` | "Hull is unstable (GM = -0.3m). Increase beam or reduce VCG." |
| Zero volume | `ZeroDivisionError` | "Hull has no submerged volume at this draft." |
| LLM timeout | `TimeoutError` | "AI is taking too long. Try a simpler request." |
| API 429 | `RateLimitError` | "Too many requests. Please wait 30 seconds." |
| Compile fail | `GeometryError` | "Sections don't form valid hull. Check section ordering." |

**Acceptance Criteria:**
1. No Python exception names visible to user.
2. Every error includes: what went wrong, why, and suggested fix.
3. Errors are logged server-side with full stack trace.
4. User-facing errors are structured JSON: `{"error": "...", "suggestion": "...", "code": "E001"}`.
5. `pytest tests/deployment/test_error_handlers.py -v` passes.

**Dependencies:** TASK-004, TASK-021

**Scope:** Medium

<!-- AGENT:START -->
Files: [magnet/deployment/api.py, magnet/deployment/error_handlers.py (new)]
Search: `@app.exception_handler`, `raise`, `HTTPException`
Pattern: Exceptions bubble up with developer messages
Replace:
1. Create `error_handlers.py` with user-friendly error mapping
2. Add global exception handler in `api.py`
3. Log full exception server-side, return sanitized error to user
Verify:
- `pytest tests/deployment/test_error_handlers.py -v`
- No Python exception names in any API response
<!-- AGENT:END -->

---

## TASK-023: Negative GM Handling — Warn, Don't Crash

**Goal:** When stability is negative, the system warns the user with explanation instead of crashing.

**Problem:** Negative GM causes `math.sqrt(negative)` → crash. User sees 500 error.

**Files:**
- `magnet/physics/geometry_hydrostatics.py`
- `magnet/physics/validators.py`

**Acceptance Criteria:**
1. Negative GM returns valid `HydrostaticsResults` with `gm_m=-0.3` (actual value).
2. Results include `warnings=["Hull is unstable (GM=-0.3m). Minimum recommended: 0.5m"]`.
3. Results include `stable=False` boolean.
4. UI shows warning banner, not error.
5. Physics pipeline does not throw exception.
6. `pytest tests/physics/test_negative_stability.py -v` passes.

**Dependencies:** TASK-004

**Scope:** Small

<!-- AGENT:START -->
Files: [magnet/physics/geometry_hydrostatics.py]
Search: `sqrt`, `math.sqrt`, `GM =`
Pattern: Calculation assumes GM is positive
Replace:
1. Remove any `sqrt(GM)` or similar that breaks on negative
2. Add `stable = gm > 0` to results
3. Add warning when `gm < 0.5`
Verify:
- `pytest tests/physics/test_negative_stability.py -v`
<!-- AGENT:END -->

---

# P1-Production — User Abandonment Blockers

Without these, users will abandon after first session.

---

## TASK-024: Undo/Redo — User Can Revert Changes

**Goal:** User can undo the last change and redo it.

**Files:**
- `magnet/core/state_manager.py`
- `magnet/deployment/spiral_endpoints.py`

**Acceptance Criteria:**
1. `POST /api/v1/designs/{id}/undo` reverts to previous version.
2. `POST /api/v1/designs/{id}/redo` re-applies reverted change.
3. Undo stack holds last 20 states.
4. UI shows undo/redo buttons that are enabled/disabled appropriately.
5. `pytest tests/integration/test_undo_redo.py -v` passes.

**Dependencies:** TASK-020 (persistence)

**Scope:** Medium

<!-- AGENT:START -->
Files: [magnet/core/state_manager.py, magnet/deployment/spiral_endpoints.py]
Search: `design_version`, `history`, `snapshot`
Pattern: No version history stored
Replace:
1. Add `_history: Dict[str, List[DesignState]]` to StateManager
2. Save state to history before each mutation
3. Add `undo()` and `redo()` methods
4. Add `/undo` and `/redo` endpoints
Verify:
- `pytest tests/integration/test_undo_redo.py -v`
<!-- AGENT:END -->

---

## TASK-025: Loading Indicators — User Knows System Is Working

**Goal:** User sees progress indication during LLM calls and geometry compilation.

**Files:**
- `magnet/ui_v2/` (frontend)
- `magnet/deployment/spiral_endpoints.py` (SSE or WebSocket progress)

**Acceptance Criteria:**
1. "Thinking..." appears during LLM call.
2. "Compiling geometry..." appears during hull build.
3. "Validating physics..." appears during hydrostatics.
4. Progress disappears when complete.
5. If > 10 seconds, show "This is taking longer than usual...".

**Dependencies:** TASK-005

**Scope:** Small

<!-- AGENT:START -->
Files: [magnet/ui_v2/js/chat.js, magnet/deployment/spiral_endpoints.py]
Search: `loading`, `spinner`, `progress`
Pattern: No loading state during async operations
Replace:
1. Add loading state to chat component
2. Show phase-specific messages based on operation
3. Add timeout warning after 10 seconds
Verify:
- Manual: Submit intent, see "Thinking..." appear
<!-- AGENT:END -->

---

## TASK-026: API Failure Handling — Graceful Degradation

**Goal:** When LLM API fails, system retries, then shows graceful error.

**Files:**
- `magnet/agents/geometry_proposer.py`
- `magnet/llm/client.py`

**Acceptance Criteria:**
1. 429 (rate limit) → retry after `Retry-After` header, max 3 times.
2. 500 (server error) → retry once after 2 seconds.
3. Timeout → show "AI is not responding. Try again or simplify request."
4. No API key → show "AI service not configured. Check ANTHROPIC_API_KEY."
5. All failures logged with request context.

**Dependencies:** None

**Scope:** Small

<!-- AGENT:START -->
Files: [magnet/llm/client.py, magnet/agents/geometry_proposer.py]
Search: `anthropic`, `openai`, `api_key`, `request`
Pattern: No retry logic, raw exceptions bubble up
Replace:
1. Add retry decorator with exponential backoff
2. Catch specific exceptions (RateLimitError, Timeout, etc.)
3. Return user-friendly error messages
Verify:
- Mock API failure, verify retry and graceful error
<!-- AGENT:END -->

---

# The PhaseMachine: Dependency of Consequences

The PhaseMachine is not a design taxonomy. It is not a catalog of "ship types." It is a **dependency graph of consequences**. 

A change in geometry (Phase 2) ripples through weight (Phase 5) and stability (Phase 6) because the laws of physics require it, not because a "vessel type" has been selected. If a phase does not consume the output of an upstream phase, it is orphaned and must be re-evaluated.

---

# Dependency Graph

```
TASK-000 (coordinate convention)
    └── None (BLOCKS ALL P0)

TASK-000b (tolerances)
    └── TASK-000

TASK-000c (physical ownership)
    └── TASK-000, TASK-004

TASK-000d (documentation structure)
    └── TASK-000

TASK-001 (hull caps)
    └── TASK-000, TASK-000b

TASK-003 (synthesis enumeration)
    └── None

TASK-002 (remove hull_families.py)
    └── TASK-003

TASK-004 (hydrostatics)
    └── None

TASK-005 (UI integration)
    └── TASK-000, TASK-001, TASK-004

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

TASK-014 (quality gates)
    └── TASK-001

TASK-015 (state lens)
    └── None

TASK-016 (ASK disambiguation)
    └── None

TASK-017 (weight enumeration)
    └── TASK-004 (Pattern reference)

TASK-018 (cost enumeration)
    └── None

TASK-019 (stability approx)
    └── TASK-004 (Needs hydrostatics refactor)

TASK-020 (persistence)
    └── None (parallel with Phase 1)

TASK-021 (agent guardrails)
    └── TASK-004

TASK-022 (error UX)
    └── TASK-004, TASK-021

TASK-023 (negative GM)
    └── TASK-004

TASK-024 (undo/redo)
    └── TASK-020

TASK-025 (loading indicators)
    └── TASK-005

TASK-026 (API failure)
    └── None
```

---

# Execution Order (Recommended)

## Phase 0: Foundation — Coordinate & Ownership Lock

1. **TASK-000** — Resolve coordinate conventions (BLOCKS ALL)
2. **TASK-000b** — Centralize tolerances
3. **TASK-000c** — Unified physical ownership
4. **TASK-000d** — Establish documentation structure

### 🚩 GATE 0: Foundation Lock
- [ ] `docs/architecture/GEOMETRY_CONVENTIONS.md` exists and is referenced.
- [ ] `grep "1e-" magnet/webgl/ magnet/hull_gen/` returns 0 matches.
- [ ] `hull.displacement_mt` is written by exactly one module.
- [ ] `docs/README.md` exists with index to all documentation.

## Phase 1: P0 Blocking — Generative Foundation

5. **TASK-001** — Fix hull end-cap
6. **TASK-003** — Remove synthesis enumeration
7. **TASK-004** — Remove hydrostatics type branches
8. **TASK-002** — Remove hull_families.py (after TASK-003)

### 🚩 GATE 1: Generative Purity
- [ ] `docs/architecture/GEOMETRY_CONVENTIONS.md` exists and matches code.
- [ ] `grep -rE "HullFamily|FAMILY_PRIORS" magnet/kernel/` returns 0 matches.
- [ ] `pytest tests/physics/test_hydrostatics.py` passes for multi-body without type branches.
- [ ] Hull renders as watertight shell below sheer.

## Phase 1.5: UI Integration Verification

9. **TASK-005** — End-to-end UI verification (human testable)

### 🚩 GATE 1.5: Human Can Use System
- [ ] Server starts: `python -m magnet.deployment.api` runs on port 8000.
- [ ] Browser loads: `http://localhost:8000/` redirects to `/ui/v2/`.
- [ ] 3D viewer shows hull without artifacts.
- [ ] Spiral loop works: intent → preview → apply → geometry update.

## Phase 2: Production Blockers — Ship-Blocking

10. **TASK-020** — Persistence (design survives restart)
11. **TASK-021** — Agent guardrails (reject absurd geometry)
12. **TASK-022** — Error UX (actionable messages)
13. **TASK-023** — Negative GM handling (warn, don't crash)

### 🚩 GATE 2: Product Not Broken
- [ ] Design survives server restart.
- [ ] `beam=500m` is rejected with explanation.
- [ ] Negative GM shows warning, not crash.
- [ ] No Python exceptions visible to user.

## Phase 3: Production Polish — Abandonment Blockers

14. **TASK-024** — Undo/Redo
15. **TASK-025** — Loading indicators
16. **TASK-026** — API failure handling
17. **TASK-006** — Transform reporting
18. **TASK-007** — Dual control plane
19. **TASK-008** — Lock enforcement

### 🚩 GATE 3: User Won't Abandon
- [ ] User can undo last change.
- [ ] Loading indicator during LLM call.
- [ ] API failure shows retry message.

## Phase 4: Interface Cleanup

20. **TASK-009** — Remove app/
21. **TASK-010** — Remove frontend/
22. **TASK-011** — Remove kernel analysis enumeration
23. **TASK-012** — Remove webgl interfaces enumeration
24. **TASK-013** — Remove migration endpoint enumeration
25. **TASK-014** — Hull quality gates
26. **TASK-015** — Token efficiency via State Lens
27. **TASK-016** — ASK Disambiguation
28. **TASK-017** — Weight enumeration removal
29. **TASK-018** — Cost enumeration removal
30. **TASK-019** — Stability acknowledgment

### 🚩 GATE 4: Production Ready
- [ ] No references to `app/` or `frontend/` in codebase.
- [ ] Quality gates provide inflection warnings for poor geometry.
- [ ] Full system test `pytest tests/` (excluding integration) passes.
- [ ] All enumeration removed from kernel.

---

# Test Verification (Pre-Implementation Audit)

**Before executing tasks, verify which tests exist vs. need creation.**

## Tests Referenced in Guide

| Test | File | Exists? | Action |
|------|------|---------|--------|
| `test_bow_convergence` | `tests/webgl/test_geometry_pipeline.py` | ❌ **No** | Must create in TASK-001 |
| `test_stern_closure` | `tests/webgl/test_geometry_pipeline.py` | ❌ **No** | Must create in TASK-001 |
| `test_no_horizontal_plate` | `tests/webgl/test_geometry_pipeline.py` | ❌ **No** | Must create in TASK-001 |
| `test_hydrostatics` | `tests/physics/test_hydrostatics.py` | ❌ **No** | Must create (unit tests exist) |
| `test_full_spiral_loop` | `tests/integration/test_ui_spiral.py` | ❌ **No** | Must create in TASK-005 |
| `test_quality_gates` | `tests/kernel/test_quality_gates.py` | ❌ **No** | Must create in TASK-014 |
| `test_program_executor` | `tests/kernel/test_program_executor.py` | ❓ **Check** | May exist |
| `test_persistence` | `tests/integration/test_persistence.py` | ❌ **No** | Must create in TASK-020 |
| `test_sanity_guardrails` | `tests/kernel/test_sanity_guardrails.py` | ❌ **No** | Must create in TASK-021 |
| `test_error_handlers` | `tests/deployment/test_error_handlers.py` | ❌ **No** | Must create in TASK-022 |
| `test_negative_stability` | `tests/physics/test_negative_stability.py` | ❌ **No** | Must create in TASK-023 |
| `test_undo_redo` | `tests/integration/test_undo_redo.py` | ❌ **No** | Must create in TASK-024 |

## Tests That DO Exist

| Test | File | Status |
|------|------|--------|
| `test_golden_path.py` | `tests/integration/` | ✅ Exists |
| `test_hull_synthesis.py` | `tests/integration/` | ✅ Exists |
| `test_physics_pipeline.py` | `tests/integration/` | ✅ Exists |
| `test_stability_pipeline.py` | `tests/integration/` | ✅ Exists |
| `test_geometry_service.py` | `tests/webgl/` | ✅ Exists |
| `test_exporter.py` | `tests/webgl/` | ✅ Exists |
| `test_api_undo_restore.py` | `tests/integration/` | ✅ Exists (may cover TASK-024) |

## Audit Command

```bash
# Run before starting implementation:
pytest tests/ --collect-only 2>/dev/null | grep "test_bow\|test_stern\|test_spiral\|test_persist\|test_sanity\|test_undo" || echo "Tests do not exist yet"
```

---

# Success Criteria (Final Validation)

Run these checks after all tasks complete:

```bash
# 1. Hull renders as closed watertight shell (open top)
pytest tests/webgl/test_geometry_pipeline.py -v -k "cap or manifold"

# 2. No enumeration in kernel or physics
grep -rE "HullFamily|FAMILY_PRIORS|hull_type.*==" magnet/kernel/ magnet/physics/
# Expected: empty output

# 3. Hydrostatics Verification (Geometry-Derived)
python3 -m pytest tests/physics/test_hydrostatics.py -v
# Ensure GM and BM are computed for multi-body via parallel axis

# 4. Coordinate conventions are consistent
grep -A2 '"x":' magnet/agents/geometry_schema.json
# Expected: "0=stern (AP), LOA=bow (FP)"

# 5. Transforms are reported, not silent
grep "transform_report" magnet/kernel/stdlib/section_compiler.py
# Expected: at least 1 match

# 6. All tests pass
pytest tests/ -v --ignore=tests/integration/
```

---

# Audit Instrumentation (Conceptual Risk Mitigation)

The following audit steps must be performed during or after implementation to mitigate generative-vs-enumerative risks:

1. **Implicit Enumeration Leakage Audit**
   - Run `grep -rE "Fn >|L/B >|speed >" magnet/kernel/` to detect regime-based branching.
   - Requirement: Regime-based logic must be ADVISORY only, never used for kernel selection/defaults.

2. **Geometry-Derived Prior Validity**
   - Verify that any "shape descriptors" used in analysis (e.g., Cb, Cp) are computed purely from geometry primitives.
   - Command: `python3 -c "from magnet.kernel.analysis import compute_metrics; print(compute_metrics(sample_hull))"` must not require `hull_type`.

3. **Kernel Silent Mutation Detection**
   - Audit `compile_section` and `tessellate` for `clamp`, `smooth`, or `auto-fix` behavior.
   - Requirement: Any mutation must be recorded in `transform_report`. Reject invalid inputs over silent correction.

4. **Many-to-One Compiler Collapse**
   - Add test ensuring two distinct construction paths (e.g., different section ordering) that produce the same shape do not canonicalize to an enumerated type.

5. **Adversarial Geometry Rejection**
   - Add tests for pathological but valid inputs (e.g., zero-thickness sections).
   - Requirement: Kernel must reject (error) rather than attempt to "repair" and proceed.

6. **Iteration Bias Detection**
   - Run 100-iteration loops on `GeometryProposer` and measure entropy of generated parameters.
   - Requirement: Parameters should not collapse to a set of fixed "style priors".

7. **Agent–Kernel Information Firewall**
   - Verify that no intermediate solver state (e.g., optimization residuals) is exposed to agents.
   - Requirement: Only final computed metrics and validated geometry are allowed in the `State Lens`.

8. **Novelty Falsifiability**
   - Declaration: If adding a "Trimaran" requires a new `HullType` enum entry to get correct stability, the system is declared *enumerated* and the task fails.

9. **Validator Neutrality & Composability**
   - Document that validators (Hydrostatics, Resistance) only remove physically impossible designs (e.g., negative volume).
   - All other checks (fairness, buildability) must be marked as ADVISORY.

10. **Responsibility Boundary**
    - The **Kernel** is responsible for "Is this a valid physical object?".
    - The **Agent** is responsible for "Is this what the user wanted?".
    - The **Human** is responsible for "Is this a good design?".

11. **The Conditional Alarm (Structural Entropy Detection)**
    - Run `grep -r "if .*==" magnet/kernel/` and compare against a baseline count.
    - Requirement: Any *new* conditional in kernel logic that checks for a string literal (e.g., `if hull_type == "..."`) must trigger an immediate architectural review. Enums should not return one `if` at a time.

12. **Bypass & Fast-Path Audit**
    - Audit kernel code for `bypass_validation`, `skip_physics`, or `force_success` flags.
    - Requirement: These are "Iteration Pressure" traps. They must be removed from the production kernel or require a privileged override that is logged.

13. **"Do Nothing" Idempotency**
    - Requirement: Submitting an empty program or a program that repeats the current state must return `success=True` but result in **zero changes** to the design state and zero new entries in `transform_report`.

---

# Architectural Falsifiability (Failure Definitions)

The "generative geometry + validating kernel" approach is declared **fundamentally flawed** if any of the following conditions are met:

1.  **The "Trimaran" Enum Re-entry:** If calculating correct stability for a 3-body configuration (Trimaran) requires adding `"TRIMARAN"` to a kernel enum because the general-purpose physics (Parallel Axis Theorem + numerical integration) fails to produce accurate results.
2.  **Representational Insufficiency:** If a standard industry hull (e.g., Damen Stan Patrol 4207) cannot be represented within 1% volumetric and fairness accuracy using only the 7 universal primitives (`section`, `surface`, `body`, `discontinuity`, `opening`, `flow_path`, `attachment`).
3.  **Heuristic Dependency:** If the kernel requires knowing the **Vessel Type** (Intent) to determine the **Submerged Area** (Reality). If `hull_type` is ever a required input for a physics calculator, the generative thesis has collapsed into enumeration.
4.  **Convergence Floor:** If an agent (Claude 3.5/4) cannot produce a valid, non-self-intersecting hull from a natural language prompt in < 5 iterations. This would prove the "compositional language" is too complex for autonomous reasoning.
5.  **Performance Death:** If the time to compile geometry and run hydrostatics on a 3-body design exceeds 5 seconds on standard hardware, breaking the "interactive design spiral" requirement.

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
| `magnet/physics/geometry_hydrostatics.py` | TASK-004, TASK-000c |
| `magnet/agents/geometry_schema.json` | TASK-000 |
| `magnet/kernel/stdlib/section_compiler.py` | TASK-000, TASK-006 |
| `magnet/webgl/interfaces.py` | TASK-000, TASK-012 |
| `magnet/deployment/api.py` | TASK-007 |
| `magnet/deployment/spiral_endpoints.py` | TASK-007, TASK-013 |
| `magnet/kernel/stdlib/quality_gates.py` | TASK-014 |
| `magnet/agents/state_lens.py` | TASK-015 |
| `magnet/kernel/stdlib/type_registry.py` | TASK-016 |
| `magnet/kernel/program_executor.py` | TASK-008, TASK-016 |
| `magnet/core/state_manager.py` | TASK-008 |
| `app/` | TASK-009 |
| `frontend/` | TASK-010 |
| `magnet/kernel/analysis.py` | TASK-011 |
| `magnet/weight/estimators/hull.py` | TASK-017 |
| `magnet/cost/estimator.py` | TASK-018 |
| `magnet/stability/gz_curve.py` | TASK-019 |
| `magnet/agents/geometry_proposer.py` | TASK-000, TASK-015, TASK-016 |
| `magnet/weight/summary_generator.py` | TASK-000c |
| `magnet/reporting/generators/design_summary.py` | TASK-000c |
| `magnet/core/design_state.py` | TASK-000c |
| `magnet/core/constants.py` | TASK-000b |
| `tests/integration/test_ui_spiral.py` | TASK-005 (new) |
| `tests/webgl/test_geometry_pipeline.py` | TASK-001 (must add tests) |
| `docs/` | TASK-000d (new structure) |
| `magnet/storage/design_store.py` | TASK-020 (new) |
| `magnet/kernel/validators/sanity.py` | TASK-021 (new) |
| `magnet/deployment/error_handlers.py` | TASK-022 (new) |
| `tests/integration/test_persistence.py` | TASK-020 (new) |
| `tests/kernel/test_sanity_guardrails.py` | TASK-021 (new) |
| `tests/deployment/test_error_handlers.py` | TASK-022 (new) |
| `tests/physics/test_negative_stability.py` | TASK-023 (new) |
| `tests/integration/test_undo_redo.py` | TASK-024 (new) |

---

> When geometry is no longer sufficient, enumeration will try to return disguised as convenience.
