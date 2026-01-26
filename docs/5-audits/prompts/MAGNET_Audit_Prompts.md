# MAGNET Codebase & System Integration Audit

<!-- AGENT_CONTEXT
Purpose: [TODO: Add purpose description]
Authoritative: No
Keywords: [magnet, audit, prompts]
Depends_On: None
Used_By: [TODO: Add users]
Status: current
Last_Verified: 2026-01-15
-->


**Version:** 1.0  
**Date:** 2026-01-05  
**Purpose:** Comprehensive audit of the MAGNET codebase against failure modes and system integration requirements  
**Alignment:** MAGNET_Design_Language_Spec_v1.0.md, MAGNET_Unified_Implementation_Plan.md, MAGNET_Failure_Modes_And_Mitigations.md

---

## What MAGNET Is

```
┌─────────────────────────────────────────────────────────────────┐
│                         ENGINEER                                │
│     (infinite creativity, domain knowledge, quality judgment)   │
└──────────────────────────────────────┬──────────────────────────┘
                                       │
                                       ▼
                            "Make the bow finer"
                            "Try a stepped configuration"
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT SWARM                                │
│          (translates intent → geometry primitives)              │
└──────────────────────────────────────┬──────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                         KERNEL                                  │
│              (validates physics, returns feedback)              │
└──────────────────────────────────────┬──────────────────────────┘
                                       │
                                       ▼
                    Results + quantified tradeoffs
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                         ENGINEER                                │
│                   (judges, refines, iterates)                   │
└─────────────────────────────────────────────────────────────────┘
```

**Core Equation:**

```
Engineer Productivity = (Arbitrary Expression) × (Quantified Feedback) × (No Artificial Limits)
```

> **Any hull form that requires a new language primitive is a failure of the language.**

**Agent Coordination Rule:** Agents never coordinate on "features" — they coordinate on **geometry and constraints only**.

---

## Executive Summary

The MAGNET codebase contains **strong foundational components** for geometry, physics, and validation but has critical gaps for the new multi-agent compositional architecture. The audit identified:

**REUSE (High Confidence):**
- `hull_gen/geometry.py` — Canonical geometry data structures (`HullSection`, `Point3D`, `HullGeometry`)
- `hull_gen/nurbs.py` — NURBS curve/surface with `gaussian_curvature()` for developability
- `physics/resistance.py` — Already has `method_valid` and `validity_note` fields
- `stability/intact_gm.py` — Pure physics, returns quantified feedback
- `optimization/sensitivity.py` — Computes ∂objective/∂variable (gradients exist!)

**DELETE:**
- `kernel/priors/hull_families.py` — `HullFamily` enum (PATROL, WORKBOAT, FERRY, PLANING, CATAMARAN) violates "no enumerated designs"

**MODIFY (Significant):**
- `hull_gen/generator.py` — Uses `HullType` enum for dispatch; needs primitive-based generation
- `hull_gen/enums.py` — `HullType` enum; change to freeform string or remove
- `kernel/synthesis.py` — Uses family priors for bootstrap; needs physics-derived cold start

