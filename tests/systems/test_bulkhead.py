from magnet.core.state_manager import StateManager
from magnet.systems.structural.bulkhead import BulkheadGenerator
from tests.conftest import refinable_write_context


def test_bulkhead_generator_includes_collision_bulkhead_and_is_sorted():
    sm = StateManager()
    with refinable_write_context(sm):
        sm.set("hull.loa", 25.0, "test")
        sm.set("hull.lwl", 23.0, "test")
        sm.set("hull.beam", 6.0, "test")
        sm.set("hull.depth", 3.0, "test")
        sm.set("hull.draft", 1.5, "test")
        sm.set("mission.max_speed_kts", 30.0, "test")

    bulkheads = BulkheadGenerator(sm).generate()
    assert bulkheads, "Expected some bulkheads"
    assert any(getattr(b, "is_collision_bulkhead", False) for b in bulkheads)
    xs = [float(b.x_position) for b in bulkheads]
    assert xs == sorted(xs)

