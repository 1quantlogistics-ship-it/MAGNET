# MAGNET Geometry Truthfulness Implementation Fix Guide

This guide converts the audit + external technical review into a concrete, implementable fix plan.

It is written to preserve MAGNET’s non‑negotiables:
- **No hull-type “if Viking then…” enums/switches** in the geometry authority path.
- **Multi-hull only via `body_count` and multiple bodies** (already geometry-derived).
- **“Style” must be expressible as geometry/metrics/constraints**, not presets.
- **Truthfulness over aesthetics**: the system must not silently return plausible geometry/physics when they diverge.

---

## Problem statement (what we must fix)

MAGNET can generate and render both smooth and hard-edge hulls, but today it can still:
- **Visually satisfy** a “Viking” / “Metal Shark” request while **physics is blind** to the critical features.
- **Smooth away or reinterpret** high-frequency geometric features via resampling/densification.
- **Show geometry even when authoritative/validated geometry is unavailable**, due to visual-only fallbacks.

Key technical traps identified:

1) **Physics Blindness Trap (critical)**
- Planing physics via Savitsky uses only coarse inputs (`beam_m`, `deadrise_deg`, `displacement_kg`, `lcg_from_transom_m`) and does **not** account for spray rails / strakes / chine sharpness as inputs.
- Evidence:
  - `magnet/physics/savitsky.py: SavitskyInputs`
  - `magnet/physics/validators.py: ResistanceValidator.validate` constructs `SavitskyInputs(...)` using `beam` + `hull.deadrise_deg` (and not feature geometry)

2) **Visual vs Physics Volume Discrepancy (high risk for faceted mode)**
- Visual faceted tessellation uses planar quads between sections (`_tessellate_faceted`), but physics hydrostatics integrates from section polygons using Simpson/trapezoid rules.
- Evidence:
  - Faceted tessellation exists: `magnet/webgl/geometry_pipeline.py: HullGeometryPipeline.tessellate_with_options/_tessellate_faceted`
  - Authoritative path currently uses smooth tessellation: `magnet/webgl/geometry_service.py: GeometryService._tessellate_grm` calls `pipeline.tessellate()`
  - Section-based integration uses Simpson where possible else trapezoid: `magnet/physics/geometry_hydrostatics.py` (see comments in the integration helpers; grep shows Simpson/trapezoid behavior)

3) **No planarity validator (patrol craft aesthetic + reflection correctness)**
- We need an explicit planarity residual metric for “flat plate” expectations.
- Evidence:
  - No planarity/dihedral validator exists (repo search); quality gates are advisory only: `magnet/kernel/stdlib/quality_gates.py`

4) **Resampling is a low-pass filter (signal-to-noise risk)**
- Multiple steps can smooth away sharp features:
  - Agent normalization resamples sections to a minimum point count: `magnet/agents/geometry_proposer.py: GeometryProposer._normalize_section_points`
  - Agent inserts intermediate sections by interpolation: `magnet/agents/geometry_proposer.py: GeometryProposer._ensure_min_loft_sections`
  - Compiler upscales low-res sections (default_32): `magnet/kernel/stdlib/section_compiler.py: _compile_polygon_section`
  - WebGL pipeline densifies along length: `magnet/webgl/geometry_pipeline.py: HullGeometryPipeline._densify_sections_linear`

5) **UI truthfulness gap (“allow_visual_only” lie)**
- UI requests `allow_visual_only=true` for scenes, so it can show a hull even when authoritative geometry is unavailable.
- Evidence:
  - UI: `magnet/ui_v2/js/scene-manager.js: SceneManager._loadAndRenderPrimitives`
  - Backend behavior: `magnet/webgl/geometry_service.py: GeometryService.get_hull_geometry`
  - Schema only has `GeometryMode.AUTHORITATIVE` vs `VISUAL_ONLY`: `magnet/webgl/schema.py: GeometryMode`

---

## Implementation roadmap (RE-SEQUENCED to protect the North Star)

This roadmap is intentionally re-ordered so we do **kernel correctness first**. Shipping UI badges before topology + physics-threading is in place is “window dressing” and risks months of debugging.

### ARCHITECTURAL PIVOT (GREENFIELD): Strict Compliance Enforcement

We are abandoning backward-compatibility and “soft” defaults. In strict compliance mode:
- `surface_definition` is **mandatory** (schema lock).
- `panelized` implies **strict topological harmonization** (linear only; no mismatched vertex counts).
- `panelized` physics uses **trapezoidal integration**; `lofted` physics uses **Simpson integration** (hard-coupled invariant).
- Planarity is a **hard gate** (manufacturing enforcement), not advisory.

### Phase 1 (Kernel): Enforce required intent + topology (must be first)

**Goal:** Prevent mesh crashes and “two displacements” inconsistencies.

1) **Mandatory surface intent (schema lock)** — every design thread must explicitly declare `surface_definition: "lofted"|"panelized"` (Fix 3)
2) **Global topological harmonization (panelized)** — linear upsample to a single vertex count across all sections; reject mismatches (Fix 5)
3) **Direct physics-geometry coupling (integration invariant)** — ensure `panelized⇒trapezoid`, `lofted⇒Simpson` is enforced at the HullState level (Fix 3)

### Phase 2 (Audit/Validators): Enforceable truth metrics (must be second)

**Goal:** Make “faceted” and “planing” truthfully enforceable.

