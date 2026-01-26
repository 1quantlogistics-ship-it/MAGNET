# MAGNET Unified Library Integration Plan

**Version:** 2.1.0  
**Date:** January 25, 2026  
**Codebase Status:** 95-99% Complete, 4500+ tests  
**Synthesis Sources:** GPT5.2, OPUS, GROK, MAGNET_North_Star.md, docs/0-architecture/system/DETAILED_ARCHITECTURE_DIAGRAM.md

> **PRODUCT GOAL:** A working naval architecture kernel with physics validation, professional CAD export, and unbounded design exploration. No demo shortcuts. No deferred correctness.

> ⚠️ **DOCUMENT SCOPE:**
> - **Phase 1:** Geometry stability (trimesh, manifold3d, hypothesis)
> - **Phase 2:** Optimization + CAD export (pymoo, BoTorch, geomdl, pythonocc)
> - **Phase 2.5:** Weight estimation foundation (new MAGNET modules)
> - **Phase 3:** Advanced physics (Capytaine, hydroblast)

> 🔴 **v2.1.0 CHANGES (Audit Reconciliation):**
> 
> | Change | Rationale |
> |--------|-----------|
> | Test count → 4500+ | Actual pytest collection is 4524 |
> | structural_design.hull_material → structural_design.hull_material | Correct existing schema path |
> | Removed MaterialType enum → use existing MaterialType | "No new enums" consistency |
> | E0.4 equilibrium solver → already fixed | solve_equilibrium_draft() already has damping |
> | pythonocc CI → conda-based workflow | Cannot install via pip |
> | geomdl in appendix → Phase 2 | Consistency with P0 designation |
> | convex_hull fallback → rejection | Destructive to hull geometry |
> | Scripts marked "TO BE CREATED" | Don't claim existence of unwritten code |
> | DesignState.clone() → state.copy() pattern | Use actual codebase API |

> 🔴 **v2.0.0 CHANGES (Product-First Refactor):**
> 
> | Change | Rationale |
> |--------|-----------|
> | Removed all "demo" language and Feb 15 deadline | Product correctness > artificial milestones |
> | E0.4 Equilibrium Solver → **P0 Blocker** | Physics validation requires working solver |
> | Weight ↔ Hydrostatics convergence → **P0 Required** | Single-pass is mathematically incorrect |
> | geomdl/STEP export → **P0 moved to Phase 2** | Professional CAD interop is a product requirement |
> | Removed "accept limitation for demo" recommendations | No half-baked implementations |
> | Golden tests fail on missing baselines (not skip) | Production-grade acceptance criteria |

---

## Table of Contents

