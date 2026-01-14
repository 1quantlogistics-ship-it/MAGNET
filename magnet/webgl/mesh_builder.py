"""
webgl/mesh_builder.py - Mesh construction utilities v1.2

Module 58: WebGL 3D Visualization
ALPHA OWNS THIS FILE.

Provides utilities for building triangle meshes with proper normals.

v1.2 Changes:
- Added EdgeType support for hard edge rendering
- Added split normal computation at hard edges
- Added mark_hard_edge() method
"""

from __future__ import annotations
from typing import List, Tuple, Optional, Set, Dict
from dataclasses import dataclass, field
from enum import Enum
import math
import logging

from .schema import MeshData
from magnet.core.constants import EPSILON_VECTOR, EPSILON_GEOMETRY

logger = logging.getLogger("webgl.mesh_builder")


# Import EdgeType from hull_gen if available, otherwise define locally
try:
    from magnet.hull_gen.geometry import EdgeType
except ImportError:
    class EdgeType(Enum):
        """Edge rendering type (local fallback)."""
        SMOOTH = "smooth"
        HARD = "hard"
        CREASE = "crease"


class MeshBuilder:
    """
    Builder for constructing triangle meshes with hard edge support.

    Usage:
        builder = MeshBuilder()
        v0 = builder.add_vertex(0, 0, 0)
        v1 = builder.add_vertex(1, 0, 0)
        v2 = builder.add_vertex(0, 1, 0)
        builder.add_triangle(v0, v1, v2)
        mesh = builder.build()
        
    v1.2: Support for hard edges via edge_type parameter and mark_hard_edge().
    """

    def __init__(self):
        self._vertices: List[float] = []
        self._indices: List[int] = []
        self._normals: List[float] = []  # v1.3: Explicit normals for faceted surfaces
        self._vertex_count = 0
        
        # v1.2: Edge type tracking for split normal support
        self._vertex_edge_types: List[EdgeType] = []
        self._hard_edges: Set[Tuple[int, int]] = set()  # Pairs of vertex indices (ordered)

    def add_vertex(
        self, 
        x: float, 
        y: float, 
        z: float,
        edge_type: EdgeType = EdgeType.SMOOTH,
    ) -> int:
        """Add a vertex with optional edge type and return its index."""
        self._vertices.extend([x, y, z])
        self._vertex_edge_types.append(edge_type)
        idx = self._vertex_count
        self._vertex_count += 1
        return idx
    
    def add_vertex_with_normal(
        self,
        x: float,
        y: float,
        z: float,
        nx: float,
        ny: float,
        nz: float,
        edge_type: EdgeType = EdgeType.SMOOTH,
    ) -> int:
        """
        Add a vertex with explicit normal.
        
        Phase 6: Used for faceted tessellation and deck surfaces where
        normals are computed per-face rather than averaged.
        """
        self._vertices.extend([x, y, z])
        self._vertex_edge_types.append(edge_type)
        # Extend normals array to match vertex count
        while len(self._normals) < len(self._vertices) - 3:
            self._normals.extend([0.0, 0.0, 1.0])
        self._normals.extend([nx, ny, nz])
        idx = self._vertex_count
        self._vertex_count += 1
        return idx

    def add_vertices(self, vertices: List[Tuple[float, float, float]]) -> List[int]:
        """Add multiple vertices and return their indices."""
        indices = []
        for x, y, z in vertices:
            indices.append(self.add_vertex(x, y, z))
        return indices

    def add_triangle(self, v0: int, v1: int, v2: int) -> None:
        """Add a triangle face (counter-clockwise winding)."""
        self._indices.extend([v0, v1, v2])

    def add_quad(self, v0: int, v1: int, v2: int, v3: int) -> None:
        """Add a quad as two triangles (v0,v1,v2,v3 in CCW order)."""
        self.add_triangle(v0, v1, v2)
        self.add_triangle(v0, v2, v3)

    def add_triangle_strip(self, vertex_indices: List[int]) -> None:
        """Add triangles from a triangle strip."""
        for i in range(len(vertex_indices) - 2):
            if i % 2 == 0:
                self.add_triangle(
                    vertex_indices[i],
                    vertex_indices[i + 1],
                    vertex_indices[i + 2],
                )
            else:
                self.add_triangle(
                    vertex_indices[i],
                    vertex_indices[i + 2],
                    vertex_indices[i + 1],
                )

    def add_triangle_fan(self, center: int, ring: List[int]) -> None:
        """Add triangles from a fan around center vertex."""
        for i in range(len(ring) - 1):
            self.add_triangle(center, ring[i], ring[i + 1])

    def mark_hard_edge(self, v0: int, v1: int) -> None:
        """
        Mark edge between v0 and v1 as hard.
        
        v1.2: Hard edges cause normal splitting at these vertices.
        """
        # Store as ordered tuple for consistent lookup
        edge = (min(v0, v1), max(v0, v1))
        self._hard_edges.add(edge)

    def build(self, compute_normals: bool = True) -> MeshData:
        """
        Build the final mesh.
        
        v1.2: If any vertices have EdgeType.HARD or hard edges are marked,
        uses split normal computation instead of smooth averaging.
        """
        has_hard_edges = (
            self._hard_edges or 
            any(et == EdgeType.HARD for et in self._vertex_edge_types)
        )
        
        if compute_normals:
            if has_hard_edges:
                # Use split normal algorithm
                vertices, indices, normals = self._compute_split_normals()
                return MeshData(
                    vertices=vertices,
                    indices=indices,
                    normals=normals,
                )
            else:
                # Use standard smooth normals
                normals = compute_vertex_normals(self._vertices, self._indices)
        else:
            normals = [0.0, 1.0, 0.0] * self._vertex_count

        return MeshData(
            vertices=self._vertices,
            indices=self._indices,
            normals=normals,
        )

    def _compute_split_normals(self) -> Tuple[List[float], List[int], List[float]]:
        """
        Compute normals with vertex splitting at hard edges.
        
        Algorithm:
        1. Compute face normals for all triangles
        2. For each vertex, group adjacent faces by hard edge boundaries
        3. For each group, average face normals
        4. If vertex has multiple groups, duplicate vertex
        5. Return expanded vertex/normal/index arrays
        
        v1.2: Foundation for hard chine rendering.
        """
        num_vertices = self._vertex_count
        num_triangles = len(self._indices) // 3
        
        if num_vertices == 0 or num_triangles == 0:
            return self._vertices.copy(), self._indices.copy(), [0.0, 0.0, 1.0] * num_vertices
        
        # Step 1: Compute face normals
        face_normals = self._compute_face_normals()
        
        # Step 2: Build vertex -> face adjacency
        vertex_faces: Dict[int, List[int]] = {i: [] for i in range(num_vertices)}
        for face_idx in range(num_triangles):
            for j in range(3):
                v = self._indices[face_idx * 3 + j]
                vertex_faces[v].append(face_idx)
        
        # Step 3-4: Process each vertex
        new_vertices: List[float] = []
        new_normals: List[float] = []
        new_indices: List[int] = list(self._indices)  # Will be updated
        
        # Track vertex remapping: (old_vertex_idx, face_idx) -> new_vertex_idx
        vertex_remap: Dict[Tuple[int, int], int] = {}
        
        for v_idx in range(num_vertices):
            edge_type = self._vertex_edge_types[v_idx] if v_idx < len(self._vertex_edge_types) else EdgeType.SMOOTH
            faces = vertex_faces[v_idx]
            
            if not faces:
                # Orphan vertex - keep as-is with default normal
                new_v_idx = len(new_vertices) // 3
                new_vertices.extend(self._vertices[v_idx*3 : v_idx*3+3])
                new_normals.extend([0.0, 0.0, 1.0])
                continue
            
            if edge_type == EdgeType.SMOOTH and not self._vertex_has_hard_edge(v_idx, faces):
                # Single vertex, averaged normal (standard behavior)
                avg_normal = self._average_face_normals([face_normals[f] for f in faces])
                new_v_idx = len(new_vertices) // 3
                new_vertices.extend(self._vertices[v_idx*3 : v_idx*3+3])
                new_normals.extend(avg_normal)
                
                # Update all face references
                for face_idx in faces:
                    for j in range(3):
                        if self._indices[face_idx * 3 + j] == v_idx:
                            new_indices[face_idx * 3 + j] = new_v_idx
            
            else:
                # Hard edge vertex - group faces and split
                face_groups = self._group_faces_by_hard_edges(v_idx, faces)
                
                for group_faces in face_groups:
                    avg_normal = self._average_face_normals([face_normals[f] for f in group_faces])
                    new_v_idx = len(new_vertices) // 3
                    new_vertices.extend(self._vertices[v_idx*3 : v_idx*3+3])
                    new_normals.extend(avg_normal)
                    
                    # Update face references for this group
                    for face_idx in group_faces:
                        for j in range(3):
                            if self._indices[face_idx * 3 + j] == v_idx:
                                new_indices[face_idx * 3 + j] = new_v_idx
        
        return new_vertices, new_indices, new_normals

    def _compute_face_normals(self) -> List[Tuple[float, float, float]]:
        """Compute normal for each triangle face."""
        normals = []
        num_triangles = len(self._indices) // 3
        
        for i in range(num_triangles):
            i0, i1, i2 = self._indices[i * 3], self._indices[i * 3 + 1], self._indices[i * 3 + 2]
            
            p0 = self._get_vertex(i0)
            p1 = self._get_vertex(i1)
            p2 = self._get_vertex(i2)
            
            # Cross product of edges
            e1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
            e2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
            
            nx = e1[1] * e2[2] - e1[2] * e2[1]
            ny = e1[2] * e2[0] - e1[0] * e2[2]
            nz = e1[0] * e2[1] - e1[1] * e2[0]
            
            # Normalize
            length = math.sqrt(nx*nx + ny*ny + nz*nz)
            if length > EPSILON_VECTOR:
                nx, ny, nz = nx/length, ny/length, nz/length
            else:
                nx, ny, nz = 0.0, 0.0, 1.0
            
            normals.append((nx, ny, nz))
        
        return normals

    def _get_vertex(self, idx: int) -> Tuple[float, float, float]:
        """Get vertex position by index."""
        return (
            self._vertices[idx * 3],
            self._vertices[idx * 3 + 1],
            self._vertices[idx * 3 + 2],
        )

    def _average_face_normals(self, normals: List[Tuple[float, float, float]]) -> List[float]:
        """Average a list of face normals."""
        if not normals:
            return [0.0, 0.0, 1.0]
        
        nx = sum(n[0] for n in normals)
        ny = sum(n[1] for n in normals)
        nz = sum(n[2] for n in normals)
        
        length = math.sqrt(nx*nx + ny*ny + nz*nz)
        if length > EPSILON_VECTOR:
            return [nx/length, ny/length, nz/length]
        else:
            return [0.0, 0.0, 1.0]

    def _vertex_has_hard_edge(self, vertex_idx: int, faces: List[int]) -> bool:
        """Check if vertex is connected to any hard edge."""
        for face_idx in faces:
            for j in range(3):
                v0 = self._indices[face_idx * 3 + j]
                v1 = self._indices[face_idx * 3 + (j + 1) % 3]
                
                if v0 == vertex_idx or v1 == vertex_idx:
                    edge = (min(v0, v1), max(v0, v1))
                    if edge in self._hard_edges:
                        return True
        return False

    def _group_faces_by_hard_edges(self, vertex_idx: int, faces: List[int]) -> List[List[int]]:
        """
        Group faces around a vertex by hard edge boundaries.
        
        Faces in the same group share smooth edges.
        Hard edges create group boundaries.
        """
        if not faces:
            return []
        
        if not self._hard_edges and not any(
            self._vertex_edge_types[vertex_idx] == EdgeType.HARD 
            for _ in [0] if vertex_idx < len(self._vertex_edge_types)
        ):
            # No hard edges, all faces in one group
            return [faces]
        
        # Build face adjacency (faces sharing an edge at this vertex, excluding hard edges)
        face_neighbors: Dict[int, Set[int]] = {f: set() for f in faces}
        
        for i, f1 in enumerate(faces):
            for f2 in faces[i+1:]:
                shared_edge = self._get_shared_edge(f1, f2, vertex_idx)
                if shared_edge is not None and shared_edge not in self._hard_edges:
                    face_neighbors[f1].add(f2)
                    face_neighbors[f2].add(f1)
        
        # Flood fill to find connected groups
        groups = []
        remaining = set(faces)
        
        while remaining:
            group = []
            start = remaining.pop()
            stack = [start]
            
            while stack:
                f = stack.pop()
                group.append(f)
                for neighbor in face_neighbors[f]:
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        stack.append(neighbor)
            
            groups.append(group)
        
        return groups

    def _get_shared_edge(self, f1: int, f2: int, vertex_idx: int) -> Optional[Tuple[int, int]]:
        """Get the edge shared by two faces at a given vertex, if any."""
        verts1 = set(self._indices[f1*3 : f1*3+3])
        verts2 = set(self._indices[f2*3 : f2*3+3])
        shared = verts1 & verts2
        
        if vertex_idx in shared and len(shared) == 2:
            other = (shared - {vertex_idx}).pop()
            return (min(vertex_idx, other), max(vertex_idx, other))
        return None

    @property
    def vertex_count(self) -> int:
        return self._vertex_count

    @property
    def face_count(self) -> int:
        return len(self._indices) // 3


