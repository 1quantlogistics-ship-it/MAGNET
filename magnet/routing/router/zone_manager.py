"""
magnet/routing/router/zone_manager.py - Zone Manager

Validates zone crossings for system routing.
Enforces fire zone, watertight, and other boundary rules.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any
from enum import Enum

try:
    import networkx as nx
except ImportError:
    nx = None

from ..schema.system_type import SystemType, get_system_properties

__all__ = ['ZoneManager', 'ZoneCrossingResult', 'ZoneType', 'CrossingStatus']


class ZoneType(Enum):
    """Types of zones for routing compliance."""
    FIRE = "fire"               # Fire zone
    WATERTIGHT = "watertight"   # Watertight compartment
    HAZARDOUS = "hazardous"     # Hazardous area
    ACCOMMODATION = "accommodation"
    MACHINERY = "machinery"
    CARGO = "cargo"
    OTHER = "other"


class CrossingStatus(Enum):
    """Status of a zone crossing check."""
    ALLOWED = "allowed"
    CONDITIONAL = "conditional"  # Allowed with requirements
    PROHIBITED = "prohibited"


@dataclass
class ZoneCrossingResult:
    """Result of a zone crossing validation."""
    is_allowed: bool
    status: CrossingStatus
    from_zone: str
    to_zone: str
    from_zone_type: Optional[ZoneType] = None
    to_zone_type: Optional[ZoneType] = None
    reason: str = ""
    requirements: List[str] = field(default_factory=list)


class ZoneManager:
    """
    Manages zone crossing validation for system routing.

    Validates whether systems can cross zone boundaries based on:
    - System type properties (can_cross_fire_zone, can_cross_watertight)
    - Zone type rules
    - Separation requirements

    Usage:
        manager = ZoneManager()
        manager.add_zone('fire_zone_1', ZoneType.FIRE, {'er', 'pump_room'})
        manager.add_zone('fire_zone_2', ZoneType.FIRE, {'corridor', 'accommodation'})

        result = manager.check_crossing('er', 'corridor', SystemType.FUEL)
        if not result.is_allowed:
            print(f"Cannot route: {result.reason}")
    """

    def __init__(self):
        """Initialize zone manager."""
        # zone_id -> ZoneType
        self._zone_types: Dict[str, ZoneType] = {}

        # zone_id -> set of space_ids in that zone
        self._zone_spaces: Dict[str, Set[str]] = {}

        # space_id -> zone_id
        self._space_to_zone: Dict[str, str] = {}

        # Explicit boundary pairs (space_a, space_b) -> boundary type
        self._boundaries: Dict[Tuple[str, str], str] = {}

    # =========================================================================
    # Zone Configuration
    # =========================================================================

    def add_zone(
        self,
        zone_id: str,
        zone_type: ZoneType,
        space_ids: Set[str],
    ) -> None:
        """
        Add a zone definition.

        Args:
            zone_id: Unique zone identifier
            zone_type: Type of zone
            space_ids: Set of space IDs in this zone
        """
        self._zone_types[zone_id] = zone_type
        self._zone_spaces[zone_id] = set(space_ids)

        for space_id in space_ids:
            self._space_to_zone[space_id] = zone_id

    def remove_zone(self, zone_id: str) -> None:
        """Remove a zone definition."""
        if zone_id in self._zone_spaces:
            for space_id in self._zone_spaces[zone_id]:
                self._space_to_zone.pop(space_id, None)
            self._zone_spaces.pop(zone_id, None)
            self._zone_types.pop(zone_id, None)

    def add_boundary(
        self,
        space_a: str,
        space_b: str,
        boundary_type: str,
    ) -> None:
        """
        Add explicit boundary between spaces.

        Args:
            space_a: First space ID
            space_b: Second space ID
            boundary_type: Type of boundary (e.g., 'watertight', 'fire')
        """
        # Store in sorted order for consistent lookup
        key = tuple(sorted([space_a, space_b]))
        self._boundaries[key] = boundary_type

    def get_zone_for_space(self, space_id: str) -> Optional[str]:
        """Get zone ID for a space."""
        return self._space_to_zone.get(space_id)

    def get_zone_type(self, zone_id: str) -> Optional[ZoneType]:
        """Get zone type for a zone ID."""
        return self._zone_types.get(zone_id)

    def is_zone_boundary(self, space_a: str, space_b: str) -> bool:
        """Check if there's a zone boundary between two spaces."""
        zone_a = self._space_to_zone.get(space_a)
        zone_b = self._space_to_zone.get(space_b)

        if zone_a and zone_b and zone_a != zone_b:
            return True

        # Check explicit boundaries
        key = tuple(sorted([space_a, space_b]))
        return key in self._boundaries

    def get_boundary_type(
        self,
        space_a: str,
        space_b: str,
    ) -> Optional[str]:
        """Get boundary type between two spaces."""
        # Check explicit boundary first
        key = tuple(sorted([space_a, space_b]))
        if key in self._boundaries:
            return self._boundaries[key]

        # Infer from zone types
        zone_a = self._space_to_zone.get(space_a)
        zone_b = self._space_to_zone.get(space_b)

        if zone_a and zone_b and zone_a != zone_b:
            type_a = self._zone_types.get(zone_a)
            type_b = self._zone_types.get(zone_b)

            if type_a == ZoneType.FIRE or type_b == ZoneType.FIRE:
                return "fire"
            if type_a == ZoneType.WATERTIGHT or type_b == ZoneType.WATERTIGHT:
                return "watertight"

            return "zone"

        return None

    # =========================================================================
    # Crossing Validation
    # =========================================================================

    def check_crossing(
        self,
        from_space: str,
        to_space: str,
        system_type: SystemType,
    ) -> ZoneCrossingResult:
        """
        Check if a system can cross from one space to another.

        Args:
            from_space: Source space ID
            to_space: Target space ID
            system_type: System type to check

        Returns:
            ZoneCrossingResult with validation status
        """
        from_zone = self._space_to_zone.get(from_space, "")
        to_zone = self._space_to_zone.get(to_space, "")

        # Same zone - always allowed
        if from_zone == to_zone:
            return ZoneCrossingResult(
                is_allowed=True,
                status=CrossingStatus.ALLOWED,
                from_zone=from_zone,
                to_zone=to_zone,
            )

        # Get zone types
        from_type = self._zone_types.get(from_zone)
        to_type = self._zone_types.get(to_zone)

        # Get system properties
        props = get_system_properties(system_type)

        # Check boundary type
        boundary_type = self.get_boundary_type(from_space, to_space)

        # Fire zone boundary check
        if boundary_type == "fire" or from_type == ZoneType.FIRE or to_type == ZoneType.FIRE:
            if not props.can_cross_fire_zone:
                return ZoneCrossingResult(
                    is_allowed=False,
                    status=CrossingStatus.PROHIBITED,
                    from_zone=from_zone,
                    to_zone=to_zone,
                    from_zone_type=from_type,
                    to_zone_type=to_type,
                    reason=f"{system_type.value} cannot cross fire zone boundary",
                )
            else:
                return ZoneCrossingResult(
                    is_allowed=True,
                    status=CrossingStatus.CONDITIONAL,
                    from_zone=from_zone,
                    to_zone=to_zone,
                    from_zone_type=from_type,
                    to_zone_type=to_type,
                    requirements=["Fire damper or penetration seal required"],
                )

        # Watertight boundary check
        if boundary_type == "watertight" or from_type == ZoneType.WATERTIGHT or to_type == ZoneType.WATERTIGHT:
            if not props.can_cross_watertight:
                return ZoneCrossingResult(
                    is_allowed=False,
                    status=CrossingStatus.PROHIBITED,
                    from_zone=from_zone,
                    to_zone=to_zone,
                    from_zone_type=from_type,
                    to_zone_type=to_type,
                    reason=f"{system_type.value} cannot cross watertight boundary",
                )
            else:
                return ZoneCrossingResult(
                    is_allowed=True,
                    status=CrossingStatus.CONDITIONAL,
                    from_zone=from_zone,
                    to_zone=to_zone,
                    from_zone_type=from_type,
                    to_zone_type=to_type,
                    requirements=["Watertight penetration required"],
                )

        # Check prohibited zones
        for prohibited in props.prohibited_zones:
            if prohibited.lower() in str(to_type).lower() if to_type else False:
                return ZoneCrossingResult(
                    is_allowed=False,
                    status=CrossingStatus.PROHIBITED,
                    from_zone=from_zone,
                    to_zone=to_zone,
                    from_zone_type=from_type,
                    to_zone_type=to_type,
                    reason=f"{system_type.value} prohibited in {prohibited} zones",
                )

        # Default: allowed
        return ZoneCrossingResult(
            is_allowed=True,
            status=CrossingStatus.ALLOWED,
            from_zone=from_zone,
            to_zone=to_zone,
            from_zone_type=from_type,
            to_zone_type=to_type,
        )

    def check_path(
        self,
        path_spaces: List[str],
        system_type: SystemType,
    ) -> Tuple[bool, List[ZoneCrossingResult]]:
        """
        Check all crossings along a path.

        Args:
            path_spaces: Ordered list of space IDs in path
            system_type: System type to check

        Returns:
            Tuple of (all_valid, list of crossing results)
        """
        if len(path_spaces) < 2:
            return True, []

        results = []
        all_valid = True

        for i in range(len(path_spaces) - 1):
            result = self.check_crossing(
                path_spaces[i], path_spaces[i + 1], system_type
            )
            if result.status == CrossingStatus.PROHIBITED:
                all_valid = False
            results.append(result)

        return all_valid, results

    # =========================================================================
    # Compliant Path Finding
    # =========================================================================

    def find_compliant_path(
        self,
        start: str,
        end: str,
        system_type: SystemType,
        graph: 'nx.Graph',
        max_paths: int = 10,
    ) -> Optional[List[str]]:
        """
        Find a zone-compliant path between spaces.

        Args:
            start: Starting space ID
            end: Ending space ID
            system_type: System type
            graph: Compartment adjacency graph
            max_paths: Maximum paths to check

        Returns:
            First compliant path found, or None
        """
        if graph is None or nx is None:
            return None

        try:
            gen = nx.shortest_simple_paths(graph, start, end, weight='cost')

            for i, path in enumerate(gen):
                if i >= max_paths:
                    break

                is_valid, _ = self.check_path(path, system_type)
                if is_valid:
                    return path

        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass

        return None

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """Get zone manager statistics."""
        type_counts = {}
        for zone_type in self._zone_types.values():
            type_counts[zone_type.value] = type_counts.get(zone_type.value, 0) + 1

        return {
            'zone_count': len(self._zone_types),
            'space_count': len(self._space_to_zone),
            'boundary_count': len(self._boundaries),
            'zones_by_type': type_counts,
        }

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Serialize zone manager to dictionary."""
        return {
            'zones': {
                zone_id: {
                    'type': self._zone_types[zone_id].value,
                    'spaces': list(spaces),
                }
                for zone_id, spaces in self._zone_spaces.items()
            },
            'boundaries': {
                f"{k[0]}:{k[1]}": v
                for k, v in self._boundaries.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ZoneManager':
        """Deserialize zone manager from dictionary."""
        manager = cls()

        for zone_id, zone_data in data.get('zones', {}).items():
            zone_type = ZoneType(zone_data['type'])
            spaces = set(zone_data['spaces'])
            manager.add_zone(zone_id, zone_type, spaces)

        for key_str, boundary_type in data.get('boundaries', {}).items():
            space_a, space_b = key_str.split(':')
            manager.add_boundary(space_a, space_b, boundary_type)

        return manager
