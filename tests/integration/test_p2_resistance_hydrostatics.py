"""
P2 Integration Tests

Validates:
  - Planing resistance routing uses Savitsky when Fn > 0.7
  - Displacement resistance routing uses Holtrop when Fn <= 0.7
  - Hydrostatics uses geometry integration when hull generator is available
  - Catamaran resistance includes an interference factor (approx)
"""

import pytest

from tests.conftest import refinable_write_context


class TestP2SavitskyAndGeometryHydrostatics:
    @pytest.fixture
    def setup_app(self):
        """Create production-wired app so Conductor is available."""
        from magnet.bootstrap import create_app

        app = create_app()
        sm = app.state_manager
        conductor = app.conductor
        conductor.create_session("p2-resistance-hydrostatics-001")
        return app, sm, conductor

    def test_planing_hull_uses_savitsky(self, setup_app):
        _app, sm, conductor = setup_app

        with refinable_write_context(sm):
            sm.set("hull.loa", 12.0, "test/p2")
            sm.set("mission.max_speed_kts", 45.0, "test/p2")
            sm.set("hull.hull_type", "planing", "test/p2")

        assert conductor.run_phase("mission").status.value in ("completed", "warning", "passed")
        assert conductor.run_phase("hull").status.value in ("completed", "warning", "passed")

        from magnet.physics.validators import ResistanceValidator

        res = ResistanceValidator().validate(sm, {})
        assert res.state.value in ("passed", "warning"), getattr(res, "error_message", None)

        # Firewall: method is always blended; check weights skew toward Savitsky in planing case.
        assert sm.get("resistance.method") == "blended"
        comps = sm.get("resistance.method_components") or {}
        w = (comps.get("weights") or {}) if isinstance(comps, dict) else {}
        assert w.get("savitsky", 0.0) > 0.70
        assert sm.get("resistance.running_trim_deg") is not None
        assert sm.get("resistance.froude_beam") is not None

        # Sanity checks
        total_kn = sm.get("resistance.total_resistance_kn")
        power_kw = sm.get("resistance.effective_power_kw")
        trim_deg = sm.get("resistance.running_trim_deg")

        assert 5.0 < total_kn < 250.0, f"Resistance {total_kn} kN unreasonable"
        assert 50.0 < power_kw < 5000.0, f"Power {power_kw} kW unreasonable"
        assert 2.0 <= trim_deg <= 12.0, f"Trim {trim_deg}° unreasonable"

    def test_displacement_hull_uses_holtrop(self, setup_app):
        _app, sm, conductor = setup_app

        with refinable_write_context(sm):
            sm.set("hull.loa", 25.0, "test/p2")
            sm.set("mission.max_speed_kts", 10.0, "test/p2")
            sm.set("hull.hull_type", "workboat", "test/p2")

        assert conductor.run_phase("mission").status.value in ("completed", "warning", "passed")
        assert conductor.run_phase("hull").status.value in ("completed", "warning", "passed")

        from magnet.physics.validators import ResistanceValidator

        res = ResistanceValidator().validate(sm, {})
        assert res.state.value in ("passed", "warning"), getattr(res, "error_message", None)

        assert sm.get("resistance.method") == "blended"
        comps = sm.get("resistance.method_components") or {}
        w = (comps.get("weights") or {}) if isinstance(comps, dict) else {}
        assert w.get("holtrop", 0.0) > 0.70
        assert sm.get("resistance.method_valid") in (True, False)  # depends on validity envelopes
        assert sm.get("resistance.running_trim_deg") is None

    def test_geometry_hydrostatics_computed(self, setup_app):
        _app, sm, conductor = setup_app

        with refinable_write_context(sm):
            sm.set("hull.loa", 20.0, "test/p2")
            sm.set("mission.max_speed_kts", 12.0, "test/p2")
            sm.set("hull.hull_type", "workboat", "test/p2")

        assert conductor.run_phase("mission").status.value in ("completed", "warning", "passed")
        assert conductor.run_phase("hull").status.value in ("completed", "warning", "passed")

        assert sm.get("hull.hydrostatics_method") == "geometry_integration"
        assert sm.get("hull.sectional_areas") is not None
        assert len(sm.get("hull.sectional_areas")) > 0
        assert len(sm.get("hull.bonjean_stations")) == len(sm.get("hull.sectional_areas"))

        cb = sm.get("hull.cb")
        cb_geom = sm.get("hull.cb_geometry")
        assert cb is not None and cb_geom is not None
        # Generator geometry is parametric/heuristic; expect rough agreement (order-of-magnitude),
        # not exact coefficient matching yet.
        assert abs(cb_geom - cb) / max(cb, 1e-6) < 0.50, f"Cb geometry {cb_geom} too far from synthesis {cb}"

    def test_catamaran_includes_interference_factor(self, setup_app):
        _app, sm, conductor = setup_app

        with refinable_write_context(sm):
            sm.set("hull.loa", 30.0, "test/p2")
            sm.set("mission.max_speed_kts", 20.0, "test/p2")
            sm.set("hull.hull_type", "catamaran", "test/p2")

        assert conductor.run_phase("mission").status.value in ("completed", "warning", "passed")
        assert conductor.run_phase("hull").status.value in ("completed", "warning", "passed")

        from magnet.physics.validators import ResistanceValidator

        res = ResistanceValidator().validate(sm, {})
        assert res.state.value in ("passed", "warning"), getattr(res, "error_message", None)

        tau = sm.get("resistance.interference_factor")
        note = sm.get("resistance.interference_note")
        assert tau is not None, "Expected catamaran interference factor"
        assert 1.0 <= tau <= 1.8, f"Interference factor τ={tau} out of expected range"
        assert note is not None and "τ=" in note

