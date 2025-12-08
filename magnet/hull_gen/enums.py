"""
hull_gen/enums.py - Hull generation enumerations.

BRAVO OWNS THIS FILE.

Module 16 v1.0 - Parametric Hull Definition enumerations.
"""

from enum import Enum


class HullType(Enum):
    """Primary hull type classification."""
    DEEP_V_PLANING = "deep_v_planing"
    SEMI_DISPLACEMENT = "semi_displacement"
    ROUND_BILGE = "round_bilge"
    HARD_CHINE = "hard_chine"
    CATAMARAN = "catamaran"
    TRIMARAN = "trimaran"
    SWATH = "swath"


class ChineType(Enum):
    """Chine configuration."""
    NONE = "none"
    SINGLE = "single"
    DOUBLE = "double"
    TRIPLE = "triple"
    SOFT = "soft"
    HARD = "hard"


class StemProfile(Enum):
    """Bow stem profile types."""
    VERTICAL = "vertical"
    RAKED = "raked"
    WAVE_PIERCING = "wave_piercing"
    BULBOUS = "bulbous"
    AXEBOW = "axebow"


class SternProfile(Enum):
    """Stern profile types."""
    TRANSOM = "transom"
    CRUISER = "cruiser"
    CANOE = "canoe"
    TUNNEL = "tunnel"


class TransomType(Enum):
    """Transom configuration."""
    DRY = "dry"
    IMMERSED = "immersed"
    SEMI_IMMERSED = "semi_immersed"


class KeelType(Enum):
    """Keel configuration."""
    FLAT = "flat"
    BAR = "bar"
    SKEG = "skeg"
    TWIN_SKEG = "twin_skeg"


class SectionShape(Enum):
    """Transverse section shape types."""
    V_SHAPE = "v_shape"
    U_SHAPE = "u_shape"
    ROUND = "round"
    FLAT_BOTTOM = "flat_bottom"
    WARPED = "warped"


class FairingQuality(Enum):
    """Fairing quality levels."""
    ROUGH = "rough"
    STANDARD = "standard"
    FINE = "fine"
    PRODUCTION = "production"


class HullRegion(Enum):
    """Hull longitudinal regions."""
    BOW = "bow"
    ENTRANCE = "entrance"
    PARALLEL = "parallel"
    RUN = "run"
    STERN = "stern"


class SurfaceType(Enum):
    """Hull surface types."""
    SHELL = "shell"
    DECK = "deck"
    BULKHEAD = "bulkhead"
    INNER_BOTTOM = "inner_bottom"
    SUPERSTRUCTURE = "superstructure"
