# MAGNET CLI v1 Architecture — Kernel-First Design

## Core Principle

**Every rule lives in kernel. Every interface is dumb.**

This document describes the CLI v1 architecture implemented in December 2024. It establishes the foundational pattern for all MAGNET interfaces: the kernel owns all business logic, and UI/CLI layers are stateless adapters.

---

## The Problem Solved

Prior to CLI v1, the chat interface duplicated kernel logic:

| UI Duplicate | Kernel Original | Problem |
|--------------|-----------------|---------|
| `REFINEMENT_CONSTRAINTS` in chat.py | Should be in kernel | Two sources of truth for bounds |
| `phase_report_from_result()` in chat.py | `PhaseResult.to_dict()` | Duplicate serialization logic |
| Direct `_session.completed_phases` manipulation | `PhaseMachine.invalidate_downstream()` | Bypasses kernel state machine |
| Custom clamping logic in UI | Should be kernel-owned | Bounds scattered across codebase |

**Result**: Inconsistent behavior, hard-to-debug issues, and architectural violations.

---

## The Solution: Wire, Don't Write

CLI v1 follows the "wire, don't write" principle:

1. **Extend existing kernel classes** (~80 lines) instead of creating new parallel structures
2. **Use existing infrastructure** that was built but never wired
3. **Delete UI duplicates** and delegate to kernel

---

## Key Components

### 1. Parameter Bounds (`magnet/core/parameter_bounds.py`)

Kernel-owned bounds for all refinable parameters:

```python
from magnet.core.parameter_bounds import validate_and_clamp, get_bounds

# Validate and clamp a value
clamped, warnings = validate_and_clamp("mission.max_speed_kts", 150)
# Returns: (100.0, ["mission.max_speed_kts clamped from 150 to 100"])

# Get bounds for a parameter
bounds = get_bounds("hull.loa")
# Returns: {"min": 5, "max": 200, "type": float}
```

**Location**: `magnet/core/parameter_bounds.py`

### 2. Conductor Extensions (`magnet/kernel/conductor.py`)

Two new methods on Conductor:

#### `run_default_pipeline()`

CLI-safe subset that runs only stable phases:

```python
def run_default_pipeline(self, context=None) -> List[PhaseResult]:
    """Run hull → weight → stability (safe subset)."""
    default_phases = ["hull", "weight", "stability"]
    # Does NOT run structure/propulsion/loading/production
```

**Why**: `run_all_phases()` runs all 13 phases, which breaks if incomplete phases exist.

#### `apply_refinement()`

Kernel-owned refinement with bounds, clamping, and invalidation:

```python
results = conductor.apply_refinement(
    path="mission.max_speed_kts",
    op="increase",  # "increase", "decrease", or "set"
    amount=5.0,
    phase_machine=phase_machine,  # Optional, for invalidation
)
```

**Key behaviors**:
- Uses `validate_and_clamp()` from parameter_bounds
- Logs warnings if value was clamped
- Determines affected phase (mission.* → hull, hull.* → structure)
- Calls `PhaseMachine.invalidate_downstream()` if provided
- Re-runs default pipeline

### 3. DesignExporter Extension (`magnet/glue/lifecycle/exporter.py`)

New method for exports with phase reports:

```python
exporter = DesignExporter(state)
session = conductor.get_session()

json_str = exporter.export_with_phase_report(session=session)
```

**Uses**: `PhaseResult.to_dict()` for canonical serialization — no duplicate logic.

### 4. Wired Chat Handler (`magnet/ui/chat.py`)

`_apply_refinement()` now delegates to kernel:

```python
def _apply_refinement(self, refinement: RefinementUpdate) -> str:
    # CLI v1: Delegate to Conductor.apply_refinement()
    if self.conductor and hasattr(self.conductor, 'apply_refinement'):
        results = self.conductor.apply_refinement(
            path=path,
            op=refinement.action or "set",
            amount=refinement.amount,
        )
        # Kernel owns bounds, clamping, invalidation
```

---

## P0 Architectural Corrections

### P0 #1: No Direct Session Manipulation

```python
# ❌ BAD - direct list surgery
self._session.completed_phases.remove(phase)

# ✅ GOOD - use PhaseMachine
phase_machine.invalidate_downstream(affected_phase)
```

### P0 #2: No Kitchen-Sink Runner as Default

```python
# ❌ BAD - runs all 13 phases, breaks on incomplete
conductor.run_all_phases()

# ✅ GOOD - CLI-safe subset
conductor.run_default_pipeline()  # hull → weight → stability
```

---

## Files Changed

| File | Changes |
|------|---------|
| `magnet/core/parameter_bounds.py` | NEW: Kernel-owned bounds |
| `magnet/kernel/conductor.py` | ADDED: `run_default_pipeline()`, `apply_refinement()` |
| `magnet/glue/lifecycle/exporter.py` | ADDED: `export_with_phase_report()` |
| `magnet/ui/chat.py` | DELETED: `REFINEMENT_CONSTRAINTS`, `phase_report_from_result()`, `PendingClarification`. WIRED: to Conductor, ClarificationManager |
| `scripts/chat_cli.py` | WIRED: export to DesignExporter |
| `magnet/kernel/conductor.py` | ADDED: internal `_phase_machine` for automatic invalidation |

---

## Infrastructure Already Built (Now Wired)

The CLI v1 work revealed 12+ orphaned systems. Here's what exists and how to use it:

| System | Location | Status |
|--------|----------|--------|
| `PhaseMachine.invalidate_downstream()` | `core/phase_states.py:492-519` | **WIRED** via Conductor internal `_phase_machine` |
| `InvalidationEngine.invalidate_parameter()` | `dependencies/invalidation.py:149-222` | Available for fine-grained invalidation |
| `ClarificationManager` | `agents/clarification.py` | **WIRED** in ChatHandler (replaces PendingClarification) |
| `DesignExporter.export()` | `glue/lifecycle/exporter.py` | **WIRED** in CLI export |
| `CycleExecutor` | `glue/protocol/executor.py` | ORPHANED - propose→validate→revise loop |
| `TransactionManager` | `glue/transactions/manager.py` | ORPHANED - ACID model |
| `ErrorHandler` | `glue/errors/recovery.py` | ORPHANED - recovery strategies |
| `NarrativeGenerator` | `glue/explanation/narrative.py` | ORPHANED - change explanations |
| `TraceCollector` | `glue/explanation/trace.py` | ORPHANED - audit trails |

---

## For Future Agents

When implementing new features:

1. **Check if infrastructure exists** — Many systems are built but not wired
2. **Don't duplicate logic in UI** — All rules live in kernel
3. **Use `run_default_pipeline()`** — Not `run_all_phases()` for CLI
4. **Use `apply_refinement()`** — Not manual clamping in UI
5. **Use `export_with_phase_report()`** — Not custom JSON building

---

## Proof Tests

To verify CLI v1 is working:

1. **Test A**: "make it faster" → `apply_refinement()` triggers → hull regenerates
2. **Test B**: Missing input → `check_phase_inputs()` → blocks until answered
3. **Test C**: Export → `export_with_phase_report()` → includes validator IDs

---

**Every rule lives in kernel. Every interface is dumb. The kernel already has the rules.**
