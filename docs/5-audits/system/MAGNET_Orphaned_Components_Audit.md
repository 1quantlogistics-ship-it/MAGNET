# MAGNET Orphaned Components Audit

<!-- AGENT_CONTEXT
Purpose: [TODO: Add purpose description]
Authoritative: No
Keywords: [magnet, orphaned, components, audit]
Depends_On: None
Used_By: [TODO: Add users]
Status: current
Last_Verified: 2026-01-15
-->


> **Implementation Plan:** See `MAGNET_Merge_Implementation_Plan.md` for the concrete 6-day execution plan derived from this audit.

## Executive Summary

The codebase contains **substantial infrastructure that is not wired to the new geometry primitives path**. Many of these components could significantly enhance the iterative design loop.

### Goal Alignment

This audit supports the mission:

> **Human-in-the-loop engineering design spiral** to enable combinatorial explosion (trillions+ of forms) through continuous geometry primitives, validated by physics, without enumeration.

| Mission Requirement | Audit Finding | Solution |
|:--------------------|:--------------|:---------|
| Human in loop | `CycleExecutor` orphaned | Wire to geometry path |
| Trillions of forms | DSL grammar exists | Use `GeometryProposal` |
| Physics validation | `ProgramExecutor` works | Keep unchanged |
| Structured feedback | `NarrativeGenerator` orphaned | Wire + add geometry templates |
| Change propagation | `CascadeExecutor` orphaned | Replace `PropagationEngine` |
| No enumeration | `GeometryCalculator` needed | Bridge to existing infra |

### Status Key
- ✅ **WIRED** — Connected to NEW path or API
- ⚠️ **PARTIAL** — Exists but not connected to NEW path
- ❌ **ORPHANED** — Complete module, not mounted/used
- 🔮 **POTENTIAL** — Could enhance NEW path if connected

---

## Part I: Agent Infrastructure

### 1.1 Clarification System ⚠️ PARTIAL

**Location:** `magnet/agents/clarification.py`, `magnet/agents/api_endpoints.py`

**What it does:**
- `ClarificationManager` — Tracks clarification request lifecycle
- ACK types: queued, presented, responded, skipped, cancelled
- Priority queue for multi-agent coordination
- Timeout handling

**Status:** API router exists (`create_agents_router`) but **NOT MOUNTED** in `api.py`

**For NEW path:**
```python
# When GeometryProposer is uncertain about intent
clarification = manager.create_request(
    agent_id="geometry_proposer",
    message="Should I add spray rails or chines for this hull type?",
    options=["spray_rails", "chines", "both", "neither"],
)
```

### 1.2 Agent Factory ⚠️ PARTIAL

**Location:** `magnet/agents/factory.py`

**What it does:**
- DI-friendly construction of agent components
- Shared LLM client access
- State manager access

**Status:** Exists but not used in `DesignConversation`

---

## Part II: Dependency & Invalidation Engine ⚠️ PARTIAL

**Location:** `magnet/dependencies/`

### Components:

| Component | Purpose | Status |
|-----------|---------|--------|
| `DependencyGraph` | DAG of parameter dependencies | ⚠️ Referenced in conductor but not in NEW path |
| `InvalidationEngine` | Cascade invalidation on changes | ⚠️ Partially used |
| `CascadeExecutor` | Ordered recalculation | ⚠️ Not connected to NEW path |
| `RevalidationScheduler` | Async revalidation | ❌ Orphaned |
| `TriggerLog` | Audit trail for changes | ⚠️ Partially used |

**For NEW path:**
```python
# When geometry changes, invalidate downstream phases
from magnet.dependencies import InvalidationEngine, CascadeExecutor

engine = InvalidationEngine(graph, state_manager)
event = engine.invalidate("geometry.body.port", reason=InvalidationReason.PARAMETER_CHANGED)
# event.invalidated_phases = ["hull", "weight", "stability", ...]

executor = CascadeExecutor(graph, engine, state_manager)
result = executor.execute_cascade(event.invalidated_parameters)
```

This is **exactly what PropagationEngine should use** instead of reimplementing.

---

## Part III: Explanation System ⚠️ PARTIAL

**Location:** `magnet/explain/`, `magnet/glue/explanation/`

### Components:

| Component | Purpose | Status |
|-----------|---------|--------|
| `TraceCollector` | Collect calculation steps | ⚠️ Not connected to NEW path |
| `NarrativeGenerator` | Human-readable explanations | ⚠️ Not connected to NEW path |
| `ChatFormatter` | Format for chat interface | ❌ Orphaned |
| `DashboardFormatter` | Format for UI dashboard | ❌ Orphaned |

**For NEW path:**
```python
# Generate explanation for why GM changed
from magnet.explain import NarrativeGenerator

generator = NarrativeGenerator()
narrative = generator.generate(
    calculation_trace=trace,
    level="detailed",  # or "brief", "technical"
)
# Output: "GM increased by 1.92m because adding twin hulls at ±4m offset
#          increases waterplane moment of inertia via the parallel axis theorem."
```

---

## Part IV: Control Plane ✅ WIRED (Partially)

**Location:** `magnet/control_plane/`

### Components:

| Component | Purpose | Status |
|-----------|---------|--------|
| `HypotheticalStateView` | Preview changes without committing | ✅ Used in intent preview |
| `ExplainRecord` | Two-phase WAL audit records | ✅ Used in conductor |
| `WhyQueryRouter` | Natural language "why" queries | ✅ Wired to API |
| `PathRegistry` | Registry of valid state paths | ⚠️ Could validate geometry paths |

**For NEW path:** Already partially integrated but `PathRegistry` could validate geometry primitive paths.

---

## Part V: LLM Services ⚠️ PARTIAL

**Location:** `magnet/llm/services/`

### Components:

| Component | Purpose | Status |
|-----------|---------|--------|
| `ClarificationService` | LLM-powered clarification generation | ⚠️ Used in ChatHandler, not NEW path |
| `ExplanationService` | LLM-powered explanations | ❌ Orphaned |
| `ComplianceService` | LLM-powered compliance checking | ❌ Orphaned |
| `RoutingService` | LLM-powered routing decisions | ❌ Orphaned |

