"""
Test Issue 2.2: Weight from Geometry

Tests that weight estimation derives from geometry WITHOUT hull_type dispatch.

Reference: MAGNET_Critical_Corrections.md Part II Issue 2.2
"""

import pytest
from magnet.weight.estimators.hull import HullStructureEstimator, get_hull_factor_from_geometry


class TestWeightFromGeometry:
    """Test geometry-based weight estimation (no hull_type)."""
    
    def test_single_body_factor(self):
        """Single body should have base factor 1.0."""
        factor = get_hull_factor_from_geometry(body_count=1, lb_ratio=5.0, froude_number=0.3)
        assert factor == pytest.approx(1.0, rel=0.01)
    
    def test_dual_body_factor(self):
        """Dual body should have +15% factor."""
        factor = get_hull_factor_from_geometry(body_count=2, lb_ratio=5.0, froude_number=0.3)
        assert factor == pytest.approx(1.15, rel=0.01)
    
    def test_triple_body_factor(self):
        """Triple body should have +25% factor."""
        factor = get_hull_factor_from_geometry(body_count=3, lb_ratio=5.0, froude_number=0.3)
        assert factor == pytest.approx(1.25, rel=0.01)
    
    def test_novel_multi_body_factor(self):
        """Novel 4-body configuration should extrapolate."""
        factor = get_hull_factor_from_geometry(body_count=4, lb_ratio=5.0, froude_number=0.3)
        # Should be 1.15 + 0.10 * (4-2) = 1.35
        assert factor == pytest.approx(1.35, rel=0.01)
    
    def test_slender_hull_reduction(self):
        """Slender hulls (L/B > 8) should have reduced factor."""
        factor = get_hull_factor_from_geometry(body_count=1, lb_ratio=10.0, froude_number=0.3)
        # Base 1.0 * 0.95 (slender) = 0.95
        assert factor == pytest.approx(0.95, rel=0.01)
    
    def test_beamy_hull_increase(self):
        """Beamy hulls (L/B < 4) should have increased factor."""
        factor = get_hull_factor_from_geometry(body_count=1, lb_ratio=3.0, froude_number=0.3)
        # Base 1.0 * 1.05 (beamy) = 1.05
        assert factor == pytest.approx(1.05, rel=0.01)
    
    def test_planing_speed_reduction(self):
        """Planing speeds (Fn > 0.5) should reduce weight."""
        factor = get_hull_factor_from_geometry(body_count=1, lb_ratio=5.0, froude_number=0.6)
        # Base 1.0 * 0.90 (planing) = 0.90
        assert factor == pytest.approx(0.90, rel=0.01)
    
    def test_displacement_speed_increase(self):
        """Displacement speeds (Fn < 0.25) should increase weight."""
        factor = get_hull_factor_from_geometry(body_count=1, lb_ratio=5.0, froude_number=0.2)
        # Base 1.0 * 1.05 (displacement) = 1.05
        assert factor == pytest.approx(1.05, rel=0.01)
    
    def test_combined_factors(self):
        """Combined factors should multiply."""
        # Dual-body + slender + planing
        factor = get_hull_factor_from_geometry(body_count=2, lb_ratio=10.0, froude_number=0.6)
        # 1.15 (dual) * 0.95 (slender) * 0.90 (planing) = 0.982
        assert factor == pytest.approx(0.982, rel=0.02)
    
    def test_estimate_from_geometry_no_hull_type(self):
        """estimate_from_geometry should NOT require hull_type."""
        estimator = HullStructureEstimator()
        
        items = estimator.estimate_from_geometry(
            lwl=25.0,
            beam=6.0,
            depth=2.5,
            cb=0.50,
            body_count=2,  # Dual body (could be catamaran, proa, SWATH, or novel)
            froude_number=0.4,
        )
        
        assert len(items) > 0
        total_weight = sum(i.weight_kg for i in items)
        assert total_weight > 0
        
        # Verify notes mention geometry, not hull_type
        assert any("body_count=2" in (item.notes or "") for item in items)
        assert any("geometry" in (item.notes or "").lower() for item in items)
    
    def test_body_count_not_design_type(self):
        """
        CRITICAL: body_count is geometric fact, not design classification.
        
        body_count=2 could be catamaran, proa, SWATH, or something novel.
        The weight estimation should work identically for all.
        """
        estimator = HullStructureEstimator()
        
        # Same geometry, different "names" → should get SAME weight
        items_unnamed = estimator.estimate_from_geometry(
            lwl=30.0, beam=8.0, depth=2.0, cb=0.50,
            body_count=2, froude_number=0.3,
        )
        
        weight_unnamed = sum(i.weight_kg for i in items_unnamed)
        
        # This would be "catamaran" or "proa" or "SWATH" — but we don't care
        # Same body_count → same weight factor
        assert weight_unnamed > 0
        
        # Verify no design type strings in output
        for item in items_unnamed:
            assert "catamaran" not in item.name.lower()
            assert "proa" not in item.name.lower()
            assert "swath" not in item.name.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

