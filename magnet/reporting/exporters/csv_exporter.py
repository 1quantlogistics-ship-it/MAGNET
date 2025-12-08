"""
reporting/exporters/csv_exporter.py - CSV exporter.

ALPHA OWNS THIS FILE.

Module 14 v1.1 - CSV export (full implementation per v1.1 P2).
"""

from __future__ import annotations
import csv
import io
from typing import TYPE_CHECKING, List

from .base import BaseExporter
from ..enums import ExportFormat

if TYPE_CHECKING:
    from ..schema import Report, ReportTable


class CSVExporter(BaseExporter):
    """
    Exports report tables to CSV format.

    v1.1 P2: Full implementation - exports all tables.
    """

    format = ExportFormat.CSV

    def __init__(self, delimiter: str = ",", include_metadata: bool = True):
        """
        Initialize CSV exporter.

        Args:
            delimiter: Field delimiter character
            include_metadata: Include report metadata header
        """
        self.delimiter = delimiter
        self.include_metadata = include_metadata

    def export(self, report: "Report") -> str:
        """
        Export all report tables to CSV string.

        Each table is separated by a blank line with table title header.
        """
        output = io.StringIO()
        writer = csv.writer(output, delimiter=self.delimiter)

        # Metadata header
        if self.include_metadata:
            writer.writerow(["# Report:", report.metadata.title])
            writer.writerow(["# Project:", report.metadata.project_name])
            writer.writerow(["# Generated:", report.metadata.generated_at])
            writer.writerow([])

        # Collect all tables from all sections
        tables = self._collect_tables(report)

        for i, (section_title, table) in enumerate(tables):
            if i > 0:
                writer.writerow([])  # Blank separator

            # Table header
            writer.writerow([f"# Section: {section_title}"])
            writer.writerow([f"# Table {table.table_id}: {table.title}"])

            # Table headers
            if table.headers:
                writer.writerow(table.headers)

            # Table rows
            for row in table.rows:
                # Clean markdown formatting
                cleaned_row = [self._clean_cell(cell) for cell in row]
                writer.writerow(cleaned_row)

        return output.getvalue()

    def _collect_tables(self, report: "Report") -> List[tuple]:
        """Collect all tables from report sections."""
        tables = []

        for section in report.sections:
            for table in section.tables:
                tables.append((section.title, table))

            # Check subsections
            for subsection in section.subsections:
                for table in subsection.tables:
                    tables.append((f"{section.title} - {subsection.title}", table))

        return tables

    def _clean_cell(self, cell) -> str:
        """Clean markdown formatting from cell value."""
        cell_str = str(cell)

        # Remove markdown bold
        if cell_str.startswith("**") and cell_str.endswith("**"):
            cell_str = cell_str[2:-2]

        return cell_str

    def export_table(self, table: "ReportTable") -> str:
        """Export a single table to CSV."""
        output = io.StringIO()
        writer = csv.writer(output, delimiter=self.delimiter)

        if table.title:
            writer.writerow([f"# {table.title}"])

        if table.headers:
            writer.writerow(table.headers)

        for row in table.rows:
            cleaned_row = [self._clean_cell(cell) for cell in row]
            writer.writerow(cleaned_row)

        return output.getvalue()
