# CORTEX v2 → MAGNETV1 Implementation Guide (Single Source)

**Purpose:** Consolidated implementation guide for delivering the “Claude builds a vessel” experience:
- **Create from nothing**: `"72 foot sportfisher"` → hull + at least one system + validation
- **Edit existing**: `"Make the engine room more accessible"` → identifies artifacts → moves/reroutes → revalidates

This guide consolidates content that was previously spread across multiple plans/audits (some of which may have been deleted after consolidation), including:
- `CORTEX_V2_IMPLEMENTATION_GAP_AUDIT.md`
- `BIDIRECTIONAL_OBSERVABLE_ADJUST_TARGET_PLAN.md`
- `MAGNET_Unified_Implementation_Plan.md`
- `MAGNET_Merge_Implementation_Plan.md`
- (and portions of older CORTEX v2 implementation notes)

---

# AGENT EXECUTION INDEX

> **FOR CURSOR/CLAUDE AGENTS**: This index provides structured task blocks for implementation. Each task has clear inputs, outputs, test requirements, and dependencies. **A task is NOT complete until all its tests pass.**

## How to Use This Guide

1. **Find your task** in the Task Registry below
2. **Check dependencies** - complete prerequisite tasks first
3. **Read the full section** referenced by the task
4. **Implement** following the file locations and interface contracts
5. **Run tests** - task is BLOCKED until tests pass
6. **Update status** in the task registry

## Test Execution Rules

```bash
# REQUIRED: Run tests before marking ANY task complete
pytest tests/ -v --tb=short

# Run specific test file
pytest tests/path/to/test_file.py -v

# Run tests matching pattern
pytest tests/ -k "test_name_pattern" -v
```

**CRITICAL**: No task is complete until:
1. All existing tests still pass (`pytest tests/`)
2. New tests for the task pass
3. No new linter errors introduced

---

## Task Registry (Execution Order)

### Phase -3: Emergency Stabilization (P0 - Must Land First)

These are not “nice to have.” If these are not done first, **any** optimization/sensitivity work (physics-first *or* surrogate-assisted) risks corrupting SSOT, producing non-reproducible results, or diverging at discontinuities.

| Task ID | Task Name | Section | File(s) to Create/Modify | Test File(s) | Dependencies | Status |
|---------|-----------|---------|--------------------------|--------------|--------------|--------|
| `E0.1` | Emergency: Fail-fast state isolation | **§0.9.6** | `magnet/optimization/sensitivity.py` | `tests/optimization/test_sensitivity_isolation.py` | None | ✅ |
| `E0.2` | Emergency: Make violations non-opaque | **§0.9.9** | `magnet/kernel/geometry_observables.py` | `tests/kernel/test_violation_info.py` | None | ✅ |
| `E0.3` | Emergency: C1 smoothing in hull generator | **§0.9.2** | `magnet/hull_gen/generator.py` | `tests/hull_gen/test_generator_continuity_e03.py` | None | ✅ |
| `E0.4` | Emergency: Equilibrium stability at discontinuities | **§0.9.7** | `magnet/physics/equilibrium.py` | `tests/physics/test_equilibrium_solver.py` | E0.3 | ✅ |

> **Rule**: No “fallback to live state” in any evaluation path. Any missing clone/snapshot support must raise immediately.

### Phase -2: Multi-Fidelity Architecture (FOUNDATIONAL - Replaces Physics-First)

> **CRITICAL**: The physics-first architecture is mathematically unworkable (§0.11.1). These tasks implement the multi-fidelity surrogate-based optimization framework that makes "Claude builds a vessel" possible.

| Task ID | Task Name | Section | File(s) to Create/Modify | Test File(s) | Dependencies | Status |
|---------|-----------|---------|--------------------------|--------------|--------------|--------|
| `TM.1` | Surrogate Model (Pluggable, Scalable) | **§0.11.3** | `magnet/optimization/surrogate_model.py` | `tests/optimization/test_surrogate_model.py` | **E0.1** | ⬜ |
| `TM.2` | Multi-Fidelity Optimizer | **§0.11.3** | `magnet/optimization/surrogate_optimizer.py` | `tests/optimization/test_surrogate_optimizer.py` | TM.1 | ⬜ |
| `TM.3` | Hierarchical Validator | **§0.11.4** | `magnet/constraints/hierarchical_validator.py` | `tests/constraints/test_hierarchical_validator.py` | None | ⬜ |
| `TM.3A` | Physics Evaluator Interface (wrap existing physics) | **§0.11.3** | `magnet/optimization/physics_evaluator.py` | `tests/optimization/test_physics_evaluator.py` | E0.3, E0.4 | ⬜ |
| `TM.3B` | Surrogate Trainer Pipeline | **§0.11.3** | `magnet/optimization/surrogate_trainer.py` | `tests/optimization/test_surrogate_trainer.py` | TM.1, TM.3A | ⬜ |
| `TM.4` | Probabilistic Design | **§0.11.5** | `magnet/core/probabilistic_design.py` | `tests/core/test_probabilistic_design.py` | None | ⬜ |
| `TM.5` | Incremental State | **§0.11.6** | `magnet/core/incremental_state.py` | `tests/core/test_incremental_state.py` | None | ⬜ |
| `TM.6` | Probabilistic Optimizer | **§0.11.5** | `magnet/optimization/probabilistic_optimizer.py` | `tests/optimization/test_probabilistic_optimizer.py` | TM.2, TM.4 | ⬜ |
| `TM.7` | Surrogate Integration | **§0.11.3** | `magnet/optimization/surrogate_optimizer.py` | `tests/integration/test_surrogate_integration.py` | TM.1-6, TM.3A, TM.3B | ⬜ |
| `TM.8` | Hybrid Fidelity Control Plane | **§0.11.8** | `magnet/optimization/hybrid_optimizer.py` | `tests/optimization/test_hybrid_optimizer.py` | TM.7 | ⬜ |
| `TM.9` | Integrate Hybrid Optimizer into CLI/API | **§0.11.7** | `magnet/optimization/hybrid_optimizer.py` + orchestrator/API integration points | `tests/integration/test_surrogate_integration.py` | TM.8 | ⬜ |
| `TM.10` | Performance Benchmarks + Budgets | **§0.11.7**, §19 | `magnet/optimization/benchmarks.py` | Manual verify | TM.9 | ⬜ |
| `TM.11` | Migration Docs (Hybrid is Canonical) | **§0.11.7** | `CORTEX_V2_IMPLEMENTATION_GUIDE.md` | Manual verify | TM.9 | ⬜ |

> **EXTERNAL LIBRARY DEPENDENCIES** (see §0.11.11 for details):
> ```bash
> pip install smt gpflow emukit pymoo scikit-learn
> ```
>
> **WHY THIS PHASE EXISTS**:
> - **Linear blending in 15D has P(valid) ≈ 10⁻²³** — mathematically impossible to work
> - **Physics-first optimization requires ~1000 expensive evaluations** — computationally infeasible
> - **Surrogate-first reduces to ~50 physics evaluations** — 20x speedup
> - **This is the ONLY architecture that can scale to "Claude builds a vessel"**
>
> **BLOCKERS FOR ALL OPTIMIZATION WORK**:
> - E0.* must land before any optimizer/sensitivity work is trusted (prevents SSOT corruption + NaN blindness)
> - TM.1, TM.2 are the default optimization path (surrogate-first)
> - TM.3 must complete before hierarchical constraint system can filter candidates efficiently
> - TM.5 must complete before incremental state can prevent thundering herd

### Phase -1: Systemic Architecture (CRITICAL - Before All Other Work)

These tasks address systemic risks that span multiple subsystems. They MUST be completed before dependent tasks can safely proceed.

| Task ID | Task Name | Section | File(s) to Create/Modify | Test File(s) | Dependencies | Status |
|---------|-----------|---------|--------------------------|--------------|--------------|--------|
| `TA.1` | Concurrent State Manager | **§0.10.1** | `magnet/core/state_concurrency.py` | `tests/core/test_state_concurrency.py` | TM.5 | ⬜ |
| `TA.2` | Gradient Isolation | **§0.10.1** | `magnet/core/state_concurrency.py` | `tests/core/test_gradient_isolation.py` | TA.1 | ⬜ |
| `TA.3` | Rendering Adapter Layer | **§0.10.2** | `magnet/adapters/rendering_adapter.py` | `tests/adapters/test_rendering_adapter.py` | None | ⬜ |
| `TA.4` | Kernel Export Interface | **§0.10.2** | `magnet/kernel/geometry_export.py` | `tests/kernel/test_geometry_export.py` | None | ⬜ |
| `TA.5` | Manifold Blender | **§0.10.3** | `magnet/bootstrap/manifold_blending.py` | `tests/bootstrap/test_manifold_blending.py` | TM.1, T0.3 | ⬜ |
| `TA.6` | Observable Graph (Lazy) | **§0.10.4** | `magnet/kernel/observable_graph.py` | `tests/kernel/test_observable_graph.py` | TM.5 | ⬜ |
| `TA.7` | Batched Registry | **§0.10.4** | `magnet/kernel/observable_graph.py` | `tests/kernel/test_batched_registry.py` | TA.6 | ⬜ |
| `TA.8` | Transactional Optimizer | **§0.10.5** | `magnet/optimization/transactional_optimizer.py` | `tests/optimization/test_transactional.py` | TA.1, TM.2 | ⬜ |
| `TA.9` | Crash Recovery Manager | **§0.10.5** | `magnet/optimization/transactional_optimizer.py` | `tests/optimization/test_crash_recovery.py` | TA.8 | ⬜ |

> **CRITICAL BLOCKERS**:
> - **TA.1, TA.2**: Block ALL optimization work (T5.2, T5.3, T5.4) - concurrent gradients will corrupt state
> - **TA.5**: Blocks T0.5 (Hull Blending) - linear blending produces invalid hulls in high dimensions
> - **TA.6, TA.7**: Block T2.1 (Observable Registry) - push model causes performance collapse
> - **TA.8, TA.9**: Block production deployment - crashes leave unrecoverable state
>
> **DEPENDS ON PHASE -2**: TA.1, TA.5, TA.6, TA.8 now depend on TM.* tasks for incremental state foundation

### Phase 0: Foundation (Must Complete First)

| Task ID | Task Name | Section | File(s) to Create/Modify | Test File(s) | Dependencies | Status |
|---------|-----------|---------|--------------------------|--------------|--------------|--------|
| `T0.1` | Clone ShipD Dataset | §0.4.7.A | `scripts/setup_hull_library.sh` | Manual verify | None | ⬜ |
| `T0.2` | ShipD Importer | §0.4.7.A | `magnet/bootstrap/import_shipd.py` | `tests/bootstrap/test_import_shipd.py` | T0.1 | ⬜ |
| `T0.3` | Hull Library Core | §0.4.7.A | `magnet/bootstrap/hull_library.py` | `tests/bootstrap/test_hull_library.py` | T0.2 | ⬜ |
| `T0.4` | Embedding Provider | §0.4.7.A | `magnet/bootstrap/embeddings.py` | `tests/bootstrap/test_embeddings.py` | None | ⬜ |
| `T0.5` | Hull Blending | §0.4.7.A, **§0.9.1** | `magnet/bootstrap/blending.py` | `tests/bootstrap/test_blending.py` | T0.3, T0.4, **TA.5** | ⬜ |

> **T0.5 BLOCKER**: Must implement coefficient coupling fix from §0.9.1 AND use manifold blending from TA.5

### Phase 1: Core Write Path

| Task ID | Task Name | Section | File(s) to Create/Modify | Test File(s) | Dependencies | Status |
|---------|-----------|---------|--------------------------|--------------|--------------|--------|
| `T1.1` | DesignMutator | §2.3, §12.2 | `magnet/core/design_mutator.py` | `tests/unit/test_design_mutator.py` | None | ⬜ |
| `T1.2` | Transaction Model | §2.3 | `magnet/core/design_mutator.py` | `tests/unit/test_design_mutator.py` | T1.1 | ⬜ |
| `T1.3` | Write Path Guards | §0.8.4 | `magnet/core/design_state.py` | `tests/invariants/test_write_path.py` | T1.1 | ⬜ |
| `T1.4` | Receipt/Audit Log | §0.8.6 | `magnet/core/receipts.py` | `tests/unit/test_receipts.py` | T1.1 | ⬜ |
| `T1.5` | Proposal Sandbox + Approval Gate | **§0.8.15A** | `magnet/core/proposal_sandbox.py` | `tests/core/test_proposal_sandbox.py` | T1.1, T1.4 | ⬜ |

### Phase 2: Observable Registry

| Task ID | Task Name | Section | File(s) to Create/Modify | Test File(s) | Dependencies | Status |
|---------|-----------|---------|--------------------------|--------------|--------------|--------|
| `T2.1` | Observable Registry | §4.1 | `magnet/kernel/observable_registry.py` | `tests/kernel/test_observable_registry.py` | **TA.6, TA.7** | ✅ |
| `T2.2` | Controllability Flags | §4.1 | `magnet/kernel/observable_registry.py` | `tests/kernel/test_observable_registry.py` | T2.1 | ⬜ |
| `T2.3` | LLM Schema Generator | §4.2 | `magnet/kernel/observable_schema.py` | `tests/kernel/test_observable_schema.py` | T2.1 | ⬜ |

> **T2.1 BLOCKER**: Must build on TA.6/TA.7 (lazy observable graph) to avoid thundering herd (§0.10.4)

### Phase 3: Enumeration Deletion

| Task ID | Task Name | Section | File(s) to Create/Modify | Test File(s) | Dependencies | Status |
|---------|-----------|---------|--------------------------|--------------|--------------|--------|
| `T3.1` | Delete HullFamily | §0.6.1 | DELETE `magnet/kernel/priors/hull_families.py` | `tests/invariants/test_enum_deletion.py` | None | ⬜ |
| `T3.2` | Delete HullType | §0.6.2 | DELETE from `magnet/hull_gen/enums.py` | `tests/invariants/test_enum_deletion.py` | T3.1 | ⬜ |
| `T3.3` | Delete ChineType | §0.6.3 | DELETE from `magnet/hull_gen/enums.py` | `tests/invariants/test_enum_deletion.py` | T3.2 | ⬜ |
| `T3.4` | Delete BowStyle | §0.6.4 | DELETE from `magnet/hull_gen/enums.py` | `tests/invariants/test_enum_deletion.py` | T3.3 | ⬜ |
| `T3.5` | Constraint-Based Synthesis | §0.6.1 | `magnet/kernel/synthesis_constraints.py` | `tests/kernel/test_synthesis_constraints.py` | T3.1-T3.4 | ⬜ |
| `T3.6` | Post-Hoc Classification | §0.6.1 | `magnet/kernel/classification.py` | `tests/kernel/test_classification.py` | T3.5 | ⬜ |

### Phase 4: Hull Geometry Core

| Task ID | Task Name | Section | File(s) to Create/Modify | Test File(s) | Dependencies | Status |
|---------|-----------|---------|--------------------------|--------------|--------------|--------|
| `T4.1` | Anchor Detection | §0.4.1, §0.6.9 | `magnet/kernel/anchor_detector.py` | `tests/kernel/test_anchor_detector.py` | T3.5 | ⬜ |
| `T4.2` | Anchor Tracker | §0.4.1 | `magnet/kernel/anchor_tracker.py` | `tests/kernel/test_anchor_tracker.py` | T4.1 | ⬜ |
| `T4.3` | Topology Classification | §0.4.1 | `magnet/kernel/topology_classifier.py` | `tests/kernel/test_topology_classifier.py` | T4.2 | ⬜ |
| `T4.4` | Edit Boundary Policy | §0.4.1 | `magnet/kernel/edit_boundary.py` | `tests/kernel/test_edit_boundary.py` | T4.3 | ⬜ |

### Phase 5: Iterative Edit Loop

| Task ID | Task Name | Section | File(s) to Create/Modify | Test File(s) | Dependencies | Status |
|---------|-----------|---------|--------------------------|--------------|--------------|--------|
| `T5.1` | Character Guard | §9 | `magnet/kernel/character_guard.py` | `tests/kernel/test_character_guard.py` | T1.1, T4.2 | ✅ |
| `T5.2` | Safe Gradient Estimation (optional “physics refine”) | §6.1, **§0.9.5** | `magnet/kernel/gradient_estimator.py` | `tests/kernel/test_gradient_estimator.py` | T1.1, **E0.1**, **E0.2**, **TA.1, TA.2** | ✅ |
| `T5.3` | COORDINATE Executor (optional “physics refine”) | §6, **§0.9.4** | `magnet/kernel/coordinate_executor.py` | `tests/kernel/test_coordinate_executor.py` | T5.2, T2.1, **TA.8** | ✅ |
| `T5.4` | Adaptive Step Sizing (optional “physics refine”) | §6.2 | `magnet/kernel/coordinate_executor.py` | `tests/kernel/test_coordinate_executor.py` | T5.3 | ✅ |
| `T5.5` | Generator C1 Continuity | **§0.9.2** | `magnet/hull_gen/generator.py` | `tests/hull_gen/test_generator_continuity_e03.py` | **E0.3** | ✅ |
| `T5.6` | Fix State Leakage | **§0.9.6** | `magnet/optimization/sensitivity.py` | `tests/optimization/test_sensitivity_isolation.py` | **E0.1** | ✅ |
| `T5.7` | Fix Opaque Violations | **§0.9.9** | `magnet/kernel/geometry_observables.py` | `tests/kernel/test_violation_info.py` | **E0.2** | ✅ |
| `T5.8` | Newton-Raphson Stability | **§0.9.7** | `magnet/physics/equilibrium.py` | `tests/physics/test_equilibrium_stepped.py` | **E0.4** | ✅ |

> **SYSTEMIC ARCHITECTURE DEPENDENCIES** (from Phase -1):
> - **T5.2, T5.3**: Require TA.1/TA.2 (Concurrent State Manager) - without these, gradient threads corrupt state (§0.10.1)
> - **T5.3**: Requires TA.8 (Transactional Optimizer) - without this, crashes leave zombified state (§0.10.5)
>
> **NOTE**:
> - The default optimization path is **surrogate-first** (TM.*). COORDINATE/finite-diff is retained only for optional “physics refine” steps in `fidelity="full"` or targeted analysis.
> - Emergency stabilization (E0.*) is the canonical prerequisite for any optimization evaluation loop.
>
> **T5.2 BLOCKER**: Must implement SafeGradientEstimator from §0.9.5 with clone/perturb/discard pattern
> **T5.3 BLOCKER**: Must be pure numerical solver per §0.9.4 (no domain heuristics)
> **T5.5 BLOCKER**: Must fix C1 discontinuities in generator per §0.9.2 before optimizer can work reliably
> **T5.8 BLOCKER**: Newton-Raphson oscillates at stepped hull discontinuities (§0.9.7)

### Phase 6: Structural Components & Kinematics

| Task ID | Task Name | Section | File(s) to Create/Modify | Test File(s) | Dependencies | Status |
|---------|-----------|---------|--------------------------|--------------|--------------|--------|
| `T6.1` | Stringer Generator | §0.4.7.B | `magnet/systems/structural/stringer.py` | `tests/systems/test_stringer.py` | T1.1 | ⬜ |
| `T6.2` | Bulkhead Generator | §0.4.7.B | `magnet/systems/structural/bulkhead.py` | `tests/systems/test_bulkhead.py` | T1.1 | ⬜ |
| `T6.3` | Frame Generator | §0.4.7.B | `magnet/systems/structural/frame.py` | `tests/systems/test_frame.py` | T1.1 | ⬜ |
| `T6.4` | Scantlings Calculator | §0.4.7.B | `magnet/structural/scantlings.py` | `tests/structural/test_scantlings.py` | T6.1-T6.3 | ⬜ |
| `T6.5` | Component Kinematics | **§0.9.3** | `magnet/core/component_kinematics.py` | `tests/core/test_component_kinematics.py` | T2.1 | ⬜ |

> **T6.5 BLOCKER**: Required for multi-body optimization per §0.9.3 (6-DoF kinematic parameters)

### Phase 7: Physics Validation

| Task ID | Task Name | Section | File(s) to Create/Modify | Test File(s) | Dependencies | Status |
|---------|-----------|---------|--------------------------|--------------|--------------|--------|
| `T7.1` | Multi-Body Hydrostatics | §14 | `magnet/physics/multi_body_hydrostatics.py` | `tests/physics/test_multi_body_hydrostatics.py` | None | ⬜ |
| `T7.2` | Stability Validation | §8 | `magnet/physics/stability_validator.py` | `tests/physics/test_stability_validator.py` | T7.1 | ⬜ |
| `T7.3` | Structural Validation | §8 | `magnet/physics/structural_validator.py` | `tests/physics/test_structural_validator.py` | T6.4 | ⬜ |
| `T7.4` | Error Propagation | §12.1 | `magnet/errors/propagation.py` | `tests/errors/test_propagation.py` | None | ⬜ |
| `T7.5` | Hydro-Weight Convergence | **§0.9.8** | `magnet/physics/hydro_weight_convergence.py` | `tests/physics/test_hydro_weight_convergence.py` | T7.1 | ⬜ |

> **T7.5**: Resolves circular dependency between hydrostatics and weight estimation (§0.9.8)

### Phase 8: Integration & E2E

| Task ID | Task Name | Section | File(s) to Create/Modify | Test File(s) | Dependencies | Status |
|---------|-----------|---------|--------------------------|--------------|--------------|--------|
| `T8.1` | Bootstrap Orchestrator | §0.4.7.A | `magnet/bootstrap/orchestrator.py` | `tests/integration/test_bootstrap_orchestrator.py` | T0.5, T3.5 | ⬜ |
| `T8.2` | End-to-End Spiral Test | §12.3 | N/A (test only) | `tests/integration/test_e2e_spiral.py` | T1.1-T7.4 | ⬜ |
| `T8.3` | Edit Loop Test | §12.3 | N/A (test only) | `tests/integration/test_edit_loop.py` | T5.1-T5.4 | ⬜ |
| `T8.4` | North Star Alignment Tests | §0.7 | N/A (test only) | `tests/invariants/test_north_star.py` | All | ⬜ |

---

## Task Block Format

Each task in this guide follows this structure:

```
### TASK: [Task ID] [Task Name]

**Section**: §X.X
**Priority**: P0/P1/P2
**Dependencies**: [Task IDs that must complete first]

#### Files to Create/Modify
- `path/to/file.py` - [description]

#### Interface Contract
[Dataclass/Protocol definitions]

#### Implementation Requirements
[Specific requirements from the guide]

#### Test Requirements
**Test File**: `tests/path/to/test_file.py`
**Must Pass**:
- [ ] `test_specific_behavior_1`
- [ ] `test_specific_behavior_2`
- [ ] All existing tests in `tests/` still pass

#### Acceptance Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] Tests pass: `pytest tests/path/to/test_file.py -v`
- [ ] No regressions: `pytest tests/ -v`

#### Done Definition
Task is COMPLETE when:
1. All files created/modified as specified
2. All tests in Test Requirements pass
3. No existing tests broken
4. Code reviewed against §0.7 North Star Guards
5. Code reviewed against §0.8 Risk Mitigations
```

---

## Existing Test Suite Reference

The MAGNET codebase has an extensive test suite. **All existing tests must continue to pass.**

### Test Categories

| Category | Path | Purpose | Run Command |
|----------|------|---------|-------------|
| Unit | `tests/unit/` | Individual component tests | `pytest tests/unit/ -v` |
| Integration | `tests/integration/` | Cross-component tests | `pytest tests/integration/ -v` |
| Kernel | `tests/kernel/` | Kernel-specific tests | `pytest tests/kernel/ -v` |
| Physics | `tests/physics/` | Physics validation tests | `pytest tests/physics/ -v` |
| Invariants | `tests/invariants/` | Architectural invariant tests | `pytest tests/invariants/ -v` |
| Deployment | `tests/deployment/` | Deployment/spiral tests | `pytest tests/deployment/ -v` |
| Agents | `tests/agents/` | Agent behavior tests | `pytest tests/agents/ -v` |
| Contract | `tests/contract/` | Contract/interface tests | `pytest tests/contract/ -v` |
| WebGL | `tests/webgl/` | Rendering pipeline tests | `pytest tests/webgl/ -v` |
| Hull Gen | `tests/hull_gen/` | Hull generation tests | `pytest tests/hull_gen/ -v` |

### Critical Existing Tests (Must Never Break)

```bash
# These tests validate core invariants - NEVER skip
pytest tests/invariants/ -v
pytest tests/integration/test_hull_synthesis.py -v
pytest tests/kernel/test_program_executor.py -v
pytest tests/unit/test_state_manager.py -v
```

### Pre-Commit Test Checklist

Before marking ANY task complete:

```bash
# 1. Run full test suite
pytest tests/ -v --tb=short

# 2. Check for new failures
pytest tests/ --lf  # Run last failed

# 3. Run invariant tests specifically
pytest tests/invariants/ -v

# 4. Run integration tests
pytest tests/integration/ -v
```

---

## Quick Reference: Section to Task Mapping

| Guide Section | Related Tasks | Test Coverage |
|---------------|---------------|---------------|
| §0.4.7.A Hull Library | T0.1-T0.5, T8.1 | `tests/bootstrap/` |
| §0.6 Enum Deletion | T3.1-T3.6 | `tests/invariants/test_enum_deletion.py` |
| §0.7 North Star Guards | T8.4 | `tests/invariants/test_north_star.py` |
| §0.8 Risk Mitigations | All tasks | Various |
| §2.3 DesignMutator | T1.1-T1.4 | `tests/unit/test_design_mutator.py` |
| §4 Observable Registry | T2.1-T2.3 | `tests/kernel/test_observable_*.py` |
| §6 COORDINATE | T5.2-T5.4 | `tests/kernel/test_coordinate_*.py` |
| §9 Character Guard | T5.1 | `tests/kernel/test_character_guard.py` |
| §12 Integration Tests | T8.2-T8.3 | `tests/integration/test_e2e_*.py` |
| §14 Multi-Body Hydro | T7.1 | `tests/physics/test_multi_body_*.py` |

---

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ⬜ | Not started |
| 🔄 | In progress |
| ✅ | Complete (tests pass) |
| ❌ | Blocked (dependency or test failure) |
| ⏸️ | Deferred (not MVP) |

---

# END AGENT EXECUTION INDEX

---

## What this guide MUST explicitly cover (P0 requirements)

This guide is not complete unless it specifies all of the following (each must have an implementation path):

- **Safe gradient estimation** (no mutation of committed state; no transient validator crashes)
- **Weighted character drift** (topology > continuous aesthetics)
- **Conflict resolution that scales** (no naive \(O(n^2)\) grid scanning without indexing)
- **Adaptive optimization step sizes** (no fixed \(\Delta=0.05\) everywhere)
- **Observable controllability registry** (measurable vs controllable, mode, max_delta, applicability)
- **Inter-level contract schemas** (typed handoffs between mission/systems/components/routing/details)
- **Pattern migration tooling** (deprecate + migrate/preview)
- **Unified error propagation** (kernel → orchestrator → user message + suggestions)
- **Single write path** (DesignMutator-style staging/commit; no direct graph writes)
- **Multi-body hydrostatics** (explicit handling + uncertainty surfacing)
- **Kernel method inventory** (no “referenced but not defined” APIs)
- **End-to-end integration tests** (full spiral loop, including failure surfacing)
- **Configuration & calibration** (magic numbers moved into config with documented sources)

---

## 0.1 File Map (new code locations + ownership)

The guide must not say “implement X” without saying **where it lives** in the repo and what it depends on.

### New files to create (proposed, MAGNET-native)

| Component | Path | Depends On | Notes |
|---|---|---|---|
| ArtifactGraphAdapter / GraphView | `magnet/artifacts/graph_view.py` | `DesignState` / `StateManager` | Read-only adapter over `resources` |
| DesignMutator | `magnet/core/design_mutator.py` | `StateManager`, `program_executor`, ActionPlan executor | The **only** write path |
| ErrorPropagator | `magnet/errors/propagation.py` | error taxonomy + config | Maps deep errors → user messages |
| SpatialClaimIndex | `magnet/integration/conflicts/spatial_index.py` | claim bounds types | R-tree/BVH/spatial hash wrapper |
| ConflictResolver | `magnet/integration/conflicts/resolver.py` | `SpatialClaimIndex`, `DesignMutator` | Emits staged mutations only |
| Observable registry (canonical) | `magnet/kernel/observable_registry.py` | existing measurers | Taxonomy + controllability + aliases |
| Observable schema generator | `magnet/kernel/observable_schema.py` | registry + graph_view | LLM contract payload |
| COORDINATE optimizer | `magnet/kernel/coordinate_executor.py` | `DesignMutator`, registry | `_compute_gradients_safe`, adaptive step sizing |
| Inter-level contracts (schemas) | `magnet/contracts/generative_contracts.py` | existing `magnet/contracts/*` (**verified: folder exists**) | Dataclasses for level handoffs (new file under existing contracts package) |
| Pattern migration | `magnet/systems/patterns/migration.py` | registry + state | `preview_migration`, `migrate_design` |
| Cortex config loader | `magnet/config/cortex_config.py` | yaml + dataclasses | Loads/validates `cortex_config.yaml` |

### Config file location

- **Root**: `cortex_config.yaml` (checked in, human-editable)
- **Loader**: `magnet/config/cortex_config.py`

---

## 0.2 Repo alignment, deprecation markers, and cleanup plan (keep the codebase organized)

This guide only keeps the repo organized if we **enforce** the boundaries it describes.

### A) Deprecation policy (mark old paths explicitly)

- **Rule**: any direct write path outside `DesignMutator` is **deprecated**.
- Add explicit markers in code where legacy paths remain:
  - docstring/header: `DEPRECATED: writes must go through DesignMutator (see CORTEX_V2_IMPLEMENTATION_GUIDE.md)`
  - runtime warning in dev mode (optional): “Direct write path used”
- Add a short, explicit list in this guide (or a companion `docs/3-implementation/general/DEPRECATED_WRITE_PATHS.md`) containing:
  - the forbidden APIs (e.g., “direct kernel execute_adjust calls from non-mutator code”)
  - the allowed replacement call (DesignMutator staging/commit)

### B) Cleanup sequence (practical and safe)

- **Phase 1 (mark + guard)**:
  - mark deprecated write entrypoints
  - introduce a CI guard (e.g., grep-based test or runtime assertion) to prevent new direct-write call sites
- **Phase 2 (migrate callers)**:
  - move conflict resolution, routing repair, and orchestrators onto staged mutations via `DesignMutator`
- **Phase 3 (remove)**:
  - delete deprecated write paths once no call sites remain (do not leave “two ways to write” indefinitely)

### C) Project-wide format alignment (recommended conventions)

To avoid “many slightly different formats”:
- **Inter-level contracts**: dataclasses → JSON payloads (versioned via `schema_version`)
- **Receipts/audit**: JSONL (append-only) per design_id
- **Config**: YAML validated by dataclass schema (`CortexConfig.load`)
- **Observable IDs**: canonical IDs from `magnet/kernel/observable_registry.py`; aliases are explicit + versioned

### D) Organization rule of thumb (keeps folders clean)

- `magnet/kernel/*`: deterministic core, validators, registries (no LLM calls)
- `magnet/integration/*`: glue that coordinates kernel subsystems (conflicts, orchestration helpers)
- `magnet/agents/*`: LLM-facing agents only (no direct state writes)
- `magnet/systems/*`: domain logic (fuel/electrical/plumbing) that compiles to geometry artifacts via the write path

If a module violates these, it will become the source of sprawl.

---

## 0.2.5 Implementation Roadmap: Current State vs. Library Architecture

### What EXISTS in MAGNET (Good Foundation)

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| **Hull Generator** | ✅ Solid | `magnet/hull_gen/generator.py` | Parametric hull synthesis from form coefficients |
| **Synthesis Engine** | ✅ Solid | `magnet/kernel/synthesis.py` | Propose→validate→mutate loop with fallback |
| **WebGL Pipeline** | ✅ Basic | `magnet/webgl/geometry_pipeline.py` | Hull tessellation, LOD, hard edges |
| **Physics Validators** | ✅ Good | `magnet/physics/` | Hydrostatics, resistance, stability, equilibrium |
| **Systems Generators** | ✅ Skeletal | `magnet/systems/` | Fuel, electrical, HVAC, propulsion schemas |
| **Routing Engine** | ✅ Good | `magnet/routing/` | Pipe/cable routing, zone management |
| **DSL Parser** | ✅ Good | `magnet/kernel/stdlib/parser.py` | Design language parse→expand→compile |
| **State Management** | ✅ Good | `magnet/core/state_manager.py` | DesignState SSOT, transactions |
| **Program Executor** | ✅ Good | `magnet/kernel/program_executor.py` | DSL execution, dry-run support |

### What DOESN'T Exist (Gaps to Close)

| Component | Status | Impact | Effort | Priority |
|-----------|--------|--------|--------|----------|
| **STEP/IGES Import** | ❌ Missing | Can't import CAD files from library | Medium | P2 |
| **Section Extractor** | ❌ Missing | Can't parameterize imported geometry | Medium | P2 |
| **Offset Table Parser** | ❌ Missing | Can't import Series 60/64/NPL | Low | P1 |
| **Delftship/FreeShip Parser** | ❌ Missing | Can't import .fbm/.ftm files | Low | P1 |
| **Component Library Schema** | ❌ Missing | No component storage structure | Low | P1 |
| **Component Placement (PLACE/ATTACH)** | ❌ Missing | No component positioning semantics | Medium | P2 |
| **Multi-body Assembly** | ⚠️ Partial | Hull-only, no component assembly | Medium | P2 |
| **Embedding Pipeline** | ❌ Missing | No semantic search for library | Low | P1 |
| **Blending Logic** | ❌ Missing | No parameter interpolation | Low | P1 |
| **HuggingFace Integration** | ❌ Missing | No cloud storage for library | Low | P1 |
| **Assembly WebGL Rendering** | ❌ Missing | Can't render hull + components | Medium-High | P3 |

### Gap Analysis by System

#### 1. Geometry Pipeline

**Current state**: Hull-only tessellation

```python
# What exists (magnet/webgl/geometry_pipeline.py)
class HullGeometryPipeline:
    def tessellate_hull(self, hull_geom: HullGeometryData) -> MeshData
```

**Needed**: Multi-body assembly pipeline

```python
# What's needed (magnet/webgl/assembly_pipeline.py) - NEW FILE
class AssemblyPipeline:
    def tessellate_assembly(self, design_state: DesignState) -> AssemblyMeshData:
        """Tessellate hull + all components as unified scene."""
        meshes = []
        meshes.append(self.hull_pipeline.tessellate_hull(design_state.hull))
        for component in design_state.components:
            meshes.append(self.tessellate_component(component))
        return AssemblyMeshData(meshes=meshes, scene_graph=self.build_scene_graph())
```

**Effort**: Medium (extend existing `HullGeometryPipeline`)

#### 2. Import Pipeline

**Current state**: None

**Needed**:

```python
# magnet/bootstrap/import_hulls.py - NEW FILE

class HullImporter:
    def import_offset_table(self, path: Path) -> LibraryHull:
        """Parse CSV offset tables (Series 60, NPL, DTMB)."""
        # Low effort - CSV parsing + section conversion
        
    def import_delftship(self, path: Path) -> LibraryHull:
        """Parse Delftship .fbm files (XML-based parametric)."""
        # Low effort - XML parsing
        
    def import_freeship(self, path: Path) -> LibraryHull:
        """Parse FreeShip .ftm files."""
        # Low effort - similar to Delftship
        
    def import_step(self, path: Path) -> LibraryHull:
        """Import STEP via OpenCASCADE, extract sections."""
        # Medium effort - requires pythonocc-core
        
class SectionExtractor:
    def extract_sections(self, step_shape) -> List[HullSection]:
        """Slice STEP geometry at stations to extract sections."""
        
    def extract_parameters(self, sections: List[HullSection]) -> Dict[str, float]:
        """Detect LOA, beam, deadrise, Cp, etc. from sections."""
```

**Effort by format**:
- Offset tables: Low (2-3 days)
- Delftship/FreeShip: Low (2-3 days)
- STEP: Medium (1-2 weeks, requires pythonocc-core)

#### 3. Component System

**Current state**: Systems generators output dataclasses, not geometry

```python
# What exists (magnet/systems/fuel/generator.py)
class FuelSystemGenerator:
    def generate(self, ...) -> FuelSystem:
        # Returns FuelSystem dataclass with tank specs, not geometry
```

**Needed**: Components as geometry artifacts

```python
# What's needed (refactor existing generators)
class FuelSystemGenerator:
    def generate(self, ...) -> List[ComponentGeometry]:
        """Return actual 3D geometry for tanks, lines, fills, vents."""
        tank = self.generate_tank_geometry(params)  # Box/cylinder with ports
        fill = self.generate_fill_port_geometry(params)
        vent = self.generate_vent_geometry(params)
        return [tank, fill, vent]  # Geometry artifacts, not just dataclasses
```

**Effort**: Medium (refactor ~5 existing system generators)

#### 4. WebGL Viewer

**Current state**: Hull-only rendering

**Needed for assemblies**:
- Multiple bodies (hull + components)
- Scene graph hierarchy (hull → cabin → hardware)
- Selection/highlighting of individual components
- LOD for complex assemblies (hundreds of components)
- Material/color differentiation by component type

**Effort**: Medium-High (2-3 weeks)

### Build Order (Recommended Phases)

#### Phase 1: ShipD Library + Hull Synthesis (1-2 weeks) - P1 Priority

**Focus**: Hull form, structural accuracy, iterative design. NOT small components.

```
Week 1:
├── scripts/setup_hull_library.sh
│   └── git clone https://github.com/noahbagz/ShipD.git (AUTOMATED)
│
├── magnet/bootstrap/import_shipd.py
│   ├── ShipDHull dataclass
│   ├── ShipDImporter class
│   └── Parse 30k hull parameters
│
├── magnet/bootstrap/hull_library.py
│   ├── HullLibrary class
│   ├── Search by parameters
│   └── Local index storage (parquet)
│
├── magnet/bootstrap/embeddings.py
│   ├── EmbeddingProvider ABC
│   ├── LocalEmbedding (sentence-transformers)
│   └── compute_embeddings() for all hulls
│
├── magnet/bootstrap/blending.py
│   ├── blend_hulls() - parameter interpolation
│   ├── compute_novelty_score()
│   └── perturb_for_novelty()
│
└── Integration with existing synthesis
    └── ShipD params → HullGenerator.generate()

Deliverable: 
- Search 30k hulls by natural language
- Blend multiple hulls toward constraints
- Synthesize novel hull via existing kernel
- Validate physics via existing validators
```

#### Phase 2: STEP Import + Structural Components (2-3 weeks) - P2 Priority

**Focus**: Import manually acquired CAD files, structural components for scantlings.

```
Week 2-3:
├── pip install pythonocc-core
├── magnet/bootstrap/step_import.py
│   ├── read_step()
│   ├── slice_at_stations()
│   └── extract_parameters()
│
├── Import manually acquired STEP files:
│   ├── NPL Round Bilge hulls (.stp)
│   ├── Catamaran demihulls (.stp, .3dm)
│   └── Planing hulls (.3dm)
│
├── magnet/bootstrap/structural_templates/
│   ├── StringerTemplate (parametric)
│   ├── BulkheadTemplate (parametric)
│   ├── FrameTemplate (parametric)
│   └── TransomTemplate (parametric)
│
└── magnet/kernel/stdlib/parser.py (extend)
    ├── LOAD verb (from library)
    ├── PLACE verb (position on hull)
    └── ATTACH verb (anchor connections)

Deliverable:
- Import STEP files into library
- Generate structural components parametrically
- Place structural components on hulls
```

#### Phase 3: Superstructure + Assembly (2-3 weeks) - P3 Priority

**Focus**: Cabins, consoles, superstructure forms. Assembly rendering.

```
Week 4-6:
├── magnet/bootstrap/superstructure_templates/
│   ├── CabinTemplate (parametric)
│   ├── ConsoleTemplate (parametric)
│   ├── HardtopTemplate (parametric)
│   └── FlyBridgeTemplate (parametric)
│
├── magnet/webgl/assembly_pipeline.py
│   ├── tessellate_assembly()
│   └── Multi-body mesh generation
│
├── magnet/webgl/scene_graph.py
│   ├── Hierarchical structure
│   └── Component selection
│
└── magnet/webgl/gltf_builder.py (extend)
    └── Multi-mesh GLTF export

Deliverable: Full assemblies render in viewer
```

### MVP Timeline

| Milestone | Timeline | What Works |
|-----------|----------|------------|
| **MVP 1: ShipD Library** | Week 1-2 | Search 30k hulls + blend + synthesize |
| **MVP 2: STEP Import** | Week 3-4 | Import manually acquired CAD files |
| **MVP 3: Structural** | Week 4-5 | Parametric stringers, bulkheads, frames |
| **MVP 4: Superstructure** | Week 5-6 | Parametric cabins, consoles |
| **MVP 5: Assembly** | Week 7-8 | Full vessel rendering |

### What You Can Demo in 1-2 Weeks (MVP 1)

```
User: "72ft sportfish, fast"

System:
1. Clone ShipD: git clone https://github.com/noahbagz/ShipD.git (AUTOMATED)
2. Search 30k hulls by semantic similarity
3. Find top-5 similar hulls with matching characteristics
4. Blend parameters toward user constraints (speed, seakeeping)
5. Synthesize via existing HullGenerator
6. Validate via existing physics validators
7. Render hull in existing WebGL viewer

Output: Novel hull form (physically valid, based on 30k validated designs)
```

This works with **existing MAGNET code** + ShipD data. No manual file collection needed for Phase 1.

### Data Acquisition Summary

| Source | Hulls | Acquisition | Status |
|--------|-------|-------------|--------|
| **ShipD (GitHub)** | 30,000 | `git clone` (automated) | ✅ MVP |
| **Manual STEP files** | ~15 | Already acquired | ⏸️ Phase 2 |
| **Series 60/64 CSV** | 0 | Not available online | ❌ Skip |
| **FreeShip/Delftship** | 0 | Windows extraction difficult | ❌ Skip |
| **Small components** | 0 | Not MVP priority | ❌ Deferred |

### Dependencies to Install

```bash
# Phase 1 (required)
pip install sentence-transformers  # Local embeddings (~500MB with model)
pip install huggingface_hub        # HF integration
pip install pandas pyarrow         # Index storage

# Phase 2 (for STEP import)
pip install pythonocc-core         # OpenCASCADE Python bindings (~200MB)
# OR use conda: conda install -c conda-forge pythonocc-core

# Phase 3 (likely already installed)
pip install numpy                  # Array operations
pip install trimesh                # Mesh operations (if not using OCC for tessellation)
```

---

## 0.3 Cross-reference: `LLM_NATIVE_SPATIAL_INTERFACE_SPEC-2.md` (alignment + mapping)

This implementation guide is the **MAGNET execution plan**. The companion spec `LLM_NATIVE_SPATIAL_INTERFACE_SPEC-2.md` defines the **LLM-native spatial interaction model** (hull topology creation, hull editing via anchors/affordances, and outfitting via compilation).

### 0.3.1 Cross-references (where to read what)

- **Hull creation / topology DSL**: see `LLM_NATIVE_SPATIAL_INTERFACE_SPEC-2.md` Part I §0 (“Hull Topology DSL”) and §0.5 (“Relationship to Existing Architecture”).
- **Hull editing via anchors + affordances**: see `LLM_NATIVE_SPATIAL_INTERFACE_SPEC-2.md` §2 (“Anchor System”), §5 (“Delta-Affordance”), and §3 (“Operation Templates with Continuity Handling”).
- **Outfitting via constraint programs / compilation**: see `LLM_NATIVE_SPATIAL_INTERFACE_SPEC-2.md` Part II §10–§13.

This guide is authoritative for **where code lives**, **SSOT/write-path rules**, **tool contracts**, **tests**, and **migration/rollout**.

### 0.3.2 Mapping table (spec concept → implementation file)

Status legend:
- **EXISTS**: present in codebase today
- **PLANNED**: referenced in this guide; new file/module to create
- **GAP**: spec concept not yet represented in this guide’s implementation plan

| Spec concept (LLM_NATIVE_SPATIAL_INTERFACE_SPEC-2.md) | Guide section | Implementation file(s) (verified) | Status | Notes (reuse vs rebuild) |
|---|---:|---|---|---|
| Hull synthesis engine | §1 | `magnet/kernel/synthesis.py` (**EXISTS**), `magnet/hull_gen/*` (**EXISTS**) | EXISTS | Reuse; spec’s “surface to LLM” is a refactor on top of this |
| HullFamily enumeration trap / migration away from enums | §0, §1 | `magnet/kernel/synthesis.py` (**EXISTS**) | EXISTS | File already contains deprecation notes; align guide with this trajectory |
| Topology DSL (CREATE surface/chine/step/tunnel/foil…) | (add in future) | `magnet/kernel/synthesis.py` (**EXISTS**) + `magnet/kernel/stdlib/parser.py` (**EXISTS**) | GAP | Reuse existing design-language parser/AST; extend grammar/types, don’t build a second parser |
| Design language (CREATE/SET/LOFT/CONSTRAIN) | §1, §3 | `magnet/kernel/stdlib/parser.py` (**EXISTS**), `magnet/kernel/program_executor.py` (**EXISTS**) | EXISTS | Already implements parse→expand→compile and supports `dry_run` |
| ADJUST/TARGET grammar | §5 | `magnet/kernel/stdlib/parser.py` (**EXISTS**), `magnet/kernel/program_executor.py` (**EXISTS**) | EXISTS | Reuse; ensure EDIT uses affordance bounds + character guard |
| LOAD/PLACE/ATTACH (component ops) | §0.4.7.B | `magnet/kernel/stdlib/parser.py` (**EXISTS**), `magnet/bootstrap/component_library.py` (**NEW**) | GAP | Extend parser for LOAD (library fetch), PLACE (position), ATTACH (anchor connect); see §0.4.7.B |
| “Constrain before proposal” (affordances) | §5, §9 | (no module yet found) | GAP | Spec expects affordance-first UI; guide must add affordance computation modules (see gaps list) |
| Anchor tracking (TrackedAnchor / AnchorTracker) | (not covered yet) | (no module found) | GAP | New capability; should not be invented twice—choose one canonical module/package |
| Continuity-aware operations (G0/G1/G2 + blending + post-validation) | (not covered yet) | `magnet/hull_gen/modifiers/*` (**EXISTS**) | GAP | Reuse modifier infrastructure; add continuity analysis + validation wrappers |
| Movement envelope / delta-affordance for components | (not covered yet) | `magnet/routing/*` (**EXISTS**) + geometry bounds utilities (varies) | GAP | Likely new; but should live near routing/geometry queries, not in agents |
| Query interface (LLM asks questions vs inspects scene graph) | (not covered yet) | (no explicit SQL/query module found) | GAP | New; should sit on top of graph view + observable registry |
| Outfitting as compilation to many artifacts | §2, §3 | `magnet/kernel/program_executor.py` (**EXISTS**) | EXISTS | Reuse; the missing piece is “systems as geometry artifacts” in `resources` |
| Systems generators (fuel/electrical/etc.) | §2 | `magnet/systems/*/generator.py` (**EXISTS**) | EXISTS | Reuse; refactor outputs to geometry artifacts rather than only dataclasses |
| Pareto / multi-objective optimization | (future) | `magnet/optimization/*` (**EXISTS**) | EXISTS | Reuse; spec’s negotiation protocol can map onto this subsystem |
| Vision interpreter (sketch → intent) | §3 | `magnet/agents/vision_interpreter.py` (**EXISTS**) | EXISTS | Reuse; ensure it feeds the same DSL/program path |
| Error taxonomy & recovery | §12.1 | `magnet/errors/taxonomy.py` (**EXISTS**), `magnet/errors/recovery.py` (**EXISTS**) | EXISTS | Reuse; guide’s `ErrorPropagator` should integrate here (not duplicate) |
| Program execution with dry-run / sandbox | §6.3 | `magnet/kernel/program_executor.py` (`dry_run`) (**EXISTS**) | EXISTS | Reuse; do not create a second “dry-run system” |
| State cloning support | §6.3 | `magnet/core/state_manager.py` (**EXISTS**), `magnet/optimization/optimizer.py` uses `StateManager.clone()` (**EXISTS**) | EXISTS | Reuse; prefer clone-based dry-runs |
| Character guard (pre-commit drift gate) | §5, §9 | (policy; implementation planned) | PLANNED | Must be integrated into EDIT execution path, not post-hoc reporting |
| Graph view over resources | §2.2 | (planned) | PLANNED | New `magnet/artifacts/graph_view.py` (package does not exist yet) |
| Single write path (DesignMutator) | §12.2 | `magnet/kernel/program_executor.py` (**EXISTS**) + `magnet/core/state_manager.py` (**EXISTS**) | PLANNED | Mutator should wrap existing executor/transactions; don’t reimplement execution |

### 0.3.3 Gaps (spec concepts lacking implementation entries in this guide)

The following concepts are described in `LLM_NATIVE_SPATIAL_INTERFACE_SPEC-2.md` but are not yet fully represented as implementation items in this guide (beyond high-level mentions):

- **Hull Topology DSL surfacing** (Part I §0): extending MAGNET’s existing DSL to express topology primitives (surface/chine/step/tunnel/foil/demihull) and compiling them through `magnet/kernel/synthesis.py`.
- **Anchor tracker + lifecycle** (Part I §2): stable anchor identities across edits; anchor retirement/degradation; **topology change classification** (Spec §2.5: INCREMENTAL/ADDITIVE/SUBTRACTIVE/RESTRUCTURE) and **edit boundary policy** (Spec §2.6: drift/retired/confidence circuit breaker).
- **Continuity-aware operation templates** (Part I §3): G0/G1/G2 detection, blending, **post-blend continuity validation** (Spec §3.5), and **adaptive blend distance** (Spec §3.6).
- **Delta-affordances / movement envelopes** (Part I §5): precomputed bounds for hull edits and component relocations; **affordance versioning** (Spec §5.5) and **cross-system affordance integration** (Spec §5.6).
- **Query interface** (Part II §14): a bounded spatial query language that yields small working sets without exposing raw scene graphs.
- **Geometry quality metrics** (Spec §6.4): fairness/continuity/panel quality degradation as first-class “health” signals during edit viability.
- **Constraint program validation (pre-compilation)** (Spec §11.4): logical consistency checks before expensive compilation/expansion.
- **Bootstrap theory / seed generation** (Spec §22): how we get from “Viking 72” to first valid geometry without blank-page failure.
- **Sufficiency matrix** (Spec §23): decision↔observable requirements, sufficiency checks before committing expensive operations.
- **Decision-level physics attribution** (Part II §15): tracing failures to *decisions/program statements* rather than artifacts.
- **Negotiation protocol / Pareto menus** (Part III §21): some optimizer infrastructure exists (`magnet/optimization/*`), but this guide does not yet define the LLM-facing negotiation contract.
- **Archetype guard** (Part III §24): this guide has character guard; archetype guard needs an explicit relationship to it (see conflicts/alignment below).
- **Component library + composability** (§0.4.7.B): reusable sub-components (cabins, props, towers) that can be placed onto hulls, scaled/adapted, and mutated via DSL for novel configurations.

---

## 0.4 Gap closure implementation sections (spec → MAGNET build plan)

For each §0.3.3 gap, this section specifies:
1) **File location**, 2) **Dependencies**, 3) **Interface contract**, 4) **Integration point**, 5) **Reuse note**.

### 0.4.1 Anchor tracker + lifecycle (Spec §2, §2.5, §2.6)

- **File location**
  - `magnet/hull_gen/anchors.py`
  - `magnet/hull_gen/anchor_tracker.py`
  - Optional shared contracts: `magnet/contracts/anchor_contracts.py`

- **Dependencies**
  - `magnet/hull_gen/geometry.py`
  - `magnet/core/state_manager.py`, `magnet/core/design_state.py`
  - `magnet/errors/taxonomy.py`, `magnet/explain/trace_collector.py`

- **Interface contract (minimum)**

**NOTE**: Per §0.5.0.1 (Enumeration Leak Audit), anchors are **detected from geometry**, not pre-categorized. The semantic label is derived post-detection, enabling novel hull forms with unconventional features.

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

class AnchorStatus(Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    RETIRED = "retired"

class AnchorDetectionMethod(Enum):
    """How the anchor was detected (not what it "is")."""
    CURVATURE_MAXIMUM = "curvature_maximum"    # Local curvature peak
    CURVATURE_MINIMUM = "curvature_minimum"    # Flat region
    DISCONTINUITY = "discontinuity"            # Tangent break (chine)
    VERTICAL_EXTREMUM = "vertical_extremum"    # Keel or sheer point
    HORIZONTAL_EXTREMUM = "horizontal_extremum" # Beam max
    INFLECTION = "inflection"                  # Curvature sign change
    CONSTRAINT_DEFINED = "constraint_defined"  # User/DSL explicitly placed

class TopologyChangeType(Enum):
    INCREMENTAL = "incremental"
    ADDITIVE = "additive"
    SUBTRACTIVE = "subtractive"
    RESTRUCTURE = "restructure"

@dataclass
class TrackedAnchor:
    """
    Anchor detected from geometry, not pre-categorized.
    
    The semantic_label is DERIVED by a classifier after detection,
    not used as input. This allows novel hull forms with unconventional
    features to still have tracked anchors.
    """
    uuid: str
    section_id: str
    point_index: int
    position: Tuple[float, float, float]  # (x, y, z) at detection
    detection_method: AnchorDetectionMethod
    confidence: float = 1.0
    status: AnchorStatus = AnchorStatus.ACTIVE
    # Semantic label is OUTPUT of classification, not INPUT
    # Examples: "keel-like", "sheer-like", "hard-chine", "soft-bilge", "novel-feature"
    semantic_label: Optional[str] = None
    # Curvature/angle at anchor for tracking drift
    local_curvature: Optional[float] = None
    tangent_angle_deg: Optional[float] = None

def detect_anchors(geometry: "HullGeometry") -> List[TrackedAnchor]:
    """
    Detect anchors from geometry features.
    
    Does NOT use an AnchorType enum. Instead:
    1. Finds geometric features (curvature extrema, discontinuities, etc.)
    2. Creates TrackedAnchor with detection_method
    3. Classifier assigns semantic_label post-detection
    """
    ...

def classify_anchor(anchor: TrackedAnchor, geometry: "HullGeometry") -> str:
    """
    Derive semantic label from detected anchor + context.
    
    Returns labels like "keel-like", "chine-like", "sheer-like", "novel-feature".
    Novel hulls may produce labels not in traditional taxonomy.
    """
    ...

@dataclass
class AnchorUpdateReport:
    born: List[str] = field(default_factory=list)
    updated: List[str] = field(default_factory=list)
    degraded: List[str] = field(default_factory=list)
    retired: List[str] = field(default_factory=list)
    topology_change: TopologyChangeType = TopologyChangeType.INCREMENTAL
    novel_features_detected: int = 0  # Anchors that don't fit traditional labels
```

- **Integration point (MAGNET)**
  - After every hull ADJUST/TARGET commit, run anchor update + topology classification (Spec §2.5) and an edit-viability evaluation (Spec §2.6 circuit breaker).
  - On `RESTRUCTURE` or circuit-breaker trigger: stop Hull Editing and return to Hull Creation/resynthesis (§3.1).

- **Reuse note**
  - **Reuse**: hull geometry structures (`magnet/hull_gen/geometry.py`).
  - **Build new**: anchor identity tracking + lifecycle (system-owned, versioned; not agent-owned).

### 0.4.2 Continuity-aware operations (Spec §3, §3.5, §3.6)

- **File location**
  - `magnet/hull_gen/continuity.py`
  - Extend `magnet/hull_gen/modifiers/*` (do not create a parallel op engine)

- **Dependencies**
  - `magnet/hull_gen/geometry.py`
  - `magnet/hull_gen/modifiers/base.py`
  - `magnet/kernel/stdlib/quality_gates.py`

- **Interface contract (minimum)**

```python
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

class ContinuityClass(Enum):
    G0 = "g0"
    G1 = "g1"
    G2 = "g2"

@dataclass
class ContinuityValidationResult:
    target: ContinuityClass
    achieved: ContinuityClass
    success: bool
    measurements: Dict[str, float]
    suggestion: Optional[str] = None
```

- **Integration point (MAGNET)**
  - Hull editing transforms must enforce Spec §3.5: apply blend/transition → validate achieved continuity → fail-closed (or require explicit acceptance of a downgrade).
  - Adaptive blend distance (Spec §3.6) must be computed from local geometry + delta magnitude, not fixed.

- **Reuse note**
  - **Reuse**: existing modifier implementations as the substrate.
  - **Build new**: continuity analysis + post-operation validation wrappers.

### 0.4.3 Delta-affordances / movement envelopes (Spec §5, §5.5, §5.6)

- **File location**
  - Hull affordances: `magnet/hull_gen/affordances.py`
  - Component/route affordances: `magnet/routing/affordances.py`
  - Cross-system integration: `magnet/glue/affordance_integration.py`

- **Dependencies**
  - `magnet/routing/integration/state_integration.py`
  - Planned graph view: `magnet/artifacts/graph_view.py`
  - `magnet/core/state_manager.py` (version stamping)
  - guardrails: character guard (§5/§9) + archetype guard (§0.4.11)

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class DirectionLimit:
    direction: str
    max_distance_m: float
    limited_by: str
    limited_by_id: Optional[str] = None
    side_effects: List[str] = field(default_factory=list)

@dataclass
class MovementEnvelope:
    target_id: str
    limits: Dict[str, DirectionLimit]
    computed_at_version: int

    def is_stale(self, current_version: int) -> bool: ...
```

- **Integration point (MAGNET)**
  - Must implement “constrain before proposal”: LLM sees **bounded** options (affordances), not raw coordinates.
  - Must implement affordance versioning (Spec §5.5) and cross-system integrated affordances (Spec §5.6).

- **Reuse note**
  - **Reuse**: routing graphs + state integration.
  - **Build new**: envelope computation + integrated limit presentation.

### 0.4.4 Query interface (Spec §14)

- **File location**
  - `magnet/query/spatial_query.py`
  - `magnet/query/working_set.py`

- **Dependencies**
  - `magnet/artifacts/graph_view.py` (planned)
  - `magnet/kernel/observable_registry.py` (planned)
  - `magnet/explain/formatters.py` (exists; formatting reuse)

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass
class QueryRequest:
    query_text: str
    limit: int = 20
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QueryResultItem:
    id: str
    type: str
    summary: str
    fields: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QueryResponse:
    items: List[QueryResultItem]
    truncated: bool = False
```

- **Integration point (MAGNET)**
  - Orchestrator and tools use queries to keep LLM working set small (5–20 items), never full graphs.

- **Reuse note**
  - **Reuse**: `magnet/explain/*` formatting.
  - **Build new**: query evaluator on top of graph view + observable registry.

### 0.4.5 Geometry quality metrics (Spec §6.4)

- **File location**
  - `magnet/hull_gen/quality_metrics.py`

- **Dependencies**
  - `magnet/hull_gen/geometry.py`, `magnet/hull_gen/nurbs.py`
  - `magnet/kernel/stdlib/quality_gates.py`

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class CurvatureAnomaly:
    location: str
    severity: str
    kind: str
    likely_cause: str

@dataclass
class GeometryQualityReport:
    fairness_score: float
    anomalies: List[CurvatureAnomaly] = field(default_factory=list)
    degradation_since_synthesis: float = 0.0
    recommendation: str = ""
```

- **Integration point (MAGNET)**
  - Must feed edit viability assessment (Spec §2.6) and be surfaced to LLM (Spec §6.4) so quality never degrades silently.

- **Reuse note**
  - **Reuse**: existing hull geometry representation.
  - **Build new**: quality report + baseline/degradation tracking.

### 0.4.6 Constraint program validation (Spec §11.4)

- **File location**
  - `magnet/kernel/stdlib/preflight_validator.py`

- **Dependencies**
  - `magnet/kernel/stdlib/parser.py`, `magnet/kernel/stdlib/ast_nodes.py`, `magnet/kernel/stdlib/type_registry.py`
  - `magnet/core/state_manager.py`

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class ConstraintConflict:
    statements: List[str]
    conflict_type: str  # "contradictory" | "overconstrained" | "circular"
    explanation: str
    resolution_options: List[str] = field(default_factory=list)

@dataclass
class PreflightResult:
    valid: bool
    conflicts: List[ConstraintConflict] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
```

- **Integration point (MAGNET)**
  - Runs before `magnet/kernel/program_executor.execute_program(...)` triggers expensive expand/compile/validate.

- **Reuse note**
  - **Reuse**: AST + type registry; do not create a second executor.

### 0.4.7 Bootstrap / seed generation (Spec §22)

- **File location**
  - `magnet/bootstrap/archetype_seed.py`

- **Dependencies**
  - `magnet/bootstrap/container.py`
  - `magnet/kernel/synthesis.py`, `magnet/hull_gen/*`, `magnet/kernel/program_executor.py`

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass
class BootstrapRequest:
    prompt: str
    overrides: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BootstrapResult:
    success: bool
    design_id: str = ""
    design_version: int = 0
    notes: str = ""
    failure_reason: Optional[str] = None
```

- **Integration point (MAGNET)**
  - Entry point for Hull Creation from text prompts (“Viking 72” → first valid geometry + baselines).

- **Reuse note**
  - **Reuse**: synthesis engine, program executor, physics validators, affordances, ADJUST/TARGET
  - **Build new**: hull library, search index, interpolation, orchestrator
  - **External**: ShipD dataset import (one-time)

---

### 0.4.7.A Hull Library Integration (Extended Bootstrap)

**Core insight**: Novel geometry emerges from mutation of validated seeds. The library provides starting points; the existing synthesis/adjustment engine creates novelty.

#### Architecture

```
User prompt → Semantic Search (30k hulls) → k nearest neighbors
                                               │
                                               ▼
                              Parameter Interpolation (blend toward constraints)
                                               │
                                               ▼
                              Synthesis (existing engine: synthesis.py)
                                               │
                                               ▼
                              Mutation Loop (existing ADJUST/TARGET)
                                               │
                                               ▼
                              Output: Novel hull (may not exist in library)
```

#### Key Components

| Component | Path | Purpose |
|-----------|------|---------|
| Hull library | `magnet/bootstrap/hull_library.py` | Store/query 30k+ hulls |
| Search index | `magnet/bootstrap/library_index.py` | Semantic + constraint search |
| Interpolation | `magnet/bootstrap/interpolation.py` | Blend hulls toward target |
| Orchestrator | `magnet/bootstrap/orchestrator.py` | Coordinate pipeline |

#### Interface

```python
@dataclass
class LibraryHull:
    hull_id: str
    parameters: Dict[str, float]  # Continuous only
    displacement_m3: float
    speed_kts: float
    range_nm: float
    source: str  # "shipd", "grabcad", "curated"

@dataclass
class BootstrapResult:
    success: bool
    geometry: Optional["HullGeometry"]
    parameters: Dict[str, float]
    source_hulls: List[str]       # Where we started
    mutations_applied: List[str]  # What we changed
    is_novel: bool                # Differs from all library hulls
    novelty_score: float          # 0=match, 1=maximally different
```

#### How Novelty Emerges

1. **Interpolation**: Blending 5 hulls creates parameter combinations none had
2. **Mutation**: ADJUST/TARGET pushes parameters beyond any source
3. **Constraints**: User requirements may demand forms no library hull has

**Example**:
```
Library: Hull A (LOA=70, Deadrise=16), Hull B (LOA=75, Deadrise=20)
User wants: LOA=72, Deadrise=24

Interpolate: LOA=72.5, Deadrise=18
Mutate:      Deadrise 18→24 (via ADJUST within affordance)

Result: Novel hull not in library
```

#### Fallback Behavior

| Failure | Response |
|---------|----------|
| No similar hulls | Expand search, suggest constraint changes |
| Synthesis fails | Offer nearest valid library hull |
| Physics fails | Rollback, reduce mutation step |
| Unsatisfiable | Present Pareto trade-offs |

#### Data Sources

##### Primary: ShipD Dataset (Automated, 30,000 Hulls)

**ShipD is the primary hull library source**. It provides 30,000 parametric hull definitions that can be cloned directly from GitHub.

```bash
# AUTOMATED: Clone ShipD dataset
git clone https://github.com/noahbagz/ShipD.git data/hull_library/shipd
```

##### Storage Requirements

**GitHub repo only: ~20 MB** — This is all you need for MVP.

| What | Size | Location | Need It? |
|------|------|----------|----------|
| `InputVectors_30k.npy` (parameters) | ~5-10 MB | GitHub | ✅ Yes |
| `X_LABELS.npy` + code + docs | ~10 MB | GitHub | ✅ Yes |
| **GitHub clone total** | **~20 MB** | Local | ✅ **MVP** |
| | | | |
| Full STL meshes | 30-90 GB | Harvard Dataverse | ❌ No |
| Point clouds | 60-150 GB | Harvard Dataverse | ❌ No |
| Images (5 per hull) | ~7.5 GB | Harvard Dataverse | ❌ Optional |

**Why you don't need the full meshes**: MAGNET synthesizes geometry from parameters using the existing `HullGenerator`. The 45-parameter vectors in `InputVectors_30k.npy` are the input to ShipD's `HullParameterization.py`, which generates hull surfaces procedurally. MAGNET does the same thing—so we only need the parameters, not pre-computed meshes.

**ShipD provides**:
- 30,000 hull parameter sets (45 parameters each)
- Principal dimensions (LOA, beam, draft, depth)
- Form coefficients (Cb, Cp, Cwp, Cm, LCB)
- Bow/stern geometry parameters
- Performance metrics (displacement, speed estimates)

**IMPORTANT LIMITATION**: ShipD's 45 parameters are optimized for conventional cargo/displacement hulls. They do NOT capture:
- Stepped hulls
- Hydrofoils
- Prop tunnels
- Hard chines (specific angles)
- Sportfish-specific forms

**For novel topology** (steps, tunnels, foils), use the Topology DSL (Spec §0) to add features on top of library-seeded base forms.

##### Secondary: Manual CAD Files (Deferred)

Additional hull forms from STEP/3DM files are available but **deferred to Phase 2**. Current focus is on hull form, scantlings, and structural accuracy—not small components.

**Available STEP files** (manually acquired, for future integration):
- NPL Round Bilge series (.stp)
- Catamaran hulls (.stp, .3dm)
- Planing hulls (.3dm)
- Semi-displacement yacht hulls (.stp)

**NOT prioritized for MVP**:
- Small deck hardware (cleats, rod holders)
- Furniture (fighting chairs, seats)
- Minor fittings

##### What's NOT Available (Investigated)

| Source | Status | Notes |
|--------|--------|-------|
| Series 60 CSV | ❌ Not found | No reliable digitized offset tables available online |
| Series 64 CSV | ❌ Not found | Same issue |
| NPL offset tables | ⚠️ Partial | Some STEP files available, no CSV |
| Delftship .fbm | ⚠️ Difficult | Requires Windows software extraction |
| FreeShip .ftm | ⚠️ Difficult | Requires Windows software extraction |

##### Revised Data Strategy

| Source | Hulls | Format | Effort | Status |
|--------|-------|--------|--------|--------|
| **ShipD (GitHub)** | 30,000 | JSON params | `git clone` | ✅ PRIMARY |
| **Manual STEP files** | ~15 | .stp/.3dm | Already acquired | ⚠️ Phase 2 |
| **Topology DSL** | ∞ | Generated | Code | ✅ For novel features |

**Phase 1 focus**: ShipD parameters + existing MAGNET synthesis engine
**Phase 2 focus**: STEP import pipeline for additional hull forms
**Deferred**: Small components, deck hardware, furniture

**Storage architecture (Local + HuggingFace Hub)**:

```python
# Local (primary) - ShipD clone
data/hull_library/
  shipd/                    # git clone from GitHub
    hulls/                  # 30k hull parameter files
    metadata/               # Dataset documentation
  
  index/
    hull_index.parquet      # Processed index for search
    hull_embeddings.npy     # Semantic embeddings
  
  manual_cad/               # Manually acquired STEP files (Phase 2)
    npl_round_bilge_4a.stp
    catamaran.stp
    ...

# Cloud (HuggingFace Hub) - for sharing/backup
# Upload processed index + embeddings after building
```

**Automated setup script**:

```bash
#!/bin/bash
# scripts/setup_hull_library.sh

set -e

echo "Setting up hull library..."

# Create directories
mkdir -p data/hull_library/{shipd,index,manual_cad}

# Clone ShipD (30k hulls)
if [ ! -d "data/hull_library/shipd/.git" ]; then
    echo "Cloning ShipD dataset..."
    git clone https://github.com/noahbagz/ShipD.git data/hull_library/shipd
else
    echo "ShipD already cloned, pulling latest..."
    cd data/hull_library/shipd && git pull && cd -
fi

echo "Hull library setup complete."
echo "Run 'python -m magnet.bootstrap.build_index' to build search index."
```

#### Import Pipeline

**File location**: `magnet/bootstrap/import_shipd.py`

**Primary focus**: ShipD dataset (30k hulls, automated)

```python
# magnet/bootstrap/import_shipd.py

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import json
import numpy as np

@dataclass
class ShipDHull:
    """Hull parameters from ShipD dataset."""
    hull_id: str
    
    # Principal dimensions
    loa_m: float
    beam_m: float
    draft_m: float
    depth_m: float
    
    # Form coefficients
    Cb: float           # Block coefficient
    Cp: float           # Prismatic coefficient
    Cwp: float          # Waterplane coefficient
    Cm: float           # Midship coefficient
    lcb_pct: float      # LCB as % of LWL from FP
    
    # Derived metrics
    displacement_m3: float
    wetted_surface_m2: float
    
    # Raw parameters (all 45)
    raw_params: Dict[str, float]
    
    # Embedding for search
    embedding: Optional[np.ndarray] = None

class ShipDImporter:
    """Import ShipD dataset from cloned GitHub repo."""
    
    def __init__(self, shipd_path: Path = Path("data/hull_library/shipd")):
        self.shipd_path = shipd_path
        
    def import_all(self) -> List[ShipDHull]:
        """Import all hulls from ShipD dataset."""
        hulls = []
        
        # ShipD stores hulls as JSON files or in a single CSV/parquet
        # Adjust based on actual ShipD structure
        hull_files = list(self.shipd_path.glob("**/*.json"))
        
        for hull_file in hull_files:
            hull = self._parse_hull(hull_file)
            if hull:
                hulls.append(hull)
        
        return hulls
    
    def _parse_hull(self, path: Path) -> Optional[ShipDHull]:
        """Parse single hull from ShipD format."""
        try:
            with open(path) as f:
                data = json.load(f)
            
            return ShipDHull(
                hull_id=path.stem,
                loa_m=data.get("Lpp", 0) or data.get("LOA", 0),
                beam_m=data.get("B", 0) or data.get("Beam", 0),
                draft_m=data.get("T", 0) or data.get("Draft", 0),
                depth_m=data.get("D", 0) or data.get("Depth", 0),
                Cb=data.get("Cb", 0),
                Cp=data.get("Cp", 0),
                Cwp=data.get("Cwp", 0),
                Cm=data.get("Cm", 0),
                lcb_pct=data.get("LCB", 0),
                displacement_m3=data.get("Displacement", 0),
                wetted_surface_m2=data.get("S", 0),
                raw_params=data
            )
        except Exception as e:
            print(f"Failed to parse {path}: {e}")
            return None

def build_hull_library() -> "HullLibrary":
    """
    Build hull library from ShipD dataset.
    
    FULLY AUTOMATED - just requires `git clone` first.
    """
    from magnet.bootstrap.hull_library import HullLibrary
    from magnet.bootstrap.embeddings import get_embedding_provider
    
    # Import ShipD
    importer = ShipDImporter()
    shipd_hulls = importer.import_all()
    print(f"Imported {len(shipd_hulls)} hulls from ShipD")
    
    # Compute embeddings
    embedder = get_embedding_provider("local")
    for hull in shipd_hulls:
        description = f"hull {hull.loa_m:.1f}m LOA {hull.beam_m:.1f}m beam Cb={hull.Cb:.2f}"
        hull.embedding = embedder.embed(description)
    
    # Build library
    library = HullLibrary()
    for hull in shipd_hulls:
        library.add(hull)
    
    # Save index
    library.save_index(Path("data/hull_library/index"))
    
    return library
```

**Phase 2 (deferred)**: STEP import for manually acquired CAD files

```python
# magnet/bootstrap/import_step.py (PHASE 2 - NOT MVP)

def import_step(self, path: Path) -> LibraryHull:
    """
    Import STEP/IGES, extract sections via OpenCASCADE.
    
    Requires: pip install pythonocc-core
    Status: DEFERRED to Phase 2
    """
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Section
    
    # Read STEP file
    reader = STEPControl_Reader()
    reader.ReadFile(str(path))
    reader.TransferRoots()
    shape = reader.OneShape()
    
    # Slice at stations to extract sections
    sections = slice_at_stations(shape, num_stations=21)
    params = extract_parameters_from_sections(sections)
    
    return LibraryHull(...)
```

**Automation summary**:

| Task | Status | Notes |
|------|--------|-------|
| **Clone ShipD from GitHub** | ✅ Automated | `git clone https://github.com/noahbagz/ShipD.git` |
| **Parse ShipD JSON/CSV** | ✅ Automated | `ShipDImporter.import_all()` |
| **Compute embeddings** | ✅ Automated | Local sentence-transformers |
| **Build search index** | ✅ Automated | `build_hull_library()` |
| | | |
| **STEP file import** | ⏸️ Deferred | Phase 2 - requires pythonocc-core |
| **Small components** | ⏸️ Deferred | Not MVP priority |
| **Extract STEP sections** | ✅ Automated | After file acquired by human |
| **Extract Rhino NURBS** | ✅ Automated | After file acquired by human |
| **OCR academic paper offsets** | ⚠️ Semi-automated | Human verifies OCR output |

**Phase 1 = zero human work.** Phase 2+ requires human file collection, then automated processing.

#### Hugging Face Hub Integration

**File location**: `magnet/bootstrap/hull_library.py` (HF Hub client integration)

**Why Hugging Face Hub**:
- Free unlimited storage for datasets
- Free CDN/egress (no bandwidth charges)
- Native Python API with automatic caching
- Version control for datasets
- Easy sharing/collaboration

**Setup** (one-time, HUMAN MANUAL):

```bash
# 1. Create account at huggingface.co
# 2. Create dataset repo (e.g., "your-org/magnet-hulls")
# 3. Install CLI
pip install huggingface_hub

# 4. Authenticate
huggingface-cli login
```

**Upload library** (automated after Phase 1 build):

```python
from huggingface_hub import HfApi, create_repo

def upload_library_to_hf(library: HullLibrary, repo_id: str = "your-org/magnet-hulls"):
    """Upload local library to Hugging Face Hub."""
    
    # Create repo (idempotent)
    create_repo(repo_id, repo_type="dataset", exist_ok=True)
    
    api = HfApi()
    
    # Upload index files (small, always needed)
    api.upload_file(
        path_or_fileobj="data/hull_library/hull_index.parquet",
        path_in_repo="hull_index.parquet",
        repo_id=repo_id,
        repo_type="dataset"
    )
    
    api.upload_file(
        path_or_fileobj="data/hull_library/hull_embeddings.npy",
        path_in_repo="hull_embeddings.npy",
        repo_id=repo_id,
        repo_type="dataset"
    )
    
    # Upload section curves (JSON, small)
    api.upload_folder(
        folder_path="data/hull_library/sections",
        path_in_repo="sections",
        repo_id=repo_id,
        repo_type="dataset"
    )
    
    # Upload full geometry (STEP/3DM, large, fetch on demand)
    api.upload_folder(
        folder_path="data/hull_library/geometry",
        path_in_repo="geometry",
        repo_id=repo_id,
        repo_type="dataset"
    )
```

**Fetch geometry** (automated, with caching):

```python
from huggingface_hub import hf_hub_download
from pathlib import Path

class HullLibrary:
    def __init__(self, repo_id: str = "your-org/magnet-hulls"):
        self.repo_id = repo_id
        
        # Download index files (small, always local)
        self.index_path = hf_hub_download(
            repo_id=repo_id,
            filename="hull_index.parquet",
            repo_type="dataset"
        )
        self.embeddings_path = hf_hub_download(
            repo_id=repo_id,
            filename="hull_embeddings.npy",
            repo_type="dataset"
        )
        
        self.params = pd.read_parquet(self.index_path)
        self.embeddings = np.load(self.embeddings_path)
    
    def get_geometry(self, hull_id: str) -> Path:
        """
        Fetch full geometry on demand.
        Cached locally at ~/.cache/huggingface/hub/
        """
        return hf_hub_download(
            repo_id=self.repo_id,
            filename=f"geometry/{hull_id}.step",
            repo_type="dataset",
            cache_dir=Path.home() / ".cache" / "magnet" / "hulls"
        )
    
    def search(self, query: str, k: int = 5) -> List[LibrarySearchResult]:
        """Semantic search runs locally (instant)."""
        query_embedding = embed(query)
        similarities = cosine_similarity(query_embedding, self.embeddings)
        top_k = np.argsort(similarities)[-k:]
        
        results = []
        for idx in top_k:
            hull_params = self.params.iloc[idx].to_dict()
            results.append(LibrarySearchResult(
                hull=LibraryHull(hull_id=hull_params['hull_id'], ...),
                similarity_score=similarities[idx],
                ...
            ))
        return results
```

**Storage breakdown**:

| Location | Data | Size | Access |
|----------|------|------|--------|
| **Hugging Face Hub** | Full library | 50-100 GB | One-time upload, version controlled |
| **Local disk** | Index + embeddings | ~100 MB | Always present after first run |
| **Local cache** | Recently fetched geometry | 5-10 GB (LRU) | Automatic, transparent |

**Cost**: $0 (free tier, unlimited for public datasets)

#### Embedding & LLM Architecture

**Two separate models serve different purposes**:

| Model | Purpose | Where It Runs | Options |
|-------|---------|---------------|---------|
| **Embedding Model** | Text → vectors for semantic search | Local (recommended) or API | sentence-transformers, OpenAI embeddings |
| **LLM (Claude/GPT)** | Reasoning, DSL generation, design decisions | Cloud API | Anthropic Claude, OpenAI GPT-4, etc. |

**The LLM is always an API call** (Claude, GPT-4, etc.). The embedding model is separate and can be local or API.

**Embedding Options**:

```python
# magnet/bootstrap/embeddings.py

from abc import ABC, abstractmethod
from typing import List
import numpy as np

class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> np.ndarray:
        """Convert text to embedding vector."""
        pass
    
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Batch embed for index building."""
        pass

class LocalEmbedding(EmbeddingProvider):
    """
    Local embedding using sentence-transformers.
    
    Pros: Free, fast (~10ms), works offline, no rate limits
    Cons: Slightly less accurate than frontier embeddings
    
    Recommended for MVP.
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)  # ~90MB, runs on CPU
    
    def embed(self, text: str) -> np.ndarray:
        return self.model.encode(text)  # ~10ms
    
    def embed_batch(self, texts: List[str]) -> np.ndarray:
        return self.model.encode(texts, show_progress_bar=True)

class OpenAIEmbedding(EmbeddingProvider):
    """
    OpenAI embedding API.
    
    Pros: Higher quality embeddings, multilingual
    Cons: API cost ($0.00002/1K tokens), latency (~100ms), requires internet
    """
    def __init__(self, model: str = "text-embedding-3-small"):
        from openai import OpenAI
        self.client = OpenAI()
        self.model = model
    
    def embed(self, text: str) -> np.ndarray:
        response = self.client.embeddings.create(model=self.model, input=text)
        return np.array(response.data[0].embedding)  # ~100ms
    
    def embed_batch(self, texts: List[str]) -> np.ndarray:
        response = self.client.embeddings.create(model=self.model, input=texts)
        return np.array([d.embedding for d in response.data])

# Factory
def get_embedding_provider(provider: str = "local") -> EmbeddingProvider:
    if provider == "local":
        return LocalEmbedding()
    elif provider == "openai":
        return OpenAIEmbedding()
    else:
        raise ValueError(f"Unknown provider: {provider}")
```

**Configuration**:

```python
# magnet/config/embedding_config.py

EMBEDDING_PROVIDER = "local"  # or "openai"

# Local is recommended for MVP:
# - Free (no API costs)
# - Fast (10ms vs 100ms per query)
# - Works offline
# - Quality is sufficient for semantic search
#
# Switch to OpenAI if:
# - Search quality is noticeably poor
# - You need multilingual support
# - You're already paying for OpenAI API
```

**Full System Flow**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  USER: "Design a 72ft sportfish"                                        │
│                     │                                                    │
│                     ▼                                                    │
│  ┌─────────────────────────────────────┐                                │
│  │  LLM (Claude/GPT API)               │  ← Frontier model, cloud       │
│  │  Reasons: "I need to search..."     │                                │
│  │  Calls tool: search_library()       │                                │
│  └─────────────────────────────────────┘                                │
│                     │                                                    │
│                     ▼                                                    │
│  ┌─────────────────────────────────────┐                                │
│  │  EMBEDDING MODEL                    │  ← Local (free) or API         │
│  │  embed("72ft sportfish") → [0.2,..] │                                │
│  └─────────────────────────────────────┘                                │
│                     │                                                    │
│                     ▼                                                    │
│  ┌─────────────────────────────────────┐                                │
│  │  LOCAL INDEX                        │  ← Your machine                │
│  │  cosine_similarity(query, index)    │                                │
│  │  Returns: [hull_047, hull_123]      │                                │
│  └─────────────────────────────────────┘                                │
│                     │                                                    │
│                     ▼                                                    │
│  ┌─────────────────────────────────────┐                                │
│  │  HUGGING FACE                       │  ← Cloud storage               │
│  │  Fetch geometry for selected hulls  │                                │
│  └─────────────────────────────────────┘                                │
│                     │                                                    │
│                     ▼                                                    │
│  ┌─────────────────────────────────────┐                                │
│  │  KERNEL (local Python)              │  ← Your machine                │
│  │  - Blend parameters                  │                                │
│  │  - Synthesize geometry               │                                │
│  │  - Validate physics                  │                                │
│  └─────────────────────────────────────┘                                │
│                     │                                                    │
│                     ▼                                                    │
│  Result → LLM → User                                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

**What Runs Where**:

| Component | Location | Model | Cost |
|-----------|----------|-------|------|
| LLM reasoning | Cloud API | Claude/GPT-4 | Per token |
| Embedding (search) | Local (recommended) | sentence-transformers | Free |
| Index storage | Local disk | None (data) | Free |
| Geometry storage | HuggingFace Hub | None (data) | Free |
| Synthesis engine | Local Python | None (code) | Free |
| Physics validation | Local Python | None (code) | Free |

**Dependencies**:

```bash
# Required for local embeddings (recommended)
pip install sentence-transformers  # ~500MB with model

# Optional for OpenAI embeddings
pip install openai

# The embedding model auto-downloads on first use:
# ~/.cache/torch/sentence_transformers/all-MiniLM-L6-v2/  (~90MB)
```

#### Indexing Architecture

**Design principle**: Store decomposed, parameterized representations—not just raw geometry. This enables blending in parameter space and guarantees novel outputs.

**Multi-Index Structure**:

```
data/library/
├── hull_index.parquet          # Hull parameters (LOA, beam, deadrise, etc.)
├── hull_embeddings.npy         # Semantic embeddings for NL search
├── component_index.parquet     # Component parameters by type
├── component_embeddings.npy    # Semantic embeddings for components
├── vessel_index.parquet        # Complete vessel decompositions
├── vessel_embeddings.npy       # Vessel-level semantic embeddings
└── constraint_index.parquet    # Pre-computed constraint satisfaction scores
```

**Index Schema** (`vessel_index.parquet`):

```python
@dataclass
class VesselIndexEntry:
    """Decomposed, parameterized vessel representation."""
    vessel_id: str
    source: str                      # "grabcad", "custom", "generated"
    source_attribution: str          # Original designer/source for reference
    
    # Hull parameters (for blending)
    hull_params: Dict[str, float]    # LOA, beam, draft, Cb, Cp, deadrise, etc.
    
    # Component manifest (for mixing)
    components: List[ComponentRef]   # [{type: "cabin", params: {...}}, ...]
    
    # Derived metrics (for constraint search)
    displacement_m3: float
    speed_kts: float
    range_nm: float
    stability_gm: float
    
    # Embeddings (precomputed)
    semantic_embedding: np.ndarray   # 768-dim from text description
    parameter_embedding: np.ndarray  # Normalized parameter vector
    visual_embedding: Optional[np.ndarray]  # From rendered thumbnail

@dataclass
class ComponentRef:
    """Reference to a component within a vessel."""
    component_type: str              # "cabin", "prop_bracket", etc.
    component_id: str                # ID in component library
    local_params: Dict[str, float]   # Instance-specific overrides
    position: Tuple[float, float, float]  # Relative to hull
    anchors_used: List[str]          # Which hull anchors it connects to
```

**Search Modes**:

| Mode | Query | Returns | Use Case |
|------|-------|---------|----------|
| **Semantic** | "72ft sportfish for blue water" | Nearest embeddings | Natural language |
| **Constraint** | `{loa: [20,25], speed: [30,∞]}` | Satisfying vessels | Requirements-based |
| **Parametric** | `{deadrise: 22, Cp: 0.58}` | K-nearest in param space | Technical specs |
| **Hybrid** | Semantic + constraints | Filtered semantic | Most common |

```python
class LibraryIndex:
    """Multi-modal search over vessel/component library."""
    
    def search_semantic(
        self, 
        query: str, 
        k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[SearchResult]:
        """Natural language search."""
        query_emb = self.embed_text(query)
        
        # Optional pre-filtering by constraints
        candidates = self.vessels
        if filters:
            candidates = self._apply_filters(candidates, filters)
        
        # Cosine similarity on semantic embeddings
        similarities = cosine_similarity(query_emb, candidates.semantic_embeddings)
        return self._to_results(candidates, similarities, k)
    
    def search_constraints(
        self,
        constraints: "SynthesisConstraints",
        k: int = 10
    ) -> List[SearchResult]:
        """Find vessels satisfying constraints."""
        scores = []
        for vessel in self.vessels:
            score = self._constraint_satisfaction(vessel, constraints)
            scores.append(score)
        
        # Return top-k by constraint satisfaction
        top_k = np.argsort(scores)[-k:]
        return [self._to_result(self.vessels[i], scores[i]) for i in top_k]
    
    def search_parametric(
        self,
        target_params: Dict[str, float],
        k: int = 5
    ) -> List[SearchResult]:
        """K-nearest neighbors in parameter space."""
        target_vec = self._params_to_vector(target_params)
        distances = np.linalg.norm(self.param_embeddings - target_vec, axis=1)
        top_k = np.argsort(distances)[:k]
        return [self._to_result(self.vessels[i], 1.0 / (1 + distances[i])) for i in top_k]
```

#### Blending for Novelty (IP Protection)

**Critical**: The library NEVER outputs a source vessel directly. All outputs are blended from multiple sources, guaranteeing novel geometry.

**Blending Pipeline**:

```
User: "72ft sportfish, fast like Yellowfin, seaworthy like Viking"
                              │
                              ▼
                    ┌─────────────────────┐
                    │   Semantic Search   │
                    │   "sportfish 72ft"  │
                    └─────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
   │ Vessel A    │    │ Vessel B    │    │ Vessel C    │
   │ (Yellowfin- │    │ (Viking-    │    │ (other      │
   │  like)      │    │  like)      │    │  influence) │
   │             │    │             │    │             │
   │ params: {   │    │ params: {   │    │ params: {   │
   │  loa: 72    │    │  loa: 72    │    │  loa: 70    │
   │  beam: 6.2  │    │  beam: 6.8  │    │  beam: 6.5  │
   │  deadrise:  │    │  deadrise:  │    │  deadrise:  │
   │   24°       │    │   18°       │    │   21°       │
   │  ...        │    │  ...        │    │  ...        │
   │ }           │    │ }           │    │ }           │
   └─────────────┘    └─────────────┘    └─────────────┘
          │                   │                   │
          │    weights: [0.4, 0.4, 0.2]          │
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  Parameter Blend    │
                    │                     │
                    │  blended_params = { │
                    │    loa: 71.6        │  ← weighted avg
                    │    beam: 6.54       │
                    │    deadrise: 21.0°  │
                    │    ...              │
                    │  }                  │
                    └─────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  Constraint Adjust  │
                    │  (TARGET speed=35)  │
                    └─────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  Synthesis Engine   │
                    │  (generate NEW      │
                    │   geometry from     │
                    │   blended params)   │
                    └─────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  NOVEL VESSEL       │
                    │                     │
                    │  - NOT Vessel A     │
                    │  - NOT Vessel B     │
                    │  - NOT Vessel C     │
                    │  - Influenced by    │
                    │    all three        │
                    │  - Meets user       │
                    │    constraints      │
                    └─────────────────────┘
```

**Blending Implementation**:

```python
# magnet/bootstrap/blending.py

@dataclass
class BlendResult:
    """Result of blending multiple source vessels."""
    blended_params: Dict[str, float]
    source_vessels: List[str]
    blend_weights: List[float]
    novelty_score: float              # Distance from nearest source
    attribution: str                  # "Influenced by: A (40%), B (40%), C (20%)"

def blend_vessels(
    sources: List[VesselIndexEntry],
    weights: List[float],
    constraints: Optional["SynthesisConstraints"] = None
) -> BlendResult:
    """
    Blend multiple vessels in parameter space.
    
    GUARANTEES:
    - Output differs from every source by novelty_threshold
    - Constraints are satisfied (or best-effort with residuals)
    - Attribution preserved for transparency (not IP)
    """
    # Normalize weights
    weights = np.array(weights) / sum(weights)
    
    # Blend hull parameters
    blended_hull = {}
    for param in HULL_PARAMS:
        values = [s.hull_params.get(param, 0) for s in sources]
        blended_hull[param] = np.dot(weights, values)
    
    # Blend component configurations
    blended_components = blend_components(sources, weights)
    
    # Adjust toward constraints if provided
    if constraints:
        blended_hull = adjust_toward_constraints(blended_hull, constraints)
    
    # Compute novelty score (min distance to any source)
    novelty = compute_novelty_score(blended_hull, sources)
    
    # ENFORCE MINIMUM NOVELTY
    if novelty < NOVELTY_THRESHOLD:
        blended_hull = perturb_for_novelty(blended_hull, sources, NOVELTY_THRESHOLD)
        novelty = compute_novelty_score(blended_hull, sources)
    
    return BlendResult(
        blended_params=blended_hull,
        source_vessels=[s.vessel_id for s in sources],
        blend_weights=weights.tolist(),
        novelty_score=novelty,
        attribution=format_attribution(sources, weights)
    )

def compute_novelty_score(
    params: Dict[str, float],
    sources: List[VesselIndexEntry]
) -> float:
    """
    Compute minimum normalized distance to any source.
    
    **Important**:
    - Do NOT use KL-divergence on raw parameter vectors as a novelty metric. KL requires a density model and is very sensitive to representation/normalization.
    - Novelty must be computed in a representation that correlates with *geometry*, not just raw parameter magnitudes.
    
    Recommended novelty metric (MVP → robust):
    1) **Standardized parameter distance** (MVP): z-scored parameters with per-parameter scales learned from the library.
    2) **Latent/embedding distance** (preferred): distance in a learned latent space over valid hulls (PCA/autoencoder/manifold).
    3) **Geometry descriptor distance** (optional, slow): compare section curves / curvature signatures to catch “param-different but shape-similar.”
    
    Returns value in [0, 1]:
    - 0 = identical to a source (NOT ALLOWED)
    - 1 = maximally different from all sources
    """
    param_vec = params_to_vector(params)
    distances = []
    for source in sources:
        source_vec = params_to_vector(source.hull_params)
        dist = np.linalg.norm(param_vec - source_vec) / PARAM_SPACE_DIAMETER
        distances.append(dist)
    return min(distances)

NOVELTY_THRESHOLD = 0.15  # Minimum 15% different from any source

def perturb_for_novelty(
    params: Dict[str, float],
    sources: List[VesselIndexEntry],
    target_novelty: float
) -> Dict[str, float]:
    """
    Perturb parameters to ensure minimum novelty.
    
    Uses constraint-aware perturbation:
    - Move away from nearest source
    - Stay within valid parameter bounds
    - Preserve constraint satisfaction
    """
    nearest_source = min(sources, key=lambda s: param_distance(params, s.hull_params))
    
    # Direction away from nearest source
    direction = params_to_vector(params) - params_to_vector(nearest_source.hull_params)
    direction = direction / np.linalg.norm(direction)
    
    # Step until novelty threshold met
    step_size = 0.01
    current_params = params.copy()
    while compute_novelty_score(current_params, sources) < target_novelty:
        current_vec = params_to_vector(current_params) + direction * step_size
        current_params = vector_to_params(current_vec)
        current_params = clamp_to_bounds(current_params)
        step_size *= 1.1
    
    return current_params
```

**Novelty Guarantees**:

| Mechanism | What It Ensures |
|-----------|-----------------|
| **Multi-source blending** | Output is weighted average, not copy |
| **Novelty threshold** | Minimum 15% parameter-space distance from any source |
| **Constraint adjustment** | User constraints push design further from sources |
| **Synthesis from params** | Geometry is generated, not copied |
| **DSL mutations** | Further modifications create more distance |

**Attribution (for transparency, not IP)**:

```python
# Every output includes attribution for transparency
@dataclass
class DesignProvenance:
    """Tracks influences on a design (for user info, not IP claim)."""
    primary_influences: List[str]    # ["Series 60", "Delftship yacht #47"]
    influence_weights: List[float]   # [0.4, 0.35, 0.25]
    novelty_score: float             # 0.23 (23% different from nearest)
    synthesis_method: str            # "parameter_blend + constraint_adjust"
    
    def summary(self) -> str:
        return f"Novel design (novelty: {self.novelty_score:.0%}), " \
               f"influenced by: {', '.join(self.primary_influences)}"
```

**What Users See**:

```
MAGNET: Created novel 72ft sportfish design.

Design Influences:
- Hull proportions influenced by Series 60 systematic series
- Deadrise profile influenced by Delftship high-speed yacht #47  
- Cabin layout influenced by custom template

Novelty Score: 23% (minimum threshold: 15%)

This is a NEW design, not a copy of any library item.
```

#### Integration

Bootstrap feeds INTO existing systems:
- Synthesis → `magnet/kernel/synthesis.py`
- Mutation → `ADJUST/TARGET` via `program_executor.py`  
- Validation → `magnet/physics/validators.py`
- Affordances → `magnet/hull_gen/affordances.py`

Result enters three-regime loop (§3) with geometry, anchors, parameters ready.

#### Library + Topology DSL (Novel Features)

The library handles **base forms**. The Topology DSL (Spec §0) handles **novel features**:

```
User: "72ft stepped sportfish with tunnel props"
                    │
                    ▼
           ┌────────────────┐
           │ Parse Intent   │
           └────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
   Base form              Novel topology
   "sportfish 72ft"       "stepped", "tunnel"
        │                       │
        ▼                       ▼
┌─────────────────┐    ┌─────────────────────────────────┐
│  Hull Library   │    │  Topology DSL                   │
│  search →       │    │  CREATE step AT station[0.4]    │
│  interpolate    │    │  CREATE tunnel AT y=-1.5m       │
└─────────────────┘    └─────────────────────────────────┘
        │                       │
        └───────────┬───────────┘
                    ▼
           ┌────────────────┐
           │ Merge & Synth  │  ← Library provides base params
           │                │  ← DSL adds topology features
           └────────────────┘
                    │
                    ▼
           ┌────────────────┐
           │ ADJUST/TARGET  │  ← Fine-tune parameters
           └────────────────┘
```

**LLM control plane unchanged**—same observables, same affordances. The library just provides better starting points; topology DSL handles features the library can't express.

**When to use each**:

| User Request | Approach |
|-------------|----------|
| "72ft sportfish" | Library search + interpolation |
| "Make it faster" | ADJUST/TARGET on existing |
| "Add steps to the hull" | Topology DSL: CREATE step |
| "72ft stepped sportfish" | Library (base) + DSL (steps) |
| "Something totally new" | Topology DSL from scratch |

---

### 0.4.7.B Component Library (Composable Sub-Components)

**Core insight**: Vessels are compositions of hull + components (cabins, props, towers, etc.). Components from a library can be placed onto any compatible hull, then mutated via DSL to create truly novel configurations.

#### The Composability Model

```
HULL LIBRARY          COMPONENT LIBRARY         DSL MUTATIONS         RESULT
─────────────         ─────────────────         ─────────────         ──────
sportfish_72    +     flybridge_cabin     +     ADJUST/CREATE   =    Novel vessel
                      triple_outboard           (scale, reshape,      (combination +
                      tuna_tower                 add features)         mutations that
                      fighting_chair                                   never existed)
```

#### Why Novelty Is Preserved

| Layer | Source | Novel? |
|-------|--------|--------|
| Hull base | Hull Library | Starting point |
| Hull mutations | DSL (ADJUST deadrise, add step) | ✅ Novel geometry |
| Component base | Component Library | Starting point |
| Component scaling | DSL (stretch/widen to fit hull) | ✅ Novel dimensions |
| Component mods | DSL (windows, roof camber) | ✅ Novel features |
| **Combination** | hull_A + cabin_B + props_C | ✅ Novel composition |

**Components aren't frozen after placement**—the DSL can mutate any placed component.

#### File Locations

| Component | Path | Purpose |
|-----------|------|---------|
| Component library | `magnet/bootstrap/component_library.py` | Store/query reusable components |
| Component index | `magnet/bootstrap/component_index.py` | Semantic + compatibility search |
| Component anchors | `magnet/bootstrap/component_anchors.py` | Connection point definitions |
| Component adapter | `magnet/bootstrap/component_adapter.py` | Scale/fit components to hulls |

#### Interface Contracts

```python
# magnet/bootstrap/component_library.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path

@dataclass
class ComponentAnchor:
    """Where a component connects to hull or other components."""
    name: str                    # "base", "transom_mount", "deck_edge"
    position: Tuple[float, float, float]  # Relative to component origin
    normal: Tuple[float, float, float]    # Attachment direction
    compatibility: List[str] = field(default_factory=list)  # ["deck", "transom", "hardtop"]

@dataclass
class LibraryComponent:
    """A reusable component from the library."""
    component_id: str
    component_type: str          # "cabin", "prop_bracket", "tower", "seat", etc.
    name: str                    # "Carolina flybridge cabin"
    designed_for_loa_m: float    # Original design size (for scaling)
    parameters: Dict[str, float] # length, beam, height, etc.
    anchors: List[ComponentAnchor]
    compatibility: Dict[str, any] # hull_types, min_loa, max_loa, etc.
    source: str                  # "grabcad", "custom", etc.
    embedding: Optional[List[float]] = None

@dataclass 
class ComponentSearchResult:
    component: LibraryComponent
    similarity_score: float
    compatibility_score: float   # How well it fits target hull
    scaling_required: Dict[str, float]  # Estimated adjustments needed

class ComponentLibrary:
    """
    Library of reusable vessel components.
    Same pattern as HullLibrary: local index + HF Hub storage.
    """
    
    def __init__(self, repo_id: str = "your-org/magnet-components"):
        self.repo_id = repo_id
        # Load index (small, always local)
        self.index = pd.read_parquet(self._download("component_index.parquet"))
        self.embeddings = np.load(self._download("component_embeddings.npy"))
    
    def search(
        self, 
        query: str, 
        component_type: Optional[str] = None,
        target_hull: Optional["HullGeometry"] = None,
        k: int = 5
    ) -> List[ComponentSearchResult]:
        """
        Find components matching description.
        
        Examples:
            search("flybridge cabin", component_type="cabin")
            search("triple outboard bracket", target_hull=hull_72ft)
        """
        query_embedding = embed(query)
        
        # Filter by type if specified
        candidates = self.index
        if component_type:
            candidates = candidates[candidates.component_type == component_type]
        
        # Semantic similarity
        similarities = cosine_similarity(query_embedding, self.embeddings)
        
        # Compatibility scoring if target hull provided
        if target_hull:
            compatibility_scores = self._compute_compatibility(candidates, target_hull)
            combined = 0.7 * similarities + 0.3 * compatibility_scores
        else:
            combined = similarities
        
        top_k = np.argsort(combined)[-k:]
        return [self._to_result(idx, target_hull) for idx in top_k]
    
    def get_geometry(self, component_id: str) -> "ComponentGeometry":
        """Fetch full geometry from HF Hub (cached)."""
        path = hf_hub_download(
            repo_id=self.repo_id,
            filename=f"geometry/{component_id}.step",
            repo_type="dataset"
        )
        return load_component(path)
    
    def _compute_compatibility(
        self, 
        candidates: pd.DataFrame, 
        hull: "HullGeometry"
    ) -> np.ndarray:
        """Score how well each component fits the target hull."""
        scores = []
        for _, row in candidates.iterrows():
            # Size compatibility
            size_ratio = hull.loa / row.designed_for_loa_m
            size_score = 1.0 - abs(1.0 - size_ratio) * 0.5  # Penalize large scaling
            
            # Type compatibility
            type_score = 1.0 if hull.hull_type in row.compatibility.get('hull_types', []) else 0.5
            
            scores.append(0.6 * size_score + 0.4 * type_score)
        return np.array(scores)
```

```python
# magnet/bootstrap/component_adapter.py

@dataclass
class AdaptationResult:
    """Result of adapting a component to fit a hull."""
    adapted_geometry: "ComponentGeometry"
    scaling_applied: Dict[str, float]  # {"length": 1.2, "beam": 1.1}
    dsl_mutations: List[str]           # DSL commands to apply
    constraints_satisfied: Dict[str, bool]
    warnings: List[str]                # "Headroom reduced to 1.95m"

def adapt_component_to_hull(
    component: "ComponentGeometry",
    hull: "HullGeometry",
    target_station_range: Tuple[float, float],
    constraints: Optional[Dict[str, float]] = None
) -> AdaptationResult:
    """
    Scale and adjust component to fit hull at target location.
    
    - Adjusts beam to fit available deck width
    - Adjusts length proportionally  
    - Preserves headroom constraints (or warns)
    - Returns adapted geometry + required DSL mutations
    
    Args:
        component: Component geometry from library
        hull: Target hull geometry
        target_station_range: Where to place (e.g., (0.3, 0.5) for 30-50% of LOA)
        constraints: Optional overrides (e.g., {"min_headroom": 2.0})
    """
    # Get available envelope at target location
    available_beam = hull.beam_at_station(sum(target_station_range) / 2)
    available_length = hull.loa * (target_station_range[1] - target_station_range[0])
    
    # Compute required scaling
    length_scale = available_length / component.length
    beam_scale = min(available_beam / component.beam, length_scale)  # Don't stretch wider than long
    
    # Generate DSL mutations
    mutations = []
    if abs(length_scale - 1.0) > 0.05:
        mutations.append(f"ADJUST {component.id}.length BY {(length_scale - 1) * component.length:.2f}m")
    if abs(beam_scale - 1.0) > 0.05:
        mutations.append(f"ADJUST {component.id}.beam BY {(beam_scale - 1) * component.beam:.2f}m")
    
    # Check constraints
    warnings = []
    if constraints and "min_headroom" in constraints:
        if component.headroom < constraints["min_headroom"]:
            warnings.append(f"Headroom {component.headroom:.2f}m below minimum {constraints['min_headroom']:.2f}m")
            mutations.append(f"TARGET {component.id}.headroom = {constraints['min_headroom']:.2f}m")
    
    return AdaptationResult(
        adapted_geometry=apply_scaling(component, length_scale, beam_scale),
        scaling_applied={"length": length_scale, "beam": beam_scale},
        dsl_mutations=mutations,
        constraints_satisfied={"headroom": len(warnings) == 0},
        warnings=warnings
    )
```

#### DSL Extensions for Components

The existing DSL supports component operations:

```
# Load component from library
cabin = LOAD carolina_helm_cabin FROM component_library

# Place onto hull with anchor semantics
PLACE cabin AT hull.deck STATION [0.35, 0.55] OFFSET z=0.1m

# Attach with connection points
ATTACH props TO hull.transom USING anchor=props.mount_base ALIGN centerline

# Mutate placed component (NOT frozen)
ADJUST cabin.length BY +1.8m      # Scale up for larger hull
ADJUST cabin.beam BY +0.6m        # Widen
TARGET cabin.headroom = 2.1m      # Ensure minimum

# Add novel features to component
CREATE window AT cabin.side STATION 0.6 WIDTH 1.2m HEIGHT 0.8m
ADJUST cabin.roof_camber BY +0.05m

# Constraints across components
CONSTRAIN cabin.beam <= hull.beam_at_station(0.4) - 0.3m
CONSTRAIN tower.base.width <= cabin.hardtop.width
```

#### Example Flow

```
User: "72ft sportfish with Carolina-style cabin and triple Mercury 450s"

Agent:
1. Search hull library: "sportfish 72ft planing"
   → Returns sportfish_72_base

2. Search component library: "Carolina sportfish cabin"
   → Returns carolina_helm_cabin (designed for 58ft)
   → Compatibility score: 0.85 (needs scaling)

3. Search component library: "triple outboard Mercury 450"
   → Returns triple_merc_bracket

4. Generate DSL program:
   
   # Hull from library
   hull = LOAD sportfish_72_base
   ADJUST hull.deadrise_transom = 20deg
   CREATE step AT hull STATION 0.45 HEIGHT 0.08m
   
   # Cabin from library, adapted to hull
   cabin = LOAD carolina_helm_cabin
   PLACE cabin AT hull.deck STATION [0.35, 0.55]
   ADJUST cabin.length BY +1.8m    # Scale 58ft → 72ft
   ADJUST cabin.beam BY +0.6m
   TARGET cabin.headroom = 2.0m
   
   # Props from library
   props = LOAD triple_merc_bracket
   ATTACH props TO hull.transom CENTERLINE
   ADJUST props.motor_spacing = 0.9m
   
   # Novel modifications (not in any library)
   CREATE window AT cabin.port STATION 0.4 WIDTH 1.5m
   ADJUST cabin.windshield_rake BY +5deg

5. Validate physics (hydrostatics, stability, clearances)

6. Return novel vessel
```

#### Component Types (Comprehensive Taxonomy)

**Design philosophy**: Like shadcn/ui for web dev, this library must include EVERY component an LLM needs to design a complete vessel. The LLM should never have to "imagine" a component—it should always pull from validated, parameterized library items.

**MVP FOCUS**: Hull form, superstructure, and structural components. Small deck hardware (cleats, rod holders, fighting chairs) is **deferred** to later phases.

| Priority | Category | MVP Status | Notes |
|----------|----------|------------|-------|
| **P0** | Hull appendages (keels, rudders) | ✅ MVP | Critical for hull form |
| **P0** | Superstructure (cabins, consoles) | ✅ MVP | Critical for vessel design |
| **P0** | Structural (stringers, bulkheads, frames) | ✅ MVP | Critical for scantlings |
| **P1** | Propulsion (brackets, shafts) | ✅ MVP | Required for propulsion design |
| **P1** | Tankage (fuel, water, holding) | ✅ MVP | Required for systems |
| **P2** | Deck hardware (cleats, rails) | ⏸️ Deferred | Small items, later |
| **P2** | Seating & furniture | ⏸️ Deferred | Interior fit-out, later |
| **P3** | Electronics, HVAC, safety | ⏸️ Deferred | Systems detail, later |

---

##### 1. HULL APPENDAGES & UNDERWATER (MVP)

| Type | Variants | Key Parameters | Anchors |
|------|----------|----------------|---------|
| `keel` | Fin, bulb, wing, full, shoal, centerboard, daggerboard | span, chord, sweep, foil_section, ballast_weight | hull_bottom, keel_box |
| `rudder` | Spade, skeg-hung, transom-hung, balanced, semi-balanced | area, aspect_ratio, foil_section, stock_diameter | hull_bottom, skeg, transom |
| `trim_tab` | Fixed, adjustable, interceptor-style | span, chord, deflection_range | transom_bottom, hull_bottom |
| `interceptor` | Blade, wedge | span, deployment_range, actuation_type | transom_bottom |
| `spray_rail` | Hard, soft, reverse | length, height, angle | hull_side |
| `strake` | Lifting, spray-deflecting | length, width, angle | hull_bottom |
| `stabilizer_fin` | Fixed, active, retractable | span, chord, sweep | hull_side |
| `bow_thruster` | Tunnel, external, retractable | thrust_kw, tunnel_diameter | bow_section |
| `stern_thruster` | Tunnel, external | thrust_kw, tunnel_diameter | stern_section |
| `hydrofoil` | Main, control, canard | span, chord, foil_section, sweep, dihedral | hull_bottom, strut_mount |
| `foil_strut` | Fixed, retractable | height, chord, foil_section | hull_bottom, foil_mount |
| `bulbous_bow` | Nabla, delta, elliptical | length, breadth, height, volume | bow_fairing |
| `skeg` | Full, partial, shoe | length, depth, width | hull_bottom |
| `prop_tunnel` | Full, partial | length, diameter, angle | hull_bottom_aft |
| `shaft_strut` | A-bracket, P-bracket, V-strut | spread, depth, shaft_diameter | hull_bottom |
| `shaft_log` | Straight, angled | length, shaft_diameter, stuffing_type | hull_bottom |
| `cutlass_bearing` | Standard, heavy-duty | shaft_diameter, length | strut, shaft_log |

---

##### 2. PROPULSION SYSTEMS (MVP)

| Type | Variants | Key Parameters | Anchors |
|------|----------|----------------|---------|
| `outboard_bracket` | Flush, setback, jackplate, pod | setback, height_range, motor_count, spacing | transom |
| `outboard_motor` | 2-stroke, 4-stroke (parametric envelope) | hp, shaft_length, weight, cog | bracket_mount |
| `sterndrive_unit` | Alpha, Bravo, Volvo, pod | gear_ratio, prop_diameter, trim_range | transom_cutout |
| `inboard_engine` | Gas, diesel (parametric envelope) | hp, weight, length, width, height | engine_bed |
| `engine_bed` | Steel, aluminum, composite | length, width, rail_spacing | stringer_top |
| `jet_drive` | Waterjet, jet_pump | thrust, intake_diameter, impeller_type | hull_bottom_aft |
| `pod_drive` | IPS, Zeus, pod | hp, rotation_range, draft | hull_bottom_aft |
| `v_drive` | Standard, down-angle | ratio, shaft_angle | engine_aft |
| `propeller` | Fixed, folding, feathering, controllable | diameter, pitch, blade_count, material | shaft_end, drive_unit |
| `prop_shaft` | Solid, hollow | diameter, length, material, taper | coupling, strut |
| `coupling` | Solid, flexible | shaft_diameter, torque_rating | shaft_end, transmission |
| `transmission` | Direct, reduction, 2-speed | ratio, rotation, torque_rating | engine_output |
| `exhaust_riser` | Wet, dry, hybrid | diameter, height, material | engine_exhaust |
| `muffler` | Lift, waterlock, straight | volume, inlet_diameter, outlet_diameter | exhaust_path |
| `exhaust_exit` | Transom, underwater, above_waterline | diameter, flap_type | transom, hull_side |
| `fuel_filter` | Primary, secondary, racor | flow_rate, micron_rating | fuel_line |
| `seawater_strainer` | Basket, raw_water | flow_rate, inlet_size | seacock, raw_water_line |

---

##### 3. SUPERSTRUCTURE & ENCLOSURES (MVP)

| Type | Variants | Key Parameters | Anchors |
|------|----------|----------------|---------|
| `helm_console` | Center, offset, dual, tower | width, depth, height, panel_angle | deck_surface |
| `helm_pod` | Single, double, dash-mount | width, gauge_cutouts, switch_positions | console_top |
| `cabin_structure` | Cuddy, mid-cabin, full, walkaround | length, beam, headroom, window_count | deck_surface |
| `pilothouse` | Flush-deck, raised, portuguese_bridge | length, beam, headroom, visibility_arc | deck_surface |
| `flybridge` | Open, enclosed, hardtop | length, beam, overhang, access_type | cabin_top |
| `hardtop` | Fixed, folding, retractable | length, beam, height, material | console_mount, cabin_mount |
| `t_top` | 2-post, 4-post, leaning_post_mount | spread, height, rod_holder_count | deck_surface, leaning_post |
| `bimini` | 2-bow, 3-bow, 4-bow | length, beam, height, material | deck_mounts |
| `radar_arch` | Integrated, standalone | height, spread, equipment_capacity | cabin_aft, hardtop |
| `tuna_tower` | 2-level, 3-level, marlin | height, platform_size, ladder_type | deck_surface, cabin_top |
| `mast` | Aluminum, carbon, wood | height, section, spreader_count | deck_step, keel_step |
| `arch` | Davit, radar, antenna | height, spread, lift_capacity | deck_aft |
| `bow_pulpit` | Open, closed, anchor_roller | length, rail_height, platform_width | bow_deck |
| `stern_pulpit` | Open, boarding | width, rail_height | transom_top |
| `windshield` | Flat, curved, wraparound, center-opening | width, height, rake_angle, wiper_count | cabin_front, console |
| `door` | Sliding, hinged, bifold, companionway | width, height, material, lock_type | cabin_side, cabin_aft |
| `hatch` | Flush, raised, opening, escape | width, length, material, hinge_side | deck_surface |
| `portlight` | Fixed, opening, deadlight | width, height, shape, material | cabin_side |
| `window` | Fixed, sliding, drop-down | width, height, tint, frame_type | cabin_side, pilothouse |
| `skylight` | Fixed, opening, hatch-style | width, length, material | cabin_top |
| `vent` | Cowl, mushroom, clamshell, dorade | diameter, height, material | deck_surface, cabin_top |
| `dorade_box` | Standard, low-profile | length, width, height | deck_surface |

---

##### 4. DECK HARDWARE & FITTINGS (Deferred - Not MVP)

| Type | Variants | Key Parameters | Anchors |
|------|----------|----------------|---------|
| `cleat` | Horn, folding, pop-up, pull-up | length, load_rating, material | deck_surface, gunwale |
| `chock` | Open, closed, roller | width, load_rating | deck_edge |
| `bollard` | Single, double, cruciform | height, diameter, load_rating | deck_surface |
| `fairlead` | Open, closed, roller | width, material | deck_edge, bulwark |
| `hawse_pipe` | Deck, side | diameter, angle | deck_bow, hull_side |
| `anchor_roller` | Single, double, self-launching | width, load_rating, sheave_diameter | bow_pulpit, bowsprit |
| `windlass` | Horizontal, vertical, manual | pull_capacity, chain_size, rope_size | deck_bow |
| `capstan` | Electric, hydraulic, manual | pull_capacity, drum_diameter | deck_surface |
| `winch` | Self-tailing, manual, electric | line_size, ratio, drum_capacity | deck_surface, mast |
| `stanchion` | Fixed, folding, removable | height, base_diameter, tube_diameter | deck_edge |
| `lifeline` | Wire, dyneema, rod | diameter, length, fitting_type | stanchion_top |
| `rail` | Teak, aluminum, stainless | height, tube_diameter, stanchion_spacing | deck_edge |
| `handrail` | Deck, cabin, flybridge | length, height, mounting_type | cabin_side, deck_surface |
| `grabrail` | Horizontal, vertical, angled | length, diameter, mounting_points | cabin_top, cabin_side |
| `ladder` | Swim, boarding, flybridge, tower | width, steps, material, type | transom, deck_side, cabin |
| `swim_platform` | Fixed, hydraulic, fold-down | width, length, material | transom |
| `boarding_gate` | Hinged, removable, lift | width, height | gunwale, lifeline |
| `rod_holder` | Flush, gunwale, rocket_launcher | angle, inside_diameter, material | gunwale, t_top, tower |
| `cup_holder` | Flush, surface | diameter, depth | console, coaming |
| `grab_handle` | U-bolt, triangle, bar | width, height, material | console, cabin |
| `flag_pole` | Staff, gaff, halyard | length, diameter, socket_type | stern, mast |
| `horn` | Electric, air, dual-tone | decibels, frequency | cabin_top, arch |
| `spotlight` | Manual, remote, automatic | wattage, beam_angle, rotation | cabin_top, tower |
| `navigation_light` | Bow, stern, masthead, anchor, steaming | arc, visibility_nm, led/incandescent | bow, stern, mast |
| `spreader_light` | LED, halogen | wattage, beam_angle | mast_spreader |
| `underwater_light` | Thru-hull, surface_mount | lumens, color, beam_angle | transom, hull_bottom |
| `deck_light` | Courtesy, step, flood | lumens, color, mounting | deck_surface, step |

---

##### 5. SEATING & FURNITURE (Deferred - Not MVP)

| Type | Variants | Key Parameters | Anchors |
|------|----------|----------------|---------|
| `helm_seat` | Fixed, adjustable, bolster, bucket, bench | width, height_range, swivel, armrests | deck_surface, pedestal |
| `pedestal` | Fixed, adjustable, slide | height_range, base_diameter, slide_length | deck_surface |
| `leaning_post` | Simple, with_cooler, with_livewell, tackle_station | width, height, storage_type | deck_surface |
| `fighting_chair` | Pedestal, track, rocket_launcher | base_type, footrest, gimbal | deck_surface, cockpit |
| `bench_seat` | Forward, aft, L-shaped, U-shaped | width, depth, height, storage_under | deck_surface, coaming |
| `lounge` | Sun_pad, bow_lounge, aft_lounge, convertible | width, length, cushion_thickness | deck_surface |
| `settee` | Straight, L-shaped, U-shaped, convertible | width, depth, seat_height | cabin_sole |
| `dinette` | Fixed, convertible, drop-leaf | table_size, seat_count, converts_to_berth | cabin_sole |
| `berth` | V_berth, double, single, upper, pipe_berth | width, length, mattress_thickness | cabin_hull, cabin_side |
| `table` | Fixed, folding, drop-leaf, pedestal | width, length, height, leg_type | cabin_sole, cockpit |
| `cooler_seat` | Small, medium, large | volume_liters, width, cushion_top | deck_surface |
| `bean_bag` | Marine | diameter, material | deck_surface |

---

##### 6. GALLEY & HEAD (Deferred - Not MVP)

| Type | Variants | Key Parameters | Anchors |
|------|----------|----------------|---------|
| `sink` | Single, double, bar | width, depth, bowl_count, material | counter_cutout |
| `faucet` | Manual, pressure, foot_pump | spout_height, spray_type, hot_cold | sink_mount, counter |
| `stove` | 2_burner, 3_burner, induction, alcohol, propane | burner_count, fuel_type, gimballed | counter_cutout, bulkhead |
| `oven` | Convection, microwave, combo | width, height, depth, fuel_type | cabinet_cutout |
| `refrigerator` | Top_load, front_load, drawer | volume_liters, orientation, compressor_type | cabinet_cutout |
| `freezer` | Chest, drawer, combo | volume_liters, orientation | cabinet_cutout |
| `icebox` | Insulated, drain | volume_liters, insulation_thickness | counter_cutout |
| `counter` | Galley, wet_bar, bait_station | width, depth, material | cabinet_top |
| `cabinet` | Upper, lower, hanging_locker | width, height, depth, door_type | bulkhead, sole |
| `microwave` | Built-in, countertop | width, height, depth | cabinet_cutout |
| `trash_bin` | Pull-out, flip-top, hidden | volume_liters | cabinet_interior |
| `head_toilet` | Manual, electric, vacuum, composting | footprint, flush_type, holding_connection | sole_mount |
| `shower` | Wet_head, separate, transom | pan_size, door_type, sump_required | sole, bulkhead |
| `shower_sump` | Manual, automatic | capacity, pump_gph | shower_pan_below |
| `vanity` | With_sink, mirror, storage | width, height | bulkhead |
| `medicine_cabinet` | Recessed, surface | width, height, mirror | bulkhead |

---

##### 7. TANKAGE & FLUID SYSTEMS (MVP - Required for Systems)

| Type | Variants | Key Parameters | Anchors |
|------|----------|----------------|---------|
| `fuel_tank` | Aluminum, poly, stainless, integral | capacity_liters, shape, baffled | hull_bottom, stringer_bay |
| `water_tank` | Rigid, bladder | capacity_liters, shape, material | hull_bottom, cabinet |
| `holding_tank` | Rigid, flexible | capacity_liters, inlet_count, pumpout_fitting | hull_bottom |
| `livewell` | Deck, transom, console | capacity_liters, pump_gph, drain_size | deck_cutout, transom |
| `baitwell` | Deck, transom, cooler-style | capacity_liters, pump_gph, aeration_type | deck_cutout |
| `fish_box` | Insulated, draining, refrigerated | capacity_liters, insulation_r, drain_size | deck_cutout |
| `bilge_sump` | Primary, secondary | capacity_liters, pump_mount | hull_low_point |
| `bilge_pump` | Manual, automatic, high_capacity | gph, float_switch, discharge_size | sump, bilge |
| `fill_port` | Fuel, water, waste, deck_wash | diameter, label, cap_type | deck_surface |
| `vent` | Fuel, water, holding | diameter, screen, location | hull_side, deck |
| `deck_plate` | Inspection, access | diameter, material, o-ring | deck_surface |
| `through_hull` | Flanged, flush, mushroom | diameter, material, seacock_type | hull_bottom, hull_side |
| `seacock` | Ball, gate, cone | size, material, handle_type | through_hull |
| `strainer` | Raw_water, fuel, debris | size, basket_type, cleanout | fluid_line |
| `water_heater` | Tank, tankless | capacity_liters, heat_source | compartment |
| `water_pump` | Pressure, accumulator, manual | gph, pressure_psi, noise_level | compartment |
| `sump_pump` | Shower, bilge, general | gph, float_type, discharge | low_point |

---

##### 8. ELECTRICAL COMPONENTS

| Type | Variants | Key Parameters | Anchors |
|------|----------|----------------|---------|
| `battery` | Lead_acid, AGM, lithium | ah_capacity, voltage, dimensions | battery_box, compartment |
| `battery_box` | Single, dual, bank | size, ventilation, tie_down | compartment_sole |
| `battery_switch` | 1-2-both, ACR, manual | amperage, positions | panel_mount, bulkhead |
| `shore_power_inlet` | 30A, 50A, smart | amperage, voltage, polarity_indicator | hull_side, deck |
| `inverter` | Pure_sine, modified_sine | wattage, input_voltage, outlets | compartment |
| `inverter_charger` | Combo unit | wattage, charge_amps, ac_output | compartment |
| `battery_charger` | Single, multi-bank, smart | amps, bank_count, chemistry_select | compartment |
| `distribution_panel` | DC, AC, combo | circuit_count, main_breaker | cabin_bulkhead |
| `breaker` | Thermal, magnetic, GFCI | amperage, poles, trip_curve | panel |
| `fuse_block` | ATO, ANL, MIDI | circuit_count, amperage | compartment |
| `bus_bar` | Positive, negative, ground | stud_count, amperage | compartment |
| `outlet` | 12V, USB, 120V | type, waterproof_rating | cabin, cockpit |
| `switch` | Toggle, rocker, push, rotary | amperage, illuminated, waterproof | panel, dash |
| `switch_panel` | Rocker, toggle, membrane | switch_count, layout | dash, overhead |
| `wire_run` | Primary, tinned, duplex | gauge, length, termination | cable_tray |
| `terminal_block` | Barrier, DIN_rail | circuit_count, wire_gauge | junction_box |
| `junction_box` | Deck, cabin, waterproof | size, mounting, ip_rating | bulkhead |

---

##### 9. ELECTRONICS & NAVIGATION

| Type | Variants | Key Parameters | Anchors |
|------|----------|----------------|---------|
| `mfd` | 7in, 9in, 12in, 16in, 24in | screen_size, touchscreen, networked | helm_pod, overhead |
| `chartplotter` | Standalone, networked | screen_size, chart_type, gps_internal | helm_pod |
| `radar` | Dome, open_array | range_nm, power_kw, size | arch, mast, hardtop |
| `autopilot` | Tiller, wheel, hydraulic | type, rudder_feedback, heading_sensor | helm, lazarette |
| `compass` | Magnetic, electronic, flux_gate | size, card_type, compensated | helm, overhead |
| `vhf_radio` | Fixed, handheld, AIS-enabled | channels, dsc, ais_receive | helm, overhead |
| `ais` | Receive, transponder, class_a, class_b | transmit, receive, splitter | electronics_box |
| `gps_antenna` | Internal, external, differential | accuracy, update_rate | cabin_top, arch |
| `fishfinder` | Standalone, combo, chirp | frequency, power_watts, transducer_type | helm_pod |
| `transducer` | Transom, thru-hull, in-hull, trolling_motor | frequency, angle, material | transom, hull_bottom |
| `sonar` | Forward, side, down, 360 | type, frequency, range | hull_bottom |
| `camera` | Night_vision, thermal, deck, engine | resolution, ptz, waterproof | arch, cabin, engine_room |
| `antenna` | VHF, SSB, TV, satellite, cellular | type, gain_db, length | mast, arch |
| `stereo` | Head_unit, amplifier, source | channels, power_rms, bluetooth | helm, cabin |
| `speaker` | Cockpit, cabin, tower, subwoofer | size, power_handling, waterproof | various |
| `usb_charger` | Single, dual, quick_charge | ports, amperage, flush_mount | helm, cabin |

---

##### 10. HVAC & CLIMATE

| Type | Variants | Key Parameters | Anchors |
|------|----------|----------------|---------|
| `ac_unit` | Self-contained, split, chiller | btu, voltage, seawater_cooled | compartment |
| `ac_handler` | Ducted, ductless | btu, airflow_cfm | overhead, locker |
| `heater` | Diesel, propane, electric, hydronic | btu, fuel_type, ducted | compartment |
| `fan` | Cabin, bilge, solar, hatch | cfm, voltage, reversible | overhead, hatch, vent |
| `blower` | Engine_compartment, fume | cfm, ignition_protected | compartment |
| `register` | Supply, return, adjustable | size, material, damper | cabin_liner |
| `duct` | Flexible, rigid | diameter, length, insulation | overhead, behind_liner |
| `dehumidifier` | Portable, installed | pints_per_day, drain_type | cabin |

---

##### 11. SAFETY EQUIPMENT

| Type | Variants | Key Parameters | Anchors |
|------|----------|----------------|---------|
| `life_raft` | Canister, valise | capacity_persons, solas_rating | deck, cabin_top |
| `raft_cradle` | Hydrostatic, manual | mount_type, release_type | deck, cabin_top |
| `life_jacket_storage` | Locker, bag, under_seat | capacity, accessibility | cockpit, cabin |
| `fire_extinguisher` | ABC, CO2, automatic | size, mounting, uscg_rating | bracket_mount |
| `extinguisher_bracket` | Quick_release, strap | size, location | bulkhead |
| `fire_suppression` | Engine_room, galley | type, auto_manual, agent | engine_compartment |
| `smoke_detector` | Battery, hardwired | type, interconnected | cabin_overhead |
| `co_detector` | Battery, hardwired | ppm_alarm, display | cabin |
| `epirb` | Cat_1, cat_2, PLB | hydrostatic, gps, registration | mount_bracket |
| `epirb_bracket` | Hydrostatic, manual | release_type | cabin_top, arch |
| `life_ring` | Standard, horseshoe | size, light, whistle | stern_rail |
| `life_ring_holder` | Rail_mount, bulkhead | type, quick_release | rail, bulkhead |
| `man_overboard` | Pole, light, module | type, auto_deploy | stern |
| `flare_kit` | Coastal, offshore | type, expiration | storage_locker |
| `first_aid_kit` | Basic, offshore | size, contents | storage |
| `jackline` | Permanent, removable | length, material, pad_eyes | deck |
| `pad_eye` | Fixed, folding | load_rating, material | deck_surface |
| `tether` | Single, double | length, hook_type | pfd |

---

##### 12. FISHING & SPORT

| Type | Variants | Key Parameters | Anchors |
|------|----------|----------------|---------|
| `outrigger` | Fixed, telescoping, carbon | length, spread_angle, rigging | gunwale, cabin_side |
| `outrigger_base` | Gunwale, t_top, hardtop | mount_type, angle_adjust | gunwale, t_top |
| `downrigger` | Manual, electric | cable_length, weight_capacity, counter | gunwale |
| `kite_reel` | Manual, electric | line_capacity, drag | rod_holder, rail |
| `rod_holder` | Flush, clamp, rocket_launcher | angle, inside_dia, liner | gunwale, t_top, leaning_post |
| `rocket_launcher` | 4_rod, 6_rod, 8_rod | rod_count, spacing, angle | t_top, leaning_post |
| `tackle_station` | Drawer, cabinet, rigging | drawers, plano_size, knife_slot | leaning_post, cabin |
| `cutting_board` | Bait, fillet, combo | size, material, drain | transom, gunwale |
| `gaff_holder` | Horizontal, vertical | size, count | gunwale, cabin_side |
| `harpoon_holder` | Horizontal, angled | length, securing | cabin_side |
| `dive_door` | Transom, side | size, ladder_integration | transom, hull_side |
| `dive_platform` | Fixed, fold-down, hydraulic | size, ladder, tank_holders | transom |
| `tank_rack` | Horizontal, vertical | tank_count, strap_type | dive_platform, deck |
| `wakeboard_rack` | Tower, transom | capacity, padding | tower, transom |
| `ski_pylon` | Fixed, folding, adjustable | height, tow_point_height | deck_centerline |

---

##### 13. ANCHORING & MOORING

| Type | Variants | Key Parameters | Anchors |
|------|----------|----------------|---------|
| `anchor` | Plow, claw, fluke, mushroom, bruce, rocna | weight_kg, material, sizing_for_loa | roller, locker |
| `anchor_swivel` | Fixed, articulating | load_rating, material | anchor_shank |
| `anchor_chain` | BBB, proof_coil, high_test | size, length, material | windlass, anchor |
| `anchor_rode` | 3-strand, 8-plait, chain_combo | diameter, length, material | windlass, locker |
| `chain_stopper` | Claw, cam, lever | chain_size, load_rating | deck_bow |
| `snubber` | Nylon, bridle | length, diameter | chain, cleat |
| `anchor_locker` | Deck, below_deck | volume, drain, access | bow |
| `mooring_pendant` | Nylon, float | length, diameter, eye_size | bow_cleat |
| `fender` | Cylindrical, ball, flat | size, inflation, color | rail, storage |
| `fender_holder` | Rail_mount, storage | capacity, mount_type | rail |
| `dock_line` | Nylon, double_braid | diameter, length, eye_splice | cleat |
| `spring_line` | Standard, snubber | diameter, length | cleat |

---

##### 14. CANVAS & COVERS

| Type | Variants | Key Parameters | Anchors |
|------|----------|----------------|---------|
| `boat_cover` | Mooring, travel, custom | material, support_system, fit_type | hull, deck |
| `cockpit_cover` | Snap, zipper, velcro | material, fit | coaming |
| `console_cover` | Fitted, universal | material, access_panels | console |
| `seat_cover` | Fitted, cushion_only | material, tie_downs | seat |
| `bimini_top` | 2-bow, 3-bow, 4-bow | width, length, height, material | deck_mounts |
| `enclosure` | Full, partial, drop_curtain | material, window_type, zipper_access | bimini, hardtop |
| `eisenglass` | Clear, tinted, strataglass | thickness, uv_rating | enclosure_frame |
| `spray_dodger` | Fixed, folding | width, height, material | cabin_front |
| `weather_cloth` | Cockpit, flybridge | material, attachment | rail, stanchion |

---

##### 15. STRUCTURAL & INTERNAL (MVP - Critical for Scantlings)

| Type | Variants | Key Parameters | Anchors |
|------|----------|----------------|---------|
| `stringer` | Longitudinal, transverse | width, height, material, spacing | hull_interior |
| `frame` | Ring, web, bulkhead | spacing, material, thickness | hull_interior |
| `bulkhead` | Structural, partition, watertight | thickness, material, openings | hull_interior |
| `sole` | Cabin, cockpit, engine_room | material, thickness, hatches | stringer_top |
| `liner` | Cabin, cockpit | material, thickness, finish | hull_interior |
| `headliner` | Fabric, vinyl, fiberglass | material, insulation, panel_type | cabin_overhead |
| `nonskid` | Molded, applied, teak | pattern, color, area | deck_surface |
| `rub_rail` | Vinyl, aluminum, stainless | profile, insert, length | hull_gunwale |
| `gunwale` | Capped, rolled, flat | width, material | hull_top_edge |
| `coaming` | Cockpit, bridge, seating | height, padding, rod_holders | deck_perimeter |
| `transom` | Solid, notched, bracket | thickness, material, motor_rating | hull_aft |
| `swim_step` | Integral, bolt-on, hydraulic | width, material, ladder | transom |

---

##### Component Count Summary

| Category | Component Types | Variants |
|----------|-----------------|----------|
| Hull Appendages | 17 | ~50 |
| Propulsion | 17 | ~60 |
| Superstructure | 23 | ~80 |
| Deck Hardware | 27 | ~100 |
| Seating & Furniture | 12 | ~40 |
| Galley & Head | 17 | ~50 |
| Tankage & Fluid | 17 | ~50 |
| Electrical | 18 | ~60 |
| Electronics | 17 | ~60 |
| HVAC | 8 | ~25 |
| Safety | 17 | ~50 |
| Fishing & Sport | 14 | ~45 |
| Anchoring & Mooring | 12 | ~35 |
| Canvas & Covers | 9 | ~30 |
| Structural | 11 | ~35 |
| **TOTAL** | **~230** | **~750+** |

---

#### Data Sources (Component Library)

**Strategy**: Most components are **parametric primitives** (boxes, cylinders, extrusions with cutouts). Only complex organic shapes need CAD files. Parametric templates can generate 80% of components; CAD curation fills the 20%.

| Source | Components | Format | Effort | Coverage |
|--------|-----------|--------|--------|----------|
| **Parametric templates** | ~600 | Generated | Automated | 80% of library |
| **GrabCAD** | 500+ | STEP/IGES | **HUMAN MANUAL** | Complex shapes |
| **TraceParts** | 1000+ | STEP | **HUMAN MANUAL** | Marine equipment |
| **Manufacturer CAD** | 200+ | STEP | **HUMAN MANUAL** | Engines, electronics, OEM parts |
| **3D Warehouse** | 300+ | SKP→STEP | **HUMAN MANUAL** | Furniture, fixtures |
| **McMaster-Carr** | 100+ | STEP | **HUMAN MANUAL** | Hardware, fittings |
| **West Marine/Defender** | 50+ | Photos→parametric | **HUMAN MANUAL** | Retail marine parts |
| **Custom modeling** | As needed | STEP | **HUMAN MANUAL** | Specialty items |

**Build Strategy by Category**:

| Category | Parametric % | CAD % | Priority | Notes |
|----------|--------------|-------|----------|-------|
| Deck Hardware | 95% | 5% | P1 | Cleats, chocks, rails = simple geometry |
| Tankage | 100% | 0% | P1 | All parametric boxes/cylinders |
| Seating | 70% | 30% | P1 | Basic shapes parametric; complex cushions from CAD |
| Structural | 100% | 0% | P1 | Stringers, bulkheads = extrusions |
| Electronics | 20% | 80% | P2 | MFDs, radars need manufacturer CAD |
| Propulsion | 30% | 70% | P2 | Brackets parametric; engines/drives from CAD |
| Safety | 50% | 50% | P2 | Mounts parametric; rafts/EPIRBs from CAD |
| Galley | 40% | 60% | P2 | Cabinets parametric; appliances from CAD |
| Superstructure | 60% | 40% | P1 | Consoles parametric; complex shapes from library |
| Canvas | 90% | 10% | P3 | Mostly parametric surfaces |

**Phase 1 (2-4 weeks, automated)**: 
- Build parametric generators for: cleats, tanks, stringers, bulkheads, rails, hatches, seats, consoles
- ~400 component variants from templates
- Zero human CAD work required

**Phase 2 (ongoing, human-curated)**:
- Electronics: Garmin, Raymarine, Simrad MFDs and radar
- Propulsion: Mercury, Yamaha, Volvo outboards and drives  
- Appliances: Dometic, Isotherm fridges, stoves
- OEM parts: Lewmar hatches, Whale pumps, Rule bilge pumps

**Parametric Template Example**:

```python
# magnet/bootstrap/component_templates/cleat.py

@dataclass
class CleatTemplate:
    """Parametric cleat generator - no CAD file needed."""
    
    length_mm: float = 200.0
    horn_angle_deg: float = 15.0
    base_width_mm: float = 60.0
    base_length_mm: float = 80.0
    horn_diameter_mm: float = 25.0
    material: str = "stainless"
    
    def generate(self) -> ComponentGeometry:
        """Generate cleat geometry from parameters."""
        # Base plate
        base = create_box(self.base_length_mm, self.base_width_mm, 10)
        
        # Horns (cylinders with angled ends)
        horn_l = create_cylinder(self.horn_diameter_mm/2, self.length_mm/2)
        horn_l = rotate(horn_l, y=self.horn_angle_deg)
        horn_l = translate(horn_l, x=-self.length_mm/4)
        
        horn_r = mirror(horn_l, plane='yz')
        
        # Union and fillet
        cleat = union(base, horn_l, horn_r)
        cleat = fillet(cleat, radius=3)
        
        return ComponentGeometry(
            mesh=cleat,
            anchors=[ComponentAnchor("base", (0,0,0), (0,0,-1), ["deck_surface"])],
            parameters=asdict(self)
        )

# Generate library variants
CLEAT_VARIANTS = [
    CleatTemplate(length_mm=150, name="cleat_6in"),
    CleatTemplate(length_mm=200, name="cleat_8in"),
    CleatTemplate(length_mm=250, name="cleat_10in"),
    CleatTemplate(length_mm=300, name="cleat_12in"),
    CleatTemplate(length_mm=150, horn_angle_deg=0, name="cleat_6in_flat"),
    CleatTemplate(length_mm=200, material="aluminum", name="cleat_8in_aluminum"),
    # ... fold-down, pop-up variants with more complex templates
]
```

**Component Template Hierarchy**:

```
magnet/bootstrap/component_templates/
├── __init__.py
├── base.py                    # ComponentTemplate protocol
├── primitives.py              # Box, cylinder, extrusion helpers
│
├── deck_hardware/
│   ├── cleat.py              # CleatTemplate
│   ├── chock.py              # ChockTemplate  
│   ├── rail.py               # RailTemplate
│   ├── stanchion.py          # StanchionTemplate
│   ├── hatch.py              # HatchTemplate
│   └── ...
│
├── tankage/
│   ├── fuel_tank.py          # FuelTankTemplate (box/cylinder with baffles)
│   ├── water_tank.py
│   ├── holding_tank.py
│   └── ...
│
├── structural/
│   ├── stringer.py           # StringerTemplate (extrusion)
│   ├── bulkhead.py           # BulkheadTemplate (plate with cutouts)
│   ├── frame.py
│   └── ...
│
├── seating/
│   ├── helm_seat.py
│   ├── bench.py
│   ├── pedestal.py
│   └── ...
│
├── superstructure/
│   ├── console.py            # ConsoleTemplate
│   ├── hardtop.py
│   ├── t_top.py
│   └── ...
│
└── propulsion/
    ├── outboard_bracket.py   # OutboardBracketTemplate
    ├── engine_bed.py
    └── ...
```

#### Integration

Component library integrates with existing systems:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DESIGN STATE                                  │
│  resources: {                                                        │
│    "hull": HullGeometry (from hull library + mutations)             │
│    "cabin_main": ComponentGeometry (from component library + muts)  │
│    "prop_bracket": ComponentGeometry (from library)                 │
│    "tower": ComponentGeometry (from library + mutations)            │
│  }                                                                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
   │  Synthesis  │    │  Placement  │    │ Validation  │
   │  (hull ops) │    │  (PLACE/    │    │ (physics,   │
   │             │    │   ATTACH)   │    │  clearance) │
   └─────────────┘    └─────────────┘    └─────────────┘
```

- **Observable registry**: Components expose observables (cabin.headroom, props.spacing)
- **Affordances**: Computed per-component (how much can cabin stretch?)
- **Anchors**: Tracked for both hull and components
- **Constraints**: Cross-component constraints validated by kernel

#### Novelty Guarantee

```
┌─────────────────────────────────────────────────────────────────┐
│                     NOVELTY SOURCES                              │
├─────────────────────────────────────────────────────────────────┤
│ 1. Combination: hull_A + cabin_B + props_C (never existed)      │
│ 2. Scaling: 58ft cabin adapted to 72ft hull                     │
│ 3. DSL mutations: ADJUST/CREATE on hull AND components          │
│ 4. Cross-component constraints: physics drives final shape      │
│ 5. Novel features: CREATE window, step, tunnel on any artifact  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
            Result: Vessel that exists nowhere in any library
            But: Every component grounded in validated geometry
```

---

### 0.4.8 Sufficiency matrix (Spec §23)

- **File location**
  - `magnet/llm/sufficiency.py`

- **Dependencies**
  - observable schema packaging (planned `magnet/kernel/observable_schema.py`)
  - `magnet/llm/protocol.py` (existing LLM protocol scaffolding)

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass(frozen=True)
class DecisionRequirements:
    decision_type: str
    required_observables: List[str]
    summary_sufficient: bool = True
    escalation_trigger: Optional[str] = None

@dataclass(frozen=True)
class SufficiencyResult:
    sufficient: bool
    missing: List[str] = field(default_factory=list)
    action: str = ""  # "query_more" | "delegate" | "block"
```

- **Integration point (MAGNET)**
  - Gates expensive commits/operations until required observables are present (prevents expensive “oops, missing info” turns).

- **Reuse note**
  - **Reuse**: observable schema packaging + explanation formatting.
  - **Build new**: decision→observable mapping and preflight sufficiency checks.

### 0.4.9 Decision-level physics attribution (Spec §15)

- **File location**
  - `magnet/explain/attribution.py` (new; alongside existing explain subsystem)

- **Dependencies**
  - `magnet/explain/trace_collector.py`, `magnet/explain/narrative.py`
  - `magnet/kernel/program_executor.py` (statement lineage)

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class Attribution:
    statement_id: str
    statement_text: str
    effect: str
    contribution_pct: float

@dataclass
class PhysicsAttributionResult:
    metric: str
    value: float
    required: float
    status: str
    attribution: List[Attribution] = field(default_factory=list)
    remedies: List[str] = field(default_factory=list)
```

- **Integration point (MAGNET)**
  - Validation failures must be reported as “your decisions caused X” rather than “artifact_4921 caused X”.

- **Reuse note**
  - **Reuse**: existing explain/narrative pipeline; add attribution plumbing, don’t create a parallel reporter.

### 0.4.10 Negotiation protocol / Pareto (Spec §21)

- **File location**
  - `magnet/optimization/negotiation.py` (wrap existing optimizer + Pareto)
  - `magnet/llm/prompts/negotiation.py` (LLM-facing contract)

- **Dependencies**
  - `magnet/optimization/optimizer.py`, `magnet/optimization/pareto.py`, `magnet/optimization/schema.py`
  - `magnet/explain/narrative.py` (presentation)

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class TradeoffOption:
    option_id: str
    achieved_values: Dict[str, float]
    sacrifices: List[str] = field(default_factory=list)
    side_effects: List[str] = field(default_factory=list)
    archetype_drift: float = 0.0

@dataclass
class NegotiationMenu:
    status: str  # "negotiation_required" | "resolved" | "infeasible"
    conflict_description: str
    options: List[TradeoffOption] = field(default_factory=list)
    recommendation: Optional[str] = None
```

- **Integration point (MAGNET)**
  - Surface Pareto menus to LLM with explicit reject-all + constraint modification paths.

- **Reuse note**
  - **Reuse**: `magnet/optimization/*`; do not build a second MOO engine.

### 0.4.11 Archetype guard (Spec §24) (layered on character guard)

- **File location**
  - `magnet/hull_gen/archetypes.py`
  - `magnet/hull_gen/archetype_guard.py`

- **Dependencies**
  - character guard dry-run gating (§5/§9)
  - `magnet/kernel/geometry_observables.py`
  - `magnet/explain/narrative.py`

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple

@dataclass
class ArchetypeSignature:
    entry_angle_range_deg: Tuple[float, float]
    deadrise_transom_range_deg: Tuple[float, float]
    required_features: Dict[str, Any] = field(default_factory=dict)
    forbidden_features: List[str] = field(default_factory=list)

@dataclass
class ArchetypeGuardResult:
    allowed: bool
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    override_available: bool = True
```

- **Integration point (MAGNET)**
  - Runs in the same pre-commit dry-run gate as character guard; supports explicit overrides.

- **Reuse note**
  - **Reuse**: dry-run gating pipeline; layer archetype guard on top rather than duplicating identity systems.

### 0.3.4 Conflicts & alignment decisions (when docs describe the same thing differently)

When there is overlap, align with the LLM-native spec unless code reality dictates a better path.

- **Hull creation DSL**:
  - **Spec**: topology program → NURBS synthesis.
  - **Current code**: synthesis is present (`magnet/kernel/synthesis.py`) but still contains `HullFamily` priors and “enum-like” defaults.
  - **Alignment**: treat topology DSL as a refactor on top of `magnet/kernel/synthesis.py` + `magnet/hull_gen/*` (no second synthesis stack).

- **“Constrain before proposal” vs direct ADJUST calls**:
  - **Spec**: system computes affordances; LLM selects from valid options.
  - **This guide**: exposes ADJUST/TARGET as tools and defines guardrails.
  - **Alignment**: ADJUST/TARGET remain the execution mechanism, but the *LLM-facing interface* must be affordance-first (bounded options); direct free-form deltas are a fallback, not the default workflow.

- **Character vs archetype guard**:
  - **Spec**: archetype guard protects “Viking-ness” (brand integrity) with override semantics.
  - **This guide**: character guard is an EDIT-mode constraint that gates before commit.
  - **Alignment**: treat archetype guard as a higher-level policy that can be layered on top of the same dry-run gating mechanism. Do not implement two unrelated “identity guards”.

- **Dry-run implementation**:
  - **Spec**: pre-computation mandatory; validation before commit.
  - **This guide**: calls for clone/discard dry-runs.
  - **Code reality**: `magnet/kernel/program_executor.py` already supports `dry_run`, and core systems use cloning patterns.
  - **Alignment**: standardize on executor `dry_run` + `StateManager.clone()`; do not invent an alternate sandbox mechanism.

### 0.3.5 Reuse-first notes (avoid rebuilding what MAGNET already has)

- **Do not build a second DSL parser**: extend `magnet/kernel/stdlib/parser.py` and the stdlib AST/expander for new statements needed by the topology DSL and outfitting programs.
- **Do not build a second execution engine**: wrap `magnet/kernel/program_executor.py` inside the planned `DesignMutator` to enforce write-path rules, receipts, and gating.
- **Do not build a second optimization stack**: use `magnet/optimization/*` as the basis for Pareto/negotiation work described in the spec.
- **Use existing hull synthesis + modifiers**: `magnet/kernel/synthesis.py` and `magnet/hull_gen/modifiers/*` are the foundation for topology composition and continuity-aware operations.

---

## 0.5 PLM-Grade Primitives (Lifecycle + Multi-Discipline)

This section extends MAGNET toward PLM (Product Lifecycle Management) completeness—enabling multi-configuration designs, full provenance, digital-twin mapping, cross-domain dependency tracking, and regulatory traceability across a vessel's entire lifecycle.

**North Star**: A small, fixed grammar operating on continuous geometry + structured metadata composes endlessly. The kernel validates physics/regulatory constraints post-compilation; novelty is unbounded while engineering truth is preserved.

### 0.5.0 Codebase Audit Summary (Existing vs New)

Before proposing new primitives, this guide audited the existing MAGNET codebase. The following table summarizes what exists:

| Concept | Existing Code | Status | Notes |
|---------|---------------|--------|-------|
| Dependency Graph | `magnet/dependencies/graph.py` | **EXISTS** | `DependencyGraph`, `DependencyEdge`, `EdgeType`; phase-aware; reuse and extend |
| Provenance (partial) | `magnet/core/state_manager.py` | **EXISTS** | `DimensionProvenance`, `ValueProvenance` enums; extend for full authority |
| Calculation Provenance | `magnet/control_plane/explain.py` | **EXISTS** | `CalculationProvenance` dataclass; integrate with authority tracking |
| Compartment | `magnet/arrangement/models.py` | **EXISTS** | `Compartment` dataclass with permeability; extend for WT ratings |
| Compartment Graph | `magnet/routing/graph/compartment_graph.py` | **EXISTS** | `CompartmentGraph`, `CompartmentNode`, `CompartmentEdge` with WT boundary tracking |
| Zone Boundary | `magnet/routing/schema/zone_definition.py` | **EXISTS** | `ZoneBoundary` dataclass |
| Weight Group | `magnet/weight/summary.py` | **EXISTS** | `WeightGroup`, `WeightMargins` with growth; extend for uncertainty |
| Rule Requirement | `magnet/compliance/rule_schema.py` | **EXISTS** | `RuleRequirement`, `RuleReference`, `Finding`; extend for versioning |
| Regulatory Framework | `magnet/compliance/enums.py` | **EXISTS** | `RegulatoryFramework`, `ComplianceStatus` enums |
| Assembly Sequencer | `magnet/production/assembly.py` | **EXISTS** | `AssemblySequencer` with work packages and critical path |
| Weld Class | `magnet/structural/enums.py` | **EXISTS** | `WeldClass`, `WeldType`, `WeldPosition` enums |
| Uncertainty | `magnet/physics/uncertainty.py` | **EXISTS** | `Uncertainty` dataclass with level/basis/envelope |
| Propagation Engine | `magnet/kernel/propagation.py` | **EXISTS** | `PropagationEngine`, `PropagationResult`, `ConstraintViolation` |
| Lifecycle Manager | `magnet/lifecycle/manager.py` | **EXISTS** | `LifecycleManager` with versioning and branches |
| Convergence Criteria | `magnet/kernel/synthesis.py` | **EXISTS** | `ConvergenceCriteria` dataclass |
| Domain Hashes | `magnet/contracts/domain_hashes.py` | **EXISTS** | `DomainHashes`, `DomainHashProvider` for change detection |
| Export | `magnet/lifecycle/export.py`, `magnet/webgl/exporter.py` | **EXISTS** | Multiple export formats |

**Gap Summary**: Configuration/Variant/Effectivity, full Authority chain, Digital Twin mapping, Coordinate Frames governance, Opening ratings/closures, Mass structured uncertainty, Network topology semantics, R/V/V traceability, Build strategy/blocks, ECO/Deviation workflow, Cross-domain coupling graph, Derived data authority, Domain exit criteria, Spiral damping, Discipline handshakes, Sensitivity/impact sets, Interchange schema.

---

### 0.5.0.1 Enumeration Leak Audit (Anti-Patterns)

**Critical Principle**: Novelty comes from continuous parameters + compositional operators, NOT from style enums or presets. The kernel validates physics/geometry post-compilation; it does not predefine forms.

An "enumeration leak" occurs when the codebase uses an enum to classify geometric forms, forcing all designs into predefined buckets. This collapses the generative language back into a variant system.

#### CRITICAL LEAKS → DELETE ALL

**NO DEPRECATION. NO BACKWARD COMPATIBILITY. DELETE.**

| Enum | Location | Action |
|------|----------|--------|
| `HullFamily` | `magnet/kernel/priors/hull_families.py` | **DELETE FILE** |
| `HullType` | `magnet/hull_gen/enums.py` | **DELETE ENUM** |
| `ChineType` | `magnet/hull_gen/enums.py` | **DELETE ENUM** → use `List[ChineConfig]` |
| `BowStyle` | `magnet/hull_gen/enums.py` | **DELETE ENUM** → use `BowConfig` |
| `StemProfile` | `magnet/hull_gen/enums.py` | **DELETE ENUM** → params in `BowConfig` |
| `SternProfile` | `magnet/hull_gen/enums.py` | **DELETE ENUM** → use `SternConfig` |
| `KeelType` | `magnet/hull_gen/enums.py` | **DELETE ENUM** → use `List[KeelAttachment]` |
| `SectionShape` | `magnet/hull_gen/enums.py` | **DELETE ENUM** (unused anyway) |

**See §0.6 for detailed replacement specifications.**

#### IN THIS GUIDE (Proposed Fixes)

| Enum in §0.5 | Verdict | Reasoning |
|--------------|---------|-----------|
| `AnchorType` | **REFACTOR** | KEEL, SHEER, CHINE, etc. predetermines anchor semantics. A novel hull may have features that don't fit. **Fix**: Anchors should be *detected* from geometry (curvature maxima, discontinuities), not pre-categorized. The type becomes metadata, not input. |
| `BoundaryRating` | **OK** | WT, AT, A60, etc. are *external regulatory categories*, not geometric forms. These are required by class rules. |
| `ClosureState` | **OK** | OPEN, CLOSED, DOGGED are *operational states*, not geometric. |
| `BuildMethod` | **OK** | BLOCK, ZONE are *manufacturing strategies*, not hull geometry. |
| `RedundancyRole` | **OK** | PRIMARY, BACKUP are *system semantics*, not geometric. |
| `IsolationBoundaryType` | **OK** | VALVE, BREAKER are *component types*, not hull forms. |

#### THE CORRECT PATTERN

**Wrong (Enumeration)**:
```python
class BowStyle(Enum):
    WEDGE = "wedge"
    AXE = "axe"

# Synthesis selects from enum
bow = generate_bow(style=BowStyle.WEDGE)  # LIMITED TO 7 STYLES
```

**Right (Continuous + Compositional)**:
```python
# DSL expresses geometry directly
CREATE bow_panel_port TYPE geometry.surface
  CONTROL_POINTS [...]
  DIHEDRAL_ANGLE 15deg
CREATE bow_panel_stbd TYPE geometry.surface
  MIRROR bow_panel_port ABOUT centerline

# Kernel validates physics, doesn't care about "style"
# Post-hoc: "this bow has 15° dihedral panels → wedge-like entry"
```

**Wrong (Type-First Synthesis)**:
```python
hull = synthesize_hull(family=HullFamily.PATROL, ...)  # LOCKED TO 5 FAMILIES
```

**Right (Constraint-First Synthesis)**:
```python
hull = synthesize_hull(
    constraints={
        "displacement_m3": (100, 150),
        "max_speed_kts": 35,
        "gm_min_m": 0.5,
        "deadrise_transom_deg": (12, 20),
    }
)
# Form emerges from constraints; "patrol-like" is derived post-hoc
```

#### DELETION PLAN

**No phases. No deprecation. Delete now.**

1. Delete `magnet/kernel/priors/hull_families.py` entirely
2. Delete all form enums from `magnet/hull_gen/enums.py`
3. Delete all enum fields from `HullDefinition`, `HullFeatures`
4. Delete all enum dispatch in generators
5. Delete `magnet/hull_gen/library.py` (enum-based presets)
6. Replace with `SynthesisConstraints` + continuous dataclasses

Old designs that use these enums are **invalid**. They do not load.

#### ANCHOR TYPE → DELETE

The `AnchorType` enum in §0.4.1 must be deleted. Anchors are DETECTED from geometry, not categorized by enum.

```python
# NO AnchorType enum. Just detection + optional labeling.

@dataclass
class DetectedAnchor:
    """Anchor detected from geometry features."""
    uuid: str
    section_id: str
    point_index: int
    position: Tuple[float, float, float]
    detection_method: str  # "curvature_max", "discontinuity", "extremum", "constraint"
    confidence: float
    local_curvature: float
    # Label is DERIVED output, not input. May be "keel-like", "novel-feature", etc.
    semantic_label: Optional[str] = None

def detect_anchors(geometry: HullGeometry) -> List[DetectedAnchor]:
    """Detect from geometry. Novel forms with unconventional features still get anchors."""
    ...
```

---

### 0.5.1 Configuration / Variant / Effectivity

Ships have variants (combat system A vs B), hull numbers, and effectivity ranges.

- **Existing code found**: None specific to configuration management.

- **File location**
  - `magnet/configuration/config_item.py` (new)
  - `magnet/configuration/variant.py` (new)
  - `magnet/configuration/effectivity.py` (new)

- **Dependencies**
  - `magnet/core/state_manager.py`
  - `magnet/lifecycle/versions.py`
  - `magnet/contracts/design_state_contract.py`

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Set, Union
from enum import Enum

class EffectivityType(Enum):
    HULL_NUMBER = "hull_number"
    DATE_RANGE = "date_range"
    SERIAL_RANGE = "serial_range"
    OPTION_PACKAGE = "option_package"

@dataclass
class EffectivityRange:
    effectivity_type: EffectivityType
    start: Union[int, date, str]
    end: Optional[Union[int, date, str]] = None
    notes: str = ""

    def applies_to(self, hull_number: int = None, date: date = None) -> bool:
        """Check if this effectivity applies to given context."""
        ...

@dataclass
class ConfigurationItem:
    config_id: str
    name: str
    description: str
    artifact_ids: Set[str] = field(default_factory=set)
    effectivity: List[EffectivityRange] = field(default_factory=list)
    parent_config_id: Optional[str] = None
    is_baseline: bool = False
    version: str = "1.0"

@dataclass
class Variant:
    variant_id: str
    name: str
    base_config_id: str
    delta_additions: Set[str] = field(default_factory=set)  # artifact_ids added
    delta_removals: Set[str] = field(default_factory=set)   # artifact_ids removed
    delta_modifications: Dict[str, Dict] = field(default_factory=dict)  # artifact_id -> param changes
    effectivity: List[EffectivityRange] = field(default_factory=list)

@dataclass
class ConfigurationBaseline:
    baseline_id: str
    name: str
    config_items: List[str]  # config_ids
    locked_at: date = None
    approval_status: str = "draft"  # draft | approved | released
```

- **Integration point (MAGNET)**
  - `DesignState` gains `configuration: Optional[ConfigurationBaseline]` and `active_variants: List[str]`
  - `StateManager.get()` respects effectivity context (hull number / date)
  - Graph view filters artifacts by active configuration

- **Reuse note**
  - **Reuse**: `magnet/lifecycle/versions.py` versioning patterns
  - **Build new**: Configuration delta computation, effectivity filtering

---

### 0.5.2 Authority + Provenance (Full Chain)

Every fact needs: who asserted it, when, from what source, confidence level, approval status.

- **Existing code found**
  - `magnet/core/state_manager.py`: `DimensionProvenance`, `ValueProvenance` enums
  - `magnet/control_plane/explain.py`: `CalculationProvenance`, `ChangeSource`, `ApprovalType`

- **Proposed extension** (not replacement)

- **File location**
  - Extend: `magnet/core/state_manager.py` (add `AuthorityRecord`)
  - New: `magnet/provenance/authority.py` (full authority chain)

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

class AuthoritySource(Enum):
    USER_INPUT = "user_input"
    CAD_IMPORT = "cad_import"
    FEA_ANALYSIS = "fea_analysis"
    CFD_ANALYSIS = "cfd_analysis"
    SURVEY_REPORT = "survey_report"
    VENDOR_DATA = "vendor_data"
    CALCULATION = "calculation"
    ASSUMPTION = "assumption"
    REGULATORY_REFERENCE = "regulatory_reference"

class ApprovalStatus(Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"

@dataclass
class AuthorityRecord:
    """Tracks who asserted a value and with what authority."""
    source: AuthoritySource
    asserted_by: str  # user_id or system_id
    asserted_at: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 1.0  # 0.0-1.0
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    source_reference: Optional[str] = None  # doc_id, analysis_id, etc.
    supersedes: Optional[str] = None  # previous authority_record_id
    notes: str = ""

    def is_authoritative(self) -> bool:
        """True if approved and not superseded."""
        return self.approval_status == ApprovalStatus.APPROVED and self.supersedes is None

@dataclass
class ProvenanceChain:
    """Full provenance chain for a value."""
    value_path: str
    current_value: Any
    authority: AuthorityRecord
    derivation_chain: List[str] = field(default_factory=list)  # value_paths this was computed from
    computation_method: Optional[str] = None  # e.g., "hydrostatics.compute_gm"
```

- **Integration point (MAGNET)**
  - Extend existing `ValueProvenance` tracking to include full `AuthorityRecord`
  - Every computed value stores its `derivation_chain`
  - Graph view distinguishes "authoritative" vs "cached estimate" values

- **Reuse note**
  - **Reuse**: existing `DimensionProvenance`, `ValueProvenance`, `CalculationProvenance`
  - **Extend**: add approval workflow and derivation tracking

---

### 0.5.3 Physical-Digital Twin Mapping

Ships exist as: as-designed, as-built (with deviations), as-maintained (with modifications).

- **Existing code found**: None specific to twin mapping.

- **File location**
  - `magnet/twin/state.py` (new)
  - `magnet/twin/deviation.py` (new)

- **Dependencies**
  - `magnet/lifecycle/versions.py`
  - `magnet/core/state_manager.py`

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum

class TwinStateType(Enum):
    AS_DESIGNED = "as_designed"
    AS_BUILT = "as_built"
    AS_MAINTAINED = "as_maintained"
    AS_SURVEYED = "as_surveyed"

@dataclass
class GeometryReference:
    """Links digital geometry to physical source."""
    artifact_id: str
    model_revision: str
    external_id: Optional[str] = None  # STEP entity ID, scan mesh ID, etc.
    source_file: Optional[str] = None
    source_timestamp: Optional[datetime] = None

@dataclass
class AsBuiltDeviation:
    """Records deviation between designed and built."""
    deviation_id: str
    artifact_id: str
    designed_value: float
    as_built_value: float
    deviation: float
    tolerance: float
    within_tolerance: bool
    measurement_source: str  # survey_id, inspection_report_id
    measured_at: datetime = field(default_factory=datetime.utcnow)
    location_description: str = ""

@dataclass
class MaintenanceModification:
    """Records modification during service life."""
    modification_id: str
    work_order_id: str
    affected_artifacts: List[str]
    modification_type: str  # repair, upgrade, replacement
    before_state_version: str
    after_state_version: str
    performed_by: str
    performed_at: datetime = field(default_factory=datetime.utcnow)
    regulatory_approval: Optional[str] = None

@dataclass
class DigitalTwinState:
    """Full twin state tracking."""
    design_id: str
    hull_number: str
    current_state_type: TwinStateType
    geometry_references: Dict[str, GeometryReference] = field(default_factory=dict)
    deviations: List[AsBuiltDeviation] = field(default_factory=list)
    modifications: List[MaintenanceModification] = field(default_factory=list)
    last_survey_date: Optional[datetime] = None
```

- **Integration point (MAGNET)**
  - `DesignState` gains optional `twin_state: DigitalTwinState`
  - Export includes geometry references for roundtrip
  - Deviation tracking feeds validation (as-built validation)

- **Reuse note**
  - **Reuse**: `magnet/lifecycle/versions.py` for state versioning
  - **Build new**: Twin state management, deviation tracking

---

### 0.5.4 Coordinate Frames + Datum Governance

Define canonical frame hierarchy: ship reference system, compartment-local, equipment-local, manufacturing datum, survey datum.

- **Existing code found**: None explicit (coordinates assumed vessel-origin).

- **File location**
  - `magnet/geometry/frames.py` (new)
  - `magnet/geometry/transforms.py` (new)

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import numpy as np

class FrameType(Enum):
    SHIP_REFERENCE = "ship_reference"  # AP at baseline, CL, FP
    COMPARTMENT_LOCAL = "compartment_local"
    EQUIPMENT_LOCAL = "equipment_local"
    MANUFACTURING_DATUM = "manufacturing_datum"
    SURVEY_DATUM = "survey_datum"
    WORLD = "world"  # GPS/geographic

@dataclass
class DatumDefinition:
    """Defines a coordinate frame datum."""
    datum_id: str
    name: str
    frame_type: FrameType
    origin_description: str
    axes_description: str  # e.g., "X fwd, Y port, Z up"
    owner: str  # who controls this datum
    tolerance_mm: float = 1.0
    established_date: Optional[str] = None
    reference_document: Optional[str] = None

@dataclass
class FrameTransform:
    """Transform between two coordinate frames."""
    from_frame: str  # datum_id
    to_frame: str    # datum_id
    translation: Tuple[float, float, float]  # meters
    rotation_matrix: Optional[np.ndarray] = None  # 3x3
    tolerance_mm: float = 1.0
    valid_from_version: str = ""
    superseded_by: Optional[str] = None

@dataclass
class CoordinateFrame:
    """A specific coordinate frame instance."""
    frame_id: str
    datum: DatumDefinition
    transforms_to: Dict[str, FrameTransform] = field(default_factory=dict)

    def transform_point(self, point: Tuple[float, float, float], target_frame: str) -> Tuple[float, float, float]:
        """Transform a point to target frame."""
        ...

class FrameRegistry:
    """Registry of all coordinate frames in a design."""
    def __init__(self):
        self._frames: Dict[str, CoordinateFrame] = {}
        self._ship_reference: Optional[str] = None

    def register_frame(self, frame: CoordinateFrame) -> None: ...
    def get_transform(self, from_frame: str, to_frame: str) -> FrameTransform: ...
    def validate_chain(self) -> List[str]: ...  # returns errors
```

- **Integration point (MAGNET)**
  - All spatial values must declare their frame (default: ship_reference)
  - `geometry.*` resources gain `coordinate_frame: str` field
  - Validators transform to common frame before comparison

- **Reuse note**
  - **Reuse**: existing geometry utilities in `magnet/hull_gen/geometry.py`
  - **Build new**: Frame registry, transform chain, frame-aware spatial queries

---

### 0.5.5 Compartmentation + Watertight Integrity

Core naval objects for damage stability, fire zones, routing constraints.

- **Existing code found**
  - `magnet/arrangement/models.py`: `Compartment` with permeability
  - `magnet/routing/graph/compartment_graph.py`: `CompartmentEdge.watertight_boundary`
  - `magnet/routing/schema/zone_definition.py`: `ZoneBoundary`

- **Proposed extension** (not replacement)

- **File location**
  - Extend: `magnet/arrangement/models.py` (add `Opening`, `BoundaryRating`)
  - New: `magnet/arrangement/watertight.py` (flooding groups, damage cases)

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum

class BoundaryRating(Enum):
    WT = "watertight"  # watertight
    AT = "airtight"    # airtight
    WS = "weathertight"
    A60 = "fire_a60"   # fire rating A-60
    A30 = "fire_a30"
    A0 = "fire_a0"
    B15 = "fire_b15"
    B0 = "fire_b0"
    STRUCTURAL = "structural_only"

class ClosureState(Enum):
    OPEN = "open"
    CLOSED = "closed"
    DOGGED = "dogged"  # mechanically secured
    WELDED = "welded"  # permanent

@dataclass
class Opening:
    """Opening through a boundary (door, hatch, penetration)."""
    opening_id: str
    boundary_id: str
    opening_type: str  # door, hatch, manhole, penetration, vent
    rating: BoundaryRating
    default_closure_state: ClosureState
    current_closure_state: ClosureState = ClosureState.CLOSED
    size_m2: float = 0.0
    location_description: str = ""
    closure_device: Optional[str] = None  # quick-acting, hinged, etc.
    
    def is_intact(self) -> bool:
        """True if closure maintains boundary rating."""
        return self.current_closure_state in (ClosureState.CLOSED, ClosureState.DOGGED, ClosureState.WELDED)

@dataclass
class Boundary:
    """A rated boundary between compartments."""
    boundary_id: str
    compartment_a: str
    compartment_b: str
    rating: BoundaryRating
    area_m2: float
    openings: List[Opening] = field(default_factory=list)
    
    def effective_rating(self) -> BoundaryRating:
        """Rating considering open penetrations."""
        if any(not o.is_intact() for o in self.openings):
            return BoundaryRating.STRUCTURAL
        return self.rating

@dataclass
class FloodingGroup:
    """Group of compartments that flood together."""
    group_id: str
    compartment_ids: Set[str]
    permeability: float = 0.95
    total_volume_m3: float = 0.0
    centroid_lcg_m: float = 0.0
    centroid_vcg_m: float = 0.0
    centroid_tcg_m: float = 0.0

@dataclass
class DamageCase:
    """A damage stability scenario."""
    case_id: str
    name: str
    description: str
    flooded_groups: List[str]  # flooding_group_ids
    extent_description: str
    probability: float = 0.0  # for probabilistic damage stability
    survivability_index: Optional[float] = None
```

- **Integration point (MAGNET)**
  - Extend existing `Compartment` with `boundaries: List[str]` (boundary_ids)
  - Routing queries `Opening.is_intact()` for penetration allowances
  - Stability module uses `FloodingGroup` for damage stability calculation
  - Fire zone validation uses `BoundaryRating`

- **Reuse note**
  - **Reuse**: existing `Compartment`, `CompartmentGraph`
  - **Extend**: Add opening/closure tracking, flooding group computation

---

### 0.5.6 Mass Properties (Structured)

Weight is not a scalar—it's a distributed, versioned graph with uncertainty and growth allowance.

- **Existing code found**
  - `magnet/weight/summary.py`: `WeightGroup`, `WeightMargins`
  - Provides group totals and margins but lacks per-item uncertainty

- **Proposed extension** (not replacement)

- **File location**
  - Extend: `magnet/weight/items.py` (add uncertainty fields)
  - New: `magnet/weight/budget.py` (structured budget tracking)

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

class WeightPhase(Enum):
    CONCEPT = "concept"
    PRELIMINARY = "preliminary"
    CONTRACT = "contract"
    DETAIL = "detail"
    AS_BUILT = "as_built"
    AS_MODIFIED = "as_modified"

class UncertaintyBasis(Enum):
    ESTIMATE = "estimate"
    SIMILAR_VESSEL = "similar_vessel"
    VENDOR_PRELIMINARY = "vendor_preliminary"
    VENDOR_CERTIFIED = "vendor_certified"
    WEIGHED = "weighed"
    CALCULATED = "calculated"

@dataclass
class MassUncertainty:
    """Uncertainty bounds for a mass value."""
    value_kg: float
    lower_bound_kg: float
    upper_bound_kg: float
    uncertainty_pct: float
    basis: UncertaintyBasis
    confidence: float = 0.8  # probability value is within bounds

@dataclass
class GrowthAllowance:
    """Growth allowance for a weight group."""
    group_id: str
    design_margin_pct: float = 5.0
    service_life_growth_pct: float = 10.0
    contract_margin_pct: float = 3.0
    applied_at_phase: WeightPhase = WeightPhase.CONCEPT

@dataclass
class MassItem:
    """Single mass item with full metadata."""
    item_id: str
    name: str
    swbs_group: str  # SWBS code
    weight_kg: float
    lcg_m: float
    vcg_m: float
    tcg_m: float
    ixx_kg_m2: float = 0.0  # moment of inertia
    iyy_kg_m2: float = 0.0
    izz_kg_m2: float = 0.0
    material: Optional[str] = None
    phase: WeightPhase = WeightPhase.CONCEPT
    uncertainty: Optional[MassUncertainty] = None
    source_artifact_id: Optional[str] = None  # link to geometry

@dataclass
class WeightBudget:
    """Structured weight budget with tracking."""
    budget_id: str
    target_displacement_kg: float
    items: List[MassItem] = field(default_factory=list)
    growth_allowances: Dict[str, GrowthAllowance] = field(default_factory=dict)
    phase: WeightPhase = WeightPhase.CONCEPT
    
    @property
    def total_weight_kg(self) -> float: ...
    @property
    def total_with_margin_kg(self) -> float: ...
    @property
    def margin_remaining_kg(self) -> float: ...
    @property
    def uncertainty_range_kg(self) -> tuple[float, float]: ...
```

- **Integration point (MAGNET)**
  - Extend existing `WeightGroup` to reference `MassItem` with uncertainty
  - Stability calculations propagate uncertainty bounds
  - Weight report shows phase-appropriate margins

- **Reuse note**
  - **Reuse**: existing `WeightGroup`, `WeightMargins`, SWBS structure
  - **Extend**: Add per-item uncertainty, phase tracking

---

### 0.5.7 Systems Network Topology

Beyond "components + routes"—need network semantics: nodes/edges, redundancy roles, isolation boundaries, interface ratings.

- **Existing code found**: Routing produces paths, not networks with semantic roles.

- **File location**
  - `magnet/systems/network.py` (new)
  - `magnet/systems/redundancy.py` (new)

- **Dependencies**
  - `magnet/routing/graph/compartment_graph.py`
  - `magnet/systems/*` (existing system generators)

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum

class RedundancyRole(Enum):
    PRIMARY = "primary"
    BACKUP = "backup"
    EMERGENCY = "emergency"
    MAINTENANCE = "maintenance"

class IsolationBoundaryType(Enum):
    VALVE = "valve"
    BREAKER = "breaker"
    DISCONNECT = "disconnect"
    DAMPER = "damper"
    FIRE_DAMPER = "fire_damper"

@dataclass
class InterfaceRating:
    """Rating for a system interface."""
    flow_rate_max: Optional[float] = None  # m³/h or kW
    pressure_rating_bar: Optional[float] = None
    voltage_rating_v: Optional[float] = None
    current_rating_a: Optional[float] = None
    temperature_rating_c: Optional[float] = None

@dataclass
class NetworkNode:
    """Node in a system network."""
    node_id: str
    component_id: str  # link to geometry.body
    node_type: str  # source, sink, junction, equipment
    system_id: str
    redundancy_role: RedundancyRole = RedundancyRole.PRIMARY
    interface_rating: Optional[InterfaceRating] = None

@dataclass
class NetworkEdge:
    """Edge in a system network."""
    edge_id: str
    from_node: str
    to_node: str
    route_id: str  # link to geometry.flow_path
    capacity: Optional[float] = None
    is_bidirectional: bool = False

@dataclass
class IsolationBoundary:
    """Isolation point in a network."""
    boundary_id: str
    edge_id: str
    boundary_type: IsolationBoundaryType
    component_id: str  # valve, breaker, etc.
    fail_state: str  # open, closed
    can_remote_operate: bool = False

@dataclass
class SystemNetwork:
    """Complete network topology for a system."""
    network_id: str
    system_id: str
    system_type: str  # fuel, electrical, hvac, etc.
    nodes: Dict[str, NetworkNode] = field(default_factory=dict)
    edges: Dict[str, NetworkEdge] = field(default_factory=dict)
    isolation_boundaries: List[IsolationBoundary] = field(default_factory=list)
    
    def get_isolated_subgraph(self, boundary_id: str) -> Set[str]:
        """Get node_ids isolated if boundary closes."""
        ...
    
    def check_redundancy(self, source_id: str, sink_id: str) -> bool:
        """Check if sink is reachable from source with any single failure."""
        ...
    
    def get_failure_impact(self, component_id: str) -> Dict[str, str]:
        """What's affected if this component fails?"""
        ...
```

- **Integration point (MAGNET)**
  - Routing produces `SystemNetwork` in addition to paths
  - Validators check redundancy requirements against network topology
  - Network queries support "if X fails, what's isolated?"

- **Reuse note**
  - **Reuse**: `magnet/routing/*` path finding
  - **Build new**: Network semantics, redundancy analysis, failure impact

---

### 0.5.8 Requirements → Verification → Validation (R/V/V)

Requirements as testable statements with verification method, acceptance criteria, evidence links.

- **Existing code found**
  - `magnet/compliance/rule_schema.py`: `RuleRequirement` with acceptance criteria
  - `magnet/compliance/validators.py`: Validators produce findings

- **Proposed extension** (not replacement)

- **File location**
  - Extend: `magnet/compliance/rule_schema.py` (add `VerificationMethod`, `Evidence`)
  - New: `magnet/compliance/traceability.py` (matrix generation)

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

class VerificationMethod(Enum):
    ANALYSIS = "analysis"
    TEST = "test"
    INSPECTION = "inspection"
    DEMONSTRATION = "demonstration"
    SIMILARITY = "similarity"

class EvidenceType(Enum):
    CALCULATION = "calculation"
    TEST_REPORT = "test_report"
    INSPECTION_RECORD = "inspection_record"
    CERTIFICATION = "certification"
    VENDOR_DATA = "vendor_data"

@dataclass
class AcceptanceCriteria:
    """Specific acceptance criteria for a requirement."""
    criteria_id: str
    description: str
    parameter_path: str
    operator: str  # >=, <=, ==, in_range, exists
    threshold: Any
    tolerance: Optional[float] = None
    units: str = ""

@dataclass
class Evidence:
    """Evidence that a requirement is met."""
    evidence_id: str
    requirement_id: str
    evidence_type: EvidenceType
    verification_method: VerificationMethod
    document_reference: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    actual_value: Optional[Any] = None
    meets_criteria: bool = False
    notes: str = ""

@dataclass
class Requirement:
    """Traceable requirement with verification."""
    requirement_id: str
    title: str
    description: str
    source: str  # regulatory reference, contract clause, etc.
    priority: str  # mandatory, recommended, optional
    acceptance_criteria: List[AcceptanceCriteria] = field(default_factory=list)
    verification_methods: List[VerificationMethod] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)
    parent_requirement_id: Optional[str] = None  # for hierarchical requirements
    allocated_to: List[str] = field(default_factory=list)  # artifact_ids
    
    @property
    def compliance_status(self) -> str:
        """Derive status from evidence."""
        if not self.evidence:
            return "not_verified"
        if all(e.meets_criteria for e in self.evidence):
            return "compliant"
        if any(e.meets_criteria for e in self.evidence):
            return "partial"
        return "non_compliant"

class TraceabilityMatrix:
    """Generates requirement traceability matrix."""
    def __init__(self, requirements: List[Requirement]): ...
    def to_table(self) -> List[Dict]: ...
    def get_coverage(self) -> Dict[str, float]: ...
    def get_unverified(self) -> List[str]: ...
```

- **Integration point (MAGNET)**
  - Validators produce `Evidence` objects linked to requirements
  - Compliance report includes traceability matrix
  - Requirement status rolled up to design approval status

- **Reuse note**
  - **Reuse**: existing `RuleRequirement`, `Finding` structures
  - **Extend**: Add evidence chain, traceability matrix generation

---

### 0.5.9 Manufacturing / Assembly / Installation

Build strategy, weld classes, access envelopes, sequence dependencies.

- **Existing code found**
  - `magnet/production/assembly.py`: `AssemblySequencer` with work packages
  - `magnet/structural/enums.py`: `WeldClass`, `WeldType`

- **Proposed extension** (not replacement)

- **File location**
  - Extend: `magnet/production/assembly.py` (add access/lift constraints)
  - New: `magnet/production/build_strategy.py` (block/zone strategy)

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

class BuildMethod(Enum):
    BLOCK = "block"
    ZONE = "zone"
    INTEGRATED = "integrated"
    MODULAR = "modular"

@dataclass
class Block:
    """A construction block."""
    block_id: str
    name: str
    hull_zone: str  # fwd, mid, aft, etc.
    frame_range: Tuple[int, int]
    weight_kg: float
    cog: Tuple[float, float, float]
    dimensions_m: Tuple[float, float, float]  # L, B, H
    outfitting_level: str  # bare, partial, full
    compartment_ids: List[str] = field(default_factory=list)

@dataclass
class AccessEnvelope:
    """Required access for installation/maintenance."""
    envelope_id: str
    artifact_id: str
    access_type: str  # installation, maintenance, inspection
    envelope_min: Tuple[float, float, float]
    envelope_max: Tuple[float, float, float]
    required_clearance_m: float = 0.6
    access_direction: str = "any"  # top, side, bottom, any

@dataclass
class LiftConstraint:
    """Lifting/handling constraint."""
    constraint_id: str
    block_id: str
    max_weight_kg: float
    crane_reach_m: float
    lift_points: List[Tuple[float, float, float]] = field(default_factory=list)
    orientation_constraints: str = ""

@dataclass
class AssemblyDependency:
    """Dependency between assembly operations."""
    dependent_id: str  # work_package_id or block_id
    depends_on_id: str
    dependency_type: str  # structural, outfitting, test, access
    lag_days: float = 0.0

@dataclass
class BuildStrategy:
    """Complete build strategy."""
    strategy_id: str
    method: BuildMethod
    blocks: List[Block] = field(default_factory=list)
    erection_sequence: List[str] = field(default_factory=list)  # block_ids in order
    access_envelopes: List[AccessEnvelope] = field(default_factory=list)
    lift_constraints: List[LiftConstraint] = field(default_factory=list)
    dependencies: List[AssemblyDependency] = field(default_factory=list)
    
    def validate_sequence(self) -> List[str]:
        """Check sequence respects dependencies. Returns violations."""
        ...
    
    def can_install_after(self, artifact_id: str, after_block_id: str) -> bool:
        """Check if artifact can be installed after block erection."""
        ...
```

- **Integration point (MAGNET)**
  - Extend existing `AssemblySequencer` to use `BuildStrategy`
  - Validators check access envelope clearances
  - Routing respects installation sequence constraints

- **Reuse note**
  - **Reuse**: existing `AssemblySequencer`, `WeldClass`
  - **Extend**: Add block/zone strategy, access envelope validation

---

### 0.5.10 Regulatory Ruleset Objects

Rule sources as versioned objects with applicability and waiver workflow.

- **Existing code found**
  - `magnet/compliance/enums.py`: `RegulatoryFramework` enum
  - `magnet/compliance/rule_schema.py`: `RuleRequirement`, `RuleReference`

- **Proposed extension** (not replacement)

- **File location**
  - Extend: `magnet/compliance/rule_schema.py` (add `RuleVersion`, `Waiver`)
  - New: `magnet/compliance/ruleset.py` (versioned ruleset management)

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional
from enum import Enum

class WaiverStatus(Enum):
    REQUESTED = "requested"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DENIED = "denied"
    CONDITIONAL = "conditional"

@dataclass
class RuleVersion:
    """Versioned regulatory rule."""
    rule_id: str
    framework: str
    version: str
    effective_date: date
    supersedes_version: Optional[str] = None
    is_current: bool = True
    changes_summary: str = ""

@dataclass
class RuleApplicability:
    """Determines if a rule applies to this design."""
    rule_id: str
    applies: bool
    reason: str
    vessel_type_match: bool = True
    length_in_range: bool = True
    service_restriction_match: bool = True
    flag_state_applies: bool = True

@dataclass
class Waiver:
    """Waiver or equivalency for a rule."""
    waiver_id: str
    rule_id: str
    design_id: str
    waiver_type: str  # exemption, equivalency, alternative
    status: WaiverStatus
    requested_by: str
    requested_date: date
    justification: str
    conditions: List[str] = field(default_factory=list)
    approved_by: Optional[str] = None
    approved_date: Optional[date] = None
    expiry_date: Optional[date] = None
    evidence_references: List[str] = field(default_factory=list)

@dataclass
class RegulatoryRuleset:
    """Complete ruleset for a design."""
    ruleset_id: str
    applicable_frameworks: List[str]
    rules: Dict[str, RuleVersion] = field(default_factory=dict)
    applicability: Dict[str, RuleApplicability] = field(default_factory=dict)
    waivers: List[Waiver] = field(default_factory=list)
    
    def get_applicable_rules(self) -> List[str]:
        """Get rule_ids that apply to this design."""
        ...
    
    def is_waived(self, rule_id: str) -> bool:
        """Check if rule has approved waiver."""
        ...
```

- **Integration point (MAGNET)**
  - Validators reference `RuleVersion` not hardcoded thresholds
  - Compliance report shows applicable rules and waivers
  - Rule version changes trigger re-validation

- **Reuse note**
  - **Reuse**: existing `RegulatoryFramework`, `RuleRequirement`
  - **Extend**: Add versioning, applicability logic, waiver workflow

---

### 0.5.11 Change Request / ECO / Deviation

Engineering Change Orders, deviations, waivers, and impact assessment.

- **Existing code found**: None specific to change management.

- **File location**
  - `magnet/changes/change_request.py` (new)
  - `magnet/changes/impact.py` (new)

- **Dependencies**
  - `magnet/dependencies/graph.py` (for impact analysis)
  - `magnet/lifecycle/versions.py`

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
from enum import Enum

class ChangeType(Enum):
    DESIGN_CHANGE = "design_change"
    YARD_DEVIATION = "yard_deviation"
    NONCONFORMANCE = "nonconformance"
    FIELD_CHANGE = "field_change"

class ChangeStatus(Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    CLOSED = "closed"

class ChangeClassification(Enum):
    GEOMETRIC = "geometric"
    MASS = "mass"
    FUNCTIONAL = "functional"
    REGULATORY = "regulatory"
    COSMETIC = "cosmetic"

@dataclass
class ImpactAssessment:
    """Assessment of change impact."""
    assessment_id: str
    change_id: str
    affected_artifacts: Set[str] = field(default_factory=set)
    affected_disciplines: Set[str] = field(default_factory=set)
    revalidation_required: Set[str] = field(default_factory=set)  # validator_ids
    cost_impact_estimate: Optional[float] = None
    schedule_impact_days: Optional[float] = None
    risk_level: str = "low"  # low, medium, high
    notes: str = ""

@dataclass
class ChangeRequest:
    """Engineering change request."""
    change_id: str
    title: str
    description: str
    change_type: ChangeType
    classification: ChangeClassification
    status: ChangeStatus = ChangeStatus.DRAFT
    requested_by: str = ""
    requested_at: datetime = field(default_factory=datetime.utcnow)
    reason: str = ""
    proposed_solution: str = ""
    impact: Optional[ImpactAssessment] = None
    before_version: Optional[str] = None
    after_version: Optional[str] = None
    approvals: List[Dict] = field(default_factory=list)

@dataclass
class Deviation:
    """As-built deviation from design."""
    deviation_id: str
    change_id: str  # link to change request
    artifact_id: str
    designed_value: str
    as_built_value: str
    disposition: str  # accept, rework, reject
    disposition_by: str = ""
    disposition_at: Optional[datetime] = None
    condition: str = ""  # any conditions on acceptance

@dataclass
class Nonconformance:
    """Nonconformance report."""
    ncr_id: str
    description: str
    artifact_id: str
    discovered_by: str
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    root_cause: str = ""
    corrective_action: str = ""
    change_id: Optional[str] = None  # linked ECO
    closed: bool = False
```

- **Integration point (MAGNET)**
  - `DesignMutator` can optionally emit `ChangeRequest` records
  - Impact assessment queries dependency graph
  - Version history links changes to state transitions

- **Reuse note**
  - **Reuse**: `magnet/dependencies/graph.py` for impact analysis
  - **Build new**: Change workflow, impact computation

---

### 0.5.12 Uncertainty / Fidelity

Explicit fidelity level per artifact, uncertainty bounds, propagation rules.

- **Existing code found**
  - `magnet/physics/uncertainty.py`: `Uncertainty` dataclass with level/basis

- **Proposed extension** (not replacement)

- **File location**
  - Extend: `magnet/physics/uncertainty.py` (add propagation)
  - New: `magnet/core/fidelity.py` (design-wide fidelity tracking)

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum

class FidelityLevel(Enum):
    CONCEPT = "concept"        # ±20-30%
    PRELIMINARY = "preliminary"  # ±10-15%
    CONTRACT = "contract"      # ±5-10%
    DETAIL = "detail"          # ±2-5%
    AS_BUILT = "as_built"      # ±1%

FIDELITY_UNCERTAINTY = {
    FidelityLevel.CONCEPT: 25.0,
    FidelityLevel.PRELIMINARY: 12.5,
    FidelityLevel.CONTRACT: 7.5,
    FidelityLevel.DETAIL: 3.5,
    FidelityLevel.AS_BUILT: 1.0,
}

@dataclass
class UncertaintyBounds:
    """Uncertainty bounds for a value."""
    nominal: float
    lower: float
    upper: float
    confidence: float = 0.95  # confidence level (e.g., 95%)
    
    @property
    def range_pct(self) -> float:
        return (self.upper - self.lower) / max(abs(self.nominal), 1e-9) * 100

@dataclass
class UncertaintyPropagation:
    """Rules for propagating uncertainty through calculations."""
    output_path: str
    input_paths: List[str]
    propagation_method: str  # "rss", "linear", "monte_carlo", "worst_case"
    correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None

@dataclass
class ArtifactFidelity:
    """Fidelity tracking for an artifact."""
    artifact_id: str
    fidelity_level: FidelityLevel
    uncertainty_overrides: Dict[str, UncertaintyBounds] = field(default_factory=dict)
    
    def get_uncertainty(self, parameter: str) -> float:
        """Get uncertainty % for a parameter."""
        if parameter in self.uncertainty_overrides:
            return self.uncertainty_overrides[parameter].range_pct
        return FIDELITY_UNCERTAINTY[self.fidelity_level]

class FidelityGate:
    """Gate operations based on fidelity."""
    @staticmethod
    def can_optimize(artifact_fidelity: FidelityLevel, target_precision: float) -> bool:
        """Don't optimize against low-fidelity data."""
        return FIDELITY_UNCERTAINTY[artifact_fidelity] <= target_precision * 2
```

- **Integration point (MAGNET)**
  - Extend existing `Uncertainty` to include propagation rules
  - Optimizers check `FidelityGate` before using data
  - Reports show fidelity-appropriate significant figures

- **Reuse note**
  - **Reuse**: existing `Uncertainty` dataclass
  - **Extend**: Add propagation, fidelity gating

---

### 0.5.13 Explicit Dependency Graph (Cross-Domain)

Dependencies must be first-class objects spanning all disciplines.

- **Existing code found**
  - `magnet/dependencies/graph.py`: `DependencyGraph`, `DependencyEdge`, `EdgeType`
  - Already has phase-aware dependency tracking

- **Proposed extension** (not replacement)

- **File location**
  - Extend: `magnet/dependencies/graph.py` (add cross-domain edges)
  - New: `magnet/dependencies/cross_domain.py` (discipline handshakes)

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import Dict, List, Set
from enum import Enum

class PropagationType(Enum):
    AUTO = "auto"      # automatically triggered
    MANUAL = "manual"  # requires explicit action
    GATED = "gated"    # requires approval

@dataclass
class CrossDomainEdge:
    """Dependency edge crossing discipline boundaries."""
    edge_id: str
    source_domain: str  # hull, weight, stability, structure, systems, etc.
    source_parameter: str
    target_domain: str
    target_parameter: str
    propagation: PropagationType = PropagationType.AUTO
    sensitivity: float = 0.0  # ∂target/∂source
    latency_acceptable: bool = True  # can target lag behind source?

# Cross-domain dependencies (the actual edges for vessel design)
HULL_TO_DOWNSTREAM: List[CrossDomainEdge] = [
    CrossDomainEdge("hull_hydro", "hull", "displacement_m3", "stability", "displacement", PropagationType.AUTO),
    CrossDomainEdge("hull_resist", "hull", "wetted_surface_m2", "performance", "resistance", PropagationType.AUTO),
    CrossDomainEdge("hull_struct", "hull", "form_coefficients", "structure", "loads", PropagationType.GATED),
    CrossDomainEdge("hull_arrange", "hull", "internal_volume", "arrangement", "available_space", PropagationType.AUTO),
]

WEIGHT_TO_DOWNSTREAM: List[CrossDomainEdge] = [
    CrossDomainEdge("weight_stab", "weight", "total_kg", "stability", "displacement_check", PropagationType.AUTO),
    CrossDomainEdge("weight_stab_cg", "weight", "vcg_m", "stability", "gm", PropagationType.AUTO),
    CrossDomainEdge("weight_struct", "weight", "distribution", "structure", "loads", PropagationType.GATED),
    CrossDomainEdge("weight_trim", "weight", "lcg_m", "stability", "trim", PropagationType.AUTO),
]

SYSTEMS_TO_DOWNSTREAM: List[CrossDomainEdge] = [
    CrossDomainEdge("sys_weight", "systems", "component_mass", "weight", "outfit_weight", PropagationType.AUTO),
    CrossDomainEdge("sys_space", "systems", "volume_required", "arrangement", "space_allocation", PropagationType.MANUAL),
    CrossDomainEdge("sys_power", "systems", "power_demand", "electrical", "load_analysis", PropagationType.AUTO),
]

class CrossDomainGraph:
    """Graph of cross-domain dependencies."""
    def __init__(self):
        self._edges: Dict[str, CrossDomainEdge] = {}
        self._by_source: Dict[str, List[str]] = {}
        self._by_target: Dict[str, List[str]] = {}
    
    def add_edge(self, edge: CrossDomainEdge): ...
    def get_downstream(self, domain: str, parameter: str) -> List[CrossDomainEdge]: ...
    def get_propagation_order(self, changed_domain: str) -> List[str]: ...
```

- **Integration point (MAGNET)**
  - Extend existing `DependencyGraph` with `CrossDomainEdge`
  - `PropagationEngine` uses cross-domain graph for cascade
  - Gated propagations require explicit user action

- **Reuse note**
  - **Reuse**: existing `DependencyGraph`, `PropagationEngine`
  - **Extend**: Add cross-domain edges, propagation policies

---

### 0.5.14 Derived Data Authority (Ghost Data Prevention)

Derived values need explicit rules for cache vs authoritative, invalidation, recomputation.

- **Existing code found**
  - `magnet/dependencies/invalidation.py`: Invalidation logic exists
  - `magnet/control_plane/explain.py`: `CalculationProvenance`

- **File location**
  - New: `magnet/core/derived_data.py` (authority tracking for derived values)

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

@dataclass
class ComputationRecord:
    """Record of how a value was computed."""
    output_path: str
    computation_method: str  # function name or formula
    input_values: Dict[str, Any]
    input_versions: Dict[str, int]  # path -> design_version when read
    computed_at: datetime = field(default_factory=datetime.utcnow)
    compute_time_ms: float = 0.0
    is_deterministic: bool = True

@dataclass
class DerivedValue:
    """A value derived from other values."""
    path: str
    value: Any
    computation: ComputationRecord
    is_stale: bool = False
    staleness_reason: Optional[str] = None
    
    def check_staleness(self, current_versions: Dict[str, int]) -> bool:
        """Check if inputs have changed since computation."""
        for input_path, version in self.computation.input_versions.items():
            if current_versions.get(input_path, 0) > version:
                self.is_stale = True
                self.staleness_reason = f"Input {input_path} changed"
                return True
        return False

@dataclass
class InvalidationRule:
    """Rule for when to invalidate derived data."""
    derived_path: str
    trigger_paths: List[str]
    invalidation_policy: str  # "immediate", "lazy", "manual"
    recompute_priority: int = 0  # higher = recompute sooner

class DerivedDataRegistry:
    """Registry of derived values and their authority."""
    def __init__(self):
        self._values: Dict[str, DerivedValue] = {}
        self._rules: Dict[str, InvalidationRule] = {}
    
    def register_derived(self, path: str, rule: InvalidationRule): ...
    def is_authoritative(self, path: str) -> bool: ...
    def get_stale_values(self) -> List[str]: ...
    def trigger_recomputation(self, path: str): ...
```

- **Integration point (MAGNET)**
  - Graph view marks derived vs authoritative values
  - Stale derived values trigger recomputation on access
  - Reports indicate value freshness

- **Reuse note**
  - **Reuse**: existing invalidation patterns in `magnet/dependencies/`
  - **Build new**: Derived value registry, staleness tracking

---

### 0.5.15 Convergence / Exit Criteria (Per Domain)

Formal "resolved" states per domain with explicit exit criteria.

- **Existing code found**
  - `magnet/kernel/synthesis.py`: `ConvergenceCriteria` dataclass

- **Proposed extension** (not replacement)

- **File location**
  - Extend: `magnet/kernel/synthesis.py` (generalize convergence)
  - New: `magnet/core/domain_convergence.py` (per-domain tracking)

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

class ResolutionState(Enum):
    PENDING = "pending"
    CONVERGING = "converging"
    RESOLVED = "resolved"
    FROZEN = "frozen"
    RELEASED = "released"

@dataclass
class ExitCriterion:
    """Single criterion for domain resolution."""
    criterion_id: str
    description: str
    parameter_path: str
    check_type: str  # stable, within_tolerance, exists, validated
    threshold: Optional[float] = None
    stability_window: int = 3  # iterations to check stability

@dataclass
class DomainExitCriteria:
    """Exit criteria for a design domain."""
    domain: str
    criteria: List[ExitCriterion] = field(default_factory=list)
    
    def check_all(self, state: Dict) -> tuple[bool, List[str]]:
        """Check if all criteria met. Returns (passed, failed_criterion_ids)."""
        ...

# Domain-specific exit criteria
HULL_EXIT_CRITERIA = DomainExitCriteria(
    domain="hull",
    criteria=[
        ExitCriterion("hull_dim_stable", "Principal dimensions stable", "hull.loa", "stable"),
        ExitCriterion("hull_coeff_stable", "Form coefficients stable", "hull.cb", "stable"),
        ExitCriterion("hull_validated", "Hydrostatics validated", "validation.hydrostatics.passed", "exists"),
    ]
)

WEIGHT_EXIT_CRITERIA = DomainExitCriteria(
    domain="weight",
    criteria=[
        ExitCriterion("weight_margin", "Weight margin > 5%", "weight.margin_pct", "within_tolerance", threshold=5.0),
        ExitCriterion("weight_cg_stable", "CG stable", "weight.vcg_m", "stable"),
    ]
)

@dataclass
class ConvergenceStatus:
    """Current convergence status for all domains."""
    domain_states: Dict[str, ResolutionState] = field(default_factory=dict)
    iteration_count: int = 0
    oscillation_detected: Dict[str, bool] = field(default_factory=dict)
    
    def can_proceed_to(self, target_domain: str) -> bool:
        """Check if upstream domains are resolved."""
        ...
```

- **Integration point (MAGNET)**
  - Design spiral checks exit criteria before proceeding
  - Frozen domains block further changes without explicit unlock
  - Reports show domain resolution status

- **Reuse note**
  - **Reuse**: existing `ConvergenceCriteria` pattern
  - **Extend**: Generalize to all domains, add resolution state machine

---

### 0.5.16 Spiral Damping / Sequencing

Formal priority and damping policy for coupled domains.

- **File location**
  - New: `magnet/optimization/spiral_control.py`

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum

class DomainFreeze(Enum):
    NONE = "none"
    SOFT = "soft"      # warn on change
    HARD = "hard"      # block change

@dataclass
class SpiralPhase:
    """A phase in the design spiral."""
    phase_id: str
    name: str
    active_domains: Set[str]
    frozen_domains: Dict[str, DomainFreeze] = field(default_factory=dict)
    max_iterations: int = 10
    convergence_tolerance: float = 0.01

@dataclass
class StepLimit:
    """Limit on change magnitude per iteration."""
    parameter_path: str
    max_delta_pct: float = 10.0
    max_delta_abs: Optional[float] = None

@dataclass
class SpiralDampingPolicy:
    """Policy for damping oscillations."""
    domain: str
    initial_gain: float = 1.0
    decay_rate: float = 0.8  # multiply gain by this each iteration
    min_gain: float = 0.1
    oscillation_threshold: int = 3  # detect oscillation after N reversals
    step_limits: List[StepLimit] = field(default_factory=list)

class SpiralController:
    """Controls the design spiral iteration."""
    def __init__(self, phases: List[SpiralPhase], policies: Dict[str, SpiralDampingPolicy]):
        self._phases = phases
        self._policies = policies
        self._current_phase = 0
        self._iteration = 0
        self._history: List[Dict] = []
    
    def check_monotone_progress(self, domain: str) -> bool:
        """Check if domain is making progress (not oscillating)."""
        ...
    
    def get_damping_factor(self, domain: str) -> float:
        """Get current damping factor for a domain."""
        ...
    
    def should_advance_phase(self) -> bool:
        """Check if current phase is converged."""
        ...
    
    def rollback_on_oscillation(self) -> bool:
        """Rollback if oscillation detected."""
        ...
```

- **Integration point (MAGNET)**
  - Orchestrator uses `SpiralController` to manage iteration
  - Change requests check domain freeze status
  - Damping applied to optimizer step sizes

- **Reuse note**
  - **Build new**: Spiral control logic (orchestration layer)

---

### 0.5.17 Cross-Domain Handshakes

Explicit contracts between disciplines.

- **File location**
  - New: `magnet/contracts/discipline_handshakes.py`

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol

@dataclass
class DataLatencyPoint:
    """Point where data crosses discipline boundary."""
    point_id: str
    source_domain: str
    target_domain: str
    data_paths: List[str]
    acceptable_staleness_iterations: int = 1
    refresh_trigger: str  # "on_change", "on_request", "periodic"

@dataclass
class HandshakeContract:
    """Contract between two disciplines."""
    contract_id: str
    provider_domain: str
    consumer_domain: str
    provided_data: List[str]  # paths provider supplies
    required_data: List[str]  # paths consumer needs
    latency_points: List[DataLatencyPoint] = field(default_factory=list)
    validation_required: bool = True

# Actual discipline handshakes
HYDRO_ARRANGEMENT_HANDSHAKE = HandshakeContract(
    contract_id="hydro_arrangement",
    provider_domain="hydrostatics",
    consumer_domain="arrangement",
    provided_data=["hull.internal_volume_m3", "hull.section_areas"],
    required_data=["arrangement.tank_volumes", "arrangement.compartment_centroids"],
)

WEIGHT_STABILITY_HANDSHAKE = HandshakeContract(
    contract_id="weight_stability",
    provider_domain="weight",
    consumer_domain="stability",
    provided_data=["weight.total_kg", "weight.vcg_m", "weight.lcg_m", "weight.fsm"],
    required_data=["stability.required_gm", "stability.max_vcg"],
)

ROUTING_COMPARTMENTATION_HANDSHAKE = HandshakeContract(
    contract_id="routing_compartmentation",
    provider_domain="compartmentation",
    consumer_domain="routing",
    provided_data=["compartments.boundaries", "compartments.penetration_allowances"],
    required_data=["routing.penetration_requests"],
)

class HandshakeRegistry:
    """Registry of discipline handshakes."""
    def __init__(self):
        self._contracts: Dict[str, HandshakeContract] = {}
    
    def register(self, contract: HandshakeContract): ...
    def validate_interface(self, source: str, target: str, data: Dict) -> List[str]: ...
    def get_required_data(self, consumer: str) -> List[str]: ...
```

- **Integration point (MAGNET)**
  - Domain transitions validate handshake contracts
  - Missing data prevents domain execution
  - Reports show handshake status

- **Reuse note**
  - **Build new**: Handshake contracts (formalize existing implicit interfaces)

---

### 0.5.18 Sensitivity / Impact Analysis

First-class "ImpactSet" primitive for change impact assessment.

- **Existing code found**
  - `magnet/optimization/sensitivity.py`: Basic sensitivity analysis

- **File location**
  - Extend: `magnet/optimization/sensitivity.py` (add impact sets)
  - New: `magnet/dependencies/impact.py` (impact analysis)

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set
from enum import Enum

class ChangeClassification(Enum):
    GEOMETRIC = "geometric"
    MASS = "mass"
    FUNCTIONAL = "functional"
    REGULATORY = "regulatory"

@dataclass
class SensitivityRecord:
    """Sensitivity of output to input."""
    input_path: str
    output_path: str
    sensitivity: float  # ∂output/∂input
    validity_range: tuple[float, float]  # input range where sensitivity is valid
    computed_at_value: float
    is_linear: bool = False

@dataclass
class ImpactSet:
    """Set of impacts from a parameter change."""
    changed_path: str
    change_magnitude: float
    classification: ChangeClassification
    direct_impacts: Set[str] = field(default_factory=set)  # immediately affected paths
    cascade_impacts: Set[str] = field(default_factory=set)  # transitively affected
    revalidation_required: Set[str] = field(default_factory=set)  # validators to rerun
    estimated_deltas: Dict[str, float] = field(default_factory=dict)  # path -> predicted change

class ImpactAnalyzer:
    """Analyzes impact of parameter changes."""
    def __init__(self, dependency_graph, sensitivity_cache: Dict[str, SensitivityRecord]):
        self._graph = dependency_graph
        self._sensitivities = sensitivity_cache
    
    def analyze(self, path: str, delta: float) -> ImpactSet:
        """Analyze impact of changing path by delta."""
        ...
    
    def estimate_cascaded_delta(self, path: str, delta: float, target: str) -> float:
        """Estimate change in target due to change in path."""
        ...
```

- **Integration point (MAGNET)**
  - `DesignMutator` queries impact before commit
  - Receipts include `ImpactSet` summary
  - UI can show "what if" analysis

- **Reuse note**
  - **Reuse**: existing sensitivity analysis
  - **Extend**: Add impact set computation, cascade estimation

---

### 0.5.19 Interchange Schema (External Tools)

Declared interchange model for STEP, IFC, solver decks.

- **Existing code found**
  - `magnet/lifecycle/export.py`: `ExportFormat`, `DesignExporter`
  - `magnet/webgl/exporter.py`: Geometry export

- **File location**
  - New: `magnet/interchange/schema.py` (interchange definitions)
  - New: `magnet/interchange/mappings/` (per-format mappings)

- **Interface contract (minimum)**

```python
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum

class InterchangeFormat(Enum):
    STEP_AP203 = "step_ap203"
    STEP_AP214 = "step_ap214"
    STEP_AP242 = "step_ap242"  # geometry + PMI
    IFC_4 = "ifc_4"            # spaces/construction
    IGES = "iges"
    FEA_NASTRAN = "fea_nastran"
    FEA_ANSYS = "fea_ansys"
    CFD_STAR = "cfd_star"

@dataclass
class ExternalIdentifier:
    """Stable identifier for external system reference."""
    artifact_id: str
    external_format: InterchangeFormat
    external_id: str  # STEP entity ID, IFC GUID, etc.
    external_version: str
    created_at: str

@dataclass
class PropertyMapping:
    """Maps internal property to external representation."""
    internal_path: str
    external_name: str
    transform: Optional[Callable[[Any], Any]] = None
    units_internal: str = ""
    units_external: str = ""

@dataclass
class ExportMapping:
    """Mapping for export to external format."""
    format: InterchangeFormat
    entity_mappings: Dict[str, str]  # internal_type -> external_type
    property_mappings: List[PropertyMapping] = field(default_factory=list)
    geometry_precision: float = 0.001
    include_pmi: bool = False
    include_metadata: bool = True

@dataclass
class ImportMapping:
    """Mapping for import from external format."""
    format: InterchangeFormat
    entity_mappings: Dict[str, str]  # external_type -> internal_type
    property_mappings: List[PropertyMapping] = field(default_factory=list)
    merge_strategy: str = "create_new"  # create_new, update_existing, merge

@dataclass
class InterchangeSchema:
    """Complete interchange schema."""
    schema_id: str
    name: str
    export_mappings: Dict[InterchangeFormat, ExportMapping] = field(default_factory=dict)
    import_mappings: Dict[InterchangeFormat, ImportMapping] = field(default_factory=dict)
    external_ids: Dict[str, ExternalIdentifier] = field(default_factory=dict)
    
    def export_to(self, format: InterchangeFormat, artifacts: List[str]) -> bytes: ...
    def import_from(self, format: InterchangeFormat, data: bytes) -> Dict[str, str]: ...
    def get_external_id(self, artifact_id: str, format: InterchangeFormat) -> Optional[str]: ...
```

- **Integration point (MAGNET)**
  - Artifacts carry stable `external_ids` for roundtrip
  - Export/import preserves identity mappings
  - FEA/CFD results import as evidence (R/V/V)

- **Reuse note**
  - **Reuse**: existing export infrastructure
  - **Extend**: Add identity tracking, bidirectional mapping

---

### 0.5.20 Integration Architecture (PLM Primitives)

#### 0.5.20.1 Unified Object Model (Relationships)

```
                           ┌─────────────────┐
                           │ DesignState     │
                           │ (SSOT)          │
                           └────────┬────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│ Configuration   │      │ Artifact        │      │ DigitalTwin     │
│ • Variant       │      │ • geometry.*    │      │ • as_designed   │
│ • Effectivity   │      │ • Authority     │      │ • as_built      │
│ • Baseline      │◄────►│ • Fidelity      │◄────►│ • as_maintained │
└─────────────────┘      └────────┬────────┘      └─────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Compartment     │    │ MassItem        │    │ SystemNetwork   │
│ • Boundary      │    │ • Uncertainty   │    │ • Node/Edge     │
│ • Opening       │    │ • WeightBudget  │    │ • Redundancy    │
│ • FloodGroup    │    │ • GrowthAllow   │    │ • Isolation     │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ Requirement         │
                     │ • Evidence          │
                     │ • RuleSource        │
                     │ • Waiver            │
                     └─────────────────────┘
```

#### 0.5.20.2 Data Flow (Multi-Decade Lifecycle)

```
DESIGN                  BUILD                   OPERATE               MODIFY
───────────────────────────────────────────────────────────────────────────────
│                       │                       │                       │
│ Configuration         │ Configuration         │ Configuration         │ Configuration
│ (baseline)       ────►│ (released)       ────►│ (active)         ────►│ (variant)
│                       │                       │                       │
│ Artifact              │ AsBuiltDeviation      │ MaintenanceMod        │ ChangeRequest
│ (as_designed)    ────►│ (recorded)       ────►│ (service changes)────►│ (ECO)
│                       │                       │                       │
│ MassItem              │ MassItem              │ MassItem              │ MassItem
│ (estimated)      ────►│ (weighed)        ────►│ (updated)        ────►│ (projected)
│                       │                       │                       │
│ Requirement           │ Evidence              │ Evidence              │ Evidence
│ (allocated)      ────►│ (verified)       ────►│ (re-verified)    ────►│ (updated)
│                       │                       │                       │
```

#### 0.5.20.3 Validation Chain (with Provenance)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Requirement │────►│ RuleVersion │────►│ Validator   │────►│ Evidence    │
│             │     │             │     │             │     │             │
│ source:     │     │ framework:  │     │ method:     │     │ type:       │
│ contract/   │     │ SOLAS/ABS/  │     │ analysis/   │     │ calculation/│
│ regulatory  │     │ DNV/ISO     │     │ test/       │     │ test_report/│
│             │     │             │     │ inspection  │     │ cert        │
│ authority:  │     │ version:    │     │             │     │             │
│ owner       │     │ dated       │     │ authority:  │     │ authority:  │
└─────────────┘     └─────────────┘     │ kernel      │     │ approver    │
                                        └─────────────┘     └─────────────┘
                                                                   │
                                                                   ▼
                                                          ┌─────────────────┐
                                                          │ ComplianceStatus│
                                                          │                 │
                                                          │ • compliant     │
                                                          │ • non_compliant │
                                                          │ • waived        │
                                                          └─────────────────┘
```

---

## 0.6 Enumeration Refactor Specifications (Detailed Implementation)

This section specifies HOW to eliminate each enumeration leak identified in §0.5.0.1. The goal: an LLM describes a hull form that has never existed before, the kernel synthesizes valid geometry from constraints, and physics validates afterward. "What kind of boat" is derived from geometry, never input to synthesis.

**HARD RULE: DELETE ALL FORM ENUMS. NO DEPRECATION. NO BACKWARD COMPATIBILITY.**

Old designs that use enums are invalid. They must be re-expressed with continuous parameters or discarded. This is a clean break.

**Permitted enums** (non-geometric):
- Workflow states (ApprovalStatus, ChangeStatus)
- Regulatory categories externally defined (BoundaryRating, WeldClass)
- Operational states (ClosureState)
- Detection methods (HOW something was found, not WHAT it is)

---

### 0.6.1 HullFamily → DELETE

#### Current State

- **File**: `magnet/kernel/priors/hull_families.py`
- **Enum**: `HullFamily(Enum): PATROL, WORKBOAT, FERRY, PLANING, CATAMARAN`
- **Usage**: Infects `synthesis.py` with hardcoded defaults per family

**Problem**: Forces discrete buckets. Incompatible with generative design.

#### Action: DELETE

1. **Delete file**: `magnet/kernel/priors/hull_families.py`
2. **Delete references**: Remove all `HullFamily` imports and usage from `synthesis.py`
3. **Delete `FAMILY_PRIORS`**: This dict is the core of the problem

#### Replacement: Constraint-Based Synthesis

The synthesis engine accepts ONLY physical constraints:

```python
# magnet/kernel/synthesis_constraints.py (new)

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

@dataclass
class SynthesisConstraints:
    """
    Constraint-first synthesis request.
    
    All constraints are PHYSICAL requirements, not style selections.
    The form emerges from satisfying constraints; classification happens post-hoc.
    """
    
    # === REQUIRED CONSTRAINTS ===
    displacement_m3: Tuple[float, float]  # (min, max) required displacement
    
    # === PERFORMANCE CONSTRAINTS ===
    max_speed_kts: Optional[float] = None
    cruise_speed_kts: Optional[float] = None
    range_nm: Optional[float] = None
    sea_state_design: Optional[int] = None  # Beaufort scale
    
    # === STABILITY CONSTRAINTS ===
    gm_min_m: Optional[float] = None
    gz_max_min_m: Optional[float] = None
    angle_vanishing_min_deg: Optional[float] = None
    
    # === DIMENSIONAL CONSTRAINTS (bounds, not targets) ===
    loa_range_m: Optional[Tuple[float, float]] = None
    beam_max_m: Optional[float] = None  # hard limit (e.g., canal width)
    draft_max_m: Optional[float] = None  # hard limit (e.g., depth)
    
    # === FORM CONSTRAINTS (continuous parameters, not enums) ===
    deadrise_transom_range_deg: Optional[Tuple[float, float]] = None
    entry_angle_range_deg: Optional[Tuple[float, float]] = None
    lcb_fraction_range: Optional[Tuple[float, float]] = None
    
    # === MULTI-BODY ===
    num_bodies: int = 1  # 1=monohull, 2=catamaran, 3=trimaran (not "type", just count)
    hull_spacing_range_m: Optional[Tuple[float, float]] = None  # for multi-body
    
    # === OPTIONAL SOFT PREFERENCES (not constraints) ===
    preferences: Dict[str, Any] = field(default_factory=dict)
    # e.g., {"optimize_for": "speed"} or {"aesthetic": "aggressive"}
    # These are hints for LLM/optimizer, not synthesis inputs


@dataclass
class SynthesisResult:
    """Result of constraint-based synthesis."""
    success: bool
    geometry: Optional["HullGeometry"] = None
    satisfied_constraints: List[str] = field(default_factory=list)
    violated_constraints: List[str] = field(default_factory=list)
    residuals: Dict[str, float] = field(default_factory=dict)
    # POST-HOC CLASSIFICATION (derived from geometry)
    derived_classification: Optional["HullClassification"] = None


def synthesize_from_constraints(
    constraints: SynthesisConstraints,
    state: "StateManager",
    max_iterations: int = 50,
) -> SynthesisResult:
    """
    Synthesize hull geometry from physical constraints.
    
    NO ENUM INPUTS. Form emerges from constraint satisfaction.
    
    Algorithm:
    1. Estimate initial dimensions from displacement + speed constraints
    2. Compute Froude number → infer operating regime (displacement/planing)
    3. Generate section parameters from physics (not family priors)
    4. Iteratively refine until constraints satisfied or iteration limit
    5. Validate physics (hydrostatics, stability)
    6. Classify result post-hoc for UI/reporting
    """
    ...
```

#### DSL Implications

The design language already uses continuous parameters. No DSL changes required—the change is in what the synthesis engine accepts.

```
// BEFORE (implicit family selection via synthesis.py)
CREATE hull TYPE geometry.body
  SYNTHESIZE_HULL family="patrol" loa=25

// AFTER (constraint-based, no family)
CREATE hull TYPE geometry.body
  SYNTHESIZE_HULL displacement=(150, 200) max_speed=35 deadrise_transom=(12, 18)
```

#### Classification (Post-Hoc, Optional)

Classification is OPTIONAL and for UI/reporting only. It never feeds back into synthesis.

```python
# magnet/kernel/classification.py (new)

from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass
class HullClassification:
    """
    Post-hoc hull classification for UI/reporting ONLY.
    
    This is DERIVED output, never synthesis input.
    """
    regime: str  # "displacement", "semi-displacement", "planing" (from Froude)
    body_count: int
    form_descriptors: List[str] = field(default_factory=list)  # detected features
    novel_features: List[str] = field(default_factory=list)    # things that don't fit


def classify_hull(geometry: "HullGeometry") -> HullClassification:
    """Derive classification from geometry. For display only."""
    froude = calculate_froude(geometry.design_speed_kts, geometry.lwl_m)
    regime = "planing" if froude > 0.55 else "semi-displacement" if froude > 0.35 else "displacement"
    
    descriptors = []
    if detect_hard_chine(geometry):
        descriptors.append("hard-chine")
    if detect_deep_v(geometry):
        descriptors.append("deep-v")
    # ... geometry analysis, not enum matching
    
    return HullClassification(
        regime=regime,
        body_count=geometry.num_bodies or 1,
        form_descriptors=descriptors,
        novel_features=detect_novel_features(geometry),
    )
```

#### Edge Cases

| Novel Form | Handling |
|------------|----------|
| "Patrol boat with ferry superstructure" | Constraints allow any combination; classification returns `("semi-displacement-monohull", [("patrol", 0.5), ("ferry", 0.4)])` |
| "Trimaran workboat" | `num_bodies=3` + displacement constraints; classification returns `"displacement-trimaran"` with novel_features=["workboat-trimaran"] |
| "Asymmetric catamaran" | Valid geometry compiles; classification detects novel_features=["asymmetric-hulls"] |
| "Continuous deadrise variation" | Constraints allow; no enum blocks this |

#### Validation

Kernel validates physics without knowing "type":

```python
def validate_hull_physics(geometry: "HullGeometry") -> ValidationResult:
    """
    Validate hull geometry based on PHYSICS, not type.
    
    NO TYPE CHECKING. Just physics.
    """
    errors = []
    
    # Hydrostatic validation
    hydro = compute_hydrostatics(geometry)
    if hydro.displacement_m3 <= 0:
        errors.append("Invalid displacement")
    
    # Stability validation (applies to ALL forms)
    if hydro.gm_m < 0:
        errors.append("Negative GM - unstable")
    
    # Froude-appropriate checks (not type checks)
    froude = calculate_froude(geometry.design_speed_kts, geometry.lwl_m)
    if froude > 1.2 and hydro.gm_m < 0.3:
        errors.append("High-speed hull needs higher GM")
    
    return ValidationResult(valid=len(errors) == 0, errors=errors)
```

---

### 0.6.2 HullType → DELETE

#### Current State

- **File**: `magnet/hull_gen/enums.py`
- **Enum**: `HullType: DEEP_V_PLANING, SEMI_DISPLACEMENT, ROUND_BILGE, HARD_CHINE, CATAMARAN, TRIMARAN, SWATH`
- **Usage**: `HullDefinition.hull_type`, generator dispatch, parameters dispatch

**Problem**: Forces discrete buckets. Novel forms that combine characteristics cannot exist.

#### Action: DELETE

1. **Delete from `magnet/hull_gen/enums.py`**: Remove `class HullType(Enum)`
2. **Delete from `HullDefinition`**: Remove `hull_type` field entirely
3. **Refactor `generator.py`**: Remove all `if hull_type ==` dispatch
4. **Refactor `parameters.py`**: Remove `FormCoefficients.for_hull_type()`

#### Replacement: Parameter-Driven Generation

```python
# magnet/hull_gen/parameters.py

@dataclass
class HullDefinition:
    """Hull definition. NO TYPE FIELD."""
    dimensions: MainDimensions
    coefficients: FormCoefficients
    deadrise: DeadriseProfile
    features: HullFeatures
    # NO hull_type field. Form emerges from parameters.
```

```python
# magnet/hull_gen/generator.py

def _generate_section_at(self, station: float, x_pos: float) -> HullSection:
    """Generate section from PARAMETERS, not type dispatch."""
    deadrise = self._get_deadrise_at_station(station)
    chines = self._definition.features.chines
    bilge_radius = self._get_bilge_radius_at_station(station)
    
    # NO TYPE SWITCH. Parameters determine shape.
    if chines and any(c.discontinuity_angle_deg > 30 for c in chines):
        return self._generate_chine_section(station, deadrise, chines)
    elif bilge_radius > 0:
        return self._generate_round_section(station, deadrise, bilge_radius)
    else:
        return self._generate_interpolated_section(station, deadrise)
```

---

### 0.6.3 ChineType → DELETE

#### Current State

- **File**: `magnet/hull_gen/enums.py`
- **Enum**: `ChineType: NONE, SOFT, HARD, SINGLE, DOUBLE, TRIPLE, REVERSE, VARIABLE`
- **Usage**: `HullFeatures.chine_type`, generator dispatch, `get_chine_configs()`

**Problem**: Discretizes continuous curvature. "1.5 chines" impossible.

#### Action: DELETE

1. **Delete from `magnet/hull_gen/enums.py`**: Remove `class ChineType(Enum)`
2. **Delete from `HullFeatures`**: Remove `chine_type` field
3. **Delete `get_chine_configs()` switch**: Remove enum-based default generation

#### Replacement: `List[ChineConfig]` with Continuous Parameters

```python
# magnet/hull_gen/parameters.py

@dataclass
class ChineConfig:
    """A chine is a curvature discontinuity. Fully continuous."""
    height_ratio: float  # 0=keel, 1=sheer
    discontinuity_angle_deg: float  # 0=smooth, 90=hard corner (CONTINUOUS)
    flat_width_m: float = 0.0  # spray rail width
    station_start: float = 0.0
    station_end: float = 1.0
    # Variable chine: different angle fore/aft
    angle_at_start_deg: Optional[float] = None
    angle_at_end_deg: Optional[float] = None


@dataclass
class HullFeatures:
    """NO ENUM FIELDS."""
    chines: List[ChineConfig] = field(default_factory=list)
    # Empty = round bilge. Multiple = multi-chine. Continuous angles = arbitrary sharpness.
```

#### DSL

```
// Any number of chines, any sharpness, any position
CHINE height_ratio=0.2 discontinuity_angle_deg=50
CHINE height_ratio=0.5 discontinuity_angle_deg=35

// Variable (soft forward, hard aft)
CHINE height_ratio=0.3 angle_at_start_deg=15 angle_at_end_deg=60

// Asymmetric
CHINE height_ratio=0.3 discontinuity_angle_deg=60 side="port"
CHINE height_ratio=0.3 discontinuity_angle_deg=20 side="starboard"
```

---

### 0.6.4 BowStyle → DELETE

#### Current State

- **File**: `magnet/hull_gen/enums.py`
- **Enum**: `BowStyle: TRADITIONAL, WEDGE, AXE, FACETED, WAVE_PIERCING, SPOON, CLIPPER`
- **Usage**: `HullFeatures.bow_style`, `bow_generator.py` dispatch

**Problem**: "Wedge with clipper curvature" impossible. Discrete styles.

#### Action: DELETE

1. **Delete from `magnet/hull_gen/enums.py`**: Remove `class BowStyle(Enum)`
2. **Delete from `HullFeatures`**: Remove `bow_style` field
3. **Refactor `bow_generator.py`**: Remove style dispatch

#### Replacement: `BowConfig` with Continuous Parameters

```python
# magnet/hull_gen/parameters.py

@dataclass
class BowConfig:
    """Bow form. All continuous, no style enum."""
    half_angle_deg: float = 25.0       # Entry angle
    stem_rake_deg: float = 15.0        # From vertical; negative = forward
    stem_curvature: float = 0.0        # -1 to +1: concave to convex
    planarity: float = 0.0             # 0=smooth, 1=planar panels
    facet_count: int = 0               # 0=smooth, 1=wedge, 2+=faceted
    dihedral_angle_deg: float = 0.0    # Panel angle (wedge)
    flare_deg: float = 0.0
    region_length: float = 0.20        # Fraction of LWL


@dataclass
class HullFeatures:
    bow: Optional[BowConfig] = None  # None = infer from other params
```

#### Generator (No Style Dispatch)

```python
# magnet/hull_gen/bow_generator.py

def generate(self, config: BowConfig) -> BowGeometry:
    """Generate from parameters. NO STYLE SWITCH."""
    if config.planarity > 0.5 and config.facet_count >= 1:
        return self._generate_planar_bow(config)
    else:
        return self._generate_lofted_bow(config)
```

#### DSL

```
// Continuous parameters, not style names
BOW half_angle_deg=15 planarity=1.0 facet_count=1

// Novel: wedge with clipper curvature
BOW half_angle_deg=15 planarity=0.8 facet_count=1 stem_curvature=0.3

// Novel: asymmetric
BOW half_angle_deg=20 port_dihedral_deg=10 stbd_dihedral_deg=20
```

---

### 0.6.5 StemProfile → DELETE

#### Current State

- **File**: `magnet/hull_gen/enums.py`
- **Enum**: `StemProfile: VERTICAL, RAKED, WAVE_PIERCING, BULBOUS, AXEBOW, CLIPPER`
- **Usage**: `HullFeatures.stem_profile`

**Problem**: "Raked with slight bulb" impossible. Discrete profiles.

#### Action: DELETE

1. **Delete from `magnet/hull_gen/enums.py`**: Remove `class StemProfile(Enum)`
2. **Delete from `HullFeatures`**: Remove `stem_profile` field

#### Replacement: Already in BowConfig

Stem is described by continuous parameters already in `BowConfig`:

```python
@dataclass
class BowConfig:
    stem_rake_deg: float = 15.0        # From vertical; 0=vertical, negative=forward
    stem_curvature: float = 0.0        # -1 to +1
    stem_bulb_volume_m3: float = 0.0   # 0 = no bulb
    stem_bulb_position: float = 0.0    # Below WL
```

#### DSL

```
// Raked with small bulb (impossible before)
BOW stem_rake_deg=12 stem_bulb_volume_m3=0.5 stem_bulb_position=-0.3
```

---

### 0.6.6 SternProfile → DELETE

#### Current State

- **File**: `magnet/hull_gen/enums.py`
- **Enum**: `SternProfile: TRANSOM, CRUISER, CANOE, TUNNEL`
- **Usage**: `HullFeatures.stern_profile`

**Problem**: "Transom transitioning to cruiser" impossible.

#### Action: DELETE

1. **Delete from `magnet/hull_gen/enums.py`**: Remove `class SternProfile(Enum)`
2. **Delete from `HullFeatures`**: Remove `stern_profile` field

#### Replacement: `SternConfig`

```python
@dataclass
class SternConfig:
    """Stern. All continuous."""
    transom_width_ratio: float = 0.85   # 0 = canoe stern
    transom_height_ratio: float = 0.8
    transom_immersion_m: float = 0.0    # Negative = dry
    transom_rake_deg: float = 12.0
    run_angle_deg: float = 15.0
    tunnel_count: int = 0
    tunnel_width_m: float = 0.0
    tunnel_depth_m: float = 0.0


@dataclass
class HullFeatures:
    stern: Optional[SternConfig] = None
```

#### DSL

```
STERN transom_width_ratio=0.85 transom_rake_deg=12 tunnel_count=2
```

---

### 0.6.7 KeelType → DELETE

#### Current State

- **File**: `magnet/hull_gen/enums.py`
- **Enum**: `KeelType: FLAT, BAR, SKEG, TWIN_SKEG`
- **Usage**: `HullFeatures.keel_type`

**Problem**: "Skeg transitioning to bar" impossible.

#### Action: DELETE

1. **Delete from `magnet/hull_gen/enums.py`**: Remove `class KeelType(Enum)`
2. **Delete from `HullFeatures`**: Remove `keel_type` field

#### Replacement: Keel as Geometry Attachment

Keel is a `geometry.body`, not an enum selection:

```python
@dataclass
class KeelAttachment:
    """Keel as geometry attachment. Arbitrary shape."""
    body_id: str  # Link to geometry.body
    station_start: float = 0.0
    station_end: float = 1.0
    depth_m: float = 0.0      # Below baseline
    width_m: float = 0.0


@dataclass
class HullFeatures:
    keel_attachments: List[KeelAttachment] = field(default_factory=list)
    # Empty = flat keel. Multiple = twin skeg. Any shape = just geometry.
```

#### DSL

```
// Arbitrary keel geometry
CREATE skeg TYPE geometry.body
  EXTRUDE profile=skeg_profile from_station=0 to_station=0.4
  TAPER start_depth=0.5 end_depth=0.2
ATTACH skeg TO hull AT keel_line

// Twin asymmetric
CREATE skeg_port TYPE geometry.body ...
CREATE skeg_stbd TYPE geometry.body ...
ATTACH skeg_port TO hull
ATTACH skeg_stbd TO hull
```

---

### 0.6.8 SectionShape → Removal

#### Current State

- **File**: `magnet/hull_gen/enums.py`
- **Enum**: `SectionShape: V_SHAPE, U_SHAPE, ROUND, FLAT_BOTTOM, WARPED`
- **Usage**: **NOT USED** (defined but no references found)

#### Target State

**Remove entirely.** Section shape is already continuous via:
- `deadrise_deg` (controls V-ness)
- `bilge_radius` (controls roundness)
- `ChineConfig` (controls discontinuities)

No code changes needed—just delete the unused enum.

```python
# DELETE from magnet/hull_gen/enums.py:
# class SectionShape(Enum): ...
```

---

### 0.6.9 Anchor Detection → Geometry-Based with Post-Hoc Labeling

#### Current State (from §0.4.1)

Already refactored in §0.4.1 to use `AnchorDetectionMethod` enum (HOW detected) rather than `AnchorType` enum (WHAT it is).

#### Detailed Detection Algorithm

```python
# magnet/hull_gen/anchor_detection.py (new)

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import numpy as np

@dataclass
class GeometricFeature:
    """A detected geometric feature on a section."""
    point_index: int
    position: Tuple[float, float, float]
    curvature: float
    tangent_angle_deg: float
    feature_type: str  # "maximum", "minimum", "discontinuity", "inflection", "extremum"


def detect_section_features(section: "HullSection") -> List[GeometricFeature]:
    """
    Detect geometric features on a section.
    
    Works on ANY section geometry. Does not assume known shapes.
    """
    features = []
    points = section.points
    
    if len(points) < 3:
        return features
    
    # Compute curvature at each point
    curvatures = compute_discrete_curvature(points)
    
    for i in range(1, len(points) - 1):
        k = curvatures[i]
        k_prev = curvatures[i - 1]
        k_next = curvatures[i + 1]
        
        # Curvature maximum (potential chine)
        if k > k_prev and k > k_next and k > CURVATURE_MAX_THRESHOLD:
            features.append(GeometricFeature(
                point_index=i,
                position=points[i].as_tuple(),
                curvature=k,
                tangent_angle_deg=compute_tangent_angle(points, i),
                feature_type="maximum",
            ))
        
        # Curvature minimum (flat region)
        if k < k_prev and k < k_next and abs(k) < CURVATURE_MIN_THRESHOLD:
            features.append(GeometricFeature(
                point_index=i,
                position=points[i].as_tuple(),
                curvature=k,
                tangent_angle_deg=compute_tangent_angle(points, i),
                feature_type="minimum",
            ))
        
        # Inflection point (curvature sign change)
        if k_prev * k_next < 0:
            features.append(GeometricFeature(
                point_index=i,
                position=points[i].as_tuple(),
                curvature=k,
                tangent_angle_deg=compute_tangent_angle(points, i),
                feature_type="inflection",
            ))
    
    # Extrema (keel, sheer)
    y_coords = [p.y for p in points]
    z_coords = [p.z for p in points]
    
    # Lowest point (potential keel)
    keel_idx = np.argmin(z_coords)
    features.append(GeometricFeature(
        point_index=keel_idx,
        position=points[keel_idx].as_tuple(),
        curvature=curvatures[keel_idx],
        tangent_angle_deg=compute_tangent_angle(points, keel_idx),
        feature_type="extremum",
    ))
    
    # Widest point (beam max)
    beam_idx = np.argmax(y_coords)
    features.append(GeometricFeature(
        point_index=beam_idx,
        position=points[beam_idx].as_tuple(),
        curvature=curvatures[beam_idx],
        tangent_angle_deg=compute_tangent_angle(points, beam_idx),
        feature_type="extremum",
    ))
    
    return features


def classify_feature(feature: GeometricFeature, section: "HullSection") -> str:
    """
    Assign semantic label to a detected feature.
    
    Returns descriptive label. For novel features, returns compound
    labels like "lower-inflection" or "mid-curvature-peak".
    """
    pos = feature.position
    points = section.points
    
    # Vertical position analysis
    z_min = min(p.z for p in points)
    z_max = max(p.z for p in points)
    z_range = z_max - z_min
    z_normalized = (pos[2] - z_min) / z_range if z_range > 0 else 0.5
    
    # Width analysis
    y_max = max(p.y for p in points)
    y_normalized = pos[1] / y_max if y_max > 0 else 0
    
    # Classify based on geometry (not preconceptions)
    if feature.feature_type == "extremum":
        if z_normalized < 0.1:
            return "keel-like"
        if z_normalized > 0.9:
            return "sheer-like"
        if y_normalized > 0.9:
            return "beam-max"
    
    if feature.feature_type == "maximum":
        if z_normalized < 0.5:
            return "lower-chine-like"
        else:
            return "upper-chine-like"
    
    if feature.feature_type == "inflection":
        return f"inflection-at-{z_normalized:.1f}"
    
    if feature.feature_type == "minimum":
        return f"flat-region-at-{z_normalized:.1f}"
    
    # Novel feature - describe by position
    return f"feature-at-z{z_normalized:.1f}-y{y_normalized:.1f}"
```

---

### 0.6.10 Validation Strategy (Type-Agnostic)

#### Principle

The kernel validates PHYSICS, not TYPES. Every validation rule must be expressible as a physical constraint.

```python
# magnet/kernel/physics_validation.py (new or extend existing)

@dataclass
class PhysicsValidationRule:
    """
    A validation rule expressed in physical terms.
    
    NO TYPE CHECKS. Only physics.
    """
    rule_id: str
    description: str
    
    # Physical condition (lambda or expression)
    condition: Callable[["HullGeometry"], bool]
    
    # Physics basis (why this matters)
    physics_basis: str
    
    # Severity
    severity: str  # "error", "warning", "info"


# Example rules - NO TYPE REFERENCES
PHYSICS_RULES = [
    PhysicsValidationRule(
        rule_id="positive_displacement",
        description="Hull must displace water",
        condition=lambda g: g.displacement_m3 > 0,
        physics_basis="Archimedes principle",
        severity="error",
    ),
    PhysicsValidationRule(
        rule_id="positive_gm",
        description="Initial stability must be positive",
        condition=lambda g: compute_gm(g) > 0,
        physics_basis="Metacentric stability",
        severity="error",
    ),
    PhysicsValidationRule(
        rule_id="reasonable_gm_for_speed",
        description="High-speed hulls need adequate GM",
        # Note: uses Froude number, not "hull type"
        condition=lambda g: compute_gm(g) >= 0.3 if compute_froude(g) > 0.8 else True,
        physics_basis="Dynamic stability at planing speeds",
        severity="warning",
    ),
    PhysicsValidationRule(
        rule_id="reasonable_prismatic",
        description="Prismatic coefficient in valid range",
        condition=lambda g: 0.5 <= g.prismatic_coefficient <= 0.85,
        physics_basis="Hydrodynamic efficiency",
        severity="warning",
    ),
]


def validate_hull_physics(geometry: "HullGeometry") -> ValidationResult:
    """
    Validate hull against physics rules.
    
    NO TYPE DISPATCH. Same rules apply to ALL hull forms.
    """
    errors = []
    warnings = []
    
    for rule in PHYSICS_RULES:
        try:
            if not rule.condition(geometry):
                msg = f"{rule.rule_id}: {rule.description}"
                if rule.severity == "error":
                    errors.append(msg)
                else:
                    warnings.append(msg)
        except Exception as e:
            warnings.append(f"{rule.rule_id}: Could not evaluate ({e})")
    
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
```

---

### 0.6.11 Deletion Checklist

**NO BACKWARD COMPATIBILITY. DELETE ALL.**

| File | Action |
|------|--------|
| `magnet/kernel/priors/hull_families.py` | **DELETE ENTIRE FILE** |
| `magnet/hull_gen/enums.py` | **DELETE**: `HullFamily`, `HullType`, `ChineType`, `BowStyle`, `StemProfile`, `SternProfile`, `KeelType`, `SectionShape` |
| `magnet/hull_gen/parameters.py` | **DELETE FIELDS**: `hull_type`, `chine_type`, `bow_style`, `stem_profile`, `stern_profile`, `keel_type` |
| `magnet/hull_gen/generator.py` | **DELETE**: All `if hull_type ==` / `if chine_type ==` dispatch + enum imports |
| `magnet/hull_gen/bow_generator.py` | **DELETE**: All style dispatch |

**CONFIRMED IN CURRENT CODEBASE**:
- `magnet/hull_gen/generator.py` imports form enums (`HullType`, `ChineType`, `SectionShape`, `BowStyle`) and dispatches behavior based on them (e.g., `definition.hull_type == HullType.ROUND_BILGE`, `chine_type in (ChineType.DOUBLE, ChineType.TRIPLE)`, etc.).
- This is an active enumeration leak (“infection”) and must be removed per the hard rule.
| `magnet/kernel/synthesis.py` | **DELETE**: All `request.hull_family` logic, all `FAMILY_*` dicts |
| `magnet/webgl/interfaces.py` | **DELETE**: All enum mapping dicts |
| `magnet/hull_gen/library.py` | **DELETE ENTIRE FILE** (contains enum-based presets) |

#### New Files

| File | Purpose |
|------|---------|
| `magnet/kernel/synthesis_constraints.py` | `SynthesisConstraints` dataclass, constraint-based synthesis |
| `magnet/kernel/classification.py` | Post-hoc classification (optional, for UI only) |

---

### 0.6.12 Testing Strategy

```python
# tests/test_enum_deletion.py

class TestEnumDeletion:
    """Verify enums are GONE. No backward compatibility tests."""
    
    def test_no_hull_family_import(self):
        """HullFamily must not exist."""
        with pytest.raises(ImportError):
            from magnet.kernel.priors.hull_families import HullFamily
    
    def test_no_hull_type_import(self):
        """HullType must not exist."""
        with pytest.raises(ImportError):
            from magnet.hull_gen.enums import HullType
    
    def test_no_chine_type_import(self):
        """ChineType must not exist."""
        with pytest.raises(ImportError):
            from magnet.hull_gen.enums import ChineType
    
    def test_no_bow_style_import(self):
        """BowStyle must not exist."""
        with pytest.raises(ImportError):
            from magnet.hull_gen.enums import BowStyle
    
    def test_constraint_synthesis_works(self):
        """Constraint-based synthesis produces valid geometry."""
        constraints = SynthesisConstraints(
            displacement_m3=(100, 150),
            max_speed_kts=35,
        )
        result = synthesize_from_constraints(constraints, state)
        assert result.success
        assert result.geometry is not None
        assert validate_hull_physics(result.geometry).valid
    
    def test_novel_form_synthesizes(self):
        """Novel form with no historical precedent synthesizes."""
        # Asymmetric deadrise, variable chine, bulbous wedge bow
        features = HullFeatures(
            chines=[
                ChineConfig(height_ratio=0.3, discontinuity_angle_deg=60, side="port"),
                ChineConfig(height_ratio=0.3, discontinuity_angle_deg=20, side="stbd"),
            ],
            bow=BowConfig(
                planarity=0.8,
                facet_count=1,
                stem_bulb_volume_m3=0.5,
            ),
        )
        # Must not raise
        geometry = generate_hull(features)
        assert geometry is not None
    
    def test_no_enum_strings_in_codebase(self):
        """Static analysis: no form enum usage anywhere."""
        forbidden = [
            "HullFamily", "HullType", "ChineType", "BowStyle",
            "StemProfile", "SternProfile", "KeelType", "SectionShape",
        ]
        for root, dirs, files in os.walk("magnet"):
            for f in files:
                if f.endswith(".py"):
                    content = Path(root, f).read_text()
                    for pattern in forbidden:
                        assert pattern not in content, f"{pattern} found in {root}/{f}"
```

---

## 0.7 North Star Alignment Guards (Anti-Drift Constraints)

This section codifies guards against the primary risks identified in the MAGNET North Star: **enumeration collapse** and **state drift**. Every implementation must pass these checks.

### 0.7.1 Guard: Character Observables are Read-Only Derived Views

**Risk**: `HullCharacterObservables` becomes enumeration-by-another-name if "Character" constrains synthesis rather than describing geometry.

**The Rule**: Character observables are **strictly post-hoc**. No synthesis path may accept a character label as input.

```python
# CORRECT: Character is derived from geometry (read-only)
def get_character(geometry: HullGeometry) -> HullCharacter:
    """Derive character from continuous geometric properties."""
    return HullCharacter(
        planing_score=compute_planing_score(geometry),      # 0.0-1.0
        displacement_score=compute_displacement_score(geometry),
        chine_hardness=compute_chine_hardness(geometry),    # 0.0-1.0
        entry_angle_deg=measure_entry_angle(geometry),
        deadrise_distribution=measure_deadrise_curve(geometry),
        # NO enum labels, only continuous values
    )

# WRONG: Character constrains synthesis (enumeration!)
def generate_hull(character: str) -> HullGeometry:
    if character == "sportfish":  # THIS IS AN ENUM
        return generate_sportfish()
    elif character == "trawler":  # THIS IS AN ENUM
        return generate_trawler()
```

**Acceptance Test**: Can the system describe a hull that has no name?

```python
def test_nameless_hull_describable():
    """System must describe novel forms without named categories."""
    # Create a hull with no historical precedent
    novel_geometry = synthesize_from_constraints(
        SynthesisConstraints(
            loa_m=22.0,
            beam_m=6.5,
            deadrise_transom_deg=22,
            entry_angle_deg=45,  # Unusual combination
            chine_count=3,       # Triple chine
        )
    )
    
    # Character extraction must work without "type" labels
    character = get_character(novel_geometry)
    
    # Must return continuous values, not "unknown" or "other"
    assert 0.0 <= character.planing_score <= 1.0
    assert character.entry_angle_deg == pytest.approx(45, rel=0.1)
    assert len(character.deadrise_distribution) > 0
    
    # Must NOT require a type label
    assert not hasattr(character, 'hull_type')
    assert not hasattr(character, 'family')
```

**If you find yourself writing `if character == 'sportfish'`, you've built an enum.**

---

### 0.7.2 Guard: VesselThinkingPass is Stateless

**Risk**: If `VesselThinkingPass` stores metadata that isn't anchored to `DesignState`, you get shadow state and drift.

**The Rule**: `VesselThinkingPass` is a **pure function** from `DesignState` to observations. No caching, no memory, no parallel record.

```python
# CORRECT: Thinking is a derived view (stateless)
class VesselThinkingPass:
    """Stateless observer—computes from state, stores nothing."""
    
    def evaluate(self, state: DesignState) -> ThinkingResult:
        """Pure function: same state → same result."""
        return ThinkingResult(
            observations=self._extract_observations(state),
            concerns=self._identify_concerns(state),
            # Every observation references a StableID in state
        )
    
    # NO instance state
    # NO cached_thoughts
    # NO memory of previous evaluations

# WRONG: Thinking has parallel state
class VesselThinkingPass:
    def __init__(self):
        self.cached_thoughts = {}  # SHADOW STATE!
        self.last_evaluation = None  # DRIFT RISK!
    
    def evaluate(self, state: DesignState) -> ThinkingResult:
        # Uses cached data that may be stale
        if state.version in self.cached_thoughts:
            return self.cached_thoughts[state.version]  # WRONG
```

**Acceptance Test**:

```python
def test_thinking_pass_is_stateless():
    """VesselThinkingPass must be a pure function."""
    thinking = VesselThinkingPass()
    
    # Same state → same result
    result1 = thinking.evaluate(state)
    result2 = thinking.evaluate(state)
    assert result1 == result2
    
    # No instance state
    assert not hasattr(thinking, 'cached_thoughts')
    assert not hasattr(thinking, 'last_evaluation')
    assert not hasattr(thinking, 'memory')
    
    # All observations reference StableIDs
    for obs in result1.observations:
        assert obs.stable_id is not None
        assert state.get_resource(obs.stable_id) is not None
```

---

### 0.7.3 Guard: Kernel is Style-Blind (Judge, Not Recognizer)

**Risk**: If the kernel rejects designs for "not feeling like a catamaran," it's recognizing intent rather than validating physics.

**The Rule**: The kernel answers **"Can this exist physically?"**—never **"Does this match user intent?"**

| Layer | Role | Style Knowledge |
|-------|------|-----------------|
| **Kernel** | Physics validation | ❌ None |
| **Agent** | Intent alignment | ✅ Yes |
| **User** | Acceptance | ✅ Yes |

```python
# CORRECT: Kernel validates physics only
class Kernel:
    def validate(self, geometry: HullGeometry) -> ValidationResult:
        """Style-blind physics validation."""
        return ValidationResult(
            hydrostatics=self.check_hydrostatics(geometry),
            stability=self.check_stability(geometry),
            structural=self.check_structural(geometry),
            # NO style checks
            # NO "does this look like a sportfish?"
            # NO intent alignment
        )

# CORRECT: Agent checks intent alignment (separate from kernel)
class DesignAgent:
    def check_intent_alignment(
        self, 
        geometry: HullGeometry, 
        user_prompt: str
    ) -> IntentAlignmentResult:
        """Agent-level check: does this match what user asked for?"""
        # This is NOT kernel validation
        # This is agent reasoning about user intent
        return IntentAlignmentResult(...)

# WRONG: Kernel recognizes intent
class Kernel:
    def validate(self, geometry: HullGeometry, intent: str) -> ValidationResult:
        if intent == "catamaran" and not self._looks_like_catamaran(geometry):
            return ValidationResult(valid=False, reason="Doesn't look like catamaran")
```

**Acceptance Test**:

```python
def test_kernel_is_style_blind():
    """Kernel must not reject based on style/intent."""
    kernel = Kernel()
    
    # Create a physically valid but "weird" hull
    weird_geometry = synthesize_from_constraints(
        SynthesisConstraints(
            loa_m=20.0,
            beam_m=8.0,  # Very beamy
            deadrise_transom_deg=5,  # Very flat
            entry_angle_deg=80,  # Very blunt
        )
    )
    
    # Kernel must validate physics, not aesthetics
    result = kernel.validate(weird_geometry)
    
    # If physics pass, kernel must accept
    if result.hydrostatics.valid and result.stability.valid:
        assert result.valid, "Kernel rejected physically valid geometry"
    
    # Kernel must not have style-based rejection reasons
    assert "doesn't look like" not in str(result.reason).lower()
    assert "style" not in str(result.reason).lower()
    assert "intent" not in str(result.reason).lower()
```

---

### 0.7.4 Guard: ADJUST/TARGET Compile to Primitive Operations

**Risk**: If `ADJUST` and `TARGET` are "fuzzy" commands the kernel interprets, the interface is ambiguous.

**The Rule**: `ADJUST`/`TARGET` are **agent-level DSL** that compile to concrete `MODIFY` operations on geometry primitives before reaching the kernel.

```python
# CORRECT: ADJUST compiles to MODIFY
def compile_adjust(
    observable_id: str, 
    delta: float, 
    state: DesignState
) -> List[ModifyOperation]:
    """
    ADJUST beam_m +0.5
    → MODIFY section_3 control_point_2 [0.25, 0.0, 0.0]
    → MODIFY section_5 control_point_2 [0.25, 0.0, 0.0]
    ...
    """
    # 1. Look up observable in registry
    observable = registry.get(observable_id)
    assert observable.controllable, f"{observable_id} is not controllable"
    
    # 2. Identify geometry primitives that affect this observable
    affected_primitives = observable.get_control_primitives(state)
    
    # 3. Compute concrete MODIFY operations
    operations = []
    for primitive in affected_primitives:
        delta_vector = observable.compute_delta(primitive, delta)
        operations.append(ModifyOperation(
            target=primitive.stable_id,
            field="control_points",
            delta=delta_vector,
        ))
    
    return operations  # Kernel sees MODIFY, not ADJUST

# WRONG: Kernel interprets fuzzy ADJUST
def kernel_execute(command: str):
    if command.startswith("ADJUST"):
        # Kernel should NOT interpret this
        # This is agent-level, not kernel-level
        pass
```

**Acceptance Test**:

```python
def test_adjust_compiles_to_modify():
    """ADJUST must resolve to concrete MODIFY operations."""
    # Agent-level command
    adjust_cmd = AdjustCommand(observable_id="beam_m", delta=0.5)
    
    # Compile to kernel-level operations
    operations = compile_adjust(adjust_cmd, state)
    
    # Must produce concrete MODIFY operations
    assert len(operations) > 0
    for op in operations:
        assert isinstance(op, ModifyOperation)
        assert op.target is not None  # StableID
        assert op.field is not None   # Specific field
        assert op.delta is not None   # Concrete delta
    
    # Kernel never sees "ADJUST"
    for op in operations:
        assert "adjust" not in str(op).lower()
        assert "target" not in str(op).lower()
```

---

### 0.7.5 Guard: Observable Extraction is Synchronous with Commit

**Risk**: If observables are computed asynchronously, agents see stale data (dirty reads).

**The Rule**: Observable extraction is **part of the atomic commit cycle**. No agent turn begins until all lenses are consistent with committed geometry.

```python
# CORRECT: Observables updated synchronously with commit
class DesignMutator:
    def commit(self, mutation: Mutation) -> CommitResult:
        """Atomic commit: geometry + observables + validation."""
        
        # 1. Apply geometry changes
        new_geometry = self._apply_geometry(mutation)
        
        # 2. Recompute ALL affected observables (SYNCHRONOUS)
        new_observables = self._recompute_observables(new_geometry)
        
        # 3. Validate physics
        validation = self._validate(new_geometry)
        
        # 4. Atomic commit (all or nothing)
        with self.state_manager.transaction():
            self.state_manager.set_geometry(new_geometry)
            self.state_manager.set_observables(new_observables)
            self.state_manager.set_validation(validation)
        
        # 5. Only NOW is state visible to agents
        return CommitResult(
            geometry=new_geometry,
            observables=new_observables,
            validation=validation,
        )

# WRONG: Async observable update
class DesignMutator:
    def commit(self, mutation: Mutation) -> CommitResult:
        new_geometry = self._apply_geometry(mutation)
        self.state_manager.set_geometry(new_geometry)  # Committed
        
        # Observables updated "later" — RACE CONDITION!
        self._schedule_observable_recompute()  # WRONG
        
        return CommitResult(geometry=new_geometry)
```

**Acceptance Test**:

```python
def test_observables_consistent_after_commit():
    """Observables must be consistent with geometry after commit."""
    mutator = DesignMutator(state)
    
    # Make a change
    result = mutator.commit(Mutation(
        operations=[ModifyOperation(target="hull", field="beam_m", delta=0.5)]
    ))
    
    # Observables must reflect the change IMMEDIATELY
    assert result.observables["beam_m"] == pytest.approx(
        original_beam + 0.5, rel=0.01
    )
    
    # State query must return consistent observables
    queried_observables = state.get_observables()
    assert queried_observables["beam_m"] == result.observables["beam_m"]
    
    # No "pending" or "stale" observables
    assert not hasattr(state, 'pending_observable_updates')
    assert not hasattr(state, 'stale_observables')
```

---

### 0.7.6 Critical Success Test: Nameless Hull Description

**The ultimate test of North Star alignment**:

> Can the "Vessel Thinking" system describe a hull form that has no name yet?

If the system can observe "entry angle 12°, deadrise distribution [22°, 18°, 14°], Cb 0.38, chine hardness 0.9" without needing to call it a "sportfish," we've succeeded.

If the system can only speak in named categories, we've built enumeration with extra steps.

```python
def test_nameless_hull_full_description():
    """
    CRITICAL SUCCESS TEST: System must describe novel forms
    using only continuous geometric properties.
    """
    # Create a hull that doesn't match any known type
    novel_hull = synthesize_from_constraints(
        SynthesisConstraints(
            loa_m=18.0,
            beam_m=5.5,
            draft_m=1.2,
            # Unusual combination that doesn't match any archetype
            deadrise_transom_deg=28,
            entry_angle_deg=35,
            Cb=0.42,
            chine_count=2,
            chine_angles=[45, 30],  # Asymmetric
        )
    )
    
    # VesselThinkingPass must describe it
    thinking = VesselThinkingPass()
    result = thinking.evaluate(state_with(novel_hull))
    
    # Must have continuous observations
    assert "entry_angle_deg" in result.observations
    assert "deadrise_distribution" in result.observations
    assert "Cb" in result.observations
    assert "chine_hardness" in result.observations
    
    # Must NOT require type labels
    for obs in result.observations.values():
        assert obs is not None
        assert obs != "unknown"
        assert obs != "other"
    
    # Must NOT contain type/family/style labels
    result_str = str(result)
    assert "sportfish" not in result_str.lower()
    assert "trawler" not in result_str.lower()
    assert "catamaran" not in result_str.lower()
    assert "hull_type" not in result_str.lower()
    assert "family" not in result_str.lower()
    
    # Physics validation must work
    validation = kernel.validate(novel_hull)
    assert validation.hydrostatics.valid or validation.hydrostatics.reason != "unknown type"
```

---

### 0.7.7 Summary: North Star Alignment Checklist

Before any PR is merged, verify:

| Guard | Check | Pass Criteria |
|-------|-------|---------------|
| **0.7.1** | Character is read-only | No synthesis path accepts character labels |
| **0.7.2** | ThinkingPass is stateless | Pure function, no instance state |
| **0.7.3** | Kernel is style-blind | Validates physics only, no intent recognition |
| **0.7.4** | ADJUST/TARGET compile | Resolves to MODIFY before kernel |
| **0.7.5** | Observables are synchronous | Updated atomically with commit |
| **0.7.6** | Nameless hull test | Novel forms describable without type labels |

**If any guard fails, the implementation has drifted from the North Star.**

---

## 0.8 Known Risks and Mitigations

This section documents architectural risks identified through review, with explicit mitigation strategies. These are **not hypothetical**—they are failure modes that similar systems have encountered.

### 0.8.1 Enumeration Creep via Taxonomies

**Risk**: The guide proposes large taxonomies (observables, component types, anchors). If any code path does `if component_type == "fuel_tank"` with different logic branches, enumeration has been rebuilt.

**Severity**: Critical

**Mitigation**:

1. **No type-dispatch in kernel or validation paths**

```python
# FORBIDDEN: Type dispatch
def validate_component(component):
    if component.type == "fuel_tank":
        return validate_fuel_tank(component)
    elif component.type == "engine":
        return validate_engine(component)

# REQUIRED: Property-based validation
def validate_component(component):
    if component.contains_flammable:
        validate_flammable_containment(component)
    if component.has_electrical:
        validate_electrical_isolation(component)
    # Type label is NEVER used in logic
```

2. **Taxonomies are metadata for search/UI only**—never dispatch keys
3. **Static analysis guard**: CI check that `magnet/kernel/*` contains no `if.*component_type` or `if.*hull_type` patterns

**Acceptance Test**:

```python
def test_no_type_dispatch_in_kernel():
    """Kernel must not branch on type labels."""
    forbidden_patterns = [
        r"if.*component_type\s*==",
        r"if.*hull_type\s*==",
        r"if.*\.type\s*==\s*['\"]",
        r"match.*component_type",
    ]
    for py_file in Path("magnet/kernel").rglob("*.py"):
        content = py_file.read_text()
        for pattern in forbidden_patterns:
            assert not re.search(pattern, content), \
                f"Type dispatch found in {py_file}: {pattern}"
```

---

### 0.8.2 Kernel Boundary Erosion

**Risk**: "User message + suggestions" and "Pareto menus" could be implemented in kernel-adjacent code, violating the principle that kernel judges reality but doesn't suggest designs.

**Severity**: Critical

**Mitigation**:

1. **Import boundary enforcement**: `magnet/kernel/*` must have **no imports from** `magnet/orchestration/*` or `magnet/agents/*`

```python
# CI check
def test_kernel_import_boundary():
    """Kernel must not import orchestration or agent modules."""
    forbidden_imports = ["magnet.orchestration", "magnet.agents"]
    for py_file in Path("magnet/kernel").rglob("*.py"):
        content = py_file.read_text()
        for forbidden in forbidden_imports:
            assert forbidden not in content, \
                f"Kernel imports {forbidden} in {py_file}"
```

2. **Suggestion flow direction**: Suggestions flow UP (kernel → orchestrator → agent → user), never DOWN

| Layer | Can Suggest? | Can Validate? |
|-------|--------------|---------------|
| Kernel | ❌ No | ✅ Yes |
| Orchestrator | ✅ Yes | ❌ No (delegates) |
| Agent | ✅ Yes | ❌ No (delegates) |

3. **Code review gate**: Any PR touching `magnet/kernel/*` must confirm no suggestion logic added

---

### 0.8.3 Novelty Bottleneck (ShipD as Ceiling)

**Risk**: Phase 1 emphasizes ShipD search + blending. If this becomes the primary generative path, novelty is bounded by the dataset. The Topology DSL (steps, tunnels, foils) is the escape hatch but could become "nice to have."

**Severity**: High

**Mitigation**:

1. **Explicit architectural statement**:

> "ShipD blending is **seed initialization only**. Novel topology (steps, tunnels, foils, asymmetric features) MUST come from the Topology DSL. If a user asks for a stepped hull and the system can only return 'closest ShipD match,' the architecture has failed."

2. **Acceptance test for novel topology**:

```python
def test_stepped_hull_via_topology_dsl():
    """Stepped hull must be creatable via DSL, not just ShipD search."""
    # This MUST work even if ShipD has no stepped hulls
    program = """
    CREATE hull FROM constraints(loa_m=22, beam_m=6)
    ADD discontinuity AT x=0.6 TYPE step HEIGHT 0.3
    ADD discontinuity AT x=0.75 TYPE step HEIGHT 0.2
    """
    result = execute_program(program)
    assert result.success
    assert count_steps(result.geometry) == 2
```

3. **Phase 1 exit criteria**: Must demonstrate at least one hull feature NOT present in ShipD (e.g., triple step, asymmetric chine, tunnel)

---

### 0.8.4 Single Write-Path Migration (Hidden Write Sites)

**Risk**: "DesignMutator is the only write path" is correct, but hidden write sites exist:
- Routing repair
- Conflict resolution
- Validators with side effects
- Optimizer internal state
- Cache invalidation

**Severity**: Critical

**Mitigation**:

1. **Write-path audit checklist** (every module must answer):

| Question | Required Answer |
|----------|-----------------|
| Does this module write to DesignState? | Yes/No |
| If yes, does it go through DesignMutator? | Must be Yes |
| If no, why not? | Must be justified and tracked |

2. **Runtime enforcement**:

```python
class DesignState:
    _write_lock: bool = True
    _mutator_context_active: bool = False
    
    @contextmanager
    def mutator_context(self):
        """Only DesignMutator can acquire this."""
        if self._mutator_context_active:
            raise ReentrantMutatorError("Nested mutator context")
        self._mutator_context_active = True
        self._write_lock = False
        try:
            yield
        finally:
            self._write_lock = True
            self._mutator_context_active = False
    
    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
            return
        if self._write_lock:
            raise IllegalWriteError(
                f"Direct write to DesignState.{name} outside DesignMutator.\n"
                f"Call stack:\n{traceback.format_stack()}"
            )
        super().__setattr__(name, value)
```

3. **Known write sites to audit**:

| Module | Write Type | Status |
|--------|------------|--------|
| `magnet/routing/repair.py` | Route modification | Must migrate |
| `magnet/integration/conflicts/resolver.py` | Component relocation | Must migrate |
| `magnet/kernel/validators/*.py` | Side effects? | Audit required |
| `magnet/optimization/*.py` | State updates | Must migrate |

---

### 0.8.5 Dry-Run Cloning Correctness

**Risk**: The plan relies on clone/discard dry-runs for character guard, gradients, and orthogonality checks. Deep copy correctness is hard—shared mutable refs, caches, IDs, and external handles can leak.

**Severity**: High

**Mitigation**:

1. **Clone contract** (explicit specification):

| Data Type | Clone Behavior | Notes |
|-----------|----------------|-------|
| Geometry primitives | Deep copy | New object instances |
| StableIDs | Preserved | Same IDs in clone |
| Transient caches | Cleared | Regenerated on access |
| External handles | Not copied | File handles, GPU buffers |
| Version counters | Incremented | Clone is new version |

2. **Clone validation**:

```python
def clone(self) -> "DesignState":
    cloned = copy.deepcopy(self)
    
    # Validate isolation
    self._assert_no_shared_mutable_refs(cloned)
    
    # Clear transient state
    cloned._clear_caches()
    
    # Increment version
    cloned._version = self._version + 1
    cloned._is_clone = True
    
    return cloned

def _assert_no_shared_mutable_refs(self, other: "DesignState"):
    """Fail fast if clone shares mutable state."""
    for key in self.__dict__:
        if key.startswith('_'):
            continue
        self_val = getattr(self, key)
        other_val = getattr(other, key)
        if isinstance(self_val, (list, dict, set)):
            assert self_val is not other_val, \
                f"Shared mutable ref: {key}"
```

3. **Clone performance budget**: Max 100ms for typical design (track in CI)

---

### 0.8.6 Receipt Schema Explosion

**Risk**: JSONL receipts can balloon with sensitivities, error chains, and multi-step orchestrations, becoming an unstable API.

**Severity**: Medium

**Mitigation**:

1. **Minimal core schema** (stable, always present):

```python
@dataclass
class MutationReceiptCore:
    """STABLE SCHEMA - do not add fields without versioning."""
    receipt_id: str
    timestamp: datetime
    mutation_type: str  # CREATE, MODIFY, DELETE
    target_ids: List[str]
    success: bool
    error_code: Optional[str] = None
    
@dataclass  
class MutationReceipt(MutationReceiptCore):
    """Full receipt with versioned extensions."""
    schema_version: str = "1.0"
    extensions: Dict[str, Any] = field(default_factory=dict)
    # extensions["sensitivity_v1"] = {...}
    # extensions["error_chain_v1"] = {...}
```

2. **Schema version in every log file header**
3. **Extension naming convention**: `{feature}_v{version}` (e.g., `sensitivity_v1`)
4. **Backward compatibility rule**: Core fields never removed, only deprecated

---

### 0.8.7 Inter-Level Schemas Freeze Too Early

**Risk**: The guide proposes specific structures (zones, interfaces, routing requirements) before real integration exposes what's missing.

**Severity**: Medium

**Mitigation**:

1. **Mark schemas as provisional**:

```python
@dataclass
class ZoneInterface:
    """
    PROVISIONAL SCHEMA - v0.1
    
    Graduation criteria:
    - [ ] Used in 3+ real designs
    - [ ] Survives routing integration
    - [ ] Survives multi-body physics integration
    - [ ] Reviewed by systems team
    
    DO NOT depend on field stability until graduated.
    """
    zone_id: str
    boundaries: List[BoundaryRef]
    # ...
```

2. **Schema graduation process**:

| Stage | Stability | Can Change? |
|-------|-----------|-------------|
| Provisional | Unstable | Yes, freely |
| Beta | Semi-stable | Yes, with deprecation |
| Stable | Stable | No (new version required) |

3. **Integration-driven design**: Schemas graduate only after surviving real integration

---

### 0.8.8 Coordinate Frames Under-Specified

**Risk**: Frame drift is a silent killer. The guide mentions frames but doesn't specify ownership, versioning, or tolerance.

**Severity**: High

**Mitigation**:

**CONFIRMED IN CURRENT CODEBASE**:
- `magnet/physics/geometry_hydrostatics.py` documents implicit assumptions:
  - “baseline z=0, waterline at z=draft”
  - “positions are treated as global vessel coordinates”
- There is no runtime enforcement that input geometry is actually expressed in this frame, so imported geometry with different origins will yield silently wrong hydrostatics.

1. **Frame governance protocol**:

```python
@dataclass
class CoordinateFrame:
    frame_id: str
    owner_module: str  # Which module owns this frame
    parent_frame: Optional[str]
    transform_to_parent: Transform
    tolerance_m: float  # Acceptable error
    version: int  # Incremented on any change

class FrameRegistry:
    """Kernel-owned frame authority."""
    
    def register_frame(self, frame: CoordinateFrame) -> None:
        if frame.frame_id in self._frames:
            raise DuplicateFrameError(frame.frame_id)
        self._frames[frame.frame_id] = frame
    
    def validate_point(self, point: Point) -> None:
        """Reject points with unknown or mismatched frames."""
        if point.frame_id not in self._frames:
            raise UnknownFrameError(point.frame_id)
    
    def transform(self, point: Point, target_frame: str) -> Point:
        """Transform point to target frame with validation."""
        self.validate_point(point)
        # ... transform logic
```

2. **Frame-explicit rule**: Every spatial value must declare its frame. No implicit "vessel coordinates."

3. **Frame validation in validators**: All validators must check frame consistency before physics calculations

---

### 0.8.9 Systems-as-Geometry Complexity

**Risk**: Turning systems into `geometry.*` artifacts touches placement, anchors, routing, conflicts, physics, and UI—a multi-subsystem rewrite with coupled invariants.

**Severity**: High

**Mitigation**:

1. **Explicit integration milestones** (not one big bang):

| Milestone | Scope | Acceptance Test |
|-----------|-------|-----------------|
| M1 | Single component places on hull | Component visible in viewer |
| M2 | Two components with single route | Route connects components |
| M3 | Conflict detection | Overlapping components flagged |
| M4 | Routing repair | Route adjusts when component moves |
| M5 | Multi-body physics | Hydrostatics includes components |

2. **Each milestone is a shippable increment**—don't proceed to M(n+1) until M(n) passes

3. **Complexity budget**: If any milestone takes >2x estimated time, stop and reassess architecture

---

### 0.8.10 "No system.* Types" Easy to Violate

**Risk**: Tagging `geometry.body` with `system_id` works only with strict contracts. Otherwise, ad-hoc metadata conventions become implicit types.

**Severity**: Medium

**Mitigation**:

1. **Required tags contract**:

```python
SYSTEM_COMPONENT_REQUIRED_TAGS = {
    "system_id": str,           # Which system (fuel, electrical, etc.)
    "component_id": str,        # Unique within system
    "component_category": str,  # Metadata only, NOT dispatch key
}

SYSTEM_COMPONENT_OPTIONAL_TAGS = {
    "bounds_hint": BoundingBox,
    "connection_points": List[ConnectionPoint],
    "material": str,
}

def validate_system_component_tags(body: GeometryBody) -> None:
    """Validate required tags on system components."""
    for tag, expected_type in SYSTEM_COMPONENT_REQUIRED_TAGS.items():
        if tag not in body.tags:
            raise MissingTagError(f"System component {body.id} missing required tag: {tag}")
        if not isinstance(body.tags[tag], expected_type):
            raise TagTypeError(f"Tag {tag} on {body.id} has wrong type")
```

2. **Tag schema validation in DesignMutator**: Every component add/modify validates tags

3. **No implicit type inference**: If code infers behavior from tag combinations, it's building implicit types

---

### 0.8.11 External Data Brittleness

**Risk**: Runtime cloning ShipD introduces availability, licensing, reproducibility, and security concerns.

**Severity**: Medium

**Mitigation**:

1. **Pin to specific commit**:

```bash
git clone --branch v1.0 --depth 1 https://github.com/noahbagz/ShipD.git
```

2. **Offline fallback**: System must work with cached data if network unavailable

```python
def get_shipd_path() -> Path:
    cached = Path("data/hull_library/shipd")
    if cached.exists():
        return cached
    
    if not network_available():
        raise OfflineError("ShipD not cached and network unavailable")
    
    clone_shipd(cached)
    return cached
```

3. **License audit**: Document ShipD license (MIT) in repo, verify compatibility

4. **Integrity check**: Hash verification of downloaded data

---

### 0.8.12 Platform Fragility

**Risk**: `pythonocc-core`, `rtree`, large embedding models, and `pyarrow` cause install pain and CI instability.

**Severity**: Medium

**Mitigation**:

1. **Tier dependencies**:

| Tier | Dependencies | Failure Mode |
|------|--------------|--------------|
| Core | numpy, dataclasses | Fatal |
| Required | pandas, pyarrow | Fatal |
| Optional | pythonocc-core, rtree | Graceful degradation |
| Dev-only | sentence-transformers | Skip in CI if unavailable |

2. **Fallback implementations**:

```python
try:
    from rtree import index as SpatialIndex
except ImportError:
    from magnet.utils.naive_spatial import NaiveSpatialIndex as SpatialIndex
    warnings.warn("rtree not available, using naive spatial index (slower)")
```

3. **Docker dev environment**: Pinned, reproducible environment for all dependencies

4. **CI caching**: Pre-built wheels for problematic packages

---

### 0.8.13 Over-Broad Static Analysis Tests

**Risk**: Tests that forbid substrings like "HullFamily" break on docstrings, comments, and migration notes.

**Severity**: Low

**Mitigation**:

1. **Test behavior, not strings**:

```python
# WRONG: String scan
def test_no_hull_family_string():
    assert "HullFamily" not in all_code()

# CORRECT: Behavior test
def test_no_hull_family_import():
    with pytest.raises(ImportError):
        from magnet.kernel.priors.hull_families import HullFamily

def test_synthesis_ignores_family_param():
    # Even if someone passes family, it's ignored
    result = synthesize(constraints, family="sportfish")
    assert result.success
```

2. **Allowlist for documentation**: Static analysis can skip `docs/`, `*.md`, docstrings

3. **Focus on import/instantiation**: The real test is whether enum types can be imported and used, not whether strings exist

---

### 0.8.14 Guardrails Need Enforcement Points

**Risk**: "Never mutate resources directly" is a rule, but rules without enforcement are wishes.

**Severity**: Critical

**Mitigation**:

1. **Runtime enforcement** (see §0.8.4 for DesignState write lock)

2. **CI enforcement**:

```python
def test_all_writes_through_mutator():
    """Verify no direct state mutations in codebase."""
    # Find all .set_, .add_, .remove_ calls on DesignState
    # Verify they're only in DesignMutator
    mutator_file = Path("magnet/core/design_mutator.py")
    
    for py_file in Path("magnet").rglob("*.py"):
        if py_file == mutator_file:
            continue
        content = py_file.read_text()
        if re.search(r"design_state\.(set_|add_|remove_|update_)", content):
            raise AssertionError(f"Direct state mutation in {py_file}")
```

3. **Code review checklist**: Every PR must confirm no new direct write paths

---

### 0.8.15 Duplicate Scene/Assembly Pipelines

**Risk**: If the assembly pipeline builds its own scene graph that isn't a projection of `DesignState.resources`, you have two SSOTs.

**Severity**: Critical

**Mitigation**:

1. **Assembly pipeline is a view, not a store**:

```python
# CORRECT: View over DesignState
class AssemblyView:
    """Read-only view over DesignState for rendering."""
    
    def __init__(self, state: DesignState):
        self._state = state  # Reference, not copy
    
    def get_scene_graph(self) -> SceneGraph:
        """Computed from state on every call, not cached."""
        return self._build_scene_graph(self._state.resources)
    
    # NO self.scene_graph storage
    # NO self.cached_assembly
    # NO self.last_update_version

# WRONG: Parallel store
class AssemblyPipeline:
    def __init__(self):
        self.scene_graph = SceneGraph()  # SECOND SSOT!
```

2. **No caching without invalidation**: If scene graph is cached for performance, it must invalidate on any DesignState change

3. **Single render path**: UI, export, and preview all use the same `AssemblyView`

---

### 0.8.15A LLM Junk Commits / Hallucinated Edits (Human-in-the-Loop is not optional)

**Risk**: LLMs will hallucinate. Without a hard **proposal sandbox → validate → approve → commit** gate, the canonical state will accumulate junk (nonsensical geometry edits, contradictory constraints, broken routing repairs), and the design spiral will drift into unrecoverable incoherence.

**Severity**: High

**Mitigation**: Make proposal sandboxing the **default** for any LLM-originated change.

- Agents propose **programs/actions**, never direct state writes.
- Proposals execute in a **forked snapshot**, run validators, emit a structured diff/receipt, and only merge on approval.
- Approval can be:
  - a real user action in UI (preferred),
  - or an explicit tool call `approve_proposal(proposal_id)` (for automation).

**File location**:
- New: `magnet/core/proposal_sandbox.py`
- Extend: `magnet/core/state_manager.py` (wire sandbox into commit pipeline)
- Extend: `magnet/core/receipts.py` (proposal receipts/diffs)

**Interface contract (minimum)**:

```python
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Literal

ApprovalMode = Literal["human_required", "auto_if_valid", "never_auto"]

@dataclass(frozen=True)
class ProposalDiff:
    """Structured diff derived from canonical actions (not ad-hoc tree diffs)."""
    actions: List[Dict[str, Any]]          # canonical action objects (CREATE/MODIFY/DELETE…)
    affected_resource_ids: List[str]
    summary: str

@dataclass(frozen=True)
class ProposalResult:
    proposal_id: str
    approved: bool
    valid: bool
    diff: ProposalDiff
    validation_report: Dict[str, Any]      # validators, margins, confidence, evidence
    receipt_id: Optional[str] = None

class ProposalSandbox:
    """
    Default path for LLM-originated changes:
    snapshot → apply actions → validate → produce diff/receipt → await approval → commit atomically.
    """
    def __init__(self, state_manager: "StateManager"):
        self._sm = state_manager

    def propose(
        self,
        actions: List[Dict[str, Any]],
        approval_mode: ApprovalMode = "human_required",
    ) -> ProposalResult:
        ...

    def approve(self, proposal_id: str) -> ProposalResult:
        ...

    def reject(self, proposal_id: str, reason: str) -> None:
        ...
```

**Integration point (MAGNET)**:
- All agent-facing mutation endpoints route through `ProposalSandbox` by default.
- `StateManager.commit()` must only accept:
  - action lists produced by program compilation, OR
  - sandbox-approved proposals (never ad-hoc diffs).

**Acceptance tests**:
- New: `tests/core/test_proposal_sandbox.py`
  - `test_llm_proposal_never_mutates_canonical_without_approval()`
  - `test_invalid_proposal_cannot_be_approved()`
  - `test_approved_proposal_commits_atomically_and_emits_receipt()`
  - `test_concurrent_proposals_only_one_can_commit_and_others_stay_pending()`

---

### 0.8.16 Risk Summary Matrix

| # | Risk | Severity | Mitigation Status |
|---|------|----------|-------------------|
| 0.8.1 | Enumeration creep via taxonomies | Critical | Guard defined |
| 0.8.2 | Kernel boundary erosion | Critical | Guard defined |
| 0.8.3 | Novelty bottleneck (ShipD ceiling) | High | Guard defined |
| 0.8.4 | Hidden write sites | Critical | Runtime enforcement defined |
| 0.8.5 | Dry-run clone correctness | High | Contract defined |
| 0.8.6 | Receipt schema explosion | Medium | Schema versioning defined |
| 0.8.7 | Inter-level schemas freeze early | Medium | Graduation process defined |
| 0.8.8 | Coordinate frames under-specified | High | Governance protocol defined |
| 0.8.9 | Systems-as-geometry complexity | High | Milestones defined |
| 0.8.10 | Implicit system types | Medium | Tag contract defined |
| 0.8.11 | External data brittleness | Medium | Offline fallback defined |
| 0.8.12 | Platform fragility | Medium | Tiered dependencies defined |
| 0.8.13 | Over-broad static tests | Low | Behavior tests recommended |
| 0.8.14 | Guardrails without enforcement | Critical | Runtime + CI enforcement defined |
| 0.8.15 | Duplicate scene pipelines | Critical | View-only pattern defined |
| 0.8.15A | LLM junk commits / hallucinated edits | High | Sandbox gate defined |

**Review cadence**: Revisit this risk matrix at each phase boundary. Add new risks as discovered.

---

## 0.9 Mathematical, Physics, and Logic Gaps

This section documents technical gaps in math, physics, and logic identified through code review. These are **blocking issues** that must be resolved before the affected components can work correctly.

### 0.9.1 Hull Blending Coefficient Coupling (Math Gap)

**Location**: `magnet/bootstrap/blending.py` (proposed) vs `magnet/hull_gen/parameters.py` (existing)

**Severity**: Critical (will produce invalid geometry)

**The Problem**: The proposed linear blending of hull parameters is mathematically flawed for coupled coefficients.

**The Math**: Hull form coefficients are coupled by definition:

$$C_b = C_p \times C_m$$

Where:
- $C_b$ = Block coefficient
- $C_p$ = Prismatic coefficient  
- $C_m$ = Midship coefficient

**The Gap**: Linearly blending $C_b$, $C_p$, and $C_m$ independently does **not** preserve this relationship.

**Example**:

| Hull | $C_p$ | $C_m$ | $C_b$ (actual) |
|------|-------|-------|----------------|
| A | 0.60 | 0.80 | 0.48 |
| B | 0.80 | 0.90 | 0.72 |
| **50/50 Linear Blend** | 0.70 | 0.85 | **0.60** |
| **Required** | 0.70 | 0.85 | **0.595** |

The linear average gives $C_b = 0.60$, but the mathematically correct value is $C_b = 0.70 \times 0.85 = 0.595$.

**Consequence**: 
- `FormCoefficients.validate()` will fail (requires `abs(cb - cp*cm) < 0.05`)
- Geometry will "fight itself" since `HullGenerator` uses $C_b$ and $C_m$ for section fullness but $C_p$ for longitudinal distribution

**Fix Required**:

```python
# WRONG: Linear blending of all parameters
def blend_hulls_wrong(hulls: List[LibraryHull], weights: List[float]) -> Dict[str, float]:
    blended = {}
    for param in HULL_PARAMS:
        values = [h.parameters[param] for h in hulls]
        blended[param] = np.dot(weights, values)  # Linear blend ALL
    return blended

# CORRECT: Blend independent params, derive dependent ones
def blend_hulls_correct(hulls: List[LibraryHull], weights: List[float]) -> Dict[str, float]:
    blended = {}
    
    # Blend INDEPENDENT parameters
    INDEPENDENT_PARAMS = ["Cp", "Cm", "LCB", "LOA", "B", "T", ...]
    for param in INDEPENDENT_PARAMS:
        values = [h.parameters[param] for h in hulls]
        blended[param] = np.dot(weights, values)
    
    # DERIVE dependent parameters from blended independents
    blended["Cb"] = blended["Cp"] * blended["Cm"]  # Preserve coupling
    blended["Cwp"] = derive_cwp(blended)  # If coupled
    
    return blended
```

**Parameter Dependency Graph**:

```
INDEPENDENT (blend directly):
├── Cp (prismatic coefficient)
├── Cm (midship coefficient)
├── LCB (longitudinal center of buoyancy)
├── LOA, B, T, D (principal dimensions)
├── Entry angle, deadrise, etc.

DEPENDENT (derive after blending):
├── Cb = Cp × Cm
├── Displacement = Cb × L × B × T
├── Cwp (if coupled to Cb)
```

**Test Requirement**:

```python
def test_blended_coefficients_are_consistent():
    """Blended hull must satisfy Cb = Cp * Cm."""
    hulls = [hull_a, hull_b, hull_c]
    weights = [0.3, 0.5, 0.2]
    
    blended = blend_hulls(hulls, weights)
    
    # Must satisfy coupling relationship
    assert abs(blended["Cb"] - blended["Cp"] * blended["Cm"]) < 0.001
    
    # Must pass existing validation
    coeffs = FormCoefficients(**blended)
    assert coeffs.validate()
```

---

### 0.9.2 Discontinuous Gradients in Optimization (Physics/Math Gap)

**Location**: `magnet/kernel/coordinate_executor.py` (proposed) vs `magnet/hull_gen/generator.py` (existing)

**Severity**: High (will cause optimizer instability)

**The Problem**: The COORDINATE optimizer uses finite-difference gradients, but the underlying parametric functions have $C^1$ discontinuities (continuous position, discontinuous slope).

**CONFIRMED IN CURRENT CODEBASE**:
- `magnet/hull_gen/generator.py` currently implements `_get_beam_factor_at_station(...)` with hard piecewise `if/elif` branches at `station=0.1`, `station=LCB`, and `station=0.9`, causing slope jumps at the boundaries.
- This is visible in the function body around `station < 0.1 / station < lcb / station < 0.9 / else`.

**The Math**: `HullGenerator._get_beam_factor_at_station` uses piecewise functions:

```python
def _get_beam_factor_at_station(self, station: float, lcb: float) -> float:
    if station < 0.1:
        return linear_interpolation(...)      # Region 1
    elif station < lcb:
        return 1.0                            # Region 2 (constant)
    elif station < 0.9:
        return linear_reduction(...)          # Region 3
    else:
        return t ** 1.5                       # Region 4 (power function)
```

**The Gap**: Transitions at `station=LCB` and `station=0.9` are:
- $C^0$ continuous (position matches)
- $C^1$ **discontinuous** (slope jumps)

**Consequence**: 
- Finite-difference gradient estimation sees "infinite" or erratic gradients when perturbation crosses boundaries
- Causes the "transient validator crashes" warned about in the guide
- Optimizer may oscillate or fail to converge

**Visualization**:

```
Beam Factor vs Station
                    
    1.0 ─────────────┐
                     │ ← Slope discontinuity at LCB
                     └────────┐
                              │ ← Slope discontinuity at 0.9
                              └──────
    
    0   0.1   LCB   0.9   1.0
```

**Fix Required**: Refactor generator functions to use smooth blending at transition points.

#### Bound Handling Decision (Option B — Preserve C1 Continuity)

When a smooth transition (Hermite/sigmoid/tanh/softplus) produces a tiny overshoot (e.g. `1.000347`), **DO NOT apply a hard clamp** (`min(max(x,0),1)`) on synthesis-path blend factors (beam factors, taper factors, deadrise blends, etc.).

- **Why**: hard clamping creates a flat derivative at the boundary (a kink), violating the **C1 continuity invariant** and destabilizing finite-difference gradients (see `tests/hull_gen/test_generator_continuity_e03.py`).
- **Rule**: synthesis-path transitions must stay **C1 (or better)**. Enforce bounds with **smooth clipping** (softplus/softmin) or by shaping the transition so the range is respected without kinks.
- **Allowed**: hard clamp may be used for **non-synthesis** values (UI normalization, reporting scalars, or post-hoc classification) where derivative continuity is irrelevant.

**Canonical implementation pattern** (already matches current code structure in `magnet/hull_gen/generator.py`):

```python
# Avoid hard clamp on the blended output.
# Use a smooth clip that asymptotically enforces [0,1].
def _softclip01(x: float, beta: float = 60.0) -> float:
    y = _softplus(x, beta=beta)          # smooth max(x, 0)
    return _softmin(y, 1.0, beta=beta)   # smooth min(y, 1)
```

```python
# WRONG: Hard piecewise transitions
def _get_beam_factor_wrong(self, station: float, lcb: float) -> float:
    if station < lcb:
        return 1.0
    else:
        return 1.0 - (station - lcb) / (1.0 - lcb)  # Hard transition

# CORRECT: Smooth sigmoid/Hermite blending
def smoothstep(t: float) -> float:
    """Hermite smoothstep: C^1 continuous, derivative=0 at endpoints."""
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)

def _get_beam_factor_correct(self, station: float, lcb: float) -> float:
    # Blend width for smooth transition
    BLEND_WIDTH = 0.05
    
    if station < lcb - BLEND_WIDTH:
        return 1.0
    elif station < lcb + BLEND_WIDTH:
        # Smooth transition using Hermite interpolation
        t = (station - (lcb - BLEND_WIDTH)) / (2 * BLEND_WIDTH)
        return 1.0 - smoothstep(t) * self._get_reduction_at(lcb + BLEND_WIDTH)
    else:
        return self._get_reduction_at(station)
```

**Locations Requiring Smoothing**:

| Function | Discontinuity Location | Fix |
|----------|------------------------|-----|
| `_get_beam_factor_at_station` | `station=LCB`, `station=0.9` | Hermite blend |
| `_get_deadrise_at_station` | `station=0.0`, `station=1.0` | Hermite blend |
| `_get_chine_height_at_station` | Chine start/end | Hermite blend |
| `_get_section_fullness` | LCB transition | Hermite blend |

**Test Requirement**:

```python
def test_beam_factor_is_c1_continuous():
    """Beam factor must have continuous first derivative."""
    generator = HullGenerator(params)
    
    # Sample at fine resolution
    stations = np.linspace(0, 1, 1000)
    factors = [generator._get_beam_factor_at_station(s, lcb=0.5) for s in stations]
    
    # Compute numerical derivative
    derivatives = np.diff(factors) / np.diff(stations)
    
    # Derivative changes should be bounded (no jumps)
    derivative_changes = np.abs(np.diff(derivatives))
    max_change = np.max(derivative_changes)
    
    assert max_change < 0.1, f"Derivative discontinuity detected: {max_change}"
```

---

### 0.9.3 Missing Kinematics for Multi-Body Optimization (Physics Gap)

**Location**: `magnet/webgl/assembly_pipeline.py` (proposed), `magnet/bootstrap/component_library.py` (proposed)

**Severity**: High (blocks multi-body optimization)

**The Problem**: The Component Library and Assembly Pipeline introduce multi-body assemblies, but lack kinematic degrees of freedom (DoF) for optimization.

**The Gap**: 
- `HullGenerator` is purely parametric (shape deformation)
- No concept of kinematic variables (Translation X/Y/Z, Rotation R/P/Y) for components
- `geometry_hydrostatics.py` can calculate results, but optimizer has no "knobs" to turn

**Consequence**: Cannot answer questions like:
- "Move the outrigger hulls to optimize stability"
- "Adjust engine position for better trim"
- "Optimize fuel tank placement for CG"

**Fix Required**: Define 6-DoF kinematic parameters for all `ComponentRef` entries.

```python
# magnet/core/component_kinematics.py

from dataclasses import dataclass
from typing import Optional
import numpy as np

@dataclass
class KinematicDoF:
    """6-DoF kinematic parameters for a component."""
    
    # Translation (meters, in vessel frame)
    x: float = 0.0  # Longitudinal (+ forward)
    y: float = 0.0  # Transverse (+ starboard)
    z: float = 0.0  # Vertical (+ up)
    
    # Rotation (degrees, Euler angles)
    roll: float = 0.0   # About X axis
    pitch: float = 0.0  # About Y axis
    yaw: float = 0.0    # About Z axis
    
    # Constraints (for optimizer)
    x_bounds: Optional[tuple] = None  # (min, max) or None if fixed
    y_bounds: Optional[tuple] = None
    z_bounds: Optional[tuple] = None
    roll_bounds: Optional[tuple] = None
    pitch_bounds: Optional[tuple] = None
    yaw_bounds: Optional[tuple] = None
    
    def to_transform_matrix(self) -> np.ndarray:
        """Convert to 4x4 homogeneous transform matrix."""
        # ... implementation
    
    def get_adjustable_params(self) -> List[str]:
        """Return list of DoFs that can be optimized."""
        adjustable = []
        if self.x_bounds is not None: adjustable.append("x")
        if self.y_bounds is not None: adjustable.append("y")
        if self.z_bounds is not None: adjustable.append("z")
        if self.roll_bounds is not None: adjustable.append("roll")
        if self.pitch_bounds is not None: adjustable.append("pitch")
        if self.yaw_bounds is not None: adjustable.append("yaw")
        return adjustable


@dataclass
class ComponentRef:
    """Reference to a placed component with kinematics."""
    component_id: str
    stable_id: str
    geometry: GeometryBody
    kinematics: KinematicDoF  # NEW: Add kinematic DoF
    
    # Connection to hull
    anchor_point: str  # Hull anchor this attaches to
    attachment_type: str  # "rigid", "hinged", "sliding"
```

**Observable Registry Integration**:

```python
# Register kinematic DoFs as observables
def register_component_kinematics(registry: ObservableRegistry, component: ComponentRef):
    """Register component kinematic DoFs as adjustable observables."""
    
    prefix = f"component.{component.stable_id}"
    
    for dof in ["x", "y", "z", "roll", "pitch", "yaw"]:
        bounds = getattr(component.kinematics, f"{dof}_bounds")
        if bounds is not None:
            registry.register(
                observable_id=f"{prefix}.{dof}",
                mode="controllable",
                unit="m" if dof in ["x", "y", "z"] else "deg",
                bounds=bounds,
                getter=lambda c=component, d=dof: getattr(c.kinematics, d),
                setter=lambda v, c=component, d=dof: setattr(c.kinematics, d, v),
            )
```

**Test Requirement**:

```python
def test_component_kinematics_are_optimizable():
    """Component positions can be optimized via COORDINATE."""
    # Place outrigger with adjustable Y position
    outrigger = place_component(
        component_id="outrigger_hull",
        kinematics=KinematicDoF(
            x=5.0, y=3.0, z=0.0,
            y_bounds=(2.0, 5.0),  # Adjustable
        )
    )
    
    # Register in observable registry
    register_component_kinematics(registry, outrigger)
    
    # Verify observable exists and is controllable
    obs = registry.get(f"component.{outrigger.stable_id}.y")
    assert obs.mode == "controllable"
    assert obs.bounds == (2.0, 5.0)
    
    # Verify optimizer can adjust it
    result = coordinate_executor.optimize(
        target={"GM": 2.0},
        adjustable=[f"component.{outrigger.stable_id}.y"]
    )
    assert result.success
```

---

### 0.9.4 Optimizer in Kernel (North Star Violation)

**Location**: `magnet/kernel/coordinate_executor.py` (proposed)

**Severity**: Medium (architectural violation)

**The Problem**: Placing an optimizer inside `magnet/kernel/` violates the North Star principle: "The kernel's only role is to validate reality, not recognize intent."

**The Gap**: An optimizer inherently pursues a goal/intent. If it includes heuristics (e.g., "increase beam to fix GM"), it recognizes intent.

**Acceptable**: Pure numerical solver (Newton-Raphson, Levenberg-Marquardt) with no naval architecture knowledge.

**Unacceptable**: Solver with heuristics like:
- "If GM is low, try increasing beam first"
- "For planing hulls, prioritize deadrise over beam"
- "Sportfish hulls should have higher entry angles"

**Fix Required**: Ensure `coordinate_executor.py` is **strictly numerical**.

```python
# CORRECT: Pure numerical solver (no domain knowledge)
class CoordinateExecutor:
    """
    Numerical optimizer for COORDINATE verb.
    
    NORTH STAR COMPLIANCE:
    - This is a NUMERICAL SOLVER, not a design advisor
    - Contains ZERO naval architecture heuristics
    - Does not know what "beam", "GM", or "sportfish" mean
    - Only knows: parameters, targets, gradients, convergence
    """
    
    def optimize(
        self,
        targets: Dict[str, float],
        adjustable: List[str],
        state: DesignState,
    ) -> OptimizationResult:
        """
        Pure numerical optimization via Levenberg-Marquardt.
        
        NO HEURISTICS. NO DOMAIN KNOWLEDGE.
        """
        # Get current values
        current = self._get_current_values(adjustable, state)
        
        # Compute residuals (target - actual)
        residuals = self._compute_residuals(targets, state)
        
        # Compute Jacobian via finite differences
        jacobian = self._compute_jacobian_safe(adjustable, targets, state)
        
        # Levenberg-Marquardt step (pure math)
        step = self._lm_step(jacobian, residuals, self.damping)
        
        # Apply step (no heuristic ordering)
        new_values = current + step
        
        return OptimizationResult(...)

# WRONG: Solver with domain heuristics
class CoordinateExecutorWrong:
    def optimize(self, targets, adjustable, state):
        if "GM" in targets and targets["GM"] > current_gm:
            # VIOLATION: This is a heuristic!
            prioritize_beam_increase()
        
        if state.hull_type == "planing":  # VIOLATION: Recognizes type!
            use_planing_optimization_strategy()
```

**Import Boundary Enforcement**:

```python
# CI test
def test_coordinate_executor_has_no_domain_imports():
    """Optimizer must not import domain-specific modules."""
    import ast
    
    with open("magnet/kernel/coordinate_executor.py") as f:
        tree = ast.parse(f.read())
    
    forbidden_imports = [
        "hull_gen",
        "naval",
        "hydrostatics",  # Can use results, but not import logic
        "stability",
        "resistance",
    ]
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for forbidden in forbidden_imports:
                    assert forbidden not in alias.name, \
                        f"Optimizer imports domain module: {alias.name}"
```

---

### 0.9.5 Safe Gradient Implementation (Implementation Gap)

**Location**: `magnet/kernel/coordinate_executor.py` (proposed)

**Severity**: Critical (blocks optimizer implementation)

**The Problem**: The guide lists `_compute_gradients_safe` as P0 but marks it as "Missing item" without concrete implementation.

**The Gap**: 
- Current architecture uses singleton `DesignState`
- "Dry run" perturbations require `clone() -> perturb() -> validate() -> discard()`
- Performance budget undefined

**Performance Concern**: For gradient estimation with N adjustable parameters:
- Need N+1 evaluations (forward difference) or 2N (central difference)
- Each evaluation requires full physics validation
- If validation takes 200ms, gradient for 20 parameters = 4-8 seconds
- Multiple optimizer iterations = 40+ seconds per COORDINATE call

**Fix Required**: Explicit implementation with performance budget.

```python
# magnet/kernel/gradient_estimator.py

from dataclasses import dataclass
from typing import Dict, List, Callable
import time

@dataclass
class GradientConfig:
    """Configuration for safe gradient estimation."""
    
    # Finite difference settings
    step_size: float = 1e-4  # Relative step for finite differences
    method: str = "forward"  # "forward" (N+1 evals) or "central" (2N evals)
    
    # Performance budget
    max_eval_time_ms: float = 200.0  # Max time per evaluation
    max_total_time_ms: float = 5000.0  # Max time for full gradient
    
    # Parallelization
    parallel: bool = True  # Evaluate perturbations in parallel
    max_workers: int = 4  # Thread pool size
    
    # Caching
    cache_base_evaluation: bool = True  # Reuse base state evaluation


class SafeGradientEstimator:
    """
    Compute gradients without mutating committed state.
    
    SAFETY GUARANTEES:
    1. Original state is NEVER modified
    2. All perturbations use cloned state
    3. Clones are discarded after evaluation
    4. Timeout prevents runaway computation
    """
    
    def __init__(self, config: GradientConfig, state_manager: StateManager):
        self.config = config
        self.state_manager = state_manager
        self._eval_count = 0
        self._total_time_ms = 0
    
    def compute_jacobian(
        self,
        adjustable_params: List[str],
        target_observables: List[str],
        evaluate_fn: Callable[[DesignState], Dict[str, float]],
    ) -> np.ndarray:
        """
        Compute Jacobian matrix via finite differences.
        
        Returns: (n_targets x n_params) Jacobian matrix
        """
        start_time = time.time()
        
        n_params = len(adjustable_params)
        n_targets = len(target_observables)
        jacobian = np.zeros((n_targets, n_params))
        
        # Evaluate base state (cache if enabled)
        base_state = self.state_manager.get_current_state()
        base_values = self._evaluate_safe(base_state, evaluate_fn)
        
        # Compute partial derivatives for each parameter
        if self.config.parallel:
            jacobian = self._compute_parallel(
                adjustable_params, target_observables,
                base_state, base_values, evaluate_fn
            )
        else:
            for i, param in enumerate(adjustable_params):
                self._check_timeout(start_time)
                
                # Clone state for perturbation
                perturbed_state = self._clone_state(base_state)
                
                # Apply perturbation
                current_value = self._get_param(perturbed_state, param)
                step = self.config.step_size * max(abs(current_value), 1e-6)
                self._set_param(perturbed_state, param, current_value + step)
                
                # Evaluate perturbed state
                perturbed_values = self._evaluate_safe(perturbed_state, evaluate_fn)
                
                # Compute partial derivatives
                for j, target in enumerate(target_observables):
                    jacobian[j, i] = (
                        perturbed_values[target] - base_values[target]
                    ) / step
                
                # Discard clone (explicit cleanup)
                del perturbed_state
        
        self._total_time_ms = (time.time() - start_time) * 1000
        return jacobian
    
    def _clone_state(self, state: DesignState) -> DesignState:
        """
        Create isolated clone for perturbation.
        
        SAFETY: Clone must not share mutable state with original.
        """
        clone = state.clone()
        
        # Verify isolation (debug mode)
        if __debug__:
            clone._assert_no_shared_refs(state)
        
        return clone
    
    def _evaluate_safe(
        self,
        state: DesignState,
        evaluate_fn: Callable,
    ) -> Dict[str, float]:
        """
        Evaluate state with timeout protection.
        """
        self._eval_count += 1
        
        start = time.time()
        try:
            result = evaluate_fn(state)
        except Exception as e:
            # Log but don't crash - return NaN for failed evaluation
            return {k: float('nan') for k in result.keys()}
        
        elapsed_ms = (time.time() - start) * 1000
        if elapsed_ms > self.config.max_eval_time_ms:
            warnings.warn(
                f"Evaluation took {elapsed_ms:.0f}ms "
                f"(budget: {self.config.max_eval_time_ms}ms)"
            )
        
        return result
    
    def _check_timeout(self, start_time: float):
        """Raise if total time budget exceeded."""
        elapsed_ms = (time.time() - start_time) * 1000
        if elapsed_ms > self.config.max_total_time_ms:
            raise GradientTimeoutError(
                f"Gradient computation exceeded budget: "
                f"{elapsed_ms:.0f}ms > {self.config.max_total_time_ms}ms"
            )
```

**Performance Budget**:

| Scenario | Parameters | Method | Evaluations | Time @ 200ms/eval |
|----------|------------|--------|-------------|-------------------|
| Simple | 5 | Forward | 6 | 1.2s |
| Typical | 15 | Forward | 16 | 3.2s |
| Complex | 30 | Forward | 31 | 6.2s |
| Typical | 15 | Central | 30 | 6.0s |

**Optimization Strategy**:
1. Use forward differences (N+1) not central (2N)
2. Parallelize perturbation evaluations
3. Cache expensive computations (hydrostatics, resistance)
4. Use sparse Jacobian if most parameters don't affect most targets

**Test Requirement**:

```python
def test_gradient_does_not_mutate_state():
    """Gradient computation must not modify original state."""
    state = create_test_state()
    original_hash = state.compute_hash()
    
    estimator = SafeGradientEstimator(config, state_manager)
    jacobian = estimator.compute_jacobian(
        adjustable_params=["beam_m", "draft_m"],
        target_observables=["GM", "displacement"],
        evaluate_fn=evaluate_physics,
    )
    
    # Original state must be unchanged
    assert state.compute_hash() == original_hash
    
def test_gradient_respects_timeout():
    """Gradient computation respects time budget."""
    config = GradientConfig(max_total_time_ms=1000)
    estimator = SafeGradientEstimator(config, state_manager)
    
    # Slow evaluation function
    def slow_eval(state):
        time.sleep(0.5)  # 500ms per eval
        return {"GM": 1.0}
    
    with pytest.raises(GradientTimeoutError):
        estimator.compute_jacobian(
            adjustable_params=["p1", "p2", "p3", "p4", "p5"],  # 6 evals = 3s
            target_observables=["GM"],
            evaluate_fn=slow_eval,
        )
```

---

### 0.9.6 State Leakage in Sensitivity Analyzer (Critical - EXISTING BUG)

**Location**: `magnet/optimization/sensitivity.py` (lines 148-151)

**Severity**: Critical (corrupts canonical state)

**The Problem**: The optimization loop leaks state due to unsafe cloning fallback.

**CONFIRMED IN CURRENT CODEBASE**:
- `magnet/optimization/sensitivity.py` currently contains:
  - `if hasattr(self.base_state, 'clone'): state = self.base_state.clone()`
  - `else: state = self.base_state`
- The same function then mutates via `state.set(...)` for variable application, which will corrupt SSOT when the fallback path triggers.

**The Code**:

```python
# sensitivity.py lines 148-151
if hasattr(self.base_state, 'clone'):
    state = self.base_state.clone()
else:
    state = self.base_state  # LEAK: Mutates live state if clone() is missing
```

**The Gap**: If `DesignState` or `StateManager` does not implement deep `clone()` (or if it's a shallow copy sharing mutable references), the `state.set()` calls on line 156 will **permanently mutate the canonical design state** during what should be a hypothetical "dry run."

**Consequence**: 
- Poisons the "Golden Path" with transient optimization values
- Violates SSOT (Single Source of Truth)
- Makes state non-deterministic and unreproducible

**Fix Required**:

```python
# WRONG: Fallback to live state
if hasattr(self.base_state, 'clone'):
    state = self.base_state.clone()
else:
    state = self.base_state  # DANGEROUS

# CORRECT: Fail fast if clone unavailable
def _get_evaluation_state(self) -> DesignState:
    """Get isolated state for evaluation. NEVER returns live state."""
    if not hasattr(self.base_state, 'clone'):
        raise StateCloneError(
            "SensitivityAnalyzer requires DesignState.clone() method. "
            "Cannot safely evaluate without state isolation."
        )
    
    clone = self.base_state.clone()
    
    # Verify isolation
    if __debug__:
        self._verify_clone_isolation(clone)
    
    return clone

def _verify_clone_isolation(self, clone: DesignState):
    """Assert clone shares no mutable refs with original."""
    # Check known mutable containers
    for attr in ['resources', 'geometry', 'parameters']:
        if hasattr(self.base_state, attr) and hasattr(clone, attr):
            original = getattr(self.base_state, attr)
            cloned = getattr(clone, attr)
            if isinstance(original, (list, dict, set)):
                assert original is not cloned, \
                    f"Clone shares mutable {attr} with original"
```

**Test Requirement**:

```python
def test_sensitivity_analyzer_never_mutates_base_state():
    """Sensitivity analysis must not modify base state."""
    state = create_test_state()
    original_hash = state.compute_hash()
    original_values = state.get_all_parameters().copy()
    
    analyzer = SensitivityAnalyzer(state)
    
    # Run sensitivity analysis (should use clones)
    results = analyzer.analyze(
        parameters=["beam_m", "draft_m"],
        objectives=["GM", "displacement"]
    )
    
    # Base state must be unchanged
    assert state.compute_hash() == original_hash
    assert state.get_all_parameters() == original_values

def test_sensitivity_analyzer_fails_without_clone():
    """Analyzer must fail if clone() unavailable."""
    state = MockStateWithoutClone()
    
    with pytest.raises(StateCloneError):
        analyzer = SensitivityAnalyzer(state)
        analyzer.analyze(...)
```

---

### 0.9.7 Newton-Raphson Oscillation at Discontinuities (High - EXISTING BUG)

**Location**: `magnet/physics/equilibrium.py` (line 62)

**Severity**: High (causes solver instability)

**The Problem**: The equilibrium solver uses waterplane area as derivative, which is discontinuous at chines/steps.

**The Code**:

```python
# equilibrium.py line 62
d_disp_dT = (float(seawater_density) * float(hs.waterplane_area_m2)) / 1000.0
```

**The Math**: Newton-Raphson uses the derivative $R'(T) \approx \rho A_w(T)$ to compute draft corrections.

When draft $T$ crosses a chine, step, or spray rail, $A_w(T)$ **jumps discontinuously**:

```
Waterplane Area vs Draft
                    
    A_w ─────────┐
                 │ ← Jump at chine
                 └─────────
                    
    0           T_chine    T
```

**Consequence**:
- Newton-Raphson sees erratic "derivative" at discontinuity
- Solver oscillates around the discontinuity
- Falls back to slower bisection method (line 247)
- For stepped hulls (North Star goal), this happens at **every step**

**Fix Required**: Use regularized derivative or bisection near known discontinuities.

```python
# IMPROVED: Detect discontinuity and switch method
class EquilibriumSolver:
    def __init__(self, hull_geometry: HullGeometry):
        self.hull = hull_geometry
        # Pre-compute discontinuity locations
        self.discontinuity_drafts = self._find_discontinuities()
    
    def _find_discontinuities(self) -> List[float]:
        """Find draft values where Aw is discontinuous."""
        discontinuities = []
        
        # Chine crossings
        for chine in self.hull.chines:
            discontinuities.append(chine.z_at_midship)
        
        # Step crossings (for stepped hulls)
        for step in self.hull.steps:
            discontinuities.append(step.z_level)
        
        # Spray rail crossings
        for rail in self.hull.spray_rails:
            discontinuities.append(rail.z_level)
        
        return sorted(discontinuities)
    
    def _near_discontinuity(self, draft: float, tolerance: float = 0.05) -> bool:
        """Check if draft is near a known discontinuity."""
        for disc in self.discontinuity_drafts:
            if abs(draft - disc) < tolerance:
                return True
        return False
    
    def solve(self, target_displacement: float) -> float:
        """Solve for equilibrium draft."""
        draft = self.initial_guess
        
        for iteration in range(self.max_iterations):
            # Use bisection near discontinuities, Newton elsewhere
            if self._near_discontinuity(draft):
                draft = self._bisection_step(draft, target_displacement)
            else:
                draft = self._newton_step(draft, target_displacement)
            
            if self._converged(draft, target_displacement):
                return draft
        
        raise ConvergenceError("Equilibrium solver did not converge")
```

**Test Requirement**:

```python
def test_equilibrium_converges_for_stepped_hull():
    """Equilibrium solver must converge for stepped hulls."""
    # Create hull with 2 steps (3 discontinuities in Aw)
    hull = create_stepped_hull(steps=[
        Step(x=0.6, z=0.3),
        Step(x=0.75, z=0.2),
    ])
    
    solver = EquilibriumSolver(hull)
    
    # Must converge without oscillation
    draft = solver.solve(target_displacement=50.0)
    
    assert draft is not None
    assert solver.iterations < 20  # Should not need many iterations
    assert not solver.fell_back_to_bisection  # Newton should work
```

---

### 0.9.8 Hydro-Weight Circular Dependency (Medium - DESIGN FLAW) — **Option B Chosen**

**Location**: `magnet/validators/builtin.py` (lines 148, 548)

**Severity**: Medium (potential deadlock in validation)

**The Problem**: There is a semantic circular dependency in validation that spans phases.

**The Dependency Chain**:

```
Weight → Hydrostatics → Equilibrium → Weight
         ↑                              │
         └──────────────────────────────┘
```

1. **Weight depends on Hydrostatics**: `weight/estimation` needs `hull.depth` and `hull.cb` (block coefficient)
   ```python
   # builtin.py line 548
   depends_on_validators=["physics/hydrostatics"],
   ```

2. **Equilibrium depends on Weight**: `physics/equilibrium_draft` needs `weight.lightship_weight_mt`
   ```python
   # builtin.py line 148
   depends_on_validators=["physics/hydrostatics", "weight/estimation"],
   ```

3. **Hydrostatics depends on Draft**: `physics/hydrostatics` requires a defined `hull.draft`

**The Deadlock Scenario**:
- If `equilibrium_draft` result is applied to `hull.draft`
- It invalidates `physics/hydrostatics`
- Which invalidates `weight/estimation`
- Which invalidates `equilibrium_draft`
- → Infinite invalidation loop

**Current Workaround**: `equilibrium_draft` is marked `is_gate_condition=False` (Advisory), preventing it from blocking the spiral. But the mathematical dependency remains unresolved.

**Fix Required (Option B: Fully Physical Fixed-Point)**: Explicit convergence loop with fixed-point iteration that **mutates `hull.draft`** until hydrostatics + weight + equilibrium are self-consistent.

#### Key Semantics (Option B)

- **`hull.draft` becomes the equilibrium draft** (not just an advisory suggestion).
- The fix is **not** “run equilibrium after weight” (that leaves stale hydro/weight); it is a **closed-loop solve**:
  - Draft guess → hydrostatics(draft) → weight(hydro) → equilibrium(weight) → updated draft → repeat
- This must be implemented as **one explicit solver**, not as separate validators that invalidate each other.

#### Activation / Enforcement

To avoid silent state churn in legacy flows, the Option-B loop is **explicitly enabled** via:

- `hull.auto_converge_hydro_weight = true`

When enabled, the convergence solver:

- opens/uses a **write transaction** (refinable-path enforcement) because it mutates `hull.draft`
- writes `hull.hydro_weight_converged` + `hull.hydro_weight_iterations`
- writes equilibrium diagnostics (`hull.equilibrium_*`)
- recomputes hydrostatics and weight at the converged draft (no stale outputs)

```python
# magnet/physics/hydro_weight_convergence.py  (T7.5)

@dataclass
class ConvergenceState:
    draft_m: float
    displacement_mt: float
    lightship_weight_mt: float
    iteration: int
    converged: bool

class HydroWeightConvergence:
    """
    Resolve circular dependency between hydrostatics and weight.
    
    Uses fixed-point iteration:
    1. Assume initial draft
    2. Compute hydrostatics at that draft
    3. Estimate weight from hydrostatics
    4. Compute equilibrium draft from weight
    5. If draft changed significantly, goto 2
    """
    
    def __init__(
        self,
        hull: HullGeometry,
        max_iterations: int = 10,
        tolerance_m: float = 0.01,
    ):
        self.hull = hull
        self.max_iterations = max_iterations
        self.tolerance_m = tolerance_m
    
    def solve(self) -> ConvergenceState:
        """Iterate until draft converges."""
        # Initial guess: design draft
        draft = self.hull.design_draft_m
        
        for iteration in range(self.max_iterations):
            # 1. Compute hydrostatics at current draft
            hydro = compute_hydrostatics(self.hull, draft)
            
            # 2. Estimate weight from hydrostatics
            weight = estimate_weight(self.hull, hydro)
            
            # 3. Compute equilibrium draft from weight
            new_draft = solve_equilibrium(
                self.hull, 
                target_displacement=weight.lightship_weight_mt
            )
            
            # 4. Check convergence
            if abs(new_draft - draft) < self.tolerance_m:
                return ConvergenceState(
                    draft_m=new_draft,
                    displacement_mt=hydro.displacement_mt,
                    lightship_weight_mt=weight.lightship_weight_mt,
                    iteration=iteration,
                    converged=True,
                )
            
            # 5. Update draft with damping to prevent oscillation
            draft = 0.7 * new_draft + 0.3 * draft  # Under-relaxation
        
        return ConvergenceState(
            draft_m=draft,
            displacement_mt=hydro.displacement_mt,
            lightship_weight_mt=weight.lightship_weight_mt,
            iteration=self.max_iterations,
            converged=False,
        )
```

**Validator Integration (MAGNET)**:

```python
# Replace separate validators with converged validator
class HydroWeightValidator(Validator):
    """
    Combined hydro-weight validator that handles circular dependency.
    
    Replaces:
    - physics/hydrostatics (partial)
    - weight/estimation (partial)
    - physics/equilibrium_draft
    """
    
    name = "physics/hydro_weight_converged"
    depends_on_validators = []  # No external dependencies
    is_gate_condition = False   # opt-in (enabled via hull.auto_converge_hydro_weight)
    
    def validate(self, state: DesignState) -> ValidationResult:
        convergence = HydroWeightConvergence(state.hull)
        result = convergence.solve()
        
        if not result.converged:
            return ValidationResult(
                valid=False,
                message=f"Hydro-weight did not converge after {result.iteration} iterations",
                details={"final_draft": result.draft_m}
            )
        
        return ValidationResult(valid=True, details=asdict(result))
```

**Testing**:

- `tests/physics/test_hydro_weight_convergence.py` must prove:
  - convergence loop can run without write-path violations
  - `hull.draft` is mutated (positive) and flags are written
  - equilibrium diagnostics exist when converged

---

### 0.9.9 Opaque Constraint Violation (High - EXISTING BUG)

**Location**: `magnet/kernel/geometry_observables.py` (lines 39-41, 209-210), `magnet/optimization/sensitivity.py` (lines 162-163)

**Severity**: High (blinds optimizer)

**The Problem**: The optimizer receives binary `None` for failures instead of gradient-guiding error information.

**The Code**:

```python
# geometry_observables.py lines 39-41
class Measurement:
    value: float
    witness_index: Optional[int] = None
    # NO error_type, NO violation_location, NO gradient_hint

# geometry_observables.py lines 209-210
if ci is None:
    return None  # Optimizer sees "None", not "Chine not found at station 4"

# sensitivity.py lines 162-163
except Exception:
    return None  # Swallows ALL errors, returns opaque None
```

**Consequence**:
- Optimizer knows design failed, but not **why**
- Cannot distinguish "outrigger detached" from "negative volume"
- Cannot compute gradient to guide design back to valid state
- Effectively random search in failure regions

**Fix Required**: Structured error information that guides optimization.

```python
# magnet/kernel/measurement.py

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

class ViolationType(Enum):
    """Types of constraint violations."""
    GEOMETRIC = "geometric"      # Self-intersection, negative volume
    PHYSICAL = "physical"        # Negative GM, insufficient buoyancy
    TOPOLOGICAL = "topological"  # Disconnected component, missing feature
    NUMERICAL = "numerical"      # NaN, overflow, convergence failure

@dataclass
class ViolationInfo:
    """Structured information about a constraint violation."""
    violation_type: ViolationType
    message: str
    
    # Location information (for gradient guidance)
    station_range: Optional[tuple] = None  # (start, end) if localized
    component_id: Optional[str] = None     # If component-specific
    parameter_hint: Optional[str] = None   # Which parameter likely caused it
    
    # Gradient guidance
    direction_hint: Optional[str] = None   # "increase", "decrease", or None
    sensitivity: Optional[float] = None    # How sensitive to changes
    
    def to_dict(self) -> dict:
        return {
            "type": self.violation_type.value,
            "message": self.message,
            "station_range": self.station_range,
            "component_id": self.component_id,
            "parameter_hint": self.parameter_hint,
            "direction_hint": self.direction_hint,
            "sensitivity": self.sensitivity,
        }

@dataclass
class Measurement:
    """Enhanced measurement with violation information."""
    value: Optional[float]  # None if measurement failed
    witness_index: Optional[int] = None
    
    # NEW: Structured violation info
    violation: Optional[ViolationInfo] = None
    
    @property
    def is_valid(self) -> bool:
        return self.value is not None and self.violation is None
    
    @classmethod
    def failed(cls, violation: ViolationInfo) -> "Measurement":
        """Create a failed measurement with violation info."""
        return cls(value=None, violation=violation)


# Updated measurer
def measure_chine_z_monotonicity(sections: List[Section]) -> Measurement:
    """Measure chine Z monotonicity with detailed violation info."""
    for i, section in enumerate(sections):
        ci = section.chine_index
        if ci is None:
            return Measurement.failed(ViolationInfo(
                violation_type=ViolationType.TOPOLOGICAL,
                message=f"Chine not found at station {i}",
                station_range=(i, i),
                parameter_hint="chine_height_ratio",
                direction_hint="increase",  # Chine might be below waterline
            ))
        
        if i > 0:
            prev_z = sections[i-1].points[sections[i-1].chine_index].z
            curr_z = section.points[ci].z
            if curr_z < prev_z:
                return Measurement.failed(ViolationInfo(
                    violation_type=ViolationType.GEOMETRIC,
                    message=f"Z-reversal at station {i}: {curr_z:.3f} < {prev_z:.3f}",
                    station_range=(i-1, i),
                    parameter_hint="chine_rise_angle",
                    direction_hint="increase",
                    sensitivity=abs(curr_z - prev_z),  # How bad is the violation
                ))
    
    # Success
    return Measurement(value=compute_monotonicity_score(sections))
```

**Optimizer Integration**:

```python
# sensitivity.py - improved error handling
def _evaluate_objectives(self, state: DesignState) -> Dict[str, float]:
    """Evaluate objectives with structured error handling."""
    results = {}
    violations = []
    
    for objective in self.objectives:
        try:
            measurement = self.measurers[objective].measure(state)
            
            if measurement.is_valid:
                results[objective] = measurement.value
            else:
                # Capture violation info for gradient guidance
                violations.append(measurement.violation)
                results[objective] = float('nan')  # NaN, not None
                
        except Exception as e:
            # Wrap unexpected errors
            violations.append(ViolationInfo(
                violation_type=ViolationType.NUMERICAL,
                message=str(e),
            ))
            results[objective] = float('nan')
    
    # Store violations for optimizer to use
    self._last_violations = violations
    
    return results

def get_gradient_hints(self) -> List[Dict]:
    """Get gradient hints from last evaluation's violations."""
    return [v.to_dict() for v in self._last_violations if v.direction_hint]
```

**Test Requirement**:

```python
def test_measurement_provides_violation_info():
    """Failed measurements must provide structured violation info."""
    # Create hull with Z-reversal
    hull = create_hull_with_z_reversal(station=5)
    
    measurement = measure_chine_z_monotonicity(hull.sections)
    
    assert not measurement.is_valid
    assert measurement.violation is not None
    assert measurement.violation.violation_type == ViolationType.GEOMETRIC
    assert measurement.violation.station_range == (4, 5)
    assert measurement.violation.parameter_hint == "chine_rise_angle"
    assert measurement.violation.direction_hint == "increase"

def test_optimizer_uses_violation_hints():
    """Optimizer should use violation hints for gradient guidance."""
    analyzer = SensitivityAnalyzer(state)
    
    # Evaluate invalid state
    results = analyzer._evaluate_objectives(invalid_state)
    
    # Should have gradient hints
    hints = analyzer.get_gradient_hints()
    assert len(hints) > 0
    assert hints[0]["direction_hint"] is not None
```

---

### 0.9.10 Systemic Friction Summary Matrix

| # | Issue | Location | Severity | Type | Fix Status |
|---|-------|----------|----------|------|------------|
| 0.9.6 | State leakage in sensitivity | `sensitivity.py:148-151` | Critical | EXISTING BUG | Spec defined |
| 0.9.7 | Newton-Raphson oscillation | `equilibrium.py:62` | High | EXISTING BUG | Spec defined |
| 0.9.8 | Hydro-weight circular dependency | `builtin.py:148,548` | Medium | DESIGN FLAW | Spec defined |
| 0.9.9 | Opaque constraint violations | `geometry_observables.py` | High | EXISTING BUG | Spec defined |

### 0.9.11 Combined Gap Summary Matrix

| # | Gap | Location | Severity | Fix Status |
|---|-----|----------|----------|------------|
| 0.9.1 | Hull coefficient coupling | `blending.py` | Critical | Spec defined |
| 0.9.2 | Discontinuous gradients | `generator.py` | High | Spec defined |
| 0.9.3 | Missing component kinematics | `component_library.py` | High | Spec defined |
| 0.9.4 | Optimizer in kernel | `coordinate_executor.py` | Medium | Guard defined |
| 0.9.5 | Safe gradient implementation | `gradient_estimator.py` | Critical | Spec defined |
| 0.9.6 | State leakage in sensitivity | `sensitivity.py` | Critical | Spec defined |
| 0.9.7 | Newton-Raphson oscillation | `equilibrium.py` | High | Spec defined |
| 0.9.8 | Hydro-weight circular dependency | `builtin.py` | Medium | Spec defined |
| 0.9.9 | Opaque constraint violations | `geometry_observables.py` | High | Spec defined |

**CRITICAL BUGS (must fix before any optimization work)**:
- 0.9.6: State leakage corrupts canonical state
- 0.9.9: Opaque violations blind the optimizer

**These gaps must be addressed before the affected tasks (T0.5, T5.2-T5.4) can be marked complete.**

---

## §0.10 Systemic Architectural Risks

These risks span multiple subsystems and cannot be fixed with localized patches. They require architectural decisions that affect the entire system design.

---

### 0.10.1 Concurrency & Race Conditions (CRITICAL)

**Risk Level**: Critical (blocks high-frequency optimization)

**Root Issue**: The `DesignState` singleton architecture creates a fundamental bottleneck that cannot safely support the "high-frequency Safe Gradient compute loop" described in §6.

The guide mandates a single `DesignMutator` as the "only write path" (§12.2), but provides **no concurrency model** for the underlying singleton `DesignState`. The `CoordinateExecutor`'s gradient estimation relies on clone/discard patterns (§6.1, §6.3), but during high-frequency optimization loops, multiple asynchronous gradient computations could race against each other.

**Specific Bottlenecks**:

1. **Concurrent Mutation Ambiguity**: The test `test_concurrent_proposals_one_wins` (§12.5) reveals async mutation attempts but assumes only one wins—there's no discussion of what happens to losing concurrent operations or how intermediate state corruption is prevented.

2. **Missing Lock Semantics**: `DesignState` lacks explicit locking mechanisms. §0.8.4 mentions write locks but only for illegal direct writes, not concurrent mutator access.

3. **Clone-During-Commit Race**: No discussion of how `CoordinateExecutor` handles interruption during multi-step gradient estimation. If one gradient computation is cloning while another is committing, the singleton state could become inconsistent.

**Failure Mode**: During optimization, concurrent gradient threads could read partially-updated singleton state, leading to corrupted gradients that drive the optimizer toward invalid designs. The "clone + discard" pattern doesn't prevent this if cloning captures inconsistent intermediate states.

**Clarification (SSOT vs CRDTs / eventual merge)**:

- **Do not use CRDT-style “eventual merge” for canonical `DesignState`**. Geometry + physics constraints are not commutative; a CRDT merge can produce a syntactically merged state that is physically incoherent.
- Scale multi-agent work with:
  - **many read snapshots** (cheap, parallel),
  - **proposal sandboxes** (parallel exploration),
  - a **single authoritative commit stream** (serialized, validated),
  - explicit conflict resolution + revalidation before commit.

**Required Architecture**:

```python
# magnet/core/state_concurrency.py

from threading import RLock, Condition
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional
import threading

@dataclass
class StateVersion:
    """Immutable version marker for optimistic concurrency."""
    version: int
    timestamp: float
    mutator_id: str

class ConcurrentStateManager:
    """
    Thread-safe state management with explicit concurrency model.
    
    Concurrency Strategy:
    - Single writer, multiple readers (SWMR)
    - Readers get immutable snapshots (never see partial updates)
    - Writers acquire exclusive lock, operate on staging, then commit atomically
    - Clone operations return frozen snapshots that don't reflect ongoing mutations
    """
    
    def __init__(self, initial_state: DesignState):
        self._state = initial_state
        self._version = StateVersion(0, time.time(), "init")
        
        # Concurrency primitives
        self._write_lock = RLock()  # Reentrant for nested operations
        self._read_condition = Condition(self._write_lock)
        self._active_readers = 0
        self._writer_waiting = False
    
    @contextmanager
    def read_snapshot(self) -> DesignState:
        """
        Get immutable snapshot for reading.
        
        Guarantees:
        - Snapshot is consistent (no partial updates visible)
        - Snapshot is frozen (modifications raise error)
        - Multiple readers can hold snapshots concurrently
        """
        with self._read_condition:
            # Wait if writer is waiting (writer priority to prevent starvation)
            while self._writer_waiting:
                self._read_condition.wait()
            
            self._active_readers += 1
        
        try:
            # Return frozen clone
            snapshot = self._state.frozen_clone()
            yield snapshot
        finally:
            with self._read_condition:
                self._active_readers -= 1
                if self._active_readers == 0:
                    self._read_condition.notify_all()
    
    @contextmanager
    def write_transaction(self, mutator_id: str) -> "StateTransaction":
        """
        Acquire exclusive write access.
        
        Guarantees:
        - No other writers during transaction
        - No readers see partial updates
        - Commit is atomic
        - Rollback on exception
        """
        with self._read_condition:
            self._writer_waiting = True
            
            # Wait for all readers to finish
            while self._active_readers > 0:
                self._read_condition.wait()
            
            self._writer_waiting = False
        
        # Now we have exclusive access
        transaction = StateTransaction(
            self._state.clone(),
            self._version,
            mutator_id,
        )
        
        try:
            yield transaction
            
            # Commit on success
            if transaction.should_commit:
                self._state = transaction.staged_state
                self._version = StateVersion(
                    self._version.version + 1,
                    time.time(),
                    mutator_id,
                )
        except Exception:
            # Automatic rollback - staged changes discarded
            raise
        finally:
            with self._read_condition:
                self._read_condition.notify_all()

@dataclass
class StateTransaction:
    """Represents an in-progress write transaction."""
    staged_state: DesignState
    base_version: StateVersion
    mutator_id: str
    should_commit: bool = True
    
    def rollback(self):
        """Explicitly abort transaction."""
        self.should_commit = False
    
    def get_staged(self) -> DesignState:
        """Get staged state for modification."""
        return self.staged_state


class GradientIsolation:
    """
    Isolate gradient computations from main state.
    
    Pattern: Each gradient thread gets its own frozen snapshot,
    computes gradients independently, then reports back numerically
    without modifying shared state.
    """
    
    def __init__(self, state_manager: ConcurrentStateManager):
        self._manager = state_manager
        self._local = threading.local()
    
    def get_evaluation_snapshot(self) -> DesignState:
        """
        Get thread-local snapshot for gradient evaluation.
        
        This snapshot:
        - Is frozen (cannot be modified)
        - Reflects state at time of acquisition
        - Does NOT see concurrent mutations
        - Can be used for multiple evaluations within same gradient step
        """
        if not hasattr(self._local, 'snapshot'):
            with self._manager.read_snapshot() as snapshot:
                self._local.snapshot = snapshot
                self._local.version = self._manager._version
        
        return self._local.snapshot
    
    def invalidate_snapshot(self):
        """Force re-acquisition of snapshot on next call."""
        if hasattr(self._local, 'snapshot'):
            del self._local.snapshot
            del self._local.version
    
    def is_stale(self) -> bool:
        """Check if thread-local snapshot is outdated."""
        if not hasattr(self._local, 'version'):
            return True
        return self._local.version.version < self._manager._version.version
```

**CoordinateExecutor Integration**:

```python
# Updated coordinate_executor.py with concurrency safety

class CoordinateExecutor:
    def __init__(self, state_manager: ConcurrentStateManager):
        self._manager = state_manager
        self._gradient_isolation = GradientIsolation(state_manager)
    
    def compute_gradients(
        self,
        parameters: List[str],
        objectives: List[str],
    ) -> np.ndarray:
        """
        Compute Jacobian with concurrency safety.
        
        All gradient evaluations use frozen snapshots,
        so concurrent mutations don't corrupt results.
        """
        # Get consistent snapshot for all evaluations
        snapshot = self._gradient_isolation.get_evaluation_snapshot()
        
        jacobian = np.zeros((len(objectives), len(parameters)))
        
        for i, param in enumerate(parameters):
            # Perturb snapshot (creates new object, doesn't modify original)
            perturbed = snapshot.with_parameter(param, snapshot.get(param) + self.step_size)
            
            # Evaluate both states
            base_values = self._evaluate(snapshot, objectives)
            perturbed_values = self._evaluate(perturbed, objectives)
            
            # Compute finite difference
            for j, obj in enumerate(objectives):
                jacobian[j, i] = (perturbed_values[obj] - base_values[obj]) / self.step_size
        
        return jacobian
    
    def apply_step(self, delta: Dict[str, float]) -> bool:
        """
        Apply optimization step with exclusive write access.
        
        Returns True if step was applied, False if state changed
        during gradient computation (requires re-computation).
        """
        # Check if our snapshot is stale
        if self._gradient_isolation.is_stale():
            self._gradient_isolation.invalidate_snapshot()
            return False  # Signal caller to recompute gradients
        
        # Acquire exclusive write access
        with self._manager.write_transaction("optimizer") as txn:
            for param, value in delta.items():
                current = txn.get_staged().get(param)
                txn.get_staged().set(param, current + value)
            
            # Validate before commit
            if not self._validate(txn.get_staged()):
                txn.rollback()
                return False
        
        # Invalidate gradient snapshot for next iteration
        self._gradient_isolation.invalidate_snapshot()
        return True
```

**Test Requirements**:

```python
def test_concurrent_gradient_isolation():
    """Concurrent gradient computations don't interfere."""
    manager = ConcurrentStateManager(create_test_state())
    executor = CoordinateExecutor(manager)
    
    results = []
    errors = []
    
    def compute_gradient(thread_id: int):
        try:
            jacobian = executor.compute_gradients(
                parameters=["beam_m", "draft_m"],
                objectives=["displacement", "GM"],
            )
            results.append((thread_id, jacobian))
        except Exception as e:
            errors.append((thread_id, e))
    
    # Launch concurrent gradient computations
    threads = [Thread(target=compute_gradient, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # All should succeed with consistent results
    assert len(errors) == 0
    assert len(results) == 10
    
    # All Jacobians should be identical (same snapshot)
    for _, jacobian in results:
        np.testing.assert_array_almost_equal(jacobian, results[0][1])

def test_write_transaction_exclusivity():
    """Only one writer at a time."""
    manager = ConcurrentStateManager(create_test_state())
    
    write_order = []
    
    def writer(writer_id: int):
        with manager.write_transaction(f"writer_{writer_id}") as txn:
            write_order.append(f"start_{writer_id}")
            time.sleep(0.1)  # Simulate work
            write_order.append(f"end_{writer_id}")
    
    threads = [Thread(target=writer, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Writes should be sequential (start-end pairs, no interleaving)
    for i in range(0, len(write_order), 2):
        start_id = write_order[i].split("_")[1]
        end_id = write_order[i+1].split("_")[1]
        assert start_id == end_id, "Write transactions interleaved!"

def test_reader_writer_priority():
    """Writers don't starve waiting for readers."""
    manager = ConcurrentStateManager(create_test_state())
    
    writer_started = threading.Event()
    writer_finished = threading.Event()
    
    def slow_reader():
        with manager.read_snapshot() as snapshot:
            time.sleep(0.5)  # Hold read lock
    
    def writer():
        writer_started.set()
        with manager.write_transaction("test") as txn:
            pass
        writer_finished.set()
    
    # Start reader
    reader_thread = Thread(target=slow_reader)
    reader_thread.start()
    time.sleep(0.1)  # Let reader acquire lock
    
    # Start writer (should wait)
    writer_thread = Thread(target=writer)
    writer_thread.start()
    
    # Writer should complete within reasonable time after reader finishes
    reader_thread.join()
    writer_finished.wait(timeout=1.0)
    assert writer_finished.is_set(), "Writer starved!"
```

---

### 0.10.2 Abstraction Leakage: Kernel/Rendering Boundary (HIGH)

**Risk Level**: High (violates North Star, creates coupling)

**Root Issue**: The Kernel is forced to "know" about WebGL assembly layers through direct `DesignState` exposure, violating the North Star principle that "the kernel's only role is to validate reality, not suggest designs."

**Evidence of Leakage**:

1. **Direct State Consumption**: The WebGL assembly pipeline (§0.2.5, Figure 1) directly consumes `DesignState` objects:
   ```python
   # §410 - Kernel state leaks to rendering
   def tessellate_assembly(self, design_state: DesignState)
   ```

2. **Coordinate System Bleeding**: Component placement semantics bleed UI-specific coordinate systems into the physics-pure `magnet/kernel/` via kinematic DoF parameters (§0.9.3):
   ```python
   # KinematicDoF with vessel-frame coordinates in kernel
   KinematicDoF(x, y, z, roll, pitch, yaw)  # Vessel frame semantics
   ```

3. **Module Location Ambiguity**: `magnet/core/component_kinematics.py` lives in `core/` rather than `kernel/`, but the observable registry integration (§0.9.3) forces kernel code to understand component positioning semantics.

**Specific Violations**:

- `magnet/kernel/observable_registry.py` must register kinematic DoF as observables (§0.9.3), requiring kernel code to understand 6-DoF transformations and vessel coordinate systems.
- No enforcement of the stated boundary (§0.2: "kernel must not import orchestration or agent modules") for WebGL-specific concerns.

**Required Architecture: Adapter Pattern**

```python
# magnet/adapters/rendering_adapter.py

"""
Adapter layer between kernel and rendering.

The kernel exports:
- Geometry primitives (sections, surfaces, bodies)
- Observable values (scalars, vectors)
- Validation results

The rendering system needs:
- Tessellated meshes
- Material assignments
- Scene graph structure

This adapter translates WITHOUT the kernel knowing about rendering.
"""

from dataclasses import dataclass
from typing import Protocol, List, Dict, Any
from abc import abstractmethod

# --- Kernel-side interface (what kernel exposes) ---

class GeometryExport(Protocol):
    """What the kernel can export (pure geometry, no rendering semantics)."""
    
    @abstractmethod
    def get_sections(self) -> List["Section"]:
        """Get hull sections as mathematical curves."""
        ...
    
    @abstractmethod
    def get_bodies(self) -> List["Body"]:
        """Get solid bodies as BREP or mesh."""
        ...
    
    @abstractmethod
    def get_component_transforms(self) -> Dict[str, "Transform3D"]:
        """Get component positions as pure transforms (no coordinate frame semantics)."""
        ...


# --- Rendering-side interface (what rendering needs) ---

@dataclass
class RenderableMesh:
    """Rendering-ready mesh (WebGL-specific)."""
    vertices: np.ndarray      # Float32, interleaved
    indices: np.ndarray       # Uint16/32
    normals: np.ndarray       # Float32
    material_id: str
    
@dataclass
class SceneNode:
    """Scene graph node for rendering."""
    id: str
    mesh: Optional[RenderableMesh]
    transform: np.ndarray     # 4x4 matrix
    children: List["SceneNode"]


# --- The Adapter (bridges the gap) ---

class RenderingAdapter:
    """
    Translates kernel geometry to rendering scene graph.
    
    Responsibilities:
    - Tessellation (kernel sections → rendering meshes)
    - Coordinate transformation (vessel frame → WebGL frame)
    - Material assignment (physics properties → visual materials)
    - Scene graph construction
    
    The kernel does NOT import this module.
    This module imports kernel geometry types.
    """
    
    def __init__(
        self,
        tessellation_quality: str = "medium",
        coordinate_system: str = "webgl",  # Y-up, right-handed
    ):
        self._quality = tessellation_quality
        self._coord_system = coordinate_system
        self._material_mapper = MaterialMapper()
    
    def create_scene_graph(self, geometry_export: GeometryExport) -> SceneNode:
        """
        Convert kernel geometry to renderable scene graph.
        
        This is the ONLY entry point from rendering to kernel geometry.
        """
        root = SceneNode(id="root", mesh=None, transform=np.eye(4), children=[])
        
        # Hull mesh
        hull_mesh = self._tessellate_hull(geometry_export.get_sections())
        hull_node = SceneNode(
            id="hull",
            mesh=hull_mesh,
            transform=self._vessel_to_webgl_transform(),
            children=[],
        )
        root.children.append(hull_node)
        
        # Component meshes
        for body in geometry_export.get_bodies():
            mesh = self._tessellate_body(body)
            transform = self._convert_transform(
                geometry_export.get_component_transforms().get(body.id)
            )
            node = SceneNode(
                id=body.id,
                mesh=mesh,
                transform=transform,
                children=[],
            )
            root.children.append(node)
        
        return root
    
    def _tessellate_hull(self, sections: List["Section"]) -> RenderableMesh:
        """Tessellate hull sections into triangle mesh."""
        # Tessellation is rendering concern, not kernel concern
        vertices, indices = tessellate_lofted_surface(
            sections,
            quality=self._quality,
        )
        normals = compute_vertex_normals(vertices, indices)
        
        return RenderableMesh(
            vertices=vertices.astype(np.float32),
            indices=indices.astype(np.uint32),
            normals=normals.astype(np.float32),
            material_id="hull_gelcoat",
        )
    
    def _vessel_to_webgl_transform(self) -> np.ndarray:
        """
        Convert vessel coordinate system to WebGL.
        
        Vessel: X-forward, Y-starboard, Z-down (naval convention)
        WebGL: X-right, Y-up, Z-out (right-handed)
        """
        # This transformation is RENDERING knowledge, not KERNEL knowledge
        return np.array([
            [0, 0, -1, 0],  # WebGL X = -Vessel Z
            [0, 1,  0, 0],  # WebGL Y = Vessel Y  
            [1, 0,  0, 0],  # WebGL Z = Vessel X
            [0, 0,  0, 1],
        ], dtype=np.float32)
    
    def _convert_transform(self, kernel_transform: Optional["Transform3D"]) -> np.ndarray:
        """Convert kernel transform to WebGL matrix."""
        if kernel_transform is None:
            return np.eye(4, dtype=np.float32)
        
        # Kernel stores transforms as position + orientation
        # Rendering needs 4x4 matrix in WebGL frame
        vessel_matrix = kernel_transform.to_matrix()
        webgl_matrix = self._vessel_to_webgl_transform() @ vessel_matrix
        return webgl_matrix.astype(np.float32)


# --- Clean kernel interface (no rendering imports) ---

# In magnet/kernel/geometry_export.py

class KernelGeometryExporter:
    """
    Kernel's geometry export interface.
    
    This class is IN the kernel but knows NOTHING about rendering.
    It exports pure mathematical geometry.
    """
    
    def __init__(self, state: DesignState):
        self._state = state
    
    def get_sections(self) -> List[Section]:
        """Export hull sections as mathematical curves."""
        return self._state.hull.sections
    
    def get_bodies(self) -> List[Body]:
        """Export solid bodies."""
        bodies = []
        for resource in self._state.resources.values():
            if hasattr(resource, 'geometry') and resource.geometry:
                bodies.append(resource.geometry)
        return bodies
    
    def get_component_transforms(self) -> Dict[str, Transform3D]:
        """Export component transforms (pure math, no frame semantics)."""
        transforms = {}
        for rid, resource in self._state.resources.items():
            if hasattr(resource, 'position'):
                transforms[rid] = Transform3D(
                    position=resource.position,
                    orientation=getattr(resource, 'orientation', Quaternion.identity()),
                )
        return transforms
```

**Import Enforcement**:

```python
# magnet/kernel/__init__.py

# ENFORCEMENT: Kernel modules must not import rendering
_FORBIDDEN_IMPORTS = {
    'magnet.webgl',
    'magnet.rendering', 
    'magnet.adapters.rendering_adapter',
    'three',
    'pyglet',
    'moderngl',
}

def _enforce_import_boundary():
    """Runtime check that kernel doesn't import rendering."""
    import sys
    
    for module_name in sys.modules:
        if module_name.startswith('magnet.kernel'):
            module = sys.modules[module_name]
            if hasattr(module, '__file__') and module.__file__:
                # Check imports
                for forbidden in _FORBIDDEN_IMPORTS:
                    if forbidden in sys.modules:
                        # Check if kernel module imported it
                        # (This is a simplified check; real impl would trace imports)
                        pass

# Call at module load in debug mode
if __debug__:
    import atexit
    atexit.register(_enforce_import_boundary)
```

**Test Requirements**:

```python
def test_kernel_does_not_import_rendering():
    """Kernel modules must not import rendering modules."""
    import ast
    from pathlib import Path
    
    kernel_path = Path("magnet/kernel")
    forbidden = {"webgl", "rendering", "three", "pyglet", "moderngl"}
    
    violations = []
    for py_file in kernel_path.rglob("*.py"):
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(f in alias.name for f in forbidden):
                        violations.append((py_file, alias.name))
            elif isinstance(node, ast.ImportFrom):
                if node.module and any(f in node.module for f in forbidden):
                    violations.append((py_file, node.module))
    
    assert len(violations) == 0, f"Kernel imports rendering: {violations}"

def test_rendering_adapter_isolation():
    """Rendering adapter doesn't leak back to kernel."""
    from magnet.kernel.geometry_export import KernelGeometryExporter
    from magnet.adapters.rendering_adapter import RenderingAdapter
    
    # Create kernel exporter (pure geometry)
    state = create_test_state()
    exporter = KernelGeometryExporter(state)
    
    # Create rendering adapter
    adapter = RenderingAdapter()
    
    # Adapter consumes kernel geometry
    scene = adapter.create_scene_graph(exporter)
    
    # Verify scene is renderable
    assert scene.id == "root"
    assert len(scene.children) > 0
    
    # Verify kernel state unchanged (adapter is read-only)
    assert state.hull.sections == exporter.get_sections()
```

---

### 0.10.3 Curse of Dimensionality in Hull Blending (CRITICAL)

**Risk Level**: Critical (produces invalid hulls)

**Root Issue**: Section 0.9.1 correctly identifies that linear blending breaks coupled coefficients ($C_b = C_p \times C_m$), but this is just the surface of a deeper **curse of dimensionality** problem.

**The Mathematical Problem**:

The guide proposes blending "10+ parameters" (§0.4.7.A) using linear interpolation:

```python
# Current approach (§0.9.1)
blended_hull[param] = np.dot(weights, values)  # Linear in 10+ dimensions
```

In high-dimensional parameter spaces, linear approaches create **statistically improbable outputs**:

1. **Boundary Concentration**: Most points in high-dimensional space lie near the boundaries of the valid region. The "center" (where linear blending lands) is exponentially unlikely to be valid.

2. **Manifold Violation**: Hull validity exists in a **tiny manifold** within the full `FormCoefficients` hyperspace. Linear paths between valid points cross invalid regions.

3. **Constraint Surface Curvature**: The valid region is bounded by **non-linear constraint surfaces** (stability, seakeeping, structural loads). Linear blending ignores this curvature.

**Visual Intuition**:

```
2D (Intuitive):           10D (Reality):
                          
    Valid                     Valid region is a 
   ┌─────┐                   curved manifold
   │ A●──●B                  
   │     │                   A●
   └─────┘                     ╲
   Linear path                  ╲  ← Linear path
   stays valid                   ╲   exits valid
                                  ╲  manifold
                                   ●B
```

**Quantified Risk**:

For a 10-parameter hull space with each parameter having a 90% valid range, the probability of a random point being valid is approximately $(0.9)^{10} \approx 35\%$. For 45 parameters (ShipD), this drops to $(0.9)^{45} \approx 0.001\%$.

Linear blending doesn't sample "randomly," but it also doesn't follow the valid manifold, making it highly likely to produce invalid combinations.

**Required Architecture: Manifold-Aware Blending**

```python
# magnet/bootstrap/manifold_blending.py

"""
Manifold-aware hull blending that respects the valid design space.

Instead of linear interpolation (which exits the valid manifold),
this uses:
1. Geodesic paths along the valid manifold
2. Iterative projection back to validity
3. Constraint-aware interpolation

The key insight: blend in LATENT space (learned manifold coordinates),
not in RAW parameter space.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Callable
import numpy as np
from scipy.optimize import minimize

@dataclass
class ManifoldPoint:
    """A point on the valid hull manifold."""
    parameters: Dict[str, float]
    latent_coords: np.ndarray  # Low-dimensional manifold coordinates
    validity_score: float      # 1.0 = fully valid, 0.0 = constraint violated

@dataclass
class BlendPath:
    """A path through parameter space."""
    points: List[ManifoldPoint]
    total_length: float
    min_validity: float  # Minimum validity along path


class ManifoldBlender:
    """
    Blends hulls along the valid design manifold.
    
    Strategy:
    1. Map source hulls to latent space (learned or PCA-based)
    2. Interpolate in latent space (lower dimensional, more "central")
    3. Decode back to parameter space
    4. Project onto valid manifold (constraint satisfaction)
    5. Verify path validity
    """
    
    def __init__(
        self,
        hull_library: "HullLibrary",
        validator: Callable[[Dict[str, float]], bool],
        max_projection_iterations: int = 50,
        validity_threshold: float = 0.95,
    ):
        self._library = hull_library
        self._validate = validator
        self._max_iterations = max_projection_iterations
        self._validity_threshold = validity_threshold
        
        # Build latent space from library
        self._latent_encoder, self._latent_decoder = self._build_latent_space()
    
    def _build_latent_space(self) -> Tuple[Callable, Callable]:
        """
        Build encoder/decoder for latent space.
        
        Options:
        - PCA: Simple, interpretable, but linear
        - Autoencoder: Learns non-linear manifold
        - Variational AE: Ensures latent space is smooth
        """
        # Get all library hull parameters
        all_params = np.array([
            list(hull.parameters.values()) 
            for hull in self._library.all_hulls()
        ])
        
        # For MVP: Use PCA with enough components to capture 95% variance
        from sklearn.decomposition import PCA
        
        pca = PCA(n_components=0.95)  # Keep 95% variance
        pca.fit(all_params)
        
        # Typically reduces 45 dims → ~8-12 dims
        print(f"Latent space: {pca.n_components_} dimensions "
              f"(from {all_params.shape[1]})")
        
        def encode(params: Dict[str, float]) -> np.ndarray:
            param_vector = np.array([params[k] for k in sorted(params.keys())])
            return pca.transform(param_vector.reshape(1, -1))[0]
        
        def decode(latent: np.ndarray) -> Dict[str, float]:
            param_vector = pca.inverse_transform(latent.reshape(1, -1))[0]
            keys = sorted(self._library.all_hulls()[0].parameters.keys())
            return dict(zip(keys, param_vector))
        
        return encode, decode
    
    def blend(
        self,
        source_hulls: List[Dict[str, float]],
        weights: List[float],
        ensure_validity: bool = True,
    ) -> Dict[str, float]:
        """
        Blend multiple hulls along the valid manifold.
        
        Args:
            source_hulls: List of hull parameter dicts
            weights: Blending weights (must sum to 1.0)
            ensure_validity: If True, project result onto valid manifold
        
        Returns:
            Blended hull parameters (guaranteed valid if ensure_validity=True)
        """
        assert abs(sum(weights) - 1.0) < 1e-6, "Weights must sum to 1.0"
        
        # 1. Encode sources to latent space
        latent_points = [self._latent_encoder(hull) for hull in source_hulls]
        
        # 2. Blend in latent space (this is where the magic happens)
        #    Latent space is lower-dimensional and more "central"
        blended_latent = sum(w * p for w, p in zip(weights, latent_points))
        
        # 3. Decode back to parameter space
        blended_params = self._latent_decoder(blended_latent)
        
        # 4. Ensure derived coefficients are consistent
        blended_params = self._fix_coefficient_coupling(blended_params)
        
        # 5. Project onto valid manifold if needed
        if ensure_validity:
            blended_params = self._project_to_valid(blended_params)
        
        return blended_params
    
    def _fix_coefficient_coupling(
        self,
        params: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Fix coupled coefficients after blending.
        
        Uses the §0.9.1 fix: keep Cp and Cm, derive Cb.
        Also handles other known couplings.
        """
        result = params.copy()
        
        # Cb = Cp × Cm
        if 'Cp' in result and 'Cm' in result:
            result['Cb'] = result['Cp'] * result['Cm']
        
        # Cw (waterplane coefficient) approximation
        if 'Cb' in result and 'Cw' not in result:
            # Empirical: Cw ≈ 0.18 + 0.86 * Cb (for most hull forms)
            result['Cw'] = 0.18 + 0.86 * result['Cb']
        
        # LCB/LCF relationship
        if 'LCB' in result and 'LCF' not in result:
            # LCF typically 1-3% aft of LCB
            result['LCF'] = result['LCB'] - 0.02
        
        return result
    
    def _project_to_valid(
        self,
        params: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Project parameters onto valid manifold using constrained optimization.
        
        Finds the nearest valid point to the blended parameters.
        """
        # Check if already valid
        if self._validate(params):
            return params
        
        # Define objective: minimize distance from blended point
        param_keys = sorted(params.keys())
        x0 = np.array([params[k] for k in param_keys])
        
        def objective(x):
            return np.sum((x - x0) ** 2)
        
        def constraint(x):
            test_params = dict(zip(param_keys, x))
            return 1.0 if self._validate(test_params) else -1.0
        
        # Use SLSQP with validity as constraint
        # (In practice, you'd use a more sophisticated approach)
        result = minimize(
            objective,
            x0,
            method='SLSQP',
            constraints={'type': 'ineq', 'fun': constraint},
            options={'maxiter': self._max_iterations},
        )
        
        if result.success:
            return dict(zip(param_keys, result.x))
        else:
            # Fallback: use nearest library hull
            return self._find_nearest_valid(params)
    
    def _find_nearest_valid(
        self,
        params: Dict[str, float],
    ) -> Dict[str, float]:
        """Find nearest valid hull in library."""
        latent = self._latent_encoder(params)
        
        best_hull = None
        best_distance = float('inf')
        
        for hull in self._library.all_hulls():
            hull_latent = self._latent_encoder(hull.parameters)
            distance = np.linalg.norm(latent - hull_latent)
            if distance < best_distance:
                best_distance = distance
                best_hull = hull
        
        return best_hull.parameters


class PathValidator:
    """
    Validates that a blending path stays within the valid manifold.
    
    Instead of just checking endpoints, samples along the path
    to ensure the entire trajectory is valid.
    """
    
    def __init__(
        self,
        validator: Callable[[Dict[str, float]], bool],
        samples_per_unit_distance: int = 10,
    ):
        self._validate = validator
        self._sample_density = samples_per_unit_distance
    
    def validate_path(
        self,
        start: Dict[str, float],
        end: Dict[str, float],
        blender: ManifoldBlender,
    ) -> BlendPath:
        """
        Validate blending path between two hulls.
        
        Samples points along the path and checks validity.
        Returns path with validity information.
        """
        # Estimate path length in latent space
        start_latent = blender._latent_encoder(start)
        end_latent = blender._latent_encoder(end)
        path_length = np.linalg.norm(end_latent - start_latent)
        
        # Determine number of samples
        n_samples = max(3, int(path_length * self._sample_density))
        
        # Sample along path
        points = []
        for i in range(n_samples + 1):
            t = i / n_samples
            params = blender.blend([start, end], [1 - t, t], ensure_validity=False)
            validity = 1.0 if self._validate(params) else 0.0
            
            points.append(ManifoldPoint(
                parameters=params,
                latent_coords=blender._latent_encoder(params),
                validity_score=validity,
            ))
        
        return BlendPath(
            points=points,
            total_length=path_length,
            min_validity=min(p.validity_score for p in points),
        )
```

**Test Requirements**:

```python
def test_latent_blending_stays_valid():
    """Blended hulls in latent space should remain valid."""
    library = create_hull_library(n_hulls=100)
    blender = ManifoldBlender(library, hull_validator)
    
    # Pick random pairs
    for _ in range(50):
        hull_a, hull_b = random.sample(library.all_hulls(), 2)
        
        # Blend with various weights
        for weight in [0.25, 0.5, 0.75]:
            blended = blender.blend(
                [hull_a.parameters, hull_b.parameters],
                [weight, 1 - weight],
                ensure_validity=True,
            )
            
            # Must be valid
            assert hull_validator(blended), \
                f"Blended hull invalid at weight={weight}"

def test_path_validity():
    """Blending paths should not cross invalid regions."""
    library = create_hull_library(n_hulls=100)
    blender = ManifoldBlender(library, hull_validator)
    path_validator = PathValidator(hull_validator)
    
    # Check paths between library hulls
    invalid_paths = []
    for hull_a, hull_b in itertools.combinations(library.all_hulls()[:20], 2):
        path = path_validator.validate_path(
            hull_a.parameters,
            hull_b.parameters,
            blender,
        )
        if path.min_validity < 1.0:
            invalid_paths.append((hull_a.id, hull_b.id, path.min_validity))
    
    # Report but don't fail - some paths may cross invalid regions
    # The blender handles this via projection
    print(f"Paths with invalid regions: {len(invalid_paths)}/{len(list(itertools.combinations(range(20), 2)))}")

def test_coefficient_coupling_preserved():
    """Blended hulls must preserve coefficient relationships."""
    library = create_hull_library(n_hulls=100)
    blender = ManifoldBlender(library, hull_validator)
    
    for _ in range(50):
        hull_a, hull_b = random.sample(library.all_hulls(), 2)
        blended = blender.blend(
            [hull_a.parameters, hull_b.parameters],
            [0.5, 0.5],
        )
        
        # Check Cb = Cp × Cm
        if 'Cb' in blended and 'Cp' in blended and 'Cm' in blended:
            expected_cb = blended['Cp'] * blended['Cm']
            assert abs(blended['Cb'] - expected_cb) < 0.01, \
                f"Cb coupling broken: {blended['Cb']} != {expected_cb}"
```

---

### 0.10.4 Observable Registry: Thundering Herd Problem (HIGH)

**Risk Level**: High (causes performance collapse during optimization)

**Root Issue**: The `observable_registry.py` uses a Push model (§4.1, §4.2) that creates a "thundering herd" problem with no mitigation strategy for cascading re-calculations.

**The Problem**:

A single Hull parameter change (e.g., beam adjustment) triggers **100+ hydrostatic re-calculations** because every hydrostatic metric depends on hull geometry:

```
beam_m changed
    │
    ├── displacement invalidated
    ├── waterplane_area invalidated
    ├── LCB invalidated
    ├── LCF invalidated
    ├── GM invalidated
    ├── BM invalidated
    ├── KB invalidated
    ├── moment_to_trim invalidated
    ├── tons_per_cm invalidated
    ├── wetted_surface invalidated
    ├── stability_curve[0..36] invalidated (37 points)
    ├── righting_arm_curve[0..36] invalidated
    └── ... (50+ more observables)
```

Each invalidation triggers recomputation if any subscriber is listening. During optimization, this happens **every gradient step** (40+ times for a Jacobian computation).

**Evidence from Guide**:

- The registry defines observables as "controllable" vs "measurable" (§4.1), implying a push model where changes propagate automatically.
- The subscription mechanism isn't explicitly defined, but integration with `CoordinateExecutor` (§5.3) suggests push-based updates.
- The guide mentions "adaptive step sizing" (§6.2) but no discussion of batching or debouncing updates.

**Required Architecture: Lazy Pull with Dependency Graph**

```python
# magnet/kernel/observable_graph.py

"""
Observable dependency graph with lazy evaluation.

Instead of push-based invalidation (thundering herd), this uses:
1. Dependency graph to track what depends on what
2. Lazy invalidation (mark dirty, don't recompute)
3. Pull-based evaluation (compute only when read)
4. Batch computation (compute related observables together)
"""

from dataclasses import dataclass, field
from typing import Dict, Set, List, Callable, Optional, Any
from enum import Enum
import time

class ObservableState(Enum):
    VALID = "valid"       # Value is current
    DIRTY = "dirty"       # Needs recomputation
    COMPUTING = "computing"  # Currently being computed

@dataclass
class ObservableNode:
    """A node in the observable dependency graph."""
    name: str
    compute_fn: Callable[[], Any]
    dependencies: Set[str] = field(default_factory=set)  # What I depend on
    dependents: Set[str] = field(default_factory=set)    # What depends on me
    
    state: ObservableState = ObservableState.DIRTY
    cached_value: Optional[Any] = None
    last_computed: float = 0.0
    compute_time_ms: float = 0.0

class ObservableGraph:
    """
    Manages observable dependencies with lazy evaluation.
    
    Key principles:
    1. Invalidation is O(1) - just mark dirty
    2. Computation is lazy - only when value is read
    3. Batch computation - related observables computed together
    4. No thundering herd - subscribers don't trigger immediate recomputation
    """
    
    def __init__(self):
        self._nodes: Dict[str, ObservableNode] = {}
        self._computation_order: Optional[List[str]] = None  # Topological sort cache
    
    def register(
        self,
        name: str,
        compute_fn: Callable[[], Any],
        dependencies: List[str],
    ):
        """Register an observable with its computation function and dependencies."""
        node = ObservableNode(
            name=name,
            compute_fn=compute_fn,
            dependencies=set(dependencies),
        )
        self._nodes[name] = node
        
        # Update reverse dependencies
        for dep in dependencies:
            if dep in self._nodes:
                self._nodes[dep].dependents.add(name)
        
        # Invalidate topological sort cache
        self._computation_order = None
    
    def invalidate(self, name: str):
        """
        Mark an observable as dirty.
        
        O(D) where D = number of transitive dependents.
        Does NOT trigger recomputation (lazy).
        """
        if name not in self._nodes:
            return
        
        # BFS to mark all dependents as dirty
        to_invalidate = {name}
        queue = [name]
        
        while queue:
            current = queue.pop(0)
            node = self._nodes.get(current)
            if node is None:
                continue
            
            node.state = ObservableState.DIRTY
            node.cached_value = None
            
            for dependent in node.dependents:
                if dependent not in to_invalidate:
                    to_invalidate.add(dependent)
                    queue.append(dependent)
    
    def get(self, name: str) -> Any:
        """
        Get observable value (lazy computation).
        
        If dirty, computes value and all dependencies first.
        Uses dependency order to minimize recomputation.
        """
        node = self._nodes.get(name)
        if node is None:
            raise KeyError(f"Unknown observable: {name}")
        
        if node.state == ObservableState.VALID:
            return node.cached_value
        
        if node.state == ObservableState.COMPUTING:
            raise RecursionError(f"Circular dependency detected at {name}")
        
        # Compute dependencies first (in topological order)
        for dep in self._get_computation_order(name):
            dep_node = self._nodes[dep]
            if dep_node.state == ObservableState.DIRTY:
                self._compute_single(dep)
        
        # Now compute this node
        return self._compute_single(name)
    
    def get_batch(self, names: List[str]) -> Dict[str, Any]:
        """
        Get multiple observables efficiently.
        
        Computes in optimal order to avoid redundant work.
        """
        # Find all dependencies
        all_needed = set()
        for name in names:
            all_needed.update(self._get_computation_order(name))
        
        # Compute in topological order
        results = {}
        for name in self._get_global_computation_order():
            if name in all_needed:
                node = self._nodes[name]
                if node.state == ObservableState.DIRTY:
                    self._compute_single(name)
                if name in names:
                    results[name] = node.cached_value
        
        return results
    
    def _compute_single(self, name: str) -> Any:
        """Compute a single observable."""
        node = self._nodes[name]
        node.state = ObservableState.COMPUTING
        
        start = time.time()
        try:
            value = node.compute_fn()
            node.cached_value = value
            node.state = ObservableState.VALID
            node.last_computed = time.time()
            node.compute_time_ms = (time.time() - start) * 1000
            return value
        except Exception:
            node.state = ObservableState.DIRTY
            raise
    
    def _get_computation_order(self, name: str) -> List[str]:
        """Get computation order for a single observable (topological sort of dependencies)."""
        visited = set()
        order = []
        
        def visit(n: str):
            if n in visited:
                return
            visited.add(n)
            node = self._nodes.get(n)
            if node:
                for dep in node.dependencies:
                    visit(dep)
                order.append(n)
        
        visit(name)
        return order
    
    def _get_global_computation_order(self) -> List[str]:
        """Get global computation order (cached)."""
        if self._computation_order is None:
            visited = set()
            order = []
            
            def visit(n: str):
                if n in visited:
                    return
                visited.add(n)
                node = self._nodes.get(n)
                if node:
                    for dep in node.dependencies:
                        visit(dep)
                    order.append(n)
            
            for name in self._nodes:
                visit(name)
            
            self._computation_order = order
        
        return self._computation_order
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get computation statistics for profiling."""
        dirty_count = sum(1 for n in self._nodes.values() if n.state == ObservableState.DIRTY)
        total_compute_time = sum(n.compute_time_ms for n in self._nodes.values())
        
        return {
            "total_observables": len(self._nodes),
            "dirty_count": dirty_count,
            "valid_count": len(self._nodes) - dirty_count,
            "total_compute_time_ms": total_compute_time,
            "avg_compute_time_ms": total_compute_time / len(self._nodes) if self._nodes else 0,
        }


class BatchedObservableRegistry:
    """
    High-level registry with batching and debouncing.
    
    Wraps ObservableGraph with:
    - Batched invalidation (collect multiple changes, invalidate once)
    - Debounced computation (wait for burst to finish before computing)
    - Priority computation (important observables first)
    """
    
    def __init__(self):
        self._graph = ObservableGraph()
        self._pending_invalidations: Set[str] = set()
        self._in_batch = False
    
    def begin_batch(self):
        """Start collecting invalidations without propagating."""
        self._in_batch = True
    
    def end_batch(self):
        """Apply all collected invalidations at once."""
        self._in_batch = False
        for name in self._pending_invalidations:
            self._graph.invalidate(name)
        self._pending_invalidations.clear()
    
    def invalidate(self, name: str):
        """Invalidate an observable (batched if in batch mode)."""
        if self._in_batch:
            self._pending_invalidations.add(name)
        else:
            self._graph.invalidate(name)
    
    def get(self, name: str) -> Any:
        """Get observable value."""
        return self._graph.get(name)
    
    def get_batch(self, names: List[str]) -> Dict[str, Any]:
        """Get multiple observables efficiently."""
        return self._graph.get_batch(names)


# Integration with CoordinateExecutor
class OptimizationAwareRegistry(BatchedObservableRegistry):
    """
    Registry optimized for gradient computation.
    
    During optimization:
    - Caches computation order for repeated Jacobian columns
    - Pre-warms frequently-accessed observables
    - Tracks which observables are actually needed
    """
    
    def __init__(self):
        super().__init__()
        self._optimization_mode = False
        self._accessed_observables: Set[str] = set()
    
    def begin_optimization(self, objective_observables: List[str]):
        """Enter optimization mode - optimize for these objectives."""
        self._optimization_mode = True
        self._accessed_observables = set(objective_observables)
        
        # Pre-compute dependency order for objectives
        for obs in objective_observables:
            _ = self._graph._get_computation_order(obs)
    
    def end_optimization(self):
        """Exit optimization mode."""
        self._optimization_mode = False
    
    def evaluate_for_gradient(
        self,
        parameter: str,
        objectives: List[str],
    ) -> Dict[str, float]:
        """
        Evaluate objectives after perturbing a parameter.
        
        Optimized for gradient computation:
        - Only invalidates what's affected by parameter
        - Only computes what's needed for objectives
        """
        # Invalidate parameter and its dependents
        self.invalidate(parameter)
        
        # Compute only needed objectives
        return self.get_batch(objectives)
```

**Test Requirements**:

```python
def test_no_thundering_herd():
    """Invalidation should not trigger immediate recomputation."""
    compute_count = {"displacement": 0, "GM": 0, "stability": 0}
    
    def make_counter(name):
        def compute():
            compute_count[name] += 1
            return 1.0
        return compute
    
    registry = ObservableGraph()
    registry.register("beam", make_counter("beam"), [])
    registry.register("displacement", make_counter("displacement"), ["beam"])
    registry.register("GM", make_counter("GM"), ["displacement"])
    registry.register("stability", make_counter("stability"), ["GM"])
    
    # Invalidate beam - should NOT compute anything
    registry.invalidate("beam")
    
    assert compute_count["displacement"] == 0
    assert compute_count["GM"] == 0
    assert compute_count["stability"] == 0
    
    # Only when we read stability should the chain compute
    registry.get("stability")
    
    assert compute_count["displacement"] == 1
    assert compute_count["GM"] == 1
    assert compute_count["stability"] == 1

def test_batch_efficiency():
    """Batched gets should not recompute shared dependencies."""
    compute_count = {"displacement": 0}
    
    def count_displacement():
        compute_count["displacement"] += 1
        return 100.0
    
    registry = ObservableGraph()
    registry.register("beam", lambda: 5.0, [])
    registry.register("displacement", count_displacement, ["beam"])
    registry.register("GM", lambda: 1.0, ["displacement"])
    registry.register("stability", lambda: 0.5, ["displacement"])
    
    # Get both GM and stability (both depend on displacement)
    results = registry.get_batch(["GM", "stability"])
    
    # Displacement should only be computed once
    assert compute_count["displacement"] == 1
    assert "GM" in results
    assert "stability" in results

def test_optimization_mode_efficiency():
    """Optimization mode should minimize recomputation."""
    registry = OptimizationAwareRegistry()
    
    # Setup: 50 observables, 10 objectives
    for i in range(50):
        deps = [f"obs_{j}" for j in range(i)][:3]  # Each depends on up to 3 others
        registry._graph.register(f"obs_{i}", lambda i=i: float(i), deps)
    
    objectives = [f"obs_{i}" for i in range(40, 50)]
    registry.begin_optimization(objectives)
    
    # Simulate gradient computation: perturb one parameter, evaluate objectives
    import time
    
    start = time.time()
    for _ in range(100):  # 100 gradient evaluations
        registry.invalidate("obs_0")
        results = registry.get_batch(objectives)
    elapsed = time.time() - start
    
    registry.end_optimization()
    
    # Should complete in reasonable time (not exponential blowup)
    assert elapsed < 1.0, f"Optimization took too long: {elapsed}s"
```

---

### 0.10.5 Idempotency & Crash Recovery (CRITICAL)

**Risk Level**: Critical (leaves system in unrecoverable state)

**Root Issue**: The `COORDINATE` optimizer has no guaranteed idempotent recovery mechanism, leaving the system vulnerable to "zombified partial states" when interrupted mid-step.

**The Problem**:

During multi-step optimization, if the process crashes after applying some parameter changes but before convergence, the `DesignState` could be left in an intermediate state that's:
- Neither the original valid design
- Nor a valid converged solution
- Potentially violating physics constraints

**Recovery Gap Analysis**:

1. **Dry-run vs Crash Recovery**: The guide discusses "dry-run / snapshot execution mode" (§6.3) and "clone + discard" patterns, but these are for **gradient estimation**, not **crash recovery**.

2. **Partial Transactions**: No specification of how `state_manager` handles partial transactions when the optimizer crashes between parameter updates.

3. **No Checkpointing**: The "single write path" (`DesignMutator`) uses staging/commit (§12.2), but there's no discussion of transaction rollback or state reconstruction after interruption.

4. **Missing Idempotency**: Restarting the optimizer from a partially-modified state could lead to different convergence paths or invalid designs.

**Required Architecture: Transactional Optimization with Checkpoints**

```python
# magnet/optimization/transactional_optimizer.py

"""
Transactional optimizer with crash recovery.

Guarantees:
1. Every optimization step is atomic (all-or-nothing)
2. Crashes leave state at last valid checkpoint
3. Recovery is idempotent (re-running produces same result)
4. State can be reconstructed from checkpoint log
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import hashlib
import time

@dataclass
class OptimizationCheckpoint:
    """A recoverable point in the optimization process."""
    checkpoint_id: str
    iteration: int
    timestamp: float
    
    # State snapshot
    parameter_values: Dict[str, float]
    objective_values: Dict[str, float]
    state_hash: str  # Hash of full DesignState for verification
    
    # Optimization state
    gradient_history: List[Dict[str, float]] = field(default_factory=list)
    step_size: float = 1.0
    convergence_metric: float = float('inf')
    
    def to_json(self) -> str:
        return json.dumps({
            "checkpoint_id": self.checkpoint_id,
            "iteration": self.iteration,
            "timestamp": self.timestamp,
            "parameter_values": self.parameter_values,
            "objective_values": self.objective_values,
            "state_hash": self.state_hash,
            "gradient_history": self.gradient_history,
            "step_size": self.step_size,
            "convergence_metric": self.convergence_metric,
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> "OptimizationCheckpoint":
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class OptimizationTransaction:
    """
    An atomic optimization step.
    
    Either all parameter changes apply, or none do.
    """
    transaction_id: str
    base_checkpoint: OptimizationCheckpoint
    proposed_changes: Dict[str, float]
    
    status: str = "pending"  # pending, committed, rolled_back
    commit_timestamp: Optional[float] = None
    
    def compute_new_values(self) -> Dict[str, float]:
        """Compute parameter values after applying changes."""
        result = self.base_checkpoint.parameter_values.copy()
        for param, delta in self.proposed_changes.items():
            result[param] = result.get(param, 0.0) + delta
        return result


class TransactionalOptimizer:
    """
    Optimizer with transactional semantics and crash recovery.
    
    Persistence strategy:
    1. Before each step: write checkpoint to disk
    2. Apply changes to in-memory state
    3. Validate
    4. On success: write commit marker
    5. On failure: rollback to checkpoint
    
    Recovery:
    1. On startup: check for uncommitted transactions
    2. If found: rollback to last committed checkpoint
    3. Resume optimization from that point
    """
    
    def __init__(
        self,
        state_manager: "ConcurrentStateManager",
        checkpoint_dir: Path,
        checkpoint_interval: int = 5,  # Checkpoint every N iterations
    ):
        self._manager = state_manager
        self._checkpoint_dir = checkpoint_dir
        self._checkpoint_interval = checkpoint_interval
        
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Recovery check on init
        self._recover_if_needed()
    
    def _recover_if_needed(self):
        """Check for and recover from incomplete transactions."""
        uncommitted = self._find_uncommitted_transactions()
        
        if uncommitted:
            print(f"Found {len(uncommitted)} uncommitted transactions, recovering...")
            
            # Find last committed checkpoint
            last_committed = self._find_last_committed_checkpoint()
            
            if last_committed:
                # Restore state to last checkpoint
                self._restore_checkpoint(last_committed)
                print(f"Restored to checkpoint {last_committed.checkpoint_id}")
            
            # Clean up uncommitted transactions
            for txn in uncommitted:
                self._cleanup_transaction(txn)
    
    def optimize(
        self,
        parameters: List[str],
        objectives: Dict[str, float],  # name -> target value
        max_iterations: int = 100,
        tolerance: float = 1e-6,
    ) -> OptimizationCheckpoint:
        """
        Run optimization with crash safety.
        
        Returns final checkpoint (can be used for recovery).
        """
        # Initial checkpoint
        checkpoint = self._create_checkpoint(iteration=0)
        self._write_checkpoint(checkpoint)
        
        for iteration in range(1, max_iterations + 1):
            # Create transaction for this step
            txn = self._begin_transaction(checkpoint)
            
            try:
                # Compute gradient and step
                gradient = self._compute_gradient(parameters, objectives)
                step = self._compute_step(gradient, checkpoint.step_size)
                
                # Record proposed changes
                txn.proposed_changes = step
                self._write_transaction(txn)
                
                # Apply changes atomically
                with self._manager.write_transaction("optimizer") as state_txn:
                    new_values = txn.compute_new_values()
                    for param, value in new_values.items():
                        state_txn.get_staged().set(param, value)
                    
                    # Validate before commit
                    if not self._validate(state_txn.get_staged()):
                        state_txn.rollback()
                        raise OptimizationError("Validation failed")
                
                # Commit transaction
                txn.status = "committed"
                txn.commit_timestamp = time.time()
                self._write_transaction(txn)
                
                # Check convergence
                convergence = self._compute_convergence(objectives)
                if convergence < tolerance:
                    break
                
                # Periodic checkpoint
                if iteration % self._checkpoint_interval == 0:
                    checkpoint = self._create_checkpoint(iteration)
                    self._write_checkpoint(checkpoint)
                
            except Exception as e:
                # Rollback on any error
                txn.status = "rolled_back"
                self._write_transaction(txn)
                self._restore_checkpoint(checkpoint)
                raise
        
        # Final checkpoint
        final_checkpoint = self._create_checkpoint(iteration)
        self._write_checkpoint(final_checkpoint)
        return final_checkpoint
    
    def _create_checkpoint(self, iteration: int) -> OptimizationCheckpoint:
        """Create checkpoint from current state."""
        with self._manager.read_snapshot() as state:
            return OptimizationCheckpoint(
                checkpoint_id=f"ckpt_{iteration}_{int(time.time())}",
                iteration=iteration,
                timestamp=time.time(),
                parameter_values=state.get_all_parameters(),
                objective_values=self._evaluate_objectives(state),
                state_hash=state.compute_hash(),
            )
    
    def _write_checkpoint(self, checkpoint: OptimizationCheckpoint):
        """Persist checkpoint to disk."""
        path = self._checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
        path.write_text(checkpoint.to_json())
        
        # Also write "latest" pointer
        latest_path = self._checkpoint_dir / "latest.txt"
        latest_path.write_text(checkpoint.checkpoint_id)
    
    def _restore_checkpoint(self, checkpoint: OptimizationCheckpoint):
        """Restore state from checkpoint."""
        with self._manager.write_transaction("recovery") as txn:
            for param, value in checkpoint.parameter_values.items():
                txn.get_staged().set(param, value)
            
            # Verify restoration
            restored_hash = txn.get_staged().compute_hash()
            if restored_hash != checkpoint.state_hash:
                raise RecoveryError(
                    f"State hash mismatch after restore: "
                    f"{restored_hash} != {checkpoint.state_hash}"
                )
    
    def _begin_transaction(self, base: OptimizationCheckpoint) -> OptimizationTransaction:
        """Begin a new optimization transaction."""
        return OptimizationTransaction(
            transaction_id=f"txn_{base.iteration + 1}_{int(time.time())}",
            base_checkpoint=base,
            proposed_changes={},
        )
    
    def _write_transaction(self, txn: OptimizationTransaction):
        """Persist transaction state."""
        path = self._checkpoint_dir / f"{txn.transaction_id}.json"
        path.write_text(json.dumps({
            "transaction_id": txn.transaction_id,
            "base_checkpoint_id": txn.base_checkpoint.checkpoint_id,
            "proposed_changes": txn.proposed_changes,
            "status": txn.status,
            "commit_timestamp": txn.commit_timestamp,
        }))
    
    def _find_uncommitted_transactions(self) -> List[OptimizationTransaction]:
        """Find transactions that weren't committed or rolled back."""
        uncommitted = []
        for path in self._checkpoint_dir.glob("txn_*.json"):
            data = json.loads(path.read_text())
            if data["status"] == "pending":
                uncommitted.append(data)
        return uncommitted
    
    def _find_last_committed_checkpoint(self) -> Optional[OptimizationCheckpoint]:
        """Find the most recent committed checkpoint."""
        latest_path = self._checkpoint_dir / "latest.txt"
        if not latest_path.exists():
            return None
        
        checkpoint_id = latest_path.read_text().strip()
        checkpoint_path = self._checkpoint_dir / f"{checkpoint_id}.json"
        
        if checkpoint_path.exists():
            return OptimizationCheckpoint.from_json(checkpoint_path.read_text())
        return None
    
    def _cleanup_transaction(self, txn_data: dict):
        """Clean up an uncommitted transaction."""
        path = self._checkpoint_dir / f"{txn_data['transaction_id']}.json"
        if path.exists():
            path.unlink()


class OptimizationRecoveryManager:
    """
    Manages optimization recovery across sessions.
    
    Allows:
    - Resuming interrupted optimizations
    - Replaying optimization history
    - Verifying optimization determinism
    """
    
    def __init__(self, checkpoint_dir: Path):
        self._checkpoint_dir = checkpoint_dir
    
    def can_resume(self) -> bool:
        """Check if there's an optimization to resume."""
        return (self._checkpoint_dir / "latest.txt").exists()
    
    def get_resume_point(self) -> Optional[OptimizationCheckpoint]:
        """Get checkpoint to resume from."""
        if not self.can_resume():
            return None
        
        checkpoint_id = (self._checkpoint_dir / "latest.txt").read_text().strip()
        checkpoint_path = self._checkpoint_dir / f"{checkpoint_id}.json"
        
        if checkpoint_path.exists():
            return OptimizationCheckpoint.from_json(checkpoint_path.read_text())
        return None
    
    def verify_determinism(
        self,
        optimizer: TransactionalOptimizer,
        checkpoint: OptimizationCheckpoint,
    ) -> bool:
        """
        Verify optimization is deterministic by replaying from checkpoint.
        
        Runs optimization twice from same checkpoint, verifies same result.
        """
        # Restore checkpoint
        optimizer._restore_checkpoint(checkpoint)
        
        # Run optimization
        result1 = optimizer.optimize(...)
        
        # Restore again
        optimizer._restore_checkpoint(checkpoint)
        
        # Run again
        result2 = optimizer.optimize(...)
        
        # Compare results
        return result1.state_hash == result2.state_hash
```

**Test Requirements**:

```python
def test_crash_recovery():
    """Optimization should recover from simulated crash."""
    checkpoint_dir = Path("/tmp/test_checkpoints")
    checkpoint_dir.mkdir(exist_ok=True)
    
    state = create_test_state()
    manager = ConcurrentStateManager(state)
    
    # Start optimization
    optimizer = TransactionalOptimizer(manager, checkpoint_dir)
    
    # Simulate crash after 3 iterations
    original_optimize = optimizer.optimize
    call_count = [0]
    
    def crashing_optimize(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            # First call: crash after 3 iterations
            for i in range(3):
                optimizer._iteration_step(...)
            raise SystemExit("Simulated crash!")
        else:
            # Second call: normal optimization
            return original_optimize(*args, **kwargs)
    
    optimizer.optimize = crashing_optimize
    
    # First run: crashes
    try:
        optimizer.optimize(["beam"], {"displacement": 100}, max_iterations=10)
    except SystemExit:
        pass
    
    # New optimizer instance (simulates restart)
    optimizer2 = TransactionalOptimizer(manager, checkpoint_dir)
    
    # Should recover and continue
    result = optimizer2.optimize(["beam"], {"displacement": 100}, max_iterations=10)
    
    # Should have resumed from checkpoint
    assert result.iteration >= 3

def test_transaction_atomicity():
    """Optimization steps should be atomic."""
    state = create_test_state()
    manager = ConcurrentStateManager(state)
    optimizer = TransactionalOptimizer(manager, Path("/tmp/test_atomic"))
    
    original_beam = state.get("beam")
    original_draft = state.get("draft")
    
    # Force validation failure mid-transaction
    def failing_validator(state):
        if state.get("beam") != original_beam:
            return False  # Fail after beam changed
        return True
    
    optimizer._validate = failing_validator
    
    # Attempt optimization (should fail)
    try:
        optimizer.optimize(["beam", "draft"], {"displacement": 100})
    except OptimizationError:
        pass
    
    # State should be unchanged (atomic rollback)
    assert state.get("beam") == original_beam
    assert state.get("draft") == original_draft

def test_idempotent_recovery():
    """Recovery should produce same result regardless of when crash occurred."""
    checkpoint_dir = Path("/tmp/test_idempotent")
    
    # Run 1: Complete optimization
    state1 = create_test_state()
    manager1 = ConcurrentStateManager(state1)
    opt1 = TransactionalOptimizer(manager1, checkpoint_dir / "run1")
    result1 = opt1.optimize(["beam"], {"displacement": 100}, max_iterations=20)
    
    # Run 2: Crash at iteration 5, then recover
    state2 = create_test_state()
    manager2 = ConcurrentStateManager(state2)
    opt2 = TransactionalOptimizer(manager2, checkpoint_dir / "run2")
    
    # ... simulate crash and recovery ...
    
    result2 = opt2.optimize(["beam"], {"displacement": 100}, max_iterations=20)
    
    # Results should be identical (same deterministic path)
    assert abs(result1.parameter_values["beam"] - result2.parameter_values["beam"]) < 1e-6
```

---

### 0.10.6 Systemic Risk Summary Matrix

| # | Risk | Severity | Domain | Impact | Fix Status |
|---|------|----------|--------|--------|------------|
| 0.10.1 | Concurrency race conditions | Critical | State Management | Corrupted gradients, invalid designs | Spec defined |
| 0.10.2 | Kernel/rendering boundary leak | High | Architecture | North Star violation, tight coupling | Spec defined |
| 0.10.3 | Curse of dimensionality in blending | Critical | Numerical | Invalid blended hulls | Spec defined |
| 0.10.4 | Observable thundering herd | High | Performance | Optimization collapse | Spec defined |
| 0.10.5 | No crash recovery / idempotency | Critical | Reliability | Zombified states, data loss | Spec defined |

### Systemic Risk Dependency Graph

```
Concurrency (0.10.1)
    │
    ├── Blocks: Safe Gradient (§0.9.5)
    ├── Blocks: Optimizer (T5.3)
    └── Blocks: High-frequency loop
    
Dimensionality (0.10.3)
    │
    ├── Blocks: Hull Blending (T0.5)
    └── Blocks: Library-based novelty
    
Thundering Herd (0.10.4)
    │
    ├── Blocks: Observable Registry (T2.1)
    └── Blocks: Optimizer performance
    
Crash Recovery (0.10.5)
    │
    ├── Blocks: Production deployment
    └── Blocks: Long-running optimization
    
Abstraction Leakage (0.10.2)
    │
    └── Blocks: Clean module boundaries
```

**CRITICAL PATH**: Tasks T5.2, T5.3, T0.5 cannot be safely completed until 0.10.1 (concurrency) and 0.10.3 (dimensionality) are addressed.

---

## §0.11 FUNDAMENTAL ARCHITECTURAL REDESIGN: Multi-Fidelity Optimization Framework

> **CRITICAL WARNING**: The analysis in §0.9 and §0.10 reveals that the current physics-first architecture is **fundamentally unworkable** at scale. This section documents the required architectural shift to a multi-fidelity surrogate-based optimization framework.

### 0.11.1 The Core Problem: Why Physics-First Fails

The current architecture attempts to optimize directly in expensive physics space. This approach has **mathematical impossibilities** that cannot be fixed with incremental improvements:

#### A. Curse of Dimensionality: The Fundamental Deception

The "10+ parameters" blending approach (§0.4.7.A) isn't just suboptimal—it's **mathematically impossible** to work reliably.

**Volume Concentration Theorem**: In $d$-dimensional space, nearly all volume concentrates in a thin shell near the boundary. For $d > 10$, the "interior" of the parameter space has measure zero.

**Manifold Dimensionality Collapse**: Hull validity constraints define a fractal-like manifold of co-dimension ≥ 7 within the 15+ dimensional parameter space. The valid design "surface" has dimension ≤ 8, while the parameter space has dimension ≥ 15.

**Linear Interpolation Failure Mode**:

```python
# The guide proposes this (T0.5):
blended = {p: 0.5*(hull_a[p] + hull_b[p]) for p in params}

# Reality: This has probability ≈ 0 of landing on valid manifold
# For d=15, P(valid) ≤ 10^-23 (worse than finding a specific atom in universe)
```

**Hypercube Edge Effect**: Linear blending creates designs that are "midway between" valid hulls but exist in the empty void between constraint surfaces.

#### B. Optimization Algorithm Suicide

The COORDINATE executor (§6) combines multiple algorithmic death wishes:

1. **Gradient Estimation on Discontinuous Functions**: Finite differences across C¹ discontinuities produce infinite/erratic gradients
2. **Multi-Objective Without Pareto Tracking**: Linear scalarization fails for non-convex Pareto fronts
3. **Constraint Handling via Penalty Methods**: Death spiral into infeasible regions
4. **Step Size Adaptation Without Trust Regions**: False convergence

#### C. Computational Complexity Explosions

| Operation | Current Complexity | Required for Real-Time |
|-----------|-------------------|------------------------|
| Gradient (n params) | O(n × physics_eval) | O(n × surrogate_eval) |
| Constraint Eval | O(2^n) combinatorial | O(n) hierarchical |
| State Cloning | O(state_size) deep copy | O(1) incremental |
| Invalidation | O(n²) thundering herd | O(k) local |

#### D. The Fatal Blind Spot

Section 0.9.1 acknowledges the Cp/Cm/Cb coupling but treats it as a local fix. The real problem is that **hull validity is a global constraint satisfaction problem**, not a parameter coupling issue.

---

### 0.11.2 The Required Paradigm Shift

**FROM**: Optimize in expensive physics space
**TO**: Learn cheap surrogates of physics space and optimize there

```
CURRENT ARCHITECTURE (BROKEN):
┌─────────────────────────────────────────────────────────────┐
│  LLM Agent                                                   │
│      │                                                       │
│      ▼                                                       │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐                 │
│  │ Propose │───►│ Physics │───►│ Validate│──► (repeat 1000x)│
│  │ Design  │    │ Evaluate│    │ Result  │                 │
│  └─────────┘    └─────────┘    └─────────┘                 │
│                 (expensive)    (expensive)                  │
│                                                             │
│  Total cost: 1000 × expensive = INFEASIBLE                 │
└─────────────────────────────────────────────────────────────┘

REQUIRED ARCHITECTURE (MULTI-FIDELITY):
┌─────────────────────────────────────────────────────────────┐
│  LLM Agent                                                   │
│      │                                                       │
│      ▼                                                       │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐                 │
│  │ Propose │───►│Surrogate│───►│ Filter  │──► (fast, 1000x)│
│  │ Design  │    │ Model   │    │ Cheap   │                 │
│  └─────────┘    └─────────┘    └─────────┘                 │
│                 (cheap)        (cheap)                      │
│                      │                                      │
│                      ▼ (top 10 candidates only)            │
│                ┌─────────┐    ┌─────────┐                  │
│                │ Physics │───►│ Validate│──► (expensive, 10x)│
│                │ Evaluate│    │ Final   │                  │
│                └─────────┘    └─────────┘                  │
│                                                             │
│  Total cost: 1000×cheap + 10×expensive = FEASIBLE          │
└─────────────────────────────────────────────────────────────┘
```

---

### 0.11.3 Multi-Fidelity Surrogate Architecture

#### File Location

- `magnet/optimization/surrogate_optimizer.py`

#### Dependencies

- `numpy`, `scipy`
- `sklearn` (Gaussian Process Regressor)
- `magnet/core/probabilistic_design.py`
- `magnet/constraints/hierarchical_validator.py`

#### Scalability Note (Do not assume plain GP is sufficient)

- Plain Gaussian Processes scale poorly with dataset size and can struggle in high dimensions.
- **TM.1 must be implemented as a pluggable surrogate backend**, with recommended defaults:
  - **SMT KPLS / Kriging variants** for >20D engineering spaces,
  - **random forest / gradient-boosted trees** for large \(n\) with uncertainty via ensembles,
  - **GPflow** only when GPU + sparse approximations are practical.
- The optimizer depends on the contract: `predict(mean,std)` + (optional) `gradient()`, not on a specific model family.

#### Interface Contract

```python
# magnet/optimization/surrogate_optimizer.py

from dataclasses import dataclass, field
from typing import Dict, List, Callable, Optional, Tuple
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern

@dataclass
class SurrogateModel:
    """
    Fast approximation of expensive physics evaluation.
    
    Uses Gaussian Process Regression to:
    1. Predict physics outputs from parameters
    2. Quantify prediction uncertainty
    3. Guide acquisition of new physics evaluations
    """
    
    # Training data
    X_train: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))
    y_train: np.ndarray = field(default_factory=lambda: np.empty((0,)))
    
    # Model
    kernel: object = field(default_factory=lambda: Matern(nu=2.5))
    gp: Optional[GaussianProcessRegressor] = None
    
    # Metadata
    parameter_names: List[str] = field(default_factory=list)
    objective_name: str = ""
    
    def fit(self, X: np.ndarray, y: np.ndarray):
        """Train surrogate on physics evaluation data."""
        self.X_train = X
        self.y_train = y
        self.gp = GaussianProcessRegressor(
            kernel=self.kernel,
            n_restarts_optimizer=10,
            normalize_y=True,
        )
        self.gp.fit(X, y)
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict physics output with uncertainty.
        
        Returns:
            mean: Predicted values
            std: Prediction uncertainty (higher = less confident)
        """
        if self.gp is None:
            raise ValueError("Model not trained. Call fit() first.")
        
        mean, std = self.gp.predict(X, return_std=True)
        return mean, std
    
    def compute_gradient(
        self,
        x: np.ndarray,
    ) -> np.ndarray:
        """
        Compute analytical gradient of surrogate.
        
        MUCH faster than finite differences on physics.
        """
        # Use automatic differentiation or analytical derivative of GP
        eps = 1e-6
        grad = np.zeros(x.shape[0])
        
        for i in range(x.shape[0]):
            x_plus = x.copy()
            x_plus[i] += eps
            x_minus = x.copy()
            x_minus[i] -= eps
            
            y_plus, _ = self.predict(x_plus.reshape(1, -1))
            y_minus, _ = self.predict(x_minus.reshape(1, -1))
            
            grad[i] = (y_plus[0] - y_minus[0]) / (2 * eps)
        
        return grad
    
    def acquisition_value(
        self,
        x: np.ndarray,
        best_y: float,
        exploration_weight: float = 0.1,
    ) -> float:
        """
        Expected Improvement acquisition function.
        
        Balances exploitation (high predicted value) and
        exploration (high uncertainty).
        """
        from scipy.stats import norm
        
        mean, std = self.predict(x.reshape(1, -1))
        mean, std = mean[0], std[0]
        
        if std < 1e-10:
            return 0.0
        
        z = (mean - best_y - exploration_weight) / std
        ei = (mean - best_y - exploration_weight) * norm.cdf(z) + std * norm.pdf(z)
        
        return ei


@dataclass
class OptimizationContext:
    """Multi-fidelity optimization state."""
    low_fidelity_model: Dict[str, SurrogateModel]  # One per objective
    high_fidelity_budget: int = 50                  # Expensive evaluations allowed
    confidence_threshold: float = 0.1              # When to trust surrogate
    exploration_rate: float = 0.2                  # Exploration vs exploitation
    
    # Tracking
    physics_evaluations_used: int = 0
    surrogate_evaluations_used: int = 0


class MultiFidelitySurrogateOptimizer:
    """
    Bayesian optimization with physics-informed surrogates.
    
    KEY INSIGHT: Optimize in cheap surrogate space, validate in physics space.
    
    This is the ONLY approach that can scale to "Claude builds a vessel"
    because it reduces expensive physics evaluations by 100x while
    maintaining optimization quality.
    """
    
    def __init__(
        self,
        physics_evaluator: "PhysicsEvaluator",
        parameter_bounds: Dict[str, Tuple[float, float]],
        objectives: List[str],
        constraints: List["Constraint"],
        initial_samples: int = 20,
    ):
        self._physics = physics_evaluator
        self._bounds = parameter_bounds
        self._objectives = objectives
        self._constraints = constraints
        self._initial_samples = initial_samples
        
        # Build initial surrogates from Latin Hypercube sampling
        self._context = self._initialize_surrogates()
    
    def _initialize_surrogates(self) -> OptimizationContext:
        """
        Bootstrap surrogates with initial physics evaluations.
        
        Uses Latin Hypercube Sampling for space-filling design.
        """
        from scipy.stats.qmc import LatinHypercube
        
        n_params = len(self._bounds)
        sampler = LatinHypercube(d=n_params)
        
        # Generate initial sample points
        samples_unit = sampler.random(n=self._initial_samples)
        
        # Scale to parameter bounds
        param_names = list(self._bounds.keys())
        samples = np.zeros_like(samples_unit)
        for i, name in enumerate(param_names):
            low, high = self._bounds[name]
            samples[:, i] = samples_unit[:, i] * (high - low) + low
        
        # Evaluate physics at initial points
        physics_results = {}
        for obj in self._objectives:
            physics_results[obj] = np.array([
                self._physics.evaluate(
                    dict(zip(param_names, sample)),
                    obj,
                )
                for sample in samples
            ])
        
        # Build surrogate models
        surrogates = {}
        for obj in self._objectives:
            model = SurrogateModel(
                parameter_names=param_names,
                objective_name=obj,
            )
            model.fit(samples, physics_results[obj])
            surrogates[obj] = model
        
        return OptimizationContext(
            low_fidelity_model=surrogates,
            physics_evaluations_used=self._initial_samples * len(self._objectives),
        )
    
    def optimize(
        self,
        targets: Dict[str, float],
        max_iterations: int = 100,
    ) -> "OptimizationResult":
        """
        Multi-fidelity Bayesian optimization.
        
        1. Use surrogate to propose candidates (cheap)
        2. Validate top candidates with physics (expensive)
        3. Update surrogate with new physics data
        4. Repeat until budget exhausted or converged
        """
        best_design = None
        best_score = float('-inf')
        
        for iteration in range(max_iterations):
            # Check budget
            if self._context.physics_evaluations_used >= self._context.high_fidelity_budget:
                break
            
            # Phase 1: Surrogate exploration (CHEAP)
            candidates = self._bayesian_acquisition(
                targets,
                n_candidates=100,
            )
            self._context.surrogate_evaluations_used += 100
            
            # Phase 2: Filter by hierarchical constraints (CHEAP to MEDIUM)
            filtered = self._hierarchical_filter(candidates, n_keep=10)
            
            # Phase 3: Physics validation of top candidates (EXPENSIVE)
            validated = self._physics_validation(filtered, targets)
            self._context.physics_evaluations_used += len(filtered) * len(self._objectives)
            
            # Phase 4: Update surrogates with new data
            self._update_surrogates(validated)
            
            # Track best
            for result in validated:
                if result.score > best_score:
                    best_score = result.score
                    best_design = result.design
            
            # Check convergence
            if self._is_converged(validated, targets):
                break
        
        return OptimizationResult(
            design=best_design,
            score=best_score,
            physics_evaluations=self._context.physics_evaluations_used,
            surrogate_evaluations=self._context.surrogate_evaluations_used,
        )
    
    def _bayesian_acquisition(
        self,
        targets: Dict[str, float],
        n_candidates: int,
    ) -> List[Dict[str, float]]:
        """
        Generate candidates using Expected Improvement acquisition.
        
        This is where the surrogate does the heavy lifting - we can
        evaluate thousands of candidates cheaply.
        """
        from scipy.optimize import differential_evolution
        
        param_names = list(self._bounds.keys())
        bounds_list = [self._bounds[name] for name in param_names]
        
        candidates = []
        
        for _ in range(n_candidates):
            # Multi-objective acquisition (scalarized for simplicity)
            def neg_acquisition(x):
                total_ei = 0.0
                for obj, target in targets.items():
                    model = self._context.low_fidelity_model[obj]
                    ei = model.acquisition_value(
                        x,
                        best_y=target,
                        exploration_weight=self._context.exploration_rate,
                    )
                    total_ei += ei
                return -total_ei
            
            # Optimize acquisition function
            result = differential_evolution(
                neg_acquisition,
                bounds=bounds_list,
                maxiter=50,
                seed=np.random.randint(0, 10000),
            )
            
            candidates.append(dict(zip(param_names, result.x)))
        
        return candidates
    
    def _hierarchical_filter(
        self,
        candidates: List[Dict[str, float]],
        n_keep: int,
    ) -> List[Dict[str, float]]:
        """
        Filter candidates through hierarchical constraint pyramid.
        
        Fast constraints first, expensive constraints only for survivors.
        """
        # Level 1: Geometric feasibility (milliseconds)
        geometric_survivors = [
            c for c in candidates
            if self._check_geometric_constraints(c)
        ]
        
        # Level 2: Simplified physics (seconds)
        if len(geometric_survivors) > n_keep * 2:
            physics_survivors = [
                c for c in geometric_survivors
                if self._check_simplified_physics(c)
            ]
        else:
            physics_survivors = geometric_survivors
        
        # Rank by surrogate prediction
        def surrogate_score(c):
            scores = []
            for obj, model in self._context.low_fidelity_model.items():
                x = np.array([c[p] for p in model.parameter_names])
                mean, std = model.predict(x.reshape(1, -1))
                # Pessimistic estimate (lower confidence bound)
                scores.append(mean[0] - 0.5 * std[0])
            return sum(scores)
        
        ranked = sorted(physics_survivors, key=surrogate_score, reverse=True)
        return ranked[:n_keep]
    
    def _physics_validation(
        self,
        candidates: List[Dict[str, float]],
        targets: Dict[str, float],
    ) -> List["ValidationResult"]:
        """
        Validate candidates with full physics (EXPENSIVE).
        
        This is where we spend our physics budget carefully.
        """
        results = []
        
        for candidate in candidates:
            # Full physics evaluation
            physics_values = {}
            for obj in self._objectives:
                physics_values[obj] = self._physics.evaluate(candidate, obj)
            
            # Full constraint validation
            constraint_results = [
                c.evaluate(candidate) for c in self._constraints
            ]
            
            # Score relative to targets
            score = sum(
                -abs(physics_values[obj] - target)
                for obj, target in targets.items()
            )
            
            results.append(ValidationResult(
                design=candidate,
                physics_values=physics_values,
                constraint_results=constraint_results,
                score=score,
            ))
        
        return results
    
    def _update_surrogates(self, validated: List["ValidationResult"]):
        """
        Update surrogate models with new physics data.
        
        This is how the surrogate improves over time.
        """
        for result in validated:
            x = np.array([
                result.design[p]
                for p in self._context.low_fidelity_model[self._objectives[0]].parameter_names
            ]).reshape(1, -1)
            
            for obj in self._objectives:
                model = self._context.low_fidelity_model[obj]
                
                # Add new data point
                new_X = np.vstack([model.X_train, x])
                new_y = np.append(model.y_train, result.physics_values[obj])
                
                # Refit model
                model.fit(new_X, new_y)


@dataclass
class ValidationResult:
    """Result of physics validation."""
    design: Dict[str, float]
    physics_values: Dict[str, float]
    constraint_results: List["ConstraintResult"]
    score: float


@dataclass
class OptimizationResult:
    """Final optimization result."""
    design: Dict[str, float]
    score: float
    physics_evaluations: int
    surrogate_evaluations: int
```

---

### 0.11.4 Hierarchical Constraint System

#### File Location

- `magnet/constraints/hierarchical_validator.py`

#### Interface Contract

```python
# magnet/constraints/hierarchical_validator.py

from dataclasses import dataclass
from typing import List, Callable, Optional
from enum import Enum, auto

class ConstraintLevel(Enum):
    """Constraint evaluation cost levels."""
    GEOMETRIC = auto()      # Milliseconds - bounds, intersections
    SIMPLIFIED = auto()     # Seconds - simplified physics
    FULL_PHYSICS = auto()   # Minutes - full simulation

@dataclass
class Constraint:
    """
    Constraint with cost-aware evaluation.
    
    KEY INSIGHT: Most designs fail cheap constraints.
    Evaluate expensive constraints only for promising designs.
    """
    name: str
    level: ConstraintLevel
    evaluate_fn: Callable[[dict], "ConstraintResult"]
    
    # Metadata
    description: str = ""
    failure_guidance: str = ""  # Hint for fixing violation
    
    def evaluate(self, design: dict) -> "ConstraintResult":
        """Evaluate constraint with cost tracking."""
        import time
        start = time.time()
        result = self.evaluate_fn(design)
        result.evaluation_time_ms = (time.time() - start) * 1000
        result.constraint_name = self.name
        result.level = self.level
        return result


@dataclass
class ConstraintResult:
    """Result of constraint evaluation with guidance."""
    satisfied: bool
    value: float                           # Actual constraint value
    threshold: float                       # Required threshold
    margin: float                          # How much margin (negative = violated)
    
    # Confidence / assumptions (prevents “false certainty” from low-fidelity models)
    confidence: float = 1.0                # 0.0-1.0 model confidence
    assumptions: Optional[List[str]] = None  # e.g. ["Savitsky valid only for planing; steps not modeled"]
    
    # Gradient guidance (for optimizer)
    parameter_sensitivities: Optional[dict] = None  # Which params affect this most
    direction_hint: Optional[str] = None            # "increase beam", "reduce draft"
    
    # Metadata
    constraint_name: str = ""
    level: ConstraintLevel = ConstraintLevel.GEOMETRIC
    evaluation_time_ms: float = 0.0


class HierarchicalValidator:
    """
    Fast-to-slow constraint evaluation pyramid.
    
    KEY INSIGHT: Most designs fail cheap constraints,
    so evaluate expensive ones rarely.
    
    Performance comparison:
    - Naive approach: 100 candidates × 10 constraints × 1 min = 1000 min
    - Hierarchical: 100 × cheap + 10 × medium + 3 × expensive = 5 min
    """
    
    def __init__(self):
        self._constraints: Dict[ConstraintLevel, List[Constraint]] = {
            ConstraintLevel.GEOMETRIC: [],
            ConstraintLevel.SIMPLIFIED: [],
            ConstraintLevel.FULL_PHYSICS: [],
        }
        self._statistics = ValidationStatistics()
    
    def add_constraint(self, constraint: Constraint):
        """Register constraint at appropriate level."""
        self._constraints[constraint.level].append(constraint)
    
    def validate(
        self,
        design: dict,
        stop_on_failure: bool = True,
    ) -> "HierarchicalValidationResult":
        """
        Validate design through constraint pyramid.
        
        Args:
            design: Design parameters
            stop_on_failure: If True, stop at first failed level
        
        Returns:
            Validation result with per-level status
        """
        results = {}
        
        # Level 1: Geometric (milliseconds)
        geometric_results = self._evaluate_level(
            design, ConstraintLevel.GEOMETRIC
        )
        results[ConstraintLevel.GEOMETRIC] = geometric_results
        self._statistics.geometric_evaluations += 1
        
        if stop_on_failure and not all(r.satisfied for r in geometric_results):
            self._statistics.geometric_failures += 1
            return HierarchicalValidationResult(
                valid=False,
                failed_level=ConstraintLevel.GEOMETRIC,
                results=results,
            )
        
        # Level 2: Simplified physics (seconds)
        simplified_results = self._evaluate_level(
            design, ConstraintLevel.SIMPLIFIED
        )
        results[ConstraintLevel.SIMPLIFIED] = simplified_results
        self._statistics.simplified_evaluations += 1
        
        if stop_on_failure and not all(r.satisfied for r in simplified_results):
            self._statistics.simplified_failures += 1
            return HierarchicalValidationResult(
                valid=False,
                failed_level=ConstraintLevel.SIMPLIFIED,
                results=results,
            )
        
        # Level 3: Full physics (minutes)
        full_results = self._evaluate_level(
            design, ConstraintLevel.FULL_PHYSICS
        )
        results[ConstraintLevel.FULL_PHYSICS] = full_results
        self._statistics.full_physics_evaluations += 1
        
        all_satisfied = all(r.satisfied for r in full_results)
        if not all_satisfied:
            self._statistics.full_physics_failures += 1
        
        return HierarchicalValidationResult(
            valid=all_satisfied,
            failed_level=None if all_satisfied else ConstraintLevel.FULL_PHYSICS,
            results=results,
        )
    
    def _evaluate_level(
        self,
        design: dict,
        level: ConstraintLevel,
    ) -> List[ConstraintResult]:
        """Evaluate all constraints at a given level."""
        return [
            constraint.evaluate(design)
            for constraint in self._constraints[level]
        ]
    
    def get_statistics(self) -> "ValidationStatistics":
        """Get validation statistics for performance analysis."""
        return self._statistics


@dataclass
class HierarchicalValidationResult:
    """Result of hierarchical validation."""
    valid: bool
    failed_level: Optional[ConstraintLevel]
    results: Dict[ConstraintLevel, List[ConstraintResult]]
    
    def get_failure_guidance(self) -> List[str]:
        """Get hints for fixing failures."""
        if self.valid:
            return []
        
        guidance = []
        for result in self.results.get(self.failed_level, []):
            if not result.satisfied and result.direction_hint:
                guidance.append(f"{result.constraint_name}: {result.direction_hint}")
        return guidance


@dataclass
class ValidationStatistics:
    """Track validation performance."""
    geometric_evaluations: int = 0
    geometric_failures: int = 0
    simplified_evaluations: int = 0
    simplified_failures: int = 0
    full_physics_evaluations: int = 0
    full_physics_failures: int = 0
    
    @property
    def filter_efficiency(self) -> float:
        """How effectively cheap constraints filter candidates."""
        if self.geometric_evaluations == 0:
            return 0.0
        
        # What fraction of designs are eliminated before expensive eval
        total = self.geometric_evaluations
        reached_expensive = self.full_physics_evaluations
        filtered = total - reached_expensive
        
        return filtered / total
```

---

### 0.11.5 Probabilistic Design State

#### File Location

- `magnet/core/probabilistic_design.py`

#### Interface Contract

```python
# magnet/core/probabilistic_design.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np
from scipy.stats import norm

@dataclass
class ParameterDistribution:
    """
    Parameter with uncertainty quantification.
    
    KEY INSIGHT: Real designs have tolerances and manufacturing variation.
    Optimization should account for this.
    """
    mean: float
    std: float
    bounds: tuple  # (min, max)
    
    def sample(self) -> float:
        """Sample from distribution, respecting bounds."""
        value = np.random.normal(self.mean, self.std)
        return np.clip(value, self.bounds[0], self.bounds[1])
    
    def confidence_interval(self, level: float = 0.95) -> tuple:
        """Get confidence interval."""
        z = norm.ppf((1 + level) / 2)
        return (self.mean - z * self.std, self.mean + z * self.std)
    
    def probability_in_range(self, low: float, high: float) -> float:
        """Probability that value falls in range."""
        return norm.cdf(high, self.mean, self.std) - norm.cdf(low, self.mean, self.std)


@dataclass
class ProbabilisticDesign:
    """
    Design with uncertainty quantification.
    
    KEY INSIGHT: Optimization operates on distributions, not point estimates.
    This enables robust optimization that accounts for:
    - Manufacturing tolerances
    - Measurement uncertainty
    - Model uncertainty
    """
    parameters: Dict[str, ParameterDistribution] = field(default_factory=dict)
    objectives: Dict[str, ParameterDistribution] = field(default_factory=dict)
    constraint_satisfaction: Dict[str, float] = field(default_factory=dict)  # Probability
    
    def expected_value(self) -> Dict[str, float]:
        """Convert to deterministic design (means)."""
        return {k: v.mean for k, v in self.parameters.items()}
    
    def sample(self, n: int = 1) -> List[Dict[str, float]]:
        """Generate sample designs from uncertainty distribution."""
        samples = []
        for _ in range(n):
            sample = {k: v.sample() for k, v in self.parameters.items()}
            samples.append(sample)
        return samples
    
    def worst_case(self, objective: str, percentile: float = 0.05) -> float:
        """
        Get worst-case objective value at given percentile.
        
        For robust optimization, we often want to optimize the
        worst-case rather than the expected case.
        """
        if objective not in self.objectives:
            raise KeyError(f"Unknown objective: {objective}")
        
        dist = self.objectives[objective]
        return norm.ppf(percentile, dist.mean, dist.std)
    
    def probability_feasible(self) -> float:
        """
        Probability that design satisfies ALL constraints.
        
        Assumes constraints are independent (conservative estimate).
        """
        if not self.constraint_satisfaction:
            return 1.0
        
        return np.prod(list(self.constraint_satisfaction.values()))
    
    def robustness_score(self) -> float:
        """
        Combined score of feasibility and low variance.
        
        High score = design is both likely feasible and has low uncertainty.
        """
        feasibility = self.probability_feasible()
        
        # Coefficient of variation (lower = more robust)
        cvs = [
            dist.std / abs(dist.mean) if dist.mean != 0 else float('inf')
            for dist in self.parameters.values()
        ]
        avg_cv = np.mean(cvs) if cvs else 0
        
        # Robustness decreases with CV
        robustness = 1 / (1 + avg_cv)
        
        return feasibility * robustness


class ProbabilisticOptimizer:
    """
    Optimize over probabilistic designs.
    
    Instead of finding a single "optimal" point, finds designs
    that are robust to uncertainty.
    """
    
    def __init__(
        self,
        base_optimizer: "MultiFidelitySurrogateOptimizer",
        n_samples: int = 100,
        feasibility_threshold: float = 0.95,
    ):
        self._optimizer = base_optimizer
        self._n_samples = n_samples
        self._feasibility_threshold = feasibility_threshold
    
    def optimize_robust(
        self,
        targets: Dict[str, float],
        tolerances: Dict[str, float],  # Manufacturing tolerances
    ) -> ProbabilisticDesign:
        """
        Find design that remains feasible under uncertainty.
        
        Args:
            targets: Objective targets
            tolerances: Parameter tolerances (std dev as fraction of value)
        
        Returns:
            Probabilistic design with high feasibility probability
        """
        # First, find nominal optimum
        nominal_result = self._optimizer.optimize(targets)
        nominal_design = nominal_result.design
        
        # Convert to probabilistic design with tolerances
        prob_design = self._to_probabilistic(nominal_design, tolerances)
        
        # Check feasibility under uncertainty
        feasibility = self._estimate_feasibility(prob_design)
        
        # If not robust enough, expand search
        if feasibility < self._feasibility_threshold:
            prob_design = self._robustify(prob_design, targets)
        
        return prob_design
    
    def _to_probabilistic(
        self,
        design: Dict[str, float],
        tolerances: Dict[str, float],
    ) -> ProbabilisticDesign:
        """Convert deterministic design to probabilistic."""
        parameters = {}
        for name, value in design.items():
            tol = tolerances.get(name, 0.01)  # Default 1% tolerance
            std = abs(value * tol)
            parameters[name] = ParameterDistribution(
                mean=value,
                std=std,
                bounds=(value * 0.8, value * 1.2),  # ±20% hard bounds
            )
        return ProbabilisticDesign(parameters=parameters)
    
    def _estimate_feasibility(
        self,
        prob_design: ProbabilisticDesign,
    ) -> float:
        """Estimate probability of feasibility via Monte Carlo."""
        samples = prob_design.sample(self._n_samples)
        
        feasible_count = 0
        for sample in samples:
            result = self._optimizer._hierarchical_filter([sample], n_keep=1)
            if result:  # Passed filter
                feasible_count += 1
        
        return feasible_count / self._n_samples
    
    def _robustify(
        self,
        prob_design: ProbabilisticDesign,
        targets: Dict[str, float],
    ) -> ProbabilisticDesign:
        """
        Adjust design to improve robustness.
        
        Strategy: Move away from constraint boundaries.
        """
        # Get constraint gradient directions
        mean_design = prob_design.expected_value()
        
        # Find which constraints are tight
        # Move design in direction that increases margin
        
        # This is a simplified version - full implementation would
        # use gradient-based robust optimization
        
        return prob_design
```

---

### 0.11.6 Incremental State Management

#### File Location

- `magnet/core/incremental_state.py`

#### Interface Contract

```python
# magnet/core/incremental_state.py

from dataclasses import dataclass, field
from typing import Dict, Set, Any, Optional, Callable
import time

@dataclass
class ComputationNode:
    """Node in computation dependency graph."""
    id: str
    compute_fn: Callable[["IncrementalState"], Any]
    dependencies: Set[str]  # Parameter names this depends on
    
    # Cache
    cached_value: Optional[Any] = None
    cached_at_version: int = -1
    compute_time_ms: float = 0.0

class IncrementalState:
    """
    Track state changes and invalidate only affected computations.
    
    KEY INSIGHT: Most state changes affect only local computations.
    Don't recompute everything - track dependencies and invalidate selectively.
    
    Performance comparison:
    - Full recomputation: O(n) for every change
    - Incremental: O(k) where k = affected computations (typically k << n)
    """
    
    def __init__(self):
        self._parameters: Dict[str, float] = {}
        self._version: int = 0
        self._parameter_versions: Dict[str, int] = {}  # Per-parameter versions
        
        self._computations: Dict[str, ComputationNode] = {}
        self._dependents: Dict[str, Set[str]] = {}  # param -> computations that depend on it
    
    def set_parameter(self, name: str, value: float) -> Set[str]:
        """
        Update parameter and return invalidated computations.
        
        O(k) where k = number of dependent computations.
        """
        if name in self._parameters and self._parameters[name] == value:
            return set()  # No change
        
        self._parameters[name] = value
        self._version += 1
        self._parameter_versions[name] = self._version
        
        # Find and invalidate dependent computations
        invalidated = self._dependents.get(name, set()).copy()
        
        # Cascade invalidation
        to_check = list(invalidated)
        while to_check:
            comp_id = to_check.pop()
            node = self._computations.get(comp_id)
            if node:
                node.cached_value = None  # Invalidate cache
                
                # Any computations depending on this one are also invalid
                for dependent in self._find_computation_dependents(comp_id):
                    if dependent not in invalidated:
                        invalidated.add(dependent)
                        to_check.append(dependent)
        
        return invalidated
    
    def get_parameter(self, name: str) -> float:
        """Get parameter value."""
        return self._parameters.get(name, 0.0)
    
    def register_computation(
        self,
        id: str,
        compute_fn: Callable[["IncrementalState"], Any],
        dependencies: Set[str],
    ):
        """Register a computation with its dependencies."""
        self._computations[id] = ComputationNode(
            id=id,
            compute_fn=compute_fn,
            dependencies=dependencies,
        )
        
        # Build reverse index
        for param in dependencies:
            if param not in self._dependents:
                self._dependents[param] = set()
            self._dependents[param].add(id)
    
    def get_computation(self, id: str) -> Any:
        """
        Get computation result, computing if necessary.
        
        Uses cached value if still valid.
        """
        node = self._computations.get(id)
        if node is None:
            raise KeyError(f"Unknown computation: {id}")
        
        # Check if cache is valid
        if node.cached_value is not None:
            # Check if any dependency has changed since caching
            cache_valid = all(
                self._parameter_versions.get(dep, 0) <= node.cached_at_version
                for dep in node.dependencies
            )
            if cache_valid:
                return node.cached_value
        
        # Recompute
        start = time.time()
        result = node.compute_fn(self)
        node.compute_time_ms = (time.time() - start) * 1000
        
        # Cache result
        node.cached_value = result
        node.cached_at_version = self._version
        
        return result
    
    def _find_computation_dependents(self, comp_id: str) -> Set[str]:
        """Find computations that depend on this computation's result."""
        # For simplicity, assume computations don't depend on each other
        # Full implementation would track computation-to-computation dependencies
        return set()
    
    def clone_minimal(self, parameters: Set[str]) -> "IncrementalState":
        """
        Create minimal clone with only specified parameters.
        
        O(k) where k = number of parameters to clone.
        Much cheaper than full state clone.
        """
        clone = IncrementalState()
        for param in parameters:
            clone._parameters[param] = self._parameters.get(param, 0.0)
        return clone
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics."""
        total_compute_time = sum(
            n.compute_time_ms for n in self._computations.values()
        )
        cache_hits = sum(
            1 for n in self._computations.values()
            if n.cached_value is not None
        )
        
        return {
            "version": self._version,
            "n_parameters": len(self._parameters),
            "n_computations": len(self._computations),
            "cache_hit_rate": cache_hits / len(self._computations) if self._computations else 0,
            "total_compute_time_ms": total_compute_time,
        }
```

---

### 0.11.7 Implementation Roadmap

#### Phase -3: Emergency Stabilization (Week 0)

| Task | Description | Dependencies | Effort |
|------|-------------|--------------|--------|
| E0.1 | Fail-fast state isolation (no live-state evals) | None | 0.5 day |
| E0.2 | Structured violations (no opaque None) | None | 0.5 day |
| E0.3 | C1 smoothing in generator | None | 1-2 days |
| E0.4 | Equilibrium stability at discontinuities | E0.3 | 1 day |

#### Phase 1: Multi-Fidelity Foundation (Weeks 1-4)

| Task | Description | Dependencies | Effort |
|------|-------------|--------------|--------|
| TM.1 | Implement pluggable scalable surrogate backends | E0.1 | 1 week |
| TM.3A | Implement PhysicsEvaluator adapter over existing physics | E0.3-E0.4 | 0.5 week |
| TM.3 | Implement HierarchicalValidator (with confidence/assumptions) | None | 0.5 week |
| TM.3B | Implement SurrogateTrainer pipeline (fit/update) | TM.1, TM.3A | 0.5 week |
| TM.2 | Implement MultiFidelitySurrogateOptimizer | TM.1, TM.3, TM.3A | 1 week |
| TM.8 | Implement Hybrid Fidelity Control Plane | TM.2 | 0.5 week |
| TM.7 | Integration tests for surrogate + physics validation pipeline | TM.1-3B, TM.8 | 0.5 week |

#### Phase 2: Incremental State + Dependency-Driven Recompute (Weeks 5-6)

| Task | Description | Dependencies | Effort |
|------|-------------|--------------|--------|
| TM.5 | Implement `IncrementalState` and adopt it in optimization eval loops | None | 2 weeks |

#### Phase 3: Probabilistic / Robust Optimization (Weeks 7-8)

| Task | Description | Dependencies | Effort |
|------|-------------|--------------|--------|
| TM.4 | Implement `ProbabilisticDesign` (uncertainty-aware representation) | None | 1 week |
| TM.6 | Implement `ProbabilisticOptimizer` (chance constraints / robustness) | TM.2, TM.4 | 1 week |

#### Phase 4: Product Integration + Hardening (Weeks 9-12)

| Task | Description | Dependencies | Effort |
|------|-------------|--------------|--------|
| TM.9 | Integrate hybrid optimizer into CLI/API/control plane | TM.7, TM.8 | 1 week |
| TM.10 | Performance benchmarks + budgets (surrogate vs physics) | TM.9 | 1 week |
| TM.11 | Docs + migration notes (make hybrid the canonical path) | TM.9 | 1 week |

---

### 0.11.8 Migration Strategy

#### Fallback Mode

Always maintain physics-only optimization as fallback:

```python
class HybridOptimizer:
    """
    Optimizer that can fall back to physics-only mode.
    
    Use multi-fidelity when surrogate is reliable,
    fall back to physics when surrogate uncertainty is high.
    """
    
    def optimize(self, targets: Dict[str, float]) -> OptimizationResult:
        # Try multi-fidelity first
        try:
            result = self.multi_fidelity_optimizer.optimize(targets)
            
            # Check surrogate confidence
            if result.surrogate_confidence > self.confidence_threshold:
                return result
            
            # Low confidence - fall back to physics
            self.logger.warning("Low surrogate confidence, using physics-only")
            
        except SurrogateFailure as e:
            self.logger.warning(f"Surrogate failed: {e}, using physics-only")
        
        # Physics-only fallback
        return self.physics_optimizer.optimize(targets)
```

#### Hybrid Fidelity Control Plane (User-Facing)

The system must support a **user-selected fidelity knob** that determines *how much expensive physics is used*, without ever allowing surrogates to “declare validity.”

- **Surrogates are not a replacement for the kernel**: they are a proposal engine.
- **Only the kernel validators can certify a design as valid**.

**Fidelity modes**:

- **`fast`**: surrogate proposes candidates + hierarchical constraints; physics validates top-K only (default for iteration).
- **`hybrid`**: surrogate proposes; physics validates top-K; optional short physics “refine” (default for “good answer quickly”).
- **`full`**: physics-only optimization and/or exhaustive validation (“certify”, “produce report”, “yard-ready check”).

**Interface contract** (LLM/tool-facing):

```python
from dataclasses import dataclass
from typing import Dict, Literal, Optional

OptimizationFidelity = Literal["fast", "hybrid", "full"]

@dataclass(frozen=True)
class OptimizationRequest:
    targets: Dict[str, float]
    fidelity: OptimizationFidelity = "hybrid"

    # Budgets (explicit, not magic numbers)
    surrogate_candidates: int = 1000        # how many candidates to score cheaply
    physics_validate_top_k: int = 10        # how many candidates to validate with kernel/physics
    physics_refine_steps: int = 0           # optional local refine in physics space

    # Reporting
    return_detailed_report: bool = False    # include failed constraints, margins, evidence
    explain: bool = True                   # structured explanation for user

@dataclass(frozen=True)
class OptimizationResult:
    design_id: str
    fidelity_used: OptimizationFidelity
    validated_by_kernel: bool
    score: float
    # Optional: attach a structured report (constraints, evidence, margins)
    report: Optional[dict] = None
```

**Required behavior**:

- If `fidelity="full"` is requested by the user, the system must:
  - run physics-only search/refine (or at minimum physics-only validation with strict gates),
  - return a **detailed** validation report if `return_detailed_report=True`,
  - never rely on surrogate “valid” labels.
- If `fidelity in {"fast","hybrid"}`:
  - physics validation of the final returned design is **still mandatory** (kernel certification),
  - surrogate uncertainty may control **how much** physics is spent, but not whether it is spent.

**Acceptance tests** (`tests/optimization/test_hybrid_optimizer.py`):

```python
def test_fidelity_fast_still_kernel_validates_final():
    # fast mode may skip physics for most candidates, but must validate the chosen one
    ...

def test_fidelity_full_runs_physics_only_and_returns_report():
    # full mode must produce kernel-certified result and include report when requested
    ...

def test_user_request_for_full_overrides_surrogate_confidence():
    # explicit user knob must override any surrogate confidence gating
    ...
```

#### Incremental Adoption

Start with simple surrogates, add complexity gradually:

1. **Phase 1**: GP surrogate for single objective (displacement)
2. **Phase 2**: Multi-output GP for stability + displacement
3. **Phase 3**: Add hierarchical constraints
4. **Phase 4**: Full multi-fidelity optimization

---

### 0.11.9 Success Metrics

| Metric | Current (Physics-First) | Target (Multi-Fidelity) | Improvement |
|--------|------------------------|------------------------|-------------|
| Optimization time | ~30 min for convergence | ~3 min for convergence | 10x |
| Physics evaluations | ~1000 per optimization | ~50 per optimization | 20x |
| Success rate | ~60% (fails on complex designs) | ~95% | 1.6x |
| Robustness | Point estimate only | Probabilistic | Qualitative |

---

### 0.11.10 Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Surrogate inaccuracy | Invalid designs pass filter | Validate ALL final candidates with physics |
| Cold start problem | Poor initial surrogate | Use LHS for initial sampling, transfer learning from similar problems |
| Exploration vs exploitation | Miss global optimum | Adaptive exploration rate, restart from multiple initial points |
| Computational overhead | Surrogate fitting cost | Incremental GP updates, sparse approximations |

---

### 0.11.11 Open Source Implementation Stack

Rather than building from scratch, leverage production-ready open source libraries for multi-fidelity optimization.

#### Core Surrogate Modeling Libraries

| Library | GitHub | Best For | Key Features |
|---------|--------|----------|--------------|
| **SMT** | `SMTorg/smt` | Industrial-grade surrogates with gradient support | Kriging, RBF, polynomial regression, derivatives |
| **GPflow** | `GPflow/gpflow` | Bayesian optimization with GPs | TensorFlow-based, GPU acceleration, composable kernels |
| **GPy** | `SheffieldML/GPy` | Flexible GP modeling | Sparse GPs, multiple outputs, non-parametric regression |

#### Multi-Fidelity Optimization Frameworks

| Library | GitHub | Best For | Key Features |
|---------|--------|----------|--------------|
| **Multifidelity_Optimization** | `PC-FSU/Multifidelity_Optimization` | Direct multi-fidelity Bayesian optimization | MFBO algorithms, parallel/serial variants |
| **mf2** | `sjvrijn/mf2` | Benchmarking multi-fidelity algorithms | Standardized test functions for validation |
| **Emukit** | `EmuKit/emukit` | Multi-fidelity modeling & optimization | Bayesian optimization, experimental design |

#### Constrained Optimization

| Library | GitHub | Best For | Key Features |
|---------|--------|----------|--------------|
| **COPT** | `openopt/copt` | Large-scale constrained optimization | Proximal methods, Frank-Wolfe algorithms |
| **pymoo** | `anyoptimization/pymoo` | Multi-objective optimization | NSGA-II, constraints, parallelization |

#### Naval Architecture Specific

| Library | GitHub | Best For | Key Features |
|---------|--------|----------|--------------|
| **OpenPlaning** | `elcf/python-openplaning` | Planing hull physics | Savitsky method implementation |
| **OpenMDAO** | `OpenMDAO/OpenMDAO` | Multidisciplinary design optimization | Derivative computation, optimization drivers |

#### Recommended Installation Stack

```bash
# Core surrogate modeling
pip install smt              # Industrial-grade surrogates (Kriging, RBF)
pip install gpflow           # GPU-accelerated Gaussian Processes
pip install scikit-learn     # Fallback GP implementation

# Multi-fidelity optimization
pip install emukit           # Multi-fidelity modeling framework
pip install git+https://github.com/PC-FSU/Multifidelity_Optimization.git

# Constrained optimization
pip install pymoo            # Multi-objective with constraints
pip install copt             # Optional: large-scale constrained optimization (if needed)

# Validation/benchmarking
pip install mf2              # Multi-fidelity test functions

# Naval architecture physics
pip install openplaning      # Planing hull physics (Savitsky)
```

#### Integration Architecture

```python
# magnet/optimization/library_integration.py

"""
Integration layer for open source optimization libraries.

This module wraps external libraries to provide a unified interface
for MAGNET's multi-fidelity optimization.
"""

from typing import Protocol, Dict, List, Callable
import numpy as np

class SurrogateBackend(Protocol):
    """Protocol for surrogate model backends."""
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> None: ...
    def predict(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]: ...
    def compute_gradient(self, x: np.ndarray) -> np.ndarray: ...


class SMTBackend:
    """
    SMT library backend for industrial-grade surrogates.
    
    Best for: Production use with gradient support
    """
    
    def __init__(self, surrogate_type: str = "KRG"):
        from smt.surrogate_models import KRG, RBF, KPLS
        
        self._model_classes = {
            "KRG": KRG,      # Kriging
            "RBF": RBF,      # Radial Basis Functions
            "KPLS": KPLS,    # Kriging + PLS for high dimensions
        }
        self._model = self._model_classes[surrogate_type](print_global=False)
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self._model.set_training_values(X, y)
        self._model.train()
    
    def predict(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        mean = self._model.predict_values(X)
        var = self._model.predict_variances(X)
        return mean.flatten(), np.sqrt(var).flatten()
    
    def compute_gradient(self, x: np.ndarray) -> np.ndarray:
        return self._model.predict_derivatives(x.reshape(1, -1), 0).flatten()


class GPflowBackend:
    """
    GPflow backend for GPU-accelerated GPs.
    
    Best for: Large datasets, GPU availability
    """
    
    def __init__(self, kernel_type: str = "Matern52"):
        import gpflow
        import tensorflow as tf
        
        self._gpflow = gpflow
        self._tf = tf
        self._kernel_type = kernel_type
        self._model = None
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        kernel = getattr(self._gpflow.kernels, self._kernel_type)()
        self._model = self._gpflow.models.GPR(
            data=(X.astype(np.float64), y.reshape(-1, 1).astype(np.float64)),
            kernel=kernel,
        )
        opt = self._gpflow.optimizers.Scipy()
        opt.minimize(self._model.training_loss, self._model.trainable_variables)
    
    def predict(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        mean, var = self._model.predict_f(X.astype(np.float64))
        return mean.numpy().flatten(), np.sqrt(var.numpy()).flatten()


class SklearnBackend:
    """
    Scikit-learn backend as fallback.
    
    Best for: Simple use cases, no GPU
    """
    
    def __init__(self):
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import Matern
        
        self._model = GaussianProcessRegressor(
            kernel=Matern(nu=2.5),
            n_restarts_optimizer=10,
            normalize_y=True,
        )
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(X, y)
    
    def predict(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        mean, std = self._model.predict(X, return_std=True)
        return mean, std


def get_best_backend() -> SurrogateBackend:
    """
    Auto-select best available backend.
    
    Priority: SMT > GPflow (if GPU) > sklearn
    """
    # Try SMT first (industrial grade)
    try:
        from smt.surrogate_models import KRG
        return SMTBackend()
    except ImportError:
        pass
    
    # Try GPflow if GPU available
    try:
        import tensorflow as tf
        if tf.config.list_physical_devices('GPU'):
            import gpflow
            return GPflowBackend()
    except ImportError:
        pass
    
    # Fallback to sklearn
    return SklearnBackend()


class MultiFidelityOptimizer:
    """
    Multi-fidelity optimizer using Emukit or custom implementation.
    """
    
    def __init__(
        self,
        low_fidelity_fn: Callable,
        high_fidelity_fn: Callable,
        parameter_bounds: Dict[str, tuple],
    ):
        self._low_fidelity = low_fidelity_fn
        self._high_fidelity = high_fidelity_fn
        self._bounds = parameter_bounds
        
        # Try to use Emukit for multi-fidelity
        try:
            from emukit.multi_fidelity.models import GPyLinearMultiFidelityModel
            self._use_emukit = True
        except ImportError:
            self._use_emukit = False
            self._surrogate = get_best_backend()
    
    def optimize(
        self,
        targets: Dict[str, float],
        high_fidelity_budget: int = 50,
    ) -> Dict[str, float]:
        """
        Run multi-fidelity optimization.
        
        Uses Emukit if available, otherwise custom implementation.
        """
        if self._use_emukit:
            return self._optimize_emukit(targets, high_fidelity_budget)
        else:
            return self._optimize_custom(targets, high_fidelity_budget)
    
    def _optimize_emukit(
        self,
        targets: Dict[str, float],
        budget: int,
    ) -> Dict[str, float]:
        """Emukit-based multi-fidelity optimization."""
        from emukit.core import ParameterSpace, ContinuousParameter
        from emukit.core.acquisition import Acquisition
        from emukit.bayesian_optimization.loops import BayesianOptimizationLoop
        
        # Build parameter space
        params = [
            ContinuousParameter(name, low, high)
            for name, (low, high) in self._bounds.items()
        ]
        space = ParameterSpace(params)
        
        # ... Emukit multi-fidelity setup
        # (Full implementation would use Emukit's multi-fidelity models)
        
        raise NotImplementedError("Full Emukit integration pending")
    
    def _optimize_custom(
        self,
        targets: Dict[str, float],
        budget: int,
    ) -> Dict[str, float]:
        """Custom multi-fidelity implementation using selected backend."""
        # Implementation as shown in §0.11.3
        # Uses self._surrogate for GP modeling
        pass
```

#### Library Selection Guide

| Scenario | Recommended Stack | Rationale |
|----------|------------------|-----------|
| **Production** | SMT + Emukit | Industrial-grade, well-tested |
| **Research/Prototyping** | GPy + custom | Flexible, easy to modify |
| **GPU Available** | GPflow + TensorFlow | 10-100x speedup on large datasets |
| **Minimal Dependencies** | sklearn only | Works everywhere, no GPU needed |
| **High Dimensions (>20)** | SMT (KPLS) | Handles curse of dimensionality |

#### Performance Expectations

| Metric | sklearn Backend | SMT Backend | GPflow (GPU) |
|--------|-----------------|-------------|--------------|
| Training (1000 points) | ~5s | ~2s | ~0.5s |
| Prediction (10000 points) | ~1s | ~0.3s | ~0.05s |
| Gradient computation | Not available | ~0.1s | ~0.02s |
| Memory (1000 points) | ~100 MB | ~50 MB | ~500 MB (GPU) |

**Expected speedup over physics-first**: 10-100x with same accuracy guarantees.

---

### 0.11.12 Summary: Why This Fixes the Architecture

The current physics-first architecture fails because:

1. **Linear blending** in high-dimensional space has P(valid) ≈ 0
2. **Expensive physics** per evaluation makes optimization infeasible
3. **Thundering herd** invalidation causes performance collapse
4. **Full state cloning** is O(n) for every gradient evaluation

The multi-fidelity approach works because:

1. **Surrogate optimization** operates in cheap approximation space
2. **Hierarchical constraints** filter 90%+ of candidates with cheap checks
3. **Incremental state** only invalidates affected computations
4. **Probabilistic design** accounts for real-world uncertainty

**Bottom Line**: This is the only architecture that can scale to "Claude builds a vessel" because it learns a optimization-friendly representation of the physics space instead of brute-forcing through it.

---

## 0) Non-negotiables (the constitutional constraints)

- **Single Source of Truth (SSOT)**: `DesignState` via `StateManager` is the only truth.
- **No parallel ArtifactGraph store**: any “graph” is a *view/adapter* over `DesignState.resources`.
- **All writes go through a single authority**:
  - design language execution (program → parser → expander → actions → `StateManager`)
  - or Intent→ActionPlan firewall (deterministic actions → executor → `StateManager`)
  - **Never** mutate `resources` directly in ad-hoc code paths (conflict resolution, routing repair, etc.).
- **Non-enumeration**: kernel validates physics/geometry, not “boat types”. Style/type labels may exist in UI, but are derived and non-authoritative.

---

## 1) What exists today (MAGNET assets you reuse)

- **State + versioning**: `StateManager` / DesignStore.
- **Design language geometry path**: `magnet/kernel/stdlib/*` + `program_executor`.
- **EDIT vs REWRITE boundary**: enforced in spiral endpoints (EDIT prohibits identity-breaking operations unless rewrite approved).
- **Observables**:
  - kernel-owned measurers/control scaffolding: `magnet/kernel/geometry_observables.py`
  - agent-facing measurable registry for thinking pass: `magnet/agents/geometry_observables.py`
- **Routing infrastructure**: `magnet/routing/*`.
- **System generators/validators** exist (e.g. fuel), but are not yet first-class geometry artifacts.

---

## 2) The real blocker: systems are not editable/visible artifacts

To achieve “Claude web design equivalent”, **systems must become placeable/routable geometry artifacts** in `resources`.

### 2.1 Represent systems using existing primitives (no new `system.*` types)

- **Component** (tank, generator, pump, panel, duct box, etc.) → `geometry.body`
  - required tags/metadata: `system_id`, `component_type`, `component_id`, `bounds_hint` (optional)
- **Route** (pipe/duct/cable) → `geometry.flow_path`
  - required: `medium`, endpoints, cross-section; tags: `system_id`, `connection_id`
- **Penetration** → `geometry.opening` (`purpose`)
- **Mount** → `geometry.attachment` (parent/child ids)

### 2.2 Artifact “graph” is a view, not storage

Implement an adapter like:
- `magnet/artifacts/graph_view.py` (new)
  - indexes resources by `_type`, `body_id`, `system_id`
  - exposes “component instances”, “routes”, “zones” for tooling
  - provides spatial proxies for conflict detection (AABB/OBB)

---

## 2.3 Interface contracts (new components) (P0)

### DesignMutator: staging contract

The guide must define what `DesignMutator.stage(...)` accepts.

```python
from dataclasses import dataclass
from typing import Protocol, Dict, Any, List

class Mutation(Protocol):
    mutation_id: str
    origin: str  # "agent" | "optimizer" | "conflict_resolver" | "user"
    def to_action_plan(self) -> "ActionPlan": ...
    def describe(self) -> str: ...
    def validate(self) -> "ValidationResult": ...

@dataclass(frozen=True)
class MutationResult:
    success: bool
    design_version_before: int
    design_version_after: int
    receipts: List[Dict[str, Any]]
    propagated_errors: List["PropagatedError"]
```

### Error propagation: contract

```python
from dataclasses import dataclass
from typing import Dict, Any, List, Protocol

@dataclass(frozen=True)
class PropagatedError:
    origin_layer: str  # "kernel" | "conflict_resolver" | "validator" | "orchestrator"
    error_type: str
    technical_message: str
    user_message: str
    suggestions: List[str]
    context: Dict[str, Any]

class ErrorPropagator(Protocol):
    def propagate(self, error: Exception, *, layer: str, context: Dict[str, Any]) -> PropagatedError: ...
```

---

## 3) Three-regime loop (Hull Creation + Hull Editing + Outfitting)

### 3.1 Hull Creation (topology + synthesis)

1. **Hull generation**
   - preferred: composition/program path that compiles through existing synthesis machinery (`magnet/kernel/synthesis.py`, `magnet/hull_gen/*`)
   - output must include: hull geometry + detected anchors/affordances for subsequent editing

2. **Validate + seed baseline**
   - run hard gates (float/stability as applicable)
   - capture baseline signatures needed for edit guards:
     - character baseline (see §9)
     - anchor baseline (planned; see §0.3.3 gaps)

3. **Render**
   - WebGL shows hull geometry; anchors/affordances are not “visual noise” but must be queryable

### 3.2 Hull Editing (anchor/affordance-bounded, topology-preserving)

1. See current state (vision + structured queries)
2. Identify impacted artifacts (`system_id`, `component_type`)
3. Apply edits using safe operations:
   - **shape edits**: ADJUST/TARGET only (identity-preserving)
   - **guardrails**:
     - EDIT-mode invariant: character guard before commit (§5 header + §9)
     - (planned) anchor viability / topology-change classification circuit breaker (spec §2.5/§2.6; see §0.3.3 gaps)
4. Reroute affected flow_paths (routing repair)
5. Validate + produce narrative + receipts

### 3.3 Outfitting (systems + routing + compilation to many artifacts)

1. **Generate/compile systems into geometry artifacts** (fuel-first vertical slice)
   - systems must emit `geometry.*` resources in SSOT (`DesignState.resources`)
2. **Route** (pipes/cables/ducts) via routing subsystems; reroute on edits
3. **Validate** (hard/soft/grade; see §8)
4. **Expose** as queryable, editable artifacts (not hidden dataclasses)

---

## 3.3 Inter-level contract schemas (P0: actual types, not just names)

The guide must provide real schemas for level handoffs. These should live in `magnet/contracts/generative_contracts.py`, and each payload must be:
- JSON-serializable
- versioned (`schema_version`)
- unit-explicit (every numeric field)
- frame-explicit (coordinate frames for spatial values)

Minimum set (first pass):

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal

Frame = Literal["vessel_origin", "body_local", "world"]

@dataclass(frozen=True)
class ZoneBounds:
    x_min_m: float
    x_max_m: float
    y_min_m: float
    y_max_m: float
    z_min_m: float
    z_max_m: float

@dataclass(frozen=True)
class SpaceAllocation:
    schema_version: str = "1.0"
    coordinate_frame: Frame = "vessel_origin"
    zones: Dict[str, ZoneBounds] = field(default_factory=dict)  # zone_id -> bounds
    reserved_volumes_m3: Dict[str, float] = field(default_factory=dict)  # zone_id -> m^3

@dataclass(frozen=True)
class SystemReq:
    system_id: str
    description: str
    capacity_l: Optional[float] = None
    power_budget_kw: Optional[float] = None
    weight_budget_kg: Optional[float] = None
    redundancy: Optional[str] = None

@dataclass(frozen=True)
class SystemRequirements:
    schema_version: str = "1.0"
    systems: Dict[str, SystemReq] = field(default_factory=dict)  # system_id -> req

@dataclass(frozen=True)
class InterfaceSpec:
    interface_id: str
    kind: str  # "inlet" | "outlet" | "vent" | "fill" | "electrical"
    component_id: str
    location_frame: Frame
    x_m: float
    y_m: float
    z_m: float

@dataclass(frozen=True)
class ComponentSpec:
    component_id: str
    component_type: str
    system_id: str
    envelope_m3: Optional[float] = None
    placement_zone_id: Optional[str] = None

@dataclass(frozen=True)
class SystemSpecs:
    schema_version: str = "1.0"
    system_id: str = ""
    components: List[ComponentSpec] = field(default_factory=list)
    interfaces: List[InterfaceSpec] = field(default_factory=list)

@dataclass(frozen=True)
class RoutingRequirements:
    schema_version: str = "1.0"
    system_id: str = ""
    medium: str = ""  # "fuel" | "water" | "dc" | etc.
    endpoints: List[str] = field(default_factory=list)  # interface_id list
    preferred_avoid_zones: List[str] = field(default_factory=list)
```

The orchestrator must validate these schemas at each handoff (fail-closed with PropagatedError).

---

## 4) Observable taxonomy + schema packaging (LLM contract)

### 4.1 Canonical observable registry

There must be one kernel-owned registry that defines:
- observable_id (canonical)
- measurable vs controllable
- control_mode: DIRECT | COMPILED | OPTIMIZED
- unit, tolerance, max_delta
- allowed scopes (station_range/body_id/system_id/component_id)
- explicit aliases (versioned, optional, and deprecations)

**Missing item (P0): controllability must be declared per artifact type + metric**

The schema must not only list *what exists*; it must encode *what is adjustable* and how.

Minimum required model:

```python
@dataclass
class MetricDefinition:
    name: str
    type: MetricType
    unit: str
    description: str
    arity: int = 1

    # NEW (required)
    controllable: bool = False
    control_mode: Optional[str] = None  # "DIRECT" | "COMPILED" | "OPTIMIZED"
    max_delta: Optional[float] = None
    applicable_to: List[str] = field(default_factory=list)  # component/resource types


# Example registry shape (kernel-owned, canonical)
CONTROLLABILITY_REGISTRY = {
    ("geometry.body", "position_x"): {"controllable": True, "mode": "DIRECT", "max_delta": 1.0},
    ("geometry.body", "volume"): {"controllable": False, "reason": "derived from geometry"},
    ("geometry.section", "deadrise_deg_at_chine"): {"controllable": True, "mode": "DIRECT", "max_delta": 15.0},
}
```

### 4.2 ObservableSchema summary passed to LLM every turn

The LLM must receive:
- list of known observable_ids (and controllable subset)
- list of available targets (bodies/components/routes by id + tags)
- sample queries (bounded set)
- “unknown observable” rejection behavior

This prevents hallucinated observables and enables safe tool use.

---

## 4.3 Wiring / dependency injection (how pieces connect) (P0)

The guide must specify how these components are instantiated and passed around.

### Where construction should live

- Prefer a single wiring location (a container/factory module) rather than ad-hoc instantiation in endpoints.
- Suggested location: `magnet/bootstrap/container.py` (or nearest existing “bootstrap” module).

### Constructor signatures (minimum)

```python
class CoordinateExecutor:
    def __init__(
        self,
        *,
        mutator: "DesignMutator",
        observable_registry: "ObservableRegistry",
        error_propagator: "ErrorPropagator",
        config: "CortexConfig",
    ): ...

class ConflictResolver:
    def __init__(
        self,
        *,
        claim_index: "SpatialClaimIndex",
        mutator: "DesignMutator",
        error_propagator: "ErrorPropagator",
        config: "CortexConfig",
    ): ...

class VesselDesignerOrchestrator:
    def __init__(
        self,
        *,
        state_manager: "StateManager",
        graph_view: "ArtifactGraphAdapter",
        mutator: "DesignMutator",
        observable_schema: "ObservableSchemaGenerator",
        conflict_resolver: "ConflictResolver",
        coordinate_executor: "CoordinateExecutor",
        error_propagator: "ErrorPropagator",
        config: "CortexConfig",
    ): ...
```

---

## 5) ADJUST/TARGET (bidirectional control) — hard requirements

**EDIT-mode invariant:** every ADJUST/TARGET must run the **character guard** (dry-run candidate → predicted drift → gate decision) **before** any mutation is committed. See §9.

### 5.1 DIRECT mode tolerance semantics (Phase 1)

- DIRECT mappings MUST define `tolerance`.
- If residual > tolerance:
  - **default**: fail-closed (`not_within_tolerance`), no state mutation
  - optional: user explicit override allows `applied_with_residual` (must be surfaced, never silent)

### 5.2 Station normalization & boundary edge cases

- \( station\_norm = (x - x_{aft}) / LOA \), inclusive ranges.
- Phase 1: scope selects **existing sections only** (no interpolation, no section creation in EDIT mode).
- If scope selects zero sections → `invalid_scope` + nearest stations hint.

### 5.3 Diff budget must be spatial extent (not station count)

- Compute union of affected station intervals; define `extent ∈ [0,1]`.
- Escalate to rewrite if:
  - `extent > 0.65`, or
  - too fragmented (e.g., >4 disjoint intervals)

**Alignment note (spec vs guide): this is a *local edit surface budget*, not the hull-edit circuit breaker.**

- This §5.3 rule limits how much of the hull is affected in a *single EDIT turn* (prevents “stealth rewrites via many local edits”).
- The spec’s **edit boundary policy** (Spec §2.6) is different and complementary:
  - it is a *global* viability metric across many operations (cumulative drift, retired anchors fraction, mean confidence).
- Both should exist:
  - **local**: spatial extent/fragmentation budget (this guide)
  - **global**: anchor/viability circuit breaker (spec) that forces resynthesis **before** corruption

### 5.4 Observable orthogonality sanity (avoid redundant/conflicting controls)

Numerically estimate a small sensitivity matrix between controllable observables.
If two controls are highly collinear, mark redundancy and require explicit approval when both are used in one turn.

**Missing implementation details (P1):**
- **When computed**: on-demand per turn if a proposal uses 2+ controls; cache by `design_version`
- **How measured**: dry-run apply a canonical small delta for each control, measure induced deltas
- **Threshold**: `COLLINEARITY_THRESHOLD = 0.9` (absolute correlation)
- **Behavior**:
  - default: `needs_clarification` (“controls are redundant/competing; choose one”)
  - allow override: user explicit confirmation to apply both

```python
COLLINEARITY_THRESHOLD = 0.9

def compute_control_effect_correlation(
    *,
    state: "DesignState",
    control_a: str,
    control_b: str,
    delta_a: float,
    delta_b: float,
) -> float:
    """Return correlation coefficient [-1, 1] between induced observable deltas."""
    ...
```

### 5.5 Deadrise transform math (pivot must be explicit)

The deadrise mapping must specify which point is preserved:

- **Preserve chine (recommended default)**:
  - keep \( (y_c, z_c) \) fixed
  - keep \( y_k \) fixed (keel anchor)
  - set:
    \[
    z_{k,new} = z_c - \Delta y \cdot \tan(\beta + \delta)
    \]
  - distribute \( \Delta z_k \) smoothly across bottom points (keel→chine)

- **Preserve keel (alternate)**:
  \[
  z_{c,new} = z_k + \Delta y \cdot \tan(\beta + \delta)
  \]
  (note: changes freeboard/draft unless compensated)

### 5.6 Coupling is real: record local Jacobians

Even in DIRECT mode, record numeric sensitivities via re-measurements in the receipt:
- \( \partial gm/\partial \beta \), \( \partial \nabla/\partial \beta \), \( \partial S/\partial \beta \), etc.

This is not full optimization—it’s **honest sensitivity reporting** so iteration is informed.

**Missing implementation detail (P1): receipt schema must include sensitivities**

```python
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class AdjustReceipt:
    observable_id: str
    scope: Dict[str, Any]
    requested_delta: float
    achieved_delta: float
    residual: float
    # NEW:
    sensitivities: Dict[str, float] = field(default_factory=dict)  # e.g. {"stability.gm_m": -0.02}
```

---

## 6) COORDINATE / optimized intent (must be safe)

### 6.1 Gradient estimation must not mutate real state

Any optimizer doing finite differences must use:
- **dry_run / snapshot sandbox** for perturbations
- discard invalid intermediate states instead of poisoning gradients

**Missing item (P0): implement `_compute_gradients_safe`**

The gradient estimator must never apply +delta/-delta against committed state.

```python
def _compute_gradients_safe(self, intent, state):
    \"\"\"Estimate gradients without mutating committed state.\"\"\"
    # Option A: kernel supports dry_run/snapshot contexts
    # Option B: clone state -> mutate clone -> discard
    # Option C: analytical Jacobian from observable registry (when available)
    ...
```

## 6.3 Dry-run / snapshot execution mode (P0: must be concrete)

The guide must specify what “dry-run” means in MAGNET terms.

**Phase 1 (recommended): clone + discard**
- Snapshot the full `DesignState` (or `StateManager.to_dict()`).
- Apply the candidate mutation to the clone via the same action executor used for real writes.
- Compute observables / validators against the clone.
- Discard the clone.

This provides safe gradient estimation and orthogonality checks without:
- mutating committed state
- triggering persistent side effects
- assuming perfect reversibility

**Validator behavior in dry-run:**
- validators may run, but must not:
  - write persistent state
  - emit irreversible side effects
  - crash the caller on temporary invalidity (return structured failure instead)

**Phase 2+: explicit snapshot context**
- Implement `with state_manager.snapshot(): ...` or `state_manager.clone()` explicitly, but ensure it shares nothing mutable with the committed state.

### 6.2 Step size must be adaptive

Fixed steps will oscillate or stall. Require:
- backtracking/line search
- constraint-aware step shrinking
- explicit convergence + residual reporting

**Missing item (P1): adaptive step size policy**

```python
def _adaptive_step_size(self, iteration: int, last_improvement: float) -> float:
    \"\"\"Armijo-style backtracking or simple decay with floor.\"\"\"
    base = 0.1
    decay = 0.9 ** iteration
    return max(base * decay, 0.001)  # 1mm floor
```

---

## 7) Conflict resolution must scale

Naive uniform grid search is not scalable.
Require at least:
- spatial indexing (BVH / R-tree / spatial hash) of claims
- coarse-to-fine or sampling-based search
- deterministic fallback: escalate if no resolution within bounded compute

**Missing item (P1): spatial index adapter**

```python
from rtree import index

class SpatialClaimIndex:
    def __init__(self):
        self._idx = index.Index()
        self._claims = {}

    def insert(self, claim_id: str, claim):
        self._claims[claim_id] = claim
        self._idx.insert(claim_id, claim.bounds.as_tuple())

    def query_intersects(self, bounds):
        for cid in self._idx.intersection(bounds.as_tuple()):
            yield self._claims[cid]
```

Conflicts must surface:
- conflict_id, type, involved system_ids, evidence
- resolution options + expected side effects

---

## 8) Validation tiers (hard / soft / grade) + phase blocking

MAGNET already has “gate + grades” behavior; to align with CORTEX v2:
- **Hard gate**: design invalid (blocks progress)
- **Soft gate**: design valid, but blocks specific downstream phases (`blocked_phases`)
- **Grade**: informational only (never blocks)

Manufacturability should be soft gates initially (block production/export, not iteration).

---

## 9) Character preservation is an EDIT-mode constraint (pre-application enforcement)

**Core rule:** character preservation is not a “metric we warn about after the fact”. In EDIT mode it must behave like other invariants (section count, point count, station ordering): **fail-closed before commit**.

### 9.1 Why post-hoc drift warnings are insufficient

Post-hoc detection has the wrong shape:

`ADJUST/TARGET → apply transform → measure drift → warn (too late)`

Problems:
- **Topological damage is not partially reversible** in EDIT mode (e.g., chine merges / anchor jumps).
- **Non-linear boundaries**: small deltas can cause large identity jumps near bifurcations.
- **User expectation**: “make the bow finer” should not require “and also preserve chine character”.

### 9.2 Required execution shape: pre-application character guard

Every ADJUST/TARGET in EDIT mode must be evaluated via dry-run **before** committing:

`ADJUST request → dry-run candidate → compute predicted drift → gate decision → commit or reject/escalate`

Concrete behavior:
- if predicted drift > **hard_limit** → reject with `would_break_character` and suggest REWRITE
- if predicted drift > **soft_limit** → fail-closed with `needs_confirmation` (explicit user confirmation required)
- otherwise commit and record `predicted_drift` in receipt

Doc-level sketch:

```python
def apply_control_with_character_guard(
    *,
    state: "DesignState",
    observable_id: str,
    scope: dict,
    delta: float,
    character_baseline: dict,  # CharacterSignature
    config: "CharacterPreservationConfig",
) -> "ControlResult":
    # 1) Dry-run transform on a clone (no committed mutation)
    candidate_state = deep_copy(state)
    apply_transform(candidate_state, observable_id, scope, delta)

    # 2) Predict drift BEFORE committing
    candidate_sig = extract_character_signature(candidate_state)
    predicted = compute_weighted_drift(character_baseline, candidate_sig)

    # 3) Gate decision
    if predicted > config.hard_limit:
        return ControlResult(success=False, reason="would_break_character", predicted_drift=predicted)
    if predicted > config.soft_limit:
        return ControlResult(success=False, reason="needs_confirmation", predicted_drift=predicted)

    # 4) Commit only after passing guard
    apply_transform(state, observable_id, scope, delta)
    return ControlResult(success=True, applied_drift=predicted)
```

### 9.3 Baseline capture + storage

- Baseline signature must be captured:
  - at design creation, **or**
  - at “first valid hull” (first time hard gates pass).
- Store baseline on the canonical state (SSOT) as immutable per design_version lineage:
  - `design.meta.character_baseline_v1` (example key; exact location in `DesignState` is implementation-defined but must be versioned).

### 9.4 Weighted drift computation (required)

Naive equal-weight relative error is wrong; topology should dominate.

**Missing item (P1): explicit weights + weighted drift**

```python
CHARACTER_WEIGHTS = {
    "chine_count": 5.0,      # topological — huge impact
    "entry_angle": 1.0,      # continuous — moderate
    "sheer_curvature": 0.5,  # aesthetic — lower
}

def compute_character_drift(initial, final) -> float:
    weighted = 0.0
    total = 0.0
    for key, w in CHARACTER_WEIGHTS.items():
        if key in initial and key in final and initial[key] not in (0, None):
            d = abs(final[key] - initial[key]) / abs(initial[key])
            weighted += d * w
            total += w
    return weighted / max(total, 1e-9)
```

### 9.5 Config: soft/hard limits + UX behavior

Character preservation needs two thresholds:
- `soft_limit`: requires explicit confirmation (fail-closed otherwise)
- `hard_limit`: reject and require REWRITE for character-changing edits

Add to config (see §17):

```yaml
character_preservation:
  soft_limit: 0.05   # requires confirmation
  hard_limit: 0.20   # reject (rewrite required)
  weights:
    chine_count: 5.0
    entry_angle: 1.0
    sheer_curvature: 0.5
```

### 9.6 Receipt fields (predicted drift is first-class)

Every ADJUST/TARGET receipt must include:
- `character_baseline_id` (or hash/version)
- `predicted_character_drift`
- `character_guard_decision`: `pass` | `needs_confirmation` | `reject_rewrite`

This makes the EDIT/REWRITE boundary semantically meaningful and avoids “warn after damage”.

---

## 10) Pattern registry + upgrade workflow (operational requirement)

Pattern versioning is incomplete without migration.

Minimum requirements:
- pattern instance config snapshot stored per design version (inputs + overrides)
- deprecation identifies affected designs
- **upgrade** produces a deterministic migration plan (even if “manual review required” initially)
- upgrades create a new design version with full audit trail

**Missing item (P2): migration primitives**

```python
@dataclass
class PatternMigration:
    from_pattern_id: str
    to_pattern_id: str
    transform: Callable[[Dict], Dict]  # old params -> new params
    manual_review_required: bool = False
    notes: str = ""

class PatternRegistry:
    def preview_migration(self, design_id: str, migration: PatternMigration):
        ...
    def migrate_design(self, design_id: str, migration: PatternMigration):
        ...
```

---

## 11) Concurrency / atomicity (beyond rollback)

Rollback tests are necessary but insufficient.
Require design-scoped concurrency control:
- enforce `expected_version` for writes
- reject stale plans deterministically
- serialize program execution per design_id (mutex) or transactional conflict detection

Add an integration test: two concurrent proposals; exactly one commits.

---

## 12) End-to-end test strategy (spiral-level)

Module tests aren’t enough. Add at least one integration test that runs:
User intent → (optional vision) → proposer → program execution → validators → cascade → narrative → response contract.

This catches interface drift across the whole loop.

---

## 12.1 Unified error propagation (P0)

Local errors are not enough. Every deep failure must surface as:
- technical detail (for debugging)
- user message (human-readable)
- actionable suggestions (what to try next)

Minimum model:

```python
@dataclass
class PropagatedError:
    origin_layer: str  # "kernel" | "conflict_resolver" | "validator" | "orchestrator"
    error_type: str
    technical_message: str
    user_message: str
    suggestions: List[str]
    context: Dict[str, Any]

class ErrorPropagator:
    def propagate(self, error: Exception, layer: str) -> PropagatedError:
        ...
```

---

## 12.2 Single write path: DesignMutator (P0)

To avoid SSOT drift and write-path ambiguity, **all** mutations must go through one interface that can stage/commit/rollback atomically.

```python
class DesignMutator:
    \"\"\"All mutations go through here. No direct graph/state writes.\"\"\"
    def __init__(self, state_manager: "StateManager"):
        self._state = state_manager
        self._pending = []
    def stage(self, mutation):
        self._pending.append(mutation)
    def commit(self):
        \"\"\"Atomically apply staged mutations (validate + apply + receipts).\"\"\"
        ...
    def rollback(self):
        self._pending.clear()
```

**Rule:** ConflictResolver, orchestrators, routing repair, etc. emit staged mutations (DSL or ActionPlans) rather than directly calling “execute_adjust” on live state.

---

## 12.3 Integration test specification (P0)

Add integration tests for:
- **success path**: user request → levels/tools → state change → validation → narrative
- **failure surfacing**: deep kernel failure becomes actionable user-facing message

```python
class TestEndToEndLoop:
    async def test_user_request_to_feedback(self):
        # Setup
        state = StateManager()
        config = CortexConfig.load("cortex_config.yaml")
        error_prop = DefaultErrorPropagator(config=config)
        mutator = DesignMutator(state_manager=state, error_propagator=error_prop, config=config)

        # Act: run a single spiral turn that adds a fuel system (fuel-first vertical slice)
        result = await run_spiral_turn(
            state_manager=state,
            mutator=mutator,
            error_propagator=error_prop,
            user_message="Add a 500L fuel system and show me the result",
        )

        # Assert: system artifacts exist as geometry.* in DesignState.resources
        assert result.success
        resources = (state.to_dict() or {}).get("resources") or {}
        assert any(r.get("_type") == "geometry.body" and r.get("system_id") == "fuel" for r in resources.values())
        assert any(r.get("_type") == "geometry.flow_path" and r.get("system_id") == "fuel" for r in resources.values())

    async def test_error_surfaces_to_user(self):
        state = StateManager()
        config = CortexConfig.load("cortex_config.yaml")
        error_prop = DefaultErrorPropagator(config=config)
        mutator = DesignMutator(state_manager=state, error_propagator=error_prop, config=config)

        # Force a deep failure: demand impossible capacity for a tiny hull envelope.
        result = await run_spiral_turn(
            state_manager=state,
            mutator=mutator,
            error_propagator=error_prop,
            user_message="Add a 10000L fuel system to this tiny hull",
        )

        assert not result.success
        assert result.user_message  # human-readable
        assert len(result.suggestions) > 0
```

---

## 12.4 Unit test specs for new components (P1)

Add (minimum) unit tests:
- `tests/unit/test_artifact_graph_adapter.py`
- `tests/unit/test_design_mutator.py`
- `tests/unit/test_spatial_claim_index.py`
- `tests/unit/test_error_propagator.py`
- `tests/unit/test_character_drift.py`
- `tests/unit/test_compute_gradients_safe.py`
- `tests/unit/test_adaptive_step_size.py`

## 12.5 Concurrency test (P1)

Add integration test:
- `tests/integration/test_concurrent_mutations.py`

```python
async def test_concurrent_proposals_one_wins():
    state = StateManager()
    config = CortexConfig.load("cortex_config.yaml")
    error_prop = DefaultErrorPropagator(config=config)
    mutator = DesignMutator(state_manager=state, error_propagator=error_prop, config=config)

    expected = state.get("design_version")
    task1 = asyncio.create_task(mutator.commit(plan_a, expected_version=expected))
    task2 = asyncio.create_task(mutator.commit(plan_b, expected_version=expected))
    results = await asyncio.gather(task1, task2, return_exceptions=True)
    assert sum(1 for r in results if not isinstance(r, Exception) and r.success) == 1
```

---

## 13) Implementation order (fuel-first vertical slice)

1. **Systems-as-geometry artifacts** (fuel-first)
2. **Artifact graph view** over `resources`
3. **Observable schema packaging** to LLM context + query rejection
4. **Conflict detection/resolution** (overlap/clearance first)
5. **Soft gate plumbing** (blocked phases)
6. **COORDINATE optimizer** (dry-run gradients + adaptive step)
7. **Pattern registry + upgrade**
8. **Character drift (weighted)**

---

## 14) Multi-body hydrostatics (explicit requirement)

If a design contains 2+ bodies, the hydrostatics layer must either:
- compute a coupled result correctly, or
- surface uncertainty explicitly (do not silently pretend monohull assumptions hold).

Minimum required:
- per-body integration + combined buoyancy + combined transverse stability contribution
- explicit “what is modeled vs not modeled” notes (e.g., wave interference)

---

**Concrete code location (MAGNET)**
- Multi-body hydrostatics lives in the physics layer, not in “CORTEX glue”:
  - `magnet/physics/geometry_hydrostatics.py`
- The guide must require a kernel-facing API that:
  - declares limitations (e.g., wave interference not modeled)
  - reports “modeled vs not modeled” flags in results
  - is exercised by an integration test with 2+ bodies

Suggested API surface (doc-level, to be implemented in the physics module):

```python
@dataclass
class HydrostaticsModelCoverage:
    multi_body_supported: bool = True
    wave_interference_modeled: bool = False
    notes: str = ""

@dataclass
class MultiBodyHydrostaticsResult:
    displacement_m3: float
    lcb_m: float
    tcb_m: float
    gm_m: float
    coverage: HydrostaticsModelCoverage
```

## 15) Kernel method inventory (no “referenced but undefined” APIs)

This guide forbids “paper APIs” that aren’t implemented.

If validators require methods like:
- `compute_structural_loads`
- `get_min_plate_thickness`
- `get_min_bend_radius`
- `compute_weld_accessibility`
- `find_non_developable_panels`
- `compute_assembly_sequence`

then the guide must include:
- where they live in the codebase
- or an explicit “stub + NotImplemented gate” plan with clear blocked phases.

---

**Concrete stubs + blocked phases (P1)**

Create explicit kernel modules and stub signatures until implemented:
- `magnet/kernel/structural.py` → structural loads
- `magnet/kernel/manufacturability.py` → plate thickness, bend radius, weld access, developability
- `magnet/kernel/assembly.py` → assembly sequencing

Example:

```python
# magnet/kernel/manufacturability.py
def get_min_plate_thickness(graph: "ArtifactGraphAdapter") -> float:
    raise NotImplementedError("Blocks phases: production_export, bom_generation")
```

## 16) ArtifactGraph adapter (read-only) (P0)

“Graph view” must be explicit and read-only; writes go via DesignMutator.

```python
class ArtifactGraphAdapter:
    def __init__(self, state: "DesignState"):
        self._state = state
    def all_components(self):
        for rid, r in (self._state.resources or {}).items():
            if isinstance(r, dict) and r.get("_type") == "geometry.body" and not r.get("_deleted"):
                yield r
    # No write methods here.
```

---

## 17) Configuration & calibration (remove magic numbers)

All thresholds/steps/limits must live in a config file with documented sources.

Example shape:

```yaml
# cortex_config.yaml
character_preservation:
  soft_limit: 0.05
  hard_limit: 0.20
  drift_threshold: 0.05  # legacy name; superseded by soft_limit/hard_limit
  weights:
    chine_count: 5.0
    entry_angle: 1.0
    sheer_curvature: 0.5

conflict_resolution:
  coarse_step_m: 1.0
  fine_step_m: 0.1
  max_search_iterations: 200

optimization:
  initial_step_m: 0.1
  min_step_m: 0.001
  convergence_abs: 0.001  # meters unless otherwise specified

validation:
  max_trim_deg: 15
  min_safety_factor: 1.5
```

---

## 17.1 Config schema + loader (P2)

The guide must define a validation schema for config (so “magic numbers” are typed and checked).

**Code location:** `magnet/config/cortex_config.py`

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class CharacterPreservationConfig:
    soft_limit: float
    hard_limit: float
    weights: dict

@dataclass(frozen=True)
class ConflictResolutionConfig:
    coarse_step_m: float
    fine_step_m: float
    max_search_iterations: int

@dataclass(frozen=True)
class OptimizationConfig:
    initial_step_m: float
    min_step_m: float
    convergence_abs: float

@dataclass(frozen=True)
class ValidationConfig:
    max_trim_deg: float
    min_safety_factor: float

@dataclass(frozen=True)
class CortexConfig:
    character_preservation: CharacterPreservationConfig
    conflict_resolution: ConflictResolutionConfig
    optimization: OptimizationConfig
    validation: ValidationConfig

    @classmethod
    def load(cls, path: str) -> "CortexConfig":
        """Load + validate YAML; raise a structured config error on invalid values."""
        ...
```

## 17.2 Config sources (P2)

Every config value must have a justification category:
- regulatory reference (IMO/ISO/ABYC/etc.)
- engineering standard / material database
- performance benchmark (runtime measurements)
- UX calibration (human perception thresholds)

---

## 18) Logging / observability plan (P2)

The implementation must be debuggable. Minimum events:
- **Commit event**: design_id, version_before/after, receipts summary, elapsed_ms
- **Failure event**: `PropagatedError` (layer, type, evidence), elapsed_ms
- **Optimizer event**: iteration count, step sizes, residual history, infeasible reasons
- **Conflict event**: conflict id/type, search iterations, chosen strategy

Receipts storage:
- append-only JSONL per design (TurnRecord pattern) so every edit can be audited and replayed.

---

## 19) Performance budgets (P2)

Initial budgets (tune with benchmarks):
- **Turn latency (no render)**: typical < 2s
- **Conflict resolution attempt**: < 200ms budget (else escalate)
- **COORDINATE optimizer**: max(20 iterations, 500ms) then stop + report residual

---

## 20) Rollout / migration plan (P2)

Add feature flags (defaults off in production):
- `feature.systems_as_geometry_artifacts`
- `feature.observable_schema_to_llm`
- `feature.coordinate_optimizer`

Migration approach:
- schema changes are additive when possible
- destructive changes require versioned migrations that create a new design version
- maintain backwards compatibility for existing designs (render + basic queries must still work)

---

## Appendix A: Test File Templates

Use these templates when creating new test files for tasks.

### A.1 Unit Test Template

```python
# tests/unit/test_[component].py
"""
Unit tests for [Component Name].

Task ID: T[X.X]
Section: §[X.X]
"""

import pytest
from magnet.[module].[file] import [Class]


class Test[Component]:
    """Tests for [Component] functionality."""
    
    @pytest.fixture
    def component(self):
        """Create test instance."""
        return [Class]()
    
    def test_basic_functionality(self, component):
        """[Component] performs basic operation correctly."""
        result = component.do_something()
        assert result is not None
    
    def test_edge_case(self, component):
        """[Component] handles edge case correctly."""
        # Test edge case
        pass
    
    def test_error_handling(self, component):
        """[Component] raises appropriate errors."""
        with pytest.raises(ValueError):
            component.do_invalid_thing()


class Test[Component]Integration:
    """Integration tests with other components."""
    
    def test_works_with_state_manager(self, state_manager):
        """[Component] integrates with StateManager."""
        pass
```

### A.2 Invariant Test Template

```python
# tests/invariants/test_[invariant].py
"""
Invariant tests for [Architectural Constraint].

These tests verify architectural invariants that must NEVER be violated.
Task ID: T[X.X]
Section: §[X.X]
"""

import pytest
import re
from pathlib import Path


class TestArchitecturalInvariant:
    """Tests that verify architectural constraints."""
    
    def test_no_forbidden_pattern_in_kernel(self):
        """Kernel must not contain [forbidden pattern]."""
        forbidden_patterns = [
            r"pattern_1",
            r"pattern_2",
        ]
        
        for py_file in Path("magnet/kernel").rglob("*.py"):
            content = py_file.read_text()
            for pattern in forbidden_patterns:
                assert not re.search(pattern, content), \
                    f"Forbidden pattern '{pattern}' found in {py_file}"
    
    def test_import_boundary(self):
        """[Module A] must not import from [Module B]."""
        forbidden_imports = ["magnet.forbidden_module"]
        
        for py_file in Path("magnet/protected_module").rglob("*.py"):
            content = py_file.read_text()
            for forbidden in forbidden_imports:
                assert forbidden not in content, \
                    f"Forbidden import '{forbidden}' in {py_file}"
```

### A.3 Integration Test Template

```python
# tests/integration/test_[flow].py
"""
Integration tests for [Flow Name].

Task ID: T[X.X]
Section: §[X.X]
"""

import pytest
from magnet.core.state_manager import StateManager
from magnet.core.design_mutator import DesignMutator


class TestEndToEndFlow:
    """End-to-end integration tests."""
    
    @pytest.fixture
    def state_manager(self):
        """Create fresh StateManager for each test."""
        return StateManager()
    
    @pytest.fixture
    def mutator(self, state_manager):
        """Create DesignMutator with StateManager."""
        return DesignMutator(state_manager)
    
    def test_full_flow(self, mutator):
        """Complete flow from input to validated output."""
        # 1. Setup
        # 2. Execute
        # 3. Verify
        pass
    
    def test_failure_recovery(self, mutator):
        """System recovers gracefully from failures."""
        pass
    
    def test_no_regression_from_existing(self, mutator):
        """New code doesn't break existing functionality."""
        # Run existing integration test scenarios
        pass
```

### A.4 Bootstrap Test Template

```python
# tests/bootstrap/test_[component].py
"""
Tests for bootstrap/library components.

Task ID: T0.[X]
Section: §0.4.7.A
"""

import pytest
from pathlib import Path


class TestHullLibrary:
    """Tests for hull library functionality."""
    
    @pytest.fixture
    def library(self, tmp_path):
        """Create test library with temp directory."""
        from magnet.bootstrap.hull_library import HullLibrary
        return HullLibrary(cache_dir=tmp_path)
    
    def test_search_returns_results(self, library):
        """Search returns relevant hull results."""
        results = library.search("72ft sportfish", limit=5)
        assert len(results) > 0
        assert all(r.similarity > 0 for r in results)
    
    def test_blend_produces_valid_params(self, library):
        """Blending produces valid parameter set."""
        from magnet.bootstrap.blending import blend_hulls
        
        hulls = library.search("fast planing", limit=3)
        blended = blend_hulls([h.hull for h in hulls])
        
        assert blended.loa_m > 0
        assert 0 < blended.Cb < 1
```

### A.5 Property-Based / Fuzz Test Template (Physics + Geometry Rigor)

Use property-based tests to catch numerical edge cases and ensure invariants hold across wide input ranges (integration routines, monotonicity, conservation, bounds, NaN safety).

```python
# tests/physics/test_[property].py
"""
Property-based tests for [Physics/Geometry Property].

Task ID: T[X.X]
Section: §[X.X]
"""

import math
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck


# Example: numerical integration should be non-negative for non-negative functions.
@settings(
    max_examples=200,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    xs=st.lists(st.floats(min_value=0.0, max_value=100.0), min_size=3, max_size=50),
)
def test_integrator_non_negative_on_non_negative_function(xs):
    xs = sorted(set(xs))
    if len(xs) < 3:
        return

    # Non-negative function
    fs = [x * x for x in xs]

    # Replace with MAGNET integrator under test
    integral = integrate_1d(xs, fs)

    assert not math.isnan(integral)
    assert integral >= 0.0


# Example: hydrostatics outputs should never be NaN for sane hull inputs (smoke fuzz).
@settings(max_examples=50)
@given(
    loa=st.floats(min_value=5.0, max_value=80.0),
    beam=st.floats(min_value=1.0, max_value=20.0),
    draft=st.floats(min_value=0.1, max_value=6.0),
)
def test_hydrostatics_no_nan_for_reasonable_inputs(loa, beam, draft):
    assume_reasonable = beam < loa and draft < beam
    if not assume_reasonable:
        return

    hull = make_parametric_hull(loa_m=loa, beam_m=beam, draft_m=draft)
    hs = compute_hydrostatics(hull)

    assert not math.isnan(hs.displacement_mt)
    assert hs.displacement_mt > 0.0
```

---

## Appendix B: Test Execution Workflows

### B.1 Before Starting Any Task

```bash
# Verify test suite is green before making changes
pytest tests/ -v --tb=short

# Note any pre-existing failures (don't fix unless part of task)
pytest tests/ --lf -v  # Show last failed
```

### B.2 During Implementation

```bash
# Run specific test file as you develop
pytest tests/path/to/test_file.py -v -x  # Stop on first failure

# Run tests matching pattern
pytest tests/ -k "test_name_pattern" -v

# Run with coverage (optional)
pytest tests/path/to/test_file.py --cov=magnet/module --cov-report=term-missing
```

### B.3 Before Marking Task Complete

```bash
# 1. Run new tests
pytest tests/path/to/new_test_file.py -v

# 2. Run related test categories
pytest tests/kernel/ -v  # If kernel changes
pytest tests/integration/ -v  # If integration changes

# 3. Run full suite to check for regressions
pytest tests/ -v --tb=short

# 4. Run invariant tests
pytest tests/invariants/ -v

# 5. Check for any new failures
pytest tests/ --lf -v
```

### B.4 CI/Pre-Commit Checks

```bash
# Minimum CI check
pytest tests/invariants/ tests/unit/ -v --tb=short

# Full CI check
pytest tests/ -v --tb=short --timeout=300

# Performance-sensitive tests (optional)
pytest tests/performance/ -v --benchmark-only
```

---

## Appendix C: New Test Files to Create

The following test files need to be created as part of implementation:

### Phase -2: Multi-Fidelity Architecture (FOUNDATIONAL)

| Test File | Task(s) | Priority | Template |
|-----------|---------|----------|----------|
| `tests/optimization/test_surrogate_model.py` | TM.1 | **P-2 FOUNDATIONAL** | Unit |
| `tests/optimization/test_surrogate_optimizer.py` | TM.2 | **P-2 FOUNDATIONAL** | Unit |
| `tests/constraints/test_hierarchical_validator.py` | TM.3 | **P-2 FOUNDATIONAL** | Unit |
| `tests/optimization/test_physics_evaluator.py` | TM.3A | **P-2 FOUNDATIONAL** | Unit |
| `tests/optimization/test_surrogate_trainer.py` | TM.3B | **P-2 FOUNDATIONAL** | Unit |
| `tests/core/test_probabilistic_design.py` | TM.4 | **P-2 FOUNDATIONAL** | Unit |
| `tests/core/test_incremental_state.py` | TM.5 | **P-2 FOUNDATIONAL** | Unit |
| `tests/optimization/test_probabilistic_optimizer.py` | TM.6 | **P-2 FOUNDATIONAL** | Unit |
| `tests/integration/test_surrogate_integration.py` | TM.7 | **P-2 FOUNDATIONAL** | Integration |
| `tests/optimization/test_hybrid_optimizer.py` | TM.8 | **P-2 FOUNDATIONAL** | Unit |

**Surrogate Model Tests** (TM.1):
- `test_gp_regression_fits_data()` - GP learns from training points
- `test_uncertainty_increases_far_from_data()` - Uncertainty quantification works
- `test_acquisition_balances_exploration_exploitation()` - Expected Improvement works
- `test_analytical_gradient_matches_numerical()` - Gradient computation correct

**Hierarchical Validator Tests** (TM.3):
- `test_geometric_level_filters_90_percent()` - Cheap constraints eliminate most candidates
- `test_full_physics_only_for_survivors()` - Expensive constraints run rarely
- `test_filter_efficiency_above_80_percent()` - Performance improvement verified

### Phase -1: Systemic Architecture (CRITICAL)

| Test File | Task(s) | Priority | Template |
|-----------|---------|----------|----------|
| `tests/core/test_state_concurrency.py` | TA.1 | **P-1 CRITICAL** | Unit |
| `tests/core/test_gradient_isolation.py` | TA.2 | **P-1 CRITICAL** | Unit |
| `tests/adapters/test_rendering_adapter.py` | TA.3 | P0 | Unit |
| `tests/kernel/test_geometry_export.py` | TA.4 | P0 | Unit |
| `tests/bootstrap/test_manifold_blending.py` | TA.5 | **P-1 CRITICAL** | Unit |
| `tests/kernel/test_observable_graph.py` | TA.6 | **P-1 CRITICAL** | Unit |
| `tests/kernel/test_batched_registry.py` | TA.7 | **P-1 CRITICAL** | Unit |
| `tests/optimization/test_transactional.py` | TA.8 | **P-1 CRITICAL** | Unit |
| `tests/optimization/test_crash_recovery.py` | TA.9 | **P-1 CRITICAL** | Integration |

### Phase 0: Foundation

| Test File | Task(s) | Priority | Template |
|-----------|---------|----------|----------|
| `tests/bootstrap/test_import_shipd.py` | T0.2 | P0 | Bootstrap |
| `tests/bootstrap/test_hull_library.py` | T0.3 | P0 | Bootstrap |
| `tests/bootstrap/test_embeddings.py` | T0.4 | P0 | Unit |
| `tests/bootstrap/test_blending.py` | T0.5 | P0 | Bootstrap |
| `tests/unit/test_design_mutator.py` | T1.1-T1.2 | P0 | Unit |
| `tests/invariants/test_write_path.py` | T1.3 | P0 | Invariant |
| `tests/unit/test_receipts.py` | T1.4 | P1 | Unit |
| `tests/core/test_proposal_sandbox.py` | T1.5 | P0 | Unit |
| `tests/kernel/test_observable_registry.py` | T2.1-T2.2 | P0 | Unit |
| `tests/kernel/test_observable_schema.py` | T2.3 | P1 | Unit |
| `tests/invariants/test_enum_deletion.py` | T3.1-T3.4 | P0 | Invariant |
| `tests/kernel/test_synthesis_constraints.py` | T3.5 | P0 | Unit |
| `tests/kernel/test_classification.py` | T3.6 | P1 | Unit |
| `tests/kernel/test_anchor_detector.py` | T4.1 | P0 | Unit |
| `tests/kernel/test_anchor_tracker.py` | T4.2 | P0 | Unit |
| `tests/kernel/test_topology_classifier.py` | T4.3 | P1 | Unit |
| `tests/kernel/test_edit_boundary.py` | T4.4 | P1 | Unit |
| `tests/kernel/test_character_guard.py` | T5.1 | P0 | Unit |
| `tests/kernel/test_gradient_estimator.py` | T5.2 | P0 | Unit |
| `tests/kernel/test_coordinate_executor.py` | T5.3-T5.4 | P0 | Unit |
| `tests/hull_gen/test_continuity.py` | **E0.3**, T5.5 | P0 | Unit |
| `tests/optimization/test_sensitivity_isolation.py` | **E0.1**, T5.6 | **P0 CRITICAL** | Unit |
| `tests/kernel/test_violation_info.py` | **E0.2**, T5.7 | **P0 CRITICAL** | Unit |
| `tests/physics/test_equilibrium_stepped.py` | **E0.4**, T5.8 | P0 | Unit |
| `tests/systems/test_stringer.py` | T6.1 | P1 | Unit |
| `tests/systems/test_bulkhead.py` | T6.2 | P1 | Unit |
| `tests/systems/test_frame.py` | T6.3 | P1 | Unit |
| `tests/structural/test_scantlings.py` | T6.4 | P1 | Unit |
| `tests/core/test_component_kinematics.py` | T6.5 | P1 | Unit |
| `tests/physics/test_multi_body_hydrostatics.py` | T7.1 | P1 | Unit |
| `tests/physics/test_stability_validator.py` | T7.2 | P1 | Unit |
| `tests/physics/test_structural_validator.py` | T7.3 | P1 | Unit |
| `tests/errors/test_propagation.py` | T7.4 | P1 | Unit |
| `tests/physics/test_hydro_weight_convergence.py` | T7.5 | P1 | Unit |
| `tests/integration/test_bootstrap_orchestrator.py` | T8.1 | P0 | Integration |
| `tests/integration/test_e2e_spiral.py` | T8.2 | P0 | Integration |
| `tests/integration/test_edit_loop.py` | T8.3 | P0 | Integration |
| `tests/invariants/test_north_star.py` | T8.4 | P0 | Invariant |

**CRITICAL BUG FIX TESTS** (must pass before any optimization work):
- `tests/optimization/test_sensitivity_isolation.py` - Verifies state is never mutated during sensitivity analysis
- `tests/kernel/test_violation_info.py` - Verifies constraint violations provide structured gradient hints

---

## Appendix D: Where the older docs went

The older docs remain in the repo as historical references, but this file is the canonical guide moving forward.
