# MAGNET Critical Corrections Plan

**Created:** 2026-01-06  
**Status:** Pre-Implementation Audit  
**Reference:** Post-implementation audit of MAGNET_Merge_Implementation_Plan.md

---

## ⚠️ EXECUTION CHECKLIST — DO NOT SKIP STEPS

**Total Effort:** 72 hours (~9 days full-time)  
**Critical Path:** Q1 (primitive completeness) MUST pass before proceeding  
**Full Context:** See detailed sections below for implementation details

### 🔴 WEEK 1: EXISTENTIAL + SECURITY (42.5 hours)

#### Day 1-2: Q1 Primitive Completeness (16h) — **THE BLOCKER**

**⚠️ IF THIS FAILS, STOP AND REASSESS ARCHITECTURE**

- [ ] Create `tests/validation/test_primitive_completeness.py`
- [ ] Define `REAL_VESSELS` list (10 vessels):
  - Damen Stan Patrol 4207
  - Austal 102m Trimaran Ferry
  - SAFE Boats Mk VI
  - Workboat with bow thruster
  - + 6 more covering diverse features
- [ ] For each vessel:
  - [ ] Document critical features
  - [ ] Attempt DSL expression using 7 primitives
  - [ ] Calculate expressibility coverage
- [ ] **DECISION GATE:** Coverage ≥ 75% for ≥8/10 vessels?
  - **YES:** Continue to Day 3
  - **NO:** STOP — Escalate to human, reassess architecture
- [ ] Document gaps using decision framework (Part XIII Q1):
  - Option A: Extend existing primitive?
  - Option B: Compose from multiple primitives?
  - Option C: Add new primitive (violates invariant)?
  - Option D: Declare out of scope?

**Reference:** Part XIII Q1 (lines 1400-1500)

#### Day 3: Q5 Parallel Axis Validation (4h)

- [ ] Find published catamaran hydrostatics data (Austal 40m or similar)
- [ ] Create `tests/validation/test_catamaran_reference.py`
- [ ] Model reference catamaran in MAGNET DSL
- [ ] Run `compute_hydrostatics_from_geometry()`
- [ ] **VALIDATE:** GM within ±10% of published value
- [ ] If wrong: Debug parallel axis theorem implementation
- [ ] Add warning if multi-body hydrostatics unvalidated

**Reference:** Part XIII Q5 (lines 1650-1750)

#### Day 4: Q10 Prompt Injection (4h)

- [ ] Create `magnet/agents/vision_interpreter.py::_sanitize_annotations()`
  - Remove SQL patterns (`DROP TABLE`, `DELETE FROM`)
  - Remove instruction override (`ignore previous`, `instead output`)
- [ ] Add schema enforcement in `interpret_sketch()`:
  - Force JSON schema output only
  - Validate extracted values (body_count < 10, loa < 300m)
- [ ] Create `tests/security/test_prompt_injection.py`:
  - SQL injection attempts
  - Instruction override attempts
  - Code injection in intent_string
- [ ] Add audit logging for suspicious interpretations

**Reference:** Part XIII Q10 (lines 1850-1950)

#### Day 5: Issue 1.1 Sketch → GLB Adapter (4h)

- [ ] Create `magnet/webgl/geometry_adapter.py`:
  - `hull_geometry_to_webgl(geometry: HullGeometry) -> HullGeometryData`
  - Convert sections, extract dimensions
- [ ] Update `magnet/deployment/api.py` in `post_design_sketch()`:
  ```python
  if result.geometry:
      webgl_geom = hull_geometry_to_webgl(result.geometry)
      pipeline = HullGeometryPipeline(hull_geom=webgl_geom)
      mesh = pipeline.tessellate()
      glb_bytes = exporter.export(mesh, ExportFormat.GLB)
  ```
- [ ] Test: Upload sketch → receive GLB URL → view in browser

**Reference:** Part I Issue 1.1 (lines 45-150)

#### Day 6: Issue 2.1 Physics from Geometry (8h)

**⚠️ DO NOT add hull_type validation — use body_count as geometric fact**

- [ ] Create `magnet/physics/geometry_hydrostatics.py`:
  - `compute_hydrostatics_from_geometry()` — no hull_type dispatch
  - `_compute_multi_body_hydrostatics()` — parallel axis theorem
  - `_compute_single_body_hydrostatics()` — numerical integration
- [ ] **CRITICAL:** Add comment in multi-body code:
  ```python
  # NOTE: body_count is geometric fact, not design classification
  # body_count=2 could be catamaran, proa, SWATH, or novel form
  ```
- [ ] Wire to calculator registry
- [ ] Test: Twin hull via primitives → GM > 1.0m (parallel axis applied)

**Reference:** Part II Issue 2.1 (lines 200-350)

#### Day 7: Q9 Dependency Resolution + Misc (6.5h)

- [ ] **Q9:** Update `magnet/dependencies/graph.py`:
  - Add `resolve_parameter()` with geometry aliases
  - `hull.beam` → extract from `hull.geometry.beam`
  - Fail loud if dependency missing (not silent)
- [ ] **Issue 1.2:** Add invariant tests to CI (0.5h):
  ```yaml
  # .github/workflows/ci.yml
  invariant-tests:
    run: pytest tests/invariants -v
  ```
- [ ] **Q3:** Add LLM retry logic (2h):
  - `AnthropicProvider.complete_with_retry()`
  - Exponential backoff on 429/503
  - State checkpointing in `DesignConversation.chat()`

**Reference:** Part XIII Q9 (lines 2000-2100), Part I Issue 1.2 (lines 150-200)

---

### 🟡 WEEK 2: CORE FIXES (15.5 hours)

#### Day 8: Physics Integration (6h)

- [ ] **Issue 2.2:** Weight from geometry (2h):
  - `_get_hull_factor_from_geometry()` — derive from body_count, lb_ratio
  - No hull_type lookup
- [ ] **Issue 2.3:** Scantlings from geometry (1h):
  - `_get_slamming_regime()` — derive from Froude number, not hull_type
- [ ] **Issue 3.3:** Register physics calculators (2h):
  - `register_all_calculators()` in geometry_calculator.py
  - Wire hydrostatics, resistance calculators to CascadeExecutor
- [ ] **Issue 3.1:** Wire ClarificationManager (0.5h):
  - Pass to DesignConversation in api.py
  - Create session-level `_clarification_managers` dict
- [ ] **Issue 3.2:** Surface validity_note (0.5h):
  - Update `narrative.py` to read `resistance.validity_note`
  - Show in feedback when method_valid=False

**Reference:** Part II Issues 2.2-2.3 (lines 350-450), Part III Issues 3.1-3.3 (lines 500-650)

#### Day 9: Agent Enhancements (6.5h)

- [ ] **Q2:** Agent learning from validation (3h):
  - Update `geometry_proposer.py` to accept `validation_history`
  - Extract failed patterns from last 5 attempts
  - Add to prompt: "PREVIOUS FAILURES TO AVOID"
- [ ] **Q7:** Agent reconciliation (1.5h):
  - In `design_conversation.py::chat_with_image()`:
  - Check vision body_count vs. DSL body_count
  - Request clarification if disagreement
- [ ] **Q6:** Session persistence (2h):
  - `DesignConversation.save_checkpoint()`
  - `DesignConversation.rollback_to(iteration_num)`
  - Parse "rollback to iteration N" commands

**Reference:** Part XIII Q2, Q6, Q7 (lines 1550-1650, 1750-1850)

#### Day 10: Performance + Advisory (4.5h)

- [ ] **Q4:** Cascade performance benchmark (1h):
  - Create `tests/performance/test_cascade_timing.py`
  - Target: Full recalc < 2s
  - Profile bottlenecks if slow
- [ ] **Q7:** Structural feasibility (2h):
  - Create `magnet/structural/feasibility.py`
  - `assess_structural_feasibility()` — ADVISORY ONLY
  - Check L/B ratio, depth/draft, taper
  - Returns warnings, never blocks
- [ ] **Issue 1.1 (cont):** Partial sketch detection (1.5h):
  - `_assess_completeness()` in vision_interpreter.py
  - Check view_count, missing dimensions
  - Request clarification if incomplete

**Reference:** Part XIII Q4, Q7 (lines 1600-1700, 1950-2050)

---

### 🟢 WEEK 3: POLISH (14 hours)

#### Day 11: Guards & Convergence (7h)

- [ ] **Issue 4.1:** Dimension hallucination guard (1h):
  - Update `VISION_INTERPRETER_SYSTEM_PROMPT`:
  - "ONLY extract dimensions VISIBLY WRITTEN"
  - "If no dimensions, return null"
  - Add `_validate_dimensions()` — flag if suspiciously complete
- [ ] **Issue 4.2:** Oscillation detection (3h):
  - Create `OscillationDetector` class in design_conversation.py
  - Track parameter history (window=4)
  - Detect alternating pattern
  - Return suggestion when oscillation detected
- [ ] **Q3:** Context overflow mitigation (3h):
  - Sliding window in `DesignConversation._prepare_context()`
  - Compress iterations beyond last 20
  - Keep key decisions only

**Reference:** Part IV Issues 4.1-4.2 (lines 650-750), Part XIII Q3 (lines 1580-1620)

