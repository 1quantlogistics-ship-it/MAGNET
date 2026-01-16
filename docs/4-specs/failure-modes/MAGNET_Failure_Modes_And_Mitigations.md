# MAGNET Implementation Plan: Engineer Creativity Amplifier

**Version:** 4.0  
**Date:** 2026-01-05  
**Status:** Implementation Specification  
**Alignment:** MAGNET_Design_Language_Spec_v1.0.md, MAGNET_Unified_Implementation_Plan.md

---

## What MAGNET Is

```
┌─────────────────────────────────────────────────────────────────┐
│                         ENGINEER                                │
│     (infinite creativity, domain knowledge, quality judgment)   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
                    "Make the bow finer"
                    "Try a stepped configuration"
                    "What if we added outriggers?"
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT SWARM                                │
│          (translates intent → geometry primitives)              │
│          (proposes options, not decisions)                      │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         KERNEL                                  │
│              (validates physics, returns feedback)              │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
                    Results + tradeoffs
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         ENGINEER                                │
│                   (judges, refines, iterates)                   │
└─────────────────────────────────────────────────────────────────┘
```

**MAGNET is not:** AI that designs boats autonomously

**MAGNET is:** A design environment where engineers express creative intent, agents translate to geometry, the kernel validates physics instantly, and the loop iterates as fast as the engineer can think

> **Any hull form that requires a new language primitive is a failure of the language.**

**Agent Coordination Rule:** Agents never coordinate on "features" — they coordinate on **geometry and constraints only**.

---

## The Core Equation

```
ENGINEER PRODUCTIVITY = creative expression × instant feedback × no artificial limits
```

| Term | What Enables It | What Blocks It |
|:-----|:----------------|:---------------|
| **Creative expression** | Compositional primitives | Enumerated hull types |
| **Instant feedback** | Fast kernel validation | Batch processing, slow physics |
| **No artificial limits** | Geometry-first design | Preset families, style catalogs |

---

## Failure Mode Reassessment

With an engineer in the loop, many failure modes simplify dramatically:

### Now Non-Critical (Engineer Handles)

| Failure Mode | Autonomous System | Engineer-in-Loop |
|:-------------|:------------------|:-----------------|
| LLMs don't know physics | **Critical** — must mitigate | **Reduced** — engineer catches nonsense |
| Multi-agent non-convergence | **Critical** — system hangs | **Non-issue** — engineer decides when to stop |
| Physics ≠ Quality | **Critical** — garbage designs | **Non-issue** — engineer judges quality |
| Cold start no anchor | **Critical** — where to begin? | **Non-issue** — engineer provides intent |

### Still Critical (System Must Handle)

| Failure Mode | Why It Still Matters |
|:-------------|:---------------------|
| **Kernel validates physics** | Engineers shouldn't wait for real-world failure to learn GM is negative |
| **Quantified feedback** | Engineers want numbers ("GM = 0.6, need 0.8, increase beam ~15cm") not just "failed" |
| **No type enumeration** | Engineers' creativity shouldn't be bounded by preset hull families |
| **Compositional primitives** | Engineers should be able to express *anything* |
| **Empirical method validity** | System should warn "Savitsky doesn't apply here" rather than return garbage |
| **Fast iteration** | Engineers need instant feedback, not batch jobs |

---

## Revised Priority Matrix

| Priority | What | Why | Effort |
|:---------|:-----|:----|:-------|
| **P0** | Semantic intent → geometry compilation | Engineers can't wait for agents to learn NURBS | 3-4 days |
| **P0** | Quantified validation feedback | "GM = 0.6, need 0.8" not just "failed" | 2-3 days |
| **P0** | Delete hull type enumerations | Unblock engineer creativity NOW | 1 day |
| **P1** | Fast kernel validation | <1s feedback for iteration speed | 2-3 days |
| **P1** | Validity envelope warnings | "Savitsky doesn't apply" not garbage numbers | 1-2 days |
| **P2** | Multi-body composition | Catamarans, trimarans from primitives | 3-4 days |
| **P2** | Manufacturing feedback | Soft developability warnings | 1-2 days |
| **Deprioritized** | Exploration memory | Engineer decides convergence | — |
| **Deprioritized** | Autonomous bootstrapping | Engineer provides intent | — |
| **Deprioritized** | Quality metrics | Engineer judges quality | — |

