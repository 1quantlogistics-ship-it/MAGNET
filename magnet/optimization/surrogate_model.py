"""
magnet/optimization/surrogate_model.py

TM.1: Pluggable surrogate model interface.

Purpose:
- Provide a fast approximation of expensive physics evaluators.
- Expose a stable contract used by multi-fidelity optimizers:
  - fit(X, y)
  - predict(X) -> (mean, std)
  - compute_gradient(x) -> grad (optional, numerical fallback)
  - acquisition_value(x, best_y, exploration_weight) -> float

Notes:
- This module is optimization infrastructure; it MUST NOT contain naval-architecture
  heuristics (North Star: kernel validates reality, does not recognize intent).
- We use sklearn's GaussianProcessRegressor as a default backend because it is
  available in the environment, but the surrounding contract is intentionally
  backend-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
from scipy.stats import norm

try:
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import Matern
except Exception as e:  # pragma: no cover
    GaussianProcessRegressor = None  # type: ignore
    Matern = None  # type: ignore
    _SKLEARN_IMPORT_ERROR = e
else:
    _SKLEARN_IMPORT_ERROR = None


@dataclass
class SurrogateModel:
    """
    Fast approximation of an expensive evaluation function.

    Default backend: Gaussian Process Regression (Matern kernel).
    """

    # Training data
    X_train: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))
    y_train: np.ndarray = field(default_factory=lambda: np.empty((0,)))

    # Model backend
    kernel: object = field(default_factory=lambda: Matern(nu=2.5) if Matern is not None else object())
    gp: Optional["GaussianProcessRegressor"] = None

    # Metadata (optional)
    parameter_names: List[str] = field(default_factory=list)
    objective_name: str = ""

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train surrogate on evaluation data."""
        if GaussianProcessRegressor is None or _SKLEARN_IMPORT_ERROR is not None:
            raise RuntimeError(f"sklearn is required for SurrogateModel GP backend: {_SKLEARN_IMPORT_ERROR}")

        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        if X.ndim != 2:
            raise ValueError("X must be 2D array [n_samples, n_features]")
        if y.ndim != 1:
            raise ValueError("y must be 1D array [n_samples]")
        if X.shape[0] != y.shape[0]:
            raise ValueError("X and y must have same number of samples")

        self.X_train = X
        self.y_train = y
        self.gp = GaussianProcessRegressor(
            kernel=self.kernel,
            n_restarts_optimizer=3,
            normalize_y=True,
        )
        self.gp.fit(X, y)

    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict mean and uncertainty (std).
        """
        if self.gp is None:
            raise ValueError("Model not trained. Call fit() first.")
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        mean, std = self.gp.predict(X, return_std=True)
        return np.asarray(mean, dtype=float), np.asarray(std, dtype=float)

    def compute_gradient(self, x: np.ndarray, *, eps: float = 1e-6) -> np.ndarray:
        """
        Numerical gradient of surrogate mean at x.

        This intentionally does NOT depend on backend-specific analytical derivatives.
        Higher-level optimizers may swap this for an analytical gradient when available.
        """
        x = np.asarray(x, dtype=float).reshape(-1)
        if x.size == 0:
            return np.asarray([], dtype=float)
        grad = np.zeros_like(x)
        for i in range(x.shape[0]):
            x_plus = x.copy()
            x_minus = x.copy()
            x_plus[i] += eps
            x_minus[i] -= eps
            y_plus, _ = self.predict(x_plus.reshape(1, -1))
            y_minus, _ = self.predict(x_minus.reshape(1, -1))
            grad[i] = (float(y_plus[0]) - float(y_minus[0])) / (2.0 * float(eps))
        return grad

    def acquisition_value(
        self,
        x: np.ndarray,
        *,
        best_y: float,
        exploration_weight: float = 0.1,
    ) -> float:
        """
        Expected Improvement acquisition (maximize EI).

        NOTE: This assumes the objective is being maximized in surrogate space.
        Callers can negate objectives if they work in minimization.
        """
        mean, std = self.predict(np.asarray(x, dtype=float).reshape(1, -1))
        m = float(mean[0])
        s = float(std[0])
        if not np.isfinite(s) or s < 1e-12:
            return 0.0
        z = (m - float(best_y) - float(exploration_weight)) / s
        ei = (m - float(best_y) - float(exploration_weight)) * float(norm.cdf(z)) + s * float(norm.pdf(z))
        return float(ei)

