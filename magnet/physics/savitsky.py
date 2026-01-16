"""
MAGNET Savitsky Planing Resistance Calculator

Implements a practical Savitsky-style planing resistance model suitable for early-stage design.

Reference:
  Savitsky, D. (1964). "Hydrodynamic Design of Planing Hulls"
  Marine Technology, Vol. 1, No. 1

Scope / Validity (rule-of-thumb):
  - Planing regime: Fn (LWL) > ~0.7 (routing handled by ResistanceValidator)
  - Beam Froude number Fn_b = V / sqrt(g*b) typically > ~1.0 for fully planing
  - Constant deadrise planing bottoms (10–30 deg preferred)
  - Prismatic hull assumptions; appendages/air drag supported via simple areas
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import math
import time
import logging

from magnet.core.constants import (
    SEAWATER_DENSITY_KG_M3,
    WATER_KINEMATIC_VISCOSITY,
    GRAVITY_M_S2,
    KNOTS_TO_MS,
)

logger = logging.getLogger(__name__)


RHO_SEAWATER = SEAWATER_DENSITY_KG_M3  # 1025.0 kg/m³
NU_SEAWATER = WATER_KINEMATIC_VISCOSITY  # 1.19e-6 m²/s
GRAVITY = GRAVITY_M_S2  # 9.81 m/s²
RHO_AIR = 1.225  # kg/m³


@dataclass(frozen=True)
class SavitskyInputs:
    """Inputs for Savitsky planing resistance calculation."""

    speed_kts: float
    beam_m: float  # Chine beam (planing beam)
    deadrise_deg: float
    displacement_kg: float  # Total supported weight (kg)
    lcg_from_transom_m: float  # LCG measured forward from transom (m)

    # Optional refinements
    vcg_m: Optional[float] = None  # VCG above keel (m) - not currently used
    deadrise_transom_deg: Optional[float] = None  # Not currently used
    appendage_area_m2: float = 0.0
    air_drag_area_m2: float = 0.0


@dataclass
class SavitskyResults:
    """Outputs from Savitsky planing resistance calculation."""

    # Primary
    total_resistance_kn: float
    effective_power_kw: float

    # Dynamic behavior
    running_trim_deg: float
    wetted_length_m: float
    wetted_surface_m2: float
    draft_at_transom_m: float

    # Coefficients (dimensionless)
    lift_coefficient: float  # CL_beta
    drag_coefficient: float  # CD (total)
    friction_coefficient: float  # Cf (ITTC-57)

    # Components
    friction_resistance_kn: float
    pressure_resistance_kn: float
    appendage_resistance_kn: float
    air_resistance_kn: float

    # Dimensionless numbers
    froude_beam: float  # Fn_b = V / sqrt(g*b)
    reynolds_number: float
    speed_coefficient: float  # Cv (same as Fn_b here)

    # Validity
    method_valid: bool
    validity_note: str
    warnings: List[str] = field(default_factory=list)
    calculation_time_ms: int = 0


class SavitskyCalculator:
    """
    Savitsky-style planing resistance model.

    Notes:
      - This implementation prioritizes robustness and reasonable outputs over
        full-fidelity Savitsky moment equilibrium details.
      - We solve for trim angle by matching a lift equation + a simple longitudinal
        balance heuristic (LCG vs center of pressure).
    """

    # Search bounds / defaults
    TRIM_DEG_MIN = 2.0
    TRIM_DEG_MAX = 12.0
    TRIM_DEG_STEPS = 51

    LAMBDA_MIN = 0.75
    LAMBDA_MAX = 6.0

    def calculate(self, inputs: SavitskyInputs) -> SavitskyResults:
        start = time.perf_counter()
        warnings: List[str] = []

        # Validate
        if inputs.speed_kts <= 0:
            raise ValueError(f"Invalid speed_kts={inputs.speed_kts}; must be > 0")
        if inputs.beam_m <= 0:
            raise ValueError(f"Invalid beam_m={inputs.beam_m}; must be > 0")
        if inputs.displacement_kg <= 0:
            raise ValueError(
                f"Invalid displacement_kg={inputs.displacement_kg}; must be > 0"
            )

        V = float(inputs.speed_kts) * KNOTS_TO_MS
        b = float(inputs.beam_m)
        beta_deg = float(inputs.deadrise_deg)
        beta_rad = math.radians(beta_deg)
        W = float(inputs.displacement_kg) * GRAVITY  # N
        lcg = max(0.0, float(inputs.lcg_from_transom_m))

        Cv = V / math.sqrt(GRAVITY * b) if b > 0 else 0.0
        Fn_b = Cv

        # Required lift coefficient (beta-deadrise)
        q = 0.5 * RHO_SEAWATER * V * V
        cl_beta_req = W / (q * b * b) if (q > 0 and b > 0) else 0.0

        # Convert to equivalent zero-deadrise lift coefficient (approx inverse)
        cl0_req = self._invert_deadrise_lift(cl_beta_req, beta_deg)

        # Solve equilibrium trim + wetted length ratio lambda = L/b
        tau_deg, lam, x_cp = self._solve_trim_and_lambda(
            cl0_req=cl0_req,
            Cv=Cv,
            lcg_from_transom_m=lcg,
            beam_m=b,
        )

        tau_rad = math.radians(tau_deg)

        # Lift coefficient with deadrise correction
        cl_beta = self._apply_deadrise_lift(cl0_req, beta_deg)

        # Wetted length (meters)
        l_wet = lam * b

        # Wetted bottom surface area (planing patch)
        wetted_surface = (l_wet * b) / max(1e-6, math.cos(beta_rad))

        # Reynolds number (use wetted length as characteristic length)
        Rn = V * l_wet / NU_SEAWATER if NU_SEAWATER > 0 else 0.0
        cf = self._ittc57_cf(Rn, warnings)

        # Friction resistance
        Rf = q * wetted_surface * cf  # N (since q = 0.5*rho*V^2)

        # Pressure / induced component (simple trim penalty)
        Rp = W * math.tan(tau_rad)

        # Appendage drag (very rough)
        Cd_app = 1.0
        R_app = q * float(inputs.appendage_area_m2) * Cd_app

        # Air drag (very rough)
        Cd_air = 0.8
        R_air = 0.5 * RHO_AIR * V * V * float(inputs.air_drag_area_m2) * Cd_air

        R_total = Rf + Rp + R_app + R_air
        total_kn = R_total / 1000.0

        # Effective power
        Pe_kw = (R_total * V) / 1000.0

        # Draft at transom (running trim line over wetted length)
        draft_transom = l_wet * math.sin(tau_rad)

        # Total drag coefficient
        cd = R_total / (q * b * b) if (q > 0 and b > 0) else 0.0

        # Validity checks
        method_valid = True
        validity_notes: List[str] = []

        if Fn_b < 1.0:
            method_valid = False
            validity_notes.append(f"Fn_beam={Fn_b:.2f} < 1.0: may not be fully planing")
            warnings.append("Low beam Froude number - hull may not be fully planing")

        if beta_deg < 10.0:
            method_valid = False
            warnings.append(f"Deadrise {beta_deg:.1f}° < 10°: outside typical Savitsky range")
        elif beta_deg > 30.0:
            method_valid = False
            warnings.append(f"Deadrise {beta_deg:.1f}° > 30°: outside typical Savitsky range")

        if lam < 1.0 or lam > 6.0:
            method_valid = False
            warnings.append(f"Wetted length ratio λ={lam:.2f} outside typical range [1, 6]")

        validity_note = (
            "Savitsky method valid for planing regime" if method_valid else "; ".join(validity_notes) or "Savitsky validity: outside typical range"
        )

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        return SavitskyResults(
            total_resistance_kn=float(total_kn),
            effective_power_kw=float(Pe_kw),
            running_trim_deg=float(tau_deg),
            wetted_length_m=float(l_wet),
            wetted_surface_m2=float(wetted_surface),
            draft_at_transom_m=float(draft_transom),
            lift_coefficient=float(cl_beta),
            drag_coefficient=float(cd),
            friction_coefficient=float(cf),
            friction_resistance_kn=float(Rf / 1000.0),
            pressure_resistance_kn=float(Rp / 1000.0),
            appendage_resistance_kn=float(R_app / 1000.0),
            air_resistance_kn=float(R_air / 1000.0),
            froude_beam=float(Fn_b),
            reynolds_number=float(Rn),
            speed_coefficient=float(Cv),
            method_valid=bool(method_valid),
            validity_note=validity_note,
            warnings=warnings,
            calculation_time_ms=elapsed_ms,
        )

    # =========================================================================
    # Internal helpers
    # =========================================================================

    def _solve_trim_and_lambda(
        self,
        cl0_req: float,
        Cv: float,
        lcg_from_transom_m: float,
        beam_m: float,
    ) -> Tuple[float, float, float]:
        """
        Solve for running trim and wetted length ratio λ by:
          - matching Savitsky CL0 equation, and
          - minimizing longitudinal balance error (LCG vs center of pressure).

        Returns:
            (trim_deg, lambda, x_cp_m)
        """
        best = None

        b = max(1e-6, float(beam_m))
        lcg_over_b = max(0.0, float(lcg_from_transom_m)) / b

        # Sweep trim candidates (deterministic and robust)
        for i in range(self.TRIM_DEG_STEPS):
            tau_deg = self.TRIM_DEG_MIN + (self.TRIM_DEG_MAX - self.TRIM_DEG_MIN) * (
                i / (self.TRIM_DEG_STEPS - 1)
            )
            lam = self._solve_lambda_for_cl0(cl0_req=cl0_req, tau_deg=tau_deg, Cv=Cv)
            if lam is None:
                continue

            lam = max(self.LAMBDA_MIN, min(self.LAMBDA_MAX, lam))

            # Center of pressure heuristic (from transom), scaled by wetted length.
            # Use a mild dependence on Cv^2/λ^2 to avoid always x_cp=0.75L.
            denom = 5.21 * (Cv * Cv) / max(1e-6, lam * lam) + 2.39
            xcp_frac = 0.75 - (1.0 / denom)
            xcp_frac = max(0.45, min(0.80, xcp_frac))
            x_cp_over_b = xcp_frac * lam

            # Balance error: LCG should be near center of pressure (planing trim moment balance)
            # Penalize wildly small/large λ to keep solutions in a realistic band.
            balance_err = (lcg_over_b - x_cp_over_b)
            lam_penalty = 0.05 * max(0.0, lam - 5.0) ** 2 + 0.05 * max(0.0, 1.5 - lam) ** 2
            score = balance_err * balance_err + lam_penalty

            if best is None or score < best[0]:
                best = (score, tau_deg, lam, xcp_frac)

        if best is None:
            # Conservative fallback
            tau_deg = 4.0
            lam = 3.0
            xcp_frac = 0.70
        else:
            _, tau_deg, lam, xcp_frac = best

        x_cp_m = xcp_frac * lam * b
        return tau_deg, lam, x_cp_m

    def _solve_lambda_for_cl0(self, cl0_req: float, tau_deg: float, Cv: float) -> Optional[float]:
        """
        Solve for wetted length ratio λ (lambda = L/b) from Savitsky CL0 equation:

            CL0 = tau^1.1 * (0.0120 * λ^0.5 + 0.0055 * λ^2.5 / Cv^2)

        Where tau is in degrees (common industry implementation).
        """
        if cl0_req <= 0 or tau_deg <= 0 or Cv <= 0:
            return None

        target = cl0_req / (tau_deg ** 1.1)

        def f(lam: float) -> float:
            return (0.0120 * math.sqrt(lam) + 0.0055 * (lam ** 2.5) / (Cv * Cv)) - target

        lo = self.LAMBDA_MIN
        hi = self.LAMBDA_MAX
        f_lo = f(lo)
        f_hi = f(hi)
        if f_lo > 0:
            return lo
        if f_hi < 0:
            return hi

        # Bisection
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            f_mid = f(mid)
            if abs(f_mid) < 1e-6:
                return mid
            if f_mid > 0:
                hi = mid
            else:
                lo = mid

        return 0.5 * (lo + hi)

    def _apply_deadrise_lift(self, cl0: float, beta_deg: float) -> float:
        """Apply Savitsky deadrise correction (empirical)."""
        beta_deg = max(0.0, float(beta_deg))
        cl0 = max(0.0, float(cl0))
        return cl0 - 0.0065 * beta_deg * (cl0 ** 0.6 if cl0 > 0 else 0.0)

    def _invert_deadrise_lift(self, cl_beta: float, beta_deg: float) -> float:
        """
        Approximate inverse of deadrise correction to obtain CL0 from CL_beta.

        Fixed-point iteration is sufficient for the operating range.
        """
        beta_deg = max(0.0, float(beta_deg))
        cl_beta = max(1e-6, float(cl_beta))
        cl0 = cl_beta
        for _ in range(12):
            cl0 = cl_beta + 0.0065 * beta_deg * (cl0 ** 0.6)
        return max(1e-6, cl0)

    def _ittc57_cf(self, reynolds_number: float, warnings: List[str]) -> float:
        """ITTC-57 friction line."""
        if reynolds_number <= 0:
            warnings.append("Invalid Reynolds number for ITTC-57 friction line")
            return 0.003
        log10_rn = math.log10(reynolds_number)
        if log10_rn <= 2.0:
            warnings.append("Reynolds number too low for ITTC-57 friction line")
            return 0.01
        return 0.075 / ((log10_rn - 2.0) ** 2)


