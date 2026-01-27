from magnet.core.state_concurrency import ConcurrentStateManager
from magnet.core.state_manager import StateManager
from magnet.optimization.transactional_optimizer import TransactionalOptimizer


def test_transactional_optimizer_applies_patch_atomically():
    sm = StateManager()
    mgr = ConcurrentStateManager(sm)
    opt = TransactionalOptimizer(manager=mgr)

    # Prime a snapshot (so it's not stale)
    opt._grad_iso.get_evaluation_snapshot()

    res = opt.apply_patch_step({"hull.loa": 20.0}, source="test")
    assert res.applied is True
    assert sm.get("hull.loa") == 20.0


def test_transactional_optimizer_rejects_when_snapshot_stale():
    sm = StateManager()
    mgr = ConcurrentStateManager(sm)
    opt = TransactionalOptimizer(manager=mgr)

    # Acquire snapshot at version 0
    opt._grad_iso.get_evaluation_snapshot()

    # Mutate canonical state directly to advance version
    with mgr.write_transaction(mutator_id="writer") as w:
        w.set("hull.beam", 5.0, "test")

    res = opt.apply_patch_step({"hull.loa": 21.0}, source="test")
    assert res.applied is False
    assert res.reason == "stale_snapshot"

