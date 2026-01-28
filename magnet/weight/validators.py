"""
MAGNET Weight Validators

Module 07 v1.3 - Production-Ready

Implements ValidatorInterface for weight estimation.

v1.3 Changes (North Star Alignment):
- GM < 0 returns WARNING (grade with suggested fix), not FAILED
- North Star Law 6: "Hydrostatics is the only hard gate. Everything else is a grade."
- Human decides whether to accept/override stability warnings

v1.2 Changes (Silence #1 CUT):
- [REVERTED in v1.3] GM < 0 returned FAILED state - violated North Star
- Removed "Still proceed" comment - low GM is warning, negative GM is warning

v1.1 Changes:
- FIX #2: Propulsion field fallbacks (installed_power_kw or total_installed_power_kw)
- FIX #5: Return FAILED for validation failures, raise for code failures
- FIX #6: determinize_dict() for hash-stable summary_data
- FIX #7: Writes stability.kg_m for stability integration
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

from .items import SWBSGroup
from .aggregator import WeightAggregator, LightshipSummary
from .utils import determinize_dict
from .estimators import (
    HullStructureEstimator,
    PropulsionPlantEstimator,
    ElectricPlantEstimator,
    CommandSurveillanceEstimator,
    AuxiliarySystemsEstimator,
    OutfitFurnishingsEstimator,
)
from magnet.core.constants import GRAVITY_M_S2, KNOTS_TO_MS

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger(__name__)


# =============================================================================
# WEIGHT ESTIMATION VALIDATOR (v1.1)
# =============================================================================

class WeightEstimationValidator(ValidatorInterface):
    """
    Main parametric weight estimator.

    Reads all SWBS inputs and produces lightship summary.

    v1.1 Changes:
    - FIX #2: Propulsion field fallbacks
    - FIX #6: determinize_dict() for summary_data

    Reads:
        hull.lwl, hull.beam, hull.depth, hull.draft, hull.cb
        propulsion.installed_power_kw (or total_installed_power_kw)
        propulsion.number_of_engines, propulsion.engine_type
        mission.crew_size, mission.passengers, mission.vessel_type
        hull.displacement_mt

    Writes:
        weight.lightship_mt, weight.lightship_lcg_m
        weight.lightship_vcg_m, weight.lightship_tcg_m
        weight.group_100_mt through weight.group_600_mt
        weight.margin_mt, weight.average_confidence
        weight.summary_data
    """

    def __init__(self, definition: Optional[ValidatorDefinition] = None):
        """Initialize with optional custom definition."""
        if definition is None:
            definition = get_weight_estimation_definition()
        super().__init__(definition)

        # Initialize estimators
        self._hull_estimator = HullStructureEstimator()
        self._propulsion_estimator = PropulsionPlantEstimator()
        self._electrical_estimator = ElectricPlantEstimator()
        self._command_estimator = CommandSurveillanceEstimator()
        self._auxiliary_estimator = AuxiliarySystemsEstimator()
        self._outfit_estimator = OutfitFurnishingsEstimator()

    def validate(
        self,
        state_manager: "StateManager",
        context: Dict[str, Any]
    ) -> ValidationResult:
        """
        Run weight estimation and write results to state.

        FIX #5:
        - Returns FAILED for validation failures (invalid inputs)
        - Returns PASSED/WARNING for success
        - Raises exceptions for code failures (will be retried)

        Args:
            state_manager: StateManager instance for reading/writing
            context: Execution context

        Returns:
            ValidationResult with findings
        """
        started_at = datetime.utcnow()
        start_time = time.perf_counter()
        findings: List[ValidationFinding] = []

        try:
            # Read required hull parameters
            lwl = state_manager.get("hull.lwl")
            beam = state_manager.get("hull.beam")
            depth = state_manager.get("hull.depth")
            draft = state_manager.get("hull.draft")
            cb = state_manager.get("hull.cb")

            # Validate required hull parameters
            missing = []
            if lwl is None or lwl <= 0:
                missing.append("hull.lwl")
            if beam is None or beam <= 0:
                missing.append("hull.beam")
            if depth is None or depth <= 0:
                missing.append("hull.depth")
            if cb is None or cb <= 0:
                missing.append("hull.cb")

            if missing:
                # FIX #5: Return FAILED for validation failure
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
                depth = (draft or 2.0) + 1.5

            # Read propulsion parameters with fallbacks (FIX #2)
            installed_power_kw = state_manager.get("propulsion.installed_power_kw")
            if installed_power_kw is None:
                installed_power_kw = state_manager.get("propulsion.total_installed_power_kw")
            if installed_power_kw is None:
                installed_power_kw = 2000.0  # Default 2MW
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message="No propulsion power specified, using default 2000 kW",
                    parameter_path="propulsion.installed_power_kw",
                ))

            num_engines = state_manager.get("propulsion.number_of_engines", 2)
            engine_type = state_manager.get("propulsion.engine_type", "high_speed_diesel")
            propulsion_type = state_manager.get("propulsion.propulsion_type", "propeller")

            # Read mission parameters
            crew_size = state_manager.get("mission.crew_size", 6)
            passengers = state_manager.get("mission.passengers", 0)
            vessel_type = state_manager.get("mission.vessel_type", "commercial")

            # Read hull material
            hull_material = state_manager.get("hull.material", "aluminum_5083")
            # TASK-017: derive body_count from geometry, not hull_type
            body_count = state_manager.get("hull.body_count") or state_manager.get("hull.num_hulls") or 1
            try:
                body_count = int(body_count)
            except Exception:
                body_count = 1
            body_count = max(1, body_count)

            # Froude number from mission speed + length (continuous; advisory only)
            speed_kts = float(state_manager.get("mission.max_speed_kts") or 0.0)
            lwl_for_fn = float(lwl or 0.0)
            froude_number = 0.0
            if lwl_for_fn > 0:
                speed_ms = speed_kts * KNOTS_TO_MS
                froude_number = speed_ms / (GRAVITY_M_S2 * lwl_for_fn) ** 0.5

            # Get displacement for auxiliary sizing
            displacement_mt = state_manager.get("hull.displacement_mt")
            if displacement_mt is None or displacement_mt <= 0:
                # Rough estimate if not available
                displacement_mt = lwl * beam * (draft or 2.0) * cb * 1.025

            # Run all estimators
            aggregator = WeightAggregator()

            # Group 100 - Hull Structure
            hull_items = self._hull_estimator.estimate(
                lwl=lwl,
                beam=beam,
                depth=depth,
                cb=cb,
                material=hull_material,
                body_count=body_count,
                froude_number=froude_number,
                service_type=vessel_type,
            )
            aggregator.add_items(hull_items)

            # Group 200 - Propulsion
            propulsion_items = self._propulsion_estimator.estimate(
                installed_power_kw=installed_power_kw,
                num_engines=num_engines,
                engine_type=engine_type,
                propulsion_type=propulsion_type,
                lwl=lwl,
            )
            aggregator.add_items(propulsion_items)

            # Group 300 - Electrical
            electrical_items = self._electrical_estimator.estimate(
                installed_power_kw=installed_power_kw,
                lwl=lwl,
                depth=depth,
            )
            aggregator.add_items(electrical_items)

            # Group 400 - Command & Surveillance
            command_items = self._command_estimator.estimate(
                lwl=lwl,
                depth=depth,
                vessel_type=vessel_type,
            )
            aggregator.add_items(command_items)

            # Group 500 - Auxiliary Systems
            auxiliary_items = self._auxiliary_estimator.estimate(
                lwl=lwl,
                beam=beam,
                depth=depth,
                displacement_mt=displacement_mt,
                crew_size=crew_size,
            )
            aggregator.add_items(auxiliary_items)

            # Group 600 - Outfit & Furnishings
            outfit_items = self._outfit_estimator.estimate(
                lwl=lwl,
                beam=beam,
                depth=depth,
                crew_size=crew_size,
                passenger_count=passengers,
            )
            aggregator.add_items(outfit_items)

            # Set margins based on vessel type
            aggregator.set_margins(vessel_type=vessel_type)

            # Calculate lightship
            summary = aggregator.calculate_lightship()

            # -----------------------------------------------------------------
            # Phase 3C: Universal primitives influence weight (explicit-only)
            #
            # Principles:
            # - Never hallucinate: only apply effects when explicit mass_kg is provided.
            # - Keep it deterministic and traceable.
            #
            # Supported semantics:
            # - geometry.attachment / geometry.flow_path / geometry.opening: mass_kg (+ optional mass_center/cg)
            # -----------------------------------------------------------------
            primitive_mass_kg = 0.0
            primitive_mass_breakdown: List[Dict[str, Any]] = []
            primitive_mx = primitive_my = primitive_mz = 0.0
            try:
                resources = state_manager.get("resources", {}) or {}
                if isinstance(resources, dict):
                    for rid, r in resources.items():
                        if not isinstance(r, dict) or r.get("_deleted"):
                            continue
                        rtype = r.get("_type")
                        if rtype not in ("geometry.attachment", "geometry.flow_path", "geometry.opening"):
                            continue
                        m = r.get("mass_kg")
                        if m is None:
                            continue
                        try:
                            m_kg = float(m)
                        except Exception:
                            continue
                        if m_kg <= 0:
                            continue

                        # Determine CG (best-effort): mass_center > buoyancy_center > position > offsets > inlet_point
                        cg = r.get("mass_center") or r.get("cg") or r.get("buoyancy_center") or r.get("position")
                        if cg is None and rtype == "geometry.flow_path":
                            cg = r.get("inlet_point")

                        x = y = z = None
                        if isinstance(cg, dict) and ("x" in cg and "y" in cg and "z" in cg):
                            try:
                                x, y, z = float(cg.get("x")), float(cg.get("y")), float(cg.get("z"))
                            except Exception:
                                x = y = z = None
                        elif isinstance(cg, list) and len(cg) >= 3:
                            try:
                                x, y, z = float(cg[0]), float(cg[1]), float(cg[2])
                            except Exception:
                                x = y = z = None
                        if x is None or y is None or z is None:
                            # Fall back to offsets for attachments, or "unknown" (co-located with existing CG)
                            try:
                                x = float(r.get("offset_x_m") or 0.0)
                                y = float(r.get("offset_y_m") or 0.0)
                                z = float(r.get("offset_z_m") or 0.0)
                            except Exception:
                                x, y, z = None, None, None

                        primitive_mass_kg += m_kg
                        primitive_mass_breakdown.append(
                            {
                                "resource_id": r.get("_id") or rid,
                                "resource_type": rtype,
                                "mass_kg": m_kg,
                                "mass_center": [x, y, z] if (x is not None and y is not None and z is not None) else None,
                            }
                        )

                        # Only apply moments if we have a usable center
                        if x is not None and y is not None and z is not None:
                            primitive_mx += m_kg * x
                            primitive_my += m_kg * y
                            primitive_mz += m_kg * z
            except Exception:
                primitive_mass_kg = 0.0
                primitive_mass_breakdown = []
                primitive_mx = primitive_my = primitive_mz = 0.0

            # Apply mass adjustment to lightship and CGs (best-effort).
            lightship_weight_mt_out = float(summary.lightship_weight_mt)
            lightship_lcg_m_out = float(summary.lightship_lcg_m)
            lightship_tcg_m_out = float(summary.lightship_tcg_m)
            lightship_vcg_m_out = float(summary.lightship_vcg_m)

            if primitive_mass_kg > 0:
                base_mass_kg = max(0.0, float(summary.lightship_weight_mt) * 1000.0)
                new_mass_kg = base_mass_kg + float(primitive_mass_kg)
                lightship_weight_mt_out = new_mass_kg / 1000.0

                # If we have primitive moments, update CGs; otherwise keep original CG.
                if new_mass_kg > 0 and (primitive_mx != 0.0 or primitive_my != 0.0 or primitive_mz != 0.0):
                    base_mx = base_mass_kg * float(summary.lightship_lcg_m)
                    base_my = base_mass_kg * float(summary.lightship_tcg_m)
                    base_mz = base_mass_kg * float(summary.lightship_vcg_m)
                    lightship_lcg_m_out = (base_mx + primitive_mx) / new_mass_kg
                    lightship_tcg_m_out = (base_my + primitive_my) / new_mass_kg
                    lightship_vcg_m_out = (base_mz + primitive_mz) / new_mass_kg

            # Write results to state
            source = "weight/estimation"
            # Canonical paths (contracts/tests expect these names)
            state_manager.set("weight.lightship_weight_mt", lightship_weight_mt_out, source)
            state_manager.set("weight.lightship_vcg_m", lightship_vcg_m_out, source)
            state_manager.set("weight.lightship_lcg_m", lightship_lcg_m_out, source)
            state_manager.set("weight.lightship_tcg_m", lightship_tcg_m_out, source)
            # Legacy alias (backward compatibility)
            state_manager.set("weight.lightship_mt", lightship_weight_mt_out, source)
            state_manager.set("weight.margin_mt", summary.margin_weight_mt, source)
            state_manager.set("weight.average_confidence", summary.average_confidence, source)
            state_manager.set("weight.primitive_mass_kg", float(primitive_mass_kg), source)
            state_manager.set("weight.primitive_mass_breakdown", list(primitive_mass_breakdown), source)

            # Write group weights
            for group in SWBSGroup:
                if group != SWBSGroup.MARGIN and group != SWBSGroup.GROUP_700:
                    weight_mt = summary.get_group_weight_mt(group)
                    state_manager.set(f"weight.group_{group.value}_mt", weight_mt, source)

            # Write summary data (FIX #6: determinized for hash stability)
            state_manager.set("weight.summary_data", summary.to_dict(), source)

            # Phase 4: Honest Output Contract (uncertainty block)
            try:
                from magnet.physics.uncertainty import make_uncertainty, novelty_impact_from_state_resources
                # Heuristic: weight is largely empirical; confidence already computed.
                # Map confidence -> uncertainty pct.
                avg_conf = float(summary.average_confidence or 0.0)
                pct = float(max(5.0, min(30.0, (1.0 - avg_conf) * 25.0 + 5.0)))
                state_manager.set(
                    "weight.uncertainty",
                    make_uncertainty(
                        value_pct=pct,
                        basis="Weight estimated from SWBS heuristics + mission/hull scaling; depends on defaults and assumed equipment",
                        validity_envelope="Early-stage estimating. Improve with vendor quotes, detailed scantlings, and equipment selections.",
                        novelty_impact=novelty_impact_from_state_resources(state_manager.get("resources", {})),
                        details={"average_confidence": avg_conf},
                    ),
                    source,
                )
            except Exception:
                pass

            # Check for weight concerns
            state = ValidatorState.PASSED

            # Check if lightship exceeds displacement
            if lightship_weight_mt_out > displacement_mt:
                ratio = lightship_weight_mt_out / displacement_mt
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=f"Lightship ({lightship_weight_mt_out:.1f} MT) exceeds displacement ({displacement_mt:.1f} MT). Ratio: {ratio:.2f}",
                    suggestion="Reduce structural weight or increase hull size",
                ))
                state = ValidatorState.WARNING

            # Check confidence level
            if summary.average_confidence < 0.6:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.INFO,
                    message=f"Low average confidence: {summary.average_confidence:.2f}",
                    suggestion="Consider vendor quotes for major equipment",
                ))

            logger.info(
                f"Weight estimation complete: {lightship_weight_mt_out:.2f} MT "
                f"(VCG={lightship_vcg_m_out:.2f}m)"
            )

            # Create success result
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

        except Exception as e:
            # Code failure - raise to allow retry
            logger.error(f"Weight estimation failed: {e}", exc_info=True)
            raise


# =============================================================================
# WEIGHT STABILITY VALIDATOR (v1.1)
# =============================================================================

class WeightStabilityValidator(ValidatorInterface):
    """
    Weight-Stability compatibility validator.

    Checks if weight results are suitable for stability calculations
    and writes KG to stability namespace.

    v1.1 FIX #7: Writes stability.kg_m for stability integration.

    Reads:
        weight.lightship_vcg_m, weight.lightship_mt
        hull.displacement_mt, hull.kb_m, hull.bm_m

    Writes:
        weight.estimated_gm_m
        weight.stability_ready
        stability.kg_m (NEW v1.1)
    """

    def __init__(self, definition: Optional[ValidatorDefinition] = None):
        """Initialize with optional custom definition."""
        if definition is None:
            definition = get_weight_stability_definition()
        super().__init__(definition)

    def validate(
        self,
        state_manager: "StateManager",
        context: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate weight-stability compatibility.

        FIX #5:
        - Returns FAILED for validation failures
        - Returns PASSED/WARNING for success
        - Raises exceptions for code failures

        Args:
            state_manager: StateManager instance
            context: Execution context

        Returns:
            ValidationResult with findings
        """
        started_at = datetime.utcnow()
        start_time = time.perf_counter()
        findings: List[ValidationFinding] = []

        try:
            # Read weight results
            lightship_vcg_m = state_manager.get("weight.lightship_vcg_m")
            lightship_mt = state_manager.get("weight.lightship_mt")

            # Read hydrostatics
            displacement_mt = state_manager.get("hull.displacement_mt")
            kb_m = state_manager.get("hull.kb_m")
            bm_m = state_manager.get("hull.bm_m")

            # Validate required inputs
            missing = []
            if lightship_vcg_m is None:
                missing.append("weight.lightship_vcg_m")
            if kb_m is None:
                missing.append("hull.kb_m")
            if bm_m is None:
                missing.append("hull.bm_m")

            if missing:
                # FIX #5: Return FAILED for validation failure
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
                    suggestion="Run weight/estimation and physics/hydrostatics first",
                ))
                # Not ready for stability
                source = "weight/stability_prep"
                state_manager.set("weight.stability_ready", False, source)
                return result

            # FIX #7: Write KG to stability namespace
            # KG (VCG from baseline) is the vertical center of gravity
            source = "weight/stability_prep"
            kg_m = lightship_vcg_m
            state_manager.set("stability.kg_m", kg_m, source)

            # Calculate estimated GM
            # GM = KB + BM - KG = KM - KG
            km_m = kb_m + bm_m
            estimated_gm_m = km_m - kg_m

            state_manager.set("weight.estimated_gm_m", estimated_gm_m, source)

            # Check GM criterion (IMO minimum 0.15m for vessels < 100m)
            # v1.3 (North Star Alignment): GM < 0 is a GRADE with suggested fix
            # North Star Law 6: "Hydrostatics is the only hard gate."
            # Human decides whether to accept, modify, override, or ignore.
            state = ValidatorState.PASSED

            if estimated_gm_m < 0:
                # GRADE: Negative GM is a severe warning with suggested fix
                # The system grades, warns, and suggests. The human decides.
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.ERROR,  # Severity remains ERROR (severe grade)
                    message=f"SEVERE GRADE: Negative GM ({estimated_gm_m:.3f}m). Vessel is capsized/unstable.",
                    parameter_path="weight.estimated_gm_m",
                    actual_value=estimated_gm_m,
                    suggestion="Lower KG by moving weight down or increase BM by widening beam",
                    # The suggested_fix field enables human decision loop
                ))
                state = ValidatorState.WARNING  # v1.3: WARNING not FAILED (grade, not gate)
                state_manager.set("weight.stability_ready", False, source)  # Still not ready for downstream
            elif estimated_gm_m < 0.15:
                # WARNING: Low GM requires attention but can proceed with caution
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=f"Low GM: {estimated_gm_m:.3f}m (< 0.15m IMO minimum)",
                    parameter_path="weight.estimated_gm_m",
                    actual_value=estimated_gm_m,
                    expected_value=0.15,
                    suggestion="Lower KG by moving weight down",
                ))
                state = ValidatorState.WARNING
                state_manager.set("weight.stability_ready", True, source)  # Can proceed with warning
            else:
                state_manager.set("weight.stability_ready", True, source)
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.INFO,
                    message=f"Estimated GM: {estimated_gm_m:.3f}m (adequate for stability)",
                    parameter_path="weight.estimated_gm_m",
                    actual_value=estimated_gm_m,
                ))

            # Check lightship vs displacement ratio
            if lightship_mt and displacement_mt:
                ratio = lightship_mt / displacement_mt
                if ratio > 0.95:
                    findings.append(ValidationFinding(
                        finding_id=str(uuid.uuid4())[:8],
                        severity=ResultSeverity.WARNING,
                        message=f"Lightship/Displacement ratio: {ratio:.2f} (very little deadweight margin)",
                        suggestion="Increase hull size or reduce weight",
                    ))
                    state = ValidatorState.WARNING

            logger.info(
                f"Weight-stability check: GM={estimated_gm_m:.3f}m, "
                f"KG={kg_m:.3f}m, KM={km_m:.3f}m"
            )

            # Create success result
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

        except Exception as e:
            # Code failure - raise to allow retry
            logger.error(f"Weight-stability check failed: {e}", exc_info=True)
            raise


