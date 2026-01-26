# Character Observables Implementation Plan

## Executive Summary

**Problem**: Current observables measure *magnitude* (sheer_rise_m = 2.1), not *shape* (sheer peaks at 72% forward). First-pass hulls are valid but generic—they lack distinctive character.

**Solution**: Add observables that measure WHERE features occur, not just HOW MUCH they vary. When the model targets these on CREATE, the hull emerges with personality, not just correctness.

**Constraints**:
- Use existing observable infrastructure (`OBSERVABLE_REGISTRY` pattern)
- No grammar changes (ADJUST/TARGET already support any `observable_id`)
- No parser changes
- **Observables must be measurable from compiled geometry**
- **Prerequisite**: emit canonical *feature curves* during compilation (so stem/transom/top-edge/bottom-edge are explicit SSOT outputs)
- Phase 1: measurable only (control mappings come later)
- Note: Multi-body vessels (catamarans, etc.) are supported by the underlying geometry pipeline. This plan is **per-body** by construction, but the initial “character score” and target profiles assume a **primary hull body** (typically the main hull).

---

## 0. Feature Curve Extraction (Compiler Prerequisite)

**Why this exists**: Several “character” observables need profile/edge curves (stem rake, stem concavity, transom rake). The geometry already contains the information implicitly, but the system does not emit it as named, stable, measurable feature curves. This step makes those curves **first-class outputs** so **all 12 observables are feasible now**.

### 0.0 CHARACTER_OBSERVABLES_IMPLEMENTATION_PLAN — Unified Technical Audit (Implementation Gate)

This section consolidates all technical, mathematical, and architectural concerns raised during audit. The implementing agent must address each item before the plan is considered complete.

#### Architectural Decision: RESOLVED ✓ — Feature Curve Extraction Method

**Concern raised**: “Do we need WebGL to extract feature curves?”  
**Resolution**: **No.**

The feature curves are already **kernel outputs**: they are first-class fields on `HullGeometry` (see `magnet/hull_gen/geometry.py`):
- `keel_profile: List[Point3D]`
- `stem_profile: List[Point3D]`
- `chine_curve: List[Point3D]`
- `deck_edge: List[Point3D]`
- `transom_outline: List[Point3D]`

**Decision**: Populate these fields **during kernel compilation** (no `webgl/*` dependency).

**Why this matters**: This preserves the correct architecture boundary:

```
kernel compilation → HullGeometry (with stem_profile, keel_profile, chine_curve, transom_outline, deck_edge)
                 ↓
kernel observables measure these
                 ↓
webgl consumes for visualization/export (separate)
```

**Implementation location**:
- Implement curve extraction in `magnet/kernel/stdlib/section_compiler.py` (or a new kernel helper module like `magnet/kernel/feature_curve_extractor.py`)
- Wire into `magnet/kernel/stdlib/compiler.py` immediately after sections are compiled into `HullGeometry`
- Use `magnet/hull_gen/generator.py` as reference SSOT for how these curves should look for parametric hulls (especially `stem_profile` and `transom_outline`)

#### Critical Issues (Must Fix Before Implementation)

1) **Coordinate convention inconsistency (station vs x_position)**
- **Problem**: Code/plan uses `section.station` and `section.x_position` interchangeably without defining the relationship.
- **Fix**: Establish one canonical coordinate system:

```python
# SSOT: x_m is the truth (meters from AP)
x_m = section.x_position  # meters, AP=0, increasing forward

# station_norm is ALWAYS derived from the section set, never stored
#
# IMPORTANT: do NOT assume AP==0. Normalize using x_min/x_max.
x_min = min(s.x_position for s in sections)
x_max = max(s.x_position for s in sections)
x_range = max(1e-9, x_max - x_min)
station_norm = (x_m - x_min) / x_range  # in [0, 1]

# NEVER use section.station unless proven equal to station_norm
```

2) **`entry_half_angle_deg` formula is mathematically wrong**
- **Incorrect**: `atan(half_beam / (LOA - x_m))` computes angle to bow tip, not local half-angle.
- **Correct**: `entry_half_angle_deg = atan(d(half_beam)/dx)` in bow region.

3) **`stem_profile` extraction must use mesh intersection**
- Single-section projection produces constant x → invalid.
- Use y=0 plane intersection in bow region; return ordered (x,z) points.

4) **`chine_line` must preserve y OR explicitly document intentional loss**
- Preferred: store full 3D `[[x,y,z], ...]` (chine is not on centerline).
- If discarding y, document it explicitly and add a planform curve later (do not silently lose information).

5) **`transom_rake_deg` must use mesh intersection or transom plane normal**
- `transom_outline` alone (y,z) cannot define a 3D plane.
- Use transom mesh vertices → best-fit plane → compute rake from plane normal.

#### High-Severity Issues

6) **Remove all invented fallbacks**
- If required curve is missing/degenerate → return `None`.
- Do not read authored “config” fields as a substitute for derived measurement.

7) **`stem_rake_deg` must use correct waterline bracketing**
- Do not pick “two closest to z=0” points (non-local tangent).
- Find adjacent segment that brackets z=0; interpolate crossing; compute local slope.

8) **`deadrise_progression_shape` normalization must be dimensionally correct**
- Existing formula is dimensionally inconsistent.
- Fix options:
  - \(score = clamp(k \cdot LOA^2 / max(span, \epsilon), 0, 1)\), or
  - normalize against a reference curvature \(k_{ref}\) (preferred).

9) **Feature curves require a smoothing pass**
- Mesh-intersection polylines can be jagged; derivatives amplify noise.
- Requirement: feature curves must be **C1-continuous** (smooth first derivative) before derivative-based observables.

#### Medium-Severity Issues

10) **Curvature stencil mismatch**
- Plan says 5-point stencil preferred; ensure implementation matches or update text.

11) **LOA derivation is fragile**
- Do not assume `loa = secs[-1].x_position`.
- Use explicit priority chain (see §1.0 coordinate SSOT).

12) **`chine_rise_rate` units inconsistency**
- Standardize on **m/m** (dimensionless slope).
- Regress on **x_m**, not `station`.

13) **Guard clauses for zero-length chords**
- Avoid divide-by-zero for near-degenerate hull features.

14) **`keel_z_m` metric assumption**
- Ensure `section_metric:keel_z_m` exists or compute inline (min z).

15) **Multi-body policy must be explicit**
- Define `select_primary_body()` and return `None` when ambiguous.

#### Lower-Priority Issues

16) **Perpendicular distance formula must be explicit** (for `stem_concavity_ratio`)

17) **Multi-body observable targeting via `body_id` scope** (already supported; ensure validator accepts it).

#### Additional Critical Issues (From Audit)

18) **`chine_rise_rate` implementation regressed on station, not x_m (example bug)**
- Definition says **m/m**, but regression on `section.station` yields **m/station**.
- **Fix**: Regress `chine_z` vs **x_m** (meters) and filter via derived `station_norm`.

19) **`bow_fineness_ratio` example filtered on `section.station`**
- **Fix**: Derive `station_norm` from `x_position` and filter on that.

20) **`_chine_like_point()` helper referenced but not clearly surfaced**
- Called by multiple observables; must be explicitly defined and easy to find.
- **Fix**: Add a dedicated subsection with the helper (see §3.3).

21) **LOA normalization assumed AP = 0**
- Current failure mode: `station_norm = x_m / LOA` is wrong when x-origin isn’t AP.
- **Fix**: `station_norm = (x_m - x_min) / (x_max - x_min)` (see §1.0).

22) **Primary body selection rule undefined**
- Plan says “select primary body” but must be deterministic.
- **Fix**: Add `select_primary_body()` rule (see §0.2).

23) **Surface/curve availability not guaranteed**
- Plan references “mesh intersection” style extraction in some places, but section compilation may not have a mesh.
- **Fix**: Add an explicit availability contract: if required curve cannot be derived from the compiled representation, emit an empty curve and downstream observables return `None` (honest absence, not a fallback) (see §0.2).

#### Implementation Checklist (Gate)

**Critical (Blocking)**:
- Mesh intersection extraction (Option A) for stem + transom
- Single coordinate SSOT (x_m truth; station_norm derived)
- entry_half_angle_deg uses derivative \(d(half\_beam)/dx\)
- Chine y handling explicit (preserve y preferred)
- No invented fallbacks; return None when missing
- Feature curve smoothing (C1)

**High**:
- Waterline bracketing for stem rake
- Dimensional correctness for deadrise_progression_shape normalization

**Medium/Low**:
- Stencil consistency, LOA derivation chain, unit consistency, guards, keel_z availability, multi-body policy, explicit formulas

### 0.1 Output contract (compiled geometry)

The compiler must emit **both**:
- **Typed curves** on `HullGeometry` (already part of `magnet/hull_gen/geometry.py`):
  - `HullGeometry.stem_profile: List[Point3D]`
  - `HullGeometry.keel_profile: List[Point3D]`
  - `HullGeometry.chine_curve: List[Point3D]`
  - `HullGeometry.deck_edge: List[Point3D]`
  - `HullGeometry.transom_outline: List[Point3D]`
- A JSON-friendly mirror under `geometry.metadata["feature_curves"]`:

```python
{
  "feature_curves": {
    # 3D where applicable (preserve y for non-centerline curves)
    "stem_profile": [[x_m, 0.0, z_m], ...],             # mesh intersection at y=0 in bow region
    "transom_outline": [[x_m, y_m, z_m], ...],          # mesh-derived transom perimeter (3D)
    "sheer_line": [[x_m, y_m, z_m], ...],               # longitudinal top edge (3D)
    "chine_line": [[x_m, y_m, z_m], ...],               # longitudinal chine (3D; uses anchor witness)
    "keel_line": [[x_m, 0.0, z_m], ...]                 # longitudinal bottom edge (typically centerline)
  }
}
```

**Invariants**:
- Curves are **derived**, never authored.
- Curves must be **deterministic** for a fixed set of sections.
- If insufficient data exists for a curve (e.g., fewer than 2 usable sections), return an **empty list** for that curve (and downstream measurers return `None`).

### 0.2 Extraction algorithms (Kernel compilation)

**Input**: compiled `HullSection`s (and their `SectionPoint`s) produced by `section_compiler.py`.  
**Output**: populate the existing `HullGeometry` curve fields (and mirror into `geometry.metadata["feature_curves"]`).

**Curve extraction primitives (required)**:
- `smooth_polyline_c1(points3d) -> points3d` for any derivative-based observable (C1 smoothing)
- `select_primary_body(sections_by_body) -> body_id|None` for multi-body policy

**`smooth_polyline_c1` (reference implementation stub)**:

```python
def smooth_polyline_c1(points: List["Point3D"], *, window: int = 5) -> List["Point3D"]:
    """
    Apply a lightweight C1-style smoothing to a polyline.

    Constraints:
    - deterministic
    - preserves endpoints
    - no mandatory heavy dependencies (numpy/scipy optional)

    Note: This is a plan-level stub. A production implementation may use:
    - Savitzky–Golay (preferred) if available
    - or a simple moving-average fallback (shown here) for plan tests / minimal deps
    """
    pts = list(points or [])
    if len(pts) < max(3, window):
        return pts
    w = max(3, int(window) | 1)  # odd window
    half = w // 2

    def _avg(vals: List[float]) -> float:
        return float(sum(vals) / max(1, len(vals)))

    out: List["Point3D"] = []
    for i in range(len(pts)):
        if i == 0 or i == len(pts) - 1:
            out.append(pts[i])
            continue
        lo = max(0, i - half)
        hi = min(len(pts), i + half + 1)
        xs = [float(p.x) for p in pts[lo:hi]]
        ys = [float(p.y) for p in pts[lo:hi]]
        zs = [float(p.z) for p in pts[lo:hi]]
        out.append(Point3D(x=_avg(xs), y=_avg(ys), z=_avg(zs)))
    return out
```

**Surface / curve availability contract (honesty contract)**:
- Not all compiled representations can provide all curves.
- If a curve cannot be derived deterministically from compiled sections (and no compiled surface/mesh exists to intersect), emit **an empty curve list** for that field.
- Any observable that depends on a missing/empty curve **returns `None`** (no invented fallback).
- If a compiled surface/mesh representation exists and is used for curve extraction, it MUST be treated as an optional input; absence is allowed and must fail-closed.

**IMPORTANT (agent pitfall): do not “guess mesh intersection”**
- This plan does **not** require a WebGL mesh.
- Curve extraction must be implemented **from compiled sections** as the primary method.
- If a future version adds mesh-intersection extraction, it must be behind an explicit capability check (e.g., `geometry.mesh is not None and has_faces`) and must not be invented when unavailable.

**Primary body selection rule (deterministic)**:

```python
def select_primary_body(bodies: Dict[str, Any]) -> Optional[str]:
    """
    Deterministic selection of primary body for character scoring.

    Priority:
    1. Body with id "main_hull" (explicit designation)
    2. Body with largest displaced volume (if available)
    3. First body alphabetically (stable fallback)
    4. None if no bodies
    """
    if not bodies:
        return None
    if "main_hull" in bodies:
        return "main_hull"
    by_volume = sorted(
        bodies.items(),
        key=lambda kv: float((kv[1] or {}).get("displaced_volume_m3", 0.0) or 0.0),
        reverse=True,
    )
    if by_volume:
        return str(by_volume[0][0])
    return sorted(str(k) for k in bodies.keys())[0]
```

**keel_profile / keel_line**:
- For each section: keel point = min z point.
- Append `Point3D(x=section.x_position, y=0, z=keel_z)` (y=0 is appropriate for keel elevation metrics).

**deck_edge / sheer_line**:
- For each section: deck edge point = max z point (preserve its y).
- Append `Point3D(x=section.x_position, y=sheer_y, z=sheer_z)`.
- Apply C1 smoothing before curvature observables.

**chine_curve / chine_line (anchor witness + preserve y)**:
- For each section: find chine anchor using the same anchor method as deadrise (knee detector preferred).
- Append `Point3D(x=section.x_position, y=chine_y, z=chine_z)` (preserve y).
- Persist per-section `witness_index` for stability.
- Apply C1 smoothing for chine rise rate (slope).

**transom_outline**:
- Use aft-most section points as the outline curve in 3D at constant x=aft_x.
- Preserve y and z of section points.

**stem_profile**:
- Populate using a kernel-derived method that produces a meaningful x–z curve (see `magnet/hull_gen/generator.py::_generate_stem_profile` and BowGenerator usage for reference).
- **Do not** use “single-section projection with constant x” for rake/concavity observables.
- If the design-language path cannot infer stem rake from available primitives, the plan must explicitly define the additional authoring or derived rule required (fail-closed; no invented fallback).

