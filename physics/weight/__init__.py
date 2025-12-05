"""
Weight estimation module for naval architecture.

Provides weight estimation for:
- Lightship (hull structure, machinery, outfit)
- Deadweight (cargo, fuel, stores, crew)
- Weight distribution (KG, LCG, TCG)
- Design margins per classification society rules
"""

from .lightship import (
    calculate_hull_steel_weight,
    calculate_machinery_weight,
    calculate_outfit_weight,
    calculate_lightship_weight,
    LightshipResult,
)
from .deadweight import (
    calculate_deadweight,
    calculate_displacement_balance,
    DeadweightResult,
    DisplacementBalance,
)
from .distribution import (
    calculate_weight_distribution,
    WeightItem,
    WeightDistribution,
)

__all__ = [
    # Lightship
    "calculate_hull_steel_weight",
    "calculate_machinery_weight",
    "calculate_outfit_weight",
    "calculate_lightship_weight",
    "LightshipResult",
    # Deadweight
    "calculate_deadweight",
    "calculate_displacement_balance",
    "DeadweightResult",
    "DisplacementBalance",
    # Distribution
    "calculate_weight_distribution",
    "WeightItem",
    "WeightDistribution",
]
