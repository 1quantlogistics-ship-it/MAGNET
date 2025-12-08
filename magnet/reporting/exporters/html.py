"""
reporting/exporters/html.py - HTML exporter.

ALPHA OWNS THIS FILE.

Module 14 v1.1 - HTML export.
"""

from __future__ import annotations
from typing import TYPE_CHECKING
import html as html_lib

from .base import BaseExporter
from ..enums import ExportFormat

if TYPE_CHECKING:
    from ..schema import Report, ReportSection, ReportTable


class HTMLExporter(BaseExporter):
    """Exports reports to HTML format."""

    format = ExportFormat.HTML

    def __init__(self, include_styles: bool = True):
        """
        Initialize HTML exporter.

        Args:
            include_styles: Include inline CSS styles
        """
        self.include_styles = include_styles

    def export(self, report: "Report") -> str:
        """Export report to HTML string."""
        parts = []

        # HTML header
        parts.append("<!DOCTYPE html>")
        parts.append("<html lang=\"en\">")
        parts.append("<head>")
        parts.append(f"<meta charset=\"UTF-8\">")
        parts.append(f"<title>{html_lib.escape(report.metadata.title)}</title>")

        if self.include_styles:
            parts.append(self._get_styles())

        parts.append("</head>")
        parts.append("<body>")

        # Main content
        parts.append("<div class=\"report\">")

        # Title and metadata
        parts.append(f"<h1>{html_lib.escape(report.metadata.title)}</h1>")
        parts.append("<div class=\"metadata\">")
        parts.append(f"<p><strong>Project:</strong> {html_lib.escape(report.metadata.project_name)}</p>")
        parts.append(f"<p><strong>Generated:</strong> {report.metadata.generated_at}</p>")
        parts.append(f"<p><strong>Version:</strong> {report.metadata.version}</p>")
        parts.append("</div>")

        # Executive summary
        if report.executive_summary:
            parts.append("<div class=\"executive-summary\">")
            parts.append("<h2>Executive Summary</h2>")
            parts.append(f"<p>{html_lib.escape(report.executive_summary)}</p>")
            parts.append("</div>")

        # Table of contents
        if report.sections:
            parts.append("<div class=\"toc\">")
            parts.append("<h2>Table of Contents</h2>")
            parts.append("<ul>")
            for section in report.sections:
                section_id = f"section-{section.section_id}".replace(".", "-")
                parts.append(f"<li><a href=\"#{section_id}\">{html_lib.escape(section.title)}</a></li>")
            parts.append("</ul>")
            parts.append("</div>")

        # Sections
        for section in report.sections:
            parts.extend(self._export_section(section))

        parts.append("</div>")  # report
        parts.append("</body>")
        parts.append("</html>")

        return "\n".join(parts)

    def _export_section(self, section: "ReportSection") -> list:
        """Export a single section."""
        parts = []

        section_id = f"section-{section.section_id}".replace(".", "-")
        parts.append(f"<section id=\"{section_id}\">")
        parts.append(f"<h2>{section.section_id}. {html_lib.escape(section.title)}</h2>")

        # Paragraphs
        for para in section.paragraphs:
            parts.append(f"<p>{html_lib.escape(para)}</p>")

        # Tables
        for table in section.tables:
            parts.extend(self._export_table(table))

        # Figures
        for figure in section.figures:
            parts.append("<figure>")
            parts.append(f"<img src=\"{figure.file_path or 'figure.png'}\" alt=\"{html_lib.escape(figure.caption)}\">")
            parts.append(f"<figcaption>Figure {figure.figure_id}: {html_lib.escape(figure.caption)}</figcaption>")
            parts.append("</figure>")

        # Subsections
        for subsection in section.subsections:
            parts.extend(self._export_subsection(subsection))

        parts.append("</section>")

        return parts

    def _export_subsection(self, section: "ReportSection") -> list:
        """Export a subsection."""
        parts = []

        parts.append("<div class=\"subsection\">")
        parts.append(f"<h3>{section.section_id}. {html_lib.escape(section.title)}</h3>")

        for para in section.paragraphs:
            parts.append(f"<p>{html_lib.escape(para)}</p>")

        for table in section.tables:
            parts.extend(self._export_table(table))

        parts.append("</div>")

        return parts

    def _export_table(self, table: "ReportTable") -> list:
        """Export a table to HTML."""
        parts = []

        parts.append("<div class=\"table-container\">")
        if table.title:
            parts.append(f"<p class=\"table-caption\">Table {table.table_id}: {html_lib.escape(table.title)}</p>")

        parts.append("<table>")

        # Header
        if table.headers:
            parts.append("<thead>")
            parts.append("<tr>")
            for header in table.headers:
                parts.append(f"<th>{html_lib.escape(str(header))}</th>")
            parts.append("</tr>")
            parts.append("</thead>")

        # Body
        if table.rows:
            parts.append("<tbody>")
            for row in table.rows:
                parts.append("<tr>")
                for cell in row:
                    cell_str = str(cell)
                    # Handle markdown bold
                    if cell_str.startswith("**") and cell_str.endswith("**"):
                        cell_str = f"<strong>{html_lib.escape(cell_str[2:-2])}</strong>"
                    else:
                        cell_str = html_lib.escape(cell_str)
                    parts.append(f"<td>{cell_str}</td>")
                parts.append("</tr>")
            parts.append("</tbody>")

        parts.append("</table>")
        parts.append("</div>")

        return parts

    def _get_styles(self) -> str:
        """Get inline CSS styles."""
        return """<style>
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.6;
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
    color: #333;
}
h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
h2 { color: #2c3e50; margin-top: 30px; }
h3 { color: #34495e; }
.metadata { background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
.executive-summary { background: #e8f4f8; padding: 20px; border-left: 4px solid #3498db; margin-bottom: 30px; }
.toc { background: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 30px; }
.toc ul { list-style-type: none; padding-left: 0; }
.toc li { margin: 8px 0; }
.toc a { color: #3498db; text-decoration: none; }
.toc a:hover { text-decoration: underline; }
table { border-collapse: collapse; width: 100%; margin: 20px 0; }
th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
th { background: #3498db; color: white; }
tr:nth-child(even) { background: #f8f9fa; }
.table-caption { font-weight: bold; margin-bottom: 5px; }
figure { margin: 20px 0; text-align: center; }
figcaption { font-style: italic; color: #666; margin-top: 10px; }
section { margin-bottom: 40px; }
</style>"""
