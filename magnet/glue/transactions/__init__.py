"""
glue/transactions/ - Transaction Model (Module 44)

ALPHA OWNS THIS FILE.

Provides transaction management for atomic state updates.
"""

from .manager import (
    TransactionState,
    TransactionRecord,
    TransactionManager,
)

from .isolation import IsolationLevel


__all__ = [
    "TransactionState",
    "TransactionRecord",
    "TransactionManager",
    "IsolationLevel",
]
