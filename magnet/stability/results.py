"""
MAGNET Stability Results

Module 06 v1.2 - Production-Ready

Result dataclasses for stability calculations.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import time


# =============================================================================
# GM RESULTS
# =============================================================================

@dataclass
class GMResults:
    """
    Results from intact GM calculation.

    GM = KB + BM - KG - FSC
    """
    # Primary result
    gm_m: float  # Metacentric height (meters)
    gm_solid_m: float  # GM without free surface correction

    # Component values
    kb_m: float  # Height of center of buoyancy from keel
    bm_m: float  # Metacentric radius
    kg_m: float  # Height of center of gravity from keel
    km_m: float  # Height of metacenter from keel (KB + BM)

    # Free surface correction
    fsc_m: float = 0.0  # Free surface correction (meters)
    has_fsc: bool = False  # Whether FSC was applied

    # KG sourcing
    kg_source: str = "unknown"  # "stability.kg_m", "weight.lightship_vcg_m", "estimated"

    # IMO criteria compliance
    passes_gm_criterion: bool = False  # GM >= 0.15m

    # Metadata
    calculation_time_ms: int = 0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gm_m": round(self.gm_m, 4),
            "gm_solid_m": round(self.gm_solid_m, 4),
            "kb_m": round(self.kb_m, 4),
            "bm_m": round(self.bm_m, 4),
            "kg_m": round(self.kg_m, 4),
            "km_m": round(self.km_m, 4),
            "fsc_m": round(self.fsc_m, 4),
            "has_fsc": self.has_fsc,
            "kg_source": self.kg_source,
            "passes_gm_criterion": self.passes_gm_criterion,
            "calculation_time_ms": self.calculation_time_ms,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GMResults":
        return cls(
            gm_m=data.get("gm_m", 0.0),
            gm_solid_m=data.get("gm_solid_m", 0.0),
            kb_m=data.get("kb_m", 0.0),
            bm_m=data.get("bm_m", 0.0),
            kg_m=data.get("kg_m", 0.0),
            km_m=data.get("km_m", 0.0),
            fsc_m=data.get("fsc_m", 0.0),
            has_fsc=data.get("has_fsc", False),
            kg_source=data.get("kg_source", "unknown"),
            passes_gm_criterion=data.get("passes_gm_criterion", False),
            calculation_time_ms=data.get("calculation_time_ms", 0),
            warnings=data.get("warnings", []),
        )


# =============================================================================
# GZ CURVE RESULTS
# =============================================================================

@dataclass
class GZCurvePoint:
    """A single point on the GZ curve."""
    heel_deg: float  # Heel angle (degrees)
    heel_rad: float  # Heel angle (radians)
    gz_m: float  # Righting arm (meters)

    def to_dict(self) -> Dict[str, float]:
        return {
            "heel_deg": round(self.heel_deg, 2),
            "heel_rad": round(self.heel_rad, 4),
            "gz_m": round(self.gz_m, 4),
        }


@dataclass
class GZCurveResults:
    """
    Results from GZ curve generation.

    Includes curve points, characteristic values, and IMO criteria compliance.
    """
    # GZ curve data
    curve: List[GZCurvePoint] = field(default_factory=list)

    # Characteristic values
    gz_max_m: float = 0.0  # Maximum righting arm
    angle_gz_max_deg: float = 0.0  # Angle of maximum GZ
    gz_30_m: float = 0.0  # GZ at 30° heel
    gz_40_m: float = 0.0  # GZ at 40° heel

    # Range of stability
    angle_of_vanishing_stability_deg: float = 90.0  # Where GZ becomes zero/negative
    range_of_stability_deg: float = 90.0  # Range of positive GZ

    # Areas under curve (meter-radians)
    area_0_30_m_rad: float = 0.0
    area_0_40_m_rad: float = 0.0
    area_30_40_m_rad: float = 0.0
    dynamic_stability_m_rad: float = 0.0  # Area to angle of max GZ

    # IMO criteria compliance
    passes_gz_30_criterion: bool = False  # GZ_30 >= 0.20m
    passes_angle_gz_max_criterion: bool = False  # Angle >= 25°
    passes_area_0_30_criterion: bool = False  # Area >= 0.055 m-rad
    passes_area_0_40_criterion: bool = False  # Area >= 0.090 m-rad
    passes_area_30_40_criterion: bool = False  # Area >= 0.030 m-rad
    passes_all_gz_criteria: bool = False  # All of above

    # Input parameters used
    gm_m: float = 0.0  # GM used for calculation
    bm_m: float = 0.0  # BM used for wall-sided formula

    # Metadata
    calculation_time_ms: int = 0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "curve": [p.to_dict() for p in self.curve],
            "gz_max_m": round(self.gz_max_m, 4),
            "angle_gz_max_deg": round(self.angle_gz_max_deg, 2),
            "gz_30_m": round(self.gz_30_m, 4),
            "gz_40_m": round(self.gz_40_m, 4),
            "angle_of_vanishing_stability_deg": round(self.angle_of_vanishing_stability_deg, 2),
            "range_of_stability_deg": round(self.range_of_stability_deg, 2),
            "area_0_30_m_rad": round(self.area_0_30_m_rad, 4),
            "area_0_40_m_rad": round(self.area_0_40_m_rad, 4),
            "area_30_40_m_rad": round(self.area_30_40_m_rad, 4),
            "dynamic_stability_m_rad": round(self.dynamic_stability_m_rad, 4),
            "passes_gz_30_criterion": self.passes_gz_30_criterion,
            "passes_angle_gz_max_criterion": self.passes_angle_gz_max_criterion,
            "passes_area_0_30_criterion": self.passes_area_0_30_criterion,
            "passes_area_0_40_criterion": self.passes_area_0_40_criterion,
            "passes_area_30_40_criterion": self.passes_area_30_40_criterion,
            "passes_all_gz_criteria": self.passes_all_gz_criteria,
            "gm_m": round(self.gm_m, 4),
            "bm_m": round(self.bm_m, 4),
            "calculation_time_ms": self.calculation_time_ms,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GZCurveResults":
        result = cls()
        result.curve = [
            GZCurvePoint(
                heel_deg=p.get("heel_deg", 0),
                heel_rad=p.get("heel_rad", 0),
                gz_m=p.get("gz_m", 0)
            )
            for p in data.get("curve", [])
        ]
        result.gz_max_m = data.get("gz_max_m", 0.0)
        result.angle_gz_max_deg = data.get("angle_gz_max_deg", 0.0)
        result.gz_30_m = data.get("gz_30_m", 0.0)
        result.gz_40_m = data.get("gz_40_m", 0.0)
        result.angle_of_vanishing_stability_deg = data.get("angle_of_vanishing_stability_deg", 90.0)
        result.range_of_stability_deg = data.get("range_of_stability_deg", 90.0)
        result.area_0_30_m_rad = data.get("area_0_30_m_rad", 0.0)
        result.area_0_40_m_rad = data.get("area_0_40_m_rad", 0.0)
        result.area_30_40_m_rad = data.get("area_30_40_m_rad", 0.0)
        result.dynamic_stability_m_rad = data.get("dynamic_stability_m_rad", 0.0)
        result.passes_gz_30_criterion = data.get("passes_gz_30_criterion", False)
        result.passes_angle_gz_max_criterion = data.get("passes_angle_gz_max_criterion", False)
        result.passes_area_0_30_criterion = data.get("passes_area_0_30_criterion", False)
        result.passes_area_0_40_criterion = data.get("passes_area_0_40_criterion", False)
        result.passes_area_30_40_criterion = data.get("passes_area_30_40_criterion", False)
        result.passes_all_gz_criteria = data.get("passes_all_gz_criteria", False)
        result.gm_m = data.get("gm_m", 0.0)
        result.bm_m = data.get("bm_m", 0.0)
        result.calculation_time_ms = data.get("calculation_time_ms", 0)
        result.warnings = data.get("warnings", [])
        return result


# =============================================================================
# DAMAGE STABILITY RESULTS
# =============================================================================

@dataclass
class DamageCase:
    """A single damage stability case."""
    case_id: str  # e.g., "forepeak", "engine_room"
    compartment: str  # Flooded compartment name
    permeability: float  # Flooding permeability (0-1)

    # Post-damage values
    residual_gm_m: float = 0.0  # GM after flooding
    residual_gz_max_m: float = 0.0  # Max GZ after flooding
    residual_range_deg: float = 0.0  # Range of stability
    heel_angle_deg: float = 0.0  # Equilibrium heel angle
    trim_m: float = 0.0  # Change in trim

    # Compliance
    passes_criteria: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "compartment": self.compartment,
            "permeability": round(self.permeability, 2),
            "residual_gm_m": round(self.residual_gm_m, 4),
            "residual_gz_max_m": round(self.residual_gz_max_m, 4),
            "residual_range_deg": round(self.residual_range_deg, 2),
            "heel_angle_deg": round(self.heel_angle_deg, 2),
            "trim_m": round(self.trim_m, 3),
            "passes_criteria": self.passes_criteria,
        }


@dataclass
class DamageResults:
    """
    Results from damage stability analysis.

    Uses lost buoyancy method for simplified damage assessment.
    """
    # Cases evaluated
    cases: List[DamageCase] = field(default_factory=list)
    cases_evaluated: int = 0

    # Worst case values
    worst_gm_m: float = 0.0
    worst_case_id: str = ""
    worst_gz_max_m: float = 0.0
    worst_range_deg: float = 0.0

    # Overall compliance
    all_cases_pass: bool = False
    failed_cases: List[str] = field(default_factory=list)

    # Metadata
    calculation_time_ms: int = 0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cases": [c.to_dict() for c in self.cases],
            "cases_evaluated": self.cases_evaluated,
            "worst_gm_m": round(self.worst_gm_m, 4),
            "worst_case_id": self.worst_case_id,
            "worst_gz_max_m": round(self.worst_gz_max_m, 4),
            "worst_range_deg": round(self.worst_range_deg, 2),
            "all_cases_pass": self.all_cases_pass,
            "failed_cases": self.failed_cases,
            "calculation_time_ms": self.calculation_time_ms,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DamageResults":
        result = cls()
        result.cases = [
            DamageCase(
                case_id=c.get("case_id", ""),
                compartment=c.get("compartment", ""),
                permeability=c.get("permeability", 0.85),
                residual_gm_m=c.get("residual_gm_m", 0.0),
                residual_gz_max_m=c.get("residual_gz_max_m", 0.0),
                residual_range_deg=c.get("residual_range_deg", 0.0),
                heel_angle_deg=c.get("heel_angle_deg", 0.0),
                trim_m=c.get("trim_m", 0.0),
                passes_criteria=c.get("passes_criteria", False),
            )
            for c in data.get("cases", [])
        ]
        result.cases_evaluated = data.get("cases_evaluated", 0)
        result.worst_gm_m = data.get("worst_gm_m", 0.0)
        result.worst_case_id = data.get("worst_case_id", "")
        result.worst_gz_max_m = data.get("worst_gz_max_m", 0.0)
        result.worst_range_deg = data.get("worst_range_deg", 0.0)
        result.all_cases_pass = data.get("all_cases_pass", False)
        result.failed_cases = data.get("failed_cases", [])
        result.calculation_time_ms = data.get("calculation_time_ms", 0)
        result.warnings = data.get("warnings", [])
        return result


# =============================================================================
# WEATHER CRITERION RESULTS
# =============================================================================

@dataclass
class WeatherCriterionResults:
    """
    Results from IMO severe wind and rolling criterion.

    Checks that energy area ratio b/a >= 1.0
    """
    # Energy areas
    heeling_area_a_m_rad: float = 0.0  # Area under heeling lever curve
    righting_area_b_m_rad: float = 0.0  # Area under righting lever curve

    # Result
    energy_ratio: float = 0.0  # b/a ratio
    passes_criterion: bool = False  # b/a >= 1.0

    # Roll characteristics
    roll_period_s: float = 0.0  # Natural roll period (seconds)
    roll_amplitude_deg: float = 0.0  # Estimated roll amplitude

    # Wind heeling
    wind_heel_lever_m: float = 0.0  # Wind heeling lever
    steady_wind_heel_deg: float = 0.0  # Steady heel from wind

    # Metadata
    calculation_time_ms: int = 0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "heeling_area_a_m_rad": round(self.heeling_area_a_m_rad, 4),
            "righting_area_b_m_rad": round(self.righting_area_b_m_rad, 4),
            "energy_ratio": round(self.energy_ratio, 3),
            "passes_criterion": self.passes_criterion,
            "roll_period_s": round(self.roll_period_s, 2),
            "roll_amplitude_deg": round(self.roll_amplitude_deg, 2),
            "wind_heel_lever_m": round(self.wind_heel_lever_m, 4),
            "steady_wind_heel_deg": round(self.steady_wind_heel_deg, 2),
            "calculation_time_ms": self.calculation_time_ms,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeatherCriterionResults":
        return cls(
            heeling_area_a_m_rad=data.get("heeling_area_a_m_rad", 0.0),
            righting_area_b_m_rad=data.get("righting_area_b_m_rad", 0.0),
            energy_ratio=data.get("energy_ratio", 0.0),
            passes_criterion=data.get("passes_criterion", False),
            roll_period_s=data.get("roll_period_s", 0.0),
            roll_amplitude_deg=data.get("roll_amplitude_deg", 0.0),
            wind_heel_lever_m=data.get("wind_heel_lever_m", 0.0),
            steady_wind_heel_deg=data.get("steady_wind_heel_deg", 0.0),
            calculation_time_ms=data.get("calculation_time_ms", 0),
            warnings=data.get("warnings", []),
        )


# =============================================================================
# FREE SURFACE DATA
# =============================================================================

@dataclass
class TankFreeSurface:
    """Free surface data for a single tank."""
    tank_id: str
    tank_name: str
    fill_percentage: float  # 0-100
    liquid_density_kg_m3: float
    moment_of_inertia_m4: float  # Transverse MOI of tank surface
    free_surface_moment_t_m: float  # FSM = ρ × i (tonnes-meters)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tank_id": self.tank_id,
            "tank_name": self.tank_name,
            "fill_percentage": round(self.fill_percentage, 1),
            "liquid_density_kg_m3": round(self.liquid_density_kg_m3, 1),
            "moment_of_inertia_m4": round(self.moment_of_inertia_m4, 4),
            "free_surface_moment_t_m": round(self.free_surface_moment_t_m, 4),
        }
