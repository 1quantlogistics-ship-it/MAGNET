"""
T8.2: End-to-End Spiral Test (offline / deterministic).

This is a lightweight integration test that exercises a full "spiral" run
without relying on any networked LLM calls:
mission -> hull -> weight -> stability
"""

import pytest

from tests.conftest import refinable_write_context


def test_e2e_spiral_mission_to_stability_runs_without_failure():
    from magnet.bootstrap import create_app

    app = create_app()
    sm = app.state_manager
    conductor = app.conductor
    conductor.create_session("e2e-spiral-offline-001")

    # Seed mission + high-level intent (keep it minimal but plausible).
    with refinable_write_context(sm):
        sm.set("mission.max_speed_kts", 28.0, "test/e2e_spiral")
        sm.set("mission.range_nm", 250.0, "test/e2e_spiral")
        sm.set("mission.crew_berthed", 6, "test/e2e_spiral")
        sm.set("hull.hull_type", "patrol", "test/e2e_spiral")
        sm.set("hull.loa", 18.0, "test/e2e_spiral")

    # Run a full dependency-respecting chain.
    for phase in ("mission", "hull", "structure", "propulsion", "weight", "stability"):
        res = conductor.run_phase(phase)
        assert res is not None
        assert res.status.value in ("completed", "passed", "warning"), (
            f"Phase {phase} failed: {getattr(res, 'errors', None)}"
        )

    # Spot-check a couple of key outputs expected after a full pass.
    assert sm.get("hull.displacement_m3") is not None
    assert sm.get("stability.gm_transverse_m") is not None or sm.get("stability.gm_m") is not None

