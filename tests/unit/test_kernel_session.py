"""
tests/unit/test_kernel_session.py - Tests for design session.

BRAVO OWNS THIS FILE.

Tests for Module 15 v1.1 - DesignSession lifecycle.
"""

import pytest
from magnet.kernel import DesignSession, SessionStatus


class MockStateManager:
    """Mock state manager for testing."""

    def __init__(self):
        self._data = {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def write(self, key, value, agent, description):
        self._data[key] = value

    def set(self, key, value, source=None):
        self._data[key] = value


class TestSessionCreation:
    """Tests for session creation."""

    def test_create_session(self):
        """Test creating a new session."""
        state = MockStateManager()
        session_mgr = DesignSession(state)

        session = session_mgr.create("design-001")

        assert session is not None
        assert session.design_id == "design-001"
        assert session.status == SessionStatus.ACTIVE
        assert session.session_id is not None

    def test_create_session_with_name(self):
        """Test creating session with design name."""
        state = MockStateManager()
        session_mgr = DesignSession(state)

        session = session_mgr.create("design-001", design_name="Test Design")

        assert session.design_id == "design-001"
        assert state._data.get("design_name") == "Test Design"

    def test_create_writes_to_state(self):
        """Test session creation writes to state."""
        state = MockStateManager()
        session_mgr = DesignSession(state)

        session = session_mgr.create("design-001")

        # Should write design_id and session to state
        assert state._data.get("design_id") == "design-001"
        assert f"sessions.{session.session_id}" in state._data


class TestSessionLoad:
    """Tests for session loading."""

    def test_load_existing_session(self):
        """Test loading an existing session."""
        state = MockStateManager()
        session_mgr = DesignSession(state)

        # Create and get session ID
        original = session_mgr.create("design-001")
        session_id = original.session_id

        # Create new session manager and load
        new_mgr = DesignSession(state)
        loaded = new_mgr.load(session_id)

        assert loaded is not None
        assert loaded.session_id == session_id
        assert loaded.design_id == "design-001"

    def test_load_nonexistent_session(self):
        """Test loading non-existent session returns None."""
        state = MockStateManager()
        session_mgr = DesignSession(state)

        result = session_mgr.load("nonexistent-id")

        assert result is None


class TestSessionLifecycle:
    """Tests for session lifecycle management."""

    def test_pause_session(self):
        """Test pausing a session."""
        state = MockStateManager()
        session_mgr = DesignSession(state)
        session_mgr.create("design-001")

        session_mgr.pause()

        session = session_mgr.get_current()
        assert session.status == SessionStatus.PAUSED

    def test_resume_session(self):
        """Test resuming a paused session."""
        state = MockStateManager()
        session_mgr = DesignSession(state)
        session_mgr.create("design-001")
        session_mgr.pause()

        session_mgr.resume()

        session = session_mgr.get_current()
        assert session.status == SessionStatus.ACTIVE

    def test_resume_only_paused(self):
        """Test resume only works on paused sessions."""
        state = MockStateManager()
        session_mgr = DesignSession(state)
        session_mgr.create("design-001")

        # Session is active, not paused
        session_mgr.resume()

        session = session_mgr.get_current()
        assert session.status == SessionStatus.ACTIVE

    def test_complete_session(self):
        """Test completing a session."""
        state = MockStateManager()
        session_mgr = DesignSession(state)
        session_mgr.create("design-001")

        session_mgr.complete()

        session = session_mgr.get_current()
        assert session.status == SessionStatus.COMPLETED

    def test_cancel_session(self):
        """Test cancelling a session."""
        state = MockStateManager()
        session_mgr = DesignSession(state)
        session_mgr.create("design-001")

        session_mgr.cancel()

        session = session_mgr.get_current()
        assert session.status == SessionStatus.CANCELLED


class TestSessionSave:
    """Tests for session saving."""

    def test_save_session(self):
        """Test explicitly saving session."""
        state = MockStateManager()
        session_mgr = DesignSession(state)
        session = session_mgr.create("design-001")

        # Clear state to verify save writes
        state._data.clear()

        session_mgr.save()

        # Should have written session state back
        assert f"sessions.{session.session_id}" in state._data


class TestSessionSummary:
    """Tests for session summary."""

    def test_get_summary_no_session(self):
        """Test summary with no session."""
        state = MockStateManager()
        session_mgr = DesignSession(state)

        summary = session_mgr.get_summary()

        assert summary["status"] == "no_session"

    def test_get_summary(self):
        """Test getting session summary."""
        state = MockStateManager()
        session_mgr = DesignSession(state)
        session_mgr.create("design-001")

        summary = session_mgr.get_summary()

        assert "session_id" in summary
        assert summary["design_id"] == "design-001"
        assert summary["status"] == "active"
        assert "created_at" in summary
        assert "updated_at" in summary


class TestGetCurrent:
    """Tests for getting current session."""

    def test_get_current_none(self):
        """Test get_current with no session."""
        state = MockStateManager()
        session_mgr = DesignSession(state)

        assert session_mgr.get_current() is None

    def test_get_current(self):
        """Test get_current returns session."""
        state = MockStateManager()
        session_mgr = DesignSession(state)
        session_mgr.create("design-001")

        session = session_mgr.get_current()

        assert session is not None
        assert session.design_id == "design-001"

