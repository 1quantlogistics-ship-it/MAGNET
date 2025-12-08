"""
reporting/exporters/docx.py - DOCX exporter stub.

ALPHA OWNS THIS FILE.

Module 14 v1.1 - DOCX export stub (per v1.1 P2).
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .base import BaseExporter
from ..enums import ExportFormat

if TYPE_CHECKING:
    from ..schema import Report


class DOCXExporter(BaseExporter):
    """
    DOCX exporter stub.

    v1.1 P2: Stub implementation - requires external library (python-docx).
    """

    format = ExportFormat.DOCX

    def export(self, report: "Report") -> str:
        """
        Export report to DOCX.

        Raises:
            NotImplementedError: DOCX export requires external library
        """
        raise NotImplementedError(
            "DOCX export requires python-docx library. "
            "Use MarkdownExporter or HTMLExporter for text-based output, "
            "then convert externally if DOCX is required."
        )

    def export_to_file(self, report: "Report", file_path: str) -> None:
        """
        Export report to DOCX file.

        Raises:
            NotImplementedError: DOCX export requires external library
        """
        raise NotImplementedError(
            "DOCX export requires python-docx library. "
            "Use MarkdownExporter or HTMLExporter for text-based output, "
            "then convert externally if DOCX is required."
        )

    @staticmethod
    def is_available() -> bool:
        """Check if DOCX export is available."""
        return False

    @staticmethod
    def get_requirements() -> str:
        """Get installation requirements for DOCX export."""
        return "DOCX export requires: pip install python-docx"
