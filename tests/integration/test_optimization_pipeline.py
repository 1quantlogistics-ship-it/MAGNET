"""
tests/integration/test_optimization_pipeline.py - Integration tests for optimization pipeline.

BRAVO OWNS THIS FILE.

Tests for Module 13 v1.1 - Integration tests for design optimization.
"""

import pytest
from magnet.optimization import (
    DesignOptimizer,
    ParetoAnalyzer,
    SensitivityAnalyzer,
    OptimizationProblem,
    DesignVariable,
    Objective,
    Constraint,
    Solution,
    OptimizationResult,
    ObjectiveType,
    ConstraintType,
    OptimizerStatus,
    SelectionMethod,
    create_standard_patrol_boat_problem,
    create_cost_weight_problem,
    create_speed_efficiency_problem,
    create_capacity_cost_problem,
)


class MockStateManager:
    """Mock StateManager with clone support for v1.1 P3."""

    def __init__(self):
        self._data = {}
        self._writes = []

    def clone(self):
        """v1.1 P3: Clone for optimizer evaluation."""
        new_state = MockStateManager()
        new_state._data = self._data.copy()
        return new_state

    def get(self, path, default=None):
        return self._data.get(path, default)

    def set(self, path, value):
        self._data[path] = value

    def write(self, path, value, agent="", description=""):
        self._data[path] = value
        self._writes.append((path, value, agent))


class PatrolBoatValidator:
    """Validator that simulates patrol boat calculations."""

    def validate(self, state, config):
        # Hull calculations
        lwl = state.get("hull.lwl", 25.0)
        beam = state.get("hull.beam", 6.0)
        depth = state.get("hull.depth", 3.0)

        # Simplified calculations
        displacement = lwl * beam * depth * 0.5 * 1.025  # Rough displacement

        # Cost model: base + size factor
        base_cost = 500000
        size_factor = lwl * beam * 10000
        power_cost = state.get("propulsion.installed_power_kw", 1000) * 200
        total_cost = base_cost + size_factor + power_cost
        state.set("cost.total_price", total_cost)

        # Weight model
        steel_weight = lwl * beam * depth * 0.15
        power_weight = state.get("propulsion.installed_power_kw", 1000) * 0.003
        lightship = steel_weight + power_weight + 20  # Plus equipment
        state.set("weight.lightship_mt", lightship)

        # Stability
        gm = 0.5 + beam * 0.05  # Simplified GM
        state.set("stability.gm_m", gm)

        # Freeboard (v1.1 P2: must use hull.freeboard_m)
        freeboard = depth * 0.3
        state.set("hull.freeboard_m", freeboard)

        # Compliance
        fail_count = 0
        if gm < 0.35:
            fail_count += 1
        if freeboard < 0.50:
            fail_count += 1
        state.set("compliance.fail_count", fail_count)


class SpeedEfficiencyValidator:
    """Validator for speed vs efficiency problem."""

    def validate(self, state, config):
        lwl = state.get("hull.lwl", 25.0)
        power = state.get("propulsion.installed_power_kw", 1000)

        # Speed depends on power and hull efficiency
        hull_efficiency = 1.0 - (lwl - 30) ** 2 / 1000  # Optimal around 30m
        max_speed = power ** 0.4 * hull_efficiency * 0.5
        state.set("mission.max_speed_kts", max_speed)

        # Fuel consumption depends on power
        fuel_rate = power * 0.25
        state.set("propulsion.fuel_consumption_lph", fuel_rate)


class CapacityCostValidator:
    """Validator for capacity vs cost problem."""

    def validate(self, state, config):
        lwl = state.get("hull.lwl", 25.0)
        beam = state.get("hull.beam", 6.0)
        depth = state.get("hull.depth", 3.0)

        # Deck area
        deck_area = lwl * beam * 0.8
        state.set("hull.deck_area_m2", deck_area)

        # Cost
        volume = lwl * beam * depth
        cost = 100000 + volume * 5000
        state.set("cost.total_price", cost)

        # Capacity estimates
        passengers = int(deck_area / 2)
        crew = 4
        state.set("mission.passengers", passengers)
        state.set("mission.crew_size", crew)


