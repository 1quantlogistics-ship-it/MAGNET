"""
explain/schemas.py - Schemas for explanation generation
BRAVO OWNS THIS FILE.

Section 42: Explanation Engine
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime


class ExplanationLevel(Enum):
    """Level of detail for explanations."""
    SUMMARY = "summary"      # One-liner
    STANDARD = "standard"    # Paragraph
    DETAILED = "detailed"    # Multiple paragraphs
    EXPERT = "expert"        # Full technical trace


@dataclass
class ParameterDiff:
    """Difference in a single parameter."""

    path: str = ""
    name: str = ""  # Human-readable name

    old_value: Any = None
    new_value: Any = None

    unit: str = ""
    change_percent: Optional[float] = None

    significance: str = "normal"  # minor, normal, major, critical

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "unit": self.unit,
            "change_percent": self.change_percent,
            "significance": self.significance,
        }


@dataclass
class ValidatorSummary:
    """Summary of a validator's results."""

    validator_name: str = "unknown"  # v1.1: Default value
    validator_id: str = ""

    passed: bool = True

    error_count: int = 0
    warning_count: int = 0

    key_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validator": self.validator_name or self.validator_id or "unknown",
            "passed": self.passed,
            "errors": self.error_count,
            "warnings": self.warning_count,
            "message": self.key_message,
        }


@dataclass
class Warning:
    """Warning to display to user."""

    severity: str = "warning"  # info, warning, error, critical
    category: str = ""
    message: str = ""

    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass
class Explanation:
    """Complete explanation of a design change or validation."""

    explanation_id: str = ""
    level: ExplanationLevel = ExplanationLevel.STANDARD

    created_at: datetime = field(default_factory=datetime.utcnow)

    # Content
    summary: str = ""
    narrative: str = ""

    # Components
    parameter_diffs: List[ParameterDiff] = field(default_factory=list)
    validator_summaries: List[ValidatorSummary] = field(default_factory=list)
    warnings: List[Warning] = field(default_factory=list)

    # Expert level
    calculation_trace: Optional[Dict] = None

    # Navigation
    next_steps: List[str] = field(default_factory=list)
    related_topics: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "explanation_id": self.explanation_id,
            "level": self.level.value,
            "summary": self.summary,
            "narrative": self.narrative,
            "parameter_diffs": [d.to_dict() for d in self.parameter_diffs],
            "validator_summaries": [v.to_dict() for v in self.validator_summaries],
            "warnings": [w.to_dict() for w in self.warnings],
            "next_steps": self.next_steps,
        }
