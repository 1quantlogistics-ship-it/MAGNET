# Module 64: Studio v7 UI Loop Wiring

## What Changed

- `snapshot_created` WS event now safely triggers `updateGeometry()` (with null check)
- PhaseIdMapper extended with 7 missing phases: propulsion, systems, weight, stability, weight_stability, compliance, production
- `_loadHullGeometry()` shows loading overlay, uses `design_version_after` for cache-bust, offers retry hint
- `reload` / `reload geometry` command added
- Apply success echoes `Design version: X → Y` and stores version for cache-busting
- Better error messages for 409 (stale) and 423 (locked)

## Backend Contracts Assumed

| Endpoint | Contract |
|----------|----------|
| `POST /intent/preview` | Returns `apply_payload` with `design_version_before` |
| `POST /actions` | Returns `design_version_before`, `design_version_after`, `actions_executed[]` |
| `POST /phases/{phase}/run` | Accepts phase ID, backend maps `hull_form` → `hull` internally |
| `GET /3d/export/glb` | Returns binary GLB only (no JSON, no headers with hash) |
| WS `snapshot_created` | Payload: `{snapshot_id, path, phase}` — NO `url` field (verify actual keys!) |

## Cache-Bust Rule

```
cacheBust = design_version_after || Date.now()
url = `/3d/export/glb?v=${cacheBust}`
```

## Phase Mapping Contract (DO NOT REMOVE)

The UI uses a PhaseIdMapper for display/compat. This is INTENTIONAL double-mapping:

| UI Name | Backend Name | Notes |
|---------|--------------|-------|
| `hull` | `hull_form` | Backend then maps `hull_form` → `hull` internally |
| `weight` | `weight_stability` | Combined phase |
| `stability` | `weight_stability` | Same backend phase |

**Why double-mapping exists:**
1. UI shows user-friendly short names
2. Backend API accepts its canonical names
3. Backend kernel has another internal mapping layer

**DO NOT "simplify" by removing PhaseIdMapper.** It exists because:
- WebSocket `phase_completed` uses backend names
- REST endpoints accept backend names
- UI sidebar uses display names

## Commands Supported

| Command | Action |
|---------|--------|
| `apply` | Execute pending preview |
| `cancel` | Discard pending preview |
| `reload` / `reload geometry` | Force GLB re-fetch |