#### Day 12: Constraint Analysis (7h)

- [ ] **Q4:** Impossible constraint detection (2h):
  - Create `magnet/kernel/constraint_analysis.py`
  - `detect_impossible_constraints()` — check GM vs. beam conflicts
  - Surface explanation + suggestions before iteration loop
- [ ] **Q6:** Dimension disambiguation (1h):
  - Add `ANNOTATION_FORMAT_RULES` to vision prompt
  - Parse "LOA: 25m" vs. "B: 8m" explicitly
  - Request clarification if ambiguous
- [ ] **Q11:** Manufacturing complexity (2h):
  - Create `magnet/manufacturing/complexity.py`
  - `estimate_manufacturing_complexity()` — ADVISORY
  - Check body_count, compound curves, symmetry
  - Return score 0-100, never blocks
- [ ] **Q12:** Novel form validation strategy (2h):
  - Document progressive validation approach
  - Add warnings for novelty_score > 0.7:
  - "Outside validated regimes — recommend model tests"

**Reference:** Part XIII Q4, Q6, Q11, Q12 (lines 1620-1750, 2050-2250)

---

### 🔒 SACRED INVARIANTS (CHECK AFTER EVERY CHANGE)

```bash
# 1. No enumeration in kernel
grep -rn "HullFamily\|HullType" magnet/kernel/stdlib/ --include="*.py" | grep -v "test\|#.*Hull"
# MUST return empty (0 matches)

# 2. All invariant tests pass
python -m pytest tests/invariants/ -v
# MUST pass 54/54 tests

# 3. THE TEST still passes
python -m pytest tests/invariants/test_the_test.py -v
# MUST pass 10/10 tests

# 4. Novel physics_category accepted (not rejected)
python -c "
from magnet.kernel.program_executor import execute_program
result = execute_program('CREATE geometry.body x { physics_category: \"novel_unknown\" }')
assert result.success == True, 'Novel category rejected (enumeration violation!)'
assert 'unknown' in str(result.warnings).lower(), 'Should warn about unknown category'
print('✅ Novel category accepted with warning')
"

# 5. Q1 primitive completeness
python -m pytest tests/validation/test_primitive_completeness.py -v
# MUST have ≥8/10 vessels at ≥75% expressibility
```

**IF ANY INVARIANT FAILS:** Revert changes immediately.

---

### 📋 FINAL VERIFICATION (Before declaring complete)

```bash
# 1. End-to-end: Sketch → GLB
curl -X POST http://localhost:8000/api/v1/design/sketch \
  -F "image=@tests/fixtures/twin_hull_sketch.png" \
  -F "user_prompt=Create from sketch"
# → Response must include glb_url

# 2. Twin hull GM correct (parallel axis)
python tests/validation/test_catamaran_hydrostatics.py
# → GM within ±10% of published Austal 40m

# 3. Prompt injection blocked
python tests/security/test_prompt_injection.py
# → All injection attempts sanitized

# 4. CI enforces invariants
# → Push PR with "HullFamily" in kernel
# → CI must FAIL on invariant-tests job

# 5. Novel form advisory warnings
python -c "
result = execute_program(VALID_NOVEL_FORM)
assert result.success == True
assert 'outside validated' in str(result.warnings).lower()
print('✅ Novel form works with advisory warnings')
"
```

---

### 🚨 BLOCKING CONDITIONS

**STOP IMMEDIATELY IF:**

1. **Q1 < 75% coverage:** Primitives insufficient → Architecture needs revision
2. **Q5 GM validation fails:** Parallel axis wrong → Fix before proceeding
3. **Any invariant test fails:** Enumeration introduced → Revert changes
4. **Novel physics_category rejected:** Validation too strict → Remove enum check

---

### 📚 REFERENCE SECTIONS (Detailed Context Below)

| Section | Lines | Purpose |
|:--------|:------|:--------|
| **Part I** | 45-200 | Pipeline breaks (sketch→GLB, CI) |
| **Part II** | 200-500 | Silent wrong values (physics from geometry) |
| **Part III** | 500-700 | Missing wiring (clarification, feedback, cascade) |
| **Part IV** | 650-800 | Missing guards (hallucination, oscillation) |
| **Part V** | 800-900 | Original roadmap (P0/P1/P2) |
| **Part IX** | 1100-1200 | Critical distinction (geometry vs. classification) |
| **Part XIII** | 1400-2200 | The hard questions (12 architectural stress tests) |
| **Part XIV** | 2200-2400 | Revised roadmap (72 hours) |
| **Part XV** | 2400-2500 | Final verification checklist |

**Use this checklist for execution. Reference detailed sections for implementation context.**

---

## Executive Summary

The MAGNET design language implementation achieved its core goal: **geometry primitives compile without enumeration**. However, comprehensive audit revealed gaps between "tests pass" and "production ready."

### What Was Found

| Category | Issues | Effort | Priority |
|----------|--------|--------|----------|
| 🔴 **Existential Risk** | 1 | 16h | **P0 BLOCKER** |
| 🔴 Pipeline Breaks | 2 | 4.5h | P0 |
| 🔴 Silent Wrong Values | 3 | 18h | P0/P1 |
| 🔴 Security | 1 | 4h | P0 |
| 🟡 Missing Wiring | 5 | 9.5h | P1 |
| 🟡 Missing Guards | 2 | 4h | P1/P2 |
| 🟡 Unknown Failure Modes | 7 | 14h | P1/P2 |
| ✅ Architectural Decision | 1 | 0.5h | P0 |
| ✅ Advisory Features | 2 | 4h | P2 |

**Bottom Line:** THE TEST passes, but **Q1 (primitive completeness) is THE existential question** — 7 primitives may not express real vessel designs. Additionally, pipeline is broken, physics is wrong for novel geometry, and security has prompt injection risk.

**Critical Path:** Q1 MUST run first. If <75% vessel expressibility, architecture needs revision.

### Document Structure

- **Parts I-II:** Critical pipeline breaks (sketch→GLB, CI enforcement)
- **Part II:** Silent wrong values (downstream physics reads `hull_type`)
- **Part III:** Missing wiring (clarification, feedback, cascade)
- **Part IV:** Missing guards (hallucination, oscillation)
- **Part V:** Prioritized roadmap (P0/P1/P2 — original)
- **Part VI-VIII:** Verification, success criteria, architectural alignment
- **Part IX:** Critical distinction (geometry vs. classification)
- **Part X:** Implementation readiness
- **Part XI:** 8 unanswered questions / failure modes
- **Part XII:** Vision model decision (Claude only)
- **Part XIII:** The hard questions — architectural stress tests (12 questions)
- **Part XIV:** Critical assessment & revised roadmap (72 hours)
- **Part XV:** Final verification checklist

**Total Implementation:** 72 hours (~9 days full-time, ~3 weeks part-time)

**CRITICAL:** Q1 (primitive completeness test) is THE existential question — must run FIRST.

---

## Part I: Critical Pipeline Breaks

### Issue 1.1: Sketch → GLB Pipeline Not Wired

**Status:** 🔴 CRITICAL — Feature doesn't work end-to-end

**Current State:**
```
Sketch → VisionInterpreter → intent_string → GeometryProposer → program_executor → HullGeometry
                                                                                        ↓
                                                                              [BROKEN LINK]
                                                                                        ↓
                                                                              HullGeometryPipeline → MeshData → GLB
```

**Root Cause:**
- `program_executor` outputs `HullGeometry` (from `magnet/hull_gen/geometry.py`)
- `HullGeometryPipeline` expects `HullGeometryData` (from `magnet/webgl/interfaces.py`)
- **These are different types with no adapter**

**Evidence:**
```python
# magnet/hull_gen/geometry.py line 373
@dataclass
class HullGeometry:
    hull_id: str = ""
    sections: List[HullSection] = ...

# magnet/webgl/interfaces.py line 184
@dataclass
class HullGeometryData:
    sections: List[HullSection]  # Different HullSection type!
```

**Required Fix:**

```python
# NEW FILE: magnet/webgl/geometry_adapter.py
"""
Adapter to convert kernel HullGeometry to webgl HullGeometryData.

This bridges the NEW geometry primitives path to the EXISTING visualization pipeline.
"""

from typing import List, Optional
from magnet.hull_gen.geometry import HullGeometry, HullSection as KernelSection
from magnet.webgl.interfaces import HullGeometryData, HullSection as WebGLSection, Point3D


def hull_geometry_to_webgl(geometry: HullGeometry) -> HullGeometryData:
    """
    Convert kernel HullGeometry to webgl HullGeometryData.
    
    This enables the NEW path to produce viewable GLB files.
    """
    webgl_sections = []
    
    for section in geometry.sections:
        # Convert kernel section to webgl section
        points = [
            Point3D(x=p[0] if len(p) > 0 else 0,
                   y=p[1] if len(p) > 1 else 0,
                   z=section.station)
            for p in section.points
        ]
        
        webgl_sections.append(WebGLSection(
            station=section.station,
            points=points,
            is_closed=False,
        ))
    
    return HullGeometryData(
        sections=webgl_sections,
        loa=geometry.loa if hasattr(geometry, 'loa') else 0,
        beam=geometry.beam if hasattr(geometry, 'beam') else 0,
        draft=geometry.draft if hasattr(geometry, 'draft') else 0,
    )
```

