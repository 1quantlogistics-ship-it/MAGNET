"""
reporting/schema.py - Report data structures.

ALPHA OWNS THIS FILE.

Module 14 v1.1 - Reporting Framework data structures.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .enums import ReportType, SectionType, FigureType


@dataclass
class ReportMetadata:
    """Report metadata."""
    title: str
    report_type: ReportType
    design_id: str
    design_name: str

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "MAGNET"
    version: str = "1.0"

    classification_society: Optional[str] = None
    project_number: Optional[str] = None
    revision: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "report_type": self.report_type.value,
            "design_id": self.design_id,
            "design_name": self.design_name,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "version": self.version,
            "classification_society": self.classification_society,
            "project_number": self.project_number,
            "revision": self.revision,
        }


@dataclass
class ReportFigure:
    """Report figure/chart."""
    figure_id: str
    figure_type: FigureType
    title: str

    caption: str = ""
    data: Any = None
    svg_content: Optional[str] = None
    image_path: Optional[str] = None

    width_percent: int = 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "figure_id": self.figure_id,
            "figure_type": self.figure_type.value,
            "title": self.title,
            "caption": self.caption,
            "has_data": self.data is not None,
            "has_svg": self.svg_content is not None,
            "image_path": self.image_path,
        }


@dataclass
class ReportTable:
    """Report table."""
    table_id: str
    title: str

    headers: List[str] = field(default_factory=list)
    rows: List[List[Any]] = field(default_factory=list)

    caption: str = ""
    column_widths: Optional[List[int]] = None

    def add_row(self, *values) -> None:
        """Add a row to the table."""
        self.rows.append(list(values))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_id": self.table_id,
            "title": self.title,
            "headers": self.headers,
            "rows": self.rows,
            "caption": self.caption,
            "row_count": len(self.rows),
        }


@dataclass
class ReportSection:
    """Report section."""
    section_id: str
    section_type: SectionType
    title: str

    content: str = ""
    level: int = 1

    tables: List[ReportTable] = field(default_factory=list)
    figures: List[ReportFigure] = field(default_factory=list)
    subsections: List["ReportSection"] = field(default_factory=list)

    def add_paragraph(self, text: str) -> None:
        """Add paragraph to content."""
        if self.content:
            self.content += "\n\n"
        self.content += text

    def add_table(self, table: ReportTable) -> None:
        """Add table to section."""
        self.tables.append(table)

    def add_figure(self, figure: ReportFigure) -> None:
        """Add figure to section."""
        self.figures.append(figure)

    def add_subsection(self, subsection: "ReportSection") -> None:
        """Add subsection."""
        subsection.level = self.level + 1
        self.subsections.append(subsection)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "section_type": self.section_type.value,
            "title": self.title,
            "content": self.content,
            "level": self.level,
            "tables": [t.to_dict() for t in self.tables],
            "figures": [f.to_dict() for f in self.figures],
            "subsections": [s.to_dict() for s in self.subsections],
        }


@dataclass
class Report:
    """Complete report."""
    metadata: ReportMetadata
    sections: List[ReportSection] = field(default_factory=list)

    executive_summary: str = ""
    table_of_contents: bool = True

    def add_section(self, section: ReportSection) -> None:
        """Add section to report."""
        self.sections.append(section)

    def get_section(self, section_type: SectionType) -> Optional[ReportSection]:
        """Get section by type."""
        for section in self.sections:
            if section.section_type == section_type:
                return section
        return None

    def get_all_tables(self) -> List[ReportTable]:
        """Get all tables from all sections."""
        tables = []
        for section in self.sections:
            tables.extend(section.tables)
            for subsection in section.subsections:
                tables.extend(subsection.tables)
        return tables

    def get_all_figures(self) -> List[ReportFigure]:
        """Get all figures from all sections."""
        figures = []
        for section in self.sections:
            figures.extend(section.figures)
            for subsection in section.subsections:
                figures.extend(subsection.figures)
        return figures

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "executive_summary": self.executive_summary,
            "sections": [s.to_dict() for s in self.sections],
            "table_count": len(self.get_all_tables()),
            "figure_count": len(self.get_all_figures()),
        }
