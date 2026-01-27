"""
Tests for session persistence and rollback.

Verifies that DesignConversation can save checkpoints and roll back
to previous iterations.
"""

import pytest
from magnet.agents.design_conversation import DesignConversation, DesignIteration
from magnet.kernel.program_executor import ExecutionResult


def test_save_checkpoint():
    """Test that checkpoint can be saved."""
    conversation = DesignConversation()
    
    checkpoint = conversation.save_checkpoint()
    
    assert "conversation_id" in checkpoint
    assert "timestamp" in checkpoint
    assert "iteration_count" in checkpoint
    assert "state" in checkpoint
    assert checkpoint["iteration_count"] == 0  # No iterations yet


def test_save_checkpoint_with_iterations():
    """Test checkpoint with iterations."""
    conversation = DesignConversation()
    
    # Add some iterations
    for i in range(3):
        iteration = DesignIteration(
            iteration_number=i + 1,
            user_request=f"Request {i+1}",
            proposed_program="CREATE geometry.body main {}",
            execution_result=None,
            metrics={"gm_m": 0.5 + i * 0.1},
            deltas={},
            feedback_to_user=f"Feedback {i+1}",
            success=True,
        )
        conversation._state.iterations.append(iteration)
        conversation._state.metrics_history.append({"gm_m": 0.5 + i * 0.1})
    
    checkpoint = conversation.save_checkpoint()
    
    assert checkpoint["iteration_count"] == 3
    assert len(checkpoint["state"]["iterations"]) == 3
    assert len(checkpoint["state"]["metrics_history"]) == 3


def test_rollback_to_earlier_iteration():
    """Test rolling back to an earlier iteration."""
    conversation = DesignConversation()
    
    # Add 5 iterations
    for i in range(5):
        iteration = DesignIteration(
            iteration_number=i + 1,
            user_request=f"Request {i+1}",
            proposed_program="CREATE geometry.body main {}",
            execution_result=None,
            metrics={},
            deltas={},
            feedback_to_user="",
            success=True,
        )
        conversation._state.iterations.append(iteration)
        conversation._state.metrics_history.append({"gm_m": 0.5})
    
    # Rollback to iteration 3
    success = conversation.rollback_to(3)
    
    assert success is True
    assert len(conversation._state.iterations) == 3
    assert len(conversation._state.metrics_history) == 3
    assert conversation._state.iterations[-1].iteration_number == 3


def test_rollback_clears_pending_clarification():
    """Test that rollback clears pending clarification."""
    conversation = DesignConversation()
    
    # Add iteration
    iteration = DesignIteration(
        iteration_number=1,
        user_request="Request",
        proposed_program="",
        execution_result=None,
        metrics={},
        deltas={},
        feedback_to_user="",
        success=True,
    )
    conversation._state.iterations.append(iteration)
    
    # Set pending clarification
    conversation._pending_clarification = "some_request_id"
    
    # Rollback
    conversation.rollback_to(1)
    
    assert conversation._pending_clarification is None


def test_rollback_invalid_iteration():
    """Test that rollback fails for invalid iteration numbers."""
    conversation = DesignConversation()
    
    # Add 3 iterations
    for i in range(3):
        iteration = DesignIteration(
            iteration_number=i + 1,
            user_request=f"Request {i+1}",
            proposed_program="",
            execution_result=None,
            metrics={},
            deltas={},
            feedback_to_user="",
            success=True,
        )
        conversation._state.iterations.append(iteration)
    
    # Try to rollback to invalid iterations
    assert conversation.rollback_to(0) is False  # Too low
    assert conversation.rollback_to(4) is False  # Too high
    assert conversation.rollback_to(-1) is False  # Negative
    
    # Iterations should be unchanged
    assert len(conversation._state.iterations) == 3


def test_rollback_to_last_iteration():
    """Test rolling back to the last iteration (no-op)."""
    conversation = DesignConversation()
    
    # Add 3 iterations
    for i in range(3):
        iteration = DesignIteration(
            iteration_number=i + 1,
            user_request=f"Request {i+1}",
            proposed_program="",
            execution_result=None,
            metrics={},
            deltas={},
            feedback_to_user="",
            success=True,
        )
        conversation._state.iterations.append(iteration)
    
    # Rollback to last iteration
    success = conversation.rollback_to(3)
    
    assert success is True
    assert len(conversation._state.iterations) == 3


def test_checkpoint_preserves_state():
    """Test that checkpoint preserves current state."""
    conversation = DesignConversation()
    conversation._state.current_state = {
        "hull": {"loa": 30.0, "beam": 6.0},
        "resources": {"body_1": {"_type": "geometry.body"}},
    }
    
    checkpoint = conversation.save_checkpoint()
    
    assert "current_state" in checkpoint["state"]
    assert checkpoint["state"]["current_state"]["hull"]["loa"] == 30.0


def test_rollback_preserves_successful_iterations():
    """Test that rollback only keeps iterations up to the target."""
    conversation = DesignConversation()
    
    # Add 5 iterations (mix of success/failure)
    for i in range(5):
        iteration = DesignIteration(
            iteration_number=i + 1,
            user_request=f"Request {i+1}",
            proposed_program="",
            execution_result=None,
            metrics={},
            deltas={},
            feedback_to_user="",
            success=(i % 2 == 0),  # Alternating success/failure
        )
        conversation._state.iterations.append(iteration)
        conversation._state.metrics_history.append({})
    
    # Rollback to iteration 3
    conversation.rollback_to(3)
    
    # Should have 3 iterations (regardless of success/failure)
    assert len(conversation._state.iterations) == 3
    assert conversation._state.iterations[0].iteration_number == 1
    assert conversation._state.iterations[1].iteration_number == 2
    assert conversation._state.iterations[2].iteration_number == 3


def test_get_summary_reflects_checkpoint_state():
    """Test that get_summary works with checkpointed state."""
    conversation = DesignConversation()
    
    # Add iterations
    for i in range(3):
        iteration = DesignIteration(
            iteration_number=i + 1,
            user_request=f"Request {i+1}",
            proposed_program="",
            execution_result=None,
            metrics={},
            deltas={},
            feedback_to_user="",
            success=True,
        )
        conversation._state.iterations.append(iteration)
    
    summary = conversation.get_summary()
    
    assert summary["iterations"] == 3
    assert summary["conversation_id"] == conversation._conversation_id


def test_rebuild_state_from_iterations():
    """Test that _rebuild_state_from_iterations replays successful changes."""
    conversation = DesignConversation()
    
    # Add iteration with successful execution
    exec_result = ExecutionResult(
        success=True,
        actions=[],
        geometry=None,
        validation={},
        errors=[],
    )
    
    iteration = DesignIteration(
        iteration_number=1,
        user_request="Request",
        proposed_program="",
        execution_result=exec_result,
        metrics={},
        deltas={},
        feedback_to_user="",
        success=True,
    )
    conversation._state.iterations.append(iteration)
    
    # Rebuild state
    conversation._rebuild_state_from_iterations()
    
    # Should have reset state (test doesn't crash)
    assert conversation._state.current_state is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

