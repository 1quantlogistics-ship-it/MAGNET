### Audit: VESSEL_THINKING_PASS → GEOMETRY_PROGRAM Contract Gap (DOF/Communication)

This audit covers **two issues only** (per request):

- **(1) DOF / contract mismatch**: the current thinking-pass validation can be satisfied while the emitted geometry remains effectively constant along length (“prismatic wedge”).
- **(2) Coordinate contract contradiction**: conflicting Z-axis guidance in the GeometryProposer prompt text.

---

## 1) DOF / contract mismatch (thinking pass can “pass” while geometry stays generic)

### Symptom (UI)
You can request a 72ft “Viking-like” sportfisher with varying longitudinal laws (sheer/rocker/chine progression), but the resulting hull can still be a **near-prismatic wedge** with minimal section-to-section variation.

### Root cause (contract gap)
The server currently validates and “re-executes” the thinking checks **only against the thinking-pass payload itself** (the DOF anchor points), not against the **actual geometry produced** by `GEOMETRY_PROGRAM`.

That means the model can:
- Provide a `ScheduleDOF` with anchor points that vary (so checks like `varies` pass), and
- Provide matching `closure_proof`,
while still emitting a `GEOMETRY_PROGRAM` that does not implement those schedules in section points.

### Evidence in code (v0 validator scope)
`magnet/agents/vessel_thinking_validator.py` explicitly scopes re-execution to “computable checks from the thinking schema itself”:

```1:13:magnet/agents/vessel_thinking_validator.py
v0 scope:
- Enforce coverage/proof completeness (DOFs ↔ checks ↔ proof).
- Re-execute a subset of checks that are computable from the thinking schema itself:
  - range, monotonic, varies (for schedule/scalar)
  - coverage (for track, interpreted conservatively)
```

The `reexecute_checks()` implementation operates on `ScheduleDOF.anchor_points` / `ScalarDOF.value` and does **not** reference compiled geometry, sections, stations, or mesh:

```142:170:magnet/agents/vessel_thinking_validator.py
def reexecute_checks(thinking: VesselThinkingPass) -> Tuple[List[ThinkingPassIssue], Dict[str, Dict[str, Any]]]:
    ...
    # Unexecutable checks (uniform/correspondence) are recorded-only in v0; do not fail.
    if isinstance(c, (CoverageCheck, RangeCheck, MonotonicCheck, VariesCheck)) is False:
        computed_by_check[cn] = {"skipped": True, "reason": "unexecutable_check_type_v0"}
        continue
```

and later, for `VariesCheck`:

```230:249:magnet/agents/vessel_thinking_validator.py
if isinstance(c, VariesCheck):
    if isinstance(dof, ScheduleDOF):
        vals = [float(p.value) for p in (dof.anchor_points or [])]
        ...
        span = max(vals) - min(vals)
        ok = span > 1e-6
```

### Implication (why this is “definitely” a DOF/contract issue)
Even with a strong model, this contract allows a “split brain”:
- **Thinking pass says**: “I varied rocker / sheer.”
- **Geometry program does**: constant section sets or weakly varying sections.

So the UI can show a generic hull despite a “PASS” proof.

### What “done” looks like (non-implementation criteria)
Without implementing the fix yet, the acceptance criteria for closing this gap is:
- Any non-defaulted DOF that claims “varies/monotonic/range” must be verifiable against a **geometry-derived observable** (e.g., section-derived longitudinal summary), not just the DOF anchor points.

---

## 2) Coordinate contract contradiction (Z-axis guidance conflict)

### Symptom (prompt-level)
The GeometryProposer system prompt contains conflicting guidance about Z, which can lead to inconsistent section shapes and misunderstandings around draft/waterline/baseline.

### Evidence (two contradictory statements)

**(A) “MAGNET Standard” says** baseline is 0 and waterline is +draft:

```220:224:magnet/agents/geometry_proposer.py
### COORDINATE CONVENTION (MAGNET Standard)
- **Y-axis**: Lateral distance from centerline (Y=0 at centerline, Y>0 toward port)
- **Z-axis**: Vertical height from baseline (Z=0 at baseline/keel, Z=draft at waterline, Z=depth at deck)
- **X-axis**: NOT in section points. X is derived from `station` (0=stern/AP, 1=bow/FP)
```

and the injected “Coordinate conventions” repeat:

```418:422:magnet/agents/geometry_proposer.py
### Coordinate conventions (do not violate)
- Global X is derived from `geometry.section.station` (0..1) and LOA. Do NOT put X into section points.
- For polygon sections: `points` is strictly `[[y, z], ...]` where **z=0 is baseline** and **waterline is z=draft**.
- Sections are HALF-BREADTH (one side only, y>=0). Start at keel (y≈0), end at deck edge.
```

**(B) But the “common mistakes” section says** negative below waterline:

```299:315:magnet/agents/geometry_proposer.py
### COMMON MISTAKES TO AVOID
...
5. ❌ **Z increasing downward**: Z should be NEGATIVE below waterline, POSITIVE above
```

### Why this matters
These two rules conflict unless you specify a different reference plane (baseline vs waterline).
In practice, this creates ambiguity for the model and can lead to malformed sections (especially around draft and chine height references).

### What “done” looks like (non-implementation criteria)
Acceptance criteria for resolving the contradiction:
- One authoritative statement for Z reference (baseline or waterline), used consistently across:
  - the system prompt guidance
  - state injection guidance
  - examples
  - any offline fallback section generation

---

## Summary (two findings)
- **(1) Contract gap**: thinking-pass validation currently proves only “the model can write a coherent DOF story,” not that **geometry implements the story**.
- **(2) Prompt contradiction**: Z-axis conventions are internally inconsistent, increasing the probability of poor geometry correspondence to intended DOFs.

