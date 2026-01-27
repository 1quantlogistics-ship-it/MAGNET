"""
Tests for agent learning from validation history.

Verifies that GeometryProposer learns from previous failures and
avoids repeating the same mistakes.
"""

import pytest
from magnet.agents.geometry_proposer import GeometryProposer
from magnet.agents.llm_client import LLMClient


def test_extract_failure_patterns_empty_history():
    """Test that empty history returns no patterns."""
    from magnet.agents.geometry_proposer import create_geometry_proposer
    
    proposer = create_geometry_proposer()
    patterns = proposer._extract_failure_patterns([])
    
    assert patterns == []


def test_extract_failure_patterns_from_geometry_errors():
    """Test extraction of geometry compilation errors."""
    from magnet.agents.geometry_proposer import create_geometry_proposer
    
    proposer = create_geometry_proposer()
    
    history = [
        {
            "iteration_num": 1,
            "success": False,
            "errors": [
                "Invalid parameter: body_type must be a string",
                "Missing required field: section_id",
            ],
            "validation": {},
        }
    ]
    
    patterns = proposer._extract_failure_patterns(history)
    
    assert len(patterns) == 1
    assert "Geometry compilation failed" in patterns[0]["summary"]
    assert "Invalid parameter" in patterns[0]["reason"]


def test_extract_failure_patterns_from_constraint_violations():
    """Test extraction of constraint violations."""
    from magnet.agents.geometry_proposer import create_geometry_proposer
    
    proposer = create_geometry_proposer()
    
    history = [
        {
            "iteration_num": 1,
            "success": False,
            "errors": [],
            "validation": {
                "constraint_violations": [
                    {
                        "path": "stability.gm_m",
                        "required": 0.5,
                        "actual": 0.35,
                    }
                ],
            },
        }
    ]
    
    patterns = proposer._extract_failure_patterns(history)
    
    assert len(patterns) == 1
    assert "stability.gm_m" in patterns[0]["summary"]
    assert "Required 0.5" in patterns[0]["reason"]
    assert patterns[0]["constraint_violated"] == "stability.gm_m"


def test_extract_failure_patterns_from_low_gm():
    """Test extraction of low GM failures."""
    from magnet.agents.geometry_proposer import create_geometry_proposer
    
    proposer = create_geometry_proposer()
    
    history = [
        {
            "iteration_num": 1,
            "success": False,
            "errors": [],
            "validation": {
                "hydrostatics": {
                    "gm_m": 0.42,
                },
            },
        }
    ]
    
    patterns = proposer._extract_failure_patterns(history)
    
    assert len(patterns) == 1
    assert "Insufficient stability" in patterns[0]["summary"]
    assert "0.42m" in patterns[0]["reason"]
    assert "increase beam" in patterns[0]["suggested_fix"].lower()


def test_extract_failure_patterns_from_invalid_resistance_method():
    """Test extraction of resistance method validation failures."""
    from magnet.agents.geometry_proposer import create_geometry_proposer
    
    proposer = create_geometry_proposer()
    
    history = [
        {
            "iteration_num": 1,
            "success": False,
            "errors": [],
            "validation": {
                "resistance": {
                    "method_valid": False,
                    "validity_note": "Form outside Holtrop-Mennen envelope (L/B > 12)",
                },
            },
        }
    ]
    
    patterns = proposer._extract_failure_patterns(history)
    
    assert len(patterns) == 1
    assert "Resistance method invalid" in patterns[0]["summary"]
    assert "Holtrop-Mennen envelope" in patterns[0]["reason"]


def test_extract_failure_patterns_limits_to_5():
    """Test that extraction limits to last 5 attempts."""
    from magnet.agents.geometry_proposer import create_geometry_proposer
    
    proposer = create_geometry_proposer()
    
    # Create 10 failed attempts
    history = [
        {
            "iteration_num": i,
            "success": False,
            "errors": [f"Error {i}"],
            "validation": {},
        }
        for i in range(1, 11)
    ]
    
    patterns = proposer._extract_failure_patterns(history)
    
    # Should only process first 5
    assert len(patterns) <= 5


