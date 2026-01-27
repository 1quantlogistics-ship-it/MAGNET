"""
Tests for agent reconciliation (Vision vs. GeometryProposer).

Verifies that the system detects and requests clarification when
vision interpreter and geometry proposer disagree on critical properties.
"""

import pytest
from magnet.agents.design_conversation import DesignConversation
from magnet.agents.clarification import ClarificationManager


def test_check_reconciliation_agreement():
    """Test that no issue is raised when vision and DSL agree."""
    conversation = DesignConversation()
    
    program_text = """
CREATE geometry.body port_hull { body_type: "demihull", offset_y_m: -3.0 }
CREATE geometry.body stbd_hull { body_type: "demihull", offset_y_m: 3.0 }
"""
    
    vision_context = {
        "body_count": 2,
        "loa_m": 25.0,
    }
    
    issue = conversation._check_vision_dsl_reconciliation(program_text, vision_context)
    
    assert issue is None, "Should not raise issue when body counts agree"


def test_check_reconciliation_disagreement():
    """Test that issue is raised when vision and DSL disagree."""
    conversation = DesignConversation()
    
    # DSL has 1 body
    program_text = """
CREATE geometry.body main_hull { body_type: "monohull" }
"""
    
    # Vision detected 2 bodies
    vision_context = {
        "body_count": 2,
        "loa_m": 25.0,
    }
    
    issue = conversation._check_vision_dsl_reconciliation(program_text, vision_context)
    
    assert issue is not None, "Should raise issue when body counts disagree"
    assert "2 hull bodies" in issue
    assert "1 bodies" in issue


def test_check_reconciliation_triple_hull():
    """Test reconciliation for trimaran (3 bodies)."""
    conversation = DesignConversation()
    
    program_text = """
CREATE geometry.body main { body_type: "main_hull", offset_y_m: 0.0 }
CREATE geometry.body port { body_type: "ama", offset_y_m: -5.0 }
CREATE geometry.body stbd { body_type: "ama", offset_y_m: 5.0 }
"""
    
    vision_context = {
        "body_count": 3,
    }
    
    issue = conversation._check_vision_dsl_reconciliation(program_text, vision_context)
    
    assert issue is None, "Should agree on 3 bodies"


def test_check_reconciliation_novel_multi_body():
    """Test reconciliation for novel multi-body configuration."""
    conversation = DesignConversation()
    
    # 4 body configuration
    program_text = """
CREATE geometry.body main_port { offset_y_m: -2.0 }
CREATE geometry.body main_stbd { offset_y_m: 2.0 }
CREATE geometry.body outrigger_port { offset_y_m: -6.0 }
CREATE geometry.body outrigger_stbd { offset_y_m: 6.0 }
"""
    
    vision_context = {
        "body_count": 4,
    }
    
    issue = conversation._check_vision_dsl_reconciliation(program_text, vision_context)
    
    assert issue is None, "Should agree on 4 bodies"


@pytest.mark.asyncio
async def test_reconciliation_clarification_requested():
    """Test that clarification is requested when disagreement detected."""
    clarification_mgr = ClarificationManager()
    conversation = DesignConversation(
        clarification_manager=clarification_mgr,
    )
    
    program_text = """
CREATE geometry.body main { body_type: "monohull" }
"""
    
    vision_context = {
        "body_count": 2,
    }
    
    issue = "Vision detected 2 bodies, DSL has 1"
    
    iteration = await conversation._request_reconciliation_clarification(
        issue=issue,
        program_text=program_text,
        vision_context=vision_context,
        iteration_num=1,
    )
    
    # Should have created clarification request
    pending = clarification_mgr.get_pending_requests()
    assert len(pending) == 1
    
    request = pending[0]
    assert request.agent_id == "geometry_reconciliation"
    assert "2 bodies" in request.message
    assert len(request.options) == 3  # Vision correct, DSL correct, Let me clarify
    
    # Iteration should indicate clarification needed
    assert iteration.success is False
    assert "reconciliation needed" in iteration.feedback_to_user.lower()


@pytest.mark.asyncio
async def test_vision_context_passed_to_chat():
    """Test that vision context is properly passed to chat method."""
    conversation = DesignConversation()
    
    # This test verifies the signature accepts vision_context
    # Actual reconciliation is tested above
    user_message = "CREATE geometry.body main { body_type: \"hull\" }"
    
    # Should not raise error
    iteration = await conversation.chat(
        user_message,
        constraints=[],
        vision_context={"body_count": 1},
    )
    
    # Direct DSL should execute without reconciliation issues
    assert iteration is not None


def test_reconciliation_issue_includes_details():
    """Test that reconciliation issue includes helpful details."""
    conversation = DesignConversation()
    
    program_text = """
CREATE geometry.body a {}
"""
    
    vision_context = {
        "body_count": 3,
    }
    
    issue = conversation._check_vision_dsl_reconciliation(program_text, vision_context)
    
    assert issue is not None
    assert "3 hull bodies" in issue  # Vision count
    assert "1 bodies" in issue       # DSL count
    assert "misinterpretation" in issue.lower()


def test_no_reconciliation_without_vision_context():
    """Test that reconciliation is skipped when no vision context provided."""
    conversation = DesignConversation()
    
    # Even if DSL has bodies, no issue should be raised without vision context
    program_text = """
CREATE geometry.body main {}
"""
    
    # No vision_context provided
    issue = conversation._check_vision_dsl_reconciliation(program_text, {})
    
    # Should compare to default body_count of 1
    assert issue is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

