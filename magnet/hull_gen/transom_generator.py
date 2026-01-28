"""
hull_gen/transom_generator.py - Parametric transom geometry generator.

BRAVO OWNS THIS FILE.

Phase 5: Generates transom geometry from TransomConfig with support for:
- Variable rake profiles
- Stepped transoms (vertical segments)
- Cutouts (tunnels, notches)
- Extensions (platforms, swim steps)
- Athwartships curvature
- Corner rounding
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from magnet.hull_gen.geometry import Point3D, SectionPoint, EdgeType, HullSection
from magnet.hull_gen.parameters import (
    TransomConfig,
    TransomSegment,
    TransomCutout,
    TransomExtension,
    TransomEdgeConfig,
    HullDefinition,
)


@dataclass
class TransomEdge:
    """
    Represents a hard edge on the transom for mesh rendering.
    
    Similar to BowPanelEdge, tracks which vertex pairs need sharp normals.
    """
    start_vertex_idx: int
    end_vertex_idx: int
    edge_type: str = "hard"  # "hard" | "soft" | "rounded"
    feature_id: str = ""     # e.g., "transom_step_0", "cutout_0_edge"


@dataclass
class TransomGeometry:
    """
    Output from transom generation containing all geometry data.
    """
    
    # Main transom surface as a section (at station = 0)
    section: HullSection
    """Transom section at the stern."""
    
    # Additional geometry from cutouts and extensions
    cutout_sections: List[HullSection] = field(default_factory=list)
    """Sections defining cutout geometry (if any)."""
    
    extension_sections: List[HullSection] = field(default_factory=list)
    """Sections defining extension geometry (if any)."""
    
    # Hard edges for mesh rendering
    hard_edges: List[TransomEdge] = field(default_factory=list)
    """Hard edges (steps, cutout borders, etc.)."""
    
    # Blending information for forward stations
    blend_stations: List[Tuple[float, float]] = field(default_factory=list)
    """Stations where transom influence blends into hull: (station, blend_factor)."""


class TransomGenerator:
    """
    Generates transom geometry from TransomConfig.
    
    The transom is fundamentally a 2D shape (Y-Z plane at X=0 or stern station)
    that may have:
    - Variable rake (X offset depending on Z height)
    - Athwartships curvature
    - Cutouts (tunnels) that extend forward
    - Extensions that project aft
    
    Output is a single HullSection at station=0 (stern) plus optional
    geometry for cutouts and extensions.
    """
    
    def __init__(self):
        """Initialize transom generator."""
        self._config: Optional[TransomConfig] = None
        self._definition: Optional[HullDefinition] = None
    
    def generate(
        self,
        config: TransomConfig,
        definition: HullDefinition,
    ) -> TransomGeometry:
        """
        Generate transom geometry from configuration.
        
        Args:
            config: Full parametric transom configuration
            definition: Hull definition for dimensions
            
        Returns:
            TransomGeometry with section, cutouts, extensions, and edges
        """
        self._config = config
        self._definition = definition
        
        # Get hull dimensions
        draft = definition.dimensions.draft
        depth = definition.dimensions.depth
        beam = definition.dimensions.beam_wl
        
        # Generate main transom section
        if config.has_segments():
            section = self._generate_segmented_transom(draft, depth, beam)
        else:
            section = self._generate_simple_transom(draft, depth, beam)
        
        # Collect hard edges
        hard_edges = self._collect_hard_edges(section)
        
        # Generate cutout geometry
        cutout_sections = []
        if config.has_cutouts():
            cutout_sections = self._generate_cutouts(draft, depth, beam)
            hard_edges.extend(self._collect_cutout_edges(cutout_sections))
        
        # Generate extension geometry
        extension_sections = []
        if config.has_extensions():
            extension_sections = self._generate_extensions(draft, depth, beam)
            hard_edges.extend(self._collect_extension_edges(extension_sections))
        
        # Calculate blend stations
        blend_stations = self._calculate_blend_stations(definition.dimensions.lwl)
        
        return TransomGeometry(
            section=section,
            cutout_sections=cutout_sections,
            extension_sections=extension_sections,
            hard_edges=hard_edges,
            blend_stations=blend_stations,
        )
    
    def _generate_simple_transom(
        self,
        draft: float,
        depth: float,
        beam: float,
    ) -> HullSection:
        """
        Generate a simple transom (no vertical segments).
        
        Points are generated from keel (Z=-draft) to deck (Z=depth-draft),
        with variable beam and curvature by height.
        """
        config = self._config
        points: List[SectionPoint] = []
        
        # Number of points for smooth representation
        n_points = 20
        
        # Generate points from keel to deck
        for i in range(n_points + 1):
            height_ratio = i / n_points
            z = -draft + height_ratio * depth
            
            # Get variable parameters at this height
            beam_ratio = config.get_beam_ratio_at_height(height_ratio)
            curvature = config.get_curvature_at_height(height_ratio)
            corner_radius = config.get_corner_radius_at_height(height_ratio)
            rake = config.get_rake_at_height(height_ratio)
            
            # Calculate Y (half-beam at this height)
            y = beam * 0.5 * beam_ratio
            
            # Apply curvature (modifies Y based on Z position within transom)
            if curvature != 0:
                y = self._apply_curvature(y, height_ratio, curvature)
            
            # Calculate X offset from rake
            x = self._calculate_rake_offset(z, draft, rake)
            
            # Determine edge type
            edge_type = EdgeType.SMOOTH
            is_edge = (i == 0 or i == n_points)  # Bottom or top edge
            
            if is_edge:
                if i == 0:
                    edge_config = config.bottom_edge
                else:
                    edge_config = config.top_edge
                edge_type = self._edge_config_to_type(edge_config)
            
            points.append(SectionPoint(
                position=Point3D(x=x, y=y, z=z),
                edge_type=edge_type,
                is_chine=False,
                feature_id=f"transom_h{height_ratio:.2f}",
            ))
        
        return HullSection(
            station=0.0,  # Stern
            points=points,
        )
    
    def _generate_segmented_transom(
        self,
        draft: float,
        depth: float,
        beam: float,
    ) -> HullSection:
        """
        Generate a transom with vertical segments (stepped transom).
        
        Each segment can have different rake and offset.
        """
        config = self._config
        points: List[SectionPoint] = []
        
        segments = config.vertical_segments
        
        for seg_idx, segment in enumerate(segments):
            # Calculate Z range for this segment
            z_start = -draft + segment.height_start * depth
            z_end = -draft + segment.height_end * depth
            
            # Points within this segment
            n_points = max(5, int((segment.height_end - segment.height_start) * 20))
            
            for i in range(n_points + 1):
                t = i / n_points
                height_ratio = segment.height_start + t * (segment.height_end - segment.height_start)
                z = z_start + t * (z_end - z_start)
                
                # Get beam at this height
                beam_ratio = config.get_beam_ratio_at_height(height_ratio)
                y = beam * 0.5 * beam_ratio
                
                # Apply segment-specific offsets
                y += segment.offset_outboard_m
                
                # Apply segment curvature
                if segment.curvature != 0:
                    y = self._apply_curvature(y, t, segment.curvature)
                
                # Calculate X from segment rake + offset
                x = self._calculate_rake_offset(z, draft, segment.rake_deg)
                x += segment.offset_aft_m
                
                # Determine edge type
                is_segment_boundary = (i == 0 or i == n_points)
                edge_type = EdgeType.SMOOTH
                
                if is_segment_boundary:
                    if segment.edge_type == "hard":
                        edge_type = EdgeType.HARD
                    elif segment.edge_type == "rounded":
                        edge_type = EdgeType.CREASE
                
                # Mark first point of non-first segments as hard (step edge)
                if seg_idx > 0 and i == 0:
                    edge_type = EdgeType.HARD
                
                points.append(SectionPoint(
                    position=Point3D(x=x, y=y, z=z),
                    edge_type=edge_type,
                    is_chine=False,
                    feature_id=f"transom_seg{seg_idx}_h{height_ratio:.2f}",
                ))
        
        return HullSection(
            station=0.0,
            points=points,
        )
    
    def _generate_cutouts(
        self,
        draft: float,
        depth: float,
        beam: float,
    ) -> List[HullSection]:
        """
        Generate geometry for transom cutouts (tunnels, notches).
        
        Each cutout is represented as a series of sections extending forward.
        """
        cutout_sections = []
        
        for cutout_idx, cutout in enumerate(self._config.cutouts):
            if cutout.depth_m <= 0:
                # Surface notch only - handled in main transom generation
                continue
            
            # Generate sections along the cutout depth
            n_sections = max(3, int(cutout.depth_m * 10))
            
            for i in range(n_sections + 1):
                t = i / n_sections
                x = -t * cutout.depth_m  # Forward into hull
                
                # Calculate cutout cross-section at this depth
                points = self._generate_cutout_section(
                    cutout, cutout_idx, x, t, draft, depth, beam
                )
                
                cutout_sections.append(HullSection(
                    station=x,  # Negative = forward of transom
                    points=points,
                ))
        
        return cutout_sections
    
    def _generate_cutout_section(
        self,
        cutout: TransomCutout,
        cutout_idx: int,
        x: float,
        t: float,  # 0=transom face, 1=deepest
        draft: float,
        depth: float,
        beam: float,
    ) -> List[SectionPoint]:
        """Generate the cross-section of a cutout at given depth."""
        points: List[SectionPoint] = []
        
        # Calculate cutout position
        center_y = cutout.center_y_ratio * beam * 0.5
        z_bottom = -draft + cutout.height_start_ratio * depth
        
        # Apply draft angle taper
        taper = 1.0 - t * math.tan(math.radians(cutout.draft_angle_deg))
        width = cutout.width_m * taper
        height = cutout.height_m * taper
        
        # Generate outline based on shape
        if cutout.shape == "semicircle":
            outline = self._generate_semicircle_outline(width, height)
        elif cutout.shape == "ellipse":
            outline = self._generate_ellipse_outline(width, height)
        else:  # rectangular
            outline = self._generate_rectangular_outline(
                width, height, cutout.corner_radius_m
            )
        
        # Convert outline to section points
        edge_type = EdgeType.HARD if cutout.edge_type == "hard" else EdgeType.SMOOTH
        
        for pt_idx, (dy, dz) in enumerate(outline):
            points.append(SectionPoint(
                position=Point3D(x=x, y=center_y + dy, z=z_bottom + dz),
                edge_type=edge_type,
                is_chine=False,
                feature_id=f"cutout_{cutout_idx}_{pt_idx}",
            ))
        
        return points
    
    def _generate_extensions(
        self,
        draft: float,
        depth: float,
        beam: float,
    ) -> List[HullSection]:
        """
        Generate geometry for transom extensions (platforms, brackets).
        """
        extension_sections = []
        
        for ext_idx, ext in enumerate(self._config.extensions):
            # Generate sections along the extension depth
            n_sections = max(3, int(ext.depth_m * 5))
            
            for i in range(n_sections + 1):
                t = i / n_sections
                x = t * ext.depth_m  # Positive = aft of transom
                
                points = self._generate_extension_section(
                    ext, ext_idx, x, t, draft, depth, beam
                )
                
                extension_sections.append(HullSection(
                    station=x,  # Positive = aft
                    points=points,
                ))
        
        return extension_sections
    
    def _generate_extension_section(
        self,
        ext: TransomExtension,
        ext_idx: int,
        x: float,
        t: float,  # 0=transom, 1=end of extension
        draft: float,
        depth: float,
        beam: float,
    ) -> List[SectionPoint]:
        """Generate cross-section of an extension at given depth."""
        points: List[SectionPoint] = []
        
        # Calculate vertical extent
        z_bottom = -draft + ext.height_start * depth
        z_top = -draft + ext.height_end * depth
        
        # Apply slope
        z_offset = t * ext.depth_m * math.tan(math.radians(ext.slope_deg))
        z_bottom += z_offset
        z_top += z_offset
        
        # Calculate width at this height
        avg_height_ratio = (ext.height_start + ext.height_end) / 2
        beam_ratio = self._config.get_beam_ratio_at_height(avg_height_ratio)
        width = beam * beam_ratio * ext.width_ratio
        
        # Apply curvature
        n_points = 10
        for i in range(n_points + 1):
            pt_t = i / n_points
            y = -width * 0.5 + pt_t * width
            z = z_bottom + (z_top - z_bottom) * 0.5  # Middle of extension
            
            # Apply extension curvature
            if ext.curvature != 0:
                # Parabolic curvature
                normalized_y = (pt_t - 0.5) * 2  # -1 to 1
                z_adjust = ext.curvature * (1 - normalized_y**2) * ext.depth_m
                z += z_adjust
            
            edge_type = EdgeType.HARD if (i == 0 or i == n_points) else EdgeType.SMOOTH
            
            points.append(SectionPoint(
                position=Point3D(x=x, y=y, z=z),
                edge_type=edge_type,
                is_chine=False,
                feature_id=f"extension_{ext_idx}_{i}",
            ))
        
        return points
    
    def _apply_curvature(
        self,
        y: float,
        height_ratio: float,
        curvature: float,
    ) -> float:
        """
        Apply athwartships curvature to Y coordinate.
        
        Curvature > 0: convex (bulges outward)
        Curvature < 0: concave (curves inward)
        """
        # Parabolic curvature centered at mid-height
        t = (height_ratio - 0.5) * 2  # -1 to 1
        y_adjust = curvature * (1 - t**2) * y * 0.1
        return y + y_adjust
    
    def _calculate_rake_offset(
        self,
        z: float,
        draft: float,
        rake_deg: float,
    ) -> float:
        """
        Calculate X offset from rake angle.
        
        Rake is measured from vertical: positive = aft rake (typical).
        At waterline (z=0), rake applies. At keel (z=-draft), typically less.
        """
        # Height from keel
        height_from_keel = z + draft
        if height_from_keel < 0:
            height_from_keel = 0
        
        # X offset = height * tan(rake)
        return height_from_keel * math.tan(math.radians(rake_deg))
    
    def _edge_config_to_type(self, edge_config: TransomEdgeConfig) -> EdgeType:
        """Convert TransomEdgeConfig to EdgeType enum."""
        if edge_config.type in ("hard", "chamfered"):
            return EdgeType.HARD
        elif edge_config.type in ("soft", "rounded", "bullnose"):
            return EdgeType.CREASE
        return EdgeType.SMOOTH
    
    def _generate_semicircle_outline(
        self,
        width: float,
        height: float,
    ) -> List[Tuple[float, float]]:
        """Generate semicircle outline for cutout."""
        points = []
        n_points = 16
        
        for i in range(n_points + 1):
            angle = math.pi * i / n_points
            dy = width * 0.5 * math.cos(angle)
            dz = height * math.sin(angle)
            points.append((dy, dz))
        
        return points
    
    def _generate_ellipse_outline(
        self,
        width: float,
        height: float,
    ) -> List[Tuple[float, float]]:
        """Generate full ellipse outline for cutout."""
        points = []
        n_points = 24
        
        for i in range(n_points):
            angle = 2 * math.pi * i / n_points
            dy = width * 0.5 * math.cos(angle)
            dz = height * 0.5 * math.sin(angle) + height * 0.5
            points.append((dy, dz))
        
        return points
    
    def _generate_rectangular_outline(
        self,
        width: float,
        height: float,
        corner_radius: float,
    ) -> List[Tuple[float, float]]:
        """Generate rectangular outline with optional corner radius."""
        points = []
        
        if corner_radius <= 0:
            # Simple rectangle
            points = [
                (-width * 0.5, 0),
                (-width * 0.5, height),
                (width * 0.5, height),
                (width * 0.5, 0),
            ]
        else:
            # Rectangle with rounded corners
            r = min(corner_radius, width * 0.5, height * 0.5)
            n_corner = 4
            
            # Bottom-left corner
            for i in range(n_corner + 1):
                angle = math.pi + math.pi * 0.5 * i / n_corner
                points.append((
                    -width * 0.5 + r + r * math.cos(angle),
                    r + r * math.sin(angle),
                ))
            
            # Top-left corner
            for i in range(n_corner + 1):
                angle = -math.pi * 0.5 + math.pi * 0.5 * i / n_corner
                points.append((
                    -width * 0.5 + r + r * math.cos(angle),
                    height - r + r * math.sin(angle),
                ))
            
            # Top-right corner
            for i in range(n_corner + 1):
                angle = math.pi * 0.5 * i / n_corner
                points.append((
                    width * 0.5 - r + r * math.cos(angle),
                    height - r + r * math.sin(angle),
                ))
            
            # Bottom-right corner
            for i in range(n_corner + 1):
                angle = math.pi * 0.5 + math.pi * 0.5 * i / n_corner
                points.append((
                    width * 0.5 - r + r * math.cos(angle),
                    r + r * math.sin(angle),
                ))
        
        return points
    
    def _collect_hard_edges(self, section: HullSection) -> List[TransomEdge]:
        """Collect hard edges from transom section."""
        edges = []
        
        for i, point in enumerate(section.points):
            if point.edge_type == EdgeType.HARD:
                # Mark edge from this point to next
                if i < len(section.points) - 1:
                    edges.append(TransomEdge(
                        start_vertex_idx=i,
                        end_vertex_idx=i + 1,
                        edge_type="hard",
                        feature_id=point.feature_id or f"transom_edge_{i}",
                    ))
        
        return edges
    
    def _collect_cutout_edges(
        self,
        cutout_sections: List[HullSection],
    ) -> List[TransomEdge]:
        """Collect hard edges from cutout sections."""
        edges = []
        
        for sec_idx, section in enumerate(cutout_sections):
            for i, point in enumerate(section.points):
                if point.edge_type == EdgeType.HARD:
                    if i < len(section.points) - 1:
                        edges.append(TransomEdge(
                            start_vertex_idx=i,
                            end_vertex_idx=i + 1,
                            edge_type="hard",
                            feature_id=point.feature_id or f"cutout_edge_{sec_idx}_{i}",
                        ))
        
        return edges
    
    def _collect_extension_edges(
        self,
        extension_sections: List[HullSection],
    ) -> List[TransomEdge]:
        """Collect hard edges from extension sections."""
        edges = []
        
        for sec_idx, section in enumerate(extension_sections):
            for i, point in enumerate(section.points):
                if point.edge_type == EdgeType.HARD:
                    if i < len(section.points) - 1:
                        edges.append(TransomEdge(
                            start_vertex_idx=i,
                            end_vertex_idx=i + 1,
                            edge_type="hard",
                            feature_id=point.feature_id or f"ext_edge_{sec_idx}_{i}",
                        ))
        
        return edges
    
    def _calculate_blend_stations(self, lwl: float) -> List[Tuple[float, float]]:
        """
        Calculate stations where transom shape blends into hull.
        
        Returns list of (station, blend_factor) where:
        - station is fraction of LWL (0=stern)
        - blend_factor is 0-1 (0=no transom influence, 1=full transom shape)
        """
        blend_length = self._config.blend_to_hull_length_m / lwl
        
        # Generate blend curve
        n_stations = 5
        stations = []
        
        for i in range(n_stations + 1):
            station = blend_length * i / n_stations
            # Smooth blend factor
            t = 1.0 - station / blend_length if blend_length > 0 else 0.0
            blend_factor = t * t * (3 - 2 * t)  # Hermite smoothstep
            stations.append((station, blend_factor))
        
        return stations