**Revised Total: 14-19 days (3-4 weeks)**

---

## Implementation Plan

### Phase 1: Unblock Engineer Creativity (Days 1-5)

**Goal:** Engineers can express anything, agents translate to geometry.

---

#### 1.1 Delete Hull Type Enumerations (Day 1)

**What:** Remove anything that constrains engineers to predefined hull families.

**DELETE:**
```
magnet/kernel/priors/hull_families.py
├── HullFamily enum (PATROL, WORKBOAT, FERRY, PLANING, CATAMARAN)
└── FAMILY_PRIORS dict
```

**DEPRECATE (mark for agent non-use):**
```
magnet/hull_gen/enums.py
├── HullType enum
├── BowStyle enum  
├── ChineType enum
└── SectionShape enum
```

**MODIFY:** Remove `hull_type` parameter from:
- `magnet/physics/hydrostatics.py` (lines 211, 317-398)
- `magnet/hull_gen/generator.py` (line 139)
- `magnet/kernel/synthesis.py` (line 48)

**Test:**
```python
def test_no_type_classification():
    """System works without hull type classification."""
    # These greps should return nothing in kernel/
    assert grep("HullFamily", "magnet/kernel/") == []
    assert grep("hull_type ==", "magnet/kernel/") == []
    assert grep("patrol", "magnet/kernel/", case_insensitive=True) == []
```

---

#### 1.2 Semantic Intent → Geometry Compilation (Days 2-4)

**What:** Engineers say "finer bow", agents translate to geometry primitives, kernel compiles to canonical geometry.

**File:** `magnet/kernel/stdlib/section_compiler.py`

```python
"""
Semantic Intent → Canonical Geometry

Engineer says: "Make the bow finer"
Agent outputs: CREATE geometry.section bow { half_beam_m: 0.4, deadrise_deg: 30, fullness: 0.3 }
Kernel compiles: HullSection with precise points

The engineer NEVER sees control points.
The agent NEVER hallucinates NURBS.
"""

from magnet.hull_gen.geometry import HullSection, SectionPoint, Point3D
import math


def compile_section(params: dict) -> HullSection:
    """
    Compile semantic section to canonical HullSection.
    
    Args:
        params: {
            "station": 0.0-1.0,          # Position along hull
            "half_beam_m": float,        # Half-beam at waterline
            "draft_m": float,            # Draft
            "deadrise_deg": float,       # Deadrise angle
            "fullness": 0.0-1.0,         # Section fullness (0=fine, 1=full)
        }
    
    Returns:
        HullSection (canonical geometry)
    """
    station = params.get("station", 0.5)
    x_pos = params.get("x_position_m", station * 15)  # Default 15m hull
    half_beam = params.get("half_beam_m", 1.0)
    draft = params.get("draft_m", 0.5)
    deadrise = math.radians(params.get("deadrise_deg", 15))
    fullness = params.get("fullness", 0.6)
    
    # Generate section points from semantic parameters
    points = _generate_section_points(
        x_pos, half_beam, draft, deadrise, fullness
    )
    
    return HullSection(
        station=station,
        x_position=x_pos,
        points=points,
        half_beam=half_beam,
        draft_local=draft,
        deadrise_deg=math.degrees(deadrise),
    )


def _generate_section_points(
    x: float,
    half_beam: float,
    draft: float,
    deadrise: float,
    fullness: float,
) -> list:
    """Generate section points from semantic parameters."""
    points = []
    
    # Keel
    points.append(SectionPoint(
        position=Point3D(x=x, y=0.0, z=-draft),
        is_keel=True,
    ))
    
    # Bottom panel (deadrise determines angle)
    flat_rise = draft * (0.5 + 0.2 * fullness)
    flat_run = flat_rise / math.tan(deadrise) if deadrise > 0.01 else half_beam * 0.4
    points.append(SectionPoint(
        position=Point3D(x=x, y=min(flat_run, half_beam * 0.8), z=-draft + flat_rise),
    ))
    
    # Chine (fullness affects how rounded)
    chine_y = half_beam * (0.6 + 0.3 * fullness)
    chine_z = -draft * 0.3 * (1 - fullness)
    points.append(SectionPoint(
        position=Point3D(x=x, y=chine_y, z=chine_z),
        is_chine=(fullness < 0.3),  # Hard chine for fine sections
    ))
    
    # Waterline
    points.append(SectionPoint(
        position=Point3D(x=x, y=half_beam, z=0.0),
    ))
    
    # Deck edge
    freeboard = draft * 0.4
    points.append(SectionPoint(
        position=Point3D(x=x, y=half_beam * 0.95, z=freeboard),
    ))
    
    return points


def compile_surface_from_sections(
    sections: list,
    params: dict,
) -> 'NURBSSurface':
    """
    Loft sections into NURBS surface.
    
    Engineer never sees this — it's internal to kernel.
    """
    from magnet.hull_gen.nurbs import NURBSSurface, Point3D as NPoint
    
    control_points = []
    for section in sections:
        row = [NPoint(p.position.x, p.position.y, p.position.z) 
               for p in section.points]
        control_points.append(row)
    
    surface = NURBSSurface(
        degree_u=3,
        degree_v=3,
        control_points=control_points,
    )
    surface.generate_uniform_knots()
    
    return surface
```

