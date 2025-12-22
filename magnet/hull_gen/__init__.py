"""
hull_gen/__init__.py - Modules 16-20 Hull Generation exports.

ALPHA OWNS THIS FILE.

Hull Form Generation System:
- Module 16: Parametric Hull Definition (enums, parameters, library, scaler)
- Module 17: Hull Geometry Representation (geometry, nurbs)
- Modules 18-20: Surface Generation, Fairing, Validation (Bravo)

COORDINATE FRAME CONTRACT
=========================
All hull geometry uses the following coordinate system:

  Origin: Intersection of After Perpendicular (AP), Centerline (CL),
          and Baseline (BL)

  X-axis: Forward (positive toward bow)
          - X = 0 at AP (aft perpendicular / transom)
          - X = LWL at FP (forward perpendicular)
          - X = LOA at stem

  Y-axis: Port (positive to port side)
          - Y = 0 at centerline
          - Y > 0 is port side
          - Y < 0 is starboard side (mirrored in tessellation)

  Z-axis: Up (positive toward sky)
          - Z = 0 at baseline (bottom of keel at AP)
          - Z = -draft at design waterline
          - Z = depth - draft at main deck

  Units: Meters (m) for all dimensions

  Half-Hull Convention:
          - Sections store port side only (y >= 0)
          - Tessellation mirrors to starboard
          - Centerline points (y = 0) are shared

  Catamaran Convention:
          - Demihull sections centered at y = hull_spacing/2
          - Mirrored demihull at y = -hull_spacing/2
          - No geometry at y = 0 (gap between hulls)
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
