"""
magnet/routing/contracts/routing_lineage.py - Routing Lineage Tracking

Tracks the provenance of routing results, linking them to their
source geometry, arrangement, and input hashes for staleness detection.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List
from datetime import datetime
import hashlib


__all__ = ['RoutingLineage', 'LineageStatus', 'quantize_coordinate']


class LineageStatus:
    """Status of routing lineage validation."""
    CURRENT = "current"           # All hashes match, routing is up-to-date
    STALE_GEOMETRY = "stale_geometry"      # Geometry changed since routing
    STALE_ARRANGEMENT = "stale_arrangement"  # Arrangement changed
    STALE_INPUT = "stale_input"    # Routing input contract changed
    STALE_MULTIPLE = "stale_multiple"  # Multiple sources changed
    UNKNOWN = "unknown"           # Lineage not yet computed


# =============================================================================
# Geometry Quantization
# =============================================================================

def quantize_coordinate(value: float, precision_m: float = 0.01) -> float:
    """
    Quantize a coordinate to a fixed precision.

    This prevents hash changes due to floating-point drift or
    minor coordinate adjustments that don't affect routing.

    Args:
        value: Coordinate value in meters
        precision_m: Quantization precision (default 1cm)

    Returns:
        Quantized coordinate value
    """
    if precision_m <= 0:
        return value
    return round(value / precision_m) * precision_m


def quantize_point(
    point: tuple,
    precision_m: float = 0.01,
) -> tuple:
    """
    Quantize a 3D point to fixed precision.

    Args:
        point: (x, y, z) coordinate tuple
        precision_m: Quantization precision

    Returns:
        Quantized coordinate tuple
    """
    return tuple(quantize_coordinate(v, precision_m) for v in point)


def compute_geometry_hash(
    space_centers: Dict[str, tuple],
    precision_m: float = 0.01,
) -> str:
    """
    Compute deterministic hash of geometry data.

    Quantizes coordinates before hashing to prevent hash explosion
    from minor floating-point variations.

    Args:
        space_centers: Dict of space_id -> (x, y, z) center coordinates
        precision_m: Quantization precision for coordinates

    Returns:
        SHA-256 hash of quantized geometry (first 32 chars)
    """
    hasher = hashlib.sha256()

    # Sort by space_id for determinism
    for space_id in sorted(space_centers.keys()):
        center = space_centers[space_id]
        quantized = quantize_point(center, precision_m)
        hasher.update(f"space:{space_id}:{quantized[0]:.4f},{quantized[1]:.4f},{quantized[2]:.4f}\n".encode())

    return hasher.hexdigest()[:32]


def compute_arrangement_hash(
    adjacency: Dict[str, set],
    fire_zones: Optional[Dict[str, set]] = None,
    watertight_boundaries: Optional[set] = None,
) -> str:
    """
    Compute deterministic hash of arrangement/topology data.

    Args:
        adjacency: Dict of space_id -> set of adjacent space_ids
        fire_zones: Optional dict of zone_id -> set of space_ids
        watertight_boundaries: Optional set of (space_a, space_b) tuples

    Returns:
        SHA-256 hash of arrangement (first 32 chars)
    """
    hasher = hashlib.sha256()

    # Hash adjacency in sorted order
    for space_id in sorted(adjacency.keys()):
        neighbors = ','.join(sorted(adjacency[space_id]))
        hasher.update(f"adj:{space_id}:{neighbors}\n".encode())

    # Hash fire zones
    if fire_zones:
        for zone_id in sorted(fire_zones.keys()):
            spaces = ','.join(sorted(fire_zones[zone_id]))
            hasher.update(f"zone:{zone_id}:{spaces}\n".encode())

    # Hash watertight boundaries
    if watertight_boundaries:
        for boundary in sorted(tuple(sorted(b)) for b in watertight_boundaries):
            hasher.update(f"wt:{boundary[0]}:{boundary[1]}\n".encode())

    return hasher.hexdigest()[:32]


# =============================================================================
# Routing Lineage Dataclass
# =============================================================================

@dataclass
class RoutingLineage:
    """
    Tracks provenance of routing results for staleness detection.

    Links routing output to the specific versions of geometry,
    arrangement, and input contract that produced it.

    Attributes:
        geometry_hash: Hash of space centers/coordinates at routing time
        arrangement_hash: Hash of adjacency/zones at routing time
        routing_input_hash: Hash of RoutingInputContract at routing time
        routing_output_hash: Hash of resulting RoutingLayout

        computed_at: When lineage was computed
        routing_version: Version of routing algorithm used

        source_design_id: Design this routing belongs to
        source_version: Design version at routing time

        geometry_precision_m: Precision used for geometry quantization
        status: Current lineage status
    """

    # Core hashes
    geometry_hash: Optional[str] = None
    arrangement_hash: Optional[str] = None
    routing_input_hash: Optional[str] = None
    routing_output_hash: Optional[str] = None

    # Timestamps
    computed_at: Optional[datetime] = None

    # Versioning
    routing_version: str = "3.0"

    # Source tracking
    source_design_id: str = ""
    source_version: int = 0

    # Configuration
    geometry_precision_m: float = 0.01

    # Status
    status: str = LineageStatus.UNKNOWN
    staleness_reasons: List[str] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def compute_from_inputs(
        self,
        space_centers: Dict[str, tuple],
        adjacency: Dict[str, set],
        fire_zones: Optional[Dict[str, set]] = None,
        watertight_boundaries: Optional[set] = None,
        routing_input_hash: Optional[str] = None,
    ) -> 'RoutingLineage':
        """
        Compute lineage hashes from input data.

        Args:
            space_centers: Dict of space_id -> center coordinates
            adjacency: Dict of space_id -> adjacent space_ids
            fire_zones: Optional fire zone definitions
            watertight_boundaries: Optional watertight boundary pairs
            routing_input_hash: Optional pre-computed input contract hash

        Returns:
            Self with computed hashes
        """
        self.geometry_hash = compute_geometry_hash(
            space_centers,
            self.geometry_precision_m
        )
        self.arrangement_hash = compute_arrangement_hash(
            adjacency, fire_zones, watertight_boundaries
        )

        if routing_input_hash:
            self.routing_input_hash = routing_input_hash

        self.computed_at = datetime.utcnow()
        self.status = LineageStatus.CURRENT

        return self

    def set_output_hash(self, routing_output_hash: str) -> None:
        """Set the routing output hash after routing completes."""
        self.routing_output_hash = routing_output_hash

    def check_staleness(
        self,
        current_geometry_hash: Optional[str] = None,
        current_arrangement_hash: Optional[str] = None,
        current_input_hash: Optional[str] = None,
    ) -> str:
        """
        Check if routing is stale compared to current state.

        Args:
            current_geometry_hash: Current geometry hash to compare
            current_arrangement_hash: Current arrangement hash
            current_input_hash: Current routing input hash

        Returns:
            LineageStatus indicating staleness
        """
        self.staleness_reasons.clear()

        stale_flags = []

        if current_geometry_hash and current_geometry_hash != self.geometry_hash:
            stale_flags.append(LineageStatus.STALE_GEOMETRY)
            self.staleness_reasons.append(
                f"Geometry changed: {self.geometry_hash[:8]}... -> {current_geometry_hash[:8]}..."
            )

        if current_arrangement_hash and current_arrangement_hash != self.arrangement_hash:
            stale_flags.append(LineageStatus.STALE_ARRANGEMENT)
            self.staleness_reasons.append(
                f"Arrangement changed: {self.arrangement_hash[:8]}... -> {current_arrangement_hash[:8]}..."
            )

        if current_input_hash and current_input_hash != self.routing_input_hash:
            stale_flags.append(LineageStatus.STALE_INPUT)
            self.staleness_reasons.append(
                f"Input contract changed: {self.routing_input_hash[:8] if self.routing_input_hash else 'none'}... -> {current_input_hash[:8]}..."
            )

        if len(stale_flags) > 1:
            self.status = LineageStatus.STALE_MULTIPLE
        elif stale_flags:
            self.status = stale_flags[0]
        else:
            self.status = LineageStatus.CURRENT

        return self.status

    def requires_reroute(
        self,
        current_geometry_hash: Optional[str] = None,
        current_arrangement_hash: Optional[str] = None,
        current_input_hash: Optional[str] = None,
    ) -> bool:
        """
        Check if routing needs to be recomputed.

        Args:
            current_geometry_hash: Current geometry hash
            current_arrangement_hash: Current arrangement hash
            current_input_hash: Current routing input hash

        Returns:
            True if rerouting is needed
        """
        status = self.check_staleness(
            current_geometry_hash,
            current_arrangement_hash,
            current_input_hash,
        )
        return status != LineageStatus.CURRENT

    def is_valid(self) -> bool:
        """Check if lineage has all required hashes."""
        return all([
            self.geometry_hash,
            self.arrangement_hash,
            self.computed_at,
        ])

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'geometry_hash': self.geometry_hash,
            'arrangement_hash': self.arrangement_hash,
            'routing_input_hash': self.routing_input_hash,
            'routing_output_hash': self.routing_output_hash,
            'computed_at': self.computed_at.isoformat() if self.computed_at else None,
            'routing_version': self.routing_version,
            'source_design_id': self.source_design_id,
            'source_version': self.source_version,
            'geometry_precision_m': self.geometry_precision_m,
            'status': self.status,
            'staleness_reasons': self.staleness_reasons,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RoutingLineage':
        """Deserialize from dictionary."""
        lineage = cls(
            geometry_hash=data.get('geometry_hash'),
            arrangement_hash=data.get('arrangement_hash'),
            routing_input_hash=data.get('routing_input_hash'),
            routing_output_hash=data.get('routing_output_hash'),
            routing_version=data.get('routing_version', '3.0'),
            source_design_id=data.get('source_design_id', ''),
            source_version=data.get('source_version', 0),
            geometry_precision_m=data.get('geometry_precision_m', 0.01),
            status=data.get('status', LineageStatus.UNKNOWN),
            staleness_reasons=data.get('staleness_reasons', []),
            metadata=data.get('metadata', {}),
        )

        if data.get('computed_at'):
            lineage.computed_at = datetime.fromisoformat(data['computed_at'])

        return lineage

    def __repr__(self) -> str:
        return (
            f"RoutingLineage(status={self.status}, "
            f"geometry={self.geometry_hash[:8] if self.geometry_hash else 'none'}..., "
            f"arrangement={self.arrangement_hash[:8] if self.arrangement_hash else 'none'}...)"
        )
