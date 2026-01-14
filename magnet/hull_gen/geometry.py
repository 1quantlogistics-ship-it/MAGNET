"""
hull_gen/geometry.py - Hull geometry data structures.

BRAVO OWNS THIS FILE.

Module 17 v1.1 - Hull geometry representation with edge type support.

v1.1 Changes:
- Added EdgeType enum for hard edge rendering support
- Extended SectionPoint with edge_type and feature_id fields
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
import math

if TYPE_CHECKING:
    from magnet.hull_gen.deck_generator import DeckGeometry


class EdgeType(Enum):
    """
    Edge rendering type for mesh generation.
    
    Controls how normals are computed at vertices:
    - SMOOTH: Averaged normals across adjacent faces (default behavior)
    - HARD: Split normals, each face gets its own normal at this vertex
    - CREASE: Hard edge only above specified angle threshold
    
    Phase 1: Foundation for hard chine rendering.
    """
    SMOOTH = "smooth"
    HARD = "hard"
    CREASE = "crease"


@dataclass
class Point3D:
    """3D point in hull coordinate system."""

    x: float = 0.0
    """Longitudinal position (m from AP, positive forward)."""

    y: float = 0.0
    """Transverse position (m from centerline, positive port). See docs/architecture/GEOMETRY_CONVENTIONS.md."""

    z: float = 0.0
    """Vertical position (m from baseline, positive up)."""

    def __add__(self, other: 'Point3D') -> 'Point3D':
        return Point3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Point3D') -> 'Point3D':
        return Point3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> 'Point3D':
        return Point3D(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> 'Point3D':
        return self.__mul__(scalar)

    def distance_to(self, other: 'Point3D') -> float:
        """Euclidean distance to another point."""
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def length(self) -> float:
        """Distance from origin."""
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalize(self) -> 'Point3D':
        """Return unit vector."""
        length = self.length()
        if length == 0:
            return Point3D()
        return Point3D(self.x / length, self.y / length, self.z / length)

    def dot(self, other: 'Point3D') -> float:
        """Dot product."""
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: 'Point3D') -> 'Point3D':
        """Cross product."""
        return Point3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def to_tuple(self) -> Tuple[float, float, float]:
        """Convert to tuple."""
        return (self.x, self.y, self.z)

    def to_dict(self) -> Dict[str, float]:
        return {"x": round(self.x, 6), "y": round(self.y, 6), "z": round(self.z, 6)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Point3D':
        return cls(
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            z=data.get("z", 0.0),
        )


@dataclass
class SectionPoint:
    """
    Point on a hull section curve.

    Includes curvature, normal, and edge type information.
    
    v1.1: Added edge_type for hard edge rendering support.
    """

    position: Point3D = field(default_factory=Point3D)
    """3D position of point."""

    normal: Optional[Point3D] = None
    """Outward normal vector."""

    curvature: float = 0.0
    """Local curvature (1/radius)."""

    is_chine: bool = False
    """Whether this point is on a chine."""

    is_keel: bool = False
    """Whether this point is at keel centerline."""

    # === v1.1: Edge rendering control ===
    edge_type: EdgeType = field(default=EdgeType.SMOOTH)
    """Edge rendering type (SMOOTH, HARD, CREASE)."""

    crease_angle_deg: float = 0.0
    """Crease angle threshold in degrees (only used if edge_type == CREASE)."""

    feature_id: Optional[str] = None
    """Feature identification for debugging/visualization (e.g., 'chine_main', 'spray_rail_1')."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position": self.position.to_dict(),
            "normal": self.normal.to_dict() if self.normal else None,
            "curvature": round(self.curvature, 6),
            "is_chine": self.is_chine,
            "is_keel": self.is_keel,
            "edge_type": self.edge_type.value,
            "feature_id": self.feature_id,
        }