**Integration Point:**
```python
# In magnet/deployment/api.py, after execute_program():

if result.success and result.geometry:
    from magnet.webgl.geometry_adapter import hull_geometry_to_webgl
    from magnet.webgl.geometry_pipeline import HullGeometryPipeline
    from magnet.webgl.exporter import GeometryExporter, ExportFormat
    
    webgl_geom = hull_geometry_to_webgl(result.geometry)
    pipeline = HullGeometryPipeline(hull_geom=webgl_geom)
    mesh = pipeline.tessellate()
    
    exporter = GeometryExporter()
    glb_bytes = exporter.export(mesh, ExportFormat.GLB)
    
    response["glb_available"] = True
    response["glb_url"] = f"/api/v1/geometry/{design_id}/export/glb"
```

**Effort:** 4 hours  
**Test:** Upload sketch → receive GLB URL → view in 3D viewer

---

### Issue 1.2: Invariant Tests Not Running in CI

**Status:** 🔴 CRITICAL — Enumeration could be merged without detection

**Current State:**
```yaml
# .github/workflows/ci.yml line 77
pytest tests/unit -v  # Only tests/unit!
```

**The Risk:**
- 54 invariant tests exist in `tests/invariants/`
- They verify FORBIDDEN_TERMS, no-enumeration, THE TEST
- **They are not enforced in CI**
- A developer could merge `hull_type == "catamaran"` in kernel code

**Required Fix:**

```yaml
# .github/workflows/ci.yml — ADD NEW JOB

  # ==========================================================================
  # Invariant Tests (MAGNET Mission Statement)
  # ==========================================================================
  invariant-tests:
    name: Invariant Tests
    runs-on: ubuntu-latest
    needs: unit-tests

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio

      - name: Run invariant tests
        run: |
          PYTHONPATH=. pytest tests/invariants -v --tb=short
        env:
          MAGNET_ENVIRONMENT: test
          MAGNET_LLM_PROVIDER: mock

      - name: Verify no enumeration in kernel
        run: |
          # Fail if forbidden terms found in kernel code
          ! grep -rn "HullFamily\|HullType" magnet/kernel/stdlib/ --include="*.py" | grep -v "test\|#.*HullFamily"
```

**Effort:** 30 minutes  
**Test:** CI fails if `HullFamily` appears in `kernel/stdlib/`

---

## Part II: Silent Wrong Values

### Issue 2.1: Downstream Physics Reads hull_type

**Status:** 🔴 CRITICAL — Novel geometry gets wrong physics values

**Affected Modules:**

| Module | File | hull_type Usage | Impact |
|--------|------|-----------------|--------|
| Hydrostatics | `physics/hydrostatics.py` | 38 references | Wrong BM, KB, wetted surface |
| Weight | `weight/estimators/hull.py` | 4 references | Wrong weight factors |
| Scantlings | `structural/scantlings.py` | 2 references | Wrong slamming pressure |

**Example Failure:**
```python
# physics/hydrostatics.py line 391
def _get_inertia_coefficient(self, hull_type: str) -> float:
    if hull_type == "deep_v":
        return CI_DEEP_V
    elif hull_type == "catamaran":
        return CI_CATAMARAN
    else:
        return CI_MONOHULL  # ← Twin hull via geometry primitives gets THIS
```

**A twin-hull created via `geometry.body port { offset_y_m: -3.0 }` will:**
1. Have no `hull_type` (or default "monohull")
2. Get monohull inertia coefficient
3. **BM will be wrong by 2-4x**

**Required Fix Strategy:**

**Option A: Derive from Geometry (Recommended)**
```python
# NEW FILE: magnet/physics/geometry_hydrostatics.py

def compute_hydrostatics_from_geometry(
    geometry: HullGeometry,
    draft: float,
    vcg: float,
) -> HydrostaticsResults:
    """
    Compute hydrostatics directly from geometry — NO hull_type dispatch.
    
    This is the NEW PATH that works with arbitrary geometry.
    """
    # Count bodies
    bodies = getattr(geometry, 'bodies', {})
    body_count = len([b for b in bodies.values() if not b.get('_deleted')])
    
    # Compute from actual geometry
    volume = abs(geometry.volume)
    
    # NOTE: body_count is a geometric fact, not a design type.
    # body_count=2 could be catamaran, proa, SWATH, or something unnamed.
    # We compute physics from geometry, not from what it's "called."
    if body_count > 1:
        # Multi-body: use parallel axis theorem
        return _compute_multi_body_hydrostatics(geometry, bodies, draft, vcg)
    else:
        # Single body: numerical integration
        return _compute_single_body_hydrostatics(geometry, draft, vcg)


def _compute_multi_body_hydrostatics(geometry, bodies, draft, vcg):
    """
    Multi-body hydrostatics using parallel axis theorem.
    
    I_total = Σ(I_local + A_wp × d²)
    
    This works for ANY multi-body configuration — not just "catamaran".
    
    CRITICAL: body_count is a geometric fact, not a design type.
    - body_count=2 could be catamaran, proa, SWATH, or something unnamed
    - body_count=3 could be trimaran, tripod, or novel configuration
    - We compute physics from actual geometry, not from what it's "called"
    """
    I_combined = 0.0
    V_total = 0.0
    
    for body_id, body in bodies.items():
        if body.get('_deleted'):
            continue
            
        # Get body geometry
        offset_y = body.get('offset_y_m', 0)
        
        # Compute local waterplane inertia
        I_local = _compute_body_waterplane_inertia(geometry, body_id, draft)
        A_wp = _compute_body_waterplane_area(geometry, body_id, draft)
        V_body = _compute_body_volume(geometry, body_id, draft)
        
        # Parallel axis theorem
        I_combined += I_local + A_wp * (offset_y ** 2)
        V_total += V_body
    
    BM = I_combined / V_total if V_total > 0 else 0
    KB = draft * 0.53  # Approximate for typical forms
    GM = KB + BM - vcg
    
    return HydrostaticsResults(
        volume=V_total,
        bm=BM,
        kb=KB,
        gm=GM,
        method="geometry_derived",
        method_valid=True,
    )
```

**Option B: Infer hull_type from Geometry (Fallback)**
```python
# Add to existing hydrostatics.py

def _infer_hull_type_from_geometry(geometry: HullGeometry) -> str:
    """
    Infer hull_type from actual geometry for legacy code compatibility.
    
    WARNING: This is a MIGRATION path. New code should use geometry directly.
    """
    bodies = getattr(geometry, 'bodies', {})
    body_count = len([b for b in bodies.values() if not b.get('_deleted')])
    
    if body_count == 1:
        # Check for deadrise
        deadrise = _estimate_deadrise_from_sections(geometry.sections)
        if deadrise > 15:
            return "deep_v"
        return "monohull"
    elif body_count == 2:
        return "catamaran"
    elif body_count == 3:
        return "trimaran"
    else:
        return "multi_body"
```

**Effort:** 8 hours (Option A) or 3 hours (Option B)  
**Test:** Twin hull via geometry primitives → GM matches reference catamaran

---

### Issue 2.2: Weight Estimator Uses hull_type Factors

**Status:** 🔴 HIGH — Novel geometry gets default factor 1.0

**Current Code:**
```python
# weight/estimators/hull.py line 125
hull_factor = HULL_TYPE_FACTORS.get(hull_type, 1.0)
```

**Required Fix:**
```python
def _get_hull_factor_from_geometry(geometry: HullGeometry) -> float:
    """
    Derive weight factor from actual geometry characteristics.
    
    - Multi-body: Higher factor (more structure)
    - Slender: Lower factor
    - Deep-V: Higher factor (more material in deadrise)
    
    NOTE: This function computes from geometry, not design type names.
    """
    bodies = getattr(geometry, 'bodies', {})
    body_count = len([b for b in bodies.values() if not b.get('_deleted')])
    
    base_factor = 1.0
    
    # Multi-body penalty (body_count is geometric fact, not design classification)
    if body_count > 1:
        base_factor *= 1.0 + 0.15 * (body_count - 1)  # +15% per additional body
    
    # Slenderness bonus
    lb_ratio = geometry.loa / geometry.beam if geometry.beam > 0 else 5
    if lb_ratio > 8:
        base_factor *= 0.95  # Slender hulls are lighter
    
    return base_factor
```

**Effort:** 2 hours  
**Test:** Novel 3-body form → weight factor > 1.0

---

### Issue 2.3: Scantlings Reads hull_type for Slamming

**Status:** 🟡 MEDIUM — May over/under-estimate slamming

**Current Code:**
```python
# structural/scantlings.py line 394
hull_type = self.state.get("hull.hull_type", "planing")
if "displacement" in str(hull_type).lower():
    p_slam *= 0.7
```

