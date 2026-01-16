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
    """
    Chine configuration types.
    
    v1.1: Added REVERSE and VARIABLE for Phase 2 chine variations.
    """
    NONE = "none"           # No chine (pure round bilge)
    SOFT = "soft"           # Rounded/soft chine
    HARD = "hard"           # Single hard chine (alias for SINGLE)
    SINGLE = "single"       # Single hard chine
    DOUBLE = "double"       # Two hard chines per side
    TRIPLE = "triple"       # Three hard chines per side
    REVERSE = "reverse"     # Outward-angled chine (sponson-style)
    VARIABLE = "variable"   # Transitions soft→hard along length


class StemProfile(Enum):
    """Bow stem profile types."""
    VERTICAL = "vertical"
    RAKED = "raked"
    WAVE_PIERCING = "wave_piercing"
    BULBOUS = "bulbous"
    AXEBOW = "axebow"
    CLIPPER = "clipper"


class BowStyle(Enum):
    """
    Bow form style.
    
    Phase 3: Added for bow form variations.
    """
    TRADITIONAL = "traditional"      # Smooth lofted sections (default)
    WEDGE = "wedge"                  # Two planar panels meeting at stem
    AXE = "axe"                      # Vertical stem, sharp entry
    FACETED = "faceted"              # Multiple planar panels
    WAVE_PIERCING = "wave_piercing"  # Fine entry, tumblehome bow
    SPOON = "spoon"                  # Curved spoon bow (traditional)
    CLIPPER = "clipper"              # Raked curved stem


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
