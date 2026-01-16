"""
Test Issue 2.3: Scantlings from Geometry (Simplified)

Verifies that scantling calculations use Froude number instead of hull_type.

Reference: MAGNET_Critical_Corrections.md Part II Issue 2.3
"""

import pytest
import inspect


class TestScantlingsNoHullType:
    """Verify hull_type removed from scantlings."""
    
    def test_no_hull_type_in_slamming_calculation(self):
        """CRITICAL: Slamming pressure should NOT use hull_type lookup."""
        from magnet.structural.scantlings import ScantlingCalculator
        
        # Get source code
        source = inspect.getsource(ScantlingCalculator._calculate_slamming_pressure)
        
        # Should NOT contain hull_type state lookup
        # Old code was: hull_type = self.state.get("hull.hull_type", "planing")
        assert 'hull.hull_type' not in source, \
            "Slamming calculation still uses hull_type — should use Froude number instead"
        
        # Should contain Froude number calculation
        assert 'froude' in source.lower() or 'fn' in source.lower(), \
            "Slamming calculation should use Froude number for speed regime"
    
    def test_froude_number_comment_present(self):
        """Verify explanatory comment is present."""
        from magnet.structural.scantlings import ScantlingCalculator
        
        source = inspect.getsource(ScantlingCalculator._calculate_slamming_pressure)
        
        # Should have explanatory comment about physics vs design type
        assert 'PHYSICS' in source.upper() or 'physics' in source.lower(), \
            "Should explain that Froude number is physics, not design type"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

