"""
validators/causal_tracer.py

Walking Trail Contract 8: causal tracing for suggested fixes.

This module is intentionally lightweight: it provides a small set of
domain-true causal chains that make grade responses actionable.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def trace_upstream(
    *,
    from_parameter: str,
    state_manager: Any,
    limit: int = 6,
) -> List[Dict[str, Any]]:
    """
    Return a causal chain explaining how upstream parameters influence a downstream violation.

    The chain is a list of steps:
      { step_number, from_parameter, to_parameter, relationship, direction }
    """
    if limit <= 0:
        return []

    # GM causal chain (common)
    if from_parameter in (
        "weight.estimated_gm_m",
        "stability.gm_m",
        "stability.gm_corrected_m",
        "stability.gm_transverse_m",
    ):
        # We intentionally keep this chain generic and physically true.
        return [
            {
                "step_number": 1,
                "from_parameter": from_parameter,
                "to_parameter": "stability.kg_m",
                "relationship": "GM = KB + BM - KG; increasing KG decreases GM",
                "direction": "upstream",
            },
            {
                "step_number": 2,
                "from_parameter": from_parameter,
                "to_parameter": "hull.bm_m",
                "relationship": "GM = KB + BM - KG; increasing BM increases GM",
                "direction": "upstream",
            },
            {
                "step_number": 3,
                "from_parameter": "hull.bm_m",
                "to_parameter": "hull.beam",
                "relationship": "BM increases strongly with beam (waterplane inertia grows with B²)",
                "direction": "upstream",
            },
            {
                "step_number": 4,
                "from_parameter": "hull.bm_m",
                "to_parameter": "hull.draft",
                "relationship": "BM depends on waterplane inertia and displacement; draft shifts both",
                "direction": "upstream",
            },
        ][:limit]

    # Default: no known chain
    return []


def estimate_side_effects_for_change(
    *,
    target_path: str,
    current_value: Optional[float],
    suggested_value: Optional[float],
) -> List[str]:
    """
    Best-effort, conservative side-effect notes.
    """
    if target_path == "hull.beam" and current_value and suggested_value:
        if suggested_value > current_value:
            return ["resistance likely increases", "weight may increase", "deck area increases"]
        if suggested_value < current_value:
            return ["stability margin likely decreases", "resistance may decrease"]
    if target_path in ("stability.kg_m", "weight.lightship_vcg_m") and current_value and suggested_value:
        if suggested_value < current_value:
            return ["stability improves", "may require heavier ballast or layout changes"]
    return []

