"""
magnet/bootstrap/import_shipd.py

T0.2: ShipD Importer

ShipD provides hulls as a parameter vector dataset (commonly 45 floats per hull).
This module imports those vectors into MAGNET as a lightweight bootstrap library.

Important:
- This importer does NOT attempt to "understand" hull families/types.
- It treats ShipD as a numeric seed source; novelty still comes from MAGNET's DSL.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import numpy as np


@dataclass(frozen=True)
class ShipDHull:
    """A single hull seed from ShipD (parameter vector only)."""

    hull_id: str
    vector: np.ndarray  # shape: (n_features,)
    source_path: str = ""

    def as_float_list(self) -> List[float]:
        return [float(x) for x in np.asarray(self.vector, dtype=float).reshape(-1)]


class ShipDImporter:
    """
    Import ShipD dataset from a local clone directory.

    The upstream repo structure can vary, so we support a small set of common
    filenames and allow callers to pass an explicit vector file path.
    """

    DEFAULT_CANDIDATE_FILES: Sequence[str] = (
        "InputVectors_30k.npy",
        "input_vectors_30k.npy",
        "input_vectors.npy",
        "InputVectors.npy",
        "shipd_vectors.npy",
    )

    def __init__(self, *, shipd_root: Path) -> None:
        self._root = Path(shipd_root)

    def find_vector_file(self) -> Path:
        if not self._root.exists():
            raise FileNotFoundError(f"ShipD root does not exist: {self._root}")
        for name in self.DEFAULT_CANDIDATE_FILES:
            p = self._root / name
            if p.exists():
                return p
        # Heuristic: look in a few common subfolders without walking entire tree.
        for sub in ("data", "dataset", "datasets", "assets"):
            for name in self.DEFAULT_CANDIDATE_FILES:
                p = self._root / sub / name
                if p.exists():
                    return p
        raise FileNotFoundError(
            "Could not locate ShipD parameter vector file. "
            f"Tried: {list(self.DEFAULT_CANDIDATE_FILES)} under {self._root}"
        )

    def import_vectors(
        self,
        *,
        vector_file: Optional[Path] = None,
        limit: Optional[int] = None,
        hull_id_prefix: str = "shipd",
    ) -> List[ShipDHull]:
        vec_path = Path(vector_file) if vector_file is not None else self.find_vector_file()
        X = np.load(vec_path)
        X = np.asarray(X, dtype=float)
        if X.ndim != 2:
            raise ValueError(f"ShipD vectors must be 2D array [n_hulls, n_features], got shape {X.shape}")
        n = int(X.shape[0])
        if limit is not None:
            n = min(n, int(limit))

        hulls: List[ShipDHull] = []
        for i in range(n):
            hulls.append(
                ShipDHull(
                    hull_id=f"{hull_id_prefix}:{i}",
                    vector=X[i].copy(),
                    source_path=str(vec_path),
                )
            )
        return hulls

    def iter_vectors(
        self,
        *,
        vector_file: Optional[Path] = None,
        limit: Optional[int] = None,
        hull_id_prefix: str = "shipd",
    ) -> Iterable[ShipDHull]:
        # Simple generator wrapper; avoids materializing all hulls if caller doesn't need it.
        vec_path = Path(vector_file) if vector_file is not None else self.find_vector_file()
        X = np.load(vec_path)
        X = np.asarray(X, dtype=float)
        if X.ndim != 2:
            raise ValueError(f"ShipD vectors must be 2D array [n_hulls, n_features], got shape {X.shape}")
        n = int(X.shape[0])
        if limit is not None:
            n = min(n, int(limit))
        for i in range(n):
            yield ShipDHull(
                hull_id=f"{hull_id_prefix}:{i}",
                vector=X[i].copy(),
                source_path=str(vec_path),
            )

