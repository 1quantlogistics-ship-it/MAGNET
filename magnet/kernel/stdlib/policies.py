"""
DERIVE policy implementations.

IMPORTANT: All DERIVE policies are OPTIONAL.
Agents can SET values directly - policies are conveniences, not requirements.

These policies encode design HEURISTICS, not physics laws.
The kernel validates physics AFTER these values are set.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class PolicyContract:
    """Contract for a DERIVE policy."""
    name: str
    description: str
    required_inputs: List[str]
    optional_inputs: List[str]
    output_type: str  # "float", "dict", "list"
    computation_type: str  # "arithmetic", "heuristic", "lookup", "iterative"
    
    
class PolicyError(Exception):
    """Raised when policy invocation fails."""
    pass


# =============================================================================
# POLICY REGISTRY
# =============================================================================

_POLICIES: Dict[str, Callable] = {}


def register_policy(name: str):
    """Decorator to register a policy function."""
    def decorator(func):
        _POLICIES[name] = func
        return func
    return decorator


def invoke_policy(name: str, inputs: Dict[str, Any]) -> Any:
    """Invoke a named policy with inputs."""
    if name not in _POLICIES:
        raise PolicyError(f"Unknown policy: {name}")
    
    policy_func = _POLICIES[name]
    try:
        return policy_func(inputs)
    except Exception as e:
        raise PolicyError(f"Policy '{name}' failed: {e}")


def list_policies() -> List[str]:
    """List all registered policies."""
    return list(_POLICIES.keys())


# =============================================================================
# CORE HULL POLICIES (ALL OPTIONAL)
# =============================================================================
# 
# These encode design heuristics, not physics.
# Agent provides the ratio/target, NOT hull type.
# No hull_type lookups - that would be enumeration.
# =============================================================================

@register_policy("lb_ratio")
def lb_ratio_policy(inputs: Dict[str, Any]) -> float:
    """
    Derive beam from length and target L/B ratio.
    
    Inputs:
        loa: Length overall (m)
        target_ratio: Desired L/B ratio (agent-specified, not from hull type!)
    
    Returns:
        Beam (m)
    
    NOTE: Agent specifies ratio directly. No hull_type lookup.
    """
    loa = inputs.get("loa")
    target_ratio = inputs.get("target_ratio")
    
    if loa is None:
        raise PolicyError("lb_ratio requires 'loa' input")
    if target_ratio is None:
        raise PolicyError("lb_ratio requires 'target_ratio' input")
    
    loa = float(loa)
    target_ratio = float(target_ratio)
    
    if target_ratio <= 0:
        raise PolicyError("target_ratio must be positive")
    
    return loa / target_ratio


@register_policy("displacement_beam")
def displacement_beam_policy(inputs: Dict[str, Any]) -> float:
    """
    Derive beam from displacement and waterline length.
    
    Uses the relationship: Δ ≈ Cb × L × B × T
    Solving for B given approximate Cb and draft estimate.
    
    Inputs:
        displacement_m3: Target displacement volume (m³)
        lwl: Waterline length (m)
        draft: Estimated draft (m), optional
        cb: Block coefficient estimate, optional
    
    Returns:
        Beam estimate (m)
    """
    disp = inputs.get("displacement_m3")
    lwl = inputs.get("lwl")
    
    if disp is None or lwl is None:
        raise PolicyError("displacement_beam requires 'displacement_m3' and 'lwl'")
    
    disp = float(disp)
    lwl = float(lwl)
    
    # Use provided or estimated values
    cb = float(inputs.get("cb", 0.5))
    draft = float(inputs.get("draft", lwl / 15))  # Rough estimate
    
    if cb <= 0 or draft <= 0 or lwl <= 0:
        raise PolicyError("Invalid parameters for displacement_beam")
    
    # B = Δ / (Cb × L × T)
    beam = disp / (cb * lwl * draft)
    return beam


@register_policy("gm_beam")
def gm_beam_policy(inputs: Dict[str, Any]) -> float:
    """
    Derive beam from GM requirement (iterative).
    
    This is a simplified approximation. For accurate GM:
    - Agent should SET values directly
    - Kernel validates actual GM after geometry compilation
    
    Inputs:
        gm_required_m: Required metacentric height (m)
        draft: Draft (m)
        displacement_m3: Displacement volume (m³)
    
    Returns:
        Beam estimate (m)
    """
    gm_req = inputs.get("gm_required_m")
    draft = inputs.get("draft")
    disp = inputs.get("displacement_m3")
    
    if None in (gm_req, draft, disp):
        raise PolicyError("gm_beam requires gm_required_m, draft, displacement_m3")
    
    gm_req = float(gm_req)
    draft = float(draft)
    disp = float(disp)
    
    # Very rough approximation: BM ≈ B² / (12 × T) for box-like section
    # GM = KB + BM - KG
    # Assuming KB ≈ 0.53T, KG ≈ 0.6T (typical)
    # GM ≈ 0.53T + B²/(12T) - 0.6T = B²/(12T) - 0.07T
    # B² = 12T × (GM + 0.07T)
    
    bm_needed = gm_req + 0.07 * draft
    if bm_needed <= 0:
        raise PolicyError("Cannot achieve requested GM with given draft")
    
    beam_squared = 12 * draft * bm_needed
    beam = beam_squared ** 0.5
    
    return beam


@register_policy("froude_draft")
def froude_draft_policy(inputs: Dict[str, Any]) -> float:
    """
    Derive draft from length and target Froude number.
    
    Inputs:
        loa: Length overall (m)
        speed_kts: Design speed (knots)
        target_fn: Target Froude number, optional
    
    Returns:
        Draft estimate (m)
    """
    loa = inputs.get("loa")
    speed_kts = inputs.get("speed_kts")
    
    if loa is None or speed_kts is None:
        raise PolicyError("froude_draft requires 'loa' and 'speed_kts'")
    
    loa = float(loa)
    speed_kts = float(speed_kts)
    
    # Convert knots to m/s
    speed_ms = speed_kts * 0.514444
    g = 9.81
    
    # Fn = V / sqrt(g × L)
    # Use LWL ≈ 0.95 × LOA
    lwl = 0.95 * loa
    fn = speed_ms / (g * lwl) ** 0.5
    
    # Heuristic draft based on Froude regime
    # Higher Fn → shallower draft (planing)
    # Lower Fn → deeper draft (displacement)
    if fn > 0.8:
        # Planing regime: shallow draft
        draft = loa / 20
    elif fn > 0.5:
        # Semi-planing: moderate draft
        draft = loa / 12
    else:
        # Displacement: deeper draft
        draft = loa / 10
    
    return draft


@register_policy("body_offset")
def body_offset_policy(inputs: Dict[str, Any]) -> Dict[str, float]:
    """
    Derive body offset for multi-body configurations.
    
    Inputs:
        beam: Overall beam (m)
        spacing_ratio: Spacing as ratio of beam
        position: "port" or "starboard"
    
    Returns:
        Dict with offset_y_m
    """
    beam = inputs.get("beam")
    spacing_ratio = inputs.get("spacing_ratio", 0.8)
    position = inputs.get("position", "port")
    
    if beam is None:
        raise PolicyError("body_offset requires 'beam'")
    
    beam = float(beam)
    spacing_ratio = float(spacing_ratio)
    
    offset = (beam * spacing_ratio) / 2
    if position.lower() == "starboard":
        offset = -offset
    
    return {"offset_y_m": offset}


# =============================================================================
# PHYSICS VALIDATION POLICIES (NOT design heuristics)
# =============================================================================
# These validate geometry/physics, not design intent

@register_policy("flow_area_adequacy")
def flow_area_adequacy_policy(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if flow path area is adequate for conditions.
    
    This is a VALIDATION policy, not a design heuristic.
    
    Inputs:
        cross_section_m2: Flow area
        medium: "air", "water", etc.
        flow_rate_m3s: Required flow rate (optional)
    
    Returns:
        Dict with adequacy ratio and assessment
    """
    area = inputs.get("cross_section_m2", 0)
    medium = inputs.get("medium", "air")
    flow_rate = inputs.get("flow_rate_m3s", None)
    
    area = float(area)
    
    if flow_rate is not None:
        # Calculate required velocity
        velocity = float(flow_rate) / area if area > 0 else float('inf')
        
        # Check against typical limits
        if medium.lower() in ("air", "exhaust"):
            max_velocity = 30  # m/s for air
        else:
            max_velocity = 5  # m/s for water
        
        adequacy = max_velocity / velocity if velocity > 0 else 1.0
    else:
        # Just check area is reasonable
        adequacy = 1.0 if area > 0.01 else 0.5
    
    return {
        "adequacy_ratio": min(adequacy, 2.0),
        "adequate": adequacy >= 1.0,
        "recommendation": None if adequacy >= 1.0 else "Increase flow area"
    }


