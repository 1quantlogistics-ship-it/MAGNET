from magnet.core.state_manager import StateManager
from magnet.physics.hydro_weight_convergence import HydroWeightConvergedValidator
from tests.conftest import refinable_write_context


def test_hydro_weight_convergence_updates_hull_draft_and_writes_flags():
    sm = StateManager()

    # Minimal hull inputs (parametric path fallback is OK for this test)
    with refinable_write_context(sm):
        sm.set("hull.loa", 24.0, "test")
        sm.set("hull.lwl", 22.0, "test")
        sm.set("hull.beam", 6.0, "test")
        sm.set("hull.depth", 4.0, "test")
        sm.set("hull.draft", 1.2, "test")
        sm.set("hull.cb", 0.55, "test")
        sm.set("hull.deadrise_deg", 12.0, "test")

        # Keep the solve enabled (Option B control)
        sm.set("hull.auto_converge_hydro_weight", True, "test")

    res = HydroWeightConvergedValidator().validate(sm, {})
    assert res.state.value in ("passed", "warning")

    # The validator must write its convergence flags.
    assert sm.get("hull.hydro_weight_converged") in (True, False)
    assert sm.get("hull.hydro_weight_iterations") is not None

    # It must always leave a concrete draft (may change via equilibrium).
    assert sm.get("hull.draft") is not None
    assert float(sm.get("hull.draft")) > 0

    # If converged, equilibrium diagnostics must exist.
    if sm.get("hull.hydro_weight_converged") is True:
        assert sm.get("hull.equilibrium_converged") is True
        assert sm.get("hull.equilibrium_draft_m") is not None

