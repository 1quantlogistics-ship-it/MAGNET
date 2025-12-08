"""
tests/unit/test_optimization_problems.py - Tests for optimization problem templates.

BRAVO OWNS THIS FILE.

Tests for Module 13 v1.1 - Standard optimization problem templates.
"""

import pytest
from magnet.optimization import (
    create_standard_patrol_boat_problem,
    create_cost_weight_problem,
    create_speed_efficiency_problem,
    create_capacity_cost_problem,
    ObjectiveType,
    ConstraintType,
)


class TestStandardPatrolBoatProblem:
    """Tests for create_standard_patrol_boat_problem."""

    def test_problem_creation(self):
        """Test problem is created successfully."""
        problem = create_standard_patrol_boat_problem()
        assert problem.name == "patrol_boat_optimization"
        assert "patrol boat" in problem.description.lower()

    def test_has_four_variables(self):
        """Test problem has correct number of variables."""
        problem = create_standard_patrol_boat_problem()
        assert problem.n_var == 4

    def test_variable_hull_length(self):
        """Test Hull Length variable configuration."""
        problem = create_standard_patrol_boat_problem()
        var = next(v for v in problem.variables if v.state_path == "hull.lwl")
        assert var.name == "Hull Length"
        assert var.lower_bound == 15.0
        assert var.upper_bound == 35.0

    def test_variable_hull_beam(self):
        """Test Hull Beam variable configuration."""
        problem = create_standard_patrol_boat_problem()
        var = next(v for v in problem.variables if v.state_path == "hull.beam")
        assert var.name == "Hull Beam"
        assert var.lower_bound == 4.0
        assert var.upper_bound == 8.0

    def test_variable_hull_depth(self):
        """Test Hull Depth variable configuration."""
        problem = create_standard_patrol_boat_problem()
        var = next(v for v in problem.variables if v.state_path == "hull.depth")
        assert var.name == "Hull Depth"
        assert var.lower_bound == 2.0
        assert var.upper_bound == 4.0

    def test_variable_installed_power(self):
        """Test Installed Power variable configuration."""
        problem = create_standard_patrol_boat_problem()
        var = next(v for v in problem.variables if v.state_path == "propulsion.installed_power_kw")
        assert var.name == "Installed Power"
        assert var.lower_bound == 500
        assert var.upper_bound == 3000

    def test_has_two_objectives(self):
        """Test problem has correct number of objectives."""
        problem = create_standard_patrol_boat_problem()
        assert problem.n_obj == 2

    def test_objective_cost(self):
        """Test Cost objective configuration."""
        problem = create_standard_patrol_boat_problem()
        obj = next(o for o in problem.objectives if o.state_path == "cost.total_price")
        assert obj.name == "Cost"
        assert obj.objective_type == ObjectiveType.MINIMIZE
        assert obj.weight == 1.0

    def test_objective_weight(self):
        """Test Weight objective configuration."""
        problem = create_standard_patrol_boat_problem()
        obj = next(o for o in problem.objectives if o.state_path == "weight.lightship_mt")
        assert obj.name == "Weight"
        assert obj.objective_type == ObjectiveType.MINIMIZE
        assert obj.weight == 1.0

    def test_has_three_constraints(self):
        """Test problem has correct number of constraints."""
        problem = create_standard_patrol_boat_problem()
        assert problem.n_constr == 3

    def test_constraint_minimum_gm(self):
        """Test Minimum GM constraint configuration."""
        problem = create_standard_patrol_boat_problem()
        constr = next(c for c in problem.constraints if c.state_path == "stability.gm_m")
        assert constr.name == "Minimum GM"
        assert constr.constraint_type == ConstraintType.INEQUALITY_GE
        assert constr.limit_value == 0.35
        assert constr.penalty_weight == 10000

    def test_constraint_minimum_freeboard_v11_p2(self):
        """Test Minimum Freeboard constraint - v1.1 P2 uses hull.freeboard_m."""
        problem = create_standard_patrol_boat_problem()
        constr = next(c for c in problem.constraints if "freeboard" in c.name.lower())
        # v1.1 P2: Must use hull.freeboard_m not hull.freeboard
        assert constr.state_path == "hull.freeboard_m"
        assert constr.constraint_type == ConstraintType.INEQUALITY_GE
        assert constr.limit_value == 0.50
        assert constr.penalty_weight == 10000

    def test_constraint_compliance(self):
        """Test Compliance constraint configuration."""
        problem = create_standard_patrol_boat_problem()
        constr = next(c for c in problem.constraints if c.state_path == "compliance.fail_count")
        assert constr.name == "Compliance"
        assert constr.constraint_type == ConstraintType.INEQUALITY_LE
        assert constr.limit_value == 0
        assert constr.penalty_weight == 100000

    def test_get_bounds(self):
        """Test bounds extraction."""
        problem = create_standard_patrol_boat_problem()
        lower, upper = problem.get_bounds()
        assert len(lower) == 4
        assert len(upper) == 4
        assert lower[0] == 15.0  # LWL lower
        assert upper[0] == 35.0  # LWL upper

    def test_to_dict(self):
        """Test dictionary serialization."""
        problem = create_standard_patrol_boat_problem()
        data = problem.to_dict()
        assert data["name"] == "patrol_boat_optimization"
        assert data["n_var"] == 4
        assert data["n_obj"] == 2
        assert data["n_constr"] == 3
        assert len(data["variables"]) == 4
        assert len(data["objectives"]) == 2
        assert len(data["constraints"]) == 3


