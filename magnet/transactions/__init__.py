"""
transactions/ - Transaction Model
BRAVO OWNS THIS FILE.

Section 44: Transaction Model

This module provides atomic state operations with commit/rollback semantics.
"""

from .schemas import (
    TransactionStatus,
    IsolationLevel,
    StateChange,
    Savepoint,
    Transaction,
)

from .manager import (
    TransactionManager,
    AtomicBatch,
    atomic,
    compare_and_swap,
)

__all__ = [
    # Schemas
    "TransactionStatus",
    "IsolationLevel",
    "StateChange",
    "Savepoint",
    "Transaction",
    # Manager
    "TransactionManager",
    "AtomicBatch",
    "atomic",
    "compare_and_swap",
]
