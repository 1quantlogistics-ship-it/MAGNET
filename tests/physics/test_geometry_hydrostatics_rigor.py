import pytest

from magnet.hull_gen.geometry import HullGeometry, HullSection, SectionPoint, Point3D
from magnet.physics.geometry_hydrostatics import compute_hydrostatics_from_geometry


def _rect_section(x: float, station: float, half_beam: float, depth: float) -> HullSection:
    pts = [
        SectionPoint(position=Point3D(x=x, y=0.0, z=0.0)),
        SectionPoint(position=Point3D(x=x, y=half_beam, z=0.0)),
        SectionPoint(position=Point3D(x=x, y=half_beam, z=depth)),
        SectionPoint(position=Point3D(x=x, y=0.0, z=depth)),
    ]
    return HullSection(station=station, x_position=x, points=pts)


def test_prismatic_volume_matches_rectangle_sections():
    # A simple prismatic hull: constant rectangular section along x
    # Full breadth = 2*half_beam, submerged depth = draft
    half_beam = 1.5
    length = 10.0
    draft = 0.8

    geom = HullGeometry(
        sections=[
            _rect_section(x=0.0, station=0.0, half_beam=half_beam, depth=2.0),
            _rect_section(x=length, station=1.0, half_beam=half_beam, depth=2.0),
        ]
    )

    res = compute_hydrostatics_from_geometry(geom, draft=draft)

    expected_area = (2.0 * half_beam) * draft
    expected_volume = expected_area * length

    assert pytest.approx(res.displacement_m3, rel=1e-6, abs=1e-9) == expected_volume