1. [North Star Constitution](#1-north-star-constitution)
2. [Integration Gate Checklist](#2-integration-gate-checklist)
3. [Library Assessment Matrix](#3-library-assessment-matrix)
4. [Phase 0: Critical Blockers](#4-phase-0-critical-blockers)
5. [Phase 1: Geometry Stability](#5-phase-1-geometry-stability)
6. [Phase 2: Optimization + CAD Export](#6-phase-2-optimization--cad-export)
   - [6.5 Phase 2.5: Weight Estimation Foundation](#65-phase-25-weight-estimation-foundation)
7. [Phase 3: Advanced Physics](#7-phase-3-advanced-physics)
8. [Phase 4: Future Enhancements](#8-phase-4-future-enhancements)
9. [Cleanup Analysis & Migration](#9-cleanup-analysis--migration)
10. [Risk Register](#10-risk-register)
11. [Integration Test Scenarios](#11-integration-test-scenarios)
12. [Appendix: Dependencies & DevOps](#12-appendix-dependencies--devops)

---

# 1. North Star Constitution

> **"The kernel's only role is to validate reality, not recognize intent."**  
> — MAGNET_North_Star.md

Every library integration MUST honor these non-negotiable principles. This section serves as the **integration constitution** that governs all decisions.

## 1.1 The Equation (Immutable)

```
NOVELTY = continuous_parameters × compositional_operators × physics_validation
```

Any integration that undermines this equation is rejected, regardless of capability gains.

## 1.2 Non-Negotiables

| Principle | Requirement | Violation Example |
|-----------|-------------|-------------------|
| **Kernel as Validation Oracle** | Kernel/validators may call libraries to **compute** reality checks (hydrostatics, resistance, mesh validity), but must NEVER contain **design suggestion logic** | ❌ "This looks like a patrol hull" |
| **Novelty Stays Continuous + Compositional** | Libraries must enable: continuous parameterization, compositional operators (loft/boolean/attach), and physics validation—**NOT enumerated hull families** | ❌ Kernel branching on classification (e.g., `if hull.hull_type == "catamaran": ...`) |
| **State is Canonical, Transactional, Observable** | Persist library-specific objects **NOWHERE** in `DesignState`. Persist only MAGNET-native primitives (arrays, dataclasses, schemas). All library integration happens behind **adapters** with deterministic conversions | ❌ Storing `trimesh.Trimesh` objects in state |
| **No New Prescriptive Enums** | If a library introduces categories (e.g., "hull types"), keep them in UI labels or post-hoc classifiers—**never as kernel decision switches** | ❌ `if hull_family == HullFamily.PLANING:` in kernel |
| **Always Degradable** | Every integration must support: **feature flag**, **graceful optional import**, and **fallback** to current implementation | ❌ Hard dependency that breaks CI when unavailable |

## 1.3 Layering Rules

*Source: GPT5.2 Section 0.2*

| Layer | May Call 3rd-Party Libs? | Must NOT Do | Typical Integration Pattern |
|-------|--------------------------|-------------|----------------------------|
| `magnet/kernel/` | Yes (for validation orchestration), but conservatively | Embed domain heuristics or prescriptive families | "Kernel calls validators; validators call adapters" |
| `magnet/physics/` | Yes | Turn into design recommender | "Physics method registry: empirical vs BEM" |
| `magnet/hull_gen/` | Yes (geometry math), but output stays MAGNET-native | Persist library objects in state | "Generate control points/sections; adapters export" |
| `magnet/webgl/` | Yes (mesh utilities), but output stays MeshData/GLB | Rewrite kernel state | "Mesh repair/volume checks via adapters" |
| `magnet/optimization/` | Yes | Mutate committed state during eval | "Surrogate/Pareto engines operate on cloned state" |
| `magnet/agents/` | Yes (LLM tools, proposal generation) | Become source of truth | "Agents propose; kernel judges" |
| `app/`, `magnet/ui_v2/` | Yes (JS libs) | Become source of truth | "Viewer/rendering is downstream of state" |

## 1.4 The Contract (From North Star)

1. **Agents propose** — in geometric primitives (surfaces, sections, bodies, constraints) composed from library seeds or invented fresh
2. **The kernel judges** — compiles geometry, runs physics, returns structured feedback; never suggests designs, never contains style knowledge
3. **State is the product** — DesignState is canonical, transactional, sliceable; LLMs reconstruct, state persists
4. **Novel designs work without new code** — if a design requires a new resource type, the system has failed

## 1.5 Why NOT LLM Memory Systems

> **"LLMs do not remember—they reconstruct, filling gaps with plausible junk when facts aren't reliably available."**  
> — MAGNET_North_Star.md

GROK's proposed "Phase 0C" (LangMem, LlamaIndex, Haystack, Mem0) **directly violates** the North Star:

| GROK Proposes | North Star Says | Verdict |
|---------------|-----------------|---------|
| "LangMem for conversation memory" | "Memory must move OUT of the LLM" | ❌ REJECTED |
| "Enable 50,000+ token context" | "Context windows are a UI convenience, but state is the product" | ❌ REJECTED |
| "Mem0 for graph-based memory" | "Canonical, sliceable, transactional state" | ❌ REJECTED |

The solution to context limitations is **better state lenses**, not LLM memory augmentation.

---

# 2. Integration Gate Checklist

*Source: OPUS Section 1, enhanced*

Every library integration MUST pass ALL gates before implementation proceeds:

| Gate | Requirement | Verification Method | Pass Criteria |
|------|-------------|---------------------|---------------|
| **G1** | Library remains geometry/physics utility only | Code review: no design intent in kernel | Zero `if design_type ==` patterns |
| **G2** | All changes observable through state lenses | Test: `StateManager.get()` returns new data | Lens coverage for new fields |
| **G3** | No new enums or prescriptive families introduced | `grep -r "class.*Enum" diff` | Zero new design-type enums |
| **G4** | Transactions remain atomic | Test: rollback on partial failure | 100% rollback coverage |
| **G5** | Existing tests pass (4524 collected) | `pytest tests/ -v` | All green |
| **G6** | Physics validation accuracy maintained or improved | Golden file comparison | ≤1% regression |
| **G7** | Graceful degradation when library unavailable | Feature flag + fallback test | Fallback path works |
| **G8** | No library objects in DesignState | `grep -r "trimesh\|manifold3d\|botorch" magnet/core/` | Zero hits |

### Gate Verification Script

> ⚠️ **AUDIT NOTE:** The repository does **not** currently contain `scripts/run_integration_gates.sh`.
> This is an **example** script body (TO BE CREATED) to make gates reproducible.

```bash
#!/bin/bash
# run_integration_gates.sh

echo "=== G1: Design Intent Check ==="
grep -rn "if.*hull_type\|if.*design_type\|if.*family" magnet/kernel/ && exit 1

echo "=== G3: Enum Check ==="
git diff --name-only | xargs grep -l "class.*Enum" | grep -v tests/ && exit 1

echo "=== G5: Test Suite ==="
pytest tests/ -v --tb=short || exit 1

echo "=== G7: Fallback Test ==="
MAGNET_DISABLE_TRIMESH=1 pytest tests/webgl/test_geometry_service.py -v || exit 1

echo "=== G8: State Purity Check ==="
grep -rn "trimesh\|manifold3d\|botorch\|pymoo" magnet/core/design_state.py && exit 1

echo "All gates passed ✓"
```

---

# 3. Library Assessment Matrix

## 3.1 Actionability Assessment

*Sources: GPT5.2 Section 2, OPUS Section 2.1, Analysis doc*

| Library/Module | Type | Feasibility | Product Impact | North Star Fit | Effort | Phase |
|----------------|------|-------------|----------------|----------------|--------|-------|
| **trimesh** | External lib | ✅ High | ✅ High | ✅ Compatible | 2-3 days | 1 |
| **manifold3d** | External lib | ✅ High | ✅ High | ✅ Compatible | 3-5 days | 1 |
| **hypothesis** | External lib | ✅ High | ✅ High (testing) | ✅ Compatible | 1-2 days | 1 |
| **pymoo** | External lib | ✅ High | ✅ High | ✅ Compatible | 5-7 days | 2 |
| **BoTorch** | External lib | ✅ High | ✅ High | ✅ Compatible | 5-7 days | 2 |
| **geomdl** | External lib | ✅ High | ✅ **Critical** (CAD export) | ✅ Compatible | 5-7 days | **2** |
| `swbs_adapter.py` | **New impl** | ✅ High | ✅ **Critical** | ✅ Compatible | 3-5 days | **2.5** |
| `tank_calculator.py` | **New impl** | ✅ High | ✅ **Critical** | ✅ Compatible | 3-5 days | **2.5** |
| `material_estimator.py` | **New impl** | ✅ High | ✅ **Critical** | ✅ Compatible | 3-5 days | **2.5** |
| `inclining_sim.py` | **New impl** | ✅ High | ✅ High | ✅ Compatible | 2-3 days | **2.5** |
| **Capytaine** | External lib | ⚠️ Medium | ⚠️ Enhancement | ✅ Compatible | 3-4 weeks | 3 |
| **hydroblast** | External lib | ⚠️ Medium | ⚠️ Enhancement | ✅ Compatible | 2-3 weeks | 3 |
| **FreeCAD Ship** | External lib | ⚠️ Low | ⚠️ Future | ✅ Compatible | 4-6 weeks | 4 |
| **xeokit-sdk** | External lib | ⚠️ Medium | ⚠️ Future | ✅ Compatible | 4-6 weeks | 4 |
| **CGAL** | External lib | ❌ Low | ❌ Future | ⚠️ GPL risk | 4-6 weeks | 4+ |

> **geomdl is P0:** Professional CAD export (STEP/IGES) is a product requirement, not an enhancement. Naval architects need NURBS-based interchange, not tessellated mesh.

> **Phase 2.5 Note:** These are **new MAGNET modules** implementing standard naval architecture formulas, NOT integrations of external libraries. See Section 6.5 for implementation details and formula sources.

> **Material Selection:** Hull construction material (steel, aluminum, composite) is stored at `structural_design.hull_material` using the existing `MaterialType` enum (`magnet/core/enums.py` L101-114). Weight estimation reads this path and dispatches to material-specific formulas.

## 3.2 Licensing Risk Assessment

*Source: OPUS Section 8.2, GPT5.2 Section 6*

| Library | License | Risk Level | Mitigation |
|---------|---------|------------|------------|
| trimesh | MIT | ✅ None | — |
| manifold3d | Apache-2.0 | ✅ None | — |
| hypothesis | MPL-2.0 | ✅ Low | Testing only |
| pymoo | Apache-2.0 | ✅ None | — |
| BoTorch | MIT | ✅ None | — |
| geomdl | MIT | ✅ None | — |
| **Capytaine** | **GPL-3.0** | ⚠️ **High** | Optional plugin, validation-only, service isolation |
| hydroblast | MIT | ✅ None | — |
| FreeCAD Ship | LGPL-2.1 | ✅ Low | Dynamic linking OK |
| xeokit-sdk | MIT | ✅ None | — |
| **CGAL** | **GPL/Commercial** | ⚠️ **High** | Defer; evaluate commercial license |

## 3.3 Codebase Compatibility

*Source: OPUS Section 2.2*

| Library | Primary Modules Touched | Potential Conflicts | Complexity |
|---------|------------------------|---------------------|------------|
| **trimesh** | `webgl/geometry_service.py`, `physics/geometry_hydrostatics.py` | None | Low |
| **manifold3d** | `bootstrap/manifold_blending.py` | sklearn PCA fallback (keep sklearn for fallback) | Medium |
| **hypothesis** | `tests/*` | None (additive) | Low |
| **pymoo** | `optimization/pareto.py` (new) | Extends existing | Medium |
| **BoTorch** | `optimization/surrogate_model.py` | sklearn GP fallback (keep sklearn for fallback) | Medium |
| `swbs_adapter.py` | `weight/swbs_adapter.py` (new), `weight/groups.py` | Enhances existing | Low |
| `tank_calculator.py` | `weight/tank_calculator.py` (new), `physics/geometry_hydrostatics.py` | None | Medium |
| `material_estimator.py` | `weight/material_estimator.py` (new), `core/enums.py` | None | Medium |
| `inclining_sim.py` | `weight/inclining_sim.py` (new), `weight/validators.py` | None | Low |
| **geomdl** | `webgl/geometry_pipeline.py` (adapter) | None | Low |
| **Capytaine** | `physics/validators.py`, new `physics/bem/` | Extends empirical | High |

> ⚠️ **sklearn Note:** Do NOT remove sklearn as a dependency. BoTorch and manifold3d fallbacks require it. The plan to "remove sklearn" was incorrect - instead, sklearn should remain for graceful degradation.

---

# 4. Phase 0: Critical Blockers (VERIFY BEFORE PROCEEDING)

> ✅ **E0.4 is already implemented.** Verify these are GREEN before proceeding.

These are foundational correctness requirements. Integration work should verify (not re-implement) these capabilities.

## 4.0.1 E0.4: Equilibrium Draft Solver — IMPLEMENTED

**Location:** `magnet/physics/equilibrium.py` → `solve_equilibrium_draft()`

**Status:** ✅ **Already implemented** with safe Newton + damping/trust region logic (lines 248-281).

> ⚠️ **AUDIT CORRECTION:** The plan previously described E0.4 as unfixed and proposed a new `find_equilibrium_draft()` function. The actual codebase has `solve_equilibrium_draft()` which already contains the damping logic. Do NOT re-implement.

**Verification Required:**

```python
# tests/physics/test_equilibrium_verification.py (TO BE CREATED)

def test_stepped_hull_convergence():
    """Verify existing E0.4 fix works on stepped hulls."""
    from magnet.physics.equilibrium import solve_equilibrium_draft
    
    # Load stepped hull test case
    hull = load_test_hull("stepped_planing_hull")
    
    # This should converge without oscillation
    draft = solve_equilibrium_draft(
        hull_definition=hull,
        target_displacement_kg=15000,
        initial_draft_m=1.5
    )
    
    assert 0.5 < draft < 3.0, "Draft in valid range"
```

**Acceptance Criteria:**

| Test Case | Requirement |
|-----------|-------------|
| Stepped hull | Converges within 10 iterations |
| All existing test hulls | Regression: still pass |
| Edge case: near-zero waterplane | Explicit error, no NaN |

**Gate:** Run existing physics tests + add stepped hull verification test.

## 4.0.2 Weight ↔ Hydrostatics Convergence

**Problem:** Tank fill levels depend on draft, but draft depends on total weight (including tanks). Single-pass calculation is mathematically incorrect.

**Required Implementation:** See Section 6.5.1.2 for detailed convergence algorithm.

**Gate:** Convergence test passes for 30m workboat with 80% tank fill.

---

# 5. Phase 1: Geometry Stability

**Priority:** P0 — Foundation for all downstream work  
**Libraries:** trimesh, manifold3d, hypothesis  
**Goal:** Make geometry truthfulness + validity checks robust, remove hand-rolled mesh math, harden invariants with property testing

## 5.1 trimesh Integration

### 4.1.1 Assessment Summary

| Criterion | Value |
|-----------|-------|
| **Actionability** | High — `pip install trimesh`, pure Python with optional C extensions |
| **Applicability** | Perfect fit — pure geometry utility, no design intent |
| **Impact** | High — eliminates 40+ lines manual volume calculation, adds mesh repair |
| **Risk** | Low — well-maintained, MIT license, 2000+ GitHub stars |
| **North Star** | ✅ Use in validation + truthfulness checks, not to decide "what hull" to build |

### 4.1.2 Files to Modify

*Sources: GPT5.2 Section 3.1.1, OPUS Section 3.1.2*

| File | Action | Lines Affected | Details |
|------|--------|----------------|---------|
| `magnet/webgl/geometry_service.py` | Replace `_mesh_volume_m3()` | DELETE lines 475-507 (~40 lines) | Manual triangle integration removed |
| `magnet/webgl/geometry_service.py` | Update volume parity logic | REFACTOR lines 458-474 (~20 lines) | Use trimesh volume |
| `magnet/webgl/mesh_utils.py` | CREATE new file | ADD ~80 lines | Adapter layer for trimesh |
| `magnet/physics/geometry_hydrostatics.py` | Optional: wetted surface | REFACTOR ~15 lines | Use trimesh surface area |
| `requirements.txt` | Add dependency | ADD 1 line | `trimesh>=4.0.0` |

### 4.1.3 Detailed Migration

**BEFORE (`geometry_service.py` lines 475-507):**

```python
def _mesh_volume_m3(m) -> float:
    """Manual volume calculation with triangle integration."""
    v = getattr(m, "vertices", []) or []
    ind = getattr(m, "indices", []) or []
    if len(v) < 3 or len(ind) < 3:
        return 0.0
    
    # ~30 lines of manual triangle volume calculation
    total = 0.0
    for i in range(0, len(ind), 3):
        i0, i1, i2 = ind[i], ind[i+1], ind[i+2]
        if i0 >= len(v) or i1 >= len(v) or i2 >= len(v):
            continue
        p0, p1, p2 = v[i0], v[i1], v[i2]
        # Manual cross-product calculations
        # Edge vector computations
        # Signed volume accumulation
        cross = [
            (p1[1] - p0[1]) * (p2[2] - p0[2]) - (p1[2] - p0[2]) * (p2[1] - p0[1]),
            (p1[2] - p0[2]) * (p2[0] - p0[0]) - (p1[0] - p0[0]) * (p2[2] - p0[2]),
            (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0]),
        ]
        total += (p0[0] * cross[0] + p0[1] * cross[1] + p0[2] * cross[2]) / 6.0
    return abs(float(total))
```

**AFTER:**

```python
import numpy as np
from typing import Optional
from magnet.webgl.mesh_utils import compute_mesh_volume, MeshValidationResult

def _mesh_volume_m3(m) -> float:
    """Volume calculation via trimesh adapter (watertight validation included)."""
    vertices = getattr(m, "vertices", None)
    indices = getattr(m, "indices", None)
    return compute_mesh_volume(vertices, indices)
```

### 4.1.4 New Adapter Module

**CREATE `magnet/webgl/mesh_utils.py`:**

```python
"""
Mesh utilities adapter layer for trimesh integration.

This module provides MAGNET-native interfaces to trimesh functionality,
ensuring no trimesh objects leak into DesignState.

North Star Compliance:
- All inputs/outputs are MAGNET-native types (np.ndarray, float, bool)
- No trimesh.Trimesh objects returned or stored
- Graceful fallback when trimesh unavailable
"""

import numpy as np
from typing import Optional, Tuple, NamedTuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Feature flag for graceful degradation
_TRIMESH_AVAILABLE = False
try:
    import trimesh
    _TRIMESH_AVAILABLE = True
except ImportError:
    logger.warning("trimesh not available; using fallback implementations")


@dataclass
class MeshValidationResult:
    """Result of mesh validation checks."""
    is_watertight: bool
    volume_m3: float
    surface_area_m2: float
    euler_number: int
    component_count: int
    has_degenerate_faces: bool
    error_message: Optional[str] = None


def compute_mesh_volume(
    vertices: Optional[np.ndarray],
    indices: Optional[np.ndarray],
    attempt_repair: bool = False
) -> float:
    """
    Compute mesh volume using trimesh, with fallback to manual calculation.
    
    Args:
        vertices: (N, 3) array of vertex positions
        indices: (M,) or (M, 3) array of face indices
        attempt_repair: If True, attempt to repair non-watertight meshes
        
    Returns:
        Absolute volume in cubic meters (always positive)
    """
    if vertices is None or indices is None:
        return 0.0
    
    vertices = np.asarray(vertices)
    indices = np.asarray(indices)
    
    if len(vertices) < 3 or len(indices) < 3:
        return 0.0
    
    if _TRIMESH_AVAILABLE:
        return _trimesh_volume(vertices, indices, attempt_repair)
    else:
        return _fallback_volume(vertices, indices)


def _trimesh_volume(
    vertices: np.ndarray,
    indices: np.ndarray,
    attempt_repair: bool
) -> float:
    """Compute volume using trimesh."""
    # Reshape indices to (n, 3) faces if flat
    if indices.ndim == 1:
        indices = indices.reshape(-1, 3)
    
    tm = trimesh.Trimesh(vertices=vertices, faces=indices)
    
    if attempt_repair and not tm.is_watertight:
        trimesh.repair.fix_normals(tm)
        trimesh.repair.fill_holes(tm)
    
    return abs(float(tm.volume))


def _fallback_volume(vertices: np.ndarray, indices: np.ndarray) -> float:
    """Fallback manual volume calculation (original implementation)."""
    # Preserved from geometry_service.py lines 475-507 for degradation
    if indices.ndim == 1:
        indices = indices.reshape(-1, 3)
    
    total = 0.0
    for face in indices:
        if np.any(face >= len(vertices)):
            continue
        p0, p1, p2 = vertices[face[0]], vertices[face[1]], vertices[face[2]]
        cross = np.cross(p1 - p0, p2 - p0)
        total += np.dot(p0, cross) / 6.0
    
    return abs(float(total))


def validate_mesh(
    vertices: np.ndarray,
    indices: np.ndarray
) -> MeshValidationResult:
    """
    Comprehensive mesh validation using trimesh.
    
    Returns MAGNET-native MeshValidationResult (no trimesh objects).
    """
    if not _TRIMESH_AVAILABLE:
        return MeshValidationResult(
            is_watertight=False,
            volume_m3=_fallback_volume(vertices, indices),
            surface_area_m2=0.0,
            euler_number=0,
            component_count=1,
            has_degenerate_faces=False,
            error_message="trimesh not available for full validation"
        )
    
    if indices.ndim == 1:
        indices = indices.reshape(-1, 3)
    
    tm = trimesh.Trimesh(vertices=vertices, faces=indices)
    
    return MeshValidationResult(
        is_watertight=tm.is_watertight,
        volume_m3=abs(float(tm.volume)),
        surface_area_m2=float(tm.area),
        euler_number=tm.euler_number,
        component_count=len(tm.split(only_watertight=False)),
        has_degenerate_faces=len(tm.degenerate_faces) > 0,
        error_message=None
    )


def repair_mesh(
    vertices: np.ndarray,
    indices: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Attempt to repair non-manifold mesh.
    
    Returns new vertices and faces arrays (MAGNET-native, not trimesh objects).
    """
    if not _TRIMESH_AVAILABLE:
        return vertices, indices
    
    if indices.ndim == 1:
        indices = indices.reshape(-1, 3)
    
    tm = trimesh.Trimesh(vertices=vertices, faces=indices)
    trimesh.repair.fix_normals(tm)
    trimesh.repair.fix_inversion(tm)
    trimesh.repair.fill_holes(tm)
    
    # Return MAGNET-native arrays, not trimesh object
    return np.array(tm.vertices), np.array(tm.faces)


def compute_signed_distance(
    mesh_vertices: np.ndarray,
    mesh_faces: np.ndarray,
    query_points: np.ndarray
) -> np.ndarray:
    """
    Compute signed distance from query points to mesh surface.
    
    Useful for collision detection and containment checks.
    """
    if not _TRIMESH_AVAILABLE:
        raise RuntimeError("trimesh required for signed distance queries")
    
    if mesh_faces.ndim == 1:
        mesh_faces = mesh_faces.reshape(-1, 3)
    
    tm = trimesh.Trimesh(vertices=mesh_vertices, faces=mesh_faces)
    return trimesh.proximity.signed_distance(tm, query_points)


def decimate_mesh(
    vertices: np.ndarray,
    faces: np.ndarray,
    target_faces: int
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Reduce mesh complexity for performance.
    
    Useful for manifold3d operations which scale O(n³).
    """
    if not _TRIMESH_AVAILABLE:
        return vertices, faces
    
    if faces.ndim == 1:
        faces = faces.reshape(-1, 3)
    
    tm = trimesh.Trimesh(vertices=vertices, faces=faces)
    simplified = tm.simplify_quadric_decimation(target_faces)
    
    return np.array(simplified.vertices), np.array(simplified.faces)
```

### 4.1.5 Test Requirements

```python
# tests/webgl/test_mesh_utils.py

import pytest
import numpy as np
from magnet.webgl.mesh_utils import (
    compute_mesh_volume,
    validate_mesh,
    repair_mesh,
    MeshValidationResult,
    _TRIMESH_AVAILABLE
)


class TestMeshVolume:
    """Volume calculation tests."""
    
    def test_unit_cube_volume(self):
        """Unit cube should have volume 1.0."""
        vertices = np.array([
            [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
            [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]
        ], dtype=float)
        # Triangulated cube faces
        faces = np.array([
            [0, 1, 2], [0, 2, 3],  # bottom
            [4, 6, 5], [4, 7, 6],  # top
            [0, 4, 5], [0, 5, 1],  # front
            [2, 6, 7], [2, 7, 3],  # back
            [0, 3, 7], [0, 7, 4],  # left
            [1, 5, 6], [1, 6, 2],  # right
        ])
        
        vol = compute_mesh_volume(vertices, faces)
        assert abs(vol - 1.0) < 0.01
    
    def test_empty_mesh_returns_zero(self):
        """Empty mesh should return 0 volume."""
        assert compute_mesh_volume(None, None) == 0.0
        assert compute_mesh_volume(np.array([]), np.array([])) == 0.0
    
    def test_flat_indices_handled(self):
        """Flat index array should be reshaped correctly."""
        vertices = np.array([[0,0,0], [1,0,0], [0,1,0], [0,0,1]], dtype=float)
        flat_indices = np.array([0, 1, 2, 0, 1, 3, 0, 2, 3, 1, 2, 3])
        
        vol = compute_mesh_volume(vertices, flat_indices)
        assert vol > 0  # Tetrahedron has positive volume


class TestMeshValidation:
    """Mesh validation tests."""
    
    @pytest.mark.skipif(not _TRIMESH_AVAILABLE, reason="trimesh not installed")
    def test_watertight_detection(self):
        """Closed mesh should be detected as watertight."""
        # Unit cube vertices and faces (watertight)
        vertices = np.array([
            [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
            [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]
        ], dtype=float)
        faces = np.array([
            [0, 1, 2], [0, 2, 3], [4, 6, 5], [4, 7, 6],
            [0, 4, 5], [0, 5, 1], [2, 6, 7], [2, 7, 3],
            [0, 3, 7], [0, 7, 4], [1, 5, 6], [1, 6, 2],
        ])
        
        result = validate_mesh(vertices, faces)
        assert result.is_watertight
        assert result.euler_number == 2  # Closed surface
    
    def test_fallback_when_trimesh_unavailable(self, monkeypatch):
        """Should return partial result when trimesh unavailable."""
        import magnet.webgl.mesh_utils as mu
        monkeypatch.setattr(mu, '_TRIMESH_AVAILABLE', False)
        
        vertices = np.array([[0,0,0], [1,0,0], [0,1,0]], dtype=float)
        faces = np.array([[0, 1, 2]])
        
        result = validate_mesh(vertices, faces)
        assert result.error_message is not None
        assert "not available" in result.error_message


class TestGracefulDegradation:
    """Ensure fallback works when trimesh unavailable."""
    
    def test_fallback_volume_matches_trimesh(self):
        """Fallback calculation should match trimesh within tolerance."""
        if not _TRIMESH_AVAILABLE:
            pytest.skip("Need trimesh to compare")
        
        from magnet.webgl.mesh_utils import _trimesh_volume, _fallback_volume
        
        # Tetrahedron
        vertices = np.array([[0,0,0], [1,0,0], [0,1,0], [0,0,1]], dtype=float)
        faces = np.array([[0,1,2], [0,1,3], [0,2,3], [1,2,3]])
        
        trimesh_vol = _trimesh_volume(vertices, faces, False)
        fallback_vol = _fallback_volume(vertices, faces)
        
        assert abs(trimesh_vol - fallback_vol) < 0.001
```

### 4.1.6 Verification Checklist

- [ ] `pytest tests/webgl/test_mesh_utils.py -v` passes
- [ ] `pytest tests/webgl/test_geometry_service.py -v` passes (volume parity unchanged)
- [ ] `MAGNET_DISABLE_TRIMESH=1 pytest tests/webgl/ -v` passes (fallback works)
- [ ] No `trimesh.Trimesh` objects in `DesignState` (`grep -r "Trimesh" magnet/core/`)
- [ ] Gate G5: Full test suite passes (3249+)

---

## 4.2 manifold3d Integration

### 4.2.1 Assessment Summary

| Criterion | Value |
|-----------|-------|
| **Actionability** | High — `pip install manifold3d`, C++ core with Python bindings |
| **Applicability** | Perfect fit — watertight guarantees for hull blending |
| **Impact** | High — replaces sklearn PCA with proper manifold projection |
| **Risk** | Medium — C++ build friction on some platforms |
| **North Star** | ✅ Pure geometry utility for validity projection |

### 4.2.2 Files to Modify

*Source: OPUS Section 3.2, GPT5.2 Appendix A.2*

| File | Action | Lines Affected | Details |
|------|--------|----------------|---------|
| `magnet/bootstrap/manifold_blending.py` | Replace PCA projection | REFACTOR lines 102-145 (~50 lines) | Use manifold3d validity projection |
| `magnet/bootstrap/manifold_blending.py` | Remove sklearn PCA import | DELETE line 24 | `from sklearn.decomposition import PCA` |
| `magnet/bootstrap/manifold_blending.py` | Remove PCA fit | DELETE lines 61-63 | PCA initialization |
| `requirements.txt` | Add dependency | ADD 1 line | `manifold3d>=2.0.0` |

### 4.2.3 Detailed Migration

**BEFORE (`manifold_blending.py` lines 102-145):**

```python
def project_to_validity(self, params: Dict[str, float]) -> Dict[str, float]:
    """Project parameters to valid manifold using PCA + binary search."""
    param_vec = self._dict_to_vector(params)
    
    # PCA projection (loses geometry guarantees)
    projected = self._pca.transform(param_vec.reshape(1, -1))
    reconstructed = self._pca.inverse_transform(projected)
    
    # Binary search to find valid point (slow, approximate)
    candidate = self._vector_to_dict(reconstructed[0])
    
    for _ in range(self._max_iterations):
        if self._validate(candidate):
            return candidate
        # Contract toward anchor
        candidate = self._contract_toward_anchor(candidate, self._anchor_params)
    
    return self._anchor_params  # Fallback to known-valid
```

**AFTER:**

```python
def project_to_validity(self, params: Dict[str, float]) -> Dict[str, float]:
    """
    Project parameters to valid manifold using manifold3d watertight projection.
    
    Falls back to PCA + contraction if manifold3d unavailable.
    """
    if not _MANIFOLD3D_AVAILABLE:
        return self._fallback_project_to_validity(params)
    
    param_vec = self._dict_to_vector(params)
    
    # Use manifold3d to project to watertight validity surface
    # This guarantees the result is geometrically valid
    projected_vec = self._manifold_project(param_vec)
    candidate = self._vector_to_dict(projected_vec)
    
    # Verify physics validity (manifold3d handles geometry, we check physics)
    if self._validate(candidate):
        return candidate
    
    # If physics invalid, contract toward anchor (rare case)
    return self._contract_toward_anchor(candidate, self._anchor_params)


def _manifold_project(self, param_vec: np.ndarray) -> np.ndarray:
    """
    Project parameter vector to valid geometry manifold.
    
    Uses manifold3d's watertight projection to ensure
    the resulting hull geometry is valid.
    """
    import manifold3d
    
    # Build hull geometry from parameters
    hull_mesh = self._params_to_mesh(param_vec)
    
    # ⚠️ NOTE: manifold3d requires manifold input. The correct API is:
    # 1. Use trimesh to prepare/repair mesh first
    # 2. Convert via MeshGL structure
    # 
    # The naive `manifold3d.Manifold(vertices, faces)` does NOT exist.
    # Use trimesh interop as documented in manifold3d examples.
    
    import trimesh
    tri_mesh = trimesh.Trimesh(vertices=hull_mesh.vertices, faces=hull_mesh.faces)
    
    # ⚠️ AUDIT FIX: Do NOT use convex_hull as fallback - this is DESTRUCTIVE
    # for naval hulls (erases cockpits, stepped hulls, transom cutouts).
    # Instead, attempt repair or reject with clear error.
    if not tri_mesh.is_watertight:
        # Try repair first
        trimesh.repair.fill_holes(tri_mesh)
        trimesh.repair.fix_normals(tri_mesh)
        
        if not tri_mesh.is_watertight:
            # REJECT - do not silently destroy geometry
            raise GeometryValidationError(
                "Hull mesh is not watertight and cannot be repaired. "
                "manifold3d requires watertight input. "
                "Check for gaps, non-manifold edges, or missing faces."
            )
    
    # Extract projected parameters from validated geometry
    return self._mesh_to_params(tri_mesh)


def _fallback_project_to_validity(self, params: Dict[str, float]) -> Dict[str, float]:
    """Original PCA + binary search fallback."""
    # Preserved original implementation for graceful degradation
    param_vec = self._dict_to_vector(params)
    projected = self._pca.transform(param_vec.reshape(1, -1))
    reconstructed = self._pca.inverse_transform(projected)
    candidate = self._vector_to_dict(reconstructed[0])
    
    for _ in range(self._max_iterations):
        if self._validate(candidate):
            return candidate
        candidate = self._contract_toward_anchor(candidate, self._anchor_params)
    
    return self._anchor_params
```

### 4.2.4 Performance Considerations

*Source: GPT5.2 Section 6, Analysis doc*

| Operation | Current (PCA) | After (manifold3d) | Mitigation |
|-----------|---------------|-------------------|------------|
| Projection | O(n²) ~50ms | O(n³) ~200ms | Mesh decimation via trimesh first |
| Memory | Low | Higher | Lazy computation, caching |

**Mitigation Strategy:**

```python
def project_to_validity(self, params: Dict[str, float]) -> Dict[str, float]:
    # Decimate mesh before manifold3d operations
    hull_mesh = self._params_to_mesh(params)
    
    if len(hull_mesh.faces) > 5000:
        # Use trimesh decimation to reduce complexity
        from magnet.webgl.mesh_utils import decimate_mesh
        vertices, faces = decimate_mesh(
            hull_mesh.vertices, 
            hull_mesh.faces, 
            target_faces=5000
        )
        hull_mesh = SimpleMesh(vertices, faces)
    
    # Now manifold3d operations are tractable
    return self._manifold_project(hull_mesh)
```

---

## 4.3 hypothesis Integration

### 4.3.1 Assessment Summary

| Criterion | Value |
|-----------|-------|
| **Actionability** | High — `pip install hypothesis`, pure Python |
| **Applicability** | Perfect fit — testing only, no production code changes |
| **Impact** | Medium — catches edge cases, hardens invariants |
| **Risk** | Low — MPL-2.0 license, test-time only dependency |
| **North Star** | ✅ Validates invariants hold across parameter space |

### 4.3.2 Property-Based Invariant Tests

*Source: GPT5.2 Section 3.1, OPUS Section 3.3*

**CREATE `tests/invariants/test_property_based.py`:**

```python
"""
Property-based invariant tests using Hypothesis.

These tests verify that MAGNET's core invariants hold across
the entire parameter space, not just specific examples.

North Star Invariants Tested:
1. Volume is always positive for valid hulls
2. No NaN values in physics outputs
3. GM is stable under small perturbations
4. Transactions are atomic (all-or-nothing)
5. State lenses return consistent snapshots
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
import numpy as np

from magnet.core.design_state import DesignState
from magnet.core.state_manager import StateManager
from magnet.physics.geometry_hydrostatics import compute_hydrostatics
from magnet.hull_gen.parameters import HullDefinition, MainDimensions
from magnet.webgl.mesh_utils import compute_mesh_volume


# =============================================================================
# Strategy Definitions
# =============================================================================

@st.composite
def hull_dimensions(draw):
    """Generate valid hull dimensions."""
    loa = draw(st.floats(min_value=5.0, max_value=500.0))
    beam = draw(st.floats(min_value=loa * 0.1, max_value=loa * 0.5))
    draft = draw(st.floats(min_value=beam * 0.05, max_value=beam * 0.8))
    
    return MainDimensions(loa=loa, beam=beam, draft=draft)


@st.composite
def section_coefficients(draw):
    """Generate valid section coefficients."""
    return {
        'Cb': draw(st.floats(min_value=0.3, max_value=0.9)),
        'Cp': draw(st.floats(min_value=0.5, max_value=0.95)),
        'Cm': draw(st.floats(min_value=0.7, max_value=0.99)),
        'Cwp': draw(st.floats(min_value=0.6, max_value=0.95)),
    }


@st.composite
def valid_hull_params(draw):
    """Generate complete valid hull parameters."""
    dims = draw(hull_dimensions())
    coeffs = draw(section_coefficients())
    
    # Ensure coefficient consistency
    assume(coeffs['Cp'] >= coeffs['Cb'])
    assume(coeffs['Cm'] >= coeffs['Cb'] / coeffs['Cp'])
    
    return {'dimensions': dims, 'coefficients': coeffs}


# =============================================================================
# Invariant Tests
# =============================================================================

class TestVolumeInvariants:
    """Volume must always be positive for valid hulls."""
    
    @given(valid_hull_params())
    @settings(max_examples=100, deadline=5000)
    def test_volume_always_positive(self, params):
        """Generated hull always has positive volume."""
        # Generate hull from params
        hull_def = HullDefinition(
            main_dimensions=params['dimensions'],
            **params['coefficients']
        )
        
        # This should never produce negative or zero volume
        mesh = hull_def.generate_mesh()
        volume = compute_mesh_volume(mesh.vertices, mesh.faces)
        
        assert volume > 0, f"Volume must be positive, got {volume}"
    
    @given(valid_hull_params())
    @settings(max_examples=50)
    def test_volume_scales_with_dimensions(self, params):
        """Volume should scale roughly as L × B × T."""
        dims = params['dimensions']
        hull_def = HullDefinition(
            main_dimensions=dims,
            **params['coefficients']
        )
        
        mesh = hull_def.generate_mesh()
        volume = compute_mesh_volume(mesh.vertices, mesh.faces)
        
        # Volume should be within order of magnitude of L*B*T
        expected_order = dims.loa * dims.beam * dims.draft
        assert 0.01 * expected_order < volume < 10 * expected_order


class TestPhysicsInvariants:
    """Physics calculations must never produce NaN."""
    
    @given(valid_hull_params())
    @settings(max_examples=100, deadline=10000)
    def test_hydrostatics_no_nan(self, params):
        """Hydrostatics must never return NaN values."""
        hull_def = HullDefinition(
            main_dimensions=params['dimensions'],
            **params['coefficients']
        )
        
        hydro = compute_hydrostatics(hull_def)
        
        # Check all numeric fields for NaN
        assert not np.isnan(hydro.displacement), "Displacement is NaN"
        assert not np.isnan(hydro.wetted_surface), "Wetted surface is NaN"
        assert not np.isnan(hydro.waterplane_area), "Waterplane area is NaN"
        assert not np.isnan(hydro.GM), "GM is NaN"
        assert not np.isnan(hydro.KB), "KB is NaN"
        assert not np.isnan(hydro.BM), "BM is NaN"
    
    @given(valid_hull_params(), st.floats(min_value=-0.1, max_value=0.1))
    @settings(max_examples=50)
    def test_gm_stability_under_perturbation(self, params, perturbation):
        """GM should be stable under small parameter changes."""
        hull_def = HullDefinition(
            main_dimensions=params['dimensions'],
            **params['coefficients']
        )
        
        gm_original = compute_hydrostatics(hull_def).GM
        
        # Perturb beam slightly
        perturbed_dims = MainDimensions(
            loa=params['dimensions'].loa,
            beam=params['dimensions'].beam * (1 + perturbation),
            draft=params['dimensions'].draft
        )
        
        hull_perturbed = HullDefinition(
            main_dimensions=perturbed_dims,
            **params['coefficients']
        )
        
        gm_perturbed = compute_hydrostatics(hull_perturbed).GM
        
        # GM should change smoothly, not jump wildly
        if abs(perturbation) < 0.01:
            assert abs(gm_perturbed - gm_original) / max(abs(gm_original), 0.1) < 0.5


class TestTransactionInvariants:
    """Transactions must be atomic."""
    
    @given(valid_hull_params())
    @settings(max_examples=20)
    def test_failed_transaction_no_side_effects(self, params):
        """Failed transaction should leave state unchanged."""
        state = DesignState()
        manager = StateManager(state)
        
        original_snapshot = manager.snapshot()
        
        try:
            with manager.transaction() as tx:
                tx.set('hull.dimensions.loa', params['dimensions'].loa)
                tx.set('hull.dimensions.beam', params['dimensions'].beam)
                # Force failure
                raise ValueError("Simulated failure")
        except ValueError:
            pass
        
        # State should be unchanged
        assert manager.snapshot() == original_snapshot


# =============================================================================
# Stateful Testing for State Machine Invariants
# =============================================================================

class DesignStateMachine(RuleBasedStateMachine):
    """
    Stateful test that verifies DesignState invariants hold
    across arbitrary sequences of operations.
    """
    
    def __init__(self):
        super().__init__()
        self.state = DesignState()
        self.manager = StateManager(self.state)
        self.committed_values = {}
    
    @rule(key=st.sampled_from(['hull.loa', 'hull.beam', 'hull.draft']),
          value=st.floats(min_value=1.0, max_value=100.0))
    def set_value(self, key, value):
        """Set a value in state."""
        with self.manager.transaction() as tx:
            tx.set(key, value)
        self.committed_values[key] = value
    
    @rule(key=st.sampled_from(['hull.loa', 'hull.beam', 'hull.draft']))
    def get_value(self, key):
        """Get a value from state."""
        if key in self.committed_values:
            actual = self.manager.get(key)
            assert actual == self.committed_values[key]
    
    @invariant()
    def state_is_consistent(self):
        """State should always be internally consistent."""
        # All committed values should be retrievable
        for key, expected in self.committed_values.items():
            actual = self.manager.get(key)
            assert actual == expected, f"{key}: expected {expected}, got {actual}"


TestDesignStateMachine = DesignStateMachine.TestCase
```

### 4.3.3 Running Property Tests

```bash
# Run with verbose output
pytest tests/invariants/test_property_based.py -v

# Run with more examples (slower, more thorough)
pytest tests/invariants/test_property_based.py -v --hypothesis-seed=0 \
    --hypothesis-settings='{"max_examples": 500}'

# Run specific invariant class
pytest tests/invariants/test_property_based.py::TestVolumeInvariants -v
```

---

# 6. Phase 2: Optimization + CAD Export

**Priority:** P0 — Core product capabilities  
**Libraries:** pymoo, BoTorch, geomdl  
**Goal:** Multi-objective Pareto fronts + improved surrogate optimization + professional CAD export

## 6.1 pymoo Integration

### 5.1.1 Assessment Summary

| Criterion | Value |
|-----------|-------|
| **Actionability** | High — `pip install pymoo`, pure Python |
| **Applicability** | Perfect fit — multi-objective optimization utility |
| **Impact** | High — enables Pareto fronts for engineer vs CFO views |
| **Risk** | Low — Apache-2.0 license, academic gold standard |
| **North Star** | ✅ Operates on cloned state, kernel judges all candidates |

### 5.1.2 Why pymoo Over Single-Objective

*Source: Analysis doc, GROK strategic positioning*

> "Ships have 10+ conflicting objectives. Design Pareto fronts instead of single 'optimal' designs."

| Current Approach | pymoo Approach |
|------------------|----------------|
| Single "best" design | Pareto front of trade-offs |
| User chooses 1 objective | User navigates trade-off surface |
| Hidden compromises | Explicit trade-off visualization |

### 5.1.3 Files to Create/Modify

| File | Action | Lines | Details |
|------|--------|-------|---------|
| `magnet/optimization/pareto.py` | CREATE | ~300 lines | Pareto optimizer using pymoo |
| `magnet/optimization/objectives.py` | CREATE | ~150 lines | Objective function definitions |
| `magnet/optimization/schema.py` | MODIFY | ~50 lines | Add Pareto result types |
| `requirements.txt` | ADD | 1 line | `pymoo>=0.6.0` |

### 5.1.4 Implementation

**CREATE `magnet/optimization/pareto.py`:**

```python
"""
Multi-objective Pareto optimization using pymoo.

North Star Compliance:
- Optimizer proposes candidates; kernel judges physics
- All evaluations on CLONED state (never mutate committed state)
- Results are MAGNET-native types, not pymoo objects
"""

import numpy as np
from typing import List, Dict, Callable, Optional, Tuple
from dataclasses import dataclass
from pymoo.core.problem import Problem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.optimize import minimize
from pymoo.util.ref_dirs import get_reference_directions

from magnet.core.design_state import DesignState
from magnet.core.state_manager import StateManager
from magnet.kernel.conductor import Conductor
from magnet.kernel.enums import PhaseStatus


@dataclass
class ParetoCandidate:
    """A single point on the Pareto front."""
    parameters: Dict[str, float]
    objectives: Dict[str, float]  # e.g., {'resistance': 1234, 'gm': 0.8, 'cost': 50000}
    validation_status: str  # 'valid', 'warning', 'invalid'
    validation_details: Dict[str, any]
    rank: int  # Pareto rank (1 = non-dominated)


@dataclass
class ParetoResult:
    """Result of multi-objective optimization."""
    candidates: List[ParetoCandidate]
    pareto_front: List[ParetoCandidate]  # Non-dominated only
    hypervolume: float
    generations: int
    evaluations: int


class MAGNETMultiObjectiveProblem(Problem):
    """
    pymoo Problem wrapper for MAGNET design optimization.
    
    Evaluates designs by:
    1. Cloning state
    2. Applying parameter changes
    3. Running kernel validation
    4. Extracting objective values
    """
    
    def __init__(
        self,
        base_state: DesignState,
        parameter_bounds: Dict[str, Tuple[float, float]],
        objective_functions: Dict[str, Callable[[DesignState], float]],
        constraint_functions: Optional[Dict[str, Callable[[DesignState], float]]] = None,
        minimize_objectives: Optional[Dict[str, bool]] = None
    ):
        self.base_state = base_state
        self.param_names = list(parameter_bounds.keys())
        self.param_bounds = parameter_bounds
        self.objective_funcs = objective_functions
        self.objective_names = list(objective_functions.keys())
        self.constraint_funcs = constraint_functions or {}
        self.minimize_objectives = minimize_objectives or {k: True for k in self.objective_names}
        
        # Build bounds arrays
        xl = np.array([parameter_bounds[p][0] for p in self.param_names])
        xu = np.array([parameter_bounds[p][1] for p in self.param_names])
        
        super().__init__(
            n_var=len(self.param_names),
            n_obj=len(self.objective_funcs),
            n_ieq_constr=len(self.constraint_funcs),
            xl=xl,
            xu=xu
        )
    
    def _evaluate(self, X, out, *args, **kwargs):
        """Evaluate population of designs."""
        F = np.zeros((len(X), self.n_obj))
        G = np.zeros((len(X), self.n_ieq_constr)) if self.n_ieq_constr > 0 else None
        
        for i, x in enumerate(X):
            # Create copy of state for evaluation (CRITICAL: never mutate base)
            # v2.1: DesignState provides copy() (deep copy via to_dict/from_dict).
            state_copy = self.base_state.copy()
            sm = StateManager(state_copy)
            
            # Apply parameters
            for j, param_name in enumerate(self.param_names):
                sm.set(param_name, x[j])
            
            # Run kernel validation (actual API: Conductor.run_phase/run_to_phase)
            # NOTE: This runs against the copied state; do NOT commit/persist from within optimization.
            conductor = Conductor(sm)
            try:
                results = conductor.run_to_phase("stability")
                is_valid = all(r.status == PhaseStatus.COMPLETED for r in results)
                if not is_valid:
                    raise RuntimeError("candidate_failed_validation")
                
                # Compute objectives
                for k, (obj_name, obj_func) in enumerate(self.objective_funcs.items()):
                    value = obj_func(state_copy)
                    # Flip sign if maximizing
                    if not self.minimize_objectives.get(obj_name, True):
                        value = -value
                    F[i, k] = value
                
                # Compute constraints (g(x) <= 0 means feasible)
                if G is not None:
                    for k, (con_name, con_func) in enumerate(self.constraint_funcs.items()):
                        G[i, k] = con_func(state_copy)
                        
            except Exception as e:
                # Invalid design gets penalty
                F[i, :] = 1e10
                if G is not None:
                    G[i, :] = 1e10
        
        out["F"] = F
        if G is not None:
            out["G"] = G


class ParetoOptimizer:
    """
    Multi-objective optimizer for MAGNET designs.
    
    Usage:
        optimizer = ParetoOptimizer(state, bounds, objectives)
        result = optimizer.optimize(n_generations=50)
        
        # Get engineer's favorite (min resistance)
        eng_fav = result.pareto_front[0]
        
        # Get CFO's favorite (min cost)
        cfo_fav = min(result.pareto_front, key=lambda c: c.objectives['cost'])
    """
    
    def __init__(
        self,
        base_state: DesignState,
        parameter_bounds: Dict[str, Tuple[float, float]],
        objective_functions: Dict[str, Callable[[DesignState], float]],
        constraint_functions: Optional[Dict[str, Callable[[DesignState], float]]] = None,
        minimize_objectives: Optional[Dict[str, bool]] = None
    ):
        self.base_state = base_state
        self.parameter_bounds = parameter_bounds
        self.objective_functions = objective_functions
        self.constraint_functions = constraint_functions
        self.minimize_objectives = minimize_objectives
        
        self.problem = MAGNETMultiObjectiveProblem(
            base_state=base_state,
            parameter_bounds=parameter_bounds,
            objective_functions=objective_functions,
            constraint_functions=constraint_functions,
            minimize_objectives=minimize_objectives
        )
    
    def optimize(
        self,
        n_generations: int = 50,
        population_size: int = 100,
        algorithm: str = 'nsga2',
        seed: Optional[int] = None
    ) -> ParetoResult:
        """
        Run multi-objective optimization.
        
        Args:
            n_generations: Number of generations to evolve
            population_size: Population size per generation
            algorithm: 'nsga2' or 'nsga3'
            seed: Random seed for reproducibility
            
        Returns:
            ParetoResult with candidates and Pareto front
        """
        if algorithm == 'nsga2':
            algo = NSGA2(pop_size=population_size)
        elif algorithm == 'nsga3':
            n_obj = len(self.objective_functions)
            ref_dirs = get_reference_directions("das-dennis", n_obj, n_partitions=12)
            algo = NSGA3(pop_size=population_size, ref_dirs=ref_dirs)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        
        result = minimize(
            self.problem,
            algo,
            ('n_gen', n_generations),
            seed=seed,
            verbose=False
        )
        
        return self._convert_result(result)
    
    def _convert_result(self, pymoo_result) -> ParetoResult:
        """Convert pymoo result to MAGNET-native ParetoResult."""
        candidates = []
        
        for i, (x, f) in enumerate(zip(pymoo_result.X, pymoo_result.F)):
            # Build parameter dict
            params = {
                name: float(x[j])
                for j, name in enumerate(self.problem.param_names)
            }
            
            # Build objectives dict (flip sign back for maximization)
            objectives = {}
            for j, name in enumerate(self.problem.objective_names):
                value = float(f[j])
                if not self.minimize_objectives.get(name, True):
                    value = -value
                objectives[name] = value
            
            # Validate candidate
            state_copy = self.base_state.copy()
            sm = StateManager(state_copy)
            for param_name, value in params.items():
                sm.set(param_name, value)
            
            conductor = Conductor(sm)
            results = conductor.run_to_phase("stability")
            is_valid = all(r.status == PhaseStatus.COMPLETED for r in results)
            
            candidates.append(ParetoCandidate(
                parameters=params,
                objectives=objectives,
                validation_status="valid" if is_valid else "invalid",
                validation_details={"phases": [r.to_dict() for r in results if hasattr(r, "to_dict")]},
                rank=1 if i < len(pymoo_result.opt) else 2
            ))
        
        # Extract Pareto front (non-dominated solutions)
        pareto_front = [c for c in candidates if c.rank == 1]
        
        return ParetoResult(
            candidates=candidates,
            pareto_front=pareto_front,
            hypervolume=float(pymoo_result.F.min(axis=0).prod()),  # Simplified
            generations=pymoo_result.algorithm.n_gen,
            evaluations=pymoo_result.algorithm.evaluator.n_eval
        )


# =============================================================================
# Utility Functions
# =============================================================================

def optimize_retrofit(
    state: DesignState,
    objectives: List[str] = ['resistance', 'gm', 'cost']
) -> ParetoResult:
    """
    Convenience function for retrofit optimization.
    
    Produces Pareto front balancing:
    - Resistance (minimize)
    - GM stability margin (maximize)
    - Estimated cost (minimize)
    """
    from magnet.optimization.objectives import (
        compute_resistance,
        compute_gm_margin,
        estimate_cost
    )
    
    # Get current bounds from state
    current_loa = state.hull.dimensions.loa
    current_beam = state.hull.dimensions.beam
    
    bounds = {
        'hull.dimensions.beam': (current_beam * 0.95, current_beam * 1.05),
        'hull.coefficients.Cb': (0.3, 0.7),
        'hull.bow.rake_angle': (0, 30),
    }
    
    objective_funcs = {
        'resistance': compute_resistance,
        'gm': compute_gm_margin,
        'cost': estimate_cost,
    }
    
    minimize_flags = {
        'resistance': True,
        'gm': False,  # Maximize GM
        'cost': True,
    }
    
    optimizer = ParetoOptimizer(
        base_state=state,
        parameter_bounds=bounds,
        objective_functions=objective_funcs,
        minimize_objectives=minimize_flags
    )
    
    return optimizer.optimize(n_generations=30, population_size=50)
```

### 5.1.5 Dual-Audience Views (Engineer vs CFO)

*Source: Analysis doc "Targeted Insight Categories"*

**CREATE `magnet/optimization/views.py`:**

```python
"""
Dual-audience views for Pareto optimization results.

Provides Engineer-focused and CFO-focused perspectives
on the same Pareto front.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from magnet.optimization.pareto import ParetoResult, ParetoCandidate


@dataclass
class EngineerView:
    """Engineer-focused view of optimization results."""
    recommended: ParetoCandidate
    reason: str
    technical_details: Dict[str, any]
    alternatives: List[ParetoCandidate]


@dataclass
class CFOView:
    """CFO-focused view of optimization results."""
    recommended: ParetoCandidate
    reason: str
    cost_savings: float
    roi_estimate: Optional[float]
    alternatives: List[ParetoCandidate]


def get_engineer_favorite(result: ParetoResult) -> EngineerView:
    """
    Select engineer's favorite from Pareto front.
    
    Prioritizes: stability margin > resistance > cost
    """
    front = result.pareto_front
    
    # Engineer cares most about GM margin
    best = max(front, key=lambda c: c.objectives.get('gm', 0))
    
    # Get alternatives with different trade-offs
    sorted_by_resistance = sorted(front, key=lambda c: c.objectives.get('resistance', float('inf')))
    
    return EngineerView(
        recommended=best,
        reason=f"Best stability margin (GM={best.objectives['gm']:.2f}m) while maintaining acceptable resistance",
        technical_details={
            'gm_margin': best.objectives.get('gm'),
            'resistance_kn': best.objectives.get('resistance'),
            'validation': best.validation_details,
        },
        alternatives=sorted_by_resistance[:3]
    )


def get_cfo_favorite(result: ParetoResult, baseline_cost: float = 0) -> CFOView:
    """
    Select CFO's favorite from Pareto front.
    
    Prioritizes: cost > fuel efficiency (resistance proxy) > meets minimum safety
    """
    front = result.pareto_front
    
    # Filter to only valid designs
    valid = [c for c in front if c.validation_status == 'valid']
    if not valid:
        valid = front  # Fall back if none valid
    
    # CFO cares most about cost
    best = min(valid, key=lambda c: c.objectives.get('cost', float('inf')))
    
    # Calculate savings
    savings = baseline_cost - best.objectives.get('cost', baseline_cost)
    
    # Sort by fuel efficiency (resistance proxy)
    sorted_by_fuel = sorted(valid, key=lambda c: c.objectives.get('resistance', float('inf')))
    
    return CFOView(
        recommended=best,
        reason=f"Lowest cost (${best.objectives['cost']:,.0f}) while meeting all safety requirements",
        cost_savings=savings,
        roi_estimate=savings / best.objectives.get('cost', 1) * 100 if savings > 0 else None,
        alternatives=sorted_by_fuel[:3]
    )
```

---

## 5.2 BoTorch Integration

### 5.2.1 Assessment Summary

| Criterion | Value |
|-----------|-------|
| **Actionability** | High — requires PyTorch stack |
| **Applicability** | Excellent fit — replaces sklearn GP |
| **Impact** | Medium — better uncertainty quantification, acquisition functions |
| **Risk** | Medium — PyTorch version conflicts possible |
| **North Star** | ✅ Optimization utility, operates on cloned state |

### 5.2.2 Files to Modify

*Source: GPT5.2 Appendix A.3, OPUS Section 4.1*

| File | Action | Lines Affected | Details |
|------|--------|----------------|---------|
| `magnet/optimization/surrogate_model.py` | Replace sklearn GP | REFACTOR lines 30-82 (~60 lines) | Use BoTorch GP |
| `requirements.txt` | ADD dependencies | 3 lines | `botorch`, `gpytorch`, `torch` |

### 5.2.3 Detailed Migration

**BEFORE (`surrogate_model.py` lines 30-82):**

```python
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel

class SurrogateModel:
    def __init__(self, kernel=None):
        kernel = kernel or ConstantKernel(1.0) * RBF(length_scale=1.0)
        self._gp = GaussianProcessRegressor(
            kernel=kernel,
            alpha=1e-6,
            normalize_y=True,
            n_restarts_optimizer=5
        )
    
    def fit(self, X, y):
        self._gp.fit(X, y)
    
    def predict(self, X, return_std=False):
        return self._gp.predict(X, return_std=return_std)
```

**AFTER:**

```python
"""
Surrogate model using BoTorch for improved uncertainty quantification.

Falls back to sklearn GP if BoTorch unavailable.
"""

import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Feature flag for graceful degradation
_BOTORCH_AVAILABLE = False
try:
    import torch
    import botorch
    from botorch.models import SingleTaskGP
    from botorch.fit import fit_gpytorch_mll
    from gpytorch.mlls import ExactMarginalLogLikelihood
    _BOTORCH_AVAILABLE = True
except ImportError:
    logger.warning("BoTorch not available; using sklearn GP fallback")
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel


class SurrogateModel:
    """
    Gaussian Process surrogate model for design optimization.
    
    Uses BoTorch when available for:
    - Better uncertainty quantification
    - GPU acceleration
    - Advanced acquisition functions
    
    Falls back to sklearn GP otherwise.
    """
    
    def __init__(self, use_gpu: bool = False):
        self.use_gpu = use_gpu and _BOTORCH_AVAILABLE and torch.cuda.is_available()
        self._model = None
        self._X_train = None
        self._y_train = None
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'SurrogateModel':
        """Fit surrogate model to training data."""
        if _BOTORCH_AVAILABLE:
            self._fit_botorch(X, y)
        else:
            self._fit_sklearn(X, y)
        return self
    
    def _fit_botorch(self, X: np.ndarray, y: np.ndarray):
        """Fit using BoTorch SingleTaskGP."""
        device = torch.device('cuda' if self.use_gpu else 'cpu')
        
        self._X_train = torch.tensor(X, dtype=torch.float64, device=device)
        self._y_train = torch.tensor(y, dtype=torch.float64, device=device).unsqueeze(-1)
        
        self._model = SingleTaskGP(self._X_train, self._y_train)
        mll = ExactMarginalLogLikelihood(self._model.likelihood, self._model)
        fit_gpytorch_mll(mll)
    
    def _fit_sklearn(self, X: np.ndarray, y: np.ndarray):
        """Fallback: fit using sklearn GP."""
        kernel = ConstantKernel(1.0) * RBF(length_scale=1.0)
        self._model = GaussianProcessRegressor(
            kernel=kernel,
            alpha=1e-6,
            normalize_y=True,
            n_restarts_optimizer=5
        )
        self._model.fit(X, y)
        self._X_train = X
        self._y_train = y
    
    def predict(
        self,
        X: np.ndarray,
        return_std: bool = False
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Predict mean (and optionally std) at query points.
        
        Returns:
            mean: (n,) array of predictions
            std: (n,) array of uncertainties (if return_std=True)
        """
        if _BOTORCH_AVAILABLE:
            return self._predict_botorch(X, return_std)
        else:
            return self._predict_sklearn(X, return_std)
    
    def _predict_botorch(
        self,
        X: np.ndarray,
        return_std: bool
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """Predict using BoTorch model."""
        device = self._X_train.device
        X_tensor = torch.tensor(X, dtype=torch.float64, device=device)
        
        self._model.eval()
        with torch.no_grad():
            posterior = self._model.posterior(X_tensor)
            mean = posterior.mean.squeeze(-1).cpu().numpy()
            
            if return_std:
                std = posterior.variance.sqrt().squeeze(-1).cpu().numpy()
                return mean, std
            return mean, None
    
    def _predict_sklearn(
        self,
        X: np.ndarray,
        return_std: bool
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """Predict using sklearn GP."""
        if return_std:
            mean, std = self._model.predict(X, return_std=True)
            return mean, std
        return self._model.predict(X), None
    
    def acquisition_ei(self, X: np.ndarray, best_f: float) -> np.ndarray:
        """
        Expected Improvement acquisition function.
        
        Only available with BoTorch; raises if unavailable.
        """
        if not _BOTORCH_AVAILABLE:
            raise RuntimeError("BoTorch required for acquisition functions")
        
        from botorch.acquisition import ExpectedImprovement
        
        device = self._X_train.device
        X_tensor = torch.tensor(X, dtype=torch.float64, device=device)
        
        ei = ExpectedImprovement(self._model, best_f=best_f)
        with torch.no_grad():
            ei_values = ei(X_tensor.unsqueeze(1))
        
        return ei_values.cpu().numpy()
```

## 6.3 geomdl + pythonocc: Professional CAD Export

> 🔴 **P0 REQUIREMENT:** Naval architects need STEP/IGES export, not tessellated mesh.

### 6.3.1 Assessment Summary

| Criterion | Value |
|-----------|-------|
| **Actionability** | High — conda install pythonocc-core |
| **Applicability** | Critical — professional CAD interchange |
| **Impact** | **Critical** — enables shipyard/CFD/classification workflows |
| **Risk** | Low — LGPL license (pythonocc) |
| **North Star** | ✅ Pure geometry export utility |

### 6.3.2 Key Insight

geomdl is excellent for NURBS manipulation but **does NOT have native STEP/IGES export**. The plan's original `exchange.export_step()` function does not exist.

**Correct Solution:** Use pythonocc (Open CASCADE Python bindings) for STEP/IGES export:

```
MAGNET NURBS → geomdl (manipulation/fairing) → pythonocc (STEP/IGES export)
```

### 6.3.3 Installation

```bash
# pythonocc requires conda (not pip)
conda install -c conda-forge pythonocc-core
pip install geomdl
```

### 6.3.4 Adapter Implementation

```python
# magnet/cad/export_adapter.py

"""
CAD export adapter using pythonocc for STEP/IGES.

geomdl is used for NURBS manipulation; pythonocc for CAD file export.
MAGNET's internal NURBS (magnet/hull_gen/nurbs.py) remains canonical.
"""

from typing import List
import numpy as np

from magnet.hull_gen.nurbs import NURBSSurface as MAGNETSurface

# Optional imports with graceful degradation
try:
    from OCC.Core.Geom import Geom_BSplineSurface
    from OCC.Core.TColgp import TColgp_Array2OfPnt
    from OCC.Core.TColStd import TColStd_Array1OfReal, TColStd_Array1OfInteger
    from OCC.Core.gp import gp_Pnt
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCC.Core.STEPControl import STEPControl_Writer, STEPControl_AsIs
    from OCC.Core.IGESControl import IGESControl_Writer
    from OCC.Core.IFSelect import IFSelect_RetDone
    from OCC.Core.TopoDS import TopoDS_Compound
    from OCC.Core.BRep import BRep_Builder
    PYTHONOCC_AVAILABLE = True
except ImportError:
    PYTHONOCC_AVAILABLE = False


def check_pythonocc():
    """Verify pythonocc is available."""
    if not PYTHONOCC_AVAILABLE:
        raise ImportError(
            "pythonocc-core required for STEP/IGES export. "
            "Install with: conda install -c conda-forge pythonocc-core"
        )


def magnet_to_occ_bspline(surface: MAGNETSurface) -> "Geom_BSplineSurface":
    """Convert MAGNET NURBSSurface to Open CASCADE BSplineSurface."""
    check_pythonocc()
    
    # Extract dimensions
    n_u, n_v = surface.n_u, surface.n_v
    degree_u, degree_v = surface.degree_u, surface.degree_v
    
    # Create control points array
    poles = TColgp_Array2OfPnt(1, n_u, 1, n_v)
    for i in range(n_u):
        for j in range(n_v):
            pt = surface.control_points[i, j]
            poles.SetValue(i + 1, j + 1, gp_Pnt(pt[0], pt[1], pt[2]))
    
    # Create knot vectors
    # (Simplified - production code needs proper multiplicity handling)
    u_knots = TColStd_Array1OfReal(1, len(surface.knots_u))
    u_mults = TColStd_Array1OfInteger(1, len(surface.knots_u))
    for i, k in enumerate(surface.knots_u):
        u_knots.SetValue(i + 1, k)
        u_mults.SetValue(i + 1, 1)  # Simplified
    
    v_knots = TColStd_Array1OfReal(1, len(surface.knots_v))
    v_mults = TColStd_Array1OfInteger(1, len(surface.knots_v))
    for i, k in enumerate(surface.knots_v):
        v_knots.SetValue(i + 1, k)
        v_mults.SetValue(i + 1, 1)  # Simplified
    
    # Create BSpline surface
    bspline = Geom_BSplineSurface(
        poles, u_knots, v_knots, u_mults, v_mults,
        degree_u, degree_v
    )
    
    return bspline


def export_step(surfaces: List[MAGNETSurface], filepath: str) -> bool:
    """
    Export MAGNET surfaces to STEP file.
    
    Returns True on success, raises on failure.
    """
    check_pythonocc()
    
    # Create compound to hold all surfaces
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    
    for surface in surfaces:
        bspline = magnet_to_occ_bspline(surface)
        face = BRepBuilderAPI_MakeFace(bspline, 1e-6).Face()
        builder.Add(compound, face)
    
    # Write STEP file
    writer = STEPControl_Writer()
    writer.Transfer(compound, STEPControl_AsIs)
    status = writer.Write(filepath)
    
    if status != IFSelect_RetDone:
        raise IOError(f"STEP export failed with status {status}")
    
    return True


def export_iges(surfaces: List[MAGNETSurface], filepath: str) -> bool:
    """Export MAGNET surfaces to IGES file."""
    check_pythonocc()
    
    writer = IGESControl_Writer()
    
    for surface in surfaces:
        bspline = magnet_to_occ_bspline(surface)
        face = BRepBuilderAPI_MakeFace(bspline, 1e-6).Face()
        writer.AddShape(face)
    
    writer.ComputeModel()
    success = writer.Write(filepath)
    
    if not success:
        raise IOError("IGES export failed")
    
    return True
```

### 6.3.5 Requirements Update

```txt
# requirements.txt - Note: pythonocc requires conda, not pip
geomdl>=5.3.0                   # NURBS manipulation
# pythonocc-core>=7.7.0         # STEP/IGES export (conda only)
```

```bash
# environment.yml for conda
dependencies:
  - python>=3.9
  - pythonocc-core>=7.7.0
  - pip
  - pip:
    - geomdl>=5.3.0
```

### 6.3.6 Acceptance Criteria

| Test | Requirement |
|------|-------------|
| STEP export | Roundtrip: MAGNET → STEP → FreeCAD opens without errors |
| IGES export | Roundtrip: MAGNET → IGES → Rhino opens without errors |
| Surface fidelity | Control points preserved within 1e-6 tolerance |
| Multi-surface | Hull + superstructure exports as single file |

---

# 6.5 Phase 2.5: Weight Estimation Foundation

**Priority:** P0 — **CRITICAL** for accurate physics  
**Current Module:** `magnet/weight/` (10 files: estimator.py, groups.py, stability.py, validators.py)  
**Goal:** Transform parametric-only weight estimation into SWBS-structured, physics-coupled system

> 🔴 **DEPENDENCY:** Requires Phase 0 (E0.4 equilibrium solver) to be complete first.

## 6.5.1 Why Weight is Foundational (Not Optional)

> **"Weight is the entry point to all downstream physics."**

```
Weight (Lightship + Variable)
    │
    ├──► Displacement = Weight / ρ_seawater
    │        │
    │        ├──► Equilibrium Draft (Newton-Raphson)
    │        │        │
    │        │        └──► Wetted Surface Area
    │        │                 │
    │        │                 └──► RESISTANCE CALCULATION
    │        │                          │
    │        │                          └──► Speed / Power
    │        │
    │        └──► Hydrostatics (KB, BM, LCB)
    │
    ├──► VCG (Vertical Center of Gravity)
    │        │
    │        └──► GM = KB + BM - KG  ◄── STABILITY
    │
    └──► LCG (Longitudinal Center of Gravity)
             │
             └──► TRIM CALCULATION
```

**Current Gap:** The existing `magnet/weight/` module uses parametric estimation only. Without SWBS-structured breakdown and tank sounding tables, resistance and stability calculations may have 10-20% error.

### 5.5.1.1 Critical Dependencies & Blockers

> 🔴 **P0 BLOCKER:** Phase 2.5 CANNOT proceed without equilibrium solver fix.

```
Weight Estimation (Phase 2.5)
    │
    └── Requires accurate hydrostatics
            │
            └── Requires equilibrium draft solver (magnet/physics/equilibrium.py)
                    │
                    └── CORTEX_V2 Task E0.4: "Newton-Raphson oscillates at 
                        stepped hull discontinuities"
```

**Impact:** If equilibrium solver is broken, weight → displacement → draft → resistance chain produces garbage. No amount of clean library integration fixes broken physics.

**Required Resolution:**

| Task | Priority | Acceptance Criteria |
|------|----------|---------------------|
| Fix E0.4 Newton-Raphson | **P0** | Converges on stepped hull within 5 iterations |
| Add damping for discontinuities | **P0** | No oscillation on test suite |
| Regression test all hull forms | **P0** | All existing forms still converge |

**Sequence:** E0.4 must be GREEN before Phase 2.5 weight work begins.

### 5.5.1.2 Weight ↔ Hydrostatics Convergence Loop (REQUIRED)

The physics coupling creates a circular dependency that **must be resolved**:

```
compute_hydrostatics_from_geometry(weight_summary)  ← takes weight as input
    │
    ├── Uses displacement from weight_summary to find equilibrium draft
    │
    └── But equilibrium draft affects tank fill volumes...
            │
            └── Which affect weight_summary.deadweight_kg
```

**Required Implementation:**

```python
def converge_weight_hydrostatics(
    state: DesignState,
    initial_draft_m: float,
    tolerance_m: float = 0.01,
    max_iterations: int = 10
) -> Tuple[WeightSummary, HydrostaticsResult]:
    """
    Iterate weight ↔ hydrostatics until convergence.
    
    This is NOT optional. Single-pass is mathematically incorrect.
    """
    draft = initial_draft_m
    
    for i in range(max_iterations):
        # Compute weight at current draft (affects tank fills)
        weight = compute_weight_at_draft(state, draft)
        
        # Compute new draft from weight
        hydro = compute_hydrostatics(state, weight.displacement_kg)
        new_draft = hydro.equilibrium_draft_m
        
        # Check convergence
        if abs(new_draft - draft) < tolerance_m:
            return weight, hydro
        
        draft = new_draft
    
    raise ConvergenceError(f"Weight/hydro failed to converge after {max_iterations} iterations")
```

**Acceptance Criteria:**
- Convergence within 5 iterations for typical designs
- Explicit error if convergence fails (no silent garbage)
- Unit tests for convergence behavior

## 6.5.2 Weight Module Implementation Matrix

> ⚠️ **CLARIFICATION:** These are **new MAGNET modules** implementing standard naval architecture formulas, NOT integrations of external libraries.

| Module | Capability | Formula Source | Product Impact | Effort | North Star |
|--------|------------|----------------|----------------|--------|------------|
| **swbs_adapter.py** | MIL-STD-1399 weight breakdown by SWBS group | MIL-STD-1399 Section 301, NAVSEA SWBS Manual | ✅ **Critical** | 3-5 days | ✅ Pure data |
| **tank_calculator.py** | Tank sounding, capacity curves, trim corrections | Standard hydrostatic interpolation | ✅ **Critical** | 3-5 days | ✅ Pure calc |
| **material_estimator.py** | Material-specific weight factors, VCG corrections | Watson & Gilfillan (1976), Schneekluth (1998) | ✅ **Critical** | 3-5 days | ✅ Pure calc |
| **inclining_sim.py** | Inclining experiment → derive lightship VCG | ASTM F1321, IMO MSC.267(85) | ✅ High | 2-3 days | ✅ Pure calc |

**Key References:**
- Watson, D.G.M. & Gilfillan, A.W. (1976). "Some Ship Design Methods." *RINA Transactions*, Vol. 118
- Schneekluth, H. & Bertram, V. (1998). *Ship Design for Efficiency and Economy*. 2nd ed. Butterworth-Heinemann. ISBN 0-7506-4133-9
- MIL-STD-1399 Section 301: Ship Work Breakdown Structure (publicly available)
- ASTM F1321-92: Standard Guide for Conducting a Stability Test (Inclining and Lightweight Survey)

### Material Selection Architecture

Material is a **user-selectable design parameter** that affects weight estimation. This is NOT a kernel design decision—it's a physical property of construction that the user specifies.

**Supported Materials (Initial Release):**
| Material | State Value | Weight Factor vs Steel | Notes |
|----------|-------------|----------------------|-------|
| **Steel** | `steel` | 1.00 (baseline) | Default, Watson & Gilfillan formulas apply directly |
| **Aluminum** | `aluminum` | ~0.45–0.55 | Representative marine aluminum; higher VCG tendency |
| **Composite** | `composite` | project-specific | Highly variable; requires calibration |

**Future Materials (Extensible):**
- `frp` — Glass reinforced plastic (if used distinctly from `composite` in `MaterialType`)
- `cfrp` — Carbon fiber reinforced plastic (if used distinctly from `composite` in `MaterialType`)

**State Path:** `structural_design.hull_material` (string enum)  
**Default:** `steel`  
**Provenance:** `USER` (explicitly set by user)

### 6.5.3 Priority Ranking

| Priority | Module | Reason |
|----------|--------|--------|
| **P0** | `tank_calculator.py` | Variable weight directly affects LCG/VCG → GM/trim |
| **P0** | `swbs_adapter.py` | Standardized breakdown enables proper validation |
| **P0** | `material_estimator.py` | **Material selection drives all weight calculations** |
| **P1** | `inclining_sim.py` | VCG validation critical for GM accuracy |

### 6.5.3.1 Why Material Selection Matters

> **"Using wrong material properties will corrupt all downstream physics."**

Standard parametric formulas (Watson & Gilfillan, Schneekluth) assume **steel construction**. When users select a different material, the weight estimation system must dispatch to material-specific formulas.

**Impact of Incorrect Material:**
| If User Selects | But System Uses Steel Formulas | Error |
|-----------------|-------------------------------|-------|
| Aluminum | Steel parametrics | **large weight overestimate** |
| Composite/FRP | Steel parametrics | **very large weight overestimate** |

This cascades through:
- Incorrect displacement predictions
- Wrong equilibrium draft  
- Cascading errors in resistance calculations
- Stability margin miscalculations

### 5.5.3.2 Material Properties Comparison

| Property | Steel (AH36) | Aluminum (5083-H116) | Design Impact |
|----------|--------------|---------------------|---------------|
| **Density** | 7,850 kg/m³ | 2,660 kg/m³ | 34% of steel density |
| **Yield Strength** | 355 MPa | 215 MPa | 61% of steel → thicker plates needed |
| **Elastic Modulus** | 206 GPa | 70 GPa | **34% of steel** → more stiffeners for deflection |
| **Fatigue Strength** | Good | Lower | More conservative joint details |
| **Weld Efficiency** | 100% | 67-85% (HAZ) | Reduced strength at welds |
| **Corrosion Allowance** | 2-3mm | 0mm | No wastage margin needed |
| **Typical Plate (30m workboat)** | 6-8mm | 8-12mm | Thicker to compensate stiffness |
| **Stiffener Spacing** | 500-600mm | 350-450mm | Closer spacing for buckling |

**Hull Weight Factors by Material (Relative to Steel):**

| Vessel Type | Steel | Aluminum | Composite GRP |
|-------------|-------|----------|---------------|
| Fast Patrol (<25m) | 1.00 | 0.45-0.50 | 0.30-0.40 |
| Workboat (20-40m) | 1.00 | 0.48-0.55 | 0.35-0.45 |
| Crew Boat (30-50m) | 1.00 | 0.50-0.55 | — |
| Ferry (passenger) | 1.00 | 0.55-0.60 | — |

**VCG Shift by Material:**
```
Non-steel materials have HIGHER VCG than steel for equivalent vessel:
- Hull structure (low in ship) becomes lighter
- Machinery (medium height) weight unchanged
- Outfit (high in ship) weight unchanged
- Superstructure may be lighter

Result: Overall CG shifts UP
- Aluminum: +5-10% of depth
- Composite: +8-15% of depth
```

## 5.5.4 Integration Architecture

### Weight State Schema Extension

```python
# magnet/core/dataclasses.py additions

@dataclass
class WeightGroup:
    """SWBS-compliant weight group."""
    swbs_code: str              # e.g., "100" (Hull Structure), "200" (Propulsion)
    name: str
    weight_kg: float
    lcg_m: float                # Longitudinal CG from AP
    vcg_m: float                # Vertical CG from baseline
    tcg_m: float                # Transverse CG from centerline
    moment_x_kg_m: float        # weight × lcg
    moment_z_kg_m: float        # weight × vcg
    source: str                 # "parametric" | "database" | "user_input" | "inclining"
    confidence: float           # 0-1


@dataclass
class TankState:
    """Individual tank state for variable weight tracking."""
    tank_id: str
    tank_type: str              # "fuel" | "freshwater" | "ballast" | "cargo"
    capacity_m3: float
    fill_percent: float         # 0-100
    contents_density_kg_m3: float
    weight_kg: float            # computed: capacity × fill × density
    lcg_m: float                # from sounding table interpolation
    vcg_m: float
    tcg_m: float
    free_surface_moment_m4: float  # for GM correction


@dataclass 
class WeightSummary:
    """Canonical weight summary for physics coupling."""
    lightship_kg: float
    lightship_lcg_m: float
    lightship_vcg_m: float
    
    deadweight_kg: float        # variable loads
    deadweight_lcg_m: float
    deadweight_vcg_m: float
    
    displacement_kg: float      # lightship + deadweight
    displacement_lcg_m: float   # combined LCG
    displacement_vcg_m: float   # combined VCG (KG)
    
    free_surface_correction_m: float  # GM reduction from tank slosh
    
    # SWBS breakdown
    groups: List[WeightGroup]
    tanks: List[TankState]
    
    # Provenance
    estimation_method: str      # "parametric" | "swbs_detailed" | "inclining_derived"
    confidence: str             # "high" | "medium" | "low"
```

### SWBS Weight Group Integration

**CREATE `magnet/weight/swbs_adapter.py`:**

```python
"""
SWBS (Ship Work Breakdown Structure) weight group adapter.

Integrates with Navy MIL-STD-1399 and commercial SWBS databases
while maintaining MAGNET-native state representation.

North Star Compliance:
- All inputs/outputs are MAGNET-native types
- No external library objects in DesignState
- Graceful fallback to parametric estimation
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# SWBS Group Definitions (MIL-STD-1399 / commercial hybrid)
SWBS_GROUPS = {
    "100": "Hull Structure",
    "200": "Propulsion Plant", 
    "300": "Electric Plant",
    "400": "Command and Surveillance",
    "500": "Auxiliary Systems",
    "600": "Outfit and Furnishings",
    "700": "Armament (or Cargo Handling)",
    "F00": "Full Load (Variable)",
    "M00": "Margins",
}


@dataclass
class SWBSEstimate:
    """SWBS-based weight estimate result."""
    group_code: str
    group_name: str
    weight_kg: float
    lcg_fraction: float         # as fraction of LWL from AP
    vcg_fraction: float         # as fraction of depth from baseline
    estimation_method: str
    confidence: float


def estimate_swbs_groups(
    loa_m: float,
    beam_m: float,
    depth_m: float,
    draft_m: float,
    cb: float,
    vessel_type: str = "commercial",
    material: str = "steel"
) -> List[SWBSEstimate]:
    """
    Estimate weight by SWBS group using parametric relationships.
    
    Uses Watson & Gilfillan, Schneekluth, and Navy parametric data.
    """
    estimates = []
    
    # Cubic number for scaling
    cubic_number = loa_m * beam_m * depth_m
    
    # Group 100: Hull Structure (Watson & Gilfillan)
    if material == "steel":
        # Ws = K × L^1.36 × B^0.53 × D^0.61 × Cb^0.69
        k_hull = 0.034 if vessel_type == "commercial" else 0.041  # naval higher
        w_hull = k_hull * (loa_m ** 1.36) * (beam_m ** 0.53) * (depth_m ** 0.61) * (cb ** 0.69) * 1000
    elif material == "aluminum":
        w_hull = 0.5 * k_hull * (loa_m ** 1.36) * (beam_m ** 0.53) * (depth_m ** 0.61) * (cb ** 0.69) * 1000
    else:
        w_hull = 0.35 * cubic_number * 7.85  # Simplified for composite
    
    estimates.append(SWBSEstimate(
        group_code="100",
        group_name="Hull Structure",
        weight_kg=w_hull,
        lcg_fraction=0.52,      # Typically slightly aft of midships
        vcg_fraction=0.45,      # Below mid-depth
        estimation_method="watson_gilfillan",
        confidence=0.85
    ))
    
    # Group 200: Propulsion Plant (parametric by power)
    # Estimate installed power from Admiralty coefficient
    estimated_power_kw = (cubic_number * 0.15) ** 0.67 * 100  # Rough estimate
    w_propulsion = 0.075 * estimated_power_kw * 1000 / 1000  # kg
    
    estimates.append(SWBSEstimate(
        group_code="200",
        group_name="Propulsion Plant",
        weight_kg=w_propulsion,
        lcg_fraction=0.35,      # Engine room typically aft
        vcg_fraction=0.25,      # Low in hull
        estimation_method="parametric_power",
        confidence=0.75
    ))
    
    # Group 300: Electric Plant
    w_electric = 0.02 * w_hull  # ~2% of hull
    estimates.append(SWBSEstimate(
        group_code="300",
        group_name="Electric Plant",
        weight_kg=w_electric,
        lcg_fraction=0.40,
        vcg_fraction=0.35,
        estimation_method="fraction_of_hull",
        confidence=0.70
    ))
    
    # Group 500: Auxiliary Systems
    w_auxiliary = 0.08 * w_hull
    estimates.append(SWBSEstimate(
        group_code="500",
        group_name="Auxiliary Systems",
        weight_kg=w_auxiliary,
        lcg_fraction=0.50,
        vcg_fraction=0.40,
        estimation_method="fraction_of_hull",
        confidence=0.70
    ))
    
    # Group 600: Outfit and Furnishings
    w_outfit = 0.12 * w_hull
    estimates.append(SWBSEstimate(
        group_code="600",
        group_name="Outfit and Furnishings",
        weight_kg=w_outfit,
        lcg_fraction=0.55,
        vcg_fraction=0.65,      # Higher (superstructure)
        estimation_method="fraction_of_hull",
        confidence=0.65
    ))
    
    # Group M00: Margins (typically 3-10%)
    subtotal = sum(e.weight_kg for e in estimates)
    margin_percent = 0.05 if vessel_type == "commercial" else 0.08
    w_margin = subtotal * margin_percent
    
    estimates.append(SWBSEstimate(
        group_code="M00",
        group_name="Margins",
        weight_kg=w_margin,
        lcg_fraction=0.50,      # Distributed
        vcg_fraction=0.50,
        estimation_method="percentage_margin",
        confidence=0.90
    ))
    
    return estimates


def compute_lightship_from_swbs(
    estimates: List[SWBSEstimate],
    lwl_m: float,
    depth_m: float
) -> Tuple[float, float, float]:
    """
    Compute lightship weight and CG from SWBS breakdown.
    
    Returns: (lightship_kg, lcg_m, vcg_m)
    """
    total_weight = 0.0
    moment_x = 0.0
    moment_z = 0.0
    
    for est in estimates:
        total_weight += est.weight_kg
        lcg_m = est.lcg_fraction * lwl_m
        vcg_m = est.vcg_fraction * depth_m
        moment_x += est.weight_kg * lcg_m
        moment_z += est.weight_kg * vcg_m
    
    lcg = moment_x / total_weight if total_weight > 0 else 0
    vcg = moment_z / total_weight if total_weight > 0 else 0
    
    return total_weight, lcg, vcg
```

### Aluminum/Composite Weight Estimation

**CREATE `magnet/weight/material_estimator.py`:**

```python
"""
Material-aware weight estimation for hull structures.

Supports multiple construction materials with material-specific
parametric corrections, VCG adjustments, and weld factors.

ARCHITECTURE INTEGRATION:
- Material is stored in DesignState at `structural_design.hull_material` (MaterialType enum)
- Weight estimators read material from state and dispatch accordingly
- Default material is STEEL (backward compatible)
- Material affects: hull weight, VCG position, weld allowances, margins

> ⚠️ AUDIT CORRECTION: Uses EXISTING MaterialType enum from magnet/core/enums.py (L101-114).
> Do NOT create a new MaterialType enum - this would violate the "no new enums" gate.

North Star Compliance:
- Material selection is USER INPUT, not kernel design intent
- Pure calculation utility with no design suggestions
- All outputs are MAGNET-native types
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Use EXISTING enum - do not create new enum
from magnet.core.enums import MaterialType


@dataclass
class MaterialProperties:
    """
    Physical and structural properties for weight estimation.
    
    These are PHYSICAL FACTS about materials, not design preferences.
    """
    name: str
    density_kg_m3: float
    yield_strength_mpa: float
    elastic_modulus_gpa: float
    
    # Weight factors relative to steel (for equivalent structural capacity)
    hull_weight_factor: float       # Multiplier vs steel hull weight
    superstructure_factor: float    # Often different (more structure above WL)
    
    # Construction factors
    weld_weight_addition: float     # % added for welds/brackets
    paint_weight_kg_m2: float       # Coating weight per surface area
    
    # VCG correction (fraction of depth to add to steel-based VCG)
    vcg_correction_factor: float    # Typically positive for lighter materials


# =============================================================================
# MATERIAL DATABASE
# =============================================================================
# 
# SOURCES FOR PROPERTY VALUES:
# 
# Density, yield strength, elastic modulus:
#   - ASM Handbook, Volume 2: Properties and Selection: Nonferrous Alloys
#   - ASTM Standards (A36, B209)
#   - Aluminum Association: Aluminum Standards and Data
#
# Hull weight factors (aluminum vs steel):
#   - Lamb, T. (2003). "Ship Design and Construction", Ch. 23 (Aluminum craft)
#   - Watson, D.G.M. (1998). "Practical Ship Design", Table 6.7
#   - Schneekluth, H. & Bertram, V. (1998). "Ship Design for Efficiency and 
#     Economy", Section 4.1.4 (aluminum correction factors)
#   - Factor of 0.45-0.55 accounts for: thicker plating (lower yield), closer
#     stiffener spacing (lower elastic modulus), higher weld allowance
#
# VCG correction factors:
#   - Empirical data from inclining tests of sister ships in steel vs aluminum
#   - Watson (1998) discusses VCG shift due to lightened hull structure
#
# =============================================================================

MATERIAL_PROPERTIES: Dict[MaterialType, MaterialProperties] = {
    MaterialType.STEEL: MaterialProperties(
        name="Steel (A36/AH36)",
        density_kg_m3=7850,              # ASTM A36
        yield_strength_mpa=250,           # ASTM A36 minimum
        elastic_modulus_gpa=200,          # Standard steel
        hull_weight_factor=1.0,           # Baseline
        superstructure_factor=1.0,
        weld_weight_addition=0.03,        # 3% typical (Schneekluth Table 4.2)
        paint_weight_kg_m2=0.3,           # Typical marine coating system
        vcg_correction_factor=0.0,        # Baseline
    ),
    # NOTE: The existing codebase enum is coarse (e.g., "aluminum"), not grade-specific.
    # Grade-level selection (5083/6061/5086) must NOT be modeled as new enum members.
    MaterialType.ALUMINUM: MaterialProperties(
        name="Aluminum (representative marine alloy)",
        density_kg_m3=2660,               # Typical marine aluminum alloy density
        yield_strength_mpa=215,           # Representative (e.g., 5083-H116 order of magnitude)
        elastic_modulus_gpa=70,           # Aluminum typical
        hull_weight_factor=0.50,          # 0.45–0.55 representative range
        superstructure_factor=0.45,
        weld_weight_addition=0.05,        # Higher weld/HAZ allowances vs steel
        paint_weight_kg_m2=0.15,
        vcg_correction_factor=0.06,       # Representative VCG shift (fraction of depth)
    ),
    MaterialType.COMPOSITE: MaterialProperties(
        name="Composite (generic)",
        density_kg_m3=1600,               # Highly variable; representative placeholder
        yield_strength_mpa=0,             # Not directly comparable to isotropic yield
        elastic_modulus_gpa=0,            # Highly configuration-dependent
        hull_weight_factor=0.35,          # Representative only; must be calibrated per build method
        superstructure_factor=0.30,
        weld_weight_addition=0.0,
        paint_weight_kg_m2=0.20,
        vcg_correction_factor=0.08,
    ),
}


def get_material_properties(material: MaterialType) -> MaterialProperties:
    """
    Get properties for a material, with fallback to steel.
    
    This is the ONLY place material dispatch should happen.
    """
    return MATERIAL_PROPERTIES.get(material, MATERIAL_PROPERTIES[MaterialType.STEEL])


@dataclass
class MaterialWeightEstimate:
    """Weight estimate with material correction applied."""
    group_code: str
    group_name: str
    
    # Steel-equivalent weight (from parametric formulas)
    steel_equivalent_kg: float
    
    # Actual weight for selected material
    actual_weight_kg: float
    
    # Factors applied
    material: MaterialType
    material_factor: float
    weld_addition_kg: float
    
    # CG positions
    lcg_fraction: float
    vcg_fraction: float
    
    # Provenance
    estimation_method: str
    confidence: float


def estimate_hull_weight_by_material(
    loa_m: float,
    beam_m: float,
    depth_m: float,
    draft_m: float,
    cb: float,
    material: MaterialType = MaterialType.STEEL,
    vessel_type: str = "workboat",
    has_superstructure: bool = True,
    superstructure_volume_m3: Optional[float] = None
) -> List[MaterialWeightEstimate]:
    """
    Estimate vessel weight by SWBS group with material correction.
    
    Method:
    1. Calculate steel-equivalent weight using parametric formulas
    2. Apply material-specific factors from MATERIAL_PROPERTIES
    3. Add weld/construction allowances
    4. Adjust VCG for material effects
    
    Args:
        loa_m: Length overall
        beam_m: Maximum beam
        depth_m: Depth to main deck
        draft_m: Design draft
        cb: Block coefficient
        material: Construction material (from structural_design.hull_material state)
        vessel_type: "workboat", "patrol", "ferry", "yacht"
        has_superstructure: Whether vessel has superstructure
        superstructure_volume_m3: Volume of superstructure (optional)
        
    Returns:
        List of MaterialWeightEstimate by SWBS group
    """
    props = get_material_properties(material)
    estimates = []
    
    # Cubic number for scaling
    cubic_number = loa_m * beam_m * depth_m
    
    # =========================================================================
    # Group 100: Hull Structure
    # =========================================================================
    
    # Steel equivalent using Watson & Gilfillan parametric formula
    # 
    # SOURCE: Watson, D.G.M. & Gilfillan, A.W. (1976). "Some Ship Design Methods."
    #         Transactions of the Royal Institution of Naval Architects, Vol. 118.
    #         Table 3: Steel hull weight coefficients
    #
    # Formula: W_hull = k * L^1.36 * B^0.53 * D^0.61 * Cb^0.69 (tonnes)
    # 
    # k values from Watson (1998) "Practical Ship Design", Table 6.3:
    #   - General cargo: 0.021-0.028
    #   - Tanker: 0.024-0.032  
    #   - Patrol/workboat: 0.030-0.038
    #
    k_hull_steel = 0.034 if vessel_type in ["workboat", "patrol"] else 0.028
    w_hull_steel = k_hull_steel * (loa_m ** 1.36) * (beam_m ** 0.53) * (depth_m ** 0.61) * (cb ** 0.69) * 1000
    
    # Apply material factor
    w_hull_material = w_hull_steel * props.hull_weight_factor
    
    # Add weld weight
    weld_addition = w_hull_material * props.weld_weight_addition
    w_hull_total = w_hull_material + weld_addition
    
    # VCG - hull structure is low in ship, material affects overall VCG
    vcg_ratio_hull = 0.42 + props.vcg_correction_factor * 0.5  # Partial correction for hull
    
    estimates.append(MaterialWeightEstimate(
        group_code="100",
        group_name="Hull Structure",
        steel_equivalent_kg=w_hull_steel,
        actual_weight_kg=w_hull_total,
        material=material,
        material_factor=props.hull_weight_factor,
        weld_addition_kg=weld_addition,
        lcg_fraction=0.52,
        vcg_fraction=vcg_ratio_hull,
        estimation_method="watson_gilfillan_material_corrected",
        confidence=0.80 if material == MaterialType.STEEL else 0.75
    ))
    
    # =========================================================================
    # Group 200: Propulsion Plant (mostly material-independent)
    # =========================================================================
    
    estimated_power_kw = (cubic_number * 0.18) ** 0.67 * 100
    w_propulsion = 0.08 * estimated_power_kw * 1000 / 1000
    
    # Slight reduction for non-steel foundations
    foundation_factor = 1.0 if material == MaterialType.STEEL else 0.95
    
    estimates.append(MaterialWeightEstimate(
        group_code="200",
        group_name="Propulsion Plant",
        steel_equivalent_kg=w_propulsion,
        actual_weight_kg=w_propulsion * foundation_factor,
        material=material,
        material_factor=foundation_factor,
        weld_addition_kg=0,
        lcg_fraction=0.30,
        vcg_fraction=0.25,
        estimation_method="parametric_power",
        confidence=0.75
    ))
    
    # =========================================================================
    # Group 300: Electric Plant (material-independent)
    # =========================================================================
    
    w_electric = 0.025 * w_hull_steel
    
    estimates.append(MaterialWeightEstimate(
        group_code="300",
        group_name="Electric Plant",
        steel_equivalent_kg=w_electric,
        actual_weight_kg=w_electric,
        material=material,
        material_factor=1.0,
        weld_addition_kg=0,
        lcg_fraction=0.35,
        vcg_fraction=0.40,
        estimation_method="fraction_of_hull",
        confidence=0.70
    ))
    
    # =========================================================================
    # Group 500: Auxiliary Systems (partially material-dependent)
    # =========================================================================
    
    w_auxiliary = 0.07 * w_hull_steel
    aux_factor = 1.0 if material == MaterialType.STEEL else 0.90  # Some Al piping/tanks
    
    estimates.append(MaterialWeightEstimate(
        group_code="500",
        group_name="Auxiliary Systems",
        steel_equivalent_kg=w_auxiliary,
        actual_weight_kg=w_auxiliary * aux_factor,
        material=material,
        material_factor=aux_factor,
        weld_addition_kg=0,
        lcg_fraction=0.50,
        vcg_fraction=0.45,
        estimation_method="fraction_of_hull",
        confidence=0.70
    ))
    
    # =========================================================================
    # Group 600: Outfit and Furnishings (material-independent)
    # =========================================================================
    
    w_outfit = 0.15 * w_hull_steel
    
    # VCG for outfit is HIGH and contributes to VCG rise in lightweight hulls
    vcg_outfit = 0.70 + props.vcg_correction_factor * 0.3
    
    estimates.append(MaterialWeightEstimate(
        group_code="600",
        group_name="Outfit and Furnishings",
        steel_equivalent_kg=w_outfit,
        actual_weight_kg=w_outfit,
        material=material,
        material_factor=1.0,
        weld_addition_kg=0,
        lcg_fraction=0.55,
        vcg_fraction=vcg_outfit,
        estimation_method="fraction_of_hull",
        confidence=0.65
    ))
    
    # =========================================================================
    # Superstructure (if applicable)
    # =========================================================================
    
    if has_superstructure:
        if superstructure_volume_m3:
            w_super_steel = superstructure_volume_m3 * 120
        else:
            w_super_steel = 0.08 * w_hull_steel
        
        w_super_material = w_super_steel * props.superstructure_factor
        
        estimates.append(MaterialWeightEstimate(
            group_code="150",
            group_name="Superstructure",
            steel_equivalent_kg=w_super_steel,
            actual_weight_kg=w_super_material,
            material=material,
            material_factor=props.superstructure_factor,
            weld_addition_kg=w_super_material * props.weld_weight_addition,
            lcg_fraction=0.45,
            vcg_fraction=0.85,
            estimation_method="volume_based" if superstructure_volume_m3 else "fraction_of_hull",
            confidence=0.70
        ))
    
    # =========================================================================
    # Group M00: Margins
    # =========================================================================
    
    subtotal = sum(e.actual_weight_kg for e in estimates)
    
    # Higher margin for non-steel (less empirical data)
    margin_percent = 0.05 if material == MaterialType.STEEL else 0.07
    w_margin = subtotal * margin_percent
    
    estimates.append(MaterialWeightEstimate(
        group_code="M00",
        group_name="Margins",
        steel_equivalent_kg=w_margin / props.hull_weight_factor if props.hull_weight_factor > 0 else w_margin,
        actual_weight_kg=w_margin,
        material=material,
        material_factor=1.0,
        weld_addition_kg=0,
        lcg_fraction=0.50,
        vcg_fraction=0.55,
        estimation_method="percentage_margin",
        confidence=0.85
    ))
    
    return estimates


def compute_lightship_from_material_estimates(
    estimates: List[MaterialWeightEstimate],
    lwl_m: float,
    depth_m: float
) -> Tuple[float, float, float, Dict[str, float]]:
    """
    Compute lightship weight and CG from material-adjusted estimates.
    
    Returns: (lightship_kg, lcg_m, vcg_m, comparison_dict)
    
    comparison_dict contains:
    - steel_equivalent_kg: What this would weigh in steel
    - weight_difference_kg: Difference from steel (negative = lighter)
    - weight_difference_percent: Percentage difference
    - material: Material used
    """
    total_actual = 0.0
    total_steel_equiv = 0.0
    moment_x = 0.0
    moment_z = 0.0
    material_used = MaterialType.STEEL
    
    for est in estimates:
        total_actual += est.actual_weight_kg
        total_steel_equiv += est.steel_equivalent_kg
        lcg_m = est.lcg_fraction * lwl_m
        vcg_m = est.vcg_fraction * depth_m
        moment_x += est.actual_weight_kg * lcg_m
        moment_z += est.actual_weight_kg * vcg_m
        material_used = est.material
    
    lcg = moment_x / total_actual if total_actual > 0 else 0
    vcg = moment_z / total_actual if total_actual > 0 else 0
    
    weight_diff = total_actual - total_steel_equiv
    
    comparison = {
        'steel_equivalent_kg': total_steel_equiv,
        'weight_difference_kg': weight_diff,
        'weight_difference_percent': (weight_diff / total_steel_equiv * 100) if total_steel_equiv > 0 else 0,
        'material': material_used.value,
    }
    
    return total_actual, lcg, vcg, comparison
```

### State Integration for Material Selection

**USE EXISTING `magnet/core/enums.py` MaterialType:**

> ⚠️ **AUDIT CORRECTION:** Do NOT add a new MaterialType enum. The codebase already has `MaterialType` at `magnet/core/enums.py` (L101-114) which includes STEEL, ALUMINUM, COMPOSITE, etc.

```python
# EXISTING - DO NOT DUPLICATE
class MaterialType(Enum):
    """Existing enum in magnet/core/enums.py - USE THIS"""
    STEEL = "steel"
    ALUMINUM = "aluminum"
    COMPOSITE = "composite"
    # ... other values
```

**EXISTING State Path:** `structural_design.hull_material` (in `magnet/core/dataclasses.py` L408-416)

> **Note:** The aluminum grades (5083, 6061, 5086) are handled via weight factor lookup tables, not enum values. The enum value is just "aluminum" and the specific grade is handled in weight estimation logic.

### Weight Estimator Dispatch Pattern

The existing `magnet/weight/estimator.py` should dispatch based on material:

```python
# magnet/weight/estimator.py update

from magnet.core.enums import MaterialType
from magnet.weight.material_estimator import (
    estimate_hull_weight_by_material,
    compute_lightship_from_material_estimates,
)

def estimate_lightship(state_manager: StateManager) -> WeightSummary:
    """
    Estimate lightship weight using material-appropriate formulas.
    
    Reads structural_design.hull_material from state and dispatches to correct estimator.
    """
    # Get material from state (default to steel for backward compatibility)
    material_str = state_manager.get('structural_design.hull_material', 'steel')
    try:
        material = MaterialType(material_str)
    except ValueError:
        material = MaterialType.STEEL
        logger.warning(f"Unknown material '{material_str}', defaulting to steel")
    
    # Get dimensions
    loa = state_manager.get('hull.loa')
    beam = state_manager.get('hull.beam')
    depth = state_manager.get('hull.depth')
    draft = state_manager.get('hull.draft')
    cb = state_manager.get('hull.cb', 0.45)
    
    # Estimate with material correction
    estimates = estimate_hull_weight_by_material(
        loa_m=loa,
        beam_m=beam,
        depth_m=depth,
        draft_m=draft,
        cb=cb,
        material=material,
        vessel_type=state_manager.get('mission.vessel_type', 'workboat')
    )
    
    lightship, lcg, vcg, comparison = compute_lightship_from_material_estimates(
        estimates, lwl_m=loa * 0.95, depth_m=depth
    )
    
    return WeightSummary(
        lightship_kg=lightship,
        lightship_lcg_m=lcg,
        lightship_vcg_m=vcg,
        # ... other fields ...
        estimation_method=f"swbs_material_corrected_{material.value}",
        confidence="high" if material == MaterialType.STEEL else "medium"
    )
```

**CREATE `magnet/weight/tank_calculator.py`:**

```python
"""
Tank capacity and sounding table calculator.

Computes variable weight contribution to displacement, LCG, VCG, and
free surface correction for GM.

North Star Compliance:
- Pure calculation utility
- No design intent in kernel
- MAGNET-native outputs only
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from scipy import interpolate


@dataclass
class SoundingTableEntry:
    """Single entry in a tank sounding table."""
    sounding_m: float           # Depth of liquid from tank bottom
    fill_percent: float         # 0-100
    volume_m3: float
    lcg_m: float                # CG of liquid at this fill level
    vcg_m: float
    tcg_m: float
    free_surface_inertia_m4: float  # For free surface correction


@dataclass
class TankDefinition:
    """Tank geometry and properties."""
    tank_id: str
    tank_type: str              # "fuel", "freshwater", "ballast", "cargo_liquid"
    capacity_m3: float
    length_m: float
    breadth_m: float
    height_m: float
    lcg_empty_m: float          # Tank centroid position
    vcg_empty_m: float
    tcg_empty_m: float
    sounding_table: List[SoundingTableEntry]


class TankCalculator:
    """
    Calculates tank state and contributions to ship weight/CG.
    
    Handles:
    - Fill level → volume/weight interpolation
    - CG shift with fill level
    - Free surface moment for GM correction
    - Trim/list corrections (advanced)
    """
    
    def __init__(self, tanks: List[TankDefinition]):
        self.tanks = {t.tank_id: t for t in tanks}
        self._interpolators = {}
        self._build_interpolators()
    
    def _build_interpolators(self):
        """Build interpolation functions for each tank."""
        for tank_id, tank in self.tanks.items():
            if not tank.sounding_table:
                continue
            
            fills = [e.fill_percent for e in tank.sounding_table]
            volumes = [e.volume_m3 for e in tank.sounding_table]
            lcgs = [e.lcg_m for e in tank.sounding_table]
            vcgs = [e.vcg_m for e in tank.sounding_table]
            fs_inertias = [e.free_surface_inertia_m4 for e in tank.sounding_table]
            
            self._interpolators[tank_id] = {
                'volume': interpolate.interp1d(fills, volumes, fill_value='extrapolate'),
                'lcg': interpolate.interp1d(fills, lcgs, fill_value='extrapolate'),
                'vcg': interpolate.interp1d(fills, vcgs, fill_value='extrapolate'),
                'fs_inertia': interpolate.interp1d(fills, fs_inertias, fill_value='extrapolate'),
            }
    
    def compute_tank_state(
        self,
        tank_id: str,
        fill_percent: float,
        contents_density_kg_m3: float
    ) -> Dict[str, float]:
        """
        Compute weight and CG for a tank at given fill level.
        
        Args:
            tank_id: Tank identifier
            fill_percent: 0-100
            contents_density_kg_m3: Density of contents (fuel ~850, FW ~1000, SW ~1025)
            
        Returns:
            Dict with weight_kg, lcg_m, vcg_m, tcg_m, free_surface_moment_m4
        """
        tank = self.tanks.get(tank_id)
        if not tank:
            raise ValueError(f"Unknown tank: {tank_id}")
        
        fill = np.clip(fill_percent, 0, 100)
        
        if tank_id in self._interpolators:
            interp = self._interpolators[tank_id]
            volume = float(interp['volume'](fill))
            lcg = float(interp['lcg'](fill))
            vcg = float(interp['vcg'](fill))
            fs_inertia = float(interp['fs_inertia'](fill))
        else:
            # Simple linear approximation if no sounding table
            volume = tank.capacity_m3 * fill / 100
            lcg = tank.lcg_empty_m
            vcg = tank.vcg_empty_m * (fill / 100) * 0.5  # Approximate
            fs_inertia = (tank.length_m * tank.breadth_m ** 3) / 12  # Rectangle
        
        weight = volume * contents_density_kg_m3
        
        # Free surface moment = inertia × density_ratio
        # Only applies for partially filled tanks (5-95%)
        if 5 < fill < 95:
            fs_moment = fs_inertia * contents_density_kg_m3 / 1025  # Normalized to SW
        else:
            fs_moment = 0.0
        
        return {
            'weight_kg': weight,
            'volume_m3': volume,
            'lcg_m': lcg,
            'vcg_m': vcg,
            'tcg_m': tank.tcg_empty_m,
            'free_surface_moment_m4': fs_moment,
        }
    
    def compute_total_variable_weight(
        self,
        tank_fills: Dict[str, Tuple[float, float]]  # tank_id → (fill%, density)
    ) -> Dict[str, float]:
        """
        Compute total variable weight contribution from all tanks.
        
        Returns:
            Dict with total_weight_kg, lcg_m, vcg_m, total_fs_moment_m4
        """
        total_weight = 0.0
        moment_x = 0.0
        moment_z = 0.0
        total_fs = 0.0
        
        for tank_id, (fill, density) in tank_fills.items():
            state = self.compute_tank_state(tank_id, fill, density)
            w = state['weight_kg']
            total_weight += w
            moment_x += w * state['lcg_m']
            moment_z += w * state['vcg_m']
            total_fs += state['free_surface_moment_m4']
        
        lcg = moment_x / total_weight if total_weight > 0 else 0
        vcg = moment_z / total_weight if total_weight > 0 else 0
        
        return {
            'total_weight_kg': total_weight,
            'lcg_m': lcg,
            'vcg_m': vcg,
            'total_fs_moment_m4': total_fs,
        }


def compute_free_surface_correction(
    free_surface_moment_m4: float,
    displacement_kg: float,
    seawater_density: float = 1025.0
) -> float:
    """
    Compute GM reduction due to free surface effect.
    
    ΔGM = Σ(i × ρ_liquid) / Δ
    
    Returns: GM correction in meters (always negative effect on stability)
    """
    displacement_m3 = displacement_kg / seawater_density
    if displacement_m3 <= 0:
        return 0.0
    
    return free_surface_moment_m4 / displacement_m3
```

### Inclining Experiment Simulator

**CREATE `magnet/weight/inclining_sim.py`:**

```python
"""
Inclining experiment simulator for VCG derivation.

Simulates the classical inclining test to derive lightship VCG
from measured heel angles with known shifting weights.

Critical for GM validation and calibration.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class InclineReading:
    """Single reading from inclining experiment."""
    weight_shifted_kg: float
    shift_distance_m: float     # Transverse distance
    heel_angle_deg: float       # Measured heel
    gm_derived_m: float         # GM = (w × d) / (Δ × tan(θ))


@dataclass
class InclineResult:
    """Result of inclining experiment analysis."""
    lightship_kg: float
    lightship_lcg_m: float
    lightship_vcg_m: float      # The key output
    gm_measured_m: float
    readings: List[InclineReading]
    confidence: str             # "high" if readings consistent


def simulate_incline_experiment(
    displacement_kg: float,
    kb_m: float,
    bm_m: float,
    true_vcg_m: float,          # "Unknown" value we're trying to find
    incline_weights: List[Tuple[float, float]],  # [(weight_kg, shift_dist_m), ...]
    noise_deg: float = 0.1      # Measurement noise
) -> InclineResult:
    """
    Simulate inclining experiment to derive VCG.
    
    The actual VCG (true_vcg_m) is treated as unknown;
    we derive it from the heel response.
    
    GM = KB + BM - KG → KG = KB + BM - GM
    GM_measured = (w × d) / (Δ × tan(θ))
    """
    true_gm = kb_m + bm_m - true_vcg_m
    readings = []
    gm_values = []
    
    for weight_kg, shift_m in incline_weights:
        # True heel angle from physics
        tan_theta = (weight_kg * shift_m) / (displacement_kg * true_gm)
        theta_true = np.degrees(np.arctan(tan_theta))
        
        # Add measurement noise
        theta_measured = theta_true + np.random.normal(0, noise_deg)
        
        # Derive GM from measurement
        tan_measured = np.tan(np.radians(theta_measured))
        if abs(tan_measured) > 1e-6:
            gm_derived = (weight_kg * shift_m) / (displacement_kg * tan_measured)
        else:
            gm_derived = float('inf')
        
        gm_values.append(gm_derived)
        readings.append(InclineReading(
            weight_shifted_kg=weight_kg,
            shift_distance_m=shift_m,
            heel_angle_deg=theta_measured,
            gm_derived_m=gm_derived
        ))
    
    # Average GM from readings
    gm_avg = np.mean([r.gm_derived_m for r in readings if np.isfinite(r.gm_derived_m)])
    
    # Derive VCG: KG = KB + BM - GM
    vcg_derived = kb_m + bm_m - gm_avg
    
    # Confidence based on reading consistency
    gm_std = np.std([r.gm_derived_m for r in readings if np.isfinite(r.gm_derived_m)])
    confidence = "high" if gm_std < 0.05 else "medium" if gm_std < 0.15 else "low"
    
    return InclineResult(
        lightship_kg=displacement_kg,  # In real test, this is measured
        lightship_lcg_m=0.0,            # Would come from draft readings
        lightship_vcg_m=vcg_derived,
        gm_measured_m=gm_avg,
        readings=readings,
        confidence=confidence
    )
```

## 5.5.5 Physics Coupling Updates

The weight system must feed directly into hydrostatics and resistance:

```python
# magnet/physics/geometry_hydrostatics.py updates

def compute_hydrostatics_from_geometry(
    geometry: HullGeometry,
    draft: float,
    weight_summary: Optional[WeightSummary] = None,  # NEW: explicit weight input
    vcg: Optional[float] = None,  # DEPRECATED: use weight_summary.displacement_vcg_m
    seawater_density: float = 1025.0
) -> HydrostaticsResult:
    """
    Compute hydrostatics from actual geometry sections.
    
    If weight_summary provided:
    - Uses displacement_vcg_m for KG (more accurate)
    - Applies free_surface_correction to GM
    - Validates displacement_kg ≈ ρ × ∇ (equilibrium check)
    """
    # ... existing computation ...
    
    if weight_summary:
        kg = weight_summary.displacement_vcg_m
        fs_correction = weight_summary.free_surface_correction_m
        
        # GM with free surface correction
        gm_corrected = kb + bm - kg - fs_correction
        
        # Equilibrium validation
        expected_disp_kg = displacement_m3 * seawater_density
        actual_disp_kg = weight_summary.displacement_kg
        disp_error_pct = abs(expected_disp_kg - actual_disp_kg) / expected_disp_kg * 100
        
        if disp_error_pct > 5:
            warnings.append(f"Displacement mismatch: computed {expected_disp_kg:.0f} kg vs weight {actual_disp_kg:.0f} kg ({disp_error_pct:.1f}%)")
```

## 5.5.6 Validator Updates

**UPDATE `magnet/weight/validators.py`:**

```python
class WeightEstimationValidator:
    """
    CRITICAL validator for weight estimation accuracy.
    
    Enhanced to:
    1. Validate SWBS group breakdown if available
    2. Check lightship + variable = displacement
    3. Verify VCG within reasonable bounds
    4. Flag high free surface moments
    """
    
    def validate(self, state_manager: StateManager) -> ValidatorResult:
        weight = state_manager.get('weight')
        hydro = state_manager.get('physics.hydrostatics')
        
        errors = []
        warnings = []
        
        # 1. Displacement equilibrium check
        if weight and hydro:
            computed_disp = hydro.displacement_kg
            stated_disp = weight.displacement_kg
            error_pct = abs(computed_disp - stated_disp) / computed_disp * 100
            
            if error_pct > 10:
                errors.append(f"Weight/displacement mismatch: {error_pct:.1f}%")
            elif error_pct > 5:
                warnings.append(f"Weight/displacement variance: {error_pct:.1f}%")
        
        # 2. VCG reasonableness (should be 40-70% of depth typically)
        if weight:
            depth = state_manager.get('hull.dimensions.depth')
            vcg_ratio = weight.displacement_vcg_m / depth if depth else 0
            
            if not (0.3 < vcg_ratio < 0.8):
                warnings.append(f"VCG ratio {vcg_ratio:.2f} outside typical range (0.4-0.7)")
        
        # 3. Free surface check
        if weight and weight.free_surface_correction_m > 0.3:
            warnings.append(f"High free surface correction: {weight.free_surface_correction_m:.2f}m - check tank fill levels")
        
        # 4. SWBS completeness
        if weight and weight.groups:
            covered_groups = {g.swbs_code for g in weight.groups}
            required_groups = {'100', '200', '500', '600'}  # Minimum for lightship
            missing = required_groups - covered_groups
            
            if missing:
                warnings.append(f"Missing SWBS groups: {missing}")
        
        return ValidatorResult(
            validator_id='weight/estimation',
            status='passed' if not errors else 'failed',
            severity='error' if errors else 'warning' if warnings else 'passed',
            errors=errors,
            warnings=warnings
        )
```

## 5.5.7 Test Requirements

```python
# tests/weight/test_swbs_integration.py

class TestSWBSWeightEstimation:
    """SWBS weight estimation tests."""
    
    def test_lightship_within_bounds(self):
        """Lightship should be within expected range for dimensions."""
        estimates = estimate_swbs_groups(
            loa_m=30.0, beam_m=8.0, depth_m=4.0, draft_m=2.5, cb=0.45
        )
        
        lightship, lcg, vcg = compute_lightship_from_swbs(estimates, lwl_m=28.0, depth_m=4.0)
        
        # 30m workboat should be roughly 50-150 tonnes
        assert 50_000 < lightship < 150_000, f"Lightship {lightship/1000:.1f}t outside expected range"
    
    def test_vcg_reasonable(self):
        """VCG should be below mid-depth."""
        estimates = estimate_swbs_groups(
            loa_m=30.0, beam_m=8.0, depth_m=4.0, draft_m=2.5, cb=0.45
        )
        
        _, _, vcg = compute_lightship_from_swbs(estimates, lwl_m=28.0, depth_m=4.0)
        
        assert vcg < 2.5, f"VCG {vcg:.2f}m seems too high for 4m depth"


class TestTankCalculator:
    """Tank capacity calculation tests."""
    
    def test_empty_tank_zero_weight(self):
        """Empty tank should contribute zero weight."""
        calc = TankCalculator([
            TankDefinition(
                tank_id="fuel_1",
                tank_type="fuel",
                capacity_m3=10.0,
                length_m=3.0,
                breadth_m=2.0,
                height_m=1.5,
                lcg_empty_m=5.0,
                vcg_empty_m=0.75,
                tcg_empty_m=0.0,
                sounding_table=[]
            )
        ])
        
        state = calc.compute_tank_state("fuel_1", fill_percent=0.0, contents_density_kg_m3=850)
        assert state['weight_kg'] == 0.0
    
    def test_full_tank_correct_weight(self):
        """Full tank should have weight = capacity × density."""
        calc = TankCalculator([
            TankDefinition(
                tank_id="fuel_1",
                tank_type="fuel",
                capacity_m3=10.0,
                length_m=3.0,
                breadth_m=2.0,
                height_m=1.5,
                lcg_empty_m=5.0,
                vcg_empty_m=0.75,
                tcg_empty_m=0.0,
                sounding_table=[]
            )
        ])
        
        state = calc.compute_tank_state("fuel_1", fill_percent=100.0, contents_density_kg_m3=850)
        assert abs(state['weight_kg'] - 8500.0) < 1.0  # 10m³ × 850 kg/m³
    
    def test_free_surface_only_partial_fill(self):
        """Free surface moment should only apply for partial fills."""
        calc = TankCalculator([...])
        
        state_full = calc.compute_tank_state("fuel_1", fill_percent=100.0, contents_density_kg_m3=850)
        state_partial = calc.compute_tank_state("fuel_1", fill_percent=50.0, contents_density_kg_m3=850)
        
        assert state_full['free_surface_moment_m4'] == 0.0
        assert state_partial['free_surface_moment_m4'] > 0.0


class TestMaterialWeightEstimation:
    """Material-aware weight estimation tests."""
    
    def test_steel_is_baseline(self):
        """Steel should return steel_equivalent == actual_weight."""
        from magnet.weight.material_estimator import (
            estimate_hull_weight_by_material,
            compute_lightship_from_material_estimates,
            MaterialType
        )
        
        estimates = estimate_hull_weight_by_material(
            loa_m=30.0, beam_m=8.0, depth_m=4.0, draft_m=2.5, cb=0.45,
            material=MaterialType.STEEL
        )
        
        # For steel, actual should equal steel_equivalent (within weld allowance)
        for est in estimates:
            if est.group_code == "100":  # Hull structure
                ratio = est.actual_weight_kg / est.steel_equivalent_kg
                assert 1.0 <= ratio <= 1.05, f"Steel hull ratio {ratio:.2f} should be ~1.03"
    
    def test_aluminum_lighter_than_steel(self):
        """Aluminum hull should be 45-55% of steel equivalent."""
        from magnet.weight.material_estimator import (
            estimate_hull_weight_by_material,
            compute_lightship_from_material_estimates,
            MaterialType
        )
        
        estimates = estimate_hull_weight_by_material(
            loa_m=25.0, beam_m=6.5, depth_m=3.2, draft_m=1.8, cb=0.42,
            material=MaterialType.ALUMINUM_5083,
            vessel_type="patrol"
        )
        
        lightship, _, _, comparison = compute_lightship_from_material_estimates(
            estimates, lwl_m=23.0, depth_m=3.2
        )
        
        # Weight should be less than steel
        assert lightship < comparison['steel_equivalent_kg']
        
        # Difference should be 40-55% savings
        savings_pct = abs(comparison['weight_difference_percent'])
        assert 35 < savings_pct < 60, f"Weight difference {savings_pct:.1f}% outside expected range"
    
    def test_material_affects_vcg(self):
        """Non-steel materials should have higher VCG than steel."""
        from magnet.weight.material_estimator import (
            estimate_hull_weight_by_material,
            compute_lightship_from_material_estimates,
            MaterialType
        )
        
        depth = 3.2
        
        # Steel estimate
        steel_estimates = estimate_hull_weight_by_material(
            loa_m=25.0, beam_m=6.5, depth_m=depth, draft_m=1.8, cb=0.42,
            material=MaterialType.STEEL
        )
        _, _, steel_vcg, _ = compute_lightship_from_material_estimates(
            steel_estimates, lwl_m=23.0, depth_m=depth
        )
        
        # Aluminum estimate
        al_estimates = estimate_hull_weight_by_material(
            loa_m=25.0, beam_m=6.5, depth_m=depth, draft_m=1.8, cb=0.42,
            material=MaterialType.ALUMINUM_5083
        )
        _, _, al_vcg, _ = compute_lightship_from_material_estimates(
            al_estimates, lwl_m=23.0, depth_m=depth
        )
        
        # Aluminum VCG should be higher
        assert al_vcg > steel_vcg, f"Aluminum VCG {al_vcg:.2f}m should be > steel {steel_vcg:.2f}m"
    
    def test_30m_workboat_weight_ranges(self):
        """30m workboat should be in expected weight range by material."""
        from magnet.weight.material_estimator import (
            estimate_hull_weight_by_material,
            compute_lightship_from_material_estimates,
            MaterialType
        )
        
        params = dict(loa_m=30.0, beam_m=8.0, depth_m=4.0, draft_m=2.2, cb=0.45,
                      vessel_type="workboat", has_superstructure=True)
        
        # Steel: expect 80-150 tonnes
        steel_est = estimate_hull_weight_by_material(**params, material=MaterialType.STEEL)
        steel_ls, _, _, _ = compute_lightship_from_material_estimates(steel_est, 28.0, 4.0)
        assert 80_000 < steel_ls < 150_000, f"Steel lightship {steel_ls/1000:.0f}t outside 80-150t"
        
        # Aluminum: expect 40-80 tonnes
        al_est = estimate_hull_weight_by_material(**params, material=MaterialType.ALUMINUM_5083)
        al_ls, _, _, _ = compute_lightship_from_material_estimates(al_est, 28.0, 4.0)
        assert 40_000 < al_ls < 80_000, f"Aluminum lightship {al_ls/1000:.0f}t outside 40-80t"
    
    def test_material_properties_available(self):
        """All supported materials should have properties defined."""
        from magnet.core.enums import MaterialType
from magnet.weight.material_estimator import estimate_hull_weight_by_material
        
        # Initial release materials
        required_materials = [
            MaterialType.STEEL,
            MaterialType.ALUMINUM_5083,
            MaterialType.ALUMINUM_6061,
            MaterialType.ALUMINUM_5086,
        ]
        
        for mat in required_materials:
            assert mat in MATERIAL_PROPERTIES, f"Missing properties for {mat}"
            props = MATERIAL_PROPERTIES[mat]
            assert props.density_kg_m3 > 0
            assert 0 < props.hull_weight_factor <= 1.0
            assert 0 <= props.vcg_correction_factor < 0.2
    
    def test_weld_addition_varies_by_material(self):
        """Weld addition should be higher for aluminum than steel."""
        from magnet.weight.material_estimator import (
            estimate_hull_weight_by_material,
            MaterialType
        )
        
        steel_est = estimate_hull_weight_by_material(
            loa_m=25.0, beam_m=6.5, depth_m=3.2, draft_m=1.8, cb=0.42,
            material=MaterialType.STEEL
        )
        al_est = estimate_hull_weight_by_material(
            loa_m=25.0, beam_m=6.5, depth_m=3.2, draft_m=1.8, cb=0.42,
            material=MaterialType.ALUMINUM_5083
        )
        
        # Get hull structure (group 100)
        steel_hull = next(e for e in steel_est if e.group_code == "100")
        al_hull = next(e for e in al_est if e.group_code == "100")
        
        # Weld ratio (weld_addition / actual_weight) should be higher for aluminum
        steel_weld_ratio = steel_hull.weld_addition_kg / steel_hull.actual_weight_kg
        al_weld_ratio = al_hull.weld_addition_kg / al_hull.actual_weight_kg
        
        assert al_weld_ratio > steel_weld_ratio, "Aluminum weld ratio should exceed steel"
    
    def test_state_integration(self):
        """Weight estimator should read material from state correctly."""
        from magnet.core.state_manager import StateManager
        from magnet.core.design_state import DesignState
        
        state = DesignState()
        manager = StateManager(state)
        
        # Set material in state
        manager.set('structural_design.hull_material', 'aluminum_5083')
        
        # Verify it reads back
        assert manager.get('structural_design.hull_material') == 'aluminum_5083'
        
        # Default should be steel
        state2 = DesignState()
        manager2 = StateManager(state2)
        assert manager2.get('structural_design.hull_material', 'steel') == 'steel'


class TestCrossLibraryIntegration:
    """
    Integration tests for the trimesh → weight → physics pipeline.
    
    These tests verify the full data flow across library boundaries,
    which was identified as a gap in the initial audit.
    """
    
    def test_mesh_to_weight_to_hydrostatics_pipeline(self):
        """Full pipeline: GLB mesh → weight estimation → hydrostatic validation."""
        import trimesh
        from magnet.webgl.mesh_utils import trimesh_to_magnet
        from magnet.core.enums import MaterialType
from magnet.weight.material_estimator import estimate_hull_weight_by_material
        from magnet.physics.geometry_hydrostatics import compute_hydrostatics_from_geometry
        
        # Step 1: Load mesh via trimesh
        # (In real test, load from test fixtures)
        mesh = trimesh.creation.box(extents=[30, 8, 4])  # Simplified hull-like box
        assert mesh.is_watertight, "Test mesh must be watertight"
        
        # Step 2: Convert to MAGNET format
        magnet_mesh = trimesh_to_magnet(mesh)
        assert magnet_mesh.volume_m3 > 0, "Volume must be positive"
        
        # Step 3: Estimate weight (using approximate dimensions from mesh)
        loa = magnet_mesh.bounds[1, 0] - magnet_mesh.bounds[0, 0]
        beam = magnet_mesh.bounds[1, 1] - magnet_mesh.bounds[0, 1]
        depth = magnet_mesh.bounds[1, 2] - magnet_mesh.bounds[0, 2]
        
        estimates = estimate_hull_weight_by_material(
            loa_m=loa, beam_m=beam, depth_m=depth, draft_m=depth * 0.5,
            cb=0.7,  # High for box
            material=MaterialType.STEEL
        )
        
        total_weight = sum(e.actual_weight_kg for e in estimates)
        assert total_weight > 0, "Weight must be positive"
        
        # Step 4: Verify weight is reasonable for hydrostatics
        # (Displacement should be achievable with this geometry)
        max_displacement = magnet_mesh.volume_m3 * 1025  # Seawater density
        assert total_weight < max_displacement, "Weight must be less than max displacement"
    
    def test_graceful_degradation_chain(self):
        """Verify fallback chain works when optional libraries are missing."""
        import sys
        import importlib
        
        # Mock missing optional library
        original_modules = sys.modules.copy()
        
        try:
            # Pretend manifold3d is not installed
            sys.modules['manifold3d'] = None
            
            # Weight estimation should still work (doesn't need manifold3d)
            from magnet.core.enums import MaterialType
from magnet.weight.material_estimator import estimate_hull_weight_by_material
            
            estimates = estimate_hull_weight_by_material(
                loa_m=25.0, beam_m=6.5, depth_m=3.2, draft_m=1.8, cb=0.45,
                material=MaterialType.ALUMINUM_5083
            )
            
            assert len(estimates) > 0, "Estimation should succeed without manifold3d"
            
        finally:
            # Restore original modules
            sys.modules.update(original_modules)
    
    def test_physics_parity_golden_file(self):
        """
        Golden file test: Verify physics outputs match known-good reference.
        
        This addresses the G6 gate (Physics accuracy maintained) audit gap.
        """
        import json
        from pathlib import Path
        
        # Load golden reference (MUST exist for production-grade testing)
        golden_path = Path("tests/fixtures/golden/30m_workboat_physics.json")
        
        if not golden_path.exists():
            # FAIL if golden file missing - this is a release blocker
            pytest.fail(
                f"Golden file {golden_path} not found. "
                "Generate with: python scripts/generate_golden_files.py\n"
                "Missing golden files are a RELEASE BLOCKER - do not ship without baselines."
            )
        
        with open(golden_path) as f:
            golden = json.load(f)
        
        # Compute current values
        from magnet.core.enums import MaterialType
from magnet.weight.material_estimator import estimate_hull_weight_by_material
        from magnet.weight.material_estimator import compute_lightship_from_material_estimates
        
        estimates = estimate_hull_weight_by_material(
            loa_m=30.0, beam_m=8.0, depth_m=4.0, draft_m=2.2, cb=0.45,
            material=MaterialType.STEEL, vessel_type="workboat"
        )
        
        lightship, lcg, vcg, _ = compute_lightship_from_material_estimates(
            estimates, lwl_m=28.0, depth_m=4.0
        )
        
        # Compare with golden values (within tolerance)
        assert abs(lightship - golden['lightship_kg']) / golden['lightship_kg'] < 0.05, \
            f"Lightship {lightship} differs from golden {golden['lightship_kg']} by >5%"
        assert abs(lcg - golden['lcg_m']) < 0.5, \
            f"LCG {lcg} differs from golden {golden['lcg_m']} by >0.5m"
        assert abs(vcg - golden['vcg_m']) < 0.3, \
            f"VCG {vcg} differs from golden {golden['vcg_m']} by >0.3m"
```

## 5.5.7 DesignState Schema Updates (REQUIRED)

> ⚠️ **MISSING FROM ORIGINAL PLAN:** The new dataclasses must be integrated into DesignState.

**UPDATE `magnet/core/dataclasses.py`:**

```python
# Add to existing imports
from typing import Dict, List, Optional
from dataclasses import dataclass, field

# ADD these new dataclasses:

@dataclass
class WeightGroup:
    """Single SWBS weight group contribution."""
    group_code: str                 # "100", "200", etc.
    group_name: str
    weight_kg: float
    lcg_m: float
    vcg_m: float
    tcg_m: float = 0.0
    estimation_method: str = "parametric"
    confidence: float = 0.75

@dataclass  
class TankState:
    """Current state of a single tank."""
    tank_id: str
    fill_percent: float             # 0-100
    contents_type: str              # "fuel", "freshwater", "ballast"
    contents_density_kg_m3: float
    volume_m3: float
    weight_kg: float
    lcg_m: float
    vcg_m: float
    tcg_m: float
    free_surface_moment_m4: float

@dataclass
class WeightSummary:
    """Complete weight summary for physics coupling."""
    lightship_kg: float
    lightship_lcg_m: float
    lightship_vcg_m: float
    
    deadweight_kg: float            # Sum of all variable weights
    deadweight_lcg_m: float
    deadweight_vcg_m: float
    
    displacement_kg: float          # lightship + deadweight
    displacement_lcg_m: float
    displacement_vcg_m: float
    
    groups: List[WeightGroup] = field(default_factory=list)
    tanks: List[TankState] = field(default_factory=list)
    
    total_free_surface_moment_m4: float = 0.0
    estimation_method: str = "swbs_parametric"
    confidence: str = "medium"      # "low", "medium", "high"
```

**UPDATE `magnet/core/design_state.py`:**

```python
# In DesignState class, update the weight section:

@dataclass
class DesignState:
    # ... existing sections ...
    
    # Section 6: Weight (UPDATED)
    weight: WeightSummary = field(default_factory=lambda: WeightSummary(
        lightship_kg=0.0,
        lightship_lcg_m=0.0,
        lightship_vcg_m=0.0,
        deadweight_kg=0.0,
        deadweight_lcg_m=0.0,
        deadweight_vcg_m=0.0,
        displacement_kg=0.0,
        displacement_lcg_m=0.0,
        displacement_vcg_m=0.0,
    ))
    
    # ... rest of sections ...
```

**UPDATE `magnet/core/dataclasses.py` HullState:**

```python
@dataclass
class HullState:
    # ... existing fields ...
    loa: float = 0.0
    lwl: float = 0.0
    beam: float = 0.0
    # ... etc ...
    
    # NEW: Construction material (affects weight estimation)
    material: str = "steel"  # MaterialType enum value: "steel", "aluminum_5083", etc.
```

**Migration Path for Existing Designs:**

```python
def migrate_design_state(old_state: dict) -> DesignState:
    """Migrate pre-Phase-2.5 designs to new schema."""
    new_state = DesignState.from_dict(old_state)
    
    # Add defaults for new fields if missing
    if not hasattr(new_state, 'weight') or new_state.weight is None:
        new_state.weight = WeightSummary(
            lightship_kg=old_state.get('weight', {}).get('lightship_tonnes', 0) * 1000,
            # ... map old fields to new structure
        )
    
    # ⚠️ AUDIT FIX: Correct path is structural_design.hull_material, not hull.material
    if not hasattr(new_state.structural_design, 'hull_material') or new_state.structural_design.hull_material is None:
        new_state.structural_design.hull_material = "steel"  # Default for legacy designs
    
    return new_state
```

> ⚠️ **AUDIT FIX: Migration Invocation Point**
> 
> The `migrate_design_state()` function must be invoked during design loading. Add to `magnet/core/state_manager.py` or `magnet/deployment/design_store.py`:
> 
> ```python
> # In state_manager.py or design_store.py
> 
> def load_design(filepath: str) -> DesignState:
>     """Load design with automatic schema migration."""
>     with open(filepath) as f:
>         raw_state = json.load(f)
>     
>     # Check schema version and migrate if needed
>     schema_version = raw_state.get('_schema_version', '1.0')
>     if version.parse(schema_version) < version.parse('2.5'):
>         return migrate_design_state(raw_state)
>     
>     return DesignState.from_dict(raw_state)
> ```

> ⚠️ **AUDIT FIX: groups.py Ownership**
> 
> The plan introduces `swbs_adapter.py` but the existing `magnet/weight/groups.py` already exists. Clarification:
> - `groups.py`: Contains existing weight group definitions - **KEEP, do not delete**
> - `swbs_adapter.py`: NEW module that imports from `groups.py` and adds MIL-STD-1399 mapping
> - Relationship: `swbs_adapter.py` extends/wraps `groups.py`, not replaces it

## 6.5.8 Requirements Updates

```txt
# requirements.txt additions for Phase 2.5: Weight Estimation

scipy>=1.10.0                   # For tank interpolation (interp1d)
scikit-learn>=1.0.0             # REQUIRED: Fallback for BoTorch/manifold3d graceful degradation

# Note: Phase 2.5 modules are NEW IMPLEMENTATIONS, not external library integrations.
# No additional external packages required beyond scipy for interpolation.
```

> ⚠️ **CRITICAL:** Do NOT remove `scikit-learn` from requirements. The graceful degradation paths for BoTorch and manifold3d depend on sklearn's PCA and GaussianProcessRegressor. Without sklearn, fallback code will crash.

---

# 7. Phase 3: Advanced Physics (Enhancement)

**Priority:** P1 — Physics accuracy improvements  
**Libraries:** Capytaine, hydroblast  
**Goal:** Optional high-fidelity BEM physics for validation

> **Note:** geomdl/STEP export has been moved to Phase 2 as a P0 product requirement.

## 7.1 Capytaine Integration (Optional)

### 6.2.1 Assessment Summary

| Criterion | Value |
|-----------|-------|
| **Actionability** | Medium — complex physics integration |
| **Applicability** | Excellent — BEM solver for hydrodynamics |
| **Impact** | Very High — 100x accuracy improvement over empirical |
| **Risk** | High — GPL-3.0 license, commercial implications |
| **North Star** | ✅ Physics validation only, no design intent |

### 6.2.2 Licensing Mitigation

*Source: GPT5.2 Section 6, OPUS Section 8.2*

**GPL Isolation Strategy:**

1. **Service Isolation**: Run Capytaine as a separate microservice
2. **Optional Plugin**: Never import in core MAGNET modules
3. **Validation Only**: Use only for physics validation, never design suggestion
4. **Legal Review**: Required before commercial deployment

```python
# magnet/physics/bem/__init__.py

"""
BEM physics backend (optional, GPL-isolated).

This module is OPTIONAL and requires explicit opt-in.
Do not import in core MAGNET modules to maintain license separation.
"""

import os

if not os.environ.get('MAGNET_ENABLE_CAPYTAINE'):
    raise ImportError(
        "Capytaine BEM backend requires explicit opt-in. "
        "Set MAGNET_ENABLE_CAPYTAINE=1 to enable. "
        "Note: Capytaine is GPL-3.0 licensed."
    )

from .solver import BEMSolver
from .adapter import capytaine_resistance

__all__ = ['BEMSolver', 'capytaine_resistance']
```

---

# 7. Phase 4: Advanced Unlocks (Future)

**Timeline:** Post-commercial launch  
**Priority:** P2 — Strategic capabilities  
**Libraries:** FreeCAD Ship, xeokit-sdk, GenCAD

## 7.1 Summary Table

| Library | Capability | Effort | North Star Considerations |
|---------|------------|--------|---------------------------|
| **FreeCAD Ship** | Bidirectional CAD workflow | 4-6 weeks | ✅ CAD interop utility |
| **xeokit-sdk** | Enterprise visualization | 4-6 weeks | ✅ Downstream of state |
| **GenCAD** | Image-to-CAD generation | 6-8 weeks | ⚠️ Requires LLM firewall |

## 7.2 GenCAD Firewall Requirements

*Source: GROK Section 3C*

> ⚠️ **DEFINITION:** "GenCAD" refers to a hypothetical future capability for image-to-CAD generation using multimodal LLMs (e.g., uploading a sketch or reference image to generate hull geometry). This is NOT a specific external library — it's a placeholder for any AI-based geometry generation that bypasses standard user input. The firewall pattern applies to ANY such capability regardless of implementation.

> "GenCAD could violate 'agents propose, kernel judges'"

**Required Safeguards:**

1. Route ALL GenCAD outputs through agent layer
2. NEVER allow direct geometry injection into kernel
3. Validate all generated geometry through standard pipeline
4. Log all GenCAD proposals for audit

```python
# magnet/agents/gencad_firewall.py

"""
Firewall for GenCAD integration.

Ensures GenCAD outputs are treated as PROPOSALS,
never as direct kernel mutations.
"""

from magnet.agents.geometry_proposer import GeometryProposer
from magnet.kernel.action_validator import ActionPlanValidator


class GenCADFirewall:
    """
    Routes GenCAD outputs through standard proposal validation.
    
    North Star: Agents propose, kernel judges.
    GenCAD is an agent capability, not a kernel bypass.
    """
    
    def __init__(self, proposer: GeometryProposer, validator: ActionPlanValidator):
        self.proposer = proposer
        self.validator = validator
    
    def process_gencad_output(self, gencad_result: dict) -> dict:
        """
        Convert GenCAD output to validated geometry proposal.
        
        1. Extract geometry from GenCAD
        2. Convert to MAGNET proposal format
        3. Validate through standard action validator
        4. Return validated proposal (or rejection)
        """
        # Convert GenCAD CAD commands to MAGNET DSL
        proposal = self._convert_to_proposal(gencad_result)
        
        # Validate through standard firewall
        validation = self.validator.validate(proposal)
        
        if not validation.is_valid:
            return {
                'status': 'rejected',
                'reason': validation.errors,
                'original': gencad_result
            }
        
        return {
            'status': 'accepted',
            'proposal': proposal,
            'validation': validation.to_dict()
        }
```

---

# 8. Cleanup Analysis & Migration

## 8.1 Code to DELETE

*Sources: GPT5.2 Appendix A, OPUS Section 7*

| File | Lines | Reason | Replacement |
|------|-------|--------|-------------|
| `magnet/webgl/geometry_service.py` | 475-507 (~40 lines) | Manual volume calculation | trimesh adapter |
| `magnet/bootstrap/manifold_blending.py` | 102-145 (~50 lines) | sklearn PCA projection | manifold3d projection |
| `magnet/bootstrap/manifold_blending.py` | 24, 61-63 (~5 lines) | sklearn PCA import/init | manifold3d import |
| `magnet/optimization/surrogate_model.py` | 30-82 (~60 lines) | sklearn GP | BoTorch GP |

**Total Lines Deleted:** ~155 lines

## 8.2 Code to ADD

| File | Lines | Purpose |
|------|-------|---------|
| `magnet/webgl/mesh_utils.py` | ~150 lines | trimesh adapter |
| `magnet/optimization/pareto.py` | ~300 lines | pymoo Pareto optimizer |
| `magnet/optimization/objectives.py` | ~150 lines | Objective functions |
| `magnet/optimization/views.py` | ~100 lines | Engineer/CFO views |
| `tests/invariants/test_property_based.py` | ~200 lines | hypothesis tests |
| `tests/webgl/test_mesh_utils.py` | ~100 lines | trimesh adapter tests |

**Total Lines Added:** ~1,000 lines

## 8.3 Code to PRESERVE (Core Invariants)

| File | Lines | Reason |
|------|-------|--------|
| `magnet/webgl/geometry_service.py` | 458-474 | Volume parity business logic (uses adapter) |
| `magnet/bootstrap/manifold_blending.py` | 1-100 | API contract, weight normalization |
| `magnet/physics/validators.py` | 2400+ lines | All physics validation logic |
| `magnet/kernel/synthesis.py` | 2200+ lines | Core synthesis engine |
| `magnet/hull_gen/generator.py` | All | Hull generation logic |
| `magnet/core/design_state.py` | All | Canonical state (NEVER touch) |

## 8.4 Net Impact Summary

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Lines of Code | ~50,000 | ~50,850 | +850 |
| Manual Implementations | 4 | 0 | -4 |
| Test Coverage (invariants) | ~3,249 | ~3,450 | +201 |
| External Dependencies | ~25 | ~31 | +6 |

---

# 9. Risk Register

## 9.1 Technical Risks

*Sources: GPT5.2 Section 6, OPUS Section 8.1*

| Risk | Severity | Probability | Mitigation | Owner |
|------|----------|-------------|------------|-------|
| **GPL contamination (Capytaine)** | High | Medium | Service isolation, legal review, defer to Phase 3+ | Legal + Arch |
| **C++ build friction (manifold3d)** | Medium | Medium | Optional dep, prebuilt wheels, Docker fallback | DevOps |
| **PyTorch version conflicts (BoTorch)** | Medium | Low | Pin versions, CI matrix, optional backend | DevOps |
| **manifold3d O(n³) performance** | Medium | Medium | Mesh decimation via trimesh, caching | Eng |
| **State leakage via optimizers** | High | Low | Enforce clone/snapshot, fail-fast assertions | Eng |
| **Embedding methods not invertible (UMAP)** | Medium | High | Use for viz/retrieval only, not decode | Arch |
| **CAD round-trip fidelity (geomdl)** | Medium | Medium | Import as artifact → reparametrize → canonicalize | Eng |

## 9.2 License Risks

| Library | License | Risk | Mitigation |
|---------|---------|------|------------|
| **Capytaine** | GPL-3.0 | ⚠️ High | Optional plugin, service isolation, legal review |
| **CGAL** | GPL/Commercial | ⚠️ High | Defer; evaluate commercial license |
| All others | MIT/Apache/BSD | ✅ None | Standard usage |

## 9.3 Performance Regression Risks

*Source: OPUS Section 8.3*

| Operation | Current | After Integration | Acceptable? | Mitigation |
|-----------|---------|-------------------|-------------|------------|
| Volume calculation | 5ms | 8ms (trimesh) | ✅ Yes | — |
| Hull blending | 50ms | 200ms (manifold3d) | ⚠️ Monitor | Decimation |
| GP prediction | 10ms | 15ms (BoTorch) | ✅ Yes | — |
| Pareto optimization | N/A | 30-60s (pymoo) | ✅ Yes | Async |
| BEM solve | N/A | 30-60s (Capytaine) | ✅ Yes | Batch/async |

---

# 10. Strategic Positioning

## 10.1 Competitive Advantage

*Sources: Analysis doc, GROK Section "Strategic Positioning"*

| Factor | Competitors | MAGNET + Libraries |
|--------|-------------|-------------------|
| **Primary Focus** | New hull generation | Retrofit optimization |
| **Physics** | Black box / Siemens CFD | Traceable empirical + optional BEM |
| **Pricing** | Enterprise subscriptions | Per-use, web-native |
| **CAD Interop** | Vendor lock-in | Open (STEP/IGES via pythonocc, NURBS via geomdl) |
| **Trade-offs** | Single "optimal" | Pareto fronts (pymoo) |

## 10.2 Why Retrofit Focus Wins

> "The existing fleet is huge; 'make this hull 5-10% better' + 'show me the trade-offs' sells faster than 'generate brand new hulls.'"  
> — GPT5.2 Section 7.2

**Market Reality:**
- ~50,000 commercial vessels in global fleet
- Retrofit decisions happen 10x more often than newbuilds
- Regulators (IMO CII, EEDI) forcing efficiency improvements
- Shipyards need "before/after" validation, not blank-canvas design

## 10.3 Product Positioning

**Before:** "AI suggests hull tweaks"  
**After:** "Upload hull file → instant baseline analysis → physics-validated design exploration with STEP export"

> **Export Capability:** STEP/IGES via geomdl + pythonocc (Phase 2). GLB/STL via trimesh for web visualization.

---

# 11. Integration Test Scenarios

These scenarios serve as **end-to-end acceptance tests** for the product. Each scenario must pass before the system is considered complete.

## 11.1 Scenario: Full Pipeline Test

**Purpose:** Verify geometry → physics → optimization → export chain works correctly.

**Preconditions:**
- [ ] Phase 0 complete (E0.4 equilibrium solver fixed)
- [ ] Phase 1 complete (trimesh, manifold3d, hypothesis)
- [ ] Phase 2 complete (pymoo, BoTorch, geomdl/STEP export)
- [ ] Phase 2.5 complete (weight convergence loop)
- [ ] Test hull loaded (Viking patrol boat or similar)

**Test Steps:**

### Step 1: Import & Validate Geometry

```python
def test_import_and_validate():
    """Import hull geometry and verify integrity."""
    hull = load_hull("test_fixtures/viking_patrol.glb")
    
    assert hull.is_watertight, "Hull must be watertight"
    assert hull.volume_m3 > 0, "Volume must be positive"
    assert abs(hull.physics_displacement_parity - 1.0) < 0.02, "Displacement parity within 2%"
```

**Expected Output:**
- Volume: 245.3 m³ ✓
- Watertight: Yes ✓
- Physics displacement parity: 98.7% ✓

### Step 2: Weight Estimation with Convergence

```python
def test_weight_convergence():
    """Verify weight ↔ hydrostatics converges."""
    hull = load_hull("test_fixtures/viking_patrol.glb")
    
    weight_summary, hydro = converge_weight_hydrostatics(
        state=hull.state,
        initial_draft_m=1.8,
        tolerance_m=0.01
    )
    
    assert weight_summary.displacement_kg > 0
    assert hydro.gm_m > 0.5, "GM must be positive for stability"
    # Convergence should happen within 5 iterations
```

### Step 3: Multi-Objective Optimization

```python
def test_pareto_optimization():
    """Generate Pareto front for competing objectives."""
    hull = load_hull("test_fixtures/viking_patrol.glb")
    
    result = run_pareto_optimization(
        state=hull.state,
        objectives=["minimize_resistance", "maximize_gm"],
        population_size=50,
        generations=30
    )
    
    assert len(result.pareto_front) >= 5, "Should find multiple Pareto-optimal points"
    assert all(p.is_physics_valid for p in result.pareto_front)
```

### Step 4: CAD Export

```python
def test_step_export():
    """Export to STEP and verify roundtrip."""
    hull = load_hull("test_fixtures/viking_patrol.glb")
    
    export_step(hull.surfaces, "output/test_export.step")
    
    # Verify file exists and is valid STEP
    assert Path("output/test_export.step").exists()
    assert Path("output/test_export.step").stat().st_size > 1000  # Non-trivial size
    
    # Roundtrip test: should open in FreeCAD without errors
    # (Manual verification or automated with FreeCAD Python bindings)
```

## 11.2 Scenario: Stepped Hull Convergence

**Purpose:** Verify E0.4 fix works on difficult geometry.

```python
def test_stepped_hull_equilibrium():
    """Stepped hull must converge without oscillation."""
    from magnet.physics.equilibrium import solve_equilibrium_draft
    
    hull = load_hull("test_fixtures/stepped_planing_hull.glb")
    
    # This was the failing case before E0.4 fix
    # ⚠️ AUDIT FIX: Actual function is solve_equilibrium_draft, not find_equilibrium_draft
    draft = solve_equilibrium_draft(
        hull_definition=hull.hull_definition,
        target_displacement_kg=15000,
        initial_draft_m=1.5
    )
    
    assert 0.5 < draft < 3.0, "Draft in valid range"
    # Should NOT oscillate - convergence within 10 iterations
```

## 11.3 Scenario: Material Selection Impact

**Purpose:** Verify material selection affects physics correctly.

```python
def test_material_affects_weight():
    """Aluminum hull should be lighter than steel."""
    hull = load_hull("test_fixtures/30m_workboat.glb")
    
    steel_weight = estimate_lightship(hull, material="steel")
    aluminum_weight = estimate_lightship(hull, material="aluminum_5083")
    
    assert aluminum_weight < steel_weight * 0.6, "Aluminum should be <60% of steel"
    assert aluminum_weight > steel_weight * 0.4, "Aluminum should be >40% of steel"
```

## 11.4 Success Criteria

| Scenario | Pass Criteria |
|----------|---------------|
| Full Pipeline | All steps complete without error |
| Stepped Hull | Equilibrium converges in ≤10 iterations |
| Material Selection | Weight ratios match published data (±10%) |
| STEP Export | Roundtrip with FreeCAD succeeds |
| Pareto Front | ≥5 valid Pareto-optimal designs found |

**The product ships when ALL scenarios pass.**

---

# 12. Appendix: Dependencies & DevOps

## 12.1 Requirements Updates

```txt
# requirements.txt additions

# ⚠️ AUDIT FIX: sklearn is currently imported by manifold_blending.py but NOT in requirements.txt
scikit-learn>=1.0.0             # Required for manifold_blending.py PCA, also BoTorch/manifold3d fallbacks

# Phase 1: Immediate stability
trimesh>=4.0.0
manifold3d>=2.0.0
hypothesis>=6.0.0

# Phase 2: Optimization
pymoo>=0.6.0
botorch>=0.9.0
gpytorch>=1.10.0
torch>=2.0.0

# Phase 2: CAD Export (P0 requirement)
geomdl>=5.3.0                   # NURBS manipulation
# pythonocc-core>=7.7.0         # STEP/IGES export - CONDA ONLY, cannot pip install

# Phase 3: Advanced Physics (optional)
# capytaine>=2.0.0  # GPL - uncomment only if isolated

# Phase 4: Advanced (as needed)
# xeokit-sdk via npm
# freecad via conda
```

> ⚠️ **AUDIT NOTE:** pythonocc-core cannot be installed via pip. For STEP/IGES export capability, use conda:
> ```bash
> conda install -c conda-forge pythonocc-core
> ```

## 12.2 Docker Updates

```dockerfile
# deployment/Dockerfile additions

# Phase 1: C++ build tools for manifold3d
RUN apt-get update && apt-get install -y \
    cmake \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Phase 2: CAD Export (pythonocc requires conda - use miniconda base image for STEP/IGES support)
# If STEP export is required, use continuumio/miniconda3 as base and:
# RUN conda install -c conda-forge pythonocc-core

# Phase 3: Optional Capytaine dependencies (commented by default)
# RUN apt-get update && apt-get install -y \
#     liblapack-dev \
#     libblas-dev \
#     && rm -rf /var/lib/apt/lists/*
```

## 12.3 CI/CD Updates

```yaml
# .github/workflows/ci.yml

name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']
        include:
          - python-version: '3.10'
            install-optional: true
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Install optional dependencies
        if: matrix.install-optional
        run: |
          pip install botorch gpytorch torch
      
      - name: Run tests
        run: pytest tests/ -v --cov=magnet --cov-report=xml
      
      # ⚠️ AUDIT NOTE: Scripts below must be created before CI will pass
      # - name: Run integration gates
      #   run: ./scripts/run_integration_gates.sh  # TO BE CREATED
      
      # - name: Test graceful degradation
      #   run: |
      #     MAGNET_DISABLE_TRIMESH=1 pytest tests/webgl/test_mesh_utils.py -v  # TO BE CREATED
      #     MAGNET_DISABLE_BOTORCH=1 pytest tests/optimization/test_surrogate.py -v

  # hypothesis:  # TO BE CREATED: tests/invariants/test_property_based.py
  #   runs-on: ubuntu-latest
  #   steps:
  #     - uses: actions/checkout@v4
  #     - name: Run property-based tests
  #       run: pytest tests/invariants/test_property_based.py -v
```

> ⚠️ **AUDIT NOTE: Scripts/Tests TO BE CREATED:**
> - `scripts/run_integration_gates.sh` - referenced but does not exist
> - `tests/invariants/test_property_based.py` - referenced but does not exist  
> - `tests/webgl/test_mesh_utils.py` - referenced but does not exist
> - `scripts/generate_golden_files.py` - referenced but does not exist

> ⚠️ **AUDIT NOTE: sklearn Dependency:**
> The codebase's `magnet/bootstrap/manifold_blending.py` imports `sklearn.decomposition.PCA` but sklearn is NOT in requirements.txt. Add to requirements.txt:
> ```
> scikit-learn>=1.0.0  # Required for manifold_blending.py
> ```

## 12.4 Feature Flags

```python
# magnet/core/feature_flags.py

"""
Feature flags for library integrations.

Enables graceful degradation and staged rollout.
"""

import os

# Phase 1
TRIMESH_ENABLED = os.environ.get('MAGNET_DISABLE_TRIMESH') != '1'
MANIFOLD3D_ENABLED = os.environ.get('MAGNET_DISABLE_MANIFOLD3D') != '1'

# Phase 2
BOTORCH_ENABLED = os.environ.get('MAGNET_DISABLE_BOTORCH') != '1'
PYMOO_ENABLED = os.environ.get('MAGNET_DISABLE_PYMOO') != '1'
GEOMDL_ENABLED = os.environ.get('MAGNET_DISABLE_GEOMDL') != '1'  # P0 for CAD export
PYTHONOCC_ENABLED = os.environ.get('MAGNET_DISABLE_PYTHONOCC') != '1'  # STEP/IGES

# Phase 3 (opt-in due to GPL)
CAPYTAINE_ENABLED = os.environ.get('MAGNET_ENABLE_CAPYTAINE') == '1'
```

---

# Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-25 | Synthesis | Initial unified plan from GPT5.2 + OPUS + GROK + Analysis |
| 1.1.0 | 2026-01-25 | Synthesis | Added Phase 2.5 Weight Estimation Foundation (SWBS, TankCalc, IncliningSim) |
| 1.2.0 | 2026-01-25 | Synthesis | Added aluminum weight support |
| 1.3.0 | 2026-01-25 | Synthesis | Refactored to material-general architecture: `structural_design.hull_material` state parameter |
| 1.4.0 | 2026-01-25 | Audit | External audit fixes (hallucinated repos, sklearn, manifold3d API, etc.) |
| **2.0.0** | **2026-01-25** | **Product** | **PRODUCT-FIRST REFACTOR — No demo shortcuts** |
| | | | 🔴 E0.4 Equilibrium Solver → P0 BLOCKER |
| | | | 🔴 Weight ↔ Hydrostatics Convergence → P0 REQUIRED |
| | | | 🔴 geomdl + pythonocc CAD Export → P0 Phase 2 |
| **2.1.0** | **2026-01-25** | **Audit** | **AUDIT RECONCILIATION — Codebase alignment:** |
| | | | ✅ Test count: 3249 → 4500+ (actual pytest collection is 4524) |
| | | | ✅ E0.4: Already fixed in solve_equilibrium_draft(), do not re-implement |
| | | | ✅ hull.material → structural_design.hull_material (correct existing path) |
| | | | ✅ Removed HullMaterial enum → use existing MaterialType |
| | | | ✅ convex_hull fallback → rejection (destructive to hull geometry) |
| | | | ✅ DesignState.clone() → copy.deepcopy() (actual API) |
| | | | ✅ Conductor.validate() → Conductor.run_phase()/run_to_phase() (actual API) |
| | | | ✅ geomdl in appendix → Phase 2 (consistency with P0 designation) |
| | | | ✅ pythonocc CI → conda-based workflow (cannot pip install) |
| | | | ✅ Scripts marked "TO BE CREATED" (don't claim existence of unwritten code) |
| | | | ⚠️ Identified missing sklearn in requirements (manifold_blending.py currently imports sklearn) |
| | | | ✅ Added migrate_design_state invocation point |
| | | | ✅ Clarified groups.py vs swbs_adapter.py relationship |

---

# Quick Reference Card

## Material Selection

Material is a **user-selectable design parameter** stored at `structural_design.hull_material`. Weight estimation automatically dispatches to material-specific formulas.

| Material Value | Description | Hull Weight Factor |
|----------------|-------------|-------------------|
| `steel` | Default, baseline | 1.00 |
| `aluminum` | Aluminum construction (representative marine alloy) | ~0.45–0.55 |
| `composite` | Composite construction (high variability) | project-specific |

## Phase Summary

| Phase | Priority | Deliverable | Libraries/Modules |
|-------|----------|-------------|-------------------|
| **0** | 🔴 Blocker | Equilibrium solver fix | `magnet/physics/equilibrium.py` |
| **1** | P0 | Geometry stability | trimesh, manifold3d, hypothesis |
| **2** | P0 | Optimization + CAD export | pymoo, BoTorch, geomdl, pythonocc |
| **2.5** | P0 | Weight estimation | swbs_adapter, tank_calculator, material_estimator |
| **3** | P1 | Advanced physics | Capytaine, hydroblast |
| **4** | P2 | Future enhancements | FreeCAD Ship, xeokit-sdk |

> **Ship when:** All Phase 0-2.5 integration tests pass.

## Critical Path: Weight → Physics

```
Material Selection (structural_design.hull_material)
    │
    ▼
Weight Estimation (material-corrected SWBS)
    │
    ├──► Displacement → Draft → Resistance → Speed
    ├──► VCG (material-corrected) → GM (Stability)
    └──► LCG → Trim
```

## Material Usage Example

```python
# Set material in state
state_manager.set('structural_design.hull_material', 'aluminum')

# Weight estimator automatically uses correct formulas
from magnet.weight.material_estimator import (
    estimate_hull_weight_by_material,
    MaterialType
)

# Explicit material parameter
estimates = estimate_hull_weight_by_material(
    loa_m=30.0, beam_m=8.0, depth_m=4.0, draft_m=2.2, cb=0.45,
    material=MaterialType.ALUMINUM  # Or read from state
)
```

## Key Commands

```bash
# Run all tests
pytest tests/ -v

# Run integration gates
./scripts/run_integration_gates.sh

# Test graceful degradation
MAGNET_DISABLE_TRIMESH=1 pytest tests/webgl/ -v

# Run property-based tests
pytest tests/invariants/test_property_based.py -v

# Run weight/material tests
pytest tests/weight/ -v

# Install Phase 1
pip install trimesh manifold3d hypothesis

# Install Phase 2 + 2.5
pip install pymoo botorch gpytorch torch scipy
```

## Phase 2.5 Implementation Sources

> ⚠️ **NOTE:** Phase 2.5 modules are **new implementations**, NOT integrations of external libraries. The code implements standard naval architecture formulas from published sources.

| Module | Type | Formula Sources | Priority |
|--------|------|-----------------|----------|
| `material_estimator.py` | New code | Watson & Gilfillan (1976), Schneekluth (1998) | **P0** |
| `swbs_adapter.py` | New code | MIL-STD-1399, NAVSEA SWBS Manual | **P0** |
| `tank_calculator.py` | New code | Standard sounding table interpolation | **P0** |
| `inclining_sim.py` | New code | ASTM F1321, IMO inclining test procedures | P1 |

**Published References:**
- Watson, D.G.M. & Gilfillan, A.W. (1976). "Some Ship Design Methods." *RINA Transactions*
- Schneekluth, H. & Bertram, V. (1998). *Ship Design for Efficiency and Economy*. Butterworth-Heinemann
- MIL-STD-1399 Section 301: Ship Work Breakdown Structure
- ASTM F1321: Standard Guide for Conducting a Stability Test

## North Star Checklist (Before Any PR)

- [ ] G1: No design intent in kernel
- [ ] G2: Changes observable via state lenses
- [ ] G3: No new design-type enums
- [ ] G4: Transactions remain atomic
- [ ] G5: All 3249+ tests pass
- [ ] G6: Physics accuracy maintained
- [ ] G7: Graceful degradation works
- [ ] G8: No library objects in DesignState

---

*This document is the authoritative unified plan for MAGNET library integration. All implementations must pass North Star alignment gates before merge.*
