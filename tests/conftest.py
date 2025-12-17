"""
MAGNET Test Configuration and Fixtures

Module 62.4: Provides transaction context for tests writing refinable paths.
"""

import pytest
from contextlib import contextmanager
from typing import Generator, TYPE_CHECKING

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


@contextmanager
def refinable_write_context(state_manager: "StateManager") -> Generator["StateManager", None, None]:
    """
    Context manager for writing refinable paths in tests.

    Module 62.4: Wraps refinable path writes in a transaction to satisfy
    enforcement without using the full ActionPlan pipeline.

    Usage:
        with refinable_write_context(sm) as sm:
            sm.set("hull.loa", 25.0, "test")
            sm.set("mission.max_speed_kts", 30.0, "test")

    Args:
        state_manager: StateManager instance

    Yields:
        The same state_manager for chaining
    """
    state_manager.begin_transaction()
    try:
        yield state_manager
        state_manager.commit()
    except Exception:
        state_manager.rollback()
        raise


@pytest.fixture
def state_manager_with_mission():
    """StateManager pre-populated with mission data."""
    from magnet.core.state_manager import StateManager
    from magnet.core.design_state import DesignState

    sm = StateManager(DesignState())

    with refinable_write_context(sm):
        sm.set("mission.vessel_type", "patrol", "test/fixture")
        sm.set("mission.max_speed_kts", 30.0, "test/fixture")
        sm.set("mission.range_nm", 500.0, "test/fixture")
        sm.set("mission.crew_berthed", 6, "test/fixture")

    return sm


@pytest.fixture
def state_manager_with_hull():
    """StateManager pre-populated with hull data."""
    from magnet.core.state_manager import StateManager
    from magnet.core.design_state import DesignState

    sm = StateManager(DesignState())

    with refinable_write_context(sm):
        sm.set("mission.vessel_type", "patrol", "test/fixture")
        sm.set("hull.loa", 25.0, "test/fixture")
        sm.set("hull.lwl", 23.0, "test/fixture")
        sm.set("hull.beam", 6.0, "test/fixture")
        sm.set("hull.draft", 1.5, "test/fixture")
        sm.set("hull.depth", 3.0, "test/fixture")
        sm.set("hull.cb", 0.45, "test/fixture")

    return sm
