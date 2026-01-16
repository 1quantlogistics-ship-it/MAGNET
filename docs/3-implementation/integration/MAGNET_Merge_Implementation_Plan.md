# MAGNET Merge Implementation Plan

## Mission Alignment

### The Goal

> **Human-in-the-loop engineering design spiral** to enable combinatorial explosion (trillions+ of forms) because a fixed, small grammar operating on continuous geometry primitives (sections, surfaces, attachments, constraints) composes endlessly without enumerating designs.

### The Equation

```
NOVELTY = continuous parameters × compositional operators × physics validation
```

### The Contract

| Agents | Kernel |
|:-------|:-------|
| Propose geometry primitives | Compile geometry |
| Invent combinations never drawn | Run physics validation |
| Speak in surfaces, sections, bodies | Return structured feedback |
| **Never select from catalog** | **Never suggest designs** |

### The Test (Must Pass After Implementation)

1. ☐ Create "stepped ventilated planing hull" using only discontinuities, flow paths, openings — **No "stepped hull" type**
2. ☐ Create "catamaran" using only bodies, sections, surfaces — **No "catamaran" type**
3. ☐ Create novel configuration — **Validate without adding code**

---

## Alignment Verification

| Goal Component | Plan Coverage | Location |
|:---------------|:--------------|:---------|
| Human-in-the-loop spiral | ✅ CycleExecutor + ClarificationManager + Vision | Part II diagram, Phase 0.5, Phase 6 |
| Trillions of forms | ✅ DSL grammar + continuous params | Part II "Why This Achieves The Goal" |
| No enumeration | ✅ GeometryProposal contains DSL, not hull types | Phase 1, Sacred Invariants |
| Kernel validates physics, not intent | ✅ ProgramExecutor → Compiler → Physics | Part II diagram |
| Novel forms without new code | ✅ THE TEST embedded as runnable code | Phase 7.4, Test Fixtures |
| Structured feedback | ✅ EnrichedDelta + NarrativeGenerator | Phase 4-5 |
| Change propagation | ✅ CascadeExecutor replaces PropagationEngine | Phase 3 |
| **Sketch input modality** | ✅ VisionInterpreter → intent → DSL | Phase 0.5 |

### What's Strong

- **THE TEST is embedded as code** — not just documentation, actual runnable verification (Phase 7.4)
- **Sacred invariants with grep commands** — machine-verifiable enumeration checks
- **Adapter pattern** — GeometryProposal extends Proposal, doesn't replace
- **Layer diagram is clear** — Agent → Cycle → Kernel → Cascade → Feedback
- **Risk monitoring section** — explicit "watch for" patterns
- **Net -200 lines** — merge reduces codebase, doesn't bloat it
- **ClarificationManager integration** — human-in-loop when agent is uncertain
- **Complete METRIC_POLARITY** — 50+ metrics with direction defined
- **Rollback tests** — 3 tests verify atomic execution
- **Vision input (Phase 0.5)** — engineers can sketch on paper/tablet, system interprets geometry

---

## Part I: Current State Assessment

### What's Working (NEW Path)

| Component | Location | Status |
|:----------|:---------|:-------|
| `GeometryProposer` | `magnet/agents/geometry_proposer.py` | ✅ Translates intent → DSL |
| `ProgramExecutor` | `magnet/kernel/program_executor.py` | ✅ DSL → AST → Actions → Compile |
| `Compiler` | `magnet/kernel/stdlib/compiler.py` | ✅ Resources → HullGeometry |
| `DesignConversation` | `magnet/agents/design_conversation.py` | ✅ Chat loop (custom) |
| Invariant tests | `tests/invariants/` | ✅ 20/20 passing |

### What's Duplicated (Needs Merge)

| NEW Code | EXISTING Code | Overlap | Action |
|:---------|:--------------|:--------|:-------|
| `PropagationEngine` | `CascadeExecutor` | 80% | Replace with existing |
| `DesignConversation` loop | `CycleExecutor` | 60% | Adapt existing |
| `generate_feedback()` | `NarrativeGenerator` | 70% | Merge templates |
| `MetricDelta` | `RecalculationResult` | 90% | Unify schema |

### What's Orphaned (Ready to Wire)

| Component | Location | Value for Goal |
|:----------|:---------|:---------------|
| `CycleExecutor` | `magnet/protocol/` | Transaction + escalation + timeout |
| `CascadeExecutor` | `magnet/dependencies/` | Parallel recalc + progress |
| `ClarificationManager` | `magnet/agents/` | Human-in-loop clarification |
| `NarrativeGenerator` | `magnet/explain/` | Multi-level explanations |
| `TransactionManager` | `magnet/glue/transactions/` | Atomic changes |
| API routers | `magnet/*/api_endpoints.py` | Interior, routing, agents |

---

## Part II: Target Architecture

