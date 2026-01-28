# Walking Trail Plan: Honest Intermediate States

<!-- AGENT_CONTEXT
Purpose: Architecture plan for provenance tracking, persistence contracts, and honest state visibility
Authoritative: Yes
Keywords: walking_trail, provenance, persistence, contracts, ledges, confidence, turn_record, explain
Depends_On: 0-architecture/core/NORTH_STAR.md
Used_By: developers, agents
Status: current
Last_Verified: 2026-01-15
-->

**Created:** January 15, 2026
**Updated:** January 15, 2026
**Philosophy:** "The potter never finishes the wheel, but each vessel fired must still hold water."

---

## The Vision

MAGNET needs **many honest intermediate states** — not final states. Each spiral turn should be:
- **Witnessed** — physics has spoken
- **Transparent** — assumptions are known
- **Traceable** — provenance is recorded
- **Reversible** — undo has meaning

**Reality ≠ Finality.** Each ledge is a moment where state becomes accountable without being complete.

---

## The Truth

People rush when the ground does not push back.

A river accelerates on flat land. A climber moves quickly when the slope forgives mistakes. A coder rushes when nothing enforces consequence.

Planning is not a mental act. Planning is a **physical constraint**. You do not slow someone by asking them to think harder. You slow them by making each step **leave a footprint**.

Right now, too many steps leave no mark:
- A number can appear without origin
- A change can occur without witness
- A guess can survive alongside a fact

**What we are building is not process. It is friction in the right places.**

A system that allows speed without memory will always outrun understanding. A system that remembers every step naturally teaches patience.

Make the ground honest. They will slow down.

---

## Contracts and Specifications

### Contract 1: Response Shape (Ledge 3)

Every API response returning design state MUST include provenance metadata.

#### Shape

```typescript
// Option A: Per-field map (CHOSEN - backward compatible)
{
  "state": {
    "hull.displacement_m3": 523.4,
    "hull.vcb_m": 0.72,
    // ... existing flat structure unchanged
  },
  "provenance": {
    "hull.displacement_m3": {
      "source": "KERNEL",
      "confidence": 0.95,
      "explain_ref": "exp_a1b2c3",
      "validator_id": "physics/hydrostatics",
      "design_version": 7
    },
    "hull.vcb_m": {
      "source": "KERNEL",
      "confidence": 0.92,
      "explain_ref": "exp_d4e5f6",
      "validator_id": "physics/hydrostatics",
      "design_version": 7
    }
  }
}
```

#### Compatibility Strategy

| Existing clients | Behavior |
|------------------|----------|
| Read `state.*` only | Unchanged — flat values still present |
| Ignore `provenance` | Works — new field is additive |
| New clients | Read `provenance.*` for accountability |

No versioned endpoint. No feature flag. Additive only.

**Operational note:** Payload size increases. Server MAY truncate provenance for large responses via `?include_provenance=full|summary|none` query parameter, defaulting to `full`.

#### Authoritative Provenance Enum

```python
class ValueProvenance(str, Enum):
    """Source of a value in design state.

    The .value string is the canonical API representation.
    Internal code uses the enum member; API responses use .value.
    """

    USER = "USER"           # Explicitly provided by user input
    LLM = "LLM"             # Proposed by agent, not yet confirmed
    KERNEL = "KERNEL"       # Computed by physics/synthesis kernel
    FALLBACK = "FALLBACK"   # Estimated when required input missing
    INHERITED = "INHERITED" # Carried from previous design version
    DEFAULT = "DEFAULT"     # From FAMILY_PRIORS or hardcoded default
```

Mapping from existing `DimensionProvenance` (internal → API `.value`):

| Internal Enum | API String |
|---------------|------------|
| `PLACEHOLDER` | `"DEFAULT"` |
| `USER` | `"USER"` |
| `LLM_PROPOSED` | `"LLM"` |
| `SYNTHESIZED` | `"KERNEL"` |
| `KERNEL` | `"KERNEL"` |

---

#### Normalization Rules

These rules define **which values require provenance** and how edge cases are handled.

##### Scope: What requires provenance

