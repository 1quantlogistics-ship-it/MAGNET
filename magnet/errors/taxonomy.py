"""
errors/taxonomy.py - Error classification system
BRAVO OWNS THIS FILE.

Section 43: Error Taxonomy
v1.1: Removed phy_convergence, added transaction tracking
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import uuid


class ErrorSeverity(Enum):
    """Error severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories."""
    # Validation errors (1xxx)
    VALIDATION = "validation"

    # Constraint errors (2xxx)
    CONSTRAINT = "constraint"

    # Bounds errors (3xxx)
    BOUNDS = "bounds"

    # Physics errors (4xxx)
    PHYSICS = "physics"

    # Numerical errors (4xxx)
    NUMERICAL = "numerical"

    # State errors (5xxx)
    STATE = "state"

    # Dependency errors (5xxx)
    DEPENDENCY = "dependency"

    # Phase errors (5xxx)
    PHASE = "phase"

    # Configuration errors (6xxx)
    CONFIGURATION = "configuration"

    # Resource errors (6xxx)
    RESOURCE = "resource"

    # Timeout errors (6xxx)
    TIMEOUT = "timeout"

    # Agent errors (7xxx)
    AGENT = "agent"

    # Protocol errors (7xxx)
    PROTOCOL = "protocol"

    # Escalation errors (7xxx)
    ESCALATION = "escalation"


class ErrorCode(Enum):
    """Specific error codes."""

    # Validation (1xxx)
    VAL_FAILED = 1001
    VAL_SCHEMA = 1002
    VAL_MISSING_FIELD = 1003
    VAL_TYPE_MISMATCH = 1004

    # Constraint (2xxx)
    CON_VIOLATED = 2001
    CON_CONFLICTING = 2002
    CON_UNSATISFIABLE = 2003

    # Bounds (3xxx)
    BND_EXCEEDED = 3001
    BND_MINIMUM = 3002
    BND_MAXIMUM = 3003

    # Physics (4xxx)
    PHY_IMPOSSIBLE = 4001
    PHY_UNSTABLE = 4002
    PHY_NEGATIVE_MASS = 4003
    PHY_NUMERICAL = 4004
    # v1.1: Removed PHY_CONVERGENCE (4005) - no convergence validator yet

    # State (5xxx)
    STA_INCONSISTENT = 5001
    STA_MISSING_DEP = 5002
    STA_CIRCULAR_DEP = 5003
    STA_PHASE_MISMATCH = 5004
    STA_TRANSACTION = 5005  # v1.1: Added for transaction errors

    # System (6xxx)
    SYS_CONFIG = 6001
    SYS_RESOURCE = 6002
    SYS_TIMEOUT = 6003
    SYS_EXTERNAL = 6004

    # Agent (7xxx)
    AGT_FAILED = 7001
    AGT_TIMEOUT = 7002
    AGT_CONFLICT = 7003
    AGT_PROTOCOL = 7004
    AGT_ESCALATION = 7005


@dataclass
class MAGNETError:
    """Structured error representation."""

    error_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    code: ErrorCode = ErrorCode.VAL_FAILED
    category: ErrorCategory = ErrorCategory.VALIDATION
    severity: ErrorSeverity = ErrorSeverity.ERROR

    message: str = ""
    detail: str = ""

    # Context
    source: str = ""  # Module/validator that raised
    path: Optional[str] = None  # State path if applicable

    # Values
    actual_value: Any = None
    expected_value: Any = None

    # Recovery
    recoverable: bool = True
    recovery_options: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)

    # v1.1: Transaction context
    transaction_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "code": self.code.value,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "source": self.source,
            "path": self.path,
            "recoverable": self.recoverable,
            "transaction_id": self.transaction_id,
        }


def create_validation_error(
    message: str,
    source: str,
    path: str = None,
    actual: Any = None,
    expected: Any = None,
    transaction_id: str = None,  # v1.1
) -> MAGNETError:
    """Factory for validation errors."""
    return MAGNETError(
        code=ErrorCode.VAL_FAILED,
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.ERROR,
        message=message,
        source=source,
        path=path,
        actual_value=actual,
        expected_value=expected,
        transaction_id=transaction_id,
    )


def create_bounds_error(
    message: str,
    source: str,
    path: str,
    actual: Any,
    min_val: Any = None,
    max_val: Any = None,
    transaction_id: str = None,  # v1.1
) -> MAGNETError:
    """Factory for bounds errors."""
    code = ErrorCode.BND_MINIMUM if min_val and actual < min_val else ErrorCode.BND_MAXIMUM

    return MAGNETError(
        code=code,
        category=ErrorCategory.BOUNDS,
        severity=ErrorSeverity.ERROR,
        message=message,
        source=source,
        path=path,
        actual_value=actual,
        expected_value=f"[{min_val}, {max_val}]",
        recovery_options=["adjust_value", "expand_bounds"],
        transaction_id=transaction_id,
    )


def create_physics_error(
    message: str,
    source: str,
    path: str = None,
    transaction_id: str = None,  # v1.1
) -> MAGNETError:
    """Factory for physics errors."""
    return MAGNETError(
        code=ErrorCode.PHY_IMPOSSIBLE,
        category=ErrorCategory.PHYSICS,
        severity=ErrorSeverity.CRITICAL,
        message=message,
        source=source,
        path=path,
        recoverable=False,
        transaction_id=transaction_id,
    )


# v1.1: Transaction error factory
def create_transaction_error(
    message: str,
    transaction_id: str,
    source: str = "transaction_manager",
) -> MAGNETError:
    """Factory for transaction errors."""
    return MAGNETError(
        code=ErrorCode.STA_TRANSACTION,
        category=ErrorCategory.STATE,
        severity=ErrorSeverity.ERROR,
        message=message,
        source=source,
        transaction_id=transaction_id,
        recovery_options=["rollback", "retry"],
    )
