"""
MAGNET V1 Hydrostatics Submodule (ALPHA)

Hydrostatic calculations: displacement, buoyancy, stability.
"""

from .displacement import (
    calculate_displacement,
    calculate_volume,
    calculate_wetted_surface_holtrop,
    calculate_wetted_surface_simple,
    calculate_wetted_surface_from_hull,
    calculate_waterplane_area,
    calculate_midship_area,
    calculate_tons_per_cm_immersion,
    calculate_moment_to_change_trim,
    SEAWATER_DENSITY,
)

from .stability import (
    calculate_stability,
    calculate_stability_from_hull,
    calculate_GM,
    calculate_KB_morrish,
    calculate_BM_transverse,
    calculate_GZ_curve,
    check_IMO_A749_criteria,
    generate_stability_report,
    StabilityResult,
)

__all__ = [
    # Displacement
    'calculate_displacement',
    'calculate_volume',
    'calculate_wetted_surface_holtrop',
    'calculate_wetted_surface_simple',
    'calculate_wetted_surface_from_hull',
    'calculate_waterplane_area',
    'calculate_midship_area',
    'calculate_tons_per_cm_immersion',
    'calculate_moment_to_change_trim',
    'SEAWATER_DENSITY',
    # Stability
    'calculate_stability',
    'calculate_stability_from_hull',
    'calculate_GM',
    'calculate_KB_morrish',
    'calculate_BM_transverse',
    'calculate_GZ_curve',
    'check_IMO_A749_criteria',
    'generate_stability_report',
    'StabilityResult',
]
