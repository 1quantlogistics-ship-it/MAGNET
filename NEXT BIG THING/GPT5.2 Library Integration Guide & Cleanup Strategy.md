## GPT5.2 Library Integration Guide & Cleanup Strategy

**Repository**: MAGNETV1 (`/Users/bengibson/MAGNETV1`)  
**Date**: 2026-01-25  
**Scope**: Integrate off-the-shelf libraries to accelerate geometry/physics/optimization/visualization **without violating MAGNET North Star invariants** (agents propose, kernel judges; novelty from continuous parameters × compositional operators × physics validation; canonical transactional state; no prescriptive enums/families inside kernel).

---

## 0) North Star guardrails (integration “constitution”)

### 0.1 Non‑negotiables

- **Kernel remains a validation oracle**  
  - Kernel/validators may call libraries to **compute** reality checks (hydrostatics, resistance, mesh validity), but must not contain **design suggestion logic** (“this looks like a patrol hull”, “use a bulbous bow”).
- **Novelty stays continuous + compositional**  
  - Libraries must enable: continuous parameterization, compositional operators (loft/boolean/attach), and physics validation—**not enumerated hull families**.
- **State is canonical, transactional, observable**  
  - Persist library-specific objects **nowhere** in `DesignState`. Persist only MAGNET-native primitives (arrays, dataclasses, schemas).  
  - All library integration happens behind **adapters** with deterministic conversions.
- **No new prescriptive enums**  
  - If a library introduces categories (e.g., “hull types”), keep them in UI labels or post-hoc classifiers—never as kernel decision switches.
- **Always degradable**  
  - Every integration must support: **feature flag**, **graceful optional import**, and **fallback** to current implementation (for demo reliability and CI stability).

### 0.2 Layering rules (where code may live)

| Layer | May call 3rd‑party libs? | Must NOT do | Typical integration pattern |
|---|---:|---|---|
| `magnet/kernel/` | Yes (for validation orchestration), but conservatively | embed domain heuristics or prescriptive families | “Kernel calls validators; validators call adapters.” |
| `magnet/physics/` | Yes | turn into design recommender | “Physics method registry: empirical vs BEM.” |
| `magnet/hull_gen/` | Yes (geometry math), but output stays MAGNET-native | persist library objects in state | “Generate control points/sections; adapters export.” |
| `magnet/webgl/` | Yes (mesh utilities), but output stays MeshData/GLB | rewrite kernel state | “Mesh repair/volume checks via adapters.” |
| `magnet/optimization/` | Yes | mutate committed state during eval | “Surrogate/pareto engines operate on cloned state.” |
| `app/`, `magnet/ui_v2/` | Yes (JS libs) | become source of truth | “Viewer/rendering is downstream of state.” |

---

## 1) Current readiness (what’s already “good enough”)

From `CORTEX_V2_IMPLEMENTATION_GUIDE.md` + project status:

- **Core spiral loop is wired**: generate → blend → classify → guarded edit → hybrid optimize → revalidate (tests green).  
- **Optimization architecture already exists**: `magnet/optimization/surrogate_model.py`, `surrogate_optimizer.py`, `hybrid_optimizer.py`, `surrogate_trainer.py`.  
- **NURBS is already MAGNET-native**: `magnet/hull_gen/nurbs.py` provides `NURBSCurve` / `NURBSSurface`.  
  - Therefore `geomdl` is **not** “add NURBS to MAGNET”; it’s “use a mature CAD/NURBS ecosystem for IO/fairing while keeping MAGNET’s NURBS schema canonical.”

Implication: integrations should target **acceleration and quality** (robust mesh operations, better manifold projection, better multi-objective optimization, better CAD IO) while preserving invariant tests and end-to-end behavior.

---

## 2) Library intake matrix (actionability, Feb 15 demo impact, North Star fit)

**Legend**:  
- **Actionability now**: feasible to integrate safely in current repo without architectural churn (High/Med/Low).  
- **Demo impact**: effect on MVP / Feb 15 demo (High/Med/Low).  
- **North Star fit**: Compatible / Compatible-with-constraints / Conflicts.  

