"""
glue/errors/ - Error Taxonomy & Recovery (Module 43)

ALPHA OWNS THIS FILE.

Provides structured error handling and recovery strategies.
"""

from .taxonomy import (
    ErrorCategory,
    ErrorSeverity,
    MAGNETError,
    ErrorContext,
    ERROR_CATALOG,
)

from .recovery import (
    RecoveryStrategy,
    RecoveryResult,
    ErrorHandler,
)


__all__ = [
    # Taxonomy
    "ErrorCategory",
    "ErrorSeverity",
    "MAGNETError",
    "ErrorContext",
    "ERROR_CATALOG",
    # Recovery
    "RecoveryStrategy",
    "RecoveryResult",
    "ErrorHandler",
]
