"""
Post-hoc hull classification (Phase 3).

Classification is DERIVED output for UI/reporting. It MUST NOT feed back into
constraint synthesis or geometry generation decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from magnet.hull_gen.geometry import EdgeType, HullGeometry


def calculate_froude(speed_kts: float, lwl_m: float) -> float:
    """Froude number (Fn = V / sqrt(g*L))."""
    if not speed_kts or not lwl_m or lwl_m <= 0:
        return 0.0
    v = float(speed_kts) * 0.514444
    g = 9.81
    return float(v / ((g * float(lwl_m)) ** 0.5))


def _body_count(geometry: HullGeometry) -> int:
    try:
        body_ids = sorted(list(set(getattr(s, "body_id", "main") for s in geometry.sections)))
        return len(body_ids) if body_ids else 1
    except Exception:
        return 1


def detect_hard_chine(geometry: HullGeometry) -> bool:
    """Detect presence of a hard chine-like discontinuity from section metadata."""
    for sec in geometry.sections:
        for p in getattr(sec, "points", []) or []:
            if getattr(p, "is_chine", False) and getattr(p, "edge_type", None) == EdgeType.HARD:
                return True
    return False


def detect_deep_v(geometry: HullGeometry) -> bool:
    """
    Heuristic deep-V detection: estimate deadrise at midship from keel→chine slope.
    """
    if not geometry.sections:
        return False
    mid = geometry.sections[len(geometry.sections) // 2]
    pts = getattr(mid, "points", []) or []
    keel = next((p for p in pts if getattr(p, "is_keel", False)), None)
    chine = next((p for p in pts if getattr(p, "is_chine", False)), None)
    if not keel or not chine:
        return False
    dy = abs(float(chine.position.y) - float(keel.position.y))
    dz = abs(float(chine.position.z) - float(keel.position.z))
    if dy <= 1e-6:
        return False
    import math

    deadrise = math.degrees(math.atan2(dz, dy))
    return deadrise >= 18.0


def detect_novel_features(_geometry: HullGeometry) -> List[str]:
    """
    Placeholder for novelty detection.
    Returns a list of detected "doesn't fit common buckets" markers.
    """
    return []


@dataclass(frozen=True)
class HullClassification:
    """
    Post-hoc hull classification for UI/reporting ONLY.

    This is DERIVED output, never synthesis input.
    """

    regime: str  # "displacement", "semi-displacement", "planing"
    body_count: int
    form_descriptors: List[str] = field(default_factory=list)
    novel_features: List[str] = field(default_factory=list)


def classify_hull(
    geometry: HullGeometry,
    speed_kts: Optional[float] = None,
    lwl_m: Optional[float] = None,
) -> HullClassification:
    """
    Derive classification from geometry. For display only.

    - Regime is inferred from Froude if speed/lwl are provided (or defaults to displacement).
    - Body count is derived from geometry sections' body_id (not from any "type" string).
    """
    body_count = _body_count(geometry)

    fn = calculate_froude(float(speed_kts or 0.0), float(lwl_m or 0.0))
    if fn > 0.55:
        regime = "planing"
    elif fn > 0.35:
        regime = "semi-displacement"
    else:
        regime = "displacement"

    descriptors: List[str] = []
    if detect_hard_chine(geometry):
        descriptors.append("hard-chine")
    if detect_deep_v(geometry):
        descriptors.append("deep-v")
    if body_count > 1:
        descriptors.append(f"multi-body:{body_count}")

    return HullClassification(
        regime=regime,
        body_count=body_count,
        form_descriptors=descriptors,
        novel_features=detect_novel_features(geometry),
    )

