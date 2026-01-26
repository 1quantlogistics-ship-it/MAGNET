# MAGNET Geometry Capability Audit (Viking-like vs. Faceted Patrol Craft)

This document consolidates **all findings and recommendations from this session** into a single, comprehensive audit.

## Executive summary (≤10 bullets)

- **Enum-free geometry generation exists and is first-class** via design-language `geometry.*` resources compiled to canonical `HullGeometry` and tessellated for UI (`magnet/kernel/stdlib/compiler.py: compile_to_geometry`, `magnet/webgl/interfaces.py: DesignLanguageAdapter`, `magnet/webgl/geometry_service.py: GeometryService.__init__`).
- **Hard edges/chines are representable and renderable** through per-vertex `edge_types` → `EdgeType.HARD` → split normals (`magnet/kernel/stdlib/section_compiler.py: _compile_polygon_section`, `magnet/webgl/geometry_pipeline.py: HullGeometryPipeline._tessellate_from_sections`, `magnet/webgl/mesh_builder.py: MeshBuilder.build/_compute_split_normals`).
- **True faceted-panel tessellation exists but is not used by default**: `HullGeometryPipeline.tessellate_with_options(faceted=True)` exists, but `GeometryService` calls `pipeline.tessellate()` (smooth path) (`magnet/webgl/geometry_pipeline.py: HullGeometryPipeline.tessellate_with_options`, `magnet/webgl/geometry_service.py: GeometryService._tessellate_grm`).
- **Multiple “fairing/smoothing” transforms can destroy authored facets/feature vertices**, especially for faceted patrol craft: agent normalization/resampling and section/LOD densification happen by default (`magnet/agents/geometry_proposer.py: GeometryProposer._normalize_section_points/_ensure_min_loft_sections`, `magnet/kernel/stdlib/section_compiler.py: _compile_polygon_section`, `magnet/webgl/geometry_pipeline.py: HullGeometryPipeline._densify_sections_linear`).
- **Asymmetric sections are not currently expressible** in the primary path because sections are treated as half-breadth and mirrored; the proposer forces `abs(y)` and the pipeline mirrors to generate the other side (`magnet/agents/geometry_proposer.py: GEOMETRY_PROPOSER_SYSTEM_PROMPT + _normalize_section_points`, `magnet/webgl/geometry_pipeline.py: HullGeometryPipeline._tessellate_from_sections`).
- **Planarity/dihedral “facet correctness” is not validated anywhere today** (no planarity/dihedral metric/validator found; faceting exists only as a tessellation mode, not an engineering constraint) (`magnet/webgl/geometry_pipeline.py: HullGeometryPipeline._tessellate_faceted`).
- **Silent failure risk is real** because (a) UI explicitly requests visual-only fallback, (b) spiral chat defaults to not running critical phases, and (c) program-level physics errors are captured as strings instead of failing execution (`magnet/ui_v2/js/scene-manager.js: SceneManager._loadAndRenderPrimitives`, `magnet/deployment/spiral_endpoints.py: SpiralChatRequest.run_critical_phases`, `magnet/kernel/program_executor.py: _run_validation`).
- **There are “repair-and-continue” agent instructions that bias toward producing *some* hull** even when fidelity is questionable (`magnet/agents/geometry_proposer.py: propose_geometry comments + _offline_fallback`).
- **Physics truthfulness scaffolding exists (uncertainty schema), but there is no agent recovery protocol that consumes it** (`magnet/physics/uncertainty.py: make_uncertainty`, `magnet/physics/validators.py: _write_hydrostatics_outputs_from_geometry`).

## Pipeline map (entry → agents → DSL/program → geometry → mesh/GLB → validators → persistence)

### Entry points (API/UI)

- **Spiral chat (design iteration)**: `magnet/deployment/spiral_endpoints.py: create_spiral_router`
  - Request model: `SpiralChatRequest`
  - Silent-failure relevant defaults: `run_critical_phases: bool = False`
- **Design language execution**: `magnet/deployment/api.py: execute_design_program` → `magnet/kernel/program_executor.py: execute_program`
- **3D scene fetch (UIv2)**: UI calls `/3d/scene?allow_visual_only=true`
  - `magnet/ui_v2/js/scene-manager.js: SceneManager._loadAndRenderPrimitives`

### Agents → Program/DSL

- **Geometry proposal (LLM → geometry primitives)**: `magnet/agents/geometry_proposer.py: GeometryProposer.propose_geometry`
  - Prompt: `GEOMETRY_PROPOSER_SYSTEM_PROMPT`
  - Pre-validation “repair” transforms:
    - `GeometryProposer._normalize_section_points`
    - `GeometryProposer._ensure_min_loft_sections`

### Program parsing/execution → state mutation

