from magnet.kernel.stdlib.type_registry import validate_resource


def test_geometry_section_polygon_points_must_be_2d_pairs():
    """
    Regression: prevent accidental [x,y,z] triples from being accepted as polygon section points.
    Polygon section points must be exactly [y,z] pairs; X comes from station.
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
    assert errors, "Expected validation errors for 3D polygon section points"
    assert any("points[0]" in e and "[y, z]" in e for e in errors), f"Unexpected errors: {errors}"


