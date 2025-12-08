"""
reporting/exporters/base.py - Base exporter class.

ALPHA OWNS THIS FILE.

Module 14 v1.1 - Base exporter interface.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional

from ..schema import Report
from ..enums import ExportFormat


class BaseExporter(ABC):
    """Abstract base class for report exporters."""

    format: ExportFormat

    @abstractmethod
    def export(self, report: Report) -> str:
        """
        Export report to string format.

        Args:
            report: Report to export

        Returns:
            String representation in target format
        """
        pass

    def export_to_file(self, report: Report, file_path: str) -> None:
        """
        Export report directly to file.

        Args:
            report: Report to export
            file_path: Output file path
        """
        content = self.export(report)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
