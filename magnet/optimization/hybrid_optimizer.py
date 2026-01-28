"""
magnet/optimization/hybrid_optimizer.py

TM.8 / TM.9 foundation: Hybrid Fidelity Control Plane.

Implements the user-facing "fidelity knob" with hard rules:
- Surrogates are a proposal engine only.
- The final returned design is always validated by the kernel (validator callable).
- "full" forces physics-only search/validation regardless of surrogate confidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Literal, Optional, Tuple

import numpy as np

from magnet.optimization.surrogate_model import SurrogateModel


OptimizationFidelity = Literal["fast", "hybrid", "full"]


@dataclass(frozen=True)
class OptimizationRequest:
    targets: Dict[str, float]
    fidelity: OptimizationFidelity = "hybrid"

    surrogate_candidates: int = 1000
    physics_validate_top_k: int = 10
    physics_refine_steps: int = 0

    return_detailed_report: bool = False
    explain: bool = True


@dataclass(frozen=True)
class OptimizationResult:
    design_id: str
    fidelity_used: OptimizationFidelity
    validated_by_kernel: bool
    score: float
    report: Optional[dict] = None


PhysicsEvalFn = Callable[[Dict[str, float], str], float]
KernelValidateFn = Callable[[Dict[str, float]], bool]


class HybridOptimizer:
    """
    Minimal hybrid optimizer control plane.

    - Physics evaluation is provided as a callable (objective name -> scalar).
    - Kernel validation is provided as a boolean predicate over params.
    """

    def __init__(
        self,
        *,
        parameter_bounds: Dict[str, Tuple[float, float]],
        physics_evaluate: PhysicsEvalFn,
        kernel_validate: KernelValidateFn,
        seed: int = 0,
    ) -> None:
        self._bounds = dict(parameter_bounds)
        self._names = list(self._bounds.keys())
        if not self._names:
            raise ValueError("parameter_bounds must be non-empty")
        self._physics_eval = physics_evaluate
        self._kernel_validate = kernel_validate
        self._rng = np.random.default_rng(int(seed))

    def optimize(self, request: OptimizationRequest) -> OptimizationResult:
        fid = str(request.fidelity)
        if fid not in ("fast", "hybrid", "full"):
            fid = "hybrid"

        if fid == "full":
            params, score, report = self._physics_only(request)
            validated = bool(self._kernel_validate(params))
            if request.return_detailed_report:
                report["validated_by_kernel"] = validated
            return OptimizationResult(
                design_id="",
                fidelity_used="full",
                validated_by_kernel=validated,
                score=float(score),
                report=report if request.return_detailed_report else None,
            )

        # fast/hybrid: surrogate proposes candidates, but we still kernel-validate final.
        params, score, report = self._surrogate_then_physics(request)
        validated = bool(self._kernel_validate(params))
        if request.return_detailed_report:
            report["validated_by_kernel"] = validated
        return OptimizationResult(
            design_id="",
            fidelity_used=fid,  # type: ignore
            validated_by_kernel=validated,
            score=float(score),
            report=report if request.return_detailed_report else None,
        )

    # -----------------------------
    # Internal strategies
    # -----------------------------

    def _score(self, params: Dict[str, float], targets: Dict[str, float]) -> float:
        # Score = -||residual||2 in objective space (pure numerical).
        r = []
        for obj, t in (targets or {}).items():
            v = float(self._physics_eval(params, str(obj)))
            r.append(float(t) - v)
        if not r:
            return 0.0
        return -float(np.linalg.norm(np.array(r, dtype=float)))

    def _sample(self, n: int) -> np.ndarray:
        X = np.zeros((int(n), len(self._names)), dtype=float)
        for j, name in enumerate(self._names):
            lo, hi = self._bounds[name]
            X[:, j] = self._rng.uniform(float(lo), float(hi), size=int(n))
        return X

    def _as_params(self, x: np.ndarray) -> Dict[str, float]:
        return {self._names[i]: float(x[i]) for i in range(len(self._names))}

    def _physics_only(self, request: OptimizationRequest) -> tuple[Dict[str, float], float, dict]:
        X = self._sample(max(1, int(request.surrogate_candidates)))
        best_params = self._as_params(X[0])
        best_score = -float("inf")

        for i in range(X.shape[0]):
            p = self._as_params(X[i])
            s = self._score(p, request.targets)
            if s > best_score:
                best_score = s
                best_params = p

        report = {
            "mode": "physics_only",
            "candidates_evaluated": int(X.shape[0]),
            "note": "full fidelity forces physics-only scoring; kernel validates final.",
        }
        return best_params, float(best_score), report

    def _surrogate_then_physics(self, request: OptimizationRequest) -> tuple[Dict[str, float], float, dict]:
        # Build a single surrogate for the score (pure scalar). Use a small physics bootstrap set.
        n_boot = min(32, max(4, int(request.physics_validate_top_k)))
        X_boot = self._sample(n_boot)
        y_boot = np.array([self._score(self._as_params(X_boot[i]), request.targets) for i in range(n_boot)], dtype=float)

        model = SurrogateModel(parameter_names=list(self._names), objective_name="score")
        model.fit(X_boot, y_boot)

        # Score many candidates cheaply with surrogate mean.
        Xc = self._sample(max(1, int(request.surrogate_candidates)))
        mean, std = model.predict(Xc)
        mean = np.asarray(mean, dtype=float).reshape(-1)
        std = np.asarray(std, dtype=float).reshape(-1)

        # Select top-K by predicted mean (no heuristics).
        k = max(1, int(request.physics_validate_top_k))
        top_idx = np.argsort(mean)[-k:][::-1]

        best_params = self._as_params(Xc[int(top_idx[0])])
        best_score = -float("inf")
        best_std = float(std[int(top_idx[0])])

        physics_evals = 0
        for i in top_idx:
            p = self._as_params(Xc[int(i)])
            s = self._score(p, request.targets)
            physics_evals += 1
            if s > best_score:
                best_score = s
                best_params = p
                best_std = float(std[int(i)])

        report = {
            "mode": "surrogate_then_physics",
            "surrogate_candidates": int(Xc.shape[0]),
            "physics_validations": int(physics_evals),
            "surrogate_uncertainty_std": float(best_std),
            "note": "fast/hybrid proposes via surrogate, but kernel validates final.",
        }
        return best_params, float(best_score), report

