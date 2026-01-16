# MAGNET Full Design Flow (Human Intent → Geometry → Physics → State → Visualization)

This document describes MAGNET’s end-to-end design flow as implemented in the codebase. It is written for skeptical technical reviewers (naval architects, computational geometry engineers, and systems engineers). It is not marketing material. Where models are approximate, the approximation is stated explicitly, along with validity regimes and known failure modes.

The core claim of MAGNET is narrow and testable:

- The system maintains a **single evolving source of truth** for design data (`magnet.core.design_state.DesignState`).
- Geometry is **constructed (compiled)** from explicit primitives (new path) or parametric presets/enums (legacy path), then physics is evaluated **after construction**, with results written back to state.
- Agents can propose changes, but **cannot directly mutate state**; changes must pass the **Intent→Action firewall** (`magnet.kernel.action_validator.ActionPlanValidator`) and execute transactionally (`magnet.kernel.action_executor.ActionExecutor`).

---

## Introduction

### What MAGNET is and what problem it is solving

MAGNET is an interactive naval design system that converts human intent (mission requirements, operational preferences, constraints) into a consistent evolving design state, producing:

- **A hull geometry representation** suitable for early-stage physics evaluation and communication.
- **Physics-derived metrics** (hydrostatics, resistance, stability, power) with explicitly limited fidelity.
- **A 3D visualization/export** pipeline for communication and iteration, with an explicit separation between **authoritative** (engineering) geometry and **visual-only** approximations.

MAGNET’s scope is early-stage design exploration under uncertainty:

- Many requirements are qualitative or incomplete at the beginning.
- Geometry is not “final CAD”; it is a machine-checkable representation used to drive estimators and iteration.
- The goal is to quickly reach designs that are *consistent enough* to justify higher-fidelity tools or human refinement.

### Why traditional enumerated design systems fail at scale

Traditional “enumerated” systems model hulls as selections from a small set of categories (e.g., “planing monohull”, “displacement trawler”, “catamaran”), with preset features and coefficients. In practice, they fail when the desired design is not close to a preset family.

Failures are structural:

- **Combinatorics**: A system with \(N\) discrete hull “types” and \(M\) discrete feature toggles has \(O(N \cdot 2^M)\) combinations before continuous parameters are even considered. Attempting to cover novel combinations explodes maintenance and validation cost.
- **Brittle mappings**: Physics and geometry “rules of thumb” become conditional logic keyed on enums. As combinations proliferate, mappings become contradictory and hard to audit.
- **Bias / novelty collapse**: Any regression-to-a-template approach pulls results toward common presets. The system quietly pushes unusual intent into the nearest known category, producing derivative or “boxy” forms because the representation cannot express the requested novelty.
- **Coefficient-as-input pathology**: Treating coefficients (e.g., \(C_B, C_P\)) as primary inputs encourages designs that satisfy numeric targets without corresponding geometric truth, especially when geometry is not actually constructed and checked.

MAGNET’s architecture explicitly rejects “selection-first” modeling for hull form generation. It uses **construction-first** modeling (build geometry, then validate).

### Design philosophy: human-in-the-loop, iterative spiral, validation after construction

MAGNET is designed around three operational principles:

- **Human-in-the-loop**: The system pauses and requests a decision when it detects critical inconsistencies (e.g., severe stability failures). Humans are not bypassed for safety-critical judgments.
- **Iterative spiral**: Design is treated as repeated cycles of proposal → evaluation → update, not a single pass.
- **Validation after construction**: Geometry is created explicitly, then physics is computed on that geometry (or a declared approximation). This inverts legacy systems that infer geometry and performance from categories.

---

## Legacy System: Enumerated Design Path

### How the old system worked

The legacy path models hull form using categorical enums and parametric “family” generators:

- **Enums / presets**: `magnet.hull_gen.enums` defines categorical selections such as `HullType`, `ChineType`, `BowStyle`, `TransomType`, etc.
- **Parametric inputs**: `magnet.hull_gen.parameters` defines `HullDefinition` and nested configs (main dimensions, coefficients, bow/transom configs, deadrise profiles, feature toggles).
- **Generator**: `magnet.hull_gen.generator.HullGenerator` constructs a `HullGeometry` from a `HullDefinition`. Internally it encodes “type-driven” heuristics (e.g., how chines are created, bow/transom shapes).

Downstream evaluation historically relied on “type-aware” empirical calculations rather than geometry:

- **Deprecated hydrostatics**: `magnet.physics.hydrostatics` is explicitly marked DEPRECATED; it estimates hydrostatics from high-level parameters plus `hull_type`-like classifications.

### Use of presets, enums, hull “types,” coefficient-as-input patterns

The enumerated system uses:

- **Discrete choices** (enums) to select a family of shapes.
- **Coefficients and ratios** as direct levers (e.g., set \(C_B\) or \(C_P\) and let the generator attempt to comply).
- **Feature toggles** for attachments and stylistic details (spray rails, knuckles, tumblehome).

This approach is convenient for common hull families where historical data supports stable defaults. It is unreliable for novel forms because the mapping from “coefficient targets” to “geometry truth” is underdetermined without an explicit constructive representation.

### Why this approach collapses novelty and produces boxy or derivative forms

The failure mechanism is that the representational space is too small:

