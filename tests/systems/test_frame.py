from magnet.core.state_manager import StateManager
from magnet.systems.structural.frame import FrameGenerator
from tests.conftest import refinable_write_context


def test_frame_generator_produces_frames_with_monotone_x():
    sm = StateManager()
    with refinable_write_context(sm):
        sm.set("hull.loa", 25.0, "test")
        sm.set("hull.lwl", 23.0, "test")
        sm.set("hull.beam", 6.0, "test")
        sm.set("hull.depth", 3.0, "test")
        sm.set("hull.draft", 1.5, "test")
        sm.set("mission.max_speed_kts", 30.0, "test")

    frames = FrameGenerator(sm).generate()
    assert len(frames) > 5
    xs = [float(f.x_position) for f in frames]
    assert xs[0] == 0.0
    assert all(xs[i] <= xs[i + 1] for i in range(len(xs) - 1))