- **DSL parse**: `magnet/kernel/stdlib/parser.py`
- **Execution**: `magnet/kernel/program_executor.py: execute_program`
  - Runs `_run_validation` (physics-oriented, best-effort; see silent-failure section)

### Geometry compilation (resources → canonical HullGeometry/HullSection)

- **Compile resources**: `magnet/kernel/stdlib/compiler.py: compile_to_geometry`
- **Compile sections**: `magnet/kernel/stdlib/section_compiler.py: compile_section/_compile_polygon_section`
  - `TransformReport` stored on compiled sections (`section.transform_report`)

### Tessellation (HullGeometry → MeshData)

- **Single-authority geometry service**: `magnet/webgl/geometry_service.py: GeometryService.get_scene/get_hull_geometry`
- **Tessellation pipeline**: `magnet/webgl/geometry_pipeline.py: HullGeometryPipeline.tessellate/_tessellate_from_sections`
- **Faceted tessellation (available)**: `magnet/webgl/geometry_pipeline.py: HullGeometryPipeline.tessellate_with_options/_tessellate_faceted`
  - Not invoked in the authoritative path by default (`magnet/webgl/geometry_service.py: GeometryService._tessellate_grm`)
- **Hard edges → split normals**:
  - `magnet/webgl/geometry_pipeline.py: HullGeometryPipeline._tessellate_from_sections` (calls `builder.mark_hard_edge`)
  - `magnet/webgl/mesh_builder.py: MeshBuilder.build/_compute_split_normals`

### Validators / phases

- **Phase orchestration / BLOCKED states**: `magnet/kernel/conductor.py: Conductor.run_phase`
- **Physics validators (authoritative outputs)**:
  - `magnet/physics/validators.py: HydrostaticsValidator.validate`
  - Geometry-derived body count helpers: `magnet/physics/validators.py: _get_body_count_from_state/_is_multi_body_from_geometry`
- **Truthfulness schema**:
  - `magnet/physics/uncertainty.py: make_uncertainty/novelty_impact_from_state_resources`
  - Written during hydrostatics writing: `magnet/physics/validators.py: _write_hydrostatics_outputs_from_geometry`

### Persistence

- **State/version persistence**: `magnet/deployment/design_store.py: DesignStore.save/append_turn_record`

## Geometry expressiveness table

| Feature | Supported? (Y/N/Partial) | Where in code | Notes |
|---|---:|---|---|
| Hard chines / sharp edges | Y | `magnet/kernel/stdlib/section_compiler.py: _compile_polygon_section`; `magnet/webgl/geometry_pipeline.py: _tessellate_from_sections`; `magnet/webgl/mesh_builder.py: MeshBuilder.build` | Works if `edge_types` survive normalization/resampling. |
| Knuckles / multi-chine sections | Partial | same as above | Multiple “hard” vertices are representable, but edge alignment can be lost in normalization (`magnet/agents/geometry_proposer.py: _normalize_section_points`). |
| Planar facets / panelized hull sides | Partial | `magnet/webgl/geometry_pipeline.py: tessellate_with_options/_tessellate_faceted` | Exists, but not used in default authoritative path (`magnet/webgl/geometry_service.py: _tessellate_grm`). No planarity validator. |
| Flat / near-flat surfaces (local) | Partial | `magnet/kernel/stdlib/section_compiler.py: _compile_polygon_section` | Flat segments can be authored, but upsampling/densification can undermine panel purity. |
| Discontinuities (spray rails, steps, surface breaks) | Partial | Agent prompt maps: `magnet/agents/geometry_proposer.py: GEOMETRY_PROPOSER_SYSTEM_PROMPT` | Present as primitives/markers; engineering semantics/validation is limited today. |
| Sharp transitions preserved through mesh | Y (if hard edges marked) | `magnet/webgl/geometry_pipeline.py: _tessellate_from_sections`; `magnet/webgl/mesh_builder.py: MeshBuilder.build` | Depends on `EdgeType.HARD` reaching tessellation. |
| Multi-chine continuity (index consistency) | Partial | Prompt guidance: `magnet/agents/geometry_proposer.py: GEOMETRY_PROPOSER_SYSTEM_PROMPT` | Not validated; resampling can change vertex indices. |
| Asymmetric sections | N | `magnet/agents/geometry_proposer.py: _normalize_section_points (abs(y))` and mirroring in `magnet/webgl/geometry_pipeline.py: _tessellate_from_sections` | Primary path is half-breadth + mirrored full hull. |
| Complex transoms | Partial | Closure via end caps: `magnet/webgl/geometry_pipeline.py: _tessellate_from_sections/_triangulate_end_cap` | No explicit transom surface primitive; closure is generated. |
| Enforceable style targets (planarity/dihedral/sheer fairness) | Mostly N | Advisory-only: `magnet/kernel/stdlib/quality_gates.py: check_fairness/check_resolution` | Gates are warnings only; no planarity/dihedral validator exists. |

