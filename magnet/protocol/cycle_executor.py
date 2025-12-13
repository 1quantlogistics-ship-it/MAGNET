"""
protocol/cycle_executor.py - Execute propose-validate-revise cycles
BRAVO OWNS THIS FILE.

Section 41: Agent ↔ Validator Protocol
v1.1: Integrated with TransactionManager for tentative writes
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timedelta
import logging
import time
import uuid

from .schemas import (
    Proposal, ProposalStatus, ValidationRequest, ValidationResult,
    AgentDecision, DecisionType
)
from .escalation import EscalationLevel, EscalationRequest
from .cycle_logger import CycleLogger

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


@dataclass
class CycleConfig:
    """Configuration for cycle execution."""

    max_iterations: int = 5
    timeout_seconds: float = 300.0

    auto_escalate_on_timeout: bool = True
    auto_escalate_on_max_iterations: bool = True

    # v1.1: Transaction integration
    use_transactions: bool = True
    rollback_on_failure: bool = True


@dataclass
class CycleState:
    """Internal state during cycle execution."""

    cycle_id: str = ""
    iteration: int = 0

    proposals: List[Proposal] = field(default_factory=list)
    validations: List[ValidationResult] = field(default_factory=list)
    decisions: List[AgentDecision] = field(default_factory=list)

    started_at: datetime = field(default_factory=datetime.utcnow)

    # v1.1: Transaction tracking
    transaction_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "iteration": self.iteration,
            "proposal_count": len(self.proposals),
            "started_at": self.started_at.isoformat(),
            "transaction_id": self.transaction_id,
        }


class CycleExecutor:
    """
    Executes the propose→validate→revise cycle.

    v1.1: Now integrates with TransactionManager for atomic operations.
    """

    def __init__(
        self,
        state: "StateManager",
        config: CycleConfig = None,
        transaction_manager: Any = None,
    ):
        self.state = state
        self.config = config or CycleConfig()
        self.tx_manager = transaction_manager

        self.logger = logging.getLogger("protocol.cycle")
        self.cycle_logger = CycleLogger()

        # Callbacks
        self._validator_executor: Optional[Callable] = None
        self._on_escalation: Optional[Callable] = None

    def register_validator_executor(
        self,
        executor: Callable[[ValidationRequest], ValidationResult],
    ) -> None:
        """Register the validation pipeline executor."""
        self._validator_executor = executor

    def register_escalation_handler(
        self,
        handler: Callable[[EscalationRequest], Dict],
    ) -> None:
        """Register escalation handler."""
        self._on_escalation = handler

    def execute_cycle(
        self,
        initial_proposal: Proposal,
        agent_callback: Callable[[ValidationResult], AgentDecision],
    ) -> Dict[str, Any]:
        """
        Execute complete propose→validate→revise cycle.

        Args:
            initial_proposal: Starting proposal from agent
            agent_callback: Function to get agent decision after validation

        Returns:
            Dict with status, final_proposal, iterations, etc.
        """
        cycle_state = CycleState(
            cycle_id=str(uuid.uuid4())[:8],
        )

        # v1.1: Begin transaction if enabled
        if self.config.use_transactions and self.tx_manager:
            cycle_state.transaction_id = f"cycle_{cycle_state.cycle_id}"
            self.tx_manager.begin(cycle_state.transaction_id)
        elif self.config.use_transactions and hasattr(self.state, 'begin_tentative'):
            cycle_state.transaction_id = f"cycle_{cycle_state.cycle_id}"
            self.state.begin_tentative(cycle_state.transaction_id)

        current_proposal = initial_proposal
        deadline = datetime.utcnow() + timedelta(seconds=self.config.timeout_seconds)

        try:
            while cycle_state.iteration < self.config.max_iterations:
                cycle_state.iteration += 1
                current_proposal.iteration = cycle_state.iteration

                self.logger.info(
                    f"Cycle {cycle_state.cycle_id} iteration {cycle_state.iteration}"
                )

                # Check timeout
                if datetime.utcnow() > deadline:
                    return self._handle_timeout(cycle_state, current_proposal)

                # === STEP 1: Apply proposal (tentative) ===
                self._apply_proposal(current_proposal, tentative=True)
                cycle_state.proposals.append(current_proposal)

                # === STEP 2: Run validation ===
                validation_result = self._run_validation(current_proposal)
                cycle_state.validations.append(validation_result)

                self.cycle_logger.log_validation(
                    cycle_state.cycle_id,
                    cycle_state.iteration,
                    validation_result,
                )

                # === STEP 3: Check if passed ===
                if validation_result.passed:
                    # Commit the changes
                    self._commit_changes(cycle_state)

                    current_proposal.status = ProposalStatus.APPROVED

                    return {
                        "status": "approved",
                        "cycle_id": cycle_state.cycle_id,
                        "iterations": cycle_state.iteration,
                        "final_proposal": current_proposal.to_dict(),
                        "validation_result": validation_result.to_dict(),
                    }

                # === STEP 4: Get agent decision ===
                decision = agent_callback(validation_result)
                cycle_state.decisions.append(decision)

                self.cycle_logger.log_decision(
                    cycle_state.cycle_id,
                    cycle_state.iteration,
                    decision,
                )

                # === STEP 5: Process decision ===
                if decision.decision == DecisionType.APPROVE:
                    # Agent accepts despite validation issues
                    self._commit_changes(cycle_state)
                    current_proposal.status = ProposalStatus.APPROVED

                    return {
                        "status": "approved_with_warnings",
                        "cycle_id": cycle_state.cycle_id,
                        "iterations": cycle_state.iteration,
                        "final_proposal": current_proposal.to_dict(),
                        "warnings": validation_result.warning_count,
                    }

                elif decision.decision == DecisionType.ESCALATE:
                    # Rollback and escalate
                    self._rollback_changes(cycle_state)

                    return self._handle_escalation(
                        cycle_state, current_proposal, decision
                    )

                elif decision.decision == DecisionType.ABORT:
                    self._rollback_changes(cycle_state)
                    current_proposal.status = ProposalStatus.REJECTED

                    return {
                        "status": "aborted",
                        "cycle_id": cycle_state.cycle_id,
                        "iterations": cycle_state.iteration,
                        "reason": decision.reasoning,
                    }

                elif decision.decision == DecisionType.REVISE:
                    # Rollback tentative, prepare for new proposal
                    self._rollback_changes(cycle_state)
                    current_proposal.status = ProposalStatus.REVISED

                    # Re-begin tentative for next iteration
                    if self.config.use_transactions:
                        if self.tx_manager:
                            cycle_state.transaction_id = f"cycle_{cycle_state.cycle_id}_{cycle_state.iteration}"
                            self.tx_manager.begin(cycle_state.transaction_id)
                        elif hasattr(self.state, 'begin_tentative'):
                            cycle_state.transaction_id = f"cycle_{cycle_state.cycle_id}_{cycle_state.iteration}"
                            self.state.begin_tentative(cycle_state.transaction_id)

            # Max iterations reached
            return self._handle_max_iterations(cycle_state, current_proposal)

        except Exception as e:
            self.logger.exception(f"Cycle {cycle_state.cycle_id} failed with exception")
            self._rollback_changes(cycle_state)

            return {
                "status": "error",
                "cycle_id": cycle_state.cycle_id,
                "iterations": cycle_state.iteration,
                "error": str(e),
            }

    def _apply_proposal(
        self,
        proposal: Proposal,
        tentative: bool = True,
    ) -> None:
        """Apply proposal changes to state."""
        # Hole #7 Fix: Use .set() with proper source for provenance
        source = "protocol/cycle_executor"
        for change in proposal.changes:
            self.state.set(change.path, change.new_value, source)

    def _run_validation(self, proposal: Proposal) -> ValidationResult:
        """Run validation pipeline."""
        if not self._validator_executor:
            # No validator registered - return pass
            return ValidationResult(
                proposal_id=proposal.proposal_id,
                passed=True,
                validators_run=["none"],
            )

        request = ValidationRequest(
            proposal=proposal,
            phase=proposal.phase,
        )

        start = time.time()
        result = self._validator_executor(request)
        result.duration_ms = (time.time() - start) * 1000

        return result

    def _commit_changes(self, cycle_state: CycleState) -> None:
        """Commit tentative changes."""
        if self.config.use_transactions:
            if self.tx_manager and cycle_state.transaction_id:
                self.tx_manager.commit(cycle_state.transaction_id)
            elif hasattr(self.state, 'commit_tentative'):
                self.state.commit_tentative()

    def _rollback_changes(self, cycle_state: CycleState) -> None:
        """Rollback tentative changes."""
        if self.config.use_transactions and self.config.rollback_on_failure:
            if self.tx_manager and cycle_state.transaction_id:
                self.tx_manager.rollback(cycle_state.transaction_id)
            elif hasattr(self.state, 'rollback_tentative'):
                self.state.rollback_tentative()

    def _handle_timeout(
        self,
        cycle_state: CycleState,
        proposal: Proposal,
    ) -> Dict[str, Any]:
        """Handle cycle timeout."""
        self._rollback_changes(cycle_state)
        proposal.status = ProposalStatus.ESCALATED

        if self.config.auto_escalate_on_timeout:
            escalation = EscalationRequest(
                source_agent=proposal.agent_id,
                proposal_id=proposal.proposal_id,
                level=EscalationLevel.SUPERVISOR,
                rule_id="TIMEOUT",
                message=f"Cycle timed out after {self.config.timeout_seconds}s",
            )

            if self._on_escalation:
                return self._on_escalation(escalation)

        return {
            "status": "timeout",
            "cycle_id": cycle_state.cycle_id,
            "iterations": cycle_state.iteration,
        }

    def _handle_max_iterations(
        self,
        cycle_state: CycleState,
        proposal: Proposal,
    ) -> Dict[str, Any]:
        """Handle max iterations reached."""
        self._rollback_changes(cycle_state)
        proposal.status = ProposalStatus.ESCALATED

        if self.config.auto_escalate_on_max_iterations:
            escalation = EscalationRequest(
                source_agent=proposal.agent_id,
                proposal_id=proposal.proposal_id,
                level=EscalationLevel.SUPERVISOR,
                rule_id="MAX_ITERATIONS",
                message=f"Max iterations ({self.config.max_iterations}) reached",
            )

            if self._on_escalation:
                return self._on_escalation(escalation)

        return {
            "status": "max_iterations",
            "cycle_id": cycle_state.cycle_id,
            "iterations": cycle_state.iteration,
            "last_proposal": proposal.to_dict(),
        }

    def _handle_escalation(
        self,
        cycle_state: CycleState,
        proposal: Proposal,
        decision: AgentDecision,
    ) -> Dict[str, Any]:
        """Handle escalation request."""
        proposal.status = ProposalStatus.ESCALATED

        escalation = EscalationRequest(
            source_agent=proposal.agent_id,
            proposal_id=proposal.proposal_id,
            level=EscalationLevel.SUPERVISOR,
            rule_id="AGENT_ESCALATION",
            message=decision.escalation_reason,
            context=decision.escalation_context,
        )

        if self._on_escalation:
            result = self._on_escalation(escalation)
            return {
                "status": "escalated",
                "cycle_id": cycle_state.cycle_id,
                "iterations": cycle_state.iteration,
                "escalation_result": result,
            }

        return {
            "status": "escalated",
            "cycle_id": cycle_state.cycle_id,
            "iterations": cycle_state.iteration,
            "escalation": escalation.to_dict(),
        }
