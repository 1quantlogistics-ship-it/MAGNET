# MAGNET V1 Complete Integration Plan v2.0

## Senior Critique Response

This plan addresses all 7 holes identified in the senior review of the original integration plan.

---

## Critical Issues Summary

| # | Issue | Risk | Solution |
|---|-------|------|----------|
| 1 | Phase name mismatch | Validators never run ("hull_form" vs "hull") | Canonical PhaseId enum |
| 2 | Not design-scoped | Multi-design contamination in concurrent API calls | Design-scoped executor/conductor |
| 3 | Warn instead of fail | Missing required implementations silently proceed | Hard fail with RuntimeError |
| 4 | Instances not verified | Required class registered ≠ instance created | Assert instances exist |
| 5 | Contracts check outputs only | Phase can complete with missing inputs | Input contracts + output contracts |
| 6 | Missing impl semantics unclear | ERROR state behavior poorly documented | Explicit NOT_IMPLEMENTED state |
| 7 | Provenance discipline | .write() → .set() loses source context | Consistent source strings |

---

## PHASE 1: Phase ID Canonicalization (Hole #1)

### Problem
- `builtin.py` uses `phase="hull_form"` for 3 validators (lines 38, 71, 165)
- `registry.py` defines `"hull"` phase in PhaseDefinition (line 61)
- `contracts.py` uses `"hull"` in PHASE_CONTRACTS
- Result: `get_validators_for_phase("hull")` returns empty list

### Secondary Mismatches
- `contracts.py:68` expects `"hull.bmt"` but validators produce `"hull.bm_m"`
- `contracts.py:78` expects `"stability.gm_transverse_m"` but validators produce `"stability.gm_m"`

### Solution

**File: `magnet/validators/phase_ids.py` (NEW)**

```python
"""
Canonical Phase IDs - Single source of truth for phase names.

ALL phase references MUST use these constants.
"""
from enum import Enum

class PhaseId(str, Enum):
    """Canonical phase identifiers."""
    MISSION = "mission"
    HULL = "hull"  # NOT "hull_form"
    STRUCTURE = "structure"
    PROPULSION = "propulsion"
    WEIGHT = "weight"
    STABILITY = "stability"
    LOADING = "loading"
    ARRANGEMENT = "arrangement"
    COMPLIANCE = "compliance"
    PRODUCTION = "production"
    COST = "cost"
    OPTIMIZATION = "optimization"
    REPORTING = "reporting"

    def __str__(self) -> str:
        return self.value
```

**File: `magnet/validators/builtin.py` (EDIT)**

Change all instances of `phase="hull_form"` to `phase="hull"`:
- Line 38: `phase="hull_form"` → `phase="hull"`
- Line 71: `phase="hull_form"` → `phase="hull"`
- Line 165: `phase="hull_form"` → `phase="hull"`

**File: `magnet/validators/contracts.py` (EDIT)**

Fix parameter names to match v1.2:
- Line 68: `"hull.bmt"` → `"hull.bm_m"`
- Line 78: `"stability.gm_transverse_m"` → `"stability.gm_m"`

---

## PHASE 2: Design-Scoped Execution (Hole #2)

### Problem

**PipelineExecutor (executor.py)**:
- `_cache: ValidationCache` (line 248) - SINGLETON across all instances
- `_last_validation_times` (line 253) - never reset
- Results from Design A leak to Design B

**Conductor (conductor.py)**:
- `_session` (line 57) - single session, overwritten by concurrent requests
- Request 1 creates session for Design-A, Request 2 overwrites with Design-B

### Solution

**File: `magnet/validators/executor.py` (EDIT)**

Add design_id scoping to cache:

```python
class PipelineExecutor:
    def __init__(
        self,
        topology: 'ValidatorTopology',
        state_manager: 'StateManager',
        validator_registry: Dict[str, 'ValidatorInterface'],
        design_id: str = None,  # NEW: Required for multi-design
    ):
        self._topology = topology
        self._state_manager = state_manager
        self._registry = validator_registry
        self._design_id = design_id  # NEW

        # Per-design cache (keyed by design_id + validator_id)
        self._cache = ValidationCache()  # Each instance gets own cache
        self._last_validation_times: Dict[str, datetime] = {}

    def _get_cache_key(self, validator_id: str) -> str:
        """Create design-scoped cache key."""
        if self._design_id:
            return f"{self._design_id}:{validator_id}"
        return validator_id
```

