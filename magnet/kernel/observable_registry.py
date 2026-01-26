"""
magnet/kernel/observable_registry.py

T2.1: Observable Registry (measurable + controllable).

This is a lightweight catalog + binding layer:
- Registers observable specs
- Provides a query surface for current values via an ObservableGraph

The goal is to let the agent ask for "what can I measure/control?" without
computing the entire world eagerly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Callable, Dict, Iterable, List, Optional

from magnet.kernel.observable_graph import BatchedRegistry, ObservableGraph


MeasureFn = Callable[[Dict[str, Any]], Any]


@dataclass(frozen=True)
class ObservableSpec:
    """
    Canonical kernel-owned observable spec.

    NOTE: This intentionally contains both "core registry" fields (T2.1) and
    "control surface" metadata used by ADJUST/TARGET plumbing (T2.2+).
    """

    observable_id: str
    measurable: bool = True
    controllable: bool = False
    # T2.2: controllability flags / modes (DIRECT|COMPILED|OPTIMIZED)
    control_mode: str = "DIRECT"
    unit: str = ""
    description: str = ""
    tolerance: float = 0.0
    max_delta: float = 0.0
    knobs: List[str] = field(default_factory=list)
    applicable_to: List[str] = field(default_factory=list)
    # Optional: scope constraints (e.g. station/body/system/component IDs)
    allowed_scopes: List[str] = field(default_factory=list)

    # Optional: control metadata (used heavily by geometry observables)
    constraints: List[str] = field(default_factory=list)
    side_effects: List[str] = field(default_factory=list)
    reason: Optional[str] = None
    alternatives: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ObservableAlias:
    """
    Versioned/optional alias mapping for observables.

    Aliases allow the kernel to keep a stable canonical observable_id surface
    while supporting older names (optionally deprecated).
    """

    alias_id: str
    canonical_id: str
    deprecated: bool = False
    note: str = ""


class ObservableRegistry:
    def __init__(self, graph: Optional[ObservableGraph] = None) -> None:
        self._graph = graph or ObservableGraph()
        self._specs: Dict[str, ObservableSpec] = {}
        self._aliases: Dict[str, ObservableAlias] = {}
        self._batched = BatchedRegistry(self._graph)

    @property
    def graph(self) -> ObservableGraph:
        return self._graph

    def register(self, spec: ObservableSpec, *, measure_fn: MeasureFn, depends_on: Optional[List[str]] = None) -> None:
        oid = str(spec.observable_id)
        self._specs[oid] = spec
        # Note: dependency IDs may include aliases; register canonical dependency keys.
        deps = [self.resolve_id(d) for d in (depends_on or [])]
        self._graph.register(oid, compute_fn=measure_fn, depends_on=deps)

    def register_alias(self, alias: ObservableAlias) -> None:
        a = str(alias.alias_id)
        c = str(alias.canonical_id)
        if not a or not c:
            raise ValueError("alias_id and canonical_id must be non-empty")
        self._aliases[a] = ObservableAlias(alias_id=a, canonical_id=c, deprecated=bool(alias.deprecated), note=str(alias.note or ""))

    def resolve_id(self, observable_id: str) -> str:
        oid = str(observable_id or "")
        ali = self._aliases.get(oid)
        return str(ali.canonical_id) if ali is not None else oid

    def list_specs(self) -> List[ObservableSpec]:
        return [self._specs[k] for k in sorted(self._specs.keys())]

    def list_observable_ids(self) -> List[str]:
        return sorted(self._specs.keys())

    def list_controllable_ids(self) -> List[str]:
        return sorted([s.observable_id for s in self._specs.values() if bool(s.controllable)])

    def list_measurable_ids(self) -> List[str]:
        return sorted([s.observable_id for s in self._specs.values() if bool(s.measurable)])

    def suggest_ids(self, query: str, *, k: int = 3) -> List[str]:
        """
        Best-effort nearest observable_id suggestions for error messages.
        """
        q = str(query or "")
        candidates = list(self._specs.keys())
        if not q or not candidates:
            return []
        scored = [(SequenceMatcher(a=q, b=c).ratio(), c) for c in candidates]
        scored.sort(key=lambda t: t[0], reverse=True)
        return [c for _s, c in scored[: max(0, int(k))]]

    def get_spec(self, observable_id: str) -> ObservableSpec:
        oid = self.resolve_id(observable_id)
        if oid not in self._specs:
            raise KeyError(f"Unknown observable: {oid}")
        return self._specs[oid]

    def get_value(self, observable_id: str, state: Dict[str, Any]) -> Any:
        oid = self.resolve_id(observable_id)
        self._ensure_fresh_cache()
        return self._graph.get(oid, state)

    def batch_get(self, observable_ids: Iterable[str], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Batch-evaluate a set of observables (lazy; reuses graph cache).
        """
        ids = [self.resolve_id(o) for o in list(observable_ids or [])]
        self._ensure_fresh_cache()
        return self._batched.batch_get(ids, state)

    def invalidate(self, key: str) -> List[str]:
        """
        Invalidate cached dependents of `key` (lazy; does not recompute).
        """
        return self._graph.invalidate(self.resolve_id(key))

    def _ensure_fresh_cache(self) -> None:
        """
        ObservableGraph's cache is not keyed by state.

        To avoid stale reads when callers evaluate against different snapshots
        (common in optimization/LLM tooling), clear the cache per evaluation
        entrypoint. Callers that need within-snapshot reuse should use
        `batch_get(...)` and/or manage caching at a higher layer keyed by
        design_version.
        """
        try:
            self._graph.clear_cache()
        except Exception:
            pass

