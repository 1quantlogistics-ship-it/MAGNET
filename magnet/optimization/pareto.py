"""
optimization/pareto.py - Pareto front analysis.

BRAVO OWNS THIS FILE.

Module 13 v1.1 - Pareto front analysis and visualization data.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .schema import Solution, OptimizationProblem
from .enums import SelectionMethod


@dataclass
class ParetoMetrics:
    """Metrics for a Pareto front."""
    n_solutions: int = 0
    hypervolume: float = 0.0
    spread: float = 0.0
    spacing: float = 0.0

    # Objective ranges
    objective_mins: List[float] = field(default_factory=list)
    objective_maxs: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_solutions": self.n_solutions,
            "hypervolume": round(self.hypervolume, 6),
            "spread": round(self.spread, 6),
            "spacing": round(self.spacing, 6),
            "objective_mins": [round(v, 6) for v in self.objective_mins],
            "objective_maxs": [round(v, 6) for v in self.objective_maxs],
        }


class ParetoAnalyzer:
    """
    Analyzer for Pareto fronts.

    Provides metrics, selection methods, and data for visualization.
    """

    def __init__(self, problem: OptimizationProblem):
        """
        Initialize analyzer.

        Args:
            problem: Optimization problem definition
        """
        self.problem = problem

    def compute_metrics(self, pareto_front: List[Solution]) -> ParetoMetrics:
        """
        Compute metrics for a Pareto front.

        Args:
            pareto_front: List of Pareto optimal solutions

        Returns:
            ParetoMetrics with various quality indicators
        """
        metrics = ParetoMetrics()

        if not pareto_front:
            return metrics

        metrics.n_solutions = len(pareto_front)

        # Compute objective ranges
        n_obj = self.problem.n_obj
        for m in range(n_obj):
            values = [s.objectives[m] for s in pareto_front]
            metrics.objective_mins.append(min(values))
            metrics.objective_maxs.append(max(values))

        # Compute hypervolume (simplified 2D)
        if n_obj == 2:
            metrics.hypervolume = self._compute_2d_hypervolume(pareto_front)

        # Compute spread
        metrics.spread = self._compute_spread(pareto_front)

        # Compute spacing
        metrics.spacing = self._compute_spacing(pareto_front)

        return metrics

    def _compute_2d_hypervolume(
        self,
        front: List[Solution],
        ref_point: Optional[List[float]] = None,
    ) -> float:
        """
        Compute 2D hypervolume indicator.

        Args:
            front: Pareto front
            ref_point: Reference point (defaults to nadir + margin)
        """
        if not front or self.problem.n_obj != 2:
            return 0.0

        # Sort by first objective
        sorted_front = sorted(front, key=lambda s: s.objectives[0])

        # Use nadir point as reference if not provided
        if ref_point is None:
            max_obj0 = max(s.objectives[0] for s in front)
            max_obj1 = max(s.objectives[1] for s in front)
            ref_point = [max_obj0 * 1.1, max_obj1 * 1.1]

        # Compute area under staircase
        hypervolume = 0.0
        prev_obj0 = 0.0

        for sol in sorted_front:
            width = sol.objectives[0] - prev_obj0
            height = ref_point[1] - sol.objectives[1]
            if width > 0 and height > 0:
                hypervolume += width * height
            prev_obj0 = sol.objectives[0]

        # Final rectangle to reference point
        width = ref_point[0] - prev_obj0
        if width > 0 and sorted_front:
            height = ref_point[1] - sorted_front[-1].objectives[1]
            if height > 0:
                hypervolume += width * height

        return hypervolume

    def _compute_spread(self, front: List[Solution]) -> float:
        """
        Compute spread metric (diversity indicator).

        Higher spread indicates better distribution along Pareto front.
        """
        if len(front) < 2:
            return 0.0

        n_obj = self.problem.n_obj

        # Compute extent in each objective
        extents = []
        for m in range(n_obj):
            values = [s.objectives[m] for s in front]
            extent = max(values) - min(values)
            extents.append(extent)

        # Spread is Euclidean norm of extents
        spread = sum(e ** 2 for e in extents) ** 0.5
        return spread

    def _compute_spacing(self, front: List[Solution]) -> float:
        """
        Compute spacing metric (uniformity indicator).

        Lower spacing indicates more uniform distribution.
        """
        if len(front) < 2:
            return 0.0

        # Compute distances to nearest neighbor
        distances = []
        for i, sol in enumerate(front):
            min_dist = float('inf')
            for j, other in enumerate(front):
                if i != j:
                    dist = self._euclidean_distance(sol.objectives, other.objectives)
                    min_dist = min(min_dist, dist)
            if min_dist < float('inf'):
                distances.append(min_dist)

        if not distances:
            return 0.0

        # Mean distance
        mean_dist = sum(distances) / len(distances)

        # Standard deviation of distances
        variance = sum((d - mean_dist) ** 2 for d in distances) / len(distances)
        spacing = variance ** 0.5

        return spacing

    def _euclidean_distance(
        self, a: List[float], b: List[float]
    ) -> float:
        """Compute Euclidean distance between two points."""
        return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5

    def select_solution(
        self,
        pareto_front: List[Solution],
        method: SelectionMethod,
        weights: Optional[List[float]] = None,
    ) -> Optional[Solution]:
        """
        Select a solution from the Pareto front.

        Args:
            pareto_front: List of Pareto optimal solutions
            method: Selection method to use
            weights: Weights for weighted selection

        Returns:
            Selected solution or None if front is empty
        """
        if not pareto_front:
            return None

        if method == SelectionMethod.UTOPIA:
            return self._select_utopia(pareto_front)
        elif method == SelectionMethod.KNEE:
            return self._select_knee(pareto_front)
        elif method == SelectionMethod.WEIGHTED:
            return self._select_weighted(pareto_front, weights)
        else:
            return pareto_front[0]

    def _select_utopia(self, front: List[Solution]) -> Solution:
        """Select solution closest to utopia point."""
        n_obj = self.problem.n_obj

        # Utopia is minimum of each objective
        utopia = []
        for m in range(n_obj):
            utopia.append(min(s.objectives[m] for s in front))

        # Normalize
        ranges = []
        for m in range(n_obj):
            obj_min = min(s.objectives[m] for s in front)
            obj_max = max(s.objectives[m] for s in front)
            ranges.append(obj_max - obj_min if obj_max > obj_min else 1.0)

        def distance(sol):
            d = 0.0
            for m in range(n_obj):
                d += ((sol.objectives[m] - utopia[m]) / ranges[m]) ** 2
            return d ** 0.5

        return min(front, key=distance)

    def _select_knee(self, front: List[Solution]) -> Solution:
        """Select knee point (maximum curvature)."""
        if len(front) <= 2:
            return self._select_utopia(front)

        if self.problem.n_obj != 2:
            return self._select_utopia(front)

        # Sort by first objective
        sorted_front = sorted(front, key=lambda s: s.objectives[0])

        # Find maximum distance from line
        start = sorted_front[0].objectives
        end = sorted_front[-1].objectives

        max_dist = 0
        knee = sorted_front[0]

        for sol in sorted_front[1:-1]:
            dist = self._point_to_line_distance(sol.objectives, start, end)
            if dist > max_dist:
                max_dist = dist
                knee = sol

        return knee

    def _point_to_line_distance(
        self,
        point: List[float],
        line_start: List[float],
        line_end: List[float],
    ) -> float:
        """Calculate distance from point to line."""
        x0, y0 = point[0], point[1]
        x1, y1 = line_start[0], line_start[1]
        x2, y2 = line_end[0], line_end[1]

        num = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
        den = ((y2 - y1) ** 2 + (x2 - x1) ** 2) ** 0.5

        return num / den if den > 0 else 0.0

    def _select_weighted(
        self,
        front: List[Solution],
        weights: Optional[List[float]] = None,
    ) -> Solution:
        """Select using weighted sum."""
        n_obj = self.problem.n_obj

        if weights is None:
            weights = [1.0 / n_obj] * n_obj

        # Normalize objectives
        ranges = []
        mins = []
        for m in range(n_obj):
            obj_min = min(s.objectives[m] for s in front)
            obj_max = max(s.objectives[m] for s in front)
            mins.append(obj_min)
            ranges.append(obj_max - obj_min if obj_max > obj_min else 1.0)

        def weighted_sum(sol):
            total = 0.0
            for m in range(n_obj):
                normalized = (sol.objectives[m] - mins[m]) / ranges[m]
                total += weights[m] * normalized
            return total

        return min(front, key=weighted_sum)

    def get_visualization_data(
        self, pareto_front: List[Solution]
    ) -> Dict[str, Any]:
        """
        Get data formatted for visualization.

        Returns dict with:
        - points: List of objective value tuples
        - variable_names: Names of design variables
        - objective_names: Names of objectives
        - metrics: Pareto metrics
        """
        if not pareto_front:
            return {
                "points": [],
                "variable_names": [v.name for v in self.problem.variables],
                "objective_names": [o.name for o in self.problem.objectives],
                "metrics": ParetoMetrics().to_dict(),
            }

        points = []
        for sol in pareto_front:
            points.append({
                "objectives": sol.objectives,
                "variables": sol.variables,
                "is_feasible": sol.is_feasible,
            })

        metrics = self.compute_metrics(pareto_front)

        return {
            "points": points,
            "variable_names": [v.name for v in self.problem.variables],
            "objective_names": [o.name for o in self.problem.objectives],
            "metrics": metrics.to_dict(),
        }
