"""
magnet/core/parameter_bounds.py - Parameter bounds for refinement clamping.

CLI v1 Foundation: Kernel-owned bounds for parameter validation.
All refinement clamping logic lives here - NOT in UI/CLI.
"""

from typing import Any, List, Tuple


PARAMETER_BOUNDS = {
    "mission.max_speed_kts": {"min": 0, "max": 100, "type": float},
    "mission.crew_berthed": {"min": 0, "max": 100, "type": int},
    "mission.range_nm": {"min": 0, "max": 10000, "type": float},
    "hull.loa": {"min": 5, "max": 200, "type": float},
    "mission.cargo_capacity_mt": {"min": 0, "max": 10000, "type": float},
}


def validate_and_clamp(path: str, value: Any) -> Tuple[Any, List[str]]:
    """
    Validate and clamp parameter value to kernel-defined bounds.

    Args:
        path: State path (e.g., "mission.max_speed_kts")
        value: Value to validate and clamp

    Returns:
        Tuple of (clamped_value, warnings)
        - clamped_value: Value clamped to bounds and cast to correct type
        - warnings: List of warning messages if value was clamped
    """
    bounds = PARAMETER_BOUNDS.get(
        path,
        {"min": float("-inf"), "max": float("inf"), "type": float}
    )
    warnings = []

    # Clamp to bounds
    clamped = max(bounds["min"], min(bounds["max"], value))

    if clamped != value:
        warnings.append(f"{path} clamped from {value} to {clamped}")

    # Cast to correct type
    return bounds["type"](clamped), warnings


def get_bounds(path: str) -> dict:
    """
    Get bounds for a parameter path.

    Args:
        path: State path (e.g., "mission.max_speed_kts")

    Returns:
        Dict with min, max, type keys
    """
    return PARAMETER_BOUNDS.get(
        path,
        {"min": float("-inf"), "max": float("inf"), "type": float}
    )
