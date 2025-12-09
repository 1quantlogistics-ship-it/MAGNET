"""
errors/recovery.py - Automatic error recovery
BRAVO OWNS THIS FILE.

Section 43: Error Taxonomy
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from enum import Enum
import logging

from .taxonomy import MAGNETError, ErrorCode, ErrorSeverity

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class RecoveryStrategy(Enum):
    """Recovery strategy types."""
    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    REVERT = "revert"
    ESCALATE = "escalate"
    ABORT = "abort"


@dataclass
class RecoveryOption:
    """Single recovery option."""

    strategy: RecoveryStrategy
    description: str = ""

    # Auto-execution
    auto_execute: bool = False
    success_probability: float = 0.5

    # For RETRY
    max_retries: int = 3

    # For FALLBACK
    fallback_value: Any = None
    fallback_path: str = ""

    # For REVERT
    revert_to_version: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "description": self.description,
            "auto_execute": self.auto_execute,
            "success_probability": self.success_probability,
        }


# Recovery strategies by error code
RECOVERY_STRATEGIES: Dict[ErrorCode, List[RecoveryOption]] = {
    ErrorCode.VAL_FAILED: [
        RecoveryOption(
            strategy=RecoveryStrategy.RETRY,
            description="Retry validation after fixing",
            max_retries=3,
        ),
        RecoveryOption(
            strategy=RecoveryStrategy.ESCALATE,
            description="Escalate to supervisor",
        ),
    ],
    ErrorCode.BND_EXCEEDED: [
        RecoveryOption(
            strategy=RecoveryStrategy.FALLBACK,
            description="Use boundary value",
            auto_execute=True,
            success_probability=0.8,
        ),
        RecoveryOption(
            strategy=RecoveryStrategy.RETRY,
            description="Retry with adjusted value",
        ),
    ],
    ErrorCode.BND_MINIMUM: [
        RecoveryOption(
            strategy=RecoveryStrategy.FALLBACK,
            description="Use minimum allowed value",
            auto_execute=True,
            success_probability=0.9,
        ),
    ],
    ErrorCode.BND_MAXIMUM: [
        RecoveryOption(
            strategy=RecoveryStrategy.FALLBACK,
            description="Use maximum allowed value",
            auto_execute=True,
            success_probability=0.9,
        ),
    ],
    ErrorCode.PHY_IMPOSSIBLE: [
        RecoveryOption(
            strategy=RecoveryStrategy.REVERT,
            description="Revert to last valid state",
        ),
        RecoveryOption(
            strategy=RecoveryStrategy.ESCALATE,
            description="Escalate - physics violation requires design change",
        ),
    ],
    ErrorCode.STA_TRANSACTION: [  # v1.1
        RecoveryOption(
            strategy=RecoveryStrategy.REVERT,
            description="Rollback transaction",
            auto_execute=True,
            success_probability=0.95,
        ),
        RecoveryOption(
            strategy=RecoveryStrategy.RETRY,
            description="Retry transaction",
            max_retries=2,
        ),
    ],
    ErrorCode.SYS_TIMEOUT: [
        RecoveryOption(
            strategy=RecoveryStrategy.RETRY,
            description="Retry with extended timeout",
            max_retries=2,
        ),
        RecoveryOption(
            strategy=RecoveryStrategy.SKIP,
            description="Skip and continue",
        ),
    ],
    ErrorCode.AGT_CONFLICT: [
        RecoveryOption(
            strategy=RecoveryStrategy.ESCALATE,
            description="Escalate to supervisor for resolution",
            auto_execute=True,
        ),
    ],
}


@dataclass
class RecoveryResult:
    """Result of recovery attempt."""

    success: bool = False
    strategy_used: RecoveryStrategy = RecoveryStrategy.ABORT

    message: str = ""

    # If recovery modified state
    modifications: List[Dict] = field(default_factory=list)

    # If further action needed
    requires_escalation: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "strategy": self.strategy_used.value,
            "message": self.message,
            "requires_escalation": self.requires_escalation,
        }


class RecoveryExecutor:
    """
    Executes recovery strategies for errors.
    """

    def __init__(self, state: "StateManager" = None):
        self.state = state
        self.logger = logging.getLogger("errors.recovery")

        # Custom handlers by error code
        self._handlers: Dict[ErrorCode, Callable] = {}

    def register_handler(
        self,
        code: ErrorCode,
        handler: Callable[[MAGNETError], RecoveryResult],
    ) -> None:
        """Register custom recovery handler."""
        self._handlers[code] = handler

    def attempt_recovery(
        self,
        error: MAGNETError,
        auto_only: bool = True,
    ) -> RecoveryResult:
        """
        Attempt to recover from an error.

        Args:
            error: The error to recover from
            auto_only: Only try auto-executable strategies
        """
        # Check for custom handler
        if error.code in self._handlers:
            try:
                return self._handlers[error.code](error)
            except Exception as e:
                self.logger.error(f"Custom handler failed: {e}")

        # Get strategies for this error
        strategies = RECOVERY_STRATEGIES.get(error.code, [])

        if auto_only:
            strategies = [s for s in strategies if s.auto_execute]

        if not strategies:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.ABORT,
                message="No recovery strategies available",
                requires_escalation=True,
            )

        # Try strategies in order
        for strategy in strategies:
            result = self._execute_strategy(error, strategy)
            if result.success:
                return result

        # All strategies failed
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.ESCALATE,
            message="All recovery strategies failed",
            requires_escalation=True,
        )

    def _execute_strategy(
        self,
        error: MAGNETError,
        option: RecoveryOption,
    ) -> RecoveryResult:
        """Execute a single recovery strategy."""

        self.logger.info(f"Attempting {option.strategy.value} for {error.code.name}")

        if option.strategy == RecoveryStrategy.FALLBACK:
            return self._execute_fallback(error, option)

        elif option.strategy == RecoveryStrategy.REVERT:
            return self._execute_revert(error, option)

        elif option.strategy == RecoveryStrategy.RETRY:
            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.RETRY,
                message=f"Will retry (max {option.max_retries})",
            )

        elif option.strategy == RecoveryStrategy.SKIP:
            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.SKIP,
                message="Skipping failed operation",
            )

        elif option.strategy == RecoveryStrategy.ESCALATE:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.ESCALATE,
                message="Escalation required",
                requires_escalation=True,
            )

        return RecoveryResult(success=False, message="Unknown strategy")

    def _execute_fallback(
        self,
        error: MAGNETError,
        option: RecoveryOption,
    ) -> RecoveryResult:
        """Execute fallback strategy."""
        if not self.state or not error.path:
            return RecoveryResult(success=False, message="Cannot apply fallback")

        fallback_value = option.fallback_value

        # Determine fallback value based on error type
        if error.code == ErrorCode.BND_MINIMUM and error.expected_value:
            # Use minimum bound
            try:
                bounds = eval(error.expected_value)
                fallback_value = bounds[0] if isinstance(bounds, (list, tuple)) else None
            except:
                pass

        elif error.code == ErrorCode.BND_MAXIMUM and error.expected_value:
            # Use maximum bound
            try:
                bounds = eval(error.expected_value)
                fallback_value = bounds[1] if isinstance(bounds, (list, tuple)) else None
            except:
                pass

        if fallback_value is not None:
            try:
                if hasattr(self.state, 'set'):
                    self.state.set(error.path, fallback_value)
                elif hasattr(self.state, 'write'):
                    self.state.write(error.path, fallback_value)

                return RecoveryResult(
                    success=True,
                    strategy_used=RecoveryStrategy.FALLBACK,
                    message=f"Applied fallback value: {fallback_value}",
                    modifications=[{"path": error.path, "value": fallback_value}],
                )
            except Exception as e:
                return RecoveryResult(
                    success=False,
                    message=f"Fallback failed: {e}",
                )

        return RecoveryResult(success=False, message="No fallback value available")

    def _execute_revert(
        self,
        error: MAGNETError,
        option: RecoveryOption,
    ) -> RecoveryResult:
        """Execute revert strategy."""
        # v1.1: Handle transaction rollback
        if error.code == ErrorCode.STA_TRANSACTION and error.transaction_id:
            if self.state and hasattr(self.state, 'rollback_tentative'):
                try:
                    self.state.rollback_tentative()
                    return RecoveryResult(
                        success=True,
                        strategy_used=RecoveryStrategy.REVERT,
                        message=f"Rolled back transaction {error.transaction_id}",
                    )
                except Exception as e:
                    return RecoveryResult(
                        success=False,
                        message=f"Transaction rollback failed: {e}",
                    )

        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.REVERT,
            message="Revert requires version control or transaction",
            requires_escalation=True,
        )
