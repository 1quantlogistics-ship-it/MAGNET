# CORTEX: A Theory of LLM Control Over Physical Artifacts

**Version:** 1.0  
**Status:** Working Theory  
**Author:** Ben / MAGNET Project  
**Date:** January 2026

---

## First-Principles Summary

You can use LLM reasoning in an intelligent design spiral if and only if:

- **The LLM reasons about what should change and why**
- **The kernel reasons about how it can change and what actually happens**
- **Every loop step replaces speculation with computed fact**

Your architecture is not limiting the LLM's intelligence.  
It is preventing the LLM from mistaking fluency for truth.

**That's the difference between a persuasive assistant and a reliable design system.**

---

## Abstract

Large Language Models can reason, plan, and generate. They cannot see, verify, or precisely manipulate physical reality. Every attempt to use LLMs for physical design fails at the same wall: the gap between language and validity.

This document presents CORTEX — a complete theory for bridging that gap. The core insight is that LLMs should never touch state directly. Instead, they operate as an **editorial layer** over pre-computed analysis, emitting **constrained intent** that a **validity-enforcing kernel** executes.

Boats are the proof case. The pattern is general.

---

## Part I: The Problem

### 1.1 The Three Fatal Limitations

LLMs have three limitations that make them dangerous when interacting with physical systems:

| Limitation | Description | Consequence |
|------------|-------------|-------------|
| **They can't see** | They process tokens, not space | They hallucinate spatial relationships |
| **They can't verify** | They can claim validity but can't prove it | They confidently produce invalid states |
| **They can't precisely manipulate** | They can express intent but can't execute | They corrupt state attempting direct edits |

### 1.2 Why Current Approaches Fail

**Approach 1: Give LLM raw data**
```
"Here are 50,000 vertices..."
```
Fails: LLM cannot reason spatially from coordinates. Context explodes. Relationships are invisible.

**Approach 2: Give LLM natural language descriptions**
```
"There's a tank near the bulkhead..."
```
Fails: Lossy. Ambiguous. Cannot execute precise changes. "Near" is not actionable.

**Approach 3: Let LLM generate commands directly**
```
LLM outputs: move(component, x=47.3, y=-12.1)
```
Fails: No validity check. No rollback. No understanding of consequences. State corruption guaranteed.

**Approach 4: Human executes everything**
```
LLM suggests, human does
```
Fails: Doesn't scale. Human becomes bottleneck. Defeats the purpose of AI assistance.

### 1.3 The Core Insight

The solution is not better prompts, bigger context, or smarter models. The solution is **architectural**:

> **LLMs must never see raw state or emit raw mutations.**
>
> They see pre-computed analysis. They emit constrained intent. A kernel validates and executes.

This transforms the LLM from an unreliable actor into a reliable **editorial layer**.

---

## Part II: The Architecture

### 2.1 The Five Components

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CORTEX ARCHITECTURE                            │
│                                                                          │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│   │   ARTIFACT   │───▶│  OBSERVABLE  │───▶│    VISION    │              │
│   │    GRAPH     │    │    LAYER     │    │    LAYER     │              │
│   │              │    │              │    │              │              │
│   │ Components   │    │ Computed     │    │ Annotated    │              │
│   │ Relationships│    │ metrics      │    │ renders      │              │
│   │ Spatial index│    │ on demand    │    │ on demand    │              │
│   └──────────────┘    └──────────────┘    └──────────────┘              │
│          │                   │                   │                       │
│          │                   ▼                   ▼                       │
│          │            ┌─────────────────────────────┐                   │
│          │            │           LLM               │                   │
│          │            │                             │                   │
│          │            │  Sees: Analysis + Views     │                   │
│          │            │  Emits: Constrained Intent  │                   │
│          │            └─────────────────────────────┘                   │
│          │                         │                                     │
│          │                         ▼                                     │
│          │            ┌─────────────────────────────┐                   │
│          │            │         KERNEL              │                   │
│          │            │                             │                   │
│          ◀────────────│  Validates + Executes      │                   │
│     (mutations)       │  Commits or Rolls Back     │                   │
│                       └─────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component 1: The Artifact Graph

