"""
transactions/schemas.py - Transaction data structures
BRAVO OWNS THIS FILE.

Section 44: Transaction Model
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import uuid


class TransactionStatus(Enum):
    """Transaction status."""
    PENDING = "pending"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class IsolationLevel(Enum):
    """Transaction isolation level."""
    READ_UNCOMMITTED = "read_uncommitted"
    READ_COMMITTED = "read_committed"
    REPEATABLE_READ = "repeatable_read"
    SERIALIZABLE = "serializable"


@dataclass
class StateChange:
    """Record of a single state change."""

    change_id: str = ""
    transaction_id: str = ""

    path: str = ""
    old_value: Any = None
    new_value: Any = None

    source: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_id": self.change_id,
            "transaction_id": self.transaction_id,
            "path": self.path,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "source": self.source,
        }


@dataclass
class Savepoint:
    """Transaction savepoint for partial rollback."""

    savepoint_id: str = ""
    transaction_id: str = ""

    name: str = ""

    created_at: datetime = field(default_factory=datetime.utcnow)

    # State snapshot at savepoint
    state_snapshot: Dict[str, Any] = field(default_factory=dict)

    # Changes since last savepoint
    changes_since: List[StateChange] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "savepoint_id": self.savepoint_id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "num_changes": len(self.changes_since),
        }


@dataclass
class Transaction:
    """Complete transaction record."""

    transaction_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    status: TransactionStatus = TransactionStatus.PENDING
    isolation: IsolationLevel = IsolationLevel.READ_COMMITTED

    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Parent transaction (for nesting)
    parent_transaction_id: Optional[str] = None

    # Changes
    changes: List[StateChange] = field(default_factory=list)

    # Savepoints
    savepoints: List[Savepoint] = field(default_factory=list)

    # v1.1: Initial state snapshot for rollback
    initial_snapshot: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    source: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "num_changes": len(self.changes),
            "num_savepoints": len(self.savepoints),
        }
