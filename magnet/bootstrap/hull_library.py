"""
magnet/bootstrap/hull_library.py

T0.3: Hull Library Core.

This is an offline-friendly, minimal implementation used by bootstrap and blending:
- stores a set of library hull parameter vectors (continuous params only)
- provides simple nearest-neighbor search by parameter distance

NOTE:
- The guide discusses a HF Hub-backed dataset. This implementation intentionally
  avoids network dependencies; higher-level loaders can be added later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


@dataclass(frozen=True)
class LibraryHull:
    hull_id: str
    parameters: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LibrarySearchResult:
    hull: LibraryHull
    distance: float


class HullLibrary:
    def __init__(self, hulls: Optional[Iterable[LibraryHull]] = None):
        self._hulls: Dict[str, LibraryHull] = {}
        if hulls:
            for h in hulls:
                self.add(h)

    def add(self, hull: LibraryHull) -> None:
        hid = str(hull.hull_id)
        if not hid:
            raise ValueError("hull_id must be non-empty")
        self._hulls[hid] = hull

    def get(self, hull_id: str) -> LibraryHull:
        hid = str(hull_id)
        if hid not in self._hulls:
            raise KeyError(hid)
        return self._hulls[hid]

    def all_hulls(self) -> List[LibraryHull]:
        return [self._hulls[k] for k in sorted(self._hulls.keys())]

    def parameter_names(self) -> List[str]:
        names: set[str] = set()
        for h in self._hulls.values():
            for k in (h.parameters or {}).keys():
                names.add(str(k))
        return sorted(names)

    def as_matrix(self, *, parameter_order: Optional[Sequence[str]] = None) -> Tuple[np.ndarray, List[str]]:
        """
        Return (X, param_names) where X is shape (n_hulls, n_params).
        Missing values are filled with 0.0.
        """
        names = list(parameter_order) if parameter_order is not None else self.parameter_names()
        hulls = self.all_hulls()
        X = np.zeros((len(hulls), len(names)), dtype=float)
        for i, h in enumerate(hulls):
            for j, k in enumerate(names):
                X[i, j] = float((h.parameters or {}).get(k, 0.0) or 0.0)
        return X, names

    def search_by_parameters(
        self,
        target: Dict[str, float],
        *,
        k: int = 5,
        parameter_order: Optional[Sequence[str]] = None,
    ) -> List[LibrarySearchResult]:
        """
        Simple nearest-neighbor search in parameter space (Euclidean).
        """
        X, names = self.as_matrix(parameter_order=parameter_order)
        if X.size == 0:
            return []
        t = np.array([float(target.get(n, 0.0) or 0.0) for n in names], dtype=float)
        d = np.linalg.norm(X - t.reshape(1, -1), axis=1)
        hulls = self.all_hulls()
        idx = np.argsort(d)[: max(0, int(k))]
        return [LibrarySearchResult(hull=hulls[int(i)], distance=float(d[int(i)])) for i in idx]

