import numpy as np

from magnet.adapters.rendering_adapter import RenderingAdapter
from magnet.kernel.geometry_export import Body, GeometryExport, Section, Transform3D


class _StubExport:
    def get_sections(self):
        return [
            Section(section_id="s0", station=0.0, body_id="main", points=[(0.0, 0.0, 0.0), (0.0, 1.0, 0.0)]),
            Section(section_id="s1", station=0.5, body_id="main", points=[(1.0, 0.0, 0.0), (1.0, 1.0, 0.0)]),
        ]

    def get_bodies(self):
        return [Body(body_id="main", metadata={})]

    def get_component_transforms(self):
        return {"c0": Transform3D(matrix=np.eye(4, dtype=float))}


def test_rendering_adapter_builds_scene_without_design_state_dependency():
    adapter = RenderingAdapter()
    scene = adapter.build_scene(_StubExport())
    assert scene.node_id == "root"
    assert len(scene.children) >= 1
    # Expect at least one mesh node below body
    body = next(n for n in scene.children if n.node_id == "body:main")
    assert any(ch.mesh is not None for ch in body.children)

