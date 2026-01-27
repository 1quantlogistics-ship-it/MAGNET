from magnet.core.design_mutator import DesignMutator
from magnet.core.state_manager import StateManager


def test_design_mutator_stages_and_commits_patch_atomically():
    sm = StateManager()
    mut = DesignMutator(sm)

    v0 = int(sm.get("design_version", 0) or 0)
    mut.stage_patch({"hull.loa": 20.0, "hull.beam": 5.0}, source="test")
    res = mut.commit(expected_version=v0)

    assert res.success is True
    assert res.design_version == v0 + 1
    assert sm.get("hull.loa") == 20.0
    assert sm.get("hull.beam") == 5.0
    assert "hull.loa" in res.written_paths
    assert "hull.beam" in res.written_paths


def test_design_mutator_rejects_stale_expected_version():
    sm = StateManager()
    mut = DesignMutator(sm)

    v0 = int(sm.get("design_version", 0) or 0)
    mut.stage_patch({"hull.loa": 20.0}, source="test")
    res1 = mut.commit(expected_version=v0)
    assert res1.success is True

    mut.stage_patch({"hull.loa": 21.0}, source="test")
    res2 = mut.commit(expected_version=v0)
    assert res2.success is False
    assert res2.error and "stale_write" in res2.error

