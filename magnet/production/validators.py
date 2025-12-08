"""
production/validators.py - Production planning validators.

BRAVO OWNS THIS FILE.

Module 11 v1.1 - Production planning validation.

v1.1 NOTE: Uses verified field names from structure.*, hull.*, mission.*
"""

from __future__ import annotations
from datetime import datetime, timezone, date
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging

from .enums import MaterialCategory, ProductionPhase
from .models import (
    MaterialTakeoffResult,
    AssemblySequenceResult,
    BuildSchedule,
    ProductionSummary,
)
from .material_takeoff import MaterialTakeoff
from .assembly import AssemblySequencer
from .schedule import BuildScheduler

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
    """
    Make dictionary deterministic for hashing.

    Sorts keys and rounds floats for consistent hash values.
    """
    if isinstance(data, dict):
        return {k: determinize_dict(v, precision) for k, v in sorted(data.items())}
    elif isinstance(data, list):
        return [determinize_dict(item, precision) for item in data]
    elif isinstance(data, float):
        return round(data, precision)
    else:
        return data


class ProductionPlanningValidator(ValidatorInterface):
    """
    Complete production planning validator.

    Generates material takeoff, assembly sequence, and build schedule.

    v1.1 verified field names:
    - structure.material
    - structure.frame_spacing_mm
    - structure.bottom_plate_thickness_mm
    - structure.side_plate_thickness_mm
    - structure.deck_plate_thickness_mm

    Reads:
        hull.lwl, hull.beam, hull.depth
        structure.material, structure.frame_spacing_mm
        structure.bottom_plate_thickness_mm, structure.side_plate_thickness_mm
        structure.deck_plate_thickness_mm
        mission.vessel_type

    Writes:
        production.material_takeoff - Material quantities and weights
        production.assembly_sequence - Work packages and dependencies
        production.build_schedule - Milestones and timeline
        production.summary - Production planning summary
    """

    def __init__(self, definition: ValidatorDefinition):
        super().__init__(definition)
        self._material_takeoff = MaterialTakeoff()
        self._assembly_sequencer = AssemblySequencer()
        self._build_scheduler = BuildScheduler()

    def validate(
        self,
        state_manager: "StateManager",
        context: Dict[str, Any]
    ) -> ValidationResult:
        """Generate and validate production planning."""
        result = ValidationResult(
            validator_id=self.definition.validator_id,
            state=ValidatorState.RUNNING,
            started_at=datetime.now(timezone.utc),
        )

        try:
            # Read inputs
            lwl = state_manager.get("hull.lwl")
            beam = state_manager.get("hull.beam")
            depth = state_manager.get("hull.depth")

            # Validate minimum inputs
            if lwl is None or beam is None or depth is None:
                result.add_finding(ValidationFinding(
                    finding_id="prod-001",
                    severity=ResultSeverity.ERROR,
                    message="Missing hull dimensions for production planning",
                ))
                result.state = ValidatorState.FAILED
                result.completed_at = datetime.now(timezone.utc)
                return result

            if lwl <= 0 or beam <= 0 or depth <= 0:
                result.add_finding(ValidationFinding(
                    finding_id="prod-002",
                    severity=ResultSeverity.ERROR,
                    message=f"Invalid hull dimensions: lwl={lwl}, beam={beam}, depth={depth}",
                ))
                result.state = ValidatorState.FAILED
                result.completed_at = datetime.now(timezone.utc)
                return result

            # Read optional structural parameters (v1.1 verified names)
            material = state_manager.get("structure.material")
            if material is None:
                material = "aluminum_5083"  # Default

            # === MATERIAL TAKEOFF ===
            material_result = self._material_takeoff.calculate(state_manager)

            # Validate material result
            if material_result.item_count == 0:
                result.add_finding(ValidationFinding(
                    finding_id="prod-mat-001",
                    severity=ResultSeverity.WARNING,
                    message="No material items generated",
                ))

            # Check total weight reasonableness
            if material_result.total_weight_kg > 0:
                weight_per_meter = material_result.total_weight_kg / lwl / 1000  # tonnes/m
                if weight_per_meter > 50:  # Very high for any vessel
                    result.add_finding(ValidationFinding(
                        finding_id="prod-mat-002",
                        severity=ResultSeverity.WARNING,
                        message=f"High material weight: {weight_per_meter:.1f} t/m",
                    ))
                elif weight_per_meter < 0.5:  # Very low
                    result.add_finding(ValidationFinding(
                        finding_id="prod-mat-003",
                        severity=ResultSeverity.WARNING,
                        message=f"Low material weight: {weight_per_meter:.1f} t/m",
                    ))

            # === ASSEMBLY SEQUENCE ===
            assembly_result = self._assembly_sequencer.generate_sequence(state_manager)

            # Validate assembly result
            if assembly_result.package_count == 0:
                result.add_finding(ValidationFinding(
                    finding_id="prod-asm-001",
                    severity=ResultSeverity.WARNING,
                    message="No work packages generated",
                ))

            # Check critical path reasonableness
            if assembly_result.critical_path_hours > 0:
                hours_per_meter = assembly_result.critical_path_hours / lwl
                if hours_per_meter > 500:  # Very long
                    result.add_finding(ValidationFinding(
                        finding_id="prod-asm-002",
                        severity=ResultSeverity.INFO,
                        message=f"Long critical path: {hours_per_meter:.0f} hours/m",
                    ))

            # === BUILD SCHEDULE ===
            # Use configured start date or today
            start_date = context.get("start_date")
            if start_date is None:
                start_date = date.today()
            elif isinstance(start_date, str):
                start_date = date.fromisoformat(start_date)

            schedule_result = self._build_scheduler.generate_schedule(
                state_manager,
                assembly_result=assembly_result,
                material_result=material_result,
                start_date=start_date,
            )

            # Validate schedule
            if schedule_result.total_days <= 0:
                result.add_finding(ValidationFinding(
                    finding_id="prod-sch-001",
                    severity=ResultSeverity.WARNING,
                    message="Build schedule has zero duration",
                ))

            # Check schedule reasonableness
            if schedule_result.total_days > 0:
                days_per_meter = schedule_result.total_days / lwl
                if days_per_meter > 30:  # Very long
                    result.add_finding(ValidationFinding(
                        finding_id="prod-sch-002",
                        severity=ResultSeverity.INFO,
                        message=f"Long build duration: {days_per_meter:.1f} days/m",
                    ))
                elif days_per_meter < 1:  # Very short
                    result.add_finding(ValidationFinding(
                        finding_id="prod-sch-003",
                        severity=ResultSeverity.INFO,
                        message=f"Short build duration: {days_per_meter:.1f} days/m",
                    ))

            # === WRITE RESULTS ===
            agent = "production/planning"

            # Material takeoff
            material_data = material_result.to_dict()
            state_manager.write(
                "production.material_takeoff",
                determinize_dict(material_data),
                agent,
                "Material takeoff quantities and weights"
            )

            # Assembly sequence
            assembly_data = assembly_result.to_dict()
            state_manager.write(
                "production.assembly_sequence",
                determinize_dict(assembly_data),
                agent,
                "Work packages and dependencies"
            )

            # Build schedule
            schedule_data = schedule_result.to_dict()
            state_manager.write(
                "production.build_schedule",
                determinize_dict(schedule_data),
                agent,
                "Build milestones and timeline"
            )

            # Production summary
            summary = ProductionSummary(
                material_weight_kg=material_result.total_weight_kg,
                work_packages=assembly_result.package_count,
                total_work_hours=assembly_result.total_work_hours,
                build_duration_days=schedule_result.total_days,
                estimated_delivery=schedule_result.end_date,
            )
            state_manager.write(
                "production.summary",
                determinize_dict(summary.to_dict()),
                agent,
                "Production planning summary"
            )

            # Set result state
            if result.error_count > 0:
                result.state = ValidatorState.FAILED
            elif result.warning_count > 0:
                result.state = ValidatorState.WARNING
            else:
                result.state = ValidatorState.PASSED

            logger.debug(
                f"Production planning complete: {material_result.item_count} materials, "
                f"{assembly_result.package_count} work packages, "
                f"{schedule_result.total_days} days"
            )

        except Exception as e:
            result.state = ValidatorState.ERROR
            result.error_message = str(e)
            logger.error(f"Production planning failed: {e}")

        result.completed_at = datetime.now(timezone.utc)
        return result


def get_production_planning_definition() -> ValidatorDefinition:
    """Get validator definition for production planning."""
    return ValidatorDefinition(
        validator_id="production/planning",
        name="Production Planning",
        description="Generate material takeoff, assembly sequence, and build schedule",
        category=ValidatorCategory.PRODUCTION,
        priority=ValidatorPriority.LOW,
        phase="production",
        is_gate_condition=False,
        depends_on_parameters=[
            "hull.lwl",
            "hull.beam",
            "hull.depth",
            "structure.material",
            "structure.frame_spacing_mm",
        ],
        produces_parameters=[
            "production.material_takeoff",
            "production.assembly_sequence",
            "production.build_schedule",
            "production.summary",
        ],
        timeout_seconds=120,
        tags=["production", "planning", "material", "schedule"],
    )


def register_production_validators(registry: Dict[str, ValidatorInterface]) -> None:
    """Register production validators with a registry."""
    defn = get_production_planning_definition()
    registry[defn.validator_id] = ProductionPlanningValidator(defn)
