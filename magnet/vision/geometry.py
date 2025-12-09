"""
vision/geometry.py - Geometry management v1.1

Module 52: Vision Subsystem

v1.1: Uses get_state_value() with aliases and safe defaults.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from enum import Enum
import logging

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger("vision.geometry")


class GeometryType(Enum):
    """Types of geometry objects."""
    HULL = "hull"
    DECK = "deck"
    SUPERSTRUCTURE = "superstructure"
    APPENDAGE = "appendage"
    COMPARTMENT = "compartment"
    SYSTEM = "system"


@dataclass
class Vertex:
    """3D vertex."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def to_array(self) -> Any:
        if HAS_NUMPY:
            return np.array([self.x, self.y, self.z])
        return [self.x, self.y, self.z]

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)


@dataclass
class Face:
    """Mesh face (triangle or quad)."""
    vertices: List[int] = field(default_factory=list)
    normal: Optional[Vertex] = None


@dataclass
class Mesh:
    """3D mesh geometry."""

    mesh_id: str = ""
    name: str = ""
    geometry_type: GeometryType = GeometryType.HULL

    vertices: List[Vertex] = field(default_factory=list)
    faces: List[Face] = field(default_factory=list)

    bounds_min: Optional[Vertex] = None
    bounds_max: Optional[Vertex] = None

    def get_vertex_array(self) -> Any:
        if not self.vertices:
            if HAS_NUMPY:
                return np.array([]).reshape(0, 3)
            return []
        if HAS_NUMPY:
            return np.array([v.to_array() for v in self.vertices])
        return [v.to_array() for v in self.vertices]

    def get_face_array(self) -> Any:
        if not self.faces:
            if HAS_NUMPY:
                return np.array([]).reshape(0, 3)
            return []
        if HAS_NUMPY:
            return np.array([f.vertices for f in self.faces])
        return [f.vertices for f in self.faces]

    def compute_bounds(self) -> None:
        if not self.vertices:
            return

        if HAS_NUMPY:
            coords = self.get_vertex_array()
            self.bounds_min = Vertex(*coords.min(axis=0))
            self.bounds_max = Vertex(*coords.max(axis=0))
        else:
            xs = [v.x for v in self.vertices]
            ys = [v.y for v in self.vertices]
            zs = [v.z for v in self.vertices]
            self.bounds_min = Vertex(min(xs), min(ys), min(zs))
            self.bounds_max = Vertex(max(xs), max(ys), max(zs))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mesh_id": self.mesh_id,
            "name": self.name,
            "type": self.geometry_type.value,
            "vertex_count": len(self.vertices),
            "face_count": len(self.faces),
        }