@dataclass
class HullSection:
    """
    Transverse section of hull.

    Represents a cross-section at a specific longitudinal position.
    """

    station: float = 0.0
    """Station position (fraction of LWL from AP, 0 = AP, 1 = FP)."""

    x_position: float = 0.0
    """Longitudinal position (m from AP)."""

    points: List[SectionPoint] = field(default_factory=list)
    """Section points from keel to deck (port side, mirrored for starboard)."""

    # === SECTION PROPERTIES ===
    area: float = 0.0
    """Section area below waterline (m^2)."""

    half_beam: float = 0.0
    """Half-beam at waterline (m)."""

    draft_local: float = 0.0
    """Local draft at this section (m)."""

    deadrise_deg: float = 0.0
    """Deadrise angle at this section (degrees)."""

    # === KEY POINTS ===
    keel_point: Optional[Point3D] = None
    chine_point: Optional[Point3D] = None
    waterline_point: Optional[Point3D] = None
    deck_edge_point: Optional[Point3D] = None

    def get_point_at_z(self, z: float) -> Optional[Point3D]:
        """
        Get section point at specified vertical position.

        Args:
            z: Vertical position (m from baseline)

        Returns:
            Interpolated point on section, or None if outside range
        """
        if not self.points:
            return None

        # Find bracketing points
        for i in range(len(self.points) - 1):
            z1 = self.points[i].position.z
            z2 = self.points[i + 1].position.z

            if z1 <= z <= z2:
                # Linear interpolation
                t = (z - z1) / (z2 - z1) if z2 != z1 else 0
                p1 = self.points[i].position
                p2 = self.points[i + 1].position
                return Point3D(
                    x=p1.x + t * (p2.x - p1.x),
                    y=p1.y + t * (p2.y - p1.y),
                    z=z,
                )

        return None

    def compute_area(self, waterline_z: float = 0.0) -> float:
        """
        Compute section area below waterline using trapezoidal rule.

        Args:
            waterline_z: Waterline height (m from baseline)
        """
        if len(self.points) < 2:
            return 0.0

        area = 0.0
        for i in range(len(self.points) - 1):
            p1 = self.points[i].position
            p2 = self.points[i + 1].position

            # Only count area below waterline
            z1 = min(p1.z, waterline_z)
            z2 = min(p2.z, waterline_z)

            if z1 > waterline_z and z2 > waterline_z:
                continue

            # Trapezoidal contribution (half section, mirrored)
            area += 0.5 * abs(p1.y + p2.y) * abs(z2 - z1)

        self.area = area * 2  # Mirror for full section
        return self.area

    def to_dict(self) -> Dict[str, Any]:
        return {
            "station": round(self.station, 4),
            "x_position": round(self.x_position, 4),
            "points": [p.to_dict() for p in self.points],
            "area": round(self.area, 4),
            "half_beam": round(self.half_beam, 4),
            "draft_local": round(self.draft_local, 4),
            "deadrise_deg": round(self.deadrise_deg, 2),
        }


@dataclass
class Waterline:
    """
    Horizontal waterline cut through hull.
    """

    z_position: float = 0.0
    """Vertical position (m from baseline)."""

    points: List[Point3D] = field(default_factory=list)
    """Waterline points from bow to stern (port side)."""

    area: float = 0.0
    """Waterplane area (m^2)."""

    length: float = 0.0
    """Waterline length (m)."""

    max_beam: float = 0.0
    """Maximum beam at this waterline (m)."""

    lcf: float = 0.0
    """Longitudinal center of flotation (m from AP)."""

    def compute_properties(self) -> None:
        """Compute waterline properties."""
        if len(self.points) < 2:
            return

        # Length
        self.length = abs(self.points[-1].x - self.points[0].x)

        # Max beam (half-beam * 2)
        self.max_beam = max(abs(p.y) for p in self.points) * 2

        # Area using trapezoidal rule
        area = 0.0
        moment_x = 0.0
        for i in range(len(self.points) - 1):
            p1 = self.points[i]
            p2 = self.points[i + 1]
            dx = p2.x - p1.x
            avg_y = (abs(p1.y) + abs(p2.y)) / 2
            strip_area = dx * avg_y * 2  # Full beam
            area += strip_area
            moment_x += strip_area * (p1.x + p2.x) / 2

        self.area = abs(area)
        self.lcf = moment_x / area if area != 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "z_position": round(self.z_position, 4),
            "points": [p.to_dict() for p in self.points],
            "area": round(self.area, 4),
            "length": round(self.length, 4),
            "max_beam": round(self.max_beam, 4),
            "lcf": round(self.lcf, 4),
        }


