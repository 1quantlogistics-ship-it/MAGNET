# LLM-Native Spatial Interface Specification

**Version:** 2.3  
**Status:** Draft  
**Date:** January 2026  

---

## North Star

> **The LLM is a naval architecture programmer. For hull form, it composes topology from primitives. For outfitting, it writes constraint programs. The kernel compiles both to validated geometry. The LLM reasons semantically while the system handles all spatial computation.**

### Three Regimes, One Principle

| Regime | Primitives | LLM Role | System Role |
|--------|------------|----------|-------------|
| **Hull Creation** | Surfaces, chines, steps, tunnels, foils, demihulls | Compose topology program | Synthesize NURBS |
| **Hull Editing** | ~10 anchors on existing hull | Pick from affordances | Compute transforms |
| **Outfitting** | Components, routes, zones, assemblies | Write constraint programs | Compile to 10k+ artifacts |

All three regimes share the same principle: **LLM writes programs, system compiles to geometry**. 

- **Hull Creation**: Topology program → NURBS synthesis
- **Hull Editing**: Affordance selection → anchor-based transforms (within existing topology)
- **Outfitting**: Constraint program → artifact expansion

The edit-vs-rewrite boundary (§2.6) determines when to switch from Hull Editing back to Hull Creation.

---

# PART I: HULL FORM (Topology & Editing)

*For creating hull topology from primitives and editing via anchor-based affordances.*

---

## 0. Hull Topology DSL (Creation, Not Enumeration)

> **IMPLEMENTATION NOTE**: This capability already exists in the current MAGNET architecture (`kernel/synthesis.py`, `hull_gen/`, `hull_gen/modifiers/`, `kernel/stdlib/`). This section specifies how to **surface it to the LLM** as a compositional DSL rather than hidden procedural code. Implementation is a **refactor/mutation** of existing synthesis machinery, not new development.

### 0.1 The Problem: Enumeration Trap

If hull creation requires selecting from `{monohull, catamaran, trimaran, stepped, tunnel, hydrofoil, ...}`, we've just moved enumeration from tools to types. The LLM can't create a "stepped catamaran with tunnel props" because no one enumerated that combination.

### 0.2 The Solution: Topological Primitives

Hull topology is **composed from primitives**, not selected from a catalog.

```python
class TopologicalPrimitive(Enum):
    """Primitives from which any hull can be composed."""
    
    SURFACE = "surface"       # Continuous hull panel (ruled, developable, or free-form)
    CHINE = "chine"           # Longitudinal discontinuity (hard edge)
    STEP = "step"             # Transverse discontinuity (ventilation break)
    TUNNEL = "tunnel"         # Void between surfaces (prop tunnel, cat tunnel)
    FOIL = "foil"             # Lifting surface (hydrofoil, trim tab)
    DEMIHULL = "demihull"     # Complete subsidiary hull body
    CROSSDECK = "crossdeck"   # Structure connecting demihulls
    SPONSON = "sponson"       # Outboard volume addition
    KEEL = "keel"             # Appendage (fin keel, bulb, etc.)
    SKEG = "skeg"             # Deadwood / propeller protection
    STRUT = "strut"           # Foil support structure

class CompositionOp(Enum):
    """Operations for combining primitives."""
    
    CREATE = "create"         # Instantiate a primitive
    CONNECT = "connect"       # Join primitives at boundaries
    MIRROR = "mirror"         # Symmetric copy across centerline
    BLEND = "blend"           # Smooth transition between surfaces
    SPLIT = "split"           # Divide surface at a station
    EXTRUDE = "extrude"       # Extend surface along path
    REVOLVE = "revolve"       # Create surface by rotation
    ARRAY = "array"           # Repeated instances (e.g., multiple steps)
```

### 0.3 Topology Program Syntax

**Simple Monohull (hard chine):**
```sql
CREATE surface[bottom] FROM keel TO chine DEADRISE 12deg
CREATE surface[topside] FROM chine TO sheer FLARE 15deg
CONSTRAIN continuity[chine] = G0  -- hard chine
CONSTRAIN continuity[sheer] = G1  -- fair sheerline
```

**Stepped Planing Hull:**
```sql
CREATE surface[fwd] FROM bow TO station[0.4] DEADRISE 18deg
CREATE step[1] AT station[0.4] HEIGHT 0.08m ANGLE 3deg
CREATE surface[mid] FROM step[1] TO station[0.7] DEADRISE 14deg
CREATE step[2] AT station[0.7] HEIGHT 0.06m ANGLE 2deg
CREATE surface[aft] FROM step[2] TO transom DEADRISE 10deg

CONSTRAIN step[1].ventilates = true
CONSTRAIN step[2].ventilates = true
CONSTRAIN step[*].edge_radius <= 0.005m  -- sharp for ventilation
```

**Catamaran:**
```sql
CREATE demihull[stbd] AS monohull(beam=2m, draft=1.2m, deadrise=20deg)
CREATE demihull[port] AS MIRROR(demihull[stbd])

SET demihull_spacing = 6m
CREATE crossdeck FROM demihull[port].sheer TO demihull[stbd].sheer

CONSTRAIN crossdeck.clearance >= 1.5m  -- wave slam clearance
CONSTRAIN demihull[*].symmetry = true
```

**Tunnel Hull (prop pockets):**
```sql
CREATE surface[main] AS monohull(deadrise=16deg)

CREATE tunnel[port] IN surface[main] AT y=-1.5m {
    depth: 0.3m,
    length: 2.5m,
    start_station: 0.7,
    end_station: 1.0
}
CREATE tunnel[stbd] AS MIRROR(tunnel[port])

CONSTRAIN tunnel[*].entry_angle <= 8deg   -- smooth water entry
CONSTRAIN tunnel[*].exit_fair = true       -- fair into transom
CONSTRAIN tunnel[*].roof_flat_width >= 0.4m  -- prop clearance
```

**Hydrofoil:**
```sql
CREATE hull AS monohull(loa=12m, beam=3m)

CREATE foil[main] TYPE surface_piercing AT station[0.3] {
    span: 4m,
    chord: 0.6m,
    section: "NACA_63-412",
    dihedral: 30deg
}
CREATE strut[main] FROM hull.bottom TO foil[main].center

CREATE foil[aft] TYPE fully_submerged AT station[0.85] {
    span: 2m,
    chord: 0.4m,
    section: "NACA_0012",
    submergence: 0.8m
}
CREATE strut[aft] FROM hull.bottom TO foil[aft].center

CONSTRAIN foil[main].span <= hull.beam * 1.3
CONSTRAIN foil[aft].submergence >= hull.draft * 0.5
CONSTRAIN strut[*].section = "NACA_0010"  -- low drag
```

**Trimaran:**
```sql
CREATE demihull[center] AS monohull(beam=4m, draft=1.5m)
CREATE demihull[port] AS ama(beam=0.8m, draft=0.6m, length_fraction=0.6)
CREATE demihull[stbd] AS MIRROR(demihull[port])

SET ama_spacing = 7m
SET ama_longitudinal_offset = 0.1  -- amas slightly aft

CREATE aka[port] CONNECTING demihull[center].side TO demihull[port].inboard
CREATE aka[stbd] AS MIRROR(aka[port])

CONSTRAIN ama[*].buoyancy_fraction >= 0.15  -- capsize recovery
CONSTRAIN aka[*].streamlined = true
```

**Novel Combination (no predefined type):**
```sql
-- "Stepped catamaran with tunnel props and bow foil"
-- This doesn't exist in any enumeration - composed from primitives

CREATE demihull[stbd] {
    -- Stepped planing hull form
    CREATE surface[fwd] FROM bow TO station[0.5] DEADRISE 20deg
    CREATE step[1] AT station[0.5] HEIGHT 0.06m
    CREATE surface[aft] FROM step[1] TO transom DEADRISE 14deg
    
    -- Prop tunnel
    CREATE tunnel[prop] AT y=0.3m DEPTH 0.25m LENGTH 1.8m
}
CREATE demihull[port] AS MIRROR(demihull[stbd])

SET demihull_spacing = 5m
CREATE crossdeck FROM demihull[port].sheer TO demihull[stbd].sheer

CREATE foil[bow] TYPE surface_piercing AT station[0.1] {
    span: 6m,
    chord: 0.5m,
    dihedral: 25deg
}

CONSTRAIN step[*].ventilates = true
CONSTRAIN tunnel[*].exit_fair = true
CONSTRAIN foil[bow].spans_both_hulls = true
CONSTRAIN crossdeck.clearance >= 1.2m
```

### 0.4 Why This Isn't Enumeration

| Approach | What LLM Does | Limitation |
|----------|---------------|------------|
| **Enumeration** | Selects `hull.type = "catamaran"` | Can't create unenumerated types |
| **Composition** | Writes topology program from primitives | Can create any physically valid form |

The LLM can compose hull forms that don't have names yet. The system validates physics regardless of whether the form is "standard."

### 0.5 Relationship to Existing Architecture

| Existing Module | Role in Topology DSL |
|-----------------|---------------------|
| `kernel/synthesis.py` | Compiles topology programs to NURBS |
| `hull_gen/generator.py` | Low-level surface generation |
| `hull_gen/geometry.py` | `HullGeometry`, `HullSection` data structures |
| `hull_gen/modifiers/` | Implementations of steps, knuckles, spray rails |
| `kernel/stdlib/` | Library of primitive implementations |
| `kernel/priors/hull_families.py` | Reference parameters (inform defaults, not hard types) |

**Refactoring Required:**

1. **Surface the DSL**: Currently, hull synthesis is driven by `HullFamily` enum + parameters. Refactor to accept topology programs.

2. **Primitive Library**: Extract existing modifier logic into composable primitives with clean interfaces.

3. **Constraint Propagation**: Topology constraints (e.g., `step.ventilates = true`) must propagate to synthesis parameters.

4. **Anchor Derivation**: After synthesis, detect anchors from resulting geometry (existing anchor detection applies unchanged).

### 0.6 Hull Creation vs Hull Editing

```
┌─────────────────────────────────────────────────────────────┐
│                    HULL CREATION                             │
│  LLM writes topology program → Kernel synthesizes NURBS     │
│  Output: New hull geometry + detected anchors               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    HULL EDITING                              │
│  LLM selects from affordances → Kernel applies transforms   │
│  Works within existing topology via anchors                 │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
     Edit viable?                    Edit boundary exceeded?
     (§2.6 policy)                   (cumulative drift, etc.)
              │                               │
              ▼                               ▼
     Continue editing              Return to HULL CREATION
                                   (new topology program)
```

**When to use each:**

| Situation | Regime | Why |
|-----------|--------|-----|
| "Create a 72ft Viking sportfish" | Hull Creation | No hull exists yet |
| "Make the bow finer" | Hull Editing | Topology unchanged, modify within anchors |
| "Add steps to the hull" | Hull Creation | Topology change (adding primitives) |
| "Increase deadrise 5°" | Hull Editing | Parameter change within existing topology |
| "Convert to catamaran" | Hull Creation | Fundamental topology change |
| Edit boundary exceeded (§2.6) | Hull Creation | Anchor tracking unreliable, resynthesize |

### 0.7 Anchor Derivation After Creation

Anchors are **outputs** of hull creation, not inputs:

```python
def create_hull_from_topology(program: "TopologyProgram") -> "HullCreationResult":
    """
    1. Parse topology program
    2. Synthesize NURBS surfaces
    3. Validate physics (floats, stable)
    4. Detect anchors from synthesized geometry
    5. Return hull + anchors for subsequent editing
    """
    
    # Compile topology to surfaces
    surfaces = compile_topology(program)
    
    # Generate NURBS
    hull_geometry = synthesize_nurbs(surfaces)
    
    # Validate
    physics_result = validate_physics(hull_geometry)
    if not physics_result.valid:
        return HullCreationResult(
            success=False,
            physics_failure=physics_result,
            attribution=attribute_to_program_statements(physics_result, program),
        )
    
    # Detect anchors from resulting geometry
    anchors = detect_anchors(hull_geometry)
    
    # Initialize edit boundary tracking
    edit_boundary_state = EditBoundaryState(
        synthesis_version=1,
        original_anchor_count=len(anchors),
    )
    
    return HullCreationResult(
        success=True,
        hull_geometry=hull_geometry,
        anchors=anchors,
        edit_boundary_state=edit_boundary_state,
        topology_program=program,  # Preserve for potential re-synthesis
    )
```

---

## 1. Core Principles

### 1.1 Division of Labor

| Task | Owner |
|------|-------|
| Parse geometry, compute bounds | System |
| Detect and track anchors | System |
| Compute clearances, conflicts | System |
| Generate movement options with limits | System |
| Assess operation feasibility | System |
| Maintain continuity (G0/G1/G2) | System |
| Generate qualitative descriptions | System |
| Understand user intent | LLM |
| Propose what should change (qualitative) | LLM |
| Choose between computed options | LLM |
| Explain tradeoffs to user | LLM |

### 1.2 Expensive Iteration Rationale

This architecture is designed for **expensive iteration** domains. Unlike web development where mistakes cost ~100ms, naval architecture operations are computationally expensive:

| Domain | Generate | Validate | Cost of Mistake |
|--------|----------|----------|-----------------|
| Web component | ~50ms | instant | ~100ms |
| Hull + structure + systems | seconds to minutes | expensive physics | minutes of compute |

**This changes everything about how the LLM must operate:**

- **No trial-and-error**: The LLM cannot "try and see what happens" — each attempt burns significant compute
- **No blind iteration**: When physics fails, the LLM needs attribution to make targeted fixes, not guesses
- **Pre-computation is mandatory**: Spatial queries against 10,000 artifacts are expensive; affordances must be cached
- **Validation before commit**: Sufficiency checks ensure the LLM has adequate information before triggering expensive operations

The abstractions in this spec (affordances, hierarchical operations, query interfaces, sufficiency matrices) are **computational necessities**, not conveniences.

### 1.3 Constrain Before Proposal (Design Pattern)

**The LLM selects from valid space. It never proposes operations that might be invalid.**

```
WRONG PATTERN (Check After Proposal):
  LLM proposes → Validate proposal → Maybe execute
  
CORRECT PATTERN (Constrain Before Proposal):
  System computes affordances → LLM selects from valid options → Execute
```

When the LLM sees:
```yaml
port:
  max: 0.5m
  blocked_by: "pipe_run_17"
```

It selects within that envelope. The "obviously doomed" operation (move 0.8m port) is never proposed because the affordance didn't offer it.

**Why this matters for expensive iteration:**

| Approach | Failure Mode | Cost |
|----------|--------------|------|
| Check after proposal | LLM proposes invalid op → rejected → re-propose | Wasted LLM turns, user frustration |
| **Constrain before proposal** | Invalid ops impossible to propose | Zero wasted operations |

This pattern applies throughout the spec:
- **Affordances**: Pre-computed movement envelopes define valid space
- **Integrated limits**: Geometry + character + archetype constraints unified before presentation
- **Sufficiency matrix**: Verify info completeness before decision, not mid-operation
- **Pareto fronts**: Pre-computed tradeoffs, not iterative "try this... try that"

**Corollary: No Approximate Physics Checks**

It might seem useful to add "speculative validation" that approximates physics before expensive operations:

```python
# WRONG - Don't do this
estimated_gm = approximate_gm_impact(proposed_change)
if estimated_gm < GM_HARD_MINIMUM:
    reject_early()
```

This is dangerous because:
1. **Redundant**: Affordances already constrain the valid space
2. **False rejections**: Approximate "no" when real physics would say "yes" loses valid options
3. **False confidence**: Approximate "ok" followed by real physics "fail" wastes compute anyway
4. **Wrong pattern**: It's "check after proposal" dressed up as optimization

The spec uses **authoritative pre-flight checks** (affordance bounds, sufficiency matrix, version validation), not physics approximations.

### 1.4 What the LLM Never Does

- Coordinate math
- Mental rotation / spatial transforms
- Distance calculations
- Collision detection
- "Will it fit?" reasoning from raw bounds
- **Propose operations outside affordance bounds**
- **Commit to operations without sufficient information**

### 1.5 What the LLM Always Gets

- Pre-computed assessments ("clearance insufficient")
- Constraint-bounded options ("can move 0-0.4m starboard")
- Qualitative descriptions ("cramped", "blocked")
- Named entities with persistent IDs
- **Integrated affordances** (unified geometry + character + archetype limits)
- **Attribution on failure** (which decisions caused which problems)

---

## 2. Anchor System (Identity Persistence)

### 2.1 The Problem

Anchors detected from geometry can shift, merge, or vanish after operations. If the LLM refers to `chine_1` but the geometry changed and `chine_1` is now `chine_0` or gone, the LLM's mental model desynchronizes.

### 2.2 Solution: Tracked Anchors with UUIDs

Anchors are not just detected—they are **born**, **tracked**, and **retired**.

```python
from dataclasses import dataclass, field
from typing import Optional, List
from uuid import uuid4
from enum import Enum

class AnchorStatus(Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"  # Confidence dropped but still trackable
    RETIRED = "retired"    # No longer valid, kept for history

class AnchorType(Enum):
    KEEL = "keel"
    SHEER = "sheer"
    CHINE = "chine"
    INFLECTION = "inflection"
    BEAM_MAX = "beam_max"

@dataclass
class TrackedAnchor:
    """Persistent anchor with stable identity across geometry changes."""
    
    # Stable identity (never changes)
    uuid: str = field(default_factory=lambda: str(uuid4()))
    
    # Semantic identity
    anchor_type: AnchorType = AnchorType.CHINE
    semantic_name: str = ""  # "primary_chine", "sheer", etc.
    
    # Current state (updated after each operation)
    section_id: str = ""
    point_index: int = 0
    confidence: float = 1.0
    status: AnchorStatus = AnchorStatus.ACTIVE
    
    # Tracking metadata
    born_at_version: int = 0
    last_seen_version: int = 0
    position_history: List[tuple] = field(default_factory=list)  # For drift detection
    
    # Detection method (for debugging/audit)
    detection_method: str = ""  # "z_minimum", "curvature_discontinuity", etc.
```

### 2.3 Anchor Lifecycle

