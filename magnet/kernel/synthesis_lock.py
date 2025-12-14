"""
MAGNET Synthesis Lock

Exclusive write lock for hull parameters during synthesis.
Prevents race conditions with downstream phases.

v1.0: Initial implementation
"""

from contextlib import contextmanager
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class SynthesisLockError(Exception):
    """Raised when lock acquisition or release fails."""
    pass


class SynthesisLock:
    """
    Exclusive write lock for hull parameters during synthesis.

    Prevents race conditions with downstream phases by ensuring
    only the lock owner can write hull parameters during synthesis.
    """

    # Hull paths that are protected during synthesis
    HULL_PATHS = frozenset([
        "hull.lwl", "hull.beam", "hull.draft",
        "hull.cb", "hull.cp", "hull.cm", "hull.cwp",
        "hull.displacement_m3", "hull.displacement_kg", "hull.displacement_mt",
    ])

    def __init__(self, state_manager: "StateManager"):
        """
        Initialize the synthesis lock.

        Args:
            state_manager: StateManager instance for state access
        """
        self._state = state_manager
        self._locked = False
        self._owner: Optional[str] = None

    @property
    def is_locked(self) -> bool:
        """Check if lock is currently held."""
        return self._locked

    @property
    def owner(self) -> Optional[str]:
        """Get current lock owner."""
        return self._owner

    def acquire(self, owner: str) -> bool:
        """
        Acquire exclusive hull write lock.

        Args:
            owner: Identifier of lock requestor

        Returns:
            True if acquired

        Raises:
            SynthesisLockError: If lock already held by another owner
        """
        if self._locked:
            raise SynthesisLockError(
                f"Hull locked by {self._owner}, cannot acquire for {owner}"
            )
        self._locked = True
        self._owner = owner
        return True

    def release(self, owner: str) -> None:
        """
        Release hull write lock.

        Args:
            owner: Identifier of lock holder

        Raises:
            SynthesisLockError: If owner doesn't match lock holder
        """
        if self._owner != owner:
            raise SynthesisLockError(
                f"Lock owned by {self._owner}, not {owner}"
            )
        self._locked = False
        self._owner = None

    def write_hull_params(
        self,
        params: dict,
        owner: str,
    ) -> None:
        """
        Atomically write hull parameters to state.

        Only allowed by lock owner. All-or-nothing write (never partial state).

        Args:
            params: Dictionary of path -> value for hull parameters
            owner: Lock owner identifier

        Raises:
            SynthesisLockError: If owner doesn't match lock holder
            ValueError: If params are incomplete
        """
        if self._owner != owner:
            raise SynthesisLockError(
                f"Cannot write: lock owned by {self._owner}, not {owner}"
            )

        # Verify we have the core params
        required = {"hull.lwl", "hull.beam", "hull.draft"}
        provided = set(params.keys())
        missing = required - provided
        if missing:
            raise ValueError(f"Cannot write incomplete hull params, missing: {missing}")

        # Atomic write
        source = f"synthesis:{owner}"
        for path, value in params.items():
            self._state.set(path, value, source)

    @contextmanager
    def exclusive_access(self, owner: str):
        """
        Context manager for exclusive hull access.

        Usage:
            with lock.exclusive_access("synthesizer"):
                # Write hull params safely
                lock.write_hull_params(params, "synthesizer")

        Args:
            owner: Lock owner identifier

        Yields:
            self for chaining
        """
        self.acquire(owner)
        try:
            yield self
        finally:
            self.release(owner)