| Category | Requires Provenance | Rationale |
|----------|---------------------|-----------|
| Leaf scalars in `state.*` | **YES** | Core design values |
| Nested objects (e.g., `weight.summary_data`) | **NO** (container only) | Provenance applies to container, not internal keys |
| Lists/arrays (e.g., `stability.gz_curve`) | **YES** (one entry for whole list) | List is a computed unit |
| Transport metadata (`design_id`, `version`) | **NO** | Not design state |
| Error payloads | **NO** | Errors are not state |

##### Granularity

Provenance is tracked at the **dot-path level**, not sub-object level.

```python
# YES - provenance for "weight.summary_data" as a whole
"weight.summary_data": {"source": "KERNEL", ...}

# NO - not this:
"weight.summary_data.lightship": {"source": "KERNEL", ...}
```

##### Missing values

| Scenario | Representation |
|----------|----------------|
| Key exists in state but not in provenance | **ERROR** — contract violation |
| Key exists in provenance but not in state | **ALLOWED** — historical reference |
| Value is `null`/`None` in state | Provenance entry with `"source": "DEFAULT"`, `"confidence": 0.0` |

##### Explicitly excluded from provenance

- `metadata.*` (design metadata, not physics)
- `_internal.*` (implementation details)
- Computed aggregates returned only in specific endpoints (e.g., `/summary`)

##### Test invariant

```python
def test_provenance_coverage(response):
    """Every state key must have provenance. No exceptions."""
    state_keys = {k for k in response["state"].keys()
                  if not k.startswith("metadata.")
                  and not k.startswith("_internal.")}
    provenance_keys = set(response["provenance"].keys())

    missing = state_keys - provenance_keys
    assert not missing, f"State keys without provenance: {missing}"
```

---

### Contract 2: Confidence Semantics

#### Definition

`confidence` is a float in `[0.0, 1.0]` representing **epistemic certainty about origin**, not correctness.

A value with `confidence=1.0` means "this value exists exactly as stated from its source."
It does NOT mean "this value is physically correct."

Physics validation is separate from provenance confidence.

#### Rules

| Provenance | Confidence | Rationale |
|------------|------------|-----------|
| `USER` | `1.0` (always) | Value exists exactly as user provided |
| `KERNEL` | `0.85 - 0.99` | Physics computation; varies by method fidelity |
| `FALLBACK` | `≤ 0.5` (hard cap) | Estimates cannot claim certainty |
| `DEFAULT` | `0.3` (fixed) | Defaults are placeholders, not knowledge |
| `LLM` | `0.4 - 0.7` | Agent proposals pending confirmation |
| `INHERITED` | Inherited value | Carries forward from source |

#### Inheritance Rule

Inherited values **retain source confidence unchanged**. No decay.

Rationale: The value hasn't changed, only moved between versions. Applying decay would punish iteration without adding information.

```python
if provenance == ValueProvenance.INHERITED:
    return original_confidence  # No decay — value is unchanged
```

#### Constraints (enforced by code)

```python
def validate_confidence(provenance: ValueProvenance, confidence: float,
                       original_confidence: Optional[float] = None) -> float:
    """Enforce confidence rules. Returns corrected value.

    This is not advisory. Code MUST call this before storing provenance.
    """
    if provenance == ValueProvenance.USER:
        return 1.0  # Always — user values exist as stated
    if provenance == ValueProvenance.FALLBACK:
        return min(confidence, 0.5)  # Hard cap — estimates cannot claim certainty
    if provenance == ValueProvenance.DEFAULT:
        return 0.3  # Fixed — defaults are placeholders
    if provenance == ValueProvenance.INHERITED:
        return original_confidence if original_confidence is not None else confidence
    return max(0.0, min(1.0, confidence))  # Clamp to valid range
```

---

### Contract 3: Turn Record (Witness/Footprints)

Every spiral turn produces an append-only record.

#### Schema

```python
@dataclass
class TurnRecord:
    """Immutable record of a single spiral turn."""

    turn_id: str                    # UUID
    design_id: str                  # Parent design
    design_version_before: int      # Version at turn start
    design_version_after: Optional[int]  # Version at turn end (None if failed)
    timestamp: datetime             # UTC
    committed: bool                 # Did this turn persist state?

    # What happened
    phase: str                      # "hull", "weight", "stability", etc.
    trigger: str                    # "user_request", "auto_progression", "agent_proposal"

    # Inputs snapshot (selective — see rules below)
    inputs_read: Dict[str, str]     # path → explain_ref (not full values)

    # Outputs delta
    outputs_written: Dict[str, str] # path → explain_ref (not full values)

    # Validator results
    validators_run: List[str]       # Validator IDs executed
    findings: List[ValidationFinding]
    gate_results: Dict[str, str]    # validator_id → "PASSED"/"FAILED"/"WARNING"

    # Assumptions made
    assumptions: List[str]          # Human-readable list: "Assumed Cb=0.55 (family prior)"

    # Error (if failed)
    error: Optional[str]            # Error message if turn failed
```