```python
class AnchorTracker:
    """Maintains anchor identity across geometry changes."""
    
    def __init__(self):
        self._anchors: Dict[str, TrackedAnchor] = {}  # uuid -> anchor
        self._version = 0
    
    def update_after_operation(self, new_geometry: "Geometry") -> "AnchorUpdateReport":
        """
        After any geometry change:
        1. Re-detect candidate anchors
        2. Match to existing tracked anchors
        3. Update, degrade, or retire as needed
        4. Birth new anchors if unmatched candidates found
        """
        self._version += 1
        candidates = detect_anchor_candidates(new_geometry)
        
        report = AnchorUpdateReport()
        matched_uuids = set()
        
        # Match candidates to existing anchors
        for candidate in candidates:
            best_match = self._find_best_match(candidate)
            
            if best_match and self._is_valid_match(best_match, candidate):
                # Update existing anchor
                self._update_anchor(best_match, candidate)
                matched_uuids.add(best_match.uuid)
                report.updated.append(best_match.uuid)
            else:
                # Birth new anchor
                new_anchor = self._birth_anchor(candidate)
                report.born.append(new_anchor.uuid)
        
        # Handle unmatched existing anchors
        for uuid, anchor in self._anchors.items():
            if uuid not in matched_uuids and anchor.status == AnchorStatus.ACTIVE:
                if self._should_degrade(anchor):
                    anchor.status = AnchorStatus.DEGRADED
                    anchor.confidence *= 0.5
                    report.degraded.append(uuid)
                else:
                    anchor.status = AnchorStatus.RETIRED
                    report.retired.append(uuid)
        
        return report
    
    def _find_best_match(self, candidate: "AnchorCandidate") -> Optional[TrackedAnchor]:
        """Match by proximity + type + continuity of position history."""
        best = None
        best_score = 0
        
        for anchor in self._anchors.values():
            if anchor.status == AnchorStatus.RETIRED:
                continue
            if anchor.anchor_type != candidate.anchor_type:
                continue
                
            # Score based on position continuity
            score = self._match_score(anchor, candidate)
            if score > best_score:
                best_score = score
                best = anchor
        
        return best if best_score > MATCH_THRESHOLD else None
    
    def get_active_anchors(self) -> List[TrackedAnchor]:
        """Return only active anchors for LLM consumption."""
        return [a for a in self._anchors.values() 
                if a.status == AnchorStatus.ACTIVE]

@dataclass
class AnchorUpdateReport:
    """Report of what changed in anchor tracking."""
    born: List[str] = field(default_factory=list)
    updated: List[str] = field(default_factory=list)
    degraded: List[str] = field(default_factory=list)
    retired: List[str] = field(default_factory=list)
    
    def has_breaking_changes(self) -> bool:
        """True if LLM's mental model may be invalid."""
        return len(self.retired) > 0 or len(self.degraded) > 0
    
    def to_llm_notification(self) -> Optional[str]:
        """Generate notification if LLM needs to know about changes."""
        if not self.has_breaking_changes():
            return None
        
        parts = []
        if self.retired:
            parts.append(f"Anchors no longer valid: {self.retired}")
        if self.degraded:
            parts.append(f"Anchors with reduced confidence: {self.degraded}")
        if self.born:
            parts.append(f"New anchors detected: {self.born}")
        
        return " | ".join(parts)
```

### 2.4 LLM-Facing Anchor References

The LLM always refers to anchors by semantic name, which maps to UUID internally:

```yaml
# LLM sees:
anchors:
  primary_chine:
    id: "primary_chine"  # Semantic name (stable for LLM)
    status: "active"
    confidence: 0.95
    location_hint: "divides bottom from topside"
    
# System maintains mapping:
# "primary_chine" -> uuid: "a1b2c3d4-..."
```

If an anchor is retired, the LLM is notified explicitly:

```yaml
anchor_changes:
  - type: "retired"
    name: "secondary_chine"
    reason: "Merged with primary_chine after deadrise adjustment"
    suggestion: "Use primary_chine for bottom operations"
```

### 2.5 Topology Change Classification

Not all anchor changes are equal. The system must distinguish between incremental edits and fundamental topology changes:

```python
class TopologyChangeType(Enum):
    """Classification of how anchor tracking changed."""
    INCREMENTAL = "incremental"  # Anchors moved but topology stable
    ADDITIVE = "additive"        # New anchors added, existing preserved
    SUBTRACTIVE = "subtractive"  # Anchors removed, topology simplified
    RESTRUCTURE = "restructure"  # Topology fundamentally changed

@dataclass
class AnchorUpdateReport:
    # ... existing fields ...
    born: List[str] = field(default_factory=list)
    updated: List[str] = field(default_factory=list)
    degraded: List[str] = field(default_factory=list)
    retired: List[str] = field(default_factory=list)
    
    # NEW: Topology classification
    topology_change: TopologyChangeType = TopologyChangeType.INCREMENTAL
    
    def get_topology_change_type(self) -> TopologyChangeType:
        """Classify based on born/retired/degraded counts and anchor types."""
        
        primary_retired = sum(1 for a in self.retired if is_primary_anchor(a))
        primary_born = sum(1 for a in self.born if is_primary_anchor(a))
        
        # Restructure: primary anchors changed (keel, sheer, major chines)
        if primary_retired > 0 or primary_born > 0:
            return TopologyChangeType.RESTRUCTURE
        
        # Subtractive: anchors removed without replacement
        if len(self.retired) > len(self.born) + len(self.updated):
            return TopologyChangeType.SUBTRACTIVE
        
        # Additive: new anchors without removing existing
        if len(self.born) > 0 and len(self.retired) == 0:
            return TopologyChangeType.ADDITIVE
        
        return TopologyChangeType.INCREMENTAL
```

**On RESTRUCTURE, force explicit LLM acknowledgment:**

```yaml
topology_change_notification:
  type: "restructure"
  severity: "high"
  
  description: |
    The hull topology has fundamentally changed. Previous anchor references
    may no longer be valid.
    
  changes:
    retired_primary: ["original_chine"]
    born_primary: ["chine_lower", "chine_upper"]
    
  impact: |
    This is no longer an incremental edit. The hull has transitioned from
    single-chine to double-chine topology.
    
  options:
    - "acknowledge_and_continue: Accept new topology, update mental model"
    - "revert: Undo last operation, preserve original topology"
    - "resynthesize: Start fresh with new archetype (double-chine sportfish)"
    
  requires_llm_decision: true
```

### 2.6 Edit Boundary Policy (Circuit Breaker)

**This is the fix for the Viking v2→v3 corruption bug.**

The system must track cumulative drift and force rewrite when edit mode is no longer viable:

```python
@dataclass
class EditBoundaryPolicy:
    """Thresholds for when to stop editing and force resynthesis."""
    
    # Geometry drift (cumulative since last synthesis)
    max_cumulative_position_drift: float = 0.3  # Σ(anchor_shift) / LOA
    
    # Anchor health
    max_retired_fraction: float = 0.5   # If >50% of original anchors retired
    min_mean_confidence: float = 0.4    # If mean confidence drops too low
    
    # Topology stability
    max_topology_restructures: int = 2  # Major restructures before forced rewrite
    
    # Operation count (safety limit)
    max_operations_since_synthesis: int = 20

class EditViability(Enum):
    CONTINUE = "continue"           # Edit mode healthy
    WARN = "warn"                   # Approaching limits
    FORCE_REWRITE = "force_rewrite" # Edit mode no longer viable

@dataclass
class EditBoundaryState:
    """Accumulated state since last synthesis."""
    synthesis_version: int
    operations_count: int = 0
    cumulative_position_drift: float = 0.0
    original_anchor_count: int = 0
    current_anchor_count: int = 0
    retired_anchor_count: int = 0
    topology_restructure_count: int = 0
    confidence_history: List[float] = field(default_factory=list)

class AnchorTracker:
    def __init__(self):
        self._anchors: Dict[str, TrackedAnchor] = {}
        self._version = 0
        self._boundary_state = EditBoundaryState(synthesis_version=0)
        self._policy = EditBoundaryPolicy()
    
    def check_edit_viability(self) -> EditViabilityResult:
        """
        Called after every operation.
        Returns CONTINUE, WARN, or FORCE_REWRITE with explanation.
        """
        state = self._boundary_state
        policy = self._policy
        
        warnings = []
        
        # Check cumulative drift
        if state.cumulative_position_drift > policy.max_cumulative_position_drift:
            return EditViabilityResult(
                viability=EditViability.FORCE_REWRITE,
                reason="Cumulative geometry drift exceeded threshold",
                metric=f"drift: {state.cumulative_position_drift:.2f} > {policy.max_cumulative_position_drift}",
                recommendation="Resynthesize hull from current parameters to reset anchor tracking"
            )
        elif state.cumulative_position_drift > policy.max_cumulative_position_drift * 0.7:
            warnings.append(f"Geometry drift at {state.cumulative_position_drift:.0%} of limit")
        
        # Check anchor retirement rate
        if state.original_anchor_count > 0:
            retired_fraction = state.retired_anchor_count / state.original_anchor_count
            if retired_fraction > policy.max_retired_fraction:
                return EditViabilityResult(
                    viability=EditViability.FORCE_REWRITE,
                    reason="Too many original anchors retired",
                    metric=f"retired: {retired_fraction:.0%} > {policy.max_retired_fraction:.0%}",
                    recommendation="Hull topology has changed significantly. Resynthesize recommended."
                )
        
        # Check mean confidence
        if state.confidence_history:
            mean_confidence = sum(state.confidence_history) / len(state.confidence_history)
            if mean_confidence < policy.min_mean_confidence:
                return EditViabilityResult(
                    viability=EditViability.FORCE_REWRITE,
                    reason="Anchor tracking confidence too low",
                    metric=f"mean_confidence: {mean_confidence:.2f} < {policy.min_mean_confidence}",
                    recommendation="Anchor identity no longer reliable. Resynthesize to restore tracking."
                )
        
        # Check topology restructures
        if state.topology_restructure_count >= policy.max_topology_restructures:
            return EditViabilityResult(
                viability=EditViability.FORCE_REWRITE,
                reason="Too many topology restructures",
                metric=f"restructures: {state.topology_restructure_count} >= {policy.max_topology_restructures}",
                recommendation="Multiple topology changes detected. Fresh synthesis recommended."
            )
        
        # Check operation count
        if state.operations_count >= policy.max_operations_since_synthesis:
            warnings.append(f"Operation count ({state.operations_count}) approaching limit")
        
        if warnings:
            return EditViabilityResult(
                viability=EditViability.WARN,
                warnings=warnings,
                recommendation="Consider resynthesis soon to maintain tracking quality"
            )
        
        return EditViabilityResult(viability=EditViability.CONTINUE)
    
    def update_after_operation(self, new_geometry: "Geometry") -> AnchorUpdateReport:
        """After any geometry change, update tracking and check viability."""
        
        report = self._do_anchor_update(new_geometry)
        
        # Update boundary state
        self._boundary_state.operations_count += 1
        self._boundary_state.cumulative_position_drift += report.position_drift
        self._boundary_state.retired_anchor_count += len(report.retired)
        
        if report.topology_change == TopologyChangeType.RESTRUCTURE:
            self._boundary_state.topology_restructure_count += 1
        
        # Record confidence snapshot
        active_confidences = [a.confidence for a in self.get_active_anchors()]
        if active_confidences:
            self._boundary_state.confidence_history.append(
                sum(active_confidences) / len(active_confidences)
            )
        
        # Check viability
        viability = self.check_edit_viability()
        report.edit_viability = viability
        
        return report
    
    def reset_on_synthesis(self, new_geometry: "Geometry"):
        """Called after hull resynthesis to reset boundary tracking."""
        self._version += 1
        self._anchors = {}
        
        # Detect fresh anchors
        candidates = detect_anchor_candidates(new_geometry)
        for candidate in candidates:
            self._birth_anchor(candidate)
        
        # Reset boundary state
        self._boundary_state = EditBoundaryState(
            synthesis_version=self._version,
            original_anchor_count=len(self._anchors),
            current_anchor_count=len(self._anchors),
        )
```

**LLM-facing viability report:**

```yaml
edit_viability_report:
  status: "force_rewrite"
  
  reason: "Cumulative geometry drift exceeded threshold"
  
  metrics:
    cumulative_drift: 0.35
    drift_limit: 0.30
    operations_since_synthesis: 12
    retired_anchors: 4
    mean_confidence: 0.52
    
  explanation: |
    After 12 edit operations, the hull geometry has drifted significantly
    from the synthesized baseline. Anchor tracking is no longer reliable.
    
    The Viking v2 → v3 transition caused:
    - 4 anchors to retire (33% of original)
    - Position drift of 35% of LOA
    - Mean tracking confidence dropped to 52%
    
  recommendation: |
    Resynthesize the hull using current parameters. This will:
    - Generate fresh geometry matching current observable targets
    - Reset anchor tracking with high-confidence detections
    - Preserve all your parameter choices (deadrise, beam, etc.)
    
  action_required: "resynthesize_or_override"
  
  options:
    - id: "resynthesize"
      description: "Generate fresh hull, reset tracking (recommended)"
      preserves: ["parameters", "systems", "zones"]
      resets: ["anchor_ids", "edit_history"]
      
    - id: "override_continue"
      description: "Continue editing despite warnings (risky)"
      warning: "Subsequent edits may produce corrupted geometry"
```

---

## 3. Operation Templates with Continuity Handling

### 3.1 The Problem

Operations on segments between anchors can create tangency breaks (kinks) on smooth hulls. A "safe operation" that preserves topology may still damage hydrodynamic continuity.

### 3.2 Solution: Transition Types

```python
from enum import Enum
from typing import Callable, List, Optional

class ContinuityClass(Enum):
    """Geometric continuity requirements."""
    G0 = "g0"  # Positional only (hard chine ok)
    G1 = "g1"  # Tangent continuous (no kinks)
    G2 = "g2"  # Curvature continuous (smooth highlights)

class TransitionType(Enum):
    """How to handle boundaries between affected and unaffected regions."""
    HARD = "hard"              # Preserve discontinuity (chines)
    BLEND_LINEAR = "blend_linear"    # Linear falloff into neighbors
    BLEND_SMOOTH = "blend_smooth"    # Bezier/spline falloff (G1)
    BLEND_CURVATURE = "blend_curvature"  # Curvature-matched (G2)

@dataclass
class OperationTemplate:
    """
    Abstract operation that can be instantiated on geometry with matching anchors.
    Now includes continuity handling.
    """
    name: str
    required_anchors: List[str]
    invariants_preserved: List[str]
    transform: Callable
    
    # Continuity handling
    default_transition: TransitionType = TransitionType.HARD
    supported_transitions: List[TransitionType] = field(
        default_factory=lambda: [TransitionType.HARD]
    )
    min_continuity_class: ContinuityClass = ContinuityClass.G0
    
    # Blend parameters (when using smooth transitions)
    blend_distance_fraction: float = 0.1  # Fraction of segment length

@dataclass 
class ConcreteOperation:
    """Instantiated operation for specific geometry."""
    
    # Identity
    operation_id: str  # Unique ID for this instantiation
    template: OperationTemplate
    
    # Anchor binding
    segment_start_anchor: str  # UUID
    segment_end_anchor: str    # UUID
    pivot_anchor: Optional[str] = None  # UUID, if applicable
    
    # Scope
    affected_sections: List[str] = field(default_factory=list)
    
    # Continuity decision (computed from geometry analysis)
    detected_continuity: ContinuityClass = ContinuityClass.G0
    recommended_transition: TransitionType = TransitionType.HARD
    transition_reason: str = ""
    
    # Bounds
    max_delta: float = 0.0
    unit: str = ""
    
    # Confidence
    confidence: float = 1.0  # Min of anchor confidences
```

### 3.3 Automatic Continuity Detection

```python
def analyze_segment_continuity(
    geometry: "Geometry",
    start_anchor: TrackedAnchor,
    end_anchor: TrackedAnchor,
) -> ContinuityClass:
    """
    Analyze the existing continuity at anchor boundaries.
    Determines what transition type is needed to preserve hull quality.
    """
    start_idx = start_anchor.point_index
    end_idx = end_anchor.point_index
    
    # Check tangent continuity at start
    if start_idx > 0:
        tangent_before = compute_tangent(geometry, start_idx - 1, start_idx)
        tangent_after = compute_tangent(geometry, start_idx, start_idx + 1)
        tangent_break_start = angle_between(tangent_before, tangent_after)
    else:
        tangent_break_start = 0
    
    # Check tangent continuity at end
    if end_idx < len(geometry.points) - 1:
        tangent_before = compute_tangent(geometry, end_idx - 1, end_idx)
        tangent_after = compute_tangent(geometry, end_idx, end_idx + 1)
        tangent_break_end = angle_between(tangent_before, tangent_after)
    else:
        tangent_break_end = 0
    
    # Classify
    if tangent_break_start > CHINE_THRESHOLD or tangent_break_end > CHINE_THRESHOLD:
        return ContinuityClass.G0  # Hard chine exists
    
    # Check curvature continuity
    curvature_break = max(
        curvature_discontinuity(geometry, start_idx),
        curvature_discontinuity(geometry, end_idx),
    )
    
    if curvature_break > CURVATURE_THRESHOLD:
        return ContinuityClass.G1  # Tangent continuous but curvature breaks
    
    return ContinuityClass.G2  # Fully smooth

def recommend_transition(
    detected_continuity: ContinuityClass,
    anchor_type: AnchorType,
) -> tuple[TransitionType, str]:
    """Recommend transition type based on detected continuity and anchor semantics."""
    
    # Hard chines should stay hard
    if anchor_type == AnchorType.CHINE and detected_continuity == ContinuityClass.G0:
        return TransitionType.HARD, "Preserving existing chine character"
    
    # Smooth hulls need smooth transitions
    if detected_continuity == ContinuityClass.G2:
        return TransitionType.BLEND_CURVATURE, "Maintaining G2 continuity for fair hull"
    
    if detected_continuity == ContinuityClass.G1:
        return TransitionType.BLEND_SMOOTH, "Maintaining tangent continuity"
    
    return TransitionType.HARD, "Default for discontinuous geometry"
```

### 3.4 Blend Implementation

