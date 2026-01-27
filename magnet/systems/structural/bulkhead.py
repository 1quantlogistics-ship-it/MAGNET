"""
magnet/systems/structural/bulkhead.py

T6.2: Bulkhead Generator (wrapper).

Reuses `magnet.structural.grid_generator.StructuralGridGenerator` to generate
bulkhead definitions from hull dimensions and simple classification heuristics.
"""

from __future__ import annotations

from typing import List, TYPE_CHECKING

from magnet.structural.grid_generator import StructuralGridGenerator
from magnet.structural.grid import Bulkhead

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class BulkheadGenerator:
    """Generate bulkheads from hull/mission parameters (wrapper)."""

    def __init__(self, state: "StateManager"):
        self.state = state

    def generate(self) -> List[Bulkhead]:
        grid = StructuralGridGenerator(self.state).generate()
        return list(grid.bulkheads or [])

