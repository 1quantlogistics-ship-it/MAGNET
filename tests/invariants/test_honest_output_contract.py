"""
Phase 4: Honest Output Contract (minimal enforcement).

This test only asserts the presence/shape of uncertainty blocks for key physics outputs.
It does NOT enforce numeric correctness (covered by physics-specific unit tests).
"""

from magnet.physics.validators import ResistanceValidator, HydrostaticsValidator
from magnet.stability.validators import IntactGMValidator, GZCurveValidator
from magnet.weight.validators import WeightEstimationValidator


class MockStateManager:
    def __init__(self, values=None):
        self._values = values or {}

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value, source=None):
        self._values[key] = value


def test_resistance_attaches_uncertainty_object():
    sm = MockStateManager(
        {
            "hull.lwl": 20.0,
            "hull.beam": 5.0,
            "hull.draft": 1.5,
            "hull.cb": 0.55,
            "hull.displacement_mt": 25.0,
            "hull.wetted_surface_m2": 120.0,
            "mission.max_speed_kts": 25.0,
        }
    )
    v = ResistanceValidator()
    res = v.validate(sm, {})
    assert res.passed is True
    u = sm.get("resistance.uncertainty")
    assert isinstance(u, dict)
    for k in ["value_pct", "level", "basis", "validity_envelope", "novelty_impact", "details"]:
        assert k in u


def test_hydrostatics_attaches_uncertainty_object():
    sm = MockStateManager(
        {
            "hull.lwl": 20.0,
            "hull.beam": 5.0,
            "hull.draft": 1.5,
            "hull.depth": 3.0,
            "hull.cb": 0.55,
        }
    )
    v = HydrostaticsValidator()
    res = v.validate(sm, {})
    assert res.passed is True
    u = sm.get("hull.hydrostatics_uncertainty")
    assert isinstance(u, dict)
    for k in ["value_pct", "level", "basis", "validity_envelope", "novelty_impact", "details"]:
        assert k in u


def test_uncertainty_mentions_unmodeled_primitives_when_present():
    # Ensure "honest output" explicitly flags primitives that are not yet modeled in physics.
    resources = {
        "opening_1": {"_type": "geometry.opening", "_id": "opening_1", "surface_id": "hull_shell", "position": [1, 0, 0], "dimensions": [0.5, 0.5]},
        "flow_1": {"_type": "geometry.flow_path", "_id": "flow_1", "medium": "water", "inlet_point": [0, 0, 0], "outlet_point": [1, 0, 0], "cross_section_m2": 0.01},
        "att_1": {"_type": "geometry.attachment", "_id": "att_1", "parent_body_id": "main", "child_body_id": "pod_1"},
    }

    # Hydrostatics
    sm_h = MockStateManager(
        {
            "hull.lwl": 20.0,
            "hull.beam": 5.0,
            "hull.draft": 1.5,
            "hull.depth": 3.0,
            "hull.cb": 0.55,
            "resources": resources,
        }
    )
    HydrostaticsValidator().validate(sm_h, {})
    u_h = sm_h.get("hull.hydrostatics_uncertainty")
    assert isinstance(u_h, dict)
    assert u_h.get("novelty_impact"), "Expected novelty_impact to be non-empty when primitives exist"

    # Resistance
    sm_r = MockStateManager(
        {
            "hull.lwl": 20.0,
            "hull.beam": 5.0,
            "hull.draft": 1.5,
            "hull.cb": 0.55,
            "hull.displacement_mt": 25.0,
            "hull.wetted_surface_m2": 120.0,
            "mission.max_speed_kts": 25.0,
            "resources": resources,
        }
    )
    ResistanceValidator().validate(sm_r, {})
    u_r = sm_r.get("resistance.uncertainty")
    assert isinstance(u_r, dict)
    assert u_r.get("novelty_impact"), "Expected novelty_impact to be non-empty when primitives exist"


def test_stability_attaches_uncertainty_objects():
    # Minimal inputs: intact GM + GZ depend on KB/BM and KG.
    sm = MockStateManager(
        {
            "hull.kb_m": 1.0,
            "hull.bm_m": 2.0,
            "stability.kg_m": 2.2,
        }
    )
    res_gm = IntactGMValidator().validate(sm, {})
    assert res_gm.passed is True
    u_gm = sm.get("stability.uncertainty")
    assert isinstance(u_gm, dict)
    for k in ["value_pct", "level", "basis", "validity_envelope", "novelty_impact", "details"]:
        assert k in u_gm

    res_gz = GZCurveValidator().validate(sm, {})
    assert res_gz.passed is True
    u_gz = sm.get("stability.gz_uncertainty")
    assert isinstance(u_gz, dict)
    for k in ["value_pct", "level", "basis", "validity_envelope", "novelty_impact", "details"]:
        assert k in u_gz