## “Faceted craft risk” (what gets smoothed/destroyed and where)

- **Agent resampling & vertex rewriting (high risk)**
  - Forced half-breadth + monotone z + point-count harmonization can alter corners: `magnet/agents/geometry_proposer.py: GeometryProposer._normalize_section_points`
  - Automatic station insertion via interpolation can blur intended panel breaks: `magnet/agents/geometry_proposer.py: GeometryProposer._ensure_min_loft_sections`
- **Section compiler default upsampling (aesthetic-driven)**
  - Default upsampling to 32 points when edge typing isn’t present: `magnet/kernel/stdlib/section_compiler.py: _compile_polygon_section`
- **Visualization densification across length**
  - Inserts intermediate sections to reach LOD section count: `magnet/webgl/geometry_pipeline.py: HullGeometryPipeline._densify_sections_linear`
- **Faceted tessellation exists but isn’t selected**
  - Faceted mode exists (`_tessellate_faceted`) but `GeometryService` uses `pipeline.tessellate()` by default: `magnet/webgl/geometry_service.py: GeometryService._tessellate_grm`

## Silent failure audit

### Where the system can appear to comply while not enforcing requirements

- **UI requests visual-only** (can show a plausible hull even if authoritative path fails)
  - `magnet/ui_v2/js/scene-manager.js: SceneManager._loadAndRenderPrimitives` uses `allow_visual_only=true`
  - Backend honors it: `magnet/webgl/geometry_service.py: GeometryService.get_hull_geometry`
- **Spiral chat defaults to not running critical phases**
  - `magnet/deployment/spiral_endpoints.py: SpiralChatRequest.run_critical_phases`
- **Program-level physics failures are captured, not escalated**
  - Hydrostatics/resistance exceptions stored as `results["..."]["error"]`: `magnet/kernel/program_executor.py: _run_validation`
- **Quality gates are advisory only**
  - `magnet/kernel/stdlib/quality_gates.py: check_fairness/check_resolution`
- **Silent transforms are tracked but not surfaced**
  - `TransformReport` exists and is stored on sections: `magnet/kernel/stdlib/section_compiler.py: TransformReport/compile_section`
  - No other consumers found in repo search for `transform_report`

### “Silent failure” instructions (truthfulness vs aesthetics) — prompt/agent audit criteria

**Truthfulness vs. Aesthetics**
- No prompt-level prohibition found that forbids proposing geometry that “looks right” while violating hydrostatics/resistance limits.
- Evidence of *aesthetic/continuity bias*:
  - “repair and continue” normalization before validation: `magnet/agents/geometry_proposer.py: propose_geometry` (comments + `_normalize_section_points`)
  - “domain-plausible” offline fallback: `magnet/agents/geometry_proposer.py: GeometryProposer._offline_fallback`

**Viking Feature Preservation**
- The proposer prompt describes hard chine continuity and gives `edge_types` examples but does not require surfacing when smoothing destroys performance-critical features.
- Evidence:
  - Hard edge guidance exists: `magnet/agents/geometry_proposer.py: GEOMETRY_PROPOSER_SYSTEM_PROMPT`
  - But transforms happen silently (unless manually inspected): `magnet/agents/geometry_proposer.py: _normalize_section_points/_ensure_min_loft_sections`, `magnet/webgl/geometry_pipeline.py: _densify_sections_linear`

**Measurable Engineering Compliance (DimensionProvenance gating)**
- `DimensionProvenance` exists in state manager (`magnet/core/state_manager.py: DimensionProvenance`), but `ActionPlanValidator` does not require SYNTHESIZED/KERNEL provenance prior to approval/execution.
- Evidence:
  - Validation checks: refinable paths, locks, units, coercion, bounds (`magnet/kernel/action_validator.py: ActionPlanValidator.validate/_validate_set/_validate_delta`)

**Failure Feedback Loop (BLOCKED → uncertainty-aware recovery)**
- Phases can be BLOCKED (`magnet/kernel/conductor.py: Conductor.run_phase`), and uncertainty objects exist (`magnet/physics/uncertainty.py: make_uncertainty`), but no explicit agent protocol was found that consumes uncertainty fields and performs a structured “error recovery” analysis.
- Spiral defaults reduce the chance of encountering/handling these failures in-loop:
  - `run_critical_phases` default false: `magnet/deployment/spiral_endpoints.py: SpiralChatRequest`

