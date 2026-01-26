"""
Thinking pass receipt persistence:

When a thinking pass is present in state at phase-run time, the Conductor should
attach a hash + summary (and optionally bounded raw payload) into TurnContract.phase_receipt.details,
and this should survive DesignStore save/load.
"""

from pathlib import Path


def test_thinking_pass_receipt_persists(tmp_path: Path):
    from magnet.core.state_manager import StateManager
    from magnet.deployment.design_store import DesignStore, DesignStoreConfig
    from magnet.kernel.conductor import Conductor

    sm = StateManager()
    sm.begin_transaction()
    sm.set("design_id", "D-THINKING", "test")
    sm.set("hull.lwl", 20.0, "test")
    sm.set("hull.beam", 6.0, "test")
    sm.set("hull.draft", 1.5, "test")
    sm.set("hull.cb", 0.45, "test")
    sm.set("geometry_intent.surface_definition", "smooth", "test")
    sm.set(
        "metadata.vessel_thinking_pass",
        {
            "station_plan": {"count": 7, "distribution": "uniform", "explicit_xs": None, "rationale": "x"},
            "dof_schema": [],
            "verification_schema": [],
            "closure_proof": [],
        },
        "test",
    )
    sm.set("metadata.vessel_thinking_pass_hash", "hash123", "test")
    sm.commit()

    # Run a phase with no required inputs/outputs to trigger TurnContract signing.
    conductor = Conductor(state_manager=sm)
    conductor.run_phase("propulsion")

    # Persist and reload
    store = DesignStore(config=DesignStoreConfig(root_dir=tmp_path))
    store.save("D-THINKING", state_manager=sm)
    sm2 = store.load("D-THINKING")

    contracts = sm2.get("turn_contracts", []) or []
    assert isinstance(contracts, list) and contracts, "Expected at least one TurnContract"
    tc = contracts[-1]
    pr = getattr(tc, "phase_receipt", None)
    assert pr is not None
    details = getattr(pr, "details", {}) or {}
    assert details.get("vessel_thinking_pass_hash") == "hash123"
    assert "vessel_thinking_pass_summary" in details

