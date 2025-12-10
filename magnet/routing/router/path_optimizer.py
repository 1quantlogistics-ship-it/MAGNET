"""
path_optimizer.py - Route optimization v1.1
BRAVO OWNS THIS FILE.

Module 60: Systems Routing
Optimizes trunk routes for length, crossings, and conflicts.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any, Tuple
from enum import Enum
import logging
import math

try:
    import networkx as nx
except ImportError:
    nx = None

__all__ = [
    'PathOptimizer',
    'OptimizationObjective',
    'OptimizationResult',
]

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class OptimizationObjective(Enum):
    """Optimization objectives for path routing."""

    LENGTH = "length"                 # Minimize total length
    CROSSINGS = "crossings"           # Minimize zone crossings
    CONFLICTS = "conflicts"           # Minimize system conflicts
    COST = "cost"                     # Minimize weighted cost
    BALANCED = "balanced"             # Balance all objectives


# =============================================================================
# OPTIMIZATION RESULT
# =============================================================================

@dataclass
class OptimizationResult:
    """
    Result of path optimization.

    Attributes:
        success: Whether optimization completed successfully
        original_path: Path before optimization
        optimized_path: Path after optimization
        improvement: Improvement metrics
        iterations: Number of optimization iterations
    """

    success: bool = True
    original_path: List[str] = field(default_factory=list)
    optimized_path: List[str] = field(default_factory=list)

    # Improvement metrics
    length_reduction_m: float = 0.0
    crossings_reduced: int = 0
    conflicts_resolved: int = 0
    cost_reduction: float = 0.0

    iterations: int = 0
    message: str = ""

    @property
    def improvement_percent(self) -> float:
        """Calculate overall improvement percentage."""
        if self.cost_reduction > 0:
            return self.cost_reduction * 100
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "original_path": self.original_path,
            "optimized_path": self.optimized_path,
            "length_reduction_m": self.length_reduction_m,
            "crossings_reduced": self.crossings_reduced,
            "conflicts_resolved": self.conflicts_resolved,
            "cost_reduction": self.cost_reduction,
            "iterations": self.iterations,
            "message": self.message,
        }


# =============================================================================
# PATH OPTIMIZER
# =============================================================================

class PathOptimizer:
    """
    Optimizes routing paths for various objectives.

    Supports optimization for:
    - Total path length
    - Number of zone crossings
    - System conflicts
    - Weighted cost combination

    Usage:
        optimizer = PathOptimizer()
        result = optimizer.optimize(
            path=current_path,
            objective=OptimizationObjective.BALANCED,
            graph=compartment_graph,
        )
    """

    def __init__(
        self,
        length_weight: float = 1.0,
        crossing_weight: float = 2.0,
        conflict_weight: float = 5.0,
        max_iterations: int = 100,
    ):
        """
        Initialize path optimizer.

        Args:
            length_weight: Weight for length in cost calculation
            crossing_weight: Weight for zone crossings
            conflict_weight: Weight for system conflicts
            max_iterations: Maximum optimization iterations
        """
        self._length_weight = length_weight
        self._crossing_weight = crossing_weight
        self._conflict_weight = conflict_weight
        self._max_iterations = max_iterations

    def optimize(
        self,
        path: List[str],
        objective: OptimizationObjective,
        compartment_graph: Any,
        system_type: Optional[str] = None,
        existing_routes: Optional[Dict[str, List[str]]] = None,
    ) -> OptimizationResult:
        """
        Optimize a path for the given objective.

        Args:
            path: Current path (list of space IDs)
            objective: Optimization objective
            compartment_graph: Compartment adjacency graph
            system_type: System being routed (for conflict checking)
            existing_routes: Other system routes (system -> path)

        Returns:
            OptimizationResult with optimized path
        """
        if nx is None:
            return OptimizationResult(
                success=False,
                original_path=path,
                optimized_path=path,
                message="networkx not available",
            )

        if len(path) < 2:
            return OptimizationResult(
                success=True,
                original_path=path,
                optimized_path=path,
                message="Path too short to optimize",
            )

        result = OptimizationResult(
            original_path=path.copy(),
        )

        # Calculate original metrics
        orig_length = self._calculate_path_length(path, compartment_graph)
        orig_crossings = self._count_zone_crossings(path, compartment_graph)
        orig_conflicts = self._count_conflicts(path, existing_routes or {})
        orig_cost = self._calculate_cost(
            orig_length, orig_crossings, orig_conflicts
        )

        # Optimize based on objective
        if objective == OptimizationObjective.LENGTH:
            optimized = self._optimize_length(path, compartment_graph)
        elif objective == OptimizationObjective.CROSSINGS:
            optimized = self._optimize_crossings(path, compartment_graph)
        elif objective == OptimizationObjective.CONFLICTS:
            optimized = self._optimize_conflicts(
                path, compartment_graph, existing_routes or {}
            )
        elif objective == OptimizationObjective.COST:
            optimized = self._optimize_cost(
                path, compartment_graph, existing_routes or {}
            )
        else:  # BALANCED
            optimized = self._optimize_balanced(
                path, compartment_graph, existing_routes or {}
            )

        result.optimized_path = optimized

        # Calculate improvement metrics
        opt_length = self._calculate_path_length(optimized, compartment_graph)
        opt_crossings = self._count_zone_crossings(optimized, compartment_graph)
        opt_conflicts = self._count_conflicts(optimized, existing_routes or {})
        opt_cost = self._calculate_cost(opt_length, opt_crossings, opt_conflicts)

        result.length_reduction_m = orig_length - opt_length
        result.crossings_reduced = orig_crossings - opt_crossings
        result.conflicts_resolved = orig_conflicts - opt_conflicts
        result.cost_reduction = (orig_cost - opt_cost) / orig_cost if orig_cost > 0 else 0

        result.success = True
        result.message = f"Optimized path: {len(path)} -> {len(optimized)} spaces"

        return result

    def optimize_length(
        self,
        path: List[str],
        compartment_graph: Any,
    ) -> List[str]:
        """
        Optimize path for minimum length.

        Args:
            path: Current path
            compartment_graph: Graph for pathfinding

        Returns:
            Optimized path
        """
        return self._optimize_length(path, compartment_graph)

    def optimize_crossings(
        self,
        path: List[str],
        compartment_graph: Any,
    ) -> List[str]:
        """
        Optimize path for minimum zone crossings.

        Args:
            path: Current path
            compartment_graph: Graph with zone information

        Returns:
            Optimized path
        """
        return self._optimize_crossings(path, compartment_graph)

    def optimize_conflicts(
        self,
        path: List[str],
        compartment_graph: Any,
        existing_routes: Dict[str, List[str]],
    ) -> List[str]:
        """
        Optimize path to minimize conflicts with existing routes.

        Args:
            path: Current path
            compartment_graph: Graph for pathfinding
            existing_routes: Routes from other systems

        Returns:
            Optimized path
        """
        return self._optimize_conflicts(path, compartment_graph, existing_routes)

    def _optimize_length(
        self,
        path: List[str],
        graph: Any,
    ) -> List[str]:
        """Optimize for minimum length."""
        if len(path) < 2:
            return path

        start = path[0]
        end = path[-1]

        try:
            # Find shortest path
            shortest = nx.shortest_path(graph, start, end, weight='distance')
            return shortest
        except (nx.NetworkXNoPath, nx.NetworkXError):
            return path

    def _optimize_crossings(
        self,
        path: List[str],
        graph: Any,
    ) -> List[str]:
        """Optimize for minimum zone crossings."""
        if len(path) < 2:
            return path

        start = path[0]
        end = path[-1]

        # Create modified graph with high zone crossing costs
        modified = graph.copy()

        for u, v, data in modified.edges(data=True):
            base_cost = data.get('distance', 1.0)
            if data.get('zone_boundary', False):
                # Add high cost for zone crossings
                modified.edges[u, v]['crossing_cost'] = base_cost + 100.0
            else:
                modified.edges[u, v]['crossing_cost'] = base_cost

        try:
            optimized = nx.shortest_path(
                modified, start, end, weight='crossing_cost'
            )
            return optimized
        except (nx.NetworkXNoPath, nx.NetworkXError):
            return path

    def _optimize_conflicts(
        self,
        path: List[str],
        graph: Any,
        existing_routes: Dict[str, List[str]],
    ) -> List[str]:
        """Optimize to avoid conflicts with existing routes."""
        if len(path) < 2 or not existing_routes:
            return path

        start = path[0]
        end = path[-1]

        # Find spaces used by existing routes
        used_spaces: Set[str] = set()
        for route in existing_routes.values():
            used_spaces.update(route)

        # Create modified graph with conflict costs
        modified = graph.copy()

        for node in modified.nodes():
            if node in used_spaces and node not in (start, end):
                # Increase cost for passing through used spaces
                for neighbor in modified.neighbors(node):
                    if modified.has_edge(node, neighbor):
                        base_cost = modified.edges[node, neighbor].get('distance', 1.0)
                        modified.edges[node, neighbor]['conflict_cost'] = base_cost + 50.0
                    else:
                        modified.edges[node, neighbor]['conflict_cost'] = base_cost

        # Set default cost for edges without conflict
        for u, v, data in modified.edges(data=True):
            if 'conflict_cost' not in data:
                data['conflict_cost'] = data.get('distance', 1.0)

        try:
            optimized = nx.shortest_path(
                modified, start, end, weight='conflict_cost'
            )
            return optimized
        except (nx.NetworkXNoPath, nx.NetworkXError):
            return path

    def _optimize_cost(
        self,
        path: List[str],
        graph: Any,
        existing_routes: Dict[str, List[str]],
    ) -> List[str]:
        """Optimize for minimum weighted cost."""
        if len(path) < 2:
            return path

        start = path[0]
        end = path[-1]

        # Find spaces used by existing routes
        used_spaces: Set[str] = set()
        for route in existing_routes.values():
            used_spaces.update(route)

        # Create modified graph with weighted costs
        modified = graph.copy()

        for u, v, data in modified.edges(data=True):
            base_length = data.get('distance', 1.0)

            # Length component
            length_cost = base_length * self._length_weight

            # Crossing component
            crossing_cost = 0.0
            if data.get('zone_boundary', False):
                crossing_cost = self._crossing_weight * 10.0

            # Conflict component
            conflict_cost = 0.0
            if u in used_spaces or v in used_spaces:
                conflict_cost = self._conflict_weight * 5.0

            modified.edges[u, v]['weighted_cost'] = (
                length_cost + crossing_cost + conflict_cost
            )

        try:
            optimized = nx.shortest_path(
                modified, start, end, weight='weighted_cost'
            )
            return optimized
        except (nx.NetworkXNoPath, nx.NetworkXError):
            return path

    def _optimize_balanced(
        self,
        path: List[str],
        graph: Any,
        existing_routes: Dict[str, List[str]],
    ) -> List[str]:
        """Balanced optimization considering all factors."""
        # Try each optimization strategy and pick best
        candidates = [
            path,
            self._optimize_length(path, graph),
            self._optimize_crossings(path, graph),
            self._optimize_conflicts(path, graph, existing_routes),
            self._optimize_cost(path, graph, existing_routes),
        ]

        best_path = path
        best_cost = float('inf')

        for candidate in candidates:
            if not candidate:
                continue

            length = self._calculate_path_length(candidate, graph)
            crossings = self._count_zone_crossings(candidate, graph)
            conflicts = self._count_conflicts(candidate, existing_routes)
            cost = self._calculate_cost(length, crossings, conflicts)

            if cost < best_cost:
                best_cost = cost
                best_path = candidate

        return best_path

    def _calculate_path_length(
        self,
        path: List[str],
        graph: Any,
    ) -> float:
        """Calculate total path length."""
        if len(path) < 2:
            return 0.0

        total = 0.0
        for i in range(len(path) - 1):
            if graph.has_edge(path[i], path[i + 1]):
                total += graph.edges[path[i], path[i + 1]].get('distance', 1.0)
            else:
                total += 10.0  # Penalty for missing edge

        return total

    def _count_zone_crossings(
        self,
        path: List[str],
        graph: Any,
    ) -> int:
        """Count number of zone boundary crossings."""
        if len(path) < 2:
            return 0

        count = 0
        for i in range(len(path) - 1):
            if graph.has_edge(path[i], path[i + 1]):
                if graph.edges[path[i], path[i + 1]].get('zone_boundary', False):
                    count += 1

        return count

    def _count_conflicts(
        self,
        path: List[str],
        existing_routes: Dict[str, List[str]],
    ) -> int:
        """Count conflicts with existing routes."""
        if not existing_routes:
            return 0

        path_spaces = set(path[1:-1])  # Exclude endpoints
        conflicts = 0

        for route in existing_routes.values():
            route_spaces = set(route[1:-1])
            conflicts += len(path_spaces & route_spaces)

        return conflicts

    def _calculate_cost(
        self,
        length: float,
        crossings: int,
        conflicts: int,
    ) -> float:
        """Calculate weighted cost."""
        return (
            self._length_weight * length +
            self._crossing_weight * crossings * 10.0 +
            self._conflict_weight * conflicts * 5.0
        )
