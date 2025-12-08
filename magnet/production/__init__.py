"""
production/ - Production Planning Module.

BRAVO OWNS THIS FILE.

Module 11 v1.1 - Production Planning.

Provides material takeoff, assembly sequencing, and build scheduling
for aluminum workboat construction.

v1.1 Verified Field Names:
    - structure.material
    - structure.frame_spacing_mm
    - structure.*_plate_thickness_mm
"""

from .enums import (
    MaterialCategory,
    AssemblyLevel,
    WorkPackageType,
    ProductionPhase,
)

from .models import (
    MaterialItem,
    MaterialTakeoffResult,
    WorkPackage,
    AssemblySequenceResult,
    ScheduleMilestone,
    BuildSchedule,
    ProductionSummary,
    MATERIAL_DENSITIES,
)

from .material_takeoff import MaterialTakeoff
from .assembly import AssemblySequencer
from .schedule import BuildScheduler

from .validators import (
    ProductionPlanningValidator,
    get_production_planning_definition,
    register_production_validators,
)

__all__ = [
    # Enums
    "MaterialCategory",
    "AssemblyLevel",
    "WorkPackageType",
    "ProductionPhase",
    # Models
    "MaterialItem",
    "MaterialTakeoffResult",
    "WorkPackage",
    "AssemblySequenceResult",
    "ScheduleMilestone",
    "BuildSchedule",
    "ProductionSummary",
    "MATERIAL_DENSITIES",
    # Calculators
    "MaterialTakeoff",
    "AssemblySequencer",
    "BuildScheduler",
    # Validators
    "ProductionPlanningValidator",
    "get_production_planning_definition",
    "register_production_validators",
]
