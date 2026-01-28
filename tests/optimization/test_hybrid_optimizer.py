from magnet.optimization.hybrid_optimizer import (
    HybridOptimizer,
    OptimizationRequest,
)


def test_fidelity_fast_still_kernel_validates_final():
    validated = {"count": 0}

    def physics_eval(params, objective):
        # objective = "y" -> y = x
        return float(params["x"])

    def kernel_validate(params):
        validated["count"] += 1
        return True

    opt = HybridOptimizer(parameter_bounds={"x": (0.0, 10.0)}, physics_evaluate=physics_eval, kernel_validate=kernel_validate, seed=0)
    res = opt.optimize(OptimizationRequest(targets={"y": 5.0}, fidelity="fast"))
    assert res.validated_by_kernel is True
    assert validated["count"] == 1


def test_fidelity_full_runs_physics_only_and_returns_report():
    def physics_eval(params, objective):
        return float(params["x"])

    def kernel_validate(params):
        return True

    opt = HybridOptimizer(parameter_bounds={"x": (0.0, 10.0)}, physics_evaluate=physics_eval, kernel_validate=kernel_validate, seed=1)
    res = opt.optimize(
        OptimizationRequest(
            targets={"y": 7.0},
            fidelity="full",
            surrogate_candidates=200,
            return_detailed_report=True,
        )
    )
    assert res.fidelity_used == "full"
    assert res.validated_by_kernel is True
    assert res.report is not None
    assert res.report.get("mode") == "physics_only"


def test_user_request_for_full_overrides_surrogate_confidence():
    calls = {"physics": 0}

    def physics_eval(params, objective):
        calls["physics"] += 1
        return float(params["x"])

    def kernel_validate(params):
        return True

    opt = HybridOptimizer(parameter_bounds={"x": (0.0, 10.0)}, physics_evaluate=physics_eval, kernel_validate=kernel_validate, seed=2)
    res = opt.optimize(OptimizationRequest(targets={"y": 3.0}, fidelity="full", surrogate_candidates=50, return_detailed_report=True))
    assert res.fidelity_used == "full"
    assert calls["physics"] > 0
    assert res.report and res.report.get("mode") == "physics_only"

