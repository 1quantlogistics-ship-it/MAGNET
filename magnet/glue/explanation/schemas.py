"""
glue/explanation/schemas.py - Explanation data structures

ALPHA OWNS THIS FILE.

Module 42: Explanation Engine
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import uuid


@dataclass
class ParameterDiff:
    """Difference in a single parameter."""

    path: str = ""
    name: str = ""
    old_value: Any = None
    new_value: Any = None
    unit: str = ""

    change_percent: Optional[float] = None
    significance: str = "minor"  # minor, moderate, major
    category: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "unit": self.unit,
            "change_percent": self.change_percent,
            "significance": self.significance,
            "category": self.category,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParameterDiff":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def is_increase(self) -> bool:
        """Check if value increased."""
        try:
            return float(self.new_value) > float(self.old_value)
        except (TypeError, ValueError):
            return False

    @property
    def is_decrease(self) -> bool:
        """Check if value decreased."""
        try:
            return float(self.new_value) < float(self.old_value)
        except (TypeError, ValueError):
            return False


@dataclass
class ValidatorSummary:
    """Summary of a validator's results for explanation."""

    validator_name: str = "unknown"  # v1.1: Made optional with default
    validator_id: str = ""
    passed: bool = True

    error_count: int = 0
    warning_count: int = 0

    key_message: str = ""
    details: List[str] = field(default_factory=list)

    affected_parameters: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validator_name": self.validator_name,
            "validator_id": self.validator_id,
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "key_message": self.key_message,
            "details": self.details,
            "affected_parameters": self.affected_parameters,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidatorSummary":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class DesignExplanation:
    """Complete explanation of design changes."""

    explanation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    # Change summary
    summary: str = ""
    narrative: str = ""

    # Parameter changes
    diffs: List[ParameterDiff] = field(default_factory=list)

    # Validation results
    validation_summaries: List[ValidatorSummary] = field(default_factory=list)
    overall_valid: bool = True

    # Context
    phase: str = ""
    iteration: int = 0
    agent_id: str = ""
    proposal_id: str = ""

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "explanation_id": self.explanation_id,
            "summary": self.summary,
            "narrative": self.narrative,
            "diffs": [d.to_dict() for d in self.diffs],
            "validation_summaries": [v.to_dict() for v in self.validation_summaries],
            "overall_valid": self.overall_valid,
            "phase": self.phase,
            "iteration": self.iteration,
            "agent_id": self.agent_id,
            "proposal_id": self.proposal_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DesignExplanation":
        diffs = [ParameterDiff.from_dict(d) for d in data.get("diffs", [])]
        summaries = [ValidatorSummary.from_dict(v) for v in data.get("validation_summaries", [])]
        return cls(
            explanation_id=data.get("explanation_id", ""),
            summary=data.get("summary", ""),
            narrative=data.get("narrative", ""),
            diffs=diffs,
            validation_summaries=summaries,
            overall_valid=data.get("overall_valid", True),
            phase=data.get("phase", ""),
            iteration=data.get("iteration", 0),
            agent_id=data.get("agent_id", ""),
            proposal_id=data.get("proposal_id", ""),
        )

    @property
    def total_changes(self) -> int:
        """Total number of parameter changes."""
        return len(self.diffs)

    @property
    def major_changes(self) -> List[ParameterDiff]:
        """Get only major significance changes."""
        return [d for d in self.diffs if d.significance == "major"]

    @property
    def total_errors(self) -> int:
        """Total validation errors."""
        return sum(v.error_count for v in self.validation_summaries)

    @property
    def total_warnings(self) -> int:
        """Total validation warnings."""
        return sum(v.warning_count for v in self.validation_summaries)
