import pytest

from magnet.core.design_state import DesignState
from magnet.core.state_manager import StateManager, MutationEnforcementError


def test_design_state_top_level_write_is_locked_without_mutator_context():
    ds = DesignState()
    with pytest.raises(RuntimeError):
        ds.design_name = "illegal"


def test_design_state_allows_top_level_write_in_mutator_context():
    ds = DesignState()
    with ds.mutator_context():
        ds.design_name = "ok"
    assert ds.design_name == "ok"


def test_refinable_paths_still_require_state_manager_transaction():
    sm = StateManager(DesignState())
    with pytest.raises(MutationEnforcementError):
        sm.set("hull.loa", 30.0, "test")
