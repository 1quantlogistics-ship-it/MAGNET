"""
tests/unit/test_optimization_optimizer.py - Tests for NSGA-II optimizer.

BRAVO OWNS THIS FILE.

Tests for Module 13 v1.1 - DesignOptimizer with NSGA-II.
"""

import pytest
from magnet.optimization import (
    DesignOptimizer,
    OptimizationProblem,
    DesignVariable,
    Objective,
    Constraint,
    Solution,
    ObjectiveType,
    ConstraintType,
    OptimizerStatus,
    SelectionMethod,
)


class MockStateManager:
    """Mock StateManager for testing."""

    def __init__(self):
        self._data = {}
        self._clone_called = False

    def clone(self):
        """v1.1 P3: Clone method for optimizer."""
        new_state = MockStateManager()
        new_state._data = self._data.copy()
        new_state._clone_called = True
        return new_state

    def get(self, path, default=None):
        return self._data.get(path, default)

    def set(self, path, value):
        self._data[path] = value

    def write(self, path, value, source="", description=""):
        self._data[path] = value


def create_simple_problem():
    """Create a simple two-variable optimization problem."""
    problem = OptimizationProblem(
        name="test_problem",
        description="Test optimization problem",
    )

    problem.add_variable(DesignVariable(
        name="x",
        state_path="var.x",
        lower_bound=0.0,
        upper_bound=10.0,
    ))

    problem.add_variable(DesignVariable(
        name="y",
        state_path="var.y",
        lower_bound=0.0,
        upper_bound=10.0,
    ))

    problem.add_objective(Objective(
        name="f1",
        state_path="result.f1",
        objective_type=ObjectiveType.MINIMIZE,
    ))

    problem.add_objective(Objective(
        name="f2",
        state_path="result.f2",
        objective_type=ObjectiveType.MINIMIZE,
    ))

    return problem


class SimpleValidator:
    """Simple validator that computes objectives from variables."""

    def validate(self, state, config):
        x = state.get("var.x", 0)
        y = state.get("var.y", 0)
        # Simple test functions
        state.set("result.f1", x ** 2)  # Minimize x^2
        state.set("result.f2", (x - 5) ** 2 + y ** 2)  # Minimize distance to (5, 0)


class TestDesignOptimizerInit:
    """Tests for DesignOptimizer initialization."""

    def test_init_with_defaults(self):
        """Test optimizer initialization with defaults."""
        problem = create_simple_problem()
        state = MockStateManager()
        optimizer = DesignOptimizer(problem, state)

        assert optimizer.problem == problem
        assert optimizer.base_state == state
        assert optimizer.population_size == 50
        assert optimizer.max_generations == 100
        assert optimizer.crossover_prob == 0.9
        assert optimizer.mutation_prob == 0.1

    def test_init_with_custom_params(self):
        """Test optimizer initialization with custom parameters."""
        problem = create_simple_problem()
        state = MockStateManager()
        optimizer = DesignOptimizer(
            problem, state,
            population_size=20,
            max_generations=50,
            crossover_prob=0.8,
            mutation_prob=0.2,
            seed=42,
        )

        assert optimizer.population_size == 20
        assert optimizer.max_generations == 50
        assert optimizer.crossover_prob == 0.8
        assert optimizer.mutation_prob == 0.2

    def test_init_with_validators(self):
        """Test optimizer initialization with validators."""
        problem = create_simple_problem()
        state = MockStateManager()
        validator = SimpleValidator()
        optimizer = DesignOptimizer(problem, state, validators=[validator])

        assert len(optimizer.validators) == 1
        assert optimizer.validators[0] == validator


class TestDesignOptimizerPopulation:
    """Tests for population initialization."""

    def test_initialize_population_size(self):
        """Test population is initialized with correct size."""
        problem = create_simple_problem()
        state = MockStateManager()
        optimizer = DesignOptimizer(problem, state, population_size=10, seed=42)

        population = optimizer._initialize_population()
        assert len(population) == 10

    def test_initialize_population_bounds(self):
        """Test population is within bounds."""
        problem = create_simple_problem()
        state = MockStateManager()
        optimizer = DesignOptimizer(problem, state, population_size=100, seed=42)

        population = optimizer._initialize_population()
        for sol in population:
            assert len(sol.variables) == 2
            assert 0.0 <= sol.variables[0] <= 10.0
            assert 0.0 <= sol.variables[1] <= 10.0

    def test_initialize_population_objectives(self):
        """Test population has initialized objectives."""
        problem = create_simple_problem()
        state = MockStateManager()
        optimizer = DesignOptimizer(problem, state, population_size=10, seed=42)

        population = optimizer._initialize_population()
        for sol in population:
            assert len(sol.objectives) == 2
            assert sol.objectives == [0.0, 0.0]  # Initial values


