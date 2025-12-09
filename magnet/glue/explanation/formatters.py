"""
glue/explanation/formatters.py - Output formatters for explanations

ALPHA OWNS THIS FILE.

Module 42: Explanation Engine
"""

from __future__ import annotations
from typing import List
from abc import ABC, abstractmethod

from .schemas import DesignExplanation, ParameterDiff, ValidatorSummary


class ExplanationFormatter(ABC):
    """Base class for explanation formatters."""

    @abstractmethod
    def format(self, explanation: DesignExplanation) -> str:
        """Format an explanation to string output."""
        pass


class MarkdownFormatter(ExplanationFormatter):
    """Formats explanations as Markdown."""

    def format(self, explanation: DesignExplanation) -> str:
        """Format explanation as Markdown."""
        sections = []

        # Header
        status = "Valid" if explanation.overall_valid else "Invalid"
        sections.append(f"# Design Change Explanation")
        sections.append(f"\n## Status: {status}")

        # Summary
        sections.append(f"\n{explanation.summary}")

        # Changes
        if explanation.diffs:
            sections.append("\n### Key Changes")
            sections.append("| Parameter | Old | New | Change |")
            sections.append("|-----------|-----|-----|--------|")

            for diff in explanation.diffs:
                change_str = f"{diff.change_percent:+.1f}%" if diff.change_percent else "-"
                sections.append(
                    f"| {diff.name} | {diff.old_value} | {diff.new_value} | {change_str} |"
                )

        # Validation
        if explanation.validation_summaries:
            sections.append("\n### Validation Results")
            for v in explanation.validation_summaries:
                icon = "✓" if v.passed else "✗"
                sections.append(f"- {icon} **{v.validator_name}**: {v.key_message}")

        return "\n".join(sections)

    def format_compact(self, explanation: DesignExplanation) -> str:
        """Format a compact Markdown summary."""
        status = "✓" if explanation.overall_valid else "✗"
        return (
            f"{status} {explanation.total_changes} changes, "
            f"{explanation.total_errors} errors, "
            f"{explanation.total_warnings} warnings"
        )


class HTMLFormatter(ExplanationFormatter):
    """Formats explanations as HTML."""

    def format(self, explanation: DesignExplanation) -> str:
        """Format explanation as HTML."""
        sections = []

        # Header
        status_class = "valid" if explanation.overall_valid else "invalid"
        sections.append("<div class='design-explanation'>")
        sections.append(f"<h1>Design Change Explanation</h1>")
        sections.append(f"<div class='status {status_class}'>{explanation.summary}</div>")

        # Changes table
        if explanation.diffs:
            sections.append("<h2>Parameter Changes</h2>")
            sections.append("<table class='changes-table'>")
            sections.append("<tr><th>Parameter</th><th>Old</th><th>New</th><th>Change</th></tr>")

            for diff in explanation.diffs:
                change_str = f"{diff.change_percent:+.1f}%" if diff.change_percent else "-"
                row_class = f"significance-{diff.significance}"
                sections.append(
                    f"<tr class='{row_class}'>"
                    f"<td>{diff.name}</td>"
                    f"<td>{diff.old_value}</td>"
                    f"<td>{diff.new_value}</td>"
                    f"<td>{change_str}</td>"
                    f"</tr>"
                )

            sections.append("</table>")

        # Validation results
        if explanation.validation_summaries:
            sections.append("<h2>Validation Results</h2>")
            sections.append("<ul class='validation-list'>")

            for v in explanation.validation_summaries:
                status_class = "passed" if v.passed else "failed"
                sections.append(
                    f"<li class='{status_class}'>"
                    f"<strong>{v.validator_name}</strong>: {v.key_message}"
                    f"</li>"
                )

            sections.append("</ul>")

        # Narrative
        if explanation.narrative:
            sections.append("<h2>Detailed Analysis</h2>")
            sections.append(f"<div class='narrative'>{self._markdown_to_html(explanation.narrative)}</div>")

        sections.append("</div>")

        return "\n".join(sections)

    def _markdown_to_html(self, text: str) -> str:
        """Simple markdown to HTML conversion."""
        # Basic conversion - replace markdown patterns
        import re

        # Headers
        text = re.sub(r'^## (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^### (.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)

        # Bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)

        # Lists
        text = re.sub(r'^- (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)

        # Paragraphs
        text = re.sub(r'\n\n', r'</p><p>', text)

        return f"<p>{text}</p>"

    def get_css(self) -> str:
        """Get CSS styles for HTML output."""
        return """
        .design-explanation {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .status { padding: 10px; border-radius: 4px; margin: 10px 0; }
        .status.valid { background: #d4edda; color: #155724; }
        .status.invalid { background: #f8d7da; color: #721c24; }
        .changes-table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        .changes-table th, .changes-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        .changes-table th { background: #f5f5f5; }
        .significance-major { background: #fff3cd; }
        .significance-moderate { background: #d1ecf1; }
        .validation-list { list-style: none; padding: 0; }
        .validation-list li { padding: 5px 10px; margin: 5px 0; border-radius: 4px; }
        .validation-list .passed { background: #d4edda; }
        .validation-list .failed { background: #f8d7da; }
        """


class JSONFormatter(ExplanationFormatter):
    """Formats explanations as JSON."""

    def format(self, explanation: DesignExplanation) -> str:
        """Format explanation as JSON."""
        import json
        return json.dumps(explanation.to_dict(), indent=2, default=str)
