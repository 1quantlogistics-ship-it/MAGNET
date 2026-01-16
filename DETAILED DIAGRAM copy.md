# MAGNETV1 DETAILED ARCHITECTURE DIAGRAM
## Comprehensive Codebase Analysis — January 15, 2026

---

# TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Directory Structure & File Counts](#2-directory-structure--file-counts)
3. [Module Dependency Graph](#3-module-dependency-graph)
4. [Core Layer](#4-core-layer)
5. [Kernel Layer](#5-kernel-layer)
6. [Physics Layer](#6-physics-layer)
7. [Hull Generation Pipeline](#7-hull-generation-pipeline)
8. [WebGL/Visualization Pipeline](#8-webglvisualization-pipeline)
9. [Validators & Taxonomy](#9-validators--taxonomy)
10. [API Endpoints](#10-api-endpoints)
11. [Agents Layer](#11-agents-layer)
12. [Data Flow Diagrams](#12-data-flow-diagrams)
13. [State Management](#13-state-management)
14. [Constants & Configuration](#14-constants--configuration)
15. [Test Organization](#15-test-organization)
16. [Key Formulas & Algorithms](#16-key-formulas--algorithms)

---

# 1. EXECUTIVE SUMMARY

| Metric | Count |
|--------|-------|
| **Total Python Files** | 633 |
| **magnet/ modules** | 449 files |
| **tests/ files** | 181 files |
| **Validator Implementations** | 19 |
| **API Endpoints** | 35+ |
| **Design State Sections** | 27 |
| **Design Phases** | 10 |
| **Physical Constants** | 100+ |

**Largest Modules:**
| Module | Size | Purpose |
|--------|------|---------|
| `kernel/synthesis.py` | 78KB | Hull generation engine |
| `deployment/api.py` | 3,400+ lines | REST API |
| `kernel/conductor.py` | 1,128 lines | Phase orchestration |
| `physics/validators.py` | 2,000+ lines | Physics validation |

---

# 2. DIRECTORY STRUCTURE & FILE COUNTS

```
/Users/bengibson/MAGNETV1/
├── magnet/                              (449 Python files)
│   ├── agents/                          (9 files)
│   │   ├── clarification.py             — ClarificationAgent, ClarificationManager
│   │   ├── design_conversation.py       — DesignConversation, Message
│   │   ├── geometry_proposer.py         — GeometryProposer, GeometryOperation
│   │   ├── vision_interpreter.py        — VisionInterpreter, SketchInterpretation
│   │   ├── state_lens.py                — StateLens (read-only state view)
│   │   ├── llm_client.py                — LLMClient interface
│   │   ├── factory.py                   — AgentFactory
│   │   └── ...
│   │
│   ├── analysis/                        (7 files)
│   │   ├── seakeeping.py                — Seakeeping analysis
│   │   ├── noise_vibration.py           — Noise/vibration analysis
│   │   └── reports.py                   — Analysis report generation
│   │
│   ├── arrangement/                     (4 files)
│   │   ├── generator.py                 — ArrangementGenerator
│   │   ├── models.py                    — Compartment, Tank, DeckLayout
│   │   └── validators.py                — ArrangementValidator
│   │
│   ├── bootstrap/                       (6 files)
│   │   ├── app.py                       — AppContext, application init
│   │   ├── container.py                 — Service container
│   │   └── config.py                    — LLMConfig, APIConfig, StorageConfig
│   │
│   ├── cli/                             (4 files)
│   │   └── main.py                      — Command-line interface
│   │
│   ├── compliance/                      (7 files)
│   │   ├── validators.py                — ComplianceValidator, StabilityComplianceValidator
│   │   └── rule_engine.py               — Class society rules
│   │
│   ├── contracts/                       (5 files)
│   │   └── interfaces.py                — Protocol definitions
│   │
│   ├── control_plane/                   (7 files)
│   │   ├── explain/                     — ExplainRecord, provenance tracking
│   │   ├── query_routing.py             — WHY system routing
│   │   └── narrative.py                 — Natural language explanations
│   │
│   ├── core/                            (14 files)
│   │   ├── design_state.py              — DesignState (27 sections)
│   │   ├── state_manager.py             — StateManager, DimensionProvenance
│   │   ├── dataclasses.py               — 34 dataclasses (MissionConfig, HullState, etc.)
│   │   ├── enums.py                     — 15 domain enums
│   │   ├── constants.py                 — 100+ physical constants
│   │   ├── phase_states.py              — PhaseMachine
│   │   ├── unit_converter.py            — UnitConverter (44+ conversions)
│   │   ├── field_aliases.py             — Path normalization
│   │   ├── refinable_schema.py          — 20+ refinable paths
│   │   └── parameter_bounds.py          — Validation bounds
│   │
│   ├── cost/                            (5 files)
│   │   ├── schema.py                    — CostBreakdown, CostCategory
│   │   ├── estimators.py                — Cost estimation models
│   │   └── validators.py                — CostValidator
│   │
│   ├── dependencies/                    (8 files)
│   │   ├── graph.py                     — DependencyGraph, DependencyNode
│   │   ├── invalidation.py              — Mark stale validators
│   │   ├── revalidation.py              — Re-run affected validators
│   │   └── cascade.py                   — Propagate changes downstream
│   │
│   ├── deployment/                      (9 files)
│   │   ├── api.py                       — FastAPI routes (35+ endpoints)
│   │   ├── design_store.py              — Design persistence
│   │   ├── websocket.py                 — WebSocket manager
│   │   └── intent_parser.py             — Parse user intents
│   │
│   ├── errors/                          (4 files)
│   │   ├── taxonomy.py                  — Error classification
│   │   ├── aggregator.py                — Error collection
│   │   └── recovery.py                  — Error recovery strategies
│   │
│   ├── explain/                         (5 files)
│   │   ├── schemas.py                   — ExplainRecord, ExplainSource
│   │   ├── narrative.py                 — Human-readable explanations
│   │   └── trace.py                     — Provenance trace
│   │
│   ├── hull_gen/                        (16 files, includes modifiers/)
│   │   ├── generator.py                 — HullGenerator (main entry)
│   │   ├── geometry.py                  — HullGeometry, HullSection
│   │   ├── parameters.py                — HullDefinition, MainDimensions
│   │   ├── bow_generator.py             — BowGenerator (specialized bows)
│   │   ├── deck_generator.py            — DeckGenerator (Phase 6)
│   │   ├── transom_generator.py         — TransomGenerator
│   │   ├── nurbs.py                     — NURBS surface generation
│   │   └── modifiers/                   (5 files)
│   │       ├── spray_rail.py            — SprayRailModifier
│   │       ├── knuckle.py               — KnuckleModifier
│   │       └── tumblehome.py            — TumblehomeModifier (Phase 6)
│   │
│   ├── interior/                        (2 files)
│   │   ├── schema/space.py              — Space, Compartment schemas
│   │   └── generator/layout_generator.py — LayoutGenerator
│   │
│   ├── kernel/                          (35 files, includes stdlib/, priors/)
│   │   ├── conductor.py                 — Conductor (phase orchestration)
│   │   ├── synthesis.py                 — HullSynthesizer (78KB)
│   │   ├── program_executor.py          — ProgramExecutor (design language)
│   │   ├── action_executor.py           — ActionExecutor
│   │   ├── action_validator.py          — ActionPlanValidator (LLM firewall)
│   │   ├── propagation.py               — ChangePropagate
│   │   ├── registry.py                  — PhaseRegistry (10 phases)
│   │   ├── validator.py                 — KernelValidator
│   │   ├── orchestrator.py              — ValidationOrchestrator
│   │   ├── session.py                   — SessionState
│   │   ├── intent_protocol.py           — IntentResolver, ActionPlan
│   │   ├── events.py                    — 21 typed events
│   │   ├── event_dispatcher.py          — EventDispatcher
│   │   ├── enriched_delta.py            — EnrichedDelta
│   │   ├── synthesis_lock.py            — SynthesisLock (concurrency)
│   │   ├── sanity_guardrails.py         — Safety checks
│   │   ├── metric_polarity.py           — Maximize/minimize tracking
│   │   ├── analysis.py                  — AnalysisEngine
│   │   ├── enums.py                     — PhaseStatus, GateCondition
│   │   ├── schema.py                    — PhaseResult, GateResult
│   │   ├── stdlib/                      (10 files)
│   │   │   ├── ast_nodes.py             — AST: Statement, CreateStatement, etc.
│   │   │   ├── parser.py                — Design language parser
│   │   │   ├── compiler.py              — AST → kernel actions
│   │   │   ├── section_compiler.py      — Section compilation
│   │   │   ├── expander.py              — Macro expansion
│   │   │   ├── policies.py              — Quality policies
│   │   │   ├── quality_gates.py         — Post-compilation checks
│   │   │   └── type_registry.py         — Type/field schemas
│   │   └── priors/                      (3 files)
│   │       ├── hull_families.py         — HullFamily (DEPRECATED)
│   │       └── geometry_defaults.py     — get_defaults_from_froude() (PREFERRED)
│   │
│   ├── lifecycle/                       (4 files)
│   │   ├── manager.py                   — DesignLifecycleManager
│   │   └── versions.py                  — Version tracking
│   │
│   ├── llm/                             (4+ files)
│   │   ├── provider_factory.py          — LLM provider factory
│   │   ├── services.py                  — LLM services
│   │   └── prompts.py                   — Prompt templates
│   │
│   ├── loading/                         (4 files)
│   │   ├── calculator.py                — LoadingCalculator
│   │   ├── models.py                    — LoadCase, Tank
│   │   └── validators.py                — LoadingComputerValidator
│   │
│   ├── optimization/                    (8 files)
│   │   ├── pareto.py                    — ParetoOptimizer
│   │   ├── sensitivity.py               — SensitivityAnalysis
│   │   ├── schema.py                    — OptimizationProblem
│   │   └── validator.py                 — OptimizationValidator
│   │
│   ├── outfitting/                      (11 files)
│   │   ├── systems.py                   — System integration
│   │   ├── furniture.py                 — Furniture placement
│   │   └── openings.py                  — Universal primitives (openings)
│   │
│   ├── performance/                     (7 files)
│   │   ├── envelope.py                  — Performance envelope
│   │   ├── predictor.py                 — Performance prediction
│   │   └── resistance.py                — High-level resistance interface
│   │
│   ├── physics/                         (10 files)
│   │   ├── validators.py                — HydrostaticsValidator, ResistanceValidator
│   │   ├── geometry_hydrostatics.py     — compute_hydrostatics_from_geometry()
│   │   ├── multi_body_hydrostatics.py   — Multi-body (parallel axis theorem)
│   │   ├── polygon_ops.py               — Polygon clipping, area, centroid
│   │   ├── resistance.py                — Holtrop-Mennen calculator
│   │   ├── savitsky.py                  — Savitsky planing calculator
│   │   ├── equilibrium.py               — Newton-Raphson draft solver
│   │   └── uncertainty.py               — Phase 4 uncertainty schema
│   │
│   ├── production/                      (10 files)
│   │   ├── assembly.py                  — Assembly sequencing
│   │   ├── coatings.py                  — Coating system
│   │   ├── scheduling.py                — Production scheduling
│   │   └── validators.py                — ProductionPlanningValidator
│   │
│   ├── protocol/                        (5 files)
│   │   └── schema.py                    — Protocol definitions
│   │
│   ├── reporting/                       (4+ files)
│   │   ├── exporters.py                 — Report exporters (PDF, HTML)
│   │   ├── generators.py                — Report generators
│   │   └── validator.py                 — ReportingValidator
│   │
│   ├── routing/                         (35+ files)
│   │   ├── router/                      — Macro-routing algorithms
│   │   │   ├── trunk_router.py          — Main trunk routing
│   │   │   ├── steiner_router.py        — Steiner tree routing
│   │   │   ├── capacity_calc.py         — Capacity calculations
│   │   │   └── path_optimizer.py        — Path optimization
│   │   └── agent/routing_agent.py       — Routing agent
│   │
│   ├── stability/                       (10 files)
│   │   ├── validators.py                — IntactGMValidator, GZCurveValidator
│   │   ├── gz_curve.py                  — GZ curve calculations
│   │   ├── damage.py                    — Damage stability
│   │   └── weather.py                   — Weather criterion
│   │
│   ├── structural/                      (13 files)
│   │   ├── scantlings.py                — Scantling calculations
│   │   ├── plates.py                    — Plating
│   │   ├── stiffeners.py                — Stiffener design
│   │   └── welds.py                     — Weld design
│   │
│   ├── systems/                         (1+ files)
│   │   └── (safety, propulsion, electrical, HVAC, fuel)
│   │
│   ├── transactions/                    (3 files)
│   │   ├── manager.py                   — TransactionManager
│   │   └── schemas.py                   — Transaction definitions
│   │
│   ├── ui/                              (8 files)
│   │   ├── components/                  — UI components
│   │   ├── chat/                        — Chat interface
│   │   └── dashboard/                   — Dashboard views
│   │
│   ├── ui_v2/                           (Frontend - static assets)
│   │   └── js/scene-manager.js          — 3D scene rendering
│   │
│   ├── validators/                      (9 files)
│   │   ├── taxonomy.py                  — ValidatorInterface, ValidatorCategory
│   │   ├── registry.py                  — ValidatorRegistry
│   │   ├── executor.py                  — PipelineExecutor
│   │   ├── aggregator.py                — ResultAggregator
│   │   ├── topology.py                  — Phase→validator mapping
│   │   ├── contracts.py                 — Validator protocols
│   │   └── builtin.py                   — Built-in validator lookup
│   │
│   ├── vision/                          (7 files)
│   │   ├── hull_forms.py                — Hull form recognition
│   │   ├── geometry.py                  — Geometry extraction
│   │   ├── snapshots.py                 — Snapshot management
│   │   └── renderer.py                  — Vision rendering
│   │
│   ├── webgl/                           (22 files)
│   │   ├── geometry_pipeline.py         — HullGeometryPipeline (tessellation)
│   │   ├── mesh_builder.py              — MeshBuilder
│   │   ├── geometry_adapter.py          — Adapt geometry to WebGL
│   │   ├── serializer.py                — glTF serialization
│   │   ├── gltf_builder.py              — glTF/GLB builder
│   │   ├── exporter.py                  — GeometryExporter
│   │   ├── materials.py                 — Material system
│   │   ├── geometry_service.py          — Geometry service (metadata export)
│   │   └── dependency_integration.py    — Geometry change hooks
│   │
│   └── weight/                          (10 files)
│       ├── validators.py                — WeightEstimationValidator
│       ├── estimator.py                 — Weight estimation
│       ├── groups.py                    — Weight groups
│       └── stability.py                 — Weight-stability coupling
│
├── tests/                               (181 Python files)
│   ├── unit/                            (78 files)
│   ├── integration/                     (25 files)
│   ├── physics/                         — Physics tests
│   ├── stability/                       — Stability tests
│   ├── hull_gen/                        — Hull generation tests
│   ├── webgl/                           — WebGL tests
│   ├── validation/                      — Validation tests
│   ├── invariants/                      — Invariant tests
│   └── fixtures/                        — Test fixtures
│
├── app/                                 (Frontend - Node.js/TypeScript)
├── deployment/                          (Docker configs)
├── docs/                                (Architecture, theory, guides)
├── plugins/                             (Extension system - Pelorus)
├── scripts/                             (3 utility scripts)
└── storage/                             (Design persistence)
```

---

# 3. MODULE DEPENDENCY GRAPH

## 3.1 High-Level Architecture

```
                                    ┌─────────────────────┐
                                    │     USER INPUT      │
                                    │   (Web UI / CLI)    │
                                    └──────────┬──────────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │     DEPLOYMENT      │
                                    │      api.py         │
                                    │  (35+ endpoints)    │
                                    └──────────┬──────────┘
                                               │
              ┌────────────────────────────────┼────────────────────────────────┐
              │                                │                                │
    ┌─────────▼─────────┐           ┌─────────▼─────────┐           ┌─────────▼─────────┐
    │      AGENTS       │           │   CONTROL PLANE   │           │     BOOTSTRAP     │
    │  clarification    │           │   explain/        │           │     app.py        │
    │  geometry_proposer│           │   query_routing   │           │    container.py   │
    │  vision_interpreter│          │   narrative       │           │    config.py      │
    └─────────┬─────────┘           └─────────┬─────────┘           └─────────┬─────────┘
              │                               │                               │
              └───────────────────────────────┼───────────────────────────────┘
                                              │
                                   ┌──────────▼──────────┐
                                   │       KERNEL        │◄─── Primary Orchestration
                                   │    conductor.py     │     (1128 lines)
                                   │    synthesis.py     │     (78KB - largest)
                                   │  program_executor   │
                                   │  action_executor    │
                                   │  action_validator   │◄─── LLM Firewall
                                   └──────────┬──────────┘
                                              │
              ┌───────────────────────────────┼───────────────────────────────┐
              │                               │                               │
    ┌─────────▼─────────┐          ┌─────────▼─────────┐          ┌─────────▼─────────┐
    │       CORE        │          │    VALIDATORS     │          │   DEPENDENCIES    │
    │   design_state    │          │     registry      │          │      graph        │
    │   state_manager   │          │     executor      │          │   invalidation    │
    │   dataclasses     │          │    aggregator     │          │   revalidation    │
    │     enums         │          │     topology      │          │     cascade       │
    │   constants       │          └─────────┬─────────┘          └─────────┬─────────┘
    └─────────┬─────────┘                    │                              │
              │                              │                              │
              └──────────────────────────────┼──────────────────────────────┘
                                             │
              ┌──────────────────────────────┼──────────────────────────────┐
              │                              │                              │
    ┌─────────▼─────────┐         ┌─────────▼─────────┐         ┌─────────▼─────────┐
    │      PHYSICS      │         │     HULL_GEN      │         │       WEBGL       │
    │geometry_hydrostatics│        │    generator      │         │  geometry_pipeline │
    │   validators      │         │    geometry       │         │   mesh_builder    │
    │   resistance      │         │   parameters      │         │    exporter       │
    │    savitsky       │         │  bow_generator    │         │   serializer      │
    │  polygon_ops      │         │  deck_generator   │         │  gltf_builder     │
    │  equilibrium      │         │    modifiers/     │         │    materials      │
    │  uncertainty      │         └───────────────────┘         └───────────────────┘
    └───────────────────┘
```

## 3.2 Detailed Import Dependencies

```
deployment/api.py
    ├── bootstrap/app.py
    │   └── bootstrap/container.py
    │       └── bootstrap/config.py (LLMConfig, APIConfig)
    │
    ├── kernel/conductor.py
    │   ├── kernel/synthesis.py
    │   │   ├── kernel/priors/hull_families.py (DEPRECATED)
    │   │   └── kernel/priors/geometry_defaults.py (PREFERRED)
    │   ├── kernel/program_executor.py
    │   │   └── kernel/stdlib/* (parser, compiler, ast_nodes)
    │   ├── kernel/action_executor.py
    │   └── kernel/action_validator.py
    │
    ├── validators/registry.py
    │   ├── validators/taxonomy.py (ValidatorInterface)
    │   ├── validators/executor.py (PipelineExecutor)
    │   └── [19 validator implementations]
    │
    ├── core/state_manager.py
    │   ├── core/design_state.py
    │   ├── core/dataclasses.py
    │   └── core/enums.py
    │
    ├── dependencies/graph.py
    │   ├── dependencies/invalidation.py
    │   └── dependencies/revalidation.py
    │
    ├── physics/* (hydrostatics, resistance, savitsky)
    │   └── core/constants.py
    │
    └── webgl/* (pipeline, builder, exporter)
```

---

# 4. CORE LAYER

## 4.1 DesignState (27 Sections)

**File:** `magnet/core/design_state.py`

```python
@dataclass
class DesignState:
    # Identity
    design_id: str
    design_name: str
    version: str = "1.19.0"          # Schema version
    design_version: int              # Monotonic counter (mutations)

    # Domain Sections (25)
    1.  mission: MissionConfig           # Vessel mission requirements
    2.  hull: HullState                  # Hull geometry + hydrostatics
    3.  structural_design: StructuralDesign
    4.  structural_loads: StructuralLoads
    5.  propulsion: PropulsionState
    6.  weight: WeightEstimate
    7.  stability: StabilityState        # GM, GZ curve
    8.  loading: LoadingState
    9.  arrangement: ArrangementState
    10. compliance: ComplianceState
    11. production: ProductionState
    12. cost: CostState
    13. optimization: OptimizationState
    14. reports: ReportsState
    15. kernel: KernelState              # Phase orchestration state
    16. analysis: AnalysisState
    17. performance: PerformanceState
    18. systems: SystemsState
    19. outfitting: OutfittingState
    20. environmental: EnvironmentalState
    21. deck_equipment: DeckEquipmentState
    22. vision: VisionState
    23. resistance: ResistanceState      # Resistance + method weights
    24. seakeeping: SeakeepingState
    25. maneuvering: ManeuveringState
    26. electrical: ElectricalState
    27. safety: SafetyState
```

## 4.2 StateManager

**File:** `magnet/core/state_manager.py`

```python
class DimensionProvenance(Enum):
    PLACEHOLDER = "placeholder"      # Ship-scale baseline (NOT authoritative)
    USER = "user"                    # Explicitly set by user
    LLM_PROPOSED = "llm_proposed"   # Proposed by LLM
    SYNTHESIZED = "synthesized"      # Derived by synthesis
    KERNEL = "kernel"                # Set by validators

class StateManager:
    def get(path: str, default=None) -> Any
    def set(path: str, value: Any, source: str = None) -> None
    def exists(path: str) -> bool
    def get_strict(path: str) -> Any  # Raises InvalidPathError
    def is_real_dimension(path: str) -> bool  # Check provenance
    def commit() -> None              # Atomic save
    def rollback() -> None            # Transaction rollback
    def to_dict() -> dict
    def from_dict(data: dict) -> DesignState
```

**Provenance-Tracked Paths:**
- `hull.loa`, `hull.lwl`, `hull.beam`, `hull.draft`, `hull.depth`
- `hull.cb`, `hull.cp`, `hull.cm`, `hull.cwp`
- `hull.deadrise_deg`, `hull.deadrise_transom_deg`
- `hull.bow_style`, `hull.chine_type`, `hull.spray_rail_count`

## 4.3 Constants

**File:** `magnet/core/constants.py` (266 lines)

```python
# Water Properties
SEAWATER_DENSITY_KG_M3 = 1025.0
FRESHWATER_DENSITY_KG_M3 = 1000.0
WATER_KINEMATIC_VISCOSITY = 1.19e-6  # m²/s at 15°C

# Gravity
GRAVITY_M_S2 = 9.81

# Froude Number Thresholds
FN_DISPLACEMENT_MAX = 0.40           # Below: displacement regime
FN_SEMI_DISPLACEMENT_MAX = 0.70      # Below: semi-displacement; Above: planing
FN_HOLTROP_VALID_MAX = 0.40          # Holtrop method valid
FN_HOLTROP_USABLE_MAX = 0.70         # Holtrop approximate

# Block Coefficient Ranges by Regime
CB_PLANING_TYPICAL = (0.35, 0.45)
CB_SEMI_DISPLACEMENT_TYPICAL = (0.45, 0.55)
CB_DISPLACEMENT_TYPICAL = (0.55, 0.85)

# Stability (IMO A.749)
GM_MIN_PASSENGER = 0.35              # m
GM_MIN_CARGO = 0.15                  # m
GM_MIN_WORKBOAT = 0.50               # m
AREA_0_30_MIN = 0.055                # m-rad
AREA_0_40_MIN = 0.090                # m-rad
GZ_AT_30_MIN = 0.20                  # m

# Geometry Tolerances (MAGNET Standard)
EPSILON_MESH = 1e-6                  # Vertex merging
EPSILON_GEOMETRY = 1e-10             # Integration/zero-checks
EPSILON_CONVERGENCE = 1e-4           # Iterative solvers
EPSILON_VECTOR = 1e-10               # Vector normalization
EPSILON_PARAMETER = 1e-10            # NURBS parameter clamping

# System Versions
DESIGN_STATE_VERSION = "1.19.0"
MAGNET_VERSION = "1.0.0"

# Limits
MAX_LOA_M = 500.0
MIN_LOA_M = 1.0
MAX_SPEED_KTS = 100.0
```

---

# 5. KERNEL LAYER

## 5.1 Conductor (Phase Orchestration)

**File:** `magnet/kernel/conductor.py` (1,128 lines)

```python
class Conductor:
    """
    Manages phase execution, gate evaluation, and session state.
    """

    def __init__(
        self,
        state_manager: StateManager,
        registry: PhaseRegistry,
        pipeline_executor: PipelineExecutor,
        result_aggregator: ResultAggregator
    )

    # Session Management
    def create_session(design_id: str) -> Session

    # Phase Execution
    def run_phase(phase_name: str, context: dict = None) -> PhaseResult
    def run_all_phases() -> List[PhaseResult]
    def run_to_phase(target_phase: str) -> List[PhaseResult]
    def run_from_phase(start_phase: str) -> List[PhaseResult]

    # Hull Generation (Two Paths)
    def _run_program_generation() -> HullGeometry    # NEW: design language
    def _run_hull_synthesis() -> HullGeometry        # LEGACY: HullFamily

    # Gate Management
    def approve_gate(gate_name: str) -> bool

    # Human Decision Point
    def _check_human_decision_point() -> bool

    # Refinement (CLI v1)
    def apply_refinement(path: str, op: str, amount: float) -> ActionResult
```

**Phase Execution Flow:**
```
run_phase(phase_name)
    │
    ├── 1. Check dependencies (prerequisite phases)
    │
    ├── 2. Hull generation hook (if hull phase, first entry)
    │   ├── NEW PATH: design_program → execute_program()
    │   └── LEGACY PATH: HullFamily → HullSynthesizer.synthesize()
    │
    ├── 3. Input contract validation (Guardrail #5)
    │
    ├── 4. Execute validators via PipelineExecutor (Guardrail #2)
    │
    ├── 5. Output contract check (Guardrail #1)
    │
    ├── 6. Gate evaluation
    │   └── If human_decision_required → return BLOCKED
    │
    └── 7. Return PhaseResult (status, errors, warnings)
```

## 5.2 Synthesis Engine

**File:** `magnet/kernel/synthesis.py` (78KB — largest module)

```python
@dataclass
class SynthesisRequest:
    """DEPRECATED (TASK-003) — use GeometrySynthesisRequest"""
    hull_family: HullFamily           # DEPRECATED
    max_speed_kts: float              # Required
    loa_m: Optional[float]
    payload_kg: Optional[float]
    crew_count: Optional[int]
    range_nm: Optional[float]
    gm_min_m: Optional[float] = 0.5
    max_iterations: int = 15

@dataclass
class GeometrySynthesisRequest:
    """PREFERRED (TASK-003 compliant) — physics-derived defaults"""
    max_speed_kts: float              # Required
    loa_m: Optional[float]
    beam_m: Optional[float]
    draft_m: Optional[float]
    crew_count: Optional[int]
    payload_kg: Optional[float]
    range_nm: Optional[float]
    gm_min_m: Optional[float] = 0.5

@dataclass
class SynthesisProposal:
    # Principal dimensions
    lwl: float
    beam: float
    draft: float
    depth: float

    # Form coefficients
    cb: float
    cp: float
    cm: float
    cwp: float

    # Computed
    displacement_m3: float
    confidence: float
    source: DimensionProvenance

class TerminationReason(Enum):
    CONVERGED = "converged"
    MAX_ITERATIONS = "max_iterations"
    NO_FEASIBLE = "no_feasible"
    FALLBACK_MODE = "fallback_mode"

@dataclass
class SynthesisResult:
    proposal: SynthesisProposal
    termination: TerminationReason
    iterations_used: int
    score_history: List[float]
    validator_results: List[ValidatorResult]
    is_usable: bool

class HullSynthesizer:
    def synthesize(request: SynthesisRequest) -> SynthesisResult
    def synthesize_from_geometry(request: GeometrySynthesisRequest) -> SynthesisResult
```

**Optimization Loop:**
```
1. Initialize: Froude → family prior OR physics defaults → initial proposal
2. Score: Run validators, aggregate results
3. Mutate: Adjust form parameters based on scores
4. Converge Check: If stable or max_iterations → terminate
5. Fallback: If no feasible solution → activate FallbackMode
```

## 5.3 Design Language (stdlib/)

**Directory:** `magnet/kernel/stdlib/`

| File | Key Classes | Purpose |
|------|-------------|---------|
| `ast_nodes.py` | `Statement`, `CreateStatement`, `SetStatement`, `LoftStatement` | AST definitions |
| `parser.py` | `Parser`, `Lexer` | Parse design language → AST |
| `compiler.py` | `Compiler`, `CompilationResult` | Compile AST → kernel actions |
| `section_compiler.py` | `SectionCompiler` | Section-level compilation |
| `expander.py` | `Expander`, `ExpansionResult` | Macro expansion |
| `policies.py` | `PolicyContract` | Quality policies |
| `quality_gates.py` | `QualityWarning` | Post-compilation checks |
| `type_registry.py` | `TypeSchema`, `FieldSchema` | Type definitions |

**AST Statement Types:**
- `CreateStatement` — Create hull form primitive
- `UpdateStatement` — Modify existing element
- `DeleteStatement` — Remove element
- `SetStatement` — Set parameter (`SET hull.beam = 5.0`)
- `LoftStatement` — Loft surface between sections
- `MirrorStatement` — Mirror geometry
- `AlignStatement` — Align elements
- `ConstrainStatement` — Add constraint
- `DeriveStatement` — Derive property
- `AskStatement` — Request user clarification

## 5.4 Priors

**Directory:** `magnet/kernel/priors/`

**geometry_defaults.py (PREFERRED):**
```python
def get_defaults_from_froude(froude_number: float) -> dict:
    """
    Physics-derived defaults based on Froude number.

    Returns:
        cb, cp, cm, cwp, deadrise_deg, lwl_beam, beam_draft

    Regime interpolation:
        - Fn < 0.40: Displacement
        - 0.40 ≤ Fn < 0.70: Semi-displacement
        - Fn ≥ 0.70: Planing
    """

def get_defaults_from_dimensions(loa, beam, draft) -> dict
def estimate_lightship_kg(dimensions: dict) -> float
def get_displacement_bounds(regime: str) -> tuple
```

**hull_families.py (DEPRECATED):**
```python
class HullFamily(Enum):
    PATROL = "patrol"
    WORKBOAT = "workboat"
    FERRY = "ferry"
    PLANING = "planing"
    CATAMARAN = "catamaran"

def get_family_prior(family: HullFamily) -> dict
def calculate_froude(speed_kts: float, lwl_m: float) -> float
def get_regime_adjusted_prior(family: HullFamily, froude: float) -> dict
```

---

# 6. PHYSICS LAYER

## 6.1 Module Overview

**Directory:** `magnet/physics/` (10 files)

| File | Key Functions/Classes | Purpose |
|------|----------------------|---------|
| `validators.py` | `HydrostaticsValidator`, `ResistanceValidator` | Physics validation |
| `geometry_hydrostatics.py` | `compute_hydrostatics_from_geometry()` | Geometry-based hydrostatics |
| `multi_body_hydrostatics.py` | Multi-body support | Parallel axis theorem |
| `polygon_ops.py` | `clip_polygon_z_le()`, `polygon_area_centroid()` | Polygon operations |
| `resistance.py` | `ResistanceCalculator` | Holtrop-Mennen method |
| `savitsky.py` | `SavitskyCalculator` | Planing resistance |
| `equilibrium.py` | `solve_equilibrium_draft()` | Newton-Raphson draft solver |
| `uncertainty.py` | `Uncertainty`, `make_uncertainty()` | Phase 4 uncertainty schema |

## 6.2 Hydrostatics

**File:** `magnet/physics/geometry_hydrostatics.py`

**CRITICAL PRINCIPLE:** "body_count is a geometric fact, NOT a design classification"

```python
def compute_hydrostatics_from_geometry(
    geometry: HullGeometry,
    draft: float,
    vcg: Optional[float] = None,
    seawater_density: float = 1025.0
) -> HydrostaticsResult:
    """
    Compute hydrostatics from actual geometry sections.

    Single-body: Direct integration
    Multi-body: Parallel axis theorem
    """
```

**HydrostaticsResult Fields:**
```python
@dataclass
class HydrostaticsResult:
    # Buoyancy
    displacement_m3: float
    displacement_kg: float
    lcb_m: float                      # Longitudinal center of buoyancy
    vcb_m: float                      # Vertical center of buoyancy
    tcb_m: float                      # Transverse center of buoyancy

    # Stability
    kb_m: float                       # Keel to center of buoyancy
    bm_transverse_m: float            # Transverse metacentric radius
    bm_longitudinal_m: float          # Longitudinal metacentric radius
    gm_transverse_m: Optional[float]  # Transverse GM (if vcg provided)
    gm_longitudinal_m: Optional[float]

    # Waterplane
    waterplane_area_m2: float
    waterplane_inertia_transverse_m4: float
    waterplane_inertia_longitudinal_m4: float

    # Wetted Surface
    wetted_surface_m2: float

    # Method Info
    method: str                       # "single_body" | "multi_body_parallel_axis"
    body_count: int
    confidence: str                   # "high" | "medium" | "low"
    stable: bool                      # True unless GM < 0
    warnings: List[str]
```

**Internal Functions:**
```
_count_bodies_in_geometry() → body_count from body_id attributes
_infer_section_centerline_y() → y0 per body (for mirroring)
_section_points_to_full_polygon_yz() → Mirror about y=y0 (NOT y=0)
_integrate_displacement_and_centers() → (volume, lcb, vcb, tcb) via Simpson/Trapezoid
_integrate_waterplane_properties() → (area, Ix, Iy) with parallel axis
_integrate_wetted_surface() → wetted_surface via trapezoid
_apply_primitive_volume_corrections() → Phase 3B void/buoyancy corrections
```

## 6.3 Polygon Operations

**File:** `magnet/physics/polygon_ops.py` (205 lines)

**Coordinate Convention:**
- (y, z) plane — transverse × vertical
- y+ = port
- z+ = up from baseline

```python
def normalize_polygon(vertices: List[Vertex2]) -> List[Vertex2]:
    """Remove duplicates, ensure closure, ensure CCW winding."""

def signed_area(vertices: List[Vertex2]) -> float:
    """Shoelace formula: 0.5 × Σ(y_i × z_{i+1} - y_{i+1} × z_i)"""

def clip_polygon_z_le(vertices: List[Vertex2], z_max: float) -> List[Vertex2]:
    """Sutherland–Hodgman clipping for z ≤ z_max (waterline clipping)."""

def polygon_area_centroid(vertices: List[Vertex2]) -> Tuple[float, float, float]:
    """Green's theorem → (area, cy, cz)"""

def polygon_second_moments(vertices: List[Vertex2]) -> Tuple[float, float, float]:
    """Planar moments: (Iy, Iz, Iyz) = (∫y²dA, ∫z²dA, ∫yz dA)"""
```

## 6.4 Resistance (Holtrop-Mennen)

**File:** `magnet/physics/resistance.py`

```python
class ResistanceCalculator:
    def calculate(
        lwl: float,
        beam: float,
        draft: float,
        displacement_m3: float,
        wetted_surface_m2: float,
        speed_kts: float,
        cb: float,
        cp: float,
        cm: float,
        lcb_fraction: float = 0.5
    ) -> ResistanceResult
```

**Output Fields:**
- `total_kn`, `total_n` — Total resistance
- `frictional_kn`, `residuary_kn`, `appendage_kn`, `air_kn` — Components
- `effective_power_kw`, `effective_power_hp`
- `froude_number`, `reynolds_number`
- `cf`, `cr`, `ct`, `form_factor`
- `regime` — "displacement" | "semi_displacement" | "planing"
- `method_valid`, `validity_note`

**Formulas:**
```
Fn = V / √(g × LWL)
Rn = V × LWL / ν

Cf = 0.075 / (log₁₀(Rn) - 2)²  [ITTC-57]

(1+k₁) = 0.93 + 0.487118 × c₁₄ × (B/L)^1.06806 × (T/L)^0.46106
         × (L/∇^(1/3))^0.121563 × (L³/∇)^0.36486 × (1-Cp)^(-0.604247)

Ct = Cf × (1+k₁) + Cr + Ca
Rt = Ct × 0.5 × ρ × V² × S
Pe = Rt × V
```

## 6.5 Resistance (Savitsky Planing)

**File:** `magnet/physics/savitsky.py`

```python
class SavitskyCalculator:
    def calculate(inputs: SavitskyInputs) -> SavitskyResults
```

**Key Methods:**
```
_solve_trim_and_lambda() → (tau_deg, lambda, x_cp_m)
    Uses bisection to solve Savitsky CL0 equation

_solve_lambda_for_cl0(cl0_req, tau_deg, Cv) → λ
    CL0 = τ^1.1 × (0.0120×√λ + 0.0055×λ^2.5/Cv²)

_apply_deadrise_lift(cl0, beta_deg) → cl_beta
    cl_beta = cl0 - 0.0065 × β × cl0^0.6

_invert_deadrise_lift(cl_beta, beta_deg) → cl0
    Fixed-point iteration (12 iterations)
```

**Validity Checks:**
- Fn_b = V / √(g×b) ≥ 1.0
- Deadrise 10°–30° typical
- λ ∈ [1, 6]

## 6.6 Equilibrium Draft Solver

**File:** `magnet/physics/equilibrium.py`

```python
def solve_equilibrium_draft(
    geometry: HullGeometry,
    target_displacement_mt: float,
    draft_guess_m: float,
    depth_m: float,
    seawater_density: float = 1025.0,
    tol_residual_mt: float = 0.01,
    tol_draft_m: float = 1e-4,
    max_iter: int = 25
) -> EquilibriumSolution
```

**Algorithm:**
1. Bracket search: Find draft interval where residual changes sign
2. Newton-Raphson: d(Disp)/dT ≈ ρ × Aw(T)
3. Bisection fallback: If Newton fails, use bisection

**Result:**
```python
@dataclass
class EquilibriumSolution:
    converged: bool
    draft_m: float
    iterations: int
    residual_mt: float
    best_draft_m: float
    best_abs_residual_mt: float
    reason: str
```

## 6.7 Uncertainty Schema (Phase 4)

**File:** `magnet/physics/uncertainty.py`

```python
@dataclass(frozen=True)
class Uncertainty:
    value_pct: float                  # ± percentage (e.g., 12.0 = ±12%)
    level: str                        # LOW/MED/HIGH/EXTREME
    basis: str                        # Model + assumptions
    validity_envelope: str            # Human-readable validity range
    novelty_impact: str = ""          # Novel primitives not modeled
    details: Optional[Dict] = None

def make_uncertainty(
    value_pct: float,
    basis: str,
    validity_envelope: str,
    novelty_impact: str = "",
    details: Optional[Dict] = None
) -> Dict[str, Any]

def novelty_impact_from_state_resources(resources: Any) -> str:
    """
    Detect universal primitives and report impact.

    IF explicit semantics (void_volume_m3, buoyancy_volume_m3):
        → "treat GM as advisory when primitives are present"
    ELSE:
        → "diagnostic-only and may ignore their effects"
    """
```

---

# 7. HULL GENERATION PIPELINE

## 7.1 Overview

**Directory:** `magnet/hull_gen/` (16 files)

```
HullDefinition (parameters.py)
    │
    ▼
HullGenerator (generator.py)
    ├── _generate_sections()
    │   ├── _generate_monohull_sections()
    │   │   ├── _generate_standard_sections() [traditional bow]
    │   │   └── _generate_sections_with_bow() [specialized bow]
    │   └── _generate_catamaran_sections()
    │       └── _generate_demihull_section()
    │
    ├── _generate_waterlines()
    ├── _generate_keel_profile()
    ├── _generate_stem_profile()
    ├── _generate_chine_curve()
    ├── _generate_transom()
    │
    └── Section Modifiers (applied in order):
        ├── SprayRailModifier
        ├── KnuckleModifier
        └── TumblehomeModifier (Phase 6)
            │
            ▼
        HullGeometry
```

## 7.2 HullGenerator

**File:** `magnet/hull_gen/generator.py`

```python
class HullGenerator:
    def __init__(self):
        self._section_modifiers = [
            SprayRailModifier(),
            KnuckleModifier(),
            TumblehomeModifier(),  # Phase 6
        ]

    def generate(definition: HullDefinition) -> HullGeometry
```

**Section Type Dispatch:**
| ChineType | Method |
|-----------|--------|
| ROUND | `_generate_round_section()` |
| SINGLE | `_generate_chine_section()` |
| MULTI | `_generate_multi_chine_section()` |
| REVERSE | `_generate_reverse_chine_section()` |
| VARIABLE | `_generate_variable_chine_section()` |
| BLENDED | `_generate_blended_chine_section()` |
| DEFAULT | `_generate_generic_section()` |

## 7.3 HullGeometry Output

**File:** `magnet/hull_gen/geometry.py`

```python
@dataclass
class HullGeometry:
    hull_id: str

    # Sections (transverse curves)
    sections: List[HullSection]

    # Waterlines (longitudinal curves at fixed z)
    waterlines: List[Waterline]

    # Key profiles
    keel_profile: List[Point3D]
    stem_profile: List[Point3D]
    chine_curve: List[Point3D]
    transom_outline: List[Point3D]

    # Phase 5: Transom edges
    transom_hard_edges: List[Tuple[int, int, str]]

    # Phase 4: Longitudinal features
    longitudinal_features: List[LongitudinalFeature]

    # Phase 6: Deck surface
    deck_geometry: Optional[DeckGeometry]

    # Computed properties
    volume_m3: float
    waterplane_area_m2: float
    wetted_surface_m2: float

@dataclass
class SectionPoint:
    position: Point3D
    normal: Optional[Point3D]
    curvature: float
    is_chine: bool
    is_keel: bool
    edge_type: EdgeType              # SMOOTH, HARD, CREASE
    crease_angle_deg: float
    feature_id: Optional[str]
```

## 7.4 Parameters

**File:** `magnet/hull_gen/parameters.py`

```python
@dataclass
class MainDimensions:
    loa: float                        # Length overall (m)
    lwl: float                        # Length waterline (m)
    lpp: float                        # Length between perpendiculars (m)
    beam_max: float                   # Maximum beam (m)
    beam_wl: float                    # Beam at waterline (m)
    beam_chine: float                 # Beam at chine (m)
    depth: float                      # Depth (m)
    draft: float                      # Design draft (m)
    draft_fwd: float                  # Draft forward (m)
    draft_aft: float                  # Draft aft (m)
    freeboard_bow: float              # Freeboard at bow (m)
    freeboard_mid: float              # Freeboard at midships (m)
    freeboard_stern: float            # Freeboard at stern (m)

@dataclass
class FormCoefficients:
    cb: float                         # Block coefficient
    cp: float                         # Prismatic coefficient
    cm: float                         # Midship coefficient
    cwp: float                        # Waterplane coefficient
    lcb_fraction: float               # LCB as % of LWL

class HullType(Enum):
    MONOHULL, CATAMARAN, TRIMARAN, SWATH, PLANING, FAST_DISPLACEMENT

class ChineType(Enum):
    ROUND, SINGLE, MULTI, REVERSE, VARIABLE, BLENDED

class BowStyle(Enum):
    TRADITIONAL, SPOON, RAKED, BULBOUS, CLIPPER

class TransomType(Enum):
    VERTICAL, RAKED, TRANSOM_BOW
```

---

# 8. WEBGL/VISUALIZATION PIPELINE

## 8.1 Overview

**Directory:** `magnet/webgl/` (22 files)

```
HullGeometry (sections with edge_type)
    │
    ▼
HullGeometryPipeline (geometry_pipeline.py)
    ├── tessellate()              [authoritative]
    ├── tessellate_by_body()      [multi-body, enum-free]
    ├── tessellate_parametric()   [visual-only]
    └── tessellate_with_options() [faceted, panel_edges_hard, deck]
        │
        ▼
    _tessellate_from_sections()
        ├── _build_port_meshes()
        └── _build_starboard_meshes() [if multi-body]
            │
            ▼
        MeshBuilder (mesh_builder.py)
            ├── add_vertex(x, y, z, edge_type)
            ├── add_triangle(v0, v1, v2)
            ├── mark_hard_edge(v0, v1)
            └── build()
                ├── _compute_split_normals() [hard edges]
                └── compute_vertex_normals() [smooth]
                    │
                    ▼
                MeshData
                    │
                    ▼
GeometryExporter (exporter.py)
    ├── export() → ExportResult
    │   ├── _export_gltf(binary=True)  → GLB
    │   ├── _export_gltf(binary=False) → GLTF
    │   ├── _export_stl(binary=True)   → STL binary
    │   ├── _export_stl(binary=False)  → STL ASCII
    │   └── _export_obj()              → OBJ
    │
    ▼
ExportResult
    ├── success: bool
    ├── data: bytes
    ├── metadata: ExportMetadata
    └── errors, warnings: List[str]
```

## 8.2 HullGeometryPipeline

**File:** `magnet/webgl/geometry_pipeline.py`

```python
class HullGeometryPipeline:
    def tessellate() -> MeshData
        """Tessellate authoritative hull geometry."""

    def tessellate_by_body() -> Dict[str, MeshData]
        """
        Multi-body enum-free tessellation.
        Partitions sections by body_id attribute.
        Returns one MeshData per body.
        """

    def tessellate_parametric() -> MeshData
        """Visual-only approximation (no authoritative geometry)."""

    def tessellate_with_options(
        faceted: bool = False,
        panel_edges_hard: bool = False,
        deck_geometry: Optional[DeckGeometry] = None
    ) -> MeshData
        """Phase 6: Enhanced tessellation with options."""
```

## 8.3 MeshBuilder

**File:** `magnet/webgl/mesh_builder.py`

```python
class MeshBuilder:
    def add_vertex(x, y, z, edge_type=EdgeType.SMOOTH) -> int
    def add_vertex_with_normal(x, y, z, nx, ny, nz, edge_type=SMOOTH) -> int
    def add_triangle(v0, v1, v2)
    def add_quad(v0, v1, v2, v3)  # Two triangles
    def mark_hard_edge(v0, v1)    # [v1.2] For split normals
    def build(compute_normals=True) -> MeshData
```

**Normal Computation:**
- **Smooth:** Average face normals at each vertex
- **Split (hard edges):** Duplicate vertices at hard edges, separate normals per face group

## 8.4 GeometryExporter

**File:** `magnet/webgl/exporter.py`

```python
@dataclass
class ExportMetadata:
    # Traceability (FM8)
    export_id: str
    design_id: str
    exported_at: str
    schema_version: str = "1.1.0"
    geometry_version: int
    source_branch: str
    commit_hash: Optional[str]

    # Export details
    format: str                       # "gltf" | "glb" | "stl" | "obj"
    lod: str                          # "low" | "medium" | "high"
    geometry_mode: str                # "authoritative" | "parametric"

    # Statistics
    vertex_count: int
    face_count: int
    file_size_bytes: int

    # Coordinate system
    units: str = "meters"
    up_axis: str = "Z"
    forward_axis: str = "X"

class GeometryExporter:
    def set_version_info(branch: str, commit_hash: str)
    def export(mesh, format, design_id, lod, geometry_mode) -> ExportResult
```

---

# 9. VALIDATORS & TAXONOMY

## 9.1 Validator Base Classes

**File:** `magnet/validators/taxonomy.py`

```python
class ValidatorCategory(Enum):
    PHYSICS, BOUNDS, CLASS_RULES, STABILITY, WEIGHT,
    ARRANGEMENT, LOADING, REGULATORY, PRODUCTION,
    ECONOMICS, OPTIMIZATION, REPORTING, CUSTOM

class ValidatorPriority(Enum):
    CRITICAL = 1      # Blocks phase advancement
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5

class ValidatorState(Enum):
    PENDING, RUNNING, PASSED, FAILED, WARNING,
    STALE, SKIPPED, ERROR, BLOCKED, NOT_IMPLEMENTED

class GateRequirement(Enum):
    REQUIRED          # Must pass for gate
    OPTIONAL          # Informational only
    INFORMATIONAL

class ResultSeverity(Enum):
    ERROR = "error"           # Blocks advancement
    WARNING = "warning"       # Advisory
    PREFERENCE = "preference" # "Could be better" (v1.4)
    INFO = "info"
    PASSED = "passed"

@dataclass
class ValidatorDefinition:
    id: str
    name: str
    category: ValidatorCategory
    priority: ValidatorPriority
    dependencies: List[str]
    resource_requirements: ResourceRequirements

class ValidatorInterface(Protocol):
    def validate(state_manager: StateManager) -> ValidatorResult
```

## 9.2 All 19 Validator Implementations

| Validator ID | Class | File:Line | Category | Phase | Severity |
|--------------|-------|-----------|----------|-------|----------|
| `physics/hydrostatics` | `HydrostaticsValidator` | `physics/validators.py:189` | PHYSICS | hull | **CRITICAL (GATE)** |
| `physics/resistance` | `ResistanceValidator` | `physics/validators.py:873` | PHYSICS | hull | NORMAL |
| `physics/equilibrium_draft` | `EquilibriumDraftValidator` | `physics/validators.py:1891` | PHYSICS | weight | HIGH |
| `bounds/proportional_harmony` | `ProportionalHarmonyValidator` | `physics/validators.py:1631` | BOUNDS | hull | NORMAL |
| `stability/intact_gm` | `IntactGMValidator` | `stability/validators.py:50` | STABILITY | stability | **CRITICAL** |
| `stability/gz_curve` | `GZCurveValidator` | `stability/validators.py:273` | STABILITY | stability | **CRITICAL** |
| `stability/damage` | `DamageStabilityValidator` | `stability/validators.py:439` | STABILITY | stability | HIGH |
| `stability/weather_criterion` | `WeatherCriterionValidator` | `stability/validators.py:611` | STABILITY | stability | HIGH |
| `weight/estimation` | `WeightEstimationValidator` | `weight/validators.py:57` | WEIGHT | weight | **CRITICAL** |
| `weight/stability` | `WeightStabilityValidator` | `weight/validators.py:466` | WEIGHT | weight | HIGH |
| `loading/computer` | `LoadingComputerValidator` | `loading/validators.py:33` | LOADING | loading | HIGH |
| `arrangement/generator` | `ArrangementValidator` | `arrangement/validators.py:31` | ARRANGEMENT | arrangement | NORMAL |
| `compliance/regulatory` | `ComplianceValidator` | `compliance/validators.py:60` | CLASS_RULES | compliance | **CRITICAL (GATE)** |
| `compliance/stability` | `StabilityComplianceValidator` | `compliance/validators.py:216` | CLASS_RULES | compliance | HIGH |
| `production/planning` | `ProductionPlanningValidator` | `production/validators.py:60` | PRODUCTION | production | NORMAL |
| `cost/estimation` | `CostValidator` | `cost/validators.py:34` | ECONOMICS | cost | NORMAL |
| `optimization/pareto` | `OptimizationValidator` | `optimization/validator.py:49` | OPTIMIZATION | optimization | NORMAL |
| `reporting/generator` | `ReportingValidator` | `reporting/validator.py:27` | REPORTING | reports | NORMAL |
| `kernel/bounds` | `KernelValidator` | `kernel/validator.py:55` | BOUNDS | mission | HIGH |

## 9.3 Validator Dependency Graph

```
physics/hydrostatics (GATE)
    │
    ├──▶ physics/resistance
    │       (depends on: displacement, lwl, beam, draft, wetted_surface)
    │
    ├──▶ physics/equilibrium_draft
    │       (depends on: hydrostatics, weight)
    │
    └──▶ stability/intact_gm
            (depends on: kb, bm, vcg)
            │
            ├──▶ stability/gz_curve
            │       (depends on: displacement, geometry)
            │
            ├──▶ stability/damage
            │
            └──▶ stability/weather_criterion
                    │
                    ▼
            weight/estimation
            weight/stability
                    │
                    ▼
            arrangement/generator
            loading/computer
                    │
                    ▼
            compliance/regulatory (GATE)
            production/planning
            cost/estimation
```

## 9.4 Validator Registry

**File:** `magnet/validators/registry.py`

```python
class ValidatorRegistry:
    _validator_classes: Dict[str, Type[ValidatorInterface]]
    _instances: Dict[str, ValidatorInterface]

    def register_class(validator_id: str, cls: Type)
    def get_instance(validator_id: str) -> ValidatorInterface
    def validate_required_implementations()  # Fail hard if missing
```

---

# 10. API ENDPOINTS

## 10.1 Complete Endpoint List

**File:** `magnet/deployment/api.py` (3,400+ lines)

### System Routes
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Health check |
| GET | `/ready` | Readiness check (includes conductor state) |

### Metadata
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/meta` | System metadata |

### Design Management (7 endpoints)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/designs` | List all designs |
| POST | `/api/v1/designs` | Create new design |
| GET | `/api/v1/designs/{design_id}` | Get design state |
| PATCH | `/api/v1/designs/{design_id}` | Update design values |
| DELETE | `/api/v1/designs/{design_id}` | Delete design |
| POST | `/api/v1/designs/{design_id}/undo` | Undo last change |
| POST | `/api/v1/designs/{design_id}/versions/{version}/restore` | Restore version |

### Phase Management (5 endpoints)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/designs/{design_id}/phases` | List phases and status |
| GET | `/api/v1/designs/{design_id}/phases/{phase}` | Get phase details |
| POST | `/api/v1/designs/{design_id}/phases/{phase}/run` | Execute phase |
| POST | `/api/v1/designs/{design_id}/phases/{phase}/validate` | Validate phase |
| POST | `/api/v1/designs/{design_id}/phases/{phase}/approve` | Approve gate |

### State Explanation (5 endpoints)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/designs/{design_id}/explain/{path:path}` | Why is value X? |
| GET | `/api/v1/designs/{design_id}/history/{path:path}` | Value history |
| GET | `/api/v1/designs/{design_id}/impact/{version}` | What changed? |
| GET | `/api/v1/designs/{design_id}/explain/latest` | Latest explanation |
| POST | `/api/v1/designs/{design_id}/why` | Natural language query |

### Background Jobs (2 endpoints)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/jobs` | Submit background job |
| GET | `/api/v1/jobs/{job_id}` | Get job status |

### Rendering/Reports (3 endpoints)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/designs/{design_id}/render` | Generate 3D model (WebGL) |
| POST | `/api/v1/designs/{design_id}/reports` | Generate report |
| POST | `/api/v1/design/sketch` | Interpret sketch/image |

### Design Language (6 endpoints)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/program` | Compile design program |
| POST | `/api/v1/propose` | LLM proposes actions (preview) |
| POST | `/api/v1/propose-and-execute` | Propose and execute |
| POST | `/api/v1/propagate` | Propagate changes downstream |
| POST | `/api/v1/design/chat` | Chat conversation |
| GET | `/api/v1/design/chat/{conversation_id}/summary` | Chat summary |
| GET | `/api/v1/design/chat/{conversation_id}/history` | Chat history |

### WebSocket
| Method | Endpoint | Purpose |
|--------|----------|---------|
| WS | `/ws/{design_id}` | Real-time updates |

### UI Routes
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Root redirect |
| GET | `/ui/v2` | UI v2 index |
| GET | `/ui/v2/` | UI v2 with trailing slash |

## 10.2 Request/Response Models

```python
class DesignCreate(BaseModel):
    name: str
    mission: Optional[MissionConfig]
    vessel_type: Optional[str]

class DesignUpdate(BaseModel):
    path: str
    value: Any

class PhaseRun(BaseModel):
    phases: Optional[List[str]]
    max_iterations: int = 15
    async_mode: bool = False

class ActionSubmit(BaseModel):
    plan_id: str
    intent_id: str
    design_version_before: int
    actions: List[LLMActionProposal]

class LLMActionProposal(BaseModel):
    action_type: str  # SET, INCREASE, DECREASE, etc.
    path: Optional[str]
    value: Optional[Any]
    amount: Optional[float]
    unit: Optional[str]
```

---

# 11. AGENTS LAYER

## 11.1 Agent Types

**Directory:** `magnet/agents/`

| Agent | File | Purpose |
|-------|------|---------|
| `ClarificationAgent` | `clarification.py` | Manage user clarifications |
| `DesignConversation` | `design_conversation.py` | Multi-turn design conversation |
| `GeometryProposer` | `geometry_proposer.py` | Propose hull geometry changes |
| `VisionInterpreter` | `vision_interpreter.py` | Interpret sketches/images |
| `StateLens` | `state_lens.py` | Read-only state view for agents |
| `LLMClient` | `llm_client.py` | LLM provider interface |
| `AgentFactory` | `factory.py` | Agent instance factory |

## 11.2 Agent Lifecycle

```
1. Creation: AgentFactory.create() or direct instantiation
2. Initialization: Set state context, load configuration
3. Processing: Process user intent, generate candidates
4. Validation: Validate proposals against constraints
5. Execution: Submit approved actions via ActionExecutor
```

## 11.3 Agent Interaction with Kernel

```
Agent
    │
    ├── Read state via StateLens (read-only view)
    │
    ├── Propose actions as ActionPlan
    │
    ├── Submit to ActionPlanValidator (LLM firewall)
    │
    ├── Execute via ActionExecutor
    │
    └── Emit events via EventDispatcher
```

---

# 12. DATA FLOW DIAGRAMS

## 12.1 Design Creation Flow

```
POST /api/v1/designs
    │
    ▼
deployment/api.py:create_design()
    │
    ├── core/state_manager.py:new_design()
    │   └── core/design_state.py (initialize 27 sections)
    │
    ├── kernel/conductor.py:create_session()
    │
    └── deployment/design_store.py (persist)
        │
        ▼
    Return: Full DesignState
```

## 12.2 Phase Execution Flow (Hull Phase)

```
POST /api/v1/designs/{design_id}/phases/hull/run
    │
    ▼
deployment/api.py:run_phase()
    │
    ▼
kernel/conductor.py:run_phase("hull")
    │
    ├── 1. Check dependencies
    │
    ├── 2. Hull generation hook (first entry)
    │   ├── NEW PATH: design_program → execute_program()
    │   │   └── kernel/stdlib/* (parser, compiler)
    │   └── LEGACY PATH: HullFamily → HullSynthesizer.synthesize()
    │       └── kernel/priors/hull_families.py
    │
    ├── 3. Input contract validation
    │
    ├── 4. Execute validators via PipelineExecutor
    │   ├── physics/hydrostatics → geometry_hydrostatics.py
    │   │   ├── _integrate_displacement_and_centers()
    │   │   ├── _integrate_waterplane_properties()
    │   │   └── _apply_primitive_volume_corrections()
    │   │
    │   ├── physics/resistance → resistance.py + savitsky.py
    │   │   └── Sigmoid blending (Phase 2.5)
    │   │
    │   └── bounds/proportional_harmony
    │
    ├── 5. Output contract check
    │
    ├── 6. Gate evaluation
    │   └── If human_decision_required → return BLOCKED
    │
    └── 7. Return PhaseResult
        │
        ▼
    deployment/websocket.py:send_update() (stream changes)
```

## 12.3 Hydrostatics Calculation Flow (Multi-body)

```
INPUT: HullGeometry with sections
    │
    ▼
geometry_hydrostatics.py (SSOT)
    │
    ├── 1. Multi-body detection
    │   └── _count_bodies_in_geometry() → body_count
    │
    ├── 2. Per-body processing
    │   └── _infer_section_centerline_y() → y0 per body
    │
    ├── 3. Section processing
    │   └── _section_points_to_full_polygon_yz()
    │       └── Mirror half-section about y=y0 (NOT y=0)
    │
    ├── 4. Waterline clipping (polygon_ops.py)
    │   └── clip_polygon_z_le(section, z_draft)
    │       └── Sutherland–Hodgman algorithm
    │
    ├── 5. Area/Centroid (Green's theorem)
    │   └── polygon_area_centroid() → (area, cy, cz)
    │
    ├── 6. Integration (Simpson's 1/3)
    │   └── _integrate_1d(xs, fs) → volume, moments
    │
    ├── 7. Second moments + Parallel Axis Theorem
    │   └── I_total = Σ(I_local + A_wp × dy²)
    │
    └── 8. Primitive volume corrections (Phase 3B)
        └── _apply_primitive_volume_corrections()
            │
            ▼
OUTPUT: HydrostaticsResult
    ├── displacement_m3, displacement_kg
    ├── lcb_m, vcb_m, tcb_m
    ├── kb_m, bm_transverse_m, bm_longitudinal_m
    ├── gm_transverse_m (if vcg provided)
    ├── waterplane_area_m2, waterplane_inertia_m4
    ├── wetted_surface_m2
    ├── method: "single_body" | "multi_body_parallel_axis"
    └── body_count, confidence, stable, warnings
```

## 12.4 Resistance Blending Flow (Phase 2.5)

```
INPUT: hull dimensions + speed
    │
    ▼
physics/validators.py::ResistanceValidator
    │
    ├── 1. Calculate Froude Number
    │   └── Fn = V / √(g × LWL)
    │
    ├── 2. Compute BOTH methods
    │   ├── HOLTROP (resistance.py)
    │   │   └── ResistanceCalculator.calculate()
    │   │       ├── Cf = 0.075 / (log₁₀(Rn) - 2)²
    │   │       ├── (1+k₁) = Holtrop form factor
    │   │       └── Ct = Cf × (1+k₁) + Cr + Ca
    │   │
    │   └── SAVITSKY (savitsky.py)
    │       └── SavitskyCalculator.calculate()
    │           ├── Solve trim via bisection
    │           └── CL0 = τ^1.1 × (0.0120×√λ + 0.0055×λ^2.5/Cv²)
    │
    ├── 3. Sigmoid blending
    │   └── w_sav = 1 / (1 + exp(-k × (Fn - Fn_center)))
    │       w_holt = 1 - w_sav
    │
    └── 4. Blend all components
        │
        ▼
OUTPUT:
    resistance.method = "blended"
    resistance.method_weights = {"holtrop": w, "savitsky": w}
    resistance.validity_envelope = "..."
    resistance.outside_envelope = bool
    resistance.extrapolation_flag = bool
    resistance.uncertainty = {...}
```

## 12.5 Universal Primitives Flow (Phase 3)

```
INPUT: Resources with geometry.opening, geometry.flow_path, geometry.attachment
    │
    ▼
uncertainty.py::novelty_impact_from_state_resources()
    │
    ├── Detect primitives
    │   ├── openings = [r for r if _type == "geometry.opening"]
    │   ├── flows = [r for r if _type == "geometry.flow_path"]
    │   └── atts = [r for r if _type == "geometry.attachment"]
    │
    ├── Check explicit semantics
    │   ├── opening_sem_count = count with void_volume_m3
    │   ├── flow_sem_count = count with void_volume_m3
    │   └── att_sem_count = count with buoyancy_volume_m3
    │
    └── Generate novelty_impact message
        │
        ├── IF explicit semantics present:
        │   → "treat GM as advisory when primitives are present"
        │   → "Resistance/weight can incorporate primitives only when
        │      explicit drag/mass semantics supplied (drag_area_m2,
        │      loss_coefficient, mass_kg)"
        │
        └── ELSE (no explicit semantics):
            → "diagnostic-only and may ignore their effects"
                │
                ▼
OUTPUT:
    metadata.primitives.semantics = "diagnostic_only" | "explicit_volume_semantics"
    UI renders: openings as spheres, flow_paths as lines, attachments as spheres
```

## 12.6 Intent→Action Flow (Design Language)

```
POST /api/v1/propose (Design Language)
    │
    ▼
deployment/intent_parser.py:parse_intent()
    │
    ▼
kernel/intent_protocol.py:IntentResolver.resolve()
    │
    ├── Parse intent text → IntentType
    │
    ├── Generate ActionPlan
    │   └── List of Action objects
    │
    └── Validate via ActionPlanValidator (LLM firewall)
        │
        ├── Check bounds
        ├── Check dependencies
        └── Check locked parameters
            │
            ▼
kernel/action_executor.py:ActionExecutor.execute()
    │
    ├── Apply actions atomically
    │
    ├── kernel/propagation.py:ChangePropagate.apply()
    │   └── dependencies/graph.py (invalidate dependents)
    │       └── dependencies/invalidation.py (mark stale)
    │
    └── Return ActionResult
```

## 12.7 WebGL Visualization Flow

```
Geometry update in state_manager
    │
    ▼
webgl/dependency_integration.py:on_geometry_change()
    │
    ▼
webgl/geometry_adapter.py:adapt_to_webgl()
    │
    ▼
webgl/geometry_pipeline.py:tessellate()
    │
    ├── _tessellate_from_sections()
    │   ├── _build_port_meshes()
    │   └── _build_starboard_meshes() [if multi-body]
    │
    └── webgl/mesh_builder.py:build()
        ├── _compute_split_normals() [hard edges]
        └── compute_vertex_normals() [smooth]
            │
            ▼
        MeshData
            │
            ▼
webgl/serializer.py:to_gltf()
    │
    └── webgl/gltf_builder.py
        └── webgl/materials.py (apply colors)
            │
            ▼
        webgl/exporter.py (export GLB)
            │
            ▼
deployment/websocket.py:broadcast_geometry()
    │
    ▼
Frontend (React WebGL viewer)
```

---

# 13. STATE MANAGEMENT

## 13.1 Design Versioning

```python
DesignState:
    design_id: str      # UUID, immutable
    design_name: str
    version: str        # Schema version (e.g., "1.19.0")
    design_version: int # Monotonic counter (increments on commit)
```

## 13.2 Provenance Tracking

```
DimensionProvenance:
    PLACEHOLDER    → Ship-scale baseline (NOT authoritative)
    USER           → Explicitly set by user
    LLM_PROPOSED   → Proposed by LLM
    SYNTHESIZED    → Derived by synthesis
    KERNEL         → Set by validators/clamping
```

## 13.3 Invalidation Cascade

```
dependencies/graph.py
    │
    ├── User changes parameter X
    │
    ├── Find all downstream parameters that depend on X
    │
    ├── dependencies/invalidation.py
    │   └── Mark them as STALE
    │
    ├── Mark phases that own them as INVALIDATED
    │
    └── dependencies/revalidation.py
        └── Run only affected validators on next phase execution
```

## 13.4 Phase Ownership Map

| Phase | Owns Parameters |
|-------|-----------------|
| **mission** | vessel_type, max_speed_kts, cruise_speed_kts, range_nm, crew_berthed, passengers, cargo_capacity_mt |
| **hull_form** | loa, lwl, beam, draft, depth, hull_type, cb, cp, cm, cwp, deadrise_deg, displacement_m3, wetted_surface_m2 |
| **structure** | hull_material, plating_zones, bottom_plating_mm, frame_spacing_mm, longitudinals |
| **arrangement** | deck_layouts, compartments, fuel_tanks, fresh_water_tanks, engine_room_volume_m3 |
| **propulsion** | propulsion_type, num_engines, engine_make, engine_model, engine_power_kw |
| **weight** | lightship_kg, fuel_capacity_l, fw_capacity_l, displacement_mt, lcg_from_ap_m, vcg_from_baseline_m |
| **stability** | displacement_m3, lcg, vcg, lcb, vcb, gm_transverse_m, gm_longitudinal_m, gz_curve_points |
| **compliance** | fail_count, warning_count, class_notations_passed |

---

# 14. CONSTANTS & CONFIGURATION

## 14.1 Physical Constants Summary

| Constant | Value | Unit |
|----------|-------|------|
| `SEAWATER_DENSITY_KG_M3` | 1025.0 | kg/m³ |
| `FRESHWATER_DENSITY_KG_M3` | 1000.0 | kg/m³ |
| `WATER_KINEMATIC_VISCOSITY` | 1.19e-6 | m²/s |
| `GRAVITY_M_S2` | 9.81 | m/s² |
| `FN_DISPLACEMENT_MAX` | 0.40 | — |
| `FN_SEMI_DISPLACEMENT_MAX` | 0.70 | — |
| `GM_MIN_WORKBOAT` | 0.50 | m |
| `AREA_0_30_MIN` | 0.055 | m-rad |
| `EPSILON_GEOMETRY` | 1e-10 | — |

## 14.2 Configuration Classes

**File:** `magnet/bootstrap/config.py`

```python
@dataclass
class LLMConfig:
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    api_key: Optional[str]
    max_tokens: int = 4096
    timeout: int = 120
    rate_limit: int = 60        # req/min
    max_cost: float = 5.00      # $/session
    fallback: bool = True       # Use deterministic fallback

@dataclass
class APIConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str]
    rate_limiting: bool = True

@dataclass
class StorageConfig:
    designs_path: str
    cache_path: str
    exports_path: str
```

---

# 15. TEST ORGANIZATION

## 15.1 Test Structure

```
tests/                               (181 files)
├── unit/                            (78 files)
│   ├── test_kernel_conductor.py
│   ├── test_kernel_session.py
│   ├── test_kernel_registry.py
│   ├── test_kernel_events.py
│   ├── test_kernel_action_validator.py
│   ├── test_state_manager.py
│   ├── test_design_state.py
│   ├── test_validators.py
│   ├── test_physics_*.py
│   ├── test_stability_*.py
│   ├── test_weight_*.py
│   ├── test_hull_gen.py
│   ├── test_arrangement.py
│   ├── test_optimization_*.py
│   ├── test_webgl_*.py
│   ├── test_dependencies_*.py (5 files)
│   └── 30+ more...
│
├── integration/                     (25 files)
│   ├── test_e2e_*.py
│   ├── test_deployment_*.py
│   └── test_kernel_*.py
│
├── physics/                         — Physics validation
│   ├── test_polygon_ops.py
│   ├── test_geometry_hydrostatics_rigor.py
│   └── test_resistance_blending.py
│
├── stability/                       — Stability analysis
├── hull_gen/                        — Hull generation
├── webgl/                           — WebGL serialization
│   └── test_geometry_pipeline.py
│
├── validation/                      — Validation tests
│   └── test_catamaran_reference.py
│
├── invariants/                      — Invariant tests
│   └── test_honest_output_contract.py
│
└── fixtures/                        — Test fixtures
    └── conftest.py
```

## 15.2 Test Markers

```python
@pytest.mark.unit           # Unit tests
@pytest.mark.integration    # Integration tests
@pytest.mark.slow           # Slow tests (excluded by default)
```

## 15.3 Key Test Files

| Test File | Purpose |
|-----------|---------|
| `test_polygon_ops.py` | Polygon clipping, area, centroid |
| `test_geometry_hydrostatics_rigor.py` | Simpson integration, multi-body |
| `test_resistance_blending.py` | Phase 2.5 sigmoid blending |
| `test_catamaran_reference.py` | Parallel axis theorem validation |
| `test_honest_output_contract.py` | Phase 4 uncertainty schema |
| `test_geometry_pipeline.py` | WebGL tessellation |

---

# 16. KEY FORMULAS & ALGORITHMS

## 16.1 Hydrostatics Integration

**Simpson's 1/3 Rule (uniform spacing):**
```
∫f dx ≈ (h/3) × [f₀ + 4×Σf_odd + 2×Σf_even + f_n]
```

**Trapezoid Rule (non-uniform):**
```
∫f dx ≈ Σ 0.5×(f_i + f_{i+1})×Δx_i
```

## 16.2 Polygon Operations

**Sutherland–Hodgman Clipping (z ≤ z_max):**
```
for each edge (s→e):
    if e inside (z ≤ z_max):
        if s outside: add intersection + e
        else: add e
    elif s inside:
        add intersection
return normalized (closed, CCW)
```

**Green's Theorem (area & centroid):**
```
area = 0.5 × Σ(y_i × z_{i+1} - y_{i+1} × z_i)
cy = (1/6A) × Σ(y_i + y_{i+1}) × cross_product
cz = (1/6A) × Σ(z_i + z_{i+1}) × cross_product
```

**Parallel Axis Theorem:**
```
I_total = Σ(I_local + A_wp × d²)
where d = distance from body center to combined center
```

## 16.3 Resistance Calculations

**Froude Number:**
```
Fn = V / √(g × LWL)
```

**Reynolds Number:**
```
Rn = V × LWL / ν
```

**ITTC-57 Friction Coefficient:**
```
Cf = 0.075 / (log₁₀(Rn) - 2)²
```

**Holtrop Form Factor:**
```
(1+k₁) = 0.93 + 0.487118 × c₁₄
         × (B/L)^1.06806 × (T/L)^0.46106
         × (L/∇^(1/3))^0.121563 × (L³/∇)^0.36486
         × (1-Cp)^(-0.604247)

where c₁₄ = 1.0 + 0.011×|LCB_fraction|×100
```

**Total Resistance:**
```
Ct = Cf × (1+k₁) + Cr + Ca
Rt = Ct × 0.5 × ρ × V² × S
Pe = Rt × V
```

**Savitsky Planing Lift:**
```
CL₀ = τ^1.1 × (0.0120×√λ + 0.0055×λ^2.5/Cv²)
where:
    τ = running trim (deg)
    λ = wetted_length / beam
    Cv = speed coefficient
```

**Sigmoid Blending (Phase 2.5):**
```
w_savitsky = 1 / (1 + exp(-k × (Fn - Fn_center)))
w_holtrop = 1 - w_savitsky
```

## 16.4 Equilibrium Draft (Newton-Raphson)

```
1. Bracket search: Find draft interval where residual changes sign
   R(T) = displaced_mass(T) - target_mass

2. Newton-Raphson iteration:
   T_{n+1} = T_n - R(T_n) / R'(T_n)
   where R'(T) ≈ ρ × Aw(T)  [waterplane area]

3. Bisection fallback if Newton fails to converge
```

---

# APPENDIX: VERIFICATION COMMANDS

```bash
# Run key test suites
cd /Users/bengibson/MAGNETV1

# Physics tests
pytest tests/physics/test_polygon_ops.py -v
pytest tests/physics/test_geometry_hydrostatics_rigor.py -v
pytest tests/physics/test_resistance_blending.py -v

# Validation tests
pytest tests/validation/test_catamaran_reference.py -v

# Invariant tests
pytest tests/invariants/test_honest_output_contract.py -v

# WebGL tests
pytest tests/webgl/test_geometry_pipeline.py -v

# Full guide closeout suite
pytest -q tests/test_geometry_hydrostatics.py
pytest -q tests/validation/test_catamaran_reference.py
pytest -q tests/physics/test_geometry_hydrostatics_rigor.py
pytest -q tests/webgl/test_geometry_pipeline.py
pytest -q tests/invariants/test_honest_output_contract.py

# File counts
find magnet -name "*.py" | wc -l    # Expected: 449
find tests -name "*.py" | wc -l     # Expected: 181
```

---

# Document Information

| Field | Value |
|-------|-------|
| **Generated** | January 15, 2026 |
| **Codebase Version** | MAGNETV1 |
| **Schema Version** | 1.19.0 |
| **Total Python Files** | 633 |
| **Validator Count** | 19 |
| **API Endpoints** | 35+ |
| **Design State Sections** | 27 |

---

*This document provides a comprehensive reference for the MAGNETV1 naval architecture codebase, including all modules, validators, API endpoints, data flows, and algorithms.*
