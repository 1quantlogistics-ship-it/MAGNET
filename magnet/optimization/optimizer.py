"""
optimization/optimizer.py - Design optimizer with NSGA-II.

BRAVO OWNS THIS FILE.

Module 13 v1.1 - Design optimizer implementation.

v1.1 PATCH P3: Uses StateManager.clone() NOT copy.deepcopy
"""

from __future__ import annotations
import random
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

from .enums import OptimizerStatus, SelectionMethod
from .schema import (
    OptimizationProblem,
    OptimizationResult,
    Solution,
)

if TYPE_CHECKING:
    from ..core.state_manager import StateManager


class DesignOptimizer:
    """
    Multi-objective design optimizer using NSGA-II algorithm.

    v1.1 PATCH P3: Uses StateManager.clone() for proper state copying.
    """

    def __init__(
        self,
        problem: OptimizationProblem,
        base_state: "StateManager",
        validators: Optional[List[Any]] = None,
        population_size: int = 50,
        max_generations: int = 100,
        crossover_prob: float = 0.9,
        mutation_prob: float = 0.1,
        seed: Optional[int] = None,
    ):
        """
        Initialize optimizer.

        Args:
            problem: Optimization problem definition
            base_state: Base state manager to clone for evaluations
            validators: List of validators to run during evaluation
            population_size: Size of population
            max_generations: Maximum number of generations
            crossover_prob: Crossover probability
            mutation_prob: Mutation probability
            seed: Random seed for reproducibility
        """
        self.problem = problem
        self.base_state = base_state
        self.validators = validators or []
        self.population_size = population_size
        self.max_generations = max_generations
        self.crossover_prob = crossover_prob
        self.mutation_prob = mutation_prob

        if seed is not None:
            random.seed(seed)

        self._evaluations = 0
        self._result = None

    def optimize(
        self,
        callback: Optional[Callable[[int, List[Solution]], None]] = None,
    ) -> OptimizationResult:
        """
        Run optimization.

        Args:
            callback: Optional callback(generation, pareto_front) called each generation

        Returns:
            OptimizationResult with Pareto front and statistics
        """
        result = OptimizationResult(
            problem_name=self.problem.name,
            status=OptimizerStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )

        self._evaluations = 0
        start_time = time.time()

        try:
            # Initialize population
            population = self._initialize_population()

            # Evaluate initial population
            for sol in population:
                self._evaluate_solution(sol)

            # Main NSGA-II loop
            for gen in range(self.max_generations):
                # Create offspring
                offspring = self._create_offspring(population)

                # Evaluate offspring
                for sol in offspring:
                    self._evaluate_solution(sol)

                # Combine and select
                combined = population + offspring
                population = self._select_population(combined)

                # Extract Pareto front
                pareto = self._extract_pareto_front(population)
                result.pareto_front = pareto
                result.iterations = gen + 1

                # Callback
                if callback:
                    callback(gen, pareto)

                # Check convergence (simple: if Pareto front is stable)
                # For now, just run all generations

            result.status = OptimizerStatus.MAX_ITERATIONS

        except Exception as e:
            result.status = OptimizerStatus.FAILED
            # Log error but don't crash
            pass

        # Finalize
        result.evaluations = self._evaluations
        result.elapsed_time_s = time.time() - start_time
        result.completed_at = datetime.now(timezone.utc)

        # Select best solution
        if result.pareto_front:
            result.selected_solution = self._select_best(
                result.pareto_front,
                SelectionMethod.UTOPIA
            )
            result.selection_method = SelectionMethod.UTOPIA

        self._result = result
        return result

    def _initialize_population(self) -> List[Solution]:
        """Initialize random population within bounds."""
        population = []

        for _ in range(self.population_size):
            variables = []
            for var in self.problem.variables:
                value = random.uniform(var.lower_bound, var.upper_bound)
                variables.append(value)

            sol = Solution(
                variables=variables,
                objectives=[0.0] * self.problem.n_obj,
            )
            population.append(sol)

        return population

    def _evaluate_solution(self, solution: Solution) -> None:
        """
        Evaluate a solution.

        v1.1 PATCH P3: Uses StateManager.clone() for proper deep copy.
        """
        self._evaluations += 1

        try:
            # Create state copy using clone() method (P3 FIX)
            if hasattr(self.base_state, 'clone'):
                state = self.base_state.clone()
            else:
                # Fallback for testing with mock
                state = self.base_state

            # Apply design variables
            for i, var in enumerate(self.problem.variables):
                value = solution.variables[i]
                if hasattr(state, 'write'):
                    state.write(var.state_path, value, "optimizer", "Design variable")
                elif hasattr(state, 'set'):
                    state.set(var.state_path, value)

            # Run validators
            for validator in self.validators:
                try:
                    validator.validate(state, {})
                except Exception:
                    # Penalty for validation failure
                    solution.objectives = [1e10] * self.problem.n_obj
                    solution.constraint_violation = 1e10
                    solution.is_feasible = False
                    return

            # Evaluate objectives
            objectives = []
            for obj in self.problem.objectives:
                value = obj.evaluate(state)
                objectives.append(value)
            solution.objectives = objectives

            # Evaluate constraints
            total_violation = 0.0
            for constr in self.problem.constraints:
                violation = constr.evaluate(state)
                total_violation += violation * constr.penalty_weight

            solution.constraint_violation = total_violation
            solution.is_feasible = total_violation == 0

        except Exception:
            # Penalty for evaluation failure
            solution.objectives = [1e10] * self.problem.n_obj
            solution.constraint_violation = 1e10
            solution.is_feasible = False

    def _create_offspring(self, population: List[Solution]) -> List[Solution]:
        """Create offspring through crossover and mutation."""
        offspring = []

        while len(offspring) < self.population_size:
            # Tournament selection
            parent1 = self._tournament_select(population)
            parent2 = self._tournament_select(population)

            # Crossover
            if random.random() < self.crossover_prob:
                child1_vars, child2_vars = self._crossover(
                    parent1.variables, parent2.variables
                )
            else:
                child1_vars = parent1.variables.copy()
                child2_vars = parent2.variables.copy()

            # Mutation
            child1_vars = self._mutate(child1_vars)
            child2_vars = self._mutate(child2_vars)

            offspring.append(Solution(
                variables=child1_vars,
                objectives=[0.0] * self.problem.n_obj,
            ))
            offspring.append(Solution(
                variables=child2_vars,
                objectives=[0.0] * self.problem.n_obj,
            ))

        return offspring[:self.population_size]

    def _tournament_select(
        self, population: List[Solution], k: int = 2
    ) -> Solution:
        """Tournament selection."""
        candidates = random.sample(population, min(k, len(population)))
        # Prefer feasible solutions, then by crowding distance would be added
        feasible = [c for c in candidates if c.is_feasible]
        if feasible:
            return min(feasible, key=lambda s: sum(s.objectives))
        return min(candidates, key=lambda s: s.constraint_violation)

    def _crossover(
        self, p1: List[float], p2: List[float]
    ) -> Tuple[List[float], List[float]]:
        """Simulated binary crossover (SBX)."""
        eta = 20.0  # Distribution index
        child1, child2 = [], []

        for i, var in enumerate(self.problem.variables):
            if random.random() < 0.5:
                # Perform crossover
                u = random.random()
                if u <= 0.5:
                    beta = (2 * u) ** (1 / (eta + 1))
                else:
                    beta = (1 / (2 * (1 - u))) ** (1 / (eta + 1))

                c1 = 0.5 * ((1 + beta) * p1[i] + (1 - beta) * p2[i])
                c2 = 0.5 * ((1 - beta) * p1[i] + (1 + beta) * p2[i])

                # Clamp to bounds
                c1 = var.clamp(c1)
                c2 = var.clamp(c2)

                child1.append(c1)
                child2.append(c2)
            else:
                child1.append(p1[i])
                child2.append(p2[i])

        return child1, child2

    def _mutate(self, variables: List[float]) -> List[float]:
        """Polynomial mutation."""
        eta = 20.0  # Distribution index
        mutated = []

        for i, var in enumerate(self.problem.variables):
            if random.random() < self.mutation_prob:
                delta_max = var.upper_bound - var.lower_bound
                u = random.random()

                if u < 0.5:
                    delta = (2 * u) ** (1 / (eta + 1)) - 1
                else:
                    delta = 1 - (2 * (1 - u)) ** (1 / (eta + 1))

                value = variables[i] + delta * delta_max
                value = var.clamp(value)
                mutated.append(value)
            else:
                mutated.append(variables[i])

        return mutated

    def _select_population(
        self, combined: List[Solution]
    ) -> List[Solution]:
        """Select next generation using non-dominated sorting."""
        # Non-dominated sorting
        fronts = self._non_dominated_sort(combined)

        selected = []
        for front in fronts:
            if len(selected) + len(front) <= self.population_size:
                selected.extend(front)
            else:
                # Need to select subset from this front
                remaining = self.population_size - len(selected)
                # Sort by crowding distance
                self._calculate_crowding_distance(front)
                front.sort(key=lambda s: getattr(s, 'crowding_distance', 0), reverse=True)
                selected.extend(front[:remaining])
                break

        return selected

    def _non_dominated_sort(
        self, population: List[Solution]
    ) -> List[List[Solution]]:
        """Non-dominated sorting."""
        fronts: List[List[Solution]] = [[]]

        # For each solution, find dominated solutions and domination count
        for p in population:
            p._dominated_by = []
            p._dominates = []
            p._dom_count = 0

        for i, p in enumerate(population):
            for j, q in enumerate(population):
                if i == j:
                    continue
                if p.dominates(q):
                    p._dominates.append(q)
                elif q.dominates(p):
                    p._dom_count += 1

            if p._dom_count == 0:
                p._rank = 0
                fronts[0].append(p)

        # If all solutions are non-dominated, return them in single front
        if not fronts[0]:
            # When no solution dominates another (all equal), put all in front 0
            for p in population:
                p._rank = 0
            fronts[0] = population[:]
            return fronts

        # Build subsequent fronts
        current_front = 0
        while current_front < len(fronts) and fronts[current_front]:
            next_front = []
            for p in fronts[current_front]:
                for q in p._dominates:
                    q._dom_count -= 1
                    if q._dom_count == 0:
                        q._rank = current_front + 1
                        next_front.append(q)
            current_front += 1
            if next_front:
                fronts.append(next_front)

        return [f for f in fronts if f]

    def _calculate_crowding_distance(self, front: List[Solution]) -> None:
        """Calculate crowding distance for solutions in a front."""
        n = len(front)
        if n == 0:
            return

        for sol in front:
            sol.crowding_distance = 0.0

        for m in range(self.problem.n_obj):
            front.sort(key=lambda s: s.objectives[m])

            # Boundary solutions have infinite distance
            front[0].crowding_distance = float('inf')
            front[-1].crowding_distance = float('inf')

            # Calculate range
            obj_range = front[-1].objectives[m] - front[0].objectives[m]
            if obj_range == 0:
                continue

            # Calculate distances
            for i in range(1, n - 1):
                front[i].crowding_distance += (
                    (front[i + 1].objectives[m] - front[i - 1].objectives[m])
                    / obj_range
                )

    def _extract_pareto_front(
        self, population: List[Solution]
    ) -> List[Solution]:
        """Extract Pareto optimal solutions."""
        fronts = self._non_dominated_sort(population)
        if fronts:
            return fronts[0]
        return []

    def _select_best(
        self,
        pareto_front: List[Solution],
        method: SelectionMethod,
    ) -> Solution:
        """Select best solution from Pareto front."""
        if not pareto_front:
            return None

        if method == SelectionMethod.UTOPIA:
            return self._select_utopia(pareto_front)
        elif method == SelectionMethod.KNEE:
            return self._select_knee(pareto_front)
        elif method == SelectionMethod.WEIGHTED:
            return self._select_weighted(pareto_front)
        else:
            return pareto_front[0]

    def _select_utopia(self, front: List[Solution]) -> Solution:
        """Select solution closest to utopia point."""
        # Utopia is minimum of each objective
        utopia = []
        for m in range(self.problem.n_obj):
            utopia.append(min(s.objectives[m] for s in front))

        # Find closest to utopia (normalized)
        ranges = []
        for m in range(self.problem.n_obj):
            obj_min = min(s.objectives[m] for s in front)
            obj_max = max(s.objectives[m] for s in front)
            ranges.append(obj_max - obj_min if obj_max > obj_min else 1.0)

        def distance(sol):
            d = 0.0
            for m in range(self.problem.n_obj):
                d += ((sol.objectives[m] - utopia[m]) / ranges[m]) ** 2
            return d ** 0.5

        return min(front, key=distance)

    def _select_knee(self, front: List[Solution]) -> Solution:
        """Select knee point (maximum curvature)."""
        if len(front) <= 2:
            return self._select_utopia(front)

        # Sort by first objective
        sorted_front = sorted(front, key=lambda s: s.objectives[0])

        # Find maximum distance from line connecting endpoints
        start = sorted_front[0].objectives
        end = sorted_front[-1].objectives

        max_dist = 0
        knee = sorted_front[0]

        for sol in sorted_front[1:-1]:
            # Distance from point to line
            dist = self._point_line_distance(sol.objectives, start, end)
            if dist > max_dist:
                max_dist = dist
                knee = sol

        return knee

    def _point_line_distance(
        self, point: List[float], line_start: List[float], line_end: List[float]
    ) -> float:
        """Calculate distance from point to line in objective space."""
        # Simple 2D case
        if len(point) == 2:
            x0, y0 = point
            x1, y1 = line_start
            x2, y2 = line_end

            num = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
            den = ((y2 - y1) ** 2 + (x2 - x1) ** 2) ** 0.5

            return num / den if den > 0 else 0

        # Multi-dimensional: use projection
        return 0.0

    def _select_weighted(
        self, front: List[Solution], weights: Optional[List[float]] = None
    ) -> Solution:
        """Select using weighted sum."""
        if weights is None:
            weights = [1.0 / self.problem.n_obj] * self.problem.n_obj

        def weighted_sum(sol):
            return sum(w * o for w, o in zip(weights, sol.objectives))

        return min(front, key=weighted_sum)
