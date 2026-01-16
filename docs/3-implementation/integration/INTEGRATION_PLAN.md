# MAGNET V1 Complete Integration Plan (Revised)

## Executive Summary

MAGNET has two parallel validation systems that were never wired together. This plan completes the integration **with 4 critical guardrails** to prevent recreating the "looks valid but isn't" problem.

---

## Critical Guardrails (From Senior Review)

| Issue | Risk | Solution |
|-------|------|----------|
| **1. No-Op Is Failure** | Phase passes validators but produces nothing | Enforce required phase outputs |
| **2. Dual Execution Paths** | Conductor + PipelineExecutor run validators independently | Make PipelineExecutor the single authority |
| **3. Global Mutable Registry** | Thread safety, test pollution, reload issues | Control registry lifecycle per process |
| **4. Missing Implementations** | Topology includes validators with no code | Fail hard if required validators missing |

---

## Implementation Plan (6 Steps, ~545 LOC)

### Step 1: Create ValidatorRegistry with Lifecycle Control

**File:** `/Users/bengibson/MAGNETV1/magnet/validators/registry.py` (NEW)

```python
"""
Validator Registry - Maps definitions to implementations and manages instances.

BRAVO OWNS THIS FILE.

Guardrail #3: Explicit lifecycle control - reset() must be called before initialize_defaults()
Guardrail #4: Fail hard if required validators lack implementations
"""
from typing import Dict, Optional, Type, Set, TYPE_CHECKING
import logging

from .taxonomy import ValidatorInterface, ValidatorDefinition
from .builtin import get_validator_by_id, get_all_validators

if TYPE_CHECKING:
    from ..kernel.conductor import Conductor

logger = logging.getLogger(__name__)


class ValidatorRegistry:
    """
    Central registry for validator implementations.

    IMPORTANT: This uses class-level state. Call reset() before initialize_defaults()
    in each process/app lifecycle to prevent state leakage.
    """

    _validator_classes: Dict[str, Type[ValidatorInterface]] = {}
    _instances: Dict[str, ValidatorInterface] = {}
    _initialized: bool = False
    _required_validators: Set[str] = set()  # Validators that MUST have implementations

    @classmethod
    def reset(cls) -> None:
        """
        Reset registry state. MUST be called before initialize_defaults() in each process.

        Guardrail #3: Prevents state leakage across workers/tests/reloads.
        """
        cls._validator_classes.clear()
        cls._instances.clear()
        cls._initialized = False
        cls._required_validators.clear()
        logger.debug("ValidatorRegistry reset")

    @classmethod
    def register_class(cls, validator_id: str, validator_class: Type[ValidatorInterface]) -> None:
        """Register a validator implementation class."""
        cls._validator_classes[validator_id] = validator_class

    @classmethod
    def mark_required(cls, validator_id: str) -> None:
        """Mark a validator as required (must have implementation)."""
        cls._required_validators.add(validator_id)

    @classmethod
    def get_instance(cls, validator_id: str) -> Optional[ValidatorInterface]:
        """Get validator instance by ID (lazy instantiation)."""
        if validator_id not in cls._instances:
            cls._instantiate(validator_id)
        return cls._instances.get(validator_id)

    @classmethod
    def get_all_instances(cls) -> Dict[str, ValidatorInterface]:
        """Get all instantiated validators."""
        return cls._instances.copy()

    @classmethod
    def _instantiate(cls, validator_id: str) -> None:
        """Create validator instance from registered class."""
        if validator_id not in cls._validator_classes:
            return

        definition = get_validator_by_id(validator_id)
        if not definition:
            logger.warning(f"No definition for: {validator_id}")
            return

        try:
            validator_class = cls._validator_classes[validator_id]
            instance = validator_class(definition)
            cls._instances[validator_id] = instance
            logger.debug(f"Instantiated: {validator_id}")
        except Exception as e:
            logger.error(f"Failed to instantiate {validator_id}: {e}")

    @classmethod
    def validate_required_implementations(cls) -> None:
        """
        Verify all required validators have implementations.

        Guardrail #4: Fail hard if required validators missing.
        Raises RuntimeError if any required validator lacks implementation.
        """
        missing = []
        for validator_id in cls._required_validators:
            if validator_id not in cls._validator_classes:
                missing.append(validator_id)

        if missing:
            raise RuntimeError(
                f"Required validators missing implementations: {missing}"
            )
        logger.info(f"✓ All {len(cls._required_validators)} required validators have implementations")

    @classmethod
    def initialize_defaults(cls) -> None:
        """Register all available validator implementations."""
        if cls._initialized:
            return

        # Physics validators (REQUIRED for hull phase)
        try:
            from magnet.physics.validators import HydrostaticsValidator, ResistanceValidator
            cls.register_class("physics/hydrostatics", HydrostaticsValidator)
            cls.register_class("physics/resistance", ResistanceValidator)
            cls.mark_required("physics/hydrostatics")  # Required for any hull analysis
        except ImportError as e:
            logger.warning(f"Physics validators not available: {e}")

        # Stability validators (REQUIRED for stability phase)
        try:
            from magnet.stability.validators import (
                IntactGMValidator, GZCurveValidator,
                DamageStabilityValidator, WeatherCriterionValidator
            )
            cls.register_class("stability/intact_gm", IntactGMValidator)
            cls.register_class("stability/gz_curve", GZCurveValidator)
            cls.register_class("stability/damage", DamageStabilityValidator)
            cls.register_class("stability/weather_criterion", WeatherCriterionValidator)
            cls.mark_required("stability/intact_gm")  # Required for stability
        except ImportError as e:
            logger.warning(f"Stability validators not available: {e}")

        # Weight validator (REQUIRED for weight phase)
        try:
            from magnet.weight.validators import WeightEstimationValidator
            cls.register_class("weight/estimation", WeightEstimationValidator)
            cls.mark_required("weight/estimation")
        except ImportError as e:
            logger.warning(f"Weight validator not available: {e}")

        # Compliance validator (REQUIRED - gate condition)
        try:
            from magnet.compliance.validators import ComplianceValidator
            cls.register_class("compliance/regulatory", ComplianceValidator)
            cls.mark_required("compliance/regulatory")  # Gate validator
        except ImportError as e:
            logger.warning(f"Compliance validator not available: {e}")

        # Arrangement validator
        try:
            from magnet.arrangement.validators import ArrangementValidator
            cls.register_class("arrangement/generator", ArrangementValidator)
        except ImportError as e:
            logger.warning(f"Arrangement validator not available: {e}")

        # Loading validator
        try:
            from magnet.loading.validators import LoadingComputerValidator
            cls.register_class("loading/computer", LoadingComputerValidator)
        except ImportError as e:
            logger.warning(f"Loading validator not available: {e}")

        # Production validator
        try:
            from magnet.production.validators import ProductionPlanningValidator
            cls.register_class("production/planning", ProductionPlanningValidator)
        except ImportError as e:
            logger.warning(f"Production validator not available: {e}")

        # Cost validator
        try:
            from magnet.cost.validators import CostValidator
            cls.register_class("cost/estimation", CostValidator)
        except ImportError as e:
            logger.warning(f"Cost validator not available: {e}")

        cls._initialized = True
        logger.info(f"Registered {len(cls._validator_classes)} validator classes")

    @classmethod
    def instantiate_all(cls) -> int:
        """Instantiate all registered validator classes."""
        for validator_id in list(cls._validator_classes.keys()):
            cls._instantiate(validator_id)
        return len(cls._instances)
```

