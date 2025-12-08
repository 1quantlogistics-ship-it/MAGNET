"""
kernel/conductor.py - Phase conductor/orchestrator.

BRAVO OWNS THIS FILE.

Module 15 v1.1 - Phase conductor for MAGNET design process.
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging

from .enums import PhaseStatus, GateCondition, SessionStatus
from .schema import PhaseResult, GateResult, SessionState
from .registry import PhaseRegistry, PhaseDefinition

if TYPE_CHECKING:
    from ..core.state_manager import StateManager
    from ..validators.taxonomy import ValidatorInterface

logger = logging.getLogger(__name__)


class Conductor:
    """
    Phase conductor for MAGNET design process.

    Manages phase execution, gate evaluation, and session state.
    """

    def __init__(
        self,
        state_manager: 'StateManager',
        registry: PhaseRegistry = None,
    ):
        """
        Initialize conductor.

        Args:
            state_manager: StateManager for design state
            registry: Phase registry (creates default if None)
        """
        self.state = state_manager
        self.registry = registry or PhaseRegistry()

        self._validators: Dict[str, 'ValidatorInterface'] = {}
        self._session: Optional[SessionState] = None

    def register_validator(
        self,
        validator_id: str,
        validator: 'ValidatorInterface',
    ) -> None:
        """Register a validator instance."""
        self._validators[validator_id] = validator

    def create_session(self, design_id: str) -> SessionState:
        """Create a new design session."""
        self._session = SessionState(
            session_id=str(uuid.uuid4()),
            design_id=design_id,
            status=SessionStatus.INITIALIZING,
        )

        self._session.status = SessionStatus.ACTIVE
        logger.info(f"Created session {self._session.session_id} for design {design_id}")
        return self._session

    def get_session(self) -> Optional[SessionState]:
        """Get current session."""
        return self._session

    def run_phase(self, phase_name: str, context: Dict[str, Any] = None) -> PhaseResult:
        """
        Run a single phase.

        Args:
            phase_name: Name of phase to run
            context: Optional context for validators
        """
        phase = self.registry.get_phase(phase_name)
        if not phase:
            return PhaseResult(
                phase_name=phase_name,
                status=PhaseStatus.FAILED,
                errors=[f"Unknown phase: {phase_name}"],
            )

        # Check dependencies
        for dep in phase.depends_on:
            if self._session and dep not in self._session.completed_phases:
                return PhaseResult(
                    phase_name=phase_name,
                    status=PhaseStatus.BLOCKED,
                    errors=[f"Dependency not completed: {dep}"],
                )

        # Execute phase
        result = self._execute_phase(phase, context or {})

        # Update session
        if self._session:
            self._session.current_phase = phase_name
            self._session.add_phase_result(result)

        # Evaluate gate if applicable
        if phase.is_gate and result.status == PhaseStatus.COMPLETED:
            gate_result = self._evaluate_gate(phase, result)
            if self._session:
                self._session.add_gate_result(gate_result)

            if not gate_result.passed:
                result.status = PhaseStatus.FAILED
                result.errors.append(f"Gate failed: {gate_result.blocking_failures}")

        logger.debug(f"Phase {phase_name} completed with status {result.status.value}")
        return result

    def run_all_phases(
        self,
        context: Dict[str, Any] = None,
        stop_on_failure: bool = True,
    ) -> List[PhaseResult]:
        """
        Run all phases in order.

        Args:
            context: Optional context for validators
            stop_on_failure: Stop if a phase fails
        """
        results = []

        for phase in self.registry.get_phases_in_order():
            result = self.run_phase(phase.name, context)
            results.append(result)

            if stop_on_failure and result.status in [PhaseStatus.FAILED, PhaseStatus.BLOCKED]:
                break

        # Update session status
        if self._session:
            if any(r.status == PhaseStatus.FAILED for r in results):
                self._session.status = SessionStatus.FAILED
            elif all(r.status == PhaseStatus.COMPLETED for r in results):
                self._session.status = SessionStatus.COMPLETED

        return results

    def run_to_phase(
        self,
        target_phase: str,
        context: Dict[str, Any] = None,
    ) -> List[PhaseResult]:
        """
        Run all phases up to and including target phase.
        """
        results = []

        for phase in self.registry.get_phases_in_order():
            result = self.run_phase(phase.name, context)
            results.append(result)

            if phase.name == target_phase:
                break

            if result.status in [PhaseStatus.FAILED, PhaseStatus.BLOCKED]:
                break

        return results

    def run_from_phase(
        self,
        start_phase: str,
        context: Dict[str, Any] = None,
    ) -> List[PhaseResult]:
        """
        Run all phases starting from a specific phase.
        """
        results = []
        started = False

        for phase in self.registry.get_phases_in_order():
            if phase.name == start_phase:
                started = True

            if started:
                result = self.run_phase(phase.name, context)
                results.append(result)

                if result.status in [PhaseStatus.FAILED, PhaseStatus.BLOCKED]:
                    break

        return results

    def _execute_phase(
        self,
        phase: PhaseDefinition,
        context: Dict[str, Any],
    ) -> PhaseResult:
        """Execute a phase by running its validators."""
        result = PhaseResult(
            phase_name=phase.name,
            status=PhaseStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )

        try:
            for validator_id in phase.validators:
                validator = self._validators.get(validator_id)

                if validator is None:
                    result.warnings.append(f"Validator not registered: {validator_id}")
                    continue

                result.validators_run += 1

                try:
                    val_result = validator.validate(self.state, context)

                    if val_result.state.value in ["passed", "warning"]:
                        result.validators_passed += 1
                    else:
                        result.validators_failed += 1
                        if val_result.error_message:
                            result.errors.append(val_result.error_message)

                except Exception as e:
                    result.validators_failed += 1
                    result.errors.append(f"Validator {validator_id} error: {str(e)}")
                    logger.error(f"Validator {validator_id} error: {e}")

            # Determine result status
            if result.validators_failed > 0:
                result.status = PhaseStatus.FAILED
            else:
                result.status = PhaseStatus.COMPLETED

        except Exception as e:
            result.status = PhaseStatus.FAILED
            result.errors.append(f"Phase execution error: {str(e)}")
            logger.error(f"Phase {phase.name} execution error: {e}")

        result.completed_at = datetime.now(timezone.utc)
        return result

    def _evaluate_gate(
        self,
        phase: PhaseDefinition,
        phase_result: PhaseResult,
    ) -> GateResult:
        """Evaluate a gate condition."""
        gate_result = GateResult(
            gate_name=f"{phase.name}_gate",
            condition=phase.gate_condition,
            passed=False,
            evaluated_at=datetime.now(timezone.utc),
        )

        if phase.gate_condition == GateCondition.ALL_PASS:
            gate_result.passed = phase_result.validators_failed == 0
            gate_result.actual_value = phase_result.pass_rate
            gate_result.threshold = 1.0

        elif phase.gate_condition == GateCondition.CRITICAL_PASS:
            # Check compliance.fail_count for critical failures
            fail_count = self.state.get("compliance.fail_count", 0)
            gate_result.passed = fail_count == 0
            gate_result.actual_value = float(fail_count)
            gate_result.threshold = 0.0

        elif phase.gate_condition == GateCondition.THRESHOLD:
            gate_result.threshold = phase.gate_threshold
            gate_result.actual_value = phase_result.pass_rate
            gate_result.passed = phase_result.pass_rate >= phase.gate_threshold

        elif phase.gate_condition == GateCondition.MANUAL:
            # Manual gates default to not passed, require explicit approval
            gate_result.passed = False
            gate_result.blocking_failures = ["Manual approval required"]

        if not gate_result.passed:
            gate_result.blocking_failures = phase_result.errors.copy()

        logger.debug(f"Gate {gate_result.gate_name} evaluated: passed={gate_result.passed}")
        return gate_result

    def approve_gate(self, gate_name: str) -> bool:
        """Manually approve a gate."""
        if self._session and gate_name in self._session.gate_results:
            gate_result = self._session.gate_results[gate_name]
            if gate_result.condition == GateCondition.MANUAL:
                gate_result.passed = True
                gate_result.blocking_failures = []
                return True
        return False

    def write_to_state(self) -> None:
        """Write conductor state to state manager."""
        if self._session:
            agent = "kernel/conductor"

            self.state.write("kernel.session", self._session.to_dict(),
                            agent, "Session state")
            self.state.write("kernel.status", self._session.status.value,
                            agent, "Kernel status")
            self.state.write("kernel.current_phase", self._session.current_phase,
                            agent, "Current phase")
            self.state.write("kernel.phase_history", self._session.completed_phases,
                            agent, "Completed phases")

            # Gate status
            gate_status = {
                name: result.passed
                for name, result in self._session.gate_results.items()
            }
            self.state.write("kernel.gate_status", gate_status,
                            agent, "Gate status")

    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of conductor status."""
        if not self._session:
            return {"status": "no_session"}

        return {
            "session_id": self._session.session_id,
            "design_id": self._session.design_id,
            "status": self._session.status.value,
            "current_phase": self._session.current_phase,
            "completed_phases": self._session.completed_phases,
            "total_validators_run": self._session.total_validators_run,
            "total_validators_passed": self._session.total_validators_passed,
            "overall_pass_rate": self._session.overall_pass_rate,
            "gate_results": {
                k: {"passed": v.passed, "condition": v.condition.value}
                for k, v in self._session.gate_results.items()
            },
        }
