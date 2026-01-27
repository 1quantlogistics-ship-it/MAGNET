"""
Tests for structural feasibility assessment (advisory only).

Verifies that feasibility warnings are generated but never block validation.
"""

import pytest
from magnet.structural.feasibility import (
    assess_structural_feasibility,
    format_feasibility_report,
    FeasibilityAssessment,
)


def test_conventional_hull_no_warnings():
    """Test that conventional proportions generate no warnings."""
    assessment = assess_structural_feasibility(
        loa=25.0,
        beam=5.0,  # L/B = 5.0 (conventional)
        draft=1.5,  # B/D = 3.33 (conventional)
        depth=2.5,  # Depth/draft = 1.67 (conventional)
    )
    
    assert assessment.overall_feasibility == "good"
    assert len(assessment.warnings) == 0


def test_beamy_hull_generates_warning():
    """Test that very beamy hull generates L/B warning."""
    assessment = assess_structural_feasibility(
        loa=10.0,
        beam=5.0,  # L/B = 2.0 (very beamy)
        draft=1.5,
    )
    
    # Should have warning about low L/B
    lb_warnings = [w for w in assessment.warnings if "L/B ratio" in w.message]
    assert len(lb_warnings) > 0
    assert "beamy" in lb_warnings[0].message.lower()


def test_slender_hull_generates_warning():
    """Test that very slender hull generates L/B warning."""
    assessment = assess_structural_feasibility(
        loa=80.0,
        beam=5.0,  # L/B = 16.0 (very slender)
        draft=1.5,
    )
    
    # Should have warning about high L/B
    lb_warnings = [w for w in assessment.warnings if "L/B ratio" in w.message]
    assert len(lb_warnings) > 0
    assert "slender" in lb_warnings[0].message.lower()


def test_shallow_depth_generates_concern():
    """Test that shallow depth/draft ratio generates concern."""
    assessment = assess_structural_feasibility(
        loa=25.0,
        beam=5.0,
        draft=2.0,
        depth=2.5,  # Depth/draft = 1.25 (low freeboard)
    )
    
    # Should have concern about depth/draft
    depth_warnings = [w for w in assessment.warnings if "Depth/draft" in w.message]
    assert len(depth_warnings) > 0
    assert depth_warnings[0].severity == "concern"


def test_wide_shallow_hull_generates_warnings():
    """Test that wide shallow hull generates multiple warnings."""
    assessment = assess_structural_feasibility(
        loa=20.0,
        beam=10.0,  # Very wide
        draft=1.5,   # B/D = 6.67 (very wide/shallow)
    )
    
    # Should have warnings
    assert len(assessment.warnings) > 0
    assert assessment.overall_feasibility in ["acceptable", "questionable"]


def test_multi_body_narrow_spacing_warning():
    """Test that narrow multi-body spacing generates warning."""
    assessment = assess_structural_feasibility(
        loa=25.0,
        beam=3.0,
        draft=1.5,
        body_count=2,
        hull_spacing=3.0,  # 12% of LOA (narrow)
    )
    
    # Should have warning about narrow spacing
    spacing_warnings = [w for w in assessment.warnings if "spacing" in w.message.lower()]
    assert len(spacing_warnings) > 0


def test_multi_body_wide_spacing_warning():
    """Test that very wide multi-body spacing generates warning."""
    assessment = assess_structural_feasibility(
        loa=25.0,
        beam=2.0,
        draft=1.5,
        body_count=2,
        hull_spacing=15.0,  # 60% of LOA (very wide)
    )
    
    # Should have warning about wide spacing
    spacing_warnings = [w for w in assessment.warnings if "spacing" in w.message.lower()]
    assert len(spacing_warnings) > 0


def test_warnings_are_advisory_not_blocking():
    """
    CRITICAL TEST: Verify warnings never block validation.
    
    Even with extreme proportions, assessment completes successfully.
    """
    # Extreme proportions
    assessment = assess_structural_feasibility(
        loa=5.0,
        beam=10.0,  # L/B = 0.5 (absurd)
        draft=0.5,   # B/D = 20 (absurd)
    )
    
    # Should complete without raising exceptions
    assert assessment is not None
    
    # May have many warnings
    assert len(assessment.warnings) > 0
    
    # But overall assessment is still returned
    assert assessment.overall_feasibility in ["good", "acceptable", "questionable"]


def test_format_feasibility_report():
    """Test that feasibility report formats correctly."""
    assessment = FeasibilityAssessment()
    assessment.add_warning(
        severity="warning",
        category="proportion",
        message="Test warning",
        recommendation="Test recommendation",
    )
    assessment.overall_feasibility = "acceptable"
    assessment.notes.append("Test note")
    
    report = format_feasibility_report(assessment)
    
    assert "Structural Feasibility Assessment" in report
    assert "ACCEPTABLE" in report
    assert "Test warning" in report
    assert "Test recommendation" in report
    assert "advisory" in report.lower()


def test_feasibility_includes_recommendations():
    """Test that warnings include actionable recommendations."""
    assessment = assess_structural_feasibility(
        loa=25.0,
        beam=12.0,  # L/B = 2.08 (beamy)
        draft=1.5,
    )
    
    # Warnings should have recommendations
    for warning in assessment.warnings:
        if warning.severity in ["warning", "concern"]:
            assert warning.recommendation is not None
            assert len(warning.recommendation) > 0


def test_novel_geometry_not_blocked():
    """
    INVARIANT TEST: Novel geometry is never blocked by feasibility.
    
    This is the core principle - structural feasibility is advisory only.
    """
    # Test various novel configurations
    novel_configs = [
        {"loa": 100.0, "beam": 5.0, "draft": 0.5},  # Extreme slenderness
        {"loa": 8.0, "beam": 8.0, "draft": 2.0},    # Nearly square
        {"loa": 25.0, "beam": 3.0, "draft": 1.5, "body_count": 4, "hull_spacing": 20.0},  # 4-body wide
    ]
    
    for config in novel_configs:
        # Should never raise exception
        assessment = assess_structural_feasibility(**config)
        
        # Should always return an assessment
        assert assessment is not None
        assert hasattr(assessment, "warnings")
        assert hasattr(assessment, "overall_feasibility")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

