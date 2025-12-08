"""
MAGNET Weather Criterion Calculator

Module 06 v1.2 - Production-Ready

Evaluates IMO severe wind and rolling (weather criterion).

v1.1 FIX #5: Roll amplitude uses simplified estimate.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import time
import math
import logging

from .gz_curve import GZPoint

logger = logging.getLogger(__name__)


# =============================================================================
# WEATHER CRITERION CONSTANTS (IMO IS Code)
# =============================================================================

# Wind pressure (Pa) - default for harbor/coastal
WIND_PRESSURE_PA = 504.0  # ~25 m/s wind

# Minimum criterion ratio
MIN_B_OVER_A_RATIO = 1.0

# Roll amplitude estimation factors
ROLL_AMPLITUDE_BASE_DEG = 25.0  # Base roll amplitude
BILGE_KEEL_REDUCTION = 0.7  # Reduction factor for bilge keels


# =============================================================================
# WEATHER CRITERION RESULTS
# =============================================================================

@dataclass
class WeatherCriterionResults:
    """
    Results from weather criterion (severe wind and rolling) calculation.

    IMO IS Code criterion: Area(b) / Area(a) ≥ 1.0

    Where:
    - Area(a) = heeling energy from θ₀ to θ₁ (wind heeling)
    - Area(b) = righting energy from θ₁ to θ₂ (vessel righting)
    """
    # Areas
    area_a_m_rad: float         # Heeling energy (m-rad)
    area_b_m_rad: float         # Righting energy (m-rad)
    ratio_b_over_a: float

    # Compliance
    passes_criterion: bool

    # Angles
    theta_0_deg: float          # Steady wind heel angle
    theta_1_deg: float          # θ₀ + roll amplitude (leeward roll)
    theta_2_deg: float          # Angle of downflooding or 50°
    roll_amplitude_deg: float   # Roll amplitude φ₁

    # Wind parameters
    wind_pressure_pa: float
    wind_heeling_moment_kn_m: float
    wind_heel_angle_deg: float

    # Roll parameters
    roll_period_s: float

    # Metadata
    calculation_time_ms: int = 0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "area_a_m_rad": round(self.area_a_m_rad, 5),
            "area_b_m_rad": round(self.area_b_m_rad, 5),
            "ratio_b_over_a": round(self.ratio_b_over_a, 3),
            "passes_criterion": self.passes_criterion,
            "theta_0_deg": round(self.theta_0_deg, 1),
            "theta_1_deg": round(self.theta_1_deg, 1),
            "theta_2_deg": round(self.theta_2_deg, 1),
            "roll_amplitude_deg": round(self.roll_amplitude_deg, 1),
            "wind_pressure_pa": round(self.wind_pressure_pa, 1),
            "wind_heeling_moment_kn_m": round(self.wind_heeling_moment_kn_m, 2),
            "wind_heel_angle_deg": round(self.wind_heel_angle_deg, 2),
            "roll_period_s": round(self.roll_period_s, 2),
            "calculation_time_ms": self.calculation_time_ms,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeatherCriterionResults":
        return cls(
            area_a_m_rad=data.get("area_a_m_rad", 0.0),
            area_b_m_rad=data.get("area_b_m_rad", 0.0),
            ratio_b_over_a=data.get("ratio_b_over_a", 0.0),
            passes_criterion=data.get("passes_criterion", False),
            theta_0_deg=data.get("theta_0_deg", 0.0),
            theta_1_deg=data.get("theta_1_deg", 0.0),
            theta_2_deg=data.get("theta_2_deg", 0.0),
            roll_amplitude_deg=data.get("roll_amplitude_deg", 0.0),
            wind_pressure_pa=data.get("wind_pressure_pa", 0.0),
            wind_heeling_moment_kn_m=data.get("wind_heeling_moment_kn_m", 0.0),
            wind_heel_angle_deg=data.get("wind_heel_angle_deg", 0.0),
            roll_period_s=data.get("roll_period_s", 0.0),
            calculation_time_ms=data.get("calculation_time_ms", 0),
            warnings=data.get("warnings", []),
        )


# =============================================================================
# WEATHER CRITERION CALCULATOR
# =============================================================================

class WeatherCriterionCalculator:
    """
    Calculator for IMO severe wind and rolling criterion.

    The weather criterion compares:
    - Area(a): Heeling energy from wind
    - Area(b): Righting energy available

    Criterion: Area(b) / Area(a) ≥ 1.0

    v1.1 FIX #5: Roll amplitude uses simplified estimate based on B/T ratio
    and bilge keel presence. For detailed analysis, use model test data.
    """

    def calculate(
        self,
        displacement_mt: float,
        gm_m: float,
        beam_m: float,
        draft_m: float,
        projected_lateral_area_m2: float,
        height_of_wind_pressure_m: float,
        gz_curve: List[GZPoint],
        downflooding_angle_deg: float = 50.0,
        has_bilge_keels: bool = True,
        wind_pressure_pa: float = WIND_PRESSURE_PA,
    ) -> WeatherCriterionResults:
        """
        Calculate weather criterion per IMO IS Code.

        Args:
            displacement_mt: Vessel displacement (tonnes)
            gm_m: Metacentric height (m)
            beam_m: Vessel beam (m)
            draft_m: Mean draft (m)
            projected_lateral_area_m2: Projected lateral area above waterline (m²)
            height_of_wind_pressure_m: Height of centroid of lateral area above waterline (m)
            gz_curve: GZ curve points
            downflooding_angle_deg: Downflooding angle (deg)
            has_bilge_keels: Whether vessel has bilge keels
            wind_pressure_pa: Wind pressure (Pa)

        Returns:
            WeatherCriterionResults

        Raises:
            ValueError: If inputs are invalid
        """
        start_time = time.perf_counter()
        warnings: List[str] = []

        # Validate inputs
        if displacement_mt <= 0:
            raise ValueError(f"Displacement must be positive: {displacement_mt}")
        if gm_m <= 0:
            warnings.append(f"Non-positive GM ({gm_m}m) - weather criterion may fail")
        if not gz_curve:
            raise ValueError("GZ curve is required")

        # Estimate roll period
        roll_period = self._estimate_roll_period(beam_m, gm_m)
        warnings.append(f"Roll period estimated as {roll_period:.2f}s (simplified method)")

        # Estimate roll amplitude
        roll_amplitude = self._estimate_roll_amplitude(
            beam_m, draft_m, has_bilge_keels, roll_period
        )
        warnings.append(f"Roll amplitude estimated as {roll_amplitude:.1f}° (v1.1 FIX #5 simplified)")

        # Calculate wind heeling moment
        wind_heeling_moment_kn_m = self._calculate_wind_heeling_moment(
            wind_pressure_pa,
            projected_lateral_area_m2,
            height_of_wind_pressure_m,
        )

        # Calculate steady wind heel angle (θ₀)
        # Wind heeling arm = moment / (Δ × g)
        g = 9.81
        wind_heeling_arm_m = wind_heeling_moment_kn_m * 1000.0 / (displacement_mt * 1000.0 * g)
        theta_0 = self._find_heel_angle_for_gz(gz_curve, wind_heeling_arm_m)
        wind_heel_angle = theta_0

        # Calculate key angles
        theta_1 = theta_0 + roll_amplitude  # Leeward roll
        theta_2 = min(downflooding_angle_deg, 50.0)  # Upper limit

        if theta_1 >= theta_2:
            warnings.append(f"θ₁ ({theta_1:.1f}°) exceeds θ₂ ({theta_2:.1f}°) - insufficient range")
            theta_1 = theta_2 - 1.0  # Adjust for calculation

        # Calculate Area(a) - heeling energy
        area_a = self._calculate_heeling_area(
            gz_curve, wind_heeling_arm_m, theta_0, theta_1
        )

        # Calculate Area(b) - righting energy
        area_b = self._calculate_righting_area(
            gz_curve, wind_heeling_arm_m, theta_1, theta_2
        )

        # Calculate ratio
        if area_a > 0:
            ratio = area_b / area_a
        else:
            ratio = float('inf') if area_b > 0 else 0.0
            warnings.append("Area(a) is zero - check wind heeling calculation")

        passes_criterion = ratio >= MIN_B_OVER_A_RATIO

        if not passes_criterion:
            warnings.append(f"Weather criterion FAILED: ratio {ratio:.3f} < {MIN_B_OVER_A_RATIO}")

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return WeatherCriterionResults(
            area_a_m_rad=area_a,
            area_b_m_rad=area_b,
            ratio_b_over_a=ratio,
            passes_criterion=passes_criterion,
            theta_0_deg=theta_0,
            theta_1_deg=theta_1,
            theta_2_deg=theta_2,
            roll_amplitude_deg=roll_amplitude,
            wind_pressure_pa=wind_pressure_pa,
            wind_heeling_moment_kn_m=wind_heeling_moment_kn_m,
            wind_heel_angle_deg=wind_heel_angle,
            roll_period_s=roll_period,
            calculation_time_ms=elapsed_ms,
            warnings=warnings,
        )

    def _estimate_roll_period(
        self,
        beam_m: float,
        gm_m: float,
    ) -> float:
        """
        Estimate natural roll period.

        T = 2π × k / √(g × GM)

        Where k ≈ 0.4 × B (radius of gyration approximation)

        Args:
            beam_m: Vessel beam (m)
            gm_m: Metacentric height (m)

        Returns:
            Roll period (seconds)
        """
        g = 9.81

        if gm_m <= 0:
            return 15.0  # Default for very low GM

        k = 0.4 * beam_m  # Approximate radius of gyration
        roll_period = 2.0 * math.pi * k / math.sqrt(g * gm_m)

        # Clamp to reasonable range
        return min(max(roll_period, 3.0), 30.0)

    def _estimate_roll_amplitude(
        self,
        beam_m: float,
        draft_m: float,
        has_bilge_keels: bool,
        roll_period_s: float,
    ) -> float:
        """
        Estimate roll amplitude for severe wind and rolling.

        v1.1 FIX #5: Simplified estimation method.
        Base amplitude ~25° with adjustments for:
        - B/T ratio
        - Bilge keel presence

        Args:
            beam_m: Vessel beam (m)
            draft_m: Mean draft (m)
            has_bilge_keels: Whether vessel has bilge keels
            roll_period_s: Natural roll period (s)

        Returns:
            Roll amplitude (degrees)
        """
        # Base amplitude
        phi_1 = ROLL_AMPLITUDE_BASE_DEG

        # Adjust for B/T ratio (wider/shallower = more roll damping)
        bt_ratio = beam_m / draft_m if draft_m > 0 else 3.0
        if bt_ratio > 4.0:
            phi_1 *= 0.9  # Reduce for beamy vessels
        elif bt_ratio < 2.5:
            phi_1 *= 1.1  # Increase for deep vessels

        # Adjust for roll period (longer period = generally larger amplitude)
        if roll_period_s > 12.0:
            phi_1 *= 1.05
        elif roll_period_s < 8.0:
            phi_1 *= 0.95

        # Apply bilge keel reduction
        if has_bilge_keels:
            phi_1 *= BILGE_KEEL_REDUCTION

        return min(max(phi_1, 10.0), 40.0)  # Clamp to reasonable range

    def _calculate_wind_heeling_moment(
        self,
        wind_pressure_pa: float,
        projected_area_m2: float,
        height_m: float,
    ) -> float:
        """
        Calculate wind heeling moment.

        M = P × A × h

        Args:
            wind_pressure_pa: Wind pressure (Pa = N/m²)
            projected_area_m2: Projected lateral area (m²)
            height_m: Height of pressure center above waterline (m)

        Returns:
            Wind heeling moment (kN-m)
        """
        moment_n_m = wind_pressure_pa * projected_area_m2 * height_m
        return moment_n_m / 1000.0  # Convert to kN-m

    def _find_heel_angle_for_gz(
        self,
        gz_curve: List[GZPoint],
        target_gz: float,
    ) -> float:
        """
        Find heel angle where GZ equals target value.

        Uses linear interpolation.

        Args:
            gz_curve: List of GZPoints
            target_gz: Target GZ value (m)

        Returns:
            Heel angle (degrees)
        """
        if not gz_curve or target_gz <= 0:
            return 0.0

        # Find intersection point
        for i in range(len(gz_curve) - 1):
            gz1 = gz_curve[i].gz_m
            gz2 = gz_curve[i + 1].gz_m
            phi1 = gz_curve[i].heel_deg
            phi2 = gz_curve[i + 1].heel_deg

            if (gz1 <= target_gz <= gz2) or (gz2 <= target_gz <= gz1):
                if abs(gz2 - gz1) > 0.0001:
                    t = (target_gz - gz1) / (gz2 - gz1)
                    return phi1 + t * (phi2 - phi1)
                return phi1

        # If target exceeds curve, return max angle or 0
        max_gz = max(p.gz_m for p in gz_curve)
        if target_gz > max_gz:
            return 16.0  # IMO limit for severe weather heel

        return 0.0

    def _calculate_heeling_area(
        self,
        gz_curve: List[GZPoint],
        wind_heeling_arm: float,
        theta_0: float,
        theta_1: float,
    ) -> float:
        """
        Calculate Area(a) - heeling energy from wind.

        Area between wind heeling arm and GZ curve from θ₀ to θ₁.

        Args:
            gz_curve: GZ curve
            wind_heeling_arm: Constant wind heeling arm (m)
            theta_0: Steady wind heel angle (deg)
            theta_1: Maximum leeward roll angle (deg)

        Returns:
            Area (m-rad)
        """
        if theta_1 <= theta_0:
            return 0.0

        area = 0.0
        for i in range(len(gz_curve) - 1):
            phi1 = gz_curve[i].heel_deg
            phi2 = gz_curve[i + 1].heel_deg
            gz1 = gz_curve[i].gz_m
            gz2 = gz_curve[i + 1].gz_m

            # Check if segment is within range
            if phi2 <= theta_0 or phi1 >= theta_1:
                continue

            # Clip to range
            if phi1 < theta_0:
                t = (theta_0 - phi1) / (phi2 - phi1)
                gz1 = gz1 + t * (gz2 - gz1)
                phi1 = theta_0

            if phi2 > theta_1:
                t = (theta_1 - phi1) / (phi2 - phi1)
                gz2 = gz1 + t * (gz2 - gz1)
                phi2 = theta_1

            # Area between wind arm and GZ (trapezoidal)
            d_phi_rad = math.radians(phi2 - phi1)
            avg_diff = ((wind_heeling_arm - gz1) + (wind_heeling_arm - gz2)) / 2.0
            segment_area = abs(avg_diff) * d_phi_rad
            area += segment_area

        return area

    def _calculate_righting_area(
        self,
        gz_curve: List[GZPoint],
        wind_heeling_arm: float,
        theta_1: float,
        theta_2: float,
    ) -> float:
        """
        Calculate Area(b) - righting energy available.

        Area between GZ curve and wind heeling arm from θ₁ to θ₂.

        Args:
            gz_curve: GZ curve
            wind_heeling_arm: Constant wind heeling arm (m)
            theta_1: Start angle (deg)
            theta_2: End angle (deg)

        Returns:
            Area (m-rad)
        """
        if theta_2 <= theta_1:
            return 0.0

        area = 0.0
        for i in range(len(gz_curve) - 1):
            phi1 = gz_curve[i].heel_deg
            phi2 = gz_curve[i + 1].heel_deg
            gz1 = gz_curve[i].gz_m
            gz2 = gz_curve[i + 1].gz_m

            # Check if segment is within range
            if phi2 <= theta_1 or phi1 >= theta_2:
                continue

            # Clip to range
            if phi1 < theta_1:
                t = (theta_1 - phi1) / (phi2 - phi1)
                gz1 = gz1 + t * (gz2 - gz1)
                phi1 = theta_1

            if phi2 > theta_2:
                t = (theta_2 - phi1) / (phi2 - phi1)
                gz2 = gz1 + t * (gz2 - gz1)
                phi2 = theta_2

            # Area between GZ and wind arm (only positive GZ above arm)
            d_phi_rad = math.radians(phi2 - phi1)
            diff1 = max(gz1 - wind_heeling_arm, 0.0)
            diff2 = max(gz2 - wind_heeling_arm, 0.0)
            segment_area = ((diff1 + diff2) / 2.0) * d_phi_rad
            area += segment_area

        return area
