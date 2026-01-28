from magnet.physics.validators import ResistanceValidator


class MockStateManager:
    def __init__(self, values=None):
        self._values = values or {}

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value, source=None):
        self._values[key] = value


def test_resistance_blending_emits_weights_and_extrapolation_flags():
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
    res = ResistanceValidator().validate(sm, {})
    assert res.passed is True

    w = sm.get("resistance.method_weights")
    assert isinstance(w, dict)
    assert "holtrop" in w and "savitsky" in w
    assert abs(float(w["holtrop"]) + float(w["savitsky"]) - 1.0) < 1e-6

    env = sm.get("resistance.validity_envelope")
    assert isinstance(env, str) and len(env) > 0

    # Must be explicit (never silently extrapolate)
    assert isinstance(sm.get("resistance.outside_envelope"), bool)
    assert isinstance(sm.get("resistance.extrapolation_flag"), bool)

