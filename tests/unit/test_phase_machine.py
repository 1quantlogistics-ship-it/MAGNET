"""
Unit tests for PhaseMachine.

Tests phase transitions, dependencies, and cascade invalidation.
"""

import pytest
from magnet.core.phase_states import PhaseMachine, GATE_CONDITIONS
from magnet.core.state_manager import StateManager
from magnet.core.enums import PhaseState
from magnet.core.phase_ownership import PHASE_ORDER, PHASE_DEPENDENCIES


class TestPhaseMachineCreation:
    """Test PhaseMachine creation."""

    def test_create(self):
        """Test creating PhaseMachine."""
        manager = StateManager()
        machine = PhaseMachine(manager)
        assert machine is not None

    def test_initial_states(self):
        """Test initial phase states are DRAFT."""
        manager = StateManager()
        machine = PhaseMachine(manager)

        for phase in PHASE_ORDER:
            status = machine.get_phase_status(phase)
            assert status == PhaseState.DRAFT


class TestPhaseTransitions:
    """Test phase transitions."""

    def test_transition_to_active(self):
        """Test transitioning to ACTIVE."""
        manager = StateManager()
        machine = PhaseMachine(manager)

        # Mission has no dependencies, should be able to activate
        success = machine.transition("mission", PhaseState.ACTIVE, source="test")
        assert success
        assert machine.get_phase_status("mission") == PhaseState.ACTIVE

    def test_transition_blocked_by_dependencies(self):
        """Test transition blocked by unmet dependencies."""
        manager = StateManager()
        machine = PhaseMachine(manager)

        # hull_form depends on mission being locked
        can, reason = machine.can_transition(
            "hull_form",
            PhaseState.DRAFT,
            PhaseState.ACTIVE,
        )
        assert not can
        assert "dependencies" in reason.lower() or "mission" in reason.lower()

    def test_transition_to_locked_requires_gate(self):
        """Test transitioning to LOCKED requires gate conditions."""
        manager = StateManager()
        machine = PhaseMachine(manager)

        # Activate mission
        machine.transition("mission", PhaseState.ACTIVE, source="test")

        # Try to lock without meeting gate conditions
        can, reason = machine.can_transition(
            "mission",
            PhaseState.ACTIVE,
            PhaseState.LOCKED,
        )
        assert not can
        assert "gate" in reason.lower() or "conditions" in reason.lower() or "failed" in reason.lower()

    def test_transition_to_locked_with_gate_met(self):
        """Test transitioning to LOCKED with gate conditions met (requires transaction)."""
        manager = StateManager()

        # Set required mission fields (refinable paths require transaction)
        manager.begin_transaction()
        manager.set("mission.vessel_type", "patrol", source="test")
        manager.set("mission.max_speed_kts", 30.0, source="test")
        manager.commit()

        machine = PhaseMachine(manager)

        # Activate then lock
        machine.transition("mission", PhaseState.ACTIVE, source="test")
        success = machine.transition("mission", PhaseState.LOCKED, source="test")
        assert success
        assert machine.get_phase_status("mission") == PhaseState.LOCKED


class TestCanStartPhase:
    """Test can_start_phase method."""

    def test_can_start_mission(self):
        """Test mission can start (no dependencies)."""
        manager = StateManager()
        machine = PhaseMachine(manager)

        can, blockers = machine.can_start_phase("mission")
        assert can
        assert len(blockers) == 0

    def test_cannot_start_hull_without_mission(self):
        """Test hull_form cannot start without mission."""
        manager = StateManager()
        machine = PhaseMachine(manager)

        can, blockers = machine.can_start_phase("hull_form")
        assert not can
        assert "mission" in blockers


class TestGateConditions:
    """Test gate condition checking."""

    def test_gate_conditions_defined(self):
        """Test gate conditions are defined for phases."""
        for phase in PHASE_ORDER:
            assert phase in GATE_CONDITIONS

    def test_check_gate_mission_empty(self):
        """Test gate check for empty mission."""
        manager = StateManager()
        machine = PhaseMachine(manager)

        passed, passed_list, failed_list = machine.check_gate_conditions("mission")
        assert not passed
        assert len(failed_list) > 0

    def test_check_gate_mission_complete(self):
        """Test gate check for complete mission (requires transaction)."""
        manager = StateManager()
        manager.begin_transaction()
        manager.set("mission.vessel_type", "patrol", source="test")
        manager.set("mission.max_speed_kts", 30.0, source="test")
        manager.commit()

        machine = PhaseMachine(manager)
        passed, passed_list, failed_list = machine.check_gate_conditions("mission")
        # Only required conditions need to pass
        # Check that required conditions pass
        required_failed = [f for f in failed_list if any(
            g.name == f and g.required for g in GATE_CONDITIONS.get("mission", [])
        )]
        assert len(required_failed) == 0


