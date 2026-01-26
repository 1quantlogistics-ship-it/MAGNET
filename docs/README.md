# MAGNET Documentation Index

<!-- AGENT_CONTEXT
Purpose: Documentation hub and navigation index
Authoritative: No
Keywords: index, hub, navigation, documentation
Depends_On: None
Used_By: all agents, developers
Status: current
Last_Verified: 2026-01-15
-->

Welcome to the MAGNET documentation hub. Navigate by **folder** (numbered categories) or by **topic** (cross-cutting indexes).

---

## Quick Links: Topic Indexes

| Index | Description |
|-------|-------------|
| [**Physics**](./_index/PHYSICS_INDEX.md) | All physics-related docs |
| [**Golden Path**](./_index/GOLDEN_PATH_INDEX.md) | All migration docs |
| [**Agents**](./_index/AGENTS_INDEX.md) | All agent/LLM docs |
| [**UI**](./_index/UI_INDEX.md) | All UI docs |
| [**Status**](./_index/STATUS_INDEX.md) | Docs by status (active/stale/archived) |

---

## [0. Architecture](./0-architecture/)

Foundational principles, coordinate systems, and component ownership.

| Subfolder | Contents |
|-----------|----------|
| [**core/**](./0-architecture/core/) | CONSTITUTION, NORTH_STAR, PHASE_MACHINE |
| [**geometry/**](./0-architecture/geometry/) | GEOMETRY_CONVENTIONS (coordinate systems) |
| [**system/**](./0-architecture/system/) | ARCHITECTURE_CORE, SYSTEM_ARCHITECTURE, CLI |

---

## [1. Theory](./1-theory/)

Physics, geometry, and naval architecture principles.

| Subfolder | Contents |
|-----------|----------|
| [**physics/**](./1-theory/physics/) | UNIFIED_PHYSICS_THEORY, North_Star, Gaps_And_Solutions |
| [**geometry/**](./1-theory/geometry/) | hull_generation_deep_dive, geometry-expansion-design, LensPack |

---

## [2. Protocols](./2-protocols/)

Communication patterns and system firewalls.

- [**INTENT_ACTION_PROTOCOL.md**](./2-protocols/INTENT_ACTION_PROTOCOL.md) – LLM→Kernel firewall
- [**MODULE_65.1_COMPOUND_INTENT.md**](./2-protocols/MODULE_65.1_COMPOUND_INTENT.md) – Compound intent resolution
- [**MODULE_67X_BROAD_CHAT_COMMANDS.md**](./2-protocols/MODULE_67X_BROAD_CHAT_COMMANDS.md) – Chat commands

---

## [3. Implementation](./3-implementation/)

Active plans, technical specs, and integration roadmaps.

| Subfolder | Contents |
|-----------|----------|
| [**golden-path/**](./3-implementation/golden-path/) | IMPLEMENTATION_GUIDE, TECHNICAL_SPEC |
| [**integration/**](./3-implementation/integration/) | INTEGRATION_PLAN, V2, Merge_Plan |
| [**physics/**](./3-implementation/physics/) | PHYSICS_RIGOR_PLAN |
| [**general/**](./3-implementation/general/) | Implementation_Guide, Spec, Unified_Plan |

---

## [4. Specifications](./4-specs/)

Feature-specific requirements and design plans.

| Subfolder | Contents |
|-----------|----------|
| [**agents/**](./4-specs/agents/) | Agent_Enhancement, Robustness_Tests, Prompt_Architecture |
| [**language/**](./4-specs/language/) | Design_Language_Spec_v1.0 |
| [**rendering/**](./4-specs/rendering/) | Rendering_Quality_And_Performance |
| [**failure-modes/**](./4-specs/failure-modes/) | Failure_Modes, Hard_Questions |

---

## [5. Audits](./5-audits/)

Analysis, verification, and codebase health checks.

| Subfolder | Contents |
|-----------|----------|
| [**golden-path/**](./5-audits/golden-path/) | Golden_Path_AUDIT_1 |
| [**system/**](./5-audits/system/) | System_State_Analysis, Orphaned_Components, Critical_Corrections |
| [**ui/**](./5-audits/ui/) | UIv2_Integration_Audit |
| [**modules/**](./5-audits/modules/) | AUDIT_WHY_ROUTER |
| [**prompts/**](./5-audits/prompts/) | Audit_Prompts |

---

## [6. Guides](./6-guides/)

Operational runbooks and technical notes.

- [**MAGNET_Local_Startup_Runbook.md**](./6-guides/MAGNET_Local_Startup_Runbook.md) – How to run locally
- [**SCHEMA_DIFF_NOTES.md**](./6-guides/SCHEMA_DIFF_NOTES.md) – Schema changes

---

## [Archive](./archive/)

Superseded documents kept for historical reference.

---

## Navigation Tips

- **By domain:** Use numbered folders (0-6) to find docs by category
- **By topic:** Use `_index/` files to see all related docs across folders
- **By status:** Use `_index/STATUS_INDEX.md` to find active vs stale docs
- **Reading order:** Start at 0-architecture, work through numbered folders
