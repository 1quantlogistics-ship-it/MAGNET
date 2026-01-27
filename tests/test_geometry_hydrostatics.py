"""
Test Issue 2.1: Geometry-Based Hydrostatics

Tests that hydrostatics derive from geometry WITHOUT hull_type dispatch.

Reference: MAGNET_Critical_Corrections.md Part II Issue 2.1
"""

import pytest
from magnet.hull_gen.geometry import HullGeometry, HullSection, Point3D
from magnet.physics.geometry_hydrostatics import (
    compute_hydrostatics_from_geometry,
    HydrostaticsResult,
)


def create_simple_box_hull() -> HullGeometry:
    """Create simple rectangular hull for testing."""
    sections = [
        HullSection(
            station=0.0,
            x_position=0.0,
            # MAGNET standard: baseline z=0 at keel; waterline at z=draft.
            points=[Point3D(0, 0, 0), Point3D(0, 2.0, 0), Point3D(0, 2.0, 1.5), Point3D(0, -2.0, 1.5), Point3D(0, -2.0, 0)],
        ),
        HullSection(
            station=1.0,
            x_position=20.0,
            points=[Point3D(20, 0, 0), Point3D(20, 2.0, 0), Point3D(20, 2.0, 1.5), Point3D(20, -2.0, 1.5), Point3D(20, -2.0, 0)],
        ),
    ]
    
    return HullGeometry(hull_id="test", sections=sections)


class TestGeometryHydrostatics:
    """Test geometry-based hydrostatics (no hull_type)."""
    
    def test_compute_from_geometry(self):
        """Test basic hydrostatics computation."""
        hull = create_simple_box_hull()
        
        result = compute_hydrostatics_from_geometry(hull, draft=1.0, vcg=0.5)
        
        assert result.method == "single_body"
        assert result.body_count == 1
        assert result.displacement_m3 > 0
        assert result.bm_transverse_m > 0
        assert result.gm_transverse_m is not None
    
    def test_no_hull_type_in_signature(self):
        """CRITICAL: Function must NOT accept hull_type parameter."""
        import inspect
        sig = inspect.signature(compute_hydrostatics_from_geometry)
        param_names = list(sig.parameters.keys())
        
        assert "hull_type" not in param_names
        assert "HullType" not in str(sig)
        assert "HullFamily" not in str(sig)
    
    def test_body_count_is_geometric_fact(self):
        """body_count must be derived from geometry, not passed in."""
        hull = create_simple_box_hull()
        result = compute_hydrostatics_from_geometry(hull, draft=1.0)
        
        # body_count is in RESULT (derived), not INPUT (prescribed)
        assert hasattr(result, 'body_count')
        assert result.body_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

