"""
glue/protocol/executor.py - Cycle executor for propose-validate-revise loop

ALPHA OWNS THIS FILE.

Module 41: Agent-Validator Protocol - v1.1 with Transaction Integration
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timezone
import logging
import time
import uuid

from .schemas import (
    Proposal,
    ProposalStatus,
    ValidationRequest,
    ValidationResult,
    ValidationFinding,
    AgentDecision,
    DecisionType,
    ParameterChange,
)
from ..utils import safe_get, safe_write

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger(__name__)


@dataclass
class CycleConfig:
    """Configuration for the propose-validate-revise cycle."""

    max_iterations: int = 5
    """Maximum revision iterations before escalation"""

    strict_mode: bool = False
    """If True, any error fails validation"""

    auto_commit: bool = True
    """If True, automatically commit successful proposals"""

    use_transactions: bool = True
    """If True, wrap proposals in transactions for rollback"""

    timeout_seconds: float = 30.0
    """Maximum time for a single cycle"""


@dataclass
class CycleResult:
    """Result of a complete propose-validate-revise cycle."""

    cycle_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    final_proposal: Optional[Proposal] = None
    final_result: Optional[ValidationResult] = None

    iterations: int = 0
    total_duration_ms: float = 0.0

    success: bool = False
    committed: bool = False

    escalated: bool = False
    escalation_reason: str = ""

    history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "final_proposal": self.final_proposal.to_dict() if self.final_proposal else None,
            "final_result": self.final_result.to_dict() if self.final_result else None,
            "iterations": self.iterations,
            "total_duration_ms": self.total_duration_ms,
            "success": self.success,
            "committed": self.committed,
            "escalated": self.escalated,
            "escalation_reason": self.escalation_reason,
        }


class CycleExecutor:
    """
    Executes the propose-validate-revise cycle.

    v1.1: Integrates with TransactionManager for tentative writes and rollback.
    """

    def __init__(
        self,
        state: "StateManager",
        validator_fn: Callable[[ValidationRequest], ValidationResult],
        config: Optional[CycleConfig] = None,
    ):
        """
        Initialize the cycle executor.

        Args:
            state: StateManager for reading/writing design state
            validator_fn: Function that runs validation on a request
            config: Cycle configuration
        """
        self.state = state
        self.validator_fn = validator_fn
        self.config = config or CycleConfig()
        self._current_transaction: Optional[str] = None

    def execute(
        self,
        proposal: Proposal,
        decision_fn: Optional[Callable[[Proposal, ValidationResult], AgentDecision]] = None,
    ) -> CycleResult:
        """
        Execute a complete propose-validate-revise cycle.

        Args:
            proposal: Initial proposal from agent
            decision_fn: Optional callback for agent decision after validation.
                         If None, uses auto-decision based on validation results.

        Returns:
            CycleResult with final outcome
        """
        result = CycleResult()
        start_time = time.perf_counter()

        current_proposal = proposal
        iteration = 0

        try:
            while iteration < self.config.max_iterations:
                iteration += 1
                current_proposal.iteration = iteration

                logger.debug(f"Cycle iteration {iteration}: proposal {current_proposal.proposal_id}")

                # Begin transaction if enabled
                if self.config.use_transactions:
                    self._begin_transaction()

                # Apply proposed changes tentatively
                self._apply_changes(current_proposal)

                # Run validation
                validation_request = ValidationRequest(
                    proposal=current_proposal,
                    phase=current_proposal.phase,
                    strict_mode=self.config.strict_mode,
                )

                validation_result = self.validator_fn(validation_request)

                # Record history
                result.history.append({
                    "iteration": iteration,
                    "proposal_id": current_proposal.proposal_id,
                    "validation_passed": validation_result.passed,
                    "error_count": validation_result.error_count,
                    "warning_count": validation_result.warning_count,
                })

                # Get agent decision
                if decision_fn:
                    decision = decision_fn(current_proposal, validation_result)
                else:
                    decision = self._auto_decision(current_proposal, validation_result)

                # Process decision
                if decision.decision == DecisionType.APPROVE:
                    # Commit changes
                    if self.config.use_transactions:
                        self._commit_transaction()

                    current_proposal.status = ProposalStatus.APPROVED
                    result.success = True
                    result.committed = self.config.auto_commit
                    break

                elif decision.decision == DecisionType.REVISE:
                    # Rollback and prepare revision
                    if self.config.use_transactions:
                        self._rollback_transaction()

                    current_proposal = self._create_revision(
                        current_proposal,
                        decision.revision_changes,
                    )

                elif decision.decision == DecisionType.ESCALATE:
                    # Rollback and escalate
                    if self.config.use_transactions:
                        self._rollback_transaction()

                    result.escalated = True
                    result.escalation_reason = decision.escalation_reason
                    current_proposal.status = ProposalStatus.ESCALATED
                    break

                elif decision.decision == DecisionType.ABORT:
                    # Rollback and abort
                    if self.config.use_transactions:
                        self._rollback_transaction()

                    current_proposal.status = ProposalStatus.REJECTED
                    break

            # Max iterations reached
            if iteration >= self.config.max_iterations and not result.success:
                if self.config.use_transactions and self._current_transaction:
                    self._rollback_transaction()
                result.escalated = True
                result.escalation_reason = f"Max iterations ({self.config.max_iterations}) reached"

        except Exception as e:
            logger.error(f"Cycle execution error: {e}")
            if self.config.use_transactions and self._current_transaction:
                self._rollback_transaction()
            raise

        finally:
            result.iterations = iteration
            result.final_proposal = current_proposal
            result.total_duration_ms = (time.perf_counter() - start_time) * 1000

        return result

    def _apply_changes(self, proposal: Proposal) -> None:
        """Apply proposed changes to state."""
        for change in proposal.changes:
            safe_write(self.state, change.path, change.new_value, f"proposal:{proposal.proposal_id}")

    def _auto_decision(self, proposal: Proposal, result: ValidationResult) -> AgentDecision:
        """
        Auto-generate decision based on validation result.

        Simple rule: approve if passed, escalate if errors, revise if only warnings.
        """
        if result.passed:
            return AgentDecision(
                proposal_id=proposal.proposal_id,
                decision=DecisionType.APPROVE,
                reasoning="Validation passed",
                confidence=0.9,
            )

        if result.error_count > 0:
            # Check if we can suggest revisions
            suggestions = [f for f in result.findings if f.suggestion]
            if suggestions:
                revision_changes = self._suggestions_to_changes(suggestions)
                return AgentDecision(
                    proposal_id=proposal.proposal_id,
                    decision=DecisionType.REVISE,
                    reasoning=f"Attempting revision based on {len(suggestions)} suggestions",
                    revision_changes=revision_changes,
                    confidence=0.6,
                )

            # No suggestions, escalate
            return AgentDecision(
                proposal_id=proposal.proposal_id,
                decision=DecisionType.ESCALATE,
                escalation_reason=f"Validation failed with {result.error_count} errors, no revision suggestions",
                confidence=0.7,
            )

        # Only warnings - approve anyway
        return AgentDecision(
            proposal_id=proposal.proposal_id,
            decision=DecisionType.APPROVE,
            reasoning=f"Validation passed with {result.warning_count} warnings",
            confidence=0.8,
        )

    def _suggestions_to_changes(self, findings: List[ValidationFinding]) -> List[ParameterChange]:
        """Convert validation suggestions to parameter changes."""
        changes = []
        for finding in findings:
            if finding.path and finding.expected_value is not None:
                changes.append(ParameterChange(
                    path=finding.path,
                    old_value=finding.actual_value,
                    new_value=finding.expected_value,
                    reasoning=f"Suggested by {finding.validator_name}: {finding.suggestion}",
                    source=f"validator:{finding.validator_name}",
                ))
        return changes

    def _create_revision(
        self,
        original: Proposal,
        changes: List[ParameterChange],
    ) -> Proposal:
        """Create a revision proposal from the original."""
        return Proposal(
            proposal_id=str(uuid.uuid4())[:8],
            agent_id=original.agent_id,
            phase=original.phase,
            iteration=original.iteration + 1,
            changes=changes or original.changes,
            status=ProposalStatus.REVISED,
            reasoning=f"Revision of {original.proposal_id}",
            parent_id=original.proposal_id,
        )

    def _begin_transaction(self) -> None:
        """Begin a tentative transaction."""
        if hasattr(self.state, 'begin_transaction'):
            self._current_transaction = self.state.begin_transaction()
        elif hasattr(self.state, 'begin_tentative'):
            self._current_transaction = str(uuid.uuid4())[:8]
            self.state.begin_tentative(self._current_transaction)

    def _commit_transaction(self) -> None:
        """Commit the current transaction."""
        if self._current_transaction:
            if hasattr(self.state, 'commit_transaction'):
                self.state.commit_transaction(self._current_transaction)
            elif hasattr(self.state, 'commit_tentative'):
                self.state.commit_tentative()
            self._current_transaction = None

    def _rollback_transaction(self) -> None:
        """Rollback the current transaction."""
        if self._current_transaction:
            if hasattr(self.state, 'rollback_transaction'):
                self.state.rollback_transaction(self._current_transaction)
            elif hasattr(self.state, 'rollback_tentative'):
                self.state.rollback_tentative()
            self._current_transaction = None
