"""
structural/enums.py - Structural detailing enumerations.

ALPHA OWNS THIS FILE.

Modules 21-24: All structural enumerations.
"""

from enum import Enum


class StructuralZone(Enum):
    """Structural zone classification for scantling requirements."""
    BOTTOM = "bottom"
    SIDE = "side"
    DECK = "deck"
    TRANSOM = "transom"
    BULKHEAD = "bulkhead"
    SUPERSTRUCTURE = "superstructure"
    INTERNAL = "internal"


class PlateType(Enum):
    """Types of structural plates."""
    SHELL = "shell"
    DECK = "deck"
    BULKHEAD = "bulkhead"
    TANK_TOP = "tank_top"
    INNER_BOTTOM = "inner_bottom"
    FLAT_BAR = "flat_bar"


class FrameType(Enum):
    """Types of transverse frames."""
    ORDINARY = "ordinary"
    WEB_FRAME = "web_frame"
    BULKHEAD = "bulkhead"
    COLLISION = "collision"
    ENGINE_ROOM = "engine_room"


class StiffenerType(Enum):
    """Types of stiffeners."""
    LONGITUDINAL = "longitudinal"
    TRANSVERSE_FRAME = "transverse_frame"
    WEB_FRAME = "web_frame"
    DECK_BEAM = "deck_beam"
    GIRDER = "girder"
    CARLING = "carling"


class ProfileType(Enum):
    """Standard structural profile types."""
    FLAT_BAR = "flat_bar"
    ANGLE = "angle"
    TEE = "tee"
    BULB_FLAT = "bulb_flat"
    CHANNEL = "channel"
    I_BEAM = "i_beam"


class WeldType(Enum):
    """Weld types."""
    FILLET = "fillet"
    BUTT = "butt"
    PLUG = "plug"
    SLOT = "slot"
    SEAM = "seam"


class WeldClass(Enum):
    """Weld quality classification (DNV-GL)."""
    CLASS_1 = "class_1"  # Full penetration, highest quality
    CLASS_2 = "class_2"  # Standard structural
    CLASS_3 = "class_3"  # Secondary structural
    CLASS_4 = "class_4"  # Non-structural


class WeldPosition(Enum):
    """Weld position codes (AWS)."""
    FLAT_1F = "1F"
    HORIZONTAL_2F = "2F"
    VERTICAL_3F = "3F"
    OVERHEAD_4F = "4F"
    FLAT_1G = "1G"
    HORIZONTAL_2G = "2G"
    VERTICAL_3G = "3G"
    OVERHEAD_4G = "4G"


class MaterialGrade(Enum):
    """Aluminum alloy grades for marine use."""
    AL_5083_H116 = "5083-H116"  # Standard hull plate
    AL_5083_H321 = "5083-H321"  # Alternative temper
    AL_5086_H116 = "5086-H116"  # Weldable plate
    AL_6061_T6 = "6061-T6"      # Extrusions
    AL_6082_T6 = "6082-T6"      # European extrusions
