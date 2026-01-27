from magnet.kernel.stdlib.type_registry import validate_resource


def test_geometry_section_polygon_points_allows_3d_triples_by_dropping_x():
    """
    Regression: LLMs sometimes emit polygon section points as [x,y,z] triples.
    The kernel deterministically drops X (since X comes from station) and treats them as [y,z].
    """
    errors = validate_resource(
        "geometry.section",
        {
            "station": 0.5,
            "definition_type": "polygon",
            "points": [
                [0.0, 0.0, -2.0],  # WRONG: 3D triple
                [1.0, 0.0, -1.0],
            ],
        },
    )
    assert not errors, f"Expected 3D triples to be normalized to [y,z] pairs (drop x). Errors: {errors}"


