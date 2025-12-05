"""
Structural member placement and layout.

Generates positions for structural members (stiffeners, frames, girders)
based on hull geometry, zone definitions, and spacing requirements.

Member Types:
- Stiffeners: Longitudinal reinforcing members on plating
- Frames: Transverse structural members
- Girders: Heavy longitudinal members
- Web frames: Heavy transverse members

References:
- ABS HSNC 2023 Part 3, Section 3 - Structural Arrangement
- DNV HSLC 2023 Pt.3 Ch.3
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

from .zones import PressureZone, ZoneType, get_zone_for_position, ZONE_DEFINITIONS
from .frames import Frame, FrameType, get_frame_locations


class MemberType(Enum):
    """Types of structural members."""
    STIFFENER = "stiffener"           # Longitudinal plate stiffener
    FRAME = "frame"                   # Transverse frame
    WEB_FRAME = "web_frame"           # Heavy transverse web frame
    GIRDER = "girder"                 # Longitudinal girder
    FLOOR = "floor"                   # Bottom transverse member
    KEEL = "keel"                     # Center girder
    DECK_BEAM = "deck_beam"           # Transverse deck member
    BULKHEAD_STIFFENER = "bulkhead_stiffener"


class MemberOrientation(Enum):
    """Member orientation."""
    LONGITUDINAL = "longitudinal"     # Runs fore-aft
    TRANSVERSE = "transverse"         # Runs port-starboard
    VERTICAL = "vertical"             # Runs up-down


@dataclass
class StructuralMember:
    """
    Individual structural member with position and properties.

    Attributes:
        member_type: Type of structural member
        orientation: Member orientation
        zone: Pressure zone where member is located
        x_start: Start x position (m from AP)
        x_end: End x position (m from AP)
        y_position: Y position (m from centerline)
        z_position: Z position (m above baseline)
        spacing_index: Index in spacing pattern (0, 1, 2...)
        frame_number: Frame number if applicable
    """
    member_type: MemberType
    orientation: MemberOrientation
    zone: PressureZone
    x_start: float
    x_end: float
    y_position: float
    z_position: float
    spacing_index: int = 0
    frame_number: Optional[int] = None

    @property
    def length(self) -> float:
        """Member length in meters."""
        return abs(self.x_end - self.x_start)

    def __repr__(self) -> str:
        return (f"{self.member_type.value} at y={self.y_position:.2f}m, "
                f"z={self.z_position:.2f}m, x={self.x_start:.2f}-{self.x_end:.2f}m")


@dataclass
class StructuralLayout:
    """
    Complete structural layout for a vessel zone or entire vessel.

    Attributes:
        length_bp: Length between perpendiculars (m)
        beam: Beam (m)
        depth: Depth (m)
        draft: Draft (m)
        stiffener_spacing: Stiffener spacing (mm)
        frame_spacing: Frame spacing (mm)
        members: List of all structural members
    """
    length_bp: float
    beam: float
    depth: float
    draft: float
    stiffener_spacing: float      # mm
    frame_spacing: float          # mm
    members: List[StructuralMember] = field(default_factory=list)

    @property
    def stiffener_spacing_m(self) -> float:
        """Stiffener spacing in meters."""
        return self.stiffener_spacing / 1000.0

    @property
    def frame_spacing_m(self) -> float:
        """Frame spacing in meters."""
        return self.frame_spacing / 1000.0

    @property
    def total_stiffeners(self) -> int:
        """Total number of stiffeners."""
        return sum(1 for m in self.members if m.member_type == MemberType.STIFFENER)

    @property
    def total_frames(self) -> int:
        """Total number of frames."""
        return sum(1 for m in self.members
                   if m.member_type in (MemberType.FRAME, MemberType.WEB_FRAME))

    def get_members_by_type(self, member_type: MemberType) -> List[StructuralMember]:
        """Get all members of a specific type."""
        return [m for m in self.members if m.member_type == member_type]

    def get_members_in_zone(self, zone: PressureZone) -> List[StructuralMember]:
        """Get all members in a specific zone."""
        return [m for m in self.members if m.zone == zone]

    def get_members_at_frame(self, frame_number: int) -> List[StructuralMember]:
        """Get all members at a specific frame."""
        return [m for m in self.members if m.frame_number == frame_number]


def get_stiffener_positions(
    zone: PressureZone,
    stiffener_spacing: float,
    length_bp: float,
    beam: float,
    depth: float,
    draft: float,
) -> List[StructuralMember]:
    """
    Generate stiffener positions for a zone.

    Stiffeners run longitudinally on shell plating, spaced transversely.
    Bottom stiffeners are typically closer spaced than side stiffeners.

    Args:
        zone: Pressure zone
        stiffener_spacing: Stiffener spacing (mm)
        length_bp: Length between perpendiculars (m)
        beam: Beam (m)
        depth: Depth (m)
        draft: Draft (m)

    Returns:
        List of StructuralMember objects for stiffeners
    """
    stiffeners = []
    spacing_m = stiffener_spacing / 1000.0

    # Get zone boundaries
    if zone not in ZONE_DEFINITIONS:
        return stiffeners

    zone_def = ZONE_DEFINITIONS[zone]
    x_start = zone_def["x_start"] * length_bp
    x_end = zone_def["x_end"] * length_bp
    z_start = zone_def["z_start"] * depth
    z_end = zone_def["z_end"] * depth

    # Determine stiffener layout based on zone type
    zone_type = zone_def["zone_type"]

    if zone_type == ZoneType.BOTTOM:
        # Bottom stiffeners: run longitudinally, spaced across beam
        num_stiffeners = int(beam / spacing_m) + 1
        for i in range(num_stiffeners):
            y = -beam / 2 + i * spacing_m
            if abs(y) <= beam / 2:
                stiffeners.append(StructuralMember(
                    member_type=MemberType.STIFFENER,
                    orientation=MemberOrientation.LONGITUDINAL,
                    zone=zone,
                    x_start=x_start,
                    x_end=x_end,
                    y_position=y,
                    z_position=(z_start + z_end) / 2,
                    spacing_index=i,
                ))

    elif zone_type == ZoneType.SIDE:
        # Side stiffeners: run longitudinally, spaced vertically
        num_stiffeners = int((z_end - z_start) / spacing_m) + 1
        for i in range(num_stiffeners):
            z = z_start + i * spacing_m
            if z_start <= z <= z_end:
                # Port side
                stiffeners.append(StructuralMember(
                    member_type=MemberType.STIFFENER,
                    orientation=MemberOrientation.LONGITUDINAL,
                    zone=zone,
                    x_start=x_start,
                    x_end=x_end,
                    y_position=beam / 2,  # Port
                    z_position=z,
                    spacing_index=i,
                ))
                # Starboard side
                stiffeners.append(StructuralMember(
                    member_type=MemberType.STIFFENER,
                    orientation=MemberOrientation.LONGITUDINAL,
                    zone=zone,
                    x_start=x_start,
                    x_end=x_end,
                    y_position=-beam / 2,  # Starboard
                    z_position=z,
                    spacing_index=i,
                ))

    elif zone_type == ZoneType.DECK:
        # Deck stiffeners: run longitudinally, spaced across beam
        num_stiffeners = int(beam / spacing_m) + 1
        for i in range(num_stiffeners):
            y = -beam / 2 + i * spacing_m
            if abs(y) <= beam / 2:
                stiffeners.append(StructuralMember(
                    member_type=MemberType.STIFFENER,
                    orientation=MemberOrientation.LONGITUDINAL,
                    zone=zone,
                    x_start=x_start,
                    x_end=x_end,
                    y_position=y,
                    z_position=depth,  # At deck level
                    spacing_index=i,
                ))

    return stiffeners


def get_frame_members(
    frame_number: int,
    frame_x: float,
    beam: float,
    depth: float,
    draft: float,
    length_bp: float,
    is_web_frame: bool = False,
) -> List[StructuralMember]:
    """
    Generate structural members for a transverse frame.

    A complete frame includes:
    - Bottom frame (floor)
    - Side frames (port and starboard)
    - Deck beam

    Args:
        frame_number: Frame number
        frame_x: X position of frame (m from AP)
        beam: Beam (m)
        depth: Depth (m)
        draft: Draft (m)
        length_bp: Length between perpendiculars (m)
        is_web_frame: Whether this is a heavy web frame

    Returns:
        List of StructuralMember objects for the frame
    """
    members = []
    member_type = MemberType.WEB_FRAME if is_web_frame else MemberType.FRAME

    # Determine zone for this x position
    x_norm = frame_x / length_bp if length_bp > 0 else 0.5
    if x_norm < 0.30:
        bottom_zone = PressureZone.BOTTOM_AFT
        side_zone = PressureZone.SIDE_AFT
    elif x_norm < 0.70:
        bottom_zone = PressureZone.BOTTOM_MIDSHIP
        side_zone = PressureZone.SIDE_MIDSHIP
    else:
        bottom_zone = PressureZone.BOTTOM_FORWARD
        side_zone = PressureZone.SIDE_FORWARD

    # Floor (bottom transverse)
    members.append(StructuralMember(
        member_type=MemberType.FLOOR,
        orientation=MemberOrientation.TRANSVERSE,
        zone=bottom_zone,
        x_start=frame_x,
        x_end=frame_x,
        y_position=0.0,  # Centerline
        z_position=0.0,  # At baseline
        frame_number=frame_number,
    ))

    # Side frames (port and starboard)
    members.append(StructuralMember(
        member_type=member_type,
        orientation=MemberOrientation.VERTICAL,
        zone=side_zone,
        x_start=frame_x,
        x_end=frame_x,
        y_position=beam / 2,  # Port
        z_position=depth / 2,  # Midheight
        frame_number=frame_number,
    ))
    members.append(StructuralMember(
        member_type=member_type,
        orientation=MemberOrientation.VERTICAL,
        zone=side_zone,
        x_start=frame_x,
        x_end=frame_x,
        y_position=-beam / 2,  # Starboard
        z_position=depth / 2,  # Midheight
        frame_number=frame_number,
    ))

    # Deck beam
    members.append(StructuralMember(
        member_type=MemberType.DECK_BEAM,
        orientation=MemberOrientation.TRANSVERSE,
        zone=PressureZone.DECK_WEATHER,
        x_start=frame_x,
        x_end=frame_x,
        y_position=0.0,  # Centerline
        z_position=depth,  # At deck
        frame_number=frame_number,
    ))

    return members


def get_girder_positions(
    length_bp: float,
    beam: float,
    depth: float,
    num_side_girders: int = 2,
) -> List[StructuralMember]:
    """
    Generate longitudinal girder positions.

    Girders are heavy longitudinal members that support stiffeners.
    Includes center keel and optional side girders.

    Args:
        length_bp: Length between perpendiculars (m)
        beam: Beam (m)
        depth: Depth (m)
        num_side_girders: Number of side girders per side

    Returns:
        List of StructuralMember objects for girders
    """
    girders = []

    # Center keel girder
    girders.append(StructuralMember(
        member_type=MemberType.KEEL,
        orientation=MemberOrientation.LONGITUDINAL,
        zone=PressureZone.BOTTOM_MIDSHIP,
        x_start=0.0,
        x_end=length_bp,
        y_position=0.0,  # Centerline
        z_position=0.0,  # At baseline
        spacing_index=0,
    ))

    # Side girders
    if num_side_girders > 0:
        girder_spacing = (beam / 2) / (num_side_girders + 1)
        for i in range(1, num_side_girders + 1):
            y_pos = i * girder_spacing
            # Port side
            girders.append(StructuralMember(
                member_type=MemberType.GIRDER,
                orientation=MemberOrientation.LONGITUDINAL,
                zone=PressureZone.BOTTOM_MIDSHIP,
                x_start=0.0,
                x_end=length_bp,
                y_position=y_pos,
                z_position=depth * 0.1,  # Slightly above baseline
                spacing_index=i,
            ))
            # Starboard side
            girders.append(StructuralMember(
                member_type=MemberType.GIRDER,
                orientation=MemberOrientation.LONGITUDINAL,
                zone=PressureZone.BOTTOM_MIDSHIP,
                x_start=0.0,
                x_end=length_bp,
                y_position=-y_pos,
                z_position=depth * 0.1,
                spacing_index=i,
            ))

    return girders


def generate_structural_layout(
    length_bp: float,
    beam: float,
    depth: float,
    draft: float,
    stiffener_spacing: float,
    frame_spacing: float,
    web_frame_interval: int = 4,
    include_girders: bool = True,
    zones: Optional[List[PressureZone]] = None,
) -> StructuralLayout:
    """
    Generate complete structural layout for vessel.

    Args:
        length_bp: Length between perpendiculars (m)
        beam: Beam (m)
        depth: Depth (m)
        draft: Draft (m)
        stiffener_spacing: Stiffener spacing (mm)
        frame_spacing: Frame spacing (mm)
        web_frame_interval: Web frame every N frames
        include_girders: Include longitudinal girders
        zones: Specific zones to generate (None = all primary zones)

    Returns:
        StructuralLayout with all members
    """
    layout = StructuralLayout(
        length_bp=length_bp,
        beam=beam,
        depth=depth,
        draft=draft,
        stiffener_spacing=stiffener_spacing,
        frame_spacing=frame_spacing,
    )

    # Default zones if not specified
    if zones is None:
        zones = [
            PressureZone.BOTTOM_FORWARD,
            PressureZone.BOTTOM_MIDSHIP,
            PressureZone.BOTTOM_AFT,
            PressureZone.SIDE_FORWARD,
            PressureZone.SIDE_MIDSHIP,
            PressureZone.SIDE_AFT,
            PressureZone.DECK_WEATHER,
        ]

    # Generate stiffeners for each zone
    for zone in zones:
        stiffeners = get_stiffener_positions(
            zone=zone,
            stiffener_spacing=stiffener_spacing,
            length_bp=length_bp,
            beam=beam,
            depth=depth,
            draft=draft,
        )
        layout.members.extend(stiffeners)

    # Generate frames
    frame_locations = get_frame_locations(length_bp, frame_spacing)
    for i, frame_x in enumerate(frame_locations):
        is_web = (i % web_frame_interval == 0) and i > 0
        frame_members = get_frame_members(
            frame_number=i,
            frame_x=frame_x,
            beam=beam,
            depth=depth,
            draft=draft,
            length_bp=length_bp,
            is_web_frame=is_web,
        )
        layout.members.extend(frame_members)

    # Generate girders
    if include_girders:
        girders = get_girder_positions(length_bp, beam, depth)
        layout.members.extend(girders)

    return layout


def summarize_layout(layout: StructuralLayout) -> Dict[str, int]:
    """
    Get summary counts of structural members.

    Args:
        layout: StructuralLayout to summarize

    Returns:
        Dict with member type counts
    """
    summary = {}
    for member_type in MemberType:
        count = sum(1 for m in layout.members if m.member_type == member_type)
        if count > 0:
            summary[member_type.value] = count
    return summary
