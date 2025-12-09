"""
ui/validation_panel.py - Validation display components v1.1
BRAVO OWNS THIS FILE.

Section 54: UI Components
Provides validation result display and error/warning management.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from enum import Enum
import logging

from .utils import get_state_value, get_phase_status

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger("ui.validation_panel")


class ValidationSeverity(Enum):
    """Severity level for validation messages."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(Enum):
    """Category of validation check."""
    STRUCTURAL = "structural"
    STABILITY = "stability"
    REGULATORY = "regulatory"
    PERFORMANCE = "performance"
    WEIGHT = "weight"
    SYSTEMS = "systems"
    GENERAL = "general"


@dataclass
class ValidationMessage:
    """Single validation message."""
    message_id: str = ""
    severity: ValidationSeverity = ValidationSeverity.INFO
    category: ValidationCategory = ValidationCategory.GENERAL
    code: str = ""
    message: str = ""
    details: str = ""
    source: str = ""
    phase: str = ""
    path: str = ""
    expected: Any = None
    actual: Any = None
    rule_ref: str = ""
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "severity": self.severity.value,
            "category": self.category.value,
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "source": self.source,
            "phase": self.phase,
            "path": self.path,
            "rule_ref": self.rule_ref,
            "suggestion": self.suggestion,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationMessage":
        """Create message from dictionary."""
        severity = data.get("severity", "info")
        if isinstance(severity, str):
            try:
                severity = ValidationSeverity(severity)
            except ValueError:
                severity = ValidationSeverity.INFO

        category = data.get("category", "general")
        if isinstance(category, str):
            try:
                category = ValidationCategory(category)
            except ValueError:
                category = ValidationCategory.GENERAL

        return cls(
            message_id=data.get("message_id", data.get("id", "")),
            severity=severity,
            category=category,
            code=data.get("code", data.get("check_id", "")),
            message=data.get("message", data.get("description", "")),
            details=data.get("details", ""),
            source=data.get("source", data.get("validator", "")),
            phase=data.get("phase", ""),
            path=data.get("path", data.get("field", "")),
            expected=data.get("expected"),
            actual=data.get("actual"),
            rule_ref=data.get("rule_ref", data.get("rule", "")),
            suggestion=data.get("suggestion", data.get("fix", "")),
        )


@dataclass
class ValidationSummary:
    """Summary of validation results."""
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    critical_count: int = 0
    overall_passed: bool = True
    phase: str = ""
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "critical_count": self.critical_count,
            "overall_passed": self.overall_passed,
            "phase": self.phase,
        }


@dataclass
class ValidationResult:
    """Complete validation result with messages and summary."""
    summary: ValidationSummary = field(default_factory=ValidationSummary)
    messages: List[ValidationMessage] = field(default_factory=list)
    by_category: Dict[str, List[ValidationMessage]] = field(default_factory=dict)
    by_severity: Dict[str, List[ValidationMessage]] = field(default_factory=dict)

    def add_message(self, message: ValidationMessage) -> None:
        """Add a validation message."""
        self.messages.append(message)

        # Update by_category
        cat = message.category.value
        if cat not in self.by_category:
            self.by_category[cat] = []
        self.by_category[cat].append(message)

        # Update by_severity
        sev = message.severity.value
        if sev not in self.by_severity:
            self.by_severity[sev] = []
        self.by_severity[sev].append(message)

        # Update summary counts
        if message.severity == ValidationSeverity.ERROR:
            self.summary.error_count += 1
            self.summary.overall_passed = False
        elif message.severity == ValidationSeverity.WARNING:
            self.summary.warning_count += 1
        elif message.severity == ValidationSeverity.INFO:
            self.summary.info_count += 1
        elif message.severity == ValidationSeverity.CRITICAL:
            self.summary.critical_count += 1
            self.summary.overall_passed = False

    def get_errors(self) -> List[ValidationMessage]:
        """Get all error messages."""
        return self.by_severity.get("error", [])

    def get_warnings(self) -> List[ValidationMessage]:
        """Get all warning messages."""
        return self.by_severity.get("warning", [])

    def get_by_category(self, category: str) -> List[ValidationMessage]:
        """Get messages by category."""
        return self.by_category.get(category, [])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary.to_dict(),
            "messages": [m.to_dict() for m in self.messages],
            "error_count": self.summary.error_count,
            "warning_count": self.summary.warning_count,
            "overall_passed": self.summary.overall_passed,
        }


