"""
magnet/llm/prompts/compliance.py - Compliance Prompt Templates

Templates for generating compliance remediation guidance.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# =============================================================================
# System Prompts
# =============================================================================

COMPLIANCE_SYSTEM_PROMPT = """You are a naval architecture compliance expert.

Your role:
- Explain why compliance rules matter for vessel safety
- Provide specific, actionable remediation guidance
- Quantify trade-offs of different remediation approaches
- Reference relevant IMO/classification standards

Guidelines:
- Be specific about parameter changes needed
- Explain impacts on other design aspects
- Consider practical constraints (cost, weight, space)
- Prioritize safety-critical issues
- Provide 2-3 remediation options when possible"""

RULE_EXPLANATION_SYSTEM_PROMPT = """You are explaining maritime compliance rules.

Your role:
- Explain the purpose and origin of compliance rules
- Describe what happens if the rule is not met
- Provide context on how the rule affects design decisions

Guidelines:
- Reference specific IMO conventions/codes when applicable
- Use examples to illustrate concepts
- Keep explanations accessible but technically accurate"""


# =============================================================================
# Compliance Rule Context
# =============================================================================

COMPLIANCE_FRAMEWORKS = {
    "imo_intact": {
        "name": "IMO Intact Stability Code",
        "description": "International Maritime Organization code for intact stability",
        "reference": "IMO Resolution MSC.267(85)",
    },
    "imo_damage": {
        "name": "IMO SOLAS Damage Stability",
        "description": "Safety of Life at Sea damage stability requirements",
        "reference": "SOLAS Chapter II-1",
    },
    "imo_loadline": {
        "name": "International Load Line Convention",
        "description": "Freeboard and subdivision requirements",
        "reference": "LL 66/88",
    },
    "class_dnv": {
        "name": "DNV GL Rules",
        "description": "Det Norske Veritas classification rules",
        "reference": "DNV GL Rules for Ships",
    },
    "class_lr": {
        "name": "Lloyd's Register Rules",
        "description": "Lloyd's Register classification requirements",
        "reference": "LR Rules for Ships",
    },
}


# =============================================================================
# Prompt Templates
# =============================================================================

def create_remediation_prompt(
    rule_name: str,
    rule_description: str,
    actual_value: Any,
    required_value: Any,
    design_context: Dict[str, Any],
    framework: Optional[str] = None,
) -> str:
    """
    Create a prompt for generating remediation guidance.

    Args:
        rule_name: Name of the failed rule
        rule_description: Description of the rule
        actual_value: Current value
        required_value: Required value
        design_context: Current design state
        framework: Compliance framework (imo_intact, class_dnv, etc.)

    Returns:
        Formatted prompt string
    """
    # Get framework info
    framework_info = COMPLIANCE_FRAMEWORKS.get(framework, {})
    framework_str = f"\nFramework: {framework_info.get('name', framework or 'Unknown')}"
    if framework_info.get("reference"):
        framework_str += f"\nReference: {framework_info['reference']}"

    # Format design context
    context_str = "\n".join(
        f"- {k}: {v}" for k, v in design_context.items()
    )

    # Calculate shortfall
    shortfall_str = ""
    if isinstance(actual_value, (int, float)) and isinstance(required_value, (int, float)):
        shortfall = required_value - actual_value
        shortfall_pct = abs(shortfall / required_value) * 100 if required_value != 0 else 0
        shortfall_str = f"\nShortfall: {shortfall:.3f} ({shortfall_pct:.1f}%)"

    return f"""Generate remediation guidance for this compliance failure:

Rule: {rule_name}
Description: {rule_description}
{framework_str}

Current Value: {actual_value}
Required Value: {required_value}
{shortfall_str}

Design Context:
{context_str}

Provide 2-3 specific remediation actions with trade-off analysis.

