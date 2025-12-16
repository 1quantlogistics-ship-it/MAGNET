# Intent→Action Protocol Architecture

## Overview

The Intent→Action Protocol is the **firewall between LLM proposals and kernel state mutations**. It ensures that:

1. **LLM never directly drives state** — All proposals are validated before execution
2. **All mutations are deterministic** — Unit conversion, bounds clamping, type coercion
3. **Stale plans are detected** — `design_version_before` must match current state
4. **Parameter locks are enforced** — Locked parameters cannot be modified
5. **Everything is auditable** — Full trace from user intent to state mutation

---

## Core Invariant

```
LLM proposes → Kernel validates → Kernel executes (or rejects)
```

The LLM can **propose** any action. The kernel **decides** whether to execute it.

---

## Type Hierarchy

```
User Input (raw text)
    │
    ▼
Intent (structured understanding)
    │
    ▼
ActionPlan (list of proposed Actions)
    │
    ▼
ActionPlanValidator.validate()
    │
    ├─── ValidationResult.approved (normalized actions)
    │
    ├─── ValidationResult.rejected (actions + reasons)
    │
    └─── ValidationResult.warnings (clamping notices)
    │
    ▼
ActionExecutor.execute() [coming soon]
    │
    ▼
ActionResult (execution outcome)
```

---

## Module Locations

| Module | Location | Purpose |
|--------|----------|---------|
| `intent_protocol.py` | `magnet/kernel/intent_protocol.py` | Core types: Intent, Action, ActionPlan, ActionResult |
| `action_validator.py` | `magnet/kernel/action_validator.py` | ActionPlanValidator — validates/clamps/rejects |
| `refinable_schema.py` | `magnet/core/refinable_schema.py` | REFINABLE_SCHEMA whitelist |
| `unit_converter.py` | `magnet/core/unit_converter.py` | Deterministic unit conversion |
| `design_state.py` | `magnet/core/design_state.py` | Contains `design_version` counter |
| `state_manager.py` | `magnet/core/state_manager.py` | Lock methods, `commit()` for version increment |

---

## Types Reference

### IntentType (Enum)

```python
class IntentType(str, Enum):
    REFINE = "refine"                   # Modify existing parameters
    CREATE = "create"                   # Create new design/component
    QUERY = "query"                     # Ask about state
    LOCK = "lock"                       # Lock parameters
    RUN_PIPELINE = "run_pipeline"       # Execute phases
    EXPORT = "export"                   # Generate outputs
    CLARIFY = "clarify"                 # Request clarification
    UNKNOWN = "unknown"                 # Unrecognized intent
```

### ActionType (Enum)

```python
class ActionType(str, Enum):
    SET = "set"                         # Set absolute value
    INCREASE = "increase"               # Add delta to current
    DECREASE = "decrease"               # Subtract delta from current
    LOCK = "lock"                       # Lock parameter
    UNLOCK = "unlock"                   # Unlock parameter
    RUN_PHASES = "run_phases"           # Execute phase list
    EXPORT = "export"                   # Generate output
    REQUEST_CLARIFICATION = "request_clarification"
    NOOP = "noop"                       # No operation
```

### Intent (Dataclass, frozen)

```python
@dataclass(frozen=True)
class Intent:
    intent_id: str              # Unique identifier
    design_id: str              # Target design
    raw_text: str               # Original user input
    intent_type: IntentType     # Classified type
    confidence: float           # Classification confidence (0-1)
    parsed_at: datetime         # When parsed
```

### Action (Dataclass, frozen)

```python
@dataclass(frozen=True)
class Action:
    action_type: ActionType
    path: Optional[str] = None          # State path (e.g., "hull.loa")
    value: Optional[Any] = None         # For SET
    amount: Optional[float] = None      # For INCREASE/DECREASE
    unit: Optional[str] = None          # Unit (converted to kernel_unit)
    phases: Optional[List[str]] = None  # For RUN_PHASES
    format: Optional[str] = None        # For EXPORT
    message: Optional[str] = None       # For REQUEST_CLARIFICATION

    def with_value(self, new_value: Any) -> "Action":
        """Return copy with new value (immutable pattern)."""
```

