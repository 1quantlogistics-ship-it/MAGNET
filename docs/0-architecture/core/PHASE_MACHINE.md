# MAGNET Phase Machine

<!-- AGENT_CONTEXT
Purpose: Phase dependencies and state machine documentation
Authoritative: Yes
Depends_On: NORTH_STAR.md, CONSTITUTION.md
Used_By: kernel/conductor.py, all phase implementations
Last_Verified: 2026-01-14
-->

## Philosophy

**The PhaseMachine is not a design taxonomy. It is a dependency graph of consequences.**

A change in geometry (Phase 2) ripples through weight (Phase 5) and stability (Phase 6) because the laws of physics require it, not because a "vessel type" has been selected.

## Phase Definitions

| Phase | Name | Inputs | Outputs |
|-------|------|--------|---------|
| 1 | Mission | User intent | Requirements |
| 2 | Hull Form | Requirements | Geometry |
| 3 | Structure | Geometry | Scantlings |
| 4 | Arrangement | Geometry + Scantlings | Compartments |
| 5 | Propulsion | Resistance + Requirements | Power plant |
| 6 | Weight | All above | Mass distribution |
| 7 | Stability | Geometry + Weight | GM, GZ curves |
| 8 | Compliance | All above | Rule checks |
| 9 | Production | All above | Build plan |

## Dependency Graph

```
Mission (1)
    ↓
Hull Form (2) ←─────────────────┐
    ↓                           │
Structure (3)                   │
    ↓                           │
Arrangement (4)                 │
    ↓                           │
Propulsion (5)                  │
    ↓                           │
Weight (6)                      │
    ↓                           │
Stability (7) ──→ [GRADE] ─────→ Severe warning if GM < 0 (Human Decision Point)
    ↓
Compliance (8)
    ↓
Production (9)
```

## Invalidation Rules

When a phase's inputs change, it becomes `STALE`:

| If This Changes | These Become STALE |
|-----------------|-------------------|
| Mission | All phases |
| Hull Form | Structure, Arrangement, Weight, Stability, Compliance |
| Structure | Weight, Stability |
| Arrangement | Weight |
| Weight | Stability, Compliance |

## Phase States

| State | Meaning |
|-------|---------|
| `PENDING` | Not yet computed |
| `READY` | Inputs available, can compute |
| `RUNNING` | Currently computing |
| `COMPLETE` | Successfully computed |
| `STALE` | Inputs changed, needs recompute |
| `FAILED` | Computation failed |

## Gate vs Grade

### Authoritative doctrine (Unified Physics Theory)
Per `docs/1-theory/physics/MAGNET_UNIFIED_PHYSICS_THEORY.md`:
- **Gates (validity)**:
  - geometric validity (pre-gate)
  - **hydrostatics** (primary gate: “does it float?”)
- **Grades (never invalidate design)**:
  - stability (GM/GZ)
  - resistance method envelope limits
  - others

### Human Decision Point (mandatory halt for severe grades)
Stability can be *severely* wrong (e.g. GM < 0). This does not make the design “invalid”,
but it should halt automatic downstream automation until a user explicitly approves continuation.

**Rule**:
- A severe grade sets `kernel.awaiting_human_decision=true` and provides a structured request.
- The system returns the computed values + suggested fixes; the user decides “continue anyway” vs “revise”.

---

> If a phase does not consume the output of an upstream phase, it is orphaned and must be re-evaluated.