### 0.3 Where to implement (file references)

### 0.3 Where to implement (file references)

**Utilities location**:
- Preferred: create `magnet/kernel/feature_curve_extractor.py` (curve extraction + smoothing)
- Acceptable: place helpers in `magnet/kernel/stdlib/section_compiler.py` if you want zero new modules

**Wire-up location**:
- `magnet/kernel/stdlib/compiler.py`: after `HullGeometry.sections` are compiled, populate:
  - `geometry.keel_profile`, `geometry.stem_profile`, `geometry.chine_curve`, `geometry.deck_edge`, `geometry.transom_outline`
  - `geometry.metadata["feature_curves"]` (JSON-friendly mirror)

**Note**: WebGL is a consumer only. Feature curve extraction is a kernel compilation responsibility.

### 0.4 Tests (compiler prerequisite)

Add unit coverage that guarantees the curves are emitted:
- `sheer_line` matches per-section max-z values
- `keel_line` matches per-section min-z values
- `stem_profile` exists and has ≥2 points when ≥1 section exists
- `transom_outline` matches aft-most section points
- `chine_line` uses a stable anchor (does not jump when minor unrelated edits occur if witness available)

---

## 1. Observable Definitions

**Coordinate convention (critical)**:
- **SSOT**: \(x_m\) in meters from AP/aft (increasing forward) — use `section.x_position`
- **Derived only**: \(station\_norm\) is ALWAYS derived from \(x_m\) using the section set:

\[
station\_norm = clamp\left(\frac{x_m - x_{min}}{x_{max}-x_{min}}, 0, 1\right)
\]

Where:
- \(x_{min} = \min(section.x\_position)\)
- \(x_{max} = \max(section.x\_position)\)

- **Rule**:
  - Derivatives / curvature / rates are computed on \(x_m\)
  - `station_range` scoping is done on derived \(station\_norm\)
  - Never use `section.station` unless explicitly proven equal to \(station\_norm\)

**Reference implementation (canonical)**:

```python
xs = [float(s.x_position) for s in sections]
x_min = min(xs)
x_max = max(xs)
x_range = max(1e-9, x_max - x_min)

x_m = float(section.x_position)
station_norm = (x_m - x_min) / x_range
```

**LOA / x-range source priority (for normalization + “bow/aft” distances)**:
1. Prefer explicit `state.hull.loa` (meters) if present and > 0
2. Else use \(x_{range} = x_{max}-x_{min}\) from compiled sections (must be > 0)

**Surface representation guarantee (honesty contract)**:
- Observables that require a longitudinal curve (stem profile, keel line, chine line, sheer line) are only measurable if the compiler can build those curves from the compiled representation.
- If required curves are missing/degenerate, **return None** (no invented fallbacks).

### 1.1 Sheer Curve Shape Observables

#### `longitudinal_metric:sheer_peak_station`
**What it measures**: WHERE the sheer curve reaches maximum height (normalized 0-1).

**Definition**:
```
sheer_peak_station = centroid of the plateau (within 1% of max) in sheer_z_m, expressed in station_norm
```

**Measurement logic**:
1. Compute `sheer_z_m` at each section, keyed by \(x_m\)
2. Let \(z_{max} = max(sheer\_z)\). Define plateau set \(P = {i | sheer\_z_i \ge 0.99 \cdot z_{max}}\)
3. Return the **centroid** of plateau positions: \(station\_norm = mean(x_i)/LOA\) over \(i \in P\)
4. Clamp result to \([0,1]\)

**Viking character**: Peak at ~0.70-0.75 creates the distinctive "teardrop" profile where sheer rises dramatically toward the bow but peaks before the stem.

**Unit**: ratio (0-1)
**Typical range**: 0.65-0.95 (most hulls peak forward)

---

#### `longitudinal_metric:sheer_curvature_peak_station`
**What it measures**: WHERE the sheer curve has maximum curvature (inflection point proxy).

**Definition**:
```
sheer_curvature_peak_station = station_norm at which smoothed curvature |d²(sheer_z)/dx²| is maximum
```

**Measurement logic**:
1. Collect \((x_m, sheer\_z)\) samples, sorted by \(x_m\)
2. Require **≥ 5 sections** (see Stability Contracts). If fewer, return `None`.
3. Smooth or stabilize curvature:
   - Prefer a **5-point stencil** second derivative on approximately uniform spacing, or
   - Fit a light smoothing spline/low-order polynomial first, then differentiate
4. Return \(station\_norm\) at the maximum curvature location, using plateau-centroid handling if the curvature peak is flat/noisy.

**Viking character**: Sharp curvature change at ~0.65-0.70 creates the "shoulder" where the sheer transitions from gentle rise to dramatic sweep.

**Unit**: ratio (0-1)
**Typical range**: 0.50-0.80

---

### 1.2 Stem/Bow Character Observables

#### `profile_metric:stem_rake_deg`
**What it measures**: Angle of stem from vertical at the bow.

**Definition**:
```
stem_rake_deg = angle from vertical of the stem profile at waterline intersection
```

**Measurement logic**:
1. Use mesh-extracted `geometry.stem_profile` (List[Point3D]) (Section 0 prerequisite).
2. Find the **adjacent segment** that brackets waterline \(z=0\):
   - identify consecutive points \((x_1,z_1)\), \((x_2,z_2)\) where \(z_1 \le 0 \le z_2\) (or vice-versa)
   - compute local tangent from that segment (or interpolate exact crossing if desired)
3. Compute rake: \(\text{rake\_deg} = \deg(\atan2(|dx|, |dz|))\)
4. If profile missing/degenerate, return `None` (no invented fallback).

**Viking character**: Moderate rake (10-18°) with slight concave curve creates the aggressive but elegant bow profile.

**Unit**: deg
**Typical range**: 0° (vertical) to 30° (heavily raked)

---

#### `profile_metric:stem_concavity_ratio`
**What it measures**: Curvature of stem profile (clipper bow character).

**Definition**:
```
stem_concavity_ratio = max_perpendicular_distance / chord_length
(chord from stem-head to DWL intersection)
```

**Measurement logic**:
1. Use compiler-emitted `geometry.stem_profile` (List[Point3D]) and operate in the x–z plane (ignore y)
2. Identify:
   - **stem-head** point = point with maximum z in `stem_profile`
   - **DWL intersection** = intersection of the polyline with z=0 (waterline proxy). If no crossing, choose point with smallest |z|.
3. Define chord from stem-head to DWL intersection. Let chord length be \(L\).
4. For each stem profile point between those endpoints, compute perpendicular distance to chord in x–z plane; take max distance \(d_{max}\).
5. Return `stem_concavity_ratio = d_max / max(L, eps)` clamped to [0, 1].
6. If fewer than 3 usable points or non-finite values → return `None`.

**Perpendicular distance formula (explicit)**:
For a point \(P_0=(x_0,z_0)\) to a line through \(P_1=(x_1,z_1)\) and \(P_2=(x_2,z_2)\):
\[
d = \frac{|(z_2-z_1)(x_0-x_1) - (x_2-x_1)(z_0-z_1)|}{\sqrt{(z_2-z_1)^2 + (x_2-x_1)^2}}
\]

**Viking character**: High ratio (0.05-0.15) = aggressive forward reach.

**Unit**: ratio (dimensionless)
**Typical range**: 0.0 (straight) to 0.20 (deeply curved)

---

### 1.3 Entry Sharpness Observables

#### `longitudinal_metric:entry_half_angle_deg`
**What it measures**: Local waterline half-angle of entry in the bow region (how sharp the entry is).

**Definition** (implemented as a longitudinal metric):
\[
entry\_half\_angle\_deg = \deg\left(\atan\left(\frac{d(half\_beam\_m)}{dx_m}\right)\right)
\]
Measured over the forward band (default `station_norm ≥ 0.85`) and summarized as p50.

**Measurement logic**:
This requires neighboring stations; implement as `longitudinal_metric:entry_half_angle_deg`:
1. Build ordered samples \((x_m, half\_beam_m)\) from sections
2. Filter to forward band: `station_norm >= 0.85`
3. Compute local slope via centered differences \(s_i \approx (hb_{i+1}-hb_{i-1})/(x_{i+1}-x_{i-1})\)
4. Convert to angles: \(\deg(\atan(s_i))\)
5. Return p50 over the forward band (fail-closed if insufficient stations)

**Viking character**: Fine entry (8-14°) allows knife-through-waves performance.

**Unit**: deg
**Typical range**: 8° (very fine) to 25° (blunt)

---

#### `longitudinal_metric:bow_fineness_ratio`
**What it measures**: Local beam/length ratio in forward 10% of hull.

**Definition**:
```
bow_fineness_ratio = mean(half_beam) / (0.1 * loa) for stations > 0.9
```

**Measurement logic**:
1. Compute `station_norm` from x-range (never from `section.station`)
2. Filter sections where `station_norm > 0.9`
3. Compute mean `max_half_beam_m` in that region
4. Divide by (0.1 × loa_m) where `loa_m` is the explicit hull LOA if present, else `x_range`

**Viking character**: Low ratio (0.15-0.25) indicates fine, knife-like bow.

**Unit**: ratio (dimensionless)
**Typical range**: 0.10-0.50

---

### 1.4 Transom Character Observables

#### `profile_metric:transom_rake_deg`
**What it measures**: Angle of transom from vertical.

**Definition**:
```
transom_rake_deg = angle from vertical of transom plane
```

**Measurement logic**:
1. Use compiler-emitted `geometry.transom_outline` (Section 0 prerequisite).
2. Fit a plane to the outline points (or a stable x–z proxy if outline is near-constant x), then compute angle from vertical.
3. If outline is missing/degenerate, return `None` (do not invent).

**Viking character**: Moderate rake (10-15°) with clean vertical edges.

**Unit**: deg
**Typical range**: 0° (vertical) to 20° (heavily raked)

---

#### `profile_metric:transom_beam_ratio`
**What it measures**: Transom beam as fraction of maximum beam.

**Definition**:
```
transom_beam_ratio = beam_at_transom / max_beam
```

**Measurement logic**:
1. Get beam at station ≈ 0 (transom)
2. Get maximum beam across all sections
3. Return ratio

**Viking character**: Wide transom (0.80-0.90) provides stability and stern lift.

**Unit**: ratio (dimensionless)
**Typical range**: 0.60-0.95

---

### 1.5 Chine Rise Progression Observables

#### `longitudinal_metric:chine_rise_rate`
**What it measures**: How fast the chine climbs toward the bow (slope).

**Definition**:
```
chine_rise_rate = d(chine_z) / dx_m over forward half (units: m/m), computed on x_m
```

**Measurement logic**:
1. For each station, find chine point from `chine_line` (preferred, derived curve) and preserve its y (planform is real)
2. Pair chine_z with \(x_m\)
3. Filter by derived `station_norm > 0.5` (forward half)
4. Compute slope via regression with \(x_m\) (meters) as the independent variable:
\[
chine\_rise\_rate = \frac{d(chine\_z)}{dx_m}
\]
5. Return slope in **m/m** (dimensionless)

**Viking character**: Aggressive rise creates the distinctive "lifted bow" look.

**Unit**: ratio (m/m)
**Typical range**: 0.01-0.10 (order-of-magnitude; tune from distributions)

---

#### `section_metric:chine_height_ratio`
**What it measures**: Chine height as fraction of sheer height at each station.

**Definition**:
```
chine_height_ratio = (chine_z - keel_z) / (sheer_z - keel_z)
```

**Measurement logic**:
1. Find keel point (min z)
2. Find chine point (geometric anchor near z≈0)
3. Find sheer point (max z)
4. Compute ratio

**Viking character**: Chine at ~0.25-0.35 of section height creates proper planing surface.

**Unit**: ratio (0-1)
**Typical range**: 0.15-0.45

---

### 1.6 Bottom Character Observables

#### `longitudinal_metric:deadrise_progression_shape`
**What it measures**: How “warped” the deadrise progression is (curvature-based, stable).

**Definition**:
```
deadrise_progression_shape = normalized curvature of deadrise_deg(x) over x_m (0 = linear, 1 = strongly warped)
```

**Measurement logic**:
1. Compute `deadrise_deg_at_chine` for each section
2. Collect \((x_m, \beta)\) samples, sorted by \(x_m\)
3. Require **≥ 5 sections**. If fewer, return `None`.
4. Compute stabilized curvature of \(\beta(x)\):
   - Smooth \(\beta\) lightly (median or spline) to reduce sample noise
   - Compute second derivative \(d^2\beta/dx^2\) via 5-point stencil where possible
5. Normalize curvature into a dimensionless \([0,1]\) score (dimensionally consistent):
   - \(span = max(\beta) - min(\beta)\)  (deg)
   - \(k = p95(|d^2\beta/dx^2|)\)       (deg/m²)
   - Option 1: \(score = clamp(k \cdot LOA^2 / max(span, \epsilon), 0, 1)\)
   - Option 2 (preferred): \(score = clamp(k / k_{ref}, 0, 1)\) with explicit \(k_{ref}\)
6. Return `score` (higher = more warp)

**Viking character**: Warped bottom (moderate curvature score) with more deadrise forward.

**Unit**: ratio (0-1)
**Typical range**: 0.0-0.6 (tune empirically)

---

#### `longitudinal_metric:rocker_profile_curvature`
**What it measures**: Curvature of keel profile along length.

**Definition**:
```
rocker_profile_curvature = mean |d²(keel_z)/dx²| over all stations
```

**Measurement logic**:
1. Compute `keel_z_m` for each section
2. Compute second derivative via finite differences
3. Return mean absolute curvature

**Viking character**: Gentle rocker (low curvature) with slight upturn at bow.

**Unit**: 1/m (curvature)
**Typical range**: 0.001-0.05 1/m

---

### 1.7 Controllability Path (How this interacts with ADJUST/TARGET)

Character observables (e.g. `longitudinal_metric:sheer_peak_station`) are **DERIVED** from geometry and are **not directly controllable in Phase 1**.

- **Directly controllable (base) observables** live in the kernel registry today (e.g. `section_metric:sheer_z_m`, `section_metric:max_half_beam_m`, `section_metric:deadrise_deg_at_chine`). These are what ADJUST/TARGET can actuate without solvers.
- **Derived (character) observables** are measured rulers that define “personality,” but require **indirect control** via base observables.
- **Bridge mechanism**: the Shape Document uses `ADJUSTMENT_MAPPINGS` to translate a character delta into actionable base adjustments. Example:
  - `sheer_peak_station` off by \(-0.20\) → suggest `ADJUST section_metric:sheer_z_m AT station_range=(0.6,0.8) BY +0.4m`

