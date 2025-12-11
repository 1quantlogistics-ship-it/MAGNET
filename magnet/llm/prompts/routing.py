"""
magnet/llm/prompts/routing.py - Routing Prompt Templates

Templates for route selection, conflict resolution, and optimization.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# =============================================================================
# System Prompts
# =============================================================================

ROUTING_SYSTEM_PROMPT = """You are a ship systems routing expert.

Your role:
- Select optimal routes for ship systems (HVAC, piping, electrical, etc.)
- Resolve conflicts between overlapping system routes
- Optimize routing for cost, maintainability, and safety
- Consider shipbuilding constraints and standards

Guidelines:
- Prioritize safety-critical systems
- Consider maintenance access requirements
- Minimize route length while avoiding conflicts
- Follow naval architecture routing best practices
- Balance cost with operational requirements"""

CONFLICT_RESOLUTION_SYSTEM_PROMPT = """You are resolving routing conflicts between ship systems.

Your role:
- Analyze conflicts between different system routes
- Select the best resolution strategy
- Minimize disruption to existing routing
- Ensure safety and compliance

Conflict Types:
- SPACE_CONFLICT: Routes occupy same physical space
- CLEARANCE_VIOLATION: Insufficient separation between systems
- ZONE_CROSSING: Route crosses restricted zone
- PRIORITY_CONFLICT: High-priority system blocked by lower-priority

Resolution Strategies:
- reroute_a: Reroute the first system
- reroute_b: Reroute the second system
- add_separation: Add physical separation
- shared_trunk: Use shared routing trunk
- priority_override: Override based on priority
- manual_review: Flag for manual engineering review"""


# =============================================================================
# System Type Definitions
# =============================================================================

SYSTEM_PRIORITIES = {
    "fire_main": 1,
    "bilge": 2,
    "fuel": 3,
    "potable_water": 4,
    "hvac": 5,
    "electrical": 3,
    "communications": 4,
    "sewage": 6,
}

SYSTEM_DESCRIPTIONS = {
    "fire_main": "Fire fighting main water system",
    "bilge": "Bilge pumping and drainage",
    "fuel": "Fuel oil service and transfer",
    "potable_water": "Potable water distribution",
    "hvac": "Heating, ventilation, and air conditioning",
    "electrical": "Power distribution cabling",
    "communications": "Communication and data cabling",
    "sewage": "Black and gray water",
}


# =============================================================================
# Prompt Templates
# =============================================================================

def create_route_selection_prompt(
    system_type: str,
    route_options: List[Dict[str, Any]],
    constraints: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a prompt for selecting the best route.

    Args:
        system_type: Type of system being routed
        route_options: List of route options with metrics
        constraints: Routing constraints

    Returns:
        Formatted prompt string
    """
    system_desc = SYSTEM_DESCRIPTIONS.get(system_type, system_type)
    priority = SYSTEM_PRIORITIES.get(system_type, 5)

    options_str = "\n".join(
        f"{i}. Route {i}: "
        f"length={opt.get('length_m', 'unknown')}m, "
        f"bends={opt.get('bend_count', 'unknown')}, "
        f"conflicts={opt.get('conflict_count', 0)}, "
        f"cost_factor={opt.get('cost_factor', 1.0):.2f}"
        for i, opt in enumerate(route_options)
    )

    constraints_str = ""
    if constraints:
        constraints_str = f"\nConstraints:\n" + "\n".join(
            f"- {k}: {v}" for k, v in constraints.items()
        )

    return f"""Select the best route for this system:

System: {system_type} ({system_desc})
Priority: {priority}/10 (1=highest)

Route Options:
{options_str}
{constraints_str}

Consider:
1. Route length and complexity (bends)
2. Conflicts with other systems
3. Cost implications
4. Maintenance accessibility
5. Safety requirements for this system type

Respond with JSON:
{{
    "selected_index": 0,
    "reasoning": "Why this route was selected",
    "confidence": 0.85,
    "alternatives_considered": ["Brief note on option 1", "Brief note on option 2"],
    "trade_offs": ["Trade-off 1", "Trade-off 2"]
}}"""


