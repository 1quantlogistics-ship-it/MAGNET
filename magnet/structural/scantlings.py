"""
structural/scantlings.py - Scantling calculations.

BRAVO OWNS THIS FILE.

Module 25 v1.0 - Scantling Calculations (DNV-GL HSLC Rules).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import math

from .enums import StructuralZone, MaterialGrade

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


@dataclass
class MaterialProperties:
    """Material mechanical properties."""

    grade: MaterialGrade = MaterialGrade.AL_5083_H116
    """Material grade."""

    yield_strength_mpa: float = 215.0
    """Minimum yield strength (MPa)."""

    tensile_strength_mpa: float = 305.0
    """Minimum tensile strength (MPa)."""

    elastic_modulus_gpa: float = 70.0
    """Elastic modulus (GPa)."""

    density_kgm3: float = 2660.0
    """Density (kg/m^3)."""

    poisson_ratio: float = 0.33
    """Poisson's ratio."""

    # Weld zone reduction factors
    weld_zone_factor: float = 0.67
    """HAZ strength reduction factor."""

    @classmethod
    def for_grade(cls, grade: MaterialGrade) -> 'MaterialProperties':
        """Get properties for material grade."""
        props = {
            MaterialGrade.AL_5083_H116: cls(
                grade=grade,
                yield_strength_mpa=215.0,
                tensile_strength_mpa=305.0,
            ),
            MaterialGrade.AL_5083_H321: cls(
                grade=grade,
                yield_strength_mpa=215.0,
                tensile_strength_mpa=305.0,
            ),
            MaterialGrade.AL_5086_H116: cls(
                grade=grade,
                yield_strength_mpa=195.0,
                tensile_strength_mpa=275.0,
            ),
            MaterialGrade.AL_6061_T6: cls(
                grade=grade,
                yield_strength_mpa=240.0,
                tensile_strength_mpa=290.0,
                weld_zone_factor=0.50,  # More reduction for 6xxx
            ),
            MaterialGrade.AL_6082_T6: cls(
                grade=grade,
                yield_strength_mpa=250.0,
                tensile_strength_mpa=290.0,
                weld_zone_factor=0.50,
            ),
        }
        return props.get(grade, cls())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grade": self.grade.value,
            "yield_strength_mpa": self.yield_strength_mpa,
            "tensile_strength_mpa": self.tensile_strength_mpa,
            "elastic_modulus_gpa": self.elastic_modulus_gpa,
            "weld_zone_factor": self.weld_zone_factor,
        }


@dataclass
class DesignPressure:
    """Design pressure for structural element."""

    zone: StructuralZone = StructuralZone.BOTTOM
    """Structural zone."""

    static_pressure_kpa: float = 0.0
    """Hydrostatic pressure (kPa)."""

    slamming_pressure_kpa: float = 0.0
    """Slamming pressure (kPa)."""

    combined_pressure_kpa: float = 0.0
    """Combined design pressure (kPa)."""

    x_position: float = 0.0
    """Longitudinal position (m from AP)."""

    z_position: float = 0.0
    """Vertical position (m from baseline)."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone": self.zone.value,
            "static_pressure_kpa": round(self.static_pressure_kpa, 1),
            "slamming_pressure_kpa": round(self.slamming_pressure_kpa, 1),
            "combined_pressure_kpa": round(self.combined_pressure_kpa, 1),
        }


@dataclass
class ScantlingResult:
    """Result of scantling calculation."""

    element_id: str = ""
    """Element identifier."""

    zone: StructuralZone = StructuralZone.BOTTOM
    """Structural zone."""

    required_thickness_mm: float = 0.0
    """Required plate thickness (mm)."""

    actual_thickness_mm: float = 0.0
    """Actual plate thickness (mm)."""

    utilization: float = 0.0
    """Utilization ratio (required/actual)."""

    is_adequate: bool = True
    """Whether scantling is adequate."""

    governing_criterion: str = ""
    """Governing design criterion."""

    design_pressure_kpa: float = 0.0
    """Design pressure used (kPa)."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "element_id": self.element_id,
            "zone": self.zone.value,
            "required_thickness_mm": round(self.required_thickness_mm, 2),
            "actual_thickness_mm": self.actual_thickness_mm,
            "utilization": round(self.utilization, 3),
            "is_adequate": self.is_adequate,
            "governing_criterion": self.governing_criterion,
        }


