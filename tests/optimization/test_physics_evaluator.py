from magnet.optimization.physics_evaluator import PhysicsEvaluator


def _box_sections_resources(*, loa: float, beam: float, depth: float) -> dict:
    hb = beam / 2.0
    pts = [[0.0, 0.0], [hb, 0.05], [hb, 1.0], [hb, depth]]
    return {
        "s0": {"_type": "geometry.section", "_id": "s0", "station": 0.0, "body_id": "main", "points": pts},
        "s1": {"_type": "geometry.section", "_id": "s1", "station": 0.5, "body_id": "main", "points": pts},
        "s2": {"_type": "geometry.section", "_id": "s2", "station": 1.0, "body_id": "main", "points": pts},
    }


def test_physics_evaluator_displacement_and_waterplane():
    loa = 20.0
    beam = 5.0
    depth = 3.0
    draft = 1.0
    state = {
        "design_id": "TEST",
        "hull": {"loa": loa, "draft": draft},
        "geometry_intent": {"surface_definition": "smooth"},
        "resources": _box_sections_resources(loa=loa, beam=beam, depth=depth),
    }
    pe = PhysicsEvaluator()

    disp_mt = pe.evaluate(state, "displacement_mt")
    assert disp_mt > 0.0

    aw = pe.evaluate(state, "waterplane_area_m2")
    assert aw > 0.0

