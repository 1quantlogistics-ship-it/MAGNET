"""
structural/__init__.py - Modules 21-25 Structural Detailing exports.

ALPHA OWNS THIS FILE.

Structural Detailing System:
- Module 21: Structural Grid (Alpha)
- Module 22: Plate Generation (Alpha)
- Modules 23-25: Stiffeners, Welds, Scantlings (Bravo - pending)
"""

# Section 21-24: Enumerations (Alpha)
from .enums import (
    StructuralZone,
    PlateType,
    FrameType,
    StiffenerType,
    ProfileType,
    WeldType,
    WeldClass,
    WeldPosition,
    MaterialGrade,
)

# Section 21: Grid (Alpha)
from .grid import StructuralGrid, Frame, Bulkhead
from .grid_generator import StructuralGridGenerator

# Section 22: Plates (Alpha)
from .plates import Plate, PlateExtent
from .plate_generator import PlateGenerator
from .nesting import NestSheet, NestingResult, NestingEngine


__all__ = [
    # Enums
    "StructuralZone",
    "PlateType",
    "FrameType",
    "StiffenerType",
    "ProfileType",
    "WeldType",
    "WeldClass",
    "WeldPosition",
    "MaterialGrade",
    # Grid (Section 21)
    "StructuralGrid",
    "Frame",
    "Bulkhead",
    "StructuralGridGenerator",
    # Plates (Section 22)
    "Plate",
    "PlateExtent",
    "PlateGenerator",
    "NestSheet",
    "NestingResult",
    "NestingEngine",
]
