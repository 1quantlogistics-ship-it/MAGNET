# MAGNET Prompt Architecture Plan v2

**Status:** Active  
**Priority:** High  
**Goal:** Complete compositional operators + transparency + token efficiency

---

## The Equation

```
NOVELTY = continuous parameters × compositional operators × physics validation
```

**The Contract:**
- Agents propose pure geometric constructions
- Kernel compiles and validates physics
- Novel designs work without new code
- **Every transformation is observable and explainable**
- **Edits are either rejected, warned, or atomically committed—never half-applied**

---

## Problem Summary

| Issue | Impact |
|-------|--------|
| ~4000 tokens before user intent | No room for state/iteration |
| LOFT/MIRROR/ALIGN undocumented | Model reinvents compound ops |
| Compiler transforms silently | Model can't learn from feedback |
| Ambiguity → hallucination | Wrong guesses instead of questions |
| No BOOLEAN operations | Can't express tunnels, cutouts cleanly |
| No multi-body constraints | Can't enforce hull spacing |
| No fairness validation | Lumpy hulls pass quality gates |
| **No transaction semantics** | **Half-applied edits corrupt state** |
| **No explain/provenance** | **Can't answer "why did this happen?"** |
| **No iteration history** | **Can't prove design spiral** |

---

## Solution: Schema + Lens + Operators + Transparency

### The Schema (Static, ~300 tokens)

```json
{
  "primitives": {
    "geometry.body": {
      "required": ["body_id"],
      "optional": ["offset_x_m", "offset_y_m", "offset_z_m"]
    },
    "geometry.section": {
      "required": ["section_id", "body_id", "station", "points"],
      "optional": ["edge_types"],
      "rules": ["station: 0-1", "points: [[y,z],...] keel→deck", "z increasing", "y >= 0"]
    },
    "geometry.surface": {
      "required": ["surface_id", "body_id", "section_ids"],
      "rules": ["section_ids ordered bow→stern"]
    },
    "geometry.discontinuity": {
      "required": ["discontinuity_id", "body_id"],
      "optional": ["station_start", "station_end", "point_index", "depth_m"]
    },
    "geometry.attachment": {
      "required": ["id", "parent_body_id", "child_body_id"],
      "optional": ["offset_x_m", "offset_y_m", "offset_z_m"]
    }
  },
  "coords": {
    "x": "longitudinal, 0=bow, LOA=stern",
    "y": "lateral, 0=centerline, +port (mirrored automatically)",
    "z": "vertical, 0=waterline, +up",
    "station": "normalized x, 0=bow, 1=stern"
  },
  "ops": {
    "CREATE": "Create new resource",
    "UPDATE": "Modify existing resource",
    "DELETE": "Remove resource",
    "LOFT": "Create surface from ordered sections",
    "MIRROR": "Mirror body across centerline (creates symmetric copy)",
    "ALIGN": "Align resource to reference",
    "BOOLEAN": "Union, subtract, or intersect bodies"
  },
  "constraints": {
    "CONSTRAIN": "Set hard constraint: CONSTRAIN path op value",
    "SPACING": "Enforce distance between bodies: SPACING body_a body_b >= value",
    "CLEARANCE": "Enforce clearance above datum: CLEARANCE surface datum >= value"
  },
  "quality_defaults": {
    "note": "These are defaults. Use CONSTRAIN to override.",
    "sections": ">= 7 (denser at bow/transom)",
    "points_per_section": ">= 12",
    "points_must_match": true,
    "z_must_increase": true,
    "chine_index_consistent": true,
    "beam_progression_smooth": true,
    "deadrise_progression_smooth": true
  }
}
```

**Note:** Quality defaults are overridable via `CONSTRAIN sections >= 5` etc.

### The State Lens (Dynamic, ~250 tokens)

```json
{
  "version": 3,
  "parent_version": 2,
  "design": {
    "loa_m": 12.0,
    "beam_m": 3.5,
    "draft_m": 0.8
  },
  "bodies": ["main"],
  "sections": {
    "count": 7,
    "stations": [0.02, 0.15, 0.35, 0.50, 0.65, 0.80, 0.95],
    "points_per": 12,
    "chine_index": 4
  },
  "geometry": {
    "bow_beam_ratio": 0.23,
    "midship_beam_m": 3.5,
    "transom_beam_m": 3.2,
    "deadrise_transom_deg": 18
  },
  "surfaces": ["hull_main"],
  "constraints": [],
  "multi_body": {
    "count": 1,
    "spacing": null
  },
  "dependencies": {
    "hull_main": ["bow_01", "mid_01", "mid_02", "stern_01"]
  }
}
```

**Version tracking:** Every state has a version number and parent. Enables rollback.

**Dependencies:** Shows what invalidates when something changes.

---

## Transparency: Explain Traces

### Transform Provenance

Every compiler transformation is explained:

```json
{
  "transforms": [
    {
      "type": "upsample",
      "target": "bow_01.points",
      "from": 12,
      "to": 32,
      "why": "smooth_curves quality gate requires >= 32 points for curvature at bow",
      "rule": "quality_defaults.smooth_curves",
      "reversible": true
    },
    {
      "type": "mirror",
      "target": "hull_port",
      "source": "hull_stbd",
      "why": "MIRROR operation requested",
      "rule": "explicit_op",
      "reversible": true
    }
  ]
}
```

### Why Queries

The system can answer "why" questions:

```python
def explain_transform(transform_id: str) -> ExplainTrace:
    """Return full provenance for a transformation."""
    return ExplainTrace(
        what=transform.description,
        why=transform.rule,
        inputs=transform.dependencies,
        reversible=transform.reversible,
        alternatives=transform.alternatives  # What else could have been done
    )
```

### Validation Explain

Every validation result includes reasoning:

```json
{
  "validation": {
    "status": "fail",
    "checks": [
      {
        "check": "beam_progression",
        "status": "fail",
        "message": "Beam jumps 23% at station 0.35",
        "evidence": {
          "station_0.15_beam": 2.1,
          "station_0.35_beam": 2.8,
          "station_0.50_beam": 2.3,
          "deviation": 0.23
        },
        "suggestion": "Reduce beam at station 0.35 to ~2.2m"
      }
    ]
  }
}
```

---

## Transaction Semantics

### Atomic Commits

All operations are wrapped in transactions:

```json
{
  "transaction": {
    "id": "tx_abc123",
    "operations": [
      {"op": "CREATE", "target": "section_bow_03", "...": "..."},
      {"op": "UPDATE", "target": "surface_main", "...": "..."}
    ],
    "commit_mode": "atomic",
    "on_failure": "rollback"
  }
}
```

### Commit States

| State | Meaning |
|-------|---------|
| `committed` | All operations applied, state updated, version incremented |
| `rejected` | Validation failed, no changes applied, state unchanged |
| `warned` | Non-fatal issues, changes applied with warnings |
| `rolled_back` | Mid-transaction failure, all changes reverted |

### Implementation

```python
def execute_transaction(tx: Transaction, state: DesignState) -> TransactionResult:
    """Execute transaction with atomic semantics."""
    snapshot = state.snapshot()  # Copy current state
    
    try:
        for op in tx.operations:
            state = apply_operation(op, state)
        
        validation = validate_state(state)
        if validation.has_errors:
            state.restore(snapshot)
            return TransactionResult(
                status="rejected",
                reason=validation.errors,
                state_version=snapshot.version  # Unchanged
            )
        
        state.increment_version()
        return TransactionResult(
            status="committed" if not validation.has_warnings else "warned",
            warnings=validation.warnings,
            state_version=state.version
        )
    
    except Exception as e:
        state.restore(snapshot)
        return TransactionResult(
            status="rolled_back",
            reason=str(e),
            state_version=snapshot.version
        )
```

