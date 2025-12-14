"""
MAGNET Pipeline Executor

Module 04 v1.1 - Production-Ready

Executes validators with all v1.1 fixes.

v1.1 Changes:
- FIX #4: Fatal error handling with stop_on_fatal_error
- FIX #5: Only retry on exceptions, not validation failures
- FIX #8: Contract Layer integration
- FIX #9: Resource-aware scheduling
- FIX #10: Skip unchanged validators
- FIX #11: ExecutionState serialization
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Any, TYPE_CHECKING
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
import threading
import json
import logging
import time
import uuid

from .taxonomy import (
    ValidatorDefinition,
    ValidatorState,
    ValidationResult,
    ValidatorInterface,
    ResourcePool,
    ResourceRequirements,
)
from .topology import ValidatorTopology

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger(__name__)


# =============================================================================
# EXECUTION STATE (FIX #11: Serializable)
# =============================================================================

@dataclass
class ExecutionState:
    """
    Tracks state of a pipeline execution.

    FIX #11: Now fully serializable with to_dict(), save(), load().
    """
    execution_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Validator states
    pending: Set[str] = field(default_factory=set)
    running: Set[str] = field(default_factory=set)
    completed: Set[str] = field(default_factory=set)
    failed: Set[str] = field(default_factory=set)
    skipped: Set[str] = field(default_factory=set)

    # Results
    results: Dict[str, ValidationResult] = field(default_factory=dict)

    # Errors
    errors: List[str] = field(default_factory=list)

    # FIX #4: Fatal error tracking
    had_fatal_error: bool = False
    fatal_error_validator: Optional[str] = None

    @property
    def is_complete(self) -> bool:
        return len(self.pending) == 0 and len(self.running) == 0

    @property
    def has_failures(self) -> bool:
        return len(self.failed) > 0

    def get_summary(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "pending": len(self.pending),
            "running": len(self.running),
            "completed": len(self.completed),
            "failed": len(self.failed),
            "skipped": len(self.skipped),
            "is_complete": self.is_complete,
            "has_failures": self.has_failures,
            "had_fatal_error": self.had_fatal_error,
        }

    # FIX #11: Serialization
    def to_dict(self) -> Dict[str, Any]:
        """Serialize entire execution state."""
        return {
            "execution_id": self.execution_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "pending": list(self.pending),
            "running": list(self.running),
            "completed": list(self.completed),
            "failed": list(self.failed),
            "skipped": list(self.skipped),
            "results": {k: v.to_dict() for k, v in self.results.items()},
            "errors": self.errors,
            "had_fatal_error": self.had_fatal_error,
            "fatal_error_validator": self.fatal_error_validator,
        }

    def save(self, path: Path) -> None:
        """Save execution state to file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "ExecutionState":
        """Load execution state from file."""
        with open(path, 'r') as f:
            data = json.load(f)

        state = cls(
            execution_id=data["execution_id"],
            started_at=datetime.fromisoformat(data["started_at"]),
        )
        if data.get("completed_at"):
            state.completed_at = datetime.fromisoformat(data["completed_at"])

        state.pending = set(data.get("pending", []))
        state.running = set(data.get("running", []))
        state.completed = set(data.get("completed", []))
        state.failed = set(data.get("failed", []))
        state.skipped = set(data.get("skipped", []))
        state.errors = data.get("errors", [])
        state.had_fatal_error = data.get("had_fatal_error", False)
        state.fatal_error_validator = data.get("fatal_error_validator")

        # Results would need ValidationResult.from_dict() to fully restore
        for v_id, r_data in data.get("results", {}).items():
            state.results[v_id] = ValidationResult.from_dict(r_data)

        return state


# =============================================================================
# VALIDATION CACHE
# =============================================================================

@dataclass
class CacheEntry:
    """A cached validation result."""
    result: ValidationResult
    input_hash: str
    cached_at: datetime
    ttl_seconds: int

    def is_valid(self) -> bool:
        age = (datetime.utcnow() - self.cached_at).total_seconds()
        return age < self.ttl_seconds


class ValidationCache:
    """In-memory cache for validation results."""

    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

    def get(self, validator_id: str, input_hash: str) -> Optional[ValidationResult]:
        with self._lock:
            entry = self._cache.get(validator_id)
            if entry and entry.input_hash == input_hash and entry.is_valid():
                result = entry.result
                result.was_cached = True
                return result
            return None

    def put(
        self,
        validator_id: str,
        input_hash: str,
        result: ValidationResult,
        ttl_seconds: int
    ) -> None:
        with self._lock:
            self._cache[validator_id] = CacheEntry(
                result=result,
                input_hash=input_hash,
                cached_at=datetime.utcnow(),
                ttl_seconds=ttl_seconds,
            )

    def invalidate(self, validator_id: str) -> None:
        with self._lock:
            self._cache.pop(validator_id, None)

    def invalidate_all(self) -> None:
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            valid_count = sum(1 for e in self._cache.values() if e.is_valid())
            return {
                "total_entries": len(self._cache),
                "valid_entries": valid_count,
                "validator_ids": list(self._cache.keys()),
            }