4) **Hard-gate Planarity (manufacturing)** — normalized warp factor gate + dihedral constraints (Fix 4)
5) **Savitsky domain check → integrity downgrade** (Fix 2 + integrity)
6) **Feature→physics blindness warnings** (rails/chines not modeled) (Fix 2A)
7) Wire the regression harness (faceted + Viking feature cases) into CI

### Phase 3 (UI): Surface truth (only after kernel + validators exist)

**Goal:** Show users the *real* truth state (not guesses).

8) Add **Simulation Integrity** tri-state and surface it in UI + API (Fix 1)
9) Surface `TransformReport` directly under the integrity badge (Fix 1)
10) In dev, default `allow_visual_only=false` and require an explicit user toggle to enable it

---

## Fix 1 — Simulation Integrity tri-state (UI + backend)

### Desired behavior

Replace the current “binary” truth signal with a tri-state:

1. **AUTHORITATIVE**: Visual mesh is derived from the same authoritative GRM used for physics, and physics is up-to-date.
2. **APPROXIMATE**: Visual is parametric/visual-only OR physics not yet run, but the system is explicit about it.
3. **DECOUPLED**: Visual and physics disagree (e.g., faceted visual + section-physics assumptions, or visual-only used while showing “validated” numbers).

### Extend integrity to include “physics domain validity” (not just geometry coupling)

**Operational requirement:** even when geometry is authoritative and physics is up-to-date, the result can still be **mathematical fiction** if the hull lies outside the validity envelope of the selected empirical method (Savitsky/Holtrop).

Concrete signals already exist:
- Savitsky reports `method_valid` + `validity_note` + warnings: `magnet/physics/savitsky.py: SavitskyResults`
- Resistance pipeline propagates `resistance.method_valid` + `resistance.validity_note`: `magnet/physics/validators.py: ResistanceValidator.validate`

**Critical contract change:** physics-domain violations must **downgrade integrity**, not just add a side note.

Recommended mapping (minimum viable):
- If `resistance.method_valid == false` (Savitsky/Holtrop out of validity range) → **Simulation Integrity becomes**:
  - `APPROXIMATE (Out of Bounds)`
- If resistance not computed → `APPROXIMATE (Unvalidated)`
- Else → keep existing coupling-based state (AUTHORITATIVE/DECOUPLED) as appropriate

Rationale:
- “Geometry matches physics inputs” is not sufficient if the physics method is out-of-domain. In that case, results are **mathematical fiction** and must not be labeled AUTHORITATIVE.

### Where to implement

- **Schema**:
  - Today: `magnet/webgl/schema.py: GeometryMode` (`AUTHORITATIVE` / `VISUAL_ONLY`)
  - Recommendation: add a *separate* field (avoid breaking `GeometryMode` contract) such as `simulation_integrity` in `SceneData.metadata`.
- **Backend computation**:
  - `magnet/webgl/geometry_service.py: GeometryService.get_scene`
    - Has: `scene.geometry_mode` and `version_id`
    - Add: `scene.metadata["simulation_integrity"] = { state }`
- **UI display**:
  - `magnet/ui_v2/js/panel-config.js` already displays hydrostatics/resistance badges.
  - Add a new “Simulation Integrity” badge/panel driven by `scene.geometry_mode`, hydrostatics method, and whether physics ran on current design version.

### TransformReport surfacing (UI location)

The section compiler already produces `section.transform_report`:
- `magnet/kernel/stdlib/section_compiler.py: TransformReport`
- Stored onto `section.transform_report` in `compile_section`

Surface it **directly under the Simulation Integrity badge** so a user immediately sees any auto-transforms, e.g.:
- “resampled: 3 pts → 32 pts (rule=default_32)”
- “hard_edges_snapped: [z1, z2, …]”
- “reversed_order=true”

Recommended wiring:
- Backend: include a summarized list in `SceneData.metadata`, e.g.:
  - `scene.metadata["transform_reports"] = [{"section_id": ..., "body_id": ..., "report": ...}, ...]`
  - (Populate from compiled sections; do not require UI to reconstruct from raw resources.)
- UI: show as an expandable “Transforms” section within the badge panel.

### Minimal mechanics (version coherency)

Add a simple version tag whenever physics validators run successfully:
- In `magnet/physics/validators.py: HydrostaticsValidator.validate` and `ResistanceValidator.validate`,
  - write `kernel.physics_last_validated_version = design_version` and `kernel.physics_last_validated_at = timestamp`.
  - (Design version is available through `StateManager` – `design_version` is used widely; if not exposed directly, write it from the conductor/phase layer.)

Then compute:
- If `scene.geometry_mode == AUTHORITATIVE` **and** `kernel.physics_last_validated_version == current_design_version`: **AUTHORITATIVE**
- If `scene.geometry_mode == VISUAL_ONLY` **or** physics missing: **APPROXIMATE**
- If physics exists but is from a different version or uses a different method than the rendered geometry implies: **DECOUPLED**

---

## Fix 2 — Physics blindness: map geometry features → physics inputs (or warn loudly)

### What’s wrong today

Savitsky planing resistance only “sees” coarse hull parameters:
- `magnet/physics/savitsky.py: SavitskyInputs` includes `beam_m`, `deadrise_deg`, `displacement_kg`, `lcg_from_transom_m` (+ appendage/air areas).
- `magnet/physics/validators.py: ResistanceValidator.validate` constructs `SavitskyInputs` without reading geometric feature primitives.

This enables a silent failure:
- Visual model: “Viking” hull with rails/chines
- Physics: drag of a generic smooth planing bottom with the same average beam/deadrise

