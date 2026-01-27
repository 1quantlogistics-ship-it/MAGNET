"""
Planarity Gate Tests

1) Prove the planarity gate can detect non-planar panels (validator level).
2) Prove PlanarityGateError blocks 3D scene rendering (service level).
"""

import pytest
from unittest.mock import patch


class MockStateManager:
    def __init__(self, values=None):
        self._values = values or {}

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value, source=None):
        self._values[key] = value

    def to_dict(self):
        return dict(self._values)


def test_planarity_validator_raises_on_warp_violation():
    from magnet.kernel.validators.planarity import _warp_factor, PlanarityValidator
    from magnet.hull_gen.geometry import Point3D

    # Construct a deliberately warped quad and prove the warp exceeds the gate threshold.
    p0 = Point3D(0.0, 0.0, 0.0)
    p1 = Point3D(0.0, 1.0, 1.0)
    p2 = Point3D(1.0, 0.0, 0.0)
    p3 = Point3D(1.0, 1.0, 1.2)  # out of plane

    w = float(_warp_factor(p0, p1, p2, p3))
    assert w > PlanarityValidator.WARP_GATE_MAX


def test_planarity_gate_blocks_geometry_service_scene_generation():
    from magnet.webgl.geometry_service import GeometryService
    from magnet.webgl.schema import LODLevel
    from magnet.webgl.interfaces import HullGeometryData, HullSection, SectionVertex, Point3D
    from magnet.kernel.validators.planarity import PlanarityGateError

    sm = MockStateManager({"design_version": 1, "kernel.physics_last_validated_version": 1})
    svc = GeometryService(state_manager=sm)

    # Construct two adjacent sections with a warped quad:
    # p3 is lifted off the plane of (p0,p1,p2) to exceed the warp threshold.
    def _v(x, y, z):
        return SectionVertex(position=Point3D(x=float(x), y=float(y), z=float(z)))

    s0 = HullSection(
        station=0.0,
        points=[_v(0.0, 0.0, 0.0), _v(0.0, 1.0, 1.0)],
        body_id="main",
    )
    s1 = HullSection(
        station=1.0,
        points=[_v(1.0, 0.0, 0.0), _v(1.0, 1.0, 1.2)],  # z bumped to create warp
        body_id="main",
    )

    fake_geom = HullGeometryData(
        design_id="d1",
        version_id="d1:v1",
        sections=[s0, s1],
        keel_profile=[],
        stem_profile=[],
        openings=[],
        flow_paths=[],
        attachments=[],
    )

    # Ensure the service takes the panelized path.
    fake_geom.metadata = {"surface_definition": "panelized"}  # type: ignore[attr-defined]

    with patch.object(svc._grm_provider, "get_hull_geometry", return_value=fake_geom):
        with pytest.raises(PlanarityGateError):
            svc.get_scene(design_id="d1", lod=LODLevel.MEDIUM, allow_visual_only=False)