**File: `magnet/kernel/conductor.py` (EDIT)**

Change session storage to design-keyed dict:

```python
class Conductor:
    def __init__(self, ...):
        ...
        self._sessions: Dict[str, SessionState] = {}  # design_id → session

    def create_session(self, design_id: str) -> SessionState:
        """Create design-scoped session."""
        session = SessionState(...)
        self._sessions[design_id] = session  # Store by design_id
        return session

    def get_session(self, design_id: str) -> Optional[SessionState]:
        """Get session for specific design."""
        return self._sessions.get(design_id)
```

---

## PHASE 3: Hard Fail for Missing Implementations (Holes #3, #4)

### Problem
- `validate_required_implementations()` checks `_validator_classes` not `_instances`
- A class can be registered but fail to instantiate (import error, constructor crash)
- Required validators marked but instances may not exist

### Solution

**File: `magnet/validators/registry.py` (EDIT)**

Add instance verification:

```python
@classmethod
def validate_required_implementations(cls) -> None:
    """
    Verify all required validators have BOTH implementations AND instances.
    """
    # First: Check class registrations
    missing_classes = []
    for validator_id in cls._required_validators:
        if validator_id not in cls._validator_classes:
            missing_classes.append(validator_id)

    if missing_classes:
        raise RuntimeError(
            f"Required validators missing class implementations: {missing_classes}"
        )

    # Second: Check instances (class registered but instantiation failed)
    missing_instances = []
    for validator_id in cls._required_validators:
        if validator_id not in cls._instances:
            missing_instances.append(validator_id)

    if missing_instances:
        raise RuntimeError(
            f"Required validators failed to instantiate: {missing_instances}"
        )
```

**File: `magnet/bootstrap/app.py` (EDIT)**

Reorder to instantiate before validate:

```python
# Step 1: Reset registry
ValidatorRegistry.reset()

# Step 2: Register validator classes
ValidatorRegistry.initialize_defaults()

# Step 3: Instantiate ALL validators BEFORE validation
instance_count = ValidatorRegistry.instantiate_all()

# Step 4: NOW verify required validators have working instances
ValidatorRegistry.validate_required_implementations()  # Raises RuntimeError if missing
```

---

## PHASE 4: Input + Output Contracts (Hole #5)

### Problem
- Contracts only check outputs (`hull.displacement_m3`, etc.)
- Phase can "succeed" if inputs missing (no hull.lwl → hydrostatics returns default)
- Should require inputs present BEFORE phase runs

### Solution

**File: `magnet/validators/contracts.py` (EDIT)**

Add input contracts:

```python
@dataclass
class PhaseContract:
    """Defines required inputs AND outputs for a phase."""
    phase_name: str
    required_inputs: List[str]   # State paths that MUST exist BEFORE phase
    required_outputs: List[str]  # State paths that MUST exist AFTER phase
    optional_outputs: List[str] = field(default_factory=list)

    def check_inputs(self, state_manager: 'StateManager') -> 'ContractResult':
        """Check if required inputs are present BEFORE phase execution."""
        missing = []
        for path in self.required_inputs:
            value = state_manager.get(path)
            if value is None:
                missing.append(path)

        return ContractResult(
            phase_name=self.phase_name,
            satisfied=len(missing) == 0,
            missing_outputs=missing,
            message=f"Phase {self.phase_name} missing required INPUTS: {missing}" if missing else None
        )


PHASE_CONTRACTS: Dict[str, PhaseContract] = {
    "hull": PhaseContract(
        phase_name="hull",
        required_inputs=[
            "hull.lwl",       # Length at waterline
            "hull.beam",      # Beam
            "hull.draft",     # Draft
            "hull.cb",        # Block coefficient
        ],
        required_outputs=[
            "hull.displacement_m3",
            "hull.vcb_m",
            "hull.bm_m",
        ],
    ),
    # ... other phases
}
```

**File: `magnet/kernel/conductor.py` (EDIT)**

Check inputs BEFORE running phase:

