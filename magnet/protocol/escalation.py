"""
protocol/escalation.py - Escalation rules and handling
BRAVO OWNS THIS FILE.

Section 41: Agent ↔ Validator Protocol
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import uuid


class EscalationLevel(Enum):
    """Where to escalate to."""
    AGENT = "agent"        # Same agent retry
    PEER = "peer"          # Another specialist agent
    SUPERVISOR = "supervisor"  # Supervisor agent
    HUMAN = "human"        # Human intervention required


@dataclass
class EscalationRule:
    """Rule for when to escalate."""

    rule_id: str = ""
    name: str = ""
    description: str = ""

    trigger_condition: str = ""
    """Condition expression or identifier"""

    target_level: EscalationLevel = EscalationLevel.SUPERVISOR
    priority: int = 50

    auto_trigger: bool = True
    """Whether to trigger automatically"""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "trigger_condition": self.trigger_condition,
            "target_level": self.target_level.value,
            "priority": self.priority,
        }


# Standard escalation rules
STANDARD_RULES = [
    EscalationRule(
        rule_id="ESC-TIMEOUT",
        name="Cycle Timeout",
        description="Cycle exceeded time limit",
        trigger_condition="cycle.elapsed > config.timeout",
        target_level=EscalationLevel.SUPERVISOR,
        priority=90,
    ),
    EscalationRule(
        rule_id="ESC-MAX-ITER",
        name="Max Iterations",
        description="Agent could not resolve issues within iteration limit",
        trigger_condition="cycle.iteration >= config.max_iterations",
        target_level=EscalationLevel.SUPERVISOR,
        priority=80,
    ),
    EscalationRule(
        rule_id="ESC-CRITICAL-ERROR",
        name="Critical Validation Error",
        description="Validation found critical error agent cannot resolve",
        trigger_condition="validation.has_critical_error",
        target_level=EscalationLevel.SUPERVISOR,
        priority=95,
    ),
    EscalationRule(
        rule_id="ESC-LOW-CONFIDENCE",
        name="Agent Uncertainty",
        description="Agent confidence too low to proceed",
        trigger_condition="agent.confidence < threshold",
        target_level=EscalationLevel.PEER,
        priority=60,
    ),
]


@dataclass
class EscalationRequest:
    """Request for escalation."""

    escalation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    source_agent: str = ""
    proposal_id: str = ""

    level: EscalationLevel = EscalationLevel.SUPERVISOR
    rule_id: str = ""

    message: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "escalation_id": self.escalation_id,
            "source_agent": self.source_agent,
            "proposal_id": self.proposal_id,
            "level": self.level.value,
            "rule_id": self.rule_id,
            "message": self.message,
        }


@dataclass
class EscalationResponse:
    """Response to escalation request."""

    escalation_id: str = ""
    handled_by: str = ""

    resolution: str = ""
    """approved, rejected, redirected, deferred"""

    new_agent_id: Optional[str] = None
    """If redirected to another agent"""

    instructions: str = ""
    additional_context: Dict[str, Any] = field(default_factory=dict)

    resolved_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "escalation_id": self.escalation_id,
            "handled_by": self.handled_by,
            "resolution": self.resolution,
            "new_agent_id": self.new_agent_id,
            "instructions": self.instructions,
        }


class EscalationHandler:
    """Handles escalation requests."""

    def __init__(self):
        self.rules = {r.rule_id: r for r in STANDARD_RULES}
        self._handlers: Dict[EscalationLevel, callable] = {}

    def register_handler(
        self,
        level: EscalationLevel,
        handler: callable,
    ) -> None:
        """Register handler for escalation level."""
        self._handlers[level] = handler

    def check_escalation_needed(
        self,
        context: Dict[str, Any],
    ) -> Optional[EscalationRule]:
        """Check if any escalation rule is triggered."""
        # Sort by priority (highest first)
        sorted_rules = sorted(
            self.rules.values(),
            key=lambda r: r.priority,
            reverse=True,
        )

        for rule in sorted_rules:
            if rule.auto_trigger and self._evaluate_condition(rule, context):
                return rule

        return None

    def _evaluate_condition(
        self,
        rule: EscalationRule,
        context: Dict[str, Any],
    ) -> bool:
        """Evaluate if rule condition is met."""
        # Simple condition evaluation
        condition = rule.trigger_condition

        if "cycle.elapsed > config.timeout" in condition:
            elapsed = context.get("elapsed_seconds", 0)
            timeout = context.get("timeout_seconds", 300)
            return elapsed > timeout

        if "cycle.iteration >= config.max_iterations" in condition:
            iteration = context.get("iteration", 0)
            max_iter = context.get("max_iterations", 5)
            return iteration >= max_iter

        if "validation.has_critical_error" in condition:
            return context.get("has_critical_error", False)

        if "agent.confidence < threshold" in condition:
            confidence = context.get("agent_confidence", 1.0)
            threshold = context.get("confidence_threshold", 0.3)
            return confidence < threshold

        return False

    def handle(self, request: EscalationRequest) -> EscalationResponse:
        """Handle an escalation request."""
        handler = self._handlers.get(request.level)

        if handler:
            return handler(request)

        # Default response if no handler
        return EscalationResponse(
            escalation_id=request.escalation_id,
            handled_by="default",
            resolution="deferred",
            instructions="No handler registered for this escalation level",
        )
