from magnet.core.state_manager import StateManager
from magnet.structural.scantlings import ScantlingCalculator
from magnet.structural.enums import StructuralZone
from tests.conftest import refinable_write_context


def test_scantlings_calculator_produces_positive_pressures_and_thickness():
    sm = StateManager()
    with refinable_write_context(sm):
        sm.set("hull.lwl", 24.0, "test")
        sm.set("hull.beam", 6.0, "test")
        sm.set("hull.depth", 3.0, "test")
        sm.set("hull.draft", 1.5, "test")
        sm.set("hull.cb", 0.5, "test")
        sm.set("mission.max_speed_kts", 30.0, "test")

    # Non-refinable write (displacement_mt is derived in pipeline, but required here)
    sm.begin_transaction()
    sm.set("hull.displacement_mt", 80.0, "test")
    sm.commit()

    calc = ScantlingCalculator(sm)

    p_bot = calc.calculate_design_pressure(StructuralZone.BOTTOM, x_position=0.5 * calc.lwl, z_position=0.0)
    assert p_bot.combined_pressure_kpa > 0.0

    t_req = calc.calculate_plate_thickness(
        StructuralZone.BOTTOM,
        span_mm=500.0,
        pressure_kpa=p_bot.combined_pressure_kpa,
        aspect_ratio=2.0,
    )
    assert t_req >= 0.0

