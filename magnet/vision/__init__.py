"""
vision/ - Vision Subsystem (Module 52)
BRAVO OWNS THIS FILE.

Provides 3D rendering, geometry intelligence, and visual snapshots.

v1.1 Changes:
- generate_from_state() uses get_state_value() with safe defaults
- Snapshot registry integration
- Phase hooks support for auto-snapshots
- Hull form generators for planing, deep-V, stepped hulls
- Material library for rendering
"""

from .geometry import (
    GeometryType,
    Vertex,
    Face,
    Mesh,
    HullGenerator,
    GeometryManager,
)

from .renderer import (
    ViewAngle,
    RenderStyle,
    RenderConfig,
    Snapshot,
    Renderer,
)

from .router import (
    VisionRequest,
    VisionResponse,
    VisionRouter,
)

from .hull_forms import (
    HullType,
    HullParameters,
    HullSection,
    HullMesh,
    PlaningHullGenerator,
    DeepVHullGenerator,
    SteppedHullGenerator,
    DisplacementHullGenerator,
    HullFormFactory,
)

from .snapshots import (
    SnapshotMetadata,
    SnapshotManager,
    PhaseSnapshotTrigger,
    create_phase_snapshot,
)

from .materials import (
    MaterialType,
    Color,
    Material,
    MarineMaterials,
    EnvironmentMaterials,
    MaterialLibrary,
    get_material_library,
)


__all__ = [
    # Geometry
    "GeometryType",
    "Vertex",
    "Face",
    "Mesh",
    "HullGenerator",
    "GeometryManager",
    # Renderer
    "ViewAngle",
    "RenderStyle",
    "RenderConfig",
    "Snapshot",
    "Renderer",
    # Router
    "VisionRequest",
    "VisionResponse",
    "VisionRouter",
    # Hull Forms
    "HullType",
    "HullParameters",
    "HullSection",
    "HullMesh",
    "PlaningHullGenerator",
    "DeepVHullGenerator",
    "SteppedHullGenerator",
    "DisplacementHullGenerator",
    "HullFormFactory",
    # Snapshots
    "SnapshotMetadata",
    "SnapshotManager",
    "PhaseSnapshotTrigger",
    "create_phase_snapshot",
    # Materials
    "MaterialType",
    "Color",
    "Material",
    "MarineMaterials",
    "EnvironmentMaterials",
    "MaterialLibrary",
    "get_material_library",
]