### Two-phase fix strategy (recommended)

#### Phase 2A (Week 1) — Truthfulness warning / uncertainty (minimal, safe)

When geometry indicates unmodeled planing features, explicitly attach warnings to resistance outputs:
- Examples of “unmodeled features” detectable from geometry:
  - Multiple hard-edge vertices (`EdgeType.HARD`) near the waterline across many stations
  - `geometry.discontinuity` markers representing rails/steps (if present in resources)

Implementation hooks:
- Extend novelty/impact messaging to include these features:
  - Existing framework: `magnet/physics/uncertainty.py: novelty_impact_from_state_resources`
  - Add additional detection in that function (or a sibling helper) for:
    - `geometry.discontinuity` count/types
    - hard edge density derived from section points (via compiled geometry in `compile_to_geometry`)
- Attach to resistance/hydrostatics uncertainty fields similarly to hydrostatics:
  - Hydro already writes uncertainty in `_write_hydrostatics_outputs_from_geometry`: `magnet/physics/validators.py`
  - Mirror for resistance: include “features not modeled” in `resistance.validity_note` or a new `resistance.uncertainty`

Acceptance criteria:
- Any design with rails/chines that are not explicitly modeled in physics produces:
  - A visible UI warning
  - A machine-readable uncertainty note

#### Phase 2B (Week 2) — Geometry-derived inputs for Savitsky (incremental modeling)

Without adding hull-type branches, derive additional continuous inputs from section geometry:

**(a) Use chine beam, not overall beam**
- Derive `beam_chine_m` from geometry:
  - For each section, identify the chine vertex as the point with `EdgeType.HARD` closest to the draft plane (or a tagged “chine” edge_type if you support that).
  - Compute local chine half-beam \(y_{chine}\), then \(b_{chine} = 2 y_{chine}\).
- Feed `SavitskyInputs.beam_m = beam_chine_m` (or blend between overall beam and chine beam with an uncertainty penalty).

Where to wire:
- `magnet/physics/validators.py: ResistanceValidator.validate` (where `SavitskyInputs(...)` is created)
- Feature extraction can live near physics:
  - New helper: `magnet/physics/geometry_feature_extract.py` (recommended location)

**(b) Spray rails/strakes**
Savitsky does not directly take “spray rail count.” If you choose to model them:
- Use **explicit, bounded correction factors** and declare them in validity/uncertainty text.
- Prefer using existing knobs:
  - `SavitskyInputs.appendage_area_m2` (can represent added wetted area/drag of rails)
  - Or adjust friction coefficient \(C_f\) via a bounded multiplier (declare as empirical).

If you do **not** model them yet (acceptable), you must:
- Emit a truthfulness warning (“spray rails present but ignored by Savitsky in this build”).

---

## Fix 3 — Faceted mode + hydrostatics consistency (avoid visual/physics divergence)

### What changes when faceted mode is enabled

Faceted tessellation builds planar panels between sections:
- `magnet/webgl/geometry_pipeline.py: HullGeometryPipeline._tessellate_faceted`

Hydrostatics, however, is currently computed from **section polygons** via deterministic 1D integration:
- `magnet/physics/geometry_hydrostatics.py: compute_hydrostatics_from_geometry`
- Integration method switches between Simpson and trapezoid:
  - `magnet/physics/geometry_hydrostatics.py: _integrate_1d` (composite Simpson when spacing is approximately uniform; trapezoid otherwise)

This matters because faceted panels imply **piecewise-linear** geometry along the length; Simpson’s parabolic assumption can diverge from linear panelization if stations are close to uniform.

### Minimum safe rule (recommended)

When a hull is declared “panelized/faceted”, hydrostatics integration must be *consistent* with that assumption.

You have two viable options:

#### Option A (minimal, recommended for 1–2 weeks): force linear integration for panelized hulls

Add an integration mode that is **hard-coupled** to surface intent:
- `surface_definition=="panelized"` ⇒ `integration_mode="linear"` (trapezoid)
- `surface_definition=="lofted"` ⇒ `integration_mode="parabolic"` (Simpson when eligible, else trapezoid fallback)

Implementation shape:
- `compute_hydrostatics_from_geometry(..., integration_mode="linear"|"parabolic")`
  - `"linear"`: always trapezoid
  - `"parabolic"`: Simpson when eligible, else trapezoid fallback (existing behavior)
- File touchpoints:
  - `magnet/physics/geometry_hydrostatics.py: compute_hydrostatics_from_geometry` (thread the flag into the integration calls)
  - `magnet/physics/geometry_hydrostatics.py: _integrate_1d` (add a bypass to trapezoid when requested)
  - `magnet/physics/validators.py: _write_hydrostatics_outputs_from_geometry` (write `hull.hydrostatics_method_detail` and uncertainty basis to reflect `"panelized_linear"` mode)

**Critical consistency requirement (avoid “two weights”): make integration_mode a HullState property**

If faceted/panelized mode switches hydrostatics integration to trapezoid, that choice must be **global** so *every* downstream physics module uses the same displaced volume/displacement.

Do **not** treat `integration_mode` as a local toggle inside one validator.

Recommended state contract (strict compliance):
- `hull.hydrostatics_integration_mode = "linear"|"parabolic"` (required; no “auto”)
- Derivation is deterministic:
  - `surface_definition=="panelized"` ⇒ write `"linear"`
  - `surface_definition=="lofted"` ⇒ write `"parabolic"`

