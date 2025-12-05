# MAGNET Project - Claude Code Agent Rules

## MANDATORY RESOURCE GUARDRAILS

These rules MUST be followed by all Claude Code agents (ALPHA, BRAVO) operating on this codebase.

### 1. PARALLEL OPERATIONS
- Maximum 2 Task subagents at a time
- Never spawn more than 3 parallel Bash commands
- Wait for completion before spawning related work

### 2. FILE SEARCH SCOPE
- ALWAYS specify path="/Users/bengibson/MAGNETV1" in Glob/Grep
- NEVER search from "/" or "~" or unscoped
- Use head_limit parameter on large searches
- Prefer targeted file reads over broad searches

### 3. BASH PROCESS MANAGEMENT
- Use explicit timeouts (timeout 60 command)
- Kill background processes when done (check with ps)
- Prefer short-running commands
- No infinite loops or watchers

### 4. MEMORY HYGIENE
- Complete one major task before starting another
- Don't accumulate unbounded context
- If context grows large, summarize and continue

### 5. AGENT PROTOCOL
- Update HANDOFF.md at session start and end
- Document resource-intensive operations before running
- Signal completion clearly

---

## VIOLATION = HARD MAC RESTART

Ignoring these rules caused 48GB RAM consumption on 2024-12-04. Follow them.

---

## Agent Roles

| Agent | Owns | Responsibilities |
|-------|------|------------------|
| ALPHA | physics/, validation/, constraints/, schemas/, geometry/, spatial/, databases/, quantization/ | Core infrastructure, physics simulation |
| BRAVO | agents/, api/, orchestration/, spiral/, memory/, checklists/, prompts/, dependencies/ | Agent orchestration, UI, memory |

## Coordination
- Use `HANDOFF.md` for inter-agent communication
- Commit prefixes: `[ALPHA]` or `[BRAVO]`
- Never modify the other agent's owned directories without coordination
