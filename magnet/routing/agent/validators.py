"""
validators.py - Routing validation rules v1.1
BRAVO OWNS THIS FILE.

Module 60: Systems Routing
Comprehensive validation for system routing.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any, Tuple
from enum import Enum
import logging

__all__ = [
    'RoutingValidator',
    'ValidationSeverity',
    'ValidationViolation',
    'ValidationResult',
]

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ValidationSeverity(Enum):
    """Severity levels for validation violations."""

    INFO = "info"                     # Informational only
    WARNING = "warning"               # Should be addressed
    ERROR = "error"                   # Must be fixed
    CRITICAL = "critical"             # Blocks routing completion


# =============================================================================
# VALIDATION TYPES
# =============================================================================

@dataclass
class ValidationViolation:
    """
    A single validation violation.

    Attributes:
        violation_id: Unique identifier
        rule_name: Name of violated rule
        severity: Violation severity
        message: Human-readable description
        system_type: System involved (if applicable)
        trunk_id: Trunk involved (if applicable)
        spaces: Spaces involved
        recommendation: Suggested fix
    """

    violation_id: str
    rule_name: str
    severity: ValidationSeverity
    message: str

    system_type: Optional[str] = None
    trunk_id: Optional[str] = None
    spaces: List[str] = field(default_factory=list)

    recommendation: str = ""
    regulation_ref: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "violation_id": self.violation_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "system_type": self.system_type,
            "trunk_id": self.trunk_id,
            "spaces": self.spaces,
            "recommendation": self.recommendation,
            "regulation_ref": self.regulation_ref,
        }


@dataclass
class ValidationResult:
    """
    Result of routing validation.

    Attributes:
        is_valid: Whether routing passes all required checks
        violations: List of violations found
        warnings_count: Number of warnings
        errors_count: Number of errors
        critical_count: Number of critical issues
    """

    is_valid: bool = True
    violations: List[ValidationViolation] = field(default_factory=list)

    # Counts by severity
    info_count: int = 0
    warnings_count: int = 0
    errors_count: int = 0
    critical_count: int = 0

    # Systems validated
    systems_validated: List[str] = field(default_factory=list)
    total_trunks_checked: int = 0

    def add_violation(self, violation: ValidationViolation) -> None:
        """Add a violation and update counts."""
        self.violations.append(violation)

        if violation.severity == ValidationSeverity.INFO:
            self.info_count += 1
        elif violation.severity == ValidationSeverity.WARNING:
            self.warnings_count += 1
        elif violation.severity == ValidationSeverity.ERROR:
            self.errors_count += 1
            self.is_valid = False
        elif violation.severity == ValidationSeverity.CRITICAL:
            self.critical_count += 1
            self.is_valid = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "is_valid": self.is_valid,
            "violations": [v.to_dict() for v in self.violations],
            "info_count": self.info_count,
            "warnings_count": self.warnings_count,
            "errors_count": self.errors_count,
            "critical_count": self.critical_count,
            "systems_validated": self.systems_validated,
            "total_trunks_checked": self.total_trunks_checked,
        }


# =============================================================================
# ROUTING VALIDATOR
# =============================================================================

class RoutingValidator:
    """
    Validates system routing for compliance.

    Checks:
    - Connectivity: All nodes reachable
    - Zone compliance: Zone crossing rules respected
    - Separation: System separation requirements met
    - Redundancy: Critical systems have backup paths
    - Capacity: Trunk sizing adequate

    Usage:
        validator = RoutingValidator()
        result = validator.validate(routing_layout, compartment_graph)
    """

    def __init__(self):
        """Initialize validator."""
        self._violation_counter = 0

    def validate(
        self,
        routing_layout: Any,
        compartment_graph: Optional[Any] = None,
        separation_rules: Optional[Any] = None,
        zone_definitions: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        Validate complete routing layout.

        Args:
            routing_layout: RoutingLayout to validate
            compartment_graph: Compartment adjacency graph
            separation_rules: System separation rules
            zone_definitions: Zone definitions for compliance

        Returns:
            ValidationResult with all violations
        """
        result = ValidationResult()

        # Get topologies from layout
        if hasattr(routing_layout, 'topologies'):
            topologies = routing_layout.topologies
        elif isinstance(routing_layout, dict):
            topologies = routing_layout.get('topologies', {})
        else:
            topologies = {}

        # Validate each system
        for system_type, topology in topologies.items():
            result.systems_validated.append(str(system_type))

            # Connectivity validation
            conn_violations = self.validate_connectivity(
                topology, system_type, compartment_graph
            )
            for v in conn_violations:
                result.add_violation(v)

            # Zone compliance validation
            if zone_definitions:
                zone_violations = self.validate_zone_compliance(
                    topology, system_type, zone_definitions
                )
                for v in zone_violations:
                    result.add_violation(v)

            # Count trunks
            if hasattr(topology, 'trunks'):
                result.total_trunks_checked += len(topology.trunks)

        # Cross-system validation
        if separation_rules and len(topologies) > 1:
            sep_violations = self.validate_separation(
                topologies, separation_rules
            )
            for v in sep_violations:
                result.add_violation(v)

        # Redundancy validation
        redundancy_violations = self.validate_redundancy(
            topologies, compartment_graph
        )
        for v in redundancy_violations:
            result.add_violation(v)

        # Capacity validation
        capacity_violations = self.validate_capacity(topologies)
        for v in capacity_violations:
            result.add_violation(v)

        return result

    def validate_connectivity(
        self,
        topology: Any,
        system_type: str,
        compartment_graph: Optional[Any] = None,
    ) -> List[ValidationViolation]:
        """
        Validate that all nodes are connected.

        Args:
            topology: System topology
            system_type: Type of system
            compartment_graph: Graph for path verification

        Returns:
            List of connectivity violations
        """
        violations = []

        # Get nodes and trunks
        nodes = self._get_topology_nodes(topology)
        trunks = self._get_topology_trunks(topology)

        if not nodes:
            return violations

        # Build connectivity set from trunks
        connected_nodes: Set[str] = set()
        for trunk in trunks.values():
            from_node = self._get_trunk_from_node(trunk)
            to_node = self._get_trunk_to_node(trunk)
            if from_node:
                connected_nodes.add(from_node)
            if to_node:
                connected_nodes.add(to_node)

        # Check each node
        for node_id, node in nodes.items():
            if node_id not in connected_nodes:
                # Check if this is a source with no downstream or consumer with no upstream
                node_type = self._get_node_type(node)

                self._violation_counter += 1
                violations.append(ValidationViolation(
                    violation_id=f"v_{self._violation_counter}",
                    rule_name="connectivity",
                    severity=ValidationSeverity.ERROR,
                    message=f"Node {node_id} ({node_type}) is not connected to routing",
                    system_type=system_type,
                    recommendation="Add trunk connection to this node",
                ))

        # Verify trunk paths exist in graph
        if compartment_graph:
            for trunk_id, trunk in trunks.items():
                path = self._get_trunk_path(trunk)
                if len(path) >= 2:
                    for i in range(len(path) - 1):
                        if not compartment_graph.has_edge(path[i], path[i + 1]):
                            self._violation_counter += 1
                            violations.append(ValidationViolation(
                                violation_id=f"v_{self._violation_counter}",
                                rule_name="path_connectivity",
                                severity=ValidationSeverity.ERROR,
                                message=f"Trunk {trunk_id} path has no edge {path[i]} -> {path[i+1]}",
                                system_type=system_type,
                                trunk_id=trunk_id,
                                spaces=[path[i], path[i + 1]],
                            ))

        return violations

    def validate_zone_compliance(
        self,
        topology: Any,
        system_type: str,
        zone_definitions: Dict[str, Any],
    ) -> List[ValidationViolation]:
        """
        Validate zone crossing compliance.

        Args:
            topology: System topology
            system_type: Type of system
            zone_definitions: Zone definitions

        Returns:
            List of zone violations
        """
        violations = []
        trunks = self._get_topology_trunks(topology)

        # Build space-to-zone map
        space_to_zone: Dict[str, str] = {}
        for zone_id, zone in zone_definitions.items():
            if hasattr(zone, 'spaces'):
                for space in zone.spaces:
                    space_to_zone[space] = zone_id
            elif isinstance(zone, dict):
                for space in zone.get('spaces', []):
                    space_to_zone[space] = zone_id

        for trunk_id, trunk in trunks.items():
            path = self._get_trunk_path(trunk)

            for i in range(len(path) - 1):
                from_space = path[i]
                to_space = path[i + 1]

                from_zone = space_to_zone.get(from_space)
                to_zone = space_to_zone.get(to_space)

                if from_zone and to_zone and from_zone != to_zone:
                    # Zone crossing - check if allowed
                    zone_def = zone_definitions.get(from_zone)
                    is_prohibited = self._is_zone_crossing_prohibited(
                        zone_def, system_type
                    )

                    if is_prohibited:
                        self._violation_counter += 1
                        violations.append(ValidationViolation(
                            violation_id=f"v_{self._violation_counter}",
                            rule_name="zone_crossing",
                            severity=ValidationSeverity.ERROR,
                            message=f"System {system_type} cannot cross from zone {from_zone} to {to_zone}",
                            system_type=system_type,
                            trunk_id=trunk_id,
                            spaces=[from_space, to_space],
                            recommendation="Reroute to avoid zone crossing",
                        ))

        return violations

    def validate_separation(
        self,
        topologies: Dict[str, Any],
        separation_rules: Any,
    ) -> List[ValidationViolation]:
        """
        Validate separation requirements between systems.

        Args:
            topologies: All system topologies
            separation_rules: Separation rule set

        Returns:
            List of separation violations
        """
        violations = []
        system_types = list(topologies.keys())

        for i, sys_a in enumerate(system_types):
            for sys_b in system_types[i + 1:]:
                sys_a_str = str(sys_a)
                sys_b_str = str(sys_b)

                # Get paths for both systems
                paths_a = self._get_all_paths(topologies[sys_a])
                paths_b = self._get_all_paths(topologies[sys_b])

                # Check for prohibited co-routing
                if separation_rules.is_prohibited(sys_a_str, sys_b_str):
                    for path_a in paths_a:
                        for path_b in paths_b:
                            shared = set(path_a) & set(path_b)
                            if shared:
                                self._violation_counter += 1
                                violations.append(ValidationViolation(
                                    violation_id=f"v_{self._violation_counter}",
                                    rule_name="prohibited_co_routing",
                                    severity=ValidationSeverity.CRITICAL,
                                    message=f"Prohibited co-routing of {sys_a_str} and {sys_b_str}",
                                    spaces=list(shared),
                                    recommendation=f"Separate {sys_a_str} and {sys_b_str} routing",
                                ))

                # Check separation distance
                min_dist = separation_rules.get_min_distance(sys_a_str, sys_b_str)
                if min_dist > 0:
                    for path_a in paths_a:
                        for path_b in paths_b:
                            shared = set(path_a) & set(path_b)
                            if shared:
                                # Distance = 0 in shared spaces
                                self._violation_counter += 1
                                violations.append(ValidationViolation(
                                    violation_id=f"v_{self._violation_counter}",
                                    rule_name="separation_distance",
                                    severity=ValidationSeverity.ERROR,
                                    message=f"{sys_a_str} and {sys_b_str} require {min_dist}m separation",
                                    spaces=list(shared),
                                    recommendation="Reroute to maintain separation",
                                ))

        return violations

    def validate_redundancy(
        self,
        topologies: Dict[str, Any],
        compartment_graph: Optional[Any],
    ) -> List[ValidationViolation]:
        """
        Validate redundancy requirements for critical systems.

        Args:
            topologies: All system topologies
            compartment_graph: Graph for path analysis

        Returns:
            List of redundancy violations
        """
        violations = []

        # Systems that require redundancy
        critical_systems = {
            'electrical_hv', 'firefighting', 'fire_detection', 'bilge'
        }

        for sys_type, topology in topologies.items():
            sys_str = str(sys_type)
            if sys_str not in critical_systems:
                continue

            nodes = self._get_topology_nodes(topology)

            # Check critical consumers have redundant feed
            for node_id, node in nodes.items():
                node_type = self._get_node_type(node)
                is_critical = self._is_node_critical(node)

                if node_type == 'consumer' and is_critical:
                    # Count incoming trunks
                    incoming = self._count_incoming_trunks(node_id, topology)

                    if incoming < 2:
                        self._violation_counter += 1
                        violations.append(ValidationViolation(
                            violation_id=f"v_{self._violation_counter}",
                            rule_name="redundancy",
                            severity=ValidationSeverity.WARNING,
                            message=f"Critical node {node_id} in {sys_str} has only {incoming} feed(s)",
                            system_type=sys_str,
                            recommendation="Add redundant feed path",
                        ))

        return violations

    def validate_capacity(
        self,
        topologies: Dict[str, Any],
    ) -> List[ValidationViolation]:
        """
        Validate trunk capacity is adequate.

        Args:
            topologies: All system topologies

        Returns:
            List of capacity violations
        """
        violations = []

        for sys_type, topology in topologies.items():
            trunks = self._get_topology_trunks(topology)

            for trunk_id, trunk in trunks.items():
                capacity = self._get_trunk_capacity(trunk)
                demand = self._get_trunk_demand(trunk, topology)

                if capacity > 0 and demand > capacity:
                    self._violation_counter += 1
                    violations.append(ValidationViolation(
                        violation_id=f"v_{self._violation_counter}",
                        rule_name="capacity",
                        severity=ValidationSeverity.ERROR,
                        message=f"Trunk {trunk_id} demand {demand} exceeds capacity {capacity}",
                        system_type=str(sys_type),
                        trunk_id=trunk_id,
                        recommendation="Increase trunk size or add parallel trunk",
                    ))

        return violations

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _get_topology_nodes(self, topology: Any) -> Dict[str, Any]:
        """Get nodes from topology."""
        if hasattr(topology, 'nodes'):
            return topology.nodes if isinstance(topology.nodes, dict) else {}
        if isinstance(topology, dict):
            return topology.get('nodes', {})
        return {}

    def _get_topology_trunks(self, topology: Any) -> Dict[str, Any]:
        """Get trunks from topology."""
        if hasattr(topology, 'trunks'):
            return topology.trunks if isinstance(topology.trunks, dict) else {}
        if isinstance(topology, dict):
            return topology.get('trunks', {})
        return {}

    def _get_trunk_from_node(self, trunk: Any) -> Optional[str]:
        """Get from_node from trunk."""
        if hasattr(trunk, 'from_node_id'):
            return trunk.from_node_id
        if isinstance(trunk, dict):
            return trunk.get('from_node_id')
        return None

    def _get_trunk_to_node(self, trunk: Any) -> Optional[str]:
        """Get to_node from trunk."""
        if hasattr(trunk, 'to_node_id'):
            return trunk.to_node_id
        if isinstance(trunk, dict):
            return trunk.get('to_node_id')
        return None

    def _get_trunk_path(self, trunk: Any) -> List[str]:
        """Get path_spaces from trunk."""
        if hasattr(trunk, 'path_spaces'):
            return trunk.path_spaces
        if isinstance(trunk, dict):
            return trunk.get('path_spaces', [])
        return []

    def _get_trunk_capacity(self, trunk: Any) -> float:
        """Get capacity from trunk."""
        if hasattr(trunk, 'capacity'):
            return trunk.capacity
        if isinstance(trunk, dict):
            return trunk.get('capacity', 0.0)
        return 0.0

    def _get_trunk_demand(self, trunk: Any, topology: Any) -> float:
        """Calculate demand for trunk based on downstream nodes."""
        to_node_id = self._get_trunk_to_node(trunk)
        if not to_node_id:
            return 0.0

        nodes = self._get_topology_nodes(topology)
        node = nodes.get(to_node_id)
        if not node:
            return 0.0

        if hasattr(node, 'demand_units'):
            return node.demand_units
        if isinstance(node, dict):
            return node.get('demand_units', 0.0)
        return 0.0

    def _get_node_type(self, node: Any) -> str:
        """Get node type."""
        if hasattr(node, 'node_type'):
            return str(node.node_type).lower().replace('nodetype.', '')
        if isinstance(node, dict):
            return node.get('node_type', '').lower()
        return ''

    def _is_node_critical(self, node: Any) -> bool:
        """Check if node is critical."""
        if hasattr(node, 'is_critical'):
            return node.is_critical
        if isinstance(node, dict):
            return node.get('is_critical', False)
        return False

    def _count_incoming_trunks(self, node_id: str, topology: Any) -> int:
        """Count trunks going to a node."""
        trunks = self._get_topology_trunks(topology)
        count = 0
        for trunk in trunks.values():
            if self._get_trunk_to_node(trunk) == node_id:
                count += 1
        return count

    def _get_all_paths(self, topology: Any) -> List[List[str]]:
        """Get all trunk paths from topology."""
        trunks = self._get_topology_trunks(topology)
        return [self._get_trunk_path(t) for t in trunks.values()]

    def _is_zone_crossing_prohibited(
        self,
        zone_def: Any,
        system_type: str,
    ) -> bool:
        """Check if system is prohibited from crossing this zone."""
        if zone_def is None:
            return False

        if hasattr(zone_def, 'prohibited_systems'):
            return system_type in zone_def.prohibited_systems
        if isinstance(zone_def, dict):
            return system_type in zone_def.get('prohibited_systems', [])

        return False
