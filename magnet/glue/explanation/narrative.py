"""
glue/explanation/narrative.py - Narrative generator for design explanations

ALPHA OWNS THIS FILE.

Module 42: Explanation Engine - v1.1
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timezone

from .schemas import ParameterDiff, ValidatorSummary, DesignExplanation
from .trace import TraceCollector
from ..utils import safe_get

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class NarrativeGenerator:
    """
    Generates human-readable narratives for design changes.

    v1.1: Handles missing fields gracefully.
    """

    def __init__(self, state: Optional["StateManager"] = None):
        """
        Initialize narrative generator.

        Args:
            state: Optional StateManager for context
        """
        self.state = state

    def generate(
        self,
        diffs: List[ParameterDiff],
        validation_summaries: List[ValidatorSummary],
        phase: str = "",
        agent_id: str = "",
        proposal_id: str = "",
    ) -> DesignExplanation:
        """
        Generate a complete design explanation.

        Args:
            diffs: Parameter changes
            validation_summaries: Validation results
            phase: Current design phase
            agent_id: Agent that made changes
            proposal_id: Related proposal ID

        Returns:
            Complete DesignExplanation
        """
        # Generate summary
        summary = self._generate_summary(diffs, validation_summaries)

        # Generate narrative
        narrative = self._generate_narrative(diffs, validation_summaries, phase)

        # Determine overall validity
        overall_valid = all(v.passed for v in validation_summaries)

        return DesignExplanation(
            summary=summary,
            narrative=narrative,
            diffs=diffs,
            validation_summaries=validation_summaries,
            overall_valid=overall_valid,
            phase=phase,
            agent_id=agent_id,
            proposal_id=proposal_id,
        )

    def generate_from_trace(
        self,
        trace: TraceCollector,
        phase: str = "",
        agent_id: str = "",
        proposal_id: str = "",
    ) -> DesignExplanation:
        """
        Generate explanation from a trace collector.

        Args:
            trace: TraceCollector with recorded events
            phase: Current design phase
            agent_id: Agent that made changes
            proposal_id: Related proposal ID

        Returns:
            Complete DesignExplanation
        """
        diffs = trace.get_diffs()
        summaries = trace.get_validation_summaries()
        return self.generate(diffs, summaries, phase, agent_id, proposal_id)

    def _generate_summary(
        self,
        diffs: List[ParameterDiff],
        validations: List[ValidatorSummary],
    ) -> str:
        """Generate a one-line summary."""
        change_count = len(diffs)
        major_count = len([d for d in diffs if d.significance == "major"])

        error_count = sum(v.error_count for v in validations)
        warning_count = sum(v.warning_count for v in validations)

        parts = []

        # Changes part
        if change_count == 0:
            parts.append("No parameter changes")
        elif change_count == 1:
            parts.append("1 parameter changed")
        else:
            parts.append(f"{change_count} parameters changed")

        if major_count > 0:
            parts.append(f"({major_count} major)")

        # Validation part
        if error_count > 0:
            parts.append(f"{error_count} errors")
        elif warning_count > 0:
            parts.append(f"{warning_count} warnings")
        else:
            parts.append("validation passed")

        return ", ".join(parts)

    def _generate_narrative(
        self,
        diffs: List[ParameterDiff],
        validations: List[ValidatorSummary],
        phase: str,
    ) -> str:
        """Generate a detailed narrative."""
        sections = []

        # Opening
        if phase:
            sections.append(f"During the {phase} phase, the following changes were made:\n")
        else:
            sections.append("The following design changes were made:\n")

        # Changes section
        if diffs:
            sections.append(self._format_changes_section(diffs))

        # Validation section
        if validations:
            sections.append(self._format_validation_section(validations))

        # Conclusion
        sections.append(self._format_conclusion(diffs, validations))

        return "\n".join(sections)

    def _format_changes_section(self, diffs: List[ParameterDiff]) -> str:
        """Format the changes section of narrative."""
        lines = ["## Parameter Changes\n"]

        # Group by category
        by_category: Dict[str, List[ParameterDiff]] = {}
        for diff in diffs:
            cat = diff.category or "other"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(diff)

        for category, cat_diffs in sorted(by_category.items()):
            lines.append(f"\n### {category.title()}\n")

            for diff in cat_diffs:
                change_str = self._format_change(diff)
                significance_icon = {
                    "major": "!",
                    "moderate": "*",
                    "minor": "-",
                }.get(diff.significance, "-")

                lines.append(f"{significance_icon} **{diff.name}**: {change_str}")

                if diff.change_percent is not None:
                    lines.append(f"  ({diff.change_percent:+.1f}% change)")

        return "\n".join(lines)

    def _format_change(self, diff: ParameterDiff) -> str:
        """Format a single change."""
        old_str = self._format_value(diff.old_value, diff.unit)
        new_str = self._format_value(diff.new_value, diff.unit)
        return f"{old_str} → {new_str}"

    def _format_value(self, value: Any, unit: str = "") -> str:
        """Format a value for display."""
        if value is None:
            return "not set"
        if isinstance(value, float):
            formatted = f"{value:.3f}".rstrip("0").rstrip(".")
        else:
            formatted = str(value)

        if unit:
            return f"{formatted} {unit}"
        return formatted

    def _format_validation_section(self, validations: List[ValidatorSummary]) -> str:
        """Format the validation section of narrative."""
        lines = ["\n## Validation Results\n"]

        for v in validations:
            status = "PASSED" if v.passed else "FAILED"
            icon = "✓" if v.passed else "✗"

            lines.append(f"{icon} **{v.validator_name}**: {status}")

            if v.error_count > 0:
                lines.append(f"  - {v.error_count} error(s)")
            if v.warning_count > 0:
                lines.append(f"  - {v.warning_count} warning(s)")
            if v.key_message:
                lines.append(f"  - {v.key_message}")

        return "\n".join(lines)

    def _format_conclusion(
        self,
        diffs: List[ParameterDiff],
        validations: List[ValidatorSummary],
    ) -> str:
        """Format the conclusion section."""
        lines = ["\n## Conclusion\n"]

        total_errors = sum(v.error_count for v in validations)
        total_warnings = sum(v.warning_count for v in validations)
        major_changes = len([d for d in diffs if d.significance == "major"])

        if total_errors > 0:
            lines.append(
                f"The design has {total_errors} validation error(s) that need to be resolved "
                "before proceeding."
            )
        elif total_warnings > 0:
            lines.append(
                f"The design is valid with {total_warnings} warning(s) to consider."
            )
        else:
            lines.append("The design passes all validation checks.")

        if major_changes > 0:
            lines.append(
                f"\n{major_changes} major change(s) may significantly affect downstream calculations."
            )

        return "\n".join(lines)
