"""
structural/plates.py - Plate definitions.

ALPHA OWNS THIS FILE.

Section 22: Plate Generation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict

from .enums import PlateType, MaterialGrade


@dataclass
class PlateExtent:
    """Plate extent definition (boundary box)."""

    frame_start: int = 0
    """Starting frame number."""

    frame_end: int = 0
    """Ending frame number."""

    y_start: float = 0.0
    """Transverse start position (m from CL)."""

    y_end: float = 0.0
    """Transverse end position (m from CL)."""

    z_start: float = 0.0
    """Vertical start position (m from baseline)."""

    z_end: float = 0.0
    """Vertical end position (m from baseline)."""

    @property
    def length_m(self) -> float:
        """Longitudinal length (m)."""
        return abs(self.y_end - self.y_start)  # For shell, this is girth

    @property
    def width_m(self) -> float:
        """Width (m) - typically transverse dimension."""
        if self.z_end != self.z_start:
            return abs(self.z_end - self.z_start)
        return abs(self.y_end - self.y_start)

    @property
    def area_m2(self) -> float:
        """Plate area (m^2)."""
        # Simplified - actual area depends on hull surface
        return self.length_m * self.width_m

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_start": self.frame_start,
            "frame_end": self.frame_end,
            "y_start": round(self.y_start, 3),
            "y_end": round(self.y_end, 3),
            "z_start": round(self.z_start, 3),
            "z_end": round(self.z_end, 3),
            "length_m": round(self.length_m, 3),
            "width_m": round(self.width_m, 3),
            "area_m2": round(self.area_m2, 3),
        }


@dataclass
class Plate:
    """Structural plate definition."""

    plate_id: str = ""
    """Unique plate identifier."""

    plate_type: PlateType = PlateType.SHELL
    """Type of plate."""

    zone: str = "bottom"
    """Structural zone (bottom, side, deck, etc.)."""

    material: MaterialGrade = MaterialGrade.AL_5083_H116
    """Material grade."""

    thickness_mm: float = 6.0
    """Plate thickness (mm)."""

    extent: PlateExtent = field(default_factory=PlateExtent)
    """Plate extent (boundaries)."""

    # === PRODUCTION INFO ===
    stock_length_mm: float = 6000.0
    """Stock sheet length (mm)."""

    stock_width_mm: float = 2000.0
    """Stock sheet width (mm)."""

    is_developed: bool = False
    """Whether plate is developable (single curvature)."""

    @property
    def weight_kg(self) -> float:
        """Calculate plate weight."""
        # Aluminum density: 2700 kg/m^3
        volume_m3 = self.extent.area_m2 * (self.thickness_mm / 1000)
        return volume_m3 * 2700

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plate_id": self.plate_id,
            "plate_type": self.plate_type.value,
            "zone": self.zone,
            "material": self.material.value,
            "thickness_mm": self.thickness_mm,
            "extent": self.extent.to_dict(),
            "weight_kg": round(self.weight_kg, 2),
            "is_developed": self.is_developed,
        }
