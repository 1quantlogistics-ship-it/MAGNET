"""
glue/explanation/trace.py - Trace collector for design changes

ALPHA OWNS THIS FILE.

Module 42: Explanation Engine
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timezone
import copy

from .schemas import ParameterDiff, ValidatorSummary
from ..utils import safe_get, serialize_state

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


@dataclass
class TraceEntry:
    """Single trace entry."""

    timestamp: datetime
    event_type: str  # "change", "validation", "decision"
    source: str
    data: Dict[str, Any]


class TraceCollector:
    """
    Collects traces of design changes and validation events.

    Used to build explanations of what happened during a design cycle.
    """

    def __init__(self, state: Optional["StateManager"] = None):
        """
        Initialize trace collector.

        Args:
            state: Optional StateManager to track
        """
        self.state = state
        self._entries: List[TraceEntry] = []
        self._before_snapshot: Dict[str, Any] = {}
        self._tracked_paths: List[str] = []

    def begin_trace(self, paths: Optional[List[str]] = None) -> None:
        """
        Begin tracing changes.

        Args:
            paths: Specific paths to track (None = all changes)
        """
        self._entries = []
        self._tracked_paths = paths or []

        if self.state:
            self._before_snapshot = serialize_state(self.state)

    def record_change(
        self,
        path: str,
        old_value: Any,
        new_value: Any,
        source: str = "",
    ) -> None:
        """
        Record a parameter change.

        Args:
            path: Parameter path
            old_value: Previous value
            new_value: New value
            source: Source of change
        """
        if self._tracked_paths and path not in self._tracked_paths:
            return

        self._entries.append(TraceEntry(
            timestamp=datetime.now(timezone.utc),
            event_type="change",
            source=source,
            data={
                "path": path,
                "old_value": old_value,
                "new_value": new_value,
            },
        ))

    def record_validation(
        self,
        validator_name: str,
        passed: bool,
        errors: int = 0,
        warnings: int = 0,
        message: str = "",
    ) -> None:
        """
        Record a validation result.

        Args:
            validator_name: Name of validator
            passed: Whether validation passed
            errors: Error count
            warnings: Warning count
            message: Summary message
        """
        self._entries.append(TraceEntry(
            timestamp=datetime.now(timezone.utc),
            event_type="validation",
            source=validator_name,
            data={
                "passed": passed,
                "errors": errors,
                "warnings": warnings,
                "message": message,
            },
        ))

    def record_decision(
        self,
        agent_id: str,
        decision: str,
        reasoning: str = "",
    ) -> None:
        """
        Record an agent decision.

        Args:
            agent_id: ID of deciding agent
            decision: Decision made
            reasoning: Reasoning for decision
        """
        self._entries.append(TraceEntry(
            timestamp=datetime.now(timezone.utc),
            event_type="decision",
            source=agent_id,
            data={
                "decision": decision,
                "reasoning": reasoning,
            },
        ))

    def get_diffs(self) -> List[ParameterDiff]:
        """
        Get parameter diffs from trace.

        Returns:
            List of ParameterDiff objects
        """
        diffs = []
        seen_paths = set()

        for entry in self._entries:
            if entry.event_type == "change":
                path = entry.data["path"]
                if path in seen_paths:
                    continue
                seen_paths.add(path)

                old_val = entry.data["old_value"]
                new_val = entry.data["new_value"]

                # Calculate change percent
                change_pct = None
                try:
                    old_f = float(old_val)
                    new_f = float(new_val)
                    if old_f != 0:
                        change_pct = ((new_f - old_f) / abs(old_f)) * 100
                except (TypeError, ValueError):
                    pass

                # Determine significance
                if change_pct is not None:
                    if abs(change_pct) > 20:
                        significance = "major"
                    elif abs(change_pct) > 5:
                        significance = "moderate"
                    else:
                        significance = "minor"
                else:
                    significance = "moderate" if old_val != new_val else "minor"

                # Extract name from path
                name = path.split(".")[-1].replace("_", " ").title()

                diffs.append(ParameterDiff(
                    path=path,
                    name=name,
                    old_value=old_val,
                    new_value=new_val,
                    change_percent=change_pct,
                    significance=significance,
                    category=path.split(".")[0] if "." in path else "",
                ))

        return diffs

    def get_validation_summaries(self) -> List[ValidatorSummary]:
        """
        Get validation summaries from trace.

        Returns:
            List of ValidatorSummary objects
        """
        summaries = []
        seen_validators = set()

        for entry in self._entries:
            if entry.event_type == "validation":
                validator_name = entry.source
                if validator_name in seen_validators:
                    continue
                seen_validators.add(validator_name)

                summaries.append(ValidatorSummary(
                    validator_name=validator_name,
                    passed=entry.data.get("passed", True),
                    error_count=entry.data.get("errors", 0),
                    warning_count=entry.data.get("warnings", 0),
                    key_message=entry.data.get("message", ""),
                ))

        return summaries

    def get_entries(self) -> List[TraceEntry]:
        """Get all trace entries."""
        return self._entries.copy()

    def get_changes_by_category(self) -> Dict[str, List[ParameterDiff]]:
        """Group diffs by category."""
        diffs = self.get_diffs()
        by_category: Dict[str, List[ParameterDiff]] = {}

        for diff in diffs:
            category = diff.category or "other"
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(diff)

        return by_category

    def clear(self) -> None:
        """Clear all trace entries."""
        self._entries = []
        self._before_snapshot = {}
