"""
protocol/cycle_logger.py - Audit logging for cycles
BRAVO OWNS THIS FILE.

Section 41: Agent ↔ Validator Protocol
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
import json


@dataclass
class CycleLogEntry:
    """Single log entry for a cycle event."""

    entry_id: str = ""
    cycle_id: str = ""
    iteration: int = 0

    event_type: str = ""
    """proposal, validation, decision, escalation, error"""

    timestamp: datetime = field(default_factory=datetime.utcnow)

    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "cycle_id": self.cycle_id,
            "iteration": self.iteration,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "data": self.data,
        }


class CycleLogger:
    """
    Logs cycle events for auditing and debugging.

    Provides structured logging of the propose→validate→revise cycle
    for later analysis and explanation generation.
    """

    def __init__(self, logger_name: str = "protocol.cycle"):
        self.logger = logging.getLogger(logger_name)
        self._entries: List[CycleLogEntry] = []
        self._entry_counter = 0

    def log_proposal(
        self,
        cycle_id: str,
        iteration: int,
        proposal: Any,
    ) -> CycleLogEntry:
        """Log a proposal submission."""
        entry = self._create_entry(
            cycle_id=cycle_id,
            iteration=iteration,
            event_type="proposal",
            message=f"Proposal submitted: {getattr(proposal, 'proposal_id', 'unknown')}",
            data=proposal.to_dict() if hasattr(proposal, 'to_dict') else {},
        )

        self.logger.info(
            f"[{cycle_id}:{iteration}] Proposal: {entry.message}"
        )

        return entry

    def log_validation(
        self,
        cycle_id: str,
        iteration: int,
        result: Any,
    ) -> CycleLogEntry:
        """Log validation result."""
        passed = getattr(result, 'passed', False)
        error_count = getattr(result, 'error_count', 0)
        warning_count = getattr(result, 'warning_count', 0)

        entry = self._create_entry(
            cycle_id=cycle_id,
            iteration=iteration,
            event_type="validation",
            message=f"Validation {'passed' if passed else 'failed'}: {error_count} errors, {warning_count} warnings",
            data=result.to_dict() if hasattr(result, 'to_dict') else {},
        )

        log_level = logging.INFO if passed else logging.WARNING
        self.logger.log(
            log_level,
            f"[{cycle_id}:{iteration}] Validation: {entry.message}"
        )

        return entry

    def log_decision(
        self,
        cycle_id: str,
        iteration: int,
        decision: Any,
    ) -> CycleLogEntry:
        """Log agent decision."""
        decision_type = getattr(decision, 'decision', None)
        decision_value = decision_type.value if hasattr(decision_type, 'value') else str(decision_type)

        entry = self._create_entry(
            cycle_id=cycle_id,
            iteration=iteration,
            event_type="decision",
            message=f"Agent decision: {decision_value}",
            data=decision.to_dict() if hasattr(decision, 'to_dict') else {},
        )

        self.logger.info(
            f"[{cycle_id}:{iteration}] Decision: {entry.message}"
        )

        return entry

    def log_escalation(
        self,
        cycle_id: str,
        iteration: int,
        escalation: Any,
    ) -> CycleLogEntry:
        """Log escalation event."""
        level = getattr(escalation, 'level', None)
        level_value = level.value if hasattr(level, 'value') else str(level)

        entry = self._create_entry(
            cycle_id=cycle_id,
            iteration=iteration,
            event_type="escalation",
            message=f"Escalated to {level_value}: {getattr(escalation, 'message', '')}",
            data=escalation.to_dict() if hasattr(escalation, 'to_dict') else {},
        )

        self.logger.warning(
            f"[{cycle_id}:{iteration}] Escalation: {entry.message}"
        )

        return entry

    def log_error(
        self,
        cycle_id: str,
        iteration: int,
        error: Exception,
        context: Optional[Dict] = None,
    ) -> CycleLogEntry:
        """Log an error during cycle execution."""
        entry = self._create_entry(
            cycle_id=cycle_id,
            iteration=iteration,
            event_type="error",
            message=f"Error: {str(error)}",
            data={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context or {},
            },
        )

        self.logger.error(
            f"[{cycle_id}:{iteration}] Error: {entry.message}",
            exc_info=True,
        )

        return entry

    def log_completion(
        self,
        cycle_id: str,
        iteration: int,
        status: str,
        summary: Optional[Dict] = None,
    ) -> CycleLogEntry:
        """Log cycle completion."""
        entry = self._create_entry(
            cycle_id=cycle_id,
            iteration=iteration,
            event_type="completion",
            message=f"Cycle completed with status: {status}",
            data={"status": status, "summary": summary or {}},
        )

        self.logger.info(
            f"[{cycle_id}:{iteration}] Completion: {entry.message}"
        )

        return entry

    def _create_entry(
        self,
        cycle_id: str,
        iteration: int,
        event_type: str,
        message: str,
        data: Dict,
    ) -> CycleLogEntry:
        """Create and store a log entry."""
        self._entry_counter += 1

        entry = CycleLogEntry(
            entry_id=f"log_{self._entry_counter:06d}",
            cycle_id=cycle_id,
            iteration=iteration,
            event_type=event_type,
            message=message,
            data=data,
        )

        self._entries.append(entry)
        return entry

    def get_entries(
        self,
        cycle_id: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> List[CycleLogEntry]:
        """Get log entries with optional filtering."""
        entries = self._entries

        if cycle_id:
            entries = [e for e in entries if e.cycle_id == cycle_id]

        if event_type:
            entries = [e for e in entries if e.event_type == event_type]

        return entries

    def get_cycle_summary(self, cycle_id: str) -> Dict[str, Any]:
        """Get summary of a cycle's log entries."""
        entries = self.get_entries(cycle_id=cycle_id)

        return {
            "cycle_id": cycle_id,
            "entry_count": len(entries),
            "event_types": list(set(e.event_type for e in entries)),
            "iterations": max((e.iteration for e in entries), default=0),
            "has_errors": any(e.event_type == "error" for e in entries),
            "entries": [e.to_dict() for e in entries],
        }

    def export_to_json(self, filepath: str) -> None:
        """Export all entries to JSON file."""
        data = {
            "exported_at": datetime.utcnow().isoformat(),
            "entry_count": len(self._entries),
            "entries": [e.to_dict() for e in self._entries],
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def clear(self) -> None:
        """Clear all entries."""
        self._entries = []