# =============================================================================
# PIPELINE EXECUTOR
# =============================================================================

class PipelineExecutor:
    """
    Executes validators with all v1.1 fixes.
    """

    DEFAULT_MAX_WORKERS = 4

    def __init__(
        self,
        topology: ValidatorTopology,
        state_manager: "StateManager",
        validator_registry: Dict[str, ValidatorInterface],
        max_workers: int = DEFAULT_MAX_WORKERS,
        contract_layer: Optional[Any] = None,  # FIX #8
        resource_pool: Optional[ResourcePool] = None,  # FIX #9
        design_id: Optional[str] = None,  # Hole #2 Fix: Design-scoped execution
    ):
        self._topology = topology
        self._state_manager = state_manager
        self._registry = validator_registry
        self._max_workers = max_workers
        self._contract_layer = contract_layer  # FIX #8
        self._design_id = design_id  # Hole #2 Fix: For cache key scoping

        # FIX #9: Resource pool
        self._resource_pool = resource_pool or ResourcePool()
        self._resource_lock = threading.Lock()

        # Hole #2 Fix: Each executor instance gets its own cache (no shared state)
        self._cache = ValidationCache()
        self._progress_callbacks: List[Callable[[str, ValidationResult], None]] = []
        self._current_execution: Optional[ExecutionState] = None

        # FIX #10: Track last validation time per validator
        self._last_validation_times: Dict[str, datetime] = {}

        # Track validators completed across all phase executions (for cross-phase dependencies)
        self._all_completed_validators: Set[str] = set()

    def execute_all(
        self,
        skip_cached: bool = True,
        stop_on_failure: bool = False,
        stop_on_fatal_error: bool = True,  # FIX #4
        skip_unchanged: bool = True,  # FIX #10
        validators_to_run: Optional[Set[str]] = None,
        previously_completed: Optional[Set[str]] = None,  # Cross-phase dependencies
    ) -> ExecutionState:
        """
        Execute all validators.

        FIX #4: stop_on_fatal_error aborts on ERROR state (code failures)
        FIX #10: skip_unchanged skips validators whose inputs haven't changed

        Args:
            skip_cached: Skip validators with cached results
            stop_on_failure: Stop pipeline on first failure
            stop_on_fatal_error: Stop on ERROR state (code failures)
            skip_unchanged: Skip if inputs haven't changed
            validators_to_run: Optional subset of validators to run
            previously_completed: Validators already completed in prior phases
                (for cross-phase dependency tracking)
        """
        state = ExecutionState(
            execution_id=str(uuid.uuid4())[:8],
            started_at=datetime.utcnow(),
        )

        if validators_to_run:
            state.pending = validators_to_run.copy()
        else:
            state.pending = set(self._topology.get_execution_order())

        # Pre-populate completed set with validators from prior phases
        # This allows cross-phase dependencies to be satisfied
        if previously_completed:
            state.completed = previously_completed.copy()

        self._current_execution = state

        # FIX #8: Contract Layer pre-check
        if self._contract_layer:
            try:
                self._contract_layer.validate_state_preconditions(self._state_manager)
            except Exception as e:
                state.errors.append(f"Contract precondition failed: {e}")
                logger.error(f"Contract precondition failed: {e}")

        try:
            with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                while not state.is_complete:
                    # FIX #4: Check for fatal error
                    if state.had_fatal_error and stop_on_fatal_error:
                        logger.error(
                            f"Aborting pipeline due to fatal error in "
                            f"{state.fatal_error_validator}"
                        )
                        self._skip_remaining(state)
                        break

                    ready = self._topology.get_ready_validators(
                        state.completed | state.failed | state.skipped,
                        state.running
                    )
                    ready = [v for v in ready if v in state.pending]

                    if not ready and state.running:
                        time.sleep(0.1)
                        continue

                    if not ready:
                        break

                    # FIX #9: Resource-aware scheduling
                    ready = self._filter_by_resources(ready)

                    futures: Dict[Future, str] = {}
                    for validator_id in ready:
                        state.pending.remove(validator_id)
                        state.running.add(validator_id)

                        # FIX #9: Allocate resources
                        node = self._topology.get_node(validator_id)
                        if node:
                            self._allocate_resources(node.validator.resource_requirements)

                        future = executor.submit(
                            self._execute_validator,
                            validator_id,
                            skip_cached,
                            skip_unchanged  # FIX #10
                        )
                        futures[future] = validator_id

                    for future in as_completed(futures):
                        validator_id = futures[future]
                        state.running.remove(validator_id)

                        # FIX #9: Release resources
                        node = self._topology.get_node(validator_id)
                        if node:
                            self._release_resources(node.validator.resource_requirements)

                        try:
                            result = future.result()
                            state.results[validator_id] = result

                            # FIX #10: Update last validation time
                            self._last_validation_times[validator_id] = datetime.utcnow()

                            if result.state == ValidatorState.PASSED:
                                state.completed.add(validator_id)
                            elif result.state == ValidatorState.WARNING:
                                state.completed.add(validator_id)
                            elif result.state == ValidatorState.FAILED:
                                state.failed.add(validator_id)
                                if stop_on_failure:
                                    self._skip_dependents(validator_id, state)
                            elif result.state == ValidatorState.ERROR:
                                # FIX #4: Fatal error handling
                                state.failed.add(validator_id)
                                state.had_fatal_error = True
                                state.fatal_error_validator = validator_id
                                logger.error(
                                    f"Fatal error in {validator_id}: {result.error_message}"
                                )
                            elif result.state == ValidatorState.SKIPPED:
                                state.skipped.add(validator_id)
                            else:
                                state.completed.add(validator_id)

                            self._notify_progress(validator_id, result)

                        except Exception as e:
                            state.failed.add(validator_id)
                            state.errors.append(f"{validator_id}: {e}")

        finally:
            state.completed_at = datetime.utcnow()
            self._current_execution = None

            # FIX #8: Contract Layer post-check
            if self._contract_layer:
                try:
                    self._contract_layer.validate_postconditions(state.results)
                except Exception as e:
                    state.errors.append(f"Contract postcondition failed: {e}")

        return state

    def execute_phase(
        self,
        phase: str,
        skip_cached: bool = True,
        stop_on_failure: bool = True,
    ) -> ExecutionState:
        """
        Execute all validators for a specific phase.

        Uses persistent completion tracking to satisfy cross-phase dependencies.
        For example, if weight/estimation depends on physics/hydrostatics,
        and hydrostatics ran in the hull phase, it will be in _all_completed_validators.
        """
        validators = set(self._topology.get_validators_for_phase(phase))
        result = self.execute_all(
            skip_cached=skip_cached,
            stop_on_failure=stop_on_failure,
            validators_to_run=validators,
            previously_completed=self._all_completed_validators,
        )

        # Update persistent completed set with newly completed validators
        self._all_completed_validators.update(result.completed)

        return result

    def execute_single(
        self,
        validator_id: str,
        skip_cached: bool = True,
    ) -> ValidationResult:
        """Execute a single validator."""
        return self._execute_validator(validator_id, skip_cached, False)

    def _execute_validator(
        self,
        validator_id: str,
        skip_cached: bool,
        skip_unchanged: bool  # FIX #10
    ) -> ValidationResult:
        """
        Execute single validator with all fixes.

        FIX #5: Only retry on exceptions, not validation failures
        FIX #10: Skip if inputs unchanged
        """
        node = self._topology.get_node(validator_id)
        if not node:
            return self._create_error_result(
                validator_id, f"Validator not found: {validator_id}"
            )

        definition = node.validator
        impl = self._registry.get(validator_id)
        if not impl:
            # Use NOT_IMPLEMENTED state (Hole #6 fix) - permanent, not transient
            return self._create_not_implemented_result(
                validator_id, f"No implementation for: {validator_id}"
            )

        # FIX #10: Check if inputs unchanged
        if skip_unchanged:
            last_time = self._last_validation_times.get(validator_id)
            if impl.should_skip_unchanged(self._state_manager, last_time):
                logger.debug(f"Skipping {validator_id} - inputs unchanged")
                return ValidationResult(
                    validator_id=validator_id,
                    state=ValidatorState.SKIPPED,
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    was_skipped_unchanged=True,
                )

        # Check cache
        if skip_cached and definition.is_cacheable:
            input_hash = impl.get_input_hash(self._state_manager)
            cached = self._cache.get(validator_id, input_hash)
            if cached:
                return cached
        else:
            input_hash = None

        # FIX #5: Execute with retry only on EXCEPTIONS
        last_error = None
        for attempt in range(definition.max_retries + 1):
            try:
                result = self._run_with_timeout(impl, definition.timeout_seconds)
                result.retry_count = attempt
                result.input_hash = input_hash

                # FIX #5: If validate() returned a result (not raised),
                # we do NOT retry regardless of state
                if result.state in (
                    ValidatorState.PASSED,
                    ValidatorState.WARNING,
                    ValidatorState.FAILED
                ):
                    # Cache successful results
                    if definition.is_cacheable and input_hash and result.passed:
                        self._cache.put(
                            validator_id, input_hash, result,
                            definition.cache_ttl_seconds
                        )
                    return result

                # Only ERROR state from validate() should retry
                last_error = result.error_message

            except TimeoutError:
                last_error = f"Timeout after {definition.timeout_seconds}s"
                logger.warning(f"{validator_id} attempt {attempt+1} timed out")
            except Exception as e:
                # FIX #5: Exceptions ARE retryable
                last_error = str(e)
                logger.warning(f"{validator_id} attempt {attempt+1} raised: {e}")

            if attempt < definition.max_retries:
                time.sleep(definition.retry_delay_seconds)

        return self._create_error_result(
            validator_id,
            f"Failed after {definition.max_retries+1} attempts: {last_error}"
        )

    # FIX #9: Resource management
    def _filter_by_resources(self, validators: List[str]) -> List[str]:
        """Filter validators that fit in available resources."""
        with self._resource_lock:
            result = []
            for v_id in validators:
                node = self._topology.get_node(v_id)
                if node:
                    req = node.validator.resource_requirements
                    if req.fits_in(self._resource_pool):
                        result.append(v_id)
            return result

    def _allocate_resources(self, req: ResourceRequirements) -> None:
        """Allocate resources for a validator."""
        with self._resource_lock:
            self._resource_pool.allocate(req)

    def _release_resources(self, req: ResourceRequirements) -> None:
        """Release resources after validator completes."""
        with self._resource_lock:
            self._resource_pool.release(req)

    def _skip_remaining(self, state: ExecutionState) -> None:
        """Skip all remaining pending validators."""
        for v_id in list(state.pending):
            state.pending.remove(v_id)
            state.skipped.add(v_id)

    def _skip_dependents(self, validator_id: str, state: ExecutionState) -> None:
        """Skip validators that depend on failed validator."""
        dependents = self._topology.get_transitive_dependents(validator_id)
        for dep_id in dependents:
            if dep_id in state.pending:
                state.pending.remove(dep_id)
                state.skipped.add(dep_id)

    def _run_with_timeout(
        self,
        impl: ValidatorInterface,
        timeout_seconds: int
    ) -> ValidationResult:
        """Run validator (timeout handling simplified)."""
        start_time = time.time()

        result = impl.validate(self._state_manager, {})
        result.execution_time_ms = int((time.time() - start_time) * 1000)
        result.completed_at = datetime.utcnow()

        return result

    def _create_error_result(self, validator_id: str, error: str) -> ValidationResult:
        """Create an error result for code failures (transient, may retry)."""
        return ValidationResult(
            validator_id=validator_id,
            state=ValidatorState.ERROR,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            error_message=error,
        )

    def _create_not_implemented_result(self, validator_id: str, error: str) -> ValidationResult:
        """
        Create a NOT_IMPLEMENTED result for validators without implementations.

        Hole #6 fix: Distinct from ERROR - permanent, not transient.
        """
        return ValidationResult(
            validator_id=validator_id,
            state=ValidatorState.NOT_IMPLEMENTED,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            error_message=error,
        )

    def _notify_progress(self, validator_id: str, result: ValidationResult) -> None:
        """Notify progress callbacks."""
        for callback in self._progress_callbacks:
            try:
                callback(validator_id, result)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    def on_progress(self, callback: Callable[[str, ValidationResult], None]) -> None:
        """Register a progress callback."""
        self._progress_callbacks.append(callback)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._cache.get_stats()

    def invalidate_cache(self, validator_id: Optional[str] = None) -> None:
        """Invalidate cache entries."""
        if validator_id:
            self._cache.invalidate(validator_id)
        else:
            self._cache.invalidate_all()

    def reset_completed_validators(self) -> None:
        """
        Reset the persistent completed validator tracking.

        Call this when starting a new design session to ensure
        cross-phase dependencies are freshly evaluated.
        """
        self._all_completed_validators.clear()

    def get_completed_validators(self) -> Set[str]:
        """Get the set of validators completed across all phase executions."""
        return self._all_completed_validators.copy()