```python
def run_phase(self, phase_name: str, design_id: str, context: Dict = None) -> PhaseResult:
    # CHECK INPUTS BEFORE EXECUTION
    from ..validators.contracts import check_phase_inputs, check_phase_outputs

    input_check = check_phase_inputs(phase_name, self.state)
    if not input_check.satisfied:
        return PhaseResult(
            phase_name=phase_name,
            status=PhaseStatus.BLOCKED,
            errors=[f"Missing required inputs: {input_check.missing_outputs}"],
        )

    # Execute phase...

    # CHECK OUTPUTS AFTER EXECUTION
    output_check = check_phase_outputs(phase_name, self.state)
    if not output_check.satisfied:
        result.status = PhaseStatus.FAILED
        result.errors.append(f"Missing required outputs: {output_check.missing_outputs}")
```

---

## PHASE 5: Missing Implementation State (Hole #6)

### Problem
- Validators without implementations return `ValidatorState.ERROR`
- ERROR implies code failure (transient), but missing impl is permanent
- Aggregator treats ERROR as blocking but semantics unclear

### Solution

**File: `magnet/validators/taxonomy.py` (EDIT)**

Add explicit state for missing implementations:

```python
class ValidatorState(str, Enum):
    """Validator execution states."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    ERROR = "error"           # Transient code error (retry possible)
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    NOT_IMPLEMENTED = "not_implemented"  # NEW: Permanent, no implementation exists
```

**File: `magnet/validators/executor.py` (EDIT)**

Use new state for missing implementations:

```python
def _execute_validator(self, validator_id: str, context: Dict = None) -> ValidationResult:
    impl = self._registry.get(validator_id)

    if not impl:
        return ValidationResult(
            validator_id=validator_id,
            state=ValidatorState.NOT_IMPLEMENTED,  # Changed from ERROR
            error_message=f"No implementation for: {validator_id}",
            execution_time_ms=0,
        )
```

---

## PHASE 6: StateManager Source Discipline (Hole #7)

