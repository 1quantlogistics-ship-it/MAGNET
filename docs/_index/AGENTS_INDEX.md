# Agents Documentation Index

<!-- AGENT_CONTEXT
Purpose: [TODO: Add purpose description]
Authoritative: No
Keywords: [agents, index]
Depends_On: None
Used_By: [TODO: Add users]
Status: current
Last_Verified: 2026-01-15
-->


All agent-related documentation - multi-agent system, prompts, and LLM integration.

---

## Specifications

| Document | Description | Status |
|----------|-------------|--------|
| [MAGNET_Agent_Enhancement_Plan.md](../4-specs/agents/MAGNET_Agent_Enhancement_Plan.md) | Agent domain knowledge gaps & solutions | P0 Critical |
| [Agent_Robustness_Tests_Plan.md](../4-specs/agents/Agent_Robustness_Tests_Plan.md) | 18 robustness tests for edge cases | In Progress |
| [MAGNET_Prompt_Architecture_Plan_v2.md](../4-specs/agents/MAGNET_Prompt_Architecture_Plan_v2.md) | Compositional operators, token efficiency | Active |

## Protocols

| Document | Description | Status |
|----------|-------------|--------|
| [INTENT_ACTION_PROTOCOL.md](../2-protocols/INTENT_ACTION_PROTOCOL.md) | LLM→Kernel firewall | Reference |
| [MODULE_65.1_COMPOUND_INTENT.md](../2-protocols/MODULE_65.1_COMPOUND_INTENT.md) | Compound intent resolution | Complete |
| [MODULE_67X_BROAD_CHAT_COMMANDS.md](../2-protocols/MODULE_67X_BROAD_CHAT_COMMANDS.md) | Chat command handling | Active |

## Related Theory

| Document | Description |
|----------|-------------|
| [MAGNET_v1.2_Implementation_Theory_LensPack.md](../1-theory/geometry/MAGNET_v1.2_Implementation_Theory_LensPack.md) | Lens Pack for token efficiency |
| [MAGNET_Design_Language_Spec_v1.0.md](../4-specs/language/MAGNET_Design_Language_Spec_v1.0.md) | Design language primitives |

## Related Audits

| Document | Description |
|----------|-------------|
| [AUDIT_WHY_ROUTER.md](../5-audits/modules/AUDIT_WHY_ROUTER.md) | WhyQueryRouter contract verification |

---

## Reading Order

1. **INTENT_ACTION_PROTOCOL.md** - Understand the firewall (LLM proposes, Kernel decides)
2. **MAGNET_Agent_Enhancement_Plan.md** - Understand agent gaps
3. **MAGNET_Prompt_Architecture_Plan_v2.md** - Understand prompt design
4. **Agent_Robustness_Tests_Plan.md** - Understand test coverage

---

## Key Concepts

- **Multi-Agent System:** Conductor orchestrates specialized agents
- **Intent→Action:** LLM never directly drives state
- **Lens Pack:** Dictionary-coded compact JSON for token efficiency
- **Compound Intent:** "60m aluminum catamaran" → multiple parameters
- **Domain Knowledge:** Agent needs naval architecture expertise