**GAPS:**
- **Quantified Feedback** — Validation returns pass/fail, not gradients
- **Multi-Body Composition** — No `geometry.body` + `geometry.attachment` support
- **Semantic Intent Layer** — LLMs must specify raw NURBS control points (they can't)
- **Validity Envelopes** — `method_valid` exists but not exposed to agents

**Estimated Implementation Effort:** 14 working days (engineer-in-loop focused)

---

# Part 1: Codebase Audit

## 1.1 File-by-File Inventory

### kernel/

| File | Purpose | Reuse | Delete | Modify | Notes |
|:-----|:--------|:------|:-------|:-------|:------|
| `kernel/validator.py` | Orchestrates validation pipeline | ✅ | | | Reusable, clean interface |
| `kernel/action_validator.py` | Validates ActionPlans against REFINABLE_SCHEMA | ✅ | | Minor | Add quantified feedback |
| `kernel/action_executor.py` | Executes validated actions | ✅ | | | Transaction support works |
| `kernel/synthesis.py` | Hull synthesis from mission | | | **Major** | Uses `HullFamily` enum |
| `kernel/conductor.py` | Phase orchestration | ✅ | | | Reusable |
| `kernel/priors/hull_families.py` | Family priors for synthesis | | **DELETE** | | `HullFamily` enum |
| `kernel/intent_protocol.py` | Action/ActionPlan schemas | ✅ | | Minor | Add `DesignProgram` ops |

### hull_gen/

| File | Purpose | Reuse | Delete | Modify | Notes |
|:-----|:--------|:------|:-------|:-------|:------|
| `hull_gen/geometry.py` | Canonical geometry: `HullSection`, `Point3D`, `HullGeometry` | **✅ CANONICAL** | | | **Do not duplicate** |
| `hull_gen/nurbs.py` | NURBS curves/surfaces, `gaussian_curvature()` | **✅ HIGH** | | | Ready for developability |
| `hull_gen/generator.py` | Parametric hull generator | | | **Major** | Uses `HullType` dispatch |
| `hull_gen/enums.py` | `HullType`, `ChineType`, etc. | | | **Major** | Remove or freeform |
| `hull_gen/parameters.py` | `HullDefinition`, `MainDimensions` | ✅ | | Minor | Support multi-body |
| `hull_gen/bow_generator.py` | Bow form generation | ✅ | | | Uses primitives |
| `hull_gen/transom_generator.py` | Transom generation | ✅ | | | Uses primitives |
| `hull_gen/deck_generator.py` | Deck surface generation | ✅ | | | Uses primitives |
| `hull_gen/modifiers/` | Spray rail, knuckle, tumblehome | ✅ | | | Compositional modifiers |

### physics/

| File | Purpose | Reuse | Delete | Modify | Notes |
|:-----|:--------|:------|:-------|:-------|:------|
| `physics/resistance.py` | Holtrop-Mennen resistance | **✅ HIGH** | | Minor | Already has `method_valid`, `validity_note` |

### stability/

| File | Purpose | Reuse | Delete | Modify | Notes |
|:-----|:--------|:------|:-------|:-------|:------|
| `stability/intact_gm.py` | GM calculation | **✅ HIGH** | | Minor | Add gradient output |

### analysis/

| File | Purpose | Reuse | Delete | Modify | Notes |
|:-----|:--------|:------|:-------|:-------|:------|
| `analysis/seakeeping_predictor.py` | Simplified seakeeping | ✅ | | | Uses geometry directly |

### optimization/

| File | Purpose | Reuse | Delete | Modify | Notes |
|:-----|:--------|:------|:-------|:-------|:------|
| `optimization/sensitivity.py` | Computes ∂objective/∂variable | **✅ HIGH** | | | **Gradients exist!** |
| `optimization/pareto.py` | Pareto front tracking | ✅ | | | Multi-objective support |

### core/

| File | Purpose | Reuse | Delete | Modify | Notes |
|:-----|:--------|:------|:-------|:-------|:------|
| `core/state_manager.py` | State + transactions | ✅ | | Minor | Add provenance for primitives |
| `core/parameter_bounds.py` | Bounds for clamping | ✅ | | **Major** | Only 5 params; expand |
| `core/refinable_schema.py` | REFINABLE_SCHEMA | ✅ | | Minor | Add geometry.* types |

### deployment/

| File | Purpose | Reuse | Delete | Modify | Notes |
|:-----|:--------|:------|:-------|:-------|:------|
| `deployment/api.py` | FastAPI REST endpoints | ✅ | | Minor | Add `/program` endpoint |
| `deployment/websocket.py` | WebSocket for updates | ✅ | | | Works |
| `deployment/intent_parser.py` | Natural language → actions | | | **Major** | Integrate swarm |

### app/src/ (Frontend)

| File | Purpose | Reuse | Delete | Modify | Notes |
|:-----|:--------|:------|:-------|:-------|:------|
| `app/src/App.tsx` | Main app component | ✅ | | | |
| `app/src/stores/` | Zustand stores | ✅ | | Minor | Add iteration history |
| `app/src/hooks/useIntent.ts` | Intent submission | ✅ | | | |
| `app/src/services/WebSocketClient.ts` | Real-time updates | ✅ | | | |
| `app/src/components/chat/` | Chat interface | ✅ | | Minor | Show agent proposals |

---

## 1.2 Failure Mode Coverage Matrix

| # | Failure Mode | Current Coverage | Files Involved | Gap |
|:-:|:-------------|:-----------------|:---------------|:----|
| 1 | LLMs don't know physics | **Partial** | `core/parameter_bounds.py` | Only 5 params; no lookup tables |
| 2 | Feedback lacks magnitude | **None** | `kernel/validator.py`, `stability/intact_gm.py` | Returns pass/fail, not ∂GM/∂beam |
| 3 | Physics validation incomplete | **Partial** | `physics/resistance.py`, `stability/`, `analysis/seakeeping_predictor.py` | Seakeeping simplified; no structures |
| 4 | Empirical methods break | **Partial** | `physics/resistance.py` lines 113-115, 279-290 | `method_valid` exists but not exposed |
| 5 | Multi-agent non-convergence | **None** | — | No iteration memory, no oscillation detection |
| 6 | Sections can't express all | **Partial** | `hull_gen/geometry.py`, `hull_gen/nurbs.py` | No multi-body composition |
| 7 | LLMs can't do NURBS | **Critical Gap** | `hull_gen/nurbs.py` | No semantic intent layer |
| 8 | Cold start no anchor | **Partial** | `kernel/priors/hull_families.py` | Uses type classification (bad) |
| 9 | Manufacturing constraints | **Partial** | `hull_gen/nurbs.py` lines 439-486 | `gaussian_curvature()` exists but unused |
| 10 | Physics ≠ Quality | **None** | — | No quality metrics |

---

## 1.3 DELETE Candidates

```
DELETE: magnet/kernel/priors/hull_families.py
REASON: enumeration
DETAILS: Contains HullFamily enum with values:
  - PATROL
  - WORKBOAT  
  - FERRY
  - PLANING
  - CATAMARAN
  
This directly violates "kernel knows geometry, not design" principle.
REPLACEMENT: Physics-derived bootstrapping using:
  - Froude number → draft/beam relationship
  - Displacement → principal dimensions
  - Speed requirement → L/B ratio
```

```
CONSIDER MODIFY: magnet/hull_gen/enums.py (lines 12-20)
REASON: HullType enum limits novelty
DETAILS: class HullType(Enum):
    DEEP_V_PLANING = "deep_v_planing"
    SEMI_DISPLACEMENT = "semi_displacement"
    ROUND_BILGE = "round_bilge"
    HARD_CHINE = "hard_chine"
    CATAMARAN = "catamaran"
    TRIMARAN = "trimaran"
    SWATH = "swath"
    
MODIFICATION: Either delete and use geometry properties, or treat as 
              agent suggestion that kernel ignores for validation.
```

---

## 1.4 REUSE Candidates

```
REUSE: magnet/hull_gen/geometry.py
CONFIDENCE: High
MODIFICATIONS NEEDED: None
NOTES: This is the CANONICAL geometry model. All primitives (geometry.section, 
       geometry.surface, geometry.body) MUST compile to these classes.
       Contains: Point3D, SectionPoint, HullSection, Waterline, Buttock, 
       LongitudinalFeature, HullGeometry
```

```
REUSE: magnet/hull_gen/nurbs.py
CONFIDENCE: High
MODIFICATIONS NEEDED: Minor (expose gaussian_curvature to agents)
NOTES: Full NURBS implementation with:
       - NURBSCurve: evaluate, derivative, curvature, arc_length
       - NURBSSurface: evaluate, normal, gaussian_curvature (lines 439-486)
       gaussian_curvature() can be used for developability validation.
```

```
REUSE: magnet/physics/resistance.py
CONFIDENCE: High
MODIFICATIONS NEEDED: Minor (surface validity_note to agent feedback)
NOTES: Already has:
       - method_valid: bool (line 114)
       - validity_note: str (line 115)
       - regime classification by Froude number (lines 279-290)
       Just needs to expose these to agent feedback.
```

```
REUSE: magnet/optimization/sensitivity.py
CONFIDENCE: High
MODIFICATIONS NEEDED: Minor (connect to validation feedback)
NOTES: Already computes:
       - ∂objective/∂variable (central difference, lines 127-131)
       - Variable importance (normalized, lines 176-191)
       This IS the quantified feedback infrastructure.
```

```
REUSE: magnet/stability/intact_gm.py
CONFIDENCE: High
MODIFICATIONS NEEDED: Minor (return sensitivity to inputs)
NOTES: Clean physics implementation. GM = KB + BM - KG - FSC
       Could add: ∂GM/∂beam, ∂GM/∂draft, ∂GM/∂KG easily.
```

---

## 1.5 Implementation Plan by Failure Mode

### Failure Mode 2: Feedback Lacks Magnitude

**Current State:**
- Validation returns pass/fail
- `sensitivity.py` computes gradients but isn't connected to feedback
- `resistance.py` has `validity_note` but not magnitude suggestions

**Files to Modify:**
- `kernel/validator.py`: Add `QuantifiedFeedback` to validation result
- `stability/intact_gm.py`: Add `sensitivity_to_beam()`, `sensitivity_to_draft()` methods
- `physics/resistance.py`: Expose `validity_note` in structured feedback

**New Files to Create:**
- `kernel/feedback/quantified_feedback.py`:

```python
@dataclass
class QuantifiedFeedback:
    """Feedback with magnitude and direction for engineer iteration."""
    metric_name: str           # e.g., "GM"
    current_value: float       # e.g., 0.45
    target_value: float        # e.g., 0.80
    gap: float                 # e.g., -0.35
    suggested_changes: List[SuggestedChange]
    
@dataclass
class SuggestedChange:
    parameter: str             # e.g., "hull.beam"
    current_value: float       # e.g., 6.5
    suggested_delta: float     # e.g., +0.4
    sensitivity: float         # ∂GM/∂beam
    confidence: str            # "high" | "medium" | "low"
```

**Integration Points:**
- `validation.py` → `QuantifiedFeedback` in response
- API response includes `suggested_changes` array
- UI shows: "GM too low (0.45m vs 0.80m). Try increasing beam by ~40cm."

**Estimated Effort:** Medium (2-3 days)

**Test Criteria:**
- Validation failure includes quantified gap
- At least one suggested change per failed metric
- Suggested change magnitude is correct order of magnitude

---

### Failure Mode 4: Empirical Methods Break on Novel Forms

**Current State:**
- `physics/resistance.py` already has `method_valid` and `validity_note` (lines 113-115, 279-290)
- Not exposed to agents

**Files to Modify:**
- `physics/resistance.py` lines 279-290: Already has regime classification:

```python
# EXISTING CODE (lines 279-290):
if froude_number < FN_HOLTROP_VALID_MAX:
    regime = "displacement"
    method_valid = True
    validity_note = "Holtrop-Mennen method valid for displacement regime"
elif froude_number < FN_HOLTROP_USABLE_MAX:
    regime = "semi_displacement"
    method_valid = False
    validity_note = "Semi-displacement regime: Holtrop results approximate (±20-30%)"
else:
    regime = "planing"
    method_valid = False
    validity_note = "Planing regime: Holtrop invalid, Savitsky method required"
```

**New Files to Create:**
- `kernel/validation/validity_envelopes.py`:

```python
@dataclass
class ValidityEnvelope:
    """Defines where an empirical method is valid."""
    method_name: str
    parameters: Dict[str, Tuple[float, float]]  # param → (min, max)
    
RESISTANCE_ENVELOPES = {
    "holtrop_mennen": ValidityEnvelope(
        method_name="Holtrop-Mennen",
        parameters={
            "froude_number": (0.0, 0.45),
            "length_beam_ratio": (3.9, 9.5),
            "beam_draft_ratio": (2.1, 4.0),
        }
    ),
    "savitsky": ValidityEnvelope(
        method_name="Savitsky",
        parameters={
            "froude_number": (0.5, 3.0),
            "deadrise_deg": (10.0, 30.0),
        }
    ),
}

def check_validity(method: str, geometry: HullGeometry) -> ValidityResult:
    """Check if method is valid for this geometry."""
    envelope = RESISTANCE_ENVELOPES.get(method)
    # ... check geometry against envelope ...
```

**Estimated Effort:** Small (1 day)

**Test Criteria:**
- Novel geometry returns "outside validated regime" warning
- Warning includes specific parameters that are out of bounds
- Agent can proceed despite warning (guide, don't gate)

---

### Failure Mode 6: Sections Can't Express All Geometry (Multi-Body)

**Current State:**
- `HullGeometry` represents single body
- `HullGenerator._generate_catamaran_sections()` exists (line 225-272) but is hardcoded

**Files to Modify:**
- `hull_gen/geometry.py`: Add `BodyGeometry`, `Attachment` classes
- `hull_gen/generator.py`: Accept multi-body composition

**New Files to Create:**
- `kernel/stdlib/primitives/body.py`:

```python
@dataclass
class BodyGeometry:
    """Single physical body (hull, outrigger, foil, etc.)."""
    body_id: str
    body_type: str              # Freeform string (agent can invent)
    physics_category: str       # "submerged" | "surface_piercing" | "above_water"
    sections: List[HullSection]
    offset_from_origin: Point3D
    
@dataclass 
class Attachment:
    """Connection between two bodies."""
    parent_body_id: str
    child_body_id: str
    attachment_type: str        # "rigid" | "hinged" | "flexible"
    position_on_parent: Point3D
    position_on_child: Point3D
```

**Integration Points:**
- `SemanticExpander` compiles `CREATE geometry.body` → `BodyGeometry`
- `HullGenerator` iterates over bodies, generates each, combines
- Hydrostatics sums contributions from all submerged bodies

**Estimated Effort:** Large (3-5 days)

**Test Criteria:**
- Can compose catamaran from two `geometry.body` primitives
- Can compose trimaran from three `geometry.body` primitives
- Novel multi-hull configuration works without new code

---

### Failure Mode 7: LLMs Can't Do Precise NURBS

**Current State:**
- `nurbs.py` requires explicit control points
- No semantic intent layer

**Files to Modify:**
- `hull_gen/nurbs.py`: Add intent-based control point generation

**New Files to Create:**
- `kernel/stdlib/geometry_intent.py`:

```python
def interpret_bow_intent(
    intent: str,                      # "finer entry", "blunter", "wave-piercing"
    current_sections: List[HullSection],
    lwl: float,
) -> List[HullSection]:
    """
    Translate semantic bow intent to section modifications.
    
    The LLM says "finer entry" and we compute:
    - Reduce beam at forward sections
    - Adjust deadrise for sharper waterline
    - Modify entrance angle
    """
    if "finer" in intent.lower():
        # Reduce waterline half-angle by 15-20%
        for section in current_sections:
            if section.station > 0.85:  # Forward 15%
                # Narrow the beam
                for point in section.points:
                    point.position.y *= 0.85
                    
    elif "blunter" in intent.lower():
        # Increase waterline half-angle
        ...
        
    return current_sections
```

**Estimated Effort:** Medium (2-3 days)

**Test Criteria:**
- Agent says "finer bow entry" → kernel produces valid geometry
- Agent says "more rocker" → kernel adjusts keel profile
- No raw control points in agent output

---

### Failure Mode 8: Cold Start Has No Anchor

**Current State:**
- `kernel/priors/hull_families.py` uses `HullFamily` enum (must delete)
- No physics-derived bootstrapping

**Files to Modify:**
- `kernel/synthesis.py`: Replace family-based priors with physics-derived

**New Files to Create:**
- `kernel/synthesis/physics_bootstrap.py`:

```python
def bootstrap_from_requirements(
    displacement_mt: float,
    max_speed_kts: float,
    lwl_m: Optional[float] = None,
) -> Dict[str, float]:
    """
    Derive starting dimensions from physics, not hull type.
    
    Uses:
    - Froude number → operating regime → appropriate L/B
    - Displacement → volume → draft/beam relationship
    - Speed → resistance → required proportions
    """
    # If LWL not given, estimate from displacement
    if lwl_m is None:
        # Cube root scaling
        lwl_m = 5.0 * (displacement_mt ** 0.333)
    
    # Compute Froude number
    speed_ms = max_speed_kts * 0.514444
    fn = speed_ms / (9.81 * lwl_m) ** 0.5
    
    # Derive L/B from Froude (physics, not type)
    if fn < 0.35:  # Displacement
        lb_ratio = 6.0 + fn * 2.0  # 6.0-6.7
    elif fn < 0.55:  # Semi-displacement
        lb_ratio = 5.5 + (fn - 0.35) * 5.0  # 5.5-6.5
    else:  # Planing
        lb_ratio = 4.0 + (0.55 - fn) * 2.0  # 4.0-5.0
    
    beam = lwl_m / lb_ratio
    
    # Derive draft from displacement
    volume_m3 = displacement_mt * 1000 / 1025
    cb_estimate = 0.45  # Conservative start
    draft = volume_m3 / (lwl_m * beam * cb_estimate)
    
    return {
        "hull.lwl": lwl_m,
        "hull.beam": beam,
        "hull.draft": draft,
        "hull.depth": draft * 1.5,  # Freeboard
    }
```

**Estimated Effort:** Medium (1-2 days)

**Test Criteria:**
- Cold start with only displacement + speed produces valid geometry
- No `HullFamily` enum anywhere in code path
- Novel requirements (e.g., 500 MT @ 50 kts) produce reasonable starting point

---

## 1.6 Dependency Graph

```
[Delete hull_families.py] ──prerequisite-for──> [Cold Start Bootstrap]
                                                       │
                                                       ▼
[Parameter Bounds Extension] ──prerequisite-for──> [Bounded Hypothesis]
         │
         ▼
[Validity Envelopes] ─────────────────────────────────────────────┐
                                                                   │
[Sensitivity Analysis (exists)] ──connect-to──> [Quantified Feedback]
                                                       │
                                                       ▼
                                             [Agent Feedback Loop]
                                                       │
[Multi-Body Composition] ──prerequisite-for──> [Novel Hull Forms]
         │
         ▼
[Semantic Intent Layer] ──────────────────────────────────────────┘
```

---

## 1.7 Priority Ordering (Engineer-in-Loop)

| Priority | Phase | Items | Estimated Days |
|:---------|:------|:------|:---------------|
| **P0** | Foundation | Delete `hull_families.py`, Extend `parameter_bounds.py` | 2 |
| **P0** | Feedback | Connect `sensitivity.py` to validation, Add `QuantifiedFeedback` | 3 |
| **P1** | Validity | Surface `method_valid` to agents, Add validity envelopes | 2 |
| **P1** | Intent | Semantic intent layer for bow/stern/rocker | 3 |
| **P2** | Multi-Body | `geometry.body` + `geometry.attachment` primitives | 4 |

**Total: 14 working days**

---

# Part 2: System Integration Audit

## 2.1 Frontend / UI Layer

| Question | Answer | Files |
|:---------|:-------|:------|
| Framework | React 18 + TypeScript | `app/src/main.tsx` |
| User input | REST API + WebSocket | `app/src/services/`, `app/src/hooks/useIntent.ts` |
| Geometry visualization | WebGL (Three.js implied by mesh format) | `magnet/webgl/` |
| Real-time updates | WebSocket | `app/src/services/WebSocketClient.ts`, `deployment/websocket.py` |
| State management | Zustand stores | `app/src/stores/` |
| Parameter controls | Chat interface, clarification components | `app/src/components/chat/`, `clarification/` |
| Chat interface | Yes | `app/src/components/chat/ChatInput.tsx` |
| Design persistence | REST API → JSONL files | `storage/designs/` |
| Export options | GLB, OBJ | `magnet/webgl/`, `storage/exports/` |

### Integration Questions

| Question | Current State | Required Change |
|:---------|:--------------|:----------------|
| Where does user intent enter? | `POST /api/v1/designs/{id}/intent/preview` | Works, add agent decomposition |
| How do agent proposals appear? | Not shown | Add agent reasoning panel |
| Multiple alternatives side-by-side? | No | Add comparison view |
| Iteration history / undo? | `design_version` + snapshots | Works, add UI history panel |
| Physics feedback display | Pass/fail in chat | Add quantified feedback panel |
| Agent reasoning visibility | Hidden | Add optional expansion |

---

## 2.2 API / Backend Layer

| Question | Answer | Files |
|:---------|:-------|:------|
| Framework | FastAPI | `deployment/api.py` |
| LLM integration | `LLMClient` via DI | `agents/llm_client.py`, `deployment/api.py` lines 1162-1170 |
| Orchestrator | `Conductor` | `kernel/conductor.py` |
| Design state management | `StateManager` with transactions | `core/state_manager.py` |
| Session management | Design ID based | `deployment/api.py` |

### Current Endpoints

```
GET  /health                              → Health check
GET  /api/v1/designs                      → List designs
POST /api/v1/designs                      → Create design
GET  /api/v1/designs/{id}                 → Get design
PATCH /api/v1/designs/{id}                → Update value
POST /api/v1/designs/{id}/intent/preview  → Preview intent (LLM translation)
POST /api/v1/designs/{id}/actions         → Execute action plan
POST /api/v1/designs/{id}/phases/{phase}/run → Run phase
GET  /api/v1/designs/{id}/explain/{path}  → Query explanation
WS   /ws/{design_id}                      → Real-time updates
```

### New Endpoints Needed

| Endpoint | Purpose | Request Format | Response Format | Priority |
|:---------|:--------|:---------------|:----------------|:---------|
| `POST /api/v1/designs/{id}/program` | Submit design language program | `DesignProgram` JSON | `ExecutionResult` | P0 |
| `GET /api/v1/designs/{id}/feedback` | Get quantified feedback | — | `QuantifiedFeedback[]` | P0 |
| `GET /api/v1/designs/{id}/iterations` | Get iteration history | — | `Iteration[]` | P1 |
| `GET /api/v1/designs/{id}/validity` | Get method validity | — | `ValidityReport` | P1 |

---

## 2.3 Geometry Pipeline

```
[User Intent] → [LLM Translation] → [ActionPlan] → [Kernel Validation]
                                           │
                                           ▼
                                    [StateManager]
                                           │
                                           ▼
                                   [HullDefinition]
                                           │
                                           ▼
                                  [HullGenerator]
                                           │
                                           ▼
                                  [HullGeometry]
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    ▼                      ▼                      ▼
              [Tessellation]        [Hydrostatics]           [Export]
                    │                      │                      │
                    ▼                      ▼                      ▼
              [WebGL Mesh]          [Physics Feedback]     [STL/IGES/GLB]
```

### Integration Points for New Architecture

| Stage | Current | Change Needed |
|:------|:--------|:--------------|
| User Intent | Natural language → `ActionPlan` | Add agent swarm decomposition |
| Parameter → HullDefinition | Direct mapping | Add primitive compilation |
| HullDefinition → Sections | `HullGenerator.generate()` | Support `geometry.body` composition |
| Sections → HullGeometry | `_generate_sections()` | Support multi-body |
| HullGeometry → NURBS | Implicit | Add `geometry.surface` compilation |
| Geometry → Tessellation | `webgl/tessellation.py` | Already works |
| Geometry → Export | `webgl/export.py` | Already works |

---

## 2.4 Validation / Physics

| Calculation | Exists? | File | Returns What? | Quantified? |
|:------------|:--------|:-----|:--------------|:------------|
| Hydrostatics | ✅ | `hull_gen/geometry.py` `compute_volume()` | Volume, LCB, VCB | Values only |
| Stability (GM) | ✅ | `stability/intact_gm.py` | GM, passes_criterion, warnings | Pass/fail + margin |
| Resistance | ✅ | `physics/resistance.py` | Total/components, regime, method_valid | Has validity_note |
| Structural | ❌ | — | — | — |
| Seakeeping | ✅ Simplified | `analysis/seakeeping_predictor.py` | Roll/pitch periods, operability | Values only |
| Developability | ✅ Exists, unused | `hull_gen/nurbs.py` `gaussian_curvature()` | Curvature value | Not exposed |

### Latency Concerns

| Calculation | Estimated Latency | Interactive? |
|:------------|:------------------|:-------------|
| Hydrostatics | <50ms | ✅ Yes |
| GM calculation | <10ms | ✅ Yes |
| Resistance | <100ms | ✅ Yes |
| Seakeeping | <200ms | ✅ Yes |
| Full geometry generation | 200-500ms | ⚠️ Marginal |
| NURBS tessellation | 100-300ms | ✅ Yes |

---

## 2.5 State / Persistence

| Question | Answer | Files |
|:---------|:-------|:------|
| Design persistence | JSONL files | `storage/designs/*.jsonl` |
| Design schema | `DesignState` dataclass | `core/design_state.py` |
| Version history | `design_version` counter + snapshots | `core/state_manager.py` lines 417-418 |
| Undo/redo | `revert_to_version()` | `core/state_manager.py` lines 980-1005 |
| Iteration tracking | History array | `DesignState.history` |

### Schema Changes Needed

```python
# Current (simplified):
@dataclass
class DesignState:
    design_id: str
    design_version: int
    mission: MissionState
    hull: HullState
    ...

# Add for compositional primitives:
@dataclass 
class DesignState:
    ...
    # NEW: Resource-based storage
    resources: Dict[str, ResourceConfig]  # id → config
    bodies: Dict[str, BodyConfig]         # For multi-body
    attachments: Dict[str, AttachmentConfig]
    
    # NEW: Iteration tracking
    iteration_history: List[IterationRecord]
```

---

## 2.6 LLM Integration

| Question | Answer | Files |
|:---------|:-------|:------|
| LLM provider | Configurable (Claude, GPT-4) | `llm/providers/` |
| API call | `LLMClient.complete_json()` | `agents/llm_client.py` |
| Prompt structure | System prompt with REFINABLE_SCHEMA | `deployment/api.py` lines 371-510 |
| Output format | Pydantic model (`LLMProposals`) | `deployment/api.py` lines 113-128 |
| Streaming | Yes (via provider) | `llm/providers/` |
| Error handling | Try/except with fallback | `deployment/api.py` lines 620-656 |
| System prompt location | Inline in `_build_translator_system_prompt()` | `deployment/api.py` |

### Integration Questions

| Question | Current | Change |
|:---------|:--------|:-------|
| LLM output → agent output? | LLM IS the agent | Add swarm coordination |
| Multiple LLM calls? | Single call | Add per-agent calls |
| Type registry in prompts? | REFINABLE_SCHEMA | Add geometry.* types |
| Structured reasoning? | Natural language | Add reasoning template |

---

## 2.7 New UI Components Needed

| Component | Purpose | Priority |
|:----------|:--------|:---------|
| Quantified Feedback Panel | Show "GM = 0.45m, need 0.80m, increase beam ~40cm" | P0 |
| Iteration History | Show design evolution, allow revert | P1 |
| Validity Warnings | Show "Savitsky doesn't apply at Fn=0.3" | P1 |
| Agent Reasoning Panel | Show what each agent proposed (optional) | P2 |
| Multi-Design Comparison | Compare alternatives side-by-side | P2 |

---

## 2.8 Keep / Modify / Delete / Build Matrix

### KEEP (No Changes)

| Component | Reason |
|:----------|:-------|
| `hull_gen/geometry.py` | Canonical geometry model |
| `hull_gen/nurbs.py` | Full NURBS implementation |
| `stability/intact_gm.py` | Clean physics |
| `optimization/sensitivity.py` | Gradient computation |
| `deployment/websocket.py` | Real-time works |
| `core/state_manager.py` | Transactions work |

### MODIFY

| Component | Current State | Required Changes |
|:----------|:--------------|:-----------------|
| `kernel/validator.py` | Returns pass/fail | Add `QuantifiedFeedback` |
| `physics/resistance.py` | Has `method_valid` internal | Expose to agent feedback |
| `hull_gen/generator.py` | Uses `HullType` enum | Support primitive composition |
| `deployment/api.py` | Single LLM call | Add `/program` endpoint |
| `core/parameter_bounds.py` | Only 5 params | Expand to 30+ params |

### DELETE

| Component | Reason | Replacement |
|:----------|:-------|:------------|
| `kernel/priors/hull_families.py` | `HullFamily` enum | Physics-derived bootstrap |

### BUILD NEW

| Component | Purpose | Dependencies |
|:----------|:--------|:-------------|
| `kernel/feedback/quantified_feedback.py` | Structured feedback with magnitudes | `sensitivity.py` |
| `kernel/validation/validity_envelopes.py` | Method applicability checks | `resistance.py` |
| `kernel/synthesis/physics_bootstrap.py` | Physics-derived cold start | None |
| `kernel/stdlib/geometry_intent.py` | Semantic → control points | `nurbs.py` |
| `kernel/stdlib/primitives/body.py` | Multi-body composition | `geometry.py` |

---

## 2.9 Risk Register

### Performance Risks

| Risk | Likelihood | Mitigation |
|:-----|:-----------|:-----------|
| Agent calls slow iteration | Medium | Cache proposals, stream updates |
| Physics validation too slow | Low | Already <100ms each |
| UI becomes unresponsive | Low | Async validation, optimistic updates |

### User Experience Risks

| Risk | Impact | Mitigation |
|:-----|:-------|:-----------|
| Too much agent "magic" | High | Show reasoning on demand, not by default |
| Too verbose | Medium | Collapse details, show summary first |
| Iteration feels slower | Medium | Instant geometry preview, async physics |

### Breaking Changes

| Feature | Why It Breaks | Migration Path |
|:--------|:--------------|:---------------|
| `HullType` enum removal | Existing designs reference types | Treat as freeform strings |
| Multi-body storage | New schema fields | Migration script for old designs |
| `DesignProgram` format | New input format | Keep ActionPlan as fallback |

---

## 2.10 Recommended Implementation Order

```
Week 1 (Foundation):
├── DELETE kernel/priors/hull_families.py
├── EXTEND core/parameter_bounds.py (30+ params)
├── CREATE kernel/feedback/quantified_feedback.py
└── CONNECT sensitivity.py → validation feedback

Week 2 (Validity + Intent):
├── CREATE kernel/validation/validity_envelopes.py
├── EXPOSE method_valid in physics/resistance.py
├── CREATE kernel/stdlib/geometry_intent.py
└── ADD /program endpoint to deployment/api.py

Week 3 (Multi-Body):
├── CREATE kernel/stdlib/primitives/body.py
├── MODIFY hull_gen/generator.py for composition
├── UPDATE hydrostatics for multi-body
└── ADD iteration history storage

Week 4 (UI + Polish):
├── ADD Quantified Feedback Panel
├── ADD Iteration History view
├── ADD Validity Warnings display
└── INTEGRATE with existing chat UI
```

---

## Related Documents

| Document | Purpose |
|:---------|:--------|
| `MAGNET_Design_Language_Spec_v1.0.md` | Complete language specification with primitives, invariants, and examples |
| `MAGNET_Unified_Implementation_Plan.md` | Multi-agent swarm architecture and full implementation roadmap |
| `MAGNET_Failure_Modes_And_Mitigations.md` | Implementation plan prioritized for engineer-in-loop workflow |
| `MAGNET_Implementation_Spec.md` | **Unified spec:** Agent prompts, API contracts, test plan, migration |
| `MAGNET_Physics_Gaps_And_Solutions.md` | **CRITICAL:** Multi-body hydrostatics, resistance method selection, form coefficient derivation |
| `MAGNET_Implementation_Guide.md` | **START HERE:** Step-by-step implementation roadmap with code |

---

## Version History

| Version | Date | Changes |
|:--------|:-----|:--------|
| 1.0 | 2026-01-05 | Complete audit with actual codebase findings. Converted from prompt storage to executed audit results. |
| 1.1 | 2026-01-05 | Added references to new implementation documents. |