- If the system can only emit shapes that exist inside a handful of families, then any request outside that space gets coerced back into it.
- When the generator attempts to satisfy incompatible targets, it typically resorts to blunt adjustments (inflate midship, flatten sections, clamp deadrise), producing “boxy” artifacts because the family constraints dominate.

### Explicit technical limitations (combinatorics, bias, brittle mappings)

In code, these limitations show up as:

- Conditional logic keyed on enums that becomes untestable as combinations grow.
- “Magic numbers” or implicit rules of thumb encoded inside generators and calculators.
- Physics models that require categorical preconditions (“this is a displacement hull”), which are then inferred from enums rather than derived from the geometry.

MAGNET retains the legacy path primarily as:

- A **fallback** when no generative geometry resources exist.
- A **visual-only approximation** path when an authoritative geometry is not available.

---

## New MAGNET Architecture Overview

### High-level pipeline

MAGNET’s preferred pipeline is:

**Human Intent → Agent Reasoning → Geometry Construction → Physics Evaluation → State Update → Visualization → Iteration**

Concretely, this is implemented as:

- **Unified state**: `magnet.core.design_state.DesignState` is the single container for all design sections (mission, hull, propulsion, weight, stability, etc.) and for generative geometry resources.
- **Controlled mutation**: `magnet.core.state_manager.StateManager` provides path-based access, alias resolution, transactions, undo/redo, and provenance tracking.
- **Intent→Action firewall**: `magnet.kernel.intent_protocol` defines `Intent`, `Action`, and `ActionPlan`; `magnet.kernel.action_validator.ActionPlanValidator` enforces schema, bounds, unit normalization, locks, and stale-plan protection.
- **Execution**: `magnet.kernel.action_executor.ActionExecutor` applies validated actions transactionally and records auditable explain records.
- **Generative geometry path**: `magnet.agents.geometry_proposer` produces geometry programs; `magnet.kernel.program_executor` parses/expands/compiles them into `magnet.hull_gen.geometry.HullGeometry`.
- **Physics evaluation**: Validators in `magnet.physics.validators` compute hydrostatics/resistance and record findings; stability modules (`magnet.stability.*`) compute GM and GZ (with declared approximations).
- **Visualization/export**: `magnet.webgl.geometry_service.GeometryService` is the single geometry entry point for WebGL consumers; `magnet.webgl.geometry_pipeline` tessellates into meshes; API endpoints in `magnet.webgl.api_endpoints` expose data and exports.

### Explicit routing: generative program path vs legacy hull synthesis

The “transition” from the legacy enumerated path to the generative path is not a documentation preference; it is encoded in orchestration logic:

- If a design-language program/resources exist for the current design, the conductor prioritizes **program execution + compilation** (`magnet.kernel.program_executor` via `magnet.kernel.conductor`).
- If no program/resources exist (or the program cannot be executed), MAGNET falls back to legacy **hull family / parametric synthesis** (legacy path using `magnet.hull_gen.*`), and downstream physics may fall back to deprecated calculators where geometry-derived inputs are unavailable.

This makes the generative geometry language the first-class mechanism for creating authoritative hull geometry, with legacy retained as compatibility and (where explicitly permitted) visual-only approximation.

### Key architectural decisions (audit-relevant)

1. **Coefficients are outputs, not inputs**
   - \(C_B, C_P, C_{WP}\) are computed from geometry (or declared approximations), not used as causal inputs to “force” geometry.

2. **Physics is computed from geometry, not categorical hull type**
   - Multi-body behavior is driven by compiled geometry (e.g., per-section `body_id` grouping) and state parameters like `hull.hull_spacing_m`, not `if hull_type == "catamaran"` branching.

3. **Validation after construction**
   - MAGNET constructs a hull representation first, then evaluates it. Novel designs can exist and fail honestly, without being coerced into a preset family.

### Explain the unified design-state concept (single evolving source of truth)

`DesignState` is the canonical data structure. All “truth” that must persist across iterations lives here:

- Inputs (mission, payload, constraints).
- Derived geometry resources (generative primitives in `state.resources` / design-language fields).
- Computed outputs (hydrostatics, resistance, stability, performance) recorded back into state sections.
- Metadata: design versioning and phase tracking.

Important consequence: **geometry is not hand-edited in-place** by arbitrary components. Geometry is derived from state in a deterministic pipeline, so undo/redo and auditing operate on state diffs.

### Why MAGNET treats coefficients as outputs, not inputs

In MAGNET’s preferred workflow:

- Designers specify intent and constraints that matter operationally (speed, range, payload, draft limits).
- The system constructs geometry that attempts to satisfy intent.
- Coefficients (e.g., \(C_B, C_P, C_{WP}\)) are *measured* from geometry or inferred from physics outputs.

This avoids the coefficient-as-input pathology where you “dial” \(C_B\) without ensuring the hull geometry is physically consistent.

If coefficients are treated as inputs, the system must solve an inverse problem (“find a geometry that yields this coefficient set”) without enough constraints. MAGNET instead commits to a forward problem: **build a geometry, then compute the coefficients**.

---

## Human Intent Ingestion

### How qualitative intent is translated into quantitative targets

MAGNET ingests intent at the mission/system level and translates it into numeric targets that can be evaluated. Typical examples:

- **Speed intent**: “fast patrol” → target top speed \(V_{max}\) and cruise \(V_c\) in knots (stored in mission state).
- **Range intent**: “2,000 nm endurance” → range \(R\) and reserve margins; implies fuel mass via SFC assumptions.
- **Payload intent**: “carry 6 tonnes payload” → deadweight targets; influences displacement and stability.
- **Draft constraints**: “draft under 1.5 m” → hard bound on draft for geometry and loading.

The translation is implemented via:

- Path-based state updates (e.g., `mission.max_speed_kts`, `mission.range_nm`, etc.) enforced by `REFINABLE_SCHEMA` (`magnet.core.refinable_schema`).
- Deterministic unit normalization (e.g., kts → m/s internally where needed) via `magnet.core.unit_converter`.

### What is intentionally not specified at this stage

MAGNET intentionally avoids requiring early commitment to:

- Exact scantlings and structure layout.
- Detailed appendages (full skeg/rudder/propulsor geometry).
- Detailed internal arrangement and tank geometry (beyond simplified tank models for stability/FSC).
- High-fidelity hydrodynamics (CFD) and seakeeping.

These are deferred because early-stage intent is insufficient to justify their complexity. MAGNET’s outputs are intended to be accurate enough to detect gross inconsistencies and guide iteration, not to replace detailed design.

---

## Agent Reasoning Layer

### Role of the LLM/agent

The agent converts natural-language intent into one of:

- A **validated ActionPlan** that changes refinable state parameters, or
- A **geometry program** (design language) that constructs hull geometry from primitives, or
- A request for clarification when constraints are underspecified (explicit `ASK` statements in the program language).

The agent is not an “oracle”; it is a proposal generator. MAGNET is explicitly designed so that:

- The agent’s output is never authoritative by itself.
- The kernel enforces correctness, bounds, and auditability.

### Constraints: no enums, no preset hulls, no hardcoded “Viking-like” logic

In the generative path, the geometry agent is constrained to **geometry primitives** and is explicitly forbidden from directly setting categorical hull identifiers and legacy feature toggles as a shortcut.

This matters because:

- Setting `hull.hull_type = "planing"` is a classification, not a construction. It does not create a hull.
- “Preset hull families” encode hidden biases (what the author thought a planing hull should look like).

The implementation enforces these constraints in the geometry proposer and in downstream validation/compilation. Violations are rejected before state is committed.

### How the agent proposes geometry operations rather than shapes

The agent proposes **operations** such as:

- Define bodies (single or multi-body).
- Define sectional shapes at stations.
- Define discontinuities (hard chines/creases) and their intended edges.
- Loft/align/mirror/derive operations to assemble a coherent hull from section data.

This is a construction graph: the output is not “a mesh”; it is a set of primitives and constraints that a deterministic compiler turns into `HullGeometry`.

---

## Generative Geometry Language

### Core primitives (sections, curves, surfaces, attachments, constraints)

MAGNET’s design language stores geometry “resources” in state and compiles them deterministically. The key primitives are:

- **Bodies**: One or more hull bodies (e.g., catamaran as two bodies with offsets).
- **Sections**: Station-indexed cross-sections defined by ordered points in the \(y\)-\(z\) plane.
- **Surfaces/lofts**: The implied surface formed by lofting sections along the longitudinal axis \(x\).
- **Discontinuities**: Explicit hard edges / chines / knuckles with edge typing for visualization and (eventually) physics.
- **Constraints and derived values**: Alignment, symmetry, and constraints tying one feature to another.

The goal is not to represent every possible CAD feature, but to represent enough constructive intent to:

- Compute hydrostatics and low-order performance.
- Render a faithful visualization with sharp features preserved.

### Continuous parameterization

The language is continuous because:

- Station positions \(x_i\) are real-valued.
- Section points \((y_{i,j}, z_{i,j})\) are real-valued.
- Body offsets, deadrise, flare, curvature, etc. are implied by continuous geometry rather than enumerated categories.

This creates a design space that is not limited to a finite number of templates.

### How hulls are constructed via composition, not selection

Instead of selecting a hull “type”, the designer (via the agent) composes:

- A set of sections defining the shape envelope.
- Constraints that enforce symmetry, continuity, and alignment.
- Optional discontinuities to produce hard features (chines, knuckles).

The resulting hull can *resemble* a known family, but it is not forced to remain within that family’s parameterization.

### Mathematical representation (section curves, lofting, continuity constraints)

#### Section representation (authoritative input to compilation)

A section at station \(x_i\) is represented as an ordered list of points in the transverse plane:

\[
\mathcal{S}(x_i) = \{(y_{i,0}, z_{i,0}), (y_{i,1}, z_{i,1}), \ldots, (y_{i,n-1}, z_{i,n-1})\}
\]

Contractual constraints (enforced at proposal/compile time) include:

- **Open curve** from keel to deck: not a closed polygonal loop.
- **Monotone ordering** in the sense of “keel → deck” progression, to avoid self-intersections and loft twisting.
- **Consistent point count** across sections within a body (or deterministic upsampling to enforce this).

Given symmetry about centerplane, the full section is implied by mirroring across \(y=0\) where appropriate.

#### Lofting / surface implication

MAGNET does not treat lofting as a “styling step”. Lofting is the map from discrete section sets to a continuous surface suitable for meshing and integration.

