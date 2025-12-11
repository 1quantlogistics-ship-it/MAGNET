"""
magnet/llm/prompts/clarification.py - Clarification Prompt Templates

Templates for generating clarification questions and parsing user responses.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# =============================================================================
# System Prompts
# =============================================================================

CLARIFICATION_SYSTEM_PROMPT = """You are a naval architecture assistant helping clarify design requirements.

Your role:
- Generate clear, concise clarification questions
- Provide sensible options with context
- Use technical terms appropriately but explain them when needed
- Keep questions focused on one topic at a time

Guidelines:
- Questions should be answerable with provided options or a brief response
- Default values should be the most common or safest choice
- Include brief descriptions for technical options
- Priority 1-3: Critical design decisions
- Priority 4-6: Important but not blocking
- Priority 7-10: Nice-to-have clarifications"""

INTENT_PARSING_SYSTEM_PROMPT = """You are parsing user responses to clarification questions.

Your role:
- Extract the intended value from the user's response
- Handle partial matches and synonyms
- Flag responses that need follow-up clarification
- Express confidence in your interpretation

Guidelines:
- If the response clearly matches an option, use that value
- If the response is ambiguous, set needs_followup=true
- For numeric values, parse units if provided
- Confidence should reflect how certain you are"""


# =============================================================================
# Prompt Templates
# =============================================================================

def create_clarification_prompt(
    parameter_path: str,
    validation_message: str,
    context: Optional[Dict[str, Any]] = None,
    option_count: int = 3,
    include_custom: bool = True,
) -> str:
    """
    Create a prompt for generating a clarification question.

    Args:
        parameter_path: The parameter that needs clarification
        validation_message: The validation failure message
        context: Additional context about the design
        option_count: Number of options to generate
        include_custom: Whether to include a custom option

    Returns:
        Formatted prompt string
    """
    context_str = ""
    if context:
        context_items = [f"- {k}: {v}" for k, v in context.items()]
        context_str = f"\nDesign Context:\n" + "\n".join(context_items)

    return f"""Generate a clarification question for this validation issue:

Parameter: {parameter_path}
Issue: {validation_message}
{context_str}

Generate {option_count} practical options{' plus a custom option' if include_custom else ''}.

Respond with JSON:
{{
    "question": "Clear, concise question",
    "options": [
        {{"value": "option_value", "label": "Human Label", "description": "Brief context"}},
        ...
    ],
    "default": "recommended_value",
    "context": "Why this matters for the design",
    "priority": 5
}}"""


def create_intent_parsing_prompt(
    original_question: str,
    options: List[Dict[str, str]],
    user_response: str,
) -> str:
    """
    Create a prompt for parsing user intent from their response.

    Args:
        original_question: The question that was asked
        options: The options that were provided
        user_response: The user's response

    Returns:
        Formatted prompt string
    """
    options_str = "\n".join(
        f"- {opt.get('label', opt.get('value'))}: {opt.get('value')}"
        for opt in options
    )

    return f"""Parse the user's response to this clarification question:

Question: {original_question}

Available Options:
{options_str}

User Response: "{user_response}"

Determine the intended value. Respond with JSON:
{{
    "understood_value": <the value they meant>,
    "confidence": 0.95,
    "needs_followup": false,
    "followup_question": null
}}"""


def create_batch_clarification_prompt(
    issues: List[Dict[str, Any]],
    max_questions: int = 5,
) -> str:
    """
    Create a prompt for generating multiple clarification questions.

    Args:
        issues: List of validation issues needing clarification
        max_questions: Maximum questions to generate

    Returns:
        Formatted prompt string
    """
    issues_str = "\n".join(
        f"{i+1}. {issue.get('parameter', 'unknown')}: {issue.get('message', 'No message')}"
        for i, issue in enumerate(issues[:max_questions])
    )

    return f"""Generate clarification questions for these validation issues:

{issues_str}

For each issue, generate a focused question with options.
Prioritize issues that block further progress.

Respond with JSON array of questions:
[
    {{
        "parameter": "parameter.path",
        "question": "Clear question",
        "options": [...],
        "default": "recommended",
        "priority": 1-10
    }},
    ...
]"""


# =============================================================================
# Domain-Specific Templates
# =============================================================================

def create_vessel_type_clarification() -> str:
    """Template for clarifying vessel type when ambiguous."""
    return """Generate options for vessel type clarification.