| Library / unlock | Actionability now | Demo impact | North Star fit | Licensing / build risk | Primary touchpoints |
|---|---|---|---|---|---|
| **trimesh** | High | High | Compatible | Permissive (MIT); pure Python | `magnet/webgl/geometry_service.py`, `magnet/webgl/*`, conversion helpers |
| **manifold3d** | Med | Med | Compatible-with-constraints | C++ build + platform friction; confirm license/version | `magnet/webgl/*` (repair/booleans), optional in blend projection |
| **hypothesis** | High | Med (stability confidence) | Compatible | Permissive (MPL 2.0); test-time only | `tests/` additions, invariant fuzzing |
| **BoTorch** | Med | Med | Compatible-with-constraints | PyTorch stack versions; GPU optional | `magnet/optimization/surrogate_model.py` backend swap, acquisition |
| **pymoo** | High | High | Compatible | Apache-2.0 | `magnet/optimization/pareto.py` (extend), `optimization/schema.py` |
| **umap-learn** | Med | Low–Med | Compatible-with-constraints | numba build perf; **inverse not reliable** | `magnet/bootstrap/manifold_blending.py` (for retrieval/viz more than decode) |
| **PaCMAP** *(requested)* | Med | Low | Compatible-with-constraints | inverse not standard; mostly embedding | same as UMAP (viz/retrieval) |
| **geomdl** | Med | Med | Compatible-with-constraints | Permissive (MIT); stable | CAD IO + fairing adapters around `magnet/hull_gen/nurbs.py` |
| **Capytaine** | Low–Med | Med | Compatible (but heavy) | **GPL-3.0** (commercial risk); physics complexity | new optional physics backend under `magnet/physics/` |
| **WaveBEM** | Low | Low (for Feb 15) | Compatible (heavy) | LGPL; C++/deal.II ecosystem | `magnet/physics/` time-domain path (future) |
| **hydroblast** | Med | Med | Compatible | MIT; quality varies | `magnet/physics/` calculators consolidation (optional) |
| **GenCAD** | Low | Low–Med | Compatible-with-constraints | research code; model weights; ops burden | new agent “visual input” path; not kernel |
| **FreeCAD Ship Workbench** | Low | Med | Compatible-with-constraints | LGPL; headless FreeCAD is fragile | `magnet/webgl/exporter.py` (STEP/IGES), import pipeline |
| **xeokit-sdk** | Med | High (viewer polish) | Compatible | MIT; frontend integration | replace/augment `magnet/ui_v2/js/scene-manager.js` |
| **CGAL** | Low | Low | Compatible-with-constraints | dual GPL/commercial: **licensing gate**; build complexity | geometry kernel “power tools” (future) |
| **pymanopt** | Low–Med | Low | Compatible | BSD-3; depends on autograd frameworks | advanced differentiable geometry/optimization (future) |
| **Vessel.js** | Med | Med | Compatible | MIT | frontend conceptual naval tools; optional complement to WebGL UI |
| **Ray** | Med | Med | Compatible | large dep; cluster ops | parallel optimization batch evaluation |
| **Modal** | Low–Med | Low–Med | Compatible-with-constraints | cloud dependency; infra | offload heavy physics/opt runs |
| **Plotly Dash** | Med | Med | Compatible | MIT | trade-off dashboards; demo-friendly |
| **LangChain** | Low | Low | Compatible-with-constraints | architecture risk (over-orchestration) | agent orchestration (optional) |
| **Guidance** | Med | Med | Compatible | MIT | constrained generation of DSL/proposals (LLM-side) |
| **Great Expectations** | Med | Low | Compatible | Apache-2.0 | data/state QA checks (CI + design store) |
| **MkDocs Material** | High | Med | Compatible | MIT | docs site |
| **Read the Docs** | Med | Low | Compatible | hosted ops | publishing docs |
| **OpenFGA** | Low | Low | Compatible | Apache-2.0; service ops | enterprise authZ (future) |
| **OPA** | Low | Low | Compatible-with-constraints | Go binary + policy ops | policy gates (future) |
| **LlamaIndex / Haystack / LangMem / Mem0 / MechRAG** *(from analysis)* | Med | Med | Compatible-with-constraints | product/infra complexity | context + retrieval (agent layer; must not become SSOT) |
| **Pinecone / Weaviate** *(from analysis)* | Low–Med | Med | Compatible-with-constraints | hosted DB; ops | vector search for similar vessels (agent assist) |
| **DVC / Pachyderm / LakeFS** *(from analysis)* | Low | Low | Compatible-with-constraints | infra heavy | design dataset lineage/versioning |
| **FoundationDB / BadgerDB** *(from analysis)* | Low | Low | Compatible-with-constraints | deep infra | transactional state store (future) |
| **Automerge / Yjs** *(from analysis)* | Med | Med | Compatible-with-constraints | frontend CRDT design | multi-agent / collaborative UI |
| **jq / JMESPath** *(from analysis)* | Med | Low–Med | Compatible | small deps | formal state lens query language |
| **OpenSCAD / ImplicitCAD / libigl / FreeFEM / MFEM** *(from analysis)* | Low | Low | Compatible-with-constraints | large compute/build | long-horizon geometry/physics expansion |
| **ShipGen / Query2CAD / CQAsk** *(from analysis)* | Low–Med | Low | Compatible-with-constraints | model+ops; CAD runtime | AI-to-CAD workflows (future) |
| **SurrealDB / Chaos Monkey** *(from analysis)* | Low | Low | Compatible-with-constraints | ops | enterprise scale/resilience |

---

## 3) Phased implementation plan (with cleanup, migration, verification, effort)

### Phase 1 — Immediate stability & quality wins (fast ROI, demo-safe)

**Goal**: Make geometry truthfulness + validity checks more robust, remove hand-rolled mesh math, and harden invariants with property testing—without changing the design spiral semantics.

