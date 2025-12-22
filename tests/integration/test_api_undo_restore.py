"""
Integration-style test for undo/restore behavior via StateManager snapshots.
"""

from magnet.core.state_manager import StateManager
from magnet.core.design_state import DesignState


def test_undo_restore_round_trip():
    sm = StateManager(DesignState())

    # Apply a change via transaction/commit
    sm.begin_transaction()
    sm.set("mission.vessel_type", "ferry", source="test")
    sm.commit()
    version_after_apply = sm.design_version

    # Undo to previous version
    assert sm.revert_to_version(version_after_apply - 1) is True
    assert sm.design_version == version_after_apply - 1
    assert sm.get("mission.vessel_type") is None

    # Restore to the applied version
    assert sm.revert_to_version(version_after_apply) is True
    assert sm.design_version == version_after_apply
    assert sm.get("mission.vessel_type") == "ferry"

