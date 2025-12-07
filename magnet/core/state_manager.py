"""
MAGNET StateManager

Path-based state access with alias resolution, transactions, and persistence.
Implements the StateManagerContract interface.
"""

import json
import copy
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from magnet.core.design_state import DesignState
from magnet.core.field_aliases import normalize_path, get_canonical


class StateManager:
    """
    State manager providing path-based access to DesignState.

    Features:
    - Dot-notation path access (e.g., 'mission.max_speed_kts')
    - Alias resolution (e.g., 'mission.max_speed_knots' -> 'mission.max_speed_kts')
    - Transaction support for atomic updates
    - File I/O for persistence
    """

    def __init__(self, state: Optional[DesignState] = None):
        """
        Initialize the state manager.

        Args:
            state: Optional DesignState to manage. Creates new if not provided.
        """
        self._state = state if state is not None else DesignState()
        self._transactions: Dict[str, Dict[str, Any]] = {}
        self._current_txn: Optional[str] = None

    @property
    def state(self) -> DesignState:
        """Access the underlying DesignState."""
        return self._state

    # ==================== Path-Based Access ====================

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
        # Resolve aliases
        canonical_path = normalize_path(path)
        parts = canonical_path.split(".")

        obj: Any = self._state
        for part in parts:
            if obj is None:
                return default
            if hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict):
                obj = obj.get(part, default)
                if obj is default:
                    return default
            else:
                return default

        return obj if obj is not None else default

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
        # Resolve aliases
        canonical_path = normalize_path(path)
        parts = canonical_path.split(".")

        if len(parts) == 0:
            return False

        # Navigate to parent
        obj: Any = self._state
        for part in parts[:-1]:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict):
                if part not in obj:
                    obj[part] = {}
                obj = obj[part]
            else:
                return False

        # Set the final attribute
        final_attr = parts[-1]
        if hasattr(obj, final_attr):
            old_value = getattr(obj, final_attr)
            setattr(obj, final_attr, value)

            # Record in history if in transaction
            if self._current_txn:
                if canonical_path not in self._transactions[self._current_txn]["changes"]:
                    self._transactions[self._current_txn]["changes"][canonical_path] = old_value

            # Update timestamp
            self._state.updated_at = datetime.utcnow().isoformat()

            # Add to history
            self._state.history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "source": source,
                "action": "set",
                "path": canonical_path,
                "old_value": self._serialize_value(old_value),
                "new_value": self._serialize_value(value),
            })

            return True
        elif isinstance(obj, dict):
            old_value = obj.get(final_attr)
            obj[final_attr] = value

            if self._current_txn:
                if canonical_path not in self._transactions[self._current_txn]["changes"]:
                    self._transactions[self._current_txn]["changes"][canonical_path] = old_value

            self._state.updated_at = datetime.utcnow().isoformat()
            return True

        return False

    def _serialize_value(self, value: Any) -> Any:
        """Serialize a value for storage in history."""
        if hasattr(value, "to_dict"):
            return value.to_dict()
        elif isinstance(value, (list, dict)):
            return copy.deepcopy(value)
        else:
            return value

    # ==================== Serialization ====================

    def to_dict(self) -> Dict[str, Any]:
        """Export the entire state as a dictionary."""
        return self._state.to_dict()

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load state from a dictionary, replacing current state."""
        self._state = DesignState.from_dict(data)

    def load_from_dict(self, data: Dict[str, Any]) -> None:
        """Alias for from_dict for API compatibility."""
        self.from_dict(data)

    def export_snapshot(self, include_metadata: bool = True) -> Dict[str, Any]:
        """
        Export a snapshot of the current state.

        Args:
            include_metadata: Whether to include history and metadata.

        Returns:
            Snapshot dictionary suitable for storage or comparison.
        """
        snapshot = self._state.to_dict()

        if not include_metadata:
            snapshot.pop("history", None)
            snapshot.pop("metadata", None)

        snapshot["snapshot_timestamp"] = datetime.utcnow().isoformat()
        return snapshot

    # ==================== File I/O ====================

    def save_to_file(self, filepath: str) -> None:
        """
        Save the current state to a JSON file.

        Args:
            filepath: Path to the output file.
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    def load_from_file(self, filepath: str) -> None:
        """
        Load state from a JSON file.

        Args:
            filepath: Path to the input file.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.from_dict(data)

    # ==================== Validation ====================

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate the current state.

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        return self._state.validate()

    def patch(self, updates: Dict[str, Any], source: str) -> List[str]:
        """
        Apply multiple updates atomically.

        Args:
            updates: Dictionary of path -> value updates.
            source: Identifier of the update source.

        Returns:
            List of paths that were modified.
        """
        modified = []
        for path, value in updates.items():
            if self.set(path, value, source):
                modified.append(normalize_path(path))
        return modified

    def diff(self, other: "StateManager") -> Dict[str, Tuple[Any, Any]]:
        """
        Compare with another state manager.

        Args:
            other: Another StateManager to compare against.

        Returns:
            Dictionary of changed paths to (old, new) tuples.
        """
        return self._state.diff(other._state)

    # ==================== Transactions ====================

    def begin_transaction(self) -> str:
        """
        Begin a new transaction.

        All changes until commit/rollback can be reverted.

        Returns:
            Transaction ID string.
        """
        if self._current_txn is not None:
            raise RuntimeError("Transaction already in progress")

        txn_id = str(uuid.uuid4())
        self._transactions[txn_id] = {
            "started_at": datetime.utcnow().isoformat(),
            "changes": {},
            "snapshot": copy.deepcopy(self._state.to_dict()),
        }
        self._current_txn = txn_id
        return txn_id

    def commit_transaction(self, txn_id: str) -> bool:
        """
        Commit a transaction, making changes permanent.

        Args:
            txn_id: Transaction ID from begin_transaction.

        Returns:
            True if commit successful.
        """
        if txn_id not in self._transactions:
            return False

        if self._current_txn != txn_id:
            return False

        # Clear transaction data
        del self._transactions[txn_id]
        self._current_txn = None

        # Add commit to history
        self._state.history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": "transaction_commit",
            "txn_id": txn_id,
        })

        return True

    def rollback_transaction(self, txn_id: str) -> bool:
        """
        Rollback a transaction, reverting all changes.

        Args:
            txn_id: Transaction ID from begin_transaction.

        Returns:
            True if rollback successful.
        """
        if txn_id not in self._transactions:
            return False

        if self._current_txn != txn_id:
            return False

        # Restore from snapshot
        snapshot = self._transactions[txn_id]["snapshot"]
        self._state = DesignState.from_dict(snapshot)

        # Clear transaction data
        del self._transactions[txn_id]
        self._current_txn = None

        # Add rollback to history
        self._state.history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": "transaction_rollback",
            "txn_id": txn_id,
        })

        return True

    def in_transaction(self) -> bool:
        """
        Check if currently in a transaction.

        Returns:
            True if a transaction is active.
        """
        return self._current_txn is not None

    # ==================== Internal API for Phase Machine ====================

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
        if phase not in self._state.phase_states:
            self._state.phase_states[phase] = {}

        self._state.phase_states[phase] = {
            "state": state,
            "entered_at": datetime.utcnow().isoformat(),
            "entered_by": entered_by,
            **(metadata or {}),
        }

        # Also update phase_metadata
        if phase not in self._state.phase_metadata:
            self._state.phase_metadata[phase] = {}

        self._state.phase_metadata[phase].update({
            "phase": phase,
            "state": state,
            "entered_at": datetime.utcnow().isoformat(),
            "entered_by": entered_by,
        })

        if metadata:
            self._state.phase_metadata[phase].update(metadata)

        self._state.updated_at = datetime.utcnow().isoformat()

    def _get_phase_states_internal(self) -> Dict[str, Dict[str, Any]]:
        """
        Internal method to get all phase states.

        Returns:
            Dictionary mapping phase names to their state info.
        """
        return copy.deepcopy(self._state.phase_states)

    def _set_phase_states_internal(self, phase_states: Dict[str, Dict[str, Any]]) -> None:
        """
        Internal method to set all phase states at once.

        Args:
            phase_states: Dictionary mapping phase names to their state info.
        """
        self._state.phase_states = copy.deepcopy(phase_states)
        self._state.updated_at = datetime.utcnow().isoformat()

    # ==================== Utility Methods ====================

    def get_design_id(self) -> Optional[str]:
        """Get the design ID."""
        return self._state.design_id

    def get_design_name(self) -> Optional[str]:
        """Get the design name."""
        return self._state.design_name

    def set_design_name(self, name: str, source: str) -> None:
        """Set the design name."""
        self.set("design_name", name, source)

    def get_version(self) -> str:
        """Get the design state version."""
        return self._state.version

    def summary(self) -> str:
        """Get a summary of the current state."""
        return self._state.summary()

    def __repr__(self) -> str:
        return f"StateManager({self._state})"
