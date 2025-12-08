"""
MAGNET Stability Calculations Framework

Module 06 v1.2 - Production-Ready

Provides intact stability, GZ curves, damage stability, and weather criterion.

v1.2 Changes:
- KG sourcing priority: stability.kg_m then weight.lightship_vcg_m
- All IMO IS Code criteria implemented
- Simplified damage stability using lost buoyancy method
"""

from .constants import (
    IMO_INTACT,
    IMO_WEATHER,
    USCG_SUBT,
    ABS_HSV,
    IMOIntactCriteria,
    IMOWeatherCriteria,
    USCGSubchapterTCriteria,
    ABSHSVCriteria,
    GZ_CURVE_ANGLES_DEG,
    check_imo_intact_criteria,
    check_uscg_subt_criteria,
)

from .results import (
    GMResults,
    GZCurveResults,
    GZCurvePoint,
    DamageResults,
    DamageCase,
    WeatherCriterionResults,
    TankFreeSurface,
)

from .calculators import (
    IntactGMCalculator,
    GZCurveCalculator,
    FreeSurfaceCalculator,
    DamageStabilityCalculator,
    WeatherCriterionCalculator,
)

from .validators import (
    IntactGMValidator,
    GZCurveValidator,
    DamageStabilityValidator,
    WeatherCriterionValidator,
    get_intact_gm_definition,
    get_gz_curve_definition,
    get_damage_stability_definition,
    get_weather_criterion_definition,
    register_stability_validators,
)

__all__ = [
    # IMO Criteria
    "IMO_INTACT",
    "IMO_WEATHER",
    "USCG_SUBT",
    "ABS_HSV",
    "IMOIntactCriteria",
    "IMOWeatherCriteria",
    "USCGSubchapterTCriteria",
    "ABSHSVCriteria",
    "GZ_CURVE_ANGLES_DEG",
    "check_imo_intact_criteria",
    "check_uscg_subt_criteria",
    # Results
    "GMResults",
    "GZCurveResults",
    "GZCurvePoint",
    "DamageResults",
    "DamageCase",
    "WeatherCriterionResults",
    "TankFreeSurface",
    # Calculators
    "IntactGMCalculator",
    "GZCurveCalculator",
    "FreeSurfaceCalculator",
    "DamageStabilityCalculator",
    "WeatherCriterionCalculator",
    # Validators
    "IntactGMValidator",
    "GZCurveValidator",
    "DamageStabilityValidator",
    "WeatherCriterionValidator",
    # Definitions
    "get_intact_gm_definition",
    "get_gz_curve_definition",
    "get_damage_stability_definition",
    "get_weather_criterion_definition",
    # Registration
    "register_stability_validators",
]