#### Input capture rules

To prevent unbounded growth:

| Rule | Specification |
|------|---------------|
| **What to capture** | Only paths declared in validator `depends_on_parameters` |
| **How to capture** | Store `explain_ref`, not raw value |
| **Size limit** | Max 100 input paths per turn |
| **Redaction** | Paths matching `*_secret`, `*_token`, `*_key` are redacted |

#### Storage

Turn records are **durable** — persisted to filesystem, not in-memory.

**Location:** `{design_store_path}/{design_id}/turns.jsonl`

Format: JSON Lines (one JSON object per line, append-only)

```python
# TurnRecords are DURABLE — stored in DesignStore backend
class DesignStore:
    def append_turn_record(self, record: TurnRecord) -> None:
        """Append-only. Never mutate existing records."""
        turns_path = self._get_turns_path(record.design_id)
        with open(turns_path, 'a') as f:
            f.write(json.dumps(dataclasses.asdict(record)) + '\n')

    def get_turn_history(self, design_id: str) -> List[TurnRecord]:
        """Return all turns for a design, ordered by timestamp."""
        turns_path = self._get_turns_path(design_id)
        if not turns_path.exists():
            return []
        with open(turns_path) as f:
            return [TurnRecord(**json.loads(line)) for line in f]

    def _get_turns_path(self, design_id: str) -> Path:
        return self._base_path / design_id / "turns.jsonl"
```

#### Retention

- Turn records are **never deleted** during design lifetime
- Linked to `design_version` for point-in-time reconstruction
- Exportable for audit trail
- **Archival:** Designs inactive > 90 days MAY have turn records archived to cold storage

#### Privacy note

Turn records may contain:
- User-provided values (via explain_ref resolution)
- Agent prompts/responses (via assumptions)
- Internal heuristics

Access control: Turn history endpoint requires same auth as design access. No public exposure.

---

### Contract 4: Concurrency and Conflict Policy (Ledge 1)

#### Strategy: Optimistic Locking by `design_version`

#### Version authority

**DesignStore owns the clock.** StateManager tracks in-memory version; DesignStore is authoritative for persisted version.

```
StateManager.commit() → increments in-memory version
DesignStore.save()    → persists and returns authoritative version
```

On save, DesignStore checks that its current version matches expected. If mismatch, save fails.

```python
def save(self, design_id: str, state_manager: StateManager,
         expected_version: int) -> int:
    """
    Persist state. Fails if version mismatch.

    Args:
        expected_version: The version number client believes is current

    Returns: new_version on success (always expected_version + 1)
    Raises: VersionConflictError if expected_version != current persisted version
    """
    current = self._get_persisted_version(design_id)
    if current != expected_version:
        raise VersionConflictError(
            design_id=design_id,
            expected=expected_version,
            actual=current,
            message="Design was modified by another request"
        )
    new_version = expected_version + 1
    self._persist(design_id, state_manager, new_version)
    return new_version
```

#### Conflict Response

```json
{
  "error": "version_conflict",
  "expected_version": 5,
  "actual_version": 6,
  "message": "Design was modified by another request. Reload and retry.",
  "design_id": "abc123"
}
```

Client must:
1. Reload current state
2. Reapply their changes
3. Retry with new `expected_version`

#### Rule

**No silent merge.** Conflicts are explicit errors. The system does not guess how to combine concurrent changes.

#### Isolation guarantee

Readers only see the last committed durable version. A reader during an in-progress phase sees the pre-phase state, never working state.

---

### Contract 5: Atomicity Semantics (Ledge 1)

#### Atomic Unit: The Phase

A phase is the atomic unit of persistence. Either:
- **All outputs persist** (phase succeeded, committed)
- **No outputs persist** (phase failed or crashed)

#### What Persists on Failure

