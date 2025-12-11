"""
magnet/routing/service/routing_service.py - Routing Service Façade

Enforces RoutingInputContract as the mandatory entry point for routing,
preventing direct router access and ensuring lineage tracking.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime
import logging

try:
    import networkx as nx
except ImportError:
    nx = None

from ..contracts.routing_input import RoutingInputContract, SpaceInfo
from ..contracts.routing_lineage import (
    RoutingLineage,
    LineageStatus,
    compute_geometry_hash,
    compute_arrangement_hash,
)
from ..schema.system_type import SystemType
from ..schema.system_node import SystemNode
from ..schema.routing_layout import RoutingLayout
from ..schema.system_topology import SystemTopology
from ..router.trunk_router import TrunkRouter, RoutingResult
from ..router.zone_manager import ZoneManager, ZoneType
from ..graph.compartment_graph import CompartmentGraph

__all__ = ['RoutingService', 'RoutingServiceResult']

logger = logging.getLogger(__name__)


@dataclass
class RoutingServiceResult:
    """Result from the routing service."""
    success: bool
    layout: Optional[RoutingLayout] = None
    lineage: Optional[RoutingLineage] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    routing_time_ms: float = 0.0


class RoutingService:
    """
    Routing service façade that enforces RoutingInputContract.

    This is the ONLY supported entry point for routing operations.
    Direct router access is deprecated and will be removed in V4.

    Features:
    - Mandatory RoutingInputContract for all routing
    - Automatic lineage tracking
    - Staleness detection before routing
    - Integrated zone management
    - Result caching (optional)

    Usage:
        service = RoutingService()

        # Build contract from design state
        contract = RoutingInputContract.create(
            spaces=design.get_spaces(),
            adjacency=design.get_adjacency(),
            fire_zones=design.get_fire_zones(),
            system_nodes=design.get_system_nodes(),
        )

        # Route with contract
        result = service.route(contract)

        if result.success:
            layout = result.layout
            lineage = result.lineage
    """

    def __init__(
        self,
        allow_zone_violations: bool = False,
        max_reroute_attempts: int = 3,
        geometry_precision_m: float = 0.01,
        enable_caching: bool = False,
    ):
        """
        Initialize routing service.

        Args:
            allow_zone_violations: Whether to allow non-compliant routes
            max_reroute_attempts: Max attempts to find compliant route
            geometry_precision_m: Precision for geometry quantization
            enable_caching: Whether to cache routing results
        """
        if nx is None:
            raise ImportError("networkx is required for RoutingService")

        self._allow_violations = allow_zone_violations
        self._max_reroute = max_reroute_attempts
        self._geometry_precision = geometry_precision_m
        self._enable_caching = enable_caching

        # Result cache: contract_hash -> (layout, lineage)
        self._cache: Dict[str, Tuple[RoutingLayout, RoutingLineage]] = {}

    def route(
        self,
        contract: RoutingInputContract,
        design_id: str = "",
        design_version: int = 0,
    ) -> RoutingServiceResult:
        """
        Route all systems defined in the contract.

        This is the primary entry point for routing. The contract
        must be a valid RoutingInputContract instance.

        Args:
            contract: Immutable routing input contract
            design_id: Optional design identifier for lineage
            design_version: Optional design version for lineage

        Returns:
            RoutingServiceResult with layout and lineage
        """
        start_time = datetime.utcnow()
        result = RoutingServiceResult(success=False)

        # Validate contract type
        if not isinstance(contract, RoutingInputContract):
            result.errors.append(
                f"Invalid contract type: {type(contract).__name__}. "
                "Use RoutingInputContract.create() to build contracts."
            )
            return result

        # Check cache
        contract_hash = contract.content_hash()
        if self._enable_caching and contract_hash in self._cache:
            cached_layout, cached_lineage = self._cache[contract_hash]
            result.success = True
            result.layout = cached_layout
            result.lineage = cached_lineage
            result.warnings.append("Using cached routing result")
            return result

        # Build lineage
        lineage = self._build_lineage(contract, design_id, design_version)

        # Build compartment graph
        try:
            compartment_graph = self._build_compartment_graph(contract)
        except Exception as e:
            result.errors.append(f"Failed to build compartment graph: {e}")
            return result

        # Setup zone manager
        zone_manager = self._build_zone_manager(contract)

        # Create router
        router = TrunkRouter(
            zone_manager=zone_manager,
            allow_zone_violations=self._allow_violations,
            max_reroute_attempts=self._max_reroute,
        )

        # Create layout
        layout = RoutingLayout(design_id=design_id)
        layout.lineage = lineage

        # Get space centers for length calculation
        space_centers = self._get_space_centers(contract)

        # Route each system
        system_nodes = contract.get_system_nodes()

        for system_type, nodes in system_nodes.items():
            if len(nodes) < 2:
                result.warnings.append(
                    f"Skipping {system_type.value}: need at least 2 nodes"
                )
                continue

            routing_result = router.route_system(
                system_type=system_type,
                nodes=nodes,
                compartment_graph=compartment_graph,
                zone_boundaries=contract.get_fire_zones(),
                space_centers=space_centers,
            )

            if routing_result.success and routing_result.topology:
                layout.add_topology(routing_result.topology)
                result.warnings.extend(routing_result.warnings)
            else:
                result.errors.extend(routing_result.errors)
                result.warnings.extend(routing_result.warnings)

        # Finalize layout
        layout.update_hash()

        # Update lineage with output hash
        lineage.set_output_hash(layout.content_hash)
        lineage.status = LineageStatus.CURRENT

        # Cache result
        if self._enable_caching:
            self._cache[contract_hash] = (layout, lineage)

        # Build result
        result.success = layout.status.value not in ('empty', 'failed')
        result.layout = layout
        result.lineage = lineage

        end_time = datetime.utcnow()
        result.routing_time_ms = (end_time - start_time).total_seconds() * 1000

        logger.info(
            f"RoutingService completed: {layout.system_count} systems, "
            f"{layout.total_trunk_count} trunks, {result.routing_time_ms:.1f}ms"
        )

        return result

    def check_staleness(
        self,
        layout: RoutingLayout,
        contract: RoutingInputContract,
    ) -> Tuple[bool, str, List[str]]:
        """
        Check if existing layout is stale relative to current contract.

        Args:
            layout: Existing routing layout with lineage
            contract: Current routing input contract

        Returns:
            Tuple of (is_stale, status, reasons)
        """
        if not layout.lineage:
            return True, LineageStatus.UNKNOWN, ["No lineage in layout"]

        # Compute current hashes
        space_centers = self._get_space_centers(contract)
        current_geometry_hash = compute_geometry_hash(
            space_centers, self._geometry_precision
        )
        current_arrangement_hash = compute_arrangement_hash(
            contract.get_adjacency(),
            contract.get_fire_zones(),
            contract.get_watertight_boundaries(),
        )
        current_input_hash = contract.content_hash()

        # Check staleness
        status = layout.lineage.check_staleness(
            current_geometry_hash=current_geometry_hash,
            current_arrangement_hash=current_arrangement_hash,
            current_input_hash=current_input_hash,
        )

        is_stale = status != LineageStatus.CURRENT
        return is_stale, status, layout.lineage.staleness_reasons

    def route_if_stale(
        self,
        layout: RoutingLayout,
        contract: RoutingInputContract,
        design_id: str = "",
        design_version: int = 0,
    ) -> RoutingServiceResult:
        """
        Route only if existing layout is stale.

        Args:
            layout: Existing routing layout to check
            contract: Current routing input contract
            design_id: Design identifier
            design_version: Design version

        Returns:
            RoutingServiceResult (may be from existing layout if not stale)
        """
        is_stale, status, reasons = self.check_staleness(layout, contract)

        if not is_stale:
            # Return existing layout
            result = RoutingServiceResult(success=True)
            result.layout = layout
            result.lineage = layout.lineage
            result.warnings.append(f"Using existing routing (status: {status})")
            return result

        # Log staleness reasons
        logger.info(f"Re-routing due to staleness: {reasons}")

        # Route fresh
        return self.route(contract, design_id, design_version)

    def clear_cache(self) -> int:
        """
        Clear the routing cache.

        Returns:
            Number of cached entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        return count

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _build_lineage(
        self,
        contract: RoutingInputContract,
        design_id: str,
        design_version: int,
    ) -> RoutingLineage:
        """Build lineage from contract."""
        space_centers = self._get_space_centers(contract)

        lineage = RoutingLineage(
            source_design_id=design_id,
            source_version=design_version,
            geometry_precision_m=self._geometry_precision,
        )

        lineage.compute_from_inputs(
            space_centers=space_centers,
            adjacency=contract.get_adjacency(),
            fire_zones=contract.get_fire_zones(),
            watertight_boundaries=contract.get_watertight_boundaries(),
            routing_input_hash=contract.content_hash(),
        )

        return lineage

    def _build_compartment_graph(
        self,
        contract: RoutingInputContract,
    ) -> 'nx.Graph':
        """Build compartment graph from contract."""
        # Convert SpaceInfo to dict format for CompartmentGraph
        spaces_dict = {}
        for space_id, space_info in contract.spaces:
            spaces_dict[space_id] = {
                'instance_id': space_info.space_id,
                'space_type': space_info.space_type,
                'deck_id': space_info.deck_id or '',
                'center': space_info.center,
                'connected_spaces': list(
                    neighbors for sid, neighbors in contract.adjacency
                    if sid == space_id
                )[0] if any(sid == space_id for sid, _ in contract.adjacency) else [],
            }

        graph_builder = CompartmentGraph()
        return graph_builder.build(
            spaces=spaces_dict,
            zone_boundaries=contract.get_fire_zones(),
            watertight_boundaries=contract.get_watertight_boundaries(),
        )

    def _build_zone_manager(
        self,
        contract: RoutingInputContract,
    ) -> ZoneManager:
        """Build zone manager from contract."""
        zone_manager = ZoneManager()

        # Add fire zones
        for zone_id, space_ids in contract.get_fire_zones().items():
            zone_manager.add_zone(zone_id, ZoneType.FIRE, space_ids)

        # Add watertight boundaries
        for space_a, space_b in contract.get_watertight_boundaries():
            zone_manager.add_boundary(space_a, space_b, 'watertight')

        return zone_manager

    def _get_space_centers(
        self,
        contract: RoutingInputContract,
    ) -> Dict[str, Tuple[float, float, float]]:
        """Extract space centers from contract."""
        return {
            space_id: space_info.center
            for space_id, space_info in contract.spaces
        }
