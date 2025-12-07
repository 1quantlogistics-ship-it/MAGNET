"""
MAGNET Validator Topology

Module 04 v1.1 - Production-Ready

Defines the directed acyclic graph of validator dependencies.

v1.1 Changes:
- FIX #3: Maps parameter dependencies -> validator dependencies (implicit edges)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from collections import deque
import logging

from .taxonomy import (
    ValidatorDefinition,
    ValidatorState,
    ValidatorPriority,
)
from .builtin import get_all_validators, get_producer_for_parameter

logger = logging.getLogger(__name__)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class TopologyError(Exception):
    """Raised when topology has structural issues."""
    pass


class CyclicDependencyError(TopologyError):
    """Raised when validator dependencies form a cycle."""

    def __init__(self, cycle: List[str]):
        self.cycle = cycle
        super().__init__(f"Cyclic dependency detected: {' -> '.join(cycle)}")


# =============================================================================
# TOPOLOGY NODE
# =============================================================================

@dataclass
class TopologyNode:
    """A node in the validator dependency graph."""
    validator: ValidatorDefinition

    # Dependencies (edges)
    depends_on: Set[str] = field(default_factory=set)  # Validator IDs
    depended_by: Set[str] = field(default_factory=set)  # Reverse edges

    # FIX #3: Track implicit dependencies from parameters
    implicit_depends_on: Set[str] = field(default_factory=set)

    # Computed during build
    depth: int = 0
    execution_group: int = 0

    @property
    def all_dependencies(self) -> Set[str]:
        """All dependencies (explicit + implicit)."""
        return self.depends_on | self.implicit_depends_on

    def can_run(self, completed: Set[str]) -> bool:
        """Can this validator run given completed validators?"""
        return self.all_dependencies.issubset(completed)


@dataclass
class ExecutionGroup:
    """A group of validators that can run in parallel."""
    group_id: int
    validators: List[str]
    priority: ValidatorPriority
    estimated_duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "validators": self.validators,
            "priority": self.priority.value,
            "estimated_duration_ms": self.estimated_duration_ms,
        }


# =============================================================================
# VALIDATOR TOPOLOGY
# =============================================================================

class ValidatorTopology:
    """
    Directed acyclic graph of validator dependencies.

    v1.1: FIX #3 - Now includes implicit edges from parameter dependencies.
    """

    def __init__(self):
        self._nodes: Dict[str, TopologyNode] = {}
        self._execution_groups: List[ExecutionGroup] = []
        self._is_built: bool = False
        self._build_timestamp: Optional[datetime] = None

    def add_validator(self, validator: ValidatorDefinition) -> None:
        """Add a validator to the topology."""
        if self._is_built:
            raise RuntimeError("Cannot modify topology after build")

        node = TopologyNode(
            validator=validator,
            depends_on=set(validator.depends_on_validators),
        )
        self._nodes[validator.validator_id] = node

    def add_all_validators(self) -> None:
        """Add all built-in validators."""
        for validator in get_all_validators():
            self.add_validator(validator)

    def build(self) -> None:
        """Build the topology graph."""
        if self._is_built:
            return

        # FIX #3: Build implicit edges from parameter dependencies
        self._build_implicit_edges()

        # Build reverse edges
        self._build_reverse_edges()

        # Validate
        self._validate_dependencies()

        # Detect cycles
        cycles = self._detect_cycles()
        if cycles:
            raise CyclicDependencyError(cycles[0])

        # Compute depths
        self._compute_depths()

        # Create execution groups
        self._create_execution_groups()

        self._is_built = True
        self._build_timestamp = datetime.utcnow()

        logger.info(
            f"Topology built: {len(self._nodes)} validators, "
            f"{len(self._execution_groups)} execution groups, "
            f"{self._count_implicit_edges()} implicit edges"
        )

    def _build_implicit_edges(self) -> None:
        """
        FIX #3: Build implicit dependency edges from parameter dependencies.

        If validator A depends on parameter X, and validator B produces X,
        then A implicitly depends on B.
        """
        for node_id, node in self._nodes.items():
            for param in node.validator.depends_on_parameters:
                producer = get_producer_for_parameter(param)
                if producer and producer != node_id and producer in self._nodes:
                    node.implicit_depends_on.add(producer)
                    logger.debug(
                        f"Implicit edge: {node_id} depends on {producer} "
                        f"(via parameter {param})"
                    )

    def _count_implicit_edges(self) -> int:
        """Count total implicit edges."""
        return sum(len(n.implicit_depends_on) for n in self._nodes.values())

    def _build_reverse_edges(self) -> None:
        """Build depended_by edges."""
        for node_id, node in self._nodes.items():
            for dep_id in node.all_dependencies:
                if dep_id in self._nodes:
                    self._nodes[dep_id].depended_by.add(node_id)

    def _validate_dependencies(self) -> None:
        """Check all dependencies exist."""
        missing = []
        for node_id, node in self._nodes.items():
            for dep_id in node.all_dependencies:
                if dep_id not in self._nodes:
                    missing.append((node_id, dep_id))

        if missing:
            msg = "; ".join(f"{n} depends on missing {d}" for n, d in missing)
            raise TopologyError(f"Missing dependencies: {msg}")

    def _detect_cycles(self) -> List[List[str]]:
        """Detect cycles using DFS."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node_id: str, path: List[str]) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            node = self._nodes[node_id]
            for dep_id in node.all_dependencies:  # Use all_dependencies
                if dep_id not in visited:
                    dfs(dep_id, path.copy())
                elif dep_id in rec_stack:
                    cycle_start = path.index(dep_id)
                    cycles.append(path[cycle_start:] + [dep_id])

            rec_stack.remove(node_id)

        for node_id in self._nodes:
            if node_id not in visited:
                dfs(node_id, [])

        return cycles

    def _compute_depths(self) -> None:
        """Compute depth using all dependencies."""
        in_degree = {n: len(self._nodes[n].all_dependencies) for n in self._nodes}
        queue = deque([n for n, d in in_degree.items() if d == 0])

        while queue:
            node_id = queue.popleft()
            node = self._nodes[node_id]

            for dependent_id in node.depended_by:
                dependent = self._nodes[dependent_id]
                dependent.depth = max(dependent.depth, node.depth + 1)
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)

    def _create_execution_groups(self) -> None:
        """Create parallel execution groups."""
        depth_groups: Dict[int, List[TopologyNode]] = {}
        for node in self._nodes.values():
            if node.depth not in depth_groups:
                depth_groups[node.depth] = []
            depth_groups[node.depth].append(node)

        group_id = 0
        for depth in sorted(depth_groups.keys()):
            nodes = depth_groups[depth]

            # Sub-group by priority
            priority_groups: Dict[ValidatorPriority, List[TopologyNode]] = {}
            for node in nodes:
                priority = node.validator.priority
                if priority not in priority_groups:
                    priority_groups[priority] = []
                priority_groups[priority].append(node)

            for priority in sorted(priority_groups.keys(), key=lambda p: p.value):
                group_nodes = priority_groups[priority]

                for node in group_nodes:
                    node.execution_group = group_id

                self._execution_groups.append(ExecutionGroup(
                    group_id=group_id,
                    validators=[n.validator.validator_id for n in group_nodes],
                    priority=priority,
                    estimated_duration_ms=max(
                        n.validator.timeout_seconds * 1000 for n in group_nodes
                    ) if group_nodes else 0,
                ))
                group_id += 1

    def get_node(self, validator_id: str) -> Optional[TopologyNode]:
        """Get a node by validator ID."""
        return self._nodes.get(validator_id)

    def get_execution_order(self) -> List[str]:
        """Get validators in execution order."""
        if not self._is_built:
            raise RuntimeError("Topology not built")

        return sorted(
            self._nodes.keys(),
            key=lambda v: (
                self._nodes[v].depth,
                self._nodes[v].validator.priority.value,
                v
            )
        )

    def get_ready_validators(
        self,
        completed: Set[str],
        running: Set[str]
    ) -> List[str]:
        """Get validators ready to run."""
        ready = []
        for node_id, node in self._nodes.items():
            if node_id in completed or node_id in running:
                continue
            if node.can_run(completed):
                ready.append(node_id)

        return sorted(
            ready,
            key=lambda v: self._nodes[v].validator.priority.value
        )

    def get_transitive_dependents(self, validator_id: str) -> Set[str]:
        """Get all validators that transitively depend on this one."""
        result = set()
        to_process = [validator_id]

        while to_process:
            current = to_process.pop()
            node = self._nodes.get(current)
            if node:
                for dep_id in node.depended_by:
                    if dep_id not in result:
                        result.add(dep_id)
                        to_process.append(dep_id)

        return result

    def get_transitive_dependencies(self, validator_id: str) -> Set[str]:
        """Get all validators this one transitively depends on."""
        result = set()
        to_process = [validator_id]

        while to_process:
            current = to_process.pop()
            node = self._nodes.get(current)
            if node:
                for dep_id in node.all_dependencies:
                    if dep_id not in result:
                        result.add(dep_id)
                        to_process.append(dep_id)

        return result

    def get_validators_for_phase(self, phase: str) -> List[str]:
        """Get validator IDs for a specific phase."""
        return [
            v_id for v_id, node in self._nodes.items()
            if node.validator.phase == phase
        ]

    def get_gate_validators_for_phase(self, phase: str) -> List[str]:
        """Get gate validator IDs for a specific phase."""
        return [
            v_id for v_id, node in self._nodes.items()
            if node.validator.phase == phase and node.validator.is_gate_condition
        ]

    def get_execution_groups(self) -> List[ExecutionGroup]:
        """Get all execution groups in order."""
        return list(self._execution_groups)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize topology for persistence."""
        return {
            "nodes": {
                v_id: {
                    "depends_on": list(node.depends_on),
                    "implicit_depends_on": list(node.implicit_depends_on),
                    "depended_by": list(node.depended_by),
                    "depth": node.depth,
                    "execution_group": node.execution_group,
                }
                for v_id, node in self._nodes.items()
            },
            "execution_groups": [g.to_dict() for g in self._execution_groups],
            "build_timestamp": self._build_timestamp.isoformat() if self._build_timestamp else None,
        }

    @property
    def is_built(self) -> bool:
        return self._is_built

    @property
    def validator_count(self) -> int:
        return len(self._nodes)

    @property
    def group_count(self) -> int:
        return len(self._execution_groups)
