"""
magnet/optimization/probabilistic_optimizer.py

TM.6: Probabilistic optimizer (chance constraints / robustness).

This is a lightweight, surrogate-space optimizer that:
- maximizes a robust objective (mean - k*std) by default
- supports simple Normal-approx chance constraints using surrogate mean/std

NOTE:
- This is NOT a naval-architecture heuristic engine.
- It operates only on distributions over scalar outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, List, Optional, Protocol, Tuple

import numpy as np


class SurrogatePredictor(Protocol):
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]: ...


@dataclass(frozen=True)
class ChanceConstraint:
    name: str
    predictor: SurrogatePredictor
    threshold: float
    direction: str  # "ge" | "le"
    min_probability: float = 0.9


@dataclass(frozen=True)
class ProbabilisticOptimizationResult:
    design: Dict[str, float]
    score: float
    physics_evaluations: int = 0
    surrogate_evaluations: int = 0
    constraint_satisfaction_probability: Dict[str, float] = None


class ProbabilisticOptimizer:
    def __init__(
        self,
        *,
        parameter_bounds: Dict[str, Tuple[float, float]],
        objective_name: str,
        objective_model: SurrogatePredictor,
        chance_constraints: Optional[List[ChanceConstraint]] = None,
        robustness_k: float = 1.0,
        seed: int = 0,
    ) -> None:
        self._bounds = dict(parameter_bounds)
        self._param_names = list(self._bounds.keys())
        self._objective_name = str(objective_name)
        self._obj = objective_model
        self._constraints = list(chance_constraints or [])
        self._k = float(robustness_k)
        self._rng = np.random.default_rng(int(seed))

        if not self._param_names:
            raise ValueError("parameter_bounds must be non-empty")

    def optimize(self, *, n_candidates: int = 512) -> ProbabilisticOptimizationResult:
        X = self._sample_candidates(int(n_candidates))

        best_i = None
        best_score = -float("inf")
        best_probs: Dict[str, float] = {}

        # objective is maximized in robust form: mean - k*std
        mean, std = self._obj.predict(X)
        mean = np.asarray(mean, dtype=float).reshape(-1)
        std = np.asarray(std, dtype=float).reshape(-1)

        for i in range(X.shape[0]):
            probs = {}
            ok = True
            for c in self._constraints:
                p = _normal_chance_satisfaction_probability(
                    predictor=c.predictor,
                    x=X[i : i + 1, :],
                    threshold=float(c.threshold),
                    direction=str(c.direction),
                )
                probs[c.name] = p
                if p < float(c.min_probability):
                    ok = False
                    break

            if not ok:
                continue

            score = float(mean[i]) - self._k * float(std[i])
            if score > best_score:
                best_score = score
                best_i = i
                best_probs = probs

        if best_i is None:
            # No feasible candidates: return best robust score without constraints.
            best_i = int(np.argmax(mean - self._k * std))
            best_score = float(mean[best_i]) - self._k * float(std[best_i])
            best_probs = {}

        design = {name: float(X[best_i, j]) for j, name in enumerate(self._param_names)}
        return ProbabilisticOptimizationResult(
            design=design,
            score=float(best_score),
            physics_evaluations=0,
            surrogate_evaluations=int(X.shape[0]),
            constraint_satisfaction_probability=best_probs,
        )

    def _sample_candidates(self, n: int) -> np.ndarray:
        X = np.zeros((int(n), len(self._param_names)), dtype=float)
        for j, name in enumerate(self._param_names):
            lo, hi = self._bounds[name]
            X[:, j] = self._rng.uniform(float(lo), float(hi), size=int(n))
        return X


def _normal_cdf(z: float) -> float:
    # Standard normal CDF via erf; avoids scipy dependency.
    return 0.5 * (1.0 + math.erf(float(z) / math.sqrt(2.0)))


def _normal_chance_satisfaction_probability(
    *,
    predictor: SurrogatePredictor,
    x: np.ndarray,
    threshold: float,
    direction: str,
) -> float:
    mean, std = predictor.predict(np.asarray(x, dtype=float))
    m = float(np.asarray(mean, dtype=float).reshape(-1)[0])
    s = float(np.asarray(std, dtype=float).reshape(-1)[0])
    if not math.isfinite(s) or s <= 1e-12:
        # Deterministic case.
        if direction == "ge":
            return 1.0 if m >= float(threshold) else 0.0
        if direction == "le":
            return 1.0 if m <= float(threshold) else 0.0
        raise ValueError("direction must be 'ge' or 'le'")

    if direction == "ge":
        # P(Y >= t) = 1 - Phi((t - m)/s)
        return float(1.0 - _normal_cdf((float(threshold) - m) / s))
    if direction == "le":
        # P(Y <= t) = Phi((t - m)/s)
        return float(_normal_cdf((float(threshold) - m) / s))
    raise ValueError("direction must be 'ge' or 'le'")

