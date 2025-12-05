"""
Structural scantlings module for naval architecture.

Implements ABS HSNC (High Speed Naval Craft) 2023 structural calculations:
- Design pressures (slamming, hydrostatic)
- Plate thickness requirements
- Stiffener section modulus
- Frame spacing
- Material properties with HAZ derating

References:
- ABS Rules for Building and Classing High-Speed Naval Craft (HSNC) 2023
- DNV Rules for Classification of High Speed and Light Craft (HSLC) 2023
"""

from .materials import (
    AluminumAlloy,
    ALLOWED_ALLOYS,
    PROHIBITED_ALLOYS,
    get_alloy_properties,
    get_haz_factor,
    MaterialProperties,
)
from .pressure import (
    calculate_hydrostatic_pressure,
    calculate_slamming_pressure,
    calculate_design_pressure,
    calculate_all_zone_pressures,
    PressureResult,
    PressureZone,
)
from .plating import (
    calculate_plate_thickness,
    calculate_minimum_thickness,
    generate_plating_schedule,
    PlatingResult,
    PlatingSchedule,
)
from .stiffeners import (
    calculate_stiffener_section_modulus,
    calculate_frame_spacing,
    select_stiffener_profile,
    calculate_all_stiffeners,
    StiffenerResult,
    StiffenerProfile,
)

__all__ = [
    # Materials
    "AluminumAlloy",
    "ALLOWED_ALLOYS",
    "PROHIBITED_ALLOYS",
    "get_alloy_properties",
    "get_haz_factor",
    "MaterialProperties",
    # Pressure
    "calculate_hydrostatic_pressure",
    "calculate_slamming_pressure",
    "calculate_design_pressure",
    "calculate_all_zone_pressures",
    "PressureResult",
    "PressureZone",
    # Plating
    "calculate_plate_thickness",
    "calculate_minimum_thickness",
    "generate_plating_schedule",
    "PlatingResult",
    "PlatingSchedule",
    # Stiffeners
    "calculate_stiffener_section_modulus",
    "calculate_frame_spacing",
    "select_stiffener_profile",
    "calculate_all_stiffeners",
    "StiffenerResult",
    "StiffenerProfile",
]