```python
def apply_operation_with_transition(
    geometry: "Geometry",
    operation: ConcreteOperation,
    delta: float,
    transition: TransitionType,
) -> "Geometry":
    """Apply operation with appropriate boundary blending."""
    
    start_idx = get_anchor_index(operation.segment_start_anchor)
    end_idx = get_anchor_index(operation.segment_end_anchor)
    segment_length = end_idx - start_idx
    
    # Compute blend zone sizes
    if transition == TransitionType.HARD:
        blend_before = 0
        blend_after = 0
    else:
        blend_size = int(segment_length * operation.template.blend_distance_fraction)
        blend_before = min(blend_size, start_idx)
        blend_after = min(blend_size, len(geometry.points) - end_idx - 1)
    
    # Apply core transform to segment
    new_geometry = geometry.copy()
    for i in range(start_idx, end_idx + 1):
        new_geometry.points[i] = operation.template.transform(
            geometry.points[i], delta
        )
    
    # Apply blending
    if transition in [TransitionType.BLEND_LINEAR, TransitionType.BLEND_SMOOTH, TransitionType.BLEND_CURVATURE]:
        # Blend before segment
        for i in range(start_idx - blend_before, start_idx):
            t = (i - (start_idx - blend_before)) / blend_before  # 0 to 1
            weight = blend_weight(t, transition)
            new_geometry.points[i] = lerp(
                geometry.points[i],
                operation.template.transform(geometry.points[i], delta),
                weight
            )
        
        # Blend after segment
        for i in range(end_idx + 1, end_idx + 1 + blend_after):
            t = (i - end_idx) / blend_after  # 0 to 1
            weight = blend_weight(1 - t, transition)  # Reverse
            new_geometry.points[i] = lerp(
                geometry.points[i],
                operation.template.transform(geometry.points[i], delta),
                weight
            )
    
    return new_geometry

def blend_weight(t: float, transition: TransitionType) -> float:
    """Compute blend weight based on transition type."""
    if transition == TransitionType.BLEND_LINEAR:
        return t
    elif transition == TransitionType.BLEND_SMOOTH:
        # Smoothstep (G1)
        return t * t * (3 - 2 * t)
    elif transition == TransitionType.BLEND_CURVATURE:
        # Smootherstep (G2)
        return t * t * t * (t * (6 * t - 15) + 10)
    else:
        return 1.0 if t > 0.5 else 0.0
```

### 3.5 Post-Blend Continuity Validation

**Applying a blend is not sufficient. We must verify the result actually achieves the target continuity.**

```python
@dataclass
class ContinuityValidationResult:
    """Result of verifying achieved continuity after blend."""
    target_continuity: ContinuityClass
    achieved_continuity: ContinuityClass
    success: bool
    
    # Detailed measurements
    tangent_break_start_deg: float = 0.0
    tangent_break_end_deg: float = 0.0
    curvature_break_start: float = 0.0
    curvature_break_end: float = 0.0
    
    # If failed
    failure_location: Optional[str] = None  # "start", "end", "both"
    suggestion: str = ""

def validate_continuity_achieved(
    geometry: "Geometry",
    operation: ConcreteOperation,
    target_continuity: ContinuityClass,
) -> ContinuityValidationResult:
    """
    After applying an operation with blending, verify the output
    geometry actually achieves the requested continuity class.
    """
    start_anchor = get_anchor(operation.segment_start_anchor)
    end_anchor = get_anchor(operation.segment_end_anchor)
    
    # Re-analyze the resulting geometry
    achieved = analyze_segment_continuity(geometry, start_anchor, end_anchor)
    
    # Measure actual breaks
    tangent_start = measure_tangent_break(geometry, start_anchor.point_index)
    tangent_end = measure_tangent_break(geometry, end_anchor.point_index)
    curvature_start = measure_curvature_break(geometry, start_anchor.point_index)
    curvature_end = measure_curvature_break(geometry, end_anchor.point_index)
    
    result = ContinuityValidationResult(
        target_continuity=target_continuity,
        achieved_continuity=achieved,
        success=(achieved.value >= target_continuity.value),
        tangent_break_start_deg=tangent_start,
        tangent_break_end_deg=tangent_end,
        curvature_break_start=curvature_start,
        curvature_break_end=curvature_end,
    )
    
    if not result.success:
        # Determine failure location
        if target_continuity == ContinuityClass.G1:
            if tangent_start > G1_THRESHOLD and tangent_end > G1_THRESHOLD:
                result.failure_location = "both"
            elif tangent_start > G1_THRESHOLD:
                result.failure_location = "start"
            else:
                result.failure_location = "end"
            result.suggestion = "Increase blend distance or reduce delta magnitude"
            
        elif target_continuity == ContinuityClass.G2:
            if curvature_start > G2_THRESHOLD and curvature_end > G2_THRESHOLD:
                result.failure_location = "both"
            elif curvature_start > G2_THRESHOLD:
                result.failure_location = "start"
            else:
                result.failure_location = "end"
            result.suggestion = "Increase blend distance, reduce delta, or accept G1 continuity"
    
    return result

def apply_operation_with_validation(
    geometry: "Geometry",
    operation: ConcreteOperation,
    delta: float,
    target_continuity: ContinuityClass,
) -> "OperationResult":
    """
    Apply operation with blending AND validate the result.
    Returns failure if target continuity not achieved.
    """
    # Determine transition type for target continuity
    if target_continuity == ContinuityClass.G0:
        transition = TransitionType.HARD
    elif target_continuity == ContinuityClass.G1:
        transition = TransitionType.BLEND_SMOOTH
    else:  # G2
        transition = TransitionType.BLEND_CURVATURE
    
    # Apply the operation
    new_geometry = apply_operation_with_transition(
        geometry, operation, delta, transition
    )
    
    # Validate achieved continuity
    validation = validate_continuity_achieved(
        new_geometry, operation, target_continuity
    )
    
    if not validation.success:
        return OperationResult(
            success=False,
            geometry=None,
            error=ContinuityValidationFailure(
                target=target_continuity,
                achieved=validation.achieved_continuity,
                failure_location=validation.failure_location,
                suggestion=validation.suggestion,
                measurements={
                    "tangent_break_start": validation.tangent_break_start_deg,
                    "tangent_break_end": validation.tangent_break_end_deg,
                    "curvature_break_start": validation.curvature_break_start,
                    "curvature_break_end": validation.curvature_break_end,
                }
            )
        )
    
    return OperationResult(
        success=True,
        geometry=new_geometry,
        continuity_validation=validation,
    )
```

**LLM notification on continuity failure:**

```yaml
continuity_failure:
  operation: "adjust_deadrise:keel_to_chine"
  delta: 8°
  
  target_continuity: "G2"
  achieved_continuity: "G1"
  
  failure_location: "end"  # At chine boundary
  
  measurements:
    tangent_break_start: 0.2°  # OK
    tangent_break_end: 0.8°    # OK for G1
    curvature_break_start: 0.02  # OK
    curvature_break_end: 0.15    # FAIL - exceeds G2 threshold
    
  explanation: |
    The operation achieved tangent continuity (G1) but not curvature 
    continuity (G2). The blend distance was insufficient for the 
    curvature rates at the chine boundary.
    
  options:
    - id: "accept_g1"
      description: "Accept G1 continuity (visible but fair highlight line)"
      impact: "Minor visual artifact at chine transition"
      
    - id: "increase_blend"
      description: "Retry with 2x blend distance"
      impact: "Larger affected region, may impact adjacent features"
      
    - id: "reduce_delta"
      description: "Reduce deadrise change to 5°"
      impact: "Achieves G2 but less geometric change"
      
    - id: "abort"
      description: "Cancel operation, preserve original geometry"
```

### 3.6 Adaptive Blend Distance

Fixed blend distance (10% of segment) is insufficient for all cases. The system should compute context-aware blend distances:

```python
def compute_adaptive_blend_distance(
    geometry: "Geometry",
    start_idx: int,
    end_idx: int,
    target_continuity: ContinuityClass,
    delta_magnitude: float,
) -> float:
    """
    Compute blend distance based on local geometry characteristics.
    """
    segment_length = end_idx - start_idx
    
    # Base: 10% of segment
    base_fraction = 0.1
    
    # Adjust for curvature: higher curvature needs longer blend
    curvature_at_start = abs(compute_curvature(geometry, start_idx))
    curvature_at_end = abs(compute_curvature(geometry, end_idx))
    max_curvature = max(curvature_at_start, curvature_at_end)
    curvature_factor = 1.0 + (max_curvature / REFERENCE_CURVATURE)
    
    # Adjust for delta magnitude: larger changes need longer blend
    delta_factor = 1.0 + (delta_magnitude / REFERENCE_DELTA)
    
    # Adjust for target continuity: G2 needs more than G1
    continuity_factor = {
        ContinuityClass.G0: 0.0,
        ContinuityClass.G1: 1.0,
        ContinuityClass.G2: 1.5,
    }[target_continuity]
    
    # Compute final fraction
    blend_fraction = base_fraction * curvature_factor * delta_factor * continuity_factor
    
    # Clamp to reasonable range
    blend_fraction = min(blend_fraction, 0.4)  # Max 40% of segment
    
    # Ensure minimum points for blending
    min_blend_points = 3
    blend_distance = max(int(segment_length * blend_fraction), min_blend_points)
    
    # Check for overlap with adjacent operations (if tracking)
    # ... overlap detection logic ...
    
    return blend_distance
```

---

## 4. Anchor Hierarchy (Semantic Filtering)

### 4.1 The Problem

Real-world geometry (especially scanned) may have dozens of detected inflection points due to noise. Exposing all of them creates "enumeration in disguise" with meaningless names like `inflection_22_to_inflection_23`.

### 4.2 Solution: Dominance Hierarchy

```python
class AnchorDominance(Enum):
    """Hierarchy level for anchor visibility."""
    PRIMARY = "primary"      # Always exposed (keel, sheer)
    SECONDARY = "secondary"  # Exposed by default (major chines, max beam)
    TERTIARY = "tertiary"    # Hidden unless zoomed (minor features)
    NOISE = "noise"          # Never exposed (artifacts, scan noise)

@dataclass
class DominanceConfig:
    """Thresholds for anchor classification."""
    
    # Curvature thresholds (degrees)
    primary_curvature_break: float = 30.0    # Major chine
    secondary_curvature_break: float = 15.0  # Minor chine
    tertiary_curvature_break: float = 5.0    # Subtle inflection
    
    # Confidence thresholds
    secondary_min_confidence: float = 0.8
    tertiary_min_confidence: float = 0.5
    
    # Spatial significance (fraction of hull dimension)
    min_segment_fraction: float = 0.05  # Ignore features < 5% of hull size

def classify_anchor_dominance(
    anchor: TrackedAnchor,
    geometry: "Geometry",
    config: DominanceConfig,
) -> AnchorDominance:
    """Classify anchor into hierarchy level."""
    
    # Keel and sheer are always primary
    if anchor.anchor_type in [AnchorType.KEEL, AnchorType.SHEER]:
        return AnchorDominance.PRIMARY
    
    # Low confidence = tertiary or noise
    if anchor.confidence < config.tertiary_min_confidence:
        return AnchorDominance.NOISE
    
    if anchor.confidence < config.secondary_min_confidence:
        return AnchorDominance.TERTIARY
    
    # Measure curvature break magnitude
    curvature_break = measure_curvature_break(geometry, anchor.point_index)
    
    if curvature_break >= config.primary_curvature_break:
        return AnchorDominance.PRIMARY
    elif curvature_break >= config.secondary_curvature_break:
        return AnchorDominance.SECONDARY
    elif curvature_break >= config.tertiary_curvature_break:
        return AnchorDominance.TERTIARY
    else:
        return AnchorDominance.NOISE

class AnchorHierarchy:
    """Manages hierarchical anchor exposure to LLM."""
    
    def __init__(self, tracker: AnchorTracker, config: DominanceConfig):
        self._tracker = tracker
        self._config = config
        self._dominance: Dict[str, AnchorDominance] = {}
    
    def update(self, geometry: "Geometry"):
        """Reclassify all anchors after geometry change."""
        for anchor in self._tracker.get_active_anchors():
            self._dominance[anchor.uuid] = classify_anchor_dominance(
                anchor, geometry, self._config
            )
    
    def get_visible_anchors(
        self,
        max_level: AnchorDominance = AnchorDominance.SECONDARY,
    ) -> List[TrackedAnchor]:
        """Get anchors visible at the requested detail level."""
        visible = []
        for anchor in self._tracker.get_active_anchors():
            level = self._dominance.get(anchor.uuid, AnchorDominance.NOISE)
            if self._level_is_visible(level, max_level):
                visible.append(anchor)
        return visible
    
    def _level_is_visible(
        self,
        level: AnchorDominance,
        max_level: AnchorDominance,
    ) -> bool:
        order = [AnchorDominance.PRIMARY, AnchorDominance.SECONDARY, AnchorDominance.TERTIARY, AnchorDominance.NOISE]
        return order.index(level) <= order.index(max_level)
```

### 4.3 LLM-Facing Hierarchy

Default view (primary + secondary):

```yaml
section_anchors:
  - name: "keel"
    type: "primary"
    role: "lowest point of section"
  - name: "primary_chine"
    type: "secondary"
    role: "hard corner between bottom and topside"
    confidence: 0.95
  - name: "sheer"
    type: "primary"
    role: "deck edge"

available_segments:
  - "keel_to_primary_chine" (bottom panel)
  - "primary_chine_to_sheer" (topside panel)
```

Zoomed view (includes tertiary):

```yaml
section_anchors_detailed:
  - name: "keel"
    type: "primary"
  - name: "spray_rail_attachment"
    type: "tertiary"
    confidence: 0.7
    note: "subtle inflection, may be noise or intentional feature"
  - name: "primary_chine"
    type: "secondary"
  - name: "secondary_chine"
    type: "tertiary"
    confidence: 0.6
    note: "minor curvature break above main chine"
  - name: "sheer"
    type: "primary"
```

---

## 5. Delta-Affordance (Proactive Constraint Reporting)

### 5.1 The Problem

LLMs cannot compute spatial feasibility. If the LLM proposes "move genset 0.3m to starboard" without knowing the fuel tank is 0.2m away, it wastes turns guessing.

### 5.2 Solution: Pre-Computed Movement Envelopes

Don't tell the LLM where things are. Tell the LLM **where things can go**.

```python
@dataclass
class MovementEnvelope:
    """Pre-computed bounds on how far a component can move."""
    component_id: str
    
    # Per-direction limits
    limits: Dict[str, "DirectionLimit"]  # "stbd", "port", "fwd", "aft", "up", "down"

@dataclass
class DirectionLimit:
    """Movement limit in one direction."""
    direction: str
    max_distance_m: float
    limited_by: str  # What stops further movement
    limited_by_id: Optional[str] = None  # ID of blocking entity
    
    # Incremental options
    safe_distance_m: float = 0.0  # Distance that maintains all clearances
    warning_distance_m: float = 0.0  # Distance that violates soft constraints
    
    # Side effects
    side_effects: List[str] = field(default_factory=list)

def compute_movement_envelope(
    state: "DesignState",
    component_id: str,
    min_clearance: float = 0.1,
) -> MovementEnvelope:
    """
    Compute how far a component can move in each direction.
    This is the "delta-affordance" — what the geometry affords.
    """
    component = state.get_component(component_id)
    bounds = component.bounds
    
    limits = {}
    
    for direction, vector in DIRECTION_VECTORS.items():
        # Ray cast from component bounds in direction
        # Find first collision
        collision = find_first_collision(
            state,
            bounds,
            vector,
            exclude=[component_id],
        )
        
        if collision:
            max_dist = collision.distance - min_clearance
            limited_by = collision.entity_name
            limited_by_id = collision.entity_id
        else:
            max_dist = float('inf')
            limited_by = "none"
            limited_by_id = None
        
        # Check zone boundaries
        zone_limit = distance_to_zone_boundary(state, component, vector)
        if zone_limit < max_dist:
            max_dist = zone_limit
            limited_by = "zone boundary"
            limited_by_id = component.parent_zone_id
        
        # Compute side effects
        side_effects = []
        affected_routes = find_affected_routes(state, component_id, vector, max_dist)
        if affected_routes:
            side_effects.append(f"Reroute required: {len(affected_routes)} connections")
        
        limits[direction] = DirectionLimit(
            direction=direction,
            max_distance_m=max(0, max_dist),
            limited_by=limited_by,
            limited_by_id=limited_by_id,
            safe_distance_m=max(0, max_dist * 0.8),  # 80% of max is "safe"
            side_effects=side_effects,
        )
    
    return MovementEnvelope(component_id=component_id, limits=limits)
```

### 5.3 LLM-Facing Affordance Format

```yaml
component: "genset"
location_description: "Forward-starboard corner of engine room"

movement_affordance:
  starboard:
    max: 0.2m
    blocked_by: "fuel_tank_2"
    safe: 0.15m
    side_effects: []
    
  port:
    max: 0.8m
    blocked_by: "main_engine"
    safe: 0.6m
    side_effects:
      - "Would create 0.6m passage along starboard side"
    
  forward:
    max: 0.4m
    blocked_by: "engine_room_fwd_bulkhead"
    safe: 0.3m
    side_effects:
      - "Exhaust run length increases by 0.4m"
    
  aft:
    max: 0.1m
    blocked_by: "main_engine"
    safe: 0m
    side_effects: []

  up:
    max: 0.3m
    blocked_by: "deck_clearance"
    safe: 0.2m
    side_effects:
      - "Exhaust reroute required"

  down:
    max: 0m
    blocked_by: "hull_bottom"
    safe: 0m
    side_effects: []

summary: "Can move up to 0.8m toward port (blocked by main_engine) or 0.2m toward starboard (blocked by fuel_tank_2). Forward movement limited to 0.4m by bulkhead."
```

The LLM reads this and knows **exactly** what's possible. No guessing.

### 5.4 Operation Affordances (For Hull Geometry)

Same concept for hull operations:

```yaml
operation: "adjust_deadrise:keel_to_chine"
scope: "bow (stations 0.0-0.25)"

affordance:
  increase:
    max_delta: 12°
    limited_by: "chine would intersect keel"
    current_value: 18°
    at_max: 30°
    
  decrease:
    max_delta: 8°
    limited_by: "minimum deadrise for spray deflection"
    current_value: 18°
    at_max: 10°
    
  side_effects:
    - "Displacement decreases ~3% per 5° increase"
    - "Entry angle affected (coupled observable)"
    
  character_impact:
    predicted_drift_at_5deg: 0.02
    predicted_drift_at_10deg: 0.08
    warning: "Changes > 8° approach character preservation soft limit"
```

### 5.5 Affordance Versioning (Staleness Detection)

Affordances are computed at a point in time. The spatial environment may change during LLM deliberation. **Stale affordances can lead to collisions.**

