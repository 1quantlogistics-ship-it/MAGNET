"""
MAGNET Stability Constants

Module 06 v1.2 - Production-Ready

IMO stability criteria and physical constants for stability calculations.

References:
- IMO IS Code (MSC.267(85)) Part A, Section 2.2 - Intact Stability Criteria
- IMO IS Code Part A, Section 2.3 - Severe Wind and Rolling Criterion
- USCG 46 CFR Subchapter T (Small Passenger Vessels)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List


# =============================================================================
# IMO INTACT STABILITY CRITERIA (IS CODE 2.2)
# =============================================================================

@dataclass(frozen=True)
class IMOIntactCriteria:
    """
    IMO Intact Stability Criteria per IS Code Part A, Section 2.2.

    These criteria apply to all ships to which the 2008 IS Code applies.
    """
    # Metacentric height
    gm_min_m: float = 0.15  # Minimum GM (meters)

    # GZ curve criteria
    gz_30_min_m: float = 0.20  # Minimum GZ at 30° heel (meters)
    angle_gz_max_min_deg: float = 25.0  # Minimum angle of maximum GZ (degrees)

    # Area under GZ curve criteria (meter-radians)
    area_0_30_min_m_rad: float = 0.055  # Area from 0° to 30°
    area_0_40_min_m_rad: float = 0.090  # Area from 0° to 40°
    area_30_40_min_m_rad: float = 0.030  # Area from 30° to 40°

    # Angle of vanishing stability
    # Note: No specific minimum in IS Code 2.2, but typically > 60° desired

    def to_dict(self) -> Dict[str, float]:
        return {
            "gm_min_m": self.gm_min_m,
            "gz_30_min_m": self.gz_30_min_m,
            "angle_gz_max_min_deg": self.angle_gz_max_min_deg,
            "area_0_30_min_m_rad": self.area_0_30_min_m_rad,
            "area_0_40_min_m_rad": self.area_0_40_min_m_rad,
            "area_30_40_min_m_rad": self.area_30_40_min_m_rad,
        }


# Singleton instance
IMO_INTACT = IMOIntactCriteria()


# =============================================================================
# IMO WEATHER CRITERION (IS CODE 2.3)
# =============================================================================

@dataclass(frozen=True)
class IMOWeatherCriteria:
    """
    IMO Severe Wind and Rolling Criterion per IS Code Part A, Section 2.3.

    The vessel must satisfy: b >= a
    where:
    - a = area under heeling lever curve (wind heeling)
    - b = area under righting lever curve (GZ)
    """
    # Wind pressure (Pa) - typical value
    wind_pressure_pa: float = 504.0  # 504 Pa = ~50 kgf/m²

    # Energy ratio requirement
    energy_ratio_min: float = 1.0  # b/a >= 1.0

    # Roll back angle factor (typically 1.0)
    roll_back_factor: float = 1.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "wind_pressure_pa": self.wind_pressure_pa,
            "energy_ratio_min": self.energy_ratio_min,
            "roll_back_factor": self.roll_back_factor,
        }


# Singleton instance
IMO_WEATHER = IMOWeatherCriteria()


# =============================================================================
# USCG SUBCHAPTER T CRITERIA (46 CFR)
# =============================================================================

@dataclass(frozen=True)
class USCGSubchapterTCriteria:
    """
    USCG Stability Criteria for Small Passenger Vessels (< 100 GT).

    Per 46 CFR Subchapter T (46 CFR 178).
    """
    # Metacentric height
    gm_min_m: float = 0.35  # Higher than IMO for passenger vessels

    # Maximum heel angles
    passenger_heel_max_deg: float = 14.0  # With passengers moved to one side
    wind_heel_max_deg: float = 14.0  # Under design wind

    # GZ requirements
    gz_max_min_m: float = 0.20  # Minimum maximum GZ
    range_min_deg: float = 60.0  # Minimum range of positive stability

    def to_dict(self) -> Dict[str, float]:
        return {
            "gm_min_m": self.gm_min_m,
            "passenger_heel_max_deg": self.passenger_heel_max_deg,
            "wind_heel_max_deg": self.wind_heel_max_deg,
            "gz_max_min_m": self.gz_max_min_m,
            "range_min_deg": self.range_min_deg,
        }


# Singleton instance
USCG_SUBT = USCGSubchapterTCriteria()


# =============================================================================
# ABS HSV CRITERIA
# =============================================================================

@dataclass(frozen=True)
class ABSHSVCriteria:
    """
    ABS High Speed Vessel Stability Criteria.

    Per ABS Rules for Building and Classing High-Speed Craft.
    """
    # Metacentric height
    gm_min_m: float = 0.50  # Higher for high-speed craft

    # Passenger heel (if applicable)
    passenger_heel_max_deg: float = 10.0

    # Dynamic stability
    # Area under GZ to 40° or flooding angle
    area_min_m_rad: float = 0.09

    def to_dict(self) -> Dict[str, float]:
        return {
            "gm_min_m": self.gm_min_m,
            "passenger_heel_max_deg": self.passenger_heel_max_deg,
            "area_min_m_rad": self.area_min_m_rad,
        }


# Singleton instance
ABS_HSV = ABSHSVCriteria()


# =============================================================================
# FREE SURFACE CONSTANTS
# =============================================================================

# Tank fill levels that contribute to free surface
FSC_FILL_MIN = 0.15  # 15% fill - below this, tank considered empty
FSC_FILL_MAX = 0.85  # 85% fill - above this, tank considered pressed full

# Seawater density for FSC calculations
RHO_SEAWATER_KG_M3 = 1025.0

# Fresh water density
RHO_FRESHWATER_KG_M3 = 1000.0

# Fuel oil density (typical)
RHO_FUEL_KG_M3 = 900.0


# =============================================================================
# GZ CURVE GENERATION
# =============================================================================

# Standard heel angles for GZ curve (degrees)
# Note: Limited to 80° because wall-sided formula becomes unrealistic at higher angles
# tan(90°) = infinity which breaks the formula
GZ_CURVE_ANGLES_DEG: List[float] = [
    0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0,
    35.0, 40.0, 45.0, 50.0, 55.0, 60.0, 70.0, 80.0
]

# Wall-sided formula validity limit
WALL_SIDED_VALID_DEG = 45.0  # Accurate up to ~45° heel


# =============================================================================
# CRITERIA CHECKING FUNCTIONS
# =============================================================================

def check_imo_intact_criteria(
    gm_m: float,
    gz_30_m: float,
    gz_max_m: float,
    angle_gz_max_deg: float,
    area_0_30_m_rad: float,
    area_0_40_m_rad: float,
    area_30_40_m_rad: float,
    criteria: IMOIntactCriteria = IMO_INTACT,
) -> Dict[str, Any]:
    """
    Check IMO intact stability criteria.

    Args:
        gm_m: Metacentric height (meters)
        gz_30_m: GZ at 30° heel (meters)
        gz_max_m: Maximum GZ value (meters)
        angle_gz_max_deg: Angle of maximum GZ (degrees)
        area_0_30_m_rad: Area under GZ curve 0-30° (m-rad)
        area_0_40_m_rad: Area under GZ curve 0-40° (m-rad)
        area_30_40_m_rad: Area under GZ curve 30-40° (m-rad)
        criteria: Criteria to check against (default IMO_INTACT)

    Returns:
        Dictionary with pass/fail for each criterion and overall result
    """
    results = {
        "gm_pass": gm_m >= criteria.gm_min_m,
        "gm_actual": gm_m,
        "gm_required": criteria.gm_min_m,

        "gz_30_pass": gz_30_m >= criteria.gz_30_min_m,
        "gz_30_actual": gz_30_m,
        "gz_30_required": criteria.gz_30_min_m,

        "angle_gz_max_pass": angle_gz_max_deg >= criteria.angle_gz_max_min_deg,
        "angle_gz_max_actual": angle_gz_max_deg,
        "angle_gz_max_required": criteria.angle_gz_max_min_deg,

        "area_0_30_pass": area_0_30_m_rad >= criteria.area_0_30_min_m_rad,
        "area_0_30_actual": area_0_30_m_rad,
        "area_0_30_required": criteria.area_0_30_min_m_rad,

        "area_0_40_pass": area_0_40_m_rad >= criteria.area_0_40_min_m_rad,
        "area_0_40_actual": area_0_40_m_rad,
        "area_0_40_required": criteria.area_0_40_min_m_rad,

        "area_30_40_pass": area_30_40_m_rad >= criteria.area_30_40_min_m_rad,
        "area_30_40_actual": area_30_40_m_rad,
        "area_30_40_required": criteria.area_30_40_min_m_rad,
    }

    # Overall pass requires all individual criteria to pass
    results["all_pass"] = all([
        results["gm_pass"],
        results["gz_30_pass"],
        results["angle_gz_max_pass"],
        results["area_0_30_pass"],
        results["area_0_40_pass"],
        results["area_30_40_pass"],
    ])

    return results


def check_uscg_subt_criteria(
    gm_m: float,
    passenger_heel_deg: float = 0.0,
    wind_heel_deg: float = 0.0,
    gz_max_m: float = 0.0,
    range_deg: float = 0.0,
    criteria: USCGSubchapterTCriteria = USCG_SUBT,
) -> Dict[str, Any]:
    """
    Check USCG Subchapter T stability criteria.

    Args:
        gm_m: Metacentric height (meters)
        passenger_heel_deg: Heel angle from passenger crowding (degrees)
        wind_heel_deg: Heel angle from wind heeling (degrees)
        gz_max_m: Maximum GZ value (meters)
        range_deg: Range of positive stability (degrees)
        criteria: Criteria to check against

    Returns:
        Dictionary with pass/fail for each criterion
    """
    results = {
        "gm_pass": gm_m >= criteria.gm_min_m,
        "gm_actual": gm_m,
        "gm_required": criteria.gm_min_m,

        "passenger_heel_pass": passenger_heel_deg <= criteria.passenger_heel_max_deg,
        "passenger_heel_actual": passenger_heel_deg,
        "passenger_heel_max": criteria.passenger_heel_max_deg,

        "wind_heel_pass": wind_heel_deg <= criteria.wind_heel_max_deg,
        "wind_heel_actual": wind_heel_deg,
        "wind_heel_max": criteria.wind_heel_max_deg,

        "gz_max_pass": gz_max_m >= criteria.gz_max_min_m,
        "gz_max_actual": gz_max_m,
        "gz_max_required": criteria.gz_max_min_m,

        "range_pass": range_deg >= criteria.range_min_deg,
        "range_actual": range_deg,
        "range_required": criteria.range_min_deg,
    }

    results["all_pass"] = all([
        results["gm_pass"],
        results["passenger_heel_pass"],
        results["wind_heel_pass"],
        results["gz_max_pass"],
        results["range_pass"],
    ])

    return results