| Item | Why now | What you ship by Feb 15 | Main risk | Effort |
|---|---|---|---|---|
| **trimesh** | Replace fragile hand-rolled mesh volume and add reliable mesh checks | More trustworthy “AUTHORITATIVE vs DECOUPLED” integrity, better export health | conversion correctness; perf | 1–2 days |
| **manifold3d (optional)** | Robust manifold repairs/booleans for “watertight or bust” | Better boolean ops + watertight repair in hard edge cases | C++ build friction | 2–5 days |
| **hypothesis** | Catch edge-case degeneracies before demo; future-proof refactors | Property-based invariant battery: volume>0, no NaNs, stable GM | test runtime; strategy design | 1–3 days |

#### 3.1 trimesh integration (detailed)

##### 3.1.1 Applicability / invariants fit

- **Fit**: Excellent. `trimesh` is a geometry utility; it does not encode domain prescriptions.  
- **Invariant support**: watertightness, volume sign/consistency, self-intersections (via collision/mesh checks), component counts, repair operations.
- **North Star**: Use in **validation + truthfulness checks**, not to decide “what hull” to build.

##### 3.1.2 Where it touches the codebase (confirmed)

- **Manual volume parity block to replace**: `magnet/webgl/geometry_service.py`  
  - Volume parity block begins at **line 456** and includes a manual `_mesh_volume_m3` implementation at **lines 475–495**.  
  - This is exactly the cleanup target the analysis flagged.

##### 3.1.3 What old code is kept / replaced / deleted (exact target)

- **Keep (business rule / invariants)**:
  - “If `SimulationIntegrity.AUTHORITATIVE` but mesh volume materially disagrees with `hull.displacement_m3`, downgrade integrity.”  
  - Metadata emission (`mesh_volume_m3`, `physics_displacement_m3`, `volume_parity_rel_error`) and the conservative downgrade to `DECOUPLED`.
- **Replace**:
  - Replace `_mesh_volume_m3` manual tetrahedralization sum with `trimesh.Trimesh(...).volume`.
- **Delete**:
  - Delete the manual triangle loop in `geometry_service.py` lines **475–495**:
    - the per-triangle cross product,
    - the `total += ... / 6.0` accumulation,
    - the `abs(total)` conversion.

##### 3.1.4 Migration plan (API/data-flow)

- **Add an adapter**, don’t leak trimesh types:
  - Proposed new module: `magnet/geometry/trimesh_adapter.py`
  - Functions:
    - `to_trimesh(mesh: MeshData) -> trimesh.Trimesh`
    - `volume_m3(mesh: MeshData) -> float`
    - `repair(mesh: MeshData) -> MeshData` *(optional; behind feature flag)*
- **Minimal change surface**:
  - Update only the volume calculation inside `GeometryService.get_scene()` parity check; keep metadata schema stable.

##### 3.1.5 Backtrack risk / refactor needed

- **Low**: This is a localized substitution.  
- **Backtrack plan**: feature flag `MAGNET_TRIMESH_ENABLED=0` keeps current logic (but you should still delete the manual volume code once confidence is high—see Cleanup section).

##### 3.1.6 Verification (tests + invariants)

- **New unit test**: `tests/webgl/test_geometry_service_volume_parity_trimesh.py`
  - Construct a simple watertight cube mesh with known volume, ensure parity metric matches.
  - Ensure downgrade triggers when displacement is perturbed.
- **Invariants to assert**:
  - **Volume>0** for watertight meshes.
  - **No NaNs** in `scene.metadata` numeric fields.
  - **No change** to state mutation semantics (this is a read-only check).

##### 3.1.7 Effort estimate

- **1–2 days** including adapter + tests, assuming dependency pinning is straightforward.

---

#### 3.2 manifold3d integration (optional in Phase 1; often Phase 2)

##### 3.2.1 Applicability / invariants fit

- **Fit**: Good *if used as an optional “repair/boolean engine”*.  
- **North Star constraint**: Use manifold ops for **geometry correctness** (watertightness, boolean composition), not for “design family” reasoning.

##### 3.2.2 Where it touches the codebase

- **Primary**: `magnet/webgl/` mesh processing stage (repair, boolean composition for attachments/openings when you move beyond diagnostic markers).  
- **Secondary**: `magnet/bootstrap/manifold_blending.py` projection step (only if you adopt mesh-based manifold projection rather than param-space contraction).

##### 3.2.3 What is kept / replaced / deleted

- **Keep**:
  - Parameter blending API and deterministic projection behavior.
- **Replace (optional)**:
  - Replace “param-space line search projection” with “mesh-based projection” only if you can keep determinism and performance acceptable.
- **Delete**:
  - None immediately; this is additive/optional for Phase 1.

##### 3.2.4 Backtrack risks

- **Build friction** is the big risk. Treat it as **optional dependency** with runtime detection and hard fallback.

##### 3.2.5 Verification

- Add a “repair and preserve volume within tolerance” test on a deliberately broken mesh.

##### 3.2.6 Effort estimate