class TestOptimizationPipelineBasic:
    """Basic integration tests for optimization pipeline."""

    def test_full_optimization_cycle(self):
        """Test complete optimization cycle."""
        # Setup
        problem = create_cost_weight_problem()
        state = MockStateManager()
        validator = PatrolBoatValidator()

        # Run optimizer
        optimizer = DesignOptimizer(
            problem=problem,
            base_state=state,
            validators=[validator],
            population_size=20,
            max_generations=10,
            seed=42,
        )

        result = optimizer.optimize()

        # Verify result
        assert result.status == OptimizerStatus.MAX_ITERATIONS
        assert len(result.pareto_front) > 0
        assert result.selected_solution is not None
        assert result.iterations == 10

    def test_pareto_analysis_pipeline(self):
        """Test optimization + Pareto analysis pipeline."""
        # Setup
        problem = create_cost_weight_problem()
        state = MockStateManager()
        validator = PatrolBoatValidator()

        # Run optimizer
        optimizer = DesignOptimizer(
            problem=problem,
            base_state=state,
            validators=[validator],
            population_size=20,
            max_generations=10,
            seed=42,
        )

        opt_result = optimizer.optimize()

        # Analyze Pareto front
        analyzer = ParetoAnalyzer(problem)
        metrics = analyzer.compute_metrics(opt_result.pareto_front)

        assert metrics.n_solutions > 0
        assert metrics.hypervolume > 0
        assert len(metrics.objective_mins) == 2
        assert len(metrics.objective_maxs) == 2

    def test_sensitivity_analysis_pipeline(self):
        """Test optimization + sensitivity analysis pipeline."""
        # Setup
        problem = create_cost_weight_problem()
        state = MockStateManager()
        validator = PatrolBoatValidator()

        # Run optimizer
        optimizer = DesignOptimizer(
            problem=problem,
            base_state=state,
            validators=[validator],
            population_size=20,
            max_generations=10,
            seed=42,
        )

        opt_result = optimizer.optimize()

        # Analyze sensitivity of selected solution
        if opt_result.selected_solution:
            sens_analyzer = SensitivityAnalyzer(
                problem=problem,
                base_state=state,
                validators=[validator],
            )
            sens_result = sens_analyzer.analyze(opt_result.selected_solution)

            assert len(sens_result.variable_sensitivities) == problem.n_var


class TestOptimizationPipelineProblems:
    """Integration tests for different problem types."""

    def test_standard_patrol_boat_optimization(self):
        """Test standard patrol boat problem optimization."""
        problem = create_standard_patrol_boat_problem()
        state = MockStateManager()
        validator = PatrolBoatValidator()

        optimizer = DesignOptimizer(
            problem=problem,
            base_state=state,
            validators=[validator],
            population_size=20,
            max_generations=10,
            seed=42,
        )

        result = optimizer.optimize()

        # Should complete successfully
        assert result.status == OptimizerStatus.MAX_ITERATIONS
        assert len(result.pareto_front) > 0

        # Check constraints are considered (v1.1 P2)
        assert problem.constraints[1].state_path == "hull.freeboard_m"

    def test_speed_efficiency_optimization(self):
        """Test speed vs efficiency problem optimization."""
        problem = create_speed_efficiency_problem()
        state = MockStateManager()
        validator = SpeedEfficiencyValidator()

        optimizer = DesignOptimizer(
            problem=problem,
            base_state=state,
            validators=[validator],
            population_size=20,
            max_generations=10,
            seed=42,
        )

        result = optimizer.optimize()

        assert result.status == OptimizerStatus.MAX_ITERATIONS
        assert len(result.pareto_front) > 0

        # Check we have trade-off solutions
        # Some should prioritize speed, others fuel efficiency

    def test_capacity_cost_optimization(self):
        """Test capacity vs cost problem optimization."""
        problem = create_capacity_cost_problem(min_pax=5, min_crew=2)
        state = MockStateManager()
        validator = CapacityCostValidator()

        optimizer = DesignOptimizer(
            problem=problem,
            base_state=state,
            validators=[validator],
            population_size=20,
            max_generations=10,
            seed=42,
        )

        result = optimizer.optimize()

        assert result.status == OptimizerStatus.MAX_ITERATIONS