Then:
- `HydrostaticsValidator` reads `hull.hydrostatics_integration_mode` and passes it into `compute_hydrostatics_from_geometry`.
- Any other module that recomputes hydrostatics-like quantities (e.g., stability curves) must also read the same state field (or, better, consume the already-written SSOT hull outputs).

Acceptance criteria:
- When panelized mode is active:
  - Hydrostatics reports `hull.hydrostatics_method="geometry_integration"` and `hull.hydrostatics_method_detail="panelized_linear"` (or similar)
  - Uncertainty basis explicitly states “linear between stations”

**Important: mark Option A as TEMPORARY in code**

Add a TODO at the integration switch point (and in the method_detail string) explicitly stating:
- This is a **temporary bridge** until mesh-based clipped volume is implemented.
- It should not silently fossilize as the final “panelized hydrostatics” method.

#### Option B (more work): mesh-based displaced volume integration

Implement mesh-based volume below the waterline (divergence theorem) on a mesh clipped at the draft plane.

This is more robust for arbitrary panelizations, but it requires careful handling because the hull mesh may not be watertight at the deck (unless you add a waterplane cap).

If you choose this route, keep it opt-in and truthfully labeled in method detail (e.g., `mesh_clipped_volume`).

### Enabling faceted tessellation without adding hull-type enums

Today, the authoritative tessellation path does **not** call the faceted mode:
- `magnet/webgl/geometry_service.py: GeometryService._tessellate_grm` calls `pipeline.tessellate()`

To enable faceting without “hull types,” use a **geometric intent signal** carried by geometry primitives.

**Implementation watch-out (architecture):**
- Do **not** add this to legacy `HullDefinition` (parameter synthesis path).
- Prefer attaching it to **authoritative geometry metadata**, so it flows through the existing GRM → exporter path without requiring broad schema changes.
  - Recommended placement: `HullGeometry.metadata` (canonical geometry object) populated by the compiler.

1) Extend the `geometry.surface` primitive to allow `definition: "panelized"` (in addition to `"lofted"`).
   - Update schema: `magnet/agents/geometry_schema.json`
   - Update proposer prompt so it can emit `geometry.surface { definition: "panelized" }` when asked for faceted aluminum craft:
     - `magnet/agents/geometry_proposer.py: GEOMETRY_PROPOSER_SYSTEM_PROMPT`

2) Propagate this intent into authoritative geometry metadata:
   - Compiler: `magnet/kernel/stdlib/compiler.py: compile_to_geometry` stores a hint like:
     - `hull_geom.metadata["surface_definition"] = "panelized"`
   - Then read that hint downstream wherever needed (tessellation, hydrostatics mode selection) without adding categorical enums.

3) Select faceted tessellation when hinted:
   - In `magnet/webgl/geometry_service.py: GeometryService._tessellate_grm`, call:
     - `pipeline.tessellate_with_options(sections, faceted=True, panel_edges_hard=True)`
     - Only when the hint indicates panelization.

4) Tie hydrostatics integration mode to the same hint:
   - If `surface_definition=="panelized"`, force hydrostatics integration mode to “linear” (Option A) or run mesh-based integration (Option B).

### Strict compliance: no migration, no defaults

We are greenfield with zero legacy users. Therefore:
- **There is no migration path.**
- **There are no defaults.**

Rules:
- `surface_definition` is **required**. If it is missing, compilation must fail loudly with a clear error:
  - “Missing required `surface_definition` (must be `lofted` or `panelized`).”
- The agent/proposer must declare surface intent at the start of every design thread (first program).
- Do not infer surface intent from shape; intent must be explicit.

---

## Fix 4 — Planarity + dihedral validator (enforceable style metrics)

### Why this is required

“Metal Shark-like” patrol craft requires:
- flat plates (planarity)
- sharp dihedral transitions at panel joins (dihedral angle constraints)

These are **not** currently validated. Quality gates only warn about “fairness,” and are not tied to faceting intent:
- `magnet/kernel/stdlib/quality_gates.py: check_fairness/check_resolution`

### Where to implement

Add a new validator module, e.g.:
- `magnet/validators/geometry_style_metrics.py` (or under `magnet/physics/` if you want it treated as engineering)

Integrate it into the phase pipeline via:
- `magnet/kernel/conductor.py: Conductor.run_phase` (phases run via validator registry / executor)
- or include it in the existing “hull” or “compliance” phase definitions (wherever phase registry lives)

### Planarity metric (concrete math)

For each quad panel defined by vertices \(p_0, p_1, p_2, p_3\):

1) Compute plane normal from triangle \(p_0,p_1,p_2\):
- \(n = (p_1 - p_0) \times (p_2 - p_0)\)
- Normalize \( \hat{n} = n / \|n\| \)

2) Compute signed distance of \(p_3\) to the plane:
- \(d = \hat{n} \cdot (p_3 - p_0)\)

3) Planarity residual is \(|d|\).

Thresholding:
- For a “plate” expectation, use a tight default like **1mm** in meters: \(|d| > 0.001\) ⇒ non-planar.
- Scale threshold by hull size if needed (e.g., \(1e^{-5} \times \text{LOA}\)), but keep defaults strict for patrol craft.

### Planarity refinement: normalized “warp factor” (grade signal)

Absolute deviation (meters) is the right **manufacturing/gate** threshold, but a **dimensionless grade** is more robust across panel sizes.

Define a warp factor \(w\) for a quad as (dimensionless):
- \(w = \frac{|d|}{\|p_2 - p_0\|_{diag}}\)

