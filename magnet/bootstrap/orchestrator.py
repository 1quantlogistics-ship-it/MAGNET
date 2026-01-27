"""
magnet/bootstrap/orchestrator.py

T8.1: Bootstrap Orchestrator

Purpose:
- Build a local, offline-friendly "seed library" from available datasets
  (currently ShipD vectors) for search/blending/starting points.

Design:
- No hull-family/type priors (numeric vectors only).
- No network dependency (HF Hub integration can be layered later).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from magnet.bootstrap.embeddings import EmbeddingProvider, HashEmbedding, embed_hull_signatures
from magnet.bootstrap.hull_library import HullLibrary, LibraryHull
from magnet.bootstrap.import_shipd import ShipDImporter


def _vector_to_parameters(vec: Sequence[float], *, prefix: str = "p") -> Dict[str, float]:
    out: Dict[str, float] = {}
    for i, v in enumerate(vec):
        out[f"{prefix}{i}"] = float(v)
    return out


@dataclass(frozen=True)
class BootstrapArtifacts:
    library: HullLibrary
    hull_ids: List[str]
    parameter_names: List[str]
    embeddings: np.ndarray  # shape (n_hulls, dim)


class BootstrapOrchestrator:
    """
    Offline-friendly bootstrap orchestrator.

    This orchestrator intentionally keeps the contract small so it can be used
    in unit/integration tests and CLI tooling without requiring the full app.
    """

    def build_shipd_library(
        self,
        *,
        shipd_root: Path,
        vector_file: Optional[Path] = None,
        limit: Optional[int] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        hull_id_prefix: str = "shipd",
        parameter_prefix: str = "p",
    ) -> BootstrapArtifacts:
        importer = ShipDImporter(shipd_root=Path(shipd_root))
        hulls = importer.import_vectors(
            vector_file=vector_file,
            limit=limit,
            hull_id_prefix=str(hull_id_prefix),
        )

        lib = HullLibrary()
        hull_ids: List[str] = []
        vectors: List[List[float]] = []
        for h in hulls:
            v = h.as_float_list()
            params = _vector_to_parameters(v, prefix=str(parameter_prefix))
            lib.add(LibraryHull(hull_id=str(h.hull_id), parameters=params, metadata={"source_path": h.source_path}))
            hull_ids.append(str(h.hull_id))
            vectors.append(v)

        provider = embedding_provider or HashEmbedding()
        embs = embed_hull_signatures(hull_ids=hull_ids, vectors=vectors, provider=provider)

        return BootstrapArtifacts(
            library=lib,
            hull_ids=hull_ids,
            parameter_names=lib.parameter_names(),
            embeddings=np.asarray(embs, dtype=float),
        )

