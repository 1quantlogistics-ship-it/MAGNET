"""
MAGNET Hull Synthesis Engine (Enum-free)

Phase 3 (Enum Deletion): This module MUST NOT depend on any form enums.

What remains:
- Global topological harmonization for section point-count consistency
- Geometry-based synthesis request + simple bounded propose→score→mutate loop

What is removed:
- Any form-enum-driven branching (no type/style buckets)
- Any “family priors” dicts or style dispatch
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

import logging
import math

from magnet.core.constants import FN_DISPLACEMENT_MAX, FN_SEMI_DISPLACEMENT_MAX
from magnet.hull_gen.geometry import HullSection, SectionPoint, Point3D, EdgeType
from magnet.kernel.priors.geometry_defaults import (
    get_defaults_from_dimensions,
)
from magnet.kernel.synthesis_lock import SynthesisLock

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager
    from magnet.validators.executor import PipelineExecutor

logger = logging.getLogger(__name__)


# =============================================================================
# Phase 1: Global Topological Harmonization (Truthfulness Foundation)
# =============================================================================

def _pchip_slopes(xs: List[float], ys: List[float]) -> List[float]:
    """
    Monotone cubic Hermite slopes (Fritsch-Carlson / PCHIP-like).

    xs must be strictly increasing.
    """
    n = len(xs)
    if n < 2:
        return [0.0] * n
    ds = []
    for i in range(n - 1):
        dx = xs[i + 1] - xs[i]
        ds.append((ys[i + 1] - ys[i]) / dx if dx != 0 else 0.0)

    m = [0.0] * n
    if n == 2:
        m[0] = ds[0]
        m[1] = ds[0]
        return m

    # Interior slopes
    for i in range(1, n - 1):
        d0 = ds[i - 1]
        d1 = ds[i]
        if d0 == 0.0 or d1 == 0.0 or (d0 > 0) != (d1 > 0):
            m[i] = 0.0
        else:
            w1 = 2 * (xs[i + 1] - xs[i]) + (xs[i] - xs[i - 1])
            w2 = (xs[i + 1] - xs[i]) + 2 * (xs[i] - xs[i - 1])
            m[i] = (w1 + w2) / (w1 / d0 + w2 / d1)

    # Endpoints (one-sided, limited)
    h0 = xs[1] - xs[0]
    h1 = xs[2] - xs[1]
    if h0 == 0 or h1 == 0:
        m[0] = ds[0]
    else:
        m0 = ((2 * h0 + h1) * ds[0] - h0 * ds[1]) / (h0 + h1)
        if (m0 > 0) != (ds[0] > 0):
            m0 = 0.0
        elif (ds[0] > 0 and m0 > 3 * ds[0]) or (ds[0] < 0 and m0 < 3 * ds[0]):
            m0 = 3 * ds[0]
        m[0] = m0

    hn1 = xs[-1] - xs[-2]
    hn2 = xs[-2] - xs[-3]
    if hn1 == 0 or hn2 == 0:
        m[-1] = ds[-1]
    else:
        mn = ((2 * hn1 + hn2) * ds[-1] - hn1 * ds[-2]) / (hn1 + hn2)
        if (mn > 0) != (ds[-1] > 0):
            mn = 0.0
        elif (ds[-1] > 0 and mn > 3 * ds[-1]) or (ds[-1] < 0 and mn < 3 * ds[-1]):
            mn = 3 * ds[-1]
        m[-1] = mn
    return m


def _eval_cubic_hermite(
    x0: float, x1: float, y0: float, y1: float, m0: float, m1: float, x: float
) -> float:
    """Evaluate cubic Hermite spline on [x0,x1] at x."""
    h = x1 - x0
    if h == 0:
        return y0
    t = (x - x0) / h
    t2 = t * t
    t3 = t2 * t
    h00 = 2 * t3 - 3 * t2 + 1
    h10 = t3 - 2 * t2 + t
    h01 = -2 * t3 + 3 * t2
    h11 = t3 - t2
    return h00 * y0 + h10 * h * m0 + h01 * y1 + h11 * h * m1


def _interp_y_of_z(
    zs: List[float],
    ys: List[float],
    zq: float,
    *,
    mode: str,
    slopes: Optional[List[float]] = None,
) -> float:
    """Interpolate y(z) at zq using linear or cubic (PCHIP-like)."""
    n = len(zs)
    if n == 0:
        return 0.0
    if n == 1:
        return ys[0]
    # Clamp
    if zq <= zs[0]:
        return ys[0]
    if zq >= zs[-1]:
        return ys[-1]

    # Find segment
    lo = 0
    hi = n - 2
    while lo <= hi:
        mid = (lo + hi) // 2
        if zs[mid] <= zq <= zs[mid + 1]:
            i = mid
            break
        if zq < zs[mid]:
            hi = mid - 1
        else:
            lo = mid + 1
    else:
        i = max(0, min(n - 2, lo))

    z0, z1 = zs[i], zs[i + 1]
    y0, y1 = ys[i], ys[i + 1]
    if mode == "linear" or slopes is None:
        t = (zq - z0) / (z1 - z0) if z1 != z0 else 0.0
        return y0 + t * (y1 - y0)

    return _eval_cubic_hermite(z0, z1, y0, y1, slopes[i], slopes[i + 1], zq)


def harmonize_sections_global(
    sections: List[HullSection],
    *,
    surface_definition: str,
) -> List[HullSection]:
    """
    Global Topological Harmonization:
    - Upsample all sections to a single vertex count (max over sections)
    - panelized => linear interpolation
    - smooth    => cubic interpolation
    - Never smooth away HARD vertices: preserve them as vertices (snap to grid indices)
    """
    if not sections:
        return sections

    target_n = max((len(s.points or []) for s in sections), default=0)
    if target_n <= 0:
        return sections

    mode = "linear" if surface_definition == "panelized" else "cubic"

    for sec in sections:
        pts = list(sec.points or [])
        if len(pts) == 0:
            continue
        if len(pts) == target_n:
            continue

        # Panelized: preserve feature anchor indices (HARD edges) by never reordering points.
        # Smooth: allow reordering to ensure monotone z for spline evaluation.
        if surface_definition != "panelized":
            pts.sort(key=lambda p: float(p.position.z))

        zs = [float(p.position.z) for p in pts]
        ys = [float(p.position.y) for p in pts]

        z_min, z_max = zs[0], zs[-1]
        if target_n == 1 or z_max == z_min:
            continue

        if surface_definition == "panelized":
            # REQUIREMENT: Preserve HARD edge indices exactly.
            for i in range(len(zs) - 1):
                if zs[i + 1] < zs[i]:
                    raise ValueError(
                        "Panelized section points must be in monotone increasing z order "
                        "to preserve HARD edge anchor indices."
                    )

            anchor_map: Dict[int, SectionPoint] = {}
            anchor_map[0] = pts[0]
            anchor_map[target_n - 1] = pts[-1]
            for idx, p in enumerate(pts):
                if p.edge_type == EdgeType.HARD:
                    anchor_map[int(idx)] = p

            anchors = sorted(anchor_map.items(), key=lambda kv: kv[0])

            new_points: List[Optional[SectionPoint]] = [None] * target_n
            for (i0, p0), (i1, p1) in zip(anchors[:-1], anchors[1:]):
                if i1 <= i0:
                    continue
                z0, z1 = float(p0.position.z), float(p1.position.z)
                for j in range(i0, i1 + 1):
                    if j == i0:
                        src = p0
                        new_points[j] = SectionPoint(
                            position=Point3D(x=float(sec.x_position), y=float(src.position.y), z=float(src.position.z)),
                            normal=None,
                            curvature=0.0,
                            is_chine=bool(src.is_chine),
                            is_keel=bool(src.is_keel),
                            edge_type=src.edge_type,
                            crease_angle_deg=float(src.crease_angle_deg),
                            feature_id=src.feature_id,
                        )
                        continue
                    if j == i1:
                        src = p1
                        new_points[j] = SectionPoint(
                            position=Point3D(x=float(sec.x_position), y=float(src.position.y), z=float(src.position.z)),
                            normal=None,
                            curvature=0.0,
                            is_chine=bool(src.is_chine),
                            is_keel=bool(src.is_keel),
                            edge_type=src.edge_type,
                            crease_angle_deg=float(src.crease_angle_deg),
                            feature_id=src.feature_id,
                        )
                        continue
                    # Interpolate z linearly in index space and y via linear y(z)
                    t = (j - i0) / (i1 - i0)
                    zq = z0 + t * (z1 - z0)
                    yq = _interp_y_of_z(zs, ys, zq, mode="linear")
                    new_points[j] = SectionPoint(
                        position=Point3D(x=float(sec.x_position), y=float(yq), z=float(zq)),
                        normal=None,
                        curvature=0.0,
                        is_chine=False,
                        is_keel=False,
                        edge_type=EdgeType.SMOOTH,
                        crease_angle_deg=0.0,
                        feature_id=None,
                    )
            sec.points = [p for p in new_points if p is not None]
            continue

        # Smooth: resample to target_n uniformly in z, using PCHIP-like slopes for y(z)
        slopes = _pchip_slopes(zs, ys) if mode == "cubic" else None
        new_points2: List[SectionPoint] = []
        for j in range(target_n):
            t = j / (target_n - 1)
            zq = z_min + t * (z_max - z_min)
            yq = _interp_y_of_z(zs, ys, zq, mode=mode, slopes=slopes)
            new_points2.append(
                SectionPoint(
                    position=Point3D(x=float(sec.x_position), y=float(yq), z=float(zq)),
                    normal=None,
                    curvature=0.0,
                    is_chine=False,
                    is_keel=False,
                    edge_type=EdgeType.SMOOTH,
                    crease_angle_deg=0.0,
                    feature_id=None,
                )
            )
        sec.points = new_points2

    return sections


# =============================================================================
# Contracts (Geometry-only)
# =============================================================================

@dataclass(frozen=True)
class GeometrySynthesisRequest:
    """
    Geometry-based synthesis request (enum-free).

    This is a minimal, engineering-first contract that encodes constraints as
    continuous values.
    """

    max_speed_kts: float

    # Optional constraints
    loa_m: Optional[float] = None
    beam_m: Optional[float] = None
    draft_m: Optional[float] = None

    # Optional mission-like inputs (kept for conductor wiring)
    crew_count: Optional[int] = None
    payload_kg: Optional[float] = None
    range_nm: Optional[float] = None
    gm_min_m: Optional[float] = None

    max_iterations: int = 15

    def __post_init__(self) -> None:
        if float(self.max_speed_kts) <= 0:
            raise ValueError("max_speed_kts must be positive")
        if int(self.max_iterations) < 1:
            raise ValueError("max_iterations must be >= 1")
        if self.loa_m is not None and float(self.loa_m) <= 0:
            raise ValueError("loa_m must be positive when provided")

    def get_physics_defaults(self) -> Dict[str, Any]:
        loa = float(self.loa_m) if self.loa_m else max(10.0, min(100.0, (float(self.max_speed_kts) / 2.0) ** 2))
        return get_defaults_from_dimensions(loa, float(self.max_speed_kts))


@dataclass(frozen=True)
class SynthesisProposal:
    lwl_m: float
    beam_m: float
    draft_m: float
    depth_m: float
    cb: float
    cp: float
    cm: float
    cwp: float
    displacement_m3: float
    confidence: float
    iteration: int
    source: str
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_complete(self) -> bool:
        return all(v > 0 for v in [self.lwl_m, self.beam_m, self.draft_m, self.depth_m, self.cb, self.cp, self.cm, self.cwp])


class TerminationReason(Enum):
    CONVERGED = "converged"
    MAX_ITERATIONS = "max_iterations"
    FALLBACK = "fallback"


@dataclass(frozen=True)
class ConvergenceCriteria:
    target_score: float = 92.0
    stagnation_limit: int = 4


DEFAULT_CONVERGENCE = ConvergenceCriteria()


@dataclass(frozen=True)
class SynthesisResult:
    proposal: SynthesisProposal
    termination: TerminationReason
    termination_message: str
    iterations_used: int
    score_history: List[float] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    # Validator pipeline results (if executed by caller/orchestrator).
    # Geometry-only synthesis does not run validators; this is present for audit wiring.
    validator_results: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_usable(self) -> bool:
        return self.proposal.is_complete and self.proposal.confidence >= 0.1

    @property
    def iterations(self) -> int:
        return int(self.iterations_used)

    @property
    def is_fallback(self) -> bool:
        return self.termination == TerminationReason.FALLBACK


# =============================================================================
# Implementation (Geometry-only synthesizer)
# =============================================================================

class HullSynthesizer:
    """
    Geometry-only hull synthesizer.

    IMPORTANT:
    - No validators are run here (fast, cheap bootstrap).
    - No style/type selection; only continuous defaults + constraints.
    """

    def __init__(self, executor: Optional["PipelineExecutor"], state_manager: "StateManager"):
        self.executor = executor
        self.state = state_manager
        self.lock = SynthesisLock(state_manager)

    @staticmethod
    def _score_proposal(p: SynthesisProposal) -> Tuple[float, List[str]]:
        warnings: List[str] = []
        if not p.is_complete:
            return 0.0, ["proposal_incomplete"]

        score = 100.0
        lb = p.lwl_m / p.beam_m if p.beam_m > 0 else 0.0
        bd = p.beam_m / p.draft_m if p.draft_m > 0 else 0.0

        if lb < 3.0:
            score -= 10.0
            warnings.append("lb_low")
        elif lb > 8.0:
            score -= 5.0
            warnings.append("lb_high")

        if bd < 2.0:
            score -= 5.0
            warnings.append("bd_low")
        elif bd > 5.0:
            score -= 5.0
            warnings.append("bd_high")

        if p.cb < 0.3 or p.cb > 0.8:
            score -= 10.0
            warnings.append("cb_out_of_range")

        if p.depth_m < p.draft_m:
            score -= 25.0
            warnings.append("depth_lt_draft")

        return max(0.0, float(score)), warnings

    @staticmethod
    def _mutate(p: SynthesisProposal, defaults: Dict[str, Any], iteration: int) -> SynthesisProposal:
        import random

        scale = 0.1 / (1.0 + iteration * 0.1)
        new_lwl = float(p.lwl_m) * (1.0 + random.gauss(0, scale))
        new_beam = float(p.beam_m) * (1.0 + random.gauss(0, scale))
        new_draft = float(p.draft_m) * (1.0 + random.gauss(0, scale))
        new_cb = max(0.3, min(0.8, float(p.cb) + random.gauss(0, scale * 0.5)))

        disp = new_lwl * new_beam * new_draft * new_cb
        depth_ratio = float(defaults.get("depth_draft_ratio", 1.5) or 1.5)

        return SynthesisProposal(
            lwl_m=new_lwl,
            beam_m=new_beam,
            draft_m=new_draft,
            depth_m=new_draft * depth_ratio,
            cb=new_cb,
            cp=float(defaults.get("cp", new_cb + 0.15) or (new_cb + 0.15)),
            cm=float(defaults.get("cm", 0.85) or 0.85),
            cwp=float(defaults.get("cwp", 0.75) or 0.75),
            displacement_m3=disp,
            confidence=float(max(0.1, p.confidence * 0.98)),
            iteration=int(iteration) + 1,
            source="mutation",
        )

    def synthesize_from_geometry(self, request: GeometrySynthesisRequest) -> SynthesisResult:
        criteria = DEFAULT_CONVERGENCE
        defaults = request.get_physics_defaults()

        with self.lock.exclusive_access("hull_synthesizer"):
            # Initial proposal from defaults + hard constraints
            lwl = float(defaults.get("lwl_m", 30.0))
            if request.loa_m:
                lwl = float(request.loa_m) * 0.95
            beam = float(request.beam_m) if request.beam_m else float(defaults.get("beam_m", 6.0))
            draft = float(request.draft_m) if request.draft_m else float(defaults.get("draft_m", 2.0))
            cb = float(defaults.get("cb", 0.5))

            disp = lwl * beam * draft * cb
            proposal = SynthesisProposal(
                lwl_m=lwl,
                beam_m=beam,
                draft_m=draft,
                depth_m=float(defaults.get("depth_m", draft * 1.5)),
                cb=cb,
                cp=float(defaults.get("cp", 0.65)),
                cm=float(defaults.get("cm", 0.85)),
                cwp=float(defaults.get("cwp", 0.75)),
                displacement_m3=disp,
                confidence=0.75,
                iteration=0,
                source="seed",
            )

            # Seed additional hull-form inputs (Phase 1/2 contract surface).
            # These are physics-derived defaults, not form enums.
            deadrise_deg = float(defaults.get("deadrise_deg", 12.0) or 12.0)
            # Very lightweight multihull hinting: if the user asserts hull.hull_type contains
            # "catamaran"/"trimaran", expose multi-body controls for downstream validators.
            hull_type_str = str(self.state.get("hull.hull_type") or "")
            is_catamaran = "catamaran" in hull_type_str.lower()
            is_trimaran = "trimaran" in hull_type_str.lower()
            num_hulls = 2 if is_catamaran else (3 if is_trimaran else 1)
            hull_spacing_m = float(defaults.get("hull_spacing_m", proposal.beam_m * 1.1) or (proposal.beam_m * 1.1))

            best = proposal
            best_score = -1.0
            history: List[float] = []
            warnings: List[str] = []
            stagnation = 0

            for it in range(int(request.max_iterations)):
                score, w = self._score_proposal(proposal)
                history.append(score)
                warnings.extend(w)

                if score > best_score:
                    best_score = score
                    best = proposal
                    stagnation = 0
                else:
                    stagnation += 1

                if score >= criteria.target_score:
                    result = SynthesisResult(
                        proposal=best,
                        termination=TerminationReason.CONVERGED,
                        termination_message="score_threshold_met",
                        iterations_used=it + 1,
                        score_history=history,
                        warnings=warnings,
                    )
                    self.lock.write_hull_params(
                        {
                            "hull.lwl": result.proposal.lwl_m,
                            "hull.beam": result.proposal.beam_m,
                            "hull.draft": result.proposal.draft_m,
                            "hull.depth": result.proposal.depth_m,
                            "hull.cb": result.proposal.cb,
                            "hull.cp": result.proposal.cp,
                            "hull.cm": result.proposal.cm,
                            "hull.cwp": result.proposal.cwp,
                            "hull.displacement_m3": result.proposal.displacement_m3,
                            # Hull-form inputs (defaults)
                            "hull.deadrise_deg": deadrise_deg,
                            "hull.deadrise_transom_deg": deadrise_deg,
                            "hull.bow_entrance_deg": float(defaults.get("bow_entrance_deg", 25.0) or 25.0),
                            "hull.bow_flare_deg": float(defaults.get("bow_flare_deg", 0.0) or 0.0),
                            "hull.stem_rake_deg": float(defaults.get("stem_rake_deg", 15.0) or 15.0),
                            "hull.transom_beam_ratio": float(defaults.get("transom_beam_ratio", 0.85) or 0.85),
                            "hull.freeboard_m": max(0.1, float(result.proposal.depth_m) - float(result.proposal.draft_m)),
                            "hull.lcb_fraction": float(defaults.get("lcb_fraction", 0.52) or 0.52),
                            "hull.draft_fwd_m": float(result.proposal.draft_m),
                            "hull.draft_aft_m": float(result.proposal.draft_m),
                            # Multi-body controls (only if user asserted multi-hull intent)
                            "hull.hull_spacing_m": float(hull_spacing_m) if num_hulls > 1 else 0.0,
                        },
                        "hull_synthesizer",
                    )
                    return result

                if stagnation >= criteria.stagnation_limit:
                    break

                proposal = self._mutate(proposal, defaults, it)

            if best.is_complete:
                result = SynthesisResult(
                    proposal=best,
                    termination=TerminationReason.MAX_ITERATIONS,
                    termination_message="stalled_or_max_iterations",
                    iterations_used=len(history),
                    score_history=history,
                    warnings=warnings,
                )
                self.lock.write_hull_params(
                    {
                        "hull.lwl": result.proposal.lwl_m,
                        "hull.beam": result.proposal.beam_m,
                        "hull.draft": result.proposal.draft_m,
                        "hull.depth": result.proposal.depth_m,
                        "hull.cb": result.proposal.cb,
                        "hull.cp": result.proposal.cp,
                        "hull.cm": result.proposal.cm,
                        "hull.cwp": result.proposal.cwp,
                        "hull.displacement_m3": result.proposal.displacement_m3,
                        # Hull-form inputs (defaults)
                        "hull.deadrise_deg": deadrise_deg,
                        "hull.deadrise_transom_deg": deadrise_deg,
                        "hull.bow_entrance_deg": float(defaults.get("bow_entrance_deg", 25.0) or 25.0),
                        "hull.bow_flare_deg": float(defaults.get("bow_flare_deg", 0.0) or 0.0),
                        "hull.stem_rake_deg": float(defaults.get("stem_rake_deg", 15.0) or 15.0),
                        "hull.transom_beam_ratio": float(defaults.get("transom_beam_ratio", 0.85) or 0.85),
                        "hull.freeboard_m": max(0.1, float(result.proposal.depth_m) - float(result.proposal.draft_m)),
                        "hull.lcb_fraction": float(defaults.get("lcb_fraction", 0.52) or 0.52),
                        "hull.draft_fwd_m": float(result.proposal.draft_m),
                        "hull.draft_aft_m": float(result.proposal.draft_m),
                        # Multi-body controls (only if user asserted multi-hull intent)
                        "hull.hull_spacing_m": float(hull_spacing_m) if num_hulls > 1 else 0.0,
                    },
                    "hull_synthesizer",
                )
                return result

            # Fallback: always return something usable
            fb = SynthesisProposal(
                lwl_m=lwl,
                beam_m=beam,
                draft_m=draft,
                depth_m=max(draft * 1.5, float(defaults.get("depth_m", draft * 1.5))),
                cb=max(0.3, min(0.8, cb)),
                cp=float(defaults.get("cp", 0.65)),
                cm=float(defaults.get("cm", 0.85)),
                cwp=float(defaults.get("cwp", 0.75)),
                displacement_m3=lwl * beam * draft * max(0.3, min(0.8, cb)),
                confidence=0.3,
                iteration=0,
                source="fallback",
            )
            result = SynthesisResult(
                proposal=fb,
                termination=TerminationReason.FALLBACK,
                termination_message="fallback_used",
                iterations_used=0,
                score_history=history,
                warnings=warnings + ["fallback_used"],
            )
            self.lock.write_hull_params(
                {
                    "hull.lwl": result.proposal.lwl_m,
                    "hull.beam": result.proposal.beam_m,
                    "hull.draft": result.proposal.draft_m,
                    "hull.depth": result.proposal.depth_m,
                    "hull.cb": result.proposal.cb,
                    "hull.cp": result.proposal.cp,
                    "hull.cm": result.proposal.cm,
                    "hull.cwp": result.proposal.cwp,
                    "hull.displacement_m3": result.proposal.displacement_m3,
                    # Hull-form inputs (defaults)
                    "hull.deadrise_deg": deadrise_deg,
                    "hull.deadrise_transom_deg": deadrise_deg,
                    "hull.bow_entrance_deg": float(defaults.get("bow_entrance_deg", 25.0) or 25.0),
                    "hull.bow_flare_deg": float(defaults.get("bow_flare_deg", 0.0) or 0.0),
                    "hull.stem_rake_deg": float(defaults.get("stem_rake_deg", 15.0) or 15.0),
                    "hull.transom_beam_ratio": float(defaults.get("transom_beam_ratio", 0.85) or 0.85),
                    "hull.freeboard_m": max(0.1, float(result.proposal.depth_m) - float(result.proposal.draft_m)),
                    "hull.lcb_fraction": float(defaults.get("lcb_fraction", 0.52) or 0.52),
                    "hull.draft_fwd_m": float(result.proposal.draft_m),
                    "hull.draft_aft_m": float(result.proposal.draft_m),
                    # Multi-body controls (only if user asserted multi-hull intent)
                    "hull.hull_spacing_m": float(hull_spacing_m) if num_hulls > 1 else 0.0,
                },
                "hull_synthesizer",
            )
            return result


