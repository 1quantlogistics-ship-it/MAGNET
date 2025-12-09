"""
errors/ - Error Taxonomy & Recovery
BRAVO OWNS THIS FILE.

Section 43: Error Taxonomy

This module provides structured error classification and
automatic recovery strategies.
"""

from .taxonomy import (
    ErrorSeverity,
    ErrorCategory,
    ErrorCode,
    MAGNETError,
    create_validation_error,
    create_bounds_error,
    create_physics_error,
    create_transaction_error,
)

from .recovery import (
    RecoveryStrategy,
    RecoveryOption,
    RecoveryResult,
    RecoveryExecutor,
    RECOVERY_STRATEGIES,
)

from .aggregator import (
    ErrorReport,
    ErrorAggregator,
)

__all__ = [
    # Taxonomy
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorCode",
    "MAGNETError",
    "create_validation_error",
    "create_bounds_error",
    "create_physics_error",
    "create_transaction_error",
    # Recovery
    "RecoveryStrategy",
    "RecoveryOption",
    "RecoveryResult",
    "RecoveryExecutor",
    "RECOVERY_STRATEGIES",
    # Aggregator
    "ErrorReport",
    "ErrorAggregator",
]