```python
@dataclass
class MovementEnvelope:
    """Pre-computed bounds on how far a component can move."""
    component_id: str
    limits: Dict[str, "DirectionLimit"]
    
    # NEW: Version tracking
    computed_at_version: int      # State version when computed
    computed_at_timestamp: float  # Unix timestamp
    valid_until_version: int      # Invalidated if state version exceeds this
    
    def is_stale(self, current_version: int) -> bool:
        """Check if this affordance is still valid."""
        return current_version > self.computed_at_version

@dataclass
class AffordanceValidationResult:
    """Result of checking affordance freshness before operation."""
    valid: bool
    affordance_version: int
    current_version: int
    
    # If invalid
    changes_since_computation: List[str] = field(default_factory=list)
    recommendation: str = ""

def validate_affordance_freshness(
    envelope: MovementEnvelope,
    current_state: "DesignState",
) -> AffordanceValidationResult:
    """
    Before executing an operation based on affordance, verify it's still valid.
    """
    current_version = current_state.version
    
    if not envelope.is_stale(current_version):
        return AffordanceValidationResult(
            valid=True,
            affordance_version=envelope.computed_at_version,
            current_version=current_version,
        )
    
    # Affordance is stale - identify what changed
    changes = []
    
    # Check if any blocking entities moved
    for direction, limit in envelope.limits.items():
        if limit.limited_by_id:
            current_position = current_state.get_component_position(limit.limited_by_id)
            if current_position != get_position_at_version(limit.limited_by_id, envelope.computed_at_version):
                changes.append(f"{limit.limited_by} has moved")
    
    # Check if new entities appeared in the movement path
    for direction, limit in envelope.limits.items():
        new_obstacles = find_new_obstacles_since(
            current_state, 
            envelope.component_id, 
            direction, 
            envelope.computed_at_version
        )
        if new_obstacles:
            changes.append(f"New obstacles in {direction} direction: {new_obstacles}")
    
    return AffordanceValidationResult(
        valid=False,
        affordance_version=envelope.computed_at_version,
        current_version=current_version,
        changes_since_computation=changes,
        recommendation="Re-query affordance before proceeding",
    )

def execute_with_affordance_check(
    state: "DesignState",
    operation: "Operation",
    affordance: MovementEnvelope,
) -> "OperationResult":
    """
    Execute operation only if affordance is still valid.
    Re-queries if stale.
    """
    validation = validate_affordance_freshness(affordance, state)
    
    if not validation.valid:
        # Re-compute affordance
        fresh_affordance = compute_movement_envelope(state, affordance.component_id)
        
        # Check if operation is still feasible
        requested_direction = operation.direction
        requested_distance = operation.distance
        
        fresh_limit = fresh_affordance.limits[requested_direction]
        
        if requested_distance > fresh_limit.max_distance_m:
            return OperationResult(
                success=False,
                error=StaleAffordanceError(
                    message="Affordance changed since query",
                    original_max=affordance.limits[requested_direction].max_distance_m,
                    current_max=fresh_limit.max_distance_m,
                    changes=validation.changes_since_computation,
                    suggestion=f"Max {requested_direction} movement is now {fresh_limit.max_distance_m}m"
                )
            )
        
        # Feasible with fresh affordance - proceed
        affordance = fresh_affordance
    
    # Execute operation
    return execute_operation(state, operation)
```

**LLM notification on stale affordance:**

```yaml
stale_affordance_error:
  operation: "move genset 0.8m to port"
  
  original_affordance:
    version: 42
    port_max: 0.8m
    blocked_by: "main_engine"
    
  current_state:
    version: 45
    port_max: 0.5m  # Changed!
    blocked_by: "new_pipe_run_17"
    
  changes_since_query:
    - "RoutingAgent placed pipe_run_17 in path"
    - "State version advanced from 42 to 45"
    
  recommendation: |
    The spatial environment changed while you were deliberating.
    A new pipe run now blocks 0.3m of the previously available space.
    
  options:
    - "Move 0.5m to port (current maximum)"
    - "Relocate pipe_run_17 first, then move genset"
    - "Re-query full affordance for updated options"
```

### 5.6 Cross-System Affordance Integration

Hull shaping affordances (Part I) and archetype guard limits (Part III) are computed separately. **They must be integrated to present unified safe ranges.**

```python
@dataclass
class IntegratedAffordance:
    """Unified affordance combining geometry limits and policy limits."""
    
    operation: str
    
    # Geometric limit (from hull analysis)
    geometric_max: float
    geometric_limited_by: str
    
    # Policy limits (from guards)
    character_soft_limit: Optional[float] = None
    character_hard_limit: Optional[float] = None
    archetype_limit: Optional[float] = None
    regulatory_limit: Optional[float] = None
    
    # Integrated result
    safe_max: float = 0.0           # Satisfies all soft limits
    absolute_max: float = 0.0       # Satisfies only hard limits
    recommended_max: float = 0.0    # Best balance
    
    # Limit attribution
    limiting_factor: str = ""       # What determines recommended_max

def compute_integrated_affordance(
    state: "DesignState",
    operation: "ConcreteOperation",
    archetype: "Archetype",
    config: "CortexConfig",
) -> IntegratedAffordance:
    """
    Combine geometric affordance with character preservation,
    archetype guard, and regulatory limits.
    """
    # Get geometric limit
    geometric = compute_operation_geometric_limit(state, operation)
    
    # Get character preservation limits
    character_soft, character_hard = compute_character_limits(
        state, operation, config.character_preservation
    )
    
    # Get archetype limits
    archetype_limit = compute_archetype_limit(state, operation, archetype)
    
    # Get regulatory limits (if any)
    regulatory = get_regulatory_limit(operation)
    
    # Compute integrated limits
    all_soft_limits = [
        geometric.max_delta,
        character_soft,
        archetype_limit,
    ]
    all_hard_limits = [
        geometric.max_delta,
        character_hard,
        regulatory,
    ]
    
    # Filter None values
    soft_limits = [l for l in all_soft_limits if l is not None]
    hard_limits = [l for l in all_hard_limits if l is not None]
    
    safe_max = min(soft_limits) if soft_limits else 0.0
    absolute_max = min(hard_limits) if hard_limits else 0.0
    
    # Determine limiting factor
    if safe_max == geometric.max_delta:
        limiting_factor = "geometry"
    elif safe_max == character_soft:
        limiting_factor = "character_preservation"
    elif safe_max == archetype_limit:
        limiting_factor = "archetype_guard"
    else:
        limiting_factor = "unknown"
    
    return IntegratedAffordance(
        operation=operation.name,
        geometric_max=geometric.max_delta,
        geometric_limited_by=geometric.limited_by,
        character_soft_limit=character_soft,
        character_hard_limit=character_hard,
        archetype_limit=archetype_limit,
        regulatory_limit=regulatory,
        safe_max=safe_max,
        absolute_max=absolute_max,
        recommended_max=safe_max,  # Default to safe
        limiting_factor=limiting_factor,
    )
```

**LLM-facing integrated affordance:**

```yaml
operation: "adjust_deadrise:keel_to_chine"
scope: "bow"
current_value: 18°

integrated_affordance:
  # What geometry allows
  geometric_max: 12°
  geometric_reason: "Chine would intersect keel beyond 12°"
  
  # What character preservation allows
  character_soft_limit: 8°
  character_hard_limit: 15°
  character_reason: "Drift exceeds soft limit at 8°, hard limit at 15°"
  
  # What archetype allows
  archetype_limit: 10°
  archetype_reason: "Viking sportfish requires deadrise 10-16° at bow"
  
  # Integrated recommendation
  safe_range: "0° to 8°"
  caution_range: "8° to 10°"  # Exceeds character soft but within archetype
  override_range: "10° to 12°"  # Requires explicit acknowledgment
  forbidden: "> 12°"  # Geometric impossibility
  
  recommended: 8°
  limiting_factor: "character_preservation"
  
  explanation: |
    You can safely adjust deadrise up to 8° without warnings.
    8-10° will trigger character preservation warnings but stays within archetype.
    10-12° requires override (exceeds archetype but geometrically possible).
    Beyond 12° is not possible (geometric constraint).
```

---

## 6. LLM Scene Description Format

### 6.1 Qualitative Descriptions (No Coordinate Math)

```yaml
engine_room:
  location: "Aft quarter of vessel, below cockpit deck"
  size_class: "medium"  # small/medium/large relative to vessel
  
  qualitative_assessment:
    overall: "Functional but cramped"
    access: "Limited - single deck hatch plus transom door"
    serviceability: "Poor for main engine, adequate for auxiliaries"
    ventilation: "Adequate with current blower arrangement"
    
  layout_narrative: |
    Main engine dominates the center-aft position, leaving limited 
    passage around it. The genset is wedged into the forward-starboard 
    corner, blocking what could be a useful passage along the starboard 
    side. Fuel tanks line both sides against the hull, which is good 
    for stability but limits width for moving equipment.
    
  problems:
    - severity: "high"
      issue: "No clear passage from deck hatch to transom door"
      affected: ["main_engine_service", "emergency_egress"]
      
    - severity: "medium"  
      issue: "Genset service requires contortion"
      affected: ["genset_oil_change", "genset_filter_access"]
      
    - severity: "low"
      issue: "Port fuel tank inspection panel partially blocked"
      affected: ["fuel_tank_inspection"]
      
  opportunities:
    - "Moving genset 0.3m to port would create viable passage"
    - "Adding deck hatch above genset would improve service access"
```

### 6.2 Augmented ASCII (Scale-Aware)

```yaml
plan_view_ascii:
  scale: "1 char = 0.5m"
  grid_size: "8m x 4m"
  view: |
    FWD BULKHEAD
    +---------------+
    |       |       |
    | [GEN] |       |
    |  1x1  |       |
    |-------|  ENG  |
    |       |  2x1  |
    | [TK2] |       |
    |  1x2  |-------|
    |       |       |
    |-------| [TK1] |
    |       |  1x2  |
    +---------------+
    AFT (TRANSOM)
    
  legend:
    GEN: "Genset (1.0m x 1.0m)"
    ENG: "Main Engine (2.0m x 1.0m)"
    TK1: "Fuel Tank 1 (1.0m x 2.0m)"
    TK2: "Fuel Tank 2 (1.0m x 2.0m)"
    
  collision_warnings:
    - "⚠ Clearance GEN↔ENG: 0.15m (minimum recommended: 0.3m)"
    - "⚠ Clearance TK1↔ENG: 0.1m (service access limited)"
```

### 6.3 Clearance Matrix (Pre-Computed)

```yaml
clearance_matrix:
  format: "component_a → component_b: clearance (status)"
  
  data:
    genset → main_engine: "0.15m (⚠ tight)"
    genset → fuel_tank_2: "0.3m (ok)"
    genset → fwd_bulkhead: "0.4m (ok)"
    genset → stbd_hull: "0.2m (⚠ tight)"
    main_engine → fuel_tank_1: "0.1m (⚠ service limited)"
    main_engine → aft_bulkhead: "0.8m (ok)"
    fuel_tank_1 → port_hull: "0.05m (ok - mounted)"
    fuel_tank_2 → stbd_hull: "0.05m (ok - mounted)"
    
  summary:
    adequate: 5
    tight: 3
    critical: 0
```

### 6.4 Geometry Quality Metrics (Beyond Clearances)

Qualitative summaries must include **geometric quality**, not just spatial relationships. A hull can progressively unfair through delta operations while maintaining adequate clearances.

```python
@dataclass
class GeometryQualityReport:
    """Quality metrics for hull geometry beyond spatial clearances."""
    
    # Surface fairness (how smooth the hull is)
    fairness_score: float          # 0-1, 1 = perfectly fair
    curvature_anomalies: List["CurvatureAnomaly"]
    
    # Panel quality (for construction)
    max_panel_warp: float          # degrees
    non_developable_panels: int
    panel_quality_score: float     # 0-1
    
    # Mesh quality (if applicable)
    aspect_ratio_worst: float
    skewness_worst: float
    mesh_quality_score: float      # 0-1
    
    # Overall
    overall_quality: str           # "excellent", "good", "fair", "poor", "degraded"
    degradation_since_synthesis: float  # Change in quality since last synthesis

@dataclass
class CurvatureAnomaly:
    """A location where curvature is unexpectedly discontinuous."""
    location: str                  # e.g., "station 0.35, chine region"
    severity: str                  # "minor", "moderate", "severe"
    type: str                      # "kink", "flat_spot", "bulge", "hollow"
    likely_cause: str              # "accumulated blend overlap", "delta too large"

def compute_geometry_quality(
    geometry: "Geometry",
    baseline_quality: Optional["GeometryQualityReport"] = None,
) -> GeometryQualityReport:
    """
    Compute comprehensive quality metrics for hull geometry.
    """
    # Compute fairness (smoothness of curvature flow)
    curvature_profile = compute_curvature_profile(geometry)
    fairness_score = compute_fairness_score(curvature_profile)
    anomalies = detect_curvature_anomalies(curvature_profile)
    
    # Compute panel quality (for developable surfaces)
    panels = extract_panels(geometry)
    max_warp = max(compute_panel_warp(p) for p in panels)
    non_dev = sum(1 for p in panels if not is_developable(p))
    panel_score = compute_panel_quality_score(panels)
    
    # Compute mesh quality (if meshed)
    if geometry.has_mesh:
        aspect_worst, skew_worst = compute_mesh_quality_metrics(geometry.mesh)
        mesh_score = compute_mesh_quality_score(geometry.mesh)
    else:
        aspect_worst = skew_worst = 0.0
        mesh_score = 1.0
    
    # Overall assessment
    scores = [fairness_score, panel_score, mesh_score]
    avg_score = sum(scores) / len(scores)
    
    if avg_score >= 0.9:
        overall = "excellent"
    elif avg_score >= 0.75:
        overall = "good"
    elif avg_score >= 0.6:
        overall = "fair"
    elif avg_score >= 0.4:
        overall = "poor"
    else:
        overall = "degraded"
    
    # Degradation tracking
    if baseline_quality:
        degradation = baseline_quality.fairness_score - fairness_score
    else:
        degradation = 0.0
    
    return GeometryQualityReport(
        fairness_score=fairness_score,
        curvature_anomalies=anomalies,
        max_panel_warp=max_warp,
        non_developable_panels=non_dev,
        panel_quality_score=panel_score,
        aspect_ratio_worst=aspect_worst,
        skewness_worst=skew_worst,
        mesh_quality_score=mesh_score,
        overall_quality=overall,
        degradation_since_synthesis=degradation,
    )
```

**LLM-facing quality report:**

```yaml
geometry_quality:
  overall: "fair"
  
  surface_fairness:
    score: 0.68
    assessment: "Minor unfairness in bow region"
    anomalies:
      - location: "station 0.15, between chine and sheer"
        type: "flat_spot"
        severity: "moderate"
        likely_cause: "Accumulated blend overlap from deadrise + flare adjustments"
        
      - location: "station 0.35, keel region"
        type: "kink"
        severity: "minor"
        likely_cause: "G1 blend insufficient for curvature rate"
        
  panel_quality:
    score: 0.82
    max_warp: 3.2°
    non_developable: 2
    assessment: "Good - minor warp in bow panels"
    
  degradation:
    since_synthesis: 0.15
    operations_since: 8
    trend: "declining"
    
  recommendation: |
    Geometry quality has degraded 15% since synthesis. Consider:
    - Resynthesize to restore fairness (recommended if continuing to edit bow)
    - Accept current quality (adequate for concept design)
    - Manually fair the flat spot at station 0.15
    
  impact:
    hydrodynamic: "~2% resistance increase due to unfairness"
    aesthetic: "Visible highlight irregularity in bow"
    production: "Panels still developable, minor fitting adjustment needed"
```

**Quality check in edit boundary policy:**

The geometry quality degradation should be included in the circuit breaker:

```python
@dataclass
class EditBoundaryPolicy:
    # ... existing fields ...
    
    # NEW: Quality degradation threshold
    max_quality_degradation: float = 0.25  # Allow 25% quality drop before forcing resynth
    
def check_edit_viability(self) -> EditViabilityResult:
    # ... existing checks ...
    
    # Check geometry quality degradation
    current_quality = compute_geometry_quality(current_geometry, baseline_quality)
    if current_quality.degradation_since_synthesis > self._policy.max_quality_degradation:
        return EditViabilityResult(
            viability=EditViability.WARN,
            warnings=[
                f"Geometry quality degraded {current_quality.degradation_since_synthesis:.0%}",
                f"Fairness: {current_quality.fairness_score:.0%} (was {baseline_quality.fairness_score:.0%})",
            ],
            recommendation="Consider resynthesis to restore surface quality"
        )
```

---

## 7. LLM Interaction Protocol

### 7.1 Request-Response Pattern

**LLM proposes (qualitative):**
```yaml
proposal:
  intent: "Improve engine room accessibility"
  target: "genset"
  desired_change: "move toward port side to create passage"
  # No distances - LLM doesn't guess
```

**System computes options:**
```yaml
options:
  - id: "opt_1"
    description: "Move genset 0.3m to port"
    result:
      passage_created: "0.45m along starboard side"
      clearance_to_engine: "0.45m (improved from 0.15m)"
    side_effects:
      - "Exhaust run increases 0.3m"
    feasibility: "recommended"
    
  - id: "opt_2"
    description: "Move genset 0.6m to port"
    result:
      passage_created: "0.75m along starboard side"
      clearance_to_engine: "0.75m (good)"
    side_effects:
      - "Exhaust run increases 0.6m"
      - "Genset now 0.2m from main engine (tight)"
    feasibility: "possible with tradeoffs"
    
  - id: "opt_3"
    description: "Move genset 0.8m to port (maximum)"
    result:
      passage_created: "0.95m along starboard side"
    side_effects:
      - "Blocked by main engine"
      - "Would require engine relocation first"
    feasibility: "not recommended"
    
  constraints_preventing_more:
    - "Main engine position is fixed (user constraint)"
    - "Minimum clearance to engine: 0.1m"
```

**LLM decides:**
```yaml
decision:
  selected: "opt_1"
  reasoning: |
    Option 1 provides adequate passage (0.45m) for service access
    while keeping side effects minimal. The 0.3m exhaust extension
    is acceptable. Option 2 would be better but creates a new 
    tight clearance with the main engine.
```

**System executes:**
```yaml
execution_result:
  success: true
  applied: "Move genset 0.3m to port"
  new_state:
    genset_position: "center-port of engine room"
    passage_starboard: "0.45m (new)"
    clearance_genset_engine: "0.45m (improved)"
  affected_systems:
    - "exhaust: rerouted (+0.3m length)"
```

### 7.2 Zoom Request Pattern

**LLM requests detail:**
```yaml
request:
  type: "zoom"
  target: "bow region"
  detail_level: "tertiary"  # Include minor anchors
```

