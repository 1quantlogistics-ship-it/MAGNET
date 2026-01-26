from magnet.constraints.hierarchical_validator import (
    Constraint,
    ConstraintLevel,
    ConstraintResult,
    HierarchicalValidator,
)


def test_hierarchical_validator_stops_on_first_failed_level():
    hv = HierarchicalValidator()

    # Geometric fails
    hv.add_constraint(Constraint(
        name="x_positive",
        level=ConstraintLevel.GEOMETRIC,
        evaluate_fn=lambda d: ConstraintResult(
            satisfied=False,
            value=float(d.get("x", 0.0)),
            threshold=0.0,
            margin=-1.0,
            confidence=1.0,
        ),
    ))
    # These must not run when stop_on_failure=True.
    hv.add_constraint(Constraint(
        name="should_not_run",
        level=ConstraintLevel.SIMPLIFIED,
        evaluate_fn=lambda _d: (_ for _ in ()).throw(AssertionError("should not run")),
    ))

    res = hv.validate({"x": -1.0}, stop_on_failure=True)
    assert res.valid is False
    assert res.failed_level == ConstraintLevel.GEOMETRIC


def test_hierarchical_validator_runs_all_levels_when_passing():
    hv = HierarchicalValidator()

    hv.add_constraint(Constraint(
        name="geo_ok",
        level=ConstraintLevel.GEOMETRIC,
        evaluate_fn=lambda d: ConstraintResult(
            satisfied=True,
            value=1.0,
            threshold=0.0,
            margin=1.0,
        ),
    ))
    hv.add_constraint(Constraint(
        name="simp_ok",
        level=ConstraintLevel.SIMPLIFIED,
        evaluate_fn=lambda d: ConstraintResult(
            satisfied=True,
            value=2.0,
            threshold=0.0,
            margin=2.0,
        ),
    ))
    hv.add_constraint(Constraint(
        name="full_ok",
        level=ConstraintLevel.FULL_PHYSICS,
        evaluate_fn=lambda d: ConstraintResult(
            satisfied=True,
            value=3.0,
            threshold=0.0,
            margin=3.0,
        ),
    ))

    res = hv.validate({"x": 1.0}, stop_on_failure=True)
    assert res.valid is True
    assert res.failed_level is None
    assert ConstraintLevel.GEOMETRIC in res.results
    assert ConstraintLevel.SIMPLIFIED in res.results
    assert ConstraintLevel.FULL_PHYSICS in res.results

