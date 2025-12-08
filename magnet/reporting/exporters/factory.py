"""
reporting/exporters/factory.py - Exporter factory.

ALPHA OWNS THIS FILE.

Module 14 v1.1 - Export factory and convenience class.
"""

from __future__ import annotations
from typing import Dict, Optional, Type, TYPE_CHECKING

from .base import BaseExporter
from .markdown import MarkdownExporter
from .html import HTMLExporter
from .json_exporter import JSONExporter
from .csv_exporter import CSVExporter
from .pdf import PDFExporter
from .docx import DOCXExporter
from ..enums import ExportFormat

if TYPE_CHECKING:
    from ..schema import Report


# Registry of exporters by format
_EXPORTER_REGISTRY: Dict[ExportFormat, Type[BaseExporter]] = {
    ExportFormat.MARKDOWN: MarkdownExporter,
    ExportFormat.HTML: HTMLExporter,
    ExportFormat.JSON: JSONExporter,
    ExportFormat.CSV: CSVExporter,
    ExportFormat.PDF: PDFExporter,
    ExportFormat.DOCX: DOCXExporter,
}


def get_exporter(format: ExportFormat, **kwargs) -> BaseExporter:
    """
    Get exporter instance for format.

    Args:
        format: Export format
        **kwargs: Exporter-specific options

    Returns:
        BaseExporter instance

    Raises:
        ValueError: Unknown export format
    """
    if format not in _EXPORTER_REGISTRY:
        raise ValueError(f"Unknown export format: {format}")

    exporter_class = _EXPORTER_REGISTRY[format]
    return exporter_class(**kwargs)


class ReportExporter:
    """
    Convenience class for exporting reports.

    Provides unified interface for all export formats.
    """

    def __init__(self):
        """Initialize report exporter."""
        self._exporters: Dict[ExportFormat, BaseExporter] = {}

    def export(
        self,
        report: "Report",
        format: ExportFormat,
        **kwargs,
    ) -> str:
        """
        Export report to string.

        Args:
            report: Report to export
            format: Target format
            **kwargs: Exporter options

        Returns:
            String representation in target format
        """
        exporter = get_exporter(format, **kwargs)
        return exporter.export(report)

    def export_to_file(
        self,
        report: "Report",
        file_path: str,
        format: Optional[ExportFormat] = None,
        **kwargs,
    ) -> None:
        """
        Export report to file.

        Args:
            report: Report to export
            file_path: Output file path
            format: Target format (auto-detected from extension if None)
            **kwargs: Exporter options
        """
        if format is None:
            format = self._detect_format(file_path)

        exporter = get_exporter(format, **kwargs)
        exporter.export_to_file(report, file_path)

    def _detect_format(self, file_path: str) -> ExportFormat:
        """Detect format from file extension."""
        ext = file_path.lower().split(".")[-1] if "." in file_path else ""

        extension_map = {
            "md": ExportFormat.MARKDOWN,
            "markdown": ExportFormat.MARKDOWN,
            "html": ExportFormat.HTML,
            "htm": ExportFormat.HTML,
            "json": ExportFormat.JSON,
            "csv": ExportFormat.CSV,
            "pdf": ExportFormat.PDF,
            "docx": ExportFormat.DOCX,
        }

        if ext not in extension_map:
            raise ValueError(
                f"Cannot detect format from extension '.{ext}'. "
                f"Supported: {list(extension_map.keys())}"
            )

        return extension_map[ext]

    @staticmethod
    def list_formats() -> list:
        """List available export formats."""
        return list(ExportFormat)

    @staticmethod
    def is_format_available(format: ExportFormat) -> bool:
        """Check if format is fully available (not a stub)."""
        # Stubs that require external libraries
        stub_formats = {ExportFormat.PDF, ExportFormat.DOCX}
        return format not in stub_formats
