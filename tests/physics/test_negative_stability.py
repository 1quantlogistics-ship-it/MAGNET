"""
TASK-023: Negative GM Handling — Warn, Don't Crash

Tests that negative GM returns valid results with warnings instead of crashing.
"""

import pytest
from magnet.physics.geometry_hydrostatics import (
    HydrostaticsResult,
    compute_hydrostatics_from_geometry,
)


class TestHydrostaticsResultStability:
    """Test stability field and warnings in HydrostaticsResult."""

    def test_positive_gm_is_stable(self):
        """Positive GM results in stable=True."""
        result = HydrostaticsResult(
            displacement_m3=100.0,
            displacement_kg=102500.0,
            lcb_m=10.0,
            vcb_m=1.0,
            tcb_m=0.0,
            kb_m=1.0,
            bm_transverse_m=3.0,
            bm_longitudinal_m=50.0,
            waterplane_area_m2=50.0,
            waterplane_inertia_transverse_m4=200.0,
            waterplane_inertia_longitudinal_m4=5000.0,
            wetted_surface_m2=150.0,
            method="single_body",
            body_count=1,
            gm_transverse_m=1.5,  # Positive GM
        )
        
        assert result.stable is True
        # Should have no warnings about instability
        assert not any("unstable" in w.lower() for w in result.warnings)

    def test_negative_gm_is_unstable(self):
        """Negative GM results in stable=False with warning."""
        result = HydrostaticsResult(
            displacement_m3=100.0,
            displacement_kg=102500.0,
            lcb_m=10.0,
            vcb_m=1.0,
            tcb_m=0.0,
            kb_m=1.0,
            bm_transverse_m=1.0,  # Low BM
            bm_longitudinal_m=50.0,
            waterplane_area_m2=50.0,
            waterplane_inertia_transverse_m4=200.0,
            waterplane_inertia_longitudinal_m4=5000.0,
            wetted_surface_m2=150.0,
            method="single_body",
            body_count=1,
            gm_transverse_m=-0.3,  # Negative GM
        )
        
        assert result.stable is False
        assert len(result.warnings) > 0
        assert any("unstable" in w.lower() for w in result.warnings)
        assert any("-0.3" in w for w in result.warnings)

    def test_low_gm_has_warning(self):
        """Low but positive GM has warning about minimum recommended."""
        result = HydrostaticsResult(
            displacement_m3=100.0,
            displacement_kg=102500.0,
            lcb_m=10.0,
            vcb_m=1.0,
            tcb_m=0.0,
            kb_m=1.0,
            bm_transverse_m=2.0,
            bm_longitudinal_m=50.0,
            waterplane_area_m2=50.0,
            waterplane_inertia_transverse_m4=200.0,
            waterplane_inertia_longitudinal_m4=5000.0,
            wetted_surface_m2=150.0,
            method="single_body",
            body_count=1,
            gm_transverse_m=0.3,  # Low but positive GM
        )
        
        assert result.stable is True  # Still stable, just low
        assert len(result.warnings) > 0
        assert any("low stability" in w.lower() for w in result.warnings)
        assert any("0.5m" in w for w in result.warnings)

    def test_zero_gm_has_warning(self):
        """Zero GM gets a low stability warning."""
        result = HydrostaticsResult(
            displacement_m3=100.0,
            displacement_kg=102500.0,
            lcb_m=10.0,
            vcb_m=1.0,
            tcb_m=0.0,
            kb_m=1.0,
            bm_transverse_m=1.5,
            bm_longitudinal_m=50.0,
            waterplane_area_m2=50.0,
            waterplane_inertia_transverse_m4=200.0,
            waterplane_inertia_longitudinal_m4=5000.0,
            wetted_surface_m2=150.0,
            method="single_body",
            body_count=1,
            gm_transverse_m=0.0,  # Zero GM
        )
        
        # Zero GM is neutral stability - gets warning but not marked unstable
        # (Only negative GM is truly unstable)
        assert result.stable is True  # Not negative, so technically stable
        assert len(result.warnings) > 0
        assert any("low stability" in w.lower() for w in result.warnings)

    def test_no_gm_no_stability_warning(self):
        """When GM not provided, no stability warnings."""
        result = HydrostaticsResult(
            displacement_m3=100.0,
            displacement_kg=102500.0,
            lcb_m=10.0,
            vcb_m=1.0,
            tcb_m=0.0,
            kb_m=1.0,
            bm_transverse_m=2.0,
            bm_longitudinal_m=50.0,
            waterplane_area_m2=50.0,
            waterplane_inertia_transverse_m4=200.0,
            waterplane_inertia_longitudinal_m4=5000.0,
            wetted_surface_m2=150.0,
            method="single_body",
            body_count=1,
            gm_transverse_m=None,  # GM not computed
        )
        
        assert result.stable is True  # Default
        assert len(result.warnings) == 0