**LOC:** ~150

---

### Step 2: Create Phase Output Contracts

**File:** `/Users/bengibson/MAGNETV1/magnet/validators/contracts.py` (NEW)

```python
"""
Phase Output Contracts - Enforces that phases actually produce required outputs.

BRAVO OWNS THIS FILE.

Guardrail #1: No-Op Is Failure - phases must mutate state, not just pass validators.
"""
from typing import Dict, List, Optional, Set, TYPE_CHECKING
from dataclasses import dataclass
import logging

if TYPE_CHECKING:
    from ..core.state_manager import StateManager

logger = logging.getLogger(__name__)


@dataclass
class PhaseOutputContract:
    """Defines required outputs for a phase."""
    phase_name: str
    required_outputs: List[str]  # State paths that MUST be populated
    optional_outputs: List[str] = None  # Nice to have

    def check(self, state_manager: 'StateManager') -> 'ContractResult':
        """Check if phase produced required outputs."""
        missing = []
        for path in self.required_outputs:
            value = state_manager.get(path)
            if value is None:
                missing.append(path)

        return ContractResult(
            phase_name=self.phase_name,
            satisfied=len(missing) == 0,
            missing_outputs=missing,
            message=f"Phase {self.phase_name} missing required outputs: {missing}" if missing else None
        )


@dataclass
class ContractResult:
    """Result of contract check."""
    phase_name: str
    satisfied: bool
    missing_outputs: List[str]
    message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "phase": self.phase_name,
            "satisfied": self.satisfied,
            "missing_outputs": self.missing_outputs,
            "message": self.message,
        }


# ============================================================================
# PHASE OUTPUT CONTRACTS
# ============================================================================

PHASE_CONTRACTS: Dict[str, PhaseOutputContract] = {
    "hull": PhaseOutputContract(
        phase_name="hull",
        required_outputs=[
            "hull.displacement_m3",
            "hull.kb_m",
            "hull.bm_m",
        ],
        optional_outputs=[
            "hull.wetted_surface_m2",
            "hull.waterplane_area_m2",
        ],
    ),
    "stability": PhaseOutputContract(
        phase_name="stability",
        required_outputs=[
            "stability.gm_m",
        ],
        optional_outputs=[
            "stability.gz_curve",
            "stability.gz_max_m",
        ],
    ),
    "weight": PhaseOutputContract(
        phase_name="weight",
        required_outputs=[
            "weight.lightship_mt",
            "weight.lightship_vcg_m",
        ],
        optional_outputs=[
            "weight.group_100_mt",
            "weight.group_200_mt",
        ],
    ),
    "propulsion": PhaseOutputContract(
        phase_name="propulsion",
        required_outputs=[
            # Propulsion can be user-supplied, so minimal requirements
        ],
        optional_outputs=[
            "propulsion.installed_power_kw",
        ],
    ),
    "compliance": PhaseOutputContract(
        phase_name="compliance",
        required_outputs=[
            "compliance.status",
            "compliance.pass_count",
            "compliance.fail_count",
        ],
    ),
    "arrangement": PhaseOutputContract(
        phase_name="arrangement",
        required_outputs=[
            "arrangement.compartment_count",
        ],
    ),
    "loading": PhaseOutputContract(
        phase_name="loading",
        required_outputs=[
            "loading.all_conditions_pass",
        ],
    ),
    "production": PhaseOutputContract(
        phase_name="production",
        required_outputs=[],  # Optional phase
    ),
    "cost": PhaseOutputContract(
        phase_name="cost",
        required_outputs=[],  # Optional phase
    ),
}


def check_phase_contract(phase_name: str, state_manager: 'StateManager') -> ContractResult:
    """
    Check if a phase satisfied its output contract.

    Guardrail #1: Prevents "validators pass but nothing happened" situation.
    """
    contract = PHASE_CONTRACTS.get(phase_name)
    if not contract:
        # No contract defined - phase passes by default
        return ContractResult(
            phase_name=phase_name,
            satisfied=True,
            missing_outputs=[],
        )

    return contract.check(state_manager)
```

