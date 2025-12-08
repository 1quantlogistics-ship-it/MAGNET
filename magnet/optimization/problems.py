"""
optimization/problems.py - Standard optimization problem templates.

BRAVO OWNS THIS FILE.

Module 13 v1.1 - Standard optimization problem templates.

v1.1 PATCH P2: hull.freeboard_m (not hull.freeboard)
"""

from .schema import OptimizationProblem, DesignVariable, Objective, Constraint
from .enums import ObjectiveType, ConstraintType


def create_standard_patrol_boat_problem() -> OptimizationProblem:
    """
    Create standard patrol boat optimization problem.

    Objectives:
    - Minimize cost.total_price
    - Minimize weight.lightship_mt

    Constraints:
    - GM >= 0.35m
    - Freeboard >= 0.50m (v1.1 P2: hull.freeboard_m)
    - Compliance pass
    """
    problem = OptimizationProblem(
        name="patrol_boat_optimization",
        description="Multi-objective patrol boat design optimization",
    )

    # Design Variables
    problem.add_variable(DesignVariable(
        name="Hull Length",
        state_path="hull.lwl",
        lower_bound=15.0,
        upper_bound=35.0,
        description="Length waterline (m)",
    ))

    problem.add_variable(DesignVariable(
        name="Hull Beam",
        state_path="hull.beam",
        lower_bound=4.0,
        upper_bound=8.0,
        description="Beam (m)",
    ))

    problem.add_variable(DesignVariable(
        name="Hull Depth",
        state_path="hull.depth",
        lower_bound=2.0,
        upper_bound=4.0,
        description="Depth (m)",
    ))

    problem.add_variable(DesignVariable(
        name="Installed Power",
        state_path="propulsion.installed_power_kw",
        lower_bound=500,
        upper_bound=3000,
        description="Total installed power (kW)",
    ))

    # Objectives
    problem.add_objective(Objective(
        name="Cost",
        state_path="cost.total_price",
        objective_type=ObjectiveType.MINIMIZE,
        weight=1.0,
        description="Total vessel price",
    ))

    problem.add_objective(Objective(
        name="Weight",
        state_path="weight.lightship_mt",
        objective_type=ObjectiveType.MINIMIZE,
        weight=1.0,
        description="Lightship weight",
    ))

    # Constraints
    problem.add_constraint(Constraint(
        name="Minimum GM",
        constraint_type=ConstraintType.INEQUALITY_GE,
        state_path="stability.gm_m",
        limit_value=0.35,
        penalty_weight=10000,
        description="GM >= 0.35m",
    ))

    # v1.1 PATCH P2: Correct path is hull.freeboard_m
    problem.add_constraint(Constraint(
        name="Minimum Freeboard",
        constraint_type=ConstraintType.INEQUALITY_GE,
        state_path="hull.freeboard_m",  # P2 FIX: was hull.freeboard
        limit_value=0.50,
        penalty_weight=10000,
        description="Freeboard >= 0.50m",
    ))

    problem.add_constraint(Constraint(
        name="Compliance",
        constraint_type=ConstraintType.INEQUALITY_LE,
        state_path="compliance.fail_count",
        limit_value=0,
        penalty_weight=100000,
        description="No compliance failures",
    ))

    return problem


def create_cost_weight_problem(
    lwl_range: tuple = (15, 35),
    beam_range: tuple = (4, 8),
) -> OptimizationProblem:
    """
    Create simple cost-weight trade-off problem.

    Args:
        lwl_range: (min, max) for LWL
        beam_range: (min, max) for beam
    """
    problem = OptimizationProblem(
        name="cost_weight_tradeoff",
        description="Cost vs weight optimization",
    )

    # Variables
    problem.add_variable(DesignVariable(
        name="Length",
        state_path="hull.lwl",
        lower_bound=lwl_range[0],
        upper_bound=lwl_range[1],
    ))

    problem.add_variable(DesignVariable(
        name="Beam",
        state_path="hull.beam",
        lower_bound=beam_range[0],
        upper_bound=beam_range[1],
    ))

    # Objectives
    problem.add_objective(Objective(
        name="Cost",
        state_path="cost.total_price",
        objective_type=ObjectiveType.MINIMIZE,
    ))

    problem.add_objective(Objective(
        name="Weight",
        state_path="weight.lightship_mt",
        objective_type=ObjectiveType.MINIMIZE,
    ))

    return problem


def create_speed_efficiency_problem() -> OptimizationProblem:
    """Create speed vs efficiency optimization problem."""
    problem = OptimizationProblem(
        name="speed_efficiency",
        description="Speed vs fuel efficiency optimization",
    )

    problem.add_variable(DesignVariable(
        name="Hull Length",
        state_path="hull.lwl",
        lower_bound=20.0,
        upper_bound=40.0,
    ))

    problem.add_variable(DesignVariable(
        name="Installed Power",
        state_path="propulsion.installed_power_kw",
        lower_bound=500,
        upper_bound=5000,
    ))

    problem.add_objective(Objective(
        name="Speed",
        state_path="mission.max_speed_kts",
        objective_type=ObjectiveType.MAXIMIZE,
        description="Maximum speed",
    ))

    problem.add_objective(Objective(
        name="Fuel Consumption",
        state_path="propulsion.fuel_consumption_lph",
        objective_type=ObjectiveType.MINIMIZE,
        description="Fuel consumption at cruise",
    ))

    return problem


def create_capacity_cost_problem(
    min_pax: int = 0,
    min_crew: int = 2,
) -> OptimizationProblem:
    """Create capacity vs cost optimization problem."""
    problem = OptimizationProblem(
        name="capacity_cost",
        description="Capacity vs cost optimization",
    )

    problem.add_variable(DesignVariable(
        name="Hull Length",
        state_path="hull.lwl",
        lower_bound=15.0,
        upper_bound=50.0,
    ))

    problem.add_variable(DesignVariable(
        name="Hull Beam",
        state_path="hull.beam",
        lower_bound=4.0,
        upper_bound=12.0,
    ))

    problem.add_variable(DesignVariable(
        name="Hull Depth",
        state_path="hull.depth",
        lower_bound=2.0,
        upper_bound=5.0,
    ))

    problem.add_objective(Objective(
        name="Cost",
        state_path="cost.total_price",
        objective_type=ObjectiveType.MINIMIZE,
    ))

    problem.add_objective(Objective(
        name="Deck Area",
        state_path="hull.deck_area_m2",
        objective_type=ObjectiveType.MAXIMIZE,
        description="Available deck area",
    ))

    if min_pax > 0:
        problem.add_constraint(Constraint(
            name="Minimum Passengers",
            constraint_type=ConstraintType.INEQUALITY_GE,
            state_path="mission.passengers",
            limit_value=min_pax,
            description=f"Passengers >= {min_pax}",
        ))

    if min_crew > 0:
        problem.add_constraint(Constraint(
            name="Minimum Crew",
            constraint_type=ConstraintType.INEQUALITY_GE,
            state_path="mission.crew_size",
            limit_value=min_crew,
            description=f"Crew >= {min_crew}",
        ))

    return problem
