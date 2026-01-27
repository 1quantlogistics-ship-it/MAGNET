# MAGNET Startup Guide

<!-- AGENT_CONTEXT
Purpose: Quick start guide for running MAGNET backend and UI v2 locally
Authoritative: Yes
Keywords: startup, guide, runbook, backend, ui, quickstart
Depends_On: None
Used_By: developers, onboarding
Status: current
Last_Verified: 2026-01-15
-->

## Backend + UI v2

### Requirements
- **Python**: `python3` available
- **Install deps** (first time):

```bash
python3 -m pip install -e .
```

### Start the backend (recommended)

```bash
python3 -m magnet.bootstrap.app --api --host 127.0.0.1 --port 8000
```

### Open the UI (important)
- Use the **canonical** URL: `http://127.0.0.1:8000/ui/v2/`
- Do **not** use `file://.../magnet/ui_v2/index.html`

### Quick “is it up?” checks

```bash
curl -sS http://127.0.0.1:8000/health | jq .
curl -sS http://127.0.0.1:8000/api/v1/meta | jq .
curl -sS http://127.0.0.1:8000/api/v1/designs | jq .
```

### Common pitfalls
- **“Backend adapter not loaded”**
  - You opened the UI at the wrong path (or without trailing slash) and the browser fetched `backend-adapter.js` from the wrong location.
  - Fix: always open `http://127.0.0.1:8000/ui/v2/` (note the trailing `/`).

- **LLM features**
  - If you’re using Anthropic, set: `ANTHROPIC_API_KEY`.
  - Offline/sandbox environments may not be able to call the provider.