| Artifact | Persists? | Rationale |
|----------|-----------|-----------|
| State changes | **NO** | Partial state is worse than no state |
| Turn record | **YES** | Failures are witnessed (with `committed=False`) |
| Findings | **YES** | Diagnostic value |
| Logs | **YES** | Debugging |

#### Crash Consistency

```python
def run_phase_atomic(self, phase: str, state_manager: StateManager) -> PhaseResult:
    """
    Phase execution with crash consistency.

    Guarantee: If this function does not return normally,
    no state changes from this phase are visible to subsequent requests.
    """
    # Capture version before we start
    version_before = self._design_store.get_version(design_id)

    # 1. Begin transaction (in-memory working state)
    txn_id = state_manager.begin_transaction()

    try:
        # 2. Execute phase (writes to working state only)
        result = self._execute_phase(phase, state_manager)

        if result.state == ValidatorState.FAILED:
            # 3a. Rollback on failure
            state_manager.rollback(txn_id)
            self._record_turn(result, committed=False, version_before=version_before)
            return result

        # 3b. Commit in-memory
        state_manager.commit(txn_id)

        # 4. Persist to durable storage (atomic write)
        # DesignStore is authoritative — use version_before as expected
        new_version = self._design_store.save(
            design_id,
            state_manager,
            expected_version=version_before
        )

        # 5. Record the turn (with committed=True)
        self._record_turn(result, committed=True,
                         version_before=version_before,
                         version_after=new_version)

        return result

    except Exception as e:
        # Crash/error: rollback, record failure
        state_manager.rollback(txn_id)
        self._record_turn(None, committed=False,
                         version_before=version_before,
                         error=str(e))
        raise
```

---

### Contract 6: Ledge 3 / Ledge 4 Separation

Ledge 3 **returns references**. Ledge 4 **resolves them**.

#### Ledge 3 Response (provenance)

```json
{
  "provenance": {
    "hull.displacement_m3": {
      "source": "KERNEL",
      "confidence": 0.95,
      "explain_ref": "exp_a1b2c3"
    }
  }
}
```

The `explain_ref` is an opaque ID. Ledge 3 does not include derivation details.

#### `explain_ref` Generation

Deterministic, content-addressable ID for caching:

```python
def generate_explain_ref(design_id: str, design_version: int, path: str) -> str:
    """Generate deterministic explain_ref.

    Same inputs always produce same ref — enables caching.
    """
    content = f"{design_id}:{design_version}:{path}"
    hash_bytes = hashlib.sha256(content.encode()).digest()[:6]
    return f"exp_{base64.urlsafe_b64encode(hash_bytes).decode().rstrip('=')}"
```

**Properties:**
- Deterministic: Same (design_id, version, path) → same ref
- Unique: Different inputs → different ref (collision probability negligible)
- Cacheable: Immutable — once generated, never changes
- Compact: 12 characters (`exp_` + 8 base64 chars)

#### Ledge 4 Endpoint (explain)

```
GET /api/v1/designs/{design_id}/explain/{explain_ref}
```

Response:

```json
{
  "explain_ref": "exp_a1b2c3",
  "parameter": "hull.displacement_m3",
  "derivation": {
    "method": "Cb-based displacement calculation",
    "formula": "Δ = Cb × L × B × T × ρ",
    "inputs": {
      "hull.cb": {"value": 0.45, "source": "USER"},
      "hull.lwl": {"value": 12.0, "source": "USER"},
      "hull.beam": {"value": 3.5, "source": "USER"},
      "hull.draft": {"value": 1.2, "source": "USER"},
      "constants.seawater_density": {"value": 1.025, "source": "DEFAULT"}
    },
    "computation_steps": [
      "Volume = 0.45 × 12.0 × 3.5 × 1.2 = 22.68 m³",
      "Displacement = 22.68 × 1.025 = 23.25 tonnes"
    ]
  },
  "validator_id": "physics/hydrostatics",
  "design_version": 7,
  "timestamp": "2026-01-15T14:32:00Z"
}
```

#### Why Separate

| Concern | Ledge 3 | Ledge 4 |
|---------|---------|---------|
| Every response | Yes | No (on demand) |
| Payload size | Small (refs only) | Large (full derivation) |
| Caching | Per-version | Per-ref (immutable) |
| Client burden | Must handle provenance | Optional deep-dive |

Ledge 3 is the hinge. Ledge 4 is the library.

---

## Implementation Targets

