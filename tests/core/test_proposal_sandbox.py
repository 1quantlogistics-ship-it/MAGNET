from magnet.core.proposal_sandbox import ProposalSandbox
from magnet.core.design_mutator import StagedMutation
from magnet.core.state_manager import StateManager


def test_proposal_sandbox_does_not_mutate_canonical_and_returns_diff():
    sm = StateManager()
    sandbox = ProposalSandbox(state_manager=sm)

    v0 = int(sm.get("design_version", 0) or 0)
    assert sm.get("hull.loa") is None

    prop = sandbox.propose(StagedMutation(kind="patch", payload={"hull.loa": 20.0}, source="test"))
    assert prop.success is True
    assert "hull.loa" in prop.diff

    # Canonical remains unchanged
    assert sm.get("hull.loa") is None
    assert int(sm.get("design_version", 0) or 0) == v0


def test_proposal_sandbox_apply_requires_approval():
    sm = StateManager()
    sandbox = ProposalSandbox(state_manager=sm)

    mut = StagedMutation(kind="patch", payload={"hull.loa": 21.0}, source="test")
    res = sandbox.apply_if_approved(mut, approved=False)
    assert res.success is False
    assert sm.get("hull.loa") is None

    res2 = sandbox.apply_if_approved(mut, approved=True)
    assert res2.success is True
    assert sm.get("hull.loa") == 21.0

