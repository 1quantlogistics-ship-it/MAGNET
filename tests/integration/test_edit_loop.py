"""
T8.3: Edit Loop Test.

This is an offline test of the "iterative edit loop" primitives:
- observable registry provides measurable/controllable variables
- safe gradients are computed from snapshots
- coordinate executor applies atomic optimizer steps
"""

from magnet.core.state_concurrency import ConcurrentStateManager
from magnet.core.state_manager import StateManager
from magnet.kernel.coordinate_executor import CoordinateExecutor, CoordinateConfig
from magnet.kernel.observable_registry import ObservableRegistry, ObservableSpec


def test_edit_loop_coordinate_executor_can_hit_simple_target():
    # Canonical state with a single controllable parameter.
    sm = StateManager()
    tx = sm.begin_transaction()
    # Use a path that is guaranteed to exist in the schema (`metadata` is a dict),
    # so patch/set will not silently no-op during optimization steps.
    sm.set("metadata.test_x", 0.0, "test/edit_loop")
    sm.commit_transaction(tx)

    csm = ConcurrentStateManager(sm)

    # Registry: `metadata.test_x` is both controllable and measurable (identity).
    registry = ObservableRegistry()
    registry.register(
        ObservableSpec(
            observable_id="metadata.test_x",
            measurable=True,
            controllable=True,
            control_mode="DIRECT",
            unit="",
            description="Synthetic scalar parameter for edit loop integration test.",
            tolerance=1e-6,
        ),
        measure_fn=lambda st: float(st.get("metadata.test_x", 0.0) or 0.0),
        depends_on=["metadata.test_x"],
    )

    ex = CoordinateExecutor(
        manager=csm,
        registry=registry,
        config=CoordinateConfig(max_iterations=6, damping=1e-6),
    )
    res = ex.optimize(targets={"metadata.test_x": 1.0}, adjustable=["metadata.test_x"])
    assert res.success is True

    # Verify canonical state was updated near target.
    assert abs(float(sm.get("metadata.test_x")) - 1.0) < 1e-3