Where:
- \(d\) is the signed distance of \(p_3\) to the plane defined by \(p_0,p_1,p_2\)
- \(\|p_2 - p_0\|_{diag}\) is the quad’s **diagonal length** (use the longer diagonal if you compute both: \(\max(\|p_2-p_0\|,\|p_3-p_1\|)\))

Use (strict compliance pivot):
- **Gate** (hard failure): \(w \le w_{max}\), where \(w_{max}\) is a **fixed dimensionless tolerance** (manufacturing spec).
  - Implement as: \(|d| \le w_{max} \cdot \max(\|p_2-p_0\|,\|p_3-p_1\|)\)
  - Choose and lock a default \(w_{max}\) for aluminum plate builds (example: \(1e^{-4}\) corresponds to 1mm over a 10m diagonal).
- **Grade** (informational): report max/median warp factor for UI reflection-line quality.

Implementation note:
- Do this on the **pre-triangulated quads** inside `magnet/webgl/geometry_pipeline.py: HullGeometryPipeline._tessellate_faceted` while you still have quad structure.
- Emit violations into state as a validator result (and into UI as part of Simulation Integrity).

### Dihedral metric (panel join sharpness)

For adjacent panels with normals \(\hat{n}_1, \hat{n}_2\):
- Dihedral angle \( \theta = \arccos(\mathrm{clamp}(\hat{n}_1 \cdot \hat{n}_2, -1, 1)) \)

Targets:
- “Hard chine” should have \(\theta\) above a minimum (e.g., \( \theta \ge 20^\circ \) depending on craft).
- “Smooth” should have \(\theta\) below a maximum (e.g., \( \theta \le 5^\circ \)).

### Validator outputs (contract)

Write both:
- **machine-readable metrics** (max residual, count over threshold, worst dihedral, etc.)
- **gate result** (PASS/WARN/FAIL depending on user intent)

Do not hardcode “Metal Shark” labels—gate only when `surface_definition=="panelized"` or when the user supplies a constraint.

### Strict compliance enforcement point (blocking semantics)

In strict compliance mode, planarity is not advisory:
- If `surface_definition=="panelized"` and any panel violates the warp gate \(w > w_{max}\), execution must be **blocked**.

Where to enforce:
- Prefer enforcement at **program execution / phase gating**, not in UI:
  - The validator returns FAILED and the conductor/program executor must refuse to “advance” or persist the new state as successful.
  - This is the operational equivalent of “ActionPlanValidator blocks progress” without overloading ActionPlanValidator with geometry-specific logic.

### Metrics schema (pin exact state paths)

To avoid schema drift and cross-branch merge pain, pin a minimal, explicit contract for where these metrics live in state.

Recommended state paths (example contract):
- `metrics.panel.planarity_max_m`
- `metrics.panel.planarity_rms_m`
- `metrics.panel.warp_factor_max`
- `metrics.panel.warp_factor_rms`
- `metrics.panel.dihedral_min_deg`
- `metrics.panel.panel_count`

Also store a validator receipt:
- `validators.geometry_style_metrics.status` (PASSED/WARNING/FAILED)
- `validators.geometry_style_metrics.findings` (list)

Pin these paths in one place (single source of truth), e.g.:
- a small “metrics path registry” module under `magnet/validators/` or `magnet/control_plane/`

---

## Fix 5 — Resampling / preservation mode (stop low-pass filtering sharp features)

### What must change

### Critical watch-out: topology trap (must harmonize point counts)

`HullGeometryPipeline` primarily “skins” between sections by **index correspondence** (point \(i\) in section A connects to point \(i\) in section B), which assumes **topological consistency**.

If preservation mode allows some sections to remain at 6 points (hard chine) while others are at 32 points (smoothed), tessellation may:
- truncate inconsistently (faceted mode uses `min_points`),
- generate degenerate triangles / pinching,
- or fail downstream validation expectations.

Evidence of correspondence assumptions:
- Visual densification and interpolation preserve “point i → point i”: `magnet/webgl/geometry_pipeline.py: HullGeometryPipeline._densify_sections_linear`
- Skinning logic operates along the ordered section curve: `magnet/webgl/geometry_pipeline.py: HullGeometryPipeline._tessellate_from_sections`

**Therefore, preservation mode must be GLOBAL or HARMONIZED across the hull**, not per-section ad hoc.

Recommended strict policy (mandatory for `surface_definition=="panelized"`):

- Decide a `target_points_per_section` once per body as:
  - `target_n = max(len(points) for sections_in_body)`

- Enforce:
  - Every section in that body must end up with **exactly `target_n` vertices**.
  - Upsampling must be **linear in z** (no splines), so plates remain piecewise-linear.
  - If after compilation any section has a different count, **fail compilation** (hard error).

Rationale (strict compliance):
- The WebGL lofter uses index correspondence; mismatched counts are “topology suicide.”
- “Panelized” is a manufacturing claim: the system must force a consistent vertex topology rather than accepting arbitrary authored counts.

Note:
- This is intentionally **strict linear upsampling** (to the maximum count), per the pivot memo.
- For `surface_definition=="lofted"`, keep existing smooth behavior, but still prefer consistent per-body point counts for clean lofting.

1) **Agent normalization must not resample away sharp features**
- Today it enforces a “smoothness floor” by resampling to `target_n >= 12`:
  - `magnet/agents/geometry_proposer.py: GeometryProposer._normalize_section_points`