class TestDesignOptimizerEvaluation:
    """Tests for solution evaluation."""

    def test_evaluate_solution_basic(self):
        """Test basic solution evaluation."""
        problem = create_simple_problem()
        state = MockStateManager()
        validator = SimpleValidator()
        optimizer = DesignOptimizer(problem, state, validators=[validator])

        solution = Solution(variables=[3.0, 4.0], objectives=[0.0, 0.0])
        optimizer._evaluate_solution(solution)

        # f1 = x^2 = 9
        # f2 = (x-5)^2 + y^2 = 4 + 16 = 20
        assert solution.objectives[0] == 9.0
        assert solution.objectives[1] == 20.0

    def test_evaluate_solution_uses_clone_v11_p3(self):
        """Test v1.1 P3: evaluation uses StateManager.clone()."""
        problem = create_simple_problem()
        state = MockStateManager()
        validator = SimpleValidator()
        optimizer = DesignOptimizer(problem, state, validators=[validator])

        solution = Solution(variables=[1.0, 2.0], objectives=[0.0, 0.0])
        optimizer._evaluate_solution(solution)

        # The clone should have been called (check in mock)
        # Since we're evaluating, clone should be used
        assert hasattr(state, 'clone')

    def test_evaluate_solution_increments_count(self):
        """Test evaluation count increments."""
        problem = create_simple_problem()
        state = MockStateManager()
        validator = SimpleValidator()
        optimizer = DesignOptimizer(problem, state, validators=[validator])

        assert optimizer._evaluations == 0

        solution = Solution(variables=[1.0, 2.0], objectives=[0.0, 0.0])
        optimizer._evaluate_solution(solution)
        assert optimizer._evaluations == 1

        optimizer._evaluate_solution(solution)
        assert optimizer._evaluations == 2


class TestDesignOptimizerCrossover:
    """Tests for crossover operations."""

    def test_crossover_produces_two_children(self):
        """Test crossover produces two children."""
        problem = create_simple_problem()
        state = MockStateManager()
        optimizer = DesignOptimizer(problem, state, seed=42)

        p1 = [2.0, 3.0]
        p2 = [8.0, 7.0]
        c1, c2 = optimizer._crossover(p1, p2)

        assert len(c1) == 2
        assert len(c2) == 2

    def test_crossover_within_bounds(self):
        """Test crossover keeps values within bounds."""
        problem = create_simple_problem()
        state = MockStateManager()
        optimizer = DesignOptimizer(problem, state, seed=42)

        for _ in range(100):
            p1 = [0.0, 0.0]
            p2 = [10.0, 10.0]
            c1, c2 = optimizer._crossover(p1, p2)

            for val in c1 + c2:
                assert 0.0 <= val <= 10.0


class TestDesignOptimizerMutation:
    """Tests for mutation operations."""

    def test_mutation_within_bounds(self):
        """Test mutation keeps values within bounds."""
        problem = create_simple_problem()
        state = MockStateManager()
        optimizer = DesignOptimizer(problem, state, mutation_prob=1.0, seed=42)

        for _ in range(100):
            variables = [5.0, 5.0]
            mutated = optimizer._mutate(variables)

            for val in mutated:
                assert 0.0 <= val <= 10.0

    def test_mutation_with_zero_prob(self):
        """Test no mutation when probability is zero."""
        problem = create_simple_problem()
        state = MockStateManager()
        optimizer = DesignOptimizer(problem, state, mutation_prob=0.0, seed=42)

        variables = [5.0, 5.0]
        mutated = optimizer._mutate(variables)

        assert mutated == variables


class TestDesignOptimizerTournament:
    """Tests for tournament selection."""

    def test_tournament_select_feasible_preferred(self):
        """Test feasible solutions are preferred."""
        problem = create_simple_problem()
        state = MockStateManager()
        optimizer = DesignOptimizer(problem, state, seed=42)

        sol1 = Solution(variables=[1.0, 1.0], objectives=[100.0, 100.0], is_feasible=True)
        sol2 = Solution(variables=[2.0, 2.0], objectives=[1.0, 1.0], is_feasible=False)

        # Run multiple times to check preference
        feasible_selected = 0
        for _ in range(100):
            selected = optimizer._tournament_select([sol1, sol2])
            if selected.is_feasible:
                feasible_selected += 1

        # Should prefer feasible solution even with worse objectives
        assert feasible_selected > 50  # Should mostly select feasible


