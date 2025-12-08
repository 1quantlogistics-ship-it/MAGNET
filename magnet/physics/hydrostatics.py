"""
MAGNET Hydrostatics Calculator

Module 05 v1.2 - Production-Ready

Parametric hydrostatics calculations for naval architecture.

v1.2 Changes:
- FIX #1-7: Added kb_m, bm_m, tpc, mct, lcf_m, waterplane_area_m2, freeboard
- Total outputs: 11 (up from 6)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
import time
import logging
import math

from magnet.core.constants import SEAWATER_DENSITY_KG_M3

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Seawater density (kg/m³)
RHO_SEAWATER = SEAWATER_DENSITY_KG_M3  # 1025.0

# Inertia coefficient for waterplane (typical values)
CI_MONOHULL = 0.5  # Coefficient for I_T calculation
CI_DEEP_V = 0.45
CI_CATAMARAN = 0.55

# Default freeboard if depth not provided (m)
DEFAULT_FREEBOARD_M = 1.5


# =============================================================================
# INPUT/OUTPUT DEFINITIONS
# =============================================================================

HYDROSTATICS_INPUTS = [
    "hull.lwl",
    "hull.beam",
    "hull.draft",
    "hull.depth",
    "hull.cb",
    "hull.cp",
    "hull.cm",
    "hull.cwp",
    "hull.hull_type",
    "hull.deadrise_deg",
]

HYDROSTATICS_OUTPUTS = [
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
]


# =============================================================================
# HYDROSTATICS RESULTS
# =============================================================================

@dataclass
class HydrostaticsResults:
    """
    Results from hydrostatics calculations.

    v1.2: Now includes 11 output fields per specification.
    """
    # Displacement
    displacement_mt: float  # Displacement in metric tonnes
    volume_displaced_m3: float  # Displaced volume in m³

    # Vertical Centers
    kb_m: float  # Height of center of buoyancy from keel (m)
    bm_m: float  # Metacentric radius (m)
    km_m: float  # Height of metacenter from keel (m) = KB + BM
    lcb_m: float  # Longitudinal center of buoyancy from AP (m)
    vcb_m: float  # Vertical center of buoyancy (alias for kb_m)

    # Waterplane Properties
    waterplane_area_m2: float  # Waterplane area (m²)
    lcf_m: float  # Longitudinal center of flotation from AP (m)
    moment_of_inertia_l_m4: float  # Longitudinal moment of inertia (m⁴)
    moment_of_inertia_t_m4: float  # Transverse moment of inertia (m⁴)

    # Trim/Stability Parameters
    tpc: float  # Tonnes per cm immersion (t/cm)
    mct: float  # Moment to change trim 1cm (t-m/cm)

    # Wetted Surface & Freeboard
    wetted_surface_m2: float  # Wetted surface area (m²)
    freeboard_m: float  # Freeboard at midship (m)

    # Metadata
    hull_type: str = "monohull"
    deadrise_deg: float = 0.0
    calculation_time_ms: int = 0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with appropriate precision."""
        return {
            # Displacement (2 decimal places for MT, 3 for m³)
            "displacement_mt": round(self.displacement_mt, 2),
            "volume_displaced_m3": round(self.volume_displaced_m3, 3),
            # Vertical/longitudinal distances (3 decimal places)
            "kb_m": round(self.kb_m, 3),
            "bm_m": round(self.bm_m, 3),
            "km_m": round(self.km_m, 3),
            "lcb_m": round(self.lcb_m, 3),
            "vcb_m": round(self.vcb_m, 3),
            "lcf_m": round(self.lcf_m, 3),
            "freeboard_m": round(self.freeboard_m, 3),
            # Areas (2 decimal places)
            "waterplane_area_m2": round(self.waterplane_area_m2, 2),
            "wetted_surface_m2": round(self.wetted_surface_m2, 2),
            # Moments of inertia (3 decimal places)
            "moment_of_inertia_l_m4": round(self.moment_of_inertia_l_m4, 3),
            "moment_of_inertia_t_m4": round(self.moment_of_inertia_t_m4, 3),
            # TPC (4 decimal places), MCT (2 decimal places)
            "tpc": round(self.tpc, 4),
            "mct": round(self.mct, 2),
            # Metadata
            "hull_type": self.hull_type,
            "deadrise_deg": round(self.deadrise_deg, 1),
            "calculation_time_ms": self.calculation_time_ms,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HydrostaticsResults":
        """Deserialize from dictionary."""
        return cls(
            displacement_mt=data.get("displacement_mt", 0.0),
            volume_displaced_m3=data.get("volume_displaced_m3", 0.0),
            kb_m=data.get("kb_m", 0.0),
            bm_m=data.get("bm_m", 0.0),
            km_m=data.get("km_m", 0.0),
            lcb_m=data.get("lcb_m", 0.0),
            vcb_m=data.get("vcb_m", 0.0),
            waterplane_area_m2=data.get("waterplane_area_m2", 0.0),
            lcf_m=data.get("lcf_m", 0.0),
            moment_of_inertia_l_m4=data.get("moment_of_inertia_l_m4", 0.0),
            moment_of_inertia_t_m4=data.get("moment_of_inertia_t_m4", 0.0),
            tpc=data.get("tpc", 0.0),
            mct=data.get("mct", 0.0),
            wetted_surface_m2=data.get("wetted_surface_m2", 0.0),
            freeboard_m=data.get("freeboard_m", 0.0),
            hull_type=data.get("hull_type", "monohull"),
            deadrise_deg=data.get("deadrise_deg", 0.0),
            calculation_time_ms=data.get("calculation_time_ms", 0),
            warnings=data.get("warnings", []),
        )


# =============================================================================
# HYDROSTATICS CALCULATOR
# =============================================================================

class HydrostaticsCalculator:
    """
    Parametric hydrostatics calculator.

    Implements empirical formulas for early-stage naval design.
    Accuracy: ±2% displacement, ±5% parametric estimates.

    v1.2: Now produces 11 output fields.
    """

    def calculate(
        self,
        lwl: float,
        beam: float,
        draft: float,
        depth: float,
        cb: float,
        cp: Optional[float] = None,
        cm: Optional[float] = None,
        cwp: Optional[float] = None,
        hull_type: str = "monohull",
        deadrise_deg: float = 0.0,
    ) -> HydrostaticsResults:
        """
        Calculate hydrostatics for given hull parameters.

        Args:
            lwl: Length waterline (m)
            beam: Beam (m)
            draft: Draft (m)
            depth: Depth to main deck (m)
            cb: Block coefficient
            cp: Prismatic coefficient (optional, estimated from cb/cm)
            cm: Midship coefficient (optional, estimated from cb)
            cwp: Waterplane coefficient (optional, estimated from cb)
            hull_type: "monohull", "deep_v", or "catamaran"
            deadrise_deg: Deadrise angle at midship (degrees)

        Returns:
            HydrostaticsResults with all calculated values
        """
        start_time = time.perf_counter()
        warnings: List[str] = []

        # Validate required inputs
        if lwl <= 0 or beam <= 0 or draft <= 0 or cb <= 0:
            raise ValueError(
                f"Invalid inputs: lwl={lwl}, beam={beam}, draft={draft}, cb={cb}. "
                "All must be positive."
            )

        # Estimate missing coefficients
        if cm is None:
            cm = self._estimate_cm(cb, hull_type, deadrise_deg)
            warnings.append(f"Cm estimated as {cm:.3f}")

        if cp is None:
            cp = self._estimate_cp(cb, cm)
            warnings.append(f"Cp estimated as {cp:.3f}")

        if cwp is None:
            cwp = self._estimate_cwp(cb, hull_type)
            warnings.append(f"Cwp estimated as {cwp:.3f}")

        # Handle missing depth
        if depth <= 0:
            depth = draft + DEFAULT_FREEBOARD_M
            warnings.append(f"Depth assumed as draft + {DEFAULT_FREEBOARD_M}m = {depth:.2f}m")

        # Calculate volume and displacement
        volume = self._calculate_volume(lwl, beam, draft, cb)
        displacement_mt = volume * RHO_SEAWATER / 1000.0

        # Calculate vertical center of buoyancy (KB)
        kb = self._calculate_kb(draft, cb, hull_type)

        # Calculate waterplane area
        awp = lwl * beam * cwp

        # Calculate moments of inertia
        ci = self._get_inertia_coefficient(hull_type)
        it = (1.0 / 12.0) * lwl * (beam ** 3) * ci * cwp  # Transverse
        il = (1.0 / 12.0) * beam * (lwl ** 3) * ci * cwp  # Longitudinal

        # Calculate metacentric radius (BM)
        bm = self._calculate_bm(it, volume, hull_type)
        bml = il / volume if volume > 0 else 0.0  # Longitudinal BM

        # Calculate KM
        km = kb + bm

        # Calculate longitudinal centers
        lcb = self._calculate_lcb(lwl, cb, cp, hull_type)
        lcf = self._calculate_lcf(lwl, cwp, hull_type)

        # Calculate TPC and MCT
        tpc = self._calculate_tpc(awp)
        # MCT requires GM_L estimate: use KB + BML - KG (assume KG ≈ 0.5 * depth for estimate)
        kg_estimate = 0.5 * depth
        gml_estimate = kb + bml - kg_estimate
        mct = self._calculate_mct(displacement_mt, gml_estimate, lwl)

        # Calculate wetted surface
        wetted_surface = self._calculate_wetted_surface(
            lwl, beam, draft, cb, cm, hull_type, deadrise_deg
        )

        # Calculate freeboard
        freeboard = depth - draft
        if freeboard < 0:
            warnings.append(f"Negative freeboard: {freeboard:.3f}m (depth < draft)")

        # Calculate elapsed time
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return HydrostaticsResults(
            displacement_mt=displacement_mt,
            volume_displaced_m3=volume,
            kb_m=kb,
            bm_m=bm,
            km_m=km,
            lcb_m=lcb,
            vcb_m=kb,  # Alias for KB
            waterplane_area_m2=awp,
            lcf_m=lcf,
            moment_of_inertia_l_m4=il,
            moment_of_inertia_t_m4=it,
            tpc=tpc,
            mct=mct,
            wetted_surface_m2=wetted_surface,
            freeboard_m=freeboard,
            hull_type=hull_type,
            deadrise_deg=deadrise_deg,
            calculation_time_ms=elapsed_ms,
            warnings=warnings,
        )

    # =========================================================================
    # COEFFICIENT ESTIMATION
    # =========================================================================

    def _estimate_cm(self, cb: float, hull_type: str, deadrise_deg: float) -> float:
        """
        Estimate midship coefficient from block coefficient.

        For monohull: Cm ≈ Cb + 0.1 (typical)
        For deep-v: Adjusted for deadrise
        """
        if hull_type == "deep_v":
            # Deep-V has lower Cm due to deadrise
            cm = cb + 0.05 - 0.002 * deadrise_deg
        elif hull_type == "catamaran":
            cm = cb + 0.15
        else:
            # Monohull
            cm = cb + 0.10

        return min(max(cm, 0.5), 0.99)  # Clamp to valid range

    def _estimate_cp(self, cb: float, cm: float) -> float:
        """
        Estimate prismatic coefficient from Cb and Cm.

        Cp = Cb / Cm (by definition)
        """
        if cm > 0:
            return cb / cm
        return cb / 0.85  # Fallback

    def _estimate_cwp(self, cb: float, hull_type: str) -> float:
        """
        Estimate waterplane coefficient from block coefficient.

        Cwp ≈ 0.18 + 0.86 × Cb (Schneekluth approximation)
        """
        if hull_type == "deep_v":
            cwp = 0.15 + 0.80 * cb
        elif hull_type == "catamaran":
            cwp = 0.20 + 0.85 * cb
        else:
            # Monohull (Schneekluth)
            cwp = 0.18 + 0.86 * cb

        return min(max(cwp, 0.50), 0.95)  # Clamp to valid range

    # =========================================================================
    # HYDROSTATIC CALCULATIONS
    # =========================================================================

    def _calculate_volume(
        self, lwl: float, beam: float, draft: float, cb: float
    ) -> float:
        """Calculate displaced volume: V = LWL × B × T × Cb"""
        return lwl * beam * draft * cb

    def _calculate_kb(self, draft: float, cb: float, hull_type: str) -> float:
        """
        Calculate height of center of buoyancy (KB).

        Morrish approximation for monohull:
            KB = T × (5/6 - Cb/3)

        Deep-V approximation:
            KB = T × (0.78 - 0.285 × Cb)
        """
        if hull_type == "deep_v":
            # Deep-V hull: center of buoyancy is higher
            return draft * (0.78 - 0.285 * cb)
        elif hull_type == "catamaran":
            # Catamaran: similar to monohull per hull
            return draft * (5.0 / 6.0 - cb / 3.0)
        else:
            # Monohull (Morrish)
            return draft * (5.0 / 6.0 - cb / 3.0)

    def _get_inertia_coefficient(self, hull_type: str) -> float:
        """Get inertia coefficient based on hull type."""
        if hull_type == "deep_v":
            return CI_DEEP_V
        elif hull_type == "catamaran":
            return CI_CATAMARAN
        else:
            return CI_MONOHULL

    def _calculate_bm(
        self, it: float, volume: float, hull_type: str
    ) -> float:
        """
        Calculate metacentric radius (BM).

        BM = I_T / V

        For catamaran: Apply parallel axis theorem.
        """
        if volume <= 0:
            return 0.0

        bm = it / volume

        if hull_type == "catamaran":
            # Catamaran has much higher BM due to hull spacing
            # This is a simplified multiplier; actual calculation
            # requires hull separation distance
            bm *= 2.5

        return bm

    def _calculate_lcb(
        self, lwl: float, cb: float, cp: float, hull_type: str
    ) -> float:
        """
        Calculate longitudinal center of buoyancy from AP.

        LCB ≈ 0.44 × LWL for typical displacement hulls
        Adjusted based on Cp (fuller forms have LCB further aft)
        """
        # Base LCB as fraction of LWL from AP
        if hull_type == "deep_v":
            lcb_fraction = 0.40 + 0.08 * cp
        elif hull_type == "catamaran":
            lcb_fraction = 0.42 + 0.10 * cp
        else:
            # Monohull
            lcb_fraction = 0.44 + 0.06 * (cp - 0.65)

        return lwl * lcb_fraction

    def _calculate_lcf(self, lwl: float, cwp: float, hull_type: str) -> float:
        """
        Calculate longitudinal center of flotation from AP.

        LCF ≈ (0.48 - 0.05 × Cwp) × LWL for typical forms
        """
        if hull_type == "deep_v":
            lcf_fraction = 0.45 - 0.08 * cwp
        elif hull_type == "catamaran":
            lcf_fraction = 0.48 - 0.06 * cwp
        else:
            # Monohull
            lcf_fraction = 0.48 - 0.05 * cwp

        return lwl * lcf_fraction

    def _calculate_tpc(self, awp: float) -> float:
        """
        Calculate tonnes per cm immersion.

        TPC = (ρ × Awp) / 100000  [t/cm]

        Where:
        - ρ = seawater density (kg/m³)
        - Awp = waterplane area (m²)
        """
        return (RHO_SEAWATER * awp) / 100000.0

    def _calculate_mct(
        self, displacement_mt: float, gml: float, lwl: float
    ) -> float:
        """
        Calculate moment to change trim 1 cm.

        MCT = (Δ × GM_L) / (100 × LWL)  [t-m/cm]

        Where:
        - Δ = displacement (t)
        - GM_L = longitudinal metacentric height (m)
        - LWL = length waterline (m)
        """
        if lwl <= 0:
            return 0.0

        return (displacement_mt * gml) / (100.0 * lwl)

    def _calculate_wetted_surface(
        self,
        lwl: float,
        beam: float,
        draft: float,
        cb: float,
        cm: float,
        hull_type: str,
        deadrise_deg: float,
    ) -> float:
        """
        Calculate wetted surface area.

        Denny-Mumford formula for monohull:
            S = 1.7 × LWL × T + V / T

        Holtrop approximation:
            S = LWL × (2T + B) × sqrt(Cm) × (0.453 + 0.4425 × Cb)

        Deep-V adjustment for deadrise angle.
        """
        volume = lwl * beam * draft * cb

        if hull_type == "deep_v":
            # Adjusted for deadrise angle
            deadrise_factor = 1.0 + 0.01 * deadrise_deg
            # Use modified Holtrop
            s = lwl * (2 * draft + beam) * math.sqrt(cm) * (0.453 + 0.4425 * cb)
            return s * deadrise_factor

        elif hull_type == "catamaran":
            # Per-hull wetted surface × 2
            # Simplified: each hull is narrower
            hull_beam = beam / 3.0  # Approximate demihull beam
            s_per_hull = lwl * (2 * draft + hull_beam) * math.sqrt(cm) * (0.453 + 0.4425 * cb)
            return s_per_hull * 2.0

        else:
            # Monohull - Holtrop approximation
            s = lwl * (2 * draft + beam) * math.sqrt(cm) * (0.453 + 0.4425 * cb)
            return s
