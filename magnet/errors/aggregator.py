"""
errors/aggregator.py - Aggregate and report errors
BRAVO OWNS THIS FILE.

Section 43: Error Taxonomy
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List
from datetime import datetime
import uuid

from .taxonomy import MAGNETError, ErrorCode, ErrorCategory, ErrorSeverity


@dataclass
class ErrorReport:
    """Aggregated error report."""

    report_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Counts
    total_errors: int = 0
    by_severity: Dict[str, int] = field(default_factory=dict)
    by_category: Dict[str, int] = field(default_factory=dict)

    # Critical errors
    critical_errors: List[MAGNETError] = field(default_factory=list)

    # Summary
    summary: str = ""

    # All errors
    all_errors: List[MAGNETError] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "total_errors": self.total_errors,
            "by_severity": self.by_severity,
            "by_category": self.by_category,
            "critical_count": len(self.critical_errors),
            "summary": self.summary,
        }


class ErrorAggregator:
    """
    Aggregates errors from multiple sources.
    """

    def __init__(self):
        self._errors: List[MAGNETError] = []
        self._by_source: Dict[str, List[MAGNETError]] = {}

    def add(self, error: MAGNETError) -> None:
        """Add an error."""
        self._errors.append(error)

        if error.source not in self._by_source:
            self._by_source[error.source] = []
        self._by_source[error.source].append(error)

    def add_all(self, errors: List[MAGNETError]) -> None:
        """Add multiple errors."""
        for error in errors:
            self.add(error)

    def get_by_severity(self, severity: ErrorSeverity) -> List[MAGNETError]:
        """Get errors by severity."""
        return [e for e in self._errors if e.severity == severity]

    def get_by_category(self, category: ErrorCategory) -> List[MAGNETError]:
        """Get errors by category."""
        return [e for e in self._errors if e.category == category]

    def get_by_source(self, source: str) -> List[MAGNETError]:
        """Get errors by source."""
        return self._by_source.get(source, [])

    def has_critical(self) -> bool:
        """Check if any critical errors."""
        return any(e.severity == ErrorSeverity.CRITICAL for e in self._errors)

    def has_errors(self) -> bool:
        """Check if any errors (not just warnings)."""
        return any(
            e.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]
            for e in self._errors
        )

    def generate_report(self) -> ErrorReport:
        """Generate aggregated report."""
        report = ErrorReport(
            report_id=str(uuid.uuid4())[:8],
            total_errors=len(self._errors),
        )

        # Count by severity
        for severity in ErrorSeverity:
            count = sum(1 for e in self._errors if e.severity == severity)
            if count > 0:
                report.by_severity[severity.value] = count

        # Count by category
        for category in ErrorCategory:
            count = sum(1 for e in self._errors if e.category == category)
            if count > 0:
                report.by_category[category.value] = count

        # Critical errors
        report.critical_errors = [
            e for e in self._errors if e.severity == ErrorSeverity.CRITICAL
        ]

        # Generate summary
        if report.critical_errors:
            report.summary = f"{len(report.critical_errors)} critical error(s) require immediate attention"
        elif report.by_severity.get("error", 0) > 0:
            report.summary = f"{report.by_severity['error']} error(s) found"
        elif report.by_severity.get("warning", 0) > 0:
            report.summary = f"{report.by_severity['warning']} warning(s) found"
        else:
            report.summary = "No significant issues"

        report.all_errors = self._errors.copy()

        return report

    def clear(self) -> None:
        """Clear all errors."""
        self._errors.clear()
        self._by_source.clear()
