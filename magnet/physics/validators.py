"""
MAGNET Physics Validators

Module 05 v1.3 - Migration to Geometry-Based

Implements ValidatorInterface for physics calculations.

v1.3 Changes (TASK-004):
- Added geometry-derived body-count helpers (no categorical type maps)
- Removed legacy string→enum mapping in the physics path

v1.2 Changes:
- HydrostaticsValidator writes 11 outputs (up from 6)
- ResistanceValidator with Holtrop-Mennen calculations
- FIX #5: FAILED for validation failures, raise for code failures
"""

from __future__ import annotations

import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import math
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
from .geometry_hydrostatics import GeometryHydrostaticsCalculator, compute_hydrostatics_from_geometry
from .equilibrium import solve_equilibrium_draft
from .resistance import ResistanceCalculator, RESISTANCE_OUTPUTS
from .savitsky import SavitskyCalculator, SavitskyInputs

from magnet.core.constants import GRAVITY_M_S2, KNOTS_TO_MS, FN_HOLTROP_USABLE_MAX, FN_HOLTROP_VALID_MAX
from magnet.core.constants import SEAWATER_DENSITY_KG_M3
from magnet.kernel.stdlib.compiler import compile_to_geometry

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager
    from magnet.hull_gen.enums import HullType

logger = logging.getLogger(__name__)


def _write_hydrostatics_outputs_from_geometry(
    *,
    state_manager: "StateManager",
    geometry: Any,
    draft_m: float,
    depth_m: float,
    lwl_m: float,
    source: str,
) -> None:
    """
    Recompute hydrostatics at the given draft and overwrite canonical hull outputs.

    Used by equilibrium draft solver to avoid a stale-draft/hydrostatics mismatch.
    """
    hs = compute_hydrostatics_from_geometry(
        geometry=geometry,
        draft=float(draft_m),
        vcg=None,
        seawater_density=float(SEAWATER_DENSITY_KG_M3),
    )

    displacement_mt = float(hs.displacement_kg) / 1000.0
    state_manager.set("hull.displacement_m3", float(hs.displacement_m3), source)
    state_manager.set("hull.displacement_mt", float(displacement_mt), source)

    # Canonical + legacy aliases
    state_manager.set("hull.kb_m", float(hs.kb_m), source)
    state_manager.set("hull.bm_m", float(hs.bm_transverse_m), source)
    state_manager.set("hull.vcb_m", float(hs.vcb_m), source)  # legacy alias
    state_manager.set("hull.bmt", float(hs.bm_transverse_m), source)  # legacy alias

    state_manager.set("hull.lcb_from_ap_m", float(hs.lcb_m), source)
    state_manager.set("hull.lcf_from_ap_m", float(hs.lcb_m), source)  # approximation

    state_manager.set("hull.waterplane_area_m2", float(hs.waterplane_area_m2), source)
    state_manager.set("hull.wetted_surface_m2", float(hs.wetted_surface_m2), source)

    freeboard = float(depth_m) - float(draft_m)
    state_manager.set("hull.freeboard", float(freeboard), source)

    # TPC (tonnes per cm immersion)
    tpc = (float(SEAWATER_DENSITY_KG_M3) * float(hs.waterplane_area_m2)) / 100000.0
    state_manager.set("hull.tpc", float(tpc), source)

    # MCT: quick estimate consistent with HydrostaticsValidator mapping
    kg_est = 0.5 * float(depth_m) if float(depth_m) > 0 else 0.0
    gml_est = float(hs.kb_m) + float(hs.bm_longitudinal_m) - float(kg_est)
    mct = (displacement_mt * gml_est) / (100.0 * float(lwl_m)) if float(lwl_m) > 0 else 0.0
    state_manager.set("hull.mct", float(mct), source)

    # Extended fields (non-breaking)
    try:
        state_manager.set("hull.it_m4", float(hs.waterplane_inertia_transverse_m4), source)
        state_manager.set("hull.il_m4", float(hs.waterplane_inertia_longitudinal_m4), source)
        state_manager.set("hull.bml", float(hs.bm_longitudinal_m), source)
        state_manager.set("hull.kmt", float(hs.kb_m + hs.bm_transverse_m), source)
        state_manager.set("hull.kml", float(hs.kb_m + hs.bm_longitudinal_m), source)
        state_manager.set("hull.hydrostatics_method", "geometry_integration", source)
        state_manager.set("hull.hydrostatics_method_detail", str(getattr(hs, "method", "")), source)
    except Exception:
        pass

    # Phase 4: keep uncertainty consistent with hydrostatics SSOT
    try:
        from magnet.physics.uncertainty import make_uncertainty, novelty_impact_from_state_resources
        novelty_note = novelty_impact_from_state_resources(state_manager.get("resources", {}))
        state_manager.set(
            "hull.hydrostatics_uncertainty",
            make_uncertainty(
                value_pct=2.0,
                basis="Section-authoritative hydrostatics (polygon clipping + numerical integration)",
                validity_envelope="Valid for well-formed section polygons; accuracy depends on section resolution and fairness",
                novelty_impact=novelty_note,
                details={"method": "geometry_integration", "equilibrated": True},
            ),
            source,
        )
    except Exception:
        pass


# =============================================================================
# GEOMETRY-DERIVED HELPERS (TASK-004)
# =============================================================================

def _get_body_count_from_state(state_manager: "StateManager") -> int:
    """
    Get body count from geometry, not hull_type string.
    
    TASK-004: This is the GENERATIVE approach - derive from geometry,
    not from categorical type.
    
    Priority order:
    1. hull.body_count (explicit geometry)
    2. hull.num_hulls (legacy)
    3. Infer from hull.hull_spacing_m > 0 (multi-hull indicator)
    4. Default to 1 (monohull)
    """
    # Try explicit body count first
    body_count = state_manager.get("hull.body_count")
    if body_count is not None and int(body_count) > 0:
        return int(body_count)
    
    # Try legacy num_hulls
    num_hulls = state_manager.get("hull.num_hulls")
    if num_hulls is not None and int(num_hulls) > 0:
        return int(num_hulls)
    
    # Infer from hull spacing (geometry-derived)
    hull_spacing = state_manager.get("hull.hull_spacing_m")
    if hull_spacing is not None and float(hull_spacing) > 0:
        # Non-zero spacing implies multi-hull
        return 2  # Conservative assumption
    
    # Default to single body
    return 1


def _is_multi_body_from_geometry(state_manager: "StateManager") -> bool:
    """
    Check if vessel is multi-body based on geometry, not hull_type.
    
    TASK-004: Replaces hull-type-string checks with geometry-derived body_count.
    """
    return _get_body_count_from_state(state_manager) > 1


# =============================================================================
# HYDROSTATICS VALIDATOR (v1.3)
# =============================================================================

