# MAGNET Mission

> **ChatGPT with a boat window.**

---

## The Goal

Human-in-the-loop engineering design spiral to enable combinatorial explosion (trillions+ of forms) because a fixed, small grammar operating on continuous geometry primitives (sections, surfaces, attachments, constraints) composes endlessly without enumerating designs—but it only truly unlocks novelty if the language can express arbitrary geometry constructions and the kernel validates outcomes rather than predefining forms.

---

## One Sentence

MAGNET is a human-in-the-loop vessel design engine where agents propose novel geometry from library-seeded starting points, mutate and compose using a declarative DSL of continuous primitives, and the kernel validates physics—enabling trillions of physically-valid forms without enumerating designs, while a canonical transactional state ensures coherence across the design spiral.

---

## The Equation

```
NOVELTY = continuous_parameters × compositional_operators × physics_validation
```

---

## Three Pillars

| Pillar | What It Means |
|--------|---------------|
| **Library Seeds, Not Blank Canvas** | Start from 30,000 validated hull forms (ShipD), blend and mutate toward user intent—novelty emerges from interpolation + topology DSL, not from scratch |
| **Compositional Grammar, Not Enumeration** | A fixed, small DSL (CREATE, ADJUST, LOFT, CONSTRAIN, LOAD, PLACE, ATTACH) operating on continuous geometry primitives composes endlessly; the kernel validates outcomes, never predefines forms |
| **Canonical State, Not LLM Memory** | DesignState is the single source of truth; agents propose, the kernel judges, transactions are atomic—coherence at scale requires the model to query and mutate only through validated operations |

---

## The Core Principle

The kernel exposes universal geometric and physical operations. Agents compose them into designs the kernel has never seen. **The kernel's only role is to validate reality, not recognize intent.**

---

## The Contract

1. **Agents propose** — in geometric primitives (surfaces, sections, bodies, constraints) composed from library seeds or invented fresh
2. **The kernel judges** — compiles geometry, runs physics, returns structured feedback; never suggests designs, never contains style knowledge
3. **State is the product** — DesignState is canonical, transactional, sliceable; LLMs reconstruct, state persists
4. **Novel designs work without new code** — if a design requires a new resource type, the system has failed

---

## We Build vs We Do NOT Build

| We Build | We Do NOT Build |
|----------|-----------------|
| A geometric/physical execution engine | AI CAD with better presets |
| Compositional primitives (surfaces, sections, bodies, constraints) | Enumerated design types ("catamaran", "stepped hull", "patrol boat") |
| Agents that invent novel geometry | Agents that select from a catalog |
| A kernel that validates physics | A kernel that recognizes design intent |
| Trillions of possible forms | Variants of predefined families |

---

## The Test

- Create a **"stepped ventilated planing hull"** using only discontinuities, flow paths, and openings. No "stepped hull" type.
- Create a **"catamaran"** using only bodies, sections, and surfaces. No "catamaran" type.
- Create a **hull configuration no naval architect has ever drawn**—and validate it without adding code.

If any test fails, we've collapsed back into enumeration.

---

## The Qualifier

Novelty comes from continuous parameters + compositional operators, not from styles or presets. As long as the language stays declarative and the kernel enforces physics/geometry constraints post-compilation, you'll get genuinely new forms—otherwise it collapses back into variants.

**Goal:** Fully cross the line from enumerated design systems to a true generative geometry language: agents propose pure geometric constructions, the kernel compiles those constructions into the existing canonical geometry pipeline, and validation happens strictly after geometry exists—so novelty is unbounded while physical truth is preserved.

---

## Why Canonical State Matters

This project is committed to full transparency: every proposal, transformation, validation, and failure must be observable, inspectable, and explainable—never hidden behind a black box.

A unified, canonical design state is the only way this scales beyond toy complexity:

- **Context windows are a UI convenience, but state is the product.**
- Design is a long-horizon computation, not a single output.
- Coherence across thousands of coupled decisions requires a shared world model.
- **LLMs do not remember—they reconstruct**, filling gaps with plausible junk when facts aren't reliably available.

Multi-agent design converges only if all agents:
- Reference the same canonical IDs
- Operate within shared coordinate frames
- Commit changes atomically
- Surface contradictions explicitly

Otherwise, you get telephone-game drift where locally correct pieces fail globally.

---

## DesignState as Single Source of Truth

In MAGNET, the LLM is not the brain of the design but a **proposal generator** operating against a durable DesignState that:

1. Serves as the **single source of truth** for geometry, derived physics, constraints, decisions, and rationale
2. Remains **decomposable** via stable IDs, ownership boundaries, and explicit interfaces
3. Is **retrievable** through targeted state lenses rather than full dumps
4. Is **strictly transactional** so edits are either rejected, warned, or atomically committed—never half-applied

---

## The Design Language

The design language is not about expressiveness but **addressability and auditability**: a narrow edit protocol for mutating state:

- `CREATE` / `MODIFY` / `DELETE`
- `ATTACH` / `ALIGN` / `LOFT` / `BOOLEAN`
- `CONSTRAIN` / `PREFER`
- With explain traces

At scale, this requires:
- A Git-like canonical state store with versioned commits
- A dependency graph to manage invalidation
- Lens-based retrieval
- Agents that propose programs rather than edits
- A compiler that enforces interfaces between shards to prevent incoherence

---

## The Next Risk

The next real risk is no longer enumeration but **state drift and interface ambiguity**.

The next unlock is not smarter prompts or more primitives, but **rigor around DesignState, lenses, transactions, and merge discipline**.

---

*If you want truly unbounded agent-driven design, memory must move out of the LLM and into a canonical, sliceable, transactional state that the model can query and mutate only through validated operations.*
