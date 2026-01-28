"""
TASK-021: Agent Guardrails — Reject Absurd Geometry

Sanity checks for LLM-proposed geometry to catch physically absurd values.

Rules:
- HARD_LIMITS: Reject immediately with error
- SOFT_LIMITS: Warn but allow (advisory)

This module ensures that technically valid but physically nonsensical
proposals are caught before they corrupt the design state.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import math
import logging

logger = logging.getLogger(__name__)


@dataclass
class SanityResult:
    """Result of sanity check."""
    passed: bool
    errors: List[str]  # Hard failures - reject proposal
    warnings: List[str]  # Soft failures - allow but warn


# =============================================================================
# HARD LIMITS (Reject immediately)
# =============================================================================

HARD_LIMITS = {
    # LOA absolute bounds
    "hull.loa": {"min": 3.0, "max": 500.0, "msg": "LOA {value}m is outside realistic vessel range (3-500m)"},
    "hull.lwl": {"min": 2.5, "max": 500.0, "msg": "LWL {value}m is outside realistic vessel range (2.5-500m)"},
    
    # Draft cannot be negative
    "hull.draft": {"min": 0.05, "max": 50.0, "msg": "Draft {value}m must be positive and realistic (0.05-50m)"},
    
    # Beam absolute bounds
    "hull.beam": {"min": 0.5, "max": 100.0, "msg": "Beam {value}m is outside realistic range (0.5-100m)"},
    
    # Depth must be positive
    "hull.depth": {"min": 0.1, "max": 60.0, "msg": "Depth {value}m must be positive and realistic (0.1-60m)"},
    
    # Form coefficients
    "hull.cb": {"min": 0.2, "max": 0.95, "msg": "Block coefficient {value} is outside valid range (0.2-0.95)"},
    "hull.cp": {"min": 0.3, "max": 0.98, "msg": "Prismatic coefficient {value} is outside valid range (0.3-0.98)"},
    "hull.cm": {"min": 0.5, "max": 1.0, "msg": "Midship coefficient {value} is outside valid range (0.5-1.0)"},
    "hull.cwp": {"min": 0.4, "max": 1.0, "msg": "Waterplane coefficient {value} is outside valid range (0.4-1.0)"},
    
    # Deadrise
    "hull.deadrise_deg": {"min": 0.0, "max": 45.0, "msg": "Deadrise {value}° is outside typical range (0-45°)"},
    "hull.deadrise_transom_deg": {"min": 0.0, "max": 45.0, "msg": "Transom deadrise {value}° is outside typical range (0-45°)"},
    
    # Section count
    "hull.section_count": {"min": 7, "max": 200, "msg": "Section count {value} is outside valid range (7-200)"},
    
    # Body count
    "hull.body_count": {"min": 1, "max": 5, "msg": "Body count {value} exceeds supported configurations (1-5)"},
    "hull.num_hulls": {"min": 1, "max": 5, "msg": "Hull count {value} exceeds supported configurations (1-5)"},
    
    # Speed
    "mission.max_speed_kts": {"min": 1.0, "max": 100.0, "msg": "Speed {value} kts is outside realistic range (1-100 kts)"},
    
    # Range
    "mission.range_nm": {"min": 1.0, "max": 20000.0, "msg": "Range {value} nm is outside realistic range (1-20000 nm)"},
}


# =============================================================================
# SOFT LIMITS (Warn but allow)
# =============================================================================

# These are checked relative to other parameters
RATIO_LIMITS = {
    "beam_to_loa": {
        "min": 0.08,
        "max": 0.5,
        "msg": "Beam/LOA ratio {value:.2f} is unusual — typical range is 0.08-0.5",
    },
    "draft_to_loa": {
        "min": 0.01,
        "max": 0.15,
        "msg": "Draft/LOA ratio {value:.2f} is unusual — typical range is 0.01-0.15",
    },
    "draft_to_beam": {
        "min": 0.05,
        "max": 0.8,
        "msg": "Draft/Beam ratio {value:.2f} is unusual — typical range is 0.05-0.8",
    },
    "depth_to_draft": {
        "min": 1.0,
        "max": 3.0,
        "msg": "Depth/Draft ratio {value:.2f} is unusual — typical range is 1.0-3.0",
    },
}


def check_hard_limits(path: str, value: Any) -> Tuple[bool, Optional[str]]:
    """
    Check if a value violates hard limits.
    
    Returns:
        (passed, error_message)
    """
    if path not in HARD_LIMITS:
        return True, None
    
    if value is None:
        return True, None
    
    try:
        val = float(value)
    except (TypeError, ValueError):
        return True, None  # Non-numeric values not checked here
    
    limits = HARD_LIMITS[path]
    min_val = limits.get("min")
    max_val = limits.get("max")
    msg_template = limits.get("msg", f"{path} value {value} is out of range")
    
    if min_val is not None and val < min_val:
        return False, msg_template.format(value=val)
    
    if max_val is not None and val > max_val:
        return False, msg_template.format(value=val)
    
    return True, None


def check_ratio_limits(state_dict: Dict[str, Any]) -> List[str]:
    """
    Check ratio-based soft limits.
    
    Returns list of warning messages.
    """
    warnings = []
    
    # Extract values
    loa = state_dict.get("hull", {}).get("loa") or state_dict.get("hull", {}).get("lwl")
    beam = state_dict.get("hull", {}).get("beam")
    draft = state_dict.get("hull", {}).get("draft")
    depth = state_dict.get("hull", {}).get("depth")
    
    # Beam/LOA ratio
    if loa and beam and loa > 0:
        ratio = beam / loa
        limits = RATIO_LIMITS["beam_to_loa"]
        if ratio < limits["min"] or ratio > limits["max"]:
            warnings.append(limits["msg"].format(value=ratio))
    
    # Draft/LOA ratio
    if loa and draft and loa > 0:
        ratio = draft / loa
        limits = RATIO_LIMITS["draft_to_loa"]
        if ratio < limits["min"] or ratio > limits["max"]:
            warnings.append(limits["msg"].format(value=ratio))
    
    # Draft/Beam ratio
    if beam and draft and beam > 0:
        ratio = draft / beam
        limits = RATIO_LIMITS["draft_to_beam"]
        if ratio < limits["min"] or ratio > limits["max"]:
            warnings.append(limits["msg"].format(value=ratio))
    
    # Depth/Draft ratio
    if depth and draft and draft > 0:
        ratio = depth / draft
        limits = RATIO_LIMITS["depth_to_draft"]
        if ratio < limits["min"] or ratio > limits["max"]:
            warnings.append(limits["msg"].format(value=ratio))
    
    return warnings


def check_froude_number(speed_kts: float, lwl_m: float) -> List[str]:
    """
    Check if Froude number is realistic.
    
    Returns list of warning messages.
    """
    warnings = []
    
    if lwl_m <= 0:
        return warnings
    
    # Calculate Froude number
    speed_ms = speed_kts * 0.514444
    fn = speed_ms / math.sqrt(9.81 * lwl_m)
    
    if fn > 3.0:
        warnings.append(f"Froude number {fn:.2f} exceeds hydrofoil range (typical max ~3.0)")
    elif fn > 1.5:
        warnings.append(f"Froude number {fn:.2f} indicates very high speed regime")
    
    return warnings


def check_sanity(
    path: str,
    value: Any,
    state_dict: Optional[Dict[str, Any]] = None,
) -> SanityResult:
    """
    Check a single value for sanity.
    
    Args:
        path: State path being set
        value: Value being set
        state_dict: Current state dictionary for ratio checks
        
    Returns:
        SanityResult with errors and warnings
    """
    errors = []
    warnings = []
    
    # Check hard limits
    passed, error = check_hard_limits(path, value)
    if not passed and error:
        errors.append(error)
    
    # If we have state context, check ratios
    if state_dict:
        # Create a merged state with the new value
        merged = dict(state_dict)
        parts = path.split(".")
        if len(parts) == 2:
            section, key = parts
            if section not in merged:
                merged[section] = {}
            merged[section][key] = value
        
        # Check ratios
        ratio_warnings = check_ratio_limits(merged)
        warnings.extend(ratio_warnings)
        
        # Check Froude number if speed or length changed
        if path in ("mission.max_speed_kts", "hull.lwl", "hull.loa"):
            speed = merged.get("mission", {}).get("max_speed_kts")
            lwl = merged.get("hull", {}).get("lwl") or merged.get("hull", {}).get("loa")
            if speed and lwl:
                fn_warnings = check_froude_number(float(speed), float(lwl) * 0.95)
                warnings.extend(fn_warnings)
    
    return SanityResult(
        passed=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def check_proposal_sanity(
    updates: Dict[str, Any],
    state_dict: Optional[Dict[str, Any]] = None,
) -> SanityResult:
    """
    Check a batch of proposed updates for sanity.
    
    Args:
        updates: Dictionary of path -> value updates
        state_dict: Current state dictionary
        
    Returns:
        SanityResult with aggregated errors and warnings
    """
    all_errors = []
    all_warnings = []
    
    # Create merged state for ratio checks
    merged_state = dict(state_dict) if state_dict else {}
    
    # Check each update
    for path, value in updates.items():
        result = check_sanity(path, value, merged_state)
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)
        
        # Update merged state for subsequent checks
        parts = path.split(".")
        if len(parts) == 2:
            section, key = parts
            if section not in merged_state:
                merged_state[section] = {}
            merged_state[section][key] = value
    
    # Deduplicate warnings
    unique_warnings = list(dict.fromkeys(all_warnings))
    
    return SanityResult(
        passed=len(all_errors) == 0,
        errors=all_errors,
        warnings=unique_warnings,
    )
