"""
MAGNET V1 Resistance Module (ALPHA)

Ship resistance prediction and power estimation.
"""

from .holtrop import (
    calculate_total_resistance,
    calculate_frictional_resistance,
    calculate_residuary_resistance,
    calculate_effective_power,
    calculate_delivered_power,
    estimate_speed_power_curve,
    ResistanceResult,
)

__all__ = [
    'calculate_total_resistance',
    'calculate_frictional_resistance',
    'calculate_residuary_resistance',
    'calculate_effective_power',
    'calculate_delivered_power',
    'estimate_speed_power_curve',
    'ResistanceResult',
]