- **2–5 days** (mostly build + CI + platform support).

---

#### 3.3 hypothesis integration (Phase 1)

##### 3.3.1 Applicability / invariants fit

- **Fit**: Excellent. Property-based tests strengthen the “kernel judges reality” contract by finding degenerate cases humans won’t enumerate.

##### 3.3.2 Where it touches the codebase

- Add new test modules only (no runtime code required).

##### 3.3.3 Verification targets (recommended invariant suite)

- **Geometry invariants**:
  - Tessellation produces finite vertices/indices, indices in range.
  - Mesh volume positive when watertight.
  - No self-intersection flags for basic hulls (where expected).
- **Physics invariants**:
  - Hydrostatics: displacement \(>0\), waterplane area \(>0\), wetted surface \(>0\).
  - Stability: \(GM>0\) for “stable” labeled results (or else must emit warnings and fail relevant validator).

##### 3.3.4 Effort estimate

- **1–3 days** (most time is designing good strategies and capping runtime).

---

### Phase 2 — Blending & optimization upgrades (Pareto, better surrogate engines)

**Goal**: Improve exploration/optimization quality while preserving transactional state + kernel validation. Deliver “engineering/CFO trade-off” UX for the demo: **Pareto fronts with explanations**.

| Item | Why now | Feb 15 demo value | Main risk | Effort |
|---|---|---|---|---|
| **pymoo** | True multi-objective optimization (naval design is never single-objective) | “Engineer vs CFO” views: speed vs fuel vs GM vs cost | objective definition discipline | 2–5 days |
| **BoTorch** | Better surrogate learning + acquisition toolkit | faster convergence / fewer expensive validations | PyTorch dependency conflicts | 4–10 days |
| **UMAP / PaCMAP (for retrieval/viz, not decode)** | Better similarity search of library seeds; better UI embedding | “show similar hulls” demo UX | no inverse transform | 2–5 days |
| **Ray (optional)** | parallel eval for multi-objective | faster Pareto generation | infra + determinism | 2–7 days |

#### 3.4 pymoo integration (recommended for Feb 15)

##### 3.4.1 Applicability / invariants fit

- **Fit**: Excellent. Multi-objective search is an optimizer; kernel remains judge.
- **North Star**: The optimizer proposes candidates; the kernel validates them. No prescriptive hull types required.

##### 3.4.2 Where it touches the codebase

- `magnet/optimization/pareto.py` (exists per architecture doc): extend to use pymoo algorithms (NSGA-II/III).  
- `magnet/optimization/schema.py`: ensure objective list + constraints are explicit and serializable.  
- `magnet/core/state_manager.py` / transactional eval paths: ensure each candidate evaluation is on a clone/snapshot (no SSOT corruption).

##### 3.4.3 Migration plan

- Keep existing optimization interfaces; add a backend selector:
  - `optimizer_backend = "native" | "pymoo"`
- Define objective functions purely from **state lens outputs**:
  - engineering: minimize resistance at cruise, maximize GM margin, minimize draft (if required), maximize payload margin
  - finance: minimize cost estimate, minimize fuel burn proxy, maximize ROI proxy

##### 3.4.4 Verification

- Tests:
  - “Pareto set contains non-dominated points.”
  - “All returned candidates satisfy hard constraints (no negative displacement, GM>0, no NaNs).”

##### 3.4.5 Effort estimate

- **2–5 days** depending on how much UI you want around Pareto visualization.

---

#### 3.5 BoTorch integration (optional for Feb 15; valuable soon after)

##### 3.5.1 Applicability / invariants fit

- **Fit**: Good if used strictly as a surrogate backend behind the existing `SurrogateModel` contract.  
- **North Star**: Surrogate suggests where to look; kernel/physics decides what’s real.

##### 3.5.2 Where it touches the codebase (confirmed)

- Current surrogate model lives at `magnet/optimization/surrogate_model.py`.  
  - It currently uses sklearn’s `GaussianProcessRegressor` + Matern kernel (lines 30–82).  
- It is used by:
  - `magnet/optimization/hybrid_optimizer.py`
  - `magnet/optimization/surrogate_optimizer.py`
  - `magnet/optimization/surrogate_trainer.py`

##### 3.5.3 What old code is kept / replaced / deleted

- **Keep (contract)**:
  - `fit(X, y)`
  - `predict(X) -> (mean, std)`
  - `compute_gradient(x)` fallback
  - `acquisition_value(x, best_y, exploration_weight)`
- **Replace (backend)**:
  - Replace sklearn GPR with BoTorch `SingleTaskGP` + posterior standard deviation.
- **Delete (once migrated)**:
  - `sklearn.gaussian_process` import try/except blocks and sklearn-only kernel setup.

##### 3.5.4 Migration plan

- Add backend selector inside `SurrogateModel`:
  - `backend="sklearn" | "botorch"`
- Implement BoTorch path returning numpy arrays to preserve call sites.
- Keep numerical gradient as default; optionally use autograd gradient when enabled (but keep deterministic seed policy).

