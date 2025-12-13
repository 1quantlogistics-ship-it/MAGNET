"""
optimization/validator.py - Optimization validator.

BRAVO OWNS THIS FILE.

Module 13 v1.1 - Optimization validation.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging

from .enums import OptimizerStatus
from .schema import OptimizationProblem, OptimizationResult
from .problems import create_standard_patrol_boat_problem
from .optimizer import DesignOptimizer
from .pareto import ParetoAnalyzer

from ..validators.taxonomy import (
    ValidatorInterface,
    ValidatorDefinition,
    ValidatorCategory,
    ValidatorPriority,
    ValidatorState,
    ValidationResult,
    ValidationFinding,
    ResultSeverity,
)

if TYPE_CHECKING:
    from ..core.state_manager import StateManager

logger = logging.getLogger(__name__)


def determinize_dict(data: Dict, precision: int = 6) -> Dict:
    """Make dictionary deterministic for hashing."""
    if isinstance(data, dict):
        return {k: determinize_dict(v, precision) for k, v in sorted(data.items())}
    elif isinstance(data, list):
        return [determinize_dict(item, precision) for item in data]
    elif isinstance(data, float):
        return round(data, precision)
    else:
        return data


class OptimizationValidator(ValidatorInterface):
    """
    Optimization validator for design optimization.

    Runs NSGA-II optimization and writes results to state.

    Reads:
        * (entire state for optimization evaluation)

    Writes:
        optimization.problem - Problem definition
        optimization.result - Optimization result
        optimization.pareto_front - Pareto front solutions
        optimization.selected_solution - Selected best solution
        optimization.sensitivity - Sensitivity analysis
        optimization.status - Optimizer status
        optimization.iterations - Number of iterations
        optimization.evaluations - Number of evaluations
    """

    def __init__(
        self,
        definition: ValidatorDefinition,
        population_size: int = 30,
        max_generations: int = 50,
    ):
        super().__init__(definition)
        self.population_size = population_size
        self.max_generations = max_generations

    def validate(
        self,
        state_manager: "StateManager",
        context: Dict[str, Any],
    ) -> ValidationResult:
        """Run optimization and validate results."""
        result = ValidationResult(
            validator_id=self.definition.validator_id,
            state=ValidatorState.RUNNING,
            started_at=datetime.now(timezone.utc),
        )

        try:
            # Get or create optimization problem
            problem = context.get("problem")
            if problem is None:
                problem = create_standard_patrol_boat_problem()

            # Check required inputs exist
            lwl = state_manager.get("hull.lwl")
            if lwl is None or lwl <= 0:
                result.add_finding(ValidationFinding(
                    finding_id="opt-001",
                    severity=ResultSeverity.ERROR,
                    message="Missing hull dimensions for optimization",
                ))
                result.state = ValidatorState.FAILED
                result.completed_at = datetime.now(timezone.utc)
                return result

            # Get validators from context or use empty list
            validators = context.get("validators", [])

            # Run optimization
            optimizer = DesignOptimizer(
                problem=problem,
                base_state=state_manager,
                validators=validators,
                population_size=self.population_size,
                max_generations=self.max_generations,
                seed=context.get("seed"),
            )

            opt_result = optimizer.optimize()

            # Validate result
            if opt_result.status == OptimizerStatus.FAILED:
                result.add_finding(ValidationFinding(
                    finding_id="opt-002",
                    severity=ResultSeverity.ERROR,
                    message="Optimization failed",
                ))
                result.state = ValidatorState.FAILED
                result.completed_at = datetime.now(timezone.utc)
                return result

            if not opt_result.pareto_front:
                result.add_finding(ValidationFinding(
                    finding_id="opt-003",
                    severity=ResultSeverity.WARNING,
                    message="Optimization produced no feasible solutions",
                ))

            # Analyze Pareto front
            analyzer = ParetoAnalyzer(problem)
            metrics = analyzer.compute_metrics(opt_result.pareto_front)

            # Write results - Hole #7 Fix: Use .set() with proper source
            source = "optimization/validator"

            # Problem definition
            state_manager.set(
                "optimization.problem",
                determinize_dict(problem.to_dict()),
                source
            )

            # Full result
            state_manager.set(
                "optimization.result",
                determinize_dict(opt_result.to_dict()),
                source
            )

            # Pareto front
            pareto_data = [s.to_dict() for s in opt_result.pareto_front]
            state_manager.set(
                "optimization.pareto_front",
                determinize_dict({"solutions": pareto_data}),
                source
            )

            # Selected solution
            if opt_result.selected_solution:
                state_manager.set(
                    "optimization.selected_solution",
                    determinize_dict(opt_result.selected_solution.to_dict()),
                    source
                )

            # Status and statistics
            state_manager.set("optimization.status", opt_result.status.value, source)

            state_manager.set("optimization.iterations", opt_result.iterations, source)

            state_manager.set("optimization.evaluations", opt_result.evaluations, source)

            # Metrics
            state_manager.set(
                "optimization.metrics",
                determinize_dict(metrics.to_dict()),
                source
            )

            # Set result state
            if result.error_count > 0:
                result.state = ValidatorState.FAILED
            elif result.warning_count > 0:
                result.state = ValidatorState.WARNING
            else:
                result.state = ValidatorState.PASSED

            logger.debug(
                f"Optimization complete: {opt_result.iterations} iterations, "
                f"{len(opt_result.pareto_front)} Pareto solutions"
            )

        except Exception as e:
            result.state = ValidatorState.ERROR
            result.error_message = str(e)
            logger.error(f"Optimization validation failed: {e}")

        result.completed_at = datetime.now(timezone.utc)
        return result


# Validator definition
OPTIMIZATION_DEFINITION = ValidatorDefinition(
    validator_id="optimization/design",
    name="Design Optimization",
    description="Multi-objective design optimization using NSGA-II",
    category=ValidatorCategory.OPTIMIZATION,
    priority=ValidatorPriority.LOW,
    phase="optimization",
    is_gate_condition=False,
    depends_on_parameters=[
        "hull.lwl",
        "hull.beam",
        "hull.depth",
        "cost.total_price",
        "weight.lightship_mt",
    ],
    produces_parameters=[
        "optimization.problem",
        "optimization.result",
        "optimization.pareto_front",
        "optimization.selected_solution",
        "optimization.status",
    ],
    timeout_seconds=600,  # 10 minutes for optimization
    tags=["optimization", "nsga-ii", "pareto", "multi-objective"],
)


def get_optimization_definition() -> ValidatorDefinition:
    """Get validator definition for optimization."""
    return OPTIMIZATION_DEFINITION


def register_optimization_validators(registry: Dict[str, ValidatorInterface]) -> None:
    """Register optimization validators with a registry."""
    defn = get_optimization_definition()
    registry[defn.validator_id] = OptimizationValidator(defn)