A simplified view of the loft is:

\[
\mathbf{p}(x, t) \approx \text{interp}_x\left(\mathbf{p}_i(t)\right)
\]

where \(t\) parameterizes the section curve (from keel to deck), and \(\mathbf{p}_i(t)\) is the piecewise-linear or spline representation of section \(i\). Longitudinal interpolation is performed between stations \(x_i\) and \(x_{i+1}\).

Continuity targets:

- **Positional continuity** (\(C^0\)): sections connect without gaps.
- **Tangent continuity** is desirable but not guaranteed in early-stage polygonal inputs; instead MAGNET flags fairness issues via advisory quality gates.

#### Chines, keel lines, flare, deadrise as emergent properties

These are *measured* or *inferred* from geometry:

- **Deadrise** at a station can be estimated from the local slope of the bottom portion of the section:
  \[
  \beta(x_i) \approx \arctan\left(\left|\frac{\Delta z}{\Delta y}\right|\right)_{\text{bottom}}
  \]
- **Chine/knuckle** is represented by explicit edge typing at a point index \(j\) on a section, implying a crease along \(x\).
- **Flare** relates to outward slope near the topsides; similarly estimated from local section slopes.

MAGNET avoids hardcoding: “if planing then add a hard chine at 0.7B”. Instead, a hard chine exists because the primitive declares a crease, and the compiler propagates it consistently.

---

## Geometry Compilation

### Deterministic compilation steps

The compilation pipeline exists to convert declarative primitives into a canonical, machine-checkable geometry object:

- **Input**: design-language resources stored in `DesignState` (e.g., `state.resources` / program-managed fields).
- **Compile**: `magnet.kernel.stdlib.compiler` and `magnet.kernel.stdlib.section_compiler` generate `magnet.hull_gen.geometry.HullGeometry`.
- **Output**: `HullGeometry` (sections, features, metadata), used both for physics evaluation and visualization.

Key determinism requirements:

- Given the same state resources, the compiled geometry must be reproducible.
- Transformations applied during compilation must be logged (transform reporting) so that the system never silently “fixes” geometry without traceability.

### Section resampling / upsampling

Raw agent-proposed sections may have inconsistent point counts or uneven spacing, which causes:

- Loft twisting or local topology corruption during meshing.
- Inconsistent numerical integration for hydrostatics.

MAGNET applies deterministic normalization:

- Deduplicate consecutive points.
- Enforce keel-to-deck ordering.
- Upsample a section to a target count \(N\) (e.g., \(N=32\)) by interpolating along cumulative arc length \(s\):

1. Compute cumulative chord-length parameter:
   \[
   s_0 = 0,\quad s_k = \sum_{m=1}^{k}\|\mathbf{q}_m - \mathbf{q}_{m-1}\|
   \]
2. Create target samples \(\hat{s}_j = j \cdot s_{n-1}/(N-1)\).
3. Interpolate piecewise linearly (or via a controlled spline) to compute new points \(\hat{\mathbf{q}}_j\).

This step is not “styling”; it is a deterministic conversion from irregular user/agent input to a canonical representation required for stable downstream algorithms.

### Continuity enforcement

MAGNET enforces minimal continuity properties necessary for downstream pipelines:

- **Structural continuity**: sections must be consistent in ordering and count to avoid meshing artifacts.
- **Feature continuity**: hard edges (chines) must be consistent along \(x\), otherwise normals and mesh topology are unstable.

Where higher-order fairness is desired (e.g., curvature continuity), MAGNET currently provides **advisory warnings** rather than silently smoothing the hull, because smoothing changes design intent. Advisory checks live in `magnet.kernel.stdlib.quality_gates` and report issues such as resolution problems and curvature spikes.

### Why this is not “styling” or post-processing

Post-processing (“styling”) implies an aesthetic, optional modification that changes the design without explicit accountability.

MAGNET’s compilation steps are:

- **Necessary** to establish a coherent numerical representation.
- **Deterministic** and reportable.
- **Conservative**: they do not invent new features; they normalize representation so that physics/meshing do not fail for purely technical reasons.

If the normalized geometry produces poor fairness, MAGNET reports the issue and expects a new proposal, rather than smoothing it away silently.

---

## Physics & Naval Architecture Calculations

MAGNET’s physics calculations are early-stage estimators. Their purpose is to:

- Provide rapid feedback on feasibility and sensitivity.
- Detect gross inconsistencies (insufficient displacement, unstable GM, power mismatch).

They are not replacements for high-fidelity solvers. Accuracy bands depend on regime and completeness of inputs.

### Hydrostatics (displacement, centers, buoyancy)

#### Authoritative path: geometry-derived hydrostatics

The authoritative hydrostatics path computes from `HullGeometry` using numerical integration (`magnet.physics.geometry_hydrostatics`).

At a given waterline \(z = z_w\), the displacement volume is approximated by integrating sectional areas along \(x\):

\[
\nabla(z_w) \approx \int_{x_{AP}}^{x_{FP}} A(x, z_w)\,dx
\]

Using discrete stations (strip method):

\[
\nabla \approx \sum_{i=0}^{n-2} \frac{A_i + A_{i+1}}{2}\,\Delta x_i
\]

