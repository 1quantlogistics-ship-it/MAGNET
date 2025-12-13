"""
MAGNET Stability Validators

Module 06 v1.2 - Production-Ready

Implements ValidatorInterface for stability calculations.

v1.2 Changes:
- KG sourcing priority: stability.kg_m then weight.lightship_vcg_m
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

from .calculators import (
    IntactGMCalculator,
    GZCurveCalculator,
    DamageStabilityCalculator,
    WeatherCriterionCalculator,
)
from .constants import IMO_INTACT

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger(__name__)


# =============================================================================
# INTACT GM VALIDATOR
# =============================================================================

class IntactGMValidator(ValidatorInterface):
    """
    Validator that calculates intact metacentric height (GM).

    v1.2: KG sourcing priority:
    1. stability.kg_m (allows loading condition updates)
    2. weight.lightship_vcg_m (fallback from weight estimation)

    Reads:
        hull.kb_m (or hull.vcb_m), hull.bm_m (or hull.bmt),
        stability.kg_m OR weight.lightship_vcg_m

    Writes:
        stability.gm_transverse_m, stability.kg_m, stability.kb_m,
        stability.bm_m, stability.gm_corrected_m
    """

    def __init__(self, definition: Optional[ValidatorDefinition] = None):
        if definition is None:
            definition = get_intact_gm_definition()
        super().__init__(definition)
        self._calculator = IntactGMCalculator()

    def validate(
        self,
        state_manager: "StateManager",
        context: Dict[str, Any]
    ) -> ValidationResult:
        """
        Calculate GM and write results to state.

        FIX #5: Returns FAILED for validation failures, raises for code failures.
        """
        started_at = datetime.utcnow()
        start_time = time.perf_counter()
        findings: List[ValidationFinding] = []

        try:
            # Read hydrostatics inputs
            # Try both naming conventions (hull.kb_m and hull.vcb_m)
            kb_m = state_manager.get("hull.kb_m")
            if kb_m is None:
                kb_m = state_manager.get("hull.vcb_m")

            bm_m = state_manager.get("hull.bm_m")
            if bm_m is None:
                bm_m = state_manager.get("hull.bmt")

            # KG sourcing priority (v1.2)
            kg_m = None
            kg_source = "unknown"

            # 1. Primary: stability.kg_m
            kg_m = state_manager.get("stability.kg_m")
            if kg_m is not None and kg_m > 0:
                kg_source = "stability.kg_m"
            else:
                # 2. Fallback: weight.lightship_vcg_m
                kg_m = state_manager.get("weight.lightship_vcg_m")
                if kg_m is not None and kg_m > 0:
                    kg_source = "weight.lightship_vcg_m"
                else:
                    # 3. Estimate from hull depth
                    depth = state_manager.get("hull.depth")
                    if depth is not None and depth > 0:
                        kg_m = 0.55 * depth  # Typical KG ~ 55% of depth
                        kg_source = "estimated"
                        findings.append(ValidationFinding(
                            finding_id=str(uuid.uuid4())[:8],
                            severity=ResultSeverity.WARNING,
                            message=f"KG estimated as 55% of depth: {kg_m:.3f}m",
                            suggestion="Provide stability.kg_m or weight.lightship_vcg_m",
                        ))

            # Validate required inputs
            missing = []
            if kb_m is None or kb_m < 0:
                missing.append("hull.kb_m (center of buoyancy)")
            if bm_m is None or bm_m < 0:
                missing.append("hull.bm_m (metacentric radius)")
            if kg_m is None or kg_m < 0:
                missing.append("KG (stability.kg_m or weight.lightship_vcg_m)")

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
                    suggestion="Run physics/hydrostatics validator first",
                ))
                return result

            # Calculate GM
            gm_results = self._calculator.calculate(
                kb_m=kb_m,
                bm_m=bm_m,
                kg_m=kg_m,
                fsc_m=0.0,  # FSC would require tank data
                kg_source=kg_source,
            )

            # Write outputs to state
            source = "stability/intact_gm"
            state_manager.set("stability.gm_transverse_m", gm_results.gm_m, source)
            state_manager.set("stability.gm_corrected_m", gm_results.gm_m, source)
            state_manager.set("stability.kg_m", gm_results.kg_m, source)
            state_manager.set("stability.kb_m", gm_results.kb_m, source)
            state_manager.set("stability.bm_m", gm_results.bm_m, source)

            # Log KG source for traceability
            logger.info(f"GM calculated using KG from {kg_source}: {gm_results.kg_m:.3f}m")

            # Add warnings from calculator
            state = ValidatorState.PASSED
            for warning in gm_results.warnings:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=warning,
                ))
                state = ValidatorState.WARNING

            # Check IMO criterion
            if not gm_results.passes_gm_criterion:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=f"GM ({gm_results.gm_m:.3f}m) below IMO minimum ({IMO_INTACT.gm_min_m}m)",
                    parameter_path="stability.gm_transverse_m",
                    actual_value=gm_results.gm_m,
                    expected_value=f">= {IMO_INTACT.gm_min_m}m",
                ))
                state = ValidatorState.WARNING

            # Add passed finding
            findings.append(ValidationFinding(
                finding_id=str(uuid.uuid4())[:8],
                severity=ResultSeverity.PASSED,
                message=f"GM calculated: {gm_results.gm_m:.3f}m (KG from {kg_source})",
            ))

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            result = ValidationResult(
                validator_id=self.definition.validator_id,
                state=state,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                execution_time_ms=elapsed_ms,
            )
            for finding in findings:
                result.add_finding(finding)

            return result

        except ValueError as e:
            # Validation failure
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
            logger.exception(f"IntactGM validator error: {e}")
            raise


# =============================================================================
# GZ CURVE VALIDATOR
# =============================================================================

class GZCurveValidator(ValidatorInterface):
    """
    Validator that generates GZ curve and checks IMO criteria.

    Reads:
        stability.gm_transverse_m, stability.bm_m (or hull.bm_m)

    Writes:
        stability.gz_curve, stability.gz_max_m, stability.angle_of_max_gz_deg,
        stability.area_0_30_m_rad, stability.area_0_40_m_rad, stability.area_30_40_m_rad,
        stability.angle_of_vanishing_stability_deg, stability.imo_intact_passed
    """

    def __init__(self, definition: Optional[ValidatorDefinition] = None):
        if definition is None:
            definition = get_gz_curve_definition()
        super().__init__(definition)
        self._calculator = GZCurveCalculator()

    def validate(
        self,
        state_manager: "StateManager",
        context: Dict[str, Any]
    ) -> ValidationResult:
        """Generate GZ curve and write results to state."""
        started_at = datetime.utcnow()
        start_time = time.perf_counter()
        findings: List[ValidationFinding] = []

        try:
            # Read GM
            gm_m = state_manager.get("stability.gm_transverse_m")
            if gm_m is None:
                gm_m = state_manager.get("stability.gm_corrected_m")

            # Read BM
            bm_m = state_manager.get("stability.bm_m")
            if bm_m is None:
                bm_m = state_manager.get("hull.bm_m")

            # Validate inputs
            missing = []
            if gm_m is None:
                missing.append("stability.gm_transverse_m (run intact_gm first)")
            if bm_m is None:
                missing.append("stability.bm_m")

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
                ))
                return result

            # Calculate GZ curve
            gz_results = self._calculator.calculate(gm_m=gm_m, bm_m=bm_m)

            # Write outputs to state
            # Convert curve to list of dicts for storage
            source = "stability/gz_curve"
            curve_data = [p.to_dict() for p in gz_results.curve]
            state_manager.set("stability.gz_curve", curve_data, source)
            state_manager.set("stability.gz_max_m", gz_results.gz_max_m, source)
            state_manager.set("stability.angle_of_max_gz_deg", gz_results.angle_gz_max_deg, source)
            state_manager.set("stability.area_0_30_m_rad", gz_results.area_0_30_m_rad, source)
            state_manager.set("stability.area_0_40_m_rad", gz_results.area_0_40_m_rad, source)
            state_manager.set("stability.area_30_40_m_rad", gz_results.area_30_40_m_rad, source)
            state_manager.set("stability.angle_of_vanishing_stability_deg",
                            gz_results.angle_of_vanishing_stability_deg, source)
            state_manager.set("stability.dynamic_stability_m_rad",
                            gz_results.dynamic_stability_m_rad, source)
            state_manager.set("stability.imo_intact_passed", gz_results.passes_all_gz_criteria, source)

            # Add warnings from calculator
            state = ValidatorState.PASSED
            for warning in gz_results.warnings:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=warning,
                ))
                state = ValidatorState.WARNING

            # Check overall criteria
            if not gz_results.passes_all_gz_criteria:
                state = ValidatorState.WARNING

            # Add passed finding
            findings.append(ValidationFinding(
                finding_id=str(uuid.uuid4())[:8],
                severity=ResultSeverity.PASSED,
                message=f"GZ curve generated: max={gz_results.gz_max_m:.3f}m at {gz_results.angle_gz_max_deg:.1f}°",
            ))

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            result = ValidationResult(
                validator_id=self.definition.validator_id,
                state=state,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                execution_time_ms=elapsed_ms,
            )
            for finding in findings:
                result.add_finding(finding)

            return result

        except ValueError as e:
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
            logger.exception(f"GZCurve validator error: {e}")
            raise


# =============================================================================
# DAMAGE STABILITY VALIDATOR
# =============================================================================

class DamageStabilityValidator(ValidatorInterface):
    """
    Validator that evaluates damage stability cases.

    Uses simplified lost buoyancy method.

    Reads:
        stability.gm_transverse_m, stability.gz_max_m, hull.displacement_mt

    Writes:
        stability.damage_cases, stability.damage_gm_min_m, stability.imo_damage_passed
    """

    def __init__(self, definition: Optional[ValidatorDefinition] = None):
        if definition is None:
            definition = get_damage_stability_definition()
        super().__init__(definition)
        self._calculator = DamageStabilityCalculator()

    def validate(
        self,
        state_manager: "StateManager",
        context: Dict[str, Any]
    ) -> ValidationResult:
        """Evaluate damage stability and write results to state."""
        started_at = datetime.utcnow()
        start_time = time.perf_counter()
        findings: List[ValidationFinding] = []

        try:
            # Read inputs
            gm_m = state_manager.get("stability.gm_transverse_m")
            gz_max_m = state_manager.get("stability.gz_max_m")
            displacement_mt = state_manager.get("hull.displacement_mt")

            # Validate
            missing = []
            if gm_m is None:
                missing.append("stability.gm_transverse_m")
            if gz_max_m is None:
                missing.append("stability.gz_max_m (run gz_curve first)")
            if displacement_mt is None:
                displacement_mt = state_manager.get("hull.displacement_m3")
                if displacement_mt:
                    displacement_mt *= 1.025  # Convert volume to mass

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
                ))
                return result

            # Calculate damage stability
            damage_results = self._calculator.calculate(
                intact_gm_m=gm_m,
                intact_gz_max_m=gz_max_m,
                displacement_mt=displacement_mt or 0.0,
            )

            # Write outputs
            source = "stability/damage"
            case_dicts = [c.to_dict() for c in damage_results.cases]
            state_manager.set("stability.damage_cases", case_dicts, source)
            state_manager.set("stability.damage_gm_min_m", damage_results.worst_gm_m, source)
            state_manager.set("stability.imo_damage_passed", damage_results.all_cases_pass, source)

            # Add warnings
            state = ValidatorState.PASSED
            for warning in damage_results.warnings:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=warning,
                ))
                state = ValidatorState.WARNING

            if not damage_results.all_cases_pass:
                state = ValidatorState.WARNING
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=f"Failed damage cases: {damage_results.failed_cases}",
                ))

            findings.append(ValidationFinding(
                finding_id=str(uuid.uuid4())[:8],
                severity=ResultSeverity.PASSED,
                message=f"Damage stability: {damage_results.cases_evaluated} cases, "
                        f"worst GM={damage_results.worst_gm_m:.3f}m",
            ))

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            result = ValidationResult(
                validator_id=self.definition.validator_id,
                state=state,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                execution_time_ms=elapsed_ms,
            )
            for finding in findings:
                result.add_finding(finding)

            return result

        except ValueError as e:
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
            logger.exception(f"DamageStability validator error: {e}")
            raise


# =============================================================================
# WEATHER CRITERION VALIDATOR
# =============================================================================

class WeatherCriterionValidator(ValidatorInterface):
    """
    Validator that checks IMO weather criterion.

    Reads:
        stability.gm_transverse_m, stability.gz_curve, hull dimensions

    Writes:
        stability.steady_wind_heel_deg, weather criterion pass/fail
    """

    def __init__(self, definition: Optional[ValidatorDefinition] = None):
        if definition is None:
            definition = get_weather_criterion_definition()
        super().__init__(definition)
        self._calculator = WeatherCriterionCalculator()

    def validate(
        self,
        state_manager: "StateManager",
        context: Dict[str, Any]
    ) -> ValidationResult:
        """Check weather criterion and write results to state."""
        started_at = datetime.utcnow()
        start_time = time.perf_counter()
        findings: List[ValidationFinding] = []

        try:
            # Read inputs
            gm_m = state_manager.get("stability.gm_transverse_m")
            bm_m = state_manager.get("stability.bm_m")
            gz_curve_data = state_manager.get("stability.gz_curve")
            displacement_mt = state_manager.get("hull.displacement_mt")
            beam_m = state_manager.get("hull.beam")
            draft_m = state_manager.get("hull.draft")
            loa_m = state_manager.get("hull.loa")

            # SENIOR AUDIT FIX: Check displacement before calculation to prevent ZeroDivisionError
            if displacement_mt is None or displacement_mt <= 0:
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
                    message=f"Invalid displacement: {displacement_mt}. Displacement must be > 0 for weather criterion.",
                    parameter_path="hull.displacement_mt",
                    suggestion="Run hull phase to calculate displacement",
                ))
                return result

            # Need GZ curve results
            if gz_curve_data is None or gm_m is None:
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
                    message="Missing GZ curve or GM (run gz_curve first)",
                ))
                return result

            # Recreate GZ curve results for calculator
            from .results import GZCurveResults, GZCurvePoint
            gz_results = GZCurveResults()
            gz_results.curve = [
                GZCurvePoint(
                    heel_deg=p.get("heel_deg", 0),
                    heel_rad=p.get("heel_rad", 0),
                    gz_m=p.get("gz_m", 0)
                )
                for p in gz_curve_data
            ]
            gz_results.area_0_30_m_rad = state_manager.get("stability.area_0_30_m_rad", 0.0)

            # Calculate weather criterion
            weather_results = self._calculator.calculate(
                gz_curve=gz_results,
                displacement_mt=displacement_mt or 0.0,
                beam_m=beam_m or 0.0,
                draft_m=draft_m or 0.0,
                loa_m=loa_m or 0.0,
                gm_m=gm_m,
            )

            # Write outputs
            source = "stability/weather_criterion"
            state_manager.set("stability.steady_wind_heel_deg", weather_results.steady_wind_heel_deg, source)
            state_manager.set("stability.weather_criterion_ratio", weather_results.energy_ratio, source)
            state_manager.set("stability.weather_criterion_passed", weather_results.passes_criterion, source)

            # Add warnings
            state = ValidatorState.PASSED
            for warning in weather_results.warnings:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=warning,
                ))

            if not weather_results.passes_criterion:
                state = ValidatorState.WARNING
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=f"Weather criterion not met: b/a = {weather_results.energy_ratio:.2f}",
                ))

            findings.append(ValidationFinding(
                finding_id=str(uuid.uuid4())[:8],
                severity=ResultSeverity.PASSED if weather_results.passes_criterion else ResultSeverity.INFO,
                message=f"Weather criterion: b/a = {weather_results.energy_ratio:.2f}",
            ))

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            result = ValidationResult(
                validator_id=self.definition.validator_id,
                state=state,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                execution_time_ms=elapsed_ms,
            )
            for finding in findings:
                result.add_finding(finding)

            return result

        except ValueError as e:
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
            logger.exception(f"WeatherCriterion validator error: {e}")
            raise


# =============================================================================
# VALIDATOR DEFINITIONS
# =============================================================================

def get_intact_gm_definition() -> ValidatorDefinition:
    """Get validator definition for intact GM calculator."""
    return ValidatorDefinition(
        validator_id="stability/intact_gm",
        name="Intact GM Calculator",
        description="Calculates metacentric height for intact stability",
        category=ValidatorCategory.STABILITY,
        priority=ValidatorPriority.CRITICAL,
        phase="stability",
        is_gate_condition=True,
        depends_on_validators=["physics/hydrostatics"],
        depends_on_parameters=[
            "hull.kb_m", "hull.bm_m",
            "stability.kg_m", "weight.lightship_vcg_m",
        ],
        produces_parameters=[
            "stability.gm_transverse_m",
            "stability.kg_m",
            "stability.kb_m",
            "stability.bm_m",
            "stability.gm_corrected_m",
        ],
        timeout_seconds=60,
        tags=["stability", "intact", "gm"],
    )


def get_gz_curve_definition() -> ValidatorDefinition:
    """Get validator definition for GZ curve generator."""
    return ValidatorDefinition(
        validator_id="stability/gz_curve",
        name="GZ Curve Generator",
        description="Generates righting arm curve across heel angles",
        category=ValidatorCategory.STABILITY,
        priority=ValidatorPriority.HIGH,
        phase="stability",
        is_gate_condition=True,
        depends_on_validators=["stability/intact_gm"],
        depends_on_parameters=[
            "stability.gm_transverse_m", "stability.bm_m",
        ],
        produces_parameters=[
            "stability.gz_curve",
            "stability.gz_max_m",
            "stability.angle_of_max_gz_deg",
            "stability.area_0_30_m_rad",
            "stability.area_0_40_m_rad",
            "stability.area_30_40_m_rad",
            "stability.angle_of_vanishing_stability_deg",
            "stability.imo_intact_passed",
        ],
        timeout_seconds=120,
        resource_requirements=ResourceRequirements(cpu_cores=2, ram_gb=1.5),
        tags=["stability", "gz", "imo"],
    )


def get_damage_stability_definition() -> ValidatorDefinition:
    """Get validator definition for damage stability."""
    return ValidatorDefinition(
        validator_id="stability/damage",
        name="Damage Stability Analysis",
        description="Evaluates stability under damaged conditions",
        category=ValidatorCategory.STABILITY,
        priority=ValidatorPriority.HIGH,
        phase="stability",
        is_gate_condition=True,
        depends_on_validators=["stability/gz_curve"],
        depends_on_parameters=[
            "stability.gm_transverse_m", "stability.gz_max_m",
            "hull.displacement_mt",
        ],
        produces_parameters=[
            "stability.damage_cases",
            "stability.damage_gm_min_m",
            "stability.imo_damage_passed",
        ],
        timeout_seconds=300,
        resource_requirements=ResourceRequirements(cpu_cores=4, ram_gb=4.0),
        tags=["stability", "damage", "compliance"],
    )


def get_weather_criterion_definition() -> ValidatorDefinition:
    """Get validator definition for weather criterion."""
    return ValidatorDefinition(
        validator_id="stability/weather_criterion",
        name="Weather Criterion Check",
        description="IMO weather criterion (wind heeling vs GZ)",
        category=ValidatorCategory.STABILITY,
        priority=ValidatorPriority.NORMAL,
        phase="stability",
        is_gate_condition=True,
        gate_severity=ResultSeverity.WARNING,
        depends_on_validators=["stability/gz_curve"],
        depends_on_parameters=[
            "stability.gm_transverse_m", "stability.gz_curve",
            "hull.loa", "hull.beam", "hull.draft",
        ],
        produces_parameters=[
            "stability.steady_wind_heel_deg",
        ],
        timeout_seconds=60,
        tags=["stability", "imo", "weather"],
    )


# =============================================================================
# REGISTRATION
# =============================================================================

def register_stability_validators(registry) -> None:
    """
    Register all stability validators with a validator registry.

    Args:
        registry: ValidatorRegistry instance
    """
    # Register intact GM
    intact_gm_def = get_intact_gm_definition()
    registry.register(intact_gm_def, IntactGMValidator)

    # Register GZ curve
    gz_curve_def = get_gz_curve_definition()
    registry.register(gz_curve_def, GZCurveValidator)

    # Register damage stability
    damage_def = get_damage_stability_definition()
    registry.register(damage_def, DamageStabilityValidator)

    # Register weather criterion
    weather_def = get_weather_criterion_definition()
    registry.register(weather_def, WeatherCriterionValidator)

    logger.info("Registered stability validators: intact_gm, gz_curve, damage, weather_criterion")
