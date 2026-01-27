"""
magnet/kernel/gradient_estimator.py

T5.2: Safe Gradient Estimation (optional “physics refine”).

Key guarantees:
- Never evaluate against the live canonical state (E0.1).
- Use clone/perturb/evaluate/discard pattern.
- Use a consistent snapshot per gradient call (TA.2).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Sequence

import numpy as np

from magnet.core.state_concurrency import ConcurrentStateManager, GradientIsolation
from magnet.core.state_manager import StateManager


ObjectiveEvaluator = Callable[[StateManager, Sequence[str]], Dict[str, float]]


@dataclass(frozen=True)
class GradientConfig:
    step_size: float = 1e-3


class SafeGradientEstimator:
    def __init__(
        self,
        *,
        state_manager: ConcurrentStateManager,
        evaluator: ObjectiveEvaluator,
        config: GradientConfig = GradientConfig(),
    ) -> None:
        self._manager = state_manager
        self._evaluator = evaluator
        self._config = config
        self._isolation = GradientIsolation(state_manager)

    def compute_jacobian(self, *, parameters: List[str], objectives: List[str]) -> np.ndarray:
        """
        Finite-difference Jacobian d(objectives)/d(parameters) using safe snapshots.
        """
        params = list(parameters)
        objs = list(objectives)
        if not params or not objs:
            return np.zeros((len(objs), len(params)), dtype=float)

        base = self._isolation.get_evaluation_snapshot()
        base_vals = self._evaluator(base, objs)

        J = np.zeros((len(objs), len(params)), dtype=float)
        h = float(self._config.step_size)

        for i, p in enumerate(params):
            # central difference around base snapshot value
            x0 = float(base.get(p, 0.0) or 0.0)
            plus = _with_parameter(base, p, x0 + h, source="gradient_estimator")
            minus = _with_parameter(base, p, x0 - h, source="gradient_estimator")
            vp = self._evaluator(plus, objs)
            vm = self._evaluator(minus, objs)

            for j, o in enumerate(objs):
                J[j, i] = (float(vp[o]) - float(vm[o])) / (2.0 * h)

        return J

    def is_stale(self) -> bool:
        return self._isolation.is_stale()

    def invalidate_snapshot(self) -> None:
        self._isolation.invalidate_snapshot()


def _with_parameter(base: StateManager, path: str, value: float, *, source: str) -> StateManager:
    """
    Clone a snapshot and apply a single parameter change via StateManager transaction.
    """
    clone = base.clone()
    txn = clone.begin_transaction()
    try:
        clone.set(str(path), float(value), str(source))
        clone.commit_transaction(txn)
    except Exception:
        try:
            clone.rollback_transaction(txn)
        except Exception:
            pass
        raise
    return clone

