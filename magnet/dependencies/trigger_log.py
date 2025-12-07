"""
MAGNET Trigger Log

Module 03 v1.1 - Production-Ready

Audit trail for all state changes and invalidations.

v1.1 Fixes Applied:
- FIX #11: Queryable by time range, parameter, phase
- FIX #12: Supports export to JSON for debugging
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
import json
import logging
import uuid

logger = logging.getLogger(__name__)


# =============================================================================
# TRIGGER TYPES
# =============================================================================

class TriggerType(Enum):
    """Type of trigger event."""
    VALUE_SET = "value_set"                    # Parameter value was set
    VALUE_CLEARED = "value_cleared"            # Parameter value was cleared
    INVALIDATION = "invalidation"              # Parameter was invalidated
    RECALCULATION = "recalculation"           # Parameter was recalculated
    PHASE_TRANSITION = "phase_transition"     # Phase state changed
    TRANSACTION_START = "transaction_start"   # Transaction began
    TRANSACTION_COMMIT = "transaction_commit" # Transaction committed
    TRANSACTION_ROLLBACK = "transaction_rollback"  # Transaction rolled back
    VALIDATION_RUN = "validation_run"         # Validator was executed
    GATE_CHECK = "gate_check"                 # Gate condition was checked


# =============================================================================
# TRIGGER ENTRY
# =============================================================================

@dataclass
class TriggerEntry:
    """A single entry in the trigger log."""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Event type
    trigger_type: TriggerType = TriggerType.VALUE_SET

    # Subject
    parameter_path: Optional[str] = None
    phase: Optional[str] = None
    transaction_id: Optional[str] = None

    # Values
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None

    # Context
    source: str = "unknown"
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    # Related entries
    caused_by: Optional[str] = None  # Entry ID that caused this
    cascade_id: Optional[str] = None  # Cascade this belongs to

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize entry to dict."""
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "trigger_type": self.trigger_type.value,
            "parameter_path": self.parameter_path,
            "phase": self.phase,
            "transaction_id": self.transaction_id,
            "old_value": _serialize_value(self.old_value),
            "new_value": _serialize_value(self.new_value),
            "source": self.source,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "caused_by": self.caused_by,
            "cascade_id": self.cascade_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TriggerEntry":
        """Load entry from dict."""
        return cls(
            entry_id=data.get("entry_id", str(uuid.uuid4())[:12]),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.utcnow(),
            trigger_type=TriggerType(data.get("trigger_type", "value_set")),
            parameter_path=data.get("parameter_path"),
            phase=data.get("phase"),
            transaction_id=data.get("transaction_id"),
            old_value=data.get("old_value"),
            new_value=data.get("new_value"),
            source=data.get("source", "unknown"),
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
            caused_by=data.get("caused_by"),
            cascade_id=data.get("cascade_id"),
            metadata=data.get("metadata", {}),
        )


