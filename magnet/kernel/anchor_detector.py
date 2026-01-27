"""
Anchor detection (Phase 4: Hull Geometry Core).

HARD RULE: No form/type enums. Anchors are detected from geometry and only
optionally given post-hoc semantic labels for UI/reporting.

This module defines:
- `TrackedAnchor`: a detected, trackable anchor point on hull geometry.
- `detect_anchors`: geometry-based anchor detection across all sections.
- `classify_anchor`: post-hoc semantic labeling (never feeds back into synthesis).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import List, Optional, Tuple
import uuid as _uuid

from magnet.hull_gen.geometry import HullGeometry, HullSection, Point3D


class AnchorStatus(Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    RETIRED = "retired"


class AnchorDetectionMethod(Enum):
    """How the anchor was detected (not what it 'is')."""

    CURVATURE_MAXIMUM = "curvature_maximum"
    CURVATURE_MINIMUM = "curvature_minimum"
    DISCONTINUITY = "discontinuity"
    VERTICAL_EXTREMUM = "vertical_extremum"
    HORIZONTAL_EXTREMUM = "horizontal_extremum"
    INFLECTION = "inflection"
    CONSTRAINT_DEFINED = "constraint_defined"


@dataclass(frozen=True)
class TrackedAnchor:
    """
    Anchor detected from geometry, not pre-categorized.

    `semantic_label` is DERIVED output. It MUST NOT be used as input to any
    geometry generation or constraint satisfaction.
    """

    uuid: str
    section_id: str
    point_index: int
    position: Tuple[float, float, float]
    detection_method: AnchorDetectionMethod
    confidence: float = 1.0
    status: AnchorStatus = AnchorStatus.ACTIVE
    semantic_label: Optional[str] = None
    local_curvature: Optional[float] = None
    tangent_angle_deg: Optional[float] = None


def detect_anchors(geometry: HullGeometry) -> List[TrackedAnchor]:
    """
    Detect anchors from geometry features.

    This function never assumes a hull "type". It operates only on section
    polylines and returns anchors with detection methods and (optional) labels.
    """
    anchors: List[TrackedAnchor] = []

    if geometry is None or not geometry.sections:
        return anchors

    for sec_idx, section in enumerate(geometry.sections):
        section_id = _section_id(geometry, sec_idx, section)
        anchors.extend(_detect_section_anchors(section, section_id, geometry.hull_id))

    return anchors


def classify_anchor(anchor: TrackedAnchor, geometry: HullGeometry) -> str:
    """
    Derive semantic label from detected anchor + local context.

    Output is descriptive, and may be novel. This label MUST NOT feed back into
    synthesis decisions.
    """
    # Use the anchor's own section to normalize position.
    section = _get_section_by_id(geometry, anchor.section_id)
    if section is None or not section.points:
        return "novel-feature"

    z_vals = [float(p.position.z) for p in section.points]
    y_vals = [float(p.position.y) for p in section.points]
    z_min, z_max = min(z_vals), max(z_vals)
    y_max = max(y_vals) if y_vals else 0.0

    z_range = (z_max - z_min) if (z_max - z_min) > 1e-12 else 1.0
    z_norm = (float(anchor.position[2]) - z_min) / z_range
    y_norm = float(anchor.position[1]) / y_max if y_max > 1e-12 else 0.0

    m = anchor.detection_method
    if m == AnchorDetectionMethod.VERTICAL_EXTREMUM:
        if z_norm < 0.1:
            return "keel-like"
        if z_norm > 0.9:
            return "sheer-like"
        return "vertical-extremum"

    if m == AnchorDetectionMethod.HORIZONTAL_EXTREMUM:
        return "beam-max"

    if m in (AnchorDetectionMethod.DISCONTINUITY, AnchorDetectionMethod.CURVATURE_MAXIMUM):
        return "lower-chine-like" if z_norm < 0.5 else "upper-chine-like"

    if m == AnchorDetectionMethod.INFLECTION:
        return f"inflection-at-{z_norm:.2f}"

    if m == AnchorDetectionMethod.CURVATURE_MINIMUM:
        return f"flat-region-at-{z_norm:.2f}"

    # Novel/unknown feature: describe by normalized position.
    return f"feature-at-z{z_norm:.2f}-y{y_norm:.2f}"


# -------------------------
# Internal helpers
# -------------------------


def _section_id(geometry: HullGeometry, sec_idx: int, section: HullSection) -> str:
    hull_id = geometry.hull_id or "hull"
    # Prefer stable positional info when present; fall back to index.
    if section is not None and section.x_position is not None:
        try:
            x = float(section.x_position)
            return f"{hull_id}/sec/x={x:.6f}"
        except Exception:
            pass
    return f"{hull_id}/sec/{sec_idx:04d}"


def _get_section_by_id(geometry: HullGeometry, section_id: str) -> Optional[HullSection]:
    if geometry is None or not geometry.sections:
        return None
    for sec_idx, sec in enumerate(geometry.sections):
        if _section_id(geometry, sec_idx, sec) == section_id:
            return sec
    return None


def _detect_section_anchors(section: HullSection, section_id: str, hull_id: str) -> List[TrackedAnchor]:
    if section is None or len(section.points) < 2:
        return []

    pts = [p.position for p in section.points]
    z_vals = [float(p.z) for p in pts]
    y_vals = [float(p.y) for p in pts]

    anchors: List[TrackedAnchor] = []

    # --- extrema anchors (always available) ---
    keel_idx = int(min(range(len(pts)), key=lambda i: z_vals[i]))
    sheer_idx = int(max(range(len(pts)), key=lambda i: z_vals[i]))
    beam_idx = int(max(range(len(pts)), key=lambda i: y_vals[i]))

    anchors.append(_make_anchor(
        hull_id=hull_id,
        section_id=section_id,
        point_index=keel_idx,
        position=pts[keel_idx],
        method=AnchorDetectionMethod.VERTICAL_EXTREMUM,
        confidence=1.0,
        local_curvature=None,
        tangent_angle_deg=_tangent_angle_deg(pts, keel_idx),
    ))
    anchors.append(_make_anchor(
        hull_id=hull_id,
        section_id=section_id,
        point_index=sheer_idx,
        position=pts[sheer_idx],
        method=AnchorDetectionMethod.VERTICAL_EXTREMUM,
        confidence=1.0,
        local_curvature=None,
        tangent_angle_deg=_tangent_angle_deg(pts, sheer_idx),
    ))
    anchors.append(_make_anchor(
        hull_id=hull_id,
        section_id=section_id,
        point_index=beam_idx,
        position=pts[beam_idx],
        method=AnchorDetectionMethod.HORIZONTAL_EXTREMUM,
        confidence=1.0,
        local_curvature=None,
        tangent_angle_deg=_tangent_angle_deg(pts, beam_idx),
    ))

    # --- discontinuity / chine-like anchor via knee detection ---
    knee_idx, knee_score = _find_knee_discontinuity_index(pts)
    if knee_idx is not None:
        # Confidence is relative (bounded [0,1]).
        conf = max(0.0, min(1.0, knee_score / 90.0))  # 90deg turn ~= strong
        anchors.append(_make_anchor(
            hull_id=hull_id,
            section_id=section_id,
            point_index=knee_idx,
            position=pts[knee_idx],
            method=AnchorDetectionMethod.DISCONTINUITY,
            confidence=conf,
            local_curvature=_signed_discrete_curvature(pts, knee_idx),
            tangent_angle_deg=_tangent_angle_deg(pts, knee_idx),
        ))

    # --- curvature extrema / inflection anchors (best-effort) ---
    if len(pts) >= 5:
        k = [_signed_discrete_curvature(pts, i) for i in range(len(pts))]
        # Find local maxima in |k|
        for i in range(1, len(pts) - 1):
            if abs(k[i]) > abs(k[i - 1]) and abs(k[i]) > abs(k[i + 1]) and abs(k[i]) > 1e-6:
                anchors.append(_make_anchor(
                    hull_id=hull_id,
                    section_id=section_id,
                    point_index=i,
                    position=pts[i],
                    method=AnchorDetectionMethod.CURVATURE_MAXIMUM,
                    confidence=max(0.0, min(1.0, abs(k[i]) * 10.0)),
                    local_curvature=k[i],
                    tangent_angle_deg=_tangent_angle_deg(pts, i),
                ))
            # Inflection: sign change across neighbors (avoid zeros)
            if k[i - 1] * k[i + 1] < 0:
                anchors.append(_make_anchor(
                    hull_id=hull_id,
                    section_id=section_id,
                    point_index=i,
                    position=pts[i],
                    method=AnchorDetectionMethod.INFLECTION,
                    confidence=0.6,
                    local_curvature=k[i],
                    tangent_angle_deg=_tangent_angle_deg(pts, i),
                ))

    # Apply post-hoc labeling (never feeds back)
    # NOTE: Use a tiny temporary HullGeometry wrapper to reuse `classify_anchor`.
    # Here we only have the section; classification needs normalization context.
    tmp_geom = HullGeometry(hull_id=hull_id, sections=[section])
    labeled: List[TrackedAnchor] = []
    for a in anchors:
        label = classify_anchor(a, tmp_geom)
        labeled.append(TrackedAnchor(
            uuid=a.uuid,
            section_id=a.section_id,
            point_index=a.point_index,
            position=a.position,
            detection_method=a.detection_method,
            confidence=a.confidence,
            status=a.status,
            semantic_label=label,
            local_curvature=a.local_curvature,
            tangent_angle_deg=a.tangent_angle_deg,
        ))

    # Deduplicate by uuid (multiple detectors may hit same index/method)
    uniq: dict[str, TrackedAnchor] = {}
    for a in labeled:
        uniq[a.uuid] = a
    return list(uniq.values())


def _make_anchor(
    *,
    hull_id: str,
    section_id: str,
    point_index: int,
    position: Point3D,
    method: AnchorDetectionMethod,
    confidence: float,
    local_curvature: Optional[float],
    tangent_angle_deg: Optional[float],
) -> TrackedAnchor:
    # Deterministic UUID for reproducibility: stable for identical geometry.
    base = f"{hull_id}|{section_id}|{point_index}|{method.value}|{position.x:.6f}|{position.y:.6f}|{position.z:.6f}"
    uid = str(_uuid.uuid5(_uuid.NAMESPACE_URL, base))
    return TrackedAnchor(
        uuid=uid,
        section_id=section_id,
        point_index=int(point_index),
        position=(float(position.x), float(position.y), float(position.z)),
        detection_method=method,
        confidence=float(confidence),
        status=AnchorStatus.ACTIVE,
        semantic_label=None,
        local_curvature=local_curvature,
        tangent_angle_deg=tangent_angle_deg,
    )


def _tangent_angle_deg(points: List[Point3D], i: int) -> Optional[float]:
    if len(points) < 2:
        return None
    if i <= 0:
        p0, p1 = points[0], points[1]
    elif i >= len(points) - 1:
        p0, p1 = points[-2], points[-1]
    else:
        p0, p1 = points[i - 1], points[i + 1]
    dy = float(p1.y) - float(p0.y)
    dz = float(p1.z) - float(p0.z)
    if abs(dy) < 1e-12 and abs(dz) < 1e-12:
        return None
    return math.degrees(math.atan2(dz, dy))


def _signed_discrete_curvature(points: List[Point3D], i: int) -> float:
    """
    Signed discrete curvature in the (y,z) plane at index i.

    Uses triangle-based curvature: k = 2*A / (a*b*c) with sign from cross product.
    """
    n = len(points)
    if n < 3 or i <= 0 or i >= n - 1:
        return 0.0

    p0, p1, p2 = points[i - 1], points[i], points[i + 1]
    y0, z0 = float(p0.y), float(p0.z)
    y1, z1 = float(p1.y), float(p1.z)
    y2, z2 = float(p2.y), float(p2.z)

    dy1, dz1 = y1 - y0, z1 - z0
    dy2, dz2 = y2 - y1, z2 - z1

    a = math.hypot(dy1, dz1)
    b = math.hypot(dy2, dz2)
    dy3, dz3 = y2 - y0, z2 - z0
    c = math.hypot(dy3, dz3)
    if a < 1e-12 or b < 1e-12 or c < 1e-12:
        return 0.0

    cross = (dy1 * dz3 - dz1 * dy3)  # signed 2*area
    area2 = abs(cross)
    k = area2 / (a * b * c)  # equals 2*A/(abc)
    return k if cross >= 0 else -k


def _find_knee_discontinuity_index(points: List[Point3D]) -> Tuple[Optional[int], float]:
    """
    Knee detector (tangent break) on section polyline in (y,z).

    Returns:
      (index, score_deg) where score is the angle change in degrees.
    """
    n = len(points)
    if n < 4:
        return (None, 0.0)

    best_i: Optional[int] = None
    best_score = 0.0

    for i in range(1, n - 1):
        p0, p1, p2 = points[i - 1], points[i], points[i + 1]
        v1y, v1z = float(p1.y - p0.y), float(p1.z - p0.z)
        v2y, v2z = float(p2.y - p1.y), float(p2.z - p1.z)
        l1 = math.hypot(v1y, v1z)
        l2 = math.hypot(v2y, v2z)
        if l1 < 1e-12 or l2 < 1e-12:
            continue
        dot = (v1y * v2y + v1z * v2z) / (l1 * l2)
        dot = max(-1.0, min(1.0, dot))
        angle = math.degrees(math.acos(dot))
        if angle > best_score:
            best_score = angle
            best_i = i

    return (best_i, best_score)