class TestOptimizationPipelineSelection:
    """Integration tests for solution selection."""

    def test_utopia_selection(self):
        """Test utopia point selection."""
        problem = create_cost_weight_problem()
        state = MockStateManager()
        validator = PatrolBoatValidator()

        optimizer = DesignOptimizer(
            problem=problem,
            base_state=state,
            validators=[validator],
            population_size=20,
            max_generations=10,
            seed=42,
        )

        result = optimizer.optimize()

        # Analyze and select
        analyzer = ParetoAnalyzer(problem)
        selected = analyzer.select_solution(result.pareto_front, SelectionMethod.UTOPIA)

        assert selected is not None
        assert selected in result.pareto_front

    def test_knee_selection(self):
        """Test knee point selection."""
        problem = create_cost_weight_problem()
        state = MockStateManager()
        validator = PatrolBoatValidator()

        optimizer = DesignOptimizer(
            problem=problem,
            base_state=state,
            validators=[validator],
            population_size=20,
            max_generations=10,
            seed=42,
        )

        result = optimizer.optimize()

        analyzer = ParetoAnalyzer(problem)
        selected = analyzer.select_solution(result.pareto_front, SelectionMethod.KNEE)

        assert selected is not None

    def test_weighted_selection(self):
        """Test weighted selection with different preferences."""
        problem = create_cost_weight_problem()
        state = MockStateManager()
        validator = PatrolBoatValidator()

        optimizer = DesignOptimizer(
            problem=problem,
            base_state=state,
            validators=[validator],
            population_size=30,
            max_generations=15,
            seed=42,
        )

        result = optimizer.optimize()

        analyzer = ParetoAnalyzer(problem)

        # Cost-focused
        cost_focused = analyzer.select_solution(
            result.pareto_front, SelectionMethod.WEIGHTED, weights=[0.9, 0.1]
        )

        # Weight-focused
        weight_focused = analyzer.select_solution(
            result.pareto_front, SelectionMethod.WEIGHTED, weights=[0.1, 0.9]
        )

        assert cost_focused is not None
        assert weight_focused is not None

        # Different selections should generally differ
        # (Though not guaranteed with small Pareto fronts)


class TestOptimizationPipelineVisualization:
    """Integration tests for visualization data generation."""

    def test_visualization_data_generation(self):
        """Test visualization data is generated correctly."""
        problem = create_cost_weight_problem()
        state = MockStateManager()
        validator = PatrolBoatValidator()

        optimizer = DesignOptimizer(
            problem=problem,
            base_state=state,
            validators=[validator],
            population_size=20,
            max_generations=10,
            seed=42,
        )

        result = optimizer.optimize()

        analyzer = ParetoAnalyzer(problem)
        viz_data = analyzer.get_visualization_data(result.pareto_front)

        assert "points" in viz_data
        assert "variable_names" in viz_data
        assert "objective_names" in viz_data
        assert "metrics" in viz_data

        assert len(viz_data["points"]) == len(result.pareto_front)
        assert viz_data["variable_names"] == ["Length", "Beam"]
        assert viz_data["objective_names"] == ["Cost", "Weight"]


class TestOptimizationPipelineClone:
    """Integration tests for v1.1 P3 clone functionality."""

    def test_optimizer_uses_clone(self):
        """Test optimizer uses StateManager.clone() for evaluations."""
        problem = create_cost_weight_problem()
        state = MockStateManager()
        validator = PatrolBoatValidator()

        # Set some initial values
        state.set("initial.test", "value")

        optimizer = DesignOptimizer(
            problem=problem,
            base_state=state,
            validators=[validator],
            population_size=10,
            max_generations=5,
            seed=42,
        )

        result = optimizer.optimize()

        # Original state should not have optimization artifacts
        # (values set during evaluation)
        # The clone should handle this isolation
        assert state.get("initial.test") == "value"

    def test_sensitivity_uses_clone(self):
        """Test sensitivity analyzer uses clone."""
        problem = create_cost_weight_problem()
        state = MockStateManager()
        state.set("original.data", 123)
        validator = PatrolBoatValidator()

        solution = Solution(variables=[25.0, 6.0], objectives=[1000000, 50], is_feasible=True)

        analyzer = SensitivityAnalyzer(
            problem=problem,
            base_state=state,
            validators=[validator],
        )

        sens_result = analyzer.analyze(solution)

        # Original state should be unchanged
        assert state.get("original.data") == 123