Respond with JSON:
{{
    "rule_name": "{rule_name}",
    "severity": "critical|high|medium|low",
    "explanation": "Why this rule matters for vessel safety",
    "current_state": "Description of current state",
    "required_state": "What needs to be achieved",
    "remediation_actions": [
        {{
            "action": "Specific action description",
            "parameter": "parameter.path",
            "suggested_value": <new value>,
            "estimated_impact": "What effect this will have",
            "trade_offs": ["Trade-off 1", "Trade-off 2"]
        }}
    ],
    "estimated_effort": "Low|Medium|High"
}}"""


def create_rule_explanation_prompt(
    rule_name: str,
    rule_description: str,
    framework: Optional[str] = None,
) -> str:
    """
    Create a prompt for explaining a compliance rule.

    Args:
        rule_name: Name of the rule
        rule_description: Brief description
        framework: Compliance framework

    Returns:
        Formatted prompt string
    """
    framework_info = COMPLIANCE_FRAMEWORKS.get(framework, {})

    return f"""Explain this maritime compliance rule:

Rule: {rule_name}
Description: {rule_description}
Framework: {framework_info.get('name', framework or 'Unknown')}
Reference: {framework_info.get('reference', 'N/A')}

Provide:
1. Purpose of the rule (safety rationale)
2. What the rule requires
3. Consequences of non-compliance
4. How it typically affects naval vessel design

Keep explanation concise but informative (2-3 paragraphs)."""


def create_batch_remediation_prompt(
    failures: List[Dict[str, Any]],
    design_context: Dict[str, Any],
) -> str:
    """
    Create a prompt for batch remediation of multiple failures.

    Args:
        failures: List of compliance failures
        design_context: Current design state

    Returns:
        Formatted prompt string
    """
    failures_str = "\n".join(
        f"{i+1}. {f.get('rule_name', 'Unknown')}: "
        f"actual={f.get('actual_value')}, required={f.get('required_value')}"
        for i, f in enumerate(failures)
    )

    context_str = "\n".join(f"- {k}: {v}" for k, v in design_context.items())

    return f"""Generate remediation plan for these compliance failures:

Failures:
{failures_str}

Design Context:
{context_str}

Prioritize actions that:
1. Address multiple failures
2. Have minimal negative trade-offs
3. Are most critical for safety

Respond with JSON array of remediation actions, sorted by priority."""


# =============================================================================
# Domain-Specific Templates
# =============================================================================

def create_stability_remediation_prompt(
    gm_actual: float,
    gm_required: float,
    design_context: Dict[str, Any],
) -> str:
    """Template for GM remediation."""
    return f"""Generate remediation for insufficient metacentric height (GM):

Current GM: {gm_actual:.3f} m
Required GM: {gm_required:.3f} m
Shortfall: {gm_required - gm_actual:.3f} m

Design Context:
- Beam: {design_context.get('hull.beam', 'unknown')} m
- VCG: {design_context.get('weight.vcg_m', 'unknown')} m
- Displacement: {design_context.get('weight.displacement_tonnes', 'unknown')} tonnes

Common remediation approaches:
1. Increase beam (affects resistance, construction cost)
2. Lower VCG (may require ballast, affects capacity)
3. Reduce topside weight (affects equipment, structure)

Provide specific parameter changes with trade-offs."""


def create_freeboard_remediation_prompt(
    freeboard_actual: float,
    freeboard_required: float,
    design_context: Dict[str, Any],
) -> str:
    """Template for freeboard remediation."""
    return f"""Generate remediation for insufficient freeboard:

Current Freeboard: {freeboard_actual:.3f} m
Required Freeboard: {freeboard_required:.3f} m
Shortfall: {freeboard_required - freeboard_actual:.3f} m

Design Context:
- Depth: {design_context.get('hull.depth', 'unknown')} m
- Draft: {design_context.get('hull.draft', 'unknown')} m
- Displacement: {design_context.get('weight.displacement_tonnes', 'unknown')} tonnes

Common remediation approaches:
1. Increase depth (affects structure, cost)
2. Reduce draft (affects displacement, stability)
3. Reduce displacement (affects payload capacity)