class HydrostaticsValidator(ValidatorInterface):
    """
    Validator that computes hydrostatics and writes results to state.

    v1.2: Now produces 11 output fields for stability calculations.

        Reads:
            hull.lwl, hull.beam, hull.draft, hull.depth, hull.cb,
            hull.cp, hull.cm, hull.cwp, hull.deadrise_deg

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
        self._geometry_calculator = GeometryHydrostaticsCalculator()
        self._hull_generator = None  # lazy init (avoid import + cost unless used)

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

            # -----------------------------------------------------------------
            # P2: Prefer geometry-based hydrostatics when hull_gen is available.
            # Fallback to parametric hydrostatics on any generation/integration failure.
            # -----------------------------------------------------------------
            hydro_method = "parametric"
            geo = None

            # Optional test/debug control: allow forcing parametric for consistency checks
            use_geometry = True
            try:
                if context and (
                    context.get("force_parametric_hydrostatics") is True
                    or context.get("hydrostatics_method") == "parametric"
                ):
                    use_geometry = False
            except Exception:
                use_geometry = True

            if use_geometry:
                try:
                    geo = self._try_geometry_hydrostatics(
                        state_manager=state_manager,
                        lwl=float(lwl),
                        beam=float(beam),
                        draft=float(draft),
                        depth=float(depth),
                        cb=float(cb),
                        cp=cp,
                        cm=cm,
                        cwp=cwp,
                        deadrise_deg=float(deadrise_deg or 0.0),
                    )
                    hydro_method = "geometry_integration"
                except Exception as e:
                    logger.debug(f"Geometry hydrostatics failed: {e}")
                    geo = None

            from .hydrostatics import HydrostaticsResults

            if geo is not None:
                freeboard = float(depth) - float(draft)
                results = HydrostaticsResults(
                    displacement_mt=float(geo.displacement_mt),
                    volume_displaced_m3=float(geo.volume_displaced_m3),
                    kb_m=float(geo.kb_m),
                    bm_m=float(geo.bmt_m),
                    km_m=float(geo.kmt_m),
                    lcb_m=float(geo.lcb_from_ap_m),
                    vcb_m=float(geo.kb_m),
                    waterplane_area_m2=float(geo.waterplane_area_m2),
                    lcf_m=float(geo.lcf_from_ap_m),
                    moment_of_inertia_l_m4=float(geo.il_m4),
                    moment_of_inertia_t_m4=float(geo.it_m4),
                    tpc=float(geo.tpc),
                    mct=float(geo.mct),
                    wetted_surface_m2=float(geo.wetted_surface_m2),
                    freeboard_m=float(freeboard),
                    deadrise_deg=float(deadrise_deg or 0.0),
                    calculation_time_ms=int(getattr(geo, "calculation_time_ms", 0)),
                    warnings=list(getattr(geo, "warnings", []) or []),
                )
            else:
                # Parametric fallback (or explicit force_parametric_hydrostatics).
                # This keeps legacy tests and offline usage functional while the design-language
                # path is being rolled out. Surface as uncertainty downstream via method marker.
                results = self._calculator.calculate(
                    lwl=float(lwl),
                    beam=float(beam),
                    draft=float(draft),
                    depth=float(depth),
                    cb=float(cb),
                    cp=float(cp) if cp is not None else None,
                    cm=float(cm) if cm is not None else None,
                    cwp=float(cwp) if cwp is not None else None,
                    hull_type=str(state_manager.get("hull.hull_type", "monohull") or "monohull"),
                    deadrise_deg=float(deadrise_deg or 0.0),
                )
                hydro_method = "parametric"
                # Honest note: geometry path didn't run or failed.
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message="Hydrostatics used parametric method (geometry integration unavailable or disabled).",
                ))

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

            # -----------------------------------------------------------------
            # P2: Write expanded hydrostatics fields (non-breaking additions)
            # -----------------------------------------------------------------
            # Longitudinal metacentric radius (BML) and KM* values (use available inertias)
            try:
                vol = float(results.volume_displaced_m3)
                if vol > 0:
                    bml = float(results.moment_of_inertia_l_m4) / vol
                    state_manager.set("hull.bml", bml, source)
                    state_manager.set("hull.kmt", float(results.km_m), source)
                    state_manager.set("hull.kml", float(results.kb_m) + bml, source)
            except Exception:
                pass

            # Method marker + inertias
            try:
                state_manager.set("hull.hydrostatics_method", hydro_method, source)
                state_manager.set("hull.it_m4", float(results.moment_of_inertia_t_m4), source)
                state_manager.set("hull.il_m4", float(results.moment_of_inertia_l_m4), source)
            except Exception:
                pass

            # Phase 4: shared uncertainty schema (non-breaking addition)
            try:
                from magnet.physics.uncertainty import make_uncertainty, novelty_impact_from_state_resources

                # Geometry integration is expected to be more "honest" about sections;
                # parametric is a regression/assumption-heavy fallback.
                if hydro_method == "geometry_integration":
                    pct = 2.0
                    basis = "Section-authoritative hydrostatics (polygon clipping + numerical integration)"
                    env = "Valid for well-formed section polygons; accuracy depends on section resolution and fairness"
                else:
                    pct = 10.0
                    basis = "Parametric hydrostatics fallback (coefficient-based early-stage model)"
                    env = "Valid for conventional hulls near coefficient assumptions; not section-authoritative"

                novelty_note = ""
                try:
                    novelty_note = novelty_impact_from_state_resources(state_manager.get("resources", {}))
                except Exception:
                    novelty_note = ""

                state_manager.set(
                    "hull.hydrostatics_uncertainty",
                    make_uncertainty(
                        value_pct=float(pct),
                        basis=basis,
                        validity_envelope=env,
                        novelty_impact=novelty_note,
                        details={"method": hydro_method},
                    ),
                    source,
                )
            except Exception:
                pass

            # Geometry-derived coefficients + Bonjean curve (avoid stale values on fallback)
            if hydro_method == "geometry_integration" and geo is not None:
                state_manager.set(
                    "hull.cb_geometry",
                    float(geo.cb_geometry) if getattr(geo, "cb_geometry", None) is not None else None,
                    source,
                )
                state_manager.set(
                    "hull.cp_geometry",
                    float(geo.cp_geometry) if getattr(geo, "cp_geometry", None) is not None else None,
                    source,
                )
                state_manager.set(
                    "hull.cm_geometry",
                    float(geo.cm_geometry) if getattr(geo, "cm_geometry", None) is not None else None,
                    source,
                )
                state_manager.set(
                    "hull.cwp_geometry",
                    float(geo.cwp_geometry) if getattr(geo, "cwp_geometry", None) is not None else None,
                    source,
                )
                state_manager.set("hull.sectional_areas", list(geo.sectional_areas_m2), source)
                state_manager.set("hull.bonjean_stations", list(geo.bonjean_stations), source)
            else:
                state_manager.set("hull.cb_geometry", None, source)
                state_manager.set("hull.cp_geometry", None, source)
                state_manager.set("hull.cm_geometry", None, source)
                state_manager.set("hull.cwp_geometry", None, source)
                state_manager.set("hull.sectional_areas", [], source)
                state_manager.set("hull.bonjean_stations", [], source)

            # Add findings for any calculator warnings
            state = ValidatorState.PASSED
            for warning in results.warnings:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=warning,
                ))
                state = ValidatorState.WARNING

            # Phase 3: surface unmodeled primitives as an explicit warning (honest semantics)
            try:
                from magnet.physics.uncertainty import novelty_impact_from_state_resources
                novelty_note = novelty_impact_from_state_resources(state_manager.get("resources", {}))
                if novelty_note:
                    findings.append(ValidationFinding(
                        finding_id=str(uuid.uuid4())[:8],
                        severity=ResultSeverity.INFO,
                        message=novelty_note,
                    ))
            except Exception:
                pass

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

    def _try_geometry_hydrostatics(
        self,
        state_manager: "StateManager",
        lwl: float,
        beam: float,
        draft: float,
        depth: float,
        cb: float,
        cp: Optional[float],
        cm: Optional[float],
        cwp: Optional[float],
        deadrise_deg: float,
    ):
        """
        Best-effort geometry-based hydrostatics.

        Returns:
            GeometryHydrostaticsResults

        Raises:
            Exception on any generation/integration failure (caller should fallback).
        """
        # ---------------------------------------------------------------------
        # SSOT (theory path): resources → compiler → HullGeometry → hydrostatics
        # ---------------------------------------------------------------------
        try:
            state = state_manager.to_dict()
            resources = (state.get("resources") or {})
            has_sections = any(
                isinstance(r, dict)
                and r.get("_type") == "geometry.section"
                and not r.get("_deleted")
                for r in resources.values()
            )
            if has_sections:
                from magnet.kernel.stdlib.compiler import compile_to_geometry

                # Compile design-language resources into canonical HullGeometry
                hull_geom = compile_to_geometry(state, loa=state.get("hull", {}).get("loa") or lwl)

                # Compute from geometry (baseline z=0; waterline z=draft)
                hs = compute_hydrostatics_from_geometry(
                    geometry=hull_geom,
                    draft=float(draft),
                    vcg=None,
                    seawater_density=float(SEAWATER_DENSITY_KG_M3),
                )

                # Adapt to the legacy "geo" object shape expected by validate()
                # (fields are used to populate HydrostaticsResults)
                class _GeoCompat:
                    pass

                geo = _GeoCompat()
                geo.volume_displaced_m3 = float(hs.displacement_m3)
                geo.displacement_mt = float(hs.displacement_kg) / 1000.0
                geo.kb_m = float(hs.kb_m)
                geo.bmt_m = float(hs.bm_transverse_m)
                geo.kmt_m = float(hs.kb_m + hs.bm_transverse_m)
                geo.lcb_from_ap_m = float(hs.lcb_m)
                # LCF: for now, approximate as LCB (Phase 2.5/Phase 4 can refine/attach uncertainty)
                geo.lcf_from_ap_m = float(hs.lcb_m)
                geo.it_m4 = float(hs.waterplane_inertia_transverse_m4)
                geo.il_m4 = float(hs.waterplane_inertia_longitudinal_m4)
                geo.waterplane_area_m2 = float(hs.waterplane_area_m2)
                geo.wetted_surface_m2 = float(hs.wetted_surface_m2)

                # TPC: (ρ × Awp) / 100000  [t/cm]
                geo.tpc = (float(SEAWATER_DENSITY_KG_M3) * float(hs.waterplane_area_m2)) / 100000.0

                # MCT: (Δ × GM_L) / (100 × LWL)  [t-m/cm]
                # Use a compatibility estimate for KG (≈ 0.5 * depth), matching hydrostatics.py approach.
                kg_est = 0.5 * float(depth)
                gml_est = float(hs.kb_m) + float(hs.bm_longitudinal_m) - kg_est
                geo.mct = (geo.displacement_mt * gml_est) / (100.0 * float(lwl)) if float(lwl) > 0 else 0.0

                geo.warnings = list(getattr(hs, "warnings", []) or [])
                geo.calculation_time_ms = 0
                # Geometry-derived coefficients (non-enum; coarse but witnessed)
                try:
                    denom = float(lwl) * float(beam) * float(draft)
                    geo.cb_geometry = float(geo.volume_displaced_m3) / denom if denom > 0 else None
                except Exception:
                    geo.cb_geometry = None
                geo.cp_geometry = None
                geo.cm_geometry = None
                geo.cwp_geometry = None

                # Bonjean curve (sectional areas at this draft), for observability/UI.
                try:
                    from magnet.physics.geometry_hydrostatics import _compute_section_area_below_waterline
                    sections = list(getattr(hull_geom, "sections", []) or [])
                    # Stable order along x
                    sections.sort(key=lambda s: float(getattr(s, "x_position", 0.0) or 0.0))
                    geo.sectional_areas_m2 = [
                        float(_compute_section_area_below_waterline(getattr(s, "points", []) or [], float(draft)))
                        for s in sections
                    ]
                    geo.bonjean_stations = [float(getattr(s, "station", 0.0) or 0.0) for s in sections]
                except Exception:
                    geo.sectional_areas_m2 = []
                    geo.bonjean_stations = []
                return geo
        except Exception as e:
            # Fall through to legacy hull_gen based path below
            logger.debug(f"SSOT geometry hydrostatics path failed; falling back: {e}")

        from magnet.hull_gen.generator import HullGenerator, GeneratorConfig
        from magnet.hull_gen.parameters import (
            HullDefinition,
            MainDimensions,
            FormCoefficients,
            DeadriseProfile,
            HullFeatures,
        )
        from magnet.hull_gen.enums import HullType

        # Lazy generator init (odd num_sections preferred for Simpson integration)
        if self._hull_generator is None:
            self._hull_generator = HullGenerator(
                GeneratorConfig(num_sections=21, points_per_section=31, num_waterlines=11, include_buttocks=False)
            )

        # Estimate coefficients if missing (match parametric hydrostatics defaults) WITHOUT
        # any hull_type string branching (TASK-004).
        planing_like = float(deadrise_deg or 0.0) > 10.0
        if cm is None:
            cm_est = cb + (0.05 if planing_like else 0.10)
            cm = max(0.50, min(0.99, float(cm_est)))
        if cp is None:
            cp = float(cb) / float(cm) if float(cm) > 0 else float(cb) / 0.85
        if cwp is None:
            cwp_est = 0.18 + 0.86 * float(cb)
            cwp = max(0.50, min(0.95, float(cwp_est)))

        # Derive hull form enum from geometry-derived signals only (no string maps).
        body_count = _get_body_count_from_state(state_manager)
        if int(body_count) == 2:
            hull_type_enum = HullType.CATAMARAN
        elif int(body_count) == 3:
            hull_type_enum = HullType.TRIMARAN
        elif planing_like:
            hull_type_enum = HullType.DEEP_V_PLANING
        else:
            hull_type_enum = HullType.HARD_CHINE

        # Get additional hull-form inputs (best-effort)
        loa = state_manager.get("hull.loa")
        if loa is None or float(loa) <= 0:
            loa = float(lwl) / 0.95

        draft_fwd = state_manager.get("hull.draft_fwd_m", draft) or draft
        draft_aft = state_manager.get("hull.draft_aft_m", draft) or draft

        if depth is None or depth <= 0:
            depth = float(draft) + 1.5

        deadrise_transom = state_manager.get("hull.deadrise_transom_deg", deadrise_deg) or deadrise_deg
        bow_flare_deg = state_manager.get("hull.bow_flare_deg", 0.0) or 0.0
        stem_rake_deg = state_manager.get("hull.stem_rake_deg", 15.0) or 15.0
        bow_entrance_deg = state_manager.get("hull.bow_entrance_deg", 25.0) or 25.0
        transom_beam_ratio = state_manager.get("hull.transom_beam_ratio", 0.85) or 0.85
        hull_spacing = state_manager.get("hull.hull_spacing_m", 0.0) or 0.0

        # LCB conversion: kernel stores fraction from FP; hull_gen expects fraction from AP.
        lcb_fraction_fp = state_manager.get("hull.lcb_fraction")
        if lcb_fraction_fp is None:
            lcb_fraction_fp = 0.52
        try:
            lcb_ap = 1.0 - float(lcb_fraction_fp)
        except Exception:
            lcb_ap = 0.48
        lcb_ap = max(0.0, min(1.0, lcb_ap))

        # TASK-004: Number of hulls from GEOMETRY, not hull_type enum
        # This is the correct generative approach - body_count is derived from geometry
        num_hulls = _get_body_count_from_state(state_manager)

        definition = HullDefinition(
            hull_id=str(state_manager.get("design_id", "")) or "geometry-hydrostatics",
            hull_name="Hydrostatics",
            hull_type=hull_type_enum,
            dimensions=MainDimensions(
                loa=float(loa),
                lwl=float(lwl),
                lpp=float(lwl) * 0.98,  # PROVISIONAL
                beam_max=float(beam),
                beam_wl=float(beam) * 0.95,
                beam_chine=float(beam) * 0.90,
                depth=float(depth),
                draft=float(draft),
                draft_fwd=float(draft_fwd),
                draft_aft=float(draft_aft),
                freeboard_bow=float(depth) - float(draft_fwd),
                freeboard_mid=float(depth) - float(draft),
                freeboard_stern=float(depth) - float(draft_aft),
            ),
            coefficients=FormCoefficients(
                cb=float(cb),
                cp=float(cp),
                cm=float(cm),
                cwp=float(cwp),
                lcb=float(lcb_ap),
                lcf=0.50,
            ),
            deadrise=DeadriseProfile.warped(
                transom=float(deadrise_transom),
                midship=float(deadrise_deg),
                bow=min(float(deadrise_deg) + 25.0, 60.0),
            ),
            features=HullFeatures(
                transom_width_fraction=float(transom_beam_ratio),
                bow_flare_deg=float(bow_flare_deg),
                stem_rake_deg=float(stem_rake_deg),
                bow_entrance_deg=float(bow_entrance_deg),
                hull_spacing=float(hull_spacing),
                num_hulls=int(num_hulls),
            ),
        )

        hull_geom = self._hull_generator.generate(definition)
        # Coordinate convention bridge:
        # The legacy hull_gen geometry often uses z=0 at waterline and negative below.
        # geometry_hydrostatics assumes baseline z=0 at keel and waterline at z=draft.
        # Shift sections upward by +draft so keel is near z=0 and WL is near z=draft.
        try:
            for sec in getattr(hull_geom, "sections", []) or []:
                for sp in getattr(sec, "points", []) or []:
                    pos = getattr(sp, "position", None)
                    if pos is not None and hasattr(pos, "z"):
                        pos.z = float(pos.z) + float(draft)
        except Exception:
            pass
        # Use geometry integration as SSOT even when geometry comes from the legacy hull generator.
        hs = compute_hydrostatics_from_geometry(
            geometry=hull_geom,
            draft=float(draft),
            vcg=None,
            seawater_density=float(SEAWATER_DENSITY_KG_M3),
        )

        class _GeoCompat:
            pass

        geo = _GeoCompat()
        geo.volume_displaced_m3 = float(hs.displacement_m3)
        geo.displacement_mt = float(hs.displacement_kg) / 1000.0
        geo.kb_m = float(hs.kb_m)
        geo.bmt_m = float(hs.bm_transverse_m)
        geo.kmt_m = float(hs.kb_m + hs.bm_transverse_m)
        geo.lcb_from_ap_m = float(hs.lcb_m)
        # LCF: approximate as LCB (future refinement)
        geo.lcf_from_ap_m = float(hs.lcb_m)
        geo.it_m4 = float(hs.waterplane_inertia_transverse_m4)
        geo.il_m4 = float(hs.waterplane_inertia_longitudinal_m4)
        geo.waterplane_area_m2 = float(hs.waterplane_area_m2)
        geo.wetted_surface_m2 = float(hs.wetted_surface_m2)
        geo.tpc = (float(SEAWATER_DENSITY_KG_M3) * float(hs.waterplane_area_m2)) / 100000.0
        kg_est = 0.5 * float(depth)
        gml_est = float(hs.kb_m) + float(hs.bm_longitudinal_m) - kg_est
        geo.mct = (geo.displacement_mt * gml_est) / (100.0 * float(lwl)) if float(lwl) > 0 else 0.0
        geo.warnings = list(getattr(hs, "warnings", []) or [])
        geo.calculation_time_ms = 0
        # Geometry-derived coefficients (coarse, but tied to the generated geometry)
        try:
            denom = float(lwl) * float(beam) * float(draft)
            geo.cb_geometry = float(geo.volume_displaced_m3) / denom if denom > 0 else None
        except Exception:
            geo.cb_geometry = None
        geo.cp_geometry = None
        geo.cm_geometry = None
        geo.cwp_geometry = None
        try:
            from magnet.physics.geometry_hydrostatics import _compute_section_area_below_waterline
            sections = list(getattr(hull_geom, "sections", []) or [])
            sections.sort(key=lambda s: float(getattr(s, "x_position", 0.0) or 0.0))
            geo.sectional_areas_m2 = [
                float(_compute_section_area_below_waterline(getattr(s, "points", []) or [], float(draft)))
                for s in sections
            ]
            geo.bonjean_stations = [float(getattr(s, "station", 0.0) or 0.0) for s in sections]
        except Exception:
            geo.sectional_areas_m2 = []
            geo.bonjean_stations = []
        return geo


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
        resistance.total_resistance_kn, resistance.frictional_resistance_kn, resistance.residuary_resistance_kn,
        resistance.effective_power_kw, resistance.froude_number, resistance.reynolds_number,
        resistance.regime, resistance.method_valid, resistance.validity_note
    """

    def __init__(self, definition: Optional[ValidatorDefinition] = None):
        """Initialize with optional custom definition."""
        if definition is None:
            definition = get_resistance_definition()
        super().__init__(definition)
        self._holtrop_calculator = ResistanceCalculator()
        self._savitsky_calculator = SavitskyCalculator()

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
            cp = state_manager.get("hull.cp")

            # LCB semantics:
            # - hull.lcb_fraction is stored as fraction of LWL from FP (0=FP/bow, 1=AP/stern).
            # - ResistanceCalculator expects fraction from midship (+ = forward), where:
            #     0.0 = midship, +0.02 = 2% forward of midship, -0.02 = 2% aft.
            lcb_fraction_midship = None
            lcb_fraction_fp = state_manager.get("hull.lcb_fraction")
            if lcb_fraction_fp is not None:
                try:
                    lcb_fraction_midship = 0.5 - float(lcb_fraction_fp)
                except Exception:
                    lcb_fraction_midship = None

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

            # -----------------------------------------------------------------
            # P2: Route to regime-appropriate resistance method
            #   - Fn <= FN_HOLTROP_USABLE_MAX: Holtrop-Mennen (displacement/semi)
            #   - Fn >  FN_HOLTROP_USABLE_MAX: Savitsky (planing)
            # -----------------------------------------------------------------
            speed_ms = float(speed_kts) * KNOTS_TO_MS
            froude_number = speed_ms / math.sqrt(GRAVITY_M_S2 * float(lwl)) if lwl and lwl > 0 else 0.0

            # TASK-004: Use geometry-derived body count instead of hull_type string
            is_multi_body = _is_multi_body_from_geometry(state_manager)
            body_count = _get_body_count_from_state(state_manager)
            
            # Multi-body behavior is derived from geometry only (TASK-004).
            is_catamaran = bool(is_multi_body)

            interference_factor = None
            interference_note = None
            savitsky = None

            # -----------------------------------------------------------------
            # Firewall (Guide Constraint):
            # - Do NOT hard-switch methods via categorical branching.
            # - Compute both where possible and blend continuously via Fn.
            # -----------------------------------------------------------------
            from .resistance import ResistanceResults

            def _sigmoid(x: float) -> float:
                # Numerically safe-ish sigmoid for small x; good enough for Fn blending.
                return 1.0 / (1.0 + math.exp(-x))

            def _regime_label(fn: float) -> str:
                # Label only (display), not a switch.
                if fn < 0.35:
                    return "displacement"
                if fn < 0.55:
                    return "semi_displacement"
                return "planing"

            # --- 1) Holtrop component (supports catamaran approximation) ---
            holtrop: ResistanceResults
            if is_catamaran:
                # Approximate: 2× demihull Holtrop + interference factor
                hull_spacing_m = state_manager.get("hull.hull_spacing_m")
                if hull_spacing_m is None or hull_spacing_m <= 0:
                    hull_spacing_m = float(lwl) * 0.25  # generator default heuristic

                demihull_beam = float(beam) / 4.0
                demihull_displacement_mt = float(displacement_mt) / 2.0
                demihull_wetted_surface = float(wetted_surface) / 2.0

                demi = self._holtrop_calculator.calculate(
                    lwl=float(lwl),
                    beam=float(demihull_beam),
                    draft=float(draft),
                    displacement_mt=float(demihull_displacement_mt),
                    wetted_surface=float(demihull_wetted_surface),
                    speed_kts=float(speed_kts),
                    cb=float(cb),
                    cp=cp,
                    lcb_fraction=lcb_fraction_midship,
                )

                # Molland/Insel-style interference factor (simple empirical)
                s_L = float(hull_spacing_m) / float(lwl) if lwl and lwl > 0 else 0.3
                if froude_number < 0.4:
                    tau = 1.0 + 0.4 * math.exp(-3.0 * s_L)
                elif froude_number < 0.7:
                    tau = 1.0 + 0.2 * math.exp(-2.5 * s_L)
                else:
                    tau = 1.0 + 0.1 * math.exp(-2.0 * s_L)

                interference_factor = float(tau)
                interference_note = f"Catamaran interference factor τ={tau:.3f} at s/L={s_L:.2f}"

                total_kn = 2.0 * float(demi.total_kn) * tau
                friction_kn = 2.0 * float(demi.frictional_kn) * tau
                residuary_kn = 2.0 * float(demi.residuary_kn) * tau
                appendage_kn = 2.0 * float(demi.appendage_kn) * tau
                air_kn = 2.0 * float(demi.air_kn) * tau

                total_n = total_kn * 1000.0
                pe_kw = (total_n * speed_ms) / 1000.0
                pe_hp = pe_kw * 1.34102

                dyn_p = 0.5 * 1025.0 * speed_ms ** 2
                ct = (total_n / (dyn_p * float(wetted_surface))) if wetted_surface and wetted_surface > 0 else 0.0
                cf = ((friction_kn * 1000.0) / (dyn_p * float(wetted_surface))) if wetted_surface and wetted_surface > 0 else 0.0
                cr = ((residuary_kn * 1000.0) / (dyn_p * float(wetted_surface))) if wetted_surface and wetted_surface > 0 else 0.0

                holtrop = ResistanceResults(
                    total_kn=float(total_kn),
                    total_n=float(total_n),
                    frictional_kn=float(friction_kn),
                    residuary_kn=float(residuary_kn),
                    appendage_kn=float(appendage_kn),
                    air_kn=float(air_kn),
                    effective_power_kw=float(pe_kw),
                    effective_power_hp=float(pe_hp),
                    froude_number=float(froude_number),
                    reynolds_number=float(demi.reynolds_number),
                    cf=float(cf),
                    cr=float(cr),
                    ct=float(ct),
                    form_factor=float(demi.form_factor),
                    speed_kts=float(speed_kts),
                    speed_ms=float(speed_ms),
                    regime=_regime_label(float(froude_number)),
                    method_valid=bool(demi.method_valid),
                    validity_note=(demi.validity_note or "") + ("; " + interference_note if interference_note else ""),
                    calculation_time_ms=int(demi.calculation_time_ms),
                    warnings=list(demi.warnings or []) + ([interference_note] if interference_note else []),
                )
            else:
                holtrop = self._holtrop_calculator.calculate(
                    lwl=lwl,
                    beam=beam,
                    draft=draft,
                    displacement_mt=displacement_mt,
                    wetted_surface=wetted_surface,
                    speed_kts=speed_kts,
                    cb=cb,
                    cp=cp,
                    lcb_fraction=lcb_fraction_midship,
                )

            # --- 2) Savitsky component (monohull planing model) ---
            savitsky = None
            try:
                deadrise = state_manager.get("hull.deadrise_deg", 15.0) or 15.0
                deadrise_transom = state_manager.get("hull.deadrise_transom_deg", deadrise) or deadrise

                disp_kg = None
                if displacement_mt is not None:
                    disp_kg = float(displacement_mt) * 1000.0
                if disp_kg is None or disp_kg <= 0:
                    disp_kg = state_manager.get("hull.displacement_kg")
                if disp_kg is None or disp_kg <= 0:
                    disp_m3 = state_manager.get("hull.displacement_m3")
                    if disp_m3:
                        disp_kg = float(disp_m3) * 1025.0
                if disp_kg is None or disp_kg <= 0:
                    disp_kg = float(displacement_mt) * 1000.0

                lcg_from_transom = self._estimate_lcg_from_transom(state_manager, lwl=float(lwl))
                sav = self._savitsky_calculator.calculate(
                    SavitskyInputs(
                        speed_kts=float(speed_kts),
                        beam_m=float(beam),
                        deadrise_deg=float(deadrise),
                        displacement_kg=float(disp_kg),
                        lcg_from_transom_m=float(lcg_from_transom),
                        vcg_m=state_manager.get("stability.kg_m"),
                        deadrise_transom_deg=float(deadrise_transom),
                    )
                )
                savitsky = sav
            except Exception as e:
                savitsky = None
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.INFO,
                    message=f"Savitsky component unavailable: {e}",
                ))

            sav_as_res: Optional[ResistanceResults] = None
            if savitsky is not None:
                total_kn = float(savitsky.total_resistance_kn)
                total_n = total_kn * 1000.0
                friction_kn = float(savitsky.friction_resistance_kn)
                residuary_kn = float(savitsky.pressure_resistance_kn)
                appendage_kn = float(savitsky.appendage_resistance_kn)
                air_kn = float(savitsky.air_resistance_kn)

                dyn_p = 0.5 * 1025.0 * speed_ms ** 2
                ref_area = float(savitsky.wetted_surface_m2) if savitsky.wetted_surface_m2 > 0 else float(wetted_surface)
                ct = (total_n / (dyn_p * ref_area)) if (dyn_p > 0 and ref_area > 0) else 0.0
                cf = float(savitsky.friction_coefficient)
                cr = ((residuary_kn * 1000.0) / (dyn_p * ref_area)) if (dyn_p > 0 and ref_area > 0) else 0.0

                sav_as_res = ResistanceResults(
                    total_kn=float(total_kn),
                    total_n=float(total_n),
                    frictional_kn=float(friction_kn),
                    residuary_kn=float(residuary_kn),
                    appendage_kn=float(appendage_kn),
                    air_kn=float(air_kn),
                    effective_power_kw=float(savitsky.effective_power_kw),
                    effective_power_hp=float(savitsky.effective_power_kw) * 1.34102,
                    froude_number=float(froude_number),
                    reynolds_number=float(savitsky.reynolds_number),
                    cf=float(cf),
                    cr=float(cr),
                    ct=float(ct),
                    form_factor=1.0,
                    speed_kts=float(speed_kts),
                    speed_ms=float(speed_ms),
                    regime=_regime_label(float(froude_number)),
                    method_valid=bool(savitsky.method_valid),
                    validity_note=str(savitsky.validity_note),
                    calculation_time_ms=int(getattr(savitsky, "calculation_time_ms", 0)),
                    warnings=list(getattr(savitsky, "warnings", []) or []),
                )

            # --- 3) Continuous blending ---
            # Keep the displacement regime strictly Holtrop so the validator matches the
            # Holtrop calculator in the Fn<=valid envelope (tests + transparency).
            fn = float(froude_number)
            if fn <= float(FN_HOLTROP_VALID_MAX):
                w_sav = 0.0
                w_holt = 1.0
            else:
                # Center transition around Holtrop usable max; width controls softness.
                center = float(FN_HOLTROP_USABLE_MAX)
                width = 0.06  # ~0.15 Fn transition band
                w_sav = float(_sigmoid((fn - center) / max(1e-6, width)))
                w_holt = 1.0 - w_sav

            # Multi-body planing blending not modeled; bias to Holtrop component.
            if is_catamaran:
                w_sav = 0.0
                w_holt = 1.0

            if sav_as_res is None:
                w_sav = 0.0
                w_holt = 1.0

            # Normalize just in case
            w_sum = max(1e-9, (w_holt + w_sav))
            w_holt /= w_sum
            w_sav /= w_sum

            def _blend(a: float, b: float) -> float:
                return (w_holt * float(a)) + (w_sav * float(b))

            # If we don't have Savitsky component, blend against Holtrop itself (no-op).
            b = sav_as_res or holtrop

            holt_valid = bool(getattr(holtrop, "method_valid", True))
            sav_valid = bool(getattr(b, "method_valid", True)) if sav_as_res is not None else False
            validity_score = (w_holt * (1.0 if holt_valid else 0.0)) + (w_sav * (1.0 if sav_valid else 0.0))
            method_valid = validity_score >= 0.5

            validity_note = (
                f"Blend: {w_holt:.2f} Holtrop + {w_sav:.2f} Savitsky "
                f"(Fn={float(froude_number):.3f}, holtrop_valid={holt_valid}, savitsky_valid={sav_valid})"
            )

            results = ResistanceResults(
                total_kn=_blend(holtrop.total_kn, b.total_kn),
                total_n=_blend(holtrop.total_n, b.total_n),
                frictional_kn=_blend(holtrop.frictional_kn, b.frictional_kn),
                residuary_kn=_blend(holtrop.residuary_kn, b.residuary_kn),
                appendage_kn=_blend(holtrop.appendage_kn, b.appendage_kn),
                air_kn=_blend(holtrop.air_kn, b.air_kn),
                effective_power_kw=_blend(holtrop.effective_power_kw, b.effective_power_kw),
                effective_power_hp=_blend(holtrop.effective_power_hp, b.effective_power_hp),
                froude_number=float(froude_number),
                reynolds_number=_blend(holtrop.reynolds_number, b.reynolds_number),
                cf=_blend(holtrop.cf, b.cf),
                cr=_blend(holtrop.cr, b.cr),
                ct=_blend(holtrop.ct, b.ct),
                form_factor=_blend(holtrop.form_factor, b.form_factor),
                speed_kts=float(speed_kts),
                speed_ms=float(speed_ms),
                regime=_regime_label(float(froude_number)),
                method_valid=bool(method_valid),
                validity_note=validity_note,
                calculation_time_ms=int(max(int(getattr(holtrop, "calculation_time_ms", 0)), int(getattr(b, "calculation_time_ms", 0)))),
                warnings=list(holtrop.warnings or []) + (list(getattr(b, "warnings", []) or []) if sav_as_res is not None else []),
            )

            if not holt_valid and w_holt > 0.2:
                results.warnings.append("Holtrop component outside typical validity envelope at this Fn.")
            if sav_as_res is not None and not sav_valid and w_sav > 0.2:
                results.warnings.append("Savitsky component outside typical validity envelope at this Fn.")

            # -----------------------------------------------------------------
            # Phase 3C: Universal primitives influence resistance (first-order)
            #
            # Principles:
            # - Never hallucinate: only apply effects when sufficient explicit semantics exist.
            # - Keep it first-order: add an additive drag term at design speed.
            #
            # Supported semantics:
            # - geometry.flow_path (medium='water'): loss model using cross_section_m2 and optional loss_coefficient K.
            # - geometry.opening / geometry.attachment: optional drag_area_m2 (CdA) and/or loss_coefficient.
            # -----------------------------------------------------------------
            primitive_resistance_kn = 0.0
            primitive_breakdown: List[Dict[str, Any]] = []
            try:
                resources = state_manager.get("resources", {}) or {}
                if isinstance(resources, dict) and float(speed_ms) > 0:
                    rho = 1025.0
                    q = 0.5 * rho * float(speed_ms) ** 2  # dynamic pressure (Pa)

                    def _as_vec3(v: Any) -> Optional[List[float]]:
                        if isinstance(v, list) and len(v) >= 3:
                            try:
                                return [float(v[0]), float(v[1]), float(v[2])]
                            except Exception:
                                return None
                        return None

                    for rid, r in resources.items():
                        if not isinstance(r, dict) or r.get("_deleted"):
                            continue
                        rtype = r.get("_type")

                        # --- Flow path losses (water) ---
                        if rtype == "geometry.flow_path":
                            medium = str(r.get("medium") or "").lower()
                            if medium not in ("water", "seawater", "coolant"):
                                continue
                            a = r.get("cross_section_m2")
                            if a is None:
                                continue
                            try:
                                area_m2 = float(a)
                            except Exception:
                                continue
                            if area_m2 <= 0:
                                continue
                            k = r.get("loss_coefficient")
                            try:
                                k_loss = float(k) if k is not None else 2.0  # intake+outlet typical order
                            except Exception:
                                k_loss = 2.0
                            if k_loss <= 0:
                                continue
                            f_n = k_loss * q * area_m2
                            kn = float(f_n) / 1000.0
                            if kn > 0:
                                primitive_resistance_kn += kn
                                primitive_breakdown.append(
                                    {
                                        "resource_id": r.get("_id") or rid,
                                        "resource_type": rtype,
                                        "model": "flow_loss",
                                        "medium": medium,
                                        "cross_section_m2": area_m2,
                                        "loss_coefficient": k_loss,
                                        "delta_kn": kn,
                                        "inlet_point": _as_vec3(r.get("inlet_point")),
                                        "outlet_point": _as_vec3(r.get("outlet_point")),
                                    }
                                )

                        # --- Explicit CdA drag areas (attachments/openings) ---
                        if rtype in ("geometry.attachment", "geometry.opening"):
                            cda = r.get("drag_area_m2")
                            if cda is None:
                                continue
                            try:
                                cdA = float(cda)
                            except Exception:
                                continue
                            if cdA <= 0:
                                continue
                            # CdA is already (Cd * Area); treat directly as equivalent drag area.
                            f_n = q * cdA
                            kn = float(f_n) / 1000.0
                            if kn > 0:
                                primitive_resistance_kn += kn
                                primitive_breakdown.append(
                                    {
                                        "resource_id": r.get("_id") or rid,
                                        "resource_type": rtype,
                                        "model": "cda_drag",
                                        "drag_area_m2": cdA,
                                        "delta_kn": kn,
                                        "position": _as_vec3(r.get("position"))
                                        or _as_vec3(r.get("buoyancy_center")),
                                    }
                                )
            except Exception:
                primitive_resistance_kn = 0.0
                primitive_breakdown = []

            # If primitives add resistance, surface it explicitly as advisory and traceable.
            if primitive_resistance_kn > 0:
                results.warnings.append(
                    f"Applied primitive resistance penalty: +{primitive_resistance_kn:.3f} kN "
                    f"(Phase 3C: flow_path loss + explicit drag_area_m2)."
                )

            # Write outputs to state
            source = "physics/resistance"
            total_kn_out = float(results.total_kn) + float(primitive_resistance_kn)
            appendage_kn_out = float(results.appendage_kn) + float(primitive_resistance_kn)
            effective_power_kw_out = float(results.effective_power_kw) + (float(primitive_resistance_kn) * float(speed_ms))
            effective_power_hp_out = float(effective_power_kw_out) * 1.34102

            state_manager.set("resistance.total_resistance_kn", total_kn_out, source)
            state_manager.set("resistance.frictional_resistance_kn", results.frictional_kn, source)
            state_manager.set("resistance.residuary_resistance_kn", results.residuary_kn, source)
            state_manager.set("resistance.appendage_resistance_kn", appendage_kn_out, source)
            state_manager.set("resistance.air_resistance_kn", results.air_kn, source)
            state_manager.set("resistance.effective_power_kw", effective_power_kw_out, source)
            state_manager.set("resistance.effective_power_hp", effective_power_hp_out, source)
            state_manager.set("resistance.froude_number", results.froude_number, source)
            state_manager.set("resistance.reynolds_number", results.reynolds_number, source)
            state_manager.set("resistance.cf", results.cf, source)
            state_manager.set("resistance.cr", results.cr, source)
            state_manager.set("resistance.ct", results.ct, source)
            # Guide firewall: do not expose categorical method switching to downstream consumers.
            state_manager.set("resistance.method", "blended", source)
            state_manager.set("resistance.regime", results.regime, source)
            state_manager.set("resistance.method_valid", results.method_valid, source)
            state_manager.set("resistance.validity_note", results.validity_note, source)
            state_manager.set("resistance.primitive_resistance_kn", float(primitive_resistance_kn), source)
            state_manager.set("resistance.primitive_resistance_breakdown", list(primitive_breakdown), source)

            # Store decomposition for traceability / "honest output" scaffolding.
            try:
                state_manager.set(
                    "resistance.method_components",
                    {
                        "weights": {"holtrop": w_holt, "savitsky": w_sav},
                        "holtrop": holtrop.to_dict() if hasattr(holtrop, "to_dict") else {},
                        "savitsky": (sav_as_res.to_dict() if (sav_as_res is not None and hasattr(sav_as_res, "to_dict")) else None),
                        "interference_factor": interference_factor,
                        "interference_note": interference_note,
                        "primitive_resistance_kn": float(primitive_resistance_kn),
                    },
                    source,
                )
                # Simple uncertainty heuristic (Phase 4 expands this contract).
                base_uncertainty = (w_holt * 0.12) + (w_sav * 0.18)
                if (w_holt > 0.1 and not bool(holtrop.method_valid)) or (w_sav > 0.1 and not bool(getattr(sav_as_res, "method_valid", True))):
                    base_uncertainty = max(base_uncertainty, 0.25)
                # Primitive effects increase uncertainty (first-order model, not validated across all forms).
                try:
                    frac = float(primitive_resistance_kn) / max(1e-9, float(total_kn_out))
                    base_uncertainty = float(min(0.60, float(base_uncertainty) + min(0.10, 0.50 * frac)))
                except Exception:
                    pass
                state_manager.set("resistance.uncertainty_fraction", float(base_uncertainty), source)
                state_manager.set("resistance.uncertainty_kn", float(base_uncertainty) * float(total_kn_out), source)

                # Phase 4: shared uncertainty schema (non-breaking addition)
                from magnet.physics.uncertainty import make_uncertainty, novelty_impact_from_state_resources
                validity_env = (
                    f"Holtrop valid up to Fn≈{float(FN_HOLTROP_VALID_MAX):.2f}; "
                    f"Savitsky typical for planing (Fn_b>~1.0, deadrise 10–30°). "
                    f"Blend centered at Fn≈{float(FN_HOLTROP_USABLE_MAX):.2f}."
                )
                basis = "Blended empirical resistance (Holtrop + Savitsky) with sigmoid Fn weighting"
                novelty_note = ""
                try:
                    novelty_note = novelty_impact_from_state_resources(state_manager.get("resources", {}))
                except Exception:
                    novelty_note = ""
                details = {
                    "weights": {"holtrop": float(w_holt), "savitsky": float(w_sav)},
                    "fn": float(froude_number),
                    "holtrop_valid": bool(getattr(holtrop, "method_valid", True)),
                    "savitsky_valid": bool(getattr(sav_as_res, "method_valid", True)) if sav_as_res is not None else False,
                    "primitive_resistance_kn": float(primitive_resistance_kn),
                }

                # Phase 2.5/4: explicit, non-hidden outputs (no silent extrapolation)
                outside_envelope = (
                    (w_holt > 0.1 and not bool(getattr(holtrop, "method_valid", True)))
                    or (w_sav > 0.1 and not bool(getattr(sav_as_res, "method_valid", True)) if sav_as_res is not None else False)
                )
                state_manager.set("resistance.method_weights", details["weights"], source)
                state_manager.set("resistance.validity_envelope", validity_env, source)
                state_manager.set("resistance.outside_envelope", bool(outside_envelope), source)
                state_manager.set("resistance.extrapolation_flag", bool(outside_envelope), source)
                state_manager.set(
                    "resistance.uncertainty",
                    make_uncertainty(
                        value_pct=float(base_uncertainty) * 100.0,
                        basis=basis,
                        validity_envelope=validity_env,
                        novelty_impact=novelty_note,
                        details=details,
                    ),
                    source,
                )
            except Exception:
                pass

            # P2: Write planing-specific outputs (clear when not planing)
            if savitsky is not None and w_sav > 0.25:
                state_manager.set("resistance.running_trim_deg", savitsky.running_trim_deg, source)
                state_manager.set("resistance.wetted_length_m", savitsky.wetted_length_m, source)
                state_manager.set("resistance.wetted_surface_m2", savitsky.wetted_surface_m2, source)
                state_manager.set("resistance.froude_beam", savitsky.froude_beam, source)
                state_manager.set("resistance.lift_coefficient", savitsky.lift_coefficient, source)
                state_manager.set("resistance.drag_coefficient", savitsky.drag_coefficient, source)
                state_manager.set("resistance.friction_coefficient", savitsky.friction_coefficient, source)
                state_manager.set("resistance.pressure_resistance_kn", savitsky.pressure_resistance_kn, source)
            else:
                state_manager.set("resistance.running_trim_deg", None, source)
                state_manager.set("resistance.wetted_length_m", None, source)
                state_manager.set("resistance.wetted_surface_m2", None, source)
                state_manager.set("resistance.froude_beam", None, source)
                state_manager.set("resistance.lift_coefficient", None, source)
                state_manager.set("resistance.drag_coefficient", None, source)
                state_manager.set("resistance.friction_coefficient", None, source)
                state_manager.set("resistance.pressure_resistance_kn", None, source)

            # P2: Catamaran interference factor (clear when not applied)
            state_manager.set("resistance.interference_factor", interference_factor, source)
            state_manager.set("resistance.interference_note", interference_note, source)

            # Add calculator warnings as findings
            state = ValidatorState.PASSED
            for warning in results.warnings:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=warning,
                ))
                state = ValidatorState.WARNING

            # Regime/method gating (P1): explicit validity surfaced for downstream consumers
            if not results.method_valid:
                findings.append(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=results.validity_note or "Resistance method validity: not valid for current regime",
                    parameter_path="resistance.method_valid",
                    actual_value=results.method_valid,
                    expected_value=True,
                    suggestion="Use a regime-appropriate resistance method (e.g., Savitsky for planing)",
                ))
                state = ValidatorState.WARNING

            # Low Froude - hull may be oversized for speed
            if results.froude_number < 0.2:
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
                    parameter_path="resistance.total_resistance_kn",
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

    def _estimate_lcg_from_transom(self, state_manager: "StateManager", lwl: float) -> float:
        """
        Estimate LCG from transom (AP) for planing calculations.

        Preferred source (if available): `weight.lightship_lcg_m` (assumed from AP).
        Fallback: derive from `hull.lcb_fraction` (stored as fraction from FP) with a small aft bias.
        """
        # Try weight module if present
        try:
            lcg_from_ap = state_manager.get("weight.lightship_lcg_m")
            if lcg_from_ap is not None:
                lcg_val = float(lcg_from_ap)
                if 0.0 <= lcg_val <= float(lwl):
                    return lcg_val
        except Exception:
            pass

        # Fallback based on buoyancy center position
        lcb_fraction_fp = state_manager.get("hull.lcb_fraction")
        if lcb_fraction_fp is None:
            lcb_fraction_fp = 0.52
        try:
            lcb_from_ap = float(lwl) * (1.0 - float(lcb_fraction_fp))
        except Exception:
            lcb_from_ap = float(lwl) * 0.48

        # Planing craft CG is typically slightly aft of LCB (toward transom)
        lcg = 0.95 * lcb_from_ap

        # Clamp to plausible range
        return max(0.15 * float(lwl), min(0.80 * float(lwl), float(lcg)))


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
# EQUILIBRIUM DRAFT VALIDATOR (Phase 3C)
# =============================================================================