The artifact graph is the **single source of truth** for physical state. It is not a file, not a directory, not a mesh — it is a **queryable spatial graph**.

```
STRUCTURE:
├── Nodes: Components
│   ├── id: unique identifier
│   ├── type: semantic category (tank, pipe, outlet, section, ...)
│   ├── geometry: bounds, mesh, curves
│   ├── properties: mass, material, capacity, ...
│   └── metadata: version, provenance, constraints
│
├── Edges: Relationships
│   ├── CONNECTS_TO (physical connection)
│   ├── MOUNTED_ON (attachment)
│   ├── ROUTES_THROUGH (path traversal)
│   ├── CLEARS (spatial separation)
│   └── DEPENDS_ON (logical dependency)
│
└── Indices:
    ├── Spatial: R-tree for proximity queries
    ├── Type: component type → instances
    └── Dependency: invalidation cascade graph
```

**Key property:** The graph is **CAD-agnostic**. Any import format (STEP, IFC, BREP, mesh) converts to the same graph structure. The system works on any vessel without vessel-specific code.

### 2.3 Component 2: The Observable Layer

Observables are **questions you can ask about the graph**, answered as numbers. They are computed on demand, not stored.

```python
# Observable grammar
{metric}:{target}
{metric}:{target_a}:{target_b}

# Examples — none of these are pre-enumerated
distance:tank_001:bulkhead_aft        → 0.47m
clearance:fuel_fill:above             → 0.12m  
weight_moment:zone_engine_room        → 4700 kg·m
routing_length:pipe_007               → 7.3m
entry_half_angle:hull                 → 11.2°
accessibility:fuel_fill_stbd          → 0.73
```

**Key property:** The observable vocabulary is **open**. You define metric *types* (distance, clearance, angle, ratio), not metric *instances*. New components = new observables without code changes.

**Observable taxonomy:**

| Type | Description | Examples |
|------|-------------|----------|
| **Spatial** | Distances, clearances, positions | `distance:A:B`, `clearance:A:direction` |
| **Geometric** | Angles, curvatures, ratios | `entry_angle:hull`, `deadrise:section_5` |
| **Physical** | Mass, volume, capacity | `weight:zone`, `volume:tank` |
| **Derived** | Computed from multiple inputs | `stability:vessel`, `accessibility:component` |
| **Relational** | Graph structure queries | `connection_count:manifold`, `path_length:A:B` |

### 2.4 Component 3: The Vision Layer

At the micro level, language is insufficient. LLMs need to **see** to reason about space.

**Solution:** Rendered, annotated, scoped views on demand.

```python
def render_view(
    focus: str,           # Component or zone ID
    scope: str,           # "local_2m", "deck", "section_x=7.2", "full"
    annotations: List[str], # "clearances", "labels", "constraints", "dimensions"
    view_angle: str       # "isometric", "top", "side", "section"
) -> AnnotatedImage:
    """
    Returns an image with kernel-computed measurements overlaid.
    LLM sees analysis, not raw geometry.
    """
```

**Key property:** The kernel annotates the view. The LLM does not infer distances from pixels — distances are computed and overlaid as text. The view is pre-analyzed.

**What the LLM receives:**
- Image centered on focus component
- Nearby components labeled with IDs
- Clearances and dimensions rendered as measurements
- Constraint violations highlighted
- All spatial reasoning pre-computed

### 2.5 Component 4: The Intent Language

The LLM can only emit structured intent. Never raw coordinates. Never direct mutations.

```
VERBS (exhaustive):

ADJUST {observable} AT {scope} BY {delta}{unit}
  → Change an observable by a relative amount

TARGET {observable} AT {scope} = {value}{unit}
  → Set an observable to an absolute value

QUERY {observable} AT {scope}
  → Request observable computation

VIEW {focus} SCOPE {radius} ANNOTATE {annotations}
  → Request annotated render
```

**That's it. Four verbs.** Any physical manipulation must be expressed as an observable change, not a coordinate change.

**Key property:** Intent is **auditable, reversible, and validatable**. The kernel translates intent to operations. The LLM never needs to know how the translation works.

### 2.6 Component 5: The Kernel

