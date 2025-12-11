"""
magnet/llm/prompts/explanation.py - Explanation Prompt Templates

Templates for generating design change explanations and narratives.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# =============================================================================
# System Prompts
# =============================================================================

EXPLANATION_SYSTEM_PROMPT = """You are a naval architecture assistant explaining design changes.

Your role:
- Explain design parameter changes in clear, technical language
- Highlight trade-offs and implications
- Provide actionable next steps
- Adjust detail level based on audience (SUMMARY/STANDARD/DETAILED/EXPERT)

Guidelines:
- Use proper naval architecture terminology
- Quantify impacts where possible
- Be concise but complete
- Focus on the "why" behind changes, not just the "what"
- Warn about potential issues or risks"""

NARRATIVE_SYSTEM_PROMPT = """You are writing design narratives for naval architects.

Your role:
- Create cohesive narratives from design changes
- Explain the reasoning behind automated optimizations
- Connect changes to their downstream effects
- Write for technical professionals

Guidelines:
- Maintain professional tone
- Use appropriate maritime/naval terminology
- Be factual and data-driven
- Include relevant metrics and comparisons"""


# =============================================================================
# Explanation Level Configuration
# =============================================================================

EXPLANATION_LEVELS = {
    "SUMMARY": {
        "description": "Brief overview for quick review",
        "max_sentences": 3,
        "include_details": False,
        "include_tradeoffs": False,
    },
    "STANDARD": {
        "description": "Normal detail for regular use",
        "max_sentences": 6,
        "include_details": True,
        "include_tradeoffs": True,
    },
    "DETAILED": {
        "description": "Full technical explanation",
        "max_sentences": 12,
        "include_details": True,
        "include_tradeoffs": True,
    },
    "EXPERT": {
        "description": "Maximum detail with calculations",
        "max_sentences": None,
        "include_details": True,
        "include_tradeoffs": True,
    },
}


# =============================================================================
# Prompt Templates
# =============================================================================

def create_change_explanation_prompt(
    parameter_diffs: List[Dict[str, Any]],
    validation_results: List[Dict[str, Any]],
    warnings: List[str],
    level: str = "STANDARD",
) -> str:
    """
    Create a prompt for explaining design changes.

    Args:
        parameter_diffs: List of parameter changes with old/new values
        validation_results: List of validation pass/fail results
        warnings: List of warning messages
        level: Explanation detail level

    Returns:
        Formatted prompt string
    """
    level_config = EXPLANATION_LEVELS.get(level, EXPLANATION_LEVELS["STANDARD"])

    # Format changes
    changes_str = "\n".join(
        f"- {d.get('name', d.get('parameter', 'unknown'))}: "
        f"{d.get('old_value', 'N/A')} -> {d.get('new_value', 'N/A')}"
        f" ({d.get('change_percent', 0):.1f}%)"
        for d in parameter_diffs
    )

    # Format validations
    validations_str = "\n".join(
        f"- {v.get('name', 'unknown')}: {'PASS' if v.get('passed') else 'FAIL'} - {v.get('message', '')}"
        for v in validation_results
    )

    # Format warnings
    warnings_str = "\n".join(f"- {w}" for w in warnings) if warnings else "None"

    return f"""Explain these design changes at {level} detail level:

Parameter Changes:
{changes_str}

Validation Results:
{validations_str}

Warnings:
{warnings_str}

Detail Level: {level} - {level_config['description']}
Max sentences: {level_config['max_sentences'] or 'unlimited'}
Include trade-offs: {level_config['include_tradeoffs']}

Respond with JSON:
{{
    "summary": "1-2 sentence overview",
    "narrative": "Detailed explanation",
    "changes": [
        {{
            "parameter": "param.path",
            "old_value": <old>,
            "new_value": <new>,
            "change_percent": 10.5,
            "impact": "moderate",
            "explanation": "Why this changed and what it means",
            "trade_offs": ["Trade-off 1", "Trade-off 2"]
        }}
    ],
    "next_steps": ["Step 1", "Step 2"],
    "warnings": ["Warning 1"]
}}"""


def create_narrative_prompt(
    design_context: Dict[str, Any],
    changes_summary: str,
    audience: str = "naval_architect",
) -> str:
    """
    Create a prompt for generating a design narrative.

    Args:
        design_context: Current design state information
        changes_summary: Summary of recent changes
        audience: Target audience for the narrative

    Returns:
        Formatted prompt string
    """
    context_str = "\n".join(
        f"- {k}: {v}" for k, v in design_context.items()
    )

    return f"""Generate a design narrative for a {audience}:

Design Context:
{context_str}

Recent Changes:
{changes_summary}

Write a cohesive narrative that:
1. Explains the current design state
2. Describes the changes made and why
3. Highlights any concerns or opportunities
4. Suggests next steps if appropriate

Keep the tone professional and technical."""


def create_next_steps_prompt(
    current_state: Dict[str, Any],
    completed_phases: List[str],
    validation_status: Dict[str, bool],
) -> str:
    """
    Create a prompt for generating recommended next steps.

    Args:
        current_state: Current design state
        completed_phases: List of completed design phases
        validation_status: Dict of validation name -> pass/fail

    Returns:
        Formatted prompt string
    """
    phases_str = ", ".join(completed_phases) if completed_phases else "None"
    validations_str = "\n".join(
        f"- {name}: {'PASS' if passed else 'FAIL'}"
        for name, passed in validation_status.items()
    )

    return f"""Recommend next steps for this design:

Completed Phases: {phases_str}

Validation Status:
{validations_str}

