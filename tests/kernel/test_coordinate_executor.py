import ast
import math

import numpy as np

from magnet.core.state_concurrency import ConcurrentStateManager
from magnet.core.state_manager import StateManager
from magnet.kernel.coordinate_executor import CoordinateConfig, CoordinateExecutor
from magnet.kernel.observable_registry import ObservableRegistry, ObservableSpec


def test_coordinate_executor_has_no_domain_imports():
    with open("magnet/kernel/coordinate_executor.py", "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    forbidden_imports = [
        "hull_gen",
        "naval",
        "hydrostatics",
        "stability",
        "resistance",
        "physics",
    ]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for forbidden in forbidden_imports:
                    assert forbidden not in alias.name, f"Optimizer imports domain module: {alias.name}"
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for forbidden in forbidden_imports:
                assert forbidden not in mod, f"Optimizer imports domain module: {mod}"


def test_coordinate_executor_converges_on_simple_quadratic():
    sm = StateManager()
    mgr = ConcurrentStateManager(sm)

    # Parameter (use an existing refinable path)
    with mgr.write_transaction(mutator_id="init") as w:
        w.set("hull.loa", 10.0, "test")

    # Observable/objective f = -(p-20)^2 (maximize by targeting f=0 at p=20)
    reg = ObservableRegistry()
    reg.register(
        ObservableSpec(observable_id="f", measurable=True, controllable=False),
        measure_fn=lambda st: -((float(st.get("hull.loa", 0.0) or 0.0) - 20.0) ** 2),
        depends_on=["hull.loa"],
    )
    # Parameter is modeled as controllable observable id too (common pattern)
    reg.register(
        ObservableSpec(observable_id="hull.loa", measurable=True, controllable=True),
        measure_fn=lambda st: float(st.get("hull.loa", 0.0) or 0.0),
        depends_on=["hull.loa"],
    )

    ex = CoordinateExecutor(
        manager=mgr,
        registry=reg,
        config=CoordinateConfig(max_iterations=6, damping=1e-2),
    )
    res = ex.optimize(targets={"f": 0.0}, adjustable=["hull.loa"])
    assert res.iterations >= 1
    assert math.isfinite(res.final_residual_norm)

    # Should move parameter near 20
    p_final = float(sm.get("hull.loa", 0.0) or 0.0)
    assert abs(p_final - 20.0) < 1.0

