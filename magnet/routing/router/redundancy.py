"""
redundancy.py - Path diversity validation v1.1
BRAVO OWNS THIS FILE.

Module 60: Systems Routing
Validates redundancy requirements for critical systems.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any, Tuple
from enum import Enum
import logging

try:
    import networkx as nx
except ImportError:
    nx = None

__all__ = [
    'RedundancyChecker',
    'RedundancyResult',
    'PathDiversity',
    'RedundancyRequirement',
]

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND TYPES
# =============================================================================

class RedundancyRequirement(Enum):
    """Redundancy requirement levels."""

    NONE = "none"                     # No redundancy required
    PREFERRED = "preferred"           # Redundancy preferred
    REQUIRED = "required"             # Redundancy mandatory
    CRITICAL = "critical"             # Multiple independent paths required


@dataclass
class PathDiversity:
    """
    Analysis of path diversity between two nodes.

    Attributes:
        from_node: Source node ID
        to_node: Target node ID
        primary_path: Primary path (list of space IDs)
        alternate_paths: List of alternate paths
        shared_spaces: Spaces common to multiple paths
        shared_edges: Edges common to multiple paths
        diversity_score: 0.0 (identical) to 1.0 (fully independent)
        min_cut_size: Minimum cut to disconnect paths
    """

    from_node: str
    to_node: str

    primary_path: List[str] = field(default_factory=list)
    alternate_paths: List[List[str]] = field(default_factory=list)

    shared_spaces: Set[str] = field(default_factory=set)
    shared_edges: Set[Tuple[str, str]] = field(default_factory=set)

    diversity_score: float = 0.0
    min_cut_size: int = 1

    @property
    def has_alternate(self) -> bool:
        """Check if alternate paths exist."""
        return len(self.alternate_paths) > 0

    @property
    def is_fully_redundant(self) -> bool:
        """Check if paths are fully independent."""
        return self.diversity_score >= 0.95 and self.has_alternate

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "from_node": self.from_node,
            "to_node": self.to_node,
            "primary_path": self.primary_path,
            "alternate_paths": self.alternate_paths,
            "shared_spaces": list(self.shared_spaces),
            "shared_edges": [list(e) for e in self.shared_edges],
            "diversity_score": self.diversity_score,
            "min_cut_size": self.min_cut_size,
        }


@dataclass
class RedundancyResult:
    """
    Result of redundancy validation for a system.

    Attributes:
        system_type: System that was validated
        requirement: Required redundancy level
        is_compliant: Whether requirements are met
        diversities: Path diversity for each critical connection
        violations: List of redundancy violations
        recommendations: Suggested improvements
    """

    system_type: str
    requirement: RedundancyRequirement

    is_compliant: bool = True
    diversities: List[PathDiversity] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    # Statistics
    avg_diversity_score: float = 0.0
    min_diversity_score: float = 0.0
    redundant_path_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "system_type": self.system_type,
            "requirement": self.requirement.value,
            "is_compliant": self.is_compliant,
            "diversities": [d.to_dict() for d in self.diversities],
            "violations": self.violations,
            "recommendations": self.recommendations,
            "avg_diversity_score": self.avg_diversity_score,
            "min_diversity_score": self.min_diversity_score,
            "redundant_path_count": self.redundant_path_count,
        }


# =============================================================================
# REDUNDANCY CHECKER
# =============================================================================

class RedundancyChecker:
    """
    Validates path diversity and redundancy for critical systems.

    Checks that critical system nodes have independent routing paths
    to ensure continued operation if one path fails.

    Usage:
        checker = RedundancyChecker()
        result = checker.check_redundancy(
            system_type='electrical_hv',
            topology=system_topology,
            compartment_graph=graph,
            requirement=RedundancyRequirement.CRITICAL,
        )
    """

    def __init__(
        self,
        min_diversity_score: float = 0.5,
        critical_min_diversity: float = 0.8,
    ):
        """
        Initialize redundancy checker.

        Args:
            min_diversity_score: Minimum acceptable diversity score
            critical_min_diversity: Minimum for critical systems
        """
        self._min_diversity = min_diversity_score
        self._critical_min_diversity = critical_min_diversity

    def check_redundancy(
        self,
        system_type: str,
        nodes: Dict[str, Any],
        trunks: Dict[str, Any],
        compartment_graph: Any,
        requirement: RedundancyRequirement = RedundancyRequirement.REQUIRED,
    ) -> RedundancyResult:
        """
        Check redundancy requirements for a system.

        Args:
            system_type: Type of system being checked
            nodes: System nodes (node_id -> node)
            trunks: System trunks (trunk_id -> trunk)
            compartment_graph: Compartment adjacency graph
            requirement: Required redundancy level

        Returns:
            RedundancyResult with compliance status
        """
        if nx is None:
            logger.warning("networkx not available, skipping redundancy check")
            return RedundancyResult(
                system_type=system_type,
                requirement=requirement,
                is_compliant=True,
                recommendations=["Install networkx for redundancy checking"],
            )

        result = RedundancyResult(
            system_type=system_type,
            requirement=requirement,
        )

        # If no redundancy required, return compliant
        if requirement == RedundancyRequirement.NONE:
            result.is_compliant = True
            return result

        # Find source nodes
        source_nodes = [
            n for n in nodes.values()
            if self._is_source_node(n)
        ]

        # Find critical consumer nodes
        critical_consumers = [
            n for n in nodes.values()
            if self._is_critical_consumer(n)
        ]

        if not source_nodes or not critical_consumers:
            result.is_compliant = True
            result.recommendations.append(
                "No sources or critical consumers found for redundancy check"
            )
            return result

        # Check diversity for each critical consumer to sources
        diversities = []
        for consumer in critical_consumers:
            for source in source_nodes:
                diversity = self._check_path_diversity(
                    source, consumer, nodes, trunks, compartment_graph
                )
                diversities.append(diversity)

        result.diversities = diversities

        # Calculate statistics
        if diversities:
            scores = [d.diversity_score for d in diversities]
            result.avg_diversity_score = sum(scores) / len(scores)
            result.min_diversity_score = min(scores)
            result.redundant_path_count = sum(
                1 for d in diversities if d.has_alternate
            )

        # Check compliance based on requirement
        min_required = self._get_min_diversity(requirement)

        for diversity in diversities:
            if not diversity.has_alternate and requirement in (
                RedundancyRequirement.REQUIRED,
                RedundancyRequirement.CRITICAL,
            ):
                result.violations.append(
                    f"No alternate path from {diversity.from_node} to {diversity.to_node}"
                )

            if diversity.diversity_score < min_required:
                result.violations.append(
                    f"Diversity score {diversity.diversity_score:.2f} below "
                    f"required {min_required:.2f} for {diversity.from_node} -> {diversity.to_node}"
                )

        result.is_compliant = len(result.violations) == 0

        # Generate recommendations
        self._generate_recommendations(result, diversities)

        return result

    def find_independent_paths(
        self,
        from_space: str,
        to_space: str,
        compartment_graph: Any,
        max_paths: int = 3,
    ) -> List[List[str]]:
        """
        Find independent paths between two spaces.

        Args:
            from_space: Source space ID
            to_space: Target space ID
            compartment_graph: Compartment adjacency graph
            max_paths: Maximum number of paths to find

        Returns:
            List of paths (each path is list of space IDs)
        """
        if nx is None:
            return []

        if from_space not in compartment_graph or to_space not in compartment_graph:
            return []

        paths = []

        try:
            # Find shortest paths using different methods
            # 1. Shortest path
            primary = nx.shortest_path(
                compartment_graph, from_space, to_space, weight='cost'
            )
            paths.append(primary)

            # 2. Find edge-disjoint paths if possible
            try:
                for path in nx.edge_disjoint_paths(
                    compartment_graph, from_space, to_space
                ):
                    if list(path) not in paths:
                        paths.append(list(path))
                    if len(paths) >= max_paths:
                        break
            except (nx.NetworkXError, nx.NetworkXNoPath):
                pass

            # 3. Find node-disjoint paths (more stringent)
            if len(paths) < max_paths:
                try:
                    for path in nx.node_disjoint_paths(
                        compartment_graph, from_space, to_space
                    ):
                        if list(path) not in paths:
                            paths.append(list(path))
                        if len(paths) >= max_paths:
                            break
                except (nx.NetworkXError, nx.NetworkXNoPath):
                    pass

        except nx.NetworkXNoPath:
            pass

        return paths[:max_paths]

    def calculate_separation_score(
        self,
        path_a: List[str],
        path_b: List[str],
    ) -> float:
        """
        Calculate separation score between two paths.

        Score is 1.0 for fully independent paths, 0.0 for identical paths.

        Args:
            path_a: First path (list of space IDs)
            path_b: Second path (list of space IDs)

        Returns:
            Separation score between 0.0 and 1.0
        """
        if not path_a or not path_b:
            return 0.0

        # Exclude start and end nodes (they must be shared)
        interior_a = set(path_a[1:-1]) if len(path_a) > 2 else set()
        interior_b = set(path_b[1:-1]) if len(path_b) > 2 else set()

        if not interior_a and not interior_b:
            # Both paths are direct connections
            return 1.0 if path_a != path_b else 0.0

        # Calculate Jaccard distance (1 - intersection/union)
        union = interior_a | interior_b
        intersection = interior_a & interior_b

        if not union:
            return 1.0

        return 1.0 - (len(intersection) / len(union))

    def _check_path_diversity(
        self,
        source_node: Any,
        consumer_node: Any,
        nodes: Dict[str, Any],
        trunks: Dict[str, Any],
        compartment_graph: Any,
    ) -> PathDiversity:
        """Check path diversity between source and consumer."""
        from_space = self._get_node_space(source_node)
        to_space = self._get_node_space(consumer_node)
        from_node_id = self._get_node_id(source_node)
        to_node_id = self._get_node_id(consumer_node)

        diversity = PathDiversity(
            from_node=from_node_id,
            to_node=to_node_id,
        )

        # Find paths
        paths = self.find_independent_paths(
            from_space, to_space, compartment_graph
        )

        if not paths:
            return diversity

        diversity.primary_path = paths[0]
        diversity.alternate_paths = paths[1:]

        # Calculate shared spaces and edges
        if len(paths) > 1:
            all_spaces = [set(p[1:-1]) for p in paths]
            diversity.shared_spaces = set.intersection(*all_spaces) if all_spaces else set()

            all_edges = []
            for path in paths:
                edges = set()
                for i in range(len(path) - 1):
                    edges.add((min(path[i], path[i+1]), max(path[i], path[i+1])))
                all_edges.append(edges)
            diversity.shared_edges = set.intersection(*all_edges) if all_edges else set()

            # Calculate diversity score (average separation from primary)
            scores = [
                self.calculate_separation_score(paths[0], p)
                for p in paths[1:]
            ]
            diversity.diversity_score = max(scores) if scores else 0.0
        else:
            diversity.diversity_score = 0.0

        # Calculate min cut
        if nx is not None and from_space in compartment_graph and to_space in compartment_graph:
            try:
                diversity.min_cut_size = nx.node_connectivity(
                    compartment_graph, from_space, to_space
                )
            except nx.NetworkXError:
                diversity.min_cut_size = 1

        return diversity

    def _is_source_node(self, node: Any) -> bool:
        """Check if node is a source."""
        if hasattr(node, 'node_type'):
            return str(node.node_type).lower() in ('source', 'nodetype.source')
        if isinstance(node, dict):
            return node.get('node_type', '').lower() == 'source'
        return False

    def _is_critical_consumer(self, node: Any) -> bool:
        """Check if node is a critical consumer."""
        if hasattr(node, 'is_critical') and hasattr(node, 'node_type'):
            is_consumer = str(node.node_type).lower() in ('consumer', 'nodetype.consumer')
            return is_consumer and node.is_critical
        if isinstance(node, dict):
            is_consumer = node.get('node_type', '').lower() == 'consumer'
            return is_consumer and node.get('is_critical', False)
        return False

    def _get_node_space(self, node: Any) -> str:
        """Get space ID from node."""
        if hasattr(node, 'space_id'):
            return node.space_id
        if isinstance(node, dict):
            return node.get('space_id', '')
        return ''

    def _get_node_id(self, node: Any) -> str:
        """Get node ID."""
        if hasattr(node, 'node_id'):
            return node.node_id
        if isinstance(node, dict):
            return node.get('node_id', '')
        return ''

    def _get_min_diversity(self, requirement: RedundancyRequirement) -> float:
        """Get minimum diversity score for requirement level."""
        if requirement == RedundancyRequirement.CRITICAL:
            return self._critical_min_diversity
        elif requirement == RedundancyRequirement.REQUIRED:
            return self._min_diversity
        elif requirement == RedundancyRequirement.PREFERRED:
            return self._min_diversity * 0.5
        return 0.0

    def _generate_recommendations(
        self,
        result: RedundancyResult,
        diversities: List[PathDiversity],
    ) -> None:
        """Generate recommendations for improving redundancy."""
        for diversity in diversities:
            if not diversity.has_alternate:
                result.recommendations.append(
                    f"Add alternate route from {diversity.from_node} to {diversity.to_node}"
                )
            elif diversity.shared_spaces:
                result.recommendations.append(
                    f"Consider routing through different spaces to avoid "
                    f"shared points: {', '.join(diversity.shared_spaces)}"
                )
            elif diversity.diversity_score < self._min_diversity:
                result.recommendations.append(
                    f"Increase path separation for {diversity.from_node} -> "
                    f"{diversity.to_node} (current: {diversity.diversity_score:.2f})"
                )
