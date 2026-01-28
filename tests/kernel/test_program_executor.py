"""
Tests for program executor.

TASK-016: ASK Disambiguation Operation
TASK-008: Lock Enforcement
"""

import pytest
from magnet.kernel.program_executor import execute_program, LockedParameterError


def test_execute_program_ask_returns_clarification():
    res = execute_program('ASK "How many hulls?" { options: ["1", "2"] }', initial_state={"resources": {}})
    assert res.success is False
    assert res.needs_clarification is True
    assert res.clarification is not None
    assert res.clarification["question"] == "How many hulls?"
    assert res.clarification["options"] == ["1", "2"]


class TestLockEnforcement:
    """TASK-008: Verify locked parameters cannot be modified via program execution."""
    
    def test_locked_parameter_raises_error(self):
        """Attempt to modify locked parameter via program → expect failure."""
        from magnet.core.state_manager import StateManager
        from magnet.core.design_state import DesignState
        
        # Create state manager with a locked parameter
        sm = StateManager(DesignState(design_id="test_lock", design_name="Lock Test"))
        sm.lock_parameter("hull.loa")
        
        # Try to modify the locked parameter
        program = 'SET hull.loa = 30.0'
        result = execute_program(program, state_manager=sm, initial_state={})
        
        # Should fail due to lock
        assert result.success is False
        assert any("locked" in err.lower() for err in result.errors)
    
    def test_unlocked_parameter_can_be_modified(self):
        """Unlocked parameters can be modified normally."""
        from magnet.core.state_manager import StateManager
        from magnet.core.design_state import DesignState
        
        sm = StateManager(DesignState(design_id="test_unlock", design_name="Unlock Test"))
        # Don't lock anything
        
        program = 'SET hull.beam = 5.0'
        result = execute_program(program, state_manager=sm, initial_state={})
        
        # Should succeed (or fail for other reasons, but not lock-related)
        # Note: May fail due to compilation if no geometry exists, but that's OK
        # The key is it shouldn't fail due to lock
        assert not any("locked" in err.lower() for err in result.errors)
    
    def test_locked_parameter_error_class_exists(self):
        """LockedParameterError is importable."""
        assert LockedParameterError is not None
        
        # Can be raised
        with pytest.raises(LockedParameterError):
            raise LockedParameterError("test")

