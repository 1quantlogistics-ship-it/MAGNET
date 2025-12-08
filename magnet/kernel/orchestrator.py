"""
kernel/orchestrator.py - Validation orchestrator.

BRAVO OWNS THIS FILE.

Module 15 v1.1 - High-level validation orchestrator.
"""

from __future__ import annotations
from typing import Any, Dict, List, TYPE_CHECKING

from .conductor import Conductor
from .registry import PhaseRegistry

if TYPE_CHECKING:
    from ..core.state_manager import StateManager
    from ..validators.taxonomy import ValidatorInterface


class ValidationOrchestrator:
    """
    High-level orchestrator for validation pipeline.

    Provides a simplified interface for running the full validation pipeline.
    """

    def __init__(
        self,
        state_manager: 'StateManager',
        registry: 'PhaseRegistry' = None,
    ):
        """
        Initialize orchestrator.

        Args:
            state_manager: StateManager for design state
            registry: Optional custom phase registry
        """
        self.state = state_manager
        self.registry = registry or PhaseRegistry()
        self.conductor = Conductor(state_manager, self.registry)

        self._validators: Dict[str, 'ValidatorInterface'] = {}

    def register_validator(
        self,
        validator_id: str,
        validator: 'ValidatorInterface',
    ) -> None:
        """Register a validator."""
        self._validators[validator_id] = validator
        self.conductor.register_validator(validator_id, validator)

    def register_validators(
        self,
        validators: Dict[str, 'ValidatorInterface'],
    ) -> None:
        """Register multiple validators."""
        for vid, validator in validators.items():
            self.register_validator(vid, validator)

    def run_full_pipeline(
        self,
        design_id: str = None,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Run the full validation pipeline.

        Args:
            design_id: Optional design ID
            context: Optional context for validators

        Returns:
            Summary dict with results
        """
        # Create session
        design_id = design_id or self.state.get("design_id", "unknown")
        session = self.conductor.create_session(design_id)

        # Run all phases
        results = self.conductor.run_all_phases(context or {})

        # Write state
        self.conductor.write_to_state()

        # Build summary
        summary = {
            "session_id": session.session_id,
            "design_id": design_id,
            "status": session.status.value,
            "phases_completed": len(session.completed_phases),
            "phases_total": len(self.registry._phases),
            "validators_run": session.total_validators_run,
            "validators_passed": session.total_validators_passed,
            "pass_rate": session.overall_pass_rate,
            "gate_results": {
                name: result.passed
                for name, result in session.gate_results.items()
            },
            "phase_results": {
                r.phase_name: r.status.value for r in results
            },
        }

        return summary

    def run_single_phase(
        self,
        phase_name: str,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Run a single phase.

        Args:
            phase_name: Phase to run
            context: Optional context
        """
        if not self.conductor.get_session():
            self.conductor.create_session(
                self.state.get("design_id", "unknown")
            )

        result = self.conductor.run_phase(phase_name, context)
        self.conductor.write_to_state()

        return result.to_dict()

    def run_to_phase(
        self,
        target_phase: str,
        design_id: str = None,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Run pipeline up to and including target phase.

        Args:
            target_phase: Phase to run to
            design_id: Optional design ID
            context: Optional context
        """
        design_id = design_id or self.state.get("design_id", "unknown")

        if not self.conductor.get_session():
            self.conductor.create_session(design_id)

        results = self.conductor.run_to_phase(target_phase, context)
        self.conductor.write_to_state()

        session = self.conductor.get_session()
        return {
            "target_phase": target_phase,
            "phases_run": len(results),
            "status": session.status.value if session else "unknown",
            "phase_results": {r.phase_name: r.status.value for r in results},
        }

    def get_available_phases(self) -> List[str]:
        """Get list of available phases."""
        return [p.name for p in self.registry.get_phases_in_order()]

    def get_phase_status(self, phase_name: str) -> str:
        """Get status of a phase."""
        session = self.conductor.get_session()
        if session and phase_name in session.phase_results:
            return session.phase_results[phase_name].status.value
        return "pending"

    def get_phase_dependencies(self, phase_name: str) -> List[str]:
        """Get dependencies for a phase."""
        return self.registry.get_dependencies(phase_name)

    def get_summary(self) -> Dict[str, Any]:
        """Get orchestrator summary."""
        return self.conductor.get_status_summary()
