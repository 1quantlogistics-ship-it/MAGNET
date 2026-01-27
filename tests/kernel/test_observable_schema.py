from magnet.kernel.observable_registry import ObservableRegistry, ObservableSpec
from magnet.kernel.observable_schema import ObservableSchemaGenerator


def test_observable_schema_includes_controllable_and_measurable_ids():
    reg = ObservableRegistry()
    reg.register(
        ObservableSpec(observable_id="a", measurable=True, controllable=False, unit="m", control_mode="DIRECT"),
        measure_fn=lambda st: 1.0,
        depends_on=[],
    )
    reg.register(
        ObservableSpec(
            observable_id="b",
            measurable=True,
            controllable=True,
            control_mode="DIRECT",
            unit="deg",
            max_delta=5.0,
            applicable_to=["geometry.section"],
        ),
        measure_fn=lambda st: 2.0,
        depends_on=[],
    )

    gen = ObservableSchemaGenerator(max_examples=10)
    schema = gen.build(registry=reg, targets=[{"kind": "body", "id": "main"}])
    d = gen.to_dict(schema)

    assert "observables" in d and len(d["observables"]) == 2
    assert d["controllable_observable_ids"] == ["b"]
    assert set(d["measurable_observable_ids"]) == {"a", "b"}
    assert d["targets"] == [{"kind": "body", "id": "main"}]
    assert "unknown_observable" in d["unknown_observable_behavior"]

