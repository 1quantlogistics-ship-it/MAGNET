## Viking “Essence” Audit (Why the hull bottom improved but the boat no longer reads like a Viking)

### Context (what you observed)
- The **bottom character** (deep‑V, rocker/run cues) is materially better after v0.2/v0.3 observables + enforcement.
- But the **overall silhouette / vessel essence** is drifting away from what a Viking sportfisher “reads like” (your reference image).

This audit focuses on *why the system’s attention shifted*, and what’s actually going wrong in the pipeline.

---

## Finding 1 (High confidence): We have a longitudinal “station” convention contradiction that can flip bow/stern intent

### Evidence A — design-language payload is authored as “station 0 = transom/stern”
Your saved design program uses:
- `section_transom` at `station: 0.0`
- `section_bow` at `station: 1.0`

See the persisted program text inside:
- `storage/designs/MAGNET-20260118-16216E49.json` (checkpoint program_text and resources)

### Evidence B — the section compiler defines the opposite mapping (station 0 = bow, station 1 = stern)
In `magnet/kernel/stdlib/section_compiler.py`:

```73:97:magnet/kernel/stdlib/section_compiler.py
    The resource format:
        {
            "_type": "geometry.section",
            "station": 0.5,  # 0=bow, 1=stern
            ...
        }
...
    # Compute x position from station
    # Station 0 = bow (x = loa), Station 1 = stern (x = 0)
    station_m = (1.0 - station_ratio) * loa
```

### Evidence C — the canonical HullSection docstring says station is “0=AP (aft), 1=FP (forward)”
In `magnet/hull_gen/geometry.py`:

```165:170:magnet/hull_gen/geometry.py
    station: float = 0.0
    """Station position (fraction of LWL from AP, 0 = AP, 1 = FP)."""
```

### Why this matters for “Viking essence”
Even if the bottom metrics are being enforced, a flipped station convention means the model’s intended distribution can land at the wrong end:
- “sharp entry forward” might be applied near the stern in compiled x-space
- “broad aft run / transom” might be applied near the bow in compiled x-space

That produces a hull that can be “deep‑V correct” locally, but the *overall fore/aft story* (which is what you perceive as “essence”) becomes wrong.

### Severity
**High.** This is a *core coordinate/contract contradiction*, not a taste issue.

### Suggested fix (not executed here)
Pick one convention and make it consistent across:
- `geometry.section.station` meaning in the DSL/proposer
- `section_compiler.py` station→x mapping
- docstrings + UI language

Given `HullSection.station` already documents **0=AP (aft), 1=FP (forward)**, the likely correction is:
- change section_compiler mapping to `x_position = station_ratio * loa`
- update its comments accordingly
- then re-validate any downstream code that assumes “bow at x≈0 vs x≈LOA” (observables already rely on `x_position` sorting; they don’t care which end is which, but “forward” subset semantics do).

---

## Finding 2 (Medium confidence): Our “character rulers” now bias the generator toward bottom compliance over topside silhouette

### What we enforce today (v0.2/v0.3)
The contract vocabulary strongly enforces bottom cues:
- deadrise-at-chine proxy
- deadrise drop (entry vs run)
- keel slope / rocker proxy
and now it can enforce *where* those occur via `station_range`.

### What we do not enforce (and what makes a Viking read like a Viking)
A Viking sportfisher’s “essence” in profile/plan view is dominated by **topside and sheerline language**, not just bottom:
- sheerline shape (rise to bow, run to stern)
- bow rake / stem profile
- transom rake + cockpit geometry (even if superstructure is out of scope)
- topside flare distribution (forward flare is a signature)
- chine sweep/height distribution (not just “exists”)

Right now, the generator can satisfy bottom observables without being forced to match those silhouette cues.

### Why your results look like “attention shifted”
Because the system is fail-closed, the model will preferentially “optimize” what is measured and punished:
- it can spend tokens/effort on deadrise/rocker compliance
- while leaving the topside/sheer language underdetermined

This is expected behavior in a contract-driven system: **what you measure becomes what you get**.

---

## Finding 3 (High confidence): The current run is “hull-only,” so the true Viking “vessel” silhouette cannot be matched yet

Your reference image includes (dominant visually):
- deckhouse / windshield line
- flybridge/tower
- foredeck camber and sheer

The current generator in this phase is producing the **hull shell only**. So even with perfect hull lines, the full “Viking vessel” read is structurally impossible right now unless/until we generate at least a minimal:
- deck edge / sheer surface
- simple superstructure envelope (even as a blocky proxy)

This doesn’t negate the station-convention bug above—it just explains why “vessel essence” will always be partially missing in hull-only mode.

---

## What to do next (recommended sequencing)

### 1) Fix the station convention contradiction (highest ROI, correctness)
Before adding more observables, align `station` semantics across:
- DSL authoring expectations
- section compiler station→x mapping
- docstrings + UI expectations

This directly affects whether “entry vs run” is enforced on the correct end of the boat.

### 2) Add 2–3 “profile/topside observables” (to rebalance incentives, not explode scope)
Keep the same “rulers not blueprints” philosophy; add a tiny set that forces overall read:
- `longitudinal_metric:sheer_slope_deg_p95` (proxy from `section_metric:sheer_z_m` vs x)
- `longitudinal_metric:beam_drop_aft` or `beam_profile_span` (from `section_metric:max_half_beam_m`)
- `longitudinal_metric:chine_height_span_m` (from `section_metric:chine_z_m`, plus a chine presence coverage metric)

Then bind Viking-like prompts naturally (no priors) because the model must justify “strong forward flare / classic sheer / cockpit transom run” with measurable targets.

### 3) (Optional) introduce a minimal “deck edge / superstructure envelope” phase
If you want the vessel to visually read like a Viking, hull-only won’t get you all the way there.
This can still be enum-free and contract-driven: generate a simple deck edge curve + a single cabin volume.

---

## Plan reference
- See the vessel-neutral v0.4 plan: `V04_PROFILE_TOPSIDE_OBSERVABLES_PLAN.md`

## Immediate takeaway
You’re not imagining it: **bottom quality improved because we now measure and enforce it**.  
But the “Viking essence” regression is largely explained by:
1) a **real station convention contradiction** (can invert fore/aft intent), and
2) **lack of silhouette-level observables** (the system is optimizing what we punish), plus
3) hull-only rendering limits vs a full Viking vessel silhouette.

