"""
Hull Synthesis E2E Tests

End-to-end verification that:
- Conductor.run_phase("hull") triggers hull synthesis from mission constraints
- Validators (via PipelineExecutor) run and satisfy the hull phase output contract
- All hull-form inputs (the 21-param schema set) are populated with realistic values
"""

import pytest

from tests.conftest import refinable_write_context


HULL_PARAMS = [
    # Principal
    "hull.loa",
    "hull.lwl",
    "hull.beam",
    "hull.draft",
    "hull.depth",
    # Coefficients
    "hull.cb",
    "hull.cp",
    "hull.cm",
    "hull.cwp",
    # Hull form inputs
    "hull.deadrise_deg",
    "hull.deadrise_transom_deg",
    "hull.bow_entrance_deg",
    "hull.bow_flare_deg",
    "hull.stem_rake_deg",
    "hull.transom_beam_ratio",
    "hull.freeboard_m",
    "hull.lcb_fraction",
    "hull.draft_fwd_m",
    "hull.draft_aft_m",
    "hull.hull_type",
]


class TestHullSynthesisE2E:
    @pytest.fixture
    def setup_app(self):
        """Create production-wired app so PipelineExecutor is available."""
        from magnet.bootstrap import create_app

        app = create_app()
        sm = app.state_manager
        conductor = app.conductor
        conductor.create_session("e2e-hull-synthesis-001")
        return app, sm, conductor

    def test_20m_patrol_35kts_8crew_300nm(self, setup_app):
        """
        Full hull phase run for a mission-sized vessel.

        Success means:
        - synthesis does not fall back due to internal errors
        - hydrostatics runs and produces hull.vcb_m + hull.bm_m
        - hull-form parameters are present and family-appropriate
        """
        _app, sm, conductor = setup_app

        # Seed mission + hull intent (leave hull dims unset so synthesis triggers)
        with refinable_write_context(sm):
            sm.set("hull.loa", 20.0, "test/e2e")
            sm.set("mission.max_speed_kts", 35.0, "test/e2e")
            sm.set("hull.hull_type", "patrol", "test/e2e")
            sm.set("mission.crew_berthed", 8, "test/e2e")
            sm.set("mission.range_nm", 300.0, "test/e2e")

        # Mission first (dependency)
        mission_result = conductor.run_phase("mission")
        assert mission_result.status.value in ("completed", "warning", "passed"), (
            f"Mission phase failed: {getattr(mission_result, 'errors', None)}"
        )

        # Run hull (synthesis hook + validators)
        result = conductor.run_phase("hull")
        assert result.status.value in ("completed", "warning", "passed"), (
            f"Hull phase failed: {getattr(result, 'errors', None)}"
        )

        # Contract outputs from hydrostatics should exist
        assert sm.get("hull.displacement_m3") is not None
        assert sm.get("hull.vcb_m") is not None
        assert sm.get("hull.bm_m") is not None

        # Synthesis audit should be attached when synthesis ran
        assert getattr(result, "synthesis_audit", None) is not None
        assert result.synthesis_audit.get("is_fallback") is False

        # Verify hull-form parameters populated
        for param in HULL_PARAMS:
            value = sm.get(param)
            assert value is not None, f"{param} is None"

        # Sanity checks for patrol-ish proportions
        loa = sm.get("hull.loa")
        lwl = sm.get("hull.lwl")
        beam = sm.get("hull.beam")
        draft = sm.get("hull.draft")
        deadrise = sm.get("hull.deadrise_deg")

        assert lwl == pytest.approx(loa * 0.95, rel=0.01)
        assert 4.5 <= (lwl / beam) <= 7.0, f"L/B {lwl/beam:.2f} outside patrol bounds"
        assert 2.0 <= (beam / draft) <= 4.5, f"B/T {beam/draft:.2f} outside patrol-ish bounds"
        assert 15.0 <= deadrise <= 30.0, f"Deadrise {deadrise}° unusual for patrol/planing patrol"


