### Goal
Make MAGNET **un-lie-able** by introducing a first-class **Turn Contract (Receipt) ledger** that gates `AUTHORITATIVE` and makes integrity transitions replayable, testable, and environment-stable.

This plan is “control-block/contract first” and intentionally de-prioritizes UI polish until the ledger is correct.

---

### Design principles (non-negotiable)

- **Cynical by default**: if the current version is not covered by a signed TurnContract, the system must not report `AUTHORITATIVE`.
- **Deterministic across environments**: contract hashes must not depend on timestamps, process IDs, or machine state.
- **No side effects on read**: `get_scene()` must not create/sign contracts; contracts are signed only during write/phase execution flows.
- **Single source of truth**:
  - Control intent must be explicit (e.g., `MissingSurfaceIntentError` stays fail-closed).
  - Multi-body centerlines must not be inferred per-section at render time; use explicit metadata (`body_centerline_y_by_body`).

---

### Scope for this implementation

We are implementing:

1) A persisted **TurnContract ledger** stored in `DesignState` (append-only).
2) A deterministic **state snapshot hash** for contracts.
3) A **gating rule**: `AUTHORITATIVE` is allowed **iff** same-version contract exists, has no violations, and required stamps exist.
4) Contract summaries surfaced in WebGL `SceneData` (thin payload only).
5) Tests proving:
   - `AUTHORITATIVE` requires contract
   - version mismatch decouples
   - persistence survives save/load

We are *not* implementing a full UI contract viewer yet.

---

### Data model

#### `TurnContract` (core persisted artifact)
Stored in `DesignState` as an append-only list.

Minimum fields:
- `contract_id: str` (stable id, e.g., short uuid)
- `design_id: str`
- `design_version: int`
- `state_snapshot_hash: str` (deterministic hash of a stable snapshot)
- `intent_snapshot_hash: str` (hash of explicit control intent only)
- `integrity_state: str` (AUTHORITATIVE | APPROXIMATE | DECOUPLED)
- `primary_reason: Optional[str]` (stable reason taxonomy)
- `violations: List[str]` (structured later; initially stable strings)
- `phases_ran: List[str]` (which phase produced this contract)
- `timestamp_s: float`

#### Thin UI/scene bridge
`SceneData.metadata.contract_summary` (or a dedicated field later):
- `contract_id`
- `integrity_state`
- `primary_reason`
- `design_version`

---

### Signing lifecycle (adjusted to avoid “contract on every trivial commit”)

#### On every commit (`StateManager.commit_transaction`)
- Increment `design_version` (already happens)
- **Invalidate** current contract pointer:
  - `current_turn_contract_id = None`
  - `simulation_integrity` becomes **DECOUPLED** (or APPROXIMATE for smooth) until a phase run signs a new contract.
- Do not create a TurnContract here (avoid ledger spam for trivial UI writes).

#### On phase completion (`Conductor.run_phase`)
- After phase run/validation completes, compute:
  - deterministic hashes
  - required stamps presence (physics/hydrostatics freshness)
  - integrity state + reason + violations
- Append a new TurnContract for the *current* `design_version`
- Set `current_turn_contract_id` to the new contract id
- Mirror integrity + reason into state for backwards compatibility (existing UI/scene consumers)

---

### Integrity gating rule (Golden Rule)

`current_version` is `AUTHORITATIVE` **iff**:
- A TurnContract exists for current `design_version`, and
- `violations == []`, and
- required stamps are present:
  - at minimum: `kernel.physics_last_validated_version == design_version`
  - and for `panelized`: `kernel.hydrostatics_last_validated_version == design_version`

Otherwise:
- `panelized` missing/stale hydrostatics ⇒ **DECOUPLED** with `missing_hydrostatics_for_panelized`
- missing contract ⇒ **APPROXIMATE** (or **DECOUPLED** for `panelized`) with `missing_contract`
- stale contract/version mismatch ⇒ **DECOUPLED** with `stale_contract`

---

### Deterministic hashing

Add a stable snapshot function that removes volatile fields such as:
- `history`
- timestamps (`*_at`, `generated_at`, etc.)
- transient metadata keys like `_last_commit_written_paths`

Hash using canonical JSON:
- `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)`
- then `sha256`

---

### Tests (must be green before UI work)

Add tests:
- `test_authoritative_requires_contract`: stamps present but no contract => not AUTHORITATIVE
- `test_version_mismatch_decouples`: contract exists for vN but state is vN+1 => DECOUPLED
- `test_contract_persistence`: save/load via DesignStore preserves contract and pointer

---

### Implementation steps

1) Add `TurnContract` + contract pointer fields to state dataclasses and ensure `to_dict/from_dict` work.
2) Add deterministic snapshot hashing helper.
3) Add contract creation/signing helper callable from Conductor.
4) Update `GeometryService.get_scene()` to gate AUTHORITATIVE based on contract presence (read-only).
5) Add tests and iterate until all contract + torture suites pass.

