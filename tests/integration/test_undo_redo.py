"""
TASK-024: Undo/Redo — User Can Revert Changes

Tests for undo/redo functionality in StateManager.
"""

import pytest
from magnet.core.state_manager import StateManager


class TestUndoRedo:
    """Test undo/redo functionality."""

    @pytest.fixture
    def state_manager(self):
        """Create a fresh StateManager for each test."""
        return StateManager()

    def test_initial_state_cannot_undo(self, state_manager):
        """Initially, undo is not available."""
        assert not state_manager.can_undo()
        assert state_manager.undo_stack_depth() == 0

    def test_initial_state_cannot_redo(self, state_manager):
        """Initially, redo is not available."""
        assert not state_manager.can_redo()
        assert state_manager.redo_stack_depth() == 0

    def test_undo_after_commit(self, state_manager):
        """Undo is available after a commit."""
        # Make a change through transaction
        txn_id = state_manager.begin_transaction()
        state_manager.set("mission.max_speed_kts", 25.0, "test")
        state_manager.commit_transaction(txn_id)
        
        assert state_manager.can_undo()
        assert state_manager.undo_stack_depth() == 1

    def test_undo_reverts_change(self, state_manager):
        """Undo reverts the last change."""
        # Record initial value
        initial_speed = state_manager.get("mission.max_speed_kts")
        
        # Make a change
        txn_id = state_manager.begin_transaction()
        state_manager.set("mission.max_speed_kts", 30.0, "test")
        state_manager.commit_transaction(txn_id)
        
        assert state_manager.get("mission.max_speed_kts") == 30.0
        
        # Undo
        result = state_manager.undo()
        assert result is True
        assert state_manager.get("mission.max_speed_kts") == initial_speed

    def test_redo_after_undo(self, state_manager):
        """Redo is available after undo."""
        # Make a change
        txn_id = state_manager.begin_transaction()
        state_manager.set("mission.max_speed_kts", 35.0, "test")
        state_manager.commit_transaction(txn_id)
        
        # Undo
        state_manager.undo()
        
        assert state_manager.can_redo()
        assert state_manager.redo_stack_depth() == 1

    def test_redo_restores_change(self, state_manager):
        """Redo restores the undone change."""
        # Make a change
        txn_id = state_manager.begin_transaction()
        state_manager.set("mission.max_speed_kts", 40.0, "test")
        state_manager.commit_transaction(txn_id)
        
        # Undo
        state_manager.undo()
        
        # Redo
        result = state_manager.redo()
        assert result is True
        assert state_manager.get("mission.max_speed_kts") == 40.0

    def test_new_commit_clears_redo(self, state_manager):
        """New commit clears the redo stack."""
        # Make first change
        txn_id = state_manager.begin_transaction()
        state_manager.set("mission.max_speed_kts", 25.0, "test")
        state_manager.commit_transaction(txn_id)
        
        # Undo
        state_manager.undo()
        assert state_manager.can_redo()
        
        # Make new change
        txn_id = state_manager.begin_transaction()
        state_manager.set("mission.max_speed_kts", 30.0, "test")
        state_manager.commit_transaction(txn_id)
        
        # Redo should be cleared
        assert not state_manager.can_redo()

    def test_multiple_undos(self, state_manager):
        """Multiple undos work correctly."""
        # Make three changes
        for speed in [20.0, 25.0, 30.0]:
            txn_id = state_manager.begin_transaction()
            state_manager.set("mission.max_speed_kts", speed, "test")
            state_manager.commit_transaction(txn_id)
        
        assert state_manager.get("mission.max_speed_kts") == 30.0
        assert state_manager.undo_stack_depth() == 3
        
        # Undo all three
        state_manager.undo()
        assert state_manager.get("mission.max_speed_kts") == 25.0
        
        state_manager.undo()
        assert state_manager.get("mission.max_speed_kts") == 20.0
        
        state_manager.undo()
        # Back to initial state (None or default)

    def test_undo_stack_limit(self, state_manager):
        """Undo stack respects maximum depth."""
        # Make more changes than max depth
        for i in range(25):
            txn_id = state_manager.begin_transaction()
            state_manager.set("mission.max_speed_kts", float(i), "test")
            state_manager.commit_transaction(txn_id)
        
        # Stack should be limited to 20
        assert state_manager.undo_stack_depth() <= 20

    def test_undo_returns_false_when_empty(self, state_manager):
        """Undo returns False when stack is empty."""
        result = state_manager.undo()
        assert result is False

    def test_redo_returns_false_when_empty(self, state_manager):
        """Redo returns False when stack is empty."""
        result = state_manager.redo()
        assert result is False


class TestUndoRedoHistory:
    """Test that undo/redo operations are recorded in history."""

    @pytest.fixture
    def state_manager(self):
        return StateManager()

    def test_undo_recorded_in_history(self, state_manager):
        """Undo operation is recorded in history."""
        # Make a change
        txn_id = state_manager.begin_transaction()
        state_manager.set("mission.max_speed_kts", 25.0, "test")
        state_manager.commit_transaction(txn_id)
        
        # Undo
        state_manager.undo()
        
        # Check history
        history = state_manager.state.history
        assert any(h.get("action") == "undo" for h in history)

    def test_redo_recorded_in_history(self, state_manager):
        """Redo operation is recorded in history."""
        # Make a change
        txn_id = state_manager.begin_transaction()
        state_manager.set("mission.max_speed_kts", 25.0, "test")
        state_manager.commit_transaction(txn_id)
        
        # Undo then redo
        state_manager.undo()
        state_manager.redo()
        
        # Check history
        history = state_manager.state.history
        assert any(h.get("action") == "redo" for h in history)
