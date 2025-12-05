"""
Zone definitions for structural layout.

Maps 3D positions to structural zones for pressure calculations,
scantling requirements, and structural member specifications.

Zone Types:
- Longitudinal: forward, midship, aft (based on x position)
- Vertical: bottom, side, deck (based on z position relative to waterline)
- Combined: PressureZone for structural calculations

References:
- ABS HSNC 2023 Part 3, Section 2 - Zone Definitions
- Integrates with physics.structural.pressure.PressureZone
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum

# Import PressureZone from structural module for compatibility
try:
    from physics.structural.pressure import PressureZone
except ImportError:
    # Define locally if structural module not available
    class PressureZone(Enum):
        BOTTOM_FORWARD = "bottom_forward"
        BOTTOM_MIDSHIP = "bottom_midship"
        BOTTOM_AFT = "bottom_aft"
        SIDE_FORWARD = "side_forward"
        SIDE_MIDSHIP = "side_midship"
        SIDE_AFT = "side_aft"
        DECK_WEATHER = "deck_weather"
        DECK_INTERNAL = "deck_internal"
        SUPERSTRUCTURE_FRONT = "superstructure_front"
        SUPERSTRUCTURE_SIDE = "superstructure_side"
        SUPERSTRUCTURE_AFT = "superstructure_aft"
        TRANSOM = "transom"
        BOW_FLARE = "bow_flare"
        WETDECK = "wetdeck"


class ZoneType(Enum):
    """Broad structural zone categories."""
    BOTTOM = "bottom"
    SIDE = "side"
    DECK = "deck"
    SUPERSTRUCTURE = "superstructure"
    TRANSOM = "transom"
    BOW = "bow"


class LongitudinalZone(Enum):
    """Longitudinal zone divisions."""
    AFT = "aft"           # 0.0 - 0.3 LBP from AP
    MIDSHIP = "midship"   # 0.3 - 0.7 LBP from AP
    FORWARD = "forward"   # 0.7 - 1.0 LBP from AP


class VerticalZone(Enum):
    """Vertical zone divisions."""
    BOTTOM = "bottom"         # Below 0.5T from baseline
    BILGE = "bilge"           # 0.5T - T (transition)
    SIDE = "side"             # T - D (between WL and deck)
    DECK = "deck"             # At main deck level
    SUPERSTRUCTURE = "superstructure"  # Above main deck


@dataclass
class StructuralZone:
    """
    Structural zone with boundaries and properties.

    Attributes:
        name: Zone name
        pressure_zone: Corresponding PressureZone enum
        zone_type: Broad zone category
        longitudinal: Longitudinal zone (aft/midship/forward)
        x_start: Start x position (fraction of LBP from AP)
        x_end: End x position (fraction of LBP from AP)
        z_start: Start z position (fraction of depth from BL)
        z_end: End z position (fraction of depth from BL)
        y_start: Start y position (fraction of beam from CL, port positive)
        y_end: End y position (fraction of beam from CL)
        is_immersed: Whether zone is below waterline
        is_slamming_zone: Whether zone subject to slamming loads
    """
    name: str
    pressure_zone: PressureZone
    zone_type: ZoneType
    longitudinal: LongitudinalZone
    x_start: float = 0.0    # Normalized (0-1)
    x_end: float = 1.0      # Normalized (0-1)
    z_start: float = 0.0    # Normalized to depth
    z_end: float = 1.0      # Normalized to depth
    y_start: float = 0.0    # Normalized to beam/2
    y_end: float = 1.0      # Normalized to beam/2
    is_immersed: bool = False
    is_slamming_zone: bool = False


# Zone boundary definitions (normalized coordinates)
# x: 0 = AP, 1 = FP
# z: 0 = baseline, 1 = main deck
ZONE_DEFINITIONS: Dict[PressureZone, Dict] = {
    # Bottom zones - immersed, subject to slamming
    PressureZone.BOTTOM_FORWARD: {
        "zone_type": ZoneType.BOTTOM,
        "longitudinal": LongitudinalZone.FORWARD,
        "x_start": 0.70, "x_end": 1.00,
        "z_start": 0.00, "z_end": 0.30,
        "is_immersed": True,
        "is_slamming_zone": True,
    },
    PressureZone.BOTTOM_MIDSHIP: {
        "zone_type": ZoneType.BOTTOM,
        "longitudinal": LongitudinalZone.MIDSHIP,
        "x_start": 0.30, "x_end": 0.70,
        "z_start": 0.00, "z_end": 0.30,
        "is_immersed": True,
        "is_slamming_zone": True,
    },
    PressureZone.BOTTOM_AFT: {
        "zone_type": ZoneType.BOTTOM,
        "longitudinal": LongitudinalZone.AFT,
        "x_start": 0.00, "x_end": 0.30,
        "z_start": 0.00, "z_end": 0.30,
        "is_immersed": True,
        "is_slamming_zone": False,
    },

    # Side zones - partially immersed
    PressureZone.SIDE_FORWARD: {
        "zone_type": ZoneType.SIDE,
        "longitudinal": LongitudinalZone.FORWARD,
        "x_start": 0.70, "x_end": 1.00,
        "z_start": 0.30, "z_end": 0.85,
        "is_immersed": True,
        "is_slamming_zone": False,
    },
    PressureZone.SIDE_MIDSHIP: {
        "zone_type": ZoneType.SIDE,
        "longitudinal": LongitudinalZone.MIDSHIP,
        "x_start": 0.30, "x_end": 0.70,
        "z_start": 0.30, "z_end": 0.85,
        "is_immersed": True,
        "is_slamming_zone": False,
    },
    PressureZone.SIDE_AFT: {
        "zone_type": ZoneType.SIDE,
        "longitudinal": LongitudinalZone.AFT,
        "x_start": 0.00, "x_end": 0.30,
        "z_start": 0.30, "z_end": 0.85,
        "is_immersed": True,
        "is_slamming_zone": False,
    },

    # Deck zones - above waterline
    PressureZone.DECK_WEATHER: {
        "zone_type": ZoneType.DECK,
        "longitudinal": LongitudinalZone.MIDSHIP,
        "x_start": 0.00, "x_end": 1.00,
        "z_start": 0.85, "z_end": 1.00,
        "is_immersed": False,
        "is_slamming_zone": False,
    },
    PressureZone.DECK_INTERNAL: {
        "zone_type": ZoneType.DECK,
        "longitudinal": LongitudinalZone.MIDSHIP,
        "x_start": 0.00, "x_end": 1.00,
        "z_start": 0.50, "z_end": 0.85,
        "is_immersed": False,
        "is_slamming_zone": False,
    },

    # Special zones
    PressureZone.TRANSOM: {
        "zone_type": ZoneType.TRANSOM,
        "longitudinal": LongitudinalZone.AFT,
        "x_start": 0.00, "x_end": 0.05,
        "z_start": 0.00, "z_end": 0.85,
        "is_immersed": True,
        "is_slamming_zone": False,
    },
    PressureZone.BOW_FLARE: {
        "zone_type": ZoneType.BOW,
        "longitudinal": LongitudinalZone.FORWARD,
        "x_start": 0.90, "x_end": 1.00,
        "z_start": 0.50, "z_end": 1.00,
        "is_immersed": False,
        "is_slamming_zone": True,
    },
    PressureZone.WETDECK: {
        "zone_type": ZoneType.BOTTOM,
        "longitudinal": LongitudinalZone.MIDSHIP,
        "x_start": 0.20, "x_end": 0.80,
        "z_start": 0.40, "z_end": 0.60,
        "is_immersed": False,
        "is_slamming_zone": True,
    },

    # Superstructure zones
    PressureZone.SUPERSTRUCTURE_FRONT: {
        "zone_type": ZoneType.SUPERSTRUCTURE,
        "longitudinal": LongitudinalZone.FORWARD,
        "x_start": 0.60, "x_end": 0.70,
        "z_start": 1.00, "z_end": 1.50,
        "is_immersed": False,
        "is_slamming_zone": False,
    },
    PressureZone.SUPERSTRUCTURE_SIDE: {
        "zone_type": ZoneType.SUPERSTRUCTURE,
        "longitudinal": LongitudinalZone.MIDSHIP,
        "x_start": 0.30, "x_end": 0.70,
        "z_start": 1.00, "z_end": 1.50,
        "is_immersed": False,
        "is_slamming_zone": False,
    },
    PressureZone.SUPERSTRUCTURE_AFT: {
        "zone_type": ZoneType.SUPERSTRUCTURE,
        "longitudinal": LongitudinalZone.AFT,
        "x_start": 0.20, "x_end": 0.30,
        "z_start": 1.00, "z_end": 1.50,
        "is_immersed": False,
        "is_slamming_zone": False,
    },
}


def get_zone_for_position(
    x: float,
    z: float,
    length_bp: float,
    depth: float,
    draft: float,
    y: float = 0.0,
    beam: float = 1.0,
) -> PressureZone:
    """
    Get the structural zone for a given 3D position.

    Args:
        x: X position (m from AP)
        z: Z position (m above baseline)
        length_bp: Length between perpendiculars (m)
        depth: Depth to main deck (m)
        draft: Design draft (m)
        y: Y position (m from centerline, port positive)
        beam: Beam (m)

    Returns:
        PressureZone for the position
    """
    # Normalize coordinates
    x_norm = x / length_bp if length_bp > 0 else 0.5
    z_norm = z / depth if depth > 0 else 0.5
    y_norm = abs(y) / (beam / 2) if beam > 0 else 0.0

    # Clamp to valid ranges
    x_norm = max(0.0, min(1.0, x_norm))
    z_norm = max(0.0, min(1.5, z_norm))  # Allow above deck
    y_norm = max(0.0, min(1.0, y_norm))

    # Determine longitudinal zone
    if x_norm < 0.30:
        long_zone = LongitudinalZone.AFT
    elif x_norm < 0.70:
        long_zone = LongitudinalZone.MIDSHIP
    else:
        long_zone = LongitudinalZone.FORWARD

    # Determine vertical zone type
    draft_norm = draft / depth if depth > 0 else 0.5

    if z_norm < 0.30:
        # Bottom
        if long_zone == LongitudinalZone.FORWARD:
            return PressureZone.BOTTOM_FORWARD
        elif long_zone == LongitudinalZone.MIDSHIP:
            return PressureZone.BOTTOM_MIDSHIP
        else:
            return PressureZone.BOTTOM_AFT

    elif z_norm < 0.85:
        # Side shell
        if long_zone == LongitudinalZone.FORWARD:
            return PressureZone.SIDE_FORWARD
        elif long_zone == LongitudinalZone.MIDSHIP:
            return PressureZone.SIDE_MIDSHIP
        else:
            return PressureZone.SIDE_AFT

    elif z_norm < 1.0:
        # Weather deck
        return PressureZone.DECK_WEATHER

    else:
        # Superstructure
        if long_zone == LongitudinalZone.FORWARD:
            return PressureZone.SUPERSTRUCTURE_FRONT
        elif long_zone == LongitudinalZone.AFT:
            return PressureZone.SUPERSTRUCTURE_AFT
        else:
            return PressureZone.SUPERSTRUCTURE_SIDE


def get_zone_boundaries(
    pressure_zone: PressureZone,
    length_bp: float,
    beam: float,
    depth: float,
) -> Dict[str, Tuple[float, float]]:
    """
    Get physical boundaries of a zone in vessel coordinates.

    Args:
        pressure_zone: Zone to get boundaries for
        length_bp: Length between perpendiculars (m)
        beam: Beam (m)
        depth: Depth to main deck (m)

    Returns:
        Dict with 'x', 'y', 'z' keys containing (min, max) tuples in meters
    """
    if pressure_zone not in ZONE_DEFINITIONS:
        # Default to full vessel
        return {
            "x": (0.0, length_bp),
            "y": (-beam / 2, beam / 2),
            "z": (0.0, depth),
        }

    zone_def = ZONE_DEFINITIONS[pressure_zone]

    return {
        "x": (zone_def["x_start"] * length_bp, zone_def["x_end"] * length_bp),
        "y": (-beam / 2, beam / 2),  # Full beam for shell zones
        "z": (zone_def["z_start"] * depth, zone_def["z_end"] * depth),
    }


def get_all_zones() -> List[StructuralZone]:
    """
    Get all defined structural zones.

    Returns:
        List of StructuralZone objects
    """
    zones = []

    for pressure_zone, zone_def in ZONE_DEFINITIONS.items():
        zones.append(StructuralZone(
            name=pressure_zone.value,
            pressure_zone=pressure_zone,
            zone_type=zone_def["zone_type"],
            longitudinal=zone_def["longitudinal"],
            x_start=zone_def["x_start"],
            x_end=zone_def["x_end"],
            z_start=zone_def["z_start"],
            z_end=zone_def["z_end"],
            is_immersed=zone_def["is_immersed"],
            is_slamming_zone=zone_def["is_slamming_zone"],
        ))

    return zones


def get_zones_by_type(zone_type: ZoneType) -> List[PressureZone]:
    """
    Get all pressure zones of a given type.

    Args:
        zone_type: Zone type to filter by

    Returns:
        List of PressureZone enums matching the type
    """
    matching = []
    for pressure_zone, zone_def in ZONE_DEFINITIONS.items():
        if zone_def["zone_type"] == zone_type:
            matching.append(pressure_zone)
    return matching


def get_slamming_zones() -> List[PressureZone]:
    """
    Get all zones subject to slamming loads.

    Returns:
        List of PressureZone enums in slamming areas
    """
    return [pz for pz, zd in ZONE_DEFINITIONS.items() if zd["is_slamming_zone"]]


def get_immersed_zones() -> List[PressureZone]:
    """
    Get all zones that are normally immersed.

    Returns:
        List of PressureZone enums below waterline
    """
    return [pz for pz, zd in ZONE_DEFINITIONS.items() if zd["is_immersed"]]


def get_longitudinal_zone(x: float, length_bp: float) -> LongitudinalZone:
    """
    Get longitudinal zone for an x position.

    Args:
        x: X position (m from AP)
        length_bp: Length between perpendiculars (m)

    Returns:
        LongitudinalZone enum
    """
    x_norm = x / length_bp if length_bp > 0 else 0.5

    if x_norm < 0.30:
        return LongitudinalZone.AFT
    elif x_norm < 0.70:
        return LongitudinalZone.MIDSHIP
    else:
        return LongitudinalZone.FORWARD


def get_vertical_zone(z: float, draft: float, depth: float) -> VerticalZone:
    """
    Get vertical zone for a z position.

    Args:
        z: Z position (m above baseline)
        draft: Design draft (m)
        depth: Depth to main deck (m)

    Returns:
        VerticalZone enum
    """
    if z < 0.5 * draft:
        return VerticalZone.BOTTOM
    elif z < draft:
        return VerticalZone.BILGE
    elif z < depth:
        return VerticalZone.SIDE
    elif z < depth * 1.05:  # Small tolerance
        return VerticalZone.DECK
    else:
        return VerticalZone.SUPERSTRUCTURE