> **Implementation note (integration rule):** The current geometry-hydrostatics implementation uses **composite Simpson’s \(1/3\)** rule when station spacing is approximately uniform, and falls back to **trapezoidal** integration otherwise (`magnet.physics.geometry_hydrostatics._integrate_1d`). Composite Simpson prefers an **odd** number of stations; if an even count occurs, the implementation applies Simpson on the first \(n-1\) points and trapezoid on the remainder.

Longitudinal center of buoyancy (LCB) is:

\[
x_B \approx \frac{1}{\nabla}\int x\,A(x)\,dx
\;\approx\;
\frac{1}{\nabla}\sum_{i}\frac{(x_i A_i + x_{i+1} A_{i+1})}{2}\Delta x_i
\]

Vertical center of buoyancy (VCB) is computed from sectional area centroids similarly:

\[
z_B \approx \frac{1}{\nabla}\int A(x)\,z_c(x)\,dx
\]

Waterplane area \(A_{WP}\) and second moments of area (\(I_T, I_L\)) are computed from the waterline intersections of sections. Transverse metacentric radius:

\[
BM_T = \frac{I_T}{\nabla}
\]

These are standard naval architecture relationships; MAGNET’s implementation uses the compiled section geometry rather than a hull-type heuristic.

> **Implementation note (waterline clipping):** Partially submerged sections are handled by explicitly clipping the full-section polygon against the half-plane \(z \le z_w\) using **Sutherland–Hodgman** polygon clipping (`magnet.physics.polygon_ops.clip_polygon_z_le`), then computing area/centroid via Green’s theorem (`polygon_area_centroid`).

#### Multi-body vessels

For multi-body hulls, per-body hydrostatics are combined using parallel-axis shifts. If each body \(k\) has waterplane inertia \(I_{T,k}\) about its own centerplane and lateral offset \(d_k\):

\[
I_T = \sum_k \left(I_{T,k} + A_{WP,k}\,d_k^2\right)
\]

This treats “body count” as a geometric fact (count of compiled bodies) rather than a categorical hull type.

> **Implementation note (body count + spacing):** In the geometry-derived path, body count is inferred from compiled geometry by grouping sections by `body_id` (see `magnet.physics.geometry_hydrostatics._count_bodies_in_geometry`). When operating via state parameters, multi-body spacing is represented explicitly as `hull.hull_spacing_m` (refinable; see `magnet.core.refinable_schema`) and recorded in `HullState.hull_spacing_m` (`magnet.core.dataclasses.HullState`).

#### Legacy fallback: deprecated parametric hydrostatics

If authoritative geometry is not available, MAGNET may fall back to `magnet.physics.hydrostatics` (explicitly deprecated). This path estimates displacement and centers from high-level coefficients and hull type assumptions. It is retained only for compatibility and should be treated as **approximate** even when it returns values.

> **Current status (validator wiring):** The primary entry point is `compute_hydrostatics_from_geometry()`; `GeometryHydrostaticsCalculator` exists as a backward-compatible wrapper (not a separate solver). The hydrostatics validator attempts a best-effort “resources → compile → geometry → hydrostatics” path and falls through to the legacy path on exceptions (`magnet.physics.validators.HydrostaticsValidator._try_geometry_hydrostatics`).

### Resistance estimation (models and validity ranges)

MAGNET uses a regime-based router in validation (`magnet.physics.validators.ResistanceValidator`) to choose an empirical model depending on speed regime.

Define Froude number:

\[
Fn = \frac{V}{\sqrt{g L}}
\]

where \(L\) is a characteristic length (typically \(L_{WL}\) or \(L_{OA}\) depending on available data).

#### Displacement / semi-displacement: Holtrop-Mennen (empirical)

For lower \(Fn\), MAGNET uses Holtrop-Mennen style estimation (`magnet.physics.resistance`).

Core structure (simplified):

- Frictional resistance:
  \[
  R_F = \tfrac{1}{2}\rho V^2 S\,C_F
  \]
- ITTC ’57 friction line:
  \[
  C_F = \frac{0.075}{(\log_{10} Re - 2)^2},
  \quad Re = \frac{V L}{\nu}
  \]
- Total resistance is friction plus form factor and residual components:
  \[
  R_T \approx (1+k)\,R_F + R_{residual} + R_{appendages} + \cdots
  \]

Validity notes:

- Empirical; sensitive to correct wetted surface \(S\), form factors, and hull fullness.
- For semi-displacement transition regimes, uncertainty increases materially.

Practical early-stage accuracy expectation (order-of-magnitude):

- **Displacement regime**: often within \(\pm 15\%\) to \(\pm 25\%\) when geometry inputs are reasonable and within model calibration ranges.
- **Semi-displacement**: commonly \(\pm 20\%\) to \(\pm 30\%\) depending on slenderness, transom immersion, and appendage assumptions.

MAGNET is expected to surface warnings when operating near/outside regime assumptions, rather than silently claiming precision.

#### Planing: Savitsky-style model (empirical/analytical hybrid)

For higher-speed craft, MAGNET uses Savitsky-style planing estimation (`magnet.physics.savitsky`).

Planing models solve for running trim \(\theta\) and wetted length ratio \(\lambda\) such that lift balances weight and moments balance about CG. A simplified view:

- Lift balance:
  \[
  L(\theta,\lambda,\beta, V, B) \approx W
  \]
- Moment balance:
  \[
  M(\theta,\lambda, x_{CG}, \ldots) \approx 0
  \]
- Total resistance includes viscous + pressure components; effective power:
  \[
  P_E = R_T\,V
  \]

Validity notes (typical for Savitsky-style methods):

- Assumes planing surface behavior and specific deadrise ranges.
- Sensitive to CG location, deadrise \(\beta\), beam \(B\), and loading.
- Outside calibration (very low/high deadrise, unconventional bottoms), errors can be large.

Practical early-stage accuracy expectation:

- **Planing regime**: commonly \(\pm 20\%\) to \(\pm 35\%\) unless inputs are well-characterized (CG, wetted geometry, appendages), which early stages often are not.

### Stability metrics

MAGNET’s intact stability pipeline uses:

- Metacentric height estimation (`magnet.stability.intact_gm`).
- Righting arm curve estimation (`magnet.stability.gz_curve`), currently using a declared approximation.
- Free surface correction for slack tanks (`magnet.stability.free_surface`).

#### GM and free surface correction

Basic relationship:

\[
GM = KB + BM - KG
\]

Where \(BM\) comes from hydrostatics:

\[
BM_T = \frac{I_T}{\nabla}
\]

Free surface correction (FSC) is applied as a reduction to effective GM:

\[
GM_{corrected} = GM - FSC
\]

Free surface correction is computed via the free surface moment (FSM) of each slack tank:

\[
FSC = \frac{\sum FSM_k}{\Delta}
\]

where \(\Delta\) is displacement (weight). The FSM depends on the free surface second moment of area of the liquid surface, scaled by fluid density (as implemented in `magnet.stability.free_surface`).

#### GZ curve (righting arm) and declared limitations

MAGNET currently uses the wall-sided approximation in `magnet.stability.gz_curve` (explicitly documented in-code as approximate). A common form used:

\[
GZ(\phi) \approx GM \sin(\phi) + \frac{BM}{2}\tan^2(\phi)\sin(\phi)
\]

Declared limitation:

- Validity is limited (commonly acceptable only to moderate heel angles; MAGNET explicitly degrades confidence beyond ~40° heel in implementation).
- Mesh-derived GZ integration is not implemented in this stage (the more authoritative approach would integrate buoyancy shifts directly from geometry at each heel).

This is intentionally “good enough to detect gross instability” but not “good enough for certification”.

### Power and propulsion estimation

MAGNET derives power requirements from resistance and a simplified propulsive chain:

- Effective power:
  \[
  P_E = R_T V
  \]
- Delivered power at propulsor:
  \[
  P_D \approx \frac{P_E}{\eta_H \eta_R \eta_O}
  \]
  where \(\eta_H\) is hull efficiency, \(\eta_R\) relative rotative efficiency, \(\eta_O\) open-water/propulsor efficiency (for waterjets, a different efficiency model applies).
- Brake power:
  \[
  P_B \approx \frac{P_D}{\eta_{mech}}
  \]

In early-stage tools, these efficiencies are often assumed or weakly inferred; therefore power and fuel estimates should be treated as approximate.

Fuel consumption and capacity are derived from:

- Specific fuel consumption (SFC) assumption:
  \[
  \dot{m}_{fuel} \approx SFC \cdot P_B
  \]
- Range/endurance:
  \[
  t \approx \frac{m_{fuel}}{\dot{m}_{fuel}},
  \quad R \approx V_c\,t
  \]

MAGNET’s implementation splits this across:

- `magnet.performance.predictor` (speed-power curves / envelope-level predictions).
- `magnet.systems.propulsion.system` (propulsion components and aggregate power/weight/fuel rates).
- `magnet.systems.fuel.generator` (fuel system sizing with reserve margins).

### Weight estimation (limitations and impact on stability uncertainty)

Early-stage weight is a dominant uncertainty driver for stability because \(KG\) is rarely known accurately before arrangement and scantlings are real. In MAGNET:

- Weight estimates are parametric and derived from principal dimensions, materials, and coarse system selections; they are suitable for iteration but not for certification-level stability.
- \(KG\) (VCG) is often assumed or heuristically estimated in early phases. This means that **even if geometry-derived \(BM\) is accurate, \(GM\) uncertainty is typically dominated by \(KG\)**:
  \[
  GM = KB + BM - KG
  \]

Review implication: treat small changes in reported \(GM\) as potentially within the \(KG\) uncertainty band unless a detailed weight study has been performed and recorded.

### Accuracy bands (±15–25%) and why

MAGNET’s “±15–25%” band is only plausible under specific conditions (and wider bands are common):

- **Hydrostatics** from compiled geometry can be relatively tight if sections are reasonable and integration resolution is sufficient (often better than resistance).
- **Resistance** is the dominant uncertainty because empirical models are regime-specific and sensitive to parameters that are not well known early (appendages, roughness, transom immersion, spray, CG, trim).
- **Stability** depends critically on KG and tank states. If KG is assumed, stability metrics are only as good as that assumption.

Therefore MAGNET’s stance should be:

- Provide numeric outputs with explicit confidence notes and regime warnings.
- Treat these outputs as **guidance** for iteration, not certification-level truth.

---