@register_policy("discontinuity_interference")
def discontinuity_interference_policy(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if discontinuities interfere with each other.
    
    Inputs:
        discontinuities: List of discontinuity dicts
    
    Returns:
        Dict with interference assessment
    """
    discs = inputs.get("discontinuities", [])
    
    interferences = []
    for i, d1 in enumerate(discs):
        for j, d2 in enumerate(discs[i+1:], i+1):
            # Check station overlap
            if (d1.get("station_start", 0) <= d2.get("station_end", 1) and
                d1.get("station_end", 1) >= d2.get("station_start", 0)):
                # Check height proximity
                h1 = d1.get("height_ratio", 0.5)
                h2 = d2.get("height_ratio", 0.5)
                if abs(h1 - h2) < 0.1:
                    interferences.append({
                        "disc1": d1.get("_id", f"disc_{i}"),
                        "disc2": d2.get("_id", f"disc_{j}"),
                        "overlap_type": "height_conflict"
                    })
    
    return {
        "has_interference": len(interferences) > 0,
        "interferences": interferences
    }


# =============================================================================
# POLICY DOCUMENTATION
# =============================================================================

POLICY_DOCS = {
    "lb_ratio": PolicyContract(
        name="lb_ratio",
        description="Derive beam from length and target L/B ratio",
        required_inputs=["loa", "target_ratio"],
        optional_inputs=[],
        output_type="float",
        computation_type="arithmetic"
    ),
    "displacement_beam": PolicyContract(
        name="displacement_beam",
        description="Derive beam from displacement and waterline length",
        required_inputs=["displacement_m3", "lwl"],
        optional_inputs=["draft", "cb"],
        output_type="float",
        computation_type="arithmetic"
    ),
    "gm_beam": PolicyContract(
        name="gm_beam",
        description="Derive beam from GM requirement (iterative)",
        required_inputs=["gm_required_m", "draft", "displacement_m3"],
        optional_inputs=[],
        output_type="float",
        computation_type="iterative"
    ),
    "froude_draft": PolicyContract(
        name="froude_draft",
        description="Derive draft from length and speed",
        required_inputs=["loa", "speed_kts"],
        optional_inputs=["target_fn"],
        output_type="float",
        computation_type="heuristic"
    ),
    "body_offset": PolicyContract(
        name="body_offset",
        description="Derive body offset for multi-body configurations",
        required_inputs=["beam"],
        optional_inputs=["spacing_ratio", "position"],
        output_type="dict",
        computation_type="arithmetic"
    ),
}


