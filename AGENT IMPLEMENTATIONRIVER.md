# Agent Implementation Plan: API Phase Execution Fixes

**Created:** January 15, 2026
**Updated:** January 15, 2026
**Priority:** High
**Scope:** Fix persistence gap, add observability, improve UX, verify VCB

---

## Status Summary

| Task | Status | Notes |
|------|--------|-------|
| Task 1: Persistence Fix | **COMPLETE** | Implemented in `spiral_endpoints.py`, tested |
| Task 2: Observability | Pending | Not started |
| Task 3: User-Friendly Errors | Pending | Not started |
| Task 4: VCB Verification | Pending | Not started |
| Task 5: Silence #1 Cut | **COMPLETE** | KG fallback removed, GM<0 = FAILED |

---

## Task 1: Fix Phase Execution Persistence (HIGH PRIORITY)

### Status: **COMPLETE**

### Problem
Phase outputs (`hull.displacement_m3`, `hull.vcb_m`, `hull.bm_m`) exist only in request-scoped StateManager memory. They are lost when the next API call loads from DesignStore.

### Root Cause
The Conductor was created without PipelineExecutor wiring, causing it to fall back to legacy execution with an empty `_validators` dict.

### Solution Implemented
Added validator wiring in `magnet/deployment/spiral_endpoints.py` lines 871-914:

```python
# Wire the river: ensure validators flow into the Conductor
if not ValidatorRegistry._initialized:
    ValidatorRegistry.reset()
    ValidatorRegistry.initialize_defaults()
    ValidatorRegistry.instantiate_all()

# Build topology from validator definitions
topology = ValidatorTopology()
for defn in get_all_validators():
    topology.add_validator(defn)
topology.build()

# Create wired executor
executor = PipelineExecutor(
    topology=topology,
    state_manager=sm,
    validator_registry=ValidatorRegistry.get_all_instances(),
)

# Now the Conductor has water to carry
conductor = Conductor(state_manager=sm)
conductor.set_pipeline_executor(executor)

# ... run phases ...

# Pour the water into the reservoir
conductor.write_to_state()
```

### Validation
- `tests/integration/test_ui_spiral.py` - 7 passed, 5 skipped
- `tests/integration/test_phase_persistence.py` - 4 passed
- `tests/integration/test_phase_execution.py::test_hull_phase_produces_outputs` - passed

### Documentation
- `MAGNETV1/docs/RIVER_FIX.md` - Full technical documentation

---

## Task 2: Add Physics Observability (MEDIUM PRIORITY)

### Status: Pending

### Problem
No metrics, logging, or alerting when physics calculations return anomalous values. Silent failures go undetected.

### Location
`magnet/physics/validators.py`

### Required Changes

#### 2.1 Add Anomaly Detection in HydrostaticsValidator

```python
# In magnet/physics/validators.py, inside HydrostaticsValidator.validate()

import logging
logger = logging.getLogger("physics.observability")

# After computing hydrostatics results:
def _check_physics_anomalies(self, result: dict, state_manager) -> list:
    """Detect and log physics anomalies."""
    anomalies = []

    displacement = result.get("displacement_m3", 0)
    gm = result.get("gm_transverse_m") or result.get("gm_m", 0)
    vcb = result.get("vcb_m", 0)
    bm = result.get("bm_m", 0)

    # Zero/negative displacement
    if displacement <= 0.01:
        anomalies.append({
            "type": "zero_displacement",
            "value": displacement,
            "severity": "critical",
        })
        logger.error(f"PHYSICS_ANOMALY: displacement={displacement}m³ (expected > 0)")

    # Severe negative GM (capsized)
    if gm < -1.0:
        anomalies.append({
            "type": "severe_negative_gm",
            "value": gm,
            "severity": "critical",
        })
        logger.error(f"PHYSICS_ANOMALY: GM={gm}m (severe instability)")

    # VCB sanity check (should typically be 0.4T to 0.6T)
    draft = state_manager.get("hull.draft", 1.5)
    expected_vcb_min = draft * 0.3
    expected_vcb_max = draft * 0.7
    if vcb < expected_vcb_min or vcb > expected_vcb_max:
        anomalies.append({
            "type": "unusual_vcb",
            "value": vcb,
            "expected_range": [expected_vcb_min, expected_vcb_max],
            "severity": "warning",
        })
        logger.warning(f"PHYSICS_ANOMALY: VCB={vcb}m outside typical range [{expected_vcb_min:.2f}, {expected_vcb_max:.2f}]")

    return anomalies
```

### Acceptance Criteria
- [ ] Anomalies logged with `PHYSICS_ANOMALY:` prefix for easy grep
- [ ] Critical anomalies (zero displacement, severe negative GM) logged at ERROR level
- [ ] Warnings for unusual but potentially valid values
- [ ] Counts accessible via `get_anomaly_counts()` for monitoring

---

## Task 3: Improve User-Facing Error Messages (MEDIUM PRIORITY)

### Status: Pending

### Problem
Errors like "Phase hull missing required OUTPUTS: ['hull.displacement_m3']" are developer-speak, not user-friendly.

### Location
`magnet/validators/contracts.py` and `magnet/deployment/api.py`

### Required Changes

Create `magnet/validators/error_messages.py`:

```python
"""User-friendly error message translations."""

from typing import Dict, Optional

# Map technical paths to user-friendly descriptions
PATH_DESCRIPTIONS: Dict[str, str] = {
    "hull.lwl": "hull length at waterline",
    "hull.beam": "hull beam (width)",
    "hull.draft": "hull draft (depth below waterline)",
    "hull.depth": "hull depth",
    "hull.cb": "block coefficient",
    "hull.displacement_m3": "hull displacement volume",
    "hull.vcb_m": "vertical center of buoyancy",
    "hull.bm_m": "metacentric radius",
    "weight.lightship_weight_mt": "lightship weight",
    "weight.lightship_vcg_m": "lightship vertical center of gravity",
    "stability.gm_transverse_m": "transverse metacentric height (GM)",
}

def translate_missing_inputs(phase: str, missing: list) -> str:
    """Generate user-friendly message for missing inputs."""
    friendly = [PATH_DESCRIPTIONS.get(p, p) for p in missing]
    if len(friendly) == 1:
        return f"Please specify the {friendly[0]} before running the {phase} phase."
    else:
        items = ", ".join(friendly[:-1]) + f" and {friendly[-1]}"
        return f"Please specify the {items} before running the {phase} phase."
```

### Acceptance Criteria
- [ ] All ContractResults include `user_message` field
- [ ] User messages are plain English, no technical paths
- [ ] API responses include both `message` (technical) and `user_message` (friendly)
- [ ] UI can display `user_message` directly to users

---

## Task 4: Verify VCB Coordinate Convention (LOW PRIORITY)

### Status: Pending

### Problem
Negative `vcb_m` values may be correct (Z=0 at waterline convention) or may indicate a bug. Needs investigation and documentation.

### Location
`magnet/physics/geometry_hydrostatics.py`

### Required Changes

1. Document coordinate convention in docstring
2. Add sanity check for unusual VCB values
3. Create test case for VCB sign convention

### Acceptance Criteria
- [ ] Coordinate convention documented in docstring
- [ ] Sanity check warns on unusual VCB values
- [ ] Test case verifies VCB is positive for simple geometries
- [ ] Any bugs found are documented and fixed

---

## Implementation Order

1. ~~**Task 1 (Persistence)**~~ - **COMPLETE**
2. **Task 2 (Observability)** - Enables detection of future issues
3. **Task 3 (UX)** - Improves user experience
4. **Task 4 (VCB)** - Investigation/documentation
5. ~~**Task 5 (Silence #1 Cut)**~~ - **COMPLETE** - Remove silent validator compensation

---

## Task 5: Cut Silence #1 (HIGH PRIORITY)

### Status: **COMPLETE** (v1.3 North Star Aligned)

### Problem
Validators silently compensated for missing data, allowing unsafe designs to proceed:
1. KG estimated as `0.55 * depth` when not provided (no physics basis)
2. "Still proceed" pattern after stability warnings

### Solution Implemented

**`magnet/stability/validators.py` v1.3:**
- Removed `kg_m = 0.55 * depth` fallback (lines 113-123)
- KG must come from `stability.kg_m` or `weight.lightship_vcg_m`
- If KG unavailable, validator returns `FAILED` state

**`magnet/weight/validators.py` v1.3 (North Star Aligned):**
- **v1.2 (superseded):** Made GM < 0 a FAILED gate — **violated North Star Law 6**
- **v1.3 (current):** Negative GM returns `ValidatorState.WARNING` with suggested fix
- North Star: "Hydrostatics is the only hard gate. Everything else is a grade."
- The system warns and suggests; the human decides

### Validation
- `tests/unit/test_stability_validators.py` - 20 passed
- `tests/unit/test_weight_validators.py` - 17 passed
- `tests/integration/test_phase_persistence.py` - 4 passed

### Documentation
- `ZENFLOW_ALIGNMENT.md` - Updated Silence #1 to FIXED status

---

## Files Modified

| File | Task | Status |
|------|------|--------|
| `magnet/deployment/spiral_endpoints.py` | 1 | **COMPLETE** - Added validator wiring |
| `tests/integration/test_phase_persistence.py` | 1 | **COMPLETE** - New test file |
| `docs/RIVER_FIX.md` | 1 | **COMPLETE** - Documentation |
| `magnet/stability/validators.py` | 5 | **COMPLETE** - v1.3: KG fallback removed |
| `magnet/weight/validators.py` | 5 | **COMPLETE** - v1.3: GM<0 = WARNING (North Star) |
| `tests/unit/test_stability_validators.py` | 5 | **COMPLETE** - Updated test |
| `tests/unit/test_weight_validators.py` | 5 | **COMPLETE** - Updated test |
| `magnet/physics/validators.py` | 2 | Pending |
| `magnet/physics/metrics.py` | 2 | Pending |
| `magnet/validators/error_messages.py` | 3 | Pending |
| `magnet/validators/contracts.py` | 3 | Pending |
| `magnet/physics/geometry_hydrostatics.py` | 4 | Pending |
| `tests/physics/test_vcb_convention.py` | 4 | Pending |

---

## The River Metaphor

> When a phase runs but leaves no trace, it has not truly happened.

**Task 1 fixed the river:**
- **Spring:** `ValidatorRegistry.initialize_defaults()` populates validators
- **Channel:** `ValidatorTopology` orders them correctly
- **Current:** `PipelineExecutor` runs them through the Conductor
- **Reservoir:** `conductor.write_to_state()` + `DesignStore.save()` persists

The river now stays wet.

---

## Rollback Plan

If issues arise after deployment:

1. **Task 1 rollback:** Revert `spiral_endpoints.py` changes (data won't persist but won't corrupt)
2. **Task 2 rollback:** Remove logging calls (silent but functional)
3. **Task 3 rollback:** Remove user_message field (technical errors still work)
4. **Task 4 rollback:** Remove validation warnings (no functional impact)

All changes are additive and can be rolled back independently.
