"""
MAGNET V1 Displacement Calculations (ALPHA)

Hydrostatic calculations for displacement, volume, and wetted surface.

References:
- Principles of Naval Architecture (SNAME)
- Holtrop, J. (1984). A Statistical Re-Analysis of Resistance and Propulsion Data
"""

from typing import Tuple
import math

# Import schema with fallback for standalone testing
try:
    from schemas.hull_params import HullParamsSchema
except ImportError:
    HullParamsSchema = None  # type: ignore

# Physical constants
SEAWATER_DENSITY = 1.025  # tonnes/m³ (standard seawater at 15°C)
FRESHWATER_DENSITY = 1.000  # tonnes/m³


def calculate_volume(
    length_wl: float,
    beam: float,
    draft: float,
    block_coefficient: float
) -> float:
    """
    Calculate submerged volume from principal dimensions.

    Args:
        length_wl: Length at waterline (m)
        beam: Beam at waterline (m)
        draft: Design draft (m)
        block_coefficient: Block coefficient (Cb)

    Returns:
        Submerged volume in cubic meters
    """
    return length_wl * beam * draft * block_coefficient


def calculate_displacement(
    length_wl: float,
    beam: float,
    draft: float,
    block_coefficient: float,
    density: float = SEAWATER_DENSITY
) -> float:
    """
    Calculate displacement from principal dimensions.

    Displacement = ρ × ∇ = ρ × L × B × T × Cb

    Args:
        length_wl: Length at waterline (m)
        beam: Beam at waterline (m)
        draft: Design draft (m)
        block_coefficient: Block coefficient (Cb)
        density: Water density (tonnes/m³), default seawater

    Returns:
        Displacement in tonnes
    """
    volume = calculate_volume(length_wl, beam, draft, block_coefficient)
    return volume * density


def calculate_displacement_from_hull(
    hull: "HullParamsSchema",
    density: float = SEAWATER_DENSITY
) -> float:
    """
    Calculate displacement from HullParamsSchema.

    Args:
        hull: HullParamsSchema instance
        density: Water density (tonnes/m³)

    Returns:
        Displacement in tonnes
    """
    return calculate_displacement(
        hull.length_waterline,
        hull.beam,
        hull.draft,
        hull.block_coefficient,
        density
    )


def calculate_wetted_surface_holtrop(
    length_wl: float,
    beam: float,
    draft: float,
    block_coefficient: float,
    midship_coefficient: float,
    waterplane_coefficient: float,
    transom_area: float = 0.0,
    bulb_transverse_area: float = 0.0
) -> float:
    """
    Calculate wetted surface area using Holtrop method.

    Based on: Holtrop, J. (1984)

    Args:
        length_wl: Length at waterline (m)
        beam: Beam at waterline (m)
        draft: Design draft (m)
        block_coefficient: Block coefficient (Cb)
        midship_coefficient: Midship coefficient (Cm)
        waterplane_coefficient: Waterplane coefficient (Cwp)
        transom_area: Transom immersed area (m²)
        bulb_transverse_area: Bulb transverse area (m²)

    Returns:
        Wetted surface area in m²
    """
    L = length_wl
    B = beam
    T = draft
    Cb = block_coefficient
    Cm = midship_coefficient
    Cwp = waterplane_coefficient
    AT = transom_area
    ABT = bulb_transverse_area

    # Holtrop formula for wetted surface
    S = L * (2*T + B) * math.sqrt(Cm) * (
        0.453 + 0.4425*Cb - 0.2862*Cm - 0.003467*(B/T) + 0.3696*Cwp
    ) + 2.38 * ABT / Cb

    # Add transom wetted area (approximation)
    if AT > 0:
        S += 0.5 * AT

    return S


