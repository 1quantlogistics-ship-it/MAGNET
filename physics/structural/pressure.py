"""
Design pressure calculations for hull structure.

Implements ABS HSNC 2023 pressure requirements:
- Hydrostatic pressure (still water)
- Slamming pressure (dynamic impact)
- Combined design pressure by zone

References:
- ABS HSNC 2023 Part 3, Chapter 3, Section 2 - Design Pressures
- ABS HSNC 2023 Table 3-3-2/5.1 - Slamming Pressure Factors
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class PressureZone(Enum):
    """Hull structural zones for pressure calculation."""
    # Bottom zones
    BOTTOM_FORWARD = "bottom_forward"       # 0 - 0.2L from FP
    BOTTOM_MIDSHIP = "bottom_midship"       # 0.2L - 0.7L from FP
    BOTTOM_AFT = "bottom_aft"               # 0.7L - 1.0L from FP

    # Side zones
    SIDE_FORWARD = "side_forward"           # Forward 0.2L
    SIDE_MIDSHIP = "side_midship"           # Midship 0.2L - 0.7L
    SIDE_AFT = "side_aft"                   # Aft 0.7L - 1.0L

    # Deck zones
    DECK_WEATHER = "deck_weather"           # Exposed weather deck
    DECK_INTERNAL = "deck_internal"         # Internal decks

    # Superstructure
    SUPERSTRUCTURE_FRONT = "superstructure_front"
    SUPERSTRUCTURE_SIDE = "superstructure_side"
    SUPERSTRUCTURE_AFT = "superstructure_aft"

    # Special zones
    TRANSOM = "transom"
    BOW_FLARE = "bow_flare"
    WETDECK = "wetdeck"                     # Catamaran cross-structure


@dataclass
class PressureResult:
    """Result of pressure calculation with audit trail."""
    zone: str
    hydrostatic_pressure: float    # kN/m² (kPa)
    slamming_pressure: float       # kN/m²
    design_pressure: float         # kN/m² (combined)

    # Factors used in calculation
    service_factor_n1: float       # N₁ - vessel type factor
    acceleration_factor_ncg: float  # n_cg - vertical acceleration
    deadrise_factor: float         # β - deadrise angle factor
    area_factor: float             # KL - longitudinal pressure reduction
    velocity_factor: float         # 1 + nv

    # Location
    position_x: float              # Longitudinal position (fraction of L from FP)
    position_z: float              # Vertical position (m above baseline)

    # Reference
    rule_reference: str
    calculation_notes: List[str] = field(default_factory=list)


# Service factors N₁ per ABS HSNC Table 3-3-2/3.1
SERVICE_FACTORS = {
    "naval_combatant": 1.0,
    "patrol_vessel": 0.9,
    "crew_boat": 0.85,
    "passenger_ferry": 0.85,
    "cargo_vessel": 0.80,
    "yacht": 0.75,
    "workboat": 0.85,
}

# Area reduction factors KL per ABS HSNC Table 3-3-2/5.1
# Based on panel length to frame spacing ratio
AREA_FACTORS = {
    1.0: 1.00,
    1.5: 0.95,
    2.0: 0.88,
    2.5: 0.82,
    3.0: 0.77,
    4.0: 0.70,
    5.0: 0.65,
}


def calculate_hydrostatic_pressure(
    draft: float,
    position_z: float = 0.0,
    seawater_density: float = 1.025,
) -> float:
    """
    Calculate hydrostatic pressure at a given depth.

    ABS HSNC 3-3-2/3.1: p_h = ρ × g × (T - z)

    Args:
        draft: Design draft (m)
        position_z: Height above baseline (m), 0 = baseline
        seawater_density: Seawater density (t/m³), default 1.025

    Returns:
        Hydrostatic pressure in kN/m² (kPa)
    """
    g = 9.81  # m/s²
    depth_below_wl = max(0, draft - position_z)
    pressure = seawater_density * g * depth_below_wl

    return pressure


def calculate_vertical_acceleration(
    length_wl: float,
    beam: float,
    draft: float,
    speed_kts: float,
    displacement: float,
    significant_wave_height: float = 2.5,
    lcg_ratio: float = 0.50,
) -> float:
    """
    Calculate vertical design acceleration at LCG.

    ABS HSNC 3-3-2/5.1 (simplified):
    n_cg = (V / √L) × Hs × K_accel

    More accurate formula per ABS HSNC:
    n_cg = (0.0078 × V² × Hs) / (Δ^0.3 × L^0.6 × B^0.1)

    Args:
        length_wl: Length at waterline (m)
        beam: Beam (m)
        draft: Draft (m)
        speed_kts: Design speed (knots)
        displacement: Displacement (tonnes)
        significant_wave_height: Hs (m), default 2.5m for unrestricted
        lcg_ratio: LCG position as fraction of L from FP

    Returns:
        Vertical acceleration at LCG in g's
    """
    if length_wl <= 0 or displacement <= 0:
        return 1.0  # Minimum 1g

    # Convert speed to m/s
    speed_ms = speed_kts * 0.5144

    # ABS HSNC acceleration formula
    # n_cg = K × V² × Hs / (Δ^0.3 × L^0.6 × B^0.1)
    K = 0.0078  # Empirical constant

    numerator = K * (speed_ms ** 2) * significant_wave_height
    denominator = (displacement ** 0.3) * (length_wl ** 0.6) * (beam ** 0.1)

    n_cg = numerator / denominator

    # Minimum acceleration = 1.0g
    n_cg = max(1.0, n_cg)

    # Maximum cap (practical limit)
    n_cg = min(n_cg, 10.0)

    return n_cg


def calculate_longitudinal_acceleration_factor(
    position_x: float,
    length_wl: float,
    lcg_ratio: float = 0.50,
) -> float:
    """
    Calculate longitudinal distribution factor for acceleration.

    Acceleration increases toward bow and stern from LCG.

    ABS HSNC 3-3-2/5.1:
    K_x = 1 + (|x - x_cg| / (0.45 × L))

    Args:
        position_x: Position from FP (m)
        length_wl: Length at waterline (m)
        lcg_ratio: LCG position as fraction of L from FP

    Returns:
        Longitudinal factor (≥ 1.0)
    """
    if length_wl <= 0:
        return 1.0

    x_ratio = position_x / length_wl
    x_cg_ratio = lcg_ratio

    distance_from_cg = abs(x_ratio - x_cg_ratio)
    factor = 1.0 + (distance_from_cg / 0.45)

    return factor


def calculate_deadrise_factor(deadrise_angle: float) -> float:
    """
    Calculate deadrise angle reduction factor for slamming.

    Higher deadrise reduces slamming pressure.

    ABS HSNC 3-3-2/5.1:
    For β ≥ 10°: K_β = (70 - β) / 70
    For β < 10°: K_β = 1.0

    Args:
        deadrise_angle: Local deadrise angle in degrees

    Returns:
        Deadrise factor (0.14 - 1.0)
    """
    if deadrise_angle < 10:
        return 1.0

    factor = (70 - deadrise_angle) / 70
    factor = max(0.14, min(1.0, factor))

    return factor


def calculate_slamming_pressure(
    displacement: float,
    length_wl: float,
    beam: float,
    draft: float,
    speed_kts: float,
    position_x: float,
    deadrise_angle: float = 15.0,
    service_type: str = "workboat",
    significant_wave_height: float = 2.5,
) -> tuple[float, Dict]:
    """
    Calculate slamming pressure per ABS HSNC 2023.

    ABS HSNC 3-3-2/5.1:
    p_sl = N₁ × n_cg × K_x × K_β × 0.5 × ρ × V²

    Simplified design formula:
    p_sl = 0.0035 × N₁ × Δ / Aw × (1 + n_cg)

    Args:
        displacement: Displacement (tonnes)
        length_wl: Length at waterline (m)
        beam: Beam (m)
        draft: Draft (m)
        speed_kts: Design speed (knots)
        position_x: Position from FP (m)
        deadrise_angle: Local deadrise angle (degrees)
        service_type: Vessel service type for N₁ factor
        significant_wave_height: Hs (m)

    Returns:
        Tuple of (slamming_pressure_kPa, factors_dict)
    """
    # Service factor
    n1 = SERVICE_FACTORS.get(service_type, 0.85)

    # Vertical acceleration at CG
    n_cg = calculate_vertical_acceleration(
        length_wl=length_wl,
        beam=beam,
        draft=draft,
        speed_kts=speed_kts,
        displacement=displacement,
        significant_wave_height=significant_wave_height,
    )

    # Longitudinal factor
    k_x = calculate_longitudinal_acceleration_factor(
        position_x=position_x,
        length_wl=length_wl,
    )

    # Deadrise factor
    k_beta = calculate_deadrise_factor(deadrise_angle)

    # Reference area (wetted surface approximation)
    # Simplified: Aw ≈ L × B × 0.7
    aw = length_wl * beam * 0.7

    # ABS simplified slamming formula
    # p_sl = 0.0035 × N₁ × Δ × (1 + n_cg) × K_x × K_β / Aw
    # Result in kN/m²

    p_sl = 0.0035 * n1 * displacement * 1000 * (1 + n_cg) * k_x * k_beta / aw

    # Apply minimum slamming pressure (ABS requirement)
    p_sl_min = 25.0  # kN/m² minimum for bottom forward
    if position_x / length_wl < 0.3:
        p_sl = max(p_sl, p_sl_min)

    factors = {
        "n1": n1,
        "n_cg": n_cg,
        "k_x": k_x,
        "k_beta": k_beta,
        "aw": aw,
    }

    return p_sl, factors


def get_zone_from_position(
    position_x: float,
    position_z: float,
    length_wl: float,
    draft: float,
    depth: float,
) -> PressureZone:
    """
    Determine structural zone from position.

    Args:
        position_x: Longitudinal position from FP (m)
        position_z: Vertical position above baseline (m)
        length_wl: Length at waterline (m)
        draft: Draft (m)
        depth: Depth to main deck (m)

    Returns:
        PressureZone enum
    """
    x_ratio = position_x / length_wl if length_wl > 0 else 0.5

    # Bottom (below waterline)
    if position_z < draft * 0.5:
        if x_ratio < 0.2:
            return PressureZone.BOTTOM_FORWARD
        elif x_ratio < 0.7:
            return PressureZone.BOTTOM_MIDSHIP
        else:
            return PressureZone.BOTTOM_AFT

    # Side shell (waterline region)
    elif position_z < draft * 1.2:
        if x_ratio < 0.2:
            return PressureZone.SIDE_FORWARD
        elif x_ratio < 0.7:
            return PressureZone.SIDE_MIDSHIP
        else:
            return PressureZone.SIDE_AFT

    # Deck
    elif position_z < depth:
        return PressureZone.DECK_INTERNAL

    # Above main deck
    else:
        return PressureZone.DECK_WEATHER


def calculate_design_pressure(
    zone: PressureZone,
    displacement: float,
    length_wl: float,
    beam: float,
    draft: float,
    depth: float,
    speed_kts: float,
    position_x: Optional[float] = None,
    position_z: Optional[float] = None,
    deadrise_angle: float = 15.0,
    service_type: str = "workboat",
    significant_wave_height: float = 2.5,
) -> PressureResult:
    """
    Calculate combined design pressure for a structural zone.

    Design pressure is the greater of:
    - Hydrostatic pressure (still water)
    - Slamming pressure (dynamic)

    Per ABS HSNC 3-3-2/5.1

    Args:
        zone: PressureZone enum
        displacement: Displacement (tonnes)
        length_wl: Length at waterline (m)
        beam: Beam (m)
        draft: Draft (m)
        depth: Depth to main deck (m)
        speed_kts: Design speed (knots)
        position_x: Longitudinal position from FP (m), or default per zone
        position_z: Vertical position above baseline (m), or default per zone
        deadrise_angle: Local deadrise angle (degrees)
        service_type: Vessel service type
        significant_wave_height: Hs (m)

    Returns:
        PressureResult with complete calculation details
    """
    # Default positions based on zone
    if position_x is None:
        position_x_defaults = {
            PressureZone.BOTTOM_FORWARD: 0.1 * length_wl,
            PressureZone.BOTTOM_MIDSHIP: 0.45 * length_wl,
            PressureZone.BOTTOM_AFT: 0.85 * length_wl,
            PressureZone.SIDE_FORWARD: 0.1 * length_wl,
            PressureZone.SIDE_MIDSHIP: 0.45 * length_wl,
            PressureZone.SIDE_AFT: 0.85 * length_wl,
            PressureZone.DECK_WEATHER: 0.5 * length_wl,
            PressureZone.DECK_INTERNAL: 0.5 * length_wl,
            PressureZone.TRANSOM: 1.0 * length_wl,
            PressureZone.BOW_FLARE: 0.05 * length_wl,
            PressureZone.WETDECK: 0.5 * length_wl,
        }
        position_x = position_x_defaults.get(zone, 0.5 * length_wl)

    if position_z is None:
        position_z_defaults = {
            PressureZone.BOTTOM_FORWARD: 0.0,
            PressureZone.BOTTOM_MIDSHIP: 0.0,
            PressureZone.BOTTOM_AFT: 0.0,
            PressureZone.SIDE_FORWARD: draft * 0.5,
            PressureZone.SIDE_MIDSHIP: draft * 0.5,
            PressureZone.SIDE_AFT: draft * 0.5,
            PressureZone.DECK_WEATHER: depth,
            PressureZone.DECK_INTERNAL: draft + 1.0,
            PressureZone.TRANSOM: draft * 0.5,
            PressureZone.BOW_FLARE: draft * 1.2,
            PressureZone.WETDECK: draft + 0.5,
        }
        position_z = position_z_defaults.get(zone, draft * 0.5)

    # Calculate hydrostatic pressure
    p_hydro = calculate_hydrostatic_pressure(
        draft=draft,
        position_z=position_z,
    )

    # Calculate slamming pressure
    p_slam, factors = calculate_slamming_pressure(
        displacement=displacement,
        length_wl=length_wl,
        beam=beam,
        draft=draft,
        speed_kts=speed_kts,
        position_x=position_x,
        deadrise_angle=deadrise_angle,
        service_type=service_type,
        significant_wave_height=significant_wave_height,
    )

    # Design pressure is the maximum
    # For bottom: primarily slamming in forward, hydrostatic aft
    # For sides: primarily hydrostatic
    # For deck: minimum design pressure applies

    if zone in [PressureZone.BOTTOM_FORWARD, PressureZone.BOW_FLARE]:
        p_design = max(p_hydro, p_slam)
    elif zone in [PressureZone.BOTTOM_MIDSHIP, PressureZone.BOTTOM_AFT]:
        p_design = max(p_hydro, p_slam * 0.7)  # Reduced slamming aft
    elif zone in [PressureZone.SIDE_FORWARD, PressureZone.SIDE_MIDSHIP, PressureZone.SIDE_AFT]:
        p_design = max(p_hydro, p_slam * 0.5)  # Side slamming reduced
    elif zone == PressureZone.WETDECK:
        p_design = max(25.0, p_slam * 0.8)  # Catamaran wetdeck minimum
    elif zone in [PressureZone.DECK_WEATHER, PressureZone.DECK_INTERNAL]:
        p_design = max(5.0, p_hydro * 0.3)  # Deck minimum
    else:
        p_design = max(p_hydro, p_slam)

    # Calculation notes
    notes = [
        f"Zone: {zone.value}",
        f"Position: x={position_x:.1f}m ({position_x/length_wl:.2f}L), z={position_z:.2f}m",
        f"Hydrostatic: {p_hydro:.1f} kN/m²",
        f"Slamming: {p_slam:.1f} kN/m²",
        f"Design: {p_design:.1f} kN/m² (governing)",
    ]

    return PressureResult(
        zone=zone.value,
        hydrostatic_pressure=p_hydro,
        slamming_pressure=p_slam,
        design_pressure=p_design,
        service_factor_n1=factors["n1"],
        acceleration_factor_ncg=factors["n_cg"],
        deadrise_factor=factors["k_beta"],
        area_factor=factors.get("k_l", 1.0),
        velocity_factor=1 + factors["n_cg"],
        position_x=position_x / length_wl,
        position_z=position_z,
        rule_reference="ABS HSNC 2023 3-3-2/5.1",
        calculation_notes=notes,
    )


def calculate_all_zone_pressures(
    displacement: float,
    length_wl: float,
    beam: float,
    draft: float,
    depth: float,
    speed_kts: float,
    deadrise_angle: float = 15.0,
    service_type: str = "workboat",
) -> Dict[PressureZone, PressureResult]:
    """
    Calculate design pressures for all hull zones.

    Args:
        displacement: Displacement (tonnes)
        length_wl: Length at waterline (m)
        beam: Beam (m)
        draft: Draft (m)
        depth: Depth (m)
        speed_kts: Design speed (knots)
        deadrise_angle: Midship deadrise angle (degrees)
        service_type: Vessel service type

    Returns:
        Dictionary of PressureZone -> PressureResult
    """
    zones = [
        PressureZone.BOTTOM_FORWARD,
        PressureZone.BOTTOM_MIDSHIP,
        PressureZone.BOTTOM_AFT,
        PressureZone.SIDE_FORWARD,
        PressureZone.SIDE_MIDSHIP,
        PressureZone.SIDE_AFT,
        PressureZone.DECK_WEATHER,
        PressureZone.TRANSOM,
    ]

    # Adjust deadrise by zone (typically higher forward)
    deadrise_by_zone = {
        PressureZone.BOTTOM_FORWARD: deadrise_angle * 1.5,  # Higher bow deadrise
        PressureZone.BOTTOM_MIDSHIP: deadrise_angle,
        PressureZone.BOTTOM_AFT: deadrise_angle * 0.7,  # Flatter aft
        PressureZone.SIDE_FORWARD: deadrise_angle,
        PressureZone.SIDE_MIDSHIP: deadrise_angle,
        PressureZone.SIDE_AFT: deadrise_angle,
        PressureZone.DECK_WEATHER: 0.0,
        PressureZone.TRANSOM: 0.0,
    }

    results = {}
    for zone in zones:
        beta = deadrise_by_zone.get(zone, deadrise_angle)
        results[zone] = calculate_design_pressure(
            zone=zone,
            displacement=displacement,
            length_wl=length_wl,
            beam=beam,
            draft=draft,
            depth=depth,
            speed_kts=speed_kts,
            deadrise_angle=beta,
            service_type=service_type,
        )

    return results


def generate_pressure_report(
    results: Dict[PressureZone, PressureResult],
    vessel_name: str = "Vessel",
) -> str:
    """Generate human-readable pressure calculation report."""
    lines = [
        f"DESIGN PRESSURE REPORT - {vessel_name}",
        "=" * 60,
        "",
        f"Reference: ABS HSNC 2023 Part 3, Chapter 3, Section 2",
        "",
        "ZONE PRESSURES",
        "-" * 60,
        f"{'Zone':<25} {'Hydro':>10} {'Slam':>10} {'Design':>10}",
        f"{'':<25} {'(kN/m²)':>10} {'(kN/m²)':>10} {'(kN/m²)':>10}",
        "-" * 60,
    ]

    for zone, result in results.items():
        lines.append(
            f"{result.zone:<25} {result.hydrostatic_pressure:>10.1f} "
            f"{result.slamming_pressure:>10.1f} {result.design_pressure:>10.1f}"
        )

    lines.extend([
        "",
        "DESIGN FACTORS",
        "-" * 40,
    ])

    # Get factors from first result
    first_result = list(results.values())[0]
    lines.extend([
        f"Service Factor N₁:      {first_result.service_factor_n1:.2f}",
        f"Acceleration n_cg:      {first_result.acceleration_factor_ncg:.2f} g",
        f"Velocity Factor:        {first_result.velocity_factor:.2f}",
        "",
    ])

    return "\n".join(lines)
