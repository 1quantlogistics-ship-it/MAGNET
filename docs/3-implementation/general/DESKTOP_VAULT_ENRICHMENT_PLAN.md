### Tightened “Vault Enrichment” Plan (v0) — no semantic lies

This is the adjusted, implementation-ready plan that avoids receipts becoming relabeled heuristics and avoids adding new integrity policy layers.

---

### Non‑negotiables

- **Typed receipts**: no `dict` blobs as primary fields; only a single optional `details` escape hatch.
- **Single timestamp authority**: phase timestamps are stamped in **one place** (Conductor) and **never** enter deterministic hashes.
- **Deterministic hashes**: snapshot/intent hashes must exclude receipts, timestamps, history, and other volatile fields.
- **Integrity policy unchanged**: `AUTHORITATIVE` gating stays “contract + stamps + existing ladder reasons”; confidence is record‑only.
- **Scene vs phase separation**: scene checks (mesh parity) are **SceneReceipt**, never misrepresented as phase guarantees.

---

### v0 definitions (locked now; escape hatch later)

#### “Dihedral” naming
v0 is **not** 3D dihedral. Use:
- `section_crease_angle_deg_*`
- `crease_jump_deg_per_m_*`
Reserve “dihedral” for future mesh-derived metrics (v1).

#### Hard-edge track identity
Hard-edge “index k” is **not stable** under harmonization unless tracked explicitly.

v0 decision:
- **Preferred**: add and propagate `hard_anchor_id` for `EdgeType.HARD` vertices through compilation/harmonization.
- **Fallback** (only if needed): nearest-neighbor matching in y–z with tolerance + match confidence and coverage.

#### Jump definition (v0)
Measured along x between adjacent sections:
- For each body, for each persistent hard track:
  - compute `section_crease_angle_deg` at section i and i+1
  - `jump = |Δangle| / Δx` in deg/m
Aggregate p50/p95/max and report **coverage**.

#### Minimum sample semantics
If `samples_count < N` (v0 N=20):
- set `metrics_valid=false` and `metrics_confidence="low"` (still record values, but mark as low confidence).

---

### Strict implementation order (to avoid churn)

#### Step 1 — Lock data models + hashing rules (no business logic changes)
- Add typed dataclasses:
  - `PhaseReceipt`
  - `ValidatorReceipt`
  - `SceneReceipt`
  - (optional) `IntegrityInputs` typed block
- Add tests:
  - receipts serialize stably
  - deterministic hashes exclude receipts/timestamps

#### Step 2 — Wire receipts end-to-end with trivial content (prove plumbing)
- TurnContract:
  - phase id/status + stamped times + stamps present + list of validator ids/states (no metrics yet)
- SceneReceipt:
  - volume parity fields already computed in `GeometryService.get_scene()`
  - attach to `SceneData.metadata.scene_receipt`
- UI shows Turn vs Scene receipts distinctly (no new toggles/policy)

#### Step 3 — Buildability proxy validator (only after stable HARD identity exists)
- Implement `section_crease_angle_deg` + `crease_jump_deg_per_m` with coverage and min-sample semantics.
- Store metrics in TurnContract receipts (not as integrity policy).

#### Step 4 — Confidence scalar + envelope distance (record-only)
- Derive from existing `method_valid` / unmodeled flags.
- Explicit tests ensure integrity decisions never read confidence_scalar.

---

### Acceptance criteria (v0)
- TurnContract receipts are typed and persisted.
- SceneReceipt is separate and never confused with phase guarantees.
- Deterministic hashes are stable across environments and exclude receipts/timestamps.
- Existing integrity ladder behavior is unchanged (only richer inspectability added).

