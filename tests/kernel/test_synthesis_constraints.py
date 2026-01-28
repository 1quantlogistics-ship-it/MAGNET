import pytest

from magnet.core.state_manager import StateManager
from magnet.kernel.synthesis_constraints import SynthesisConstraints, synthesize_from_constraints
from tests.conftest import refinable_write_context


def test_constraint_synthesis_produces_geometry_and_classification():
    sm = StateManager()

    constraints = SynthesisConstraints(
        displacement_m3=(120.0, 160.0),
        max_speed_kts=35.0,
        deadrise_transom_range_deg=(12.0, 18.0),
        num_bodies=1,
    )

    result = synthesize_from_constraints(constraints, sm, max_iterations=20)
    assert result.success is True
    assert result.geometry is not None
    assert result.derived_classification is not None
    assert result.derived_classification.regime in ("displacement", "semi-displacement", "planing")
    assert result.derived_classification.body_count >= 1


def test_constraint_synthesis_multibody_sets_spacing_in_state():
    sm = StateManager()
    constraints = SynthesisConstraints(
        displacement_m3=(800.0, 1200.0),
        max_speed_kts=20.0,
        num_bodies=2,
        hull_spacing_range_m=(3.0, 6.0),
    )
    with refinable_write_context(sm):
        result = synthesize_from_constraints(constraints, sm, max_iterations=10)
    assert result.geometry is not None
    assert sm.get("hull.hull_spacing_m") is not None
    assert sm.get("hull.hull_spacing_m") > 0


def test_constraints_validate_displacement_bounds():
    with pytest.raises(ValueError):
        SynthesisConstraints(displacement_m3=(0.0, 10.0))