This keeps the language stable (open observable IDs) while Phase 1 remains deterministic and safe.

---

### 1.8 Stability Contracts

- **Coordinate convention**: \(x_m\) (meters) for all physics/derivatives; `station_norm = x_m / LOA` for scoping (`station_range`).
- **Peak stability**: Use plateau centroid (within 1% of max) rather than raw argmax.
- **Curvature stability**: Minimum 5 sections; prefer smoothed 5-point stencil (or spline fit then differentiate).
- **Warp stability**: Use curvature-based warp score (not \(R^2\)).
- **Multi-body**: Return primary body only; explicit `None` if ambiguous (for this plan, assume single-body hulls).
- **Validation**: Non-finite inputs/outputs → `None`; ratios clamped to \([0,1]\).

---

### 1.9 Minimum Data Requirements (Failure mode: insufficient sections)

Many observables require a minimum number of sections. If there is insufficient data, the measurer must **return null / unmeasurable** (and Shape Document must omit the value or mark it as unmeasured), rather than inventing values.

**Minimum sections required (single body)**:
- **Basic maxima/minima metrics** (e.g. `sheer_peak_station`, `transom_beam_ratio`): **≥ 3** sections
- **Slope / regression metrics** (e.g. `chine_rise_rate`): **≥ 4** sections (recommended ≥ 5 for stability)
- **Curvature metrics** (e.g. `sheer_curvature_peak_station`, `rocker_profile_curvature`): **≥ 5** sections
- **Warp metrics** (e.g. `deadrise_progression_shape`): **≥ 5** sections

**Behavior**:
- If requirements are not met, return **`None`** from the measurement function.
- In Shape Document generation, exclude missing keys from `observable_snapshot` and exclude them from `comparison`, `critique_hints`, and `suggested_adjustments`.

## 2. Registry Entries

Add to `magnet/kernel/geometry_observables.py`:

```python
# === CHARACTER OBSERVABLES (Phase 1: Measurable Only) ===

# Sheer shape
"longitudinal_metric:sheer_peak_station": ObservableSpec(
    observable_id="longitudinal_metric:sheer_peak_station",
    measurable=True,
    controllable=False,
    control_mode="COMPILED",
    unit="ratio",
    tolerance=0.02,
    max_delta=0.1,
    reason="Phase 1 measurable only; control via sheer_z_m schedule in Phase 2.",
    alternatives=["section_metric:sheer_z_m"],
),

"longitudinal_metric:sheer_curvature_peak_station": ObservableSpec(
    observable_id="longitudinal_metric:sheer_curvature_peak_station",
    measurable=True,
    controllable=False,
    control_mode="OPTIMIZED",
    unit="ratio",
    tolerance=0.03,
    max_delta=0.15,
    reason="Requires solver to hit specific curvature peak location.",
    alternatives=["section_metric:sheer_z_m"],
),

# Stem/bow
"profile_metric:stem_rake_deg": ObservableSpec(
    observable_id="profile_metric:stem_rake_deg",
    measurable=True,
    controllable=False,
    control_mode="COMPILED",
    unit="deg",
    tolerance=1.0,
    max_delta=5.0,
    reason="Phase 1 measurable only; control via bow geometry params in Phase 2.",
),

"profile_metric:stem_concavity_ratio": ObservableSpec(
    observable_id="profile_metric:stem_concavity_ratio",
    measurable=True,
    controllable=False,
    control_mode="COMPILED",
    unit="ratio",
    tolerance=0.01,
    max_delta=0.05,
    reason="Phase 1 measurable only; requires bow/stem shape controls (Phase 2).",
),

# Entry sharpness (requires neighboring stations; implemented as longitudinal metric)
"longitudinal_metric:entry_half_angle_deg": ObservableSpec(
    observable_id="longitudinal_metric:entry_half_angle_deg",
    measurable=True,
    controllable=False,
    control_mode="COMPILED",
    unit="deg",
    tolerance=1.0,
    max_delta=5.0,
    reason="Computed from d(half_beam)/dx in forward band (p50). Control via forward beam schedule.",
    alternatives=["section_metric:max_half_beam_m"],
),

"longitudinal_metric:bow_fineness_ratio": ObservableSpec(
    observable_id="longitudinal_metric:bow_fineness_ratio",
    measurable=True,
    controllable=False,
    control_mode="COMPILED",
    unit="ratio",
    tolerance=0.02,
    max_delta=0.1,
    reason="Phase 1 measurable only; control via forward beam schedule.",
    alternatives=["section_metric:max_half_beam_m"],
),

# Transom
"profile_metric:transom_rake_deg": ObservableSpec(
    observable_id="profile_metric:transom_rake_deg",
    measurable=True,
    controllable=False,
    control_mode="DIRECT",
    unit="deg",
    tolerance=1.0,
    max_delta=5.0,
    reason="Measured from compiler-emitted transom_outline feature curve (Section 0 prerequisite).",
),

"profile_metric:transom_beam_ratio": ObservableSpec(
    observable_id="profile_metric:transom_beam_ratio",
    measurable=True,
    controllable=False,
    control_mode="DIRECT",
    unit="ratio",
    tolerance=0.02,
    max_delta=0.1,
    reason="Phase 1 measurable only; direct control via transom_width_fraction.",
),

# Chine progression
"longitudinal_metric:chine_rise_rate": ObservableSpec(
    observable_id="longitudinal_metric:chine_rise_rate",
    measurable=True,
    controllable=False,
    control_mode="COMPILED",
    unit="ratio",
    tolerance=0.05,
    max_delta=0.3,
    reason="Phase 1 measurable only; slope computed on x_m. Control via chine/section schedules in Phase 2.",
),

"section_metric:chine_height_ratio": ObservableSpec(
    observable_id="section_metric:chine_height_ratio",
    measurable=True,
    controllable=False,
    control_mode="COMPILED",
    unit="ratio",
    tolerance=0.02,
    max_delta=0.1,
    reason="Phase 1 measurable only; control via chine_config.height_ratio.",
),

# Bottom character
"longitudinal_metric:deadrise_progression_shape": ObservableSpec(
    observable_id="longitudinal_metric:deadrise_progression_shape",
    measurable=True,
    controllable=False,
    control_mode="OPTIMIZED",
    unit="ratio",
    tolerance=0.02,
    max_delta=0.1,
    reason="Curvature-based warp score (stable); requires solver/compiled control to achieve specific warp.",
),

"longitudinal_metric:rocker_profile_curvature": ObservableSpec(
    observable_id="longitudinal_metric:rocker_profile_curvature",
    measurable=True,
    controllable=False,
    control_mode="COMPILED",
    unit="1/m",
    tolerance=0.002,
    max_delta=0.01,
    reason="Phase 1 measurable only; control via keel_z schedule.",
),
```

---

## 3. Measurement Functions

### 3.1 File Location

Observables are **kernel truth**. Keep registry + measurement functions together in the kernel.

- `magnet/kernel/geometry_observables.py`: **registry + measurement functions** (single source of truth)
- `magnet/agents/`: imports from kernel, never owns observable definitions or measurers

### 3.2 Implementation Signatures
### 3.3 Chine Anchor Helper

```python
def _chine_like_point(points: List[Any], *, witness_index: Optional[int] = None) -> Optional[Any]:
    """
    Find a stable chine anchor using knee detection (max slope change) with witness reuse.

    Returns: SectionPoint at chine, or None if insufficient data.
    """
    pts = list(points or [])
    if len(pts) < 4:
        return None

    # Witness reuse (stable anchor across edits)
    if witness_index is not None:
        wi = int(witness_index)
        if 0 <= wi < len(pts):
            return pts[wi]

    # Knee detector: maximum change in dy/dz slope along the curve.
    ys = [float(getattr(p.position, "y")) for p in pts]
    max_y = max(ys) if ys else 0.0
    best = None
    best_delta = None
    prev_slope = None
    for i in range(len(pts) - 1):
        y1 = float(getattr(pts[i].position, "y"))
        z1 = float(getattr(pts[i].position, "z"))
        y2 = float(getattr(pts[i + 1].position, "y"))
        z2 = float(getattr(pts[i + 1].position, "z"))
        dz = z2 - z1
        if abs(dz) < 1e-12:
            continue
        slope = (y2 - y1) / dz
        if prev_slope is not None and 0 < i < len(pts) - 1:
            delta = abs(slope - prev_slope)
            if float(getattr(pts[i].position, "y")) >= 0.25 * max_y:
                if best_delta is None or delta > best_delta:
                    best_delta = delta
                    best = pts[i]
        prev_slope = slope
    if best is not None:
        return best

    # Fallback: max-y point in a depth-scaled band around local keel z (honest geometry-only anchor)
    zs = [float(getattr(p.position, "z")) for p in pts]
    keel_z = min(zs) if zs else 0.0
    depth = (max(zs) - min(zs)) if zs else 0.0
    z_band = max(0.25, 0.5 * float(depth))
    band = [p for p in pts if abs(float(getattr(p.position, "z")) - keel_z) <= z_band]
    if not band:
        return None
    return max(band, key=lambda q: float(getattr(q.position, "y")))
```

### 3.4 Measurement Implementations (Examples)