Fix:
- If a section has any hard edges in `edge_types`, do **not** upsample or resample it in `_normalize_section_points`.
- Only enforce the smoothness floor for purely smooth sections.
 - BUT: if you skip resampling for some sections, you must still harmonize the *whole body* to a common `target_n` later (see topology trap policy above).

2) **Agent auto-section insertion must be disabled for panelized hulls**
- `_ensure_min_loft_sections` inserts interpolated sections for lofting smoothness:
  - `magnet/agents/geometry_proposer.py: GeometryProposer._ensure_min_loft_sections`

Fix:
- If surface definition is `"panelized"`, skip densification and require the authored station set to define panel breaks.

3) **SectionCompiler must expose a preservation mode explicitly**
- Section compiler already has a strong start:
  - Preserves authored vertices when edge typing is present (unless forced): `magnet/kernel/stdlib/section_compiler.py: _compile_polygon_section`
  - Has explicit `resample_points` override

Add:
- `preservation_mode: "authored"|"linear_upsample"|"default"` on `geometry.section`
  - For `"authored"`: never resample; never enforce default_32.
  - For `"linear_upsample"`: allow *linear* resampling only (no splines) and preserve hard edges.
  - For `"default"`: keep existing behavior.

Nyquist-inspired guard (practical heuristic):
- If `len(points) < 6` **and** any edge is HARD, default to `preservation_mode="authored"`.

Also ensure transforms are visible:
- `magnet/kernel/stdlib/section_compiler.py: TransformReport` exists; expose it in scene metadata and spiral responses.

### Where to implement harmonization (recommended insertion points)

To avoid spaghetti and keep authority boundaries clean:
- Implement “target_n selection + linear resample to target_n” in the **compiler** stage, not in WebGL:
  - `magnet/kernel/stdlib/section_compiler.py`: extend `_compile_polygon_section` to optionally accept a `target_n` decided per-body by the caller.
  - `magnet/kernel/stdlib/compiler.py: compile_to_geometry`: decide `target_n` per body based on:
    - `surface_definition` metadata (“panelized” vs “lofted”)
    - authored point counts
    - preservation_mode

---

## Refinement: where to put `beam_chine` extraction (physics-local, geometry-aware)

Per the “first principles” guidance, keep hydrodynamic geometry awareness inside the geometry-based physics module:
- Put a helper like `_extract_hydrodynamic_beam(section, draft)` in:
  - `magnet/physics/geometry_hydrostatics.py`

Then have `magnet/physics/validators.py: ResistanceValidator.validate` call this helper when constructing `SavitskyInputs.beam_m`, instead of using `hull.beam` directly.


---

## Fix 6 — Make spiral execution “truthful by default” for performance/style requests

Today spiral chat defaults to not running critical phases:
- `magnet/deployment/spiral_endpoints.py: SpiralChatRequest.run_critical_phases` default `False`

Fix without breaking “noisy phases” concerns:
- Keep the default, but when the user requests performance-critical or panelized style, automatically:
  - Set `run_critical_phases=true`
  - Include at minimum: `["hull", "stability", "compliance"]` (and your new geometry-style-metrics validator phase)

Also: treat physics errors as truth failures in spiral responses:
- Program executor stores errors in validation output:
  - `magnet/kernel/program_executor.py: _run_validation` sets `results["hydrostatics"]["error"]` and `results["resistance"]["error"]`
- Spiral should surface these as `status="partial"` with explicit keys.

---

## UI changes checklist (Simulation Integrity badge)

UI already surfaces:
- Hydrostatics method badge: `magnet/ui_v2/js/panel-config.js` (`hull.hydrostatics_method`)
- Resistance validity badge: `magnet/ui_v2/js/panel-config.js` (`resistance.method_valid` + `validity_note`)

Add:
- A “Simulation Integrity” badge based on:
  - `scene.geometry_mode` (`magnet/webgl/schema.py: GeometryMode`)
  - `kernel.physics_last_validated_version` (new)
  - `hull.hydrostatics_method` + `hull.hydrostatics_method_detail` (existing + new detail)
  - style-metrics validator outputs (new)

Behavior:
- AUTHORITATIVE: green “Verified”
- APPROXIMATE: blue “Unverified Geometry”
- DECOUPLED: red “Decoupled (visual ≠ physics)”

Also: stop hardcoding `allow_visual_only=true` in the default 3D scene fetch:
- UI currently does: `magnet/ui_v2/js/scene-manager.js: SceneManager._loadAndRenderPrimitives`
- Make visual-only an explicit user toggle (and reflect it in the integrity badge).

---

## Agent prompt update checklist (prevent enum back-sliding)

When updating the proposer to emit panelized intent, include explicit negative examples so “helpful tags” don’t creep in.

Where:
- `magnet/agents/geometry_proposer.py: GEOMETRY_PROPOSER_SYSTEM_PROMPT`

Add:
- Positive example: `geometry.surface { definition: "panelized" }`
- Negative examples:
  - “Never add hull-type tags like `metal_shark: true`, `viking: true`, `style: patrol`”
  - “Never set `hull.hull_type`”

### “Fail loudly” rule for panelized/faceted intent (no repair-and-continue)

Current proposer behavior includes “repair-and-continue” normalization and section insertion, which is useful for generic hulls but **contradicts truthfulness** for strict faceted intent:
- `magnet/agents/geometry_proposer.py: GeometryProposer._normalize_section_points` (resampling)
- `magnet/agents/geometry_proposer.py: GeometryProposer._ensure_min_loft_sections` (inserts stations)

