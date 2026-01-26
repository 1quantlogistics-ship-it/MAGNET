"""
Edit boundary policy (Phase 4: Hull Geometry Core).

Spec intent (LLM_NATIVE_SPATIAL_INTERFACE_SPEC-2.md §2.6):
- Hull EDIT operations must be topology-preserving.
- If edits cross a global viability boundary (anchor churn / drift / low confidence),
  the system must circuit-break and force resynthesis / REWRITE before corruption.

This module is intentionally simple and deterministic: it consumes anchor lifecycle
signals (born/retired/degraded, topology classification, confidence) and returns
an edit viability decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from magnet.kernel.anchor_detector import TrackedAnchor
from magnet.kernel.anchor_tracker import AnchorUpdateReport
from magnet.kernel.topology_classifier import TopologyChangeType


@dataclass(frozen=True)
class EditBoundaryConfig:
    """
    Circuit-breaker thresholds.

    These defaults are conservative; they can be moved into config later.
    """

    # If topology is RESTRUCTURE, never continue EDIT.
    restructure_forces_resynthesis: bool = True

    # Per-step fractions.
    max_retired_fraction: float = 0.25
    max_degraded_fraction: float = 0.25
    min_mean_confidence: float = 0.50

    # Novel features are allowed, but too many indicates we're losing interpretable anchors.
    max_novel_features_detected: int = 50


@dataclass(frozen=True)
class EditViabilityDecision:
    ok_to_continue_editing: bool
    requires_resynthesis: bool
    reason: str
    topology_change: TopologyChangeType
    prev_anchor_count: int
    cur_anchor_count: int
    born_count: int
    retired_count: int
    degraded_count: int
    born_fraction: float
    retired_fraction: float
    degraded_fraction: float
    mean_confidence: float
    warnings: List[str] = field(default_factory=list)


def evaluate_edit_boundary(
    *,
    prev_anchors: List[TrackedAnchor],
    cur_anchors: List[TrackedAnchor],
    update_report: AnchorUpdateReport,
    config: EditBoundaryConfig = EditBoundaryConfig(),
) -> EditViabilityDecision:
    """
    Decide whether we can continue in EDIT mode or must resynthesize.
    """
    prev_n = len(prev_anchors or [])
    cur_n = len(cur_anchors or [])

    born_n = len(update_report.born or [])
    retired_n = len(update_report.retired or [])
    degraded_n = len(update_report.degraded or [])

    born_fraction = born_n / max(cur_n, 1)
    retired_fraction = retired_n / max(prev_n, 1)
    degraded_fraction = degraded_n / max(max(prev_n, cur_n), 1)

    mean_conf = _mean_confidence(cur_anchors)
    warnings: List[str] = []

    # 1) Hard gate: restructure means leave EDIT.
    if config.restructure_forces_resynthesis and update_report.topology_change == TopologyChangeType.RESTRUCTURE:
        return EditViabilityDecision(
            ok_to_continue_editing=False,
            requires_resynthesis=True,
            reason="topology_restructure_detected",
            topology_change=update_report.topology_change,
            prev_anchor_count=prev_n,
            cur_anchor_count=cur_n,
            born_count=born_n,
            retired_count=retired_n,
            degraded_count=degraded_n,
            born_fraction=born_fraction,
            retired_fraction=retired_fraction,
            degraded_fraction=degraded_fraction,
            mean_confidence=mean_conf,
            warnings=warnings,
        )

    # 2) Anchor loss gate.
    if retired_fraction > config.max_retired_fraction:
        return EditViabilityDecision(
            ok_to_continue_editing=False,
            requires_resynthesis=True,
            reason="too_many_anchors_retired",
            topology_change=update_report.topology_change,
            prev_anchor_count=prev_n,
            cur_anchor_count=cur_n,
            born_count=born_n,
            retired_count=retired_n,
            degraded_count=degraded_n,
            born_fraction=born_fraction,
            retired_fraction=retired_fraction,
            degraded_fraction=degraded_fraction,
            mean_confidence=mean_conf,
            warnings=warnings,
        )

    # 3) Excessive degradation gate.
    if degraded_fraction > config.max_degraded_fraction:
        return EditViabilityDecision(
            ok_to_continue_editing=False,
            requires_resynthesis=True,
            reason="too_many_anchors_degraded",
            topology_change=update_report.topology_change,
            prev_anchor_count=prev_n,
            cur_anchor_count=cur_n,
            born_count=born_n,
            retired_count=retired_n,
            degraded_count=degraded_n,
            born_fraction=born_fraction,
            retired_fraction=retired_fraction,
            degraded_fraction=degraded_fraction,
            mean_confidence=mean_conf,
            warnings=warnings,
        )

    # 4) Low confidence gate.
    if mean_conf < config.min_mean_confidence:
        return EditViabilityDecision(
            ok_to_continue_editing=False,
            requires_resynthesis=True,
            reason="anchor_confidence_too_low",
            topology_change=update_report.topology_change,
            prev_anchor_count=prev_n,
            cur_anchor_count=cur_n,
            born_count=born_n,
            retired_count=retired_n,
            degraded_count=degraded_n,
            born_fraction=born_fraction,
            retired_fraction=retired_fraction,
            degraded_fraction=degraded_fraction,
            mean_confidence=mean_conf,
            warnings=warnings,
        )

    # 5) Novel features warning (not a hard stop by default).
    if update_report.novel_features_detected > config.max_novel_features_detected:
        warnings.append("many_novel_features_detected")

    return EditViabilityDecision(
        ok_to_continue_editing=True,
        requires_resynthesis=False,
        reason="within_edit_boundary",
        topology_change=update_report.topology_change,
        prev_anchor_count=prev_n,
        cur_anchor_count=cur_n,
        born_count=born_n,
        retired_count=retired_n,
        degraded_count=degraded_n,
        born_fraction=born_fraction,
        retired_fraction=retired_fraction,
        degraded_fraction=degraded_fraction,
        mean_confidence=mean_conf,
        warnings=warnings,
    )


def _mean_confidence(anchors: List[TrackedAnchor]) -> float:
    if not anchors:
        return 0.0
    vals = [float(a.confidence) for a in anchors if a is not None]
    if not vals:
        return 0.0
    return sum(vals) / len(vals)

