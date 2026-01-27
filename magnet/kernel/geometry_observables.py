"""
magnet/kernel/geometry_observables.py

Kernel-owned observable registry (measurable + controllable) for ADJUST/TARGET.

Phase 1 scope:
- DIRECT controls only (deterministic, no solver)
- Small set of controllable observables to unblock Viking iteration
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import math


Unit = str  # "deg" | "m" | "ratio"

from magnet.kernel.observable_registry import ObservableSpec


@dataclass
class Measurement:
    """
    Measurement value plus optional witness and structured violation info.

    IMPORTANT:
    - Never use `None` as a silent failure signal. If a measurement cannot be
      computed, return `Measurement.failed(...)` with a reason.
    - Callers may still choose to treat failed measurements as "unavailable",
      but they must have access to *why* it failed.
    """

    value: Optional[float]
    witness_index: Optional[int] = None
    violation: Optional["ViolationInfo"] = None

    @property
    def is_valid(self) -> bool:
        return self.value is not None and self.violation is None

    @classmethod
    def failed(cls, *, violation: "ViolationInfo") -> "Measurement":
        return cls(value=None, witness_index=violation.witness_index, violation=violation)


@dataclass(frozen=True)
class ViolationInfo:
    """
    Structured information about why a measurement failed.

    Lightweight by design: no form enums and no heavy dependencies.
    """

    violation_type: str  # "geometric" | "topological" | "numerical" | "physical"
    message: str
    witness_index: Optional[int] = None
    section_id: Optional[str] = None
    parameter_hint: Optional[str] = None
    direction_hint: Optional[str] = None


def _fail(
    *,
    violation_type: str,
    message: str,
    witness_index: Optional[int] = None,
    section_id: Optional[str] = None,
    parameter_hint: Optional[str] = None,
    direction_hint: Optional[str] = None,
) -> Measurement:
    return Measurement.failed(
        violation=ViolationInfo(
            violation_type=str(violation_type),
            message=str(message),
            witness_index=witness_index,
            section_id=section_id,
            parameter_hint=parameter_hint,
            direction_hint=direction_hint,
        )
    )


# ---------------------------------------------------------------------------
# Helpers: scope parsing / station filtering
# ---------------------------------------------------------------------------

def _normalize_station_range(rng: Any) -> Tuple[float, float]:
    try:
        lo = float(rng[0])
        hi = float(rng[1])
    except Exception:
        return (0.0, 1.0)
    if lo > hi:
        lo, hi = hi, lo
    lo = max(0.0, lo)
    hi = min(1.0, hi)
    return (lo, hi)


def _sections_for_scope(
    *,
    resources: Dict[str, Any],
    body_id: str,
    station_range: Optional[Tuple[float, float]] = None,
    station: Optional[float] = None,
) -> List[Tuple[str, Dict[str, Any]]]:
    secs: List[Tuple[str, Dict[str, Any]]] = []
    for rid, r in (resources or {}).items():
        if not isinstance(r, dict) or r.get("_deleted"):
            continue
        if r.get("_type") != "geometry.section":
            continue
        if str(r.get("body_id") or "main") != str(body_id):
            continue
        try:
            st = float(r.get("station"))
        except Exception:
            continue
        secs.append((str(rid), r))

    secs.sort(key=lambda t: float(t[1].get("station", 0.0) or 0.0))

    if station is not None:
        # nearest station (deterministic)
        target = float(station)
        best = None
        best_d = None
        for rid, r in secs:
            try:
                st = float(r.get("station"))
            except Exception:
                continue
            d = abs(st - target)
            if best_d is None or d < best_d:
                best_d = d
                best = (rid, r)
        return [best] if best is not None else []

    if station_range is None:
        return secs

    lo, hi = _normalize_station_range(station_range)
    out: List[Tuple[str, Dict[str, Any]]] = []
    for rid, r in secs:
        try:
            st = float(r.get("station"))
        except Exception:
            continue
        if lo <= st <= hi:
            out.append((rid, r))
    return out


def _parse_points_yz(section: Dict[str, Any]) -> List[Tuple[float, float]]:
    pts = section.get("points") or []
    out: List[Tuple[float, float]] = []
    if not isinstance(pts, list):
        return out
    for p in pts:
        if isinstance(p, (list, tuple)) and len(p) >= 2:
            try:
                y = float(p[0])
                z = float(p[1])
            except Exception:
                continue
            out.append((y, z))
    return out


def _find_sheer_index(points: List[Tuple[float, float]]) -> Optional[int]:
    if not points:
        return None
    # max z
    best_i = None
    best_z = None
    for i, (_y, z) in enumerate(points):
        if best_z is None or z > best_z:
            best_z = z
            best_i = i
    return best_i


def _find_chine_like_index(points: List[Tuple[float, float]], *, z0: Optional[float] = None, z_band_m: float = 0.25) -> Optional[int]:
    """
    Geometric chine-like anchor: max-y point within |z - z0| <= z_band_m.
    Uses local keel z as default reference (so rocker doesn't break detection).
    """
    # First try a knee detector (max slope change dy/dz along the section curve).
    if len(points) >= 3:
        try:
            max_y = max(y for y, _z in points)
            best_i = None
            best_delta = None
            prev_slope = None
            for i in range(len(points) - 1):
                y1, z1 = points[i]
                y2, z2 = points[i + 1]
                dz = float(z2 - z1)
                if abs(dz) < 1e-12:
                    continue
                slope = float((y2 - y1) / dz)
                if prev_slope is not None and 0 < i < len(points) - 1:
                    delta = abs(slope - prev_slope)
                    # Avoid selecting near-keel noise: require some outboardness.
                    if float(points[i][0]) >= 0.25 * float(max_y):
                        if best_delta is None or delta > best_delta:
                            best_delta = delta
                            best_i = i
                prev_slope = slope
            if best_i is not None:
                return int(best_i)
        except Exception:
            pass

    if points:
        keel_z = min(z for _y, z in points)
        sheer_z = max(z for _y, z in points)
        depth = float(sheer_z - keel_z)
        z_band_m = float(max(z_band_m, 0.5 * depth))
        if z0 is None:
            z0 = float(keel_z)
    cand: List[Tuple[int, float]] = []
    for i, (y, z) in enumerate(points):
        if abs(z - z0) <= z_band_m:
            cand.append((i, y))
    if not cand:
        return None
    return max(cand, key=lambda t: t[1])[0]


# ---------------------------------------------------------------------------
# Phase 1 measurers (return value + witness_index)
# ---------------------------------------------------------------------------

def measure_section_metric_deadrise_deg_at_chine(section: Dict[str, Any], *, witness_index: Optional[int] = None) -> Measurement:
    pts = _parse_points_yz(section)
    if len(pts) < 2:
        return _fail(violation_type="topological", message="insufficient_points_for_deadrise", parameter_hint="points")

    # keel = min z
    keel_i = min(range(len(pts)), key=lambda i: pts[i][1])
    ky, kz = pts[keel_i]

    ci = witness_index
    if ci is None or not (0 <= ci < len(pts)):
        ci = _find_chine_like_index(pts)
    if ci is None:
        return _fail(violation_type="topological", message="chinelike_anchor_not_found", parameter_hint="chine")
    cy, cz = pts[ci]

    dy = cy - ky
    dz = cz - kz
    if abs(dy) < 1e-12:
        return _fail(violation_type="numerical", message="degenerate_dy_for_deadrise", witness_index=int(ci))
    beta = math.degrees(math.atan2(abs(dz), abs(dy)))
    return Measurement(value=float(beta), witness_index=int(ci))


def measure_section_metric_max_half_beam_m(section: Dict[str, Any]) -> Measurement:
    pts = _parse_points_yz(section)
    if not pts:
        return _fail(violation_type="topological", message="no_points_for_max_half_beam", parameter_hint="points")
    max_y = max(y for y, _z in pts)
    # witness = index of max y (stable)
    wi = max(range(len(pts)), key=lambda i: pts[i][0])
    return Measurement(value=float(max_y), witness_index=int(wi))


def measure_section_metric_sheer_z_m(section: Dict[str, Any], *, witness_index: Optional[int] = None) -> Measurement:
    pts = _parse_points_yz(section)
    if not pts:
        return _fail(violation_type="topological", message="no_points_for_sheer_z", parameter_hint="points")
    wi = witness_index
    if wi is None or not (0 <= wi < len(pts)):
        wi = _find_sheer_index(pts)
    if wi is None:
        return _fail(violation_type="topological", message="sheer_index_not_found", parameter_hint="points")
    return Measurement(value=float(pts[wi][1]), witness_index=int(wi))


# ---------------------------------------------------------------------------
# Character Observable Measurements (Phase 1)
# ---------------------------------------------------------------------------

# Import from feature curve extractor for chine detection
from magnet.kernel.feature_curve_extractor import _find_chine_anchor


def _find_chine_like_point_from_hullsection(points: List[Any]) -> Optional[Any]:
    """Wrapper to use feature curve extractor's chine finder on HullSection points."""
    return _find_chine_anchor(points)


def _get_loa_from_geometry(geometry: Any, sections: List[Any]) -> float:
    """
    Get LOA using priority chain: geometry.loa_m > max(x_position) > 1.0
    """
    if hasattr(geometry, 'loa_m') and geometry.loa_m:
        return float(geometry.loa_m)
    if sections:
        xs = [float(getattr(s, "x_position", 0.0)) for s in sections]
        if xs:
            return max(xs)
    return 1.0


# SHEER SHAPE

def measure_longitudinal_metric_sheer_peak_station(geometry: Any) -> Measurement:
    """Find station where sheer_z is maximum (plateau centroid)."""
    sections = getattr(geometry, "sections", [])
    if len(sections) < 3:
        return _fail(violation_type="topological", message="insufficient_sections_for_sheer_peak", parameter_hint="sections")
    
    pairs: List[Tuple[float, float]] = []
    for s in sections:
        pts = list(getattr(s, "points", []) or [])
        if not pts:
            continue
        max_pt = max(pts, key=lambda p: float(p.position.z))
        x_m = float(getattr(s, "x_position", 0.0))
        sheer_z = float(max_pt.position.z)
        pairs.append((x_m, sheer_z))
    
    if len(pairs) < 3:
        return _fail(violation_type="topological", message="insufficient_pairs_for_sheer_peak", parameter_hint="sections")
    
    z_max = max(z for _x, z in pairs)
    if not math.isfinite(z_max):
        return _fail(violation_type="numerical", message="nonfinite_sheer_peak", parameter_hint="sections")
    
    plateau = [(x, z) for x, z in pairs if z >= 0.99 * z_max]
    if not plateau:
        return _fail(violation_type="numerical", message="empty_plateau_for_sheer_peak", parameter_hint="sections")
    
    x_centroid = sum(x for x, _z in plateau) / len(plateau)
    xs = [x for x, _z in pairs]
    x_min, x_max = min(xs), max(xs)
    x_range = max(1e-9, x_max - x_min)
    station_norm = max(0.0, min(1.0, (x_centroid - x_min) / x_range))
    
    return Measurement(value=float(station_norm))


def measure_longitudinal_metric_sheer_curvature_peak_station(geometry: Any) -> Measurement:
    """Find station where sheer curvature (second derivative) is maximum."""
    sections = getattr(geometry, "sections", [])
    if len(sections) < 5:
        return _fail(violation_type="topological", message="insufficient_sections_for_sheer_curvature", parameter_hint="sections")
    
    pairs: List[Tuple[float, float]] = []
    for s in sections:
        pts = list(getattr(s, "points", []) or [])
        if not pts:
            continue
        max_pt = max(pts, key=lambda p: float(p.position.z))
        x_m = float(getattr(s, "x_position", 0.0))
        sheer_z = float(max_pt.position.z)
        pairs.append((x_m, sheer_z))
    
    pairs = sorted(pairs, key=lambda p: p[0])
    if len(pairs) < 5:
        return _fail(violation_type="topological", message="insufficient_pairs_for_sheer_curvature", parameter_hint="sections")
    
    curvatures: List[Tuple[float, float]] = []
    for i in range(1, len(pairs) - 1):
        x0, z0 = pairs[i - 1]
        x1, z1 = pairs[i]
        x2, z2 = pairs[i + 1]
        
        dx1 = x1 - x0
        dx2 = x2 - x1
        if dx1 < 1e-9 or dx2 < 1e-9:
            continue
        
        d2z = ((z2 - z1) / dx2 - (z1 - z0) / dx1) / ((dx1 + dx2) / 2)
        curvatures.append((x1, abs(d2z)))
    
    if not curvatures:
        return _fail(violation_type="numerical", message="no_curvature_samples_for_sheer", parameter_hint="sections")
    
    max_curv = max(curvatures, key=lambda c: c[1])
    x_peak = float(max_curv[0])
    
    xs = [x for x, _z in pairs]
    x_min, x_max = min(xs), max(xs)
    x_range = max(1e-9, x_max - x_min)
    station_norm = max(0.0, min(1.0, (x_peak - x_min) / x_range))
    
    return Measurement(value=float(station_norm))


# STEM/BOW

def measure_profile_metric_stem_rake_deg(geometry: Any) -> Optional[Measurement]:
    """Compute stem rake angle from vertical at waterline crossing."""
    stem_profile = list(getattr(geometry, "stem_profile", []) or [])
    if len(stem_profile) < 2:
        return None

    pts = [(float(p.x), float(p.z)) for p in stem_profile]
    for i in range(len(pts) - 1):
        x1, z1 = pts[i]
        x2, z2 = pts[i + 1]
        if (z1 <= 0.0 <= z2) or (z2 <= 0.0 <= z1):
            dx = x2 - x1
            dz = z2 - z1
            if abs(dz) < 1e-9:
                return None
            rake = float(math.degrees(math.atan2(abs(dx), abs(dz))))
            return Measurement(value=rake)
    
    return None


def measure_profile_metric_stem_concavity_ratio(geometry: Any) -> Optional[Measurement]:
    """Compute stem concavity ratio: max perpendicular distance to chord / chord length."""
    stem_profile = list(getattr(geometry, "stem_profile", []) or [])
    if len(stem_profile) < 3:
        return None

    pts = [(float(p.x), float(p.z)) for p in stem_profile]
    
    xh, zh = max(pts, key=lambda t: t[1])
    
    dwl = None
    for (x0, z0), (x1, z1) in zip(pts[:-1], pts[1:]):
        if (z0 <= 0 <= z1) or (z1 <= 0 <= z0):
            dz = z1 - z0
            if abs(dz) < 1e-12:
                continue
            t = (0.0 - z0) / dz
            if 0.0 <= t <= 1.0:
                dwl = (x0 + t * (x1 - x0), 0.0)
                break
    if dwl is None:
        dwl = min(pts, key=lambda t: abs(t[1]))
    xd, zd = dwl
    
    L = math.hypot(xd - xh, zd - zh)
    if not math.isfinite(L) or L < 1e-9:
        return None
    
    max_d = 0.0
    ax, az = xh, zh
    bx, bz = xd, zd
    vx, vz = (bx - ax), (bz - az)
    denom = math.hypot(vx, vz)
    if denom < 1e-9:
        return None
    
    for px, pz in pts:
        cx = (px - ax) * vz - (pz - az) * vx
        d = abs(cx) / denom
        if math.isfinite(d):
            max_d = max(max_d, d)
    
    ratio = max_d / L
    if not math.isfinite(ratio):
        return None
    return Measurement(value=float(max(0.0, min(1.0, ratio))))


# ENTRY SHARPNESS

def measure_longitudinal_metric_entry_half_angle_deg(geometry: Any) -> Optional[Measurement]:
    """Compute local waterline half-angle of entry using slope d(half_beam)/dx in bow region."""
    sections = getattr(geometry, "sections", [])
    if len(sections) < 5:
        return None
    
    pairs: List[Tuple[float, float]] = []
    for s in sections:
        pts = list(getattr(s, "points", []) or [])
        if not pts:
            continue
        max_y = max(float(p.position.y) for p in pts)
        x_m = float(getattr(s, "x_position", 0.0))
        pairs.append((x_m, max_y))
    
    if len(pairs) < 5:
        return None
    
    pairs = sorted(pairs, key=lambda p: p[0])
    x_min = min(x for x, _hb in pairs)
    x_max = max(x for x, _hb in pairs)
    x_range = max(1e-9, x_max - x_min)
    
    indices = [i for i, (x, _hb) in enumerate(pairs) if ((x - x_min) / x_range) >= 0.85]
    if len(indices) < 3:
        return None
    
    angles: List[float] = []
    for i in indices:
        if i <= 0 or i >= len(pairs) - 1:
            continue
        x0, hb0 = pairs[i - 1]
        x2, hb2 = pairs[i + 1]
        dx = x2 - x0
        if abs(dx) < 1e-9:
            continue
        slope = (hb2 - hb0) / dx
        ang = float(math.degrees(math.atan(float(slope))))
        if math.isfinite(ang):
            angles.append(ang)
    
    if not angles:
        return None
    
    angles = sorted(angles)
    return Measurement(value=float(angles[len(angles) // 2]))


def measure_longitudinal_metric_bow_fineness_ratio(geometry: Any) -> Optional[Measurement]:
    """Compute mean half-beam / (0.1 * LOA) for forward 10% of hull."""
    sections = getattr(geometry, "sections", [])
    if len(sections) < 2:
        return None
    
    loa = _get_loa_from_geometry(geometry, sections)
    
    xs = [float(getattr(s, "x_position", 0.0)) for s in sections]
    x_min, x_max = min(xs), max(xs)
    x_range = max(1e-9, x_max - x_min)
    
    forward_beams: List[float] = []
    for s in sections:
        x_m = float(getattr(s, "x_position", 0.0))
        station_norm = (x_m - x_min) / x_range
        if station_norm < 0.9:
            continue
        pts = list(getattr(s, "points", []) or [])
        if pts:
            hb = max(float(p.position.y) for p in pts)
            forward_beams.append(hb)
    
    if len(forward_beams) < 2:
        return None
    
    mean_beam = sum(forward_beams) / len(forward_beams)
    ratio = mean_beam / (0.1 * max(1e-9, float(loa)))
    return Measurement(value=float(ratio))


# TRANSOM

def measure_profile_metric_transom_rake_deg(geometry: Any) -> Optional[Measurement]:
    """Get transom rake angle from transom_outline (compiler-emitted feature curve)."""
    transom_outline = list(getattr(geometry, "transom_outline", []) or [])
    if len(transom_outline) < 3:
        return None
    
    n = len(transom_outline)
    p0 = transom_outline[0]
    p1 = transom_outline[n // 2]
    p2 = transom_outline[-1]
    
    v1 = (p1.x - p0.x, p1.y - p0.y, p1.z - p0.z)
    v2 = (p2.x - p0.x, p2.y - p0.y, p2.z - p0.z)
    
    nx = v1[1] * v2[2] - v1[2] * v2[1]
    ny = v1[2] * v2[0] - v1[0] * v2[2]
    nz = v1[0] * v2[1] - v1[1] * v2[0]
    
    nn = math.sqrt(nx*nx + ny*ny + nz*nz)
    if nn < 1e-12:
        return None
    
    nx /= nn
    ny /= nn
    nz /= nn
    
    rake = float(math.degrees(math.atan2(abs(nx), abs(nz))))
    if math.isfinite(rake):
        return Measurement(value=rake)
    
    return None


def measure_profile_metric_transom_beam_ratio(geometry: Any) -> Optional[Measurement]:
    """Compute transom beam / max beam (using x_position-derived station_norm)."""
    sections = getattr(geometry, "sections", [])
    if len(sections) < 3:
        return None
    
    xs = [float(getattr(s, "x_position", 0.0)) for s in sections]
    x_min, x_max = min(xs), max(xs)
    x_range = max(1e-9, x_max - x_min)
    
    beams: List[Tuple[float, float]] = []
    for s in sections:
        x_m = float(getattr(s, "x_position", 0.0))
        station_norm = (x_m - x_min) / x_range
        
        pts = list(getattr(s, "points", []) or [])
        if pts:
            hb = max(float(p.position.y) for p in pts)
            beams.append((station_norm, hb))
    
    if len(beams) < 3:
        return None
    
    aft_beam = min(beams, key=lambda b: b[0])[1]
    max_beam = max(b[1] for b in beams)
    
    if max_beam < 0.01:
        return None
    
    return Measurement(value=float(aft_beam / max_beam))


# CHINE PROGRESSION

def measure_longitudinal_metric_chine_rise_rate(geometry: Any) -> Optional[Measurement]:
    """Compute slope of chine_z vs x_m in forward half. Returns m/m (dimensionless slope)."""
    sections = getattr(geometry, "sections", [])
    if len(sections) < 3:
        return None
    
    loa = _get_loa_from_geometry(geometry, sections)
    
    xs = [float(getattr(s, "x_position", 0.0)) for s in sections]
    x_min, x_max = min(xs), max(xs)
    x_range = max(1e-9, x_max - x_min)
    
    pairs: List[Tuple[float, float]] = []
    for s in sections:
        x_m = float(getattr(s, "x_position", 0.0))
        station_norm = (x_m - x_min) / x_range
        if station_norm < 0.5:
            continue
        
        pts = list(getattr(s, "points", []) or [])
        chine = _find_chine_like_point_from_hullsection(pts)
        if chine is None:
            continue
        chine_z = float(chine.position.z)
        pairs.append((x_m, chine_z))
    
    if len(pairs) < 3:
        return None
    
    n = len(pairs)
    sum_x = sum(p[0] for p in pairs)
    sum_y = sum(p[1] for p in pairs)
    sum_xy = sum(p[0] * p[1] for p in pairs)
    sum_x2 = sum(p[0] ** 2 for p in pairs)
    
    denom = n * sum_x2 - sum_x ** 2
    if abs(denom) < 1e-12:
        return None
    
    slope = (n * sum_xy - sum_x * sum_y) / denom
    return Measurement(value=float(slope))


def measure_section_metric_chine_height_ratio(geometry: Any, section_id: str) -> Optional[Measurement]:
    """Compute (chine_z - keel_z) / (sheer_z - keel_z) for a section."""
    sections = getattr(geometry, "sections", [])
    section = None
    for s in sections:
        if getattr(s, "id", None) == section_id:
            section = s
            break
    
    if section is None:
        return None
    
    pts = list(getattr(section, "points", []) or [])
    if len(pts) < 3:
        return None
    
    keel_z = min(float(p.position.z) for p in pts)
    sheer_z = max(float(p.position.z) for p in pts)
    
    chine = _find_chine_like_point_from_hullsection(pts)
    if chine is None:
        return None
    chine_z = float(chine.position.z)
    
    depth = sheer_z - keel_z
    if depth < 1e-9:
        return None
    
    ratio = (chine_z - keel_z) / depth
    return Measurement(value=float(max(0.0, min(1.0, ratio))))


# DEADRISE PROGRESSION

def measure_longitudinal_metric_deadrise_progression_shape(geometry: Any) -> Optional[Measurement]:
    """Compute warp score: normalized curvature of deadrise progression."""
    sections = getattr(geometry, "sections", [])
    if len(sections) < 5:
        return None
    
    loa = _get_loa_from_geometry(geometry, sections)
    
    pairs: List[Tuple[float, float]] = []
    for s in sections:
        pts = list(getattr(s, "points", []) or [])
        if len(pts) < 3:
            continue
        
        keel_i = min(range(len(pts)), key=lambda i: float(pts[i].position.z))
        chine = _find_chine_like_point_from_hullsection(pts)
        if chine is None:
            continue
        
        ky = float(pts[keel_i].position.y)
        kz = float(pts[keel_i].position.z)
        cy = float(chine.position.y)
        cz = float(chine.position.z)
        
        dy = cy - ky
        dz = cz - kz
        if abs(dy) < 1e-12:
            continue
        
        beta = math.degrees(math.atan2(abs(dz), abs(dy)))
        x_m = float(getattr(s, "x_position", 0.0))
        pairs.append((x_m, beta))
    
    if len(pairs) < 5:
        return None
    
    pairs = sorted(pairs, key=lambda p: p[0])
    
    curvatures: List[float] = []
    for i in range(1, len(pairs) - 1):
        x0, b0 = pairs[i - 1]
        x1, b1 = pairs[i]
        x2, b2 = pairs[i + 1]
        
        dx1 = x1 - x0
        dx2 = x2 - x1
        if dx1 < 1e-9 or dx2 < 1e-9:
            continue
        
        d2b = ((b2 - b1) / dx2 - (b1 - b0) / dx1) / ((dx1 + dx2) / 2)
        curvatures.append(abs(d2b))
    
    if not curvatures:
        return None
    
    curvatures = sorted(curvatures)
    k_p95 = curvatures[int(0.95 * len(curvatures))]
    
    betas = [b for _x, b in pairs]
    span = max(betas) - min(betas)
    
    score = (k_p95 * (loa ** 2)) / max(span, 1e-9)
    score = max(0.0, min(1.0, score))
    
    return Measurement(value=float(score))


# ROCKER CURVATURE

def measure_longitudinal_metric_rocker_profile_curvature(geometry: Any) -> Optional[Measurement]:
    """Compute keel profile curvature: p95(|d²(keel_z)/dx²|) in 1/m."""
    keel_profile = list(getattr(geometry, "keel_profile", []) or [])
    if len(keel_profile) < 5:
        return None
    
    pts = sorted(keel_profile, key=lambda p: float(p.x))
    
    curvatures: List[float] = []
    for i in range(1, len(pts) - 1):
        x0, z0 = float(pts[i - 1].x), float(pts[i - 1].z)
        x1, z1 = float(pts[i].x), float(pts[i].z)
        x2, z2 = float(pts[i + 1].x), float(pts[i + 1].z)
        
        dx1 = x1 - x0
        dx2 = x2 - x1
        if dx1 < 1e-9 or dx2 < 1e-9:
            continue
        
        d2z = ((z2 - z1) / dx2 - (z1 - z0) / dx1) / ((dx1 + dx2) / 2)
        curvatures.append(abs(d2z))
    
    if not curvatures:
        return None
    
    curvatures = sorted(curvatures)
    k_p95 = curvatures[int(0.95 * len(curvatures))]
    
    return Measurement(value=float(k_p95))


# ---------------------------------------------------------------------------
# Registry (Phase 1)
# ---------------------------------------------------------------------------

# Canonical registry. Keyed by observable_id.
OBSERVABLE_REGISTRY: Dict[str, ObservableSpec] = {
    # DIRECT controls
    "section_metric:deadrise_deg_at_chine": ObservableSpec(
        observable_id="section_metric:deadrise_deg_at_chine",
        controllable=True,
        control_mode="DIRECT",
        unit="deg",
        tolerance=0.5,
        max_delta=15.0,
        knobs=["keel_z", "bottom_z_distribution"],
        constraints=["identity_continuity", "z_monotone", "point_count_constant"],
        side_effects=["longitudinal_metric:deadrise_drop_deg", "longitudinal_metric:keel_slope_deg_p95"],
    ),
    "section_metric:max_half_beam_m": ObservableSpec(
        observable_id="section_metric:max_half_beam_m",
        controllable=True,
        control_mode="DIRECT",
        unit="m",
        tolerance=0.02,
        max_delta=1.0,
        knobs=["section_y_scale"],
        constraints=["identity_continuity", "y_nonnegative", "point_count_constant"],
        side_effects=["longitudinal_metric:entry_fineness_p95"],
    ),
    "section_metric:sheer_z_m": ObservableSpec(
        observable_id="section_metric:sheer_z_m",
        controllable=True,
        control_mode="DIRECT",
        unit="m",
        tolerance=0.02,
        max_delta=1.0,
        knobs=["sheer_z_translate"],
        constraints=["identity_continuity", "z_monotone", "point_count_constant"],
        side_effects=["longitudinal_metric:sheer_rise_m"],
    ),
    # Measurable-only section metrics
    "section_metric:keel_z_m": ObservableSpec(
        observable_id="section_metric:keel_z_m",
        controllable=False,
        control_mode="COMPILED",
        unit="m",
        tolerance=0.02,
        max_delta=1.0,
        reason="Phase 1 does not provide a direct keel rocker control; use longitudinal_metric:keel_slope_deg_p95 as a ruler.",
        alternatives=["longitudinal_metric:keel_slope_deg_p95"],
    ),
    "section_metric:chine_z_m": ObservableSpec(
        observable_id="section_metric:chine_z_m",
        controllable=False,
        control_mode="COMPILED",
        unit="m",
        tolerance=0.02,
        max_delta=1.0,
        reason="Phase 1 uses geometric chine anchoring for deadrise; direct chine_z control is deferred.",
        alternatives=["section_metric:deadrise_deg_at_chine"],
    ),
    "section_metric:topside_angle_deg_above_chine": ObservableSpec(
        observable_id="section_metric:topside_angle_deg_above_chine",
        controllable=False,
        control_mode="COMPILED",
        unit="deg",
        tolerance=1.0,
        max_delta=10.0,
        reason="Phase 1 focuses on bottom character; topside compiled controls are deferred.",
        alternatives=[],
    ),
    # Measurable-only (Phase 2 controllability)
    "longitudinal_metric:deadrise_drop_deg": ObservableSpec(
        observable_id="longitudinal_metric:deadrise_drop_deg",
        controllable=False,
        control_mode="COMPILED",
        unit="deg",
        tolerance=1.0,
        max_delta=20.0,
        reason="Derived from section_metric:deadrise_deg_at_chine across stations; Phase 2 may offer a compiled control.",
        alternatives=["section_metric:deadrise_deg_at_chine"],
    ),
    "longitudinal_metric:keel_slope_deg_p95": ObservableSpec(
        observable_id="longitudinal_metric:keel_slope_deg_p95",
        controllable=False,
        control_mode="COMPILED",
        unit="deg",
        tolerance=0.5,
        max_delta=10.0,
        reason="Derived from keel_z schedule; Phase 2 may offer compiled rocker control.",
        alternatives=["section_metric:keel_z_m"],
    ),
    "longitudinal_metric:sheer_rise_m": ObservableSpec(
        observable_id="longitudinal_metric:sheer_rise_m",
        controllable=False,
        control_mode="COMPILED",
        unit="m",
        tolerance=0.05,
        max_delta=1.0,
        reason="Phase 1 controls sheer via section_metric:sheer_z_m within station_range; compiled control comes in Phase 2.",
        alternatives=["section_metric:sheer_z_m"],
    ),
    "longitudinal_metric:entry_fineness_p95": ObservableSpec(
        observable_id="longitudinal_metric:entry_fineness_p95",
        controllable=False,
        control_mode="COMPILED",
        unit="ratio",
        tolerance=0.02,
        max_delta=0.2,
        reason="Phase 2 compiled control: adjust forebody max_half_beam_m schedule in station_range to hit target slope.",
        alternatives=["section_metric:max_half_beam_m"],
    ),
    # === CHARACTER OBSERVABLES (Phase 1: Measurable Only) ===
    
    # Sheer shape
    "longitudinal_metric:sheer_peak_station": ObservableSpec(
        observable_id="longitudinal_metric:sheer_peak_station",
        measurable=True,
        controllable=False,
        control_mode="COMPILED",
        unit="ratio",
        tolerance=0.02,
        max_delta=0.1,
        reason="Phase 1 measurable only; control via sheer_z_m schedule in Phase 2.",
        alternatives=["section_metric:sheer_z_m"],
    ),
    "longitudinal_metric:sheer_curvature_peak_station": ObservableSpec(
        observable_id="longitudinal_metric:sheer_curvature_peak_station",
        measurable=True,
        controllable=False,
        control_mode="OPTIMIZED",
        unit="ratio",
        tolerance=0.03,
        max_delta=0.15,
        reason="Requires solver to hit specific curvature peak location.",
        alternatives=["section_metric:sheer_z_m"],
    ),
    # Stem/bow
    "profile_metric:stem_rake_deg": ObservableSpec(
        observable_id="profile_metric:stem_rake_deg",
        measurable=True,
        controllable=False,
        control_mode="COMPILED",
        unit="deg",
        tolerance=1.0,
        max_delta=5.0,
        reason="Phase 1 measurable only; control via bow geometry params in Phase 2.",
    ),
    "profile_metric:stem_concavity_ratio": ObservableSpec(
        observable_id="profile_metric:stem_concavity_ratio",
        measurable=True,
        controllable=False,
        control_mode="COMPILED",
        unit="ratio",
        tolerance=0.01,
        max_delta=0.05,
        reason="Phase 1 measurable only; requires bow/stem shape controls (Phase 2).",
    ),
    # Entry sharpness
    "longitudinal_metric:entry_half_angle_deg": ObservableSpec(
        observable_id="longitudinal_metric:entry_half_angle_deg",
        measurable=True,
        controllable=False,
        control_mode="COMPILED",
        unit="deg",
        tolerance=1.0,
        max_delta=5.0,
        reason="Phase 1 measurable only; control via forward beam schedule.",
        alternatives=["section_metric:max_half_beam_m"],
    ),
    "longitudinal_metric:bow_fineness_ratio": ObservableSpec(
        observable_id="longitudinal_metric:bow_fineness_ratio",
        measurable=True,
        controllable=False,
        control_mode="COMPILED",
        unit="ratio",
        tolerance=0.02,
        max_delta=0.1,
        reason="Phase 1 measurable only; control via forward beam schedule.",
        alternatives=["section_metric:max_half_beam_m"],
    ),
    # Transom
    "profile_metric:transom_rake_deg": ObservableSpec(
        observable_id="profile_metric:transom_rake_deg",
        measurable=True,
        controllable=False,
        control_mode="DIRECT",
        unit="deg",
        tolerance=1.0,
        max_delta=5.0,
        reason="Measured from compiler-emitted transom_outline feature curve (Section 0 prerequisite).",
    ),
    "profile_metric:transom_beam_ratio": ObservableSpec(
        observable_id="profile_metric:transom_beam_ratio",
        measurable=True,
        controllable=False,
        control_mode="COMPILED",
        unit="ratio",
        tolerance=0.02,
        max_delta=0.1,
        reason="Phase 1 measurable only; control via aft beam in Phase 2.",
        alternatives=["section_metric:max_half_beam_m"],
    ),
    # Chine progression
    "longitudinal_metric:chine_rise_rate": ObservableSpec(
        observable_id="longitudinal_metric:chine_rise_rate",
        measurable=True,
        controllable=False,
        control_mode="COMPILED",
        unit="ratio",
        tolerance=0.01,
        max_delta=0.05,
        reason="Phase 1 measurable only; compiled chine schedule control in Phase 2.",
    ),
    "section_metric:chine_height_ratio": ObservableSpec(
        observable_id="section_metric:chine_height_ratio",
        measurable=True,
        controllable=False,
        control_mode="COMPILED",
        unit="ratio",
        tolerance=0.02,
        max_delta=0.1,
        reason="Phase 1 measurable only; control via chine_z in Phase 2.",
    ),
    # Deadrise progression (warp score)
    "longitudinal_metric:deadrise_progression_shape": ObservableSpec(
        observable_id="longitudinal_metric:deadrise_progression_shape",
        measurable=True,
        controllable=False,
        control_mode="OPTIMIZED",
        unit="ratio",
        tolerance=0.02,
        max_delta=0.1,
        reason="Curvature-based warp score (stable); requires solver/compiled control to achieve specific warp.",
    ),
    # Rocker curvature
    "longitudinal_metric:rocker_profile_curvature": ObservableSpec(
        observable_id="longitudinal_metric:rocker_profile_curvature",
        measurable=True,
        controllable=False,
        control_mode="COMPILED",
        unit="1/m",
        tolerance=0.002,
        max_delta=0.01,
        reason="Phase 1 measurable only; control via keel_z schedule.",
    ),
}


def get_observable_spec(observable_id: str) -> Optional[ObservableSpec]:
    return OBSERVABLE_REGISTRY.get(str(observable_id or ""))