**System provides:**
```yaml
bow_detail:
  anchors:
    - name: "keel" (primary)
    - name: "spray_rail_root" (tertiary, confidence: 0.7)
    - name: "primary_chine" (secondary)
    - name: "flare_inflection" (tertiary, confidence: 0.6)
    - name: "sheer" (primary)
    
  operations_available:
    - "adjust_deadrise:keel_to_spray_rail_root"
    - "adjust_deadrise:spray_rail_root_to_primary_chine"
    - "adjust_flare:primary_chine_to_flare_inflection"
    - "adjust_flare:flare_inflection_to_sheer"
    
  note: "Tertiary anchors (spray_rail_root, flare_inflection) have lower confidence. Operations on these segments may need confirmation."
```

---

## 8. Constraint & Conflict Schema

### 8.1 Constraint Types

```python
class ConstraintType(Enum):
    CLEARANCE = "clearance"        # Minimum distance between components
    ZONE_BOUND = "zone_bound"      # Must stay within zone
    STRUCTURAL = "structural"       # Load path, attachment point
    REGULATORY = "regulatory"       # Class rules, safety codes
    CONTINUITY = "continuity"       # G0/G1/G2 requirements
    CHARACTER = "character"         # Identity preservation
    USER = "user"                   # Explicit user constraint

@dataclass
class Constraint:
    """A constraint that limits what operations are possible."""
    constraint_id: str
    constraint_type: ConstraintType
    
    # What's constrained
    target_id: str  # Component or anchor UUID
    
    # The constraint
    description: str
    limit_value: Optional[float] = None
    limit_unit: str = ""
    
    # Source
    source: str = ""  # "IMO SOLAS II-1", "user", "detected", etc.
    
    # Enforcement
    hard: bool = True  # Hard = blocks operation, Soft = warning only
```

### 8.2 Conflict Reporting

When an operation would violate constraints:

```yaml
conflict_report:
  proposed_operation: "adjust_deadrise:keel_to_chine +10°"
  
  conflicts:
    - type: "clearance"
      description: "Engine room height reduced below minimum"
      current: "1.5m headroom"
      after_operation: "1.35m headroom"
      required: "1.4m (regulatory)"
      source: "ISO 11591"
      
    - type: "character"
      description: "Approaches character preservation limit"
      current_drift: 0.0
      after_operation_drift: 0.12
      soft_limit: 0.05
      hard_limit: 0.20
      
  resolution_options:
    - "Reduce deadrise change to +6° (stays within all constraints)"
    - "Accept character drift with explicit confirmation"
    - "Modify engine room floor to maintain headroom (requires structural change)"
    
  recommendation: "Reduce to +6° - achieves 60% of desired change within all constraints"
```

---

## 9. Implementation Roadmap

### Phase 1: Anchor Tracking Foundation
1. Implement `TrackedAnchor` and `AnchorTracker`
2. Implement anchor detection for basic hull types
3. Build anchor matching across geometry changes
4. Add LLM notification for anchor lifecycle events

### Phase 2: Continuity-Aware Operations
1. Implement continuity detection (`G0`/`G1`/`G2`)
2. Add transition types to operation templates
3. Implement blend functions
4. Test on hard chine vs round bilge hulls

### Phase 3: Anchor Hierarchy
1. Implement dominance classification
2. Add zoom interface for detail levels
3. Filter operations based on visible anchors
4. Test with noisy/scanned geometry

### Phase 4: Delta-Affordance System
1. Implement `MovementEnvelope` computation
2. Add operation affordances for hull geometry
3. Build constraint checking into affordance computation
4. Generate LLM-readable affordance summaries

### Phase 5: LLM Interface Polish
1. Implement qualitative description generator
2. Build augmented ASCII views
3. Implement option generation from proposals
4. Full request-response protocol

---

# PART II: PROGRAMMATIC DESIGN (10k+ Artifact Scale)

*For outfitting, systems, and full vessel completion via constraint programming.*

---

## 10. The Scale Problem

### 10.1 Why Direct Manipulation Fails at Scale

| Problem | Impact |
|---------|--------|
| **Observable Wall** | 10,000 artifacts = information entropy. LLM can't hold or navigate scene graph. |
| **Affordance Explosion** | 10,000 artifacts × 5 operations = 50,000 choices. Unnavigable action space. |
| **Control Plane Blindness** | LLM sees "resistance +2%" but can't attribute to which of 10,000 artifacts caused it. |
| **Granularity Trap** | "Make engine room bigger" requires 500 individual artifact operations. |

### 10.2 The Solution: Compilation, Not Manipulation

The LLM doesn't edit 10,000 artifacts. It writes **constraint programs** that compile to 10,000 artifacts.

```
Direct manipulation: 10,000 artifacts × 5 operations = 50,000 choices (impossible)
Constraint programming: ~50 statements → compile → 10,000 artifacts (tractable)
```

---

## 11. The Design Language (DSL)

### 11.1 The Universal Modifier

Instead of 10,000 tools for 10,000 artifacts, every artifact inherits from a generic schema.

**Enumerative (wrong):**
```python
move_engine()
resize_fuel_tank()
adjust_chine_angle()
# ... 9,997 more
```

**Non-enumerative (correct):**
```python
modify(target_id, attribute_path, value)
```

The LLM queries the schema for any object, sees its properties, and issues a `PATCH`. The action space is always size = 1.

### 11.2 Constraint Program Syntax

The LLM writes high-level statements that the kernel compiles to geometry:

```sql
-- High-level intent (LLM writes this)
SET hull.style = "sportfish_broken_sheer"
SET hull.loa = 72ft
SET hull.beam = 20ft

SET zone.engine_room.length = 4m
SET zone.engine_room.position = aft

SET system.fuel.capacity = 1200L
SET system.propulsion.type = "twin_diesel_inboard"
SET system.propulsion.target_speed = 40kts

CONSTRAIN clearance.main_engine.all_sides >= 0.6m
CONSTRAIN stability.gm_min >= 0.5m
CONSTRAIN weight.total <= 45000kg

RUN PHASE "arrangement"
RUN PHASE "structural"
RUN PHASE "routing"
RUN PHASE "physics"
```

**Six SET statements + three CONSTRAINTs** control thousands of artifacts. The kernel expands each statement:

| Statement | Compiled Artifacts |
|-----------|-------------------|
| `SET zone.engine_room.length = 4m` | 2 bulkheads, 12 foundations, 47 brackets |
| `SET system.fuel.capacity = 1200L` | 2 tanks, 15 pipe segments, 8 fittings, 3 vents |
| `CONSTRAIN clearance.main_engine >= 0.6m` | Validation rule applied to ~30 adjacent artifacts |

### 11.3 Program Synthesis from Intent

The LLM doesn't pick from menus. It **synthesizes** programs from latent knowledge:

```python
# LLM synthesizes this on the fly, not picked from a list
hull = HullSynthesizer.from_archetype("sportfish", loa=72)

tower = Assembly(type="tuna_tower")
tower.attach_to(hull.hardtop)

engines = PropulsionPlant(model="MTU_2000_V16")
engines.place_in(hull.zones.engine_room)

fuel = FuelSystem(capacity=1200, tank_count=2)
fuel.distribute_in(hull.zones.engine_room, bias="aft")
```

The LLM composes from primitives and constraints, not enumerating pre-built options.

### 11.4 Constraint Program Validation (Pre-Compilation Check)

Multi-statement programs might be individually valid but **jointly unsatisfiable**. The system must detect this **before** expensive compilation.

```python
@dataclass
class ConstraintConflict:
    """Two or more constraints that cannot be simultaneously satisfied."""
    constraints: List[str]
    conflict_type: str  # "contradictory", "overconstrained", "circular"
    explanation: str
    resolution_options: List[str]

@dataclass
class ProgramValidationResult:
    """Result of pre-compilation constraint validation."""
    valid: bool
    
    # If invalid
    conflicts: List[ConstraintConflict] = field(default_factory=list)
    
    # Warnings (valid but risky)
    warnings: List[str] = field(default_factory=list)
    
    # Suggestions
    suggested_modifications: List[str] = field(default_factory=list)

def validate_constraint_program(
    statements: List["Statement"],
    current_state: "DesignState",
) -> ProgramValidationResult:
    """
    Check if constraint program is internally consistent
    BEFORE expensive compilation.
    
    This is EXACT logical validation, not approximate physics.
    """
    conflicts = []
    warnings = []
    
    # Extract all constraints
    constraints = [s for s in statements if s.type == "CONSTRAIN"]
    sets = [s for s in statements if s.type == "SET"]
    
    # Check for direct contradictions
    # e.g., "speed >= 60kts" AND "hull.type = displacement"
    for c1, c2 in combinations(constraints, 2):
        if is_contradictory(c1, c2):
            conflicts.append(ConstraintConflict(
                constraints=[str(c1), str(c2)],
                conflict_type="contradictory",
                explanation=f"{c1} and {c2} cannot both be satisfied",
                resolution_options=["Remove one constraint", "Relax targets"],
            ))
    
    # Check for overconstrained systems
    # e.g., SET loa=72ft AND SET displacement=X AND SET speed=Y where X,Y are incompatible at 72ft
    degrees_of_freedom = count_degrees_of_freedom(sets)
    constraint_count = len(constraints)
    if constraint_count > degrees_of_freedom:
        warnings.append(
            f"System may be overconstrained: {constraint_count} constraints "
            f"vs {degrees_of_freedom} degrees of freedom"
        )
    
    # Check for known-infeasible combinations
    # e.g., planing hull + 2000nm range (known to require displacement hull)
    known_conflicts = check_known_infeasible_combinations(statements)
    conflicts.extend(known_conflicts)
    
    # Check SET values against archetype bounds
    archetype = extract_archetype(statements)
    if archetype:
        for s in sets:
            if not within_archetype_bounds(s, archetype):
                warnings.append(
                    f"{s} is outside typical {archetype.name} bounds"
                )
    
    if conflicts:
        return ProgramValidationResult(
            valid=False,
            conflicts=conflicts,
            suggested_modifications=generate_conflict_resolutions(conflicts),
        )
    
    return ProgramValidationResult(
        valid=True,
        warnings=warnings,
    )
```

**Example: Detecting Unsatisfiable Program**

```yaml
# LLM writes:
program:
  - SET hull.type = "planing"
  - SET system.propulsion.target_speed = 60kts
  - CONSTRAIN range >= 2000nm
  - CONSTRAIN weight.total <= 35000kg

# Pre-compilation validation detects:
validation_result:
  valid: false
  
  conflicts:
    - constraints:
        - "hull.type = planing"
        - "CONSTRAIN range >= 2000nm"
      conflict_type: "contradictory"
      explanation: |
        2000nm range requires ~8000L fuel capacity.
        At 0.85 kg/L, fuel alone weighs 6800kg.
        Combined with structure and systems, displacement exceeds planing threshold.
        Planing hulls cannot achieve 2000nm range.
      resolution_options:
        - "Change to displacement hull (achieves range, loses speed)"
        - "Reduce range requirement to ~500nm (maintains planing)"
        - "Specify as negotiation (let system find Pareto front)"

# LLM can fix before expensive compilation attempt:
revised_program:
  - SET hull.type = "planing"
  - SET system.propulsion.target_speed = 60kts
  - CONSTRAIN range >= 400nm  # Reduced to feasible for planing
  - CONSTRAIN weight.total <= 35000kg
```

**Key Distinction: This is NOT speculative physics**

| Speculative Physics (Wrong) | Constraint Validation (Correct) |
|----------------------------|--------------------------------|
| Approximate GM calculation | Exact logical consistency check |
| "Probably won't float" | "These constraints contradict by definition" |
| May have false positives/negatives | Authoritative yes/no |
| Physics approximation | Constraint satisfaction |

Constraint validation catches **logically impossible** programs before compilation. It doesn't approximate whether the result will pass physics—that's what actual physics validation does after compilation.

---

## 12. Procedural Generators

### 12.1 The Expansion Model

The 10,000 artifacts come from **deterministic generators** that the LLM parameterizes:

| Generator | LLM Provides | System Produces |
|-----------|--------------|-----------------|
| `ScantlingGenerator` | "Frame spacing 500mm, plate 6mm" | 200 frames, 150 plates, 1000 brackets |
| `ArrangementGenerator` | "Engine room aft, 4m × 4m" | Zone bounds, bulkhead positions, access paths |
| `RoutingAgent` | "Connect fuel tanks to engine" | 15 pipe segments, 8 fittings, 3 penetrations |
| `OutfittingGenerator` | "Twin 500hp diesels" | Engines, mounts, foundations, exhaust runs |
| `ElectricalGenerator` | "Shore power + genset backup" | Panels, cables, breakers, bonding |

### 12.2 Autonomous Subsystems

Generators handle complexity internally. They escalate only when stuck:

```python
class RoutingAgent:
    """Autonomous pipe/cable routing with internal conflict resolution."""
    
    def route(self, start: str, end: str, medium: str) -> RoutingResult:
        """
        Attempts routing with progressive constraint relaxation.
        Only escalates if all attempts fail.
        """
        attempts = [
            {"bend_radius": 3.0, "max_length": 1.5},  # Strict
            {"bend_radius": 2.5, "max_length": 2.0},  # Relaxed
            {"bend_radius": 2.0, "max_length": 3.0},  # Minimum viable
        ]
        
        for params in attempts:
            result = self._attempt_route(start, end, medium, params)
            if result.success:
                return result
        
        # All attempts failed - escalate to LLM
        return RoutingResult(
            success=False,
            escalation_required=True,
            message="Cannot route within any viable parameters",
            blocking_artifacts=self._identify_blockers(),
            suggested_resolutions=[
                "Move start component 0.3m forward",
                "Relocate interfering stiffener",
                "Accept longer route through adjacent zone",
            ]
        )
```

### 12.3 Conflict Resolution Hierarchy

```
Level 1: Generator solves internally (no LLM involvement)
         ↓ if stuck
Level 2: Generator relaxes constraints, retries (no LLM involvement)
         ↓ if still stuck
Level 3: Generator escalates with options (LLM picks)
         ↓ if options unacceptable
Level 4: LLM modifies zone/arrangement constraints (LLM writes new program)
```

The LLM only intervenes when autonomous systems exhaust their options.

---

## 13. Hierarchical Operations

### 13.1 First-Class Semantic Entities

Zones, systems, and assemblies are **operable entities**, not just groupings:

```python
@dataclass
class Zone:
    """A zone is a first-class entity that can be operated on directly."""
    zone_id: str
    name: str
    bounds: BoundingBox
    parent_zone: Optional[str] = None
    
    # Containment (auto-maintained)
    contained_artifacts: List[str] = field(default_factory=list)
    
    # Constraints
    min_volume_m3: Optional[float] = None
    required_access: List[str] = field(default_factory=list)
    
    def expand(self, direction: str, amount: float) -> "ZoneExpansionPlan":
        """
        Expanding a zone propagates to all contained artifacts.
        Returns a plan, doesn't execute directly.
        """
        # System computes what this means for contained artifacts
        ...

@dataclass
class ZoneExpansionPlan:
    """What happens when a zone expands."""
    zone_id: str
    direction: str
    amount: float
    
    # Computed effects
    affected_artifacts: List[str]
    artifact_relocations: Dict[str, Vector3]
    bulkhead_moves: List[str]
    penetration_relocations: List[str]
    route_extensions: List[str]
    
    # Conflicts
    conflicts: List[Conflict]
    blocked_by: Optional[str] = None  # e.g., "galley_zone" if expansion conflicts
    
    # Summary for LLM
    summary: str = ""  # "Affects 47 artifacts, extends 3 pipe runs, conflicts with galley"
```

### 13.2 Operation Propagation

```yaml
# LLM says:
action: "Expand engine room forward by 0.5m"

# System computes:
expansion_plan:
  zone: "engine_room"
  direction: "forward"
  amount: 0.5m
  
  propagation:
    bulkheads:
      - "bulkhead_12: relocate to frame 42"
    foundations:
      - "foundation_4 through foundation_15: shift forward 0.5m"
    penetrations:
      - "pen_fuel_supply: relocate"
      - "pen_exhaust: relocate"
    routes:
      - "fuel_supply_run: extend 0.5m"
      - "exhaust_run: extend 0.5m"
      - "electrical_main: extend 0.5m"
      
  affected_artifact_count: 47
  
  conflicts:
    - type: "zone_overlap"
      description: "Galley zone shrinks by 0.5m"
      severity: "warning"
      resolution: "Acceptable if galley remains > 8m²"
      
  summary: "47 artifacts relocate, 3 routes extend, galley shrinks 0.5m"

# LLM decides:
decision: "Accept - galley at 8.5m² after change is acceptable"
```

The LLM operates on "engine room", not on 47 individual artifacts.

---

## 14. Query Interface (Not View)

### 14.1 The Problem with Views

Showing an LLM a 10,000-node scene graph is noise. Even summarized, it's too much to reason about.

### 14.2 Spatial Query Language

The LLM **asks questions** instead of **inspecting trees**:

```sql
-- "What's near the fuel pump?"
SELECT id, type, distance_m 
FROM artifacts 
WHERE distance_to("fuel_pump_1") < 0.5
ORDER BY distance_m

-- Result: 3 items
-- bracket_4921: 0.12m
-- pipe_run_17: 0.28m  
-- stiffener_42: 0.41m
```

```sql
-- "What's blocking the engine room passage?"
SELECT id, type, clearance_m
FROM artifacts
WHERE zone = "engine_room"
  AND tags CONTAINS "passage_obstruction"
  AND clearance_to("passage_centerline") < 0.6

-- Result: 2 items
-- genset: clearance 0.15m
-- fuel_tank_2: clearance 0.42m
```

```sql
-- "Which zone is most space-constrained?"
SELECT zone_id, utilization_pct, free_volume_m3
FROM zones
ORDER BY utilization_pct DESC
LIMIT 3

-- Result:
-- engine_room: 87% utilized, 2.1m³ free
-- lazarette: 82% utilized, 0.8m³ free
-- cabin_fwd: 71% utilized, 4.2m³ free
```

### 14.3 Query-Driven Workflow

