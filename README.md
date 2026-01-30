# MAGNET — Naval Engineering Toolkit

<div align="center">

**A parametric system for vessel design, analysis, and iteration.**

</div>

---

MAGNET is a **parametric naval architecture engine** with deterministic physics modules and a 3D interface. It transforms high-level requirements into validated geometry, layout, routing, and reports.

This repository contains the full implementation of MAGNET V1.5, including:

- **Unified Design State** — 500+ parameters, 27 dataclasses, full serialization
- **Kernel Conductor** — Phase-gated orchestration with dependency resolution
- **Hull Synthesis Engine** — Auto-generates hull from mission parameters with coefficient coupling
- **CLI v1 Infrastructure** — Kernel-first architecture with wired refinement, export, invalidation
- **Physics Engines** — Hydrostatics, stability, resistance, scantlings
- **Interior Spatial Layout System** — Compartment packing, egress validation
- **Systems Macro-Routing Engine** — Piping, electrical, HVAC trunk logic
- **Real-Time Geometry Sync + 3D Viewer** — WebGL with engineering accuracy
- **Validator Graph + Rule Engine** — Classification society compliance
- **Export Pipeline** — glTF, GLB, STL, OBJ, STEP-ready geometry

**MAGNET is not CAD with automation sprinkled on top.**
**It is a design operating system.**

---

## Why MAGNET Exists

Traditional marine design workflows require:

| Pain Point | Reality |
|------------|---------|
| **8+ disconnected tools** | Hull in Rhino, hydro in Maxsurf, structure in Excel, stability in NAPA... |
| **Weeks of iteration** | Every change means re-running 6 different programs |
| **Heavy manual labor** | Copy-paste values between tools, pray nothing breaks |
| **Duplicate data entry** | Enter LOA in 5 different places, hope they match |
| **No central "truth"** | Which file is current? Nobody knows |
| **No intent-level tooling** | Tools don't understand requirements, only button clicks |

**MAGNET replaces all of that with:**

- **One unified design state** — Single source of truth
- **Deterministic physics + constraint solvers** — Engineering checks with explicit gates
- **A live 3D parametric model** — What you see matches what the math calculates
- **Automatic validation and correction** — Catches errors before they compound
- **Streaming updates as the design evolves** — Change propagates through the system

**Users describe what they want → MAGNET figures out how to build it.**

---

## What MAGNET Can Do

### V1.5 — CLI v1 Infrastructure (Current)