Current State Summary:
- Vessel Type: {current_state.get('mission.vessel_type', 'unknown')}
- Length: {current_state.get('hull.length', 'unknown')} m
- Phase: {current_state.get('current_phase', 'unknown')}

Generate 3-5 prioritized next steps. Focus on:
1. Addressing any failing validations
2. Completing required design phases
3. Optimization opportunities

Respond with JSON array of next steps, each with:
{{
    "step": "Description",
    "priority": 1-5,
    "reason": "Why this step"
}}"""


# =============================================================================
# Domain-Specific Templates
# =============================================================================

def create_stability_explanation_prompt(
    stability_changes: Dict[str, Any],
    compliance_status: Dict[str, bool],
) -> str:
    """Template for explaining stability-related changes."""
    changes_str = "\n".join(
        f"- {k}: {v.get('old', 'N/A')} -> {v.get('new', 'N/A')}"
        for k, v in stability_changes.items()
    )

    compliance_str = "\n".join(
        f"- {k}: {'COMPLIANT' if v else 'NON-COMPLIANT'}"
        for k, v in compliance_status.items()
    )

    return f"""Explain these stability-related changes:

Changes:
{changes_str}

IMO Compliance:
{compliance_str}

Focus on:
1. Impact on vessel safety
2. IMO/classification compliance
3. Operational implications
4. Recommendations if non-compliant

Use standard naval architecture stability terminology."""


def create_performance_explanation_prompt(
    performance_metrics: Dict[str, Any],
    previous_metrics: Optional[Dict[str, Any]] = None,
) -> str:
    """Template for explaining performance changes."""
    if previous_metrics:
        changes_str = "\n".join(
            f"- {k}: {previous_metrics.get(k, 'N/A')} -> {v}"
            for k, v in performance_metrics.items()
        )
    else:
        changes_str = "\n".join(
            f"- {k}: {v}"
            for k, v in performance_metrics.items()
        )

    return f"""Explain these performance metrics:

{'Changes' if previous_metrics else 'Current Values'}:
{changes_str}

Include:
1. What these metrics mean for operations
2. How they compare to typical values
3. Trade-offs with other design aspects
4. Optimization opportunities"""


# =============================================================================
# Template Registry
# =============================================================================

EXPLANATION_TEMPLATES = {
    "changes": create_change_explanation_prompt,
    "narrative": create_narrative_prompt,
    "next_steps": create_next_steps_prompt,
    "stability": create_stability_explanation_prompt,
    "performance": create_performance_explanation_prompt,
}


# =============================================================================
# Fallback Responses
# =============================================================================

# Parameter name mappings for human-readable output
PARAMETER_DISPLAY_NAMES = {
    "hull.length": "Length Overall (LOA)",
    "hull.beam": "Beam",
    "hull.draft": "Design Draft",
    "hull.depth": "Depth",
    "hull.block_coefficient": "Block Coefficient (Cb)",
    "stability.gm_m": "Metacentric Height (GM)",
    "stability.gz_max_m": "Maximum Righting Arm (GZ)",
    "weight.displacement_tonnes": "Displacement",
    "weight.lightship_tonnes": "Lightship Weight",
    "weight.deadweight_tonnes": "Deadweight",
    "resistance.total_kn": "Total Resistance",
    "propulsion.power_kw": "Required Power",
    "mission.speed_knots": "Design Speed",
    "mission.range_nm": "Range",
    "mission.endurance_days": "Endurance",
}


def get_parameter_display_name(parameter_path: str) -> str:
    """Get human-readable name for a parameter."""
    return PARAMETER_DISPLAY_NAMES.get(
        parameter_path,
        parameter_path.split(".")[-1].replace("_", " ").title()
    )


def get_fallback_explanation(
    parameter_diffs: List[Dict[str, Any]],
    validation_results: List[Dict[str, Any]],
    warnings: List[str],
) -> Dict[str, Any]:
    """
    Generate fallback explanation without LLM.

    Args:
        parameter_diffs: List of parameter changes
        validation_results: Validation results
        warnings: Warning messages

    Returns:
        Static explanation response
    """
    # Build summary
    change_count = len(parameter_diffs)
    fail_count = sum(1 for v in validation_results if not v.get("passed"))

    summary = f"{change_count} parameter(s) changed"
    if fail_count > 0:
        summary += f", {fail_count} validation(s) failing"

    # Build narrative
    narrative_parts = []
    if parameter_diffs:
        narrative_parts.append("The following parameters were modified:")
        for diff in parameter_diffs[:5]:  # Limit to 5
            name = get_parameter_display_name(diff.get("parameter", diff.get("name", "unknown")))
            old_val = diff.get("old_value", "N/A")
            new_val = diff.get("new_value", "N/A")
            pct = diff.get("change_percent", 0)
            narrative_parts.append(f"- {name}: {old_val} -> {new_val} ({pct:+.1f}%)")

    # Build next steps
    next_steps = []
    if fail_count > 0:
        next_steps.append("Review and address failing validations")
    next_steps.append("Verify changes meet design requirements")
    if warnings:
        next_steps.append("Review warnings for potential issues")

    return {
        "summary": summary,
        "narrative": "\n".join(narrative_parts) if narrative_parts else "No significant changes to report.",
        "changes": [
            {
                "parameter": d.get("parameter", d.get("name", "unknown")),
                "old_value": d.get("old_value"),
                "new_value": d.get("new_value"),
                "change_percent": d.get("change_percent", 0),
                "impact": "moderate",
                "explanation": f"{get_parameter_display_name(d.get('parameter', ''))} was modified",
                "trade_offs": [],
            }
            for d in parameter_diffs
        ],
        "next_steps": next_steps,
        "warnings": warnings,
    }
