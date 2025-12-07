"""
MAGNET State Transitions

Defines legal phase state transitions and transition events.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from magnet.core.enums import PhaseState, DesignPhase, TransitionTrigger


# ==================== Legal State Transitions ====================
# Maps each state to the states it can transition to

LEGAL_TRANSITIONS: Dict[PhaseState, List[PhaseState]] = {
    PhaseState.DRAFT: [
        PhaseState.ACTIVE,
        PhaseState.SKIPPED,
    ],

    PhaseState.ACTIVE: [
        PhaseState.LOCKED,
        PhaseState.DRAFT,
        PhaseState.ERROR,
    ],

    PhaseState.LOCKED: [
        PhaseState.INVALIDATED,
        PhaseState.ACTIVE,
        PhaseState.APPROVED,
    ],

    PhaseState.INVALIDATED: [
        PhaseState.ACTIVE,
        PhaseState.DRAFT,
    ],

    PhaseState.PENDING: [
        PhaseState.DRAFT,
        PhaseState.ACTIVE,
    ],

    PhaseState.COMPLETED: [
        PhaseState.INVALIDATED,
        PhaseState.ACTIVE,
    ],

    PhaseState.APPROVED: [
        PhaseState.INVALIDATED,
        PhaseState.ACTIVE,
    ],

    PhaseState.ERROR: [
        PhaseState.DRAFT,
        PhaseState.ACTIVE,
    ],

    PhaseState.SKIPPED: [
        PhaseState.DRAFT,
    ],
}


# ==================== Transition Event ====================

@dataclass
class TransitionEvent:
    """
    Record of a phase state transition.
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    phase: str = ""
    from_state: str = ""
    to_state: str = ""
    triggered_by: str = ""
    trigger_type: str = "user_request"  # TransitionTrigger value
    reason: str = ""
    downstream_invalidated: List[str] = field(default_factory=list)
    gate_conditions_passed: List[str] = field(default_factory=list)
    gate_conditions_failed: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransitionEvent":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ==================== Transition Validator ====================

class TransitionValidator:
    """
    Validates phase state transitions.
    """

    @staticmethod
    def is_valid_transition(from_state: PhaseState, to_state: PhaseState) -> bool:
        """
        Check if a transition from one state to another is legal.

        Args:
            from_state: Current phase state
            to_state: Target phase state

        Returns:
            True if transition is legal
        """
        legal_targets = LEGAL_TRANSITIONS.get(from_state, [])
        return to_state in legal_targets

    @staticmethod
    def get_valid_transitions(from_state: PhaseState) -> List[PhaseState]:
        """
        Get all valid target states from a given state.

        Args:
            from_state: Current phase state

        Returns:
            List of valid target states
        """
        return LEGAL_TRANSITIONS.get(from_state, [])

    @staticmethod
    def get_transition_description(from_state: PhaseState, to_state: PhaseState) -> str:
        """
        Get a human-readable description of a transition.

        Args:
            from_state: Current state
            to_state: Target state

        Returns:
            Description string
        """
        descriptions = {
            (PhaseState.DRAFT, PhaseState.ACTIVE): "Starting work on phase",
            (PhaseState.ACTIVE, PhaseState.LOCKED): "Completing and locking phase",
            (PhaseState.ACTIVE, PhaseState.DRAFT): "Reverting to draft (uncommitting)",
            (PhaseState.ACTIVE, PhaseState.ERROR): "Phase encountered an error",
            (PhaseState.LOCKED, PhaseState.ACTIVE): "Unlocking for modifications",
            (PhaseState.LOCKED, PhaseState.APPROVED): "Approving locked phase",
            (PhaseState.LOCKED, PhaseState.INVALIDATED): "Invalidating due to upstream changes",
            (PhaseState.INVALIDATED, PhaseState.ACTIVE): "Re-activating invalidated phase",
            (PhaseState.INVALIDATED, PhaseState.DRAFT): "Resetting to draft",
            (PhaseState.APPROVED, PhaseState.ACTIVE): "Revoking approval for modifications",
            (PhaseState.APPROVED, PhaseState.INVALIDATED): "Invalidating approved phase",
            (PhaseState.ERROR, PhaseState.DRAFT): "Resetting from error state",
            (PhaseState.ERROR, PhaseState.ACTIVE): "Retrying after error",
            (PhaseState.DRAFT, PhaseState.SKIPPED): "Skipping phase",
            (PhaseState.SKIPPED, PhaseState.DRAFT): "Un-skipping phase",
            (PhaseState.PENDING, PhaseState.DRAFT): "Moving from pending to draft",
            (PhaseState.PENDING, PhaseState.ACTIVE): "Activating pending phase",
            (PhaseState.COMPLETED, PhaseState.ACTIVE): "Re-opening completed phase",
            (PhaseState.COMPLETED, PhaseState.INVALIDATED): "Invalidating completed phase",
        }

        return descriptions.get(
            (from_state, to_state),
            f"Transitioning from {from_state.value} to {to_state.value}"
        )

    @staticmethod
    def requires_gate_check(to_state: PhaseState) -> bool:
        """
        Check if transitioning to a state requires gate condition validation.

        Args:
            to_state: Target state

        Returns:
            True if gate conditions must be checked
        """
        return to_state in [PhaseState.LOCKED, PhaseState.COMPLETED]

    @staticmethod
    def requires_dependency_check(to_state: PhaseState) -> bool:
        """
        Check if transitioning to a state requires dependency validation.

        Args:
            to_state: Target state

        Returns:
            True if dependencies must be checked
        """
        return to_state in [PhaseState.ACTIVE]

    @staticmethod
    def triggers_cascade_invalidation(from_state: PhaseState, to_state: PhaseState) -> bool:
        """
        Check if a transition should trigger cascade invalidation.

        Args:
            from_state: Current state
            to_state: Target state

        Returns:
            True if downstream phases should be invalidated
        """
        # Unlocking a locked/approved/completed phase triggers cascade
        if from_state in [PhaseState.LOCKED, PhaseState.APPROVED, PhaseState.COMPLETED]:
            if to_state in [PhaseState.ACTIVE, PhaseState.DRAFT]:
                return True
        return False


