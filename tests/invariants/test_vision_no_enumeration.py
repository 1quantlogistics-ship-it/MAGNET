"""
Invariant tests for vision interpreter.

INVARIANT: Vision output must NEVER contain design type names.
           Only geometric descriptions are allowed.

Reference: MAGNET_Merge_Implementation_Plan.md Phase 0.5
"""

import pytest
from unittest.mock import Mock, AsyncMock

from magnet.agents.vision_interpreter import (
    VisionInterpreter,
    SketchInterpretation,
    BodyDescription,
    SurfaceFeature,
    FORBIDDEN_TERMS,
    VISION_INTERPRETER_SYSTEM_PROMPT,
)


class TestVisionNoEnumeration:
    """Vision interpreter must not output design type names."""
    
    def test_forbidden_terms_list_complete(self):
        """Forbidden terms list includes all design types."""
        required_forbidden = [
            "catamaran", "trimaran", "monohull",
            "stepped hull", "planing hull",
            "patrol boat", "workboat", "yacht",
        ]
        for term in required_forbidden:
            assert term in FORBIDDEN_TERMS, f"Missing forbidden term: {term}"
    
    def test_check_forbidden_terms_detects_catamaran(self):
        """Detects 'catamaran' in geometric description."""
        interpreter = VisionInterpreter(llm_provider=None)
        
        interpretation = SketchInterpretation(
            body_count=2,
            geometric_description="This looks like a catamaran with twin hulls",
        )
        
        violation = interpreter._check_forbidden_terms(interpretation)
        assert violation == "catamaran"
    
    def test_check_forbidden_terms_detects_trimaran(self):
        """Detects 'trimaran' in geometric description."""
        interpreter = VisionInterpreter(llm_provider=None)
        
        interpretation = SketchInterpretation(
            body_count=3,
            geometric_description="This appears to be a trimaran configuration",
        )
        
        violation = interpreter._check_forbidden_terms(interpretation)
        assert violation == "trimaran"
    
    def test_check_forbidden_terms_detects_patrol_boat(self):
        """Detects 'patrol boat' in geometric description."""
        interpreter = VisionInterpreter(llm_provider=None)
        
        interpretation = SketchInterpretation(
            body_count=1,
            geometric_description="This is a patrol boat design",
        )
        
        violation = interpreter._check_forbidden_terms(interpretation)
        assert violation == "patrol boat"
    
    def test_check_forbidden_terms_allows_geometry(self):
        """Allows pure geometric descriptions."""
        interpreter = VisionInterpreter(llm_provider=None)
        
        interpretation = SketchInterpretation(
            body_count=2,
            geometric_description="Two hull bodies offset laterally by 4m, each with L/B ratio of 8:1",
        )
        
        violation = interpreter._check_forbidden_terms(interpretation)
        assert violation is None
    
    def test_check_forbidden_terms_allows_multi_body_description(self):
        """Allows '2-body' or '3-body' geometric descriptions."""
        interpreter = VisionInterpreter(llm_provider=None)
        
        interpretation = SketchInterpretation(
            body_count=2,
            geometric_description="A 2-body configuration with symmetric lateral offset",
        )
        
        violation = interpreter._check_forbidden_terms(interpretation)
        assert violation is None


class TestVisionIntentGeneration:
    """Vision interpreter generates valid intent strings."""
    
    def test_generate_intent_string_no_design_types(self):
        """Generated intent string contains no design types."""
        interpreter = VisionInterpreter(llm_provider=None)
        
        interpretation = SketchInterpretation(
            body_count=2,
            dimensions={"loa_m": 25, "beam_m": 5, "body_spacing_m": 8},
            geometric_description="Two parallel hull bodies",
        )
        
        intent = interpreter._generate_intent_string(interpretation, "")
        
        for term in FORBIDDEN_TERMS:
            assert term.lower() not in intent.lower(), \
                f"Intent string contains forbidden term: {term}"
    
    def test_generate_intent_includes_dimensions(self):
        """Intent string includes extracted dimensions."""
        interpreter = VisionInterpreter(llm_provider=None)
        
        interpretation = SketchInterpretation(
            body_count=1,
            dimensions={"loa_m": 25, "beam_m": 5},
        )
        
        intent = interpreter._generate_intent_string(interpretation, "")
        
        assert "25" in intent, "Intent should include length"
        assert "5" in intent or "beam" in intent, "Intent should include beam"
    
    def test_generate_intent_includes_body_count(self):
        """Intent string includes body count."""
        interpreter = VisionInterpreter(llm_provider=None)
        
        interpretation = SketchInterpretation(
            body_count=3,
            dimensions={},
        )
        
        intent = interpreter._generate_intent_string(interpretation, "")
        
        assert "3-body" in intent or "3 body" in intent.lower()
    
    def test_generate_intent_includes_surface_features(self):
        """Intent string includes surface features."""
        interpreter = VisionInterpreter(llm_provider=None)
        
        interpretation = SketchInterpretation(
            body_count=1,
            surface_features=[
                SurfaceFeature(type="step", station_fraction_estimate=0.4),
            ],
        )
        
        intent = interpreter._generate_intent_string(interpretation, "")
        
        assert "discontinuity" in intent.lower() or "step" in intent.lower()


