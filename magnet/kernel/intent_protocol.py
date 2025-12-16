"""
MAGNET Intent→Action Protocol v1.0

The firewall between LLM proposals and kernel mutations.

This module defines the typed protocol for:
- Intent: Parsed user intent from natural language
- Action: Single deterministic kernel operation
- ActionPlan: List of Actions to be validated and executed

INVARIANT: LLM never directly drives state. It only proposes ActionPlans.
The kernel validates, clamps, rejects, executes, and audits.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# =============================================================================
# INTENT TYPES
# =============================================================================

class IntentType(str, Enum):
    """
    Classification of user intent extracted from natural language.

    Used by the LLM parser to categorize what the user wants to do.
    """
    REFINE = "refine"           # Modify parameter value
    CREATE = "create"           # New design
    QUERY = "query"             # Get value or explain (no mutation)
    LOCK = "lock"               # Lock/unlock parameter
    RUN_PIPELINE = "run_pipeline"  # Execute phases
    EXPORT = "export"           # Generate output
    CLARIFY = "clarify"         # User responding to clarification
    UNKNOWN = "unknown"         # Could not parse


# =============================================================================
# ACTION TYPES
# =============================================================================

class ActionType(str, Enum):
    """
    Deterministic kernel operations.

    Each action type maps to exactly one mutation path in the kernel.
    """
    SET = "set"                 # SET(path, value)
    INCREASE = "increase"       # INCREASE(path, amount)
    DECREASE = "decrease"       # DECREASE(path, amount)
    LOCK = "lock"               # LOCK(path)
    UNLOCK = "unlock"           # UNLOCK(path)
    RUN_PHASES = "run_phases"   # RUN_PHASES(phases=[...])
    EXPORT = "export"           # EXPORT(format=...)
    REQUEST_CLARIFICATION = "request_clarification"  # Ask user for more info
    NOOP = "noop"               # Query-only, no mutation


# =============================================================================
# INTENT
# =============================================================================

@dataclass(frozen=True)
class Intent:
    """
    Typed intent extracted from natural language.

    Immutable record of what the user wanted to do.
    """
    intent_id: str                  # Correlation ID (UUID)
    design_id: str                  # Target design
    raw_text: str                   # Original user input
    intent_type: IntentType         # Classified type
    confidence: float               # LLM confidence (0-1)
    parsed_at: datetime             # When parsed

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON/storage."""
        return {
            "intent_id": self.intent_id,
            "design_id": self.design_id,
            "raw_text": self.raw_text,
            "intent_type": self.intent_type.value,
            "confidence": self.confidence,
            "parsed_at": self.parsed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Intent":
        """Deserialize from dictionary."""
        return cls(
            intent_id=data["intent_id"],
            design_id=data["design_id"],
            raw_text=data["raw_text"],
            intent_type=IntentType(data["intent_type"]),
            confidence=data["confidence"],
            parsed_at=datetime.fromisoformat(data["parsed_at"]),
        )


# =============================================================================
# ACTION
# =============================================================================

@dataclass(frozen=True)
class Action:
    """
    Single kernel action. Deterministic, validatable, replayable.

    Immutable - use with_value() to create modified copies.
    """
    action_type: ActionType
    path: Optional[str] = None          # For SET/INCREASE/DECREASE/LOCK/UNLOCK
    value: Optional[Any] = None         # For SET
    amount: Optional[float] = None      # For INCREASE/DECREASE
    unit: Optional[str] = None          # For value normalization
    phases: Optional[List[str]] = None  # For RUN_PHASES
    format: Optional[str] = None        # For EXPORT
    message: Optional[str] = None       # For REQUEST_CLARIFICATION

    def with_value(self, new_value: Any) -> "Action":
        """
        Create a copy with a different value (for clamping).

        Preserves immutability of original Action.
        """
        return replace(self, value=new_value)

    def with_amount(self, new_amount: float) -> "Action":
        """Create a copy with a different amount (for clamping)."""
        return replace(self, amount=new_amount)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON/storage."""
        result = {"action_type": self.action_type.value}
        if self.path is not None:
            result["path"] = self.path
        if self.value is not None:
            result["value"] = self.value
        if self.amount is not None:
            result["amount"] = self.amount
        if self.unit is not None:
            result["unit"] = self.unit
        if self.phases is not None:
            result["phases"] = self.phases
        if self.format is not None:
            result["format"] = self.format
        if self.message is not None:
            result["message"] = self.message
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Action":
        """Deserialize from dictionary."""
        return cls(
            action_type=ActionType(data["action_type"]),
            path=data.get("path"),
            value=data.get("value"),
            amount=data.get("amount"),
            unit=data.get("unit"),
            phases=data.get("phases"),
            format=data.get("format"),
            message=data.get("message"),
        )


# =============================================================================
# ACTION PLAN
# =============================================================================

@dataclass(frozen=True)
class ActionPlan:
    """
    List of Actions the kernel can validate and execute.

    Links back to originating Intent for audit trail.
    Includes design_version_before for stale plan detection.
    """
    plan_id: str                    # Unique plan ID (UUID)
    intent_id: str                  # Links to originating Intent
    design_id: str                  # Target design
    actions: tuple                  # Tuple[Action, ...] for immutability
    design_version_before: int      # State version when plan was created
    proposed_at: datetime           # When plan was created

    def __post_init__(self):
        """Ensure actions is a tuple for true immutability."""
        if isinstance(self.actions, list):
            object.__setattr__(self, 'actions', tuple(self.actions))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON/storage."""
        return {
            "plan_id": self.plan_id,
            "intent_id": self.intent_id,
            "design_id": self.design_id,
            "actions": [a.to_dict() for a in self.actions],
            "design_version_before": self.design_version_before,
            "proposed_at": self.proposed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionPlan":
        """Deserialize from dictionary."""
        return cls(
            plan_id=data["plan_id"],
            intent_id=data["intent_id"],
            design_id=data["design_id"],
            actions=[Action.from_dict(a) for a in data["actions"]],
            design_version_before=data["design_version_before"],
            proposed_at=datetime.fromisoformat(data["proposed_at"]),
        )

    def __len__(self) -> int:
        """Number of actions in the plan."""
        return len(self.actions)

    def __iter__(self):
        """Iterate over actions."""
        return iter(self.actions)


# =============================================================================
# ACTION RESULT (Output of execution)
# =============================================================================

@dataclass(frozen=True)
class ActionResult:
    """
    Result of executing an ActionPlan.

    Contains audit trail of what was executed, rejected, and warnings.
    """
    plan_id: str                            # Original plan ID
    intent_id: str                          # Original intent ID
    design_id: str                          # Target design
    design_version_before: int              # Version before execution
    design_version_after: int               # Version after execution
    actions_executed: tuple                 # Tuple[Action, ...] actually executed
    actions_rejected: tuple                 # Tuple[(Action, reason), ...] rejected
    warnings: tuple                         # Tuple[str, ...] warnings (e.g., clamping)
    executed_at: datetime                   # When executed

    def __post_init__(self):
        """Ensure tuples for immutability."""
        if isinstance(self.actions_executed, list):
            object.__setattr__(self, 'actions_executed', tuple(self.actions_executed))
        if isinstance(self.actions_rejected, list):
            object.__setattr__(self, 'actions_rejected', tuple(self.actions_rejected))
        if isinstance(self.warnings, list):
            object.__setattr__(self, 'warnings', tuple(self.warnings))

    @property
    def success(self) -> bool:
        """True if at least one action was executed."""
        return len(self.actions_executed) > 0

    @property
    def version_changed(self) -> bool:
        """True if design_version was incremented."""
        return self.design_version_after > self.design_version_before

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON/API response."""
        return {
            "plan_id": self.plan_id,
            "intent_id": self.intent_id,
            "design_id": self.design_id,
            "design_version_before": self.design_version_before,
            "design_version_after": self.design_version_after,
            "actions_executed": [a.to_dict() for a in self.actions_executed],
            "actions_rejected": [
                {"action": a.to_dict(), "reason": r}
                for a, r in self.actions_rejected
            ],
            "warnings": list(self.warnings),
            "executed_at": self.executed_at.isoformat(),
            "success": self.success,
            "version_changed": self.version_changed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionResult":
        """Deserialize from dictionary."""
        return cls(
            plan_id=data["plan_id"],
            intent_id=data["intent_id"],
            design_id=data["design_id"],
            design_version_before=data["design_version_before"],
            design_version_after=data["design_version_after"],
            actions_executed=[Action.from_dict(a) for a in data["actions_executed"]],
            actions_rejected=[
                (Action.from_dict(item["action"]), item["reason"])
                for item in data["actions_rejected"]
            ],
            warnings=data["warnings"],
            executed_at=datetime.fromisoformat(data["executed_at"]),
        )
