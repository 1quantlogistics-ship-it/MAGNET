"""
vision/renderer.py - 3D rendering engine v1.1

Module 52: Vision Subsystem

Provides rendering capabilities for hull geometry visualization.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
import uuid
import logging

if TYPE_CHECKING:
    from .geometry import Mesh

logger = logging.getLogger("vision.renderer")


class ViewAngle(Enum):
    """Standard view angles for rendering."""
    PERSPECTIVE = "perspective"
    FRONT = "front"
    SIDE = "side"
    TOP = "top"
    ISOMETRIC = "isometric"
    BOW = "bow"
    STERN = "stern"
    PROFILE = "profile"


class RenderStyle(Enum):
    """Rendering styles."""
    WIREFRAME = "wireframe"
    SOLID = "solid"
    SHADED = "shaded"
    TEXTURED = "textured"
    OUTLINE = "outline"


@dataclass
class RenderConfig:
    """Configuration for rendering."""

    width: int = 1920
    height: int = 1080
    background_color: str = "#FFFFFF"
    line_color: str = "#333333"
    fill_color: str = "#4A90D9"
    style: RenderStyle = RenderStyle.SHADED
    show_grid: bool = True
    show_axes: bool = True
    show_waterline: bool = True
    antialiasing: bool = True
    shadows: bool = True


@dataclass
class Snapshot:
    """A rendered snapshot."""

    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    phase: str = ""
    view: ViewAngle = ViewAngle.PERSPECTIVE
    style: RenderStyle = RenderStyle.SHADED

    image_path: Optional[str] = None
    thumbnail_path: Optional[str] = None

    width: int = 1920
    height: int = 1080

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "phase": self.phase,
            "view": self.view.value,
            "style": self.style.value,
            "image_path": self.image_path,
            "thumbnail_path": self.thumbnail_path,
            "width": self.width,
            "height": self.height,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Renderer:
    """
    3D rendering engine for hull visualization.

    Provides software-based rendering for environments without
    GPU acceleration. Can generate wireframe and basic shaded views.
    """

    def __init__(self, config: Optional[RenderConfig] = None):
        self.config = config or RenderConfig()
        self._cache: Dict[str, Snapshot] = {}

    def render_views(
        self,
        mesh: "Mesh",
        views: List[ViewAngle] = None,
        output_dir: str = "/tmp/magnet_render",
        phase: str = "",
    ) -> List[Snapshot]:
        """
        Render mesh from multiple view angles.

        Args:
            mesh: Mesh to render
            views: List of view angles (defaults to perspective)
            output_dir: Directory for output images
            phase: Phase name for snapshot metadata

        Returns:
            List of Snapshot objects
        """
        if views is None:
            views = [ViewAngle.PERSPECTIVE]

        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        snapshots = []
        for view in views:
            snapshot = self._render_view(mesh, view, output_dir, phase)
            snapshots.append(snapshot)
            self._cache[snapshot.snapshot_id] = snapshot

        return snapshots

    def _render_view(
        self,
        mesh: "Mesh",
        view: ViewAngle,
        output_dir: str,
        phase: str,
    ) -> Snapshot:
        """Render a single view."""

        snapshot = Snapshot(
            phase=phase,
            view=view,
            style=self.config.style,
            width=self.config.width,
            height=self.config.height,
        )

        # Generate SVG representation (software rendering)
        svg_content = self._generate_svg(mesh, view)

        # Save SVG
        filename = f"{mesh.mesh_id}_{view.value}_{snapshot.snapshot_id}.svg"
        filepath = Path(output_dir) / filename
        filepath.write_text(svg_content)

        snapshot.image_path = str(filepath)

        logger.debug(f"Rendered {view.value} view to {filepath}")

        return snapshot

    def _generate_svg(self, mesh: "Mesh", view: ViewAngle) -> str:
        """
        Generate SVG representation of mesh.

        Uses simple orthographic projection for 2D rendering.
        """
        width = self.config.width
        height = self.config.height

        # Get projection matrix based on view
        proj = self._get_projection(view)

        # Project vertices to 2D
        points_2d = []
        mesh.compute_bounds()

        if mesh.bounds_min and mesh.bounds_max:
            # Calculate scale and offset for centering
            dim_x = mesh.bounds_max.x - mesh.bounds_min.x
            dim_y = mesh.bounds_max.y - mesh.bounds_min.y
            dim_z = mesh.bounds_max.z - mesh.bounds_min.z

            max_dim = max(dim_x, dim_y, dim_z, 0.001)
            scale = min(width, height) * 0.8 / max_dim

            cx = (mesh.bounds_min.x + mesh.bounds_max.x) / 2
            cy = (mesh.bounds_min.y + mesh.bounds_max.y) / 2
            cz = (mesh.bounds_min.z + mesh.bounds_max.z) / 2
        else:
            scale = 10.0
            cx, cy, cz = 0, 0, 0

        for v in mesh.vertices:
            x, y = self._project_point(
                v.x - cx, v.y - cy, v.z - cz,
                proj, scale, width / 2, height / 2
            )
            points_2d.append((x, y))

        # Generate SVG
        lines = [
            f'<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            f'  <rect width="100%" height="100%" fill="{self.config.background_color}"/>',
        ]

        # Add grid if enabled
        if self.config.show_grid:
            lines.append(self._generate_grid(width, height))

        # Draw edges from faces
        lines.append(f'  <g stroke="{self.config.line_color}" stroke-width="1" fill="none">')

        drawn_edges = set()
        for face in mesh.faces:
            verts = face.vertices
            for i in range(len(verts)):
                v1_idx = verts[i]
                v2_idx = verts[(i + 1) % len(verts)]

                edge = tuple(sorted([v1_idx, v2_idx]))
                if edge not in drawn_edges and v1_idx < len(points_2d) and v2_idx < len(points_2d):
                    drawn_edges.add(edge)
                    x1, y1 = points_2d[v1_idx]
                    x2, y2 = points_2d[v2_idx]
                    lines.append(f'    <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')

        lines.append('  </g>')

        # Add waterline if enabled
        if self.config.show_waterline:
            wl_y = height / 2 + cz * scale  # Approximate waterline position
            lines.append(f'  <line x1="0" y1="{wl_y:.1f}" x2="{width}" y2="{wl_y:.1f}" stroke="#0066CC" stroke-width="2" stroke-dasharray="10,5"/>')

        # Add title
        lines.append(f'  <text x="10" y="30" font-family="sans-serif" font-size="16" fill="#333">MAGNET Hull - {view.value.title()} View</text>')

        lines.append('</svg>')

        return '\n'.join(lines)

    def _get_projection(self, view: ViewAngle) -> Dict[str, float]:
        """Get projection parameters for view angle."""
        projections = {
            ViewAngle.PERSPECTIVE: {"rx": 0.7, "ry": 0.7, "rz": 0.0},
            ViewAngle.FRONT: {"rx": 0.0, "ry": 1.0, "rz": 0.0},
            ViewAngle.SIDE: {"rx": 1.0, "ry": 0.0, "rz": 0.0},
            ViewAngle.TOP: {"rx": 0.0, "ry": 0.0, "rz": 1.0},
            ViewAngle.ISOMETRIC: {"rx": 0.577, "ry": 0.577, "rz": 0.577},
            ViewAngle.BOW: {"rx": 0.0, "ry": 0.8, "rz": 0.2},
            ViewAngle.STERN: {"rx": 0.0, "ry": -0.8, "rz": 0.2},
            ViewAngle.PROFILE: {"rx": 1.0, "ry": 0.0, "rz": 0.0},
        }
        return projections.get(view, projections[ViewAngle.PERSPECTIVE])

    def _project_point(
        self,
        x: float, y: float, z: float,
        proj: Dict[str, float],
        scale: float,
        offset_x: float,
        offset_y: float,
    ) -> tuple:
        """Project 3D point to 2D using simple orthographic projection."""
        rx, ry, rz = proj["rx"], proj["ry"], proj["rz"]

        # Simple orthographic projection
        px = x * rx + y * ry
        py = z + x * rz * 0.3 + y * rz * 0.3

        return (
            offset_x + px * scale,
            offset_y - py * scale  # Flip Y for SVG coordinates
        )

    def _generate_grid(self, width: int, height: int) -> str:
        """Generate background grid SVG."""
        grid_size = 50
        lines = ['  <g stroke="#EEEEEE" stroke-width="1">']

        for x in range(0, width, grid_size):
            lines.append(f'    <line x1="{x}" y1="0" x2="{x}" y2="{height}"/>')
        for y in range(0, height, grid_size):
            lines.append(f'    <line x1="0" y1="{y}" x2="{width}" y2="{y}"/>')

        lines.append('  </g>')
        return '\n'.join(lines)

    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """Get cached snapshot by ID."""
        return self._cache.get(snapshot_id)

    def clear_cache(self) -> None:
        """Clear snapshot cache."""
        self._cache.clear()
