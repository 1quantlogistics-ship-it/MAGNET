"""
magnet/routing/schema/system_node.py - System Node Schema

Nodes represent points in the system topology where routing
starts (SOURCE), ends (CONSUMER), branches (JUNCTION), or
passes through boundaries (PASS_THROUGH).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
import uuid

from .system_type import SystemType

__all__ = ['NodeType', 'SystemNode', 'generate_node_id']


class NodeType(Enum):
    """Type of node in system topology."""
    SOURCE = "source"           # Produces (tank, generator, pump)
    JUNCTION = "junction"       # Distributes (manifold, panel, valve)
    CONSUMER = "consumer"       # Consumes (equipment, outlet, fixture)
    PASS_THROUGH = "pass_through"  # Routes through (penetration, transition)


def generate_node_id() -> str:
    """Generate unique node ID."""
    return f"node_{uuid.uuid4().hex[:12]}"


@dataclass
class SystemNode:
    """
    Node in a system topology.

    Represents a point where system routing starts, ends, branches,
    or passes through a boundary.

    Attributes:
        node_id: Unique identifier for this node
        node_type: SOURCE, JUNCTION, CONSUMER, or PASS_THROUGH
        system_type: Which system this node belongs to

        space_id: Reference to SpaceInstance where node is located
        position: Optional 3D position within space (x, y, z in meters)

        capacity_units: Capacity in system-specific units
            - Fluid: liters or liters/hour
            - Electrical: watts or amps
            - HVAC: cubic meters/hour

        demand_units: Demand (for consumers) or supply (for sources)

        connected_trunks: List of trunk IDs connected to this node

        equipment_id: Reference to equipment item (if applicable)
        is_critical: Whether this is a critical node
        requires_redundant_feed: Whether redundant supply required

        name: Human-readable name
        description: Optional description
        metadata: Extension point for additional data
    """

    # Identity
    node_id: str
    node_type: NodeType
    system_type: SystemType

    # Location
    space_id: str
    position: Optional[Tuple[float, float, float]] = None

    # Capacity (units depend on system type)
    capacity_units: float = 0.0
    demand_units: float = 0.0

    # Connections (populated during routing)
    connected_trunks: List[str] = field(default_factory=list)

    # References
    equipment_id: Optional[str] = None

    # Flags
    is_critical: bool = False
    requires_redundant_feed: bool = False

    # Metadata
    name: str = ""
    description: str = ""
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and normalize node data."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        self.modified_at = datetime.utcnow()

        # Sources have supply (capacity), not demand
        if self.node_type == NodeType.SOURCE and self.demand_units > 0:
            self.capacity_units = max(self.capacity_units, self.demand_units)
            self.demand_units = 0.0

        # Consumers have demand, not capacity
        if self.node_type == NodeType.CONSUMER and self.capacity_units > 0:
            self.demand_units = max(self.demand_units, self.capacity_units)
            self.capacity_units = 0.0

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def is_source(self) -> bool:
        """Check if this is a source node."""
        return self.node_type == NodeType.SOURCE

    @property
    def is_consumer(self) -> bool:
        """Check if this is a consumer node."""
        return self.node_type == NodeType.CONSUMER

    @property
    def is_junction(self) -> bool:
        """Check if this is a junction node."""
        return self.node_type == NodeType.JUNCTION

    @property
    def is_pass_through(self) -> bool:
        """Check if this is a pass-through node."""
        return self.node_type == NodeType.PASS_THROUGH

    @property
    def is_endpoint(self) -> bool:
        """Check if this node is an endpoint (source or consumer)."""
        return self.node_type in (NodeType.SOURCE, NodeType.CONSUMER)

    @property
    def connection_count(self) -> int:
        """Number of connected trunks."""
        return len(self.connected_trunks)

    @property
    def effective_value(self) -> float:
        """Get capacity (for sources) or demand (for consumers)."""
        if self.node_type == NodeType.SOURCE:
            return self.capacity_units
        elif self.node_type == NodeType.CONSUMER:
            return self.demand_units
        else:
            return 0.0

    # =========================================================================
    # Connection Management
    # =========================================================================

    def add_trunk(self, trunk_id: str) -> None:
        """
        Add a connected trunk.

        Args:
            trunk_id: ID of trunk to connect
        """
        if trunk_id not in self.connected_trunks:
            self.connected_trunks.append(trunk_id)
            self.modified_at = datetime.utcnow()

    def remove_trunk(self, trunk_id: str) -> None:
        """
        Remove a connected trunk.

        Args:
            trunk_id: ID of trunk to disconnect
        """
        if trunk_id in self.connected_trunks:
            self.connected_trunks.remove(trunk_id)
            self.modified_at = datetime.utcnow()

    def has_trunk(self, trunk_id: str) -> bool:
        """Check if trunk is connected to this node."""
        return trunk_id in self.connected_trunks

    def clear_trunks(self) -> None:
        """Remove all trunk connections."""
        self.connected_trunks.clear()
        self.modified_at = datetime.utcnow()

    # =========================================================================
    # Validation
    # =========================================================================

    def validate(self) -> List[str]:
        """
        Validate node configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self.node_id:
            errors.append("node_id is required")

        if not self.space_id:
            errors.append("space_id is required")

        if self.node_type == NodeType.SOURCE and self.capacity_units <= 0:
            errors.append("SOURCE nodes must have capacity_units > 0")

        if self.node_type == NodeType.CONSUMER and self.demand_units <= 0:
            errors.append("CONSUMER nodes must have demand_units > 0")

        if self.position is not None and len(self.position) != 3:
            errors.append("position must be a 3-tuple (x, y, z)")

        return errors

    def is_valid(self) -> bool:
        """Check if node configuration is valid."""
        return len(self.validate()) == 0

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize node to dictionary.

        Returns:
            Dictionary representation for JSON serialization
        """
        return {
            'node_id': self.node_id,
            'node_type': self.node_type.value,
            'system_type': self.system_type.value,
            'space_id': self.space_id,
            'position': list(self.position) if self.position else None,
            'capacity_units': self.capacity_units,
            'demand_units': self.demand_units,
            'connected_trunks': list(self.connected_trunks),
            'equipment_id': self.equipment_id,
            'is_critical': self.is_critical,
            'requires_redundant_feed': self.requires_redundant_feed,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'modified_at': self.modified_at.isoformat() if self.modified_at else None,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemNode':
        """
        Deserialize node from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            SystemNode instance
        """
        data = data.copy()

        # Convert enums
        data['node_type'] = NodeType(data['node_type'])
        data['system_type'] = SystemType(data['system_type'])

        # Convert position tuple
        if data.get('position'):
            data['position'] = tuple(data['position'])

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
        return (
            f"SystemNode(id={self.node_id!r}, type={self.node_type.value}, "
            f"system={self.system_type.value}, space={self.space_id!r})"
        )

    def __str__(self) -> str:
        name_part = f" '{self.name}'" if self.name else ""
        return f"{self.node_type.value.upper()}{name_part} [{self.system_type.value}] in {self.space_id}"


# =========================================================================
# Factory Functions
# =========================================================================

def create_source_node(
    system_type: SystemType,
    space_id: str,
    capacity: float,
    name: str = "",
    position: Optional[Tuple[float, float, float]] = None,
    equipment_id: Optional[str] = None,
    is_critical: bool = False,
) -> SystemNode:
    """
    Create a source node (tank, generator, pump).

    Args:
        system_type: Type of system
        space_id: Space where source is located
        capacity: Capacity in system-specific units
        name: Human-readable name
        position: Optional 3D position
        equipment_id: Optional equipment reference
        is_critical: Whether this is a critical source

    Returns:
        Configured SystemNode
    """
    return SystemNode(
        node_id=generate_node_id(),
        node_type=NodeType.SOURCE,
        system_type=system_type,
        space_id=space_id,
        position=position,
        capacity_units=capacity,
        equipment_id=equipment_id,
        is_critical=is_critical,
        name=name,
    )


def create_consumer_node(
    system_type: SystemType,
    space_id: str,
    demand: float,
    name: str = "",
    position: Optional[Tuple[float, float, float]] = None,
    equipment_id: Optional[str] = None,
    is_critical: bool = False,
    requires_redundant_feed: bool = False,
) -> SystemNode:
    """
    Create a consumer node (equipment, outlet, fixture).

    Args:
        system_type: Type of system
        space_id: Space where consumer is located
        demand: Demand in system-specific units
        name: Human-readable name
        position: Optional 3D position
        equipment_id: Optional equipment reference
        is_critical: Whether this is a critical consumer
        requires_redundant_feed: Whether redundant supply is required

    Returns:
        Configured SystemNode
    """
    return SystemNode(
        node_id=generate_node_id(),
        node_type=NodeType.CONSUMER,
        system_type=system_type,
        space_id=space_id,
        position=position,
        demand_units=demand,
        equipment_id=equipment_id,
        is_critical=is_critical,
        requires_redundant_feed=requires_redundant_feed,
        name=name,
    )


def create_junction_node(
    system_type: SystemType,
    space_id: str,
    name: str = "",
    position: Optional[Tuple[float, float, float]] = None,
) -> SystemNode:
    """
    Create a junction node (manifold, panel, valve).

    Args:
        system_type: Type of system
        space_id: Space where junction is located
        name: Human-readable name
        position: Optional 3D position

    Returns:
        Configured SystemNode
    """
    return SystemNode(
        node_id=generate_node_id(),
        node_type=NodeType.JUNCTION,
        system_type=system_type,
        space_id=space_id,
        position=position,
        name=name,
    )
