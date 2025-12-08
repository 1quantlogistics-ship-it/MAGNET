"""
structural/grid.py - Structural grid schema.

ALPHA OWNS THIS FILE.

Section 21: Structural Grid.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .enums import FrameType


@dataclass
class Frame:
    """Transverse frame definition."""

    frame_number: int = 0
    """Frame number (0 = AP, positive forward)."""

    x_position: float = 0.0
    """Longitudinal position from AP (m)."""

    frame_type: FrameType = FrameType.ORDINARY
    """Type of frame."""

    is_web_frame: bool = False
    """Whether this is a web frame (heavier)."""

    is_bulkhead: bool = False
    """Whether this coincides with a bulkhead."""

    spacing_fwd: float = 0.0
    """Spacing to next forward frame (mm)."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_number": self.frame_number,
            "x_position": round(self.x_position, 3),
            "frame_type": self.frame_type.value,
            "is_web_frame": self.is_web_frame,
            "is_bulkhead": self.is_bulkhead,
            "spacing_fwd": round(self.spacing_fwd, 1),
        }


@dataclass
class Bulkhead:
    """Bulkhead definition."""

    bulkhead_id: str = ""
    """Unique bulkhead identifier."""

    frame_number: int = 0
    """Frame number where bulkhead is located."""

    x_position: float = 0.0
    """Longitudinal position from AP (m)."""

    bulkhead_type: str = "watertight"
    """Type: watertight, non-watertight, collision, etc."""

    is_collision_bulkhead: bool = False
    """Whether this is the collision bulkhead."""

    compartment_fwd: str = ""
    """Compartment forward of bulkhead."""

    compartment_aft: str = ""
    """Compartment aft of bulkhead."""

    height_m: float = 0.0
    """Bulkhead height (m)."""

    width_m: float = 0.0
    """Bulkhead width at base (m)."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bulkhead_id": self.bulkhead_id,
            "frame_number": self.frame_number,
            "x_position": round(self.x_position, 3),
            "bulkhead_type": self.bulkhead_type,
            "is_collision_bulkhead": self.is_collision_bulkhead,
            "compartment_fwd": self.compartment_fwd,
            "compartment_aft": self.compartment_aft,
            "height_m": round(self.height_m, 2),
            "width_m": round(self.width_m, 2),
        }


@dataclass
class StructuralGrid:
    """Complete structural grid definition."""

    # === DIMENSIONS ===
    loa: float = 0.0
    """Length overall (m)."""

    lwl: float = 0.0
    """Length on waterline (m)."""

    beam: float = 0.0
    """Maximum beam (m)."""

    depth: float = 0.0
    """Moulded depth (m)."""

    # === FRAME SYSTEM ===
    frame_spacing_mm: float = 500.0
    """Standard frame spacing (mm)."""

    web_frame_spacing: int = 4
    """Web frame every N ordinary frames."""

    frames: List[Frame] = field(default_factory=list)
    """All frames from AP to FP."""

    # === BULKHEADS ===
    bulkheads: List[Bulkhead] = field(default_factory=list)
    """All bulkheads."""

    collision_bulkhead_frame: int = 0
    """Frame number of collision bulkhead."""

    # === LONGITUDINAL SPACING ===
    bottom_long_spacing_mm: float = 300.0
    """Bottom longitudinal spacing (mm)."""

    side_long_spacing_mm: float = 400.0
    """Side longitudinal spacing (mm)."""

    deck_long_spacing_mm: float = 500.0
    """Deck longitudinal spacing (mm)."""

    def get_bulkheads(self) -> List[Bulkhead]:
        """Get all bulkheads."""
        return self.bulkheads

    def get_web_frames(self) -> List[Frame]:
        """Get all web frames."""
        return [f for f in self.frames if f.is_web_frame]

    def get_frame_at_x(self, x: float, tolerance: float = 0.1) -> Optional[Frame]:
        """Get frame closest to x position."""
        for frame in self.frames:
            if abs(frame.x_position - x) < tolerance:
                return frame
        return None

    def get_frames_in_range(self, x_start: float, x_end: float) -> List[Frame]:
        """Get all frames within x range."""
        return [f for f in self.frames
                if x_start <= f.x_position <= x_end]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loa": round(self.loa, 2),
            "lwl": round(self.lwl, 2),
            "beam": round(self.beam, 2),
            "depth": round(self.depth, 2),
            "frame_spacing_mm": self.frame_spacing_mm,
            "web_frame_spacing": self.web_frame_spacing,
            "frames": [f.to_dict() for f in self.frames],
            "bulkheads": [b.to_dict() for b in self.bulkheads],
            "collision_bulkhead_frame": self.collision_bulkhead_frame,
            "bottom_long_spacing_mm": self.bottom_long_spacing_mm,
            "side_long_spacing_mm": self.side_long_spacing_mm,
            "deck_long_spacing_mm": self.deck_long_spacing_mm,
        }
