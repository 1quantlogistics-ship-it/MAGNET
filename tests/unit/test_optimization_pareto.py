"""
tests/unit/test_optimization_pareto.py - Tests for Pareto front analysis.

BRAVO OWNS THIS FILE.

Tests for Module 13 v1.1 - ParetoAnalyzer and ParetoMetrics.
"""

import pytest
from magnet.optimization import (
    ParetoAnalyzer,
    ParetoMetrics,
    OptimizationProblem,
    DesignVariable,
    Objective,
    Solution,
    ObjectiveType,
    SelectionMethod,
)


def create_two_objective_problem():
    """Create a simple two-objective problem for testing."""
    problem = OptimizationProblem(
        name="test_problem",
        description="Test two-objective problem",
    )

    problem.add_variable(DesignVariable(
        name="x", state_path="var.x", lower_bound=0.0, upper_bound=10.0,
    ))
    problem.add_variable(DesignVariable(
        name="y", state_path="var.y", lower_bound=0.0, upper_bound=10.0,
    ))

    problem.add_objective(Objective(
        name="f1", state_path="result.f1", objective_type=ObjectiveType.MINIMIZE,
    ))
    problem.add_objective(Objective(
        name="f2", state_path="result.f2", objective_type=ObjectiveType.MINIMIZE,
    ))

    return problem


class TestParetoMetrics:
    """Tests for ParetoMetrics dataclass."""

    def test_default_values(self):
        """Test default values."""
        metrics = ParetoMetrics()
        assert metrics.n_solutions == 0
        assert metrics.hypervolume == 0.0
        assert metrics.spread == 0.0
        assert metrics.spacing == 0.0
        assert metrics.objective_mins == []
        assert metrics.objective_maxs == []

    def test_to_dict(self):
        """Test dictionary serialization."""
        metrics = ParetoMetrics(
            n_solutions=5,
            hypervolume=100.123456789,
            spread=10.987654321,
            spacing=1.111111111,
            objective_mins=[0.1, 0.2],
            objective_maxs=[10.3, 20.4],
        )
        data = metrics.to_dict()

        assert data["n_solutions"] == 5
        assert data["hypervolume"] == 100.123457  # Rounded to 6 decimal places
        assert data["spread"] == 10.987654
        assert data["spacing"] == 1.111111
        assert data["objective_mins"] == [0.1, 0.2]
        assert data["objective_maxs"] == [10.3, 20.4]