def compute_normals(vertices: List[float], indices: List[int]) -> List[float]:
    """Compute per-vertex normals from mesh data (alias for compute_vertex_normals)."""
    return compute_vertex_normals(vertices, indices)


def compute_vertex_normals(vertices: List[float], indices: List[int]) -> List[float]:
    """
    Compute smooth per-vertex normals.

    Uses angle-weighted averaging of face normals.
    """
    vertex_count = len(vertices) // 3

    # Initialize normals to zero
    normals = [0.0] * len(vertices)

    # Accumulate face normals
    for i in range(0, len(indices), 3):
        i0, i1, i2 = indices[i], indices[i + 1], indices[i + 2]

        # Get vertex positions
        v0 = (vertices[i0 * 3], vertices[i0 * 3 + 1], vertices[i0 * 3 + 2])
        v1 = (vertices[i1 * 3], vertices[i1 * 3 + 1], vertices[i1 * 3 + 2])
        v2 = (vertices[i2 * 3], vertices[i2 * 3 + 1], vertices[i2 * 3 + 2])

        # Calculate edges
        e1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
        e2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])

        # Cross product for face normal
        nx = e1[1] * e2[2] - e1[2] * e2[1]
        ny = e1[2] * e2[0] - e1[0] * e2[2]
        nz = e1[0] * e2[1] - e1[1] * e2[0]

        # Accumulate to each vertex
        for idx in [i0, i1, i2]:
            normals[idx * 3] += nx
            normals[idx * 3 + 1] += ny
            normals[idx * 3 + 2] += nz

    # Normalize all normals
    for i in range(vertex_count):
        nx = normals[i * 3]
        ny = normals[i * 3 + 1]
        nz = normals[i * 3 + 2]

        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length > EPSILON_VECTOR:
            normals[i * 3] = nx / length
            normals[i * 3 + 1] = ny / length
            normals[i * 3 + 2] = nz / length
        else:
            # Default to up vector for degenerate normals
            normals[i * 3] = 0.0
            normals[i * 3 + 1] = 0.0
            normals[i * 3 + 2] = 1.0

    return normals


