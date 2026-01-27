from magnet.kernel.observable_graph import ObservableGraph


def test_observable_graph_is_lazy_and_invalidates_transitively():
    g = ObservableGraph()

    # a -> b -> c dependency chain
    g.register("b", compute_fn=lambda st: st["a"] + 1, depends_on=["a"])
    g.register("c", compute_fn=lambda st: g.get("b", st) * 2, depends_on=["b"])

    st = {"a": 10}
    assert g.get("c", st) == 22

    # Update input and invalidate dependents
    st["a"] = 20
    invalidated = g.invalidate("a")
    assert "b" in invalidated
    assert "c" in invalidated

    assert g.get("c", st) == 42

