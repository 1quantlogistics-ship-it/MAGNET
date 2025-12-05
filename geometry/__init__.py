"""
Geometry Reference Model for naval vessel design.

Provides frame numbering, zone definitions, and structural member placement
to bridge hull parameters to structural layout.

Key Components:
- frames: Frame numbering, spacing, and locations
- zones: Zone definitions mapping position to pressure zones
- members: Structural member placement (stiffeners, frames, girders)
- reference: Coordinate system and station definitions

References:
- ABS HSNC 2023 Part 3 - Hull Structure
- Ship Structure Committee guidelines
"""

from .reference import (
    CoordinateSystem,
    Station,
    get_station_at_x,
    get_stations,
)
from .frames import (
    Frame,
    FrameSystem,
    get_frame_locations,
    get_frame_at_x,
    get_frames_in_zone,
)
from .zones import (
    StructuralZone,
    ZoneType,
    get_zone_for_position,
    get_zone_boundaries,
    get_all_zones,
)
from .members import (
    StructuralMember,
    MemberType,
    get_stiffener_positions,
    get_frame_members,
    generate_structural_layout,
    StructuralLayout,
)

__all__ = [
    # Reference
    "CoordinateSystem",
    "Station",
    "get_station_at_x",
    "get_stations",
    # Frames
    "Frame",
    "FrameSystem",
    "get_frame_locations",
    "get_frame_at_x",
    "get_frames_in_zone",
    # Zones
    "StructuralZone",
    "ZoneType",
    "get_zone_for_position",
    "get_zone_boundaries",
    "get_all_zones",
    # Members
    "StructuralMember",
    "MemberType",
    "get_stiffener_positions",
    "get_frame_members",
    "generate_structural_layout",
    "StructuralLayout",
]
