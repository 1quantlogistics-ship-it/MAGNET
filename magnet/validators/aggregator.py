"""
MAGNET Result Aggregator

Module 04 v1.1 - Production-Ready

Aggregates validation results for gate conditions.

v1.1: FIX #7 - Added staleness, contract errors, intent violations, missing validators.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, TYPE_CHECKING
import logging

from .taxonomy import (
    ValidatorState,
    ValidationResult,
    ValidationFinding,
    ResultSeverity,
)
from .executor import ExecutionState
from .topology import ValidatorTopology

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger(__name__)


# =============================================================================
# GATE STATUS
# =============================================================================

@dataclass
class GateStatus:
    """
    Status of a gate condition check.

    FIX #7: Now includes staleness, contract errors, intent violations.
    """
    gate_id: str
    can_advance: bool

    # Validator summaries
    required_passed: int = 0
    required_failed: int = 0
    recommended_passed: int = 0
    recommended_failed: int = 0

    # Blocking issues
    blocking_validators: List[str] = field(default_factory=list)
    blocking_findings: List[ValidationFinding] = field(default_factory=list)

    # Warnings
    warning_validators: List[str] = field(default_factory=list)
    warning_findings: List[ValidationFinding] = field(default_factory=list)

    # FIX #7: Additional blocking conditions
    stale_parameters: List[str] = field(default_factory=list)
    missing_validators: List[str] = field(default_factory=list)
    contract_errors: List[str] = field(default_factory=list)
    intent_violations: List[str] = field(default_factory=list)

    # All results
    validator_results: Dict[str, ValidationResult] = field(default_factory=dict)

    # Metadata
    checked_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def has_blocking_conditions(self) -> bool:
        """Are there any conditions blocking advancement?"""
        return (
            self.required_failed > 0 or
            len(self.stale_parameters) > 0 or
            len(self.missing_validators) > 0 or
            len(self.contract_errors) > 0 or
            len(self.intent_violations) > 0
        )

    def get_all_blocking_messages(self) -> List[str]:
        """
        Get all blocking messages for UI display.

        Provides consolidated blocking summary.
        """
        messages = []

        for v_id in self.blocking_validators:
            result = self.validator_results.get(v_id)
            if result:
                for f in result.findings:
                    if f.severity == ResultSeverity.ERROR:
                        messages.append(f"[{v_id}] {f.message}")
            else:
                messages.append(f"[{v_id}] Did not run")

        for param in self.stale_parameters:
            messages.append(f"[STALE] Parameter {param} needs recalculation")

        for v_id in self.missing_validators:
            messages.append(f"[MISSING] Validator {v_id} not registered")

        for error in self.contract_errors:
            messages.append(f"[CONTRACT] {error}")

        for violation in self.intent_violations:
            messages.append(f"[INTENT] {violation}")

        return messages

    def get_all_warning_messages(self) -> List[str]:
        """Get all warning messages for UI display."""
        messages = []

        for v_id in self.warning_validators:
            result = self.validator_results.get(v_id)
            if result:
                for f in result.findings:
                    if f.severity == ResultSeverity.WARNING:
                        messages.append(f"[{v_id}] {f.message}")

        return messages

    def get_summary(self) -> Dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "can_advance": self.can_advance,
            "required_passed": self.required_passed,
            "required_failed": self.required_failed,
            "recommended_passed": self.recommended_passed,
            "recommended_failed": self.recommended_failed,
            "blocking_count": len(self.blocking_validators),
            "warning_count": len(self.warning_validators),
            "stale_count": len(self.stale_parameters),
            "missing_count": len(self.missing_validators),
            "contract_error_count": len(self.contract_errors),
            "intent_violation_count": len(self.intent_violations),
            "checked_at": self.checked_at.isoformat(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Full serialization."""
        return {
            **self.get_summary(),
            "blocking_validators": self.blocking_validators,
            "blocking_messages": self.get_all_blocking_messages(),
            "warning_validators": self.warning_validators,
            "warning_messages": self.get_all_warning_messages(),
            "stale_parameters": self.stale_parameters,
            "missing_validators": self.missing_validators,
            "contract_errors": self.contract_errors,
            "intent_violations": self.intent_violations,
        }


# =============================================================================
# RESULT AGGREGATOR
# =============================================================================