class ScantlingCalculator:
    """
    Calculate scantlings per DNV-GL HSLC rules.

    High Speed Light Craft rules for aluminum vessels.
    """

    # Minimum plate thicknesses (mm) by zone
    MIN_THICKNESS = {
        StructuralZone.BOTTOM: 4.0,
        StructuralZone.SIDE: 3.0,
        StructuralZone.DECK: 3.0,
        StructuralZone.TRANSOM: 4.0,
        StructuralZone.BULKHEAD: 3.0,
        StructuralZone.SUPERSTRUCTURE: 2.5,
    }

    # Load factors
    SLAMMING_FACTOR = 1.0  # Design factor for slamming
    STATIC_FACTOR = 1.0    # Design factor for static loads

    def __init__(self, state: 'StateManager'):
        self.state = state

        # Get vessel parameters
        self.lwl = state.get("hull.lwl", 24)
        self.beam = state.get("hull.beam", 6)
        self.depth = state.get("hull.depth", 3)
        self.draft = state.get("hull.draft", 1.5)
        self.speed_kts = state.get("mission.max_speed_kts", 30)
        self.displacement_mt = state.get("hull.displacement_mt", 80)

        # Material
        self.material = MaterialProperties.for_grade(MaterialGrade.AL_5083_H116)

    def calculate_design_pressure(
        self,
        zone: StructuralZone,
        x_position: float = 0.0,
        z_position: float = 0.0,
    ) -> DesignPressure:
        """Calculate design pressure for zone and position."""
        pressure = DesignPressure(
            zone=zone,
            x_position=x_position,
            z_position=z_position,
        )

        # Static hydrostatic pressure
        if zone in [StructuralZone.BOTTOM, StructuralZone.SIDE]:
            head = self.draft - z_position
            pressure.static_pressure_kpa = 10.0 * max(0, head)  # rho*g*h

        # Slamming pressure (DNV-GL HSLC simplified)
        if zone == StructuralZone.BOTTOM:
            pressure.slamming_pressure_kpa = self._calculate_slamming_pressure(x_position)
        elif zone == StructuralZone.SIDE:
            # Side slamming at bow
            if x_position > 0.7 * self.lwl:
                pressure.slamming_pressure_kpa = self._calculate_slamming_pressure(x_position) * 0.5

        # Combined (max of factored values)
        pressure.combined_pressure_kpa = max(
            pressure.static_pressure_kpa * self.STATIC_FACTOR,
            pressure.slamming_pressure_kpa * self.SLAMMING_FACTOR,
        )

        return pressure

    def calculate_plate_thickness(
        self,
        zone: StructuralZone,
        span_mm: float,
        pressure_kpa: float,
        aspect_ratio: float = 2.0,
    ) -> float:
        """
        Calculate required plate thickness.

        Uses DNV-GL HSLC formula:
        t = s * sqrt(p / (k * sigma))

        Args:
            zone: Structural zone
            span_mm: Unsupported span (mm)
            pressure_kpa: Design pressure (kPa)
            aspect_ratio: Plate aspect ratio (length/width)

        Returns:
            Required thickness (mm)
        """
        # Allowable stress (with HAZ factor)
        sigma_allow = (self.material.yield_strength_mpa *
                       self.material.weld_zone_factor / 1.5)  # Safety factor

        # Plate coefficient (depends on aspect ratio and boundary conditions)
        k = self._get_plate_coefficient(aspect_ratio)

        # Calculate thickness
        if sigma_allow > 0 and k > 0:
            t_required = span_mm * math.sqrt(pressure_kpa / 1000 / (k * sigma_allow))
        else:
            t_required = 0

        # Apply minimum
        t_min = self.MIN_THICKNESS.get(zone, 3.0)
        return max(t_required, t_min)

    def calculate_stiffener_modulus(
        self,
        zone: StructuralZone,
        span_mm: float,
        spacing_mm: float,
        pressure_kpa: float,
    ) -> float:
        """
        Calculate required stiffener section modulus.

        Uses beam bending formula:
        SM = (p * s * l^2) / (12 * sigma)

        Args:
            zone: Structural zone
            span_mm: Stiffener span (mm)
            spacing_mm: Stiffener spacing (mm)
            pressure_kpa: Design pressure (kPa)

        Returns:
            Required section modulus (cm^3)
        """
        # Allowable stress
        sigma_allow = (self.material.yield_strength_mpa *
                       self.material.weld_zone_factor / 1.5)

        # Pressure in N/mm^2
        p = pressure_kpa / 1000

        # Section modulus formula (fixed-fixed beam)
        sm_required = (p * spacing_mm * span_mm ** 2) / (12 * sigma_allow)

        # Convert mm^3 to cm^3
        return sm_required / 1000

    def check_scantling(
        self,
        element_id: str,
        zone: StructuralZone,
        actual_thickness_mm: float,
        span_mm: float,
        x_position: float = 0.0,
        z_position: float = 0.0,
    ) -> ScantlingResult:
        """Check if scantling is adequate."""
        # Get design pressure
        pressure = self.calculate_design_pressure(zone, x_position, z_position)

        # Calculate required thickness
        required = self.calculate_plate_thickness(
            zone, span_mm, pressure.combined_pressure_kpa
        )

        # Calculate utilization
        utilization = required / actual_thickness_mm if actual_thickness_mm > 0 else float('inf')

        return ScantlingResult(
            element_id=element_id,
            zone=zone,
            required_thickness_mm=required,
            actual_thickness_mm=actual_thickness_mm,
            utilization=utilization,
            is_adequate=utilization <= 1.0,
            governing_criterion="slamming" if pressure.slamming_pressure_kpa > pressure.static_pressure_kpa else "hydrostatic",
            design_pressure_kpa=pressure.combined_pressure_kpa,
        )

    def check_all_plates(
        self,
        plates: List,  # List[Plate]
        grid,  # StructuralGrid
    ) -> List[ScantlingResult]:
        """Check scantlings for all plates."""
        results = []

        for plate in plates:
            # Get zone enum
            zone = self._zone_from_string(plate.zone)

            # Calculate span (frame spacing for longitudinally framed)
            span_mm = grid.frame_spacing_mm

            # Get position
            x_pos = (plate.extent.frame_start + plate.extent.frame_end) / 2 * (grid.frame_spacing_mm / 1000)
            z_pos = (plate.extent.z_start + plate.extent.z_end) / 2

            result = self.check_scantling(
                element_id=plate.plate_id,
                zone=zone,
                actual_thickness_mm=plate.thickness_mm,
                span_mm=span_mm,
                x_position=x_pos,
                z_position=z_pos,
            )
            results.append(result)

        return results

    def _calculate_slamming_pressure(self, x_position: float) -> float:
        """
        Calculate slamming pressure per DNV-GL HSLC.

        Simplified formula:
        p_sl = 0.35 * V^2 * (1 + x/L) * deadrise_factor

        Args:
            x_position: Position from AP (m)

        Returns:
            Slamming pressure (kPa)
        """
        # Speed in m/s
        v = self.speed_kts * 0.5144

        # Position factor (higher at bow)
        pos_factor = 1 + (x_position / self.lwl)

        # Deadrise factor (assume 20 deg average)
        deadrise_deg = self.state.get("hull.deadrise_deg", 20)
        deadrise_factor = max(0.3, 1.0 - deadrise_deg / 50)

        # Calculate pressure
        p_slam = 0.35 * v ** 2 * pos_factor * deadrise_factor

        # Apply reduction for semi-displacement
        hull_type = self.state.get("hull.hull_type", "planing")
        if "displacement" in str(hull_type).lower():
            p_slam *= 0.7

        return p_slam

    def _get_plate_coefficient(self, aspect_ratio: float) -> float:
        """Get plate bending coefficient for aspect ratio."""
        # Simplified from plate theory
        # k approaches 0.5 for long plates, 0.25 for square
        if aspect_ratio >= 3:
            return 0.5
        elif aspect_ratio >= 2:
            return 0.45
        elif aspect_ratio >= 1.5:
            return 0.40
        else:
            return 0.35

    def _zone_from_string(self, zone_str: str) -> StructuralZone:
        """Convert zone string to enum."""
        mapping = {
            "bottom": StructuralZone.BOTTOM,
            "side": StructuralZone.SIDE,
            "deck": StructuralZone.DECK,
            "transom": StructuralZone.TRANSOM,
            "bulkhead": StructuralZone.BULKHEAD,
            "superstructure": StructuralZone.SUPERSTRUCTURE,
        }
        return mapping.get(zone_str.lower(), StructuralZone.BOTTOM)


