"""
magnet/routing/schema/trunk_segment.py - Trunk Segment Schema

Trunks represent the macro-level routing between nodes,
passing through one or more compartments/spaces.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import uuid
import math

from .system_type import SystemType

__all__ = ['TrunkSegment', 'TrunkSize', 'generate_trunk_id']


def generate_trunk_id() -> str:
    """Generate unique trunk ID."""
    return f"trunk_{uuid.uuid4().hex[:12]}"


@dataclass
class TrunkSize:
    """
    Physical sizing for a trunk segment.

    Different system types use different sizing attributes:
    - Fluid systems: diameter_mm
    - Electrical systems: cable_rating_a, cable_size_mm2
    - HVAC systems: duct_width_mm, duct_height_mm
    """

    # For fluid systems (pipes)
    diameter_mm: float = 0.0

    # For electrical systems (cables)
    cable_rating_a: float = 0.0
    cable_size_mm2: float = 0.0

    # For HVAC systems (ducts)
    duct_width_mm: float = 0.0
    duct_height_mm: float = 0.0

    # Standard designation (e.g., "DN50", "4/0 AWG", "300x200")
    nominal_size: str = ""

    @property
    def is_sized(self) -> bool:
        """Check if trunk has been sized."""
        return (
            self.diameter_mm > 0 or
            self.cable_rating_a > 0 or
            self.duct_width_mm > 0
        )

    @property
    def cross_section_area_mm2(self) -> float:
        """Calculate cross-sectional area in mm²."""
        if self.diameter_mm > 0:
            # Circular pipe
            return math.pi * (self.diameter_mm / 2) ** 2
        elif self.duct_width_mm > 0 and self.duct_height_mm > 0:
            # Rectangular duct
            return self.duct_width_mm * self.duct_height_mm
        elif self.cable_size_mm2 > 0:
            return self.cable_size_mm2
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'diameter_mm': self.diameter_mm,
            'cable_rating_a': self.cable_rating_a,
            'cable_size_mm2': self.cable_size_mm2,
            'duct_width_mm': self.duct_width_mm,
            'duct_height_mm': self.duct_height_mm,
            'nominal_size': self.nominal_size,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrunkSize':
        """Deserialize from dictionary."""
        return cls(**data)

    def __repr__(self) -> str:
        if self.nominal_size:
            return f"TrunkSize({self.nominal_size})"
        elif self.diameter_mm > 0:
            return f"TrunkSize(D{self.diameter_mm}mm)"
        elif self.cable_rating_a > 0:
            return f"TrunkSize({self.cable_rating_a}A)"
        elif self.duct_width_mm > 0:
            return f"TrunkSize({self.duct_width_mm}x{self.duct_height_mm}mm)"
        return "TrunkSize(unsized)"


@dataclass
class TrunkSegment:
    """
    Trunk-level routing segment between two nodes.

    Represents the macro routing of a system passing through
    one or more compartments/spaces.

    Attributes:
        trunk_id: Unique identifier
        system_type: Which system this trunk belongs to

        from_node_id: Starting node ID
        to_node_id: Ending node ID

        path_spaces: Ordered list of space IDs the trunk passes through
        path_points: Optional detailed 3D path points

        size: Physical sizing (diameter, rating, etc.)
        capacity: Capacity in system-specific units

        length_m: Total trunk length in meters

        zone_crossings: List of zone IDs crossed
        is_zone_compliant: Whether all crossings are valid
        zone_violation_reason: Reason if not compliant

        is_redundant_path: Whether this is a backup/redundant path
        parallel_trunk_id: ID of parallel redundant trunk

        is_routed: Whether routing has been calculated
        routing_notes: Notes from routing algorithm
    """

    # Identity
    trunk_id: str
    system_type: SystemType

    # Endpoints (node references)
    from_node_id: str
    to_node_id: str

    # Path through spaces
    path_spaces: List[str] = field(default_factory=list)
    path_points: List[Tuple[float, float, float]] = field(default_factory=list)

    # Sizing
    size: TrunkSize = field(default_factory=TrunkSize)
    capacity: float = 0.0

    # Physical measurements
    length_m: float = 0.0

    # Zone compliance
    zone_crossings: List[str] = field(default_factory=list)
    is_zone_compliant: bool = True
    zone_violation_reason: str = ""

    # Redundancy
    is_redundant_path: bool = False
    parallel_trunk_id: Optional[str] = None

    # Routing status
    is_routed: bool = False
    routing_notes: str = ""

    # Timestamps
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize timestamps."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        self.modified_at = datetime.utcnow()

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def is_valid(self) -> bool:
        """Check if trunk is valid for use."""
        return (
            self.is_routed and
            self.is_zone_compliant and
            len(self.path_spaces) > 0
        )

    @property
    def space_count(self) -> int:
        """Number of spaces this trunk passes through."""
        return len(self.path_spaces)

    @property
    def crossing_count(self) -> int:
        """Number of zone crossings."""
        return len(self.zone_crossings)

    @property
    def has_path(self) -> bool:
        """Check if trunk has a calculated path."""
        return len(self.path_spaces) > 0

    @property
    def has_redundant_pair(self) -> bool:
        """Check if trunk has a redundant parallel."""
        return self.parallel_trunk_id is not None

    # =========================================================================
    # Path Management
    # =========================================================================

    def set_path(
        self,
        spaces: List[str],
        points: Optional[List[Tuple[float, float, float]]] = None,
    ) -> None:
        """
        Set the trunk path through spaces.

        Args:
            spaces: Ordered list of space IDs
            points: Optional detailed 3D path points
        """
        self.path_spaces = list(spaces)
        if points:
            self.path_points = list(points)
        self.is_routed = len(spaces) > 0
        self.modified_at = datetime.utcnow()

    def clear_path(self) -> None:
        """Clear the trunk path."""
        self.path_spaces.clear()
        self.path_points.clear()
        self.is_routed = False
        self.length_m = 0.0
        self.modified_at = datetime.utcnow()

    def passes_through(self, space_id: str) -> bool:
        """Check if trunk passes through a space."""
        return space_id in self.path_spaces

    def get_space_sequence(self) -> List[Tuple[str, str]]:
        """
        Get sequence of space-to-space transitions.

        Returns:
            List of (from_space, to_space) tuples
        """
        if len(self.path_spaces) < 2:
            return []
        return [
            (self.path_spaces[i], self.path_spaces[i + 1])
            for i in range(len(self.path_spaces) - 1)
        ]

    # =========================================================================
    # Zone Management
    # =========================================================================

    def add_zone_crossing(self, zone_id: str) -> None:
        """Record a zone crossing."""
        if zone_id not in self.zone_crossings:
            self.zone_crossings.append(zone_id)
            self.modified_at = datetime.utcnow()

    def clear_zone_crossings(self) -> None:
        """Clear all zone crossings."""
        self.zone_crossings.clear()
        self.modified_at = datetime.utcnow()

    def mark_zone_violation(self, reason: str) -> None:
        """Mark trunk as having zone violation."""
        self.is_zone_compliant = False
        self.zone_violation_reason = reason
        self.modified_at = datetime.utcnow()

    def clear_zone_violation(self) -> None:
        """Clear zone violation."""
        self.is_zone_compliant = True
        self.zone_violation_reason = ""
        self.modified_at = datetime.utcnow()

    # =========================================================================
    # Length Calculation
    # =========================================================================

    def calculate_length(
        self,
        space_centers: Dict[str, Tuple[float, float, float]],
    ) -> float:
        """
        Calculate trunk length from path.

        Uses detailed path points if available, otherwise
        calculates Euclidean distance between space centers.

        Args:
            space_centers: Mapping of space_id to center (x, y, z)

        Returns:
            Total length in meters
        """
        if self.path_points and len(self.path_points) >= 2:
            # Use detailed path points
            length = 0.0
            for i in range(len(self.path_points) - 1):
                p1, p2 = self.path_points[i], self.path_points[i + 1]
                length += math.sqrt(
                    (p2[0] - p1[0])**2 +
                    (p2[1] - p1[1])**2 +
                    (p2[2] - p1[2])**2
                )
            self.length_m = length

        elif self.path_spaces and len(self.path_spaces) >= 2:
            # Use space centers
            length = 0.0
            for i in range(len(self.path_spaces) - 1):
                s1, s2 = self.path_spaces[i], self.path_spaces[i + 1]
                if s1 in space_centers and s2 in space_centers:
                    c1 = space_centers[s1]
                    c2 = space_centers[s2]
                    length += math.sqrt(
                        (c2[0] - c1[0])**2 +
                        (c2[1] - c1[1])**2 +
                        (c2[2] - c1[2])**2
                    )
            self.length_m = length

        self.modified_at = datetime.utcnow()
        return self.length_m

    # =========================================================================
    # Validation
    # =========================================================================

    def validate(self) -> List[str]:
        """
        Validate trunk configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self.trunk_id:
            errors.append("trunk_id is required")

        if not self.from_node_id:
            errors.append("from_node_id is required")

        if not self.to_node_id:
            errors.append("to_node_id is required")

        if self.from_node_id == self.to_node_id:
            errors.append("from_node_id and to_node_id must be different")

        if self.is_routed and len(self.path_spaces) == 0:
            errors.append("routed trunk must have path_spaces")

        if not self.is_zone_compliant and not self.zone_violation_reason:
            errors.append("zone violation must have reason")

        return errors

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'trunk_id': self.trunk_id,
            'system_type': self.system_type.value,
            'from_node_id': self.from_node_id,
            'to_node_id': self.to_node_id,
            'path_spaces': list(self.path_spaces),
            'path_points': [list(p) for p in self.path_points],
            'size': self.size.to_dict(),
            'capacity': self.capacity,
            'length_m': self.length_m,
            'zone_crossings': list(self.zone_crossings),
            'is_zone_compliant': self.is_zone_compliant,
            'zone_violation_reason': self.zone_violation_reason,
            'is_redundant_path': self.is_redundant_path,
            'parallel_trunk_id': self.parallel_trunk_id,
            'is_routed': self.is_routed,
            'routing_notes': self.routing_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'modified_at': self.modified_at.isoformat() if self.modified_at else None,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrunkSegment':
        """Deserialize from dictionary."""
        data = data.copy()

        # Convert enum
        data['system_type'] = SystemType(data['system_type'])

        # Convert nested objects
        data['size'] = TrunkSize.from_dict(data['size'])
        data['path_points'] = [tuple(p) for p in data.get('path_points', [])]

        # Convert datetimes
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('modified_at'):
            data['modified_at'] = datetime.fromisoformat(data['modified_at'])

        return cls(**data)

    # =========================================================================
    # String Representation
    # =========================================================================

    def __repr__(self) -> str:
        status = "routed" if self.is_routed else "unrouted"
        return (
            f"TrunkSegment(id={self.trunk_id!r}, "
            f"system={self.system_type.value}, "
            f"{self.from_node_id} -> {self.to_node_id}, "
            f"spaces={self.space_count}, {status})"
        )

    def __str__(self) -> str:
        size_str = str(self.size) if self.size.is_sized else "unsized"
        return (
            f"Trunk [{self.system_type.value}] "
            f"{self.from_node_id} -> {self.to_node_id} "
            f"({self.space_count} spaces, {self.length_m:.1f}m, {size_str})"
        )


# =========================================================================
# Factory Function
# =========================================================================

def create_trunk(
    system_type: SystemType,
    from_node_id: str,
    to_node_id: str,
    path_spaces: Optional[List[str]] = None,
) -> TrunkSegment:
    """
    Create a trunk segment.

    Args:
        system_type: Type of system
        from_node_id: Starting node ID
        to_node_id: Ending node ID
        path_spaces: Optional initial path

    Returns:
        Configured TrunkSegment
    """
    trunk = TrunkSegment(
        trunk_id=generate_trunk_id(),
        system_type=system_type,
        from_node_id=from_node_id,
        to_node_id=to_node_id,
    )

    if path_spaces:
        trunk.set_path(path_spaces)

    return trunk