def compute_uvs(
    vertices: List[float],
    projection: str = "box",
    scale: float = 1.0,
) -> List[float]:
    """
    Compute UV coordinates for mesh.

    Args:
        vertices: Vertex positions
        projection: UV projection type ('box', 'planar_xy', 'planar_xz', 'planar_yz')
        scale: UV scale factor

    Returns:
        UV coordinates (2 floats per vertex)
    """
    vertex_count = len(vertices) // 3
    uvs = []

    for i in range(vertex_count):
        x = vertices[i * 3]
        y = vertices[i * 3 + 1]
        z = vertices[i * 3 + 2]

        if projection == "planar_xy":
            u, v = x * scale, y * scale
        elif projection == "planar_xz":
            u, v = x * scale, z * scale
        elif projection == "planar_yz":
            u, v = y * scale, z * scale
        else:  # box projection
            # Choose projection based on dominant normal direction
            # Simple approximation: use largest absolute coordinate
            ax, ay, az = abs(x), abs(y), abs(z)
            if ax >= ay and ax >= az:
                u, v = y * scale, z * scale
            elif ay >= ax and ay >= az:
                u, v = x * scale, z * scale
            else:
                u, v = x * scale, y * scale

        uvs.extend([u, v])

    return uvs


def compute_tangents(
    vertices: List[float],
    normals: List[float],
    uvs: List[float],
    indices: List[int],
) -> List[float]:
    """
    Compute tangent vectors for normal mapping.

    Returns tangent vectors as 4 floats per vertex (xyz + handedness).
    """
    vertex_count = len(vertices) // 3

    # Initialize tangent accumulators
    tangents = [0.0] * (vertex_count * 3)
    bitangents = [0.0] * (vertex_count * 3)

    # Accumulate tangents from faces
    for i in range(0, len(indices), 3):
        i0, i1, i2 = indices[i], indices[i + 1], indices[i + 2]

        # Positions
        p0 = (vertices[i0 * 3], vertices[i0 * 3 + 1], vertices[i0 * 3 + 2])
        p1 = (vertices[i1 * 3], vertices[i1 * 3 + 1], vertices[i1 * 3 + 2])
        p2 = (vertices[i2 * 3], vertices[i2 * 3 + 1], vertices[i2 * 3 + 2])

        # UVs
        uv0 = (uvs[i0 * 2], uvs[i0 * 2 + 1])
        uv1 = (uvs[i1 * 2], uvs[i1 * 2 + 1])
        uv2 = (uvs[i2 * 2], uvs[i2 * 2 + 1])

        # Edges
        dp1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        dp2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])

        duv1 = (uv1[0] - uv0[0], uv1[1] - uv0[1])
        duv2 = (uv2[0] - uv0[0], uv2[1] - uv0[1])

        # Calculate tangent and bitangent
        denom = duv1[0] * duv2[1] - duv2[0] * duv1[1]
        if abs(denom) < EPSILON_GEOMETRY:
            continue

        r = 1.0 / denom

        tangent = (
            (duv2[1] * dp1[0] - duv1[1] * dp2[0]) * r,
            (duv2[1] * dp1[1] - duv1[1] * dp2[1]) * r,
            (duv2[1] * dp1[2] - duv1[1] * dp2[2]) * r,
        )

        bitangent = (
            (duv1[0] * dp2[0] - duv2[0] * dp1[0]) * r,
            (duv1[0] * dp2[1] - duv2[0] * dp1[1]) * r,
            (duv1[0] * dp2[2] - duv2[0] * dp1[2]) * r,
        )

        # Accumulate
        for idx in [i0, i1, i2]:
            tangents[idx * 3] += tangent[0]
            tangents[idx * 3 + 1] += tangent[1]
            tangents[idx * 3 + 2] += tangent[2]

            bitangents[idx * 3] += bitangent[0]
            bitangents[idx * 3 + 1] += bitangent[1]
            bitangents[idx * 3 + 2] += bitangent[2]

    # Orthonormalize and compute handedness
    result = []
    for i in range(vertex_count):
        n = (normals[i * 3], normals[i * 3 + 1], normals[i * 3 + 2])
        t = (tangents[i * 3], tangents[i * 3 + 1], tangents[i * 3 + 2])
        b = (bitangents[i * 3], bitangents[i * 3 + 1], bitangents[i * 3 + 2])

        # Gram-Schmidt orthogonalize
        dot_nt = n[0] * t[0] + n[1] * t[1] + n[2] * t[2]
        t_ortho = (
            t[0] - n[0] * dot_nt,
            t[1] - n[1] * dot_nt,
            t[2] - n[2] * dot_nt,
        )

        # Normalize
        length = math.sqrt(t_ortho[0] ** 2 + t_ortho[1] ** 2 + t_ortho[2] ** 2)
        if length > EPSILON_VECTOR:
            t_ortho = (t_ortho[0] / length, t_ortho[1] / length, t_ortho[2] / length)
        else:
            t_ortho = (1.0, 0.0, 0.0)

        # Calculate handedness
        cross = (
            n[1] * t_ortho[2] - n[2] * t_ortho[1],
            n[2] * t_ortho[0] - n[0] * t_ortho[2],
            n[0] * t_ortho[1] - n[1] * t_ortho[0],
        )
        handedness = 1.0 if (cross[0] * b[0] + cross[1] * b[1] + cross[2] * b[2]) >= 0 else -1.0

        result.extend([t_ortho[0], t_ortho[1], t_ortho[2], handedness])

    return result


