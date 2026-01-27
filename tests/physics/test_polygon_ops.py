from magnet.physics.polygon_ops import (
    normalize_polygon,
    clip_polygon_z_le,
    polygon_area_centroid,
)


def test_clip_rectangle_partially_submerged_area_centroid():
    # Rectangle in (y,z): width 2 (y=-1..1), height 2 (z=0..2)
    rect = [(-1.0, 0.0), (1.0, 0.0), (1.0, 2.0), (-1.0, 2.0)]

    # Clip at z<=1 -> rectangle becomes width 2, height 1 => area=2
    clipped = clip_polygon_z_le(rect, z_max=1.0)
    area, cy, cz = polygon_area_centroid(clipped)

    assert abs(area - 2.0) < 1e-9
    assert abs(cy - 0.0) < 1e-9
    assert abs(cz - 0.5) < 1e-9


def test_normalize_polygon_makes_ccw_and_closed():
    # Same rectangle but CW and unclosed
    rect_cw = [(-1.0, 0.0), (-1.0, 2.0), (1.0, 2.0), (1.0, 0.0)]
    norm = normalize_polygon(rect_cw)
    assert norm[0] == norm[-1]
    area, _, _ = polygon_area_centroid(norm)
    assert area > 0

