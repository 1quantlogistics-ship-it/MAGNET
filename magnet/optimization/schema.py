"""
optimization/schema.py - Optimization data structures.

BRAVO OWNS THIS FILE.

Module 13 v1.1 - Design Optimization data structures.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .enums import ObjectiveType, ConstraintType, OptimizerStatus, SelectionMethod

if TYPE_CHECKING:
    from ..core.state_manager import StateManager


@dataclass
class DesignVariable:
    """Design variable definition."""
    name: str
    state_path: str
    lower_bound: float
    upper_bound: float

    initial_value: Optional[float] = None
    step_size: Optional[float] = None
    description: str = ""

    def __post_init__(self):
        if self.initial_value is None:
            self.initial_value = (self.lower_bound + self.upper_bound) / 2
        if self.step_size is None:
            self.step_size = (self.upper_bound - self.lower_bound) / 20

    def normalize(self, value: float) -> float:
        """Normalize value to [0, 1]."""
        return (value - self.lower_bound) / (self.upper_bound - self.lower_bound)

    def denormalize(self, normalized: float) -> float:
        """Denormalize from [0, 1] to actual range."""
        return self.lower_bound + normalized * (self.upper_bound - self.lower_bound)

    def clamp(self, value: float) -> float:
        """Clamp value to bounds."""
        return max(self.lower_bound, min(self.upper_bound, value))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state_path": self.state_path,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "initial_value": self.initial_value,
            "step_size": self.step_size,
            "description": self.description,
        }


@dataclass
class Objective:
    """Optimization objective."""
    name: str
    state_path: str
    objective_type: ObjectiveType = ObjectiveType.MINIMIZE
    weight: float = 1.0
    target_value: Optional[float] = None
    description: str = ""

    def evaluate(self, state: "StateManager") -> float:
        """Evaluate objective from state."""
        value = state.get(self.state_path, 0)

        if self.target_value is not None:
            # Distance from target
            value = abs(value - self.target_value)

        if self.objective_type == ObjectiveType.MAXIMIZE:
            value = -value  # Convert to minimization

        return value * self.weight

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state_path": self.state_path,
            "type": self.objective_type.value,
            "weight": self.weight,
            "target_value": self.target_value,
            "description": self.description,
        }


@dataclass
class Constraint:
    """Optimization constraint."""
    name: str
    constraint_type: ConstraintType
    state_path: str
    limit_value: float

    penalty_weight: float = 1000.0
    tolerance: float = 0.001
    description: str = ""

    def evaluate(self, state: "StateManager") -> float:
        """
        Evaluate constraint violation.

        Returns:
            Violation amount (0 if satisfied)
        """
        value = state.get(self.state_path, 0)

        if self.constraint_type == ConstraintType.EQUALITY:
            violation = abs(value - self.limit_value)
        elif self.constraint_type == ConstraintType.INEQUALITY_LE:
            violation = max(0, value - self.limit_value)
        elif self.constraint_type == ConstraintType.INEQUALITY_GE:
            violation = max(0, self.limit_value - value)
        else:
            violation = 0

        return violation if violation > self.tolerance else 0

    def is_satisfied(self, state: "StateManager") -> bool:
        """Check if constraint is satisfied."""
        return self.evaluate(state) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.constraint_type.value,
            "state_path": self.state_path,
            "limit_value": self.limit_value,
            "penalty_weight": self.penalty_weight,
            "tolerance": self.tolerance,
            "description": self.description,
        }


@dataclass
class OptimizationProblem:
    """Complete optimization problem definition."""
    name: str
    description: str = ""

    variables: List[DesignVariable] = field(default_factory=list)
    objectives: List[Objective] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)

    @property
    def n_var(self) -> int:
        return len(self.variables)

    @property
    def n_obj(self) -> int:
        return len(self.objectives)

    @property
    def n_constr(self) -> int:
        return len(self.constraints)

    def add_variable(self, var: DesignVariable) -> None:
        self.variables.append(var)

    def add_objective(self, obj: Objective) -> None:
        self.objectives.append(obj)

    def add_constraint(self, constr: Constraint) -> None:
        self.constraints.append(constr)

    def get_bounds(self) -> tuple:
        """Get lower and upper bounds for all variables."""
        lower = [v.lower_bound for v in self.variables]
        upper = [v.upper_bound for v in self.variables]
        return lower, upper

    def get_initial_values(self) -> List[float]:
        """Get initial values for all variables."""
        return [v.initial_value for v in self.variables]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "n_var": self.n_var,
            "n_obj": self.n_obj,
            "n_constr": self.n_constr,
            "variables": [v.to_dict() for v in self.variables],
            "objectives": [o.to_dict() for o in self.objectives],
            "constraints": [c.to_dict() for c in self.constraints],
        }


@dataclass
class Solution:
    """Single optimization solution."""
    variables: List[float]
    objectives: List[float]
    constraint_violation: float = 0.0
    is_feasible: bool = True

    def dominates(self, other: "Solution") -> bool:
        """Check if this solution dominates another (for minimization)."""
        if not self.is_feasible:
            return False
        if not other.is_feasible:
            return True

        better_in_any = False
        for i in range(len(self.objectives)):
            if self.objectives[i] > other.objectives[i]:
                return False
            if self.objectives[i] < other.objectives[i]:
                better_in_any = True

        return better_in_any

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variables": [round(v, 6) for v in self.variables],
            "objectives": [round(o, 6) for o in self.objectives],
            "constraint_violation": round(self.constraint_violation, 6),
            "is_feasible": self.is_feasible,
        }


@dataclass
class OptimizationResult:
    """Optimization result."""
    problem_name: str
    status: OptimizerStatus

    # Pareto front (for multi-objective)
    pareto_front: List[Solution] = field(default_factory=list)

    # Selected solution
    selected_solution: Optional[Solution] = None
    selection_method: SelectionMethod = SelectionMethod.UTOPIA

    # Statistics
    iterations: int = 0
    evaluations: int = 0
    elapsed_time_s: float = 0.0

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def n_solutions(self) -> int:
        """Number of Pareto solutions."""
        return len(self.pareto_front)

    @property
    def is_successful(self) -> bool:
        """Check if optimization was successful."""
        return self.status in (OptimizerStatus.CONVERGED, OptimizerStatus.MAX_ITERATIONS)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "problem_name": self.problem_name,
            "status": self.status.value,
            "pareto_front": [s.to_dict() for s in self.pareto_front],
            "selected_solution": self.selected_solution.to_dict() if self.selected_solution else None,
            "selection_method": self.selection_method.value,
            "n_solutions": self.n_solutions,
            "statistics": {
                "iterations": self.iterations,
                "evaluations": self.evaluations,
                "elapsed_time_s": round(self.elapsed_time_s, 2),
            },
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
