"""
webgl/events.py - Geometry events for EventBus v1.1

Module 58: WebGL 3D Visualization
ALPHA OWNS THIS FILE.

Provides geometry-related events for EventBus integration.

Addresses: FM7 (Streaming under-specified)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum
import uuid
import logging

from .schema import MeshData, StructureSceneData, GeometryMode

logger = logging.getLogger("webgl.events")


# =============================================================================
# EVENT TYPES
# =============================================================================

class GeometryEventType(Enum):
    """Geometry-specific event types."""
    GEOMETRY_READY = "geometry_ready"
    GEOMETRY_INVALIDATED = "geometry_invalidated"
    GEOMETRY_FAILED = "geometry_failed"
    GEOMETRY_UPDATE = "geometry_update"


# =============================================================================
# EVENT CLASSES
# =============================================================================

@dataclass
class GeometryEvent:
    """Base class for geometry events."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    design_id: str = ""
    artifact: str = ""
    source: str = "webgl"


@dataclass
class GeometryReadyEvent(GeometryEvent):
    """Emitted when geometry generation completes."""
    event_type: str = "geometry_ready"
    mode: GeometryMode = GeometryMode.AUTHORITATIVE
    lod: str = "medium"
    mesh_id: str = ""
    vertex_count: int = 0
    face_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "design_id": self.design_id,
            "artifact": self.artifact,
            "source": self.source,
            "mode": self.mode.value,
            "lod": self.lod,
            "mesh_id": self.mesh_id,
            "vertex_count": self.vertex_count,
            "face_count": self.face_count,
        }


@dataclass
class GeometryInvalidatedEvent(GeometryEvent):
    """Emitted when geometry is invalidated and needs regeneration."""
    event_type: str = "geometry_invalidated"
    reason: str = ""
    source_phase: Optional[str] = None
    affected_components: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "design_id": self.design_id,
            "artifact": self.artifact,
            "source": self.source,
            "reason": self.reason,
            "source_phase": self.source_phase,
            "affected_components": self.affected_components,
        }


@dataclass
class GeometryFailedEvent(GeometryEvent):
    """Emitted when geometry generation fails."""
    event_type: str = "geometry_failed"
    error_code: str = ""
    error_message: str = ""
    recovery_hint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "design_id": self.design_id,
            "artifact": self.artifact,
            "source": self.source,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "recovery_hint": self.recovery_hint,
        }


# =============================================================================
# WEBSOCKET STREAMING MESSAGES
# =============================================================================

@dataclass
class GeometryUpdateMessage:
    """
    v1.1: Delta-based streaming message.

    Instead of full scene, send only changed components with versioning.
    """
    message_type: str = "geometry_update"
    update_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prev_update_id: str = ""  # Previous update for ordering
    design_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Changed components only (None = unchanged)
    hull: Optional[Dict[str, Any]] = None
    deck: Optional[Dict[str, Any]] = None
    structure: Optional[Dict[str, Any]] = None

    # Metadata
    is_full_update: bool = False  # True = ignore delta, replace all
    geometry_mode: str = "authoritative"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_type": self.message_type,
            "update_id": self.update_id,
            "prev_update_id": self.prev_update_id,
            "design_id": self.design_id,
            "timestamp": self.timestamp,
            "hull": self.hull,
            "deck": self.deck,
            "structure": self.structure,
            "is_full_update": self.is_full_update,
            "geometry_mode": self.geometry_mode,
        }

    @classmethod
    def from_mesh_data(
        cls,
        design_id: str,
        hull: Optional[MeshData] = None,
        deck: Optional[MeshData] = None,
        structure: Optional[StructureSceneData] = None,
        prev_update_id: str = "",
        is_full_update: bool = False,
        geometry_mode: GeometryMode = GeometryMode.AUTHORITATIVE,
    ) -> "GeometryUpdateMessage":
        """Create update message from mesh data."""
        return cls(
            design_id=design_id,
            prev_update_id=prev_update_id,
            hull=hull.to_dict() if hull else None,
            deck=deck.to_dict() if deck else None,
            structure=structure.to_dict() if structure else None,
            is_full_update=is_full_update,
            geometry_mode=geometry_mode.value,
        )


@dataclass
class GeometryFailedMessage:
    """WebSocket message for geometry failure."""
    message_type: str = "geometry_failed"
    error_code: str = ""
    error_message: str = ""
    recovery_hint: Optional[str] = None
    design_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_type": self.message_type,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "recovery_hint": self.recovery_hint,
            "design_id": self.design_id,
            "timestamp": self.timestamp,
        }


# =============================================================================
# EVENT EMISSION HELPERS
# =============================================================================

def emit_geometry_ready(
    design_id: str,
    mesh: MeshData,
    mode: GeometryMode,
    lod: str,
) -> None:
    """Emit a geometry ready event to the EventBus."""
    try:
        from magnet.ui.events import event_bus, EventType

        event = GeometryReadyEvent(
            design_id=design_id,
            artifact="geometry.hull",
            mode=mode,
            lod=lod,
            mesh_id=mesh.mesh_id,
            vertex_count=mesh.vertex_count,
            face_count=mesh.face_count,
        )

        event_bus.emit_simple(
            EventType.GEOMETRY_GENERATED,
            source="webgl.events",
            **event.to_dict(),
        )
    except Exception as e:
        logger.debug(f"Could not emit geometry_ready event: {e}")


def emit_geometry_invalidated(
    design_id: str,
    reason: str,
    source_phase: Optional[str] = None,
    affected_components: Optional[List[str]] = None,
) -> None:
    """Emit a geometry invalidated event to the EventBus."""
    try:
        from magnet.ui.events import event_bus, EventType

        event = GeometryInvalidatedEvent(
            design_id=design_id,
            artifact="geometry.hull",
            reason=reason,
            source_phase=source_phase,
            affected_components=affected_components or ["hull", "deck", "structure"],
        )

        # Use STATE_CHANGED if GEOMETRY_INVALIDATED not available
        event_type = getattr(EventType, 'GEOMETRY_INVALIDATED', EventType.STATE_CHANGED)

        event_bus.emit_simple(
            event_type,
            source="webgl.events",
            **event.to_dict(),
        )
    except Exception as e:
        logger.debug(f"Could not emit geometry_invalidated event: {e}")


def emit_geometry_failed(
    design_id: str,
    error_code: str,
    error_message: str,
    recovery_hint: Optional[str] = None,
) -> None:
    """Emit a geometry failed event to the EventBus."""
    try:
        from magnet.ui.events import event_bus, EventType

        event = GeometryFailedEvent(
            design_id=design_id,
            artifact="geometry.hull",
            error_code=error_code,
            error_message=error_message,
            recovery_hint=recovery_hint,
        )

        # Use VALIDATION_COMPLETED if GEOMETRY_FAILED not available
        event_type = getattr(EventType, 'GEOMETRY_FAILED', EventType.VALIDATION_COMPLETED)

        event_bus.emit_simple(
            event_type,
            source="webgl.events",
            **event.to_dict(),
        )
    except Exception as e:
        logger.debug(f"Could not emit geometry_failed event: {e}")