```python
# === SHEER SHAPE ===

def _longitudinal_metric_sheer_peak_station(secs: List[Any]) -> Optional[float]:
    """
    Find station where sheer_z is maximum.
    
    Returns: station_norm (0-1) or None if insufficient data.
    """
    pairs: List[Tuple[float, float]] = []  # (x_m, sheer_z)
    for s in secs:
        sheer_z = _metric_for_section(s, "section_metric:sheer_z_m")
        if sheer_z is None:
            continue
        x_m = float(getattr(s, "x_position", 0.0))
        pairs.append((x_m, sheer_z))
    
    if len(pairs) < 3:
        return None
    
    z_max = max(z for _x, z in pairs)
    if not math.isfinite(z_max):
        return None
    plateau = [(x, z) for x, z in pairs if z >= 0.99 * z_max]
    if not plateau:
        return None
    x_centroid = sum(x for x, _z in plateau) / len(plateau)
    x_min = min(x for x, _z in pairs)
    x_max = max(x for x, _z in pairs)
    x_range = max(1e-9, x_max - x_min)
    station_norm = max(0.0, min(1.0, (x_centroid - x_min) / x_range))
    return float(station_norm)


def _longitudinal_metric_sheer_curvature_peak_station(secs: List[Any]) -> Optional[float]:
    """
    Find station where sheer curvature (second derivative) is maximum.
    
    Returns: station_norm (0-1) or None if insufficient data.
    """
    # Collect (x_m, sheer_z) pairs sorted by x_m
    pairs: List[Tuple[float, float]] = []
    for s in secs:
        sheer_z = _metric_for_section(s, "section_metric:sheer_z_m")
        if sheer_z is None:
            continue
        x_m = float(getattr(s, "x_position", 0.0))
        pairs.append((x_m, sheer_z))
    
    pairs = sorted(pairs, key=lambda p: p[0])
    if len(pairs) < 5:  # Need enough points for stabilized curvature
        return None
    
    # Compute second derivative via a stabilized method (5-point stencil preferred; smoothing optional)
    curvatures: List[Tuple[float, float]] = []  # (station, |d²z/dx²|)
    for i in range(1, len(pairs) - 1):
        x0, z0 = pairs[i - 1]
        x1, z1 = pairs[i]
        x2, z2 = pairs[i + 1]
        
        dx1 = x1 - x0
        dx2 = x2 - x1
        if dx1 < 1e-9 or dx2 < 1e-9:
            continue
        
        # Second derivative approximation
        d2z = ((z2 - z1) / dx2 - (z1 - z0) / dx1) / ((dx1 + dx2) / 2)
        curvatures.append((x1, abs(d2z)))
    
    if not curvatures:
        return None
    
    max_curv = max(curvatures, key=lambda c: c[1])
    x_peak = float(max_curv[0])
    x_min = min(x for x, _z in pairs)
    x_max = max(x for x, _z in pairs)
    x_range = max(1e-9, x_max - x_min)
    station_norm = max(0.0, min(1.0, (x_peak - x_min) / x_range))
    return float(station_norm)


# === STEM/BOW ===

def _profile_metric_stem_rake_deg(geometry: Any) -> Optional[float]:
    """
    Compute stem rake angle from vertical.
    
    Uses stem_profile if available; if absent/degenerate, returns None (no invented fallback).
    """
    stem_profile = list(getattr(geometry, "stem_profile", []) or [])
    if len(stem_profile) < 2:
        return None

    # IMPORTANT: do NOT reorder the polyline (sorting by z breaks adjacency).
    pts = [(float(p.x), float(p.z)) for p in stem_profile]
    for i in range(len(pts) - 1):
        x1, z1 = pts[i]
        x2, z2 = pts[i + 1]
        if (z1 <= 0.0 <= z2) or (z2 <= 0.0 <= z1):
            dx = x2 - x1
            dz = z2 - z1
            if abs(dz) < 1e-9:
                return None
            return float(math.degrees(math.atan2(abs(dx), abs(dz))))
    return None


def _profile_metric_stem_concavity_ratio(geometry: Any) -> Optional[float]:
    """
    Compute stem concavity ratio in x–z plane:
        max perpendicular distance to chord / chord length

    Chord endpoints:
    - stem-head: max z on stem_profile
    - DWL intersection: z=0 polyline intersection (fallback: nearest |z|)
    """
    stem_profile = getattr(geometry, "stem_profile", None)
    if not stem_profile or len(stem_profile) < 3:
        return None
    
    pts = [(float(p.x), float(p.z)) for p in stem_profile]
    if len(pts) < 3:
        return None
    
    # stem-head = max z
    xh, zh = max(pts, key=lambda t: t[1])

    # DWL intersection with z=0 (fallback: nearest |z|)
    dwl = None
    for (x0, z0), (x1, z1) in zip(pts[:-1], pts[1:]):
        if (z0 <= 0 <= z1) or (z1 <= 0 <= z0):
            dz = z1 - z0
            if abs(dz) < 1e-12:
                continue
            t = (0.0 - z0) / dz
            if 0.0 <= t <= 1.0:
                dwl = (x0 + t * (x1 - x0), 0.0)
                break
    if dwl is None:
        dwl = min(pts, key=lambda t: abs(t[1]))
    xd, zd = dwl

    # chord length
    dx = xd - xh
    dz = zd - zh
    L = math.hypot(dx, dz)
    if not math.isfinite(L) or L < 1e-9:
        return None
    
    # point-to-line distance in 2D
    # distance = |(p - a) x (b - a)| / |b - a|
    max_d = 0.0
    ax, az = xh, zh
    bx, bz = xd, zd
    vx, vz = (bx - ax), (bz - az)
    denom = math.hypot(vx, vz)
    if denom < 1e-9:
        return None
    for px, pz in pts:
        # 2D cross magnitude
        cx = (px - ax) * vz - (pz - az) * vx
        d = abs(cx) / denom
        if math.isfinite(d):
            max_d = max(max_d, d)

    ratio = max_d / L
    if not math.isfinite(ratio):
        return None
    return float(max(0.0, min(1.0, ratio)))


# === ENTRY SHARPNESS ===

def _section_metric_entry_half_angle_deg(section: Any, loa: float) -> Optional[float]:
    """
    Deprecated stub.

    `entry_half_angle_deg` requires neighboring stations to estimate \(d(half\_beam)/dx\).
    Implement as `longitudinal_metric:entry_half_angle_deg` over the forward band instead.
    """
    _ = section
    _ = loa
    return None


def _longitudinal_metric_entry_half_angle_deg(secs: List[Any]) -> Optional[float]:
    """
    Compute local waterline half-angle of entry in the bow region using slope d(half_beam)/dx.

    Returns: representative bow entry half-angle in degrees (p50 over forward band).
    """
    pairs: List[Tuple[float, float]] = []  # (x_m, half_beam_m)
    for s in secs:
        hb = _metric_for_section(s, "section_metric:max_half_beam_m")
        if hb is None:
            continue
        x_m = float(getattr(s, "x_position", 0.0) or 0.0)
        pairs.append((x_m, float(hb)))
    if len(pairs) < 5:
        return None
    pairs = sorted(pairs, key=lambda p: p[0])
    x_min = min(x for x, _hb in pairs)
    x_max = max(x for x, _hb in pairs)
    x_range = max(1e-9, x_max - x_min)
    
    # forward band: station_norm >= 0.85
    indices = [i for i, (x, _hb) in enumerate(pairs) if ((x - x_min) / x_range) >= 0.85]
    if len(indices) < 3:
        return None
    
    angles: List[float] = []
    for i in indices:
        if i <= 0 or i >= len(pairs) - 1:
            continue
        x0, hb0 = pairs[i - 1]
        x2, hb2 = pairs[i + 1]
        dx = x2 - x0
        if abs(dx) < 1e-9:
            continue
        slope = (hb2 - hb0) / dx  # d(half_beam)/dx
        ang = float(math.degrees(math.atan(float(slope))))
        if math.isfinite(ang):
            angles.append(ang)
    if not angles:
        return None
    angles = sorted(angles)
    return float(angles[len(angles) // 2])  # p50


def _longitudinal_metric_bow_fineness_ratio(secs: List[Any], loa: float) -> Optional[float]:
    """
    Compute mean half-beam / (0.1 * loa) for forward 10% of hull.
    """
    # station_norm must be derived from x_m and x-range (never from section.station)
    xs = [float(getattr(s, "x_position", 0.0) or 0.0) for s in secs]
    if not xs:
        return None
    x_min = min(xs)
    x_max = max(xs)
    x_range = max(1e-9, x_max - x_min)

    forward_beams: List[float] = []
    for s in secs:
        x_m = float(getattr(s, "x_position", 0.0) or 0.0)
        station_norm = (x_m - x_min) / x_range
        if station_norm < 0.9:
            continue
        hb = _metric_for_section(s, "section_metric:max_half_beam_m")
        if hb is not None:
            forward_beams.append(hb)
    
    if len(forward_beams) < 2:
        return None
    
    mean_beam = sum(forward_beams) / len(forward_beams)
    ratio = mean_beam / (0.1 * max(1e-9, float(loa)))
    return float(ratio)


# === TRANSOM ===

def _profile_metric_transom_rake_deg(geometry: Any, features: Any) -> Optional[float]:
    """
    Get transom rake angle.
    
    Priority (v0 after Section 0 prerequisite):
    - transom_outline (compiler-emitted)
    - (no fallback “estimate from section chord”: return None if missing)
    """
    # IMPORTANT: Do not read authored config fields as a substitute for derived measurement.
    # Only derive from compiler-emitted geometry (fail-closed if missing).

    # Derive from transom_outline (3D points at aft plane)
    transom_outline = getattr(geometry, "transom_outline", None)
    if transom_outline and len(transom_outline) >= 3:
        # Plane fit (minimal, dependency-free):
        # Use 3 non-collinear points to get a plane normal; no bounding-box shortcuts.
        pts = [(float(p.x), float(p.y), float(p.z)) for p in transom_outline]
        a = pts[0]
        b = pts[len(pts) // 2]
        c = pts[-1]

        ux, uy, uz = (b[0] - a[0]), (b[1] - a[1]), (b[2] - a[2])
        vx, vy, vz = (c[0] - a[0]), (c[1] - a[1]), (c[2] - a[2])
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        nn = math.sqrt(nx * nx + ny * ny + nz * nz)
        if nn < 1e-12:
    return None
        nx /= nn
        nz /= nn

        # Rake in x–z: atan2(|nx|, |nz|) in degrees
        rake = float(math.degrees(math.atan2(abs(nx), abs(nz))))
        if math.isfinite(rake):
            return rake
    
    return None


def _profile_metric_transom_beam_ratio(secs: List[Any]) -> Optional[float]:
    """
    Compute transom beam / max beam.
    """
    # station_norm must be derived from x_position (never from section.station)
    xs = [float(getattr(s, "x_position", 0.0) or 0.0) for s in secs]
    if not xs:
        return None
    x_min = min(xs)
    x_max = max(xs)
    x_range = max(1e-9, x_max - x_min)

    beams: List[Tuple[float, float]] = []  # (station_norm, half_beam)
    for s in secs:
        x_m = float(getattr(s, "x_position", 0.0) or 0.0)
        station_norm = (x_m - x_min) / x_range
        hb = _metric_for_section(s, "section_metric:max_half_beam_m")
        if hb is not None:
            beams.append((station_norm, hb))
    
    if len(beams) < 3:
        return None
    
    # Find aft-most (transom) and max
    aft_beam = min(beams, key=lambda b: b[0])[1]
    max_beam = max(b[1] for b in beams)
    
    if max_beam < 0.01:
        return None
    
    return float(aft_beam / max_beam)


# === CHINE PROGRESSION ===

def _longitudinal_metric_chine_rise_rate(secs: List[Any], loa: float) -> Optional[float]:
    """
    Compute slope of chine_z vs x_m in forward half.

    Returns: m/m (dimensionless slope).
    """
    # station_norm must be derived from x_m and x-range (never from section.station)
    xs = [float(getattr(s, "x_position", 0.0) or 0.0) for s in secs]
    if not xs:
        return None
    x_min = min(xs)
    x_max = max(xs)
    x_range = max(1e-9, x_max - x_min)

    pairs: List[Tuple[float, float]] = []  # (x_m, chine_z)
    for s in secs:
        x_m = float(getattr(s, "x_position", 0.0) or 0.0)
        station_norm = (x_m - x_min) / x_range
        if station_norm < 0.5:
            continue  # Forward half only
        
        pts = list(getattr(s, "points", []) or [])
        chine = _chine_like_point(pts)
        if chine is None:
            continue
        chine_z = float(getattr(chine.position, "z"))
        pairs.append((x_m, chine_z))
    
    if len(pairs) < 3:
        return None
    
    # Linear regression on x_m (meters): result is m/m (dimensionless slope)
    n = len(pairs)
    sum_x = sum(p[0] for p in pairs)
    sum_y = sum(p[1] for p in pairs)
    sum_xy = sum(p[0] * p[1] for p in pairs)
    sum_x2 = sum(p[0] ** 2 for p in pairs)
    
    denom = n * sum_x2 - sum_x ** 2
    if abs(denom) < 1e-12:
        return None
    
    slope = (n * sum_xy - sum_x * sum_y) / denom
    return float(slope)


def _section_metric_chine_height_ratio(section: Any) -> Optional[float]:
    """
    Compute (chine_z - keel_z) / (sheer_z - keel_z).
    """
    pts = list(getattr(section, "points", []) or [])
    if len(pts) < 3:
        return None
    
    # Find keel (min z), sheer (max z), chine (geometric anchor)
    keel = min(pts, key=lambda p: float(getattr(p.position, "z")))
    sheer = max(pts, key=lambda p: float(getattr(p.position, "z")))
    chine = _chine_like_point(pts)
    
    if chine is None:
        return None
    
    keel_z = float(getattr(keel.position, "z"))
    sheer_z = float(getattr(sheer.position, "z"))
    chine_z = float(getattr(chine.position, "z"))
    
    height_range = sheer_z - keel_z
    if height_range < 0.01:
        return None
    
    ratio = (chine_z - keel_z) / height_range
    return float(ratio)


# === BOTTOM CHARACTER ===

def _longitudinal_metric_deadrise_progression_shape(secs: List[Any]) -> Optional[float]:
    """
    Compute curvature-based warp score for deadrise progression (stable).
    Returns: score in [0,1], where 0 ~ linear-ish and higher ~ more warped.
    """
    pairs: List[Tuple[float, float]] = []  # (x_m, deadrise_deg)
    for s in secs:
        x_m = float(getattr(s, "x_position", 0.0))
        deadrise = _metric_for_section(s, "section_metric:deadrise_deg_at_chine")
        if deadrise is not None:
            pairs.append((x_m, deadrise))
    
    if len(pairs) < 5:
        return None
    
    pairs = sorted(pairs, key=lambda t: t[0])
    xs = [p[0] for p in pairs]
    bs = [p[1] for p in pairs]
    span = max(bs) - min(bs)
    if not math.isfinite(span) or span < 1e-9:
        return 0.0
    
    # Placeholder: stabilized 2nd-derivative magnitude proxy (5-point stencil preferred in real implementation)
    curvs: List[float] = []
    for i in range(1, len(xs) - 1):
        x0, b0 = xs[i - 1], bs[i - 1]
        x1, b1 = xs[i], bs[i]
        x2, b2 = xs[i + 1], bs[i + 1]
        dx1 = x1 - x0
        dx2 = x2 - x1
        if dx1 < 1e-9 or dx2 < 1e-9:
            continue
        d2 = ((b2 - b1) / dx2 - (b1 - b0) / dx1) / ((dx1 + dx2) / 2)
        if math.isfinite(d2):
            curvs.append(abs(d2))
    if not curvs:
        return None
    curvs.sort()
    k_p95 = curvs[int(0.95 * (len(curvs) - 1))]  # deg/m^2
    loa = max(xs) - min(xs)
    loa = max(1e-9, loa)
    # Dimensionally consistent normalization: k * LOA^2 / span
    score = (k_p95 * (loa ** 2)) / max(span, 1e-9)
    return float(max(0.0, min(1.0, score)))


def _longitudinal_metric_rocker_profile_curvature(secs: List[Any]) -> Optional[float]:
    """
    Compute mean absolute curvature of keel profile.
    """
    pairs: List[Tuple[float, float]] = []  # (x_position, keel_z)
    for s in secs:
        x_pos = float(getattr(s, "x_position", 0.0))
        keel_z = _metric_for_section(s, "section_metric:keel_z_m")
        if keel_z is not None:
            pairs.append((x_pos, keel_z))
    
    pairs = sorted(pairs, key=lambda p: p[0])
    if len(pairs) < 5:
        return None
    
    # Compute second derivative at each interior point
    curvatures: List[float] = []
    for i in range(1, len(pairs) - 1):
        x0, z0 = pairs[i - 1]
        x1, z1 = pairs[i]
        x2, z2 = pairs[i + 1]
        
        dx1 = x1 - x0
        dx2 = x2 - x1
        if dx1 < 1e-9 or dx2 < 1e-9:
            continue
        
        d2z = ((z2 - z1) / dx2 - (z1 - z0) / dx1) / ((dx1 + dx2) / 2)
        curvatures.append(abs(d2z))
    
    if not curvatures:
        return None
    
    return float(sum(curvatures) / len(curvatures))
```

---

## 4. Validation

### 4.1 Unit Tests

Add to `tests/agents/test_hull_character_observables_v05.py`:

```python
@pytest.mark.asyncio
async def test_sheer_peak_station_teardrop_profile():
    """
    PASS: Sheer peaks at station ~0.72 (teardrop shape).
    """
    # Create hull with sheer peaking at 0.72
    # Assert sheer_peak_station ≈ 0.72 ± 0.05


@pytest.mark.asyncio
async def test_stem_rake_deg_moderate_rake():
    """
    PASS: Stem rake ~12° (moderate Viking rake).
    """
    # Create hull with 12° stem rake
    # Assert stem_rake_deg ≈ 12 ± 2


@pytest.mark.asyncio
async def test_entry_half_angle_fine_entry():
    """
    PASS: Entry half-angle ~10° (fine entry).
    """
    # Create hull with fine bow
    # Assert entry_half_angle_deg ≈ 10 ± 2


@pytest.mark.asyncio
async def test_transom_beam_ratio_wide_transom():
    """
    PASS: Transom beam ratio ~0.85 (wide transom).
    """
    # Create hull with wide transom
    # Assert transom_beam_ratio ≈ 0.85 ± 0.05


@pytest.mark.asyncio
async def test_deadrise_progression_warped():
    """
    PASS: Deadrise progression warp score is in expected band (warped bottom).
    """
    # Create hull with warped deadrise
    # Assert deadrise_progression_shape is within expected band (tune empirically)
```

### 4.2 Reference Hull Test Cases

| Hull Type | sheer_peak_station | stem_rake_deg | stem_concavity_ratio | entry_half_angle_deg | transom_beam_ratio | deadrise_progression_shape |
|-----------|-------------------|---------------|---------------------|-------------------|---------------------------|
| Viking 72 | 0.70-0.75 | 12-15 | 0.05-0.15 | 10-14 | 0.82-0.88 | (warp_score band) |
| Generic planing | 0.85-0.95 | 5-10 | 0.00-0.05 | 15-20 | 0.75-0.85 | (warp_score band) |
| Displacement | 0.90-1.00 | 0-5 | 0.00-0.03 | 20-30 | 0.60-0.75 | (warp_score band) |

---

## 5. Proposer Integration

### 5.1 System Prompt Update

Add to `magnet/agents/geometry_proposer.py` system prompt:

```
CHARACTER OBSERVABLES (Phase 1: Measurable)

When creating hulls with distinctive character, bind DOFs to these observables:

SHEER SHAPE:
- longitudinal_metric:sheer_peak_station — WHERE sheer peaks (0-1)
  Viking: 0.70-0.75 (teardrop), Generic: 0.85-0.95 (bow-peaked)

- longitudinal_metric:sheer_curvature_peak_station — WHERE sheer curve changes
  Viking: 0.65-0.70 (shoulder), Generic: 0.80-0.90 (gradual)

STEM/BOW:
- profile_metric:stem_rake_deg — stem angle from vertical
  Viking: 12-15°, Aggressive: 15-20°, Vertical: 0-5°
- profile_metric:stem_concavity_ratio — stem curvature (aggressive reach)
  Viking: 0.05-0.15, Straight: 0.0-0.05

ENTRY:
- longitudinal_metric:entry_half_angle_deg — bow sharpness (forward band p50)
  Fine: 8-12°, Moderate: 12-18°, Blunt: 18-25°

- longitudinal_metric:bow_fineness_ratio — beam/length in forward 10%
  Fine: 0.15-0.25, Moderate: 0.25-0.35, Full: 0.35-0.50

TRANSOM:
- profile_metric:transom_rake_deg — transom angle from vertical
  Viking: 10-15°, Vertical: 0-5°, Raked: 15-20°

- profile_metric:transom_beam_ratio — transom width / max beam
  Wide: 0.80-0.90, Moderate: 0.70-0.80, Narrow: 0.60-0.70

CHINE:
- longitudinal_metric:chine_rise_rate — how fast chine climbs forward
  Note: computed on x_m (m/m). Use distributions to set bands.

- section_metric:chine_height_ratio — chine height / section height
  Low: 0.20-0.30, Moderate: 0.30-0.40, High: 0.40-0.50

BOTTOM:
- longitudinal_metric:deadrise_progression_shape — curvature-based warp score (stable)
  Linear-ish: low score, Warped: moderate score (tune empirically)

- longitudinal_metric:rocker_profile_curvature — keel curvature
  Flat: <0.005, Gentle: 0.005-0.015, Curved: 0.015-0.030
```

### 5.2 Binding Table Example

```json
{
  "binding_table": [
    {
      "dof_name": "sheer_profile",
      "binds_to": ["longitudinal_metric:sheer_rise_m", "longitudinal_metric:sheer_peak_station"],
      "observation_targets": [
        {"observable_id": "longitudinal_metric:sheer_rise_m", "span_min": 0.8},
        {"observable_id": "longitudinal_metric:sheer_peak_station", "threshold_min": 0.68, "threshold_max": 0.78}
      ]
    },
    {
      "dof_name": "entry_shape",
      "binds_to": ["longitudinal_metric:entry_half_angle_deg", "longitudinal_metric:bow_fineness_ratio"],
      "observation_targets": [
        {"observable_id": "longitudinal_metric:entry_half_angle_deg", "threshold_max": 14.0, "station_range": [0.85, 1.0]},
        {"observable_id": "longitudinal_metric:bow_fineness_ratio", "threshold_max": 0.25}
      ]
    }
  ]
}
```

---

## 6. Phase 1 Scope: Priority Observables

### Highest Character Impact (Implement First)

| Priority | Observable | Viking Impact | Implementation Complexity |
|----------|-----------|---------------|--------------------------|
| **1** | `longitudinal_metric:sheer_peak_station` | Defines teardrop silhouette | Low (plateau-centroid over existing metric) |
| **2** | `profile_metric:transom_beam_ratio` | Wide stern character | Low (ratio of existing metrics) |
| **3** | `longitudinal_metric:entry_half_angle_deg` | Fine bow character | Medium (requires slope estimation d(half_beam)/dx in forward band) |
| **4** | `longitudinal_metric:chine_rise_rate` | Lifted bow look | Medium (regression) |
| **5** | `longitudinal_metric:deadrise_progression_shape` | Warped bottom | Medium (curvature-based warp score) |

### Phase 1 Deliverable

Implement observables 1-5 above. These five observables capture:
- **Silhouette** (sheer_peak_station)
- **Stern** (transom_beam_ratio)
- **Bow** (entry_half_angle_deg)
- **Chine** (chine_rise_rate)
- **Bottom** (deadrise_progression_shape)

Together they transform a "valid planing hull" into a hull with distinctive, targetable character.

---

## 7. Files to Touch

### Core Implementation

| File | Changes |
|------|---------|
| `magnet/kernel/stdlib/section_compiler.py` | **NEW prerequisite**: extract feature curves from sections (stem_profile, transom_outline, sheer_line, chine_line (witness), keel_line) |
| `magnet/kernel/geometry_observables.py` | Add 12 new `ObservableSpec` entries to `OBSERVABLE_REGISTRY` |
| `magnet/kernel/geometry_observables.py` | Add 12 measurement functions + stability policies (plateau centroid, curvature smoothing) |
| `magnet/agents/geometry_observables.py` | Import from kernel only (no ownership); optional thin wrappers for backward compatibility |

### Shape Document System (Wiring + Glue)

| File | Changes |
|------|---------|
| `magnet/kernel/shape_document.py` | **NEW**: Shape Document schema + generation (`generate_shape_document`) + target profile registry |
| `magnet/deployment/spiral_endpoints.py` | Wire Shape Document generation into request flow (EDIT mode auto-generates + passes to proposer); enforce EDIT-mode verb whitelist; diff-budget/identity guard |
| `magnet/kernel/intent_protocol.py` | **NEW (or extend existing intent router)**: deterministic mode inference (CREATE vs EDIT vs REWRITE) |
| `magnet/kernel/feature_curve_extractor.py` | **Optional NEW**: shared helpers for curve extraction + `smooth_polyline_c1` (if not kept inside `section_compiler.py`) |

### Proposer Integration

| File | Changes |
|------|---------|
| `magnet/agents/geometry_proposer.py` | Update system prompt with character observable guidance |

### Tests

| File | Changes |
|------|---------|
| `tests/agents/test_hull_character_observables_v05.py` | New file with character observable tests |

### Documentation

| File | Changes |
|------|---------|
| `docs/3-implementation/general/V05_CHARACTER_OBSERVABLES_PLAN.md` | This plan (move from root after implementation) |

---

## 8. Test Cases: Known Hull → Expected Values

### Viking 72 Sportfisher Reference

```python
VIKING_72_EXPECTED = {
    "longitudinal_metric:sheer_peak_station": (0.70, 0.76),  # (min, max)
    "longitudinal_metric:sheer_curvature_peak_station": (0.64, 0.72),
    "profile_metric:stem_rake_deg": (11.0, 16.0),
    "profile_metric:stem_concavity_ratio": (0.05, 0.15),
    "longitudinal_metric:entry_half_angle_deg": (9.0, 14.0),  # forward band p50
    "longitudinal_metric:bow_fineness_ratio": (0.18, 0.26),
    "profile_metric:transom_rake_deg": (10.0, 15.0),
    "profile_metric:transom_beam_ratio": (0.82, 0.88),
    "longitudinal_metric:chine_rise_rate": (0.01, 0.10),  # m/m (tune empirically)
    "section_metric:chine_height_ratio": (0.22, 0.35),  # midship
    # curvature-based warp_score in [0,1] (tune empirically once distributions are known)
    "longitudinal_metric:deadrise_progression_shape": (0.10, 0.45),
    "longitudinal_metric:rocker_profile_curvature": (0.003, 0.012),
}
```

### Generic Planing Hull Reference

```python
GENERIC_PLANING_EXPECTED = {
    "longitudinal_metric:sheer_peak_station": (0.88, 0.98),
    "profile_metric:stem_rake_deg": (4.0, 10.0),
    "profile_metric:stem_concavity_ratio": (0.00, 0.05),
    "longitudinal_metric:entry_half_angle_deg": (16.0, 22.0),
    "longitudinal_metric:bow_fineness_ratio": (0.30, 0.42),
    "profile_metric:transom_beam_ratio": (0.74, 0.84),
    "longitudinal_metric:deadrise_progression_shape": (0.00, 0.25),
}
```

---

## 9. Success Criteria

### Phase 1 Complete When:

1. ✅ All 5 priority observables are measurable from compiled geometry
2. ✅ Registry entries exist with correct metadata
3. ✅ Unit tests pass for known hull → expected value ranges
4. ✅ Proposer system prompt includes character observable guidance
5. ✅ Model can bind DOFs to character observables in thinking pass

### Character Achieved When:

Given prompt "Create a Viking 72-style sportfisher hull":
- `sheer_peak_station` ∈ [0.68, 0.78] (not [0.88, 0.98])
- `entry_half_angle_deg` ∈ [9, 14] (not [16, 22])
- `transom_beam_ratio` ∈ [0.82, 0.88] (not [0.74, 0.84])

The hull should be *recognizably Viking*, not generically valid.

---

## Appendix A: Coordinate Conventions

- **Station**: 0 = aft (AP/transom), 1 = forward (FP/bow)
- **x_position**: meters from AP (0 = transom, loa = bow)
- **y**: transverse, positive port
- **z**: vertical, positive up from baseline

## Appendix B: Existing Observable IDs

From `magnet/kernel/geometry_observables.py`:
- `section_metric:deadrise_deg_at_chine` (controllable)
- `section_metric:max_half_beam_m` (controllable)
- `section_metric:sheer_z_m` (controllable)
- `longitudinal_metric:sheer_rise_m` (measurable)
- `longitudinal_metric:entry_fineness_p95` (measurable)
- `longitudinal_metric:deadrise_drop_deg` (measurable)
- `longitudinal_metric:keel_slope_deg_p95` (measurable)
- `section_metric:topside_angle_deg_above_chine` (measurable)

---

# Part II: Shape Document System

The following sections define a compact, token-efficient representation of hull state that enables the model to critique and fix hulls without spatial reasoning from raw coordinates.

---

## 10. Shape Document Specification

### 10.1 Problem Statement

Models cannot spatially reason from coordinate lists:
- **Bad**: `[[0, -1.5], [2.1, -1.2], [2.3, -0.8], ...]` → model has no idea what this looks like
- **Good**: `entry_half_angle_deg: 18.2 (target: 11.0, delta: -7.2)` → model knows entry is too blunt

The Shape Document pre-computes everything the model needs to critique and fix a hull.

### 10.2 Schema Definition

```json
{
  "schema_version": "1.0.0",
  "generated_at": "2026-01-19T14:32:00Z",
  
  "hull_identity": {
    "hull_id": "MAGNET-20260119-abc123",
    "design_version": 42,
    "body_count": 1
  },
  
  "principal_dimensions": {
    "loa_m": 22.0,
    "lwl_m": 20.5,
    "beam_m": 6.2,
    "draft_m": 1.4,
    "depth_m": 2.8
  },

  "bodies": {
    "main_hull": {
      "observable_snapshot": {
        "sheer_peak_station": 0.92,
        "entry_half_angle_deg": 18.2,
        "transom_beam_ratio": 0.76
      },
      "comparison": {
        "sheer_peak_station": {"current": 0.92, "target": 0.72, "delta": -0.20, "status": "off", "controllable": false}
      }
    },
    "superstructure_1": {
      "observable_snapshot": {
        "sheer_peak_station": 0.92
      }
    }
  },
  
  "observable_snapshot": {
    "sheer_peak_station": 0.92,
    "sheer_rise_m": 1.85,
    "stem_rake_deg": 8.2,
    "stem_concavity_ratio": 0.03,
    "entry_half_angle_deg": 18.2,
    "bow_fineness_ratio": 0.38,
    "transom_rake_deg": 12.0,
    "transom_beam_ratio": 0.76,
    "chine_rise_rate": 0.03,
    "deadrise_drop_deg": 4.2,
    "deadrise_progression_shape": 0.22
  },
  
  "target_profile": {
    "profile_id": "viking_sportfisher",
    "source": "named_profile",
    "targets": {
      "sheer_peak_station": 0.72,
      "stem_concavity_ratio": 0.10,
      "entry_half_angle_deg": 11.0,
      "transom_beam_ratio": 0.85,
      "deadrise_progression_shape": 0.25,
      "chine_rise_rate": 0.04
    }
  },
  
  "comparison": {
    "sheer_peak_station": {
      "current": 0.92,
      "target": 0.72,
      "delta": -0.20,
      "delta_pct": -21.7,
      "status": "off",
      "controllable": false
    },
    "entry_half_angle_deg": {
      "current": 18.2,
      "target": 11.0,
      "delta": -7.2,
      "delta_pct": -39.6,
      "status": "off",
      "controllable": false
    },
    "transom_beam_ratio": {
      "current": 0.76,
      "target": 0.85,
      "delta": 0.09,
      "delta_pct": 11.8,
      "status": "off",
      "controllable": false
    }
  },
  
  "critique_hints": [
    "Sheer peaks too far forward (0.92 vs 0.72 target) — lacks teardrop character",
    "Entry too blunt (18.2° vs 11.0° target) — will pound in chop",
    "Transom too narrow (0.76 vs 0.85 target) — reduced planing stability"
  ],
  
  "suggested_adjustments": [
    {
      "observable_id": "section_metric:max_half_beam_m",
      "scope": {"station_range": [0.85, 1.0]},
      "operation": "ADJUST",
      "delta": -0.8,
      "unit": "m",
      "rationale": "Narrow forward sections to sharpen entry"
    },
    {
      "observable_id": "section_metric:sheer_z_m",
      "scope": {"station_range": [0.6, 0.8]},
      "operation": "ADJUST",
      "delta": 0.4,
      "unit": "m",
      "rationale": "Raise sheer in mid-forward region to shift peak aft"
    }
  ],
  
  "quality_summary": {
    "observables_measured": 11,
    "targets_defined": 5,
    "targets_met": 0,
    "targets_close": 1,
    "targets_off": 4,
    "overall_character_score": 0.32
  }
}
```

### 10.3 Field Descriptions

| Field | Type | Description | Model Use |
|-------|------|-------------|-----------|
| `hull_identity` | object | Design ID, version, body count | Traceability |
| `principal_dimensions` | object | LOA, beam, draft, depth | Context for scale |
| `bodies` | object | Per-body snapshots (and optional per-body comparisons/critiques) keyed by `body_id` | Multi-body critique without mixing signals |
| `observable_snapshot` | object | Current values for all measurable observables | "What is the hull now?" |
| `target_profile` | object | Target values (if any) | "What should it be?" |
| `comparison` | object | Per-observable current/target/delta/status | "How far off is each?" |
| `critique_hints` | array | Pre-computed natural language critiques | "What's wrong in words?" |
| `suggested_adjustments` | array | Actionable ADJUST/TARGET statements | "How to fix it?" |
| `quality_summary` | object | Aggregate metrics | "Overall status" |