**Integration with Existing Pipeline:**

```python
# In deployment/api.py or kernel/action_executor.py

def execute_create_section(statement: dict, state: StateManager) -> dict:
    """Execute CREATE geometry.section statement."""
    from magnet.kernel.stdlib.section_compiler import compile_section
    
    params = statement["params"]
    resource_id = statement["as"]
    
    # Compile semantic intent to canonical geometry
    section = compile_section(params)
    
    # Store in state
    state.set(f"resources.sections.{resource_id}", section.to_dict(), "kernel")
    
    return {
        "success": True,
        "resource_id": resource_id,
        "geometry_created": True,
    }
```

---

#### 1.3 Bounds That Clip, Don't Reject (Day 5)

**What:** Soft guardrails that prevent hallucinated garbage without blocking creativity.

**File:** `magnet/core/parameter_bounds.py` (expand existing)

```python
"""
Soft Parameter Bounds

Engineer asks for deadrise_deg: 60 → clipped to 45 with warning
Engineer asks for deadrise_deg: 44 → proceeds unchanged (unusual but valid)

NEVER reject. Always proceed with clipped value.
"""

PARAMETER_BOUNDS = {
    # Principal dimensions
    "hull.lwl": (5, 200),
    "hull.beam": (1, 50),
    "hull.draft": (0.2, 15),
    
    # Form coefficients
    "hull.cb": (0.20, 0.90),
    "hull.cp": (0.45, 0.90),
    "hull.cm": (0.50, 0.995),
    
    # Hull form
    "hull.deadrise_deg": (0, 45),
    "hull.deadrise_transom_deg": (0, 35),
    "hull.bow_entrance_deg": (5, 60),
    "hull.bow_flare_deg": (0, 50),
    "hull.transom_beam_ratio": (0, 1.0),
    
    # Geometry primitives
    "geometry.section.half_beam_m": (0.1, 25),
    "geometry.section.draft_m": (0.1, 10),
    "geometry.section.deadrise_deg": (0, 45),
    "geometry.section.fullness": (0, 1),
    "geometry.discontinuity.depth_m": (0, 0.5),
    "geometry.body.offset_y_m": (-50, 50),
}


def clip_to_bounds(path: str, value: float) -> tuple:
    """
    Clip value to bounds. NEVER reject.
    
    Returns: (clipped_value, warning_or_none)
    """
    bounds = PARAMETER_BOUNDS.get(path)
    
    if bounds is None:
        return value, None  # Unknown param — allow it
    
    lo, hi = bounds
    
    if value < lo:
        return lo, f"{path}: {value} → {lo} (min)"
    if value > hi:
        return hi, f"{path}: {value} → {hi} (max)"
    
    return value, None
```

