"""
magnet/routing/schema/system_topology.py - System Topology Aggregate

SystemTopology represents the complete routing for a single system type,
containing all nodes, trunks, and validation state.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from datetime import datetime
from enum import Enum

from .system_type import SystemType, get_system_properties
from .system_node import SystemNode, NodeType
from .trunk_segment import TrunkSegment

__all__ = ['SystemTopology', 'TopologyStatus']


class TopologyStatus(Enum):
    """Status of a system topology."""
    EMPTY = "empty"           # No nodes defined
    PARTIAL = "partial"       # Some nodes, incomplete routing
    ROUTED = "routed"         # All nodes connected
    VALIDATED = "validated"   # Routing complete and validated
    FAILED = "failed"         # Routing failed


@dataclass
class SystemTopology:
    """
    Complete topology for a single system type.

    Contains all nodes (sources, junctions, consumers) and
    trunk segments connecting them.

    Attributes:
        system_type: The system this topology describes
        nodes: Dictionary of node_id -> SystemNode
        trunks: Dictionary of trunk_id -> TrunkSegment

        status: Current topology status
        validation_errors: List of validation errors
        validation_warnings: List of validation warnings

        total_capacity: Total source capacity
        total_demand: Total consumer demand
        total_length_m: Total trunk length

        has_redundancy: Whether redundant paths exist
        redundant_paths: List of redundant trunk pairs

        created_at: Creation timestamp
        modified_at: Last modification timestamp
        metadata: Extension point
    """

    # Identity
    system_type: SystemType

    # Components
    nodes: Dict[str, SystemNode] = field(default_factory=dict)
    trunks: Dict[str, TrunkSegment] = field(default_factory=dict)

    # Status
    status: TopologyStatus = TopologyStatus.EMPTY
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)

    # Aggregates (computed)
    total_capacity: float = 0.0
    total_demand: float = 0.0
    total_length_m: float = 0.0

    # Redundancy
    has_redundancy: bool = False
    redundant_paths: List[tuple] = field(default_factory=list)

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
    # Node Management
    # =========================================================================

    def add_node(self, node: SystemNode) -> None:
        """
        Add a node to the topology.

        Args:
            node: SystemNode to add

        Raises:
            ValueError: If node system type doesn't match
        """
        if node.system_type != self.system_type:
            raise ValueError(
                f"Node system type {node.system_type} doesn't match "
                f"topology system type {self.system_type}"
            )

        self.nodes[node.node_id] = node
        self._update_status()
        self._update_aggregates()
        self.modified_at = datetime.utcnow()

    def remove_node(self, node_id: str) -> Optional[SystemNode]:
        """
        Remove a node from the topology.

        Also removes any trunks connected to the node.

        Args:
            node_id: ID of node to remove

        Returns:
            Removed node, or None if not found
        """
        if node_id not in self.nodes:
            return None

        node = self.nodes.pop(node_id)

        # Remove connected trunks
        trunks_to_remove = [
            t for t in self.trunks.values()
            if t.from_node_id == node_id or t.to_node_id == node_id
        ]
        for trunk in trunks_to_remove:
            self.trunks.pop(trunk.trunk_id, None)

        self._update_status()
        self._update_aggregates()
        self.modified_at = datetime.utcnow()

        return node

    def get_node(self, node_id: str) -> Optional[SystemNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_nodes_by_type(self, node_type: NodeType) -> List[SystemNode]:
        """Get all nodes of a specific type."""
        return [n for n in self.nodes.values() if n.node_type == node_type]

    @property
    def sources(self) -> List[SystemNode]:
        """Get all source nodes."""
        return self.get_nodes_by_type(NodeType.SOURCE)

    @property
    def consumers(self) -> List[SystemNode]:
        """Get all consumer nodes."""
        return self.get_nodes_by_type(NodeType.CONSUMER)

    @property
    def junctions(self) -> List[SystemNode]:
        """Get all junction nodes."""
        return self.get_nodes_by_type(NodeType.JUNCTION)

    # =========================================================================
    # Trunk Management
    # =========================================================================

    def add_trunk(self, trunk: TrunkSegment) -> None:
        """
        Add a trunk to the topology.

        Args:
            trunk: TrunkSegment to add

        Raises:
            ValueError: If trunk system type doesn't match or endpoints invalid
        """
        if trunk.system_type != self.system_type:
            raise ValueError(
                f"Trunk system type {trunk.system_type} doesn't match "
                f"topology system type {self.system_type}"
            )

        if trunk.from_node_id not in self.nodes:
            raise ValueError(f"from_node_id {trunk.from_node_id} not in topology")

        if trunk.to_node_id not in self.nodes:
            raise ValueError(f"to_node_id {trunk.to_node_id} not in topology")

        self.trunks[trunk.trunk_id] = trunk

        # Update node connections
        self.nodes[trunk.from_node_id].add_trunk(trunk.trunk_id)
        self.nodes[trunk.to_node_id].add_trunk(trunk.trunk_id)

        self._update_status()
        self._update_aggregates()
        self.modified_at = datetime.utcnow()

    def remove_trunk(self, trunk_id: str) -> Optional[TrunkSegment]:
        """
        Remove a trunk from the topology.

        Args:
            trunk_id: ID of trunk to remove

        Returns:
            Removed trunk, or None if not found
        """
        if trunk_id not in self.trunks:
            return None

        trunk = self.trunks.pop(trunk_id)

        # Update node connections
        if trunk.from_node_id in self.nodes:
            self.nodes[trunk.from_node_id].remove_trunk(trunk_id)
        if trunk.to_node_id in self.nodes:
            self.nodes[trunk.to_node_id].remove_trunk(trunk_id)

        self._update_status()
        self._update_aggregates()
        self.modified_at = datetime.utcnow()

        return trunk

    def get_trunk(self, trunk_id: str) -> Optional[TrunkSegment]:
        """Get a trunk by ID."""
        return self.trunks.get(trunk_id)

    def get_trunks_for_node(self, node_id: str) -> List[TrunkSegment]:
        """Get all trunks connected to a node."""
        return [
            t for t in self.trunks.values()
            if t.from_node_id == node_id or t.to_node_id == node_id
        ]

    # =========================================================================
    # Connectivity
    # =========================================================================

    def get_connected_nodes(self, node_id: str) -> Set[str]:
        """
        Get all nodes directly connected to a node.

        Args:
            node_id: Node to find connections for

        Returns:
            Set of connected node IDs
        """
        connected = set()
        for trunk in self.trunks.values():
            if trunk.from_node_id == node_id:
                connected.add(trunk.to_node_id)
            elif trunk.to_node_id == node_id:
                connected.add(trunk.from_node_id)
        return connected

    def is_connected(self) -> bool:
        """
        Check if all nodes are connected.

        Uses BFS to verify all nodes are reachable from any source.
        """
        if not self.nodes:
            return True

        if not self.sources:
            return False

        # Start from first source
        start = self.sources[0].node_id
        visited = {start}
        queue = [start]

        while queue:
            current = queue.pop(0)
            for connected in self.get_connected_nodes(current):
                if connected not in visited:
                    visited.add(connected)
                    queue.append(connected)

        return len(visited) == len(self.nodes)

    def get_unconnected_nodes(self) -> List[str]:
        """Get list of nodes not connected to any source."""
        if not self.sources:
            return list(self.nodes.keys())

        start = self.sources[0].node_id
        visited = {start}
        queue = [start]

        while queue:
            current = queue.pop(0)
            for connected in self.get_connected_nodes(current):
                if connected not in visited:
                    visited.add(connected)
                    queue.append(connected)

        return [nid for nid in self.nodes if nid not in visited]

    # =========================================================================
    # Status & Validation
    # =========================================================================

    def _update_status(self) -> None:
        """Update topology status based on current state."""
        if not self.nodes:
            self.status = TopologyStatus.EMPTY
        elif not self.trunks:
            self.status = TopologyStatus.PARTIAL
        elif not self.is_connected():
            self.status = TopologyStatus.PARTIAL
        elif self.validation_errors:
            self.status = TopologyStatus.FAILED
        elif self.validation_warnings:
            self.status = TopologyStatus.ROUTED
        else:
            self.status = TopologyStatus.VALIDATED

    def _update_aggregates(self) -> None:
        """Update aggregate values."""
        self.total_capacity = sum(
            n.capacity_units for n in self.nodes.values()
            if n.node_type == NodeType.SOURCE
        )
        self.total_demand = sum(
            n.demand_units for n in self.nodes.values()
            if n.node_type == NodeType.CONSUMER
        )
        self.total_length_m = sum(
            t.length_m for t in self.trunks.values()
        )

    def validate(self) -> bool:
        """
        Validate the topology.

        Returns:
            True if valid, False if errors found
        """
        self.validation_errors.clear()
        self.validation_warnings.clear()

        # Check for nodes
        if not self.nodes:
            self.validation_errors.append("No nodes defined")
            self._update_status()
            return False

        # Check for sources
        if not self.sources:
            self.validation_errors.append("No source nodes defined")

        # Check for consumers
        if not self.consumers:
            self.validation_errors.append("No consumer nodes defined")

        # Check connectivity
        unconnected = self.get_unconnected_nodes()
        if unconnected:
            self.validation_errors.append(
                f"Unconnected nodes: {', '.join(unconnected)}"
            )

        # Check capacity vs demand
        if self.total_capacity < self.total_demand:
            self.validation_warnings.append(
                f"Total capacity ({self.total_capacity}) < total demand ({self.total_demand})"
            )

        # Check trunk zone compliance
        for trunk in self.trunks.values():
            if not trunk.is_zone_compliant:
                self.validation_errors.append(
                    f"Trunk {trunk.trunk_id}: {trunk.zone_violation_reason}"
                )

        # Check redundancy requirements
        props = get_system_properties(self.system_type)
        if props.requires_redundancy and not self.has_redundancy:
            self.validation_warnings.append(
                f"System {self.system_type.value} requires redundancy but none found"
            )

        self._update_status()
        return len(self.validation_errors) == 0

    # =========================================================================
    # Statistics
    # =========================================================================

    @property
    def node_count(self) -> int:
        """Total number of nodes."""
        return len(self.nodes)

    @property
    def trunk_count(self) -> int:
        """Total number of trunks."""
        return len(self.trunks)

    @property
    def source_count(self) -> int:
        """Number of source nodes."""
        return len(self.sources)

    @property
    def consumer_count(self) -> int:
        """Number of consumer nodes."""
        return len(self.consumers)

    def get_statistics(self) -> Dict[str, Any]:
        """Get topology statistics."""
        return {
            'system_type': self.system_type.value,
            'status': self.status.value,
            'node_count': self.node_count,
            'source_count': self.source_count,
            'consumer_count': self.consumer_count,
            'junction_count': len(self.junctions),
            'trunk_count': self.trunk_count,
            'total_capacity': self.total_capacity,
            'total_demand': self.total_demand,
            'total_length_m': self.total_length_m,
            'has_redundancy': self.has_redundancy,
            'is_connected': self.is_connected(),
            'error_count': len(self.validation_errors),
            'warning_count': len(self.validation_warnings),
        }

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'system_type': self.system_type.value,
            'nodes': {nid: n.to_dict() for nid, n in self.nodes.items()},
            'trunks': {tid: t.to_dict() for tid, t in self.trunks.items()},
            'status': self.status.value,
            'validation_errors': self.validation_errors,
            'validation_warnings': self.validation_warnings,
            'total_capacity': self.total_capacity,
            'total_demand': self.total_demand,
            'total_length_m': self.total_length_m,
            'has_redundancy': self.has_redundancy,
            'redundant_paths': self.redundant_paths,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'modified_at': self.modified_at.isoformat() if self.modified_at else None,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemTopology':
        """Deserialize from dictionary."""
        topology = cls(
            system_type=SystemType(data['system_type']),
            status=TopologyStatus(data.get('status', 'empty')),
            validation_errors=data.get('validation_errors', []),
            validation_warnings=data.get('validation_warnings', []),
            total_capacity=data.get('total_capacity', 0.0),
            total_demand=data.get('total_demand', 0.0),
            total_length_m=data.get('total_length_m', 0.0),
            has_redundancy=data.get('has_redundancy', False),
            redundant_paths=data.get('redundant_paths', []),
            metadata=data.get('metadata', {}),
        )

        # Restore timestamps
        if data.get('created_at'):
            topology.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('modified_at'):
            topology.modified_at = datetime.fromisoformat(data['modified_at'])

        # Restore nodes
        for node_data in data.get('nodes', {}).values():
            node = SystemNode.from_dict(node_data)
            topology.nodes[node.node_id] = node

        # Restore trunks
        for trunk_data in data.get('trunks', {}).values():
            trunk = TrunkSegment.from_dict(trunk_data)
            topology.trunks[trunk.trunk_id] = trunk

        return topology

    # =========================================================================
    # String Representation
    # =========================================================================

    def __repr__(self) -> str:
        return (
            f"SystemTopology(system={self.system_type.value}, "
            f"nodes={self.node_count}, trunks={self.trunk_count}, "
            f"status={self.status.value})"
        )

    def __str__(self) -> str:
        return (
            f"[{self.system_type.value.upper()}] "
            f"{self.source_count} sources, {self.consumer_count} consumers, "
            f"{self.trunk_count} trunks, {self.total_length_m:.1f}m total"
        )