def test_extract_failure_patterns_deduplicates():
    """Test that patterns are deduplicated by summary."""
    from magnet.agents.geometry_proposer import create_geometry_proposer
    
    proposer = create_geometry_proposer()
    
    history = [
        {
            "iteration_num": 1,
            "success": False,
            "errors": [],
            "validation": {
                "hydrostatics": {"gm_m": 0.42},
            },
        },
        {
            "iteration_num": 2,
            "success": False,
            "errors": [],
            "validation": {
                "hydrostatics": {"gm_m": 0.43},
            },
        },
    ]
    
    patterns = proposer._extract_failure_patterns(history)
    
    # Should only have one "Insufficient stability" pattern
    assert len(patterns) == 1


def test_extract_failure_patterns_skips_successes():
    """Test that successful validations are not included in patterns."""
    from magnet.agents.geometry_proposer import create_geometry_proposer
    
    proposer = create_geometry_proposer()
    
    history = [
        {
            "iteration_num": 1,
            "success": True,  # Success
            "errors": [],
            "validation": {
                "hydrostatics": {"gm_m": 0.8},
            },
        },
        {
            "iteration_num": 2,
            "success": False,
            "errors": ["Error"],
            "validation": {},
        },
    ]
    
    patterns = proposer._extract_failure_patterns(history)
    
    # Should only have pattern from failed iteration
    assert len(patterns) == 1
    assert "Geometry compilation failed" in patterns[0]["summary"]


def test_build_prompt_includes_failure_patterns():
    """Test that failure patterns are included in the prompt."""
    from magnet.agents.geometry_proposer import create_geometry_proposer
    
    proposer = create_geometry_proposer()
    
    validation_history = [
        {
            "iteration_num": 1,
            "success": False,
            "errors": ["Invalid body_type"],
            "validation": {},
        }
    ]
    
    prompt = proposer._build_prompt(
        intent="Create a vessel",
        current_state=None,
        constraints=None,
        validation_history=validation_history,
    )
    
    # Should include failure section
    assert "PREVIOUS FAILURES TO AVOID" in prompt
    assert "Geometry compilation failed" in prompt
    assert "DO NOT repeat these patterns" in prompt


def test_build_prompt_without_history():
    """Test that prompt works without validation history."""
    from magnet.agents.geometry_proposer import create_geometry_proposer
    
    proposer = create_geometry_proposer()
    
    prompt = proposer._build_prompt(
        intent="Create a vessel",
        current_state=None,
        constraints=None,
        validation_history=None,
    )
    
    # Should not include failure section
    assert "PREVIOUS FAILURES" not in prompt
    assert "Design Request" in prompt


def test_design_conversation_builds_validation_history():
    """Test that DesignConversation builds validation history correctly."""
    from magnet.agents.design_conversation import DesignConversation, DesignIteration
    from magnet.kernel.program_executor import ExecutionResult
    
    conversation = DesignConversation()
    
    # Add some iterations to history
    for i in range(3):
        iteration = DesignIteration(
            iteration_number=i + 1,
            user_request=f"Request {i+1}",
            proposed_program="CREATE geometry.body main {}",
            execution_result=ExecutionResult(
                success=(i % 2 == 0),  # Alternate success/failure
                errors=[] if i % 2 == 0 else [f"Error {i+1}"],
                validation={
                    "hydrostatics": {"gm_m": 0.5 + i * 0.1}
                },
            ),
            metrics={},
            deltas={},
            feedback_to_user="",
            success=(i % 2 == 0),
        )
        conversation._state.iterations.append(iteration)
    
    history = conversation._build_validation_history()
    
    # Should have 3 entries (reverse order)
    assert len(history) == 3
    assert history[0]["iteration_num"] == 3  # Most recent first
    assert history[2]["iteration_num"] == 1  # Oldest last


def test_design_conversation_limits_history_to_5():
    """Test that validation history is limited to last 5 iterations."""
    from magnet.agents.design_conversation import DesignConversation, DesignIteration
    from magnet.kernel.program_executor import ExecutionResult
    
    conversation = DesignConversation()
    
    # Add 10 iterations
    for i in range(10):
        iteration = DesignIteration(
            iteration_number=i + 1,
            user_request=f"Request {i+1}",
            proposed_program="CREATE geometry.body main {}",
            execution_result=ExecutionResult(
                success=False,
                errors=[f"Error {i+1}"],
                validation={},
            ),
            metrics={},
            deltas={},
            feedback_to_user="",
            success=False,
        )
        conversation._state.iterations.append(iteration)
    
    history = conversation._build_validation_history()
    
    # Should only have last 5
    assert len(history) == 5
    assert history[0]["iteration_num"] == 10  # Most recent
    assert history[4]["iteration_num"] == 6   # 5th most recent


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

