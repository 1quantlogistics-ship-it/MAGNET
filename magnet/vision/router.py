"""
vision/router.py - Vision request router v1.1

Module 52: Vision Subsystem

v1.1: Integrated with snapshot registry and phase hooks.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timezone
import logging

from .geometry import GeometryManager, Mesh
from .renderer import Renderer, Snapshot, ViewAngle, RenderStyle

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger("vision.router")


@dataclass
class VisionRequest:
    """Request for vision operation."""
    request_id: str = ""
    operation: str = ""  # generate, render, export, analyze, snapshot
    parameters: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class VisionResponse:
    """Response from vision operation."""
    request_id: str = ""
    success: bool = True
    result: Any = None
    snapshots: List[Snapshot] = field(default_factory=list)
    error: Optional[str] = None


class VisionRouter:
    """
    Routes vision requests to appropriate handlers.

    v1.1: Integrated with snapshot registry and phase hooks.
    """

    def __init__(self, state: Optional["StateManager"] = None):
        self.state = state

        self.geometry_manager = GeometryManager()
        self.renderer = Renderer()

        self._current_hull: Optional[Mesh] = None
        self._snapshots: Dict[str, Snapshot] = {}

    def process_request(self, request: VisionRequest) -> VisionResponse:
        """Process a vision request."""

        handlers = {
            "generate": self._handle_generate,
            "render": self._handle_render,
            "export": self._handle_export,
            "analyze": self._handle_analyze,
            "snapshot": self._handle_snapshot,
        }

        handler = handlers.get(request.operation)

        if not handler:
            return VisionResponse(
                request_id=request.request_id,
                success=False,
                error=f"Unknown operation: {request.operation}",
            )

        try:
            return handler(request)
        except Exception as e:
            logger.exception(f"Vision request failed: {e}")
            return VisionResponse(
                request_id=request.request_id,
                success=False,
                error=str(e),
            )

    def _handle_generate(self, request: VisionRequest) -> VisionResponse:
        """Generate geometry from state."""

        if not self.state:
            return VisionResponse(
                request_id=request.request_id,
                success=False,
                error="State not available",
            )

        # v1.1: generate_from_state uses get_state_value internally
        mesh = self.geometry_manager.generate_hull_from_state(self.state)
        self._current_hull = mesh

        return VisionResponse(
            request_id=request.request_id,
            success=True,
            result=mesh.to_dict(),
        )

    def _handle_render(self, request: VisionRequest) -> VisionResponse:
        """Render current geometry."""

        if not self._current_hull:
            gen_response = self._handle_generate(request)
            if not gen_response.success:
                return gen_response

        views = request.parameters.get("views", ["perspective"])
        output_dir = request.parameters.get("output_dir", "/tmp/magnet_render")
        phase = request.parameters.get("phase", "render")

        view_angles = []
        for v in views:
            try:
                view_angles.append(ViewAngle(v))
            except ValueError:
                view_angles.append(ViewAngle.PERSPECTIVE)

        snapshots = self.renderer.render_views(
            self._current_hull,
            views=view_angles,
            output_dir=output_dir,
        )

        # v1.1: Register snapshots in global registry (fixes blocker #8)
        try:
            from magnet.ui.utils import snapshot_registry

            for snapshot in snapshots:
                self._snapshots[snapshot.snapshot_id] = snapshot

                section_id = request.parameters.get(
                    "section_id",
                    f"{phase}_{snapshot.view.value}" if snapshot.view else f"{phase}_render"
                )

                if snapshot.image_path:
                    snapshot_registry.register(section_id, snapshot.image_path, phase)
        except ImportError:
            # ui.utils not available, just cache locally
            for snapshot in snapshots:
                self._snapshots[snapshot.snapshot_id] = snapshot

        return VisionResponse(
            request_id=request.request_id,
            success=True,
            snapshots=snapshots,
        )

    def _handle_export(self, request: VisionRequest) -> VisionResponse:
        """Export geometry to file."""

        if not self._current_hull:
            return VisionResponse(
                request_id=request.request_id,
                success=False,
                error="No geometry available. Run 'generate' first.",
            )

        format_type = request.parameters.get("format", "obj")
        output_path = request.parameters.get("path", f"/tmp/hull.{format_type}")

        if format_type == "obj":
            success = self.geometry_manager.export_obj(self._current_hull.mesh_id, output_path)
        elif format_type == "stl":
            success = self.geometry_manager.export_stl(self._current_hull.mesh_id, output_path)
        else:
            return VisionResponse(
                request_id=request.request_id,
                success=False,
                error=f"Unsupported format: {format_type}",
            )

        return VisionResponse(
            request_id=request.request_id,
            success=success,
            result={"path": output_path, "format": format_type},
        )

    def _handle_analyze(self, request: VisionRequest) -> VisionResponse:
        """Analyze geometry properties."""

        if not self._current_hull:
            return VisionResponse(
                request_id=request.request_id,
                success=False,
                error="No geometry available",
            )

        mesh = self._current_hull
        mesh.compute_bounds()

        analysis = {
            "vertex_count": len(mesh.vertices),
            "face_count": len(mesh.faces),
            "bounds": {
                "min": mesh.bounds_min.to_tuple() if mesh.bounds_min else None,
                "max": mesh.bounds_max.to_tuple() if mesh.bounds_max else None,
            },
            "dimensions": {
                "length": mesh.bounds_max.x - mesh.bounds_min.x if mesh.bounds_max else 0,
                "width": (mesh.bounds_max.y - mesh.bounds_min.y) if mesh.bounds_max else 0,
                "height": (mesh.bounds_max.z - mesh.bounds_min.z) if mesh.bounds_max else 0,
            },
        }

        return VisionResponse(
            request_id=request.request_id,
            success=True,
            result=analysis,
        )

    def _handle_snapshot(self, request: VisionRequest) -> VisionResponse:
        """Take a snapshot for a specific phase."""

        phase = request.parameters.get("phase", "current")
        view = request.parameters.get("view", "perspective")
        section_id = request.parameters.get("section_id", f"{phase}_render")

        if not self._current_hull:
            gen_response = self._handle_generate(request)
            if not gen_response.success:
                return gen_response

        try:
            view_angle = ViewAngle(view)
        except ValueError:
            view_angle = ViewAngle.PERSPECTIVE

        output_dir = request.parameters.get("output_dir", "/tmp/magnet_snapshots")

        snapshots = self.renderer.render_views(
            self._current_hull,
            views=[view_angle],
            output_dir=output_dir,
        )

        if snapshots:
            snapshot = snapshots[0]
            snapshot.phase = phase
            self._snapshots[snapshot.snapshot_id] = snapshot

            # v1.1: Register with snapshot registry (fixes blocker #8)
            try:
                from magnet.ui.utils import snapshot_registry
                if snapshot.image_path:
                    snapshot_registry.register(section_id, snapshot.image_path, phase)
            except ImportError:
                pass

        return VisionResponse(
            request_id=request.request_id,
            success=True,
            snapshots=snapshots,
        )

    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        return self._snapshots.get(snapshot_id)

    def list_snapshots(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._snapshots.values()]

    def get_snapshots_for_report(self, sections: List[str] = None) -> Dict[str, str]:
        """
        Get snapshot paths for report sections.

        v1.1: Uses snapshot registry for section_id mapping.
        """
        try:
            from magnet.ui.utils import snapshot_registry
            if sections:
                return {s: snapshot_registry.get(s) for s in sections if snapshot_registry.get(s)}
            return snapshot_registry.get_all()
        except ImportError:
            return {}