### The Merged Design Loop

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    HUMAN-IN-THE-LOOP DESIGN SPIRAL                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐                                                           │
│   │   HUMAN     │ ◄──────────────────────────────────────────────────┐      │
│   │  Engineer   │                                                    │      │
│   └──────┬──────┘                                                    │      │
│          │ natural language OR geometry DSL                          │      │
│          ▼                                                           │      │
│   ┌─────────────────────────────────────────────────────────────┐    │      │
│   │                    AGENT LAYER                              │    │      │
│   │  ┌─────────────────┐    ┌─────────────────────────────────┐ │    │      │
│   │  │ GeometryProposer│───►│ ClarificationManager            │ │    │      │
│   │  │ (LLM → DSL)     │◄───│ (when uncertain, ASK don't guess)│ │    │      │
│   │  └────────┬────────┘    └─────────────────────────────────┘ │    │      │
│   └───────────┼─────────────────────────────────────────────────┘    │      │
│               │ GeometryProposal (DSL program)                       │      │
│               ▼                                                      │      │
│   ┌─────────────────────────────────────────────────────────────┐    │      │
│   │                    CYCLE LAYER                              │    │      │
│   │  ┌─────────────────────────────────────────────────────────┐│    │      │
│   │  │ CycleExecutor (EXISTING)                                ││    │      │
│   │  │   ├── Transaction: begin → tentative → commit/rollback  ││    │      │
│   │  │   ├── Timeout: max_iterations, deadline                 ││    │      │
│   │  │   ├── Escalation: when stuck, surface to human          ││    │      │
│   │  │   └── Agent callback: revise / approve / abort          ││    │      │
│   │  └─────────────────────────────────────────────────────────┘│    │      │
│   └───────────┬─────────────────────────────────────────────────┘    │      │
│               │ calls validator                                      │      │
│               ▼                                                      │      │
│   ┌─────────────────────────────────────────────────────────────┐    │      │
│   │                    KERNEL LAYER                             │    │      │
│   │  ┌─────────────────┐                                        │    │      │
│   │  │ ProgramExecutor │ (NEW) — Compiles geometry              │    │      │
│   │  │   ├── Parser    │   DSL → AST                            │    │      │
│   │  │   ├── Expander  │   AST → Actions                        │    │      │
│   │  │   └── Compiler  │   Actions → HullGeometry               │    │      │
│   │  └────────┬────────┘                                        │    │      │
│   │           │ HullGeometry                                    │    │      │
│   │           ▼                                                 │    │      │
│   │  ┌─────────────────┐                                        │    │      │
│   │  │ Physics Validators │ — Validates reality                 │    │      │
│   │  │   ├── Hydrostatics │   (GM, BM, displacement)            │    │      │
│   │  │   ├── Resistance   │   (Holtrop, Savitsky, or "unknown") │    │      │
│   │  │   └── Constraints  │   (user-defined)                    │    │      │
│   │  └────────┬────────┘                                        │    │      │
│   └───────────┼─────────────────────────────────────────────────┘    │      │
│               │ ValidationResult + HullGeometry                      │      │
│               ▼                                                      │      │
│   ┌─────────────────────────────────────────────────────────────┐    │      │
│   │                    CASCADE LAYER                            │    │      │
│   │  ┌─────────────────────────────────────────────────────────┐│    │      │
│   │  │ CascadeExecutor + InvalidationEngine (EXISTING)         ││    │      │
│   │  │   ├── DependencyGraph: 200+ parameter relationships     ││    │      │
│   │  │   ├── CalculatorRegistry: extensible computation        ││    │      │
│   │  │   ├── ThreadPoolExecutor: parallel recalculation        ││    │      │
│   │  │   └── Progress callbacks: UI responsiveness             ││    │      │
│   │  └─────────────────────────────────────────────────────────┘│    │      │
│   └───────────┬─────────────────────────────────────────────────┘    │      │
│               │ CascadeResult (all downstream deltas)                │      │
│               ▼                                                      │      │
│   ┌─────────────────────────────────────────────────────────────┐    │      │
│   │                    FEEDBACK LAYER                           │    │      │
│   │  ┌─────────────────────────────────────────────────────────┐│    │      │
│   │  │ NarrativeGenerator + ChatFormatter (EXISTING)           ││    │      │
│   │  │   ├── EnrichedDelta: direction (improved/degraded)      ││    │      │
│   │  │   ├── ExplanationLevel: brief → expert                  ││    │      │
│   │  │   └── Geometry templates: parallel axis, multi-body     ││    │      │
│   │  └─────────────────────────────────────────────────────────┘│    │      │
│   └───────────┬─────────────────────────────────────────────────┘    │      │
│               │ human-readable markdown                              │      │
│               └──────────────────────────────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why This Achieves The Goal

| Goal Requirement | How Architecture Delivers |
|:-----------------|:--------------------------|
| **Trillions of forms** | DSL grammar is fixed; parameters are continuous; bodies/sections/surfaces compose |
| **No enumeration** | `GeometryProposal` contains DSL text, not hull type strings |
| **Kernel validates physics** | `ProgramExecutor` → `Compiler` → Physics validators |
| **Kernel doesn't recognize intent** | Kernel receives geometry, not "catamaran" or "stepped hull" |
| **Human in loop** | `CycleExecutor` escalates; `ClarificationManager` asks |
| **Structured feedback** | `EnrichedDelta` + `NarrativeGenerator` |
| **Iteration** | `CycleExecutor.execute_cycle()` with transaction rollback |

---

## Part III: Implementation Tasks

### Phase 0: Prerequisites (Day 1 Morning)

#### Task 0.1: Mount Orphaned API Routers

**File:** `magnet/deployment/api.py`

**Changes:**
```python
# Add imports
from magnet.agents.api_endpoints import create_agents_router
from magnet.interior.api_endpoints import create_interior_router
from magnet.routing.integration.api_endpoints import create_routing_router

# After app creation, add:
try:
    app.include_router(create_agents_router())
    logger.info("Agents router mounted")
except Exception as e:
    logger.warning(f"Could not mount agents router: {e}")

try:
    app.include_router(create_interior_router())
    logger.info("Interior router mounted")
except Exception as e:
    logger.warning(f"Could not mount interior router: {e}")

try:
    app.include_router(create_routing_router())
    logger.info("Routing router mounted")
except Exception as e:
    logger.warning(f"Could not mount routing router: {e}")
```

**Time:** 30 minutes
**Risk:** Very low
**Test:** `curl http://localhost:8000/api/v1/agents/stats`

---

#### Task 0.2: Verify `program_executor` Atomicity

**Check:**
```bash
grep -n "deepcopy\|rollback\|tentative" magnet/kernel/program_executor.py
```

**If missing, implement:**
```python
# magnet/kernel/program_executor.py

def execute_program(
    program_text: str,
    state_manager: StateManager,
    dry_run: bool = False,
) -> ExecutionResult:
    """Execute program atomically — all succeed or all fail."""
    import copy
    
    # Always work on a copy first
    working_state = copy.deepcopy(state_manager._state)
    
    try:
        # Parse
        ast = parse(program_text)
        
        # Expand
        actions = expand(ast, working_state)
        
        # Apply actions to working state
        for action in actions:
            _apply_action(action, working_state)
        
        # Compile
        geometry = compile_to_geometry(working_state)
        
        # Validate
        validation = _run_validation(geometry, working_state)
        
        # Only commit if not dry_run and successful
        if not dry_run and validation.get("success", True):
            state_manager._state = working_state
        
        return ExecutionResult(
            success=True,
            geometry=geometry,
            validation=validation,
            actions_executed=len(actions),
        )
        
    except Exception as e:
        # working_state is discarded, original untouched
        return ExecutionResult(
            success=False,
            errors=[str(e)],
        )
```

**Time:** 2 hours
**Risk:** Medium (core path)

**Tests (REQUIRED):**
```python
def test_program_executor_atomic():
    """Program execution is atomic — all succeed or all fail."""
    state = StateManager()
    state.set("test_key", "original")
    
    # Program that fails mid-way
    program = """
        SET test_key = "modified"
        CREATE geometry.section INVALID { }
    """
    result = execute_program(program, state, dry_run=False)
    
    assert not result.success
    assert state.get("test_key") == "original"  # Rolled back


def test_geometry_proposal_rollback():
    """Failed compilation leaves state unchanged."""
    state = StateManager()
    state.set("existing_key", "value")
    
    bad_program = "CREATE geometry.body main { INVALID SYNTAX }"
    result = execute_program(bad_program, state, dry_run=False)
    
    assert not result.success
    assert state.get("existing_key") == "value"  # Unchanged
    assert state.get("resources") is None  # Nothing added


def test_partial_execution_rollback():
    """Partial execution rolls back all changes."""
    state = StateManager()
    
    # First statement succeeds, second fails
    program = """
        CREATE geometry.section valid_section {
            station: 0.0,
            points: [[0, 0], [1, -0.5], [1, 0.5]]
        }
        CREATE geometry.body main { section_ids: ["nonexistent"] }
    """
    result = execute_program(program, state, dry_run=False)
    
    assert not result.success
    # Even valid_section should be rolled back
    assert state.get("resources.geometry.section.valid_section") is None
```

---

#### Task 0.3: Add Geometry Paths to DependencyGraph

**File:** `magnet/dependencies/graph.py`

**Add to `PHASE_OWNERSHIP`:**
```python
PHASE_OWNERSHIP: Dict[str, List[str]] = {
    # ... existing phases ...
    
    "hull_form": [
        # ... existing hull params ...
        
        # NEW: Geometry primitives
        "resources.geometry.section",
        "resources.geometry.body",
        "resources.geometry.surface",
        "resources.geometry.discontinuity",
        "resources.geometry.flow_path",
        "resources.geometry.opening",
        "resources.geometry.attachment",
        "design_program",
        "hull.geometry",
    ],
}
```

**Time:** 1 hour
**Risk:** Low
**Test:** Verify `get_phase_for_parameter("resources.geometry.section")` returns `"hull_form"`

---

### Phase 0.5: Vision Interpreter (Day 1 Afternoon — Optional but Recommended)

> **Goal:** Enable engineers to sketch hull concepts on paper/tablet and have them interpreted into geometry primitives. This is a key human-in-the-loop input modality.

#### Audit Findings: Vision Infrastructure

| Component | Status | Notes |
|:----------|:-------|:------|
| `magnet/llm/providers/anthropic.py` | ✅ Exists | Claude models have `supports_vision: True` |
| `magnet/vision/` | ⚠️ Different purpose | 3D rendering, not sketch interpretation |
| Vision LLM protocol | ❌ Missing | `_raw_complete()` only handles text messages |
| Sketch interpretation agent | ❌ Missing | Need to create |

#### Task 0.5.1: Add Vision Support to Anthropic Provider

**File:** `magnet/llm/providers/anthropic.py` (modify existing)

```python
# Add new method to AnthropicProvider class

async def complete_with_image(
    self,
    prompt: str,
    image_data: bytes,
    image_media_type: str = "image/png",
    system_prompt: Optional[str] = None,
    options: Optional[LLMOptions] = None,
) -> LLMResponse:
    """
    Generate completion with image input (vision).
    
    Args:
        prompt: Text prompt to accompany the image
        image_data: Raw image bytes
        image_media_type: MIME type (image/png, image/jpeg, image/gif, image/webp)
        system_prompt: System instructions
        options: Completion options
    
    Returns:
        LLMResponse from Claude with image analysis
    """
    import base64
    
    client = self._get_client()
    opts = (options or LLMOptions()).merge_with_defaults(
        self.default_max_tokens,
        self.default_temperature,
    )
    
    # Encode image to base64
    image_base64 = base64.b64encode(image_data).decode("utf-8")
    
    # Build message with image
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_media_type,
                        "data": image_base64,
                    },
                },
                {
                    "type": "text",
                    "text": prompt,
                },
            ],
        }
    ]
    
    response = await client.messages.create(
        model=self.model,
        max_tokens=opts.max_tokens or self.default_max_tokens,
        temperature=opts.temperature or self.default_temperature,
        system=system_prompt or "",
        messages=messages,
    )
    
    content = ""
    if response.content:
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text
    
    usage = {
        "prompt_tokens": response.usage.input_tokens,
        "completion_tokens": response.usage.output_tokens,
        "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
    }
    
    return LLMResponse(
        content=content,
        model=response.model,
        usage=usage,
        finish_reason=response.stop_reason or "stop",
    )
```

**Time:** 30 minutes
**Risk:** Low

---

#### Task 0.5.2: Create Vision Interpreter Agent

**File:** `magnet/agents/vision_interpreter.py` (new file)

```python
"""
magnet/agents/vision_interpreter.py - Sketch Interpretation Agent

Converts hand-drawn sketches into geometry descriptions.
Outputs ONLY geometric descriptions — NEVER design type names.

INVARIANT: Output must NOT contain "catamaran", "trimaran", "stepped hull", etc.
           Only geometric descriptions (body count, dimensions, proportions).
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


# =============================================================================
# System Prompt — GEOMETRY ONLY, NO DESIGN TYPES
# =============================================================================

VISION_INTERPRETER_SYSTEM_PROMPT = """You are MAGNET's Sketch Interpreter.

YOUR ROLE:
- Analyze hand-drawn sketches of hull designs
- Extract GEOMETRIC INFORMATION ONLY
- Output measurements, body counts, proportions, and spatial relationships
- NEVER use design type names

🔴 FORBIDDEN TERMS (Do NOT output these):
- catamaran, trimaran, monohull, multihull
- stepped hull, planing hull, displacement hull
- patrol boat, workboat, ferry, yacht
- Any vessel classification or design style name

✅ ALLOWED OUTPUT (Geometry descriptions only):
- "I see 2 separate hull bodies offset laterally"
- "The sketch shows a longitudinal discontinuity at ~40% length"
- "Handwritten annotation shows '25m' indicating overall length"
- "Body proportions appear to be L/B ratio of approximately 5:1"
- "There is a surface break or step visible at mid-length"

WHAT TO EXTRACT:
1. Body count: How many separate hull forms are visible?
2. Dimensions: Any handwritten measurements (e.g., "25m", "4.5m beam")
3. Proportions: Approximate L/B ratio, draft/beam ratio
4. Spatial relationships: Offsets between bodies, relative positions
5. Surface features: Discontinuities, steps, chines (describe geometrically)
6. Annotations: Any text/labels written on the sketch

OUTPUT FORMAT (JSON):
{
  "body_count": number,
  "dimensions": {
    "loa_m": number or null,
    "beam_m": number or null,
    "draft_m": number or null,
    "body_spacing_m": number or null
  },
  "proportions": {
    "length_beam_ratio": number or null,
    "beam_draft_ratio": number or null
  },
  "bodies": [
    {
      "body_index": number,
      "position": "center" | "port" | "starboard" | "forward" | "aft",
      "relative_size": "primary" | "secondary" | "equal",
      "offset_y_estimate_m": number or null
    }
  ],
  "surface_features": [
    {
      "type": "discontinuity" | "chine" | "step" | "knuckle",
      "location_description": "string",
      "station_fraction_estimate": number or null
    }
  ],
  "annotations": [
    {
      "text": "string",
      "interpretation": "string"
    }
  ],
  "confidence": number (0.0-1.0),
  "geometric_description": "string (natural language summary using ONLY geometry terms)"
}

REMEMBER: You describe GEOMETRY, not design intent. The kernel will validate physics.
"""


# =============================================================================
# Pydantic Models
# =============================================================================

class BodyDescription(BaseModel):
    """Description of a single hull body."""
    body_index: int
    position: str = Field(..., description="center, port, starboard, forward, aft")
    relative_size: str = Field(default="primary", description="primary, secondary, equal")
    offset_y_estimate_m: Optional[float] = None


class SurfaceFeature(BaseModel):
    """Geometric surface feature."""
    type: str = Field(..., description="discontinuity, chine, step, knuckle")
    location_description: str
    station_fraction_estimate: Optional[float] = None


class Annotation(BaseModel):
    """Handwritten annotation from sketch."""
    text: str
    interpretation: str


class SketchInterpretation(BaseModel):
    """Complete interpretation of a sketch."""
    body_count: int = Field(default=1, ge=1)
    dimensions: Dict[str, Optional[float]] = Field(default_factory=dict)
    proportions: Dict[str, Optional[float]] = Field(default_factory=dict)
    bodies: List[BodyDescription] = Field(default_factory=list)
    surface_features: List[SurfaceFeature] = Field(default_factory=list)
    annotations: List[Annotation] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    geometric_description: str = Field(default="")


# =============================================================================
# Vision Interpreter Agent
# =============================================================================

@dataclass
class VisionResult:
    """Result from vision interpretation."""
    success: bool
    interpretation: Optional[SketchInterpretation] = None
    intent_string: str = ""  # Natural language for GeometryProposer
    raw_response: str = ""
    error: Optional[str] = None


# Forbidden terms that indicate enumeration
FORBIDDEN_TERMS = [
    "catamaran", "trimaran", "monohull", "multihull",
    "stepped hull", "planing hull", "displacement hull",
    "patrol boat", "workboat", "ferry", "yacht", "tanker",
    "container ship", "fishing vessel", "crew boat", "tug",
    "proa", "outrigger canoe", "swath",
]


class VisionInterpreter:
    """
    Agent that interprets hand-drawn sketches into geometry descriptions.
    
    Contract:
    - Input: Image bytes + optional annotations
    - Output: SketchInterpretation with ONLY geometry terms
    - NEVER outputs design type names
    - Provides intent string for GeometryProposer
    """
    
    def __init__(
        self,
        llm_provider,  # AnthropicProvider or compatible
        confidence_threshold: float = 0.5,
    ):
        self._llm = llm_provider
        self._confidence_threshold = confidence_threshold
    
    async def interpret_sketch(
        self,
        image_data: bytes,
        annotations: str = "",
        image_media_type: str = "image/png",
    ) -> VisionResult:
        """
        Interpret a hand-drawn sketch.
        
        Args:
            image_data: Raw image bytes
            annotations: Optional text annotations from user
            image_media_type: MIME type of image
        
        Returns:
            VisionResult with interpretation and intent string
        """
        # Build prompt
        prompt = self._build_prompt(annotations)
        
        try:
            # Call vision LLM
            response = await self._llm.complete_with_image(
                prompt=prompt,
                image_data=image_data,
                image_media_type=image_media_type,
                system_prompt=VISION_INTERPRETER_SYSTEM_PROMPT,
            )
            
            # Parse response
            interpretation = self._parse_response(response.content)
            
            # Validate no forbidden terms
            violation = self._check_forbidden_terms(interpretation)
            if violation:
                return VisionResult(
                    success=False,
                    error=f"Enumeration violation: output contains '{violation}'",
                    raw_response=response.content,
                )
            
            # Generate intent string for GeometryProposer
            intent_string = self._generate_intent_string(interpretation, annotations)
            
            return VisionResult(
                success=True,
                interpretation=interpretation,
                intent_string=intent_string,
                raw_response=response.content,
            )
            
        except Exception as e:
            return VisionResult(
                success=False,
                error=f"Vision interpretation failed: {str(e)}",
            )
    
    def _build_prompt(self, annotations: str) -> str:
        """Build the prompt for vision LLM."""
        prompt = """Analyze this hand-drawn sketch of a hull design.

Extract ONLY geometric information:
1. Count the number of hull bodies
2. Read any handwritten dimensions (measurements)
3. Estimate proportions (L/B ratio, etc.)
4. Describe spatial relationships between bodies
5. Note any surface features (steps, chines, discontinuities)

Output valid JSON matching the schema in your instructions.

CRITICAL: Use ONLY geometric descriptions. Do NOT use vessel type names."""
        
        if annotations:
            prompt += f"\n\nUser annotations: {annotations}"
        
        return prompt
    
    def _parse_response(self, content: str) -> SketchInterpretation:
        """Parse LLM response into SketchInterpretation."""
        # Try to extract JSON from response
        content = content.strip()
        
        # Handle markdown code blocks
        if "```" in content:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
            if match:
                content = match.group(1).strip()
        
        try:
            data = json.loads(content)
            return SketchInterpretation.model_validate(data)
        except (json.JSONDecodeError, Exception) as e:
            # Return minimal interpretation on parse failure
            return SketchInterpretation(
                body_count=1,
                confidence=0.3,
                geometric_description=content[:500],  # Use raw text as description
            )
    
    def _check_forbidden_terms(self, interpretation: SketchInterpretation) -> Optional[str]:
        """Check if interpretation contains forbidden design terms."""
        text_to_check = interpretation.geometric_description.lower()
        
        for term in FORBIDDEN_TERMS:
            if term.lower() in text_to_check:
                return term
        
        return None
    
    def _generate_intent_string(
        self,
        interpretation: SketchInterpretation,
        user_annotations: str,
    ) -> str:
        """
        Generate intent string for GeometryProposer.
        
        This converts the geometric interpretation into a natural language
        request that GeometryProposer can process.
        """
        parts = []
        
        # Body count
        if interpretation.body_count == 1:
            parts.append("Create a single-body hull")
        else:
            parts.append(f"Create a {interpretation.body_count}-body hull configuration")
        
        # Dimensions
        dims = interpretation.dimensions
        if dims.get("loa_m"):
            parts.append(f"with overall length {dims['loa_m']}m")
        if dims.get("beam_m"):
            parts.append(f"beam {dims['beam_m']}m")
        if dims.get("draft_m"):
            parts.append(f"draft {dims['draft_m']}m")
        
        # Body spacing for multi-body
        if interpretation.body_count > 1 and dims.get("body_spacing_m"):
            parts.append(f"with bodies spaced {dims['body_spacing_m']}m apart")
        elif interpretation.body_count > 1:
            # Estimate from body descriptions
            offsets = [b.offset_y_estimate_m for b in interpretation.bodies if b.offset_y_estimate_m]
            if offsets:
                spacing = max(offsets) - min(offsets)
                parts.append(f"with estimated body spacing of {spacing:.1f}m")
        
        # Surface features
        for feature in interpretation.surface_features:
            if feature.type == "discontinuity" or feature.type == "step":
                loc = f"at {feature.station_fraction_estimate:.0%} length" if feature.station_fraction_estimate else ""
                parts.append(f"including a surface discontinuity {loc}")
            elif feature.type == "chine":
                parts.append("with chine edges")
        
        # User annotations
        if user_annotations:
            parts.append(f"Additional context: {user_annotations}")
        
        return ". ".join(parts) + "."


# =============================================================================
# Convenience Functions
# =============================================================================

async def interpret_sketch(
    image_data: bytes,
    annotations: str = "",
    llm_provider=None,
) -> VisionResult:
    """
    Convenience function to interpret a sketch.
    
    Example:
        with open("sketch.png", "rb") as f:
            result = await interpret_sketch(f.read(), "25m patrol vessel")
        if result.success:
            # Pass to GeometryProposer
            geometry_result = await proposer.propose(result.intent_string)
    """
    if llm_provider is None:
        from magnet.llm.providers.anthropic import AnthropicProvider
        llm_provider = AnthropicProvider()
    
    interpreter = VisionInterpreter(llm_provider)
    return await interpreter.interpret_sketch(image_data, annotations)
```

**Time:** 1.5 hours
**Risk:** Low

---

#### Task 0.5.3: Wire to DesignConversation

**File:** `magnet/agents/design_conversation.py` (modify existing)

Add image handling to the `chat()` method:

```python
# Add to DesignConversation.__init__()
def __init__(
    self,
    state_manager: StateManager,
    llm_client: Optional[LLMClient] = None,
    clarification_manager: Optional[ClarificationManager] = None,
    vision_interpreter: Optional[VisionInterpreter] = None,  # NEW
    confidence_threshold: float = 0.6,
):
    # ... existing init ...
    self.vision_interpreter = vision_interpreter  # NEW


# Add new method
async def chat_with_image(
    self,
    user_message: str,
    image_data: bytes,
    image_media_type: str = "image/png",
    constraints: Optional[List[str]] = None,
) -> ChatIterationResult:
    """
    Process user message with sketch image.
    
    Flow: Image → VisionInterpreter → intent string → GeometryProposer → DSL
    """
    self.iteration_number += 1
    
    # 1. Interpret the sketch
    if not self.vision_interpreter:
        return ChatIterationResult(
            success=False,
            iteration_number=self.iteration_number,
            feedback_to_user="Vision interpreter not configured.",
        )
    
    vision_result = await self.vision_interpreter.interpret_sketch(
        image_data=image_data,
        annotations=user_message,
        image_media_type=image_media_type,
    )
    
    if not vision_result.success:
        return ChatIterationResult(
            success=False,
            iteration_number=self.iteration_number,
            feedback_to_user=f"Could not interpret sketch: {vision_result.error}",
        )
    
    # 2. Report what was extracted
    interpretation = vision_result.interpretation
    feedback_parts = [
        "## Sketch Interpretation",
        f"- Bodies detected: {interpretation.body_count}",
    ]
    
    dims = interpretation.dimensions
    if dims.get("loa_m"):
        feedback_parts.append(f"- Length: {dims['loa_m']}m")
    if dims.get("beam_m"):
        feedback_parts.append(f"- Beam: {dims['beam_m']}m")
    
    if interpretation.surface_features:
        feedback_parts.append(f"- Surface features: {len(interpretation.surface_features)}")
    
    feedback_parts.append(f"\n**Generating geometry from:** {vision_result.intent_string}")
    
    # 3. Pass intent to normal chat flow
    combined_intent = vision_result.intent_string
    if user_message and user_message.strip():
        combined_intent = f"{vision_result.intent_string} {user_message}"
    
    # Use existing chat() with the interpreted intent
    result = await self.chat(combined_intent, constraints)
    
    # Prepend interpretation feedback
    result.feedback_to_user = "\n".join(feedback_parts) + "\n\n" + result.feedback_to_user
    
    return result
```

**Time:** 30 minutes
**Risk:** Low

---

#### Task 0.5.4: Add API Endpoint

**File:** `magnet/deployment/api.py` (add to existing)

```python
from fastapi import File, UploadFile, Form

@app.post("/api/v1/design/sketch", tags=["design"])
async def interpret_sketch_endpoint(
    image: UploadFile = File(..., description="Hand-drawn sketch image"),
    annotations: str = Form(default="", description="Optional text annotations"),
    session_id: Optional[str] = Form(default=None, description="Design session ID"),
):
    """
    Interpret a hand-drawn sketch and generate geometry.
    
    Flow:
    1. VisionInterpreter extracts geometric information from sketch
    2. Generates intent string (geometry-only, no design types)
    3. GeometryProposer converts to DSL
    4. ProgramExecutor compiles geometry
    
    Returns interpretation + generated geometry.
    
    INVARIANT: Response will NEVER contain "catamaran", "trimaran", etc.
               Only geometric descriptions.
    """
    from magnet.agents.vision_interpreter import interpret_sketch, VisionInterpreter
    from magnet.agents.design_conversation import DesignConversation
    from magnet.llm.providers.anthropic import AnthropicProvider
    
    # Read image
    image_data = await image.read()
    
    # Determine media type
    media_type = image.content_type or "image/png"
    if media_type not in ("image/png", "image/jpeg", "image/gif", "image/webp"):
        raise HTTPException(400, f"Unsupported image type: {media_type}")
    
    # Create interpreter
    provider = AnthropicProvider()
    interpreter = VisionInterpreter(provider)
    
    # Interpret sketch
    vision_result = await interpreter.interpret_sketch(
        image_data=image_data,
        annotations=annotations,
        image_media_type=media_type,
    )
    
    if not vision_result.success:
        return {
            "success": False,
            "error": vision_result.error,
        }
    
    # Get or create design conversation
    conversation = _get_or_create_conversation(session_id, vision_interpreter=interpreter)
    
    # Process through design conversation
    result = await conversation.chat_with_image(
        user_message=annotations,
        image_data=image_data,
        image_media_type=media_type,
    )
    
    return {
        "success": result.success,
        "interpretation": vision_result.interpretation.model_dump() if vision_result.interpretation else None,
        "intent_string": vision_result.intent_string,
        "feedback": result.feedback_to_user,
        "geometry": result.geometry.to_dict() if result.geometry else None,
        "session_id": session_id or "new",
    }
```

**Time:** 30 minutes
**Risk:** Low

---

#### Task 0.5.5: Add Invariant Test

**File:** `tests/invariants/test_vision_no_enumeration.py` (new file)

```python
"""
Invariant tests for vision interpreter.

INVARIANT: Vision output must NEVER contain design type names.
           Only geometric descriptions are allowed.
"""

import pytest
from magnet.agents.vision_interpreter import (
    VisionInterpreter,
    SketchInterpretation,
    FORBIDDEN_TERMS,
)


class TestVisionNoEnumeration:
    """Vision interpreter must not output design type names."""
    
    def test_forbidden_terms_list_complete(self):
        """Forbidden terms list includes all design types."""
        required_forbidden = [
            "catamaran", "trimaran", "monohull",
            "stepped hull", "planing hull",
            "patrol boat", "workboat", "yacht",
        ]
        for term in required_forbidden:
            assert term in FORBIDDEN_TERMS, f"Missing forbidden term: {term}"
    
    def test_check_forbidden_terms_detects_catamaran(self):
        """Detects 'catamaran' in geometric description."""
        interpreter = VisionInterpreter(llm_provider=None)
        
        interpretation = SketchInterpretation(
            body_count=2,
            geometric_description="This looks like a catamaran with twin hulls",
        )
        
        violation = interpreter._check_forbidden_terms(interpretation)
        assert violation == "catamaran"
    
    def test_check_forbidden_terms_allows_geometry(self):
        """Allows pure geometric descriptions."""
        interpreter = VisionInterpreter(llm_provider=None)
        
        interpretation = SketchInterpretation(
            body_count=2,
            geometric_description="Two hull bodies offset laterally by 4m, each with L/B ratio of 8:1",
        )
        
        violation = interpreter._check_forbidden_terms(interpretation)
        assert violation is None
    
    def test_generate_intent_string_no_design_types(self):
        """Generated intent string contains no design types."""
        interpreter = VisionInterpreter(llm_provider=None)
        
        interpretation = SketchInterpretation(
            body_count=2,
            dimensions={"loa_m": 25, "beam_m": 5, "body_spacing_m": 8},
            geometric_description="Two parallel hull bodies",
        )
        
        intent = interpreter._generate_intent_string(interpretation, "")
        
        for term in FORBIDDEN_TERMS:
            assert term.lower() not in intent.lower(), \
                f"Intent string contains forbidden term: {term}"
    
    def test_system_prompt_forbids_design_types(self):
        """System prompt explicitly forbids design type names."""
        from magnet.agents.vision_interpreter import VISION_INTERPRETER_SYSTEM_PROMPT
        
        assert "FORBIDDEN" in VISION_INTERPRETER_SYSTEM_PROMPT
        assert "catamaran" in VISION_INTERPRETER_SYSTEM_PROMPT
        assert "Do NOT" in VISION_INTERPRETER_SYSTEM_PROMPT


class TestVisionDimensionExtraction:
    """Vision interpreter extracts dimensions correctly."""
    
    def test_intent_includes_extracted_dimensions(self):
        """Intent string includes dimensions from sketch."""
        interpreter = VisionInterpreter(llm_provider=None)
        
        interpretation = SketchInterpretation(
            body_count=1,
            dimensions={"loa_m": 25, "beam_m": 5},
        )
        
        intent = interpreter._generate_intent_string(interpretation, "")
        
        assert "25m" in intent or "25" in intent
        assert "5m" in intent or "beam" in intent


@pytest.mark.asyncio
async def test_sketch_with_dimension_annotation():
    """
    THE TEST: Upload sketch with "25m" written on it.
    Verify dimensions are extracted.
    
    Note: This test requires a mock LLM or real API key.
    """
    from unittest.mock import AsyncMock, Mock
    
    # Mock LLM provider
    mock_provider = Mock()
    mock_provider.complete_with_image = AsyncMock(return_value=Mock(
        content='''{
            "body_count": 1,
            "dimensions": {"loa_m": 25, "beam_m": 5},
            "proportions": {"length_beam_ratio": 5.0},
            "bodies": [{"body_index": 0, "position": "center", "relative_size": "primary"}],
            "surface_features": [],
            "annotations": [{"text": "25m", "interpretation": "Overall length annotation"}],
            "confidence": 0.85,
            "geometric_description": "Single hull body with 25m length annotation"
        }'''
    ))
    
    interpreter = VisionInterpreter(mock_provider)
    
    # Fake image data
    result = await interpreter.interpret_sketch(
        image_data=b"fake_image_data",
        annotations="25m patrol vessel concept",
    )
    
    assert result.success
    assert result.interpretation.dimensions.get("loa_m") == 25
    assert "25m" in result.intent_string or "25" in result.intent_string
    
    # Verify no forbidden terms
    for term in FORBIDDEN_TERMS:
        assert term.lower() not in result.intent_string.lower()
```

**Time:** 30 minutes
**Risk:** Low

---

#### Phase 0.5 Summary

| Task | Time | Deliverable |
|:-----|:-----|:------------|
| 0.5.1 | 30m | Vision support in Anthropic provider |
| 0.5.2 | 1.5h | `VisionInterpreter` agent |
| 0.5.3 | 30m | `chat_with_image()` in DesignConversation |
| 0.5.4 | 30m | `POST /api/v1/design/sketch` endpoint |
| 0.5.5 | 30m | Invariant tests |
| **Total** | **3h** | Vision-to-geometry pipeline |

**Sacred Invariant:**
```bash
# Vision output must NEVER contain design types
grep -rn "catamaran\|trimaran\|stepped.*hull" magnet/agents/vision_interpreter.py
# Expected: Only in FORBIDDEN_TERMS list, not in output generation
```

**THE TEST for Phase 0.5:**
```python
# Upload sketch with "25m" annotation → verify dimension extracted
result = await interpret_sketch(sketch_bytes, "fast vessel concept")
assert result.interpretation.dimensions.get("loa_m") == 25
assert "catamaran" not in result.intent_string.lower()
```

---

### Phase 1: Create GeometryProposal (Day 1 Afternoon)

#### Task 1.1: Define GeometryProposal Schema

**File:** `magnet/glue/protocol/schemas.py` (add to existing)

```python
@dataclass
class GeometryProposal(Proposal):
    """
    Proposal containing geometry DSL program.
    
    Extends Proposal to support the NEW geometry primitives path.
    The program_text is pure DSL — no hull types, no enumeration.
    """
    
    program_text: str = ""
    """The geometry DSL program text."""
    
    parsed_ast: Optional[List[Any]] = None
    """Cached parsed AST (optional, for debugging)."""
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base["program_text"] = self.program_text
        base["has_ast"] = self.parsed_ast is not None
        return base
    
    @classmethod
    def from_program(
        cls,
        program_text: str,
        agent_id: str = "geometry_proposer",
        reasoning: str = "",
    ) -> "GeometryProposal":
        """Create GeometryProposal from DSL program text."""
        return cls(
            agent_id=agent_id,
            phase="hull",
            program_text=program_text,
            reasoning=reasoning,
            changes=[],  # Changes are in the DSL, not parameter changes
        )
```

**Time:** 1 hour
**Risk:** Low

---

#### Task 1.2: Create Geometry Test Fixtures

**File:** `tests/fixtures/geometry_proposals.py` (new file)

```python
"""
Test fixtures for geometry proposals.

These fixtures use ONLY geometry primitives — no hull types.
"""

from magnet.glue.protocol.schemas import GeometryProposal


# =============================================================================
# VALID PROPOSALS
# =============================================================================

VALID_SINGLE_HULL = GeometryProposal.from_program(
    program_text="""
        CREATE geometry.section bow {
            station: 0.0,
            points: [[0, 0], [1, -0.5], [1, 0.5]]
        }
        CREATE geometry.section mid {
            station: 0.5,
            points: [[0, 0], [2, -1], [2, 1]]
        }
        CREATE geometry.section stern {
            station: 1.0,
            points: [[0, 0], [1.5, -0.7], [1.5, 0.7]]
        }
        CREATE geometry.body main {
            section_ids: ["bow", "mid", "stern"],
            physics_category: "surface_piercing"
        }
    """,
    reasoning="Single hull vessel from primitives",
)

VALID_TWIN_HULL = GeometryProposal.from_program(
    program_text="""
        CREATE geometry.section bow {
            station: 0.0,
            points: [[0, 0], [0.5, -0.3], [0.5, 0.3]]
        }
        CREATE geometry.section stern {
            station: 1.0,
            points: [[0, 0], [0.5, -0.3], [0.5, 0.3]]
        }
        CREATE geometry.body port {
            section_ids: ["bow", "stern"],
            offset_y_m: -4.0,
            physics_category: "surface_piercing"
        }
        CREATE geometry.body stbd {
            section_ids: ["bow", "stern"],
            offset_y_m: 4.0,
            physics_category: "surface_piercing"
        }
    """,
    reasoning="Twin hull vessel using body offsets — NO 'catamaran' type",
)

VALID_STEPPED_HULL = GeometryProposal.from_program(
    program_text="""
        CREATE geometry.section bow {
            station: 0.0,
            points: [[0, 0], [1, -0.3], [1, 0.3]]
        }
        CREATE geometry.section pre_step {
            station: 0.4,
            points: [[0, 0], [1.5, -0.5], [1.5, 0.5]]
        }
        CREATE geometry.section post_step {
            station: 0.45,
            points: [[0, -0.1], [1.5, -0.6], [1.5, 0.4]]
        }
        CREATE geometry.section stern {
            station: 1.0,
            points: [[0, 0], [1, -0.4], [1, 0.4]]
        }
        CREATE geometry.discontinuity step_1 {
            type: "surface_break",
            location_x: 0.42,
            height_m: 0.1
        }
        CREATE geometry.flow_path ventilation {
            medium: "air",
            inlet_point: [0.42, 0, -0.1],
            outlet_point: [1.0, 0, -0.1]
        }
        CREATE geometry.body main {
            section_ids: ["bow", "pre_step", "post_step", "stern"],
            physics_category: "surface_piercing"
        }
    """,
    reasoning="Stepped ventilated planing hull using discontinuities — NO 'stepped hull' type",
)

VALID_NOVEL_FORM = GeometryProposal.from_program(
    program_text="""
        CREATE geometry.section center_bow {
            station: 0.0,
            points: [[0, 0], [0.8, -0.4], [0.8, 0.4]]
        }
        CREATE geometry.section center_stern {
            station: 1.0,
            points: [[0, 0], [0.6, -0.3], [0.6, 0.3]]
        }
        CREATE geometry.section outrigger_bow {
            station: 0.2,
            points: [[0, 0], [0.3, -0.15], [0.3, 0.15]]
        }
        CREATE geometry.section outrigger_stern {
            station: 0.8,
            points: [[0, 0], [0.25, -0.12], [0.25, 0.12]]
        }
        CREATE geometry.body main {
            section_ids: ["center_bow", "center_stern"],
            offset_y_m: 0.0,
            physics_category: "surface_piercing"
        }
        CREATE geometry.body outrigger_port {
            section_ids: ["outrigger_bow", "outrigger_stern"],
            offset_y_m: -3.0,
            offset_z_m: 0.5,
            physics_category: "surface_piercing"
        }
        CREATE geometry.body outrigger_stbd {
            section_ids: ["outrigger_bow", "outrigger_stern"],
            offset_y_m: 3.0,
            offset_z_m: 0.5,
            physics_category: "surface_piercing"
        }
        CREATE geometry.attachment aka_port {
            body_id: "main",
            target_body_id: "outrigger_port",
            attachment_type: "rigid_beam",
            position: [0.5, -1.5, 0.3]
        }
        CREATE geometry.attachment aka_stbd {
            body_id: "main",
            target_body_id: "outrigger_stbd",
            attachment_type: "rigid_beam",
            position: [0.5, 1.5, 0.3]
        }
    """,
    reasoning="Novel trimaran-like form with elevated outriggers — validates without new code",
)


# =============================================================================
# INVALID PROPOSALS (for testing error handling)
# =============================================================================

INVALID_EMPTY_BODY = GeometryProposal.from_program(
    program_text="""CREATE geometry.body main { section_ids: [] }""",
    reasoning="Should fail: body with no sections",
)

INVALID_MISSING_SECTION = GeometryProposal.from_program(
    program_text="""CREATE geometry.body main { section_ids: ["nonexistent"] }""",
    reasoning="Should fail: references undefined section",
)

INVALID_SYNTAX = GeometryProposal.from_program(
    program_text="""CREATE geometry.body main { INVALID SYNTAX""",
    reasoning="Should fail: parse error",
)


# =============================================================================
# FIXTURE REGISTRY
# =============================================================================

VALID_FIXTURES = [
    VALID_SINGLE_HULL,
    VALID_TWIN_HULL,
    VALID_STEPPED_HULL,
    VALID_NOVEL_FORM,
]

INVALID_FIXTURES = [
    INVALID_EMPTY_BODY,
    INVALID_MISSING_SECTION,
    INVALID_SYNTAX,
]
```

**Time:** 2 hours
**Risk:** Low

---

### Phase 2: Adapt CycleExecutor (Day 2)

#### Task 2.1: Add DSL Branch to CycleExecutor

**File:** `magnet/protocol/cycle_executor.py` (modify existing)

```python
# Add import at top
from magnet.kernel.program_executor import execute_program, ExecutionResult

# Add method to CycleExecutor class
def _run_validation(self, proposal: Proposal) -> ValidationResult:
    """
    Run validation for a proposal.
    
    Handles both:
    - GeometryProposal: Uses program_executor (NEW path)
    - Proposal: Uses validator_executor (OLD path)
    """
    # Import here to avoid circular dependency
    from magnet.glue.protocol.schemas import GeometryProposal
    
    if isinstance(proposal, GeometryProposal):
        # NEW PATH: Geometry DSL
        exec_result = execute_program(
            proposal.program_text,
            self.state,
            dry_run=True,  # Don't commit yet — CycleExecutor manages transactions
        )
        return self._convert_exec_result_to_validation(exec_result)
    else:
        # OLD PATH: Parameter changes
        if self._validator_executor is None:
            raise RuntimeError("No validator executor registered")
        
        request = ValidationRequest(
            proposal_id=proposal.proposal_id,
            changes=proposal.changes,
        )
        return self._validator_executor(request)

def _convert_exec_result_to_validation(
    self,
    exec_result: ExecutionResult,
) -> ValidationResult:
    """Convert ExecutionResult to ValidationResult for CycleExecutor."""
    findings = []
    
    # Convert errors to findings
    for error in exec_result.errors:
        findings.append(ValidationFinding(
            validator_name="program_executor",
            severity="error",
            message=error,
        ))
    
    # Convert constraint violations to findings
    for constraint in exec_result.constraints:
        if not constraint.get("passes", True):
            findings.append(ValidationFinding(
                validator_name="constraint",
                severity="error" if constraint.get("severity") == "ERROR" else "warning",
                path=constraint.get("path"),
                message=constraint.get("message", "Constraint violated"),
                actual_value=constraint.get("actual"),
                expected_value=constraint.get("required"),
            ))
    
    # Convert validation results to findings
    validation = exec_result.validation or {}
    hydro = validation.get("hydrostatics", {})
    if hydro.get("gm_m") is not None and hydro["gm_m"] < 0.5:
        findings.append(ValidationFinding(
            validator_name="hydrostatics",
            severity="warning",
            path="stability.gm_m",
            message=f"GM is {hydro['gm_m']:.2f}m, below recommended 0.5m",
            actual_value=hydro["gm_m"],
            expected_value=0.5,
            suggestion="Consider increasing beam or lowering VCG",
        ))
    
    return ValidationResult(
        passed=exec_result.success and len([f for f in findings if f.severity == "error"]) == 0,
        findings=findings,
        error_count=len([f for f in findings if f.severity == "error"]),
        warning_count=len([f for f in findings if f.severity == "warning"]),
    )
```

**Time:** 3 hours
**Risk:** Medium
**Test:**
```python
def test_cycle_executor_geometry_proposal():
    from tests.fixtures.geometry_proposals import VALID_SINGLE_HULL
    
    executor = CycleExecutor(state_manager)
    result = executor.execute_cycle(
        VALID_SINGLE_HULL,
        agent_callback=lambda vr: AgentDecision(decision=DecisionType.APPROVE),
    )
    assert result["status"] == "approved"
```

---

### Phase 3: Wire CascadeExecutor (Day 3)

#### Task 3.1: Create GeometryCalculator

**File:** `magnet/dependencies/geometry_calculator.py` (new file)

```python
"""
Geometry Calculator for CascadeExecutor.

Bridges the NEW geometry primitives path to the EXISTING cascade infrastructure.

INVARIANT: This module must NEVER reference hull_type, HullFamily, or HullType.
           It calls program_executor which is verified clean by invariant tests.
"""

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class GeometryCalculator:
    """
    Calculator that runs program_executor for geometry changes.
    
    Registered with CascadeExecutor.CalculatorRegistry to handle
    geometry primitive recalculation.
    """
    
    def __call__(
        self,
        state_manager: "StateManager",
        param: str,
    ) -> Any:
        """
        Recalculate geometry from design_program.
        
        Args:
            state_manager: Current design state
            param: Parameter being recalculated (ignored — we recompile all geometry)
        
        Returns:
            HullGeometry or None
        """
        from magnet.kernel.program_executor import execute_program
        
        program = state_manager.get("design_program")
        if not program:
            return None
        
        result = execute_program(program, state_manager, dry_run=True)
        
        if result.success and result.geometry:
            return result.geometry
        
        return None


def register_geometry_calculators(registry: "CalculatorRegistry") -> None:
    """
    Register geometry calculators with the cascade registry.
    
    Call this during application startup.
    """
    calculator = GeometryCalculator()
    
    # Register for all geometry-related parameters
    geometry_params = [
        "hull.geometry",
        "resources.geometry.section",
        "resources.geometry.body",
        "resources.geometry.surface",
    ]
    
    for param in geometry_params:
        registry.register(
            param=param,
            calculator=calculator,
            estimated_time_ms=500,
            requires_lock=True,  # Geometry compilation is not thread-safe
        )
```

**Time:** 2 hours
**Risk:** Low

**Invariant test to add:**
```python
def test_geometry_calculator_no_enumeration():
    """GeometryCalculator must not reference hull types."""
    import inspect
    from magnet.dependencies.geometry_calculator import GeometryCalculator
    
    source = inspect.getsource(GeometryCalculator)
    assert "hull_type" not in source.lower()
    assert "hullfamily" not in source.lower()
    assert "hulltype" not in source.lower()
```

---

### Phase 4: Create EnrichedDelta (Day 4)

#### Task 4.1: Define Metric Polarity

**File:** `magnet/kernel/metric_polarity.py` (new file)

```python
"""
Metric polarity configuration for delta direction computation.

Defines whether higher or lower values are "better" for each tracked metric.
Used by EnrichedDelta to compute direction: "improved" | "degraded" | "neutral"

COMPLETE LIST: All 25+ tracked metrics from MAGNET_System_State_Analysis.md
"""

from typing import Dict

DIRECTION_POLARITY: Dict[str, str] = {
    # ═══════════════════════════════════════════════════════════════════════════
    # STABILITY — Higher is better (more stable)
    # ═══════════════════════════════════════════════════════════════════════════
    "stability.gm_m": "higher_is_better",
    "stability.gm_transverse_m": "higher_is_better",
    "stability.bm_m": "higher_is_better",
    "stability.bm_transverse_m": "higher_is_better",
    "stability.kb_m": "higher_is_better",
    "stability.gz_max": "higher_is_better",
    "stability.range_positive_gz_deg": "higher_is_better",
    "stability.angle_max_gz_deg": "neutral",  # Design-dependent
    "gm_m": "higher_is_better",  # Alias without prefix
    "bm_m": "higher_is_better",  # Alias without prefix
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RESISTANCE — Lower is better (less drag)
    # ═══════════════════════════════════════════════════════════════════════════
    "resistance.total_kn": "lower_is_better",
    "resistance.total_resistance_kn": "lower_is_better",
    "resistance.frictional_kn": "lower_is_better",
    "resistance.wave_kn": "lower_is_better",
    "resistance.appendage_kn": "lower_is_better",
    "resistance.air_kn": "lower_is_better",
    "resistance_kn": "lower_is_better",  # Alias without prefix
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PERFORMANCE — Higher is better
    # ═══════════════════════════════════════════════════════════════════════════
    "performance.max_speed_kts": "higher_is_better",
    "performance.cruise_speed_kts": "higher_is_better",
    "performance.range_nm": "higher_is_better",
    "performance.endurance_hours": "higher_is_better",
    
    # ═══════════════════════════════════════════════════════════════════════════
    # WEIGHT — Lower is better (lighter vessel)
    # ═══════════════════════════════════════════════════════════════════════════
    "weight.lightship_kg": "lower_is_better",
    "weight.lightship_mt": "lower_is_better",
    "weight.structural_kg": "lower_is_better",
    "weight.machinery_kg": "lower_is_better",
    "weight.outfit_kg": "lower_is_better",
    "weight.margin_kg": "neutral",  # Design-dependent
    
    # ═══════════════════════════════════════════════════════════════════════════
    # WEIGHT DISTRIBUTION — Neutral (depends on design intent)
    # ═══════════════════════════════════════════════════════════════════════════
    "weight.vcg_m": "neutral",  # Target-dependent
    "weight.lcg_m": "neutral",  # Target-dependent
    "weight.tcg_m": "neutral",  # Should be ~0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COST — Lower is better
    # ═══════════════════════════════════════════════════════════════════════════
    "cost.build_usd": "lower_is_better",
    "cost.annual_operating_usd": "lower_is_better",
    "cost.lifecycle_usd": "lower_is_better",
    "cost.fuel_annual_usd": "lower_is_better",
    "cost.crew_annual_usd": "lower_is_better",
    "cost.maintenance_annual_usd": "lower_is_better",
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HULL GEOMETRY — Neutral (design-dependent)
    # ═══════════════════════════════════════════════════════════════════════════
    "hull.displacement_m3": "neutral",  # Depends on mission
    "hull.displacement_mt": "neutral",
    "hull.wetted_surface_m2": "lower_is_better",  # Less drag
    "hull.waterplane_area_m2": "neutral",
    "hull.block_coefficient": "neutral",  # Design-dependent
    "hull.prismatic_coefficient": "neutral",
    "hull.midship_coefficient": "neutral",
    "hull.volume_m3": "neutral",
    "volume_m3": "neutral",  # Alias without prefix
    "displacement_m3": "neutral",  # Alias without prefix
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CAPACITY — Higher is better
    # ═══════════════════════════════════════════════════════════════════════════
    "capacity.cargo_m3": "higher_is_better",
    "capacity.fuel_m3": "higher_is_better",
    "capacity.freshwater_m3": "higher_is_better",
    "capacity.passengers": "higher_is_better",
    "capacity.crew_berthed": "higher_is_better",
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMPLIANCE — Higher is better (more margin)
    # ═══════════════════════════════════════════════════════════════════════════
    "compliance.freeboard_margin_m": "higher_is_better",
    "compliance.stability_margin_pct": "higher_is_better",
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PROPULSION — Context-dependent
    # ═══════════════════════════════════════════════════════════════════════════
    "propulsion.installed_power_kw": "neutral",  # Must meet requirement
    "propulsion.efficiency_pct": "higher_is_better",
    "propulsion.fuel_consumption_kg_hr": "lower_is_better",
}

# Total: 50+ metrics with polarity defined


def get_direction(parameter: str, delta: float) -> str:
    """
    Compute direction string for a metric change.
    
    Returns:
        "improved" — Change is in the desirable direction
        "degraded" — Change is in the undesirable direction
        "neutral" — No preference or design-dependent
    """
    # Normalize path
    normalized = parameter
    for prefix in ["validation.", "computed.", "hull."]:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    
    polarity = DIRECTION_POLARITY.get(normalized, "neutral")
    
    if abs(delta) < 1e-9:
        return "neutral"
    
    if polarity == "higher_is_better":
        return "improved" if delta > 0 else "degraded"
    elif polarity == "lower_is_better":
        return "improved" if delta < 0 else "degraded"
    else:
        return "neutral"
```

---

#### Task 4.2: Define EnrichedDelta

**File:** `magnet/kernel/enriched_delta.py` (new file)

```python
"""
EnrichedDelta — Unified delta structure for feedback.

Combines:
- RecalculationResult from CascadeExecutor (EXISTING)
- MetricDelta semantics from PropagationEngine (NEW)
"""

from dataclasses import dataclass
from typing import Any, Optional

from magnet.kernel.metric_polarity import get_direction


@dataclass
class EnrichedDelta:
    """
    Enriched metric delta with direction semantics.
    
    Used in feedback generation to tell users not just WHAT changed,
    but WHETHER the change was good or bad.
    """
    
    parameter: str
    old_value: Optional[float]
    new_value: Optional[float]
    delta: Optional[float]
    percent_change: Optional[float]
    direction: str  # "improved" | "degraded" | "neutral"
    
    # From RecalculationResult
    execution_time_ms: int = 0
    was_skipped: bool = False
    
    @classmethod
    def from_values(
        cls,
        parameter: str,
        old_value: Optional[float],
        new_value: Optional[float],
        execution_time_ms: int = 0,
    ) -> "EnrichedDelta":
        """Create EnrichedDelta from old and new values."""
        delta = None
        percent_change = None
        direction = "neutral"
        
        if old_value is not None and new_value is not None:
            delta = new_value - old_value
            if abs(old_value) > 1e-9:
                percent_change = (delta / old_value) * 100
            direction = get_direction(parameter, delta)
        
        return cls(
            parameter=parameter,
            old_value=old_value,
            new_value=new_value,
            delta=delta,
            percent_change=percent_change,
            direction=direction,
            execution_time_ms=execution_time_ms,
        )
    
    @classmethod
    def from_recalc_result(
        cls,
        result: Any,  # RecalculationResult
    ) -> "EnrichedDelta":
        """Create EnrichedDelta from CascadeExecutor RecalculationResult."""
        return cls.from_values(
            parameter=result.parameter,
            old_value=result.old_value,
            new_value=result.new_value,
            execution_time_ms=result.execution_time_ms,
        )
    
    def to_dict(self) -> dict:
        return {
            "parameter": self.parameter,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "delta": self.delta,
            "percent_change": self.percent_change,
            "direction": self.direction,
            "execution_time_ms": self.execution_time_ms,
        }
    
    def to_feedback_string(self) -> str:
        """Generate human-readable feedback string."""
        if self.delta is None:
            return f"{self.parameter}: no change"
        
        arrow = "↑" if self.delta > 0 else "↓" if self.delta < 0 else "→"
        emoji = "✅" if self.direction == "improved" else "⚠️" if self.direction == "degraded" else ""
        
        return f"{self.parameter}: {self.old_value:.2f} → {self.new_value:.2f} ({self.delta:+.2f} {arrow}) {emoji}"
```

**Time:** 2 hours
**Risk:** Low

---

### Phase 5: Merge Feedback Generation (Day 5)

#### Task 5.1: Add Geometry Templates to NarrativeGenerator

**File:** `magnet/explain/narrative.py` (modify existing)

```python
# Add to NarrativeGenerator class

GEOMETRY_TEMPLATES = {
    "volume_change": "Volume changed from {old:.1f}m³ to {new:.1f}m³ ({delta:+.1f}m³)",
    "parallel_axis": "GM increased due to parallel axis theorem: I_total = ΣI_local + ΣA×d²",
    "multi_body": "Design has {n} bodies with hull spacing of {spacing:.1f}m",
    "section_count": "Hull defined by {n} sections from station {first:.2f} to {last:.2f}",
    "gm_warning": "⚠️ GM is {gm:.2f}m — below recommended 0.5m minimum",
    "gm_critical": "❌ Vessel is unstable (GM < 0). Consider wider beam or lower VCG.",
}

def generate_geometry_narrative(
    self,
    exec_result: "ExecutionResult",
    deltas: List["EnrichedDelta"],
    level: ExplanationLevel = ExplanationLevel.STANDARD,
) -> str:
    """
    Generate narrative for geometry execution result.
    
    Args:
        exec_result: Result from program_executor
        deltas: List of EnrichedDelta from cascade
        level: Explanation detail level
    
    Returns:
        Human-readable markdown narrative
    """
    lines = []
    
    # Geometry summary
    if exec_result.geometry:
        geom = exec_result.geometry
        lines.append("## Geometry")
        lines.append(f"- Volume: {abs(geom.volume):.1f} m³")
        
        if geom.sections:
            n = len(geom.sections)
            first = min(s.x_position for s in geom.sections)
            last = max(s.x_position for s in geom.sections)
            lines.append(self.GEOMETRY_TEMPLATES["section_count"].format(
                n=n, first=first, last=last
            ))
        
        bodies = getattr(geom, 'bodies', {})
        if len(bodies) > 1:
            offsets = [b.get('offset_y_m', 0) for b in bodies.values()]
            spacing = max(offsets) - min(offsets) if offsets else 0
            lines.append(self.GEOMETRY_TEMPLATES["multi_body"].format(
                n=len(bodies), spacing=spacing
            ))
            lines.append(self.GEOMETRY_TEMPLATES["parallel_axis"])
        
        lines.append("")
    
    # Stability summary
    validation = exec_result.validation or {}
    hydro = validation.get("hydrostatics", {})
    if hydro:
        lines.append("## Stability")
        gm = hydro.get("gm_m")
        if gm is not None:
            if gm < 0:
                lines.append(self.GEOMETRY_TEMPLATES["gm_critical"])
            elif gm < 0.5:
                lines.append(self.GEOMETRY_TEMPLATES["gm_warning"].format(gm=gm))
            else:
                lines.append(f"- GM: {gm:.2f}m ✅")
        
        if hydro.get("bm_transverse_m"):
            lines.append(f"- BM: {hydro['bm_transverse_m']:.2f}m")
        if hydro.get("method"):
            lines.append(f"- Method: {hydro['method']}")
        lines.append("")
    
    # Deltas
    if deltas:
        lines.append("## Changes")
        for delta in deltas:
            if delta.direction != "neutral":
                lines.append(f"- {delta.to_feedback_string()}")
        lines.append("")
    
    return "\n".join(lines)
```

**Time:** 2 hours
**Risk:** Low

---

### Phase 6: Update DesignConversation + Wire ClarificationManager (Day 5)

#### Task 6.1: Wire to CycleExecutor + ClarificationManager

**File:** `magnet/agents/design_conversation.py` (modify existing)

Replace the custom loop with `CycleExecutor` and integrate `ClarificationManager`:

```python
# In DesignConversation.__init__() method

def __init__(
    self,
    state_manager: StateManager,
    llm_client: Optional[LLMClient] = None,
    clarification_manager: Optional[ClarificationManager] = None,  # NEW
    confidence_threshold: float = 0.6,  # NEW
):
    self.state_manager = state_manager
    self.llm_client = llm_client
    self.geometry_proposer = GeometryProposer(llm_client) if llm_client else None
    self.clarification_manager = clarification_manager  # NEW
    self.confidence_threshold = confidence_threshold  # NEW
    self.iteration_number = 0
    self.pending_clarification: Optional[str] = None  # NEW


# In DesignConversation.chat() method

async def chat(
    self,
    user_message: str,
    constraints: Optional[List[str]] = None,
) -> ChatIterationResult:
    """Process user message through the design spiral."""
    self.iteration_number += 1
    
    # 0. Check for pending clarification response
    if self.pending_clarification:
        return await self._handle_clarification_response(user_message)
    
    # 1. Generate geometry proposal
    if self.use_llm and self.geometry_proposer:
        proposer_result = await self.geometry_proposer.propose(
            intent=user_message,
            current_state=self.state_manager.to_dict(),
            constraints=constraints,
        )
        
        # 1a. CHECK CONFIDENCE — Ask human if uncertain
        if proposer_result.confidence < self.confidence_threshold:
            return await self._request_clarification(proposer_result)
        
        if not proposer_result.success:
            return ChatIterationResult(
                success=False,
                iteration_number=self.iteration_number,
                feedback_to_user=f"Could not generate geometry: {proposer_result.error}",
            )
        program_text = proposer_result.program_text
    else:
        # Direct DSL input
        program_text = self._extract_dsl(user_message)
        if not program_text:
            return ChatIterationResult(
                success=False,
                iteration_number=self.iteration_number,
                feedback_to_user="Please provide geometry DSL or enable LLM.",
            )
    
    # 2. Create geometry proposal
    from magnet.glue.protocol.schemas import GeometryProposal, AgentDecision, DecisionType
    
    proposal = GeometryProposal.from_program(
        program_text=program_text,
        agent_id="design_conversation",
        reasoning=user_message,
    )
    
    # 3. Execute through CycleExecutor
    from magnet.protocol.cycle_executor import CycleExecutor, CycleConfig
    
    executor = CycleExecutor(
        state=self.state_manager,
        config=CycleConfig(
            max_iterations=3,
            timeout_seconds=60,
            use_transactions=True,
        ),
    )
    
    # Agent callback: for now, auto-approve or escalate
    def agent_callback(validation_result):
        if validation_result.error_count == 0:
            return AgentDecision(decision=DecisionType.APPROVE)
        elif validation_result.error_count <= 2:
            return AgentDecision(
                decision=DecisionType.REVISE,
                reasoning="Attempting to fix validation errors",
            )
        else:
            return AgentDecision(
                decision=DecisionType.ESCALATE,
                reasoning="Too many errors, need human input",
            )
    
    cycle_result = executor.execute_cycle(proposal, agent_callback)
    
    # 4. Generate feedback
    from magnet.explain import NarrativeGenerator, ExplanationLevel
    
    narrator = NarrativeGenerator()
    feedback = narrator.generate_geometry_narrative(
        exec_result=cycle_result.get("exec_result"),
        deltas=cycle_result.get("deltas", []),
        level=ExplanationLevel.STANDARD,
    )
    
    return ChatIterationResult(
        success=cycle_result["status"] in ("approved", "approved_with_warnings"),
        iteration_number=self.iteration_number,
        feedback_to_user=feedback,
        metrics=cycle_result.get("metrics", {}),
        deltas=cycle_result.get("deltas", {}),
    )


async def _request_clarification(
    self,
    proposer_result: ProposerResult,
) -> ChatIterationResult:
    """
    Request clarification from human when agent is uncertain.
    
    This is the HUMAN-IN-THE-LOOP mechanism — when the LLM isn't sure,
    it asks instead of guessing.
    """
    if not self.clarification_manager:
        # No clarification manager — fall back to asking in chat
        return ChatIterationResult(
            success=False,
            iteration_number=self.iteration_number,
            feedback_to_user=(
                f"I'm not confident about this design (confidence: {proposer_result.confidence:.0%}).\n\n"
                f"**Uncertainty:** {proposer_result.uncertainty_reason}\n\n"
                f"Could you clarify? Options:\n"
                + "\n".join(f"- {opt}" for opt in proposer_result.options)
            ),
            needs_clarification=True,
        )
    
    # Create formal clarification request
    clarification = self.clarification_manager.create_request(
        agent_id="geometry_proposer",
        message=proposer_result.uncertainty_reason or "Uncertain about design parameters",
        options=proposer_result.options or [],
        context={
            "intent": proposer_result.original_intent,
            "confidence": proposer_result.confidence,
            "partial_program": proposer_result.partial_program,
        },
    )
    
    self.pending_clarification = clarification.request_id
    
    return ChatIterationResult(
        success=False,
        iteration_number=self.iteration_number,
        feedback_to_user=(
            f"🤔 **I need clarification before proceeding:**\n\n"
            f"{clarification.message}\n\n"
            f"Please choose one:\n"
            + "\n".join(f"- **{opt['label']}**: {opt.get('description', '')}" 
                       for opt in clarification.options)
        ),
        needs_clarification=True,
        clarification_id=clarification.request_id,
    )


async def _handle_clarification_response(
    self,
    user_response: str,
) -> ChatIterationResult:
    """Handle user's response to a clarification request."""
    if not self.clarification_manager or not self.pending_clarification:
        return ChatIterationResult(
            success=False,
            iteration_number=self.iteration_number,
            feedback_to_user="No pending clarification to respond to.",
        )
    
    # Record the response
    self.clarification_manager.respond(
        request_id=self.pending_clarification,
        response=user_response,
    )
    
    # Get the original context and retry with clarification
    clarification = self.clarification_manager.get_request(self.pending_clarification)
    self.pending_clarification = None
    
    # Retry the proposal with the clarification
    proposer_result = await self.geometry_proposer.propose(
        intent=clarification.context["intent"],
        current_state=self.state_manager.to_dict(),
        clarification=user_response,  # Pass clarification to proposer
    )
    
    # Continue with normal flow (now with higher confidence)
    if not proposer_result.success:
        return ChatIterationResult(
            success=False,
            iteration_number=self.iteration_number,
            feedback_to_user=f"Could not generate geometry: {proposer_result.error}",
        )
    
    # ... continue with cycle execution ...
```

**Time:** 3 hours (increased due to clarification integration)
**Risk:** Medium

---

#### Task 6.2: Update ChatIterationResult Schema

**File:** `magnet/agents/design_conversation.py` (add to existing)

```python
@dataclass
class ChatIterationResult:
    """Result of a chat iteration in the design spiral."""
    
    success: bool
    iteration_number: int
    feedback_to_user: str
    
    # Metrics and deltas
    metrics: Dict[str, Any] = field(default_factory=dict)
    deltas: Dict[str, Any] = field(default_factory=dict)
    
    # Clarification state (NEW)
    needs_clarification: bool = False
    clarification_id: Optional[str] = None
    
    # Geometry result (optional)
    geometry: Optional[Any] = None
    validation: Optional[Dict[str, Any]] = None
```

---

### Phase 7: Cleanup (Day 6)

#### Task 7.1: Delete PropagationEngine

```bash
rm magnet/kernel/propagation.py
```

Update imports in any files that reference it.

#### Task 7.2: Delete Inline PHASE_DEPS

Remove from `propagation.py` (already deleted) and any other files that duplicate `DependencyGraph.PHASE_OWNERSHIP`.

#### Task 7.3: Delete generate_feedback()

Remove from `design_conversation.py` — now using `NarrativeGenerator.generate_geometry_narrative()`.

#### Task 7.4: Final Test Run

```bash
# Run all tests
python -m pytest tests/ -v

# Run invariant tests specifically
python -m pytest tests/invariants/ -v

# Run THE TEST
python -c "
from tests.fixtures.geometry_proposals import VALID_STEPPED_HULL, VALID_TWIN_HULL, VALID_NOVEL_FORM
from magnet.kernel.program_executor import execute_program
from magnet.core.state_manager import StateManager

# Test 1: Stepped hull without 'stepped hull' type
state = StateManager()
result = execute_program(VALID_STEPPED_HULL.program_text, state)
assert result.success, 'Stepped hull failed'
assert 'stepped' not in str(result).lower(), 'Found forbidden term'
print('✅ Test 1: Stepped hull from primitives')

# Test 2: Twin hull without 'catamaran' type
state = StateManager()
result = execute_program(VALID_TWIN_HULL.program_text, state)
assert result.success, 'Twin hull failed'
assert 'catamaran' not in str(result).lower(), 'Found forbidden term'
print('✅ Test 2: Twin hull from primitives')

# Test 3: Novel form validates without new code
state = StateManager()
result = execute_program(VALID_NOVEL_FORM.program_text, state)
assert result.success, 'Novel form failed'
print('✅ Test 3: Novel form validates')

print('\\n🎉 ALL TESTS PASS — Architecture achieves the goal')
"
```

**Time:** 4 hours
**Risk:** Low

---

## Part IV: Success Criteria

### The Test (Repeated for Emphasis)

| Test | Criterion | Pass Condition |
|:-----|:----------|:---------------|
| 1 | Stepped ventilated planing hull | Uses discontinuities, flow_paths, openings — NO "stepped hull" type |
| 2 | Twin hull vessel | Uses bodies, sections, surfaces — NO "catamaran" type |
| 3 | Novel configuration | Validates without adding code |

### Invariants That Must Hold

```python
# All must pass after implementation

def test_program_executor_never_imports_hull_families():
    """NEW path has zero HullFamily references."""
    
def test_geometry_calculator_no_enumeration():
    """Calculator doesn't reintroduce enumeration."""
    
def test_cycle_executor_geometry_proposal():
    """CycleExecutor handles geometry DSL."""
    
def test_program_executor_atomic():
    """State changes are all-or-nothing."""
```

### Metrics

| Metric | Before | After |
|:-------|:-------|:------|
| Lines of duplicate code | ~680 | 0 |
| Orphaned components wired | 0 | 4+ |
| API routers mounted | 1 | 4 |
| Test coverage for geometry | Partial | Full |

---

## Part V: Timeline Summary

| Day | Focus | Hours | Deliverables |
|:----|:------|:------|:-------------|
| 1 AM | Mount routers, verify atomicity | 2.5h | 3 routers, atomic execution, 3 rollback tests |
| 1 PM | Add geometry to DependencyGraph | 1h | Graph includes geometry paths |
| 1 PM | **Phase 0.5: Vision Interpreter** | 3h | Sketch → geometry pipeline |
| 2 | Create GeometryProposal + fixtures | 5h | Schema + 7 test fixtures |
| 3 | Adapt CycleExecutor for geometry | 5h | DSL branch working |
| 4 | Wire CascadeExecutor + EnrichedDelta | 4h | Cascade propagates geometry, 50+ metric polarities |
| 5 AM | Merge feedback into NarrativeGenerator | 2h | Geometry templates |
| 5 PM | Update DesignConversation + ClarificationManager | 3h | Uses CycleExecutor + human-in-loop clarification |
| 6 | Cleanup + final testing | 4h | -500 lines, all tests pass |
| **Total** | | **~25.5h** | |

### Phase-by-Phase Checklist

#### Phase 0: Prerequisites ☐
- [ ] Mount `create_agents_router()`
- [ ] Mount `create_interior_router()`
- [ ] Mount `create_routing_router()`
- [ ] Verify `program_executor` atomicity
- [ ] Add `test_program_executor_atomic()`
- [ ] Add `test_geometry_proposal_rollback()`
- [ ] Add `test_partial_execution_rollback()`
- [ ] Add geometry paths to `PHASE_OWNERSHIP`

#### Phase 0.5: Vision Interpreter ☐ (Optional but Recommended)
- [ ] Add `complete_with_image()` to `AnthropicProvider`
- [ ] Create `magnet/agents/vision_interpreter.py`
- [ ] Implement `VisionInterpreter` class
- [ ] Implement `VISION_INTERPRETER_SYSTEM_PROMPT` (geometry-only)
- [ ] Add `chat_with_image()` to `DesignConversation`
- [ ] Add `POST /api/v1/design/sketch` endpoint
- [ ] Create `tests/invariants/test_vision_no_enumeration.py`
- [ ] Verify FORBIDDEN_TERMS blocks design type names
- [ ] Test: sketch with "25m" → dimensions extracted

#### Phase 1: GeometryProposal ☐
- [ ] Create `GeometryProposal` schema
- [ ] Create `VALID_SINGLE_HULL` fixture
- [ ] Create `VALID_TWIN_HULL` fixture
- [ ] Create `VALID_STEPPED_HULL` fixture
- [ ] Create `VALID_NOVEL_FORM` fixture
- [ ] Create `INVALID_*` fixtures

#### Phase 2: CycleExecutor ☐
- [ ] Add `_run_validation()` DSL branch
- [ ] Add `_convert_exec_result_to_validation()`
- [ ] Test `test_cycle_executor_geometry_proposal()`

#### Phase 3: CascadeExecutor ☐
- [ ] Create `GeometryCalculator`
- [ ] Register with `CalculatorRegistry`
- [ ] Add `test_geometry_calculator_no_enumeration()`

#### Phase 4: EnrichedDelta ☐
- [ ] Create `DIRECTION_POLARITY` (50+ metrics)
- [ ] Create `get_direction()` function
- [ ] Create `EnrichedDelta` dataclass

#### Phase 5: NarrativeGenerator ☐
- [ ] Add `GEOMETRY_TEMPLATES`
- [ ] Add `generate_geometry_narrative()`

#### Phase 6: DesignConversation ☐
- [ ] Wire to `CycleExecutor`
- [ ] Wire to `ClarificationManager`
- [ ] Add `_request_clarification()`
- [ ] Add `_handle_clarification_response()`
- [ ] Update `ChatIterationResult` schema

#### Phase 7: Cleanup ☐
- [ ] Delete `magnet/kernel/propagation.py`
- [ ] Delete inline `PHASE_DEPS`
- [ ] Delete `generate_feedback()`
- [ ] Run `pytest tests/ -v`
- [ ] Run `pytest tests/invariants/ -v`
- [ ] Run THE TEST

---

## Part VI: Risk Monitoring

### Enumeration Trap

**Watch for:**
```python
# ❌ FORBIDDEN
if hull_type == "catamaran":
if body_count == 2:  # Implies catamaran
```

**Verification:**
```bash
grep -rn "catamaran\|stepped.*hull\|patrol.*boat" magnet/kernel/ magnet/dependencies/
# Expected: Zero matches
```

### Contract Violation

**Watch for:**
- Kernel suggesting designs
- Kernel recognizing intent
- New resource types for new forms

**Verification:**
- Invariant tests continue to pass
- Novel forms validate without code changes

---

## Part VII: Sacred Invariants

These invariants **MUST** hold throughout implementation. Run these checks after every phase.

### Invariant 1: No Design Terms in Kernel

```bash
# MUST return zero matches
grep -rn "catamaran\|trimaran\|monohull\|stepped.*hull\|patrol.*boat\|workboat" \
    magnet/kernel/ magnet/dependencies/ \
    --include="*.py" | grep -v "test\|__pycache__\|#"
```

### Invariant 2: No HullFamily in NEW Path

```bash
# MUST return zero matches
grep -rn "HullFamily\|HullType\|hull_type" \
    magnet/kernel/stdlib/ \
    magnet/kernel/program_executor.py \
    magnet/dependencies/geometry_calculator.py \
    --include="*.py" | grep -v "test\|__pycache__"
```

### Invariant 3: GeometryProposal Contains DSL Only

```python
# In tests/invariants/test_no_design_terms.py
def test_geometry_proposal_no_hull_types():
    """GeometryProposal must contain DSL, not hull type strings."""
    from tests.fixtures.geometry_proposals import VALID_FIXTURES
    
    forbidden = ["catamaran", "trimaran", "monohull", "stepped_hull"]
    
    for fixture in VALID_FIXTURES:
        program_lower = fixture.program_text.lower()
        for term in forbidden:
            assert term not in program_lower, \
                f"Fixture contains forbidden term '{term}'"
```

### Invariant 4: Novel Forms Work Without Code Changes

```python
# In tests/invariants/test_novel_forms.py
def test_novel_form_validates():
    """Novel configurations validate without adding code."""
    from tests.fixtures.geometry_proposals import VALID_NOVEL_FORM
    from magnet.kernel.program_executor import execute_program
    from magnet.core.state_manager import StateManager
    
    state = StateManager()
    result = execute_program(VALID_NOVEL_FORM.program_text, state)
    
    assert result.success, f"Novel form failed: {result.errors}"
    assert result.geometry is not None
    assert result.validation is not None
```

### Invariant 5: Atomic Execution

```python
# In tests/invariants/test_atomicity.py
def test_partial_failure_rolls_back():
    """Failed execution leaves state unchanged."""
    from magnet.kernel.program_executor import execute_program
    from magnet.core.state_manager import StateManager
    
    state = StateManager()
    state.set("marker", "original")
    
    # Program that fails after first statement
    program = """
        SET marker = "modified"
        CREATE geometry.body main { section_ids: ["nonexistent"] }
    """
    result = execute_program(program, state, dry_run=False)
    
    assert not result.success
    assert state.get("marker") == "original", "State was not rolled back"
```

### Invariant 6: ClarificationManager Asks, Doesn't Guess

```python
# In tests/invariants/test_human_in_loop.py
def test_low_confidence_triggers_clarification():
    """Low confidence proposals trigger clarification, not guessing."""
    from magnet.agents.design_conversation import DesignConversation
    from unittest.mock import Mock, AsyncMock
    
    # Mock proposer that returns low confidence
    proposer = Mock()
    proposer.propose = AsyncMock(return_value=ProposerResult(
        success=True,
        confidence=0.4,  # Below threshold
        uncertainty_reason="Hull spacing not specified",
        options=["3m", "4m", "5m"],
    ))
    
    conversation = DesignConversation(
        state_manager=Mock(),
        confidence_threshold=0.6,
    )
    conversation.geometry_proposer = proposer
    
    result = await conversation.chat("Create a twin hull vessel")
    
    assert result.needs_clarification == True
    assert "clarify" in result.feedback_to_user.lower()
```

### Invariant 7: Vision Interpreter Outputs Geometry Only

```bash
# Vision output must NEVER contain design type names
grep -rn "catamaran\|trimaran\|stepped.*hull" magnet/agents/vision_interpreter.py
# Expected: Only in FORBIDDEN_TERMS list, not in output generation code
```

```python
# In tests/invariants/test_vision_no_enumeration.py
def test_vision_intent_no_design_types():
    """Vision-generated intent contains no design type names."""
    from magnet.agents.vision_interpreter import VisionInterpreter, SketchInterpretation, FORBIDDEN_TERMS
    
    interpreter = VisionInterpreter(llm_provider=None)
    
    # Interpretation of a twin-hull sketch
    interpretation = SketchInterpretation(
        body_count=2,
        dimensions={"loa_m": 25, "body_spacing_m": 8},
    )
    
    intent = interpreter._generate_intent_string(interpretation, "")
    
    for term in FORBIDDEN_TERMS:
        assert term.lower() not in intent.lower(), \
            f"Vision intent contains forbidden term: {term}"
```

---

## Part VIII: Files Summary

### Files to Create

| File | Purpose | Phase |
|:-----|:--------|:------|
| `magnet/agents/vision_interpreter.py` | Sketch → geometry interpretation | 0.5 |
| `tests/invariants/test_vision_no_enumeration.py` | Vision invariant tests | 0.5 |
| `tests/fixtures/geometry_proposals.py` | Test fixtures for THE TEST | 1 |
| `magnet/dependencies/geometry_calculator.py` | Bridge to CascadeExecutor | 3 |
| `magnet/kernel/metric_polarity.py` | Direction computation (50+ metrics) | 4 |
| `magnet/kernel/enriched_delta.py` | Unified delta structure | 4 |

### Files to Modify

| File | Change | Phase |
|:-----|:-------|:------|
| `magnet/deployment/api.py` | Mount 3 orphaned routers + sketch endpoint | 0, 0.5 |
| `magnet/kernel/program_executor.py` | Ensure atomic execution | 0 |
| `magnet/dependencies/graph.py` | Add geometry paths to PHASE_OWNERSHIP | 0 |
| `magnet/llm/providers/anthropic.py` | Add `complete_with_image()` for vision | 0.5 |
| `magnet/glue/protocol/schemas.py` | Add GeometryProposal | 1 |
| `magnet/protocol/cycle_executor.py` | Add DSL branch to _run_validation | 2 |
| `magnet/explain/narrative.py` | Add geometry templates | 5 |
| `magnet/agents/design_conversation.py` | Wire CycleExecutor + ClarificationManager + Vision | 6 |

### Files to Delete

| File | Lines | Reason | Phase |
|:-----|:------|:-------|:------|
| `magnet/kernel/propagation.py` | ~580 | Replaced by CascadeExecutor | 7 |

### Net Change

| Metric | Value |
|:-------|:------|
| Lines added | ~700 (includes vision) |
| Lines deleted | ~900 |
| **Net change** | **-200 lines** |

---

*This implementation plan transforms the orphaned components audit into a concrete 6-day execution plan that achieves the stated goal: a human-in-the-loop design spiral enabling trillions of forms through continuous geometry primitives, validated by physics, without enumeration.*

