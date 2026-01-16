"""
hull_gen/bow_generator.py - Bow form generator module.

BRAVO OWNS THIS FILE.

Phase 3: Generates bow region geometry for various styles:
- Traditional (smooth lofted)
- Wedge (two planar panels)
- Axe (vertical stem, sharp entry)
- Faceted (multiple planar panels)
- Wave-piercing (fine entry, tumblehome)

All bow forms are parametric and produce EdgeType metadata for proper
hard edge rendering in the mesh pipeline.
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from magnet.hull_gen.geometry import Point3D, SectionPoint, EdgeType, HullSection
from magnet.hull_gen.parameters import BowConfig, HullDefinition
from magnet.hull_gen.enums import BowStyle, StemProfile


@dataclass
class BowPanelEdge:
    """
    Edge of a bow panel for hard edge tracking.
    
    Used by mesh builder to mark edges requiring split normals.
    """
    start_point: Point3D
    end_point: Point3D
    is_hard: bool = True
    feature_id: str = ""


@dataclass
class BowGeometry:
    """Generated bow geometry."""
    sections: List[HullSection] = field(default_factory=list)
    """Bow sections (from FP aft)."""
    
    stem_curve: List[Point3D] = field(default_factory=list)
    """Stem profile points."""
    
    panel_edges: List[BowPanelEdge] = field(default_factory=list)
    """Hard edges between panels."""
    
    waterline_entry: List[Point3D] = field(default_factory=list)
    """Waterline curve at bow."""


class BowGenerator:
    """
    Generates bow region geometry based on style configuration.
    
    The bow region extends from the forward perpendicular (FP) aft
    to the bow_region_length fraction of LWL.
    
    Usage:
        generator = BowGenerator()
        bow_config = BowConfig(style=BowStyle.WEDGE)
        bow_geometry = generator.generate(definition, bow_config)
    """
    
    def __init__(self):
        self._definition: Optional[HullDefinition] = None
        self._config: Optional[BowConfig] = None
    
    def generate(
        self,
        definition: HullDefinition,
        config: BowConfig,
        num_sections: int = 8,
    ) -> BowGeometry:
        """
        Generate bow geometry.
        
        Args:
            definition: Hull definition with dimensions
            config: Bow configuration
            num_sections: Number of sections in bow region
            
        Returns:
            BowGeometry with sections, stem curve, and panel edges
        """
        self._definition = definition
        self._config = config
        
        # Dispatch to style-specific generator
        if config.style == BowStyle.WEDGE:
            return self._generate_wedge_bow(num_sections)
        elif config.style == BowStyle.AXE:
            return self._generate_axe_bow(num_sections)
        elif config.style == BowStyle.FACETED:
            return self._generate_faceted_bow(num_sections)
        elif config.style == BowStyle.WAVE_PIERCING:
            return self._generate_wave_piercing_bow(num_sections)
        else:
            return self._generate_traditional_bow(num_sections)
    
    # =========================================================================
    # WEDGE BOW
    # =========================================================================
    
    def _generate_wedge_bow(self, num_sections: int) -> BowGeometry:
        """
        Generate wedge bow with two planar panels meeting at stem.
        
        Side view:          Top view:
            │                  ╱│╲
            │\\                ╱ │ ╲
            │ \\              ╱  │  ╲
            │  \\            ╱   │   ╲
            └───            ────┴────
        """
        sections = []
        panel_edges = []
        
        dims = self._definition.dimensions
        lwl = dims.lwl
        bow_length = lwl * self._config.region_length
        half_angle_rad = math.radians(self._config.half_angle_deg)
        
        # Generate stem curve (leading edge)
        stem_curve = self._generate_stem_curve()
        
        for i in range(num_sections):
            # Station progresses from stem (0) to end of bow region (1)
            t = i / (num_sections - 1) if num_sections > 1 else 0
            x = t * bow_length
            
            # Beam at this station (linear growth from stem)
            # At end of bow region, we reach ~50% of max beam
            local_half_beam = t * dims.beam_max * 0.5
            
            # Generate wedge section
            section = self._generate_wedge_section(x, t, local_half_beam)
            sections.append(section)
        
        # Define panel edges (stem to each side)
        if sections:
            last_section = sections[-1]
            waterline_y = max(p.position.y for p in last_section.points) if last_section.points else 0
            
            panel_edges.append(BowPanelEdge(
                start_point=stem_curve[0] if stem_curve else Point3D(0, 0, -dims.draft),
                end_point=Point3D(x=bow_length, y=waterline_y, z=0),
                is_hard=True,
                feature_id="bow_panel_port",
            ))
            panel_edges.append(BowPanelEdge(
                start_point=stem_curve[0] if stem_curve else Point3D(0, 0, -dims.draft),
                end_point=Point3D(x=bow_length, y=-waterline_y, z=0),
                is_hard=True,
                feature_id="bow_panel_starboard",
            ))
        
        # Stem edge itself is hard
        if len(stem_curve) >= 2:
            panel_edges.append(BowPanelEdge(
                start_point=stem_curve[0],
                end_point=stem_curve[-1],
                is_hard=True,
                feature_id="stem_edge",
            ))
        
        return BowGeometry(
            sections=sections,
            stem_curve=stem_curve,
            panel_edges=panel_edges,
            waterline_entry=self._extract_waterline_entry(sections),
        )
    
    def _generate_wedge_section(
        self,
        x: float,
        t: float,  # 0=stem, 1=end of bow region
        local_half_beam: float,
    ) -> HullSection:
        """Generate a single wedge bow section."""
        points = []
        dims = self._definition.dimensions
        draft = dims.draft
        depth = dims.depth
        
        # At stem (t=0), section is a single point or very narrow
        if t < 0.01:
            # Stem point
            stem_z = -draft
            points.append(SectionPoint(
                position=Point3D(x=x, y=0, z=stem_z),
                edge_type=EdgeType.HARD,
                is_keel=True,
                feature_id="stem",
            ))
        else:
            # Wedge section: keel → chine → deck edge
            num_points = 7
            
            for j in range(num_points):
                s = j / (num_points - 1)  # 0=keel, 1=deck edge
                
                # Y: linear from 0 to local_half_beam
                y = s * local_half_beam
                
                # Z: follows deadrise angle from keel, then vertical to deck
                if s < 0.5:  # Bottom panel (V-shape)
                    z = -draft + s * 2 * draft * 0.7
                    is_chine = False
                elif s < 0.55:  # Chine transition
                    z = -draft * 0.3
                    is_chine = True
                else:  # Side panel
                    z_chine = -draft * 0.3
                    z = z_chine + (s - 0.55) / 0.45 * (depth - z_chine - draft)
                    is_chine = False
                
                # Edge type: hard at stem and chine
                if j == 0 or is_chine:
                    edge_type = EdgeType.HARD
                else:
                    edge_type = EdgeType.SMOOTH
                
                points.append(SectionPoint(
                    position=Point3D(x=x, y=y, z=z),
                    edge_type=edge_type,
                    is_keel=(j == 0),
                    is_chine=is_chine,
                    feature_id="wedge_bottom" if s < 0.5 else "wedge_side",
                ))
        
        # Calculate station as fraction of LWL
        station = 1.0 - (t * self._config.region_length)  # Bow is near station 1.0
        
        return HullSection(
            station=station,
            points=points,
        )
    
    # =========================================================================
    # AXE BOW
    # =========================================================================
    
    def _generate_axe_bow(self, num_sections: int) -> BowGeometry:
        """
        Generate axe bow with vertical stem and sharp entry.
        
        Characteristic features:
        - Vertical or near-vertical stem
        - Very fine waterline entry angle
        - Deep forefoot
        """
        sections = []
        panel_edges = []
        
        dims = self._definition.dimensions
        lwl = dims.lwl
        bow_length = lwl * self._config.region_length
        
        # Axe bow has vertical stem
        stem_curve = self._generate_vertical_stem_curve()
        
        for i in range(num_sections):
            t = i / (num_sections - 1) if num_sections > 1 else 0
            x = t * bow_length
            
            # Very fine entry - beam grows slowly (square root for fine forward sections)
            local_half_beam = math.sqrt(t) * dims.beam_max * 0.4
            
            section = self._generate_axe_section(x, t, local_half_beam)
            sections.append(section)
        
        # Axe bow has hard stem edge
        if len(stem_curve) >= 2:
            panel_edges.append(BowPanelEdge(
                start_point=stem_curve[0],
                end_point=stem_curve[-1],
                is_hard=True,
                feature_id="axe_stem",
            ))
        
        return BowGeometry(
            sections=sections,
            stem_curve=stem_curve,
            panel_edges=panel_edges,
            waterline_entry=self._extract_waterline_entry(sections),
        )
    
    def _generate_axe_section(
        self,
        x: float,
        t: float,
        local_half_beam: float,
    ) -> HullSection:
        """Generate a single axe bow section."""
        points = []
        dims = self._definition.dimensions
        draft = dims.draft
        depth = dims.depth
        
        num_points = 9
        
        for j in range(num_points):
            s = j / (num_points - 1)
            
            # Axe sections are V-shaped with hard chine
            if s < 0.45:  # V-bottom
                y = s / 0.45 * local_half_beam * 0.7
                z = -draft + s / 0.45 * draft * 0.6
                is_chine = False
            elif s < 0.55:  # Chine region
                y = local_half_beam * 0.7
                z = -draft * 0.4
                is_chine = True
            else:  # Topside
                st = (s - 0.55) / 0.45
                y = local_half_beam * 0.7 + st * local_half_beam * 0.3
                z = -draft * 0.4 + st * (depth + draft * 0.4)
                is_chine = False
            
            edge_type = EdgeType.HARD if (is_chine or j == 0) else EdgeType.SMOOTH
            
            points.append(SectionPoint(
                position=Point3D(x=x, y=y, z=z),
                edge_type=edge_type,
                is_keel=(j == 0),
                is_chine=is_chine,
                feature_id="axe_bottom" if s < 0.45 else "axe_side",
            ))
        
        station = 1.0 - (t * self._config.region_length)
        
        return HullSection(
            station=station,
            points=points,
        )
    
    def _generate_vertical_stem_curve(self) -> List[Point3D]:
        """Generate vertical stem curve for axe bow."""
        dims = self._definition.dimensions
        points = []
        
        num_points = 5
        for i in range(num_points):
            t = i / (num_points - 1)
            z = -dims.draft + t * (dims.depth + dims.draft)
            points.append(Point3D(x=0, y=0, z=z))
        
        return points
    
    # =========================================================================
    # FACETED BOW
    # =========================================================================
    
    def _generate_faceted_bow(self, num_sections: int) -> BowGeometry:
        """
        Generate faceted bow with N planar panels per side.
        
        Each panel is a flat surface, meeting adjacent panels at hard edges.
        More panels = more gradual transition, fewer = more angular.
        
        Top view (3 panels per side):
                 ╱│╲
               ╱  │  ╲
             ╱────│────╲
           ╱      │      ╲
         ╱────────│────────╲
        ╱         │         ╲
        """
        sections = []
        panel_edges = []
        
        dims = self._definition.dimensions
        lwl = dims.lwl
        bow_length = lwl * self._config.region_length
        facet_count = max(1, self._config.facet_count)
        
        stem_curve = self._generate_stem_curve()
        
        # Generate sections
        for i in range(num_sections):
            t = i / (num_sections - 1) if num_sections > 1 else 0
            x = t * bow_length
            local_half_beam = t * dims.beam_max * 0.5
            
            section = self._generate_faceted_section(x, t, local_half_beam, facet_count)
            sections.append(section)
        
        # Generate panel edges for each facet
        for panel_idx in range(facet_count):
            # Each panel has an edge running from stem to aft end
            panel_angle = (panel_idx + 1) / facet_count * math.pi / 2  # 0 to 90 degrees
            
            end_y = math.sin(panel_angle) * dims.beam_max * 0.5
            end_z = -dims.draft + math.cos(panel_angle) * dims.draft
            
            panel_edges.append(BowPanelEdge(
                start_point=Point3D(x=0, y=0, z=-dims.draft),
                end_point=Point3D(x=bow_length, y=end_y, z=end_z),
                is_hard=True,
                feature_id=f"bow_facet_{panel_idx}",
            ))
        
        return BowGeometry(
            sections=sections,
            stem_curve=stem_curve,
            panel_edges=panel_edges,
            waterline_entry=self._extract_waterline_entry(sections),
        )
    
    def _generate_faceted_section(
        self,
        x: float,
        t: float,
        local_half_beam: float,
        facet_count: int,
    ) -> HullSection:
        """Generate a section with faceted (planar panel) geometry."""
        points = []
        dims = self._definition.dimensions
        draft = dims.draft
        depth = dims.depth
        
        # Keel point
        points.append(SectionPoint(
            position=Point3D(x=x, y=0, z=-draft),
            edge_type=EdgeType.HARD,
            is_keel=True,
            feature_id="keel",
        ))
        
        # Generate points at panel boundaries
        points_per_facet = 2
        
        for facet_idx in range(facet_count):
            for j in range(points_per_facet):
                # Progress through this facet
                facet_start = facet_idx / facet_count
                facet_end = (facet_idx + 1) / facet_count
                s = facet_start + (j + 1) / points_per_facet * (facet_end - facet_start)
                
                # Position based on facet geometry
                y = s * local_half_beam
                # Rise from keel to above waterline
                z_range = depth + draft * 0.2
                z = -draft + s * z_range
                
                # Hard edge at facet boundaries (end of each facet)
                is_boundary = (j == points_per_facet - 1)
                edge_type = EdgeType.HARD if is_boundary else EdgeType.SMOOTH
                
                points.append(SectionPoint(
                    position=Point3D(x=x, y=y, z=z),
                    edge_type=edge_type,
                    is_chine=is_boundary,
                    feature_id=f"facet_{facet_idx}",
                ))
        
        station = 1.0 - (t * self._config.region_length)
        
        return HullSection(
            station=station,
            points=points,
        )
    
    # =========================================================================
    # WAVE-PIERCING BOW
    # =========================================================================
    
    def _generate_wave_piercing_bow(self, num_sections: int) -> BowGeometry:
        """
        Generate wave-piercing bow with very fine entry.
        
        Characteristics:
        - Extremely fine waterline entry (< 15°)
        - Often with tumblehome (inward lean) at bow
        - Deep forefoot
        - Forward-raked stem
        """
        sections = []
        panel_edges = []
        
        dims = self._definition.dimensions
        lwl = dims.lwl
        bow_length = lwl * self._config.region_length
        
        # Wave piercer has forward-raked stem
        stem_curve = self._generate_wave_piercing_stem_curve()
        
        for i in range(num_sections):
            t = i / (num_sections - 1) if num_sections > 1 else 0
            x = t * bow_length
            
            # Very gradual beam growth (t^2 for fine entry)
            local_half_beam = (t ** 2) * dims.beam_max * 0.35
            
            section = self._generate_wave_piercing_section(x, t, local_half_beam)
            sections.append(section)
        
        # Wave piercer has hard stem edge
        if len(stem_curve) >= 2:
            panel_edges.append(BowPanelEdge(
                start_point=stem_curve[0],
                end_point=stem_curve[-1],
                is_hard=True,
                feature_id="wave_piercing_stem",
            ))
        
        return BowGeometry(
            sections=sections,
            stem_curve=stem_curve,
            panel_edges=panel_edges,
            waterline_entry=self._extract_waterline_entry(sections),
        )
    
    def _generate_wave_piercing_section(
        self,
        x: float,
        t: float,
        local_half_beam: float,
    ) -> HullSection:
        """Generate wave-piercing bow section with tumblehome."""
        points = []
        dims = self._definition.dimensions
        draft = dims.draft
        depth = dims.depth
        
        num_points = 10
        tumblehome_deg = self._config.flare_deg  # Negative = tumblehome
        
        for j in range(num_points):
            s = j / (num_points - 1)
            
            # Fine V-section
            y_base = s * local_half_beam
            z = -draft + s * (depth + draft)
            
            # Apply tumblehome above waterline
            if z > 0 and tumblehome_deg < 0:
                tumblehome_offset = z * math.tan(math.radians(abs(tumblehome_deg)))
                y = max(0, y_base - tumblehome_offset)
            else:
                y = y_base
            
            # Only keel is hard edge (smooth wave-piercing form)
            edge_type = EdgeType.HARD if j == 0 else EdgeType.SMOOTH
            
            points.append(SectionPoint(
                position=Point3D(x=x, y=y, z=z),
                edge_type=edge_type,
                is_keel=(j == 0),
                feature_id="wave_piercing",
            ))
        
        station = 1.0 - (t * self._config.region_length)
        
        return HullSection(
            station=station,
            points=points,
        )
    
    def _generate_wave_piercing_stem_curve(self) -> List[Point3D]:
        """Generate forward-raked stem curve for wave-piercing bow."""
        dims = self._definition.dimensions
        points = []
        
        rake_deg = self._config.stem_rake_deg
        rake_rad = math.radians(abs(rake_deg))
        is_forward = rake_deg < 0
        
        num_points = 6
        
        for i in range(num_points):
            t = i / (num_points - 1)
            z = -dims.draft + t * (dims.depth + dims.draft)
            
            # Forward rake (negative X as we go up above waterline)
            if z > 0 and is_forward:
                x = -z * math.tan(rake_rad)
            elif z > 0:
                x = z * math.tan(rake_rad)
            else:
                x = 0
            
            points.append(Point3D(x=x, y=0, z=z))
        
        return points
    
    # =========================================================================
    # TRADITIONAL BOW
    # =========================================================================
    
    def _generate_traditional_bow(self, num_sections: int) -> BowGeometry:
        """
        Generate traditional smooth lofted bow.
        
        This maintains backward compatibility with existing generation.
        """
        sections = []
        
        dims = self._definition.dimensions
        lwl = dims.lwl
        bow_length = lwl * self._config.region_length
        
        stem_curve = self._generate_stem_curve()
        
        for i in range(num_sections):
            t = i / (num_sections - 1) if num_sections > 1 else 0
            x = t * bow_length
            local_half_beam = t * dims.beam_max * 0.5
            
            section = self._generate_traditional_section(x, t, local_half_beam)
            sections.append(section)
        
        return BowGeometry(
            sections=sections,
            stem_curve=stem_curve,
            panel_edges=[],  # No hard edges for traditional
            waterline_entry=self._extract_waterline_entry(sections),
        )
    
    def _generate_traditional_section(
        self,
        x: float,
        t: float,
        local_half_beam: float,
    ) -> HullSection:
        """Generate traditional smooth bow section."""
        points = []
        dims = self._definition.dimensions
        draft = dims.draft
        depth = dims.depth
        
        num_points = 12
        
        for j in range(num_points):
            s = j / (num_points - 1)
            
            # Smooth elliptical section
            y = s * local_half_beam
            # Parabolic rise from keel
            z = -draft + (s ** 0.7) * (depth + draft)
            
            # Only keel might be hard, rest is smooth
            edge_type = EdgeType.SMOOTH
            
            points.append(SectionPoint(
                position=Point3D(x=x, y=y, z=z),
                edge_type=edge_type,
                is_keel=(j == 0),
            ))
        
        station = 1.0 - (t * self._config.region_length)
        
        return HullSection(
            station=station,
            points=points,
        )
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _generate_stem_curve(self) -> List[Point3D]:
        """Generate default raked stem curve."""
        dims = self._definition.dimensions
        rake_rad = math.radians(self._config.stem_rake_deg)
        points = []
        
        num_points = 5
        for i in range(num_points):
            t = i / (num_points - 1)
            z = -dims.draft + t * (dims.depth + dims.draft)
            # Aft rake (positive X as we go up)
            x = max(0, z * math.tan(rake_rad)) if z > 0 else 0
            points.append(Point3D(x=x, y=0, z=z))
        
        return points
    
    def _extract_waterline_entry(self, sections: List[HullSection]) -> List[Point3D]:
        """Extract waterline curve from sections."""
        waterline = []
        
        for section in sections:
            if not section.points:
                continue
            # Find point closest to z=0
            wl_point = min(section.points, key=lambda p: abs(p.position.z))
            waterline.append(wl_point.position)
        
        return waterline

