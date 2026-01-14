# MAGNET North Star

<!-- AGENT_CONTEXT
Purpose: Mission statement and core equation defining MAGNET's purpose
Authoritative: Yes
Depends_On: None
Used_By: All modules, all agents
Last_Verified: 2026-01-14
-->

## The Equation

```
Human Intent → LLM → Geometry Primitives → Validating Kernel → Validated Design
```

## The Mission

MAGNET enables naval architects to explore the design space through natural language, with every design validated by physics before presentation.

## The Thesis

**Any valid vessel can be represented by composing universal geometry primitives.**

The kernel validates physics, not categories. If `hull_type` is ever required to compute hydrostatics, the architecture has failed.

## The Constraints

1. **Generative, Not Enumerative:** Designs emerge from geometry composition, not preset selection.
2. **Physics as Gate:** Only hydrostatics validation can reject a design. Everything else is advisory.
3. **Kernel Purity:** The kernel cannot import from agents. Agents cannot mutate state directly.
4. **State is Product:** DesignState is the source of truth. Exports are derived.

## The Test

If a novel hull form (not in training data) produces correct hydrostatics without code changes, the system is working.

If a novel hull form requires a new enum entry, the system has failed.

---

> The future is not a catalog of past designs. It is the space of all physically valid geometry.
