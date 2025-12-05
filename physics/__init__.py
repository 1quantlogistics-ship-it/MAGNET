"""
MAGNET V1 Physics Module (ALPHA)

Physics simulation and calculations for naval vessel design.

Submodules:
- hydrostatics: Displacement, stability, buoyancy
- resistance: Resistance prediction, power estimation
- weight: Weight estimation and distribution
- structural: Scantling calculations (ABS HSNC 2023)
"""

from .hydrostatics import (
    calculate_displacement,
    calculate_wetted_surface_from_hull,
    calculate_wetted_surface_holtrop,
    calculate_stability,
    calculate_stability_from_hull,
    StabilityResult,
)

from .resistance import (
    calculate_total_resistance,
    estimate_speed_power_curve,
    ResistanceResult,
)

from .weight import (
    calculate_lightship_weight,
    calculate_deadweight,
    calculate_displacement_balance,
    calculate_weight_distribution,
    LightshipResult,
    DeadweightResult,
    DisplacementBalance,
    WeightDistribution,
    WeightItem,
)

from .structural import (
    AluminumAlloy,
    ALLOWED_ALLOYS,
    PROHIBITED_ALLOYS,
    get_alloy_properties,
    PressureZone,
    calculate_design_pressure,
    calculate_all_zone_pressures,
    generate_plating_schedule,
    PlatingSchedule,
    calculate_all_stiffeners,
    StiffenerResult,
)

__all__ = [
    # Hydrostatics
    'calculate_displacement',
    'calculate_wetted_surface_from_hull',
    'calculate_wetted_surface_holtrop',
    'calculate_stability',
    'calculate_stability_from_hull',
    'StabilityResult',
    # Resistance
    'calculate_total_resistance',
    'estimate_speed_power_curve',
    'ResistanceResult',
    # Weight
    'calculate_lightship_weight',
    'calculate_deadweight',
    'calculate_displacement_balance',
    'calculate_weight_distribution',
    'LightshipResult',
    'DeadweightResult',
    'DisplacementBalance',
    'WeightDistribution',
    'WeightItem',
    # Structural
    'AluminumAlloy',
    'ALLOWED_ALLOYS',
    'PROHIBITED_ALLOYS',
    'get_alloy_properties',
    'PressureZone',
    'calculate_design_pressure',
    'calculate_all_zone_pressures',
    'generate_plating_schedule',
    'PlatingSchedule',
    'calculate_all_stiffeners',
    'StiffenerResult',
]
