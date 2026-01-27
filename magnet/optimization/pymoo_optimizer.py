"""
magnet/optimization/pymoo_optimizer.py

Phase 2 (Optimization): optional pymoo-backed optimizer.

This is an adapter that allows MAGNET's existing OptimizationProblem/schema to be
solved using pymoo algorithms (e.g. NSGA2) when pymoo is installed.

North Star / kernel contract:
- Optimizer operates on cloned state; kernel/validators "judge" feasibility.
- No design intent is introduced here; this is purely numeric search.
- Graceful degradation: if pymoo is unavailable, importing this module is safe.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, List, Optional, TYPE_CHECKING

import logging

from .enums import OptimizerStatus, SelectionMethod
from .schema import OptimizationProblem, OptimizationResult, Solution

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger(__name__)


_PYMOO_AVAILABLE = False
try:
    import numpy as np  # type: ignore

    from pymoo.core.problem import Problem  # type: ignore
    from pymoo.algorithms.moo.nsga2 import NSGA2  # type: ignore
    from pymoo.optimize import minimize  # type: ignore

    _PYMOO_AVAILABLE = True
except Exception:
    np = None  # type: ignore
    Problem = object  # type: ignore
    NSGA2 = None  # type: ignore
    minimize = None  # type: ignore
    _PYMOO_AVAILABLE = False


@dataclass(frozen=True)
class PymooSettings:
    population_size: int = 50
    max_generations: int = 100
    seed: Optional[int] = None


class _MagnetPymooProblem(Problem):  # type: ignore[misc]
    """
    Bridge MAGNET OptimizationProblem -> pymoo Problem.
    """

    def __init__(
        self,
        *,
        problem: OptimizationProblem,
        base_state: "StateManager",
        validators: List[Any],
    ):
        self._problem = problem
        self._base_state = base_state
        self._validators = list(validators or [])

        xl = [float(v.lower_bound) for v in problem.variables]
        xu = [float(v.upper_bound) for v in problem.variables]

        super().__init__(
            n_var=int(problem.n_var),
            n_obj=int(problem.n_obj),
            n_ieq_constr=int(problem.n_constr),
            xl=xl,
            xu=xu,
        )

    def _evaluate(self, X, out, *args, **kwargs):  # noqa: N802
        # X: (n, n_var)
        F = []
        G = []

        for row in X:
            sol = self._evaluate_one(list(row))
            F.append(sol.objectives)
            # pymoo expects G <= 0. We use violation (0 satisfied, >0 violated).
            if self._problem.n_constr > 0:
                G.append([float(sol.constraint_violation)])
            else:
                G.append([])

        out["F"] = np.asarray(F, dtype=float)
        if self._problem.n_constr > 0:
            out["G"] = np.asarray(G, dtype=float)

    def _evaluate_one(self, variables: List[float]) -> Solution:
        # Create state copy using clone() method when available
        if hasattr(self._base_state, "clone"):
            state = self._base_state.clone()
        else:
            state = self._base_state

        opened_txn = False
        try:
            if hasattr(state, "begin_transaction") and getattr(state, "_current_txn", None) is None:
                state.begin_transaction()
                opened_txn = True
        except Exception:
            opened_txn = False

        # Apply design variables
        source = "optimization/pymoo"
        for i, var in enumerate(self._problem.variables):
            state.set(var.state_path, float(variables[i]), source)

        # Run validators
        try:
            for validator in self._validators:
                try:
                    validator.validate(state, {})
                except Exception:
                    return Solution(
                        variables=[float(x) for x in variables],
                        objectives=[1e10] * self._problem.n_obj,
                        constraint_violation=1e10,
                        is_feasible=False,
                    )

            # Evaluate objectives (MAGNET Objective.evaluate already normalizes MAXIMIZE -> MINIMIZE)
            objectives = [float(obj.evaluate(state)) for obj in self._problem.objectives]

            # Constraints: compute total violation for compatibility with existing schema
            total_violation = 0.0
            for constr in self._problem.constraints:
                v = float(constr.evaluate(state))
                total_violation += v * float(constr.penalty_weight)

            return Solution(
                variables=[float(x) for x in variables],
                objectives=objectives,
                constraint_violation=float(total_violation),
                is_feasible=bool(total_violation == 0.0),
            )
        finally:
            if opened_txn and hasattr(state, "rollback"):
                try:
                    state.rollback()
                except Exception:
                    pass


class PymooDesignOptimizer:
    """
    Multi-objective design optimizer using pymoo.

    If pymoo is not installed, construct/optimize will raise ImportError.
    """

    def __init__(
        self,
        *,
        problem: OptimizationProblem,
        base_state: "StateManager",
        validators: Optional[List[Any]] = None,
        settings: Optional[PymooSettings] = None,
    ):
        if not _PYMOO_AVAILABLE:
            raise ImportError("pymoo is not installed (install `pymoo` to enable this backend)")

        self.problem = problem
        self.base_state = base_state
        self.validators = validators or []
        self.settings = settings or PymooSettings()

    def optimize(self) -> OptimizationResult:
        result = OptimizationResult(
            problem_name=self.problem.name,
            status=OptimizerStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )

        try:
            algo = NSGA2(pop_size=int(self.settings.population_size))
            prob = _MagnetPymooProblem(
                problem=self.problem,
                base_state=self.base_state,
                validators=self.validators,
            )

            res = minimize(
                prob,
                algo,
                ("n_gen", int(self.settings.max_generations)),
                seed=self.settings.seed,
                verbose=False,
            )

            X = getattr(res, "X", None)
            F = getattr(res, "F", None)
            if X is None or F is None:
                # Defensive: treat as empty result
                result.status = OptimizerStatus.FAILED
                return result

            pareto_front: List[Solution] = []
            for x, f in zip(np.asarray(X), np.asarray(F)):
                pareto_front.append(
                    Solution(
                        variables=[float(v) for v in list(x)],
                        objectives=[float(o) for o in list(f)],
                        constraint_violation=0.0,
                        is_feasible=True,
                    )
                )

            result.pareto_front = pareto_front
            # Best-effort stats from pymoo algorithm
            try:
                result.evaluations = int(getattr(res.algorithm.evaluator, "n_eval", 0) or 0)
            except Exception:
                result.evaluations = 0
            try:
                result.iterations = int(getattr(res.algorithm, "n_gen", 0) or 0)
            except Exception:
                result.iterations = 0

            result.status = OptimizerStatus.MAX_ITERATIONS

            if result.pareto_front:
                # Use same default selection semantics as the native optimizer
                from .pareto import ParetoAnalyzer

                analyzer = ParetoAnalyzer(self.problem)
                result.selected_solution = analyzer.select_solution(
                    result.pareto_front, SelectionMethod.UTOPIA
                )
                result.selection_method = SelectionMethod.UTOPIA

        except Exception as e:
            logger.debug(f"pymoo optimize failed: {e}")
            result.status = OptimizerStatus.FAILED

        result.completed_at = datetime.now(timezone.utc)
        return result

