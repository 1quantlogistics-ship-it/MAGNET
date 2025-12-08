"""
Unit tests for optimization schema.

Tests DesignVariable, Objective, Constraint, OptimizationProblem, Solution.
"""

import pytest
from magnet.optimization.schema import (
    DesignVariable,
    Objective,
    Constraint,
    OptimizationProblem,
    Solution,
    OptimizationResult,
)
from magnet.optimization.enums import (
    ObjectiveType,
    ConstraintType,
    OptimizerStatus,
    SelectionMethod,
)


class MockStateManager:
    """Mock StateManager for testing."""

    def __init__(self, data: dict = None):
        self._data = data or {}

    def get(self, key: str, default=None):
        keys = key.split(".")
        current = self._data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current


class TestDesignVariable:
    """Tests for DesignVariable."""

    def test_create_variable(self):
        """Test creating design variable."""
        var = DesignVariable(
            name="Hull Length",
            state_path="hull.lwl",
            lower_bound=15.0,
            upper_bound=35.0,
        )

        assert var.name == "Hull Length"
        assert var.state_path == "hull.lwl"
        assert var.lower_bound == 15.0
        assert var.upper_bound == 35.0

    def test_default_initial_value(self):
        """Test default initial value is midpoint."""
        var = DesignVariable(
            name="Test",
            state_path="test.path",
            lower_bound=10.0,
            upper_bound=20.0,
        )

        assert var.initial_value == 15.0

    def test_default_step_size(self):
        """Test default step size is 5% of range."""
        var = DesignVariable(
            name="Test",
            state_path="test.path",
            lower_bound=0.0,
            upper_bound=100.0,
        )

        assert var.step_size == 5.0  # (100-0) / 20

    def test_normalize(self):
        """Test value normalization."""
        var = DesignVariable(
            name="Test",
            state_path="test.path",
            lower_bound=10.0,
            upper_bound=30.0,
        )

        assert var.normalize(10.0) == 0.0
        assert var.normalize(20.0) == 0.5
        assert var.normalize(30.0) == 1.0

    def test_denormalize(self):
        """Test value denormalization."""
        var = DesignVariable(
            name="Test",
            state_path="test.path",
            lower_bound=10.0,
            upper_bound=30.0,
        )

        assert var.denormalize(0.0) == 10.0
        assert var.denormalize(0.5) == 20.0
        assert var.denormalize(1.0) == 30.0

    def test_clamp(self):
        """Test value clamping."""
        var = DesignVariable(
            name="Test",
            state_path="test.path",
            lower_bound=10.0,
            upper_bound=30.0,
        )

        assert var.clamp(5.0) == 10.0
        assert var.clamp(20.0) == 20.0
        assert var.clamp(40.0) == 30.0

    def test_to_dict(self):
        """Test serialization."""
        var = DesignVariable(
            name="Hull Length",
            state_path="hull.lwl",
            lower_bound=15.0,
            upper_bound=35.0,
            description="Length waterline",
        )

        data = var.to_dict()
        assert data["name"] == "Hull Length"
        assert data["state_path"] == "hull.lwl"
        assert data["lower_bound"] == 15.0