---

### Phase 2: Instant Quantified Feedback (Days 6-10)

**Goal:** Engineers get numbers, not just pass/fail.

---

#### 2.1 Quantified Validation Feedback (Days 6-8)

**What:** "GM = 0.6m, need 0.8m. Increase beam by ~15cm or reduce KG by ~0.2m."

**File:** `magnet/kernel/feedback/quantified_feedback.py`

```python
"""
Quantified Feedback for Engineers

Engineers want NUMBERS, not just "failed".
They want to know HOW MUCH to adjust.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class QuantifiedFeedback:
    """Actionable feedback with numbers."""
    parameter: str
    current_value: float
    required_value: float
    deficit: float
    
    # What to adjust and by how much
    suggested_adjustments: Dict[str, float]
    
    # Human-readable explanation
    explanation: str


# Pre-computed sensitivities (physics relationships)
SENSITIVITIES = {
    "stability.gm_m": {
        "hull.beam": 0.15,      # +15cm GM per +1m beam
        "stability.kg_m": -1.0, # -1m GM per +1m KG
        "hull.draft": -0.08,    # -8cm GM per +1m draft
    },
    "resistance.total_kn": {
        "hull.lwl": -0.05,      # Longer = less resistance
        "hull.beam": 0.02,      # Wider = more resistance
        "hull.cb": 0.10,        # Fuller = more resistance
    },
}


def generate_feedback(
    parameter: str,
    current: float,
    required: float,
) -> QuantifiedFeedback:
    """Generate quantified feedback for validation failure."""
    
    deficit = required - current
    sensitivities = SENSITIVITIES.get(parameter, {})
    
    # Find smallest adjustment that fixes deficit
    suggested = {}
    if sensitivities:
        # Pick the most effective adjustment
        best_param = max(sensitivities.keys(), key=lambda p: abs(sensitivities[p]))
        best_sens = sensitivities[best_param]
        if abs(best_sens) > 0.001:
            adjustment = deficit / best_sens
            suggested[best_param] = round(adjustment, 3)
    
    # Build explanation
    explanation = f"{parameter} = {current:.3f}, need {required:.3f}"
    if suggested:
        param, delta = list(suggested.items())[0]
        if delta > 0:
            explanation += f". Increase {param} by ~{abs(delta):.2f}"
        else:
            explanation += f". Decrease {param} by ~{abs(delta):.2f}"
    
    return QuantifiedFeedback(
        parameter=parameter,
        current_value=current,
        required_value=required,
        deficit=deficit,
        suggested_adjustments=suggested,
        explanation=explanation,
    )
```

**Integration with Existing Validators:**

```python
# Modify magnet/stability/validators.py

def validate_gm(state) -> ValidationResult:
    """Validate GM with quantified feedback for engineers."""
    from magnet.kernel.feedback.quantified_feedback import generate_feedback
    
    gm = state.get("stability.gm_m", 0)
    gm_min = 0.15
    
    result = ValidationResult(validator_id="stability/gm")
    
    if gm < gm_min:
        feedback = generate_feedback("stability.gm_m", gm, gm_min)
        
        result.add_finding(ValidationFinding(
            finding_id="gm-001",
            severity=ResultSeverity.ERROR,
            message=feedback.explanation,  # "GM = 0.12, need 0.15. Increase beam by ~0.20"
            current_value=gm,
            target_value=gm_min,
            suggested_adjustment=feedback.suggested_adjustments,
        ))
        result.state = ValidatorState.FAILED
    else:
        result.state = ValidatorState.PASSED
    
    return result
```

---

#### 2.2 Method Validity Warnings (Days 9-10)

**What:** "Savitsky method doesn't apply at this Froude number" — not garbage numbers.

**File:** `magnet/physics/validity_envelopes.py`