| Contract | Primary File(s) | Entry Point |
|----------|-----------------|-------------|
| 1. Response Shape | `magnet/deployment/api.py`, `spiral_endpoints.py` | Response builders |
| 2. Confidence | `magnet/state/provenance.py` | `validate_confidence()` |
| 3. Turn Record | `magnet/deployment/design_store.py` | `append_turn_record()` |
| 4. Concurrency | `magnet/deployment/design_store.py` | `save()` with version check |
| 5. Atomicity | `magnet/deployment/spiral_endpoints.py` | Phase execution wrapper |
| 6. Explain | `magnet/deployment/api.py` | New `/explain` endpoint |
| 7. Error/Grade Response | `magnet/deployment/api.py` | Response handlers |
| 8. Suggested Fix | `magnet/validators/fix_generator.py` | `generate_fixes()` |

---

### Contract 7: Error Response Shape

All error responses follow a consistent structure.

#### Schema

```json
{
  "error": "grade_warning",
  "phase": "weight",
  "grade": "weight/stability_check",
  "findings": [
    {
      "finding_id": "f1a2b3c4",
      "severity": "ERROR",
      "message": "SEVERE GRADE: Negative GM (-1.5m). Vessel is capsized/unstable.",
      "parameter_path": "weight.estimated_gm_m",
      "actual_value": -1.5,
      "suggestion": "Lower KG by moving weight down or increase BM by widening beam"
    }
  ],
  "suggested_fixes": [
    {
      "fix_id": "fix_beam_increase",
      "finding_id": "f1a2b3c4",
      "target_path": "hull.beam",
      "current_value": 4.0,
      "suggested_value": 4.5,
      "rationale": "Increasing beam raises BM, improving GM",
      "confidence": 0.85,
      "side_effects": ["resistance +8%"]
    }
  ],
  "turn_id": "turn_xyz123",
  "design_version": 7,
  "human_decision_required": true
}
```

#### Error Types

| `error` | HTTP Status | `human_decision_required` | Meaning |
|---------|-------------|---------------------------|---------|
| `gate_failed` | 422 | false | Hydrostatics gate failed (geometry invalid) |
| `grade_warning` | 200 | true | Grade threshold crossed (human decides) |
| `version_conflict` | 409 | — | Concurrent modification (reload and retry) |
| `missing_inputs` | 400 | — | Required parameters not set |
| `not_found` | 404 | — | Design or resource not found |
| `internal_error` | 500 | — | Unexpected server error |

#### Gate vs Grade (North Star Model)

- **Gate failed (`gate_failed`):** Geometry is physically invalid. Cannot proceed. (Only hydrostatics)
- **Grade warning (`grade_warning`):** Threshold crossed but human can decide. Design proceeds if human accepts/overrides.

The system never blocks on grades. It warns, suggests fixes, and the human decides.

---

### Contract 8: Suggested Fix Object (North Star Core Loop)

The North Star defines the core loop: **Agents propose → Kernel judges → System suggests fixes → Human decides.**

The "suggested fix" is a first-class output, not an afterthought.

#### Schema

```typescript
interface SuggestedFix {
  // Identity
  fix_id: string;                    // Unique ID for this suggestion
  finding_id: string;                // Links to the ValidationFinding that triggered it

  // What to change
  target_path: string;               // Parameter to modify (e.g., "hull.beam")
  current_value: number | string;    // Current value
  suggested_value: number | string;  // Recommended new value
  change_delta?: number | string;    // Optional: "+0.3m" or "×1.1"

  // Why this fix
  rationale: string;                 // Human-readable explanation
  causal_chain: CausalStep[];        // How we traced from violation to fix

  // Confidence
  confidence: number;                // 0.0-1.0: How confident are we this fix works?
  side_effects: string[];            // Known tradeoffs: ["resistance +8%", "cost +$5k"]

  // Human decision options
  actions: FixAction[];              // Available user responses
}

interface CausalStep {
  // Traces the derivation chain from violation to suggested fix
  step_number: number;
  from_parameter: string;            // e.g., "stability.gm_m"
  to_parameter: string;              // e.g., "weight.lightship_vcg_m"
  relationship: string;              // e.g., "GM = KB + BM - KG"
  direction: "upstream" | "downstream";
}

interface FixAction {
  action: "accept" | "modify" | "override" | "ignore";
  label: string;                     // Display text
  requires_confirmation: boolean;    // True for override/ignore
}
```

