"""
Feature Preservation Audit: HARD edge anchor indices must not drift.

Panelized harmonization/upsampling is allowed to add vertices, but it must not
move the indices of vertices explicitly marked as EdgeType.HARD.
"""

from magnet.kernel.synthesis import harmonize_sections_global
from magnet.hull_gen.geometry import HullSection, SectionPoint, Point3D, EdgeType


def _make_section(x: float, zs: list[float], ys: list[float], hard_indices: set[int]) -> HullSection:
    pts = []
    for i, (z, y) in enumerate(zip(zs, ys)):
        et = EdgeType.HARD if i in hard_indices else EdgeType.SMOOTH
        pts.append(SectionPoint(position=Point3D(x=x, y=float(y), z=float(z)), edge_type=et))
    return HullSection(x_position=float(x), station=0.0, points=pts)


def test_panelized_harmonization_preserves_hard_edge_indices_exactly():
    # Base section: 8 vertices, hard chines at indices 2 and 5.
    zs8 = [0, 0.5, 1.0, 1.5, 2.0, 2.4, 2.7, 3.0]
    ys8 = [0, 0.2, 0.8, 1.0, 0.9, 0.6, 0.3, 0.0]
    hard = {2, 5}

    s8 = _make_section(0.0, zs8, ys8, hard)

    # Another section has higher resolution: forces target_n > 8.
    zs12 = [0, 0.3, 0.6, 1.0, 1.2, 1.5, 2.0, 2.2, 2.4, 2.7, 2.85, 3.0]
    ys12 = [0, 0.1, 0.25, 0.8, 0.9, 1.0, 0.9, 0.75, 0.6, 0.35, 0.15, 0.0]
    s12 = _make_section(1.0, zs12, ys12, hard_indices=set())

    out = harmonize_sections_global([s8, s12], surface_definition="panelized")

    # Find the upsampled version of the 8-vertex section (now length == 12)
    sec0 = out[0]
    assert len(sec0.points) == 12
    assert sec0.points[2].edge_type == EdgeType.HARD
    assert sec0.points[5].edge_type == EdgeType.HARD

