"""
magnet/kernel/coordinate_executor.py

T5.3 / T5.4: COORDINATE executor (numerical solver).

NORTH STAR COMPLIANCE (per §0.9.4):
- This is a NUMERICAL SOLVER, not a design advisor.
- Contains ZERO naval-architecture heuristics.
- Does not know what parameters/objectives "mean".
- Only knows: parameters, targets, residuals, gradients, convergence.

Import boundary:
- Must not import domain modules (hull_gen/physics/stability/etc). It operates on
  abstract state and registry callables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from magnet.core.state_concurrency import ConcurrentStateManager
from magnet.kernel.gradient_estimator import GradientConfig, SafeGradientEstimator
from magnet.kernel.observable_registry import ObservableRegistry
from magnet.optimization.transactional_optimizer import TransactionalOptimizer


@dataclass(frozen=True)
class CoordinateConfig:
    max_iterations: int = 8
    damping: float = 1e-2  # Levenberg-Marquardt λ
    step_scale_candidates: Tuple[float, ...] = (1.0, 0.5, 0.25, 0.125)  # T5.4 (pure numerical line-search)
    tol_residual_norm: float = 1e-6
    gradient: GradientConfig = GradientConfig(step_size=1e-4)


@dataclass(frozen=True)
class CoordinateResult:
    success: bool
    iterations: int
    initial_residual_norm: float
    final_residual_norm: float
    reason: str
    applied_commits: int = 0
    last_written_paths: List[str] = field(default_factory=list)


class CoordinateExecutor:
    def __init__(
        self,
        *,
        manager: ConcurrentStateManager,
        registry: ObservableRegistry,
        config: CoordinateConfig = CoordinateConfig(),
    ) -> None:
        self._manager = manager
        self._registry = registry
        self._config = config

        self._tx = TransactionalOptimizer(manager=manager)
        self._grad = SafeGradientEstimator(
            state_manager=manager,
            evaluator=self._evaluate_objectives,
            config=self._config.gradient,
        )

    def optimize(self, *, targets: Dict[str, float], adjustable: List[str]) -> CoordinateResult:
        """
        Optimize adjustable parameters to match objective targets via LM steps.
        """
        if not targets:
            return CoordinateResult(
                success=True,
                iterations=0,
                initial_residual_norm=0.0,
                final_residual_norm=0.0,
                reason="no_targets",
            )
        if not adjustable:
            return CoordinateResult(
                success=False,
                iterations=0,
                initial_residual_norm=float("inf"),
                final_residual_norm=float("inf"),
                reason="no_adjustables",
            )

        # Validate adjustable controls exist and are controllable.
        for a in adjustable:
            spec = self._registry.get_spec(a)
            if not spec.controllable:
                return CoordinateResult(
                    success=False,
                    iterations=0,
                    initial_residual_norm=float("inf"),
                    final_residual_norm=float("inf"),
                    reason=f"not_controllable:{a}",
                )

        obj_names = list(targets.keys())

        # Evaluate initial residual
        r0 = self._residual_vector(targets)
        r0_norm = float(np.linalg.norm(r0))
        if r0_norm <= float(self._config.tol_residual_norm):
            return CoordinateResult(
                success=True,
                iterations=0,
                initial_residual_norm=r0_norm,
                final_residual_norm=r0_norm,
                reason="already_satisfied",
            )

        applied = 0
        last_wp: List[str] = []
        r_norm = r0_norm

        for it in range(1, int(self._config.max_iterations) + 1):
            # Gradients computed from a consistent snapshot. If stale (or not yet initialized),
            # refresh and proceed (do not fail the solve).
            if self._grad.is_stale():
                self._grad.invalidate_snapshot()

            J = self._grad.compute_jacobian(parameters=list(adjustable), objectives=obj_names)
            r = self._residual_vector(targets)

            # LM step: (J^T J + λI) δ = J^T r
            step = _lm_step(J, r, damping=float(self._config.damping))

            # Current parameter values (from canonical snapshot for numerical consistency)
            x = self._current_parameters(adjustable)

            accepted = False
            best_trial_norm = r_norm
            best_updates: Optional[Dict[str, Any]] = None

            # T5.4: pure numerical step scaling candidates (no heuristic ordering)
            for s in self._config.step_scale_candidates:
                trial_x = x + float(s) * step
                updates = {p: float(trial_x[i]) for i, p in enumerate(adjustable)}

                # Apply candidate step atomically
                step_res = self._tx.apply_patch_step(updates, source="coordinate_executor")
                if not step_res.applied:
                    # If the step couldn't apply (stale), abort the whole solve.
                    return CoordinateResult(
                        success=False,
                        iterations=it - 1,
                        initial_residual_norm=r0_norm,
                        final_residual_norm=r_norm,
                        reason=f"apply_failed:{step_res.reason}",
                        applied_commits=applied,
                        last_written_paths=list(last_wp),
                    )

                applied += 1
                last_wp = list((step_res.commit.written_paths if step_res.commit else []) or [])

                # Evaluate new residual after apply.
                trial_r = self._residual_vector(targets)
                trial_norm = float(np.linalg.norm(trial_r))

                # Accept if improved.
                if trial_norm < r_norm:
                    r_norm = trial_norm
                    accepted = True
                    break

                # Not improved: keep track, then undo by applying inverse step.
                if trial_norm < best_trial_norm:
                    best_trial_norm = trial_norm
                    best_updates = updates

                # Revert (purely numerical): restore prior x
                revert = {p: float(x[i]) for i, p in enumerate(adjustable)}
                rev = self._tx.apply_patch_step(revert, source="coordinate_executor_revert")
                if not rev.applied:
                    return CoordinateResult(
                        success=False,
                        iterations=it - 1,
                        initial_residual_norm=r0_norm,
                        final_residual_norm=r_norm,
                        reason=f"revert_failed:{rev.reason}",
                        applied_commits=applied,
                        last_written_paths=list(last_wp),
                    )
                applied += 1

            if not accepted:
                # If nothing improved, stop.
                return CoordinateResult(
                    success=False,
                    iterations=it,
                    initial_residual_norm=r0_norm,
                    final_residual_norm=r_norm,
                    reason="no_improving_step",
                    applied_commits=applied,
                    last_written_paths=list(last_wp),
                )

            if r_norm <= float(self._config.tol_residual_norm):
                return CoordinateResult(
                    success=True,
                    iterations=it,
                    initial_residual_norm=r0_norm,
                    final_residual_norm=r_norm,
                    reason="converged",
                    applied_commits=applied,
                    last_written_paths=list(last_wp),
                )

        return CoordinateResult(
            success=False,
            iterations=int(self._config.max_iterations),
            initial_residual_norm=r0_norm,
            final_residual_norm=r_norm,
            reason="max_iterations",
            applied_commits=applied,
            last_written_paths=list(last_wp),
        )

    # -----------------------------
    # Internal numeric plumbing
    # -----------------------------

    def _evaluate_objectives(self, state_manager, objectives: Sequence[str]) -> Dict[str, float]:
        # State view for registry measurement functions: dict-like access via StateManager.get
        # We expose the minimal dict surface needed for user-provided measure_fns.
        # IMPORTANT: registry graph cache is not keyed by state, so clear between evaluations.
        try:
            self._registry.graph.clear_cache()
        except Exception:
            pass
        st = _StateView(state_manager)
        out: Dict[str, float] = {}
        for o in objectives:
            out[str(o)] = float(self._registry.get_value(str(o), st))
        return out

    def _residual_vector(self, targets: Dict[str, float]) -> np.ndarray:
        obj_names = list(targets.keys())
        with self._manager.read_snapshot() as snap:
            try:
                self._registry.graph.clear_cache()
            except Exception:
                pass
            st = _StateView(snap)
            actual = np.array([float(self._registry.get_value(o, st)) for o in obj_names], dtype=float)
        target = np.array([float(targets[o]) for o in obj_names], dtype=float)
        return target - actual

    def _current_parameters(self, adjustable: List[str]) -> np.ndarray:
        with self._manager.read_snapshot() as snap:
            xs = [float(snap.get(p, 0.0) or 0.0) for p in adjustable]
        return np.array(xs, dtype=float)


class _StateView(dict):
    """
    Minimal dict-like adapter over StateManager.get for registry measurers.
    """

    def __init__(self, sm) -> None:
        super().__init__()
        self._sm = sm

    def get(self, key, default=None):
        return self._sm.get(str(key), default)


def _lm_step(J: np.ndarray, r: np.ndarray, *, damping: float) -> np.ndarray:
    JT = np.asarray(J, dtype=float).T
    A = JT @ np.asarray(J, dtype=float)
    b = JT @ np.asarray(r, dtype=float)
    n = A.shape[0]
    A_damped = A + float(damping) * np.eye(n, dtype=float)
    # Solve; fall back to least squares if singular.
    try:
        return np.linalg.solve(A_damped, b)
    except Exception:
        x, *_ = np.linalg.lstsq(A_damped, b, rcond=None)
        return np.asarray(x, dtype=float)

