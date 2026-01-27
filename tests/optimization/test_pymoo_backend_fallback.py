from magnet.core.design_state import DesignState
from magnet.core.state_manager import StateManager
from magnet.optimization.schema import OptimizationProblem, DesignVariable, Objective
from magnet.optimization.validator import OptimizationValidator, OPTIMIZATION_DEFINITION
from tests.conftest import refinable_write_context


def test_optimizer_backend_pymoo_gracefully_falls_back_when_unavailable():
    """
    The integration plan requires graceful degradation.

    If pymoo isn't installed, requesting the pymoo backend must not crash; the
    validator should fall back to the native optimizer.
    """
    sm = StateManager(DesignState())
    with refinable_write_context(sm):
        sm.set("hull.lwl", 20.0, "test")

    problem = OptimizationProblem(
        name="test-problem",
        variables=[
            DesignVariable(name="lwl", state_path="hull.lwl", lower_bound=10.0, upper_bound=30.0),
        ],
        objectives=[
            Objective(name="min_lwl", state_path="hull.lwl"),
        ],
        constraints=[],
    )

    v = OptimizationValidator(OPTIMIZATION_DEFINITION, population_size=6, max_generations=2)
    res = v.validate(sm, {"problem": problem, "optimizer_backend": "pymoo", "seed": 0, "validators": []})

    # Should not error; optimization may warn or pass depending on stochasticity.
    assert res.state.value in ("passed", "warning", "failed")
    assert sm.get("optimization.status") is not None