class ValidationPanel:
    """
    Validation panel for displaying validation results.

    v1.1: Uses get_state_value for state access with aliases.
    """

    def __init__(self, state: "StateManager"):
        self.state = state
        self._result: Optional[ValidationResult] = None

    def load_from_state(self) -> ValidationResult:
        """Load validation results from state."""
        result = ValidationResult()

        # v1.1: Use aliased paths
        errors = get_state_value(self.state, "compliance.errors", [])
        warnings = get_state_value(self.state, "compliance.warnings", [])
        checks = get_state_value(self.state, "compliance.checks", [])

        # Process errors
        if isinstance(errors, list):
            for i, err in enumerate(errors):
                if isinstance(err, dict):
                    msg = ValidationMessage.from_dict(err)
                    msg.severity = ValidationSeverity.ERROR
                    if not msg.message_id:
                        msg.message_id = f"err_{i}"
                    result.add_message(msg)
                elif isinstance(err, str):
                    result.add_message(ValidationMessage(
                        message_id=f"err_{i}",
                        severity=ValidationSeverity.ERROR,
                        message=err,
                    ))

        # Process warnings
        if isinstance(warnings, list):
            for i, warn in enumerate(warnings):
                if isinstance(warn, dict):
                    msg = ValidationMessage.from_dict(warn)
                    msg.severity = ValidationSeverity.WARNING
                    if not msg.message_id:
                        msg.message_id = f"warn_{i}"
                    result.add_message(msg)
                elif isinstance(warn, str):
                    result.add_message(ValidationMessage(
                        message_id=f"warn_{i}",
                        severity=ValidationSeverity.WARNING,
                        message=warn,
                    ))

        # Process check results
        if isinstance(checks, list):
            result.summary.total_checks = len(checks)
            for check in checks:
                if isinstance(check, dict):
                    passed = check.get("passed", check.get("status") == "passed")
                    if passed:
                        result.summary.passed_checks += 1
                    else:
                        result.summary.failed_checks += 1

        # Overall status
        overall = get_state_value(self.state, "compliance.overall_passed", None)
        if overall is not None:
            result.summary.overall_passed = bool(overall)

        self._result = result
        return result

    def get_result(self) -> ValidationResult:
        """Get current validation result."""
        if self._result is None:
            return self.load_from_state()
        return self._result

    def render_ascii(self) -> str:
        """Render validation panel as ASCII."""
        result = self.get_result()
        lines = []

        # Header
        status = "\u2713 PASSED" if result.summary.overall_passed else "\u2717 FAILED"
        lines.append(f"Validation Status: {status}")
        lines.append("=" * 50)

        # Summary
        lines.append(f"Checks: {result.summary.passed_checks}/{result.summary.total_checks} passed")
        lines.append(f"Errors: {result.summary.error_count}")
        lines.append(f"Warnings: {result.summary.warning_count}")
        lines.append("")

        # Errors
        if result.summary.error_count > 0:
            lines.append("ERRORS:")
            lines.append("-" * 30)
            for msg in result.get_errors()[:10]:
                lines.append(f"  \u2717 [{msg.code}] {msg.message}")
                if msg.details:
                    lines.append(f"    {msg.details}")
                if msg.suggestion:
                    lines.append(f"    Fix: {msg.suggestion}")
            if result.summary.error_count > 10:
                lines.append(f"  ... and {result.summary.error_count - 10} more errors")
            lines.append("")

        # Warnings
        if result.summary.warning_count > 0:
            lines.append("WARNINGS:")
            lines.append("-" * 30)
            for msg in result.get_warnings()[:5]:
                lines.append(f"  \u26a0 [{msg.code}] {msg.message}")
            if result.summary.warning_count > 5:
                lines.append(f"  ... and {result.summary.warning_count - 5} more warnings")

        return "\n".join(lines)

    def render_html(self) -> str:
        """Render validation panel as HTML."""
        result = self.get_result()

        status_class = "passed" if result.summary.overall_passed else "failed"
        status_text = "PASSED" if result.summary.overall_passed else "FAILED"

        html = [
            '<div class="validation-panel">',
            f'  <div class="validation-header {status_class}">',
            f'    <span class="status-icon"></span>',
            f'    <span class="status-text">{status_text}</span>',
            '  </div>',
            '  <div class="validation-summary">',
            f'    <div class="stat">Checks: {result.summary.passed_checks}/{result.summary.total_checks}</div>',
            f'    <div class="stat errors">Errors: {result.summary.error_count}</div>',
            f'    <div class="stat warnings">Warnings: {result.summary.warning_count}</div>',
            '  </div>',
        ]

        # Errors section
        if result.summary.error_count > 0:
            html.append('  <div class="validation-errors">')
            html.append('    <h3>Errors</h3>')
            html.append('    <ul>')
            for msg in result.get_errors():
                html.append(f'      <li class="error-item">')
                html.append(f'        <span class="code">{msg.code}</span>')
                html.append(f'        <span class="message">{msg.message}</span>')
                if msg.suggestion:
                    html.append(f'        <span class="suggestion">Fix: {msg.suggestion}</span>')
                html.append('      </li>')
            html.append('    </ul>')
            html.append('  </div>')

        # Warnings section
        if result.summary.warning_count > 0:
            html.append('  <div class="validation-warnings">')
            html.append('    <h3>Warnings</h3>')
            html.append('    <ul>')
            for msg in result.get_warnings():
                html.append(f'      <li class="warning-item">')
                html.append(f'        <span class="code">{msg.code}</span>')
                html.append(f'        <span class="message">{msg.message}</span>')
                html.append('      </li>')
            html.append('    </ul>')
            html.append('  </div>')

        html.append('</div>')
        return "\n".join(html)

    def render_json(self) -> Dict[str, Any]:
        """Render validation panel as JSON-serializable dict."""
        return self.get_result().to_dict()


