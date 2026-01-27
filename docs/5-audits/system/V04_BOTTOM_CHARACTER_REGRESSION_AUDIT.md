## v0.4 Regression Audit — “Bottom Character is Gone”

### Scope
This audit explains why the latest Viking prompt **looks like it lost deep‑V / warped bottom character** after the v0.4 changes, and what the most likely fix is.

Design examined:
- `storage/designs/MAGNET-20260118-5BF68653.json`

---

## 1) Quick facts from the saved design (this run)

### 1.1 Geometry content is present (not a “missing hull” case)
- **Sections**: 9 (`geometry.section` resources)
- **HARD edges**: exactly 1 HARD vertex per section (edge_types contains one `"hard"` each)
- **Surface**: `geometry.surface` exists with `surface_definition: "smooth"` and ordered `section_ids`
- **Discontinuity**: `geometry.discontinuity chine_line` exists (but note: current observables use section point `edge_type`, not discontinuity resources)

### 1.2 The thinking-pass artifact is not persisted in the design JSON
Search in the design JSON shows **no** `metadata.vessel_thinking_pass` or `vessel_thinking_pass_hash`.

Impact:
- We cannot inspect **binding_table** / observation_targets / DEFAULTED vs VERIFIED DOFs for this run from the persisted state.
- This removes the strongest debug artifact (“what the model claimed and bound”).

---

## 2) What the kernel observables actually measure for this run

Even without the stored thinking pass, we can compute observables from the persisted `program_text` via the existing dry-run pipeline.

Computed (from the saved `program_text` in `phase_states.hull_form.spiral.checkpoints[0]`):

- **`section_metric:deadrise_deg_at_chine`**:
  - values: `[26.56, 25.46, 24.44, 23.50, 24.44, 29.05, 37.57, 48.37, 63.43]`
  - span: ~39.94°

- **`longitudinal_metric:deadrise_drop_deg`**:
  - value: **~24.30°**

- **`longitudinal_metric:keel_slope_deg_p95`**:
  - value: **~15.28°**

- **v0.4 profile observables also compute**:
  - `sheer_rise_m`: ~3.0
  - `entry_fineness_p95`: ~0.678
  - `section_metric:topside_angle_deg_above_chine` span: ~8.84°

### Why these numbers are a red flag
The bottom metrics are now so large that they can “pass” almost any threshold, even if the hull doesn’t visually read as intended:
- `deadrise_drop_deg ~24°` is **implausibly large** for the intended meaning “entry vs run deadrise schedule difference”.
- `keel_slope_deg_p95 ~15°` indicates extremely aggressive rocker/forefoot lift, which can distort the global look.

This suggests the *measurement proxy* is being satisfied in a way that does not correspond to the user’s mental model of “warped deep‑V” (i.e., the ruler is being gamed).

---

## 3) Root cause (most likely): “HARD chine” anchoring is not landing on the chine

The current deadrise proxy (`section_metric:deadrise_deg_at_chine`) uses:
- keel = min z point
- chine = most outboard **HARD** point

In this run, each section has exactly one `"hard"` entry, but it is **not obviously at the chine breakline** (it’s at an interior point, not the deck-edge or the likely chine/waterline knee).

Consequences:
- `deadrise_deg_at_chine` becomes “keel → arbitrary hard vertex” angle, which can explode toward 60°+ as y gets small near the bow.
- `deadrise_drop_deg` becomes “difference between two averages of a noisy proxy”, which can become very large even without meaningful bottom warping.

Net: the bottom “truth” contract becomes toothless, because the anchor is drifting.

---

## 4) Station mapping fix is NOT the direct cause of bottom loss (but it changed semantics)

After the v0.4 station fix, compiled x positions match the canonical convention:
- station 0.02 → x ≈ 0.439 m (aft)
- station 0.98 → x ≈ 21.511 m (forward)

So the system is no longer silently inverted. That’s correct.

However, it *exposes* proxy weaknesses:
- when the fore/aft meaning becomes consistent, the model can now exploit the proxy more reliably (e.g., make the bow extremely narrow so the “chine” proxy becomes nearly vertical).

---

## 5) Secondary contributor: incentive shift toward new profile observables

Now that profile/topside observables exist, the model can satisfy “sharp entry / flare / sheer” claims with measurable rulers.
If it does not also bind bottom DOFs (or binds them but with a weak proxy), it can appear that bottom character regressed even while “some rulers are satisfied”.

Because the thinking pass is not persisted for this run, we cannot prove whether the model bound bottom DOFs or defaulted them — but this is a plausible contributor.

---

## 6) Suggested fix (minimal, high ROI)

### Fix A (highest ROI): make “chine anchoring” robust so the bottom ruler can’t be gamed
Two minimal options:

1) **Proposer normalization (preferred for v0.4.x hotfix)**
   - If a section has exactly one HARD vertex, snap that HARD marker to the point that best matches “chine knee”:
     - heuristic: among points with z closest to 0 (baseline/waterline convention used elsewhere), choose the max-y point and mark that index HARD.
   - This preserves the existing observable definition and makes deadrise/rules meaningful again.

2) **Observable definition change (slightly larger blast radius)**
   - Redefine `deadrise_deg_at_chine` to compute against an interpolated “z=0 crossing” point rather than HARD.
   - This is more robust across LLM outputs, but it changes the meaning of the observable and will require test updates.

### Fix B: re-enable persistence of the thinking pass artifact
Ensure the design store includes `metadata.vessel_thinking_pass` + hash so we can audit:
- which DOFs were DEFAULTED vs VERIFIED
- what was bound to bottom vs profile observables
- what targets were claimed and whether they were met

### Fix C: add a “chine presence coverage” observable (optional)
To prevent “bathtub-ish” hulls:
- measure fraction of stations where chine is measurable (HARD present and in the expected region)
- fail-closed when the prompt claims “crisp chine” but coverage is low

---

## 7) Immediate answer to your check question
> “What did the thinking pass report for `deadrise_drop_deg` computed value?”

The thinking pass wasn’t persisted in this run, but the kernel’s computed value from the actual emitted program is:
- **`longitudinal_metric:deadrise_drop_deg ≈ 24.30°`**

That magnitude strongly indicates the proxy is being satisfied in a way that isn’t semantically “warped deep‑V” in the intended sense.