**For NEW path:**
```python
# Generate clarification when GeometryProposer is uncertain
from magnet.llm.services import ClarificationService

clarifier = ClarificationService(llm=llm_client)
response = await clarifier.generate_clarification(
    parameter_path="geometry.body.offset_y_m",
    validation_message="Hull separation not specified",
)
# response.question = "How far apart should the twin hulls be?"
# response.options = [{"label": "2m", "value": 2.0}, ...]
```

---

## Part VI: Glue Layer ❌ MOSTLY ORPHANED

**Location:** `magnet/glue/`

### Components:

| Component | Purpose | Status |
|-----------|---------|--------|
| `CycleExecutor` | propose→validate→revise cycles | ❌ Orphaned — **CRITICAL** |
| `TransactionManager` | Atomic design changes | ❌ Orphaned |
| `EscalationHandler` | Escalation when stuck | ❌ Orphaned |
| `LifecycleManager` | Design lifecycle states | ❌ Orphaned |
| `DesignExporter` | Export to various formats | ❌ Orphaned |
| `ErrorHandler` | Error taxonomy & recovery | ❌ Orphaned |

**`CycleExecutor` is exactly what the iterative design loop needs!**

```python
# From magnet/protocol/cycle_executor.py
class CycleExecutor:
    """Executes the propose→validate→revise cycle."""
    
    def execute_cycle(self, initial_proposal: Proposal) -> CycleResult:
        # 1. Validate proposal
        # 2. If fails, revise
        # 3. Repeat until success or max_iterations
        # 4. Return result with transaction support
```

---

## Part VII: Optimization Module ❌ ORPHANED

**Location:** `magnet/optimization/`

### Components:

| Component | Purpose | Status |
|-----------|---------|--------|
| `DesignOptimizer` | NSGA-II multi-objective optimization | ❌ Orphaned |
| `ParetoAnalyzer` | Pareto frontier analysis | ❌ Orphaned |
| `SensitivityAnalyzer` | Parameter sensitivity analysis | ❌ Orphaned |
| Problem templates | Standard optimization problems | ❌ Orphaned |

**For NEW path:**
```python
# Optimize geometry for multiple objectives
from magnet.optimization import DesignOptimizer, Objective, DesignVariable

optimizer = DesignOptimizer(state_manager)
problem = OptimizationProblem(
    variables=[
        DesignVariable(path="geometry.body.port.offset_y_m", min=2.0, max=6.0),
        DesignVariable(path="geometry.section.mid.points", ...),
    ],
    objectives=[
        Objective(path="validation.hydrostatics.gm_m", type=ObjectiveType.MAXIMIZE),
        Objective(path="validation.resistance.resistance_kn", type=ObjectiveType.MINIMIZE),
    ],
)
result = optimizer.optimize(problem)
# result.pareto_front = [Solution(...), ...]
```

---

## Part VIII: Vision & WebGL ⚠️ PARTIAL

**Location:** `magnet/vision/`, `magnet/webgl/`

### Components:

| Component | Purpose | Status |
|-----------|---------|--------|
| `VisionRouter` | 3D rendering requests | ⚠️ Wired but uses OLD hull types |
| `HullFormFactory` | Generate hull forms | ⚠️ Uses `HullType` enum |
| `GeometryStreamManager` | WebSocket 3D streaming | ✅ Wired |
| `Annotation3D` | 3D annotations | ❌ Orphaned |
| `GeometryPipeline` | Geometry processing | ⚠️ Uses OLD path |

**For NEW path:** The Vision system uses `HullType` enum internally. Would need to accept `HullGeometry` from NEW path.

```python
# CURRENT (OLD path):
from magnet.vision import HullFormFactory, HullType
factory = HullFormFactory()
mesh = factory.generate(HullType.PLANING, params)  # ← Enum!

# NEEDED (NEW path):
from magnet.vision import Renderer
renderer = Renderer()
mesh = renderer.from_hull_geometry(compiled_geometry)  # ← HullGeometry from compiler
```

---

## Part IX: Reporting Module ❌ ORPHANED

**Location:** `magnet/reporting/`

### Components:

| Component | Purpose | Status |
|-----------|---------|--------|
| `DesignSummaryGenerator` | Design summary reports | ❌ Orphaned |
| `ComplianceReportGenerator` | Compliance reports | ❌ Orphaned |
| `CostReportGenerator` | Cost reports | ❌ Orphaned |
| `FullReportGenerator` | Full design reports | ❌ Orphaned |
| Exporters | PDF, DOCX, HTML, Markdown, JSON, CSV | ❌ Orphaned |

**For NEW path:**
```python
# Generate design report after compilation
from magnet.reporting import FullReportGenerator, PDFExporter

generator = FullReportGenerator(state_manager)
report = generator.generate()

exporter = PDFExporter()
exporter.export(report, "design_report.pdf")
```

---

## Part X: Interior & Routing ❌ ORPHANED API ROUTERS

**Location:** `magnet/interior/`, `magnet/routing/`

### Interior:
- `create_interior_router()` exists but **NOT MOUNTED**
- Full interior layout generation, validation, optimization
- REST API endpoints ready

### Routing:
- `create_routing_router()` exists but **NOT MOUNTED**
- Systems routing (fuel, electrical, HVAC)
- Multi-system coordination

**Both have complete API routers that just need `app.include_router()`**

---

## Part XI: Analysis Modules ❌ ORPHANED

**Location:** `magnet/analysis/`

### Components:

| Component | Purpose | Status |
|-----------|---------|--------|
| `SeakeepingPredictor` | Seakeeping analysis | ❌ Orphaned |
| `NoiseVibrationAnalyzer` | Noise/vibration analysis | ❌ Orphaned |
| Validators | Analysis validation | ❌ Orphaned |

---

## Summary: What Should Be Wired

### Priority 0 (Critical for Design Loop)

| Component | Location | Action |
|-----------|----------|--------|
| `CycleExecutor` | `magnet/glue/protocol/` | Use for propose→validate→revise |
| `CascadeExecutor` | `magnet/dependencies/` | Use for change propagation |
| `ClarificationManager` | `magnet/agents/` | Mount API router |
| `NarrativeGenerator` | `magnet/explain/` | Generate feedback explanations |

### Priority 1 (Enhances Design Loop)

| Component | Location | Action |
|-----------|----------|--------|
| `TransactionManager` | `magnet/glue/transactions/` | Atomic geometry changes |
| `DesignOptimizer` | `magnet/optimization/` | Multi-objective optimization |
| Vision `HullGeometry` support | `magnet/vision/` | Accept compiled geometry |
| `create_agents_router` | `magnet/agents/` | Mount to API |

