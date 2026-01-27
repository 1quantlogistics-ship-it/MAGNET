"""
magnet/core/proposal_sandbox.py

T1.5: Proposal sandbox + approval gate.

Goal:
- Allow speculative "what-if" execution without mutating canonical state.
- Surface diffs and require explicit approval before applying.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from magnet.core.design_mutator import DesignMutator, StagedMutation, CommitResult
from magnet.core.state_manager import StateManager


@dataclass(frozen=True)
class ProposalResult:
    success: bool
    diff: Dict[str, tuple[Any, Any]]
    error: Optional[str] = None


class ProposalSandbox:
    def __init__(self, *, state_manager: StateManager):
        self._state = state_manager

    def propose(self, mutation: StagedMutation) -> ProposalResult:
        """
        Execute staged mutation on a clone and return a diff against canonical.
        """
        try:
            base = self._state
            cand = base.clone()
            mut = DesignMutator(cand)
            mut.stage(mutation)
            res = mut.commit(expected_version=int(cand.get("design_version", 0) or 0))
            if not res.success:
                return ProposalResult(success=False, diff={}, error=res.error or "commit_failed")
            d = base.diff(cand)
            return ProposalResult(success=True, diff=d, error=None)
        except Exception as e:
            return ProposalResult(success=False, diff={}, error=str(e))

    def apply_if_approved(self, mutation: StagedMutation, *, approved: bool) -> CommitResult:
        """
        Apply the mutation to canonical state only if approved.
        """
        if not approved:
            dv = int(self._state.get("design_version", 0) or 0)
            return CommitResult(success=False, design_version=dv, written_paths=[], error="not_approved")

        mut = DesignMutator(self._state)
        mut.stage(mutation)
        return mut.commit(expected_version=int(self._state.get("design_version", 0) or 0))

