"""
cost/enums.py - Cost estimation enumerations.

ALPHA OWNS THIS FILE.

Module 12 v1.1 - Cost Estimation Framework enumerations.
"""

from enum import Enum


class CostCategory(Enum):
    """Major cost categories."""
    HULL_STRUCTURE = "hull_structure"
    PROPULSION = "propulsion"
    ELECTRICAL = "electrical"
    OUTFITTING = "outfitting"
    NAVIGATION = "navigation"
    SAFETY = "safety"
    ENGINEERING = "engineering"
    MANAGEMENT = "management"
    TESTING = "testing"
    CONTINGENCY = "contingency"


class CostConfidence(Enum):
    """Cost estimate confidence levels."""
    ROM = "rom"                  # Rough Order of Magnitude (±50%)
    BUDGETARY = "budgetary"      # Budgetary (±25%)
    DEFINITIVE = "definitive"   # Definitive (±10%)
    FIRM = "firm"               # Firm/Fixed (±5%)


class CostPhase(Enum):
    """Project cost phases."""
    DESIGN = "design"
    MATERIAL = "material"
    FABRICATION = "fabrication"
    ASSEMBLY = "assembly"
    OUTFITTING = "outfitting"
    TESTING = "testing"
    DELIVERY = "delivery"


class LifecyclePhase(Enum):
    """Lifecycle cost phases."""
    ACQUISITION = "acquisition"
    OPERATIONS = "operations"
    MAINTENANCE = "maintenance"
    DISPOSAL = "disposal"
