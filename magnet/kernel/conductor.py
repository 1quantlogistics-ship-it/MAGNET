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
from ..validators.taxonomy import ValidatorState

if TYPE_CHECKING:
    from ..core.state_manager import StateManager
    from ..core.phase_states import PhaseMachine
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

        # CLI v1: Internal PhaseMachine for invalidation support
        from ..core.phase_states import PhaseMachine
        self._phase_machine: Optional['PhaseMachine'] = PhaseMachine(state_manager) if state_manager else None

    def set_pipeline_executor(self, executor: 'PipelineExecutor') -> None:
        """Set the pipeline executor (Guardrail #2: single execution authority)."""
        self._pipeline_executor = executor

    def set_result_aggregator(self, aggregator: 'ResultAggregator') -> None:
        """Set the result aggregator."""
        self._result_aggregator = aggregator

    # =========================================================================
    # Module 62 P0.2.3: Lazy-load ActionPlan dependencies
    # =========================================================================

    def _get_protocol_services(self):
        """Get Intent→Action protocol services via kernel factory."""
        from magnet.kernel.services import get_intent_protocol_services
        return get_intent_protocol_services(self.state)

    def _get_validator(self):
        """Get ActionPlanValidator via kernel services factory."""
        validator, _ = self._get_protocol_services()
        return validator

    def _get_executor(self):
        """Get ActionExecutor via kernel services factory."""
        _, executor = self._get_protocol_services()
        return executor

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

        # ---------------------------------------------------------------------
        # MAGNET Unified Physics Theory: Human Decision Point (Mandatory Halt)
        # If the system is awaiting human decision, block downstream automation
        # phases (but do NOT mark the design invalid).
        # ---------------------------------------------------------------------
        try:
            if self.state.get("kernel.awaiting_human_decision", False):
                # Allow re-running up to and including stability so the user can revise inputs and re-evaluate.
                allowed = {"mission", "hull", "structure", "propulsion", "weight", "stability"}
                if phase_name not in allowed:
                    return PhaseResult(
                        phase_name=phase_name,
                        status=PhaseStatus.BLOCKED,
                        errors=[],
                        warnings=[
                            "Awaiting human decision: severe grade detected. "
                            "Downstream automation is paused until approval or revision."
                        ],
                    )
        except Exception:
            # If state access fails for any reason, do not block phase execution.
            pass

        # Check dependencies
        for dep in phase.depends_on:
            if self._session and dep not in self._session.completed_phases:
                return PhaseResult(
                    phase_name=phase_name,
                    status=PhaseStatus.BLOCKED,
                    errors=[f"Dependency not completed: {dep}"],
                )

        # v1.2: Hull generation hook - MUST run BEFORE input contract check
        # (generates hull dimensions that contracts require)
        # v1.3: Capture audit for debugging
        # v2.0: Integrated design language path (Option B)
        synthesis_audit = None
        if phase_name == "hull" and not self._hull_exists():
            # v2.0: Check for design program (new path) first
            design_program = self.state.get("design_program")
            
            if design_program:
                # NEW PATH: Use design language (bypasses HullFamily)
                generation_result = self._run_program_generation(design_program)
                if generation_result:
                    synthesis_audit = self._build_program_audit(generation_result)
                    
                    if not generation_result.success:
                        return PhaseResult(
                            phase_name=phase_name,
                            status=PhaseStatus.FAILED,
                            errors=[f"Hull generation failed: {generation_result.errors}"],
                            synthesis_audit=synthesis_audit,
                        )
                    # Record explain trace for new path
                    self._record_program_explain(generation_result)
            else:
                # OLD PATH: Use HullFamily synthesis (legacy)
                synthesis_result = self._run_hull_synthesis()
                if synthesis_result:
                    # Build audit trail for debugging
                    synthesis_audit = self._build_synthesis_audit(synthesis_result)

                    if not synthesis_result.is_usable:
                        return PhaseResult(
                            phase_name=phase_name,
                            status=PhaseStatus.FAILED,
                            errors=[f"Hull synthesis failed: {synthesis_result.termination_message}"],
                            synthesis_audit=synthesis_audit,
                        )
            # If generation/synthesis succeeded, continue to input contract check
            # (should have populated hull.lwl, hull.beam, etc.)

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

        # v1.3: Attach synthesis audit to hull phase result
        if phase_name == "hull" and synthesis_audit:
            result.synthesis_audit = synthesis_audit

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

        # ---------------------------------------------------------------------
        # Human Decision Point trigger (after stability evaluation)
        # Trigger conditions (theory-aligned):
        # - Severe stability: GM < 0
        # - Severe freeboard: freeboard < 0 (deck awash)
        # ---------------------------------------------------------------------
        try:
            if phase_name == "stability" and result.status == PhaseStatus.COMPLETED:
                gm = self.state.get("stability.gm_transverse_m")
                if gm is None:
                    gm = self.state.get("stability.gm_m")
                freeboard = self.state.get("hull.freeboard")

                severe_reasons = []
                if gm is not None and float(gm) < 0.0:
                    severe_reasons.append(f"GM < 0 (GM={float(gm):.3f}m)")
                if freeboard is not None and float(freeboard) < 0.0:
                    severe_reasons.append(f"freeboard < 0 (freeboard={float(freeboard):.3f}m)")

                if severe_reasons:
                    source = "kernel/conductor"
                    request_payload = {
                        "reason": "SEVERE_GRADE",
                        "severe_reasons": severe_reasons,
                        "options": ["CONTINUE_DESPITE_WARNING", "REVISE"],
                        "snapshot": {
                            "stability.gm_transverse_m": gm,
                            "stability.gm_m": self.state.get("stability.gm_m"),
                            "hull.freeboard": freeboard,
                            "hull.displacement_mt": self.state.get("hull.displacement_mt"),
                        },
                        "requested_at": datetime.now(timezone.utc).isoformat(),
                    }
                    self.state.set("kernel.awaiting_human_decision", True, source)
                    self.state.set("kernel.human_decision_request", request_payload, source)

                    # Surface to caller as a warning (not an error) so upstream APIs can
                    # return success + needs_clarification instead of failing.
                    result.warnings.append(
                        "Human Decision Point: severe grade detected. "
                        "Downstream automation paused until approval or revision."
                    )
        except Exception:
            pass

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
            # Legacy execution path: run phase.validators against validators explicitly
            # registered on the Conductor instance (self._validators).
            #
            # Note: API uses PipelineExecutor wiring; this legacy path primarily supports
            # unit tests and non-API execution contexts.
            for validator_id in (phase.validators or []):
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
                        msg = val_result.error_message or f"{validator_id} failed"
                        # IMPORTANT: use `is True` so plain `Mock()` validators
                        # don't accidentally behave like gate conditions.
                        if getattr(validator, "is_gate_condition", False) is True:
                            result.errors.append(str(msg))
                        else:
                            result.warnings.append(f"{validator_id}: {msg}")

                except Exception as e:
                    result.validators_failed += 1
                    result.errors.append(f"Validator {validator_id} error: {str(e)}")
                    logger.error(f"Validator {validator_id} error: {e}")

            # Determine result status
            if result.errors:
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
            #
            # GATE_VS_GRADES: we do NOT stop on "validation failures" because most
            # validators are advisory grades. Only REQUIRED gate validators (hydrostatics)
            # should be allowed to block the phase.
            execution_state = self._pipeline_executor.execute_phase(phase.name, stop_on_failure=False)

            # Aggregate results
            result.validators_run = len(execution_state.completed) + len(execution_state.failed)
            result.validators_passed = len(execution_state.completed)
            result.validators_failed = len(execution_state.failed)

            # Classify failures: REQUIRED gate failures block; advisory failures become warnings.
            blocking_failures: List[str] = []
            advisory_failures: List[str] = []

            # Prefer the executor's topology if available (keeps definitions aligned)
            topology = getattr(self._pipeline_executor, "_topology", None)
            gate_validators: List[str] = []
            try:
                if topology:
                    if hasattr(topology, "get_required_gate_validators_for_phase"):
                        gate_validators = list(topology.get_required_gate_validators_for_phase(phase.name))
                    elif hasattr(topology, "get_gate_validators_for_phase"):
                        # Back-compat: older topology implementations may return required-only here.
                        gate_validators = list(topology.get_gate_validators_for_phase(phase.name))
            except Exception:
                gate_validators = []

            for vid in execution_state.failed:
                val_result = execution_state.results.get(vid)
                msg = None
                if val_result and getattr(val_result, "error_message", None):
                    msg = str(val_result.error_message)
                else:
                    msg = "Validator failed"

                # Execution errors (code failure) are always blocking
                if val_result and getattr(val_result, "state", None) == ValidatorState.ERROR:
                    blocking_failures.append(f"{vid}: {msg}")
                    continue

                # REQUIRED gate validators are blocking (by topology definition)
                if vid in gate_validators:
                    blocking_failures.append(f"{vid}: {msg}")
                else:
                    advisory_failures.append(f"{vid}: {msg}")

            # Surface advisory failures as warnings (not phase errors)
            result.warnings.extend(advisory_failures)

            # Determine status (only blocking failures fail the phase)
            if execution_state.errors:
                result.errors.extend(list(execution_state.errors))
                result.status = PhaseStatus.FAILED
            elif blocking_failures:
                result.errors.extend(blocking_failures)
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
    # HULL GENERATION v2.0: Integrated Design Language Path
    # =========================================================================

    def _run_program_generation(self, design_program: str) -> Optional['ExecutionResult']:
        """
        Run hull generation via design language (NEW PATH).
        
        This path bypasses HullFamily enumeration entirely.
        Agents express geometry as primitives, kernel compiles to HullGeometry.
        
        Args:
            design_program: Design language program text
            
        Returns:
            ExecutionResult or None if generation cannot be run
        """
        from magnet.kernel.program_executor import execute_program, ExecutionResult
        
        logger.info("[conductor] Using design language path (HullFamily bypassed)")
        
        try:
            result = execute_program(
                program_text=design_program,
                state_manager=self.state,
                dry_run=False,  # Commit to state
                validate=True,
            )
            
            if result.success:
                logger.info(
                    f"[conductor] Design program executed: "
                    f"{len(result.actions)} actions, "
                    f"geometry={'yes' if result.geometry else 'no'}"
                )
            else:
                logger.warning(f"[conductor] Design program failed: {result.errors}")
            
            return result
            
        except Exception as e:
            logger.error(f"[conductor] Design program execution failed: {e}")
            return None

    def _build_program_audit(self, result: 'ExecutionResult') -> Dict[str, Any]:
        """
        Build audit dict from ExecutionResult.
        
        Analogous to _build_synthesis_audit but for design language path.
        """
        return {
            "path": "design_language",
            "success": result.success,
            "actions_count": len(result.actions),
            "constraints_count": len(result.constraints) if hasattr(result, 'constraints') else 0,
            "geometry_generated": result.geometry is not None,
            "validation": result.validation,
            "errors": result.errors,
            "warnings": result.warnings if hasattr(result, 'warnings') else [],
        }

    def _record_program_explain(self, result: 'ExecutionResult') -> None:
        """
        Record explain trace for design language execution.
        
        Integrates with existing explain infrastructure so downstream
        phases can trace provenance.
        """
        try:
            from magnet.control_plane.explain import ExplainRecord
            
            for action in result.actions:
                # Record each action as an explain entry
                record = ExplainRecord(
                    path=action.path,
                    value=action.value,
                    source="design_language",
                    reason=action.reason if hasattr(action, 'reason') else "design program action",
                    confidence=1.0,
                )
                
                # Store via state manager if available
                if hasattr(self.state, 'record_explain'):
                    self.state.record_explain(record)
                    
        except ImportError:
            logger.debug("[conductor] Explain infrastructure not available")
        except Exception as e:
            logger.warning(f"[conductor] Failed to record explain: {e}")

    # =========================================================================
    # HULL SYNTHESIS (v1.2) - Legacy Path
    # =========================================================================

    def _hull_exists(self) -> bool:
        """
        Check if hull dimensions already exist in state WITH REAL PROVENANCE.

        Returns True only if LWL, beam, and draft are all set AND have
        non-placeholder provenance (user, synthesized, or kernel).
        
        Constraint-Aware Completion v1.0: Placeholder baselines no longer
        prevent synthesis from running. This ensures that ship-scale
        defaults (8m beam, 2m draft) get replaced with proportional values.
        
        Used to decide whether to run hull synthesis.
        """
        # Check values exist
        lwl = self.state.get("hull.lwl")
        beam = self.state.get("hull.beam")
        draft = self.state.get("hull.draft")
        
        if not all(v is not None and v > 0 for v in [lwl, beam, draft]):
            return False
        
        # Constraint-Aware Completion v1.0: Check for placeholder values
        # KNOWN BASELINES from design creation (api.py):
        BASELINE_BEAM = 8.0
        BASELINE_DRAFT = 2.0
        BASELINE_DEPTH = 4.0
        
        # Method 1: Check provenance tracking (if available)
        if hasattr(self.state, 'is_real_dimension'):
            beam_real = self.state.is_real_dimension("hull.beam")
            draft_real = self.state.is_real_dimension("hull.draft")
            
            if not (beam_real and draft_real):
                logger.info(
                    f"[conductor] Hull dimensions exist but are placeholders "
                    f"(beam_real={beam_real}, draft_real={draft_real}). "
                    f"Synthesis required for constraint-aware completion."
                )
                return False
        
        # Method 2: Fallback heuristic for when provenance isn't persisted
        # If beam/draft exactly match design-init baselines AND loa differs
        # from baseline (30.0), treat as placeholder
        loa = self.state.get("hull.loa") or lwl
        BASELINE_LOA = 30.0
        
        beam_is_baseline = abs(beam - BASELINE_BEAM) < 0.01
        draft_is_baseline = abs(draft - BASELINE_DRAFT) < 0.01
        loa_changed = abs(loa - BASELINE_LOA) > 0.01
        
        if loa_changed and (beam_is_baseline or draft_is_baseline):
            logger.info(
                f"[conductor] Hull dimensions match baseline defaults "
                f"(beam={beam}≈{BASELINE_BEAM}, draft={draft}≈{BASELINE_DRAFT}) "
                f"but LOA changed ({loa}≠{BASELINE_LOA}). "
                f"Synthesis required for proportional dimensions."
            )
            return False
        
        return True

    def _build_geometry_synthesis_request(self) -> Optional['GeometrySynthesisRequest']:
        """
        TASK-002: Build a GeometrySynthesisRequest from current state.
        
        This is the PREFERRED synthesis path - uses physics-derived defaults
        instead of HullFamily enumeration.
        
        Returns None if required parameters are missing.
        """
        from .synthesis import GeometrySynthesisRequest

        # Required: max speed
        max_speed_kts = self.state.get("mission.max_speed_kts")
        if not max_speed_kts or max_speed_kts <= 0:
            logger.warning("Cannot build geometry synthesis request: max_speed_kts missing")
            return None

        # Optional parameters
        loa_m = self.state.get("mission.loa") or self.state.get("hull.loa")
        beam_m = self.state.get("hull.beam")
        draft_m = self.state.get("hull.draft")
        crew_count = self.state.get("mission.crew_berthed") or self.state.get("mission.crew_count")
        passengers = self.state.get("mission.passengers") or 0
        cargo_mt = self.state.get("mission.cargo_capacity_mt") or 0
        range_nm = self.state.get("mission.range_nm")
        gm_min_m = self.state.get("mission.gm_required_m")

        # Mission → synthesis bridging
        try:
            total_persons = int(crew_count or 0) + int(passengers or 0)
        except Exception:
            total_persons = 0

        try:
            payload_kg = float(cargo_mt or 0) * 1000.0
        except Exception:
            payload_kg = 0.0

        logger.info(f"[conductor] Using geometry-based synthesis (HullFamily bypassed)")

        return GeometrySynthesisRequest(
            max_speed_kts=float(max_speed_kts),
            loa_m=float(loa_m) if loa_m else None,
            beam_m=float(beam_m) if beam_m else None,
            draft_m=float(draft_m) if draft_m else None,
            crew_count=total_persons if total_persons > 0 else None,
            payload_kg=payload_kg if payload_kg > 0 else None,
            range_nm=float(range_nm) if range_nm else None,
            gm_min_m=float(gm_min_m) if gm_min_m else None,
        )

    def _build_synthesis_request(self) -> Optional['SynthesisRequest']:
        """
        DEPRECATED: Build a SynthesisRequest from current state.
        
        This method uses HullFamily enumeration which is scheduled for removal.
        Use _build_geometry_synthesis_request() instead.

        Reads mission parameters to construct synthesis request.
        Returns None if required parameters are missing.
        """
        import warnings
        warnings.warn(
            "_build_synthesis_request uses HullFamily enumeration. "
            "Use _build_geometry_synthesis_request() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        
        from .synthesis import SynthesisRequest
        from .priors.hull_families import HullFamily
        from .analysis import recommend_family

        # Required: max speed
        max_speed_kts = self.state.get("mission.max_speed_kts")
        if not max_speed_kts or max_speed_kts <= 0:
            logger.warning("Cannot build synthesis request: max_speed_kts missing")
            return None

        # Optional parameters
        loa_m = self.state.get("mission.loa") or self.state.get("hull.loa")
        crew_count = self.state.get("mission.crew_berthed") or self.state.get("mission.crew_count")
        passengers = self.state.get("mission.passengers") or 0
        cargo_mt = self.state.get("mission.cargo_capacity_mt") or 0
        range_nm = self.state.get("mission.range_nm")
        gm_min_m = self.state.get("mission.gm_required_m")

        # Mission → synthesis bridging:
        # - Treat passengers as crew-equivalent for weight/displacement heuristics.
        # - Map cargo capacity (metric tonnes) to payload_kg for displacement heuristics.
        try:
            total_persons = int(crew_count or 0) + int(passengers or 0)
        except Exception:
            total_persons = 0

        try:
            payload_kg = float(cargo_mt or 0) * 1000.0
        except Exception:
            payload_kg = 0.0

        # Get hull type from hull.hull_type or vessel_type
        hull_type_str = (
            self.state.get("hull.hull_type") or
            self.state.get("mission.vessel_type") or
            None
        )

        # Try explicit HullFamily match first
        hull_family = None
        family_rationale = None
        if hull_type_str:
            try:
                hull_family = HullFamily(hull_type_str.lower())
                family_rationale = f"User specified {hull_type_str}"
            except (ValueError, AttributeError):
                pass

        # Fall back to Froude-based auto-selection
        if hull_family is None:
            lwl_estimate = float(loa_m) * 0.95 if loa_m else 30.0
            hull_family, family_rationale = recommend_family(
                speed_kts=float(max_speed_kts),
                lwl_estimate=lwl_estimate,
                vessel_type=hull_type_str,
            )

        logger.info(f"Synthesis family: {hull_family.value} — {family_rationale}")

        return SynthesisRequest(
            hull_family=hull_family,
            max_speed_kts=max_speed_kts,
            loa_m=loa_m,
            crew_count=total_persons,
            payload_kg=payload_kg,
            range_nm=range_nm,
            gm_min_m=gm_min_m,
        )

    def _build_synthesis_audit(self, result: 'SynthesisResult') -> Dict[str, Any]:
        """
        Build synthesis audit dict from SynthesisResult.

        v1.3: Exposes full synthesis trail for debugging.

        Returns:
            Dict with termination, iterations, score_history, warnings, proposal.
        """
        return {
            "termination": result.termination.value,
            "termination_message": result.termination_message,
            "iterations_used": result.iterations_used,
            "score_history": result.score_history,
            "validators_run": result.validator_results,
            "warnings": result.warnings,
            "is_fallback": result.is_fallback,
            "final_proposal": {
                "lwl_m": result.proposal.lwl_m,
                "beam_m": result.proposal.beam_m,
                "draft_m": result.proposal.draft_m,
                "depth_m": result.proposal.depth_m,
                "displacement_m3": result.proposal.displacement_m3,
                "cb": result.proposal.cb,
                "confidence": result.proposal.confidence,
                "source": result.proposal.source,
            },
        }

    def _run_hull_synthesis(self) -> Optional['SynthesisResult']:
        """
        Run hull synthesis to generate initial hull dimensions.

        TASK-002: Now uses geometry-based synthesis as the PREFERRED path.
        Falls back to legacy HullFamily synthesis only if geometry synthesis fails.
        
        Creates a HullSynthesizer and runs synthesis loop.
        Returns SynthesisResult or None if synthesis cannot be run.
        """
        from .synthesis import HullSynthesizer, SynthesisResult

        # Create synthesizer
        synthesizer = HullSynthesizer(
            executor=self._pipeline_executor,
            state_manager=self.state,
        )

        # TASK-002: Try geometry-based synthesis first (PREFERRED)
        geo_request = self._build_geometry_synthesis_request()
        if geo_request is not None:
            logger.info(f"Running geometry-based hull synthesis at {geo_request.max_speed_kts} kts")
            try:
                result = synthesizer.synthesize_from_geometry(geo_request)

                if result.is_usable:
                    logger.info(
                        f"Geometry synthesis completed: "
                        f"iterations={result.iterations}, "
                        f"LWL={result.proposal.lwl_m:.2f}m"
                    )
                    return result
                else:
                    logger.warning(f"Geometry synthesis produced unusable result, trying legacy path")
            except Exception as e:
                logger.warning(f"Geometry synthesis failed ({e}), trying legacy path")

        # DEPRECATED: Fall back to legacy HullFamily synthesis
        request = self._build_synthesis_request()
        if request is None:
            logger.warning("Hull synthesis skipped: cannot build request")
            return None

        # Run legacy synthesis
        logger.info(f"Running legacy hull synthesis for {request.hull_family.value} at {request.max_speed_kts} kts")
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

    # =========================================================================
    # CLI v1 FOUNDATION (Wire existing infrastructure)
    # =========================================================================

    def run_default_pipeline(
        self,
        context: Dict[str, Any] = None,
    ) -> List[PhaseResult]:
        """
        Run CLI-safe pipeline: hull → weight → stability.

        Does NOT run structure/propulsion/loading/production unless explicitly requested.
        This is the safe subset for interactive CLI usage.

        Args:
            context: Optional context for validators

        Returns:
            List of PhaseResults for each phase run
        """
        default_phases = ["hull", "weight", "stability"]
        results = []

        for phase in default_phases:
            result = self.run_phase(phase, context)
            results.append(result)

            if result.status in [PhaseStatus.FAILED, PhaseStatus.BLOCKED]:
                break

        return results

    def apply_refinement(
        self,
        path: str,
        op: str,
        amount: Optional[float] = None,
        phase_machine: Optional[Any] = None,
    ) -> List[PhaseResult]:
        """
        Apply refinement via Intent→Action Protocol and re-run affected phases.

        Module 62 P0.2.3: Closed bypass route - no longer uses self.state.set()
        Routes through ActionPlanValidator → ActionExecutor pipeline.

        Uses PhaseMachine.invalidate_downstream() - NOT direct session manipulation.
        Kernel owns all refinement logic: bounds, clamping, invalidation.

        Args:
            path: State path (e.g., "mission.max_speed_kts")
            op: Operation - "increase", "decrease", or "set"
            amount: Amount for operation (defaults to 10% for increase/decrease)
            phase_machine: Optional PhaseMachine for invalidation

        Returns:
            List of PhaseResults from re-running affected phases
        """
        from magnet.kernel.intent_protocol import Action, ActionPlan, ActionType

        # 1. Map op to ActionType
        action_type_map = {
            "increase": ActionType.INCREASE,
            "decrease": ActionType.DECREASE,
            "set": ActionType.SET,
        }
        action_type = action_type_map.get(op, ActionType.SET)

        # 2. Build Action based on operation type
        if action_type == ActionType.SET:
            # For SET, the amount is the absolute value
            action = Action(action_type=ActionType.SET, path=path, value=amount)
        else:
            # For INCREASE/DECREASE, compute amount if not provided
            if amount is None:
                current = self.state.get(path) or 0
                amount = current * 0.1  # Default 10%
            action = Action(action_type=action_type, path=path, amount=amount)

        # 3. Build ActionPlan
        design_id = self.state.get("metadata.design_id") if self.state else "default"
        plan = ActionPlan(
            plan_id=f"refine_{uuid.uuid4().hex[:8]}",
            intent_id=f"refine_intent_{uuid.uuid4().hex[:8]}",
            design_id=design_id or "default",
            design_version_before=self.state.design_version if self.state else 0,
            actions=[action],
            proposed_at=datetime.now(timezone.utc),
        )

        # 4. Validate and execute through ActionPlan pipeline
        validator = self._get_validator()
        executor = self._get_executor()

        validation_result = validator.validate(plan, self.state)

        if validation_result.has_rejections:
            rejection = validation_result.rejected[0]
            logger.warning(f"Refinement rejected: {rejection[0].path} - {rejection[1]}")
            return []

        exec_result = executor.execute(validation_result.approved, plan)

        if not exec_result.success:
            logger.error(f"Refinement execution failed: {exec_result.errors}")
            return []

        for warning in exec_result.warnings:
            logger.warning(warning)

        # 5. CLI v1 CORRECTION #3: Always invalidate from hull for any refinement
        # This is conservative but safe. Future versions can use
        # InvalidationEngine.get_affected_phases(path) for precision.
        affected_phase = "hull"

        # 6. Invalidate downstream phases (P0 #1: use PhaseMachine, not direct list surgery)
        # Use provided phase_machine or fall back to internal instance
        pm = phase_machine or self._phase_machine
        if pm and hasattr(pm, 'invalidate_downstream'):
            pm.invalidate_downstream(affected_phase)

        # 7. Re-run from affected phase using default pipeline
        return self.run_default_pipeline()