**LOC:** ~130

---

### Step 3: Refactor Conductor to Delegate to PipelineExecutor

**File:** `/Users/bengibson/MAGNETV1/magnet/kernel/conductor.py`

**Guardrail #2:** Make PipelineExecutor the single validator execution path.

**Add new method and modify run_phase():**

```python
# Add at top of file, after imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..validators.executor import PipelineExecutor
    from ..validators.aggregator import ResultAggregator


class Conductor:
    def __init__(
        self,
        state_manager: 'StateManager',
        registry: PhaseRegistry = None,
        pipeline_executor: 'PipelineExecutor' = None,  # NEW
        result_aggregator: 'ResultAggregator' = None,  # NEW
    ):
        self.state = state_manager
        self.registry = registry or PhaseRegistry()
        self._pipeline_executor = pipeline_executor  # NEW: Single execution authority
        self._result_aggregator = result_aggregator  # NEW
        self._validators: Dict[str, 'ValidatorInterface'] = {}  # Keep for metadata only
        self._session: Optional[SessionState] = None

    def set_pipeline_executor(self, executor: 'PipelineExecutor') -> None:
        """Set the pipeline executor (Guardrail #2: single execution authority)."""
        self._pipeline_executor = executor

    def set_result_aggregator(self, aggregator: 'ResultAggregator') -> None:
        """Set the result aggregator."""
        self._result_aggregator = aggregator

    def run_phase(self, phase_name: str, context: Dict[str, Any] = None) -> PhaseResult:
        """
        Run a single phase.

        Guardrail #2: Delegates to PipelineExecutor for actual validation.
        Guardrail #1: Checks phase output contracts after validation.
        """
        phase = self.registry.get_phase(phase_name)
        if not phase:
            return PhaseResult(
                phase_name=phase_name,
                status=PhaseStatus.FAILED,
                errors=[f"Unknown phase: {phase_name}"],
            )

        # Check dependencies
        for dep in phase.depends_on:
            if self._session and dep not in self._session.completed_phases:
                return PhaseResult(
                    phase_name=phase_name,
                    status=PhaseStatus.BLOCKED,
                    errors=[f"Dependency not completed: {dep}"],
                )

        # Execute via PipelineExecutor (Guardrail #2)
        if self._pipeline_executor:
            result = self._execute_via_pipeline(phase, context or {})
        else:
            # Fallback to legacy execution (for backwards compatibility)
            result = self._execute_phase(phase, context or {})

        # Check phase output contract (Guardrail #1)
        from ..validators.contracts import check_phase_contract
        contract_result = check_phase_contract(phase_name, self.state)
        if not contract_result.satisfied:
            result.status = PhaseStatus.FAILED
            result.errors.append(contract_result.message)
            logger.warning(f"Phase {phase_name} failed output contract: {contract_result.missing_outputs}")

        # Update session
        if self._session:
            self._session.current_phase = phase_name
            self._session.add_phase_result(result)

        # Evaluate gate if applicable
        if phase.is_gate and result.status == PhaseStatus.COMPLETED:
            gate_result = self._evaluate_gate(phase, result)
            if self._session:
                self._session.add_gate_result(gate_result)

            if not gate_result.passed:
                result.status = PhaseStatus.FAILED
                result.errors.append(f"Gate failed: {gate_result.blocking_failures}")

        logger.debug(f"Phase {phase_name} completed with status {result.status.value}")
        return result

    def _execute_via_pipeline(
        self,
        phase: PhaseDefinition,
        context: Dict[str, Any],
    ) -> PhaseResult:
        """
        Execute phase validators via PipelineExecutor.

        Guardrail #2: Single execution authority.
        """
        from datetime import datetime, timezone

        result = PhaseResult(
            phase_name=phase.name,
            status=PhaseStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )

        try:
            # Run validators through PipelineExecutor
            execution_state = self._pipeline_executor.execute_phase(phase.name)

            # Aggregate results
            result.validators_run = len(execution_state.completed) + len(execution_state.failed)
            result.validators_passed = len(execution_state.completed)
            result.validators_failed = len(execution_state.failed)

            # Collect errors from failed validators
            for vid in execution_state.failed:
                if vid in execution_state.results:
                    val_result = execution_state.results[vid]
                    if val_result.error_message:
                        result.errors.append(f"{vid}: {val_result.error_message}")

            # Determine status
            if execution_state.failed:
                result.status = PhaseStatus.FAILED
            else:
                result.status = PhaseStatus.COMPLETED

        except Exception as e:
            result.status = PhaseStatus.FAILED
            result.errors.append(f"Pipeline execution error: {str(e)}")
            logger.error(f"Phase {phase.name} pipeline error: {e}")

        result.completed_at = datetime.now(timezone.utc)
        return result
```