class HullGenerator:
    """
    Generate hull mesh from parameters.

    v1.1: Uses get_state_value() with aliases and safe defaults.
    """

    def __init__(self):
        self.num_stations = 21
        self.num_waterlines = 11
        self.num_buttocks = 6

    def generate_from_state(self, state: Any) -> Mesh:
        """
        Generate hull mesh from design state.

        v1.1: Uses unified accessors with safe defaults for all parameters.
        Handles missing hull.deadrise_deg and hull.transom_width_ratio via aliases.
        """
        # Import here to avoid circular imports
        from magnet.ui.utils import get_state_value

        # Extract parameters with aliases and safe defaults
        loa = get_state_value(state, "hull.loa", 25.0)
        lwl = get_state_value(state, "hull.lwl", None)
        if lwl is None:
            lwl = loa * 0.92  # Safe default

        beam = get_state_value(state, "hull.beam", None)
        if beam is None:
            beam = loa / 4.5  # Safe default

        draft = get_state_value(state, "hull.draft", None)
        if draft is None:
            draft = beam / 3.5  # Safe default

        depth = get_state_value(state, "hull.depth", None)
        if depth is None:
            depth = draft * 2.0  # Safe default

        cb = get_state_value(state, "hull.cb", 0.45)
        cp = get_state_value(state, "hull.cp", 0.65)
        cwp = get_state_value(state, "hull.cwp", 0.75)

        # v1.1: These now resolve via aliases (fixes blocker #7)
        deadrise_deg = get_state_value(state, "hull.deadrise_deg", 15.0)
        transom_ratio = get_state_value(state, "hull.transom_width_ratio", 0.8)

        return self.generate(
            loa=float(loa),
            lwl=float(lwl),
            beam=float(beam),
            draft=float(draft),
            depth=float(depth),
            cb=float(cb),
            cp=float(cp),
            cwp=float(cwp),
            deadrise_deg=float(deadrise_deg),
            transom_width_ratio=float(transom_ratio),
        )

    def generate(
        self,
        loa: float,
        lwl: float,
        beam: float,
        draft: float,
        depth: float,
        cb: float = 0.45,
        cp: float = 0.65,
        cwp: float = 0.75,
        deadrise_deg: float = 15.0,
        transom_width_ratio: float = 0.8,
    ) -> Mesh:
        """Generate hull mesh from parameters."""

        mesh = Mesh(
            mesh_id="hull_main",
            name="Main Hull",
            geometry_type=GeometryType.HULL,
        )

        if not HAS_NUMPY:
            logger.warning("NumPy not available, generating minimal hull mesh")
            # Generate minimal mesh without numpy
            mesh.vertices = [
                Vertex(0, 0, -draft),
                Vertex(lwl, 0, -draft),
                Vertex(lwl, beam/2, 0),
                Vertex(0, beam/2, 0),
            ]
            mesh.faces = [Face(vertices=[0, 1, 2]), Face(vertices=[0, 2, 3])]
            mesh.compute_bounds()
            return mesh

        stations = np.linspace(0, lwl, self.num_stations)
        half_beam = beam / 2

        for i, x in enumerate(stations):
            t = x / lwl if lwl > 0 else 0

            section_beam = self._section_beam(t, half_beam, cp, transom_width_ratio)
            section_draft = self._section_draft(t, draft, cb)

            section_verts = self._generate_section(
                x, section_beam, section_draft, depth,
                deadrise_deg, cwp,
            )

            mesh.vertices.extend(section_verts)

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

    def _section_beam(self, t: float, max_beam: float, cp: float, transom_ratio: float) -> float:
        if t < 0.1:
            return max_beam * (t / 0.1) ** 0.5 * 0.6
        elif t > 0.9:
            return max_beam * transom_ratio
        else:
            return max_beam * (1 - 0.3 * (2 * t - 1) ** 2)

    def _section_draft(self, t: float, max_draft: float, cb: float) -> float:
        if t < 0.2:
            return max_draft * (0.5 + 0.5 * t / 0.2)
        return max_draft

    def _generate_section(
        self, x: float, half_beam: float, draft: float, depth: float,
        deadrise_deg: float, cwp: float,
    ) -> List[Vertex]:
        vertices = []
        deadrise_rad = np.radians(deadrise_deg)

        vertices.append(Vertex(x, 0, -draft))

        for i in range(1, 6):
            y = half_beam * (i / 5) ** 0.8
            z_deadrise = -draft + y * np.tan(deadrise_rad)
            z = max(z_deadrise, -draft * 0.3)
            vertices.append(Vertex(x, y, z))

        for i in range(1, 5):
            y = half_beam * (1 - 0.1 * (1 - i / 4))
            z = -draft * 0.3 + (depth + draft * 0.3) * (i / 4)
            vertices.append(Vertex(x, y, z))

        vertices.append(Vertex(x, half_beam, depth - draft))

        return vertices

    def _mirror_hull(self, mesh: Mesh) -> None:
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


class GeometryManager:
    """Manages all geometry for a design."""

    def __init__(self):
        self._meshes: Dict[str, Mesh] = {}
        self._hull_generator = HullGenerator()

    def generate_hull_from_state(self, state: Any) -> Mesh:
        """Generate hull mesh from design state."""
        mesh = self._hull_generator.generate_from_state(state)
        self._meshes["hull_main"] = mesh
        return mesh

    def get_mesh(self, mesh_id: str) -> Optional[Mesh]:
        return self._meshes.get(mesh_id)

    def list_meshes(self) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self._meshes.values()]

    def export_obj(self, mesh_id: str, path: str) -> bool:
        mesh = self._meshes.get(mesh_id)
        if not mesh:
            return False

        lines = [f"# MAGNET Hull Export: {mesh.name}"]

        for v in mesh.vertices:
            lines.append(f"v {v.x:.6f} {v.y:.6f} {v.z:.6f}")

        for f in mesh.faces:
            indices = " ".join(str(i + 1) for i in f.vertices)
            lines.append(f"f {indices}")

        with open(path, 'w') as file:
            file.write("\n".join(lines))

        return True

    def export_stl(self, mesh_id: str, path: str) -> bool:
        mesh = self._meshes.get(mesh_id)
        if not mesh:
            return False

        if not HAS_NUMPY:
            logger.warning("NumPy required for STL export")
            return False

        lines = [f"solid {mesh.name}"]
        verts = mesh.get_vertex_array()

        for face in mesh.faces:
            if len(face.vertices) >= 3:
                v0 = verts[face.vertices[0]]
                v1 = verts[face.vertices[1]]
                v2 = verts[face.vertices[2]]

                edge1 = v1 - v0
                edge2 = v2 - v0
                normal = np.cross(edge1, edge2)
                norm = np.linalg.norm(normal)
                if norm > 0:
                    normal = normal / norm
                else:
                    normal = np.array([0, 0, 1])

                lines.append(f"  facet normal {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}")
                lines.append("    outer loop")
                lines.append(f"      vertex {v0[0]:.6f} {v0[1]:.6f} {v0[2]:.6f}")
                lines.append(f"      vertex {v1[0]:.6f} {v1[1]:.6f} {v1[2]:.6f}")
                lines.append(f"      vertex {v2[0]:.6f} {v2[1]:.6f} {v2[2]:.6f}")
                lines.append("    endloop")
                lines.append("  endfacet")

        lines.append(f"endsolid {mesh.name}")

        with open(path, 'w') as file:
            file.write("\n".join(lines))

        return True
