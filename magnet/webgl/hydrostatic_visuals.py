"""
webgl/hydrostatic_visuals.py - Hydrostatic visualization v1.1

Module 58: WebGL 3D Visualization
ALPHA OWNS THIS FILE.

Provides visualization of hydrostatic elements (waterlines, sections, curves).
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List, Tuple
import math
import logging

from .schema import MeshData, HydrostaticSceneData, LineData, LODLevel

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger("webgl.hydrostatic_visuals")


class HydrostaticVisualBuilder:
    """Builder for hydrostatic visualization data."""

    def __init__(self, state_manager: "StateManager"):
        self._sm = state_manager

    def build(self, lod: LODLevel = LODLevel.MEDIUM) -> HydrostaticSceneData:
        """Build all hydrostatic visualizations."""
        return HydrostaticSceneData(
            waterlines=self._build_waterlines(lod),
            sectional_areas=self._build_sectional_areas(lod),
            bonjean_curves=self._build_bonjean_curves(lod),
            displacement_volume=self._build_displacement_volume(lod),
        )

    def _get_hull_params(self) -> dict:
        """Get hull parameters from state."""
        try:
            from magnet.ui.utils import get_state_value
            return {
                "loa": get_state_value(self._sm, "hull.loa", 25.0),
                "lwl": get_state_value(self._sm, "hull.lwl", 23.0),
                "beam": get_state_value(self._sm, "hull.beam", 6.0),
                "draft": get_state_value(self._sm, "hull.draft", 1.5),
                "cb": get_state_value(self._sm, "hull.cb", 0.45),
                "cwp": get_state_value(self._sm, "hull.cwp", 0.75),
            }
        except Exception:
            return {
                "loa": 25.0,
                "lwl": 23.0,
                "beam": 6.0,
                "draft": 1.5,
                "cb": 0.45,
                "cwp": 0.75,
            }

    def _build_waterlines(self, lod: LODLevel) -> List[LineData]:
        """Build waterline curves at various drafts."""
        waterlines = []
        hull = self._get_hull_params()

        draft = hull["draft"]
        loa = hull["loa"]
        lwl = hull["lwl"]
        beam = hull["beam"]
        cwp = hull["cwp"]

        # Number of waterlines based on LOD
        n_waterlines = {
            LODLevel.LOW: 3,
            LODLevel.MEDIUM: 5,
            LODLevel.HIGH: 10,
            LODLevel.ULTRA: 20,
        }.get(lod, 5)

        n_points = {
            LODLevel.LOW: 10,
            LODLevel.MEDIUM: 20,
            LODLevel.HIGH: 40,
            LODLevel.ULTRA: 80,
        }.get(lod, 20)

        for i in range(n_waterlines):
            # Waterline at this draft
            z = -draft + (i + 1) * draft / (n_waterlines + 1)

            points = self._generate_waterline_points(
                z=z,
                loa=loa,
                lwl=lwl,
                beam=beam,
                cwp=cwp,
                draft=draft,
                n_points=n_points,
            )

            waterline = LineData(
                points=points,
                closed=False,
                line_id=f"waterline_{i}",
            )
            waterlines.append(waterline)

        # Design waterline
        design_wl_points = self._generate_waterline_points(
            z=0.0,
            loa=loa,
            lwl=lwl,
            beam=beam,
            cwp=cwp,
            draft=draft,
            n_points=n_points,
        )
        waterlines.append(LineData(
            points=design_wl_points,
            closed=False,
            line_id="design_waterline",
        ))

        return waterlines

    def _generate_waterline_points(
        self,
        z: float,
        loa: float,
        lwl: float,
        beam: float,
        cwp: float,
        draft: float,
        n_points: int,
    ) -> List[Tuple[float, float, float]]:
        """Generate points for a waterline at height z."""
        points = []

        # Draft ratio affects waterline shape
        z_ratio = (z + draft) / draft if draft > 0 else 1.0
        z_ratio = max(0.01, min(1.0, z_ratio))

        # Local beam varies with depth
        local_beam = beam * z_ratio ** 0.5

        # Waterline length varies with depth (shorter at bottom)
        local_lwl = lwl * z_ratio ** 0.3

        # Offset from stern
        x_start = (loa - local_lwl) / 2
        x_end = x_start + local_lwl

        # Generate port side points from stern to bow
        for i in range(n_points + 1):
            x_ratio = i / n_points
            x = x_start + x_ratio * local_lwl

            # Y coordinate based on waterplane coefficient
            # Simple approximation: y = beam/2 * (1 - (x_normalized)^2)^(1/cwp_factor)
            x_normalized = abs(x_ratio - 0.5) * 2  # 0 at midship, 1 at ends

            # Entry/run shape factor
            if x_ratio < 0.5:
                # Run (aft)
                shape_factor = 1.0 / max(0.3, cwp)
            else:
                # Entry (forward)
                shape_factor = 1.0 / max(0.3, cwp * 0.9)

            y = (local_beam / 2) * (1 - x_normalized ** 2) ** shape_factor

            points.append((x, y, z))

        return points

    def _build_sectional_areas(self, lod: LODLevel) -> List[LineData]:
        """Build sectional area curve."""
        hull = self._get_hull_params()
        sections = []

        loa = hull["loa"]
        beam = hull["beam"]
        draft = hull["draft"]
        cb = hull["cb"]
        lwl = hull["lwl"]

        # Midship section area
        am = beam * draft * cb / 0.7  # Approximate based on Cm

        n_stations = {
            LODLevel.LOW: 11,
            LODLevel.MEDIUM: 21,
            LODLevel.HIGH: 41,
            LODLevel.ULTRA: 81,
        }.get(lod, 21)

        points = []
        for i in range(n_stations):
            x = i * loa / (n_stations - 1)

            # Sectional area curve (SAC) approximation
            # Based on typical displacement hull shape
            x_norm = x / loa

            if x_norm < 0.5:
                # Aft of midship
                area = am * (1 - ((0.5 - x_norm) / 0.5) ** 2)
            else:
                # Forward of midship
                area = am * (1 - ((x_norm - 0.5) / 0.5) ** 2.5)

            area = max(0, area)

            # Plot as Y = area, Z = 0
            points.append((x, area, 0))

        sections.append(LineData(
            points=points,
            closed=False,
            line_id="sectional_area_curve",
        ))

        return sections

    def _build_bonjean_curves(self, lod: LODLevel) -> List[LineData]:
        """Build Bonjean curves (sectional area vs draft)."""
        hull = self._get_hull_params()
        curves = []

        loa = hull["loa"]
        beam = hull["beam"]
        draft = hull["draft"]
        cb = hull["cb"]

        # Number of stations for Bonjean curves
        n_stations = {
            LODLevel.LOW: 5,
            LODLevel.MEDIUM: 11,
            LODLevel.HIGH: 21,
            LODLevel.ULTRA: 41,
        }.get(lod, 11)

        n_drafts = 10

        for i in range(n_stations):
            x = i * loa / (n_stations - 1)
            x_norm = x / loa

            # Calculate max section area at this station
            if x_norm < 0.5:
                area_factor = (1 - ((0.5 - x_norm) / 0.5) ** 2)
            else:
                area_factor = (1 - ((x_norm - 0.5) / 0.5) ** 2.5)

            points = []
            for j in range(n_drafts + 1):
                z_ratio = j / n_drafts
                z = -draft * z_ratio

                # Area at this draft
                # Simple approximation: area varies with draft^1.5
                area = beam * draft * cb * area_factor * z_ratio ** 1.5
                area = max(0, area)

                # Plot as (area, z) curve at station x
                points.append((x, area * 0.1, z))  # Scale area for visibility

            curves.append(LineData(
                points=points,
                closed=False,
                line_id=f"bonjean_{i}",
            ))

        return curves

    def _build_displacement_volume(self, lod: LODLevel) -> Optional[MeshData]:
        """Build mesh representing displaced volume."""
        # Complex to visualize - return None for basic implementation
        return None
