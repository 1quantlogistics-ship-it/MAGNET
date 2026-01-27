"""
magnet/core/incremental_state.py

TM.5: Incremental state + invalidation.

Goal:
- Avoid recomputing all derived values on every mutation ("thundering herd").
- Track which computations depend on which inputs.
- Invalidate only affected cached computations when an input changes.

This is a standalone utility that can later be wired into StateManager/observable graphs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Set


@dataclass
class ComputationGraph:
    # input_key -> set(computation_id)
    dependents: Dict[str, Set[str]] = field(default_factory=dict)
    # computation_id -> set(input_key)
    inputs: Dict[str, Set[str]] = field(default_factory=dict)

    def register(self, computation_id: str, depends_on: List[str]) -> None:
        cid = str(computation_id)
        keys = {str(k) for k in (depends_on or [])}
        self.inputs[cid] = keys
        for k in keys:
            self.dependents.setdefault(k, set()).add(cid)

    def find_dependents(self, input_key: str) -> Set[str]:
        return set(self.dependents.get(str(input_key), set()))


@dataclass
class ComputationCache:
    values: Dict[str, Any] = field(default_factory=dict)

    def has(self, computation_id: str) -> bool:
        return str(computation_id) in self.values

    def get(self, computation_id: str) -> Any:
        return self.values[str(computation_id)]

    def set(self, computation_id: str, value: Any) -> None:
        self.values[str(computation_id)] = value

    def invalidate(self, computation_id: str) -> None:
        self.values.pop(str(computation_id), None)


class IncrementalStateManager:
    """
    Minimal incremental state with dependency-aware invalidation.
    """

    def __init__(self) -> None:
        self.state: Dict[str, Any] = {}
        self.graph = ComputationGraph()
        self.cache = ComputationCache()

    def update_parameter(self, key: str, value: Any) -> List[str]:
        """
        Update an input parameter and invalidate dependent computations.

        Returns list of invalidated computation_ids.
        """
        k = str(key)
        self.state[k] = value
        invalidated = sorted(self.graph.find_dependents(k))
        for cid in invalidated:
            self.cache.invalidate(cid)
        return invalidated

    def register_computation(self, computation_id: str, depends_on: List[str]) -> None:
        self.graph.register(computation_id, depends_on)

    def get_computation(self, computation_id: str, compute_fn: Callable[[Dict[str, Any]], Any]) -> Any:
        """
        Get cached computation result or compute and cache it.
        """
        cid = str(computation_id)
        if self.cache.has(cid):
            return self.cache.get(cid)
        val = compute_fn(self.state)
        self.cache.set(cid, val)
        return val

