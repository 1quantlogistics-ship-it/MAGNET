# MAGNET North Star

**The Human-in-the-Loop Iterative Design Spiral**

---

## What It Should Feel Like

> **"ChatGPT for marine engineering—but with a boat window and real physics."**

The user talks to it like a chatbot. They describe what they want in plain language. But behind the conversation is a deterministic physics engine, a canonical design state, and a 3D window that shows what they're actually building—updated in real-time as the design evolves.

It's conversational AI with engineering truth. Not hallucinated renders. Not artistic interpretations. **Real geometry. Real physics. Real vessel.**

---

## The Vision in One Sentence

> **ChatGPT with a boat window**: A human-in-the-loop iterative design spiral where every change propagates through the system—upstream decisions inform downstream physics, downstream violations trigger upstream revisions—and the 3D window updates in real-time as the design converges.

---

## The Core Insight: Design is Iteration, Not Output

**Design is not a single answer. Design is a conversation.**

Traditional CAD treats design as: input parameters → run solver → get output. Done.

MAGNET treats design as: **propose → validate → learn → revise → converge**—with a human steering every iteration.

```
         ┌──────────────────────────────────────────────────────────┐
         │                  THE DESIGN SPIRAL                        │
         │                                                           │
         │    Human Intent ──► Agent Proposal ──► Kernel Validation  │
         │          ▲                                      │         │
         │          │                                      ▼         │
         │          │                              Physics Feedback  │
         │          │                                      │         │
         │          │         ◄── State Update ◄───────────┘         │
         │          │                   │                            │
         │          └───────────────────┘                            │
         │                                                           │
         │    Each loop: human sees results, decides next move       │
         │    State accumulates decisions, never forgets             │
         │    Downstream changes propagate upstream                  │
         └──────────────────────────────────────────────────────────┘
```

**The human is always in the loop.** MAGNET proposes, validates, and shows consequences—but the human decides what matters and when to stop.

---

## The Core Principle

The kernel exposes universal geometric and physical operations. Agents compose them into designs the kernel has never seen. **The kernel's only role is to validate reality, not recognize intent.**

---

## Why Iteration Changes Everything

### The Problem with Traditional Tools

| Traditional CAD | MAGNET |
|-----------------|--------|
| Change beam → manually re-run stability | Change beam → stability auto-updates |
| GM fails → start over or guess | GM fails → system shows why, suggests fix, user approves |
| Decisions forgotten between sessions | Every decision persisted with rationale |
| No memory of tradeoffs considered | Full history of alternatives explored |
| Downstream doesn't talk to upstream | Downstream violations cascade to upstream |

### The Iterative Advantage

**One change. Everything updates.**

```
User: "Increase beam by 0.5m"
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  AUTOMATIC CASCADE                                               │
│                                                                  │
│  hull.beam: 4.0 → 4.5m                                          │
│       │                                                          │
│       ├──► Sections recomputed (volume changes)                 │
│       │         │                                                │
│       │         ├──► Hydrostatics recalculated                  │
│       │         │         │                                      │
│       │         │         ├──► Displacement: 12.5 → 14.2 tonnes │
│       │         │         ├──► BMt: 1.8 → 2.1m                  │
│       │         │         └──► GM: 0.4 → 0.7m ✓ (was failing)   │
│       │         │                                                │
│       │         ├──► Resistance recalculated                    │
│       │         │         └──► +8% drag at design speed         │
│       │         │                                                │
│       │         └──► Weight estimation updated                  │
│       │                   └──► Lightship: +0.3 tonnes           │
│       │                                                          │
│       └──► Downstream phases marked STALE                       │
│             └──► stability, compliance need re-validation       │
│                                                                  │
│  3D window updates. Human sees tradeoff: better stability,      │
│  worse resistance. Human decides: acceptable? Or try something  │
│  else?                                                           │
└─────────────────────────────────────────────────────────────────┘
```

**The human didn't re-run 6 programs. The human made one decision and saw all consequences instantly.**

---

## The Bidirectional Spiral: Upstream ↔ Downstream

### Downstream Propagation (Changes Flow Forward)

When you change an upstream parameter, everything downstream that depends on it updates:

```
MISSION defines requirements
    │
    └──► HULL geometry synthesized to meet requirements
            │
            ├──► STRUCTURE sized for hull geometry
            │         │
            │         └──► WEIGHT estimated from structure
            │                   │
            │                   └──► STABILITY computed from weight
            │                             │
            │                             └──► COMPLIANCE checked
            │
            └──► PROPULSION sized for hull resistance
```

**Change mission speed → hull reshapes → structure resizes → weight changes → stability recomputes → compliance re-evaluates.**

### Upstream Feedback (Violations Flow Backward)

