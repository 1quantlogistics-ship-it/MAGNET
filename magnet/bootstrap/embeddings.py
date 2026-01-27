"""
magnet/bootstrap/embeddings.py

T0.4: Embedding Provider

Purpose:
- Provide a pluggable embedding interface for semantic search over the hull library.
- Keep a dependency-light default so tests and offline workflows do not break.

Notes:
- In early phases, embeddings are used for *retrieval* (working set selection), not synthesis.
- Kernel synthesis remains continuous/constraint-based; retrieval is an accelerator, not a ceiling.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, List, Optional, Protocol, Sequence

import numpy as np

try:  # optional dependency
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # pragma: no cover
    SentenceTransformer = None  # type: ignore


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> np.ndarray: ...

    def embed_many(self, texts: Sequence[str]) -> np.ndarray: ...


@dataclass(frozen=True)
class HashEmbedding(EmbeddingProvider):
    """
    Deterministic, dependency-free embedding.

    This is NOT "semantic" in a language-model sense, but it provides:
    - stable shape
    - fast local computation
    - no external model downloads
    Useful for tests and as a safe fallback.
    """

    dim: int = 384

    def embed(self, text: str) -> np.ndarray:
        d = int(self.dim)
        if d <= 0:
            raise ValueError("dim must be positive")
        # Expand a sha256 digest stream into dim floats in [-1, 1].
        out = np.empty((d,), dtype=float)
        seed = text.encode("utf-8", errors="ignore")
        for i in range(d):
            h = hashlib.sha256(seed + i.to_bytes(4, "little")).digest()
            u = int.from_bytes(h[:8], "little") / float(2**64 - 1)
            out[i] = 2.0 * u - 1.0
        # Normalize for cosine similarity usage.
        n = float(np.linalg.norm(out)) or 1.0
        return out / n

    def embed_many(self, texts: Sequence[str]) -> np.ndarray:
        vecs = [self.embed(t) for t in texts]
        if not vecs:
            return np.empty((0, int(self.dim)), dtype=float)
        return np.stack(vecs, axis=0)


@dataclass(frozen=True)
class SentenceTransformersEmbedding(EmbeddingProvider):
    """
    Local semantic embeddings via sentence-transformers (optional dependency).
    """

    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    def __post_init__(self) -> None:
        if SentenceTransformer is None:  # pragma: no cover
            raise RuntimeError("sentence-transformers is not installed")

    def _model(self) -> "SentenceTransformer":  # type: ignore
        # Construct lazily to allow import-time usage without downloading models.
        return SentenceTransformer(self.model_name)  # type: ignore

    def embed(self, text: str) -> np.ndarray:
        return np.asarray(self._model().encode([text], normalize_embeddings=True)[0], dtype=float)

    def embed_many(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=float)
        X = self._model().encode(list(texts), normalize_embeddings=True)
        return np.asarray(X, dtype=float)


def build_hull_signature_text(
    *,
    hull_id: str,
    params: Sequence[float],
    max_params: int = 12,
) -> str:
    """
    Convert a parameter vector into a compact, stable "signature" string.

    This is used to compute embeddings even when upstream does not provide
    natural-language descriptions for hulls.
    """

    vals = [float(x) for x in params[: max(0, int(max_params))]]
    parts = [f"{v:+.4f}" for v in vals]
    return f"hull_id={hull_id} p[:{len(parts)}]=" + ",".join(parts)


def embed_hull_signatures(
    *,
    hull_ids: Sequence[str],
    vectors: Sequence[Sequence[float]],
    provider: EmbeddingProvider,
    max_params: int = 12,
) -> np.ndarray:
    if len(hull_ids) != len(vectors):
        raise ValueError("hull_ids and vectors must have same length")
    texts: List[str] = []
    for hid, vec in zip(hull_ids, vectors):
        texts.append(build_hull_signature_text(hull_id=str(hid), params=list(vec), max_params=max_params))
    return provider.embed_many(texts)

