"""
glue/transactions/isolation.py - Transaction isolation levels

ALPHA OWNS THIS FILE.

Module 44: Transaction Model
"""

from enum import Enum


class IsolationLevel(Enum):
    """
    Transaction isolation levels.

    Defines how concurrent transactions interact with each other.
    """

    READ_UNCOMMITTED = "read_uncommitted"
    """
    Lowest isolation. Transactions can see uncommitted changes from other transactions.
    Allows dirty reads.
    """

    READ_COMMITTED = "read_committed"
    """
    Default level. Transactions only see committed changes.
    Prevents dirty reads but allows non-repeatable reads.
    """

    REPEATABLE_READ = "repeatable_read"
    """
    Higher isolation. Guarantees same query returns same results within transaction.
    Prevents non-repeatable reads but allows phantom reads.
    """

    SERIALIZABLE = "serializable"
    """
    Highest isolation. Transactions are completely isolated.
    Prevents all concurrency anomalies but may reduce throughput.
    """

    @classmethod
    def default(cls) -> "IsolationLevel":
        """Get the default isolation level."""
        return cls.READ_COMMITTED

    @property
    def allows_dirty_reads(self) -> bool:
        """Check if this level allows dirty reads."""
        return self == IsolationLevel.READ_UNCOMMITTED

    @property
    def prevents_phantom_reads(self) -> bool:
        """Check if this level prevents phantom reads."""
        return self == IsolationLevel.SERIALIZABLE
