"""
MAGNET Resistance Calculator

Module 05 v1.2 - Production-Ready

Resistance calculations using Holtrop-Mennen simplified method for naval architecture.

Implements ITTC-57 friction line and empirical residuary resistance correlations.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import time
import logging
import math

from magnet.core.constants import (
    SEAWATER_DENSITY_KG_M3,
    WATER_KINEMATIC_VISCOSITY,
    GRAVITY_M_S2,
    KNOTS_TO_MS,
    FROUDE_DISPLACEMENT_MAX,
    FROUDE_SEMI_DISPLACEMENT_MAX,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Seawater properties
RHO_SEAWATER = SEAWATER_DENSITY_KG_M3  # 1025.0 kg/m³
NU_SEAWATER = WATER_KINEMATIC_VISCOSITY  # 1.19e-6 m²/s
GRAVITY = GRAVITY_M_S2  # 9.81 m/s²

# ITTC-57 friction line constant
ITTC_57_CONSTANT = 0.075

# Correlation allowance (typical roughness allowance)
CA_ROUGHNESS = 0.0004

# Froude thresholds for warnings
FN_HIGH_WARNING = 0.50  # Planing regime begins
FN_VERY_HIGH_WARNING = 0.70  # Fully planing


# =============================================================================
# INPUT/OUTPUT DEFINITIONS
# =============================================================================

RESISTANCE_INPUTS = [
    "hull.lwl",
    "hull.beam",
    "hull.draft",
    "hull.displacement_mt",
    "hull.wetted_surface_m2",
    "hull.cb",
    "mission.max_speed_kts",
]

RESISTANCE_OUTPUTS = [
    "resistance.total_kn",
    "resistance.frictional_kn",
    "resistance.residuary_kn",
    "resistance.effective_power_kw",
    "resistance.froude_number",
    "resistance.reynolds_number",
]


# =============================================================================
# RESISTANCE RESULTS
# =============================================================================

@dataclass
class ResistanceResults:
    """
    Results from resistance calculations.

    Uses Holtrop-Mennen simplified method for early-stage design.
    """
    # Total resistance
    total_kn: float  # Total resistance in kilonewtons
    total_n: float  # Total resistance in newtons

    # Resistance components
    frictional_kn: float  # Frictional resistance (kN)
    residuary_kn: float  # Residuary (wave-making + form) resistance (kN)
    appendage_kn: float  # Appendage resistance (kN)
    air_kn: float  # Air resistance (kN)

    # Power
    effective_power_kw: float  # Effective power Pe = Rt × V (kW)
    effective_power_hp: float  # Effective power in horsepower

    # Dimensionless numbers
    froude_number: float  # Fn = V / sqrt(g × L)
    reynolds_number: float  # Rn = V × L / ν

    # Coefficients
    cf: float  # Frictional resistance coefficient
    cr: float  # Residuary resistance coefficient
    ct: float  # Total resistance coefficient
    form_factor: float  # Form factor (1 + k1)

    # Speed
    speed_kts: float  # Design speed (knots)
    speed_ms: float  # Design speed (m/s)

    # Metadata
    calculation_time_ms: int = 0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with appropriate precision."""
        return {
            # Resistance (3 decimal places for kN)
            "total_kn": round(self.total_kn, 3),
            "total_n": round(self.total_n, 1),
            "frictional_kn": round(self.frictional_kn, 3),
            "residuary_kn": round(self.residuary_kn, 3),
            "appendage_kn": round(self.appendage_kn, 3),
            "air_kn": round(self.air_kn, 3),
            # Power (2 decimal places)
            "effective_power_kw": round(self.effective_power_kw, 2),
            "effective_power_hp": round(self.effective_power_hp, 2),
            # Dimensionless numbers (4 decimal places)
            "froude_number": round(self.froude_number, 4),
            "reynolds_number": round(self.reynolds_number, 0),
            # Coefficients (6 decimal places)
            "cf": round(self.cf, 6),
            "cr": round(self.cr, 6),
            "ct": round(self.ct, 6),
            "form_factor": round(self.form_factor, 4),
            # Speed
            "speed_kts": round(self.speed_kts, 2),
            "speed_ms": round(self.speed_ms, 3),
            # Metadata
            "calculation_time_ms": self.calculation_time_ms,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResistanceResults":
        """Deserialize from dictionary."""
        return cls(
            total_kn=data.get("total_kn", 0.0),
            total_n=data.get("total_n", 0.0),
            frictional_kn=data.get("frictional_kn", 0.0),
            residuary_kn=data.get("residuary_kn", 0.0),
            appendage_kn=data.get("appendage_kn", 0.0),
            air_kn=data.get("air_kn", 0.0),
            effective_power_kw=data.get("effective_power_kw", 0.0),
            effective_power_hp=data.get("effective_power_hp", 0.0),
            froude_number=data.get("froude_number", 0.0),
            reynolds_number=data.get("reynolds_number", 0.0),
            cf=data.get("cf", 0.0),
            cr=data.get("cr", 0.0),
            ct=data.get("ct", 0.0),
            form_factor=data.get("form_factor", 1.0),
            speed_kts=data.get("speed_kts", 0.0),
            speed_ms=data.get("speed_ms", 0.0),
            calculation_time_ms=data.get("calculation_time_ms", 0),
            warnings=data.get("warnings", []),
        )


# =============================================================================
# RESISTANCE CALCULATOR
# =============================================================================

class ResistanceCalculator:
    """
    Holtrop-Mennen simplified resistance calculator.

    Implements:
    - ITTC-57 friction line for frictional resistance
    - Empirical correlations for residuary resistance
    - Form factor estimation based on hull form

    Accuracy: ±10-15% for displacement hulls in the Fn < 0.4 range.
    Higher Froude numbers require planing hull methods.
    """

    def calculate(
        self,
        lwl: float,
        beam: float,
        draft: float,
        displacement_mt: float,
        wetted_surface: float,
        speed_kts: float,
        cb: float,
        cp: Optional[float] = None,
        lcb_fraction: Optional[float] = None,
        appendage_area: float = 0.0,
        transom_area: float = 0.0,
        superstructure_area: float = 0.0,
    ) -> ResistanceResults:
        """
        Calculate resistance for given hull parameters.

        Args:
            lwl: Length waterline (m)
            beam: Beam (m)
            draft: Draft (m)
            displacement_mt: Displacement (metric tonnes)
            wetted_surface: Wetted surface area (m²)
            speed_kts: Design speed (knots)
            cb: Block coefficient
            cp: Prismatic coefficient (optional, estimated from cb)
            lcb_fraction: LCB as fraction of LWL from midship (+ = fwd)
            appendage_area: Total appendage wetted area (m²)
            transom_area: Transom immersed area (m²)
            superstructure_area: Frontal area of superstructure (m²)

        Returns:
            ResistanceResults with all calculated values
        """
        start_time = time.perf_counter()
        warnings: List[str] = []

        # Validate required inputs
        if lwl <= 0 or beam <= 0 or draft <= 0:
            raise ValueError(
                f"Invalid dimensions: lwl={lwl}, beam={beam}, draft={draft}. "
                "All must be positive."
            )

        if displacement_mt <= 0 or wetted_surface <= 0:
            raise ValueError(
                f"Invalid hydrostatics: displacement_mt={displacement_mt}, "
                f"wetted_surface={wetted_surface}. All must be positive."
            )

        if speed_kts <= 0:
            raise ValueError(f"Invalid speed: {speed_kts} kts. Must be positive.")

        if cb <= 0 or cb > 1:
            raise ValueError(f"Invalid block coefficient: {cb}. Must be in (0, 1].")

        # Convert speed
        speed_ms = speed_kts * KNOTS_TO_MS

        # Calculate volume
        volume_m3 = displacement_mt * 1000.0 / RHO_SEAWATER

        # Estimate missing coefficients
        if cp is None:
            # Estimate Cp from Cb (typical relationship)
            cm_estimated = min(cb + 0.10, 0.98)
            cp = cb / cm_estimated
            warnings.append(f"Cp estimated as {cp:.3f}")

        if lcb_fraction is None:
            # Default LCB at 2% aft of midship for typical forms
            lcb_fraction = -0.02
            warnings.append(f"LCB fraction assumed as {lcb_fraction}")

        # Calculate dimensionless numbers
        froude_number = self._calculate_froude_number(speed_ms, lwl)
        reynolds_number = self._calculate_reynolds_number(speed_ms, lwl)

        # Add warnings for high Froude numbers
        if froude_number > FN_VERY_HIGH_WARNING:
            warnings.append(
                f"Froude number {froude_number:.3f} > {FN_VERY_HIGH_WARNING}: "
                "Fully planing regime. Results unreliable."
            )
        elif froude_number > FN_HIGH_WARNING:
            warnings.append(
                f"Froude number {froude_number:.3f} > {FN_HIGH_WARNING}: "
                "Semi-planing regime. Results less accurate."
            )

        # Calculate frictional resistance coefficient (ITTC-57)
        cf = self._calculate_cf_ittc57(reynolds_number)

        # Calculate form factor
        form_factor = self._calculate_form_factor(
            lwl, beam, draft, volume_m3, cp, lcb_fraction
        )

        # Calculate residuary resistance coefficient
        cr = self._calculate_cr(
            froude_number, cb, cp, lwl, beam, draft, volume_m3, transom_area
        )

        # Add correlation allowance
        ca = CA_ROUGHNESS

        # Total resistance coefficient
        ct = (cf * form_factor) + cr + ca

        # Calculate resistance forces
        dynamic_pressure = 0.5 * RHO_SEAWATER * speed_ms ** 2

        rf_n = cf * form_factor * dynamic_pressure * wetted_surface
        rr_n = cr * dynamic_pressure * wetted_surface

        # Appendage resistance (simplified)
        rapp_n = 0.0
        if appendage_area > 0:
            cf_app = cf * 1.2  # Appendages have higher local friction
            rapp_n = cf_app * dynamic_pressure * appendage_area

        # Air resistance (simplified)
        rair_n = 0.0
        if superstructure_area > 0:
            cd_air = 0.8  # Typical drag coefficient for superstructure
            rair_n = 0.5 * 1.225 * speed_ms ** 2 * cd_air * superstructure_area

        # Total resistance
        rt_n = rf_n + rr_n + rapp_n + rair_n

        # Convert to kilonewtons
        rt_kn = rt_n / 1000.0
        rf_kn = rf_n / 1000.0
        rr_kn = rr_n / 1000.0
        rapp_kn = rapp_n / 1000.0
        rair_kn = rair_n / 1000.0

        # Calculate effective power
        pe_w = rt_n * speed_ms
        pe_kw = pe_w / 1000.0
        pe_hp = pe_kw * 1.34102

        # Calculate elapsed time
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return ResistanceResults(
            total_kn=rt_kn,
            total_n=rt_n,
            frictional_kn=rf_kn,
            residuary_kn=rr_kn,
            appendage_kn=rapp_kn,
            air_kn=rair_kn,
            effective_power_kw=pe_kw,
            effective_power_hp=pe_hp,
            froude_number=froude_number,
            reynolds_number=reynolds_number,
            cf=cf,
            cr=cr,
            ct=ct,
            form_factor=form_factor,
            speed_kts=speed_kts,
            speed_ms=speed_ms,
            calculation_time_ms=elapsed_ms,
            warnings=warnings,
        )

    # =========================================================================
    # DIMENSIONLESS NUMBERS
    # =========================================================================

    def _calculate_froude_number(self, speed_ms: float, lwl: float) -> float:
        """
        Calculate Froude number.

        Fn = V / sqrt(g × L)

        Args:
            speed_ms: Speed in m/s
            lwl: Length waterline in m

        Returns:
            Froude number (dimensionless)
        """
        if lwl <= 0:
            return 0.0
        return speed_ms / math.sqrt(GRAVITY * lwl)

    def _calculate_reynolds_number(self, speed_ms: float, lwl: float) -> float:
        """
        Calculate Reynolds number.

        Rn = V × L / ν

        Args:
            speed_ms: Speed in m/s
            lwl: Length waterline in m

        Returns:
            Reynolds number (dimensionless)
        """
        if lwl <= 0 or NU_SEAWATER <= 0:
            return 0.0
        return (speed_ms * lwl) / NU_SEAWATER

    # =========================================================================
    # FRICTIONAL RESISTANCE
    # =========================================================================

    def _calculate_cf_ittc57(self, reynolds_number: float) -> float:
        """
        Calculate frictional resistance coefficient using ITTC-57 line.

        Cf = 0.075 / (log10(Rn) - 2)²

        This is the internationally accepted correlation for flat plate
        friction in turbulent flow.

        Args:
            reynolds_number: Reynolds number

        Returns:
            Frictional resistance coefficient
        """
        if reynolds_number <= 100:
            # Below turbulent threshold, use laminar approximation
            return 1.328 / math.sqrt(max(reynolds_number, 1))

        log_rn = math.log10(reynolds_number)
        denominator = log_rn - 2.0

        if abs(denominator) < 0.01:
            return 0.01  # Prevent division by zero

        cf = ITTC_57_CONSTANT / (denominator ** 2)
        return cf

    # =========================================================================
    # FORM FACTOR
    # =========================================================================

    def _calculate_form_factor(
        self,
        lwl: float,
        beam: float,
        draft: float,
        volume_m3: float,
        cp: float,
        lcb_fraction: float,
    ) -> float:
        """
        Calculate form factor (1 + k1) using Holtrop correlation.

        (1 + k1) = 0.93 + 0.487118 × c14 × (B/L)^1.06806 × (T/L)^0.46106
                   × (L/∇^(1/3))^0.121563 × (L³/∇)^0.36486 × (1-Cp)^(-0.604247)

        Simplified version for early-stage design.

        Args:
            lwl: Length waterline (m)
            beam: Beam (m)
            draft: Draft (m)
            volume_m3: Displaced volume (m³)
            cp: Prismatic coefficient
            lcb_fraction: LCB fraction from midship

        Returns:
            Form factor (1 + k1)
        """
        if lwl <= 0 or volume_m3 <= 0 or cp <= 0:
            return 1.15  # Default form factor

        # Length ratios
        bl_ratio = beam / lwl
        tl_ratio = draft / lwl
        l_over_vol_third = lwl / (volume_m3 ** (1.0 / 3.0))
        l3_over_vol = (lwl ** 3) / volume_m3

        # c14 coefficient (stern type - assume normal stern)
        c14 = 1.0 + 0.011 * abs(lcb_fraction) * 100  # Convert fraction to %

        # Prevent cp from being exactly 1 (would cause division by zero)
        cp_term = max(1 - cp, 0.001)

        # Simplified Holtrop formula
        try:
            k1 = (
                0.93
                + 0.487118 * c14
                * (bl_ratio ** 1.06806)
                * (tl_ratio ** 0.46106)
                * (l_over_vol_third ** 0.121563)
                * (l3_over_vol ** 0.36486)
                * (cp_term ** (-0.604247))
            )
        except (ValueError, OverflowError):
            # Fallback for numerical issues
            k1 = 1.15

        # Clamp to reasonable range
        k1 = max(min(k1, 1.60), 1.0)

        return k1

    # =========================================================================
    # RESIDUARY RESISTANCE
    # =========================================================================

    def _calculate_cr(
        self,
        fn: float,
        cb: float,
        cp: float,
        lwl: float,
        beam: float,
        draft: float,
        volume_m3: float,
        transom_area: float,
    ) -> float:
        """
        Calculate residuary resistance coefficient.

        Uses simplified Holtrop-Mennen correlation for wave-making resistance.

        Args:
            fn: Froude number
            cb: Block coefficient
            cp: Prismatic coefficient
            lwl: Length waterline (m)
            beam: Beam (m)
            draft: Draft (m)
            volume_m3: Displaced volume (m³)
            transom_area: Immersed transom area (m²)

        Returns:
            Residuary resistance coefficient
        """
        if fn <= 0:
            return 0.0

        # Base residuary coefficient from Fn
        # This is a simplified polynomial fit to Holtrop data
        if fn < 0.1:
            # Very low speed - minimal wave making
            cr_base = 0.0001 * fn ** 2
        elif fn < 0.4:
            # Displacement regime - primary hump around Fn = 0.35
            # Simplified polynomial approximation
            cr_base = (
                0.0014 * fn ** 2
                - 0.0002 * fn
                + 0.0001
            )
            # Increase near the hump
            if fn > 0.25:
                hump_factor = 1.0 + 2.0 * (fn - 0.25) ** 2
                cr_base *= hump_factor
        elif fn < 0.55:
            # Transition region - hollow after primary hump
            cr_base = 0.001 + 0.002 * (fn - 0.4)
        else:
            # High Fn - secondary hump and planing onset
            cr_base = 0.002 + 0.015 * (fn - 0.55) ** 1.5

        # Hull form corrections
        # Fuller forms have higher residuary resistance
        cb_correction = 1.0 + 2.0 * (cb - 0.5)
        cb_correction = max(min(cb_correction, 2.0), 0.5)

        # L/B ratio correction (slender hulls are more efficient)
        lb_ratio = lwl / beam if beam > 0 else 6.0
        lb_correction = 1.0 + 0.5 * max(0, 5.0 - lb_ratio)

        # B/T ratio correction
        bt_ratio = beam / draft if draft > 0 else 3.0
        bt_correction = 1.0 + 0.1 * max(0, bt_ratio - 3.0)

        # Transom correction
        transom_correction = 1.0
        if transom_area > 0 and volume_m3 > 0:
            at_ratio = transom_area / (volume_m3 ** (2.0 / 3.0))
            # Immersed transom adds resistance at low speeds,
            # reduces it at high speeds (planing benefit)
            if fn < 0.4:
                transom_correction = 1.0 + 0.5 * at_ratio
            else:
                transom_correction = 1.0 - 0.2 * at_ratio * (fn - 0.4)
            transom_correction = max(transom_correction, 0.8)

        # Total residuary coefficient
        cr = cr_base * cb_correction * lb_correction * bt_correction * transom_correction

        return max(cr, 0.0)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_resistance(
    lwl: float,
    beam: float,
    draft: float,
    displacement_mt: float,
    wetted_surface: float,
    speed_kts: float,
    cb: float,
    **kwargs
) -> ResistanceResults:
    """
    Convenience function for resistance calculation.

    Args:
        See ResistanceCalculator.calculate()

    Returns:
        ResistanceResults
    """
    calculator = ResistanceCalculator()
    return calculator.calculate(
        lwl=lwl,
        beam=beam,
        draft=draft,
        displacement_mt=displacement_mt,
        wetted_surface=wetted_surface,
        speed_kts=speed_kts,
        cb=cb,
        **kwargs
    )
