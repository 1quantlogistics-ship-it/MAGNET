"""
magnet/routing/schema/routing_layout.py - Routing Layout Aggregate

RoutingLayout aggregates all system topologies for a vessel,
providing a complete view of all routed systems.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import Enum

from .system_type import SystemType
from .system_topology import SystemTopology, TopologyStatus

__all__ = ['RoutingLayout', 'LayoutStatus']


class LayoutStatus(Enum):
    """Overall status of the routing layout."""
    EMPTY = "empty"           # No systems routed
    PARTIAL = "partial"       # Some systems routed
    COMPLETE = "complete"     # All systems routed
    VALIDATED = "validated"   # All systems validated
    FAILED = "failed"         # One or more systems failed


@dataclass
class RoutingLayout:
    """
    Complete routing layout for all vessel systems.

    Aggregates SystemTopology instances for each routed system type,
    providing cross-system statistics and validation.

    Attributes:
        design_id: Reference to the design this routing belongs to
        topologies: Dictionary of SystemType -> SystemTopology

        status: Overall routing status
        routed_systems: Set of successfully routed system types
        failed_systems: Set of failed system types

        total_trunk_length_m: Total length of all trunks
        zone_crossing_count: Total zone crossings across all systems

        created_at: Creation timestamp
        modified_at: Last modification timestamp
        version: Layout version number
        metadata: Extension point
    """

    # Identity
    design_id: str = ""

    # System topologies
    topologies: Dict[SystemType, SystemTopology] = field(default_factory=dict)

    # Status tracking
    status: LayoutStatus = LayoutStatus.EMPTY
    routed_systems: Set[SystemType] = field(default_factory=set)
    failed_systems: Set[SystemType] = field(default_factory=set)

    # Aggregates
    total_trunk_length_m: float = 0.0
    zone_crossing_count: int = 0

    # Versioning
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    version: int = 1

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize timestamps."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        self.modified_at = datetime.utcnow()

    # =========================================================================
    # Topology Management
    # =========================================================================

    def add_topology(self, topology: SystemTopology) -> None:
        """
        Add or replace a system topology.

        Args:
            topology: SystemTopology to add
        """
        self.topologies[topology.system_type] = topology

        # Update tracking sets
        if topology.status in (TopologyStatus.ROUTED, TopologyStatus.VALIDATED):
            self.routed_systems.add(topology.system_type)
            self.failed_systems.discard(topology.system_type)
        elif topology.status == TopologyStatus.FAILED:
            self.failed_systems.add(topology.system_type)
            self.routed_systems.discard(topology.system_type)

        self._update_status()
        self._update_aggregates()
        self.modified_at = datetime.utcnow()

    def remove_topology(self, system_type: SystemType) -> Optional[SystemTopology]:
        """
        Remove a system topology.

        Args:
            system_type: System type to remove

        Returns:
            Removed topology, or None if not found
        """
        topology = self.topologies.pop(system_type, None)

        if topology:
            self.routed_systems.discard(system_type)
            self.failed_systems.discard(system_type)
            self._update_status()
            self._update_aggregates()
            self.modified_at = datetime.utcnow()

        return topology

    def get_topology(self, system_type: SystemType) -> Optional[SystemTopology]:
        """Get topology for a system type."""
        return self.topologies.get(system_type)

    def has_topology(self, system_type: SystemType) -> bool:
        """Check if topology exists for a system type."""
        return system_type in self.topologies

    # =========================================================================
    # Status & Validation
    # =========================================================================

    def _update_status(self) -> None:
        """Update overall layout status."""
        if not self.topologies:
            self.status = LayoutStatus.EMPTY
        elif self.failed_systems:
            self.status = LayoutStatus.FAILED
        elif not self.routed_systems:
            self.status = LayoutStatus.PARTIAL
        elif all(
            t.status == TopologyStatus.VALIDATED
            for t in self.topologies.values()
        ):
            self.status = LayoutStatus.VALIDATED
        elif all(
            t.status in (TopologyStatus.ROUTED, TopologyStatus.VALIDATED)
            for t in self.topologies.values()
        ):
            self.status = LayoutStatus.COMPLETE
        else:
            self.status = LayoutStatus.PARTIAL

    def _update_aggregates(self) -> None:
        """Update aggregate values."""
        self.total_trunk_length_m = sum(
            t.total_length_m for t in self.topologies.values()
        )
        self.zone_crossing_count = sum(
            sum(len(trunk.zone_crossings) for trunk in t.trunks.values())
            for t in self.topologies.values()
        )

    def validate_all(self) -> bool:
        """
        Validate all topologies.

        Returns:
            True if all topologies are valid
        """
        all_valid = True

        for topology in self.topologies.values():
            if not topology.validate():
                all_valid = False
                self.failed_systems.add(topology.system_type)
                self.routed_systems.discard(topology.system_type)
            else:
                self.routed_systems.add(topology.system_type)
                self.failed_systems.discard(topology.system_type)

        self._update_status()
        return all_valid

    def get_validation_errors(self) -> Dict[SystemType, List[str]]:
        """Get all validation errors by system type."""
        return {
            st: t.validation_errors
            for st, t in self.topologies.items()
            if t.validation_errors
        }

    def get_validation_warnings(self) -> Dict[SystemType, List[str]]:
        """Get all validation warnings by system type."""
        return {
            st: t.validation_warnings
            for st, t in self.topologies.items()
            if t.validation_warnings
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    @property
    def system_count(self) -> int:
        """Number of system topologies."""
        return len(self.topologies)

    @property
    def total_node_count(self) -> int:
        """Total nodes across all systems."""
        return sum(t.node_count for t in self.topologies.values())

    @property
    def total_trunk_count(self) -> int:
        """Total trunks across all systems."""
        return sum(t.trunk_count for t in self.topologies.values())

    def get_statistics(self) -> Dict[str, Any]:
        """Get layout statistics."""
        return {
            'design_id': self.design_id,
            'status': self.status.value,
            'system_count': self.system_count,
            'routed_systems': [s.value for s in self.routed_systems],
            'failed_systems': [s.value for s in self.failed_systems],
            'total_node_count': self.total_node_count,
            'total_trunk_count': self.total_trunk_count,
            'total_trunk_length_m': self.total_trunk_length_m,
            'zone_crossing_count': self.zone_crossing_count,
            'version': self.version,
            'systems': {
                st.value: t.get_statistics()
                for st, t in self.topologies.items()
            },
        }

    def get_systems_by_status(
        self,
        status: TopologyStatus,
    ) -> List[SystemType]:
        """Get system types with a specific status."""
        return [
            st for st, t in self.topologies.items()
            if t.status == status
        ]

    # =========================================================================
    # Cross-System Analysis
    # =========================================================================

    def get_spaces_with_systems(self) -> Dict[str, List[SystemType]]:
        """
        Get mapping of spaces to systems that route through them.

        Returns:
            Dictionary of space_id -> list of SystemType
        """
        space_systems: Dict[str, List[SystemType]] = {}

        for system_type, topology in self.topologies.items():
            # Check nodes
            for node in topology.nodes.values():
                if node.space_id not in space_systems:
                    space_systems[node.space_id] = []
                if system_type not in space_systems[node.space_id]:
                    space_systems[node.space_id].append(system_type)

            # Check trunk paths
            for trunk in topology.trunks.values():
                for space_id in trunk.path_spaces:
                    if space_id not in space_systems:
                        space_systems[space_id] = []
                    if system_type not in space_systems[space_id]:
                        space_systems[space_id].append(system_type)

        return space_systems

    def get_system_density_by_space(self) -> Dict[str, int]:
        """
        Get system count per space.

        Returns:
            Dictionary of space_id -> number of systems
        """
        space_systems = self.get_spaces_with_systems()
        return {
            space_id: len(systems)
            for space_id, systems in space_systems.items()
        }

    def get_high_density_spaces(self, threshold: int = 3) -> List[str]:
        """
        Get spaces with high system density.

        Args:
            threshold: Minimum number of systems to be considered high density

        Returns:
            List of space IDs with system count >= threshold
        """
        density = self.get_system_density_by_space()
        return [
            space_id for space_id, count in density.items()
            if count >= threshold
        ]

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'design_id': self.design_id,
            'topologies': {
                st.value: t.to_dict()
                for st, t in self.topologies.items()
            },
            'status': self.status.value,
            'routed_systems': [s.value for s in self.routed_systems],
            'failed_systems': [s.value for s in self.failed_systems],
            'total_trunk_length_m': self.total_trunk_length_m,
            'zone_crossing_count': self.zone_crossing_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'modified_at': self.modified_at.isoformat() if self.modified_at else None,
            'version': self.version,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RoutingLayout':
        """Deserialize from dictionary."""
        layout = cls(
            design_id=data.get('design_id', ''),
            status=LayoutStatus(data.get('status', 'empty')),
            routed_systems={SystemType(s) for s in data.get('routed_systems', [])},
            failed_systems={SystemType(s) for s in data.get('failed_systems', [])},
            total_trunk_length_m=data.get('total_trunk_length_m', 0.0),
            zone_crossing_count=data.get('zone_crossing_count', 0),
            version=data.get('version', 1),
            metadata=data.get('metadata', {}),
        )

        # Restore timestamps
        if data.get('created_at'):
            layout.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('modified_at'):
            layout.modified_at = datetime.fromisoformat(data['modified_at'])

        # Restore topologies
        for st_value, topo_data in data.get('topologies', {}).items():
            topology = SystemTopology.from_dict(topo_data)
            layout.topologies[SystemType(st_value)] = topology

        return layout

    # =========================================================================
    # String Representation
    # =========================================================================

    def __repr__(self) -> str:
        return (
            f"RoutingLayout(design={self.design_id!r}, "
            f"systems={self.system_count}, status={self.status.value})"
        )

    def __str__(self) -> str:
        systems_str = ", ".join(
            st.value for st in sorted(self.routed_systems, key=lambda x: x.value)
        )
        return (
            f"RoutingLayout [{self.design_id}]: "
            f"{self.system_count} systems, "
            f"{self.total_trunk_count} trunks, "
            f"{self.total_trunk_length_m:.1f}m total"
        )
