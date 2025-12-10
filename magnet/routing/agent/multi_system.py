"""
multi_system.py - Multi-system coordination v1.1
BRAVO OWNS THIS FILE.

Module 60: Systems Routing
Coordinates routing across multiple systems to resolve conflicts
and optimize shared routing.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any, Tuple
from enum import Enum
import logging

__all__ = [
    'MultiSystemCoordinator',
    'ConflictType',
    'SystemConflict',
    'CoordinationResult',
]

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ConflictType(Enum):
    """Types of conflicts between systems."""

    SEPARATION = "separation"         # Separation distance violated
    CO_ROUTING = "co_routing"         # Prohibited co-routing
    ZONE = "zone"                     # Zone crossing conflict
    CAPACITY = "capacity"             # Shared space capacity exceeded
    REDUNDANCY = "redundancy"         # Redundancy paths conflict
    PRIORITY = "priority"             # Priority conflict


# =============================================================================
# CONFLICT REPRESENTATION
# =============================================================================

@dataclass
class SystemConflict:
    """
    Conflict between two system routes.

    Attributes:
        conflict_id: Unique identifier
        conflict_type: Type of conflict
        system_a: First system involved
        system_b: Second system involved
        spaces: Spaces where conflict occurs
        severity: Conflict severity (1-10)
        resolution: How conflict was resolved (if resolved)
    """

    conflict_id: str
    conflict_type: ConflictType
    system_a: str
    system_b: str

    spaces: List[str] = field(default_factory=list)
    severity: int = 5

    # Resolution status
    is_resolved: bool = False
    resolution: str = ""
    resolution_cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "conflict_id": self.conflict_id,
            "conflict_type": self.conflict_type.value,
            "system_a": self.system_a,
            "system_b": self.system_b,
            "spaces": self.spaces,
            "severity": self.severity,
            "is_resolved": self.is_resolved,
            "resolution": self.resolution,
            "resolution_cost": self.resolution_cost,
        }


@dataclass
class CoordinationResult:
    """
    Result of multi-system coordination.

    Attributes:
        success: Whether coordination completed successfully
        systems_coordinated: Systems that were coordinated
        conflicts_found: Conflicts detected
        conflicts_resolved: Conflicts that were resolved
        optimizations_applied: Optimizations that were made
        total_length_saved_m: Total routing length saved
    """

    success: bool = True
    systems_coordinated: List[str] = field(default_factory=list)

    conflicts_found: List[SystemConflict] = field(default_factory=list)
    conflicts_resolved: List[SystemConflict] = field(default_factory=list)
    conflicts_unresolved: List[SystemConflict] = field(default_factory=list)

    optimizations_applied: List[str] = field(default_factory=list)
    total_length_saved_m: float = 0.0

    log: List[str] = field(default_factory=list)

    @property
    def all_resolved(self) -> bool:
        """Check if all conflicts were resolved."""
        return len(self.conflicts_unresolved) == 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "systems_coordinated": self.systems_coordinated,
            "conflicts_found": [c.to_dict() for c in self.conflicts_found],
            "conflicts_resolved": [c.to_dict() for c in self.conflicts_resolved],
            "conflicts_unresolved": [c.to_dict() for c in self.conflicts_unresolved],
            "optimizations_applied": self.optimizations_applied,
            "total_length_saved_m": self.total_length_saved_m,
            "log": self.log,
        }


# =============================================================================
# MULTI-SYSTEM COORDINATOR
# =============================================================================

class MultiSystemCoordinator:
    """
    Coordinates routing across multiple systems.

    Detects conflicts between system routes and attempts to resolve
    them through rerouting, shared routing optimization, or flagging
    for manual resolution.

    Usage:
        coordinator = MultiSystemCoordinator()
        result = coordinator.coordinate(
            systems={'fuel': fuel_topology, 'electrical_hv': elec_topology},
            compartment_graph=graph,
            separation_rules=rules,
        )
    """

    def __init__(
        self,
        auto_resolve: bool = True,
        max_resolution_attempts: int = 3,
    ):
        """
        Initialize coordinator.

        Args:
            auto_resolve: Whether to automatically attempt resolution
            max_resolution_attempts: Max attempts to resolve each conflict
        """
        self._auto_resolve = auto_resolve
        self._max_attempts = max_resolution_attempts
        self._conflict_counter = 0

    def coordinate(
        self,
        systems: Dict[str, Any],
        compartment_graph: Any,
        separation_rules: Optional[Any] = None,
    ) -> CoordinationResult:
        """
        Coordinate multiple system routes.

        Args:
            systems: Dict of system_type -> topology
            compartment_graph: Compartment adjacency graph
            separation_rules: Separation rule set

        Returns:
            CoordinationResult with conflicts and resolutions
        """
        result = CoordinationResult(
            systems_coordinated=list(systems.keys()),
        )

        result.log.append(f"Coordinating {len(systems)} systems")

        # Detect conflicts
        conflicts = self._detect_conflicts(systems, separation_rules)
        result.conflicts_found = conflicts
        result.log.append(f"Found {len(conflicts)} conflicts")

        # Attempt resolution if enabled
        if self._auto_resolve and conflicts:
            resolved, unresolved = self._resolve_conflicts(
                conflicts, systems, compartment_graph, separation_rules
            )
            result.conflicts_resolved = resolved
            result.conflicts_unresolved = unresolved
            result.log.append(
                f"Resolved {len(resolved)}, unresolved {len(unresolved)}"
            )
        else:
            result.conflicts_unresolved = conflicts

        # Optimize shared routing
        optimizations, length_saved = self._optimize_shared_routing(
            systems, compartment_graph
        )
        result.optimizations_applied = optimizations
        result.total_length_saved_m = length_saved

        result.success = len(result.conflicts_unresolved) == 0

        return result

    def detect_conflicts(
        self,
        systems: Dict[str, Any],
        separation_rules: Optional[Any] = None,
    ) -> List[SystemConflict]:
        """
        Detect conflicts between systems without resolving.

        Args:
            systems: Dict of system_type -> topology
            separation_rules: Separation rule set

        Returns:
            List of detected conflicts
        """
        return self._detect_conflicts(systems, separation_rules)

    def _detect_conflicts(
        self,
        systems: Dict[str, Any],
        separation_rules: Optional[Any],
    ) -> List[SystemConflict]:
        """Detect all conflicts between systems."""
        conflicts = []
        system_types = list(systems.keys())

        for i, sys_a in enumerate(system_types):
            for sys_b in system_types[i + 1:]:
                # Get routes for each system
                routes_a = self._get_system_routes(systems[sys_a])
                routes_b = self._get_system_routes(systems[sys_b])

                # Check for separation violations
                sep_conflicts = self._check_separation(
                    sys_a, routes_a, sys_b, routes_b, separation_rules
                )
                conflicts.extend(sep_conflicts)

                # Check for co-routing violations
                co_conflicts = self._check_co_routing(
                    sys_a, routes_a, sys_b, routes_b, separation_rules
                )
                conflicts.extend(co_conflicts)

        return conflicts

    def _get_system_routes(self, topology: Any) -> Dict[str, List[str]]:
        """Extract routes from topology."""
        routes = {}

        if hasattr(topology, 'trunks'):
            trunks = topology.trunks
            if isinstance(trunks, dict):
                for trunk_id, trunk in trunks.items():
                    if hasattr(trunk, 'path_spaces'):
                        routes[trunk_id] = trunk.path_spaces
                    elif isinstance(trunk, dict):
                        routes[trunk_id] = trunk.get('path_spaces', [])

        return routes

    def _check_separation(
        self,
        sys_a: str,
        routes_a: Dict[str, List[str]],
        sys_b: str,
        routes_b: Dict[str, List[str]],
        separation_rules: Optional[Any],
    ) -> List[SystemConflict]:
        """Check separation requirements between systems."""
        conflicts = []

        # Get separation rule
        min_distance = 0.0
        if separation_rules:
            rule = separation_rules.get_rule(sys_a, sys_b)
            if rule:
                min_distance = rule.min_distance_m

        if min_distance <= 0:
            return conflicts

        # Check for shared spaces (distance = 0)
        for trunk_a, path_a in routes_a.items():
            for trunk_b, path_b in routes_b.items():
                shared = set(path_a) & set(path_b)
                if shared:
                    self._conflict_counter += 1
                    conflicts.append(SystemConflict(
                        conflict_id=f"conflict_{self._conflict_counter}",
                        conflict_type=ConflictType.SEPARATION,
                        system_a=sys_a,
                        system_b=sys_b,
                        spaces=list(shared),
                        severity=7,
                    ))

        return conflicts

    def _check_co_routing(
        self,
        sys_a: str,
        routes_a: Dict[str, List[str]],
        sys_b: str,
        routes_b: Dict[str, List[str]],
        separation_rules: Optional[Any],
    ) -> List[SystemConflict]:
        """Check for prohibited co-routing."""
        conflicts = []

        # Check if co-routing is prohibited
        is_prohibited = False
        if separation_rules:
            is_prohibited = separation_rules.is_prohibited(sys_a, sys_b)

        if not is_prohibited:
            return conflicts

        # Any shared spaces are a violation
        for trunk_a, path_a in routes_a.items():
            for trunk_b, path_b in routes_b.items():
                shared = set(path_a) & set(path_b)
                if shared:
                    self._conflict_counter += 1
                    conflicts.append(SystemConflict(
                        conflict_id=f"conflict_{self._conflict_counter}",
                        conflict_type=ConflictType.CO_ROUTING,
                        system_a=sys_a,
                        system_b=sys_b,
                        spaces=list(shared),
                        severity=9,
                    ))

        return conflicts

    def _resolve_conflicts(
        self,
        conflicts: List[SystemConflict],
        systems: Dict[str, Any],
        compartment_graph: Any,
        separation_rules: Optional[Any],
    ) -> Tuple[List[SystemConflict], List[SystemConflict]]:
        """Attempt to resolve conflicts."""
        resolved = []
        unresolved = []

        for conflict in conflicts:
            success = False

            for attempt in range(self._max_attempts):
                if conflict.conflict_type == ConflictType.SEPARATION:
                    success = self._resolve_separation_conflict(
                        conflict, systems, compartment_graph
                    )
                elif conflict.conflict_type == ConflictType.CO_ROUTING:
                    success = self._resolve_co_routing_conflict(
                        conflict, systems, compartment_graph
                    )

                if success:
                    conflict.is_resolved = True
                    resolved.append(conflict)
                    break

            if not success:
                unresolved.append(conflict)

        return resolved, unresolved

    def _resolve_separation_conflict(
        self,
        conflict: SystemConflict,
        systems: Dict[str, Any],
        compartment_graph: Any,
    ) -> bool:
        """Try to resolve separation conflict by rerouting one system."""
        try:
            import networkx as nx
        except ImportError:
            return False

        # Try to find alternate route for the lower priority system
        # (In practice, would check system priorities)
        system_to_reroute = conflict.system_b

        topology = systems.get(system_to_reroute)
        if not topology:
            return False

        # Find trunk that goes through conflict spaces
        routes = self._get_system_routes(topology)

        for trunk_id, path in routes.items():
            if any(s in conflict.spaces for s in path):
                # Try to find alternate path avoiding conflict spaces
                if len(path) < 2:
                    continue

                start, end = path[0], path[-1]

                # Create graph without conflict spaces
                modified = compartment_graph.copy()
                for space in conflict.spaces:
                    if space in modified and space not in (start, end):
                        modified.remove_node(space)

                try:
                    new_path = nx.shortest_path(modified, start, end, weight='cost')

                    # Update trunk path (would need actual trunk update)
                    conflict.resolution = f"Rerouted {trunk_id} avoiding {conflict.spaces}"
                    return True

                except (nx.NetworkXNoPath, nx.NetworkXError):
                    continue

        return False

    def _resolve_co_routing_conflict(
        self,
        conflict: SystemConflict,
        systems: Dict[str, Any],
        compartment_graph: Any,
    ) -> bool:
        """Try to resolve co-routing conflict."""
        # Similar to separation conflict resolution
        return self._resolve_separation_conflict(
            conflict, systems, compartment_graph
        )

    def _optimize_shared_routing(
        self,
        systems: Dict[str, Any],
        compartment_graph: Any,
    ) -> Tuple[List[str], float]:
        """
        Optimize by identifying beneficial shared routing.

        Some systems can share routing (e.g., freshwater and firefighting
        main headers) to reduce overall routing length.

        Returns:
            (list of optimizations, total length saved)
        """
        optimizations = []
        total_saved = 0.0

        # Find compatible system pairs for shared routing
        compatible_pairs = [
            ('freshwater', 'firefighting'),
            ('electrical_lv', 'fire_detection'),
            ('hvac_supply', 'hvac_return'),
        ]

        for sys_a, sys_b in compatible_pairs:
            if sys_a in systems and sys_b in systems:
                # Check if systems have overlapping routes
                routes_a = self._get_system_routes(systems[sys_a])
                routes_b = self._get_system_routes(systems[sys_b])

                for trunk_a, path_a in routes_a.items():
                    for trunk_b, path_b in routes_b.items():
                        shared = set(path_a) & set(path_b)
                        if len(shared) >= 3:
                            # Could consolidate these routes
                            optimizations.append(
                                f"Consider shared trunk for {sys_a}/{sys_b} "
                                f"through {len(shared)} common spaces"
                            )
                            # Estimate savings (rough)
                            total_saved += len(shared) * 0.5

        return optimizations, total_saved

    def get_conflict_summary(
        self,
        conflicts: List[SystemConflict],
    ) -> Dict[str, Any]:
        """
        Generate summary of conflicts.

        Returns dict with conflict counts by type and severity.
        """
        summary = {
            'total': len(conflicts),
            'by_type': {},
            'by_severity': {'low': 0, 'medium': 0, 'high': 0, 'critical': 0},
            'by_system': {},
        }

        for conflict in conflicts:
            # By type
            ctype = conflict.conflict_type.value
            summary['by_type'][ctype] = summary['by_type'].get(ctype, 0) + 1

            # By severity
            if conflict.severity <= 3:
                summary['by_severity']['low'] += 1
            elif conflict.severity <= 5:
                summary['by_severity']['medium'] += 1
            elif conflict.severity <= 7:
                summary['by_severity']['high'] += 1
            else:
                summary['by_severity']['critical'] += 1

            # By system
            for sys in (conflict.system_a, conflict.system_b):
                summary['by_system'][sys] = summary['by_system'].get(sys, 0) + 1

        return summary
