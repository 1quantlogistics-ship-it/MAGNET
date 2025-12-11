"""
magnet/llm/prompts/schemas.py - Pydantic Response Models

Defines structured response schemas for LLM outputs to ensure
type-safe, validated responses.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Clarification Schemas
# =============================================================================


class ClarificationOption(BaseModel):
    """A single option for a clarification question."""

    value: str = Field(..., description="The option value")
    label: str = Field(..., description="Human-readable label")
    description: Optional[str] = Field(None, description="Additional context")


class ClarificationResponse(BaseModel):
    """Response schema for clarification question generation."""

    question: str = Field(..., description="The clarification question to ask")
    options: List[ClarificationOption] = Field(
        default_factory=list,
        description="Available options for the user",
        max_length=10,
    )
    default: Optional[str] = Field(None, description="Default option value")
    context: Optional[str] = Field(
        None, description="Additional context for the question"
    )
    priority: int = Field(
        default=5, ge=1, le=10, description="Priority (1=highest, 10=lowest)"
    )


class UserIntentResponse(BaseModel):
    """Response schema for parsing user intent from clarification response."""

    understood_value: Any = Field(..., description="The parsed value from user input")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence in interpretation"
    )
    needs_followup: bool = Field(
        default=False, description="Whether additional clarification is needed"
    )
    followup_question: Optional[str] = Field(
        None, description="Follow-up question if needed"
    )


# =============================================================================
# Explanation Schemas
# =============================================================================


class ChangeImpact(str, Enum):
    """Impact level of a design change."""

    CRITICAL = "critical"
    SIGNIFICANT = "significant"
    MODERATE = "moderate"
    MINOR = "minor"
    NEGLIGIBLE = "negligible"


class ParameterChangeExplanation(BaseModel):
    """Explanation for a single parameter change."""

    parameter: str = Field(..., description="Parameter path")
    old_value: Any = Field(..., description="Previous value")
    new_value: Any = Field(..., description="New value")
    change_percent: Optional[float] = Field(None, description="Percentage change")
    impact: ChangeImpact = Field(
        default=ChangeImpact.MODERATE, description="Impact level"
    )
    explanation: str = Field(..., description="Human-readable explanation")
    trade_offs: List[str] = Field(
        default_factory=list, description="Associated trade-offs"
    )


class ExplanationResponse(BaseModel):
    """Response schema for design change explanations."""

    summary: str = Field(..., description="Brief summary of changes")
    narrative: str = Field(..., description="Detailed narrative explanation")
    changes: List[ParameterChangeExplanation] = Field(
        default_factory=list, description="Individual change explanations"
    )
    next_steps: List[str] = Field(
        default_factory=list, description="Recommended next steps"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Warnings or concerns"
    )


# =============================================================================
# Compliance Schemas
# =============================================================================


class RemediationAction(BaseModel):
    """A specific action to remediate a compliance failure."""

    action: str = Field(..., description="Description of the action")
    parameter: Optional[str] = Field(None, description="Parameter to modify")
    suggested_value: Optional[Any] = Field(None, description="Suggested new value")
    estimated_impact: Optional[str] = Field(None, description="Expected impact")
    trade_offs: List[str] = Field(
        default_factory=list, description="Trade-offs of this action"
    )


class ComplianceRemediationResponse(BaseModel):
    """Response schema for compliance remediation guidance."""

    rule_name: str = Field(..., description="Name of the failed rule")
    severity: str = Field(
        default="medium", description="Severity: critical, high, medium, low"
    )
    explanation: str = Field(..., description="Why this rule matters")
    current_state: str = Field(..., description="Description of current state")
    required_state: str = Field(..., description="Description of required state")
    remediation_actions: List[RemediationAction] = Field(
        ..., min_length=1, description="Actions to fix the issue"
    )
    estimated_effort: Optional[str] = Field(
        None, description="Estimated effort to remediate"
    )


# =============================================================================
# Routing Schemas
# =============================================================================


class RouteSelectionResponse(BaseModel):
    """Response schema for route selection decisions."""

    selected_index: int = Field(..., ge=0, description="Index of selected route")
    reasoning: str = Field(..., description="Why this route was selected")
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Confidence in selection"
    )
    alternatives_considered: List[str] = Field(
        default_factory=list, description="Brief notes on alternatives"
    )
    trade_offs: List[str] = Field(
        default_factory=list, description="Trade-offs of selected route"
    )


class ConflictResolutionStrategy(str, Enum):
    """Available strategies for resolving routing conflicts."""

    REROUTE_A = "reroute_a"
    REROUTE_B = "reroute_b"
    ADD_SEPARATION = "add_separation"
    SHARED_TRUNK = "shared_trunk"
    PRIORITY_OVERRIDE = "priority_override"
    MANUAL_REVIEW = "manual_review"


class ConflictResolutionResponse(BaseModel):
    """Response schema for conflict resolution decisions."""

    strategy: ConflictResolutionStrategy = Field(
        ..., description="Selected resolution strategy"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Strategy-specific parameters"
    )
    reasoning: str = Field(..., description="Why this strategy was selected")
    affected_systems: List[str] = Field(
        default_factory=list, description="Systems affected by resolution"
    )
    estimated_rework: Optional[str] = Field(
        None, description="Estimated rework required"
    )


class OptimizationSuggestion(BaseModel):
    """A suggestion for route optimization."""

    description: str = Field(..., description="Description of optimization")
    benefit: str = Field(..., description="Expected benefit")
    implementation: str = Field(..., description="How to implement")
    priority: int = Field(
        default=5, ge=1, le=10, description="Priority (1=highest)"
    )


class RouteOptimizationResponse(BaseModel):
    """Response schema for route optimization suggestions."""

    suggestions: List[OptimizationSuggestion] = Field(
        ..., min_length=1, description="Optimization suggestions"
    )
    overall_assessment: str = Field(
        ..., description="Overall assessment of current routing"
    )
    potential_savings: Optional[str] = Field(
        None, description="Potential cost/time savings"
    )


# =============================================================================
# Validation Schemas
# =============================================================================


class ValidationFix(BaseModel):
    """A suggested fix for a validation issue."""

    description: str = Field(..., description="Description of the fix")
    parameter: Optional[str] = Field(None, description="Parameter to modify")
    suggested_value: Optional[Any] = Field(None, description="Suggested value")
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Confidence this will fix issue"
    )


class ValidationExplanationResponse(BaseModel):
    """Response schema for validation failure explanations."""

    issue: str = Field(..., description="Brief description of the issue")
    explanation: str = Field(..., description="Detailed explanation")
    impact: str = Field(..., description="Impact if not addressed")
    suggested_fixes: List[ValidationFix] = Field(
        ..., min_length=1, description="Suggested fixes"
    )
    related_validations: List[str] = Field(
        default_factory=list, description="Related validations that may be affected"
    )


# =============================================================================
# Chat/Conversational Schemas
# =============================================================================


class ChatResponseType(str, Enum):
    """Type of chat response."""

    ANSWER = "answer"
    CLARIFICATION = "clarification"
    ACTION = "action"
    ERROR = "error"


class ChatResponse(BaseModel):
    """Response schema for conversational chat interactions."""

    response_type: ChatResponseType = Field(..., description="Type of response")
    content: str = Field(..., description="Response content")
    suggested_actions: List[str] = Field(
        default_factory=list, description="Suggested follow-up actions"
    )
    context_used: List[str] = Field(
        default_factory=list, description="Context items used in response"
    )
    confidence: float = Field(
        default=0.9, ge=0.0, le=1.0, description="Confidence in response"
    )