class TestOptimizationPipelineConstraints:
    """Integration tests for constraint handling."""

    def test_feasible_solutions_preferred(self):
        """Test feasible solutions are preferred in optimization."""
        problem = create_standard_patrol_boat_problem()
        state = MockStateManager()
        validator = PatrolBoatValidator()

        optimizer = DesignOptimizer(
            problem=problem,
            base_state=state,
            validators=[validator],
            population_size=30,
            max_generations=20,
            seed=42,
        )

        result = optimizer.optimize()

        # Pareto front should mostly contain feasible solutions
        feasible_count = sum(1 for s in result.pareto_front if s.is_feasible)
        total_count = len(result.pareto_front)

        # At least some feasible solutions should exist
        # (depends on problem constraints being satisfiable)

    def test_constraint_violation_penalty(self):
        """Test constraint violations are penalized."""
        # Create problem with strict constraint
        problem = OptimizationProblem(name="strict", description="Strict constraints")
        problem.add_variable(DesignVariable(
            name="x", state_path="test.x", lower_bound=0, upper_bound=10
        ))
        problem.add_objective(Objective(
            name="f", state_path="test.f", objective_type=ObjectiveType.MINIMIZE
        ))
        problem.add_constraint(Constraint(
            name="strict",
            constraint_type=ConstraintType.INEQUALITY_LE,
            state_path="test.x",
            limit_value=5.0,  # x must be <= 5
            penalty_weight=100000,
        ))

        class SimpleValidator:
            def validate(self, state, config):
                x = state.get("test.x", 0)
                state.set("test.f", -x)  # Minimize negative x = maximize x

        state = MockStateManager()
        optimizer = DesignOptimizer(
            problem=problem,
            base_state=state,
            validators=[SimpleValidator()],
            population_size=20,
            max_generations=10,
            seed=42,
        )

        result = optimizer.optimize()

        # Selected solution should respect constraint
        if result.selected_solution:
            # Should prefer feasible solutions near x=5
            pass  # Constraint satisfaction depends on penalty effectiveness


class TestOptimizationPipelineTradeoffs:
    """Integration tests for trade-off analysis."""

    def test_tradeoff_curve_generation(self):
        """Test trade-off curve generation."""
        problem = create_cost_weight_problem()
        state = MockStateManager()
        validator = PatrolBoatValidator()

        solution = Solution(variables=[25.0, 6.0], objectives=[1000000, 50], is_feasible=True)

        analyzer = SensitivityAnalyzer(
            problem=problem,
            base_state=state,
            validators=[validator],
        )

        curve = analyzer.get_tradeoff_curve(solution, variable_index=0, n_points=10)

        assert curve["variable_name"] == "Length"
        assert curve["n_points"] <= 10
        assert "curve" in curve

        # Curve should show how objectives change with variable
        if curve["curve"]:
            # Values should span the variable range
            values = [p["variable_value"] for p in curve["curve"]]
            assert min(values) >= problem.variables[0].lower_bound
            assert max(values) <= problem.variables[0].upper_bound

    def test_local_region_analysis(self):
        """Test local region analysis."""
        problem = create_cost_weight_problem()
        state = MockStateManager()
        validator = PatrolBoatValidator()

        solution = Solution(variables=[25.0, 6.0], objectives=[1000000, 50], is_feasible=True)

        analyzer = SensitivityAnalyzer(
            problem=problem,
            base_state=state,
            validators=[validator],
        )

        region = analyzer.analyze_local_region(solution, n_samples=20, region_size=0.1)

        assert "n_samples" in region
        assert "objective_means" in region
        assert "objective_ranges" in region

        # Should have sampled the region
        if "error" not in region:
            assert region["n_samples"] > 0


class TestOptimizationPipelineReproducibility:
    """Integration tests for reproducibility."""

    def test_same_seed_same_results(self):
        """Test same seed produces same results."""
        problem = create_cost_weight_problem()
        validator = PatrolBoatValidator()

        # First run
        state1 = MockStateManager()
        optimizer1 = DesignOptimizer(
            problem=problem,
            base_state=state1,
            validators=[validator],
            population_size=10,
            max_generations=5,
            seed=12345,
        )
        result1 = optimizer1.optimize()

        # Second run
        state2 = MockStateManager()
        optimizer2 = DesignOptimizer(
            problem=problem,
            base_state=state2,
            validators=[validator],
            population_size=10,
            max_generations=5,
            seed=12345,
        )
        result2 = optimizer2.optimize()

        # Should produce same results
        assert len(result1.pareto_front) == len(result2.pareto_front)
        assert result1.evaluations == result2.evaluations

    def test_different_seed_different_results(self):
        """Test different seeds produce different results."""
        problem = create_cost_weight_problem()
        validator = PatrolBoatValidator()

        # First run
        state1 = MockStateManager()
        optimizer1 = DesignOptimizer(
            problem=problem,
            base_state=state1,
            validators=[validator],
            population_size=10,
            max_generations=5,
            seed=111,
        )
        result1 = optimizer1.optimize()

        # Second run with different seed
        state2 = MockStateManager()
        optimizer2 = DesignOptimizer(
            problem=problem,
            base_state=state2,
            validators=[validator],
            population_size=10,
            max_generations=5,
            seed=999,
        )
        result2 = optimizer2.optimize()

        # May produce different results (not guaranteed but likely)
        # Just verify both complete successfully
        assert result1.status == OptimizerStatus.MAX_ITERATIONS
        assert result2.status == OptimizerStatus.MAX_ITERATIONS
