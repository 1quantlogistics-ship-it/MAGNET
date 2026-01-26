from magnet.core.state_manager import StateManager
from magnet.systems.structural.stringer import StringerGenerator
from tests.conftest import refinable_write_context


def test_stringer_generator_produces_longitudinals():
    sm = StateManager()
    with refinable_write_context(sm):
        sm.set("hull.loa", 25.0, "test")
        sm.set("hull.lwl", 23.0, "test")
        sm.set("hull.beam", 6.0, "test")
        sm.set("hull.depth", 3.0, "test")
        sm.set("hull.draft", 1.5, "test")
        sm.set("hull.cb", 0.45, "test")
        sm.set("mission.max_speed_kts", 30.0, "test")

    stringers = StringerGenerator(sm).generate()
    assert len(stringers) > 0
    assert all(getattr(s, "zone", None) is not None for s in stringers)

