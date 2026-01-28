"""
Emergency stabilization tests for sensitivity isolation.

Task IDs:
- E0.1 (Emergency: Fail-fast state isolation)
- T5.6 (Fix State Leakage)
"""

from __future__ import annotations

import pytest

from magnet.optimization.schema import DesignVariable, Objective, OptimizationProblem, Solution
from magnet.optimization.sensitivity import SensitivityAnalyzer, UnsafeStateEvaluationError


class _StateWithoutClone:
    def get(self, path: str, default=None):
        return default

    def set(self, path: str, value, source: str):
        raise AssertionError("set() should never be called without clone()")


class _StateCloneReturnsSelf(_StateWithoutClone):
    def clone(self):
        return self


class _StateCloneOk:
    def __init__(self):
        self._data = {}

    def clone(self):
        c = _StateCloneOk()
        c._data = dict(self._data)
        return c

    def get(self, path: str, default=None):
        return self._data.get(path, default)

    def set(self, path: str, value, source: str):
        self._data[path] = value


def _make_problem() -> OptimizationProblem:
    return OptimizationProblem(
        name="test_problem",
        variables=[
            DesignVariable(
                name="beam",
                state_path="hull.beam_m",
                lower_bound=1.0,
                upper_bound=10.0,
            )
        ],
        objectives=[
            Objective(
                name="disp",
                state_path="physics.displacement_mt",
            )
        ],
    )


def _make_solution(problem: OptimizationProblem) -> Solution:
    return Solution(
        variables=[problem.variables[0].initial_value],
        objectives=[0.0],
    )


def test_sensitivity_fails_fast_without_clone():
    problem = _make_problem()
    sol = _make_solution(problem)
    analyzer = SensitivityAnalyzer(problem=problem, base_state=_StateWithoutClone())

    with pytest.raises(UnsafeStateEvaluationError):
        analyzer.analyze(sol)


def test_sensitivity_fails_fast_if_clone_returns_self():
    problem = _make_problem()
    sol = _make_solution(problem)
    analyzer = SensitivityAnalyzer(problem=problem, base_state=_StateCloneReturnsSelf())

    with pytest.raises(UnsafeStateEvaluationError):
        analyzer.analyze(sol)


def test_sensitivity_uses_clone_and_does_not_mutate_base_state():
    problem = _make_problem()
    sol = _make_solution(problem)
    base = _StateCloneOk()
    analyzer = SensitivityAnalyzer(problem=problem, base_state=base)

    analyzer.analyze(sol)

    # Base state should remain unchanged because evaluation uses clones.
    assert base.get("hull.beam_m") is None
