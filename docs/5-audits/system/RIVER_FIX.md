# The River That Stays Wet: API Phase Execution Fix

<!-- AGENT_CONTEXT
Purpose: Documents fix for API phase execution where physics calculations were not persisting
Authoritative: Yes
Keywords: api, phase, persistence, conductor, validator, physics, bugfix, spiral_endpoints
Depends_On: 0-architecture/core/PHASE_MACHINE.md
Used_By: developers, debugging
Status: current
Last_Verified: 2026-01-15
-->


**Date:** January 15, 2026
**Status:** Implemented and Tested
**Location:** `magnet/deployment/spiral_endpoints.py` lines 867-918

---

## The Problem: A River That Forgot Its Water

When the API executed phases via `spiral_endpoints.py`, the physics calculations (displacement, VCB, BM) were computed but **never persisted**. The next API request would load from DesignStore and find the riverbed dry.

### Root Cause Chain

```
API creates Conductor → no PipelineExecutor → legacy fallback → empty _validators → "completed" with no physics
```

The Conductor was instantiated without validator wiring:

```python
# BEFORE (broken):
conductor = Conductor(state_manager=sm)
for p in phases:
    res = conductor.run_phase(p)
```

This caused:
1. `Conductor._pipeline_executor` was `None`
2. Conductor fell back to legacy `_execute_phase()` method
3. Legacy method checked `self._validators` dict - which was **empty**
4. All validators returned "not registered" warnings
5. Phase "completed" without computing any physics
6. DesignStore saved empty state

---

## The Fix: Wire the River

The fix ensures validators flow into the Conductor before phase execution:

```python
# AFTER (fixed):
from magnet.validators.registry import ValidatorRegistry
from magnet.validators.topology import ValidatorTopology
from magnet.validators.executor import PipelineExecutor
from magnet.validators.builtin import get_all_validators

# 1. Initialize validator registry (the spring)
if not ValidatorRegistry._initialized:
    ValidatorRegistry.reset()
    ValidatorRegistry.initialize_defaults()
    ValidatorRegistry.instantiate_all()

# 2. Build topology (the channel)
topology = ValidatorTopology()
for defn in get_all_validators():
    topology.add_validator(defn)
topology.build()

# 3. Create wired executor (the current)
executor = PipelineExecutor(
    topology=topology,
    state_manager=sm,
    validator_registry=ValidatorRegistry.get_all_instances(),
)

# 4. Wire Conductor (connect spring to river)
conductor = Conductor(state_manager=sm)
conductor.set_pipeline_executor(executor)

# 5. Run phases (let water flow)
for p in phases:
    res = conductor.run_phase(p)

# 6. Pour into reservoir (persist)
conductor.write_to_state()
```

The existing `DesignStore.save()` at line 983 then persists the computed values.

---

## Flow Diagram

```
                    ┌─────────────────────────┐
                    │   ValidatorRegistry     │
                    │   (the spring)          │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │   ValidatorTopology     │
                    │   (the channel)         │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │   PipelineExecutor      │
                    │   (the current)         │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │      Conductor          │
                    │   (carries water)       │
                    └───────────┬─────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
            ┌──────────────┐       ┌──────────────┐
            │  run_phase() │       │  run_phase() │
            │   (hull)     │       │  (weight)    │
            └──────────────┘       └──────────────┘
                    │                       │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │  conductor.write_to_   │
                    │       state()          │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │   DesignStore.save()   │
                    │   (the lake)           │
                    └─────────────────────────┘
```

---

## Validation

### Tests Added
- `tests/integration/test_phase_persistence.py`

### Tests Passing
- `test_ui_spiral.py` - 7 passed, 5 skipped
- `test_phase_persistence.py` - 4 passed
- `test_phase_execution.py::test_hull_phase_produces_outputs` - passed

### Pre-existing Failures (Not Related)
- `test_run_mission_phase` - Missing bounds validators (pre-existing)
- `test_weight_phase_produces_outputs` - equilibrium_draft failure (pre-existing)

---

## Key Insight

> The legacy path isn't broken, it's just empty. It runs fine — it just has nothing to run.

The fix doesn't change the Conductor's behavior. It ensures the Conductor **has validators to run** when invoked from the API.

---

## Related Files

| File | Change |
|------|--------|
| `magnet/deployment/spiral_endpoints.py` | Added validator wiring (lines 871-914) |
| `tests/integration/test_phase_persistence.py` | New test file |
| `docs/RIVER_FIX.md` | This documentation |

---

## Remaining Work

The audit identified additional gaps that were NOT fixed in this change:

1. **PATCH endpoint persistence** - The `/api/v1/designs/{id}` PATCH endpoint may have a similar persistence gap
2. **Observability** - No metrics/logging for physics anomalies
3. **User-friendly errors** - Technical error messages exposed to users
4. **VCB convention** - Negative VCB values need documentation

See `AGENT_IMPLEMENTATION.md` for details on these remaining tasks.
