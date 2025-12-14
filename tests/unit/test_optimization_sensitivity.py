"""
tests/unit/test_optimization_sensitivity.py - Tests for sensitivity analysis.

BRAVO OWNS THIS FILE.

Tests for Module 13 v1.1 - SensitivityAnalyzer, VariableSensitivity, SensitivityResult.
"""

import pytest
from magnet.optimization import (
    SensitivityAnalyzer,
    SensitivityResult,
    VariableSensitivity,
    OptimizationProblem,
    DesignVariable,
    Objective,
    Solution,
    ObjectiveType,
)


class MockStateManager:
    """Mock StateManager for testing."""

    def __init__(self):
        self._data = {}

    def clone(self):
        """Clone method for testing."""
        new_state = MockStateManager()
        new_state._data = self._data.copy()
        return new_state

    def get(self, path, default=None):
        return self._data.get(path, default)

    def set(self, path, value, source=None):
        self._data[path] = value

    def write(self, path, value, source="", description=""):
        self._data[path] = value


def create_two_variable_problem():
    """Create a simple two-variable problem."""
    problem = OptimizationProblem(
        name="test_problem",
        description="Test problem for sensitivity",
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


class LinearValidator:
    """Validator that computes linear objectives."""

    def validate(self, state, config):
        x = state.get("var.x", 0)
        y = state.get("var.y", 0)
        # f1 = 2x + y
        # f2 = x + 3y
        state.set("result.f1", 2 * x + y)
        state.set("result.f2", x + 3 * y)


class QuadraticValidator:
    """Validator that computes quadratic objectives."""

    def validate(self, state, config):
        x = state.get("var.x", 0)
        y = state.get("var.y", 0)
        # f1 = x^2
        # f2 = y^2
        state.set("result.f1", x ** 2)
        state.set("result.f2", y ** 2)


class TestVariableSensitivity:
    """Tests for VariableSensitivity dataclass."""

    def test_default_values(self):
        """Test default values."""
        vs = VariableSensitivity(variable_name="x", state_path="var.x")
        assert vs.variable_name == "x"
        assert vs.state_path == "var.x"
        assert vs.sensitivities == {}
        assert vs.importance == 0.0

    def test_to_dict(self):
        """Test dictionary serialization."""
        vs = VariableSensitivity(
            variable_name="x",
            state_path="var.x",
            sensitivities={"f1": 2.123456789, "f2": 1.987654321},
            importance=0.75,
        )
        data = vs.to_dict()

        assert data["variable_name"] == "x"
        assert data["state_path"] == "var.x"
        assert data["sensitivities"]["f1"] == 2.123457  # Rounded
        assert data["sensitivities"]["f2"] == 1.987654
        assert data["importance"] == 0.75


class TestSensitivityResult:
    """Tests for SensitivityResult dataclass."""

    def test_default_values(self):
        """Test default values."""
        result = SensitivityResult()
        assert result.base_solution is None
        assert result.variable_sensitivities == []
        assert result.perturbation_size == 0.01

    def test_to_dict_empty(self):
        """Test dictionary serialization when empty."""
        result = SensitivityResult()
        data = result.to_dict()

        assert data["base_solution"] is None
        assert data["variable_sensitivities"] == []
        assert data["perturbation_size"] == 0.01

    def test_to_dict_with_data(self):
        """Test dictionary serialization with data."""
        solution = Solution(variables=[1.0, 2.0], objectives=[5.0, 10.0], is_feasible=True)
        vs = VariableSensitivity(variable_name="x", state_path="var.x")

        result = SensitivityResult(
            base_solution=solution,
            variable_sensitivities=[vs],
            perturbation_size=0.05,
        )
        data = result.to_dict()

        assert data["base_solution"] is not None
        assert len(data["variable_sensitivities"]) == 1
        assert data["perturbation_size"] == 0.05


class TestSensitivityAnalyzerInit:
    """Tests for SensitivityAnalyzer initialization."""

    def test_init_basic(self):
        """Test basic initialization."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        analyzer = SensitivityAnalyzer(problem, state)

        assert analyzer.problem == problem
        assert analyzer.base_state == state
        assert analyzer.validators == []

    def test_init_with_validators(self):
        """Test initialization with validators."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        validator = LinearValidator()
        analyzer = SensitivityAnalyzer(problem, state, validators=[validator])

        assert len(analyzer.validators) == 1


class TestSensitivityAnalyzerAnalyze:
    """Tests for sensitivity analysis."""

    def test_analyze_linear_objectives(self):
        """Test sensitivity analysis with linear objectives."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        validator = LinearValidator()
        analyzer = SensitivityAnalyzer(problem, state, validators=[validator])

        solution = Solution(variables=[5.0, 5.0], objectives=[15.0, 20.0], is_feasible=True)
        result = analyzer.analyze(solution)

        assert result.base_solution == solution
        assert len(result.variable_sensitivities) == 2

        # For linear f1 = 2x + y, df1/dx = 2
        x_sens = result.variable_sensitivities[0]
        assert x_sens.variable_name == "x"
        assert abs(x_sens.sensitivities["f1"] - 2.0) < 0.1

        # For linear f2 = x + 3y, df2/dy = 3
        y_sens = result.variable_sensitivities[1]
        assert y_sens.variable_name == "y"
        assert abs(y_sens.sensitivities["f2"] - 3.0) < 0.1

    def test_analyze_quadratic_objectives(self):
        """Test sensitivity analysis with quadratic objectives."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        validator = QuadraticValidator()
        analyzer = SensitivityAnalyzer(problem, state, validators=[validator])

        # At x=5, df1/dx = 2x = 10
        solution = Solution(variables=[5.0, 3.0], objectives=[25.0, 9.0], is_feasible=True)
        result = analyzer.analyze(solution)

        x_sens = result.variable_sensitivities[0]
        # f1 = x^2, df1/dx = 2x = 10 at x=5
        assert abs(x_sens.sensitivities["f1"] - 10.0) < 1.0

        y_sens = result.variable_sensitivities[1]
        # f2 = y^2, df2/dy = 2y = 6 at y=3
        assert abs(y_sens.sensitivities["f2"] - 6.0) < 1.0

    def test_analyze_returns_result_type(self):
        """Test analyze returns SensitivityResult."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        validator = LinearValidator()
        analyzer = SensitivityAnalyzer(problem, state, validators=[validator])

        solution = Solution(variables=[5.0, 5.0], objectives=[15.0, 20.0], is_feasible=True)
        result = analyzer.analyze(solution)

        assert isinstance(result, SensitivityResult)

    def test_analyze_custom_perturbation_size(self):
        """Test analyze with custom perturbation size."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        validator = LinearValidator()
        analyzer = SensitivityAnalyzer(problem, state, validators=[validator])

        solution = Solution(variables=[5.0, 5.0], objectives=[15.0, 20.0], is_feasible=True)
        result = analyzer.analyze(solution, perturbation_size=0.05)

        assert result.perturbation_size == 0.05


class TestSensitivityAnalyzerImportance:
    """Tests for importance computation."""

    def test_importance_normalized(self):
        """Test importance values are normalized."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        validator = LinearValidator()
        analyzer = SensitivityAnalyzer(problem, state, validators=[validator])

        solution = Solution(variables=[5.0, 5.0], objectives=[15.0, 20.0], is_feasible=True)
        result = analyzer.analyze(solution)

        # Max importance should be 1.0
        max_importance = max(vs.importance for vs in result.variable_sensitivities)
        assert abs(max_importance - 1.0) < 0.01

    def test_importance_all_in_range(self):
        """Test all importance values are in [0, 1]."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        validator = LinearValidator()
        analyzer = SensitivityAnalyzer(problem, state, validators=[validator])

        solution = Solution(variables=[5.0, 5.0], objectives=[15.0, 20.0], is_feasible=True)
        result = analyzer.analyze(solution)

        for vs in result.variable_sensitivities:
            assert 0.0 <= vs.importance <= 1.0


class TestSensitivityAnalyzerEvaluateObjectives:
    """Tests for objective evaluation helper."""

    def test_evaluate_objectives_basic(self):
        """Test basic objective evaluation."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        validator = LinearValidator()
        analyzer = SensitivityAnalyzer(problem, state, validators=[validator])

        objectives = analyzer._evaluate_objectives([2.0, 3.0])

        # f1 = 2*2 + 3 = 7
        # f2 = 2 + 3*3 = 11
        assert objectives is not None
        assert abs(objectives[0] - 7.0) < 0.01
        assert abs(objectives[1] - 11.0) < 0.01

    def test_evaluate_objectives_uses_clone(self):
        """Test evaluation uses state clone."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        validator = LinearValidator()
        analyzer = SensitivityAnalyzer(problem, state, validators=[validator])

        # Original state should not be modified
        original_data = state._data.copy()
        analyzer._evaluate_objectives([5.0, 5.0])

        # Original state should be unchanged
        assert state._data == original_data


class TestSensitivityAnalyzerLocalRegion:
    """Tests for local region analysis."""

    def test_local_region_basic(self):
        """Test basic local region analysis."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        validator = LinearValidator()
        analyzer = SensitivityAnalyzer(problem, state, validators=[validator])

        solution = Solution(variables=[5.0, 5.0], objectives=[15.0, 20.0], is_feasible=True)
        result = analyzer.analyze_local_region(solution, n_samples=10)

        assert "n_samples" in result
        assert result["n_samples"] <= 10
        assert "objective_means" in result
        assert "objective_mins" in result
        assert "objective_maxs" in result
        assert "objective_ranges" in result

    def test_local_region_custom_size(self):
        """Test local region with custom size."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        validator = LinearValidator()
        analyzer = SensitivityAnalyzer(problem, state, validators=[validator])

        solution = Solution(variables=[5.0, 5.0], objectives=[15.0, 20.0], is_feasible=True)
        result = analyzer.analyze_local_region(solution, n_samples=10, region_size=0.2)

        assert result["region_size"] == 0.2

    def test_local_region_ranges_positive(self):
        """Test local region ranges are non-negative."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        validator = LinearValidator()
        analyzer = SensitivityAnalyzer(problem, state, validators=[validator])

        solution = Solution(variables=[5.0, 5.0], objectives=[15.0, 20.0], is_feasible=True)
        result = analyzer.analyze_local_region(solution, n_samples=20)

        for r in result["objective_ranges"]:
            assert r >= 0


class TestSensitivityAnalyzerTradeoffCurve:
    """Tests for trade-off curve generation."""

    def test_tradeoff_curve_basic(self):
        """Test basic trade-off curve generation."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        validator = LinearValidator()
        analyzer = SensitivityAnalyzer(problem, state, validators=[validator])

        solution = Solution(variables=[5.0, 5.0], objectives=[15.0, 20.0], is_feasible=True)
        result = analyzer.get_tradeoff_curve(solution, variable_index=0, n_points=10)

        assert result["variable_name"] == "x"
        assert result["variable_index"] == 0
        assert result["n_points"] <= 10
        assert "curve" in result

    def test_tradeoff_curve_spans_bounds(self):
        """Test trade-off curve spans variable bounds."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        validator = LinearValidator()
        analyzer = SensitivityAnalyzer(problem, state, validators=[validator])

        solution = Solution(variables=[5.0, 5.0], objectives=[15.0, 20.0], is_feasible=True)
        result = analyzer.get_tradeoff_curve(solution, variable_index=0, n_points=10)

        curve = result["curve"]
        if curve:
            # First point should be at lower bound
            assert abs(curve[0]["variable_value"] - 0.0) < 0.01
            # Last point should be at upper bound
            assert abs(curve[-1]["variable_value"] - 10.0) < 0.01

    def test_tradeoff_curve_objectives_correct(self):
        """Test trade-off curve objectives are correct."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        validator = LinearValidator()
        analyzer = SensitivityAnalyzer(problem, state, validators=[validator])

        solution = Solution(variables=[5.0, 5.0], objectives=[15.0, 20.0], is_feasible=True)
        result = analyzer.get_tradeoff_curve(solution, variable_index=0, n_points=5)

        # Check first point (x=0, y=5)
        # f1 = 2*0 + 5 = 5
        # f2 = 0 + 3*5 = 15
        curve = result["curve"]
        if curve:
            first = curve[0]
            assert abs(first["objectives"][0] - 5.0) < 0.1
            assert abs(first["objectives"][1] - 15.0) < 0.1

    def test_tradeoff_curve_second_variable(self):
        """Test trade-off curve for second variable."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        validator = LinearValidator()
        analyzer = SensitivityAnalyzer(problem, state, validators=[validator])

        solution = Solution(variables=[5.0, 5.0], objectives=[15.0, 20.0], is_feasible=True)
        result = analyzer.get_tradeoff_curve(solution, variable_index=1, n_points=10)

        assert result["variable_name"] == "y"
        assert result["variable_index"] == 1


class TestSensitivityAnalyzerEdgeCases:
    """Tests for edge cases."""

    def test_analysis_at_bounds(self):
        """Test sensitivity analysis at variable bounds."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        validator = LinearValidator()
        analyzer = SensitivityAnalyzer(problem, state, validators=[validator])

        # Solution at lower bounds
        solution = Solution(variables=[0.0, 0.0], objectives=[0.0, 0.0], is_feasible=True)
        result = analyzer.analyze(solution)

        assert len(result.variable_sensitivities) == 2
        # Should still compute sensitivities (clamped perturbation)

    def test_analysis_at_upper_bounds(self):
        """Test sensitivity analysis at upper bounds."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        validator = LinearValidator()
        analyzer = SensitivityAnalyzer(problem, state, validators=[validator])

        # Solution at upper bounds
        solution = Solution(variables=[10.0, 10.0], objectives=[30.0, 40.0], is_feasible=True)
        result = analyzer.analyze(solution)

        assert len(result.variable_sensitivities) == 2

    def test_small_perturbation_size(self):
        """Test analysis with small perturbation size."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        validator = LinearValidator()
        analyzer = SensitivityAnalyzer(problem, state, validators=[validator])

        solution = Solution(variables=[5.0, 5.0], objectives=[15.0, 20.0], is_feasible=True)
        result = analyzer.analyze(solution, perturbation_size=0.001)

        # Should still work with very small perturbation
        assert len(result.variable_sensitivities) == 2


class FailingValidator:
    """Validator that always fails."""

    def validate(self, state, config):
        raise ValueError("Validation failed")


class TestSensitivityAnalyzerFailure:
    """Tests for handling failures."""

    def test_failing_validator_returns_none(self):
        """Test failing validator returns None for objectives."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        analyzer = SensitivityAnalyzer(problem, state, validators=[FailingValidator()])

        objectives = analyzer._evaluate_objectives([5.0, 5.0])
        assert objectives is None

    def test_local_region_with_failures(self):
        """Test local region handles evaluation failures."""
        problem = create_two_variable_problem()
        state = MockStateManager()
        analyzer = SensitivityAnalyzer(problem, state, validators=[FailingValidator()])

        solution = Solution(variables=[5.0, 5.0], objectives=[15.0, 20.0], is_feasible=True)
        result = analyzer.analyze_local_region(solution, n_samples=10)

        # Should return error or empty samples
        assert "error" in result or result.get("n_samples", 0) == 0