The kernel is the **only component that touches state**. It provides the validity guarantee.

```
KERNEL RESPONSIBILITIES:

1. TRANSLATE intent to operations
   - ADJUST entry_angle BY -2° → reduce forward beam by X
   - Control mappings convert intent to geometry changes

2. EXECUTE operations on artifact graph
   - Apply changes to components
   - Update relationships
   - Cascade to dependent observables

3. VALIDATE all constraints
   - Physical: clearances, weights, stability
   - Semantic: type constraints, relationships
   - Domain: floats, doesn't capsize, meets code

4. COMMIT or ROLLBACK atomically
   - All changes succeed together or none persist
   - Invalid state cannot exist

5. RETURN receipt
   - Before/after observables
   - Validation results
   - Suggestions for next action
```

**Key property:** No matter what the LLM proposes, **invalid state cannot persist**. The kernel is the validity gate.

---

## Part III: The Four Axioms

These axioms emerged from implementation. They are not optional.

### Axiom 1: Exploration Must Be Compelled, Not Assumed

> **LLMs are lazy explorers. They optimize for local coherence, not global completeness.**

Even with perfect graph access, an LLM will:
- Query some observables, not all relevant ones
- Stop early if partial evidence seems consistent
- Fail to notice missing queries unless forced

**Implementation:** Obligatory exploration surfaces.

```python
# Before accepting a proposal, demand evidence
REQUIRED_QUERIES = {
    "hull_modification": ["stability", "displacement", "resistance"],
    "component_move": ["clearance_all_directions", "accessibility", "routing_impact"],
    "system_change": ["weight_distribution", "dependency_cascade"],
}

def validate_exploration(proposal: Proposal, queries_made: List[str]) -> bool:
    """Reject proposals that didn't query required observables."""
    required = REQUIRED_QUERIES.get(proposal.type, [])
    missing = set(required) - set(queries_made)
    if missing:
        raise ExplorationIncomplete(f"Must query: {missing}")
    return True
```

**Principle:** Query access is not enough. Observable computation is not enough. The system must **demand** completeness.

### Axiom 2: Meaning Must Be Time-Indexed

> **Observables are not timeless truths. They are functions whose meaning must be frozen per decision.**

The same observable ID can mean different things over time:
- Metric definitions evolve
- Geometry kernels change
- CAD importers improve
- Calibration drifts

**Implementation:** Semantic versioning of meaning.

```python
@dataclass
class ObservableReading:
    observable_id: str
    value: float
    unit: str
    
    # Time-indexing (required)
    definition_version: str    # Hash of the measurement function
    inputs_hash: str           # Hash of geometry/data inputs
    computed_at: datetime      # When this reading was taken
    
    def is_stale(self, current_definition_version: str) -> bool:
        return self.definition_version != current_definition_version
```

**Principle:** Every decision binds against a versioned reading. Re-evaluation is allowed, but **accountability survives** because the original meaning is preserved.

### Axiom 3: Intent and Consequence Must Be Formally Separated

> **LLMs author intent. Systems compute consequences. Policy mediates the gap.**

Observables fall into two fundamentally different classes:

| Class | Description | Examples | Who Owns It |
|-------|-------------|----------|-------------|
| **Intent** | What the designer wants | "Entry angle ≈ 11°", "Clearance ≥ 0.3m" | LLM declares |
| **Consequence** | What results from geometry | "CG shifted 0.2m", "Resistance +4%" | Kernel computes |

**Implementation:**

```python
class ObservableType(Enum):
    INTENT = "intent"           # Declared before geometry exists
    CONSEQUENCE = "consequence"  # Computed after geometry exists

# LLM can emit TARGET for intent observables
# LLM can only READ consequence observables
# Policy determines acceptable gaps

@dataclass  
class PolicyGap:
    intent_observable: str
    intent_value: float
    consequence_observable: str
    consequence_value: float
    acceptable: bool
    override_required: bool
```

**Principle:** LLMs should never "decide" consequences, only react to them. The separation prevents hallucinated physics.

### Axiom 4: Override Must Be a Recorded Semantic Act

> **Human decisions must be as inspectable as model decisions.**