class ValidationHistory:
    """Tracks validation history across phases."""

    def __init__(self):
        self._history: List[ValidationResult] = []
        self._by_phase: Dict[str, ValidationResult] = {}

    def record(self, result: ValidationResult, phase: str = "") -> None:
        """Record a validation result."""
        result.summary.phase = phase
        self._history.append(result)
        if phase:
            self._by_phase[phase] = result

    def get_latest(self) -> Optional[ValidationResult]:
        """Get most recent validation result."""
        return self._history[-1] if self._history else None

    def get_for_phase(self, phase: str) -> Optional[ValidationResult]:
        """Get validation result for a phase."""
        return self._by_phase.get(phase)

    def get_trend(self) -> Dict[str, Any]:
        """Get error/warning trend over time."""
        if not self._history:
            return {"entries": [], "improving": True}

        entries = []
        for i, result in enumerate(self._history):
            entries.append({
                "index": i,
                "phase": result.summary.phase,
                "errors": result.summary.error_count,
                "warnings": result.summary.warning_count,
                "passed": result.summary.overall_passed,
            })

        # Determine if improving
        improving = True
        if len(entries) >= 2:
            latest = entries[-1]["errors"]
            previous = entries[-2]["errors"]
            improving = latest <= previous

        return {"entries": entries, "improving": improving}

    def clear(self) -> None:
        """Clear history."""
        self._history.clear()
        self._by_phase.clear()