### 10.4 Token Budget Breakdown

Target: **~1500 tokens** total

Note: Multi-body vessels are supported by the geometry pipeline. This plan is *per-body* by construction, but profile targets and “character scoring” should apply to a selected primary body.

| Section | Estimated Tokens | Notes |
|---------|-----------------|-------|
| `hull_identity` | ~30 | Fixed overhead |
| `principal_dimensions` | ~40 | 5 values |
| `observable_snapshot` | ~150 | 10-15 observables × 10 tokens |
| `target_profile` | ~80 | Profile ID + 5-8 targets |
| `comparison` | ~300 | 5-8 comparisons × 40 tokens |
| `critique_hints` | ~200 | 3-5 hints × 40 tokens |
| `suggested_adjustments` | ~250 | 3-5 suggestions × 50 tokens |
| `quality_summary` | ~50 | Aggregate stats |
| **JSON overhead** | ~100 | Braces, keys, formatting |
| **Total** | **~1200** | Under budget |

### 10.5 What Each Field Enables

| Field | Model Capability |
|-------|-----------------|
| `observable_snapshot` | Compare numbers: "current 0.92, that's high" |
| `comparison.delta` | Quantify gap: "need to reduce by 0.20" |
| `comparison.status` | Quick triage: focus on "off" items |
| `comparison.controllable` | Know what can be directly adjusted |
| `critique_hints` | Understand WHY it's wrong in domain terms |
| `suggested_adjustments` | Start with pre-computed fix, modify if needed |
| `quality_summary` | Decide: iterate or rewrite? |

---

## 11. Shape Document Generation

### 11.1 When to Generate

| Event | Generate Shape Document? | Include Targets? |
|-------|-------------------------|------------------|
| After CREATE (new hull) | Yes | Yes, if target profile specified |
| After ADJUST/TARGET | Yes | Yes, same targets |
| On explicit request | Yes | Optional |
| In EDIT mode context | Yes | Yes |
| In REWRITE mode | No (full regeneration) | N/A |

### 11.2 Function Signature

```python
# magnet/kernel/shape_document.py

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


@dataclass
class Comparison:
    current: float
    target: Optional[float]
    delta: Optional[float]
    delta_pct: Optional[float]
    status: str  # "met" | "close" | "off" | "no_target"
    controllable: bool


@dataclass
class SuggestedAdjustment:
    observable_id: str
    scope: Dict[str, Any]
    operation: str  # "ADJUST" | "TARGET"
    delta: Optional[float]
    value: Optional[float]
    unit: str
    rationale: str


@dataclass
class ShapeDocument:
    schema_version: str = "1.0.0"
    generated_at: str = ""
    
    hull_identity: Dict[str, Any] = field(default_factory=dict)
    principal_dimensions: Dict[str, float] = field(default_factory=dict)
    observable_snapshot: Dict[str, float] = field(default_factory=dict)
    target_profile: Optional[Dict[str, Any]] = None
    comparison: Dict[str, Comparison] = field(default_factory=dict)
    critique_hints: List[str] = field(default_factory=list)
    suggested_adjustments: List[SuggestedAdjustment] = field(default_factory=list)
    quality_summary: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        d = asdict(self)
        # Convert Comparison objects
        d["comparison"] = {
            k: asdict(v) if isinstance(v, Comparison) else v
            for k, v in self.comparison.items()
        }
        d["suggested_adjustments"] = [
            asdict(a) if isinstance(a, SuggestedAdjustment) else a
            for a in self.suggested_adjustments
        ]
        return d
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def token_estimate(self) -> int:
        """Estimate token count (rough: 4 chars per token)."""
        return len(self.to_json(indent=None)) // 4


def generate_shape_document(
    state: Dict[str, Any],
    geometry: Any,
    target_profile: Optional[Dict[str, Any]] = None,
    target_profile_id: Optional[str] = None,
) -> ShapeDocument:
    """
    Generate a Shape Document from current state and geometry.
    
    Args:
        state: Current design state dict
        geometry: Compiled HullGeometry object
        target_profile: Explicit target values dict, or None
        target_profile_id: Named profile ID to load targets from
    
    Returns:
        ShapeDocument with all fields populated
    """
    doc = ShapeDocument()
    doc.generated_at = datetime.utcnow().isoformat() + "Z"
    
    # 1. Hull identity
    doc.hull_identity = _extract_hull_identity(state)
    
    # 2. Principal dimensions
    doc.principal_dimensions = _extract_principal_dimensions(state)
    
    # 3. Observable snapshot (measure all)
    doc.observable_snapshot = _measure_all_observables(geometry, state)
    
    # 4. Target profile
    if target_profile_id:
        target_profile = get_target_profile(target_profile_id)
    if target_profile:
        doc.target_profile = {
            "profile_id": target_profile.get("profile_id", "custom"),
            "source": target_profile.get("source", "explicit"),
            "targets": target_profile.get("targets", {}),
        }
    
    # 5. Comparison (if targets exist)
    if doc.target_profile:
        doc.comparison = _compute_comparisons(
            doc.observable_snapshot,
            doc.target_profile["targets"],
        )
    
    # 6. Critique hints
    doc.critique_hints = _generate_critique_hints(doc.comparison)
    
    # 7. Suggested adjustments
    doc.suggested_adjustments = _generate_suggested_adjustments(doc.comparison)
    
    # 8. Quality summary
    doc.quality_summary = _compute_quality_summary(doc.comparison)
    
    return doc


def _measure_all_observables(geometry: Any, state: Dict[str, Any]) -> Dict[str, float]:
    """
    Measure all character observables.

    **None-handling rule (critical)**:
    - If an observable is unmeasurable (returns None), omit its key entirely.
    - Do NOT include `null` values in observable_snapshot.
    - Unmeasured observables must not appear in `comparison`, `critique_hints`, or `suggested_adjustments`.
    """
    snapshot: Dict[str, float] = {}
    for obs_id in CHARACTER_OBSERVABLE_IDS:
        val = measure_observable(obs_id, geometry, state=state)
        if val is None:
            continue
        if isinstance(val, (int, float)) and math.isfinite(float(val)):
            snapshot[str(obs_id)] = float(val)
    return snapshot


def _generate_critique_hints(comparisons: Dict[str, Comparison]) -> List[str]:
    """
    Critique only what was measured.
    """
    hints: List[str] = []
    for obs_id, comp in (comparisons or {}).items():
        if comp is None or comp.current is None:
            continue
        # ... template-based critique selection ...
    return hints


def _extract_hull_identity(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "hull_id": state.get("design_id", "unknown"),
        "design_version": state.get("design_version", 0),
        "body_count": len(state.get("resources", {}).get("geometry.body", {})) or 1,
    }


def _extract_principal_dimensions(state: Dict[str, Any]) -> Dict[str, float]:
    hull = state.get("hull", {})
    return {
        "loa_m": float(hull.get("loa", 0)),
        "lwl_m": float(hull.get("lwl", 0)),
        "beam_m": float(hull.get("beam", 0)),
        "draft_m": float(hull.get("draft", 0)),
        "depth_m": float(hull.get("depth", 0)),
    }


def _measure_all_observables(geometry: Any, state: Dict[str, Any]) -> Dict[str, float]:
    """Measure all registered observables from geometry."""
    from magnet.kernel.geometry_observables import compute_observable_series_from_geometry
    
    series = compute_observable_series_from_geometry(geometry)
    snapshot = {}
    
    for key, obs_series in series.items():
        # Extract observable_id from "body_id:observable_id"
        parts = key.split(":", 1)
        if len(parts) == 2:
            obs_id = parts[1]
        else:
            obs_id = key
        
        # Use first value for longitudinal metrics, or aggregate
        if obs_series.values:
            if obs_id.startswith("longitudinal_metric:"):
                snapshot[obs_id] = obs_series.values[0]
            else:
                # For section metrics, could use mean or specific station
                snapshot[obs_id] = sum(obs_series.values) / len(obs_series.values)
    
    return snapshot


def _compute_comparisons(
    snapshot: Dict[str, float],
    targets: Dict[str, float],
) -> Dict[str, Comparison]:
    """Compute comparison for each target."""
    from magnet.kernel.geometry_observables import get_observable_spec
    
    comparisons = {}
    
    for obs_id, target_val in targets.items():
        current_val = snapshot.get(obs_id)
        if current_val is None:
            continue
        
        delta = target_val - current_val
        delta_pct = (delta / abs(current_val) * 100) if current_val != 0 else 0
        
        # Determine status based on tolerance
        spec = get_observable_spec(obs_id)
        tolerance = spec.tolerance if spec else 0.05
        
        if abs(delta) <= tolerance:
            status = "met"
        elif abs(delta) <= tolerance * 3:
            status = "close"
        else:
            status = "off"
        
        controllable = spec.controllable if spec else False
        
        comparisons[obs_id] = Comparison(
            current=round(current_val, 3),
            target=round(target_val, 3),
            delta=round(delta, 3),
            delta_pct=round(delta_pct, 1),
            status=status,
            controllable=controllable,
        )
    
    return comparisons
```

### 11.3 File Location

```
magnet/kernel/shape_document.py  (NEW FILE)
```

### 11.4 Integration with spiral_endpoints.py

```python
# In magnet/deployment/spiral_endpoints.py

from magnet.kernel.shape_document import generate_shape_document, get_target_profile

@router.post("/api/v1/designs/{design_id}/shape-document")
async def get_shape_document(
    design_id: str,
    target_profile_id: Optional[str] = None,
    custom_targets: Optional[Dict[str, float]] = None,
):
    """
    Generate Shape Document for current hull state.
    
    Args:
        design_id: Design to analyze
        target_profile_id: Named profile ("viking_sportfisher", etc.)
        custom_targets: Explicit target values
    
    Returns:
        ShapeDocument JSON
    """
    state = await get_design_state(design_id)
    geometry = await compile_geometry(state)
    
    target_profile = None
    if target_profile_id:
        target_profile = get_target_profile(target_profile_id)
    elif custom_targets:
        target_profile = {
            "profile_id": "custom",
            "source": "explicit",
            "targets": custom_targets,
        }
    
    doc = generate_shape_document(
        state=state,
        geometry=geometry,
        target_profile=target_profile,
    )
    
    return doc.to_dict()


# PRIMARY WIRING: Shape Document flows into the model automatically in EDIT mode
@router.post("/api/v1/designs/{design_id}/iterate")
async def iterate_design(design_id: str, request: "IterateRequest"):
    """
    One-shot iteration endpoint.

    - CREATE: model generates a new hull
    - EDIT: model emits ADJUST/TARGET using shape_document context
    - REWRITE: model regenerates hull (requires explicit confirmation)
    """
    state = await get_design_state(design_id)
    mode = infer_mode(request.intent, state, explicit_mode=getattr(request, "mode", None))

    geometry = None
    shape_doc = None
    if mode == "EDIT":
        geometry = await compile_geometry(state)
        shape_doc = generate_shape_document(
            state=state,
            geometry=geometry,
            target_profile_id=getattr(request, "target_profile_id", None),
            target_profile=getattr(request, "target_profile", None),
        ).to_dict()

    proposal = await proposer.propose(
        intent=request.intent,
        mode=mode,
        current_state=state,
        shape_document=shape_doc,
    )

    # EDIT mode must be verb-restricted (see §15.3.1) and diff-budget guarded (see §15.5)
    if mode == "EDIT":
        validate_edit_mode_program(proposal.program_text)

    await execute_program(design_id, proposal.program_text)

    # Always return updated shape_document after an EDIT turn
    updated_state = await get_design_state(design_id)
    updated_geometry = await compile_geometry(updated_state)
    updated_doc = generate_shape_document(
        state=updated_state,
        geometry=updated_geometry,
        target_profile_id=getattr(request, "target_profile_id", None),
        target_profile=getattr(request, "target_profile", None),
    )

    return {
        "success": True,
        "mode": mode,
        "state": updated_state,
        "shape_document": updated_doc.to_dict(),
    }


# Include in EDIT mode responses
@router.post("/api/v1/designs/{design_id}/edit")
async def edit_design(design_id: str, request: EditRequest):
    # ... execute edits ...
    
    # Generate shape document for response
    doc = generate_shape_document(
        state=updated_state,
        geometry=updated_geometry,
        target_profile=request.target_profile,
    )
    
    return {
        "success": True,
        "state": updated_state,
        "shape_document": doc.to_dict(),  # Always include
    }
```

### 11.5 Request Flow Wiring (Agent-Executable Spec)

**Single source of truth (no ambiguity)**:
- Shape Document generation lives in: `magnet/kernel/shape_document.py`
- Request orchestration lives in: `magnet/deployment/spiral_endpoints.py`
- The proposer consumes a precomputed `shape_document` in EDIT mode: `magnet/agents/geometry_proposer.py`

**Canonical call chain (EDIT turn)**:

```python
# magnet/deployment/spiral_endpoints.py
#
# 1) read state
# 2) compile geometry (kernel)
# 3) generate shape_document (kernel)
# 4) call proposer with shape_document (agents)
# 5) validate program: EDIT verb whitelist (server)
# 6) execute program (kernel)
# 7) recompile + regenerate shape_document (kernel)
# 8) return response (server)

async def iterate_design(design_id: str, request: IterateRequest) -> Dict[str, Any]:
    state_before = await get_design_state(design_id)
    mode = infer_mode(request.intent, state_before, explicit_mode=request.mode)

    shape_doc = None
    if mode == "EDIT":
        geom_before = await compile_geometry(state_before)
        shape_doc = generate_shape_document(
            state=state_before,
            geometry=geom_before,
            target_profile_id=request.target_profile_id,
            target_profile=request.target_profile,
        ).to_dict()

    proposal = await proposer.propose(
        intent=request.intent,
        mode=mode,
        current_state=state_before,
        shape_document=shape_doc,
    )

    if mode == "EDIT":
        validate_edit_mode_program(proposal.program_text)

    await execute_program(design_id, proposal.program_text)

    state_after = await get_design_state(design_id)
    geom_after = await compile_geometry(state_after)
    doc_after = generate_shape_document(
        state=state_after,
        geometry=geom_after,
        target_profile_id=request.target_profile_id,
        target_profile=request.target_profile,
    )

    return {
        "success": True,
        "mode": mode,
        "state": state_after,
        "shape_document": doc_after.to_dict(),
    }
```

