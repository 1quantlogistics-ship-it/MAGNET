"""
magnet/optimization/transactional_optimizer.py

TA.8: Transactional optimizer scaffold.

Goal:
- Ensure optimizer steps are atomic: propose -> validate -> commit or rollback.
- Provide crash-safe hooks (TA.9 will extend) and version-checked commits.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from magnet.core.design_mutator import CommitResult
from magnet.core.state_concurrency import ConcurrentStateManager, GradientIsolation


@dataclass(frozen=True)
class OptimizerStepResult:
    applied: bool
    reason: str
    commit: Optional[CommitResult] = None


class TransactionalOptimizer:
    def __init__(self, *, manager: ConcurrentStateManager):
        self._manager = manager
        self._grad_iso = GradientIsolation(manager)

    def apply_patch_step(self, updates: Dict[str, Any], *, source: str = "transactional_optimizer") -> OptimizerStepResult:
        """
        Apply a patch atomically if the gradient snapshot isn't stale.
        """
        # Ensure we have a baseline version marker; "no snapshot yet" should not block.
        try:
            self._grad_iso.ensure_version_baseline()
        except Exception:
            self._grad_iso.invalidate_snapshot()
            return OptimizerStepResult(applied=False, reason="snapshot_unavailable")

        if self._grad_iso.is_stale():
            self._grad_iso.invalidate_snapshot()
            return OptimizerStepResult(applied=False, reason="stale_snapshot")

        # Exclusive canonical write. NOTE: ConcurrentStateManager.write_transaction()
        # already opens a StateManager transaction, so we must NOT nest another.
        try:
            with self._manager.write_transaction(mutator_id="optimizer") as sm:
                sm.patch(dict(updates), source=str(source))
        except Exception as e:
            dv = int(getattr(self._manager, "_sm").get("design_version", 0) or 0)  # best-effort
            return OptimizerStepResult(
                applied=False,
                reason="commit_failed",
                commit=CommitResult(success=False, design_version=dv, written_paths=[], error=str(e)),
            )

        # Read commit metadata after commit
        sm_canon = getattr(self._manager, "_sm")
        dv2 = int(sm_canon.get("design_version", 0) or 0)
        wp = sm_canon.get_last_commit_written_paths()
        res = CommitResult(success=True, design_version=dv2, written_paths=list(wp), error=None)

        # Snapshot invalid after any write
        self._grad_iso.invalidate_snapshot()
        return OptimizerStepResult(applied=True, reason="applied", commit=res)


@dataclass(frozen=True)
class OptimizationCheckpoint:
    """
    Minimal recoverable checkpoint for TA.9.
    """

    checkpoint_id: str
    design_version: int
    timestamp: float
    state_snapshot: Dict[str, Any]
    state_hash: str

    def to_json(self) -> str:
        return json.dumps(
            {
                "checkpoint_id": self.checkpoint_id,
                "design_version": self.design_version,
                "timestamp": self.timestamp,
                "state_snapshot": self.state_snapshot,
                "state_hash": self.state_hash,
            }
        )

    @classmethod
    def from_json(cls, s: str) -> "OptimizationCheckpoint":
        data = json.loads(s)
        return cls(
            checkpoint_id=str(data["checkpoint_id"]),
            design_version=int(data["design_version"]),
            timestamp=float(data["timestamp"]),
            state_snapshot=dict(data["state_snapshot"]),
            state_hash=str(data["state_hash"]),
        )


class CrashRecoveryManager:
    """
    TA.9: Crash recovery manager.

    Scope (minimal, consistent with current StateManager capabilities):
    - Detect "zombified" in-progress transactions (state mutated but not committed)
    - Roll back to the pre-transaction snapshot deterministically
    - Optionally persist a checkpoint snapshot to disk
    """

    def __init__(self, *, checkpoint_dir: Optional[Path] = None) -> None:
        self._dir = Path(checkpoint_dir) if checkpoint_dir is not None else None
        if self._dir is not None:
            self._dir.mkdir(parents=True, exist_ok=True)

    def write_checkpoint(self, *, state_manager: Any, checkpoint_id: str) -> OptimizationCheckpoint:
        import time

        snap = state_manager.to_dict()
        dv = int(snap.get("design_version", 0) or 0)
        digest = _hash_state_snapshot(snap)
        ckpt = OptimizationCheckpoint(
            checkpoint_id=str(checkpoint_id),
            design_version=dv,
            timestamp=float(time.time()),
            state_snapshot=snap,
            state_hash=digest,
        )

        if self._dir is not None:
            p = self._dir / f"checkpoint_{ckpt.design_version}_{ckpt.checkpoint_id}.json"
            p.write_text(ckpt.to_json(), encoding="utf-8")
        return ckpt

    def recover_if_needed(self, *, state_manager: Any) -> Tuple[bool, str]:
        """
        Recover from an incomplete in-memory transaction.

        Returns (recovered, reason).
        """
        # In-memory zombie transaction recovery.
        cur_txn = getattr(state_manager, "_current_txn", None)
        if cur_txn is not None:
            try:
                state_manager.rollback_transaction(cur_txn)
                return True, "rolled_back_incomplete_transaction"
            except Exception as e:
                return False, f"rollback_failed:{e}"

        return False, "no_recovery_needed"


def _hash_state_snapshot(snapshot: Dict[str, Any]) -> str:
    # Stable hash of snapshot content (for integrity checks / debugging).
    b = json.dumps(snapshot, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(b).hexdigest()