For panelized intent, change the contract:
- If the proposer cannot satisfy **planarity/topological consistency** without smoothing away features, it must **not** “make something that looks right.”
- Instead, it should:
  - return an explicit clarification request (ASK) for missing panel topology / station set, or
  - return a structured failure (`success=false`) with a reason like `FACETED_CONTRACT_VIOLATION`, surfaced to UI as “cannot satisfy request truthfully.”

Minimum enforcement rule:
- If `surface_definition=="panelized"`:
  - disable `_ensure_min_loft_sections`
  - disable “smoothness floor” resampling
  - require global harmonization to a consistent `target_n` (compiler step)
  - if harmonization would destroy hard-edge alignment, fail loudly

---

## Regression harness (wire into CI once metrics land)

Once planarity/dihedral + feature→physics warnings exist, wire a small torture suite so regressions can’t reintroduce silent failures.

Hook:
- Add a test group that:
  - Generates a panelized hull program and asserts planarity metrics + simulation_integrity are correct
  - Generates a “Viking-like” planing hull with hard edges and asserts:
    - `beam_chine` extraction is used (or at least a warning is emitted if not modeled yet)
    - resistance uncertainty/validity note flags any unmodeled feature set

Where:
- Prefer `tests/validation/` and `tests/physics/` plus a small integration test that calls the same pipeline the spiral uses.

## Test plan (must add/adjust)

### Unit tests

- **Planarity validator**
  - Add tests under `tests/validation/` or `tests/webgl/`
  - Cases: perfectly planar quad (pass), 2mm folded quad (fail), near-threshold (warn)

- **Hydrostatics linear integration mode**
  - Add tests under `tests/physics/`
  - Ensure `integration_mode="linear"` forces trapezoid even for uniform station spacing (`magnet/physics/geometry_hydrostatics.py: _integrate_1d`)

- **Feature extraction for chine beam**
  - Add tests under `tests/physics/` or `tests/kernel/`
  - Construct sections with a hard-edge vertex at waterline and verify `beam_chine_m` derivation

### Integration tests

- **Simulation Integrity tri-state**
  - Add tests under `tests/integration/`:
    - Visual-only mode ⇒ integrity APPROXIMATE
    - Authoritative + physics up-to-date ⇒ AUTHORITATIVE
    - Authoritative visual but physics version lag ⇒ DECOUPLED

---

## Definition of done (acceptance checklist)

- **No silent feature loss**:
  - Resampling/densification that changes authored geometry produces a surfaced warning (spiral + UI).
- **No silent physics blindness**:
  - If unmodeled features are present, resistance outputs carry explicit warnings/uncertainty.
- **Faceted crafts are verifiable**:
  - Panelized hulls use faceted tessellation, planarity metrics exist, and hydrostatics method is consistent and labeled.
- **UI truth badge is correct**:
  - Users can always tell whether what they see is what physics used.


---

## Appendix A — Implementation Patterns (For Cursor / “AI Context” Layer)

This appendix is deliberately explicit so Cursor can apply changes across the repo **without inventing new architecture**.

### A1) Pattern reference: “smooth-only” → `surface_definition` aware (Before vs After)

**Before (pattern):** logic implicitly assumes smooth lofted hulls and applies “helpful” smoothing.

```python
# BEFORE (pattern)
# - no explicit surface intent
# - implicit default smoothing / densification
def compile_sections(resources, loa):
    sections = _compile_all_sections(resources, loa)
    # default smoothing
    sections = _maybe_resample_default_32(sections)
    return sections
```

**After (pattern):** logic is explicitly surface-intent aware, and strict-compliance rules are enforced **upstream** (compiler), not patched in WebGL.

```python
# AFTER (pattern)
# - surface_definition is REQUIRED and validated early
# - panelized => strict linear upsampling to uniform target_n
# - lofted    => allow smooth defaults
def compile_sections(resources, loa, *, surface_definition: str):
    if surface_definition not in ("panelized", "lofted"):
        raise MissingSurfaceIntentError("surface_definition must be 'panelized' or 'lofted'")

    sections = _compile_all_sections(resources, loa)

    if surface_definition == "panelized":
        sections = harmonize_sections_linear_to_target_n(sections)  # strict
    else:
        sections = _maybe_resample_default_32(sections)  # existing behavior

    return sections
```

**Invariant:** No module is allowed to “guess” surface intent from geometry shape.

### A2) Dependency-ordered Phase 1 file manifest (“Touch List”)

These are the Phase 1 files Cursor should touch **in this order**, to avoid side-effects in the 400+ module repo.

| Order | Responsibility | File(s) |
|---:|---|---|
| 1 | **Schema lock**: require surface intent in primitives | `magnet/agents/geometry_schema.json` (and/or `magnet/agents/geometry_schema.json` if that is the active schema source) |
| 2 | **Proposer contract**: must emit surface intent first | `magnet/agents/geometry_proposer.py` (`GEOMETRY_PROPOSER_SYSTEM_PROMPT`, program validation rules) |
| 3 | **Compiler**: enforce required `surface_definition` and write into `HullGeometry.metadata` | `magnet/kernel/stdlib/compiler.py` |
| 4 | **Section compiler**: implement strict linear harmonization for `panelized` | `magnet/kernel/stdlib/section_compiler.py` |
| 5 | **Program execution**: fail loudly on missing surface intent / topology violations | `magnet/kernel/program_executor.py` (or whichever program execution path surfaces compile errors) |
| 6 | **Optional: WebGL**: read metadata/hints only (no smoothing logic here) | `magnet/webgl/geometry_service.py`, `magnet/webgl/geometry_pipeline.py` |

