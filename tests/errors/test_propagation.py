from magnet.errors.propagation import DefaultErrorPropagator
from magnet.errors.taxonomy import create_bounds_error
from magnet.optimization.sensitivity import UnsafeStateEvaluationError


def test_propagates_generic_exception_with_user_message_and_suggestions():
    p = DefaultErrorPropagator()
    out = p.propagate(RuntimeError("boom"), layer="kernel")
    assert out.origin_layer == "kernel"
    assert out.user_message
    assert isinstance(out.suggestions, list)
    assert len(out.suggestions) > 0


def test_propagates_magnet_error_preserves_message_and_uses_recovery_descriptions():
    p = DefaultErrorPropagator()
    err = create_bounds_error(
        message="beam too large",
        source="validator.bounds",
        path="hull.beam",
        actual=12.0,
        min_val=1.0,
        max_val=6.0,
    )
    out = p.propagate(err, layer="validator")
    assert "beam too large" in out.user_message
    # Recovery suggestions come from configured recovery descriptions when available.
    assert len(out.suggestions) > 0


def test_maps_unsafe_state_evaluation_to_safety_message():
    p = DefaultErrorPropagator()
    out = p.propagate(UnsafeStateEvaluationError("no clone"), layer="optimization")
    assert "Safety guard" in out.user_message
    assert len(out.suggestions) > 0

