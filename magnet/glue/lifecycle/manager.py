"""
glue/lifecycle/manager.py - Design lifecycle manager

ALPHA OWNS THIS FILE.

Module 45: Design Lifecycle & Export - v1.1
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timezone
from enum import Enum
import uuid
import logging

from ..utils import safe_get, safe_write, serialize_state

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger(__name__)


class DesignPhase(Enum):
    """Design phases in MAGNET lifecycle."""
    CONCEPT = "concept"
    PRELIMINARY = "preliminary"
    CONTRACT = "contract"
    DETAIL = "detail"
    PRODUCTION = "production"
    COMPLETE = "complete"

    @classmethod
    def get_order(cls) -> List["DesignPhase"]:
        """Get phases in order."""
        return [
            cls.CONCEPT,
            cls.PRELIMINARY,
            cls.CONTRACT,
            cls.DETAIL,
            cls.PRODUCTION,
            cls.COMPLETE,
        ]

    def next_phase(self) -> Optional["DesignPhase"]:
        """Get the next phase in sequence."""
        order = self.get_order()
        try:
            idx = order.index(self)
            if idx < len(order) - 1:
                return order[idx + 1]
        except ValueError:
            pass
        return None

    def previous_phase(self) -> Optional["DesignPhase"]:
        """Get the previous phase in sequence."""
        order = self.get_order()
        try:
            idx = order.index(self)
            if idx > 0:
                return order[idx - 1]
        except ValueError:
            pass
        return None


class LifecycleState(Enum):
    """State of a design phase."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class PhaseTransition:
    """Record of a phase transition."""

    transition_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    from_phase: Optional[DesignPhase] = None
    to_phase: DesignPhase = DesignPhase.CONCEPT

    from_state: LifecycleState = LifecycleState.NOT_STARTED
    to_state: LifecycleState = LifecycleState.IN_PROGRESS

    # Context
    triggered_by: str = ""
    reason: str = ""

    # Validation
    gate_conditions_checked: List[str] = field(default_factory=list)
    gate_conditions_passed: List[str] = field(default_factory=list)
    gate_conditions_failed: List[str] = field(default_factory=list)

    # Timing
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "from_phase": self.from_phase.value if self.from_phase else None,
            "to_phase": self.to_phase.value,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "triggered_by": self.triggered_by,
            "reason": self.reason,
            "gate_conditions_passed": self.gate_conditions_passed,
            "gate_conditions_failed": self.gate_conditions_failed,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class LifecycleManager:
    """
    Manages design lifecycle and phase transitions.

    v1.1: Uses serialize_state() helper for missing to_dict().
    """

    def __init__(self, state: Optional["StateManager"] = None):
        """
        Initialize lifecycle manager.

        Args:
            state: StateManager to manage
        """
        self.state = state
        self._current_phase: DesignPhase = DesignPhase.CONCEPT
        self._current_state: LifecycleState = LifecycleState.NOT_STARTED
        self._transitions: List[PhaseTransition] = []

        # Gate condition validators by phase
        self._gate_conditions: Dict[DesignPhase, List[str]] = {
            DesignPhase.PRELIMINARY: ["mission_complete", "hull_defined"],
            DesignPhase.CONTRACT: ["stability_verified", "weight_estimated"],
            DesignPhase.DETAIL: ["structure_designed", "systems_specified"],
            DesignPhase.PRODUCTION: ["compliance_verified", "cost_estimated"],
            DesignPhase.COMPLETE: ["all_validators_passed"],
        }

    @property
    def current_phase(self) -> DesignPhase:
        """Get current design phase."""
        return self._current_phase

    @property
    def current_state(self) -> LifecycleState:
        """Get current lifecycle state."""
        return self._current_state

    def start_phase(self, phase: DesignPhase, triggered_by: str = "") -> PhaseTransition:
        """
        Start a new design phase.

        Args:
            phase: Phase to start
            triggered_by: Source of transition

        Returns:
            PhaseTransition record
        """
        transition = PhaseTransition(
            from_phase=self._current_phase,
            to_phase=phase,
            from_state=self._current_state,
            to_state=LifecycleState.IN_PROGRESS,
            triggered_by=triggered_by,
            reason=f"Starting {phase.value} phase",
        )

        self._current_phase = phase
        self._current_state = LifecycleState.IN_PROGRESS
        self._transitions.append(transition)

        # Update state
        self._update_state_lifecycle()

        logger.info(f"Phase transition: {transition.from_phase} -> {transition.to_phase}")

        return transition

    def advance_phase(
        self,
        triggered_by: str = "",
        check_gates: bool = True,
    ) -> Optional[PhaseTransition]:
        """
        Advance to the next design phase.

        Args:
            triggered_by: Source of transition
            check_gates: Whether to check gate conditions

        Returns:
            PhaseTransition if successful, None if at end or gates failed
        """
        next_phase = self._current_phase.next_phase()

        if next_phase is None:
            logger.warning("Already at final phase")
            return None

        # Check gate conditions
        if check_gates:
            passed, failed = self._check_gate_conditions(next_phase)

            if failed:
                logger.warning(f"Gate conditions failed for {next_phase}: {failed}")
                transition = PhaseTransition(
                    from_phase=self._current_phase,
                    to_phase=next_phase,
                    from_state=self._current_state,
                    to_state=LifecycleState.REJECTED,
                    triggered_by=triggered_by,
                    reason=f"Gate conditions failed: {failed}",
                    gate_conditions_passed=passed,
                    gate_conditions_failed=failed,
                )
                self._transitions.append(transition)
                return transition

        return self.start_phase(next_phase, triggered_by)

    def submit_for_review(self, triggered_by: str = "") -> PhaseTransition:
        """Submit current phase for review."""
        transition = PhaseTransition(
            from_phase=self._current_phase,
            to_phase=self._current_phase,
            from_state=self._current_state,
            to_state=LifecycleState.PENDING_REVIEW,
            triggered_by=triggered_by,
            reason="Submitted for review",
        )

        self._current_state = LifecycleState.PENDING_REVIEW
        self._transitions.append(transition)
        self._update_state_lifecycle()

        return transition

    def approve_phase(self, triggered_by: str = "", reason: str = "") -> PhaseTransition:
        """Approve current phase."""
        transition = PhaseTransition(
            from_phase=self._current_phase,
            to_phase=self._current_phase,
            from_state=self._current_state,
            to_state=LifecycleState.APPROVED,
            triggered_by=triggered_by,
            reason=reason or "Phase approved",
        )

        self._current_state = LifecycleState.APPROVED
        self._transitions.append(transition)
        self._update_state_lifecycle()

        return transition

    def reject_phase(self, triggered_by: str = "", reason: str = "") -> PhaseTransition:
        """Reject current phase."""
        transition = PhaseTransition(
            from_phase=self._current_phase,
            to_phase=self._current_phase,
            from_state=self._current_state,
            to_state=LifecycleState.REJECTED,
            triggered_by=triggered_by,
            reason=reason or "Phase rejected",
        )

        self._current_state = LifecycleState.REJECTED
        self._transitions.append(transition)
        self._update_state_lifecycle()

        return transition

    def _check_gate_conditions(self, phase: DesignPhase) -> tuple[List[str], List[str]]:
        """
        Check gate conditions for a phase.

        Returns:
            Tuple of (passed_conditions, failed_conditions)
        """
        conditions = self._gate_conditions.get(phase, [])
        passed = []
        failed = []

        for condition in conditions:
            if self._evaluate_condition(condition):
                passed.append(condition)
            else:
                failed.append(condition)

        return passed, failed

    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate a gate condition."""
        if not self.state:
            return True  # Skip checks if no state

        # Map conditions to state checks
        condition_checks = {
            "mission_complete": lambda: safe_get(self.state, "mission.vessel_type") is not None,
            "hull_defined": lambda: safe_get(self.state, "hull.loa", 0) > 0,
            "stability_verified": lambda: safe_get(self.state, "stability.gm_transverse_m", 0) > 0,
            "weight_estimated": lambda: safe_get(self.state, "weight.lightship_mt", 0) > 0,
            "structure_designed": lambda: safe_get(self.state, "structural_design.complete", False),
            "systems_specified": lambda: safe_get(self.state, "systems.complete", False),
            "compliance_verified": lambda: safe_get(self.state, "compliance.verified", False),
            "cost_estimated": lambda: safe_get(self.state, "cost.total_cost", 0) > 0,
            "all_validators_passed": lambda: safe_get(self.state, "kernel.all_passed", False),
        }

        check_fn = condition_checks.get(condition)
        if check_fn:
            try:
                return check_fn()
            except Exception as e:
                logger.error(f"Condition check failed for {condition}: {e}")
                return False

        # Unknown condition - pass by default
        return True

    def _update_state_lifecycle(self) -> None:
        """Update lifecycle information in state."""
        if self.state:
            safe_write(self.state, "lifecycle.current_phase", self._current_phase.value, "lifecycle")
            safe_write(self.state, "lifecycle.current_state", self._current_state.value, "lifecycle")
            safe_write(
                self.state,
                "lifecycle.last_transition",
                self._transitions[-1].to_dict() if self._transitions else None,
                "lifecycle",
            )

    def get_transitions(self) -> List[PhaseTransition]:
        """Get all transitions."""
        return self._transitions.copy()

    def get_phase_history(self) -> List[Dict[str, Any]]:
        """Get phase history as dicts."""
        return [t.to_dict() for t in self._transitions]

    def get_status(self) -> Dict[str, Any]:
        """Get current lifecycle status."""
        return {
            "current_phase": self._current_phase.value,
            "current_state": self._current_state.value,
            "transition_count": len(self._transitions),
            "can_advance": self._current_phase.next_phase() is not None,
            "can_retreat": self._current_phase.previous_phase() is not None,
        }
