"""
magnet/optimization/surrogate_trainer.py

TM.3B: Surrogate training pipeline.

Responsibilities:
- Maintain a simple training record format
- Convert records into (X, y) arrays
- Fit SurrogateModel instances per objective
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence

import numpy as np

from magnet.optimization.surrogate_model import SurrogateModel


@dataclass(frozen=True)
class TrainingRecord:
    params: Dict[str, float]
    objectives: Dict[str, float]


@dataclass
class SurrogateTrainingResult:
    models: Dict[str, SurrogateModel] = field(default_factory=dict)
    param_names: List[str] = field(default_factory=list)
    n_samples: int = 0


class SurrogateTrainer:
    def __init__(self, *, param_names: Sequence[str], objectives: Sequence[str]):
        self.param_names = list(param_names)
        self.objectives = list(objectives)
        if not self.param_names:
            raise ValueError("param_names must be non-empty")
        if not self.objectives:
            raise ValueError("objectives must be non-empty")

    def train(self, records: List[TrainingRecord]) -> SurrogateTrainingResult:
        if not records:
            return SurrogateTrainingResult(models={}, param_names=list(self.param_names), n_samples=0)

        X = np.array([[float(r.params[n]) for n in self.param_names] for r in records], dtype=float)
        models: Dict[str, SurrogateModel] = {}
        for obj in self.objectives:
            y = np.array([float(r.objectives[obj]) for r in records], dtype=float)
            m = SurrogateModel(parameter_names=list(self.param_names), objective_name=str(obj))
            m.fit(X, y)
            models[obj] = m

        return SurrogateTrainingResult(models=models, param_names=list(self.param_names), n_samples=int(X.shape[0]))

