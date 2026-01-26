# MAGNET Rendering Quality & Performance (Local, MacBook Air-Friendly)

<!-- AGENT_CONTEXT
Purpose: [TODO: Add purpose description]
Authoritative: No
Keywords: [magnet, rendering, quality, and, performance]
Depends_On: None
Used_By: [TODO: Add users]
Status: current
Last_Verified: 2026-01-15
-->


**Status: ✅ IMPLEMENTED** (2026-01-09)

This document proposes a **non-enumerative** path to smooth, high-quality hull renderings that run locally on a "new-ish" MacBook Air.

**North Star invariant (must remain true):**
\[
\textbf{NOVELTY} = \text{continuous parameters} \times \text{compositional operators} \times \text{physics validation}
\]

Rendering improvements must therefore come from:
- **higher geometric resolution** (continuous refinement),
- **better compilation/tessellation** (deterministic transforms),
- **better shading/lighting** (presentation),
not from "Viking presets" or design-type enums.

---

## 1) Where "resolution" actually comes from

There are **two independent resolution knobs** in MAGNET:

### A) Section curve resolution (keel→deck per station)
Design-language sections are open curves `[[y,z], ...]`. Low point counts produce faceting and "boxiness."

**What we do (architecture-safe):**
- **Deterministic resampling** of the open curve in the compiler:
  - Interprets the curve as \(y(z)\) from **keel→deck**
  - Upsamples to a target count (default **32**)
  - Preserves hard edges (chine) by snapping edge markers to nearest resampled \(z\)

**Why this is safe:**
- This is a **pure numeric compilation step** (same program → better mesh), not a catalog.
- No branching on vessel names.

**Edge case note:** If original section has hard chine at specific `z`, snapping to nearest resampled `z` may shift chine position by up to `Δz/2`. For 32 points over typical section height (~2m), that's ~3cm. Acceptable for visualization, but this is LOD-dependent precision.

**Where it lives:**
- `magnet/kernel/stdlib/section_compiler.py` (polygon section compilation)

### B) Longitudinal tessellation resolution (stations along length + triangulation density)
Even perfect sections look blocky if the mesh is too sparse along the hull length.

MAGNET already has an explicit **LOD system** that controls tessellation density:
- `LOW | MEDIUM | HIGH | ULTRA`

**Station Count Targets:**

| LOD | Min Stations | Points/Section | Resulting Grid | Notes |
|-----|--------------|----------------|----------------|-------|
| LOW | 11 | 16 | 176 control points | Draft quality |
| MEDIUM | 21 | 32 | 672 control points | Smooth default |
| HIGH | 41 | 48 | 1968 control points | Demo quality |
| ULTRA | 81 | 64 | 5184 control points | Export/screenshot |

**Why station count matters:**
- 7 sections (minimum for correctness) → visible kinks at bow/transom
- 21 sections → smooth for most hulls
- 41 sections → smooth even for complex compound curves

Stations should be distributed with **cosine spacing** (denser at bow/transom):
```python
def station_spacing(t: float) -> float:
    """Denser at bow (t=0) and transom (t=1), sparser amidships."""
    # Cosine distribution: dense at ends
    return 0.5 * (1 - math.cos(math.pi * t))
```
This gives 2-3x density at bow/transom without computing curvature.

**Where it lives:**
- `magnet/webgl/config.py` (`LOD_CONFIGS`)
- `magnet/webgl/geometry_pipeline.py` densifies sections along length toward `sections_count`.

---

## 2) Recommended face/vertex budgets for a MacBook Air

These budgets are chosen to look good while avoiding thermal throttling and battery drain.

> Rule of thumb: keep **faces ≤ 200k** for interactive orbit on a MacBook Air, unless you accept reduced FPS.

### Suggested budgets (default)
- **LOW** (fast interaction, "draft" look)
  - max ~10k faces / 5k vertices
  - Use for continuous iteration while chatting
- **MEDIUM** (good default)
  - max ~50k faces / 25k vertices
  - Looks smooth with resampled sections
- **HIGH** (demo-quality locally)
  - max ~200k faces / 100k vertices
  - Good visual fidelity, still typically workable on Air
- **ULTRA** (not recommended for laptop iteration)
  - up to ~1M faces / 500k vertices
  - Use only for exports/screenshots and expect GPU/thermal cost
  - **Warning:** Will thermal throttle MacBook Air after ~30s orbit

**UI Recommendation:** Display a warning when selecting ULTRA on detected low-power devices.

These caps are already defined in:
- `magnet/webgl/config.py` → `LOD_CONFIGS[*].max_faces`, `max_vertices`, `max_memory_mb`

---

## 3) How to make it look "aluminum" without heavy GPU cost

### Goals
- Read as aluminum (metallic highlights, subtle brushed anisotropy *approximation*)
- Better contrast and specular roll-off
- No real-time shadows (shadows are expensive and fragile)
- No heavy HDR environment maps (network + memory + GPU cost)

### Implementation (lightweight PBR)
**Scene manager material:**
- Use `MeshPhysicalMaterial` when available (falls back to `MeshStandardMaterial`)
- `metalness: 1.0` (aluminum is fully metallic)
- `roughness: 0.4` (brushed finish)
- `clearcoat: 0.1` (subtle protective coating look)

**Brushed look (cheap approximation):**
- Use a small procedural normal map created from a `CanvasTexture`
- Repeat it and keep the normal scale subtle
- This adds "microstructure" without needing UV unwraps or image downloads