```python
"""
Empirical Method Validity Warnings

Don't return garbage when outside validity envelope.
WARN the engineer and let them decide.
"""

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class ValidityEnvelope:
    method: str
    parameters: Dict[str, Tuple[float, float]]
    source: str


HOLTROP_ENVELOPE = ValidityEnvelope(
    method="Holtrop-Mennen",
    parameters={
        "froude_number": (0.0, 0.55),
        "length_beam_ratio": (4.0, 8.0),
        "block_coefficient": (0.50, 0.85),
    },
    source="Series 60, BSRA model tests",
)

SAVITSKY_ENVELOPE = ValidityEnvelope(
    method="Savitsky",
    parameters={
        "froude_number": (1.0, 3.0),
        "length_beam_ratio": (2.5, 7.0),
        "deadrise_deg": (10, 30),
    },
    source="EMB Series 62/65 model tests",
)


def check_validity(
    method: str,
    values: Dict[str, float],
) -> Dict:
    """
    Check if method is valid for given values.
    
    Returns warning info — NEVER blocks.
    """
    envelopes = {
        "holtrop": HOLTROP_ENVELOPE,
        "savitsky": SAVITSKY_ENVELOPE,
    }
    
    envelope = envelopes.get(method.lower())
    if not envelope:
        return {"valid": True, "warnings": []}
    
    warnings = []
    for param, (lo, hi) in envelope.parameters.items():
        value = values.get(param, (lo + hi) / 2)
        if value < lo:
            warnings.append(f"{param}={value:.2f} below valid range [{lo}, {hi}]")
        elif value > hi:
            warnings.append(f"{param}={value:.2f} above valid range [{lo}, {hi}]")
    
    return {
        "valid": len(warnings) == 0,
        "method": envelope.method,
        "warnings": warnings,
        "note": f"Results may be unreliable" if warnings else "Within valid range",
        "source": envelope.source,
    }
```

**Integration with resistance.py:**

```python
# In magnet/physics/resistance.py, add to calculate():

validity = check_validity("holtrop", {
    "froude_number": froude_number,
    "length_beam_ratio": lwl / beam,
    "block_coefficient": cb,
})

# Include in results
return ResistanceResults(
    ...,
    method_valid=validity["valid"],
    validity_warnings=validity["warnings"],
    validity_note=validity["note"],
)
```

---

### Phase 3: Multi-Body Composition (Days 11-14)

**Goal:** Engineers can express catamarans, trimarans, novel configurations without "catamaran" type.

---

#### 3.1 Multi-Body Geometry (Days 11-14)

**What:** Add `HullBody` and `MultiBodyHull` to canonical geometry.

**File:** `magnet/hull_gen/geometry.py` (additions)

```python
# ADD to existing geometry.py

@dataclass
class HullBody:
    """
    A distinct solid volume in a multi-hull vessel.
    
    Enables: catamarans, trimarans, SWATH, novel configurations
    WITHOUT: "catamaran" type, "trimaran" type
    
    Engineer says: "Add two demihulls offset 3m from centerline"
    System creates: Two HullBody objects with offset_y_m = ±3.0
    """
    body_id: str
    
    # FREEFORM type — engineer can call it anything
    body_type: str = "hull"
    
    # Physics category — for hydrostatics treatment
    physics_category: str = "surface_piercing"  # or "submerged", "above_water"
    
    # Position
    offset_x_m: float = 0.0
    offset_y_m: float = 0.0
    offset_z_m: float = 0.0
    
    # Geometry (populated during compilation)
    sections: list = None
    surface: 'NURBSSurface' = None


@dataclass
class MultiBodyHull:
    """
    Complete vessel with multiple bodies.
    
    The kernel doesn't know this is a "catamaran".
    It just validates the combined geometry.
    """
    vessel_id: str
    bodies: Dict[str, HullBody] = None
    
    def __post_init__(self):
        if self.bodies is None:
            self.bodies = {}
    
    def add_body(self, body: HullBody):
        self.bodies[body.body_id] = body
    
    def get_combined_hydrostatics(self) -> dict:
        """
        Combine all bodies for hydrostatics calculation.
        
        Kernel validates THIS — not "catamaran rules".
        """
        combined_volume = 0.0
        combined_lcb_moment = 0.0
        combined_vcb_moment = 0.0
        
        for body in self.bodies.values():
            if body.physics_category == "submerged":
                # Fully submerged body
                vol = self._compute_body_volume(body)
                combined_volume += vol
            elif body.physics_category == "surface_piercing":
                # Normal hull - compute below waterline
                vol = self._compute_body_volume_below_wl(body)
                combined_volume += vol
        
        return {
            "total_volume_m3": combined_volume,
            "body_count": len(self.bodies),
        }
```