def calculate_wetted_surface_simple(
    length_wl: float,
    beam: float,
    draft: float,
    block_coefficient: float,
    midship_coefficient: float
) -> float:
    """
    Simplified wetted surface calculation.

    Suitable for early-stage estimates.

    Args:
        length_wl: Length at waterline (m)
        beam: Beam at waterline (m)
        draft: Design draft (m)
        block_coefficient: Block coefficient (Cb)
        midship_coefficient: Midship coefficient (Cm)

    Returns:
        Wetted surface area in m²
    """
    L = length_wl
    B = beam
    T = draft
    Cb = block_coefficient
    Cm = midship_coefficient

    # Simplified Holtrop formula (no bulb, no transom)
    S = L * (2*T + B) * (0.453 + 0.4425*Cb - 0.2862*Cm)
    return S


def calculate_wetted_surface_from_hull(
    hull: "HullParamsSchema",
    method: str = "holtrop"
) -> float:
    """
    Calculate wetted surface from HullParamsSchema.

    Args:
        hull: HullParamsSchema instance
        method: "holtrop" (full) or "simple"

    Returns:
        Wetted surface area in m²
    """
    if method == "simple":
        return calculate_wetted_surface_simple(
            hull.length_waterline,
            hull.beam,
            hull.draft,
            hull.block_coefficient,
            hull.midship_coefficient
        )
    else:
        return calculate_wetted_surface_holtrop(
            hull.length_waterline,
            hull.beam,
            hull.draft,
            hull.block_coefficient,
            hull.midship_coefficient,
            hull.waterplane_coefficient
        )


def calculate_waterplane_area(
    length_wl: float,
    beam: float,
    waterplane_coefficient: float
) -> float:
    """
    Calculate waterplane area.

    Awp = Cwp × L × B

    Args:
        length_wl: Length at waterline (m)
        beam: Beam at waterline (m)
        waterplane_coefficient: Waterplane coefficient (Cwp)

    Returns:
        Waterplane area in m²
    """
    return length_wl * beam * waterplane_coefficient


def calculate_midship_area(
    beam: float,
    draft: float,
    midship_coefficient: float
) -> float:
    """
    Calculate midship section area.

    Am = Cm × B × T

    Args:
        beam: Beam at waterline (m)
        draft: Design draft (m)
        midship_coefficient: Midship coefficient (Cm)

    Returns:
        Midship section area in m²
    """
    return beam * draft * midship_coefficient


def calculate_tons_per_cm_immersion(
    length_wl: float,
    beam: float,
    waterplane_coefficient: float,
    density: float = SEAWATER_DENSITY
) -> float:
    """
    Calculate tonnes per centimeter immersion (TPC).

    TPC indicates weight required to increase draft by 1 cm.

    Args:
        length_wl: Length at waterline (m)
        beam: Beam at waterline (m)
        waterplane_coefficient: Waterplane coefficient (Cwp)
        density: Water density (tonnes/m³)

    Returns:
        TPC in tonnes/cm
    """
    awp = calculate_waterplane_area(length_wl, beam, waterplane_coefficient)
    return (awp * density) / 100  # Convert m to cm


def calculate_moment_to_change_trim(
    length_wl: float,
    beam: float,
    draft: float,
    block_coefficient: float,
    waterplane_coefficient: float,
    density: float = SEAWATER_DENSITY
) -> float:
    """
    Calculate moment to change trim by 1 cm (MCT).

    Approximate formula for initial estimates.

    Args:
        length_wl: Length at waterline (m)
        beam: Beam at waterline (m)
        draft: Design draft (m)
        block_coefficient: Block coefficient (Cb)
        waterplane_coefficient: Waterplane coefficient (Cwp)
        density: Water density (tonnes/m³)

    Returns:
        MCT in tonne-meters per cm
    """
    displacement = calculate_displacement(
        length_wl, beam, draft, block_coefficient, density
    )

    # Approximate BML (longitudinal metacentric radius)
    # BML ≈ L² × Cwp / (12 × T)
    bml = (length_wl ** 2) * waterplane_coefficient / (12 * draft)

    # MCT = Δ × BML / (100 × L)
    mct = displacement * bml / (100 * length_wl)

    return mct
