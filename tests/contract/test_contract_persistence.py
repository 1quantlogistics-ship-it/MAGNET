"""
TurnContract Vault: contract persistence survives save/load.
"""

from pathlib import Path

from magnet.core.dataclasses import TurnContract


def test_contract_persistence_roundtrip(tmp_path: Path):
    from magnet.deployment.design_store import DesignStore, DesignStoreConfig
    from magnet.core.state_manager import StateManager

    store = DesignStore(config=DesignStoreConfig(root_dir=tmp_path))

    sm = StateManager()
    sm.begin_transaction()
    sm.set("design_id", "D-PERSIST", "test")
    sm.set("geometry_intent.surface_definition", "panelized", "test")
    sm.commit()

    dv = int(sm.get("design_version", 0) or 0)

    c = TurnContract(
        contract_id="persist123",
        design_id="D-PERSIST",
        design_version=dv,
        state_snapshot_hash="h",
        intent_snapshot_hash="i",
        integrity_state="APPROXIMATE",
        primary_reason="missing_physics",
        violations=["no_physics"],
        timestamp_s=1.0,
    )
    sm.begin_transaction()
    sm.set("turn_contracts", [c], "test")
    sm.set("current_turn_contract_id", "persist123", "test")
    sm.commit()

    store.save("D-PERSIST", state_manager=sm)
    sm2 = store.load("D-PERSIST")

    contracts = sm2.get("turn_contracts", [])
    assert isinstance(contracts, list) and len(contracts) == 1
    assert getattr(contracts[0], "contract_id", None) == "persist123"
    assert sm2.get("current_turn_contract_id") == "persist123"

