from magnet.kernel.stdlib.compiler import compile_to_geometry


def _minimal_section(station: float = 0.5):
    # Minimal monotone keel->deck polygon in [y,z]
    return {
        "_type": "geometry.section",
        "_id": f"section_{station}",
        "station": station,
        "body_id": "main",
        "points": [[0.0, 0.0], [0.5, 0.2], [0.8, 0.6], [0.6, 1.0], [0.0, 1.2]],
    }


def test_compiler_passes_through_opening_flow_path_attachment():
    state = {
        "design_id": "TEST",
        "hull": {"loa": 10.0},
        "resources": {
            "s0": _minimal_section(0.0),
            "s1": _minimal_section(0.5),
            "s2": _minimal_section(1.0),
            "opening_1": {
                "_type": "geometry.opening",
                "_id": "opening_1",
                "surface_id": "hull_shell",
                "position": [5.0, 0.5, 0.8],
                "dimensions": [0.4, 0.3],
                "shape": "rectangular",
            },
            "flow_1": {
                "_type": "geometry.flow_path",
                "_id": "flow_1",
                "medium": "water",
                "inlet_point": [2.0, 0.0, 0.2],
                "outlet_point": [8.0, 0.0, 0.2],
                "cross_section_m2": 0.01,
                "body_id": "main",
            },
            "att_1": {
                "_type": "geometry.attachment",
                "_id": "att_1",
                "parent_body_id": "main",
                "child_body_id": "pod_1",
                "attachment_type": "rigid",
                "offset_x_m": 7.0,
                "offset_y_m": 0.0,
                "offset_z_m": -0.2,
            },
        },
    }

    geo = compile_to_geometry(state)
    assert isinstance(geo.openings, list) and len(geo.openings) == 1
    assert geo.openings[0].get("_id") == "opening_1"
    assert isinstance(geo.flow_paths, list) and len(geo.flow_paths) == 1
    assert geo.flow_paths[0].get("_id") == "flow_1"
    assert isinstance(geo.attachments, list) and len(geo.attachments) == 1
    assert geo.attachments[0].get("_id") == "att_1"


def test_deleted_primitives_are_ignored():
    state = {
        "design_id": "TEST",
        "hull": {"loa": 10.0},
        "resources": {
            "s0": _minimal_section(0.0),
            "s1": _minimal_section(0.5),
            "s2": _minimal_section(1.0),
            "opening_1": {
                "_type": "geometry.opening",
                "_id": "opening_1",
                "_deleted": True,
                "surface_id": "hull_shell",
                "position": [5.0, 0.5, 0.8],
                "dimensions": [0.4, 0.3],
            },
            "flow_1": {"_type": "geometry.flow_path", "_id": "flow_1", "_deleted": True, "medium": "air", "inlet_point": [0, 0, 0], "outlet_point": [1, 0, 0]},
            "att_1": {"_type": "geometry.attachment", "_id": "att_1", "_deleted": True, "parent_body_id": "main", "child_body_id": "pod_1"},
        },
    }
    geo = compile_to_geometry(state)
    assert geo.openings == []
    assert geo.flow_paths == []
    assert geo.attachments == []