```
LLM: "I need to improve access to the main engine"

System: [runs spatial queries internally]
        "Current clearance analysis:
         - Forward: 0.4m (insufficient for filter service)
         - Aft: 0.8m (adequate)
         - Port: 0.6m (adequate)
         - Starboard: 0.15m (blocked by genset)"

LLM: "What's blocking starboard access?"

System: [query: artifacts within 0.3m of engine starboard face]
        "Genset (0.15m), fuel_tank_2 (0.28m)"

LLM: "Can the genset move?"

System: [query: genset movement envelope]
        "Genset can move:
         - 0.8m to port (blocked by main engine)
         - 0.2m to starboard (blocked by fuel tank)
         - 0.4m forward (blocked by bulkhead)
         - 0.1m aft (blocked by transom)"

LLM: "Move genset 0.6m to port to create passage"

System: [computes plan, returns options]
```

The LLM never holds 10,000 items. It holds a **working set** of ~5-10 items relevant to the current task.

---

## 15. Physics Attribution

### 15.1 The Problem

When physics fails (GM too low, trim excessive), the LLM needs to know **which decisions caused it**, not which of 10,000 artifacts.

### 15.2 Decision-Level Attribution

```python
@dataclass
class PhysicsResult:
    """Physics outcome with decision-level attribution."""
    
    # The metric
    metric: str  # "gm_m", "trim_deg", "resistance_kn"
    value: float
    required: Optional[float] = None
    status: str = "ok"  # "ok", "warning", "failed"
    
    # Attribution to LLM decisions (not artifacts)
    attribution: List[Attribution] = field(default_factory=list)
    
    # Suggested remedies (in LLM-actionable terms)
    remedies: List[str] = field(default_factory=list)

@dataclass
class Attribution:
    """How much a decision contributed to a physics outcome."""
    decision: str           # "Engine room moved aft 0.5m"
    decision_id: str        # Reference to the program statement
    effect: str             # "+0.08m VCG"
    contribution_pct: float # 65%
```

### 15.3 Attribution Example

```yaml
physics_result:
  metric: "stability.gm_m"
  value: 0.42
  required: 0.50
  status: "failed"
  
  attribution:
    - decision: "Engine room zone moved aft 0.5m"
      statement: "SET zone.engine_room.position = aft"
      effect: "+0.08m VCG (weight concentration aft)"
      contribution: 65%
      
    - decision: "Fuel capacity increased to 1200L"
      statement: "SET system.fuel.capacity = 1200L"
      effect: "+0.03m VCG (tank height)"
      contribution: 25%
      
    - decision: "Tuna tower added"
      statement: "ADD system.fishing_gear(tower=True)"
      effect: "+0.02m VCG (elevated weight)"
      contribution: 10%
      
  remedies:
    - "Add 2t ballast at keel (CONSTRAIN ballast.keel >= 2000kg)"
    - "Reduce fuel capacity to 1000L"
    - "Move engine room forward 0.3m"
    - "Lower tuna tower mounting point"
    
  recommendation: "Add ballast - preserves range and layout while restoring GM"
```

The LLM sees: "My decision to move the engine room aft caused 65% of the stability problem." It can reason about tradeoffs.

---

## 16. Latent Archetypal Knowledge

### 16.1 The Viking Test

When the user says "Viking 72 sportfish", the LLM taps into **latent archetypal knowledge**:

- Aggressive "broken" sheer line
- High-performance deadrise (~12° at transom)
- Mezzanine seating layout
- Massive engine requirements (twin MTU 2000s)
- Tuna tower and outriggers
- Fuel-heavy for offshore range

This knowledge doesn't come from a database. It's **latent in the LLM's training**.

### 16.2 Latent-to-Parametric Mapping

```yaml
# User says:
"Create a 72ft Viking sportfish"

# LLM's latent knowledge activates:
archetype: "Viking sportfish"
characteristics:
  - aggressive_sheer: true
  - high_performance: true
  - offshore_capable: true
  - fishing_optimized: true

# LLM synthesizes a Design Program:
program: |
  SET hull.archetype = "sportfish_broken_sheer"
  SET hull.loa = 72ft
  SET hull.beam = 20ft
  SET hull.deadrise_transom = 12deg
  
  SET zone.cockpit.type = "fishing"
  SET zone.cockpit.features = ["mezzanine", "fighting_chair", "bait_station"]
  
  SET system.propulsion.type = "twin_diesel_inboard"
  SET system.propulsion.model_hint = "MTU_2000_class"
  SET system.propulsion.target_speed = 40kts
  
  SET system.fishing.tower = true
  SET system.fishing.outriggers = true
  
  SET system.fuel.capacity = 1500L  # Offshore range
  SET system.fuel.distribution = "aft_bias"  # Vikings carry fuel aft
  
  CONSTRAIN stability.gm_min >= 0.5m
  CONSTRAIN performance.speed_loaded >= 35kts
  
  RUN PHASE "all"
```

### 16.3 Archetypal Priming vs Procedural Expansion

| Stage | What Happens | Who Does It |
|-------|--------------|-------------|
| **Intent** | "Viking 72" | User |
| **Archetypal Priming** | Set style, performance targets, general arrangement | LLM (latent knowledge) |
| **Procedural Expansion** | Generate 2000 frames, route 3000 cables, place 500 fittings | System (generators) |
| **Validation** | Check physics, flag violations | System (validators) |
| **Attribution** | "GM low because fuel is too high" | System (instrumented cascade) |
| **Correction** | "Move fuel tanks down" or "add ballast" | LLM (informed by attribution) |

The LLM provides **strategy** (Viking-ness). The system provides **tactics** (10,000 artifacts).

---

## 17. Constraint-Driven Evolution

### 17.1 Objectives, Not Operations

To avoid enumerating "how to reduce weight", the LLM sets **objectives**:

```sql
-- Instead of picking weight-reduction operations:
GOAL weight.total < 45000kg
PRIORITY high

-- The system finds solutions:
RUN OPTIMIZE
```

The system uses deterministic solvers to adjust the 10,000 artifacts until the constraint is met.

### 17.2 Gradient-Based Steering

```python
@dataclass
class Objective:
    """A goal the system should optimize toward."""
    metric: str           # "weight.total", "stability.gm", "performance.speed"
    operator: str         # "<", ">", "==", "maximize", "minimize"
    target: Optional[float] = None
    priority: str = "medium"  # "low", "medium", "high", "critical"

@dataclass
class OptimizationResult:
    """Result of constraint-driven optimization."""
    objectives_met: List[str]
    objectives_failed: List[str]
    
    # What changed
    parameter_changes: Dict[str, tuple]  # param -> (old, new)
    
    # Tradeoffs made
    tradeoffs: List[str]
    
    # If failed, why
    blocking_constraints: List[str]
    relaxation_suggestions: List[str]
```

### 17.3 Example: Range vs Weight Tradeoff

```yaml
# LLM sets objectives:
objectives:
  - metric: "performance.range_nm"
    operator: ">="
    target: 500
    priority: "high"
    
  - metric: "weight.total"
    operator: "<="
    target: 45000kg
    priority: "medium"

# System optimizes:
optimization_result:
  status: "partial"
  
  objectives_met:
    - "weight.total: 44,800kg (under 45,000kg limit)"
    
  objectives_failed:
    - "performance.range_nm: 420nm (below 500nm target)"
    
  tradeoffs:
    - "Fuel reduced from 1500L to 1100L to meet weight target"
    - "Range reduced 80nm as consequence"
    
  suggestions:
    - "Relax weight limit to 47,000kg to achieve 500nm range"
    - "Accept 420nm range to maintain weight"
    - "Upgrade to lighter engine (reduces weight 800kg, adds cost)"
    
# LLM decides:
decision: "Relax weight to 47,000kg - range is critical for offshore fishing"
```

---

## 18. Failure Recovery Protocol

### 18.1 Escalation Levels

```
Level 0: Success - no intervention needed
         ↓
Level 1: Generator self-corrects (constraint relaxation)
         ↓
Level 2: Generator escalates with options (LLM picks)
         ↓
Level 3: Physics fails - LLM receives attribution + remedies
         ↓
Level 4: Constraint conflict - LLM must relax or reprioritize
         ↓
Level 5: Fundamental infeasibility - LLM must change requirements
```

### 18.2 Structured Failure Reports

```yaml
failure_report:
  level: 3
  phase: "physics.stability"
  
  failure:
    metric: "gm_m"
    value: 0.42
    required: 0.50
    
  attribution:
    primary: "Engine room position aft (65%)"
    secondary: "Fuel capacity increase (25%)"
    tertiary: "Tuna tower weight (10%)"
    
  remedies:
    - action: "Add ballast"
      command: "CONSTRAIN ballast.keel >= 2000kg"
      effect: "GM +0.12m"
      tradeoff: "Weight +2000kg, draft +0.05m"
      
    - action: "Move engine room forward"
      command: "SET zone.engine_room.position = midship"
      effect: "GM +0.08m"
      tradeoff: "Cockpit space reduced 0.5m"
      
    - action: "Reduce fuel"
      command: "SET system.fuel.capacity = 1000L"
      effect: "GM +0.04m"
      tradeoff: "Range reduced 100nm"
      
  recommendation: "Add ballast (least impact on design intent)"
  
  llm_action_required: "Select remedy or propose alternative"
```

---

## 19. Complete Workflow Example

### 19.1 The Viking Test End-to-End

**User Input:**
```
"Create a 72ft Viking-style sportfish. Needs to do 40 knots and have 500nm range."
```

**Step 1: LLM Archetypal Priming**
```sql
-- LLM synthesizes from latent knowledge
SET hull.archetype = "sportfish_broken_sheer"
SET hull.loa = 72ft
SET hull.beam = 20ft
SET hull.deadrise_transom = 12deg

SET zone.engine_room.position = aft
SET zone.cockpit.type = "fishing_mezzanine"

SET system.propulsion = "twin_diesel_inboard"
SET system.propulsion.target_speed = 40kts
SET system.fuel.capacity = 1800L  -- estimated for 500nm
SET system.fishing.tower = true

CONSTRAIN stability.gm_min >= 0.5m
CONSTRAIN performance.speed >= 40kts
CONSTRAIN performance.range >= 500nm

RUN PHASE "all"
```

**Step 2: System Procedural Expansion**
```yaml
expansion_report:
  hull: "Generated from sportfish template"
  structural:
    frames: 187
    plates: 156
    stiffeners: 423
    brackets: 892
  systems:
    propulsion: 47 components
    fuel: 38 components
    electrical: 124 components
    fishing: 67 components
  total_artifacts: 2,847
  
  phase_status:
    arrangement: "complete"
    structural: "complete"
    routing: "complete - 3 routes required relaxed bend radius"
    physics: "FAILED"
```

**Step 3: Physics Failure with Attribution**
```yaml
physics_failure:
  metric: "stability.gm_m"
  value: 0.38
  required: 0.50
  
  attribution:
    - "Fuel tanks at 1800L mounted high (55%)"
    - "Tuna tower weight (25%)"
    - "Engine room aft position (20%)"
    
  remedies:
    - "Lower fuel tank mounting (-0.3m Z)"
    - "Add 3t keel ballast"
    - "Reduce fuel to 1400L (range drops to 400nm)"
```

**Step 4: LLM Corrective Action**
```sql
-- LLM reasons: "Lower tanks + ballast preserves range"
SET system.fuel.tank_z_offset = -0.3m
CONSTRAIN ballast.keel >= 2500kg

RUN PHASE "physics"
```

**Step 5: Success**
```yaml
physics_result:
  stability.gm_m: 0.54  # Now passing
  performance.speed: 41.2kts
  performance.range: 485nm  # Slightly under due to ballast weight
  
  warnings:
    - "Range 485nm vs 500nm target (97%)"
    
  llm_options:
    - "Accept 485nm (within 3% of target)"
    - "Reduce ballast 500kg, accept GM 0.51m"
    - "Increase fuel 5% to compensate"
```

**Step 6: LLM Acceptance**
```
LLM: "Accept 485nm range - within acceptable margin for offshore operation"
```

**Final Result:**
- 2,847 artifacts generated
- Physics-validated vessel
- LLM wrote ~15 statements total
- System handled all geometric complexity

---

## 20. Implementation Roadmap

### Part I Phases (Hull Shaping)

**Phase 1: Anchor Tracking Foundation**
1. Implement `TrackedAnchor` and `AnchorTracker`
2. Implement anchor detection for basic hull types
3. Build anchor matching across geometry changes
4. Add LLM notification for anchor lifecycle events

**Phase 2: Continuity-Aware Operations**
1. Implement continuity detection (`G0`/`G1`/`G2`)
2. Add transition types to operation templates
3. Implement blend functions
4. Test on hard chine vs round bilge hulls

**Phase 3: Anchor Hierarchy**
1. Implement dominance classification
2. Add zoom interface for detail levels
3. Filter operations based on visible anchors
4. Test with noisy/scanned geometry

**Phase 4: Delta-Affordance System**
1. Implement `MovementEnvelope` computation
2. Add operation affordances for hull geometry
3. Build constraint checking into affordance computation
4. Generate LLM-readable affordance summaries

**Phase 5: LLM Interface Polish**
1. Implement qualitative description generator
2. Build augmented ASCII views
3. Implement option generation from proposals
4. Full request-response protocol

### Part II Phases (Programmatic Design)

**Phase 6: Design Language Core**
1. Implement DSL parser for SET/CONSTRAIN/RUN statements
2. Build universal modifier (`modify(target, path, value)`)
3. Implement statement → artifact expansion
4. Add program validation and error reporting

**Phase 7: Procedural Generators**
1. Implement `ScantlingGenerator` (frames, plates, brackets)
2. Implement `ArrangementGenerator` (zones, bulkheads)
3. Implement `RoutingAgent` with autonomous retry
4. Implement `OutfittingGenerator` for major systems

**Phase 8: Hierarchical Operations**
1. Implement Zone as first-class entity
2. Build operation propagation (zone change → artifact changes)
3. Implement Assembly grouping
4. Add System-level operations

**Phase 9: Query Interface**
1. Implement spatial query language
2. Build working-set management
3. Add query result formatting for LLM consumption
4. Implement progressive disclosure (zoom)

**Phase 10: Physics Attribution**
1. Instrument physics cascade with decision tracking
2. Implement `Attribution` data structure
3. Build remedy suggestion engine
4. Add optimization with constraint priorities

**Phase 11: Integration**
1. Connect hull shaping (Part I) to programmatic design (Part II)
2. Implement full Viking Test workflow
3. Add failure recovery protocol
4. Performance optimization for 10k+ artifacts

---

# PART III: THEORETICAL FOUNDATIONS

*The "Why-Logic" that enables autonomous design resolution.*

---

## 21. Negotiation Protocol (The Trade-off Engine)

### 21.1 The Problem: Physically Null States

In naval architecture, you never get something for nothing. The "Impossible Triangle" (Speed, Range, Weight) means that if the LLM asks for a "Viking 72" that does 60 knots with a 2,000nm range, it has entered a **Physically Null State** — no valid design exists.

Returning an error is insufficient. The system must help the LLM understand **what IS possible**.

### 21.2 Constraint Priority Schema

Every constraint has a priority that determines relaxation order:

```python
class ConstraintPriority(Enum):
    SAFETY = "safety"        # Never relax (stability, structural)
    REGULATORY = "regulatory"  # Relax only with explicit waiver
    CRITICAL = "critical"    # User's primary intent
    HIGH = "high"            # User's secondary intent
    MEDIUM = "medium"        # Nice to have
    LOW = "low"              # Soft preference
    DERIVED = "derived"      # Computed from other constraints

@dataclass
class PrioritizedConstraint:
    constraint_id: str
    metric: str              # "speed_kts", "range_nm", "gm_m"
    operator: str            # ">=", "<=", "=="
    target: float
    priority: ConstraintPriority
    source: str              # "user_explicit", "archetype", "regulation"
    relaxable: bool = True   # False for safety constraints
    
    # Relaxation bounds (if relaxable)
    min_acceptable: Optional[float] = None
    max_acceptable: Optional[float] = None
```

### 21.3 Pareto Front Generation

When constraints conflict, the system generates a **trade-off menu**:

```python
@dataclass
class TradeoffOption:
    option_id: str
    name: str                          # "Prioritize Speed", "Balanced", etc.
    achieved_values: Dict[str, float]  # metric -> achieved value
    sacrifices: List[str]              # What was given up
    side_effects: List[str]            # Consequences
    archetype_drift: float             # How far from original intent

@dataclass
class NegotiationResult:
    status: str                        # "satisfied", "negotiation_required", "infeasible"
    
    # If satisfied
    solution: Optional["DesignState"] = None
    
    # If negotiation required
    conflict_description: str = ""
    conflicting_constraints: List[str] = field(default_factory=list)
    pareto_front: List[TradeoffOption] = field(default_factory=list)
    
    # Explanation
    why_conflict: str = ""             # "Displacement-to-length ratio at hydrodynamic limit"
    physical_limit: str = ""           # The fundamental constraint preventing satisfaction

def generate_pareto_front(
    constraints: List[PrioritizedConstraint],
    design_space: "DesignSpace",
    num_samples: int = 100,
) -> List[TradeoffOption]:
    """
    Multi-objective optimization to find the achievable frontier.
    Returns discrete options along the Pareto front.
    """
    # Run MOO (e.g., NSGA-II) across relaxable constraints
    # Cluster results into human-interpretable options
    # Label each option by which constraint it prioritizes
    ...
```

### 21.4 Negotiation Workflow

```yaml
# User intent:
constraints:
  - metric: "speed_kts"
    target: 60
    priority: "critical"
  - metric: "range_nm"
    target: 2000
    priority: "high"

# System detects conflict:
negotiation_result:
  status: "negotiation_required"
  
  conflict_description: "Cannot satisfy 60kts AND 2000nm range simultaneously"
  
  why_conflict: |
    60kts requires planing hull with low displacement.
    2000nm requires 8000L fuel capacity.
    Fuel weight pushes displacement beyond planing threshold.
    
  physical_limit: "Planing hull displacement limit: 35,000kg. Required for 2000nm: 52,000kg."
  
  pareto_front:
    - option_id: "speed_priority"
      name: "Prioritize Speed"
      achieved_values:
        speed_kts: 60
        range_nm: 380
      sacrifices:
        - "Range reduced 81% (2000nm → 380nm)"
      side_effects:
        - "Fuel capacity: 1200L"
        - "Offshore capability limited"
      archetype_drift: 0.15
      
    - option_id: "range_priority"
      name: "Prioritize Range"
      achieved_values:
        speed_kts: 28
        range_nm: 2000
      sacrifices:
        - "Speed reduced 53% (60kts → 28kts)"
      side_effects:
        - "Hull form changes to displacement (not planing)"
        - "No longer a 'sportfish' archetype"
      archetype_drift: 0.85  # Major departure
      
    - option_id: "balanced"
      name: "Viking Sweet Spot"
      achieved_values:
        speed_kts: 42
        range_nm: 550
      sacrifices:
        - "Speed reduced 30% (60kts → 42kts)"
        - "Range reduced 72% (2000nm → 550nm)"
      side_effects:
        - "Maintains sportfish archetype"
        - "Typical Viking performance envelope"
      archetype_drift: 0.05  # Closest to intent
      
  recommendation: "Option 'balanced' - closest to Viking archetype with viable tradeoffs"

# LLM decides:
decision:
  selected: "balanced"
  reasoning: "42kts and 550nm maintains the sportfish character. The user can refuel for longer trips."
```