class TestObjective:
    """Tests for Objective."""

    def test_create_minimize_objective(self):
        """Test creating minimize objective."""
        obj = Objective(
            name="Cost",
            state_path="cost.total_price",
            objective_type=ObjectiveType.MINIMIZE,
        )

        assert obj.name == "Cost"
        assert obj.objective_type == ObjectiveType.MINIMIZE

    def test_create_maximize_objective(self):
        """Test creating maximize objective."""
        obj = Objective(
            name="Speed",
            state_path="mission.max_speed_kts",
            objective_type=ObjectiveType.MAXIMIZE,
        )

        assert obj.objective_type == ObjectiveType.MAXIMIZE

    def test_evaluate_minimize(self):
        """Test evaluating minimize objective."""
        obj = Objective(
            name="Cost",
            state_path="cost.total_price",
            objective_type=ObjectiveType.MINIMIZE,
            weight=1.0,
        )

        state = MockStateManager({"cost": {"total_price": 1000000}})
        value = obj.evaluate(state)

        assert value == 1000000

    def test_evaluate_maximize(self):
        """Test evaluating maximize objective (converted to minimize)."""
        obj = Objective(
            name="Speed",
            state_path="mission.max_speed_kts",
            objective_type=ObjectiveType.MAXIMIZE,
            weight=1.0,
        )

        state = MockStateManager({"mission": {"max_speed_kts": 30}})
        value = obj.evaluate(state)

        assert value == -30  # Negated for minimization

    def test_evaluate_with_target(self):
        """Test evaluating objective with target value."""
        obj = Objective(
            name="Length",
            state_path="hull.lwl",
            objective_type=ObjectiveType.MINIMIZE,
            target_value=25.0,
        )

        state = MockStateManager({"hull": {"lwl": 27.0}})
        value = obj.evaluate(state)

        assert value == 2.0  # |27 - 25|

    def test_evaluate_with_weight(self):
        """Test evaluating with weight."""
        obj = Objective(
            name="Cost",
            state_path="cost.total_price",
            objective_type=ObjectiveType.MINIMIZE,
            weight=2.0,
        )

        state = MockStateManager({"cost": {"total_price": 1000}})
        value = obj.evaluate(state)

        assert value == 2000

    def test_to_dict(self):
        """Test serialization."""
        obj = Objective(
            name="Cost",
            state_path="cost.total_price",
            objective_type=ObjectiveType.MINIMIZE,
        )

        data = obj.to_dict()
        assert data["name"] == "Cost"
        assert data["type"] == "minimize"


class TestConstraint:
    """Tests for Constraint."""

    def test_create_ge_constraint(self):
        """Test creating >= constraint."""
        constr = Constraint(
            name="Minimum GM",
            constraint_type=ConstraintType.INEQUALITY_GE,
            state_path="stability.gm_m",
            limit_value=0.35,
        )

        assert constr.name == "Minimum GM"
        assert constr.constraint_type == ConstraintType.INEQUALITY_GE
        assert constr.limit_value == 0.35

    def test_evaluate_ge_satisfied(self):
        """Test >= constraint is satisfied."""
        constr = Constraint(
            name="Minimum GM",
            constraint_type=ConstraintType.INEQUALITY_GE,
            state_path="stability.gm_m",
            limit_value=0.35,
        )

        state = MockStateManager({"stability": {"gm_m": 0.50}})
        violation = constr.evaluate(state)

        assert violation == 0
        assert constr.is_satisfied(state)

    def test_evaluate_ge_violated(self):
        """Test >= constraint is violated."""
        constr = Constraint(
            name="Minimum GM",
            constraint_type=ConstraintType.INEQUALITY_GE,
            state_path="stability.gm_m",
            limit_value=0.35,
        )

        state = MockStateManager({"stability": {"gm_m": 0.20}})
        violation = constr.evaluate(state)

        assert abs(violation - 0.15) < 0.001  # 0.35 - 0.20
        assert not constr.is_satisfied(state)

    def test_evaluate_le_satisfied(self):
        """Test <= constraint is satisfied."""
        constr = Constraint(
            name="Max Failures",
            constraint_type=ConstraintType.INEQUALITY_LE,
            state_path="compliance.fail_count",
            limit_value=0,
        )

        state = MockStateManager({"compliance": {"fail_count": 0}})
        violation = constr.evaluate(state)

        assert violation == 0

    def test_evaluate_le_violated(self):
        """Test <= constraint is violated."""
        constr = Constraint(
            name="Max Failures",
            constraint_type=ConstraintType.INEQUALITY_LE,
            state_path="compliance.fail_count",
            limit_value=0,
        )

        state = MockStateManager({"compliance": {"fail_count": 2}})
        violation = constr.evaluate(state)

        assert violation == 2  # 2 - 0

    def test_evaluate_equality(self):
        """Test equality constraint."""
        constr = Constraint(
            name="Target Length",
            constraint_type=ConstraintType.EQUALITY,
            state_path="hull.lwl",
            limit_value=25.0,
            tolerance=0.1,
        )

        # Satisfied (within tolerance)
        state = MockStateManager({"hull": {"lwl": 25.05}})
        assert constr.is_satisfied(state)

        # Violated
        state = MockStateManager({"hull": {"lwl": 26.0}})
        assert not constr.is_satisfied(state)

    def test_tolerance(self):
        """Test tolerance is applied."""
        constr = Constraint(
            name="Test",
            constraint_type=ConstraintType.INEQUALITY_GE,
            state_path="test.value",
            limit_value=1.0,
            tolerance=0.01,
        )

        # Within tolerance
        state = MockStateManager({"test": {"value": 0.995}})
        violation = constr.evaluate(state)
        assert violation == 0

    def test_to_dict(self):
        """Test serialization."""
        constr = Constraint(
            name="Minimum GM",
            constraint_type=ConstraintType.INEQUALITY_GE,
            state_path="stability.gm_m",
            limit_value=0.35,
        )

        data = constr.to_dict()
        assert data["name"] == "Minimum GM"
        assert data["type"] == "inequality_ge"
        assert data["limit_value"] == 0.35


