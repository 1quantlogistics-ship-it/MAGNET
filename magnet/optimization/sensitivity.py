"""
optimization/sensitivity.py - Sensitivity analysis.

BRAVO OWNS THIS FILE.

Module 13 v1.1 - Design sensitivity analysis.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .schema import OptimizationProblem, Solution

if TYPE_CHECKING:
    from ..core.state_manager import StateManager


@dataclass
class VariableSensitivity:
    """Sensitivity of objectives to a design variable."""
    variable_name: str
    state_path: str

    # Sensitivity to each objective (partial derivative estimate)
    sensitivities: Dict[str, float] = field(default_factory=dict)

    # Relative importance (normalized)
    importance: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variable_name": self.variable_name,
            "state_path": self.state_path,
            "sensitivities": {k: round(v, 6) for k, v in self.sensitivities.items()},
            "importance": round(self.importance, 4),
        }


@dataclass
class SensitivityResult:
    """Complete sensitivity analysis result."""
    base_solution: Optional[Solution] = None
    variable_sensitivities: List[VariableSensitivity] = field(default_factory=list)
    perturbation_size: float = 0.01

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_solution": self.base_solution.to_dict() if self.base_solution else None,
            "variable_sensitivities": [v.to_dict() for v in self.variable_sensitivities],
            "perturbation_size": self.perturbation_size,
        }


class SensitivityAnalyzer:
    """
    Analyzer for design sensitivity.

    Computes how sensitive objectives are to changes in design variables.
    """

    def __init__(
        self,
        problem: OptimizationProblem,
        base_state: "StateManager",
        validators: Optional[List[Any]] = None,
    ):
        """
        Initialize analyzer.

        Args:
            problem: Optimization problem definition
            base_state: Base state manager for evaluations
            validators: List of validators to run during evaluation
        """
        self.problem = problem
        self.base_state = base_state
        self.validators = validators or []

    def analyze(
        self,
        solution: Solution,
        perturbation_size: float = 0.01,
    ) -> SensitivityResult:
        """
        Perform sensitivity analysis around a solution.

        Uses finite difference to estimate partial derivatives.

        Args:
            solution: Base solution to analyze
            perturbation_size: Relative perturbation size (0.01 = 1%)

        Returns:
            SensitivityResult with sensitivities for each variable
        """
        result = SensitivityResult(
            base_solution=solution,
            perturbation_size=perturbation_size,
        )

        # Get base objectives
        base_objectives = solution.objectives

        # Analyze each variable
        for i, var in enumerate(self.problem.variables):
            sensitivity = VariableSensitivity(
                variable_name=var.name,
                state_path=var.state_path,
            )

            # Compute perturbation
            delta = (var.upper_bound - var.lower_bound) * perturbation_size

            # Perturb up
            perturbed_vars = solution.variables.copy()
            perturbed_vars[i] = var.clamp(solution.variables[i] + delta)

            obj_plus = self._evaluate_objectives(perturbed_vars)

            # Perturb down
            perturbed_vars = solution.variables.copy()
            perturbed_vars[i] = var.clamp(solution.variables[i] - delta)

            obj_minus = self._evaluate_objectives(perturbed_vars)

            # Central difference for each objective
            for j, obj in enumerate(self.problem.objectives):
                if obj_plus and obj_minus:
                    deriv = (obj_plus[j] - obj_minus[j]) / (2 * delta)
                    sensitivity.sensitivities[obj.name] = deriv
                else:
                    sensitivity.sensitivities[obj.name] = 0.0

            result.variable_sensitivities.append(sensitivity)

        # Compute relative importance
        self._compute_importance(result)

        return result

    def _evaluate_objectives(
        self, variables: List[float]
    ) -> Optional[List[float]]:
        """Evaluate objectives for given variable values."""
        try:
            # Create state copy
            if hasattr(self.base_state, 'clone'):
                state = self.base_state.clone()
            else:
                state = self.base_state

            # Apply variables - Hole #7 Fix: Use .set() with proper source
            source = "optimization/sensitivity"
            for i, var in enumerate(self.problem.variables):
                state.set(var.state_path, variables[i], source)

            # Run validators
            for validator in self.validators:
                try:
                    validator.validate(state, {})
                except Exception:
                    return None

            # Evaluate objectives
            objectives = []
            for obj in self.problem.objectives:
                value = obj.evaluate(state)
                objectives.append(value)

            return objectives

        except Exception:
            return None

    def _compute_importance(self, result: SensitivityResult) -> None:
        """Compute relative importance of each variable."""
        if not result.variable_sensitivities:
            return

        # Sum of absolute sensitivities for each variable
        totals = []
        for vs in result.variable_sensitivities:
            total = sum(abs(s) for s in vs.sensitivities.values())
            totals.append(total)

        # Normalize
        max_total = max(totals) if totals else 1.0
        if max_total > 0:
            for i, vs in enumerate(result.variable_sensitivities):
                vs.importance = totals[i] / max_total

    def analyze_local_region(
        self,
        solution: Solution,
        n_samples: int = 20,
        region_size: float = 0.1,
    ) -> Dict[str, Any]:
        """
        Analyze local region around a solution.

        Samples the region and computes statistics.

        Args:
            solution: Center solution
            n_samples: Number of samples
            region_size: Size of region relative to bounds

        Returns:
            Dict with local region statistics
        """
        import random

        samples = []

        for _ in range(n_samples):
            # Generate random point in region
            vars_sample = []
            for i, var in enumerate(self.problem.variables):
                delta = (var.upper_bound - var.lower_bound) * region_size
                value = solution.variables[i] + random.uniform(-delta, delta)
                value = var.clamp(value)
                vars_sample.append(value)

            objectives = self._evaluate_objectives(vars_sample)
            if objectives:
                samples.append({
                    "variables": vars_sample,
                    "objectives": objectives,
                })

        if not samples:
            return {"error": "No valid samples"}

        # Compute statistics
        n_obj = self.problem.n_obj
        obj_means = [0.0] * n_obj
        obj_mins = [float('inf')] * n_obj
        obj_maxs = [float('-inf')] * n_obj

        for sample in samples:
            for j in range(n_obj):
                obj_means[j] += sample["objectives"][j]
                obj_mins[j] = min(obj_mins[j], sample["objectives"][j])
                obj_maxs[j] = max(obj_maxs[j], sample["objectives"][j])

        for j in range(n_obj):
            obj_means[j] /= len(samples)

        return {
            "n_samples": len(samples),
            "region_size": region_size,
            "objective_means": [round(v, 6) for v in obj_means],
            "objective_mins": [round(v, 6) for v in obj_mins],
            "objective_maxs": [round(v, 6) for v in obj_maxs],
            "objective_ranges": [
                round(obj_maxs[j] - obj_mins[j], 6) for j in range(n_obj)
            ],
        }

    def get_tradeoff_curve(
        self,
        solution: Solution,
        variable_index: int,
        n_points: int = 20,
    ) -> Dict[str, Any]:
        """
        Get trade-off curve varying one variable.

        Args:
            solution: Base solution
            variable_index: Index of variable to vary
            n_points: Number of points on curve

        Returns:
            Dict with curve data
        """
        var = self.problem.variables[variable_index]

        curve_points = []
        for i in range(n_points):
            # Interpolate between bounds
            t = i / (n_points - 1)
            value = var.lower_bound + t * (var.upper_bound - var.lower_bound)

            # Create perturbed solution
            vars_perturbed = solution.variables.copy()
            vars_perturbed[variable_index] = value

            objectives = self._evaluate_objectives(vars_perturbed)
            if objectives:
                curve_points.append({
                    "variable_value": round(value, 6),
                    "objectives": [round(o, 6) for o in objectives],
                })

        return {
            "variable_name": var.name,
            "variable_index": variable_index,
            "n_points": len(curve_points),
            "curve": curve_points,
        }