### ActionPlan (Dataclass, frozen)

```python
@dataclass(frozen=True)
class ActionPlan:
    plan_id: str                        # Unique identifier
    intent_id: str                      # Source intent
    design_id: str                      # Target design
    actions: List[Action]               # Proposed actions (ordered)
    design_version_before: int          # Expected state version
    proposed_at: datetime               # When proposed
```

### ValidationResult (Dataclass)

```python
@dataclass
class ValidationResult:
    approved: List[Action]              # Actions that passed (may be clamped)
    rejected: List[Tuple[Action, str]]  # (action, reason) pairs
    warnings: List[str]                 # Clamping warnings

    @property
    def has_rejections(self) -> bool: ...

    @property
    def all_approved(self) -> bool: ...
```

---

## REFINABLE_SCHEMA

The `REFINABLE_SCHEMA` is the **whitelist** of state paths that can be modified via Actions.

### Structure

```python
REFINABLE_SCHEMA: Dict[str, RefinableField] = {
    "hull.loa": RefinableField(
        path="hull.loa",
        type="float",               # "float", "int", or "bool"
        kernel_unit="m",            # Canonical unit stored in state
        allowed_units=("m", "ft"),  # Units LLM may use
        min_value=5.0,              # Lower bound (clamps, doesn't reject)
        max_value=500.0,            # Upper bound
        keywords=("length", "loa", "overall length"),  # For keyword search
        description="Length overall",
    ),
    # ... 20+ more fields
}
```

### Current Refinable Paths

| Category | Paths |
|----------|-------|
| Hull Dimensions | `hull.loa`, `hull.lwl`, `hull.beam`, `hull.draft`, `hull.depth` |
| Hull Form | `hull.cb`, `hull.cp`, `hull.cm`, `hull.deadrise_deg` |
| Propulsion | `propulsion.total_installed_power_kw`, `propulsion.num_engines`, `propulsion.num_propellers`, `propulsion.propeller_diameter_m` |
| Mission | `mission.max_speed_kts`, `mission.cruise_speed_kts`, `mission.range_nm`, `mission.crew_berthed`, `mission.passengers` |
| Stability | `mission.gm_required_m` |

### Helper Functions

```python
from magnet.core.refinable_schema import (
    is_refinable,           # Check if path is in whitelist
    get_field,              # Get RefinableField by path
    get_all_refinable_paths, # List all paths
    find_by_keyword,        # Search by keyword
)
```

---

## UnitConverter

Deterministic unit conversion with 44+ conversion pairs.

### Usage

```python
from magnet.core.unit_converter import UnitConverter, clamp_to_bounds

# Convert 2 MW to kW
kw = UnitConverter.normalize(2, "MW", "kW")  # Returns 2000.0

# Check if conversion exists
UnitConverter.can_convert("ft", "m")  # True

# Get all supported units
units = UnitConverter.get_supported_units()

# Clamp to bounds
clamped, was_clamped = clamp_to_bounds(150, 0, 100)  # (100, True)
```

### Supported Conversions

| From | To | Factor |
|------|-----|--------|
| MW | kW | 1000 |
| hp | kW | 0.7457 |
| ft | m | 0.3048 |
| nm | km | 1.852 |
| kts | m/s | 0.514444 |
| mt | kg | 1000 |
| deg | rad | 0.017453... |
| ... | ... | ... |

---

## ActionPlanValidator

The **firewall**. Validates every action before execution.

### Validation Steps

For each action:

1. **Check path is refinable** — Must be in REFINABLE_SCHEMA
2. **Check for locks** — Parameter must not be locked (existing or pending in same plan)
3. **Convert unit** — Normalize to kernel_unit if different
4. **Coerce type** — int, float, or bool
5. **Clamp to bounds** — Warn but allow (don't reject)

### Stale Plan Detection

```python
if plan.design_version_before != state_manager.design_version:
    raise StalePlanError(
        f"Plan is stale: expected {plan.design_version_before}, "
        f"current={state_manager.design_version}"
    )
```

**Why this matters**: If another process modified state after the LLM created its plan, the plan is based on outdated information. The LLM must re-fetch state and resubmit.

### Lock-Then-Set Detection

Within a single plan, if an action LOCKs a path, subsequent actions in the **same plan** cannot modify it:

```python
# This plan will have action[1] rejected:
actions = [
    Action(ActionType.LOCK, path="hull.loa"),        # Approved
    Action(ActionType.SET, path="hull.loa", value=100),  # REJECTED
]
```

### Usage

```python
from magnet.kernel.action_validator import ActionPlanValidator, StalePlanError

validator = ActionPlanValidator()

try:
    result = validator.validate(plan, state_manager)
except StalePlanError as e:
    # Plan is stale — re-fetch state and resubmit
    ...

if result.all_approved:
    # Execute approved actions
    for action in result.approved:
        executor.execute(action)
else:
    # Handle rejections
    for action, reason in result.rejected:
        log.warning(f"Rejected: {action.path} - {reason}")
```

---

## design_version

A **monotonically increasing integer** that tracks state mutations.

### Location

```python
# In DesignState
@dataclass
class DesignState:
    design_version: int = 0  # Increments on commit()
    # ... other fields
```

### Increment Logic

```python
# In StateManager.commit()
def commit(self) -> int:
    """Canonical commit path."""
    # ... commit transaction
    self._state.design_version += 1
    return self._state.design_version
```

### Why It Matters

1. **Stale Plan Detection** — Plan's `design_version_before` must match current
2. **Optimistic Concurrency** — Multiple agents can propose; validator serializes
3. **Audit Trail** — Every mutation is numbered

---

## Parameter Locks

Ephemeral locks that prevent modification during refinement.

### API

```python
# In StateManager
state_manager.lock_parameter("hull.loa")        # Lock
state_manager.unlock_parameter("hull.loa")      # Unlock
state_manager.is_locked("hull.loa")             # Check
state_manager.get_locked_parameters()           # Get all
```

### Stored In

```python
# In DesignState
@dataclass
class DesignState:
    locked_parameters: Set[str] = field(default_factory=set)
```

### Serialization

```python
# Serialized as list (JSON doesn't support sets)
{
    "locked_parameters": ["hull.loa", "hull.beam"]
}
```

---

## For Future Agents

### When Implementing LLM Integration

1. **Always include `design_version_before`** in ActionPlan
2. **Handle `StalePlanError`** by re-fetching state and retrying
3. **Use `is_refinable()`** to check paths before proposing
4. **Use `find_by_keyword()`** to map natural language to paths

### When Adding New Refinable Fields

1. Add to `REFINABLE_SCHEMA` in `refinable_schema.py`
2. Include `kernel_unit` and `allowed_units`
3. Set appropriate `min_value` / `max_value`
4. Add `keywords` for natural language matching
5. Add unit conversions to `unit_converter.py` if needed

### When Extending Validation

1. Add new `ActionType` to `intent_protocol.py`
2. Add handler in `ActionPlanValidator._validate_action()`
3. Add tests in `tests/unit/test_action_validator.py`

---

## Test Coverage

| Module | Tests | Location |
|--------|-------|----------|
| intent_protocol.py | 24 | tests/unit/test_intent_protocol.py |
| action_validator.py | 25 | tests/unit/test_action_validator.py |
| refinable_schema.py | 21 | tests/unit/test_refinable_schema.py |
| unit_converter.py | 22 | tests/unit/test_unit_converter.py |
| design_version + locks | 17 | tests/unit/test_state_manager.py |

**Total: 163+ tests** for Intent→Action Protocol.

---

## REST API Endpoint

### POST /api/v1/designs/{design_id}/actions

Submit an ActionPlan for validation and execution.

**Request Body:**

```json
{
    "plan_id": "plan_001",
    "intent_id": "intent_001",
    "design_version_before": 5,
    "actions": [
        {
            "action_type": "set",
            "path": "hull.loa",
            "value": 100,
            "unit": "m"
        },
        {
            "action_type": "set",
            "path": "propulsion.total_installed_power_kw",
            "value": 2,
            "unit": "MW"
        }
    ]
}
```

**Success Response (200):**

```json
{
    "success": true,
    "plan_id": "plan_001",
    "actions_executed": 2,
    "design_version_before": 5,
    "design_version_after": 6,
    "warnings": ["propulsion.total_installed_power_kw converted from MW to kW"],
    "errors": []
}
```

**Stale Plan Response (409):**

```json
{
    "error": "stale_plan",
    "message": "Plan is stale: expected design_version=5, current=7",
    "current_design_version": 7
}
```

**Rejection Response (200 with success=false):**

```json
{
    "success": false,
    "plan_id": "plan_001",
    "design_version": 5,
    "approved_count": 1,
    "rejected_count": 1,
    "rejections": [
        {"path": "invalid.path", "reason": "Path not refinable: invalid.path"}
    ],
    "warnings": []
}
```

---

## Quick Reference

### Import All Types

```python
# Intent Protocol Types
from magnet.kernel.intent_protocol import (
    Intent, IntentType,
    Action, ActionType,
    ActionPlan, ActionResult,
)

# Validation
from magnet.kernel.action_validator import (
    ActionPlanValidator,
    ValidationResult,
    StalePlanError,
)

# Execution
from magnet.kernel.action_executor import (
    ActionExecutor,
    ExecutionResult,
)

# Events
from magnet.kernel.event_dispatcher import EventDispatcher
from magnet.kernel.events import (
    KernelEventType,
    KernelEvent,
    ActionExecutedEvent,
    StateMutatedEvent,
    PhaseCompletedEvent,
    # ... 20+ event types
)

# Schema & Units
from magnet.core.refinable_schema import (
    REFINABLE_SCHEMA,
    RefinableField,
    is_refinable,
    get_field,
    find_by_keyword,
)
from magnet.core.unit_converter import (
    UnitConverter,
    UnitConversionError,
    clamp_to_bounds,
)
```

---

## Module Summary

| Module | Location | LOC | Tests |
|--------|----------|-----|-------|
| intent_protocol.py | kernel/ | ~220 | 24 |
| action_validator.py | kernel/ | ~320 | 25 |
| action_executor.py | kernel/ | ~270 | 23 |
| event_dispatcher.py | kernel/ | ~200 | 25 |
| events.py | kernel/ | ~350 | 23 |
| refinable_schema.py | core/ | ~230 | 21 |
| unit_converter.py | core/ | ~175 | 22 |

---

## Migration Notes

### Phase 8: set_phase_status() Deprecation

The `set_phase_status()` function in `magnet/ui/utils.py` is **deprecated** as of v1.5.

**Old approach:**
```python
from magnet.ui.utils import set_phase_status
set_phase_status(state_manager, "hull", "completed", "my_source")  # DEPRECATED
```

**New approach:**
```python
from magnet.core.phase_states import PhaseMachine
from magnet.core.enums import PhaseState

phase_machine = PhaseMachine(state_manager)
phase_machine.transition("hull", PhaseState.COMPLETED, "my_source", "Reason for transition")
```

The deprecated function now:
1. Emits a `DeprecationWarning`
2. Attempts to use `PhaseMachine.transition()` internally
3. Falls back to legacy behavior for dict-based state

**Will be removed in v2.0.**

### Phase 9: Removed Hacks

The following patterns have been removed:

```python
# REMOVED from chat.py and runpod_handler.py:
conductor._session.completed_phases.append("mission")  # BAD - bypassed FSM

# REPLACED WITH:
phase_machine.transition("mission", PhaseState.COMPLETED, source, reason)  # GOOD - proper FSM
```

The `_run_design_pipeline()` method in `chat.py` now delegates to `conductor.run_default_pipeline()` instead of manually iterating phases.

---

**The kernel owns truth. The LLM proposes. The validator decides.**