When downstream validation fails, the system surfaces *why* and *what upstream change would fix it*:

```
COMPLIANCE fails: GM < 0.5m required
    │
    └──► Traces back to STABILITY
            │
            └──► GM low because KG too high
                    │
                    └──► KG high because WEIGHT distribution wrong
                            │
                            └──► Weight high because STRUCTURE overbuilt
                                    │
                                    └──► Structure overbuilt because HULL too slender
                                            │
                                            └──► SUGGESTED FIX: Increase beam or reduce draft
                                                        │
                                                        └──► User approves or revises
```

**The human doesn't debug. The system shows the causal chain, suggests the upstream fix, and the user decides whether to apply it.**

---

## The Validation Model: Gate + Grades

### The Only Gate: Does It Float?

Hydrostatics is the only hard gate. If geometry doesn't displace water correctly, it's invalid—full stop.

```
GATE:  Hydrostatics — Does it float?
       │
       ├── YES → Geometry is valid, proceed to grades
       └── NO  → Invalid geometry, cannot proceed
```

### Everything Else is a Grade

All other physics results are grades with thresholds. When thresholds are crossed, warnings surface to the user. **The system suggests fixes; the user approves.**

```
GRADES (with threshold warnings):

┌─────────────────────────────────────────────────────────────────┐
│  GM < 0.5m                                                       │
│      └── ⚠️ WARNING: Marginal stability                         │
│      └── 💡 SUGGESTED FIX: Increase beam by 0.3m                │
│      └── User: [Accept] [Modify] [Override] [Ignore]            │
├─────────────────────────────────────────────────────────────────┤
│  Resistance +20% vs baseline                                     │
│      └── ⚠️ WARNING: High resistance penalty                    │
│      └── 💡 SUGGESTED FIX: Reduce wetted surface or Cp          │
│      └── User: [Accept] [Modify] [Override] [Ignore]            │
├─────────────────────────────────────────────────────────────────┤
│  Outside Holtrop-Mennen envelope (Fn > 0.45)                    │
│      └── ⚠️ WARNING: Resistance estimate extrapolated           │
│      └── 💡 INFO: Consider Savitsky method for planing regime   │
│      └── User: [Acknowledge] [Switch Method]                    │
├─────────────────────────────────────────────────────────────────┤
│  Angle of Vanishing Stability < 90°                             │
│      └── ⚠️ WARNING: Reduced capsize resistance                 │
│      └── 💡 SUGGESTED FIX: Lower VCG or increase beam           │
│      └── User: [Accept] [Modify] [Override] [Ignore]            │
└─────────────────────────────────────────────────────────────────┘

The system grades, warns, and suggests.
The human decides.
```

**Novel geometry is never blocked by grades.** If physics methods don't cover it, that's a warning—not a rejection.

---

## Human-in-the-Loop: What It Actually Means

### The Human Decides

| MAGNET Does | Human Decides |
|-------------|---------------|
| Proposes geometry changes | Whether to accept the proposal |
| Validates physics (gate + grades) | Whether grade warnings are acceptable |
| Shows tradeoffs | Which tradeoffs to make |
| **Suggests fixes for violations** | **Whether to apply the fix** |
| Tracks all alternatives | Which path to pursue |
| Remembers every decision | When the design is "done" |

### The Human Steers

```
Iteration 1: "Design a 12m patrol boat"
    └── Agent proposes hull, physics validates
    └── ⚠️ GM is marginal (0.42m)
    └── 💡 Suggested fix: Increase beam by 0.2m
    └── Human: "Accept suggested fix"

Iteration 2: Beam increased per suggestion
    └── GM improves to 0.65m ✓
    └── ⚠️ Resistance increased 12%
    └── 💡 Suggested fix: Reduce Cp or draft
    └── Human: "Ignore—resistance is acceptable for this mission"

Iteration 3: Human says "Now add a chine for spray deflection"
    └── Chine added via discontinuity primitive
    └── Physics shows improved lift at speed
    └── Human: "Good. Lock hull phase, move to structure."
```

**Every iteration: human sees state, system suggests, human decides, state updates, repeat.**

---

## Resolution = Quality, Not Enumeration

### "Viking-like" is Not a Type

There is no "Viking sportfisher" enum. There is no preset. There is only geometry at sufficient resolution.

**"Viking-like" means continuous parameters expressed with enough fidelity:**

