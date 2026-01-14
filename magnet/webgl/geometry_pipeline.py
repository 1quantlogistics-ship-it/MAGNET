"""
webgl/geometry_pipeline.py - Hull tessellation pipeline v1.2

Module 58: WebGL 3D Visualization
ALPHA OWNS THIS FILE.

Provides tessellation of hull geometry to triangle meshes.

v1.2 Changes:
- Added EdgeType support for hard edge rendering
- Pass edge_type from section points to mesh builder
- Mark hard edges for split normal computation
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
from magnet.core.constants import EPSILON_VECTOR, EPSILON_MESH

if TYPE_CHECKING:
    from magnet.hull_gen.deck_generator import DeckGeometry
    from .mesh_builder import MeshBuilder

logger = logging.getLogger("webgl.geometry_pipeline")

# Import EdgeType for hard edge support
try:
    from magnet.hull_gen.geometry import EdgeType
except ImportError:
    from enum import Enum
    class EdgeType(Enum):
        SMOOTH = "smooth"
        HARD = "hard"
        CREASE = "crease"


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

    def tessellate_by_body(self) -> dict[str, MeshData]:
        """
        Tessellate authoritative hull geometry into one MeshData per body.

        This is the enum-free multi-body fix: we partition by geometric ownership
        (`HullSection.body_id`) and tessellate each body independently so the mesh
        generator never skins across bodies.
        """
        if self._hull_geom is None:
            raise ValueError("No hull geometry available for tessellation")

        sections = self._hull_geom.sections or []
        by_body: dict[str, list[HullSection]] = {}
        for s in sections:
            body_id = getattr(s, "body_id", "main") or "main"
            by_body.setdefault(str(body_id), []).append(s)

        # Deterministic ordering: sort bodies by id; sort sections by station within body
        out: dict[str, MeshData] = {}
        for body_id in sorted(by_body.keys()):
            s_list = sorted(by_body[body_id], key=lambda ss: ss.station)
            # Per-body tessellation MUST NOT replicate across ship centerline.
            # Each body already exists as its own geometry; we only mirror about
            # the body's own centerline as needed.
            mesh = self._tessellate_from_sections(s_list, replicate_ship_pair=False)
            mesh.mesh_id = mesh.mesh_id or f"hull_{body_id}"
            out[body_id] = mesh
        return out

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
    
    # =========================================================================
    # Phase 6: Enhanced tessellation with faceted panels and deck
    # =========================================================================
    
    def tessellate_with_options(
        self,
        sections: List[HullSection],
        faceted: bool = False,
        panel_edges_hard: bool = True,
        deck_geometry: Optional['DeckGeometry'] = None,
    ) -> MeshData:
        """
        Tessellate hull with Phase 6 options.
        
        Args:
            sections: Hull sections to tessellate
            faceted: If True, use flat panel tessellation (for aluminum hulls)
            panel_edges_hard: Whether to mark panel edges as hard in faceted mode
            deck_geometry: Optional deck surface to add to mesh
            
        Returns:
            Complete mesh with hull and optional deck
        """
        from .mesh_builder import MeshBuilder
        builder = MeshBuilder()
        
        if faceted:
            self._tessellate_faceted(sections, builder, panel_edges_hard)
        else:
            # Use standard smooth tessellation, then add to same builder
            mesh = self._tessellate_from_sections(sections)
            # Copy mesh data to builder
            for i in range(0, len(mesh.vertices), 3):
                if i + 2 < len(mesh.vertices):
                    builder.add_vertex(
                        mesh.vertices[i],
                        mesh.vertices[i + 1],
                        mesh.vertices[i + 2],
                    )
            for i in range(0, len(mesh.indices), 3):
                if i + 2 < len(mesh.indices):
                    builder.add_triangle(
                        mesh.indices[i],
                        mesh.indices[i + 1],
                        mesh.indices[i + 2],
                    )
            # Return early if no deck - we already have the mesh
            if deck_geometry is None:
                return mesh
            # Otherwise rebuild to add deck
            builder = MeshBuilder()
            for i in range(0, len(mesh.vertices), 3):
                if i + 2 < len(mesh.vertices):
                    builder.add_vertex(
                        mesh.vertices[i],
                        mesh.vertices[i + 1],
                        mesh.vertices[i + 2],
                    )
            for i in range(0, len(mesh.indices), 3):
                if i + 2 < len(mesh.indices):
                    builder.add_triangle(
                        mesh.indices[i],
                        mesh.indices[i + 1],
                        mesh.indices[i + 2],
                    )
        
        # Add deck surface if present
        if deck_geometry is not None and len(deck_geometry.vertices) > 0:
            self._add_deck_to_builder(builder, deck_geometry)
        
        return builder.build(compute_normals=True)
    
    def _tessellate_faceted(
        self,
        sections: List[HullSection],
        builder: 'MeshBuilder',
        panel_edges_hard: bool = True,
    ) -> None:
        """
        Tessellate hull with flat faceted panels.
        
        Phase 6: Each quad between sections becomes a flat panel with
        per-face normals. Appropriate for aluminum construction.
        
        In faceted mode:
        - Each quad is planar (flat panel)
        - Normals are face normals, not averaged vertex normals
        - Edges between panels are hard
        """
        if not sections or len(sections) < 2:
            return
        
        for i in range(len(sections) - 1):
            section_a = sections[i]
            section_b = sections[i + 1]
            
            points_a = section_a.points
            points_b = section_b.points
            
            min_points = min(len(points_a), len(points_b))
            if min_points < 2:
                continue
            
            for j in range(min_points - 1):
                # Get quad corners (port side)
                p0 = points_a[j].position
                p1 = points_a[j + 1].position
                p2 = points_b[j].position
                p3 = points_b[j + 1].position
                
                # Compute face normal for this quad
                face_normal = self._compute_quad_normal(p0, p1, p2, p3)
                
                # Add vertices with face normal (each quad gets own vertices)
                v0 = builder.add_vertex_with_normal(
                    p0.x, p0.y, p0.z,
                    face_normal[0], face_normal[1], face_normal[2],
                )
                v1 = builder.add_vertex_with_normal(
                    p1.x, p1.y, p1.z,
                    face_normal[0], face_normal[1], face_normal[2],
                )
                v2 = builder.add_vertex_with_normal(
                    p2.x, p2.y, p2.z,
                    face_normal[0], face_normal[1], face_normal[2],
                )
                v3 = builder.add_vertex_with_normal(
                    p3.x, p3.y, p3.z,
                    face_normal[0], face_normal[1], face_normal[2],
                )
                
                # Add triangles (port side winding)
                builder.add_triangle(v0, v2, v1)
                builder.add_triangle(v1, v2, v3)
                
                # Mark edges as hard if requested
                if panel_edges_hard:
                    builder.mark_hard_edge(v0, v1)
                    builder.mark_hard_edge(v2, v3)
                    builder.mark_hard_edge(v0, v2)
                    builder.mark_hard_edge(v1, v3)
                
                # Mirror for starboard side
                if p0.y > 0.001:  # Not centerline
                    s_v0 = builder.add_vertex_with_normal(
                        p0.x, -p0.y, p0.z,
                        face_normal[0], -face_normal[1], face_normal[2],
                    )
                    s_v1 = builder.add_vertex_with_normal(
                        p1.x, -p1.y, p1.z,
                        face_normal[0], -face_normal[1], face_normal[2],
                    )
                    s_v2 = builder.add_vertex_with_normal(
                        p2.x, -p2.y, p2.z,
                        face_normal[0], -face_normal[1], face_normal[2],
                    )
                    s_v3 = builder.add_vertex_with_normal(
                        p3.x, -p3.y, p3.z,
                        face_normal[0], -face_normal[1], face_normal[2],
                    )
                    
                    # Reversed winding for starboard
                    builder.add_triangle(s_v0, s_v1, s_v2)
                    builder.add_triangle(s_v1, s_v3, s_v2)
                    
                    if panel_edges_hard:
                        builder.mark_hard_edge(s_v0, s_v1)
                        builder.mark_hard_edge(s_v2, s_v3)
                        builder.mark_hard_edge(s_v0, s_v2)
                        builder.mark_hard_edge(s_v1, s_v3)
    
    def _compute_quad_normal(
        self,
        p0: Point3D,
        p1: Point3D,
        p2: Point3D,
        p3: Point3D,
    ) -> Tuple[float, float, float]:
        """
        Compute normal for a quad (average of two triangle normals).
        
        Triangle 1: p0 -> p2 -> p1
        Triangle 2: p1 -> p2 -> p3
        """
        # Triangle 1 edges
        e1 = (p2.x - p0.x, p2.y - p0.y, p2.z - p0.z)
        e2 = (p1.x - p0.x, p1.y - p0.y, p1.z - p0.z)
        n1 = self._cross(e1, e2)
        
        # Triangle 2 edges
        e3 = (p2.x - p1.x, p2.y - p1.y, p2.z - p1.z)
        e4 = (p3.x - p1.x, p3.y - p1.y, p3.z - p1.z)
        n2 = self._cross(e3, e4)
        
        # Average and normalize
        nx = n1[0] + n2[0]
        ny = n1[1] + n2[1]
        nz = n1[2] + n2[2]
        
        length = math.sqrt(nx*nx + ny*ny + nz*nz)
        if length > EPSILON_VECTOR:
            return (nx/length, ny/length, nz/length)
        return (0.0, 0.0, 1.0)
    
    def _cross(
        self,
        a: Tuple[float, float, float],
        b: Tuple[float, float, float],
    ) -> Tuple[float, float, float]:
        """Cross product of two 3D vectors."""
        return (
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        )
    
    def _add_deck_to_builder(
        self,
        builder: 'MeshBuilder',
        deck: 'DeckGeometry',
    ) -> None:
        """
        Add deck surface to mesh builder.
        
        Phase 6: Deck vertices and triangles are added to the existing
        hull mesh to create a closed volume.
        """
        # Map deck vertex indices to builder indices
        vertex_map = {}
        
        for i, pt in enumerate(deck.vertices):
            normal = deck.normals[i] if i < len(deck.normals) else (0.0, 0.0, 1.0)
            v_idx = builder.add_vertex_with_normal(
                pt.x, pt.y, pt.z,
                normal[0], normal[1], normal[2],
            )
            vertex_map[i] = v_idx
        
        # Add triangles
        for tri in deck.triangles:
            if tri[0] in vertex_map and tri[1] in vertex_map and tri[2] in vertex_map:
                builder.add_triangle(
                    vertex_map[tri[0]],
                    vertex_map[tri[1]],
                    vertex_map[tri[2]],
                )

    def _tessellate_from_sections(self, sections: List[HullSection], replicate_ship_pair: bool = True) -> MeshData:
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

        # Densify along length to reduce visible "breaks" when only a few sparse
        # sections exist (e.g., bow/mid/stern). This is visualization-quality glue.
        sections = self._densify_sections_linear(sections, target_count=self._config.sections_count)

        # Detect whether sections include ship-centerline vertices (monohull-style).
        # If not, treat as multihull-style sections that must be mirrored about a
        # demihull centerline to produce inboard + outboard surfaces.
        eps = 0.001
        has_ship_centerline = False
        for s in sections:
            for p in s.points:
                # Access position.y for SectionPoint objects
                y_val = p.position.y if hasattr(p, 'position') else (p.y if hasattr(p, 'y') else 0)
                if abs(y_val) <= eps:
                    has_ship_centerline = True
                    break
            if has_ship_centerline:
                break

        expected_vert_multiplier = 2  # port + starboard

        if has_ship_centerline:
            # -----------------------------------------------------------------
            # MONOHULL MODE
            # -----------------------------------------------------------------
            # Build SEPARATE vertex grids for port and starboard
            # Citation: 67.1.md - "Separate arrays for port (y >= 0) and starboard (y <= 0)"
            port_indices: List[List[int]] = []
            starboard_indices: List[List[int]] = []

            for section in sections:
                port_section = []
                starboard_section = []

                for i, point in enumerate(section.points):
                    # v1.2: Get edge type from section point (defaults to SMOOTH)
                    edge_type = getattr(point, 'edge_type', None) or EdgeType.SMOOTH
                    
                    # Handle both Point3D (x, y, z) and SectionPoint (position.x, etc.)
                    if hasattr(point, 'position'):
                        px, py, pz = point.position.x, point.position.y, point.position.z
                    else:
                        px, py, pz = point.x, point.y, point.z
                    
                    # Port side (original points, y >= 0)
                    idx_port = builder.add_vertex(px, py, pz, edge_type=edge_type)
                    port_section.append(idx_port)

                    # Starboard side (mirrored, y <= 0)
                    if abs(py) > eps:
                        idx_starboard = builder.add_vertex(px, -py, pz, edge_type=edge_type)
                    else:
                        # Centerline point - use same vertex for both sides
                        # Citation: 67.1.md - "prevents gaps at keel"
                        idx_starboard = idx_port
                    starboard_section.append(idx_starboard)
                    
                    # v1.2: Mark hard edges along section curve
                    if edge_type == EdgeType.HARD and i > 0:
                        # Mark edge to previous point as hard
                        builder.mark_hard_edge(port_section[-2], port_section[-1])
                        if starboard_section[-2] != starboard_section[-1]:  # Not centerline
                            builder.mark_hard_edge(starboard_section[-2], starboard_section[-1])

                port_indices.append(port_section)
                starboard_indices.append(starboard_section)

            # Generate faces for PORT side
            _triangulate_hull_side(builder, port_indices, reverse_winding=False)

            # Generate faces for STARBOARD side (reverse winding for correct normals)
            # Citation: 67.1.md Winding Direction Rationale table
            _triangulate_hull_side(builder, starboard_indices, reverse_winding=True)

            # -----------------------------------------------------------------
            # 67.7 Hull Form UX: Add end caps (bow/stern) so hull is closed.
            # -----------------------------------------------------------------
            if port_indices and starboard_indices:
                # Stern cap (first section)
                _triangulate_end_cap(builder, port_indices[0], starboard_indices[0], reverse_winding=False)
                # Bow cap (last section)
                _triangulate_end_cap(builder, port_indices[-1], starboard_indices[-1], reverse_winding=True)

        else:
            # -----------------------------------------------------------------
            # MULTIHULL MODE (catamaran-style sections)
            #
            # Sections are offset from ship centerline and contain no shared CL
            # vertices. We build 4 surface strips:
            # - Port outboard (+Y normals)
            # - Port inboard (-Y normals), mirrored about demihull centerline
            # - Starboard outboard (-Y normals), mirrored about ship centerline
            # - Starboard inboard (+Y normals), mirrored about demihull centerline
            #
            # End caps are added per-demihull (no bridging across ship centerline).
            # -----------------------------------------------------------------
            expected_vert_multiplier = 4 if replicate_ship_pair else 2

            port_outboard: List[List[int]] = []
            port_inboard: List[List[int]] = []
            stb_outboard: List[List[int]] = []
            stb_inboard: List[List[int]] = []

            for section in sections:
                if not section.points:
                    port_outboard.append([])
                    port_inboard.append([])
                    stb_outboard.append([])
                    stb_inboard.append([])
                    continue

                # Demihull centerline inferred from first point (keel point).
                # Support both Point3D-style points and SectionPoint-style points.
                p0 = section.points[0]
                if hasattr(p0, "position"):
                    y0 = p0.position.y
                else:
                    y0 = p0.y

                po = []
                pi = []
                so = []
                si = []

                for i, point in enumerate(section.points):
                    # v1.2: Get edge type from section point (defaults to SMOOTH)
                    edge_type = getattr(point, 'edge_type', None) or EdgeType.SMOOTH
                    
                    if hasattr(point, "position"):
                        px, py, pz = point.position.x, point.position.y, point.position.z
                    else:
                        px, py, pz = point.x, point.y, point.z

                    # Outboard surface for THIS body (as-provided)
                    idx_po = builder.add_vertex(px, py, pz, edge_type=edge_type)
                    po.append(idx_po)

                    if replicate_ship_pair:
                        # Legacy: replicate to the other demihull about ship centerline (y=0)
                        idx_so = builder.add_vertex(px, -py, pz, edge_type=edge_type)
                        so.append(idx_so)

                    # Inboard surface: mirror about the body's own centerline y=y0
                    y_pi = (2.0 * y0) - py
                    if abs(y_pi - py) <= eps:
                        idx_pi = idx_po  # shared centerline vertex
                    else:
                        idx_pi = builder.add_vertex(px, y_pi, pz, edge_type=edge_type)
                    pi.append(idx_pi)

                    if replicate_ship_pair:
                        # Legacy: replicate inboard to other demihull about ship centerline
                        y_si = -y_pi
                        if abs(y_si - (-py)) <= eps:
                            idx_si = idx_so  # shared centerline vertex for replicated hull
                        else:
                            idx_si = builder.add_vertex(px, y_si, pz, edge_type=edge_type)
                        si.append(idx_si)
                    
                    # v1.2: Mark hard edges along section curve
                    if edge_type == EdgeType.HARD and i > 0:
                        builder.mark_hard_edge(po[-2], po[-1])
                        if replicate_ship_pair:
                            builder.mark_hard_edge(so[-2], so[-1])
                            if si[-2] != si[-1]:
                                builder.mark_hard_edge(si[-2], si[-1])
                        if pi[-2] != pi[-1]:
                            builder.mark_hard_edge(pi[-2], pi[-1])

                port_outboard.append(po)
                port_inboard.append(pi)
                if replicate_ship_pair:
                    stb_outboard.append(so)
                    stb_inboard.append(si)

            # Side surfaces
            _triangulate_hull_side(builder, port_outboard, reverse_winding=False)   # +Y normals
            _triangulate_hull_side(builder, port_inboard, reverse_winding=True)    # -Y normals
            if replicate_ship_pair:
                _triangulate_hull_side(builder, stb_outboard, reverse_winding=True)    # -Y normals
                _triangulate_hull_side(builder, stb_inboard, reverse_winding=False)    # +Y normals

            # End caps per-demihull (no bridging wall between hulls)
            if port_outboard and port_inboard:
                # Stern (first section)
                _triangulate_end_cap(builder, port_outboard[0], port_inboard[0], reverse_winding=False)
                if replicate_ship_pair:
                    _triangulate_end_cap(builder, stb_inboard[0], stb_outboard[0], reverse_winding=False)
                # Bow (last section)
                _triangulate_end_cap(builder, port_outboard[-1], port_inboard[-1], reverse_winding=True)
                if replicate_ship_pair:
                    _triangulate_end_cap(builder, stb_inboard[-1], stb_outboard[-1], reverse_winding=True)

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
        expected_verts = total_section_points * expected_vert_multiplier
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

    def _densify_sections_linear(self, sections: List[HullSection], target_count: int) -> List[HullSection]:
        """
        Insert intermediate sections by linear interpolation to reach target_count.

        Uses COSINE SPACING (denser at bow/transom, sparser amidships) per
        MAGNET_Rendering_Quality_And_Performance.md §1B:
            station_t = 0.5 * (1 - cos(π * t))
        This gives 2-3x density at ends without computing curvature.

        Preserves point correspondence by interpolating point i -> point i, which is
        the best we can do without a full curve parameterization.
        """
        import math

        try:
            target_count = int(target_count or 0)
        except Exception:
            target_count = 0
        if target_count <= 0:
            return sections

        base = [s for s in (sections or []) if getattr(s, "points", None)]
        if len(base) < 2 or len(base) >= target_count:
            return sections

        base = sorted(base, key=lambda s: float(getattr(s, "station", 0.0) or 0.0))
        total_needed = target_count - len(base)
        gaps = len(base) - 1
        if total_needed <= 0 or gaps <= 0:
            return base

        # Cosine spacing: allocate more inserts to gaps near bow (station~0) and transom (station~1)
        # Gap i spans from base[i].station to base[i+1].station
        # Weight each gap by how close it is to the ends (cosine distribution)
        gap_weights = []
        for gi in range(gaps):
            s0 = float(base[gi].station)
            s1 = float(base[gi + 1].station)
            mid = (s0 + s1) / 2.0
            # Cosine weight: higher at ends (mid near 0 or 1), lower amidships (mid near 0.5)
            # Using 1 + cos(2π * mid) which peaks at 0 and 1, troughs at 0.5
            weight = 1.0 + math.cos(2.0 * math.pi * mid)
            gap_weights.append(max(0.1, weight))  # floor to avoid zero

        total_weight = sum(gap_weights)
        per_gap = [0] * gaps
        # Distribute inserts proportionally to weights
        for gi in range(gaps):
            per_gap[gi] = int(round(total_needed * gap_weights[gi] / total_weight))

        # Adjust for rounding errors
        diff = total_needed - sum(per_gap)
        for i in range(abs(diff)):
            idx = i % gaps
            per_gap[idx] += 1 if diff > 0 else -1

        def _pos(p):
            return p.position if hasattr(p, "position") else p

        def _edge(p):
            return getattr(p, "edge_type", None)

        out: List[HullSection] = []
        for gi in range(gaps):
            a = base[gi]
            b = base[gi + 1]
            out.append(a)

            n_insert = per_gap[gi]
            if n_insert <= 0:
                continue

            a_pts = list(a.points)
            b_pts = list(b.points)
            n_pts = min(len(a_pts), len(b_pts))
            if n_pts < 2:
                continue

            for k in range(1, n_insert + 1):
                t = k / (n_insert + 1)
                station = (1 - t) * float(a.station) + t * float(b.station)

                new_points = []
                for pi in range(n_pts):
                    pa = _pos(a_pts[pi])
                    pb = _pos(b_pts[pi])
                    # IMPORTANT: X must be interpolated in meters (world coordinates), not the
                    # normalized station ratio. Using `station` here collapses intermediate
                    # sections near x≈0..1 which creates diagonal "wings"/folded panels.
                    x = (1 - t) * float(pa.x) + t * float(pb.x)
                    y = (1 - t) * float(pa.y) + t * float(pb.y)
                    z = (1 - t) * float(pa.z) + t * float(pb.z)

                    ea = _edge(a_pts[pi])
                    eb = _edge(b_pts[pi])
                    edge_type = ea or eb
                    try:
                        if (getattr(ea, "value", "") in ("hard", "crease")) or (getattr(eb, "value", "") in ("hard", "crease")):
                            edge_type = ea if getattr(ea, "value", "") in ("hard", "crease") else eb
                    except Exception:
                        pass

                    # Avoid top-level import cycle by importing here.
                    from magnet.webgl.interfaces import SectionVertex, Point3D as InterfacePoint3D
                    if edge_type is not None:
                        new_points.append(SectionVertex(position=InterfacePoint3D(x=x, y=y, z=z), edge_type=edge_type))
                    else:
                        new_points.append(InterfacePoint3D(x=x, y=y, z=z))

                out.append(HullSection(station=station, points=new_points, body_id=getattr(a, "body_id", "main")))

        out.append(base[-1])
        return out

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


def _section_has_centerline(port_section: List[int], starboard_section: List[int]) -> bool:
    """Detect whether a section includes any shared centerline vertices."""
    n = min(len(port_section), len(starboard_section))
    for i in range(n):
        if port_section[i] == starboard_section[i]:
            return True
    return False


def _triangulate_end_cap(
    builder: 'MeshBuilder',
    port_section: List[int],
    starboard_section: List[int],
    reverse_winding: bool = False,
) -> None:
    """
    Triangulate an end-cap surface at a single section (x = constant).

    Creates triangles bridging port and starboard section curves.
    Uses a simple strip triangulation; skips degenerate triangles created by
    shared centerline vertices.
    """
    n = min(len(port_section), len(starboard_section))
    if n < 2:
        return

    def _add(a: int, b: int, c: int):
        if len({a, b, c}) == 3:
            builder.add_triangle(a, b, c)

    # Visualization-only:
    # Sections in MAGNET are OPEN curves (keel→deck). A full end-cap strip at the *bow* creates a
    # large "wing/plate" across the open sheer/deck edge which reads as a geometric artifact.
    #
    # However, the *stern* end-cap is the transom closure and should remain fully capped.
    #
    # Convention in this module:
    # - reverse_winding=True  => bow cap
    # - reverse_winding=False => stern cap
    try:
        verts = getattr(builder, "_vertices", None)
    except Exception:
        verts = None

    def _z_of(v_idx: int) -> float:
        if not isinstance(verts, list) or len(verts) < (v_idx * 3 + 3):
            return float("inf")
        return float(verts[v_idx * 3 + 2])

    # Bathtub closure (watertight bottom+sides, open top):
    #
    # End-capping an OPEN keel→sheer curve by bridging port→starboard directly creates
    # a large diagonal plate across the open deck edge (the "wing" artifact).
    #
    # Instead, build the cap as TWO strips that triangulate to the CENTERLINE:
    #   port → centerline, then centerline → starboard.
    #
    # This preserves the open top while creating a clean end wall.
    #
    # NOTE: We do NOT need any new design primitives for this; it's purely a tessellation fix.
    if not isinstance(verts, list):
        # No coordinate access; fall back to legacy behavior (should not happen).
        for j in range(n - 1):
            p0 = port_section[j]
            p1 = port_section[j + 1]
            s0 = starboard_section[j]
            s1 = starboard_section[j + 1]
            if reverse_winding:
                _add(p0, s1, p1)
                _add(p0, s0, s1)
            else:
                _add(p0, p1, s1)
                _add(p0, s1, s0)
        return

    def _xyz(v_idx: int) -> tuple[float, float, float]:
        return (
            float(verts[v_idx * 3 + 0]),
            float(verts[v_idx * 3 + 1]),
            float(verts[v_idx * 3 + 2]),
        )

    # Build centerline vertices aligned to the section curve (keel→sheer).
    # If the section already has a centerline vertex at an index (port==starboard),
    # reuse it to avoid degenerates and preserve watertightness at the keel.
    center: List[int] = []
    for j in range(n):
        pj = port_section[j]
        sj = starboard_section[j]
        if pj == sj:
            center.append(pj)
            continue
        x_p, _, z_p = _xyz(pj)
        x_s, _, z_s = _xyz(sj)
        x = 0.5 * (x_p + x_s)
        z = 0.5 * (z_p + z_s)
        center.append(builder.add_vertex(x, 0.0, z))

    # Strip 1: port -> center
    for j in range(n - 1):
        p0 = port_section[j]
        p1 = port_section[j + 1]
        c0 = center[j]
        c1 = center[j + 1]
        if reverse_winding:
            _add(p0, c1, p1)
            _add(p0, c0, c1)
        else:
            _add(p0, p1, c1)
            _add(p0, c1, c0)

    # Strip 2: center -> starboard
    for j in range(n - 1):
        c0 = center[j]
        c1 = center[j + 1]
        s0 = starboard_section[j]
        s1 = starboard_section[j + 1]
        if reverse_winding:
            _add(c0, s1, c1)
            _add(c0, s0, s1)
        else:
            _add(c0, c1, s1)
            _add(c0, s1, s0)


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


def _count_degenerate_triangles(mesh: MeshData, area_threshold: float = EPSILON_MESH) -> int:
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