In real design:
- Engineers knowingly violate heuristics
- Architects accept tradeoffs
- Clients choose risk

The system must handle this without collapsing into either:
- Authoritarian rigidity (unusable)
- Silent permissiveness (vibes)

**Implementation:**

```python
@dataclass
class Override:
    id: str
    timestamp: datetime
    user_id: str
    
    # What was overridden
    constraint_id: str
    original_value: Any
    override_value: Any
    
    # Why (required)
    justification: str
    risk_acknowledged: bool
    
    # Consequences
    weakened_contracts: List[str]
    spawned_branch: Optional[str]
    expires_at: Optional[datetime]

# Override is itself an observable
def get_override_count(scope: str) -> int:
    """How many overrides exist in this scope?"""

def get_override_risk_score(scope: str) -> float:
    """Aggregate risk from all overrides."""
```

**Principle:** Overrides are **first-class semantic acts** with recorded consequences. They don't break the system — they become part of the auditable history.

---

## Part IV: The Loop

### 4.1 The Complete Interaction Cycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         THE CONTROL LOOP                                 │
│                                                                          │
│  1. USER expresses intent (natural language)                            │
│     "Move the fuel fill lower, it's hard to reach from the dock"        │
│                                                                          │
│  2. SYSTEM prepares context                                              │
│     - Queries graph for relevant components                              │
│     - Computes observables (clearance, accessibility, constraints)       │
│     - Renders annotated view of affected area                            │
│     - Generates suggestions with computed deltas                         │
│                                                                          │
│  3. LLM receives analysis (not raw data)                                │
│     - Image: annotated view of fuel fill area                            │
│     - Observables: {height: 2.1m, clearance: 0.3m, accessibility: 0.6}  │
│     - Constraints: {min_clearance: 0.15m}                                │
│     - Suggestion: "ADJUST height BY -0.15m → accessibility +0.12"       │
│                                                                          │
│  4. LLM reasons and emits intent                                        │
│     ADJUST position:z AT fuel_fill_stbd BY -0.15m                       │
│                                                                          │
│  5. KERNEL validates and executes                                        │
│     - Translates intent to operation                                     │
│     - Executes on graph                                                  │
│     - Validates all constraints                                          │
│     - Commits (if valid) or rolls back (if invalid)                     │
│                                                                          │
│  6. RECEIPT returned                                                     │
│     - Before/after observables                                           │
│     - Validation status                                                  │
│     - Suggestions for next action                                        │
│                                                                          │
│  7. LOOP until user satisfied or REWRITE required                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Failure Handling

**Validation Failure:**
```
Kernel: "Cannot execute. clearance_below would be 0.0m (min 0.15m)."
LLM: [Sees failure reason, adjusts intent, tries smaller delta]
```

**Exploration Failure:**
```
System: "Proposal rejected. Must query: stability, weight_distribution"
LLM: [Queries required observables, resubmits with evidence]
```

**Convergence Failure:**
```
System: "Target unreachable after 3 attempts. Offer REWRITE?"
User: [Decides to approve REWRITE or accept current state]
```

### 4.3 The REWRITE Escape Hatch

When ADJUST cannot achieve a target:

```python
def should_offer_rewrite(attempts: List[EditResult]) -> bool:
    """Detect when ADJUST can't converge."""
    if len(attempts) >= 3:
        deltas = [a.remaining_delta for a in attempts[-3:]]
        if all(d > 0.5 * attempts[-3].remaining_delta for d in deltas):
            return True  # Not converging
    if any(a.validation_failed for a in attempts):
        return True  # Hitting hard constraints
    return False
```

REWRITE requires explicit user approval. It is a **semantic act** (Axiom 4), recorded with justification.

---

## Part V: Generalization

### 5.1 Beyond Boats

The pattern is domain-agnostic:

| Domain | Artifact Graph | Observables | Validity Gates |
|--------|---------------|-------------|----------------|
| **Naval Architecture** | Hull + systems + outfit | Entry angle, stability, clearance | Floats, doesn't capsize |
| **Building Architecture** | Structure + MEP + envelope | Window ratio, load paths, egress | Stands, meets code |
| **Circuit Design** | Components + nets + layers | Timing, power, area | Meets timing, doesn't overheat |
| **Drug Design** | Molecules + bonds + conformers | Binding affinity, solubility | Synthesizable, non-toxic |
| **Manufacturing** | Parts + assembly + tooling | Tolerances, accessibility | Builds, assembles correctly |

### 5.2 What Changes Per Domain

| Component | What's Universal | What's Domain-Specific |
|-----------|-----------------|------------------------|
| Artifact Graph | Node/edge structure, query patterns | Component types, relationship semantics |
| Observable Layer | Computation framework, grammar | Metric definitions, physics |
| Vision Layer | Rendering pipeline, annotation system | View conventions, domain symbols |
| Intent Language | ADJUST/TARGET/QUERY/VIEW verbs | Observable vocabularies |
| Kernel | Validation framework, transaction model | Domain validity rules |

### 5.3 The Infrastructure Layer

What we're building is not a boat tool. It's:

> **The missing infrastructure layer between LLMs and physical reality.**

Every domain where AI meets physics needs this layer. We're proving it works on boats, then generalizing.

---

## Part VI: The Contracts

### 6.1 Kernel Guarantees

```
1. VALIDITY: Invalid state cannot persist
2. ATOMICITY: Operations commit entirely or not at all
3. AUDITABILITY: Every change has a receipt
4. REVERSIBILITY: Any committed change can be rolled back
5. DETERMINISM: Same intent + same state = same result
```

### 6.2 LLM Boundaries

```
1. CANNOT see raw state (only analysis)
2. CANNOT emit raw mutations (only intent)
3. CANNOT bypass validation
4. CANNOT claim unexplored evidence
5. MUST declare intent observables before expecting consequences
```

### 6.3 Human Authorities

```
1. CAN override any constraint (with recorded justification)
2. CAN approve REWRITE when ADJUST fails
3. CAN set policy thresholds
4. CAN audit any decision (human or model)
5. CANNOT be overridden by model decisions
```

---

## Part VII: Implementation Roadmap

### Phase 1: Hull Control Loop (Current)
- Section-based observables
- Shape document with computed suggestions
- ADJUST/TARGET grammar
- Character preservation through iteration
- **Proves:** Closed-loop LLM control over geometry

### Phase 2: Full Vessel Artifact Graph
- CAD import → component graph
- System-level observables (outfit, MEP, structure)
- Spatial queries and relationships
- **Proves:** Pattern works beyond parametric geometry

### Phase 3: Vision Layer
- Annotated renders on demand
- Scoped views (local, deck, section)
- LLM spatial reasoning via images
- **Proves:** Micro-level control with visual feedback

### Phase 4: Agent Exploration
- Query tools for graph traversal
- Obligatory exploration enforcement
- Multi-step reasoning with state
- **Proves:** Complex design tasks with guaranteed completeness

### Phase 5: Domain Generalization
- Pluggable validity gates
- Pluggable observable types
- Domain configuration without code changes
- **Proves:** Infrastructure is truly general

---

## Part VIII: The Pitch

### For Engineers

> We built the control system that makes LLMs safe for physical design.
>
> Observables give them eyes. Constraints give them guardrails. The kernel gives them a validity guarantee.
>
> They can't corrupt state. They can only propose, and the system validates.

### For Executives

> Every company using AI for physical products faces the same problem: LLMs are confident but wrong.
>
> We built the layer that makes them useful: pre-computed analysis they can reason about, constrained actions they can propose, and validation that guarantees nothing breaks.
>
> It works for boats. It works for anything with physics.

### For Investors

> LLMs are open-loop controllers pretending to be closed-loop.
>
> We built the feedback path.
>
> This is the infrastructure layer between language models and physical reality. Every domain where intent must become valid physical change — vessels, buildings, circuits, molecules — needs what we've built.
>
> Boats are the proof case. The TAM is everything physical.

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **Artifact Graph** | Queryable spatial graph representing physical state |
| **Observable** | Computed question about the graph, answered as a number |
| **Intent Observable** | Observable the designer wants to achieve |
| **Consequence Observable** | Observable computed from resulting geometry |
| **Kernel** | Validity-enforcing execution layer |
| **Shape Document** | Pre-computed analysis sized for LLM context |
| **Control Mapping** | Translation from intent to geometry operations |
| **Override** | Recorded human decision to bypass a constraint |
| **REWRITE** | Permission to regenerate (not just edit) geometry |

