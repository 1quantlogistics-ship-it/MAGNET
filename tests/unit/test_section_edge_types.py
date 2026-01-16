from magnet.kernel.stdlib.section_compiler import compile_section


def test_section_edge_types_are_compiled_to_hard_edges():
    """
    Ensure geometry.section.edge_types is honored and produces EdgeType.HARD
    on the corresponding SectionPoint(s).
    """
    r = {
        "_type": "geometry.section",
        "_id": "s",
        "station": 0.5,
        "definition_type": "polygon",
        "points": [[0.0, -1.0], [1.0, -0.5], [2.0, 0.0]],
        "edge_types": ["smooth", "hard", "smooth"],
    }
    s = compile_section(r, loa=10.0)
    # middle point should be HARD
    assert s.points[1].edge_type.value in ("hard", "crease")


def test_section_points_negative_y_normalized_via_type_registry_on_update():
    """
    validate_resource normalization should make negative y magnitudes canonical (abs(y)).
    This prevents sign mistakes from breaking multihull tessellation conventions.
    """
    from magnet.kernel.stdlib.parser import parse
    from magnet.kernel.stdlib.expander import expand

    state = {
        "resources": {
            "s1": {
                "_type": "geometry.section",
                "_id": "s1",
                "station": 0.5,
                "body_id": "main",
                "definition_type": "polygon",
                "points": [[0.0, -1.0], [1.0, 0.0]],
            }
        }
    }

    program_text = "UPDATE s1 { points: [[-2.0, -1.0], [-1.0, 0.0]] }"
    res = expand(parse(program_text), state)
    assert not res.errors, res.errors
    action = res.actions[0]
    pts = action.value["points"]
    assert pts[0][0] == 2.0 and pts[1][0] == 1.0


