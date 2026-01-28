"""
TASK-014: Hull Quality Gates (Resolution + Fairness)
"""

import math
from magnet.kernel.stdlib.quality_gates import check_resolution, check_fairness, QualityWarning
from magnet.hull_gen.geometry import HullSection, Point3D, SectionPoint


def _make_section(station: float, points):
    return HullSection(
        station=station,
        points=[SectionPoint(position=p) for p in points],
    )


def test_resolution_low_points_warns():
    section = _make_section(0.0, [Point3D(0, 0, i) for i in range(10)])
    warnings = check_resolution([section])
    assert any(w.code == "RESOLUTION_LOW" for w in warnings)


def test_resolution_high_points_warns():
    section = _make_section(0.0, [Point3D(0, 0, i) for i in range(130)])
    warnings = check_resolution([section])
    assert any(w.code == "RESOLUTION_HIGH" for w in warnings)


def test_fairness_spike_detected():
    # Create a sharp kink in YZ plane
    pts = [
        Point3D(0, 0.0, 0.0),
        Point3D(0, 0.0, 1.0),
        Point3D(0, 1.0, 1.0),  # 90 deg turn
        Point3D(0, 1.0, 2.0),
    ]
    section = _make_section(0.5, pts)
    warnings = check_fairness([section])
    assert any(w.code == "FAIRNESS_SPIKE" for w in warnings)
