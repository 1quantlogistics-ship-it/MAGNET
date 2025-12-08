"""
reporting/exporters/pdf.py - PDF exporter stub.

ALPHA OWNS THIS FILE.

Module 14 v1.1 - PDF export stub (per v1.1 P2).
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .base import BaseExporter
from ..enums import ExportFormat

if TYPE_CHECKING:
    from ..schema import Report


class PDFExporter(BaseExporter):
    """
    PDF exporter stub.

    v1.1 P2: Stub implementation - requires external library (reportlab/weasyprint).
    """

    format = ExportFormat.PDF

    def export(self, report: "Report") -> str:
        """
        Export report to PDF.

        Raises:
            NotImplementedError: PDF export requires external library
        """
        raise NotImplementedError(
            "PDF export requires external library (reportlab or weasyprint). "
            "Use MarkdownExporter or HTMLExporter for text-based output, "
            "then convert externally if PDF is required."
        )

    def export_to_file(self, report: "Report", file_path: str) -> None:
        """
        Export report to PDF file.

        Raises:
            NotImplementedError: PDF export requires external library
        """
        raise NotImplementedError(
            "PDF export requires external library (reportlab or weasyprint). "
            "Use MarkdownExporter or HTMLExporter for text-based output, "
            "then convert externally if PDF is required."
        )

    @staticmethod
    def is_available() -> bool:
        """Check if PDF export is available."""
        return False

    @staticmethod
    def get_requirements() -> str:
        """Get installation requirements for PDF export."""
        return (
            "PDF export requires one of the following:\n"
            "  pip install reportlab  # For programmatic PDF generation\n"
            "  pip install weasyprint  # For HTML-to-PDF conversion"
        )
