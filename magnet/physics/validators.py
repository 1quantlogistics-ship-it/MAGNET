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
    GateRequirement,  # v1.4
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

            # Check for negative freeboard (v1.3: with adjustment hint)
            if results.freeboard_m < 0:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=f"Negative freeboard: {results.freeboard_m:.3f}m. Depth < Draft.",
                    parameter_path="hull.freeboard",
                    actual_value=results.freeboard_m,
                    suggestion="Increase hull depth or reduce draft",
                    adjustment={"path": "hull.draft", "direction": "decrease", "magnitude": 0.05},
                ))
                state = ValidatorState.WARNING

            # v1.3: L/B ratio check with structured adjustment
            l_b_ratio = lwl / beam if beam > 0 else 0
            if l_b_ratio < 4.0:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=f"L/B ratio {l_b_ratio:.2f} is low - vessel may be unstable",
                    parameter_path="hull.lwl",
                    actual_value=l_b_ratio,
                    expected_value="4.0-7.0",
                    suggestion="Increase length or decrease beam for better stability",
                    adjustment={"path": "hull.lwl", "direction": "increase", "magnitude": 0.05},
                ))
                state = ValidatorState.WARNING
            elif l_b_ratio > 7.0:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=f"L/B ratio {l_b_ratio:.2f} is high - structural concerns",
                    parameter_path="hull.lwl",
                    actual_value=l_b_ratio,
                    expected_value="4.0-7.0",
                    suggestion="Decrease length or increase beam for structural efficiency",
                    adjustment={"path": "hull.lwl", "direction": "decrease", "magnitude": 0.05},
                ))
                state = ValidatorState.WARNING

            # v1.3: BM stability check with adjustment
            if results.bm_m < 0.5:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=f"BM {results.bm_m:.3f}m is low - stability concern",
                    parameter_path="hull.bm_m",
                    actual_value=results.bm_m,
                    expected_value=">0.5m",
                    suggestion="Increase beam to improve transverse stability",
                    adjustment={"path": "hull.beam", "direction": "increase", "magnitude": 0.05},
                ))
                state = ValidatorState.WARNING

            # v1.3: Block coefficient check
            if cb < 0.35:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=f"Block coefficient {cb:.3f} is very low - fine-lined hull",
                    parameter_path="hull.cb",
                    actual_value=cb,
                    expected_value="0.35-0.65",
                    suggestion="Consider if displacement is sufficient for payload requirements",
                    adjustment={"path": "hull.cb", "direction": "increase", "magnitude": 0.02},
                ))
                state = ValidatorState.WARNING
            elif cb > 0.65:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=f"Block coefficient {cb:.3f} is high - full-bodied hull",
                    parameter_path="hull.cb",
                    actual_value=cb,
                    expected_value="0.35-0.65",
                    suggestion="May have high resistance at speed",
                    adjustment={"path": "hull.cb", "direction": "decrease", "magnitude": 0.02},
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

            # v1.3: Froude number checks with structured adjustments
            if results.froude_number > 0.5:
                # High Froude - suggest longer hull to reduce Fn
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=f"Froude number {results.froude_number:.3f} > 0.5: "
                            "Results less accurate in semi-planing/planing regime",
                    parameter_path="resistance.froude_number",
                    actual_value=results.froude_number,
                    expected_value="<0.5 for displacement hull methods",
                    suggestion="Consider planing hull resistance methods or increase hull length",
                    adjustment={"path": "hull.lwl", "direction": "increase", "magnitude": 0.05},
                ))
                state = ValidatorState.WARNING
            elif results.froude_number < 0.2:
                # Low Froude - hull may be oversized for speed
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.INFO,
                    message=f"Froude number {results.froude_number:.3f} < 0.2: "
                            "Hull may be oversized for speed requirement",
                    parameter_path="resistance.froude_number",
                    actual_value=results.froude_number,
                    expected_value="0.2-0.5 for efficient displacement hull",
                    suggestion="Consider shorter hull to improve Froude number efficiency",
                    adjustment={"path": "hull.lwl", "direction": "decrease", "magnitude": 0.05},
                ))

            # v1.3: Specific resistance check (resistance per unit displacement)
            specific_resistance = results.total_kn / (displacement_mt * 9.81 / 1000) if displacement_mt > 0 else 0
            if specific_resistance > 0.1:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=f"High specific resistance: {specific_resistance:.4f} (Rt/Δ)",
                    parameter_path="resistance.total_kn",
                    actual_value=specific_resistance,
                    expected_value="<0.1",
                    suggestion="Slenderer hull (higher L/B) would reduce resistance",
                    adjustment={"path": "hull.lwl", "direction": "increase", "magnitude": 0.03},
                ))
                state = ValidatorState.WARNING

            # v1.3: Power efficiency check
            if displacement_mt > 0 and results.effective_power_kw > 0:
                power_per_tonne = results.effective_power_kw / displacement_mt
                if power_per_tonne > 50:  # High power requirement
                    findings.append(ValidationFinding(
                        finding_id=str(uuid.uuid4())[:8],
                        severity=ResultSeverity.WARNING,
                        message=f"High power requirement: {power_per_tonne:.1f} kW/tonne displacement",
                        parameter_path="resistance.effective_power_kw",
                        actual_value=power_per_tonne,
                        expected_value="<50 kW/tonne",
                        suggestion="Consider hull form optimization or reduce speed requirement",
                        adjustment={"path": "hull.lwl", "direction": "increase", "magnitude": 0.04},
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
# PROPORTIONAL HARMONY VALIDATOR (v1.4)
# =============================================================================

class ProportionalHarmonyValidator(ValidatorInterface):
    """
    Engineering-grounded proportional harmony checks for hull form (v1.4).

    Uses PREFERENCE severity for "could be better but not wrong" findings.
    All checks are grounded in naval architecture principles with explicit
    engineering basis and confidence levels in metadata.

    This validator never blocks phase advancement - it provides advisory
    guidance to improve hull form harmony.

    Checks performed:
    1. L/B ratio vs. Froude regime envelope
    2. Coefficient consistency: Cb = Cp × Cm
    3. Freeboard ratio concept envelope (simplified ICLL approximation)
    """

    def __init__(self, definition: Optional[ValidatorDefinition] = None):
        """Initialize with optional custom definition."""
        if definition is None:
            definition = get_proportional_harmony_definition()
        super().__init__(definition)

    def validate(
        self,
        state_manager: "StateManager",
        context: Dict[str, Any]
    ) -> ValidationResult:
        """
        Run proportional harmony checks and write results to state.

        All findings use PREFERENCE severity - advisory only.

        Args:
            state_manager: StateManager instance for reading/writing
            context: Execution context (unused currently)

        Returns:
            ValidationResult with preference-level findings
        """
        started_at = datetime.utcnow()
        start_time = time.perf_counter()
        findings: List[ValidationFinding] = []
        state = ValidatorState.PASSED

        try:
            # Read required inputs
            lwl = state_manager.get("hull.lwl")
            beam = state_manager.get("hull.beam")
            draft = state_manager.get("hull.draft")
            depth = state_manager.get("hull.depth")
            cb = state_manager.get("hull.cb")
            cp = state_manager.get("hull.cp")
            cm = state_manager.get("hull.cm")
            speed_kts = state_manager.get("mission.max_speed_kts")
            displacement_m3 = state_manager.get("hull.displacement_m3")

            # Validate required inputs present
            if lwl is None or beam is None or draft is None:
                # Can't proceed without basic dimensions - but don't block
                return self._create_skipped_result(started_at, start_time,
                    "Missing required hull dimensions for proportional checks")

            source = "bounds/proportional_harmony"

            # =================================================================
            # CHECK 1: L/B Ratio vs. Froude Regime Envelope
            # =================================================================
            lb_ratio = lwl / beam if beam > 0 else 0
            state_manager.set("bounds.lb_ratio_actual", lb_ratio, source)

            # Froude-based L/B envelope (engineering basis: wave-making and stability)
            # Higher speed → higher Froude → need longer, slenderer hull
            froude = 0.0
            if lwl > 0 and speed_kts is not None:
                g = 9.81
                speed_ms = speed_kts * 0.5144
                froude = speed_ms / (g * lwl) ** 0.5

            # L/B envelope based on Froude regime
            # Low Froude (displacement): L/B 4-6 typical
            # High Froude (planing): L/B 3-5 typical (shorter, wider for stability)
            if froude < 0.35:
                lb_min, lb_max = 4.0, 7.0
                regime = "displacement"
            elif froude < 0.55:
                lb_min, lb_max = 4.5, 6.5
                regime = "semi-displacement"
            elif froude < 1.0:
                lb_min, lb_max = 4.0, 6.0
                regime = "semi-planing"
            else:
                lb_min, lb_max = 3.0, 5.5
                regime = "planing"

            state_manager.set("bounds.lb_envelope_min", lb_min, source)
            state_manager.set("bounds.lb_envelope_max", lb_max, source)

            if lb_ratio < lb_min:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.PREFERENCE,
                    message=f"L/B ratio {lb_ratio:.2f} below {regime} regime envelope ({lb_min}-{lb_max}). "
                            f"Vessel may experience excessive wave-making or stability concerns.",
                    parameter_path="hull.lwl",
                    actual_value=lb_ratio,
                    expected_value=f"{lb_min}-{lb_max} for Fn={froude:.2f}",
                    suggestion=f"Consider increasing L/B by lengthening hull or reducing beam",
                    reference="General naval architecture - Froude regime L/B correlations",
                    adjustment={"path": "hull.lwl", "direction": "increase", "magnitude": 0.03},
                ))
                state = ValidatorState.WARNING
            elif lb_ratio > lb_max:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.PREFERENCE,
                    message=f"L/B ratio {lb_ratio:.2f} above {regime} regime envelope ({lb_min}-{lb_max}). "
                            f"Vessel may have structural concerns or reduced transverse stability.",
                    parameter_path="hull.beam",
                    actual_value=lb_ratio,
                    expected_value=f"{lb_min}-{lb_max} for Fn={froude:.2f}",
                    suggestion=f"Consider decreasing L/B by widening beam or shortening hull",
                    reference="General naval architecture - structural efficiency limits",
                    adjustment={"path": "hull.beam", "direction": "increase", "magnitude": 0.03},
                ))
                state = ValidatorState.WARNING

            # =================================================================
            # CHECK 2: Coefficient Consistency (Cb = Cp × Cm)
            # =================================================================
            if cb is not None and cp is not None and cm is not None and cp > 0:
                cb_implied = cp * cm
                cb_error = abs(cb - cb_implied) / cb if cb > 0 else 0
                is_consistent = cb_error < 0.05  # 5% tolerance

                state_manager.set("bounds.coefficient_consistency", is_consistent, source)

                if not is_consistent:
                    findings.append(ValidationFinding(
                        finding_id=str(uuid.uuid4())[:8],
                        severity=ResultSeverity.PREFERENCE,
                        message=f"Coefficient inconsistency: Cb={cb:.3f} but Cp×Cm={cb_implied:.3f} "
                                f"(error: {cb_error*100:.1f}%). Implies geometrically inconsistent hull.",
                        parameter_path="hull.cb",
                        actual_value=cb,
                        expected_value=f"{cb_implied:.3f} (= Cp × Cm)",
                        suggestion="Adjust Cb to match Cp×Cm for geometric consistency",
                        reference="Naval architecture definition: Cb = Cp × Cm",
                        adjustment={"path": "hull.cb", "direction": "decrease" if cb > cb_implied else "increase",
                                   "magnitude": abs(cb - cb_implied) / 2},
                    ))
                    state = ValidatorState.WARNING
            else:
                state_manager.set("bounds.coefficient_consistency", None, source)

            # =================================================================
            # CHECK 3: Freeboard Ratio Concept Envelope (Simplified ICLL)
            # =================================================================
            # NOTE: This is NOT ICLL class determination - just concept envelope
            if depth is not None and draft is not None and depth > 0:
                freeboard = depth - draft
                freeboard_ratio = freeboard / depth

                state_manager.set("bounds.freeboard_ratio_actual", freeboard_ratio, source)

                # Simplified freeboard envelope based on vessel size
                # Actual ICLL requires tabular lookup - this is concept-level only
                if lwl < 25:
                    fb_min_ratio = 0.20  # Small craft need proportionally more freeboard
                elif lwl < 50:
                    fb_min_ratio = 0.18
                else:
                    fb_min_ratio = 0.15

                state_manager.set("bounds.freeboard_envelope_min", fb_min_ratio, source)

                if freeboard_ratio < fb_min_ratio:
                    # NOTE: This is a low-confidence check - ICLL concept envelope only
                    findings.append(ValidationFinding(
                        finding_id=str(uuid.uuid4())[:8],
                        severity=ResultSeverity.PREFERENCE,
                        message=f"Freeboard ratio {freeboard_ratio:.2f} is low (concept min: {fb_min_ratio}). "
                                f"Freeboard={freeboard:.2f}m for depth={depth:.2f}m. "
                                f"[Low confidence - simplified ICLL approximation, NOT class determination]",
                        parameter_path="hull.depth",
                        actual_value=freeboard_ratio,
                        expected_value=f">{fb_min_ratio} (concept envelope)",
                        suggestion="Consider increasing depth or decreasing draft for adequate freeboard. "
                                   "Actual ICLL requires tabular lookup.",
                        reference="ICLL concept envelope (NOT class determination)",
                        adjustment={"path": "hull.depth", "direction": "increase", "magnitude": 0.03},
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

            # Add summary finding
            checks_count = 3
            preference_count = len([f for f in findings if f.severity == ResultSeverity.PREFERENCE])
            if preference_count == 0:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.PASSED,
                    message=f"Proportional harmony: {checks_count} checks passed. "
                            f"L/B={lb_ratio:.2f}, Fn={froude:.3f} ({regime})",
                ))
            else:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.INFO,
                    message=f"Proportional harmony: {preference_count} improvement suggestions. "
                            f"L/B={lb_ratio:.2f}, Fn={froude:.3f} ({regime})",
                ))

            for finding in findings:
                result.add_finding(finding)

            return result

        except Exception as e:
            # This validator is advisory - log and return passed to not block
            logger.warning(f"Proportional harmony check error (non-blocking): {e}")
            return self._create_skipped_result(started_at, start_time,
                f"Proportional check skipped due to error: {e}")

    def _create_skipped_result(
        self,
        started_at: datetime,
        start_time: float,
        message: str
    ) -> ValidationResult:
        """Create a non-blocking skipped result."""
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        result = ValidationResult(
            validator_id=self.definition.validator_id,
            state=ValidatorState.PASSED,  # Don't block on advisory validator
            started_at=started_at,
            completed_at=datetime.utcnow(),
            execution_time_ms=elapsed_ms,
        )
        result.add_finding(ValidationFinding(
            finding_id=str(uuid.uuid4())[:8],
            severity=ResultSeverity.INFO,
            message=message,
        ))
        return result


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