### 21.5 Negotiation Grammar

The LLM can express priorities in the DSL:

```sql
-- Explicit priority
CONSTRAIN speed >= 40kts PRIORITY critical
CONSTRAIN range >= 500nm PRIORITY high

-- Relative priority
PREFER speed OVER range

-- Acceptable degradation
CONSTRAIN speed >= 40kts ACCEPT >= 35kts  -- Hard floor

-- Optimization target
MAXIMIZE speed SUBJECT TO range >= 400nm
```

### 21.6 Pareto Rejection Path

The LLM must be able to reject all Pareto options and request renegotiation. **Forcing selection from inadequate options leads to confabulation.**

```python
@dataclass
class NegotiationResponse:
    """LLM's response to a Pareto front."""
    
    action: str  # "select", "reject_all", "modify_constraints", "request_more_options"
    
    # If selecting
    selected_option_id: Optional[str] = None
    reasoning: str = ""
    
    # If rejecting all
    rejection_reason: Optional[str] = None
    unmet_requirement: Optional[str] = None
    
    # If modifying constraints
    constraint_modifications: List["ConstraintModification"] = field(default_factory=list)
    
    # If requesting more options
    exploration_direction: Optional[str] = None  # "more_speed", "more_range", "different_hull"

@dataclass
class ConstraintModification:
    """A proposed change to constraints for renegotiation."""
    constraint_id: str
    modification_type: str  # "relax", "tighten", "remove", "add"
    new_value: Optional[float] = None
    new_priority: Optional[str] = None

def handle_negotiation_response(
    response: NegotiationResponse,
    current_pareto: List[TradeoffOption],
    constraints: List[PrioritizedConstraint],
) -> "NegotiationResult":
    """Handle LLM's response to Pareto front."""
    
    if response.action == "select":
        option = find_option(current_pareto, response.selected_option_id)
        return NegotiationResult(
            status="resolved",
            selected_option=option,
            reasoning=response.reasoning,
        )
    
    elif response.action == "reject_all":
        # LLM found all options unacceptable
        return NegotiationResult(
            status="rejected",
            rejection_reason=response.rejection_reason,
            next_action="request_constraint_modification",
            prompt=f"None of the options meet your requirement for {response.unmet_requirement}. "
                   f"Would you like to modify your constraints or explore a different design approach?",
        )
    
    elif response.action == "modify_constraints":
        # Apply modifications and regenerate Pareto
        modified_constraints = apply_modifications(
            constraints, response.constraint_modifications
        )
        new_pareto = generate_pareto_front(modified_constraints)
        
        return NegotiationResult(
            status="renegotiating",
            new_pareto=new_pareto,
            modifications_applied=response.constraint_modifications,
        )
    
    elif response.action == "request_more_options":
        # Expand Pareto front in requested direction
        expanded_pareto = expand_pareto_front(
            current_pareto, 
            constraints,
            direction=response.exploration_direction,
        )
        
        return NegotiationResult(
            status="expanded",
            new_pareto=expanded_pareto,
            exploration_direction=response.exploration_direction,
        )
```

**LLM rejection workflow:**

```yaml
# System presents Pareto front:
pareto_front:
  options:
    - id: "speed_priority"
      speed: 60kts
      range: 380nm
      
    - id: "range_priority"
      speed: 28kts
      range: 2000nm
      
    - id: "balanced"
      speed: 42kts
      range: 550nm

# LLM rejects all:
negotiation_response:
  action: "reject_all"
  
  rejection_reason: |
    None of these options are acceptable. The customer specifically 
    requested offshore tournament fishing capability, which requires 
    BOTH 45+ knots to reach fishing grounds AND 600+ nm range for 
    multi-day trips.
    
  unmet_requirement: "simultaneous speed (45kts) and range (600nm)"

# System responds:
renegotiation_prompt:
  status: "rejected"
  
  acknowledgment: |
    I understand. The current hull form cannot achieve both 45kts and 600nm
    simultaneously due to the displacement-to-length ratio limit.
    
  options:
    - id: "relax_speed"
      description: "Accept 40kts (closest achievable with 600nm)"
      tradeoff: "5kts slower than requested"
      
    - id: "relax_range"
      description: "Accept 500nm (closest achievable with 45kts)"
      tradeoff: "100nm shorter than requested"
      
    - id: "change_archetype"
      description: "Switch to larger hull (78ft) that can achieve both"
      tradeoff: "Significant cost increase, different vessel class"
      
    - id: "add_capability"
      description: "Add midship fuel bladder for extended range missions"
      tradeoff: "Temporary range extension, reduced deck space when installed"
      
  request: "Which approach would you like to explore?"

# LLM selects new direction:
negotiation_response:
  action: "modify_constraints"
  
  constraint_modifications:
    - constraint_id: "speed_min"
      modification_type: "relax"
      new_value: 40  # Accept 40kts instead of 45kts
      
  reasoning: |
    40kts with 600nm range is acceptable. The 5kt reduction still allows
    reaching fishing grounds quickly, and the full range enables multi-day trips.

# System regenerates Pareto with relaxed constraint:
new_pareto_front:
  status: "resolved"
  
  achievable_solution:
    speed: 40kts
    range: 620nm
    note: "Slightly exceeds range target with relaxed speed constraint"
```

**Key principle:** The LLM is never forced to pick from inadequate options. It can always:
1. Reject and explain why
2. Modify constraints
3. Request different exploration directions
4. Escalate to user for guidance

---

## 22. Bootstrap Theory (The Archetypal Seed)

### 22.1 The Zero-to-One Problem

When the prompt is "Viking 72", where does the **first valid geometry** come from? The LLM can't start from nothing — it needs a topologically valid seed that captures the archetype.

### 22.2 Archetypes as Constraint Programs

An archetype isn't a template file — it's a **seed instruction set**:

```python
@dataclass
class Archetype:
    """A vessel archetype that seeds initial geometry."""
    
    archetype_id: str
    name: str                          # "Viking Sportfish"
    category: str                      # "sportfish", "trawler", "sailboat"
    
    # Topology selection
    hull_topology: str                 # "twin_chine_planing", "round_bilge_displacement"
    chine_count: int
    deck_levels: int
    
    # Parameter ranges (defines the "design space")
    parameter_ranges: Dict[str, tuple]  # param -> (min, max, default)
    
    # Heuristic seeding (primes the generators)
    weight_distribution_hint: str       # "aft_heavy", "balanced", "forward"
    typical_systems: List[str]          # ["twin_diesel", "tuna_tower", "outriggers"]
    
    # Aesthetic invariants (the "brand")
    required_features: Dict[str, Any]   # Must have
    forbidden_features: List[str]       # Must not have
    
    # Character signature (for drift detection)
    character_signature: "ArchetypeSignature"

VIKING_SPORTFISH = Archetype(
    archetype_id="viking_sportfish",
    name="Viking Sportfish",
    category="sportfish",
    
    hull_topology="twin_chine_high_flare_planing",
    chine_count=1,
    deck_levels=2,
    
    parameter_ranges={
        "loa_m": (18, 30, 22),
        "beam_m": (5, 7, 5.8),
        "deadrise_transom_deg": (10, 16, 12),
        "bow_flare_deg": (15, 25, 20),
        "sheer_break_position": (0.4, 0.6, 0.5),  # Fraction of LOA
    },
    
    weight_distribution_hint="aft_heavy",
    typical_systems=["twin_diesel_inboard", "tuna_tower", "outriggers", "mezzanine_seating"],
    
    required_features={
        "broken_sheer": True,
        "bow_flare_deg": ">= 15",
        "transom_style": "integrated_platform",
        "cockpit_type": "fishing",
    },
    forbidden_features=["plumb_bow", "displacement_hull", "sailplan"],
    
    character_signature=ArchetypeSignature(
        sheer_curvature_sign_change=True,
        entry_angle_range=(18, 28),
        flare_above_chine=True,
    ),
)
```

### 22.3 The Bootstrap Pipeline

```
"Viking 72"
     │
     ▼
┌─────────────────────────────────────────────────┐
│ 1. ARCHETYPE RESOLUTION                          │
│    "Viking" → VIKING_SPORTFISH archetype         │
│    "72" → loa_m = 21.9 (72ft)                   │
└─────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────┐
│ 2. TOPOLOGY SELECTION                            │
│    Select hull graph: twin_chine_high_flare      │
│    Initialize section count from LOA             │
│    Set anchor positions (keel, chine, sheer)    │
└─────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────┐
│ 3. PARAMETER SEEDING                             │
│    Apply archetype defaults:                     │
│      beam = 5.8m (scaled to LOA)                │
│      deadrise_transom = 12°                      │
│      bow_flare = 20°                            │
│      sheer_break = 0.5 LOA                      │
└─────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────┐
│ 4. HULL SYNTHESIS                                │
│    HullSynthesizer generates Class-A surface     │
│    Output: Valid NURBS with correct topology    │
└─────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────┐
│ 5. HEURISTIC OUTFITTING                          │
│    Prime generators with archetype hints:        │
│      - Engine room aft (weight_distribution)    │
│      - Twin diesel placeholders                  │
│      - Tuna tower attachment points             │
│    Output: Zone layout + system stubs           │
└─────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────┐
│ 6. VALIDATION                                    │
│    Check physics (floats on lines)               │
│    Check archetype compliance                    │
│    Output: Valid "Viking-shaped" baseline       │
└─────────────────────────────────────────────────┘
```

### 22.4 LLM Latent-to-Archetype Mapping

The LLM's latent knowledge helps select and parameterize the archetype:

```yaml
# LLM interpretation of "Viking 72 sportfish"
archetype_selection:
  base_archetype: "viking_sportfish"
  confidence: 0.95
  
  latent_knowledge_applied:
    - "Viking = aggressive aesthetics, high performance"
    - "Sportfish = fishing focus, large cockpit, tower"
    - "72ft = upper-mid range, twin MTU class engines"
    
  parameter_overrides:
    loa_m: 21.9  # 72ft
    # Other params use archetype defaults
    
  system_expectations:
    - "Twin diesel ~1800hp total"
    - "1200-1500L fuel for offshore range"
    - "Tuna tower with outriggers"
    - "Mezzanine seating in cockpit"
```

---

## 23. Lossless Abstraction (Sufficiency Matrix)

### 23.1 The Problem: Is the Summary Enough?

The LLM makes decisions from summaries without seeing 10,000 artifacts. How do we **guarantee** the summary contains enough information for correct decisions?

### 23.2 Decision-Observable Matrix

For each decision type, define the **required observables**:

```python
@dataclass
class DecisionRequirements:
    """What information is needed for a decision type."""
    decision_type: str
    required_observables: List[str]
    summary_sufficient: bool
    escalation_trigger: Optional[str] = None  # When to query for more

DECISION_REQUIREMENTS = {
    "global_arrangement": DecisionRequirements(
        decision_type="global_arrangement",
        required_observables=[
            "zone_volumes",
            "zone_adjacencies", 
            "lcg_m",
            "vcg_m",
            "total_weight_kg",
        ],
        summary_sufficient=True,
    ),
    
    "zone_resize": DecisionRequirements(
        decision_type="zone_resize",
        required_observables=[
            "zone_bounds",
            "adjacent_zone_bounds",
            "contained_artifact_count",
            "affected_penetrations",
        ],
        summary_sufficient=True,
    ),
    
    "component_relocation": DecisionRequirements(
        decision_type="component_relocation",
        required_observables=[
            "component_bounds",
            "movement_envelope",  # Delta-affordance
            "connected_routes",
            "clearances",
        ],
        summary_sufficient=True,  # If movement_envelope is provided
    ),
    
    "routing_decision": DecisionRequirements(
        decision_type="routing_decision",
        required_observables=[
            "start_point",
            "end_point",
            "obstacles_in_path",
            "bend_radius_constraints",
        ],
        summary_sufficient=False,  # System handles autonomously
        escalation_trigger="routing_agent_failure",
    ),
    
    "clash_resolution": DecisionRequirements(
        decision_type="clash_resolution",
        required_observables=[
            "clashing_artifacts",
            "clash_volume",
            "movement_options_for_each",
        ],
        summary_sufficient=False,  # Need specific geometry
        escalation_trigger="system_cannot_resolve",
    ),
    
    "stability_correction": DecisionRequirements(
        decision_type="stability_correction",
        required_observables=[
            "gm_m",
            "vcg_m",
            "weight_by_zone",
            "sensitivity_to_ballast",
            "sensitivity_to_weight_relocation",
        ],
        summary_sufficient=True,
    ),
}
```

### 23.3 Sufficiency Checking

Before presenting a decision to the LLM, verify sufficiency:

```python
def check_decision_sufficiency(
    decision_type: str,
    available_observables: Set[str],
) -> "SufficiencyResult":
    """Verify the LLM has enough information to decide."""
    
    requirements = DECISION_REQUIREMENTS.get(decision_type)
    if not requirements:
        return SufficiencyResult(sufficient=False, reason="Unknown decision type")
    
    missing = set(requirements.required_observables) - available_observables
    
    if missing:
        return SufficiencyResult(
            sufficient=False,
            missing_observables=list(missing),
            action="Query for missing observables or delegate to system",
        )
    
    if not requirements.summary_sufficient:
        return SufficiencyResult(
            sufficient=False,
            reason="Decision type requires system-level handling",
            action="Delegate to autonomous subsystem",
        )
    
    return SufficiencyResult(sufficient=True)
```

### 23.4 Escalation Protocol

When summary is insufficient:

```yaml
# LLM attempts decision without sufficient info:
decision_attempt:
  type: "clash_resolution"
  target: "pipe_run_17 clashes with stiffener_42"
  
# System checks sufficiency:
sufficiency_check:
  sufficient: false
  reason: "Clash resolution requires specific geometry"
  
# System response:
escalation:
  action: "delegate_to_system"
  message: |
    This clash requires geometric analysis. The RoutingAgent will attempt 
    automatic resolution. I'll report back if it fails and needs your input.
    
# RoutingAgent attempts fix:
autonomous_attempt:
  success: true
  resolution: "Rerouted pipe_run_17 via alternate path (+0.3m length)"
  
# Only escalate if autonomous resolution fails:
# (LLM never needed to see stiffener_42's exact coordinates)
```

### 23.5 Observable Completeness Guarantee

```python
@dataclass
class StateLensView:
    """The view provided to the LLM."""
    
    # What's included
    observables: Dict[str, Any]
    
    # Completeness metadata
    decision_types_supported: List[str]
    decision_types_insufficient: List[str]
    
    def can_decide(self, decision_type: str) -> bool:
        return decision_type in self.decision_types_supported

def generate_state_lens_view(
    state: "DesignState",
    context: "TaskContext",
) -> StateLensView:
    """Generate a view sufficient for the current task context."""
    
    # Determine likely decision types from context
    likely_decisions = infer_decision_types(context)
    
    # Gather required observables for all likely decisions
    required = set()
    for dt in likely_decisions:
        reqs = DECISION_REQUIREMENTS.get(dt)
        if reqs:
            required.update(reqs.required_observables)
    
    # Compute observables
    observables = {}
    for obs_name in required:
        observables[obs_name] = compute_observable(state, obs_name)
    
    # Determine what's supported
    supported = []
    insufficient = []
    for dt in DECISION_REQUIREMENTS:
        if check_decision_sufficiency(dt, set(observables.keys())).sufficient:
            supported.append(dt)
        else:
            insufficient.append(dt)
    
    return StateLensView(
        observables=observables,
        decision_types_supported=supported,
        decision_types_insufficient=insufficient,
    )
```

---

## 24. Archetype Guard (Brand Integrity)

### 24.1 The Problem: Optimization Destroys Character

Optimization algorithms minimize metrics. They don't understand "Viking-ness." Without constraints, an optimizer will produce "The Blob" — a technically optimal but aesthetically soul-less design.

### 24.2 Archetype Signature

Define the measurable characteristics that make a Viking a Viking:

```python
@dataclass
class ArchetypeSignature:
    """Measurable characteristics that define an archetype."""
    
    # Hull geometry
    sheer_curvature_sign_change: bool = False  # Broken sheer
    entry_angle_range: tuple = (0, 90)         # degrees
    flare_above_chine: bool = False
    deadrise_range: tuple = (0, 30)            # degrees at transom
    
    # Proportions
    loa_beam_ratio_range: tuple = (3.0, 5.0)
    bow_overhang_fraction: tuple = (0.02, 0.08)
    
    # Arrangement
    cockpit_fraction_range: tuple = (0.2, 0.4)  # Fraction of deck area
    engine_room_position: str = "aft"           # "aft", "mid", "forward"
    
    # Required features
    required_features: List[str] = field(default_factory=list)
    forbidden_features: List[str] = field(default_factory=list)

VIKING_SIGNATURE = ArchetypeSignature(
    sheer_curvature_sign_change=True,
    entry_angle_range=(18, 28),
    flare_above_chine=True,
    deadrise_range=(10, 16),
    loa_beam_ratio_range=(3.5, 4.2),
    bow_overhang_fraction=(0.03, 0.06),
    cockpit_fraction_range=(0.25, 0.40),
    engine_room_position="aft",
    required_features=["broken_sheer", "integrated_transom_platform", "high_bow_flare"],
    forbidden_features=["plumb_bow", "displacement_hull", "low_freeboard_bow"],
)
```

### 24.3 Drift Detection

After any change, check archetype compliance:

