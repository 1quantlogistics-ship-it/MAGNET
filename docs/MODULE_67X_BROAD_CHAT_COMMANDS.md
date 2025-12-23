## Module 67.x — Broad Chat Commands (Kernel-First, LLM-First)

### 1) Summary
Natural language chat compiles into `ActionPlan` via an **LLM-first translator**; deterministic parsing is used only as a fallback when the LLM is unavailable or fails to translate. All mutations still flow through `ActionPlanValidator → ActionExecutor → StateManager.commit`, with provenance tagging, atomic transactions, baselines for unset values, and path-aware bucket deltas. Undo/restore remains available after every commit.

### 2) Control Flow (canonical)
User text  
→ LLM translator (primary) (`magnet/deployment/api.py::_compile_intent_with_llm_fallback`)  
  - system_prompt injects allowed paths + kernel units from `REFINABLE_SCHEMA`  
  - `options=LLMOptions(temperature=0)`  
→ Build ActionPlan (`magnet/kernel/intent_protocol.py`)  
→ Validate (no mutation) (`magnet/kernel/action_validator.py`)  
  ├─ approved → apply_payload (gated by `MAGNET_CHAT_GUESS_APPLY`)  
  └─ blocked/empty → Deterministic parser fallback (`magnet/deployment/intent_parser.py`)  
        → Build ActionPlan  
        → Validate (no mutation)  
→ Apply via `/actions` (`magnet/deployment/api.py`)  
→ Transaction → Commit (`StateManager.commit`)  
→ Undo / restore available (`/undo`, `/versions/{v}/restore`)

### 3) Key Files (ownership)
- `magnet/kernel/action_validator.py`: `_BASELINE_VALUES`, `_DELTA_POLICY`, bucket-to-numeric delta conversion, unit normalize, clamp, type coercion, lock checks, stale plan detection.
- `magnet/kernel/action_executor.py`: provenance derivation from plan_id prefix, structured source string into `StateManager.set`, atomic transactions with rollback-on-any-error, emits events with provenance.
- `magnet/deployment/api.py`: `_compile_intent_with_llm_fallback()` (**LLM-first translator**, deterministic fallback, allowlist filtering, system_prompt path+unit injection from `REFINABLE_SCHEMA`, `LLMOptions(temperature=0)`, `llm_meta` + `llm_output_sha256`, apply_payload gating), preview endpoints wiring.
- `magnet/ui_v2/js/backend-adapter.js`: session toggle `auto-apply guesses on|off|status`, provenance-aware preview handling for guesses vs deterministic, undo/rest hooks.

### 4) Bucket Deltas (path-aware)
- Policy table `_DELTA_POLICY` in `action_validator.py`:
  - Hull (absolute meters): `hull.loa` (+1.0/+2.0/+5.0), `hull.beam` (+0.2/+0.5/+1.0), `hull.draft` (+0.10/+0.25/+0.50), `hull.depth` (+0.20/+0.50/+1.00)
  - Mission: `mission.max_speed_kts` (+1/+3/+7), `mission.cruise_speed_kts` (+1/+2/+5), `mission.range_nm` (+50/+200/+500), `mission.crew_berthed` (+1/+3/+8), `mission.passengers` (+10/+50/+200)
  - Propulsion: `propulsion.total_installed_power_kw` bounded percent (a_bit=5%, normal=15%, way=35%, min_abs=100 kW)
- Bucket token is `unit="bucket:<bucket>"`; buckets outside policy or paths outside table are rejected.

### 5) Baselines on Null
- `_BASELINE_VALUES` in `action_validator.py` for hull dims, mission speeds/range/crew/passengers, propulsion power.
- If delta current is unset and path in baselines: substitute baseline, warn `baseline_used:{path}={value}`, then apply delta.
- Paths without baselines still reject deltas on unset.

### 6) LLM-First Translation Rules
- **LLM-first**: translator is attempted for every preview request.
- Deterministic parser is used only when:
  - `llm_client` is `None` / provider unavailable, **or**
  - the LLM call throws, **or**
  - the LLM returns no usable actions after filtering.
- LLM call uses `LLMClient.complete_json(prompt, schema, system_prompt=..., options=LLMOptions(temperature=0))`.
- Allowlist: only paths in `LLM_ALLOWED_PATHS` (mirrors baseline/delta policy); non-refinable or non-allowlisted proposals are dropped pre-validation.
- LLM path builds `llm_*` plan_id/intent_id, validates via the same validator, returns `llm_meta` + `llm_output_sha256`.
- `apply_payload` for LLM results is gated by `MAGNET_CHAT_GUESS_APPLY` (default **true** in code; can be disabled by setting `MAGNET_CHAT_GUESS_APPLY=false`).
- `LLM_PROMPT_VERSION` is included in `llm_meta` for audit, but is not routed through the provider layer.

### 7) Provenance Tagging
- Plan prefixes: `det_*` (deterministic), `llm_*` (LLM guess).
- Source string from executor: `action_executor|prov=<deterministic|llm_guess|external>|plan=<plan_id>|intent=<intent_id>` passed into `StateManager.set` and emitted in events.
- `ActionExecutedEvent` and `StateMutatedEvent` carry `source`.

### 8) How to Extend Safely
- New refinable paths requiring baselines/deltas: add to `_BASELINE_VALUES`, add path-aware entry to `_DELTA_POLICY`, and add to `LLM_ALLOWED_PATHS` (api.py) if LLM should propose it.
- Keep bucket policies path-specific; do not introduce global percentages.
- Maintain LLM-first translation inside `_compile_intent_with_llm_fallback()`; do not scatter LLM calls across routes.
- Preserve atomic execution: any multi-action apply must roll back entirely on error.