def _serialize_value(value: Any) -> Any:
    """Serialize a value for JSON storage."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, dict)):
        try:
            json.dumps(value)
            return value
        except (TypeError, ValueError):
            return str(value)
    return str(value)


# =============================================================================
# TRIGGER LOG
# =============================================================================

class TriggerLog:
    """
    Audit trail for all state changes and invalidations.

    v1.1 Fixes:
    - FIX #11: Queryable by time, parameter, phase
    - FIX #12: JSON export
    """

    DEFAULT_MAX_ENTRIES = 10000
    DEFAULT_RETENTION_DAYS = 7

    def __init__(
        self,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        retention_days: int = DEFAULT_RETENTION_DAYS,
    ):
        self._entries: List[TriggerEntry] = []
        self._max_entries = max_entries
        self._retention_days = retention_days

        # Indexes for fast lookup
        self._by_parameter: Dict[str, List[TriggerEntry]] = {}
        self._by_phase: Dict[str, List[TriggerEntry]] = {}
        self._by_cascade: Dict[str, List[TriggerEntry]] = {}
        self._by_transaction: Dict[str, List[TriggerEntry]] = {}

    def log(self, entry: TriggerEntry) -> str:
        """
        Add an entry to the log.

        Returns:
            Entry ID
        """
        # Clean old entries periodically
        if len(self._entries) % 1000 == 0:
            self._cleanup_old_entries()

        # Add entry
        self._entries.append(entry)

        # Update indexes
        if entry.parameter_path:
            if entry.parameter_path not in self._by_parameter:
                self._by_parameter[entry.parameter_path] = []
            self._by_parameter[entry.parameter_path].append(entry)

        if entry.phase:
            if entry.phase not in self._by_phase:
                self._by_phase[entry.phase] = []
            self._by_phase[entry.phase].append(entry)

        if entry.cascade_id:
            if entry.cascade_id not in self._by_cascade:
                self._by_cascade[entry.cascade_id] = []
            self._by_cascade[entry.cascade_id].append(entry)

        if entry.transaction_id:
            if entry.transaction_id not in self._by_transaction:
                self._by_transaction[entry.transaction_id] = []
            self._by_transaction[entry.transaction_id].append(entry)

        # Enforce max entries
        if len(self._entries) > self._max_entries:
            self._trim_entries()

        return entry.entry_id

    def log_value_set(
        self,
        parameter: str,
        old_value: Any,
        new_value: Any,
        source: str = "unknown",
        transaction_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Convenience method to log a value set."""
        from .graph import get_phase_for_parameter

        entry = TriggerEntry(
            trigger_type=TriggerType.VALUE_SET,
            parameter_path=parameter,
            phase=get_phase_for_parameter(parameter),
            old_value=old_value,
            new_value=new_value,
            source=source,
            transaction_id=transaction_id,
            **kwargs
        )
        return self.log(entry)

    def log_invalidation(
        self,
        parameter: str,
        source: str = "InvalidationEngine",
        cascade_id: Optional[str] = None,
        caused_by: Optional[str] = None,
        **kwargs
    ) -> str:
        """Convenience method to log an invalidation."""
        from .graph import get_phase_for_parameter

        entry = TriggerEntry(
            trigger_type=TriggerType.INVALIDATION,
            parameter_path=parameter,
            phase=get_phase_for_parameter(parameter),
            source=source,
            cascade_id=cascade_id,
            caused_by=caused_by,
            **kwargs
        )
        return self.log(entry)

    def log_recalculation(
        self,
        parameter: str,
        old_value: Any,
        new_value: Any,
        cascade_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Convenience method to log a recalculation."""
        from .graph import get_phase_for_parameter

        entry = TriggerEntry(
            trigger_type=TriggerType.RECALCULATION,
            parameter_path=parameter,
            phase=get_phase_for_parameter(parameter),
            old_value=old_value,
            new_value=new_value,
            source="CascadeExecutor",
            cascade_id=cascade_id,
            **kwargs
        )
        return self.log(entry)

    def log_phase_transition(
        self,
        phase: str,
        old_state: str,
        new_state: str,
        source: str = "PhaseStateMachine",
        **kwargs
    ) -> str:
        """Convenience method to log a phase transition."""
        entry = TriggerEntry(
            trigger_type=TriggerType.PHASE_TRANSITION,
            phase=phase,
            old_value=old_state,
            new_value=new_state,
            source=source,
            **kwargs
        )
        return self.log(entry)

    def log_transaction(
        self,
        transaction_id: str,
        event_type: TriggerType,
        source: str = "StateManager",
        **kwargs
    ) -> str:
        """Convenience method to log a transaction event."""
        entry = TriggerEntry(
            trigger_type=event_type,
            transaction_id=transaction_id,
            source=source,
            **kwargs
        )
        return self.log(entry)

    # FIX #11: Query methods

    def query(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        parameter: Optional[str] = None,
        phase: Optional[str] = None,
        trigger_types: Optional[Set[TriggerType]] = None,
        source: Optional[str] = None,
        cascade_id: Optional[str] = None,
        transaction_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[TriggerEntry]:
        """
        Query the trigger log.

        FIX #11: Supports filtering by time, parameter, phase, etc.

        Args:
            since: Only entries after this time
            until: Only entries before this time
            parameter: Filter by parameter path
            phase: Filter by phase
            trigger_types: Filter by trigger type(s)
            source: Filter by source
            cascade_id: Filter by cascade
            transaction_id: Filter by transaction
            limit: Maximum entries to return

        Returns:
            List of matching entries (newest first)
        """
        # Start with appropriate index if available
        if parameter and parameter in self._by_parameter:
            entries = self._by_parameter[parameter]
        elif phase and phase in self._by_phase:
            entries = self._by_phase[phase]
        elif cascade_id and cascade_id in self._by_cascade:
            entries = self._by_cascade[cascade_id]
        elif transaction_id and transaction_id in self._by_transaction:
            entries = self._by_transaction[transaction_id]
        else:
            entries = self._entries

        # Apply filters
        filtered = []
        for entry in reversed(entries):  # Newest first
            # Time filters
            if since and entry.timestamp < since:
                continue
            if until and entry.timestamp > until:
                continue

            # Content filters (if not already filtered by index)
            if parameter and entry.parameter_path != parameter:
                continue
            if phase and entry.phase != phase:
                continue
            if trigger_types and entry.trigger_type not in trigger_types:
                continue
            if source and entry.source != source:
                continue
            if cascade_id and entry.cascade_id != cascade_id:
                continue
            if transaction_id and entry.transaction_id != transaction_id:
                continue

            filtered.append(entry)
            if len(filtered) >= limit:
                break

        return filtered

    def get_recent(self, count: int = 100) -> List[TriggerEntry]:
        """Get most recent entries."""
        return list(reversed(self._entries[-count:]))

    def get_for_parameter(
        self,
        parameter: str,
        limit: int = 100
    ) -> List[TriggerEntry]:
        """Get entries for a specific parameter."""
        entries = self._by_parameter.get(parameter, [])
        return list(reversed(entries[-limit:]))

    def get_for_phase(
        self,
        phase: str,
        limit: int = 100
    ) -> List[TriggerEntry]:
        """Get entries for a specific phase."""
        entries = self._by_phase.get(phase, [])
        return list(reversed(entries[-limit:]))

    def get_cascade(self, cascade_id: str) -> List[TriggerEntry]:
        """Get all entries for a cascade."""
        return self._by_cascade.get(cascade_id, [])

    def get_transaction(self, transaction_id: str) -> List[TriggerEntry]:
        """Get all entries for a transaction."""
        return self._by_transaction.get(transaction_id, [])

    # FIX #12: Export methods

    def export_to_json(
        self,
        path: Path,
        since: Optional[datetime] = None,
        limit: int = 10000,
    ) -> int:
        """
        Export log entries to JSON file.

        FIX #12: Supports export for debugging.

        Args:
            path: Output file path
            since: Only entries after this time
            limit: Maximum entries to export

        Returns:
            Number of entries exported
        """
        entries = self.query(since=since, limit=limit)

        data = {
            "exported_at": datetime.utcnow().isoformat(),
            "entry_count": len(entries),
            "entries": [e.to_dict() for e in entries],
        }

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported {len(entries)} trigger log entries to {path}")
        return len(entries)

    def import_from_json(self, path: Path) -> int:
        """
        Import log entries from JSON file.

        Args:
            path: Input file path

        Returns:
            Number of entries imported
        """
        with open(path, 'r') as f:
            data = json.load(f)

        count = 0
        for entry_data in data.get("entries", []):
            entry = TriggerEntry.from_dict(entry_data)
            self.log(entry)
            count += 1

        logger.info(f"Imported {count} trigger log entries from {path}")
        return count

    def to_dict(self) -> Dict[str, Any]:
        """Serialize recent entries for state persistence."""
        return {
            "entries": [e.to_dict() for e in self._entries[-1000:]],
            "max_entries": self._max_entries,
            "retention_days": self._retention_days,
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load from serialized data."""
        for entry_data in data.get("entries", []):
            entry = TriggerEntry.from_dict(entry_data)
            self.log(entry)

    def _cleanup_old_entries(self) -> None:
        """Remove entries older than retention period."""
        cutoff = datetime.utcnow() - timedelta(days=self._retention_days)

        old_count = len(self._entries)
        self._entries = [e for e in self._entries if e.timestamp >= cutoff]

        # Rebuild indexes
        self._rebuild_indexes()

        removed = old_count - len(self._entries)
        if removed > 0:
            logger.debug(f"Cleaned up {removed} old trigger log entries")

    def _trim_entries(self) -> None:
        """Trim to max entries."""
        if len(self._entries) <= self._max_entries:
            return

        trim_count = len(self._entries) - self._max_entries
        self._entries = self._entries[trim_count:]

        # Rebuild indexes
        self._rebuild_indexes()

        logger.debug(f"Trimmed {trim_count} trigger log entries")

    def _rebuild_indexes(self) -> None:
        """Rebuild all indexes from entries."""
        self._by_parameter.clear()
        self._by_phase.clear()
        self._by_cascade.clear()
        self._by_transaction.clear()

        for entry in self._entries:
            if entry.parameter_path:
                if entry.parameter_path not in self._by_parameter:
                    self._by_parameter[entry.parameter_path] = []
                self._by_parameter[entry.parameter_path].append(entry)

            if entry.phase:
                if entry.phase not in self._by_phase:
                    self._by_phase[entry.phase] = []
                self._by_phase[entry.phase].append(entry)

            if entry.cascade_id:
                if entry.cascade_id not in self._by_cascade:
                    self._by_cascade[entry.cascade_id] = []
                self._by_cascade[entry.cascade_id].append(entry)

            if entry.transaction_id:
                if entry.transaction_id not in self._by_transaction:
                    self._by_transaction[entry.transaction_id] = []
                self._by_transaction[entry.transaction_id].append(entry)

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()
        self._by_parameter.clear()
        self._by_phase.clear()
        self._by_cascade.clear()
        self._by_transaction.clear()

    def __len__(self) -> int:
        return len(self._entries)
