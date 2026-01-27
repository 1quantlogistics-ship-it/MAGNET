"""
magnet/optimization/benchmarks.py

TM.10: Performance Benchmarks + Budgets

This module is intentionally lightweight and does not run in CI by default.
It provides a small benchmarking harness to compare:
- surrogate-assisted optimization (fast/hybrid)
- physics-only scoring/validation loops

Goal: establish and document local performance budgets (time per iteration,
physics evaluations consumed, etc.) without changing core behavior.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


PhysicsEvalFn = Callable[[Dict[str, float], str], float]
KernelValidateFn = Callable[[Dict[str, float]], bool]


@dataclass(frozen=True)
class BenchmarkConfig:
    seed: int = 0
    n_candidates: int = 1000
    validate_top_k: int = 10
    n_trials: int = 3


@dataclass(frozen=True)
class BenchmarkResult:
    name: str
    seconds: float
    physics_evals: int
    best_score: float


def _sample_uniform(
    *,
    rng: np.random.Generator,
    bounds: Dict[str, Tuple[float, float]],
    n: int,
) -> np.ndarray:
    names = list(bounds.keys())
    X = np.zeros((int(n), len(names)), dtype=float)
    for j, name in enumerate(names):
        lo, hi = bounds[name]
        X[:, j] = rng.uniform(float(lo), float(hi), size=int(n))
    return X


def _as_params(names: Sequence[str], x: np.ndarray) -> Dict[str, float]:
    return {str(names[i]): float(x[i]) for i in range(len(names))}


def run_physics_only_random_search(
    *,
    parameter_bounds: Dict[str, Tuple[float, float]],
    targets: Dict[str, float],
    physics_evaluate: PhysicsEvalFn,
    kernel_validate: KernelValidateFn,
    config: BenchmarkConfig = BenchmarkConfig(),
) -> BenchmarkResult:
    """
    Baseline: physics-only scoring on random candidates.

    This is NOT meant to be a strong optimizer, only a measurable baseline.
    """
    rng = np.random.default_rng(int(config.seed))
    names = list(parameter_bounds.keys())
    X = _sample_uniform(rng=rng, bounds=parameter_bounds, n=int(config.n_candidates))

    physics_evals = 0
    best_score = -float("inf")

    def score(params: Dict[str, float]) -> float:
        nonlocal physics_evals
        r = []
        for obj, t in targets.items():
            v = float(physics_evaluate(params, str(obj)))
            physics_evals += 1
            r.append(float(t) - v)
        return -float(np.linalg.norm(np.asarray(r, dtype=float))) if r else 0.0

    t0 = time.time()
    for i in range(X.shape[0]):
        p = _as_params(names, X[i])
        if not kernel_validate(p):
            continue
        s = score(p)
        if s > best_score:
            best_score = s
    dt = float(time.time() - t0)

    return BenchmarkResult(
        name="physics_only_random_search",
        seconds=dt,
        physics_evals=int(physics_evals),
        best_score=float(best_score),
    )


def run_hybrid_optimizer_benchmark(
    *,
    parameter_bounds: Dict[str, Tuple[float, float]],
    targets: Dict[str, float],
    physics_evaluate: PhysicsEvalFn,
    kernel_validate: KernelValidateFn,
    config: BenchmarkConfig = BenchmarkConfig(),
) -> BenchmarkResult:
    """
    Benchmark the HybridOptimizer control plane.

    Import is local to avoid making this module a hard dependency.
    """
    from magnet.optimization.hybrid_optimizer import HybridOptimizer, OptimizationRequest

    opt = HybridOptimizer(
        parameter_bounds=parameter_bounds,
        physics_evaluate=physics_evaluate,
        kernel_validate=kernel_validate,
        seed=int(config.seed),
    )

    t0 = time.time()
    res = opt.optimize(
        OptimizationRequest(
            targets=dict(targets),
            fidelity="hybrid",
            surrogate_candidates=int(config.n_candidates),
            physics_validate_top_k=int(config.validate_top_k),
            return_detailed_report=True,
        )
    )
    dt = float(time.time() - t0)
    report = res.report or {}
    physics_evals = int(report.get("physics_validations", 0))
    return BenchmarkResult(
        name="hybrid_optimizer",
        seconds=dt,
        physics_evals=physics_evals,
        best_score=float(res.score),
    )


def run_benchmarks(
    *,
    parameter_bounds: Dict[str, Tuple[float, float]],
    targets: Dict[str, float],
    physics_evaluate: PhysicsEvalFn,
    kernel_validate: KernelValidateFn,
    config: BenchmarkConfig = BenchmarkConfig(),
) -> List[BenchmarkResult]:
    """
    Run both baselines a few times and return results.

    Intended usage (manual):
    - wire a cheap physics_evaluate + kernel_validate
    - run locally, record times and physics budget consumption
    """
    results: List[BenchmarkResult] = []
    for trial in range(int(config.n_trials)):
        cfg = BenchmarkConfig(
            seed=int(config.seed) + trial,
            n_candidates=int(config.n_candidates),
            validate_top_k=int(config.validate_top_k),
            n_trials=1,
        )
        results.append(
            run_physics_only_random_search(
                parameter_bounds=parameter_bounds,
                targets=targets,
                physics_evaluate=physics_evaluate,
                kernel_validate=kernel_validate,
                config=cfg,
            )
        )
        results.append(
            run_hybrid_optimizer_benchmark(
                parameter_bounds=parameter_bounds,
                targets=targets,
                physics_evaluate=physics_evaluate,
                kernel_validate=kernel_validate,
                config=cfg,
            )
        )
    return results

