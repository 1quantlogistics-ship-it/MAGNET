# Studio v7 UI Runbook

## Local Setup

1. Start backend:
   ```bash
   cd /Users/bengibson/MAGNETV1
   python -m magnet.bootstrap.entrypoints api
   ```

2. Serve UI:
   ```bash
   cd magnet/ui_v2
   python3 -m http.server 3000
   ```

3. Open: http://localhost:3000

## Golden Demo Loop

```
1. set hull length to 40 meters
   → Preview shown
2. apply
   → Design version: 5 → 6
   → Running hull phase...
   → ✓ 3D model loaded
3. reload
   → Loading overlay → fresh GLB
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Design changed since preview" (409) | Stale plan | Re-enter command to get fresh preview |
| "Parameter is locked" (423) | Field locked by previous action | Use different parameter |
| GLB parse error | Binary corruption or wrong endpoint | Check Network tab for actual response |
| WS not connecting | Wrong URL or backend down | Check console for WebSocket error, verify backend running |
| "updateGeometry is not a function" | Old JS cached | Hard refresh (Cmd+Shift+R) |
| No geometry after apply | `snapshot_created` not emitted | Check WS messages in DevTools |
