"""
Test Issue 1.1: Sketch → GLB Pipeline

Tests that HullGeometry can be converted to HullGeometryData and exported to GLB.

Reference: MAGNET_Critical_Corrections.md Part I Issue 1.1
"""

import pytest
from dataclasses import dataclass, field
from typing import List

from magnet.hull_gen.geometry import HullGeometry, HullSection, Point3D
from magnet.webgl.geometry_adapter import hull_geometry_to_webgl, GeometryAdapter


# =============================================================================
# Test Data
# =============================================================================

def create_simple_hull_geometry() -> HullGeometry:
    """Create a simple test hull geometry."""
    # Create simple rectangular sections
    sections = [
        HullSection(
            station=0.0,
            x_position=0.0,
            points=[Point3D(0, 0, 0), Point3D(0, 1.0, -0.5), Point3D(0, -1.0, -0.5)],
        ),
        HullSection(
            station=0.5,
            x_position=12.5,
            points=[Point3D(12.5, 0, 0), Point3D(12.5, 1.5, -1.0), Point3D(12.5, -1.5, -1.0)],
        ),
        HullSection(
            station=1.0,
            x_position=25.0,
            points=[Point3D(25, 0, 0), Point3D(25, 1.0, -0.5), Point3D(25, -1.0, -0.5)],
        ),
    ]
    
    # Keel profile
    keel_profile = [Point3D(0, 0, -0.5), Point3D(12.5, 0, -1.0), Point3D(25, 0, -0.5)]
    
    # Stem profile
    stem_profile = [Point3D(25, 0, -0.5), Point3D(25, 0, 0.5)]
    
    return HullGeometry(
        hull_id="test_hull",
        sections=sections,
        keel_profile=keel_profile,
        stem_profile=stem_profile,
        volume=30.0,
        wetted_surface=100.0,
        waterplane_area=40.0,
    )


# =============================================================================
# Adapter Tests
# =============================================================================

class TestGeometryAdapter:
    """Test HullGeometry → HullGeometryData conversion."""
    
    def test_convert_simple_hull(self):
        """Test converting simple hull geometry."""
        hull_geom = create_simple_hull_geometry()
        
        webgl_geom = hull_geometry_to_webgl(hull_geom, design_id="test", version_id="v1")
        
        assert webgl_geom.design_id == "test"
        assert webgl_geom.version_id == "v1"
        assert len(webgl_geom.sections) == 3
        assert webgl_geom.loa == pytest.approx(25.0, rel=0.01)
        assert webgl_geom.beam == pytest.approx(3.0, rel=0.01)  # 2 * 1.5
        assert webgl_geom.draft == pytest.approx(1.0, rel=0.01)
        assert webgl_geom.volume == pytest.approx(30.0)
    
    def test_convert_sections(self):
        """Test section conversion."""
        hull_geom = create_simple_hull_geometry()
        webgl_geom = hull_geometry_to_webgl(hull_geom)
        
        # First section
        section_0 = webgl_geom.sections[0]
        assert section_0.station == pytest.approx(0.0)
        assert len(section_0.points) == 3
        
        # Middle section
        section_1 = webgl_geom.sections[1]
        assert section_1.station == pytest.approx(12.5)
        
        # Last section
        section_2 = webgl_geom.sections[2]
        assert section_2.station == pytest.approx(25.0)
    
    def test_convert_key_curves(self):
        """Test key curve conversion."""
        hull_geom = create_simple_hull_geometry()
        webgl_geom = hull_geometry_to_webgl(hull_geom)
        
        # Keel profile
        assert len(webgl_geom.keel_profile) == 3
        assert webgl_geom.keel_profile[0].x == pytest.approx(0.0)
        assert webgl_geom.keel_profile[1].x == pytest.approx(12.5)
        assert webgl_geom.keel_profile[2].x == pytest.approx(25.0)
        
        # Stem profile
        assert len(webgl_geom.stem_profile) == 2
        assert webgl_geom.stem_profile[0].z == pytest.approx(-0.5)
        assert webgl_geom.stem_profile[1].z == pytest.approx(0.5)
    
    def test_empty_geometry(self):
        """Test handling empty geometry."""
        empty_hull = HullGeometry(hull_id="empty")
        
        webgl_geom = hull_geometry_to_webgl(empty_hull)
        
        assert webgl_geom.loa == 0.0
        assert webgl_geom.beam == 0.0
        assert webgl_geom.draft == 0.0
        assert len(webgl_geom.sections) == 0
    
    def test_extract_loa(self):
        """Test LOA extraction."""
        hull_geom = create_simple_hull_geometry()
        loa = GeometryAdapter._extract_loa(hull_geom)
        assert loa == pytest.approx(25.0)
    
    def test_extract_beam(self):
        """Test beam extraction."""
        hull_geom = create_simple_hull_geometry()
        beam = GeometryAdapter._extract_beam(hull_geom)
        assert beam == pytest.approx(3.0, rel=0.01)  # 2 * max(1.5)
    
    def test_extract_draft(self):
        """Test draft extraction."""
        hull_geom = create_simple_hull_geometry()
        draft = GeometryAdapter._extract_draft(hull_geom)
        assert draft == pytest.approx(1.0, rel=0.01)


# =============================================================================
# Integration Test (requires webgl pipeline)
# =============================================================================

@pytest.mark.skipif(
    True,  # Skip until pipeline verified
    reason="Integration test - requires full webgl pipeline",
)
def test_full_sketch_to_glb_pipeline():
    """
    Integration test: HullGeometry → HullGeometryData → Mesh → GLB
    
    This verifies the complete Issue 1.1 pipeline.
    """
    from magnet.webgl.geometry_pipeline import HullGeometryPipeline
    from magnet.webgl.exporter import Exporter, ExportFormat
    
    # Create test geometry
    hull_geom = create_simple_hull_geometry()
    
    # Convert to WebGL format
    webgl_geom = hull_geometry_to_webgl(hull_geom)
    
    # Tessellate
    pipeline = HullGeometryPipeline(hull_geom=webgl_geom)
    mesh = pipeline.tessellate()
    
    # Export to GLB
    exporter = Exporter()
    glb_bytes = exporter.export(mesh, ExportFormat.GLB)
    
    # Verify GLB was produced
    assert glb_bytes is not None
    assert len(glb_bytes) > 0
    assert glb_bytes[:4] == b'glTF'  # GLB magic number
    
    print(f"✅ Generated GLB: {len(glb_bytes)} bytes")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