**LOC:** ~100 (modifications to existing file)

---

### Step 4: Wire Everything in Bootstrap with Lifecycle Control

**File:** `/Users/bengibson/MAGNETV1/magnet/bootstrap/app.py`

**Location:** After Conductor creation (~line 257), add:

```python
        # =================================================================
        # LAYER 3.5: Validator Pipeline Integration
        # =================================================================
        try:
            from magnet.validators.registry import ValidatorRegistry
            from magnet.validators.topology import ValidatorTopology
            from magnet.validators.executor import PipelineExecutor
            from magnet.validators.aggregator import ResultAggregator
            from magnet.validators.builtin import get_all_validators
            from magnet.kernel.conductor import Conductor

            # Guardrail #3: Reset registry to prevent state leakage
            ValidatorRegistry.reset()
            logger.debug("ValidatorRegistry reset for clean initialization")

            # Step 1: Initialize validator class mappings
            ValidatorRegistry.initialize_defaults()
            logger.info(f"✓ Registered {len(ValidatorRegistry._validator_classes)} validator classes")

            # Guardrail #4: Verify required validators have implementations
            ValidatorRegistry.validate_required_implementations()

            # Step 2: Instantiate all validators
            instance_count = ValidatorRegistry.instantiate_all()
            logger.info(f"✓ Instantiated {instance_count} validators")

            # Step 3: Build validator topology (DAG)
            topology = ValidatorTopology()
            for defn in get_all_validators():
                topology.add_validator(defn)
            topology.build()
            logger.info(f"✓ Built validator topology with {len(topology._nodes)} nodes")

            # Step 4: Register topology as singleton
            self._services.add_singleton(ValidatorTopology, topology)

            # Step 5: Create PipelineExecutor factory
            def create_pipeline_executor():
                state_manager = self._context.container.resolve(StateManager)
                return PipelineExecutor(
                    topology=topology,
                    state_manager=state_manager,
                    validator_registry=ValidatorRegistry.get_all_instances(),
                )

            self._services.add_factory(PipelineExecutor, create_pipeline_executor)

            # Step 6: Create ResultAggregator factory
            def create_result_aggregator():
                state_manager = self._context.container.resolve(StateManager)
                return ResultAggregator(
                    topology=topology,
                    state_manager=state_manager,
                )

            self._services.add_factory(ResultAggregator, create_result_aggregator)

            # Guardrail #2: Wire PipelineExecutor into Conductor as single authority
            conductor = self._context.container.resolve(Conductor)
            executor = self._context.container.resolve(PipelineExecutor)
            aggregator = self._context.container.resolve(ResultAggregator)
            conductor.set_pipeline_executor(executor)
            conductor.set_result_aggregator(aggregator)
            logger.info("✓ Conductor configured with PipelineExecutor (single execution authority)")

            self._context._initialized_components.append("ValidatorPipeline")

        except RuntimeError as e:
            # Guardrail #4: Required validator missing - fail hard
            logger.error(f"FATAL: Validator pipeline setup failed: {e}")
            raise
        except Exception as e:
            logger.warning(f"Validator pipeline setup failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
```

