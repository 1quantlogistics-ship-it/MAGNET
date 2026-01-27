"""
Anchor tracking (Phase 4: Hull Geometry Core).

Tracks anchors across edits with a lifecycle:
- born: new anchors appear
- updated: existing anchors matched and updated in-place (uuid preserved)
- degraded: matched but drift exceeds tolerance
- retired: previous anchors no longer present

This is a geometry-first tracking system. It does not assume any hull "type".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from magnet.hull_gen.geometry import HullGeometry
from magnet.kernel.anchor_detector import AnchorStatus, TrackedAnchor, detect_anchors
from magnet.kernel.topology_classifier import TopologyChangeType, classify_topology_change


@dataclass
class AnchorUpdateReport:
    born: List[str] = field(default_factory=list)
    updated: List[str] = field(default_factory=list)
    degraded: List[str] = field(default_factory=list)
    retired: List[str] = field(default_factory=list)
    topology_change: TopologyChangeType = TopologyChangeType.INCREMENTAL
    novel_features_detected: int = 0


class AnchorTracker:
    """
    Tracks anchors across successive hull geometries.

    The tracker preserves UUIDs for matched anchors, allowing downstream
    systems (character guard, edit boundary policy) to reason about drift.
    """

    def __init__(
        self,
        *,
        match_distance_m: float = 0.25,
        degraded_distance_m: float = 0.75,
    ) -> None:
        self.match_distance_m = float(match_distance_m)
        self.degraded_distance_m = float(degraded_distance_m)

    def initialize(self, geometry: HullGeometry) -> List[TrackedAnchor]:
        return detect_anchors(geometry)

    def update(
        self,
        previous: List[TrackedAnchor],
        geometry: HullGeometry,
    ) -> Tuple[List[TrackedAnchor], AnchorUpdateReport]:
        """
        Update tracked anchors from previous → current geometry.

        Returns:
          (current_anchors, report)
        """
        report = AnchorUpdateReport()

        prev = list(previous or [])
        cur = detect_anchors(geometry)

        if not cur:
            # No anchors detected => all previous are retired.
            report.retired = [a.uuid for a in prev]
            report.topology_change = (
                TopologyChangeType.SUBTRACTIVE if report.retired else TopologyChangeType.INCREMENTAL
            )
            return ([], report)

        matched_prev: Dict[str, bool] = {a.uuid: False for a in prev}
        used_cur: Dict[str, bool] = {a.uuid: False for a in cur}

        # Greedy matching by nearest distance within threshold, constrained by detection method.
        pairs: List[Tuple[float, TrackedAnchor, TrackedAnchor]] = []
        for p in prev:
            for c in cur:
                if p.detection_method != c.detection_method:
                    continue
                d = _distance(p.position, c.position)
                if d <= self.match_distance_m:
                    pairs.append((d, p, c))
        pairs.sort(key=lambda t: t[0])

        updated: List[TrackedAnchor] = []

        for d, p, c in pairs:
            if matched_prev.get(p.uuid, False):
                continue
            if used_cur.get(c.uuid, False):
                continue

            matched_prev[p.uuid] = True
            used_cur[c.uuid] = True

            status = AnchorStatus.ACTIVE
            if d > self.degraded_distance_m:
                status = AnchorStatus.DEGRADED
                report.degraded.append(p.uuid)

            # Preserve uuid from previous anchor; update everything else from current.
            updated.append(TrackedAnchor(
                uuid=p.uuid,
                section_id=c.section_id,
                point_index=c.point_index,
                position=c.position,
                detection_method=c.detection_method,
                confidence=c.confidence,
                status=status,
                semantic_label=c.semantic_label,
                local_curvature=c.local_curvature,
                tangent_angle_deg=c.tangent_angle_deg,
            ))
            report.updated.append(p.uuid)

        # Unmatched current anchors are born.
        for c in cur:
            if used_cur.get(c.uuid, False):
                continue
            updated.append(c)
            report.born.append(c.uuid)

        # Unmatched previous anchors are retired.
        for p in prev:
            if matched_prev.get(p.uuid, False):
                continue
            report.retired.append(p.uuid)

        topo = classify_topology_change(
            prev_count=len(prev),
            cur_count=len(updated),
            born_count=len(report.born),
            retired_count=len(report.retired),
            degraded_count=len(report.degraded),
        )
        report.topology_change = topo.change_type

        # Count "novel" anchors (anything not in the simple label set).
        known = {"keel-like", "sheer-like", "beam-max", "lower-chine-like", "upper-chine-like"}
        report.novel_features_detected = sum(
            1 for a in updated if (a.semantic_label is not None and a.semantic_label not in known)
        )

        return (updated, report)


def _distance(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    dx = float(a[0]) - float(b[0])
    dy = float(a[1]) - float(b[1])
    dz = float(a[2]) - float(b[2])
    return (dx * dx + dy * dy + dz * dz) ** 0.5

