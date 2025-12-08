"""
MAGNET Arrangement Module (Module 08)

Provides general arrangement generation and validation for vessels.
Includes tank definitions, compartments, bulkheads, and deck layouts.

Version 1.1 - Production-Ready with critical fixes.
"""

from .models import (
    # Enumerations
    FluidType,
    SpaceType,
    DeckType,
    BulkheadType,
    FLUID_DENSITIES,
    STANDARD_PERMEABILITIES,

    # Data classes
    Tank,
    DeckDefinition,
    BulkheadDefinition,
    Compartment,
    GeneralArrangement,

    # Utilities
    determinize_dict,
)

from .generator import (
    VesselServiceProfile,
    ArrangementGenerator,
)

from .validators import (
    ArrangementValidator,
)

__all__ = [
    # Enumerations
    "FluidType",
    "SpaceType",
    "DeckType",
    "BulkheadType",
    "FLUID_DENSITIES",
    "STANDARD_PERMEABILITIES",

    # Data classes
    "Tank",
    "DeckDefinition",
    "BulkheadDefinition",
    "Compartment",
    "GeneralArrangement",

    # Generator
    "VesselServiceProfile",
    "ArrangementGenerator",

    # Validators
    "ArrangementValidator",

    # Utilities
    "determinize_dict",
]
