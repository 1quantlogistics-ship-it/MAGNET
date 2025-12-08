"""
MAGNET Weight Utilities

Module 07 v1.1 - Production-Ready

Utility functions for weight estimation module.

v1.1 FIX #6: determinize_dict() for hash-stable summary_data.
"""

from __future__ import annotations
import json
from typing import Any, Dict


def determinize_dict(data: Dict[str, Any], precision: int = 6) -> Dict[str, Any]:
    """
    Make a dictionary deterministic for hashing and caching.

    v1.1 FIX #6: Ensures summary_data is hash-stable.

    Operations:
    - Sorts all keys recursively
    - Rounds floats to consistent precision
    - Ensures consistent JSON serialization

    Args:
        data: Dictionary to determinize
        precision: Float rounding precision (default: 6)

    Returns:
        Deterministic dictionary with sorted keys and rounded floats
    """
    def _process(obj: Any) -> Any:
        if isinstance(obj, float):
            return round(obj, precision)
        elif isinstance(obj, dict):
            return {k: _process(v) for k, v in sorted(obj.items())}
        elif isinstance(obj, list):
            return [_process(item) for item in obj]
        elif isinstance(obj, (int, str, bool, type(None))):
            return obj
        else:
            # Convert unknown types to string
            return str(obj)

    processed = _process(data)
    # Serialize and deserialize to ensure consistent structure
    return json.loads(json.dumps(processed, sort_keys=True))


def calculate_weighted_average(
    values: list,
    weights: list,
    default: float = 0.0
) -> float:
    """
    Calculate weighted average of values.

    Args:
        values: List of values
        weights: List of weights (same length as values)
        default: Default value if weights sum to zero

    Returns:
        Weighted average or default
    """
    if len(values) != len(weights):
        raise ValueError("Values and weights must have same length")

    total_weight = sum(weights)
    if total_weight <= 0:
        return default

    weighted_sum = sum(v * w for v, w in zip(values, weights))
    return weighted_sum / total_weight


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safe division that returns default if denominator is zero.

    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value for division by zero

    Returns:
        Result of division or default
    """
    if abs(denominator) < 1e-10:
        return default
    return numerator / denominator