---

## Iteration History (v1.0 Minimal)

Design is a long-horizon computation. We must track iterations to prove the spiral.

### Minimal History (v1.0)

Store last N iterations (default: 5):

```json
{
  "iteration": {
    "current": 3,
    "history": [
      {
        "version": 1,
        "intent": "12m hull with fine entry",
        "result": "committed",
        "changes": ["created 7 sections", "lofted hull_main"]
      },
      {
        "version": 2,
        "intent": "Add hard chine",
        "result": "committed",
        "changes": ["updated edge_types on 7 sections"]
      },
      {
        "version": 3,
        "intent": "Increase beam to 4m",
        "result": "rejected",
        "reason": "beam_progression check failed at station 0.35"
      }
    ]
  }
}
```

### Injection into Prompt

```json
{
  "recent_iterations": [
    {"v": 2, "intent": "Add hard chine", "result": "ok"},
    {"v": 3, "intent": "Increase beam to 4m", "result": "rejected: beam jump at 0.35"}
  ]
}
```

This gives the model context about what was tried and why it failed.

---

## Intent + Feedback (Dynamic)

```json
{
  "intent": "Two symmetric hulls with 2.5m tunnel clearance",
  "iteration": 4,
  "recent_history": [
    {"v": 3, "intent": "Single hull", "result": "committed"}
  ],
  "last_result": {
    "status": "committed",
    "version": 3,
    "transforms": [
      {
        "type": "upsample",
        "target": "bow_01",
        "from": 12,
        "to": 32,
        "why": "smooth_curves quality gate"
      }
    ],
    "physics": {
      "floats": true,
      "gm_m": 0.65,
      "displacement_m3": 45.2
    },
    "quality": {
      "fairness": "pass",
      "chine_continuity": "pass"
    }
  }
}
```

### ASK Operation (Human-in-Loop)

```json
{
  "op": "ASK",
  "question": "Should the tunnel roof be flat or cambered?",
  "options": ["flat", "cambered_5deg", "cambered_10deg"],
  "default": "flat",
  "context": "Cambered roof improves structural strength but reduces clearance by ~0.1m"
}
```

