"""
magnet/kernel/observable_graph.py

TA.6 / TA.7: Lazy observable graph + batched registry.

Motivation:
- Downstream systems query derived observables frequently.
- Computing everything eagerly causes a thundering herd and collapses performance.
- We need a minimal lazy graph with invalidation and batching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Set


ComputeFn = Callable[[Dict[str, Any]], Any]


@dataclass
class ObservableNode:
    observable_id: str
    compute_fn: ComputeFn
    depends_on: Set[str] = field(default_factory=set)


class ObservableGraph:
    def __init__(self) -> None:
        self._nodes: Dict[str, ObservableNode] = {}
        self._cache: Dict[str, Any] = {}
        self._dependents: Dict[str, Set[str]] = {}

    def register(self, observable_id: str, *, compute_fn: ComputeFn, depends_on: Optional[Iterable[str]] = None) -> None:
        oid = str(observable_id)
        deps = {str(d) for d in (depends_on or [])}
        self._nodes[oid] = ObservableNode(observable_id=oid, compute_fn=compute_fn, depends_on=deps)
        for d in deps:
            self._dependents.setdefault(d, set()).add(oid)

    def invalidate(self, key: str) -> List[str]:
        """
        Invalidate cached observables that depend on `key`.
        Returns list of invalidated observable_ids.
        """
        invalidated: Set[str] = set()
        stack = [str(key)]
        while stack:
            k = stack.pop()
            for dep in self._dependents.get(k, set()):
                if dep in invalidated:
                    continue
                invalidated.add(dep)
                # Invalidate transitive dependents too
                stack.append(dep)
        for oid in invalidated:
            self._cache.pop(oid, None)
        return sorted(invalidated)

    def get(self, observable_id: str, state: Dict[str, Any]) -> Any:
        oid = str(observable_id)
        if oid in self._cache:
            return self._cache[oid]
        node = self._nodes.get(oid)
        if node is None:
            raise KeyError(f"Unknown observable: {oid}")
        val = node.compute_fn(state)
        self._cache[oid] = val
        return val

    def clear_cache(self) -> None:
        """Clear all cached observable values."""
        self._cache.clear()


class BatchedRegistry:
    """
    Simple batch wrapper over an ObservableGraph.
    """

    def __init__(self, graph: ObservableGraph):
        self._graph = graph

    def batch_get(self, observable_ids: List[str], state: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for oid in observable_ids:
            out[str(oid)] = self._graph.get(str(oid), state)
        return out