**Required Fix:**
```python
def _get_slamming_regime(geometry: HullGeometry, speed_kts: float) -> str:
    """
    Derive slamming regime from geometry and speed — not hull_type string.
    """
    # Estimate Froude number
    lwl = geometry.loa * 0.95  # Approximate
    fn = speed_kts * 0.5144 / (9.81 * lwl) ** 0.5
    
    if fn < 0.4:
        return "displacement"
    elif fn < 1.0:
        return "semi_displacement"
    else:
        return "planing"
```

**Effort:** 1 hour  
**Test:** Novel geometry at Fn=0.3 → slamming reduced by 30%

---

## Part III: Missing Wiring

### Issue 3.1: ClarificationManager Not Wired in API

**Status:** 🟡 HIGH — Low-confidence guesses proceed without human review

**Current Code:**
```python
# api.py line 2938
conversation = DesignConversation(
    initial_state={"hull": {"loa": 25.0, "draft": 1.5, "vcg": 1.0}},
    conversation_id=conv_id,
    use_llm=request.use_llm,
    # clarification_manager NOT PASSED ← BUG
)
```

**Required Fix:**
```python
# Get or create clarification manager for this session
from magnet.agents.clarification import ClarificationManager

# Session-level clarification manager
if conv_id not in _clarification_managers:
    _clarification_managers[conv_id] = ClarificationManager()

conversation = DesignConversation(
    initial_state={"hull": {"loa": 25.0, "draft": 1.5, "vcg": 1.0}},
    conversation_id=conv_id,
    use_llm=request.use_llm,
    clarification_manager=_clarification_managers[conv_id],  # ← ADD THIS
    confidence_threshold=0.6,
)
```

**Effort:** 30 minutes  
**Test:** Ambiguous request → API returns clarification prompt, not guess

---

### Issue 3.2: Resistance validity_note Not Surfaced

**Status:** 🟡 MEDIUM — User sees null, not explanation

**Current Feedback:**
```
🚀 Resistance: None
```

**Should Show:**
```
⚠️ Resistance: Cannot estimate — Planing regime, Holtrop method invalid
   Recommendation: Use Savitsky method or CFD for Fn > 0.55
```

**Required Fix:**
```python
# In magnet/explain/narrative.py, _format_geometry_validation():

resist = validation.get("resistance", {})
if resist:
    resistance = resist.get("resistance_kn")
    method_valid = resist.get("method_valid", True)
    validity_note = resist.get("validity_note", "")
    
    if resistance is not None:
        lines.append(f"  🚀 Resistance: {resistance:.1f}kN")
    elif not method_valid:
        lines.append(f"  ⚠️ Resistance: Cannot estimate")
        lines.append(f"     Reason: {validity_note}")
    else:
        lines.append(f"  🚀 Resistance: Not computed")
```

**Effort:** 30 minutes  
**Test:** Novel high-speed form → feedback explains why resistance is unknown

---

### Issue 3.3: Cascade Calculators Not Registered for Physics

**Status:** 🟡 HIGH — Beam change doesn't trigger physics recalc

**Current State:**
- `GeometryCalculator` registered for `hull.geometry`
- **No calculator for** `stability.gm_m`, `resistance.total_kn`, etc.

**Required Fix:**
```python
# In magnet/dependencies/geometry_calculator.py

def register_all_calculators(registry: "CalculatorRegistry") -> None:
    """Register all calculators including physics."""
    
    # Geometry (existing)
    register_geometry_calculators(registry)
    
    # Hydrostatics
    from magnet.physics.hydrostatics import HydrostaticsCalculator
    hydro_calc = HydrostaticsCalculator()
    
    hydro_params = [
        "stability.gm_m",
        "stability.bm_m",
        "hull.displacement_m3",
        "hull.wetted_surface_m2",
    ]
    for param in hydro_params:
        registry.register(
            param=param,
            calculator=hydro_calc,
            estimated_time_ms=100,
        )
    
    # Resistance
    from magnet.physics.resistance import ResistanceCalculator
    resist_calc = ResistanceCalculator()
    
    resist_params = [
        "resistance.total_kn",
        "resistance.froude_number",
    ]
    for param in resist_params:
        registry.register(
            param=param,
            calculator=resist_calc,
            estimated_time_ms=200,
        )
```

**Effort:** 2 hours  
**Test:** Change beam → GM and resistance automatically recompute

---

## Part IV: Missing Guards

### Issue 4.1: VisionInterpreter May Hallucinate Dimensions

**Status:** 🟡 MEDIUM — LLM may invent dimensions not in sketch

**Current Prompt:**
```
2. Read any handwritten dimensions (measurements)
```

**Problem:** Doesn't say "if none visible, return null"

**Required Fix:**
```python
# In vision_interpreter.py, VISION_INTERPRETER_SYSTEM_PROMPT:

VISION_INTERPRETER_SYSTEM_PROMPT = """...

CRITICAL RULES FOR DIMENSIONS:
1. ONLY extract dimensions that are VISIBLY WRITTEN on the sketch
2. If no dimensions are written, set all dimension fields to null
3. Do NOT estimate or infer dimensions from proportions
4. If you see "25m" written, that's a dimension. If you see nothing written, dimensions are null.

Example:
- Sketch with "25m" written → {"loa_m": 25, "beam_m": null}
- Sketch with no text → {"loa_m": null, "beam_m": null}
- Sketch with proportions but no numbers → {"loa_m": null, "beam_m": null}

..."""
```

**Also Add Validation:**
```python
def _validate_dimensions(self, interpretation: SketchInterpretation) -> List[str]:
    """Check for likely hallucinated dimensions."""
    warnings = []
    
    dims = interpretation.dimensions
    if dims.get("loa_m") and dims.get("beam_m") and dims.get("draft_m"):
        # Suspiciously complete — likely hallucinated
        if interpretation.confidence < 0.8:
            warnings.append(
                "All dimensions provided but confidence is low — "
                "verify dimensions were actually written on sketch"
            )
    
    return warnings
```

**Effort:** 1 hour  
**Test:** Sketch with no text → dimensions are all null

---

### Issue 4.2: No Convergence Detection in Iteration Loop

**Status:** 🟡 MEDIUM — Conflicting constraints cause oscillation

**Current Behavior:**
```
Iteration 1: GM=0.4 → "Increase beam"
Iteration 2: GM=0.6, Resistance=60kN → "Reduce beam"
Iteration 3: GM=0.4 → "Increase beam"
... oscillates until max_iterations
```

**Required Fix:**
```python
# In magnet/agents/design_conversation.py

class DesignConversation:
    def __init__(self, ...):
        ...
        self._oscillation_detector = OscillationDetector()
    
    async def chat(self, ...):
        ...
        # After getting result
        oscillation = self._oscillation_detector.check(
            iteration_num,
            current_metrics,
        )
        
        if oscillation.detected:
            feedback += f"\n\n⚠️ **Oscillation Detected**\n"
            feedback += f"Parameters {oscillation.params} are cycling.\n"
            feedback += f"This usually means conflicting constraints.\n"
            feedback += f"Consider: {oscillation.suggestion}\n"


class OscillationDetector:
    """Detect when parameters oscillate instead of converging."""
    
    def __init__(self, window_size: int = 4):
        self._history: List[Dict[str, float]] = []
        self._window_size = window_size
    
    def check(self, iteration: int, metrics: Dict[str, float]) -> OscillationResult:
        self._history.append(metrics)
        
        if len(self._history) < self._window_size:
            return OscillationResult(detected=False)
        
        # Check for alternating pattern
        recent = self._history[-self._window_size:]
        
        for param in metrics.keys():
            values = [m.get(param) for m in recent if m.get(param) is not None]
            if len(values) >= 4:
                # Check if values alternate: up, down, up, down
                deltas = [values[i+1] - values[i] for i in range(len(values)-1)]
                if self._is_alternating(deltas):
                    return OscillationResult(
                        detected=True,
                        params=[param],
                        suggestion=f"Try fixing {param} as a constraint instead of optimizing it",
                    )
        
        return OscillationResult(detected=False)
    
    def _is_alternating(self, deltas: List[float]) -> bool:
        """Check if deltas alternate sign."""
        if len(deltas) < 3:
            return False
        signs = [1 if d > 0 else -1 for d in deltas if abs(d) > 0.01]
        if len(signs) < 3:
            return False
        # Check for +, -, +, - or -, +, -, + pattern
        for i in range(len(signs) - 1):
            if signs[i] == signs[i+1]:
                return False
        return True
```

**Effort:** 3 hours  
**Test:** Conflicting GM/resistance constraints → oscillation warning after 4 iterations

---

## Part V: Implementation Priority

### P0: Blocking the Mission (Must fix before demo)

| Issue | Effort | Owner | Test |
|-------|--------|-------|------|
| 1.1 Sketch → GLB adapter | 4h | | Upload sketch → view GLB |
| 1.2 Invariant tests in CI | 0.5h | | CI fails on enumeration |
| 2.1 Physics from geometry | 8h | | Twin hull GM matches reference |
| Q3 LLM retry + state checkpoint | 2h | | Rate limit → retry + state preserved |
| Q9 Claude vision lock-in | 0.5h | | Config enforces single model |

**Total P0:** 15 hours

### P1: Should Fix Before Demo