**Triggers for ASK:**
- Ambiguous intent (multiple valid interpretations)
- Trade-off decision (can't optimize both)
- Outside validated parameter range

---

## New Compositional Operators

### BOOLEAN (Enables Tunnels, Complex Shapes)

```
BOOLEAN union body_a body_b → combined_body
BOOLEAN subtract body_main cutout_volume → body_with_hole
BOOLEAN intersect body_a body_b → intersection
```

**Use cases:**
- Prop tunnel: `BOOLEAN subtract hull tunnel_negative`
- Joined hulls: `BOOLEAN union hull_port cross_structure`

### SPACING Constraint (Enables Multi-Hull)

```
SPACING body_port body_stbd >= 2.5
```

**Enforces:** Minimum distance between body centerlines.

### CLEARANCE Constraint (Enables Tunnel Validation)

```
CLEARANCE tunnel_roof waterline >= 0.8
```

**Enforces:** Minimum vertical distance between surface and datum.

---

## Quality Gates (Longitudinal Fairness)

### Beam Progression

```python
def check_beam_progression(sections: List[Section]) -> QualityResult:
    """Beam should vary smoothly along length."""
    beams = [max(p[0] for p in s.points) for s in sections]
    for i in range(1, len(beams) - 1):
        local_avg = (beams[i-1] + beams[i+1]) / 2
        deviation = abs(beams[i] - local_avg) / local_avg
        if deviation > 0.15:  # 15% deviation = lumpy
            return QualityResult(
                status="fail",
                message=f"Beam jumps at station {sections[i].station}",
                evidence={"deviation": deviation, "station": sections[i].station},
                suggestion=f"Adjust beam to ~{local_avg:.2f}m"
            )
    return QualityResult(status="pass")
```

### Deadrise Progression

```python
def check_deadrise_progression(sections: List[Section]) -> QualityResult:
    """Deadrise should vary smoothly (no random spikes)."""
    deadrises = [compute_deadrise(s) for s in sections]
    for i in range(1, len(deadrises) - 1):
        local_avg = (deadrises[i-1] + deadrises[i+1]) / 2
        deviation = abs(deadrises[i] - local_avg)
        if deviation > 5:  # 5° deviation = unfair
            return QualityResult(
                status="fail",
                message=f"Deadrise jumps at station {sections[i].station}",
                evidence={"deviation_deg": deviation},
                suggestion=f"Adjust deadrise to ~{local_avg:.1f}°"
            )
    return QualityResult(status="pass")
```

### Chine Continuity

```python
def check_chine_continuity(sections: List[Section]) -> QualityResult:
    """Chine index should be consistent across sections."""
    chine_indices = [find_chine_index(s) for s in sections]
    if len(set(chine_indices)) > 1:
        return QualityResult(
            status="fail",
            message=f"Chine index varies: {chine_indices}",
            evidence={"indices": chine_indices},
            suggestion="Ensure chine is at same point index across all sections"
        )
    return QualityResult(status="pass")
```

---

## Token Budget

| Component | Before | After |
|-----------|--------|-------|
| Primitive schema | 500 | 150 |
| Operations (LOFT, MIRROR, ALIGN, BOOLEAN) | 0 | 80 |
| Constraints (SPACING, CLEARANCE) | 0 | 40 |
| Coordinates | 300 | 50 |
| Examples | 800 | 0 |
| Translation guides | 1200 | 0 |
| State lens (with version) | 1000 | 250 |
| Quality requirements | 0 | 80 |
| Iteration history (last 3) | 0 | 100 |
| **Total** | **~4200** | **~750** |

---

## Acceptance Tests (No Type Names)

| Test | Geometric Description | Pass Condition |
|------|----------------------|----------------|
| Token count | - | Base prompt < 800 tokens |
| BOOLEAN | Subtracted volume | `BOOLEAN subtract hull tunnel` produces valid mesh |
| SPACING | Two bodies with gap | Constraint validates distance >= specified |
| CLEARANCE | Surface above datum | Constraint validates height >= specified |
| Fairness | Smooth beam/deadrise | Lumpy hull fails quality check |
| Fine entry | bow_beam_ratio < 0.25, smooth flare | Compiles without "sportfish" |
| Twin symmetric | MIRROR + SPACING >= 2.5m | Compiles without "catamaran" |
| Shallow + tunnel | draft < 0.5m, BOOLEAN subtract | Compiles without "flats boat" |
| Round bilge | No edge_types, smooth sections | Compiles without "trawler" |
| Transaction | Multi-op change | Atomic commit or full rollback |
| Explain | Any transform | Returns why, rule, reversible |
| History | 3 iterations | Last 3 in prompt context |

---

## Implementation

| Step | Time | Deliverable |
|------|------|-------------|
| Create geometry_schema.json | 30 min | Schema with all ops |
| Create state_lens.py | 1 hour | Lens with version + dependencies |
| Add transaction wrapper | 1 hour | Atomic commit/rollback |
| Add explain traces | 1 hour | Provenance for transforms |
| Add iteration history | 30 min | Store/retrieve last N |
| Implement BOOLEAN | 2 hours | Boolean operations |
| Implement SPACING/CLEARANCE | 1 hour | Multi-body constraints |
| Implement quality gates | 1 hour | Fairness validation with suggestions |
| Update build_prompt() | 30 min | New prompt format |
| Test | 1.5 hours | All acceptance tests |

**Total: ~10.5 hours**

---

## Detailed Implementation Plan

### File Structure

```
magnet/
├── agents/
│   ├── geometry_proposer.py      # Update: use schema + lens
│   ├── geometry_schema.json      # NEW: static schema
│   └── state_lens.py             # NEW: state extraction
├── kernel/
│   ├── stdlib/
│   │   ├── parser.py             # Update: BOOLEAN, SPACING, CLEARANCE
│   │   ├── expander.py           # Update: constraint expansion
│   │   ├── compiler.py           # Update: transform provenance
│   │   ├── quality_gates.py      # NEW: fairness validation
│   │   └── transaction.py        # NEW: atomic execution
│   └── program_executor.py       # Update: transaction wrapper

tests/
├── prompt_architecture/          # NEW test directory
│   ├── __init__.py
│   ├── test_schema_validation.py
│   ├── test_state_lens.py
│   ├── test_transaction_atomicity.py
│   ├── test_explain_traces.py
│   ├── test_iteration_history.py
│   ├── test_quality_gates.py
│   └── test_compositional_ops.py
├── invariants/
│   ├── test_no_design_terms.py   # EXISTS: extend
│   ├── test_atomicity.py         # EXISTS: extend
│   └── test_transparency.py      # NEW: explain invariants
```

---

### Step 1: Create Schema File (30 min)

**File:** `magnet/agents/geometry_schema.json`

```json
{
  "version": "2.0",
  "primitives": {
    "geometry.body": {
      "required": ["body_id"],
      "optional": ["offset_x_m", "offset_y_m", "offset_z_m"]
    },
    "geometry.section": {
      "required": ["section_id", "body_id", "station", "points"],
      "optional": ["edge_types"],
      "rules": ["station: 0-1", "points: [[y,z],...] keel→deck", "z increasing", "y >= 0"]
    },
    "geometry.surface": {
      "required": ["surface_id", "body_id", "section_ids"],
      "rules": ["section_ids ordered bow→stern"]
    },
    "geometry.discontinuity": {
      "required": ["discontinuity_id", "body_id"],
      "optional": ["station_start", "station_end", "point_index", "depth_m"]
    },
    "geometry.attachment": {
      "required": ["id", "parent_body_id", "child_body_id"],
      "optional": ["offset_x_m", "offset_y_m", "offset_z_m"]
    }
  },
  "coords": {
    "x": "longitudinal, 0=bow, LOA=stern",
    "y": "lateral, 0=centerline, +port",
    "z": "vertical, 0=waterline, +up",
    "station": "normalized x, 0=bow, 1=stern"
  },
  "ops": {
    "CREATE": "Create new resource",
    "UPDATE": "Modify existing resource",
    "DELETE": "Remove resource",
    "LOFT": "Create surface from ordered sections",
    "MIRROR": "Mirror body across centerline",
    "ALIGN": "Align resource to reference",
    "BOOLEAN": "union|subtract|intersect bodies"
  },
  "constraints": {
    "CONSTRAIN": "CONSTRAIN path op value",
    "SPACING": "SPACING body_a body_b >= value",
    "CLEARANCE": "CLEARANCE surface datum >= value"
  },
  "quality_defaults": {
    "sections": ">= 7",
    "points_per_section": ">= 12",
    "points_must_match": true,
    "z_must_increase": true,
    "chine_index_consistent": true,
    "beam_progression_smooth": true,
    "deadrise_progression_smooth": true
  }
}
```

**Test:** `tests/prompt_architecture/test_schema_validation.py`

```python
"""
Test schema file is valid and parseable.
"""
import pytest
import json
from pathlib import Path


class TestSchemaValidation:
    """Test geometry schema file."""
    
    @pytest.fixture
    def schema(self):
        schema_path = Path(__file__).parent.parent.parent / "magnet/agents/geometry_schema.json"
        assert schema_path.exists(), f"Schema not found at {schema_path}"
        return json.loads(schema_path.read_text())
    
    def test_schema_has_required_sections(self, schema):
        """Schema must have all required top-level keys."""
        required = ["primitives", "coords", "ops", "constraints", "quality_defaults"]
        for key in required:
            assert key in schema, f"Missing required section: {key}"
    
    def test_all_primitives_have_required_field(self, schema):
        """Every primitive must specify required fields."""
        for name, defn in schema["primitives"].items():
            assert "required" in defn, f"{name} missing 'required' field"
    
    def test_no_hull_types_in_schema(self, schema):
        """Schema must not contain hull type enumerations."""
        schema_str = json.dumps(schema).lower()
        forbidden = ["catamaran", "monohull", "trimaran", "sportfish", "trawler", "skiff"]
        for term in forbidden:
            assert term not in schema_str, f"Forbidden term '{term}' in schema"
    
    def test_schema_token_count(self, schema):
        """Schema should be compact (< 400 tokens estimated)."""
        # Rough estimate: 4 chars per token
        schema_str = json.dumps(schema, separators=(',', ':'))
        estimated_tokens = len(schema_str) / 4
        assert estimated_tokens < 400, f"Schema too large: ~{estimated_tokens} tokens"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

### Step 2: Create State Lens (1 hour)

**File:** `magnet/agents/state_lens.py`

```python
"""
State lens for extracting compact state summaries.

The lens extracts derived facts from canonical state for LLM context.
"""
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import math


@dataclass
class StateLens:
    """Compact state summary for prompt injection."""
    version: int
    parent_version: Optional[int]
    design: Dict[str, float]
    bodies: List[str]
    sections: Dict[str, Any]
    geometry: Dict[str, float]
    surfaces: List[str]
    constraints: List[str]
    multi_body: Dict[str, Any]
    dependencies: Dict[str, List[str]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "parent_version": self.parent_version,
            "design": self.design,
            "bodies": self.bodies,
            "sections": self.sections,
            "geometry": self.geometry,
            "surfaces": self.surfaces,
            "constraints": self.constraints,
            "multi_body": self.multi_body,
            "dependencies": self.dependencies,
        }


def extract_state_lens(state: Dict[str, Any]) -> StateLens:
    """
    Extract compact state summary for LLM context.
    
    Args:
        state: Full design state dict
        
    Returns:
        StateLens with derived metrics
    """
    resources = state.get("resources", {})
    hull = state.get("hull", {})
    
    # Extract bodies
    bodies = [
        rid for rid, res in resources.items()
        if res.get("_type") == "geometry.body"
    ]
    
    # Extract sections
    sections = [
        res for res in resources.values()
        if res.get("_type") == "geometry.section"
    ]
    sections_sorted = sorted(sections, key=lambda s: s.get("station", 0))
    
    # Extract surfaces
    surfaces = [
        rid for rid, res in resources.items()
        if res.get("_type") == "geometry.surface"
    ]
    
    # Compute derived geometry metrics
    geometry = {}
    if sections_sorted:
        geometry["bow_beam_ratio"] = _compute_bow_beam_ratio(sections_sorted)
        geometry["midship_beam_m"] = _get_midship_beam(sections_sorted)
        geometry["transom_beam_m"] = _get_transom_beam(sections_sorted)
        if sections_sorted[-1].get("points"):
            geometry["deadrise_transom_deg"] = _compute_deadrise(sections_sorted[-1])
    
    # Build dependencies map
    dependencies = {}
    for rid, res in resources.items():
        if res.get("_type") == "geometry.surface":
            section_ids = res.get("section_ids", [])
            dependencies[rid] = section_ids
    
    return StateLens(
        version=state.get("_version", 1),
        parent_version=state.get("_parent_version"),
        design={
            "loa_m": hull.get("loa", 0),
            "beam_m": hull.get("beam", 0),
            "draft_m": hull.get("draft", 0),
        },
        bodies=bodies,
        sections={
            "count": len(sections_sorted),
            "stations": [s.get("station", 0) for s in sections_sorted],
            "points_per": len(sections_sorted[0].get("points", [])) if sections_sorted else 0,
            "chine_index": _find_chine_index(sections_sorted[0]) if sections_sorted else None,
        },
        geometry=geometry,
        surfaces=surfaces,
        constraints=list(state.get("constraints", {}).keys()),
        multi_body={
            "count": len(bodies) if bodies else 1,
            "spacing": _compute_body_spacing(resources, bodies) if len(bodies) > 1 else None,
        },
        dependencies=dependencies,
    )


def _compute_bow_beam_ratio(sections: List[Dict]) -> float:
    """Compute bow beam / midship beam ratio."""
    if len(sections) < 2:
        return 0.0
    bow_beam = _max_beam(sections[0])
    mid_idx = len(sections) // 2
    mid_beam = _max_beam(sections[mid_idx])
    return bow_beam / mid_beam if mid_beam > 0 else 0.0


def _max_beam(section: Dict) -> float:
    """Get maximum beam (y-coordinate) from section."""
    points = section.get("points", [])
    if not points:
        return 0.0
    return max(p[0] for p in points)


def _get_midship_beam(sections: List[Dict]) -> float:
    """Get beam at midship."""
    if not sections:
        return 0.0
    mid_idx = len(sections) // 2
    return _max_beam(sections[mid_idx])


def _get_transom_beam(sections: List[Dict]) -> float:
    """Get beam at transom (last section)."""
    if not sections:
        return 0.0
    return _max_beam(sections[-1])


def _compute_deadrise(section: Dict) -> float:
    """Compute deadrise angle from keel to first point."""
    points = section.get("points", [])
    if len(points) < 2:
        return 0.0
    # Deadrise is angle from horizontal at keel
    keel = points[0]
    next_point = points[1]
    dy = next_point[0] - keel[0]
    dz = next_point[1] - keel[1]
    if dy == 0:
        return 90.0
    return math.degrees(math.atan2(abs(dz), dy))


def _find_chine_index(section: Dict) -> Optional[int]:
    """Find chine point index (max curvature change)."""
    points = section.get("points", [])
    if len(points) < 3:
        return None
    # Simple: find point with largest angle change
    max_angle_change = 0
    chine_idx = None
    for i in range(1, len(points) - 1):
        # Compute angle change at this point
        prev = points[i-1]
        curr = points[i]
        next_pt = points[i+1]
        angle1 = math.atan2(curr[1] - prev[1], curr[0] - prev[0])
        angle2 = math.atan2(next_pt[1] - curr[1], next_pt[0] - curr[0])
        angle_change = abs(angle2 - angle1)
        if angle_change > max_angle_change:
            max_angle_change = angle_change
            chine_idx = i
    return chine_idx


def _compute_body_spacing(resources: Dict, bodies: List[str]) -> Optional[float]:
    """Compute spacing between bodies."""
    if len(bodies) < 2:
        return None
    offsets = []
    for body_id in bodies:
        body = resources.get(body_id, {})
        offset_y = body.get("offset_y_m", 0)
        offsets.append(offset_y)
    if len(offsets) >= 2:
        return abs(max(offsets) - min(offsets))
    return None
```

**Test:** `tests/prompt_architecture/test_state_lens.py`

```python
"""
Test state lens extraction.
"""
import pytest
from magnet.agents.state_lens import extract_state_lens, StateLens


class TestStateLens:
    """Test state lens extraction."""
    
    @pytest.fixture
    def sample_state(self):
        return {
            "_version": 3,
            "_parent_version": 2,
            "hull": {"loa": 12.0, "beam": 3.5, "draft": 0.8},
            "resources": {
                "main": {"_type": "geometry.body"},
                "bow_01": {
                    "_type": "geometry.section",
                    "station": 0.02,
                    "body_id": "main",
                    "points": [[0, 0], [0.5, -0.3], [1.0, -0.8], [0, -1.0]],
                },
                "mid_01": {
                    "_type": "geometry.section",
                    "station": 0.5,
                    "body_id": "main",
                    "points": [[0, 0], [1.5, -0.2], [1.75, -0.6], [0, -0.9]],
                },
                "stern_01": {
                    "_type": "geometry.section",
                    "station": 0.95,
                    "body_id": "main",
                    "points": [[0, 0], [1.4, -0.2], [1.6, -0.5], [0, -0.7]],
                },
                "hull_main": {
                    "_type": "geometry.surface",
                    "body_id": "main",
                    "section_ids": ["bow_01", "mid_01", "stern_01"],
                },
            },
        }
    
    def test_extracts_version(self, sample_state):
        """Lens extracts version info."""
        lens = extract_state_lens(sample_state)
        assert lens.version == 3
        assert lens.parent_version == 2
    
    def test_extracts_bodies(self, sample_state):
        """Lens extracts body IDs."""
        lens = extract_state_lens(sample_state)
        assert "main" in lens.bodies
    
    def test_extracts_section_summary(self, sample_state):
        """Lens extracts section summary."""
        lens = extract_state_lens(sample_state)
        assert lens.sections["count"] == 3
        assert len(lens.sections["stations"]) == 3
        assert lens.sections["points_per"] == 4
    
    def test_computes_bow_beam_ratio(self, sample_state):
        """Lens computes bow/midship beam ratio."""
        lens = extract_state_lens(sample_state)
        # bow max_beam = 1.0, mid max_beam = 1.75
        expected = 1.0 / 1.75
        assert abs(lens.geometry["bow_beam_ratio"] - expected) < 0.01
    
    def test_extracts_dependencies(self, sample_state):
        """Lens extracts surface → section dependencies."""
        lens = extract_state_lens(sample_state)
        assert "hull_main" in lens.dependencies
        assert lens.dependencies["hull_main"] == ["bow_01", "mid_01", "stern_01"]
    
    def test_to_dict_is_serializable(self, sample_state):
        """Lens output is JSON-serializable."""
        import json
        lens = extract_state_lens(sample_state)
        # Should not raise
        json_str = json.dumps(lens.to_dict())
        assert len(json_str) > 0
    
    def test_multi_body_spacing(self):
        """Lens computes multi-body spacing."""
        state = {
            "hull": {"loa": 20.0},
            "resources": {
                "port": {"_type": "geometry.body", "offset_y_m": -3.0},
                "stbd": {"_type": "geometry.body", "offset_y_m": 3.0},
            },
        }
        lens = extract_state_lens(state)
        assert lens.multi_body["count"] == 2
        assert lens.multi_body["spacing"] == 6.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

### Step 3: Transaction Wrapper (1 hour)

**File:** `magnet/kernel/stdlib/transaction.py`

```python
"""
Transaction wrapper for atomic execution.

INVARIANT: Program execution is atomic — all succeed or all fail.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
import copy


class TransactionStatus(Enum):
    PENDING = "pending"
    COMMITTED = "committed"
    REJECTED = "rejected"
    WARNED = "warned"
    ROLLED_BACK = "rolled_back"


@dataclass
class TransactionResult:
    """Result of transaction execution."""
    status: TransactionStatus
    state_version: int
    transforms: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    reason: Optional[str] = None


@dataclass
class Transaction:
    """Wraps operations for atomic execution."""
    id: str
    operations: List[Dict[str, Any]]
    
    def execute(self, state: Dict[str, Any], validators: List) -> TransactionResult:
        """
        Execute transaction with atomic semantics.
        
        If any operation or validation fails, rollback ALL changes.
        """
        # Snapshot current state
        snapshot = copy.deepcopy(state)
        original_version = state.get("_version", 0)
        transforms = []
        
        try:
            # Apply all operations
            for op in self.operations:
                result = self._apply_operation(op, state)
                if result.get("transform"):
                    transforms.append(result["transform"])
                if result.get("error"):
                    raise ValueError(result["error"])
            
            # Run validation
            warnings = []
            errors = []
            for validator in validators:
                vresult = validator(state)
                if vresult.get("warnings"):
                    warnings.extend(vresult["warnings"])
                if vresult.get("errors"):
                    errors.extend(vresult["errors"])
            
            if errors:
                # Rollback
                state.clear()
                state.update(snapshot)
                return TransactionResult(
                    status=TransactionStatus.REJECTED,
                    state_version=original_version,
                    transforms=transforms,
                    errors=errors,
                    reason="; ".join(errors),
                )
            
            # Commit: increment version
            state["_version"] = original_version + 1
            state["_parent_version"] = original_version
            
            return TransactionResult(
                status=TransactionStatus.WARNED if warnings else TransactionStatus.COMMITTED,
                state_version=state["_version"],
                transforms=transforms,
                warnings=warnings,
            )
        
        except Exception as e:
            # Rollback on any exception
            state.clear()
            state.update(snapshot)
            return TransactionResult(
                status=TransactionStatus.ROLLED_BACK,
                state_version=original_version,
                transforms=transforms,
                errors=[str(e)],
                reason=str(e),
            )
    
    def _apply_operation(self, op: Dict, state: Dict) -> Dict:
        """Apply a single operation. Returns transform info if any."""
        # Implementation depends on operation type
        op_type = op.get("op")
        if op_type == "CREATE":
            return self._apply_create(op, state)
        elif op_type == "UPDATE":
            return self._apply_update(op, state)
        elif op_type == "DELETE":
            return self._apply_delete(op, state)
        else:
            return {"error": f"Unknown operation: {op_type}"}
    
    def _apply_create(self, op: Dict, state: Dict) -> Dict:
        """Apply CREATE operation."""
        target = op.get("target")
        value = op.get("value", {})
        resources = state.setdefault("resources", {})
        if target in resources:
            return {"error": f"Resource already exists: {target}"}
        resources[target] = value
        return {"transform": {"type": "create", "target": target, "why": "explicit_op"}}
    
    def _apply_update(self, op: Dict, state: Dict) -> Dict:
        """Apply UPDATE operation."""
        target = op.get("target")
        value = op.get("value", {})
        resources = state.get("resources", {})
        if target not in resources:
            return {"error": f"Resource not found: {target}"}
        resources[target].update(value)
        return {"transform": {"type": "update", "target": target, "why": "explicit_op"}}
    
    def _apply_delete(self, op: Dict, state: Dict) -> Dict:
        """Apply DELETE operation."""
        target = op.get("target")
        resources = state.get("resources", {})
        if target not in resources:
            return {"error": f"Resource not found: {target}"}
        del resources[target]
        return {"transform": {"type": "delete", "target": target, "why": "explicit_op"}}
```

**Test:** `tests/prompt_architecture/test_transaction_atomicity.py`

```python
"""
Test transaction atomicity.

INVARIANT: Execution is all-or-nothing.
"""
import pytest
from magnet.kernel.stdlib.transaction import Transaction, TransactionStatus


class TestTransactionAtomicity:
    """Test atomic transaction execution."""
    
    def test_successful_transaction_commits(self):
        """Successful transaction increments version."""
        state = {"_version": 1, "resources": {}}
        tx = Transaction(
            id="tx_001",
            operations=[
                {"op": "CREATE", "target": "section_01", "value": {"_type": "geometry.section"}},
            ],
        )
        
        result = tx.execute(state, validators=[])
        
        assert result.status == TransactionStatus.COMMITTED
        assert state["_version"] == 2
        assert "section_01" in state["resources"]
    
    def test_failed_validation_rolls_back(self):
        """Failed validation rolls back all changes."""
        state = {"_version": 1, "resources": {}}
        
        def failing_validator(s):
            return {"errors": ["Validation failed"]}
        
        tx = Transaction(
            id="tx_002",
            operations=[
                {"op": "CREATE", "target": "section_01", "value": {"_type": "geometry.section"}},
            ],
        )
        
        result = tx.execute(state, validators=[failing_validator])
        
        assert result.status == TransactionStatus.REJECTED
        assert state["_version"] == 1  # Unchanged
        assert "section_01" not in state["resources"]  # Rolled back
    
    def test_partial_failure_rolls_back_all(self):
        """Partial execution failure rolls back ALL operations."""
        state = {"_version": 1, "resources": {"existing": {"_type": "geometry.body"}}}
        
        tx = Transaction(
            id="tx_003",
            operations=[
                {"op": "CREATE", "target": "new_section", "value": {}},
                {"op": "DELETE", "target": "nonexistent"},  # Will fail
            ],
        )
        
        result = tx.execute(state, validators=[])
        
        assert result.status == TransactionStatus.ROLLED_BACK
        assert "new_section" not in state["resources"]  # First op rolled back
    
    def test_warnings_still_commit(self):
        """Warnings don't prevent commit, but are reported."""
        state = {"_version": 1, "resources": {}}
        
        def warning_validator(s):
            return {"warnings": ["Minor issue"]}
        
        tx = Transaction(
            id="tx_004",
            operations=[
                {"op": "CREATE", "target": "section_01", "value": {}},
            ],
        )
        
        result = tx.execute(state, validators=[warning_validator])
        
        assert result.status == TransactionStatus.WARNED
        assert state["_version"] == 2  # Committed despite warning
        assert "Minor issue" in result.warnings
    
    def test_version_tracking(self):
        """Version and parent_version are tracked."""
        state = {"_version": 5, "resources": {}}
        
        tx = Transaction(id="tx_005", operations=[])
        result = tx.execute(state, validators=[])
        
        assert state["_version"] == 6
        assert state["_parent_version"] == 5


class TestTransactionTransforms:
    """Test transform tracking in transactions."""
    
    def test_transforms_recorded(self):
        """Transforms are recorded in result."""
        state = {"_version": 1, "resources": {}}
        
        tx = Transaction(
            id="tx_006",
            operations=[
                {"op": "CREATE", "target": "bow_01", "value": {"_type": "geometry.section"}},
                {"op": "CREATE", "target": "stern_01", "value": {"_type": "geometry.section"}},
            ],
        )
        
        result = tx.execute(state, validators=[])
        
        assert len(result.transforms) == 2
        assert result.transforms[0]["type"] == "create"
        assert result.transforms[0]["target"] == "bow_01"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

### Step 4: Explain Traces (1 hour)

**File:** `magnet/kernel/stdlib/explain.py`

```python
"""
Explain traces for transform provenance.

Every transformation must be observable and explainable.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class ExplainTrace:
    """Provenance for a transformation."""
    transform_id: str
    what: str
    why: str
    rule: str
    inputs: List[str] = field(default_factory=list)
    reversible: bool = True
    alternatives: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "transform_id": self.transform_id,
            "what": self.what,
            "why": self.why,
            "rule": self.rule,
            "inputs": self.inputs,
            "reversible": self.reversible,
            "alternatives": self.alternatives,
        }


class ExplainRegistry:
    """Registry for transform explanations."""
    
    def __init__(self):
        self._traces: Dict[str, ExplainTrace] = {}
    
    def record(self, trace: ExplainTrace) -> None:
        """Record a transform explanation."""
        self._traces[trace.transform_id] = trace
    
    def explain(self, transform_id: str) -> Optional[ExplainTrace]:
        """Get explanation for a transform."""
        return self._traces.get(transform_id)
    
    def explain_all(self) -> List[ExplainTrace]:
        """Get all recorded explanations."""
        return list(self._traces.values())
    
    def clear(self) -> None:
        """Clear all recorded explanations."""
        self._traces.clear()


# Standard rule explanations
RULE_EXPLANATIONS = {
    "explicit_op": "Operation explicitly requested in program",
    "quality_defaults.smooth_curves": "Smooth curves quality gate requires sufficient points",
    "quality_defaults.beam_progression": "Beam must vary smoothly along length",
    "quality_defaults.deadrise_progression": "Deadrise must vary smoothly along length",
    "quality_defaults.chine_continuity": "Chine must be at same point index across sections",
    "constraint.spacing": "SPACING constraint requires minimum distance between bodies",
    "constraint.clearance": "CLEARANCE constraint requires minimum height above datum",
}


def create_explain_trace(
    transform_type: str,
    target: str,
    rule: str,
    details: Dict[str, Any] = None,
) -> ExplainTrace:
    """Create an explain trace with standard explanations."""
    details = details or {}
    
    return ExplainTrace(
        transform_id=f"{transform_type}_{target}_{id(details) % 10000}",
        what=f"{transform_type} on {target}",
        why=RULE_EXPLANATIONS.get(rule, rule),
        rule=rule,
        inputs=details.get("inputs", []),
        reversible=details.get("reversible", True),
        alternatives=details.get("alternatives", []),
    )
```

**Test:** `tests/prompt_architecture/test_explain_traces.py`

```python
"""
Test explain trace functionality.
"""
import pytest
from magnet.kernel.stdlib.explain import (
    ExplainTrace, ExplainRegistry, create_explain_trace, RULE_EXPLANATIONS
)


class TestExplainTrace:
    """Test ExplainTrace dataclass."""
    
    def test_trace_to_dict(self):
        """Trace converts to dict."""
        trace = ExplainTrace(
            transform_id="upsample_bow_01_1234",
            what="upsample on bow_01.points",
            why="Smooth curves quality gate requires sufficient points",
            rule="quality_defaults.smooth_curves",
            inputs=["bow_01.points"],
            reversible=True,
        )
        
        d = trace.to_dict()
        
        assert d["transform_id"] == "upsample_bow_01_1234"
        assert d["why"] == "Smooth curves quality gate requires sufficient points"
        assert d["reversible"] is True


class TestExplainRegistry:
    """Test ExplainRegistry."""
    
    def test_record_and_explain(self):
        """Registry records and retrieves traces."""
        registry = ExplainRegistry()
        trace = ExplainTrace(
            transform_id="test_001",
            what="test transform",
            why="testing",
            rule="test_rule",
        )
        
        registry.record(trace)
        retrieved = registry.explain("test_001")
        
        assert retrieved is not None
        assert retrieved.what == "test transform"
    
    def test_explain_missing_returns_none(self):
        """Missing transform returns None."""
        registry = ExplainRegistry()
        assert registry.explain("nonexistent") is None
    
    def test_explain_all(self):
        """explain_all returns all traces."""
        registry = ExplainRegistry()
        registry.record(ExplainTrace("t1", "w1", "y1", "r1"))
        registry.record(ExplainTrace("t2", "w2", "y2", "r2"))
        
        all_traces = registry.explain_all()
        
        assert len(all_traces) == 2


class TestCreateExplainTrace:
    """Test explain trace factory."""
    
    def test_creates_with_standard_explanation(self):
        """Factory uses standard explanations."""
        trace = create_explain_trace(
            transform_type="upsample",
            target="bow_01",
            rule="quality_defaults.smooth_curves",
        )
        
        assert "smooth curves" in trace.why.lower()
    
    def test_unknown_rule_uses_rule_as_why(self):
        """Unknown rule uses rule string as explanation."""
        trace = create_explain_trace(
            transform_type="custom",
            target="section_01",
            rule="custom_rule_xyz",
        )
        
        assert trace.why == "custom_rule_xyz"


class TestRuleExplanations:
    """Test standard rule explanations."""
    
    def test_all_quality_rules_have_explanations(self):
        """All quality rules should have explanations."""
        quality_rules = [
            "quality_defaults.smooth_curves",
            "quality_defaults.beam_progression",
            "quality_defaults.deadrise_progression",
            "quality_defaults.chine_continuity",
        ]
        for rule in quality_rules:
            assert rule in RULE_EXPLANATIONS, f"Missing explanation for {rule}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

### Step 5: Iteration History (30 min)

**File:** `magnet/agents/iteration_history.py`

```python
"""
Iteration history for design spiral tracking.

Stores last N iterations for prompt context injection.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from collections import deque


@dataclass
class IterationRecord:
    """Record of a single iteration."""
    version: int
    intent: str
    result: str  # "committed", "rejected", "warned"
    changes: List[str] = field(default_factory=list)
    reason: Optional[str] = None
    
    def to_compact(self) -> Dict[str, Any]:
        """Compact format for prompt injection."""
        d = {"v": self.version, "intent": self.intent, "result": self.result}
        if self.reason:
            d["result"] = f"{self.result}: {self.reason}"
        return d


class IterationHistory:
    """Manages iteration history with bounded size."""
    
    def __init__(self, max_size: int = 5):
        self._history: deque = deque(maxlen=max_size)
        self._current_iteration: int = 0
    
    def record(self, intent: str, result: str, changes: List[str] = None, reason: str = None) -> None:
        """Record an iteration."""
        self._current_iteration += 1
        self._history.append(IterationRecord(
            version=self._current_iteration,
            intent=intent,
            result=result,
            changes=changes or [],
            reason=reason,
        ))
    
    def get_recent(self, n: int = 3) -> List[IterationRecord]:
        """Get last N iterations."""
        return list(self._history)[-n:]
    
    def get_compact_for_prompt(self, n: int = 3) -> List[Dict[str, Any]]:
        """Get compact format for prompt injection."""
        return [r.to_compact() for r in self.get_recent(n)]
    
    @property
    def current_iteration(self) -> int:
        return self._current_iteration
    
    def to_dict(self) -> Dict[str, Any]:
        """Full history as dict."""
        return {
            "current": self._current_iteration,
            "history": [
                {
                    "version": r.version,
                    "intent": r.intent,
                    "result": r.result,
                    "changes": r.changes,
                    "reason": r.reason,
                }
                for r in self._history
            ],
        }
```

**Test:** `tests/prompt_architecture/test_iteration_history.py`

```python
"""
Test iteration history tracking.
"""
import pytest
from magnet.agents.iteration_history import IterationHistory, IterationRecord


class TestIterationHistory:
    """Test iteration history."""
    
    def test_records_iterations(self):
        """History records iterations."""
        history = IterationHistory()
        history.record("Create 12m hull", "committed", ["created 7 sections"])
        history.record("Add chine", "committed", ["updated edge_types"])
        
        assert history.current_iteration == 2
        assert len(history.get_recent()) == 2
    
    def test_bounded_size(self):
        """History respects max_size."""
        history = IterationHistory(max_size=3)
        for i in range(5):
            history.record(f"Intent {i}", "committed")
        
        recent = history.get_recent(10)  # Ask for more than exists
        assert len(recent) == 3
        assert recent[0].version == 3  # Oldest in bounded history
    
    def test_compact_format(self):
        """Compact format is minimal for prompts."""
        history = IterationHistory()
        history.record("Fine entry bow", "committed")
        history.record("Increase beam", "rejected", reason="beam_progression failed")
        
        compact = history.get_compact_for_prompt()
        
        assert compact[0] == {"v": 1, "intent": "Fine entry bow", "result": "committed"}
        assert "rejected: beam_progression failed" in compact[1]["result"]
    
    def test_to_dict_serializable(self):
        """to_dict is JSON-serializable."""
        import json
        history = IterationHistory()
        history.record("Test", "committed", ["change1"])
        
        d = history.to_dict()
        json_str = json.dumps(d)
        assert len(json_str) > 0


class TestIterationRecord:
    """Test IterationRecord."""
    
    def test_compact_without_reason(self):
        """Compact without reason is minimal."""
        record = IterationRecord(version=1, intent="Test", result="committed")
        assert record.to_compact() == {"v": 1, "intent": "Test", "result": "committed"}
    
    def test_compact_with_reason(self):
        """Compact with reason includes reason in result."""
        record = IterationRecord(version=2, intent="Test", result="rejected", reason="failed check")
        compact = record.to_compact()
        assert compact["result"] == "rejected: failed check"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

### Step 6: Quality Gates (1 hour)

**File:** `magnet/kernel/stdlib/quality_gates.py`

```python
"""
Quality gates for hull fairness validation.

These validate geometric quality, NOT design style.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import math


@dataclass
class QualityResult:
    """Result of a quality check."""
    status: str  # "pass", "fail", "warn"
    check: str
    message: Optional[str] = None
    evidence: Dict[str, Any] = field(default_factory=dict)
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = {"check": self.check, "status": self.status}
        if self.message:
            d["message"] = self.message
        if self.evidence:
            d["evidence"] = self.evidence
        if self.suggestion:
            d["suggestion"] = self.suggestion
        return d


def check_beam_progression(sections: List[Dict], threshold: float = 0.15) -> QualityResult:
    """
    Check that beam varies smoothly along length.
    
    Args:
        sections: List of section dicts with 'points' and 'station'
        threshold: Max allowed deviation (default 15%)
    
    Returns:
        QualityResult
    """
    if len(sections) < 3:
        return QualityResult(status="pass", check="beam_progression")
    
    beams = [_max_beam(s) for s in sections]
    
    for i in range(1, len(beams) - 1):
        if beams[i-1] == 0 or beams[i+1] == 0:
            continue
        local_avg = (beams[i-1] + beams[i+1]) / 2
        if local_avg == 0:
            continue
        deviation = abs(beams[i] - local_avg) / local_avg
        
        if deviation > threshold:
            return QualityResult(
                status="fail",
                check="beam_progression",
                message=f"Beam jumps {deviation:.0%} at station {sections[i].get('station', i)}",
                evidence={
                    "station": sections[i].get("station"),
                    "beam": beams[i],
                    "expected": local_avg,
                    "deviation": deviation,
                },
                suggestion=f"Adjust beam to ~{local_avg:.2f}m",
            )
    
    return QualityResult(status="pass", check="beam_progression")


def check_deadrise_progression(sections: List[Dict], threshold_deg: float = 5.0) -> QualityResult:
    """
    Check that deadrise varies smoothly along length.
    
    Args:
        sections: List of section dicts
        threshold_deg: Max allowed deviation in degrees
    
    Returns:
        QualityResult
    """
    if len(sections) < 3:
        return QualityResult(status="pass", check="deadrise_progression")
    
    deadrises = [_compute_deadrise(s) for s in sections]
    
    for i in range(1, len(deadrises) - 1):
        local_avg = (deadrises[i-1] + deadrises[i+1]) / 2
        deviation = abs(deadrises[i] - local_avg)
        
        if deviation > threshold_deg:
            return QualityResult(
                status="fail",
                check="deadrise_progression",
                message=f"Deadrise jumps {deviation:.1f}° at station {sections[i].get('station', i)}",
                evidence={
                    "station": sections[i].get("station"),
                    "deadrise_deg": deadrises[i],
                    "expected_deg": local_avg,
                    "deviation_deg": deviation,
                },
                suggestion=f"Adjust deadrise to ~{local_avg:.1f}°",
            )
    
    return QualityResult(status="pass", check="deadrise_progression")


def check_chine_continuity(sections: List[Dict]) -> QualityResult:
    """
    Check that chine index is consistent across sections.
    
    Returns:
        QualityResult
    """
    if len(sections) < 2:
        return QualityResult(status="pass", check="chine_continuity")
    
    chine_indices = [_find_chine_index(s) for s in sections]
    chine_indices = [c for c in chine_indices if c is not None]
    
    if len(set(chine_indices)) > 1:
        return QualityResult(
            status="fail",
            check="chine_continuity",
            message=f"Chine index varies: {chine_indices}",
            evidence={"chine_indices": chine_indices},
            suggestion="Ensure chine is at same point index across all sections",
        )
    
    return QualityResult(status="pass", check="chine_continuity")


def run_all_quality_checks(sections: List[Dict]) -> List[QualityResult]:
    """Run all quality checks and return results."""
    return [
        check_beam_progression(sections),
        check_deadrise_progression(sections),
        check_chine_continuity(sections),
    ]


def _max_beam(section: Dict) -> float:
    """Get max beam (y-coordinate) from section."""
    points = section.get("points", [])
    if not points:
        return 0.0
    return max(p[0] for p in points)


def _compute_deadrise(section: Dict) -> float:
    """Compute deadrise angle from keel."""
    points = section.get("points", [])
    if len(points) < 2:
        return 0.0
    keel = points[0]
    next_pt = points[1]
    dy = next_pt[0] - keel[0]
    dz = next_pt[1] - keel[1]
    if dy == 0:
        return 90.0
    return math.degrees(math.atan2(abs(dz), dy))


def _find_chine_index(section: Dict) -> Optional[int]:
    """Find chine point index."""
    points = section.get("points", [])
    edge_types = section.get("edge_types", [])
    
    # If edge_types specified, find "chine" or "hard"
    for i, et in enumerate(edge_types):
        if et and ("chine" in str(et).lower() or "hard" in str(et).lower()):
            return i
    
    # Otherwise find max curvature change
    if len(points) < 3:
        return None
    
    max_change = 0
    chine_idx = None
    for i in range(1, len(points) - 1):
        prev, curr, next_pt = points[i-1], points[i], points[i+1]
        a1 = math.atan2(curr[1] - prev[1], curr[0] - prev[0])
        a2 = math.atan2(next_pt[1] - curr[1], next_pt[0] - curr[0])
        change = abs(a2 - a1)
        if change > max_change:
            max_change = change
            chine_idx = i
    
    return chine_idx
```

**Test:** `tests/prompt_architecture/test_quality_gates.py`

```python
"""
Test quality gate validation.
"""
import pytest
from magnet.kernel.stdlib.quality_gates import (
    check_beam_progression,
    check_deadrise_progression,
    check_chine_continuity,
    run_all_quality_checks,
    QualityResult,
)


class TestBeamProgression:
    """Test beam progression check."""
    
    def test_smooth_beam_passes(self):
        """Smooth beam progression passes."""
        sections = [
            {"station": 0.0, "points": [[1.0, 0], [1.0, -1]]},
            {"station": 0.5, "points": [[1.5, 0], [1.5, -1]]},
            {"station": 1.0, "points": [[1.4, 0], [1.4, -1]]},
        ]
        result = check_beam_progression(sections)
        assert result.status == "pass"
    
    def test_lumpy_beam_fails(self):
        """Lumpy beam progression fails."""
        sections = [
            {"station": 0.0, "points": [[1.0, 0], [1.0, -1]]},
            {"station": 0.5, "points": [[2.0, 0], [2.0, -1]]},  # Big jump
            {"station": 1.0, "points": [[1.0, 0], [1.0, -1]]},
        ]
        result = check_beam_progression(sections)
        assert result.status == "fail"
        assert "suggestion" in result.to_dict()


class TestDeadriseProgression:
    """Test deadrise progression check."""
    
    def test_smooth_deadrise_passes(self):
        """Smooth deadrise progression passes."""
        sections = [
            {"station": 0.0, "points": [[0, 0], [1, -0.3]]},  # ~17°
            {"station": 0.5, "points": [[0, 0], [1, -0.35]]}, # ~19°
            {"station": 1.0, "points": [[0, 0], [1, -0.4]]},  # ~22°
        ]
        result = check_deadrise_progression(sections)
        assert result.status == "pass"
    
    def test_spiky_deadrise_fails(self):
        """Spiky deadrise fails."""
        sections = [
            {"station": 0.0, "points": [[0, 0], [1, -0.2]]},  # ~11°
            {"station": 0.5, "points": [[0, 0], [1, -0.7]]},  # ~35° - big spike
            {"station": 1.0, "points": [[0, 0], [1, -0.2]]},  # ~11°
        ]
        result = check_deadrise_progression(sections)
        assert result.status == "fail"


class TestChineContinuity:
    """Test chine continuity check."""
    
    def test_consistent_chine_passes(self):
        """Consistent chine index passes."""
        sections = [
            {"station": 0.0, "points": [[0, 0], [0.5, -0.2], [1, -0.5], [0, -0.8]]},
            {"station": 0.5, "points": [[0, 0], [0.7, -0.15], [1.2, -0.4], [0, -0.7]]},
            {"station": 1.0, "points": [[0, 0], [0.6, -0.1], [1.1, -0.35], [0, -0.6]]},
        ]
        result = check_chine_continuity(sections)
        # May pass or warn depending on curvature detection
        assert result.status in ("pass", "warn")


class TestRunAllChecks:
    """Test running all quality checks."""
    
    def test_returns_all_results(self):
        """run_all_quality_checks returns list of results."""
        sections = [
            {"station": 0.0, "points": [[0, 0], [1, -0.5]]},
            {"station": 0.5, "points": [[0, 0], [1.2, -0.4]]},
            {"station": 1.0, "points": [[0, 0], [1.1, -0.35]]},
        ]
        results = run_all_quality_checks(sections)
        
        assert len(results) == 3
        assert all(isinstance(r, QualityResult) for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

### Step 7: Update Invariant Tests

**Extend:** `tests/invariants/test_transparency.py` (NEW)

```python
"""
Invariant tests for transparency.

INVARIANT: Every transformation must be observable and explainable.
"""
import pytest


class TestTransparencyInvariant:
    """Test that transparency invariant is maintained."""
    
    def test_transactions_always_return_transforms(self):
        """Transaction results always include transforms list."""
        from magnet.kernel.stdlib.transaction import Transaction, TransactionStatus
        
        state = {"_version": 1, "resources": {}}
        tx = Transaction(
            id="tx_test",
            operations=[
                {"op": "CREATE", "target": "test_section", "value": {"_type": "geometry.section"}},
            ],
        )
        
        result = tx.execute(state, validators=[])
        
        assert hasattr(result, "transforms")
        assert isinstance(result.transforms, list)
    
    def test_quality_results_include_evidence(self):
        """Failed quality checks include evidence."""
        from magnet.kernel.stdlib.quality_gates import check_beam_progression
        
        # Create sections with lumpy beam
        sections = [
            {"station": 0.0, "points": [[1.0, 0]]},
            {"station": 0.5, "points": [[3.0, 0]]},  # Big jump
            {"station": 1.0, "points": [[1.0, 0]]},
        ]
        
        result = check_beam_progression(sections)
        
        if result.status == "fail":
            assert result.evidence, "Failed check must include evidence"
            assert result.suggestion, "Failed check should include suggestion"
    
    def test_explain_registry_tracks_all_transforms(self):
        """ExplainRegistry tracks all recorded transforms."""
        from magnet.kernel.stdlib.explain import ExplainRegistry, ExplainTrace
        
        registry = ExplainRegistry()
        
        # Record multiple transforms
        for i in range(5):
            registry.record(ExplainTrace(
                transform_id=f"t_{i}",
                what=f"Transform {i}",
                why="test",
                rule="test_rule",
            ))
        
        # All should be retrievable
        all_traces = registry.explain_all()
        assert len(all_traces) == 5
        
        # Each should be explainable
        for i in range(5):
            trace = registry.explain(f"t_{i}")
            assert trace is not None
            assert trace.why == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

### Running the Tests

```bash
# Run all new prompt architecture tests
pytest tests/prompt_architecture/ -v

# Run specific test file
pytest tests/prompt_architecture/test_transaction_atomicity.py -v

# Run with coverage
pytest tests/prompt_architecture/ --cov=magnet.kernel.stdlib --cov=magnet.agents -v

# Run invariant tests (existing + new)
pytest tests/invariants/ -v

# Run integration to verify nothing broken
pytest tests/integration/test_kernel_pipeline.py -v
```

---

### CI Integration

Add to existing pytest configuration (already in `pyproject.toml`):

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
markers = [
    "prompt_arch: marks tests for prompt architecture (deselect with '-m \"not prompt_arch\"')",
    "invariant: marks invariant tests that should never be skipped",
]
```

---

## What This Enables

**Twin hull with tunnel (no type name):**
```
CREATE body hull_stbd { sections: [...] }
MIRROR hull_stbd → hull_port
SPACING hull_port hull_stbd >= 2.5
CREATE surface tunnel_roof { section_ids: [...] }
CLEARANCE tunnel_roof waterline >= 0.8
```

**Subtracted tunnel (no type name):**
```
CREATE body tunnel_negative { sections: [...shallow tunnel shape...] }
BOOLEAN subtract hull tunnel_negative → hull_with_tunnel
```

**Fine entry hull (no type name):**
```
CREATE section bow_01 { station: 0.02, points: [[0.1, -0.8], ...] }  // fine entry
CREATE section bow_02 { station: 0.08, points: [[0.15, -0.7], ...] }  // progressive flare
... (7-11 sections, consistent chine, smooth beam/deadrise)
```

No vessel names. Pure geometry. Kernel validates. **Every step explainable.**

---

## What This Doesn't Do (Deferred)

| Feature | When | Why Defer |
|---------|------|-----------|
| Cavity primitive | v1.3 | Inner elements need more design |
| Reserve buoyancy | v1.3 | Requires cavity |
| Multi-agent coordination | v1.2 | Single agent proves control plane first |
| Full dependency graph invalidation | v1.2 | Current dependencies are informational |

---

## Alignment Checklist

| Mission Requirement | This Plan |
|---------------------|-----------|
| NOVELTY = continuous × compositional × validation | ✅ Equation central |
| No enumeration | ✅ No hull types in schema |
| Every transformation observable | ✅ Explain traces |
| Edits atomic or rejected | ✅ Transaction semantics |
| State is the product | ✅ Versioned canonical state |
| Human-in-loop | ✅ ASK operation with context |
| Design spiral | ✅ Iteration history in v1.0 |
| Addressability | ✅ All resources have IDs |
| Dependency tracking | ✅ Dependencies in lens |

---

## Summary

**Gaps Closed:**
- BOOLEAN → tunnels, cutouts, complex shapes
- SPACING → multi-hull spacing
- CLEARANCE → tunnel clearance validation
- Fairness gates → no lumpy hulls (with suggestions)
- ASK → disambiguation instead of hallucination
- **Explain traces → "why did this happen?"**
- **Transaction semantics → atomic or rollback**
- **Iteration history → design spiral proof**
- **Version tracking → rollback capability**
- Token efficiency → ~750 vs ~4200 tokens

**The Equation:**
```
NOVELTY = continuous parameters × compositional operators × physics validation
```

Now with **complete compositional operators**, **full transparency**, and **proven design spiral**.
