"""
Frame system for structural layout.

Frames are transverse structural members that define the vessel's shape
and provide primary structural support. Frame spacing is critical for
structural scantling calculations.

Frame numbering conventions:
- Frames numbered from AP (frame 0) forward
- Frame spacing typically 400-800mm for high-speed craft
- Web frames (heavier) at larger intervals (3-5 frame spacings)

References:
- ABS HSNC 2023 Part 3, Section 3 - Framing
- DNV HSLC 2023 Pt.3 Ch.3 Sec.6
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class FrameType(Enum):
    """Types of transverse frames."""
    TRANSVERSE = "transverse"      # Standard frame
    WEB_FRAME = "web_frame"        # Heavy web frame
    BULKHEAD = "bulkhead"          # Watertight bulkhead
    PARTIAL_BULKHEAD = "partial_bulkhead"


@dataclass
class Frame:
    """
    Transverse frame structural member.

    Attributes:
        number: Frame number (0 = AP)
        x: X coordinate of frame (m from AP)
        frame_type: Type of frame
        is_watertight: Whether frame is watertight
        zone: Longitudinal zone (forward, midship, aft)
    """
    number: int
    x: float                                  # m from AP
    frame_type: FrameType = FrameType.TRANSVERSE
    is_watertight: bool = False
    zone: str = "midship"

    def __repr__(self) -> str:
        type_str = f" ({self.frame_type.value})" if self.frame_type != FrameType.TRANSVERSE else ""
        return f"Frame {self.number}{type_str}: x={self.x:.3f}m"


@dataclass
class FrameSystem:
    """
    Complete frame system for vessel.

    Attributes:
        length_bp: Length between perpendiculars (m)
        frame_spacing: Standard frame spacing (mm)
        web_frame_interval: Web frame every N frames
        frames: List of all frames
        total_frames: Total number of frames
    """
    length_bp: float
    frame_spacing: float                      # mm
    web_frame_interval: int = 4               # Web frame every N frames
    frames: List[Frame] = field(default_factory=list)

    @property
    def total_frames(self) -> int:
        """Total number of frames."""
        return len(self.frames)

    @property
    def frame_spacing_m(self) -> float:
        """Frame spacing in meters."""
        return self.frame_spacing / 1000.0

    def get_frame(self, number: int) -> Optional[Frame]:
        """Get frame by number."""
        for frame in self.frames:
            if frame.number == number:
                return frame
        return None

    def get_frames_between(self, x_start: float, x_end: float) -> List[Frame]:
        """Get all frames between two x positions."""
        return [f for f in self.frames if x_start <= f.x <= x_end]

    def get_web_frames(self) -> List[Frame]:
        """Get all web frames."""
        return [f for f in self.frames if f.frame_type == FrameType.WEB_FRAME]

    def get_bulkheads(self) -> List[Frame]:
        """Get all bulkhead frames."""
        return [f for f in self.frames
                if f.frame_type in (FrameType.BULKHEAD, FrameType.PARTIAL_BULKHEAD)]


def calculate_frame_spacing(
    length_bp: float,
    speed_kts: float,
    hull_type: str = "semi_displacement",
) -> float:
    """
    Calculate recommended frame spacing per ABS HSNC.

    ABS HSNC 3-3-1/3.1: Frame spacing shall not exceed:
    - 2 × stiffener spacing for transverse framing
    - Typically 400-800mm for high-speed craft

    Args:
        length_bp: Length between perpendiculars (m)
        speed_kts: Design speed (knots)
        hull_type: Hull type (displacement, semi_displacement, planing)

    Returns:
        Recommended frame spacing in mm
    """
    # Base frame spacing from vessel length
    # Typical: 500mm for 30-40m, 600mm for 40-50m, 750mm for 50-70m
    if length_bp < 30:
        base_spacing = 400.0
    elif length_bp < 40:
        base_spacing = 500.0
    elif length_bp < 50:
        base_spacing = 600.0
    elif length_bp < 70:
        base_spacing = 750.0
    else:
        base_spacing = 800.0

    # Adjust for speed (higher speed = closer spacing)
    if speed_kts > 35:
        speed_factor = 0.85
    elif speed_kts > 25:
        speed_factor = 0.92
    else:
        speed_factor = 1.0

    # Adjust for hull type
    hull_factors = {
        "displacement": 1.0,
        "semi_displacement": 0.95,
        "planing": 0.90,
    }
    hull_factor = hull_factors.get(hull_type, 1.0)

    spacing = base_spacing * speed_factor * hull_factor

    # Round to nearest 25mm
    return round(spacing / 25) * 25


def get_frame_locations(
    length_bp: float,
    frame_spacing: float,
    start_x: float = 0.0,
) -> List[float]:
    """
    Generate frame x-locations along vessel length.

    Args:
        length_bp: Length between perpendiculars (m)
        frame_spacing: Frame spacing (mm)
        start_x: Starting x position (m from AP)

    Returns:
        List of x positions for each frame (m)
    """
    spacing_m = frame_spacing / 1000.0
    locations = []

    x = start_x
    while x <= length_bp + 0.001:  # Small tolerance
        locations.append(round(x, 4))
        x += spacing_m

    return locations


def get_frame_at_x(
    x: float,
    length_bp: float,
    frame_spacing: float,
) -> Tuple[int, float]:
    """
    Get nearest frame number and distance to a given x position.

    Args:
        x: X position (m from AP)
        length_bp: Length between perpendiculars (m)
        frame_spacing: Frame spacing (mm)

    Returns:
        Tuple of (frame_number, distance_to_frame in m)
    """
    spacing_m = frame_spacing / 1000.0

    # Calculate frame number
    frame_num = round(x / spacing_m)
    frame_x = frame_num * spacing_m

    # Clamp to valid range
    max_frame = int(length_bp / spacing_m)
    frame_num = max(0, min(frame_num, max_frame))
    frame_x = frame_num * spacing_m

    distance = abs(x - frame_x)

    return frame_num, distance


def get_frames_in_zone(
    zone: str,
    length_bp: float,
    frame_spacing: float,
) -> List[Frame]:
    """
    Get all frames in a longitudinal zone.

    Zones:
    - "forward": 0.67-1.0 LBP (bow region)
    - "midship": 0.33-0.67 LBP (parallel middle body)
    - "aft": 0.0-0.33 LBP (stern region)

    Args:
        zone: Zone name ("forward", "midship", "aft")
        length_bp: Length between perpendiculars (m)
        frame_spacing: Frame spacing (mm)

    Returns:
        List of frames in the specified zone
    """
    zone_bounds = {
        "aft": (0.0, 0.33),
        "midship": (0.33, 0.67),
        "forward": (0.67, 1.0),
    }

    if zone not in zone_bounds:
        raise ValueError(f"Unknown zone: {zone}. Use 'forward', 'midship', or 'aft'")

    x_start_norm, x_end_norm = zone_bounds[zone]
    x_start = x_start_norm * length_bp
    x_end = x_end_norm * length_bp

    spacing_m = frame_spacing / 1000.0
    frames = []

    # Find first frame in zone
    first_frame = int(x_start / spacing_m)
    if first_frame * spacing_m < x_start:
        first_frame += 1

    # Generate frames in zone
    frame_num = first_frame
    while True:
        x = frame_num * spacing_m
        if x > x_end:
            break

        frames.append(Frame(
            number=frame_num,
            x=x,
            frame_type=FrameType.TRANSVERSE,
            is_watertight=False,
            zone=zone,
        ))
        frame_num += 1

    return frames


def generate_frame_system(
    length_bp: float,
    frame_spacing: float,
    web_frame_interval: int = 4,
    bulkhead_positions: Optional[List[float]] = None,
) -> FrameSystem:
    """
    Generate complete frame system for vessel.

    Args:
        length_bp: Length between perpendiculars (m)
        frame_spacing: Frame spacing (mm)
        web_frame_interval: Web frame every N frames
        bulkhead_positions: List of bulkhead x positions (m)

    Returns:
        FrameSystem with all frames
    """
    spacing_m = frame_spacing / 1000.0
    frames = []

    # Generate all frame locations
    frame_num = 0
    while True:
        x = frame_num * spacing_m
        if x > length_bp + 0.001:
            break

        # Determine zone
        x_norm = x / length_bp if length_bp > 0 else 0
        if x_norm < 0.33:
            zone = "aft"
        elif x_norm < 0.67:
            zone = "midship"
        else:
            zone = "forward"

        # Determine frame type
        is_bulkhead = False
        if bulkhead_positions:
            for bh_x in bulkhead_positions:
                if abs(x - bh_x) < spacing_m / 2:
                    is_bulkhead = True
                    break

        if is_bulkhead:
            frame_type = FrameType.BULKHEAD
            is_watertight = True
        elif frame_num % web_frame_interval == 0 and frame_num > 0:
            frame_type = FrameType.WEB_FRAME
            is_watertight = False
        else:
            frame_type = FrameType.TRANSVERSE
            is_watertight = False

        frames.append(Frame(
            number=frame_num,
            x=round(x, 4),
            frame_type=frame_type,
            is_watertight=is_watertight,
            zone=zone,
        ))

        frame_num += 1

    return FrameSystem(
        length_bp=length_bp,
        frame_spacing=frame_spacing,
        web_frame_interval=web_frame_interval,
        frames=frames,
    )


def get_standard_bulkhead_positions(
    length_bp: float,
    num_watertight_compartments: int = 5,
) -> List[float]:
    """
    Get standard bulkhead positions for watertight subdivision.

    Args:
        length_bp: Length between perpendiculars (m)
        num_watertight_compartments: Number of watertight compartments

    Returns:
        List of bulkhead x positions (m from AP)
    """
    if num_watertight_compartments < 2:
        return []

    # Evenly space bulkheads (excluding AP and FP ends)
    positions = []
    for i in range(1, num_watertight_compartments):
        x = (i / num_watertight_compartments) * length_bp
        positions.append(round(x, 2))

    return positions
