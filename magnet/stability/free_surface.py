"""
MAGNET Free Surface Calculator

Module 06 v1.2 - Production-Ready

Calculates free surface correction (FSC) for slack tanks.

v1.1 FIX #1: Unit handling - divide by 1000 for kg→t conversion.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Any
import logging

from magnet.core.constants import SEAWATER_DENSITY_KG_M3, FRESHWATER_DENSITY_KG_M3

logger = logging.getLogger(__name__)


# =============================================================================
# FLUID DENSITIES
# =============================================================================

FLUID_DENSITIES = {
    "seawater": SEAWATER_DENSITY_KG_M3,  # 1025 kg/m³
    "freshwater": FRESHWATER_DENSITY_KG_M3,  # 1000 kg/m³
    "fuel_oil": 850.0,  # kg/m³ (typical)
    "diesel": 850.0,  # kg/m³
    "lube_oil": 900.0,  # kg/m³
    "ballast": SEAWATER_DENSITY_KG_M3,  # Same as seawater
}


# =============================================================================
# TANK FREE SURFACE
# =============================================================================

@dataclass
class TankFreeSurface:
    """
    Free surface data for a single tank.

    v1.1 FIX #1: Units are now consistent:
    - FSM in t-m (tonne-meters)
    - Requires division by 1000 for kg→t conversion
    """
    tank_id: str
    length_m: float
    breadth_m: float
    permeability: float
    fluid_density_kg_m3: float
    fluid_type: str

    # Calculated values
    inertia_m4: float           # Moment of inertia of free surface (m⁴)
    fsm_t_m: float              # Free surface moment (tonne-meters)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "tank_id": self.tank_id,
            "length_m": round(self.length_m, 3),
            "breadth_m": round(self.breadth_m, 3),
            "permeability": round(self.permeability, 2),
            "fluid_density_kg_m3": round(self.fluid_density_kg_m3, 1),
            "fluid_type": self.fluid_type,
            "inertia_m4": round(self.inertia_m4, 4),
            "fsm_t_m": round(self.fsm_t_m, 4),
        }


# =============================================================================
# FREE SURFACE CALCULATOR
# =============================================================================

class FreeSurfaceCalculator:
    """
    Calculator for free surface effects in slack tanks.

    Free surface reduces effective GM by raising the apparent center of gravity.

    FSM = (ρ × i) / 1000  [t-m]    # v1.1 FIX #1: divide by 1000
    FSC = Σ(FSM) / Δ      [m]

    Where:
    - ρ = fluid density (kg/m³)
    - i = moment of inertia of free surface (m⁴)
    - Δ = vessel displacement (tonnes)
    """

    def calculate_rectangular_tank(
        self,
        tank_id: str,
        length_m: float,
        breadth_m: float,
        permeability: float = 0.95,
        fluid_type: str = "seawater",
        fluid_density_kg_m3: float = None,
    ) -> TankFreeSurface:
        """
        Calculate free surface effect for a rectangular tank.

        For a rectangular tank:
        i = (1/12) × L × B³ × k

        Where:
        - L = tank length (m)
        - B = tank breadth (m)
        - k = permeability factor (typically 0.95)

        Args:
            tank_id: Tank identifier
            length_m: Tank length (m)
            breadth_m: Tank breadth (m)
            permeability: Permeability factor (default: 0.95)
            fluid_type: Type of fluid ("seawater", "freshwater", "fuel_oil", etc.)
            fluid_density_kg_m3: Override fluid density (kg/m³)

        Returns:
            TankFreeSurface with calculated FSM

        Raises:
            ValueError: If dimensions are invalid
        """
        if length_m <= 0 or breadth_m <= 0:
            raise ValueError(f"Tank dimensions must be positive: L={length_m}, B={breadth_m}")

        if permeability <= 0 or permeability > 1:
            raise ValueError(f"Permeability must be in (0, 1]: {permeability}")

        # Get fluid density
        if fluid_density_kg_m3 is None:
            fluid_density_kg_m3 = FLUID_DENSITIES.get(fluid_type, 1000.0)

        # Calculate moment of inertia
        # i = (1/12) × L × B³ × permeability
        inertia_m4 = (1.0 / 12.0) * length_m * (breadth_m ** 3) * permeability

        # Calculate free surface moment
        # v1.1 FIX #1: Divide by 1000 to convert kg to tonnes
        fsm_t_m = (fluid_density_kg_m3 * inertia_m4) / 1000.0

        return TankFreeSurface(
            tank_id=tank_id,
            length_m=length_m,
            breadth_m=breadth_m,
            permeability=permeability,
            fluid_density_kg_m3=fluid_density_kg_m3,
            fluid_type=fluid_type,
            inertia_m4=inertia_m4,
            fsm_t_m=fsm_t_m,
        )

    def calculate_trapezoidal_tank(
        self,
        tank_id: str,
        length_m: float,
        breadth_fwd_m: float,
        breadth_aft_m: float,
        permeability: float = 0.95,
        fluid_type: str = "seawater",
        fluid_density_kg_m3: float = None,
    ) -> TankFreeSurface:
        """
        Calculate free surface effect for a trapezoidal tank.

        Uses average breadth as approximation.

        Args:
            tank_id: Tank identifier
            length_m: Tank length (m)
            breadth_fwd_m: Forward breadth (m)
            breadth_aft_m: Aft breadth (m)
            permeability: Permeability factor
            fluid_type: Type of fluid
            fluid_density_kg_m3: Override fluid density

        Returns:
            TankFreeSurface with calculated FSM
        """
        # Use average breadth (simplified approximation)
        avg_breadth = (breadth_fwd_m + breadth_aft_m) / 2.0

        return self.calculate_rectangular_tank(
            tank_id=tank_id,
            length_m=length_m,
            breadth_m=avg_breadth,
            permeability=permeability,
            fluid_type=fluid_type,
            fluid_density_kg_m3=fluid_density_kg_m3,
        )

    def total_free_surface_correction(
        self,
        tanks: List[TankFreeSurface],
        displacement_mt: float,
    ) -> float:
        """
        Calculate total free surface correction.

        FSC = Σ(FSM) / Δ

        Args:
            tanks: List of TankFreeSurface objects
            displacement_mt: Vessel displacement (tonnes)

        Returns:
            Total free surface correction (m)

        Raises:
            ValueError: If displacement is invalid
        """
        if displacement_mt <= 0:
            raise ValueError(f"Displacement must be positive: {displacement_mt}")

        if not tanks:
            return 0.0

        # Sum all FSM values
        total_fsm = sum(tank.fsm_t_m for tank in tanks)

        # Calculate FSC
        fsc = total_fsm / displacement_mt

        return fsc

    def calculate_from_tank_list(
        self,
        tank_definitions: List[Dict[str, Any]],
        displacement_mt: float,
    ) -> tuple[List[TankFreeSurface], float]:
        """
        Calculate FSC from a list of tank definitions.

        Convenience method for processing multiple tanks.

        Args:
            tank_definitions: List of tank dicts with keys:
                - tank_id: str
                - length_m: float
                - breadth_m: float
                - permeability: float (optional)
                - fluid_type: str (optional)
            displacement_mt: Vessel displacement (tonnes)

        Returns:
            Tuple of (list of TankFreeSurface, total FSC)
        """
        tanks = []

        for tank_def in tank_definitions:
            tank = self.calculate_rectangular_tank(
                tank_id=tank_def["tank_id"],
                length_m=tank_def["length_m"],
                breadth_m=tank_def["breadth_m"],
                permeability=tank_def.get("permeability", 0.95),
                fluid_type=tank_def.get("fluid_type", "seawater"),
            )
            tanks.append(tank)

        total_fsc = self.total_free_surface_correction(tanks, displacement_mt)

        return tanks, total_fsc
