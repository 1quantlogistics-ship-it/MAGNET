"""
kernel/conductor.py - Phase conductor/orchestrator.

BRAVO OWNS THIS FILE.

Module 15 v1.2 - Phase conductor for MAGNET design process.

v1.2: Added hull synthesis hook for automatic hull generation.
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
    from ..validators.executor import PipelineExecutor
    from ..validators.aggregator import ResultAggregator

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
        pipeline_executor: 'PipelineExecutor' = None,
        result_aggregator: 'ResultAggregator' = None,
    ):
        """
        Initialize conductor.

        Args:
            state_manager: StateManager for design state
            registry: Phase registry (creates default if None)
            pipeline_executor: PipelineExecutor for delegated validation (Guardrail #2)
            result_aggregator: ResultAggregator for gate checking
        """
        self.state = state_manager
        self.registry = registry or PhaseRegistry()
        self._pipeline_executor = pipeline_executor  # Guardrail #2: Single execution authority
        self._result_aggregator = result_aggregator

        self._validators: Dict[str, 'ValidatorInterface'] = {}  # Keep for metadata/fallback
        # Hole #2 Fix: Design-keyed sessions instead of single _session
        self._sessions: Dict[str, SessionState] = {}
        self._session: Optional[SessionState] = None  # Backwards compat: last created session

    def set_pipeline_executor(self, executor: 'PipelineExecutor') -> None:
        """Set the pipeline executor (Guardrail #2: single execution authority)."""
        self._pipeline_executor = executor

    def set_result_aggregator(self, aggregator: 'ResultAggregator') -> None:
        """Set the result aggregator."""
        self._result_aggregator = aggregator

    def register_validator(
        self,
        validator_id: str,
        validator: 'ValidatorInterface',
    ) -> None:
        """Register a validator instance."""
        self._validators[validator_id] = validator

    def create_session(self, design_id: str) -> SessionState:
        """Create a new design session."""
        session = SessionState(
            session_id=str(uuid.uuid4()),
            design_id=design_id,
            status=SessionStatus.INITIALIZING,
        )

        session.status = SessionStatus.ACTIVE
        # Hole #2 Fix: Store by design_id to prevent concurrent request contamination
        self._sessions[design_id] = session
        self._session = session  # Backwards compat
        logger.info(f"Created session {session.session_id} for design {design_id}")
        return session

    def get_session(self, design_id: Optional[str] = None) -> Optional[SessionState]:
        """
        Get session by design_id or current session.

        Hole #2 Fix: Supports design-specific session lookup.
        """
        if design_id:
            return self._sessions.get(design_id)
        return self._session

    def run_phase(self, phase_name: str, context: Dict[str, Any] = None) -> PhaseResult:
        """
        Run a single phase.

        Guardrail #2: Delegates to PipelineExecutor for actual validation.
        Guardrail #1: Checks phase output contracts after validation.

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

        # v1.2: Hull synthesis hook - MUST run BEFORE input contract check
        # (synthesis generates the hull dimensions that contracts require)
        if phase_name == "hull" and not self._hull_exists():
            synthesis_result = self._run_hull_synthesis()
            if synthesis_result and not synthesis_result.is_usable:
                return PhaseResult(
                    phase_name=phase_name,
                    status=PhaseStatus.FAILED,
                    errors=[f"Hull synthesis failed: {synthesis_result.termination_message}"],
                )
            # If synthesis succeeded, continue to input contract check
            # (synthesis should have populated hull.lwl, hull.beam, etc.)

        # Hole #5 Fix: Check INPUT contracts BEFORE execution
        from ..validators.contracts import check_phase_inputs
        input_result = check_phase_inputs(phase_name, self.state)
        if not input_result.satisfied:
            return PhaseResult(
                phase_name=phase_name,
                status=PhaseStatus.BLOCKED,
                errors=[f"Missing required inputs: {input_result.missing_outputs}"],
            )

        # Execute via PipelineExecutor (Guardrail #2) or legacy fallback
        if self._pipeline_executor:
            result = self._execute_via_pipeline(phase, context or {})
        else:
            # Fallback to legacy execution (for backwards compatibility)
            result = self._execute_phase(phase, context or {})

        # Check phase output contract (Guardrail #1)
        from ..validators.contracts import check_phase_contract
        contract_result = check_phase_contract(phase_name, self.state)
        if not contract_result.satisfied:
            result.status = PhaseStatus.FAILED
            result.errors.append(contract_result.message)
            logger.warning(f"Phase {phase_name} failed output contract: {contract_result.missing_outputs}")

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

    def _execute_via_pipeline(
        self,
        phase: PhaseDefinition,
        context: Dict[str, Any],
    ) -> PhaseResult:
        """
        Execute phase validators via PipelineExecutor.

        Guardrail #2: Single execution authority.
        """
        result = PhaseResult(
            phase_name=phase.name,
            status=PhaseStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )

        try:
            # Run validators through PipelineExecutor
            execution_state = self._pipeline_executor.execute_phase(phase.name)

            # Aggregate results
            result.validators_run = len(execution_state.completed) + len(execution_state.failed)
            result.validators_passed = len(execution_state.completed)
            result.validators_failed = len(execution_state.failed)

            # Collect errors from failed validators
            for vid in execution_state.failed:
                if vid in execution_state.results:
                    val_result = execution_state.results[vid]
                    if val_result.error_message:
                        result.errors.append(f"{vid}: {val_result.error_message}")

            # Determine status
            if execution_state.failed:
                result.status = PhaseStatus.FAILED
            else:
                result.status = PhaseStatus.COMPLETED

        except Exception as e:
            result.status = PhaseStatus.FAILED
            result.errors.append(f"Pipeline execution error: {str(e)}")
            logger.error(f"Phase {phase.name} pipeline error: {e}")

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
            source = "kernel/conductor"  # Hole #7 Fix: Proper source for provenance

            self.state.set("kernel.session", self._session.to_dict(), source)
            self.state.set("kernel.status", self._session.status.value, source)
            self.state.set("kernel.current_phase", self._session.current_phase, source)
            self.state.set("kernel.phase_history", self._session.completed_phases, source)

            # Gate status
            gate_status = {
                name: result.passed
                for name, result in self._session.gate_results.items()
            }
            self.state.set("kernel.gate_status", gate_status, source)

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

    # =========================================================================
    # HULL SYNTHESIS (v1.2)
    # =========================================================================

    def _hull_exists(self) -> bool:
        """
        Check if hull dimensions already exist in state.

        Returns True if LWL, beam, and draft are all set.
        Used to decide whether to run hull synthesis.
        """
        lwl = self.state.get("hull.lwl")
        beam = self.state.get("hull.beam")
        draft = self.state.get("hull.draft")

        return all(v is not None and v > 0 for v in [lwl, beam, draft])

    def _build_synthesis_request(self) -> Optional['SynthesisRequest']:
        """
        Build a SynthesisRequest from current state.

        Reads mission parameters to construct synthesis request.
        Returns None if required parameters are missing.
        """
        from .synthesis import SynthesisRequest
        from .priors.hull_families import HullFamily

        # Get hull type from hull.hull_type or vessel_type
        hull_type_str = (
            self.state.get("hull.hull_type") or
            self.state.get("mission.vessel_type") or
            "workboat"
        )
        try:
            hull_family = HullFamily(hull_type_str.lower())
        except (ValueError, AttributeError):
            hull_family = HullFamily.WORKBOAT  # Default

        # Required: max speed
        max_speed_kts = self.state.get("mission.max_speed_kts")
        if not max_speed_kts or max_speed_kts <= 0:
            logger.warning("Cannot build synthesis request: max_speed_kts missing")
            return None

        # Optional parameters
        loa_m = self.state.get("mission.loa") or self.state.get("hull.loa")
        crew_count = self.state.get("mission.crew_berthed") or self.state.get("mission.crew_count")
        range_nm = self.state.get("mission.range_nm")
        gm_min_m = self.state.get("mission.gm_required_m")

        return SynthesisRequest(
            hull_family=hull_family,
            max_speed_kts=max_speed_kts,
            loa_m=loa_m,
            crew_count=crew_count,
            range_nm=range_nm,
            gm_min_m=gm_min_m,
        )

    def _run_hull_synthesis(self) -> Optional['SynthesisResult']:
        """
        Run hull synthesis to generate initial hull dimensions.

        Creates a HullSynthesizer and runs synthesis loop.
        Returns SynthesisResult or None if synthesis cannot be run.
        """
        from .synthesis import HullSynthesizer, SynthesisResult

        # Build synthesis request
        request = self._build_synthesis_request()
        if request is None:
            logger.warning("Hull synthesis skipped: cannot build request")
            return None

        # Create synthesizer
        synthesizer = HullSynthesizer(
            executor=self._pipeline_executor,
            state_manager=self.state,
        )

        # Run synthesis
        logger.info(f"Running hull synthesis for {request.hull_family.value} at {request.max_speed_kts} kts")
        try:
            result = synthesizer.synthesize(request)

            if result.is_usable:
                logger.info(
                    f"Hull synthesis completed: {result.termination.value}, "
                    f"iterations={result.iterations_used}, "
                    f"LWL={result.proposal.lwl_m:.2f}m"
                )
            else:
                logger.warning(f"Hull synthesis produced unusable result: {result.termination_message}")

            return result

        except Exception as e:
            logger.error(f"Hull synthesis failed: {e}")
            return None
