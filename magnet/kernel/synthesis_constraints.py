"""
Constraint-based synthesis (Phase 3).

HARD RULE: No form enums, no family/type priors.
This module exposes a constraint-first contract for producing a hull geometry
candidate from purely physical constraints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from magnet.core.state_manager import StateManager
from magnet.hull_gen.generator import GeneratorConfig, HullGenerator
from magnet.hull_gen.parameters import (
    BowConfig,
    DeadriseProfile,
    FormCoefficients,
    HullDefinition,
    HullFeatures,
    MainDimensions,
)
from magnet.kernel.priors.geometry_defaults import get_defaults_from_dimensions
from magnet.physics.geometry_hydrostatics import compute_hydrostatics_from_geometry

from .classification import HullClassification, classify_hull


@dataclass(frozen=True)
class SynthesisConstraints:
    """
    Constraint-first synthesis request.

    All constraints are PHYSICAL requirements, not style selections.
    Classification (e.g., "planing", "catamaran") is derived post-hoc and never
    fed back into synthesis.
    """

    # === REQUIRED CONSTRAINTS ===
    displacement_m3: Tuple[float, float]  # (min, max)

    # === PERFORMANCE CONSTRAINTS ===
    max_speed_kts: Optional[float] = None
    cruise_speed_kts: Optional[float] = None
    range_nm: Optional[float] = None
    sea_state_design: Optional[int] = None

    # === STABILITY CONSTRAINTS ===
    gm_min_m: Optional[float] = None
    gz_max_min_m: Optional[float] = None
    angle_vanishing_min_deg: Optional[float] = None

    # === DIMENSIONAL CONSTRAINTS ===
    loa_range_m: Optional[Tuple[float, float]] = None
    beam_max_m: Optional[float] = None
    draft_max_m: Optional[float] = None

    # === FORM CONSTRAINTS (continuous) ===
    deadrise_transom_range_deg: Optional[Tuple[float, float]] = None
    entry_angle_range_deg: Optional[Tuple[float, float]] = None
    lcb_fraction_range: Optional[Tuple[float, float]] = None

    # === MULTI-BODY (geometry fact, not "type") ===
    num_bodies: int = 1
    hull_spacing_range_m: Optional[Tuple[float, float]] = None

    # === OPTIONAL SOFT PREFERENCES (hints only) ===
    preferences: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        lo, hi = self.displacement_m3
        if float(lo) <= 0 or float(hi) <= 0 or float(hi) < float(lo):
            raise ValueError("displacement_m3 must be (min>0, max>=min)")
        if int(self.num_bodies) < 1:
            raise ValueError("num_bodies must be >= 1")


@dataclass
class SynthesisResult:
    """Result of constraint-based synthesis."""

    success: bool
    geometry: Optional[Any] = None  # magnet.hull_gen.geometry.HullGeometry
    satisfied_constraints: List[str] = field(default_factory=list)
    violated_constraints: List[str] = field(default_factory=list)
    residuals: Dict[str, float] = field(default_factory=dict)
    derived_classification: Optional[HullClassification] = None


def _mid(bounds: Tuple[float, float]) -> float:
    return (float(bounds[0]) + float(bounds[1])) / 2.0


def synthesize_from_constraints(
    constraints: SynthesisConstraints,
    state: StateManager,
    max_iterations: int = 30,
) -> SynthesisResult:
    """
    Synthesize a hull geometry candidate from physical constraints.

    This is intentionally simple and deterministic: it produces a seed hull
    based on physics-derived defaults, scales to meet displacement bounds, runs
    geometry-based hydrostatics, and returns a result with residuals.
    """

    speed_kts = float(constraints.max_speed_kts or constraints.cruise_speed_kts or 12.0)
    target_disp = _mid(constraints.displacement_m3)

    if constraints.loa_range_m is not None:
        loa_m = _mid(constraints.loa_range_m)
    else:
        # Very rough LOA estimate from displacement (keeps results in sane range).
        # disp ≈ 0.08 * LOA^3  -> LOA ≈ (disp/0.08)^(1/3)
        loa_m = max(6.0, min(120.0, (target_disp / 0.08) ** (1.0 / 3.0)))

    defaults = get_defaults_from_dimensions(float(loa_m), float(speed_kts))
    lwl = float(defaults.get("lwl_m", loa_m * 0.95))
    beam = float(defaults.get("beam_m", lwl / 6.0))
    draft = float(defaults.get("draft_m", beam / 3.2))
    cb = float(defaults.get("cb", 0.55))

    # Apply hard limits (beam/draft caps) before scaling.
    if constraints.beam_max_m is not None:
        beam = min(beam, float(constraints.beam_max_m))
    if constraints.draft_max_m is not None:
        draft = min(draft, float(constraints.draft_max_m))

    # Scale beam/draft to hit displacement target (keep LWL fixed at LOA-derived).
    denom = max(1e-6, lwl * beam * draft * cb)
    scale = (target_disp / denom) ** 0.5  # split across beam & draft
    beam *= scale
    draft *= scale

    # Re-apply hard limits after scaling.
    if constraints.beam_max_m is not None:
        beam = min(beam, float(constraints.beam_max_m))
    if constraints.draft_max_m is not None:
        draft = min(draft, float(constraints.draft_max_m))

    # Pick continuous form parameters from ranges when provided.
    deadrise_deg = float(defaults.get("deadrise_deg", 12.0))
    if constraints.deadrise_transom_range_deg is not None:
        deadrise_deg = _mid(constraints.deadrise_transom_range_deg)

    entry_angle = float(defaults.get("bow_entrance_deg", 25.0))
    if constraints.entry_angle_range_deg is not None:
        entry_angle = _mid(constraints.entry_angle_range_deg)

    lcb_fraction = float(defaults.get("lcb_fraction", 0.52))
    if constraints.lcb_fraction_range is not None:
        lcb_fraction = _mid(constraints.lcb_fraction_range)

    # Multi-body: only a count + spacing range (continuous).
    num_bodies = int(constraints.num_bodies or 1)
    num_bodies = max(1, num_bodies)
    hull_spacing = 0.0
    if num_bodies > 1:
        hull_spacing = _mid(constraints.hull_spacing_range_m) if constraints.hull_spacing_range_m else (beam * 1.1)

    definition = HullDefinition(
        hull_id="constraint_synth",
        hull_name="constraint_synth",
        dimensions=MainDimensions(
            loa=float(loa_m),
            lwl=float(lwl),
            lpp=float(lwl * 0.98),
            beam_max=float(beam),
            beam_wl=float(beam),
            beam_chine=float(beam * 0.93),
            depth=float(float(defaults.get("depth_m", draft * 1.5)) or (draft * 1.5)),
            draft=float(draft),
        ),
        coefficients=FormCoefficients(
            cb=float(cb),
            cp=float(defaults.get("cp", cb + 0.15)),
            cm=float(defaults.get("cm", 0.85)),
            cwp=float(defaults.get("cwp", 0.75)),
            lcb=float(lcb_fraction),
        ),
        deadrise=DeadriseProfile.warped(
            float(deadrise_deg),
            float(min(25.0, deadrise_deg + 2.0)),
            float(min(55.0, max(25.0, deadrise_deg + 18.0))),
        ),
        features=HullFeatures(
            chine_count=1,
            hull_spacing=float(hull_spacing),
            num_hulls=int(num_bodies),
            bow_config=BowConfig(
                half_angle_deg=float(entry_angle),
                region_length=0.20,
                flare_deg=0.0,
            ),
        ),
    )

    gen = HullGenerator(config=GeneratorConfig(num_sections=21, points_per_section=25))

    satisfied: List[str] = []
    violated: List[str] = []
    residuals: Dict[str, float] = {}

    best_geom = None
    best_disp_resid = float("inf")

    for _ in range(max(1, int(max_iterations))):
        geom = gen.generate(definition)

        hs = compute_hydrostatics_from_geometry(geom, draft=float(definition.dimensions.draft))
        disp_geom = float(hs.displacement_m3 or 0.0)

        lo, hi = constraints.displacement_m3
        if disp_geom < float(lo):
            residuals["displacement_m3"] = float(lo) - disp_geom
            satisfied = []
            violated = ["displacement_m3_min"]
            definition.dimensions.beam_max *= 1.03
            definition.dimensions.beam_wl *= 1.03
            definition.dimensions.beam_chine *= 1.03
        elif disp_geom > float(hi):
            residuals["displacement_m3"] = disp_geom - float(hi)
            satisfied = []
            violated = ["displacement_m3_max"]
            definition.dimensions.beam_max *= 0.97
            definition.dimensions.beam_wl *= 0.97
            definition.dimensions.beam_chine *= 0.97
        else:
            residuals["displacement_m3"] = 0.0
            satisfied = ["displacement_m3"]
            violated = []
            best_geom = geom
            break

        if constraints.beam_max_m is not None:
            cap = float(constraints.beam_max_m)
            definition.dimensions.beam_max = min(definition.dimensions.beam_max, cap)
            definition.dimensions.beam_wl = min(definition.dimensions.beam_wl, cap)
            definition.dimensions.beam_chine = min(definition.dimensions.beam_chine, cap * 0.93)

        resid = abs(residuals.get("displacement_m3", 0.0))
        if resid < best_disp_resid:
            best_disp_resid = resid
            best_geom = geom

    success = bool(best_geom is not None and not violated)

    derived = None
    if best_geom is not None:
        derived = classify_hull(best_geom, speed_kts=speed_kts, lwl_m=float(definition.dimensions.lwl))

        try:
            state.set("hull.loa", float(definition.dimensions.loa), "constraint_synth")
            state.set("hull.lwl", float(definition.dimensions.lwl), "constraint_synth")
            state.set("hull.beam", float(definition.dimensions.beam_wl), "constraint_synth")
            state.set("hull.draft", float(definition.dimensions.draft), "constraint_synth")
            state.set("hull.depth", float(definition.dimensions.depth), "constraint_synth")
            state.set("hull.cb", float(definition.coefficients.cb), "constraint_synth")
            state.set("hull.deadrise_deg", float(deadrise_deg), "constraint_synth")
            state.set("hull.hydrostatics_method", "geometry_integration", "constraint_synth")
            state.set("hull.hull_spacing_m", float(hull_spacing) if num_bodies > 1 else 0.0, "constraint_synth")
        except Exception:
            pass

    return SynthesisResult(
        success=success,
        geometry=best_geom,
        satisfied_constraints=satisfied,
        violated_constraints=violated,
        residuals=residuals,
        derived_classification=derived,
    )