##### 3.5.5 Backtrack risk

- **Medium**: Torch versioning conflicts can disrupt the environment. Make it optional and CI-gated.

##### 3.5.6 Verification

- Re-run existing surrogate tests + add:
  - “BoTorch backend predicts finite stddev.”
  - “Backend swap does not change optimizer API.”

##### 3.5.7 Effort estimate

- **4–10 days** including dependency resolution and performance benchmarking.

---

#### 3.6 UMAP / PaCMAP integration (honest constraints)

##### 3.6.1 What it’s good for in MAGNET

- **Good**: similarity search over hull library seeds; visualization embeddings; clustering for “show me like this hull.”  
- **Not good** (for your current blending API): reversible encode/decode. UMAP inverse transform is not generally well-defined; PaCMAP is similarly not “invertible” by default.

##### 3.6.2 Recommended use in MAGNET (North Star compatible)

- Use embeddings to **select** seeds and neighborhoods; keep blending in parameter space or PCA latent space.
- Add:
  - `HullLibrary.similar(hull_id, k)` using embedding neighbors (optional).

##### 3.6.3 Where it touches the codebase

- `magnet/bootstrap/hull_library.py` (for embedding storage)
- `magnet/bootstrap/manifold_blending.py` (for neighborhood restriction, not decode)

##### 3.6.4 Effort estimate

- **2–5 days** for embedding pipeline + retrieval, excluding dataset packaging.

---

### Phase 3 — Geometry & physics “revolution” (bigger accuracy gains, bigger risks)

**Goal**: CAD-grade surfaces and higher-fidelity hydrodynamics, while keeping MAGNET’s state canonical and validator boundaries clean.

| Item | Why it matters | Feb 15 demo value | Main risk | Effort |
|---|---|---|---|---|
| **geomdl** | STEP/IGES IO + fairing/loft utilities; use a mature NURBS ecosystem | CAD export / “pro-grade surface” story | conflict with existing MAGNET NURBS if done wrong | 1–3 weeks |
| **hydroblast** | consolidate classic naval calcs (sanity checks, reporting) | stronger “naval architect credibility” | correctness + duplication with existing physics | 1–2 weeks |
| **Capytaine** | BEM hydrodynamics for wave interaction / frequency-domain | credibility for grant/demo (if shown as optional) | **GPL-3**, heavy compute, model assumptions | 2–6 weeks |
| **WaveBEM** | time-domain nonlinear potential flow | not needed for Feb 15 | major integration complexity | 6–12+ weeks |

#### 3.7 geomdl integration (do **not** replace MAGNET NURBS schema)

##### 3.7.1 Reality check: MAGNET already has NURBS

- MAGNET defines `NURBSCurve` and `NURBSSurface` in `magnet/hull_gen/nurbs.py`.
- Therefore, `geomdl` should be integrated as:
  - **IO + utility layer** (fitting, fairing, export/import),
  - while the canonical representation remains MAGNET-native.

##### 3.7.2 Where it touches the codebase

- Canonical geometry: `magnet/hull_gen/nurbs.py`
- Program compiler already supports NURBS sections: `magnet/kernel/stdlib/section_compiler.py` references `NURBSCurve`.
- WebGL tessellation remains: `magnet/webgl/geometry_pipeline.py`

##### 3.7.3 Migration plan (safe path)

- Add `magnet/geometry/geomdl_adapter.py`:
  - `from_magnet_curve(curve: NURBSCurve) -> geomdl.Curve`
  - `to_magnet_curve(geomdl_curve) -> NURBSCurve`
  - `export_step(surface: NURBSSurface) -> bytes` *(if supported via downstream toolchain; otherwise IGES or intermediate)*
- Store only control points/knots/degree in state, never geomdl objects.

##### 3.7.4 Backtrack risk

- **Medium**: CAD export chains can become fragile; keep it optional and “best effort” for demo.

##### 3.7.5 Verification

- Round-trip tests:
  - MAGNET NURBS → geomdl → MAGNET NURBS (within tolerance).
- Surface fairness metrics (optional):
  - curvature continuity sanity checks.

##### 3.7.6 Effort estimate

- **1–3 weeks** depending on how deep you go into STEP/IGES workflows.

---

#### 3.8 Capytaine integration (brutal honesty)

##### 3.8.1 North Star fit

- **Conceptually fits**: kernel validates physics, Capytaine provides a stronger physics oracle.  
- **Operational fit**: heavy compute and modeling assumptions; must be optional and clearly labeled.

##### 3.8.2 Licensing red flag

- Capytaine is **GPL-3.0** (per analysis). If MAGNET is intended for closed-source/commercial distribution, this is a **hard legal gate**.  
  - Mitigation: isolate Capytaine as an **external service** with a clean boundary (separate process/repo) so MAGNET core is not a derived work. Still needs legal review.

##### 3.8.3 Where it touches the codebase

- Add a new optional backend under `magnet/physics/`:
  - `magnet/physics/hydrodynamics/capytaine_backend.py`
  - integrate via `physics/validators.py` as “high fidelity method” whose outputs are fed into uncertainty + validity envelope logic.

