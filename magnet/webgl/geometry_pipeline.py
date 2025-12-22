"""
webgl/geometry_pipeline.py - Hull tessellation pipeline v1.1

Module 58: WebGL 3D Visualization
ALPHA OWNS THIS FILE.

Provides tessellation of hull geometry to triangle meshes.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List, Tuple
from dataclasses import dataclass
import math
import logging

from .schema import MeshData, LODLevel
from .interfaces import (
    GeometryInputProvider,
    HullGeometryData,
    HullSection,
    Point3D,
)
from .config import TessellationConfig, LOD_CONFIGS

if TYPE_CHECKING:
    pass

logger = logging.getLogger("webgl.geometry_pipeline")


# Re-export TessellationConfig
__all__ = ["HullGeometryPipeline", "TessellationConfig"]


class HullGeometryPipeline:
    """
    Pipeline for tessellating hull geometry to triangle meshes.

    Can work from either:
    - HullGeometryData (authoritative GRM)
    - GeometryInputProvider (parametric approximation)
    """

    def __init__(
        self,
        hull_geom: Optional[HullGeometryData] = None,
        inputs: Optional[GeometryInputProvider] = None,
        config: Optional[TessellationConfig] = None,
    ):
        self._hull_geom = hull_geom
        self._inputs = inputs
        self._config = config or TessellationConfig()

        if hull_geom is None and inputs is None:
            raise ValueError("Must provide either hull_geom or inputs")

    @classmethod
    def from_inputs(
        cls,
        inputs: GeometryInputProvider,
        config: Optional[TessellationConfig] = None,
    ) -> "HullGeometryPipeline":
        """Create pipeline from input parameters (for visual-only mode)."""
        return cls(hull_geom=None, inputs=inputs, config=config)

    def tessellate(self) -> MeshData:
        """
        Tessellate authoritative hull geometry to mesh.

        Requires hull_geom to be set.
        """
        if self._hull_geom is None:
            raise ValueError("No hull geometry available for tessellation")

        return self._tessellate_from_sections(self._hull_geom.sections)

    def tessellate_parametric(self) -> MeshData:
        """
        Generate parametric hull mesh (visual-only approximation).

        Uses input parameters to generate approximate hull form.
        """
        if self._inputs is None:
            raise ValueError("No inputs available for parametric tessellation")

        # Generate sections parametrically
        sections = self._generate_parametric_sections()
        return self._tessellate_from_sections(sections)

    def _tessellate_from_sections(self, sections: List[HullSection]) -> MeshData:
        """
        Tessellate from hull sections.

        Critical invariant: Within a section, adjacency must be monotonic
        along the section curve (keel→deck), not alternating across Y.

        Fix for topology corruption: Uses separate port/starboard vertex grids
        instead of interleaving mirrored vertices into the same array.
        Citation: 67.1.md Phase 1 - Geometry Pipeline Fix
        """
        from .mesh_builder import MeshBuilder

        builder = MeshBuilder()

        if not sections:
            logger.warning("No sections to tessellate")
            return builder.build()

        # Build SEPARATE vertex grids for port and starboard
        # Citation: 67.1.md - "Separate arrays for port (y >= 0) and starboard (y <= 0)"
        port_indices: List[List[int]] = []
        starboard_indices: List[List[int]] = []

        for section in sections:
            port_section = []
            starboard_section = []

            for point in section.points:
                # Port side (original points, y >= 0)
                idx_port = builder.add_vertex(point.x, point.y, point.z)
                port_section.append(idx_port)

                # Starboard side (mirrored, y <= 0)
                if abs(point.y) > 0.001:
                    idx_starboard = builder.add_vertex(point.x, -point.y, point.z)
                else:
                    # Centerline point - use same vertex for both sides
                    # Citation: 67.1.md - "prevents gaps at keel"
                    idx_starboard = idx_port
                starboard_section.append(idx_starboard)

            port_indices.append(port_section)
            starboard_indices.append(starboard_section)

        # Generate faces for PORT side
        _triangulate_hull_side(builder, port_indices, reverse_winding=False)

        # Generate faces for STARBOARD side (reverse winding for correct normals)
        # Citation: 67.1.md Winding Direction Rationale table
        _triangulate_hull_side(builder, starboard_indices, reverse_winding=True)

        mesh = builder.build()

        # Topology validation - Citation: 67.1.md Phase 5.2
        if mesh.vertex_count == 0 or mesh.face_count == 0:
            logger.error("Empty mesh generated!")

        # NaN check
        if any(math.isnan(v) for v in mesh.vertices):
            logger.error("NaN values in vertex data!")

        # Vertex count sanity - use SUM of per-section point counts
        # Citation: 67.1.md - "sections may vary in point count near bow/stern"
        total_section_points = sum(len(s.points) for s in sections)
        expected_verts = total_section_points * 2  # port + starboard
        if mesh.vertex_count > expected_verts * 1.5:
            logger.warning(
                f"Vertex count {mesh.vertex_count} higher than expected {expected_verts}"
            )

        # Degenerate triangle check (PRIMARY validation)
        # Citation: 67.1.md Phase 5.1 - area-based detection
        degen_count = _count_degenerate_triangles(mesh)
        if degen_count > 0:
            logger.error(f"Degenerate triangles detected: {degen_count}")

        logger.debug(
            f"Tessellated {len(sections)} sections into "
            f"{mesh.vertex_count} vertices, {mesh.face_count} faces"
        )

        return mesh

    def _generate_parametric_sections(self) -> List[HullSection]:
        """Generate hull sections from parametric inputs."""
        sections = []

        loa = self._inputs.loa
        lwl = self._inputs.lwl
        beam = self._inputs.beam
        draft = self._inputs.draft
        depth = self._inputs.depth
        cb = self._inputs.cb
        cp = self._inputs.cp
        cwp = self._inputs.cwp
        deadrise = self._inputs.deadrise_deg
        transom_ratio = self._inputs.transom_width_ratio

        n_sections = self._config.sections_count
        n_points = self._config.circumferential_points

        # Generate sections from stern (x=0) to bow (x=loa)
        for i in range(n_sections + 1):
            x_ratio = i / n_sections
            x = x_ratio * loa

            # Determine section shape based on position
            section_points = self._generate_section_curve(
                x=x,
                x_ratio=x_ratio,
                loa=loa,
                lwl=lwl,
                beam=beam,
                draft=draft,
                depth=depth,
                cb=cb,
                cp=cp,
                cwp=cwp,
                deadrise_deg=deadrise,
                transom_ratio=transom_ratio,
                n_points=n_points,
            )

            sections.append(HullSection(
                station=x,
                points=section_points,
                is_closed=False,
            ))

        return sections

    def _generate_section_curve(
        self,
        x: float,
        x_ratio: float,
        loa: float,
        lwl: float,
        beam: float,
        draft: float,
        depth: float,
        cb: float,
        cp: float,
        cwp: float,
        deadrise_deg: float,
        transom_ratio: float,
        n_points: int,
    ) -> List[Point3D]:
        """Generate points for a hull section at station x."""
        points = []

        # Calculate local beam based on waterplane coefficient
        # Simple approximation: beam varies along length
        # Peak beam typically at ~0.5-0.6 LOA for monohull

        # Position factor for beam distribution
        if x_ratio < 0.5:
            # Stern half - starts at transom width, grows to max beam
            beam_factor = transom_ratio + (1 - transom_ratio) * (x_ratio * 2) ** 0.8
        else:
            # Bow half - max beam to fine entry
            bow_ratio = (x_ratio - 0.5) * 2
            beam_factor = 1.0 - (1 - 0.1) * bow_ratio ** 2

        local_beam = beam * beam_factor

        # Calculate local draft
        # Draft varies less along length for displacement hulls
        if x_ratio > 0.9:
            # Bow rises up
            draft_factor = 1.0 - (x_ratio - 0.9) * 5
        elif x_ratio < 0.1:
            # Transom may be above waterline
            draft_factor = transom_ratio + (1 - transom_ratio) * (x_ratio * 10)
        else:
            draft_factor = 1.0

        local_draft = draft * max(0.1, draft_factor)

        # Deadrise angle effect
        deadrise_rad = math.radians(deadrise_deg)

        # Generate section curve from keel to sheer
        for j in range(n_points + 1):
            z_ratio = j / n_points  # 0 at keel, 1 at sheer

            # Calculate Y (half-breadth) based on section shape
            if z_ratio < 0.5:
                # Below waterline - use deadrise and block coefficient
                z_local = z_ratio * 2  # 0 to 1 in lower half
                y_factor = z_local ** (1.0 / max(0.3, cb))

                # Apply deadrise at bottom
                deadrise_factor = 1 - (1 - z_local) * math.tan(deadrise_rad) / 2

                y = (local_beam / 2) * y_factor * deadrise_factor

                z = -local_draft + z_ratio * (draft + depth)
            else:
                # Above waterline - flare out to sheer
                z_local = (z_ratio - 0.5) * 2  # 0 to 1 in upper half
                y = (local_beam / 2) * (1 + 0.1 * z_local)  # Slight flare

                z = -local_draft + z_ratio * (draft + depth)

            # Ensure we stay within bounds
            y = max(0, min(local_beam / 2, y))

            points.append(Point3D(x=x, y=y, z=z))

        return points


# =============================================================================
# TESSELLATION HELPERS
# Citation: 67.1.md Phase 1 - Helper function for hull side triangulation
# =============================================================================

def _triangulate_hull_side(
    builder: 'MeshBuilder',
    vertex_indices: List[List[int]],
    reverse_winding: bool = False
) -> None:
    """
    Triangulate one side of the hull.

    Citation: 67.1.md Winding Direction Rationale
    - Port (reverse_winding=False): (v0, v2, v1), (v1, v2, v3) → normals +Y
    - Starboard (reverse_winding=True): (v0, v1, v2), (v1, v3, v2) → normals -Y

    Non-goal: watertight hull caps (caps deferred)
    """
    for i in range(len(vertex_indices) - 1):
        curr_section = vertex_indices[i]
        next_section = vertex_indices[i + 1]

        n_curr = len(curr_section)
        n_next = len(next_section)

        if n_curr == 0 or n_next == 0:
            continue

        # Section point count mismatch warning
        # Citation: feedback - "can create gaps or sliver triangles"
        if n_curr != n_next:
            logger.debug(
                f"Section point count mismatch at section {i}: "
                f"curr={n_curr}, next={n_next}"
            )

        n_points = min(n_curr, n_next)

        for j in range(n_points - 1):
            v0 = curr_section[j]
            v1 = curr_section[j + 1]
            v2 = next_section[j]
            v3 = next_section[j + 1]

            if reverse_winding:
                # Starboard: flip triangle winding for outward normals
                builder.add_triangle(v0, v1, v2)
                builder.add_triangle(v1, v3, v2)
            else:
                # Port: normal winding
                builder.add_triangle(v0, v2, v1)
                builder.add_triangle(v1, v2, v3)


def _compute_triangle_area(v0: int, v1: int, v2: int, vertices: List[float]) -> float:
    """
    Compute triangle area using cross product magnitude.

    Citation: 67.1.md Phase 5.1 - Area-based degenerate detection
    """
    # Get vertex positions (vertices is flat array: x0,y0,z0,x1,y1,z1,...)
    p0 = (vertices[v0 * 3], vertices[v0 * 3 + 1], vertices[v0 * 3 + 2])
    p1 = (vertices[v1 * 3], vertices[v1 * 3 + 1], vertices[v1 * 3 + 2])
    p2 = (vertices[v2 * 3], vertices[v2 * 3 + 1], vertices[v2 * 3 + 2])

    # Edge vectors
    e1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
    e2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])

    # Cross product
    cx = e1[1] * e2[2] - e1[2] * e2[1]
    cy = e1[2] * e2[0] - e1[0] * e2[2]
    cz = e1[0] * e2[1] - e1[1] * e2[0]

    # Area = 0.5 * |cross product|
    return 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)


def _count_degenerate_triangles(mesh: MeshData, area_threshold: float = 1e-6) -> int:
    """
    Count triangles with near-zero area (the actual failure mode).

    Citation: 67.1.md Phase 5.1
    "detects near-zero area triangles that the index-duplicate check misses"
    """
    degenerate_count = 0
    indices = mesh.indices
    vertices = mesh.vertices

    for i in range(0, len(indices), 3):
        v0, v1, v2 = indices[i], indices[i + 1], indices[i + 2]

        # Check duplicate indices (trivial degenerates)
        if v0 == v1 or v1 == v2 or v0 == v2:
            degenerate_count += 1
            continue

        # Check near-zero area (the bug's actual failure mode)
        area = _compute_triangle_area(v0, v1, v2, vertices)
        if area < area_threshold:
            degenerate_count += 1

    return degenerate_count


# =============================================================================
# PARAMETRIC HULL FORMS
# =============================================================================

def generate_series_60_section(
    x_ratio: float,
    beam: float,
    draft: float,
    cb: float,
) -> List[Tuple[float, float]]:
    """
    Generate Series 60 hull section offsets.

    Returns list of (y, z) coordinates for half-section.
    """
    # Simplified Series 60 section shape
    n_points = 10
    offsets = []

    # Section area coefficient varies along length
    if x_ratio < 0.5:
        # Forward sections are finer
        cm = cb + (1 - cb) * (1 - x_ratio * 2) ** 2
    else:
        # Aft sections fuller
        cm = cb + (1 - cb) * ((x_ratio - 0.5) * 2) ** 1.5

    for i in range(n_points + 1):
        z_ratio = i / n_points
        z = -draft * (1 - z_ratio)

        # Y follows power curve based on midship coefficient
        y = (beam / 2) * z_ratio ** (1.0 / max(0.3, cm))

        offsets.append((y, z))

    return offsets


def generate_chine_hull_section(
    x_ratio: float,
    beam: float,
    draft: float,
    chine_height_ratio: float = 0.3,
    deadrise_deg: float = 15.0,
) -> List[Tuple[float, float]]:
    """
    Generate hard-chine hull section.

    Returns list of (y, z) coordinates for half-section.
    """
    offsets = []

    deadrise_rad = math.radians(deadrise_deg)

    # Keel point
    offsets.append((0, -draft))

    # Bottom panel - follows deadrise
    chine_z = -draft * (1 - chine_height_ratio)
    chine_y = abs(chine_z + draft) / math.tan(deadrise_rad) if deadrise_rad > 0.01 else beam / 4

    offsets.append((chine_y, chine_z))

    # Topsides - straight up from chine
    offsets.append((beam / 2, 0))

    return offsets