Provide specific parameter changes with trade-offs."""


def create_gz_remediation_prompt(
    gz_actual: float,
    gz_required: float,
    angle: float,
    design_context: Dict[str, Any],
) -> str:
    """Template for GZ curve remediation."""
    return f"""Generate remediation for insufficient righting arm (GZ):

GZ at {angle}°: {gz_actual:.3f} m
Required GZ: {gz_required:.3f} m
Shortfall: {gz_required - gz_actual:.3f} m

Design Context:
- GM: {design_context.get('stability.gm_m', 'unknown')} m
- KG: {design_context.get('weight.kg_m', 'unknown')} m
- Beam: {design_context.get('hull.beam', 'unknown')} m

Consider hull form and weight distribution changes.
Provide specific parameter changes with trade-offs."""


# =============================================================================
# Template Registry
# =============================================================================

COMPLIANCE_TEMPLATES = {
    "remediation": create_remediation_prompt,
    "rule_explanation": create_rule_explanation_prompt,
    "batch_remediation": create_batch_remediation_prompt,
    "stability_gm": create_stability_remediation_prompt,
    "freeboard": create_freeboard_remediation_prompt,
    "stability_gz": create_gz_remediation_prompt,
}


# =============================================================================
# Fallback Responses
# =============================================================================

# Standard remediation suggestions by rule type
FALLBACK_REMEDIATIONS = {
    "gm": [
        {
            "action": "Increase beam to improve form stability",
            "parameter": "hull.beam",
            "estimated_impact": "GM increases approximately 0.1m per 0.5m beam increase",
            "trade_offs": ["Increased resistance", "Higher construction cost"],
        },
        {
            "action": "Lower vertical center of gravity (VCG)",
            "parameter": "weight.vcg_m",
            "estimated_impact": "GM increases directly with VCG reduction",
            "trade_offs": ["May require ballast", "Reduced internal volume"],
        },
    ],
    "freeboard": [
        {
            "action": "Increase hull depth",
            "parameter": "hull.depth",
            "estimated_impact": "Freeboard increases directly with depth",
            "trade_offs": ["Increased structural weight", "Higher cost"],
        },
        {
            "action": "Reduce design draft",
            "parameter": "hull.draft",
            "estimated_impact": "Freeboard increases directly with draft reduction",
            "trade_offs": ["Reduced displacement capacity", "May affect stability"],
        },
    ],
    "gz": [
        {
            "action": "Modify hull form for improved righting arm",
            "parameter": "hull.block_coefficient",
            "estimated_impact": "GZ curve shape affected by hull form",
            "trade_offs": ["May affect resistance", "Requires hull redesign"],
        },
    ],
    "default": [
        {
            "action": "Review design parameters and adjust as needed",
            "parameter": None,
            "estimated_impact": "Depends on specific changes made",
            "trade_offs": ["Trade-offs vary by modification"],
        },
    ],
}


def get_fallback_remediation(
    rule_name: str,
    actual_value: Any,
    required_value: Any,
) -> Dict[str, Any]:
    """
    Generate fallback remediation without LLM.

    Args:
        rule_name: Name of the failed rule
        actual_value: Current value
        required_value: Required value

    Returns:
        Static remediation response
    """
    # Determine rule type for fallback selection
    rule_lower = rule_name.lower()
    if "gm" in rule_lower or "metacentric" in rule_lower:
        rule_type = "gm"
    elif "freeboard" in rule_lower:
        rule_type = "freeboard"
    elif "gz" in rule_lower or "righting" in rule_lower:
        rule_type = "gz"
    else:
        rule_type = "default"

    actions = FALLBACK_REMEDIATIONS.get(rule_type, FALLBACK_REMEDIATIONS["default"])

    return {
        "rule_name": rule_name,
        "severity": "medium",
        "explanation": f"The {rule_name} requirement ensures vessel safety and regulatory compliance.",
        "current_state": f"Current value ({actual_value}) does not meet requirement ({required_value})",
        "required_state": f"Value must be at least {required_value}",
        "remediation_actions": actions,
        "estimated_effort": "Medium",
    }