## Design Spiral and State Evolution

### How each iteration updates the unified state

An iteration in MAGNET is a transactionally safe cycle:

1. **Propose**: user intent or agent proposal produces actions and/or a geometry program.
2. **Validate**: actions are checked against schema, bounds, units, and locks; geometry programs are checked against geometry contracts.
3. **Apply**: validated mutations are applied within a transaction; `design_version` increments on commit.
4. **Compile geometry**: state resources are compiled into `HullGeometry` (authoritative when the design language path is used successfully).
5. **Run validators**: hydrostatics/resistance/stability validators compute outputs and attach findings.
6. **Persist & render**: outputs and metadata are stored; the visualization pipeline requests geometry at a chosen LOD.

This is orchestrated by the kernel conductor (`magnet.kernel.conductor`), which determines when to execute program generation versus legacy synthesis and manages phase progression.

### What changes automatically vs what requires human intervention

Automatic changes (kernel-owned) include:

- Unit normalization and bounds clamping (with warnings).
- Deterministic geometry compilation normalization (resampling, ordering), with transform reports.
- Running physics validators and writing derived metrics to state.

Human intervention is required when:

- The system reaches a “human decision point” (e.g., severe stability failures, negative freeboard, nonphysical results). The conductor sets flags (e.g., awaiting human decision) to pause automation.
- Conflicts arise between locked parameters and required feasibility adjustments.
- The agent proposes changes that are rejected due to schema/lock/regime violations.

### Convergence vs exploration tradeoffs

MAGNET deliberately supports both:

- **Exploration**: allow larger changes and accept that physics outputs are approximate; use warnings to avoid obviously invalid regions.
- **Convergence**: tighten constraints (locks, narrower bounds, higher-quality geometry resolution) and reduce degrees of freedom.

The unified state plus provenance tracking supports this:

- Values can be marked as user-provided vs agent-proposed vs synthesized vs kernel-derived, enabling more disciplined convergence when needed.

---

## 3D Generation & Visualization

### Purpose: communication, not manufacturing

MAGNET’s 3D output is intended to:

- Communicate hull form and major features.
- Support rapid iteration (visual sanity checks, stakeholder review).
- Provide export formats for downstream workflows (GLB/OBJ/STL), with explicit caveats.

It is not intended to replace final CAD/production drawings without additional constraints and verification.

### How geometry is converted to meshes or renders

Key pipeline components:

- **Geometry service**: `magnet.webgl.geometry_service.GeometryService` is the single entry point. It selects data sources, enforces geometry mode (authoritative vs visual-only), manages LOD, and caches results.
- **Adapters**: `magnet.webgl.geometry_adapter` converts kernel `HullGeometry` into WebGL-friendly interfaces.
- **Tessellation**: `magnet.webgl.geometry_pipeline` converts sections/surfaces into triangle meshes (`MeshData`: vertices, indices, normals).
- **API layer**: `magnet.webgl.api_endpoints` exposes endpoints for hull meshes, full scenes, binary payloads, and exports.

Mesh generation details that matter technically:

- **Hard edges**: `EdgeType` on section points is used to split normals so chines/knuckles render correctly (and are not smoothed away).
- **Multi-body**: bodies are tessellated with care to avoid topology corruption (e.g., separate port/starboard vertex grids), because naive mirroring can create degenerate triangles or incorrect index stitching.
- **LOD**: geometry can be tessellated at different resolutions for interactive performance vs higher-quality exports.

### CAD-style studio renders (lighting, views, intent)

The viewer (UI/WebGL) renders:

- The tessellated mesh with materials and lighting.
- Optional overlays (waterlines, section cuts, hydrostatic “visuals”).

Some visual aids are explicitly representative (not authoritative), for example hydrostatic visuals that may be generated from high-level parameters rather than from full geometry integration (depending on the implementation path).

### Explicit statement of what is not dimensionally authoritative

MAGNET distinguishes:

- **AUTHORITATIVE geometry**: derived from compiled design-language resources and used for physics evaluation. This is the geometry that downstream engineering calculations should reference within MAGNET’s fidelity scope.
- **VISUAL_ONLY geometry**: parametric fallback or approximations used when authoritative geometry is unavailable or disallowed. This must not be used for engineering decisions without explicit acknowledgement.

This boundary is enforced in the WebGL/geometry service layer via an explicit geometry mode (see `magnet.webgl.schema.GeometryMode`) and “allow visual-only” flags on API requests (see `magnet.webgl.api_endpoints`). The intended invariant is: engineering-critical consumers do not receive approximations unless they explicitly opt in.

Additionally, even authoritative meshes are not production CAD:

- Tessellation introduces discretization error; sharp edges are represented via normals and topology conventions, not exact CAD edges.
- Exports (STL/OBJ/GLB) are **representations** suitable for visualization and early prototyping, not guaranteed watertight solids with manufacturing tolerances.

---

## Failure Modes and Guardrails

### Where the system can break

MAGNET’s failure modes cluster into:

- **Input/intent failures**: underspecified or contradictory requirements (e.g., “500 kts, 2 m draft, 2000 nm range”).
- **Geometry failures**: invalid sections (self-intersections, wrong ordering), inconsistent point counts, insufficient sections for lofting, discontinuities that cannot be compiled consistently.
- **Physics failures**: models used outside regime, missing/assumed inputs (KG, CG, appendages), nonphysical outputs (negative GM, negative displacement).
- **Visualization failures**: degenerate triangles, NaN normals, topology corruption due to bad mirroring or section mismatches.

