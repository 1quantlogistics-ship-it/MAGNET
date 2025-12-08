"""
reporting/__init__.py - Reporting module exports.

ALPHA OWNS THIS FILE.

Module 14 v1.1 - Reporting framework.
"""

from .enums import ReportType, ExportFormat, SectionType, FigureType
from .schema import (
    ReportMetadata,
    ReportFigure,
    ReportTable,
    ReportSection,
    Report,
)
from .generators import (
    BaseReportGenerator,
    DesignSummaryGenerator,
    ComplianceReportGenerator,
    CostReportGenerator,
    FullReportGenerator,
)
from .exporters import (
    MarkdownExporter,
    HTMLExporter,
    JSONExporter,
    CSVExporter,
    PDFExporter,
    DOCXExporter,
    ReportExporter,
    get_exporter,
)
from .validator import ReportingValidator

__all__ = [
    # Enums
    "ReportType",
    "ExportFormat",
    "SectionType",
    "FigureType",
    # Schema
    "ReportMetadata",
    "ReportFigure",
    "ReportTable",
    "ReportSection",
    "Report",
    # Generators
    "BaseReportGenerator",
    "DesignSummaryGenerator",
    "ComplianceReportGenerator",
    "CostReportGenerator",
    "FullReportGenerator",
    # Exporters
    "MarkdownExporter",
    "HTMLExporter",
    "JSONExporter",
    "CSVExporter",
    "PDFExporter",
    "DOCXExporter",
    "ReportExporter",
    "get_exporter",
    # Validator
    "ReportingValidator",
]