## Appendix B: The One-Page Summary

```
THE PROBLEM
LLMs can't see, verify, or manipulate physical reality.
Every attempt to use them for physical design fails.

THE INSIGHT  
Don't give LLMs raw data. Don't let them emit raw commands.
Give them pre-computed analysis. Let them emit constrained intent.
A kernel validates and executes.

THE ARCHITECTURE
Artifact Graph → Observable Layer → Vision Layer
                      ↓
                    LLM (editorial)
                      ↓
                   Kernel (validity)
                      ↓
              Artifact Graph (updated)

THE AXIOMS
1. Exploration must be compelled, not assumed
2. Meaning must be time-indexed
3. Intent and consequence must be formally separated
4. Override must be a recorded semantic act

THE GUARANTEE
Invalid state cannot persist.
Every change is auditable.
Humans remain in control.

THE GENERALIZATION
Boats prove the pattern.
Buildings, circuits, molecules, manufacturing — same architecture.
This is the infrastructure layer between LLMs and physical reality.
```

---

## Part IX: Concrete Implementation

The theory above is architecture. This section is code. Everything described here works with current APIs — no future tech required.

### 9.1 The Core Insight

The system requires:
1. **Model thinks deeply before acting** (extended reasoning)
2. **Model sees current state** (vision)
3. **Model requests specific views it needs** (agentic vision)
4. **Model operates in a loop until done** (agent loop)

All of this is buildable today with Claude's tool use API and vision capabilities.

### 9.2 Extended Thinking via Two-Pass Architecture

You don't wait for Anthropic to give you extended thinking. You BUILD it with two passes:

```python
# Pass 1: Thinking pass - model reasons about what to do
thinking_response = client.messages.create(
    model="claude-sonnet-4-20250514",
    system="""You are analyzing a design task. 
    
    DO NOT take action yet. Only reason about:
    1. What observables are relevant?
    2. What views do I need to see?
    3. What constraints apply?
    4. What's my plan?
    
    Output structured JSON with your analysis.""",
    messages=[
        {"role": "user", "content": f"Task: {user_request}\n\nCurrent state:\n{state_summary}"}
    ]
)

# Parse thinking output
thinking = json.loads(thinking_response.content)

# Fetch what the model asked for
views_needed = thinking.get("views_needed", [])
observables_needed = thinking.get("observables_needed", [])

# Gather evidence
evidence = gather_evidence(views_needed, observables_needed)

# Pass 2: Action pass - model acts with full context
action_response = client.messages.create(
    model="claude-sonnet-4-20250514",
    system="""You have completed analysis. Now emit ONLY valid commands:
    ADJUST {observable} AT {scope} BY {delta}
    TARGET {observable} AT {scope} = {value}
    
    No explanation. Just commands.""",
    messages=[
        {"role": "user", "content": f"Task: {user_request}"},
        {"role": "assistant", "content": f"My analysis:\n{json.dumps(thinking)}"},
        {"role": "user", "content": f"Evidence gathered:\n{format_evidence(evidence)}"}
    ]
)
```

**Key insight:** Pass 1 is "think out loud, request what you need." System gathers evidence. Pass 2 is "now act with full context."

### 9.3 Vision - Model Sees Current State

Claude's vision API accepts images. Use it:

```python
# Render current state to image
view_image = render_view(
    focus=component_id,
    scope="local_2m",
    annotations=["clearances", "labels", "constraints"]
)

# Send to model with image
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": base64.b64encode(view_image).decode()
                    }
                },
                {
                    "type": "text", 
                    "text": f"""Task: {user_request}
                    
Observables:
{format_observables(current_observables)}

What command should I execute?"""
                }
            ]
        }
    ]
)
```

**This is not future tech. This works today.**

### 9.4 Agentic Vision - Model Requests Views

