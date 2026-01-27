from magnet.kernel.topology_classifier import TopologyChangeType, classify_topology_change


def test_topology_classifier_incremental_when_low_churn():
    cls = classify_topology_change(
        prev_count=20,
        cur_count=20,
        born_count=1,
        retired_count=0,
        degraded_count=0,
        restructure_churn_ratio=0.9,  # make restructure very unlikely
    )
    assert cls.change_type in (TopologyChangeType.INCREMENTAL, TopologyChangeType.ADDITIVE)


def test_topology_classifier_additive_when_only_born():
    cls = classify_topology_change(
        prev_count=20,
        cur_count=25,
        born_count=5,
        retired_count=0,
        degraded_count=0,
    )
    assert cls.change_type == TopologyChangeType.ADDITIVE


def test_topology_classifier_subtractive_when_only_retired():
    cls = classify_topology_change(
        prev_count=20,
        cur_count=15,
        born_count=0,
        retired_count=5,
        degraded_count=0,
    )
    assert cls.change_type == TopologyChangeType.SUBTRACTIVE


def test_topology_classifier_restructure_when_mixed_churn():
    cls = classify_topology_change(
        prev_count=20,
        cur_count=20,
        born_count=6,
        retired_count=6,
        degraded_count=0,
        minor_restructure_floor=0.1,
    )
    assert cls.change_type == TopologyChangeType.RESTRUCTURE

