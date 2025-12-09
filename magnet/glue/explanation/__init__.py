"""
glue/explanation/ - Explanation Engine (Module 42)

ALPHA OWNS THIS FILE.

Provides design change explanations and narratives for agents and users.
"""

from .schemas import (
    ParameterDiff,
    ValidatorSummary,
    DesignExplanation,
)

from .trace import TraceCollector

from .narrative import NarrativeGenerator

from .formatters import (
    MarkdownFormatter,
    HTMLFormatter,
)


__all__ = [
    # Schemas
    "ParameterDiff",
    "ValidatorSummary",
    "DesignExplanation",
    # Trace
    "TraceCollector",
    # Narrative
    "NarrativeGenerator",
    # Formatters
    "MarkdownFormatter",
    "HTMLFormatter",
]
