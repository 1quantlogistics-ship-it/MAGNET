# Geometry Visualization Breakage — Trace, Diagnosis, Suggested Fix (No Code Changes Yet)

## Observed symptom (from UI screenshot)
- Hull shows **surface tearing / pinching / “exploded” facets** (especially around the stern/transom edge and along one side).
- The shape is **much improved** (Viking-ish), but the rendered mesh has **local topology artifacts** that read like broken triangulation rather than “wrong hull intent”.

## Strongest evidence in the runtime logs
The WebGL tessellation path is **explicitly detecting degenerate triangles**:
- `webgl.geometry_pipeline` logs: **“Degenerate triangles detected: N”**

This is a *rendering mesh* quality error (triangle area ~ 0), not a physics/intent coupling error.

## Trace: where the breakage is detected (but not prevented)

### 1) Degenerates are counted after tessellation
`HullGeometryPipeline._tessellate_from_sections(...)` builds the mesh and then calls `_count_degenerate_triangles(mesh)` and logs if any are found — but **does not remove them** before returning the mesh.

File: `magnet/webgl/geometry_pipeline.py`
- The mesh build + detection happens after all sides + end caps are triangulated.
- The resulting mesh is returned even if degenerates exist.

### 2) The degenerate detector is “area-based” (good) but used only for logging
`_count_degenerate_triangles(...)` checks:
- duplicate indices (trivial degenerates)
- **near-zero area** (actual failure mode)

File: `magnet/webgl/geometry_pipeline.py`
- `_compute_triangle_area(...)`
- `_count_degenerate_triangles(...)`

### 3) End-cap triangulation is a likely source of sliver/zero-area triangles
`_triangulate_end_cap(...)` constructs “bathtub” end-walls via **port → centerline** and **centerline → starboard** strips.

Key risk:
- It creates new centerline vertices at `y = 0.0` (`builder.add_vertex(x, 0.0, z)`).
- This is correct only if the body’s centerline is actually `y=0`.
- Even for monohulls, if port/starboard seam points are very close to centerline, the midpoint strip can create extremely thin triangles near the keel or near the sheer.

File: `magnet/webgl/geometry_pipeline.py`
- `_triangulate_end_cap(...)` “centerline vertices aligned to the section curve”

### 4) Mesh/schema validation currently checks only duplicate-index degenerates
`validate_mesh_data(mesh)` flags a triangle if `(a==b or b==c or a==c)` but **does not check near-zero area** degeneracy.

File: `magnet/webgl/schema.py`
- `validate_mesh_data(...)` “Check for degenerate triangles”

This means the system can “pass” the validation helper while still producing zero-area triangles (exactly the failure mode being logged by `_count_degenerate_triangles`).

## What this most likely is (high confidence)
This is **WebGL tessellation robustness** (triangle generation) rather than a deeper kernel geometry bug:
- The kernel produced plausible geometry (your screenshot confirms the macro-form improved).
- The pipeline itself acknowledges **degenerate faces**.
- Degenerate faces will:
  - explode normals / produce hard shading seams
  - create “paper-thin spikes”
  - cause z-fighting or flicker
  - potentially break watertightness assumptions for downstream visual checks

## Probable root causes (ranked)

### A) End-cap centerline construction creates near-zero-area triangles
Especially when:
- port/starboard points are nearly coincident (keel region)
- a section already contains (or nearly contains) centerline points
- station spacing is tight and the end-cap forms a narrow “fan”

### B) Point-count mismatch and `min(n_curr, n_next)` strip triangulation creates slivers
`_triangulate_hull_side(...)` skins using the **minimum point count** between adjacent sections.
When adjacent sections differ materially in spacing/shape, the strip can generate:
- long skinny triangles (poor aspect ratio)
- near-colinear triangles (area ~ 0)

### C) Centerline assumption `y=0.0` is wrong for multi-body and can be wrong for offset bodies
Even if you’re testing monohulls right now, this is a latent bug:
- the end-cap code uses `y=0.0` rather than a per-body `centerline_y`.
This can generate “bridges” or twisted caps if a body is not centered at y=0.

## Suggested fix (minimal, safe, and *purely visualization* oriented)

### Fix 1 (must-do): Skip degenerate triangles during mesh build
Implement one of:
- **A) In `MeshBuilder.add_triangle(...)`**:
  - if indices are not unique → skip
  - if triangle area < `EPSILON_MESH` → skip
- **B) Post-process in `MeshBuilder.build(...)`**:
  - filter out degenerate faces from `indices` before normals/uvs

Why this is safe:
- It does not change the kernel geometry.
- It removes triangles that are “mathematically meaningless” (zero-area) and only harm rendering.

### Fix 2 (should-do): Use per-body centerline in `_triangulate_end_cap(...)`
Change centerline vertex creation from:
- `builder.add_vertex(x, 0.0, z)`
to:
- `builder.add_vertex(x, centerline_y, z)`

Implementation detail:
- Either pass `centerline_y` into `_triangulate_end_cap(...)`, or
- derive it once in `_tessellate_from_sections(...)` and keep it alongside the section index lists.

This closes the known multi-body failure mode and reduces sliver risk even for monohulls (by consistent seam placement).

### Fix 3 (nice-to-have): Upgrade `validate_mesh_data(...)` to include area-based degenerate checks
Mirror `_compute_triangle_area` logic (bounded to first N faces to keep it cheap), so validation utilities match the actual failure mode.

## How to verify the fix (acceptance criteria)

### Manual
- Re-run the same Viking prompt.
- Expected:
  - no visible “exploded” or tearing triangles
  - no transom/keel spikes

### Log-level
- `Degenerate triangles detected: N` should become **0** (ideal) or at least drop to a negligible count.

### Test-level (recommended follow-up)
- Add a focused unit/integration test that:
  - runs tessellation for a representative “warped deep‑V” hull
  - asserts `_count_degenerate_triangles(mesh) == 0`

## Risk assessment (whether this is “deeper/more concerning”)
- **Most likely not deeper**: current evidence points to a mesh-generation artifact, not a kernel truthfulness failure.
- **But it can become truth-affecting** if you later use the rendered mesh for invariants (volume parity, watertightness) without filtering degenerates.

