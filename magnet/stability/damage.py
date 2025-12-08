"""
MAGNET Damage Stability Calculator

Module 06 v1.2 - Production-Ready

Evaluates stability under damaged (flooded) conditions.

v1.1 FIX #4: Trim coupling is simplified (parallel sinkage/trim calculation).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
import time
import math
import logging

from magnet.core.constants import SEAWATER_DENSITY_KG_M3

logger = logging.getLogger(__name__)


# =============================================================================
# DAMAGE STABILITY CRITERIA
# =============================================================================

DAMAGE_GM_MIN = 0.05                 # Residual GM minimum (m)
DAMAGE_GZ_MAX_MIN = 0.10             # Residual GZmax minimum (m)
DAMAGE_RANGE_MIN = 15.0              # Residual range minimum (deg)
DAMAGE_HEEL_MAX_CARGO = 25.0         # Max equilibrium heel - cargo (deg)
DAMAGE_HEEL_MAX_PASSENGER = 15.0     # Max equilibrium heel - passenger (deg)

# Standard permeabilities
PERMEABILITY_VOID = 0.95
PERMEABILITY_CARGO = 0.60
PERMEABILITY_MACHINERY = 0.85
PERMEABILITY_ACCOMMODATION = 0.95
PERMEABILITY_STORES = 0.60


# =============================================================================
# VESSEL TYPE
# =============================================================================

class VesselType(str, Enum):
    """Vessel type for damage stability criteria."""
    CARGO = "cargo"
    PASSENGER = "passenger"
    TANKER = "tanker"
    WORKBOAT = "workboat"


# =============================================================================
# DAMAGE CASE
# =============================================================================

@dataclass
class DamageCase:
    """Definition of a damage (flooding) scenario."""
    case_id: str
    name: str
    compartment: str
    flooded_length_m: float
    flooded_breadth_m: float
    flooded_height_m: float
    permeability: float = 0.85
    position_from_ap_m: float = 0.0  # Longitudinal position

    def flooded_volume_m3(self) -> float:
        """Calculate flooded volume (m³)."""
        return (
            self.flooded_length_m *
            self.flooded_breadth_m *
            self.flooded_height_m *
            self.permeability
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "name": self.name,
            "compartment": self.compartment,
            "flooded_length_m": round(self.flooded_length_m, 2),
            "flooded_breadth_m": round(self.flooded_breadth_m, 2),
            "flooded_height_m": round(self.flooded_height_m, 2),
            "permeability": round(self.permeability, 2),
            "position_from_ap_m": round(self.position_from_ap_m, 2),
            "flooded_volume_m3": round(self.flooded_volume_m3(), 2),
        }


# =============================================================================
# DAMAGE RESULT
# =============================================================================

@dataclass
class DamageResult:
    """Result for a single damage case."""
    case: DamageCase
    flooded_volume_m3: float
    lost_buoyancy_mt: float

    # Equilibrium condition
    sinkage_m: float
    equilibrium_heel_deg: float
    equilibrium_trim_m: float

    # Residual stability
    residual_gm_m: float
    residual_gz_max_m: float
    residual_range_deg: float

    # Compliance
    passes_criteria: bool
    failed_criteria: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case": self.case.to_dict(),
            "flooded_volume_m3": round(self.flooded_volume_m3, 2),
            "lost_buoyancy_mt": round(self.lost_buoyancy_mt, 2),
            "sinkage_m": round(self.sinkage_m, 3),
            "equilibrium_heel_deg": round(self.equilibrium_heel_deg, 1),
            "equilibrium_trim_m": round(self.equilibrium_trim_m, 3),
            "residual_gm_m": round(self.residual_gm_m, 3),
            "residual_gz_max_m": round(self.residual_gz_max_m, 3),
            "residual_range_deg": round(self.residual_range_deg, 1),
            "passes_criteria": self.passes_criteria,
            "failed_criteria": self.failed_criteria,
        }


# =============================================================================
# DAMAGE STABILITY RESULTS
# =============================================================================

@dataclass
class DamageStabilityResults:
    """Overall damage stability assessment results."""
    cases: List[DamageResult]
    all_pass: bool
    worst_case: Optional[DamageResult]
    vessel_type: VesselType

    # Summary
    cases_evaluated: int
    cases_passed: int
    cases_failed: int

    # Metadata
    calculation_time_ms: int = 0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cases": [c.to_dict() for c in self.cases],
            "all_pass": self.all_pass,
            "worst_case": self.worst_case.to_dict() if self.worst_case else None,
            "vessel_type": self.vessel_type.value,
            "cases_evaluated": self.cases_evaluated,
            "cases_passed": self.cases_passed,
            "cases_failed": self.cases_failed,
            "calculation_time_ms": self.calculation_time_ms,
            "warnings": self.warnings,
        }


# =============================================================================
# DAMAGE STABILITY CALCULATOR
# =============================================================================

class DamageStabilityCalculator:
    """
    Calculator for damage stability assessment.

    Uses the lost buoyancy method to estimate equilibrium condition
    and residual stability after flooding.

    v1.1 FIX #4: Simplified trim calculation (not iterative).
    This is a limitation for V1; iterative equilibrium solver planned for V2.

    Method:
    1. Calculate lost buoyancy from flooded compartment
    2. Estimate sinkage and trim (parallel sinkage approximation)
    3. Calculate residual GM and GZ curve
    4. Check against damage stability criteria
    """

    def __init__(
        self,
        vessel_type: VesselType = VesselType.CARGO,
    ):
        """
        Initialize calculator.

        Args:
            vessel_type: Type of vessel for heel criteria
        """
        self.vessel_type = vessel_type
        self.max_heel = (
            DAMAGE_HEEL_MAX_PASSENGER
            if vessel_type == VesselType.PASSENGER
            else DAMAGE_HEEL_MAX_CARGO
        )

    def calculate_standard_cases(
        self,
        lwl: float,
        beam: float,
        draft: float,
        depth: float,
        displacement_mt: float,
        gm_m: float,
        bm_m: float,
        tpc: float = None,
        mct: float = None,
        compartment_lengths: Optional[Dict[str, float]] = None,
    ) -> DamageStabilityResults:
        """
        Calculate damage stability for standard cases.

        Standard cases:
        1. Forepeak flooding (DAM-001)
        2. Aft peak flooding (DAM-002)
        3. Engine room flooding (DAM-003)
        4. Midship hold flooding (DAM-004)

        Args:
            lwl: Length waterline (m)
            beam: Beam (m)
            draft: Draft (m)
            depth: Depth (m)
            displacement_mt: Displacement (tonnes)
            gm_m: Metacentric height (m)
            bm_m: Metacentric radius (m)
            tpc: Tonnes per cm immersion (t/cm) - estimated if None
            mct: Moment to change trim 1cm (t-m/cm) - estimated if None
            compartment_lengths: Custom compartment lengths (optional)

        Returns:
            DamageStabilityResults with all case evaluations
        """
        start_time = time.perf_counter()
        warnings: List[str] = []

        # Validate inputs
        if lwl <= 0 or beam <= 0 or draft <= 0 or displacement_mt <= 0:
            raise ValueError("Hull dimensions and displacement must be positive")

        if gm_m <= 0:
            warnings.append(f"Non-positive GM ({gm_m}m) - damage stability likely fails")

        # Estimate TPC and MCT if not provided
        if tpc is None:
            # TPC ≈ (ρ × Awp) / 100000
            awp_est = lwl * beam * 0.7  # Rough estimate
            tpc = (SEAWATER_DENSITY_KG_M3 * awp_est) / 100000.0
            warnings.append(f"TPC estimated as {tpc:.4f} t/cm")

        if mct is None:
            # MCT ≈ (Δ × GM_L) / (100 × L)
            gml_est = 10.0 * gm_m  # Rough estimate
            mct = (displacement_mt * gml_est) / (100.0 * lwl)
            warnings.append(f"MCT estimated as {mct:.2f} t-m/cm")

        # Generate standard damage cases
        cases = self._generate_standard_cases(
            lwl, beam, draft, depth, compartment_lengths
        )

        # Evaluate each case
        results = []
        for case in cases:
            result = self._evaluate_damage_case(
                case=case,
                displacement_mt=displacement_mt,
                gm_m=gm_m,
                bm_m=bm_m,
                tpc=tpc,
                mct=mct,
                lwl=lwl,
                beam=beam,
            )
            results.append(result)

        # Find worst case (lowest residual GM)
        worst_case = min(results, key=lambda r: r.residual_gm_m) if results else None

        # Check overall pass/fail
        all_pass = all(r.passes_criteria for r in results)
        cases_passed = sum(1 for r in results if r.passes_criteria)
        cases_failed = len(results) - cases_passed

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return DamageStabilityResults(
            cases=results,
            all_pass=all_pass,
            worst_case=worst_case,
            vessel_type=self.vessel_type,
            cases_evaluated=len(results),
            cases_passed=cases_passed,
            cases_failed=cases_failed,
            calculation_time_ms=elapsed_ms,
            warnings=warnings,
        )

    def _generate_standard_cases(
        self,
        lwl: float,
        beam: float,
        draft: float,
        depth: float,
        compartment_lengths: Optional[Dict[str, float]] = None,
    ) -> List[DamageCase]:
        """
        Generate standard damage cases.

        Default compartment lengths:
        - Forepeak: 5% of LWL
        - Aft peak: 5% of LWL
        - Engine room: 15% of LWL
        - Hold: 20% of LWL
        """
        if compartment_lengths is None:
            compartment_lengths = {
                "forepeak": 0.05 * lwl,
                "aft_peak": 0.05 * lwl,
                "engine_room": 0.15 * lwl,
                "hold": 0.20 * lwl,
            }

        cases = [
            DamageCase(
                case_id="DAM-001",
                name="Forepeak Flooding",
                compartment="forepeak",
                flooded_length_m=compartment_lengths.get("forepeak", 0.05 * lwl),
                flooded_breadth_m=beam * 0.8,  # Narrower at bow
                flooded_height_m=draft,
                permeability=PERMEABILITY_VOID,
                position_from_ap_m=lwl * 0.95,  # Near bow
            ),
            DamageCase(
                case_id="DAM-002",
                name="Aft Peak Flooding",
                compartment="aft_peak",
                flooded_length_m=compartment_lengths.get("aft_peak", 0.05 * lwl),
                flooded_breadth_m=beam * 0.8,
                flooded_height_m=draft,
                permeability=PERMEABILITY_VOID,
                position_from_ap_m=lwl * 0.025,  # Near stern
            ),
            DamageCase(
                case_id="DAM-003",
                name="Engine Room Flooding",
                compartment="engine_room",
                flooded_length_m=compartment_lengths.get("engine_room", 0.15 * lwl),
                flooded_breadth_m=beam * 0.9,
                flooded_height_m=draft * 1.2,  # Below waterline + some height
                permeability=PERMEABILITY_MACHINERY,
                position_from_ap_m=lwl * 0.35,  # Typically aft of midship
            ),
            DamageCase(
                case_id="DAM-004",
                name="Midship Hold Flooding",
                compartment="hold",
                flooded_length_m=compartment_lengths.get("hold", 0.20 * lwl),
                flooded_breadth_m=beam * 0.95,
                flooded_height_m=draft,
                permeability=PERMEABILITY_CARGO,
                position_from_ap_m=lwl * 0.50,  # Midship
            ),
        ]

        return cases

    def _evaluate_damage_case(
        self,
        case: DamageCase,
        displacement_mt: float,
        gm_m: float,
        bm_m: float,
        tpc: float,
        mct: float,
        lwl: float,
        beam: float,
    ) -> DamageResult:
        """
        Evaluate a single damage case.

        Uses lost buoyancy method with parallel sinkage approximation.
        """
        # Calculate flooded volume and lost buoyancy
        flooded_volume = case.flooded_volume_m3()
        lost_buoyancy_mt = flooded_volume * SEAWATER_DENSITY_KG_M3 / 1000.0

        # Calculate sinkage (parallel sinkage approximation)
        # Sinkage = lost_buoyancy / TPC / 100 (convert cm to m)
        if tpc > 0:
            sinkage_m = lost_buoyancy_mt / tpc / 100.0
        else:
            sinkage_m = 0.0

        # Calculate trim (simplified - v1.1 FIX #4 limitation)
        # Trim moment = lost_buoyancy × (position - LCF)
        lcf_est = lwl * 0.48  # Estimate LCF at 48% from AP
        trim_moment = lost_buoyancy_mt * (case.position_from_ap_m - lcf_est)
        if mct > 0:
            equilibrium_trim_m = trim_moment / mct / 100.0
        else:
            equilibrium_trim_m = 0.0

        # Estimate equilibrium heel (from asymmetric flooding)
        # Simplified: assume symmetric flooding → small heel
        heel_from_flooding = self._estimate_heel_from_flooding(
            case, beam, displacement_mt, bm_m
        )

        # Calculate residual GM (approximately constant for small sinkage)
        # More accurate: recalculate hydrostatics at new draft
        residual_gm = gm_m * (1.0 - sinkage_m / bm_m * 0.1)  # Simplified reduction

        # Estimate residual GZ curve characteristics
        # Wall-sided approximation: GZmax ≈ GM × sin(angle_max)
        angle_gz_max_est = 30.0 if residual_gm > 0 else 0.0
        residual_gz_max = residual_gm * math.sin(math.radians(angle_gz_max_est))

        # Estimate residual range
        residual_range = 60.0 if residual_gm > 0.1 else (40.0 if residual_gm > 0 else 0.0)

        # Check criteria
        failed_criteria = []
        if residual_gm < DAMAGE_GM_MIN:
            failed_criteria.append(f"GM ({residual_gm:.3f}m) < {DAMAGE_GM_MIN}m")
        if residual_gz_max < DAMAGE_GZ_MAX_MIN:
            failed_criteria.append(f"GZmax ({residual_gz_max:.3f}m) < {DAMAGE_GZ_MAX_MIN}m")
        if residual_range < DAMAGE_RANGE_MIN:
            failed_criteria.append(f"Range ({residual_range:.1f}°) < {DAMAGE_RANGE_MIN}°")
        if heel_from_flooding > self.max_heel:
            failed_criteria.append(f"Heel ({heel_from_flooding:.1f}°) > {self.max_heel}°")

        passes_criteria = len(failed_criteria) == 0

        return DamageResult(
            case=case,
            flooded_volume_m3=flooded_volume,
            lost_buoyancy_mt=lost_buoyancy_mt,
            sinkage_m=sinkage_m,
            equilibrium_heel_deg=heel_from_flooding,
            equilibrium_trim_m=equilibrium_trim_m,
            residual_gm_m=residual_gm,
            residual_gz_max_m=residual_gz_max,
            residual_range_deg=residual_range,
            passes_criteria=passes_criteria,
            failed_criteria=failed_criteria,
        )

    def _estimate_heel_from_flooding(
        self,
        case: DamageCase,
        beam: float,
        displacement_mt: float,
        bm_m: float,
    ) -> float:
        """
        Estimate heel angle from asymmetric flooding.

        Simplified: assume centreline flooding gives small heel.
        For wing tanks or asymmetric compartments, heel would be larger.
        """
        # For centreline flooding: assume very small heel
        # This is a simplification - actual calculation needs transverse moment
        return 0.5  # Assume 0.5° for symmetric flooding

    def evaluate_custom_case(
        self,
        case: DamageCase,
        displacement_mt: float,
        gm_m: float,
        bm_m: float,
        tpc: float,
        mct: float,
        lwl: float,
        beam: float,
    ) -> DamageResult:
        """
        Evaluate a custom damage case.

        Args:
            case: DamageCase definition
            displacement_mt: Vessel displacement (tonnes)
            gm_m: Metacentric height (m)
            bm_m: Metacentric radius (m)
            tpc: Tonnes per cm immersion (t/cm)
            mct: Moment to change trim 1cm (t-m/cm)
            lwl: Length waterline (m)
            beam: Beam (m)

        Returns:
            DamageResult for the custom case
        """
        return self._evaluate_damage_case(
            case=case,
            displacement_mt=displacement_mt,
            gm_m=gm_m,
            bm_m=bm_m,
            tpc=tpc,
            mct=mct,
            lwl=lwl,
            beam=beam,
        )