### Priority 2 (Nice to Have)

| Component | Location | Action |
|-----------|----------|--------|
| `ReportGenerator` | `magnet/reporting/` | Design reports |
| `create_interior_router` | `magnet/interior/` | Mount to API |
| `create_routing_router` | `magnet/routing/` | Mount to API |
| `SeakeepingPredictor` | `magnet/analysis/` | Add to validation |

---

## Recommendations

### 1. Replace PropagationEngine with CascadeExecutor

The `magnet/kernel/propagation.py` I created reimplements what `CascadeExecutor` already does. Should use existing infrastructure.

### 2. Use CycleExecutor for Design Loop

The `CycleExecutor` in `magnet/protocol/` already implements propose→validate→revise with:
- Transaction support
- Escalation handling
- Timeout management
- Iteration limits

### 3. Mount Orphaned API Routers

```python
# In api.py, add:
from magnet.agents.api_endpoints import create_agents_router
from magnet.interior.api_endpoints import create_interior_router
from magnet.routing.integration.api_endpoints import create_routing_router

# After app creation:
app.include_router(create_agents_router())
app.include_router(create_interior_router())
app.include_router(create_routing_router())
```

### 4. Connect Explanation to Chat Feedback

Use `NarrativeGenerator` + `ChatFormatter` to generate human-readable feedback instead of custom `generate_feedback()` function.

### 5. Update Vision to Accept HullGeometry

The Vision system needs a path to render `HullGeometry` from the NEW compiler, not just `HullType` enums.

---

## The Big Picture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    WHAT EXISTS vs WHAT'S WIRED                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    ORPHANED (Ready to Wire)                       │  │
│  │                                                                   │  │
│  │  CycleExecutor          TransactionManager     DesignOptimizer    │  │
│  │  CascadeExecutor        EscalationHandler      ParetoAnalyzer     │  │
│  │  RevalidationScheduler  NarrativeGenerator     SensitivityAnalyzer│  │
│  │  ClarificationManager   ReportGenerators       Interior Router    │  │
│  │  ExplanationService     ChatFormatter          Routing Router     │  │
│  │  ComplianceService      ErrorHandler           Annotation3D       │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                  ↓                                      │
│                           (should flow to)                              │
│                                  ↓                                      │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                         WIRED (Working)                           │  │
│  │                                                                   │  │
│  │  GeometryProposer → ProgramExecutor → Compiler → HullGeometry    │  │
│  │                                                                   │  │
│  │  DesignConversation → chat endpoint → feedback                   │  │
│  │                                                                   │  │
│  │  WhyQueryRouter → ExplainRecords → Control Plane                 │  │
│  │                                                                   │  │
│  │  WebGL GeometryStreamManager → 3D rendering                      │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Part XII: Merge Analysis — Best of Both Worlds

### The Duplication Problem

| NEW Code (Built) | EXISTING Code (Orphaned) | Overlap |
|:-----------------|:-------------------------|:--------|
| `PropagationEngine` | `CascadeExecutor` + `InvalidationEngine` | ~80% |
| `DesignConversation` | `CycleExecutor` | ~60% |
| `generate_feedback()` | `NarrativeGenerator` + `ChatFormatter` | ~70% |
| `MetricDelta` | `RecalculationResult.value_changed` | ~90% |
| `ConstraintViolation` | `ValidationFinding` | ~85% |

### What Each System Does Well

#### NEW Code Strengths

| Component | Strength | Why It Matters |
|:----------|:---------|:---------------|
| `PropagationEngine.TRACKED_METRICS` | Explicit list of metrics to track | Clear contract for delta computation |
| `PropagationEngine.KEY_TO_PHASE` | Maps state keys to phases | Fast invalidation lookup |
| `MetricDelta.direction` | "improved"/"degraded"/"neutral" | User-friendly feedback |
| `generate_feedback()` | Geometry-aware markdown | Understands sections, bodies, parallel axis |
| `DesignConversation` | Async + LLM integration | Modern async/await pattern |

#### EXISTING Code Strengths

| Component | Strength | Why It Matters |
|:----------|:---------|:---------------|
| `CycleExecutor` | Transaction support | Atomic changes, rollback on failure |
| `CycleExecutor` | Escalation handling | What to do when stuck |
| `CycleExecutor` | Timeout management | Prevents infinite loops |
| `CycleExecutor.agent_callback` | Agent decision injection | Clean separation of concerns |
| `CascadeExecutor` | Parallel recalculation | ThreadPoolExecutor for speed |
| `CascadeExecutor` | Calculator registry | Extensible computation model |
| `CascadeExecutor.progress_callbacks` | Progress tracking | UI responsiveness |
| `InvalidationEngine` | Scoped invalidation | Parameter vs phase vs all |
| `InvalidationEngine` | Reason tracking | Why was this invalidated |
| `DependencyGraph` | Complete DAG | 200+ parameter relationships |
| `NarrativeGenerator` | Multi-level explanations | Brief, standard, detailed, expert |
| `Proposal`/`ValidationResult` | Mature schemas | Confidence, reasoning, parent_id |
| `TransactionManager` | Isolation levels | Concurrent safety |

---