def test_weight_attaches_uncertainty_object():
    sm = MockStateManager(
        {
            "hull.lwl": 20.0,
            "hull.beam": 5.0,
            "hull.depth": 3.0,
            "hull.draft": 1.5,
            "hull.cb": 0.55,
            "mission.max_speed_kts": 25.0,
            "propulsion.installed_power_kw": 2000.0,
        }
    )
    res = WeightEstimationValidator().validate(sm, {})
    assert res.passed is True
    u = sm.get("weight.uncertainty")
    assert isinstance(u, dict)
    for k in ["value_pct", "level", "basis", "validity_envelope", "novelty_impact", "details"]:
        assert k in u


def test_damage_stability_attaches_uncertainty_object():
    # Minimal inputs: damage stability uses GM, GZ max, displacement.
    from magnet.stability.validators import DamageStabilityValidator

    sm = MockStateManager(
        {
            "stability.gm_transverse_m": 1.0,
            "stability.gz_max_m": 0.4,
            "hull.displacement_mt": 25.0,
        }
    )
    res = DamageStabilityValidator().validate(sm, {})
    assert res.passed is True
    u = sm.get("stability.damage_uncertainty")
    assert isinstance(u, dict)
    for k in ["value_pct", "level", "basis", "validity_envelope", "novelty_impact", "details"]:
        assert k in u


def test_primitives_increase_resistance_when_modeled():
    """
    Phase 3C: primitives are not just annotations — they can affect resistance.

    Minimal modeled case: a water flow_path with cross_section_m2 adds a loss-based drag term.
    """
    base = {
        "hull.lwl": 20.0,
        "hull.beam": 5.0,
        "hull.draft": 1.5,
        "hull.cb": 0.55,
        "hull.displacement_mt": 25.0,
        "hull.wetted_surface_m2": 120.0,
        "mission.max_speed_kts": 25.0,
    }

    sm0 = MockStateManager(dict(base))
    ResistanceValidator().validate(sm0, {})
    rt0 = float(sm0.get("resistance.total_resistance_kn") or 0.0)
    prim0 = float(sm0.get("resistance.primitive_resistance_kn") or 0.0)
    assert prim0 == 0.0

    sm1 = MockStateManager(
        {
            **base,
            "resources": {
                "flow_1": {
                    "_type": "geometry.flow_path",
                    "_id": "flow_1",
                    "medium": "water",
                    "inlet_point": [2.0, 0.0, 0.2],
                    "outlet_point": [8.0, 0.0, 0.2],
                    "cross_section_m2": 0.05,
                    # Optional override; test should still pass without this.
                    "loss_coefficient": 2.0,
                }
            },
        }
    )
    ResistanceValidator().validate(sm1, {})
    rt1 = float(sm1.get("resistance.total_resistance_kn") or 0.0)
    prim1 = float(sm1.get("resistance.primitive_resistance_kn") or 0.0)
    assert prim1 > 0.0
    assert rt1 > rt0


def test_primitives_increase_weight_when_mass_provided():
    """
    Phase 3C: primitives affect weight when explicit mass semantics are provided.
    """
    base = {
        "hull.lwl": 20.0,
        "hull.beam": 5.0,
        "hull.depth": 3.0,
        "hull.draft": 1.5,
        "hull.cb": 0.55,
        "mission.max_speed_kts": 25.0,
        "propulsion.installed_power_kw": 2000.0,
    }

    sm0 = MockStateManager(dict(base))
    WeightEstimationValidator().validate(sm0, {})
    w0 = float(sm0.get("weight.lightship_weight_mt") or 0.0)
    pm0 = float(sm0.get("weight.primitive_mass_kg") or 0.0)
    assert pm0 == 0.0

    sm1 = MockStateManager(
        {
            **base,
            "resources": {
                "att_1": {
                    "_type": "geometry.attachment",
                    "_id": "att_1",
                    "parent_body_id": "main",
                    "child_body_id": "pod_1",
                    "attachment_type": "rigid",
                    "offset_x_m": 7.0,
                    "offset_y_m": 0.0,
                    "offset_z_m": -0.2,
                    "mass_kg": 1000.0,
                    "mass_center": [7.0, 0.0, -0.2],
                }
            },
        }
    )
    WeightEstimationValidator().validate(sm1, {})
    w1 = float(sm1.get("weight.lightship_weight_mt") or 0.0)
    pm1 = float(sm1.get("weight.primitive_mass_kg") or 0.0)
    assert pm1 == 1000.0
    assert w1 > w0

