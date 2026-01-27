from magnet.core.state_manager import StateManager
from magnet.kernel.geometry_export import StateGeometryExport


def _box_sections_resources(*, loa: float, beam: float, depth: float) -> dict:
    hb = beam / 2.0
    pts = [[0.0, 0.0], [hb, 0.05], [hb, 1.0], [hb, depth]]
    return {
        "s0": {"_type": "geometry.section", "_id": "s0", "station": 0.0, "body_id": "main", "points": pts},
        "s1": {"_type": "geometry.section", "_id": "s1", "station": 0.5, "body_id": "main", "points": pts},
        "s2": {"_type": "geometry.section", "_id": "s2", "station": 1.0, "body_id": "main", "points": pts},
    }


def test_geometry_export_provides_sections_and_bodies():
    sm = StateManager()
    sm.from_dict(
        {
            "design_id": "TEST",
            "hull": {"loa": 20.0, "draft": 1.0},
            "geometry_intent": {"surface_definition": "smooth"},
            "resources": _box_sections_resources(loa=20.0, beam=5.0, depth=3.0),
        }
    )

    exp = StateGeometryExport(sm)
    secs = exp.get_sections()
    assert len(secs) >= 3
    assert all(len(s.points) >= 2 for s in secs)

    bodies = exp.get_bodies()
    assert len(bodies) == 1
    assert bodies[0].body_id == "main"

    xf = exp.get_component_transforms()
    assert isinstance(xf, dict)

