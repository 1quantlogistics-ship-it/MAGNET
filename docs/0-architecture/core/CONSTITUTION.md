# MAGNET Constitution

<!-- AGENT_CONTEXT
Purpose: Inviolable laws and constraints for the MAGNET system
Authoritative: Yes
Depends_On: NORTH_STAR.md
Used_By: All modules, all agents
Last_Verified: 2026-01-14
-->

## Article I: Separation of Powers

### Kernel Authority
The kernel is the sole authority for:
- Physics validation (hydrostatics, stability, resistance)
- Geometry compilation (primitives → mesh)
- State transitions (phase advancement)

### Agent Authority
Agents are the sole authority for:
- Intent interpretation (natural language → actions)
- Explanation generation (state → human-readable text)
- Clarification requests (ambiguous input → structured questions)

### Human Authority
Humans are the sole authority for:
- Design intent (what the vessel should do)
- Trade-off decisions (when physics conflicts with mission)
- Final acceptance (design is complete)

## Article II: Information Firewall

1. **Kernel cannot import from agents.** The kernel must be pure computation.
2. **Agents cannot mutate state directly.** All mutations go through kernel protocol.
3. **Intermediate solver state is not exposed.** Agents see results, not process.

## Article III: Gate vs Grade

1. **Hydrostatics is a Gate.** Failure to float = rejection.
2. **Everything else is a Grade.** Advisory warnings, not blocking errors.
3. **Grades inform, Gates decide.** A design can have many warnings and still be valid.

## Article IV: Enumeration Prohibition

1. **No vessel type → parameter mappings.** Defaults come from geometry, not categories.
2. **No hull family conditionals.** Physics is computed from shape, not name.
3. **No style presets.** Every design is novel composition.

## Article V: Coordinate Sovereignty

1. **MAGNET Standard is law.** See `GEOMETRY_CONVENTIONS.md`.
2. **Y+ is Port.** Right-handed coordinate system.
3. **Z=0 is Baseline.** Static datum, not waterline.

## Article VI: Tolerance Uniformity

1. **No folklore tolerances.** All `1e-X` literals use named constants.
2. **Constants are centralized.** See `magnet/core/constants.py`.
3. **Idempotency is required.** Same geometry → same results.

## Article VII: Amendment Process

These laws may only be changed when:
1. A novel hull form cannot be represented with current primitives.
2. Physics validation is proven incorrect.
3. Human usability is fundamentally blocked.

Changes require:
1. Written justification
2. Test demonstrating the failure
3. Minimal modification to restore capability

---

> The Constitution is not a suggestion. It is the difference between a system and a collection of scripts.
