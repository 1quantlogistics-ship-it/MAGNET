"""
MAGNET Cascade Executor

Module 03 v1.1 - Production-Ready

Executes recalculations in dependency order after invalidation.

v1.1 Fixes Applied:
- FIX #8: Supports partial recalculation (subset of stale params)
- FIX #9: Tracks execution time per parameter
- FIX #10: Integrates with StateManager for value updates
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, TYPE_CHECKING
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import logging
import time

if TYPE_CHECKING:
    from .graph import DependencyGraph
    from .invalidation import InvalidationEngine
    from magnet.core.state_manager import StateManager

logger = logging.getLogger(__name__)


# =============================================================================
# RECALCULATION RESULT
# =============================================================================

@dataclass
class RecalculationResult:
    """Result of recalculating a single parameter."""
    parameter: str
    success: bool
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Value info
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    value_changed: bool = False

    # Execution info
    execution_time_ms: int = 0
    was_skipped: bool = False
    skip_reason: Optional[str] = None

    # Errors
    error: Optional[str] = None
    error_traceback: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter": self.parameter,
            "success": self.success,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "old_value": str(self.old_value) if self.old_value is not None else None,
            "new_value": str(self.new_value) if self.new_value is not None else None,
            "value_changed": self.value_changed,
            "execution_time_ms": self.execution_time_ms,
            "was_skipped": self.was_skipped,
            "skip_reason": self.skip_reason,
            "error": self.error,
        }


@dataclass
class RecalculationOrder:
    """Ordered list of parameters to recalculate."""
    parameters: List[str]
    phases_affected: List[str]
    total_count: int
    estimated_time_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameters": self.parameters,
            "phases_affected": self.phases_affected,
            "total_count": self.total_count,
            "estimated_time_ms": self.estimated_time_ms,
        }


@dataclass
class CascadeResult:
    """Result of a cascade recalculation."""
    cascade_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Results
    results: Dict[str, RecalculationResult] = field(default_factory=dict)

    # Summary
    total_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0

    # Timing
    total_time_ms: int = 0

    # Metadata
    triggered_by: str = "system"
    trigger_parameter: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.failed_count == 0

    def get_summary(self) -> Dict[str, Any]:
        return {
            "cascade_id": self.cascade_id,
            "success": self.success,
            "total": self.total_count,
            "succeeded": self.success_count,
            "failed": self.failed_count,
            "skipped": self.skipped_count,
            "total_time_ms": self.total_time_ms,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cascade_id": self.cascade_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "results": {k: v.to_dict() for k, v in self.results.items()},
            "total_count": self.total_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "total_time_ms": self.total_time_ms,
            "triggered_by": self.triggered_by,
            "trigger_parameter": self.trigger_parameter,
        }


# =============================================================================
# CALCULATOR REGISTRY
# =============================================================================

# Type for calculator functions
CalculatorFunc = Callable[["StateManager", str], Any]


class CalculatorRegistry:
    """Registry of calculator functions for computed parameters."""

    def __init__(self):
        self._calculators: Dict[str, CalculatorFunc] = {}
        self._calculator_metadata: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        param: str,
        calculator: CalculatorFunc,
        estimated_time_ms: int = 100,
        requires_lock: bool = False,
    ) -> None:
        """Register a calculator for a parameter."""
        self._calculators[param] = calculator
        self._calculator_metadata[param] = {
            "estimated_time_ms": estimated_time_ms,
            "requires_lock": requires_lock,
        }

    def has_calculator(self, param: str) -> bool:
        """Check if a calculator is registered for a parameter."""
        return param in self._calculators

    def get_calculator(self, param: str) -> Optional[CalculatorFunc]:
        """Get calculator for a parameter."""
        return self._calculators.get(param)

    def get_estimated_time(self, param: str) -> int:
        """Get estimated execution time for a calculator."""
        meta = self._calculator_metadata.get(param, {})
        return meta.get("estimated_time_ms", 100)

    def list_calculators(self) -> List[str]:
        """List all registered calculator parameters."""
        return list(self._calculators.keys())


# =============================================================================
# CASCADE EXECUTOR
# =============================================================================

class CascadeExecutor:
    """
    Executes parameter recalculations in dependency order.

    v1.1 Fixes:
    - FIX #8: Supports partial recalculation
    - FIX #9: Tracks execution time
    - FIX #10: Integrates with StateManager
    """

    DEFAULT_MAX_WORKERS = 4

    def __init__(
        self,
        dependency_graph: "DependencyGraph",
        invalidation_engine: "InvalidationEngine",
        state_manager: "StateManager",
        calculator_registry: Optional[CalculatorRegistry] = None,
        max_workers: int = DEFAULT_MAX_WORKERS,
    ):
        self._graph = dependency_graph
        self._invalidation = invalidation_engine
        self._state_manager = state_manager
        self._registry = calculator_registry or CalculatorRegistry()
        self._max_workers = max_workers

        # Execution state
        self._lock = threading.Lock()
        self._is_running = False
        self._current_cascade: Optional[CascadeResult] = None

        # Progress callbacks
        self._progress_callbacks: List[Callable[[str, RecalculationResult], None]] = []

    def get_recalculation_order(
        self,
        params: Optional[Set[str]] = None
    ) -> RecalculationOrder:
        """
        Get the order in which parameters should be recalculated.

        FIX #8: Supports partial recalculation with subset of params.

        Args:
            params: Optional set of parameters to recalculate.
                   If None, uses all stale parameters.

        Returns:
            RecalculationOrder with parameters in dependency order
        """
        if params is None:
            params = self._invalidation.get_stale_parameters()

        if not params:
            return RecalculationOrder(
                parameters=[],
                phases_affected=[],
                total_count=0,
            )

        # Get computation order
        ordered = self._graph.get_computation_order(params)

        # Filter to only those with calculators
        ordered = [p for p in ordered if self._registry.has_calculator(p)]

        # Get affected phases
        phases = set()
        from .graph import get_phase_for_parameter
        for p in ordered:
            phase = get_phase_for_parameter(p)
            if phase:
                phases.add(phase)

        # Estimate total time
        estimated_time = sum(
            self._registry.get_estimated_time(p)
            for p in ordered
        )

        return RecalculationOrder(
            parameters=ordered,
            phases_affected=sorted(phases),
            total_count=len(ordered),
            estimated_time_ms=estimated_time,
        )

    def execute(
        self,
        params: Optional[Set[str]] = None,
        stop_on_error: bool = False,
        parallel: bool = True,
        triggered_by: str = "system",
        trigger_parameter: Optional[str] = None,
    ) -> CascadeResult:
        """
        Execute cascade recalculation.

        FIX #8: Can recalculate subset of parameters
        FIX #9: Tracks timing per parameter
        FIX #10: Updates StateManager with new values

        Args:
            params: Parameters to recalculate (None = all stale)
            stop_on_error: Stop on first error
            parallel: Run independent calculations in parallel
            triggered_by: Who triggered this cascade
            trigger_parameter: Original parameter that changed

        Returns:
            CascadeResult with all results
        """
        import uuid

        with self._lock:
            if self._is_running:
                raise RuntimeError("Cascade already in progress")
            self._is_running = True

        try:
            cascade_id = str(uuid.uuid4())[:8]
            start_time = datetime.utcnow()

            result = CascadeResult(
                cascade_id=cascade_id,
                started_at=start_time,
                triggered_by=triggered_by,
                trigger_parameter=trigger_parameter,
            )
            self._current_cascade = result

            # Get recalculation order
            order = self.get_recalculation_order(params)
            result.total_count = order.total_count

            if not order.parameters:
                result.completed_at = datetime.utcnow()
                return result

            logger.info(
                f"Starting cascade {cascade_id}: "
                f"{order.total_count} parameters, "
                f"estimated {order.estimated_time_ms}ms"
            )

            # Execute calculations
            if parallel and self._max_workers > 1:
                self._execute_parallel(order.parameters, result, stop_on_error)
            else:
                self._execute_sequential(order.parameters, result, stop_on_error)

            result.completed_at = datetime.utcnow()
            result.total_time_ms = int(
                (result.completed_at - start_time).total_seconds() * 1000
            )

            logger.info(
                f"Cascade {cascade_id} complete: "
                f"{result.success_count} succeeded, "
                f"{result.failed_count} failed, "
                f"{result.skipped_count} skipped in {result.total_time_ms}ms"
            )

            return result

        finally:
            with self._lock:
                self._is_running = False
                self._current_cascade = None

    def _execute_sequential(
        self,
        params: List[str],
        result: CascadeResult,
        stop_on_error: bool,
    ) -> None:
        """Execute calculations sequentially."""
        for param in params:
            calc_result = self._execute_single(param)
            result.results[param] = calc_result

            if calc_result.success:
                result.success_count += 1
            elif calc_result.was_skipped:
                result.skipped_count += 1
            else:
                result.failed_count += 1
                if stop_on_error:
                    logger.warning(f"Stopping cascade due to error in {param}")
                    break

            # Notify progress
            self._notify_progress(param, calc_result)

    def _execute_parallel(
        self,
        params: List[str],
        result: CascadeResult,
        stop_on_error: bool,
    ) -> None:
        """Execute calculations in parallel where possible."""
        completed = set()
        pending = set(params)
        stop_flag = threading.Event()

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            while pending and not stop_flag.is_set():
                # Find ready parameters (all dependencies completed)
                ready = []
                for p in pending:
                    deps = self._graph.get_direct_dependencies(p)
                    calc_deps = deps & set(params)  # Only deps we're calculating
                    if calc_deps.issubset(completed):
                        ready.append(p)

                if not ready:
                    # Shouldn't happen if graph is correct
                    logger.warning("No ready parameters but pending remain")
                    break

                # Submit ready parameters
                futures = {}
                for param in ready:
                    pending.remove(param)
                    future = executor.submit(self._execute_single, param)
                    futures[future] = param

                # Wait for results
                for future in as_completed(futures):
                    param = futures[future]
                    try:
                        calc_result = future.result()
                    except Exception as e:
                        calc_result = RecalculationResult(
                            parameter=param,
                            success=False,
                            started_at=datetime.utcnow(),
                            completed_at=datetime.utcnow(),
                            error=str(e),
                        )

                    result.results[param] = calc_result
                    completed.add(param)

                    if calc_result.success:
                        result.success_count += 1
                    elif calc_result.was_skipped:
                        result.skipped_count += 1
                    else:
                        result.failed_count += 1
                        if stop_on_error:
                            stop_flag.set()

                    self._notify_progress(param, calc_result)

    def _execute_single(self, param: str) -> RecalculationResult:
        """Execute a single parameter calculation."""
        start_time = datetime.utcnow()
        calc_result = RecalculationResult(
            parameter=param,
            success=False,
            started_at=start_time,
        )

        # Get calculator
        calculator = self._registry.get_calculator(param)
        if not calculator:
            calc_result.was_skipped = True
            calc_result.skip_reason = "No calculator registered"
            calc_result.completed_at = datetime.utcnow()
            return calc_result

        # Get old value
        try:
            calc_result.old_value = self._state_manager.get(param)
        except Exception:
            calc_result.old_value = None

        # Execute calculation
        try:
            start = time.time()
            new_value = calculator(self._state_manager, param)
            calc_result.execution_time_ms = int((time.time() - start) * 1000)

            calc_result.new_value = new_value
            calc_result.value_changed = calc_result.old_value != new_value
            calc_result.success = True

            # FIX #10: Update StateManager with new value
            self._state_manager.set(param, new_value, source="CascadeExecutor")

            # Mark parameter as valid
            self._invalidation.mark_valid(param)

        except Exception as e:
            import traceback
            calc_result.error = str(e)
            calc_result.error_traceback = traceback.format_exc()
            logger.error(f"Calculation error for {param}: {e}")

        calc_result.completed_at = datetime.utcnow()
        return calc_result

    def _notify_progress(self, param: str, result: RecalculationResult) -> None:
        """Notify progress callbacks."""
        for callback in self._progress_callbacks:
            try:
                callback(param, result)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    def on_progress(
        self,
        callback: Callable[[str, RecalculationResult], None]
    ) -> None:
        """Register a progress callback."""
        self._progress_callbacks.append(callback)

    def is_running(self) -> bool:
        """Check if a cascade is currently running."""
        return self._is_running

    def get_current_cascade(self) -> Optional[CascadeResult]:
        """Get the current cascade result (if running)."""
        return self._current_cascade

    def register_calculator(
        self,
        param: str,
        calculator: CalculatorFunc,
        estimated_time_ms: int = 100,
    ) -> None:
        """Convenience method to register a calculator."""
        self._registry.register(param, calculator, estimated_time_ms)
