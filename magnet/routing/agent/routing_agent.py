"""
magnet/routing/agent/routing_agent.py - Routing Agent

Main agent for routing all vessel systems through interior spaces.
Orchestrates the routing pipeline from node discovery to topology generation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple, Protocol, runtime_checkable
from enum import Enum
from datetime import datetime

try:
    import networkx as nx
except ImportError:
    nx = None

from ..schema.system_type import SystemType, get_system_properties, Criticality
from ..schema.system_node import SystemNode, NodeType
from ..schema.trunk_segment import TrunkSegment, TrunkSize
from ..schema.system_topology import SystemTopology, TopologyStatus
from ..schema.routing_layout import RoutingLayout, LayoutStatus
from ..graph.compartment_graph import CompartmentGraph
from ..router.trunk_router import TrunkRouter
from ..router.zone_manager import ZoneManager
from ..router.capacity_calc import CapacityCalculator

__all__ = ['RoutingAgent', 'RoutingConfig', 'RoutingStatus', 'AgentResult']


# =============================================================================
# Protocols for M59 Integration
# =============================================================================

@runtime_checkable
class InteriorLayoutProtocol(Protocol):
    """Protocol for M59 InteriorLayout."""
    spaces: Dict[str, Any]

    def get_space(self, space_id: str) -> Optional[Any]: ...
    def get_spaces_by_type(self, space_type: str) -> List[Any]: ...


@runtime_checkable
class EquipmentProtocol(Protocol):
    """Protocol for equipment items."""
    equipment_id: str
    space_id: str
    equipment_type: str
    power_kw: Optional[float]
    flow_rate_m3_h: Optional[float]


# =============================================================================
# Configuration and Result Classes
# =============================================================================

class RoutingStatus(Enum):
    """Status of the routing agent."""
    IDLE = "idle"
    ROUTING = "routing"
    OPTIMIZING = "optimizing"
    VALIDATING = "validating"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class RoutingConfig:
    """Configuration for routing operations."""
    # Routing behavior
    enable_redundancy: bool = True
    max_alternative_paths: int = 5
    prefer_existing_routes: bool = True

    # Zone compliance
    strict_zone_compliance: bool = True
    allow_conditional_crossings: bool = True

    # Optimization
    optimize_after_routing: bool = True
    optimization_iterations: int = 3

    # Validation
    validate_after_routing: bool = True
    fail_on_warnings: bool = False

    # System ordering
    route_critical_first: bool = True

    # Performance
    cache_compartment_graph: bool = True


@dataclass
class AgentResult:
    """Result of a routing operation."""
    success: bool
    status: RoutingStatus
    layout: Optional[RoutingLayout] = None

    routed_systems: List[SystemType] = field(default_factory=list)
    failed_systems: List[SystemType] = field(default_factory=list)
    skipped_systems: List[SystemType] = field(default_factory=list)

    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Routing Agent
# =============================================================================

class RoutingAgent:
    """
    Main agent for routing vessel systems.

    Orchestrates the complete routing pipeline:
    1. Discover system nodes from equipment/layout
    2. Build compartment graph from interior spaces
    3. Route each system using MST algorithm
    4. Validate zone compliance
    5. Optimize routes (optional)
    6. Generate RoutingLayout aggregate

    Usage:
        agent = RoutingAgent()

        # Route all systems
        result = agent.route_all(interior_layout, systems=[
            SystemType.FUEL,
            SystemType.FRESHWATER,
            SystemType.ELECTRICAL_LV,
        ])

        if result.success:
            layout = result.layout
            print(f"Routed {len(layout.routed_systems)} systems")
    """

    def __init__(self, config: Optional[RoutingConfig] = None):
        """
        Initialize routing agent.

        Args:
            config: Optional configuration (uses defaults if None)
        """
        self.config = config or RoutingConfig()

        # Components
        self._graph_builder = CompartmentGraph()
        self._router = TrunkRouter()
        self._zone_manager = ZoneManager()
        self._capacity_calc = CapacityCalculator()

        # State
        self._status = RoutingStatus.IDLE
        self._compartment_graph: Optional['nx.Graph'] = None
        self._current_layout: Optional[RoutingLayout] = None

        # Caches
        self._node_cache: Dict[SystemType, List[SystemNode]] = {}

    @property
    def status(self) -> RoutingStatus:
        """Get current agent status."""
        return self._status

    # =========================================================================
    # Main Routing Methods
    # =========================================================================

    def route_all(
        self,
        layout: Any,  # InteriorLayoutProtocol
        systems: Optional[List[SystemType]] = None,
        nodes_by_system: Optional[Dict[SystemType, List[SystemNode]]] = None,
        design_id: str = "",
    ) -> AgentResult:
        """
        Route all specified systems through the interior layout.

        Args:
            layout: Interior layout with spaces (M59)
            systems: List of system types to route (None = all)
            nodes_by_system: Pre-defined nodes by system type
            design_id: Design identifier for the result

        Returns:
            AgentResult with routing status and layout
        """
        start_time = datetime.utcnow()
        errors = []
        warnings = []

        try:
            self._status = RoutingStatus.ROUTING

            # Determine systems to route
            if systems is None:
                systems = list(SystemType)

            # Order systems by criticality if configured
            if self.config.route_critical_first:
                systems = self._order_by_criticality(systems)

            # Build compartment graph
            if self._compartment_graph is None or not self.config.cache_compartment_graph:
                self._compartment_graph = self._build_compartment_graph(layout)

            if self._compartment_graph is None:
                return AgentResult(
                    success=False,
                    status=RoutingStatus.FAILED,
                    errors=["Failed to build compartment graph"],
                )

            # Create routing layout
            routing_layout = RoutingLayout(design_id=design_id)

            routed = []
            failed = []
            skipped = []

            # Route each system
            for system_type in systems:
                # Get nodes for this system
                if nodes_by_system and system_type in nodes_by_system:
                    nodes = nodes_by_system[system_type]
                else:
                    nodes = self._discover_nodes(layout, system_type)

                if not nodes:
                    skipped.append(system_type)
                    warnings.append(f"No nodes found for {system_type.value}")
                    continue

                # Route the system
                result = self.route_system(
                    system_type=system_type,
                    nodes=nodes,
                    compartment_graph=self._compartment_graph,
                )

                if result.success:
                    routing_layout.add_topology(result.topology)
                    routed.append(system_type)
                else:
                    failed.append(system_type)
                    errors.extend(result.errors)

            # Optimize if configured
            if self.config.optimize_after_routing and routed:
                self._status = RoutingStatus.OPTIMIZING
                self._optimize_layout(routing_layout)

            # Validate if configured
            if self.config.validate_after_routing:
                self._status = RoutingStatus.VALIDATING
                validation_errors = self._validate_layout(routing_layout)
                if validation_errors:
                    if self.config.fail_on_warnings:
                        errors.extend(validation_errors)
                    else:
                        warnings.extend(validation_errors)

            # Determine success
            success = len(failed) == 0 and len(routed) > 0
            self._status = RoutingStatus.COMPLETE if success else RoutingStatus.FAILED
            self._current_layout = routing_layout

            duration = (datetime.utcnow() - start_time).total_seconds()

            return AgentResult(
                success=success,
                status=self._status,
                layout=routing_layout,
                routed_systems=routed,
                failed_systems=failed,
                skipped_systems=skipped,
                errors=errors,
                warnings=warnings,
                duration_seconds=duration,
                metadata={
                    'config': {
                        'redundancy': self.config.enable_redundancy,
                        'strict_zones': self.config.strict_zone_compliance,
                    },
                },
            )

        except Exception as e:
            self._status = RoutingStatus.FAILED
            return AgentResult(
                success=False,
                status=RoutingStatus.FAILED,
                errors=[f"Routing failed: {str(e)}"],
            )

    def route_system(
        self,
        system_type: SystemType,
        nodes: List[SystemNode],
        compartment_graph: Optional['nx.Graph'] = None,
    ) -> 'SystemRoutingResult':
        """
        Route a single system.

        Args:
            system_type: System type to route
            nodes: List of system nodes
            compartment_graph: Optional pre-built graph

        Returns:
            SystemRoutingResult with topology
        """
        errors = []

        # Use cached graph if available
        graph = compartment_graph or self._compartment_graph
        if graph is None:
            return SystemRoutingResult(
                success=False,
                system_type=system_type,
                errors=["No compartment graph available"],
            )

        # Get system properties
        props = get_system_properties(system_type)

        # Configure router for this system
        enable_redundancy = (
            self.config.enable_redundancy and
            props.requires_redundancy
        )

        # Route using TrunkRouter
        if enable_redundancy:
            result = self._router.route_with_redundancy(
                system_type=system_type,
                nodes=nodes,
                compartment_graph=graph,
                zone_manager=self._zone_manager,
            )
        else:
            result = self._router.route_system(
                system_type=system_type,
                nodes=nodes,
                compartment_graph=graph,
                zone_manager=self._zone_manager,
            )

        if not result.success:
            return SystemRoutingResult(
                success=False,
                system_type=system_type,
                errors=result.errors,
            )

        # Build topology from result
        topology = self._build_topology(
            system_type=system_type,
            nodes=nodes,
            trunks=result.trunks,
        )

        # Check zone compliance
        if self.config.strict_zone_compliance:
            compliance_errors = self._check_zone_compliance(topology)
            if compliance_errors:
                topology.status = TopologyStatus.FAILED
                topology.validation_errors.extend(compliance_errors)
                errors.extend(compliance_errors)
        else:
            topology.status = TopologyStatus.ROUTED

        return SystemRoutingResult(
            success=len(errors) == 0,
            system_type=system_type,
            topology=topology,
            errors=errors,
        )

    def reroute(
        self,
        system_type: SystemType,
        layout: Any,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """
        Reroute a single system with optional constraints.

        Args:
            system_type: System to reroute
            layout: Interior layout
            constraints: Optional routing constraints

        Returns:
            AgentResult with updated layout
        """
        # Get existing nodes
        if self._current_layout and system_type in self._current_layout.topologies:
            existing = self._current_layout.topologies[system_type]
            nodes = list(existing.nodes.values())
        else:
            nodes = self._discover_nodes(layout, system_type)

        # Rebuild graph if needed
        if self._compartment_graph is None:
            self._compartment_graph = self._build_compartment_graph(layout)

        # Route with constraints
        result = self.route_system(
            system_type=system_type,
            nodes=nodes,
            compartment_graph=self._compartment_graph,
        )

        if result.success and self._current_layout:
            self._current_layout.add_topology(result.topology)

        return AgentResult(
            success=result.success,
            status=RoutingStatus.COMPLETE if result.success else RoutingStatus.FAILED,
            layout=self._current_layout,
            routed_systems=[system_type] if result.success else [],
            failed_systems=[] if result.success else [system_type],
            errors=result.errors,
        )

    # =========================================================================
    # Node Discovery
    # =========================================================================

    def _discover_nodes(
        self,
        layout: Any,
        system_type: SystemType,
    ) -> List[SystemNode]:
        """
        Discover system nodes from interior layout.

        Args:
            layout: Interior layout with spaces
            system_type: System type to find nodes for

        Returns:
            List of discovered SystemNodes
        """
        # Check cache
        if system_type in self._node_cache:
            return self._node_cache[system_type]

        nodes = []

        # This would normally integrate with equipment placement
        # For now, return empty - nodes should be provided externally
        # or discovered from equipment in spaces

        # Cache for reuse
        self._node_cache[system_type] = nodes
        return nodes

    def register_nodes(
        self,
        system_type: SystemType,
        nodes: List[SystemNode],
    ) -> None:
        """
        Register nodes for a system type.

        Args:
            system_type: System type
            nodes: List of nodes to register
        """
        self._node_cache[system_type] = nodes

    def clear_node_cache(self) -> None:
        """Clear the node cache."""
        self._node_cache.clear()

    # =========================================================================
    # Graph Building
    # =========================================================================

    def _build_compartment_graph(
        self,
        layout: Any,
    ) -> Optional['nx.Graph']:
        """
        Build compartment graph from interior layout.

        Args:
            layout: Interior layout with spaces

        Returns:
            NetworkX graph or None if failed
        """
        if nx is None:
            return None

        try:
            # Extract spaces from layout
            if hasattr(layout, 'spaces'):
                spaces = layout.spaces
            elif isinstance(layout, dict):
                spaces = layout.get('spaces', layout)
            else:
                return None

            # Build graph using CompartmentGraph
            graph = self._graph_builder.build(spaces)
            return graph

        except Exception:
            return None

    # =========================================================================
    # Topology Building
    # =========================================================================

    def _build_topology(
        self,
        system_type: SystemType,
        nodes: List[SystemNode],
        trunks: List[TrunkSegment],
    ) -> SystemTopology:
        """
        Build SystemTopology from nodes and trunks.

        Args:
            system_type: System type
            nodes: List of nodes
            trunks: List of trunk segments

        Returns:
            SystemTopology aggregate
        """
        topology = SystemTopology(system_type=system_type)

        # Add nodes
        for node in nodes:
            topology.add_node(node)

        # Add trunks and connect to nodes
        for trunk in trunks:
            topology.add_trunk(trunk)

        return topology

    # =========================================================================
    # Zone Compliance
    # =========================================================================

    def _check_zone_compliance(
        self,
        topology: SystemTopology,
    ) -> List[str]:
        """
        Check zone compliance for a topology.

        Args:
            topology: System topology to check

        Returns:
            List of compliance error messages
        """
        errors = []

        for trunk in topology.trunks.values():
            if not trunk.is_zone_compliant:
                errors.append(
                    f"Trunk {trunk.trunk_id} has zone compliance issues"
                )

            # Check each path segment
            if len(trunk.path_spaces) >= 2:
                is_valid, crossings = self._zone_manager.check_path(
                    trunk.path_spaces,
                    topology.system_type,
                )
                if not is_valid:
                    for crossing in crossings:
                        if not crossing.is_allowed:
                            errors.append(
                                f"Invalid zone crossing: {crossing.reason}"
                            )

        return errors

    # =========================================================================
    # Optimization
    # =========================================================================

    def _optimize_layout(self, layout: RoutingLayout) -> None:
        """
        Optimize routing layout.

        Args:
            layout: Layout to optimize (modified in place)
        """
        # Placeholder for optimization logic
        # Would typically:
        # 1. Consolidate parallel routes
        # 2. Minimize zone crossings
        # 3. Balance trunk utilization
        pass

    # =========================================================================
    # Validation
    # =========================================================================

    def _validate_layout(self, layout: RoutingLayout) -> List[str]:
        """
        Validate entire routing layout.

        Args:
            layout: Layout to validate

        Returns:
            List of validation error/warning messages
        """
        messages = []

        # Validate each topology
        for system_type, topology in layout.topologies.items():
            errors = topology.validate()
            if errors:
                messages.extend(errors)

        # Cross-system validation
        # Check for conflicts between systems
        space_systems = layout.get_spaces_with_systems()
        high_density = layout.get_high_density_spaces(threshold=5)

        for space_id in high_density:
            systems = space_systems.get(space_id, [])
            messages.append(
                f"High system density in {space_id}: {len(systems)} systems"
            )

        return messages

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _order_by_criticality(
        self,
        systems: List[SystemType],
    ) -> List[SystemType]:
        """
        Order systems by criticality (most critical first).

        Args:
            systems: List of system types

        Returns:
            Ordered list
        """
        def criticality_key(st: SystemType) -> int:
            props = get_system_properties(st)
            order = {
                Criticality.CRITICAL: 0,
                Criticality.HIGH: 1,
                Criticality.MEDIUM: 2,
                Criticality.LOW: 3,
            }
            return order.get(props.criticality, 4)

        return sorted(systems, key=criticality_key)

    def get_statistics(self) -> Dict[str, Any]:
        """Get agent statistics."""
        stats = {
            'status': self._status.value,
            'cached_nodes': len(self._node_cache),
            'has_compartment_graph': self._compartment_graph is not None,
        }

        if self._current_layout:
            stats['layout'] = self._current_layout.get_statistics()

        return stats

    def reset(self) -> None:
        """Reset agent state."""
        self._status = RoutingStatus.IDLE
        self._compartment_graph = None
        self._current_layout = None
        self._node_cache.clear()
        self._capacity_calc.clear_cache()


# =============================================================================
# Helper Result Classes
# =============================================================================

@dataclass
class SystemRoutingResult:
    """Result of routing a single system."""
    success: bool
    system_type: SystemType
    topology: Optional[SystemTopology] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
