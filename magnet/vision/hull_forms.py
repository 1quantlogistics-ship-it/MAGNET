"""
vision/hull_forms.py - Hull form generation v1.1
BRAVO OWNS THIS FILE.

Section 52: Vision Subsystem
Provides specialized hull form generators for different vessel types.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from enum import Enum
import math
import logging

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

from .geometry import Mesh, Vertex, Face, GeometryType

from magnet.ui.utils import get_state_value

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger("vision.hull_forms")


class HullType(Enum):
    """Types of hull forms."""
    PLANING = "planing"
    SEMI_PLANING = "semi_planing"
    DISPLACEMENT = "displacement"
    DEEP_V = "deep_v"
    CATAMARAN = "catamaran"
    STEPPED = "stepped"


# Safe defaults for aluminum HSC
SAFE_DEFAULTS = {
    "hull.loa": 25.0,
    "hull.lwl": 23.0,
    "hull.beam": 5.5,
    "hull.draft": 1.4,
    "hull.depth": 3.2,
    "hull.cb": 0.45,
    "hull.cp": 0.65,
    "hull.cwp": 0.75,
    "hull.deadrise_deg": 18.0,
    "hull.transom_width_ratio": 0.92,
    "hull.bow_half_angle_deg": 15.0,
    "hull.chine_height_ratio": 0.3,
}


@dataclass
class HullParameters:
    """Hull form parameters."""
    # Principal dimensions
    loa: float = 25.0
    lwl: float = 23.0
    beam: float = 5.5
    draft: float = 1.4
    depth: float = 3.2

    # Form coefficients
    cb: float = 0.45
    cp: float = 0.65
    cwp: float = 0.75
    cm: float = 0.70

    # Planing hull parameters
    deadrise_deg: float = 18.0
    transom_width_ratio: float = 0.92
    bow_half_angle_deg: float = 15.0
    chine_height_ratio: float = 0.3

    # Step parameters (for stepped hulls)
    step_location_ratio: float = 0.6
    step_depth_ratio: float = 0.02

    # Hull type
    hull_type: HullType = HullType.PLANING

    def validate(self) -> "HullParameters":
        """Validate and clamp parameters to realistic ranges."""
        # LOA range: 8-80m for aluminum HSC
        self.loa = max(8.0, min(80.0, self.loa))

        # LWL typically 90-96% of LOA
        self.lwl = max(self.loa * 0.90, min(self.loa * 0.96, self.lwl))

        # Beam: L/B ratio 4.0-6.0
        min_beam = self.loa / 6.0
        max_beam = self.loa / 4.0
        self.beam = max(min_beam, min(max_beam, self.beam))

        # Draft: B/T ratio 3.0-5.0
        min_draft = self.beam / 5.0
        max_draft = self.beam / 3.0
        self.draft = max(min_draft, min(max_draft, self.draft))

        # Depth: D/T ratio 2.0-3.0
        self.depth = max(self.draft * 2.0, min(self.draft * 3.0, self.depth))

        # Block coefficient: 0.35-0.55 for planing/semi-planing
        self.cb = max(0.35, min(0.55, self.cb))

        # Prismatic coefficient: 0.55-0.75
        self.cp = max(0.55, min(0.75, self.cp))

        # Deadrise: 12-25° for aluminum HSC
        self.deadrise_deg = max(12.0, min(25.0, self.deadrise_deg))

        # Transom width ratio: 0.85-0.98
        self.transom_width_ratio = max(0.85, min(0.98, self.transom_width_ratio))

        return self

    @classmethod
    def from_state(cls, state: Any) -> "HullParameters":
        """Create parameters from design state with safe defaults."""
        params = cls()

        for path, default in SAFE_DEFAULTS.items():
            attr = path.split(".")[-1]
            value = get_state_value(state, path, default)
            if hasattr(params, attr):
                setattr(params, attr, float(value) if value is not None else default)

        # Determine hull type from state
        hull_type_str = get_state_value(state, "hull.hull_type", "planing")
        try:
            params.hull_type = HullType(hull_type_str.lower())
        except (ValueError, AttributeError):
            params.hull_type = HullType.PLANING

        return params.validate()


class PlaningHullGenerator:
    """
    Generates planing hull geometry.

    v1.1: Uses safe defaults and validated parameters.
    """

    def __init__(self, num_stations: int = 21, num_waterlines: int = 11):
        self.num_stations = num_stations
        self.num_waterlines = num_waterlines

    def generate(self, params: HullParameters) -> Mesh:
        """Generate planing hull mesh."""
        mesh = Mesh(
            mesh_id="hull_planing",
            name="Planing Hull",
            geometry_type=GeometryType.HULL,
        )

        if not HAS_NUMPY:
            logger.warning("NumPy not available, using simplified hull")
            return self._generate_simplified(params, mesh)

        # Generate stations along length
        stations = np.linspace(0, params.lwl, self.num_stations)
        half_beam = params.beam / 2

        for i, x in enumerate(stations):
            t = x / params.lwl if params.lwl > 0 else 0

            # Section parameters vary along length
            section_beam = self._section_beam(t, half_beam, params)
            section_draft = self._section_draft(t, params.draft, params)
            section_deadrise = self._section_deadrise(t, params.deadrise_deg, params)

            # Generate section vertices
            section_verts = self._generate_section(
                x, section_beam, section_draft, params.depth,
                section_deadrise, params.chine_height_ratio,
            )
            mesh.vertices.extend(section_verts)

        # Generate faces
        if mesh.vertices:
            verts_per_section = len(mesh.vertices) // self.num_stations
            self._generate_faces(mesh, verts_per_section)

            # Mirror hull
            self._mirror_hull(mesh)

        mesh.compute_bounds()
        return mesh

    def _section_beam(self, t: float, max_beam: float, params: HullParameters) -> float:
        """Calculate section beam at normalized station."""
        if t < 0.1:
            # Bow region - narrow entry
            return max_beam * (t / 0.1) ** 0.5 * 0.5
        elif t > 0.9:
            # Transom region
            return max_beam * params.transom_width_ratio
        else:
            # Midship region - full beam with slight narrowing
            return max_beam * (1 - 0.15 * (2 * t - 1) ** 2)

    def _section_draft(self, t: float, max_draft: float, params: HullParameters) -> float:
        """Calculate section draft at normalized station."""
        if t < 0.15:
            # Bow rises
            return max_draft * (0.6 + 0.4 * t / 0.15)
        elif t > 0.85:
            # Stern may have different draft
            return max_draft * 0.95
        return max_draft

    def _section_deadrise(self, t: float, max_deadrise: float, params: HullParameters) -> float:
        """Calculate section deadrise angle at normalized station."""
        if t < 0.2:
            # Higher deadrise at bow
            return max_deadrise * 1.3
        elif t > 0.8:
            # Lower deadrise at stern (planing surface)
            return max_deadrise * 0.8
        return max_deadrise

    def _generate_section(
        self,
        x: float,
        half_beam: float,
        draft: float,
        depth: float,
        deadrise_deg: float,
        chine_ratio: float,
    ) -> List[Vertex]:
        """Generate vertices for a hull section."""
        vertices = []
        deadrise_rad = math.radians(deadrise_deg)

        # Keel point
        vertices.append(Vertex(x, 0, -draft))

        # Bottom panel (deadrise)
        for i in range(1, 6):
            y = half_beam * (i / 5) ** 0.8
            z_deadrise = -draft + y * math.tan(deadrise_rad)
            z = max(z_deadrise, -draft * (1 - chine_ratio))
            vertices.append(Vertex(x, y, z))

        # Chine to sheer
        chine_z = -draft * (1 - chine_ratio)
        sheer_z = depth - draft

        for i in range(1, 5):
            y = half_beam * (1 - 0.05 * (1 - i / 4))
            z = chine_z + (sheer_z - chine_z) * (i / 4)
            vertices.append(Vertex(x, y, z))

        # Sheer point
        vertices.append(Vertex(x, half_beam, sheer_z))

        return vertices

    def _generate_faces(self, mesh: Mesh, verts_per_section: int) -> None:
        """Generate mesh faces between sections."""
        for i in range(self.num_stations - 1):
            for j in range(verts_per_section - 1):
                v0 = i * verts_per_section + j
                v1 = v0 + 1
                v2 = (i + 1) * verts_per_section + j
                v3 = v2 + 1

                mesh.faces.append(Face(vertices=[v0, v1, v2]))
                mesh.faces.append(Face(vertices=[v1, v3, v2]))

    def _mirror_hull(self, mesh: Mesh) -> None:
        """Mirror hull to create port side."""
        original_count = len(mesh.vertices)

        for i in range(original_count):
            v = mesh.vertices[i]
            if v.y > 0:
                mesh.vertices.append(Vertex(v.x, -v.y, v.z))

        original_faces = len(mesh.faces)
        for i in range(original_faces):
            f = mesh.faces[i]
            mirrored = [v + original_count for v in f.vertices]
            mesh.faces.append(Face(vertices=mirrored[::-1]))

    def _generate_simplified(self, params: HullParameters, mesh: Mesh) -> Mesh:
        """Generate simplified hull without NumPy."""
        # Create basic box hull
        half_beam = params.beam / 2
        draft = params.draft
        depth = params.depth
        lwl = params.lwl

        # 8 corner vertices
        mesh.vertices = [
            Vertex(0, 0, -draft),
            Vertex(0, half_beam * 0.5, -draft * 0.5),
            Vertex(0, half_beam * 0.6, depth - draft),
            Vertex(lwl, 0, -draft),
            Vertex(lwl, half_beam, -draft * 0.8),
            Vertex(lwl, half_beam, depth - draft),
        ]

        mesh.faces = [
            Face(vertices=[0, 1, 3]),
            Face(vertices=[1, 4, 3]),
            Face(vertices=[1, 2, 4]),
            Face(vertices=[2, 5, 4]),
        ]

        self._mirror_hull(mesh)
        mesh.compute_bounds()
        return mesh


class DeepVHullGenerator(PlaningHullGenerator):
    """Generates deep-V hull forms (higher deadrise)."""

    def _section_deadrise(self, t: float, max_deadrise: float, params: HullParameters) -> float:
        """Deep-V maintains high deadrise throughout."""
        if t < 0.1:
            return max_deadrise * 1.2
        elif t > 0.9:
            return max_deadrise * 0.95
        return max_deadrise


class SteppedHullGenerator(PlaningHullGenerator):
    """Generates stepped planing hull forms."""

    def generate(self, params: HullParameters) -> Mesh:
        """Generate stepped hull mesh."""
        # Generate base hull
        mesh = super().generate(params)

        if not HAS_NUMPY or not mesh.vertices:
            return mesh

        # Add step geometry
        step_x = params.lwl * params.step_location_ratio
        step_depth = params.draft * params.step_depth_ratio

        # Modify vertices around step location
        for vertex in mesh.vertices:
            if vertex.x > step_x and vertex.z < -params.draft * 0.5:
                vertex.z -= step_depth

        mesh.name = "Stepped Planing Hull"
        mesh.mesh_id = "hull_stepped"
        return mesh


class DisplacementHullGenerator:
    """Generates displacement hull forms."""

    def __init__(self, num_stations: int = 21, num_waterlines: int = 11):
        self.num_stations = num_stations
        self.num_waterlines = num_waterlines

    def generate(self, params: HullParameters) -> Mesh:
        """Generate displacement hull mesh."""
        mesh = Mesh(
            mesh_id="hull_displacement",
            name="Displacement Hull",
            geometry_type=GeometryType.HULL,
        )

        if not HAS_NUMPY:
            return mesh

        stations = np.linspace(0, params.lwl, self.num_stations)
        half_beam = params.beam / 2

        for i, x in enumerate(stations):
            t = x / params.lwl if params.lwl > 0 else 0

            # Displacement hull has rounder sections
            section_beam = self._section_beam(t, half_beam, params)
            section_draft = self._section_draft(t, params.draft, params)

            section_verts = self._generate_round_section(
                x, section_beam, section_draft, params.depth,
            )
            mesh.vertices.extend(section_verts)

        # Generate faces
        if mesh.vertices:
            verts_per_section = len(mesh.vertices) // self.num_stations

            for i in range(self.num_stations - 1):
                for j in range(verts_per_section - 1):
                    v0 = i * verts_per_section + j
                    v1 = v0 + 1
                    v2 = (i + 1) * verts_per_section + j
                    v3 = v2 + 1

                    mesh.faces.append(Face(vertices=[v0, v1, v2]))
                    mesh.faces.append(Face(vertices=[v1, v3, v2]))

            self._mirror_hull(mesh)

        mesh.compute_bounds()
        return mesh

    def _section_beam(self, t: float, max_beam: float, params: HullParameters) -> float:
        """Calculate section beam for displacement hull."""
        if t < 0.15:
            # Bow entry
            return max_beam * math.sin(t / 0.15 * math.pi / 2) * 0.7
        elif t > 0.75:
            # Run (narrowing toward stern)
            stern_factor = (1 - t) / 0.25
            return max_beam * (0.5 + 0.5 * stern_factor)
        else:
            # Parallel midbody
            return max_beam

    def _section_draft(self, t: float, max_draft: float, params: HullParameters) -> float:
        """Calculate section draft for displacement hull."""
        if t < 0.2:
            return max_draft * (0.7 + 0.3 * t / 0.2)
        return max_draft

    def _generate_round_section(
        self,
        x: float,
        half_beam: float,
        draft: float,
        depth: float,
    ) -> List[Vertex]:
        """Generate vertices for a round section."""
        vertices = []
        num_points = 11

        for i in range(num_points):
            angle = i * math.pi / 2 / (num_points - 1)

            y = half_beam * math.sin(angle)
            z = -draft * math.cos(angle)

            # Add some bilge radius
            if i > 0 and i < num_points - 1:
                y *= 0.95 + 0.05 * math.sin(angle * 2)

            vertices.append(Vertex(x, y, z))

        # Add topside vertices to sheer
        sheer_z = depth - draft
        for i in range(3):
            y = half_beam * (1 - 0.05 * i)
            z = (sheer_z) * (i / 2)
            vertices.append(Vertex(x, y, z))

        vertices.append(Vertex(x, half_beam * 0.95, sheer_z))

        return vertices

    def _mirror_hull(self, mesh: Mesh) -> None:
        """Mirror hull geometry."""
        original_count = len(mesh.vertices)

        for i in range(original_count):
            v = mesh.vertices[i]
            if v.y > 0:
                mesh.vertices.append(Vertex(v.x, -v.y, v.z))

        original_faces = len(mesh.faces)
        for i in range(original_faces):
            f = mesh.faces[i]
            mirrored = [v + original_count for v in f.vertices]
            mesh.faces.append(Face(vertices=mirrored[::-1]))


class HullFormFactory:
    """Factory for creating hull form generators."""

    _generators = {
        HullType.PLANING: PlaningHullGenerator,
        HullType.SEMI_PLANING: PlaningHullGenerator,
        HullType.DEEP_V: DeepVHullGenerator,
        HullType.STEPPED: SteppedHullGenerator,
        HullType.DISPLACEMENT: DisplacementHullGenerator,
    }

    @classmethod
    def get_generator(cls, hull_type: HullType):
        """Get appropriate generator for hull type."""
        generator_class = cls._generators.get(hull_type, PlaningHullGenerator)
        return generator_class()

    @classmethod
    def generate_from_state(cls, state: Any) -> Mesh:
        """Generate hull mesh from design state."""
        params = HullParameters.from_state(state)
        generator = cls.get_generator(params.hull_type)
        return generator.generate(params)