class TestCostWeightProblem:
    """Tests for create_cost_weight_problem."""

    def test_default_problem(self):
        """Test default problem configuration."""
        problem = create_cost_weight_problem()
        assert problem.name == "cost_weight_tradeoff"
        assert problem.n_var == 2
        assert problem.n_obj == 2
        assert problem.n_constr == 0

    def test_custom_lwl_range(self):
        """Test custom LWL range."""
        problem = create_cost_weight_problem(lwl_range=(20, 40))
        var = next(v for v in problem.variables if v.state_path == "hull.lwl")
        assert var.lower_bound == 20
        assert var.upper_bound == 40

    def test_custom_beam_range(self):
        """Test custom beam range."""
        problem = create_cost_weight_problem(beam_range=(5, 10))
        var = next(v for v in problem.variables if v.state_path == "hull.beam")
        assert var.lower_bound == 5
        assert var.upper_bound == 10

    def test_objectives(self):
        """Test objectives configuration."""
        problem = create_cost_weight_problem()
        obj_paths = [o.state_path for o in problem.objectives]
        assert "cost.total_price" in obj_paths
        assert "weight.lightship_mt" in obj_paths


class TestSpeedEfficiencyProblem:
    """Tests for create_speed_efficiency_problem."""

    def test_problem_creation(self):
        """Test problem is created successfully."""
        problem = create_speed_efficiency_problem()
        assert problem.name == "speed_efficiency"
        assert problem.n_var == 2
        assert problem.n_obj == 2

    def test_variable_hull_length(self):
        """Test Hull Length variable configuration."""
        problem = create_speed_efficiency_problem()
        var = next(v for v in problem.variables if v.state_path == "hull.lwl")
        assert var.lower_bound == 20.0
        assert var.upper_bound == 40.0

    def test_variable_installed_power(self):
        """Test Installed Power variable configuration."""
        problem = create_speed_efficiency_problem()
        var = next(v for v in problem.variables if v.state_path == "propulsion.installed_power_kw")
        assert var.lower_bound == 500
        assert var.upper_bound == 5000

    def test_objective_speed_maximize(self):
        """Test Speed objective is MAXIMIZE."""
        problem = create_speed_efficiency_problem()
        obj = next(o for o in problem.objectives if o.state_path == "mission.max_speed_kts")
        assert obj.name == "Speed"
        assert obj.objective_type == ObjectiveType.MAXIMIZE

    def test_objective_fuel_minimize(self):
        """Test Fuel Consumption objective is MINIMIZE."""
        problem = create_speed_efficiency_problem()
        obj = next(o for o in problem.objectives if o.state_path == "propulsion.fuel_consumption_lph")
        assert obj.name == "Fuel Consumption"
        assert obj.objective_type == ObjectiveType.MINIMIZE


class TestCapacityCostProblem:
    """Tests for create_capacity_cost_problem."""

    def test_default_problem(self):
        """Test default problem configuration."""
        problem = create_capacity_cost_problem()
        assert problem.name == "capacity_cost"
        assert problem.n_var == 3
        assert problem.n_obj == 2
        # No constraints by default (min_pax=0, min_crew=2 adds crew constraint)
        assert problem.n_constr == 1  # min_crew=2 default

    def test_no_constraints(self):
        """Test with no constraints."""
        problem = create_capacity_cost_problem(min_pax=0, min_crew=0)
        assert problem.n_constr == 0

    def test_with_min_passengers(self):
        """Test with minimum passengers constraint."""
        problem = create_capacity_cost_problem(min_pax=10)
        assert problem.n_constr == 2  # min_pax and default min_crew
        constr = next(c for c in problem.constraints if c.state_path == "mission.passengers")
        assert constr.limit_value == 10
        assert constr.constraint_type == ConstraintType.INEQUALITY_GE

    def test_with_min_crew(self):
        """Test with minimum crew constraint."""
        problem = create_capacity_cost_problem(min_crew=5)
        constr = next(c for c in problem.constraints if c.state_path == "mission.crew_size")
        assert constr.limit_value == 5
        assert constr.constraint_type == ConstraintType.INEQUALITY_GE

    def test_variables(self):
        """Test variable configuration."""
        problem = create_capacity_cost_problem()
        var_paths = [v.state_path for v in problem.variables]
        assert "hull.lwl" in var_paths
        assert "hull.beam" in var_paths
        assert "hull.depth" in var_paths

    def test_objectives(self):
        """Test objectives configuration."""
        problem = create_capacity_cost_problem()
        obj_names = [o.name for o in problem.objectives]
        assert "Cost" in obj_names
        assert "Deck Area" in obj_names

    def test_deck_area_maximize(self):
        """Test Deck Area objective is MAXIMIZE."""
        problem = create_capacity_cost_problem()
        obj = next(o for o in problem.objectives if o.state_path == "hull.deck_area_m2")
        assert obj.objective_type == ObjectiveType.MAXIMIZE