##### 3.8.4 Migration plan

- Keep existing empirical methods (Holtrop/Savitsky) as default.
- Add capability flags in state:
  - `physics.hydrodynamics.method = "empirical" | "capytaine"`
  - plus explicit uncertainty fields when using empirical outside envelope.

##### 3.8.5 Verification

- “Capytaine backend never mutates state; only returns results.”
- “If unavailable, system falls back with explicit uncertainty messaging.”

##### 3.8.6 Effort estimate

- **2–6 weeks** including geometry-to-panelization pipeline, compute budgets, caching, and licensing strategy.

---

### Phase 4 — Advanced unlocks (visual inputs, bidirectional CAD, enterprise viewer)

**Goal**: “Upload CAD → insights → retrofits → exports” workflow and demo polish: pro viewer, optional CAD round-tripping, optional visual references.

| Item | Demo value | Biggest risk | Effort |
|---|---|---|---|
| **xeokit-sdk** | High (viewer polish, large CAD) | frontend integration complexity | 1–2 weeks |
| **FreeCAD Ship Workbench** | High (round-trip CAD story) | headless FreeCAD fragility | 2–6 weeks |
| **GenCAD** | Med (wow factor) | research model ops | 4–10+ weeks |
| **Query2CAD / CQAsk** | Med | CAD runtime integration | 2–8 weeks |
| **Vessel.js** | Med | scope creep | 1–3 weeks |
| **OpenFGA / OPA** | Low (demo), high (enterprise) | infra + policy design | 4–12 weeks |

#### 3.9 xeokit-sdk integration (recommended for demo polish)

##### 3.9.1 North Star fit

- Viewer only: downstream of state, no kernel impact. Great fit.

##### 3.9.2 Where it touches the codebase

- `magnet/ui_v2/js/scene-manager.js` is the current custom viewer integration point (called out in the analysis).

##### 3.9.3 Migration plan

- Introduce a viewer adapter layer:
  - `magnet/ui_v2/js/viewer-adapter.js`
  - swap implementation: Three.js scene manager vs xeokit viewer.
- Keep glTF/GLB export contract unchanged (`magnet/webgl/serializer.py` / exporter path).

##### 3.9.4 Verification

- E2E check: upload/design → render → viewer loads GLB, camera controls work, materials render correctly.

##### 3.9.5 Effort estimate

- **1–2 weeks** depending on desired UI polish.

---

#### 3.10 FreeCAD Ship Workbench integration (bidirectional CAD)

##### 3.10.1 North Star fit

- Fits if treated as an **external editor** and MAGNET remains canonical.  
- Rule: FreeCAD edits come back as **imports** that are re-validated by kernel; no direct kernel “trust” of external CAD.

##### 3.10.2 Where it touches the codebase

- Export path:
  - `magnet/webgl/exporter.py` currently supports glTF/GLB/STL/OBJ (per architecture). Add STEP/IGES as optional export format (or a parallel exporter).
- Import path:
  - new ingestion module (likely under `magnet/deployment/` endpoints or `magnet/loading/`), producing MAGNET primitives (sections/surfaces) and re-running validators.

##### 3.10.3 Migration plan

- Start with **one-way export** (demo-safe).  
- Then add “round-trip” with constraints:
  - import must map back to canonical section/surface representation; if it cannot, store as a referenced artifact and mark geometry as `DECOUPLED` until reparametrized.

##### 3.10.4 Biggest risks

- Headless FreeCAD can be brittle; version mismatches; platform-specific behavior.

##### 3.10.5 Effort estimate

- **2–6 weeks**.

---

#### 3.11 GenCAD / visual CAD generation (research unlock)

##### 3.11.1 Reality check

- Great “wow,” but high operational risk (model weights, determinism, safety).
- Must live in agent layer and produce **proposals** only; kernel still validates.

##### 3.11.2 Migration plan

- Treat as external “proposal generator”:
  - input: image → candidate geometry program (MAGNET DSL)
  - output: a proposal that goes through existing `ActionPlanValidator` firewall.

##### 3.11.3 Effort estimate

- **4–10+ weeks**.

---

## 4) Cleanup analysis (per library: obsolete inventory, kept logic, net impact)

### 4.1 trimesh

| Category | What | File(s) / lines | Action |
|---|---|---|---|
| **Obsolete code** | Manual mesh volume tetrahedralization | `magnet/webgl/geometry_service.py` **475–495** | **Delete**; replace with adapter call |
| **Kept logic** | Volume parity “silent killer defense” and integrity downgrade | `magnet/webgl/geometry_service.py` **456–507** | Keep rule; replace volume computation only |
| **New code** | MeshData↔trimesh conversion + volume helper | *(new)* `magnet/geometry/trimesh_adapter.py` | Add |
| **Net impact (est.)** | -25 to -40 LOC manual math; +40 to +120 LOC adapter/tests | repo-wide | Favor clarity + tests |