class TestOptimizationProblem:
    """Tests for OptimizationProblem."""

    def test_create_problem(self):
        """Test creating optimization problem."""
        problem = OptimizationProblem(
            name="test_problem",
            description="Test problem",
        )

        assert problem.name == "test_problem"
        assert problem.n_var == 0
        assert problem.n_obj == 0
        assert problem.n_constr == 0

    def test_add_variable(self):
        """Test adding variable."""
        problem = OptimizationProblem(name="test")
        problem.add_variable(DesignVariable(
            name="Length",
            state_path="hull.lwl",
            lower_bound=15.0,
            upper_bound=35.0,
        ))

        assert problem.n_var == 1
        assert problem.variables[0].name == "Length"

    def test_add_objective(self):
        """Test adding objective."""
        problem = OptimizationProblem(name="test")
        problem.add_objective(Objective(
            name="Cost",
            state_path="cost.total_price",
        ))

        assert problem.n_obj == 1

    def test_add_constraint(self):
        """Test adding constraint."""
        problem = OptimizationProblem(name="test")
        problem.add_constraint(Constraint(
            name="GM",
            constraint_type=ConstraintType.INEQUALITY_GE,
            state_path="stability.gm_m",
            limit_value=0.35,
        ))

        assert problem.n_constr == 1

    def test_get_bounds(self):
        """Test getting bounds."""
        problem = OptimizationProblem(name="test")
        problem.add_variable(DesignVariable(
            name="Length",
            state_path="hull.lwl",
            lower_bound=15.0,
            upper_bound=35.0,
        ))
        problem.add_variable(DesignVariable(
            name="Beam",
            state_path="hull.beam",
            lower_bound=4.0,
            upper_bound=8.0,
        ))

        lower, upper = problem.get_bounds()
        assert lower == [15.0, 4.0]
        assert upper == [35.0, 8.0]

    def test_get_initial_values(self):
        """Test getting initial values."""
        problem = OptimizationProblem(name="test")
        problem.add_variable(DesignVariable(
            name="Length",
            state_path="hull.lwl",
            lower_bound=10.0,
            upper_bound=30.0,
        ))

        initials = problem.get_initial_values()
        assert initials == [20.0]

    def test_to_dict(self):
        """Test serialization."""
        problem = OptimizationProblem(
            name="test",
            description="Test problem",
        )
        problem.add_variable(DesignVariable(
            name="Length",
            state_path="hull.lwl",
            lower_bound=15.0,
            upper_bound=35.0,
        ))
        problem.add_objective(Objective(
            name="Cost",
            state_path="cost.total_price",
        ))

        data = problem.to_dict()
        assert data["name"] == "test"
        assert data["n_var"] == 1
        assert data["n_obj"] == 1
        assert len(data["variables"]) == 1