```python
@dataclass
class ArchetypeDriftReport:
    """Report on how far the design has drifted from its archetype."""
    
    archetype_id: str
    overall_drift: float  # 0.0 = perfect match, 1.0 = completely different
    
    violations: List["ArchetypeViolation"]
    warnings: List["ArchetypeWarning"]
    
    still_valid: bool     # Is it still "a Viking"?
    recommendation: str

@dataclass
class ArchetypeViolation:
    feature: str
    requirement: str
    actual: Any
    severity: str  # "hard" (blocks), "soft" (warns)
    impact: str    # "Removes 'dryness' in heavy seas"

def check_archetype_drift(
    state: "DesignState",
    archetype: Archetype,
) -> ArchetypeDriftReport:
    """Check if design still matches its archetype."""
    
    signature = archetype.character_signature
    violations = []
    warnings = []
    drift_score = 0.0
    
    # Check required features
    for feature, requirement in archetype.required_features.items():
        actual = measure_feature(state, feature)
        if not satisfies(actual, requirement):
            violations.append(ArchetypeViolation(
                feature=feature,
                requirement=str(requirement),
                actual=actual,
                severity="hard",
                impact=FEATURE_IMPACTS.get(feature, "Unknown impact"),
            ))
            drift_score += 0.2
    
    # Check forbidden features
    for feature in archetype.forbidden_features:
        if has_feature(state, feature):
            violations.append(ArchetypeViolation(
                feature=feature,
                requirement="must not exist",
                actual="present",
                severity="hard",
                impact=f"'{feature}' is incompatible with {archetype.name}",
            ))
            drift_score += 0.3
    
    # Check parameter ranges
    for param, (min_val, max_val) in signature_ranges(signature).items():
        actual = measure_parameter(state, param)
        if actual < min_val or actual > max_val:
            warnings.append(ArchetypeWarning(
                parameter=param,
                range=(min_val, max_val),
                actual=actual,
            ))
            drift_score += 0.05
    
    return ArchetypeDriftReport(
        archetype_id=archetype.archetype_id,
        overall_drift=min(drift_score, 1.0),
        violations=violations,
        warnings=warnings,
        still_valid=len([v for v in violations if v.severity == "hard"]) == 0,
        recommendation=generate_drift_recommendation(violations, warnings),
    )
```

### 24.4 Guard Integration

The archetype guard runs before committing changes:

```python
class ArchetypeGuard:
    """Prevents changes that violate archetype identity."""
    
    def __init__(self, archetype: Archetype, strictness: str = "normal"):
        self._archetype = archetype
        self._strictness = strictness  # "strict", "normal", "relaxed"
    
    def check_proposed_change(
        self,
        current_state: "DesignState",
        proposed_state: "DesignState",
    ) -> "GuardResult":
        """Check if proposed change maintains archetype integrity."""
        
        current_drift = check_archetype_drift(current_state, self._archetype)
        proposed_drift = check_archetype_drift(proposed_state, self._archetype)
        
        # Hard violations always block
        new_hard_violations = [
            v for v in proposed_drift.violations 
            if v.severity == "hard" and v not in current_drift.violations
        ]
        
        if new_hard_violations:
            return GuardResult(
                allowed=False,
                reason="Change violates archetype identity",
                violations=new_hard_violations,
                suggestion=f"This change would make the design 'not a {self._archetype.name}'",
            )
        
        # Drift increase warnings
        drift_increase = proposed_drift.overall_drift - current_drift.overall_drift
        
        if self._strictness == "strict" and drift_increase > 0.05:
            return GuardResult(
                allowed=False,
                reason="Change increases archetype drift beyond strict threshold",
                drift_before=current_drift.overall_drift,
                drift_after=proposed_drift.overall_drift,
            )
        
        if drift_increase > 0.1:
            return GuardResult(
                allowed=True,
                warning=f"Archetype drift increased by {drift_increase:.1%}. Design is becoming less '{self._archetype.name}-like'.",
            )
        
        return GuardResult(allowed=True)
```

### 24.5 LLM Feedback on Archetype Violations

```yaml
# LLM proposes reducing bow flare to save weight:
proposed_change:
  operation: "SET hull.bow_flare_deg = 10"
  intent: "Reduce windage, save weight"

# Archetype guard blocks:
guard_result:
  allowed: false
  
  violation:
    feature: "bow_flare_deg"
    requirement: ">= 15"
    proposed: 10
    severity: "hard"
    
  impact: |
    High bow flare is a defining characteristic of the Viking Sportfish.
    Reducing to 10° would:
    - Drop 'Dryness' rating from 9/10 to 4/10 in head seas
    - Remove the aggressive Viking aesthetic
    - Make the design indistinguishable from generic sportfish
    
  suggestion: |
    If weight reduction is critical, consider:
    - Reduce tower height (saves 200kg, preserves flare)
    - Lighter engine option (saves 400kg, preserves flare)
    - Accept flare at 15° minimum (saves 50kg vs 20°)
    
  override_available: true
  override_warning: "Overriding will change archetype to 'generic_sportfish'"

# LLM can either:
# 1. Accept suggestion
# 2. Override (with consequence)
# 3. Abandon change
```

---

## 25. Success Criteria (Updated)

### 25.0 Hull Topology DSL (Creation)

**Composition from Primitives:**
- [ ] Monohull synthesized from `CREATE surface[bottom]...surface[topside]` program
- [ ] Stepped hull synthesized with ventilating steps from step primitives
- [ ] Catamaran synthesized from `CREATE demihull[stbd]...MIRROR` program
- [ ] Tunnel hull synthesized with prop pockets from tunnel primitives
- [ ] Hydrofoil synthesized with foil + strut primitives
- [ ] Novel combination ("stepped cat with tunnels and bow foil") synthesizes without predefined type

**Non-Enumeration Validation:**
- [ ] No `hull.type` enum in the DSL — all forms composed from primitives
- [ ] LLM can create forms that don't have standard names
- [ ] System validates physics for any composed form, not just "known" types

**Anchor Derivation:**
- [ ] Anchors detected automatically from synthesized geometry
- [ ] Chines created via `CREATE chine` become tracked anchors
- [ ] Steps created via `CREATE step` become tracked anchors
- [ ] Demihull boundaries become tracked anchors

**Topology → Edit Transition:**
- [ ] After hull creation, editing via affordances works normally
- [ ] Topology-changing edit ("add a step") triggers return to creation mode
- [ ] Edit boundary policy (§2.6) correctly triggers resynthesis

### 25.1 Part I: Hull Editing

- [ ] Anchors persist across 10 sequential operations without ID drift
- [ ] Round bilge operations maintain G1 continuity (no visible kinks)
- [ ] Scanned hull with 50+ inflection points shows ≤5 operations to LLM (hierarchy working)
- [ ] LLM never proposes infeasible distances (affordances working)
- [ ] Constraint violations produce actionable resolution options

**Audit Fix Validations:**
- [ ] Edit boundary policy triggers WARN at 70% drift threshold
- [ ] Edit boundary policy triggers FORCE_REWRITE before geometry corrupts (Viking v2→v3 test)
- [ ] Topology change classification correctly identifies RESTRUCTURE (e.g., round bilge → hard chine)
- [ ] Post-blend continuity validation detects when G2 degrades to G1
- [ ] Adaptive blend distance increases for high-curvature regions
- [ ] Stale affordances are rejected or auto-refreshed before operation execution
- [ ] Geometry quality degradation >25% triggers warning

### 25.2 Part II: Programmatic Design

- [ ] LLM can generate complete vessel from "Viking 72 sportfish" in ~15 statements
- [ ] System expands statements to 2,000+ artifacts without LLM involvement
- [ ] Routing failures self-resolve in ≥80% of cases (autonomous retry)
- [ ] Physics failures include decision-level attribution (not artifact-level)
- [ ] Zone-level operations propagate correctly to all contained artifacts
- [ ] Query interface keeps LLM working set to <20 items for any task

**Constraint Program Validation:**
- [ ] Contradictory constraints detected before compilation (e.g., planing hull + 2000nm range)
- [ ] Overconstrained programs generate warnings before compilation
- [ ] Constraint validation is exact logic, not approximate physics
- [ ] Invalid programs return specific conflicts with resolution options

### 25.3 Part III: Theoretical Foundations

**Negotiation Protocol:**
- [ ] Conflicting constraints generate Pareto front with ≥3 options
- [ ] Each option includes achieved values, sacrifices, and archetype drift
- [ ] LLM can express priorities in DSL (PRIORITY, PREFER, ACCEPT)
- [ ] "Impossible triangle" scenarios produce actionable tradeoff menus
- [ ] **NEW:** LLM can reject all Pareto options and request renegotiation
- [ ] **NEW:** Constraint modifications regenerate Pareto front

**Bootstrap Synthesis:**
- [ ] "Viking 72" produces valid, physics-passing hull in single bootstrap
- [ ] Generated hull matches archetype signature (drift < 0.1)
- [ ] Heuristic outfitting primes zones correctly for archetype
- [ ] No "blank page" — LLM always starts with valid seed

**Lossless Abstraction:**
- [ ] Decision-observable matrix covers all common decision types
- [ ] Sufficiency check runs before presenting decisions to LLM
- [ ] Insufficient decisions delegate to autonomous subsystems
- [ ] LLM never sees raw geometry for decisions that don't require it

**Archetype Guard:**
- [ ] Hard violations block commits with explanation
- [ ] Drift detection catches gradual erosion of archetype
- [ ] Override path exists with explicit consequence warning
- [ ] "Viking-ness" preserved through 10+ optimization cycles

### 25.4 The Viking Test (End-to-End)

- [ ] Input: "Create a 72ft Viking-style sportfish, 40 knots, 500nm range"
- [ ] LLM writes ≤20 DSL statements
- [ ] System generates 2,000+ validated artifacts
- [ ] Initial physics failure is attributed and resolved within 2 correction cycles
- [ ] Final vessel passes all stability, performance, and structural validators
- [ ] Total LLM turns: ≤5 (including corrections)
- [ ] Archetype drift < 0.1 (still recognizably "Viking")
- [ ] If constraints conflict, Pareto front presented before failure

**The v2→v3 Corruption Test (Audit Fix Validation):**
- [ ] After 10 sequential hull edits, edit boundary policy correctly assesses viability
- [ ] If cumulative drift exceeds threshold, FORCE_REWRITE is triggered before corruption
- [ ] Resynthesis preserves all parameter choices while resetting anchor tracking
- [ ] Post-resynthesis anchors have confidence ≥ 0.9

### 25.5 Anti-Goals (What Must NOT Happen)

- [ ] LLM never directly manipulates individual brackets, fittings, or stiffeners
- [ ] LLM never sees raw coordinate data for 10k+ artifacts
- [ ] LLM never picks from a menu of >20 options
- [ ] System never requires LLM involvement for routine routing/conflict resolution
- [ ] Physics failures never report "artifact_4921 caused this" (must be decision-level)
- [ ] Optimizer never removes archetype-defining features without explicit override
- [ ] System never returns "impossible" without offering Pareto alternatives

**Audit Fix Anti-Goals:**
- [ ] System never applies blend without post-validation of achieved continuity
- [ ] System never executes operation with stale affordance (version mismatch)
- [ ] System never allows edit mode to continue past circuit breaker thresholds
- [ ] Affordances from different subsystems (geometry, character, archetype) never contradict without unified presentation
- [ ] Geometry quality never degrades silently (must be surfaced in scene descriptions)

**Constrain Before Proposal Anti-Goals:**
- [ ] LLM never proposes operations outside affordance bounds (invalid ops unpresentable)
- [ ] System never uses "speculative physics" to approximate operation validity
- [ ] System never enters "propose → reject → re-propose" cycles (all options pre-validated)
- [ ] Constraint programs never reach compilation if logically inconsistent

---

## 26. Glossary

| Term | Definition |
|------|------------|
| **Affordance** | What an artifact allows — operations derived from its geometry |
| **Affordance Versioning** | Tracking when affordances were computed to detect staleness |
| **Anchor** | Structural feature point (keel, chine, sheer) tracked across changes |
| **Anchor Derivation** | Detecting anchors automatically from synthesized geometry (anchors are outputs, not inputs) |
| **Archetype** | Vessel style pattern (sportfish, trawler, etc.) with measurable signature |
| **Archetype Guard** | System that prevents changes from eroding vessel identity |
| **Attribution** | Tracing physics outcomes to LLM decisions, not individual artifacts |
| **Bootstrap** | Generating first valid geometry from archetype + parameters |
| **Circuit Breaker** | Edit boundary policy that forces resynthesis when edit mode is no longer viable |
| **Composition** | Building hull topology from primitives rather than selecting from enumerated types |
| **Constrain Before Proposal** | Design pattern: LLM selects from valid space, never proposes potentially invalid ops |
| **Constraint Program** | DSL statements that compile to geometry changes |
| **Constraint Validation** | Pre-compilation check for logical consistency (not approximate physics) |
| **Continuity Validation** | Post-operation check that achieved continuity matches target |
| **Cumulative Drift** | Total geometric shift since last synthesis (triggers circuit breaker) |
| **Delta-Affordance** | Pre-computed movement envelope showing what's possible |
| **Demihull** | Topological primitive: complete subsidiary hull body (catamaran, trimaran) |
| **Edit Boundary** | Threshold beyond which incremental edits should yield to resynthesis |
| **Enumeration Trap** | Anti-pattern where hull types are selected from a list rather than composed |
| **Expensive Iteration** | Domain characteristic where operations take seconds-to-minutes, not milliseconds |
| **Generator** | Deterministic subsystem that produces artifacts from parameters |
| **Geometry Quality** | Surface fairness, panel warp, mesh regularity — beyond clearances |
| **Hull Creation** | Composing topology program → synthesizing NURBS (vs editing existing hull) |
| **Hull Editing** | Modifying existing hull via anchor-based affordances (within existing topology) |
| **Integrated Affordance** | Unified limit combining geometry, character, archetype constraints |
| **Lossless Abstraction** | Guarantee that summary contains enough info for correct decisions |
| **Negotiation** | Resolving constraint conflicts via Pareto front generation |
| **Pareto Front** | Set of optimal tradeoffs when constraints can't all be satisfied |
| **Pareto Rejection** | LLM ability to reject all options and request renegotiation |
| **Propagation** | Zone/system operation expanding to constituent artifacts |
| **Query Interface** | LLM asks questions vs inspects scene graph |
| **Stale Affordance** | Movement envelope computed at outdated state version |
| **Step** | Topological primitive: transverse discontinuity for ventilation (stepped hull) |
| **Sufficiency Matrix** | Mapping of decision types to required observables |
| **Topological Primitive** | Basic element for hull composition: surface, chine, step, tunnel, foil, demihull, etc. |
| **Topology Change** | INCREMENTAL, ADDITIVE, SUBTRACTIVE, or RESTRUCTURE classification |
| **Topology Program** | DSL program that composes hull form from primitives |
| **Tunnel** | Topological primitive: void between surfaces (prop tunnel, catamaran tunnel) |
| **Working Set** | Small subset (~5-20) of artifacts relevant to current task |

---

## 27. Audit Trail

This specification incorporates fixes for the following identified gaps:

| Gap | Fix | Section |
|-----|-----|---------|
| Hull creation is enumeration | Hull Topology DSL (composition from primitives) | §0 |
| Edit-vs-Rewrite boundary undefined | Edit Boundary Policy with circuit breaker | §2.6 |
| Anchor matching under topology change | Topology Change Classification | §2.5 |
| Continuity validation missing | Post-Blend Continuity Validation | §3.5 |
| Fixed blend distance | Adaptive Blend Distance | §3.6 |
| Affordance staleness undetected | Affordance Versioning | §5.5 |
| Contradictory affordance limits | Cross-System Affordance Integration | §5.6 |
| Geometry quality not surfaced | Geometry Quality Metrics | §6.4 |
| No Pareto rejection path | Pareto Rejection Path | §21.6 |

**Root Cause of Viking v2→v3 Bug:** Cumulative geometric drift exceeded implicit threshold while anchor tracker continued attempting incremental matching. Fix: Explicit edit boundary policy (§2.6) with circuit breaker that forces resynthesis before corruption occurs.

**Root Cause of Enumeration Trap:** Original spec assumed hull topology exists and LLM only edits via affordances. This prevents creating stepped hulls, catamarans, hydrofoils, etc. Fix: Hull Topology DSL (§0) where LLM composes from primitives instead of selecting from enumerated types. This capability already exists in `kernel/synthesis.py`, `hull_gen/`, and `hull_gen/modifiers/` — requires refactor to surface as DSL.

---

## 28. Design Rationale

### Why Composition Over Enumeration

| Approach | What LLM Does | Limitation |
|----------|---------------|------------|
| **Enumeration** | Selects `hull.type = "catamaran"` | Can't create unenumerated types |
| **Composition** | Writes topology program from primitives | Can create any physically valid form |

The LLM can compose hull forms that don't have standard names ("stepped catamaran with tunnel props and bow foil"). The system validates physics for any composed form. This follows the same pattern as outfitting (constraint program → artifact expansion).

**Implementation Note:** Hull synthesis machinery already exists (`kernel/synthesis.py`, `hull_gen/`, modifiers). The refactor surfaces this as a compositional DSL rather than procedural code driven by `HullFamily` enum.

### Why This Architecture (Expensive Iteration)

This spec's abstractions exist because naval architecture is an **expensive iteration domain**:

| Abstraction | Why It's Necessary |
|-------------|-------------------|
| **Topology DSL** | LLM composes forms from primitives; avoids enumeration of hull types |
| **Affordance pre-computation** | Spatial queries against 10k artifacts are expensive; must cache |
| **Hierarchical operations** | LLM cannot reason about 10k individual artifacts; zones/systems are mandatory |
| **Query interface** | Working set of ~20 items, not 10k-node scene graph |
| **Sufficiency matrix** | Verify before commit; "oops, need more info" wastes expensive compute |
| **Attribution** | Targeted fixes, not blind iteration when physics fails |
| **Pareto fronts** | Pre-compute tradeoffs once, not iterative trial-and-error |

### Why "Constrain Before Proposal"

The pattern throughout this spec is:
```
System computes valid space → LLM selects within it → Execute
```

NOT:
```
LLM proposes → System validates → Maybe execute
```

**Rationale:** In expensive-iteration domains, wasted operations cost minutes of compute. By constraining the LLM to select from pre-validated options, we eliminate the "propose invalid operation → rejection → re-propose" cycle entirely.

### Why No Speculative Physics

It might seem useful to add approximate physics checks before expensive operations. This is **explicitly rejected** because:

1. **Redundant:** Affordances already constrain the valid space
2. **Dangerous:** Approximations have false positives (reject valid ops) and false negatives (approve doomed ops)
3. **Wrong pattern:** It's "check after proposal" disguised as optimization

The spec uses **authoritative checks** (affordance bounds, sufficiency verification, version validation), not approximations. Constraint program validation (§11.4) is exact logical consistency checking, not physics approximation.

---

*End of specification.*
