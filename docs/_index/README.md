# Topic Indexes

<!-- AGENT_CONTEXT
Purpose: Index folder overview and navigation guide
Authoritative: No
Keywords: index, navigation, topics, manifest
Depends_On: None
Used_By: all agents, developers
Status: current
Last_Verified: 2026-01-15
-->

Cross-cutting indexes that aggregate related documentation across the folder structure.

---

## For AI Agents: Machine-Readable Index

**Load [`MANIFEST.yaml`](./MANIFEST.yaml) first** for O(1) documentation lookup.

The manifest provides:
- **All 68 files** with paths and metadata
- **Keyword index** for topic-based search
- **Authority chain** - recommended reading order for new agents
- **Deprecation markers** - skip files with `status: deprecated`

```yaml
# Example: Find physics docs
keyword_index:
  physics:
    - "1-theory/physics/MAGNET_UNIFIED_PHYSICS_THEORY.md"
    - "3-implementation/physics/MAGNET_PHYSICS_RIGOR_PLAN.md"
    ...
```

---

## Available Topic Indexes (Human-Readable)

| Index | Description |
|-------|-------------|
| [PHYSICS_INDEX.md](PHYSICS_INDEX.md) | All physics-related docs (theory, implementation, specs) |
| [GOLDEN_PATH_INDEX.md](GOLDEN_PATH_INDEX.md) | All Golden Path migration docs |
| [AGENTS_INDEX.md](AGENTS_INDEX.md) | All agent/LLM-related docs |
| [UI_INDEX.md](UI_INDEX.md) | All UI-related docs |
| [STATUS_INDEX.md](STATUS_INDEX.md) | All docs categorized by status |

---

## Navigation Options

| Method | Best For |
|--------|----------|
| **MANIFEST.yaml** | AI agents, programmatic access |
| **Topic Indexes** | Human browsing by domain |
| **Folder Structure** | Human browsing by document type |

### Examples

- **Agent looking for physics docs:** Load `MANIFEST.yaml`, query `keyword_index.physics`
- **Human exploring physics:** Read `PHYSICS_INDEX.md` for curated list with context
- **Human reading implementation:** Browse `3-implementation/` folder

---

## AGENT_CONTEXT Headers

All documentation files should have an `AGENT_CONTEXT` HTML comment header:

```html
<!-- AGENT_CONTEXT
Purpose: One-sentence description
Authoritative: Yes/No
Keywords: [searchable, terms]
Depends_On: [prerequisite docs]
Used_By: [modules/agents that reference this]
Status: current/deprecated/archived
Last_Verified: 2026-01-15
-->
```

Use the validation script to check coverage:
```bash
python scripts/validate_docs.py --check
```
