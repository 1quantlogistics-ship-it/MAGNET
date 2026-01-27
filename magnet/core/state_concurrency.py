"""
magnet/core/state_concurrency.py

TA.1 / TA.2 foundation: explicit concurrency model for canonical state.

Concurrency Strategy (SWMR):
- Many readers obtain isolated snapshots via StateManager.clone()
- Exactly one writer holds an exclusive transaction at a time
- Writer priority prevents starvation (new readers wait if writer is waiting)

This module does NOT attempt CRDT/eventual merge: geometry+physics constraints are
not commutative, and "eventual merge" can create incoherent states.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import time
import threading
from threading import Condition, RLock
from typing import Generator, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


@dataclass(frozen=True)
class StateVersion:
    """Immutable version marker for optimistic concurrency."""

    version: int
    timestamp: float
    mutator_id: str


class ConcurrentStateManager:
    """
    Thread-safe wrapper providing SWMR semantics over a canonical StateManager.
    """

    def __init__(self, state_manager: "StateManager") -> None:
        self._sm = state_manager
        self._version = StateVersion(version=0, timestamp=time.time(), mutator_id="init")

        self._lock = RLock()
        self._cond = Condition(self._lock)
        self._active_readers = 0
        self._writer_waiting = False
        self._writer_active = False

    def current_version(self) -> StateVersion:
        with self._lock:
            return self._version

    @contextmanager
    def read_snapshot(self) -> Generator["StateManager", None, None]:
        """
        Get an isolated snapshot for reading (never sees partial updates).
        """
        with self._cond:
            while self._writer_waiting or self._writer_active:
                self._cond.wait()
            self._active_readers += 1

        try:
            # Snapshot is isolated (E0.1 requirement).
            snapshot = self._sm.clone()
            yield snapshot
        finally:
            with self._cond:
                self._active_readers -= 1
                if self._active_readers == 0:
                    self._cond.notify_all()

    @contextmanager
    def write_transaction(self, *, mutator_id: str, expected_version: Optional[int] = None) -> Generator["StateManager", None, None]:
        """
        Acquire exclusive write access.

        Notes:
        - This yields the canonical StateManager directly; callers must keep the
          critical section short.
        - On exit, increments version and unblocks readers/writers.
        """
        with self._cond:
            self._writer_waiting = True
            while self._active_readers > 0 or self._writer_active:
                self._cond.wait()
            self._writer_waiting = False
            self._writer_active = True

            if expected_version is not None and int(expected_version) != int(self._version.version):
                self._writer_active = False
                self._cond.notify_all()
                raise RuntimeError(
                    f"stale_write: expected_version={expected_version} current_version={self._version.version}"
                )

        txn_id: Optional[str] = None
        committed = False
        try:
            # StateManager enforces writes via explicit transactions.
            txn_id = self._sm.begin_transaction()
            yield self._sm
            committed = bool(self._sm.commit_transaction(txn_id))
        except Exception:
            if txn_id is not None:
                try:
                    self._sm.rollback_transaction(txn_id)
                except Exception:
                    pass
            raise
        finally:
            with self._cond:
                # Only advance version if we actually committed.
                if committed:
                    self._version = StateVersion(
                        version=int(self._version.version) + 1,
                        timestamp=time.time(),
                        mutator_id=str(mutator_id),
                    )
                self._writer_active = False
                self._cond.notify_all()


class GradientIsolation:
    """
    Thread-local snapshot cache for gradient / what-if evaluation loops.

    Guarantees:
    - Each thread gets a consistent snapshot for a whole gradient computation.
    - Snapshots are invalidated when the canonical state version advances.
    """

    def __init__(self, manager: ConcurrentStateManager) -> None:
        self._manager = manager
        self._local = threading.local()

    def get_evaluation_snapshot(self) -> "StateManager":
        if getattr(self._local, "snapshot", None) is None or self.is_stale():
            with self._manager.read_snapshot() as snap:
                self._local.snapshot = snap
                self._local.version = self._manager.current_version()
        return self._local.snapshot

    def is_stale(self) -> bool:
        v = getattr(self._local, "version", None)
        if v is None:
            return True
        return int(v.version) < int(self._manager.current_version().version)

    def ensure_version_baseline(self) -> None:
        """
        Ensure a version baseline exists without forcing a snapshot clone.

        This is useful for write gates that want to detect "state changed since
        the last compute loop" even if that loop did not need a full snapshot.
        """
        if getattr(self._local, "version", None) is None:
            self._local.version = self._manager.current_version()

    def invalidate_snapshot(self) -> None:
        if hasattr(self._local, "snapshot"):
            delattr(self._local, "snapshot")
        if hasattr(self._local, "version"):
            delattr(self._local, "version")

