"""
structural/plate_generator.py - Plate generation.

ALPHA OWNS THIS FILE.

Section 22: Plate Generation.
"""

from typing import Dict, List, Any, TYPE_CHECKING
import math

from .grid import StructuralGrid
from .plates import Plate, PlateExtent
from .enums import PlateType, MaterialGrade

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class PlateGenerator:
    """Generate structural plates from grid."""

    # Standard stock sheet sizes (mm)
    STOCK_SHEETS = [
        (6000, 2000),  # 6m x 2m
        (4000, 2000),  # 4m x 2m
        (3000, 1500),  # 3m x 1.5m
    ]

    # Minimum thicknesses by zone (mm) - DNV-GL HSLC
    MIN_THICKNESS = {
        "bottom": 5.0,
        "side": 4.0,
        "deck": 4.0,
        "transom": 5.0,
        "bulkhead": 4.0,
    }

    def __init__(self, state: 'StateManager'):
        self.state = state

        # Get design parameters
        self.lwl = state.get("hull.lwl", 24)
        self.beam = state.get("hull.beam", 6)
        self.depth = state.get("hull.depth", 3)
        self.draft = state.get("hull.draft", 1.5)

    def generate_shell_plates(self, grid: StructuralGrid) -> List[Plate]:
        """Generate shell (hull) plates."""
        plates = []

        # Bottom plates
        bottom_plates = self._generate_zone_plates(
            grid, "bottom",
            z_start=0, z_end=self.draft * 0.5,
            thickness_mm=self.state.get("structure.bottom_plate_thickness_mm", 6.0),
        )
        plates.extend(bottom_plates)

        # Side plates (below deck)
        side_plates = self._generate_zone_plates(
            grid, "side",
            z_start=self.draft * 0.5, z_end=self.depth,
            thickness_mm=self.state.get("structure.side_plate_thickness_mm", 5.0),
        )
        plates.extend(side_plates)

        # Transom
        transom = self._generate_transom_plate(grid)
        if transom:
            plates.append(transom)

        return plates

    def generate_deck_plates(self, grid: StructuralGrid) -> List[Plate]:
        """Generate deck plates."""
        plates = []

        # Main deck
        deck_plates = self._generate_deck_zone(
            grid, "deck",
            z_height=self.depth,
            thickness_mm=self.state.get("structure.deck_plate_thickness_mm", 5.0),
        )
        plates.extend(deck_plates)

        return plates

    def generate_bulkhead_plates(self, grid: StructuralGrid) -> List[Plate]:
        """Generate bulkhead plates."""
        plates = []

        for bh in grid.bulkheads:
            plate = Plate(
                plate_id=f"PL-{bh.bulkhead_id}",
                plate_type=PlateType.BULKHEAD,
                zone="bulkhead",
                material=MaterialGrade.AL_5083_H116,
                thickness_mm=self._get_bulkhead_thickness(bh.is_collision_bulkhead),
                extent=PlateExtent(
                    frame_start=bh.frame_number,
                    frame_end=bh.frame_number,
                    y_start=-self.beam / 2,
                    y_end=self.beam / 2,
                    z_start=0,
                    z_end=bh.height_m,
                ),
                is_developed=True,
            )
            plates.append(plate)

        return plates

    def generate_all_plates(self, grid: StructuralGrid) -> List[Plate]:
        """Generate all plates for the vessel."""
        plates = []
        plates.extend(self.generate_shell_plates(grid))
        plates.extend(self.generate_deck_plates(grid))
        plates.extend(self.generate_bulkhead_plates(grid))
        return plates

    def _generate_zone_plates(
        self,
        grid: StructuralGrid,
        zone: str,
        z_start: float,
        z_end: float,
        thickness_mm: float,
    ) -> List[Plate]:
        """Generate plates for a zone between bulkheads."""
        plates = []
        plate_counter = 1

        # Get max plate size from stock
        max_length = self.STOCK_SHEETS[0][0] / 1000  # m

        # Generate plates between consecutive bulkheads
        bh_positions = sorted([0] + [bh.x_position for bh in grid.bulkheads] + [grid.loa])

        for i in range(len(bh_positions) - 1):
            x_start = bh_positions[i]
            x_end = bh_positions[i + 1]
            compartment_length = x_end - x_start

            # Number of plates needed longitudinally
            num_long = max(1, math.ceil(compartment_length / max_length))
            plate_length = compartment_length / num_long

            # Half-breadth strakes
            half_beam = self.beam / 2
            strake_width = min(1.5, half_beam / 2)  # Max 1.5m strakes
            num_strakes = max(1, math.ceil(half_beam / strake_width))

            for j in range(num_long):
                for k in range(num_strakes):
                    # Find frame numbers
                    frame_start = self._find_frame_at_x(grid, x_start + j * plate_length)
                    frame_end = self._find_frame_at_x(grid, x_start + (j + 1) * plate_length)

                    y_start = k * strake_width
                    y_end = min((k + 1) * strake_width, half_beam)

                    plate = Plate(
                        plate_id=f"PL-{zone.upper()}-{plate_counter:03d}",
                        plate_type=PlateType.SHELL if zone != "deck" else PlateType.DECK,
                        zone=zone,
                        material=MaterialGrade.AL_5083_H116,
                        thickness_mm=max(thickness_mm, self.MIN_THICKNESS.get(zone, 4.0)),
                        extent=PlateExtent(
                            frame_start=frame_start,
                            frame_end=frame_end,
                            y_start=y_start,
                            y_end=y_end,
                            z_start=z_start,
                            z_end=z_end,
                        ),
                        is_developed=(zone != "bottom"),  # Bottom may have compound curvature
                    )
                    plates.append(plate)
                    plate_counter += 1

        return plates

    def _generate_deck_zone(
        self,
        grid: StructuralGrid,
        zone: str,
        z_height: float,
        thickness_mm: float,
    ) -> List[Plate]:
        """Generate horizontal deck plates."""
        plates = []
        plate_counter = 1

        max_length = self.STOCK_SHEETS[0][0] / 1000
        max_width = self.STOCK_SHEETS[0][1] / 1000

        # Split into panels
        num_long = max(1, math.ceil(grid.loa / max_length))
        num_trans = max(1, math.ceil(self.beam / max_width))

        for i in range(num_long):
            for j in range(num_trans):
                frame_start = self._find_frame_at_x(grid, i * (grid.loa / num_long))
                frame_end = self._find_frame_at_x(grid, (i + 1) * (grid.loa / num_long))

                y_start = -self.beam / 2 + j * (self.beam / num_trans)
                y_end = -self.beam / 2 + (j + 1) * (self.beam / num_trans)

                plate = Plate(
                    plate_id=f"PL-DECK-{plate_counter:03d}",
                    plate_type=PlateType.DECK,
                    zone=zone,
                    material=MaterialGrade.AL_5083_H116,
                    thickness_mm=thickness_mm,
                    extent=PlateExtent(
                        frame_start=frame_start,
                        frame_end=frame_end,
                        y_start=y_start,
                        y_end=y_end,
                        z_start=z_height,
                        z_end=z_height,
                    ),
                    is_developed=True,
                )
                plates.append(plate)
                plate_counter += 1

        return plates

    def _generate_transom_plate(self, grid: StructuralGrid) -> Plate:
        """Generate transom plate."""
        return Plate(
            plate_id="PL-TRANSOM-001",
            plate_type=PlateType.SHELL,
            zone="transom",
            material=MaterialGrade.AL_5083_H116,
            thickness_mm=self.state.get("structure.transom_plate_thickness_mm", 6.0),
            extent=PlateExtent(
                frame_start=0,
                frame_end=0,
                y_start=-self.beam / 2,
                y_end=self.beam / 2,
                z_start=0,
                z_end=self.depth,
            ),
            is_developed=True,
        )

    def _get_bulkhead_thickness(self, is_collision: bool) -> float:
        """Get bulkhead plate thickness."""
        if is_collision:
            return 6.0  # Heavier for collision bulkhead
        return 5.0

    def _find_frame_at_x(self, grid: StructuralGrid, x: float) -> int:
        """Find frame number at x position."""
        frame = grid.get_frame_at_x(x)
        return frame.frame_number if frame else 0