The user has not specified a clear vessel type. Generate options based on common
naval vessel categories suitable for the MAGNET system.

Include:
- Patrol/fast attack craft
- Workboats/utility vessels
- Research/survey vessels
- Passenger/ferry vessels
- Custom/specialized

Respond with standard clarification JSON format."""


def create_dimension_clarification(
    dimension: str,
    current_value: Optional[float],
    constraints: Optional[Dict[str, float]] = None,
) -> str:
    """
    Template for clarifying vessel dimensions.

    Args:
        dimension: The dimension (length, beam, draft, etc.)
        current_value: Current value if any
        constraints: Min/max constraints if any
    """
    constraints_str = ""
    if constraints:
        constraints_str = f"\nConstraints: {constraints}"

    current_str = f"\nCurrent value: {current_value}" if current_value else ""

    return f"""The {dimension} needs clarification.
{current_str}{constraints_str}

Generate options that:
- Are within any specified constraints
- Cover typical ranges for small-medium naval vessels
- Include a custom option for specific requirements

Respond with standard clarification JSON format."""


def create_material_clarification(
    component: str,
    options_hint: Optional[List[str]] = None,
) -> str:
    """
    Template for clarifying material selection.

    Args:
        component: The component needing material selection
        options_hint: Suggested material options
    """
    hint_str = ""
    if options_hint:
        hint_str = f"\nConsider these materials: {', '.join(options_hint)}"

    return f"""Material selection needed for: {component}
{hint_str}

Generate material options with:
- Common marine-grade materials
- Trade-offs (cost, weight, maintenance)
- Typical applications

Respond with standard clarification JSON format."""


# =============================================================================
# Template Registry
# =============================================================================

CLARIFICATION_TEMPLATES = {
    "generic": create_clarification_prompt,
    "intent": create_intent_parsing_prompt,
    "batch": create_batch_clarification_prompt,
    "vessel_type": create_vessel_type_clarification,
    "dimension": create_dimension_clarification,
    "material": create_material_clarification,
}


# =============================================================================
# Fallback Responses
# =============================================================================

def get_fallback_clarification(
    parameter_path: str,
    message: str,
) -> Dict[str, Any]:
    """
    Generate a fallback clarification when LLM is unavailable.

    Args:
        parameter_path: The parameter needing clarification
        message: The validation message

    Returns:
        Static clarification response
    """
    # Extract the parameter name for a more readable question
    param_name = parameter_path.split(".")[-1].replace("_", " ").title()

    return {
        "question": f"Please specify {param_name}",
        "options": [
            {"value": "default", "label": "Use Default", "description": "Use system default value"},
            {"value": "custom", "label": "Custom Value", "description": "Specify a custom value"},
        ],
        "default": "default",
        "context": message,
        "priority": 5,
    }


def get_fallback_intent(user_response: str, options: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Parse user intent without LLM (simple matching).

    Args:
        user_response: The user's response
        options: Available options

    Returns:
        Best-effort intent parsing
    """
    response_lower = user_response.lower().strip()

    # Try exact match on value or label
    for opt in options:
        if response_lower == opt.get("value", "").lower():
            return {
                "understood_value": opt["value"],
                "confidence": 1.0,
                "needs_followup": False,
                "followup_question": None,
            }
        if response_lower == opt.get("label", "").lower():
            return {
                "understood_value": opt["value"],
                "confidence": 0.95,
                "needs_followup": False,
                "followup_question": None,
            }

    # Try partial match
    for opt in options:
        if opt.get("value", "").lower() in response_lower:
            return {
                "understood_value": opt["value"],
                "confidence": 0.7,
                "needs_followup": False,
                "followup_question": None,
            }
        if opt.get("label", "").lower() in response_lower:
            return {
                "understood_value": opt["value"],
                "confidence": 0.7,
                "needs_followup": False,
                "followup_question": None,
            }

    # No match - needs follow-up
    return {
        "understood_value": user_response,
        "confidence": 0.3,
        "needs_followup": True,
        "followup_question": "Could you please select one of the provided options or clarify your response?",
    }
