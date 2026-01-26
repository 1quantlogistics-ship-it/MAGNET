import threading
import time

import pytest

from magnet.core.state_concurrency import ConcurrentStateManager
from magnet.core.state_manager import StateManager


def test_read_snapshot_is_isolated_and_consistent():
    sm = StateManager()
    csm = ConcurrentStateManager(sm)

    with csm.write_transaction(mutator_id="t", expected_version=0) as w:
        w.set("hull.beam", 5.0, "test")

    with csm.read_snapshot() as snap:
        assert snap.get("hull.beam") == 5.0
        # Snapshot is read-only unless it starts its own transaction.
        # (Enforcement happens in StateManager.)
        from magnet.core.state_manager import MutationEnforcementError
        with pytest.raises(MutationEnforcementError):
            snap.set("hull.beam", 7.0, "test")

    assert sm.get("hull.beam") == 5.0


def test_writer_priority_blocks_new_readers_while_waiting():
    sm = StateManager()
    csm = ConcurrentStateManager(sm)

    reader_started = threading.Event()
    writer_started = threading.Event()
    writer_done = threading.Event()
    reader_acquired_after_writer = {"ok": False}

    def writer():
        writer_started.set()
        with csm.write_transaction(mutator_id="writer") as w:
            # Hold the write lock briefly
            time.sleep(0.15)
            w.set("hull.loa", 20.0, "test")
        writer_done.set()

    def reader():
        # Ensure writer is already waiting/active before reader tries.
        writer_started.wait(timeout=1.0)
        reader_started.set()
        t0 = time.time()
        with csm.read_snapshot() as _:
            t1 = time.time()
        # Reader should not acquire before writer releases.
        reader_acquired_after_writer["ok"] = (t1 - t0) >= 0.10

    tw = threading.Thread(target=writer)
    tr = threading.Thread(target=reader)
    tw.start()
    tr.start()
    tw.join(timeout=2.0)
    tr.join(timeout=2.0)

    assert writer_done.is_set()
    assert reader_started.is_set()
    assert reader_acquired_after_writer["ok"] is True


def test_write_transaction_rejects_stale_expected_version():
    sm = StateManager()
    csm = ConcurrentStateManager(sm)

    with csm.write_transaction(mutator_id="t1", expected_version=0):
        pass

    with pytest.raises(RuntimeError):
        with csm.write_transaction(mutator_id="t2", expected_version=0):
            pass