#### Example Response

```json
{
  "findings": [
    {
      "finding_id": "f1a2b3c4",
      "severity": "ERROR",
      "message": "SEVERE GRADE: Negative GM (-1.5m). Vessel is capsized/unstable.",
      "parameter_path": "weight.estimated_gm_m",
      "actual_value": -1.5
    }
  ],
  "suggested_fixes": [
    {
      "fix_id": "fix_beam_increase",
      "finding_id": "f1a2b3c4",
      "target_path": "hull.beam",
      "current_value": 4.0,
      "suggested_value": 4.5,
      "change_delta": "+0.5m",
      "rationale": "Increasing beam widens the waterplane, raising BM and improving GM.",
      "causal_chain": [
        {
          "step_number": 1,
          "from_parameter": "weight.estimated_gm_m",
          "to_parameter": "hull.bm_m",
          "relationship": "GM = KB + BM - KG; low GM means BM too low",
          "direction": "upstream"
        },
        {
          "step_number": 2,
          "from_parameter": "hull.bm_m",
          "to_parameter": "hull.beam",
          "relationship": "BM ∝ B² / (12 × draft × Cb); increasing B increases BM",
          "direction": "upstream"
        }
      ],
      "confidence": 0.85,
      "side_effects": ["resistance +8%", "lightship +2%"],
      "actions": [
        {"action": "accept", "label": "Accept Fix", "requires_confirmation": false},
        {"action": "modify", "label": "Modify Value", "requires_confirmation": false},
        {"action": "override", "label": "Override Warning", "requires_confirmation": true},
        {"action": "ignore", "label": "Ignore", "requires_confirmation": true}
      ]
    }
  ]
}
```

#### Why This Matters

Without structured suggested fixes:
- Users see "GM is bad" but don't know what to do
- The system has knowledge it doesn't share
- The human-in-the-loop becomes human-in-the-dark

