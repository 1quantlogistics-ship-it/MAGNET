# UI Documentation Index

<!-- AGENT_CONTEXT
Purpose: [TODO: Add purpose description]
Authoritative: No
Keywords: [ui, index]
Depends_On: None
Used_By: [TODO: Add users]
Status: current
Last_Verified: 2026-01-15
-->


All UI-related documentation - frontend architecture, rendering, and integration.

---

## Authoritative UI

**Location:** `magnet/ui_v2/`

The authoritative UI is served from `magnet/ui_v2/`. All other UI directories are deprecated.

## Deprecated Directories

| Directory | Status | Notes |
|-----------|--------|-------|
| `app/` | DEPRECATED | Legacy React frontend - archive only |
| `frontend/` | DEPRECATED | Legacy shared frontend - archive only |

---

## Specifications

| Document | Description | Status |
|----------|-------------|--------|
| [MAGNET_Rendering_Quality_And_Performance.md](../4-specs/rendering/MAGNET_Rendering_Quality_And_Performance.md) | WebGL rendering, MacBook Air performance | Implemented |

## Audits

| Document | Description | Status |
|----------|-------------|--------|
| [MAGNET_UIv2_Integration_Audit.md](../5-audits/ui/MAGNET_UIv2_Integration_Audit.md) | UIv2 integration audit | Complete |

## Related Architecture

| Document | Description |
|----------|-------------|
| [CLI_V1_ARCHITECTURE.md](../0-architecture/system/CLI_V1_ARCHITECTURE.md) | CLI architecture (kernel-first pattern) |
| [ARCHITECTURE_CORE.md](../0-architecture/system/ARCHITECTURE_CORE.md) | Component ownership including UI |

## Related Golden Path

| Document | Description |
|----------|-------------|
| [GOLDEN_PATH_IMPLEMENTATION_GUIDE.md](../3-implementation/golden-path/GOLDEN_PATH_IMPLEMENTATION_GUIDE.md) | TASK-009/010 deprecated old UIs |

---

## Reading Order

1. **MAGNET_UIv2_Integration_Audit.md** - Understand current UI state
2. **MAGNET_Rendering_Quality_And_Performance.md** - Understand rendering approach
3. **CLI_V1_ARCHITECTURE.md** - Understand "wire, don't write" pattern

---

## Key Concepts

- **Kernel-First:** UI is a stateless adapter, kernel owns all logic
- **Wire, Don't Write:** CLI/UI wires to kernel, doesn't duplicate logic
- **Single Interface:** `magnet/ui_v2/` is the only production UI
- **WebGL Rendering:** Non-enumerative path for smooth hull rendering