**Compilation from Design Language:**

```python
# In kernel/stdlib/body_compiler.py

def compile_body(statement: dict, resources: dict) -> HullBody:
    """
    Compile CREATE geometry.body statement.
    
    Example:
        CREATE geometry.body port_hull {
            body_type: "demihull",
            physics_category: "surface_piercing", 
            offset_y_m: -3.0
        }
    """
    params = statement["params"]
    body_id = statement["as"]
    
    return HullBody(
        body_id=body_id,
        body_type=params.get("body_type", "hull"),
        physics_category=params.get("physics_category", "surface_piercing"),
        offset_x_m=params.get("offset_x_m", 0.0),
        offset_y_m=params.get("offset_y_m", 0.0),
        offset_z_m=params.get("offset_z_m", 0.0),
    )
```

---

## Deprioritized Items (Engineer Handles)

These were critical for autonomous systems but are now handled by the engineer:

### Exploration Memory
**Autonomous:** Critical — system doesn't know when to stop  
**Engineer-in-loop:** Engineer decides "that's good enough" or "try something else"

### Physics-Derived Bootstrapping
**Autonomous:** Critical — system doesn't know where to start  
**Engineer-in-loop:** Engineer says "start with a 15m patrol boat going 35 knots"

### Quality Metrics
**Autonomous:** Critical — system produces valid garbage  
**Engineer-in-loop:** Engineer looks at result and says "that's ugly" or "that's elegant"

### Multi-Agent Convergence Detection
**Autonomous:** Critical — system oscillates forever  
**Engineer-in-loop:** Engineer sees two options and picks one

---

## Validation Checklist

Before any implementation is complete:

### Creativity Unblocked
- [ ] No `HullFamily` enum in codebase
- [ ] No `hull_type ==` comparisons in kernel
- [ ] No "patrol", "catamaran", "planing" strings in kernel
- [ ] Engineer can express any hull configuration from primitives

### Instant Feedback
- [ ] Validation returns quantified numbers, not just pass/fail
- [ ] Method validity warnings included in results
- [ ] Feedback includes suggested adjustments

### Fast Iteration
- [ ] Single validation cycle < 1 second
- [ ] No batch processing required
- [ ] Results available immediately after geometry change

---

## Acid Tests

### Test 1: Engineer Creates Catamaran from Primitives

```
Engineer: "I want a catamaran with 6m hull spacing"

Agent translates:
CREATE geometry.body port { body_type: "demihull", offset_y_m: -3.0 }
CREATE geometry.body stbd { body_type: "demihull", offset_y_m: 3.0 }
CREATE geometry.section bow { station: 0.0, half_beam_m: 0.5, deadrise_deg: 25 }
CREATE geometry.section mid { station: 0.5, half_beam_m: 0.8, deadrise_deg: 15 }
CREATE geometry.surface port_shell { body_id: "port", section_ids: ["bow", "mid"] }
MIRROR port_shell AS stbd_shell

Kernel validates:
✓ Combined displacement
✓ Stability (including hull spacing effect)
✓ Resistance

Engineer sees:
"Displacement: 12.5t, GM: 2.3m, Rt@30kts: 45kN"
```

**Pass criteria:** No "catamaran" anywhere in kernel logs.

### Test 2: Engineer Gets Quantified Feedback

```
Engineer: "Check stability"

Kernel returns:
{
  "parameter": "stability.gm_m",
  "current": 0.12,
  "required": 0.15,
  "deficit": 0.03,
  "explanation": "GM = 0.12m, need 0.15m. Increase beam by ~0.20m",
  "suggested_adjustments": {"hull.beam": 0.20}
}
```

