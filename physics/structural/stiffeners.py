"""
Stiffener and frame calculations for hull structure.

Implements ABS HSNC 2023 stiffener requirements:
- Section modulus requirements
- Frame spacing calculations
- Standard profile selection

References:
- ABS HSNC 2023 Part 3, Chapter 3, Section 3 - Framing
- ABS HSNC 2023 Table 3-3-3/5.1 - Section Modulus Requirements
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

from .materials import (
    AluminumAlloy,
    MaterialProperties,
    get_alloy_properties,
    DEFAULT_ALLOY,
)
from .pressure import PressureZone, PressureResult


class StiffenerType(Enum):
    """Standard stiffener profile types."""
    FLAT_BAR = "flat_bar"
    ANGLE = "angle"
    TEE = "tee"
    BULB_FLAT = "bulb_flat"
    CHANNEL = "channel"


@dataclass
class StiffenerProfile:
    """Standard stiffener profile definition."""
    type: StiffenerType
    designation: str           # e.g., "L 100x75x8"
    height: float              # mm (web height)
    width: float               # mm (flange width)
    web_thickness: float       # mm
    flange_thickness: float    # mm
    section_modulus: float     # cm³
    moment_of_inertia: float   # cm⁴
    area: float                # cm²
    weight_per_meter: float    # kg/m


# Standard aluminum angle profiles (common marine sizes)
STANDARD_ANGLES: List[StiffenerProfile] = [
    StiffenerProfile(StiffenerType.ANGLE, "L 50x50x5", 50, 50, 5, 5, 3.55, 11.0, 4.80, 1.28),
    StiffenerProfile(StiffenerType.ANGLE, "L 60x60x6", 60, 60, 6, 6, 6.19, 22.8, 6.91, 1.84),
    StiffenerProfile(StiffenerType.ANGLE, "L 75x75x6", 75, 75, 6, 6, 9.67, 44.8, 8.71, 2.32),
    StiffenerProfile(StiffenerType.ANGLE, "L 75x75x8", 75, 75, 8, 8, 12.5, 56.5, 11.5, 3.06),
    StiffenerProfile(StiffenerType.ANGLE, "L 80x80x8", 80, 80, 8, 8, 14.4, 68.5, 12.3, 3.28),
    StiffenerProfile(StiffenerType.ANGLE, "L 100x75x8", 100, 75, 8, 8, 18.2, 112.0, 13.5, 3.60),
    StiffenerProfile(StiffenerType.ANGLE, "L 100x100x10", 100, 100, 10, 10, 28.2, 177.0, 19.2, 5.12),
    StiffenerProfile(StiffenerType.ANGLE, "L 120x80x10", 120, 80, 10, 10, 33.8, 252.0, 19.2, 5.12),
    StiffenerProfile(StiffenerType.ANGLE, "L 120x120x12", 120, 120, 12, 12, 48.6, 368.0, 27.5, 7.33),
    StiffenerProfile(StiffenerType.ANGLE, "L 150x100x12", 150, 100, 12, 12, 64.5, 605.0, 28.7, 7.65),
    StiffenerProfile(StiffenerType.ANGLE, "L 150x150x15", 150, 150, 15, 15, 95.8, 902.0, 43.2, 11.5),
]

# Standard flat bars (for smaller stiffeners)
STANDARD_FLAT_BARS: List[StiffenerProfile] = [
    StiffenerProfile(StiffenerType.FLAT_BAR, "FB 60x6", 60, 6, 6, 6, 3.60, 10.8, 3.60, 0.96),
    StiffenerProfile(StiffenerType.FLAT_BAR, "FB 80x8", 80, 8, 8, 8, 8.53, 34.1, 6.40, 1.71),
    StiffenerProfile(StiffenerType.FLAT_BAR, "FB 100x10", 100, 10, 10, 10, 16.7, 83.3, 10.0, 2.67),
    StiffenerProfile(StiffenerType.FLAT_BAR, "FB 120x12", 120, 12, 12, 12, 28.8, 173.0, 14.4, 3.84),
    StiffenerProfile(StiffenerType.FLAT_BAR, "FB 150x12", 150, 12, 12, 12, 45.0, 338.0, 18.0, 4.80),
]

# Standard tee profiles
STANDARD_TEES: List[StiffenerProfile] = [
    StiffenerProfile(StiffenerType.TEE, "T 75x50x6", 75, 50, 6, 6, 8.75, 32.8, 7.20, 1.92),
    StiffenerProfile(StiffenerType.TEE, "T 100x65x8", 100, 65, 8, 8, 19.2, 96.0, 12.4, 3.30),
    StiffenerProfile(StiffenerType.TEE, "T 120x80x10", 120, 80, 10, 10, 35.2, 211.0, 19.2, 5.12),
    StiffenerProfile(StiffenerType.TEE, "T 150x100x12", 150, 100, 12, 12, 62.5, 469.0, 28.8, 7.68),
]

# All standard profiles
STANDARD_PROFILES = STANDARD_FLAT_BARS + STANDARD_ANGLES + STANDARD_TEES


@dataclass
class StiffenerResult:
    """Result of stiffener calculation with audit trail."""
    zone: str
    required_section_modulus: float  # cm³
    selected_profile: Optional[StiffenerProfile]
    actual_section_modulus: float    # cm³

    # Compliance
    is_compliant: bool
    margin_percent: float

    # Design parameters
    design_pressure: float           # kN/m²
    stiffener_spacing: float         # mm
    frame_spacing: float             # mm
    span: float                      # mm (unsupported length)
    allowable_stress: float          # MPa

    # Material
    alloy: str
    in_haz: bool

    # Reference
    rule_reference: str
    formula: str
    calculation_notes: List[str] = field(default_factory=list)


def calculate_frame_spacing(
    length_wl: float,
    beam: float,
    draft: float,
    speed_kts: float,
    zone: PressureZone = PressureZone.BOTTOM_MIDSHIP,
) -> float:
    """
    Calculate recommended frame spacing.

    ABS HSNC provides guidance based on vessel size and service.
    Typical range: 400-800mm for high-speed craft.

    Args:
        length_wl: Length at waterline (m)
        beam: Beam (m)
        draft: Draft (m)
        speed_kts: Design speed (knots)
        zone: Structural zone

    Returns:
        Recommended frame spacing (mm)
    """
    # Base spacing from vessel length
    # Smaller vessels = tighter spacing
    if length_wl < 20:
        base_spacing = 400
    elif length_wl < 35:
        base_spacing = 500
    elif length_wl < 50:
        base_spacing = 600
    else:
        base_spacing = 700

    # Speed factor - higher speed = tighter spacing
    froude = speed_kts * 0.5144 / math.sqrt(9.81 * length_wl)
    if froude > 0.6:
        speed_factor = 0.85
    elif froude > 0.4:
        speed_factor = 0.92
    else:
        speed_factor = 1.0

    # Zone factor - forward bottom needs tighter spacing
    zone_factors = {
        PressureZone.BOTTOM_FORWARD: 0.85,
        PressureZone.BOTTOM_MIDSHIP: 1.0,
        PressureZone.BOTTOM_AFT: 1.05,
        PressureZone.SIDE_FORWARD: 0.90,
        PressureZone.SIDE_MIDSHIP: 1.0,
        PressureZone.SIDE_AFT: 1.05,
        PressureZone.DECK_WEATHER: 1.1,
        PressureZone.DECK_INTERNAL: 1.15,
    }
    zone_factor = zone_factors.get(zone, 1.0)

    spacing = base_spacing * speed_factor * zone_factor

    # Round to standard increments (50mm)
    spacing = round(spacing / 50) * 50

    # Limits
    spacing = max(300, min(800, spacing))

    return spacing


def calculate_stiffener_section_modulus(
    design_pressure: float,
    stiffener_spacing: float,
    frame_spacing: float,
    alloy: AluminumAlloy = DEFAULT_ALLOY,
    in_haz: bool = True,
    end_fixity: float = 12.0,
) -> Tuple[float, str, List[str]]:
    """
    Calculate required section modulus for stiffener.

    ABS HSNC 3-3-3/5.1:
    SM = (p × s × l²) / (C × σ_a)

    where:
        SM = section modulus (cm³)
        p = design pressure (kN/m²)
        s = stiffener spacing (m)
        l = span (frame spacing) (m)
        C = end fixity factor (12 for clamped, 10 for supported)
        σ_a = allowable stress (MPa)

    Args:
        design_pressure: Design pressure (kN/m²)
        stiffener_spacing: Stiffener spacing (mm)
        frame_spacing: Frame/span (mm)
        alloy: Aluminum alloy
        in_haz: Calculate for HAZ
        end_fixity: End fixity factor (8-12)

    Returns:
        Tuple of (section_modulus_cm3, formula, notes)
    """
    props = get_alloy_properties(alloy)

    # Allowable stress
    if in_haz:
        sigma_a = props.allowable_stress_haz
    else:
        sigma_a = props.allowable_stress

    # Convert to meters for formula
    s = stiffener_spacing / 1000  # m
    l = frame_spacing / 1000      # m

    # Calculate section modulus
    # SM = (p × s × l²) / (C × σ_a) × 1000 for cm³
    if sigma_a <= 0:
        sm_required = 0.0
    else:
        sm_required = (design_pressure * s * l**2) / (end_fixity * sigma_a) * 1000

    formula = f"SM = (p × s × l²) / (C × σ_a) = ({design_pressure:.1f} × {s:.3f} × {l:.3f}²) / ({end_fixity} × {sigma_a:.1f}) × 1000"

    notes = [
        f"Design pressure: p = {design_pressure:.1f} kN/m²",
        f"Stiffener spacing: s = {stiffener_spacing:.0f} mm",
        f"Span (frame spacing): l = {frame_spacing:.0f} mm",
        f"End fixity factor: C = {end_fixity:.0f}",
        f"Allowable stress: σ_a = {sigma_a:.1f} MPa ({'HAZ' if in_haz else 'parent'})",
        f"Required SM: {sm_required:.2f} cm³",
    ]

    return sm_required, formula, notes


def select_stiffener_profile(
    required_sm: float,
    max_height: float = 200.0,
    preferred_type: Optional[StiffenerType] = None,
) -> Optional[StiffenerProfile]:
    """
    Select standard profile that meets section modulus requirement.

    Args:
        required_sm: Required section modulus (cm³)
        max_height: Maximum stiffener height (mm)
        preferred_type: Preferred profile type (optional)

    Returns:
        StiffenerProfile or None if no suitable profile found
    """
    # Filter by type if specified
    if preferred_type:
        candidates = [p for p in STANDARD_PROFILES if p.type == preferred_type]
    else:
        candidates = STANDARD_PROFILES

    # Filter by height
    candidates = [p for p in candidates if p.height <= max_height]

    # Sort by section modulus
    candidates.sort(key=lambda p: p.section_modulus)

    # Find smallest profile that meets requirement
    for profile in candidates:
        if profile.section_modulus >= required_sm:
            return profile

    # If no standard profile works, return largest available
    if candidates:
        return candidates[-1]

    return None


def calculate_stiffener_result(
    zone: PressureZone,
    pressure_result: PressureResult,
    stiffener_spacing: float,
    frame_spacing: float,
    alloy: AluminumAlloy = DEFAULT_ALLOY,
    in_haz: bool = True,
    max_height: float = 200.0,
) -> StiffenerResult:
    """
    Calculate complete stiffener result for a zone.

    Args:
        zone: Pressure zone
        pressure_result: PressureResult from pressure calculation
        stiffener_spacing: Stiffener spacing (mm)
        frame_spacing: Frame spacing (mm)
        alloy: Aluminum alloy
        in_haz: Calculate for HAZ
        max_height: Maximum stiffener height (mm)

    Returns:
        StiffenerResult with full audit trail
    """
    props = get_alloy_properties(alloy)

    # Calculate required section modulus
    sm_required, formula, notes = calculate_stiffener_section_modulus(
        design_pressure=pressure_result.design_pressure,
        stiffener_spacing=stiffener_spacing,
        frame_spacing=frame_spacing,
        alloy=alloy,
        in_haz=in_haz,
    )

    # Select profile
    profile = select_stiffener_profile(sm_required, max_height)

    if profile:
        sm_actual = profile.section_modulus
        is_compliant = sm_actual >= sm_required
        margin = ((sm_actual - sm_required) / sm_required * 100) if sm_required > 0 else 0

        notes.extend([
            f"",
            f"Selected profile: {profile.designation}",
            f"Actual SM: {sm_actual:.2f} cm³",
            f"Margin: {margin:.1f}%",
            f"Weight: {profile.weight_per_meter:.2f} kg/m",
            f"Compliance: {'PASS' if is_compliant else 'FAIL'}",
        ])
    else:
        sm_actual = 0.0
        is_compliant = False
        margin = -100.0
        notes.append("WARNING: No suitable standard profile found")

    sigma_a = props.allowable_stress_haz if in_haz else props.allowable_stress

    return StiffenerResult(
        zone=zone.value,
        required_section_modulus=sm_required,
        selected_profile=profile,
        actual_section_modulus=sm_actual,
        is_compliant=is_compliant,
        margin_percent=margin,
        design_pressure=pressure_result.design_pressure,
        stiffener_spacing=stiffener_spacing,
        frame_spacing=frame_spacing,
        span=frame_spacing,
        allowable_stress=sigma_a,
        alloy=alloy.value,
        in_haz=in_haz,
        rule_reference="ABS HSNC 2023 3-3-3/5.1",
        formula=formula,
        calculation_notes=notes,
    )


def calculate_all_stiffeners(
    pressure_results: Dict[PressureZone, PressureResult],
    stiffener_spacing: float,
    frame_spacing: float,
    alloy: AluminumAlloy = DEFAULT_ALLOY,
) -> Dict[PressureZone, StiffenerResult]:
    """
    Calculate stiffeners for all zones.

    Args:
        pressure_results: Dict of zone pressure results
        stiffener_spacing: Stiffener spacing (mm)
        frame_spacing: Frame spacing (mm)
        alloy: Aluminum alloy

    Returns:
        Dict of PressureZone -> StiffenerResult
    """
    results = {}

    # Different max heights by zone
    max_heights = {
        PressureZone.BOTTOM_FORWARD: 150,
        PressureZone.BOTTOM_MIDSHIP: 120,
        PressureZone.BOTTOM_AFT: 100,
        PressureZone.SIDE_FORWARD: 120,
        PressureZone.SIDE_MIDSHIP: 100,
        PressureZone.SIDE_AFT: 100,
        PressureZone.DECK_WEATHER: 80,
        PressureZone.DECK_INTERNAL: 80,
    }

    for zone, pressure in pressure_results.items():
        max_h = max_heights.get(zone, 120)
        results[zone] = calculate_stiffener_result(
            zone=zone,
            pressure_result=pressure,
            stiffener_spacing=stiffener_spacing,
            frame_spacing=frame_spacing,
            alloy=alloy,
            max_height=max_h,
        )

    return results


def generate_stiffener_report(
    results: Dict[PressureZone, StiffenerResult],
    vessel_name: str = "Vessel",
) -> str:
    """Generate human-readable stiffener schedule report."""
    lines = [
        f"STIFFENER SCHEDULE - {vessel_name}",
        "=" * 80,
        "",
        "Reference: ABS HSNC 2023 Part 3, Chapter 3, Section 3",
        "",
        "STIFFENER SIZING BY ZONE",
        "-" * 80,
        f"{'Zone':<25} {'Pressure':>10} {'Req SM':>10} {'Profile':<18} {'Act SM':>10} {'Status':>8}",
        f"{'':<25} {'(kN/m²)':>10} {'(cm³)':>10} {'':>18} {'(cm³)':>10} {'':>8}",
        "-" * 80,
    ]

    total_weight = 0.0
    for zone, result in results.items():
        status = "✓ PASS" if result.is_compliant else "✗ FAIL"
        profile_name = result.selected_profile.designation if result.selected_profile else "N/A"

        lines.append(
            f"{result.zone:<25} {result.design_pressure:>10.1f} "
            f"{result.required_section_modulus:>10.2f} {profile_name:<18} "
            f"{result.actual_section_modulus:>10.2f} {status:>8}"
        )

        if result.selected_profile:
            # Estimate weight: frame_spacing * number of stiffeners * weight/m
            # Simplified: assume ~10 stiffeners per zone typical
            total_weight += result.selected_profile.weight_per_meter * (result.frame_spacing / 1000) * 10

    lines.extend([
        "",
        "STANDARD PROFILES USED",
        "-" * 40,
    ])

    used_profiles = set()
    for result in results.values():
        if result.selected_profile:
            used_profiles.add(result.selected_profile.designation)

    for profile_name in sorted(used_profiles):
        profile = next((p for p in STANDARD_PROFILES if p.designation == profile_name), None)
        if profile:
            lines.append(
                f"{profile.designation:<15} SM={profile.section_modulus:>6.1f} cm³  "
                f"I={profile.moment_of_inertia:>6.1f} cm⁴  wt={profile.weight_per_meter:.2f} kg/m"
            )

    lines.extend([
        "",
        f"Estimated Stiffener Weight: {total_weight:.0f} kg (approximate)",
        "",
    ])

    return "\n".join(lines)