def create_conflict_resolution_prompt(
    system_a: str,
    system_b: str,
    conflict_type: str,
    affected_spaces: List[str],
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a prompt for resolving a routing conflict.

    Args:
        system_a: First system in conflict
        system_b: Second system in conflict
        conflict_type: Type of conflict
        affected_spaces: Spaces where conflict occurs
        context: Additional context

    Returns:
        Formatted prompt string
    """
    priority_a = SYSTEM_PRIORITIES.get(system_a, 5)
    priority_b = SYSTEM_PRIORITIES.get(system_b, 5)

    spaces_str = ", ".join(affected_spaces) if affected_spaces else "unknown"

    context_str = ""
    if context:
        context_str = f"\nAdditional Context:\n" + "\n".join(
            f"- {k}: {v}" for k, v in context.items()
        )

    return f"""Resolve this routing conflict:

System A: {system_a} (priority {priority_a})
System B: {system_b} (priority {priority_b})
Conflict Type: {conflict_type}
Affected Spaces: {spaces_str}
{context_str}

Available Strategies:
- reroute_a: Reroute {system_a}
- reroute_b: Reroute {system_b}
- add_separation: Add physical separation between systems
- shared_trunk: Use shared routing trunk where compatible
- priority_override: Higher priority system takes precedence
- manual_review: Flag for manual engineering review

Consider:
1. System priorities (lower number = higher priority)
2. Rerouting cost and complexity
3. Safety implications
4. Maintenance access requirements

Respond with JSON:
{{
    "strategy": "reroute_b",
    "parameters": {{"separation_mm": 100}},
    "reasoning": "Why this strategy was selected",
    "affected_systems": ["{system_a}", "{system_b}"],
    "estimated_rework": "Low|Medium|High"
}}"""


def create_optimization_prompt(
    current_routing: Dict[str, Any],
    optimization_goals: List[str],
) -> str:
    """
    Create a prompt for route optimization suggestions.

    Args:
        current_routing: Current routing state
        optimization_goals: Goals for optimization

    Returns:
        Formatted prompt string
    """
    routing_str = "\n".join(
        f"- {system}: {info.get('length_m', 'unknown')}m, "
        f"{info.get('bend_count', 'unknown')} bends"
        for system, info in current_routing.items()
    )

    goals_str = "\n".join(f"- {goal}" for goal in optimization_goals)

    return f"""Suggest optimizations for this routing layout:

Current Routing:
{routing_str}

Optimization Goals:
{goals_str}

For each suggestion, include:
1. Description of the optimization
2. Expected benefit
3. How to implement
4. Priority (1-10, 1=highest)

Respond with JSON:
{{
    "suggestions": [
        {{
            "description": "Optimization description",
            "benefit": "Expected benefit",
            "implementation": "How to implement",
            "priority": 3
        }}
    ],
    "overall_assessment": "Assessment of current routing",
    "potential_savings": "Estimated cost/time savings"
}}"""


def create_zone_compliance_prompt(
    route: Dict[str, Any],
    zones: List[Dict[str, Any]],
    violations: List[Dict[str, Any]],
) -> str:
    """
    Create a prompt for zone compliance routing fixes.

    Args:
        route: Route information
        zones: Zone definitions
        violations: Current violations

    Returns:
        Formatted prompt string
    """
    zones_str = "\n".join(
        f"- {z.get('name', 'unknown')}: {z.get('restrictions', 'no restrictions')}"
        for z in zones
    )

    violations_str = "\n".join(
        f"- {v.get('zone', 'unknown')}: {v.get('message', 'violation')}"
        for v in violations
    )

    return f"""Fix zone compliance violations for this route:

Route System: {route.get('system_type', 'unknown')}
Route Length: {route.get('length_m', 'unknown')}m

Zones:
{zones_str}

Current Violations:
{violations_str}

Suggest compliant rerouting options that:
1. Avoid restricted zones
2. Minimize additional route length
3. Maintain system performance

Respond with JSON array of rerouting options."""


# =============================================================================
# Template Registry
# =============================================================================

ROUTING_TEMPLATES = {
    "route_selection": create_route_selection_prompt,
    "conflict_resolution": create_conflict_resolution_prompt,
    "optimization": create_optimization_prompt,
    "zone_compliance": create_zone_compliance_prompt,
}


# =============================================================================
# Fallback Responses
# =============================================================================

def get_fallback_route_selection(
    route_options: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Select route using deterministic algorithm.

    Args:
        route_options: List of route options

    Returns:
        Selection response
    """
    if not route_options:
        return {
            "selected_index": 0,
            "reasoning": "No routes available",
            "confidence": 0.0,
            "alternatives_considered": [],
            "trade_offs": [],
        }

    # Score routes: prioritize fewer conflicts, then shorter length
    def score_route(route: Dict[str, Any]) -> float:
        conflicts = route.get("conflict_count", 0)
        length = route.get("length_m", float("inf"))
        bends = route.get("bend_count", 0)
        cost = route.get("cost_factor", 1.0)

        # Lower is better
        return conflicts * 1000 + length + bends * 10 + cost * 100

    scores = [(i, score_route(r)) for i, r in enumerate(route_options)]
    scores.sort(key=lambda x: x[1])

    best_idx = scores[0][0]

    return {
        "selected_index": best_idx,
        "reasoning": "Selected route with lowest combined score (conflicts, length, bends, cost)",
        "confidence": 0.7,
        "alternatives_considered": [
            f"Route {i}: score={s:.1f}"
            for i, s in scores[1:4]
        ],
        "trade_offs": ["Deterministic selection may not consider all factors"],
    }


def get_fallback_conflict_resolution(
    system_a: str,
    system_b: str,
    conflict_type: str,
) -> Dict[str, Any]:
    """
    Resolve conflict using priority-based rules.

    Args:
        system_a: First system
        system_b: Second system
        conflict_type: Type of conflict

    Returns:
        Resolution response
    """
    priority_a = SYSTEM_PRIORITIES.get(system_a, 5)
    priority_b = SYSTEM_PRIORITIES.get(system_b, 5)

    # Higher priority (lower number) wins
    if priority_a < priority_b:
        strategy = "reroute_b"
        reasoning = f"{system_a} has higher priority ({priority_a}) than {system_b} ({priority_b})"
    elif priority_b < priority_a:
        strategy = "reroute_a"
        reasoning = f"{system_b} has higher priority ({priority_b}) than {system_a} ({priority_a})"
    else:
        # Equal priority - use separation
        strategy = "add_separation"
        reasoning = f"Equal priority systems ({priority_a}) - adding separation"

    return {
        "strategy": strategy,
        "parameters": {"separation_mm": 100} if strategy == "add_separation" else {},
        "reasoning": reasoning,
        "affected_systems": [system_a, system_b],
        "estimated_rework": "Medium",
    }


def get_fallback_optimization() -> Dict[str, Any]:
    """
    Return generic optimization suggestions.

    Returns:
        Optimization response
    """
    return {
        "suggestions": [
            {
                "description": "Review routes for potential shortcuts",
                "benefit": "Reduced material cost and installation time",
                "implementation": "Analyze each route for direct path opportunities",
                "priority": 5,
            },
            {
                "description": "Identify shared trunk opportunities",
                "benefit": "Reduced total routing length",
                "implementation": "Group compatible systems for shared routing",
                "priority": 6,
            },
            {
                "description": "Review conflict resolutions for alternatives",
                "benefit": "Potential for simpler routing",
                "implementation": "Re-evaluate routes with updated constraints",
                "priority": 7,
            },
        ],
        "overall_assessment": "Routing appears functional. Manual review may identify additional optimizations.",
        "potential_savings": "Unknown - requires detailed analysis",
    }