The model outputs structured requests, system fulfills them, model continues.

**Tool definitions:**

```python
tools = [
    {
        "name": "request_view",
        "description": "Request a rendered view of part of the vessel",
        "input_schema": {
            "type": "object",
            "properties": {
                "focus": {
                    "type": "string", 
                    "description": "Component ID or zone to center on"
                },
                "scope": {
                    "type": "string", 
                    "enum": ["local_1m", "local_2m", "local_5m", "deck", "section", "full"]
                },
                "annotations": {
                    "type": "array",
                    "items": {
                        "type": "string", 
                        "enum": ["clearances", "labels", "dimensions", "constraints"]
                    }
                },
                "view_angle": {
                    "type": "string", 
                    "enum": ["isometric", "top", "side", "front", "section"]
                }
            },
            "required": ["focus", "scope"]
        }
    },
    {
        "name": "query_observable",
        "description": "Compute an observable metric",
        "input_schema": {
            "type": "object", 
            "properties": {
                "observable": {
                    "type": "string", 
                    "description": "e.g., 'clearance:tank_001:above'"
                },
            },
            "required": ["observable"]
        }
    },
    {
        "name": "query_nearby",
        "description": "Find components near a target",
        "input_schema": {
            "type": "object",
            "properties": {
                "component_id": {"type": "string"},
                "radius_m": {"type": "number"}
            },
            "required": ["component_id", "radius_m"]
        }
    },
    {
        "name": "execute_adjust",
        "description": "Execute an ADJUST command",
        "input_schema": {
            "type": "object",
            "properties": {
                "observable": {"type": "string"},
                "scope": {"type": "string"},
                "delta": {"type": "number"},
                "unit": {"type": "string"}
            },
            "required": ["observable", "scope", "delta", "unit"]
        }
    }
]
```

### 9.5 The Agent Loop

```python
def run_agent(user_request: str, artifact_graph: ArtifactGraph, max_turns: int = 10):
    messages = [
        {"role": "user", "content": user_request}
    ]
    
    for turn in range(max_turns):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            system=AGENT_SYSTEM_PROMPT,
            tools=tools,
            messages=messages
        )
        
        # Check if model wants to use tools
        if response.stop_reason == "tool_use":
            tool_results = []
            
            for tool_call in response.content:
                if tool_call.type == "tool_use":
                    # Execute the tool
                    result = execute_tool(
                        tool_call.name, 
                        tool_call.input,
                        artifact_graph
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": result  # Can be text OR image
                    })
            
            # Add assistant message and tool results to history
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            
        elif response.stop_reason == "end_turn":
            # Model is done
            return response.content
    
    return "Max turns reached"
```

### 9.6 Tool Execution (Including Vision)

```python
def execute_tool(name: str, inputs: dict, graph: ArtifactGraph):
    if name == "request_view":
        # Render the view - THIS IS THE KEY CAPABILITY
        image = render_view(
            focus=inputs["focus"],
            scope=inputs["scope"],
            annotations=inputs.get("annotations", ["labels"]),
            view_angle=inputs.get("view_angle", "isometric")
        )
        # Return as image content - model SEES this
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png", 
                "data": base64.b64encode(image).decode()
            }
        }
    
    elif name == "query_observable":
        value = compute_observable(graph, inputs["observable"])
        return f"{inputs['observable']} = {value}"
    
    elif name == "query_nearby":
        components = graph.query_near(inputs["component_id"], inputs["radius_m"])
        return format_components(components)
    
    elif name == "execute_adjust":
        result = kernel.execute_adjust(
            observable=inputs["observable"],
            scope=inputs["scope"],
            delta=inputs["delta"],
            unit=inputs["unit"]
        )
        if result.success:
            return f"Success. Before: {result.before}, After: {result.after}"
        else:
            return f"Failed: {result.error}"
```

### 9.7 Complete Agent Flow Example