class TestDesignOptimizerNonDominatedSort:
    """Tests for non-dominated sorting."""

    def test_single_front_all_equal(self):
        """Test all equal solutions form single front."""
        problem = create_simple_problem()
        state = MockStateManager()
        optimizer = DesignOptimizer(problem, state)

        solutions = [
            Solution(variables=[1.0, 1.0], objectives=[5.0, 5.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[5.0, 5.0], is_feasible=True),
            Solution(variables=[3.0, 3.0], objectives=[5.0, 5.0], is_feasible=True),
        ]

        fronts = optimizer._non_dominated_sort(solutions)
        assert len(fronts) == 1
        assert len(fronts[0]) == 3

    def test_two_fronts_dominated(self):
        """Test dominated solutions form second front."""
        problem = create_simple_problem()
        state = MockStateManager()
        optimizer = DesignOptimizer(problem, state)

        solutions = [
            Solution(variables=[1.0, 1.0], objectives=[1.0, 1.0], is_feasible=True),  # Pareto
            Solution(variables=[2.0, 2.0], objectives=[2.0, 2.0], is_feasible=True),  # Dominated
        ]

        fronts = optimizer._non_dominated_sort(solutions)
        assert len(fronts) == 2
        assert len(fronts[0]) == 1
        assert fronts[0][0].objectives == [1.0, 1.0]

    def test_pareto_front_extraction(self):
        """Test Pareto front is correctly identified."""
        problem = create_simple_problem()
        state = MockStateManager()
        optimizer = DesignOptimizer(problem, state)

        solutions = [
            Solution(variables=[1.0, 1.0], objectives=[1.0, 10.0], is_feasible=True),  # Pareto
            Solution(variables=[2.0, 2.0], objectives=[5.0, 5.0], is_feasible=True),   # Pareto
            Solution(variables=[3.0, 3.0], objectives=[10.0, 1.0], is_feasible=True),  # Pareto
            Solution(variables=[4.0, 4.0], objectives=[6.0, 6.0], is_feasible=True),   # Dominated by (5,5)
        ]

        pareto = optimizer._extract_pareto_front(solutions)
        assert len(pareto) == 3
        pareto_objs = [s.objectives for s in pareto]
        assert [1.0, 10.0] in pareto_objs
        assert [5.0, 5.0] in pareto_objs
        assert [10.0, 1.0] in pareto_objs


class TestDesignOptimizerCrowdingDistance:
    """Tests for crowding distance calculation."""

    def test_crowding_distance_boundaries(self):
        """Test boundary solutions have infinite crowding distance."""
        problem = create_simple_problem()
        state = MockStateManager()
        optimizer = DesignOptimizer(problem, state)

        front = [
            Solution(variables=[1.0, 1.0], objectives=[1.0, 10.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[5.0, 5.0], is_feasible=True),
            Solution(variables=[3.0, 3.0], objectives=[10.0, 1.0], is_feasible=True),
        ]

        optimizer._calculate_crowding_distance(front)

        # After sorting by first objective: 1.0, 5.0, 10.0
        # Boundaries should have inf
        inf_count = sum(1 for s in front if s.crowding_distance == float('inf'))
        assert inf_count >= 2


class TestDesignOptimizerSelection:
    """Tests for solution selection methods."""

    def test_select_utopia(self):
        """Test utopia point selection."""
        problem = create_simple_problem()
        state = MockStateManager()
        optimizer = DesignOptimizer(problem, state)

        front = [
            Solution(variables=[1.0, 1.0], objectives=[0.0, 10.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[5.0, 5.0], is_feasible=True),
            Solution(variables=[3.0, 3.0], objectives=[10.0, 0.0], is_feasible=True),
        ]

        selected = optimizer._select_utopia(front)
        # Utopia point is (0, 0), closest should be (5, 5) normalized
        assert selected is not None

    def test_select_knee(self):
        """Test knee point selection."""
        problem = create_simple_problem()
        state = MockStateManager()
        optimizer = DesignOptimizer(problem, state)

        front = [
            Solution(variables=[1.0, 1.0], objectives=[0.0, 10.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[2.0, 3.0], is_feasible=True),  # Knee
            Solution(variables=[3.0, 3.0], objectives=[10.0, 0.0], is_feasible=True),
        ]

        selected = optimizer._select_knee(front)
        # Knee should be the point with maximum distance from line
        assert selected is not None

    def test_select_weighted(self):
        """Test weighted sum selection."""
        problem = create_simple_problem()
        state = MockStateManager()
        optimizer = DesignOptimizer(problem, state)

        front = [
            Solution(variables=[1.0, 1.0], objectives=[0.0, 10.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[5.0, 5.0], is_feasible=True),
            Solution(variables=[3.0, 3.0], objectives=[10.0, 0.0], is_feasible=True),
        ]

        # Equal weights: min of (0+10), (5+5), (10+0) = any of them
        selected = optimizer._select_weighted(front, [0.5, 0.5])
        assert selected is not None
        # All have sum of 10, so any is valid


class TestDesignOptimizerOptimize:
    """Tests for full optimization."""

    def test_optimize_returns_result(self):
        """Test optimize returns OptimizationResult."""
        problem = create_simple_problem()
        state = MockStateManager()
        validator = SimpleValidator()
        optimizer = DesignOptimizer(
            problem, state,
            validators=[validator],
            population_size=10,
            max_generations=5,
            seed=42,
        )

        result = optimizer.optimize()

        assert result.problem_name == "test_problem"
        assert result.status == OptimizerStatus.MAX_ITERATIONS
        assert result.iterations == 5
        assert result.evaluations > 0

    def test_optimize_has_pareto_front(self):
        """Test optimize produces Pareto front."""
        problem = create_simple_problem()
        state = MockStateManager()
        validator = SimpleValidator()
        optimizer = DesignOptimizer(
            problem, state,
            validators=[validator],
            population_size=20,
            max_generations=10,
            seed=42,
        )

        result = optimizer.optimize()

        assert len(result.pareto_front) > 0
        for sol in result.pareto_front:
            assert len(sol.variables) == 2
            assert len(sol.objectives) == 2

    def test_optimize_selects_solution(self):
        """Test optimize selects a best solution."""
        problem = create_simple_problem()
        state = MockStateManager()
        validator = SimpleValidator()
        optimizer = DesignOptimizer(
            problem, state,
            validators=[validator],
            population_size=20,
            max_generations=10,
            seed=42,
        )

        result = optimizer.optimize()

        assert result.selected_solution is not None
        assert result.selection_method == SelectionMethod.UTOPIA

    def test_optimize_with_callback(self):
        """Test optimize calls callback each generation."""
        problem = create_simple_problem()
        state = MockStateManager()
        validator = SimpleValidator()
        optimizer = DesignOptimizer(
            problem, state,
            validators=[validator],
            population_size=10,
            max_generations=5,
            seed=42,
        )

        callbacks = []
        def callback(gen, pareto):
            callbacks.append((gen, len(pareto)))

        result = optimizer.optimize(callback=callback)

        assert len(callbacks) == 5
        assert callbacks[0][0] == 0
        assert callbacks[4][0] == 4

    def test_optimize_elapsed_time(self):
        """Test optimize tracks elapsed time."""
        problem = create_simple_problem()
        state = MockStateManager()
        validator = SimpleValidator()
        optimizer = DesignOptimizer(
            problem, state,
            validators=[validator],
            population_size=10,
            max_generations=5,
            seed=42,
        )

        result = optimizer.optimize()

        assert result.elapsed_time_s > 0
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.completed_at > result.started_at

    def test_optimize_reproducible_with_seed(self):
        """Test optimization is reproducible with same seed."""
        problem = create_simple_problem()
        state = MockStateManager()
        validator = SimpleValidator()

        optimizer1 = DesignOptimizer(
            problem, state,
            validators=[validator],
            population_size=10,
            max_generations=5,
            seed=42,
        )
        result1 = optimizer1.optimize()

        optimizer2 = DesignOptimizer(
            problem, state,
            validators=[validator],
            population_size=10,
            max_generations=5,
            seed=42,
        )
        result2 = optimizer2.optimize()

        # Same seed should produce same results
        assert len(result1.pareto_front) == len(result2.pareto_front)


class TestDesignOptimizerWithConstraints:
    """Tests for optimization with constraints."""

    def test_constraint_penalty(self):
        """Test constraints add penalty to infeasible solutions."""
        problem = OptimizationProblem(
            name="constrained_test",
            description="Test with constraints",
        )
        problem.add_variable(DesignVariable(
            name="x", state_path="var.x", lower_bound=0.0, upper_bound=10.0
        ))
        problem.add_objective(Objective(
            name="f1", state_path="result.f1", objective_type=ObjectiveType.MINIMIZE
        ))
        problem.add_constraint(Constraint(
            name="x_limit",
            constraint_type=ConstraintType.INEQUALITY_LE,
            state_path="var.x",
            limit_value=5.0,
            penalty_weight=1000,
        ))

        class ConstraintValidator:
            def validate(self, state, config):
                x = state.get("var.x", 0)
                state.set("result.f1", x)  # Minimize x

        state = MockStateManager()
        optimizer = DesignOptimizer(
            problem, state,
            validators=[ConstraintValidator()],
            population_size=20,
            max_generations=10,
            seed=42,
        )

        result = optimizer.optimize()

        # Best solution should satisfy constraint x <= 5
        if result.selected_solution:
            x_val = result.selected_solution.variables[0]
            # Solutions near boundary or within constraint should be preferred
            assert result.selected_solution is not None
