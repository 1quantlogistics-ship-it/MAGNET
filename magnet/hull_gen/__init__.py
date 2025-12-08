"""
hull_gen/__init__.py - Modules 16-20 Hull Generation exports.

ALPHA OWNS THIS FILE.

Hull Form Generation System:
- Module 16: Parametric Hull Definition (enums, parameters, library, scaler)
- Module 17: Hull Geometry Representation (geometry, nurbs)
- Modules 18-20: Surface Generation, Fairing, Validation (Bravo)
"""

# Section 16: Enumerations
from .enums import (
    HullType,
    ChineType,
    StemProfile,
    SternProfile,
    TransomType,
    KeelType,
    SectionShape,
    FairingQuality,
    HullRegion,
    SurfaceType,
)

# Section 16: Parameters
from .parameters import (
    MainDimensions,
    FormCoefficients,
    DeadriseProfile,
    HullFeatures,
    HullDefinition,
)

# Section 16: Library & Scaler
from .library import ParentHullLibrary
from .scaler import HullScaler

# Section 17: Geometry
from .geometry import (
    Point3D,
    SectionPoint,
    HullSection,
    Waterline,
    Buttock,
    HullGeometry,
)

# Section 17: NURBS
from .nurbs import NURBSCurve, NURBSSurface


__all__ = [
    # Enums (Section 16)
    "HullType",
    "ChineType",
    "StemProfile",
    "SternProfile",
    "TransomType",
    "KeelType",
    "SectionShape",
    "FairingQuality",
    "HullRegion",
    "SurfaceType",
    # Parameters (Section 16)
    "MainDimensions",
    "FormCoefficients",
    "DeadriseProfile",
    "HullFeatures",
    "HullDefinition",
    # Library (Section 16)
    "ParentHullLibrary",
    "HullScaler",
    # Geometry (Section 17)
    "Point3D",
    "SectionPoint",
    "HullSection",
    "Waterline",
    "Buttock",
    "HullGeometry",
    # NURBS (Section 17)
    "NURBSCurve",
    "NURBSSurface",
]
