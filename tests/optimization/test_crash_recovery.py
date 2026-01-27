from pathlib import Path

from magnet.core.state_manager import StateManager
from magnet.optimization.transactional_optimizer import CrashRecoveryManager


def test_crash_recovery_rolls_back_incomplete_transaction(tmp_path: Path):
    sm = StateManager()

    # Establish a committed baseline.
    sm.begin_transaction()
    sm.set("hull.loa", 20.0, source="test")
    sm.commit()
    assert sm.get("hull.loa") == 20.0

    # Start a transaction, mutate state, and "crash" (no commit/rollback).
    txn = sm.begin_transaction()
    sm.set("hull.loa", 25.0, source="test")
    assert sm.get("hull.loa") == 25.0
    assert sm.in_transaction() is True

    # Recover should rollback to pre-transaction snapshot.
    crm = CrashRecoveryManager(checkpoint_dir=tmp_path)
    recovered, reason = crm.recover_if_needed(state_manager=sm)
    assert recovered is True
    assert "rolled_back" in reason
    assert sm.in_transaction() is False
    assert sm.get("hull.loa") == 20.0


def test_crash_recovery_can_write_checkpoint(tmp_path: Path):
    sm = StateManager()
    sm.begin_transaction()
    sm.set("hull.loa", 22.0, source="test")
    sm.commit()

    crm = CrashRecoveryManager(checkpoint_dir=tmp_path)
    ckpt = crm.write_checkpoint(state_manager=sm, checkpoint_id="ck0")
    assert ckpt.design_version == int(sm.get("design_version", 0) or 0)

    # File exists
    files = list(tmp_path.glob("checkpoint_*.json"))
    assert files, "expected checkpoint file"

