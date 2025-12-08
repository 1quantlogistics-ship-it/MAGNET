"""
structural/weld_generator.py - Weld generation.

BRAVO OWNS THIS FILE.

Module 24 v1.0 - Weld Generation.
"""

from typing import Dict, List, TYPE_CHECKING

from .grid import StructuralGrid
from .plates import Plate
from .stiffeners import Stiffener
from .welds import WeldJoint, WeldSeam, WeldSummary, WeldParameters, WeldProcess
from .enums import (
    WeldType, WeldClass, WeldPosition,
    MaterialGrade, StiffenerType,
)

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class WeldGenerator:
    """Generate welds for structural assembly."""

    # Default fillet sizes by plate thickness (mm)
    FILLET_SIZE_TABLE = {
        4: 3,
        5: 4,
        6: 4,
        8: 5,
        10: 6,
        12: 8,
    }

    # Weld class by joint criticality
    JOINT_CLASS = {
        "hull_seam": WeldClass.CLASS_1,
        "deck_seam": WeldClass.CLASS_2,
        "bulkhead_seam": WeldClass.CLASS_1,
        "stiffener_to_plate": WeldClass.CLASS_2,
        "girder_to_plate": WeldClass.CLASS_1,
        "bracket": WeldClass.CLASS_3,
    }

    def __init__(self, state: 'StateManager'):
        self.state = state
        self.weld_counter = 0

    def generate_plate_seam_welds(
        self,
        plates: List[Plate],
    ) -> List[WeldJoint]:
        """Generate welds at plate seam joints."""
        welds = []

        # Find adjacent plates and create butt welds
        plate_dict = {p.plate_id: p for p in plates}

        # Group by zone
        by_zone: Dict[str, List[Plate]] = {}
        for plate in plates:
            if plate.zone not in by_zone:
                by_zone[plate.zone] = []
            by_zone[plate.zone].append(plate)

        # Generate longitudinal seams (between plates in same zone)
        for zone, zone_plates in by_zone.items():
            zone_welds = self._generate_zone_seams(zone, zone_plates)
            welds.extend(zone_welds)

        return welds

    def generate_stiffener_welds(
        self,
        stiffeners: List[Stiffener],
        plates: List[Plate],
    ) -> List[WeldJoint]:
        """Generate welds attaching stiffeners to plates."""
        welds = []

        for stiffener in stiffeners:
            # Find attached plate
            plate = self._find_plate_for_stiffener(stiffener, plates)
            if plate is None:
                continue

            # Determine weld parameters
            leg_size = self._get_fillet_size(stiffener.profile.web_thickness_mm)

            # Two fillet welds (both sides of stiffener)
            for side in ["A", "B"]:
                weld = WeldJoint(
                    weld_id=f"W-{self.weld_counter:05d}",
                    weld_type=WeldType.FILLET,
                    weld_class=self._get_weld_class(stiffener),
                    position=self._estimate_position(stiffener.zone),
                    leg_size_mm=leg_size,
                    length_mm=stiffener.length_m * 1000,
                    part_a=stiffener.stiffener_id,
                    part_b=plate.plate_id if plate else stiffener.attached_to_plate,
                    base_material_a=stiffener.material,
                    base_material_b=plate.material if plate else MaterialGrade.AL_5083_H116,
                    thickness_a_mm=stiffener.profile.web_thickness_mm,
                    thickness_b_mm=plate.thickness_mm if plate else 6.0,
                    x_start=stiffener.frame_start * 0.5,  # Approximate
                    x_end=stiffener.frame_end * 0.5,
                    y_position=stiffener.y_position,
                    z_position=stiffener.z_position,
                    parameters=self._get_weld_parameters(leg_size),
                )
                welds.append(weld)
                self.weld_counter += 1

        return welds

    def generate_bulkhead_welds(
        self,
        grid: StructuralGrid,
        plates: List[Plate],
    ) -> List[WeldJoint]:
        """Generate welds for bulkhead connections."""
        welds = []

        # Find bulkhead plates
        bh_plates = [p for p in plates if p.zone == "bulkhead"]

        for bh_plate in bh_plates:
            # Perimeter weld to shell
            perimeter_length = 2 * (bh_plate.extent.width_m +
                                    abs(bh_plate.extent.y_end - bh_plate.extent.y_start)) * 1000

            weld = WeldJoint(
                weld_id=f"W-{self.weld_counter:05d}",
                weld_type=WeldType.FILLET,
                weld_class=WeldClass.CLASS_1,  # Critical structural
                position=WeldPosition.VERTICAL_3F,  # Mixed positions
                leg_size_mm=self._get_fillet_size(bh_plate.thickness_mm),
                length_mm=perimeter_length,
                part_a=bh_plate.plate_id,
                part_b="SHELL",
                base_material_a=bh_plate.material,
                base_material_b=MaterialGrade.AL_5083_H116,
                thickness_a_mm=bh_plate.thickness_mm,
                thickness_b_mm=6.0,
                parameters=self._get_weld_parameters(
                    self._get_fillet_size(bh_plate.thickness_mm)
                ),
            )
            welds.append(weld)
            self.weld_counter += 1

        return welds

    def generate_all_welds(
        self,
        grid: StructuralGrid,
        plates: List[Plate],
        stiffeners: List[Stiffener],
    ) -> List[WeldJoint]:
        """Generate all welds for the structure."""
        self.weld_counter = 0
        welds = []

        # Plate seams
        welds.extend(self.generate_plate_seam_welds(plates))

        # Stiffener attachment
        welds.extend(self.generate_stiffener_welds(stiffeners, plates))

        # Bulkhead connections
        welds.extend(self.generate_bulkhead_welds(grid, plates))

        return welds

    def calculate_summary(self, welds: List[WeldJoint]) -> WeldSummary:
        """Calculate weld summary."""
        summary = WeldSummary(total_welds=len(welds))

        for weld in welds:
            # Totals
            summary.total_length_m += weld.length_mm / 1000
            summary.total_weight_kg += weld.weight_kg
            summary.total_time_hours += weld.weld_time_minutes / 60

            # By type
            type_key = weld.weld_type.value
            summary.by_type[type_key] = summary.by_type.get(type_key, 0) + 1

            # By class
            class_key = weld.weld_class.value
            summary.by_class[class_key] = summary.by_class.get(class_key, 0) + 1

            # By position
            pos_key = weld.position.value
            summary.by_position[pos_key] = summary.by_position.get(pos_key, 0) + 1

        # Filler consumption (approx 1.2x deposited weight)
        summary.filler_consumption_kg = summary.total_weight_kg * 1.2

        return summary

    def _generate_zone_seams(
        self,
        zone: str,
        plates: List[Plate],
    ) -> List[WeldJoint]:
        """Generate seam welds within a zone."""
        welds = []

        # Sort by position to find adjacent plates
        sorted_plates = sorted(plates, key=lambda p: (p.extent.frame_start, p.extent.y_start))

        for i in range(len(sorted_plates) - 1):
            plate_a = sorted_plates[i]
            plate_b = sorted_plates[i + 1]

            # Check if plates are adjacent (share a boundary)
            if self._plates_adjacent(plate_a, plate_b):
                # Calculate seam length
                seam_length = self._calculate_seam_length(plate_a, plate_b)

                if seam_length > 0:
                    weld = WeldJoint(
                        weld_id=f"W-{self.weld_counter:05d}",
                        weld_type=WeldType.BUTT,
                        weld_class=self._get_seam_class(zone),
                        position=self._estimate_position(zone),
                        leg_size_mm=0,
                        throat_mm=min(plate_a.thickness_mm, plate_b.thickness_mm),
                        length_mm=seam_length,
                        part_a=plate_a.plate_id,
                        part_b=plate_b.plate_id,
                        base_material_a=plate_a.material,
                        base_material_b=plate_b.material,
                        thickness_a_mm=plate_a.thickness_mm,
                        thickness_b_mm=plate_b.thickness_mm,
                        parameters=self._get_weld_parameters(
                            min(plate_a.thickness_mm, plate_b.thickness_mm)
                        ),
                    )
                    welds.append(weld)
                    self.weld_counter += 1

        return welds

    def _plates_adjacent(self, plate_a: Plate, plate_b: Plate) -> bool:
        """Check if two plates share a boundary."""
        # Check longitudinal adjacency (same y range, adjacent frames)
        if (abs(plate_a.extent.y_start - plate_b.extent.y_start) < 0.01 and
            abs(plate_a.extent.y_end - plate_b.extent.y_end) < 0.01):
            if plate_a.extent.frame_end == plate_b.extent.frame_start:
                return True

        # Check transverse adjacency (same frame range, adjacent y)
        if (plate_a.extent.frame_start == plate_b.extent.frame_start and
            plate_a.extent.frame_end == plate_b.extent.frame_end):
            if abs(plate_a.extent.y_end - plate_b.extent.y_start) < 0.01:
                return True

        return False

    def _calculate_seam_length(self, plate_a: Plate, plate_b: Plate) -> float:
        """Calculate length of seam between plates (mm)."""
        # Longitudinal seam
        if plate_a.extent.frame_end == plate_b.extent.frame_start:
            return abs(plate_a.extent.y_end - plate_a.extent.y_start) * 1000

        # Transverse seam
        if abs(plate_a.extent.y_end - plate_b.extent.y_start) < 0.01:
            # Approximate from frame count (assume 0.5m spacing)
            frames = plate_a.extent.frame_end - plate_a.extent.frame_start
            return frames * 500  # mm

        return 0

    def _find_plate_for_stiffener(
        self,
        stiffener: Stiffener,
        plates: List[Plate],
    ) -> Plate:
        """Find the plate a stiffener is attached to."""
        # First try by ID
        if stiffener.attached_to_plate:
            for plate in plates:
                if plate.plate_id == stiffener.attached_to_plate:
                    return plate

        # Fall back to position matching
        for plate in plates:
            if plate.zone == stiffener.zone:
                if (plate.extent.frame_start <= stiffener.frame_start <= plate.extent.frame_end or
                    plate.extent.frame_start <= stiffener.frame_end <= plate.extent.frame_end):
                    return plate

        return None

    def _get_fillet_size(self, thickness_mm: float) -> float:
        """Get fillet weld leg size for plate thickness."""
        for t, size in sorted(self.FILLET_SIZE_TABLE.items()):
            if thickness_mm <= t:
                return size
        return 8  # Maximum

    def _get_weld_class(self, stiffener: Stiffener) -> WeldClass:
        """Determine weld class for stiffener attachment."""
        if stiffener.stiffener_type == StiffenerType.GIRDER:
            return WeldClass.CLASS_1
        elif stiffener.stiffener_type in [StiffenerType.WEB_FRAME, StiffenerType.LONGITUDINAL]:
            return WeldClass.CLASS_2
        else:
            return WeldClass.CLASS_3

    def _get_seam_class(self, zone: str) -> WeldClass:
        """Get weld class for plate seam by zone."""
        if zone in ["bottom", "bulkhead"]:
            return WeldClass.CLASS_1
        elif zone in ["side", "deck"]:
            return WeldClass.CLASS_2
        else:
            return WeldClass.CLASS_3

    def _estimate_position(self, zone: str) -> WeldPosition:
        """Estimate weld position from zone."""
        if zone == "deck":
            return WeldPosition.FLAT_1F
        elif zone == "bottom":
            return WeldPosition.OVERHEAD_4F
        elif zone == "side":
            return WeldPosition.VERTICAL_3F
        else:
            return WeldPosition.HORIZONTAL_2F

    def _get_weld_parameters(self, leg_or_throat_mm: float) -> WeldParameters:
        """Get welding parameters for given weld size."""
        # Scale parameters with weld size
        base_current = 150 + leg_or_throat_mm * 10
        base_voltage = 22 + leg_or_throat_mm * 0.5

        return WeldParameters(
            process=WeldProcess.GMAW,
            filler_wire="ER5356",
            wire_diameter_mm=1.2,
            shielding_gas="Argon",
            gas_flow_lpm=18.0,
            current_amps=min(base_current, 250),
            voltage_v=min(base_voltage, 28),
            travel_speed_mmpm=400 - leg_or_throat_mm * 20,
        )