class TestWarningMessages:
    """Test that warning messages are user-friendly."""

    def test_negative_gm_warning_includes_value(self):
        """Negative GM warning includes the actual GM value."""
        result = HydrostaticsResult(
            displacement_m3=100.0,
            displacement_kg=102500.0,
            lcb_m=10.0,
            vcb_m=1.0,
            tcb_m=0.0,
            kb_m=1.0,
            bm_transverse_m=1.0,
            bm_longitudinal_m=50.0,
            waterplane_area_m2=50.0,
            waterplane_inertia_transverse_m4=200.0,
            waterplane_inertia_longitudinal_m4=5000.0,
            wetted_surface_m2=150.0,
            method="single_body",
            body_count=1,
            gm_transverse_m=-0.45,
        )
        
        # Should include the actual value
        assert any("-0.45" in w for w in result.warnings)

    def test_negative_gm_warning_includes_suggestion(self):
        """Negative GM warning includes actionable suggestion."""
        result = HydrostaticsResult(
            displacement_m3=100.0,
            displacement_kg=102500.0,
            lcb_m=10.0,
            vcb_m=1.0,
            tcb_m=0.0,
            kb_m=1.0,
            bm_transverse_m=1.0,
            bm_longitudinal_m=50.0,
            waterplane_area_m2=50.0,
            waterplane_inertia_transverse_m4=200.0,
            waterplane_inertia_longitudinal_m4=5000.0,
            wetted_surface_m2=150.0,
            method="single_body",
            body_count=1,
            gm_transverse_m=-0.3,
        )
        
        # Should include suggestion
        warning = result.warnings[0]
        assert "beam" in warning.lower() or "vcg" in warning.lower()


class TestNoCrashOnNegativeGM:
    """Test that negative GM doesn't cause crashes."""

    def test_no_sqrt_crash(self):
        """Creating result with negative GM doesn't crash."""
        # This should not raise any exception
        try:
            result = HydrostaticsResult(
                displacement_m3=100.0,
                displacement_kg=102500.0,
                lcb_m=10.0,
                vcb_m=1.0,
                tcb_m=0.0,
                kb_m=1.0,
                bm_transverse_m=0.5,
                bm_longitudinal_m=50.0,
                waterplane_area_m2=50.0,
                waterplane_inertia_transverse_m4=200.0,
                waterplane_inertia_longitudinal_m4=5000.0,
                wetted_surface_m2=150.0,
                method="single_body",
                body_count=1,
                gm_transverse_m=-1.0,  # Very negative GM
            )
            # Should succeed
            assert result is not None
            assert result.gm_transverse_m == -1.0
        except Exception as e:
            pytest.fail(f"Creating result with negative GM crashed: {e}")

    def test_result_usable_with_negative_gm(self):
        """Result with negative GM can be used normally."""
        result = HydrostaticsResult(
            displacement_m3=100.0,
            displacement_kg=102500.0,
            lcb_m=10.0,
            vcb_m=1.0,
            tcb_m=0.0,
            kb_m=1.0,
            bm_transverse_m=0.5,
            bm_longitudinal_m=50.0,
            waterplane_area_m2=50.0,
            waterplane_inertia_transverse_m4=200.0,
            waterplane_inertia_longitudinal_m4=5000.0,
            wetted_surface_m2=150.0,
            method="single_body",
            body_count=1,
            gm_transverse_m=-0.5,
        )
        
        # All fields should be accessible
        assert result.displacement_m3 == 100.0
        assert result.gm_transverse_m == -0.5
        assert result.stable is False
        assert len(result.warnings) > 0
