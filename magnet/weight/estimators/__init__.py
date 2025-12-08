"""
MAGNET Weight Estimators

Module 07 v1.1 - Production-Ready

SWBS (Ship Work Breakdown Structure) group estimators.
"""

from .hull import HullStructureEstimator
from .propulsion import PropulsionPlantEstimator
from .electrical import ElectricPlantEstimator
from .command import CommandSurveillanceEstimator
from .auxiliary import AuxiliarySystemsEstimator
from .outfit import OutfitFurnishingsEstimator


__all__ = [
    "HullStructureEstimator",
    "PropulsionPlantEstimator",
    "ElectricPlantEstimator",
    "CommandSurveillanceEstimator",
    "AuxiliarySystemsEstimator",
    "OutfitFurnishingsEstimator",
]
