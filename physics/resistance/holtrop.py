"""
MAGNET V1 Resistance Prediction - Holtrop-Mennen Method (ALPHA)

Implementation of the Holtrop-Mennen statistical method for
ship resistance prediction.

References:
- Holtrop, J. & Mennen, G.G.J. (1982). An Approximate Power Prediction Method
- Holtrop, J. (1984). A Statistical Re-Analysis of Resistance and Propulsion Data
- ITTC 1957 Friction Line

Valid for:
- Displacement ships
- Semi-displacement ships
- Fn < 0.45
- L/B = 3.9 - 15
- B/T = 2.1 - 4.0
- Cp = 0.55 - 0.85
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import math

# Physical constants
SEAWATER_DENSITY = 1025.0  # kg/m³
KINEMATIC_VISCOSITY = 1.19e-6  # m²/s at 15°C
GRAVITY = 9.81  # m/s²


@dataclass
class ResistanceResult:
    """Result of resistance calculations."""
    speed_kts: float
    speed_ms: float
    froude_number: float
    reynolds_number: float

    # Resistance components (Newtons)
    frictional_resistance: float
    residuary_resistance: float
    appendage_resistance: float
    wave_resistance: float
    total_resistance: float

    # Power (Watts)
    effective_power: float  # PE = RT × V
    delivered_power: float  # PD = PE / efficiency

    # Coefficients
    Cf: float  # Frictional resistance coefficient
    Cr: float  # Residuary resistance coefficient
    Ct: float  # Total resistance coefficient


def knots_to_ms(speed_kts: float) -> float:
    """Convert knots to m/s."""
    return speed_kts * 0.5144


def calculate_froude_number(speed_ms: float, length_wl: float) -> float:
    """
    Calculate Froude number.

    Fn = V / sqrt(g × L)

    Args:
        speed_ms: Speed in m/s
        length_wl: Length at waterline (m)

    Returns:
        Froude number (dimensionless)
    """
    return speed_ms / math.sqrt(GRAVITY * length_wl)


def calculate_reynolds_number(speed_ms: float, length_wl: float) -> float:
    """
    Calculate Reynolds number.

    Rn = V × L / ν

    Args:
        speed_ms: Speed in m/s
        length_wl: Length at waterline (m)

    Returns:
        Reynolds number (dimensionless)
    """
    return speed_ms * length_wl / KINEMATIC_VISCOSITY


def calculate_Cf_ITTC57(reynolds_number: float) -> float:
    """
    Calculate frictional resistance coefficient using ITTC 1957 line.

    Cf = 0.075 / (log10(Rn) - 2)²

    Args:
        reynolds_number: Reynolds number

    Returns:
        Frictional resistance coefficient
    """
    if reynolds_number <= 0:
        return 0.0

    log_rn = math.log10(reynolds_number)
    denominator = (log_rn - 2) ** 2
    if denominator <= 0:
        return 0.0
    return 0.075 / denominator


def calculate_frictional_resistance(
    speed_ms: float,
    length_wl: float,
    wetted_surface: float,
    form_factor: float = 1.0
) -> Tuple[float, float]:
    """
    Calculate frictional resistance using ITTC 1957 with form factor.

    RF = (1 + k) × 0.5 × ρ × V² × S × Cf

    Args:
        speed_ms: Speed in m/s
        length_wl: Length at waterline (m)
        wetted_surface: Wetted surface area (m²)
        form_factor: Form factor k (default 1.0 = no correction)

    Returns:
        Tuple of (frictional_resistance_N, Cf)
    """
    Rn = calculate_reynolds_number(speed_ms, length_wl)
    Cf = calculate_Cf_ITTC57(Rn)

    RF = (1 + form_factor) * 0.5 * SEAWATER_DENSITY * (speed_ms ** 2) * wetted_surface * Cf

    return RF, Cf


def calculate_form_factor_holtrop(
    length_wl: float,
    beam: float,
    draft: float,
    block_coefficient: float,
    prismatic_coefficient: float,
    lcb_fraction: float = 0.52
) -> float:
    """
    Calculate form factor (1+k1) using Holtrop method.

    (1+k1) = c13 × [0.93 + c12 × (B/LR)^0.92497 × (0.95 - Cp)^(-0.521448) ×
              (1 - Cp + 0.0225×lcb)^0.6906]

    Simplified version for initial estimates.

    Args:
        length_wl: Length at waterline (m)
        beam: Beam (m)
        draft: Draft (m)
        block_coefficient: Block coefficient (Cb)
        prismatic_coefficient: Prismatic coefficient (Cp)
        lcb_fraction: LCB position as fraction from midship (+ = forward)

    Returns:
        Form factor (1+k1)
    """
    # Length of run (approximate)
    LR = length_wl * (1 - prismatic_coefficient + 0.06 * prismatic_coefficient * abs(lcb_fraction) /
                       (4 * prismatic_coefficient - 1))

    # Simplified Holtrop form factor
    c12 = (draft / length_wl) ** 0.2228446

    # Coefficient c13 depends on Cstern (stern shape coefficient)
    # For normal sterns, c13 ≈ 1.0
    c13 = 1.0

    # Calculate form factor
    try:
        k1 = c13 * (0.93 + c12 * ((beam / LR) ** 0.92497) *
                    ((0.95 - prismatic_coefficient) ** -0.521448) *
                    ((1 - prismatic_coefficient + 0.0225 * (lcb_fraction - 0.5)) ** 0.6906))
    except (ValueError, ZeroDivisionError):
        # Fallback for edge cases
        k1 = 1.2

    return max(1.0, min(k1, 2.0))  # Clamp to reasonable range


def calculate_wave_resistance_holtrop(
    speed_ms: float,
    length_wl: float,
    beam: float,
    draft: float,
    displacement_m3: float,
    block_coefficient: float,
    prismatic_coefficient: float,
    waterplane_coefficient: float,
    transom_area: float = 0.0,
    bulb_area: float = 0.0
) -> float:
    """
    Calculate wave-making resistance using Holtrop method.

    Simplified version suitable for concept design.

    Args:
        speed_ms: Speed in m/s
        length_wl: Length at waterline (m)
        beam: Beam (m)
        draft: Draft (m)
        displacement_m3: Displacement volume (m³)
        block_coefficient: Block coefficient (Cb)
        prismatic_coefficient: Prismatic coefficient (Cp)
        waterplane_coefficient: Waterplane coefficient (Cwp)
        transom_area: Immersed transom area (m²)
        bulb_area: Bulb transverse area (m²)

    Returns:
        Wave resistance (N)
    """
    Fn = calculate_froude_number(speed_ms, length_wl)

    # For low Froude numbers, wave resistance is small
    if Fn < 0.1:
        return 0.0

    # Slenderness coefficient
    L_nabla = length_wl / (displacement_m3 ** (1/3))

    # Basic wave resistance coefficient (simplified Holtrop)
    # Full Holtrop uses many empirical coefficients; this is simplified

    # c1 coefficient (simplified)
    c1 = 2223105 * ((block_coefficient / (beam / length_wl)) ** 3.78613) * \
         ((draft / beam) ** 1.07961) * (90 - 0) ** (-1.37565)  # 0 = half entrance angle placeholder

    # c2 coefficient (accounts for bulb)
    if bulb_area > 0:
        c2 = math.exp(-1.89 * math.sqrt(bulb_area / (beam * draft * block_coefficient)))
    else:
        c2 = 1.0

    # c5 coefficient (transom immersion)
    if transom_area > 0:
        AT_ratio = transom_area / (beam * draft * prismatic_coefficient)
        c5 = 1 - 0.8 * AT_ratio
    else:
        c5 = 1.0

    # m1 coefficient
    m1 = 0.0140407 * (length_wl / draft) - 1.75254 * (displacement_m3 ** (1/3) / length_wl) - \
         4.79323 * (beam / length_wl) - c1

    # Wave resistance (simplified)
    # RW = c1 × c2 × c5 × ∇ × ρ × g × exp(m1 × Fn^d + m2 × cos(λ × Fn^-2))

    # Simplified wave resistance for concept design
    Cw = c1 * 1e-6 * (Fn ** 4) / (1 + Fn ** 2)  # Very simplified

    RW = Cw * 0.5 * SEAWATER_DENSITY * (speed_ms ** 2) * (beam * draft)

    return max(0, RW)


def calculate_residuary_resistance(
    speed_ms: float,
    length_wl: float,
    beam: float,
    draft: float,
    displacement_m3: float,
    block_coefficient: float,
    prismatic_coefficient: float,
    wetted_surface: float
) -> Tuple[float, float]:
    """
    Calculate residuary resistance (wave + eddy + spray).

    Uses simplified Holtrop correlation.

    Args:
        speed_ms: Speed in m/s
        length_wl: Length at waterline (m)
        beam: Beam (m)
        draft: Draft (m)
        displacement_m3: Displacement volume (m³)
        block_coefficient: Block coefficient (Cb)
        prismatic_coefficient: Prismatic coefficient (Cp)
        wetted_surface: Wetted surface area (m²)

    Returns:
        Tuple of (residuary_resistance_N, Cr)
    """
    Fn = calculate_froude_number(speed_ms, length_wl)

    # Slenderness ratio
    slenderness = length_wl / (displacement_m3 ** (1/3))

    # Simplified residuary resistance coefficient
    # Based on regression of Holtrop data

    if Fn < 0.1:
        Cr = 0.0
    elif Fn < 0.25:
        # Low speed regime
        Cr = 0.001 * (Fn ** 2) * (5.5 - slenderness) / block_coefficient
    elif Fn < 0.40:
        # Hump regime
        base_Cr = 0.002 * math.exp(-3 * (Fn - 0.35) ** 2)
        Cr = base_Cr * (block_coefficient / 0.6) * (6.5 / slenderness)
    else:
        # High speed regime
        Cr = 0.003 * Fn * (block_coefficient / 0.6)

    Cr = max(0, Cr)

    RR = Cr * 0.5 * SEAWATER_DENSITY * (speed_ms ** 2) * wetted_surface

    return RR, Cr


def calculate_appendage_resistance(
    speed_ms: float,
    wetted_surface: float,
    appendage_area: float = 0.0
) -> float:
    """
    Calculate appendage resistance (rudder, shafts, struts, etc.).

    Simplified estimate based on appendage wetted area.

    Args:
        speed_ms: Speed in m/s
        wetted_surface: Hull wetted surface (m²)
        appendage_area: Total appendage wetted area (m²)

    Returns:
        Appendage resistance (N)
    """
    if appendage_area <= 0:
        # Estimate appendage area as percentage of hull wetted surface
        # Typical values: 2-6% for single screw, 4-10% for twin screw
        appendage_area = 0.04 * wetted_surface

    # Appendage drag coefficient (typical value)
    Cd_app = 0.004

    R_app = Cd_app * 0.5 * SEAWATER_DENSITY * (speed_ms ** 2) * appendage_area

    return R_app


def calculate_total_resistance(
    speed_kts: float,
    length_wl: float,
    beam: float,
    draft: float,
    block_coefficient: float,
    prismatic_coefficient: float,
    waterplane_coefficient: float,
    wetted_surface: float,
    displacement_tonnes: Optional[float] = None
) -> ResistanceResult:
    """
    Calculate total ship resistance using Holtrop-Mennen method.

    Args:
        speed_kts: Speed in knots
        length_wl: Length at waterline (m)
        beam: Beam (m)
        draft: Draft (m)
        block_coefficient: Block coefficient (Cb)
        prismatic_coefficient: Prismatic coefficient (Cp)
        waterplane_coefficient: Waterplane coefficient (Cwp)
        wetted_surface: Wetted surface area (m²)
        displacement_tonnes: Displacement (tonnes), calculated if not provided

    Returns:
        ResistanceResult with all resistance components
    """
    speed_ms = knots_to_ms(speed_kts)

    # Calculate displacement if not provided
    if displacement_tonnes is None:
        displacement_m3 = length_wl * beam * draft * block_coefficient
        displacement_tonnes = displacement_m3 * SEAWATER_DENSITY / 1000
    else:
        displacement_m3 = displacement_tonnes * 1000 / SEAWATER_DENSITY

    # Froude and Reynolds numbers
    Fn = calculate_froude_number(speed_ms, length_wl)
    Rn = calculate_reynolds_number(speed_ms, length_wl)

    # Form factor
    k1 = calculate_form_factor_holtrop(
        length_wl, beam, draft, block_coefficient, prismatic_coefficient
    )

    # Frictional resistance
    RF, Cf = calculate_frictional_resistance(
        speed_ms, length_wl, wetted_surface, form_factor=(k1 - 1)
    )

    # Residuary resistance
    RR, Cr = calculate_residuary_resistance(
        speed_ms, length_wl, beam, draft, displacement_m3,
        block_coefficient, prismatic_coefficient, wetted_surface
    )

    # Wave resistance (already included in residuary for this simplified method)
    RW = 0.0  # Accounted for in RR

    # Appendage resistance
    R_app = calculate_appendage_resistance(speed_ms, wetted_surface)

    # Total resistance
    RT = RF + RR + R_app

    # Total resistance coefficient
    Ct = RT / (0.5 * SEAWATER_DENSITY * (speed_ms ** 2) * wetted_surface) if speed_ms > 0 else 0

    # Effective power
    PE = RT * speed_ms  # Watts

    # Delivered power (assuming propulsive efficiency)
    eta_D = 0.65  # Typical propulsive efficiency
    PD = PE / eta_D

    return ResistanceResult(
        speed_kts=speed_kts,
        speed_ms=speed_ms,
        froude_number=Fn,
        reynolds_number=Rn,
        frictional_resistance=RF,
        residuary_resistance=RR,
        appendage_resistance=R_app,
        wave_resistance=RW,
        total_resistance=RT,
        effective_power=PE,
        delivered_power=PD,
        Cf=Cf,
        Cr=Cr,
        Ct=Ct
    )


def calculate_effective_power(total_resistance: float, speed_ms: float) -> float:
    """
    Calculate effective power.

    PE = RT × V

    Args:
        total_resistance: Total resistance (N)
        speed_ms: Speed (m/s)

    Returns:
        Effective power in Watts
    """
    return total_resistance * speed_ms


def calculate_delivered_power(
    effective_power: float,
    propulsive_efficiency: float = 0.65
) -> float:
    """
    Calculate delivered power.

    PD = PE / ηD

    Args:
        effective_power: Effective power (W)
        propulsive_efficiency: Overall propulsive efficiency (default 0.65)

    Returns:
        Delivered power in Watts
    """
    return effective_power / propulsive_efficiency


def estimate_speed_power_curve(
    length_wl: float,
    beam: float,
    draft: float,
    block_coefficient: float,
    prismatic_coefficient: float,
    waterplane_coefficient: float,
    wetted_surface: float,
    min_speed_kts: float = 5.0,
    max_speed_kts: float = 30.0,
    speed_step_kts: float = 2.0
) -> List[ResistanceResult]:
    """
    Generate speed-power curve over a range of speeds.

    Args:
        length_wl: Length at waterline (m)
        beam: Beam (m)
        draft: Draft (m)
        block_coefficient: Block coefficient (Cb)
        prismatic_coefficient: Prismatic coefficient (Cp)
        waterplane_coefficient: Waterplane coefficient (Cwp)
        wetted_surface: Wetted surface area (m²)
        min_speed_kts: Minimum speed (knots)
        max_speed_kts: Maximum speed (knots)
        speed_step_kts: Speed increment (knots)

    Returns:
        List of ResistanceResult at each speed
    """
    results = []
    speed = min_speed_kts

    while speed <= max_speed_kts:
        result = calculate_total_resistance(
            speed_kts=speed,
            length_wl=length_wl,
            beam=beam,
            draft=draft,
            block_coefficient=block_coefficient,
            prismatic_coefficient=prismatic_coefficient,
            waterplane_coefficient=waterplane_coefficient,
            wetted_surface=wetted_surface
        )
        results.append(result)
        speed += speed_step_kts

    return results


def generate_resistance_report(result: ResistanceResult) -> str:
    """
    Generate a human-readable resistance report.

    Args:
        result: ResistanceResult from resistance calculation

    Returns:
        Formatted report string
    """
    lines = [
        "=" * 50,
        "RESISTANCE ANALYSIS REPORT",
        "=" * 50,
        "",
        "OPERATING CONDITION",
        "-" * 30,
        f"  Speed:               {result.speed_kts:>10.1f} kts ({result.speed_ms:.2f} m/s)",
        f"  Froude Number:       {result.froude_number:>10.4f}",
        f"  Reynolds Number:     {result.reynolds_number:>10.2e}",
        "",
        "RESISTANCE BREAKDOWN",
        "-" * 30,
        f"  Frictional (RF):     {result.frictional_resistance/1000:>10.1f} kN",
        f"  Residuary (RR):      {result.residuary_resistance/1000:>10.1f} kN",
        f"  Appendage:           {result.appendage_resistance/1000:>10.1f} kN",
        f"  TOTAL (RT):          {result.total_resistance/1000:>10.1f} kN",
        "",
        "RESISTANCE COEFFICIENTS",
        "-" * 30,
        f"  Cf (frictional):     {result.Cf:>10.6f}",
        f"  Cr (residuary):      {result.Cr:>10.6f}",
        f"  Ct (total):          {result.Ct:>10.6f}",
        "",
        "POWER REQUIREMENTS",
        "-" * 30,
        f"  Effective Power (PE):{result.effective_power/1000:>10.1f} kW",
        f"  Delivered Power (PD):{result.delivered_power/1000:>10.1f} kW",
        f"  (assuming ηD = 0.65)",
        "=" * 50,
    ]

    return "\n".join(lines)
