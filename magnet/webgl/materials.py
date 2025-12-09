"""
webgl/materials.py - Material definitions for WebGL v1.1

Module 58: WebGL 3D Visualization
ALPHA OWNS THIS FILE.

Provides material definitions for Three.js rendering.
"""

from __future__ import annotations
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

from .schema import MaterialDef

logger = logging.getLogger("webgl.materials")


# =============================================================================
# DEFAULT MATERIALS
# =============================================================================

DEFAULT_HULL_MATERIAL = MaterialDef(
    name="hull_steel",
    type="MeshStandardMaterial",
    color="#B8B8B8",
    metalness=0.9,
    roughness=0.4,
    opacity=1.0,
    transparent=False,
    side="front",
)

DEFAULT_STRUCTURE_MATERIAL = MaterialDef(
    name="structure_steel",
    type="MeshStandardMaterial",
    color="#708090",
    metalness=0.8,
    roughness=0.5,
    opacity=1.0,
    transparent=False,
    side="double",
)

DEFAULT_WATERLINE_MATERIAL = MaterialDef(
    name="waterline",
    type="MeshBasicMaterial",
    color="#0066CC",
    metalness=0.0,
    roughness=1.0,
    opacity=0.8,
    transparent=True,
    side="double",
)

DEFAULT_DECK_MATERIAL = MaterialDef(
    name="deck_teak",
    type="MeshStandardMaterial",
    color="#DEB887",
    metalness=0.0,
    roughness=0.8,
    opacity=1.0,
    transparent=False,
    side="front",
)

DEFAULT_TRANSOM_MATERIAL = MaterialDef(
    name="transom",
    type="MeshStandardMaterial",
    color="#B8B8B8",
    metalness=0.85,
    roughness=0.45,
    opacity=1.0,
    transparent=False,
    side="double",
)

DEFAULT_KEEL_MATERIAL = MaterialDef(
    name="keel",
    type="MeshStandardMaterial",
    color="#404040",
    metalness=0.95,
    roughness=0.3,
    opacity=1.0,
    transparent=False,
    side="front",
)

DEFAULT_XRAY_MATERIAL = MaterialDef(
    name="xray",
    type="MeshBasicMaterial",
    color="#FFFFFF",
    metalness=0.0,
    roughness=1.0,
    opacity=0.15,
    transparent=True,
    side="double",
)

DEFAULT_WIREFRAME_MATERIAL = MaterialDef(
    name="wireframe",
    type="MeshBasicMaterial",
    color="#333333",
    metalness=0.0,
    roughness=1.0,
    opacity=1.0,
    transparent=False,
    side="double",
)

DEFAULT_HIGHLIGHT_MATERIAL = MaterialDef(
    name="highlight",
    type="MeshBasicMaterial",
    color="#FFFF00",
    metalness=0.0,
    roughness=1.0,
    opacity=0.6,
    transparent=True,
    side="double",
    emissive="#FFFF00",
    emissiveIntensity=0.5,
)


# =============================================================================
# MATERIAL LIBRARY
# =============================================================================

