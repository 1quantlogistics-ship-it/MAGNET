"""
structural/stiffeners.py - Stiffener definitions.

BRAVO OWNS THIS FILE.

Module 23 v1.0 - Stiffener Data Structures.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .enums import StiffenerType, ProfileType, MaterialGrade


@dataclass
class ProfileSection:
    """Standard structural profile section properties."""

    profile_type: ProfileType = ProfileType.FLAT_BAR
    """Profile shape type."""

    designation: str = ""
    """Profile designation (e.g., '100x10', 'L75x50x6')."""

    # === DIMENSIONS (mm) ===
    height_mm: float = 100.0
    """Web/profile height (mm)."""

    width_mm: float = 50.0
    """Flange width (mm) - for angle/tee profiles."""

    web_thickness_mm: float = 6.0
    """Web thickness (mm)."""

    flange_thickness_mm: float = 0.0
    """Flange thickness (mm) - for angle/tee profiles."""

    # === SECTION PROPERTIES ===
    area_mm2: float = 0.0
    """Cross-sectional area (mm^2)."""

    moment_of_inertia_cm4: float = 0.0
    """Moment of inertia about neutral axis (cm^4)."""

    section_modulus_cm3: float = 0.0
    """Section modulus (cm^3)."""

    @classmethod
    def flat_bar(cls, height_mm: float, thickness_mm: float) -> 'ProfileSection':
        """Create flat bar profile."""
        area = height_mm * thickness_mm
        # I = b*h^3/12 for rectangle
        inertia = thickness_mm * (height_mm ** 3) / 12 / 1e4  # cm^4
        # S = I / (h/2)
        modulus = inertia / (height_mm / 2 / 10)  # cm^3

        return cls(
            profile_type=ProfileType.FLAT_BAR,
            designation=f"{height_mm:.0f}x{thickness_mm:.0f}",
            height_mm=height_mm,
            width_mm=thickness_mm,
            web_thickness_mm=thickness_mm,
            area_mm2=area,
            moment_of_inertia_cm4=inertia,
            section_modulus_cm3=modulus,
        )

    @classmethod
    def angle(cls, height_mm: float, width_mm: float, thickness_mm: float) -> 'ProfileSection':
        """Create angle profile (L-section)."""
        # Simplified calculation for equal/unequal angle
        area = (height_mm + width_mm - thickness_mm) * thickness_mm
        # Approximate I for angle section
        inertia = (thickness_mm * height_mm ** 3 / 12 +
                   width_mm * thickness_mm ** 3 / 12) / 1e4  # cm^4
        modulus = inertia / (height_mm / 2 / 10)  # cm^3

        return cls(
            profile_type=ProfileType.ANGLE,
            designation=f"L{height_mm:.0f}x{width_mm:.0f}x{thickness_mm:.0f}",
            height_mm=height_mm,
            width_mm=width_mm,
            web_thickness_mm=thickness_mm,
            flange_thickness_mm=thickness_mm,
            area_mm2=area,
            moment_of_inertia_cm4=inertia,
            section_modulus_cm3=modulus,
        )

    @classmethod
    def tee(cls, height_mm: float, width_mm: float,
            web_thickness_mm: float, flange_thickness_mm: float) -> 'ProfileSection':
        """Create tee profile (T-section)."""
        # Area of web + flange
        area = (height_mm - flange_thickness_mm) * web_thickness_mm + width_mm * flange_thickness_mm
        # Approximate I for tee section
        web_i = web_thickness_mm * (height_mm - flange_thickness_mm) ** 3 / 12
        flange_i = width_mm * flange_thickness_mm ** 3 / 12
        # Parallel axis theorem contribution
        na = height_mm * 0.4  # Approximate neutral axis
        inertia = (web_i + flange_i) / 1e4  # cm^4
        modulus = inertia / (na / 10) if na > 0 else 0

        return cls(
            profile_type=ProfileType.TEE,
            designation=f"T{height_mm:.0f}x{width_mm:.0f}",
            height_mm=height_mm,
            width_mm=width_mm,
            web_thickness_mm=web_thickness_mm,
            flange_thickness_mm=flange_thickness_mm,
            area_mm2=area,
            moment_of_inertia_cm4=inertia,
            section_modulus_cm3=modulus,
        )

    @classmethod
    def bulb_flat(cls, height_mm: float, width_mm: float) -> 'ProfileSection':
        """Create bulb flat profile (HP section)."""
        # Bulb flat has thickened head
        web_thickness = width_mm * 0.6
        bulb_area = width_mm * width_mm * 0.5  # Approximate bulb
        web_area = (height_mm - width_mm) * web_thickness
        area = web_area + bulb_area

        # Approximate I for bulb flat
        inertia = web_thickness * height_mm ** 3 / 12 / 1e4  # cm^4
        modulus = inertia / (height_mm / 2 / 10)

        return cls(
            profile_type=ProfileType.BULB_FLAT,
            designation=f"HP{height_mm:.0f}x{width_mm:.0f}",
            height_mm=height_mm,
            width_mm=width_mm,
            web_thickness_mm=web_thickness,
            area_mm2=area,
            moment_of_inertia_cm4=inertia,
            section_modulus_cm3=modulus,
        )

    @property
    def weight_per_meter_kg(self) -> float:
        """Weight per meter (kg/m) for aluminum."""
        # Aluminum density: 2700 kg/m^3
        return self.area_mm2 / 1e6 * 2700  # kg/m

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_type": self.profile_type.value,
            "designation": self.designation,
            "height_mm": self.height_mm,
            "width_mm": self.width_mm,
            "web_thickness_mm": self.web_thickness_mm,
            "flange_thickness_mm": self.flange_thickness_mm,
            "area_mm2": round(self.area_mm2, 1),
            "moment_of_inertia_cm4": round(self.moment_of_inertia_cm4, 2),
            "section_modulus_cm3": round(self.section_modulus_cm3, 2),
            "weight_per_meter_kg": round(self.weight_per_meter_kg, 2),
        }


@dataclass
class Stiffener:
    """Structural stiffener definition."""

    stiffener_id: str = ""
    """Unique stiffener identifier."""

    stiffener_type: StiffenerType = StiffenerType.LONGITUDINAL
    """Type of stiffener."""

    zone: str = "bottom"
    """Structural zone (bottom, side, deck, bulkhead)."""

    material: MaterialGrade = MaterialGrade.AL_6061_T6
    """Material grade (typically 6061-T6 for extrusions)."""

    profile: ProfileSection = field(default_factory=ProfileSection)
    """Profile section properties."""

    # === POSITION ===
    frame_start: int = 0
    """Starting frame number."""

    frame_end: int = 0
    """Ending frame number."""

    y_position: float = 0.0
    """Transverse position from centerline (m)."""

    z_position: float = 0.0
    """Vertical position from baseline (m)."""

    # === LENGTH ===
    length_m: float = 0.0
    """Stiffener length (m)."""

    # === ATTACHMENT ===
    attached_to_plate: str = ""
    """ID of plate this stiffener is attached to."""

    weld_type: str = "fillet"
    """Weld type for attachment."""

    @property
    def weight_kg(self) -> float:
        """Calculate stiffener weight."""
        return self.profile.weight_per_meter_kg * self.length_m

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stiffener_id": self.stiffener_id,
            "stiffener_type": self.stiffener_type.value,
            "zone": self.zone,
            "material": self.material.value,
            "profile": self.profile.to_dict(),
            "frame_start": self.frame_start,
            "frame_end": self.frame_end,
            "y_position": round(self.y_position, 3),
            "z_position": round(self.z_position, 3),
            "length_m": round(self.length_m, 3),
            "weight_kg": round(self.weight_kg, 2),
            "attached_to_plate": self.attached_to_plate,
        }


@dataclass
class StiffenerSummary:
    """Summary of stiffeners for a structure."""

    total_count: int = 0
    """Total number of stiffeners."""

    by_type: Dict[str, int] = field(default_factory=dict)
    """Count by stiffener type."""

    by_zone: Dict[str, int] = field(default_factory=dict)
    """Count by zone."""

    total_length_m: float = 0.0
    """Total stiffener length (m)."""

    total_weight_kg: float = 0.0
    """Total stiffener weight (kg)."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_count": self.total_count,
            "by_type": self.by_type,
            "by_zone": self.by_zone,
            "total_length_m": round(self.total_length_m, 1),
            "total_weight_kg": round(self.total_weight_kg, 1),
        }