# =============================================================================
# VALIDATOR DEFINITIONS
# =============================================================================

def get_weight_estimation_definition() -> ValidatorDefinition:
    """Get ValidatorDefinition for weight/estimation."""
    return ValidatorDefinition(
        validator_id="weight/estimation",
        name="Parametric Weight Estimator",
        description="SWBS parametric weight estimation (v1.1)",
        category=ValidatorCategory.WEIGHT,
        priority=ValidatorPriority.HIGH,
        phase="weight",
        is_gate_condition=True,
        depends_on_validators=["physics/hydrostatics"],
        depends_on_parameters=[
            "hull.lwl", "hull.beam", "hull.depth", "hull.draft", "hull.cb",
            "propulsion.installed_power_kw", "propulsion.number_of_engines",
            "mission.crew_size", "mission.passengers", "mission.vessel_type",
        ],
        produces_parameters=[
            "weight.lightship_mt", "weight.lightship_lcg_m",
            "weight.lightship_vcg_m", "weight.lightship_tcg_m",
            "weight.group_100_mt", "weight.group_200_mt",
            "weight.group_300_mt", "weight.group_400_mt",
            "weight.group_500_mt", "weight.group_600_mt",
            "weight.margin_mt", "weight.average_confidence",
            "weight.summary_data",
        ],
        timeout_seconds=120,
        resource_requirements=ResourceRequirements(cpu_cores=1, ram_gb=0.5),
        tags=["weight", "swbs", "parametric", "v1.1"],
    )


