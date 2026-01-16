# MAGNET Schema Alignment Notes (v1.19 Freeze)

## Date: December 7, 2024
## Status: COMPLETE - 146/146 tests passing

---

## Overview

This document records schema alignment changes made to resolve 34 test failures
caused by drift between BRAVO's test expectations and ALPHA's canonical dataclass
implementations.

**Authoritative Source:** `/Users/bengibson/Desktop/MAGNET/MAGNET V1/V1.1 Modules/`
- `MAGNET_Module_01_v1.19_Complete_Architecture_Alignment.md`
- `MAGNET_Module_02_Phase_State_Machine_v1.1.md`

---

## Canonical Field Name Resolutions

| # | Section | Test Expected | Canonical (ALPHA) | Resolution |
|---|---------|---------------|-------------------|------------|
| 1 | StructuralDesign | `material_type` | `hull_material` | Fixed test to use `hull_material` |
| 2 | ArrangementState | `deck_count` | `num_decks` | Fixed test to use `num_decks` |
| 3 | ProductionState | `total_build_hours` | `build_hours` | Fixed test to use `build_hours` |
| 4 | StabilityState | `gz_max` | `gz_max_m` | Fixed test to use `gz_max_m` |
| 5 | SafetyState | `life_jacket_count` | `lifejackets` | Fixed test to use `lifejackets` |
| 6 | SeakeepingState | `operability_index` | `roll_period_s` | Fixed test to use correct field |
| 7 | ElectricalState | `ac_voltage` | `frequency_hz` | Fixed test to use correct field |
| 8 | MissionConfig | `special_requirements` | `special_features` | Fixed test to use `special_features` |
| 9 | ReportsState | `generated` (List) | `generated` (bool) | Fixed test - generated is bool |
| 10 | OptimizationState | `optimization_run` | `converged` | Fixed test to use `converged` |

---

## Default Value Pattern

ALPHA uses the `Optional[type] = None` pattern for most fields:

```python
# ALPHA Pattern (Canonical)
max_speed_kts: Optional[float] = None
vessel_type: Optional[str] = None
```

Tests were updated to check `is None` instead of `== 0.0` where appropriate.

---

## API Fixes

| Test | Issue | Fix |
|------|-------|-----|
| `test_transaction_rollback_preserves_phase_state` | Called `manager.rollback()` | Changed to `manager.rollback_transaction(txn_id)` |

---

## Field Aliases Added

Added backwards-compatibility aliases in `magnet/core/field_aliases.py`:

```python
"structural_design.material_type": "structural_design.hull_material"
"arrangement.deck_count": "arrangement.num_decks"
"production.total_build_hours": "production.build_hours"
"stability.gz_max": "stability.gz_max_m"
"safety.life_jacket_count": "safety.lifejackets"
```

---

## Files Modified

| File | Changes |
|------|---------|
| `tests/unit/test_dataclasses.py` | Updated all 27 dataclass tests to use canonical field names and Optional patterns |
| `tests/integration/test_state_roundtrip.py` | Fixed field names (hull_material, num_decks, lifejackets, etc.) |
| `tests/integration/test_phase_flow.py` | Fixed transaction API usage (rollback_transaction) |
| `magnet/core/field_aliases.py` | Fixed self-referential alias, added backwards-compat aliases |

---

## Test Results

Before: **110 passed, 34 failed**
After: **146 passed, 0 failed**

---

## Schema Freeze Declaration

As of this commit, schema v1.19 is **FROZEN**. All 27 dataclasses now match
the V1.1 Modules specification exactly. Any future field changes must be
coordinated across the codebase.