def merge_meshes(meshes: List[MeshData]) -> MeshData:
    """Merge multiple meshes into a single mesh."""
    builder = MeshBuilder()

    for mesh in meshes:
        # Add vertices and track index offset
        offset = builder.vertex_count

        for i in range(mesh.vertex_count):
            x = mesh.vertices[i * 3]
            y = mesh.vertices[i * 3 + 1]
            z = mesh.vertices[i * 3 + 2]
            builder.add_vertex(x, y, z)

        # Add faces with offset
        for i in range(0, len(mesh.indices), 3):
            builder.add_triangle(
                mesh.indices[i] + offset,
                mesh.indices[i + 1] + offset,
                mesh.indices[i + 2] + offset,
            )

    return builder.build()


def transform_mesh(
    mesh: MeshData,
    translate: Tuple[float, float, float] = (0, 0, 0),
    scale: Tuple[float, float, float] = (1, 1, 1),
) -> MeshData:
    """Transform mesh vertices."""
    new_vertices = []

    for i in range(mesh.vertex_count):
        x = mesh.vertices[i * 3] * scale[0] + translate[0]
        y = mesh.vertices[i * 3 + 1] * scale[1] + translate[1]
        z = mesh.vertices[i * 3 + 2] * scale[2] + translate[2]
        new_vertices.extend([x, y, z])

    return MeshData(
        vertices=new_vertices,
        indices=mesh.indices.copy() if isinstance(mesh.indices, list) else list(mesh.indices),
        normals=mesh.normals.copy() if isinstance(mesh.normals, list) else list(mesh.normals),
        mesh_id=mesh.mesh_id,
    )