class TestParetoAnalyzerInit:
    """Tests for ParetoAnalyzer initialization."""

    def test_init_with_problem(self):
        """Test analyzer initialization."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)
        assert analyzer.problem == problem


class TestParetoAnalyzerMetrics:
    """Tests for metrics computation."""

    def test_compute_metrics_empty_front(self):
        """Test metrics computation for empty front."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        metrics = analyzer.compute_metrics([])

        assert metrics.n_solutions == 0
        assert metrics.hypervolume == 0.0
        assert metrics.spread == 0.0
        assert metrics.spacing == 0.0

    def test_compute_metrics_single_solution(self):
        """Test metrics computation for single solution."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        front = [Solution(variables=[1.0, 2.0], objectives=[5.0, 10.0], is_feasible=True)]
        metrics = analyzer.compute_metrics(front)

        assert metrics.n_solutions == 1
        assert metrics.objective_mins == [5.0, 10.0]
        assert metrics.objective_maxs == [5.0, 10.0]
        assert metrics.spread == 0.0
        assert metrics.spacing == 0.0

    def test_compute_metrics_multiple_solutions(self):
        """Test metrics computation for multiple solutions."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        front = [
            Solution(variables=[1.0, 1.0], objectives=[1.0, 10.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[5.0, 5.0], is_feasible=True),
            Solution(variables=[3.0, 3.0], objectives=[10.0, 1.0], is_feasible=True),
        ]
        metrics = analyzer.compute_metrics(front)

        assert metrics.n_solutions == 3
        assert metrics.objective_mins == [1.0, 1.0]
        assert metrics.objective_maxs == [10.0, 10.0]
        assert metrics.spread > 0
        assert metrics.hypervolume > 0

    def test_compute_metrics_objective_ranges(self):
        """Test objective range computation."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        front = [
            Solution(variables=[1.0, 1.0], objectives=[0.0, 100.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[50.0, 50.0], is_feasible=True),
            Solution(variables=[3.0, 3.0], objectives=[100.0, 0.0], is_feasible=True),
        ]
        metrics = analyzer.compute_metrics(front)

        assert metrics.objective_mins[0] == 0.0
        assert metrics.objective_maxs[0] == 100.0
        assert metrics.objective_mins[1] == 0.0
        assert metrics.objective_maxs[1] == 100.0


class TestParetoAnalyzerHypervolume:
    """Tests for hypervolume computation."""

    def test_hypervolume_two_solutions(self):
        """Test hypervolume with two solutions."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        front = [
            Solution(variables=[1.0, 1.0], objectives=[0.0, 10.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[10.0, 0.0], is_feasible=True),
        ]

        hypervolume = analyzer._compute_2d_hypervolume(front)
        assert hypervolume > 0

    def test_hypervolume_single_solution(self):
        """Test hypervolume with single solution."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        front = [Solution(variables=[1.0, 1.0], objectives=[5.0, 5.0], is_feasible=True)]

        hypervolume = analyzer._compute_2d_hypervolume(front)
        # Single point should still have hypervolume to reference point
        assert hypervolume >= 0

    def test_hypervolume_custom_reference(self):
        """Test hypervolume with custom reference point."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        front = [
            Solution(variables=[1.0, 1.0], objectives=[0.0, 5.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[5.0, 0.0], is_feasible=True),
        ]

        hv1 = analyzer._compute_2d_hypervolume(front, ref_point=[10.0, 10.0])
        hv2 = analyzer._compute_2d_hypervolume(front, ref_point=[100.0, 100.0])

        # Larger reference point should give larger hypervolume
        assert hv2 > hv1


