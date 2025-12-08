"""
production/enums.py - Production planning enumerations.

BRAVO OWNS THIS FILE.

Module 11 v1.1 - Production Planning enumerations.
"""

from enum import Enum


class MaterialCategory(Enum):
    """Material category types for takeoff."""
    PLATE = "plate"
    PROFILE = "profile"
    PIPE = "pipe"
    FITTING = "fitting"
    FASTENER = "fastener"
    WELDING = "welding"
    COATING = "coating"
    EQUIPMENT = "equipment"


class AssemblyLevel(Enum):
    """Assembly hierarchy levels."""
    COMPONENT = "component"
    SUBASSEMBLY = "subassembly"
    UNIT = "unit"
    ZONE = "zone"
    HULL = "hull"


class WorkPackageType(Enum):
    """Work package types for scheduling."""
    FABRICATION = "fabrication"
    WELDING = "welding"
    OUTFITTING = "outfitting"
    PAINTING = "painting"
    TESTING = "testing"
    INSTALLATION = "installation"


class ProductionPhase(Enum):
    """Production phases for scheduling."""
    DESIGN = "design"
    MATERIAL_PROCUREMENT = "material_procurement"
    FABRICATION = "fabrication"
    SUBASSEMBLY = "subassembly"
    ASSEMBLY = "assembly"
    OUTFITTING = "outfitting"
    PAINTING = "painting"
    LAUNCH = "launch"
    SEA_TRIALS = "sea_trials"
    DELIVERY = "delivery"
