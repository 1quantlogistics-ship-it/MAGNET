"""
structural/stiffener_generator.py - Stiffener generation.

BRAVO OWNS THIS FILE.

Module 23 v1.0 - Stiffener Generation.
"""

from typing import List, TYPE_CHECKING

from .grid import StructuralGrid
from .plates import Plate
from .stiffeners import Stiffener, ProfileSection, StiffenerSummary
from .enums import StiffenerType, ProfileType, MaterialGrade

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class StiffenerGenerator:
    """Generate stiffeners for structural plates."""

    # Default profile sizes by zone (height_mm, thickness_mm for flat bars)
    DEFAULT_PROFILES = {
        "bottom": (100, 8),    # Heavy for slamming
        "side": (80, 6),       # Medium
        "deck": (75, 6),       # Medium
        "bulkhead": (60, 5),   # Lighter
        "transom": (80, 6),    # Medium
    }

    def __init__(self, state: 'StateManager'):
        self.state = state

        # Get dimensions
        self.lwl = state.get("hull.lwl", 24)
        self.beam = state.get("hull.beam", 6)
        self.depth = state.get("hull.depth", 3)
        self.draft = state.get("hull.draft", 1.5)

    def generate_longitudinals(
        self,
        grid: StructuralGrid,
        plates: List[Plate],
    ) -> List[Stiffener]:
        """Generate longitudinal stiffeners."""
        stiffeners = []
        stiff_counter = 1

        # Group plates by zone
        by_zone = {}
        for plate in plates:
            zone = plate.zone
            if zone not in by_zone:
                by_zone[zone] = []
            by_zone[zone].append(plate)

        # Generate stiffeners for each zone
        for zone, zone_plates in by_zone.items():
            spacing_mm = self._get_longitudinal_spacing(grid, zone)
            profile = self._get_profile_for_zone(zone)

            for plate in zone_plates:
                plate_stiffeners = self._generate_plate_longitudinals(
                    grid, plate, spacing_mm, profile, stiff_counter
                )
                stiffeners.extend(plate_stiffeners)
                stiff_counter += len(plate_stiffeners)

        return stiffeners

    def generate_transverse_frames(
        self,
        grid: StructuralGrid,
        plates: List[Plate],
    ) -> List[Stiffener]:
        """Generate transverse frame stiffeners."""
        stiffeners = []
        stiff_counter = 1

        # Generate frame stiffeners at each frame location
        for frame in grid.frames:
            if frame.is_web_frame:
                # Web frames get heavier stiffening
                profile = ProfileSection.tee(150, 100, 8, 10)
                stiff_type = StiffenerType.WEB_FRAME
            else:
                # Ordinary frames
                profile = ProfileSection.angle(80, 50, 6)
                stiff_type = StiffenerType.TRANSVERSE_FRAME

            # Bottom frame stiffener
            stiff = Stiffener(
                stiffener_id=f"FR-{frame.frame_number:03d}-BOT",
                stiffener_type=stiff_type,
                zone="bottom",
                material=MaterialGrade.AL_6061_T6,
                profile=profile,
                frame_start=frame.frame_number,
                frame_end=frame.frame_number,
                y_position=0,
                z_position=-self.draft / 2,
                length_m=self.beam,
            )
            stiffeners.append(stiff)
            stiff_counter += 1

            # Side frame stiffeners (port and starboard)
            for side in [-1, 1]:
                side_stiff = Stiffener(
                    stiffener_id=f"FR-{frame.frame_number:03d}-{'P' if side < 0 else 'S'}",
                    stiffener_type=stiff_type,
                    zone="side",
                    material=MaterialGrade.AL_6061_T6,
                    profile=profile,
                    frame_start=frame.frame_number,
                    frame_end=frame.frame_number,
                    y_position=side * self.beam / 2,
                    z_position=self.depth / 2,
                    length_m=self.depth,
                )
                stiffeners.append(side_stiff)
                stiff_counter += 1

        return stiffeners

    def generate_deck_beams(
        self,
        grid: StructuralGrid,
    ) -> List[Stiffener]:
        """Generate deck beams (transverse deck stiffeners)."""
        stiffeners = []

        for frame in grid.frames:
            if frame.is_web_frame:
                profile = ProfileSection.tee(120, 80, 8, 10)
            else:
                profile = ProfileSection.flat_bar(80, 6)

            beam = Stiffener(
                stiffener_id=f"DB-{frame.frame_number:03d}",
                stiffener_type=StiffenerType.DECK_BEAM,
                zone="deck",
                material=MaterialGrade.AL_6061_T6,
                profile=profile,
                frame_start=frame.frame_number,
                frame_end=frame.frame_number,
                y_position=0,
                z_position=self.depth,
                length_m=self.beam,
            )
            stiffeners.append(beam)

        return stiffeners

    def generate_girders(
        self,
        grid: StructuralGrid,
    ) -> List[Stiffener]:
        """Generate main girders (heavy longitudinals)."""
        stiffeners = []

        # Centerline girder
        cl_girder = Stiffener(
            stiffener_id="GIRDER-CL",
            stiffener_type=StiffenerType.GIRDER,
            zone="bottom",
            material=MaterialGrade.AL_6061_T6,
            profile=ProfileSection.tee(200, 150, 10, 12),
            frame_start=0,
            frame_end=len(grid.frames) - 1,
            y_position=0,
            z_position=-self.draft,
            length_m=grid.loa,
        )
        stiffeners.append(cl_girder)

        # Side girders at 1/4 beam
        for side in [-1, 1]:
            side_girder = Stiffener(
                stiffener_id=f"GIRDER-{'P' if side < 0 else 'S'}",
                stiffener_type=StiffenerType.GIRDER,
                zone="bottom",
                material=MaterialGrade.AL_6061_T6,
                profile=ProfileSection.tee(150, 100, 8, 10),
                frame_start=0,
                frame_end=len(grid.frames) - 1,
                y_position=side * self.beam / 4,
                z_position=-self.draft,
                length_m=grid.loa,
            )
            stiffeners.append(side_girder)

        return stiffeners

    def generate_all_stiffeners(
        self,
        grid: StructuralGrid,
        plates: List[Plate],
    ) -> List[Stiffener]:
        """Generate all stiffeners for the structure."""
        stiffeners = []

        # Longitudinals
        stiffeners.extend(self.generate_longitudinals(grid, plates))

        # Transverse frames
        stiffeners.extend(self.generate_transverse_frames(grid, plates))

        # Deck beams
        stiffeners.extend(self.generate_deck_beams(grid))

        # Girders
        stiffeners.extend(self.generate_girders(grid))

        return stiffeners

    def calculate_summary(self, stiffeners: List[Stiffener]) -> StiffenerSummary:
        """Calculate stiffener summary."""
        summary = StiffenerSummary(total_count=len(stiffeners))

        for stiff in stiffeners:
            # By type
            type_key = stiff.stiffener_type.value
            summary.by_type[type_key] = summary.by_type.get(type_key, 0) + 1

            # By zone
            summary.by_zone[stiff.zone] = summary.by_zone.get(stiff.zone, 0) + 1

            # Totals
            summary.total_length_m += stiff.length_m
            summary.total_weight_kg += stiff.weight_kg

        return summary

    def _generate_plate_longitudinals(
        self,
        grid: StructuralGrid,
        plate: Plate,
        spacing_mm: float,
        profile: ProfileSection,
        start_counter: int,
    ) -> List[Stiffener]:
        """Generate longitudinal stiffeners for a single plate."""
        stiffeners = []

        # Calculate plate dimensions
        y_start = plate.extent.y_start
        y_end = plate.extent.y_end
        plate_width = abs(y_end - y_start)

        # Calculate number of stiffeners
        spacing_m = spacing_mm / 1000
        num_stiffs = max(1, int(plate_width / spacing_m) - 1)

        if num_stiffs == 0:
            return stiffeners

        # Generate stiffeners
        stiff_spacing = plate_width / (num_stiffs + 1)

        for i in range(num_stiffs):
            y_pos = y_start + (i + 1) * stiff_spacing

            # Calculate length (frame to frame)
            x_start = grid.frames[plate.extent.frame_start].x_position if plate.extent.frame_start < len(grid.frames) else 0
            x_end = grid.frames[plate.extent.frame_end].x_position if plate.extent.frame_end < len(grid.frames) else grid.loa
            length = abs(x_end - x_start)

            stiff = Stiffener(
                stiffener_id=f"L-{plate.zone.upper()}-{start_counter + i:03d}",
                stiffener_type=StiffenerType.LONGITUDINAL,
                zone=plate.zone,
                material=MaterialGrade.AL_6061_T6,
                profile=profile,
                frame_start=plate.extent.frame_start,
                frame_end=plate.extent.frame_end,
                y_position=y_pos,
                z_position=(plate.extent.z_start + plate.extent.z_end) / 2,
                length_m=length,
                attached_to_plate=plate.plate_id,
            )
            stiffeners.append(stiff)

        return stiffeners

    def _get_longitudinal_spacing(self, grid: StructuralGrid, zone: str) -> float:
        """Get longitudinal stiffener spacing for zone."""
        if zone == "bottom":
            return grid.bottom_long_spacing_mm
        elif zone == "side":
            return grid.side_long_spacing_mm
        elif zone == "deck":
            return grid.deck_long_spacing_mm
        else:
            return 400.0  # Default

    def _get_profile_for_zone(self, zone: str) -> ProfileSection:
        """Get default profile for zone."""
        dims = self.DEFAULT_PROFILES.get(zone, (80, 6))
        return ProfileSection.flat_bar(dims[0], dims[1])
