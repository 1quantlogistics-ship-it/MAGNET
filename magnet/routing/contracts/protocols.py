"""
magnet/routing/contracts/protocols.py - Protocol Definitions

Defines protocols (interfaces) for routing layer boundaries,
enabling dependency injection and independent testing.
"""

from typing import Protocol, Dict, List, Optional, Set, Any, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from magnet.routing.schema.system_type import SystemType
    from magnet.routing.schema.system_node import SystemNode
    from magnet.routing.schema.trunk_segment import TrunkSegment

__all__ = [
    'GraphBuilderProtocol',
    'RouterProtocol',
    'ZoneValidatorProtocol',
    'RoutingResultProtocol',
]


class RoutingResultProtocol(Protocol):
    """Protocol for routing results."""

    @property
    def success(self) -> bool:
        """Whether routing succeeded."""
        ...

    @property
    def trunks(self) -> List['TrunkSegment']:
        """List of routed trunks."""
        ...

    @property
    def errors(self) -> List[str]:
        """List of routing errors."""
        ...


class GraphBuilderProtocol(Protocol):
    """
    Protocol for compartment graph builders.

    Implementations build a graph representing space connectivity
    for routing purposes.
    """

    def build(
        self,
        spaces: Dict[str, Any],
        zone_boundaries: Optional[Dict[str, Set[str]]] = None,
        watertight_boundaries: Optional[Set[Tuple[str, str]]] = None,
    ) -> Any:
        """
        Build connectivity graph from spaces.

        Args:
            spaces: Dictionary of space_id -> space object
            zone_boundaries: Optional fire zone definitions
            watertight_boundaries: Optional watertight boundary pairs

        Returns:
            Graph object (typically networkx.Graph)
        """
        ...


class RouterProtocol(Protocol):
    """
    Protocol for trunk routers.

    Implementations compute routing between system nodes
    through a compartment graph.
    """

    def route_system(
        self,
        system_type: 'SystemType',
        nodes: List['SystemNode'],
        compartment_graph: Any,
        zone_boundaries: Optional[Dict[str, Set[str]]] = None,
    ) -> RoutingResultProtocol:
        """
        Route connections between nodes.

        Args:
            system_type: Type of system being routed
            nodes: List of nodes to connect
            compartment_graph: Graph representing space connectivity
            zone_boundaries: Optional zone boundary definitions

        Returns:
            Routing result with trunks and status
        """
        ...


class ZoneValidatorProtocol(Protocol):
    """
    Protocol for zone validation.

    Implementations check and score zone crossings for routing.
    """

    def validate_path(
        self,
        path_spaces: List[str],
        system_type: 'SystemType',
    ) -> bool:
        """
        Check if path is zone-compliant for system type.

        Args:
            path_spaces: List of space IDs in path
            system_type: Type of system

        Returns:
            True if path complies with zone rules
        """
        ...

    def get_crossing_cost(
        self,
        from_space: str,
        to_space: str,
        system_type: 'SystemType',
    ) -> float:
        """
        Get cost multiplier for edge based on zone crossings.

        Args:
            from_space: Source space ID
            to_space: Destination space ID
            system_type: Type of system

        Returns:
            Cost multiplier (1.0 = no crossing, inf = prohibited)
        """
        ...

    def get_zone_crossings(
        self,
        path_spaces: List[str],
    ) -> List[Tuple[str, str, str]]:
        """
        Get all zone crossings in a path.

        Args:
            path_spaces: List of space IDs in path

        Returns:
            List of (from_space, to_space, crossing_type) tuples
        """
        ...


class CapacityCalculatorProtocol(Protocol):
    """
    Protocol for capacity/sizing calculations.

    Implementations compute physical sizes for trunks.
    """

    def calculate_size(
        self,
        system_type: 'SystemType',
        demand: float,
        length_m: float = 0.0,
    ) -> Any:
        """
        Calculate trunk size for given demand.

        Args:
            system_type: Type of system
            demand: Demand in system-specific units
            length_m: Optional length for voltage drop calculations

        Returns:
            Sizing result with selected size and notes
        """
        ...
