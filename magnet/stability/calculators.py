"""
MAGNET Stability Calculators

Module 06 v1.2 - Production-Ready

Calculation engines for stability analysis.

Implements:
- IntactGMCalculator: GM = KB + BM - KG - FSC
- GZCurveCalculator: Wall-sided formula for GZ curve
- FreeSurfaceCalculator: Free surface correction
- DamageStabilityCalculator: Lost buoyancy method (simplified)
- WeatherCriterionCalculator: IMO severe wind and rolling criterion
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any, Tuple
import math
import time
import logging

from .constants import (
    IMO_INTACT,
    IMO_WEATHER,
    GZ_CURVE_ANGLES_DEG,
    WALL_SIDED_VALID_DEG,
    FSC_FILL_MIN,
    FSC_FILL_MAX,
    RHO_SEAWATER_KG_M3,
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

logger = logging.getLogger(__name__)


# =============================================================================
# INTACT GM CALCULATOR
# =============================================================================

class IntactGMCalculator:
    """
    Calculates intact metacentric height (GM).

    GM = KB + BM - KG - FSC

    Where:
    - KB: Height of center of buoyancy from keel
    - BM: Metacentric radius (I_T / V)
    - KG: Height of center of gravity from keel
    - FSC: Free surface correction (optional)
    """

    def calculate(
        self,
        kb_m: float,
        bm_m: float,
        kg_m: float,
        fsc_m: float = 0.0,
        kg_source: str = "unknown",
    ) -> GMResults:
        """
        Calculate intact GM.

        Args:
            kb_m: Center of buoyancy height from keel (meters)
            bm_m: Metacentric radius (meters)
            kg_m: Center of gravity height from keel (meters)
            fsc_m: Free surface correction (meters), optional
            kg_source: Source of KG value for traceability

        Returns:
            GMResults with calculated values
        """
        start_time = time.perf_counter()
        warnings: List[str] = []

        # Validate inputs
        if kb_m < 0:
            raise ValueError(f"KB must be non-negative: {kb_m}")
        if bm_m < 0:
            raise ValueError(f"BM must be non-negative: {bm_m}")
        if kg_m < 0:
            raise ValueError(f"KG must be non-negative: {kg_m}")
        if fsc_m < 0:
            warnings.append(f"Negative FSC ({fsc_m}m) treated as zero")
            fsc_m = 0.0

        # Calculate KM
        km_m = kb_m + bm_m

        # Calculate GM (solid - without FSC)
        gm_solid_m = kb_m + bm_m - kg_m

        # Calculate GM with FSC
        gm_m = gm_solid_m - fsc_m
        has_fsc = fsc_m > 0

        # Check for negative GM (unstable)
        if gm_m < 0:
            warnings.append(f"Negative GM ({gm_m:.3f}m) indicates instability!")

        # Check IMO criterion
        passes_gm_criterion = gm_m >= IMO_INTACT.gm_min_m

        if not passes_gm_criterion:
            warnings.append(
                f"GM ({gm_m:.3f}m) below IMO minimum ({IMO_INTACT.gm_min_m}m)"
            )

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return GMResults(
            gm_m=gm_m,
            gm_solid_m=gm_solid_m,
            kb_m=kb_m,
            bm_m=bm_m,
            kg_m=kg_m,
            km_m=km_m,
            fsc_m=fsc_m,
            has_fsc=has_fsc,
            kg_source=kg_source,
            passes_gm_criterion=passes_gm_criterion,
            calculation_time_ms=elapsed_ms,
            warnings=warnings,
        )


# =============================================================================
# GZ CURVE CALCULATOR
# =============================================================================

class GZCurveCalculator:
    """
    Generates GZ (righting arm) curve using wall-sided formula.

    GZ(φ) = sin(φ) × (GM + 0.5 × BM × tan²(φ))

    This formula is accurate to approximately 40-45° heel.
    Beyond that, actual hull shape significantly affects the curve.
    """

    def calculate(
        self,
        gm_m: float,
        bm_m: float,
        angles_deg: Optional[List[float]] = None,
    ) -> GZCurveResults:
        """
        Calculate GZ curve.

        Args:
            gm_m: Metacentric height (meters)
            bm_m: Metacentric radius (meters)
            angles_deg: List of heel angles to calculate (degrees)

        Returns:
            GZCurveResults with curve data and criteria compliance
        """
        start_time = time.perf_counter()
        warnings: List[str] = []

        if angles_deg is None:
            angles_deg = GZ_CURVE_ANGLES_DEG

        # Generate GZ curve
        curve: List[GZCurvePoint] = []
        gz_values: Dict[float, float] = {}  # For easy lookup

        for angle_deg in angles_deg:
            angle_rad = math.radians(angle_deg)
            gz_m = self._calculate_gz_wall_sided(gm_m, bm_m, angle_rad)
            curve.append(GZCurvePoint(
                heel_deg=angle_deg,
                heel_rad=angle_rad,
                gz_m=gz_m,
            ))
            gz_values[angle_deg] = gz_m

        # Add warning for angles beyond wall-sided validity
        max_angle = max(angles_deg)
        if max_angle > WALL_SIDED_VALID_DEG:
            warnings.append(
                f"GZ values beyond {WALL_SIDED_VALID_DEG}° use wall-sided approximation, "
                "actual values depend on hull shape"
            )

        # Find characteristic values
        gz_max_m, angle_gz_max_deg = self._find_gz_max(curve)

        # Get GZ at specific angles (interpolate if needed)
        gz_30_m = self._interpolate_gz(curve, 30.0)
        gz_40_m = self._interpolate_gz(curve, 40.0)

        # Find angle of vanishing stability (where GZ crosses zero)
        angle_vanishing_deg = self._find_vanishing_angle(curve)
        range_deg = angle_vanishing_deg  # Range is 0 to vanishing angle

        # Calculate areas under curve
        area_0_30 = self._calculate_area(curve, 0.0, 30.0)
        area_0_40 = self._calculate_area(curve, 0.0, 40.0)
        area_30_40 = self._calculate_area(curve, 30.0, 40.0)
        dynamic_stability = self._calculate_area(curve, 0.0, angle_gz_max_deg)

        # Check IMO criteria
        passes_gz_30 = gz_30_m >= IMO_INTACT.gz_30_min_m
        passes_angle_gz_max = angle_gz_max_deg >= IMO_INTACT.angle_gz_max_min_deg
        passes_area_0_30 = area_0_30 >= IMO_INTACT.area_0_30_min_m_rad
        passes_area_0_40 = area_0_40 >= IMO_INTACT.area_0_40_min_m_rad
        passes_area_30_40 = area_30_40 >= IMO_INTACT.area_30_40_min_m_rad

        passes_all = all([
            passes_gz_30,
            passes_angle_gz_max,
            passes_area_0_30,
            passes_area_0_40,
            passes_area_30_40,
        ])

        # Add warnings for failed criteria
        if not passes_gz_30:
            warnings.append(f"GZ at 30° ({gz_30_m:.3f}m) below minimum ({IMO_INTACT.gz_30_min_m}m)")
        if not passes_angle_gz_max:
            warnings.append(f"Angle of max GZ ({angle_gz_max_deg:.1f}°) below minimum ({IMO_INTACT.angle_gz_max_min_deg}°)")
        if not passes_area_0_30:
            warnings.append(f"Area 0-30° ({area_0_30:.4f} m-rad) below minimum ({IMO_INTACT.area_0_30_min_m_rad})")
        if not passes_area_0_40:
            warnings.append(f"Area 0-40° ({area_0_40:.4f} m-rad) below minimum ({IMO_INTACT.area_0_40_min_m_rad})")
        if not passes_area_30_40:
            warnings.append(f"Area 30-40° ({area_30_40:.4f} m-rad) below minimum ({IMO_INTACT.area_30_40_min_m_rad})")

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return GZCurveResults(
            curve=curve,
            gz_max_m=gz_max_m,
            angle_gz_max_deg=angle_gz_max_deg,
            gz_30_m=gz_30_m,
            gz_40_m=gz_40_m,
            angle_of_vanishing_stability_deg=angle_vanishing_deg,
            range_of_stability_deg=range_deg,
            area_0_30_m_rad=area_0_30,
            area_0_40_m_rad=area_0_40,
            area_30_40_m_rad=area_30_40,
            dynamic_stability_m_rad=dynamic_stability,
            passes_gz_30_criterion=passes_gz_30,
            passes_angle_gz_max_criterion=passes_angle_gz_max,
            passes_area_0_30_criterion=passes_area_0_30,
            passes_area_0_40_criterion=passes_area_0_40,
            passes_area_30_40_criterion=passes_area_30_40,
            passes_all_gz_criteria=passes_all,
            gm_m=gm_m,
            bm_m=bm_m,
            calculation_time_ms=elapsed_ms,
            warnings=warnings,
        )

    def _calculate_gz_wall_sided(
        self, gm_m: float, bm_m: float, angle_rad: float
    ) -> float:
        """
        Calculate GZ using wall-sided formula.

        GZ = sin(φ) × (GM + 0.5 × BM × tan²(φ))
        """
        if abs(angle_rad) < 0.001:
            return 0.0

        sin_phi = math.sin(angle_rad)
        tan_phi = math.tan(angle_rad)

        gz = sin_phi * (gm_m + 0.5 * bm_m * tan_phi * tan_phi)
        return gz

    def _find_gz_max(self, curve: List[GZCurvePoint]) -> Tuple[float, float]:
        """Find maximum GZ and its angle."""
        if not curve:
            return 0.0, 0.0

        max_point = max(curve, key=lambda p: p.gz_m)
        return max_point.gz_m, max_point.heel_deg

    def _interpolate_gz(self, curve: List[GZCurvePoint], target_deg: float) -> float:
        """Interpolate GZ at a specific angle."""
        if not curve:
            return 0.0

        # Find surrounding points
        below = None
        above = None
        for p in curve:
            if p.heel_deg == target_deg:
                return p.gz_m
            if p.heel_deg < target_deg:
                below = p
            elif p.heel_deg > target_deg and above is None:
                above = p

        if below is None or above is None:
            # Extrapolate using nearest point
            nearest = min(curve, key=lambda p: abs(p.heel_deg - target_deg))
            return nearest.gz_m

        # Linear interpolation
        t = (target_deg - below.heel_deg) / (above.heel_deg - below.heel_deg)
        return below.gz_m + t * (above.gz_m - below.gz_m)

    def _find_vanishing_angle(self, curve: List[GZCurvePoint]) -> float:
        """Find angle where GZ becomes zero or negative."""
        if not curve:
            return 90.0

        # Find where GZ crosses zero after being positive
        found_positive = False
        for i, p in enumerate(curve):
            if p.gz_m > 0:
                found_positive = True
            elif found_positive and p.gz_m <= 0:
                # Interpolate to find exact crossing
                if i > 0:
                    prev = curve[i - 1]
                    if prev.gz_m != p.gz_m:
                        t = prev.gz_m / (prev.gz_m - p.gz_m)
                        return prev.heel_deg + t * (p.heel_deg - prev.heel_deg)
                return p.heel_deg

        # If GZ never goes negative, return last angle
        return curve[-1].heel_deg if curve else 90.0

    def _calculate_area(
        self, curve: List[GZCurvePoint], start_deg: float, end_deg: float
    ) -> float:
        """
        Calculate area under GZ curve between two angles.

        Uses trapezoidal integration.
        Returns area in meter-radians.
        """
        if not curve:
            return 0.0

        # Filter points in range
        points = [p for p in curve if start_deg <= p.heel_deg <= end_deg]

        # Add interpolated endpoints if needed
        if points and points[0].heel_deg > start_deg:
            gz_start = self._interpolate_gz(curve, start_deg)
            points.insert(0, GZCurvePoint(
                heel_deg=start_deg,
                heel_rad=math.radians(start_deg),
                gz_m=gz_start,
            ))

        if points and points[-1].heel_deg < end_deg:
            gz_end = self._interpolate_gz(curve, end_deg)
            points.append(GZCurvePoint(
                heel_deg=end_deg,
                heel_rad=math.radians(end_deg),
                gz_m=gz_end,
            ))

        if len(points) < 2:
            return 0.0

        # Trapezoidal integration
        area = 0.0
        for i in range(1, len(points)):
            p1, p2 = points[i - 1], points[i]
            # Area in meter-radians
            d_rad = p2.heel_rad - p1.heel_rad
            avg_gz = (p1.gz_m + p2.gz_m) / 2.0
            area += avg_gz * d_rad

        return max(area, 0.0)


# =============================================================================
# FREE SURFACE CALCULATOR
# =============================================================================

class FreeSurfaceCalculator:
    """
    Calculates free surface correction (FSC).

    FSC = Σ(FSM) / Δ

    Where:
    - FSM = ρ × i (free surface moment per tank)
    - ρ = liquid density (t/m³)
    - i = transverse moment of inertia of tank surface (m⁴)
    - Δ = displacement (tonnes)

    FIX #7: Explicit unit handling
    [kg/m³] × [m⁴] ÷ 1000 = [t-m]
    [t-m] ÷ [t] = [m]
    """

    def calculate(
        self,
        displacement_mt: float,
        tanks: List[TankFreeSurface],
    ) -> Tuple[float, List[str]]:
        """
        Calculate total free surface correction.

        Args:
            displacement_mt: Vessel displacement (tonnes)
            tanks: List of TankFreeSurface data

        Returns:
            Tuple of (FSC in meters, list of warnings)
        """
        warnings: List[str] = []

        if displacement_mt <= 0:
            raise ValueError(f"Displacement must be positive: {displacement_mt}")

        if not tanks:
            return 0.0, ["No tanks provided for FSC calculation"]

        total_fsm = 0.0
        active_tanks = 0

        for tank in tanks:
            # Only tanks between 15% and 85% fill contribute
            fill_frac = tank.fill_percentage / 100.0

            if fill_frac < FSC_FILL_MIN or fill_frac > FSC_FILL_MAX:
                continue

            # FSM = ρ × i / 1000 (convert kg-m to t-m)
            # FIX #7: Explicit unit derivation
            fsm_t_m = (tank.liquid_density_kg_m3 * tank.moment_of_inertia_m4) / 1000.0
            total_fsm += fsm_t_m
            active_tanks += 1

        if active_tanks == 0:
            warnings.append("No tanks in 15-85% fill range for FSC")
            return 0.0, warnings

        # FSC = Σ(FSM) / Δ
        fsc_m = total_fsm / displacement_mt

        warnings.append(f"FSC from {active_tanks} tanks: {fsc_m:.4f}m")

        return fsc_m, warnings


# =============================================================================
# DAMAGE STABILITY CALCULATOR (SIMPLIFIED)
# =============================================================================

class DamageStabilityCalculator:
    """
    Simplified damage stability calculator using lost buoyancy method.

    This is a first-order approximation. Full damage stability requires
    iterative equilibrium calculations with actual compartment geometry.
    """

    # Standard damage cases with typical permeabilities
    STANDARD_CASES = [
        ("forepeak", "Forepeak compartment", 0.95),
        ("engine_room", "Engine room", 0.85),
        ("aft_peak", "Aft peak compartment", 0.95),
        ("midship_hold", "Midship hold/tank", 0.60),
    ]

    def calculate(
        self,
        intact_gm_m: float,
        intact_gz_max_m: float,
        displacement_mt: float,
        compartment_volumes: Optional[Dict[str, float]] = None,
    ) -> DamageResults:
        """
        Calculate simplified damage stability.

        For each standard damage case, estimates residual stability
        assuming lost buoyancy reduces GM proportionally.

        Args:
            intact_gm_m: Intact GM (meters)
            intact_gz_max_m: Intact maximum GZ (meters)
            displacement_mt: Vessel displacement (tonnes)
            compartment_volumes: Optional dict of compartment volumes (m³)

        Returns:
            DamageResults with cases and overall assessment
        """
        start_time = time.perf_counter()
        warnings: List[str] = []
        cases: List[DamageCase] = []

        if compartment_volumes is None:
            # Use simplified estimation
            warnings.append("Using simplified damage estimation without compartment geometry")
            compartment_volumes = {}

        worst_gm = float('inf')
        worst_case_id = ""
        failed_cases: List[str] = []

        for case_id, compartment, permeability in self.STANDARD_CASES:
            # Simplified: assume GM reduction of 10-30% per damage case
            # This is a rough approximation
            gm_reduction_factor = 0.85 - 0.05 * self.STANDARD_CASES.index(
                (case_id, compartment, permeability)
            )

            residual_gm = intact_gm_m * gm_reduction_factor
            residual_gz_max = intact_gz_max_m * gm_reduction_factor

            # Simplified range estimate
            residual_range = 60.0 if residual_gm > 0 else 0.0

            # Check if passes damage stability criteria
            # Simplified: residual GM > 0.05m and range > 15°
            passes = residual_gm >= 0.05 and residual_range >= 15.0

            case = DamageCase(
                case_id=case_id,
                compartment=compartment,
                permeability=permeability,
                residual_gm_m=residual_gm,
                residual_gz_max_m=residual_gz_max,
                residual_range_deg=residual_range,
                heel_angle_deg=0.0,  # Would need iteration to calculate
                trim_m=0.0,
                passes_criteria=passes,
            )
            cases.append(case)

            if residual_gm < worst_gm:
                worst_gm = residual_gm
                worst_case_id = case_id

            if not passes:
                failed_cases.append(case_id)

        all_pass = len(failed_cases) == 0

        if not all_pass:
            warnings.append(f"Failed damage cases: {', '.join(failed_cases)}")

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return DamageResults(
            cases=cases,
            cases_evaluated=len(cases),
            worst_gm_m=worst_gm,
            worst_case_id=worst_case_id,
            worst_gz_max_m=min(c.residual_gz_max_m for c in cases) if cases else 0.0,
            worst_range_deg=min(c.residual_range_deg for c in cases) if cases else 0.0,
            all_cases_pass=all_pass,
            failed_cases=failed_cases,
            calculation_time_ms=elapsed_ms,
            warnings=warnings,
        )


# =============================================================================
# WEATHER CRITERION CALCULATOR
# =============================================================================

class WeatherCriterionCalculator:
    """
    Simplified IMO weather criterion calculator.

    Checks that the energy balance b/a >= 1.0 where:
    - a = area under heeling lever curve
    - b = area under righting lever curve

    This implementation uses simplified formulas for wind heeling
    and roll amplitude estimation.
    """

    def calculate(
        self,
        gz_curve: GZCurveResults,
        displacement_mt: float,
        beam_m: float,
        draft_m: float,
        loa_m: float,
        gm_m: float,
        windage_area_m2: Optional[float] = None,
        windage_lever_m: Optional[float] = None,
    ) -> WeatherCriterionResults:
        """
        Calculate weather criterion compliance.

        Args:
            gz_curve: GZ curve results
            displacement_mt: Displacement (tonnes)
            beam_m: Beam (meters)
            draft_m: Draft (meters)
            loa_m: Length overall (meters)
            gm_m: Metacentric height (meters)
            windage_area_m2: Lateral windage area (optional, estimated if not provided)
            windage_lever_m: Lever from center of windage to half draft (optional)

        Returns:
            WeatherCriterionResults
        """
        start_time = time.perf_counter()
        warnings: List[str] = []

        # Estimate windage area if not provided
        if windage_area_m2 is None:
            # Rough estimate: 0.5 * LOA * (depth above waterline)
            depth_above_wl = 0.4 * draft_m  # Assume freeboard ~ 40% of draft
            windage_area_m2 = 0.5 * loa_m * depth_above_wl
            warnings.append(f"Windage area estimated as {windage_area_m2:.1f}m²")

        # Estimate windage lever if not provided
        if windage_lever_m is None:
            # Assume center of windage at half the height above waterline
            windage_lever_m = draft_m * 0.7
            warnings.append(f"Windage lever estimated as {windage_lever_m:.2f}m")

        # Calculate wind heeling lever
        # lw = (P × A × z) / (1000 × g × Δ)
        # where P = wind pressure (Pa), A = area (m²), z = lever (m), Δ = displacement (t)
        gravity = 9.81
        wind_pressure = IMO_WEATHER.wind_pressure_pa

        wind_heel_lever_m = (
            wind_pressure * windage_area_m2 * windage_lever_m
        ) / (1000.0 * gravity * displacement_mt)

        # Estimate steady wind heel angle (small angle: heel ≈ lw/GM in radians)
        if gm_m > 0:
            steady_wind_heel_rad = wind_heel_lever_m / gm_m
            steady_wind_heel_deg = math.degrees(steady_wind_heel_rad)
        else:
            steady_wind_heel_deg = 90.0  # Unstable

        # Estimate roll period (simplified)
        # T = 2π × k / √(g × GM)
        # where k ≈ 0.4 × B (radius of gyration estimate)
        k = 0.4 * beam_m
        if gm_m > 0:
            roll_period_s = 2.0 * math.pi * k / math.sqrt(gravity * gm_m)
        else:
            roll_period_s = 0.0

        # Estimate roll amplitude (simplified - typically 15-25° for workboats)
        roll_amplitude_deg = 15.0 + 10.0 * (1.0 - min(gm_m / 1.0, 1.0))
        warnings.append(f"Roll amplitude estimated as {roll_amplitude_deg:.1f}°")

        # Calculate heeling area (a) - area under wind heeling lever
        # Simplified: assume constant heeling lever
        roll_back_angle_rad = math.radians(roll_amplitude_deg)
        heeling_area_a = wind_heel_lever_m * roll_back_angle_rad

        # Calculate righting area (b) - area under GZ curve from windward heel to leeward
        # Simplified: use area from 0 to roll amplitude on GZ curve
        righting_area_b = gz_curve.area_0_30_m_rad * (roll_amplitude_deg / 30.0)

        # Energy ratio
        if heeling_area_a > 0:
            energy_ratio = righting_area_b / heeling_area_a
        else:
            energy_ratio = float('inf') if righting_area_b > 0 else 0.0

        passes_criterion = energy_ratio >= IMO_WEATHER.energy_ratio_min

        if not passes_criterion:
            warnings.append(
                f"Weather criterion not met: b/a = {energy_ratio:.2f} < 1.0"
            )

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return WeatherCriterionResults(
            heeling_area_a_m_rad=heeling_area_a,
            righting_area_b_m_rad=righting_area_b,
            energy_ratio=energy_ratio,
            passes_criterion=passes_criterion,
            roll_period_s=roll_period_s,
            roll_amplitude_deg=roll_amplitude_deg,
            wind_heel_lever_m=wind_heel_lever_m,
            steady_wind_heel_deg=steady_wind_heel_deg,
            calculation_time_ms=elapsed_ms,
            warnings=warnings,
        )
