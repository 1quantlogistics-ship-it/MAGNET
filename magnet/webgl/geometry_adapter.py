"""
magnet/webgl/geometry_adapter.py - HullGeometry → HullGeometryData Adapter

Converts kernel HullGeometry (from design language compilation) to
webgl HullGeometryData (for 3D visualization and GLB export).

This enables sketch → compile → GLB pipeline (Issue 1.1).

Reference: MAGNET_Critical_Corrections.md Part I Issue 1.1
"""

from typing import List, Optional
from dataclasses import dataclass

from magnet.hull_gen.geometry import HullGeometry, HullSection as KernelSection, Point3D
from magnet.webgl.interfaces import HullGeometryData, HullSection as WebGLSection, Point3D as WebGLPoint3D


__all__ = [
    'hull_geometry_to_webgl',
    'GeometryAdapter',
]


# =============================================================================
# Type Conversions
# =============================================================================

def convert_point3d(point: Point3D) -> WebGLPoint3D:
    """Convert kernel Point3D to webgl Point3D."""
    return WebGLPoint3D(x=point.x, y=point.y, z=point.z)


def convert_section(section: KernelSection, loa: float) -> WebGLSection:
    """
    Convert kernel HullSection to webgl HullSection.
    
    Args:
        section: Kernel section with absolute x_position
        loa: Length overall for computing station fraction
    
    Returns:
        WebGL section with station (x position) and points
    
    Note: WebGL HullSection uses 'station' field for x position directly.
    """
    # Convert points to WebGL Point3D
    points = [convert_point3d(p) for p in section.points]
    
    return WebGLSection(
        station=section.x_position,  # WebGL uses station for x position
        points=points,
        is_closed=False,  # Hull sections are typically not closed
    )


# =============================================================================
# Main Adapter
# =============================================================================

class GeometryAdapter:
    """
    Adapter: kernel HullGeometry → webgl HullGeometryData.
    
    Converts from design language compiled geometry to 3D visualization format.
    Enables sketch → DSL → HullGeometry → HullGeometryData → GLB pipeline.
    """
    
    @staticmethod
    def convert(
        hull_geometry: HullGeometry,
        design_id: str = "design",
        version_id: str = "v1",
    ) -> HullGeometryData:
        """
        Convert HullGeometry to HullGeometryData.
        
        Args:
            hull_geometry: Compiled hull geometry from kernel
            design_id: Design identifier
            version_id: Version identifier
        
        Returns:
            HullGeometryData ready for tessellation and GLB export
        """
        # Extract LOA from geometry
        loa = GeometryAdapter._extract_loa(hull_geometry)
        
        # Convert sections
        sections = [
            convert_section(s, loa)
            for s in hull_geometry.sections
        ]
        
        # Convert key curves
        keel_profile = [convert_point3d(p) for p in hull_geometry.keel_profile]
        stem_profile = [convert_point3d(p) for p in hull_geometry.stem_profile]
        
        chine_curve = None
        if hull_geometry.chine_curve:
            chine_curve = [convert_point3d(p) for p in hull_geometry.chine_curve]
        
        sheer_curve = None
        if hull_geometry.deck_edge:
            sheer_curve = [convert_point3d(p) for p in hull_geometry.deck_edge]
        
        transom_outline = None
        if hull_geometry.transom_outline:
            transom_outline = [convert_point3d(p) for p in hull_geometry.transom_outline]
        
        # Extract principal dimensions
        beam = GeometryAdapter._extract_beam(hull_geometry)
        draft = GeometryAdapter._extract_draft(hull_geometry)
        lwl = loa * 0.95  # Approximate LWL as 95% of LOA
        
        return HullGeometryData(
            design_id=design_id,
            version_id=version_id,
            sections=sections,
            keel_profile=keel_profile,
            stem_profile=stem_profile,
            chine_curve=chine_curve,
            sheer_curve=sheer_curve,
            transom_outline=transom_outline,
            loa=loa,
            lwl=lwl,
            beam=beam,
            draft=draft,
            volume=hull_geometry.volume,
            wetted_surface=hull_geometry.wetted_surface,
            waterplane_area=hull_geometry.waterplane_area,
        )
    
    @staticmethod
    def _extract_loa(hull_geometry: HullGeometry) -> float:
        """Extract LOA from hull geometry."""
        if not hull_geometry.sections:
            return 0.0
        
        # LOA is the distance from first to last section
        x_positions = [s.x_position for s in hull_geometry.sections]
        return max(x_positions) - min(x_positions)
    
    @staticmethod
    def _extract_beam(hull_geometry: HullGeometry) -> float:
        """Extract beam from hull geometry."""
        if not hull_geometry.sections:
            return 0.0
        
        # Beam is the maximum y-coordinate across all sections
        max_y = 0.0
        for section in hull_geometry.sections:
            for point in section.points:
                max_y = max(max_y, abs(point.y))
        
        return 2.0 * max_y  # Beam is double the max offset (port + starboard)
    
    @staticmethod
    def _extract_draft(hull_geometry: HullGeometry) -> float:
        """Extract draft from hull geometry."""
        if not hull_geometry.sections:
            return 0.0
        
        # Draft is the minimum (most negative) z-coordinate
        min_z = 0.0
        for section in hull_geometry.sections:
            for point in section.points:
                min_z = min(min_z, point.z)
        
        return abs(min_z)


# =============================================================================
# Convenience Function
# =============================================================================

def hull_geometry_to_webgl(
    hull_geometry: HullGeometry,
    design_id: str = "design",
    version_id: str = "v1",
) -> HullGeometryData:
    """
    Convert HullGeometry to HullGeometryData (convenience function).
    
    This is the primary entry point for the sketch → GLB pipeline.
    
    Example:
        >>> from magnet.kernel.program_executor import execute_program
        >>> from magnet.webgl.geometry_adapter import hull_geometry_to_webgl
        >>> from magnet.webgl.geometry_pipeline import HullGeometryPipeline
        >>> from magnet.webgl.exporter import Exporter, ExportFormat
        >>>
        >>> # Execute design program
        >>> result = execute_program(dsl_program)
        >>> 
        >>> # Convert to WebGL format
        >>> webgl_geom = hull_geometry_to_webgl(result.geometry)
        >>>
        >>> # Tessellate and export
        >>> pipeline = HullGeometryPipeline(hull_geom=webgl_geom)
        >>> mesh = pipeline.tessellate()
        >>> 
        >>> exporter = Exporter()
        >>> glb_bytes = exporter.export(mesh, ExportFormat.GLB)
    
    Args:
        hull_geometry: Compiled hull geometry from kernel
        design_id: Design identifier
        version_id: Version identifier
    
    Returns:
        HullGeometryData ready for 3D visualization
    """
    return GeometryAdapter.convert(hull_geometry, design_id, version_id)

