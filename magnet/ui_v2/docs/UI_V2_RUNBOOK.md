# Studio v7 UI Runbook

## Quick Start (Module 65.2)

1. Start MAGNET:
   ```bash
   python -m magnet.bootstrap.entrypoints api --port 8000
   ```

2. Open browser:
   ```
   http://localhost:8000
   ```

That's it. Studio will auto-connect and show available designs.

## Advanced Options

- Force demo mode: `http://localhost:8000/?demo=true`
- Specific design: `http://localhost:8000/?design=MAGNET-XXX`
- Debug mode: Add `&debug=true` to any URL

## What Changed (Module 65.2)

**Before**: UI served separately, required `?design=ID&host=HOST&port=PORT`
**After**: UI served from backend, auto-connects to same-origin

| Old Way | New Way |
|---------|---------|
| `python -m http.server 3000` + backend on 8000 | Just start backend on 8000 |
| `localhost:3000/?design=X&host=127.0.0.1&port=8000` | `localhost:8000` |
| Silent demo mode if params missing | Explicit demo mode with banner |

## Golden Demo Loop

```
1. Open http://localhost:8000
   → Auto-connects, shows design picker or last design

2. Type: 60m aluminum catamaran ferry beam 12m draft 3m 25 knots
   → Preview shows 7 extracted parameters

3. Type: apply
   → Design version increments
   → Hull phase runs
   → 3D model loads in viewport

4. Type: reload
   → Fresh GLB loads
```

## Demo Mode

When demo mode is active (no backend or `?demo=true`), you'll see:
- Amber banner: "DEMO MODE — No backend connected"
- Commands are simulated (no real state changes)
- Geometry won't update

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Amber "DEMO MODE" banner | Backend not running or not same-origin | Start backend: `python -m magnet.bootstrap.entrypoints api` |
| "Design changed since preview" (409) | Stale plan | Re-enter command to get fresh preview |
| "Parameter is locked" (423) | Field locked by previous action | Use different parameter |
| GLB parse error | Binary corruption or wrong endpoint | Check Network tab for actual response |
| WS not connecting | WebSocket blocked or backend down | Check console, verify backend running |
| "updateGeometry is not a function" | Old JS cached | Hard refresh (Cmd+Shift+R) |
| No geometry after apply | `snapshot_created` not emitted | Check WS messages in DevTools |

## RunPod Deployment

For RunPod CPU pods:
1. Expose port 8000 in RunPod UI (Pod Settings → HTTP Port)
2. Access via `http://<pod-ip>:8000`

For RunPod GPU pods with proxy:
1. Backend auto-detects `*-8000.proxy.runpod.net` pattern
2. Just open the RunPod proxy URL
