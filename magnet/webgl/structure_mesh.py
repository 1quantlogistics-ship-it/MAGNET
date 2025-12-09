"""
webgl/structure_mesh.py - Structural visualization meshes v1.1

Module 58: WebGL 3D Visualization
ALPHA OWNS THIS FILE.

Provides mesh generation for structural elements (frames, stringers, plating).
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List
import math
import logging

from .schema import MeshData, StructureSceneData, LODLevel
from .mesh_builder import MeshBuilder
from .config import TessellationConfig

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger("webgl.structure_mesh")


class StructureMeshBuilder:
    """Builder for structural visualization meshes."""

    def __init__(self, state_manager: "StateManager"):
        self._sm = state_manager

    def build(self, lod: LODLevel = LODLevel.MEDIUM) -> StructureSceneData:
        """Build all structural meshes."""
        return StructureSceneData(
            frames=self._build_frames(lod),
            stringers=self._build_stringers(lod),
            keel=self._build_keel(lod),
            girders=self._build_girders(lod),
            plating=self._build_plating(lod),
        )

    def _get_structure_params(self) -> dict:
        """Get structural parameters from state."""
        try:
            from magnet.ui.utils import get_state_value
            return {
                "frame_spacing": get_state_value(self._sm, "structure.frame_spacing", 0.6),
                "frame_depth": get_state_value(self._sm, "structure.frame_depth_mm", 100) / 1000,
                "frame_thickness": get_state_value(self._sm, "structure.frame_thickness_mm", 6) / 1000,
                "stringer_count": get_state_value(self._sm, "structure.stringer_count", 4),
                "stringer_depth": get_state_value(self._sm, "structure.stringer_depth_mm", 80) / 1000,
                "keel_depth": get_state_value(self._sm, "structure.keel_depth_mm", 200) / 1000,
                "keel_width": get_state_value(self._sm, "structure.keel_width_mm", 150) / 1000,
                "bottom_plating": get_state_value(self._sm, "structure.bottom_plating_mm", 5) / 1000,
                "side_plating": get_state_value(self._sm, "structure.side_plating_mm", 4) / 1000,
            }
        except Exception:
            return {
                "frame_spacing": 0.6,
                "frame_depth": 0.1,
                "frame_thickness": 0.006,
                "stringer_count": 4,
                "stringer_depth": 0.08,
                "keel_depth": 0.2,
                "keel_width": 0.15,
                "bottom_plating": 0.005,
                "side_plating": 0.004,
            }

    def _get_hull_params(self) -> dict:
        """Get hull parameters from state."""
        try:
            from magnet.ui.utils import get_state_value
            return {
                "loa": get_state_value(self._sm, "hull.loa", 25.0),
                "beam": get_state_value(self._sm, "hull.beam", 6.0),
                "draft": get_state_value(self._sm, "hull.draft", 1.5),
                "depth": get_state_value(self._sm, "hull.depth", 3.0),
            }
        except Exception:
            return {
                "loa": 25.0,
                "beam": 6.0,
                "draft": 1.5,
                "depth": 3.0,
            }

    def _build_frames(self, lod: LODLevel) -> List[MeshData]:
        """Build frame meshes."""
        frames = []
        params = self._get_structure_params()
        hull = self._get_hull_params()

        spacing = params["frame_spacing"]
        depth = params["frame_depth"]
        thickness = params["frame_thickness"]

        loa = hull["loa"]
        beam = hull["beam"]
        draft = hull["draft"]
        hull_depth = hull["depth"]

        # Number of frames based on LOD
        if lod == LODLevel.LOW:
            n_frames = int(loa / spacing / 3)
        elif lod == LODLevel.HIGH or lod == LODLevel.ULTRA:
            n_frames = int(loa / spacing)
        else:
            n_frames = int(loa / spacing / 2)

        for i in range(n_frames):
            x = (i + 1) * loa / (n_frames + 1)

            # Create frame as a rectangular ring
            builder = MeshBuilder()

            # Simplified frame shape - U-shaped
            # Inner profile
            inner_points = [
                (x, -beam / 2 + depth, -draft),
                (x, -beam / 2 + depth, hull_depth - depth),
                (x, beam / 2 - depth, hull_depth - depth),
                (x, beam / 2 - depth, -draft),
            ]

            # Outer profile
            outer_points = [
                (x, -beam / 2, -draft),
                (x, -beam / 2, hull_depth),
                (x, beam / 2, hull_depth),
                (x, beam / 2, -draft),
            ]

            # Add vertices
            inner_indices = builder.add_vertices(inner_points)
            outer_indices = builder.add_vertices(outer_points)

            # Create faces between inner and outer
            for j in range(len(inner_indices) - 1):
                i0 = inner_indices[j]
                i1 = inner_indices[j + 1]
                o0 = outer_indices[j]
                o1 = outer_indices[j + 1]
                builder.add_quad(i0, o0, o1, i1)

            mesh = builder.build()
            mesh.mesh_id = f"frame_{i}"
            frames.append(mesh)

        return frames

    def _build_stringers(self, lod: LODLevel) -> List[MeshData]:
        """Build stringer meshes."""
        stringers = []
        params = self._get_structure_params()
        hull = self._get_hull_params()

        stringer_count = params["stringer_count"]
        stringer_depth = params["stringer_depth"]
        loa = hull["loa"]
        beam = hull["beam"]
        draft = hull["draft"]

        # Stringer positions (from keel upward)
        for i in range(stringer_count):
            z = -draft + (i + 1) * draft / (stringer_count + 1)

            # Port side stringer
            builder = MeshBuilder()
            y = beam / 4  # Simplified position

            # Stringer as a simple box
            points = [
                (0, y, z),
                (loa, y, z),
                (loa, y + 0.02, z),
                (0, y + 0.02, z),
                (0, y, z + stringer_depth),
                (loa, y, z + stringer_depth),
                (loa, y + 0.02, z + stringer_depth),
                (0, y + 0.02, z + stringer_depth),
            ]

            indices = builder.add_vertices(points)

            # Bottom face
            builder.add_quad(indices[0], indices[1], indices[2], indices[3])
            # Top face
            builder.add_quad(indices[4], indices[7], indices[6], indices[5])
            # Front face
            builder.add_quad(indices[0], indices[4], indices[5], indices[1])
            # Back face
            builder.add_quad(indices[3], indices[2], indices[6], indices[7])

            mesh = builder.build()
            mesh.mesh_id = f"stringer_port_{i}"
            stringers.append(mesh)

            # Starboard side (mirror)
            builder2 = MeshBuilder()
            points_starboard = [(p[0], -p[1], p[2]) for p in points]
            indices2 = builder2.add_vertices(points_starboard)
            builder2.add_quad(indices2[0], indices2[3], indices2[2], indices2[1])
            builder2.add_quad(indices2[4], indices2[5], indices2[6], indices2[7])
            builder2.add_quad(indices2[0], indices2[1], indices2[5], indices2[4])
            builder2.add_quad(indices2[3], indices2[7], indices2[6], indices2[2])

            mesh2 = builder2.build()
            mesh2.mesh_id = f"stringer_stbd_{i}"
            stringers.append(mesh2)

        return stringers

    def _build_keel(self, lod: LODLevel) -> Optional[MeshData]:
        """Build keel mesh."""
        params = self._get_structure_params()
        hull = self._get_hull_params()

        keel_depth = params["keel_depth"]
        keel_width = params["keel_width"]
        loa = hull["loa"]
        draft = hull["draft"]

        builder = MeshBuilder()

        # Keel as a box along centerline
        hw = keel_width / 2
        z_bottom = -draft - keel_depth
        z_top = -draft

        points = [
            (0, -hw, z_bottom),
            (loa, -hw, z_bottom),
            (loa, hw, z_bottom),
            (0, hw, z_bottom),
            (0, -hw, z_top),
            (loa, -hw, z_top),
            (loa, hw, z_top),
            (0, hw, z_top),
        ]

        indices = builder.add_vertices(points)

        # Bottom
        builder.add_quad(indices[0], indices[3], indices[2], indices[1])
        # Top
        builder.add_quad(indices[4], indices[5], indices[6], indices[7])
        # Front
        builder.add_quad(indices[0], indices[1], indices[5], indices[4])
        # Back
        builder.add_quad(indices[2], indices[3], indices[7], indices[6])
        # Port side
        builder.add_quad(indices[1], indices[2], indices[6], indices[5])
        # Starboard side
        builder.add_quad(indices[0], indices[4], indices[7], indices[3])

        mesh = builder.build()
        mesh.mesh_id = "keel"
        return mesh

    def _build_girders(self, lod: LODLevel) -> List[MeshData]:
        """Build girder meshes."""
        # Simplified - not implemented in basic version
        return []

    def _build_plating(self, lod: LODLevel) -> List[MeshData]:
        """Build plating visualization meshes."""
        # Simplified - not implemented in basic version
        return []
