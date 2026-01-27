"""
Tests for partial sketch detection.

Verifies that VisionInterpreter detects incomplete sketches and requests clarification.
"""

import pytest
from magnet.agents.vision_interpreter import VisionInterpreter, SketchInterpretation


def test_assess_completeness_complete_sketch():
    """Test that complete sketch passes assessment."""
    interpreter = VisionInterpreter(None)
    
    interpretation = SketchInterpretation(
        body_count=1,
        dimensions={"loa_m": 25.0, "beam_m": 5.0, "draft_m": 1.5},
        geometric_description="Single hull with typical displacement form, rounded sections, moderate deadrise",
        confidence=0.8,
    )
    
    issue = interpreter._assess_completeness(interpretation)
    
    assert issue is None, "Complete sketch should not raise issues"


def test_assess_completeness_missing_all_dimensions():
    """Test that sketch with no dimensions is flagged."""
    interpreter = VisionInterpreter(None)
    
    interpretation = SketchInterpretation(
        body_count=1,
        dimensions={},  # No dimensions
        geometric_description="Hull form sketch",
        confidence=0.7,
    )
    
    issue = interpreter._assess_completeness(interpretation)
    
    assert issue is not None
    assert "Missing critical dimensions" in issue


def test_assess_completeness_missing_two_dimensions():
    """Test that sketch with only 1 dimension is flagged."""
    interpreter = VisionInterpreter(None)
    
    interpretation = SketchInterpretation(
        body_count=1,
        dimensions={"loa_m": 25.0},  # Only LOA
        geometric_description="Hull form with sections",
        confidence=0.7,
    )
    
    issue = interpreter._assess_completeness(interpretation)
    
    assert issue is not None
    assert "beam" in issue or "draft" in issue


def test_assess_completeness_vague_description():
    """Test that sketch with vague description is flagged."""
    interpreter = VisionInterpreter(None)
    
    interpretation = SketchInterpretation(
        body_count=1,
        dimensions={"loa_m": 25.0, "beam_m": 5.0, "draft_m": 1.5},
        geometric_description="boat",  # Too vague
        confidence=0.7,
    )
    
    issue = interpreter._assess_completeness(interpretation)
    
    assert issue is not None
    assert "brief" in issue.lower() or "detail" in issue.lower()


def test_assess_completeness_low_confidence():
    """Test that low confidence interpretation is flagged."""
    interpreter = VisionInterpreter(None)
    
    interpretation = SketchInterpretation(
        body_count=1,
        dimensions={"loa_m": 25.0, "beam_m": 5.0, "draft_m": 1.5},
        geometric_description="Hull form with displacement characteristics",
        confidence=0.2,  # Very low
    )
    
    issue = interpreter._assess_completeness(interpretation)
    
    assert issue is not None
    assert "confidence" in issue.lower()


def test_assess_completeness_one_dimension_sufficient_if_detailed():
    """Test that sketch with 1 dimension but detailed description might pass."""
    interpreter = VisionInterpreter(None)
    
    interpretation = SketchInterpretation(
        body_count=2,
        dimensions={"loa_m": 25.0, "beam_m": 5.0},  # 2 dimensions
        geometric_description=(
            "Twin hull catamaran with symmetric demihulls, "
            "moderate deadrise, typical displacement sections, "
            "hull spacing approximately 40% of LOA"
        ),
        confidence=0.75,
    )
    
    issue = interpreter._assess_completeness(interpretation)
    
    # Should be considered complete (2/3 dimensions + good description)
    assert issue is None


def test_vision_result_includes_requires_clarification():
    """Test that VisionResult has requires_clarification field."""
    from magnet.agents.vision_interpreter import VisionResult
    
    result = VisionResult(
        success=False,
        error="Incomplete sketch",
        requires_clarification=True,
    )
    
    assert hasattr(result, "requires_clarification")
    assert result.requires_clarification is True


def test_assess_completeness_multiple_issues():
    """Test that multiple completeness issues are combined."""
    interpreter = VisionInterpreter(None)
    
    interpretation = SketchInterpretation(
        body_count=1,
        dimensions={},  # No dimensions
        geometric_description="hull",  # Too vague
        confidence=0.25,  # Low confidence
    )
    
    issue = interpreter._assess_completeness(interpretation)
    
    assert issue is not None
    # Should contain multiple issues separated by |
    assert "|" in issue or (
        "dimensions" in issue and "brief" in issue
    )


def test_assess_completeness_allows_novel_geometry():
    """Test that novel geometry descriptions are not flagged as incomplete."""
    interpreter = VisionInterpreter(None)
    
    interpretation = SketchInterpretation(
        body_count=4,  # Novel 4-body configuration
        dimensions={"loa_m": 30.0, "beam_m": 12.0, "draft_m": 1.2},
        geometric_description=(
            "Four hull configuration with outer stabilizing pods, "
            "inner main hulls with cargo capacity, "
            "symmetric arrangement with 20% spacing"
        ),
        confidence=0.7,
    )
    
    issue = interpreter._assess_completeness(interpretation)
    
    # Novel geometry should not be flagged as incomplete
    assert issue is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