### The Merged Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       MERGED ITERATIVE DESIGN LOOP                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   User Chat Message                                                         │
│         │                                                                   │
│         ▼                                                                   │
│   ┌─────────────────┐                                                       │
│   │ GeometryProposer│ (NEW) — Translates intent to geometry primitives     │
│   │ + LLMClient     │                                                       │
│   └────────┬────────┘                                                       │
│            │ geometry DSL program                                           │
│            ▼                                                                │
│   ┌─────────────────┐                                                       │
│   │ CycleExecutor   │ (EXISTING) — Manages propose→validate→revise         │
│   │   ├── Proposal  │             with transactions, escalation, timeout   │
│   │   ├── Timeout   │                                                       │
│   │   └── Rollback  │                                                       │
│   └────────┬────────┘                                                       │
│            │ calls validator                                                │
│            ▼                                                                │
│   ┌─────────────────┐                                                       │
│   │ ProgramExecutor │ (NEW) — DSL → AST → Actions → Compile                │
│   │   ├── Parser    │                                                       │
│   │   ├── Expander  │                                                       │
│   │   └── Compiler  │                                                       │
│   └────────┬────────┘                                                       │
│            │ HullGeometry + validation results                              │
│            ▼                                                                │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ CascadeExecutor + InvalidationEngine (EXISTING)                     │   │
│   │   ├── DependencyGraph.get_all_downstream()                          │   │
│   │   ├── CalculatorRegistry — extensible computation                   │   │
│   │   ├── ThreadPoolExecutor — parallel recalculation                   │   │
│   │   └── Progress callbacks — UI responsiveness                        │   │
│   └────────┬────────────────────────────────────────────────────────────┘   │
│            │ CascadeResult with all deltas                                  │
│            ▼                                                                │
│   ┌─────────────────┐                                                       │
│   │ Delta Enricher  │ (MERGED) — Combines:                                 │
│   │   ├── PropagationEngine.TRACKED_METRICS                                │
│   │   ├── RecalculationResult.value_changed                                │
│   │   └── MetricDelta.direction ("improved"/"degraded")                   │
│   └────────┬────────┘                                                       │
│            │ enriched deltas                                                │
│            ▼                                                                │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ NarrativeGenerator + ChatFormatter (EXISTING)                       │   │
│   │   ├── ExplanationLevel (brief/standard/detailed/expert)             │   │
│   │   └── Geometry-aware templates (FROM NEW generate_feedback)         │   │
│   └────────┬────────────────────────────────────────────────────────────┘   │
│            │ human-readable markdown                                        │
│            ▼                                                                │
│   ┌─────────────────┐                                                       │
│   │ Chat Response   │ — Returns to user with:                              │
│   │   ├── Feedback  │   - What changed                                     │
│   │   ├── Deltas    │   - By how much                                      │
│   │   ├── Violations│   - What's wrong                                     │
│   │   └── Suggest   │   - What to try next                                 │
│   └─────────────────┘                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Component-by-Component Merge Plan

#### 1. Replace `PropagationEngine` with `CascadeExecutor`

| Keep from NEW | Keep from EXISTING | Delete |
|:--------------|:-------------------|:-------|
| `TRACKED_METRICS` list | `CascadeExecutor` class | `PropagationEngine` class |
| `KEY_TO_PHASE` mapping | `CalculatorRegistry` | Inline phase deps |
| `MetricDelta.direction` | `InvalidationEngine` | Custom invalidation |
| — | `DependencyGraph` | — |
| — | `RecalculationResult` | — |
| — | Progress callbacks | — |

**Integration Point:**
```python
# NEW: Create a GeometryCalculator for the registry
class GeometryCalculator:
    """Calculator that runs program_executor for geometry changes."""
    
    def __call__(self, state_manager: StateManager, param: str) -> Any:
        program = state_manager.get("design_program")
        if not program:
            return None
        result = program_executor.execute_program(program, state_manager)
        return result.geometry

# Register it
registry.register(
    "hull.geometry",
    GeometryCalculator(),
    estimated_time_ms=500,
)
```

**Work Required:** ~4 hours
- Create `GeometryCalculator` wrapper
- Register geometry primitives in `CalculatorRegistry`
- Add `direction` computation to `RecalculationResult`
- Wire `DependencyGraph` to include geometry paths

---

#### 2. Adapt `CycleExecutor` for Geometry Proposals

| Keep from NEW | Keep from EXISTING | Modify |
|:--------------|:-------------------|:-------|
| `DesignProgram` schema | `CycleExecutor` class | Add DSL execution as proposal type |
| DSL validation | `Proposal` schema | Extend for geometry |
| — | Transaction support | — |
| — | Escalation handling | — |
| — | Agent callback pattern | — |

**Integration Point:**
```python
# NEW: GeometryProposal extends Proposal
@dataclass
class GeometryProposal(Proposal):
    """Proposal containing geometry DSL program."""
    program_text: str = ""
    parsed_ast: Optional[List] = None

# Modify CycleExecutor._run_validation to handle GeometryProposal
def _run_validation(self, proposal: Proposal) -> ValidationResult:
    if isinstance(proposal, GeometryProposal):
        # Use program_executor
        exec_result = program_executor.execute_program(
            proposal.program_text,
            self.state,
            dry_run=True,  # Don't commit yet
        )
        return self._convert_exec_result(exec_result)
    else:
        # Existing validation path
        return self._validator_executor(ValidationRequest(...))
```

**Work Required:** ~3 hours
- Create `GeometryProposal` subclass
- Add DSL branch to `_run_validation()`
- Map `ExecutionResult` → `ValidationResult`

---

#### 3. Merge `generate_feedback()` into `NarrativeGenerator`

| Keep from NEW | Keep from EXISTING | Delete |
|:--------------|:-------------------|:-------|
| Geometry-aware templates | `NarrativeGenerator` class | `generate_feedback()` function |
| Section/body counting | `ExplanationLevel` enum | — |
| Parallel axis explanation | Multi-level output | — |
| Markdown formatting | `ChatFormatter` | — |

**Integration Point:**
```python
# Add geometry templates to NarrativeGenerator
class NarrativeGenerator:
    GEOMETRY_TEMPLATES = {
        "volume_change": "Volume changed from {old:.1f}m³ to {new:.1f}m³ ({delta:+.1f}m³)",
        "parallel_axis": "GM increased due to parallel axis theorem: I_total = ΣI_local + ΣA×d²",
        "multi_body": "Design has {n} bodies with hull spacing of {spacing:.1f}m",
    }
    
    def generate_geometry_narrative(
        self,
        exec_result: ExecutionResult,
        level: ExplanationLevel,
    ) -> str:
        # Use templates based on level
        ...
```

**Work Required:** ~2 hours
- Add geometry templates to `NarrativeGenerator`
- Port parallel axis explanation
- Wire to `ChatFormatter`

---

#### 4. Unify Data Structures

| NEW Structure | EXISTING Structure | Merged Structure |
|:--------------|:-------------------|:-----------------|
| `MetricDelta` | `RecalculationResult` | `EnrichedDelta` |
| `ConstraintViolation` | `ValidationFinding` | Use `ValidationFinding` + extension |
| `ConversationState` | `CycleState` | `DesignSession` |

