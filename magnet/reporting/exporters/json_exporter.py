"""
reporting/exporters/json_exporter.py - JSON exporter.

ALPHA OWNS THIS FILE.

Module 14 v1.1 - JSON export.
"""

from __future__ import annotations
import json
from typing import TYPE_CHECKING

from .base import BaseExporter
from ..enums import ExportFormat

if TYPE_CHECKING:
    from ..schema import Report


class JSONExporter(BaseExporter):
    """Exports reports to JSON format."""

    format = ExportFormat.JSON

    def __init__(self, indent: int = 2, ensure_ascii: bool = False):
        """
        Initialize JSON exporter.

        Args:
            indent: JSON indentation level
            ensure_ascii: Force ASCII encoding
        """
        self.indent = indent
        self.ensure_ascii = ensure_ascii

    def export(self, report: "Report") -> str:
        """Export report to JSON string."""
        data = report.to_dict()
        return json.dumps(
            data,
            indent=self.indent,
            ensure_ascii=self.ensure_ascii,
            default=str,
        )
