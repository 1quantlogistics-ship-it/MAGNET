"""
optimization/enums.py - Optimization enumerations.

BRAVO OWNS THIS FILE.

Module 13 v1.1 - Design Optimization enumerations.
"""

from enum import Enum


class ObjectiveType(Enum):
    """Objective function types."""
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


class ConstraintType(Enum):
    """Constraint types."""
    EQUALITY = "equality"              # g(x) = 0
    INEQUALITY_LE = "inequality_le"    # g(x) <= 0
    INEQUALITY_GE = "inequality_ge"    # g(x) >= 0


class OptimizerStatus(Enum):
    """Optimizer execution status."""
    PENDING = "pending"
    RUNNING = "running"
    CONVERGED = "converged"
    MAX_ITERATIONS = "max_iterations"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SelectionMethod(Enum):
    """Solution selection methods."""
    UTOPIA = "utopia"            # Closest to utopia point
    KNEE = "knee"                # Maximum curvature on Pareto front
    WEIGHTED = "weighted"        # Weighted sum of objectives
    MANUAL = "manual"            # User-selected
