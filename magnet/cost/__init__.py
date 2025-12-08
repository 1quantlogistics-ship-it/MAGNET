"""
cost/ - Cost Estimation Framework.

ALPHA OWNS THIS FILE.

Module 12 v1.1 - Cost Estimation Framework.

Provides comprehensive cost estimation including material, labor,
equipment, and lifecycle costs for vessel construction.

v1.1 Verified Field Names:
    - hull.lwl, hull.beam, hull.depth
    - propulsion.installed_power_kw
    - structure.material
    - mission.vessel_type, mission.crew_size
    - production.materials (optional)
    - weight.lightship_mt (optional)
"""

from .enums import (
    CostCategory,
    CostConfidence,
    CostPhase,
    LifecyclePhase,
)

from .schema import (
    CostItem,
    CostBreakdown,
    CostEstimate,
    LifecycleCost,
)

from .models import (
    MaterialCostModel,
    LaborCostModel,
    EquipmentCostModel,
    LifecycleCostModel,
)

from .estimator import CostEstimator

from .validators import (
    CostValidator,
    get_cost_validator_definition,
    register_cost_validators,
)


__all__ = [
    # Enums
    "CostCategory",
    "CostConfidence",
    "CostPhase",
    "LifecyclePhase",
    # Schema
    "CostItem",
    "CostBreakdown",
    "CostEstimate",
    "LifecycleCost",
    # Models
    "MaterialCostModel",
    "LaborCostModel",
    "EquipmentCostModel",
    "LifecycleCostModel",
    # Estimator
    "CostEstimator",
    # Validators
    "CostValidator",
    "get_cost_validator_definition",
    "register_cost_validators",
]
