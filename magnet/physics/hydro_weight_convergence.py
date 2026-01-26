"""
magnet/physics/hydro_weight_convergence.py

T7.5 / §0.9.8: Hydro-Weight Convergence (Option B: Fully Physical Fixed-Point).

Problem:
    There is a semantic circular dependency:
        Weight -> Hydrostatics -> Equilibrium(draft) -> Weight ...

Fix (Option B):
    Provide an explicit fixed-point iteration that *mutates* `hull.draft` until
    hydrostatics + weight + equilibrium are self-consistent.

IMPORTANT:
    - This module is the ONLY place that performs the circular solve.
    - It is opt-in via `hull.auto_converge_hydro_weight=True` to avoid silent
      state churn; callers/UX can choose to enable it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from magnet.core.constants import SEAWATER_DENSITY_KG_M3


@dataclass(frozen=True)
class ConvergenceState:
    draft_m: float
    displacement_mt: float
    lightship_weight_mt: float
    iteration: int
    converged: bool
    reason: str = ""


def _get_target_displacement_mt(state_manager: Any) -> Optional[float]:
    # Prefer loading (total displacement) if present; else lightship.
    target = state_manager.get("loading.total_displacement_mt")
    if target is None:
        target = state_manager.get("weight.lightship_weight_mt")
    if target is None:
        target = state_manager.get("weight.lightship_mt")
    try:
        return float(target) if target is not None else None
    except Exception:
        return None


def _compile_geometry_for_equilibrium(state_manager: Any) -> Optional[Any]:
    """
    Best-effort HullGeometry for equilibrium solve.

    Prefers SSOT design-language resources; falls back to parametric hull_gen.
    """
    resources = state_manager.get("resources", {})
    if isinstance(resources, dict) and resources:
        try:
            from magnet.kernel.stdlib.compiler import compile_to_geometry

            lwl = state_manager.get("hull.lwl") or state_manager.get("hull.loa") or 25.0
            state_dict: Dict[str, Any] = {
                "design_id": state_manager.get("design_id") or "",
                "hull": {"loa": state_manager.get("hull.loa") or lwl},
                "resources": resources,
            }

            # Surface intent is explicit; try to preserve it if present.
            try:
                gi = state_manager.get("geometry_intent")
                if isinstance(gi, dict) and gi:
                    state_dict["geometry_intent"] = gi
                else:
                    sd = state_manager.get("geometry_intent.surface_definition")
                    if sd is not None:
                        state_dict["geometry_intent"] = {"surface_definition": sd}
            except Exception:
                pass

            return compile_to_geometry(state_dict)
        except Exception:
            return None

    # Fallback: build legacy hull_gen geometry from scalar hull params.
    try:
        from magnet.hull_gen.generator import HullGenerator, GeneratorConfig
        from magnet.hull_gen.parameters import DeadriseProfile, FormCoefficients, HullDefinition, HullFeatures, MainDimensions

        lwl = float(state_manager.get("hull.lwl") or state_manager.get("hull.loa") or 0.0)
        beam = float(state_manager.get("hull.beam") or 0.0)
        draft = float(state_manager.get("hull.draft") or 0.0)
        depth = float(state_manager.get("hull.depth") or (draft + 1.5))
        cb = float(state_manager.get("hull.cb") or 0.0)
        if lwl <= 0 or beam <= 0 or draft <= 0 or cb <= 0:
            return None

        cp = state_manager.get("hull.cp")
        cm = state_manager.get("hull.cm")
        cwp = state_manager.get("hull.cwp")
        deadrise = float(state_manager.get("hull.deadrise_deg") or 0.0)

        # Coefficient fallbacks (match hydrostatics validator approach)
        planing_like = float(deadrise or 0.0) > 10.0
        if cm is None:
            cm_est = cb + (0.05 if planing_like else 0.10)
            cm = max(0.50, min(0.99, float(cm_est)))
        if cp is None:
            cp = float(cb) / float(cm) if float(cm) > 0 else float(cb) / 0.85
        if cwp is None:
            cwp_est = 0.18 + 0.86 * float(cb)
            cwp = max(0.50, min(0.95, float(cwp_est)))

        loa = float(state_manager.get("hull.loa") or (lwl / 0.95))
        deadrise_transom = float(state_manager.get("hull.deadrise_transom_deg") or deadrise)
        bow_flare_deg = float(state_manager.get("hull.bow_flare_deg") or 0.0)
        stem_rake_deg = float(state_manager.get("hull.stem_rake_deg") or 15.0)
        bow_entrance_deg = float(state_manager.get("hull.bow_entrance_deg") or 25.0)
        transom_beam_ratio = float(state_manager.get("hull.transom_beam_ratio") or 0.85)
        hull_spacing = float(state_manager.get("hull.hull_spacing_m") or 0.0)
        num_hulls = int(state_manager.get("hull.body_count") or state_manager.get("hull.num_hulls") or 1)

        lcb_fraction_fp = state_manager.get("hull.lcb_fraction")
        try:
            lcb_ap = 1.0 - float(lcb_fraction_fp) if lcb_fraction_fp is not None else 0.48
        except Exception:
            lcb_ap = 0.48
        lcb_ap = max(0.0, min(1.0, lcb_ap))

        gen = HullGenerator(GeneratorConfig(num_sections=21, points_per_section=31, num_waterlines=11, include_buttocks=False))
        definition = HullDefinition(
            hull_id=str(state_manager.get("design_id") or "hydro-weight"),
            hull_name="HydroWeight",
            dimensions=MainDimensions(
                loa=float(loa),
                lwl=float(lwl),
                lpp=float(lwl) * 0.98,
                beam_max=float(beam),
                beam_wl=float(beam) * 0.95,
                beam_chine=float(beam) * 0.90,
                depth=float(depth),
                draft=float(draft),
                draft_fwd=float(state_manager.get("hull.draft_fwd_m", draft) or draft),
                draft_aft=float(state_manager.get("hull.draft_aft_m", draft) or draft),
                freeboard_bow=float(depth) - float(draft),
                freeboard_mid=float(depth) - float(draft),
                freeboard_stern=float(depth) - float(draft),
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
                midship=float(deadrise),
                bow=min(float(deadrise) + 25.0, 60.0),
            ),
            features=HullFeatures(
                transom_width_fraction=float(transom_beam_ratio),
                bow_flare_deg=float(bow_flare_deg),
                stem_rake_deg=float(stem_rake_deg),
                bow_entrance_deg=float(bow_entrance_deg),
                hull_spacing=float(hull_spacing),
                num_hulls=int(max(1, num_hulls)),
            ),
        )
        hull_geom = gen.generate(definition)

        # Coordinate convention bridge (match hydrostatics validator):
        # hull_gen often has WL at z=0; shift up so keel is ~0 and WL is ~draft.
        try:
            for sec in getattr(hull_geom, "sections", []) or []:
                for sp in getattr(sec, "points", []) or []:
                    pos = getattr(sp, "position", None)
                    if pos is not None and hasattr(pos, "z"):
                        pos.z = float(pos.z) + float(draft)
        except Exception:
            pass

        return hull_geom
    except Exception:
        return None


def converge_hydro_weight(
    *,
    state_manager: Any,
    max_iterations: int = 10,
    tolerance_m: float = 0.01,
    damping: float = 0.7,
) -> ConvergenceState:
    """
    Fixed-point solve that mutates `hull.draft` until consistent.
    """
    source = "physics/hydro_weight_converged"

    depth = state_manager.get("hull.depth")
    draft = state_manager.get("hull.draft")
    if depth is None or float(depth) <= 0:
        return ConvergenceState(
            draft_m=float(draft or 0.0),
            displacement_mt=0.0,
            lightship_weight_mt=0.0,
            iteration=0,
            converged=False,
            reason="missing_hull.depth",
        )
    if draft is None or float(draft) <= 0:
        draft = min(0.8 * float(depth), 1.0)

    # Instantiate existing validators for reuse (do not duplicate logic).
    from magnet.physics.validators import HydrostaticsValidator
    from magnet.weight.validators import WeightEstimationValidator
    from magnet.physics.equilibrium import solve_equilibrium_draft

    hydro_v = HydrostaticsValidator()
    weight_v = WeightEstimationValidator()

    last_disp = 0.0
    last_wt = 0.0

    for it in range(int(max_iterations)):
        # 1) Set current draft guess
        state_manager.set("hull.draft", float(draft), source)

        # 2) Hydrostatics at this draft
        hydro_res = hydro_v.validate(state_manager, {})
        if not getattr(hydro_res, "passed", False) and getattr(hydro_res, "state", None) is not None:
            # FAILED/ERROR: stop early
            return ConvergenceState(
                draft_m=float(draft),
                displacement_mt=float(state_manager.get("hull.displacement_mt") or 0.0),
                lightship_weight_mt=float(state_manager.get("weight.lightship_weight_mt") or 0.0),
                iteration=it,
                converged=False,
                reason="hydrostatics_failed",
            )

        # 3) Weight estimation (depends on hydrostatics outputs)
        weight_res = weight_v.validate(state_manager, {})
        if not getattr(weight_res, "passed", False) and getattr(weight_res, "state", None) is not None:
            return ConvergenceState(
                draft_m=float(draft),
                displacement_mt=float(state_manager.get("hull.displacement_mt") or 0.0),
                lightship_weight_mt=float(state_manager.get("weight.lightship_weight_mt") or 0.0),
                iteration=it,
                converged=False,
                reason="weight_failed",
            )

        disp_mt = float(state_manager.get("hull.displacement_mt") or 0.0)
        wt_mt = float(state_manager.get("weight.lightship_weight_mt") or state_manager.get("weight.lightship_mt") or 0.0)
        last_disp = disp_mt
        last_wt = wt_mt

        # Need geometry to solve equilibrium.
        geometry = _compile_geometry_for_equilibrium(state_manager)
        if geometry is None:
            return ConvergenceState(
                draft_m=float(draft),
                displacement_mt=float(disp_mt),
                lightship_weight_mt=float(wt_mt),
                iteration=it,
                converged=False,
                reason="no_geometry_for_equilibrium",
            )

        # 4) Equilibrium draft solve (target = current weight)
        sol = solve_equilibrium_draft(
            geometry=geometry,
            target_displacement_mt=float(wt_mt),
            draft_guess_m=float(draft),
            depth_m=float(depth),
            seawater_density=float(SEAWATER_DENSITY_KG_M3),
        )

        state_manager.set("hull.equilibrium_draft_m", float(sol.draft_m), source)
        state_manager.set("hull.equilibrium_converged", bool(sol.converged), source)
        state_manager.set("hull.equilibrium_iterations", int(sol.iterations), source)
        state_manager.set("hull.equilibrium_residual_mt", float(sol.residual_mt), source)
        state_manager.set("hull.equilibrium_target_displacement_mt", float(wt_mt), source)
        state_manager.set("hull.equilibrium_reason", str(sol.reason or ""), source)

        new_draft = float(sol.draft_m)
        if abs(new_draft - float(draft)) < float(tolerance_m) and bool(sol.converged):
            # Converged: set final draft and finalize one last hydro+weight pass at that draft.
            state_manager.set("hull.draft", float(new_draft), source)
            hydro_v.validate(state_manager, {})
            weight_v.validate(state_manager, {})
            return ConvergenceState(
                draft_m=float(new_draft),
                displacement_mt=float(state_manager.get("hull.displacement_mt") or disp_mt),
                lightship_weight_mt=float(state_manager.get("weight.lightship_weight_mt") or wt_mt),
                iteration=it + 1,
                converged=True,
                reason="converged",
            )

        # 5) Under-relaxation to prevent oscillation
        draft = float(damping) * float(new_draft) + (1.0 - float(damping)) * float(draft)

    return ConvergenceState(
        draft_m=float(draft),
        displacement_mt=float(last_disp),
        lightship_weight_mt=float(last_wt),
        iteration=int(max_iterations),
        converged=False,
        reason="max_iterations",
    )


# -----------------------------------------------------------------------------
# Validator wrapper
# -----------------------------------------------------------------------------

from magnet.validators.taxonomy import (  # noqa: E402
    ValidatorDefinition,
    ValidatorInterface,
    ValidationResult,
    ValidationFinding,
    ValidatorState,
    ResultSeverity,
)
from datetime import datetime  # noqa: E402
import time  # noqa: E402
import uuid  # noqa: E402


class HydroWeightConvergedValidator(ValidatorInterface):
    """
    Combined hydro+weight+equilibrium validator that resolves the draft loop.

    Opt-in: requires `hull.auto_converge_hydro_weight=True`.
    """

    def __init__(self, definition: Optional[ValidatorDefinition] = None):
        if definition is None:
            # Late import to avoid import cycles at module load.
            from magnet.validators.builtin import get_validator_by_id

            definition = get_validator_by_id("physics/hydro_weight_converged")
        super().__init__(definition)

    def validate(self, state_manager: Any, context: Dict[str, Any]) -> ValidationResult:
        started_at = datetime.utcnow()
        start_time = time.perf_counter()

        enabled = bool(state_manager.get("hull.auto_converge_hydro_weight") or False)
        if not enabled:
            return ValidationResult(
                validator_id=self.definition.validator_id,
                state=ValidatorState.SKIPPED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                execution_time_ms=int((time.perf_counter() - start_time) * 1000),
            )

        cfg = context or {}
        max_iter = int(cfg.get("hydro_weight_max_iterations", 10))
        tol_m = float(cfg.get("hydro_weight_tolerance_m", 0.01))
        damping = float(cfg.get("hydro_weight_damping", 0.7))

        # Refinable-path enforcement: this validator mutates `hull.draft`, so it
        # must run inside a transaction. Support both call sites:
        # - called from the validator pipeline (which may already be in a txn)
        # - called directly in unit tests (no txn)
        owns_txn = getattr(state_manager, "_current_txn", None) is None
        if owns_txn and hasattr(state_manager, "begin_transaction"):
            state_manager.begin_transaction()
        try:
            conv = converge_hydro_weight(
                state_manager=state_manager,
                max_iterations=max_iter,
                tolerance_m=tol_m,
                damping=damping,
            )
            if owns_txn and hasattr(state_manager, "commit"):
                state_manager.commit()
        except Exception:
            if owns_txn and hasattr(state_manager, "rollback"):
                state_manager.rollback()
            raise

        source = "physics/hydro_weight_converged"
        state_manager.set("hull.hydro_weight_converged", bool(conv.converged), source)
        state_manager.set("hull.hydro_weight_iterations", int(conv.iteration), source)

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        state = ValidatorState.PASSED if conv.converged else ValidatorState.WARNING
        res = ValidationResult(
            validator_id=self.definition.validator_id,
            state=state,
            started_at=started_at,
            completed_at=datetime.utcnow(),
            execution_time_ms=elapsed_ms,
        )

        if conv.converged:
            res.add_finding(
                ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.PASSED,
                    message=f"Hydro-weight converged: draft={conv.draft_m:.3f} m in {conv.iteration} iters",
                )
            )
        else:
            res.add_finding(
                ValidationFinding(
                    finding_id=str(uuid.uuid4())[:8],
                    severity=ResultSeverity.WARNING,
                    message=f"Hydro-weight did not converge ({conv.reason}) after {conv.iteration} iters",
                    suggestion="Increase hull size, adjust weight drivers, or increase max iterations/tolerance.",
                )
            )

        return res

