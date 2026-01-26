import numpy as np

from magnet.core.state_concurrency import ConcurrentStateManager
from magnet.core.state_manager import StateManager
from magnet.kernel.gradient_estimator import GradientConfig, SafeGradientEstimator


def test_safe_gradient_estimator_matches_known_derivative():
    sm = StateManager()
    mgr = ConcurrentStateManager(sm)

    with mgr.write_transaction(mutator_id="init") as w:
        w.set("hull.beam", 5.0, "test")
        w.set("hull.draft", 1.2, "test")

    def evaluator(state: StateManager, objectives):
        beam = float(state.get("hull.beam", 0.0) or 0.0)
        draft = float(state.get("hull.draft", 0.0) or 0.0)
        # objective: f = beam^2 + 3*draft
        return {"f": beam * beam + 3.0 * draft}

    est = SafeGradientEstimator(
        state_manager=mgr,
        evaluator=evaluator,
        config=GradientConfig(step_size=1e-4),
    )

    J = est.compute_jacobian(parameters=["hull.beam", "hull.draft"], objectives=["f"])
    assert J.shape == (1, 2)

    # df/dbeam = 2*beam = 10, df/ddraft = 3
    np.testing.assert_allclose(J[0, 0], 10.0, rtol=1e-3, atol=1e-3)
    np.testing.assert_allclose(J[0, 1], 3.0, rtol=1e-3, atol=1e-3)

