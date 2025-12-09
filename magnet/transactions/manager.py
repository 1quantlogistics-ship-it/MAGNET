"""
transactions/manager.py - Transaction management
BRAVO OWNS THIS FILE.

Section 44: Transaction Model
v1.1: Properly integrates with StateManager tentative mode
"""

from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime
from contextlib import contextmanager
import logging
import uuid

from .schemas import (
    Transaction, TransactionStatus, IsolationLevel,
    StateChange, Savepoint
)

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


def _serialize_state(state: Any) -> Dict[str, Any]:
    """Serialize state to dict for snapshot."""
    if hasattr(state, 'to_dict'):
        return state.to_dict()
    elif hasattr(state, '_state'):
        if hasattr(state._state, 'to_dict'):
            return state._state.to_dict()
        elif hasattr(state._state, '__dict__'):
            return dict(state._state.__dict__)
    elif hasattr(state, '__dict__'):
        return dict(state.__dict__)
    return {}


class TransactionManager:
    """
    Manages transactions for atomic state operations.

    v1.1: Integrates with StateManager tentative write mode.
    """

    def __init__(self, state: "StateManager"):
        self.state = state
        self.logger = logging.getLogger("transactions")

        # Active transactions
        self._transactions: Dict[str, Transaction] = {}

        # Transaction stack (for nesting)
        self._stack: List[str] = []

        # Completed transactions (for audit)
        self._history: List[Transaction] = []
        self._max_history = 100

    @property
    def active_transaction(self) -> Optional[Transaction]:
        """Get current active transaction."""
        if self._stack:
            return self._transactions.get(self._stack[-1])
        return None

    @property
    def active_transaction_id(self) -> Optional[str]:
        """Get current active transaction ID."""
        return self._stack[-1] if self._stack else None

    def begin(
        self,
        transaction_id: str = None,
        source: str = "",
        description: str = "",
        isolation: IsolationLevel = IsolationLevel.READ_COMMITTED,
    ) -> Transaction:
        """Begin a new transaction."""
        tx_id = transaction_id or str(uuid.uuid4())[:8]

        # Create transaction
        tx = Transaction(
            transaction_id=tx_id,
            status=TransactionStatus.ACTIVE,
            isolation=isolation,
            source=source,
            description=description,
        )

        # Set parent if nested
        if self._stack:
            tx.parent_transaction_id = self._stack[-1]

        # v1.1: Capture initial snapshot for rollback
        tx.initial_snapshot = _serialize_state(self.state)

        # v1.1: Tell StateManager to enter tentative mode
        if hasattr(self.state, 'begin_tentative'):
            self.state.begin_tentative(tx_id)
        elif hasattr(self.state, '_active_transaction'):
            self.state._active_transaction = tx_id

        # Store and push
        self._transactions[tx_id] = tx
        self._stack.append(tx_id)

        self.logger.info(f"Transaction {tx_id} started")

        return tx

    def commit(self, transaction_id: str = None) -> bool:
        """Commit a transaction."""
        tx_id = transaction_id or self.active_transaction_id

        if not tx_id or tx_id not in self._transactions:
            self.logger.error(f"Cannot commit: transaction {tx_id} not found")
            return False

        tx = self._transactions[tx_id]

        # Must be active
        if tx.status != TransactionStatus.ACTIVE:
            self.logger.error(f"Cannot commit: transaction {tx_id} is {tx.status.value}")
            return False

        # v1.1: Tell StateManager to commit tentative writes
        if hasattr(self.state, 'commit_tentative'):
            self.state.commit_tentative()
        elif hasattr(self.state, '_active_transaction'):
            self.state._active_transaction = None

        # Update transaction
        tx.status = TransactionStatus.COMMITTED
        tx.completed_at = datetime.utcnow()

        # Remove from stack
        if tx_id in self._stack:
            self._stack.remove(tx_id)

        # Move to history
        self._add_to_history(tx)
        del self._transactions[tx_id]

        self.logger.info(f"Transaction {tx_id} committed")

        return True

    def rollback(self, transaction_id: str = None) -> bool:
        """Rollback a transaction."""
        tx_id = transaction_id or self.active_transaction_id

        if not tx_id or tx_id not in self._transactions:
            self.logger.error(f"Cannot rollback: transaction {tx_id} not found")
            return False

        tx = self._transactions[tx_id]

        # Must be active
        if tx.status != TransactionStatus.ACTIVE:
            self.logger.error(f"Cannot rollback: transaction {tx_id} is {tx.status.value}")
            return False

        # v1.1: Tell StateManager to rollback tentative writes
        if hasattr(self.state, 'rollback_tentative'):
            self.state.rollback_tentative()
        elif tx.initial_snapshot:
            # Fallback: restore from snapshot
            self._restore_snapshot(tx.initial_snapshot)

        if hasattr(self.state, '_active_transaction'):
            self.state._active_transaction = None

        # Update transaction
        tx.status = TransactionStatus.ROLLED_BACK
        tx.completed_at = datetime.utcnow()

        # Remove from stack
        if tx_id in self._stack:
            self._stack.remove(tx_id)

        # Move to history
        self._add_to_history(tx)
        del self._transactions[tx_id]

        self.logger.info(f"Transaction {tx_id} rolled back")

        return True

    def _restore_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """Restore state from snapshot."""
        if hasattr(self.state, 'load_from_dict'):
            self.state.load_from_dict(snapshot)
        else:
            # Manual restoration
            for key, value in snapshot.items():
                if hasattr(self.state, '_state') and hasattr(self.state._state, key):
                    setattr(self.state._state, key, value)

    def create_savepoint(self, name: str = None) -> Optional[Savepoint]:
        """Create a savepoint in current transaction."""
        tx = self.active_transaction
        if not tx:
            return None

        savepoint = Savepoint(
            savepoint_id=str(uuid.uuid4())[:8],
            transaction_id=tx.transaction_id,
            name=name or f"sp_{len(tx.savepoints) + 1}",
            state_snapshot=_serialize_state(self.state),
        )

        tx.savepoints.append(savepoint)

        self.logger.debug(f"Savepoint {savepoint.name} created")

        return savepoint

    def rollback_to_savepoint(self, savepoint_name: str) -> bool:
        """Rollback to a savepoint."""
        tx = self.active_transaction
        if not tx:
            return False

        # Find savepoint
        savepoint = None
        for sp in reversed(tx.savepoints):
            if sp.name == savepoint_name:
                savepoint = sp
                break

        if not savepoint:
            self.logger.error(f"Savepoint {savepoint_name} not found")
            return False

        # Restore state
        self._restore_snapshot(savepoint.state_snapshot)

        # Remove savepoints after this one
        idx = tx.savepoints.index(savepoint)
        tx.savepoints = tx.savepoints[:idx + 1]

        self.logger.info(f"Rolled back to savepoint {savepoint_name}")

        return True

    def record_change(
        self,
        path: str,
        old_value: Any,
        new_value: Any,
        source: str = "",
    ) -> Optional[StateChange]:
        """Record a state change in active transaction."""
        tx = self.active_transaction
        if not tx:
            return None

        change = StateChange(
            change_id=str(uuid.uuid4())[:8],
            transaction_id=tx.transaction_id,
            path=path,
            old_value=old_value,
            new_value=new_value,
            source=source,
        )

        tx.changes.append(change)

        return change

    @contextmanager
    def transaction(
        self,
        source: str = "",
        description: str = "",
    ):
        """Context manager for transactions."""
        tx = self.begin(source=source, description=description)
        try:
            yield tx
            self.commit(tx.transaction_id)
        except Exception as e:
            self.rollback(tx.transaction_id)
            raise

    def _add_to_history(self, tx: Transaction) -> None:
        """Add transaction to history."""
        self._history.append(tx)

        # Trim history
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_history(self, limit: int = 20) -> List[Transaction]:
        """Get transaction history."""
        return self._history[-limit:]


