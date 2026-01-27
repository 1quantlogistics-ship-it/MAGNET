from magnet.kernel.observable_graph import BatchedRegistry, ObservableGraph


def test_batched_registry_returns_all_requested_observables():
    g = ObservableGraph()
    g.register("x2", compute_fn=lambda st: st["x"] * 2, depends_on=["x"])
    g.register("x3", compute_fn=lambda st: st["x"] * 3, depends_on=["x"])

    br = BatchedRegistry(g)
    out = br.batch_get(["x2", "x3"], {"x": 10})
    assert out["x2"] == 20
    assert out["x3"] == 30

