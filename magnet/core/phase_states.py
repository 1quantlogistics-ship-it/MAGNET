"""
MAGNET Phase State Machine v1.1

Manages the 9-phase design workflow with gate conditions,
transitions, and cascade invalidation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum

from magnet.core.enums import PhaseState, DesignPhase
from magnet.core.phase_ownership import (
    PHASE_ORDER,
    PHASE_DEPENDENCIES,
    DOWNSTREAM_PHASES,
    get_all_downstream,
)


# ==================== Gate Conditions ====================

@dataclass
class GateCondition:
    """
    A condition that must be met before a phase can be locked.
    """
    name: str
    description: str
    check_path: str  # State path to check
    check_fn: Optional[Callable[[Any], bool]] = None  # Custom validation function
    required: bool = True  # If False, it's a warning not an error
    error_message: str = ""

    def evaluate(self, state_manager: Any) -> Tuple[bool, str]:
        """
        Evaluate this gate condition against the current state.

        Returns:
            Tuple of (passed, message)
        """
        value = state_manager.get(self.check_path)

        if self.check_fn is not None:
            try:
                passed = self.check_fn(value)
            except Exception as e:
                return False, f"Gate check error: {e}"
        else:
            # Default check: value must be non-None and non-empty
            passed = value is not None
            if passed and isinstance(value, (list, dict, str)):
                passed = len(value) > 0

        if passed:
            return True, f"Gate '{self.name}' passed"
        else:
            msg = self.error_message or f"Gate '{self.name}' failed: {self.check_path} not set"
            return False, msg


# ==================== Gate Condition Definitions ====================

def _check_positive(value: Any) -> bool:
    """Check that value is positive number."""
    return value is not None and isinstance(value, (int, float)) and value > 0


def _check_non_negative(value: Any) -> bool:
    """Check that value is non-negative number."""
    return value is not None and isinstance(value, (int, float)) and value >= 0


def _check_coefficient(value: Any) -> bool:
    """Check that value is a valid coefficient (0-1)."""
    return value is not None and isinstance(value, (int, float)) and 0 <= value <= 1


def _check_geometry_ready(value: Any) -> bool:
    """Check that geometry has been generated."""
    return value is True


def _check_compliance_passed(value: Any) -> bool:
    """Check that compliance checks passed."""
    return value is True


GATE_CONDITIONS: Dict[str, List[GateCondition]] = {
    "mission": [
        GateCondition(
            name="vessel_type_set",
            description="Vessel type must be specified",
            check_path="mission.vessel_type",
            error_message="Vessel type is required",
        ),
        GateCondition(
            name="max_speed_set",
            description="Maximum speed must be specified",
            check_path="mission.max_speed_kts",
            check_fn=_check_positive,
            error_message="Maximum speed must be positive",
        ),
        GateCondition(
            name="range_set",
            description="Operating range should be specified",
            check_path="mission.range_nm",
            check_fn=_check_positive,
            required=False,
            error_message="Operating range not specified",
        ),
    ],

    "hull_form": [
        GateCondition(
            name="loa_set",
            description="Length overall must be specified",
            check_path="hull.loa",
            check_fn=_check_positive,
            error_message="LOA must be positive",
        ),
        GateCondition(
            name="beam_set",
            description="Beam must be specified",
            check_path="hull.beam",
            check_fn=_check_positive,
            error_message="Beam must be positive",
        ),
        GateCondition(
            name="draft_set",
            description="Draft must be specified",
            check_path="hull.draft",
            check_fn=_check_positive,
            error_message="Draft must be positive",
        ),
        GateCondition(
            name="cb_valid",
            description="Block coefficient should be set",
            check_path="hull.cb",
            check_fn=_check_coefficient,
            required=False,
            error_message="Block coefficient should be between 0 and 1",
        ),
        GateCondition(
            name="geometry_generated",
            description="Hull geometry must be generated",
            check_path="vision.geometry_generated",
            check_fn=_check_geometry_ready,
            required=False,
            error_message="Hull geometry not yet generated",
        ),
    ],

    "structure": [
        GateCondition(
            name="material_set",
            description="Hull material must be specified",
            check_path="structural_design.hull_material",
            error_message="Hull material is required",
        ),
        GateCondition(
            name="bottom_plating_set",
            description="Bottom plating thickness must be specified",
            check_path="structural_design.bottom_plating_mm",
            check_fn=_check_positive,
            error_message="Bottom plating thickness required",
        ),
        GateCondition(
            name="frame_spacing_set",
            description="Frame spacing should be specified",
            check_path="structural_design.frame_spacing_mm",
            check_fn=_check_positive,
            required=False,
            error_message="Frame spacing not specified",
        ),
    ],

    "arrangement": [
        GateCondition(
            name="compartments_defined",
            description="Compartments should be defined",
            check_path="arrangement.compartments",
            required=False,
            error_message="No compartments defined",
        ),
        GateCondition(
            name="fuel_capacity_set",
            description="Fuel tank capacity should be specified",
            check_path="arrangement.total_fuel_capacity_l",
            check_fn=_check_positive,
            required=False,
            error_message="Fuel capacity not specified",
        ),
    ],

    "propulsion": [
        GateCondition(
            name="power_set",
            description="Installed power must be specified",
            check_path="propulsion.total_installed_power_kw",
            check_fn=_check_positive,
            error_message="Installed power must be positive",
        ),
        GateCondition(
            name="num_engines_set",
            description="Number of engines must be specified",
            check_path="propulsion.num_engines",
            check_fn=lambda v: v is not None and v > 0,
            error_message="Number of engines required",
        ),
        GateCondition(
            name="propeller_set",
            description="Propeller diameter should be specified",
            check_path="propulsion.propeller_diameter_m",
            check_fn=_check_positive,
            required=False,
            error_message="Propeller diameter not specified",
        ),
    ],

    "weight": [
        GateCondition(
            name="lightship_set",
            description="Lightship weight must be calculated",
            check_path="weight.lightship_weight_mt",
            check_fn=_check_positive,
            error_message="Lightship weight required",
        ),
        GateCondition(
            name="displacement_set",
            description="Full load displacement must be calculated",
            check_path="weight.full_load_displacement_mt",
            check_fn=_check_positive,
            error_message="Full load displacement required",
        ),
        GateCondition(
            name="lcg_set",
            description="LCG should be calculated",
            check_path="weight.lightship_lcg_m",
            required=False,
            error_message="LCG not calculated",
        ),
    ],

    "stability": [
        GateCondition(
            name="gm_calculated",
            description="GM must be calculated",
            check_path="stability.gm_transverse_m",
            check_fn=_check_positive,
            error_message="GM must be positive (stable)",
        ),
        GateCondition(
            name="gz_curve_generated",
            description="GZ curve should be generated",
            check_path="stability.gz_curve",
            required=False,
            error_message="GZ curve not generated",
        ),
        GateCondition(
            name="imo_intact_checked",
            description="IMO intact stability should be checked",
            check_path="stability.imo_intact_passed",
            required=False,
            error_message="IMO intact stability not checked",
        ),
    ],

    "compliance": [
        GateCondition(
            name="compliance_checked",
            description="All compliance checks must pass",
            check_path="compliance.overall_passed",
            check_fn=_check_compliance_passed,
            error_message="Compliance checks not passed",
        ),
        GateCondition(
            name="stability_compliant",
            description="Stability checks must pass",
            check_path="compliance.stability_checks_passed",
            check_fn=_check_compliance_passed,
            error_message="Stability compliance not passed",
        ),
    ],

    "production": [
        GateCondition(
            name="build_hours_estimated",
            description="Build hours should be estimated",
            check_path="production.build_hours",
            check_fn=_check_positive,
            required=False,
            error_message="Build hours not estimated",
        ),
        GateCondition(
            name="cost_estimated",
            description="Total cost should be estimated",
            check_path="cost.total_cost",
            check_fn=_check_positive,
            required=False,
            error_message="Cost not estimated",
        ),
    ],
}


# ==================== Phase Machine ====================

class PhaseMachine:
    """
    Finite State Machine for managing design phase transitions.

    Handles:
    - Phase state tracking (DRAFT, ACTIVE, LOCKED, etc.)
    - Gate condition evaluation
    - Cascade invalidation when upstream phases change
    - Transition validation
    """

    def __init__(self, state_manager: Any):
        """
        Initialize the phase machine.

        Args:
            state_manager: StateManager instance to operate on
        """
        self._state_manager = state_manager
        self._initialize_phases()

    def _initialize_phases(self) -> None:
        """Initialize all phases to DRAFT if not already set."""
        phase_states = self._state_manager._get_phase_states_internal()

        for phase in PHASE_ORDER:
            if phase not in phase_states:
                self._state_manager._set_phase_state_internal(
                    phase=phase,
                    state=PhaseState.DRAFT.value,
                    entered_by="system",
                    metadata={"initialized": True},
                )

    # ==================== Status Methods ====================

    def get_phase_status(self, phase: str) -> PhaseState:
        """
        Get the current status of a phase.

        Args:
            phase: Phase name

        Returns:
            Current PhaseState value
        """
        phase_states = self._state_manager._get_phase_states_internal()

        if phase in phase_states:
            state_str = phase_states[phase].get("state", "draft")
            try:
                return PhaseState(state_str)
            except ValueError:
                return PhaseState.DRAFT

        return PhaseState.DRAFT

    def get_all_phase_states(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the state of all phases.

        Returns:
            Dictionary mapping phase names to their state info
        """
        return self._state_manager._get_phase_states_internal()

    # ==================== Transition Methods ====================

    def can_transition(
        self,
        phase: str,
        from_state: PhaseState,
        to_state: PhaseState,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a phase transition is valid.

        Args:
            phase: Phase name
            from_state: Current state
            to_state: Desired state

        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        from magnet.core.state_transitions import LEGAL_TRANSITIONS

        # Check if transition is legal
        legal_targets = LEGAL_TRANSITIONS.get(from_state, [])
        if to_state not in legal_targets:
            return False, f"Transition from {from_state.value} to {to_state.value} not allowed"

        # If transitioning to ACTIVE, check dependencies
        if to_state == PhaseState.ACTIVE:
            can_start, blockers = self.can_start_phase(phase)
            if not can_start:
                return False, f"Dependencies not met: {', '.join(blockers)}"

        # If transitioning to LOCKED, check gate conditions
        if to_state == PhaseState.LOCKED:
            passed, passed_list, failed_list = self.check_gate_conditions(phase)
            required_failed = [f for f in failed_list if self._is_required_gate(phase, f)]
            if required_failed:
                return False, f"Required gate conditions failed: {', '.join(required_failed)}"

        return True, None

    def transition(
        self,
        phase: str,
        to_state: PhaseState,
        source: str,
        reason: str = "",
    ) -> bool:
        """
        Perform a phase state transition.

        Args:
            phase: Phase name
            to_state: Target state
            source: Who is triggering the transition
            reason: Optional reason for the transition

        Returns:
            True if transition was successful
        """
        current_state = self.get_phase_status(phase)

        # Validate transition
        can_trans, error = self.can_transition(phase, current_state, to_state)
        if not can_trans:
            return False

        # If unlocking a locked phase, invalidate downstream
        invalidated = []
        if current_state == PhaseState.LOCKED and to_state in [PhaseState.ACTIVE, PhaseState.DRAFT]:
            invalidated = self.invalidate_downstream(phase)

        # Perform the transition
        self._state_manager._set_phase_state_internal(
            phase=phase,
            state=to_state.value,
            entered_by=source,
            metadata={
                "reason": reason,
                "from_state": current_state.value,
                "downstream_invalidated": invalidated,
            },
        )

        return True

    def _is_required_gate(self, phase: str, gate_name: str) -> bool:
        """Check if a gate condition is required."""
        gates = GATE_CONDITIONS.get(phase, [])
        for gate in gates:
            if gate.name == gate_name:
                return gate.required
        return False

    # ==================== Dependency Methods ====================

    def can_start_phase(self, phase: str) -> Tuple[bool, List[str]]:
        """
        Check if all dependencies are satisfied to start a phase.

        Args:
            phase: Phase name

        Returns:
            Tuple of (can_start, list_of_blocking_phases)
        """
        dependencies = PHASE_DEPENDENCIES.get(phase, [])
        blockers = []

        for dep in dependencies:
            dep_status = self.get_phase_status(dep)
            if dep_status not in [PhaseState.LOCKED, PhaseState.APPROVED, PhaseState.COMPLETED]:
                blockers.append(dep)

        return len(blockers) == 0, blockers

    def invalidate_downstream(self, phase: str) -> List[str]:
        """
        Invalidate all phases downstream of the given phase.

        Args:
            phase: The phase that was modified

        Returns:
            List of phase names that were invalidated
        """
        downstream = get_all_downstream(phase)
        invalidated = []

        for downstream_phase in downstream:
            current_status = self.get_phase_status(downstream_phase)
            if current_status in [PhaseState.LOCKED, PhaseState.APPROVED, PhaseState.COMPLETED]:
                self._state_manager._set_phase_state_internal(
                    phase=downstream_phase,
                    state=PhaseState.INVALIDATED.value,
                    entered_by="system",
                    metadata={
                        "invalidated_by_phase": phase,
                        "previous_state": current_status.value,
                    },
                )
                invalidated.append(downstream_phase)

        return invalidated

    # ==================== Gate Condition Methods ====================

    def check_gate_conditions(self, phase: str) -> Tuple[bool, List[str], List[str]]:
        """
        Check if gate conditions are met for locking a phase.

        Args:
            phase: Phase name

        Returns:
            Tuple of (all_required_passed, passed_conditions, failed_conditions)
        """
        gates = GATE_CONDITIONS.get(phase, [])
        passed = []
        failed = []

        for gate in gates:
            result, message = gate.evaluate(self._state_manager)
            if result:
                passed.append(gate.name)
            else:
                failed.append(gate.name)

        # Check if all required gates passed
        required_failed = [
            gate.name for gate in gates
            if gate.required and gate.name in failed
        ]

        return len(required_failed) == 0, passed, failed

    def get_gate_conditions(self, phase: str) -> List[GateCondition]:
        """
        Get the gate conditions for a phase.

        Args:
            phase: Phase name

        Returns:
            List of GateCondition objects
        """
        return GATE_CONDITIONS.get(phase, [])

    # ==================== Approval Methods ====================

    def approve_phase(self, phase: str, approver: str, comment: str = "") -> bool:
        """
        Approve a locked phase.

        Args:
            phase: Phase name
            approver: Who is approving
            comment: Optional approval comment

        Returns:
            True if approval was successful
        """
        current_status = self.get_phase_status(phase)

        if current_status != PhaseState.LOCKED:
            return False

        self._state_manager._set_phase_state_internal(
            phase=phase,
            state=PhaseState.APPROVED.value,
            entered_by=approver,
            metadata={
                "approval_comment": comment,
                "approved_by": approver,
                "approved_at": datetime.utcnow().isoformat(),
            },
        )

        return True

    # ==================== Utility Methods ====================

    def get_available_transitions(self, phase: str) -> List[PhaseState]:
        """
        Get valid transitions from the current state.

        Args:
            phase: Phase name

        Returns:
            List of states that can be transitioned to
        """
        from magnet.core.state_transitions import LEGAL_TRANSITIONS

        current = self.get_phase_status(phase)
        legal = LEGAL_TRANSITIONS.get(current, [])

        # Filter by what's actually achievable
        available = []
        for target in legal:
            can_trans, _ = self.can_transition(phase, current, target)
            if can_trans:
                available.append(target)

        return available

    def persist(self) -> None:
        """Persist phase states to the underlying state manager."""
        # Phase states are already stored in state manager
        pass

    def load(self) -> None:
        """Load phase states from the underlying state manager."""
        self._initialize_phases()

    def summary(self) -> str:
        """Get a summary of all phase states."""
        lines = ["Phase Status Summary:", "=" * 40]

        for phase in PHASE_ORDER:
            status = self.get_phase_status(phase)
            can_start, blockers = self.can_start_phase(phase)

            status_str = status.value.upper()
            if not can_start and status == PhaseState.DRAFT:
                status_str += f" (blocked by: {', '.join(blockers)})"

            lines.append(f"  {phase:15} : {status_str}")

        return "\n".join(lines)
