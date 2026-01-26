# Golden Path Documentation Index

<!-- AGENT_CONTEXT
Purpose: [TODO: Add purpose description]
Authoritative: No
Keywords: [golden, path, index]
Depends_On: None
Used_By: [TODO: Add users]
Status: current
Last_Verified: 2026-01-15
-->


All Golden Path migration documentation - the primary architectural migration effort.

---

## Implementation Guides

| Document | Description | Status |
|----------|-------------|--------|
| [GOLDEN_PATH_IMPLEMENTATION_GUIDE.md](../3-implementation/golden-path/GOLDEN_PATH_IMPLEMENTATION_GUIDE.md) | Step-by-step agent execution guide | Active |
| [GOLDEN_PATH_TECHNICAL_SPEC.md](../3-implementation/golden-path/GOLDEN_PATH_TECHNICAL_SPEC.md) | Technical specification & architecture | Reference |

## Audits

| Document | Description | Status |
|----------|-------------|--------|
| [Golden_Path_AUDIT_1.md](../5-audits/golden-path/Golden_Path_AUDIT_1.md) | Initial architectural audit | Complete |

## Related Protocols

| Document | Description |
|----------|-------------|
| [INTENT_ACTION_PROTOCOL.md](../2-protocols/INTENT_ACTION_PROTOCOL.md) | LLM→Kernel firewall (Golden Path enforces this) |
| [MODULE_65.1_COMPOUND_INTENT.md](../2-protocols/MODULE_65.1_COMPOUND_INTENT.md) | Compound intent resolution |

## Related Integration Plans

| Document | Description |
|----------|-------------|
| [INTEGRATION_PLAN_V2.md](../3-implementation/integration/INTEGRATION_PLAN_V2.md) | System integration (overlaps with Golden Path) |
| [MAGNET_Merge_Implementation_Plan.md](../3-implementation/integration/MAGNET_Merge_Implementation_Plan.md) | Merge plan for orphaned components |

---

## Task Status

| Task ID | Description | Status |
|---------|-------------|--------|
| TASK-009 | Deprecate `app/` and `frontend/` | Complete |
| TASK-010 | Migrate to `magnet/ui_v2/` | Complete |
| TASK-011+ | See GOLDEN_PATH_IMPLEMENTATION_GUIDE.md | In Progress |

---

## Reading Order

1. **GOLDEN_PATH_TECHNICAL_SPEC.md** - Understand the migration plan
2. **Golden_Path_AUDIT_1.md** - Understand current state assessment
3. **GOLDEN_PATH_IMPLEMENTATION_GUIDE.md** - Execute the migration

---

## Key Concepts

- **Authoritative UI:** `magnet/ui_v2/` is the single production interface
- **Deprecated:** `app/` and `frontend/` are archive-only
- **Kernel-first:** All business logic lives in kernel, UI is stateless adapter
- **Intent→Action Protocol:** LLM proposes, Kernel validates, Kernel executes
