"""
magnet/core/probabilistic_design.py

TM.4: Probabilistic design representation.

Why:
- Real engineering inputs are uncertain (weights, efficiencies, coefficients).
- Surrogate models provide uncertainty estimates.
- Optimization should be able to operate on distributions (chance constraints),
  even if the first implementation only supports sampling + expected-value views.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Dict, List, Optional


@dataclass(frozen=True)
class NormalDistribution:
    mean: float
    std: float

    def sample(self, rng: Optional[random.Random] = None) -> float:
        r = rng or random
        if self.std <= 0:
            return float(self.mean)
        return float(r.gauss(float(self.mean), float(self.std)))


@dataclass(frozen=True)
class ProbabilisticDesign:
    """
    A probabilistic view of a design: parameters/objectives as distributions.
    """

    parameters: Dict[str, NormalDistribution]
    objectives: Dict[str, NormalDistribution]
    constraint_satisfaction_probability: Dict[str, float] | None = None

    def expected_parameters(self) -> Dict[str, float]:
        return {k: float(v.mean) for k, v in (self.parameters or {}).items()}

    def expected_objectives(self) -> Dict[str, float]:
        return {k: float(v.mean) for k, v in (self.objectives or {}).items()}

    def sample_parameters(self, n: int, *, seed: Optional[int] = None) -> List[Dict[str, float]]:
        rng = random.Random(seed)
        out: List[Dict[str, float]] = []
        for _ in range(int(n)):
            out.append({k: dist.sample(rng) for k, dist in (self.parameters or {}).items()})
        return out

    def confidence_interval(self, key: str, *, level: float = 0.95, where: str = "parameters") -> tuple[float, float]:
        """
        Normal-approx CI: mean ± z*std.
        """
        if where not in ("parameters", "objectives"):
            raise ValueError("where must be 'parameters' or 'objectives'")
        dmap = self.parameters if where == "parameters" else self.objectives
        if key not in dmap:
            raise KeyError(key)
        dist = dmap[key]
        z = _z_for_level(level)
        lo = float(dist.mean) - z * float(dist.std)
        hi = float(dist.mean) + z * float(dist.std)
        return (lo, hi)


def _z_for_level(level: float) -> float:
    # Minimal mapping for common levels; fallback to 1.96.
    lvl = float(level)
    if abs(lvl - 0.90) < 1e-6:
        return 1.645
    if abs(lvl - 0.95) < 1e-6:
        return 1.960
    if abs(lvl - 0.99) < 1e-6:
        return 2.576
    # Crude approximation for others (avoid importing scipy here)
    return 1.960

