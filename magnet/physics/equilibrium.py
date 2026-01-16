"""
magnet/physics/equilibrium.py

Phase 3C → Phase 1 connector:
Solve for draft T such that buoyancy equals total weight (equilibrium).

This is intentionally "honest" and first-order:
- Uses SSOT hydrostatics from section polygons: compute_hydrostatics_from_geometry()
- Uses Newton-Raphson with bracketing + bisection fallback
- Uses derivative d(Disp)/dT ≈ rho * Aw(T)

No silent mutation: callers decide whether to apply the solved draft to state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import math

from magnet.core.constants import SEAWATER_DENSITY_KG_M3
from magnet.hull_gen.geometry import HullGeometry
from magnet.physics.geometry_hydrostatics import compute_hydrostatics_from_geometry


@dataclass(frozen=True)
class EquilibriumSolution:
    converged: bool
    draft_m: float
    iterations: int
    residual_mt: float  # signed residual at returned draft: disp_mt - target_mt

    # Best found during search (useful when not converged)
    best_draft_m: float
    best_abs_residual_mt: float
    reason: str = ""


def _eval_residual(
    geometry: HullGeometry,
    draft_m: float,
    target_displacement_mt: float,
    seawater_density: float,
) -> Tuple[float, float, float]:
    """
    Evaluate residual and derivative surrogate.

    Returns:
      (residual_mt, disp_mt, d_disp_dT_mt_per_m)
    """
    hs = compute_hydrostatics_from_geometry(
        geometry=geometry,
        draft=float(draft_m),
        vcg=None,
        seawater_density=float(seawater_density),
    )
    disp_mt = float(hs.displacement_kg) / 1000.0
    residual_mt = disp_mt - float(target_displacement_mt)

    # d(Disp_kg)/dT ≈ rho * Aw  => d(Disp_mt)/dT ≈ rho*Aw/1000
    d_disp_dT = (float(seawater_density) * float(hs.waterplane_area_m2)) / 1000.0
    return residual_mt, disp_mt, d_disp_dT


def solve_equilibrium_draft(
    *,
    geometry: HullGeometry,
    target_displacement_mt: float,
    draft_guess_m: float,
    depth_m: float,
    seawater_density: float = float(SEAWATER_DENSITY_KG_M3),
    tol_residual_mt: float = 0.01,
    tol_draft_m: float = 1e-4,
    max_iter: int = 25,
    min_draft_m: float = 0.01,
    max_draft_fraction_of_depth: float = 0.995,
) -> EquilibriumSolution:
    """
    Solve for draft where displaced mass equals target mass.

    Notes:
    - Draft is constrained to (min_draft, depth*max_draft_fraction_of_depth)
    - If the hull cannot displace the target mass even near max draft, returns non-converged
      with best residual (honest output).
    """
    try:
        target_mt = float(target_displacement_mt)
    except Exception:
        return EquilibriumSolution(
            converged=False,
            draft_m=float(draft_guess_m) if draft_guess_m else 0.0,
            iterations=0,
            residual_mt=float("nan"),
            best_draft_m=float(draft_guess_m) if draft_guess_m else 0.0,
            best_abs_residual_mt=float("inf"),
            reason="invalid_target_displacement",
        )

    if target_mt <= 0:
        return EquilibriumSolution(
            converged=True,
            draft_m=max(float(min_draft_m), float(draft_guess_m or min_draft_m)),
            iterations=0,
            residual_mt=0.0,
            best_draft_m=max(float(min_draft_m), float(draft_guess_m or min_draft_m)),
            best_abs_residual_mt=0.0,
            reason="non_positive_target",
        )

    d = max(0.0, float(depth_m or 0.0))
    max_draft_m = max(float(min_draft_m), d * float(max_draft_fraction_of_depth))
    if max_draft_m <= float(min_draft_m):
        max_draft_m = max(float(min_draft_m) * 2.0, float(draft_guess_m or min_draft_m) * 2.0)

    # Clamp initial guess into domain
    x0 = float(draft_guess_m or min_draft_m)
    x0 = max(float(min_draft_m), min(float(max_draft_m), x0))

    # Bracket search: want R(low) <= 0 and R(high) >= 0 (typical)
    low = float(min_draft_m)
    high = max(float(max_draft_m), float(min_draft_m) * 2.0)

    best_draft = x0
    best_abs_res = float("inf")
    best_res = float("inf")

    def _update_best(draft_m: float, residual_mt: float) -> None:
        nonlocal best_draft, best_abs_res, best_res
        a = abs(float(residual_mt))
        if a < best_abs_res:
            best_abs_res = a
            best_draft = float(draft_m)
            best_res = float(residual_mt)

    try:
        r_low, _, _ = _eval_residual(geometry, low, target_mt, seawater_density)
        _update_best(low, r_low)
    except Exception as e:
        return EquilibriumSolution(
            converged=False,
            draft_m=x0,
            iterations=0,
            residual_mt=float("nan"),
            best_draft_m=x0,
            best_abs_residual_mt=float("inf"),
            reason=f"hydrostatics_error_low: {e}",
        )

    # Expand high until we cross (or until max_draft_m)
    high = max(x0, high)
    high = min(high, max_draft_m)

    r_high = None
    for _ in range(10):
        try:
            r, _, _ = _eval_residual(geometry, high, target_mt, seawater_density)
            r_high = r
            _update_best(high, r)
        except Exception:
            # If hydrostatics fails at this draft, try slightly smaller
            high = max(low + 0.05, high * 0.95)
            high = min(high, max_draft_m)
            continue

        # If bracketed, stop expanding
        if (r_low <= 0 <= r_high) or (r_high <= 0 <= r_low):
            break

        # If still negative at max draft, we are overweight (insufficient buoyancy)
        if r_high < 0 and abs(high - max_draft_m) < 1e-6:
            return EquilibriumSolution(
                converged=False,
                draft_m=best_draft,
                iterations=0,
                residual_mt=best_res,
                best_draft_m=best_draft,
                best_abs_residual_mt=best_abs_res,
                reason="insufficient_buoyancy_at_max_draft",
            )

        # Increase high within depth constraint
        high = min(max_draft_m, max(high * 1.3, high + 0.2))

    if r_high is None:
        return EquilibriumSolution(
            converged=False,
            draft_m=best_draft,
            iterations=0,
            residual_mt=best_res,
            best_draft_m=best_draft,
            best_abs_residual_mt=best_abs_res,
            reason="failed_to_evaluate_bracket_high",
        )

    # If already close at guess, return
    try:
        r0, _, d0 = _eval_residual(geometry, x0, target_mt, seawater_density)
        _update_best(x0, r0)
        if abs(r0) <= tol_residual_mt:
            return EquilibriumSolution(
                converged=True,
                draft_m=x0,
                iterations=0,
                residual_mt=r0,
                best_draft_m=best_draft,
                best_abs_residual_mt=best_abs_res,
                reason="initial_guess_satisfies",
            )
    except Exception:
        # fall back to midpoint for iteration start
        x0 = 0.5 * (low + high)

    x = x0
    last_x = x

    for it in range(1, int(max_iter) + 1):
        try:
            r, _, d_disp_dT = _eval_residual(geometry, x, target_mt, seawater_density)
            _update_best(x, r)
        except Exception as e:
            # Treat as non-fatal: bisection step in bracket
            x = 0.5 * (low + high)
            if abs(x - last_x) <= tol_draft_m:
                break
            last_x = x
            continue

        if abs(r) <= tol_residual_mt:
            return EquilibriumSolution(
                converged=True,
                draft_m=x,
                iterations=it,
                residual_mt=r,
                best_draft_m=best_draft,
                best_abs_residual_mt=best_abs_res,
                reason="residual_tolerance_met",
            )

        # Maintain bracket
        if r > 0:
            high = min(high, x)
        else:
            low = max(low, x)

        # If derivative unusable, bisect
        if not math.isfinite(d_disp_dT) or abs(d_disp_dT) < 1e-6:
            x_new = 0.5 * (low + high)
        else:
            x_new = x - (r / d_disp_dT)
            # If Newton step escapes bracket, bisect
            if not (low <= x_new <= high):
                x_new = 0.5 * (low + high)

        # Clamp to domain
        x_new = max(float(min_draft_m), min(float(max_draft_m), float(x_new)))

        if abs(x_new - x) <= tol_draft_m:
            # Small step; accept as converged if residual small-ish
            if abs(r) <= max(tol_residual_mt * 5.0, 0.05):
                return EquilibriumSolution(
                    converged=True,
                    draft_m=x_new,
                    iterations=it,
                    residual_mt=r,
                    best_draft_m=best_draft,
                    best_abs_residual_mt=best_abs_res,
                    reason="step_tolerance_met",
                )
            break

        last_x = x
        x = x_new

    # Not converged: return best found (explicitly)
    return EquilibriumSolution(
        converged=False,
        draft_m=best_draft,
        iterations=int(max_iter),
        residual_mt=best_res,
        best_draft_m=best_draft,
        best_abs_residual_mt=best_abs_res,
        reason="max_iterations_or_stalled",
    )

