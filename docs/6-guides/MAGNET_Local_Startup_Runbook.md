# MAGNET Local Startup Runbook (macOS) — Spiral Architecture (UIv2 + DesignStore + WS + GLB)

<!-- AGENT_CONTEXT
Purpose: Step-by-step guide to run MAGNET locally on macOS
Authoritative: No
Keywords: startup, local, development, runbook, macos, uvicorn
Depends_On: None
Used_By: developers, new contributors
Status: current
Last_Verified: 2026-01-15
-->

This is the **single source of truth** for running and validating the **new spiral architecture** locally on a Mac:

**UIv2 (browser)** → **/spiral/chat + /spiral/sketch** → **program execution** → **physics phases** → **GLB export** → **WebSocket updates** → **persisted DesignStore**.

---

## What “new architecture” means (operationally)

- **Single authority for mutation**: `/api/v1/designs/{design_id}/spiral/*`
- **Persistence**: `DesignStore` writes to disk (`storage/designs/{design_id}.json`)
- **Realtime**: UI receives `design_updated` + `snapshot_created` on `/ws/{design_id}`
- **No enumeration contract**: agents propose `geometry.*` primitives; kernel validates outcomes.

Key files:
- **API**: `magnet/deployment/api.py` (router wiring, UI static serving, WS)
- **Spiral endpoints**: `magnet/deployment/spiral_endpoints.py`
- **DesignStore v2**: `magnet/deployment/design_store.py`
- **UIv2**: `magnet/ui_v2/index.html`, `magnet/ui_v2/js/backend-adapter.js`, `magnet/ui_v2/js/spiral-adapter.js`
- **3D**: `magnet/ui_v2/js/scene-manager.js` (loads GLB by URL)

---

## Hard requirement (do not skip): start the API via DI bootstrap

If you run FastAPI without the DI container, spiral endpoints won’t be able to load persisted designs.

✅ Use:

```bash
python3 -m magnet.bootstrap.entrypoints api --port 8000
```

❌ Do **not** use:

```bash
uvicorn magnet.deployment.api:app
```

---

## Prereqs (macOS)

