from magnet.kernel.observable_registry import ObservableAlias, ObservableRegistry, ObservableSpec


def test_observable_registry_registers_specs_and_measures_values():
    reg = ObservableRegistry()
    reg.register(
        ObservableSpec(observable_id="hull.beam", measurable=True, controllable=True, unit="m"),
        measure_fn=lambda st: float(st.get("hull.beam", 0.0)),
        depends_on=["hull.beam"],
    )

    specs = reg.list_specs()
    assert len(specs) == 1
    assert specs[0].observable_id == "hull.beam"

    v = reg.get_value("hull.beam", {"hull.beam": 5.0})
    assert v == 5.0


def test_observable_registry_alias_resolution_and_batch_get():
    reg = ObservableRegistry()
    reg.register(
        ObservableSpec(observable_id="a", measurable=True, controllable=True),
        measure_fn=lambda st: float(st.get("a", 0.0) or 0.0),
        depends_on=["a"],
    )
    reg.register_alias(ObservableAlias(alias_id="legacy.a", canonical_id="a", deprecated=True))

    assert reg.get_spec("legacy.a").observable_id == "a"
    assert reg.get_value("legacy.a", {"a": 3.0}) == 3.0

    out = reg.batch_get(["legacy.a", "a"], {"a": 7.0})
    assert out["a"] == 7.0