@dataclass
class ScantlingSummary:
    """Summary of scantling checks."""

    total_elements: int = 0
    """Total elements checked."""

    adequate_count: int = 0
    """Elements with adequate scantlings."""

    inadequate_count: int = 0
    """Elements with inadequate scantlings."""

    max_utilization: float = 0.0
    """Maximum utilization ratio."""

    max_utilization_element: str = ""
    """Element with maximum utilization."""

    average_utilization: float = 0.0
    """Average utilization ratio."""

    by_zone: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    """Results by zone."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_elements": self.total_elements,
            "adequate_count": self.adequate_count,
            "inadequate_count": self.inadequate_count,
            "max_utilization": round(self.max_utilization, 3),
            "max_utilization_element": self.max_utilization_element,
            "average_utilization": round(self.average_utilization, 3),
            "by_zone": self.by_zone,
        }

    @classmethod
    def from_results(cls, results: List[ScantlingResult]) -> 'ScantlingSummary':
        """Create summary from results list."""
        summary = cls(total_elements=len(results))

        if not results:
            return summary

        utilizations = []
        by_zone: Dict[str, Dict[str, Any]] = {}

        for result in results:
            utilizations.append(result.utilization)

            if result.is_adequate:
                summary.adequate_count += 1
            else:
                summary.inadequate_count += 1

            if result.utilization > summary.max_utilization:
                summary.max_utilization = result.utilization
                summary.max_utilization_element = result.element_id

            # By zone
            zone_key = result.zone.value
            if zone_key not in by_zone:
                by_zone[zone_key] = {"count": 0, "adequate": 0, "max_util": 0}
            by_zone[zone_key]["count"] += 1
            if result.is_adequate:
                by_zone[zone_key]["adequate"] += 1
            by_zone[zone_key]["max_util"] = max(
                by_zone[zone_key]["max_util"], result.utilization
            )

        summary.average_utilization = sum(utilizations) / len(utilizations)
        summary.by_zone = by_zone

        return summary
