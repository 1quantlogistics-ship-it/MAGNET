# MAGNET V1

**Maritime Architecture Generation & Naval Engineering Toolkit**

## Overview

MAGNET is a comprehensive naval architecture design system built on a foundation of:
- **Module 01**: Unified Design State - 27 state dataclasses with serialization
- **Module 02**: Phase State Machine - 9-phase design workflow with gate conditions

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FOUNDATION LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │              MODULE 02: PHASE STATE MACHINE                          │    │
│  │      PhaseState │ Transitions │ Validator │ Persistence             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                   │                                          │
│                                   ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │              MODULE 01: UNIFIED DESIGN STATE                         │    │
│  │   DesignState │ StateManager │ Serialization │ Accessors │ Aliases  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

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

## Usage

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

## Version

- **DesignState**: v1.19.0
- **Phase Machine**: v1.1

## License

Proprietary - 1Quant Logistics