def get_proportional_harmony_definition() -> ValidatorDefinition:
    """
    Get the validator definition for proportional harmony (v1.4).

    This validator is advisory only - it uses PREFERENCE severity
    and never blocks phase advancement.
    """
    return ValidatorDefinition(
        validator_id="bounds/proportional_harmony",
        name="Proportional Harmony Validator",
        description=(
            "Engineering-grounded proportional checks for hull form harmony (v1.4). "
            "Uses PREFERENCE severity - suggests improvements without blocking."
        ),
        category=ValidatorCategory.BOUNDS,
        priority=ValidatorPriority.LOW,  # Non-blocking advisory
        phase="hull",
        is_gate_condition=False,  # Never blocks advancement
        gate_requirement=GateRequirement.INFORMATIONAL,  # Advisory only
        gate_severity=ResultSeverity.WARNING,
        depends_on_validators=["physics/hydrostatics"],
        depends_on_parameters=[
            "hull.lwl", "hull.beam", "hull.draft", "hull.depth",
            "hull.cb", "hull.cp", "hull.cm",
            "mission.max_speed_kts", "hull.displacement_m3",
        ],
        produces_parameters=[
            "bounds.lb_ratio_actual",
            "bounds.lb_envelope_min",
            "bounds.lb_envelope_max",
            "bounds.freeboard_ratio_actual",
            "bounds.freeboard_envelope_min",
            "bounds.coefficient_consistency",
        ],
        timeout_seconds=30,
        resource_requirements=ResourceRequirements(cpu_cores=1, ram_gb=0.1),
        tags=["bounds", "proportional", "harmony", "preference", "v1.4"],
    )


# =============================================================================
# REGISTRATION HELPER
# =============================================================================

def register_physics_validators(registry) -> None:
    """
    Register all physics validators with a validator registry.

    v1.4: Added proportional harmony validator.

    Args:
        registry: ValidatorRegistry instance from magnet.validators.registry
    """
    # Register hydrostatics
    hydro_def = get_hydrostatics_definition()
    registry.register(hydro_def, HydrostaticsValidator)

    # Register resistance
    res_def = get_resistance_definition()
    registry.register(res_def, ResistanceValidator)

    # v1.4: Register proportional harmony
    prop_def = get_proportional_harmony_definition()
    registry.register(prop_def, ProportionalHarmonyValidator)

    logger.info(f"Registered physics validators: {hydro_def.validator_id}, "
                f"{res_def.validator_id}, {prop_def.validator_id}")