**Merged Schema:**
```python
@dataclass
class EnrichedDelta:
    """Combines RecalculationResult with MetricDelta semantics."""
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
    def from_recalc_result(cls, result: RecalculationResult) -> "EnrichedDelta":
        delta = None
        direction = "neutral"
        if result.old_value is not None and result.new_value is not None:
            delta = result.new_value - result.old_value
            direction = cls._compute_direction(result.parameter, delta)
        return cls(
            parameter=result.parameter,
            old_value=result.old_value,
            new_value=result.new_value,
            delta=delta,
            direction=direction,
            execution_time_ms=result.execution_time_ms,
        )
    
    @staticmethod
    def _compute_direction(parameter: str, delta: float) -> str:
        """Compute direction based on metric polarity."""
        polarity = DIRECTION_POLARITY.get(parameter, "neutral")
        
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

### Direction Polarity Configuration

**Required:** Define polarity for all tracked metrics so `direction` can be computed correctly.

```python
# magnet/kernel/metric_polarity.py

DIRECTION_POLARITY = {
    # ═══════════════════════════════════════════════════════════════════════
    # STABILITY — Higher is better (more stable)
    # ═══════════════════════════════════════════════════════════════════════
    "stability.gm_m": "higher_is_better",
    "stability.gm_transverse_m": "higher_is_better",
    "stability.bm_m": "higher_is_better",
    "stability.kb_m": "higher_is_better",
    "stability.gz_max": "higher_is_better",
    "stability.range_positive_gz_deg": "higher_is_better",
    
    # ═══════════════════════════════════════════════════════════════════════
    # RESISTANCE — Lower is better (less drag)
    # ═══════════════════════════════════════════════════════════════════════
    "resistance.total_kn": "lower_is_better",
    "resistance.total_resistance_kn": "lower_is_better",
    "resistance.frictional_kn": "lower_is_better",
    "resistance.wave_kn": "lower_is_better",
    "resistance.appendage_kn": "lower_is_better",
    
    # ═══════════════════════════════════════════════════════════════════════
    # PERFORMANCE — Higher is better
    # ═══════════════════════════════════════════════════════════════════════
    "performance.max_speed_kts": "higher_is_better",
    "performance.cruise_speed_kts": "higher_is_better",
    "performance.range_nm": "higher_is_better",
    "performance.endurance_hours": "higher_is_better",
    
    # ═══════════════════════════════════════════════════════════════════════
    # WEIGHT — Lower is better (lighter vessel)
    # ═══════════════════════════════════════════════════════════════════════
    "weight.lightship_kg": "lower_is_better",
    "weight.lightship_mt": "lower_is_better",
    "weight.structural_kg": "lower_is_better",
    "weight.machinery_kg": "lower_is_better",
    "weight.outfit_kg": "lower_is_better",
    
    # ═══════════════════════════════════════════════════════════════════════
    # WEIGHT DISTRIBUTION — Neutral (depends on design intent)
    # ═══════════════════════════════════════════════════════════════════════
    "weight.vcg_m": "neutral",  # Target-dependent
    "weight.lcg_m": "neutral",  # Target-dependent
    "weight.tcg_m": "neutral",  # Should be ~0
    
    # ═══════════════════════════════════════════════════════════════════════
    # COST — Lower is better
    # ═══════════════════════════════════════════════════════════════════════
    "cost.build_usd": "lower_is_better",
    "cost.annual_operating_usd": "lower_is_better",
    "cost.lifecycle_usd": "lower_is_better",
    "cost.fuel_annual_usd": "lower_is_better",
    "cost.crew_annual_usd": "lower_is_better",
    
    # ═══════════════════════════════════════════════════════════════════════
    # HULL GEOMETRY — Neutral (design-dependent)
    # ═══════════════════════════════════════════════════════════════════════
    "hull.displacement_m3": "neutral",  # Depends on mission
    "hull.displacement_mt": "neutral",
    "hull.wetted_surface_m2": "lower_is_better",  # Less drag
    "hull.waterplane_area_m2": "neutral",
    "hull.block_coefficient": "neutral",  # Design-dependent
    "hull.prismatic_coefficient": "neutral",
    "hull.midship_coefficient": "neutral",
    
    # ═══════════════════════════════════════════════════════════════════════
    # CAPACITY — Higher is better
    # ═══════════════════════════════════════════════════════════════════════
    "capacity.cargo_m3": "higher_is_better",
    "capacity.fuel_m3": "higher_is_better",
    "capacity.freshwater_m3": "higher_is_better",
    "capacity.passengers": "higher_is_better",
    "capacity.crew_berthed": "higher_is_better",
    
    # ═══════════════════════════════════════════════════════════════════════
    # COMPLIANCE — Higher is better (more margin)
    # ═══════════════════════════════════════════════════════════════════════
    "compliance.freeboard_margin_m": "higher_is_better",
    "compliance.stability_margin_pct": "higher_is_better",
    
    # ═══════════════════════════════════════════════════════════════════════
    # PROPULSION — Context-dependent
    # ═══════════════════════════════════════════════════════════════════════
    "propulsion.installed_power_kw": "neutral",  # Must meet requirement
    "propulsion.efficiency_pct": "higher_is_better",
    "propulsion.fuel_consumption_kg_hr": "lower_is_better",
}

def get_direction(parameter: str, delta: float) -> str:
    """
    Get direction string for a metric change.
    
    Returns:
        "improved" — Change is in the desirable direction
        "degraded" — Change is in the undesirable direction
        "neutral" — No preference or design-dependent
    """
    # Normalize parameter path (strip prefixes)
    normalized = parameter
    for prefix in ["validation.", "hull.", "computed."]:
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

**Work Required:** ~2 hours
- Create `EnrichedDelta` combining both
- Implement `DIRECTION_POLARITY` config
- Add `_compute_direction()` method
- Update consumers

---

### Total Merge Effort Estimate (Revised)

| Task | Initial Est. | Realistic Est. | Risk | Notes |
|:-----|:-------------|:---------------|:-----|:------|
| Replace `PropagationEngine` with `CascadeExecutor` | 4h | **6h** | Medium | Testing cascade behavior across phases |
| Adapt `CycleExecutor` for geometry | 3h | **5h** | Medium | Edge cases in DSL validation |
| Merge `generate_feedback` into `NarrativeGenerator` | 2h | 2h | Low | Template addition |
| Unify data structures | 2h | 2h | Low | Schema alignment |
| Integration testing | 3h | **5h** | High | 13 phases, many touchpoints |
| Mount orphaned routers | 0.5h | 0.5h | Very low | Just imports |
| **Total** | ~~14.5h~~ | **20.5h** | **Medium-High** | Budget ~3 days |

