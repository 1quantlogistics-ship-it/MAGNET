"""
magnet/agents/geometry_observables.py

Kernel-computable geometry observables used by the VESSEL_THINKING_PASS binding table.

This is intentionally a *small* registry of measurable quantities (not hull-type priors).
The vocabulary is closed (for v0.1) so the kernel can deterministically compute and verify.
DOFs remain open; only DOFs that want PASS/FAIL checks must bind to known observables.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import math


# Canonical observable ids come from the kernel registry (open vocabulary at runtime; closed set per version).
# This module remains the computation backend for series measurements used by the thinking pass.
try:
    from magnet.kernel.geometry_observables import OBSERVABLE_REGISTRY

    VALID_OBSERVABLE_IDS = set(OBSERVABLE_REGISTRY.keys())
except Exception:
    # Fallback (should not happen in normal runtime)
    VALID_OBSERVABLE_IDS = {
        "section_metric:max_half_beam_m",
        "section_metric:keel_z_m",
        "section_metric:sheer_z_m",
        "section_metric:chine_z_m",
        "section_metric:deadrise_deg_at_chine",
        "longitudinal_metric:deadrise_drop_deg",
        "longitudinal_metric:keel_slope_deg_p95",
        "longitudinal_metric:sheer_rise_m",
        "longitudinal_metric:entry_fineness_p95",
        "section_metric:topside_angle_deg_above_chine",
    }


# v0.4.x hotfix: geometric chine anchor band near the local keel z (proxy gaming defense).
CHINE_Z_BAND_M = 0.25


def _chine_like_point(pts: List[Any], *, z0: Optional[float] = None, z_band_m: float = CHINE_Z_BAND_M) -> Optional[Any]:
    """
    Choose a stable geometric chine-like anchor:
    - pick points within |z - z0| <= z_band_m
    - return the max-y point in that band

    This intentionally does NOT trust model-provided HARD markers (proxy gaming defense).
    """
    if z0 is None:
        # Use local keel as the reference so rocker (nonzero keel_z) doesn't break anchor detection.
        try:
            zs0 = [float(getattr(p.position, "z")) for p in (pts or [])]
            z0 = min(zs0) if zs0 else 0.0
        except Exception:
            z0 = 0.0

    # Prefer knee detection (max dy/dz slope change) to avoid selecting topside points in deep sections.
    try:
        if pts and len(pts) >= 3:
            max_y = max(float(getattr(p.position, "y")) for p in pts)
            best = None
            best_delta = None
            prev_slope = None
            for i in range(len(pts) - 1):
                y1 = float(getattr(pts[i].position, "y"))
                z1 = float(getattr(pts[i].position, "z"))
                y2 = float(getattr(pts[i + 1].position, "y"))
                z2 = float(getattr(pts[i + 1].position, "z"))
                dz = z2 - z1
                if abs(dz) < 1e-12:
                    continue
                slope = (y2 - y1) / dz
                if prev_slope is not None and 0 < i < len(pts) - 1:
                    delta = abs(slope - prev_slope)
                    if float(getattr(pts[i].position, "y")) >= 0.25 * max_y:
                        if best_delta is None or delta > best_delta:
                            best_delta = delta
                            best = pts[i]
                prev_slope = slope
            if best is not None:
                return best
    except Exception:
        pass

    # Expand band based on section depth so the anchor includes the bottom "run" even for deep-V.
    try:
        zs_all = [float(getattr(p.position, "z")) for p in (pts or [])]
        if zs_all:
            depth = float(max(zs_all) - min(zs_all))
            z_band_m = float(max(z_band_m, 0.5 * depth))
    except Exception:
        pass
    band: List[Any] = []
    for p in pts or []:
        try:
            z = float(getattr(p.position, "z"))
            if abs(z - float(z0)) <= float(z_band_m):
                band.append(p)
        except Exception:
            continue
    if not band:
        return None
    try:
        return max(band, key=lambda q: float(getattr(q.position, "y")))
    except Exception:
        return None


@dataclass
class ObservableSeries:
    body_id: str
    observable_id: str
    xs: List[float]
    values: List[float]

    @property
    def span(self) -> Optional[float]:
        if not self.values:
            return None
        return float(max(self.values) - min(self.values))


def _group_sections_by_body(sections: List[Any]) -> Dict[str, List[Any]]:
    out: Dict[str, List[Any]] = {}
    for s in sections or []:
        bid = str(getattr(s, "body_id", "main"))
        out.setdefault(bid, []).append(s)
    for bid in list(out.keys()):
        out[bid] = sorted(out[bid], key=lambda sec: float(getattr(sec, "x_position", 0.0)))
    return out


def _metric_for_section(section: Any, observable_id: str) -> Optional[float]:
    pts = list(getattr(section, "points", []) or [])
    if not pts:
        return None

    if observable_id == "section_metric:max_half_beam_m":
        try:
            ys = [float(getattr(p.position, "y")) for p in pts]
            return max(ys) if ys else None
        except Exception:
            return None

    if observable_id == "section_metric:keel_z_m":
        try:
            zs = [float(getattr(p.position, "z")) for p in pts]
            return min(zs) if zs else None
        except Exception:
            return None

    if observable_id == "section_metric:sheer_z_m":
        try:
            zs = [float(getattr(p.position, "z")) for p in pts]
            return max(zs) if zs else None
        except Exception:
            return None

    if observable_id == "section_metric:chine_z_m":
        # v0: treat chine as the most outboard HARD edge point (max y among hard points)
        try:
            hard = []
            for p in pts:
                et = getattr(p, "edge_type", None)
                if str(et).lower().endswith("hard") or str(et).lower() == "hard":
                    hard.append(p)
            if not hard:
                return None
            hp = max(hard, key=lambda q: float(getattr(q.position, "y")))
            return float(getattr(hp.position, "z"))
        except Exception:
            return None

    if observable_id == "section_metric:deadrise_deg_at_chine":
        # v0.4.x hotfix: anchor chine geometrically (max-y near z≈0) to prevent HARD proxy gaming.
        try:
            # Keel point = minimum z in section
            keel = min(pts, key=lambda q: float(getattr(q.position, "z")))
            kz = float(getattr(keel.position, "z"))
            ky = float(getattr(keel.position, "y"))

            chine = _chine_like_point(pts)
            if chine is None:
                return None
            cz = float(getattr(chine.position, "z"))
            cy = float(getattr(chine.position, "y"))

            dy = cy - ky
            dz = cz - kz
            if abs(dy) < 1e-12:
                return None
            beta = math.degrees(math.atan2(abs(dz), abs(dy)))
            return float(beta)
        except Exception:
            return None

    if observable_id == "section_metric:topside_angle_deg_above_chine":
        # v0.4: signed topside angle proxy above chine (flare/tumblehome).
        # Positive => flares outward with height; negative => tumblehome.
        try:
            zs = [float(getattr(p.position, "z")) for p in pts]
            if not zs:
                return None
            z_min = min(zs)
            z_max = max(zs)
            if z_max <= z_min + 1e-9:
                return None

            # v0.4.x hotfix: use geometric chine-like anchor (max-y near z≈0), not HARD.
            chine = _chine_like_point(pts)
            if chine is None:
                return None
            cy = float(getattr(chine.position, "y"))
            cz = float(getattr(chine.position, "z"))

            # Choose a point above chine near 80% z of the section range.
            z_target = z_min + 0.8 * (z_max - z_min)
            above = _nearest_point_by_z(pts, z_target)
            if above is None:
                return None
            ay = float(getattr(above.position, "y"))
            az = float(getattr(above.position, "z"))
            dz = az - cz
            dy = ay - cy
            if dz <= 1e-9:
                return None

            # Angle from vertical (deg). Signed by dy.
            ang = math.degrees(math.atan2(abs(dy), dz))
            if dy < 0:
                ang = -ang
            return float(ang)
        except Exception:
            return None

    return None


def _nearest_point_by_z(pts: List[Any], z_target: float) -> Optional[Any]:
    best = None
    best_d = None
    for p in pts or []:
        try:
            z = float(getattr(p.position, "z"))
        except Exception:
            continue
        d = abs(z - float(z_target))
        if best_d is None or d < best_d:
            best_d = d
            best = p
    return best


def _percentile(values: List[float], p: float) -> Optional[float]:
    xs = sorted(float(x) for x in values if isinstance(x, (int, float)))
    if not xs:
        return None
    if p <= 0:
        return xs[0]
    if p >= 100:
        return xs[-1]
    k = (len(xs) - 1) * (p / 100.0)
    i = int(k)
    j = min(i + 1, len(xs) - 1)
    t = k - i
    return (1 - t) * xs[i] + t * xs[j]


def _longitudinal_metric_for_body(secs: List[Any], observable_id: str) -> Optional[float]:
    """
    Compute longitudinal metrics for one body from its sorted sections.
    """
    if not secs:
        return None
    # Ensure station order by x
    secs = sorted(secs, key=lambda sec: float(getattr(sec, "x_position", 0.0)))
    xs = [float(getattr(s, "x_position", 0.0)) for s in secs]

    if observable_id == "longitudinal_metric:keel_slope_deg_p95":
        # p95 of adjacent-station keel slope magnitude (deg).
        keel_z = []
        x2 = []
        for s, x in zip(secs, xs):
            kz = _metric_for_section(s, "section_metric:keel_z_m")
            if kz is None:
                continue
            x2.append(float(x))
            keel_z.append(float(kz))
        if len(x2) < 3:
            return None
        slopes: List[float] = []
        for i in range(len(x2) - 1):
            dx = x2[i + 1] - x2[i]
            dz = keel_z[i + 1] - keel_z[i]
            if abs(dx) < 1e-12:
                continue
            theta = math.degrees(math.atan(abs(dz / dx)))
            slopes.append(float(theta))
        return _percentile(slopes, 95.0) if slopes else None

    if observable_id == "longitudinal_metric:deadrise_drop_deg":
        # forward mean - aft mean (30% split in measurable samples)
        # Coordinate convention (canonical): x_position is meters from AP (aft).
        # Therefore forward (toward FP/bow) is HIGH x; aft (toward AP/stern) is LOW x.
        pairs: List[Tuple[float, float]] = []
        for s, x in zip(secs, xs):
            beta = _metric_for_section(s, "section_metric:deadrise_deg_at_chine")
            if beta is None:
                continue
            pairs.append((float(x), float(beta)))
        if len(pairs) < 4:
            return None
        pairs = sorted(pairs, key=lambda t: t[0])
        n = len(pairs)
        k = int(math.ceil(0.3 * n))
        k = max(1, min(k, n))
        aft = pairs[:k]
        fwd = pairs[-k:]
        if len(fwd) < 2 or len(aft) < 2:
            return None
        fwd_mean = sum(b for _, b in fwd) / len(fwd)
        aft_mean = sum(b for _, b in aft) / len(aft)
        return float(fwd_mean - aft_mean)

    if observable_id == "longitudinal_metric:sheer_rise_m":
        zs: List[float] = []
        for s in secs:
            v = _metric_for_section(s, "section_metric:sheer_z_m")
            if v is None:
                continue
            zs.append(float(v))
        if len(zs) < 2:
            return None
        return float(max(zs) - min(zs))

    if observable_id == "longitudinal_metric:entry_fineness_p95":
        # Proxy: p95 of |d(half_beam)/dx| over available adjacent stations.
        half_beam = []
        x2 = []
        for s, x in zip(secs, xs):
            hb = _metric_for_section(s, "section_metric:max_half_beam_m")
            if hb is None:
                continue
            x2.append(float(x))
            half_beam.append(float(hb))
        if len(x2) < 3:
            return None
        rates: List[float] = []
        for i in range(len(x2) - 1):
            dx = x2[i + 1] - x2[i]
            db = half_beam[i + 1] - half_beam[i]
            if abs(dx) < 1e-12:
                continue
            rates.append(abs(db / dx))
        return _percentile(rates, 95.0) if rates else None

    return None


def _profile_metric_for_geometry(geometry: Any, observable_id: str) -> Optional[float]:
    """
    Profile-level metrics are geometry-level (single-valued), not per-section series.

    This module is used by the thinking pass; kernel owns the authoritative measurers.
    """
    try:
        from magnet.kernel.geometry_observables import (
            measure_profile_metric_stem_rake_deg,
            measure_profile_metric_stem_concavity_ratio,
            measure_profile_metric_transom_rake_deg,
            measure_profile_metric_transom_beam_ratio,
        )
    except Exception:
        return None

    if observable_id == "profile_metric:stem_rake_deg":
        m = measure_profile_metric_stem_rake_deg(geometry)
        return float(m.value) if m is not None else None

    if observable_id == "profile_metric:stem_concavity_ratio":
        m = measure_profile_metric_stem_concavity_ratio(geometry)
        return float(m.value) if m is not None else None

    if observable_id == "profile_metric:transom_rake_deg":
        m = measure_profile_metric_transom_rake_deg(geometry)
        return float(m.value) if m is not None else None

    if observable_id == "profile_metric:transom_beam_ratio":
        m = measure_profile_metric_transom_beam_ratio(geometry)
        return float(m.value) if m is not None else None

    return None


def _kernel_longitudinal_metric_for_geometry(geometry: Any, observable_id: str) -> Optional[float]:
    """
    Newer longitudinal metrics live in kernel and are geometry-level.
    Keep a small bridge here for thinking-pass compatibility.
    """
    try:
        from magnet.kernel.geometry_observables import (
            measure_longitudinal_metric_sheer_peak_station,
            measure_longitudinal_metric_sheer_curvature_peak_station,
            measure_longitudinal_metric_entry_half_angle_deg,
            measure_longitudinal_metric_bow_fineness_ratio,
            measure_longitudinal_metric_chine_rise_rate,
            measure_longitudinal_metric_deadrise_progression_shape,
            measure_longitudinal_metric_rocker_profile_curvature,
        )
    except Exception:
        return None

    if observable_id == "longitudinal_metric:sheer_peak_station":
        m = measure_longitudinal_metric_sheer_peak_station(geometry)
        if m is None or (hasattr(m, "is_valid") and not m.is_valid) or getattr(m, "value", None) is None:
            return None
        return float(m.value)
    if observable_id == "longitudinal_metric:sheer_curvature_peak_station":
        m = measure_longitudinal_metric_sheer_curvature_peak_station(geometry)
        if m is None or (hasattr(m, "is_valid") and not m.is_valid) or getattr(m, "value", None) is None:
            return None
        return float(m.value)
    if observable_id == "longitudinal_metric:entry_half_angle_deg":
        m = measure_longitudinal_metric_entry_half_angle_deg(geometry)
        if m is None or (hasattr(m, "is_valid") and not m.is_valid) or getattr(m, "value", None) is None:
            return None
        return float(m.value)
    if observable_id == "longitudinal_metric:bow_fineness_ratio":
        m = measure_longitudinal_metric_bow_fineness_ratio(geometry)
        if m is None or (hasattr(m, "is_valid") and not m.is_valid) or getattr(m, "value", None) is None:
            return None
        return float(m.value)
    if observable_id == "longitudinal_metric:chine_rise_rate":
        m = measure_longitudinal_metric_chine_rise_rate(geometry)
        if m is None or (hasattr(m, "is_valid") and not m.is_valid) or getattr(m, "value", None) is None:
            return None
        return float(m.value)
    if observable_id == "longitudinal_metric:deadrise_progression_shape":
        m = measure_longitudinal_metric_deadrise_progression_shape(geometry)
        if m is None or (hasattr(m, "is_valid") and not m.is_valid) or getattr(m, "value", None) is None:
            return None
        return float(m.value)
    if observable_id == "longitudinal_metric:rocker_profile_curvature":
        m = measure_longitudinal_metric_rocker_profile_curvature(geometry)
        if m is None or (hasattr(m, "is_valid") and not m.is_valid) or getattr(m, "value", None) is None:
            return None
        return float(m.value)

    return None


def compute_observable_series_from_geometry(geometry: Any) -> Dict[str, ObservableSeries]:
    """
    Compute observable series from a compiled HullGeometry-like object.

    Returns dict keyed by "{body_id}:{observable_id}".
    """
    series: Dict[str, ObservableSeries] = {}
    sections = list(getattr(geometry, "sections", []) or [])
    by_body = _group_sections_by_body(sections)

    for body_id, secs in by_body.items():
        xs = [float(getattr(s, "x_position", 0.0)) for s in secs]
        for oid in VALID_OBSERVABLE_IDS:
            if oid.startswith("profile_metric:"):
                v = _profile_metric_for_geometry(geometry, oid)
                series[f"{body_id}:{oid}"] = ObservableSeries(
                    body_id=str(body_id),
                    observable_id=str(oid),
                    xs=[],
                    values=[float(v)] if isinstance(v, (int, float)) else [],
                )
            elif oid.startswith("longitudinal_metric:"):
                # Prefer kernel measurers for newer longitudinal metrics, fall back to legacy local ones.
                v = _kernel_longitudinal_metric_for_geometry(geometry, oid)
                if v is None:
                    v = _longitudinal_metric_for_body(secs, oid)
                series[f"{body_id}:{oid}"] = ObservableSeries(
                    body_id=str(body_id),
                    observable_id=str(oid),
                    xs=[],
                    values=[float(v)] if isinstance(v, (int, float)) else [],
                )
            else:
                vals: List[float] = []
                xs2: List[float] = []
                for s, x in zip(secs, xs):
                    v = _metric_for_section(s, oid)
                    if v is None:
                        continue
                    xs2.append(float(x))
                    vals.append(float(v))
                series[f"{body_id}:{oid}"] = ObservableSeries(
                    body_id=str(body_id),
                    observable_id=str(oid),
                    xs=xs2,
                    values=vals,
                )

    return series


def compute_observables_via_dry_run(
    *,
    program_text: str,
    current_state: Dict[str, Any],
) -> Tuple[Optional[Dict[str, ObservableSeries]], Optional[str]]:
    """
    Best-effort: compile geometry from program_text applied to current_state (dry-run, no commit),
    then compute observable series.

    Returns: (series, error_message)
    """
    try:
        from magnet.kernel.program_executor import execute_program

        res = execute_program(program_text=program_text, initial_state=current_state, dry_run=True, validate=False)
        if not getattr(res, "success", False):
            errs = list(getattr(res, "errors", []) or [])
            return None, "dry_run_failed:" + (";".join(errs) if errs else "unknown")
        geom = getattr(res, "geometry", None)
        if geom is None:
            return None, "dry_run_no_geometry"
        return compute_observable_series_from_geometry(geom), None
    except Exception as e:
        return None, f"dry_run_exception:{type(e).__name__}:{e}"

