## Kernel Validation + Persistence Hardening (Final Architecture)

### Purpose
Make MAGNET’s “kernel judges reality” loop **durable, design-scoped, and honest**:
- Agents propose **pure geometry constructions** (`geometry.*` resources, constraints).
- Kernel compiles/runs physics validators **after geometry exists**.
- Kernel writes derived outputs to the **canonical DesignState**.
- Every run is **observable** (history/provenance) and **persistent** (DesignStore), so UI and agents never see “phantom success”.

This guide is written to prevent the recurring failure mode:
> Validators run, but outputs are missing (or validation reads the wrong state).

---

## 1) The invariants (non-negotiable)

### 1.1 Single authority / single state
- **All phase run + validate endpoints must operate on the design-scoped `StateManager` loaded from `DesignStore.load(design_id)`**.
- No global/singleton `StateManager` may be used for phase execution.

### 1.2 Durable truth (persistence)
- If a phase/validation execution mutates state (writes physics/weights/etc), those mutations must be:
  - committed (`StateManager.begin_transaction()` → writes → `StateManager.commit()`), then
  - persisted (`DesignStore.save(design_id, expected_version=design_version_before)`).

### 1.3 Honesty (no phantom “completed”)
- API responses must not claim “completed” if:
  - input contract is unsatisfied, or
  - output contract is unsatisfied, or
  - a REQUIRED gate validator failed.

### 1.4 Optional optimistic locking (race protection)
- Endpoints should accept `expected_version` and return **409** on mismatch.
- Default behavior may omit it (UI convenience), but server must support it for correctness.

---

## 2) Root causes we are fixing

### 2.1 Validate endpoint not design-scoped
`/api/v1/designs/{design_id}/phases/{phase}/validate` currently depends on a DI-resolved `PipelineExecutor`.
That executor is not design-scoped and can validate against the wrong state, producing false “missing inputs”.

### 2.2 Phase execution not committed/persisted
`/phases/{phase}/run` executes validators and writes derived values in-memory, but does not:
- wrap execution in a transaction (required for `commit()`), nor
- persist the resulting state back to DesignStore.

Because `GET /api/v1/designs/{id}` reloads from `DesignStore`, it can appear as if outputs “disappeared”.

### 2.3 Error semantics swallowed
The validate endpoint catches exceptions and returns `"status":"error"` with a stringified `HTTPException`,
preventing the UI from reliably distinguishing:
- missing inputs (400),
- gate failures (422),
- real server errors (500).

---

## 3) Implementation changes (what to do)

### 3.1 Add request fields
Update models in `magnet/deployment/api.py`:
- `PhaseRun.expected_version: Optional[int] = None`
- `ValidationRun.expected_version: Optional[int] = None`
- `ValidationRun.persist: bool = True` (default: persist validator writes)

### 3.2 Build a design-scoped pipeline per request
Create a helper in `magnet/deployment/api.py`:
- `_build_design_scoped_pipeline(state_manager) -> (PipelineExecutor, ResultAggregator)`

Rules:
- `ValidatorTopology` can be reused (definition-only), but `PipelineExecutor` must be created per request because it binds `state_manager`.
- Ensure `ValidatorRegistry.initialize_defaults()` + `instantiate_all()` has been called before building executor.

### 3.3 Harden `/phases/{phase}/run`
In `run_phase`:
- Load design-scoped `StateManager` (already done via `get_state_manager`)
- Determine `design_version_before`
- If `expected_version` provided and mismatched, return 409
- `state_manager.begin_transaction()`
- Run phase via `Conductor` using a design-scoped `PipelineExecutor`
- `state_manager.commit()`
- Persist via `DesignStore.save(design_id, expected_version=design_version_before)`
- Return `status` derived from the actual `PhaseResult.status` (not always “completed”)

### 3.4 Harden `/phases/{phase}/validate`
In `validate_phase`:
- Build a design-scoped `PipelineExecutor` (do not use DI-resolved one)
- If `persist=True`:
  - `begin_transaction()` → execute validators → `commit()` → `DesignStore.save(...)`
- Let `HTTPException` propagate (don’t stringify it)

### 3.5 Output contract enforcement location
Keep contract checks where they belong:
- **Kernel/Conductor**: authoritative output contract check after execution
- **API validate endpoint**: contract check for the requested phase used to shape response payload and HTTP status

---

## 4) Verification plan (must pass)

### 4.1 End-to-end demo (single design)
1. Create design
2. Spiral chat: create hull via `geometry.*`
3. Verify spiral bridge seeds:
   - `hull.lwl`, `hull.beam`, `hull.draft`, `hull.cb`
   - `mission.max_speed_kts`
4. Run hull phase:
   - `hull.displacement_m3`, `hull.vcb_m`, `hull.bm_m` must be non-null in **GET design**
5. Run weight phase:
   - `weight.lightship_weight_mt`, `weight.lightship_vcg_m` must be non-null in **GET design**
6. Run stability phase:
   - `stability.gm_transverse_m` must be non-null in **GET design**

### 4.2 Consistency checks
- `POST .../validate` results must match `POST .../run` (no contradictory missing inputs when state contains inputs)
- Response status codes:
  - 400 for missing inputs
  - 409 for version conflicts (when `expected_version` supplied)
  - 422 for REQUIRED gate failure

---

## 5) Demo link expectations
For a “fresh demo” we will run the server on a new port (avoids killing existing processes):
- UI: `http://127.0.0.1:<port>/ui/v2/`

