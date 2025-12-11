"""
magnet/llm/prompts - LLM Prompt Templates and Response Schemas

Provides structured prompts and Pydantic models for LLM interactions.
"""

from .schemas import (
    ClarificationResponse,
    ExplanationResponse,
    ComplianceRemediationResponse,
    RouteSelectionResponse,
    ConflictResolutionResponse,
)
from .clarification import CLARIFICATION_TEMPLATES
from .explanation import EXPLANATION_TEMPLATES
from .compliance import COMPLIANCE_TEMPLATES
from .routing import ROUTING_TEMPLATES

__all__ = [
    # Response schemas
    "ClarificationResponse",
    "ExplanationResponse",
    "ComplianceRemediationResponse",
    "RouteSelectionResponse",
    "ConflictResolutionResponse",
    # Templates
    "CLARIFICATION_TEMPLATES",
    "EXPLANATION_TEMPLATES",
    "COMPLIANCE_TEMPLATES",
    "ROUTING_TEMPLATES",
]