```
Resolution requirements for high-quality hull forms:

SECTIONS:
├── Minimum 7 sections for basic form
├── Denser at bow (rapid shape change)
├── Denser at transom (critical for planing)
└── Interpolated smoothly between control sections

POINTS PER SECTION:
├── Minimum 12 points per section
├── More points where curvature is high
├── Sufficient to capture chines, knuckles, spray rails
└── Smooth B-spline or NURBS interpolation

RESOLUTION UNLOCKS CHARACTER:
├── Low resolution (3 sections, 6 points) → Generic blob
├── Medium resolution (5 sections, 10 points) → Recognizable hull
├── High resolution (7+ sections, 12+ points) → Distinctive character
└── The "Viking look" emerges from the geometry, not from a label
```

**The insight:** Quality comes from resolution. Character comes from continuous parameters. "Viking-like" is what happens when an agent proposes the right deadrise progression, sheer line, and bow flare at sufficient resolution—not when it looks up a preset.

---

## The Equation

```
NOVELTY = continuous parameters × compositional operators × physics validation
```

But novelty without iteration is just random generation. **Iteration with human feedback is design.**

```
DESIGN = NOVELTY × ITERATION × HUMAN JUDGMENT
```

---

## State is the Product (Not the Output)

### Why State, Not Files

Traditional: Work happens → Save file → File is the product

MAGNET: **Work happens IN state → State IS the product → Files are exports**

```
DesignState contains:
├── Every geometry resource with stable ID
├── Every parameter value with provenance
├── Every decision with rationale (ExplainRecord)
├── Every constraint (hard and soft)
├── Every violation and its suggested fix
├── Every phase status and gate condition
├── Every version (full Git-like history)
└── The complete audit trail of how we got here
```

### Why This Matters for Iteration

**LLMs don't remember. State remembers.**

- Pass 1: Agent proposes deep-V hull for rough water
- Pass 2: Human says "too much drag"
- Pass 3: Agent proposes moderate deadrise
- Pass 4: Human says "better, but check stability"
- Pass 5: Agent runs stability, GM marginal → suggests beam increase
- Pass 6: Human approves suggestion
- Pass 7: Final geometry converges

**Without persistent state:** By pass 7, the agent has forgotten passes 1-6. It hallucinates.

**With persistent state:** Every decision is recorded. Pass 7 reads the full history. No hallucination.

---

## The Design Spiral Phases

### The 13-Phase Workflow

```
         MISSION (what we're building)
             │
             ▼
         HULL (geometry that achieves mission)
             │
             ├────────────┬────────────┐
             ▼            ▼            ▼
       STRUCTURE    PROPULSION    ARRANGEMENT
             │            │            │
             └─────┬──────┴────────────┘
                   ▼
               WEIGHT (mass from all above)
                   │
                   ▼
              STABILITY (physics of weight distribution)
                   │
                   ▼
              COMPLIANCE ◄─── LOADING
                   │           (loading conditions)
                   │
                   ▼
             PRODUCTION (how to build it)
                   │
                   ▼
                COST (what it costs)
                   │
                   ▼
            OPTIMIZATION (make it better)
                   │
                   ▼
             REPORTING (document it)
```

### Phase Dependencies = Automatic Invalidation

When an upstream phase changes, downstream phases automatically invalidate:

```python
# User changes hull.beam
state.set("hull.beam", 5.0)

# Automatic cascade:
# ├── hull phase: geometry recomputes
# ├── structure phase: INVALIDATED (depends on hull)
# ├── propulsion phase: INVALIDATED (depends on hull)
# ├── weight phase: INVALIDATED (depends on structure, propulsion)
# ├── stability phase: INVALIDATED (depends on weight)
# ├── compliance phase: INVALIDATED (depends on stability)
# └── All downstream: INVALIDATED

# Human sees: "Hull changed. 6 phases need re-validation. Run?"
```

**No stale data. No forgotten updates. The spiral maintains coherence.**

---

## The Contract

**Agents propose.** They speak in geometric primitives—surfaces, sections, discontinuities, bodies, constraints. They can invent combinations no engineer has ever drawn.

**The kernel judges.** It compiles geometry, runs physics (gate + grades), checks constraints, and returns structured feedback with suggested fixes. It never suggests designs. It never contains style knowledge. It only answers: *can this exist, and what are the tradeoffs?*

**The human decides.** Accept, reject, modify, override, or explore alternatives. Apply suggested fixes or ignore them.

**Novel designs work without new code.** If a design requires a new resource type to express, the system has failed.

---

## What We Build vs What We Do NOT Build

| We Build | We Do NOT Build |
|----------|-----------------|
| A geometric/physical execution engine | AI CAD with better presets |
| Compositional primitives (surfaces, sections, bodies, constraints) | Enumerated design types ("catamaran", "stepped hull", "patrol boat") |
| Agents that invent novel geometry | Agents that select from a catalog |
| A kernel that validates physics (gate + grades) | A kernel that recognizes design intent |
| Trillions of possible forms | Variants of predefined families |
| **Human-in-the-loop iteration** | **Autonomous design without oversight** |
| **Bidirectional state propagation** | **One-way parameter-to-output pipelines** |
| **Resolution-based quality** | **Style presets or templates** |

