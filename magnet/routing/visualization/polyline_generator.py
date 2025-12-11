"""
magnet/routing/visualization/polyline_generator.py - Polyline Generator

Generates 3D polylines for trunk visualization in UI,
including crossing metadata for zone boundary markers.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any
from enum import Enum
import math

from ..schema.system_type import SystemType
from ..schema.trunk_segment import TrunkSegment
from ..schema.system_topology import SystemTopology
from ..schema.routing_layout import RoutingLayout

__all__ = [
    'PolylineGenerator',
    'TrunkPolyline',
    'CrossingMarker',
    'CrossingType',
    'VisualizationData',
]


class CrossingType(Enum):
    """Type of boundary crossing for visualization."""
    FIRE_ZONE = "fire_zone"
    WATERTIGHT = "watertight"
    DECK = "deck"
    ZONE = "zone"
    DOOR = "door"
    PENETRATION = "penetration"


@dataclass
class CrossingMarker:
    """
    Marker for a boundary crossing along a trunk path.

    Used by UI to render crossing indicators (dampers, penetrations, etc.)
    """
    position: Tuple[float, float, float]  # 3D position of crossing
    crossing_type: CrossingType
    from_space: str
    to_space: str
    zone_id: Optional[str] = None
    requires_damper: bool = False
    requires_seal: bool = False
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'position': list(self.position),
            'crossing_type': self.crossing_type.value,
            'from_space': self.from_space,
            'to_space': self.to_space,
            'zone_id': self.zone_id,
            'requires_damper': self.requires_damper,
            'requires_seal': self.requires_seal,
            'notes': self.notes,
        }


@dataclass
class TrunkPolyline:
    """
    Polyline representation of a trunk for UI rendering.

    Contains:
    - 3D points defining the trunk path
    - Crossing markers for boundary visualizations
    - Styling information
    """
    trunk_id: str
    system_type: SystemType
    from_node_id: str
    to_node_id: str

    # Path geometry
    points: List[Tuple[float, float, float]] = field(default_factory=list)

    # Crossing metadata
    crossings: List[CrossingMarker] = field(default_factory=list)

    # Styling
    color: Tuple[int, int, int] = (128, 128, 128)  # RGB
    line_width: float = 2.0
    dash_pattern: Optional[List[float]] = None  # For redundant paths
    opacity: float = 1.0

    # Sizing info
    diameter_mm: float = 0.0
    nominal_size: str = ""

    # Status
    is_zone_compliant: bool = True
    is_redundant: bool = False

    @property
    def length_m(self) -> float:
        """Calculate polyline length."""
        if len(self.points) < 2:
            return 0.0

        total = 0.0
        for i in range(len(self.points) - 1):
            p1, p2 = self.points[i], self.points[i + 1]
            total += math.sqrt(
                (p2[0] - p1[0])**2 +
                (p2[1] - p1[1])**2 +
                (p2[2] - p1[2])**2
            )
        return total

    @property
    def bounding_box(self) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """Get bounding box of polyline."""
        if not self.points:
            return ((0, 0, 0), (0, 0, 0))

        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        zs = [p[2] for p in self.points]

        return (
            (min(xs), min(ys), min(zs)),
            (max(xs), max(ys), max(zs)),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'trunk_id': self.trunk_id,
            'system_type': self.system_type.value,
            'from_node_id': self.from_node_id,
            'to_node_id': self.to_node_id,
            'points': [list(p) for p in self.points],
            'crossings': [c.to_dict() for c in self.crossings],
            'color': list(self.color),
            'line_width': self.line_width,
            'dash_pattern': self.dash_pattern,
            'opacity': self.opacity,
            'diameter_mm': self.diameter_mm,
            'nominal_size': self.nominal_size,
            'is_zone_compliant': self.is_zone_compliant,
            'is_redundant': self.is_redundant,
            'length_m': self.length_m,
        }


@dataclass
class VisualizationData:
    """
    Complete visualization data for a routing layout.

    Contains polylines for all trunks plus global metadata.
    """
    design_id: str
    polylines: List[TrunkPolyline] = field(default_factory=list)
    node_positions: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)

    # Aggregates
    total_length_m: float = 0.0
    total_crossings: int = 0
    systems: List[str] = field(default_factory=list)

    # Bounding box for all content
    bounding_box: Tuple[Tuple[float, float, float], Tuple[float, float, float]] = (
        (0, 0, 0), (0, 0, 0)
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'design_id': self.design_id,
            'polylines': [p.to_dict() for p in self.polylines],
            'node_positions': {k: list(v) for k, v in self.node_positions.items()},
            'total_length_m': self.total_length_m,
            'total_crossings': self.total_crossings,
            'systems': self.systems,
            'bounding_box': [list(self.bounding_box[0]), list(self.bounding_box[1])],
            'polyline_count': len(self.polylines),
        }


# System type to color mapping
SYSTEM_COLORS: Dict[SystemType, Tuple[int, int, int]] = {
    SystemType.FUEL: (139, 69, 19),           # Saddle brown
    SystemType.FRESHWATER: (0, 191, 255),     # Deep sky blue
    SystemType.SEAWATER: (0, 139, 139),       # Dark cyan
    SystemType.GREY_WATER: (192, 192, 192),   # Silver
    SystemType.BLACK_WATER: (139, 90, 43),    # Dark brown
    SystemType.LUBE_OIL: (218, 165, 32),      # Goldenrod
    SystemType.HYDRAULIC: (255, 215, 0),      # Gold
    SystemType.HVAC_SUPPLY: (144, 238, 144),  # Light green
    SystemType.HVAC_RETURN: (60, 179, 113),   # Medium sea green
    SystemType.HVAC_EXHAUST: (105, 105, 105), # Dim gray
    SystemType.ELECTRICAL_HV: (255, 0, 0),    # Red
    SystemType.ELECTRICAL_LV: (255, 165, 0),  # Orange
    SystemType.ELECTRICAL_DC: (255, 255, 0),  # Yellow
    SystemType.FIREFIGHTING: (255, 0, 0),     # Red
    SystemType.FIRE_DETECTION: (255, 69, 0),  # Orange red
    SystemType.BILGE: (128, 128, 128),        # Gray
    SystemType.COMPRESSED_AIR: (173, 216, 230),  # Light blue
    SystemType.STEAM: (255, 255, 255),        # White
}


class PolylineGenerator:
    """
    Generates polylines from routing data for UI visualization.

    Usage:
        generator = PolylineGenerator()
        vis_data = generator.generate(
            layout=routing_layout,
            space_centers=design.get_space_centers(),
            zone_boundaries=design.get_fire_zones(),
        )

        # Use in UI
        for polyline in vis_data.polylines:
            render_trunk(polyline.points, polyline.color)
            for crossing in polyline.crossings:
                render_marker(crossing.position, crossing.crossing_type)
    """

    def __init__(
        self,
        interpolation_points: int = 0,  # 0 = straight lines, >0 = curved
        z_offset_per_system: float = 0.1,  # Vertical offset to separate overlapping systems
        show_crossing_markers: bool = True,
    ):
        """
        Initialize polyline generator.

        Args:
            interpolation_points: Points to add between space centers (smoothing)
            z_offset_per_system: Vertical offset per system for visibility
            show_crossing_markers: Whether to generate crossing markers
        """
        self._interpolation = interpolation_points
        self._z_offset = z_offset_per_system
        self._show_crossings = show_crossing_markers

    def generate(
        self,
        layout: RoutingLayout,
        space_centers: Dict[str, Tuple[float, float, float]],
        zone_boundaries: Optional[Dict[str, Set[str]]] = None,
        watertight_boundaries: Optional[Set[Tuple[str, str]]] = None,
    ) -> VisualizationData:
        """
        Generate visualization data from routing layout.

        Args:
            layout: Routing layout with topologies
            space_centers: Space center coordinates
            zone_boundaries: Fire zone definitions
            watertight_boundaries: Watertight boundary pairs

        Returns:
            VisualizationData for UI rendering
        """
        vis_data = VisualizationData(design_id=layout.design_id)

        zone_boundaries = zone_boundaries or {}
        watertight_boundaries = watertight_boundaries or set()

        # Build space-to-zone lookup
        space_to_zone: Dict[str, str] = {}
        for zone_id, spaces in zone_boundaries.items():
            for space_id in spaces:
                space_to_zone[space_id] = zone_id

        # Process each system
        system_index = 0
        for system_type, topology in layout.topologies.items():
            z_offset = system_index * self._z_offset
            system_index += 1

            vis_data.systems.append(system_type.value)

            # Collect node positions
            for node in topology.nodes.values():
                if node.space_id in space_centers:
                    center = space_centers[node.space_id]
                    vis_data.node_positions[node.node_id] = (
                        center[0], center[1], center[2] + z_offset
                    )

            # Generate polyline for each trunk
            for trunk in topology.trunks.values():
                polyline = self._generate_trunk_polyline(
                    trunk=trunk,
                    space_centers=space_centers,
                    space_to_zone=space_to_zone,
                    watertight_boundaries=watertight_boundaries,
                    z_offset=z_offset,
                )
                vis_data.polylines.append(polyline)
                vis_data.total_crossings += len(polyline.crossings)

        # Calculate totals
        vis_data.total_length_m = sum(p.length_m for p in vis_data.polylines)

        # Calculate bounding box
        if vis_data.polylines:
            all_points = [p for poly in vis_data.polylines for p in poly.points]
            if all_points:
                xs = [p[0] for p in all_points]
                ys = [p[1] for p in all_points]
                zs = [p[2] for p in all_points]
                vis_data.bounding_box = (
                    (min(xs), min(ys), min(zs)),
                    (max(xs), max(ys), max(zs)),
                )

        return vis_data

    def _generate_trunk_polyline(
        self,
        trunk: TrunkSegment,
        space_centers: Dict[str, Tuple[float, float, float]],
        space_to_zone: Dict[str, str],
        watertight_boundaries: Set[Tuple[str, str]],
        z_offset: float,
    ) -> TrunkPolyline:
        """Generate polyline for a single trunk."""
        polyline = TrunkPolyline(
            trunk_id=trunk.trunk_id,
            system_type=trunk.system_type,
            from_node_id=trunk.from_node_id,
            to_node_id=trunk.to_node_id,
            color=SYSTEM_COLORS.get(trunk.system_type, (128, 128, 128)),
            is_zone_compliant=trunk.is_zone_compliant,
            is_redundant=trunk.is_redundant_path,
        )

        # Set styling based on trunk properties
        if trunk.is_redundant_path:
            polyline.dash_pattern = [5, 3]  # Dashed line
            polyline.opacity = 0.7

        if not trunk.is_zone_compliant:
            polyline.color = (255, 0, 0)  # Red for violations

        if trunk.size.is_sized:
            polyline.diameter_mm = trunk.size.diameter_mm
            polyline.nominal_size = trunk.size.nominal_size
            # Scale line width based on size
            polyline.line_width = max(1.0, min(5.0, trunk.size.diameter_mm / 50))

        # Generate points from path
        if trunk.path_points:
            # Use existing detailed path
            polyline.points = [
                (p[0], p[1], p[2] + z_offset) for p in trunk.path_points
            ]
        elif trunk.path_spaces:
            # Generate from space centers
            for space_id in trunk.path_spaces:
                if space_id in space_centers:
                    center = space_centers[space_id]
                    polyline.points.append(
                        (center[0], center[1], center[2] + z_offset)
                    )

        # Generate crossing markers
        if self._show_crossings and len(trunk.path_spaces) >= 2:
            for i in range(len(trunk.path_spaces) - 1):
                from_space = trunk.path_spaces[i]
                to_space = trunk.path_spaces[i + 1]

                marker = self._detect_crossing(
                    from_space, to_space,
                    space_centers, space_to_zone, watertight_boundaries,
                    z_offset,
                )

                if marker:
                    polyline.crossings.append(marker)

        return polyline

    def _detect_crossing(
        self,
        from_space: str,
        to_space: str,
        space_centers: Dict[str, Tuple[float, float, float]],
        space_to_zone: Dict[str, str],
        watertight_boundaries: Set[Tuple[str, str]],
        z_offset: float,
    ) -> Optional[CrossingMarker]:
        """Detect and create crossing marker between spaces."""
        # Calculate midpoint for marker position
        if from_space not in space_centers or to_space not in space_centers:
            return None

        c1 = space_centers[from_space]
        c2 = space_centers[to_space]
        midpoint = (
            (c1[0] + c2[0]) / 2,
            (c1[1] + c2[1]) / 2,
            (c1[2] + c2[2]) / 2 + z_offset,
        )

        # Check for watertight boundary
        boundary_pair = tuple(sorted([from_space, to_space]))
        if boundary_pair in watertight_boundaries or (to_space, from_space) in watertight_boundaries:
            return CrossingMarker(
                position=midpoint,
                crossing_type=CrossingType.WATERTIGHT,
                from_space=from_space,
                to_space=to_space,
                requires_seal=True,
                notes="Watertight penetration required",
            )

        # Check for fire zone crossing
        zone_from = space_to_zone.get(from_space)
        zone_to = space_to_zone.get(to_space)

        if zone_from and zone_to and zone_from != zone_to:
            return CrossingMarker(
                position=midpoint,
                crossing_type=CrossingType.FIRE_ZONE,
                from_space=from_space,
                to_space=to_space,
                zone_id=f"{zone_from}->{zone_to}",
                requires_damper=True,
                notes="Fire damper or penetration seal required",
            )

        # Check for deck crossing (significant Z difference)
        if abs(c1[2] - c2[2]) > 1.5:  # More than 1.5m vertical
            return CrossingMarker(
                position=midpoint,
                crossing_type=CrossingType.DECK,
                from_space=from_space,
                to_space=to_space,
                notes="Deck penetration",
            )

        return None

    def generate_for_system(
        self,
        topology: SystemTopology,
        space_centers: Dict[str, Tuple[float, float, float]],
        zone_boundaries: Optional[Dict[str, Set[str]]] = None,
        watertight_boundaries: Optional[Set[Tuple[str, str]]] = None,
    ) -> List[TrunkPolyline]:
        """
        Generate polylines for a single system topology.

        Args:
            topology: System topology
            space_centers: Space center coordinates
            zone_boundaries: Fire zone definitions
            watertight_boundaries: Watertight boundaries

        Returns:
            List of polylines for this system
        """
        zone_boundaries = zone_boundaries or {}
        watertight_boundaries = watertight_boundaries or set()

        space_to_zone: Dict[str, str] = {}
        for zone_id, spaces in zone_boundaries.items():
            for space_id in spaces:
                space_to_zone[space_id] = zone_id

        polylines = []
        for trunk in topology.trunks.values():
            polyline = self._generate_trunk_polyline(
                trunk=trunk,
                space_centers=space_centers,
                space_to_zone=space_to_zone,
                watertight_boundaries=watertight_boundaries,
                z_offset=0,
            )
            polylines.append(polyline)

        return polylines