def get_weight_stability_definition() -> ValidatorDefinition:
    """Get ValidatorDefinition for weight/stability_check."""
    return ValidatorDefinition(
        validator_id="weight/stability_check",
        name="Weight-Stability Compatibility",
        description="Validates weight for stability and writes KG (v1.1)",
        category=ValidatorCategory.WEIGHT,
        priority=ValidatorPriority.HIGH,
        phase="weight",
        is_gate_condition=True,
        depends_on_validators=["weight/estimation", "physics/hydrostatics"],
        depends_on_parameters=[
            "weight.lightship_vcg_m", "weight.lightship_mt",
            "hull.displacement_mt", "hull.kb_m", "hull.bm_m",
        ],
        produces_parameters=[
            "weight.estimated_gm_m",
            "weight.stability_ready",
            "stability.kg_m",  # NEW v1.1
        ],
        timeout_seconds=30,
        resource_requirements=ResourceRequirements(cpu_cores=1, ram_gb=0.2),
        tags=["weight", "stability", "v1.1"],
    )


# =============================================================================
# REGISTRATION HELPER
# =============================================================================

def register_weight_validators(registry: Dict[str, ValidatorInterface]) -> None:
    """
    Register weight validators with the validation registry.

    Args:
        registry: Dictionary mapping validator_id to ValidatorInterface
    """
    weight_estimation = WeightEstimationValidator()
    weight_stability = WeightStabilityValidator()

    registry[weight_estimation.definition.validator_id] = weight_estimation
    registry[weight_stability.definition.validator_id] = weight_stability

    logger.info("Registered weight validators: weight/estimation, weight/stability_check")
