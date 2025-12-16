"""
MAGNET ActionExecutor v1.0

Executes validated ActionPlans against the StateManager.

This is the final stage of the Intent→Action Protocol:
1. Intent parsed → 2. ActionPlan proposed → 3. Validated → 4. EXECUTED

The ActionExecutor:
- Takes ONLY validated actions (from ActionPlanValidator)
- Executes within a transaction
- Emits events for each mutation
- Returns ActionResult with execution details

INVARIANT: ActionExecutor only receives pre-validated actions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
import logging

from magnet.kernel.intent_protocol import Action, ActionPlan, ActionType, ActionResult
from magnet.kernel.action_validator import ValidationResult
from magnet.kernel.event_dispatcher import EventDispatcher
from magnet.kernel.events import (
    ActionExecutedEvent,
    PlanExecutedEvent,
    StateMutatedEvent,
    ParameterLockedEvent,
    ParameterUnlockedEvent,
    DesignVersionIncrementedEvent,
    PhaseStartedEvent,
)

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


logger = logging.getLogger("kernel.action_executor")


# =============================================================================
# EXECUTION RESULT
# =============================================================================

@dataclass
class ExecutionResult:
    """
    Result of executing an ActionPlan.

    Contains execution summary and any warnings/errors.
    """
    success: bool
    actions_executed: int
    design_version_before: int
    design_version_after: int
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0


# =============================================================================
# ACTION EXECUTOR
# =============================================================================

class ActionExecutor:
    """
    Executes validated ActionPlans against state.

    Usage:
        executor = ActionExecutor(state_manager, event_dispatcher)

        # Execute a validated plan
        result = executor.execute(validation_result.approved, plan)

        # Check result
        if result.success:
            print(f"Executed {result.actions_executed} actions")
    """

    def __init__(
        self,
        state_manager: "StateManager",
        event_dispatcher: Optional[EventDispatcher] = None,
    ):
        """
        Initialize the executor.

        Args:
            state_manager: StateManager for mutations
            event_dispatcher: Optional dispatcher for events
        """
        self._state_manager = state_manager
        self._events = event_dispatcher

    def execute(
        self,
        actions: List[Action],
        plan: Optional[ActionPlan] = None,
    ) -> ExecutionResult:
        """
        Execute a list of validated actions.

        Args:
            actions: Pre-validated actions (from ValidationResult.approved)
            plan: Original ActionPlan (for context in events)

        Returns:
            ExecutionResult with summary
        """
        start_time = datetime.now(timezone.utc)
        warnings = []
        errors = []

        design_id = plan.design_id if plan else self._state_manager._state.design_id
        version_before = self._state_manager.design_version

        if not actions:
            return ExecutionResult(
                success=True,
                actions_executed=0,
                design_version_before=version_before,
                design_version_after=version_before,
                execution_time_ms=0.0,
            )

        # Begin transaction
        try:
            self._state_manager.begin_transaction()
        except Exception as e:
            logger.error(f"Failed to begin transaction: {e}")
            return ExecutionResult(
                success=False,
                actions_executed=0,
                design_version_before=version_before,
                design_version_after=version_before,
                errors=[f"Transaction start failed: {e}"],
            )

        # Execute each action
        executed_count = 0
        try:
            for action in actions:
                result = self._execute_action(action, design_id)
                if result.success:
                    executed_count += 1
                    warnings.extend(result.warnings)
                else:
                    errors.extend(result.errors)
                    # Continue executing other actions (partial success)

            # Commit transaction
            new_version = self._state_manager.commit()

            # Emit version increment event
            if self._events:
                self._events.emit(DesignVersionIncrementedEvent(
                    design_id=design_id,
                    design_version=new_version,
                    old_version=version_before,
                    new_version=new_version,
                ))

            # Emit plan executed event
            if self._events and plan:
                self._events.emit(PlanExecutedEvent(
                    design_id=design_id,
                    design_version=new_version,
                    plan_id=plan.plan_id,
                    intent_id=plan.intent_id,
                    actions_executed=executed_count,
                    design_version_before=version_before,
                    design_version_after=new_version,
                ))

        except Exception as e:
            logger.error(f"Execution failed, rolling back: {e}")
            try:
                self._state_manager.rollback_transaction()
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}")

            return ExecutionResult(
                success=False,
                actions_executed=0,
                design_version_before=version_before,
                design_version_after=version_before,
                errors=[f"Execution failed: {e}"],
            )

        end_time = datetime.now(timezone.utc)
        execution_ms = (end_time - start_time).total_seconds() * 1000

        return ExecutionResult(
            success=True,
            actions_executed=executed_count,
            design_version_before=version_before,
            design_version_after=new_version,
            warnings=warnings,
            errors=errors,
            execution_time_ms=execution_ms,
        )

    def _execute_action(
        self,
        action: Action,
        design_id: str,
    ) -> ExecutionResult:
        """
        Execute a single action.

        Args:
            action: The action to execute
            design_id: Design ID for events

        Returns:
            ExecutionResult for this action
        """
        try:
            match action.action_type:
                case ActionType.SET:
                    return self._execute_set(action, design_id)

                case ActionType.LOCK:
                    return self._execute_lock(action, design_id)

                case ActionType.UNLOCK:
                    return self._execute_unlock(action, design_id)

                case ActionType.RUN_PHASES:
                    return self._execute_run_phases(action, design_id)

                case ActionType.EXPORT:
                    return self._execute_export(action, design_id)

                case ActionType.REQUEST_CLARIFICATION:
                    return self._execute_clarification(action, design_id)

                case ActionType.NOOP:
                    return ExecutionResult(
                        success=True,
                        actions_executed=1,
                        design_version_before=0,
                        design_version_after=0,
                    )

                case _:
                    return ExecutionResult(
                        success=False,
                        actions_executed=0,
                        design_version_before=0,
                        design_version_after=0,
                        errors=[f"Unknown action type: {action.action_type}"],
                    )

        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            return ExecutionResult(
                success=False,
                actions_executed=0,
                design_version_before=0,
                design_version_after=0,
                errors=[str(e)],
            )

    def _execute_set(self, action: Action, design_id: str) -> ExecutionResult:
        """Execute a SET action."""
        old_value = self._state_manager.get(action.path)
        self._state_manager.set(action.path, action.value, source="action_executor")

        # Emit state mutated event
        if self._events:
            self._events.emit(StateMutatedEvent(
                design_id=design_id,
                design_version=self._state_manager.design_version,
                path=action.path,
                old_value=old_value,
                new_value=action.value,
                source="action_executor",
            ))

            self._events.emit(ActionExecutedEvent(
                design_id=design_id,
                design_version=self._state_manager.design_version,
                action_type="set",
                path=action.path,
                old_value=old_value,
                new_value=action.value,
                unit=action.unit,
            ))

        return ExecutionResult(
            success=True,
            actions_executed=1,
            design_version_before=0,
            design_version_after=0,
        )

    def _execute_lock(self, action: Action, design_id: str) -> ExecutionResult:
        """Execute a LOCK action."""
        self._state_manager.lock_parameter(action.path)

        if self._events:
            self._events.emit(ParameterLockedEvent(
                design_id=design_id,
                design_version=self._state_manager.design_version,
                path=action.path,
                locked_by="action_executor",
            ))

        return ExecutionResult(
            success=True,
            actions_executed=1,
            design_version_before=0,
            design_version_after=0,
        )

    def _execute_unlock(self, action: Action, design_id: str) -> ExecutionResult:
        """Execute an UNLOCK action."""
        self._state_manager.unlock_parameter(action.path)

        if self._events:
            self._events.emit(ParameterUnlockedEvent(
                design_id=design_id,
                design_version=self._state_manager.design_version,
                path=action.path,
            ))

        return ExecutionResult(
            success=True,
            actions_executed=1,
            design_version_before=0,
            design_version_after=0,
        )

    def _execute_run_phases(self, action: Action, design_id: str) -> ExecutionResult:
        """
        Execute a RUN_PHASES action.

        Note: This emits phase start events but actual phase execution
        is delegated to the Conductor.
        """
        # Emit phase start events for tracking
        if self._events and action.phases:
            for phase in action.phases:
                self._events.emit(PhaseStartedEvent(
                    design_id=design_id,
                    design_version=self._state_manager.design_version,
                    phase=phase,
                ))

        # Note: Actual phase execution is handled by Conductor
        # This action just signals intent to run phases
        return ExecutionResult(
            success=True,
            actions_executed=1,
            design_version_before=0,
            design_version_after=0,
            warnings=["RUN_PHASES action recorded; execution delegated to Conductor"],
        )

    def _execute_export(self, action: Action, design_id: str) -> ExecutionResult:
        """
        Execute an EXPORT action.

        Note: Actual export is handled by DesignExporter.
        This action just signals intent to export.
        """
        return ExecutionResult(
            success=True,
            actions_executed=1,
            design_version_before=0,
            design_version_after=0,
            warnings=[f"EXPORT action recorded; format={action.format}"],
        )

    def _execute_clarification(self, action: Action, design_id: str) -> ExecutionResult:
        """
        Execute a REQUEST_CLARIFICATION action.

        This is a no-op in terms of state mutation, but it's recorded
        for the response to include the clarification message.
        """
        return ExecutionResult(
            success=True,
            actions_executed=1,
            design_version_before=0,
            design_version_after=0,
            warnings=[f"Clarification requested: {action.message}"],
        )
