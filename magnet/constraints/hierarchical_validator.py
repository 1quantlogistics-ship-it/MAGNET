"""
magnet/constraints/hierarchical_validator.py

TM.3: Hierarchical constraint system (fast-to-slow pyramid).

Key idea:
- Most candidates fail cheap constraints.
- Evaluate GEOMETRIC constraints for all candidates.
- Evaluate SIMPLIFIED constraints only for candidates that pass geometric.
- Evaluate FULL_PHYSICS constraints only for candidates that pass simplified.

This module is intentionally domain-agnostic: constraints are supplied as callables
over a `design: dict` (typically a parameter dict or a serialized state view).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional


class ConstraintLevel(Enum):
    """Constraint evaluation cost levels."""

    GEOMETRIC = auto()  # milliseconds
    SIMPLIFIED = auto()  # seconds
    FULL_PHYSICS = auto()  # minutes


@dataclass
class ConstraintResult:
    """Result of a single constraint evaluation."""

    satisfied: bool
    value: float
    threshold: float
    margin: float

    confidence: float = 1.0
    assumptions: Optional[List[str]] = None

    parameter_sensitivities: Optional[dict] = None
    direction_hint: Optional[str] = None

    constraint_name: str = ""
    level: ConstraintLevel = ConstraintLevel.GEOMETRIC
    evaluation_time_ms: float = 0.0


@dataclass
class Constraint:
    """
    Cost-aware constraint wrapper.
    """

    name: str
    level: ConstraintLevel
    evaluate_fn: Callable[[dict], ConstraintResult]
    description: str = ""
    failure_guidance: str = ""

    def evaluate(self, design: dict) -> ConstraintResult:
        import time

        start = time.time()
        res = self.evaluate_fn(design)
        res.evaluation_time_ms = (time.time() - start) * 1000.0
        res.constraint_name = self.name
        res.level = self.level
        return res


@dataclass
class ValidationStatistics:
    geometric_evaluations: int = 0
    simplified_evaluations: int = 0
    full_physics_evaluations: int = 0

    geometric_failures: int = 0
    simplified_failures: int = 0
    full_physics_failures: int = 0


@dataclass
class HierarchicalValidationResult:
    valid: bool
    failed_level: Optional[ConstraintLevel] = None
    results: Dict[ConstraintLevel, List[ConstraintResult]] = field(default_factory=dict)
    statistics: ValidationStatistics = field(default_factory=ValidationStatistics)


class HierarchicalValidator:
    def __init__(self) -> None:
        self._constraints: Dict[ConstraintLevel, List[Constraint]] = {
            ConstraintLevel.GEOMETRIC: [],
            ConstraintLevel.SIMPLIFIED: [],
            ConstraintLevel.FULL_PHYSICS: [],
        }
        self._statistics = ValidationStatistics()

    def add_constraint(self, constraint: Constraint) -> None:
        self._constraints[constraint.level].append(constraint)

    def validate(self, design: dict, *, stop_on_failure: bool = True) -> HierarchicalValidationResult:
        results: Dict[ConstraintLevel, List[ConstraintResult]] = {}

        # Level 1
        geo = self._evaluate_level(design, ConstraintLevel.GEOMETRIC)
        results[ConstraintLevel.GEOMETRIC] = geo
        self._statistics.geometric_evaluations += 1
        if stop_on_failure and not all(r.satisfied for r in geo):
            self._statistics.geometric_failures += 1
            return HierarchicalValidationResult(
                valid=False,
                failed_level=ConstraintLevel.GEOMETRIC,
                results=results,
                statistics=self._statistics,
            )

        # Level 2
        simp = self._evaluate_level(design, ConstraintLevel.SIMPLIFIED)
        results[ConstraintLevel.SIMPLIFIED] = simp
        self._statistics.simplified_evaluations += 1
        if stop_on_failure and not all(r.satisfied for r in simp):
            self._statistics.simplified_failures += 1
            return HierarchicalValidationResult(
                valid=False,
                failed_level=ConstraintLevel.SIMPLIFIED,
                results=results,
                statistics=self._statistics,
            )

        # Level 3
        full = self._evaluate_level(design, ConstraintLevel.FULL_PHYSICS)
        results[ConstraintLevel.FULL_PHYSICS] = full
        self._statistics.full_physics_evaluations += 1
        if stop_on_failure and not all(r.satisfied for r in full):
            self._statistics.full_physics_failures += 1
            return HierarchicalValidationResult(
                valid=False,
                failed_level=ConstraintLevel.FULL_PHYSICS,
                results=results,
                statistics=self._statistics,
            )

        return HierarchicalValidationResult(valid=True, results=results, statistics=self._statistics)

    def _evaluate_level(self, design: dict, level: ConstraintLevel) -> List[ConstraintResult]:
        out: List[ConstraintResult] = []
        for c in self._constraints[level]:
            out.append(c.evaluate(design))
        return out

