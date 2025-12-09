# MAGNET V1.1

<div align="center">

**Maritime Architecture Generation & Naval Engineering Toolkit**

*The world's first AI-native, fully integrated naval architecture platform*

[![Tests](https://img.shields.io/badge/tests-2090%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.13-blue)]()
[![Version](https://img.shields.io/badge/version-1.1.0-orange)]()
[![Modules](https://img.shields.io/badge/modules-58%20complete-purple)]()
[![LOC](https://img.shields.io/badge/lines%20of%20code-150k+-red)]()

</div>

---

## The Future of Naval Architecture

**MAGNET** is not just another CAD tool. It's a **paradigm shift** in how vessels are designed, engineered, and built.

While legacy naval architecture software forces engineers to juggle disconnected tools, manually transfer data between systems, and pray that their hydrostatics match their hull geometry — MAGNET delivers a **unified, state-driven design environment** where every calculation is traceable, every change propagates instantly, and every decision is backed by engineering intelligence.

### Why MAGNET Changes Everything

| Traditional Workflow | MAGNET |
|---------------------|--------|
| Hull design in one tool, hydrostatics in another, structure in a third | **Single unified state** — one source of truth |
| Manual data entry between phases | **Automatic propagation** — change LOA once, everything updates |
| Static 2D drawings | **Real-time 3D WebGL visualization** with engineering accuracy |
| Compliance checked at the end | **Continuous validation** at every design phase |
| "It worked on my machine" | **2,090 automated tests** ensure consistency |
| Weeks to iterate on designs | **Minutes** — parametric everything |

---

## Platform Capabilities

### 58 Integrated Modules

MAGNET comprises **58 production-ready modules** spanning the complete naval architecture workflow:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│   ███╗   ███╗ █████╗  ██████╗ ███╗   ██╗███████╗████████╗                       │
│   ████╗ ████║██╔══██╗██╔════╝ ████╗  ██║██╔════╝╚══██╔══╝                       │
│   ██╔████╔██║███████║██║  ███╗██╔██╗ ██║█████╗     ██║                          │
│   ██║╚██╔╝██║██╔══██║██║   ██║██║╚██╗██║██╔══╝     ██║                          │
│   ██║ ╚═╝ ██║██║  ██║╚██████╔╝██║ ╚████║███████╗   ██║                          │
│   ╚═╝     ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝   ╚═╝                          │
│                                                                                 │
│   Maritime Architecture Generation & Naval Engineering Toolkit                  │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                         PRESENTATION LAYER                                      │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │  MODULE 58: WebGL 3D Visualization                                     │     │
│  │  Real-time hull rendering • LOD streaming • glTF/GLB export           │     │
│  │  Section cuts • Hydrostatic overlays • Engineering-accurate geometry   │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                         APPLICATION LAYER                                       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│  │  FastAPI     │ │  WebSocket   │ │  Lifecycle   │ │  Job Queue   │           │
│  │  REST + WS   │ │  Real-time   │ │  Management  │ │  Background  │           │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                         ENGINEERING LAYER                                       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│  │  Hull Gen    │ │  Structure   │ │  Stability   │ │  Propulsion  │           │
│  │  GRM + NURBS │ │  Scantlings  │ │  Intact/Dmg  │ │  Resistance  │           │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│  │  Weight Est  │ │  Arrangement │ │  Systems     │ │  Compliance  │           │
│  │  LCG/VCG/TCG │ │  Compartment │ │  Piping/Elec │ │  Class Rules │           │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                         FOUNDATION LAYER                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │  MODULE 02: Phase State Machine                                        │     │
│  │  9-phase workflow • Gate conditions • Validation • Persistence         │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
│                                    │                                            │
│                                    ▼                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │  MODULE 01: Unified Design State                                       │     │
│  │  27 dataclasses • 500+ parameters • Full serialization • Event bus    │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Engineering Capabilities

### Hull Generation & Geometry

- **Parametric Hull Forms** — Define principal dimensions, generate complete geometry
- **NURBS Surface Modeling** — Mathematical precision for hydrostatic calculations
- **Geometry Reference Model (GRM)** — Single authoritative geometry source
- **Multi-LOD Tessellation** — From ultra-high for engineering to optimized for real-time viz
- **Automatic Fairing** — Mathematically smooth surfaces guaranteed

### Hydrostatics & Stability

- **Full Hydrostatic Suite** — Displacement, LCB, VCB, LCF, BMt, BMl, KMt, KMl
- **Intact Stability** — GZ curves, dynamic stability, wind heeling
- **Damage Stability** — Probabilistic and deterministic damage cases
- **Tank Effects** — Free surface corrections, slack tanks, cross-flooding
- **Load Conditions** — Lightship, full load, partial conditions

### Structural Analysis

- **Automated Scantlings** — Rule-based structural member sizing
- **Frame Spacing** — Optimized transverse and longitudinal framing
- **Section Modulus** — Hull girder strength calculations
- **Classification Rules** — Lloyd's, ABS, DNV-GL, BV rule integration
- **Finite Element Ready** — Export to FEA packages

### Propulsion & Resistance

- **Resistance Prediction** — Holtrop-Mennen, Savitsky, CFD-ready geometry
- **Propeller Sizing** — Wageningen B-series, optimal diameter/pitch
- **Engine Matching** — Power curves, fuel consumption, operating envelope
- **Speed-Power Prediction** — Full range from displacement to planing

### Weight & Stability

- **Parametric Weight Estimation** — Statistical methods calibrated to vessel type
- **Center of Gravity Tracking** — LCG, VCG, TCG with full breakdown
- **Loading Computer** — Real-time stability with load changes
- **Deadweight Tracking** — Cargo, fuel, water, stores

---

## The 9-Phase Design Workflow

MAGNET enforces a **gated design process** ensuring engineering integrity:

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ MISSION │───▶│  HULL   │───▶│STRUCTURE│───▶│ARRANGE- │───▶│PROPUL-  │
│         │    │  FORM   │    │         │    │  MENT   │    │  SION   │
│ Define  │    │ Generate│    │ Size    │    │ Layout  │    │ Select  │
│ require-│    │ hull    │    │ scant-  │    │ compart-│    │ engine  │
│ ments   │    │ geometry│    │ lings   │    │ ments   │    │ & prop  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
                                                                  │
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐          │
│PRODUC-  │◀───│COMPLI-  │◀───│STABILITY│◀───│ WEIGHT  │◀─────────┘
│  TION   │    │  ANCE   │    │         │    │         │
│         │    │         │    │ Verify  │    │ Estimate│
│ Build   │    │ Class   │    │ intact  │    │ mass &  │
│ planning│    │ rules   │    │ & damage│    │ centers │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
```

Each phase has:
- **Entry Conditions** — Prerequisites that must be satisfied
- **Validators** — Continuous checks during active work
- **Exit Gates** — Criteria required to advance
- **Rollback Support** — Safe return to previous phases

---

## Real-Time 3D Visualization

### WebGL Engine (Module 58)

MAGNET includes a **production-grade 3D visualization system** built for naval architecture:

- **Engineering-Accurate Geometry** — What you see IS what the hydrostatics calculate
- **Real-Time Updates** — Design changes reflect instantly in 3D
- **Section Cuts** — Slice the hull at any station, waterline, or buttock
- **Hydrostatic Overlays** — Waterlines, LCB markers, metacentric height visualization
- **Multi-Format Export** — glTF, GLB, STL, OBJ with full traceability

```python
from magnet.webgl.geometry_service import GeometryService
from magnet.webgl.exporter import GeometryExporter, ExportFormat

# Single authoritative geometry source
service = GeometryService(state_manager=manager)
mesh, mode = service.get_hull_geometry(lod="high")

# Export with full traceability
exporter = GeometryExporter(design_id="patrol_25m")
exporter.set_version_info(branch="main", commit_hash="abc123")
result = exporter.export(mesh, ExportFormat.GLB)

# Every export is traceable
print(f"Export ID: {result.metadata.export_id}")
print(f"Vertices: {result.metadata.vertex_count}")
print(f"Exported: {result.metadata.exported_at}")
```

---

## Technical Excellence

### By The Numbers

| Metric | Value |
|--------|-------|
| **Modules** | 58 complete |
| **Test Coverage** | 2,090 tests passing |
| **Lines of Code** | 150,000+ |
| **State Parameters** | 500+ tracked values |
| **Dataclasses** | 27 domain models |
| **API Endpoints** | 80+ REST routes |
| **Export Formats** | glTF, GLB, STL, OBJ, JSON |

### Engineering Guarantees

- **Single Source of Truth** — No geometry drift between visualization and calculations
- **Versioned Schemas** — Every data structure versioned for compatibility
- **Full Traceability** — Every calculation, export, and change is logged
- **Deterministic Results** — Same inputs always produce same outputs
- **Classification Ready** — Output packages for Lloyd's, ABS, DNV-GL, BV submission

### Modern Architecture

- **Event-Driven** — Reactive updates via EventBus
- **State Machine** — Formal verification of design phase transitions
- **Dependency Injection** — Testable, modular components
- **Async-First** — Non-blocking operations for heavy computations
- **Type-Safe** — Full Python type hints, runtime validation

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

# Initialize a new design
state = DesignState(design_name="Patrol Vessel 25m")
manager = StateManager(state)

# Define mission requirements
manager.set("mission.vessel_type", "PATROL", source="user")
manager.set("mission.loa", 25.0, source="user")
manager.set("mission.max_speed_kts", 30.0, source="user")
manager.set("mission.range_nm", 500.0, source="user")
manager.set("mission.crew", 6, source="user")

# Start the design workflow
machine = PhaseMachine(manager)
machine.transition("mission", PhaseState.ACTIVE, source="user")

# Complete mission phase and advance
machine.transition("mission", PhaseState.COMPLETE, source="user")
machine.transition("hull_form", PhaseState.ACTIVE, source="user")

# Hull geometry is now generated and available
hull_mesh = manager.get("hull.geometry.mesh")
print(f"Hull generated: {hull_mesh.vertex_count} vertices")
```

### Run Tests

```bash
# Full test suite
pytest

# With coverage report
pytest --cov=magnet --cov-report=html

# Specific module
pytest tests/webgl/ -v
```

---

## API Reference

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/designs` | GET | List all designs |
| `/api/v1/designs/{id}` | GET | Get design state |
| `/api/v1/designs/{id}/hull` | GET | Get hull geometry |
| `/api/v1/designs/{id}/3d/scene` | GET | Get full 3D scene |
| `/api/v1/designs/{id}/3d/section` | POST | Generate section cut |
| `/api/v1/designs/{id}/3d/export/{format}` | GET | Export geometry |
| `/api/v1/designs/{id}/hydrostatics` | GET | Get hydrostatic data |
| `/api/v1/designs/{id}/stability` | GET | Get stability curves |

### WebSocket Streams

| Channel | Description |
|---------|-------------|
| `ws://host/ws/design/{id}` | Real-time design updates |
| `ws://host/ws/geometry/{id}` | Geometry change stream |
| `ws://host/ws/validation/{id}` | Live validation results |

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| **1.1.0** | Dec 2024 | WebGL 3D visualization, 58 modules complete |
| **1.0.0** | Nov 2024 | Production release, 55 modules |
| **0.9.0** | Oct 2024 | Beta release, core engineering complete |

---

## The Team

MAGNET is developed by **1Quant Logistics** — bringing computational intelligence to maritime engineering.

We believe the future of naval architecture is:
- **Parametric** — Define intent, generate geometry
- **Integrated** — One platform, complete workflow
- **Intelligent** — AI-assisted design optimization
- **Accessible** — Professional tools for every yard

---

## License

Proprietary Software — 1Quant Logistics

For licensing inquiries: [contact@1quantlogistics.com](mailto:contact@1quantlogistics.com)

---

<div align="center">

**MAGNET V1.1** — *Engineering the Future of Maritime Design*

*58 modules • 2,090 tests • 150k+ lines of code • One unified platform*

</div>