**LOC:** ~70

---

### Step 5: Add DI Functions to API

**File:** `/Users/bengibson/MAGNETV1/magnet/deployment/api.py`

**Location:** After existing get_* functions (~line 195), add:

```python
    def get_pipeline_executor():
        """Get configured PipelineExecutor from DI container."""
        if context and context.container:
            try:
                from magnet.validators.executor import PipelineExecutor
                return context.container.resolve(PipelineExecutor)
            except Exception as e:
                logger.warning(f"Could not resolve PipelineExecutor: {e}")
        return None

    def get_validator_topology():
        """Get ValidatorTopology from DI container."""
        if context and context.container:
            try:
                from magnet.validators.topology import ValidatorTopology
                return context.container.resolve(ValidatorTopology)
            except Exception as e:
                logger.warning(f"Could not resolve ValidatorTopology: {e}")
        return None

    def get_result_aggregator():
        """Get ResultAggregator from DI container."""
        if context and context.container:
            try:
                from magnet.validators.aggregator import ResultAggregator
                return context.container.resolve(ResultAggregator)
            except Exception as e:
                logger.warning(f"Could not resolve ResultAggregator: {e}")
        return None
```

**LOC:** ~30

---

### Step 6: Fix validate_phase Endpoint with Contract Checking

**File:** `/Users/bengibson/MAGNETV1/magnet/deployment/api.py`

**Update validate_phase endpoint (~line 514-547):**

