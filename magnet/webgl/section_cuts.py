"""
webgl/section_cuts.py - Section plane generation v1.1

Module 58: WebGL 3D Visualization
ALPHA OWNS THIS FILE.

Provides section cut generation for transverse, longitudinal, and waterplane sections.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import math
import logging

from .schema import MeshData, LineData

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger("webgl.section_cuts")


class SectionPlane(Enum):
    """Section plane types."""
    TRANSVERSE = "transverse"      # X = constant (body plan view)
    LONGITUDINAL = "longitudinal"  # Y = constant (profile view)
    WATERPLANE = "waterplane"      # Z = constant (plan view)


@dataclass
class SectionResult:
    """Result of a section cut operation."""
    plane: SectionPlane
    position: float
    curves: List[LineData]
    metadata: dict


class SectionCutGenerator:
    """Generator for section cuts through hull geometry."""

    def __init__(self, state_manager: "StateManager"):
        self._sm = state_manager

    def cut(
        self,
        plane: SectionPlane,
        position: float,
    ) -> SectionResult:
        """
        Generate a section cut.

        Args:
            plane: Type of section plane
            position: Position along the axis (0.0 to 1.0 normalized)

        Returns:
            SectionResult with curve data
        """
        hull = self._get_hull_params()

        if plane == SectionPlane.TRANSVERSE:
            return self._transverse_section(position, hull)
        elif plane == SectionPlane.LONGITUDINAL:
            return self._longitudinal_section(position, hull)
        elif plane == SectionPlane.WATERPLANE:
            return self._waterplane_section(position, hull)
        else:
            raise ValueError(f"Unknown plane type: {plane}")

    def _get_hull_params(self) -> dict:
        """Get hull parameters from state."""
        try:
            from magnet.ui.utils import get_state_value
            return {
                "loa": get_state_value(self._sm, "hull.loa", 25.0),
                "beam": get_state_value(self._sm, "hull.beam", 6.0),
                "draft": get_state_value(self._sm, "hull.draft", 1.5),
                "depth": get_state_value(self._sm, "hull.depth", 3.0),
                "cb": get_state_value(self._sm, "hull.cb", 0.45),
                "deadrise_deg": get_state_value(self._sm, "hull.deadrise_deg", 15.0),
                "transom_ratio": get_state_value(self._sm, "hull.transom_width_ratio", 0.85),
            }
        except Exception:
            return {
                "loa": 25.0,
                "beam": 6.0,
                "draft": 1.5,
                "depth": 3.0,
                "cb": 0.45,
                "deadrise_deg": 15.0,
                "transom_ratio": 0.85,
            }

    def _transverse_section(self, position: float, hull: dict) -> SectionResult:
        """Generate transverse (body plan) section."""
        loa = hull["loa"]
        beam = hull["beam"]
        draft = hull["draft"]
        depth = hull["depth"]
        cb = hull["cb"]
        deadrise = hull["deadrise_deg"]
        transom_ratio = hull["transom_ratio"]

        x = position * loa

        # Calculate local beam at this station
        if position < 0.5:
            # Aft of midship
            beam_factor = transom_ratio + (1 - transom_ratio) * (position * 2) ** 0.8
        else:
            # Forward of midship
            bow_ratio = (position - 0.5) * 2
            beam_factor = 1.0 - (1 - 0.1) * bow_ratio ** 2

        local_beam = beam * beam_factor

        # Generate section curve
        n_points = 20
        points = []

        deadrise_rad = math.radians(deadrise)

        for i in range(n_points + 1):
            z_ratio = i / n_points
            z = -draft + z_ratio * (draft + depth)

            if z_ratio < 0.5:
                # Below waterline
                z_local = z_ratio * 2
                y_factor = z_local ** (1.0 / max(0.3, cb))
                deadrise_factor = 1 - (1 - z_local) * math.tan(deadrise_rad) / 2
                y = (local_beam / 2) * y_factor * deadrise_factor
            else:
                # Above waterline
                z_local = (z_ratio - 0.5) * 2
                y = (local_beam / 2) * (1 + 0.1 * z_local)

            y = max(0, min(local_beam / 2, y))
            points.append((x, y, z))

        # Add starboard side (mirror)
        mirrored = [(p[0], -p[1], p[2]) for p in reversed(points[1:])]

        curve = LineData(
            points=mirrored + points,
            closed=False,
            line_id=f"transverse_{position:.3f}",
        )

        return SectionResult(
            plane=SectionPlane.TRANSVERSE,
            position=position,
            curves=[curve],
            metadata={
                "x_position": x,
                "local_beam": local_beam,
            },
        )

    def _longitudinal_section(self, position: float, hull: dict) -> SectionResult:
        """Generate longitudinal (profile) section."""
        loa = hull["loa"]
        beam = hull["beam"]
        draft = hull["draft"]
        depth = hull["depth"]

        # Y position (0 = centerline, 1 = max beam)
        y = position * beam / 2

        # Generate profile curve
        n_points = 40
        points = []

        for i in range(n_points + 1):
            x_ratio = i / n_points
            x = x_ratio * loa

            # Calculate z at this x position
            # Centerline profile
            if position < 0.1:
                # Near centerline - keel line
                if x_ratio < 0.1:
                    # Stern
                    z = -draft * (1 - (0.1 - x_ratio) * 2)
                elif x_ratio > 0.95:
                    # Bow
                    z = -draft * (1 - (x_ratio - 0.95) * 10)
                else:
                    z = -draft
            else:
                # Buttock line
                y_factor = position  # How far from centerline

                if x_ratio < 0.5:
                    z_factor = (x_ratio * 2) ** 0.5
                else:
                    z_factor = 1.0 - (x_ratio - 0.5) * 2 * 0.3

                z = -draft * z_factor * (1 - y_factor * 0.5)

            points.append((x, y, z))

        # Add sheer line
        sheer_points = []
        for i in range(n_points + 1):
            x_ratio = i / n_points
            x = x_ratio * loa
            z = depth

            # Sheer curve (slight droop at ends)
            if x_ratio < 0.2:
                z = depth - 0.1 * (0.2 - x_ratio) * 5
            elif x_ratio > 0.9:
                z = depth + 0.2 * (x_ratio - 0.9) * 10  # Bow rise

            sheer_points.append((x, y, z))

        bottom_curve = LineData(
            points=points,
            closed=False,
            line_id=f"longitudinal_bottom_{position:.3f}",
        )

        sheer_curve = LineData(
            points=sheer_points,
            closed=False,
            line_id=f"longitudinal_sheer_{position:.3f}",
        )

        return SectionResult(
            plane=SectionPlane.LONGITUDINAL,
            position=position,
            curves=[bottom_curve, sheer_curve],
            metadata={
                "y_position": y,
            },
        )

    def _waterplane_section(self, position: float, hull: dict) -> SectionResult:
        """Generate waterplane (plan view) section."""
        loa = hull["loa"]
        beam = hull["beam"]
        draft = hull["draft"]
        cb = hull["cb"]
        transom_ratio = hull["transom_ratio"]

        # Z position (0 = keel, 1 = DWL)
        z = -draft + position * draft

        z_ratio = position

        # Local beam varies with depth
        local_beam = beam * z_ratio ** 0.5

        # Generate waterplane curve
        n_points = 40
        points = []

        for i in range(n_points + 1):
            x_ratio = i / n_points
            x = x_ratio * loa

            # Calculate y at this x position
            if x_ratio < 0.5:
                # Aft
                run_factor = (x_ratio * 2) ** 0.8
                y = local_beam / 2 * run_factor * transom_ratio + local_beam / 2 * run_factor * (1 - transom_ratio)
            else:
                # Forward
                entry_factor = 1 - ((x_ratio - 0.5) * 2) ** 2
                y = local_beam / 2 * entry_factor

            y = max(0, y)
            points.append((x, y, z))

        # Add starboard side (mirror)
        mirrored = [(p[0], -p[1], p[2]) for p in reversed(points[1:-1])]

        # Complete waterplane outline
        full_points = points + mirrored
        full_points.append(points[0])  # Close the curve

        curve = LineData(
            points=full_points,
            closed=True,
            line_id=f"waterplane_{position:.3f}",
        )

        return SectionResult(
            plane=SectionPlane.WATERPLANE,
            position=position,
            curves=[curve],
            metadata={
                "z_position": z,
                "waterplane_area": local_beam * loa * 0.75 * z_ratio,  # Approximate
            },
        )
