"""
Character guard (Phase 5: Iterative Edit Loop).

Spec/guide intent (§9 in CORTEX_V2_IMPLEMENTATION_GUIDE.md):
- In EDIT mode, character preservation is a pre-commit invariant.
- Every ADJUST/TARGET must be dry-run on a clone and evaluated before committing.
- If predicted drift > hard_limit: reject (requires REWRITE / resynthesis).
- If predicted drift > soft_limit: fail-closed (explicit user confirmation required).

This module is intentionally:
- type-agnostic (no hull type enums)
- deterministic
- geometry-derived (signatures extracted from HullGeometry, not user intent)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import math
from typing import Dict, List, Optional, Tuple

from magnet.hull_gen.geometry import HullGeometry, HullSection, Point3D


@dataclass(frozen=True)
class CharacterPreservationConfig:
    soft_limit: float = 0.05
    hard_limit: float = 0.20
    weights: Dict[str, float] = field(
        default_factory=lambda: {
            "chine_count": 5.0,
            "entry_angle": 1.0,
            # Deadrise proxy (midship bottom slope) - continuous but identity-relevant.
            "bottom_angle": 1.0,
            # Direct midship deadrise if available on sections (generator-derived).
            "deadrise_midship_deg": 1.0,
            "sheer_curvature": 0.5,
        }
    )


@dataclass(frozen=True)
class CharacterSignature:
    """
    A small set of derived, stable-ish geometry descriptors.

    Important: this signature is not "the truth" of a vessel, it is a guardrail
    to prevent identity-breaking edits from sneaking into EDIT mode.
    """

    metrics: Dict[str, float]
    signature_id: str
    schema_version: str = "1.0"


@dataclass(frozen=True)
class CharacterGuardResult:
    decision: str  # "pass" | "needs_confirmation" | "reject_rewrite"
    predicted_drift: float
    reason: str
    baseline_id: str


def extract_character_signature(geometry: HullGeometry) -> CharacterSignature:
    """
    Derive a character signature from canonical HullGeometry.

    Uses feature curves produced during compilation:
    - `geometry.chine_curve` (chine line proxy)
    - `geometry.deck_edge` (sheer line)

    Also derives an entry-angle proxy from the forward-most section's lower profile.
    """
    metrics: Dict[str, float] = {}

    # Topological-ish proxy: presence of a chine curve (0/1 for now).
    chine_count = 1.0 if (geometry.chine_curve and len(geometry.chine_curve) >= 2) else 0.0
    metrics["chine_count"] = chine_count

    # Continuous proxy: entry angle at bow (degrees)
    entry_angle = _estimate_entry_angle_deg(geometry.sections or [])
    if entry_angle is not None:
        metrics["entry_angle"] = float(entry_angle)

    # Continuous proxy: midship bottom angle (degrees) - deadrise-like.
    bottom_angle = _estimate_midship_bottom_angle_deg(geometry.sections or [])
    if bottom_angle is not None:
        metrics["bottom_angle"] = float(bottom_angle)

    # If sections provide explicit deadrise (generator-derived), include it.
    midship_deadrise = _estimate_midship_deadrise_deg(geometry.sections or [])
    if midship_deadrise is not None:
        metrics["deadrise_midship_deg"] = float(midship_deadrise)

    # Aesthetic proxy: sheer curvature along deck edge
    sheer_curve = geometry.deck_edge or []
    if len(sheer_curve) >= 3:
        metrics["sheer_curvature"] = float(_polyline_turning_curvature(sheer_curve))

    sig_id = _hash_metrics(metrics)
    return CharacterSignature(metrics=metrics, signature_id=sig_id)


def compute_weighted_drift(
    baseline: CharacterSignature | Dict[str, float],
    candidate: CharacterSignature | Dict[str, float],
    *,
    weights: Dict[str, float],
) -> float:
    """
    Weighted relative drift, skipping missing/zero baseline terms.
    """
    b = baseline.metrics if isinstance(baseline, CharacterSignature) else dict(baseline or {})
    c = candidate.metrics if isinstance(candidate, CharacterSignature) else dict(candidate or {})

    weighted = 0.0
    total = 0.0
    for key, w in (weights or {}).items():
        if key not in b or key not in c:
            continue
        bval = b.get(key)
        cval = c.get(key)
        if bval in (None,) or cval in (None,):
            continue
        try:
            bval_f = float(bval)
            cval_f = float(cval)
        except Exception:
            continue
        if abs(bval_f) < 1e-12:
            continue
        d = abs(cval_f - bval_f) / abs(bval_f)
        weighted += d * float(w)
        total += float(w)
    return weighted / max(total, 1e-9)


def evaluate_character_guard(
    *,
    baseline: CharacterSignature,
    candidate: CharacterSignature,
    config: CharacterPreservationConfig = CharacterPreservationConfig(),
) -> CharacterGuardResult:
    predicted = compute_weighted_drift(baseline, candidate, weights=config.weights)
    if predicted > float(config.hard_limit):
        return CharacterGuardResult(
            decision="reject_rewrite",
            predicted_drift=float(predicted),
            reason="would_break_character",
            baseline_id=baseline.signature_id,
        )
    if predicted > float(config.soft_limit):
        return CharacterGuardResult(
            decision="needs_confirmation",
            predicted_drift=float(predicted),
            reason="needs_confirmation",
            baseline_id=baseline.signature_id,
        )
    return CharacterGuardResult(
        decision="pass",
        predicted_drift=float(predicted),
        reason="within_limits",
        baseline_id=baseline.signature_id,
    )


def baseline_from_state_dict(state_dict: Dict[str, object]) -> Optional[CharacterSignature]:
    """
    Read baseline signature from canonical state dict, if present.

    Storage convention from guide:
      metadata.character_baseline_v1 = {"schema_version":"1.0","signature_id":"...","metrics":{...}}
    """
    md = (state_dict or {}).get("metadata") if isinstance(state_dict, dict) else None
    if not isinstance(md, dict):
        return None
    raw = md.get("character_baseline_v1")
    if not isinstance(raw, dict):
        return None
    metrics = raw.get("metrics")
    if not isinstance(metrics, dict):
        return None
    sid = raw.get("signature_id") or _hash_metrics(metrics)
    try:
        return CharacterSignature(metrics={k: float(v) for k, v in metrics.items()}, signature_id=str(sid))
    except Exception:
        return None


def baseline_to_state_payload(sig: CharacterSignature) -> Dict[str, object]:
    return {"schema_version": sig.schema_version, "signature_id": sig.signature_id, "metrics": dict(sig.metrics)}


# -------------------------
# Internals
# -------------------------


def _hash_metrics(metrics: Dict[str, float]) -> str:
    items = sorted((str(k), float(v)) for k, v in (metrics or {}).items())
    payload = "|".join(f"{k}={v:.8f}" for k, v in items)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _estimate_entry_angle_deg(sections: List[HullSection]) -> Optional[float]:
    """
    Estimate bow entry angle (degrees) from the forward-most section.

    Heuristic:
    - take forward-most section
    - find keel z_min and deck z_max
    - sample at 10% height above keel
    - compute local dy/dz slope over a small z window
    - convert to an angle in degrees (0=vertical, 90=horizontal)
    """
    if not sections:
        return None
    fwd = max(sections, key=lambda s: float(getattr(s, "x_position", 0.0)))
    if not fwd.points or len(fwd.points) < 3:
        return None

    pts = sorted(fwd.points, key=lambda p: float(p.position.z))
    z_min = float(pts[0].position.z)
    z_max = float(pts[-1].position.z)
    z_rng = z_max - z_min
    if z_rng < 1e-6:
        return None

    z0 = z_min + 0.10 * z_rng
    z1 = z_min + 0.15 * z_rng
    p0 = fwd.get_point_at_z(z0)
    p1 = fwd.get_point_at_z(z1)
    if p0 is None or p1 is None:
        return None

    dy = float(p1.y) - float(p0.y)
    dz = float(p1.z) - float(p0.z)
    if abs(dz) < 1e-9 and abs(dy) < 1e-9:
        return None

    # Angle of the section profile tangent relative to vertical in (y,z).
    # A finer entry has smaller dy for given dz → smaller angle.
    angle = math.degrees(math.atan2(abs(dy), abs(dz)))
    return float(angle)


def _estimate_midship_bottom_angle_deg(sections: List[HullSection]) -> Optional[float]:
    """
    Estimate a deadrise-like angle from the midship section's bottom slope.

    Heuristic:
    - choose section closest to station=0.5 (or median x_position)
    - sample near keel (10-15% of height) and compute dy/dz slope
    - return angle in degrees (0=vertical, 90=horizontal)
    """
    if not sections:
        return None

    # Prefer station if present; otherwise use x_position median.
    try:
        mid = min(sections, key=lambda s: abs(float(getattr(s, "station", 0.5)) - 0.5))
    except Exception:
        xs = sorted(float(getattr(s, "x_position", 0.0)) for s in sections)
        if not xs:
            return None
        x_mid = xs[len(xs) // 2]
        mid = min(sections, key=lambda s: abs(float(getattr(s, "x_position", 0.0)) - x_mid))

    if not mid.points or len(mid.points) < 3:
        return None

    pts = sorted(mid.points, key=lambda p: float(p.position.z))
    z_min = float(pts[0].position.z)
    z_max = float(pts[-1].position.z)
    z_rng = z_max - z_min
    if z_rng < 1e-6:
        return None

    z0 = z_min + 0.10 * z_rng
    z1 = z_min + 0.15 * z_rng
    p0 = mid.get_point_at_z(z0)
    p1 = mid.get_point_at_z(z1)
    if p0 is None or p1 is None:
        return None

    dy = float(p1.y) - float(p0.y)
    dz = float(p1.z) - float(p0.z)
    if abs(dz) < 1e-9 and abs(dy) < 1e-9:
        return None

    angle = math.degrees(math.atan2(abs(dy), abs(dz)))
    return float(angle)


def _estimate_midship_deadrise_deg(sections: List[HullSection]) -> Optional[float]:
    """
    Read midship deadrise from section metadata if available.
    """
    if not sections:
        return None
    try:
        mid = min(sections, key=lambda s: abs(float(getattr(s, "station", 0.5)) - 0.5))
    except Exception:
        mid = sections[len(sections) // 2]
    try:
        val = float(getattr(mid, "deadrise_deg", 0.0))
    except Exception:
        return None
    # Deadrise of 0 is valid; keep it.
    return val


def _polyline_turning_curvature(points: List[Point3D]) -> float:
    """
    A simple, unitless curvature proxy: average turning angle per segment length.
    """
    if len(points) < 3:
        return 0.0
    total_turn = 0.0
    total_len = 0.0
    for i in range(1, len(points) - 1):
        p0, p1, p2 = points[i - 1], points[i], points[i + 1]
        v1 = (float(p1.x - p0.x), float(p1.y - p0.y), float(p1.z - p0.z))
        v2 = (float(p2.x - p1.x), float(p2.y - p1.y), float(p2.z - p1.z))
        l1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2 + v1[2] ** 2)
        l2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2 + v2[2] ** 2)
        if l1 < 1e-9 or l2 < 1e-9:
            continue
        dot = (v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]) / (l1 * l2)
        dot = max(-1.0, min(1.0, dot))
        turn = math.acos(dot)
        total_turn += turn
        total_len += (l1 + l2) / 2.0
    return float(total_turn / max(total_len, 1e-9))

