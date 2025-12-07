"""
Unit tests for StateManager.

Tests path-based access, transactions, and file I/O.
"""

import pytest
import tempfile
import os
from magnet.core.state_manager import StateManager
from magnet.core.design_state import DesignState


class TestStateManagerCreation:
    """Test StateManager creation."""

    def test_create_empty(self):
        """Test creating StateManager without state."""
        manager = StateManager()
        assert manager.state is not None
        assert isinstance(manager.state, DesignState)

    def test_create_with_state(self):
        """Test creating StateManager with existing state."""
        state = DesignState(design_name="Test")
        manager = StateManager(state)
        assert manager.state is state
        assert manager.state.design_name == "Test"


class TestStateManagerPathAccess:
    """Test path-based access."""

    def test_get_simple_path(self):
        """Test getting value at simple path."""
        manager = StateManager()
        manager.state.design_name = "Test"
        assert manager.get("design_name") == "Test"

    def test_get_nested_path(self):
        """Test getting value at nested path."""
        manager = StateManager()
        manager.state.mission.vessel_type = "patrol"
        assert manager.get("mission.vessel_type") == "patrol"

    def test_get_with_default(self):
        """Test getting with default value."""
        manager = StateManager()
        result = manager.get("nonexistent.path", default="default_value")
        assert result == "default_value"

    def test_set_nested_path(self):
        """Test setting value at nested path."""
        manager = StateManager()
        success = manager.set("mission.vessel_type", "ferry", source="test")
        assert success
        assert manager.state.mission.vessel_type == "ferry"

    def test_set_numeric_value(self):
        """Test setting numeric value."""
        manager = StateManager()
        manager.set("hull.loa", 25.0, source="test")
        assert manager.get("hull.loa") == 25.0

    def test_set_records_history(self):
        """Test that set records history."""
        manager = StateManager()
        initial_history_len = len(manager.state.history)
        manager.set("mission.vessel_type", "patrol", source="test")
        assert len(manager.state.history) > initial_history_len


class TestStateManagerAliases:
    """Test alias resolution."""

    def test_get_with_alias(self):
        """Test getting value using alias."""
        manager = StateManager()
        manager.state.mission.max_speed_kts = 30.0
        # Use alias
        result = manager.get("mission.max_speed_knots")
        assert result == 30.0

    def test_set_with_alias(self):
        """Test setting value using alias."""
        manager = StateManager()
        manager.set("mission.max_speed_knots", 35.0, source="test")
        assert manager.state.mission.max_speed_kts == 35.0


class TestStateManagerTransactions:
    """Test transaction support."""

    def test_begin_transaction(self):
        """Test beginning a transaction."""
        manager = StateManager()
        txn_id = manager.begin_transaction()
        assert txn_id is not None
        assert manager.in_transaction()

    def test_commit_transaction(self):
        """Test committing a transaction."""
        manager = StateManager()
        txn_id = manager.begin_transaction()
        manager.set("mission.vessel_type", "patrol", source="test")
        success = manager.commit_transaction(txn_id)
        assert success
        assert not manager.in_transaction()
        assert manager.state.mission.vessel_type == "patrol"

    def test_rollback_transaction(self):
        """Test rolling back a transaction."""
        manager = StateManager()
        manager.set("mission.vessel_type", "original", source="test")

        txn_id = manager.begin_transaction()
        manager.set("mission.vessel_type", "changed", source="test")
        assert manager.state.mission.vessel_type == "changed"

        success = manager.rollback_transaction(txn_id)
        assert success
        assert not manager.in_transaction()
        assert manager.state.mission.vessel_type == "original"

    def test_nested_transaction_not_allowed(self):
        """Test that nested transactions raise error."""
        manager = StateManager()
        manager.begin_transaction()
        with pytest.raises(RuntimeError):
            manager.begin_transaction()


class TestStateManagerSerialization:
    """Test serialization methods."""

    def test_to_dict(self):
        """Test exporting to dictionary."""
        manager = StateManager()
        manager.state.design_name = "Test"
        data = manager.to_dict()
        assert isinstance(data, dict)
        assert data["design_name"] == "Test"

    def test_from_dict(self):
        """Test loading from dictionary."""
        manager = StateManager()
        data = {"design_name": "Loaded", "mission": {"vessel_type": "ferry"}}
        manager.from_dict(data)
        assert manager.state.design_name == "Loaded"
        assert manager.state.mission.vessel_type == "ferry"


class TestStateManagerFileIO:
    """Test file I/O operations."""

    def test_save_and_load_file(self):
        """Test saving and loading from file."""
        manager = StateManager()
        manager.state.design_name = "File Test"
        manager.state.mission.vessel_type = "patrol"
        manager.state.hull.loa = 25.0

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name

        try:
            manager.save_to_file(filepath)

            # Load into new manager
            manager2 = StateManager()
            manager2.load_from_file(filepath)

            assert manager2.state.design_name == "File Test"
            assert manager2.state.mission.vessel_type == "patrol"
            assert manager2.state.hull.loa == 25.0
        finally:
            os.unlink(filepath)


class TestStateManagerValidation:
    """Test validation methods."""

    def test_validate_valid_state(self):
        """Test validation of valid state."""
        manager = StateManager()
        is_valid, errors = manager.validate()
        # Empty state should have design_id (auto-generated)
        assert is_valid or len(errors) == 0

    def test_validate_invalid_state(self):
        """Test validation catches invalid state."""
        manager = StateManager()
        manager.state.hull.loa = 20.0
        manager.state.hull.lwl = 25.0  # Invalid: lwl > loa

        is_valid, errors = manager.validate()
        assert not is_valid
        assert len(errors) > 0


class TestStateManagerPatch:
    """Test patch method."""

    def test_patch_multiple(self):
        """Test patching multiple values."""
        manager = StateManager()
        updates = {
            "mission.vessel_type": "patrol",
            "hull.loa": 25.0,
            "propulsion.num_engines": 2,
        }
        modified = manager.patch(updates, source="test")
        assert len(modified) == 3
        assert manager.get("mission.vessel_type") == "patrol"
        assert manager.get("hull.loa") == 25.0


class TestStateManagerDiff:
    """Test diff method."""

    def test_diff_managers(self):
        """Test diffing two managers."""
        manager1 = StateManager()
        manager1.state.mission.vessel_type = "patrol"

        manager2 = StateManager()
        manager2.state.mission.vessel_type = "ferry"

        diff = manager1.diff(manager2)
        assert "mission.vessel_type" in diff


class TestStateManagerUtilities:
    """Test utility methods."""

    def test_get_design_id(self):
        """Test getting design ID."""
        manager = StateManager()
        design_id = manager.get_design_id()
        assert design_id is not None

    def test_get_design_name(self):
        """Test getting design name."""
        manager = StateManager()
        manager.state.design_name = "Test Name"
        assert manager.get_design_name() == "Test Name"

    def test_set_design_name(self):
        """Test setting design name."""
        manager = StateManager()
        manager.set_design_name("New Name", source="test")
        assert manager.state.design_name == "New Name"

    def test_summary(self):
        """Test summary output."""
        manager = StateManager()
        manager.state.design_name = "Summary Test"
        summary = manager.summary()
        assert isinstance(summary, str)
        assert "Summary Test" in summary
