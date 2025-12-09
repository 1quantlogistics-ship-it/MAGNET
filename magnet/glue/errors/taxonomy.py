"""
glue/errors/taxonomy.py - Error taxonomy and categorization

ALPHA OWNS THIS FILE.

Module 43: Error Taxonomy & Recovery - v1.1
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime, timezone
import traceback
import uuid


class ErrorCategory(Enum):
    """Categories of errors in MAGNET."""
    VALIDATION = "validation"      # Validation rule failures
    PHYSICS = "physics"            # Physical constraint violations
    STATE = "state"                # State management errors
    INTEGRATION = "integration"    # Cross-module integration errors
    CONFIGURATION = "config"       # Configuration errors
    DATA = "data"                  # Data quality/format errors
    SYSTEM = "system"              # System/runtime errors
    AGENT = "agent"                # Agent communication errors


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    DEBUG = "debug"        # Diagnostic information
    INFO = "info"          # Informational
    WARNING = "warning"    # Non-blocking issue
    ERROR = "error"        # Blocking issue, recoverable
    CRITICAL = "critical"  # Blocking issue, may need intervention
    FATAL = "fatal"        # Unrecoverable, abort required


@dataclass
class ErrorContext:
    """Context information for an error."""

    # Location
    module: str = ""
    function: str = ""
    line: int = 0

    # State
    phase: str = ""
    validator_id: str = ""
    agent_id: str = ""
    proposal_id: str = ""

    # Parameters involved
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Stack trace
    stack_trace: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module": self.module,
            "function": self.function,
            "line": self.line,
            "phase": self.phase,
            "validator_id": self.validator_id,
            "agent_id": self.agent_id,
            "proposal_id": self.proposal_id,
            "parameters": self.parameters,
        }

    @classmethod
    def capture(cls, **kwargs) -> "ErrorContext":
        """Capture current context including stack trace."""
        ctx = cls(**kwargs)
        ctx.stack_trace = traceback.format_exc()
        return ctx


@dataclass
class MAGNETError:
    """Structured error in MAGNET system."""

    error_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    code: str = ""
    message: str = ""

    category: ErrorCategory = ErrorCategory.SYSTEM
    severity: ErrorSeverity = ErrorSeverity.ERROR

    context: ErrorContext = field(default_factory=ErrorContext)

    # Recovery hints
    suggestion: str = ""
    recoverable: bool = True

    # Related errors
    related_errors: List[str] = field(default_factory=list)
    caused_by: Optional[str] = None

    # Timestamps
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "code": self.code,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": self.context.to_dict(),
            "suggestion": self.suggestion,
            "recoverable": self.recoverable,
            "related_errors": self.related_errors,
            "caused_by": self.caused_by,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MAGNETError":
        return cls(
            error_id=data.get("error_id", ""),
            code=data.get("code", ""),
            message=data.get("message", ""),
            category=ErrorCategory(data.get("category", "system")),
            severity=ErrorSeverity(data.get("severity", "error")),
            suggestion=data.get("suggestion", ""),
            recoverable=data.get("recoverable", True),
            related_errors=data.get("related_errors", []),
            caused_by=data.get("caused_by"),
        )

    @classmethod
    def from_exception(
        cls,
        exc: Exception,
        code: str = "",
        category: ErrorCategory = ErrorCategory.SYSTEM,
        **context_kwargs,
    ) -> "MAGNETError":
        """Create error from Python exception."""
        return cls(
            code=code or exc.__class__.__name__,
            message=str(exc),
            category=category,
            severity=ErrorSeverity.ERROR,
            context=ErrorContext.capture(**context_kwargs),
            recoverable=True,
        )

    def is_blocking(self) -> bool:
        """Check if error blocks progress."""
        return self.severity in (ErrorSeverity.ERROR, ErrorSeverity.CRITICAL, ErrorSeverity.FATAL)


# Error catalog with standard codes
ERROR_CATALOG: Dict[str, Dict[str, Any]] = {
    # Validation errors (VAL-xxx)
    "VAL-001": {
        "message": "Required parameter missing",
        "category": ErrorCategory.VALIDATION,
        "severity": ErrorSeverity.ERROR,
        "suggestion": "Provide the required parameter value",
    },
    "VAL-002": {
        "message": "Parameter out of valid range",
        "category": ErrorCategory.VALIDATION,
        "severity": ErrorSeverity.ERROR,
        "suggestion": "Adjust parameter to fall within valid range",
    },
    "VAL-003": {
        "message": "Parameter type mismatch",
        "category": ErrorCategory.VALIDATION,
        "severity": ErrorSeverity.ERROR,
        "suggestion": "Provide parameter with correct type",
    },
    "VAL-004": {
        "message": "Constraint violation",
        "category": ErrorCategory.VALIDATION,
        "severity": ErrorSeverity.WARNING,
        "suggestion": "Review and adjust conflicting parameters",
    },

    # Physics errors (PHY-xxx)
    "PHY-001": {
        "message": "Physical constraint violated",
        "category": ErrorCategory.PHYSICS,
        "severity": ErrorSeverity.ERROR,
        "suggestion": "Adjust parameters to satisfy physical constraints",
    },
    "PHY-002": {
        "message": "Stability criterion not met",
        "category": ErrorCategory.PHYSICS,
        "severity": ErrorSeverity.ERROR,
        "suggestion": "Improve stability by adjusting weight distribution",
    },
    "PHY-003": {
        "message": "Displacement mismatch",
        "category": ErrorCategory.PHYSICS,
        "severity": ErrorSeverity.WARNING,
        "suggestion": "Review weight estimates against hull displacement",
    },

    # State errors (STA-xxx)
    "STA-001": {
        "message": "State not initialized",
        "category": ErrorCategory.STATE,
        "severity": ErrorSeverity.ERROR,
        "suggestion": "Initialize state before operations",
    },
    "STA-002": {
        "message": "Transaction conflict",
        "category": ErrorCategory.STATE,
        "severity": ErrorSeverity.ERROR,
        "suggestion": "Retry operation after current transaction completes",
    },
    "STA-003": {
        "message": "Circular dependency detected",
        "category": ErrorCategory.STATE,
        "severity": ErrorSeverity.CRITICAL,
        "suggestion": "Review parameter dependencies",
    },

    # Integration errors (INT-xxx)
    "INT-001": {
        "message": "Module dependency not satisfied",
        "category": ErrorCategory.INTEGRATION,
        "severity": ErrorSeverity.ERROR,
        "suggestion": "Run prerequisite validators first",
    },
    "INT-002": {
        "message": "Cross-module data inconsistency",
        "category": ErrorCategory.INTEGRATION,
        "severity": ErrorSeverity.WARNING,
        "suggestion": "Re-run validation pipeline from affected module",
    },

    # Agent errors (AGT-xxx)
    "AGT-001": {
        "message": "Agent communication timeout",
        "category": ErrorCategory.AGENT,
        "severity": ErrorSeverity.ERROR,
        "suggestion": "Retry operation or check agent status",
    },
    "AGT-002": {
        "message": "Invalid proposal format",
        "category": ErrorCategory.AGENT,
        "severity": ErrorSeverity.ERROR,
        "suggestion": "Ensure proposal follows required schema",
    },
}


def create_error(code: str, **kwargs) -> MAGNETError:
    """Create error from catalog code."""
    if code in ERROR_CATALOG:
        template = ERROR_CATALOG[code]
        return MAGNETError(
            code=code,
            message=kwargs.get("message", template["message"]),
            category=template["category"],
            severity=template["severity"],
            suggestion=kwargs.get("suggestion", template["suggestion"]),
            context=ErrorContext(**kwargs.get("context", {})),
        )
    else:
        return MAGNETError(
            code=code,
            message=kwargs.get("message", f"Unknown error: {code}"),
            **kwargs,
        )