**Non-goals (guardrails)**:
- Do **not** generate shape_document inside the proposer.
- Do **not** import `magnet/agents/*` from `magnet/kernel/*`.
- Proposer treats `shape_document` as read-only context, never recomputes it.

**Sequence diagram (EDIT)**:

```
User
  │  intent + target_profile_id
  ▼
API: magnet/deployment/spiral_endpoints.py  (/iterate or /edit)
  │  get_design_state()
  │  compile_geometry()
  │  generate_shape_document()
  ▼
Proposer: magnet/agents/geometry_proposer.py
  │  consumes shape_document, emits ADJUST/TARGET program_text
  ▼
API gate: validate_edit_mode_program()
  ▼
Kernel: execute_program()  → StateManager commit → design_version++
  │  compile_geometry()
  │  generate_shape_document()
  ▼
API response: {state, shape_document, mode}
```

### 11.6 Mode Inference (CREATE vs EDIT vs REWRITE)

**Goal**: deterministically decide mode so the Shape Document wiring is automatic and predictable.

```python
def infer_mode(intent: str, state: Dict[str, Any], *, explicit_mode: Optional[str] = None) -> str:
    """
    Determine mode.

    Priority:
    1) explicit_mode (if present and valid)
    2) if no hull exists -> CREATE
    3) if rewrite intent signals -> REWRITE (requires confirmation gate)
    4) else -> EDIT
    """
    if explicit_mode in {"CREATE", "EDIT", "REWRITE"}:
        return explicit_mode

    resources = (state or {}).get("resources") or {}
    hull_exists = any(
        isinstance(r, dict) and r.get("_type") in {"geometry.section", "geometry.surface", "geometry.body"} and not r.get("_deleted")
        for r in (resources.values() if isinstance(resources, dict) else [])
    )
    if not hull_exists:
        return "CREATE"

    rewrite_signals = ["start over", "completely different", "new hull", "replace hull", "rewrite:"]
    text = (intent or "").lower()
    if any(sig in text for sig in rewrite_signals):
        return "REWRITE"

    return "EDIT"
```

**REWRITE confirmation handshake**:
- If inferred mode is REWRITE, the server must return `needs_clarification` asking for explicit confirmation before allowing identity-breaking edits.
- After user confirms, the next call can pass `explicit_mode="REWRITE"` or a structured confirmation payload.

---

## 12. Target Profiles

### 12.1 How Targets Are Specified

| Source | Priority | Example |
|--------|----------|---------|
| Explicit custom targets | 1 (highest) | `{"sheer_peak_station": 0.72}` |
| Named profile ID | 2 | `target_profile_id="viking_sportfisher"` |
| Inferred from vessel type | 3 | `vessel_type="sportfisher"` → inferred named profile |
| User natural language | 4 | "sheer should peak around 70% forward" |
| None (snapshot only) | 5 | No comparison, just current values |

### 12.2 Named Profile Registry

**Note**: Named profiles are **convenience shortcuts**, not a limit.
- Users can define **custom targets** via prompt (or explicit `custom_targets`).
- The model can **compose targets from any observable values** (mix-and-match across profiles or override selectively).
- If a target profile name is unknown, fall back to `custom_targets` rather than failing.

```python
# magnet/kernel/shape_document.py

TARGET_PROFILES: Dict[str, Dict[str, Any]] = {
    "viking_sportfisher": {
        "profile_id": "viking_sportfisher",
        "source": "named_profile",
        "description": "Viking Yachts sportfisher character",
        "targets": {
            "sheer_peak_station": 0.72,
            "sheer_rise_m": 1.2,
            "stem_rake_deg": 13.0,
            "stem_concavity_ratio": 0.10,
            "entry_half_angle_deg": 11.0,
            "bow_fineness_ratio": 0.22,
            "transom_rake_deg": 12.0,
            "transom_beam_ratio": 0.85,
            # chine_rise_rate is m/m; 0.65 would be absurdly steep (~33°). Use ~6.5% as a plausible target.
            "chine_rise_rate": 0.065,
            "deadrise_drop_deg": 6.0,
            "deadrise_progression_shape": 0.90,
        },
    },
    
    "displacement_trawler": {
        "profile_id": "displacement_trawler",
        "source": "named_profile",
        "description": "Traditional displacement trawler",
        "targets": {
            "sheer_peak_station": 0.95,
            "sheer_rise_m": 0.8,
            "stem_rake_deg": 5.0,
            "stem_concavity_ratio": 0.02,
            "entry_half_angle_deg": 22.0,
            "bow_fineness_ratio": 0.40,
            "transom_rake_deg": 5.0,
            "transom_beam_ratio": 0.70,
            "deadrise_progression_shape": 0.98,
        },
    },
    
    "center_console": {
        "profile_id": "center_console",
        "source": "named_profile",
        "description": "Modern center console fishing boat",
        "targets": {
            "sheer_peak_station": 0.85,
            "sheer_rise_m": 0.6,
            "stem_rake_deg": 10.0,
            "stem_concavity_ratio": 0.05,
            "entry_half_angle_deg": 14.0,
            "transom_beam_ratio": 0.88,
            # m/m (dimensionless); ~4.5% is plausible for CC-style lifted chines.
            "chine_rise_rate": 0.045,
            "deadrise_drop_deg": 5.0,
        },
    },
    
    "express_cruiser": {
        "profile_id": "express_cruiser",
        "source": "named_profile",
        "description": "Express cruiser / weekender",
        "targets": {
            "sheer_peak_station": 0.80,
            "sheer_rise_m": 1.0,
            "stem_rake_deg": 12.0,
            "stem_concavity_ratio": 0.06,
            "entry_half_angle_deg": 13.0,
            "transom_beam_ratio": 0.82,
            "deadrise_progression_shape": 0.92,
        },
    },
}


def get_target_profile(profile_id: str) -> Optional[Dict[str, Any]]:
    """Get a named target profile."""
    return TARGET_PROFILES.get(profile_id)


def list_target_profiles() -> List[str]:
    """List available profile IDs."""
    return list(TARGET_PROFILES.keys())


def infer_profile_from_vessel_type(vessel_type: str) -> Optional[str]:
    """Map vessel type to profile ID."""
    mapping = {
        "sportfisher": "viking_sportfisher",
        "sportfishing": "viking_sportfisher",
        "viking": "viking_sportfisher",
        "trawler": "displacement_trawler",
        "displacement": "displacement_trawler",
        "center_console": "center_console",
        "cc": "center_console",
        "express": "express_cruiser",
        "cruiser": "express_cruiser",
    }
    return mapping.get(vessel_type.lower().replace(" ", "_").replace("-", "_"))
```

### 12.3 Custom Targets from User Prompt

When user says "sheer should peak around 70% forward", the proposer extracts:

```python
custom_targets = {
    "sheer_peak_station": 0.70,
}
```

This merges with any named profile (custom overrides profile).

### 12.4 No Target Mode

When `target_profile=None`:
- `observable_snapshot` is populated
- `comparison` is empty
- `critique_hints` is empty
- `suggested_adjustments` is empty
- Model sees current state but no guidance

Useful for: initial exploration, "show me what we have"

---

## 13. Critique Generation

### 13.1 Rule-Based Critique from Deltas

Each observable has a critique template that generates natural language from delta magnitude and direction.

```python
# magnet/kernel/shape_document.py

CRITIQUE_TEMPLATES: Dict[str, Dict[str, str]] = {
    "sheer_peak_station": {
        "too_high": "Sheer peaks too far forward ({current} vs {target} target) — lacks teardrop character",
        "too_low": "Sheer peaks too far aft ({current} vs {target} target) — bow looks heavy",
    },
    "entry_half_angle_deg": {
        "too_high": "Entry too blunt ({current}° vs {target}° target) — will pound in chop",
        "too_low": "Entry too fine ({current}° vs {target}° target) — may lack buoyancy forward",
    },
    "transom_beam_ratio": {
        "too_high": "Transom too wide ({current} vs {target} target) — may look boxy",
        "too_low": "Transom too narrow ({current} vs {target} target) — reduced planing stability",
    },
    "stem_rake_deg": {
        "too_high": "Stem too raked ({current}° vs {target}° target) — aggressive but may lose waterline length",
        "too_low": "Stem too vertical ({current}° vs {target}° target) — lacks character",
    },
    "stem_concavity_ratio": {
        "too_high": "Stem concavity too high ({current} vs {target} target) — may look overly hooked",
        "too_low": "Stem too straight ({current} vs {target} target) — lacks aggressive forward reach",
    },
    "chine_rise_rate": {
        "too_high": "Chine rises too aggressively ({current} vs {target} target) — may affect running trim",
        "too_low": "Chine too flat ({current} vs {target} target) — lacks lifted bow character",
    },
    "deadrise_progression_shape": {
        "too_high": "Deadrise too warped (warp_score={current} vs {target} target) — may affect predictability",
        "too_low": "Deadrise too linear (warp_score={current} vs {target} target) — lacks warped bottom character",
    },
    "deadrise_drop_deg": {
        "too_high": "Deadrise varies too much ({current}° vs {target}° target) — extreme warp",
        "too_low": "Deadrise too constant ({current}° vs {target}° target) — lacks variation",
    },
    "bow_fineness_ratio": {
        "too_high": "Bow too full ({current} vs {target} target) — blunt entry",
        "too_low": "Bow too fine ({current} vs {target} target) — may lack reserve buoyancy",
    },
}


def _generate_critique_hints(comparisons: Dict[str, Comparison]) -> List[str]:
    """Generate natural language critique hints from comparisons."""
    hints = []
    
    # Sort by absolute delta percentage (biggest misses first)
    sorted_comps = sorted(
        [(k, v) for k, v in comparisons.items() if v.status == "off"],
        key=lambda x: abs(x[1].delta_pct or 0),
        reverse=True,
    )
    
    for obs_id, comp in sorted_comps[:5]:  # Top 5 issues
        templates = CRITIQUE_TEMPLATES.get(obs_id)
        if not templates:
            continue
        
        direction = "too_high" if (comp.delta or 0) < 0 else "too_low"
        template = templates.get(direction)
        if not template:
            continue
        
        hint = template.format(
            current=comp.current,
            target=comp.target,
        )
        hints.append(hint)
    
    return hints
```

### 13.2 Critique Characteristics

| Property | Value |
|----------|-------|
| Source | Rule-based (not LLM-generated) |
| Deterministic | Yes |
| Domain-aware | Yes (naval architecture terms) |
| Actionable | Yes (implies what to fix) |
| Token cost | ~40 tokens per hint |

### 13.3 Example Critiques

| Observable | Delta | Generated Critique |
|------------|-------|-------------------|
| `sheer_peak_station` | -0.20 | "Sheer peaks too far forward (0.92 vs 0.72 target) — lacks teardrop character" |
| `entry_half_angle_deg` | -7.2 | "Entry too blunt (18.2° vs 11.0° target) — will pound in chop" |
| `transom_beam_ratio` | +0.09 | "Transom too narrow (0.76 vs 0.85 target) — reduced planing stability" |

---

## 14. Suggested Adjustments

### 14.1 Auto-Generation from Deltas

For each comparison where `status == "off"`, generate a suggested adjustment if the observable (or a related controllable observable) can be adjusted.

```python
# magnet/kernel/shape_document.py

# Map non-controllable observables to controllable alternatives
ADJUSTMENT_MAPPINGS: Dict[str, Dict[str, Any]] = {
    "sheer_peak_station": {
        "controllable_via": "section_metric:sheer_z_m",
        "scope_strategy": "mid_forward",  # Adjust sheer in 0.6-0.8 region
        "rationale_template": "Raise sheer in mid-forward region to shift peak {direction}",
    },
    "entry_half_angle_deg": {
        "controllable_via": "section_metric:max_half_beam_m",
        "scope_strategy": "forward",  # Adjust beam in 0.85-1.0 region
        "rationale_template": "{action} forward beam to {action2} entry",
    },
    "transom_beam_ratio": {
        "controllable_via": "section_metric:max_half_beam_m",
        "scope_strategy": "aft",  # Adjust beam at station 0-0.15
        "rationale_template": "{action} aft beam to {action2} transom width",
    },
    "chine_rise_rate": {
        "controllable_via": "section_metric:sheer_z_m",  # Proxy via chine z
        "scope_strategy": "forward",
        "rationale_template": "Adjust chine height in forward sections",
    },
    "deadrise_drop_deg": {
        "controllable_via": "section_metric:deadrise_deg_at_chine",
        "scope_strategy": "forward",
        "rationale_template": "Adjust forward deadrise to {action2} variation",
    },
}

SCOPE_STRATEGIES: Dict[str, Dict[str, Any]] = {
    "forward": {"station_range": [0.85, 1.0]},
    "mid_forward": {"station_range": [0.6, 0.8]},
    "aft": {"station_range": [0.0, 0.15]},
    "midship": {"station_range": [0.4, 0.6]},
    "full": {},  # No scope restriction
}


def _generate_suggested_adjustments(
    comparisons: Dict[str, Comparison],
) -> List[SuggestedAdjustment]:
    """Generate suggested ADJUST/TARGET statements from comparisons."""
    from magnet.kernel.geometry_observables import get_observable_spec
    
    suggestions = []
    
    # Sort by absolute delta (biggest misses first)
    sorted_comps = sorted(
        [(k, v) for k, v in comparisons.items() if v.status == "off"],
        key=lambda x: abs(x[1].delta or 0),
        reverse=True,
    )
    
    for obs_id, comp in sorted_comps[:5]:  # Top 5
        spec = get_observable_spec(obs_id)
        
        # If directly controllable, suggest direct adjustment
        if spec and spec.controllable:
            suggestions.append(SuggestedAdjustment(
                observable_id=obs_id,
                scope={},
                operation="ADJUST",
                delta=comp.delta,
                value=None,
                unit=spec.unit,
                rationale=f"Direct adjustment to reach target",
            ))
            continue
        
        # Otherwise, use mapping to controllable alternative
        mapping = ADJUSTMENT_MAPPINGS.get(obs_id)
        if not mapping:
            continue
        
        ctrl_obs = mapping["controllable_via"]
        ctrl_spec = get_observable_spec(ctrl_obs)
        if not ctrl_spec:
            continue
        
        scope = SCOPE_STRATEGIES.get(mapping["scope_strategy"], {})
        
        # Estimate delta for controllable observable
        # (simplified: use same delta magnitude, may need scaling)
        ctrl_delta = comp.delta
        if ctrl_spec.unit == "m" and spec.unit == "deg":
            ctrl_delta = comp.delta * 0.1  # Rough scaling
        elif ctrl_spec.unit == "deg" and spec.unit == "ratio":
            ctrl_delta = comp.delta * 10  # Rough scaling
        
        # Generate rationale
        direction = "aft" if (comp.delta or 0) > 0 else "forward"
        action = "Increase" if (ctrl_delta or 0) > 0 else "Decrease"
        action2 = "widen" if (ctrl_delta or 0) > 0 else "narrow"
        
        rationale = mapping["rationale_template"].format(
            direction=direction,
            action=action,
            action2=action2,
        )
        
        suggestions.append(SuggestedAdjustment(
            observable_id=ctrl_obs,
            scope=scope,
            operation="ADJUST",
            delta=round(ctrl_delta, 2) if ctrl_delta else None,
            value=None,
            unit=ctrl_spec.unit,
            rationale=rationale,
        ))
    
    return suggestions[:5]  # Cap at 5
```