class MaterialLibrary:
    """Library of material definitions for 3D rendering."""

    def __init__(self):
        self._materials: Dict[str, MaterialDef] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default materials."""
        defaults = [
            DEFAULT_HULL_MATERIAL,
            DEFAULT_STRUCTURE_MATERIAL,
            DEFAULT_WATERLINE_MATERIAL,
            DEFAULT_DECK_MATERIAL,
            DEFAULT_TRANSOM_MATERIAL,
            DEFAULT_KEEL_MATERIAL,
            DEFAULT_XRAY_MATERIAL,
            DEFAULT_WIREFRAME_MATERIAL,
            DEFAULT_HIGHLIGHT_MATERIAL,
        ]

        for mat in defaults:
            self._materials[mat.name] = mat

    def get(self, name: str) -> Optional[MaterialDef]:
        """Get material by name."""
        return self._materials.get(name)

    def get_or_default(self, name: str, default: MaterialDef = None) -> MaterialDef:
        """Get material by name, returning default if not found."""
        return self._materials.get(name, default or DEFAULT_HULL_MATERIAL)

    def add(self, material: MaterialDef) -> None:
        """Add or update a material."""
        self._materials[material.name] = material
        logger.debug(f"Added material: {material.name}")

    def remove(self, name: str) -> bool:
        """Remove a material."""
        if name in self._materials:
            del self._materials[name]
            return True
        return False

    def list_all(self) -> List[MaterialDef]:
        """Get all materials."""
        return list(self._materials.values())

    def to_dict(self) -> Dict[str, Dict]:
        """Serialize library to dictionary."""
        return {name: mat.to_dict() for name, mat in self._materials.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Dict]) -> "MaterialLibrary":
        """Create library from dictionary."""
        library = cls()
        for name, mat_data in data.items():
            library.add(MaterialDef.from_dict(mat_data))
        return library


# =============================================================================
# MATERIAL PRESETS
# =============================================================================

def get_render_mode_materials(mode: str) -> List[MaterialDef]:
    """
    Get materials for a render mode.

    Modes:
    - solid: Standard PBR materials
    - wireframe: Wireframe rendering
    - xray: Transparent X-ray view
    - structure: Highlight structural elements
    """
    if mode == "wireframe":
        return [
            MaterialDef(
                name="wireframe_hull",
                type="MeshBasicMaterial",
                color="#333333",
                metalness=0.0,
                roughness=1.0,
                opacity=1.0,
                transparent=False,
                side="front",
            ),
        ]

    elif mode == "xray":
        return [
            MaterialDef(
                name="xray_hull",
                type="MeshBasicMaterial",
                color="#FFFFFF",
                metalness=0.0,
                roughness=1.0,
                opacity=0.15,
                transparent=True,
                side="double",
            ),
            MaterialDef(
                name="xray_structure",
                type="MeshBasicMaterial",
                color="#0066CC",
                metalness=0.0,
                roughness=1.0,
                opacity=0.8,
                transparent=True,
                side="double",
            ),
        ]

    elif mode == "structure":
        return [
            MaterialDef(
                name="hull_transparent",
                type="MeshStandardMaterial",
                color="#B8B8B8",
                metalness=0.5,
                roughness=0.5,
                opacity=0.3,
                transparent=True,
                side="front",
            ),
            DEFAULT_STRUCTURE_MATERIAL,
            DEFAULT_KEEL_MATERIAL,
        ]

    else:  # solid (default)
        return [
            DEFAULT_HULL_MATERIAL,
            DEFAULT_DECK_MATERIAL,
            DEFAULT_TRANSOM_MATERIAL,
        ]


def get_paint_scheme_materials(scheme: str) -> List[MaterialDef]:
    """
    Get materials for a paint scheme.

    Schemes:
    - steel: Raw steel finish
    - white: Classic white yacht
    - navy: Navy blue with white superstructure
    - racing: High-visibility racing colors
    """
    schemes = {
        "steel": [
            MaterialDef(name="hull_steel", type="MeshStandardMaterial",
                       color="#B8B8B8", metalness=0.9, roughness=0.4),
        ],
        "white": [
            MaterialDef(name="hull_white", type="MeshStandardMaterial",
                       color="#FAFAFA", metalness=0.1, roughness=0.6),
            MaterialDef(name="accent_blue", type="MeshStandardMaterial",
                       color="#003366", metalness=0.1, roughness=0.5),
        ],
        "navy": [
            MaterialDef(name="hull_navy", type="MeshStandardMaterial",
                       color="#1A237E", metalness=0.2, roughness=0.5),
            MaterialDef(name="superstructure_white", type="MeshStandardMaterial",
                       color="#FFFFFF", metalness=0.1, roughness=0.6),
        ],
        "racing": [
            MaterialDef(name="hull_orange", type="MeshStandardMaterial",
                       color="#FF6600", metalness=0.3, roughness=0.4),
            MaterialDef(name="accent_black", type="MeshStandardMaterial",
                       color="#1A1A1A", metalness=0.8, roughness=0.3),
        ],
    }

    return schemes.get(scheme, schemes["steel"])


# Global material library instance
_material_library: Optional[MaterialLibrary] = None


def get_material_library() -> MaterialLibrary:
    """Get the global material library."""
    global _material_library
    if _material_library is None:
        _material_library = MaterialLibrary()
    return _material_library
