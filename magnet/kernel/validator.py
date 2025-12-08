"""
kernel/validator.py - Kernel validator.

BRAVO OWNS THIS FILE.

Module 15 v1.1 - Kernel validator for orchestration.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, TYPE_CHECKING
import logging

from .orchestrator import ValidationOrchestrator

from ..validators.taxonomy import (
    ValidatorInterface,
    ValidatorDefinition,
    ValidationResult,
    ValidatorState,
    ValidationFinding,
    ResultSeverity,
    ValidatorCategory,
    ValidatorPriority,
)

if TYPE_CHECKING:
    from ..core.state_manager import StateManager

logger = logging.getLogger(__name__)


KERNEL_DEFINITION = ValidatorDefinition(
    validator_id="kernel/orchestrator",
    name="Kernel Orchestrator",
    description="Orchestrates the full validation pipeline",
    category=ValidatorCategory.CUSTOM,  # Kernel is a system-level validator
    priority=ValidatorPriority.CRITICAL,
    phase="kernel",
    is_gate_condition=False,
    depends_on_validators=[],  # Kernel depends on nothing
    depends_on_parameters=[],
    produces_parameters=[
        "kernel.status",
        "kernel.current_phase",
        "kernel.phase_history",
        "kernel.session",
        "kernel.gate_status",
    ],
    timeout_seconds=600,  # 10 minutes for full pipeline
    tags=["kernel", "orchestrator", "pipeline"],
)


class KernelValidator(ValidatorInterface):
    """
    Kernel validator for design orchestration.

    Validates that the design pipeline has been properly executed
    and all phases have completed successfully.

    Reads:
        kernel.status - Current kernel status
        kernel.phase_history - Completed phases
        kernel.gate_status - Gate results

    Writes:
        kernel.validation_complete - Whether validation is complete
        kernel.validation_summary - Summary of validation
    """

    def __init__(self, definition: ValidatorDefinition = None):
        super().__init__(definition or KERNEL_DEFINITION)

    def validate(
        self,
        state_manager: 'StateManager',
        context: Dict[str, Any],
    ) -> ValidationResult:
        """Validate kernel state and pipeline completion."""
        result = ValidationResult(
            validator_id=self.definition.validator_id,
            state=ValidatorState.RUNNING,
            started_at=datetime.now(timezone.utc),
        )

        try:
            # Check kernel status
            kernel_status = state_manager.get("kernel.status")
            if kernel_status is None:
                result.add_finding(ValidationFinding(
                    finding_id="kern-001",
                    severity=ResultSeverity.WARNING,
                    message="Kernel status not set - pipeline may not have run",
                ))

            # Check completed phases
            completed_phases = state_manager.get("kernel.phase_history", [])
            total_phases = 13  # Standard MAGNET phase count

            if len(completed_phases) < total_phases:
                result.add_finding(ValidationFinding(
                    finding_id="kern-002",
                    severity=ResultSeverity.INFO,
                    message=f"Pipeline incomplete: {len(completed_phases)}/{total_phases} phases",
                ))

            # Check gate status
            gate_status = state_manager.get("kernel.gate_status", {})
            failed_gates = [k for k, v in gate_status.items() if not v]
            if failed_gates:
                result.add_finding(ValidationFinding(
                    finding_id="kern-003",
                    severity=ResultSeverity.ERROR,
                    message=f"Failed gates: {', '.join(failed_gates)}",
                ))

            # Check critical phase results
            critical_phases = ["compliance", "stability"]
            for phase in critical_phases:
                if phase not in completed_phases:
                    result.add_finding(ValidationFinding(
                        finding_id=f"kern-004-{phase}",
                        severity=ResultSeverity.WARNING,
                        message=f"Critical phase not completed: {phase}",
                    ))

            # Write validation summary
            agent = "kernel/validator"

            validation_summary = {
                "completed_phases": len(completed_phases),
                "total_phases": total_phases,
                "failed_gates": failed_gates,
                "kernel_status": kernel_status,
                "findings": len(result.findings),
                "errors": result.error_count,
                "warnings": result.warning_count,
            }

            state_manager.write(
                "kernel.validation_summary",
                validation_summary,
                agent,
                "Kernel validation summary",
            )

            state_manager.write(
                "kernel.validation_complete",
                result.error_count == 0,
                agent,
                "Validation complete status",
            )

            # Determine result state
            if result.error_count > 0:
                result.state = ValidatorState.FAILED
            elif result.warning_count > 0:
                result.state = ValidatorState.WARNING
            else:
                result.state = ValidatorState.PASSED

            logger.debug(
                f"Kernel validation complete: {result.state.value}, "
                f"{len(completed_phases)} phases, {len(failed_gates)} failed gates"
            )

        except Exception as e:
            result.state = ValidatorState.ERROR
            result.error_message = str(e)
            logger.error(f"Kernel validation error: {e}")

        result.completed_at = datetime.now(timezone.utc)
        return result


def get_kernel_definition() -> ValidatorDefinition:
    """Get kernel validator definition."""
    return KERNEL_DEFINITION


def register_kernel_validators(registry: Dict[str, ValidatorInterface]) -> None:
    """Register kernel validators with a registry."""
    defn = get_kernel_definition()
    registry[defn.validator_id] = KernelValidator(defn)