class TestSolution:
    """Tests for Solution."""

    def test_create_solution(self):
        """Test creating solution."""
        sol = Solution(
            variables=[25.0, 6.0],
            objectives=[1000000, 50.0],
        )

        assert sol.variables == [25.0, 6.0]
        assert sol.objectives == [1000000, 50.0]
        assert sol.is_feasible

    def test_infeasible_solution(self):
        """Test infeasible solution."""
        sol = Solution(
            variables=[25.0, 6.0],
            objectives=[1000000, 50.0],
            constraint_violation=0.5,
            is_feasible=False,
        )

        assert not sol.is_feasible
        assert sol.constraint_violation == 0.5

    def test_dominates_better_all(self):
        """Test domination when better in all objectives."""
        sol1 = Solution(
            variables=[25.0, 6.0],
            objectives=[100, 10],
        )
        sol2 = Solution(
            variables=[26.0, 7.0],
            objectives=[200, 20],
        )

        assert sol1.dominates(sol2)
        assert not sol2.dominates(sol1)

    def test_dominates_better_one(self):
        """Test domination when better in one, equal in others."""
        sol1 = Solution(
            variables=[25.0, 6.0],
            objectives=[100, 10],
        )
        sol2 = Solution(
            variables=[26.0, 7.0],
            objectives=[100, 20],
        )

        assert sol1.dominates(sol2)

    def test_no_domination_tradeoff(self):
        """Test no domination with trade-off."""
        sol1 = Solution(
            variables=[25.0, 6.0],
            objectives=[100, 20],
        )
        sol2 = Solution(
            variables=[26.0, 7.0],
            objectives=[200, 10],
        )

        assert not sol1.dominates(sol2)
        assert not sol2.dominates(sol1)

    def test_infeasible_never_dominates(self):
        """Test infeasible solution never dominates."""
        sol1 = Solution(
            variables=[25.0, 6.0],
            objectives=[100, 10],
            is_feasible=False,
        )
        sol2 = Solution(
            variables=[26.0, 7.0],
            objectives=[200, 20],
            is_feasible=True,
        )

        assert not sol1.dominates(sol2)
        assert sol2.dominates(sol1)

    def test_to_dict(self):
        """Test serialization."""
        sol = Solution(
            variables=[25.0, 6.0],
            objectives=[1000000, 50.0],
        )

        data = sol.to_dict()
        assert len(data["variables"]) == 2
        assert len(data["objectives"]) == 2


class TestOptimizationResult:
    """Tests for OptimizationResult."""

    def test_create_result(self):
        """Test creating result."""
        result = OptimizationResult(
            problem_name="test",
            status=OptimizerStatus.CONVERGED,
        )

        assert result.problem_name == "test"
        assert result.status == OptimizerStatus.CONVERGED
        assert result.n_solutions == 0

    def test_with_pareto_front(self):
        """Test result with Pareto front."""
        result = OptimizationResult(
            problem_name="test",
            status=OptimizerStatus.CONVERGED,
            pareto_front=[
                Solution(variables=[25.0], objectives=[100, 50]),
                Solution(variables=[30.0], objectives=[150, 30]),
            ],
        )

        assert result.n_solutions == 2

    def test_is_successful(self):
        """Test success check."""
        converged = OptimizationResult(
            problem_name="test",
            status=OptimizerStatus.CONVERGED,
        )
        max_iter = OptimizationResult(
            problem_name="test",
            status=OptimizerStatus.MAX_ITERATIONS,
        )
        failed = OptimizationResult(
            problem_name="test",
            status=OptimizerStatus.FAILED,
        )

        assert converged.is_successful
        assert max_iter.is_successful
        assert not failed.is_successful

    def test_to_dict(self):
        """Test serialization."""
        result = OptimizationResult(
            problem_name="test",
            status=OptimizerStatus.CONVERGED,
            iterations=50,
            evaluations=2500,
        )

        data = result.to_dict()
        assert data["problem_name"] == "test"
        assert data["status"] == "converged"
        assert data["statistics"]["iterations"] == 50