---

## The 8 Constitutional Laws

### Law 1: Identity — Edit vs Rewrite Must Be Explicit
- **EDIT**: Preserve identity, mutate deltas (beam change = same boat, different beam)
- **REWRITE**: Discard most identity, preserve anchors (sportfisher→destroyer = new boat)

### Law 2: Truthfulness — No Silent Guessing
- Uncertainty MUST surface
- "I don't know" is valid and required

### Law 3: Non-Enumeration — Knowledge Lives in the LLM, Not the Kernel
- No vessel-type presets in kernel
- New vessel types require zero new code
- "Viking-like" = resolution + parameters, not a type

### Law 4: State Sovereignty — DesignState is the Only Truth
- Single Source of Truth
- Stable IDs, versioned commits, atomic transactions

### Law 5: Authority Boundaries — Who May Assert What
- Agents propose, kernel validates, **system suggests fixes**, human decides

### Law 6: Validity Envelopes — Novelty Must Not Be Punished
- Hydrostatics is the only gate (float or fail)
- Everything else is a grade with threshold warnings
- Novel geometry is never blocked

### Law 7: Convergence — Iteration Must Make Progress
- Detect thrashing (oscillation)
- Detect stalling (no improvement)
- Escalate to human, don't spin forever

### Law 8: Kill Criteria — Project Failure Conditions
- New vessel type requires new code → FAIL
- Edit silently becomes rewrite → FAIL
- Confident output without sufficient info → FAIL

---

## The Acid Test

| Test | Method | Validates |
|------|--------|-----------|
| Stepped planing hull | discontinuities + flow paths + openings | No "stepped hull" type |
| Catamaran | bodies + sections + surfaces | No "catamaran" type |
| Viking sportfisher | 7+ sections, 12+ points, proper deadrise progression | Resolution = quality, not enumeration |
| Novel configuration | Whatever the human imagines | Works without new code |
| **Iterative refinement** | Change beam → see GM update → system suggests fix → user approves → converge | **Spiral works** |
| **Upstream fix from downstream failure** | Compliance fails → traces to hull → suggests beam change → user approves | **Bidirectional flow** |

---

## The Promise

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  User: "I need a 15m crew transfer vessel for offshore wind farms" │
│                                                                     │
│  Iteration 1: Agent proposes initial hull geometry                 │
│      └── Gate: Floats ✓                                            │
│      └── Grade: GM 0.8m, resistance 12kN                           │
│      └── Human: "Looks good, but I need better seakeeping"         │
│                                                                     │
│  Iteration 2: Agent increases deadrise, adjusts bow sections       │
│      └── Gate: Floats ✓                                            │
│      └── ⚠️ Grade: GM drops to 0.5m (marginal)                     │
│      └── 💡 Suggested fix: Increase beam by 0.25m                  │
│      └── Human: "Accept fix"                                       │
│                                                                     │
│  Iteration 3: Beam increased per suggestion                        │
│      └── Gate: Floats ✓                                            │
│      └── Grade: GM 0.9m ✓, resistance +8%                          │
│      └── Human: "Acceptable tradeoff. Lock hull, move on."         │
│                                                                     │
│  Iteration 4-N: Structure, propulsion, arrangement...              │
│      └── Each phase: propose → validate → suggest → decide → next  │
│                                                                     │
│  Final: Complete, validated design with full audit trail           │
│      └── Every decision recorded                                    │
│      └── Every suggested fix and user response logged              │
│      └── Every tradeoff documented                                  │
│                                                                     │
│  No new code was written. The spiral just worked.                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Summary

**MAGNET is a human-in-the-loop iterative design spiral.**

- **One change propagates everywhere** — upstream to downstream, downstream feedback to upstream
- **Human decides at every step** — system proposes, validates, suggests fixes, human approves
- **Gate + Grades** — hydrostatics gates validity; everything else grades with threshold warnings
- **Resolution = Quality** — "Viking-like" is 7+ sections at 12+ points, not a preset
- **State accumulates intelligence** — decisions, rationale, alternatives, full history
- **Novelty is unbounded** — trillions of forms through compositional geometry
- **Physical truth is preserved** — kernel validates reality, not intent
- **Novel designs work without new code** — if it requires new types, we've failed

The equation:

```
DESIGN = NOVELTY × ITERATION × HUMAN JUDGMENT
```

The promise:

```
Describe what you want → See it validated in real-time →
System suggests improvements → You decide →
Refine until it's right → Every decision remembered
```

---

*This is the North Star. When in doubt, return here.*