- **Python**: 3.11+ (3.12+ OK)
- **Deps**: `pip install -e ".[dev]"` (preferred) or `pip install -r requirements.txt`
- Optional but recommended: [`ripgrep`](https://github.com/BurntSushi/ripgrep) (`brew install ripgrep`) for checklist greps.

---

## Environment variables (local)

### Required for the “real” spiral loop (LLM-backed)

Spiral chat currently uses the agent stack to translate natural language → geometry program.

- **Anthropic key** (for chat; also required for sketch):

```bash
export ANTHROPIC_API_KEY="..."
```

Model override (optional):

```bash
export MAGNET_LLM_MODEL="claude-sonnet-4-20250514"
```

### Feature flags (recommended defaults for the new architecture)

```bash
export MAGNET_SPIRAL_ENABLED=true
export MAGNET_LEGACY_INTENT_PROTOCOL_ENABLED=false
export MAGNET_DESIGN_STORE_DIR="storage/designs"
```

Notes:
- `MAGNET_SPIRAL_ENABLED` gates the spiral router in `magnet/deployment/spiral_endpoints.py`.
- Legacy intent protocol endpoints are **disabled by default** in `magnet/deployment/api.py`.

---

## Local startup (copy/paste)

From repo root:

```bash
# 1) (Recommended) install deps
python3 -m pip install -e ".[dev]"

# 2) Start backend (DI bootstrapped)
export MAGNET_SPIRAL_ENABLED=true
export MAGNET_LEGACY_INTENT_PROTOCOL_ENABLED=false
export MAGNET_DESIGN_STORE_DIR="storage/designs"
export ANTHROPIC_API_KEY="..."

python3 -m magnet.bootstrap.entrypoints api --port 8000
```

Open:
- **UIv2**: `http://localhost:8000`
- **API docs**: `http://localhost:8000/docs`

---

## What the UI does at startup (so you can debug it)

### UI serving

- The backend serves UIv2 from `magnet/ui_v2/` at `/` (see `magnet/deployment/api.py` static mounting).

### Design selection

In `magnet/ui_v2/index.html`:
- If `?design=...` is present, it connects to that design.
- Otherwise it calls `GET /api/v1/designs` and auto-selects the most recent or creates a new one via `POST /api/v1/designs`.

### Connection + event loop

- WebSocket connects to `/ws/{design_id}`
- UI events:
  - `MagnetStudio.on('command', ...)` → routed to **spiral chat** (see `magnet/ui_v2/js/backend-adapter.js`)
  - `emit('sketchUpload', ...)` (from `index.html`) → routed to **spiral sketch** (see `backend-adapter.js`)

---

## Smoke test checklist (local)

### 0) Sanity: tests pass

```bash
python3 -m pytest tests/invariants/ -q
python3 -m pytest tests/deployment/ -q
```

### 1) UI loads and connects

- Visit `http://localhost:8000`
- In DevTools console, you should see:
  - backend “Connected”
  - WS connected to `/ws/{design_id}`

### 2) Spiral chat (human-in-loop)

In the UI command box, enter a simple instruction.

Expected:
- request goes to `POST /api/v1/designs/{design_id}/spiral/chat`
- backend emits `design_updated` and `snapshot_created`
- viewport loads a GLB (or retries until ready)

**If the agent responds low-confidence**:
- UI should show a confirmation dialog (from `spiral-adapter.js`)

### 3) Spiral sketch (must require confirmation)

- Click **Sketch** button → upload a PNG/JPG
- Expect:
  - first call returns `status="awaiting_confirmation"` with extracted values
  - UI shows confirmation dialog
  - only after confirm does it execute and generate GLB

### 4) Persistence (DesignStore)

After applying any spiral change:

```bash
ls -la storage/designs | head
```

You should see `{design_id}.json` files being created/updated.

---

## API-only quick probes (no browser)

### Spiral chat

```bash
curl -sS -X POST "http://localhost:8000/api/v1/designs/TEST/spiral/chat" \
  -H "Content-Type: application/json" \
  -d '{"message":"Create a hull","force_apply":true}' | jq .
```

### Spiral sketch

```bash
curl -sS -X POST "http://localhost:8000/api/v1/designs/TEST/spiral/sketch" \
  -F "image=@./path/to/sketch.png" \
  -F "annotations=25m" | jq .
```

---

## Common failure modes (and where to look)

### “No backend detected / DEMO MODE”

- Backend not running on same origin.
- Fix: start backend via `python3 -m magnet.bootstrap.entrypoints api --port 8000`

### UI calls legacy `/intent/preview` and gets 404

- You’re on a stale UI build or custom JS.
- Expected in the new architecture: UI routes commands to `/spiral/chat`.
- Check:
  - `magnet/ui_v2/js/backend-adapter.js` command handler
  - `MAGNET_LEGACY_INTENT_PROTOCOL_ENABLED` is false by default

### Spiral chat fails with provider error / missing key

- You did not set `ANTHROPIC_API_KEY`.
- For now, **spiral chat requires a working LLM**.

### GLB loads never complete

Check:
- `GET /api/v1/designs/{design_id}/3d/export/glb?v={version}` returns 200
- WS shows `snapshot_created`
- `magnet/ui_v2/js/scene-manager.js` has a working `GLTFLoader`

---

## “New architecture” validation gates (for future agents)

### Gate A: invariants

```bash
python3 -m pytest tests/invariants/ -v
```

### Gate B: spiral endpoints

```bash
python3 -m pytest tests/deployment/test_spiral_*.py -v
```

### Gate C: persistence

```bash
python3 -m pytest tests/deployment/test_design_store_persistence.py -v
```

---

## Known gaps (documented so future agents don’t waste time)

- **Local LLM selection**: `MAGNET_LLM_PROVIDER` exists, but spiral chat/sketch currently defaults to Anthropic unless refactored to honor env everywhere.
- **Dev reload**: `magnet.bootstrap.entrypoints api --reload` is parsed but not currently passed through to `uvicorn.run()` (so reload may be a no-op).