class EquilibriumDraftValidator(ValidatorInterface):
    """
    Solve for equilibrium draft given target weight, then (optionally) apply it.

    Honest Output Contract:
    - Always writes equilibrium_* diagnostic fields when a target weight exists.
    - Only mutates hull.draft if hull.auto_equilibrate_draft is explicitly True.
    - If it mutates draft, it immediately recomputes and overwrites hydrostatics outputs
      so downstream stability/resistance do not consume stale buoyancy at the old draft.
    """

    def __init__(self, definition: Optional[ValidatorDefinition] = None):
        if definition is None:
            definition = get_equilibrium_draft_definition()
        super().__init__(definition)

    def validate(self, state_manager: "StateManager", context: Dict[str, Any]) -> ValidationResult:
        started_at = datetime.utcnow()
        start_time = time.perf_counter()
        findings: List[ValidationFinding] = []

        auto_apply = bool(state_manager.get("hull.auto_equilibrate_draft") or False)

        # Target displacement (mt): prefer loading computer if present, else lightship
        target_mt = state_manager.get("loading.total_displacement_mt")
        if target_mt is None:
            target_mt = state_manager.get("weight.lightship_weight_mt")
        if target_mt is None:
            target_mt = state_manager.get("weight.lightship_mt")  # legacy alias

        # No target => skip silently (non-blocking)
        if target_mt is None:
            return ValidationResult(
                validator_id=self.definition.validator_id,
                state=ValidatorState.SKIPPED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                execution_time_ms=int((time.perf_counter() - start_time) * 1000),
            )

        depth = state_manager.get("hull.depth")
        draft_guess = state_manager.get("hull.draft")
        lwl = state_manager.get("hull.lwl") or state_manager.get("hull.loa") or 0.0

        # Need depth to bound the solve.
        if depth is None or float(depth) <= 0:
            if not auto_apply:
                return ValidationResult(
                    validator_id=self.definition.validator_id,
                    state=ValidatorState.SKIPPED,
                    started_at=started_at,
                    completed_at=datetime.utcnow(),
                    execution_time_ms=int((time.perf_counter() - start_time) * 1000),
                )
            result = ValidationResult(
                validator_id=self.definition.validator_id,
                state=ValidatorState.WARNING,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                execution_time_ms=int((time.perf_counter() - start_time) * 1000),
            )
            result.add_finding(
                ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message="Equilibrium draft requested but hull.depth is missing; cannot solve equilibrium.",
                    suggestion="Set hull.depth and hull.draft, or disable hull.auto_equilibrate_draft.",
                )
            )
            return result

        if draft_guess is None or float(draft_guess) <= 0:
            draft_guess = min(0.8 * float(depth), 1.0)

        resources = state_manager.get("resources", {})
        if not isinstance(resources, dict) or not resources:
            if not auto_apply:
                return ValidationResult(
                    validator_id=self.definition.validator_id,
                    state=ValidatorState.SKIPPED,
                    started_at=started_at,
                    completed_at=datetime.utcnow(),
                    execution_time_ms=int((time.perf_counter() - start_time) * 1000),
                )
            findings.append(
                ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message="Equilibrium draft requested but no DesignState.resources exist; cannot compile geometry.",
                    suggestion="Ensure DesignState.resources contains geometry.section polygons (design_program path).",
                )
            )
            result = ValidationResult(
                validator_id=self.definition.validator_id,
                state=ValidatorState.WARNING,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                execution_time_ms=int((time.perf_counter() - start_time) * 1000),
            )
            for f in findings:
                result.add_finding(f)
            return result

        # Compile geometry from design-language resources (SSOT path)
        try:
            state_dict = {
                "design_id": state_manager.get("design_id") or "",
                "hull": {"loa": state_manager.get("hull.loa") or lwl or 25.0},
                "resources": resources,
            }
            geometry = compile_to_geometry(state_dict)
        except Exception as e:
            if not auto_apply:
                return ValidationResult(
                    validator_id=self.definition.validator_id,
                    state=ValidatorState.SKIPPED,
                    started_at=started_at,
                    completed_at=datetime.utcnow(),
                    execution_time_ms=int((time.perf_counter() - start_time) * 1000),
                )
            findings.append(
                ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=f"Equilibrium draft requested but geometry compilation failed: {e}",
                    suggestion="Fix invalid geometry.section polygons and re-run.",
                )
            )
            result = ValidationResult(
                validator_id=self.definition.validator_id,
                state=ValidatorState.WARNING,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                execution_time_ms=int((time.perf_counter() - start_time) * 1000),
            )
            for f in findings:
                result.add_finding(f)
            return result

        # Solve equilibrium using SSOT hydrostatics
        try:
            sol = solve_equilibrium_draft(
                geometry=geometry,
                target_displacement_mt=float(target_mt),
                draft_guess_m=float(draft_guess),
                depth_m=float(depth),
                seawater_density=float(SEAWATER_DENSITY_KG_M3),
            )
        except Exception as e:
            # Non-blocking: equilibrium is advisory unless explicitly auto-applied.
            if not auto_apply:
                result = ValidationResult(
                    validator_id=self.definition.validator_id,
                    state=ValidatorState.SKIPPED,
                    started_at=started_at,
                    completed_at=datetime.utcnow(),
                    execution_time_ms=int((time.perf_counter() - start_time) * 1000),
                )
                result.add_finding(ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.INFO,
                    message=f"Equilibrium draft solve skipped (non-blocking): {e}",
                ))
                return result

            result = ValidationResult(
                validator_id=self.definition.validator_id,
                state=ValidatorState.WARNING,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                execution_time_ms=int((time.perf_counter() - start_time) * 1000),
            )
            result.add_finding(ValidationFinding(
                finding_id=str(uuid.uuid4())[:8],
                severity=ResultSeverity.WARNING,
                message=f"Equilibrium draft solve failed: {e}",
                suggestion="Disable hull.auto_equilibrate_draft or fix geometry/resources, then retry.",
            ))
            return result

        source = "physics/equilibrium_draft"
        state_manager.set("hull.equilibrium_draft_m", float(sol.draft_m), source)
        state_manager.set("hull.equilibrium_converged", bool(sol.converged), source)
        state_manager.set("hull.equilibrium_iterations", int(sol.iterations), source)
        state_manager.set("hull.equilibrium_residual_mt", float(sol.residual_mt), source)
        state_manager.set("hull.equilibrium_target_displacement_mt", float(target_mt), source)
        state_manager.set("hull.equilibrium_best_abs_residual_mt", float(sol.best_abs_residual_mt), source)
        state_manager.set("hull.equilibrium_reason", str(sol.reason or ""), source)

        if sol.converged:
            findings.append(
                ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.PASSED,
                    message=f"Equilibrium draft solved: T={float(sol.draft_m):.3f} m (residual={float(sol.residual_mt):.3f} MT)",
                )
            )
        else:
            findings.append(
                ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=f"Equilibrium draft did not converge (best residual={float(sol.best_abs_residual_mt):.3f} MT): {sol.reason}",
                    suggestion="If overweight: increase beam/depth or reduce weight; if underweight: reduce draft target or verify inputs.",
                )
            )

        # Explicit mutation + immediate hydrostatics recompute (avoid stale outputs)
        if auto_apply and sol.converged:
            state_manager.set("hull.draft", float(sol.draft_m), source)
            try:
                _write_hydrostatics_outputs_from_geometry(
                    state_manager=state_manager,
                    geometry=geometry,
                    draft_m=float(sol.draft_m),
                    depth_m=float(depth),
                    lwl_m=float(lwl or 0.0),
                    source=source,
                )
                findings.append(
                    ValidationFinding(
                        finding_id=str(uuid.uuid4())[:8],
                        severity=ResultSeverity.INFO,
                        message="Applied equilibrium draft to hull.draft and recomputed hydrostatics (explicit).",
                    )
                )
            except Exception as e:
                findings.append(
                    ValidationFinding(
                        finding_id=str(uuid.uuid4())[:8],
                        severity=ResultSeverity.WARNING,
                        message=f"Equilibrium draft applied, but hydrostatics recompute failed: {e}",
                        suggestion="Re-run physics/hydrostatics after fixing geometry.",
                    )
                )

        state = ValidatorState.PASSED if sol.converged else ValidatorState.WARNING
        result = ValidationResult(
            validator_id=self.definition.validator_id,
            state=state,
            started_at=started_at,
            completed_at=datetime.utcnow(),
            execution_time_ms=int((time.perf_counter() - start_time) * 1000),
        )
        for f in findings:
            result.add_finding(f)
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
        phase="hull",
        is_gate_condition=True,
        depends_on_parameters=[
            "hull.loa", "hull.lwl", "hull.beam", "hull.depth", "hull.draft",
            "hull.cb", "hull.cp", "hull.cm", "hull.cwp",
            "hull.deadrise_deg"
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
        phase="hull",
        is_gate_condition=True,
        depends_on_validators=["physics/hydrostatics"],
        depends_on_parameters=[
            "hull.lwl", "hull.beam", "hull.draft", "hull.cb",
            "hull.displacement_mt", "hull.wetted_surface_m2",
            "mission.max_speed_kts"
        ],
        produces_parameters=[
            "resistance.total_resistance_kn",
            "resistance.frictional_resistance_kn",
            "resistance.residuary_resistance_kn",
            "resistance.effective_power_kw",
            "resistance.froude_number",
            "resistance.reynolds_number",
            "resistance.regime",
            "resistance.method_valid",
            "resistance.validity_note",
        ],
        timeout_seconds=180,
        resource_requirements=ResourceRequirements(cpu_cores=2, ram_gb=2.0),
        tags=["core", "hull", "propulsion"],
    )


def get_equilibrium_draft_definition() -> ValidatorDefinition:
    """Get the validator definition for equilibrium draft solver."""
    return ValidatorDefinition(
        validator_id="physics/equilibrium_draft",
        name="Equilibrium Draft Solver",
        description="Solves draft where buoyancy equals estimated weight (Phase 3C)",
        category=ValidatorCategory.PHYSICS,
        priority=ValidatorPriority.HIGH,
        phase="weight",
        is_gate_condition=False,
        gate_requirement=GateRequirement.OPTIONAL,
        depends_on_validators=["physics/hydrostatics", "weight/estimation"],
        depends_on_parameters=[
            "hull.depth", "hull.draft",
            "weight.lightship_weight_mt",
        ],
        produces_parameters=[
            "hull.equilibrium_draft_m",
            "hull.equilibrium_converged",
            "hull.equilibrium_iterations",
            "hull.equilibrium_residual_mt",
            "hull.equilibrium_target_displacement_mt",
        ],
        timeout_seconds=120,
        resource_requirements=ResourceRequirements(cpu_cores=2, ram_gb=1.0),
        tags=["physics", "equilibrium", "draft", "phase3c"],
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
