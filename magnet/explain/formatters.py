"""
explain/formatters.py - Format explanations for different outputs
BRAVO OWNS THIS FILE.

Section 42: Explanation Engine
"""

from __future__ import annotations
from abc import ABC, abstractmethod

from .schemas import Explanation, ExplanationLevel


class BaseFormatter(ABC):
    """Base class for explanation formatters."""

    @abstractmethod
    def format(self, explanation: Explanation) -> str:
        pass


class ChatFormatter(BaseFormatter):
    """Format explanations for chat interface."""

    def format(self, explanation: Explanation) -> str:
        lines = []

        # Summary always shown
        lines.append(f"**Summary:** {explanation.summary}")

        # Narrative for standard+
        if explanation.level != ExplanationLevel.SUMMARY and explanation.narrative:
            lines.append("")
            lines.append(explanation.narrative)

        # Warnings
        if explanation.warnings:
            lines.append("")
            for w in explanation.warnings[:3]:
                icon = "!" if w.severity == "warning" else "X" if w.severity == "error" else "i"
                lines.append(f"[{icon}] {w.message}")

        # Next steps
        if explanation.next_steps:
            lines.append("")
            lines.append("**Next steps:**")
            for step in explanation.next_steps[:3]:
                lines.append(f"- {step}")

        return "\n".join(lines)


class DashboardFormatter(BaseFormatter):
    """Format explanations for dashboard display."""

    def format(self, explanation: Explanation) -> str:
        sections = []

        # Status badge
        all_passed = all(v.passed for v in explanation.validator_summaries)
        status = "[PASSED]" if all_passed else "[ISSUES]"
        sections.append(f"## Status: {status}")

        # Summary
        sections.append(f"\n{explanation.summary}")

        # Key changes table
        if explanation.parameter_diffs:
            sections.append("\n### Key Changes")
            sections.append("| Parameter | Old | New | Change |")
            sections.append("|-----------|-----|-----|--------|")
            for diff in explanation.parameter_diffs[:10]:
                change_str = f"{diff.change_percent:+.1f}%" if diff.change_percent else "-"
                sections.append(f"| {diff.name} | {diff.old_value} | {diff.new_value} | {change_str} |")

        # Validation results
        if explanation.validator_summaries:
            sections.append("\n### Validation Results")
            for v in explanation.validator_summaries:
                icon = "[OK]" if v.passed else "[FAIL]"
                sections.append(f"- {icon} **{v.validator_name}**: {v.key_message}")

        return "\n".join(sections)


class ReportFormatter(BaseFormatter):
    """Format explanations for formal reports."""

    def format(self, explanation: Explanation) -> str:
        sections = []

        # Header
        sections.append("# Design Change Report")
        sections.append(f"\nGenerated: {explanation.created_at.isoformat()}")
        sections.append(f"\nReport ID: {explanation.explanation_id}")

        # Executive Summary
        sections.append("\n## Executive Summary")
        sections.append(explanation.summary)

        # Detailed Analysis
        if explanation.narrative:
            sections.append("\n## Detailed Analysis")
            sections.append(explanation.narrative)

        # Parameter Changes
        if explanation.parameter_diffs:
            sections.append("\n## Parameter Changes")
            for diff in explanation.parameter_diffs:
                sections.append(f"\n### {diff.name}")
                sections.append(f"- Path: `{diff.path}`")
                sections.append(f"- Previous Value: {diff.old_value}")
                sections.append(f"- New Value: {diff.new_value}")
                if diff.change_percent:
                    sections.append(f"- Change: {diff.change_percent:+.1f}%")
                sections.append(f"- Significance: {diff.significance}")

        # Validation Summary
        if explanation.validator_summaries:
            sections.append("\n## Validation Summary")
            for v in explanation.validator_summaries:
                status = "PASSED" if v.passed else "FAILED"
                sections.append(f"\n### {v.validator_name}: {status}")
                sections.append(f"- Errors: {v.error_count}")
                sections.append(f"- Warnings: {v.warning_count}")
                if v.key_message:
                    sections.append(f"- Key Finding: {v.key_message}")

        # Recommendations
        if explanation.next_steps:
            sections.append("\n## Recommendations")
            for i, step in enumerate(explanation.next_steps, 1):
                sections.append(f"{i}. {step}")

        return "\n".join(sections)
