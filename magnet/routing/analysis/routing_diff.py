"""
magnet/routing/analysis/routing_diff.py - Routing Diff Analysis

Compares two routing layouts/topologies to identify differences,
useful for debugging, version comparison, and change tracking.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum

from ..schema.system_type import SystemType
from ..schema.system_topology import SystemTopology
from ..schema.routing_layout import RoutingLayout
from ..schema.trunk_segment import TrunkSegment
from ..schema.system_node import SystemNode

__all__ = ['RoutingDiff', 'DiffType', 'DiffEntry', 'TopologyDiff']


class DiffType(Enum):
    """Type of difference detected."""
    ADDED = "added"           # Present in new, not in old
    REMOVED = "removed"       # Present in old, not in new
    MODIFIED = "modified"     # Present in both but different
    UNCHANGED = "unchanged"   # Identical in both


@dataclass
class DiffEntry:
    """A single difference entry."""
    diff_type: DiffType
    entity_type: str  # "node", "trunk", "topology", "layout"
    entity_id: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    changes: Dict[str, Tuple[Any, Any]] = field(default_factory=dict)

    def __repr__(self) -> str:
        if self.diff_type == DiffType.ADDED:
            return f"+ {self.entity_type}:{self.entity_id}"
        elif self.diff_type == DiffType.REMOVED:
            return f"- {self.entity_type}:{self.entity_id}"
        elif self.diff_type == DiffType.MODIFIED:
            changes_str = ", ".join(f"{k}: {v[0]} -> {v[1]}" for k, v in self.changes.items())
            return f"~ {self.entity_type}:{self.entity_id} ({changes_str})"
        return f"= {self.entity_type}:{self.entity_id}"


@dataclass
class TopologyDiff:
    """Diff result for a single system topology."""
    system_type: SystemType
    nodes_added: List[str] = field(default_factory=list)
    nodes_removed: List[str] = field(default_factory=list)
    nodes_modified: List[DiffEntry] = field(default_factory=list)
    trunks_added: List[str] = field(default_factory=list)
    trunks_removed: List[str] = field(default_factory=list)
    trunks_modified: List[DiffEntry] = field(default_factory=list)
    total_length_diff_m: float = 0.0
    zone_crossing_diff: int = 0

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return bool(
            self.nodes_added or self.nodes_removed or self.nodes_modified or
            self.trunks_added or self.trunks_removed or self.trunks_modified
        )

    @property
    def change_count(self) -> int:
        """Total number of changes."""
        return (
            len(self.nodes_added) + len(self.nodes_removed) + len(self.nodes_modified) +
            len(self.trunks_added) + len(self.trunks_removed) + len(self.trunks_modified)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'system_type': self.system_type.value,
            'nodes_added': self.nodes_added,
            'nodes_removed': self.nodes_removed,
            'nodes_modified': [
                {'id': e.entity_id, 'changes': e.changes}
                for e in self.nodes_modified
            ],
            'trunks_added': self.trunks_added,
            'trunks_removed': self.trunks_removed,
            'trunks_modified': [
                {'id': e.entity_id, 'changes': e.changes}
                for e in self.trunks_modified
            ],
            'total_length_diff_m': self.total_length_diff_m,
            'zone_crossing_diff': self.zone_crossing_diff,
            'has_changes': self.has_changes,
            'change_count': self.change_count,
        }


class RoutingDiff:
    """
    Compares routing layouts and topologies.

    Usage:
        diff = RoutingDiff()
        result = diff.compare_layouts(old_layout, new_layout)

        for system_type, topo_diff in result.items():
            if topo_diff.has_changes:
                print(f"{system_type}: {topo_diff.change_count} changes")
    """

    def __init__(
        self,
        ignore_timestamps: bool = True,
        ignore_metadata: bool = True,
        path_tolerance_m: float = 0.1,
    ):
        """
        Initialize routing diff analyzer.

        Args:
            ignore_timestamps: Whether to ignore timestamp differences
            ignore_metadata: Whether to ignore metadata differences
            path_tolerance_m: Tolerance for path length comparisons
        """
        self._ignore_timestamps = ignore_timestamps
        self._ignore_metadata = ignore_metadata
        self._path_tolerance = path_tolerance_m

    def compare_layouts(
        self,
        old_layout: RoutingLayout,
        new_layout: RoutingLayout,
    ) -> Dict[SystemType, TopologyDiff]:
        """
        Compare two routing layouts.

        Args:
            old_layout: Previous routing layout
            new_layout: Current routing layout

        Returns:
            Dictionary of SystemType -> TopologyDiff
        """
        result: Dict[SystemType, TopologyDiff] = {}

        # Get all system types from both layouts
        all_systems = set(old_layout.topologies.keys()) | set(new_layout.topologies.keys())

        for system_type in all_systems:
            old_topology = old_layout.topologies.get(system_type)
            new_topology = new_layout.topologies.get(system_type)

            if old_topology is None and new_topology is not None:
                # New topology added
                diff = TopologyDiff(system_type=system_type)
                diff.nodes_added = list(new_topology.nodes.keys())
                diff.trunks_added = list(new_topology.trunks.keys())
                diff.total_length_diff_m = new_topology.total_length_m
                result[system_type] = diff

            elif old_topology is not None and new_topology is None:
                # Topology removed
                diff = TopologyDiff(system_type=system_type)
                diff.nodes_removed = list(old_topology.nodes.keys())
                diff.trunks_removed = list(old_topology.trunks.keys())
                diff.total_length_diff_m = -old_topology.total_length_m
                result[system_type] = diff

            elif old_topology and new_topology:
                # Compare topologies
                result[system_type] = self.compare_topologies(
                    old_topology, new_topology
                )

        return result

    def compare_topologies(
        self,
        old_topology: SystemTopology,
        new_topology: SystemTopology,
    ) -> TopologyDiff:
        """
        Compare two system topologies.

        Args:
            old_topology: Previous topology
            new_topology: Current topology

        Returns:
            TopologyDiff with all differences
        """
        diff = TopologyDiff(system_type=new_topology.system_type)

        # Compare nodes
        old_nodes = set(old_topology.nodes.keys())
        new_nodes = set(new_topology.nodes.keys())

        diff.nodes_added = list(new_nodes - old_nodes)
        diff.nodes_removed = list(old_nodes - new_nodes)

        # Check modified nodes
        common_nodes = old_nodes & new_nodes
        for node_id in common_nodes:
            entry = self._compare_nodes(
                old_topology.nodes[node_id],
                new_topology.nodes[node_id],
            )
            if entry.diff_type == DiffType.MODIFIED:
                diff.nodes_modified.append(entry)

        # Compare trunks
        old_trunks = set(old_topology.trunks.keys())
        new_trunks = set(new_topology.trunks.keys())

        diff.trunks_added = list(new_trunks - old_trunks)
        diff.trunks_removed = list(old_trunks - new_trunks)

        # Check modified trunks
        common_trunks = old_trunks & new_trunks
        for trunk_id in common_trunks:
            entry = self._compare_trunks(
                old_topology.trunks[trunk_id],
                new_topology.trunks[trunk_id],
            )
            if entry.diff_type == DiffType.MODIFIED:
                diff.trunks_modified.append(entry)

        # Calculate aggregate differences
        diff.total_length_diff_m = new_topology.total_length_m - old_topology.total_length_m

        old_crossings = sum(len(t.zone_crossings) for t in old_topology.trunks.values())
        new_crossings = sum(len(t.zone_crossings) for t in new_topology.trunks.values())
        diff.zone_crossing_diff = new_crossings - old_crossings

        return diff

    def _compare_nodes(
        self,
        old_node: SystemNode,
        new_node: SystemNode,
    ) -> DiffEntry:
        """Compare two nodes for differences."""
        changes: Dict[str, Tuple[Any, Any]] = {}

        # Compare key attributes
        if old_node.space_id != new_node.space_id:
            changes['space_id'] = (old_node.space_id, new_node.space_id)

        if old_node.node_type != new_node.node_type:
            changes['node_type'] = (old_node.node_type.value, new_node.node_type.value)

        if old_node.capacity_units != new_node.capacity_units:
            changes['capacity_units'] = (old_node.capacity_units, new_node.capacity_units)

        if old_node.demand_units != new_node.demand_units:
            changes['demand_units'] = (old_node.demand_units, new_node.demand_units)

        if old_node.name != new_node.name:
            changes['name'] = (old_node.name, new_node.name)

        diff_type = DiffType.MODIFIED if changes else DiffType.UNCHANGED

        return DiffEntry(
            diff_type=diff_type,
            entity_type="node",
            entity_id=old_node.node_id,
            old_value=old_node,
            new_value=new_node,
            changes=changes,
        )

    def _compare_trunks(
        self,
        old_trunk: TrunkSegment,
        new_trunk: TrunkSegment,
    ) -> DiffEntry:
        """Compare two trunks for differences."""
        changes: Dict[str, Tuple[Any, Any]] = {}

        # Compare endpoints
        if old_trunk.from_node_id != new_trunk.from_node_id:
            changes['from_node_id'] = (old_trunk.from_node_id, new_trunk.from_node_id)

        if old_trunk.to_node_id != new_trunk.to_node_id:
            changes['to_node_id'] = (old_trunk.to_node_id, new_trunk.to_node_id)

        # Compare path
        if old_trunk.path_spaces != new_trunk.path_spaces:
            changes['path_spaces'] = (
                ','.join(old_trunk.path_spaces),
                ','.join(new_trunk.path_spaces),
            )

        # Compare length with tolerance
        if abs(old_trunk.length_m - new_trunk.length_m) > self._path_tolerance:
            changes['length_m'] = (
                round(old_trunk.length_m, 2),
                round(new_trunk.length_m, 2),
            )

        # Compare zone compliance
        if old_trunk.is_zone_compliant != new_trunk.is_zone_compliant:
            changes['is_zone_compliant'] = (
                old_trunk.is_zone_compliant,
                new_trunk.is_zone_compliant,
            )

        # Compare zone crossings
        if set(old_trunk.zone_crossings) != set(new_trunk.zone_crossings):
            changes['zone_crossings'] = (
                ','.join(sorted(old_trunk.zone_crossings)),
                ','.join(sorted(new_trunk.zone_crossings)),
            )

        # Compare sizing
        if old_trunk.size.nominal_size != new_trunk.size.nominal_size:
            changes['nominal_size'] = (
                old_trunk.size.nominal_size,
                new_trunk.size.nominal_size,
            )

        diff_type = DiffType.MODIFIED if changes else DiffType.UNCHANGED

        return DiffEntry(
            diff_type=diff_type,
            entity_type="trunk",
            entity_id=old_trunk.trunk_id,
            old_value=old_trunk,
            new_value=new_trunk,
            changes=changes,
        )

    def summarize(
        self,
        diff_result: Dict[SystemType, TopologyDiff],
    ) -> Dict[str, Any]:
        """
        Generate summary of diff result.

        Args:
            diff_result: Result from compare_layouts()

        Returns:
            Summary dictionary
        """
        total_changes = 0
        systems_changed = []
        systems_added = []
        systems_removed = []

        for system_type, topo_diff in diff_result.items():
            if topo_diff.has_changes:
                total_changes += topo_diff.change_count
                if topo_diff.nodes_removed and not topo_diff.nodes_added:
                    # All nodes removed = system removed
                    if len(topo_diff.nodes_removed) == topo_diff.change_count:
                        systems_removed.append(system_type.value)
                        continue
                if topo_diff.nodes_added and not topo_diff.nodes_removed:
                    # All nodes added = new system
                    if len(topo_diff.nodes_added) == topo_diff.change_count:
                        systems_added.append(system_type.value)
                        continue
                systems_changed.append(system_type.value)

        return {
            'total_changes': total_changes,
            'systems_changed': systems_changed,
            'systems_added': systems_added,
            'systems_removed': systems_removed,
            'has_changes': total_changes > 0,
            'details': {
                st.value: td.to_dict()
                for st, td in diff_result.items()
                if td.has_changes
            },
        }

    def format_report(
        self,
        diff_result: Dict[SystemType, TopologyDiff],
        verbose: bool = False,
    ) -> str:
        """
        Format diff result as human-readable report.

        Args:
            diff_result: Result from compare_layouts()
            verbose: Include detailed change information

        Returns:
            Formatted report string
        """
        lines = ["Routing Diff Report", "=" * 40]

        summary = self.summarize(diff_result)

        if not summary['has_changes']:
            lines.append("No changes detected.")
            return "\n".join(lines)

        lines.append(f"Total changes: {summary['total_changes']}")

        if summary['systems_added']:
            lines.append(f"Systems added: {', '.join(summary['systems_added'])}")
        if summary['systems_removed']:
            lines.append(f"Systems removed: {', '.join(summary['systems_removed'])}")
        if summary['systems_changed']:
            lines.append(f"Systems modified: {', '.join(summary['systems_changed'])}")

        lines.append("")

        for system_type, topo_diff in diff_result.items():
            if not topo_diff.has_changes:
                continue

            lines.append(f"\n{system_type.value}:")
            lines.append("-" * 30)

            if topo_diff.nodes_added:
                lines.append(f"  Nodes added: {len(topo_diff.nodes_added)}")
                if verbose:
                    for node_id in topo_diff.nodes_added[:5]:
                        lines.append(f"    + {node_id}")
                    if len(topo_diff.nodes_added) > 5:
                        lines.append(f"    ... and {len(topo_diff.nodes_added) - 5} more")

            if topo_diff.nodes_removed:
                lines.append(f"  Nodes removed: {len(topo_diff.nodes_removed)}")
                if verbose:
                    for node_id in topo_diff.nodes_removed[:5]:
                        lines.append(f"    - {node_id}")

            if topo_diff.nodes_modified:
                lines.append(f"  Nodes modified: {len(topo_diff.nodes_modified)}")
                if verbose:
                    for entry in topo_diff.nodes_modified[:5]:
                        lines.append(f"    ~ {entry}")

            if topo_diff.trunks_added:
                lines.append(f"  Trunks added: {len(topo_diff.trunks_added)}")

            if topo_diff.trunks_removed:
                lines.append(f"  Trunks removed: {len(topo_diff.trunks_removed)}")

            if topo_diff.trunks_modified:
                lines.append(f"  Trunks modified: {len(topo_diff.trunks_modified)}")
                if verbose:
                    for entry in topo_diff.trunks_modified[:5]:
                        lines.append(f"    ~ {entry}")

            if abs(topo_diff.total_length_diff_m) > 0.1:
                sign = "+" if topo_diff.total_length_diff_m > 0 else ""
                lines.append(f"  Length change: {sign}{topo_diff.total_length_diff_m:.1f}m")

            if topo_diff.zone_crossing_diff != 0:
                sign = "+" if topo_diff.zone_crossing_diff > 0 else ""
                lines.append(f"  Zone crossings: {sign}{topo_diff.zone_crossing_diff}")

        return "\n".join(lines)