| Issue | Effort | Owner | Test |
|-------|--------|-------|------|
| 2.2 Weight from geometry | 2h | | Novel form weight factor correct |
| 2.3 Scantlings from geometry | 1h | | Slamming regime correct |
| 3.1 Wire ClarificationManager | 0.5h | | Low confidence → prompt |
| 3.2 Surface validity_note | 0.5h | | Unknown method → explanation |
| 3.3 Register physics calculators | 2h | | Beam change → GM recalc |
| Q1 Impossible geometry validation | 2h | | Self-intersecting → error |
| Q2 Partial sketch detection | 1h | | Profile-only → clarification |
| Q4 Cascade performance benchmark | 1h | | Full recalc <2s |
| Q6 Session persistence + rollback | 2h | | "Rollback to iteration 3" works |
| Q7 Agent reconciliation | 1.5h | | Vision/Proposer disagreement → clarify |

**Total P1:** 13.5 hours

### P2: Technical Debt

| Issue | Effort | Owner | Test |
|-------|--------|-------|------|
| 4.1 Dimension hallucination guard | 1h | | No-text sketch → null dims |
| 4.2 Oscillation detection | 3h | | Conflict → warning |
| Q5 Memory footprint test | 1h | | 100 sections <100MB |
| Q8 Optimistic concurrency | 2h | | Concurrent edits → version error |

**Total P2:** 7 hours

---

### Grand Total Implementation Effort

**P0 (Blocking):** 15 hours  
**P1 (Before Demo):** 13.5 hours  
**P2 (Tech Debt):** 7 hours  

**Total:** 35.5 hours (~4.5 days)

---

## Part VI: Verification Checklist

After implementing corrections, verify:

```bash
# 1. Sketch → GLB works
curl -X POST /api/v1/design/sketch \
  -F "image=@test_sketch.png" \
  -F "generate_geometry=true"
# → Response includes glb_url

# 2. Invariant tests in CI
git push  # → CI runs tests/invariants/

# 3. Twin hull physics correct
python -c "
from tests.fixtures.geometry_proposals import VALID_TWIN_HULL
from magnet.kernel.program_executor import execute_program
result = execute_program(VALID_TWIN_HULL.program_text)
gm = result.validation['hydrostatics']['gm_m']
assert gm > 1.0, f'Twin hull GM should be >1.0 due to parallel axis, got {gm}'
print(f'✅ Twin hull GM: {gm:.2f}m (parallel axis theorem applied)')
"

# 4. Clarification surfaces
curl -X POST /api/v1/design/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "make it better", "use_llm": true}'
# → Response includes clarification prompt (ambiguous request)

# 5. Validity note surfaces
# (Create high-speed novel form, check feedback includes validity_note)

# 6. Cascade triggers physics
# (Change beam, verify GM and resistance recalculate)
```

---

## Part VII: Success Criteria

The corrections are complete when:

1. **End-to-end works:** Sketch upload → GLB viewable in browser
2. **Physics correct:** Twin hull via primitives has GM >1.0m (parallel axis applied)
3. **CI enforces:** PR with `HullFamily` in kernel fails CI
4. **Human in loop:** Ambiguous request triggers clarification, not guess
5. **Feedback explains:** Unknown resistance method shows validity_note
6. **No silent failures:** All 13 phases recompute on beam change

---

## Part VIII: Architectural Principle Preserved

These corrections maintain the MAGNET Mission Statement:

> The kernel exposes universal geometric and physical operations.  
> Agents compose them into designs the kernel has never seen.  
> The kernel's only role is to validate reality, not recognize intent.

The fixes:
- **Do NOT add new hull types** — they derive physics from geometry
- **Do NOT enumerate** — they use body_count, not "catamaran" string
- **Do NOT recognize intent** — they compute from actual shape

The equation remains:

```
NOVELTY = continuous parameters × compositional operators × physics validation
```

We're just making sure the physics validation actually runs on the novel geometry.

---

## Part IX: Critical Distinction — Geometry vs. Classification

Throughout these corrections, we use `body_count`, `lb_ratio`, `fn`, `deadrise` — **these are geometric measurements, not classifications**.

| Geometric Fact | NOT Classification |
|:---------------|:-------------------|
| `body_count = 2` | ≠ "catamaran" (could be proa, SWATH, novel form) |
| `body_count = 3` | ≠ "trimaran" (could be tripod, Y-config, novel) |
| `deadrise > 15°` | ≠ "deep-v" (could be stepped V, warped V, novel) |
| `fn > 1.0` | ≠ "planing hull" (could be hydrofoil, surface effect, novel) |

**The Principle:**

Physics depends on **what the geometry IS** (shape, dimensions, mass distribution), not **what it's CALLED** (catamaran, trimaran, etc.).

When we write:
```python
if body_count > 1:
    apply_parallel_axis_theorem()
```

We're saying: "If multiple bodies exist, their spatial separation affects moment of inertia."

We are **NOT** saying: "If it's a catamaran, use catamaran physics."

This is the difference between:
- ✅ **Deriving from reality** — measuring what exists
- ❌ **Recognizing intent** — classifying what we think it is

The former enables infinite novelty. The latter collapses to enumeration.

---

## Part XIII: Implementation Readiness

**Status:** ✅ **READY FOR IMPLEMENTATION**

All corrections + failure mode mitigations:
- Preserve mission statement ✅
- Add zero enumeration ✅
- Derive from geometry ✅
- Fix real end-to-end gaps ✅
- Address unknown failure modes ✅
- Include test criteria ✅
- Prioritized by impact ✅

**Scope:**
- 10 critical fixes (original audit)
- 8 failure mode mitigations (new questions)
- 1 architectural decision (Claude vision only)

**Total:** 19 addressable items, 35.5 hours

**Next Steps:**
1. Implement P0 fixes (15 hours) — blocking issues
   - Sketch → GLB adapter
   - CI invariant enforcement
   - Physics from geometry (parallel axis theorem)
   - LLM retry + state checkpointing
   - Claude vision lock-in
2. Verify end-to-end flow:
   - Sketch upload → GLB viewable
   - Twin hull GM > 1.0m (parallel axis applied)
   - Rate limit → graceful retry
   - Invariant test failure blocks merge
3. Implement P1 fixes (13.5 hours) — demo-critical
   - Impossible geometry validation
   - Partial sketch detection
   - Agent reconciliation
   - Session persistence + rollback
   - Performance benchmarks
4. Implement P2 fixes (7 hours) — technical debt
   - Memory footprint tests
   - Optimistic concurrency
   - Enhanced guards

**Total Implementation:** 35.5 hours (~4.5 days full-time)

**The audit is complete. The corrections are aligned. The unknowns are now answerable. Ready to proceed.**

---

## Part XI: Unanswered Questions / Failure Modes

The 10 critical questions revealed implementable gaps. These 8 questions expose **unknowns** that need answers before production.

### 1. What happens when geometry is physically impossible?

**Scenario:**
- User sketches a hull with negative buoyancy
- Sections are inverted (keel above deck)
- Surfaces self-intersect

**Current Behavior:** Unknown — no tests for impossible geometry

**Questions:**
- Does compiler detect self-intersection?
- Does hydrostatics return negative displacement?
- Does feedback explain "this cannot float" or just show null values?

**Required Investigation:**
```python
# Test case needed
IMPOSSIBLE_GEOMETRY = """
CREATE geometry.section bow {
    station: 0.0,
    points: [[0, 0], [1, 2], [1, -2], [0, 1]]  # Self-intersecting
}
"""
result = execute_program(IMPOSSIBLE_GEOMETRY)
# What does result.errors contain?
# Does result.geometry exist?
# Does validation catch it?
```

**Decision Needed:**
- Reject at compile time? (Strict)
- Warn but allow? (Permissive)
- Let physics validation fail? (Lazy)

---

### 2. How does the system handle partial sketches?

**Scenario:**
- Sketch shows profile view only (side view)
- No plan view, no body plan, no section definition
- Vision can extract length and depth, but not beam

**Current Behavior:** Likely hallucinates beam

**Questions:**
- Does VisionInterpreter recognize "incomplete sketch"?
- Does it request additional views?
- Does it fail gracefully?

**Required Fix:**
```python
# In vision_interpreter.py

def _assess_completeness(self, interpretation: SketchInterpretation) -> List[str]:
    """Check if sketch provides enough information."""
    warnings = []
    
    # If only one view visible
    if interpretation.view_count == 1:
        warnings.append(
            "Only one view detected. For accurate geometry, please provide:\n"
            "- Profile view (side)\n"
            "- Plan view (top)\n"
            "- Body plan (sections) or dimensions"
        )
    
    # If no beam but length visible
    if interpretation.dimensions.get("loa_m") and not interpretation.dimensions.get("beam_m"):
        warnings.append(
            "Length visible but no beam dimension found. "
            "Please annotate beam or provide plan view."
        )
    
    return warnings
```

---

### 3. What if LLM rate limits or API outage during iteration loop?

**Scenario:**
- Mid-design iteration, user at iteration 3/10
- Anthropic returns `429 Rate Limit` or `503 Service Unavailable`
- CycleExecutor is waiting for GeometryProposer

**Current Behavior:** Unknown — no retry logic visible

**Questions:**
- Does request fail immediately?
- Is state corrupted?
- Can user resume from last successful iteration?

