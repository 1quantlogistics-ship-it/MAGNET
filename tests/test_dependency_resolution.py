"""
Test Q9: Dependency Resolution with Geometry Aliases

Tests that CascadeExecutor can resolve parameters from both:
- Direct state keys (old path)
- Geometry extraction (new path)

Reference: MAGNET_Critical_Corrections.md Part III Q9
"""

import pytest
from magnet.dependencies.graph import resolve_parameter


class TestDependencyResolution:
    """Test parameter resolution with geometry aliases."""
    
    def test_direct_lookup_old_path(self):
        """Old path: Parameter directly in state."""
        state = {
            "hull": {
                "beam": 8.0,
                "loa": 25.0,
            }
        }
        
        found, value, error = resolve_parameter("hull.beam", state)
        
        assert found
        assert value == 8.0
        assert error is None
    
    def test_geometry_extraction_new_path(self):
        """New path: Extract from geometry dict."""
        state = {
            "hull": {
                "geometry": {
                    "beam": 8.0,
                    "loa": 25.0,
                }
            }
        }
        
        found, value, error = resolve_parameter("hull.beam", state)
        
        assert found
        assert value == 8.0
        assert error is None
    
    def test_geometry_object_extraction(self):
        """New path: Extract from Hull Geometry object."""
        from types import SimpleNamespace
        
        geometry = SimpleNamespace(beam=8.0, loa=25.0, draft=1.5)
        state = {
            "hull": {
                "geometry": geometry
            }
        }
        
        found, value, error = resolve_parameter("hull.beam", state)
        
        assert found
        assert value == 8.0
        assert error is None
    
    def test_missing_parameter_fails_loud(self):
        """Missing parameter should fail with clear error."""
        state = {
            "hull": {}
        }
        
        found, value, error = resolve_parameter("hull.beam", state)
        
        assert not found
        assert value is None
        assert "not found" in error.lower()
        assert "hull.beam" in error
    
    def test_nested_parameter_resolution(self):
        """Non-hull nested parameters should work."""
        state = {
            "mission": {
                "max_speed_kts": 35.0
            }
        }
        
        found, value, error = resolve_parameter("mission.max_speed_kts", state)
        
        assert found
        assert value == 35.0
        assert error is None
    
    def test_prefers_direct_over_geometry(self):
        """If both exist, prefer direct value."""
        state = {
            "hull": {
                "beam": 8.0,  # Direct
                "geometry": {
                    "beam": 7.5  # Geometry (should not be used)
                }
            }
        }
        
        found, value, error = resolve_parameter("hull.beam", state)
        
        assert found
        assert value == 8.0  # Prefer direct


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

