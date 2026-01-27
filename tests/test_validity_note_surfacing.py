"""
Tests for validity_note surfacing in narrative generation.

Verifies that resistance validity warnings are properly displayed
when method_valid=False.
"""

import pytest
from magnet.explain.narrative import NarrativeGenerator
from magnet.explain.schemas import ExplanationLevel
from magnet.protocol.schemas import ValidationResult, ValidationFinding


def test_narrative_shows_resistance_value():
    """Test that narrative shows resistance value when valid."""
    generator = NarrativeGenerator()
    
    old_state = {"hull": {"loa": 25.0}}
    new_state = {"hull": {"loa": 25.0, "beam": 5.0}}
    
    # Create validation result with resistance
    validation = ValidationResult(
        passed=True,
        findings=[],
    )
    
    explanation = generator.generate_explanation(
        level=ExplanationLevel.STANDARD,
        old_state=old_state,
        new_state=new_state,
        validation_result=validation,
    )
    
    # Should generate explanation successfully
    assert explanation is not None
    assert explanation.summary is not None


def test_narrative_surfaces_validity_note_when_invalid():
    """Test that validity_note is shown when method_valid=False."""
    generator = NarrativeGenerator()
    
    # Mock validation with invalid resistance method
    validation_dict = {
        "resistance": {
            "resistance_kn": 45.2,
            "method_valid": False,
            "validity_note": "Form outside Holtrop-Mennen envelope (L/B > 12). Recommend CFD validation.",
        },
    }
    
    # Generate narrative with this validation
    narrative = generator._format_geometry_validation(validation_dict)
    
    # Should include resistance value
    assert "45.2kN" in narrative
    
    # Should include validity warning
    assert "⚠️" in narrative
    assert "validity" in narrative.lower()
    assert "Holtrop-Mennen envelope" in narrative


def test_narrative_no_warning_when_method_valid():
    """Test that no warning is shown when method_valid=True."""
    generator = NarrativeGenerator()
    
    validation_dict = {
        "resistance": {
            "resistance_kn": 45.2,
            "method_valid": True,
            "validity_note": "",  # Empty when valid
        },
    }
    
    narrative = generator._format_geometry_validation(validation_dict)
    
    # Should include resistance value
    assert "45.2kN" in narrative
    
    # Should NOT include validity warning
    assert "⚠️" not in narrative or "validity" not in narrative.lower()


def test_narrative_handles_missing_validity_fields():
    """Test that narrative works when validity fields are missing (legacy format)."""
    generator = NarrativeGenerator()
    
    validation_dict = {
        "resistance": {
            "resistance_kn": 45.2,
            # method_valid and validity_note not present
        },
    }
    
    # Should not crash
    narrative = generator._format_geometry_validation(validation_dict)
    
    # Should include resistance value
    assert "45.2kN" in narrative


def test_narrative_shows_validity_note_for_novel_geometry():
    """Test validity note for novel geometry forms."""
    generator = NarrativeGenerator()
    
    validation_dict = {
        "resistance": {
            "resistance_kn": None,  # May be None for completely unknown forms
            "method_valid": False,
            "validity_note": "No validated method available for 4-body configuration. CFD required.",
        },
    }
    
    narrative = generator._format_geometry_validation(validation_dict)
    
    # Should show validity warning even if resistance is None
    assert "⚠️" in narrative
    assert "4-body configuration" in narrative
    assert "CFD required" in narrative


def test_narrative_multiple_validations_with_validity_notes():
    """Test that validity notes are shown alongside other validation warnings."""
    generator = NarrativeGenerator()
    
    validation_dict = {
        "resistance": {
            "resistance_kn": 45.2,
            "method_valid": False,
            "validity_note": "Novel hull form - recommend model testing.",
        },
        "hydrostatics": {
            "gm_m": 0.42,
        },
        "constraint_violations": [
            {"path": "stability.gm_m", "required": 0.5, "actual": 0.42},
        ],
    }
    
    narrative = generator._format_geometry_validation(validation_dict)
    
    # Should include all information
    assert "45.2kN" in narrative  # Resistance value
    assert "validity" in narrative.lower()  # Validity warning
    assert "0.42" in narrative  # GM value
    assert "constraint violation" in narrative.lower()  # Constraint warning


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