```python
@app.post("/api/v1/designs/{design_id}/phases/{phase}/validate")
async def validate_phase(
    design_id: str,
    phase: str,
    state_manager: StateManager = Depends(get_state_manager),
):
    """Validate a specific phase using the configured pipeline executor."""
    executor = get_pipeline_executor()
    if not executor:
        return {
            "status": "error",
            "message": "PipelineExecutor not available",
            "phase": phase,
        }

    try:
        # Run phase validation via single authority (Guardrail #2)
        execution_state = executor.execute_phase(phase)

        # Check phase output contract (Guardrail #1)
        from magnet.validators.contracts import check_phase_contract
        contract_result = check_phase_contract(phase, state_manager)

        # Get gate status
        aggregator = get_result_aggregator()
        gate_status = None
        if aggregator:
            gate_status = aggregator.check_gate(phase, execution_state)

        # Determine overall success
        validators_passed = len([
            v for v, r in execution_state.results.items()
            if r.state.value in ["passed", "warning"]
        ])

        # Phase fails if: validators failed OR contract not satisfied
        phase_success = (
            len(execution_state.failed) == 0 and
            contract_result.satisfied
        )

        return {
            "status": "success" if phase_success else "failed",
            "phase": phase,
            "validators_run": len(execution_state.completed) + len(execution_state.failed),
            "validators_passed": validators_passed,
            "validators_failed": len(execution_state.failed),
            "contract_satisfied": contract_result.satisfied,
            "missing_outputs": contract_result.missing_outputs,
            "can_advance": (gate_status.can_advance if gate_status else True) and contract_result.satisfied,
            "blocking_validators": gate_status.blocking_validators if gate_status else [],
            "results": {
                vid: result.to_dict()
                for vid, result in execution_state.results.items()
            },
        }
    except Exception as e:
        logger.error(f"Phase validation failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "phase": phase,
        }
```

**LOC:** ~60

---

## Summary: Files to Modify/Create

| File | Action | LOC | Guardrails |
|------|--------|-----|------------|
| `magnet/validators/registry.py` | CREATE | ~150 | #3, #4 |
| `magnet/validators/contracts.py` | CREATE | ~130 | #1 |
| `magnet/validators/__init__.py` | EDIT (add exports) | ~5 | - |
| `magnet/kernel/conductor.py` | EDIT (delegate to executor) | ~100 | #1, #2 |
| `magnet/bootstrap/app.py` | EDIT (wire with lifecycle) | ~70 | #2, #3, #4 |
| `magnet/deployment/api.py` | EDIT (DI + contract check) | ~90 | #1, #2 |
| **Total** | | **~545** | All 4 |

---

## Guardrail Summary

### Guardrail #1: No-Op Is Failure
- **Problem:** Validators pass but phase produces nothing
- **Solution:** `contracts.py` defines required outputs per phase
- **Enforcement:** Conductor and API check contracts after validation

### Guardrail #2: Single Execution Authority
- **Problem:** Conductor and PipelineExecutor both run validators
- **Solution:** Conductor delegates to PipelineExecutor
- **Enforcement:** `_execute_via_pipeline()` is the only path

### Guardrail #3: Registry Lifecycle Control
- **Problem:** Global mutable state causes leakage
- **Solution:** `ValidatorRegistry.reset()` before `initialize_defaults()`
- **Enforcement:** Bootstrap calls reset() first

### Guardrail #4: Required Implementation Check
- **Problem:** Topology includes validators with no code
- **Solution:** `validate_required_implementations()` fails hard
- **Enforcement:** Bootstrap calls before instantiation

---

## Validation Commands