@dataclass
class Buttock:
    """
    Longitudinal section parallel to centerplane.
    """

    y_position: float = 0.0
    """Transverse offset from centerline (m)."""

    points: List[Point3D] = field(default_factory=list)
    """Buttock points from bow to stern."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "y_position": round(self.y_position, 4),
            "points": [p.to_dict() for p in self.points],
        }


@dataclass
class LongitudinalFeature:
    """
    A longitudinal feature line (spray rail, knuckle, etc.).
    
    Phase 4: Tracks feature lines for mesh edge rendering.
    """
    feature_type: str = ""
    """Feature type: 'spray_rail', 'knuckle', etc."""
    
    feature_id: str = ""
    """Unique identifier for the feature."""
    
    points: List[Point3D] = field(default_factory=list)
    """Points along the feature from stern to bow."""
    
    is_hard: bool = True
    """Whether this is a hard edge requiring split normals."""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_type": self.feature_type,
            "feature_id": self.feature_id,
            "points": [p.to_dict() for p in self.points],
            "is_hard": self.is_hard,
        }


@dataclass
class HullGeometry:
    """
    Complete hull geometry representation.
    """

    hull_id: str = ""

    # === SECTIONS ===
    sections: List[HullSection] = field(default_factory=list)
    """Transverse sections from AP to FP."""

    # === WATERLINES ===
    waterlines: List[Waterline] = field(default_factory=list)
    """Horizontal waterline cuts."""

    # === BUTTOCKS ===
    buttocks: List[Buttock] = field(default_factory=list)
    """Longitudinal sections."""

    # === KEY CURVES ===
    stem_profile: List[Point3D] = field(default_factory=list)
    """Stem curve from keel to deck."""

    keel_profile: List[Point3D] = field(default_factory=list)
    """Keel curve from AP to FP."""

    chine_curve: List[Point3D] = field(default_factory=list)
    """Chine curve from transom to bow."""

    deck_edge: List[Point3D] = field(default_factory=list)
    """Deck edge curve."""

    transom_outline: List[Point3D] = field(default_factory=list)
    """Transom perimeter curve."""
    
    # === Phase 3: Bow panel edges ===
    bow_panel_edges: List[Any] = field(default_factory=list)
    """Hard edges from bow panels (BowPanelEdge objects)."""
    
    # === Phase 4: Longitudinal features ===
    longitudinal_features: List['LongitudinalFeature'] = field(default_factory=list)
    """Longitudinal features (spray rails, knuckle lines)."""
    
    # === Phase 5: Transom features ===
    transom_hard_edges: List[Tuple[int, int, str]] = field(default_factory=list)
    """Hard edges on transom: (start_idx, end_idx, feature_id)."""
    
    # === Phase 6: Deck geometry ===
    deck_geometry: Optional['DeckGeometry'] = None
    """Generated deck surface (if enabled)."""

    # === COMPUTED PROPERTIES ===
    volume: float = 0.0
    """Displaced volume (m^3)."""

    wetted_surface: float = 0.0
    """Wetted surface area (m^2)."""

    waterplane_area: float = 0.0
    """Waterplane area at design draft (m^2)."""

    lcb: float = 0.0
    """Longitudinal center of buoyancy (m from AP)."""

    vcb: float = 0.0
    """Vertical center of buoyancy (m from baseline)."""

    def get_section_at_x(self, x: float) -> Optional[HullSection]:
        """
        Get section at longitudinal position by interpolation.
        """
        if not self.sections:
            return None

        # Find bracketing sections
        for i in range(len(self.sections) - 1):
            x1 = self.sections[i].x_position
            x2 = self.sections[i + 1].x_position

            if x1 <= x <= x2:
                # Return closest section (simplified, could interpolate)
                t = (x - x1) / (x2 - x1) if x2 != x1 else 0
                return self.sections[i] if t < 0.5 else self.sections[i + 1]

        return None

    def compute_volume(self) -> float:
        """
        Compute displaced volume using Simpson's rule.
        """
        if len(self.sections) < 3:
            return 0.0

        volume = 0.0
        n = len(self.sections)

        for i in range(n - 1):
            s1 = self.sections[i]
            s2 = self.sections[i + 1]
            dx = s2.x_position - s1.x_position

            # Trapezoidal integration
            volume += 0.5 * (s1.area + s2.area) * dx

        self.volume = volume
        return volume

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hull_id": self.hull_id,
            "sections": [s.to_dict() for s in self.sections],
            "waterlines": [w.to_dict() for w in self.waterlines],
            "buttocks": [b.to_dict() for b in self.buttocks],
            "volume": round(self.volume, 4),
            "wetted_surface": round(self.wetted_surface, 4),
            "waterplane_area": round(self.waterplane_area, 4),
            "lcb": round(self.lcb, 4),
            "vcb": round(self.vcb, 4),
        }