# ==================== Transition History ====================

class TransitionHistory:
    """
    Maintains a history of phase transitions.
    """

    def __init__(self):
        self._events: List[TransitionEvent] = []

    def record(self, event: TransitionEvent) -> None:
        """Record a transition event."""
        self._events.append(event)

    def get_events(
        self,
        phase: Optional[str] = None,
        limit: int = 100,
    ) -> List[TransitionEvent]:
        """
        Get transition events, optionally filtered by phase.

        Args:
            phase: Optional phase to filter by
            limit: Maximum number of events to return

        Returns:
            List of transition events
        """
        events = self._events
        if phase:
            events = [e for e in events if e.phase == phase]
        return events[-limit:]

    def get_last_transition(self, phase: str) -> Optional[TransitionEvent]:
        """Get the most recent transition for a phase."""
        for event in reversed(self._events):
            if event.phase == phase:
                return event
        return None

    def to_list(self) -> List[Dict[str, Any]]:
        """Export history as list of dicts."""
        return [e.to_dict() for e in self._events]

    def from_list(self, data: List[Dict[str, Any]]) -> None:
        """Load history from list of dicts."""
        self._events = [TransitionEvent.from_dict(d) for d in data]

    def clear(self) -> None:
        """Clear all history."""
        self._events = []


# ==================== Transition Rules ====================

# States that indicate work is complete
COMPLETION_STATES = [
    PhaseState.LOCKED,
    PhaseState.APPROVED,
    PhaseState.COMPLETED,
]

# States that indicate phase can accept changes
EDITABLE_STATES = [
    PhaseState.DRAFT,
    PhaseState.ACTIVE,
]

# States that indicate phase needs attention
ATTENTION_STATES = [
    PhaseState.INVALIDATED,
    PhaseState.ERROR,
    PhaseState.PENDING,
]


def is_phase_complete(state: PhaseState) -> bool:
    """Check if a phase state indicates completion."""
    return state in COMPLETION_STATES


def is_phase_editable(state: PhaseState) -> bool:
    """Check if a phase state allows editing."""
    return state in EDITABLE_STATES


def needs_attention(state: PhaseState) -> bool:
    """Check if a phase state needs user attention."""
    return state in ATTENTION_STATES


def get_state_color(state: PhaseState) -> str:
    """Get a display color for a phase state."""
    colors = {
        PhaseState.DRAFT: "gray",
        PhaseState.ACTIVE: "blue",
        PhaseState.LOCKED: "green",
        PhaseState.INVALIDATED: "orange",
        PhaseState.PENDING: "yellow",
        PhaseState.COMPLETED: "green",
        PhaseState.APPROVED: "green",
        PhaseState.ERROR: "red",
        PhaseState.SKIPPED: "gray",
    }
    return colors.get(state, "gray")


def get_state_icon(state: PhaseState) -> str:
    """Get a display icon for a phase state."""
    icons = {
        PhaseState.DRAFT: "📝",
        PhaseState.ACTIVE: "🔄",
        PhaseState.LOCKED: "🔒",
        PhaseState.INVALIDATED: "⚠️",
        PhaseState.PENDING: "⏳",
        PhaseState.COMPLETED: "✅",
        PhaseState.APPROVED: "✓",
        PhaseState.ERROR: "❌",
        PhaseState.SKIPPED: "⏭️",
    }
    return icons.get(state, "•")
