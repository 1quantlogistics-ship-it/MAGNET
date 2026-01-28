from magnet.core.state_manager import StateManager
from magnet.physics.structural_validator import validate_structure
from tests.conftest import refinable_write_context


def test_structural_validator_returns_recommendation_and_warnings_list():
    sm = StateManager()
    with refinable_write_context(sm):
        sm.set("hull.loa", 25.0, "test")
        sm.set("hull.lwl", 23.0, "test")
        sm.set("hull.beam", 6.0, "test")
        sm.set("hull.depth", 3.0, "test")
        sm.set("hull.draft", 1.5, "test")
        sm.set("hull.cb", 0.45, "test")
        sm.set("mission.max_speed_kts", 30.0, "test")

    # Scantlings wants a displacement; provide best-effort derived value.
    sm.begin_transaction()
    sm.set("hull.displacement_mt", 80.0, "test")
    sm.commit()

    out = validate_structure(sm)
    assert out.passed is True
    assert isinstance(out.warnings, list)
    # Recommendation may be None if scantlings fail; but in this setup it should exist.
    assert out.recommended_bottom_plating_mm is not None
    assert out.recommended_bottom_plating_mm >= 0.0