class ResultAggregator:
    """
    Aggregates validation results for phase gate conditions.

    FIX #7: Now checks staleness, contracts, and design intent.
    """

    def __init__(
        self,
        topology: ValidatorTopology,
        state_manager: Optional["StateManager"] = None,
        contract_layer: Optional[Any] = None,
        intent_engine: Optional[Any] = None
    ):
        self._topology = topology
        self._state_manager = state_manager
        self._contract_layer = contract_layer
        self._intent_engine = intent_engine

    def check_gate(
        self,
        phase: str,
        execution_state: ExecutionState
    ) -> GateStatus:
        """Check if gate conditions are met for a phase."""
        status = GateStatus(gate_id=phase, can_advance=True)

        gate_validators = self._topology.get_gate_validators_for_phase(phase)

        for validator_id in gate_validators:
            node = self._topology.get_node(validator_id)
            if not node:
                # FIX #7: Track missing validators
                status.missing_validators.append(validator_id)
                continue

            definition = node.validator
            result = execution_state.results.get(validator_id)

            if result:
                status.validator_results[validator_id] = result

            is_required = definition.gate_severity == ResultSeverity.ERROR

            if not result:
                # FIX #7: Missing result is blocking
                if is_required:
                    status.required_failed += 1
                    status.blocking_validators.append(validator_id)
                else:
                    status.recommended_failed += 1
            elif result.state in (ValidatorState.ERROR, ValidatorState.BLOCKED):
                if is_required:
                    status.required_failed += 1
                    status.blocking_validators.append(validator_id)
            elif result.state == ValidatorState.FAILED:
                if is_required:
                    status.required_failed += 1
                    status.blocking_validators.append(validator_id)
                    status.blocking_findings.extend(
                        f for f in result.findings if f.severity == ResultSeverity.ERROR
                    )
                else:
                    status.recommended_failed += 1
            elif result.state == ValidatorState.PASSED:
                if is_required:
                    status.required_passed += 1
                else:
                    status.recommended_passed += 1
            elif result.state == ValidatorState.WARNING:
                if is_required:
                    status.required_passed += 1
                else:
                    status.recommended_passed += 1
                status.warning_validators.append(validator_id)
                status.warning_findings.extend(
                    f for f in result.findings if f.severity == ResultSeverity.WARNING
                )

        # FIX #7: Check staleness
        if self._state_manager:
            status.stale_parameters = self._check_stale_parameters(phase)

        # FIX #7: Check contract layer
        if self._contract_layer:
            status.contract_errors = self._check_contracts(phase)

        # FIX #7: Check design intent
        if self._intent_engine:
            status.intent_violations = self._check_intent(phase)

        # FIX #7: Can only advance if ALL conditions met
        status.can_advance = not status.has_blocking_conditions

        return status

    def check_all_gates(
        self,
        execution_state: ExecutionState
    ) -> Dict[str, GateStatus]:
        """Check gate conditions for all phases."""
        from magnet.dependencies.graph import PHASE_OWNERSHIP

        results = {}
        for phase in PHASE_OWNERSHIP.keys():
            results[phase] = self.check_gate(phase, execution_state)

        return results

    def get_blocking_summary(
        self,
        execution_state: ExecutionState
    ) -> Dict[str, Any]:
        """Get summary of what's blocking phase advancement."""
        all_gates = self.check_all_gates(execution_state)

        blocked_phases = []
        total_blocking = 0
        total_warnings = 0

        for phase, status in all_gates.items():
            if not status.can_advance:
                blocked_phases.append(phase)
            total_blocking += len(status.blocking_validators)
            total_warnings += len(status.warning_validators)

        return {
            "blocked_phases": blocked_phases,
            "total_blocked_phases": len(blocked_phases),
            "total_blocking_validators": total_blocking,
            "total_warnings": total_warnings,
            "gate_statuses": {p: s.get_summary() for p, s in all_gates.items()},
        }

    def _check_stale_parameters(self, phase: str) -> List[str]:
        """FIX #7: Check for stale parameters in this phase."""
        stale = []

        if not self._state_manager:
            return stale

        # Get parameters owned by this phase
        from magnet.dependencies.graph import PHASE_OWNERSHIP
        params = PHASE_OWNERSHIP.get(phase, [])

        for param in params:
            # Check if parameter is marked stale
            if hasattr(self._state_manager, 'is_field_stale'):
                if self._state_manager.is_field_stale(param):
                    stale.append(param)

        return stale

    def _check_contracts(self, phase: str) -> List[str]:
        """FIX #7: Check contract layer for violations."""
        if not self._contract_layer:
            return []

        try:
            if hasattr(self._contract_layer, 'get_violations_for_phase'):
                violations = self._contract_layer.get_violations_for_phase(phase)
                return [str(v) for v in violations]
        except Exception as e:
            logger.warning(f"Contract check failed for {phase}: {e}")

        return []

    def _check_intent(self, phase: str) -> List[str]:
        """FIX #7: Check design intent violations."""
        if not self._intent_engine:
            return []

        try:
            if hasattr(self._intent_engine, 'get_violations_for_phase'):
                violations = self._intent_engine.get_violations_for_phase(phase)
                return [str(v) for v in violations]
        except Exception as e:
            logger.warning(f"Intent check failed for {phase}: {e}")

        return []


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_aggregator(
    state_manager: Optional["StateManager"] = None,
) -> ResultAggregator:
    """Create an aggregator with a fresh topology."""
    topology = ValidatorTopology()
    topology.add_all_validators()
    topology.build()

    return ResultAggregator(
        topology=topology,
        state_manager=state_manager,
    )


def check_phase_gate(
    phase: str,
    execution_state: ExecutionState,
    state_manager: Optional["StateManager"] = None,
) -> GateStatus:
    """Convenience function to check a single phase gate."""
    aggregator = create_aggregator(state_manager)
    return aggregator.check_gate(phase, execution_state)