| Capability | Status |
|------------|--------|
| Mission interpretation & requirements capture | Complete |
| Hull synthesis from mission parameters | Complete |
| Coefficient coupling (Cb = Cp × Cm enforcement) | Complete |
| Mutation escalation for local optima escape | Complete |
| Per-iteration bounds clamping with ratio preservation | Complete |
| Parametric hull generation (GRM + NURBS) | Complete |
| Full hydrostatics suite (displacement, LCB, BMt, KMt...) | Complete |
| Intact & damage stability (GZ curves, AVS) | Complete |
| Structural scantlings (frames, stringers, plating) | Complete |
| Weight & CG modeling (LCG, VCG, TCG) | Complete |
| Propulsion sizing (Holtrop-Mennen, Savitsky) | Complete |
| Arrangement & compartment layout | Complete |
| Kernel phase orchestration with gates | Complete |
| Classification rule checking (Lloyd's, ABS, DNV-GL, BV) | Complete |
| PREFERENCE severity for "could be better" guidance | Complete |
| Proportional harmony validator | Complete |
| Real-time WebGL 3D visualization | Complete |
| Multi-format geometry export | Complete |
| Engineering packet generation | Complete |
| **CLI v1: Kernel-owned parameter bounds** | Complete |
| **CLI v1: Conductor.apply_refinement() with invalidation** | Complete |
| **CLI v1: run_default_pipeline() safe subset** | Complete |
| **CLI v1: DesignExporter.export_with_phase_report()** | Complete |
| **CLI v1: ClarificationManager ACK lifecycle** | Complete |
| **CLI v1: PhaseMachine internal wiring** | Complete |
| **Intent→Action Protocol foundation** | Complete |
| **ActionPlanValidator (safety firewall)** | Complete |
| **REFINABLE_SCHEMA (20+ refinable paths)** | Complete |
| **UnitConverter (44+ conversion pairs)** | Complete |
| **design_version tracking (stale plan detection)** | Complete |
| **Parameter locks (ephemeral mutation prevention)** | Complete |
| **EventDispatcher (20+ typed kernel events)** | Complete |
| **ActionExecutor (transactional execution)** | Complete |
| **POST /actions endpoint (refinement API)** | Complete |
| **Geometry router wiring + hull_hash** | Complete |
| **set_phase_status() deprecation with PhaseMachine wrapper** | Complete |
| **Kill list cleanup (removed phase append hacks)** | Complete |

### V2 — Concept-to-Preliminary Designer (Roadmap)

All roadmap items below are **future improvements**; see the docs guides for sequencing.

- Multi-candidate exploration with determinism & cost semantics
- Bounded Cp movement for shape character exploration
- Variant generation & comparison
- Optimization (NSGA-II, novelty search)
- Natural language mission briefs
- Sketch/image interpretation
- Automated trade studies

### Future Improvements (Phase 4+)

The remaining roadmap items (e.g., xeokit-sdk visualization, FreeCAD Ship interop, GenCAD firewall) are **future enhancements**.

### V3 — Interior + Systems Intelligence (Roadmap)

- Interior layout engine with spatial packing
- Corridor & egress generation
- Systems macro-routing (piping, electrical, HVAC)
- Walkthrough mode
- Click-anything → get recommendations
- Interactive 3D VisionOS workspace

### V4 — Production-Grade Layout + Routing (Roadmap)

- 3D pipe/cable/duct routing with clash detection
- Bulkhead/deck penetrations & reinforcement
- Full class rule automation
- STEP/IGES CAD export
- Stress overlays & FEA integration
- System redundancy & compliance verification

### V5 — Beyond Marine (Vision)

- AI-BIM for architecture
- Aerospace structural/layout mode
- Ground vehicle design mode
- General engineering design intelligence
- IFC/STEP universal CAD pipeline

---

## How MAGNET Works

MAGNET uses a **modular architecture** where each component is responsible for a domain:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           COMPONENT CLUSTER                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│   │  DIRECTOR   │    │    NAVAL    │    │ STRUCTURAL  │    │   SYSTEMS   │ │
│   │  MODULE     │    │  ARCHITECT  │    │  ENGINEER   │    │  MODULE     │ │
│   │             │    │  MODULE     │    │  MODULE     │    │             │ │
│   │ Interprets  │    │ Hull form   │    │ Scantlings  │    │ Propulsion  │ │
│   │ user intent │    │ Coefficients│    │ Loads       │    │ Electrical  │ │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘ │
│          │                  │                  │                  │        │
│          └──────────────────┴──────────────────┴──────────────────┘        │
│                                    │                                        │
│                                    ▼                                        │
│          ┌─────────────────────────────────────────────────────────┐       │
│          │              UNIFIED DESIGN STATE                        │       │
│          │     500+ parameters • Event bus • Full traceability     │       │
│          └─────────────────────────────────────────────────────────┘       │
│                                    │                                        │
│          ┌──────────────────┬──────┴───────┬──────────────────┐            │
│          ▼                  ▼              ▼                  ▼            │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│   │  INTERIOR   │    │  STABILITY  │    │ COMPLIANCE  │    │ SUPERVISOR  │ │
│   │  MODULE     │    │   /WEIGHT   │    │  MODULE     │    │  MODULE     │ │
│   │             │    │   MODULE    │    │             │    │             │ │
│   │ Spatial     │    │ Hydrostatics│    │ Rule book   │    │ Arbitration │ │
│   │ layout      │    │ Balance     │    │ logic       │    │ Tradeoffs   │ │
│   └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

All components read from and write to the **Unified Design State**, ensuring the entire system is deterministic and self-consistent.

**Validators enforce physical realism at every step.**

---

## Architecture

```
magnet/
├── bootstrap/          # Application wiring and dependency injection
├── core/               # Unified Design State, Serializer, Phase Machine
│   ├── parameter_bounds.py  # CLI v1: Kernel-owned bounds for refinement
│   ├── refinable_schema.py  # REFINABLE_SCHEMA whitelist for intent actions
│   └── unit_converter.py    # Deterministic unit conversion (44+ pairs)
├── kernel/             # Conductor, phase registry, hull synthesis engine
│   ├── conductor.py    # Phase orchestration + apply_refinement() + run_default_pipeline()
│   ├── intent_protocol.py  # Intent→Action Protocol types (Intent, Action, ActionPlan)
│   ├── action_validator.py # ActionPlanValidator — firewall between proposals and kernel
│   ├── registry.py     # Phase definitions and dependencies
│   ├── synthesis.py    # Hull synthesis with coefficient coupling & escalation
│   └── priors/         # Hull family priors with bounds & constraints
├── glue/lifecycle/     # Design export and lifecycle management
│   └── exporter.py     # CLI v1: export_with_phase_report()
├── hull_gen/           # Parametric hull generation, GRM, NURBS
├── physics/            # Hydrostatics, resistance calculations
├── stability/          # Intact & damage stability, GZ curves
├── structural/         # Scantlings, frames, stringers, plating
├── weight/             # Mass estimation, LCG/VCG/TCG tracking
├── arrangement/        # Compartment layout, deck plans
├── systems/            # Piping, electrical, HVAC routing
├── compliance/         # Classification society rule engines
├── loading/            # Loading condition calculations
├── production/         # Production planning and cost estimation
├── webgl/              # Real-time 3D visualization engine
├── validators/         # Rule-based validation graph with taxonomy
├── optimization/       # NSGA-II, sensitivity analysis
└── reporting/          # Engineering packet generator

tests/
├── unit/               # 1800+ unit tests
├── integration/        # 400+ integration tests (golden path, pipelines)
├── deployment/         # Worker smoke tests
└── webgl/              # 90 tests for 3D visualization
```

---

## The Math Inside MAGNET

MAGNET integrates **12 mathematical engines**, each a domain in itself:

| Engine | What It Does |
|--------|--------------|
| **NURBS/B-splines** | Hull surface representation with mathematical precision |
| **Hydrostatics Integration** | Simpson's Rule for displacement, centers, waterplane properties |
| **Righting Arm Physics** | GZ curve generation across heel angles |
| **GM/AVS Stability Math** | Metacentric height, angle of vanishing stability |
| **Plate & Stiffener Equations** | Section modulus, moment of inertia, buckling |
| **Holtrop-Mennen Resistance** | Displacement hull resistance prediction |
| **Savitsky Planing** | High-speed planing hull resistance |
| **Power/Range Estimation** | Fuel consumption, operating envelope |
| **Weight/CG Propagation** | Parametric mass estimation with center tracking |
| **Spatial Packing Algorithms** | Interior layout optimization |
| **R-tree Spatial Indexing** | Fast geometric queries for routing |
| **A*/Graph Routing** | Systems routing through 3D space |

**Most commercial tools include 1–3 of these.**
**MAGNET unifies all 12.**

---

## By The Numbers

| Metric | Value |
|--------|-------|
| **Modules** | 40 production-ready |
| **Tests** | 2,355 passing |
| **Lines of Code** | 105,000+ |
| **State Parameters** | 500+ tracked values |
| **Validators** | 15+ physics/stability/compliance |
| **Hull Families** | 5 (patrol, workboat, ferry, planing, catamaran) |
| **Physics Engines** | 12 integrated |
| **Export Formats** | glTF, GLB, STL, OBJ, JSON |
| **Classification Societies** | Lloyd's, ABS, DNV-GL, BV |

---

## The 9-Phase Design Workflow

MAGNET enforces a **gated design process** ensuring engineering integrity:

```
   MISSION ──▶ HULL FORM ──▶ STRUCTURE ──▶ ARRANGEMENT ──▶ PROPULSION
      │                                                        │
      │    Define         Generate        Size            Layout         Select
      │    requirements   geometry        scantlings      compartments   engine
      │                                                        │
      ▼                                                        ▼
PRODUCTION ◀── COMPLIANCE ◀── STABILITY ◀── WEIGHT ◀─────────┘

   Build         Class          Verify          Estimate
   planning      rules          GZ curves       mass & CG
```

Each phase has:
- **Entry Conditions** — Prerequisites that must be satisfied
- **Validators** — Continuous checks during active work
- **Exit Gates** — Criteria required to advance
- **Rollback Support** — Safe return to previous phases

---

## Intent→Action Protocol

MAGNET uses a typed **Intent→Action Protocol** as a firewall between user input and kernel state mutations:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       INTENT → ACTION FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   User Input         Interpreter            Validator              Kernel   │
│   "Make it faster"   Proposes ActionPlan    Validates/Clamps       Executes │
│         │                   │                      │                  │     │
│         ▼                   ▼                      ▼                  ▼     │
│   ┌──────────┐       ┌─────────────┐       ┌─────────────┐    ┌──────────┐ │
│   │  Intent  │  ───▶ │ ActionPlan  │  ───▶ │ Validation  │───▶│  State   │ │
│   │  (raw)   │       │ (proposed)  │       │  Result     │    │ Mutation │ │
│   └──────────┘       └─────────────┘       └─────────────┘    └──────────┘ │
│                             │                     │                         │
│                             │                     ▼                         │
│                             │              ┌─────────────┐                  │
│                             │              │  Rejected?  │                  │
│                             │              │  Clamped?   │                  │
│                             │              │  Warnings?  │                  │
│                             │              └─────────────┘                  │
│                             │                                               │
│                    design_version_before                                    │
│                    must match current                                       │
│                    (stale plan detection)                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Core invariant: proposals never directly drive state.**

### Key Components

| Component | Purpose |
|-----------|---------|
| **Intent** | Structured representation of user's raw input |
| **ActionPlan** | Proposed list of Actions with `design_version_before` |
| **ActionPlanValidator** | Validates against REFINABLE_SCHEMA, converts units, clamps bounds, checks locks |
| **REFINABLE_SCHEMA** | Whitelist of 20+ state paths that can be modified via actions |
| **UnitConverter** | Deterministic conversion (44+ pairs: MW→kW, ft→m, kts→m/s, etc.) |
| **design_version** | Per-mutation counter enabling stale plan detection |
| **Parameter Locks** | Ephemeral locks preventing modification during refinement |

### Example Flow

```python
from magnet.kernel.intent_protocol import Action, ActionPlan, ActionType
from magnet.kernel.action_validator import ActionPlanValidator

# Proposal suggests increasing power
plan = ActionPlan(
    plan_id="plan_001",
    intent_id="intent_001",
    design_id="patrol_32ft",
    design_version_before=5,  # Must match current state
    actions=[
        Action(action_type=ActionType.SET, path="propulsion.total_installed_power_kw", value=2, unit="MW"),
    ],
    proposed_at=datetime.now(),
)

# Validator converts MW→kW, clamps to bounds, checks locks
validator = ActionPlanValidator()
result = validator.validate(plan, state_manager)

# result.approved contains normalized actions (2 MW → 2000 kW)
# result.rejected contains any invalid actions with reasons
# result.warnings contains clamping notices
```

**See [docs/2-protocols/INTENT_ACTION_PROTOCOL.md](docs/2-protocols/INTENT_ACTION_PROTOCOL.md) for full architecture documentation.**

---

## Studio v7 — Natural Language Design (Module 65.1)

MAGNET supports **broad-first natural language design input**. Users can describe a vessel in one sentence and receive a structured, validated proposal before committing changes.

### Example

```
> 60m aluminum catamaran ferry beam 12m draft 3m 25 knots

MAGNET understood:
  hull.loa: 60 m
  hull.beam: 12 m
  hull.draft: 3 m
  hull.hull_type: catamaran
  structural_design.hull_material: aluminum
  mission.vessel_type: ferry
  mission.max_speed_kts: 25 kts

Type "apply" to execute, or add missing fields
```

The system extracts **7 parameters** from a single input, reports missing requirements, detects unsupported concepts, and applies all changes atomically after confirmation.

### Running the API

> **The MAGNET API must be run via DI bootstrap.**

```bash
python3 -m magnet.bootstrap.app run-api
```

**Do not use:** `uvicorn magnet.deployment.api:app` — StateManager will be unavailable.

**See [magnet/ui_v2/docs/MODULE_65_1_INTENT_RESOLUTION.md](magnet/ui_v2/docs/MODULE_65_1_INTENT_RESOLUTION.md) for full documentation.**

---

## Real-Time 3D Visualization

MAGNET includes a **production-grade WebGL engine** built for naval architecture:

```python
from magnet.webgl.geometry_service import GeometryService
from magnet.webgl.exporter import GeometryExporter, ExportFormat

# Single authoritative geometry source — no drift between viz and calcs
service = GeometryService(state_manager=manager)
mesh, mode = service.get_hull_geometry(lod="high")

# Export with full traceability
exporter = GeometryExporter(design_id="patrol_32ft")
exporter.set_version_info(branch="main", commit_hash="abc123")
result = exporter.export(mesh, ExportFormat.GLB)

# Every export is traceable
print(f"Export ID: {result.metadata.export_id}")
print(f"Vertices: {result.metadata.vertex_count}")
print(f"Schema: {result.metadata.schema_version}")
```

**Key capabilities:**
- Engineering-accurate geometry (what you see IS what the math calculates)
- Real-time updates as design changes
- Section cuts at any station, waterline, or buttock
- Hydrostatic overlays (waterlines, LCB markers, metacentric visualization)
- Multi-LOD streaming for performance
- Full export traceability

---

## Quick Start

### Installation

```bash
git clone https://github.com/1quantlogistics-ship-it/MAGNET.git
cd MAGNET
pip install -e ".[dev]"
```

### Create Your First Design

```python
from magnet.core.design_state import DesignState
from magnet.core.state_manager import StateManager
from magnet.core.phase_states import PhaseMachine, PhaseState

# Initialize
state = DesignState(design_name="Patrol Cat 32ft")
manager = StateManager(state)

# Define mission — MAGNET figures out the rest
manager.set("mission.vessel_type", "PATROL", source="user")
manager.set("mission.loa", 32.0, source="user")  # feet
manager.set("mission.max_speed_kts", 35.0, source="user")
manager.set("mission.range_nm", 300.0, source="user")
manager.set("mission.crew", 4, source="user")

# Start the design workflow
machine = PhaseMachine(manager)
machine.transition("mission", PhaseState.COMPLETE, source="user")
machine.transition("hull_form", PhaseState.ACTIVE, source="user")

# Hull geometry is automatically generated
hull = manager.get("hull.geometry")
print(f"Generated hull: {hull.loa}m LOA, Cb={hull.block_coefficient:.3f}")
```

### Run Tests

```bash
# Full test suite (2,355 tests)
PYTHONPATH=. pytest tests/ -v

# Specific module
pytest tests/webgl/ -v

# Integration tests (golden path, pipelines)
pytest tests/integration/ -v

# With coverage
pytest --cov=magnet --cov-report=html
```

---

## Studio v7 UI (HTML)

The design interface is in `magnet/ui_v2/` and is served by the backend at `/ui/v2/`.

### Quick Start
```bash
python3 -m magnet.bootstrap.entrypoints api
open http://localhost:8000/ui/v2/
```

### Golden Loop
```
set hull length to 40 meters → apply → (auto phase run) → GLB loads
```

See [UI Runbook](magnet/ui_v2/docs/UI_V2_RUNBOOK.md) for details.

---

## Where MAGNET Is Going

MAGNET aims to become an engineering design OS capable of:

- Reading mission briefs and constraints
- Producing design packets
- Walking users through the vessel
- Explaining decisions with evidence
- Updating geometry live
- Generating variants and comparisons
- Exporting to professional CAD tools
- Extending beyond marine workflows

---

## Founder's Note

MAGNET began as a challenge:

> *Could one system unify the entire naval design spiral — mission, hull, physics, structure, systems, interior, routing, compliance — into a single engine?*

**The answer is yes.**
**And this repository is proof.**

MAGNET is not a plugin.
It's not a thin wrapper over existing tools.
It's a new category: **an engineering operating system.**

The long-term vision is larger than naval architecture.
MAGNET is a foundation for design workflows across **ships, buildings, aircraft, and beyond.**

**This is only the beginning.**

---








---

<div align="center">

**MAGNET V1.5** — *The Design Operating System*

*40 modules • 2,355 tests • 12 physics engines • 105k+ lines of code*

*One unified platform. Zero disconnected tools. Infinite possibilities.*

</div>
