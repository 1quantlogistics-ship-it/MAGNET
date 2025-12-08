"""
structural/welds.py - Weld definitions.

BRAVO OWNS THIS FILE.

Module 24 v1.0 - Weld Data Structures.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

from .enums import WeldType, WeldClass, WeldPosition, MaterialGrade


class WeldProcess(Enum):
    """Welding process types."""
    GMAW = "gmaw"        # Gas Metal Arc Welding (MIG)
    GTAW = "gtaw"        # Gas Tungsten Arc Welding (TIG)
    FCAW = "fcaw"        # Flux-Cored Arc Welding
    SAW = "saw"          # Submerged Arc Welding
    FSW = "fsw"          # Friction Stir Welding


@dataclass
class WeldParameters:
    """Welding parameters for procedure specification."""

    process: WeldProcess = WeldProcess.GMAW
    """Welding process."""

    filler_wire: str = "ER5356"
    """Filler wire designation."""

    wire_diameter_mm: float = 1.2
    """Wire diameter (mm)."""

    shielding_gas: str = "Argon"
    """Shielding gas type."""

    gas_flow_lpm: float = 18.0
    """Gas flow rate (L/min)."""

    current_amps: float = 180.0
    """Welding current (A)."""

    voltage_v: float = 24.0
    """Arc voltage (V)."""

    travel_speed_mmpm: float = 400.0
    """Travel speed (mm/min)."""

    preheat_temp_c: float = 0.0
    """Preheat temperature (C) - typically none for aluminum."""

    interpass_temp_c: float = 150.0
    """Maximum interpass temperature (C)."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "process": self.process.value,
            "filler_wire": self.filler_wire,
            "wire_diameter_mm": self.wire_diameter_mm,
            "shielding_gas": self.shielding_gas,
            "gas_flow_lpm": self.gas_flow_lpm,
            "current_amps": self.current_amps,
            "voltage_v": self.voltage_v,
            "travel_speed_mmpm": self.travel_speed_mmpm,
        }


@dataclass
class WeldJoint:
    """Weld joint definition."""

    weld_id: str = ""
    """Unique weld identifier."""

    weld_type: WeldType = WeldType.FILLET
    """Type of weld."""

    weld_class: WeldClass = WeldClass.CLASS_2
    """Quality classification."""

    position: WeldPosition = WeldPosition.FLAT_1F
    """Weld position code."""

    # === GEOMETRY ===
    leg_size_mm: float = 5.0
    """Fillet weld leg size (mm)."""

    throat_mm: float = 0.0
    """Effective throat (mm) - calculated if 0."""

    length_mm: float = 0.0
    """Weld length (mm)."""

    # === CONNECTION ===
    part_a: str = ""
    """First part ID (plate or stiffener)."""

    part_b: str = ""
    """Second part ID (plate or stiffener)."""

    # === MATERIAL ===
    base_material_a: MaterialGrade = MaterialGrade.AL_5083_H116
    """Material of part A."""

    base_material_b: MaterialGrade = MaterialGrade.AL_5083_H116
    """Material of part B."""

    thickness_a_mm: float = 6.0
    """Thickness of part A (mm)."""

    thickness_b_mm: float = 6.0
    """Thickness of part B (mm)."""

    # === POSITION ===
    x_start: float = 0.0
    """Start x position (m)."""

    x_end: float = 0.0
    """End x position (m)."""

    y_position: float = 0.0
    """Y position (m from CL)."""

    z_position: float = 0.0
    """Z position (m from baseline)."""

    # === PARAMETERS ===
    parameters: WeldParameters = field(default_factory=WeldParameters)
    """Welding parameters."""

    def __post_init__(self):
        """Calculate derived values."""
        if self.throat_mm == 0 and self.leg_size_mm > 0:
            # Throat = 0.707 * leg for fillet welds
            self.throat_mm = 0.707 * self.leg_size_mm

    @property
    def volume_mm3(self) -> float:
        """Calculate weld volume (mm^3)."""
        if self.weld_type == WeldType.FILLET:
            # Triangular cross-section
            area = 0.5 * self.leg_size_mm * self.leg_size_mm
            return area * self.length_mm
        elif self.weld_type == WeldType.BUTT:
            # V-groove approximation
            area = 0.5 * self.throat_mm * self.throat_mm
            return area * self.length_mm
        else:
            return 0

    @property
    def weight_kg(self) -> float:
        """Calculate weld metal weight (kg)."""
        # Aluminum filler density: ~2700 kg/m^3
        volume_m3 = self.volume_mm3 / 1e9
        return volume_m3 * 2700

    @property
    def weld_time_minutes(self) -> float:
        """Estimate welding time (minutes)."""
        if self.parameters.travel_speed_mmpm > 0:
            return self.length_mm / self.parameters.travel_speed_mmpm
        return 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "weld_id": self.weld_id,
            "weld_type": self.weld_type.value,
            "weld_class": self.weld_class.value,
            "position": self.position.value,
            "leg_size_mm": self.leg_size_mm,
            "throat_mm": round(self.throat_mm, 2),
            "length_mm": round(self.length_mm, 1),
            "part_a": self.part_a,
            "part_b": self.part_b,
            "weight_kg": round(self.weight_kg, 3),
            "weld_time_minutes": round(self.weld_time_minutes, 2),
            "parameters": self.parameters.to_dict(),
        }


@dataclass
class WeldSeam:
    """Continuous weld seam (collection of welds along a joint)."""

    seam_id: str = ""
    """Unique seam identifier."""

    welds: List[WeldJoint] = field(default_factory=list)
    """Individual welds in seam."""

    seam_type: str = "plate_to_plate"
    """Seam type: plate_to_plate, stiffener_to_plate, etc."""

    @property
    def total_length_mm(self) -> float:
        """Total seam length."""
        return sum(w.length_mm for w in self.welds)

    @property
    def total_weight_kg(self) -> float:
        """Total weld metal weight."""
        return sum(w.weight_kg for w in self.welds)

    @property
    def total_time_minutes(self) -> float:
        """Total welding time."""
        return sum(w.weld_time_minutes for w in self.welds)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seam_id": self.seam_id,
            "seam_type": self.seam_type,
            "weld_count": len(self.welds),
            "total_length_mm": round(self.total_length_mm, 1),
            "total_weight_kg": round(self.total_weight_kg, 3),
            "total_time_minutes": round(self.total_time_minutes, 1),
        }


@dataclass
class WeldSummary:
    """Summary of all welds for a structure."""

    total_welds: int = 0
    """Total number of weld joints."""

    total_length_m: float = 0.0
    """Total weld length (m)."""

    total_weight_kg: float = 0.0
    """Total weld metal weight (kg)."""

    total_time_hours: float = 0.0
    """Total welding time (hours)."""

    by_type: Dict[str, int] = field(default_factory=dict)
    """Weld count by type."""

    by_class: Dict[str, int] = field(default_factory=dict)
    """Weld count by class."""

    by_position: Dict[str, int] = field(default_factory=dict)
    """Weld count by position."""

    filler_consumption_kg: float = 0.0
    """Estimated filler wire consumption (kg)."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_welds": self.total_welds,
            "total_length_m": round(self.total_length_m, 1),
            "total_weight_kg": round(self.total_weight_kg, 2),
            "total_time_hours": round(self.total_time_hours, 1),
            "by_type": self.by_type,
            "by_class": self.by_class,
            "filler_consumption_kg": round(self.filler_consumption_kg, 2),
        }