---

### What Gets Deleted After Merge

| File | Lines | Reason |
|:-----|:------|:-------|
| `magnet/kernel/propagation.py` | ~580 | Replaced by `CascadeExecutor` |
| `design_conversation.generate_feedback()` | ~70 | Merged into `NarrativeGenerator` |
| Inline `PHASE_DEPS` | ~15 | Use `DependencyGraph` |
| Inline `KEY_TO_PHASE` | ~15 | Use `PHASE_OWNERSHIP` from graph |

**Total reduction:** ~680 lines of duplicate code

---

### What Gets Added

| Component | Lines | Purpose |
|:----------|:------|:--------|
| `GeometryCalculator` | ~40 | Bridge program_executor to CalculatorRegistry |
| `GeometryProposal` | ~20 | Extend Proposal for DSL |
| Geometry templates | ~50 | Add to NarrativeGenerator |
| `EnrichedDelta` | ~40 | Unified delta structure |
| Wiring code | ~30 | Connect components |

**Total addition:** ~180 lines of integration code

**Net change:** -500 lines (reduction in codebase complexity)

---

### Benefits of Merge

| Benefit | Details |
|:--------|:--------|
| **Transaction safety** | CycleExecutor already handles rollback |
| **Escalation** | When stuck, escalate to human |
| **Timeout** | Prevent infinite iteration loops |
| **Parallel compute** | CascadeExecutor uses ThreadPoolExecutor |
| **Progress tracking** | UI can show recalculation progress |
| **Mature schemas** | Proposal/ValidationResult are battle-tested |
| **Multi-level explanation** | Brief → Expert levels from NarrativeGenerator |
| **500 fewer lines** | Less code to maintain |

---

### Risks of Merge

| Risk | Mitigation |
|:-----|:-----------|
| Schema mismatch | Create adapter layer (`GeometryProposal`) |
| Testing gap | Run existing CycleExecutor tests + **add geometry-specific tests** (see below) |
| Feature regression | Keep NEW path functional during migration |
| Scope creep | Time-box to **20 hours**, defer P2 items |
| **Rollback behavior** | Verify `program_executor` can undo partial state changes (see below) |

---

### ⚠️ Critical Gap: Geometry-Specific Tests for CycleExecutor

Existing `CycleExecutor` tests cover parameter proposals, **not geometry DSL**. New tests required:

```python
# tests/integration/test_cycle_executor_geometry.py

def test_cycle_executor_geometry_proposal_success():
    """CycleExecutor handles successful geometry proposal."""
    proposal = GeometryProposal(
        program_text="""
            CREATE geometry.section bow { station: 0.0, points: [[0,0], [1,-0.5], [1,0.5]] }
            CREATE geometry.section mid { station: 0.5, points: [[0,0], [2,-1], [2,1]] }
            CREATE geometry.body main { section_ids: ["bow", "mid"] }
        """
    )
    result = executor.execute_cycle(proposal, agent_callback=auto_approve)
    assert result["status"] == "approved"
    assert "geometry" in result

def test_cycle_executor_geometry_proposal_validation_failure():
    """CycleExecutor handles geometry that fails validation."""
    proposal = GeometryProposal(
        program_text="""
            CREATE geometry.body main { section_ids: [] }  # No sections = invalid
        """
    )
    result = executor.execute_cycle(proposal, agent_callback=auto_revise)
    assert result["status"] in ("revised", "escalated", "aborted")

def test_cycle_executor_geometry_rollback():
    """CycleExecutor rolls back partial geometry on failure."""
    state_before = state_manager.to_dict()
    proposal = GeometryProposal(
        program_text="""
            CREATE geometry.section s1 { station: 0.0, points: [[0,0]] }
            CREATE geometry.section INVALID { }  # Will fail
        """
    )
    result = executor.execute_cycle(proposal, agent_callback=auto_abort)
    state_after = state_manager.to_dict()
    assert state_after == state_before  # Rollback successful

def test_cycle_executor_geometry_transaction_commit():
    """CycleExecutor commits geometry only after full validation."""
    proposal = GeometryProposal(program_text="CREATE geometry.body main {}")
    
    # During validation, state should be tentative
    # After approval, state should be committed
    result = executor.execute_cycle(proposal, agent_callback=auto_approve)
    
    assert result["status"] == "approved"
    assert state_manager.get("resources.geometry.body.main") is not None
```

---

### ⚠️ Critical Gap: Rollback Behavior for Geometry

**Question:** Does `program_executor` support rollback?

**Current behavior:**
```python
# program_executor.py
def execute_program(program_text: str, state_manager: StateManager, dry_run: bool = False):
    if dry_run:
        state_copy = copy.deepcopy(state_manager._state)
        # Apply to copy, don't commit
    else:
        # Apply directly — NO ROLLBACK IF FAILS MID-WAY
```

**Problem:** If geometry compile fails after 5 of 10 actions, the first 5 are already applied.

**Required fix before merge:**
```python
def execute_program(program_text: str, state_manager: StateManager, dry_run: bool = False):
    # Always work on a copy first
    working_state = copy.deepcopy(state_manager._state)
    
    try:
        # Parse, expand, apply to working_state
        result = _execute_on_state(program_text, working_state)
        
        if not dry_run and result.success:
            # Only commit if everything succeeded
            state_manager._state = working_state
        
        return result
    except Exception as e:
        # working_state is discarded, original state untouched
        return ExecutionResult(success=False, errors=[str(e)])
```

**Verification test:**
```python
def test_program_executor_atomic():
    """Program execution is atomic — all or nothing."""
    state = StateManager()
    state.set("test_key", "original")
    
    program = """
        SET test_key = "modified"
        CREATE geometry.section INVALID { }  # Will fail
    """
    result = execute_program(program, state, dry_run=False)
    
    assert not result.success
    assert state.get("test_key") == "original"  # Rolled back
```

---

### Migration Order

