import pytest

from magnet.hull_gen.geometry import HullGeometry, HullSection, SectionPoint, Point3D
from magnet.physics.geometry_hydrostatics import compute_hydrostatics_from_geometry
from magnet.core.constants import EPSILON_GEOMETRY


def _rect_section(x: float, half_beam: float = 1.0, depth: float = 1.0) -> HullSection:
    """
    Simple rectangular half-section (port side) from keel (z=0) to deck (z=depth).
    Full beam is 2*half_beam after mirroring.
    """
    pts = [
        SectionPoint(position=Point3D(x=x, y=0.0, z=0.0)),
        SectionPoint(position=Point3D(x=x, y=half_beam, z=0.0)),
        SectionPoint(position=Point3D(x=x, y=half_beam, z=depth)),
        SectionPoint(position=Point3D(x=x, y=0.0, z=depth)),
    ]
    return HullSection(station=x / 10.0, x_position=x, points=pts)


def test_opening_void_volume_subtracts_displacement_and_shifts_lcb():
    # Prism: full-section area = (2*1.0)*1.0 = 2.0, length=10 -> volume=20.0, LCB=5.0, VCB=0.5
    s0 = _rect_section(0.0)
    s1 = _rect_section(5.0)
    s2 = _rect_section(10.0)
    geo = HullGeometry(sections=[s0, s1, s2])
    geo.openings = [
        {
            "_type": "geometry.opening",
            "_id": "o1",
            "shape": "rectangular",
            "position": [7.0, 0.0, 0.5],
            "dimensions": [0.5, 0.5],
            "void_volume_m3": 2.0,  # explicit semantics (Phase 3B)
            "body_id": "main",
            "surface_id": "hull_shell",
        }
    ]

    res = compute_hydrostatics_from_geometry(geo, draft=1.0, vcg=None, seawater_density=1000.0)
    assert res.displacement_m3 == pytest.approx(18.0, abs=EPSILON_GEOMETRY)
    # New LCB = (20*5 - 2*7)/18 = 86/18 = 4.777...
    assert res.lcb_m == pytest.approx(86.0 / 18.0, abs=1e-6)
    assert res.confidence in ("medium", "low")
    assert any("primitive volume corrections" in (w or "").lower() for w in (res.warnings or []))


def test_attachment_buoyancy_volume_adds_displacement_and_shifts_lcb():
    # Same base prism: volume=20.0, LCB=5.0
    s0 = _rect_section(0.0)
    s1 = _rect_section(5.0)
    s2 = _rect_section(10.0)
    geo = HullGeometry(sections=[s0, s1, s2])
    geo.attachments = [
        {
            "_type": "geometry.attachment",
            "_id": "a1",
            "parent_body_id": "main",
            "child_body_id": "pod_1",
            "buoyancy_volume_m3": 2.0,  # explicit semantics (Phase 3B)
            "buoyancy_center": [9.0, 0.0, 0.5],
            "offset_x_m": 0.0,
            "offset_y_m": 0.0,
            "offset_z_m": 0.0,
        }
    ]

    res = compute_hydrostatics_from_geometry(geo, draft=1.0, vcg=None, seawater_density=1000.0)
    assert res.displacement_m3 == pytest.approx(22.0, abs=EPSILON_GEOMETRY)
    # New LCB = (20*5 + 2*9)/22 = 118/22 = 5.3636...
    assert res.lcb_m == pytest.approx(118.0 / 22.0, abs=1e-6)
    assert res.confidence in ("medium", "low")
    assert any("primitive volume corrections" in (w or "").lower() for w in (res.warnings or []))