**Required Fix:**
```python
# In magnet/llm/providers/anthropic.py

class AnthropicProvider:
    async def complete_with_retry(
        self,
        prompt: str,
        max_retries: int = 3,
        backoff_seconds: float = 2.0,
    ) -> LLMResponse:
        """Call LLM with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                return await self.complete(prompt)
            except RateLimitError as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = backoff_seconds * (2 ** attempt)
                logger.warning(f"Rate limited, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            except ServiceUnavailableError as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Service unavailable, retrying...")
                await asyncio.sleep(backoff_seconds)
```

**State Protection:**
```python
# In design_conversation.py

async def chat(self, user_message: str):
    # Save state BEFORE LLM call
    checkpoint = self._state.to_dict()
    
    try:
        program_text = await self._get_program_text(user_message)
    except LLMError as e:
        # Restore state on LLM failure
        self._state = ConversationState.from_dict(checkpoint)
        return DesignIteration(
            success=False,
            feedback_to_user=f"⚠️ AI service temporarily unavailable: {e}\nPlease try again.",
        )
```

---

### 4. Performance at scale — how long does full cascade take?

**Scenario:**
- 13 phases in dependency graph
- 200+ parameters tracked
- Beam change triggers geometry, hydrostatics, resistance, weight, cost...

**Current Behavior:** Unknown — no benchmarks

**Questions:**
- Is cascade <1s for interactive feel?
- Does it block UI for 30s?
- Which phases are bottlenecks?

**Required Benchmark:**
```python
# tests/performance/test_cascade_timing.py

def test_cascade_full_recalculation():
    """Benchmark full cascade after parameter change."""
    state = create_baseline_design()
    
    start = time.time()
    state.set("hull.beam", 5.5)  # Trigger cascade
    cascade_executor.recalculate_all()
    elapsed = time.time() - start
    
    print(f"Full cascade: {elapsed:.2f}s")
    
    # Target: <2s for interactive feel
    assert elapsed < 2.0, f"Cascade took {elapsed:.2f}s (too slow)"
```