**Pass criteria:** Engineer knows exactly what to change and by how much.

### Test 3: Engineer Warned About Method Validity

```
Engineer: "What's the resistance at 45 knots?"

Kernel returns:
{
  "resistance_kn": 85.2,
  "method_valid": false,
  "warnings": ["froude_number=1.8 above valid range [0.0, 0.55]"],
  "note": "Results may be unreliable. Holtrop-Mennen calibrated for Fn < 0.55."
}
```

**Pass criteria:** Engineer knows to be skeptical of the number.

---

## Timeline

| Phase | Days | What | Why |
|:------|:-----|:-----|:----|
| 1 | 1-5 | Unblock creativity | Engineers can express anything |
| 2 | 6-10 | Quantified feedback | Engineers know what to adjust |
| 3 | 11-14 | Multi-body composition | Catamarans, trimarans work |

**Total: 14 days (3 weeks)**

---

## Summary

| What We Build | What We Don't Build |
|:--------------|:--------------------|
| Fast iteration loop | Autonomous design |
| Compositional primitives | Hull type catalogs |
| Quantified physics feedback | AI quality judgment |
| Validity warnings | Auto-convergence |
| Arbitrary expression | Preset families |

**One Sentence:**

MAGNET ensures engineers can express **anything** (compositional primitives), get **instant physics feedback** (kernel validation), and never be constrained by **what someone enumerated** (no hull types) — while agents handle the tedious translation from intent to geometry.

---

## Related Documents

| Document | Purpose |
|:---------|:--------|
| `MAGNET_Design_Language_Spec_v1.0.md` | Complete language specification with primitives, invariants, and examples |
| `MAGNET_Unified_Implementation_Plan.md` | Multi-agent swarm architecture and full implementation roadmap |
| `MAGNET_Audit_Prompts.md` | Completed codebase audit with file inventory and implementation plan |
| `MAGNET_Implementation_Spec.md` | **Unified spec:** Agent prompts, API contracts, test plan, migration |
| `MAGNET_Physics_Gaps_And_Solutions.md` | **CRITICAL:** Concrete solutions for multi-body hydrostatics, resistance methods, novelty detection |
| `MAGNET_Implementation_Guide.md` | **START HERE:** Step-by-step implementation roadmap with code |
| `MAGNET_Audit_Prompts.md` | **Completed audit** with file inventory, failure mode coverage, and implementation plan |

---

## Audit Verification Summary

The following findings from `MAGNET_Audit_Prompts.md` v1.0 have been verified and integrated:

| Finding | Verified Location | Status |
|:--------|:------------------|:-------|
| `method_valid` exists in resistance | `physics/resistance.py` lines 113-115, 279-290 | ✅ Ready to expose |
| Gradients already computed | `optimization/sensitivity.py` lines 127-131 | ✅ Ready to connect |
| `gaussian_curvature()` for developability | `hull_gen/nurbs.py` lines 439-486 | ✅ Ready to use |
| `HullFamily` enum to delete | `kernel/priors/hull_families.py` | ✅ Marked for deletion |
| Multi-body not supported | `hull_gen/generator.py` | ⚠️ Needs implementation |
| Semantic intent layer missing | `hull_gen/nurbs.py` | ⚠️ Needs implementation |

---

## Version History

| Version | Date | Changes |
|:--------|:-----|:--------|
| 1.0 | 2026-01-05 | Initial failure mode analysis |
| 2.0 | 2026-01-05 | Codebase audit |
| 3.0 | 2026-01-05 | Concrete implementation plan |
| 4.0 | 2026-01-05 | **REFRAMED**: Engineer creativity amplifier, not autonomous system. Deprioritized convergence/bootstrap/quality (engineer handles). Focus on: expression freedom, quantified feedback, fast iteration. |
| 4.1 | 2026-01-05 | Added reference to `MAGNET_Audit_Prompts.md` in Related Documents. |
| 4.2 | 2026-01-05 | Aligned with `MAGNET_Audit_Prompts.md` v1.0 completed audit findings. Confirmed file locations and line numbers. |
