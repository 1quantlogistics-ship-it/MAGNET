"""
cost/validators.py - Cost estimation validator.

ALPHA OWNS THIS FILE.

Module 12 v1.1 - Cost Estimation Framework validator.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, TYPE_CHECKING
import logging

from .estimator import CostEstimator

from ..validators.taxonomy import (
    ValidatorInterface,
    ValidatorDefinition,
    ValidationResult,
    ValidationFinding,
    ValidatorState,
    ValidatorCategory,
    ValidatorPriority,
    ResultSeverity,
    ResourceRequirements,
)

if TYPE_CHECKING:
    from ..core.state_manager import StateManager

logger = logging.getLogger(__name__)


class CostValidator(ValidatorInterface):
    """
    Cost estimation validator for MAGNET validation pipeline.

    Reads:
        hull.lwl, hull.beam, hull.depth
        propulsion.installed_power_kw
        structure.material
        mission.vessel_type, mission.crew_size, mission.passengers
        production.materials (optional)
        weight.lightship_mt (optional)

    Writes:
        cost.estimate - Complete cost estimate dictionary
        cost.total_price - Total price (acquisition cost)
        cost.acquisition_cost - Acquisition cost
        cost.lifecycle_npv - Lifecycle NPV
        cost.subtotal_material - Material subtotal
        cost.subtotal_labor - Labor subtotal
        cost.subtotal_equipment - Equipment subtotal
        cost.summary - Cost summary dictionary
        cost.confidence - Estimate confidence level
    """

    def __init__(self, definition: ValidatorDefinition):
        super().__init__(definition)
        self.estimator = CostEstimator()

    def validate(
        self,
        state_manager: "StateManager",
        context: Dict[str, Any],
    ) -> ValidationResult:
        """Generate cost estimate and write to state."""
        result = ValidationResult(
            validator_id=self.definition.validator_id,
            state=ValidatorState.RUNNING,
            started_at=datetime.now(timezone.utc),
        )

        try:
            # Generate estimate
            estimate = self.estimator.estimate(state_manager)

            # Write results to state
            state_manager.set("cost.estimate", estimate.to_dict())
            state_manager.set("cost.total_price", estimate.total_price)
            state_manager.set("cost.acquisition_cost", estimate.acquisition_cost)
            state_manager.set("cost.lifecycle_npv", estimate.lifecycle_npv)
            state_manager.set("cost.subtotal_material", estimate.subtotal_material)
            state_manager.set("cost.subtotal_labor", estimate.subtotal_labor)
            state_manager.set("cost.subtotal_equipment", estimate.subtotal_equipment)
            state_manager.set("cost.confidence", estimate.confidence.value)

            # Summary
            summary = {
                "total_price": estimate.total_price,
                "acquisition_cost": estimate.acquisition_cost,
                "lifecycle_npv": estimate.lifecycle_npv,
                "confidence": estimate.confidence.value,
                "hours": estimate.get_total_hours(),
            }
            state_manager.set("cost.summary", summary)

            # Add informational finding
            result.add_finding(ValidationFinding(
                finding_id="cost-001",
                severity=ResultSeverity.INFO,
                message=f"Cost estimate at {estimate.confidence.value.upper()} confidence: ${estimate.total_price:,.0f}",
            ))

            if estimate.confidence.value == "rom":
                result.add_finding(ValidationFinding(
                    finding_id="cost-002",
                    severity=ResultSeverity.WARNING,
                    message="Estimate accuracy: ±50% (ROM level - production data not available)",
                    suggestion="Run production planning to improve estimate accuracy",
                ))

            result.state = ValidatorState.PASSED
            logger.info(
                f"Cost estimation: total_price=${estimate.total_price:,.0f}, "
                f"confidence={estimate.confidence.value}"
            )

        except Exception as e:
            logger.error(f"Cost estimation error: {e}")
            result.state = ValidatorState.ERROR
            result.error_message = str(e)

        result.completed_at = datetime.now(timezone.utc)
        return result


# =============================================================================
# VALIDATOR DEFINITION FACTORY
# =============================================================================

def get_cost_validator_definition() -> ValidatorDefinition:
    """Create ValidatorDefinition for cost/estimation validator."""
    return ValidatorDefinition(
        validator_id="cost/estimation",
        name="Cost Estimation Engine",
        description="Generates comprehensive cost estimate for vessel design (v1.1)",
        category=ValidatorCategory.ECONOMICS,
        priority=ValidatorPriority.NORMAL,
        phase="cost",
        is_gate_condition=False,
        depends_on_validators=["production/planning", "weight/estimation"],
        depends_on_parameters=[
            "hull.lwl", "hull.beam", "hull.depth",
            "propulsion.installed_power_kw",
            "structure.material",
            "mission.vessel_type", "mission.crew_size",
        ],
        produces_parameters=[
            "cost.estimate",
            "cost.total_price",
            "cost.acquisition_cost",
            "cost.lifecycle_npv",
            "cost.subtotal_material",
            "cost.subtotal_labor",
            "cost.subtotal_equipment",
            "cost.summary",
            "cost.confidence",
        ],
        timeout_seconds=60,
        resource_requirements=ResourceRequirements(cpu_cores=1, ram_gb=0.25),
        tags=["cost", "economics", "estimation", "v1.1"],
    )


def register_cost_validators():
    """Register cost validators with the pipeline."""
    return [
        (get_cost_validator_definition(), CostValidator),
    ]
