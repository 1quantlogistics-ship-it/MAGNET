"""
MAGNET V1 Stability Calculations (ALPHA)

Hydrostatic stability calculations including:
- GM (metacentric height)
- KB (center of buoyancy)
- BM (metacentric radius)
- GZ (righting arm) curve
- IMO A.749 intact stability criteria

References:
- IMO Resolution A.749(18) - Code on Intact Stability
- Principles of Naval Architecture (SNAME)
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import math

# Import schema with fallback for standalone testing
try:
    from schemas.hull_params import HullParamsSchema
except ImportError:
    HullParamsSchema = None  # type: ignore

# Physical constants
SEAWATER_DENSITY = 1.025  # tonnes/m³
GRAVITY = 9.81  # m/s²


@dataclass
class StabilityResult:
    """Result of stability calculations."""
    GM: float  # Metacentric height (m)
    KB: float  # Center of buoyancy height (m)
    KG: float  # Center of gravity height (m)
    BM: float  # Metacentric radius (m)
    KM: float  # Height of metacenter (m)
    displacement: float  # Displacement (tonnes)

    # GZ curve data
    heel_angles: List[float]  # Heel angles (degrees)
    gz_values: List[float]  # GZ values at each angle (m)

    # Key stability values
    max_gz: float  # Maximum GZ value (m)
    angle_max_gz: float  # Angle at maximum GZ (degrees)
    range_positive_stability: float  # Range of positive stability (degrees)

    # IMO criteria results
    imo_criteria_passed: bool
    imo_criteria_details: dict

    def is_stable(self) -> bool:
        """Check if vessel has positive initial stability."""
        return self.GM > 0 and self.imo_criteria_passed


def calculate_KB_box(draft: float) -> float:
    """
    Calculate KB for box-shaped vessel (approximation).

    KB = T/2 for a wall-sided vessel

    Args:
        draft: Design draft (m)

    Returns:
        KB (center of buoyancy height above keel) in meters
    """
    return draft / 2


def calculate_KB_morrish(
    draft: float,
    block_coefficient: float,
    waterplane_coefficient: float
) -> float:
    """
    Calculate KB using Morrish's formula.

    KB = T × (5/6 - Cb/(3×Cwp))

    More accurate than box approximation for actual hull forms.

    Args:
        draft: Design draft (m)
        block_coefficient: Block coefficient (Cb)
        waterplane_coefficient: Waterplane coefficient (Cwp)

    Returns:
        KB in meters
    """
    return draft * (5/6 - block_coefficient / (3 * waterplane_coefficient))


def calculate_KB_posdunine(
    draft: float,
    block_coefficient: float
) -> float:
    """
    Calculate KB using Posdunine's formula.

    KB = T × (0.9 - 0.36 × Cb)

    Args:
        draft: Design draft (m)
        block_coefficient: Block coefficient (Cb)

    Returns:
        KB in meters
    """
    return draft * (0.9 - 0.36 * block_coefficient)


def calculate_BM_transverse(
    length_wl: float,
    beam: float,
    draft: float,
    block_coefficient: float,
    waterplane_coefficient: float
) -> float:
    """
    Calculate transverse metacentric radius (BM).

    BM = I / V

    Where:
    - I = second moment of waterplane area about centerline
    - V = displaced volume

    Using approximation: I ≈ Cwp × L × B³ / 12

    Args:
        length_wl: Length at waterline (m)
        beam: Beam (m)
        draft: Draft (m)
        block_coefficient: Block coefficient (Cb)
        waterplane_coefficient: Waterplane coefficient (Cwp)

    Returns:
        BM in meters
    """
    # Second moment of waterplane area (approximation)
    # For a rectangular waterplane: I = L × B³ / 12
    # Corrected for actual waterplane shape: I = Cwp × Cit × L × B³ / 12
    # where Cit is the transverse inertia coefficient (≈ 0.89 for typical hulls)
    Cit = 0.89  # Transverse inertia coefficient
    I = waterplane_coefficient * Cit * length_wl * (beam ** 3) / 12

    # Displaced volume
    V = length_wl * beam * draft * block_coefficient

    return I / V


def calculate_BM_simple(
    beam: float,
    draft: float,
    block_coefficient: float,
    waterplane_coefficient: float
) -> float:
    """
    Simplified BM calculation.

    BM ≈ Cwp × B² / (12 × Cb × T)

    Args:
        beam: Beam (m)
        draft: Draft (m)
        block_coefficient: Block coefficient (Cb)
        waterplane_coefficient: Waterplane coefficient (Cwp)

    Returns:
        BM in meters
    """
    return waterplane_coefficient * (beam ** 2) / (12 * block_coefficient * draft)


def calculate_GM(
    KB: float,
    BM: float,
    KG: float
) -> float:
    """
    Calculate metacentric height (GM).

    GM = KB + BM - KG = KM - KG

    Args:
        KB: Center of buoyancy height (m)
        BM: Metacentric radius (m)
        KG: Center of gravity height (m)

    Returns:
        GM in meters (positive = stable, negative = unstable)
    """
    return KB + BM - KG


def estimate_KG(
    depth: float,
    hull_type: str = "displacement"
) -> float:
    """
    Estimate center of gravity height (KG) based on typical values.

    This is a rough approximation - actual KG depends on loading condition.

    Args:
        depth: Molded depth (m)
        hull_type: Type of vessel

    Returns:
        Estimated KG in meters
    """
    # Typical KG/D ratios
    kg_ratios = {
        "displacement": 0.55,
        "semi_displacement": 0.50,
        "planing": 0.45,
        "catamaran": 0.60,
    }
    ratio = kg_ratios.get(hull_type, 0.55)
    return depth * ratio


def calculate_GZ_at_heel(
    GM: float,
    heel_angle_deg: float,
    beam: float,
    freeboard: Optional[float] = None
) -> float:
    """
    Calculate righting arm (GZ) at a given heel angle.

    Using the wall-sided formula for small angles:
    GZ = GM × sin(φ)

    For larger angles, includes beam correction:
    GZ = (GM + BM × tan²(φ)/2) × sin(φ)

    Args:
        GM: Metacentric height (m)
        heel_angle_deg: Heel angle (degrees)
        beam: Beam (m)
        freeboard: Freeboard (m), for deck edge immersion

    Returns:
        GZ value in meters
    """
    phi = math.radians(heel_angle_deg)

    if abs(heel_angle_deg) < 10:
        # Small angle approximation
        gz = GM * math.sin(phi)
    else:
        # Large angle correction (simplified)
        # This is a simplification - full calculation requires hull geometry
        tan_phi = math.tan(phi)
        gz = GM * math.sin(phi) + 0.5 * (beam / 12) * (tan_phi ** 2) * math.sin(phi)

    return gz


def calculate_GZ_curve(
    GM: float,
    beam: float,
    max_angle: float = 90.0,
    angle_step: float = 5.0
) -> Tuple[List[float], List[float]]:
    """
    Calculate the GZ curve (righting arm vs heel angle).

    Args:
        GM: Metacentric height (m)
        beam: Beam (m)
        max_angle: Maximum heel angle to calculate (degrees)
        angle_step: Step between angles (degrees)

    Returns:
        Tuple of (heel_angles, gz_values)
    """
    angles = []
    gz_values = []

    angle = 0.0
    while angle <= max_angle:
        angles.append(angle)
        gz = calculate_GZ_at_heel(GM, angle, beam)
        gz_values.append(gz)
        angle += angle_step

    return angles, gz_values


def find_max_GZ(gz_values: List[float], angles: List[float]) -> Tuple[float, float]:
    """
    Find maximum GZ and the angle at which it occurs.

    Args:
        gz_values: List of GZ values
        angles: Corresponding heel angles

    Returns:
        Tuple of (max_gz, angle_at_max_gz)
    """
    max_gz = max(gz_values)
    max_idx = gz_values.index(max_gz)
    angle_at_max = angles[max_idx]
    return max_gz, angle_at_max


def find_range_positive_stability(gz_values: List[float], angles: List[float]) -> float:
    """
    Find the range of positive stability (angle where GZ becomes zero).

    Args:
        gz_values: List of GZ values
        angles: Corresponding heel angles

    Returns:
        Range of positive stability in degrees
    """
    for i, gz in enumerate(gz_values):
        if gz <= 0 and i > 0:
            # Interpolate to find zero crossing
            prev_gz = gz_values[i - 1]
            prev_angle = angles[i - 1]
            curr_angle = angles[i]

            # Linear interpolation
            if prev_gz != gz:
                zero_angle = prev_angle + (curr_angle - prev_angle) * prev_gz / (prev_gz - gz)
                return zero_angle

    # If GZ never goes negative, return the max angle
    return angles[-1]


def check_IMO_A749_criteria(
    GM: float,
    gz_values: List[float],
    angles: List[float],
    severe_wind_heeling_moment: Optional[float] = None
) -> Tuple[bool, dict]:
    """
    Check IMO A.749(18) intact stability criteria.

    Criteria for passenger and cargo ships:
    1. Area under GZ curve 0-30° >= 0.055 m·rad
    2. Area under GZ curve 0-40° (or flood angle) >= 0.09 m·rad
    3. Area under GZ curve 30-40° >= 0.03 m·rad
    4. GZ at 30° >= 0.20 m
    5. Maximum GZ at angle >= 25°
    6. GM >= 0.15 m

    Args:
        GM: Metacentric height (m)
        gz_values: List of GZ values
        angles: Corresponding heel angles (degrees)
        severe_wind_heeling_moment: Optional wind heeling moment for weather criterion

    Returns:
        Tuple of (all_passed, criteria_details)
    """
    criteria = {}

    # Criterion 1: Area 0-30° >= 0.055 m·rad
    area_0_30 = _calculate_area_under_curve(gz_values, angles, 0, 30)
    criteria['area_0_30'] = {
        'value': area_0_30,
        'required': 0.055,
        'passed': area_0_30 >= 0.055,
        'unit': 'm·rad'
    }

    # Criterion 2: Area 0-40° >= 0.09 m·rad
    area_0_40 = _calculate_area_under_curve(gz_values, angles, 0, 40)
    criteria['area_0_40'] = {
        'value': area_0_40,
        'required': 0.09,
        'passed': area_0_40 >= 0.09,
        'unit': 'm·rad'
    }

    # Criterion 3: Area 30-40° >= 0.03 m·rad
    area_30_40 = _calculate_area_under_curve(gz_values, angles, 30, 40)
    criteria['area_30_40'] = {
        'value': area_30_40,
        'required': 0.03,
        'passed': area_30_40 >= 0.03,
        'unit': 'm·rad'
    }

    # Criterion 4: GZ at 30° >= 0.20 m
    gz_30 = _interpolate_gz(gz_values, angles, 30)
    criteria['gz_at_30'] = {
        'value': gz_30,
        'required': 0.20,
        'passed': gz_30 >= 0.20,
        'unit': 'm'
    }

    # Criterion 5: Maximum GZ at angle >= 25°
    max_gz, angle_max = find_max_GZ(gz_values, angles)
    criteria['angle_of_max_gz'] = {
        'value': angle_max,
        'required': 25,
        'passed': angle_max >= 25,
        'unit': '°'
    }

    # Criterion 6: GM >= 0.15 m
    criteria['gm'] = {
        'value': GM,
        'required': 0.15,
        'passed': GM >= 0.15,
        'unit': 'm'
    }

    all_passed = all(c['passed'] for c in criteria.values())

    return all_passed, criteria


def _calculate_area_under_curve(
    gz_values: List[float],
    angles: List[float],
    start_angle: float,
    end_angle: float
) -> float:
    """
    Calculate area under GZ curve using trapezoidal rule.

    Args:
        gz_values: List of GZ values
        angles: Corresponding heel angles (degrees)
        start_angle: Start of integration (degrees)
        end_angle: End of integration (degrees)

    Returns:
        Area in m·rad
    """
    area = 0.0

    for i in range(len(angles) - 1):
        if angles[i] >= start_angle and angles[i + 1] <= end_angle:
            # Convert degrees to radians for area calculation
            d_angle = math.radians(angles[i + 1] - angles[i])
            avg_gz = (gz_values[i] + gz_values[i + 1]) / 2
            area += avg_gz * d_angle

    return area


def _interpolate_gz(gz_values: List[float], angles: List[float], target_angle: float) -> float:
    """
    Interpolate GZ value at a specific angle.

    Args:
        gz_values: List of GZ values
        angles: Corresponding heel angles
        target_angle: Angle to interpolate to

    Returns:
        Interpolated GZ value
    """
    for i in range(len(angles) - 1):
        if angles[i] <= target_angle <= angles[i + 1]:
            # Linear interpolation
            t = (target_angle - angles[i]) / (angles[i + 1] - angles[i])
            return gz_values[i] + t * (gz_values[i + 1] - gz_values[i])

    # If target is beyond range, return last value
    return gz_values[-1] if target_angle > angles[-1] else gz_values[0]


def calculate_stability(
    length_wl: float,
    beam: float,
    draft: float,
    depth: float,
    block_coefficient: float,
    waterplane_coefficient: float,
    KG: Optional[float] = None,
    hull_type: str = "displacement"
) -> StabilityResult:
    """
    Comprehensive stability calculation.

    Args:
        length_wl: Length at waterline (m)
        beam: Beam (m)
        draft: Draft (m)
        depth: Molded depth (m)
        block_coefficient: Block coefficient (Cb)
        waterplane_coefficient: Waterplane coefficient (Cwp)
        KG: Center of gravity height (m), if None will be estimated
        hull_type: Type of vessel for KG estimation

    Returns:
        StabilityResult with all stability parameters
    """
    # Calculate displacement
    volume = length_wl * beam * draft * block_coefficient
    displacement = volume * SEAWATER_DENSITY

    # Calculate KB using Morrish's formula
    KB = calculate_KB_morrish(draft, block_coefficient, waterplane_coefficient)

    # Calculate BM
    BM = calculate_BM_transverse(
        length_wl, beam, draft, block_coefficient, waterplane_coefficient
    )

    # KG (estimated if not provided)
    if KG is None:
        KG = estimate_KG(depth, hull_type)

    # Calculate GM
    GM = calculate_GM(KB, BM, KG)
    KM = KB + BM

    # Calculate GZ curve
    angles, gz_values = calculate_GZ_curve(GM, beam)

    # Find key GZ values
    max_gz, angle_max_gz = find_max_GZ(gz_values, angles)
    range_stability = find_range_positive_stability(gz_values, angles)

    # Check IMO criteria
    imo_passed, imo_details = check_IMO_A749_criteria(GM, gz_values, angles)

    return StabilityResult(
        GM=GM,
        KB=KB,
        KG=KG,
        BM=BM,
        KM=KM,
        displacement=displacement,
        heel_angles=angles,
        gz_values=gz_values,
        max_gz=max_gz,
        angle_max_gz=angle_max_gz,
        range_positive_stability=range_stability,
        imo_criteria_passed=imo_passed,
        imo_criteria_details=imo_details
    )


def calculate_stability_from_hull(
    hull: "HullParamsSchema",
    KG: Optional[float] = None
) -> StabilityResult:
    """
    Calculate stability from HullParamsSchema.

    Args:
        hull: HullParamsSchema instance
        KG: Center of gravity height (m), if None will be estimated

    Returns:
        StabilityResult with all stability parameters
    """
    hull_type = hull.hull_type.value if hasattr(hull, 'hull_type') and hull.hull_type else "displacement"

    return calculate_stability(
        length_wl=hull.length_waterline,
        beam=hull.beam,
        draft=hull.draft,
        depth=hull.depth,
        block_coefficient=hull.block_coefficient,
        waterplane_coefficient=hull.waterplane_coefficient,
        KG=KG,
        hull_type=hull_type
    )


def generate_stability_report(result: StabilityResult) -> str:
    """
    Generate a human-readable stability report.

    Args:
        result: StabilityResult from stability calculation

    Returns:
        Formatted report string
    """
    lines = [
        "=" * 50,
        "STABILITY ANALYSIS REPORT",
        "=" * 50,
        "",
        "HYDROSTATIC PARAMETERS",
        "-" * 30,
        f"  Displacement:        {result.displacement:>10.1f} tonnes",
        f"  KB (center of B):    {result.KB:>10.3f} m",
        f"  KG (center of G):    {result.KG:>10.3f} m",
        f"  BM (metacentric R):  {result.BM:>10.3f} m",
        f"  KM (metacenter):     {result.KM:>10.3f} m",
        f"  GM (metacentric H):  {result.GM:>10.3f} m",
        "",
        "STABILITY CHARACTERISTICS",
        "-" * 30,
        f"  Maximum GZ:          {result.max_gz:>10.3f} m",
        f"  Angle at max GZ:     {result.angle_max_gz:>10.1f}°",
        f"  Range of stability:  {result.range_positive_stability:>10.1f}°",
        "",
        "IMO A.749 CRITERIA",
        "-" * 30,
    ]

    for name, details in result.imo_criteria_details.items():
        status = "✓ PASS" if details['passed'] else "✗ FAIL"
        lines.append(
            f"  {name:20} {details['value']:>8.3f} {details['unit']:>6} "
            f"(req: {details['required']:.3f}) [{status}]"
        )

    lines.extend([
        "",
        "-" * 30,
        f"OVERALL: {'STABLE' if result.is_stable() else 'UNSTABLE'}",
        "=" * 50,
    ])

    return "\n".join(lines)
