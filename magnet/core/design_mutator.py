"""
magnet/core/design_mutator.py

T1.1 / T1.2: DesignMutator + transaction model.

Design principle:
- **Single write path**: all mutations to canonical design state must flow through
  this interface, which stages mutations and commits atomically.

This wraps the existing StateManager transaction mechanism rather than creating
another executor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from magnet.core.state_manager import StateManager


@dataclass(frozen=True)
class StagedMutation:
    """
    Minimal transaction model for staged mutations.
    """

    kind: str  # "patch" | "program"
    payload: Any
    source: str = "design_mutator"


@dataclass(frozen=True)
class CommitResult:
    success: bool
    design_version: int
    written_paths: List[str] = field(default_factory=list)
    error: Optional[str] = None


class DesignMutator:
    """All mutations go through here. No direct graph/state writes."""

    def __init__(self, state_manager: StateManager):
        self._state = state_manager
        self._pending: List[StagedMutation] = []

    def stage(self, mutation: StagedMutation) -> None:
        self._pending.append(mutation)

    def stage_patch(self, updates: Dict[str, Any], *, source: str = "design_mutator") -> None:
        self.stage(StagedMutation(kind="patch", payload=dict(updates), source=str(source)))

    def stage_program(self, program: str, *, source: str = "design_mutator") -> None:
        self.stage(StagedMutation(kind="program", payload=str(program), source=str(source)))

    def rollback(self) -> None:
        self._pending.clear()

    def commit(self, *, expected_version: Optional[int] = None) -> CommitResult:
        """
        Atomically apply staged mutations.

        - Begins a StateManager transaction
        - Applies each staged mutation in order
        - Commits on success or rolls back on failure
        """
        # Optimistic concurrency check (design_version is the canonical marker).
        try:
            cur = int(self._state.get("design_version", 0) or 0)
        except Exception:
            cur = 0
        if expected_version is not None and int(expected_version) != int(cur):
            return CommitResult(
                success=False,
                design_version=cur,
                written_paths=[],
                error=f"stale_write: expected_version={expected_version} current_version={cur}",
            )

        txn_id = self._state.begin_transaction()
        try:
            for m in list(self._pending):
                self._apply_one(m)
            ok = bool(self._state.commit_transaction(txn_id))
            dv = int(self._state.get("design_version", cur) or cur)
            wp = self._state.get_last_commit_written_paths()
            self._pending.clear()
            return CommitResult(success=ok, design_version=dv, written_paths=list(wp))
        except Exception as e:
            try:
                self._state.rollback_transaction(txn_id)
            except Exception:
                pass
            return CommitResult(
                success=False,
                design_version=cur,
                written_paths=[],
                error=str(e),
            )

    def _apply_one(self, m: StagedMutation) -> None:
        if m.kind == "patch":
            if not isinstance(m.payload, dict):
                raise TypeError("patch mutation payload must be dict[path,value]")
            self._state.patch(m.payload, source=str(m.source))
            return

        if m.kind == "program":
            # Wrap the existing program executor; do not create a second executor.
            from magnet.kernel.program_executor import execute_program

            program = str(m.payload)
            execute_program(state_manager=self._state, program=program, dry_run=False, validate=True)
            return

        raise ValueError(f"unknown mutation kind: {m.kind!r}")

