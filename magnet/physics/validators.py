"""
MAGNET Physics Validators

Module 05 v1.2 - Production-Ready

Implements ValidatorInterface for physics calculations.

v1.2 Changes:
- HydrostaticsValidator writes 11 outputs (up from 6)
- ResistanceValidator with Holtrop-Mennen calculations
- FIX #5: FAILED for validation failures, raise for code failures
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import time
import logging
import uuid

from magnet.validators.taxonomy import (
    ValidatorInterface,
    ValidatorDefinition,
    ValidationResult,
    ValidationFinding,
    ValidatorState,
    ResultSeverity,
    ValidatorCategory,
    ValidatorPriority,
    ResourceRequirements,
)

from .hydrostatics import HydrostaticsCalculator, HYDROSTATICS_OUTPUTS
from .resistance import ResistanceCalculator, RESISTANCE_OUTPUTS

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger(__name__)


# =============================================================================
# HYDROSTATICS VALIDATOR (v1.2)
# =============================================================================

class HydrostaticsValidator(ValidatorInterface):
    """
    Validator that computes hydrostatics and writes results to state.

    v1.2: Now produces 11 output fields for stability calculations.

    Reads:
        hull.lwl, hull.beam, hull.draft, hull.depth, hull.cb,
        hull.cp, hull.cm, hull.cwp, hull.hull_type, hull.deadrise_deg

    Writes:
        hull.displacement_m3, hull.kb_m, hull.bm_m, hull.lcb_from_ap_m,
        hull.vcb_m, hull.tpc, hull.mct, hull.lcf_from_ap_m,
        hull.waterplane_area_m2, hull.wetted_surface_m2, hull.freeboard
    """

    def __init__(self, definition: Optional[ValidatorDefinition] = None):
        """Initialize with optional custom definition."""
        if definition is None:
            definition = get_hydrostatics_definition()
        super().__init__(definition)
        self._calculator = HydrostaticsCalculator()

    def validate(
        self,
        state_manager: "StateManager",
        context: Dict[str, Any]
    ) -> ValidationResult:
        """
        Run hydrostatics calculations and write results to state.

        FIX #5:
        - Returns FAILED for validation failures (invalid inputs)
        - Returns PASSED/WARNING for success
        - Raises exceptions for code failures (will be retried)

        Args:
            state_manager: StateManager instance for reading/writing
            context: Execution context (unused currently)

        Returns:
            ValidationResult with findings
        """
        started_at = datetime.utcnow()
        start_time = time.perf_counter()
        findings: List[ValidationFinding] = []

        try:
            # Read required inputs
            lwl = state_manager.get("hull.lwl")
            beam = state_manager.get("hull.beam")
            draft = state_manager.get("hull.draft")
            depth = state_manager.get("hull.depth")
            cb = state_manager.get("hull.cb")

            # Read optional inputs
            cp = state_manager.get("hull.cp")
            cm = state_manager.get("hull.cm")
            cwp = state_manager.get("hull.cwp")
            hull_type = state_manager.get("hull.hull_type", "monohull")
            deadrise_deg = state_manager.get("hull.deadrise_deg", 0.0)

            # Validate required inputs
            missing = []
            if lwl is None or lwl <= 0:
                missing.append("hull.lwl")
            if beam is None or beam <= 0:
                missing.append("hull.beam")
            if draft is None or draft <= 0:
                missing.append("hull.draft")
            if cb is None or cb <= 0:
                missing.append("hull.cb")

            if missing:
                # FIX #5: Return FAILED for validation failure (not exception)
                result = ValidationResult(
                    validator_id=self.definition.validator_id,
                    state=ValidatorState.FAILED,
                    started_at=started_at,
                    completed_at=datetime.utcnow(),
                    execution_time_ms=int((time.perf_counter() - start_time) * 1000),
                )
                result.add_finding(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.ERROR,
                    message=f"Missing required parameters: {', '.join(missing)}",
                    suggestion="Provide valid positive values for all required hull parameters",
                ))
                return result

            # Default depth if not provided
            if depth is None or depth <= 0:
                depth = draft + 1.5  # Default 1.5m freeboard

            # Run calculation (may raise for code failures - will be retried)
            results = self._calculator.calculate(
                lwl=lwl,
                beam=beam,
                draft=draft,
                depth=depth,
                cb=cb,
                cp=cp,
                cm=cm,
                cwp=cwp,
                hull_type=hull_type,
                deadrise_deg=deadrise_deg,
            )

            # Write ALL outputs to state (v1.2: 11 outputs + canonical aliases)
            # Nomenclature note:
            # - KB = VCB = Vertical Center of Buoyancy (height above keel)
            # - BM = BMT = Transverse Metacentric Radius
            # - BML = Longitudinal Metacentric Radius
            source = "physics/hydrostatics"
            state_manager.set("hull.displacement_m3", results.volume_displaced_m3, source)

            # Canonical paths (contracts/tests expect these names)
            state_manager.set("hull.kb_m", results.vcb_m, source)   # KB = VCB (verified in hydrostatics.py:94,298)
            state_manager.set("hull.bm_m", results.bm_m, source)    # BM canonical

            # Legacy aliases (backward compatibility for existing code)
            state_manager.set("hull.vcb_m", results.vcb_m, source)  # Alias for KB
            state_manager.set("hull.bmt", results.bm_m, source)     # Alias for BM

            state_manager.set("hull.lcb_from_ap_m", results.lcb_m, source)
            state_manager.set("hull.tpc", results.tpc, source)
            state_manager.set("hull.mct", results.mct, source)
            state_manager.set("hull.lcf_from_ap_m", results.lcf_m, source)
            state_manager.set("hull.waterplane_area_m2", results.waterplane_area_m2, source)
            state_manager.set("hull.wetted_surface_m2", results.wetted_surface_m2, source)
            state_manager.set("hull.freeboard", results.freeboard_m, source)

            # Also write displacement in metric tonnes (commonly needed)
            state_manager.set("hull.displacement_mt", results.displacement_mt, source)

            # Add findings for any calculator warnings
            state = ValidatorState.PASSED
            for warning in results.warnings:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=warning,
                ))
                state = ValidatorState.WARNING

            # Check for negative freeboard
            if results.freeboard_m < 0:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=f"Negative freeboard: {results.freeboard_m:.3f}m. Depth < Draft.",
                    parameter_path="hull.freeboard",
                    actual_value=results.freeboard_m,
                    suggestion="Increase hull depth or reduce draft",
                ))
                state = ValidatorState.WARNING

            # Create success result
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            result = ValidationResult(
                validator_id=self.definition.validator_id,
                state=state,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                execution_time_ms=elapsed_ms,
            )

            # Add passed finding
            findings.append(ValidationFinding(
                finding_id=str(uuid.uuid4())[:8],
                severity=ResultSeverity.PASSED,
                message=f"Hydrostatics computed: displacement={results.displacement_mt:.2f}t, "
                        f"KB={results.kb_m:.3f}m, BM={results.bm_m:.3f}m",
            ))

            for finding in findings:
                result.add_finding(finding)

            return result

        except ValueError as e:
            # FIX #5: ValueError is a validation failure - return FAILED, don't retry
            result = ValidationResult(
                validator_id=self.definition.validator_id,
                state=ValidatorState.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                execution_time_ms=int((time.perf_counter() - start_time) * 1000),
            )
            result.add_finding(ValidationFinding(
                finding_id=str(uuid.uuid4())[:8],
                severity=ResultSeverity.ERROR,
                message=str(e),
            ))
            return result

        except Exception as e:
            # FIX #5: Other exceptions are code failures - raise to trigger retry
            logger.exception(f"Hydrostatics validator error: {e}")
            raise


# =============================================================================
# RESISTANCE VALIDATOR
# =============================================================================

class ResistanceValidator(ValidatorInterface):
    """
    Validator that computes hull resistance using Holtrop-Mennen method.

    Depends on hydrostatics outputs (implicit dependency).

    Reads:
        hull.lwl, hull.beam, hull.draft, hull.displacement_mt,
        hull.wetted_surface_m2, hull.cb, mission.max_speed_kts

    Writes:
        resistance.total_kn, resistance.frictional_kn, resistance.residuary_kn,
        resistance.effective_power_kw, resistance.froude_number, resistance.reynolds_number
    """

    def __init__(self, definition: Optional[ValidatorDefinition] = None):
        """Initialize with optional custom definition."""
        if definition is None:
            definition = get_resistance_definition()
        super().__init__(definition)
        self._calculator = ResistanceCalculator()

    def validate(
        self,
        state_manager: "StateManager",
        context: Dict[str, Any]
    ) -> ValidationResult:
        """
        Run resistance calculations and write results to state.

        FIX #5:
        - Returns FAILED for validation failures (missing inputs)
        - Returns WARNING for high Froude number
        - Raises exceptions for code failures

        Args:
            state_manager: StateManager instance
            context: Execution context

        Returns:
            ValidationResult
        """
        started_at = datetime.utcnow()
        start_time = time.perf_counter()
        findings: List[ValidationFinding] = []

        try:
            # Read hull dimensions
            lwl = state_manager.get("hull.lwl")
            beam = state_manager.get("hull.beam")
            draft = state_manager.get("hull.draft")
            cb = state_manager.get("hull.cb")

            # Read hydrostatics outputs (implicit dependency)
            displacement_mt = state_manager.get("hull.displacement_mt")
            wetted_surface = state_manager.get("hull.wetted_surface_m2")

            # Read mission parameter
            speed_kts = state_manager.get("mission.max_speed_kts")

            # Validate required inputs
            missing = []
            if lwl is None or lwl <= 0:
                missing.append("hull.lwl")
            if beam is None or beam <= 0:
                missing.append("hull.beam")
            if draft is None or draft <= 0:
                missing.append("hull.draft")
            if cb is None or cb <= 0:
                missing.append("hull.cb")
            if displacement_mt is None or displacement_mt <= 0:
                missing.append("hull.displacement_mt (run hydrostatics first)")
            if wetted_surface is None or wetted_surface <= 0:
                missing.append("hull.wetted_surface_m2 (run hydrostatics first)")
            if speed_kts is None or speed_kts <= 0:
                missing.append("mission.max_speed_kts")

            if missing:
                result = ValidationResult(
                    validator_id=self.definition.validator_id,
                    state=ValidatorState.FAILED,
                    started_at=started_at,
                    completed_at=datetime.utcnow(),
                    execution_time_ms=int((time.perf_counter() - start_time) * 1000),
                )
                result.add_finding(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.ERROR,
                    message=f"Missing required parameters: {', '.join(missing)}",
                    suggestion="Ensure hull dimensions and hydrostatics are computed first",
                ))
                return result

            # Run resistance calculation
            results = self._calculator.calculate(
                lwl=lwl,
                beam=beam,
                draft=draft,
                displacement_mt=displacement_mt,
                wetted_surface=wetted_surface,
                speed_kts=speed_kts,
                cb=cb,
            )

            # Write outputs to state
            source = "physics/resistance"
            state_manager.set("resistance.total_kn", results.total_kn, source)
            state_manager.set("resistance.frictional_kn", results.frictional_kn, source)
            state_manager.set("resistance.residuary_kn", results.residuary_kn, source)
            state_manager.set("resistance.effective_power_kw", results.effective_power_kw, source)
            state_manager.set("resistance.froude_number", results.froude_number, source)
            state_manager.set("resistance.reynolds_number", results.reynolds_number, source)

            # Also write additional useful outputs
            state_manager.set("resistance.total_n", results.total_n, source)
            state_manager.set("resistance.effective_power_hp", results.effective_power_hp, source)

            # Add calculator warnings as findings
            state = ValidatorState.PASSED
            for warning in results.warnings:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=warning,
                ))
                state = ValidatorState.WARNING

            # Add specific warning for high Froude number
            if results.froude_number > 0.5:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=f"Froude number {results.froude_number:.3f} > 0.5: "
                            "Results less accurate in semi-planing/planing regime",
                    parameter_path="resistance.froude_number",
                    actual_value=results.froude_number,
                    suggestion="Consider planing hull resistance methods for high-speed vessels",
                ))
                state = ValidatorState.WARNING

            # Create success result
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            result = ValidationResult(
                validator_id=self.definition.validator_id,
                state=state,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                execution_time_ms=elapsed_ms,
            )

            # Add passed finding
            findings.append(ValidationFinding(
                finding_id=str(uuid.uuid4())[:8],
                severity=ResultSeverity.PASSED,
                message=f"Resistance computed: Rt={results.total_kn:.2f}kN, "
                        f"Pe={results.effective_power_kw:.1f}kW, Fn={results.froude_number:.3f}",
            ))

            for finding in findings:
                result.add_finding(finding)

            return result

        except ValueError as e:
            # Validation failure - don't retry
            result = ValidationResult(
                validator_id=self.definition.validator_id,
                state=ValidatorState.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                execution_time_ms=int((time.perf_counter() - start_time) * 1000),
            )
            result.add_finding(ValidationFinding(
                finding_id=str(uuid.uuid4())[:8],
                severity=ResultSeverity.ERROR,
                message=str(e),
            ))
            return result

        except Exception as e:
            # Code failure - raise for retry
            logger.exception(f"Resistance validator error: {e}")
            raise


# =============================================================================
# VALIDATOR DEFINITIONS
# =============================================================================

def get_hydrostatics_definition() -> ValidatorDefinition:
    """Get the validator definition for hydrostatics."""
    return ValidatorDefinition(
        validator_id="physics/hydrostatics",
        name="Hydrostatics Calculator",
        description="Computes displacement, centers, stability parameters (v1.2)",
        category=ValidatorCategory.PHYSICS,
        priority=ValidatorPriority.CRITICAL,
        phase="hull_form",
        is_gate_condition=True,
        depends_on_parameters=[
            "hull.loa", "hull.lwl", "hull.beam", "hull.depth", "hull.draft",
            "hull.cb", "hull.cp", "hull.cm", "hull.cwp",
            "hull.hull_type", "hull.deadrise_deg"
        ],
        produces_parameters=[
            "hull.displacement_m3",
            "hull.kb_m",
            "hull.bm_m",
            "hull.lcb_from_ap_m",
            "hull.vcb_m",
            "hull.tpc",
            "hull.mct",
            "hull.lcf_from_ap_m",
            "hull.waterplane_area_m2",
            "hull.wetted_surface_m2",
            "hull.freeboard",
        ],
        timeout_seconds=120,
        resource_requirements=ResourceRequirements(cpu_cores=2, ram_gb=1.0),
        tags=["core", "hull", "buoyancy", "v1.2"],
    )


def get_resistance_definition() -> ValidatorDefinition:
    """Get the validator definition for resistance."""
    return ValidatorDefinition(
        validator_id="physics/resistance",
        name="Resistance Prediction",
        description="Calculates hull resistance using Holtrop-Mennen method",
        category=ValidatorCategory.PHYSICS,
        priority=ValidatorPriority.CRITICAL,
        phase="hull_form",
        is_gate_condition=True,
        depends_on_validators=["physics/hydrostatics"],
        depends_on_parameters=[
            "hull.lwl", "hull.beam", "hull.draft", "hull.cb",
            "hull.displacement_mt", "hull.wetted_surface_m2",
            "mission.max_speed_kts"
        ],
        produces_parameters=[
            "resistance.total_kn",
            "resistance.frictional_kn",
            "resistance.residuary_kn",
            "resistance.effective_power_kw",
            "resistance.froude_number",
            "resistance.reynolds_number",
        ],
        timeout_seconds=180,
        resource_requirements=ResourceRequirements(cpu_cores=2, ram_gb=2.0),
        tags=["core", "hull", "propulsion"],
    )


# =============================================================================
# REGISTRATION HELPER
# =============================================================================

def register_physics_validators(registry) -> None:
    """
    Register all physics validators with a validator registry.

    Args:
        registry: ValidatorRegistry instance from magnet.validators.registry
    """
    # Register hydrostatics
    hydro_def = get_hydrostatics_definition()
    registry.register(hydro_def, HydrostaticsValidator)

    # Register resistance
    res_def = get_resistance_definition()
    registry.register(res_def, ResistanceValidator)

    logger.info(f"Registered physics validators: {hydro_def.validator_id}, {res_def.validator_id}")