**Hard Edge Awareness**
- Yes: prompt explicitly instructs distinguishing hard vs smooth via `edge_types`, and tessellation respects `EdgeType.HARD`.
- Evidence:
  - Prompt examples: `magnet/agents/geometry_proposer.py: GEOMETRY_PROPOSER_SYSTEM_PROMPT`
  - Pipeline honors edge types: `magnet/webgl/geometry_pipeline.py: _tessellate_from_sections` and `magnet/webgl/mesh_builder.py: MeshBuilder.build`

### Proposed instrumentation points (file paths, log keys)

- **Expose `geometry_mode` prominently in UI**
  - Already present in scene payload (`magnet/webgl/geometry_service.py: GeometryService.get_scene` sets `SceneData.geometry_mode`)
  - UI should display/warn when `VISUAL_ONLY` (client: `magnet/ui_v2/js/scene-manager.js`)
- **Surface transforms**
  - Return/emit a structured list of transforms in spiral responses:
    - Proposer transforms: `magnet/agents/geometry_proposer.py: _normalize_section_points/_ensure_min_loft_sections`
    - Compiler transforms: `magnet/kernel/stdlib/section_compiler.py: TransformReport` (currently stored on sections only)
- **Escalate physics unavailability to a “partial/failed” truthfulness status**
  - If `_run_validation` yields `"hydrostatics.error"` / `"resistance.error"`, set spiral `status="partial"` and include a machine-readable failure code:
    - `magnet/kernel/program_executor.py: _run_validation`
    - `magnet/deployment/spiral_endpoints.py: SpiralChatResponse.status/failed_phases/errors`

## Final verdicts (required structure)

### Viking-like sportfish (smooth, feature-anchored geometry)

- **Verdict**: PARTIAL
- **Why**:
  - Smooth sections + hard edges are expressible and renderable (`magnet/kernel/stdlib/section_compiler.py`, `magnet/webgl/geometry_pipeline.py`, `magnet/webgl/mesh_builder.py`).
  - Proposer prompt provides explicit geometric mappings for features (flare, deadrise progression, chine continuity) (`magnet/agents/geometry_proposer.py: GEOMETRY_PROPOSER_SYSTEM_PROMPT`).
- **Blocking gaps**:
  - No enforceable metrics/constraints for feature anchors (sheer law, chine continuity, flare law); fairness gates are advisory-only (`magnet/kernel/stdlib/quality_gates.py`).
  - Silent transforms can erase key authored features without surfacing (`magnet/agents/geometry_proposer.py`, `magnet/kernel/stdlib/section_compiler.py`, `magnet/webgl/geometry_pipeline.py`).
- **Minimal change set**:
  - Add a small validator computing and gating on **sheer fairness**, **chine continuity**, **deadrise progression** derived from section geometry (new validator; run via conductor pipeline `magnet/kernel/conductor.py: Conductor.run_phase`).
  - Surface transform warnings (resample/densify) in spiral responses and/or scene metadata.
  - Ensure spiral runs **hull + hydrostatics/resistance** when the user asks for performance-critical features (still opt-in; but make it agent-driven).
- **Risk**:
  - Metric thresholds require tuning; false positives can block good designs, false negatives enable silent failures.

### Metal Shark–like faceted patrol craft (planar facets, hard chines, sharp transitions)

- **Verdict**: PARTIAL
- **Why**:
  - Hard edges are supported end-to-end (`edge_types` → `EdgeType.HARD` → split normals) (`magnet/agents/geometry_proposer.py`, `magnet/webgl/mesh_builder.py`).
  - Faceted tessellation exists and produces per-panel planar quads with per-face normals (`magnet/webgl/geometry_pipeline.py: HullGeometryPipeline._tessellate_faceted`).
- **Blocking gaps**:
  - Faceted tessellation is not activated in default authoritative path (`magnet/webgl/geometry_service.py: GeometryService._tessellate_grm`).
  - No planarity/dihedral validators exist; cannot enforce “faceted” as an engineering target (no planarity/dihedral validator found; only advisory quality gates exist: `magnet/kernel/stdlib/quality_gates.py`).
  - Multiple smoothing transforms can introduce unintended curvature (agent/compiler/pipeline densification).
- **Minimal change set**:
  - Add a **purely geometric** “panelized surface intent” signal (e.g., `geometry.surface.definition = "panelized"` or similar) and route to `tessellate_with_options(faceted=True)` in `GeometryService._tessellate_grm`.
  - Add a validator computing **panel planarity residuals** and **dihedral angles at hard edges**; surface failures in spiral.
  - In facet-intent mode, avoid LOD densification/upsampling that creates non-authored vertices (config-only threading; no architectural rewrite).
- **Risk**:
  - Planarity/dihedral metrics are sensitive to sampling and vertex correspondence; requires a consistent authored-vertex contract or explicit panel topology to avoid false positives.

