"""
magnet/adapters/rendering_adapter.py

TA.3: Rendering Adapter Layer.

This adapter consumes kernel geometry exports and produces a rendering-friendly
scene structure. It is intentionally "thin":
- It does not touch DesignState directly.
- It only depends on kernel exports (TA.4) and numpy.
- No WebGL implementation details are required for this layer to exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from magnet.kernel.geometry_export import Body, GeometryExport, Section, Transform3D


@dataclass(frozen=True)
class RenderableMesh:
    """
    Rendering-ready mesh (generic).
    """

    vertices: np.ndarray  # shape (N, 3)
    indices: np.ndarray  # shape (M, 2) line segments for now
    material_id: str = "default"


@dataclass
class SceneNode:
    node_id: str
    mesh: Optional[RenderableMesh] = None
    transform: np.ndarray = field(default_factory=lambda: np.eye(4, dtype=float))
    children: List["SceneNode"] = field(default_factory=list)


class RenderingAdapter:
    """
    Translates kernel geometry into a generic scene graph.
    """

    def __init__(self, *, tessellation_quality: str = "medium") -> None:
        self._quality = str(tessellation_quality)

    def build_scene(self, export: GeometryExport) -> SceneNode:
        """
        Build a scene graph from kernel geometry.
        """
        root = SceneNode(node_id="root", mesh=None)

        bodies = export.get_bodies()
        sections = export.get_sections()
        transforms = export.get_component_transforms()

        # Body grouping nodes
        by_body: dict[str, list[Section]] = {}
        for s in sections:
            by_body.setdefault(str(s.body_id), []).append(s)

        for b in bodies:
            body_node = SceneNode(node_id=f"body:{b.body_id}")
            root.children.append(body_node)

            # Add section polyline meshes
            for sec in by_body.get(str(b.body_id), []):
                mesh = _section_as_polyline_mesh(sec)
                body_node.children.append(SceneNode(node_id=f"section:{sec.section_id}", mesh=mesh))

        # Components (if any transforms exported)
        if transforms:
            comp_root = SceneNode(node_id="components")
            for cid, tf in transforms.items():
                comp_root.children.append(SceneNode(node_id=f"component:{cid}", transform=tf.matrix))
            root.children.append(comp_root)

        return root


def _section_as_polyline_mesh(sec: Section) -> RenderableMesh:
    # Represent section curve as line segments for rendering; true surface tessellation
    # belongs in rendering/WebGL layer.
    verts = np.array([[x, y, z] for (x, y, z) in (sec.points or [])], dtype=float)
    if verts.shape[0] < 2:
        idx = np.zeros((0, 2), dtype=int)
    else:
        idx = np.array([[i, i + 1] for i in range(verts.shape[0] - 1)], dtype=int)
    return RenderableMesh(vertices=verts, indices=idx, material_id="hull_section")

