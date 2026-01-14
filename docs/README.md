# MAGNET Documentation

<!-- AGENT_CONTEXT
Purpose: Index of all MAGNET documentation
Authoritative: Yes
Depends_On: None
Used_By: All agents, developers, contributors
Last_Verified: 2026-01-14
-->

## Overview

MAGNET is a naval architecture design system that uses LLMs to translate natural language into validated 3D hull geometry.

**The North Star Equation:**
```
Human Intent → LLM → Geometry Primitives → Validating Kernel → Validated Design
```

---

## Documentation Structure

### Architecture (`architecture/`)

Core architectural documents that define the system's philosophy and constraints.

| Document | Purpose |
|----------|---------|
| [GEOMETRY_CONVENTIONS.md](architecture/GEOMETRY_CONVENTIONS.md) | Coordinate system and geometry standards |
| [NORTH_STAR.md](architecture/NORTH_STAR.md) | Mission and core equation |
| [CONSTITUTION.md](architecture/CONSTITUTION.md) | Laws and constraints |
| [PHASE_MACHINE.md](architecture/PHASE_MACHINE.md) | Phase dependencies |

### Implementation (`implementation/`)

Implementation guides and roadmaps.

| Document | Purpose |
|----------|---------|
| [GOLDEN_PATH.md](implementation/GOLDEN_PATH.md) | Implementation guide |
| [ROADMAP.md](implementation/ROADMAP.md) | Development phases |

### Technical (`technical/`)

Technical documentation for specific subsystems.

| Document | Purpose |
|----------|---------|
| [HYDROSTATICS.md](technical/HYDROSTATICS.md) | Physics computation docs |
| [RESISTANCE.md](technical/RESISTANCE.md) | Resistance methods |
| [STABILITY.md](technical/STABILITY.md) | Stability calculations |

### Agents (`agents/`)

Documentation for LLM agent integration.

| Document | Purpose |
|----------|---------|
| [PROMPT_ARCHITECTURE.md](agents/PROMPT_ARCHITECTURE.md) | LLM context design |
| [STATE_LENS.md](agents/STATE_LENS.md) | What agents see |
| [GEOMETRY_SCHEMA.md](agents/GEOMETRY_SCHEMA.md) | Primitive reference |

---

## Quick Links

- **Getting Started:** See `README.md` in project root
- **Implementation Guide:** [GOLDEN_PATH.md](implementation/GOLDEN_PATH.md)
- **Coordinate System:** [GEOMETRY_CONVENTIONS.md](architecture/GEOMETRY_CONVENTIONS.md)

---

## For Agents

All documentation files include an `<!-- AGENT_CONTEXT -->` header with:
- `Purpose`: One-sentence description
- `Authoritative`: Whether this is the source of truth
- `Depends_On`: Required reading before this document
- `Used_By`: Which modules/agents reference this
- `Last_Verified`: Date of last verification

---

## Enumeration Warning

<!-- ENUMERATION_WARNING
This documentation must not contain:
- Vessel type → parameter mappings
- Hull family conditionals
- Style presets or catalogs
-->

The MAGNET system is **generative**, not **enumerative**. Documentation should describe:
- Geometry primitives and their composition
- Physics validation (not type-based selection)
- Continuous parameters (not categorical presets)

---

> When geometry is no longer sufficient, enumeration will try to return disguised as convenience.
