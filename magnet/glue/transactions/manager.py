"""
glue/transactions/manager.py - Transaction manager for atomic updates

ALPHA OWNS THIS FILE.

Module 44: Transaction Model - v1.1
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timezone
from enum import Enum
import copy
import uuid
import logging

from .isolation import IsolationLevel
from ..utils import serialize_state

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger(__name__)


class TransactionState(Enum):
    """Transaction lifecycle states."""
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class TransactionRecord:
    """Record of a transaction."""

    transaction_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    state: TransactionState = TransactionState.ACTIVE
    isolation_level: IsolationLevel = IsolationLevel.READ_COMMITTED

    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    # Context
    source: str = ""
    description: str = ""

    # Changes
    changes: Dict[str, Any] = field(default_factory=dict)
    """Path -> (old_value, new_value) mapping"""

    # Snapshot for rollback
    snapshot: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "state": self.state.value,
            "isolation_level": self.isolation_level.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "source": self.source,
            "description": self.description,
            "change_count": len(self.changes),
        }


class TransactionManager:
    """
    Manages transactions for atomic state updates.

    v1.1: Integrates with StateManager tentative mode.
    """

    def __init__(self, state: Optional["StateManager"] = None):
        """
        Initialize transaction manager.

        Args:
            state: StateManager to manage transactions for
        """
        self.state = state
        self._transactions: Dict[str, TransactionRecord] = {}
        self._active_transaction: Optional[str] = None

    def begin(
        self,
        source: str = "",
        description: str = "",
        isolation: IsolationLevel = IsolationLevel.READ_COMMITTED,
    ) -> str:
        """
        Begin a new transaction.

        Args:
            source: Source identifier
            description: Transaction description
            isolation: Isolation level

        Returns:
            Transaction ID

        Raises:
            RuntimeError: If transaction already active
        """
        if self._active_transaction is not None:
            raise RuntimeError(
                f"Transaction {self._active_transaction} already active. "
                "Commit or rollback before starting new transaction."
            )

        # Create transaction record
        txn = TransactionRecord(
            source=source,
            description=description,
            isolation_level=isolation,
        )

        # Take snapshot for rollback
        if self.state:
            txn.snapshot = serialize_state(self.state)

            # Use StateManager's transaction if available
            if hasattr(self.state, 'begin_transaction'):
                state_txn_id = self.state.begin_transaction()
                txn.transaction_id = state_txn_id

        self._transactions[txn.transaction_id] = txn
        self._active_transaction = txn.transaction_id

        logger.debug(f"Transaction {txn.transaction_id} started by {source}")

        return txn.transaction_id

    def commit(self, transaction_id: Optional[str] = None) -> bool:
        """
        Commit a transaction.

        Args:
            transaction_id: Transaction to commit (defaults to active)

        Returns:
            True if committed successfully
        """
        txn_id = transaction_id or self._active_transaction

        if txn_id is None:
            logger.warning("No active transaction to commit")
            return False

        if txn_id not in self._transactions:
            logger.warning(f"Transaction {txn_id} not found")
            return False

        txn = self._transactions[txn_id]

        if txn.state != TransactionState.ACTIVE:
            logger.warning(f"Transaction {txn_id} is not active: {txn.state}")
            return False

        # Commit via StateManager if available
        if self.state and hasattr(self.state, 'commit_transaction'):
            try:
                self.state.commit_transaction(txn_id)
            except Exception as e:
                logger.error(f"StateManager commit failed: {e}")
                txn.state = TransactionState.FAILED
                return False

        txn.state = TransactionState.COMMITTED
        txn.completed_at = datetime.now(timezone.utc)

        if self._active_transaction == txn_id:
            self._active_transaction = None

        logger.debug(f"Transaction {txn_id} committed")
        return True

    def rollback(self, transaction_id: Optional[str] = None) -> bool:
        """
        Rollback a transaction.

        Args:
            transaction_id: Transaction to rollback (defaults to active)

        Returns:
            True if rolled back successfully
        """
        txn_id = transaction_id or self._active_transaction

        if txn_id is None:
            logger.warning("No active transaction to rollback")
            return False

        if txn_id not in self._transactions:
            logger.warning(f"Transaction {txn_id} not found")
            return False

        txn = self._transactions[txn_id]

        if txn.state != TransactionState.ACTIVE:
            logger.warning(f"Transaction {txn_id} is not active: {txn.state}")
            return False

        # Rollback via StateManager if available
        if self.state:
            if hasattr(self.state, 'rollback_transaction'):
                try:
                    self.state.rollback_transaction(txn_id)
                except Exception as e:
                    logger.error(f"StateManager rollback failed: {e}")

            # Restore from snapshot if direct rollback unavailable
            elif txn.snapshot and hasattr(self.state, 'from_dict'):
                try:
                    self.state.from_dict(txn.snapshot)
                except Exception as e:
                    logger.error(f"Snapshot restore failed: {e}")
                    txn.state = TransactionState.FAILED
                    return False

        txn.state = TransactionState.ROLLED_BACK
        txn.completed_at = datetime.now(timezone.utc)

        if self._active_transaction == txn_id:
            self._active_transaction = None

        logger.debug(f"Transaction {txn_id} rolled back")
        return True

    def record_change(
        self,
        path: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """
        Record a change within the active transaction.

        Args:
            path: Parameter path
            old_value: Previous value
            new_value: New value
        """
        if self._active_transaction:
            txn = self._transactions[self._active_transaction]
            if path not in txn.changes:
                txn.changes[path] = {"old": old_value, "new": new_value}
            else:
                # Update new value, keep original old value
                txn.changes[path]["new"] = new_value

    def get_active_transaction(self) -> Optional[TransactionRecord]:
        """Get the currently active transaction."""
        if self._active_transaction:
            return self._transactions.get(self._active_transaction)
        return None

    def get_transaction(self, transaction_id: str) -> Optional[TransactionRecord]:
        """Get a transaction by ID."""
        return self._transactions.get(transaction_id)

    def get_all_transactions(self) -> List[TransactionRecord]:
        """Get all transactions."""
        return list(self._transactions.values())

    def get_transaction_history(self) -> List[Dict[str, Any]]:
        """Get transaction history as dicts."""
        return [t.to_dict() for t in self._transactions.values()]

    def is_active(self) -> bool:
        """Check if a transaction is active."""
        return self._active_transaction is not None

    def clear_history(self, keep_active: bool = True) -> None:
        """
        Clear transaction history.

        Args:
            keep_active: If True, keep active transaction
        """
        if keep_active and self._active_transaction:
            active = self._transactions.get(self._active_transaction)
            self._transactions = {self._active_transaction: active} if active else {}
        else:
            self._transactions = {}
            self._active_transaction = None
