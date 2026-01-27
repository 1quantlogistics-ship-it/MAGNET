import math

from magnet.optimization.surrogate_optimizer import MultiFidelitySurrogateOptimizer


class _QuadraticPhysics:
    """
    Simple deterministic objective: maximize -(x-2)^2
    """

    def evaluate(self, params, objective: str) -> float:
        x = float(params["x"])
        if objective == "score":
            return -(x - 2.0) ** 2
        raise KeyError(objective)


def test_surrogate_optimizer_respects_physics_budget_and_improves_best():
    opt = MultiFidelitySurrogateOptimizer(
        physics_evaluator=_QuadraticPhysics(),
        parameter_bounds={"x": (-5.0, 5.0)},
        objectives=["score"],
        initial_samples=10,
        high_fidelity_budget=25,
        seed=123,
    )

    res = opt.optimize(max_iterations=50)
    assert res.physics_evaluations_used <= 25
    assert "x" in res.best_params
    assert "score" in res.best_objectives
    assert math.isfinite(res.best_objectives["score"])

    # Should land near the true maximizer x=2.
    assert abs(float(res.best_params["x"]) - 2.0) < 1.0

