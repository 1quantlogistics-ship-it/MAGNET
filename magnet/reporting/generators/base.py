"""
reporting/generators/base.py - Base report generator.

ALPHA OWNS THIS FILE.

Module 14 v1.1 - Base class for report generators.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

from ..schema import Report, ReportMetadata
from ..enums import ReportType

if TYPE_CHECKING:
    from ...core.state_manager import StateManager


class BaseReportGenerator(ABC):
    """Base class for report generators."""

    report_type: ReportType = ReportType.CUSTOM

    def __init__(self):
        self._section_counter = 0
        self._table_counter = 0
        self._figure_counter = 0

    @abstractmethod
    def generate(self, state: "StateManager") -> Report:
        """Generate report from state."""
        pass

    def _create_metadata(self, state: "StateManager", title: str) -> ReportMetadata:
        """Create report metadata from state."""
        return ReportMetadata(
            title=title,
            report_type=self.report_type,
            design_id=state.get("design_id", "unknown"),
            design_name=state.get("design_name", "Unnamed Design"),
            classification_society=state.get("mission.classification_society"),
            project_number=state.get("project_number"),
        )

    def _next_section_id(self) -> str:
        """Get next section ID."""
        self._section_counter += 1
        return f"SEC-{self._section_counter:03d}"

    def _next_table_id(self) -> str:
        """Get next table ID."""
        self._table_counter += 1
        return f"TBL-{self._table_counter:03d}"

    def _next_figure_id(self) -> str:
        """Get next figure ID."""
        self._figure_counter += 1
        return f"FIG-{self._figure_counter:03d}"

    def _format_value(self, value: Any, precision: int = 2) -> str:
        """Format value for display."""
        if value is None:
            return "N/A"
        if isinstance(value, float):
            return f"{value:.{precision}f}"
        if isinstance(value, bool):
            return "Yes" if value else "No"
        return str(value)
