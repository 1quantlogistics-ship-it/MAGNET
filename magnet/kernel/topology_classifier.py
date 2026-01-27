"""
Topology change classification (Phase 4: Hull Geometry Core).

Classifies how "big" an edit was in geometric terms by measuring anchor churn:
- INCREMENTAL: mostly the same anchors, small drift
- ADDITIVE: new anchors appeared (features added)
- SUBTRACTIVE: anchors disappeared (features removed)
- RESTRUCTURE: substantial churn / reconfiguration (stop editing, resynthesize)

This is used by edit boundary policy and the hull edit loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TopologyChangeType(Enum):
    INCREMENTAL = "incremental"
    ADDITIVE = "additive"
    SUBTRACTIVE = "subtractive"
    RESTRUCTURE = "restructure"


@dataclass(frozen=True)
class TopologyClassification:
    change_type: TopologyChangeType
    born_ratio: float
    retired_ratio: float
    degraded_ratio: float
    churn_ratio: float
    reason: str


def classify_topology_change(
    *,
    prev_count: int,
    cur_count: int,
    born_count: int,
    retired_count: int,
    degraded_count: int = 0,
    restructure_churn_ratio: float = 0.35,
    restructure_degraded_ratio: float = 0.35,
    minor_restructure_floor: float = 0.15,
) -> TopologyClassification:
    """
    Classify topology change severity from anchor lifecycle counts.
    """
    prev_n = max(int(prev_count), 0)
    cur_n = max(int(cur_count), 0)
    born = max(int(born_count), 0)
    retired = max(int(retired_count), 0)
    degraded = max(int(degraded_count), 0)

    denom_prev = max(prev_n, 1)
    denom_cur = max(cur_n, 1)
    denom = max(max(prev_n, cur_n), 1)

    born_ratio = born / denom_cur
    retired_ratio = retired / denom_prev
    degraded_ratio = degraded / denom
    churn_ratio = (born + retired) / denom

    # Edge cases
    if prev_n == 0 and cur_n > 0:
        return TopologyClassification(
            change_type=TopologyChangeType.ADDITIVE,
            born_ratio=born_ratio,
            retired_ratio=retired_ratio,
            degraded_ratio=degraded_ratio,
            churn_ratio=churn_ratio,
            reason="no previous anchors; anchors introduced",
        )
    if cur_n == 0 and prev_n > 0:
        return TopologyClassification(
            change_type=TopologyChangeType.SUBTRACTIVE,
            born_ratio=born_ratio,
            retired_ratio=retired_ratio,
            degraded_ratio=degraded_ratio,
            churn_ratio=churn_ratio,
            reason="no current anchors; anchors removed",
        )

    # Restructure conditions
    if degraded_ratio >= restructure_degraded_ratio:
        return TopologyClassification(
            change_type=TopologyChangeType.RESTRUCTURE,
            born_ratio=born_ratio,
            retired_ratio=retired_ratio,
            degraded_ratio=degraded_ratio,
            churn_ratio=churn_ratio,
            reason="too many degraded anchors",
        )
    if churn_ratio >= restructure_churn_ratio:
        return TopologyClassification(
            change_type=TopologyChangeType.RESTRUCTURE,
            born_ratio=born_ratio,
            retired_ratio=retired_ratio,
            degraded_ratio=degraded_ratio,
            churn_ratio=churn_ratio,
            reason="anchor churn exceeds restructure threshold",
        )
    if born > 0 and retired > 0 and churn_ratio >= minor_restructure_floor:
        return TopologyClassification(
            change_type=TopologyChangeType.RESTRUCTURE,
            born_ratio=born_ratio,
            retired_ratio=retired_ratio,
            degraded_ratio=degraded_ratio,
            churn_ratio=churn_ratio,
            reason="mixed add/remove indicates reconfiguration",
        )

    # Additive/subtractive/simple incremental
    if born > 0 and retired == 0:
        return TopologyClassification(
            change_type=TopologyChangeType.ADDITIVE,
            born_ratio=born_ratio,
            retired_ratio=retired_ratio,
            degraded_ratio=degraded_ratio,
            churn_ratio=churn_ratio,
            reason="anchors added",
        )
    if retired > 0 and born == 0:
        return TopologyClassification(
            change_type=TopologyChangeType.SUBTRACTIVE,
            born_ratio=born_ratio,
            retired_ratio=retired_ratio,
            degraded_ratio=degraded_ratio,
            churn_ratio=churn_ratio,
            reason="anchors removed",
        )

    return TopologyClassification(
        change_type=TopologyChangeType.INCREMENTAL,
        born_ratio=born_ratio,
        retired_ratio=retired_ratio,
        degraded_ratio=degraded_ratio,
        churn_ratio=churn_ratio,
        reason="low churn and low degradation",
    )

