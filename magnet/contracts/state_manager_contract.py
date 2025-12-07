"""
StateManager Contract - Abstract Base Class

Defines the interface for state management operations including:
- Path-based access with alias resolution
- Serialization and persistence
- Transaction support
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple, Optional


class StateManagerContract(ABC):
    """
    Abstract contract for the state manager.

    Provides path-based access to design state with:
    - Alias resolution (e.g., 'mission.max_speed_knots' -> 'mission.max_speed_kts')
    - Transaction support for atomic updates
    - File I/O for persistence
    """

    # ==================== Path-Based Access ====================

    @abstractmethod
    def get(self, path: str, default: Any = None) -> Any:
        """
        Get a value from the state using dot-notation path.

        Supports alias resolution - alternative names are mapped to canonical paths.

        Args:
            path: Dot-notation path (e.g., 'mission.max_speed_kts')
            default: Value to return if path not found.

        Returns:
            The value at the path, or default if not found.
        """
        pass

    @abstractmethod
    def set(self, path: str, value: Any, source: str) -> bool:
        """
        Set a value in the state using dot-notation path.

        Args:
            path: Dot-notation path to set.
            value: New value to assign.
            source: Identifier of who is making the change.

        Returns:
            True if successful, False otherwise.
        """
        pass

    # ==================== Serialization ====================

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Export the entire state as a dictionary.

        Returns:
            Complete state serialized to dictionary.
        """
        pass

    @abstractmethod
    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Load state from a dictionary, replacing current state.

        Args:
            data: Dictionary containing serialized state.
        """
        pass

    @abstractmethod
    def load_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Alias for from_dict for API compatibility.
        """
        pass

    @abstractmethod
    def export_snapshot(self, include_metadata: bool = True) -> Dict[str, Any]:
        """
        Export a snapshot of the current state.

        Args:
            include_metadata: Whether to include history and metadata.

        Returns:
            Snapshot dictionary suitable for storage or comparison.
        """
        pass

    # ==================== File I/O ====================

    @abstractmethod
    def save_to_file(self, filepath: str) -> None:
        """
        Save the current state to a JSON file.

        Args:
            filepath: Path to the output file.
        """
        pass

    @abstractmethod
    def load_from_file(self, filepath: str) -> None:
        """
        Load state from a JSON file.

        Args:
            filepath: Path to the input file.
        """
        pass

    # ==================== Validation ====================

    @abstractmethod
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate the current state.

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        pass

    @abstractmethod
    def patch(self, updates: Dict[str, Any], source: str) -> List[str]:
        """
        Apply multiple updates atomically.

        Args:
            updates: Dictionary of path -> value updates.
            source: Identifier of the update source.

        Returns:
            List of paths that were modified.
        """
        pass

    @abstractmethod
    def diff(self, other: "StateManagerContract") -> Dict[str, Tuple[Any, Any]]:
        """
        Compare with another state manager.

        Args:
            other: Another StateManager to compare against.

        Returns:
            Dictionary of changed paths to (old, new) tuples.
        """
        pass

    # ==================== Transactions ====================

    @abstractmethod
    def begin_transaction(self) -> str:
        """
        Begin a new transaction.

        All changes until commit/rollback can be reverted.

        Returns:
            Transaction ID string.
        """
        pass

    @abstractmethod
    def commit_transaction(self, txn_id: str) -> bool:
        """
        Commit a transaction, making changes permanent.

        Args:
            txn_id: Transaction ID from begin_transaction.

        Returns:
            True if commit successful.
        """
        pass

    @abstractmethod
    def rollback_transaction(self, txn_id: str) -> bool:
        """
        Rollback a transaction, reverting all changes.

        Args:
            txn_id: Transaction ID from begin_transaction.

        Returns:
            True if rollback successful.
        """
        pass

    @abstractmethod
    def in_transaction(self) -> bool:
        """
        Check if currently in a transaction.

        Returns:
            True if a transaction is active.
        """
        pass

    # ==================== Internal API for Phase Machine ====================

    @abstractmethod
    def _set_phase_state_internal(
        self,
        phase: str,
        state: str,
        entered_by: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Internal method for phase machine to update phase states.

        This bypasses normal validation to allow the phase machine
        to manage its own state transitions.

        Args:
            phase: Phase name (e.g., 'mission', 'hull_form')
            state: New state (e.g., 'draft', 'active', 'locked')
            entered_by: Who triggered the transition
            metadata: Additional metadata for the transition
        """
        pass

    @abstractmethod
    def _get_phase_states_internal(self) -> Dict[str, Dict[str, Any]]:
        """
        Internal method to get all phase states.

        Returns:
            Dictionary mapping phase names to their state info.
        """
        pass
