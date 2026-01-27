"""
hull_gen/deck_generator.py - Simple deck surface generator.

BRAVO OWNS THIS FILE.

Phase 6: Generates a flat or cambered deck surface from hull sheer line
to close the hull mesh. Complex features (cockpits, hatches) deferred
to post-scantlings phase.
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from magnet.hull_gen.geometry import Point3D, HullSection
from magnet.hull_gen.parameters import DeckConfig, HullDefinition


@dataclass
class DeckGeometry:
    """Generated deck surface geometry."""
    
    vertices: List[Point3D] = field(default_factory=list)
    """Deck surface vertices."""
    
    triangles: List[Tuple[int, int, int]] = field(default_factory=list)
    """Triangle indices into vertices list."""
    
    edge_points: List[Point3D] = field(default_factory=list)
    """Deck edge (sheer line) points."""
    
    centerline_points: List[Point3D] = field(default_factory=list)
    """Centerline curve points."""
    
    normals: List[Tuple[float, float, float]] = field(default_factory=list)
    """Vertex normals (pointing up)."""


class DeckGenerator:
    """
    Generates simple deck surface from hull sections.
    
    The deck spans from the sheer line (deck edge of each section)
    to the centerline, with optional camber (crown).
    
    Phase 6 scope:
    - Flat deck (close mesh)
    - Parabolic camber
    - Circular arc camber
    - Sheer adjustment (bow/stern height variation)
    
    Deferred:
    - Cockpit cutouts
    - Hatch openings
    - Cabin footprints
    """
    
    def __init__(self, num_strips: int = 5):
        """
        Initialize deck generator.
        
        Args:
            num_strips: Number of strips across deck (centerline to edge)
        """
        self._num_strips = num_strips
    
    def generate(
        self,
        sections: List[HullSection],
        config: DeckConfig,
        definition: HullDefinition,
    ) -> DeckGeometry:
        """
        Generate deck surface.
        
        Args:
            sections: Hull sections with deck edge points
            config: Deck configuration
            definition: Hull definition
            
        Returns:
            DeckGeometry with vertices, triangles, edges
        """
        if not config.enabled:
            return DeckGeometry()
        
        # Extract deck edge points from sections
        edge_points = self._extract_deck_edge(sections)
        
        if len(edge_points) < 2:
            return DeckGeometry(edge_points=edge_points)
        
        # Generate centerline points with camber
        centerline_points = self._generate_centerline(
            edge_points, config, len(sections)
        )
        
        # Generate deck surface mesh (starboard side, then mirror)
        vertices, triangles, normals = self._generate_deck_mesh(
            edge_points, centerline_points, config
        )
        
        return DeckGeometry(
            vertices=vertices,
            triangles=triangles,
            edge_points=edge_points,
            centerline_points=centerline_points,
            normals=normals,
        )
    
    def _extract_deck_edge(self, sections: List[HullSection]) -> List[Point3D]:
        """
        Extract deck edge points from hull sections.
        
        The deck edge is the last point of each section (highest Z, at half-beam).
        """
        edge_points = []
        
        for section in sections:
            if section.points:
                # Last point of each section is deck edge
                deck_point = section.points[-1].position
                edge_points.append(deck_point)
        
        return edge_points
    
    def _generate_centerline(
        self,
        edge_points: List[Point3D],
        config: DeckConfig,
        num_sections: int,
    ) -> List[Point3D]:
        """
        Generate centerline points with optional camber.
        
        Centerline is at Y=0, with Z = edge_Z + camber + sheer_adjustment.
        """
        centerline = []
        
        for i, edge_pt in enumerate(edge_points):
            # Station fraction for sheer adjustment
            t = i / (num_sections - 1) if num_sections > 1 else 0
            
            # Base Z at centerline = edge Z + camber
            base_z = edge_pt.z
            
            # Add camber at centerline
            if config.camber_m > 0:
                base_z += config.camber_m
            
            # Add sheer adjustment (interpolate bow to stern)
            # t=0 is stern (aft), t=1 is bow (forward)
            sheer_adj = (
                config.sheer_adjustment_bow_m * t +
                config.sheer_adjustment_stern_m * (1 - t)
            )
            base_z += sheer_adj
            
            centerline.append(Point3D(
                x=edge_pt.x,
                y=0.0,  # Centerline is at Y=0
                z=base_z,
            ))
        
        return centerline
    
    def _generate_deck_mesh(
        self,
        edge_points: List[Point3D],
        centerline_points: List[Point3D],
        config: DeckConfig,
    ) -> Tuple[List[Point3D], List[Tuple[int, int, int]], List[Tuple[float, float, float]]]:
        """
        Generate triangulated deck surface mesh.
        
        Creates a grid of vertices from centerline to edge for starboard side,
        then mirrors for port side.
        """
        vertices: List[Point3D] = []
        triangles: List[Tuple[int, int, int]] = []
        normals: List[Tuple[float, float, float]] = []
        
        num_sections = len(edge_points)
        num_strips = self._num_strips
        
        # Generate vertex grid for starboard side
        # Rows = sections (longitudinal), Cols = strips across deck
        vertex_grid: List[List[int]] = []  # [section_idx][strip_idx] = vertex_idx
        
        for i in range(num_sections):
            row = []
            edge_pt = edge_points[i]
            center_pt = centerline_points[i]
            half_beam = edge_pt.y if edge_pt.y > 0 else 1.0
            
            for j in range(num_strips + 1):
                s = j / num_strips  # 0 = centerline, 1 = edge
                
                # Interpolate position
                x = center_pt.x  # Same X along section
                y = s * edge_pt.y  # Linear Y interpolation
                
                # Z with camber profile
                z = self._calculate_deck_z(
                    s, edge_pt.z, center_pt.z, half_beam, config
                )
                
                vertex_idx = len(vertices)
                vertices.append(Point3D(x=x, y=y, z=z))
                normals.append((0.0, 0.0, 1.0))  # Deck normal points up
                row.append(vertex_idx)
            
            vertex_grid.append(row)
        
        # Generate triangles for starboard side
        for i in range(num_sections - 1):
            for j in range(num_strips):
                # Quad vertices
                v00 = vertex_grid[i][j]
                v01 = vertex_grid[i][j + 1]
                v10 = vertex_grid[i + 1][j]
                v11 = vertex_grid[i + 1][j + 1]
                
                # Two triangles per quad (counter-clockwise for up-facing normals)
                triangles.append((v00, v10, v01))
                triangles.append((v01, v10, v11))
        
        # Mirror for port side (negative Y)
        num_starboard_verts = len(vertices)
        port_grid: List[List[int]] = []
        
        for i in range(num_sections):
            row = []
            for j in range(num_strips + 1):
                if j == 0:
                    # Centerline vertices are shared
                    row.append(vertex_grid[i][0])
                else:
                    # Mirror non-centerline vertices
                    orig_idx = vertex_grid[i][j]
                    orig_pt = vertices[orig_idx]
                    mirrored_pt = Point3D(x=orig_pt.x, y=-orig_pt.y, z=orig_pt.z)
                    new_idx = len(vertices)
                    vertices.append(mirrored_pt)
                    normals.append((0.0, 0.0, 1.0))
                    row.append(new_idx)
            port_grid.append(row)
        
        # Generate triangles for port side (reversed winding for consistent normals)
        for i in range(num_sections - 1):
            for j in range(num_strips):
                v00 = port_grid[i][j]
                v01 = port_grid[i][j + 1]
                v10 = port_grid[i + 1][j]
                v11 = port_grid[i + 1][j + 1]
                
                # Reversed winding for port side
                triangles.append((v00, v01, v10))
                triangles.append((v01, v11, v10))
        
        return vertices, triangles, normals
    
    def _calculate_deck_z(
        self,
        s: float,  # 0=centerline, 1=edge
        edge_z: float,
        center_z: float,
        half_beam: float,
        config: DeckConfig,
    ) -> float:
        """
        Calculate deck Z height at given transverse position.
        
        Args:
            s: Transverse position (0=centerline, 1=edge)
            edge_z: Z at deck edge
            center_z: Z at centerline (includes camber)
            half_beam: Half beam at this section
            config: Deck configuration
            
        Returns:
            Z height at this point
        """
        if config.is_flat() or config.camber_m <= 0:
            # Flat: linear interpolation
            return center_z * (1 - s) + edge_z * s
        
        y = s * half_beam
        
        if config.camber_profile == "parabolic":
            # Parabolic: z = center_z - camber * (y/half_beam)^2
            # At edge (s=1): z = center_z - camber = edge_z (as expected)
            camber_offset = config.camber_m * (1 - s * s)
            return edge_z + camber_offset
        
        elif config.camber_profile == "circular":
            # Circular arc: compute arc height at position
            # Arc passes through edge (y=half_beam, z=edge_z) with rise = camber at center
            if half_beam > 0:
                # Radius from camber and half_beam
                r = (half_beam ** 2 + config.camber_m ** 2) / (2 * config.camber_m)
                # Arc height at y position
                arc_height = r - math.sqrt(max(0, r ** 2 - y ** 2))
                return edge_z + arc_height
            else:
                return center_z
        
        else:
            # Default: linear
            return center_z * (1 - s) + edge_z * s

