"""
explain/ - Explanation Engine
BRAVO OWNS THIS FILE.

Section 42: Explanation Engine

This module transforms raw validator data into human-readable
narratives at multiple detail levels.
"""

from .schemas import (
    ExplanationLevel,
    ParameterDiff,
    ValidatorSummary,
    Warning,
    Explanation,
)

from .trace_collector import (
    CalculationStep,
    CalculationTrace,
    TraceCollector,
)

from .narrative import (
    NarrativeGenerator,
    PARAMETER_NAMES,
)

from .formatters import (
    BaseFormatter,
    ChatFormatter,
    DashboardFormatter,
    ReportFormatter,
)

__all__ = [
    # Schemas
    "ExplanationLevel",
    "ParameterDiff",
    "ValidatorSummary",
    "Warning",
    "Explanation",
    # Trace
    "CalculationStep",
    "CalculationTrace",
    "TraceCollector",
    # Narrative
    "NarrativeGenerator",
    "PARAMETER_NAMES",
    # Formatters
    "BaseFormatter",
    "ChatFormatter",
    "DashboardFormatter",
    "ReportFormatter",
]