```
Phase 1 (4h): Mount orphaned routers
   └── create_agents_router, create_interior_router, create_routing_router

Phase 2 (6h): Replace PropagationEngine
   ├── Create GeometryCalculator
   ├── Register in CalculatorRegistry
   └── Wire to CascadeExecutor

Phase 3 (4h): Adapt CycleExecutor
   ├── Create GeometryProposal
   ├── Add DSL validation branch
   └── Update DesignConversation to use CycleExecutor

Phase 4 (2h): Merge feedback generation
   ├── Add templates to NarrativeGenerator
   └── Wire ChatFormatter
```

---

### Decision Matrix (Revised)

| Option | Effort | Code Quality | Risk | Recommendation |
|:-------|:-------|:-------------|:-----|:---------------|
| **A: Wire existing only** | 8h | Good | Low | Quick win |
| **B: Keep new, delete orphans** | 4h | Fair | Medium | Tech debt |
| **C: Merge best of both** | **20h** | Excellent | Medium | Best long-term |

**Verdict:** Option C delivers the cleanest architecture but Option A is the pragmatic choice if time-constrained. Option B should be avoided — it discards production-hardened code for newer, less-tested implementations.

---

### ✅ Architectural Alignment Confirmation

| Goal Component | Audit Coverage | Status |
|:---------------|:---------------|:-------|
| Human-in-the-loop spiral | CycleExecutor + ClarificationManager | ✅ |
| Trillions of forms via primitives | GeometryProposal uses DSL, not enums | ✅ |
| Kernel validates physics, not intent | program_executor unchanged | ✅ |
| Structured feedback for iteration | NarrativeGenerator + EnrichedDelta | ✅ |
| Change propagation | CascadeExecutor replaces PropagationEngine | ✅ |
| No enumeration | GeometryCalculator bridges to existing infra | ✅ |

#### Contract Preservation

The `CycleExecutor` integration preserves the core contract:

```python
if isinstance(proposal, GeometryProposal):
    exec_result = program_executor.execute_program(
        proposal.program_text,
        self.state,
        dry_run=True,
    )
```

**Why this is correct:**
- `CycleExecutor` wraps iteration (propose → validate → revise)
- `CycleExecutor` does NOT inject design knowledge
- `program_executor` compiles geometry, then validates physics
- The kernel's role remains: validate reality, not recognize intent

#### Cross-Reference with Existing Docs

| Document | Section | Audit Alignment |
|:---------|:--------|:----------------|
| `MAGNET_System_State_Analysis.md` | Part VIII (Design Spiral) | ✅ CycleExecutor implements propose→validate→revise |
| `MAGNET_System_State_Analysis.md` | Part XIV (Propagation) | ✅ CascadeExecutor replaces custom PropagationEngine |
| `MAGNET_Implementation_Guide.md` | Phase 5-6 | ✅ program_executor remains the compile path |
| Invariant tests | 20/20 passing | ✅ Merge doesn't touch kernel/stdlib — tests stay valid |

---

### ⚠️ Risk to Monitor: CalculatorRegistry Enumeration

The existing `CascadeExecutor` uses `CalculatorRegistry` which may contain calculators that read `hull_type` or `HullFamily`.

**When wiring `GeometryCalculator`, verify:**

```python
# ✅ CORRECT — calls program_executor (verified: zero HullFamily references)
class GeometryCalculator:
    def __call__(self, state_manager, param):
        program = state_manager.get("design_program")
        return program_executor.execute_program(program, state_manager)

# ❌ WRONG — would reintroduce enumeration
class GeometryCalculator:
    def __call__(self, state_manager, param):
        hull_type = state_manager.get("hull.hull_type")  # ← FORBIDDEN
        if hull_type == "catamaran":  # ← ENUMERATION
            ...
```

**Verification command:**
```bash
# Run before and after wiring GeometryCalculator
grep -rn "hull_type\|HullFamily\|HullType" magnet/dependencies/cascade.py
grep -rn "hull_type\|HullFamily\|HullType" magnet/dependencies/calculator*.py
```

**Expected result:** Zero matches in any new calculator code.

**Invariant test to add:**
```python
def test_geometry_calculator_no_enumeration():
    """GeometryCalculator must not reference hull types."""
    import inspect
    from magnet.dependencies.calculator import GeometryCalculator
    
    source = inspect.getsource(GeometryCalculator)
    assert "hull_type" not in source.lower()
    assert "hullfamily" not in source.lower()
    assert "hulltype" not in source.lower()
```

**Contract:** As long as `GeometryCalculator` calls `program_executor` (which has zero `HullFamily` references per invariant test `test_program_executor_never_imports_hull_families`), the architectural contract holds.

---

## Part XIII: Pre-Merge Checklist

Before starting Option C implementation, verify these prerequisites:

### ☐ 1. Verify `program_executor` Atomicity

```bash
# Check current rollback behavior
grep -n "deepcopy\|rollback\|tentative" magnet/kernel/program_executor.py
```

**Expected:** State changes are atomic (all succeed or all fail)
**If missing:** Implement copy-then-commit pattern before merge

### ☐ 2. Verify CycleExecutor Transaction Support

```bash
# Check transaction integration
grep -n "begin_tentative\|commit\|rollback" magnet/protocol/cycle_executor.py
```

**Expected:** Lines 127-134 show transaction begin, lines 167, 192 show commit, lines 205, 212, 224 show rollback

### ☐ 3. Verify DependencyGraph Completeness

```bash
# Check if geometry paths are in the graph
grep -n "geometry\." magnet/dependencies/graph.py
```

**Expected:** May be missing — will need to add geometry paths to `PHASE_OWNERSHIP`

### ☐ 4. Create Geometry Test Fixtures

Before adapting CycleExecutor, create test fixtures:

```python
# tests/fixtures/geometry_proposals.py

VALID_SINGLE_HULL = GeometryProposal(
    program_text="""
        CREATE geometry.section bow { station: 0.0, points: [[0,0], [1,-0.5], [1,0.5]] }
        CREATE geometry.section mid { station: 0.5, points: [[0,0], [2,-1], [2,1]] }
        CREATE geometry.section stern { station: 1.0, points: [[0,0], [1.5,-0.7], [1.5,0.7]] }
        CREATE geometry.body main { section_ids: ["bow", "mid", "stern"] }
    """
)

VALID_TWIN_HULL = GeometryProposal(
    program_text="""
        CREATE geometry.section bow { station: 0.0, points: [[0,0], [0.5,-0.3], [0.5,0.3]] }
        CREATE geometry.section stern { station: 1.0, points: [[0,0], [0.5,-0.3], [0.5,0.3]] }
        CREATE geometry.body port { section_ids: ["bow", "stern"], offset_y_m: -4.0 }
        CREATE geometry.body stbd { section_ids: ["bow", "stern"], offset_y_m: 4.0 }
    """
)

INVALID_EMPTY_BODY = GeometryProposal(
    program_text="""CREATE geometry.body main { section_ids: [] }"""
)

INVALID_MISSING_SECTION = GeometryProposal(
    program_text="""CREATE geometry.body main { section_ids: ["nonexistent"] }"""
)
```

