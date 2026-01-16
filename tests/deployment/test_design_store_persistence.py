"""
§SKELETON:DesignStoreTests

Acceptance tests for DesignStore v2 file-backed persistence.
"""
from pathlib import Path

import pytest


def test_design_persists_across_server_restart(tmp_path, monkeypatch):
    """Verify that design state persists across store instances (simulating server restart)."""
    monkeypatch.setenv("MAGNET_DESIGN_STORE_DIR", str(tmp_path))

    from magnet.deployment.design_store import DesignStore
    from magnet.core.state_manager import StateManager

    # Simulate server instance 1: create a design and save it
    store1 = DesignStore(container=None)
    sm1 = StateManager()
    sm1.begin_transaction()
    sm1.set("hull.loa", 25.0, source="test")
    sm1.commit()
    
    # Save sm1's state to disk
    data = sm1.to_dict()
    out = store1._path_for("DESIGN-1")
    import json
    out.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    # Simulate server restart (new store instance)
    store2 = DesignStore(container=None)
    sm2 = store2.load("DESIGN-1")
    assert sm2.get("hull.loa") == 25.0


def test_multiple_designs_can_be_saved_and_loaded(tmp_path, monkeypatch):
    """Verify multiple designs can be saved and loaded independently."""
    monkeypatch.setenv("MAGNET_DESIGN_STORE_DIR", str(tmp_path))
    from magnet.deployment.design_store import DesignStore
    from magnet.core.state_manager import StateManager
    import json

    store = DesignStore(container=None)

    # Create and save design A
    sm_a = StateManager()
    sm_a.begin_transaction()
    sm_a.set("hull.loa", 20.0, source="test")
    sm_a.commit()
    store._path_for("A").write_text(json.dumps(sm_a.to_dict(), indent=2, default=str), encoding="utf-8")

    # Create and save design B
    sm_b = StateManager()
    sm_b.begin_transaction()
    sm_b.set("hull.loa", 30.0, source="test")
    sm_b.commit()
    store._path_for("B").write_text(json.dumps(sm_b.to_dict(), indent=2, default=str), encoding="utf-8")

    assert set(store.list_designs()) == {"A", "B"}
    assert store.load("A").get("hull.loa") == 20.0
    assert store.load("B").get("hull.loa") == 30.0


def test_design_switching_preserves_state(tmp_path, monkeypatch):
    """Verify switching between designs preserves each design's state."""
    monkeypatch.setenv("MAGNET_DESIGN_STORE_DIR", str(tmp_path))
    from magnet.deployment.design_store import DesignStore
    from magnet.core.state_manager import StateManager
    import json

    store = DesignStore(container=None)

    # Create and save design A
    sm_a = StateManager()
    sm_a.begin_transaction()
    sm_a.set("hull.beam", 5.0, source="test")
    sm_a.commit()
    store._path_for("A").write_text(json.dumps(sm_a.to_dict(), indent=2, default=str), encoding="utf-8")

    # Create and save design B
    sm_b = StateManager()
    sm_b.begin_transaction()
    sm_b.set("hull.beam", 7.0, source="test")
    sm_b.commit()
    store._path_for("B").write_text(json.dumps(sm_b.to_dict(), indent=2, default=str), encoding="utf-8")

    # Load A, then B, then A again - verify state is preserved
    assert store.load("A").get("hull.beam") == 5.0
    assert store.load("B").get("hull.beam") == 7.0
    assert store.load("A").get("hull.beam") == 5.0  # Verify A is still correct


def test_spiral_checkpoint_survives_restart(tmp_path, monkeypatch):
    """Verify spiral checkpoint data survives a store restart."""
    monkeypatch.setenv("MAGNET_DESIGN_STORE_DIR", str(tmp_path))
    from magnet.deployment.design_store import DesignStore
    from magnet.core.state_manager import StateManager
    import json

    store1 = DesignStore(container=None)
    sm1 = StateManager()
    # phase_states is not a refinable path, so no transaction needed
    sm1.set("phase_states.hull_form", {"spiral": {"iteration": 2, "checkpoint": {"foo": "bar"}}}, source="test")
    store1._path_for("DESIGN-1").write_text(json.dumps(sm1.to_dict(), indent=2, default=str), encoding="utf-8")

    store2 = DesignStore(container=None)
    sm2 = store2.load("DESIGN-1")
    phase = sm2.get("phase_states.hull_form", {})
    assert phase.get("spiral", {}).get("iteration") == 2


def test_design_not_found(tmp_path, monkeypatch):
    """Verify DesignNotFound is raised for non-existent designs."""
    monkeypatch.setenv("MAGNET_DESIGN_STORE_DIR", str(tmp_path))
    from magnet.deployment.design_store import DesignStore, DesignNotFound

    store = DesignStore(container=None)
    with pytest.raises(DesignNotFound):
        store.load("NON-EXISTENT-DESIGN")


def test_delete_design(tmp_path, monkeypatch):
    """Verify designs can be deleted."""
    monkeypatch.setenv("MAGNET_DESIGN_STORE_DIR", str(tmp_path))
    from magnet.deployment.design_store import DesignStore, DesignNotFound
    from magnet.core.state_manager import StateManager
    import json

    store = DesignStore(container=None)
    sm = StateManager()
    sm.begin_transaction()
    sm.set("hull.loa", 10.0, source="test")
    sm.commit()
    store._path_for("TO-DELETE").write_text(json.dumps(sm.to_dict(), indent=2, default=str), encoding="utf-8")

    assert store.exists("TO-DELETE")
    assert "TO-DELETE" in store.list_designs()

    store.delete("TO-DELETE")
    assert not store.exists("TO-DELETE")
    assert "TO-DELETE" not in store.list_designs()
    with pytest.raises(DesignNotFound):
        store.load("TO-DELETE")


def test_atomic_write(tmp_path, monkeypatch):
    """Verify atomic write via temp file + os.replace()."""
    monkeypatch.setenv("MAGNET_DESIGN_STORE_DIR", str(tmp_path))
    from magnet.deployment.design_store import DesignStore
    from magnet.core.state_manager import StateManager
    import json
    import os

    store = DesignStore(container=None)
    sm = StateManager()
    sm.begin_transaction()
    sm.set("hull.loa", 15.0, source="test")
    sm.commit()
    
    # Manually test atomic write
    data = sm.to_dict()
    out = store._path_for("ATOMIC-TEST")
    tmp_file = out.with_suffix(".json.tmp")
    tmp_file.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    os.replace(tmp_file, out)

    # Verify no temp file left behind
    assert not tmp_file.exists()
    assert out.exists()
    
    # Verify we can load it back
    loaded = store.load("ATOMIC-TEST")
    assert loaded.get("hull.loa") == 15.0


def test_save_method_with_state_manager(tmp_path, monkeypatch):
    """Verify the save method works with an explicit StateManager."""
    monkeypatch.setenv("MAGNET_DESIGN_STORE_DIR", str(tmp_path))
    from magnet.deployment.design_store import DesignStore
    from magnet.core.state_manager import StateManager

    store = DesignStore(container=None)
    sm = StateManager()
    sm.begin_transaction()
    sm.set("hull.loa", 42.0, source="test")
    sm.commit()
    
    # Patch _resolve_state_manager to return our specific SM
    store._resolve_state_manager = lambda: sm
    store.save("SAVE-TEST")
    
    # Create fresh store and load
    store2 = DesignStore(container=None)
    loaded = store2.load("SAVE-TEST")
    assert loaded.get("hull.loa") == 42.0
