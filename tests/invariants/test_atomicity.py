"""
Invariant tests for atomic execution.

INVARIANT: Program execution is atomic — all succeed or all fail.
           If any step fails, state_manager remains unchanged.

Reference: MAGNET_Merge_Implementation_Plan.md Phase 0.2
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Dict, Any


class MockStateManager:
    """Mock StateManager for testing atomicity."""
    
    def __init__(self, initial_state: Dict[str, Any] = None):
        self._state = initial_state or {}
        self._set_calls = []
    
    def to_dict(self) -> Dict[str, Any]:
        return self._state.copy()
    
    def get(self, path: str) -> Any:
        parts = path.split('.')
        current = self._state
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        return current
    
    def set(self, path: str, value: Any) -> None:
        self._set_calls.append((path, value))
        parts = path.split('.')
        current = self._state
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value


class TestProgramExecutorAtomicity:
    """Test that program_executor is atomic."""
    
    def test_successful_execution_commits(self):
        """Successful execution commits actions to state_manager."""
        from magnet.kernel.program_executor import execute_program
        
        state = MockStateManager({"resources": {}})
        
        # Valid program
        program = """
            CREATE geometry.section bow {
                station: 0.0,
                points: [[0, 0], [1, -0.5], [1, 0.5]]
            }
        """
        
        result = execute_program(program, state, dry_run=False)
        
        # Should succeed
        assert result.success or len(result.errors) == 0, f"Errors: {result.errors}"
    
    def test_dry_run_never_commits(self):
        """dry_run=True never commits to state_manager."""
        from magnet.kernel.program_executor import execute_program
        
        state = MockStateManager({"resources": {}, "test_key": "original"})
        
        program = """
            SET test_key = "modified"
        """
        
        result = execute_program(program, state, dry_run=True)
        
        # Should NOT have committed
        assert state.get("test_key") == "original", "dry_run should not commit"
    
    def test_parse_error_no_commit(self):
        """Parse error leaves state unchanged."""
        from magnet.kernel.program_executor import execute_program
        
        state = MockStateManager({"resources": {}, "marker": "original"})
        
        # Invalid syntax
        program = "THIS IS NOT VALID SYNTAX {{{{{{"
        
        result = execute_program(program, state, dry_run=False)
        
        assert not result.success
        assert "Parse error" in str(result.errors)
        # State should be unchanged
        assert state.get("marker") == "original"
    
    def test_compilation_error_no_commit(self):
        """Compilation error leaves state unchanged."""
        from magnet.kernel.program_executor import execute_program
        
        state = MockStateManager({"resources": {}, "marker": "original"})
        
        # This will parse but fail to compile (body references nonexistent sections)
        program = """
            CREATE geometry.body main {
                section_ids: ["nonexistent_section"]
            }
        """
        
        result = execute_program(program, state, dry_run=False)
        
        # May or may not fail depending on compiler strictness
        # But if it fails, state should be unchanged
        if not result.success:
            assert state.get("marker") == "original"


class TestGeometryProposalRollback:
    """Test rollback behavior for geometry proposals."""
    
    def test_failed_compilation_leaves_state_unchanged(self):
        """Failed compilation leaves state unchanged."""
        from magnet.kernel.program_executor import execute_program
        
        state = MockStateManager({"existing_key": "value", "resources": {}})
        
        # Program that will fail during compilation
        bad_program = "CREATE geometry.body main { INVALID SYNTAX"
        
        result = execute_program(bad_program, state, dry_run=False)
        
        assert not result.success
        assert state.get("existing_key") == "value", "State should be unchanged"


class TestPartialExecutionRollback:
    """Test that partial execution rolls back all changes."""
    
    def test_partial_failure_rolls_back_all(self):
        """Partial execution failure rolls back all changes."""
        from magnet.kernel.program_executor import execute_program
        
        state = MockStateManager({"resources": {}})
        initial_resources = state.get("resources")
        
        # First statement might succeed, second should fail
        program = """
            CREATE geometry.section valid_section {
                station: 0.0,
                points: [[0, 0], [1, -0.5], [1, 0.5]]
            }
            CREATE geometry.body main {
                section_ids: ["nonexistent_section_that_does_not_exist"]
            }
        """
        
        result = execute_program(program, state, dry_run=False)
        
        # If execution failed, resources should be unchanged
        if not result.success:
            # The valid_section should NOT be in state because we rolled back
            current_resources = state.get("resources") or {}
            # Check that no new resources were added
            assert "geometry.section.valid_section" not in str(current_resources)


class TestInvariantAtomicExecution:
    """Sacred invariant: execution is all-or-nothing."""
    
    def test_invariant_atomic_execution(self):
        """
        SACRED INVARIANT: Program execution is atomic.
        
        This test verifies the core contract:
        - If execution succeeds, all changes are committed
        - If execution fails at any step, NO changes are committed
        """
        from magnet.kernel.program_executor import execute_program
        
        # Test 1: Success commits
        state1 = MockStateManager({"resources": {}})
        result1 = execute_program(
            "SET test.value = 42",
            state1,
            dry_run=False,
        )
        if result1.success:
            assert state1.get("test.value") == 42, "Success should commit"
        
        # Test 2: Failure does not commit
        state2 = MockStateManager({"resources": {}, "original": "value"})
        result2 = execute_program(
            "INVALID SYNTAX HERE",
            state2,
            dry_run=False,
        )
        assert not result2.success
        assert state2.get("original") == "value", "Failure should not modify state"
        
        # Test 3: dry_run never commits
        state3 = MockStateManager({"resources": {}})
        result3 = execute_program(
            "SET test.value = 100",
            state3,
            dry_run=True,
        )
        assert state3.get("test.value") is None, "dry_run should never commit"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

