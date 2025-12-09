"""
webgl/__init__.py - WebGL 3D Visualization package v1.1
BRAVO OWNS THIS FILE.

Module 58: WebGL 3D Visualization
Provides real-time 3D hull visualization with WebSocket streaming.
"""

from __future__ import annotations

# BRAVO-owned modules
from .websocket_stream import (
    GeometryStreamManager,
    get_stream_manager,
    GeometryUpdateMessage,
    GeometryFailedMessage,
)
from .annotations import (
    Annotation3D,
    Measurement3D,
    AnnotationCategory,
    AnnotationStore,
    get_annotation_store,
)

__all__ = [
    # WebSocket streaming
    "GeometryStreamManager",
    "get_stream_manager",
    "GeometryUpdateMessage",
    "GeometryFailedMessage",
    # Annotations
    "Annotation3D",
    "Measurement3D",
    "AnnotationCategory",
    "AnnotationStore",
    "get_annotation_store",
]