class TestParetoAnalyzerSpread:
    """Tests for spread computation."""

    def test_spread_single_solution(self):
        """Test spread with single solution is zero."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        front = [Solution(variables=[1.0, 1.0], objectives=[5.0, 5.0], is_feasible=True)]
        spread = analyzer._compute_spread(front)

        assert spread == 0.0

    def test_spread_two_solutions(self):
        """Test spread with two solutions."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        front = [
            Solution(variables=[1.0, 1.0], objectives=[0.0, 10.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[10.0, 0.0], is_feasible=True),
        ]
        spread = analyzer._compute_spread(front)

        # Spread should be sqrt(10^2 + 10^2) = sqrt(200) ~ 14.14
        assert abs(spread - 14.142135) < 0.001

    def test_spread_increases_with_diversity(self):
        """Test spread increases with more diverse front."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        front_narrow = [
            Solution(variables=[1.0, 1.0], objectives=[4.0, 6.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[6.0, 4.0], is_feasible=True),
        ]

        front_wide = [
            Solution(variables=[1.0, 1.0], objectives=[0.0, 10.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[10.0, 0.0], is_feasible=True),
        ]

        spread_narrow = analyzer._compute_spread(front_narrow)
        spread_wide = analyzer._compute_spread(front_wide)

        assert spread_wide > spread_narrow


class TestParetoAnalyzerSpacing:
    """Tests for spacing computation."""

    def test_spacing_single_solution(self):
        """Test spacing with single solution is zero."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        front = [Solution(variables=[1.0, 1.0], objectives=[5.0, 5.0], is_feasible=True)]
        spacing = analyzer._compute_spacing(front)

        assert spacing == 0.0

    def test_spacing_uniform_distribution(self):
        """Test spacing for uniformly distributed front."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        # Uniformly distributed solutions
        front = [
            Solution(variables=[1.0, 1.0], objectives=[0.0, 10.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[5.0, 5.0], is_feasible=True),
            Solution(variables=[3.0, 3.0], objectives=[10.0, 0.0], is_feasible=True),
        ]
        spacing = analyzer._compute_spacing(front)

        # Low spacing indicates uniform distribution
        assert spacing >= 0

    def test_spacing_non_uniform_distribution(self):
        """Test spacing for non-uniformly distributed front."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        # Non-uniform distribution (two solutions close, one far)
        front = [
            Solution(variables=[1.0, 1.0], objectives=[0.0, 10.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[0.5, 9.5], is_feasible=True),  # Close to first
            Solution(variables=[3.0, 3.0], objectives=[10.0, 0.0], is_feasible=True),  # Far from others
        ]
        spacing = analyzer._compute_spacing(front)

        # Higher spacing indicates non-uniform distribution
        assert spacing >= 0


class TestParetoAnalyzerEuclideanDistance:
    """Tests for Euclidean distance helper."""

    def test_euclidean_distance_same_point(self):
        """Test distance to same point is zero."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        dist = analyzer._euclidean_distance([1.0, 2.0], [1.0, 2.0])
        assert dist == 0.0

    def test_euclidean_distance_horizontal(self):
        """Test horizontal distance."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        dist = analyzer._euclidean_distance([0.0, 0.0], [3.0, 0.0])
        assert dist == 3.0

    def test_euclidean_distance_diagonal(self):
        """Test diagonal distance (3-4-5 triangle)."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        dist = analyzer._euclidean_distance([0.0, 0.0], [3.0, 4.0])
        assert dist == 5.0


class TestParetoAnalyzerSelection:
    """Tests for solution selection methods."""

    def test_select_solution_empty_front(self):
        """Test selection from empty front returns None."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        selected = analyzer.select_solution([], SelectionMethod.UTOPIA)
        assert selected is None

    def test_select_utopia(self):
        """Test utopia selection."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        front = [
            Solution(variables=[1.0, 1.0], objectives=[0.0, 10.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[5.0, 5.0], is_feasible=True),
            Solution(variables=[3.0, 3.0], objectives=[10.0, 0.0], is_feasible=True),
        ]

        selected = analyzer.select_solution(front, SelectionMethod.UTOPIA)

        assert selected is not None
        # Utopia is (0, 0), closest normalized should be (5, 5)
        assert selected.objectives == [5.0, 5.0]

    def test_select_knee(self):
        """Test knee selection."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        front = [
            Solution(variables=[1.0, 1.0], objectives=[0.0, 10.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[2.0, 3.0], is_feasible=True),  # Knee point
            Solution(variables=[3.0, 3.0], objectives=[10.0, 0.0], is_feasible=True),
        ]

        selected = analyzer.select_solution(front, SelectionMethod.KNEE)

        assert selected is not None
        # Knee should be the point with max distance from line
        assert selected.objectives == [2.0, 3.0]

    def test_select_knee_small_front(self):
        """Test knee selection falls back to utopia for small front."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        front = [
            Solution(variables=[1.0, 1.0], objectives=[0.0, 10.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[10.0, 0.0], is_feasible=True),
        ]

        selected = analyzer.select_solution(front, SelectionMethod.KNEE)

        assert selected is not None

    def test_select_weighted_equal_weights(self):
        """Test weighted selection with equal weights."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        front = [
            Solution(variables=[1.0, 1.0], objectives=[0.0, 10.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[5.0, 5.0], is_feasible=True),
            Solution(variables=[3.0, 3.0], objectives=[10.0, 0.0], is_feasible=True),
        ]

        selected = analyzer.select_solution(front, SelectionMethod.WEIGHTED, weights=[0.5, 0.5])

        assert selected is not None

    def test_select_weighted_biased_first_objective(self):
        """Test weighted selection biased toward first objective."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        front = [
            Solution(variables=[1.0, 1.0], objectives=[0.0, 100.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[50.0, 50.0], is_feasible=True),
            Solution(variables=[3.0, 3.0], objectives=[100.0, 0.0], is_feasible=True),
        ]

        # Heavily weight first objective
        selected = analyzer.select_solution(front, SelectionMethod.WEIGHTED, weights=[0.9, 0.1])

        assert selected is not None
        # Should prefer solution with best first objective
        assert selected.objectives[0] == 0.0

    def test_select_weighted_biased_second_objective(self):
        """Test weighted selection biased toward second objective."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        front = [
            Solution(variables=[1.0, 1.0], objectives=[0.0, 100.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[50.0, 50.0], is_feasible=True),
            Solution(variables=[3.0, 3.0], objectives=[100.0, 0.0], is_feasible=True),
        ]

        # Heavily weight second objective
        selected = analyzer.select_solution(front, SelectionMethod.WEIGHTED, weights=[0.1, 0.9])

        assert selected is not None
        # Should prefer solution with best second objective
        assert selected.objectives[1] == 0.0

    def test_select_manual_returns_first(self):
        """Test manual selection returns first solution."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        front = [
            Solution(variables=[1.0, 1.0], objectives=[5.0, 5.0], is_feasible=True),
            Solution(variables=[2.0, 2.0], objectives=[3.0, 7.0], is_feasible=True),
        ]

        selected = analyzer.select_solution(front, SelectionMethod.MANUAL)

        assert selected is not None
        assert selected == front[0]


class TestParetoAnalyzerPointToLineDistance:
    """Tests for point-to-line distance calculation."""

    def test_point_on_line(self):
        """Test point on line has zero distance."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        # Point on line from (0,0) to (10,10)
        dist = analyzer._point_to_line_distance([5.0, 5.0], [0.0, 0.0], [10.0, 10.0])
        assert abs(dist) < 0.001

    def test_point_off_line(self):
        """Test point off line has positive distance."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        # Point (0, 5) distance to line from (0,0) to (10,0) is 5
        dist = analyzer._point_to_line_distance([5.0, 5.0], [0.0, 0.0], [10.0, 0.0])
        assert abs(dist - 5.0) < 0.001


class TestParetoAnalyzerVisualizationData:
    """Tests for visualization data generation."""

    def test_visualization_data_empty_front(self):
        """Test visualization data for empty front."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        data = analyzer.get_visualization_data([])

        assert data["points"] == []
        assert data["variable_names"] == ["x", "y"]
        assert data["objective_names"] == ["f1", "f2"]
        assert data["metrics"]["n_solutions"] == 0

    def test_visualization_data_with_solutions(self):
        """Test visualization data with solutions."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        front = [
            Solution(variables=[1.0, 2.0], objectives=[5.0, 10.0], is_feasible=True),
            Solution(variables=[3.0, 4.0], objectives=[10.0, 5.0], is_feasible=True),
        ]

        data = analyzer.get_visualization_data(front)

        assert len(data["points"]) == 2
        assert data["points"][0]["objectives"] == [5.0, 10.0]
        assert data["points"][0]["variables"] == [1.0, 2.0]
        assert data["points"][0]["is_feasible"] == True
        assert data["metrics"]["n_solutions"] == 2

    def test_visualization_data_includes_all_fields(self):
        """Test visualization data includes all expected fields."""
        problem = create_two_objective_problem()
        analyzer = ParetoAnalyzer(problem)

        front = [
            Solution(variables=[1.0, 2.0], objectives=[5.0, 10.0], is_feasible=True),
        ]

        data = analyzer.get_visualization_data(front)

        assert "points" in data
        assert "variable_names" in data
        assert "objective_names" in data
        assert "metrics" in data

        # Check metrics fields
        metrics = data["metrics"]
        assert "n_solutions" in metrics
        assert "hypervolume" in metrics
        assert "spread" in metrics
        assert "spacing" in metrics
        assert "objective_mins" in metrics
        assert "objective_maxs" in metrics
