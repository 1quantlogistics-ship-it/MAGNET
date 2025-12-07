"""
PhaseMachine Contract - Abstract Base Class

Defines the interface for the phase state machine including:
- Phase state enumeration
- Design phase ordering
- Gate conditions and transitions
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PhaseStateEnum(str, Enum):
    """
    Possible states for each design phase.
    """
    DRAFT = "draft"           # Initial state, work in progress
    ACTIVE = "active"         # Currently being worked on
    LOCKED = "locked"         # Completed and locked
    INVALIDATED = "invalidated"  # Upstream change invalidated this phase
    PENDING = "pending"       # Waiting for dependencies
    COMPLETED = "completed"   # Finished (alias for locked in some contexts)
    APPROVED = "approved"     # Explicitly approved by reviewer
    ERROR = "error"           # Phase encountered an error
    SKIPPED = "skipped"       # Phase intentionally skipped


class DesignPhaseEnum(str, Enum):
    """
    The 9 ordered design phases in MAGNET.

    Flow: mission -> hull_form -> structure -> arrangement ->
          propulsion -> weight -> stability -> compliance -> production
    """
    MISSION = "mission"
    HULL_FORM = "hull_form"
    STRUCTURE = "structure"
    ARRANGEMENT = "arrangement"
    PROPULSION = "propulsion"
    WEIGHT = "weight"
    STABILITY = "stability"
    COMPLIANCE = "compliance"
    PRODUCTION = "production"


# Ordered list of design phases for iteration
DESIGN_PHASES: List[str] = [
    "mission",
    "hull_form",
    "structure",
    "arrangement",
    "propulsion",
    "weight",
    "stability",
    "compliance",
    "production",
]

# Phase dependency graph
PHASE_DEPENDENCIES: Dict[str, List[str]] = {
    "mission": [],
    "hull_form": ["mission"],
    "structure": ["hull_form"],
    "arrangement": ["hull_form", "structure"],
    "propulsion": ["hull_form", "mission"],
    "weight": ["structure", "propulsion", "arrangement"],
    "stability": ["hull_form", "weight"],
    "compliance": ["structure", "stability", "weight"],
    "production": ["compliance"],
}


class PhaseMachineContract(ABC):
    """
    Abstract contract for the phase state machine.

    Manages the 9-phase design workflow with:
    - Gate conditions that must pass before phase lock
    - Cascade invalidation when upstream phases change
    - Transition validation
    """

    @abstractmethod
    def get_phase_status(self, phase: str) -> PhaseStateEnum:
        """
        Get the current status of a phase.

        Args:
            phase: Phase name (e.g., 'mission', 'hull_form')

        Returns:
            Current PhaseStateEnum value.
        """
        pass

    @abstractmethod
    def can_transition(
        self,
        phase: str,
        from_state: PhaseStateEnum,
        to_state: PhaseStateEnum,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a phase transition is valid.

        Args:
            phase: Phase name.
            from_state: Current state.
            to_state: Desired state.

        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        pass

    @abstractmethod
    def transition(
        self,
        phase: str,
        to_state: PhaseStateEnum,
        source: str,
        reason: str = "",
    ) -> bool:
        """
        Perform a phase state transition.

        Args:
            phase: Phase name.
            to_state: Target state.
            source: Who is triggering the transition.
            reason: Optional reason for the transition.

        Returns:
            True if transition was successful.
        """
        pass

    @abstractmethod
    def invalidate_downstream(self, phase: str) -> List[str]:
        """
        Invalidate all phases downstream of the given phase.

        Called when a locked phase is unlocked or modified.

        Args:
            phase: The phase that was modified.

        Returns:
            List of phase names that were invalidated.
        """
        pass

    @abstractmethod
    def can_start_phase(self, phase: str) -> Tuple[bool, List[str]]:
        """
        Check if all dependencies are satisfied to start a phase.

        Args:
            phase: Phase name.

        Returns:
            Tuple of (can_start, list_of_blocking_phases)
        """
        pass

    @abstractmethod
    def check_gate_conditions(self, phase: str) -> Tuple[bool, List[str], List[str]]:
        """
        Check if gate conditions are met for locking a phase.

        Args:
            phase: Phase name.

        Returns:
            Tuple of (all_passed, passed_conditions, failed_conditions)
        """
        pass

    @abstractmethod
    def approve_phase(self, phase: str, approver: str, comment: str = "") -> bool:
        """
        Approve a locked phase for downstream progression.

        Args:
            phase: Phase name.
            approver: Who is approving.
            comment: Optional approval comment.

        Returns:
            True if approval was successful.
        """
        pass

    @abstractmethod
    def get_all_phase_states(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the state of all phases.

        Returns:
            Dictionary mapping phase names to their state info.
        """
        pass

    @abstractmethod
    def get_available_transitions(self, phase: str) -> List[PhaseStateEnum]:
        """
        Get valid transitions from the current state.

        Args:
            phase: Phase name.

        Returns:
            List of states that can be transitioned to.
        """
        pass

    @abstractmethod
    def persist(self) -> None:
        """
        Persist phase states to the underlying state manager.
        """
        pass

    @abstractmethod
    def load(self) -> None:
        """
        Load phase states from the underlying state manager.
        """
        pass


# Legal state transitions
LEGAL_TRANSITIONS: Dict[PhaseStateEnum, List[PhaseStateEnum]] = {
    PhaseStateEnum.DRAFT: [PhaseStateEnum.ACTIVE, PhaseStateEnum.SKIPPED],
    PhaseStateEnum.ACTIVE: [PhaseStateEnum.LOCKED, PhaseStateEnum.DRAFT, PhaseStateEnum.ERROR],
    PhaseStateEnum.LOCKED: [PhaseStateEnum.INVALIDATED, PhaseStateEnum.ACTIVE, PhaseStateEnum.APPROVED],
    PhaseStateEnum.INVALIDATED: [PhaseStateEnum.ACTIVE, PhaseStateEnum.DRAFT],
    PhaseStateEnum.PENDING: [PhaseStateEnum.DRAFT, PhaseStateEnum.ACTIVE],
    PhaseStateEnum.COMPLETED: [PhaseStateEnum.INVALIDATED, PhaseStateEnum.ACTIVE],
    PhaseStateEnum.APPROVED: [PhaseStateEnum.INVALIDATED, PhaseStateEnum.ACTIVE],
    PhaseStateEnum.ERROR: [PhaseStateEnum.DRAFT, PhaseStateEnum.ACTIVE],
    PhaseStateEnum.SKIPPED: [PhaseStateEnum.DRAFT],
}
