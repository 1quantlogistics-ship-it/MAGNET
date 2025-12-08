"""
production/models.py - Production planning data structures.

BRAVO OWNS THIS FILE.

Module 11 v1.1 - Production planning data models.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta, timezone
from typing import Any, Dict, List, Optional

from .enums import MaterialCategory, AssemblyLevel, WorkPackageType, ProductionPhase


# Material densities by type (kg/m³)
MATERIAL_DENSITIES = {
    "aluminum_5083": 2660.0,
    "aluminum_5086": 2660.0,
    "aluminum_6061": 2700.0,
    "steel_mild": 7850.0,
    "steel_hts": 7850.0,
    "stainless_316": 8000.0,
    "frp": 1800.0,
    "composite": 1600.0,
}


@dataclass
class MaterialItem:
    """Single material line item for takeoff."""
    item_id: str
    category: MaterialCategory
    material_type: str
    description: str
    thickness_mm: Optional[float] = None
    length_m: Optional[float] = None
    width_m: Optional[float] = None
    quantity: float = 1.0
    unit: str = "ea"
    area_m2: Optional[float] = None
    weight_kg: Optional[float] = None
    standard_size: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize material item."""
        return {
            "item_id": self.item_id,
            "category": self.category.value,
            "material_type": self.material_type,
            "description": self.description,
            "thickness_mm": self.thickness_mm,
            "length_m": round(self.length_m, 2) if self.length_m else None,
            "width_m": round(self.width_m, 2) if self.width_m else None,
            "quantity": round(self.quantity, 2),
            "unit": self.unit,
            "area_m2": round(self.area_m2, 2) if self.area_m2 else None,
            "weight_kg": round(self.weight_kg, 1) if self.weight_kg else None,
            "standard_size": self.standard_size,
        }


@dataclass
class MaterialTakeoffResult:
    """Complete material takeoff result."""
    items: List[MaterialItem] = field(default_factory=list)
    plate_area_m2: float = 0.0
    plate_weight_kg: float = 0.0
    profile_length_m: float = 0.0
    profile_weight_kg: float = 0.0
    total_weight_kg: float = 0.0
    scrap_factor: float = 1.15

    @property
    def item_count(self) -> int:
        """Number of material items."""
        return len(self.items)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize material takeoff result."""
        return {
            "items": [i.to_dict() for i in self.items],
            "summary": {
                "plate_area_m2": round(self.plate_area_m2, 2),
                "plate_weight_kg": round(self.plate_weight_kg, 1),
                "profile_length_m": round(self.profile_length_m, 1),
                "profile_weight_kg": round(self.profile_weight_kg, 1),
                "total_weight_kg": round(self.total_weight_kg, 1),
                "scrap_factor": self.scrap_factor,
            },
            "item_count": self.item_count,
        }


@dataclass
class WorkPackage:
    """Work package for assembly sequencing."""
    package_id: str
    name: str
    package_type: WorkPackageType
    assembly_level: AssemblyLevel
    work_hours: float
    dependencies: List[str] = field(default_factory=list)
    zone: Optional[str] = None
    discipline: str = "hull"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize work package."""
        return {
            "package_id": self.package_id,
            "name": self.name,
            "package_type": self.package_type.value,
            "assembly_level": self.assembly_level.value,
            "work_hours": round(self.work_hours, 1),
            "dependencies": self.dependencies,
            "zone": self.zone,
            "discipline": self.discipline,
            "description": self.description,
        }


@dataclass
class AssemblySequenceResult:
    """Assembly sequence result."""
    packages: List[WorkPackage] = field(default_factory=list)
    total_work_hours: float = 0.0
    critical_path_hours: float = 0.0

    @property
    def package_count(self) -> int:
        """Number of work packages."""
        return len(self.packages)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize assembly sequence."""
        return {
            "packages": [p.to_dict() for p in self.packages],
            "summary": {
                "package_count": self.package_count,
                "total_work_hours": round(self.total_work_hours, 1),
                "critical_path_hours": round(self.critical_path_hours, 1),
            },
        }


@dataclass
class ScheduleMilestone:
    """Build schedule milestone."""
    milestone_id: str
    name: str
    phase: ProductionPhase
    planned_date: Optional[date] = None
    duration_days: int = 0
    dependencies: List[str] = field(default_factory=list)
    is_critical: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize schedule milestone."""
        return {
            "milestone_id": self.milestone_id,
            "name": self.name,
            "phase": self.phase.value,
            "planned_date": self.planned_date.isoformat() if self.planned_date else None,
            "duration_days": self.duration_days,
            "dependencies": self.dependencies,
            "is_critical": self.is_critical,
        }


@dataclass
class BuildSchedule:
    """Complete build schedule."""
    milestones: List[ScheduleMilestone] = field(default_factory=list)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_days: int = 0
    work_days_per_week: int = 5
    hours_per_day: float = 8.0

    @property
    def milestone_count(self) -> int:
        """Number of milestones."""
        return len(self.milestones)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize build schedule."""
        return {
            "milestones": [m.to_dict() for m in self.milestones],
            "summary": {
                "start_date": self.start_date.isoformat() if self.start_date else None,
                "end_date": self.end_date.isoformat() if self.end_date else None,
                "total_days": self.total_days,
                "work_days_per_week": self.work_days_per_week,
                "hours_per_day": self.hours_per_day,
            },
            "milestone_count": self.milestone_count,
        }


@dataclass
class ProductionSummary:
    """Production planning summary."""
    material_weight_kg: float = 0.0
    work_packages: int = 0
    total_work_hours: float = 0.0
    build_duration_days: int = 0
    estimated_delivery: Optional[date] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize production summary."""
        return {
            "material_weight_kg": round(self.material_weight_kg, 1),
            "work_packages": self.work_packages,
            "total_work_hours": round(self.total_work_hours, 1),
            "build_duration_days": self.build_duration_days,
            "estimated_delivery": self.estimated_delivery.isoformat() if self.estimated_delivery else None,
        }
