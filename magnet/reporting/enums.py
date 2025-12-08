"""
reporting/enums.py - Reporting enumerations.

ALPHA OWNS THIS FILE.

Module 14 v1.1 - Reporting Framework enumerations.
"""

from enum import Enum


class ReportType(Enum):
    """Report type identifiers."""
    DESIGN_SUMMARY = "design_summary"
    COMPLIANCE = "compliance"
    COST = "cost"
    STABILITY = "stability"
    STRUCTURAL = "structural"
    PRODUCTION = "production"
    FULL = "full"
    CUSTOM = "custom"


class ExportFormat(Enum):
    """Export format options."""
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    PDF = "pdf"
    DOCX = "docx"
    CSV = "csv"
    XML = "xml"


class SectionType(Enum):
    """Report section types."""
    TITLE = "title"
    SUMMARY = "summary"
    PRINCIPAL_CHARACTERISTICS = "principal_characteristics"
    HULL_FORM = "hull_form"
    WEIGHT_ESTIMATE = "weight_estimate"
    STABILITY = "stability"
    PROPULSION = "propulsion"
    COMPLIANCE = "compliance"
    COST = "cost"
    PRODUCTION = "production"
    APPENDIX = "appendix"
    CUSTOM = "custom"


class FigureType(Enum):
    """Figure/chart types."""
    GZ_CURVE = "gz_curve"
    BODY_PLAN = "body_plan"
    LINES_PLAN = "lines_plan"
    GENERAL_ARRANGEMENT = "general_arrangement"
    WEIGHT_BREAKDOWN = "weight_breakdown"
    COST_BREAKDOWN = "cost_breakdown"
    GANTT_CHART = "gantt_chart"
    CUSTOM = "custom"
