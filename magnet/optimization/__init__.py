"""
optimization/ - Design Optimization Module.

BRAVO OWNS THIS FILE.

Module 13 v1.1 - Design Optimization.

Provides multi-objective design optimization using NSGA-II,
Pareto analysis, and sensitivity analysis.

v1.1 Patches Applied:
    - P2: hull.freeboard_m (not hull.freeboard)
    - P3: StateManager.clone() for evaluations
"""

from .enums import (
    ObjectiveType,
    ConstraintType,
    OptimizerStatus,
    SelectionMethod,
)

from .schema import (
    DesignVariable,
    Objective,
    Constraint,
    OptimizationProblem,
    Solution,
    OptimizationResult,
)

from .problems import (
    create_standard_patrol_boat_problem,
    create_cost_weight_problem,
    create_speed_efficiency_problem,
    create_capacity_cost_problem,
)

from .optimizer import DesignOptimizer
from .pareto import ParetoAnalyzer, ParetoMetrics
from .sensitivity import SensitivityAnalyzer, SensitivityResult, VariableSensitivity

from .validator import (
    OptimizationValidator,
    OPTIMIZATION_DEFINITION,
    get_optimization_definition,
    register_optimization_validators,
)

__all__ = [
    # Enums
    "ObjectiveType",
    "ConstraintType",
    "OptimizerStatus",
    "SelectionMethod",
    # Schema
    "DesignVariable",
    "Objective",
    "Constraint",
    "OptimizationProblem",
    "Solution",
    "OptimizationResult",
    # Problem templates
    "create_standard_patrol_boat_problem",
    "create_cost_weight_problem",
    "create_speed_efficiency_problem",
    "create_capacity_cost_problem",
    # Optimizer
    "DesignOptimizer",
    # Analysis
    "ParetoAnalyzer",
    "ParetoMetrics",
    "SensitivityAnalyzer",
    "SensitivityResult",
    "VariableSensitivity",
    # Validator
    "OptimizationValidator",
    "OPTIMIZATION_DEFINITION",
    "get_optimization_definition",
    "register_optimization_validators",
]