class TestCascadeInvalidation:
    """Test cascade invalidation."""

    def test_invalidate_downstream(self):
        """Test downstream invalidation (requires transaction)."""
        manager = StateManager()
        manager.begin_transaction()
        manager.set("mission.vessel_type", "patrol", source="test")
        manager.set("mission.max_speed_kts", 30.0, source="test")
        manager.set("hull.loa", 25.0, source="test")
        manager.set("hull.beam", 6.0, source="test")
        manager.set("hull.draft", 1.5, source="test")
        manager.commit()

        machine = PhaseMachine(manager)

        # Lock mission
        machine.transition("mission", PhaseState.ACTIVE, source="test")
        machine.transition("mission", PhaseState.LOCKED, source="test")

        # Lock hull_form (dependencies met)
        machine.transition("hull_form", PhaseState.ACTIVE, source="test")
        machine.transition("hull_form", PhaseState.LOCKED, source="test")

        # Invalidate downstream from mission should affect hull_form
        invalidated = machine.invalidate_downstream("mission")
        assert "hull_form" in invalidated
        assert machine.get_phase_status("hull_form") == PhaseState.INVALIDATED


class TestPhaseApproval:
    """Test phase approval."""

    def test_approve_locked_phase(self):
        """Test approving a locked phase (requires transaction)."""
        manager = StateManager()
        manager.begin_transaction()
        manager.set("mission.vessel_type", "patrol", source="test")
        manager.set("mission.max_speed_kts", 30.0, source="test")
        manager.commit()

        machine = PhaseMachine(manager)

        # Lock mission
        machine.transition("mission", PhaseState.ACTIVE, source="test")
        machine.transition("mission", PhaseState.LOCKED, source="test")

        # Approve
        success = machine.approve_phase("mission", approver="reviewer", comment="Looks good")
        assert success
        assert machine.get_phase_status("mission") == PhaseState.APPROVED


class TestGetAllPhaseStates:
    """Test get_all_phase_states method."""

    def test_get_all_states(self):
        """Test getting all phase states."""
        manager = StateManager()
        machine = PhaseMachine(manager)

        states = machine.get_all_phase_states()
        assert isinstance(states, dict)
        assert len(states) == len(PHASE_ORDER)

        for phase in PHASE_ORDER:
            assert phase in states


class TestGetAvailableTransitions:
    """Test get_available_transitions method."""

    def test_available_from_draft(self):
        """Test available transitions from DRAFT."""
        manager = StateManager()
        machine = PhaseMachine(manager)

        # Mission can go to ACTIVE from DRAFT (no deps)
        available = machine.get_available_transitions("mission")
        assert PhaseState.ACTIVE in available

    def test_available_from_active(self):
        """Test available transitions from ACTIVE."""
        manager = StateManager()
        machine = PhaseMachine(manager)

        machine.transition("mission", PhaseState.ACTIVE, source="test")
        available = machine.get_available_transitions("mission")

        # Should be able to go back to DRAFT
        assert PhaseState.DRAFT in available


class TestPhaseMachineSummary:
    """Test utility methods."""

    def test_summary(self):
        """Test summary output."""
        manager = StateManager()
        machine = PhaseMachine(manager)

        summary = machine.summary()
        assert isinstance(summary, str)
        assert "mission" in summary.lower()


class TestPhaseMachinePersistence:
    """Test persistence methods."""

    def test_persist_and_load(self):
        """Test persisting and loading phase states."""
        manager = StateManager()
        machine = PhaseMachine(manager)

        machine.transition("mission", PhaseState.ACTIVE, source="test")
        machine.persist()

        # Create new machine with same manager
        machine2 = PhaseMachine(manager)
        assert machine2.get_phase_status("mission") == PhaseState.ACTIVE
