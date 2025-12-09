"""
vision/materials.py - Material library v1.1
BRAVO OWNS THIS FILE.

Section 52: Vision Subsystem
Defines materials for rendering hull and structure.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger("vision.materials")


class MaterialType(Enum):
    """Types of materials."""
    METAL = "metal"
    COMPOSITE = "composite"
    PAINT = "paint"
    GLASS = "glass"
    RUBBER = "rubber"
    WATER = "water"
    SKY = "sky"


@dataclass
class Color:
    """RGB color with alpha."""
    r: float = 0.5
    g: float = 0.5
    b: float = 0.5
    a: float = 1.0

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.r, self.g, self.b)

    def to_rgba(self) -> Tuple[float, float, float, float]:
        return (self.r, self.g, self.b, self.a)

    def to_hex(self) -> str:
        r = int(self.r * 255)
        g = int(self.g * 255)
        b = int(self.b * 255)
        return f"#{r:02x}{g:02x}{b:02x}"

    @classmethod
    def from_hex(cls, hex_color: str) -> "Color":
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16) / 255
        g = int(hex_color[2:4], 16) / 255
        b = int(hex_color[4:6], 16) / 255
        return cls(r, g, b)

    @classmethod
    def white(cls) -> "Color":
        return cls(1.0, 1.0, 1.0)

    @classmethod
    def black(cls) -> "Color":
        return cls(0.0, 0.0, 0.0)

    @classmethod
    def aluminum(cls) -> "Color":
        return cls(0.77, 0.78, 0.78)

    @classmethod
    def steel(cls) -> "Color":
        return cls(0.55, 0.56, 0.58)

    @classmethod
    def marine_white(cls) -> "Color":
        return cls(0.95, 0.95, 0.93)

    @classmethod
    def navy_blue(cls) -> "Color":
        return cls(0.0, 0.12, 0.25)

    @classmethod
    def ocean_blue(cls) -> "Color":
        return cls(0.0, 0.4, 0.6)


@dataclass
class Material:
    """Material definition for rendering."""
    name: str = "Default"
    material_type: MaterialType = MaterialType.METAL

    # Colors
    diffuse: Color = field(default_factory=Color.aluminum)
    specular: Color = field(default_factory=Color.white)
    ambient: Color = field(default_factory=lambda: Color(0.1, 0.1, 0.1))
    emissive: Color = field(default_factory=lambda: Color(0.0, 0.0, 0.0))

    # Lighting properties
    shininess: float = 50.0  # 0-128
    reflectivity: float = 0.3  # 0-1
    transparency: float = 0.0  # 0-1
    roughness: float = 0.5  # 0-1 (PBR)
    metallic: float = 0.8  # 0-1 (PBR)

    # Texture
    texture_path: Optional[str] = None
    bump_map_path: Optional[str] = None
    normal_map_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.material_type.value,
            "diffuse": self.diffuse.to_hex(),
            "specular": self.specular.to_hex(),
            "shininess": self.shininess,
            "reflectivity": self.reflectivity,
            "roughness": self.roughness,
            "metallic": self.metallic,
        }


# Standard marine materials
class MarineMaterials:
    """Standard materials for marine vessels."""

    @staticmethod
    def aluminum_hull() -> Material:
        """Bare aluminum hull material."""
        return Material(
            name="Aluminum Hull",
            material_type=MaterialType.METAL,
            diffuse=Color.aluminum(),
            specular=Color(0.9, 0.9, 0.9),
            shininess=80.0,
            reflectivity=0.4,
            roughness=0.3,
            metallic=1.0,
        )

    @staticmethod
    def painted_hull(color: Color = None) -> Material:
        """Painted hull material."""
        return Material(
            name="Painted Hull",
            material_type=MaterialType.PAINT,
            diffuse=color or Color.marine_white(),
            specular=Color(0.3, 0.3, 0.3),
            shininess=30.0,
            reflectivity=0.1,
            roughness=0.6,
            metallic=0.0,
        )

    @staticmethod
    def antifouling_bottom() -> Material:
        """Antifouling paint for bottom."""
        return Material(
            name="Antifouling Bottom",
            material_type=MaterialType.PAINT,
            diffuse=Color(0.3, 0.1, 0.1),  # Dark red/copper
            specular=Color(0.1, 0.1, 0.1),
            shininess=10.0,
            reflectivity=0.05,
            roughness=0.8,
            metallic=0.0,
        )

    @staticmethod
    def steel_structure() -> Material:
        """Steel structural elements."""
        return Material(
            name="Steel Structure",
            material_type=MaterialType.METAL,
            diffuse=Color.steel(),
            specular=Color(0.7, 0.7, 0.7),
            shininess=60.0,
            reflectivity=0.3,
            roughness=0.4,
            metallic=0.9,
        )

    @staticmethod
    def stainless_steel() -> Material:
        """Stainless steel fittings."""
        return Material(
            name="Stainless Steel",
            material_type=MaterialType.METAL,
            diffuse=Color(0.8, 0.8, 0.82),
            specular=Color(1.0, 1.0, 1.0),
            shininess=100.0,
            reflectivity=0.5,
            roughness=0.2,
            metallic=1.0,
        )

    @staticmethod
    def teak_deck() -> Material:
        """Teak deck material."""
        return Material(
            name="Teak Deck",
            material_type=MaterialType.COMPOSITE,
            diffuse=Color(0.6, 0.45, 0.25),
            specular=Color(0.2, 0.2, 0.2),
            shininess=20.0,
            reflectivity=0.05,
            roughness=0.7,
            metallic=0.0,
        )

    @staticmethod
    def fiberglass() -> Material:
        """Fiberglass composite."""
        return Material(
            name="Fiberglass",
            material_type=MaterialType.COMPOSITE,
            diffuse=Color.marine_white(),
            specular=Color(0.4, 0.4, 0.4),
            shininess=40.0,
            reflectivity=0.15,
            roughness=0.5,
            metallic=0.0,
        )

    @staticmethod
    def window_glass() -> Material:
        """Window glass material."""
        return Material(
            name="Window Glass",
            material_type=MaterialType.GLASS,
            diffuse=Color(0.1, 0.15, 0.2, 0.3),
            specular=Color(1.0, 1.0, 1.0),
            shininess=100.0,
            reflectivity=0.6,
            transparency=0.8,
            roughness=0.1,
            metallic=0.0,
        )

    @staticmethod
    def rubber_fender() -> Material:
        """Rubber fender material."""
        return Material(
            name="Rubber Fender",
            material_type=MaterialType.RUBBER,
            diffuse=Color(0.1, 0.1, 0.1),
            specular=Color(0.1, 0.1, 0.1),
            shininess=5.0,
            reflectivity=0.02,
            roughness=0.9,
            metallic=0.0,
        )


class EnvironmentMaterials:
    """Environment materials for rendering."""

    @staticmethod
    def ocean_water() -> Material:
        """Ocean water material."""
        return Material(
            name="Ocean Water",
            material_type=MaterialType.WATER,
            diffuse=Color.ocean_blue(),
            specular=Color(0.8, 0.8, 0.9),
            shininess=80.0,
            reflectivity=0.7,
            transparency=0.4,
            roughness=0.2,
            metallic=0.0,
        )

    @staticmethod
    def calm_water() -> Material:
        """Calm water material."""
        return Material(
            name="Calm Water",
            material_type=MaterialType.WATER,
            diffuse=Color(0.1, 0.3, 0.5),
            specular=Color(0.9, 0.9, 1.0),
            shininess=100.0,
            reflectivity=0.8,
            transparency=0.5,
            roughness=0.1,
            metallic=0.0,
        )

    @staticmethod
    def sky_day() -> Material:
        """Daytime sky material."""
        return Material(
            name="Day Sky",
            material_type=MaterialType.SKY,
            diffuse=Color(0.5, 0.7, 0.9),
            emissive=Color(0.3, 0.4, 0.5),
        )


class MaterialLibrary:
    """
    Library of materials for vessel rendering.
    """

    def __init__(self):
        self._materials: Dict[str, Material] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default material library."""
        # Hull materials
        self.add("aluminum_hull", MarineMaterials.aluminum_hull())
        self.add("painted_hull_white", MarineMaterials.painted_hull(Color.marine_white()))
        self.add("painted_hull_navy", MarineMaterials.painted_hull(Color.navy_blue()))
        self.add("antifouling", MarineMaterials.antifouling_bottom())

        # Structure materials
        self.add("steel", MarineMaterials.steel_structure())
        self.add("stainless", MarineMaterials.stainless_steel())

        # Deck materials
        self.add("teak", MarineMaterials.teak_deck())
        self.add("fiberglass", MarineMaterials.fiberglass())

        # Other
        self.add("glass", MarineMaterials.window_glass())
        self.add("rubber", MarineMaterials.rubber_fender())

        # Environment
        self.add("ocean", EnvironmentMaterials.ocean_water())
        self.add("calm_water", EnvironmentMaterials.calm_water())
        self.add("sky", EnvironmentMaterials.sky_day())

    def add(self, key: str, material: Material) -> None:
        """Add a material to the library."""
        self._materials[key] = material

    def get(self, key: str) -> Optional[Material]:
        """Get a material by key."""
        return self._materials.get(key)

    def get_or_default(self, key: str, default: str = "aluminum_hull") -> Material:
        """Get a material or return default."""
        return self._materials.get(key) or self._materials.get(default, Material())

    def list_materials(self) -> List[str]:
        """List all material keys."""
        return list(self._materials.keys())

    def get_hull_material(self, hull_material: str = "aluminum") -> Material:
        """Get appropriate hull material based on specification."""
        material_map = {
            "aluminum": "aluminum_hull",
            "aluminium": "aluminum_hull",
            "steel": "steel",
            "fiberglass": "fiberglass",
            "frp": "fiberglass",
            "composite": "fiberglass",
            "painted": "painted_hull_white",
        }
        key = material_map.get(hull_material.lower(), "aluminum_hull")
        return self.get_or_default(key)

    def create_custom(
        self,
        name: str,
        color: str = "#808080",
        metallic: float = 0.5,
        roughness: float = 0.5,
    ) -> Material:
        """Create a custom material."""
        return Material(
            name=name,
            material_type=MaterialType.PAINT,
            diffuse=Color.from_hex(color),
            metallic=metallic,
            roughness=roughness,
        )


# Global material library instance
_material_library: Optional[MaterialLibrary] = None


def get_material_library() -> MaterialLibrary:
    """Get the global material library."""
    global _material_library
    if _material_library is None:
        _material_library = MaterialLibrary()
    return _material_library
