import numpy as np

from magnet.optimization.probabilistic_optimizer import (
    ChanceConstraint,
    ProbabilisticOptimizer,
)


class _ParabolaModel:
    """
    mean(x) = -(x-2)^2, std(x)=0.1 (constant)
    """

    def predict(self, X: np.ndarray):
        x = np.asarray(X, dtype=float).reshape(-1)
        mean = -((x - 2.0) ** 2)
        std = np.full_like(mean, 0.1)
        return mean, std


class _LinearConstraintModel:
    """
    mean(x)=x, std=0.5
    """

    def predict(self, X: np.ndarray):
        x = np.asarray(X, dtype=float).reshape(-1)
        mean = x
        std = np.full_like(mean, 0.5)
        return mean, std


def test_probabilistic_optimizer_prefers_near_optimum_under_robust_score():
    opt = ProbabilisticOptimizer(
        parameter_bounds={"x": (-5.0, 5.0)},
        objective_name="score",
        objective_model=_ParabolaModel(),
        robustness_k=1.0,
        seed=123,
    )
    res = opt.optimize(n_candidates=2000)
    assert abs(res.design["x"] - 2.0) < 0.5


def test_probabilistic_optimizer_enforces_chance_constraint():
    # Chance constraint: P(x >= 1.0) >= 0.9 with std=0.5 forces mean well above 1.0.
    cc = ChanceConstraint(
        name="x_ge_1",
        predictor=_LinearConstraintModel(),
        threshold=1.0,
        direction="ge",
        min_probability=0.9,
    )
    opt = ProbabilisticOptimizer(
        parameter_bounds={"x": (-5.0, 5.0)},
        objective_name="score",
        objective_model=_ParabolaModel(),
        chance_constraints=[cc],
        robustness_k=1.0,
        seed=7,
    )
    res = opt.optimize(n_candidates=4000)
    assert res.design["x"] > 1.0
    assert "x_ge_1" in (res.constraint_satisfaction_probability or {})
    assert res.constraint_satisfaction_probability["x_ge_1"] >= 0.9

