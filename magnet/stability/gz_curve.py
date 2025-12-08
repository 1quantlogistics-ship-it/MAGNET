"""
MAGNET GZ Curve Calculator

Module 06 v1.2 - Production-Ready

Generates righting arm (GZ) curves for stability assessment.

v1.1 FIX #2: GZ areas use explicit m-rad units.

Implements wall-sided formula:
GZ = GM·sin(φ) + (BM/2)·tan²(φ)·sin(φ)

Valid for heel angles up to ~40° for conventional hulls.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import time
import math
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# IMO INTACT STABILITY CRITERIA (IS Code A.749)
# =============================================================================

IMO_GZ_30_MIN = 0.20             # GZ at 30° minimum (m)
IMO_ANGLE_GZ_MAX_MIN = 25.0      # Angle of GZmax minimum (deg)
IMO_AREA_0_30_MIN = 0.055        # Area 0-30° minimum (m-rad)
IMO_AREA_0_40_MIN = 0.090        # Area 0-40° minimum (m-rad)
IMO_AREA_30_40_MIN = 0.030       # Area 30-40° minimum (m-rad)


# =============================================================================
# GZ POINT
# =============================================================================

@dataclass
class GZPoint:
    """Single point on the GZ curve."""
    heel_deg: float
    gz_m: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "heel_deg": round(self.heel_deg, 1),
            "gz_m": round(self.gz_m, 4),
        }


# =============================================================================
# GZ CURVE RESULTS
# =============================================================================

@dataclass
class GZCurveResults:
    """
    Results from GZ curve calculation.

    v1.1 FIX #2: Area fields use explicit m-rad units.
    """
    # Curve data
    curve: List[GZPoint]

    # Key values
    gz_max_m: float
    gz_30_m: float
    angle_gz_max_deg: float
    angle_of_vanishing_stability_deg: float
    range_of_stability_deg: float

    # Areas under curve (v1.1 FIX #2: explicit m-rad units)
    area_0_30_m_rad: float
    area_0_40_m_rad: float
    area_30_40_m_rad: float

    # Downflooding angle
    downflooding_angle_deg: float

    # IMO Compliance
    passes_all_criteria: bool
    criteria_results: Dict[str, bool] = field(default_factory=dict)

    # Metadata
    calculation_time_ms: int = 0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "curve": [p.to_dict() for p in self.curve],
            "gz_max_m": round(self.gz_max_m, 4),
            "gz_30_m": round(self.gz_30_m, 4),
            "angle_gz_max_deg": round(self.angle_gz_max_deg, 1),
            "angle_of_vanishing_stability_deg": round(self.angle_of_vanishing_stability_deg, 1),
            "range_of_stability_deg": round(self.range_of_stability_deg, 1),
            "area_0_30_m_rad": round(self.area_0_30_m_rad, 4),
            "area_0_40_m_rad": round(self.area_0_40_m_rad, 4),
            "area_30_40_m_rad": round(self.area_30_40_m_rad, 4),
            "downflooding_angle_deg": round(self.downflooding_angle_deg, 1),
            "passes_all_criteria": self.passes_all_criteria,
            "criteria_results": self.criteria_results,
            "calculation_time_ms": self.calculation_time_ms,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GZCurveResults":
        """Deserialize from dictionary."""
        curve = [GZPoint(**p) for p in data.get("curve", [])]
        return cls(
            curve=curve,
            gz_max_m=data.get("gz_max_m", 0.0),
            gz_30_m=data.get("gz_30_m", 0.0),
            angle_gz_max_deg=data.get("angle_gz_max_deg", 0.0),
            angle_of_vanishing_stability_deg=data.get("angle_of_vanishing_stability_deg", 0.0),
            range_of_stability_deg=data.get("range_of_stability_deg", 0.0),
            area_0_30_m_rad=data.get("area_0_30_m_rad", 0.0),
            area_0_40_m_rad=data.get("area_0_40_m_rad", 0.0),
            area_30_40_m_rad=data.get("area_30_40_m_rad", 0.0),
            downflooding_angle_deg=data.get("downflooding_angle_deg", 90.0),
            passes_all_criteria=data.get("passes_all_criteria", False),
            criteria_results=data.get("criteria_results", {}),
            calculation_time_ms=data.get("calculation_time_ms", 0),
            warnings=data.get("warnings", []),
        )


# =============================================================================
# GZ CURVE CALCULATOR
# =============================================================================

class GZCurveCalculator:
    """
    Calculator for GZ (righting arm) curves.

    Implements the wall-sided formula:
    GZ = GM·sin(φ) + (BM/2)·tan²(φ)·sin(φ)

    This approximation is valid for:
    - Heel angles up to ~40° for conventional hulls
    - Wall-sided sections (vertical hull sides)

    For larger angles or complex hull forms, use cross-curves
    from hydrostatic tables (V2 feature).

    Accuracy: ±5% up to 40°, degrades at higher angles
    """

    def calculate(
        self,
        gm_m: float,
        bm_m: float,
        beam_m: float,
        freeboard_m: float,
        max_heel_deg: float = 90.0,
        heel_step_deg: float = 5.0,
    ) -> GZCurveResults:
        """
        Calculate GZ curve using wall-sided formula.

        Args:
            gm_m: Metacentric height (m)
            bm_m: Metacentric radius (m)
            beam_m: Vessel beam (m)
            freeboard_m: Freeboard at midship (m)
            max_heel_deg: Maximum heel angle to calculate (default: 90°)
            heel_step_deg: Step between heel angles (default: 5°)

        Returns:
            GZCurveResults with curve and compliance status

        Raises:
            ValueError: If inputs are invalid
        """
        start_time = time.perf_counter()
        warnings: List[str] = []

        # Validate inputs
        if bm_m <= 0:
            raise ValueError(f"BM must be positive: {bm_m}")
        if beam_m <= 0:
            raise ValueError(f"Beam must be positive: {beam_m}")
        if freeboard_m <= 0:
            warnings.append(f"Non-positive freeboard: {freeboard_m}m")

        if gm_m <= 0:
            warnings.append(f"Non-positive GM: {gm_m}m - vessel may be unstable")

        if max_heel_deg > 90:
            max_heel_deg = 90.0
            warnings.append("Max heel limited to 90°")

        # Estimate downflooding angle
        downflooding_angle = self._estimate_downflooding_angle(beam_m, freeboard_m)

        # Generate GZ curve
        curve = []
        heel_deg = 0.0
        while heel_deg <= max_heel_deg:
            gz = self._calculate_gz_wall_sided(gm_m, bm_m, heel_deg)
            curve.append(GZPoint(heel_deg=heel_deg, gz_m=gz))
            heel_deg += heel_step_deg

        # Find key values
        gz_max, angle_gz_max = self._find_gz_max(curve)
        gz_30 = self._interpolate_gz_at_angle(curve, 30.0)
        vanishing_angle = self._find_vanishing_angle(curve)
        range_of_stability = vanishing_angle

        # Calculate areas (v1.1 FIX #2: explicit m-rad units)
        area_0_30 = self._calculate_area(curve, 0.0, 30.0)
        area_0_40 = self._calculate_area(curve, 0.0, 40.0)
        area_30_40 = self._calculate_area(curve, 30.0, 40.0)

        # Check IMO criteria
        criteria_results = {
            "gz_30": gz_30 >= IMO_GZ_30_MIN,
            "angle_gz_max": angle_gz_max >= IMO_ANGLE_GZ_MAX_MIN,
            "area_0_30": area_0_30 >= IMO_AREA_0_30_MIN,
            "area_0_40": area_0_40 >= IMO_AREA_0_40_MIN,
            "area_30_40": area_30_40 >= IMO_AREA_30_40_MIN,
        }
        passes_all = all(criteria_results.values())

        # Add warnings for failed criteria
        if not criteria_results["gz_30"]:
            warnings.append(f"GZ at 30° ({gz_30:.3f}m) < minimum ({IMO_GZ_30_MIN}m)")
        if not criteria_results["angle_gz_max"]:
            warnings.append(f"Angle of GZmax ({angle_gz_max:.1f}°) < minimum ({IMO_ANGLE_GZ_MAX_MIN}°)")
        if not criteria_results["area_0_30"]:
            warnings.append(f"Area 0-30° ({area_0_30:.4f} m-rad) < minimum ({IMO_AREA_0_30_MIN} m-rad)")
        if not criteria_results["area_0_40"]:
            warnings.append(f"Area 0-40° ({area_0_40:.4f} m-rad) < minimum ({IMO_AREA_0_40_MIN} m-rad)")
        if not criteria_results["area_30_40"]:
            warnings.append(f"Area 30-40° ({area_30_40:.4f} m-rad) < minimum ({IMO_AREA_30_40_MIN} m-rad)")

        # Add accuracy warning for high angles
        if angle_gz_max > 40:
            warnings.append(f"GZmax at {angle_gz_max:.1f}° - wall-sided formula less accurate above 40°")

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return GZCurveResults(
            curve=curve,
            gz_max_m=gz_max,
            gz_30_m=gz_30,
            angle_gz_max_deg=angle_gz_max,
            angle_of_vanishing_stability_deg=vanishing_angle,
            range_of_stability_deg=range_of_stability,
            area_0_30_m_rad=area_0_30,
            area_0_40_m_rad=area_0_40,
            area_30_40_m_rad=area_30_40,
            downflooding_angle_deg=downflooding_angle,
            passes_all_criteria=passes_all,
            criteria_results=criteria_results,
            calculation_time_ms=elapsed_ms,
            warnings=warnings,
        )

    def _calculate_gz_wall_sided(
        self,
        gm_m: float,
        bm_m: float,
        heel_deg: float,
    ) -> float:
        """
        Calculate GZ using wall-sided formula.

        GZ = GM·sin(φ) + (BM/2)·tan²(φ)·sin(φ)

        Args:
            gm_m: Metacentric height (m)
            bm_m: Metacentric radius (m)
            heel_deg: Heel angle (degrees)

        Returns:
            GZ value (m)
        """
        if abs(heel_deg) < 0.001:
            return 0.0

        # Clamp heel to avoid division issues at 90°
        if abs(heel_deg) >= 89.0:
            heel_deg = 89.0 if heel_deg > 0 else -89.0

        phi = math.radians(heel_deg)
        sin_phi = math.sin(phi)
        tan_phi = math.tan(phi)

        gz = gm_m * sin_phi + (bm_m / 2.0) * (tan_phi ** 2) * sin_phi

        return gz

    def _estimate_downflooding_angle(
        self,
        beam_m: float,
        freeboard_m: float,
    ) -> float:
        """
        Estimate downflooding angle from freeboard and beam.

        Conservative estimate: angle at which deck edge enters water.

        θ_df ≈ arctan(2F / B)

        Args:
            beam_m: Vessel beam (m)
            freeboard_m: Freeboard at midship (m)

        Returns:
            Estimated downflooding angle (degrees)
        """
        if beam_m <= 0 or freeboard_m <= 0:
            return 90.0  # No limit

        tan_theta = (2.0 * freeboard_m) / beam_m
        theta_rad = math.atan(tan_theta)
        theta_deg = math.degrees(theta_rad)

        # Clamp to reasonable range
        return min(max(theta_deg, 15.0), 90.0)

    def _find_gz_max(self, curve: List[GZPoint]) -> tuple[float, float]:
        """
        Find maximum GZ and its angle.

        Args:
            curve: List of GZPoints

        Returns:
            Tuple of (gz_max, angle_at_max)
        """
        if not curve:
            return 0.0, 0.0

        max_point = max(curve, key=lambda p: p.gz_m)
        return max_point.gz_m, max_point.heel_deg

    def _interpolate_gz_at_angle(
        self,
        curve: List[GZPoint],
        target_angle: float,
    ) -> float:
        """
        Interpolate GZ at a specific angle.

        Args:
            curve: List of GZPoints
            target_angle: Target heel angle (degrees)

        Returns:
            Interpolated GZ value (m)
        """
        if not curve:
            return 0.0

        # Find bracketing points
        for i in range(len(curve) - 1):
            if curve[i].heel_deg <= target_angle <= curve[i + 1].heel_deg:
                # Linear interpolation
                t = (target_angle - curve[i].heel_deg) / (curve[i + 1].heel_deg - curve[i].heel_deg)
                return curve[i].gz_m + t * (curve[i + 1].gz_m - curve[i].gz_m)

        # Target outside range - use nearest point
        if target_angle <= curve[0].heel_deg:
            return curve[0].gz_m
        return curve[-1].gz_m

    def _find_vanishing_angle(self, curve: List[GZPoint]) -> float:
        """
        Find angle of vanishing stability (where GZ = 0 after max).

        Args:
            curve: List of GZPoints

        Returns:
            Vanishing angle (degrees)
        """
        if not curve:
            return 0.0

        # Find max first
        max_idx = 0
        for i, p in enumerate(curve):
            if p.gz_m > curve[max_idx].gz_m:
                max_idx = i

        # Search after max for zero crossing
        for i in range(max_idx, len(curve) - 1):
            if curve[i].gz_m >= 0 and curve[i + 1].gz_m < 0:
                # Linear interpolation to find exact crossing
                if abs(curve[i].gz_m - curve[i + 1].gz_m) > 0.001:
                    t = curve[i].gz_m / (curve[i].gz_m - curve[i + 1].gz_m)
                    return curve[i].heel_deg + t * (curve[i + 1].heel_deg - curve[i].heel_deg)
                return curve[i].heel_deg

        # No zero crossing found - use max angle
        return curve[-1].heel_deg

    def _calculate_area(
        self,
        curve: List[GZPoint],
        angle_start: float,
        angle_end: float,
    ) -> float:
        """
        Calculate area under GZ curve between two angles.

        Uses trapezoidal integration.
        Result is in m-rad (v1.1 FIX #2).

        Args:
            curve: List of GZPoints
            angle_start: Start angle (degrees)
            angle_end: End angle (degrees)

        Returns:
            Area under curve (m-rad)
        """
        if not curve or angle_start >= angle_end:
            return 0.0

        area = 0.0
        for i in range(len(curve) - 1):
            # Check if segment is within range
            phi1 = curve[i].heel_deg
            phi2 = curve[i + 1].heel_deg
            gz1 = curve[i].gz_m
            gz2 = curve[i + 1].gz_m

            # Clip to range
            if phi2 <= angle_start or phi1 >= angle_end:
                continue

            # Adjust endpoints if needed
            if phi1 < angle_start:
                t = (angle_start - phi1) / (phi2 - phi1)
                gz1 = gz1 + t * (gz2 - gz1)
                phi1 = angle_start

            if phi2 > angle_end:
                t = (angle_end - phi1) / (phi2 - phi1)
                gz2 = gz1 + t * (gz2 - gz1)
                phi2 = angle_end

            # Trapezoidal rule (convert degrees to radians for m-rad result)
            d_phi_rad = math.radians(phi2 - phi1)
            segment_area = 0.5 * (gz1 + gz2) * d_phi_rad
            area += max(segment_area, 0.0)  # Only count positive GZ

        return area