# === DECORATORS ===

def atomic(state: "StateManager"):
    """
    Decorator for atomic functions.

    Usage:
        @atomic(state_manager)
        def my_function():
            ...
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            tx_manager = TransactionManager(state)
            with tx_manager.transaction(source=func.__name__):
                return func(*args, **kwargs)
        return wrapper
    return decorator


class AtomicBatch:
    """
    Batch multiple writes into single transaction.

    Usage:
        with AtomicBatch(state) as batch:
            batch.write("hull.beam", 6.0)
            batch.write("hull.draft", 1.5)
    """

    def __init__(self, state: "StateManager"):
        self.state = state
        self.tx_manager = TransactionManager(state)
        self._writes: List[tuple] = []
        self._tx: Optional[Transaction] = None

    def __enter__(self):
        self._tx = self.tx_manager.begin(source="atomic_batch")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.tx_manager.rollback()
        else:
            self.tx_manager.commit()

    def write(self, path: str, value: Any, source: str = "batch") -> None:
        """Queue a write."""
        if hasattr(self.state, 'set'):
            self.state.set(path, value)
        elif hasattr(self.state, 'write'):
            self.state.write(path, value)
        self._writes.append((path, value))


def compare_and_swap(
    state: "StateManager",
    path: str,
    expected: Any,
    new_value: Any,
) -> bool:
    """
    Atomic compare-and-swap operation.

    Returns True if swap succeeded (current value matched expected).
    """
    tx_manager = TransactionManager(state)

    try:
        with tx_manager.transaction(source="cas"):
            if hasattr(state, 'get'):
                current = state.get(path)
            else:
                current = None

            if current == expected:
                if hasattr(state, 'set'):
                    state.set(path, new_value)
                elif hasattr(state, 'write'):
                    state.write(path, new_value)
                return True
            else:
                # Rollback will happen automatically
                raise ValueError(f"CAS failed: expected {expected}, got {current}")
    except ValueError:
        return False
