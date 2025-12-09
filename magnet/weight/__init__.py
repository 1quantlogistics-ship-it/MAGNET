"""
MAGNET Weight Estimation Framework

Modules 07 + 36 v1.1 - Production-Ready

Performs parametric weight estimation using SWBS (Ship Work Breakdown Structure).
Module 36 adds weight summary and loading conditions for stability analysis.

v1.1 Changes:
- Propulsion field fallbacks for schema compatibility
- determinize_dict() for hash-stable summary_data
- Writes stability.kg_m for stability integration
- Module 36: Loading conditions and weight summary
"""

from .groups import (
    SWBSGroup,
    WeightItem,
    GroupSummary,
    SWBS_GROUP_NAMES,
)

from .aggregator import (
    WeightAggregator,
    LightshipSummary,
)

from .utils import determinize_dict

from .estimators import (
    HullStructureEstimator,
    PropulsionPlantEstimator,
    ElectricPlantEstimator,
    CommandSurveillanceEstimator,
    AuxiliarySystemsEstimator,
    OutfitFurnishingsEstimator,
)

from .validators import (
    WeightEstimationValidator,
    WeightStabilityValidator,
    get_weight_estimation_definition,
    get_weight_stability_definition,
    register_weight_validators,
)

# Module 36: Loading Conditions and Weight Summary
from .loading import LoadingCondition, STANDARD_CONDITIONS
from .summary import WeightGroup, WeightMargins, WeightSummary, SWBS_DEFINITIONS
from .summary_generator import WeightSummaryGenerator
from .summary_validator import WeightSummaryValidator


# Weight estimation constants
HULL_WEIGHT_K = 0.034           # Watson-Gilfillan base coefficient
ALUMINUM_FACTOR = 0.65          # Aluminum vs steel factor
STEEL_FACTOR = 1.0              # Steel reference

ENGINE_SPECIFIC_WEIGHTS = {
    "high_speed_diesel": 4.0,    # kg/kW
    "medium_speed_diesel": 12.0,
    "gas_turbine": 1.5,
    "outboard": 2.5,
}

DEFAULT_WEIGHT_MARGIN = 0.10    # 10% of base weight
DEFAULT_VCG_FACTOR = 1.05       # Margin weight at elevated VCG


__all__ = [
    # Data structures
    "SWBSGroup",
    "WeightItem",
    "GroupSummary",
    "SWBS_GROUP_NAMES",
    # Aggregator
    "WeightAggregator",
    "LightshipSummary",
    # Utilities
    "determinize_dict",
    # Estimators
    "HullStructureEstimator",
    "PropulsionPlantEstimator",
    "ElectricPlantEstimator",
    "CommandSurveillanceEstimator",
    "AuxiliarySystemsEstimator",
    "OutfitFurnishingsEstimator",
    # Validators (Module 07)
    "WeightEstimationValidator",
    "WeightStabilityValidator",
    "get_weight_estimation_definition",
    "get_weight_stability_definition",
    "register_weight_validators",
    # Module 36: Loading & Summary
    "LoadingCondition",
    "STANDARD_CONDITIONS",
    "WeightGroup",
    "WeightMargins",
    "WeightSummary",
    "SWBS_DEFINITIONS",
    "WeightSummaryGenerator",
    "WeightSummaryValidator",
    # Constants
    "HULL_WEIGHT_K",
    "ALUMINUM_FACTOR",
    "STEEL_FACTOR",
    "ENGINE_SPECIFIC_WEIGHTS",
    "DEFAULT_WEIGHT_MARGIN",
    "DEFAULT_VCG_FACTOR",
]
