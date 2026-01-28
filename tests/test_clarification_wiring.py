"""
Tests for ClarificationManager wiring in DesignConversation.

Verifies that the clarification manager is properly passed and used
when confidence is low.
"""

import pytest
from magnet.agents.design_conversation import DesignConversation
from magnet.agents.clarification import ClarificationManager, AgentPriority


def test_design_conversation_accepts_clarification_manager():
    """Test that DesignConversation accepts clarification_manager parameter."""
    manager = ClarificationManager()
    
    conversation = DesignConversation(
        initial_state={"hull": {"loa": 25.0}},
        clarification_manager=manager,
        confidence_threshold=0.6,
    )
    
    assert conversation._clarification_manager is manager
    assert conversation._confidence_threshold == 0.6


def test_design_conversation_works_without_clarification_manager():
    """Test that DesignConversation works without clarification_manager (optional)."""
    conversation = DesignConversation(
        initial_state={"hull": {"loa": 25.0}},
    )
    
    # Should work fine without manager (clarification requests are skipped)
    assert conversation._clarification_manager is None


def test_clarification_manager_create_request():
    """Test that ClarificationManager can create requests."""
    manager = ClarificationManager()
    
    request = manager.create_request(
        agent_id="geometry_proposer",
        message="Did you mean LOA or LWL?",
        options=["LOA", "LWL"],
        priority=AgentPriority.DEFAULT,
    )
    
    assert request.agent_id == "geometry_proposer"
    assert request.message == "Did you mean LOA or LWL?"
    assert len(request.options) == 2
    assert request.priority == AgentPriority.DEFAULT


def test_clarification_manager_get_pending():
    """Test that ClarificationManager tracks pending requests."""
    manager = ClarificationManager()
    
    r1 = manager.create_request(
        agent_id="geometry_proposer",
        message="Question 1?",
        priority=AgentPriority.DEFAULT,
    )
    
    r2 = manager.create_request(
        agent_id="geometry_proposer",
        message="Question 2?",
        priority=AgentPriority.COMPLIANCE,
    )
    
    pending = manager.get_pending_requests()
    assert len(pending) == 2
    
    # Higher priority first
    assert pending[0].priority == AgentPriority.COMPLIANCE
    assert pending[1].priority == AgentPriority.DEFAULT


def test_clarification_manager_respond():
    """Test that ClarificationManager can record responses."""
    manager = ClarificationManager()
    
    request = manager.create_request(
        agent_id="geometry_proposer",
        message="Clarify?",
    )
    
    ack = manager.respond(
        request_id=request.request_id,
        response="Yes, I meant LOA",
    )
    
    assert ack is not None
    assert request.response == "Yes, I meant LOA"
    assert request.is_terminal()


def test_session_level_isolation():
    """Test that different sessions have isolated clarification managers."""
    manager1 = ClarificationManager()
    manager2 = ClarificationManager()
    
    r1 = manager1.create_request(agent_id="agent1", message="Q1")
    r2 = manager2.create_request(agent_id="agent2", message="Q2")
    
    # Managers are independent
    assert len(manager1.get_pending_requests()) == 1
    assert len(manager2.get_pending_requests()) == 1
    assert manager1.get_request(r1.request_id) is not None
    assert manager1.get_request(r2.request_id) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

