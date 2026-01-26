from magnet.kernel.anchor_detector import AnchorDetectionMethod, AnchorStatus, TrackedAnchor
from magnet.kernel.anchor_tracker import AnchorUpdateReport
from magnet.kernel.edit_boundary import EditBoundaryConfig, evaluate_edit_boundary
from magnet.kernel.topology_classifier import TopologyChangeType


def _anchor(uid: str, *, conf: float = 1.0) -> TrackedAnchor:
    return TrackedAnchor(
        uuid=uid,
        section_id="h/sec/0",
        point_index=0,
        position=(0.0, 0.0, 0.0),
        detection_method=AnchorDetectionMethod.VERTICAL_EXTREMUM,
        confidence=conf,
        status=AnchorStatus.ACTIVE,
        semantic_label="keel-like",
        local_curvature=None,
        tangent_angle_deg=None,
    )


def test_edit_boundary_restructure_forces_resynthesis():
    prev = [_anchor("a1"), _anchor("a2")]
    cur = [_anchor("a1"), _anchor("a2")]
    report = AnchorUpdateReport(
        born=[],
        updated=["a1", "a2"],
        degraded=[],
        retired=[],
        topology_change=TopologyChangeType.RESTRUCTURE,
        novel_features_detected=0,
    )

    decision = evaluate_edit_boundary(prev_anchors=prev, cur_anchors=cur, update_report=report)
    assert decision.ok_to_continue_editing is False
    assert decision.requires_resynthesis is True
    assert decision.reason == "topology_restructure_detected"


def test_edit_boundary_too_many_retired_forces_resynthesis():
    prev = [_anchor(f"a{i}") for i in range(8)]
    cur = [_anchor("a0"), _anchor("a1")]
    report = AnchorUpdateReport(
        born=[],
        updated=["a0", "a1"],
        degraded=[],
        retired=[f"a{i}" for i in range(2, 8)],  # 6/8 retired = 0.75
        topology_change=TopologyChangeType.SUBTRACTIVE,
        novel_features_detected=0,
    )

    decision = evaluate_edit_boundary(prev_anchors=prev, cur_anchors=cur, update_report=report)
    assert decision.requires_resynthesis is True
    assert decision.reason == "too_many_anchors_retired"


def test_edit_boundary_low_confidence_forces_resynthesis():
    prev = [_anchor("a1", conf=1.0)]
    cur = [_anchor("a1", conf=0.1)]
    report = AnchorUpdateReport(
        born=[],
        updated=["a1"],
        degraded=[],
        retired=[],
        topology_change=TopologyChangeType.INCREMENTAL,
        novel_features_detected=0,
    )
    cfg = EditBoundaryConfig(min_mean_confidence=0.5)

    decision = evaluate_edit_boundary(prev_anchors=prev, cur_anchors=cur, update_report=report, config=cfg)
    assert decision.requires_resynthesis is True
    assert decision.reason == "anchor_confidence_too_low"


def test_edit_boundary_within_limits_allows_edit():
    prev = [_anchor("a1"), _anchor("a2"), _anchor("a3"), _anchor("a4")]
    cur = [_anchor("a1"), _anchor("a2"), _anchor("a3"), _anchor("a4")]
    report = AnchorUpdateReport(
        born=[],
        updated=["a1", "a2", "a3", "a4"],
        degraded=[],
        retired=[],
        topology_change=TopologyChangeType.INCREMENTAL,
        novel_features_detected=0,
    )

    decision = evaluate_edit_boundary(prev_anchors=prev, cur_anchors=cur, update_report=report)
    assert decision.ok_to_continue_editing is True
    assert decision.requires_resynthesis is False
    assert decision.reason == "within_edit_boundary"

