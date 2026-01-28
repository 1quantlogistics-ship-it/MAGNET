# MAGNET System State Analysis & Implementation Guide

<!-- AGENT_CONTEXT
Purpose: [TODO: Add purpose description]
Authoritative: No
Keywords: [magnet, system, state, analysis]
Depends_On: None
Used_By: [TODO: Add users]
Status: current
Last_Verified: 2026-01-15
-->


**Document Purpose**: Complete guide to the MAGNET generative geometry system — state analysis, implementation paths, best practices, and the iterative design spiral.  
**Last Updated**: January 2026  
**Status**: Living document — the source of truth

---

## Table of Contents

1. [First Principles](#part-i-first-principles)
2. [What Is Solid](#part-ii-what-is-solid)
3. [What Is Fragile](#part-iii-what-is-fragile)
4. [Pipeline Blockers](#part-iv-pipeline-blockers-detailed)
5. [What We Learned](#part-v-what-we-learned)
6. [Where We Stand](#part-vi-where-we-stand)
7. [The Path Forward](#part-vii-the-path-forward)
8. [The Iterative Design Spiral](#part-viii-the-iterative-design-spiral)
9. [Implementation Guide](#part-ix-implementation-guide)
10. [Best Practices](#part-x-best-practices)
11. [Anti-Patterns](#part-xi-anti-patterns-what-not-to-do)
12. [The Fundamental Truth](#part-xii-the-fundamental-truth)
13. [Module Compatibility Audit](#part-xiii-module-compatibility-audit)
14. [Change Propagation](#part-xiv-change-propagation)
15. [Appendices](#appendices)

---

## Part I: First Principles

### What System Are We Actually Building?

We are building **a way to turn imagination into reality under laws**.

More precisely:
- **Agents imagine** — they propose shapes, structures, relationships, constraints
- **The system does not trust imagination** — it subjects every proposal to physics, geometry, and consistency
- **Reality does not design** — it only says yes, no, or *this breaks here*
- **Iteration happens through feedback, not presets**

That's the irreducible core.

### The North Star Goal

> **Enable combinatorial explosion (trillions+ of forms)** because a fixed, small grammar operating on continuous geometry primitives (sections, surfaces, attachments, constraints) composes endlessly without enumerating designs—but it only truly unlocks novelty if the language can express arbitrary geometry constructions (e.g., section lofts, NURBS control nets, multi-body composition) and the kernel validates outcomes rather than predefining forms.

**The Qualifier**: Novelty comes from continuous parameters + compositional operators, not from styles or presets. As long as the language stays declarative and the kernel enforces physics/geometry constraints post-compilation, you'll get genuinely new forms—otherwise it collapses back into variants.

**The Goal**: Fully cross the line from enumerated design systems to a true generative geometry language: agents propose pure geometric constructions, the kernel compiles those constructions into the existing canonical geometry pipeline, and validation happens strictly after geometry exists—so novelty is unbounded while physical truth is preserved.

---

### The Mission Statement

> The kernel exposes universal geometric and physical operations.  
> Agents compose them into designs the kernel has never seen.  
> The kernel's only role is to validate reality, not recognize intent.

| We Build | We Do NOT Build |
|----------|-----------------|
| A geometric/physical execution engine | AI CAD with better presets |
| Compositional primitives (surfaces, sections, bodies, constraints) | Enumerated design types ("catamaran", "stepped hull", "patrol boat") |
| Agents that invent novel geometry | Agents that select from a catalog |
| A kernel that validates physics | A kernel that recognizes design intent |
| Trillions of possible forms | Variants of predefined families |

### The Contract

**Agents propose.** They speak in geometric primitives—surfaces, sections, discontinuities, bodies, constraints. They can invent combinations no engineer has ever drawn.

**The kernel judges.** It compiles geometry, runs physics, checks constraints, and returns structured feedback. It never suggests designs. It never contains style knowledge. It only answers: *can this exist?*

**Novel designs work without new code.** If a design requires a new resource type to express, the system has failed.

### The Equation

```
NOVELTY = continuous parameters × compositional operators × physics validation
```

### The Tests

1. Create a "stepped ventilated planing hull" using only discontinuities, flow paths, and openings. No "stepped hull" type.
2. Create a "catamaran" using only bodies, sections, and surfaces. No "catamaran" type.
3. Create a hull configuration no naval architect has ever drawn—and validate it without adding code.

**If any test fails, we've collapsed back into enumeration.**

---

## Part II: What Is Solid

What is solid is anything that answers **"what is allowed to exist?"** rather than "what should exist?"

### Locked Down: Irreversible Wins

#### 1. A Canonical Notion of Reality
- There is exactly one geometry model (`HullGeometry`)
- There is exactly one physics pipeline
- There is exactly one validation firewall

#### 2. A Language That Can Describe Arbitrary Constructions
- **Continuous parameters**, not categories
- **Compositional operators**, not selections
- **Multi-body geometry**, not named vessel types

#### 3. Determinism
- Same proposal + same state → same result
- This is what makes trust, debugging, and engineering possible

**These are load-bearing because they define truth, not behavior.**

### The Grammar: 7 Primitives for Infinite Forms

| Primitive | Purpose | Freeform Fields | Continuous Parameters |
|-----------|---------|-----------------|----------------------|
| `geometry.body` | Distinct solid volume | `body_type`, `physics_category` | `offset_x_m`, `offset_y_m`, `offset_z_m` |
| `geometry.section` | Cross-section profile | Supports polygon + NURBS | `station` (0-1), `points[]`, `control_points[]` |
| `geometry.surface` | Lofted/NURBS surface | `surface_type` | `u_degree`, `v_degree`, knot vectors |
| `geometry.discontinuity` | Steps, chines, rails | `discontinuity_type`, `profile` | `station_start`, `station_end`, `height_ratio`, `depth_m`, `angle_deg` |
| `geometry.attachment` | Body-to-body connection | `attachment_type` | `offset_x_m`, `offset_y_m`, `offset_z_m` |
| `geometry.flow_path` | Ventilation/cooling | `medium` | `inlet_point[]`, `outlet_point[]`, `cross_section_m2` |
| `geometry.opening` | Vents, hatches, intakes | `shape`, `purpose` | `position[]`, `dimensions[]` |

**All type fields are freeform strings.** The kernel validates physics, not names.

### Why 7 Primitives Enable Trillions of Forms

```
Forms = body_configs × section_shapes × surface_types × discontinuities × attachments × flow_paths × openings

Where:
- body_configs: ∞ (any offset, any body_type string)
- section_shapes: ∞ (continuous point coordinates, NURBS control points)
- surface_types: ∞ (any string + continuous degree/knot params)
- discontinuities: ∞ (continuous station, height, depth, angle)
- attachments: ∞ (any body pair, any type string, continuous offsets)
- flow_paths: ∞ (continuous inlet/outlet positions)
- openings: ∞ (continuous position/size)

Result: ∞ × ∞ × ∞ × ∞ × ∞ × ∞ × ∞ = unbounded novelty
```

### Mission Test Results (Verified)

```
✅ Test 1 - Stepped Planing Hull:
   7 statements → 7 actions, 0 errors
   Body types: {'stepped_planing'}
   Physics categories: {'surface_piercing'}
   NO "stepped hull" type used

✅ Test 2 - Multi-Body Vessel:
   9 statements → 9 actions, 0 errors
   Body types: {'demihull'}
   Method: parallel_axis_theorem
   NO "catamaran" type used

✅ Test 3 - Novel Asymmetric Trimaran:
   10 statements → 10 actions, 0 errors
   Body types: {'wave_piercing_main', 'hydrofoil_strut', 'stabilizing_outrigger'}
   Physics categories: {'submerged', 'partially_submerged', 'surface_piercing'}
   
   Geometry compiled: ✅
   Sections: 9
   Bodies: 3
   Volume: 226.969 m³
   Hydrostatics method: parallel_axis_theorem
   NO new code added
```

**VERDICT: Language can express novel forms without adding types.** ✅

---

## Part III: What Is Fragile

What is fragile is anything that answers **"how does this get executed?"** rather than "what is true?"

### Current Fragilities

#### 1. The New System Is Not The Authority

Two paths exist:
```
OLD PATH (legacy):   HullFamily.PATROL → synthesis.py → HullGeometry
                     ↑ 86 references, enumerated, limits novelty

NEW PATH (implemented): geometry.* primitives → compiler.py → HullGeometry
                        ↑ 0 references to HullFamily, unlimited novelty
```

The old one still runs silently. **The system can lie to you without you noticing.**

#### 2. Feedback Is Incomplete

Reality is computed, but not always explained:

| Calculation | Single Hull | Multi-Body | Status |
|-------------|-------------|------------|--------|
| Displacement | ✅ Works | ✅ Works | OK |
| GM | ⚠️ Returns None | ⚠️ Returns None | **Missing wrapper** |
| Resistance | ❌ Import error | ❌ Import error | **Wrong function name** |
| Constraints | ⚠️ None = fail | ⚠️ None = fail | Needs values |

Without explanation, humans and agents can't learn. Without learning, iteration stalls.

#### 3. Downstream Physics Assumes Familiarity

Some solvers assume conventional shapes:
- Holtrop-Mennen calibrated on BSRA Series 60 models (conventional monohulls)
- Form coefficients (Cp, Cwp) assume known prismatic forms
- Novel geometry breaks hidden assumptions

**This is not a bug — it's a known boundary we must expose.**

---

## Part IV: Pipeline Blockers (Detailed)

### 🔴 Blocker #1: `design_program` Cannot Be Set in State

**Evidence:**
```python
state.set('design_program', 'test program', 'test_source')
# Returns: False (silently fails)
# state.get('design_program') → None
```

**Root Cause:** `StateManager` uses a fixed schema. The path `design_program` isn't in the schema.

**Impact:** Conductor integration at `conductor.py:163-179` will **never trigger** the new path because `state.get("design_program")` always returns `None`.

**Fix:** Store in `metadata.design_program` (flexible dict) or add `design_program` to schema.

**Implementation:**
```python
# Option A: Use metadata (no schema change)
state._state.metadata["design_program"] = program_text

# Option B: Direct attribute on DesignState (requires schema change)
# Add to design_state.py: design_program: Optional[str] = None
```

---

### 🔴 Blocker #2: Missing `compute_gm_from_geometry` Function

**Evidence:**
```python
from magnet.stability.intact_gm import compute_gm_from_geometry
# ImportError: cannot import name 'compute_gm_from_geometry'
```

**Available:** `IntactGMCalculator` class with `calculate(kb, bm, kg, fsc)` method

**Fix:** Create wrapper in `magnet/stability/intact_gm.py`:

```python
def compute_gm_from_geometry(
    geometry: 'HullGeometry',
    draft: float,
    vcg: float,
) -> Dict[str, Any]:
    """
    Compute GM from HullGeometry.
    
    Wrapper that extracts KB, BM from geometry and calls IntactGMCalculator.
    """
    # Extract geometric properties
    if hasattr(geometry, 'vcb'):
        kb = abs(geometry.vcb)  # KB = distance from keel to center of buoyancy
    else:
        kb = draft * 0.53  # Approximation: KB ≈ 0.53 * T for standard forms
    
    # BM = I / V (waterplane inertia / displaced volume)
    # For now, use geometric approximation
    if hasattr(geometry, 'volume') and geometry.volume > 0:
        beam = _estimate_beam_from_geometry(geometry)
        # BM ≈ B² / (12 * T) for wall-sided approximation
        bm = (beam ** 2) / (12 * draft) if draft > 0 else 0
    else:
        bm = 0
    
    # Calculate GM
    calculator = IntactGMCalculator()
    result = calculator.calculate(
        kb_m=kb,
        bm_m=bm,
        kg_m=vcg,
        free_surface_correction_m=0.0,
    )
    
    return {
        "gm_m": result.gm_m,
        "kb_m": kb,
        "bm_m": bm,
        "kg_m": vcg,
        "passes": result.gm_m >= GM_MIN if result.gm_m else False,
    }
```

---

### 🔴 Blocker #3: Missing `estimate_resistance` Function

**Evidence:**
```python
from magnet.physics.resistance import estimate_resistance
# ImportError: cannot import name 'estimate_resistance'
```

**Available:** `calculate_resistance()` function

**Fix:** In `program_executor.py`, change:
```python
# FROM:
from magnet.physics.resistance import estimate_resistance

# TO:
from magnet.physics.resistance import calculate_resistance as estimate_resistance
```

Or create alias in `resistance.py`:
```python
# Add at end of resistance.py:
estimate_resistance = calculate_resistance  # Alias for backwards compatibility
```

---

### 🔴 Blocker #4: Negative Volume Calculation

**Evidence:**
```
Volume: -140.312 m³
```

**Root Cause:** Section points winding order. Area calculation assumes counter-clockwise, test points create clockwise.

**Fix:** Normalize winding order in `section_compiler.py`:

```python
def _normalize_winding_order(points: List[List[float]]) -> List[List[float]]:
    """
    Ensure counter-clockwise winding order for section points.
    
    Uses shoelace formula to detect winding direction.
    """
    if len(points) < 3:
        return points
    
    # Calculate signed area using shoelace formula
    signed_area = 0.0
    n = len(points)
    for i in range(n):
        j = (i + 1) % n
        signed_area += points[i][0] * points[j][1]
        signed_area -= points[j][0] * points[i][1]
    signed_area /= 2.0
    
    # If negative (clockwise), reverse the points
    if signed_area < 0:
        return list(reversed(points))
    return points
```

---

### 🔴 Blocker #5: API Endpoints Bypass Conductor Integration

**Current Flow:**
```
POST /api/v1/program → execute_program() → returns result
                       ↑ DIRECT (bypasses conductor)
```

**Expected Flow:**
```
POST /api/v1/design-language → store in state → conductor.run_phase("hull")
                                                → _run_program_generation()
                                                → execute_program()
                                                → explain records ✅
```

**Fix:** Create conductor-integrated endpoint in `api.py`:

```python
@app.post("/api/v1/design-language", tags=["Design Language"])
async def design_language_endpoint(
    request: ProgramRequest,
    state_manager=Depends(get_state_manager),
):
    """
    Execute design program through conductor (authoritative path).
    
    This is the ONLY path that should be used for production.
    Ensures explain records, phase orchestration, and state management.
    """
    from magnet.kernel.conductor import Conductor
    
    # Store program in state
    if hasattr(state_manager._state, 'metadata'):
        state_manager._state.metadata["design_program"] = request.program_text
    
    # Create conductor and run hull phase
    conductor = Conductor(state_manager)
    conductor.create_session(state_manager.get("design_id") or "new_design")
    
    result = conductor.run_phase("hull")
    
    return {
        "success": result.status.value == "completed",
        "phase_result": result.to_dict(),
        "explain_records": conductor.get_status_summary(),
    }
```

---

## Part V: What We Learned

Three deep insights that most teams never articulate:

### 1. Enumeration Is Entropy

- If you name things ("catamaran", "step", "style"), the system freezes
- Enumeration feels helpful but kills novelty
- **The universe does not work in enums**

Evidence: `HullFamily` enum has 86 references. The new path has zero. Only one path enables trillions of forms.

**The Trap:**
```python
# ❌ WRONG: Enumeration trap
class HullType(Enum):
    CATAMARAN = "catamaran"
    TRIMARAN = "trimaran"
    STEPPED = "stepped"
    # ... every new design needs a new enum value

# ✅ RIGHT: Continuous composition
CREATE geometry.body port { body_type: "any_string_I_want", offset_y: -3.0 }
CREATE geometry.body stbd { body_type: "any_string_I_want", offset_y: 3.0 }
# This IS a catamaran, but without naming it
```

### 2. Language Beats Configuration

- Configuration edits known things
- Language creates unknown things
- **We crossed that boundary**

Evidence: The 7 geometry primitives with continuous parameters can express forms that don't exist in any naval architecture textbook.

**The Difference:**
```python
# Configuration: "Which preset do you want?"
hull_type: "fast_patrol"
beam_modifier: 1.1

# Language: "What shape do you want?"
CREATE geometry.section bow { station: 0.0, points: [[0,0], [1.2,-0.3], [1.2,-1.8], [0,-2.1]] }
CREATE geometry.discontinuity spray_rail { station_start: 0.1, station_end: 0.6, height_ratio: 0.7, depth_m: 0.04 }
```

### 3. Actors Matter After The Stage

- We built the stage first (correct)
- Actors (agents) only make sense once reality pushes back
- Otherwise they just hallucinate

Evidence: `GeometryProposer` exists but is useless without validation feedback. The kernel must judge before agents can learn.

**The Order:**
```
1. Stage (kernel + validation) — DONE ✅
2. Feedback loop (quantified physics) — IN PROGRESS ⚠️
3. Actors (agents that iterate) — WAITING
```

---

## Part VI: Where We Stand

We are standing at the boundary between:
- **A compiler that can create realities**
- **A system that people can actually use**

We've already solved the rare problem:

> "How do we let imagination run without breaking truth?"

What remains is the ordinary but necessary problem:

> "How do we make this the only path things flow through?"

### Current Architecture State

| Component | Status | North Star Alignment |
|-----------|--------|---------------------|
| Parser (`parser.py`) | ✅ Works | ✅ Accepts freeform strings |
| Expander (`expander.py`) | ✅ Works | ✅ No design knowledge |
| Compiler (`compiler.py`) | ⚠️ Volume sign bug | ✅ Compiles novel forms |
| Program Executor | ❌ Missing imports | ⚠️ Incomplete validation |
| Hydrostatics | ❌ Function not found | ⚠️ Partial |
| Resistance | ❌ Function not found | ⚠️ Partial |
| Conductor Integration | ❌ Can't set design_program | ❌ Not authoritative |
| API Endpoints | ⚠️ Bypass conductor | ❌ Two paths exist |
| Agent (`geometry_proposer.py`) | ⚠️ Needs API key | ✅ Outputs only geometry.* |

---

## Part VII: The Path Forward

### What We Don't Need

- More ideas
- More primitives
- More types
- More configuration options

### What We Need

**Authority.**

From first principles, the next step is:

> Ensure there is exactly one way a hull comes into existence, and it is the language-driven path that produces auditable reality.

That means:
- **One conductor path**
- **One explain path**
- **One geometry → physics → validation chain**
- **Zero silent fallbacks**

### Execution Plan

| Priority | Task | Hours | Category |
|----------|------|-------|----------|
| P0 | Create `compute_gm_from_geometry` wrapper | 1 | Validation |
| P0 | Fix `estimate_resistance` import | 0.5 | Validation |
| P0 | Fix section winding normalization | 1 | Compilation |
| P0 | Test full validation pipeline | 1 | Verification |
| P1 | Add `metadata.design_program` storage | 1 | Integration |
| P1 | Create conductor-integrated API endpoint | 2 | Authority |
| P1 | End-to-end test with novel forms | 2 | Verification |

**Total: ~8 hours of focused work**

### Success Criteria

After fixes, this must work:

```
Input: "Create an asymmetric trimaran with wave-piercing main hull 
        and retractable hydrofoils"

→ Parses to 10 geometry.* primitives  
→ Compiles to HullGeometry (3 bodies, 9 sections)  
→ Validates: GM=1.2m ✅, Resistance=52kN, Volume=227m³  
→ No new code added
→ Explain records generated
→ Conductor orchestrated
```

---

## Part VIII: The Iterative Design Spiral

### The Core Loop

The MAGNET system enables fast, accurate, infinitely iterable design through a tight feedback loop:

```
    ┌─────────────────────────────────────────────────┐
    │                                                 │
    │   USER INTENT                                   │
    │   "Make it faster" / "More stable" / "Lighter"  │
    │                                                 │
    └─────────────────────┬───────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────┐
    │                                                 │
    │   AGENT PROPOSES                                │
    │   geometry.* primitives with reasoning          │
    │                                                 │
    └─────────────────────┬───────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────┐
    │                                                 │
    │   KERNEL COMPILES                               │
    │   primitives → HullGeometry                     │
    │                                                 │
    └─────────────────────┬───────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────┐
    │                                                 │
    │   PHYSICS VALIDATES                             │
    │   GM=?, Resistance=?, Volume=?, Constraints=?   │
    │                                                 │
    └─────────────────────┬───────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────┐
    │                                                 │
    │   FEEDBACK TO USER/AGENT                        │
    │   "GM improved by 15%, but resistance +8%"      │
    │                                                 │
    └─────────────────────┬───────────────────────────┘
                          │
                          └──────────────┐
                                         │
                          ┌──────────────┘
                          │
                          ▼
                    [NEXT ITERATION]
```

### One Change Affects Others

The design spiral acknowledges that naval architecture is a coupled system:

| Change This | Affects These |
|-------------|---------------|
| Beam wider | Stability ↑, Resistance ↑, Weight ↑ |
| Draft deeper | Resistance ↓, Stability ?, Grounding risk ↑ |
| Add body | GM changes (parallel axis), Weight ↑, Complexity ↑ |
| Step in hull | Resistance ↓ (at speed), Wetted area ↓, Complexity ↑ |
| Finer bow | Resistance ↓, Volume ↓, Buoyancy distribution changes |

**The kernel computes ALL of these consequences.** The agent doesn't need to know the physics—it just needs to see the numbers change.

### Fast Iteration Requirements

For the spiral to work, each iteration must be:

| Requirement | Target | Why |
|-------------|--------|-----|
| **Parse time** | <10ms | Instant feedback |
| **Compile time** | <100ms | User doesn't wait |
| **Validation time** | <500ms | Can iterate rapidly |
| **Total cycle** | <1s | Flow state preserved |

### The Feedback Contract

Every validation result MUST include:

```python
{
    "metric": "gm_m",
    "value": 1.23,
    "required": 0.5,        # If constrained
    "passes": True,
    "delta_from_previous": +0.15,  # What changed
    "confidence": 0.95,     # How sure are we?
    "method": "parallel_axis_theorem",
    "recommendation": None,  # Or "Consider reducing VCG"
}
```

Without `delta_from_previous`, agents can't learn what their changes did.

### Breaking the Loop: What Stops Iteration

| Failure Mode | Symptom | Solution |
|--------------|---------|----------|
| No validation | GM=None | Fix wrapper functions (P0) |
| Slow compilation | >5s per cycle | Profile and optimize |
| Unclear feedback | "Failed" with no reason | Structured error messages |
| Coupled failures | Change A breaks B,C,D | Constraint prioritization |
| Local minima | Agent stuck | Multi-objective exploration |

---

## Part IX: Implementation Guide

### Step-by-Step: Making the Pipeline Work

#### Phase 1: Fix Validation (Day 1 Morning)

**1.1 Create `compute_gm_from_geometry`**

File: `magnet/stability/intact_gm.py`

```python
def compute_gm_from_geometry(
    geometry: 'HullGeometry',
    draft: float,
    vcg: float,
) -> Dict[str, Any]:
    """Compute GM from compiled HullGeometry."""
    
    # For multi-body, delegate to multi_body_hydrostatics
    if hasattr(geometry, 'bodies') and len(geometry.bodies) > 1:
        from magnet.physics.multi_body_hydrostatics import compute_multi_body_gm
        return compute_multi_body_gm(geometry.bodies, geometry, draft, vcg)
    
    # Single hull calculation
    kb = _compute_kb(geometry, draft)
    bm = _compute_bm(geometry, draft)
    
    calculator = IntactGMCalculator()
    result = calculator.calculate(kb_m=kb, bm_m=bm, kg_m=vcg)
    
    return {
        "gm_m": result.gm_m,
        "bm_m": bm,
        "kb_m": kb,
        "passes": result.gm_m >= GM_MIN,
    }


def _compute_kb(geometry: 'HullGeometry', draft: float) -> float:
    """Compute KB from geometry."""
    if hasattr(geometry, 'vcb') and geometry.vcb is not None:
        return abs(geometry.vcb)
    return draft * 0.53  # Standard approximation


def _compute_bm(geometry: 'HullGeometry', draft: float) -> float:
    """Compute BM from geometry using waterplane inertia."""
    if not hasattr(geometry, 'sections') or not geometry.sections:
        return 0.0
    
    # Compute waterplane inertia from sections at waterline
    I_wp = 0.0
    for section in geometry.sections:
        # Find half-beam at waterline
        y_max = 0.0
        for pt in section.points:
            if abs(pt.position.z) < 0.1:  # Near waterline
                y_max = max(y_max, abs(pt.position.y))
        I_wp += (2 * y_max) ** 3 / 12  # Rectangular approximation
    
    # BM = I / V
    volume = abs(geometry.volume) if geometry.volume else 1.0
    return I_wp / volume if volume > 0 else 0.0
```

**1.2 Fix resistance import**

File: `magnet/kernel/program_executor.py`, line ~390

```python
# Change from:
from magnet.physics.resistance import estimate_resistance

# To:
try:
    from magnet.physics.resistance import calculate_resistance
    
    def estimate_resistance(lwl, beam, draft, displacement, speed_kts):
        """Wrapper for backwards compatibility."""
        result = calculate_resistance(
            lwl=lwl,
            beam=beam,
            draft=draft,
            displacement_mt=displacement / 1000,  # Convert kg to tonnes
            wetted_surface=lwl * beam * 0.7,  # Approximation
            speed_kts=speed_kts,
        )
        return {"resistance_kn": result.total_resistance_kn, "method": "holtrop"}
except ImportError:
    def estimate_resistance(*args, **kwargs):
        return {"error": "Resistance module not available"}
```

**1.3 Fix winding order**

File: `magnet/kernel/stdlib/section_compiler.py`

Add after line ~90:

```python
def _normalize_winding_order(points: List[List[float]]) -> List[List[float]]:
    """Ensure counter-clockwise winding for positive area."""
    if len(points) < 3:
        return points
    
    # Shoelace formula for signed area
    signed_area = 0.0
    n = len(points)
    for i in range(n):
        j = (i + 1) % n
        y1, z1 = points[i][0], points[i][1]
        y2, z2 = points[j][0], points[j][1]
        signed_area += y1 * z2 - y2 * z1
    
    # Negative = clockwise, reverse to make CCW
    if signed_area < 0:
        return list(reversed(points))
    return points
```

Then in `compile_section()`, add:

```python
# Normalize winding order before creating points
points_raw = _normalize_winding_order(points_raw)
```

#### Phase 2: Test Validation (Day 1 Afternoon)

```bash
cd /Users/bengibson/MAGNETV1
python3 -c "
from magnet.kernel.program_executor import execute_program

program = '''
CREATE geometry.body main { body_type: \"test\", physics_category: \"surface_piercing\" }
CREATE geometry.section bow { station: 0.0, body_id: \"main\", points: [[0,0], [1,-0.5], [1,-1.5], [0,-2]] }
CREATE geometry.section mid { station: 0.5, body_id: \"main\", points: [[0,0], [2,-0.5], [2,-2], [0,-2.5]] }
CREATE geometry.section stern { station: 1.0, body_id: \"main\", points: [[0,0], [1.5,-0.4], [1.5,-1.2], [0,-1.5]] }
CONSTRAIN hull.gm >= 0.5
'''

result = execute_program(
    program_text=program,
    initial_state={'hull': {'loa': 25.0, 'draft': 1.5, 'vcg': 1.0}},
    validate=True,
)

print(f'Success: {result.success}')
print(f'Volume: {result.geometry.volume if result.geometry else \"N/A\"}')
print(f'GM: {result.validation.get(\"hydrostatics\", {}).get(\"gm_m\")}')
print(f'Resistance: {result.validation.get(\"resistance\")}')
"
```

**Expected output:**
```
Success: True
Volume: 140.31 (positive now!)
GM: 0.85
Resistance: {'resistance_kn': 12.5, 'method': 'holtrop'}
```

#### Phase 3: Integrate with Conductor (Day 2)

**3.1 Enable design_program storage**

File: `magnet/core/design_state.py`

Add to `DesignState` class:

```python
@dataclass
class DesignState:
    # ... existing fields ...
    
    # Design language program (new path)
    design_program: Optional[str] = None
```

Or use the metadata approach (no schema change):

File: `magnet/kernel/conductor.py`, update `_run_program_generation`:

```python
def _run_program_generation(self, design_program: str) -> Optional['ExecutionResult']:
    """Run hull generation via design language."""
    from magnet.kernel.program_executor import execute_program, ExecutionResult
    
    logger.info("[conductor] Using design language path")
    
    result = execute_program(
        program_text=design_program,
        state_manager=self.state,
        dry_run=False,
        validate=True,
    )
    
    # Record explain trace
    if result.success:
        self._record_program_explain(result)
    
    return result
```

**3.2 Create authoritative endpoint**

File: `magnet/deployment/api.py`

```python
class DesignLanguageRequest(BaseModel):
    """Request for design language endpoint."""
    program_text: str
    design_id: Optional[str] = None
    run_validation: bool = True


@app.post("/api/v1/design-language", tags=["Design Language"])
async def design_language_endpoint(
    request: DesignLanguageRequest,
    state_manager=Depends(get_state_manager),
):
    """
    Execute design program through conductor.
    
    This is the AUTHORITATIVE path. All production code should use this.
    """
    from magnet.kernel.conductor import Conductor
    
    # Store program in state (use metadata for flexibility)
    state_manager._state.metadata = state_manager._state.metadata or {}
    state_manager._state.metadata["design_program"] = request.program_text
    
    # Also set on state for conductor to find
    state_manager._design_program = request.program_text
    
    # Run through conductor
    conductor = Conductor(state_manager)
    design_id = request.design_id or state_manager.get("design_id") or str(uuid.uuid4())
    conductor.create_session(design_id)
    
    result = conductor.run_phase("hull")
    
    return {
        "success": result.status.value == "completed",
        "design_id": design_id,
        "phase_status": result.status.value,
        "errors": result.errors,
        "synthesis_audit": result.synthesis_audit,
        "explain": conductor.get_status_summary(),
    }
```

**3.3 Update conductor to check metadata**

File: `magnet/kernel/conductor.py`, line ~163

```python
# Check for design program
design_program = None

# Try multiple locations
if hasattr(self.state, '_design_program'):
    design_program = self.state._design_program
elif hasattr(self.state, '_state') and hasattr(self.state._state, 'metadata'):
    design_program = self.state._state.metadata.get("design_program")

if design_program:
    # NEW PATH
    generation_result = self._run_program_generation(design_program)
    # ...
```

---

## Part X: Best Practices

### For Kernel Development

#### DO ✅

```python
# Accept any string for type fields
body_type = properties.get("body_type", "hull")  # Freeform

# Derive physics from geometry
submergence = compute_submergence_from_geometry(body, waterline)

# Return structured feedback
return {
    "metric": "gm_m",
    "value": 1.23,
    "passes": True,
    "method": "parallel_axis_theorem",
}

# Validate after compilation
geometry = compile_to_geometry(state)
validation = run_validation(geometry)  # Physics checks geometry
```

#### DON'T ❌

```python
# Don't enumerate types
if body_type == "catamaran":  # ❌ Design knowledge in kernel
    ...

# Don't assume shape
if hull_type in KNOWN_HULL_TYPES:  # ❌ Enumeration trap
    ...

# Don't return bare pass/fail
return False  # ❌ No feedback for iteration

# Don't validate during parsing
if not is_valid_hull_type(type_str):  # ❌ Pre-compilation validation
    raise Error
```

### For Agent Development

#### DO ✅

```python
# Output only geometry.* primitives
operations = [
    {"op": "CREATE", "type": "geometry.body", "id": "main", ...},
    {"op": "CREATE", "type": "geometry.section", "id": "bow", ...},
]

# Include reasoning
{
    "reasoning": "Adding spray rail at 70% height to reduce wetted surface",
    "confidence": 0.8,
}

# React to physics feedback
if previous_gm < required_gm:
    # Propose wider beam or lower VCG
```

#### DON'T ❌

```python
# Don't use hull.* types
{"op": "CREATE", "type": "hull.catamaran", ...}  # ❌ Enumeration

# Don't skip reasoning
{"op": "CREATE", ...}  # ❌ No explanation

# Don't ignore feedback
# Agent keeps proposing same thing despite failing validation ❌
```

### For API Design

#### DO ✅

```python
# Route through conductor for authority
result = conductor.run_phase("hull")

# Return explain records
return {
    "result": result,
    "explain": conductor.get_status_summary(),
}

# Support dry_run for previews
execute_program(program, dry_run=True)
```

#### DON'T ❌

```python
# Don't bypass conductor
result = execute_program(program)  # ❌ No explain records

# Don't have multiple paths
if old_mode:
    use_hull_family()
else:
    use_design_language()  # ❌ Two paths = confusion
```

---

## Part XI: Anti-Patterns (What NOT To Do)

### Anti-Pattern 1: The Enumeration Trap

**Symptom:** Adding new enum values for new designs

```python
# ❌ WRONG
class HullType(Enum):
    CATAMARAN = "catamaran"
    TRIMARAN = "trimaran"
    STEPPED = "stepped"  # New! Now we need stepped hull support
    HYDROFOIL = "hydrofoil"  # New! Another enum value
    
    # This grows forever, each requiring new code
```

**Solution:** Use geometry composition

```python
# ✅ RIGHT
# A "stepped hull" is just:
CREATE geometry.discontinuity step { discontinuity_type: "transverse_step", ... }
CREATE geometry.flow_path vent { medium: "air", ... }

# A "hydrofoil" is just:
CREATE geometry.body foil { body_type: "lifting_surface", physics_category: "submerged" }
CREATE geometry.attachment strut { attachment_type: "foil_strut", ... }
```

### Anti-Pattern 2: Design Knowledge in Kernel

**Symptom:** Kernel code references design concepts

```python
# ❌ WRONG
def compute_resistance(geometry, state):
    if is_catamaran(geometry):  # Design knowledge!
        return catamaran_resistance(geometry)
    elif is_planing(geometry):  # Design knowledge!
        return planing_resistance(geometry)
```

**Solution:** Derive from physics

```python
# ✅ RIGHT
def compute_resistance(geometry, state):
    froude = compute_froude_number(geometry, speed)
    body_count = count_bodies(geometry)
    
    if froude > 0.5:
        return high_speed_resistance(geometry)  # Physics-based
    else:
        return displacement_resistance(geometry)  # Physics-based
```

### Anti-Pattern 3: Pre-Compilation Validation

**Symptom:** Rejecting programs before geometry exists

```python
# ❌ WRONG
def parse(program):
    for stmt in program:
        if stmt.body_type not in ALLOWED_BODY_TYPES:
            raise ValidationError("Unknown body type")  # Pre-compilation!
```

**Solution:** Validate physics after compilation

```python
# ✅ RIGHT
def execute_program(program):
    ast = parse(program)  # Accept anything
    actions = expand(ast)  # Accept anything
    geometry = compile(actions)  # Create geometry
    validation = validate_physics(geometry)  # NOW check physics
    return validation  # Return feedback, don't reject
```

### Anti-Pattern 4: Silent Fallbacks

**Symptom:** System uses old path without telling you

```python
# ❌ WRONG
def generate_hull(state):
    try:
        return new_path(state)
    except:
        return old_path(state)  # Silent fallback to enumeration!
```

**Solution:** Explicit failure

```python
# ✅ RIGHT
def generate_hull(state):
    if has_design_program(state):
        result = new_path(state)
        if not result.success:
            raise GeometryError(result.errors)  # Explicit failure
        return result
    else:
        raise ConfigurationError("No design program provided")
```

### Anti-Pattern 5: Opaque Feedback

**Symptom:** Validation returns pass/fail without explanation

```python
# ❌ WRONG
def validate(geometry):
    if gm < 0.5:
        return False  # Why? What is GM? What should agent do?
```

**Solution:** Structured feedback

```python
# ✅ RIGHT
def validate(geometry):
    return {
        "metric": "gm_m",
        "value": 0.35,
        "required": 0.5,
        "passes": False,
        "delta": -0.15,  # Changed from last iteration
        "recommendation": "Consider increasing beam or lowering VCG",
    }
```

---

## Part XII: The Fundamental Truth

We didn't build a demo.  
We didn't build a feature.

**We built a law-based creative system.**

The work left is not conceptual.  
It's about making reality singular and unavoidable.

### What We Have

- A grammar of 7 primitives that enables trillions of forms
- A compiler that turns imagination into geometry
- A physics engine that validates reality
- Tests proving novel forms work without new code

### What We Need

- One path (authority)
- Complete feedback (learning)
- Fast iteration (flow)

### The Measure of Success

```
1. Novel form described → ✅ 7 primitives compose anything
2. Geometry compiled → ✅ compiler produces HullGeometry
3. Physics validated → ⚠️ needs wrapper fixes
4. Feedback returned → ⚠️ needs structured responses
5. Iteration enabled → ⚠️ needs conductor integration
6. No new code needed → ✅ proven with 3 mission tests
```

When items 3-5 are ✅, we have crossed the line.

---

## Part XIII: Module Compatibility Audit

**Purpose**: Ensure ALL modules can plug into the design spiral (propose → compile → validate → feedback → iterate) without depending on HullFamily, hull_type, or design intent strings.

### Full Pipeline Map

#### Phase Execution Order (from `kernel/registry.py`)

| Order | Phase | Type | Depends On | Validators | State Namespace |
|-------|-------|------|------------|------------|-----------------|
| 1 | `mission` | DEFINITION | — | `mission/requirements` | `mission` |
| 2 | `hull` | ANALYSIS | `mission` | `hull/form`, `physics/hydrostatics` | `hull` |
| 3 | `structure` | ANALYSIS | `hull` | `structure/scantlings` | `structure` |
| 4 | `propulsion` | ANALYSIS | `hull` | `propulsion/sizing` | `propulsion` |
| 5 | `weight` | ANALYSIS | `hull`, `structure`, `propulsion` | `weight/estimation` | `weight` |
| 6 | `stability` | ANALYSIS | `weight` | `stability/intact_gm`, `stability/gz_curve` | `stability` |
| 7 | `loading` | INTEGRATION | `weight`, `stability` | `loading/computer` | `loading` |
| 8 | `arrangement` | INTEGRATION | `hull` | `arrangement/generator` | `arrangement` |
| 9 | `compliance` | VERIFICATION | `stability`, `loading` | `compliance/regulatory` | `compliance` |
| 10 | `production` | VERIFICATION | `structure`, `weight` | `production/planning` | `production` |
| 11 | `cost` | VERIFICATION | `production` | `cost/estimation` | `cost` |
| 12 | `optimization` | OUTPUT | `cost`, `compliance` | `optimization/design` | `optimization` |
| 13 | `reporting` | OUTPUT | `compliance`, `cost` | `reporting/generator` | `reports` |

#### Phase Dependency Graph

```
mission ─────┬─────────────────────────────────────────────────────┐
             │                                                     │
             ▼                                                     │
           hull ─────┬──────────────┬──────────────┐               │
             │       │              │              │               │
             │       ▼              ▼              ▼               │
             │   structure      propulsion    arrangement          │
             │       │              │                              │
             │       └──────┬──────┘                               │
             │              │                                      │
             │              ▼                                      │
             └────────► weight                                     │
                           │                                       │
                           ▼                                       │
                       stability                                   │
                           │                                       │
                           ▼                                       │
                       loading                                     │
                           │                                       │
                           ▼                                       │
                      compliance ◄─────────────────────────────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              production        cost
                    │             │
                    └──────┬──────┘
                           ▼
                     optimization
                           │
                           ▼
                      reporting
```

---

### Enumeration Violations by Module

#### Grep Results: `HullFamily|hull_type|hull_family|HullType`

**Found in 39 files.** Categorized by severity:

#### 🔴 CRITICAL: Decision-Making Based on Enumeration

| Module | File | Line | Violation | Decision Made |
|--------|------|------|-----------|---------------|
| **synthesis** | `kernel/synthesis.py` | 21 | `from .priors.hull_families import HullFamily` | Entire synthesis path |
| **synthesis** | `kernel/synthesis.py` | 398-413 | `LIGHTSHIP_K_TONNES: Dict[HullFamily, float]` | Weight estimation |
| **synthesis** | `kernel/synthesis.py` | 449-467 | `_infer_hull_type()` | Maps family → hull_type |
| **synthesis** | `kernel/synthesis.py` | 1154-1182 | Chine selection by family | Geometry generation |
| **physics/validators** | `physics/validators.py` | 476-495 | Type map to `HullType` enum | Hydrostatics method |
| **physics/validators** | `physics/validators.py` | 526-531 | `if hull_type_enum == HullType.CATAMARAN` | Body count |
| **physics/validators** | `physics/validators.py` | 707 | `is_catamaran = hull_form == "catamaran"` | Interference factor |
| **hull_gen/generator** | `hull_gen/generator.py` | 139 | `if definition.hull_type == HullType.CATAMARAN` | Section generation |
| **hull_gen/generator** | `hull_gen/generator.py` | 462-465 | Dispatch on `HullType` | Section shape |
| **structural/scantlings** | `structural/scantlings.py` | 394-396 | `if "displacement" in hull_type` | Slam pressure |
| **weight/estimators** | `weight/estimators/hull.py` | 125 | `HULL_TYPE_FACTORS.get(hull_type)` | Weight factor |

#### 🟡 MEDIUM: Reads hull_type but Can Derive from Geometry

| Module | File | Line | What It Reads | Can Derive From |
|--------|------|------|---------------|-----------------|
| **physics/hydrostatics** | `physics/hydrostatics.py` | 229 | `hull_type` for Cm estimation | Geometry (section shape) |
| **physics/hydrostatics** | `physics/hydrostatics.py` | 237 | `hull_type` for Cwp estimation | Waterplane shape |
| **physics/hydrostatics** | `physics/hydrostatics.py` | 250 | `hull_type` for KB estimation | Section centroids |
| **physics/hydrostatics** | `physics/hydrostatics.py` | 256 | `hull_type` for inertia coefficient | Section second moment |
| **physics/hydrostatics** | `physics/hydrostatics.py` | 268-269 | `hull_type` for LCB/LCF | Section integration |
| **physics/geometry_hydrostatics** | `physics/geometry_hydrostatics.py` | 102-106 | `hull_type == "catamaran"` | Section Y offset detection |
| **weight/validators** | `weight/validators.py` | 183-201 | `hull_type` for estimation | Can derive from geometry |

#### 🟢 LOW: Comments/Documentation Only

| Module | File | Line | Context |
|--------|------|------|---------|
| `kernel/stdlib/policies.py` | 69, 84 | Comments about avoiding hull_type | ✅ Correct guidance |
| `deployment/api.py` | 2403, 2463 | Comments about bypassing HullFamily | ✅ Correct guidance |
| `kernel/conductor.py` | 166, 181, 513, 524 | Comments about new/old path | ✅ Correct guidance |

#### 🟢 ACCEPTABLE: State Storage Only

| Module | File | Line | Context |
|--------|------|------|---------|
| `core/state_manager.py` | 156, 162 | `hull.hull_type` in refinable paths | Just path storage |
| `core/dataclasses.py` | various | `hull_type: Optional[str]` | Field definition |

---

### Geometry Interface Status

#### Per-Module Geometry Compatibility

| Module | Accepts HullGeometry | Works with Multi-Body | Notes |
|--------|---------------------|----------------------|-------|
| `hull_gen/generator.py` | ✅ Produces it | ⚠️ Dispatches on enum | Uses `HullType.CATAMARAN` |
| `physics/hydrostatics.py` | ❌ Uses parameters | ❌ Assumes single hull | Parametric only |
| `physics/geometry_hydrostatics.py` | ✅ Uses sections | ⚠️ Partial | Detects catamaran by Y offset |
| `physics/validators.py` | ✅ Can generate | ⚠️ Enum dispatch | Maps to `HullType` enum |
| `physics/multi_body_hydrostatics.py` | ✅ Full support | ✅ Yes | NEW PATH ✅ |
| `stability/intact_gm.py` | ❌ Uses KB/BM params | ❌ No | Needs wrapper |
| `weight/estimators/hull.py` | ❌ Uses params | ❌ No | Uses `hull_type` factor |
| `structural/scantlings.py` | ❌ Uses params | ❌ No | Uses `hull_type` for slam |

#### What "Multi-Body Compatible" Means

For a module to work with multi-body geometry from the design language path:

1. **Input**: Accept `HullGeometry` with `.bodies` attribute
2. **Processing**: Handle sections with different body_ids
3. **Output**: Return results aggregated across bodies OR per-body

**Currently multi-body compatible:**
- `physics/multi_body_hydrostatics.py` ✅
- `kernel/stdlib/compiler.py` ✅

**NOT multi-body compatible:**
- Everything else ❌

---

### State Key Dependencies

#### Phase → State Keys Read/Written

| Phase | Reads | Writes | Design Language Compatible? |
|-------|-------|--------|----------------------------|
| **mission** | User inputs | `mission.*` | ✅ Yes |
| **hull** | `mission.*` | `hull.lwl`, `hull.beam`, `hull.draft`, `hull.displacement_m3`, `hull.hull_type` | ⚠️ Partial — `hull_type` written |
| **structure** | `hull.*` | `structural_design.*` | ⚠️ Reads `hull.hull_type` |
| **propulsion** | `hull.*`, `mission.*` | `propulsion.*` | ⚠️ May read hull_type |
| **weight** | `hull.*`, `structural.*` | `weight.*` | ⚠️ Reads `hull.hull_type` |
| **stability** | `hull.*`, `weight.*` | `stability.*` | ✅ Uses geometry params |
| **loading** | `weight.*`, `stability.*` | `loading.*` | ✅ Yes |
| **compliance** | `stability.*`, `loading.*` | `compliance.*` | ✅ Yes |

#### State Keys When Hull Comes From Design Language

When using the design language path, these state keys ARE populated:

```python
# Populated by program_executor.py after compile_to_geometry():
"resources.*"           # ✅ All geometry.* primitives
"hull.loa"              # ✅ If SET in program
"hull.beam"             # ⚠️ May need to estimate from geometry
"hull.draft"            # ⚠️ May need to estimate from geometry
"hull.displacement_m3"  # ⚠️ From validation.hydrostatics
```

These state keys ARE NOT populated:

```python
"hull.hull_type"        # ❌ Not set — no enumeration!
"hull.cb"               # ❌ Must derive from geometry
"hull.cp"               # ❌ Must derive from geometry
"hull.cm"               # ❌ Must derive from geometry
"hull.cwp"              # ❌ Must derive from geometry
```

#### Downstream Impact

Modules that READ `hull.hull_type` will get `None` when hull comes from design language:

1. `physics/validators.py:113` → Will use default "monohull"
2. `physics/hydrostatics.py:196` → Will use default "monohull"
3. `weight/validators.py:183` → Will use default "monohull"
4. `structural/scantlings.py:394` → Will use default

**This is ACCEPTABLE for now** — defaults prevent crashes, but results may be suboptimal.

---

### Feedback Structure Compliance

#### Required Feedback Structure for Design Spiral

For agents to iterate effectively, each validation result must include:

```python
{
    "metric": str,           # What was measured
    "value": float,          # Current value
    "required": float,       # Threshold (if applicable)
    "passes": bool,          # Did it pass?
    "delta_from_previous": float,  # CRITICAL: Change from last iteration
    "method": str,           # How it was calculated
    "confidence": float,     # How reliable is this?
}
```

#### Current Feedback Structure: `ValidationFinding`

From `validators/taxonomy.py`:

```python
@dataclass
class ValidationFinding:
    finding_id: str
    severity: ResultSeverity  # ERROR, WARNING, PREFERENCE, INFO, PASSED
    message: str
    parameter_path: Optional[str]     # ✅ Maps to "metric"
    expected_value: Optional[Any]     # ✅ Maps to "required"
    actual_value: Optional[Any]       # ✅ Maps to "value"
    suggestion: Optional[str]
    reference: Optional[str]
    adjustment: Optional[Dict]        # ✅ Structured hint
```

#### Compliance by Module

| Module | Returns Structured Feedback | Has `actual_value` | Has `expected_value` | Has `delta` | Iteration-Ready |
|--------|---------------------------|-------------------|---------------------|-------------|-----------------|
| `physics/hydrostatics` | ✅ `HydrostaticsResults` | ✅ Yes | ⚠️ No threshold | ❌ No | ⚠️ Partial |
| `physics/resistance` | ✅ `ResistanceResults` | ✅ Yes | ⚠️ No threshold | ❌ No | ⚠️ Partial |
| `stability/intact_gm` | ✅ `IntactGMResults` | ✅ Yes | ✅ GM_MIN | ❌ No | ⚠️ Partial |
| `weight/estimation` | ⚠️ `WeightItem` list | ✅ Yes | ❌ No | ❌ No | ❌ No |
| `structural/scantlings` | ⚠️ Findings | ✅ Yes | ✅ Yes | ❌ No | ⚠️ Partial |

#### Missing: `delta_from_previous`

**NO MODULE** currently tracks `delta_from_previous`. This is critical for:

1. Agent learning ("my change improved GM by 0.15m")
2. Convergence detection ("stability oscillating, stop iteration")
3. User feedback ("beam increase caused 8% resistance penalty")

**Required Implementation:**

```python
# In program_executor.py or conductor.py:

class IterationTracker:
    """Track metric changes across iterations."""
    
    def __init__(self):
        self._previous_metrics: Dict[str, float] = {}
    
    def compute_delta(self, metric: str, current_value: float) -> Optional[float]:
        """Compute delta from previous iteration."""
        previous = self._previous_metrics.get(metric)
        self._previous_metrics[metric] = current_value
        
        if previous is None:
            return None
        return current_value - previous
    
    def wrap_validation(self, validation: Dict) -> Dict:
        """Add delta_from_previous to validation results."""
        result = dict(validation)
        
        for key in ["gm_m", "displacement_m3", "resistance_kn"]:
            if key in result:
                result[f"{key}_delta"] = self.compute_delta(key, result[key])
        
        return result
```

---

### Recommended Fixes (by Module)

#### Priority 0: Critical for Design Language Path

| # | Module | Issue | Fix | Effort |
|---|--------|-------|-----|--------|
| 1 | `program_executor.py` | Missing `compute_gm_from_geometry` | Create wrapper function | 1h |
| 2 | `program_executor.py` | Wrong `estimate_resistance` import | Change to `calculate_resistance` | 10m |
| 3 | `section_compiler.py` | Negative volume (winding order) | Add `_normalize_winding_order()` | 1h |
| 4 | `conductor.py` | `design_program` not stored | Store in `metadata.design_program` | 30m |

#### Priority 1: Enumeration Removal from Physics

| # | Module | Issue | Fix | Effort |
|---|--------|-------|-----|--------|
| 5 | `physics/hydrostatics.py` | Coefficient estimation uses `hull_type` | Derive from geometry shape | 4h |
| 6 | `physics/validators.py` | Maps to `HullType` enum | Remove enum, use body count | 2h |
| 7 | `physics/geometry_hydrostatics.py` | Checks `hull_type == "catamaran"` | Use section Y offset only | 1h |

#### Priority 2: Enumeration Removal from Weight/Structure

| # | Module | Issue | Fix | Effort |
|---|--------|-------|-----|--------|
| 8 | `weight/estimators/hull.py` | `HULL_TYPE_FACTORS` lookup | Derive factor from geometry | 2h |
| 9 | `weight/validators.py` | Reads `hull.hull_type` | Use geometry-derived params | 1h |
| 10 | `structural/scantlings.py` | `"displacement" in hull_type` | Use Froude number instead | 30m |

#### Priority 3: Feedback Structure Enhancement

| # | Module | Issue | Fix | Effort |
|---|--------|-------|-----|--------|
| 11 | All validators | No `delta_from_previous` | Add `IterationTracker` | 3h |
| 12 | `HydrostaticsResults` | No threshold | Add `required_*` fields | 1h |
| 13 | `program_executor.py` | Basic validation structure | Match design spiral spec | 2h |

#### Priority 4: Multi-Body Support

| # | Module | Issue | Fix | Effort |
|---|--------|-------|-----|--------|
| 14 | `physics/hydrostatics.py` | Single hull only | Add multi-body path | 4h |
| 15 | `weight/estimators/hull.py` | Single hull only | Sum per-body estimates | 2h |
| 16 | `stability/intact_gm.py` | Single hull only | Use `multi_body_hydrostatics` | 1h |

---

### Module Compatibility Summary

#### Overall Compatibility Score

| Aspect | Score | Notes |
|--------|-------|-------|
| Pipeline Map | ✅ 100% | All phases documented |
| Enumeration Freedom | ⚠️ 40% | 11 critical violations remain |
| Geometry Interface | ⚠️ 30% | Only 2/10 modules accept HullGeometry |
| Multi-Body Support | ⚠️ 20% | Only `multi_body_hydrostatics` + `compiler` |
| State Compatibility | ⚠️ 60% | Defaults prevent crashes, but suboptimal |
| Feedback Structure | ⚠️ 50% | Has values, missing `delta` |

#### What Works Today

```
Design Language Program
        ↓
    parser.py ✅
        ↓
    expander.py ✅
        ↓
    compiler.py ✅ (multi-body)
        ↓
    HullGeometry
        ↓
    multi_body_hydrostatics.py ✅
        ↓
    GM, BM, Volume (for multi-body)
```

#### What Doesn't Work Today

```
HullGeometry
        ↓
    physics/hydrostatics.py ❌ (needs hull_type)
        ↓
    weight/estimators/hull.py ❌ (needs hull_type)
        ↓
    structural/scantlings.py ❌ (needs hull_type)
```

#### Path to Full Module Compatibility

**Total effort: ~25 hours**

1. **Week 1 (8h)**: P0 fixes — validation glue code
2. **Week 2 (10h)**: P1-P2 fixes — enumeration removal
3. **Week 3 (7h)**: P3-P4 fixes — feedback + multi-body

After these fixes:

```
Novel Geometry → Compiles → Full Physics Validation → Structured Feedback → Iteration
                              ↑                              ↑
                         No hull_type              delta_from_previous
                         No HullFamily             For agent learning
```

---

## Part XIV: Change Propagation

The design spiral (propose → compile → validate → feedback) assumes discrete iterations. But real engineering requires **continuous propagation**: when one parameter changes, all dependent calculations must update automatically.

### The Propagation Contract

When an engineer or agent changes a value, the system must:

```python
# Example: Engineer changes beam
engineer_changes("hull.beam", 5.0)

# System response:
{
    "changed": "hull.beam",
    "previous_value": 4.5,
    "new_value": 5.0,
    
    "invalidated_phases": ["hull", "weight", "stability", "loading", "compliance", "cost"],
    "recomputed": {
        "hull.displacement_m3": {"previous": 120.5, "current": 134.2, "delta": +13.7},
        "hull.wetted_surface_m2": {"previous": 95.3, "current": 102.1, "delta": +6.8},
        "stability.gm_m": {"previous": 0.65, "current": 0.42, "delta": -0.23},
        "resistance.total_kn": {"previous": 45.2, "current": 52.8, "delta": +7.6},
        "weight.lightship_kg": {"previous": 45000, "current": 48500, "delta": +3500},
        "cost.build_usd": {"previous": 2100000, "current": 2280000, "delta": +180000},
    },
    
    "constraint_violations": [
        {
            "constraint": "hull.gm >= 0.5",
            "current_value": 0.42,
            "required_value": 0.5,
            "severity": "ERROR",
            "suggestion": "Consider reducing VCG or increasing beam further"
        }
    ],
    
    "cascade_time_ms": 127,
}
```

---

### State Key → Phase Invalidation Map

When these state keys change, these phases must re-run:

| State Key Changed | Invalidates Phases | Reason |
|-------------------|-------------------|--------|
| `hull.loa` | hull, structure, propulsion, weight, stability, loading, compliance, production, cost | Primary dimension |
| `hull.beam` | hull, weight, stability, loading, compliance, cost | Affects volume, GM, resistance |
| `hull.draft` | hull, weight, stability, loading, compliance, cost | Affects displacement, GM |
| `hull.displacement_m3` | weight, stability, loading, compliance, cost | Weight basis |
| `geometry.section.*` | hull, weight, stability, loading, compliance, cost | Form change |
| `geometry.body.*` | hull, weight, stability, loading, compliance, cost | Multi-body change |
| `structure.material` | structure, weight, production, cost | Scantlings recalc |
| `propulsion.engine_kw` | propulsion, weight, cost | Power/weight |
| `weight.lightship_kg` | stability, loading, compliance | GM, loading |
| `weight.vcg_m` | stability, loading, compliance | GM directly |
| `mission.speed_kts` | propulsion, resistance, compliance | Performance |
| `mission.range_nm` | propulsion, weight, cost | Fuel weight |

---

### Dependency Graph for Propagation

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                    GEOMETRY LAYER                        │
                    │  geometry.section, geometry.body, geometry.surface       │
                    └─────────────────────────┬───────────────────────────────┘
                                              │
                                              ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │                    HULL PARAMETERS                       │
                    │  hull.loa, hull.beam, hull.draft, hull.displacement      │
                    └───────┬─────────────────┬─────────────────┬─────────────┘
                            │                 │                 │
              ┌─────────────┘                 │                 └─────────────┐
              ▼                               ▼                               ▼
┌─────────────────────────┐   ┌─────────────────────────┐   ┌─────────────────────────┐
│       STRUCTURE         │   │       PROPULSION        │   │       ARRANGEMENT       │
│  scantlings, materials  │   │  power, engines, props  │   │  spaces, access         │
└───────────┬─────────────┘   └───────────┬─────────────┘   └─────────────────────────┘
            │                             │
            └──────────┬──────────────────┘
                       ▼
            ┌─────────────────────────┐
            │         WEIGHT          │
            │  lightship, VCG, LCG    │
            └───────────┬─────────────┘
                        │
                        ▼
            ┌─────────────────────────┐
            │        STABILITY        │
            │  GM, GZ curve, BM       │
            └───────────┬─────────────┘
                        │
                        ▼
            ┌─────────────────────────┐
            │        LOADING          │
            │  conditions, tanks      │
            └───────────┬─────────────┘
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
┌─────────────────────┐   ┌─────────────────────┐
│     COMPLIANCE      │   │     PRODUCTION      │
│  regulations, class │   │  build plan, BOM    │
└─────────┬───────────┘   └─────────┬───────────┘
          │                         │
          └───────────┬─────────────┘
                      ▼
            ┌─────────────────────────┐
            │          COST           │
            │  build, operate, LCC    │
            └─────────────────────────┘
```

---

### Selective Revalidation Algorithm

Only recompute phases whose inputs changed:

```python
class PropagationEngine:
    """Tracks dependencies and triggers selective revalidation."""
    
    # Phase dependencies (from Part XIII pipeline map)
    PHASE_DEPS = {
        "mission": set(),
        "hull": {"mission"},
        "structure": {"hull"},
        "propulsion": {"hull"},
        "arrangement": {"hull"},
        "weight": {"hull", "structure", "propulsion"},
        "stability": {"weight"},
        "loading": {"weight", "stability"},
        "compliance": {"stability", "loading", "mission"},
        "production": {"structure", "weight"},
        "cost": {"production"},
        "optimization": {"cost", "compliance"},
        "reporting": {"compliance", "cost"},
    }
    
    # State key to phase mapping
    KEY_TO_PHASE = {
        "hull.": "hull",
        "geometry.": "hull",
        "structure.": "structure",
        "propulsion.": "propulsion",
        "weight.": "weight",
        "stability.": "stability",
        "loading.": "loading",
        "mission.": "mission",
    }
    
    def get_invalidated_phases(self, changed_key: str) -> List[str]:
        """Get all phases that need recomputation."""
        # Find which phase owns this key
        source_phase = None
        for prefix, phase in self.KEY_TO_PHASE.items():
            if changed_key.startswith(prefix):
                source_phase = phase
                break
        
        if not source_phase:
            return []
        
        # BFS to find all downstream phases
        invalidated = {source_phase}
        queue = [source_phase]
        
        while queue:
            current = queue.pop(0)
            for phase, deps in self.PHASE_DEPS.items():
                if current in deps and phase not in invalidated:
                    invalidated.add(phase)
                    queue.append(phase)
        
        # Return in execution order
        order = ["mission", "hull", "structure", "propulsion", "arrangement",
                 "weight", "stability", "loading", "compliance", "production",
                 "cost", "optimization", "reporting"]
        return [p for p in order if p in invalidated]
    
    def propagate_change(
        self,
        key: str,
        new_value: Any,
        state_manager: 'StateManager',
        conductor: 'Conductor',
    ) -> 'PropagationResult':
        """Execute change and propagate through pipeline."""
        
        # Capture previous state
        previous_metrics = self._capture_metrics(state_manager)
        
        # Apply change
        state_manager.set(key, new_value, source="user_change")
        
        # Determine what to recompute
        phases_to_run = self.get_invalidated_phases(key)
        
        # Run phases in order
        results = {}
        for phase in phases_to_run:
            result = conductor.run_phase(phase)
            results[phase] = result
        
        # Capture new state and compute deltas
        current_metrics = self._capture_metrics(state_manager)
        deltas = self._compute_deltas(previous_metrics, current_metrics)
        
        # Check constraints
        violations = self._check_constraints(state_manager)
        
        return PropagationResult(
            changed_key=key,
            previous_value=previous_metrics.get(key),
            new_value=new_value,
            invalidated_phases=phases_to_run,
            metric_deltas=deltas,
            constraint_violations=violations,
            phase_results=results,
        )
```

---

### Delta Computation for All Metrics

After propagation, compute how every tracked metric changed:

```python
TRACKED_METRICS = [
    # Hull
    "hull.displacement_m3",
    "hull.wetted_surface_m2",
    "hull.block_coefficient",
    "hull.prismatic_coefficient",
    
    # Stability
    "stability.gm_m",
    "stability.bm_m",
    "stability.kb_m",
    "stability.gz_30_m",
    "stability.angle_of_vanishing_stability_deg",
    
    # Resistance/Performance
    "resistance.total_kn",
    "resistance.wave_kn",
    "resistance.friction_kn",
    "performance.max_speed_kts",
    "performance.range_nm",
    
    # Weight
    "weight.lightship_kg",
    "weight.deadweight_kg",
    "weight.vcg_m",
    "weight.lcg_m",
    
    # Cost
    "cost.build_usd",
    "cost.annual_operating_usd",
    "cost.lifecycle_usd",
]

def _compute_deltas(
    self,
    previous: Dict[str, float],
    current: Dict[str, float],
) -> Dict[str, MetricDelta]:
    """Compute delta for each tracked metric."""
    deltas = {}
    
    for metric in TRACKED_METRICS:
        prev_val = previous.get(metric)
        curr_val = current.get(metric)
        
        if prev_val is not None and curr_val is not None:
            delta = curr_val - prev_val
            pct_change = (delta / prev_val * 100) if prev_val != 0 else None
            
            deltas[metric] = MetricDelta(
                metric=metric,
                previous=prev_val,
                current=curr_val,
                delta=delta,
                percent_change=pct_change,
                direction="improved" if self._is_improvement(metric, delta) else "degraded",
            )
    
    return deltas

def _is_improvement(self, metric: str, delta: float) -> bool:
    """Determine if a change is an improvement."""
    # Metrics where LOWER is better
    LOWER_IS_BETTER = {
        "resistance.total_kn",
        "resistance.wave_kn",
        "resistance.friction_kn",
        "weight.lightship_kg",
        "cost.build_usd",
        "cost.annual_operating_usd",
        "cost.lifecycle_usd",
    }
    
    # Metrics where HIGHER is better
    HIGHER_IS_BETTER = {
        "stability.gm_m",
        "stability.gz_30_m",
        "performance.max_speed_kts",
        "performance.range_nm",
    }
    
    if metric in LOWER_IS_BETTER:
        return delta < 0
    elif metric in HIGHER_IS_BETTER:
        return delta > 0
    else:
        return True  # Neutral metrics
```

---

### Constraint Violation Surfacing

After propagation, check all constraints and surface violations:

```python
@dataclass
class ConstraintViolation:
    """A constraint that failed after propagation."""
    constraint_id: str
    expression: str          # "hull.gm >= 0.5"
    current_value: float     # 0.42
    required_value: float    # 0.5
    severity: str            # "ERROR" | "WARNING"
    caused_by: str           # "hull.beam" (the change that caused this)
    suggestion: str          # "Consider reducing VCG"

def _check_constraints(
    self,
    state_manager: 'StateManager',
) -> List[ConstraintViolation]:
    """Check all constraints against current state."""
    violations = []
    
    # Get all active constraints from state
    constraints = state_manager.get("constraints", {})
    
    for constraint_id, constraint in constraints.items():
        result = self._evaluate_constraint(constraint, state_manager)
        
        if not result.passes:
            violations.append(ConstraintViolation(
                constraint_id=constraint_id,
                expression=constraint.expression,
                current_value=result.actual_value,
                required_value=result.required_value,
                severity="ERROR" if constraint.is_hard else "WARNING",
                caused_by=self._last_changed_key,
                suggestion=self._generate_suggestion(constraint, result),
            ))
    
    return violations

def _generate_suggestion(
    self,
    constraint: 'Constraint',
    result: 'ConstraintResult',
) -> str:
    """Generate actionable suggestion for constraint violation."""
    
    # Common suggestions based on constraint type
    SUGGESTIONS = {
        "hull.gm": "Consider: increase beam, decrease VCG, add ballast",
        "hull.displacement": "Consider: adjust dimensions, reduce payload",
        "resistance.total": "Consider: finer bow, reduce wetted surface",
        "weight.lightship": "Consider: lighter materials, optimize structure",
        "cost.build": "Consider: simpler construction, standard components",
    }
    
    for key, suggestion in SUGGESTIONS.items():
        if key in constraint.expression:
            gap = result.required_value - result.actual_value
            return f"{suggestion}. Gap: {gap:.2f}"
    
    return "Review design parameters affecting this constraint"
```

---

### Auto-Adjustment for Constraint Satisfaction

When a constraint violation occurs, the system can suggest or auto-apply adjustments:

```python
class ConstraintSolver:
    """Attempts to satisfy constraints by adjusting parameters."""
    
    # Which parameters can be adjusted to satisfy which constraints
    ADJUSTMENT_MAP = {
        "stability.gm_m": [
            ("hull.beam", +0.1, "Increase beam"),
            ("weight.vcg_m", -0.1, "Lower VCG"),
            ("weight.ballast_kg", +1000, "Add ballast"),
        ],
        "resistance.total_kn": [
            ("hull.beam", -0.05, "Reduce beam"),
            ("hull.loa", +0.5, "Lengthen hull"),
        ],
        "weight.lightship_kg": [
            ("structure.material", "aluminum", "Switch to aluminum"),
            ("hull.loa", -0.5, "Reduce length"),
        ],
    }
    
    def suggest_adjustments(
        self,
        violation: ConstraintViolation,
        state_manager: 'StateManager',
    ) -> List[SuggestedAdjustment]:
        """Generate possible adjustments to satisfy constraint."""
        suggestions = []
        
        # Get adjustment options for this constraint type
        for metric_key in self.ADJUSTMENT_MAP:
            if metric_key in violation.expression:
                for param, delta, reason in self.ADJUSTMENT_MAP[metric_key]:
                    current = state_manager.get(param)
                    
                    if current is not None:
                        if isinstance(delta, (int, float)):
                            new_value = current + delta
                        else:
                            new_value = delta
                        
                        suggestions.append(SuggestedAdjustment(
                            parameter=param,
                            current_value=current,
                            suggested_value=new_value,
                            reason=reason,
                            estimated_impact=self._estimate_impact(
                                violation, param, delta
                            ),
                        ))
        
        return suggestions
    
    def auto_adjust(
        self,
        violation: ConstraintViolation,
        state_manager: 'StateManager',
        conductor: 'Conductor',
        max_iterations: int = 10,
    ) -> AutoAdjustResult:
        """Iteratively adjust parameters until constraint is satisfied."""
        
        for i in range(max_iterations):
            suggestions = self.suggest_adjustments(violation, state_manager)
            
            if not suggestions:
                return AutoAdjustResult(success=False, reason="No adjustments available")
            
            # Apply the first (best) suggestion
            best = suggestions[0]
            propagation = propagation_engine.propagate_change(
                best.parameter,
                best.suggested_value,
                state_manager,
                conductor,
            )
            
            # Check if constraint is now satisfied
            remaining_violations = [
                v for v in propagation.constraint_violations
                if v.constraint_id == violation.constraint_id
            ]
            
            if not remaining_violations:
                return AutoAdjustResult(
                    success=True,
                    iterations=i + 1,
                    adjustments_made=[best],
                    final_value=state_manager.get(violation.expression.split()[0]),
                )
        
        return AutoAdjustResult(success=False, reason="Max iterations reached")
```

---

### Propagation API Endpoint

Expose change propagation through the API:

```python
@app.post("/api/v1/propagate", tags=["Design Language"])
async def propagate_change(
    request: PropagateRequest,
    state_manager=Depends(get_state_manager),
    conductor=Depends(get_conductor),
):
    """
    Change a parameter and propagate through the pipeline.
    
    Returns deltas for all affected metrics and any constraint violations.
    """
    engine = PropagationEngine()
    
    result = engine.propagate_change(
        key=request.key,
        new_value=request.value,
        state_manager=state_manager,
        conductor=conductor,
    )
    
    return {
        "success": len(result.constraint_violations) == 0,
        "changed": {
            "key": result.changed_key,
            "previous": result.previous_value,
            "new": result.new_value,
        },
        "invalidated_phases": result.invalidated_phases,
        "deltas": {
            k: {
                "previous": v.previous,
                "current": v.current,
                "delta": v.delta,
                "percent_change": v.percent_change,
                "direction": v.direction,
            }
            for k, v in result.metric_deltas.items()
        },
        "constraint_violations": [
            {
                "constraint": v.expression,
                "current": v.current_value,
                "required": v.required_value,
                "severity": v.severity,
                "suggestion": v.suggestion,
            }
            for v in result.constraint_violations
        ],
        "cascade_time_ms": result.cascade_time_ms,
    }


class PropagateRequest(BaseModel):
    """Request to propagate a parameter change."""
    key: str              # "hull.beam"
    value: Any            # 5.0
    auto_adjust: bool = False  # Attempt to fix constraint violations
```

---

### Example: Beam Change Propagation

```python
# Engineer changes beam from 4.5m to 5.0m
POST /api/v1/propagate
{
    "key": "hull.beam",
    "value": 5.0
}

# Response shows full cascade
{
    "success": false,  # Constraint violated
    
    "changed": {
        "key": "hull.beam",
        "previous": 4.5,
        "new": 5.0
    },
    
    "invalidated_phases": [
        "hull", "weight", "stability", "loading", "compliance", "cost"
    ],
    
    "deltas": {
        "hull.displacement_m3": {
            "previous": 120.5,
            "current": 134.2,
            "delta": 13.7,
            "percent_change": 11.4,
            "direction": "neutral"
        },
        "stability.gm_m": {
            "previous": 0.65,
            "current": 0.42,
            "delta": -0.23,
            "percent_change": -35.4,
            "direction": "degraded"  # GM dropped!
        },
        "resistance.total_kn": {
            "previous": 45.2,
            "current": 52.8,
            "delta": 7.6,
            "percent_change": 16.8,
            "direction": "degraded"
        },
        "cost.build_usd": {
            "previous": 2100000,
            "current": 2280000,
            "delta": 180000,
            "percent_change": 8.6,
            "direction": "degraded"
        }
    },
    
    "constraint_violations": [
        {
            "constraint": "stability.gm_m >= 0.5",
            "current": 0.42,
            "required": 0.5,
            "severity": "ERROR",
            "suggestion": "Consider: increase beam further, decrease VCG, add ballast. Gap: 0.08"
        }
    ],
    
    "cascade_time_ms": 127
}
```

---

### Integration with Design Spiral

Change propagation connects to the iterative design spiral:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DESIGN SPIRAL WITH PROPAGATION                       │
│                                                                              │
│   USER/AGENT INTENT                                                          │
│   "Make it wider"                                                            │
│        │                                                                     │
│        ▼                                                                     │
│   CHANGE PROPOSED                                                            │
│   propagate_change("hull.beam", 5.0)                                        │
│        │                                                                     │
│        ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    PROPAGATION ENGINE                                │   │
│   │                                                                      │   │
│   │   1. Identify affected phases (hull → weight → stability → ...)     │   │
│   │   2. Re-run phases in dependency order                               │   │
│   │   3. Compute deltas for ALL tracked metrics                          │   │
│   │   4. Check ALL constraints                                           │   │
│   │   5. Return structured result                                        │   │
│   │                                                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│        │                                                                     │
│        ▼                                                                     │
│   FEEDBACK TO USER/AGENT                                                     │
│   "Beam +0.5m caused: displacement +11%, GM -35% (VIOLATION), cost +8%"     │
│        │                                                                     │
│        ▼                                                                     │
│   AGENT DECISION                                                             │
│   Option A: Accept trade-off, fix GM by lowering VCG                        │
│   Option B: Revert beam change, try different approach                      │
│   Option C: Request auto-adjust to satisfy constraint                       │
│        │                                                                     │
│        └──────────────────────► [NEXT ITERATION]                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Dependency graph | ✅ Defined | In Part XIII |
| State key → phase map | ✅ Defined | In this section |
| Propagation algorithm | 📋 Specified | Needs implementation |
| Delta computation | 📋 Specified | Needs implementation |
| Constraint checking | 📋 Specified | Needs implementation |
| Auto-adjustment | 📋 Specified | Needs implementation |
| API endpoint | 📋 Specified | Needs implementation |

**Implementation effort: ~8 hours**

1. `PropagationEngine` class (3h)
2. Delta computation + constraint checking (2h)
3. Auto-adjustment solver (2h)
4. API endpoint integration (1h)

---

## Appendices

### Appendix A: Key Files Reference

| File | Purpose | Status |
|------|---------|--------|
| `magnet/kernel/stdlib/parser.py` | Parse DSL → AST | ✅ Complete |
| `magnet/kernel/stdlib/expander.py` | AST → Actions | ✅ Complete |
| `magnet/kernel/stdlib/compiler.py` | State → HullGeometry | ⚠️ Volume bug |
| `magnet/kernel/stdlib/type_registry.py` | Primitive schemas | ✅ Complete |
| `magnet/kernel/stdlib/policies.py` | DERIVE policies | ✅ No hull_type |
| `magnet/kernel/program_executor.py` | End-to-end pipeline | ⚠️ Import errors |
| `magnet/kernel/conductor.py` | Phase orchestration | ⚠️ Orphaned path |
| `magnet/physics/multi_body_hydrostatics.py` | Parallel axis BM | ✅ Complete |
| `magnet/agents/geometry_proposer.py` | LLM → geometry.* | ✅ Complete |
| `magnet/stability/intact_gm.py` | GM calculation | ⚠️ Missing wrapper |
| `magnet/physics/resistance.py` | Resistance calculation | ✅ Function exists |
| `magnet/deployment/api.py` | REST endpoints | ⚠️ Needs new endpoint |

### Appendix B: Sacred Invariants

These must never be violated:

1. **"Any hull form that requires a new language primitive is a failure of the language."**
2. **"Agents never coordinate on features — they coordinate on geometry and constraints only."**
3. **"body_type, physics_category, surface_type are FREEFORM strings (not enums)."**
4. **"The kernel validates physics, not design intent."**
5. **"Same proposal + same state → same result."**
6. **"Feedback must be quantified, not just pass/fail."**
7. **"One path. No silent fallbacks."**

### Appendix C: Forbidden Terms in Kernel

These strings must NEVER appear in `magnet/kernel/stdlib/`:

```
catamaran, trimaran, monohull, swath, proa, outrigger_canoe,
patrol_boat, workboat, ferry, yacht, tanker, container_ship,
fishing_vessel, crew_boat, pilot_boat, tug, research_vessel
```

Test command:
```bash
grep -r "catamaran\|trimaran\|patrol_boat" magnet/kernel/stdlib/
```

Expected result: No matches.

### Appendix D: Test Commands

**Run invariant tests:**
```bash
python3 -m pytest tests/invariants/ -v
```

**Test full pipeline:**
```bash
python3 -c "
from magnet.kernel.program_executor import execute_program
result = execute_program('CREATE geometry.body main {}', initial_state={})
print(result.success, result.errors)
"
```

**Check for forbidden terms:**
```bash
grep -rn "HullFamily\|HullType\|catamaran" magnet/kernel/stdlib/
```

---

## Appendix E: Implementation Checklist

### P0: Make Validation Work
- [ ] Create `compute_gm_from_geometry` in `intact_gm.py`
- [ ] Fix `estimate_resistance` import in `program_executor.py`
- [ ] Add `_normalize_winding_order` in `section_compiler.py`
- [ ] Test: Volume is positive
- [ ] Test: GM returns a number
- [ ] Test: Resistance returns a number

### P1: Establish Authority
- [ ] Add `design_program` storage to state
- [ ] Create `/api/v1/design-language` endpoint
- [ ] Update conductor to find design_program
- [ ] Test: Conductor triggers new path
- [ ] Test: Explain records generated
- [ ] Test: Old path is not used

### P2: Complete the Loop
- [ ] Add `delta_from_previous` to feedback
- [ ] Add timing metrics (parse/compile/validate)
- [ ] Configure LLM API key
- [ ] Test: Full iteration cycle <1s
- [ ] Test: Agent can iterate on feedback

---

## Appendix F: Architecture After Integration

The design language path is now integrated into the conductor:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ UNIFIED PATH (conductor routes automatically)                                │
│                                                                              │
│   POST /run-phases OR POST /api/v1/designs/{id}/phases/hull/run             │
│        ↓                                                                     │
│   kernel/conductor.py ──→ run_phase("hull")                                 │
│        ↓                                                                     │
│   Check: state.get("design_program") != None?                               │
│        ↓                                                                     │
│   ┌────┴────┐                                                               │
│   │ YES     │ NO                                                            │
│   ↓         ↓                                                               │
│   _run_program_generation()         _run_hull_synthesis()                   │
│   (NEW PATH)                        (LEGACY PATH)                           │
│        ↓                                 ↓                                  │
│   program_executor.py              HullFamily enum                          │
│        ↓                                 ↓                                  │
│   kernel/stdlib/*                  synthesis.py                             │
│        ↓                                 ↓                                  │
│   HullGeometry                     HullGeometry                             │
│        ↓                                 ↓                                  │
│   _record_program_explain()        (existing explain)                       │
│        ↓                                 ↓                                  │
│   Continue to downstream phases... ─────┘                                   │
│                                                                              │
│   ✅ Conductor orchestration preserved                                       │
│   ✅ Explain records work for both paths                                     │
│   ✅ Downstream phases triggered normally                                    │
│   ✅ State management works                                                  │
│   ✅ Novel geometry when design_program present                              │
│   ✅ Legacy path unchanged when no design_program                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ DIRECT API ACCESS (also available)                                           │
│                                                                              │
│   POST /api/v1/program ──→ execute_program() directly                       │
│   POST /api/v1/propose ──→ LLM generates geometry primitives                │
│   POST /api/v1/propose-and-execute ──→ LLM + execute in one call            │
│                                                                              │
│   Use these for:                                                             │
│   - Testing design programs directly                                         │
│   - LLM-assisted design without full pipeline                                │
│   - Dry-run validation                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix G: How to Use the New Path

### Method 1: Via Conductor (Integrated — Recommended)

Set `design_program` in state before running hull phase:

```python
# Store design program in state
state_manager._state.metadata["design_program"] = """
CREATE geometry.body main { body_type: "slender_displacement", physics_category: "surface_piercing" }
CREATE geometry.section bow { station: 0.0, body_id: "main", points: [[0,0], [1.5,-0.5], [1.5,-2], [0,-2.5]] }
CREATE geometry.section mid { station: 0.5, body_id: "main", points: [[0,0], [2,-0.5], [2,-2.5], [0,-3]] }
CREATE geometry.section stern { station: 1.0, body_id: "main", points: [[0,0], [1.5,-0.4], [1.5,-1.8], [0,-2.2]] }
SET hull.loa = 25.0
CONSTRAIN hull.gm >= 0.5
"""

# Now run hull phase - automatically uses new path
from magnet.kernel.conductor import Conductor
conductor = Conductor(state_manager)
conductor.create_session("my_design")
result = conductor.run_phase("hull")  # Uses design language path
```

**Benefits:**
- Explain records generated
- Downstream phases triggered
- State management preserved
- Full audit trail

### Method 2: Via Direct API

For testing or standalone use:

```bash
# Direct program execution
curl -X POST http://localhost:8000/api/v1/program \
  -H "Content-Type: application/json" \
  -d '{
    "program_text": "CREATE geometry.body main { body_type: \"test\" }",
    "dry_run": false
  }'

# LLM-assisted (requires API key)
curl -X POST http://localhost:8000/api/v1/propose-and-execute \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "Create a 25m fast patrol vessel with twin hulls",
    "min_confidence": 0.6
  }'
```

### Method 3: Programmatic (Python)

```python
from magnet.kernel.program_executor import execute_program

program = """
CREATE geometry.body main { body_type: "novel_form", physics_category: "surface_piercing" }
CREATE geometry.section bow { station: 0.0, body_id: "main", points: [[0,0], [1.5,-0.5], [1.5,-2], [0,-2.5]] }
CREATE geometry.section stern { station: 1.0, body_id: "main", points: [[0,0], [1.2,-0.3], [1.2,-1.5], [0,-1.8]] }
"""

result = execute_program(
    program_text=program,
    initial_state={"hull": {"loa": 25.0}},
    validate=True,
)

print(f"Success: {result.success}")
print(f"Geometry: {result.geometry}")
print(f"Validation: {result.validation}")
```

---

## Appendix H: API Endpoints Reference

### Design Language Endpoints (New Path)

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/api/v1/program` | POST | Execute design program directly | ✅ Implemented |
| `/api/v1/propose` | POST | LLM generates geometry from intent | ✅ Implemented |
| `/api/v1/propose-and-execute` | POST | LLM + execute in one call | ✅ Implemented |
| `/api/v1/design-language` | POST | Execute via conductor (authoritative) | ⚠️ Needs integration |

### Request/Response Examples

**POST /api/v1/program**
```json
// Request
{
  "program_text": "CREATE geometry.body main {...}",
  "design_id": "optional-id",
  "dry_run": false
}

// Response
{
  "success": true,
  "design_id": "generated-id",
  "actions_applied": 5,
  "validation": {"hydrostatics": {...}},
  "errors": [],
  "geometry_generated": true
}
```

**POST /api/v1/propose**
```json
// Request
{
  "intent": "Create a fast patrol vessel",
  "constraints": ["GM >= 0.8m"]
}

// Response
{
  "success": true,
  "program_text": "CREATE geometry.body main {...}",
  "program_id": "prop_abc123",
  "operations_count": 7,
  "average_confidence": 0.85,
  "errors": []
}
```

---

## Appendix I: Verification Commands

### Test Isolation (No HullFamily in New Path)

```bash
# Should return NOTHING
grep -r "HullFamily" magnet/kernel/stdlib/ magnet/kernel/program_executor.py magnet/agents/geometry_proposer.py
```

### Test Full Pipeline

```bash
python3 -c "
from magnet.kernel.program_executor import execute_program

program = '''
CREATE geometry.body main { body_type: \"test\", physics_category: \"surface_piercing\" }
CREATE geometry.section bow { station: 0.0, body_id: \"main\", points: [[0,0], [1.5,-0.5], [1.5,-2], [0,-2.5]] }
CREATE geometry.section stern { station: 1.0, body_id: \"main\", points: [[0,0], [1.2,-0.3], [1.2,-1.5], [0,-1.8]] }
'''

result = execute_program(program, initial_state={'hull': {'loa': 25.0}}, validate=True)
print(f'Success: {result.success}')
print(f'Geometry sections: {len(result.geometry.sections) if result.geometry else 0}')
print(f'Validation: {result.validation}')
"
```

### Test API Endpoints

```bash
# Start server
cd /Users/bengibson/MAGNETV1
uvicorn magnet.deployment.api:app --host 0.0.0.0 --port 8000

# In another terminal:
curl -X POST http://localhost:8000/api/v1/program \
  -H "Content-Type: application/json" \
  -d '{"program_text": "CREATE geometry.body main {}", "dry_run": true}'
```

---

## Appendix J: Implementation Status Summary

### Wire New Path Guide Tasks

| Task | Description | Status |
|------|-------------|--------|
| Task 1 | Add `/program` endpoint | ✅ DONE |
| Task 2 | Add `/propose` endpoint | ✅ DONE |
| Task 3 | Add `/propose-and-execute` endpoint | ✅ DONE |
| Task 4 | Add isolation invariant tests | ✅ DONE |
| Task 5 | Update ExecutionResult with constraints | ✅ DONE |
| Task 6 | OpenAPI documentation | ✅ Tags added |

### Module Compatibility Audit

**Full audit in:** [Part XIII: Module Compatibility Audit](#part-xiii-module-compatibility-audit)

| Aspect | Score | Notes |
|--------|-------|-------|
| Pipeline Map | ✅ 100% | All 13 phases documented |
| Enumeration Freedom | ⚠️ 40% | 11 critical violations remain in 39 files |
| Geometry Interface | ⚠️ 30% | Only 2/10 modules accept HullGeometry |
| Multi-Body Support | ⚠️ 20% | Only `multi_body_hydrostatics` + `compiler` |
| State Compatibility | ⚠️ 60% | Defaults prevent crashes |
| Feedback Structure | ⚠️ 50% | Missing `delta_from_previous` |

**Critical Enumeration Violations (Must Fix):**
- `kernel/synthesis.py` — Entire legacy path (86 references)
- `physics/validators.py` — Maps to HullType enum
- `physics/hydrostatics.py` — Coefficient estimation
- `hull_gen/generator.py` — Section dispatch
- `weight/estimators/hull.py` — Factor lookup

### Remaining Work (From This Guide)

| Category | Task | Status |
|----------|------|--------|
| **P0: Validation** | `compute_gm_from_geometry` wrapper | ⚠️ TODO |
| **P0: Validation** | Fix `estimate_resistance` import | ⚠️ TODO |
| **P0: Compilation** | Section winding normalization | ⚠️ TODO |
| **P1: Authority** | `design_program` state storage | ⚠️ TODO |
| **P1: Authority** | Conductor-integrated endpoint | ⚠️ TODO |
| **P2: Loop** | `delta_from_previous` feedback | ⚠️ TODO |
| **P2: Loop** | Timing metrics | ⚠️ TODO |

### Notes

- **LLM Required:** `/propose` and `/propose-and-execute` require Anthropic API key
- **Backwards Compatible:** Old path works when no `design_program` in state
- **Explain Records:** Both paths record provenance for downstream phases
- **No HullFamily Deletion:** Legacy path still available for existing workflows

---

## Part XV: Two Coexisting Paths (Architecture Clarification)

### Two Systems — Both Correct

| System | Purpose | Status |
|--------|---------|--------|
| **OLD PATH** | Parameter refinement (hull.beam, mission.speed) | Legacy, works |
| **NEW PATH** | Geometry primitives (geometry.body, geometry.section) | New, works |

**These are NOT meant to merge. They coexist until the old path is deprecated.**

### OLD PATH: Parameter Refinement

```
intent_protocol.py → ActionPlanValidator → ActionExecutor → synthesis.py → HullFamily
```

- Uses `REFINABLE_SCHEMA` paths (hull.loa, mission.max_speed_kts)
- Routes through `synthesis.py` which uses `HullFamily` enum
- Good for iterative parameter tuning on existing designs
- Tied to enumerated hull types

### NEW PATH: Geometry Primitives

```
geometry_proposer.py → program_executor.py → compiler.py → HullGeometry
```

- Uses geometry primitives (geometry.body, geometry.section)
- Bypasses `synthesis.py` and `HullFamily` entirely
- Enables infinite novel forms without new code
- NO enumeration

### Chat-Based Design Loop (NEW PATH)

The `DesignConversation` class (`magnet/agents/design_conversation.py`) provides the iterative loop:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   NEW PATH: CHAT-BASED DESIGN LOOP                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Engineer                                                               │
│     │                                                                   │
│     │ "Create twin hull vessel" OR direct DSL                          │
│     ▼                                                                   │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │ DesignConversation                                             │    │
│  │ (magnet/agents/design_conversation.py)                         │    │
│  │                                                                │    │
│  │ - Session management                                           │    │
│  │ - Message history                                              │    │
│  │ - Metrics tracking                                             │    │
│  │ - Delta computation                                            │    │
│  └────────────────────┬───────────────────────────────────────────┘    │
│                       │                                                 │
│                       │ Direct DSL or via GeometryProposer (LLM)       │
│                       ▼                                                 │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │ program_executor.py                                            │    │
│  │                                                                │    │
│  │ - Parses DSL (parser.py)                                       │    │
│  │ - Expands to actions (expander.py)                            │    │
│  │ - Compiles to HullGeometry (compiler.py)                      │    │
│  │ - Runs validation (hydrostatics, resistance)                  │    │
│  │                                                                │    │
│  │ NO HullFamily. NO synthesis.py.                               │    │
│  └────────────────────┬───────────────────────────────────────────┘    │
│                       │                                                 │
│                       ▼                                                 │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │ ExecutionResult                                                │    │
│  │                                                                │    │
│  │ - geometry: HullGeometry                                       │    │
│  │ - validation: {hydrostatics, resistance, constraints}         │    │
│  │ - actions: List[Action]                                        │    │
│  │ - success: bool                                                │    │
│  └────────────────────┬───────────────────────────────────────────┘    │
│                       │                                                 │
│                       ▼                                                 │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │ Feedback to Engineer                                           │    │
│  │                                                                │    │
│  │ ## Iteration 2 Results                                         │    │
│  │ ### Stability                                                  │    │
│  │ - GM: 1.39m ✅ (Δ +1.92m ↑)                                     │    │
│  │ - Method: parallel_axis_theorem                                │    │
│  │                                                                │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Engineer iterates...                                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### API Endpoints

| Endpoint | Path | Description |
|----------|------|-------------|
| NEW PATH | `POST /api/v1/design/chat` | Chat-based geometry design |
| NEW PATH | `POST /api/v1/design-language` | Direct DSL execution via conductor |
| NEW PATH | `POST /api/v1/propagate` | Change propagation |
| OLD PATH | `POST /api/v1/designs/{id}/intent/preview` | Parameter refinement preview |

### Test Results

```
Test 1: Single hull → GM: -0.52m (unstable)
Test 2: Add twin hulls → GM: +1.39m ✅ (parallel axis theorem)
Delta: +1.92m improvement

20/20 invariant tests passing
```

---

## Part XVI: Implementation Status

### Completed (All Working)

| Component | Status | Notes |
|-----------|--------|-------|
| `ast_nodes.py` | ✅ Done | Parser AST nodes |
| `parser.py` | ✅ Done | DSL parser |
| `type_registry.py` | ✅ Done | Geometry schemas |
| `expander.py` | ✅ Done | AST → Actions |
| `policies.py` | ✅ Done | DERIVE policies |
| `section_compiler.py` | ✅ Done | Section compilation |
| `compiler.py` | ✅ Done | Full geometry compilation |
| `program_executor.py` | ✅ Done | End-to-end execution |
| `multi_body_hydrostatics.py` | ✅ Done | Parallel axis theorem |
| `geometry_proposer.py` | ✅ Done | LLM → geometry agent |
| `design_conversation.py` | ✅ Done | Chat-based design loop |
| `propagation.py` | ✅ Done | Change propagation |
| Conductor integration | ✅ Done | Design program detection |
| `/api/v1/design-language` | ✅ Done | Conductor-routed endpoint |
| `/api/v1/design/chat` | ✅ Done | Chat-based design endpoint |
| `/api/v1/propagate` | ✅ Done | Propagation endpoint |
| Invariant tests | ✅ Done | 20 tests passing |

### The Design Loop Works

```python
# Direct DSL (no LLM required)
POST /api/v1/design/chat
{
  "message": "CREATE geometry.body port { body_type: \"demihull\", offset_y_m: -4.0 }\nCREATE geometry.body stbd { body_type: \"demihull\", offset_y_m: 4.0 }",
  "use_llm": false
}

# Natural language (requires LLM)
POST /api/v1/design/chat
{
  "message": "Create a 25m fast patrol vessel with twin hulls",
  "use_llm": true
}

# Continue conversation
POST /api/v1/design/chat
{
  "message": "Make it more stable",
  "conversation_id": "...",
  "use_llm": true
}
```

### Remaining Work (Optional Enhancements)

| Task | Priority | Status |
|------|----------|--------|
| Connect to WebSocket for real-time updates | P2 | ⚠️ Optional |
| Persist conversations to DB | P2 | ⚠️ Optional |
| Deprecate old path | P3 | ⚠️ Future |

---

*This document is the source of truth for MAGNET system state and implementation. Update as the system evolves.*
