# MAGNET Implementation Specification v1.0

<!-- AGENT_CONTEXT
Purpose: [TODO: Add purpose description]
Authoritative: No
Keywords: [magnet, implementation, spec]
Depends_On: None
Used_By: [TODO: Add users]
Status: current
Last_Verified: 2026-01-15
-->


> **Document Purpose:** Unified specification for agents, API contracts, and testing.  
> **Status:** Implementation Specification  
> **Last Updated:** 2026-01-05  
> **Version:** 1.0

---

## Table of Contents

- [Part 1: Agent Prompt Specification](#part-1-agent-prompt-specification)
  - [1.1 Core Principle](#11-core-principle)
  - [1.2 Agent Types](#12-agent-types)
  - [1.3 System Prompts](#13-system-prompts)
  - [1.4 State Injection Format](#14-state-injection-format)
  - [1.5 Feedback Format](#15-feedback-format)
  - [1.6 Structured Reasoning](#16-structured-reasoning)
  - [1.7 Multi-Agent Coordination](#17-multi-agent-coordination)
  - [1.8 Conflict Resolution](#18-conflict-resolution)
  - [1.9 Output Schema Validation](#19-output-schema-validation)
- [Part 2: API Contract](#part-2-api-contract)
  - [2.1 Base Configuration](#21-base-configuration)
  - [2.2 Design Program Endpoint](#22-design-program-endpoint)
  - [2.3 Validation Endpoint](#23-validation-endpoint)
  - [2.4 Feedback Endpoint](#24-feedback-endpoint)
  - [2.5 Streaming Protocol](#25-streaming-protocol)
  - [2.6 Error Format](#26-error-format)
  - [2.7 Schema Definitions](#27-schema-definitions)
  - [2.8 Authentication & Rate Limits](#28-authentication--rate-limits)
- [Part 3: Test Plan](#part-3-test-plan)
  - [3.1 Unit Tests](#31-unit-tests)
  - [3.2 Integration Tests](#32-integration-tests)
  - [3.3 Invariant Tests](#33-invariant-tests)
  - [3.4 Performance Tests](#34-performance-tests)
  - [3.5 Acid Tests](#35-acid-tests)
  - [3.6 Test Infrastructure](#36-test-infrastructure)
- [Part 4: Migration Specification](#part-4-migration-specification)
  - [4.1 Schema Changes](#41-schema-changes)
  - [4.2 Migration Strategy](#42-migration-strategy)
  - [4.3 Default Values](#43-default-values)
  - [4.4 Backward Compatibility](#44-backward-compatibility)
  - [4.5 Migration Validation](#45-migration-validation)
  - [4.6 Rollback Strategy](#46-rollback-strategy)
- [Implementation Checklist](#implementation-checklist)
- [Related Documents](#related-documents)

---

# Part 1: Agent Prompt Specification

## 1.1 Core Principle

```
The engineer has INFINITE CREATIVITY.
Agents are TRANSLATORS, not designers.
Agents output GEOMETRY PRIMITIVES, not decisions.
The kernel validates PHYSICS, returns NUMBERS.
```

> **Any hull form that requires a new language primitive is a failure of the language.**

**Agent Coordination Rule:** Agents never coordinate on "features" — they coordinate on **geometry and constraints only**.
- ❌ **Wrong:** Agents debate "should we add a spray rail?"  
- ✅ **Right:** Agents debate "this surface edge should introduce a discontinuity here to reduce wetted area"

**Agents must NEVER:**
- Decide what design is "best"
- Enumerate design categories (no "patrol boat", "catamaran", "stepped hull")
- Propose style/aesthetic judgments
- Block engineer intent with safety concerns
- Debate "features" — only geometry and physics

**Agents must ALWAYS:**
- Translate intent to `geometry.*` primitives
- Include confidence and reasoning
- Request clarification when intent is ambiguous
- Pass through engineer decisions unchanged

---

## 1.2 Agent Types

### Agent Taxonomy

| Agent Type | Role | Speaks When | Output Type |
|:-----------|:-----|:------------|:------------|
| **Intent Decomposer** | Parses natural language → structured problem | First in pipeline | `DesignProblem` |
| **Geometry Proposer** | Proposes primitives to achieve problem constraints | After decomposition | `DesignProgram` |
| **Critic Agent** | Reviews proposals for physics feasibility | After proposals | `CritiqueReport` |
| **Refinement Agent** | Adjusts proposals based on feedback | After critique/validation | `DesignProgram` |
| **Merge Agent** | Combines multiple proposals | When multiple proposals exist | `DesignProgram` |

### Agent Responsibilities Matrix

```
┌─────────────────────┬─────────────────────────────────────────────────────────┐
│ Agent Type          │ What It Does                                            │
├─────────────────────┼─────────────────────────────────────────────────────────┤
│ Intent Decomposer   │ "Make it faster" → { constraints: [speed > 30kts] }     │
│ Geometry Proposer   │ { speed > 30kts } → CREATE geometry.body { L/B: 6.0 }   │
│ Critic Agent        │ "L/B 6.0 with draft 1.2m → Fn > 1.0, cavitation risk"   │
│ Refinement Agent    │ Adjusts draft to 0.9m based on critique                 │
│ Merge Agent         │ Combines "fine bow" + "wide stern" proposals            │
└─────────────────────┴─────────────────────────────────────────────────────────┘
```

---

## 1.3 System Prompts

### 1.3.1 Intent Decomposer System Prompt

```python
INTENT_DECOMPOSER_SYSTEM_PROMPT = """You are MAGNET's Intent Decomposer.

YOUR ROLE:
- Convert natural language engineer requests into structured design problems
- Extract constraints (must satisfy), preferences (should satisfy), and requirements
- NEVER add constraints the engineer didn't mention
- NEVER filter or reject engineer intent

DESIGN PROBLEM STRUCTURE:
{
  "problem_id": "string",
  "original_intent": "string (the exact user input)",
  "constraints": [
    {"type": "min"|"max"|"eq"|"range", "parameter": "path", "value": number, "unit": "string"}
  ],
  "preferences": [
    {"direction": "maximize"|"minimize", "parameter": "path", "weight": 0.0-1.0}
  ],
  "requirements": [
    {"description": "string", "category": "performance"|"stability"|"geometry"}
  ],
  "ambiguities": [
    {"question": "string", "options": ["string"], "default": "string"}
  ]
}

RULES:
1. If the engineer says "fast" without a number, add ambiguity asking for target speed
2. If the engineer uses a design term you recognize (e.g., catamaran, proa, SWATH, trimaran), 
   describe the GEOMETRIC CHARACTERISTICS you believe it implies. Do NOT use a lookup table.
   If you don't recognize the term or are uncertain about its geometry, add an ambiguity 
   asking the engineer to describe the geometric arrangement they envision.
3. NEVER reject intent. If something seems impossible, add it as a constraint anyway.
4. ALWAYS preserve the original_intent verbatim for audit.

EXAMPLES:

Input: "Design a 15m fast catamaran"
Output: {
  "problem_id": "prob_abc123",
  "original_intent": "Design a 15m fast catamaran",
  "constraints": [
    {"type": "eq", "parameter": "hull.loa", "value": 15.0, "unit": "m"}
  ],
  "preferences": [
    {"direction": "maximize", "parameter": "performance.speed_kts", "weight": 0.8}
  ],
  "requirements": [
    {"description": "Two bodies with lateral offset (catamaran configuration)", "category": "geometry"}
  ],
  "ambiguities": [
    {"question": "What target speed defines 'fast'?", "options": ["25 kts", "30 kts", "35 kts", "40+ kts"], "default": "30 kts"}
  ]
}
"""
```

### 1.3.2 Geometry Proposer System Prompt

```python
GEOMETRY_PROPOSER_SYSTEM_PROMPT = """You are MAGNET's Geometry Proposer.

YOUR ROLE:
- Convert design problems into geometry primitives
- Output ONLY geometry.* operations (see allowed primitives below)
- NEVER use hull.* types (deprecated for agent use)
- Include confidence and reasoning for every operation

ALLOWED PRIMITIVES (geometry.* only):
- geometry.body: {body_id, body_type (freeform string), physics_category (freeform string), offset_x_m, offset_y_m, offset_z_m}
- geometry.section: {section_id, body_id, station_fraction (0-1), points [...], edge_types [...]}
- geometry.surface: {surface_id, body_id, definition_type (nurbs|lofted), physics_category (freeform string), ...}
- geometry.discontinuity: {id, body_id, type (freeform string), start_station, end_station, profile (freeform string), depth_m}
- geometry.flow_path: {id, body_id, medium (freeform string), inlet_point, outlet_point, cross_section_m2}
- geometry.opening: {id, surface_id, position, dimensions, purpose (freeform string)}
- geometry.attachment: {id, parent_body_id, child_body_id, attachment_type (freeform string), offset_x_m, offset_y_m, offset_z_m}

DESIGN PROGRAM FORMAT:
{
  "program_id": "string",
  "version": 1,
  "operations": [
    {
      "op": "CREATE"|"UPDATE"|"DELETE",
      "type": "geometry.body"|"geometry.section"|...,
      "id": "string (stable UUID)",
      "params": {...},
      "reasoning": "string (why this operation)",
      "confidence": 0.0-1.0
    }
  ],
  "constraints": [
    {"type": "CONSTRAIN", "constraint_type": "min_value"|"max_value"|"equality", "target": "path", "value": number}
  ]
}

PHYSICS CATEGORY RULES:
- body_type can be ANY string (e.g., "main_hull", "outrigger", "hydrofoil_strut", "sail_keel")
- physics_category can be ANY string (e.g., "submerged", "surface_piercing", "above_water", 
  "partially_submerged", "spray_zone", "cavitating", or any novel category)
- The kernel validates: "can physics be computed for this body?" NOT "is this a known category?"
- Describe the physics regime, not a design classification

RULES:
1. ALWAYS include reasoning explaining WHY this geometry achieves the goal
2. NEVER output hull.spray_rail, hull.chine, etc. — use geometry.* primitives
3. Use freeform strings for body_type, surface_type, medium — be descriptive
4. Set confidence < 0.7 if the translation is uncertain
5. If multiple approaches exist, output the SIMPLEST one first
"""
```

### 1.3.3 Critic Agent System Prompt

```python
CRITIC_AGENT_SYSTEM_PROMPT = """You are MAGNET's Critic Agent.

YOUR ROLE:
- Review geometry proposals for PHYSICS feasibility (not aesthetics)
- Identify potential issues BEFORE kernel validation
- Suggest specific adjustments with magnitudes
- NEVER reject proposals — only critique and suggest

CRITIQUE REPORT FORMAT:
{
  "critique_id": "string",
  "proposal_id": "string (the proposal being critiqued)",
  "issues": [
    {
      "severity": "warning"|"concern"|"blocker",
      "category": "stability"|"resistance"|"structural"|"geometry"|"manufacturability",
      "description": "string",
      "affected_operations": ["op_id_1", "op_id_2"],
      "suggested_adjustment": {
        "operation_id": "string",
        "parameter": "string",
        "current_value": number,
        "suggested_value": number,
        "reasoning": "string"
      }
    }
  ],
  "physics_predictions": [
    {"metric": "GM_m", "predicted_value": number, "confidence": 0.0-1.0}
  ],
  "overall_assessment": "likely_valid"|"needs_adjustment"|"high_risk",
  "confidence": 0.0-1.0
}

WHAT TO CHECK:
1. Stability (GM, GZ curve implications)
2. Resistance (Froude number regime)
3. Geometry validity (self-intersecting sections, discontinuities)
4. Manufacturability (Gaussian curvature, sharp reversals)

RULES:
1. ALWAYS provide quantified predictions, not just "too low" or "too high"
2. ALWAYS suggest specific adjustment magnitudes
3. NEVER use design-semantic terms ("this looks like a patrol boat")
4. If you can't predict a metric, set confidence < 0.5 and say why
"""
```

### 1.3.4 Refinement Agent System Prompt

```python
REFINEMENT_AGENT_SYSTEM_PROMPT = """You are MAGNET's Refinement Agent.

YOUR ROLE:
- Adjust proposals based on critique and validation feedback
- Apply suggested adjustments from critics
- Apply adjustments from kernel validation feedback
- Preserve original intent while fixing physics issues

INPUT FORMAT (you receive):
{
  "original_problem": {...},
  "current_proposal": {...},
  "critique": {...},
  "validation_feedback": {
    "passed": false,
    "findings": [...],
    "gradients": {"gm_m": {"beam": 0.12, "draft": -0.08}}
  }
}

OUTPUT FORMAT:
{
  "refined_program": {...},
  "changes_made": [
    {"operation_id": "string", "parameter": "string", "old_value": number, "new_value": number, "reason": "string"}
  ],
  "unresolved_issues": [...],
  "confidence": 0.0-1.0
}

REFINEMENT STRATEGY:
1. Apply kernel adjustment suggestions first (they have gradients)
2. Apply critic suggestions second
3. If adjustments conflict, prefer kernel (it has physics truth)
4. If an issue can't be fixed without violating original intent, add to unresolved_issues

RULES:
1. NEVER change parameters that weren't flagged in feedback
2. NEVER apply aesthetic refinements — only physics corrections
3. ALWAYS cite which feedback item motivated each change
4. If validation passed, return current_proposal unchanged
"""
```

### 1.3.5 Merge Agent System Prompt

```python
MERGE_AGENT_SYSTEM_PROMPT = """You are MAGNET's Merge Agent.

YOUR ROLE:
- Combine multiple valid proposals into a single coherent program
- Resolve conflicts between proposals
- Preserve the best aspects of each proposal

CONFLICT RESOLUTION RULES:
1. Same body, different params: prefer higher confidence proposal
2. Conflicting constraints: flag as unresolvable, return both options to engineer
3. Overlapping operations: combine if compatible, choose one if not
4. Structural conflicts (e.g., body A overlaps body B): flag for engineer decision

RULES:
1. NEVER invent new operations not present in any proposal
2. ALWAYS track which proposal each operation came from
3. If proposals are incompatible, say so and present options
4. When in doubt, keep it simple — fewer operations is better
"""
```

---

## 1.4 State Injection Format

Agents receive current design state in a standardized format:

```python
STATE_INJECTION_FORMAT = """
## Current Design State

### Geometry
```json
{
  "bodies": {
    "body_main": {
      "body_type": "displacement_monohull",
      "physics_category": "surface_piercing",
      "offset_x_m": 0, "offset_y_m": 0, "offset_z_m": 0
    }
  },
  "sections": [...],
  "surfaces": {},
  "discontinuities": {},
  "attachments": {}
}
```

### Hull Parameters (computed from geometry)
| Parameter | Value | Unit |
|:----------|:------|:-----|
| LOA | 15.0 | m |
| Beam | 4.5 | m |
| Draft | 1.2 | m |
| Displacement | 25.4 | tonnes |

### Physics Status
| Metric | Value | Target | Status |
|:-------|:------|:-------|:-------|
| GM | 0.92 | ≥0.80 | ✓ PASS |
| GZ_30 | 0.25 | ≥0.20 | ✓ PASS |

### Active Constraints
- hull.loa = 15.0m (pinned by engineer)
- mission.max_speed_kts ≥ 25 (from problem)
"""
```

---

## 1.5 Feedback Format

### Quantified Validation Feedback

```python
@dataclass
class QuantifiedFeedback:
    """Feedback format agents receive from kernel validation."""
    passed: bool
    findings: List[ValidationFinding]
    gradients: Dict[str, Dict[str, float]]  # {metric: {param: sensitivity}}
    validity_envelope: Dict[str, bool]      # Which empirical methods are valid
    
@dataclass
class ValidationFinding:
    severity: str  # "error" | "warning" | "info"
    code: str
    message: str
    path: str
    actual_value: float
    expected_value: float
    margin: float          # Negative = failing
    adjustment: Optional[AdjustmentHint]
    
@dataclass  
class AdjustmentHint:
    path: str              # Parameter to adjust
    direction: str         # "increase" | "decrease"
    magnitude: float       # Suggested change amount
    unit: str
    gradient: float        # ∂metric/∂param
    confidence: float
```

### Example Feedback

```json
{
  "passed": false,
  "findings": [
    {
      "severity": "error",
      "code": "STABILITY_001",
      "message": "Initial GM below minimum requirement",
      "path": "stability.gm_m",
      "actual_value": 0.45,
      "expected_value": 0.80,
      "margin": -0.35,
      "adjustment": {
        "path": "hull.beam",
        "direction": "increase",
        "magnitude": 0.42,
        "unit": "m",
        "gradient": 0.12,
        "confidence": 0.85
      }
    }
  ],
  "gradients": {
    "gm_m": {"hull.beam": 0.12, "hull.draft": -0.08, "hull.vcg": -0.15}
  },
  "validity_envelope": {
    "holtrop_mennen": true,
    "savitsky": false
  }
}
```

---

## 1.6 Structured Reasoning

All agent outputs must include structured reasoning:

```python
REASONING_TEMPLATE = """
## Reasoning Trace

### 1. Intent Understanding
{what_the_engineer_wants}

### 2. Current State Analysis  
{relevant_aspects_of_current_design}

### 3. Approach Selection
{why_this_approach_was_chosen}

### 4. Operation Justification
For each operation:
- Operation: {op_type} {resource_type}
- Purpose: {what_this_achieves}
- Confidence: {0-1} because {reasoning}

### 5. Risk Assessment
- Potential issues: {list}
- Mitigation: {how_addressed}

### 6. Verification Criteria
- Success if: {conditions}
- Fail if: {conditions}
"""
```

---

## 1.7 Multi-Agent Coordination

### Orchestration Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATOR                                       │
│                    (manages agent sequence, tracks state)                   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
   ┌───────────┐            ┌───────────┐            ┌───────────┐
   │  Intent   │            │ Geometry  │            │  Critic   │
   │Decomposer │───────────▶│ Proposer  │───────────▶│   Agent   │
   └───────────┘            └───────────┘            └───────────┘
         │                        │                        │
         │ DesignProblem         │ DesignProgram         │ CritiqueReport
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                                  ▼
                           ┌───────────┐
                           │Refinement │◀─────────────┐
                           │   Agent   │              │
                           └─────┬─────┘              │
                                 │                    │
                                 ▼                    │
                           ┌───────────┐              │
                           │  KERNEL   │──────────────┘
                           │VALIDATION │  (feedback loop until pass or max iterations)
                           └───────────┘
```

### Agent Sequencing Rules

```python
class AgentSequencer:
    def next_agent(self, state: OrchestrationState) -> AgentType:
        if not state.has_problem:
            return AgentType.INTENT_DECOMPOSER
        if not state.has_proposal:
            return AgentType.GEOMETRY_PROPOSER
        if not state.has_critique and state.iteration == 1:
            return AgentType.CRITIC_AGENT
        if state.needs_refinement:
            return AgentType.REFINEMENT_AGENT
        if state.has_multiple_proposals:
            return AgentType.MERGE_AGENT
        return AgentType.DONE
```

### Iteration Control

```python
ITERATION_CONFIG = {
    "max_iterations": 5,           # Maximum refinement attempts
    "max_no_progress": 3,          # Stop if no improvement for N iterations
    "timeout_seconds": 30,         # Per-agent timeout
    "total_timeout_seconds": 120,  # Total orchestration timeout
}
```

---

## 1.8 Conflict Resolution

### Conflict Types

| Conflict Type | Example | Resolution Strategy |
|:--------------|:--------|:--------------------|
| Parameter Conflict | Agent A: beam=5m, Agent B: beam=4m | Higher confidence wins |
| Structural Conflict | Two bodies occupy same space | Flag for engineer |
| Constraint Violation | Proposal violates engineer constraint | Reject proposal, try again |
| Intent Ambiguity | "Fast" could mean 25kts or 40kts | Ask engineer |
| Physics Incompatibility | Can't satisfy both GM and speed | Present tradeoff to engineer |

### Escalation Format

```json
{
  "escalation_type": "conflict",
  "message": "I found two possible approaches. Which do you prefer?",
  "options": [
    {
      "option_id": "A",
      "description": "Wider hull (beam=5m) for stability",
      "tradeoffs": ["Higher resistance", "Better GM"],
      "predicted_metrics": {"GM": 1.2, "resistance_kw": 85}
    },
    {
      "option_id": "B", 
      "description": "Narrower hull (beam=4m) for speed",
      "tradeoffs": ["Lower GM", "Better speed"],
      "predicted_metrics": {"GM": 0.85, "resistance_kw": 65}
    }
  ],
  "recommendation": "A",
  "recommendation_reasoning": "Option A provides better stability margin"
}
```

---

## 1.9 Output Schema Validation

### JSON Schema for Agent Outputs

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AgentOutput",
  "type": "object",
  "required": ["agent_type", "output_type", "content", "reasoning", "confidence"],
  "properties": {
    "agent_type": {
      "type": "string",
      "enum": ["intent_decomposer", "geometry_proposer", "critic", "refinement", "merge"]
    },
    "output_type": {
      "type": "string",
      "enum": ["design_problem", "design_program", "critique_report", "merge_result"]
    },
    "content": {
      "type": "object",
      "description": "The actual output (DesignProblem, DesignProgram, etc.)"
    },
    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1
    }
  }
}
```

---

# Part 2: API Contract

## 2.1 Base Configuration

```yaml
openapi: 3.0.3
info:
  title: MAGNET Design API
  version: 1.0.0
  description: API for multi-agent naval architecture design system

servers:
  - url: http://localhost:8000
    description: Local development
  - url: https://api.magnet.dev
    description: Production

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

---

## 2.2 Design Program Endpoint

### `POST /program`

Execute a design program against the current design state.

#### Request Body

```json
{
  "design_id": "string (UUID)",
  "program": {
    "program_id": "string",
    "version": 1,
    "operations": [
      {
        "op": "CREATE | UPDATE | DELETE",
        "type": "geometry.body | geometry.section | geometry.surface | ...",
        "id": "string (stable resource ID)",
        "params": {
          "body_type": "string (freeform)",
          "physics_category": "string (freeform, e.g., submerged, surface_piercing, cavitating)",
          "offset_x_m": 0.0,
          "offset_y_m": 0.0,
          "offset_z_m": 0.0
        }
      }
    ],
    "constraints": [
      {
        "type": "CONSTRAIN",
        "constraint_type": "min_value | max_value | equality",
        "target": "path.to.parameter",
        "value": 0.0
      }
    ]
  },
  "options": {
    "dry_run": false,
    "validate_only": false,
    "include_gradients": true,
    "max_iterations": 5
  }
}
```

#### Response Body (Success)

```json
{
  "success": true,
  "program_id": "string",
  "design_id": "string",
  "design_version": 42,
  
  "committed_state": {
    "bodies": {...},
    "sections": [...],
    "computed_params": {"hull.loa": 15.0, "hull.beam": 4.5}
  },
  
  "validation": {
    "passed": true,
    "tier": "full",
    "findings": [],
    "metrics": {"gm_m": 0.92, "gz_30_m": 0.25, "resistance_cruise_kw": 45.2}
  },
  
  "feedback": {
    "gradients": {"gm_m": {"hull.beam": 0.12, "hull.draft": -0.08}},
    "suggestions": [],
    "validity_envelope": {"holtrop_mennen": true, "savitsky": false}
  },
  
  "trace": {
    "operations_executed": 3,
    "compile_time_ms": 45,
    "validate_time_ms": 120,
    "total_time_ms": 165
  }
}
```

#### Response Body (Validation Failed)

```json
{
  "success": false,
  "program_id": "string",
  "design_id": "string",
  "design_version": 41,
  "committed_state": null,
  
  "validation": {
    "passed": false,
    "findings": [
      {
        "severity": "error",
        "code": "STABILITY_001",
        "message": "Initial GM below minimum requirement",
        "path": "stability.gm_m",
        "actual_value": 0.45,
        "expected_value": 0.80,
        "margin": -0.35,
        "adjustment": {
          "path": "hull.beam",
          "direction": "increase",
          "magnitude": 0.42,
          "unit": "m",
          "gradient": 0.12,
          "confidence": 0.85
        }
      }
    ]
  },
  
  "feedback": {
    "gradients": {"gm_m": {"hull.beam": 0.12, "hull.draft": -0.08, "hull.vcg": -0.15}},
    "suggestions": [
      {
        "priority": 1,
        "action": "Increase beam by 0.42m to achieve GM target",
        "impact": "GM: 0.45 → 0.85m (+0.40m)",
        "side_effects": ["Resistance +8%", "Displacement +12%"]
      }
    ]
  }
}
```

---

## 2.3 Validation Endpoint

### `POST /validate`

Validate a program without committing changes (dry run).

#### Request

```json
{
  "design_id": "string",
  "program": { ... },
  "tiers": ["hydrostatics", "resistance", "seakeeping"],
  "include_gradients": true
}
```

#### Response

```json
{
  "valid": true,
  "tier_results": {
    "hydrostatics": {
      "passed": true,
      "findings": [],
      "metrics": {"gm_m": 0.92, "displacement_tonnes": 25.4}
    },
    "resistance": {
      "passed": true,
      "findings": [],
      "metrics": {"resistance_cruise_kw": 45.2},
      "validity_note": "Holtrop-Mennen method applicable for Fn=0.38"
    },
    "seakeeping": {
      "passed": null,
      "validity_note": "Simplified model, recommend CFD for final design"
    }
  },
  "gradients": { ... },
  "estimated_state": {"hull.loa": 15.0, "hull.beam": 4.5, "stability.gm_m": 0.92}
}
```

---

## 2.4 Feedback Endpoint

### `GET /feedback/{design_id}`

Get detailed quantified feedback for current design state.

#### Response

```json
{
  "design_id": "string",
  "design_version": 42,
  "timestamp": "2026-01-05T12:00:00Z",
  
  "current_state": {
    "hull.loa": 15.0,
    "hull.beam": 4.5,
    "stability.gm_m": 0.92
  },
  
  "targets": {
    "stability.gm_m": {"min": 0.80, "target": 1.0, "max": null}
  },
  
  "margins": {
    "stability.gm_m": {"value": 0.92, "margin": 0.12, "status": "pass"}
  },
  
  "sensitivity_matrix": {
    "gm_m": {
      "hull.beam": {"gradient": 0.12, "unit": "m/m"},
      "hull.draft": {"gradient": -0.08, "unit": "m/m"}
    }
  },
  
  "what_if": [
    {
      "scenario": "Increase beam by 0.5m",
      "effects": {
        "gm_m": {"current": 0.92, "predicted": 0.98, "change": "+0.06"},
        "displacement_tonnes": {"current": 25.4, "predicted": 28.1, "change": "+2.7"}
      }
    }
  ],
  
  "validity_envelope": {
    "holtrop_mennen": {"valid": true, "reason": "L/B=3.33, Fn=0.38 within method bounds"},
    "savitsky": {"valid": false, "reason": "Fn=0.38 < 1.0, not in planing regime"}
  }
}
```

---

## 2.5 Streaming Protocol

### WebSocket Connection: `/ws/{design_id}`

### Connection Flow

```
Client                                    Server
  │                                          │
  │──── CONNECT /ws/{design_id} ──────────▶│
  │◀─────── CONNECTION_ACK ──────────────────│
  │──── SUBSCRIBE {events: [...]} ────────▶│
  │◀─────── SUBSCRIBED ──────────────────────│
  │                                          │
  │◀─────── ITERATION_START ─────────────────│
  │◀─────── AGENT_OUTPUT ────────────────────│
  │◀─────── VALIDATION_START ────────────────│
  │◀─────── VALIDATION_PROGRESS ─────────────│
  │◀─────── VALIDATION_COMPLETE ─────────────│
  │◀─────── ITERATION_COMPLETE ──────────────│
```

### Event Types

```typescript
// Server → Client events
type ServerEvent = 
  | { type: "CONNECTION_ACK"; session_id: string; design_version: number }
  | { type: "ITERATION_START"; iteration: number; agent: AgentType }
  | { type: "AGENT_OUTPUT"; agent: AgentType; output: AgentOutput; confidence: number }
  | { type: "VALIDATION_START"; iteration: number }
  | { type: "VALIDATION_PROGRESS"; tier: string; status: "running" | "complete"; metrics?: Record<string, number> }
  | { type: "VALIDATION_COMPLETE"; passed: boolean; findings: ValidationFinding[]; metrics: Record<string, number> }
  | { type: "ITERATION_COMPLETE"; iteration: number; result: "pass" | "refine" | "escalate" | "fail" }
  | { type: "PROGRAM_COMPLETE"; success: boolean; final_state: DesignState }
  | { type: "ESCALATION"; message: string; options: EscalationOption[] }
  | { type: "ERROR"; code: string; message: string }

// Client → Server events
type ClientEvent =
  | { type: "SUBSCRIBE"; events: string[] }
  | { type: "ESCALATION_RESPONSE"; option_id: string }
  | { type: "CANCEL" }
  | { type: "PING" }
```

---

## 2.6 Error Format

### Standard Error Response

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": { ... },
    "trace_id": "string (for support)"
  }
}
```

### Error Taxonomy

| Category | Code | HTTP Status | Description |
|:---------|:-----|:------------|:------------|
| **Parse** | `PARSE_001` | 400 | Invalid JSON syntax |
| **Parse** | `PARSE_002` | 400 | Missing required field |
| **Parse** | `PARSE_003` | 400 | Invalid operation type |
| **Parse** | `PARSE_004` | 400 | Unknown primitive type |
| **Validation** | `VAL_001` | 422 | Physics validation failed |
| **Validation** | `VAL_002` | 422 | Constraint violation |
| **Validation** | `VAL_003` | 422 | Geometry invalid (self-intersecting) |
| **Validation** | `VAL_004` | 422 | Resource not found |
| **Physics** | `PHYS_001` | 422 | Stability check failed |
| **Physics** | `PHYS_002` | 422 | Resistance calculation failed |
| **Physics** | `PHYS_003` | 422 | Outside empirical method validity |
| **System** | `SYS_001` | 500 | Internal kernel error |
| **System** | `SYS_002` | 500 | LLM provider unavailable |
| **System** | `SYS_003` | 503 | Service overloaded |
| **Auth** | `AUTH_001` | 401 | Invalid or expired token |
| **Auth** | `AUTH_002` | 403 | Insufficient permissions |

---

## 2.7 Schema Definitions

### Core Schemas

```yaml
components:
  schemas:
    
    DesignProgram:
      type: object
      required: [program_id, version, operations]
      properties:
        program_id:
          type: string
          format: uuid
        version:
          type: integer
          minimum: 1
        operations:
          type: array
          items:
            $ref: '#/components/schemas/Operation'
    
    Operation:
      type: object
      required: [op, type, id]
      properties:
        op:
          type: string
          enum: [CREATE, UPDATE, DELETE]
        type:
          type: string
          enum: [geometry.body, geometry.section, geometry.surface, geometry.discontinuity, geometry.flow_path, geometry.opening, geometry.attachment]
        id:
          type: string
        params:
          type: object
        reasoning:
          type: string
        confidence:
          type: number
          minimum: 0
          maximum: 1
    
    ValidationFinding:
      type: object
      required: [severity, code, message]
      properties:
        severity:
          type: string
          enum: [error, warning, info]
        code:
          type: string
        message:
          type: string
        path:
          type: string
        actual_value:
          type: number
        expected_value:
          type: number
        margin:
          type: number
        adjustment:
          $ref: '#/components/schemas/AdjustmentHint'
    
    AdjustmentHint:
      type: object
      required: [path, direction, magnitude]
      properties:
        path:
          type: string
        direction:
          type: string
          enum: [increase, decrease]
        magnitude:
          type: number
        unit:
          type: string
        gradient:
          type: number
        confidence:
          type: number
          minimum: 0
          maximum: 1
```

---

## 2.8 Authentication & Rate Limits

### JWT Token Format

```json
{
  "sub": "user_id",
  "iss": "magnet.auth",
  "aud": "magnet.api",
  "exp": 1736100000,
  "scope": ["design:read", "design:write", "program:execute"],
  "design_ids": ["uuid1", "uuid2"]
}
```

### Required Scopes

| Endpoint | Required Scope |
|:---------|:---------------|
| `GET /feedback/{id}` | `design:read` |
| `POST /validate` | `design:read` |
| `POST /program` | `program:execute` |
| `WS /ws/{id}` | `design:read` |

### Rate Limits

| Endpoint | Rate Limit | Burst |
|:---------|:-----------|:------|
| `POST /program` | 10/min | 3 |
| `POST /validate` | 30/min | 10 |
| `GET /feedback` | 60/min | 20 |
| WebSocket events | 100/min | 50 |

---

# Part 3: Test Plan

## 3.1 Unit Tests

### Design Language Parser

| Test ID | Test Name | Input | Expected Output | Pass Criteria |
|:--------|:----------|:------|:----------------|:--------------|
| `PARSE_001` | Valid CREATE body | `{"op": "CREATE", "type": "geometry.body", ...}` | Parsed Operation | No errors |
| `PARSE_002` | Reject hull.* types | `{"op": "CREATE", "type": "hull.spray_rail", ...}` | ParseError | Error code `PARSE_004` |
| `PARSE_003` | Any physics_category | `{"physics_category": "submerged"}` | Parsed | No errors |
| `PARSE_004` | Novel physics_category | `{"physics_category": "cavitating_supercritical"}` | Parsed | No errors, freeform accepted |
| `PARSE_005` | Freeform body_type | `{"body_type": "novel_stabilizer"}` | Parsed | No errors, any string accepted |

```python
def test_reject_deprecated_hull_types():
    """Agents must not use hull.* types."""
    program = {
        "program_id": "test",
        "version": 1,
        "operations": [
            {"op": "CREATE", "type": "hull.spray_rail", "id": "rail_1", "params": {}}
        ]
    }
    with pytest.raises(ParseError) as exc:
        parse_program(program)
    assert exc.value.code == "PARSE_004"
    assert "geometry." in exc.value.message
```

### Semantic Expander

| Test ID | Test Name | Input | Expected Output |
|:--------|:----------|:------|:----------------|
| `EXPAND_001` | MIRROR body | `MIRROR body_main` | Two bodies with negated offset_y |
| `EXPAND_002` | ALIGN sections | `ALIGN section_A section_B` | Sections at same station |
| `EXPAND_003` | SCALE body | `SCALE body_main 1.1` | All dimensions scaled 10% |
| `EXPAND_004` | DERIVE displacement | `DERIVE displacement FROM geometry` | Computed value |
| `EXPAND_005` | LOFT sections | `LOFT [sec_1, sec_2, sec_3]` | Valid NURBSSurface |

### Geometry Compiler

| Test ID | Test Name | Pass Criteria |
|:--------|:----------|:--------------|
| `COMPILE_001` | Body → HullGeometry | Valid canonical object |
| `COMPILE_002` | Section → HullSection | Points preserved |
| `COMPILE_003` | Surface → NURBSSurface | Control points valid |
| `COMPILE_004` | Multi-body compile | Separate HullGeometry instances |

```python
def test_no_second_geometry_engine():
    """Language compiles INTO existing HullSection/NURBSSurface."""
    from magnet.hull_gen.geometry import HullSection, HullGeometry
    from magnet.hull_gen.nurbs import NURBSSurface
    
    program = create_test_program_with_sections()
    compiled = compile_to_canonical(program)
    
    for section in compiled.sections:
        assert isinstance(section, HullSection)
    for surface in compiled.surfaces:
        assert isinstance(surface, NURBSSurface)
```

### Validation Pipeline

| Test ID | Test Name | Pass Criteria |
|:--------|:----------|:--------------|
| `VAL_001` | Hydrostatics pass | GM > min |
| `VAL_002` | Hydrostatics fail | passed=False, adjustment hint with gradient |
| `VAL_003` | Quantified feedback | Numerical values, no "too low" without numbers |
| `VAL_004` | Validity envelope | Method validity flags present |

```python
def test_quantified_feedback_includes_gradients():
    """Validation must return numbers, not just pass/fail."""
    geometry = create_marginal_stability_geometry()
    result = validate_geometry(geometry, include_gradients=True)
    
    assert not result.passed
    finding = result.findings[0]
    assert finding.actual_value is not None
    assert finding.adjustment.gradient is not None
    assert abs(finding.adjustment.gradient) > 0.001
```

---

## 3.2 Integration Tests

### Full Pipeline Tests

| Test ID | Test Name | Scenario | Pass Criteria | Timeout |
|:--------|:----------|:---------|:--------------|:--------|
| `INT_001` | Simple monohull | "Create 10m monohull" | Valid geometry | 30s |
| `INT_002` | Catamaran from primitives | "Create catamaran" → two bodies | No "catamaran" type | 30s |
| `INT_003` | Stepped hull from primitives | "Add step for ventilation" | geometry.discontinuity used | 30s |
| `INT_004` | Validation feedback loop | Create invalid → refine | Passes within 5 iterations | 60s |
| `INT_005` | Escalation to engineer | Impossible constraint | Escalation event fired | 30s |

```python
@pytest.mark.integration
def test_dual_body_vessel_from_primitives():
    """Multi-body vessels emerge from geometry.body composition, not hull_type enum."""
    intent = "Design a 12m vessel with two hulls for coastal patrol"
    result = execute_design_intent(intent, max_iterations=5)
    
    assert result.success
    bodies = result.final_state.get("resources.bodies", {})
    assert len(bodies) >= 2
    
    y_offsets = [b["offset_y_m"] for b in bodies.values()]
    assert min(y_offsets) < 0 and max(y_offsets) > 0
    
    # CRITICAL: No "catamaran" string anywhere
    program_json = json.dumps(result.program)
    assert "catamaran" not in program_json.lower()
```

### API Integration Tests

| Test ID | Test Name | Endpoint | Pass Criteria |
|:--------|:----------|:---------|:--------------|
| `API_001` | Execute valid program | `POST /program` | 200, state committed |
| `API_002` | Reject invalid program | `POST /program` | 400, parse error |
| `API_003` | Physics failure response | `POST /program` | 422, adjustment hints |
| `API_004` | Validation dry run | `POST /validate` | 200, no state change |
| `API_005` | Get feedback | `GET /feedback/{id}` | 200, gradients present |
| `API_006` | WebSocket iteration events | `WS /ws/{id}` | ITERATION_* events received |

---

## 3.3 Invariant Tests

These tests run on every commit and **block merge** if failed.

| Invariant ID | Rule | Test Method |
|:-------------|:-----|:------------|
| `INV_001` | No "catamaran" in kernel | grep kernel/ |
| `INV_002` | No "stepped" in kernel | grep kernel/ |
| `INV_003` | No "planing" in kernel | grep kernel/ |
| `INV_004` | No "patrol" in kernel | grep kernel/ |
| `INV_005` | No HullType enum in new code | AST analysis |
| `INV_006` | No hull.* in agent outputs | Output validation |
| `INV_007` | All validation returns numbers | Return type check |
| `INV_008` | Geometry compiles to canonical | Type assertion |

```python
# Design types = vessel classifications (FORBIDDEN in kernel)
FORBIDDEN_DESIGN_TYPES = [
    "patrol_boat", "workboat", "ferry", "yacht", "tanker", "container_ship",
    "fishing_vessel", "tug", "supply_vessel", "crew_boat"
]

# Hull configurations = geometric arrangements (FORBIDDEN as kernel logic, OK in comments/docs)
FORBIDDEN_HULL_CONFIGS = [
    "catamaran", "trimaran", "monohull", "swath", "proa", "outrigger_canoe"
]

# Physics terms = regimes/behaviors (ALLOWED - these describe physics, not design intent)
# "planing", "displacement", "submerged", "cavitating" are physics, not design

KERNEL_PATHS = ["magnet/kernel/", "magnet/hull_gen/generator.py", "magnet/physics/"]

@pytest.mark.invariant
@pytest.mark.parametrize("term", FORBIDDEN_DESIGN_TYPES + FORBIDDEN_HULL_CONFIGS)
def test_no_design_terms_in_kernel(term):
    """INVARIANT: Kernel must not contain design-semantic terms."""
    for path in KERNEL_PATHS:
        result = subprocess.run(["grep", "-ri", term, path], capture_output=True, text=True)
        matches = [line for line in result.stdout.split('\n')
                   if line and not line.strip().startswith('#') and '"""' not in line]
        assert len(matches) == 0, f"Forbidden term '{term}' found in kernel"
```

---

## 3.4 Performance Tests

### Latency Requirements

| Operation | Target | P95 Target |
|:----------|:-------|:-----------|
| Parse program | <50ms | <100ms |
| Expand semantics | <100ms | <200ms |
| Compile to canonical | <200ms | <500ms |
| Hydrostatics validation | <500ms | <1s |
| Full pipeline (intent→valid) | <2s | <5s |
| Agent LLM call | <3s | <10s |

```python
@pytest.mark.performance
def test_validation_latency():
    """Validation must complete in <1s for real-time feedback."""
    geometry = create_complex_geometry(sections=20)
    
    start = time.perf_counter()
    result = validate_geometry(geometry, include_gradients=True)
    elapsed = time.perf_counter() - start
    
    assert elapsed < 1.0, f"Validation took {elapsed:.2f}s, target <1s"
```

### Throughput Requirements

| Metric | Target |
|:-------|:-------|
| Concurrent designs | 10 |
| Programs/second | 5 |
| WebSocket connections | 100 per server |

---

## 3.5 Acid Tests

### Acid Test #1: Dual-Body Composition (No Design Enum)

```python
@pytest.mark.acid
def test_acid_dual_body_from_primitives():
    """
    Multi-hull vessels MUST emerge from body composition:
    - Two geometry.body primitives with lateral offset
    - NO design type strings (catamaran, etc.) in kernel operations
    """
    program = {
        "program_id": "acid_dual_body",
        "version": 1,
        "operations": [
            {"op": "CREATE", "type": "geometry.body", "id": "hull_port",
             "params": {"body_type": "slender_displacement", "physics_category": "surface_piercing", "offset_y_m": -3.0}},
            {"op": "CREATE", "type": "geometry.body", "id": "hull_stbd",
             "params": {"body_type": "slender_displacement", "physics_category": "surface_piercing", "offset_y_m": 3.0}}
        ]
    }
    result = execute_program(program)
    assert "catamaran" not in str(result).lower()
    bodies = result.committed_state.get("resources.bodies", {})
    assert len(bodies) == 2
```

### Acid Test #2: Surface Discontinuity Composition (No Feature Enum)

```python
@pytest.mark.acid
def test_acid_discontinuity_from_primitives():
    """
    Hull features MUST emerge from discontinuity primitives:
    - geometry.discontinuity with transverse orientation
    - geometry.flow_path for ventilation
    - NO feature type strings (stepped_hull, etc.) in kernel operations
    """
    program = {
        "program_id": "acid_discontinuity",
        "version": 1,
        "operations": [
            {"op": "CREATE", "type": "geometry.body", "id": "main_hull",
             "params": {"body_type": "high_speed_planing", "physics_category": "surface_piercing"}},
            {"op": "CREATE", "type": "geometry.discontinuity", "id": "step_1",
             "params": {"body_id": "main_hull", "type": "transverse_step", "start_station": 0.55, "depth_m": 0.12}},
            {"op": "CREATE", "type": "geometry.flow_path", "id": "vent_1",
             "params": {"body_id": "main_hull", "medium": "air", "cross_section_m2": 0.02}}
        ]
    }
    result = execute_program(program)
    assert "stepped" not in json.dumps(result.program).lower().replace("transverse_step", "")
```

### Acid Test #3: Unbounded Novel Configuration

```python
@pytest.mark.acid
def test_acid_unbounded_novel_configuration():
    """
    Configurations NEVER enumerated in any codebase must work:
    - Asymmetric multi-body arrangements
    - Freeform body_type and physics_category strings
    - No parse errors for novel types
    """
    program = {
        "program_id": "acid_novel",
        "version": 1,
        "operations": [
            {"op": "CREATE", "type": "geometry.body", "id": "main",
             "params": {"body_type": "wave_piercing_displacement", "physics_category": "surface_piercing"}},
            {"op": "CREATE", "type": "geometry.body", "id": "outrigger_port",
             "params": {"body_type": "stability_ama", "physics_category": "surface_piercing", "offset_y_m": -5.0}},
            {"op": "CREATE", "type": "geometry.body", "id": "outrigger_stbd",
             "params": {"body_type": "stability_ama_large", "physics_category": "surface_piercing", "offset_y_m": 4.0}},
            {"op": "CREATE", "type": "geometry.body", "id": "foil_strut",
             "params": {"body_type": "hydrofoil_vertical_strut", "physics_category": "submerged", "offset_z_m": -1.5}}
        ]
    }
    result = execute_program(program)
    # Novel types should NOT cause parse errors
    if not result.success:
        for finding in result.validation.findings:
            assert "unknown type" not in finding.message.lower()
```

---

## 3.6 Test Infrastructure

### Fixtures

```python
# tests/conftest.py

@pytest.fixture
def state_manager():
    """Fresh state manager for each test."""
    return StateManager(design_id="test_design")

@pytest.fixture
def validator(state_manager):
    """Validator with test configuration."""
    return DesignValidator(state_manager)

@pytest.fixture
def test_program():
    """Minimal valid program for testing."""
    return {
        "program_id": "test_prog",
        "version": 1,
        "operations": [
            {"op": "CREATE", "type": "geometry.body", "id": "hull_main",
             "params": {"body_type": "test_hull", "physics_category": "surface_piercing"}}
        ]
    }
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
name: MAGNET Tests
on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pytest tests/unit -v --tb=short

  invariant-tests:
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/invariants -v --tb=short -x  # -x = fail fast

  integration-tests:
    needs: [unit-tests, invariant-tests]
    steps:
      - run: pytest tests/integration -v --tb=short

  acid-tests:
    needs: [integration-tests]
    steps:
      - run: pytest tests/ -m acid -v --tb=long
```

### Coverage Requirements

| Module | Target Coverage |
|:-------|:----------------|
| `kernel/language/` | 90% |
| `kernel/validator.py` | 85% |
| `agents/prompts/` | 80% |
| `hull_gen/geometry.py` | 85% |
| `deployment/api.py` | 80% |

---

# Part 4: Migration Specification

This section defines how existing designs migrate to the new primitives-based schema.

---

## 4.1 Schema Changes

### Before/After Comparison

#### Old Schema (v1.x)

```python
@dataclass
class HullState:
    hull_type: HullType  # Enum: MONOHULL, CATAMARAN, TRIMARAN, ...
    loa: float
    lwl: float
    beam: float
    draft: float
    
    # Features as lists
    spray_rails: List[SprayRailConfig]
    chines: List[ChineConfig]
    knuckle_lines: List[KnuckleConfig]
```

#### New Schema (v2.0)

```python
@dataclass
class DesignState:
    resources: ResourceStore = field(default_factory=ResourceStore)
    computed: ComputedParameters = field(default_factory=ComputedParameters)
    constraints: ConstraintStore = field(default_factory=ConstraintStore)

@dataclass
class ResourceStore:
    bodies: Dict[str, BodyConfig] = field(default_factory=dict)
    sections: Dict[str, SectionConfig] = field(default_factory=dict)
    surfaces: Dict[str, SurfaceConfig] = field(default_factory=dict)
    discontinuities: Dict[str, DiscontinuityConfig] = field(default_factory=dict)
    flow_paths: Dict[str, FlowPathConfig] = field(default_factory=dict)
    openings: Dict[str, OpeningConfig] = field(default_factory=dict)
    attachments: Dict[str, AttachmentConfig] = field(default_factory=dict)
```

### Field Mapping Table

| Old Path | New Path | Transformation |
|:---------|:---------|:---------------|
| `hull.hull_type` | `resources.bodies[main].body_type` | Enum → freeform string |
| `hull.loa` | `computed.loa_m` | Moved to computed |
| `hull.beam` | `computed.beam_m` | Moved to computed |
| `hull.draft` | `computed.draft_m` | Moved to computed |
| `hull.spray_rails[i]` | `resources.discontinuities[spray_rail_i]` | List → dict with stable ID |
| `hull.chines[i]` | `resources.discontinuities[chine_i]` | List → dict with stable ID |
| `hull.features.transom_cutout` | `resources.openings[transom_cutout]` | Nested → flat |

### HullType → Primitives Mapping

| Old HullType | New Primitives | Body Count | Physics Category |
|:-------------|:---------------|:-----------|:-----------------|
| `MONOHULL` | 1 body, offset_y=0 | 1 | surface_piercing |
| `CATAMARAN` | 2 bodies, offset_y=±spacing/2 | 2 | surface_piercing |
| `TRIMARAN` | 3 bodies | 3 | surface_piercing |
| `SWATH` | 2 bodies, physics_category=submerged | 2 | submerged |
| `PLANING` | 1 body, body_type="planing_v" | 1 | surface_piercing |

---

## 4.2 Migration Strategy

### Migration Modes

| Mode | Description | Use Case |
|:-----|:------------|:---------|
| **Automatic** | Convert on load, transparent to user | Default |
| **On-Demand** | Convert when user explicitly requests | Legacy support |
| **Dual-Write** | Write both old and new format | Transition period |

### Migration Function

```python
def migrate_design_v1_to_v2(old_state: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate v1.x design state to v2.0 primitives-based schema."""
    new_state = {
        "schema_version": "2.0.0",
        "resources": {
            "bodies": {},
            "sections": {},
            "surfaces": {},
            "discontinuities": {},
            "flow_paths": {},
            "openings": {},
            "attachments": {},
        },
        "computed": {},
        "constraints": [],
        "metadata": {
            "migrated_from": old_state.get("version", "1.0.0"),
            "migration_timestamp": datetime.utcnow().isoformat(),
        }
    }
    
    # Step 1: Convert hull_type to bodies
    hull = old_state.get("hull", {})
    hull_type = hull.get("hull_type", "monohull")
    bodies = _convert_hull_type_to_bodies(hull_type, hull)
    new_state["resources"]["bodies"] = bodies
    
    # Step 2: Convert features to discontinuities
    spray_rails = hull.get("spray_rails", [])
    for i, rail in enumerate(spray_rails):
        disc_id = f"spray_rail_{i}"
        new_state["resources"]["discontinuities"][disc_id] = {
            "body_id": "main",
            "type": "longitudinal_rail",
            "start_station": rail.get("start_station", 0.2),
            "end_station": rail.get("end_station", 0.9),
            "profile": "triangular",
            "height_m": rail.get("height_ratio", 0.5) * hull.get("draft", 1.0),
        }
    
    # Step 3: Preserve computed parameters
    new_state["computed"] = {
        "loa_m": hull.get("loa"),
        "lwl_m": hull.get("lwl"),
        "beam_m": hull.get("beam"),
        "draft_m": hull.get("draft"),
    }
    
    return new_state


def _convert_hull_type_to_bodies(hull_type: str, hull_params: Dict) -> Dict[str, Dict]:
    """
    Convert HullType enum to geometry.body primitives.
    
    ⚠️  MIGRATION ONLY — DO NOT COPY THIS PATTERN  ⚠️
    
    This function exists SOLELY for one-time migration of legacy designs
    that used the old HullType enum. It contains hardcoded type→geometry
    mappings that violate the "no design knowledge in kernel" principle.
    
    NEW DESIGNS MUST:
    - Use geometry.body primitives directly
    - NOT reference this function
    - NOT use hull_type strings like "catamaran" or "trimaran"
    
    This code should be DELETED once all legacy designs are migrated.
    """
    hull_type_lower = hull_type.lower()
    spacing = hull_params.get("hull_spacing_m", 4.0)
    
    if hull_type_lower in ("monohull", "planing", "displacement"):
        return {
            "main": {
                "body_type": hull_type_lower,
                "physics_category": "surface_piercing",
                "offset_y_m": 0,
            }
        }
    
    elif hull_type_lower == "catamaran":
        return {
            "hull_port": {
                "body_type": "demihull",
                "physics_category": "surface_piercing",
                "offset_y_m": -spacing / 2,
            },
            "hull_stbd": {
                "body_type": "demihull",
                "physics_category": "surface_piercing",
                "offset_y_m": spacing / 2,
            }
        }
    
    elif hull_type_lower == "trimaran":
        main_beam = hull_params.get("beam", 3.0)
        outrigger_offset = spacing + main_beam / 2
        return {
            "main": {"body_type": "main_hull", "physics_category": "surface_piercing", "offset_y_m": 0},
            "outrigger_port": {"body_type": "outrigger_ama", "physics_category": "surface_piercing", "offset_y_m": -outrigger_offset},
            "outrigger_stbd": {"body_type": "outrigger_ama", "physics_category": "surface_piercing", "offset_y_m": outrigger_offset}
        }
    
    elif hull_type_lower == "swath":
        return {
            "hull_port": {"body_type": "swath_lower_hull", "physics_category": "submerged", "offset_y_m": -spacing / 2},
            "hull_stbd": {"body_type": "swath_lower_hull", "physics_category": "submerged", "offset_y_m": spacing / 2}
        }
    
    else:
        return {"main": {"body_type": hull_type_lower, "physics_category": "surface_piercing", "offset_y_m": 0}}
```

---

## 4.3 Default Values

### Missing Field Defaults

| Field | Default Value | Rationale |
|:------|:--------------|:----------|
| `body_type` | `"generic_hull"` | Safe generic |
| `physics_category` | `"surface_piercing"` | Most common |
| `offset_x_m` | `0.0` | Center of reference |
| `offset_y_m` | `0.0` | Centerline |
| `offset_z_m` | `0.0` | Baseline |
| `start_station` | `0.0` | Full length |
| `end_station` | `1.0` | Full length |

### Section Generation

If no sections exist in v1 design, generate default sections:

```python
def generate_default_sections(body_id: str, hull_params: Dict, num_sections: int = 11) -> Dict[str, Dict]:
    """Generate default sections from hull parameters."""
    from magnet.hull_gen.generator import HullGenerator
    
    generator = HullGenerator()
    geometry = generator.generate(
        loa=hull_params.get("loa", 15.0),
        lwl=hull_params.get("lwl", 14.0),
        beam=hull_params.get("beam", 4.0),
        draft=hull_params.get("draft", 1.2),
    )
    
    sections = {}
    for i, section in enumerate(geometry.sections):
        section_id = f"{body_id}_sec_{i}"
        sections[section_id] = {
            "body_id": body_id,
            "station_fraction": section.station / hull_params.get("lwl", 14.0),
            "points": [[p.y, p.z] for p in section.points],
        }
    
    return sections
```

---

## 4.4 Backward Compatibility

### Dual-Schema Support Period

```python
class StateManager:
    def load(self, design_id: str) -> Dict[str, Any]:
        """Load design, auto-migrating if needed."""
        raw_state = self._storage.load(design_id)
        schema_version = raw_state.get("schema_version", "1.0.0")
        
        if schema_version.startswith("1."):
            migrated = migrate_design_v1_to_v2(raw_state)
            if self._config.persist_migrations:
                self._storage.save(design_id, migrated)
            return migrated
        
        return raw_state
    
    def save(self, design_id: str, state: Dict[str, Any]) -> None:
        """Save design in v2 format."""
        state["schema_version"] = "2.0.0"
        
        if self._config.dual_write:
            v1_state = convert_v2_to_v1(state)
            self._storage.save(f"{design_id}_v1", v1_state)
        
        self._storage.save(design_id, state)
```

### API Compatibility Layer

```python
@app.post("/hull/set_type")
async def set_hull_type(design_id: str, hull_type: str):
    """
    DEPRECATED: Use POST /program with geometry.body primitives.
    """
    warnings.warn("set_hull_type is deprecated", DeprecationWarning)
    
    bodies = _convert_hull_type_to_bodies(hull_type, {})
    program = {
        "program_id": f"compat_{uuid.uuid4().hex[:8]}",
        "version": 1,
        "operations": [
            {"op": "CREATE", "type": "geometry.body", "id": body_id, "params": params}
            for body_id, params in bodies.items()
        ]
    }
    return await execute_program(design_id, program)
```

---

## 4.5 Migration Validation

### Validation Checks

```python
def validate_migration(old_state: Dict, new_state: Dict) -> ValidationResult:
    """Validate that migration preserved design intent."""
    errors = []
    warnings = []
    
    # Check 1: Bodies were created (at least one)
    new_bodies = new_state.get("resources", {}).get("bodies", {})
    if len(new_bodies) == 0:
        errors.append("Migration produced no bodies")
    
    # Note: We do NOT validate expected body count from hull_type.
    # That would be enumeration. Any body count is valid.
    
    # Check 2: Computed values preserved
    old_loa = old_state.get("hull", {}).get("loa")
    new_loa = new_state.get("computed", {}).get("loa_m")
    if old_loa and new_loa and abs(old_loa - new_loa) > 0.001:
        errors.append(f"LOA mismatch: {old_loa} → {new_loa}")
    
    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
```

### Migration Tests

```python
@pytest.mark.migration
def test_legacy_dual_body_migration():
    """Legacy hull_type enum converts to body primitives."""
    old_state = {
        "version": "1.19.0",
        "hull": {"hull_type": "catamaran", "loa": 15.0, "hull_spacing_m": 5.0}  # Legacy format
    }
    
    new_state = migrate_design_v1_to_v2(old_state)
    
    bodies = new_state["resources"]["bodies"]
    assert len(bodies) == 2
    
    offsets = [b["offset_y_m"] for b in bodies.values()]
    assert -2.5 in offsets and 2.5 in offsets


@pytest.mark.migration
def test_features_become_discontinuities():
    """Spray rails become discontinuities."""
    old_state = {
        "hull": {
            "hull_type": "planing",
            "draft": 0.5,
            "spray_rails": [{"start_station": 0.2}, {"start_station": 0.3}]
        }
    }
    
    new_state = migrate_design_v1_to_v2(old_state)
    discs = new_state["resources"]["discontinuities"]
    assert len(discs) >= 2
```

---

## 4.6 Rollback Strategy

### V2 → V1 Conversion

For emergency rollback:

```python
def convert_v2_to_v1(new_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert v2.0 state back to v1.x format.
    WARNING: v1 format is limited. Novel configurations become "custom_N_body".
    """
    old_state = {"version": "1.19.0", "hull": {}, "mission": {}}
    
    # Preserve body count without inferring design classification
    # Do NOT map body_count → hull_type names (that's enumeration)
    bodies = new_state.get("resources", {}).get("bodies", {})
    body_count = len(bodies)
    
    # Use generic descriptive name, not design classification
    old_state["hull"]["hull_type"] = f"custom_{body_count}_body"
    old_state["hull"]["body_count"] = body_count  # Preserve actual count
    
    # Restore computed values
    computed = new_state.get("computed", {})
    old_state["hull"]["loa"] = computed.get("loa_m")
    old_state["hull"]["beam"] = computed.get("beam_m")
    old_state["hull"]["draft"] = computed.get("draft_m")
    
    return old_state
```

---

# Implementation Checklist

## Files to Create

| File | Purpose | Priority |
|:-----|:--------|:---------|
| `magnet/agents/prompts/intent_decomposer.py` | Intent decomposer prompt | P0 |
| `magnet/agents/prompts/geometry_proposer.py` | Geometry proposer prompt | P0 |
| `magnet/agents/prompts/critic.py` | Critic agent prompt | P1 |
| `magnet/agents/prompts/refinement.py` | Refinement agent prompt | P1 |
| `magnet/agents/prompts/merge.py` | Merge agent prompt | P2 |
| `magnet/agents/orchestrator.py` | Agent sequencing logic | P0 |
| `magnet/agents/state_injector.py` | State formatting for prompts | P0 |
| `magnet/agents/output_validator.py` | Schema validation | P0 |
| `magnet/core/migration.py` | v1→v2 migration function | P0 |
| `tests/migration/test_migration.py` | Migration tests | P0 |

## Integration Points

```
magnet/agents/prompts/*.py ──────▶ magnet/agents/orchestrator.py
                                            │
magnet/core/state_manager.py ───────────────┤
                                            │
magnet/kernel/validator.py ─────────────────┤
                                            │
magnet/deployment/api.py ◀──────────────────┘
```

---

# Related Documents

| Document | Purpose |
|:---------|:--------|
| `MAGNET_Design_Language_Spec_v1.0.md` | Language primitives and compilation |
| `MAGNET_Unified_Implementation_Plan.md` | Overall architecture and roadmap |
| `MAGNET_Failure_Modes_And_Mitigations.md` | Robustness strategies |
| `MAGNET_Audit_Prompts.md` | Codebase audit results |
| `MAGNET_Physics_Gaps_And_Solutions.md` | **CRITICAL:** Multi-body hydrostatics, resistance method selection, novelty detection |
| `MAGNET_Hard_Questions_Answers.md` | Reality check: codebase verification, LLM config, costs, milestones |
| `MAGNET_Implementation_Guide.md` | **START HERE:** Step-by-step implementation roadmap with code |

---

## Version History

| Version | Date | Changes |
|:--------|:-----|:--------|
| 1.0 | 2026-01-05 | Initial unified specification (Agent Prompt Spec, API Contract, Test Plan) |
| 1.1 | 2026-01-05 | Added Part 4: Migration Specification |
| 1.2 | 2026-01-05 | **Critical fix:** Removed all closed enums. physics_category, body_type, attachment_type now freeform. Removed design→geometry lookup tables. Migration uses generic body counts. |
| 1.3 | 2026-01-05 | Added reference to `MAGNET_Physics_Gaps_And_Solutions.md` for multi-body physics extensions |
| 1.4 | 2026-01-05 | **MIGRATION WARNING**: Added explicit "MIGRATION ONLY — DO NOT COPY" warning to `_convert_hull_type_to_bodies()` function documenting that it violates the "no design knowledge in kernel" principle and exists solely for legacy data conversion |

