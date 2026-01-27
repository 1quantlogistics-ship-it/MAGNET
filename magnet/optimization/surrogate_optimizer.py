"""
magnet/optimization/surrogate_optimizer.py

TM.2: Multi-fidelity surrogate optimizer (surrogate-first, physics-validated).

This is a *numerical search* strategy. It must not contain intent or
naval-architecture heuristics. It operates only on:
- parameter bounds
- objective scalar outputs (from a PhysicsEvaluator-like adapter)
- optional constraint predicates

Contract focus:
- deterministic operation with a seed
- explicit physics evaluation budget
- explicit tracking of surrogate vs physics evaluations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Protocol, Tuple

import numpy as np
from scipy.stats.qmc import LatinHypercube

from magnet.optimization.surrogate_model import SurrogateModel


class PhysicsEvaluator(Protocol):
    """
    Minimal evaluator contract (TM.3A will formalize this).
    """

    def evaluate(self, params: Dict[str, float], objective: str) -> float: ...


ConstraintFn = Callable[[Dict[str, float]], bool]


@dataclass
class OptimizationContext:
    """Multi-fidelity optimization state."""

    low_fidelity_model: Dict[str, SurrogateModel] = field(default_factory=dict)  # objective -> model
    high_fidelity_budget: int = 50
    confidence_threshold: float = 0.1
    exploration_rate: float = 0.2

    physics_evaluations_used: int = 0
    surrogate_evaluations_used: int = 0

    # Training archive (for transparency/debugging)
    X: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))
    y_by_objective: Dict[str, np.ndarray] = field(default_factory=dict)
    param_names: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class OptimizationResult:
    best_params: Dict[str, float]
    best_objectives: Dict[str, float]
    physics_evaluations_used: int
    surrogate_evaluations_used: int


class MultiFidelitySurrogateOptimizer:
    """
    Simple Bayesian-optimization-like loop:
    - bootstrap with LHS physics samples
    - fit surrogates per objective
    - iterate: propose candidates via random EI search, evaluate physics, refit
    """

    def __init__(
        self,
        *,
        physics_evaluator: PhysicsEvaluator,
        parameter_bounds: Dict[str, Tuple[float, float]],
        objectives: List[str],
        constraints: Optional[List[ConstraintFn]] = None,
        initial_samples: int = 16,
        high_fidelity_budget: int = 50,
        seed: int = 0,
    ):
        self._physics = physics_evaluator
        self._bounds = dict(parameter_bounds)
        self._objectives = list(objectives)
        self._constraints = list(constraints or [])
        self._initial_samples = int(initial_samples)
        self._seed = int(seed)

        if not self._bounds:
            raise ValueError("parameter_bounds must be non-empty")
        if not self._objectives:
            raise ValueError("objectives must be non-empty")

        self._context = OptimizationContext(
            high_fidelity_budget=int(high_fidelity_budget),
        )
        self._context.param_names = list(self._bounds.keys())

        self._rng = np.random.default_rng(self._seed)

    def optimize(self, *, max_iterations: int = 30) -> OptimizationResult:
        self._initialize_surrogates()

        # Choose incumbent by max of first objective (caller can negate if minimizing).
        best_params, best_obj = self._best_seen()

        for _ in range(int(max_iterations)):
            if self._context.physics_evaluations_used >= self._context.high_fidelity_budget:
                break

            cand = self._propose_candidate(best_obj[self._objectives[0]])
            obj_vals = self._evaluate_physics(cand)
            self._append_training(cand, obj_vals)
            self._refit_surrogates()

            best_params, best_obj = self._best_seen()

        return OptimizationResult(
            best_params=best_params,
            best_objectives=best_obj,
            physics_evaluations_used=int(self._context.physics_evaluations_used),
            surrogate_evaluations_used=int(self._context.surrogate_evaluations_used),
        )

    # -------------------------
    # Initialization / training
    # -------------------------

    def _initialize_surrogates(self) -> None:
        # Initial LHS points in bounds
        n_params = len(self._bounds)
        sampler = LatinHypercube(d=n_params, seed=self._seed)
        samples_unit = sampler.random(n=self._initial_samples)

        X = np.zeros_like(samples_unit)
        for i, name in enumerate(self._context.param_names):
            lo, hi = self._bounds[name]
            X[:, i] = samples_unit[:, i] * (hi - lo) + lo

        # Evaluate physics
        for row in X:
            params = dict(zip(self._context.param_names, [float(v) for v in row]))
            if not self._constraints_satisfied(params):
                continue
            obj_vals = self._evaluate_physics(params)
            self._append_training(params, obj_vals)

        # Create and fit models per objective.
        for obj in self._objectives:
            self._context.low_fidelity_model[obj] = SurrogateModel(
                parameter_names=list(self._context.param_names),
                objective_name=str(obj),
            )
        self._refit_surrogates()

    def _refit_surrogates(self) -> None:
        if self._context.X.size == 0:
            return
        X = self._context.X
        for obj, model in self._context.low_fidelity_model.items():
            y = self._context.y_by_objective.get(obj)
            if y is None or y.size == 0:
                continue
            model.fit(X, y)

    def _append_training(self, params: Dict[str, float], obj_vals: Dict[str, float]) -> None:
        x = np.array([[float(params[n]) for n in self._context.param_names]], dtype=float)
        if self._context.X.size == 0:
            self._context.X = x
        else:
            self._context.X = np.vstack([self._context.X, x])

        for obj in self._objectives:
            y = self._context.y_by_objective.get(obj)
            v = float(obj_vals[obj])
            if y is None or y.size == 0:
                self._context.y_by_objective[obj] = np.array([v], dtype=float)
            else:
                self._context.y_by_objective[obj] = np.concatenate([y, np.array([v], dtype=float)])

    # -------------------------
    # Candidate proposal
    # -------------------------

    def _propose_candidate(self, best_y: float, *, n_candidates: int = 256) -> Dict[str, float]:
        # Random candidate pool, score via EI on the first objective.
        obj0 = self._objectives[0]
        model = self._context.low_fidelity_model[obj0]

        cand_params: List[Dict[str, float]] = []
        Xc = np.zeros((int(n_candidates), len(self._bounds)), dtype=float)
        for i in range(int(n_candidates)):
            p = {}
            for j, name in enumerate(self._context.param_names):
                lo, hi = self._bounds[name]
                v = float(self._rng.uniform(lo, hi))
                p[name] = v
                Xc[i, j] = v
            cand_params.append(p)

        # Filter constraints (cheap)
        feasible_idx = [i for i, p in enumerate(cand_params) if self._constraints_satisfied(p)]
        if not feasible_idx:
            # No feasible candidates in pool: return a random draw (still deterministic).
            return cand_params[0]

        best_i = feasible_idx[0]
        best_ei = -1.0
        for i in feasible_idx:
            self._context.surrogate_evaluations_used += 1
            ei = model.acquisition_value(Xc[i], best_y=float(best_y), exploration_weight=0.01)
            if ei > best_ei:
                best_ei = ei
                best_i = i

        return cand_params[best_i]

    # -------------------------
    # Evaluation helpers
    # -------------------------

    def _evaluate_physics(self, params: Dict[str, float]) -> Dict[str, float]:
        self._context.physics_evaluations_used += 1
        out: Dict[str, float] = {}
        for obj in self._objectives:
            out[obj] = float(self._physics.evaluate(params, obj))
        return out

    def _constraints_satisfied(self, params: Dict[str, float]) -> bool:
        for c in self._constraints:
            try:
                if not bool(c(params)):
                    return False
            except Exception:
                return False
        return True

    def _best_seen(self) -> Tuple[Dict[str, float], Dict[str, float]]:
        # Choose best by objective[0] maximum.
        if self._context.X.size == 0:
            # Fallback: center of bounds
            p = {k: float((lo + hi) / 2.0) for k, (lo, hi) in self._bounds.items()}
            o = {obj: float("nan") for obj in self._objectives}
            return p, o

        obj0 = self._objectives[0]
        y0 = self._context.y_by_objective[obj0]
        i = int(np.argmax(y0))
        x = self._context.X[i]
        params = {n: float(x[j]) for j, n in enumerate(self._context.param_names)}
        objectives = {obj: float(self._context.y_by_objective[obj][i]) for obj in self._objectives}
        return params, objectives

