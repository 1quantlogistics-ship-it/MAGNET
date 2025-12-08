"""
reporting/exporters/markdown.py - Markdown exporter.

ALPHA OWNS THIS FILE.

Module 14 v1.1 - Markdown export.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .base import BaseExporter
from ..enums import ExportFormat

if TYPE_CHECKING:
    from ..schema import Report, ReportSection, ReportTable


class MarkdownExporter(BaseExporter):
    """Exports reports to Markdown format."""

    format = ExportFormat.MARKDOWN

    def export(self, report: "Report") -> str:
        """Export report to Markdown string."""
        lines = []

        # Title and metadata
        lines.append(f"# {report.metadata.title}")
        lines.append("")
        lines.append(f"**Project:** {report.metadata.project_name}")
        lines.append(f"**Generated:** {report.metadata.generated_at}")
        lines.append(f"**Version:** {report.metadata.version}")
        lines.append("")

        # Executive summary
        if report.executive_summary:
            lines.append("## Executive Summary")
            lines.append("")
            lines.append(report.executive_summary)
            lines.append("")

        # Table of contents
        if report.sections:
            lines.append("## Table of Contents")
            lines.append("")
            for section in report.sections:
                lines.append(f"- [{section.title}](#{self._slugify(section.title)})")
            lines.append("")

        # Sections
        for section in report.sections:
            lines.extend(self._export_section(section))

        return "\n".join(lines)

    def _export_section(self, section: "ReportSection") -> list:
        """Export a single section."""
        lines = []

        # Section header
        lines.append(f"## {section.section_id}. {section.title}")
        lines.append("")

        # Paragraphs
        for para in section.paragraphs:
            lines.append(para)
            lines.append("")

        # Tables
        for table in section.tables:
            lines.extend(self._export_table(table))

        # Figures (reference only)
        for figure in section.figures:
            lines.append(f"![{figure.caption}]({figure.file_path or 'figure'})")
            lines.append(f"*Figure {figure.figure_id}: {figure.caption}*")
            lines.append("")

        # Subsections
        for subsection in section.subsections:
            lines.extend(self._export_subsection(subsection))

        return lines

    def _export_subsection(self, section: "ReportSection") -> list:
        """Export a subsection (level 3)."""
        lines = []

        lines.append(f"### {section.section_id}. {section.title}")
        lines.append("")

        for para in section.paragraphs:
            lines.append(para)
            lines.append("")

        for table in section.tables:
            lines.extend(self._export_table(table))

        return lines

    def _export_table(self, table: "ReportTable") -> list:
        """Export a table to Markdown format."""
        lines = []

        if table.title:
            lines.append(f"**Table {table.table_id}: {table.title}**")
            lines.append("")

        if not table.headers:
            return lines

        # Header row
        header_row = "| " + " | ".join(str(h) for h in table.headers) + " |"
        lines.append(header_row)

        # Separator
        separator = "| " + " | ".join("---" for _ in table.headers) + " |"
        lines.append(separator)

        # Data rows
        for row in table.rows:
            row_str = "| " + " | ".join(str(cell) for cell in row) + " |"
            lines.append(row_str)

        lines.append("")

        return lines

    def _slugify(self, text: str) -> str:
        """Convert text to URL-safe slug."""
        return text.lower().replace(" ", "-").replace("&", "and")
