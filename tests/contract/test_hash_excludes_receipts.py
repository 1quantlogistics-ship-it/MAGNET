from magnet.core.turn_contracts import stable_state_snapshot_for_hash, sha256_hex


def test_hash_excludes_receipts_and_timestamps():
    """
    Deterministic hash must exclude:
    - turn_contracts / current_turn_contract_id
    - history / created_at / updated_at
    - any future scene_receipts
    """
    state = {
        "design_id": "D",
        "design_version": 3,
        "created_at": "t0",
        "updated_at": "t1",
        "history": [{"x": 1}],
        "current_turn_contract_id": "c1",
        "turn_contracts": [{"contract_id": "c1", "timestamp_s": 999.0}],
        "scene_receipts": [{"scene_receipt_id": "s1", "timestamp_s": 999.0}],
        "metadata": {"generated_at": "t2", "_last_commit_written_paths": ["x"]},
        "kernel": {"physics_last_validated_at": "t3"},
        "geometry_intent": {"surface_definition": "panelized"},
    }

    snap = stable_state_snapshot_for_hash(state)
    h1 = sha256_hex(snap)

    # Mutate only volatile fields; hash should remain identical.
    state2 = dict(state)
    state2["created_at"] = "different"
    state2["updated_at"] = "different"
    state2["history"] = [{"x": 2}]
    state2["turn_contracts"] = [{"contract_id": "c1", "timestamp_s": 123.0}]
    state2["scene_receipts"] = [{"scene_receipt_id": "s1", "timestamp_s": 123.0}]
    state2["metadata"] = {"generated_at": "zzz", "_last_commit_written_paths": ["y"]}
    state2["kernel"] = {"physics_last_validated_at": "zzz"}

    snap2 = stable_state_snapshot_for_hash(state2)
    h2 = sha256_hex(snap2)

    assert h1 == h2