### 4.2 manifold3d

| Category | What | File(s) / lines | Action |
|---|---|---|---|
| **Obsolete code (if replacing PCA entirely)** | PCA latent build for blending | `magnet/bootstrap/manifold_blending.py` **24, 61–77** | Replace with manifold method only if build+perf acceptable |
| **Kept logic** | Deterministic projection toward anchor | `magnet/bootstrap/manifold_blending.py` **102–125** | Keep conceptual behavior (projection), even if implementation changes |
| **New code** | Optional “mesh repair/booleans” utilities | *(new)* `magnet/geometry/manifold_adapter.py` | Add behind feature flag |
| **Net impact (est.)** | varies | | Treat as optional |

### 4.3 hypothesis

| Category | What | File(s) | Action |
|---|---|---|---|
| **Obsolete code** | none | — | — |
| **Kept logic** | existing unit/integration tests | `tests/` | Keep |
| **New code** | property strategies + invariant tests | *(new)* `tests/strategies/geometry_strategies.py`, `tests/invariants/test_geometry_properties.py` | Add |
| **Net impact (est.)** | +200–600 LOC tests | | Acceptable (testing-only) |

### 4.4 BoTorch

| Category | What | File(s) / lines | Action |
|---|---|---|---|
| **Obsolete code (post-migration)** | sklearn GP backend imports/config | `magnet/optimization/surrogate_model.py` **30–38, 54–83** | Replace with BoTorch backend (optional), then remove sklearn-only code if desired |
| **Kept logic** | SurrogateModel contract + numerical gradient fallback | `magnet/optimization/surrogate_model.py` **41–138** | Keep, extend |
| **Net impact (est.)** | +150–400 LOC + deps | | Biggest risk is dependency conflicts |

### 4.5 pymoo

| Category | What | File(s) | Action |
|---|---|---|---|
| **Obsolete code** | “single point optimum only” assumptions | `magnet/optimization/*` | Refactor to allow Pareto sets |
| **Kept logic** | objective extraction from state + validator calls | `magnet/optimization/` | Keep |
| **New code** | NSGA-II/III backend + decision tools | `magnet/optimization/pareto.py` | Add |
| **Net impact (est.)** | +200–800 LOC | | High leverage |

### 4.6 umap-learn / PaCMAP

| Category | What | File(s) | Action |
|---|---|---|---|
| **Obsolete code** | none directly | — | — |
| **Kept logic** | PCA-based reversible latent blending | `magnet/bootstrap/manifold_blending.py` | Keep for decode |
| **New code** | embedding + neighbor retrieval | `magnet/bootstrap/hull_library.py` + new embedding store | Add (optional) |
| **Net impact (est.)** | +200–700 LOC + data mgmt | | Use for retrieval, not decode |

### 4.7 geomdl

| Category | What | File(s) | Action |
|---|---|---|---|
| **Obsolete code** | none (NURBS already exists) | — | — |
| **Kept logic** | MAGNET-native `NURBSCurve` / `NURBSSurface` | `magnet/hull_gen/nurbs.py` | Keep canonical |
| **New code** | geomdl adapter + export/import utilities | *(new)* `magnet/geometry/geomdl_adapter.py` | Add |
| **Net impact (est.)** | +300–1200 LOC depending on IO scope | | Moderate risk |

### 4.8 Capytaine / WaveBEM / hydroblast

| Library | Obsolete code likely | Kept code | Net impact | Biggest risk |
|---|---|---|---|---|
| **Capytaine** | parts of empirical hydrodynamics *only if you choose to deprecate them* | existing validators + uncertainty surfacing | +1000s LOC + caches | **GPL-3** + compute + geometry prep |
| **WaveBEM** | none (new capability) | existing physics for fallback | large | time-domain complexity |
| **hydroblast** | potentially duplicates existing calculators | existing physics + validators as SSOT | medium | correctness validation |

### 4.9 GenCAD / FreeCAD Ship / xeokit / Vessel.js / Query2CAD / CQAsk

| Library | Cleanup impact | Kept invariants | Net impact | Biggest risk |
|---|---|---|---|---|
| **xeokit** | none (frontend swap) | “viewer is downstream” | medium JS changes | frontend integration |
| **FreeCAD Ship** | may supersede ad-hoc STEP handling | kernel revalidation always | large | headless CAD fragility |
| **GenCAD** | none | kernel firewall + validation | large | model ops |
| **Query2CAD/CQAsk** | none | proposals only | medium | CAD runtime |
| **Vessel.js** | none | state is SSOT | medium | scope creep |

### 4.10 Enterprise / infra ecosystem (OpenFGA, OPA, DVC, LakeFS, etc.)

These are **not Feb 15 demo-critical** and should be treated as separate, opt-in tracks to avoid destabilizing MAGNET’s core loop.

---

## 5) Concrete “what to change first” checklist (demo-oriented)

### 5.1 Phase 1 (week 1)

- **Add `trimesh` adapter + replace manual volume**  
  - Replace `magnet/webgl/geometry_service.py` `_mesh_volume_m3` (lines **475–495**) with `trimesh` volume.
