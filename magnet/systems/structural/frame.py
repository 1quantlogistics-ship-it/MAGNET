"""
magnet/systems/structural/frame.py

T6.3: Frame Generator (wrapper).

Reuses `magnet.structural.grid_generator.StructuralGridGenerator` to produce
frames from hull dimensions.
"""

from __future__ import annotations

from typing import List, TYPE_CHECKING

from magnet.structural.grid_generator import StructuralGridGenerator
from magnet.structural.grid import Frame

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class FrameGenerator:
    """Generate transverse frames from hull parameters (wrapper)."""

    def __init__(self, state: "StateManager"):
        self.state = state

    def generate(self) -> List[Frame]:
        grid = StructuralGridGenerator(self.state).generate()
        return list(grid.frames or [])

