"""
glue/errors/recovery.py - Error recovery strategies

ALPHA OWNS THIS FILE.

Module 43: Error Taxonomy & Recovery
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from enum import Enum
from datetime import datetime, timezone
import logging

from .taxonomy import MAGNETError, ErrorCategory, ErrorSeverity

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Strategies for error recovery."""
    RETRY = "retry"              # Retry the operation
    SKIP = "skip"                # Skip and continue
    ROLLBACK = "rollback"        # Rollback to previous state
    DEFAULT = "default"          # Use default value
    ESCALATE = "escalate"        # Escalate to user/agent
    ABORT = "abort"              # Abort the operation


@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""

    success: bool = False
    strategy_used: RecoveryStrategy = RecoveryStrategy.ABORT

    message: str = ""
    recovered_value: Any = None

    # If recovery changed state
    state_modified: bool = False
    modifications: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "strategy": self.strategy_used.value,
            "message": self.message,
            "state_modified": self.state_modified,
            "modifications": self.modifications,
        }


# Type for recovery handler callbacks
RecoveryCallback = Callable[[MAGNETError, Optional["StateManager"]], RecoveryResult]


class ErrorHandler:
    """
    Handles errors and attempts recovery.

    Provides a registry of recovery strategies by error code/category.
    """

    def __init__(self, state: Optional["StateManager"] = None):
        """
        Initialize error handler.

        Args:
            state: Optional StateManager for state-modifying recoveries
        """
        self.state = state
        self._handlers: Dict[str, RecoveryCallback] = {}
        self._category_handlers: Dict[ErrorCategory, RecoveryCallback] = {}
        self._default_handler: Optional[RecoveryCallback] = None
        self._error_log: List[MAGNETError] = []

    def register_handler(
        self,
        handler: RecoveryCallback,
        code: Optional[str] = None,
        category: Optional[ErrorCategory] = None,
    ) -> None:
        """
        Register a recovery handler.

        Args:
            handler: Recovery callback function
            code: Error code to handle (takes priority)
            category: Error category to handle
        """
        if code:
            self._handlers[code] = handler
        elif category:
            self._category_handlers[category] = handler

    def set_default_handler(self, handler: RecoveryCallback) -> None:
        """Set the default recovery handler."""
        self._default_handler = handler

    def handle(self, error: MAGNETError) -> RecoveryResult:
        """
        Handle an error and attempt recovery.

        Args:
            error: The error to handle

        Returns:
            RecoveryResult with outcome
        """
        self._error_log.append(error)

        logger.debug(f"Handling error {error.code}: {error.message}")

        # Try code-specific handler first
        if error.code in self._handlers:
            try:
                return self._handlers[error.code](error, self.state)
            except Exception as e:
                logger.error(f"Handler for {error.code} failed: {e}")

        # Try category handler
        if error.category in self._category_handlers:
            try:
                return self._category_handlers[error.category](error, self.state)
            except Exception as e:
                logger.error(f"Category handler for {error.category} failed: {e}")

        # Try default handler
        if self._default_handler:
            try:
                return self._default_handler(error, self.state)
            except Exception as e:
                logger.error(f"Default handler failed: {e}")

        # No handler - return failed result
        logger.warning(f"No handler for error {error.code}")
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.ABORT,
            message=f"No recovery handler for error {error.code}",
        )

    def handle_with_strategy(
        self,
        error: MAGNETError,
        strategy: RecoveryStrategy,
        **kwargs,
    ) -> RecoveryResult:
        """
        Handle error with a specific strategy.

        Args:
            error: The error to handle
            strategy: Recovery strategy to use
            **kwargs: Strategy-specific parameters

        Returns:
            RecoveryResult with outcome
        """
        self._error_log.append(error)

        if strategy == RecoveryStrategy.RETRY:
            return self._handle_retry(error, kwargs.get("max_retries", 3))

        elif strategy == RecoveryStrategy.SKIP:
            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.SKIP,
                message=f"Skipped error {error.code}",
            )

        elif strategy == RecoveryStrategy.ROLLBACK:
            return self._handle_rollback(error, kwargs.get("transaction_id"))

        elif strategy == RecoveryStrategy.DEFAULT:
            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.DEFAULT,
                message=f"Using default value for {error.context.parameters}",
                recovered_value=kwargs.get("default_value"),
            )

        elif strategy == RecoveryStrategy.ESCALATE:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.ESCALATE,
                message=f"Escalating error {error.code} for manual resolution",
            )

        else:  # ABORT
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.ABORT,
                message=f"Aborting due to error {error.code}",
            )

    def _handle_retry(self, error: MAGNETError, max_retries: int) -> RecoveryResult:
        """Handle retry strategy."""
        # Note: Actual retry logic would be implemented by caller
        return RecoveryResult(
            success=False,  # Caller implements actual retry
            strategy_used=RecoveryStrategy.RETRY,
            message=f"Retry requested (max {max_retries} attempts)",
        )

    def _handle_rollback(
        self,
        error: MAGNETError,
        transaction_id: Optional[str],
    ) -> RecoveryResult:
        """Handle rollback strategy."""
        if self.state and transaction_id:
            try:
                if hasattr(self.state, 'rollback_transaction'):
                    self.state.rollback_transaction(transaction_id)
                    return RecoveryResult(
                        success=True,
                        strategy_used=RecoveryStrategy.ROLLBACK,
                        message=f"Rolled back transaction {transaction_id}",
                        state_modified=True,
                    )
            except Exception as e:
                logger.error(f"Rollback failed: {e}")

        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.ROLLBACK,
            message="Rollback failed or not available",
        )

    def get_errors(self) -> List[MAGNETError]:
        """Get all logged errors."""
        return self._error_log.copy()

    def get_errors_by_severity(self, severity: ErrorSeverity) -> List[MAGNETError]:
        """Get errors of a specific severity."""
        return [e for e in self._error_log if e.severity == severity]

    def get_blocking_errors(self) -> List[MAGNETError]:
        """Get errors that block progress."""
        return [e for e in self._error_log if e.is_blocking()]

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors."""
        by_category = {}
        for cat in ErrorCategory:
            by_category[cat.value] = len([e for e in self._error_log if e.category == cat])

        by_severity = {}
        for sev in ErrorSeverity:
            by_severity[sev.value] = len([e for e in self._error_log if e.severity == sev])

        return {
            "total": len(self._error_log),
            "blocking": len(self.get_blocking_errors()),
            "by_category": by_category,
            "by_severity": by_severity,
        }

    def clear(self) -> None:
        """Clear error log."""
        self._error_log = []


# Default handlers for common error types

def default_validation_handler(error: MAGNETError, state: Optional["StateManager"]) -> RecoveryResult:
    """Default handler for validation errors."""
    if error.severity == ErrorSeverity.WARNING:
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.SKIP,
            message=f"Validation warning acknowledged: {error.message}",
        )
    return RecoveryResult(
        success=False,
        strategy_used=RecoveryStrategy.ESCALATE,
        message=f"Validation error requires attention: {error.message}",
    )


def default_state_handler(error: MAGNETError, state: Optional["StateManager"]) -> RecoveryResult:
    """Default handler for state errors."""
    return RecoveryResult(
        success=False,
        strategy_used=RecoveryStrategy.ROLLBACK,
        message=f"State error - rollback recommended: {error.message}",
    )
