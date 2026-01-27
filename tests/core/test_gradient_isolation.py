import threading

from magnet.core.state_concurrency import ConcurrentStateManager, GradientIsolation
from magnet.core.state_manager import StateManager


def test_gradient_isolation_provides_consistent_thread_local_snapshots():
    sm = StateManager()
    mgr = ConcurrentStateManager(sm)
    gi = GradientIsolation(mgr)

    with mgr.write_transaction(mutator_id="init") as w:
        w.set("hull.beam", 5.0, "test")

    values = []
    errors = []

    def worker():
        try:
            snap = gi.get_evaluation_snapshot()
            values.append(float(snap.get("hull.beam")))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=2.0)

    assert not errors
    assert len(values) == 10
    assert all(v == 5.0 for v in values)


def test_gradient_isolation_detects_stale_after_write():
    sm = StateManager()
    mgr = ConcurrentStateManager(sm)
    gi = GradientIsolation(mgr)

    with mgr.write_transaction(mutator_id="init") as w:
        w.set("hull.loa", 20.0, "test")

    snap = gi.get_evaluation_snapshot()
    assert float(snap.get("hull.loa")) == 20.0
    assert gi.is_stale() is False

    with mgr.write_transaction(mutator_id="mut") as w:
        w.set("hull.loa", 21.0, "test")

    assert gi.is_stale() is True

