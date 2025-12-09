# MAGNET V1.1

**Maritime Architecture Generation & Naval Engineering Toolkit**

[![Tests](https://img.shields.io/badge/tests-2090%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.13-blue)]()
[![Version](https://img.shields.io/badge/version-1.1.0-orange)]()

## Overview

MAGNET is a comprehensive naval architecture design system for yacht and small vessel engineering. The platform provides an integrated workflow from initial concept through production planning.

## Module Status

| Module | Name | Status | Tests |
|--------|------|--------|-------|
| 01 | Unified Design State | Complete | 180+ |
| 02 | Phase State Machine | Complete | 120+ |
| 03-10 | Core Engineering | Complete | 400+ |
| 11-20 | Hull & Structure | Complete | 300+ |
| 21-30 | Systems & Arrangement | Complete | 250+ |
| 31-40 | Analysis & Compliance | Complete | 200+ |
| 41-50 | Integration & API | Complete | 300+ |
| 51-54 | Advanced Features | Complete | 150+ |
| 55 | Bootstrap & Initialization | Complete | 50+ |
| 56 | Deployment Infrastructure | Complete | 60+ |
| 57 | Testing Framework | Complete | 40+ |
| **58** | **WebGL 3D Visualization** | **Complete** | **90** |

**Total: 2090 tests passing**

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  Module 58: WebGL 3D Visualization                                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │ GeometryServ │ │ MeshBuilder  │ │ Exporter     │ │ WebSocket    │       │
│  │ (FM1)        │ │              │ │ (FM8)        │ │ Stream       │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
├─────────────────────────────────────────────────────────────────────────────┤
│                           APPLICATION LAYER                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Modules 41-57: API, Bootstrap, Deployment, Testing                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │ FastAPI      │ │ Lifecycle    │ │ Docker       │ │ Pytest       │       │
│  │ Endpoints    │ │ Manager      │ │ Compose      │ │ Framework    │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
├─────────────────────────────────────────────────────────────────────────────┤
│                           ENGINEERING LAYER                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Modules 11-40: Hull, Structure, Systems, Analysis, Compliance              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │ HullGen      │ │ Structures   │ │ Stability    │ │ Classification│      │
│  │ GRM          │ │ Scantlings   │ │ Hydrostatics │ │ Rules        │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
├─────────────────────────────────────────────────────────────────────────────┤
│                           FOUNDATION LAYER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │              MODULE 02: PHASE STATE MACHINE                          │    │
│  │      PhaseState │ Transitions │ Validators │ Persistence            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                   │                                          │
│                                   ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │              MODULE 01: UNIFIED DESIGN STATE                         │    │
│  │   DesignState │ StateManager │ Serialization │ Accessors │ Aliases  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Module 58: WebGL 3D Visualization (v1.1)

Interactive 3D hull visualization with single authoritative geometry source.

### Failure Modes Addressed

| FM | Issue | Resolution |
|----|-------|------------|
| FM1 | Visual/Engineering divergence | Single authoritative `GeometryService` |
| FM2 | Schema drift | Versioned schema + TypeScript generation |
| FM3 | Performance collapse | LOD configs + resource limits |
| FM4 | StateManager coupling | `GeometryInputProvider` protocol |
| FM5 | Weak error signaling | `GeometryError` taxonomy (GEOM_001-008) |
| FM7 | EventBus not integrated | Geometry event streaming |
| FM8 | Export not versioned | `ExportMetadata` traceability |

### Key Components

- **GeometryService** - Single entry point for authoritative geometry
- **Schema** - Versioned data contracts (SCHEMA_VERSION=1.1.0)
- **Exporter** - glTF/GLB, STL, OBJ with full traceability
- **Serializer** - Binary MNET format for efficient transfer

## Design Phases

1. **Mission** - Vessel requirements and operational parameters
2. **Hull Form** - Geometry generation and hull coefficients
3. **Structure** - Scantlings, framing, and structural analysis
4. **Arrangement** - Compartment layout and deck plans
5. **Propulsion** - Engine selection and propeller sizing
6. **Weight** - Mass estimation and center of gravity
7. **Stability** - Intact and damaged stability analysis
8. **Compliance** - Classification society rule checking
9. **Production** - Build planning and cost estimation

## Installation

```bash
pip install -e ".[dev]"
```

## Quick Start

```python
from magnet.core.design_state import DesignState
from magnet.core.state_manager import StateManager
from magnet.core.phase_states import PhaseMachine

# Create a new design
state = DesignState(design_name="Patrol Vessel 25m")
manager = StateManager(state)

# Set mission parameters
manager.set("mission.vessel_type", "PATROL", source="user")
manager.set("mission.max_speed_kts", 30.0, source="user")
manager.set("mission.range_nm", 500.0, source="user")

# Progress through design phases
machine = PhaseMachine(manager)
machine.transition("mission", PhaseState.ACTIVE, source="user")
```

### 3D Visualization

```python
from magnet.webgl.geometry_service import GeometryService
from magnet.webgl.exporter import GeometryExporter, ExportFormat

# Get authoritative hull geometry
service = GeometryService(state_manager=manager)
mesh, mode = service.get_hull_geometry(lod="high")

# Export to glTF
exporter = GeometryExporter(design_id="patrol_25m")
result = exporter.export(mesh, ExportFormat.GLB)

# Save with full traceability
with open("hull.glb", "wb") as f:
    f.write(result.data)
print(f"Export ID: {result.metadata.export_id}")
```

## Running Tests

```bash
# Run all tests
pytest

# Run specific module tests
pytest tests/webgl/ -v

# Run with coverage
pytest --cov=magnet
```

## Version

- **MAGNET**: v1.1.0
- **DesignState**: v1.19.0
- **Phase Machine**: v1.1
- **WebGL Schema**: v1.1.0

## License

Proprietary - 1Quant Logistics