### 14.2 Suggestion Characteristics

| Property | Value |
|----------|-------|
| Only controllable observables | Yes |
| Ranked by delta magnitude | Yes |
| Capped at 3-5 | Yes |
| Includes scope | Yes (station_range) |
| Includes rationale | Yes |

### 14.3 Example Suggestions

```json
{
  "suggested_adjustments": [
    {
      "observable_id": "section_metric:max_half_beam_m",
      "scope": {"station_range": [0.85, 1.0]},
      "operation": "ADJUST",
      "delta": -0.8,
      "unit": "m",
      "rationale": "Decrease forward beam to narrow entry"
    },
    {
      "observable_id": "section_metric:sheer_z_m",
      "scope": {"station_range": [0.6, 0.8]},
      "operation": "ADJUST",
      "delta": 0.4,
      "unit": "m",
      "rationale": "Raise sheer in mid-forward region to shift peak aft"
    },
    {
      "observable_id": "section_metric:max_half_beam_m",
      "scope": {"station_range": [0.0, 0.15]},
      "operation": "ADJUST",
      "delta": 0.3,
      "unit": "m",
      "rationale": "Increase aft beam to widen transom width"
    }
  ]
}
```

---

## 15. Integration with Proposer

### 15.1 EDIT Mode Context

In EDIT mode, the proposer receives the Shape Document as part of its context:

```python
# magnet/agents/geometry_proposer.py

async def propose_edit(
    self,
    intent: str,
    current_state: Dict[str, Any],
    shape_document: Optional[Dict[str, Any]] = None,
) -> ProposalResult:
    """
    Propose edits to existing hull.
    
    Args:
        intent: User's edit intent
        current_state: Current design state
        shape_document: Pre-computed shape analysis (if available)
    """
    
    # Build context for model
    context = {
        "mode": "EDIT",
        "intent": intent,
        "current_dimensions": _extract_dimensions(current_state),
    }
    
    if shape_document:
        context["shape_analysis"] = {
            "observable_snapshot": shape_document.get("observable_snapshot"),
            "comparison": shape_document.get("comparison"),
            "critique_hints": shape_document.get("critique_hints"),
            "suggested_adjustments": shape_document.get("suggested_adjustments"),
            "quality_summary": shape_document.get("quality_summary"),
        }
    
    # Model sees: current state, deltas, critique, suggested fixes
    # Model can: accept suggestions, modify them, or propose different approach
```

### 15.2 System Prompt Addition

```
SHAPE DOCUMENT (EDIT MODE)

When editing an existing hull, you receive a Shape Document containing:

1. OBSERVABLE_SNAPSHOT: Current measured values for all character observables
2. COMPARISON: For each target, shows current/target/delta/status
3. CRITIQUE_HINTS: Pre-computed analysis of what's wrong (in domain terms)
4. SUGGESTED_ADJUSTMENTS: Pre-computed ADJUST statements to fix issues

YOUR WORKFLOW:
1. Review critique_hints to understand what's wrong
2. Review suggested_adjustments as starting points
3. Either:
   a) Accept suggestions as-is (emit them in your program)
   b) Modify suggestions (adjust deltas, change scope)
   c) Propose different approach (if you see a better fix)

IMPORTANT:
- You do NOT need to spatially reason from coordinates
- The Shape Document pre-computes everything you need
- Focus on: "Is the delta reasonable? Is the scope right?"
- Trust the measurements; critique the strategy

EXAMPLE:
If shape_document shows:
  critique: "Entry too blunt (18° vs 11° target)"
  suggestion: "ADJUST max_half_beam_m AT station_range=(0.85,1.0) BY -0.8m"

You might:
  - Accept: emit the suggestion as-is
  - Modify: change delta to -0.6m if -0.8m seems aggressive
  - Alternative: suggest adjusting deadrise instead if that's more appropriate
```

### 15.3 Model Response Flow

```
1. Model receives: intent + shape_document
2. Model reviews: critique_hints (what's wrong)
3. Model considers: suggested_adjustments (pre-computed fixes)
4. Model decides: accept / modify / alternative
5. Model emits: ADJUST/TARGET statements
6. Kernel executes: applies changes
7. New shape_document generated: model sees updated state
8. Iterate until: quality_summary.targets_met >= threshold
```

### 15.3.1 EDIT Mode Verb Restrictions (Server-side gate)

In EDIT mode, the program is restricted to:
- `ADJUST ...`
- `TARGET ...`
- `SET metadata.* = ...`

Everything else (`CREATE`, `UPDATE`, `DELETE`, `LOFT`, etc.) is rejected **before execution**.

```python
EDIT_MODE_ALLOWED_VERBS = {"ADJUST", "TARGET", "SET"}

class EditModeViolation(RuntimeError):
    pass

def validate_edit_mode_program(program_text: str) -> None:
    """
    Reject CREATE/UPDATE/DELETE/LOFT (and any other verbs) in EDIT mode.
    Allow `SET metadata.* = ...` only.
    """
    for raw in (program_text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        verb = line.split()[0]
        if verb not in EDIT_MODE_ALLOWED_VERBS:
            raise EditModeViolation(f"Verb '{verb}' not allowed in EDIT mode")
        if verb == "SET" and not line.startswith("SET metadata."):
            raise EditModeViolation("Only `SET metadata.*` is allowed in EDIT mode")
```

### 15.4 Quality Gate

```python
def should_continue_editing(shape_document: Dict[str, Any]) -> bool:
    """Determine if more edits are needed."""
    summary = shape_document.get("quality_summary", {})
    
    targets_met = summary.get("targets_met", 0)
    targets_defined = summary.get("targets_defined", 0)
    
    if targets_defined == 0:
        return False  # No targets, nothing to iterate toward
    
    # Continue if less than 80% of targets met
    return (targets_met / targets_defined) < 0.8
```

### 15.5 Iteration Orchestration (Who runs the loop)

The system needs an orchestrator that:
- Regenerates shape_document each iteration (so the model sees updated measurements)
- Stops when quality gate passes
- Caps iterations to prevent runaway loops
- Lives in `magnet/deployment/spiral_endpoints.py` (server orchestration layer)

```python
async def edit_until_converged(
    design_id: str,
    intent: str,
    *,
    target_profile_id: Optional[str] = None,
    max_iterations: int = 5,
) -> Dict[str, Any]:
    """
    Server-side loop for EDIT mode. Returns final state + shape_document.
    """
    for i in range(max_iterations):
        state = await get_design_state(design_id)
        geometry = await compile_geometry(state)
        doc = generate_shape_document(state=state, geometry=geometry, target_profile_id=target_profile_id)

        if not should_continue_editing(doc.to_dict()):
            return {"converged": True, "iterations": i, "state": state, "shape_document": doc.to_dict()}

        proposal = await proposer.propose(
            intent=intent,
            mode="EDIT",
            current_state=state,
            shape_document=doc.to_dict(),
        )
        validate_edit_mode_program(proposal.program_text)
        await execute_program(design_id, proposal.program_text)

    # Final snapshot after max_iterations
    final_state = await get_design_state(design_id)
    final_geom = await compile_geometry(final_state)
    final_doc = generate_shape_document(state=final_state, geometry=final_geom, target_profile_id=target_profile_id)
    return {"converged": False, "iterations": max_iterations, "state": final_state, "shape_document": final_doc.to_dict()}
```

### 15.6 Diff Budget / Identity Guard (Prevent stealth rewrites)

Even if a program uses only ADJUST/TARGET, it can still effectively rewrite a hull by touching “everything”.
Add a guard that measures how many stations were materially changed and, if it exceeds 50%, return `needs_clarification` (“this looks like a rewrite”).

```python
def sections_equivalent(a: Any, b: Any, *, eps: float = 1e-9) -> bool:
    # Implementation detail: compare point arrays (y,z) and hard-edge indices;
    # allow tiny numeric jitter.
    return _points_close(a.points, b.points, eps=eps) and _hard_edge_track_equal(a, b)

def check_edit_scope(before: Any, after: Any) -> Dict[str, Any]:
    total = len(getattr(before, "sections", []) or [])
    if total <= 0:
        return {"allowed": True, "affected_ratio": 0.0}

    affected = 0
    for b, a in zip(before.sections, after.sections):
        if not sections_equivalent(b, a):
            affected += 1
    ratio = affected / max(1, total)
    if ratio > 0.5:
        return {
            "allowed": False,
            "needs_clarification": True,
            "reason": f"Edit affects {ratio:.0%} of stations; this looks like a rewrite. Confirm?",
        }
    return {"allowed": True, "affected_ratio": ratio}
```

---

## 16. Implementation Checklist

### Phase 1: Shape Document Core

- [ ] Create `magnet/kernel/shape_document.py`
- [ ] Implement `ShapeDocument` dataclass
- [ ] Implement `generate_shape_document()` function
- [ ] Implement `_measure_all_observables()` (uses existing infrastructure)
- [ ] Implement `_compute_comparisons()`
- [ ] Add unit tests for shape document generation

### Phase 2: Target Profiles

- [ ] Define `TARGET_PROFILES` registry
- [ ] Implement `get_target_profile()`
- [ ] Implement `infer_profile_from_vessel_type()`
- [ ] Add tests for profile loading

### Phase 3: Critique & Suggestions

- [ ] Define `CRITIQUE_TEMPLATES`
- [ ] Implement `_generate_critique_hints()`
- [ ] Define `ADJUSTMENT_MAPPINGS`
- [ ] Implement `_generate_suggested_adjustments()`
- [ ] Add tests for critique/suggestion generation

### Phase 4: API Integration

- [ ] Add `/api/v1/designs/{id}/shape-document` endpoint
- [ ] Include shape_document in EDIT mode responses
- [ ] Update proposer to accept shape_document context

### Phase 5: Proposer Integration

- [ ] Update system prompt with Shape Document guidance
- [ ] Implement `propose_edit()` with shape_document parameter
- [ ] Add quality gate logic
- [ ] Add integration tests

### 16.5 Test Fixtures (Agent-Ready)

**Goal**: prevent incorrect mocking. Provide a single fixture factory that returns real-ish state + compiled geometry.

**Fixture signature**:

```python
# tests/fixtures/hulls.py (NEW)

from typing import Any, Dict, Tuple

def make_viking_style_hull(
    *,
    loa_m: float = 22.0,
    stations: int = 11,
    points_per_section: int = 8,
    surface_definition: str = "smooth",
    target_profile_id: str = "viking_sportfisher",
) -> Tuple[Dict[str, Any], Any]:
    """
    Create a deterministic, test-friendly Viking-like hull.

    Returns:
      state_dict: DesignState-like dict suitable for compile_geometry / shape_document generation
      geometry: compiled HullGeometry (result of kernel compilation)

    Requirements:
    - sections exist and are sorted by x_position
    - station convention is canonical (0=aft, 1=forward) but tests must use x_position SSOT
    - feature curves are populated (keel_profile, chine_curve, deck_edge, transom_outline, stem_profile may be empty if not derivable)
    - surface_definition explicitly set
    """
    # Implementation options:
    # A) Build resources dict (geometry.body/section/surface) and call kernel compiler
    # B) If a helper exists, reuse it (preferred)
    raise NotImplementedError
```

**What this fixture must NOT do**:
- Do not stub observables directly (tests must go through real measurers)
- Do not hand-wave stations using `section.station` (tests must validate x_position-based normalization)

**Minimum test return contract**:
- `state_dict["hull"]["loa"] == loa_m`
- `state_dict["resources"]` contains:
  - at least 1 `geometry.body`
  - at least 2 `geometry.section`
  - exactly 1 `geometry.surface` with `surface_definition`
- `geometry.sections` exists and has matching x_position ordering


---

## Appendix C: Token Budget Validation

### Minimal Shape Document (~800 tokens)

```json
{
  "hull_identity": {"hull_id": "X", "design_version": 1},
  "principal_dimensions": {"loa_m": 22, "beam_m": 6.2},
  "observable_snapshot": {
    "sheer_peak_station": 0.92,
    "entry_half_angle_deg": 18.2,
    "transom_beam_ratio": 0.76
  },
  "comparison": {
    "sheer_peak_station": {"current": 0.92, "target": 0.72, "delta": -0.20, "status": "off"}
  },
  "critique_hints": ["Sheer peaks too far forward"],
  "suggested_adjustments": [{"observable_id": "sheer_z_m", "delta": 0.4}]
}
```

### Full Shape Document (~1400 tokens)

Complete example with all fields populated (see §10.2).

### Budget Compliance

| Scenario | Tokens | Status |
|----------|--------|--------|
| Minimal | ~800 | ✅ Under budget |
| Typical | ~1200 | ✅ Under budget |
| Full | ~1400 | ✅ Under budget |
| Maximum | ~1500 | ✅ At budget |

---

## Appendix D: Shape Document vs Raw Geometry

### What the Model Sees

**Without Shape Document** (bad):
```
sections: [
  {station: 0.0, points: [[0, -1.5], [2.1, -1.2], [2.3, -0.8], ...]},
  {station: 0.12, points: [[0, -1.4], [2.2, -1.1], [2.4, -0.7], ...]},
  ...
]
```
Model cannot reason about this spatially.

**With Shape Document** (good):
```
observable_snapshot: {sheer_peak_station: 0.92, entry_half_angle_deg: 18.2}
comparison: {sheer_peak_station: {current: 0.92, target: 0.72, delta: -0.20}}
critique: "Sheer peaks too far forward — lacks teardrop character"
suggestion: "ADJUST sheer_z_m AT station_range=(0.6,0.8) BY +0.4m"
```
Model can reason numerically and accept/modify suggestions.