```
USER: "Move the fuel fill lower"
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│                      AGENT LOOP                              │
│                                                              │
│  Turn 1: Model calls query_nearby("fuel_fill", 2m)          │
│          System returns: [pipe_007, bracket_012, ...]       │
│                                                              │
│  Turn 2: Model calls request_view(                          │
│            focus="fuel_fill",                                │
│            scope="local_2m",                                 │
│            annotations=["clearances"]                        │
│          )                                                   │
│          System returns: [annotated PNG image]               │
│          Model SEES the fuel fill and surrounding area       │
│                                                              │
│  Turn 3: Model calls query_observable(                       │
│            "clearance:fuel_fill:below"                       │
│          )                                                   │
│          System returns: "0.31m"                             │
│                                                              │
│  Turn 4: Model reasons: "I can move down 0.15m safely"      │
│          Model calls execute_adjust(                         │
│            observable="position:z",                          │
│            scope="fuel_fill_stbd",                           │
│            delta=-0.15,                                      │
│            unit="m"                                          │
│          )                                                   │
│          Kernel validates → Success                          │
│          System returns: {before: -1.2m, after: -1.35m}     │
│                                                              │
│  Turn 5: Model calls request_view(...) to verify            │
│          Model sees updated state, confirms change           │
│          Model: "Done. Fuel fill lowered 15cm."             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 9.8 What's Required vs What Exists

| Component | Implementation | Status |
|-----------|----------------|--------|
| **Agent loop** | Tool use API + message history | ✅ Available now |
| **Vision in messages** | Base64 images in content | ✅ Available now |
| **Tool calling** | Claude tools API | ✅ Available now |
| **View rendering** | WebGL pipeline exports PNG | ✅ You have this (needs headless mode) |
| **Observable queries** | geometry_observables.py | ✅ You have this |
| **Artifact graph** | CAD import → queryable structure | ⚠️ Need to build |
| **Spatial index** | R-tree for proximity queries | ⚠️ Need to build |
| **Kernel validation** | expander.py + validators | ✅ You have this |

### 9.9 What's Missing From Current MAGNET

**1. Tool definitions for agent mode**
You have the capabilities. They're not exposed as callable tools.

**2. Headless view rendering**
WebGL renders to browser. Need render-to-PNG for API responses.

**3. Artifact graph with spatial queries**
You have sections. Need components with `query_near()`, `query_path()`.

**4. The agent loop wrapper**
~50 lines once tools exist.

### 9.10 The Minimal Implementation

The entire pattern reduces to:

```python
tools = [
    request_view,      # Model asks to see something → gets image
    query_observable,  # Model asks for a metric → gets number
    query_nearby,      # Model asks what's near X → gets list
    execute_adjust,    # Model emits intent → kernel validates
]

while not done:
    response = call_model(messages, tools)
    if response.uses_tools:
        results = execute_tools(response.tool_calls)
        messages.append(response)
        messages.append(results)  # Images go here too
    else:
        done = True
```

**Four tools. One loop. That's the implementation.**

### 9.11 Next Concrete Step

Build `request_view` with headless rendering. Once the model can ask "show me the fuel fill area" and receive an annotated image, everything else follows.

```python
def render_view_headless(
    artifact_graph: ArtifactGraph,
    focus: str,
    scope: str,
    annotations: List[str],
    view_angle: str = "isometric",
    resolution: Tuple[int, int] = (1024, 768)
) -> bytes:
    """
    Render artifact graph to PNG without browser.
    
    Uses: headless OpenGL (OSMesa), or export to trimesh + pyrender
    
    Returns: PNG bytes ready for base64 encoding
    """
    # 1. Extract geometry in scope
    components = artifact_graph.query_in_scope(focus, scope)
    meshes = [c.get_mesh() for c in components]
    
    # 2. Set up camera based on view_angle
    camera = compute_camera(components, view_angle)
    
    # 3. Render base image
    image = render_meshes(meshes, camera, resolution)
    
    # 4. Overlay annotations (kernel-computed, not inferred)
    if "clearances" in annotations:
        image = overlay_clearances(image, components, camera)
    if "labels" in annotations:
        image = overlay_labels(image, components, camera)
    if "dimensions" in annotations:
        image = overlay_dimensions(image, components, camera)
    if "constraints" in annotations:
        image = overlay_constraints(image, components, camera)
    
    # 5. Encode to PNG
    return encode_png(image)
```

---

*End of document.*
