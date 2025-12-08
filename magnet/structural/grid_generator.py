"""
structural/grid_generator.py - Structural grid generation.

ALPHA OWNS THIS FILE.

Section 21: Structural Grid Generation.
"""

from typing import List, Optional, TYPE_CHECKING

from .grid import StructuralGrid, Frame, Bulkhead
from .enums import FrameType

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class StructuralGridGenerator:
    """Generate structural grid from hull parameters."""

    def __init__(self, state: 'StateManager'):
        self.state = state

        # Get hull dimensions
        self.loa = state.get("hull.loa", 0) or state.get("hull.lwl", 24) * 1.08
        self.lwl = state.get("hull.lwl", 24)
        self.beam = state.get("hull.beam", 6)
        self.depth = state.get("hull.depth", 3)
        self.draft = state.get("hull.draft", 1.5)

        # Get mission parameters for bulkhead placement
        self.speed = state.get("mission.max_speed_kts", 30)

    def generate(self) -> StructuralGrid:
        """Generate complete structural grid."""
        grid = StructuralGrid(
            loa=self.loa,
            lwl=self.lwl,
            beam=self.beam,
            depth=self.depth,
        )

        # Calculate frame spacing based on vessel size
        grid.frame_spacing_mm = self._calculate_frame_spacing()
        grid.web_frame_spacing = self._calculate_web_frame_spacing()

        # Generate frames
        grid.frames = self._generate_frames(grid)

        # Generate bulkheads
        grid.bulkheads = self._generate_bulkheads(grid)

        # Mark bulkhead frames
        for bh in grid.bulkheads:
            for frame in grid.frames:
                if frame.frame_number == bh.frame_number:
                    frame.is_bulkhead = True
                    if bh.is_collision_bulkhead:
                        frame.frame_type = FrameType.COLLISION
                    else:
                        frame.frame_type = FrameType.BULKHEAD

        # Calculate longitudinal spacing
        grid.bottom_long_spacing_mm = self._calculate_long_spacing("bottom")
        grid.side_long_spacing_mm = self._calculate_long_spacing("side")
        grid.deck_long_spacing_mm = self._calculate_long_spacing("deck")

        return grid

    def _calculate_frame_spacing(self) -> float:
        """Calculate frame spacing based on vessel length."""
        if self.lwl < 15:
            return 400.0
        elif self.lwl < 25:
            return 500.0
        elif self.lwl < 40:
            return 600.0
        else:
            return 700.0

    def _calculate_web_frame_spacing(self) -> int:
        """Calculate web frame interval."""
        if self.speed > 35:
            return 3  # High-speed: web every 3rd frame
        elif self.speed > 25:
            return 4  # Medium-speed
        else:
            return 5  # Low-speed

    def _generate_frames(self, grid: StructuralGrid) -> List[Frame]:
        """Generate all frames from AP to FP."""
        frames = []

        spacing_m = grid.frame_spacing_mm / 1000
        num_frames = int(self.loa / spacing_m) + 1

        for i in range(num_frames):
            x_pos = i * spacing_m

            is_web = (i % grid.web_frame_spacing == 0) and i > 0

            frame = Frame(
                frame_number=i,
                x_position=x_pos,
                frame_type=FrameType.WEB_FRAME if is_web else FrameType.ORDINARY,
                is_web_frame=is_web,
                spacing_fwd=grid.frame_spacing_mm,
            )

            frames.append(frame)

        return frames

    def _generate_bulkheads(self, grid: StructuralGrid) -> List[Bulkhead]:
        """Generate bulkheads based on classification rules."""
        bulkheads = []

        # Collision bulkhead: 5% LWL but not less than 2m from FP
        collision_x = max(self.lwl * 0.95, self.loa - 2.0)
        collision_frame = self._find_nearest_frame(grid.frames, collision_x)

        collision_bh = Bulkhead(
            bulkhead_id="BH-COLLISION",
            frame_number=collision_frame,
            x_position=grid.frames[collision_frame].x_position if collision_frame < len(grid.frames) else collision_x,
            bulkhead_type="watertight",
            is_collision_bulkhead=True,
            compartment_fwd="forepeak",
            compartment_aft="forward_hold",
            height_m=self.depth,
            width_m=self.beam,
        )
        bulkheads.append(collision_bh)
        grid.collision_bulkhead_frame = collision_frame

        # Engine room bulkheads (aft ~25% of vessel)
        er_aft_x = self.loa * 0.15
        er_fwd_x = self.loa * 0.35

        er_aft_frame = self._find_nearest_frame(grid.frames, er_aft_x)
        er_fwd_frame = self._find_nearest_frame(grid.frames, er_fwd_x)

        er_aft_bh = Bulkhead(
            bulkhead_id="BH-ER-AFT",
            frame_number=er_aft_frame,
            x_position=grid.frames[er_aft_frame].x_position if er_aft_frame < len(grid.frames) else er_aft_x,
            bulkhead_type="watertight",
            compartment_fwd="engine_room",
            compartment_aft="lazarette",
            height_m=self.depth,
            width_m=self.beam,
        )
        bulkheads.append(er_aft_bh)

        er_fwd_bh = Bulkhead(
            bulkhead_id="BH-ER-FWD",
            frame_number=er_fwd_frame,
            x_position=grid.frames[er_fwd_frame].x_position if er_fwd_frame < len(grid.frames) else er_fwd_x,
            bulkhead_type="watertight",
            compartment_fwd="main_hold",
            compartment_aft="engine_room",
            height_m=self.depth,
            width_m=self.beam,
        )
        bulkheads.append(er_fwd_bh)

        # Mid bulkhead if vessel > 30m
        if self.lwl > 30:
            mid_x = self.loa * 0.55
            mid_frame = self._find_nearest_frame(grid.frames, mid_x)

            mid_bh = Bulkhead(
                bulkhead_id="BH-MID",
                frame_number=mid_frame,
                x_position=grid.frames[mid_frame].x_position if mid_frame < len(grid.frames) else mid_x,
                bulkhead_type="watertight",
                compartment_fwd="forward_hold",
                compartment_aft="main_hold",
                height_m=self.depth,
                width_m=self.beam,
            )
            bulkheads.append(mid_bh)

        return sorted(bulkheads, key=lambda b: b.x_position)

    def _find_nearest_frame(self, frames: List[Frame], x: float) -> int:
        """Find frame number nearest to x position."""
        if not frames:
            return 0

        closest = min(frames, key=lambda f: abs(f.x_position - x))
        return closest.frame_number

    def _calculate_long_spacing(self, zone: str) -> float:
        """Calculate longitudinal stiffener spacing for zone."""
        # Based on DNV-GL HSLC rules
        base_spacing = 300.0  # mm

        if zone == "bottom":
            # Closer spacing for slamming loads
            return base_spacing
        elif zone == "side":
            return base_spacing * 1.33  # 400mm typical
        else:  # deck
            return base_spacing * 1.67  # 500mm typical
