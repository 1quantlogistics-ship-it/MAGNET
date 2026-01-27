import pytest

from magnet.hull_gen.geometry import HullGeometry, HullSection, SectionPoint, Point3D
from magnet.physics.geometry_hydrostatics import GeometryHydrostaticsCalculator


def _rect_section(x: float, station: float, half_beam: float, depth: float) -> HullSection:
    # Simple rectangular half-section curve (port side), keel(z=0) → deck(z=depth)
    pts = [
        SectionPoint(position=Point3D(x=x, y=0.0, z=0.0)),
        SectionPoint(position=Point3D(x=x, y=half_beam, z=0.0)),
        SectionPoint(position=Point3D(x=x, y=half_beam, z=depth)),
        SectionPoint(position=Point3D(x=x, y=0.0, z=depth)),
    ]
    return HullSection(station=station, x_position=x, points=pts)


def test_geometry_hydrostatics_calculator_calculate_is_wired():
    geom = HullGeometry(
        sections=[
            _rect_section(x=0.0, station=0.0, half_beam=1.0, depth=1.0),
            _rect_section(x=10.0, station=1.0, half_beam=1.0, depth=1.0),
        ]
    )

    calc = GeometryHydrostaticsCalculator()

    # Should not raise NotImplementedError
    result = calc.calculate(geometry=geom, draft=0.5)

    assert result.displacement_m3 > 0
    assert result.waterplane_area_m2 > 0