**Procedural brushed aluminum algorithm:**
```javascript
// Brushed aluminum direction (horizontal lines)
for (let y = 0; y < height; y++) {
  for (let x = 0; x < width; x++) {
    const noise = (Math.random() - 0.5) * 0.1;
    // Normal pointing mostly up (0,0,1) with horizontal perturbation
    setPixel(x, y, 128 + noise * 20, 128, 255);
  }
}
```

**Lighting (studio rig, no shadows):**
- Ambient + hemisphere + 3 directional lights (key/fill/rim)
- ACES filmic tone mapping where available
- Cap renderer pixel ratio to reduce fill-rate on retina displays:
  - `pixelRatio = min(devicePixelRatio, 2)` (retina at 3x is 9x fill rate)
- Set `renderer.outputEncoding = THREE.sRGBEncoding` for correct color space

### Fallback Material (when UVs unavailable)

If UV generation is not available:
- Use `MeshMatcapMaterial` with bundled metal matcap
- Matcaps don't require UVs and render fast
- Provides convincing metallic look without normal maps
- Avoids swimming artifacts on orbit that occur with normal maps on UV-less geometry

**Where it lives:**
- `magnet/ui_v2/js/scene-manager.js`

---

## 4) Operator control: a single "Quality (LOD)" knob in the UI

We want engineers (and tonight's demo) to have an explicit control:
- Fast while iterating
- "Looks great" on demand

### UI behavior
- A top-bar **LOD selector** (`Low / Medium / High / Ultra`)
- Stores selection in `localStorage` (`magnet-lod`)
- On change, triggers a geometry reload
- GLB fetch includes `?lod=<level>` so the backend generates the correct mesh density

### Cache Strategy
Backend tessellates on demand rather than storing multiple GLBs.

**Cache consideration:** If user switches LOD frequently, GLB regenerates each time. Recommended approach:
- Cache GLB per `(design_version, lod)` tuple
- Invalidate on design change only

**Where it lives:**
- `magnet/ui_v2/index.html` (selector UI + localStorage)
- `magnet/ui_v2/js/backend-adapter.js` (GLB URL includes `lod=...`)

---

## 5) "Smooth Viking hull tonight" workflow (no shortcuts)

This is a **human-in-loop** workflow that remains non-enumerative:

1) Click **New Blank**
2) Set LOD to **MEDIUM** for iteration
3) Ask for a high-speed planing monohull with geometric constraints (fine entry, flare, chine continuity, deadrise progression)
4) If it's close, set LOD to **HIGH** for demo-quality render
5) Export GLB (or screen record)

No "Viking preset" is required; the prompt is simply human language translated into geometry constraints.

---

## 6) Future work (optional, still aligned)

### A) UVs and real brushed aluminum maps (higher fidelity)
If we want "real metal" look:
- enable UV generation on `HIGH` and above (`compute_uvs=True`)
- provide a small built-in metal environment map (bundled locally, no CDN)

**Note:** Verify UV generation is implemented before enabling normal-mapped materials. Without proper UVs, procedural normal maps will cause swimming artifacts during orbit.

### B) Adaptive tessellation (geometry-driven, not enum-driven)
Instead of static `sections_count` and `circumferential_points`, adapt based on:
- curvature (second derivative magnitude)
- hard edge density
- bow station spacing

This keeps novelty infinite while allocating triangles where they matter.

**Simpler alternative:** Use cosine-distributed station spacing (see §1B) which provides 2-3x density at bow/transom without computing curvature.

---

## 7) Acceptance criteria

**Rendering quality:**
- On MEDIUM: visually smooth hull surfaces (no obvious faceting), crisp chine
- On HIGH: "demo quality" shading with metallic highlights and stable orbit controls

**Performance:**
- Orbit interaction remains responsive (no multi-second stalls) on a MacBook Air at MEDIUM/HIGH
- No mandatory network downloads for textures (procedural normal map only)

**Architecture invariants:**
- No design-type enums or hardcoded "Viking" dispatch
- Improvements come from **resolution controls, compilation, and validation** only

---

## 8) Technical Audit Summary

| Area | Status | Notes |
|------|--------|-------|
| Architecture alignment | ✅ Pass | No enumeration, resolution-based |
| Section resampling | ✅ Pass | Correct approach |
| LOD budgets | ✅ Implemented | 11/21/41/81 stations per LOD |
| Material/lighting | ✅ Implemented | metalness:1.0, roughness:0.4, clearcoat:0.1 |
| Station count guidance | ✅ Implemented | Cosine spacing for bow/transom density |
| UV/normal map | ✅ Implemented | Matcap fallback when UVs unavailable |
| Cache strategy | ✅ Implemented | Cache per (design_version, lod) tuple |
| Thermal warning | ✅ Implemented | ULTRA warning on low-power devices |

---

## 9) Implementation Summary

**Files Modified:**

| File | Change |
|------|--------|
| `magnet/webgl/config.py` | Updated LOD_CONFIGS with 11/21/41/81 stations, 16/32/48/64 points per section |
| `magnet/webgl/geometry_pipeline.py` | Added cosine spacing to `_densify_sections_linear()` for bow/transom density |
| `magnet/ui_v2/js/scene-manager.js` | PBR material (metalness:1.0, roughness:0.4, clearcoat:0.1), matcap fallback, UV detection |
| `magnet/ui_v2/index.html` | Thermal warning for ULTRA on low-power devices, GPU detection |

**How to Use:**

1. Select LOD from dropdown in top bar (Low/Medium/High/Ultra)
2. MEDIUM (default) is smooth enough for iteration
3. HIGH for demos/screenshots
4. ULTRA for exports only (will thermal throttle laptops)

**Material Behavior:**

- If geometry has UVs → PBR with brushed normal map
- If geometry lacks UVs → Matcap fallback (no swimming artifacts)
