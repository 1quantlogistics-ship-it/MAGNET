"""
Turn Contract utilities (Vault).

Deterministic snapshot hashing + contract creation helpers.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from magnet.core.dataclasses import IntegrityInputs, PhaseReceipt, TurnContract, ValidatorReceipt


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def sha256_hex(obj: Any) -> str:
    return hashlib.sha256(_stable_json(obj).encode("utf-8")).hexdigest()


def stable_state_snapshot_for_hash(state_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a stable snapshot suitable for hashing across environments.

    Removes volatile fields (timestamps, history, current contract pointers, etc.).
    """
    s = dict(state_dict or {})

    # Remove mutation log / volatile timeline fields
    s.pop("history", None)
    s.pop("created_at", None)
    s.pop("updated_at", None)

    # Remove the contract ledger itself (avoid self-reference)
    s.pop("turn_contracts", None)
    s.pop("current_turn_contract_id", None)
    # Scene receipts (if persisted later) must never enter deterministic hashes
    s.pop("scene_receipts", None)

    # Remove volatile metadata keys
    meta = s.get("metadata")
    if isinstance(meta, dict):
        meta = dict(meta)
        meta.pop("_last_commit_written_paths", None)
        meta.pop("generated_at", None)
        meta.pop("simulation_integrity_reason", None)
        # Thinking-pass artifacts must never enter deterministic hashes.
        meta.pop("vessel_thinking_pass", None)
        meta.pop("vessel_thinking_pass_hash", None)
        s["metadata"] = meta

    # Kernel state often contains volatile timestamps; keep structural fields only.
    kernel = s.get("kernel")
    if isinstance(kernel, dict):
        k = dict(kernel)
        for kf in [
            "started_at",
            "last_activity",
            "physics_last_validated_at",
            "hydrostatics_last_validated_at",
        ]:
            k.pop(kf, None)
        s["kernel"] = k

    return s


def intent_snapshot_for_hash(state_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Intent snapshot is derived only from explicit control intent (not derived geometry).
    """
    gi = (state_dict or {}).get("geometry_intent") or {}
    if not isinstance(gi, dict):
        gi = {}
    return {
        "surface_definition": gi.get("surface_definition"),
    }


def make_turn_contract(
    *,
    design_id: str,
    design_version: int,
    state_dict: Dict[str, Any],
    phase_receipt: Optional[PhaseReceipt],
    validator_receipts: Optional[List[ValidatorReceipt]],
    integrity_inputs: Optional[IntegrityInputs],
    integrity_state: str,
    primary_reason: Optional[str],
    violations: Optional[List[str]] = None,
) -> TurnContract:
    snap = stable_state_snapshot_for_hash(state_dict)
    intent = intent_snapshot_for_hash(state_dict)
    return TurnContract(
        schema_version="1.0",
        contract_id=str(uuid.uuid4().hex[:12]),
        design_id=str(design_id),
        design_version=int(design_version),
        state_snapshot_hash=sha256_hex(snap),
        intent_snapshot_hash=sha256_hex(intent),
        integrity_state=str(integrity_state),
        primary_reason=primary_reason,
        violations=list(violations or []),
        phase_receipt=phase_receipt,
        validator_receipts=list(validator_receipts or []),
        integrity_inputs=integrity_inputs,
        timestamp_s=float(time.time()),
    )