### Problem
- ~65 calls to `state_manager.write()` (doesn't exist)
- Should be `state_manager.set(path, value, source)`
- Source string critical for provenance/audit/debugging

### Source String Convention

```python
# Pattern: "{module}/{function}" or "{validator_id}"
state_manager.set("hull.displacement_m3", 1500.0, "physics/hydrostatics")
state_manager.set("stability.gm_m", 2.1, "stability/intact_gm")
state_manager.set("session.phase", "hull", "conductor/run_phase")
```

### Files to Fix (Priority Order)

**P0 - CRITICAL (Core Functionality)**

| File | Calls | Pattern |
|------|-------|---------|
| `magnet/kernel/conductor.py` | 5 | `.write()` → `.set()` |
| `magnet/production/validators.py` | 4 | `.write()` → `.set()` |
| `magnet/arrangement/validators.py` | 6 | `.write()` → `.set()` |
| `magnet/loading/validators.py` | 5 | `.write()` → `.set()` |

**P1 - HIGH (Secondary Features)**

| File | Calls | Pattern |
|------|-------|---------|
| `magnet/kernel/session.py` | 4 | `.write()` → `.set()` |
| `magnet/kernel/validator.py` | 2 | `.write()` → `.set()` |
| `magnet/reporting/validator.py` | 4 | `.write()` → `.set()` |
| `magnet/webgl/annotations.py` | 2 | 2-arg `.set()` → 3-arg |

**P2 - MEDIUM (Systems)**

| File | Calls | Pattern |
|------|-------|---------|
| `magnet/systems/electrical/validator.py` | 8 | `.write()` → `.set()` |
| `magnet/systems/propulsion/validator.py` | 10+ | `.write()` → `.set()` |
| `magnet/optimization/validator.py` | 8 | `.write()` → `.set()` |
| `magnet/optimization/sensitivity.py` | 1 | `.write()` → `.set()` |

**P3 - LOW (Edge Cases)**

| File | Calls | Pattern |
|------|-------|---------|
| `magnet/optimization/optimizer.py` | 1 | `.write()` → `.set()` |
| `magnet/transactions/manager.py` | 2 | `.write()` → `.set()` |
| `magnet/glue/utils.py` | 1 | `.write()` → `.set()` |
| `magnet/errors/recovery.py` | 1 | `.write()` → `.set()` |
| `magnet/protocol/cycle_executor.py` | 1 | `.write()` → `.set()` |

### Fix Pattern

```python
# BROKEN (4 args to non-existent method):
state_manager.write("hull.displacement_m3", 1500.0, agent, "calculated displacement")

# FIXED (3 args to correct method with proper source):
state_manager.set("hull.displacement_m3", 1500.0, "physics/hydrostatics")
```

---

## Implementation Order

### Step 1: Phase ID Canonicalization (Hole #1)
1. Create `magnet/validators/phase_ids.py` with PhaseId enum
2. Update `builtin.py` lines 38, 71, 165: `phase="hull_form"` → `phase="hull"`
3. Fix parameter name mismatches in contracts.py

### Step 2: Hard Fail + Instance Verification (Holes #3, #4)
1. Update `registry.py` `validate_required_implementations()` to check instances
2. Update bootstrap order: register → instantiate → validate

### Step 3: Missing Implementation State (Hole #6)
1. Add `ValidatorState.NOT_IMPLEMENTED` to taxonomy.py
2. Update executor.py to use new state
3. Update aggregator.py to handle new state

### Step 4: Input Contracts (Hole #5)
1. Refactor `PhaseOutputContract` → `PhaseContract` with inputs
2. Add `check_phase_inputs()` function
3. Update conductor.py to check inputs before execution

### Step 5: Design-Scoped Execution (Hole #2)
1. Add `design_id` parameter to PipelineExecutor
2. Scope cache keys by design_id
3. Change Conductor `_session` to `_sessions: Dict[str, SessionState]`
4. Update API endpoints to pass design_id

### Step 6: StateManager Fixes (Hole #7)
1. Fix P0 files (conductor, production, arrangement, loading)
2. Fix P1 files (session, validator, reporting, webgl)
3. Fix P2 files (systems validators, optimization)
4. Fix P3 files (edge cases)

---

## Success Criteria

| # | Criterion | Test |
|---|-----------|------|
| 1 | Phase IDs match | `get_validators_for_phase("hull")` returns hydrostatics validator |
| 2 | Design isolation | Concurrent designs don't share cache/session |
| 3 | Hard fail works | Missing required impl raises RuntimeError |
| 4 | Instances verified | `validate_required_implementations()` checks `_instances` |
| 5 | Input contracts work | Phase blocked if inputs missing |
| 6 | NOT_IMPLEMENTED state | Missing impl returns NOT_IMPLEMENTED, not ERROR |
| 7 | No .write() calls | `grep -r "\.write("` returns 0 matches |

---

## Files to Modify

### Phase 1 (Hole #1)
- `magnet/validators/phase_ids.py` (NEW)
- `magnet/validators/builtin.py` (lines 38, 71, 165)
- `magnet/validators/contracts.py` (lines 68, 78)

### Phase 2 (Holes #3, #4)
- `magnet/validators/registry.py` (lines 89-105)
- `magnet/bootstrap/app.py` (validator wiring section)

### Phase 3 (Hole #6)
- `magnet/validators/taxonomy.py` (ValidatorState enum)
- `magnet/validators/executor.py` (_execute_validator)
- `magnet/validators/aggregator.py` (check_gate)

### Phase 4 (Hole #5)
- `magnet/validators/contracts.py` (PhaseContract class)
- `magnet/kernel/conductor.py` (run_phase)

### Phase 5 (Hole #2)
- `magnet/validators/executor.py` (design_id param)
- `magnet/kernel/conductor.py` (_sessions dict)
- `magnet/bootstrap/app.py` (factory updates)
- `magnet/deployment/api.py` (endpoint updates)

### Phase 6 (Hole #7)
- 16 files with .write() → .set() fixes (see detailed list above)

---

## Architecture After Fixes

```
API Request (design_id=X)
    │
    ├─► get_conductor()
    │       └─► _sessions["X"] (design-scoped)
    │
    ├─► create_pipeline_executor(design_id="X")
    │       └─► _cache scoped to "X:*" keys
    │
    ├─► check_phase_inputs()     ← Hole #5: Pre-execution check
    │       └─► BLOCK if inputs missing
    │
    ├─► execute_phase()
    │       ├─► validators use PhaseId.HULL    ← Hole #1: Canonical names
    │       ├─► missing impl → NOT_IMPLEMENTED ← Hole #6: Explicit state
    │       └─► state_manager.set(..., source) ← Hole #7: Provenance
    │
    ├─► check_phase_outputs()    ← Existing Guardrail #1
    │
    └─► ValidatorRegistry.validate_required_implementations()
            ├─► checks _validator_classes    ← Hole #3: Hard fail
            └─► checks _instances            ← Hole #4: Instance verify
```