class TestSystemPrompt:
    """System prompt correctly forbids design types."""
    
    def test_system_prompt_forbids_design_types(self):
        """System prompt explicitly forbids design type names."""
        assert "FORBIDDEN" in VISION_INTERPRETER_SYSTEM_PROMPT
        assert "catamaran" in VISION_INTERPRETER_SYSTEM_PROMPT
        assert "Do NOT" in VISION_INTERPRETER_SYSTEM_PROMPT
    
    def test_system_prompt_requires_geometry_only(self):
        """System prompt requires geometry-only output."""
        assert "GEOMETRY" in VISION_INTERPRETER_SYSTEM_PROMPT.upper()
        assert "geometric" in VISION_INTERPRETER_SYSTEM_PROMPT.lower()
    
    def test_system_prompt_includes_json_schema(self):
        """System prompt includes JSON output schema."""
        assert "body_count" in VISION_INTERPRETER_SYSTEM_PROMPT
        assert "dimensions" in VISION_INTERPRETER_SYSTEM_PROMPT
        assert "JSON" in VISION_INTERPRETER_SYSTEM_PROMPT


class TestVisionInterpretation:
    """Test sketch interpretation with mock LLM."""
    
    @pytest.mark.asyncio
    async def test_sketch_with_dimension_annotation(self):
        """
        THE TEST: Upload sketch with "25m" written on it.
        Verify dimensions are extracted.
        """
        # Mock LLM provider
        mock_provider = Mock()
        mock_provider.complete_with_image = AsyncMock(return_value=Mock(
            content='''{
                "body_count": 1,
                "dimensions": {"loa_m": 25, "beam_m": 5, "draft_m": 1.5},
                "proportions": {"length_beam_ratio": 5.0},
                "bodies": [{"body_index": 0, "position": "center", "relative_size": "primary"}],
                "surface_features": [],
                "annotations": [{"text": "25m", "interpretation": "Overall length annotation"}],
                "confidence": 0.85,
                "geometric_description": "Single hull body with 25m length annotation, moderate displacement form with rounded bilge sections and typical bow entry"
            }'''
        ))
        
        interpreter = VisionInterpreter(mock_provider)
        
        # Fake image data
        result = await interpreter.interpret_sketch(
            image_data=b"fake_image_data",
            annotations="25m vessel concept",
        )
        
        assert result.success
        assert result.interpretation.dimensions.get("loa_m") == 25
        assert "25" in result.intent_string
        
        # Verify no forbidden terms
        for term in FORBIDDEN_TERMS:
            assert term.lower() not in result.intent_string.lower()
    
    @pytest.mark.asyncio
    async def test_multi_body_sketch_interpretation(self):
        """Interpret multi-body sketch without using design type names."""
        mock_provider = Mock()
        mock_provider.complete_with_image = AsyncMock(return_value=Mock(
            content='''{
                "body_count": 2,
                "dimensions": {"loa_m": 20, "beam_m": 2.5, "draft_m": 1.2, "body_spacing_m": 6},
                "proportions": {"length_beam_ratio": 10.0},
                "bodies": [
                    {"body_index": 0, "position": "port", "relative_size": "equal", "offset_y_estimate_m": -3},
                    {"body_index": 1, "position": "starboard", "relative_size": "equal", "offset_y_estimate_m": 3}
                ],
                "surface_features": [],
                "annotations": [],
                "confidence": 0.8,
                "geometric_description": "Two slender hull bodies arranged symmetrically with 6m lateral spacing, displacement form with typical sections"
            }'''
        ))
        
        interpreter = VisionInterpreter(mock_provider)
        
        result = await interpreter.interpret_sketch(
            image_data=b"fake_image_data",
            annotations="twin hull concept",
        )
        
        assert result.success
        assert result.interpretation.body_count == 2
        assert "2-body" in result.intent_string
        
        # CRITICAL: Must NOT contain "catamaran"
        assert "catamaran" not in result.intent_string.lower()
        assert "catamaran" not in result.interpretation.geometric_description.lower()
    
    @pytest.mark.asyncio
    async def test_vision_rejects_enumerated_response(self):
        """Vision interpreter rejects LLM responses containing design types."""
        mock_provider = Mock()
        mock_provider.complete_with_image = AsyncMock(return_value=Mock(
            content='''{
                "body_count": 2,
                "dimensions": {},
                "proportions": {},
                "bodies": [],
                "surface_features": [],
                "annotations": [],
                "confidence": 0.9,
                "geometric_description": "This is clearly a catamaran design"
            }'''
        ))
        
        interpreter = VisionInterpreter(mock_provider)
        
        result = await interpreter.interpret_sketch(
            image_data=b"fake_image_data",
            annotations="",
        )
        
        # Should FAIL because LLM used forbidden term
        assert not result.success
        assert "Enumeration violation" in result.error
        assert "catamaran" in result.error


class TestInvariantVisionGeometryOnly:
    """Sacred invariant: vision output is geometry only."""
    
    def test_invariant_no_design_types_in_output(self):
        """
        SACRED INVARIANT: Vision output contains ONLY geometry terms.
        
        This test verifies the core contract:
        - Vision interpreter extracts geometric information
        - Output NEVER contains design type names
        - Intent string is suitable for GeometryProposer
        """
        interpreter = VisionInterpreter(llm_provider=None)
        
        # Valid geometric interpretation
        valid_interpretation = SketchInterpretation(
            body_count=2,
            dimensions={"loa_m": 25, "body_spacing_m": 8},
            bodies=[
                BodyDescription(body_index=0, position="port", offset_y_estimate_m=-4),
                BodyDescription(body_index=1, position="starboard", offset_y_estimate_m=4),
            ],
            geometric_description="Two hull bodies with symmetric lateral offset",
        )
        
        # Should pass validation
        violation = interpreter._check_forbidden_terms(valid_interpretation)
        assert violation is None, "Valid geometry should not be flagged"
        
        # Intent should be geometry-only
        intent = interpreter._generate_intent_string(valid_interpretation, "")
        for term in FORBIDDEN_TERMS:
            assert term.lower() not in intent.lower(), \
                f"Intent contains forbidden term: {term}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