**If slow, optimize:**
- Parallel calculator execution (already planned)
- Cache unchanged values
- Lazy evaluation (only compute what's requested)

---

### 5. What's the memory footprint of HullGeometry for complex forms?

**Scenario:**
- Complex multi-body: 50 sections × 4 bodies × 100 points each = 20,000 points
- Each point: 3 floats (x, y, z) = 24 bytes
- Total: ~500KB for points alone
- Plus mesh data, validation results, state history

**Questions:**
- Does GLB export OOM?
- Does state manager keep full history in memory?
- What's the practical limit on section count?

**Required Test:**
```python
def test_large_geometry_memory():
    """Verify memory usage for complex forms."""
    import tracemalloc
    
    tracemalloc.start()
    
    # Create large geometry
    sections = []
    for i in range(100):  # 100 sections
        points = [[i, j, i/100] for j in range(200)]  # 200 points each
        sections.append(HullSection(station=i/100, points=points))
    
    geometry = HullGeometry(sections=sections)
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    print(f"Memory: {peak / 1024 / 1024:.2f} MB")
    
    # Target: <100MB for large designs
    assert peak < 100 * 1024 * 1024
```

---

### 6. How do you version/rollback a design session?

**Scenario:**
- User: "Go back to what we had 5 iterations ago"
- Or: "Show me iteration 3 again"
- Or: Browser crash mid-session

**Current Behavior:** `ConversationState` has `iterations` list, but unclear if persisted

**Questions:**
- Is history in memory only (lost on restart)?
- Can user reload session after crash?
- Is there undo/redo?

**Required Feature:**
```python
# magnet/agents/design_conversation.py

class DesignConversation:
    def save_checkpoint(self, iteration_num: int):
        """Persist conversation state to disk."""
        checkpoint_path = f"sessions/{self._conversation_id}/iteration_{iteration_num}.json"
        with open(checkpoint_path, 'w') as f:
            json.dump(self._state.to_dict(), f)
    
    def rollback_to(self, iteration_num: int) -> bool:
        """Restore state from earlier iteration."""
        checkpoint_path = f"sessions/{self._conversation_id}/iteration_{iteration_num}.json"
        if not os.path.exists(checkpoint_path):
            return False
        
        with open(checkpoint_path) as f:
            state_dict = json.load(f)
        
        self._state = ConversationState.from_dict(state_dict)
        return True
    
    async def chat(self, user_message: str):
        # Check for rollback command
        if user_message.lower().startswith("rollback to iteration"):
            match = re.search(r"iteration (\d+)", user_message.lower())
            if match:
                iter_num = int(match.group(1))
                success = self.rollback_to(iter_num)
                return DesignIteration(
                    success=success,
                    feedback_to_user=f"✅ Rolled back to iteration {iter_num}" if success else "❌ Iteration not found",
                )
```

---

### 7. What if GeometryProposer and VisionInterpreter disagree?

**Scenario:**
- VisionInterpreter: "Three distinct hull bodies detected"
- GeometryProposer generates DSL with only two bodies
- User uploaded sketch explicitly shows 3 hulls

**Current Behavior:** No reconciliation logic

**Questions:**
- Does system detect disagreement?
- Does it ask user to clarify?
- Which agent's interpretation is used?

**Required Reconciliation:**
```python
# In design_conversation.py

async def chat_with_image(self, image_bytes: bytes, user_prompt: str):
    # Step 1: Vision interpretation
    vision_result = await self._vision_interpreter.interpret_sketch(image_bytes, user_prompt)
    expected_body_count = vision_result.interpretation.body_count
    
    # Step 2: Geometry proposal
    program_text = await self._geometry_proposer.propose(
        intent=vision_result.intent_string,
    )
    
    # Step 3: Verify agreement
    actual_body_count = program_text.count("CREATE geometry.body")
    
    if actual_body_count != expected_body_count:
        # Reconciliation needed
        return await self._request_clarification(
            f"I detected {expected_body_count} hull bodies in your sketch, "
            f"but generated DSL for {actual_body_count}. "
            f"Which is correct?"
        )
```

---

### 8. Multi-user concurrency on same design?

**Scenario:**
- Two engineers working on same design_id simultaneously
- Engineer A changes beam at 10:00:01
- Engineer B changes draft at 10:00:02
- Both submit — whose change wins?

**Current Behavior:** Likely last-write-wins (data loss)

**Questions:**
- Is there locking?
- Conflict detection?
- Merge strategy?

**Required Strategy:**

**Option A: Pessimistic Locking**
```python
# In state_manager.py

class StateManager:
    def acquire_lock(self, user_id: str, timeout: int = 30):
        """Acquire exclusive lock on design state."""
        if self._lock_owner and self._lock_owner != user_id:
            raise LockError(f"Design locked by {self._lock_owner}")
        self._lock_owner = user_id
        self._lock_expires = time.time() + timeout
    
    def release_lock(self, user_id: str):
        if self._lock_owner == user_id:
            self._lock_owner = None
```

**Option B: Optimistic Concurrency (Recommended)**
```python
# Use version numbers

class StateManager:
    def __init__(self):
        self._version = 0
    
    def set(self, path: str, value: Any, expected_version: Optional[int] = None):
        if expected_version is not None and self._version != expected_version:
            raise ConcurrencyError(
                f"State modified by another user. "
                f"Expected version {expected_version}, current version {self._version}. "
                f"Please refresh and retry."
            )
        
        self._set_nested(path, value)
        self._version += 1
```

**Option C: Real-time Collaboration (Future)**
- WebSocket-based operational transforms
- Like Google Docs for ship design
- Out of scope for Phase 0

**Decision:** Start with **Option B** — optimistic concurrency with version checks.

---

## Part XII: Vision Model Selection — Keep It Simple

**Decision:** ✅ **Use Claude Sonnet 4 exclusively**

### Why One Model?

```python
# ❌ WRONG: Model selection complexity
if sketch_has_dimensions:
    use_claude_vision()
elif sketch_is_technical:
    use_gpt4_vision()
else:
    use_gemini_vision()
```

**Problems with multi-model:**
1. Inconsistent output formats
2. Different confidence calibrations
3. Testing becomes 3× harder
4. Deployment complexity (multiple API keys)
5. User confusion ("why did results change?")

```python
# ✅ RIGHT: One model, one path
VISION_MODEL = "claude-sonnet-4-20250514"

async def interpret_sketch(image: bytes) -> SketchInterpretation:
    """Use Claude Sonnet 4 for all sketch interpretation."""
    return await anthropic_client.complete_with_image(
        model=VISION_MODEL,
        image=image,
        prompt=VISION_INTERPRETER_SYSTEM_PROMPT,
    )
```

### Why Claude?

**Strengths:**
- ✅ Handles handwritten annotations (OCR-like)
- ✅ Strong at technical diagram interpretation
- ✅ Proportional reasoning (L/B ratios)
- ✅ JSON structured output
- ✅ Already using Anthropic for GeometryProposer (consistent stack)

**If Claude vision fails on a specific sketch:**
- ❌ Don't add model routing
- ✅ **Improve the prompt**
- ✅ Add that failure case to test suite
- ✅ Iterate on `VISION_INTERPRETER_SYSTEM_PROMPT`

### Implementation

```python
# magnet/llm/providers/anthropic.py

class AnthropicProvider:
    # Default to Claude Sonnet 4 for vision
    VISION_MODEL = "claude-sonnet-4-20250514"
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "supports_vision": True,
            "model": self.VISION_MODEL,
            "max_tokens": 4096,
        }
```

**Lock it in. One model. Consistent behavior. Simple stack.**

---

## Summary: Questions + Decisions

| Question | Priority | Decision |
|:---------|:---------|:---------|
| 1. Impossible geometry | P1 | Validate at compile, return structured errors |
| 2. Partial sketches | P1 | Detect incompleteness, request clarification |
| 3. LLM outages | P0 | Retry with backoff, checkpoint state |
| 4. Cascade performance | P1 | Benchmark, target <2s |
| 5. Memory footprint | P2 | Test with 100+ sections |
| 6. Version/rollback | P1 | Persist iterations, support rollback commands |
| 7. Agent disagreement | P1 | Reconciliation logic |
| 8. Multi-user concurrency | P2 | Optimistic concurrency (version checks) |
| Vision model | P0 | ✅ Claude Sonnet 4 only |

**Add to P0 Fixes:**
- LLM retry logic (1 hour)
- State checkpointing (1 hour)
- Claude vision lock-in (0.5 hours)

**Updated P0 Total:** 15 hours

# MAGNET Critical Corrections - Part XIII & XIV

**APPEND TO MAGNET_Critical_Corrections.md**

---

## Part XIII: The Hard Questions — Architectural Stress Tests

These questions expose assumptions, missing validations, and gaps that could invalidate the entire architecture.

### Q1: Can the 7 primitives express real vessel designs?

**Honest Answer:** **Unknown — NOT tested beyond 3 mission tests.**

**Current Testing:**
- ✅ 3 mission tests (stepped hull, twin hull, novel form)
- ❌ Real vessel designs (patrol boats, workboats, ferries)
- ❌ Complex features (spray rails, tunnels, transom steps)

**The Existential Risk:**
```
Real Design: "Damen Stan Patrol 4207 with spray rails, hard chines, tunnel transom"

Can Current Primitives Express This?
- sections: Chine angles ✅
- discontinuity: Hard edges ✅
- surface: Spray rail geometry... maybe? 🤔
- opening: Tunnel... or is that flow_path? 🤔
```

**Decision Framework If Primitives Are Insufficient:**

```
IF real vessel feature cannot be expressed THEN:
  
  OPTION A: Extend existing primitive
  - Add fields to geometry.surface for spray rails
  - ✅ No new primitive (preserves invariant)
  - ✅ Backward compatible
  - Decision rule: Choose this if feature is variation of existing concept
  
  OPTION B: Compose cleverly from multiple primitives
  - Tunnel = opening + flow_path + surface modifications
  - ✅ No new primitive
  - ❌ May be too complex for agents to discover
  - Decision rule: Choose if composition is intuitive
  
  OPTION C: Add new primitive
  - CREATE geometry.tunnel {...}
  - ❌ Violates "no new primitives" invariant
  - ✅ May be necessary for truly new concepts
  - Decision rule: Only if Options A & B fail AND feature is common
  
  OPTION D: Declare out of scope
  - "Spray rails are beyond MAGNET's scope"
  - ❌ Reduces addressable market
  - ✅ Maintains architectural purity
  - Decision rule: Choose if feature is rare or non-structural

DECISION CRITERIA:
1. Is feature structural or cosmetic? (Structural = must support)
2. How common is feature? (Common = must support)
3. Can it compose from existing? (Yes = Option B)
4. Can existing primitive extend? (Yes = Option A)
5. Still can't express? (Option C or D)
```

**Required Test Plan:**

```python
# tests/validation/test_primitive_completeness.py

REAL_VESSELS = [
    {
        "name": "Damen Stan Patrol 4207",
        "category": "patrol",
        "critical_features": [
            "hard_chine",
            "spray_rails",
            "bow_flare",
            "transom_stern",
        ],
    },
    {
        "name": "Austal 102m Trimaran Ferry",
        "category": "ferry",
        "critical_features": [
            "three_hulls",
            "outrigger_connection",
            "wave_piercing_bow",
            "large_deck_openings",
        ],
    },
    {
        "name": "SAFE Boats Mk VI",
        "category": "military",
        "critical_features": [
            "stepped_planing_hull",
            "tunnel_transom",
            "lifting_strakes",
            "spray_suppression",
        ],
    },
    {
        "name": "Workboat with Bow Thruster",
        "category": "utility",
        "critical_features": [
            "bow_thruster_tunnel",
            "skeg",
            "rubbing_strakes",
        ],
    },
    # Add 6 more covering: hydrofoil, SWATH, semi-sub, hovercraft base, etc.
]

def test_vessel_expressibility(vessel):
    """Attempt to express vessel in 7 primitives."""
    
    # Try to write DSL for each feature
    dsl_attempts = {}
    for feature in vessel["critical_features"]:
        dsl_attempts[feature] = attempt_to_express_feature(feature)
    
    # Calculate coverage
    expressible = [f for f, dsl in dsl_attempts.items() if dsl.success]
    coverage = len(expressible) / len(vessel["critical_features"])
    
    # Document what failed
    failed = [f for f, dsl in dsl_attempts.items() if not dsl.success]
    
    return ExpressionResult(
        vessel=vessel["name"],
        coverage=coverage,
        expressible_features=expressible,
        failed_features=failed,
        recommended_action=[decide_action(f) for f in failed],
    )

# Run on all vessels
for vessel in REAL_VESSELS:
    result = test_vessel_expressibility(vessel)
    assert result.coverage > 0.75, \
        f"{vessel['name']}: Only {result.coverage*100:.0f}% expressible. " \
        f"Failed: {result.failed_features}"
```

**Effort:** 16 hours
- 8h: Research 10 vessels, document features
- 6h: Attempt DSL expression for each
- 2h: Document gaps + decision framework application

**This is THE existential test.** Everything else is fixable wiring.

---

### Q2-Q7: [Content from previous Part XIV remains the same]

---

### Q8: Does freeform body_type create garbage-in-garbage-out?

**Revised Answer:** **Yes, but physics handles it correctly — not enumeration.**

**The Mission Conflict:**

```
WRONG APPROACH (Enumeration):
VALID_PHYSICS_CATEGORIES = ["surface_piercing", "submerged", ...]
if physics_category not in VALID_PHYSICS_CATEGORIES:
    raise ExpansionError("Invalid category")  # ← Rejects novel physics
```

This violates: *"Any hull form that requires a new language primitive is a failure."*

**If someone invents:**
```python
CREATE geometry.body hydrofoil_strut {
    physics_category: "cavitating_supercavitating",  # Novel!
}
```

**Enumeration** would reject this.  
**Correct approach** lets physics decide.

**CORRECT APPROACH:**

```python
# ✅ Accept ANY physics_category string at parse/expand time
# Let physics code handle unknown categories

def compute_hydrostatics(geometry, physics_category):
    """Compute hydrostatics based on physics behavior."""
    
    if physics_category in ["surface_piercing", "floating"]:
        return _compute_surface_piercing(geometry)
    
    elif physics_category in ["submerged", "fully_submerged"]:
        return _compute_submerged(geometry)
    
    elif physics_category in ["above_water", "superstructure", "non_wetted"]:
        return _compute_above_water(geometry)
    
    else:
        # Novel category we don't recognize
        logger.warning(f"Unknown physics_category '{physics_category}', assuming surface_piercing")
        
        return HydrostaticsResult(
            success=True,  # Still compute
            warning=f"⚠️ Unknown physics_category '{physics_category}'. "
                   f"Assumed surface_piercing behavior. "
                   f"If this is incorrect, define how this category affects buoyancy.",
            method="assumed_surface_piercing",
            confidence=0.5,  # Low confidence for unknown category
            ...
        )
```

**Key Principle:**
1. **Parser/Expander:** Accept any string (no enumeration)
2. **Physics:** Try to infer behavior, return "unknown" with assumption stated
3. **Feedback:** User sees "I don't know what 'cavitating_supercavitating' means, so I assumed..."
4. **User choice:** Accept assumption, change category, or add physics knowledge

**This preserves novelty while providing honest feedback.**

---

### Q7: Structural Feasibility — Advisory Only

**Critical Clarification:** Structural validation is **ADVISORY**, not **BLOCKING**.

**The Contract:**
```
Kernel Role: Validate PHYSICS (does it float, propel, not capsize?)
NOT Kernel Role: Validate DESIGN INTENT (buildable, pretty, cost-effective)
```

**Structural feasibility is design intent,** not physics.

**Implementation:**

```python
# magnet/structural/feasibility.py (ADVISORY MODULE)

def assess_structural_feasibility(geometry: HullGeometry) -> FeasibilityAssessment:
    """
    Advisory structural checks — NOT blocking validation.
    
    Returns warnings, never errors. Kernel still validates physics only.
    """
    
    concerns = []
    
    # Slenderness check
    lb_ratio = geometry.loa / geometry.beam
    if lb_ratio > 12:
        concerns.append(StructuralConcern(
            severity="advisory",
            category="slenderness",
            message=f"L/B = {lb_ratio:.1f} is very slender. Consider longitudinal stiffening.",
            recommendation="Review structural requirements with naval architect",
        ))
    
    # Depth/draft ratio
    if geometry.depth / geometry.draft < 1.5:
        concerns.append(StructuralConcern(
            severity="advisory",
            category="depth",
            message="Low depth/draft may limit structural strength",
            recommendation="Consider increasing hull depth or using higher-grade materials",
        ))
    
    return FeasibilityAssessment(
        is_advisory=True,  # ← KEY: This is advice, not validation
        concerns=concerns,
        overall_assessment="Concerns noted but physics is valid",
    )

# In program_executor.py
result.advisory_structural = assess_structural_feasibility(result.geometry)
result.success = result.success  # Advisory doesn't affect success
```

**Structural concerns appear in feedback but DON'T block compilation.**

**Human decides:** "Physics works but structure is concerning — I'll use exotic materials / add stiffeners / accept risk."

---

### Q9-Q12: [Content from previous remains]

---

## Part XIV: Critical Assessment & Revised Roadmap

### What's Strong

| Aspect | Assessment |
|:-------|:-----------|
| **Q1** | Correctly identifies existential risk + decision framework |
| **Q5** | Admits no ground truth, proposes concrete validation |
| **Q8** | Correctly frames novelty vs. validation trade-off (revised) |
| **Q10** | Security risk with layered mitigation |
| **Q12** | Philosophically honest about novel form validation |

### Issues Corrected

**1. Q8 Enumeration Risk — FIXED**
- ❌ Was: Validate `physics_category` against fixed list
- ✅ Now: Accept any string, let physics handle unknown categories
- **Preserves mission:** No rejection of novel physics categories

**2. Q7 Scope Creep — CLARIFIED**
- ✅ Structural feasibility stays **advisory only**
- ✅ Never blocks compilation
- ✅ Kernel validates physics, engineer validates buildability

**3. Q1 Effort Underestimate — CORRECTED**
- Was: Mentioned but no effort
- Now: **16 hours** with detailed test plan
- **This is the blocking question**

**4. Decision Framework — ADDED**
- Clear criteria for: extend primitive, compose, add new, or declare out-of-scope
- Prevents ad-hoc decisions during testing

---

### Revised Priority & Effort

**P0: Blocking the Mission**

| Issue | Hours | Critical? |
|:------|:------|:----------|
| **Q1: Primitive completeness test** | 16 | 🔴 EXISTENTIAL |
| 1.1 Sketch → GLB adapter | 4 | 🔴 HIGH |
| 1.2 Invariant tests in CI | 0.5 | 🔴 HIGH |
| 2.1 Physics from geometry | 8 | 🔴 CRITICAL |
| Q3 LLM retry + checkpointing | 2 | 🔴 HIGH |
| Q5 Parallel axis validation | 4 | 🔴 CRITICAL |
| Q9 Dependency alias resolution | 4 | 🔴 HIGH |
| Q10 Prompt injection mitigation | 4 | 🔴 CRITICAL |
| **P0 Total** | **42.5 hours** | |

**P1: Demo-Critical**

| Issue | Hours |
|:------|:------|
| 2.2 Weight from geometry | 2 |
| 2.3 Scantlings from geometry | 1 |
| 3.1 Wire ClarificationManager | 0.5 |
| 3.2 Surface validity_note | 0.5 |
| 3.3 Register physics calculators | 2 |
| Q2 Agent learning from validation | 3 |
| Q4 Cascade performance benchmark | 1 |
| Q6 Session persistence + rollback | 2 |
| Q7 Agent reconciliation | 1.5 |
| Q7 Structural feasibility (advisory) | 2 |
| **P1 Total** | **15.5 hours** |

**P2: Technical Debt**

| Issue | Hours |
|:------|:------|
| 4.1 Dimension hallucination guard | 1 |
| 4.2 Oscillation detection | 3 |
| Q3 Context overflow (sliding window) | 3 |
| Q4 Impossible constraint detection | 2 |
| Q6 Dimension disambiguation | 1 |
| Q11 Manufacturing complexity (advisory) | 2 |
| Q12 Novel form validation strategy | 2 |
| **P2 Total** | **14 hours** |

---

### Grand Total

**P0 (Blocking):** 42.5 hours  
**P1 (Demo-Critical):** 15.5 hours  
**P2 (Tech Debt):** 14 hours  

**Total:** **72 hours (~9 days full-time, ~3 weeks part-time)**

**Critical Path:** Q1 (primitive completeness) → If primitives insufficient, architecture needs revision.

---

### Implementation Sequence

**Week 1: Existential Questions**
- Day 1-2: Q1 Primitive completeness test (16h)
  - **BLOCKER:** If coverage < 75%, reassess architecture
- Day 3: Q5 Parallel axis validation (4h)
- Day 4: Q10 Prompt injection (4h)
- Day 5: 1.1 Sketch → GLB (4h)

**Week 2: Core Fixes**
- Day 6: 2.1 Physics from geometry (8h)
- Day 7: Q9 Dependency resolution (4h) + 1.2 CI (0.5h) + Q3 retry (2h)
- Day 8: P1 fixes (weight, scantlings, clarification, calculators) (6h)
- Day 9: P1 fixes (agent learning, reconciliation, rollback) (6.5h)
- Day 10: P1 fixes (cascade perf, validity notes, structural advisory) (4.5h)

**Week 3: Polish**
- Day 11-12: P2 technical debt (14h)
- Day 13: Integration testing + documentation

---

### Success Criteria

**The corrections are complete when:**

1. **✅ Primitive completeness:** 8/10 real vessels expressible at ≥75% coverage
2. **✅ End-to-end works:** Sketch → GLB viewable
3. **✅ Physics correct:** Twin hull GM validated against published catamaran data
4. **✅ No enumeration:** Novel physics_category doesn't error, returns "unknown" with assumption
5. **✅ CI enforces:** PR with `HullFamily` in kernel fails
6. **✅ Security:** Prompt injection blocked by sanitization + schema
7. **✅ Failure modes handled:** LLM retry, state checkpoint, agent reconciliation
8. **✅ Advisory feedback:** Structural/manufacturing concerns shown but don't block

---

### The Honest Bottom Line

**What We Built (Phases 0-7):** ✅ A working geometry language with no enumeration

**What the First Audit Found:** 🔴 10 critical gaps (pipeline, physics, wiring)

**What the Hard Questions Revealed:** 🔴 The existential test hasn't been run

**Q1 is THE question:** Can the 7 primitives express real vessel designs?

- If YES (≥75% coverage): **72 hours of fixes → production ready**
- If NO (<75% coverage): **Architecture needs revision**

**Everything else is fixable.** Q1 determines if the foundation is sound.

**Recommendation:** Run Q1 test FIRST (16 hours). If primitives are complete, proceed with remaining 56 hours. If not, reassess before continuing.

---

## Part XV: Final Verification Checklist

After implementing all corrections:

### Existential Tests
```bash
# 1. Primitive completeness (THE TEST)
python tests/validation/test_primitive_completeness.py
# → MUST PASS: ≥8/10 vessels at ≥75% coverage

# 2. Mission statement tests
python tests/invariants/test_the_test.py
# → Stepped hull, twin hull, novel form all compile without enumeration

# 3. No enumeration in kernel
grep -rn "HullFamily\|HullType" magnet/kernel/stdlib/ --include="*.py" | grep -v "test\|#.*Hull"
# → MUST return empty (no matches)
```

### End-to-End Tests
```bash
# 4. Sketch → GLB pipeline
curl -X POST /api/v1/design/sketch \
  -F "image=@tests/fixtures/twin_hull_sketch.png" \
  -F "user_prompt=Create geometry from this sketch"
# → Response includes glb_url

# 5. Physics validation (parallel axis)
python tests/validation/test_catamaran_hydrostatics.py
# → GM within ±10% of published Austal 40m data

# 6. Novel physics category
python -c "
result = execute_program('CREATE geometry.body x { physics_category: \"novel_category\" }')
assert result.success == True
assert 'unknown' in result.warnings[0].lower()
print('✅ Novel category accepted with warning')
"
```

### Security & Robustness
```bash
# 7. Prompt injection blocked
python tests/security/test_prompt_injection.py
# → SQL injection, instruction override attempts sanitized

# 8. LLM retry on rate limit
python tests/integration/test_llm_resilience.py
# → 429 errors trigger retry with exponential backoff

# 9. State rollback on failure
python tests/invariants/test_atomicity.py
# → All 7 atomicity tests pass
```

### CI Enforcement
```bash
# 10. Push PR with enumeration
echo 'if hull_type == "catamaran":' >> magnet/kernel/stdlib/compiler.py
git add . && git commit -m "test: add enumeration"
git push
# → CI MUST FAIL on invariant-tests job
```

**If all 10 pass:** System is production-ready.  
**If Q1 fails:** Architecture needs revision before continuing.

---

**The audit is complete. The corrections are comprehensive. The existential question is identified. Ready to proceed — starting with Q1.**

