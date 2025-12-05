"""
Plate thickness calculations for hull structure.

Implements ABS HSNC 2023 plating requirements:
- Minimum thickness by location
- Required thickness from design pressure
- Commercial size quantization

References:
- ABS HSNC 2023 Part 3, Chapter 3, Section 2 - Shell Plating
- ABS HSNC 2023 Table 3-3-2/5.1 - Plating Requirements
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
    ALLOWED_ALLOYS,
)
from .pressure import PressureZone, PressureResult


# Commercial plate thickness increments (mm)
COMMERCIAL_THICKNESSES = [
    3.0, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 8.0, 9.0, 10.0,
    11.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 25.0, 28.0, 30.0,
]


class BoundaryCondition(Enum):
    """Plate boundary conditions for stress calculation."""
    CLAMPED = "clamped"           # k = 0.5 - welded edges
    SIMPLY_SUPPORTED = "simply_supported"  # k = 0.7
    FREE_EDGE = "free_edge"       # k = 1.0


# Boundary condition factors per ABS HSNC
BOUNDARY_FACTORS = {
    BoundaryCondition.CLAMPED: 0.50,
    BoundaryCondition.SIMPLY_SUPPORTED: 0.70,
    BoundaryCondition.FREE_EDGE: 1.00,
}


@dataclass
class PlatingResult:
    """Result of plate thickness calculation with audit trail."""
    zone: str
    required_thickness: float      # mm (from calculation)
    minimum_thickness: float       # mm (code minimum)
    proposed_thickness: float      # mm (commercial size)

    # Compliance
    is_compliant: bool
    margin_percent: float          # % above required

    # Inputs used
    design_pressure: float         # kN/m²
    stiffener_spacing: float       # mm
    allowable_stress: float        # MPa
    boundary_factor: float         # k factor

    # Material
    alloy: str
    in_haz: bool
    corrosion_allowance: float     # mm

    # Reference
    rule_reference: str
    formula: str
    calculation_notes: List[str] = field(default_factory=list)


@dataclass
class PlatingSchedule:
    """Complete plating schedule for vessel."""
    zones: Dict[str, PlatingResult]
    total_plate_weight: float      # kg (estimated)
    average_thickness: float       # mm

    # Summary by zone type
    bottom_thickness: float        # mm (max)
    side_thickness: float          # mm (max)
    deck_thickness: float          # mm (max)

    # Design parameters
    alloy: str
    stiffener_spacing: float       # mm
    frame_spacing: float           # mm

    rule_reference: str


def calculate_minimum_thickness(
    zone: PressureZone,
    length_wl: float,
    alloy: AluminumAlloy = DEFAULT_ALLOY,
) -> float:
    """
    Calculate minimum plate thickness per ABS HSNC.

    ABS HSNC 3-3-2/3.3: Minimum thickness requirements
    t_min = 0.70 × √L + 1.0 mm (bottom)
    t_min = 0.62 × √L + 0.5 mm (sides)

    Absolute minimum: 4.0 mm for primary structure

    Args:
        zone: PressureZone
        length_wl: Length at waterline (m)
        alloy: Aluminum alloy

    Returns:
        Minimum thickness in mm
    """
    # ABS HSNC absolute minimum
    absolute_min = 4.0  # mm

    # Zone-based minimums (ABS HSNC 3-3-2/3.3)
    sqrt_l = math.sqrt(length_wl)

    zone_minimums = {
        # Bottom shell - highest requirements
        PressureZone.BOTTOM_FORWARD: 0.70 * sqrt_l + 1.5,
        PressureZone.BOTTOM_MIDSHIP: 0.70 * sqrt_l + 1.0,
        PressureZone.BOTTOM_AFT: 0.65 * sqrt_l + 1.0,

        # Side shell
        PressureZone.SIDE_FORWARD: 0.62 * sqrt_l + 1.0,
        PressureZone.SIDE_MIDSHIP: 0.62 * sqrt_l + 0.5,
        PressureZone.SIDE_AFT: 0.60 * sqrt_l + 0.5,

        # Deck
        PressureZone.DECK_WEATHER: 0.55 * sqrt_l + 0.5,
        PressureZone.DECK_INTERNAL: 0.50 * sqrt_l + 0.0,

        # Special areas
        PressureZone.TRANSOM: 0.65 * sqrt_l + 1.0,
        PressureZone.BOW_FLARE: 0.75 * sqrt_l + 1.5,
        PressureZone.WETDECK: 0.70 * sqrt_l + 1.5,

        # Superstructure (lighter)
        PressureZone.SUPERSTRUCTURE_FRONT: 0.50 * sqrt_l + 0.5,
        PressureZone.SUPERSTRUCTURE_SIDE: 0.45 * sqrt_l + 0.5,
        PressureZone.SUPERSTRUCTURE_AFT: 0.45 * sqrt_l + 0.5,
    }

    zone_min = zone_minimums.get(zone, 0.60 * sqrt_l + 0.5)

    # Material factor - stronger alloys can be slightly thinner
    props = get_alloy_properties(alloy)
    material_factor = 215.0 / props.yield_strength  # Relative to 5083-H116
    material_factor = max(0.90, min(1.10, material_factor))

    zone_min *= material_factor

    return max(absolute_min, zone_min)


def calculate_plate_thickness(
    design_pressure: float,
    stiffener_spacing: float,
    alloy: AluminumAlloy = DEFAULT_ALLOY,
    boundary_condition: BoundaryCondition = BoundaryCondition.CLAMPED,
    in_haz: bool = True,
    corrosion_allowance: float = 0.5,
) -> Tuple[float, str, List[str]]:
    """
    Calculate required plate thickness per ABS HSNC 2023.

    ABS HSNC 3-3-2/5.1:
    t = s × √(p × k / σ_a) + t_c

    where:
        t = required thickness (mm)
        s = stiffener spacing (mm)
        p = design pressure (kN/m² = kPa)
        k = boundary condition factor
        σ_a = allowable stress (MPa)
        t_c = corrosion allowance (mm)

    Args:
        design_pressure: Design pressure (kN/m²)
        stiffener_spacing: Stiffener spacing (mm)
        alloy: Aluminum alloy
        boundary_condition: Plate boundary condition
        in_haz: Calculate for heat-affected zone (conservative)
        corrosion_allowance: Corrosion allowance (mm)

    Returns:
        Tuple of (thickness_mm, formula_string, calculation_notes)
    """
    props = get_alloy_properties(alloy)

    # Get allowable stress
    if in_haz:
        sigma_a = props.allowable_stress_haz
    else:
        sigma_a = props.allowable_stress

    # Boundary factor
    k = BOUNDARY_FACTORS[boundary_condition]

    # Calculate required thickness
    # ABS formula: t = s × √(p × k / σ_a)
    # Units: s in mm, p in kN/m² (need to convert to N/mm²), σ_a in MPa (N/mm²)
    # 1 kN/m² = 0.001 N/mm²
    s = stiffener_spacing  # mm
    p_nmm2 = design_pressure * 0.001  # Convert kN/m² to N/mm²

    # ABS formula
    if sigma_a <= 0 or design_pressure <= 0:
        t_calc = 0.0
    else:
        t_calc = s * math.sqrt(p_nmm2 * k / sigma_a)

    # Add corrosion allowance
    t_required = t_calc + corrosion_allowance

    # Formula string for documentation
    formula = f"t = s × √(p × k / σ_a) + t_c = {s:.0f} × √({design_pressure:.1f} × {k:.2f} / {sigma_a:.1f}) + {corrosion_allowance:.1f}"

    # Calculation notes
    notes = [
        f"Design pressure: p = {design_pressure:.1f} kN/m²",
        f"Stiffener spacing: s = {stiffener_spacing:.0f} mm",
        f"Boundary factor: k = {k:.2f} ({boundary_condition.value})",
        f"Allowable stress: σ_a = {sigma_a:.1f} MPa ({'HAZ' if in_haz else 'parent'})",
        f"Corrosion allowance: t_c = {corrosion_allowance:.1f} mm",
        f"Calculated thickness: t_calc = {t_calc:.2f} mm",
        f"Required thickness: t = {t_required:.2f} mm",
    ]

    return t_required, formula, notes


def quantize_to_commercial(thickness: float) -> float:
    """
    Round thickness up to next commercial plate size.

    Args:
        thickness: Required thickness (mm)

    Returns:
        Next commercial thickness (mm)
    """
    for commercial in COMMERCIAL_THICKNESSES:
        if commercial >= thickness:
            return commercial

    # If larger than standard, round up to 1mm
    return math.ceil(thickness)


def generate_plating_result(
    zone: PressureZone,
    pressure_result: PressureResult,
    stiffener_spacing: float,
    length_wl: float,
    alloy: AluminumAlloy = DEFAULT_ALLOY,
    boundary_condition: BoundaryCondition = BoundaryCondition.CLAMPED,
    in_haz: bool = True,
) -> PlatingResult:
    """
    Generate complete plating result for a zone.

    Args:
        zone: Pressure zone
        pressure_result: PressureResult from pressure calculation
        stiffener_spacing: Stiffener spacing (mm)
        length_wl: Length at waterline (m)
        alloy: Aluminum alloy
        boundary_condition: Plate boundary condition
        in_haz: Calculate for HAZ

    Returns:
        PlatingResult with full audit trail
    """
    props = get_alloy_properties(alloy)

    # Calculate required thickness
    t_required, formula, notes = calculate_plate_thickness(
        design_pressure=pressure_result.design_pressure,
        stiffener_spacing=stiffener_spacing,
        alloy=alloy,
        boundary_condition=boundary_condition,
        in_haz=in_haz,
    )

    # Get minimum thickness
    t_min = calculate_minimum_thickness(zone, length_wl, alloy)

    # Take maximum of required and minimum
    t_governing = max(t_required, t_min)

    # Quantize to commercial size
    t_proposed = quantize_to_commercial(t_governing)

    # Check compliance
    is_compliant = t_proposed >= t_governing
    margin = ((t_proposed - t_governing) / t_governing * 100) if t_governing > 0 else 0

    # Add compliance notes
    notes.extend([
        f"Minimum thickness: t_min = {t_min:.2f} mm (ABS HSNC 3-3-2/3.3)",
        f"Governing thickness: {t_governing:.2f} mm",
        f"Proposed (commercial): {t_proposed:.1f} mm",
        f"Margin: {margin:.1f}%",
        f"Compliance: {'PASS' if is_compliant else 'FAIL'}",
    ])

    k = BOUNDARY_FACTORS[boundary_condition]
    sigma_a = props.allowable_stress_haz if in_haz else props.allowable_stress

    return PlatingResult(
        zone=zone.value,
        required_thickness=t_required,
        minimum_thickness=t_min,
        proposed_thickness=t_proposed,
        is_compliant=is_compliant,
        margin_percent=margin,
        design_pressure=pressure_result.design_pressure,
        stiffener_spacing=stiffener_spacing,
        allowable_stress=sigma_a,
        boundary_factor=k,
        alloy=alloy.value,
        in_haz=in_haz,
        corrosion_allowance=props.corrosion_allowance,
        rule_reference="ABS HSNC 2023 3-3-2/5.1",
        formula=formula,
        calculation_notes=notes,
    )


def generate_plating_schedule(
    pressure_results: Dict[PressureZone, PressureResult],
    stiffener_spacing: float,
    frame_spacing: float,
    length_wl: float,
    beam: float,
    depth: float,
    alloy: AluminumAlloy = DEFAULT_ALLOY,
) -> PlatingSchedule:
    """
    Generate complete plating schedule for vessel.

    Args:
        pressure_results: Dict of zone pressure results
        stiffener_spacing: Stiffener spacing (mm)
        frame_spacing: Frame spacing (mm)
        length_wl: Length at waterline (m)
        beam: Beam (m)
        depth: Depth (m)
        alloy: Aluminum alloy

    Returns:
        PlatingSchedule with all zone results
    """
    zones = {}
    total_weight = 0.0
    thickness_sum = 0.0

    bottom_max = 0.0
    side_max = 0.0
    deck_max = 0.0

    for zone, pressure in pressure_results.items():
        result = generate_plating_result(
            zone=zone,
            pressure_result=pressure,
            stiffener_spacing=stiffener_spacing,
            length_wl=length_wl,
            alloy=alloy,
        )
        zones[zone.value] = result
        thickness_sum += result.proposed_thickness

        # Track maximums by zone type
        if "bottom" in zone.value.lower():
            bottom_max = max(bottom_max, result.proposed_thickness)
        elif "side" in zone.value.lower():
            side_max = max(side_max, result.proposed_thickness)
        elif "deck" in zone.value.lower():
            deck_max = max(deck_max, result.proposed_thickness)

    # Estimate total plate weight
    # Simplified: shell area ≈ (L × girth), girth ≈ 2D + B
    props = get_alloy_properties(alloy)
    girth = 2 * depth + beam
    shell_area = length_wl * girth  # m²
    avg_thickness = thickness_sum / len(zones) if zones else 6.0
    plate_volume = shell_area * (avg_thickness / 1000)  # m³
    total_weight = plate_volume * props.density  # kg

    return PlatingSchedule(
        zones=zones,
        total_plate_weight=total_weight,
        average_thickness=avg_thickness,
        bottom_thickness=bottom_max,
        side_thickness=side_max,
        deck_thickness=deck_max,
        alloy=alloy.value,
        stiffener_spacing=stiffener_spacing,
        frame_spacing=frame_spacing,
        rule_reference="ABS HSNC 2023 Part 3, Chapter 3",
    )


def generate_plating_report(schedule: PlatingSchedule, vessel_name: str = "Vessel") -> str:
    """Generate human-readable plating schedule report."""
    lines = [
        f"PLATING SCHEDULE - {vessel_name}",
        "=" * 70,
        "",
        f"Reference: {schedule.rule_reference}",
        f"Material: {schedule.alloy}",
        f"Stiffener Spacing: {schedule.stiffener_spacing:.0f} mm",
        f"Frame Spacing: {schedule.frame_spacing:.0f} mm",
        "",
        "PLATE THICKNESS BY ZONE",
        "-" * 70,
        f"{'Zone':<25} {'Pressure':>10} {'Required':>10} {'Min':>8} {'Proposed':>10} {'Status':>8}",
        f"{'':<25} {'(kN/m²)':>10} {'(mm)':>10} {'(mm)':>8} {'(mm)':>10} {'':>8}",
        "-" * 70,
    ]

    for zone_name, result in schedule.zones.items():
        status = "✓ PASS" if result.is_compliant else "✗ FAIL"
        lines.append(
            f"{zone_name:<25} {result.design_pressure:>10.1f} "
            f"{result.required_thickness:>10.2f} {result.minimum_thickness:>8.1f} "
            f"{result.proposed_thickness:>10.1f} {status:>8}"
        )

    lines.extend([
        "",
        "SUMMARY",
        "-" * 40,
        f"Bottom (max):        {schedule.bottom_thickness:8.1f} mm",
        f"Side (max):          {schedule.side_thickness:8.1f} mm",
        f"Deck (max):          {schedule.deck_thickness:8.1f} mm",
        f"Average:             {schedule.average_thickness:8.1f} mm",
        f"",
        f"Estimated Plate Weight: {schedule.total_plate_weight/1000:.1f} tonnes",
        "",
    ])

    return "\n".join(lines)