### Geometry that passes compilation but fails physics

This is expected and is part of the design spiral:

- A hull can be geometrically valid yet have insufficient displacement at target draft.
- A hull can meet displacement but have unstable GM given assumed KG.
- A hull can be stable but require unrealistic power at target speed.

MAGNET’s correct behavior is:

- Compile successfully (if geometry is structurally valid).
- Run physics validators and emit explicit findings/warnings.
- Pause or request human decision when failures are severe or safety-critical.

### Physics models used outside their regime

Empirical models are not universal. Guardrails include:

- Regime selection (e.g., Fn-based routing between Holtrop and Savitsky).
- Warnings when key nondimensional parameters are out of calibration bounds.
- Confidence degradation (e.g., heel-angle confidence in wall-sided GZ).

When the system lacks the data required to assert regime applicability, it must:

- Report increased uncertainty, not false precision.

### Agent hallucination risks and how MAGNET constrains them

MAGNET constrains agents via layered defenses:

- **Protocol firewall**: the agent cannot directly mutate state; only validated `ActionPlan`s can.
- **Whitelist schema**: only refinable paths can be modified, with type/unit/bounds enforcement (`REFINABLE_SCHEMA`).
- **Stale-plan detection**: proposals built on old state versions are rejected to prevent race-condition corruption.
- **Geometry contracts**: geometry programs must satisfy strict contracts (section point format, counts, allowed primitives). Invalid programs are rejected before compilation.
- **Transactional execution**: all updates apply atomically or not at all; partial mutations are rolled back.

These defenses are designed so that “hallucination” results in a rejection + explanation, not silent state corruption.

---

## Why This Architecture Scales

### Combinatorial explosion via continuous geometry + composition

MAGNET scales by moving from “choose from a finite set” to “compose from primitives”:

- Continuous parameters yield a high-dimensional design space without requiring pre-enumeration.
- Composition supports feature combinations without exponentially growing a preset library.

The cost shifts from maintaining \(2^M\) templates to maintaining:

- A small, well-defined set of primitives.
- A deterministic compiler.
- Validators that operate on constructed geometry (and therefore generalize across forms).

### Why novelty is preserved

Novelty is preserved because:

- The system does not coerce intent into a nearest “type” by construction.
- Physics is computed from the resulting geometry, not from categorical assumptions.

Novel forms may still fail physics (and should), but they are not prevented from being represented.

### Why validation after generation is the critical unlock

Validation-after-generation decouples:

- The representation (what the hull is) from
- The evaluation (how it performs).

This avoids the legacy trap where evaluation assumes the hull must belong to a known family. MAGNET instead asks: “given this geometry, what do the estimators say?” and then iterates.

---

## Future Extensions

### Current implementation status (for reviewers)

| Component | Status | Notes |
|-----------|--------|-------|
| Geometry compilation | Implemented | Design-language resources compile to `HullGeometry` |
| Hydrostatics (geometry-derived) | Implemented | Polygon clipping + Green’s theorem + Simpson/trapezoid integration |
| Hydrostatics (legacy parametric) | Implemented (deprecated) | Fallback only; should be treated as approximate |
| Stability (GM) | Implemented | Depends on \(KG\) assumptions; FSC supported |
| Stability (GZ curve) | Approximate | Wall-sided formula with confidence degradation at larger heel angles |
| Resistance (Holtrop-Mennen) | Implemented | Validity depends on envelope; uncertainty increases near edges |
| Resistance (Savitsky-style) | Implemented | Empirical/iterative; uncertainty often higher in early stages |
| Multi-body hydrostatics | Implemented | Parallel axis combination; body count derived from geometry |
| 3D pipeline authoritative vs visual-only | Implemented | `GeometryMode` + explicit “allow visual-only” request gating |

### Higher-fidelity solvers

Planned or natural extensions include:

- Mesh-based hydrostatics and stability at heel (replacing wall-sided GZ with geometry-derived buoyancy integration).
- Higher-fidelity resistance and seakeeping tools (panel methods, RANS/CFD), with explicit interfaces so outputs can be attached to state as higher-confidence evidence.

### CAD export

To become manufacturing-relevant, MAGNET would need:

- Watertight solid modeling constraints.
- Tolerance management.
- Feature-level parametrization consistent with CAD kernels (NURBS surfaces with continuity controls).

Exports should carry metadata indicating geometry mode (authoritative vs visual-only), LOD, and compile transforms to maintain auditability.

### Yard-specific constraints

Shipyards impose constraints (plate forming limits, allowable curvature, frame spacing norms). MAGNET can represent these as:

- Additional validators (constraints) that run on compiled geometry and structure state.
- Parameter locks and tighter bounds in refinable schema.

### Regulatory checks

Regulatory frameworks (IMO intact stability criteria, class rules) can be integrated as:

- Explicit gate checks in the conductor’s phase machine.
- Validator outputs with traceable criteria computations and declared applicability limits.

The key design requirement is auditability: each regulatory check must record inputs, assumptions, and computed margins in state, not just a pass/fail flag.