With structured suggested fixes:
- The system shows the causal chain (why this fix?)
- The system quantifies side effects (what's the tradeoff?)
- The human has clear options (what can I do?)

This is the North Star's promise: **"The human didn't debug. The system shows the causal chain, suggests the upstream fix, and the user decides whether to apply it."**

#### Implementation Target

| Component | File | Entry Point |
|-----------|------|-------------|
| Fix generation | `magnet/validators/fix_generator.py` | `generate_fixes()` |
| Causal tracing | `magnet/validators/causal_tracer.py` | `trace_upstream()` |
| Response integration | `magnet/deployment/api.py` | Include in validation responses |

---

## Test Plan

### Ledge 1: Persistence Tests

```python
class TestPersistenceContracts:

    def test_crash_mid_phase_no_partial_state(self):
        """Kill process during phase execution. Verify no partial state persisted."""

    def test_concurrent_writes_conflict_error(self):
        """Two simultaneous writes to same design. Second must get VersionConflictError."""

    def test_failed_phase_no_state_change(self):
        """Phase returns FAILED. Verify state unchanged from before phase."""

    def test_failed_phase_turn_record_exists(self):
        """Phase fails. Verify TurnRecord still created with committed=False."""

    def test_readers_see_committed_only(self):
        """During phase execution, concurrent reader sees pre-phase state."""
```

### Ledge 3: Provenance Tests

```python
class TestProvenanceContracts:

    def test_no_value_without_provenance(self):
        """Every key in state must have corresponding entry in provenance."""
        response = client.get(f"/api/v1/designs/{design_id}")
        state_keys = {k for k in response.json()["state"].keys()
                      if not k.startswith("metadata.")
                      and not k.startswith("_internal.")}
        provenance_keys = set(response.json()["provenance"].keys())
        assert state_keys == provenance_keys, "All values must have provenance"

    def test_fallback_confidence_capped(self):
        """Values with source=FALLBACK must have confidence ≤ 0.5."""
        for path, prov in response.json()["provenance"].items():
            if prov["source"] == "FALLBACK":
                assert prov["confidence"] <= 0.5, f"{path} fallback exceeds confidence cap"

    def test_user_values_confidence_one(self):
        """Values with source=USER must have confidence = 1.0."""

    def test_provenance_includes_explain_ref(self):
        """Every provenance entry must include explain_ref for Ledge 4."""

    def test_backward_compatible_state_shape(self):
        """Existing clients reading only state.* still work."""

    def test_null_value_has_provenance(self):
        """Null values still have provenance entry with confidence=0.0."""
```

### Ledge 4: Explain Tests

```python
class TestExplainContracts:

    def test_explain_resolves_ref(self):
        """explain_ref from Ledge 3 response resolves via explain endpoint."""

    def test_explain_includes_input_provenance(self):
        """Derivation shows provenance of each input used."""

    def test_explain_ref_immutable(self):
        """Same explain_ref always returns same derivation (cacheable)."""

    def test_explain_404_for_unknown_ref(self):
        """Unknown explain_ref returns 404, not error."""
```

### Turn Record Tests

```python
class TestTurnRecordContracts:

    def test_turn_record_created_on_success(self):
        """Successful phase creates TurnRecord with committed=True."""

    def test_turn_record_created_on_failure(self):
        """Failed phase creates TurnRecord with committed=False."""

    def test_turn_records_append_only(self):
        """Turn records cannot be modified after creation."""

    def test_undo_preserves_provenance(self):
        """After undo, provenance reflects reverted state correctly."""

    def test_findings_surfaced_in_response(self):
        """ValidationFindings appear in API response, not just logs."""

    def test_turn_record_redacts_secrets(self):
        """Paths matching *_secret, *_token, *_key are redacted."""
```

---

## Distance Assessment

### Ledge 1: Persistence (Write Barrier)

**Status:** ⚠️ Code paths exist, contracts not enforced

| Claim | Evidence | Gap |
|-------|----------|-----|
| `commit()` writes to DesignStore | `spiral_endpoints.py:871-914` wiring | ✓ Implemented |
| Values survive API restart | `test_phase_persistence.py` passes | Need crash-recovery test |
| Transaction rollback on failure | `begin_transaction()` exists | Atomicity not proven |
| Version conflict detection | — | **NOT IMPLEMENTED** |

**Definition of Done:**
- [ ] Test: Kill process mid-phase, verify partial state not persisted
- [ ] Test: Concurrent writes return `VersionConflictError`
- [ ] Implement: `expected_version` parameter on save
- [ ] Document: Transaction boundaries explicitly marked in code

---

### Ledge 2: Gate/Grade Model (North Star Aligned)

**Status:** ✅ Implemented and tested

**North Star Law 6:** "Hydrostatics is the only hard gate. Everything else is a grade with threshold warnings."

| Claim | Evidence | Gap |
|-------|----------|-----|
| KG fallback removed | `stability/validators.py` v1.3 | ✓ Verified |
| GM < 0 returns WARNING (grade) | `weight/validators.py` v1.3 | ✓ Aligned with North Star |
| Tests cover grade behavior | `test_kg_missing_fails_v13`, `test_negative_gm_grade_v13` | ✓ Passing |

**Key Distinction:**
- **GATE (hydrostatics only):** Invalid geometry → FAILED → Cannot proceed
- **GRADE (everything else):** Threshold crossed → WARNING + suggested fix → Human decides

**Definition of Done:**
- [x] Remove `kg_m = 0.55 * depth` silent estimation
- [x] Negative GM returns `ValidatorState.WARNING` with suggested fix (v1.3 North Star alignment)
- [x] Tests verify grade behavior (human decides, system doesn't block)
- [x] Audit other validators for remaining "still proceed" patterns

**v1.3 Change (January 15, 2026):**
The v1.2 change that made `GM < 0 → FAILED` violated North Star Law 6. Reverted to `WARNING` with structured suggested fix. The system warns and suggests; the human decides.

**Audit Results (January 15, 2026):**
```bash
grep -ri "still proceed\|continue anyway\|proceed anyway" magnet/
```

| File | Line | Pattern | Status |
|------|------|---------|--------|
| `weight/validators.py` | 10 | Docstring reference | ✓ Historical note, not code |
| `spiral_endpoints.py` | 940 | "Continue anyway?" | ✓ User prompt for severe grade — **CORRECT** |

The `spiral_endpoints.py:940` pattern is **correct** — it's the human decision point for severe grades. The system asks the human to confirm, which is exactly what the North Star requires.

---

### Ledge 3: Fallback Visibility (THE HINGE)

**Status:** ❌ Internal only, not user-visible

| Claim | Evidence | Gap |
|-------|----------|-----|
| `DimensionProvenance` enum exists | `state/provenance.py` | Internal tracking only |
| Fallbacks marked in state | `source=` parameter on `set()` | Not surfaced to API response |
| User can see what was estimated | — | **NOT IMPLEMENTED** |
| `explain_ref` returned | — | **NOT IMPLEMENTED** |

**Why This Is The Hinge:**
Before Ledge 3, honesty is internal (we know). After Ledge 3, honesty is user-visible (they know).

**Definition of Done:**
- [ ] API responses include `provenance` map (Contract 1)
- [ ] Normalization rules enforced (Contract 1 addendum)
- [ ] Confidence rules enforced (Contract 2)
- [ ] `explain_ref` included for each value
- [ ] Test: No value returned without provenance
- [ ] Test: Fallback confidence ≤ 0.5

---

### Ledge 4: Explain on Demand

**Status:** ❌ Not implemented

| Claim | Evidence | Gap |
|-------|----------|-----|
| `make_uncertainty()` in Phase 4 | Code exists | Not wired to explain system |
| Validation findings captured | `ValidationFinding` dataclass | Findings not in API response |
| `explain_ref` resolvable | — | **NOT IMPLEMENTED** |

**Definition of Done:**
- [ ] `/explain/{design_id}/{explain_ref}` endpoint implemented
- [ ] Derivation includes input provenance
- [ ] Findings surfaced in API response (not just logs)
- [ ] Test: explain_ref from Ledge 3 resolves correctly

---

### Ledge 5: Agent Reformation

**Status:** ❌ Not started

| Claim | Evidence | Gap |
|-------|----------|-----|
| Agents preserve provenance | — | Not implemented |
| Multi-turn context maintained | — | Not implemented |
| Agent actions are reversible | — | Not implemented |

**Definition of Done:**
- [ ] Agent writes include provenance markers
- [ ] Agent session state persists across turns
- [ ] Undo operation reverses agent proposals
- [ ] Turn records capture agent proposals

---

## The Trail Order

```
[Ledge 1: Persistence]     ⚠️ Add version conflict detection
         ↓
[Ledge 2: Gate/Grade]      ✅ Complete (North Star aligned)
         ↓
[Ledge 3: Fallback Viz]    ❌ ← THE HINGE (you are here)
         ↓                      Returns explain_refs
[Ledge 4: Explain]         ❌ Resolves explain_refs
         ↓
[Ledge 5: Agents]          ❌ Future
```

---

## Honest Summary

| Ledge | Status | Blocker | Contract |
|-------|--------|---------|----------|
| 1. Persistence | ⚠️ | Version conflict | Contract 4, 5 |
| 2. Gate/Grade | ✅ | None | Contract 8 |
| 3. Fallback Viz | ❌ | API surface | Contract 1, 2 |
| 4. Explain | ❌ | Depends on Ledge 3 refs | Contract 6 |
| 5. Agents | ❌ | Depends on Ledge 4 | — |

**Distance to "honest intermediate states":** Ledge 3 is the gate. Internal tracking exists but user visibility does not. The system knows where values came from; the user doesn't.

---

## Privacy Note

Not all truth is for all eyes.

Explain payloads and turn records may expose:
- Internal heuristics and formulas
- Agent prompts and reasoning
- User-provided sensitive values

Access controls must match design access. No public exposure of explain or turn history endpoints.

---

## Priority Order

| Priority | Item | Effort | Status |
|----------|------|--------|--------|
| P0 | PATCH persistence | 30 min | ✅ COMPLETE |
| P0 | Silence #1 Cut (KG, GM gates) | 2 hours | ✅ COMPLETE |
| P1 | `expected_version` on save | 2-4 hours | ❌ Not started |
| P2 | Ledge 3 provenance in API response | 4-8 hours | ❌ Not started |
| P3 | `explain_ref` generation | 1 hour | ❌ Design complete |
| P4 | Turn record storage | 1 hour | ❌ Design complete |
| P5 | Error response shape | 2 hours | ❌ Design complete |

---

## Related Documents

- [ZENFLOW_ALIGNMENT.md](./ZENFLOW_ALIGNMENT.md) — Gravity map and tributary audit
- [AGENT IMPLEMENTATIONRIVER.md](./AGENT%20IMPLEMENTATIONRIVER.md) — Task tracking for river fixes
