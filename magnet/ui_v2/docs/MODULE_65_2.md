# Module 65.2 — Single-Server UI + API Integration

**Status**: Complete

---

## Overview

Module 65.2 simplifies MAGNET's runtime architecture by eliminating the need for a separate UI server and manual URL configuration. The UI and API now run from a single server and auto-configure at runtime using same-origin discovery.

This removes friction for first-time users and enables a clean, production-like execution path.

---

## Files Modified

| File | Change |
|------|--------|
| `api.py` | Added `UI_V2_PATH`, `/api/v1/meta` endpoint, prioritized UI v2 static serving |
| `index.html` | Reversed demo-mode logic, added `tryAutoConnect()`, `showDesignPicker()`, demo banner |
| `backend-adapter.js` | Defaulted base URL resolution to same-origin |
| `UI_V2_RUNBOOK.md` | Simplified quick-start instructions |

---

## What Changed (Behaviorally)

### Before

- **Two servers required**
  - UI on `localhost:3000`
  - API on `localhost:8000`
- UI required URL parameters (`?design=&host=&port=`)
- Missing parameters silently triggered demo mode
- No programmatic way for UI to discover backend state

### After

- **Single server** on port 8000 serves both UI and API
- UI auto-connects using same-origin
- Demo mode is explicit and visually indicated
- `/api/v1/meta` endpoint exposes backend state for UI auto-configuration

---

## New Architecture

```
┌─────────────────────────────┐
│        Browser UI           │
│  (served from /ui_v2)       │
└───────────────▲─────────────┘
                │ same-origin
┌───────────────┴─────────────┐
│        MAGNET API           │
│  /api/v1/*                  │
│  /api/v1/meta               │
│  Static UI serving          │
└─────────────────────────────┘
```

The UI discovers backend capabilities via `/api/v1/meta` and configures itself automatically.

---

## New User Flow

1. **Start the system:**
   ```bash
   python -m magnet.bootstrap.entrypoints api --port 8000
   ```

2. **Open a browser:**
   ```
   http://localhost:8000
   ```

3. **UI auto-connects to backend**
   - If designs exist → design picker shown
   - If none exist → new design is created

4. **Example prompt:**
   ```
   60m aluminum catamaran ferry beam 12m draft 3m 25 knots
   ```

5. **Apply changes:**
   ```
   apply
   ```

---

## Key Outcomes

- No URL parameters required
- No separate UI server
- No silent demo mode
- Cleaner onboarding
- Production-aligned execution path

---

## Why This Matters

This module removes setup ambiguity and aligns the developer experience with how MAGNET will run in production. It also establishes a clean contract (`/api/v1/meta`) between UI and backend that future modules can rely on.

**Net result**: fewer moving parts, fewer failure modes, faster iteration.