### ☐ 5. Verify Existing CycleExecutor Tests Pass

```bash
python -m pytest tests/ -k "cycle_executor" -v
```

**Expected:** All existing tests pass before any modifications

### ☐ 6. Document Current Test Coverage

```bash
# Check what CycleExecutor tests exist
find tests -name "*.py" -exec grep -l "CycleExecutor" {} \;
```

**Note coverage gaps** for geometry-specific scenarios.

---

## Part XIV: Implementation Sequence (Option C)

### Week 1: Foundation (Days 1-2)

| Day | Task | Hours | Deliverable |
|:----|:-----|:------|:------------|
| 1 AM | Mount orphaned routers | 0.5h | 3 new API routes working |
| 1 PM | Verify program_executor atomicity | 2h | Test passes or fix implemented |
| 1 PM | Add geometry paths to DependencyGraph | 2h | `PHASE_OWNERSHIP` includes geometry |
| 2 AM | Create geometry test fixtures | 2h | 4+ test fixtures ready |
| 2 PM | Write geometry-specific CycleExecutor tests | 3h | Tests exist (will fail initially) |

### Week 1: Core Merge (Days 3-4)

| Day | Task | Hours | Deliverable |
|:----|:-----|:------|:------------|
| 3 AM | Create `GeometryProposal` class | 1h | Extends Proposal |
| 3 AM | Add DSL branch to `CycleExecutor._run_validation()` | 3h | Geometry proposals validate |
| 3 PM | Create `GeometryCalculator` for registry | 2h | Bridges program_executor |
| 4 AM | Wire `CascadeExecutor` to geometry | 3h | Cascade works for geometry changes |
| 4 PM | Implement `DIRECTION_POLARITY` config | 1h | 40+ metrics configured |

### Week 2: Integration (Day 5)

| Day | Task | Hours | Deliverable |
|:----|:-----|:------|:------------|
| 5 AM | Create `EnrichedDelta` class | 1h | Unified delta structure |
| 5 AM | Merge `generate_feedback` into `NarrativeGenerator` | 2h | Geometry templates added |
| 5 PM | Update `DesignConversation` to use `CycleExecutor` | 2h | Chat uses existing infrastructure |
| 5 PM | Integration testing | 5h | All 13 phases work with geometry |

### Week 2: Cleanup (Day 6)

| Day | Task | Hours | Deliverable |
|:----|:-----|:------|:------------|
| 6 | Delete `PropagationEngine` | 0.5h | ~580 lines removed |
| 6 | Delete inline `PHASE_DEPS` | 0.5h | Use DependencyGraph |
| 6 | Delete `generate_feedback()` | 0.5h | Use NarrativeGenerator |
| 6 | Final test run | 2h | All tests pass |
| 6 | Documentation update | 1h | Update MAGNET_System_State_Analysis.md |

**Total: ~20.5 hours over 6 working days**

---

## Part XV: Implementation Plan Reference

The detailed implementation plan has been extracted to:

**`MAGNET_Merge_Implementation_Plan.md`**

### Quick Reference

| Phase | Day | Focus | Hours |
|:------|:----|:------|:------|
| 0 | 1 AM | Mount routers, verify atomicity, rollback tests | 2.5h |
| 0 | 1 PM | Add geometry to DependencyGraph | 2h |
| 1 | 2 | Create GeometryProposal + fixtures | 5h |
| 2 | 3 | Adapt CycleExecutor for geometry | 5h |
| 3 | 4 | Wire CascadeExecutor + EnrichedDelta (50+ metrics) | 4h |
| 4 | 5 AM | Merge feedback into NarrativeGenerator | 2h |
| 5 | 5 PM | Update DesignConversation + ClarificationManager | 3h |
| 6 | 6 | Cleanup + final testing | 4h |
| **Total** | | | **~22.5h** |

### Gaps Addressed in v2

| Gap | Resolution |
|:----|:-----------|
| Rollback test missing | Added 3 rollback tests in Phase 0.2 |
| METRIC_POLARITY incomplete | Expanded to 50+ metrics in Phase 4 |
| ClarificationManager not wired | Added to Phase 6 with full integration |

### The Test (Must Pass)

1. ☐ Stepped ventilated planing hull from primitives — NO "stepped hull" type
2. ☐ Twin hull vessel from primitives — NO "catamaran" type  
3. ☐ Novel configuration validates — NO new code required

### Files to Create

| File | Purpose |
|:-----|:--------|
| `magnet/glue/protocol/schemas.py` | Add `GeometryProposal` |
| `magnet/dependencies/geometry_calculator.py` | Bridge to CascadeExecutor |
| `magnet/kernel/metric_polarity.py` | Direction computation |
| `magnet/kernel/enriched_delta.py` | Unified delta structure |
| `tests/fixtures/geometry_proposals.py` | Test fixtures |

### Files to Modify

| File | Change |
|:-----|:-------|
| `magnet/deployment/api.py` | Mount 3 orphaned routers |
| `magnet/kernel/program_executor.py` | Ensure atomic execution |
| `magnet/dependencies/graph.py` | Add geometry paths |
| `magnet/protocol/cycle_executor.py` | Add DSL branch |
| `magnet/explain/narrative.py` | Add geometry templates |
| `magnet/agents/design_conversation.py` | Wire to CycleExecutor |

### Files to Delete

| File | Lines | Reason |
|:-----|:------|:-------|
| `magnet/kernel/propagation.py` | ~580 | Replaced by CascadeExecutor |

---

*This audit identifies components that are complete and tested but not connected to the NEW geometry primitives path. The implementation plan in `MAGNET_Merge_Implementation_Plan.md` provides a concrete 6-day execution path to wire these components and achieve the stated goal.*

