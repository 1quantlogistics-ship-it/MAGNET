### Viking “Hull Form Only” Audit (why it doesn’t read like a Viking yet)

Scope: **hull shell geometry only** (sections, chine, deadrise progression, transom run, spray rails/strakes if modeled as geometry primitives).  
Out of scope: deckhouse, windshield, foredeck camber, towers, sheer styling above deck.

---

### What “reads Viking” from hull form alone (recognizable cues)

- **Fine bow entry + convex forefoot**: very narrow half-beam near station \(< 0.12\) at/near waterline; clean entry with a “knife” feel.
- **Strong bow flare (still hull form)**: forebody sections where **above-water** points push outward with increasing z (flare) even without a deckhouse; this affects spray pattern and silhouette.
- **Hard chine continuity**: a persistent hard edge track (same anchor across stations) defining planing surface boundary.
- **Deadrise progression**: higher deadrise forward, moderating toward transom (e.g., ~25–30° fore → ~14–18° aft) rather than constant V.
- **Aft running surface**: flatter run aft with a defined keel/center pad or mild delta, not a uniformly curved bottom.
- **Transom definition**: crisp transom section + runout; not a “rounded-off” stern.
- **Strakes / spray rails (optional but high signal)**: discontinuities that create spray control; if unmodeled, “Viking-like” will always look generic.

These are **geometric constraints**, not “brand” labels—if we hit these cues, the hull can read “Viking-ish” even without topsides.

---

### What MAGNET is likely doing today (why your output looks “improved but generic”)

From the spiral path:
- The NL request (“create a 72ft viking sport fishing yacht”) is converted by `magnet/agents/geometry_proposer.py` into a **minimal complete hull program** (body + sections + loft).
- On blank designs, the proposer is biased toward **safe generic planing defaults** (deep‑V with moderate beam/draft) unless the prompt explicitly calls out the cues above (chine track, deadrise schedule, entry fineness, flare).

From the compilation path:
- The compiler/harmonizer enforces topology rules (consistent point counts, optional upsampling/harmonization). Even when deterministic, these steps can **smooth away distinctive shapes** if the proposal did not encode strong anchors.

Net: You get a coherent planing hull, but without enough “signature constraints,” it reads as a **generic deep‑V**.

---

### Current blockers (hull-form specific)

- **No explicit “style-to-geometry” contract**: “Viking” is not a geometric spec; without explicit cues, the proposer chooses generic defaults.
- **No enforceable feature anchors yet**: we do not currently require or grade:
  - chine track continuity
  - deadrise progression targets
  - bow entry ratio targets
- **No variation harness**: there’s no systematic suite proving the generator can produce *distinct* planing hull families on demand (so we still rely on eyeballing).
- **Transform visibility gap**: we still don’t emit structured receipts for:
  - section resample/upsample/harmonization (where character can get normalized)
  - any station insertion policy (where fore/aft curvature can be diluted)

---

### Next steps (order matters) to get “wow, that’s a Viking” from hull shell alone

#### 1) Add a “Viking hull cues” stress case (no UI work needed)
Create a canonical program/prompt that explicitly specifies:
- bow entry fineness ratio (bow half-beam / midship half-beam)
- a deadrise schedule (fore/mid/aft)
- a hard chine track
- aft run flattening near transom
- (optional) spray rail discontinuity

Acceptance criteria (objective, not eyeballing):
- bow entry ratio < X (e.g., < 0.15)
- chine track exists and is continuous across ≥ Y% stations
- deadrise decreases monotonically from fore to aft within tolerance

#### 2) Add **transform receipts** where sameness can be introduced
Record (phase-time) in TurnContract receipts:
- number of stations/sections before vs after compile
- point count per section before vs after harmonization
- any hard-edge snapping performed

This is the minimal “sameness injector detector.”

#### 3) Add **grade-only** geometry validators for Viking cues (do not gate integrity yet)
Implement deterministic section-derived grading for:
- **chine continuity** (track existence + station coverage)
- **deadrise progression** (fore→aft trend, not a single target)
- **bow entry fineness ratio**

Surface these metrics in receipts; do not change `SimulationIntegrity` based on them (v0).

---

### Practical “do this now” prompt language (hull-form only)

If you want the generator to produce Viking-like cues today, your command needs to include hull-form specs, not brand:
- “72ft planing deep‑V with **very fine bow entry**, **strong bow flare**, **hard chine**, **deadrise 26° forward → 16° aft**, and a **clean flat run into a crisp transom**.”

That forces the proposer to encode the cues into sections rather than defaulting.

---

### Debugging: how to see what the system actually did (today)

- In UI: type **“what changed”** to retrieve the last applied `program_text` from spiral checkpoints.
- Inspect whether the program includes:
  - an explicit hard edge in `geometry.section.edge_types`
  - a station distribution denser at bow/stern
  - enough points per section (12–20) to express flare/chine without being washed out

