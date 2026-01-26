"""
magnet/bootstrap/manifold_blending.py

TA.5: Manifold Blender (manifold-aware hull blending).

This is a pragmatic MVP that follows the guide's intent without requiring
networked datasets or heavy training pipelines:
- builds a latent space using PCA over library parameter vectors (sklearn)
- blends in latent space
- decodes to parameter space
- projects back to a validity predicate using a simple contraction search

NOTE:
- Validity is provided as a callable (no domain heuristics here).
- Projection is numerical and deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from magnet.bootstrap.hull_library import HullLibrary, LibraryHull


ValidatorFn = Callable[[Dict[str, float]], bool]


class _NumpyPCA:
    """
    Minimal PCA implementation using numpy SVD.

    Purpose:
    - Avoid hard dependency on scikit-learn (import-time failure risk)
    - Provide deterministic encode/decode for blending
    """

    def __init__(self, *, variance_to_keep: float = 0.95) -> None:
        self._variance_to_keep = float(variance_to_keep)
        self.mean_: Optional[np.ndarray] = None
        self.components_: Optional[np.ndarray] = None  # shape: (k, n_features)
        self.n_components_: Optional[int] = None

    def fit(self, X: np.ndarray) -> "_NumpyPCA":
        X = np.asarray(X, dtype=float)
        if X.ndim != 2:
            raise ValueError("X must be 2D")
        if X.shape[0] < 2:
            # Degenerate: treat as identity.
            self.mean_ = np.mean(X, axis=0) if X.size else np.zeros((X.shape[1],), dtype=float)
            self.components_ = np.eye(X.shape[1], dtype=float)
            self.n_components_ = int(X.shape[1])
            return self

        mu = np.mean(X, axis=0)
        Xc = X - mu
        # SVD of centered data matrix.
        # Xc = U S Vt ; principal axes are rows of Vt
        _, S, Vt = np.linalg.svd(Xc, full_matrices=False)

        # Explained variance proportional to S^2
        var = (S**2) / max(1, X.shape[0] - 1)
        total = float(np.sum(var)) if var.size else 0.0
        if not np.isfinite(total) or total <= 0.0:
            k = int(X.shape[1])
        else:
            ratio = var / total
            cum = np.cumsum(ratio)
            keep = self._variance_to_keep
            if not np.isfinite(keep) or keep <= 0:
                k = 1
            elif keep >= 1:
                k = int(X.shape[1])
            else:
                k = int(np.searchsorted(cum, keep) + 1)
                k = max(1, min(int(X.shape[1]), k))

        self.mean_ = mu
        self.components_ = Vt[:k, :]
        self.n_components_ = int(k)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        if self.mean_ is None or self.components_ is None:
            raise RuntimeError("PCA not fit")
        X = np.asarray(X, dtype=float)
        return (X - self.mean_) @ self.components_.T

    def inverse_transform(self, Z: np.ndarray) -> np.ndarray:
        if self.mean_ is None or self.components_ is None:
            raise RuntimeError("PCA not fit")
        Z = np.asarray(Z, dtype=float)
        return (Z @ self.components_) + self.mean_


@dataclass(frozen=True)
class ManifoldPoint:
    parameters: Dict[str, float]
    latent_coords: np.ndarray
    validity_score: float


class ManifoldBlender:
    def __init__(
        self,
        *,
        hull_library: HullLibrary,
        validator: Optional[ValidatorFn] = None,
        variance_to_keep: float = 0.95,
        max_projection_iterations: int = 30,
    ) -> None:
        self._lib = hull_library
        self._validate = validator or (lambda _p: True)
        self._max_proj = int(max_projection_iterations)
        self._param_names = self._lib.parameter_names()
        if not self._param_names:
            raise ValueError("HullLibrary must contain at least one parameter key")

        X, _ = self._lib.as_matrix(parameter_order=self._param_names)
        if X.shape[0] < 2:
            # Degenerate library: treat latent as identity.
            self._pca = None
            self._latent_dim = len(self._param_names)
        else:
            self._pca = _NumpyPCA(variance_to_keep=float(variance_to_keep))
            self._pca.fit(X)
            self._latent_dim = int(getattr(self._pca, "n_components_", X.shape[1]) or X.shape[1])

    def encode(self, params: Dict[str, float]) -> np.ndarray:
        x = np.array([float(params.get(k, 0.0) or 0.0) for k in self._param_names], dtype=float).reshape(1, -1)
        if self._pca is None:
            return x.reshape(-1)
        return np.asarray(self._pca.transform(x), dtype=float).reshape(-1)

    def decode(self, latent: np.ndarray) -> Dict[str, float]:
        z = np.asarray(latent, dtype=float).reshape(1, -1)
        if self._pca is None:
            x = z
        else:
            x = np.asarray(self._pca.inverse_transform(z), dtype=float)
        return {k: float(x[0, i]) for i, k in enumerate(self._param_names)}

    def blend(
        self,
        *,
        hull_ids: Sequence[str],
        weights: Sequence[float],
        anchor_hull_id: Optional[str] = None,
    ) -> Dict[str, float]:
        hulls = [self._lib.get(hid) for hid in hull_ids]
        w = _normalize_weights(weights, n=len(hulls))

        # Weighted latent blend
        Z = np.stack([self.encode(h.parameters) for h in hulls], axis=0)
        z_blend = (w.reshape(-1, 1) * Z).sum(axis=0)
        p_blend = self.decode(z_blend)

        if self._validate(p_blend):
            return p_blend

        # Projection: contract toward an anchor until valid.
        anchor = self._lib.get(anchor_hull_id) if anchor_hull_id else hulls[int(np.argmax(w))]
        p_anchor = dict(anchor.parameters)
        return self.project_to_validity(p_blend, anchor=p_anchor)

    def project_to_validity(self, params: Dict[str, float], *, anchor: Dict[str, float]) -> Dict[str, float]:
        """
        Numerical projection by shrinking toward a known-valid anchor.
        """
        # If anchor isn't valid, just return anchor as best-effort.
        if not self._validate(anchor):
            return dict(anchor)

        # Line search alpha in [0,1] for p = (1-a)*anchor + a*params, find largest a valid.
        a_lo = 0.0
        a_hi = 1.0
        best = dict(anchor)

        for _ in range(self._max_proj):
            a = 0.5 * (a_lo + a_hi)
            cand = _lerp_dict(anchor, params, a)
            if self._validate(cand):
                best = cand
                a_lo = a
            else:
                a_hi = a
            if abs(a_hi - a_lo) < 1e-6:
                break
        return best


def _normalize_weights(weights: Sequence[float], *, n: int) -> np.ndarray:
    if n <= 0:
        return np.zeros((0,), dtype=float)
    if len(weights) != n:
        raise ValueError("weights length must match hull_ids length")
    w = np.array([float(x) for x in weights], dtype=float)
    s = float(np.sum(w))
    if not np.isfinite(s) or abs(s) < 1e-12:
        return np.ones((n,), dtype=float) / float(n)
    return w / s


def _lerp_dict(a: Dict[str, float], b: Dict[str, float], t: float) -> Dict[str, float]:
    out: Dict[str, float] = {}
    keys = set(a.keys()) | set(b.keys())
    tt = float(t)
    for k in keys:
        va = float(a.get(k, 0.0) or 0.0)
        vb = float(b.get(k, 0.0) or 0.0)
        out[str(k)] = (1.0 - tt) * va + tt * vb
    return out

