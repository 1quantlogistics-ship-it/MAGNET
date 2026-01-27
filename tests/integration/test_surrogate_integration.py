from magnet.optimization.hybrid_optimizer import HybridOptimizer, OptimizationRequest


def test_surrogate_integration_fast_mode_validates_final_design():
    """
    TM.7: Integration smoke test for surrogate->physics->kernel validation pipeline.
    """

    # physics objective: y = x (target y=5)
    def physics_eval(params, objective):
        return float(params["x"])

    # kernel validator: accept only x within [0,10]
    def kernel_validate(params):
        x = float(params["x"])
        return 0.0 <= x <= 10.0

    opt = HybridOptimizer(parameter_bounds={"x": (0.0, 10.0)}, physics_evaluate=physics_eval, kernel_validate=kernel_validate, seed=42)
    res = opt.optimize(OptimizationRequest(targets={"y": 5.0}, fidelity="fast", surrogate_candidates=200, physics_validate_top_k=5))
    assert res.validated_by_kernel is True

