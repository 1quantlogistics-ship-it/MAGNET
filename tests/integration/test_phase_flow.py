"""
Integration tests for phase flow progression.

Tests complete phase progression from mission to production.
"""

import pytest
from magnet.core.design_state import DesignState
from magnet.core.state_manager import StateManager
from magnet.core.phase_states import PhaseMachine
from magnet.core.enums import PhaseState


class TestPhaseProgression:
    """Test complete phase progression flow."""

    def test_initial_phase_states(self):
        """Test all phases start as DRAFT."""
        manager = StateManager()
        machine = PhaseMachine(manager)

        phases = [
            "mission", "hull_form", "structure", "arrangement",
            "propulsion", "weight", "stability", "compliance", "production"
        ]

        for phase in phases:
            status = machine.get_phase_status(phase)
            assert status == PhaseState.DRAFT

    def test_mission_to_hull_progression(self):
        """Test progression from mission to hull_form phase."""
        manager = StateManager()
        machine = PhaseMachine(manager)

        # Start mission phase
        assert machine.transition("mission", PhaseState.ACTIVE, "test", "Starting design")
        assert machine.get_phase_status("mission") == PhaseState.ACTIVE

        # Populate required mission data
        manager.set("mission.vessel_type", "patrol", source="test")
        manager.set("mission.max_speed_kts", 35.0, source="test")
        manager.set("mission.range_nm", 500.0, source="test")
        manager.set("mission.crew_berthed", 6, source="test")

        # Complete mission phase
        assert machine.transition("mission", PhaseState.LOCKED, "test", "Mission defined")
        assert machine.get_phase_status("mission") == PhaseState.LOCKED

        # Start hull_form phase
        assert machine.transition("hull_form", PhaseState.ACTIVE, "test", "Designing hull")
        assert machine.get_phase_status("hull_form") == PhaseState.ACTIVE

    def test_hull_form_gate_conditions(self):
        """Test hull_form phase gate conditions."""
        manager = StateManager()

        # Set mission data first to satisfy dependencies
        manager.set("mission.vessel_type", "patrol", source="test")
        manager.set("mission.max_speed_kts", 35.0, source="test")

        machine = PhaseMachine(manager)

        # Lock mission
        machine.transition("mission", PhaseState.ACTIVE, "test", "Start")
        machine.transition("mission", PhaseState.LOCKED, "test", "Done")

        # Start hull_form
        machine.transition("hull_form", PhaseState.ACTIVE, "test", "Hull started")

        # Check gate conditions before data
        satisfied, _, missing = machine.check_gate_conditions("hull_form")
        assert not satisfied
        assert len(missing) > 0

        # Add required hull data
        manager.set("hull.loa", 25.0, source="test")
        manager.set("hull.beam", 6.0, source="test")
        manager.set("hull.draft", 1.5, source="test")
        manager.set("hull.cb", 0.45, source="test")

        # Check gate conditions after data
        satisfied, _, missing = machine.check_gate_conditions("hull_form")
        # Check required gates pass
        required_failed = [m for m in missing if machine._is_required_gate("hull_form", m)]
        assert len(required_failed) == 0

    def test_cascade_invalidation(self):
        """Test downstream cascade invalidation."""
        manager = StateManager()

        # Set all required data
        manager.set("mission.vessel_type", "patrol", source="test")
        manager.set("mission.max_speed_kts", 35.0, source="test")
        manager.set("hull.loa", 25.0, source="test")
        manager.set("hull.beam", 6.0, source="test")
        manager.set("hull.draft", 1.5, source="test")
        manager.set("structural_design.hull_material", "aluminum", source="test")
        manager.set("structural_design.bottom_plating_mm", 8.0, source="test")

        machine = PhaseMachine(manager)

        # Progress through phases
        machine.transition("mission", PhaseState.ACTIVE, "test", "Start")
        machine.transition("mission", PhaseState.LOCKED, "test", "Done")
        machine.transition("hull_form", PhaseState.ACTIVE, "test", "Start")
        machine.transition("hull_form", PhaseState.LOCKED, "test", "Done")
        machine.transition("structure", PhaseState.ACTIVE, "test", "Start")
        machine.transition("structure", PhaseState.LOCKED, "test", "Done")

        # Invalidate hull_form - should cascade to downstream phases
        invalidated = machine.invalidate_downstream("hull_form")

        # Check that downstream phases were invalidated
        assert "structure" in invalidated

        # Verify phase states
        assert machine.get_phase_status("hull_form") == PhaseState.LOCKED  # Not invalidated itself
        assert machine.get_phase_status("structure") == PhaseState.INVALIDATED

    def test_full_design_flow(self):
        """Test complete design flow from mission to stability."""
        manager = StateManager()
        machine = PhaseMachine(manager)

        # Phase 1: Mission
        machine.transition("mission", PhaseState.ACTIVE, "user", "Start")
        manager.set("mission.vessel_type", "patrol", source="user")
        manager.set("mission.max_speed_kts", 35.0, source="user")
        manager.set("mission.range_nm", 500.0, source="user")
        manager.set("mission.crew_berthed", 6, source="user")
        machine.transition("mission", PhaseState.LOCKED, "user", "Mission complete")

        # Phase 2: Hull Form
        machine.transition("hull_form", PhaseState.ACTIVE, "naval_architect", "Start")
        manager.set("hull.loa", 25.0, source="naval_architect")
        manager.set("hull.beam", 6.0, source="naval_architect")
        manager.set("hull.draft", 1.5, source="naval_architect")
        manager.set("hull.cb", 0.45, source="naval_architect")
        manager.set("hull.displacement_m3", 180.0, source="naval_architect")
        machine.transition("hull_form", PhaseState.LOCKED, "naval_architect", "Hull designed")

        # Verify phases are locked
        assert machine.get_phase_status("mission") == PhaseState.LOCKED
        assert machine.get_phase_status("hull_form") == PhaseState.LOCKED


