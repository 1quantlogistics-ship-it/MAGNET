"""
kernel/session.py - Design session management.

BRAVO OWNS THIS FILE.

Module 15 v1.1 - Design session manager.
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, TYPE_CHECKING

from .enums import SessionStatus
from .schema import SessionState

if TYPE_CHECKING:
    from ..core.state_manager import StateManager


class DesignSession:
    """
    Design session manager.

    Manages the lifecycle of a design session including
    state persistence and recovery.
    """

    def __init__(self, state_manager: 'StateManager'):
        """
        Initialize session manager.

        Args:
            state_manager: StateManager for design state
        """
        self.state = state_manager
        self._session: Optional[SessionState] = None

    def create(self, design_id: str, design_name: str = None) -> SessionState:
        """
        Create a new design session.

        Args:
            design_id: Unique design identifier
            design_name: Human-readable design name
        """
        self._session = SessionState(
            session_id=str(uuid.uuid4()),
            design_id=design_id,
            status=SessionStatus.ACTIVE,
        )

        # Write initial state - Hole #7 Fix: Proper source for provenance
        source = "kernel/session"
        self.state.set("design_id", design_id, source)
        if design_name:
            self.state.set("design_name", design_name, source)

        self._write_session_state()
        return self._session

    def load(self, session_id: str) -> Optional[SessionState]:
        """
        Load an existing session.

        Args:
            session_id: Session ID to load
        """
        session_data = self.state.get(f"sessions.{session_id}")
        if session_data:
            self._session = self._deserialize_session(session_data)
            return self._session
        return None

    def save(self) -> None:
        """Save current session state."""
        if self._session:
            self._write_session_state()

    def pause(self) -> None:
        """Pause current session."""
        if self._session:
            self._session.status = SessionStatus.PAUSED
            self._session.updated_at = datetime.now(timezone.utc)
            self._write_session_state()

    def resume(self) -> None:
        """Resume paused session."""
        if self._session and self._session.status == SessionStatus.PAUSED:
            self._session.status = SessionStatus.ACTIVE
            self._session.updated_at = datetime.now(timezone.utc)
            self._write_session_state()

    def complete(self) -> None:
        """Mark session as completed."""
        if self._session:
            self._session.status = SessionStatus.COMPLETED
            self._session.updated_at = datetime.now(timezone.utc)
            self._write_session_state()

    def cancel(self) -> None:
        """Cancel current session."""
        if self._session:
            self._session.status = SessionStatus.CANCELLED
            self._session.updated_at = datetime.now(timezone.utc)
            self._write_session_state()

    def get_current(self) -> Optional[SessionState]:
        """Get current session."""
        return self._session

    def get_summary(self) -> Dict[str, Any]:
        """Get session summary."""
        if not self._session:
            return {"status": "no_session"}

        return {
            "session_id": self._session.session_id,
            "design_id": self._session.design_id,
            "status": self._session.status.value,
            "created_at": self._session.created_at.isoformat(),
            "updated_at": self._session.updated_at.isoformat(),
            "current_phase": self._session.current_phase,
            "completed_phases": self._session.completed_phases,
            "pass_rate": self._session.overall_pass_rate,
        }

    def _write_session_state(self) -> None:
        """Write session to state manager."""
        if self._session:
            source = "kernel/session"  # Hole #7 Fix: Proper source for provenance
            self.state.set(
                f"sessions.{self._session.session_id}",
                self._session.to_dict(),
                source
            )
            self.state.set("kernel.current_session", self._session.session_id, source)

    def _deserialize_session(self, data: Dict[str, Any]) -> SessionState:
        """Deserialize session from dict."""
        return SessionState(
            session_id=data["session_id"],
            design_id=data["design_id"],
            status=SessionStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            current_phase=data.get("current_phase"),
            completed_phases=data.get("completed_phases", []),
        )