- **Add hypothesis invariants**  
  - Property tests around tessellation + hydrostatics sanity invariants.
- **(Optional) Add basic mesh validity metrics to metadata**  
  - `is_watertight`, `euler_number`, `component_count`—strictly as observability.

### 5.2 Phase 2 (weeks 2–3)

- **Add `pymoo` Pareto optimizer** producing:
  - 10–50 candidate designs on a Pareto front
  - each candidate annotated with physics validator outputs and a short “why it’s on the front”
- **Add “engineer vs CFO” view**:
  - engineer: GM margin, resistance, draft, compliance flags
  - CFO: fuel proxy, cost proxy, schedule proxy (if available)

### 5.3 Phase 3+ (post-demo)

- Start geomdl export adapters.
- Decide Capytaine path only after licensing strategy is confirmed.

---

## 6) Risk register (be brutal)

| Risk | Why it matters | Mitigation | Severity |
|---|---|---|---|
| **GPL contamination (Capytaine, CGAL GPL mode)** | can block commercialization | isolate as external service; legal review; prefer permissive alternatives | **High** |
| **C++ build fragility (manifold3d, CGAL)** | breaks CI and dev onboarding | optional deps; prebuilt wheels; containerized builds | High |
| **Embedding methods not invertible (UMAP/PaCMAP)** | cannot replace reversible blend | use for retrieval/viz only | Med |
| **Torch dependency conflicts (BoTorch)** | breaks environment quickly | optional backend; pinned lockfile; CI matrix | Med–High |
| **Performance regressions** | demo latency, “feels broken” | benchmarks + budgets; decimate meshes before heavy ops | Med |
| **State leakage via optimizers** | corrupts SSOT/invariants | enforce clone/snapshot evaluation; fail-fast | **High** |
| **CAD round-trip fidelity** | imported geometry may not map to canonical primitives | import as artifact → reparametrize → only then canonicalize | Med–High |

---

## 7) Strategic positioning (Metal Shark / “Chris” demo + retrofit + grants)

### 7.1 The product story these integrations enable

**Upload CAD → instant truthfulness report → retrofit suggestions → Pareto trade-offs → export + paper trail**

- **Upload CAD** (now: GLB/OBJ/STL; soon: STEP/IGES via geomdl/FreeCAD chain)
- **Instant baseline** (Phase 1):
  - robust mesh volume + watertightness checks (trimesh)
  - transparent “AUTHORITATIVE vs APPROXIMATE vs DECOUPLED” integrity labeling
- **Retrofit suggestions** (Phase 2):
  - multi-objective Pareto front exploration (pymoo)
  - keep kernel as oracle: every suggested tweak is validated
- **Executive + engineering views**:
  - engineer sees constraints + stability/resistance envelopes
  - CFO sees cost/fuel/ROI deltas
- **Grant / credibility** (Phase 3):
  - optional high-fidelity hydrodynamics backend (Capytaine/WaveBEM) presented honestly as “high-fidelity mode,” with explicit uncertainty tracking and licensing clarity

### 7.2 Why this is defensible

- **Competitors optimize in black boxes**; MAGNET’s differentiator is **canonical state + validation receipts**.  
- Libraries improve compute, but the moat is: **proposal → transaction → validation → traceability**, not any single solver.
- **Retrofit wedge**: the existing fleet is huge; “make this hull 5–10% better” + “show me the trade-offs” sells faster than “generate brand new hulls.”

### 7.3 Demo script (Feb 15)

- Import / generate a baseline hull
- Show viewer (xeokit optional) with integrity badge:
  - mesh volume vs physics displacement parity
- Ask for two competing intents:
  - “reduce fuel at cruise” vs “maximize payload while keeping GM margin”
- Generate a Pareto front (pymoo) and show two highlighted points:
  - “engineer favorite” vs “CFO favorite”
- Export geometry + a lightweight report with receipts (what changed, why, and which validators passed)

---

## Appendix A — Confirmed cleanup targets in current code (for implementers)

### A.1 Manual volume parity code to replace (trimesh)

- `magnet/webgl/geometry_service.py`
  - Volume parity block: **456–507**
  - Manual `_mesh_volume_m3`: **475–495**

### A.2 Current manifold blending implementation (PCA + anchor contraction)

- `magnet/bootstrap/manifold_blending.py`
  - PCA dependency: `from sklearn.decomposition import PCA` (line **24**)
  - PCA fit: (lines **61–63**)
  - Projection method: `project_to_validity` (lines **102–125**)

### A.3 Current surrogate model backend (sklearn GP)

- `magnet/optimization/surrogate_model.py`
  - sklearn backend import (lines **30–38**)
  - `GaussianProcessRegressor` initialization (lines **77–82**)

### A.4 MAGNET-native NURBS (canonical)

- `magnet/hull_gen/nurbs.py`
  - `NURBSCurve`, `NURBSSurface` are already present; treat geomdl as an adapter layer.