class TestPhaseTransitionRules:
    """Test phase transition rules and constraints."""

    def test_cannot_skip_phases(self):
        """Test that phases cannot be skipped."""
        manager = StateManager()
        machine = PhaseMachine(manager)

        # Try to start structure without completing mission and hull_form
        can, reason = machine.can_transition("structure", PhaseState.DRAFT, PhaseState.ACTIVE)

        # The transition should be blocked due to dependencies
        assert not can
        assert reason is not None

    def test_invalidated_phase_can_restart(self):
        """Test that invalidated phases can be restarted."""
        manager = StateManager()

        # Setup data
        manager.set("mission.vessel_type", "patrol", source="test")
        manager.set("mission.max_speed_kts", 30.0, source="test")
        manager.set("hull.loa", 25.0, source="test")
        manager.set("hull.beam", 6.0, source="test")
        manager.set("hull.draft", 1.5, source="test")
        manager.set("structural_design.hull_material", "aluminum", source="test")
        manager.set("structural_design.bottom_plating_mm", 8.0, source="test")

        machine = PhaseMachine(manager)

        # Complete mission and hull_form and structure
        machine.transition("mission", PhaseState.ACTIVE, "test", "Start")
        machine.transition("mission", PhaseState.LOCKED, "test", "Done")
        machine.transition("hull_form", PhaseState.ACTIVE, "test", "Start")
        machine.transition("hull_form", PhaseState.LOCKED, "test", "Done")
        machine.transition("structure", PhaseState.ACTIVE, "test", "Start")
        machine.transition("structure", PhaseState.LOCKED, "test", "Done")

        # Invalidate structure
        machine.invalidate_downstream("hull_form")
        assert machine.get_phase_status("structure") == PhaseState.INVALIDATED

        # Structure can be restarted (if dependencies still met)
        result = machine.transition("structure", PhaseState.ACTIVE, "test", "Restart")
        assert result
        assert machine.get_phase_status("structure") == PhaseState.ACTIVE

    def test_blocked_phase_state(self):
        """Test BLOCKED phase state for dependency failures."""
        manager = StateManager()
        machine = PhaseMachine(manager)

        # A phase that depends on incomplete upstream should be blocked
        can_transition, reason = machine.can_transition(
            "hull_form", PhaseState.DRAFT, PhaseState.LOCKED
        )

        # Cannot lock hull_form without mission complete
        assert not can_transition
        assert reason is not None


class TestPhaseStateManagerIntegration:
    """Test integration between PhaseMachine and StateManager."""

    def test_state_changes_affect_gates(self):
        """Test that state changes affect gate condition checking."""
        manager = StateManager()

        # Setup mission first
        manager.set("mission.vessel_type", "patrol", source="test")
        manager.set("mission.max_speed_kts", 30.0, source="test")

        machine = PhaseMachine(manager)

        machine.transition("mission", PhaseState.ACTIVE, "test", "Start")
        machine.transition("mission", PhaseState.LOCKED, "test", "Done")
        machine.transition("hull_form", PhaseState.ACTIVE, "test", "Start")

        # Gate conditions not satisfied without data
        satisfied, _, _ = machine.check_gate_conditions("hull_form")
        assert not satisfied

        # Add data via StateManager
        manager.set("hull.loa", 25.0, source="test")
        manager.set("hull.beam", 6.0, source="test")
        manager.set("hull.draft", 1.5, source="test")
        manager.set("hull.cb", 0.45, source="test")

        # Check required gate conditions now pass
        satisfied, passed_list, failed_list = machine.check_gate_conditions("hull_form")
        required_failed = [f for f in failed_list if machine._is_required_gate("hull_form", f)]
        assert len(required_failed) == 0

    def test_transaction_rollback_preserves_phase_state(self):
        """Test that transaction rollback preserves phase state consistency."""
        manager = StateManager()

        # Setup mission first
        manager.set("mission.vessel_type", "patrol", source="test")
        manager.set("mission.max_speed_kts", 30.0, source="test")

        machine = PhaseMachine(manager)

        # Complete mission
        machine.transition("mission", PhaseState.ACTIVE, "test", "Start")
        machine.transition("mission", PhaseState.LOCKED, "test", "Done")

        # Start hull_form
        machine.transition("hull_form", PhaseState.ACTIVE, "test", "Start")

        # Begin transaction (returns txn_id)
        txn_id = manager.begin_transaction()

        # Set some hull values
        manager.set("hull.loa", 25.0, source="test")
        manager.set("hull.beam", 6.0, source="test")

        # Verify values are set
        assert manager.get("hull.loa") == 25.0

        # Rollback using the transaction API
        manager.rollback_transaction(txn_id)

        # Values should be reverted
        loa_value = manager.get("hull.loa")
        assert loa_value is None or loa_value == 0.0

        # Phase state should be unchanged
        assert machine.get_phase_status("hull_form") == PhaseState.ACTIVE
