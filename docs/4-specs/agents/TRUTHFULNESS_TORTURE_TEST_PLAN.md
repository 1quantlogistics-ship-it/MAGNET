### Context: what’s happening right now (and why this is risky)

We’re transitioning MAGNET from “construction” to “defensive engineering.” The previous Phase 1–3 work made the system capable of producing **AUTHORITATIVE** outputs, but the dangerous failure mode is *quietly drifting into wrong-but-confident behavior*.

To address that, the current branch has started implementing **negative-path enforcement** so the system fails loudly and flips the **Simulation Integrity** signal when inputs are out-of-bounds or when physics is stale relative to geometry.

However: these defensive changes are currently **partially implemented** (some enforcement exists, but the torture tests that prove it are not yet in place). Before proceeding further, we need to stabilize the failure semantics and pin them down with tests.

---

### What has already been changed (current partial state)

- **No more silent surface intent defaults**
  - `magnet/kernel/stdlib/compiler.py` now raises `MissingSurfaceIntentError` if `surface_definition` is missing, instead of defaulting to `"smooth"`.
  - This is intentional: defaulting changes integration/tessellation and creates silent truth drift.

- **Physics freshness stamping**
  - `magnet/core/dataclasses.py` adds:
    - `kernel.physics_last_validated_version`
    - `kernel.physics_last_validated_at`
  - `magnet/physics/validators.py` now stamps these fields from `design_version` after hydrostatics and resistance validations succeed.

- **Scene integrity can flip to DECOUPLED**
  - `magnet/webgl/geometry_service.py` now compares:
    - `design_version` vs `kernel.physics_last_validated_version`
  - If physics is missing => `APPROXIMATE`
  - If physics version != current design version => `DECOUPLED`

- **Planarity failure is enforced as fail-closed in scene generation (panelized only)**
  - `magnet/webgl/geometry_service.py` performs a planarity warp check when `surface_definition == "panelized"`.
  - If warp exceeds threshold, it raises `PlanarityGateError` and scene generation fails (no mesh emitted).

---

### Why we must pause now

These are “contract-level” behavior changes:

- **Missing intent now raises** instead of defaulting.
- **Scene truthfulness can downgrade** to `DECOUPLED` based on version mismatch.
- **Planarity can hard-block rendering.**

If we continue refactoring without tests, we risk:

- Breaking legacy flows that previously relied on defaults.
- Creating inconsistent integrity behavior between validators and webgl scene generation.
- Shipping a UI badge that looks “correct” but isn’t reliably tied to backend invariants.

So the next step must be to add the torture harness tests first, then iterate until they pass.

---

### Plan (lock negative-path verification before proceeding)

#### 1) Stabilize “Missing Intent” as a first-class contract

- **Goal**: any missing `surface_definition` must raise `MissingSurfaceIntentError` (never default).
- **Work**
  - Ensure all internal producers of `geometry.surface` set `surface_definition` explicitly.
  - Audit any test fixtures / legacy payloads that relied on the default.
- **Test**
  - `tests/invariants/test_integrity_flip.py::test_missing_intent_raises` (new)

#### 2) Make DECOUPLED deterministic and immediate (the “Dirty Geometry” test)

- **Goal**: if geometry changes but physics isn’t recomputed, **scene integrity becomes DECOUPLED**.
- **Mechanism**
  - Geometry edits advance `design_version` (via `StateManager.commit()`).
  - Physics validators stamp `kernel.physics_last_validated_version`.
  - Scene compares them and flips integrity if stale.
- **Test**
  - `tests/invariants/test_integrity_flip.py::test_dirty_geometry_decoupled` (new)

#### 3) Prove APPROXIMATE on physics out-of-envelope (Savitsky OOB)

- **Goal**: if Savitsky is out-of-bounds (e.g., deadrise 45°, Fn_b 0.9), the system must **not** claim AUTHORITATIVE.
- **Preferred truth signal**
  - `resistance.method_valid == False` (or `resistance.outside_envelope == True`) drives integrity downgrade.
  - Scene should downgrade to `APPROXIMATE` when physics flags invalidity.
- **Test**
  - `tests/invariants/test_integrity_flip.py::test_savitsky_oob_approximate` (new)

#### 4) Add station-spacing risk warning (numerical integration honesty)

- **Goal**: if station spacing variation RMS > 0.2, emit an `IntegrationRiskWarning` (or at least a warning string) so users know trapezoid assumptions are at risk.
- **Implementation**
  - Add station spacing metrics in `magnet/physics/geometry_hydrostatics.py` where `xs` are assembled.
  - Compute a normalized RMS variation and append warning to `HydrostaticsResult.warnings`.
- **Test**
  - Extend/introduce a regression test that creates non-uniform spacing and asserts warning is present.

#### 5) Feature anchor preservation audit (HARD edge indices)

- **Goal**: global harmonization must not “renumber” chines for panelized surfaces.
- **Work**
  - If harmonization currently “snaps” hard vertices to nearest available indices, that can shift indices.
  - Adjust harmonization strategy to preserve HARD vertex indices exactly (or introduce a stable anchor mapping).
- **Test**
  - `tests/kernel/test_feature_anchors.py` (new)

#### 6) Planarity gate must block rendering (explicit)

- **Goal**: planarity violations must prevent `get_scene()` from returning a mesh when `allow_visual_only=False`.
- **Test**
  - `tests/kernel/test_planarity_gate.py` (new) or `tests/webgl/test_geometry_service_planarity_gate.py` (new)

#### 7) Lock “no visual-only fallback” for DEV and PROD

- **Goal**: `allow_visual_only` default must be `False` for DEV and PROD tiers; system must never render what it cannot validate.
- **Work**
  - Update `magnet/webgl/config.py` to enforce this and add a test that asserts config values.

---

### Deliverables checklist (must land together)

- **New tests**
  - `tests/invariants/test_integrity_flip.py`
  - `tests/kernel/test_feature_anchors.py`
  - `tests/kernel/test_planarity_gate.py`
- **Core fixes if tests fail**
  - Harmonizer HARD-edge anchor preservation in `magnet/kernel/synthesis.py`
  - Station spacing warning in `magnet/physics/geometry_hydrostatics.py`
  - Config lock in `magnet/webgl/config.py`
- **Proof**
  - A planarity violation raises and blocks `GeometryService.get_scene()` (no mesh returned) when `allow_visual_only=False`.

---

### Immediate next action (after this plan is approved)

Implement the three test files first (as failing tests), then iterate the kernel/physics/webgl code until they pass. No additional refactors until these negative-path tests are green.

