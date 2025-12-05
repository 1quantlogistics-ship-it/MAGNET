"""
Coordinate system and station definitions for naval vessel geometry.

Implements standard naval architecture coordinate conventions:
- X-axis: Longitudinal (positive forward from AP)
- Y-axis: Transverse (positive to port)
- Z-axis: Vertical (positive upward from baseline)

Stations are evenly spaced longitudinal reference lines used for
hull form definition and structural layout.

References:
- Ship Design and Construction (Taggart)
- ABS HSNC 2023 notation conventions
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class ReferencePoint(Enum):
    """Standard reference points on vessel."""
    AP = "after_perpendicular"      # Aft end of LWL or rudder stock
    FP = "forward_perpendicular"    # Forward end of LWL
    MIDSHIP = "midship"             # Half LBP from AP
    LCF = "center_of_flotation"     # Longitudinal center of flotation
    LCB = "center_of_buoyancy"      # Longitudinal center of buoyancy


@dataclass
class CoordinateSystem:
    """
    Vessel coordinate system definition.

    Standard naval architecture convention:
    - Origin at intersection of AP, centerline, and baseline
    - X positive forward (toward bow)
    - Y positive to port (starboard is negative)
    - Z positive upward

    Attributes:
        length_bp: Length between perpendiculars (m)
        beam: Beam at waterline (m)
        depth: Depth to main deck (m)
        draft: Design draft (m)
        origin_x: X of origin relative to AP (typically 0)
        origin_z: Z of origin relative to baseline (typically 0)
    """
    length_bp: float      # m
    beam: float           # m
    depth: float          # m
    draft: float          # m
    origin_x: float = 0.0  # m (AP reference)
    origin_z: float = 0.0  # m (baseline reference)

    @property
    def x_fp(self) -> float:
        """X coordinate of forward perpendicular."""
        return self.length_bp + self.origin_x

    @property
    def x_ap(self) -> float:
        """X coordinate of after perpendicular."""
        return self.origin_x

    @property
    def x_midship(self) -> float:
        """X coordinate of midship."""
        return self.length_bp / 2 + self.origin_x

    @property
    def y_centerline(self) -> float:
        """Y coordinate of centerline."""
        return 0.0

    @property
    def y_port(self) -> float:
        """Y coordinate of port side (half beam)."""
        return self.beam / 2

    @property
    def y_starboard(self) -> float:
        """Y coordinate of starboard side (negative half beam)."""
        return -self.beam / 2

    @property
    def z_baseline(self) -> float:
        """Z coordinate of baseline."""
        return self.origin_z

    @property
    def z_waterline(self) -> float:
        """Z coordinate of design waterline."""
        return self.draft + self.origin_z

    @property
    def z_deck(self) -> float:
        """Z coordinate of main deck."""
        return self.depth + self.origin_z

    def normalize_x(self, x: float) -> float:
        """Convert x to fraction of LBP (0 = AP, 1 = FP)."""
        return (x - self.origin_x) / self.length_bp

    def denormalize_x(self, x_norm: float) -> float:
        """Convert normalized x (0-1) to actual x coordinate."""
        return x_norm * self.length_bp + self.origin_x

    def is_forward(self, x: float) -> bool:
        """Check if position is in forward third of vessel."""
        return self.normalize_x(x) > 0.67

    def is_midship(self, x: float) -> bool:
        """Check if position is in middle third of vessel."""
        x_norm = self.normalize_x(x)
        return 0.33 <= x_norm <= 0.67

    def is_aft(self, x: float) -> bool:
        """Check if position is in aft third of vessel."""
        return self.normalize_x(x) < 0.33


@dataclass
class Station:
    """
    Transverse station (reference line) on vessel.

    Stations are numbered from AP (station 0) to FP (station N).
    Standard practice uses 10 or 20 stations for hull definition.

    Attributes:
        number: Station number (0 = AP)
        x: X coordinate of station (m from origin)
        x_normalized: Fraction of LBP (0 = AP, 1 = FP)
        name: Optional station name (e.g., "midship", "AP")
    """
    number: int
    x: float
    x_normalized: float
    name: Optional[str] = None

    def __repr__(self) -> str:
        name_str = f" ({self.name})" if self.name else ""
        return f"Station {self.number}{name_str}: x={self.x:.2f}m ({self.x_normalized:.1%} LBP)"


def get_stations(
    length_bp: float,
    num_stations: int = 10,
    include_half_stations: bool = False,
) -> List[Station]:
    """
    Generate evenly spaced stations along vessel length.

    Args:
        length_bp: Length between perpendiculars (m)
        num_stations: Number of station intervals (10 or 20 typical)
        include_half_stations: Include half-stations between main stations

    Returns:
        List of Station objects from AP (0) to FP (num_stations)
    """
    stations = []
    divisor = num_stations * 2 if include_half_stations else num_stations

    for i in range(divisor + 1):
        if include_half_stations:
            station_num = i / 2
            x_norm = i / divisor
        else:
            station_num = i
            x_norm = i / num_stations

        x = x_norm * length_bp

        # Name special stations
        name = None
        if station_num == 0:
            name = "AP"
        elif station_num == num_stations:
            name = "FP"
        elif station_num == num_stations / 2:
            name = "midship"

        stations.append(Station(
            number=int(station_num) if station_num == int(station_num) else station_num,
            x=x,
            x_normalized=x_norm,
            name=name,
        ))

    return stations


def get_station_at_x(
    x: float,
    length_bp: float,
    num_stations: int = 10,
) -> Station:
    """
    Get or interpolate station at a specific x position.

    Args:
        x: X coordinate (m from AP)
        length_bp: Length between perpendiculars (m)
        num_stations: Number of station intervals

    Returns:
        Station at or near the specified x position
    """
    x_norm = x / length_bp if length_bp > 0 else 0.0
    x_norm = max(0.0, min(1.0, x_norm))  # Clamp to valid range

    # Calculate station number (may be fractional)
    station_num = x_norm * num_stations

    # Name if at special location
    name = None
    if abs(station_num) < 0.01:
        name = "AP"
    elif abs(station_num - num_stations) < 0.01:
        name = "FP"
    elif abs(station_num - num_stations / 2) < 0.01:
        name = "midship"

    return Station(
        number=round(station_num, 1),
        x=x,
        x_normalized=x_norm,
        name=name,
    )


def get_reference_point_x(
    ref_point: ReferencePoint,
    length_bp: float,
    lcb_from_midship: float = 0.0,
    lcf_from_midship: float = 0.0,
) -> float:
    """
    Get x coordinate of a reference point.

    Args:
        ref_point: Reference point type
        length_bp: Length between perpendiculars (m)
        lcb_from_midship: LCB distance from midship (+ forward) (m)
        lcf_from_midship: LCF distance from midship (+ forward) (m)

    Returns:
        X coordinate of reference point (m from AP)
    """
    if ref_point == ReferencePoint.AP:
        return 0.0
    elif ref_point == ReferencePoint.FP:
        return length_bp
    elif ref_point == ReferencePoint.MIDSHIP:
        return length_bp / 2
    elif ref_point == ReferencePoint.LCB:
        return length_bp / 2 + lcb_from_midship
    elif ref_point == ReferencePoint.LCF:
        return length_bp / 2 + lcf_from_midship
    else:
        return length_bp / 2  # Default to midship
