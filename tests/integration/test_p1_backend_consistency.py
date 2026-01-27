"""
P1 Backend Consistency Tests

Ensures resistance/stability outputs are internally consistent and written to
canonical schema fields so downstream consumers (UI/contracts) can trust them.
"""

import pytest

from tests.conftest import refinable_write_context


class TestP1ResistanceConsistency:
    def test_cp_lcb_passthrough_no_estimation_warnings(self):
        """
        ResistanceValidator should pass Cp and LCB (from state) to the calculator so the
        calculator does NOT emit "Cp estimated" / "LCB fraction assumed" warnings.
        """
        from magnet.core.state_manager import StateManager
        from magnet.core.design_state import DesignState
        from magnet.physics.validators import ResistanceValidator

        sm = StateManager(DesignState())

        # Set refinable inputs (transaction required)
        with refinable_write_context(sm):
            sm.set("hull.lwl", 25.0, "test/p1")
            sm.set("hull.beam", 5.0, "test/p1")
            sm.set("hull.draft", 1.5, "test/p1")
            sm.set("hull.cb", 0.55, "test/p1")
            sm.set("hull.cp", 0.65, "test/p1")
            sm.set("hull.lcb_fraction", 0.52, "test/p1")  # from FP; slightly aft of midship
            sm.set("mission.max_speed_kts", 12.0, "test/p1")

        # Set non-refinable prerequisites (allowed outside transaction)
        sm.set("hull.displacement_mt", 50.0, "test/p1")
        sm.set("hull.wetted_surface_m2", 120.0, "test/p1")

        result = ResistanceValidator().validate(sm, {})

        messages = " | ".join(f.message for f in result.findings)
        assert "Cp estimated" not in messages
        assert "LCB fraction assumed" not in messages

    def test_regime_gating_displacement_valid(self):
        """Fn < 0.4 => displacement regime => method_valid=True."""
        from magnet.core.state_manager import StateManager
        from magnet.core.design_state import DesignState
        from magnet.physics.validators import ResistanceValidator

        sm = StateManager(DesignState())

        with refinable_write_context(sm):
            sm.set("hull.lwl", 25.0, "test/p1")
            sm.set("hull.beam", 6.0, "test/p1")
            sm.set("hull.draft", 2.0, "test/p1")
            sm.set("hull.cb", 0.60, "test/p1")
            sm.set("mission.max_speed_kts", 10.0, "test/p1")  # Fn ~ 0.33

        sm.set("hull.displacement_mt", 150.0, "test/p1")
        sm.set("hull.wetted_surface_m2", 350.0, "test/p1")

        ResistanceValidator().validate(sm, {})

        assert sm.get("resistance.regime") == "displacement"
        assert sm.get("resistance.method_valid") is True
        assert "Holtrop" in (sm.get("resistance.validity_note") or "")

    def test_regime_gating_planing_invalid(self):
        """Fn >= 0.7 => planing regime => route to Savitsky and expose method validity."""
        from magnet.core.state_manager import StateManager
        from magnet.core.design_state import DesignState
        from magnet.physics.validators import ResistanceValidator

        sm = StateManager(DesignState())

        with refinable_write_context(sm):
            sm.set("hull.lwl", 15.0, "test/p1")
            sm.set("hull.beam", 3.5, "test/p1")
            sm.set("hull.draft", 0.9, "test/p1")
            sm.set("hull.cb", 0.40, "test/p1")
            sm.set("mission.max_speed_kts", 40.0, "test/p1")  # Fn > 0.7

        sm.set("hull.displacement_mt", 20.0, "test/p1")
        sm.set("hull.wetted_surface_m2", 80.0, "test/p1")

        ResistanceValidator().validate(sm, {})

        assert sm.get("resistance.regime") == "planing"
        # Firewall: method is always blended; in planing case weights should skew toward Savitsky.
        assert sm.get("resistance.method") == "blended"
        comps = sm.get("resistance.method_components") or {}
        w = (comps.get("weights") or {}) if isinstance(comps, dict) else {}
        assert w.get("savitsky", 0.0) > 0.70
        assert sm.get("resistance.method_valid") in (True, False)
        assert "Savitsky" in (sm.get("resistance.validity_note") or "")


class TestP1StabilityConsistency:
    def test_stability_contract_fields_and_fsc(self):
        """
        Stability validators should write canonical contract fields and apply FSC so:
        - gm_transverse_m (solid) > gm_corrected_m
        - fsc_m stored
        - canonical GZ/damage/weather keys exist
        """
        from magnet.core.state_manager import StateManager
        from magnet.core.design_state import DesignState
        from magnet.stability.validators import (
            IntactGMValidator,
            GZCurveValidator,
            DamageStabilityValidator,
            WeatherCriterionValidator,
        )

        sm = StateManager(DesignState())

        # Refinable hull dimensions used by some stability validators
        with refinable_write_context(sm):
            sm.set("hull.loa", 50.0, "test/p1")
            sm.set("hull.beam", 10.0, "test/p1")
            sm.set("hull.draft", 2.5, "test/p1")
            sm.set("hull.depth", 4.0, "test/p1")
            sm.set("stability.kg_m", 2.8, "test/p1")

        # Physics prerequisites (normally from hydrostatics)
        sm.set("hull.kb_m", 1.5, "test/p1")
        sm.set("hull.bm_m", 2.5, "test/p1")
        sm.set("hull.displacement_mt", 700.0, "test/p1")

        IntactGMValidator().validate(sm, {})
        GZCurveValidator().validate(sm, {})
        DamageStabilityValidator().validate(sm, {})
        WeatherCriterionValidator().validate(sm, {})

        gm_solid = sm.get("stability.gm_transverse_m")
        gm_corrected = sm.get("stability.gm_corrected_m")
        fsc_m = sm.get("stability.fsc_m")

        assert gm_solid is not None and gm_corrected is not None and fsc_m is not None
        assert gm_corrected < gm_solid
        assert (gm_solid - gm_corrected) == pytest.approx(fsc_m, rel=0.05)

        # Canonical contract fields (builtin/schema)
        for path in [
            "stability.gm_m",
            "stability.gm_solid_m",
            "stability.km_m",
            "stability.passes_gm_criterion",
            "stability.gz_30_m",
            "stability.angle_gz_max_deg",
            "stability.angle_vanishing_deg",
            "stability.range_deg",
            "stability.passes_gz_criteria",
            "stability.damage_results",
            "stability.weather_ratio",
            "stability.weather_passes",
        ]:
            assert sm.get(path) is not None, f"Expected {path} to be set"