class CategoryPanel:
    """Panel for displaying validation by category."""

    CATEGORY_ICONS = {
        ValidationCategory.STRUCTURAL: "\u2692",     # ⚒
        ValidationCategory.STABILITY: "\u2696",      # ⚖
        ValidationCategory.REGULATORY: "\u2696",     # ⚖
        ValidationCategory.PERFORMANCE: "\u26a1",    # ⚡
        ValidationCategory.WEIGHT: "\u2696",         # ⚖
        ValidationCategory.SYSTEMS: "\u2699",        # ⚙
        ValidationCategory.GENERAL: "\u2139",        # ℹ
    }

    def __init__(self, result: ValidationResult):
        self.result = result

    def render_ascii(self) -> str:
        """Render category breakdown as ASCII."""
        lines = ["Validation by Category", "=" * 40]

        for category in ValidationCategory:
            messages = self.result.get_by_category(category.value)
            if not messages:
                continue

            icon = self.CATEGORY_ICONS.get(category, "?")
            error_count = sum(1 for m in messages if m.severity == ValidationSeverity.ERROR)
            warn_count = sum(1 for m in messages if m.severity == ValidationSeverity.WARNING)

            status = "\u2713" if error_count == 0 else "\u2717"
            lines.append(f"{icon} {category.value.upper()}: {status}")
            lines.append(f"   Errors: {error_count}, Warnings: {warn_count}")

        return "\n".join(lines)


class ComplianceMatrix:
    """Matrix view of compliance checks by regulation."""

    def __init__(self, state: "StateManager"):
        self.state = state

    def load_matrix(self) -> Dict[str, Any]:
        """Load compliance matrix from state."""
        checks = get_state_value(self.state, "compliance.checks", [])

        matrix = {
            "regulations": {},
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
            }
        }

        if not isinstance(checks, list):
            return matrix

        for check in checks:
            if not isinstance(check, dict):
                continue

            reg = check.get("regulation", check.get("rule_ref", "General"))
            if reg not in matrix["regulations"]:
                matrix["regulations"][reg] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "checks": [],
                }

            reg_data = matrix["regulations"][reg]
            reg_data["total"] += 1
            matrix["summary"]["total"] += 1

            passed = check.get("passed", check.get("status") == "passed")
            if passed:
                reg_data["passed"] += 1
                matrix["summary"]["passed"] += 1
            else:
                reg_data["failed"] += 1
                matrix["summary"]["failed"] += 1

            reg_data["checks"].append({
                "code": check.get("code", check.get("check_id", "")),
                "description": check.get("description", check.get("message", "")),
                "passed": passed,
            })

        return matrix

    def render_ascii(self) -> str:
        """Render compliance matrix as ASCII table."""
        matrix = self.load_matrix()
        lines = ["Compliance Matrix", "=" * 60]

        header = f"{'Regulation':<20} {'Passed':<10} {'Failed':<10} {'Status':<10}"
        lines.append(header)
        lines.append("-" * 60)

        for reg, data in matrix["regulations"].items():
            status = "\u2713" if data["failed"] == 0 else "\u2717"
            line = f"{reg:<20} {data['passed']:<10} {data['failed']:<10} {status:<10}"
            lines.append(line)

        lines.append("-" * 60)
        summary = matrix["summary"]
        lines.append(f"{'TOTAL':<20} {summary['passed']:<10} {summary['failed']:<10}")

        return "\n".join(lines)

    def render_html(self) -> str:
        """Render compliance matrix as HTML table."""
        matrix = self.load_matrix()

        html = [
            '<div class="compliance-matrix">',
            '  <table>',
            '    <thead>',
            '      <tr>',
            '        <th>Regulation</th>',
            '        <th>Passed</th>',
            '        <th>Failed</th>',
            '        <th>Status</th>',
            '      </tr>',
            '    </thead>',
            '    <tbody>',
        ]

        for reg, data in matrix["regulations"].items():
            status_class = "passed" if data["failed"] == 0 else "failed"
            status_icon = "\u2713" if data["failed"] == 0 else "\u2717"
            html.append(f'      <tr class="{status_class}">')
            html.append(f'        <td>{reg}</td>')
            html.append(f'        <td>{data["passed"]}</td>')
            html.append(f'        <td>{data["failed"]}</td>')
            html.append(f'        <td>{status_icon}</td>')
            html.append('      </tr>')

        html.extend([
            '    </tbody>',
            '  </table>',
            '</div>',
        ])

        return "\n".join(html)
