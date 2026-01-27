# Physics Documentation Index

<!-- AGENT_CONTEXT
Purpose: [TODO: Add purpose description]
Authoritative: No
Keywords: [physics, index]
Depends_On: None
Used_By: [TODO: Add users]
Status: current
Last_Verified: 2026-01-15
-->


All physics-related documentation across the MAGNET project.

---

## Theory (Foundations)

| Document | Description | Status |
|----------|-------------|--------|
| [MAGNET_UNIFIED_PHYSICS_THEORY.md](../1-theory/physics/MAGNET_UNIFIED_PHYSICS_THEORY.md) | **AUTHORITATIVE** physics kernel specification | v2.5 |
| [MAGNET_North_Star.md](../1-theory/physics/MAGNET_North_Star.md) | Physics mission statement & core equation | Current |
| [MAGNET_Physics_Gaps_And_Solutions.md](../1-theory/physics/MAGNET_Physics_Gaps_And_Solutions.md) | Gap analysis for novel forms | Reference |

## Implementation

| Document | Description | Status |
|----------|-------------|--------|
| [MAGNET_PHYSICS_RIGOR_PLAN.md](../3-implementation/physics/MAGNET_PHYSICS_RIGOR_PLAN.md) | Physics kernel upgrade plan (Simpson's rule, polygon clipping) | In Progress |

## Related Architecture

| Document | Description |
|----------|-------------|
| [GEOMETRY_CONVENTIONS.md](../0-architecture/geometry/GEOMETRY_CONVENTIONS.md) | Coordinate systems (MAGNET Standard) |
| [CONSTITUTION.md](../0-architecture/core/CONSTITUTION.md) | Laws & constraints governing physics |

## Related Geometry Theory

| Document | Description |
|----------|-------------|
| [hull_generation_deep_dive.md](../1-theory/geometry/hull_generation_deep_dive.md) | How hull geometry is generated |
| [geometry-expansion-design.md](../1-theory/geometry/geometry-expansion-design.md) | Hard chines, angular bows, spray rails |

## Related Specs

| Document | Description |
|----------|-------------|
| [MAGNET_Rendering_Quality_And_Performance.md](../4-specs/rendering/MAGNET_Rendering_Quality_And_Performance.md) | Rendering (uses physics for visualization) |

---

## Reading Order

1. **MAGNET_North_Star.md** - Understand the "why" (mission, core equation)
2. **MAGNET_UNIFIED_PHYSICS_THEORY.md** - Understand the "what" (full physics spec)
3. **MAGNET_Physics_Gaps_And_Solutions.md** - Understand the gaps
4. **MAGNET_PHYSICS_RIGOR_PLAN.md** - Understand how to improve

---

## Key Concepts

- **Hydrostatics:** Volume, displacement, center of buoyancy
- **Stability:** GM, GZ curves, righting moment
- **Resistance:** Froude method, wave-making resistance
- **Station integration:** Simpson's 1/3 rule (target upgrade)
- **Waterline clipping:** Sutherland-Hodgman algorithm (target upgrade)