### A3) Error handling & warning taxonomy (what to throw vs. what to report)

Strict Compliance requires a **small, named taxonomy** so tests and UI can key off stable codes.

Define these as structured errors (names are suggested; keep them stable):

- `MissingSurfaceIntentError`
  - Trigger: `surface_definition` missing or not one of `{"lofted","panelized"}`
  - Enforcement point: compiler (Phase 1)

- `PanelizedTopologyError`
  - Trigger: non-uniform point counts after mandatory harmonization; or harmonization cannot be performed deterministically
  - Enforcement point: section compiler/compiler (Phase 1)

- `PlanarityGateError`
  - Trigger: warp factor \(w > w_{max}\) for any quad in panelized mode
  - Enforcement point: geometry-style validator (Phase 2; but gate behavior is required)

- `PhysicsDomainViolation`
  - Trigger: `resistance.method_valid == false` (Savitsky/Holtrop out-of-envelope)
  - Enforcement point: integrity computation (Phase 2/3)

All errors should include:
- `code` (stable string)
- `message` (human readable)
- `details` (structured, for debugging)

### A4) Pseudo-code: global topological harmonization (strict panelized)

**Constraint:** Panelized mode must not use splines. Interpolation is linear in z.

```text
harmonize_sections_linear_panelized(sections):
  assert len(sections) >= 2

  # Step 1: choose target_n (strict compliance)
  target_n = max(len(sec.points) for sec in sections)

  # Step 2: for each section, resample y(z) to target_n
  for sec in sections:
    pts = sec.points (as [y,z] monotone in z)
    z_grid = linspace(z_min, z_max, target_n)
    y_grid = linear_interpolate_y_of_z(pts, z_grid)
    # Step 2b: preserve hard edges by snapping their z positions to nearest z_grid index
    #          and copying edge_types marker to that index.
    sec.points = zip(y_grid, z_grid) with edge_types mapped

  # Step 3: assert uniformity
  if any(len(sec.points) != target_n for sec in sections):
    raise PanelizedTopologyError

  return sections
```

**Why this is safe:** WebGL tessellation relies on index correspondence; uniform `target_n` prevents “square-to-circle stitching.”

---

## Appendix B — Hard-Gate Specification (Strict Compliance Contract)

These are the **non-negotiable** invariants in strict compliance mode.

### B1) Hard gates (must reject)

A design MUST be rejected (hard failure) if any of the following are true:

1) **Missing surface intent**
- `surface_definition` is missing/null/not in `{lofted,panelized}`
- Error: `MissingSurfaceIntentError`

2) **Panelized topology mismatch**
- `surface_definition=="panelized"` and section vertex counts are non-uniform after harmonization
- Error: `PanelizedTopologyError`

3) **Planarity gate violated**
- `surface_definition=="panelized"` and any quad warp factor exceeds tolerance:
  - \( w = \frac{|d|}{\max(\|p_2-p_0\|,\|p_3-p_1\|)} \)
  - Reject if \( w > w_{max} \)
- Error: `PlanarityGateError`

### B2) Integrity downgrade (must not claim AUTHORITATIVE)

These do not necessarily reject geometry, but they MUST downgrade truth labeling:

4) **Physics Domain Violation**
- If Savitsky/Holtrop reports out-of-envelope (`resistance.method_valid == false`)
- Integrity: `APPROXIMATE (Out of Bounds)`
- Error/warning code: `PhysicsDomainViolation`

---

## Appendix C — Verification Data Manifest (Truth Layer)

### C1) Gold fixtures (frozen reference geometry)

Add a dedicated fixtures directory:
- `tests/fixtures/gold_standard/`

Required fixtures (minimum set):

1) `box_barge.json`
- Purpose: hydrostatics truth baseline (linear integration should match exact prismatic volume)
- Expected: displacement is exact within tight tolerance

2) `viking_v1_sharp.json`
- Purpose: feature-preservation + physics-blindness detection
- Expected: `beam_chine` extractor differs from `beam_max` when flare exists; warning emitted if rails are unmodeled

3) `twisted_plate.json`
- Purpose: planarity hard-gate failure
- Expected: `PlanarityGateError` (reject)

### C2) Failure mode matrix (“Expected Rejections”)

| Case | Input | Expected result |
|---|---|---|
| Missing intent | no `surface_definition` | reject with `MissingSurfaceIntentError` |
| Panelized mismatch | panelized + mixed point counts | reject with `PanelizedTopologyError` |
| Twisted panel | panelized + warp factor \(w > w_{max}\) | reject with `PlanarityGateError` |
| Savitsky OOB | extreme deadrise/ratios | integrity becomes `APPROXIMATE (Out of Bounds)` + `PhysicsDomainViolation` |

### C3) Performance regression benchmark

Harmonization (upsampling) can be expensive; require a perf test:
- Target: **<200ms** for harmonization + compile on “high” resolution (define vertex/station counts in test)
- Location: `tests/performance/` (or existing performance harness)

### C4) State-transition integration test (“Dirty State”)

Add an integration test that simulates:
- Start with valid AUTHORITATIVE design (physics run)
- Mutate geometry (e.g., change a section)
- Expect: integrity flips immediately to “unvalidated/decoupled” until physics is re-run

This prevents the system from showing “Verified” after any geometry mutation.