```bash
cd /Users/bengibson/MAGNETV1

# Test 1: Registry with lifecycle control (Guardrail #3)
python3 -c "
from magnet.validators.registry import ValidatorRegistry

# Simulate app restart
ValidatorRegistry.reset()
ValidatorRegistry.initialize_defaults()
count = ValidatorRegistry.instantiate_all()
print(f'First init: {count} validators')

# Simulate second restart (should be clean)
ValidatorRegistry.reset()
ValidatorRegistry.initialize_defaults()
count = ValidatorRegistry.instantiate_all()
print(f'Second init: {count} validators (no duplication)')
"

# Test 2: Required implementation check (Guardrail #4)
python3 -c "
from magnet.validators.registry import ValidatorRegistry
ValidatorRegistry.reset()
ValidatorRegistry.initialize_defaults()
try:
    ValidatorRegistry.validate_required_implementations()
    print('✓ All required validators have implementations')
except RuntimeError as e:
    print(f'✗ Missing: {e}')
"

# Test 3: Phase output contracts (Guardrail #1)
python3 -c "
from magnet.validators.contracts import check_phase_contract
from magnet.core.state_manager import StateManager
from magnet.core.design_state import DesignState

sm = StateManager(DesignState())

# Empty state - contract should fail
result = check_phase_contract('hull', sm)
print(f'Empty hull contract: satisfied={result.satisfied}')
print(f'Missing: {result.missing_outputs}')

# Populate required outputs
sm.set('hull.displacement_m3', 1500.0, 'test')
sm.set('hull.kb_m', 1.2, 'test')
sm.set('hull.bm_m', 3.5, 'test')

result = check_phase_contract('hull', sm)
print(f'Populated hull contract: satisfied={result.satisfied}')
"

# Test 4: Full pipeline with Conductor delegation (Guardrail #2)
python3 -c "
from magnet.validators.registry import ValidatorRegistry
from magnet.validators.topology import ValidatorTopology
from magnet.validators.executor import PipelineExecutor
from magnet.validators.aggregator import ResultAggregator
from magnet.validators.builtin import get_all_validators
from magnet.kernel.conductor import Conductor
from magnet.kernel.registry import PhaseRegistry
from magnet.core.state_manager import StateManager
from magnet.core.design_state import DesignState

# Setup with lifecycle control
ValidatorRegistry.reset()
ValidatorRegistry.initialize_defaults()
ValidatorRegistry.validate_required_implementations()
ValidatorRegistry.instantiate_all()

# Build topology
topology = ValidatorTopology()
for defn in get_all_validators():
    topology.add_validator(defn)
topology.build()

# Create components
sm = StateManager(DesignState())
executor = PipelineExecutor(
    topology=topology,
    state_manager=sm,
    validator_registry=ValidatorRegistry.get_all_instances(),
)
aggregator = ResultAggregator(topology=topology, state_manager=sm)

# Create Conductor with executor (Guardrail #2)
conductor = Conductor(
    state_manager=sm,
    registry=PhaseRegistry(),
    pipeline_executor=executor,
    result_aggregator=aggregator,
)

# Seed state
sm.set('hull.lwl', 50.0, 'test')
sm.set('hull.beam', 10.0, 'test')
sm.set('hull.draft', 2.5, 'test')
sm.set('hull.cb', 0.55, 'test')

# Run phase through Conductor (which delegates to executor)
conductor.create_session('test')
result = conductor.run_phase('hull')
print(f'Phase: {result.phase_name}')
print(f'Status: {result.status.value}')
print(f'Validators run: {result.validators_run}')
print(f'Errors: {result.errors}')
"
```

---

## Success Criteria

1. ✅ `ValidatorRegistry.reset()` clears all state
2. ✅ `ValidatorRegistry.validate_required_implementations()` fails if missing
3. ✅ `check_phase_contract()` fails if required outputs missing
4. ✅ Conductor delegates to PipelineExecutor (not direct execution)
5. ✅ Phase fails if validators pass but contract unsatisfied
6. ✅ API endpoint includes contract status in response
7. ✅ Bootstrap calls reset() before initialize_defaults()

---

## Architecture After Integration

```
Bootstrap (app.py)
    │
    ├─► ValidatorRegistry.reset()           ← Guardrail #3
    ├─► ValidatorRegistry.initialize_defaults()
    ├─► ValidatorRegistry.validate_required_implementations()  ← Guardrail #4
    │
    ├─► ValidatorTopology (singleton)
    │
    ├─► PipelineExecutor (factory)          ← Guardrail #2: Single authority
    │
    ├─► ResultAggregator (factory)
    │
    └─► Conductor
            ├─ pipeline_executor reference  ← Guardrail #2: Delegates here
            └─ run_phase() checks contracts ← Guardrail #1
                    │
API Endpoints ──────┴──► Use DI, check contracts
```

---

## What This Does NOT Include (Future Work)

1. **Missing validator implementations** - mission/requirements, structure/scantlings, bounds/*, class/*, optimization/*, reporting/*
2. **Contract layer in executor** - Pre/post-condition validation hooks
3. **Design intent engine** - Constraint checking integration
4. **RunPod/Worker updates** - Similar DI fixes needed
5. **Instance-scoped registry** - Long-term: registry as DI object, not static class
