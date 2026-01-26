from magnet.core.state_manager import StateManager
from magnet.physics.validators import HydrostaticsValidator
from magnet.physics.stability_validator import validate_stability
from tests.conftest import refinable_write_context


def test_stability_validator_wrapper_produces_gm():
    sm = StateManager()
    with refinable_write_context(sm):
        sm.set("hull.loa", 25.0, "test")
        sm.set("hull.lwl", 23.0, "test")
        sm.set("hull.beam", 6.0, "test")
        sm.set("hull.depth", 3.0, "test")
        sm.set("hull.draft", 1.5, "test")
        sm.set("hull.cb", 0.45, "test")
        sm.set("hull.cp", 0.65, "test")
        sm.set("hull.cm", 0.80, "test")
        sm.set("hull.cwp", 0.75, "test")
        sm.set("hull.deadrise_deg", 12.0, "test")

    # Hydrostatics writes KB/BM and displacement.
    HydrostaticsValidator().validate(sm, {})

    # Provide KG via weight (required by v1.3 stability validators).
    sm.begin_transaction()
    sm.set("weight.lightship_vcg_m", 1.2, "test")
    sm.commit()

    out = validate_stability(sm, {})
    assert out.gm_m is not None
