"""
MAGNET Arrangement Generator (v1.1)

Parametric arrangement generation with service profile support.

Version 1.1 Fixes:
- Service profile support for conditional tank generation (CI#4)
- User override hooks (CI#8)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging

from .models import (
    GeneralArrangement, DeckDefinition, BulkheadDefinition,
    Compartment, Tank, DeckType, BulkheadType, SpaceType,
    FluidType, FLUID_DENSITIES
)

if TYPE_CHECKING:
    from ..core.state_manager import StateManager

logger = logging.getLogger(__name__)


# =============================================================================
# SERVICE PROFILE
# =============================================================================

@dataclass
class VesselServiceProfile:
    """
    Vessel services profile.

    Controls which tanks and systems are generated.
    """
    fuel: bool = True
    freshwater: bool = True
    sewage: bool = True
    lube_oil: bool = True
    hydraulic_oil: bool = False
    ballast: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, bool]) -> 'VesselServiceProfile':
        """Create profile from dictionary."""
        return cls(
            fuel=data.get("fuel", True),
            freshwater=data.get("freshwater", True),
            sewage=data.get("sewage", True),
            lube_oil=data.get("lube_oil", True),
            hydraulic_oil=data.get("hydraulic_oil", False),
            ballast=data.get("ballast", False),
        )

    @classmethod
    def from_vessel_type(cls, vessel_type: str, endurance_days: float = 1.0) -> 'VesselServiceProfile':
        """
        Create profile based on vessel type heuristics.

        Minimal services: rib, work_skiff, drone, unmanned, barge
        Short endurance: < 1 day → no freshwater/sewage
                        < 2 days → no sewage
        Military: adds ballast
        """
        profile = cls()

        vessel_type_lower = vessel_type.lower()

        # Minimal service vessels
        if vessel_type_lower in ["rib", "work_skiff", "drone", "unmanned", "barge", "tender"]:
            profile.freshwater = False
            profile.sewage = False
            profile.lube_oil = False

        # Short endurance
        if endurance_days < 1.0:
            profile.freshwater = False
            profile.sewage = False
        elif endurance_days < 2.0:
            profile.sewage = False

        # Military vessels
        if vessel_type_lower in ["military", "naval", "patrol_military", "combatant"]:
            profile.ballast = True

        return profile

    def to_dict(self) -> Dict[str, bool]:
        """Convert to dictionary."""
        return {
            "fuel": self.fuel,
            "freshwater": self.freshwater,
            "sewage": self.sewage,
            "lube_oil": self.lube_oil,
            "hydraulic_oil": self.hydraulic_oil,
            "ballast": self.ballast,
        }


# =============================================================================
# ARRANGEMENT GENERATOR
# =============================================================================

class ArrangementGenerator:
    """
    Generates parametric general arrangement.

    Version 1.1 Fixes:
    - Service profile support for conditional tank generation (CI#4)
    - User override hooks (CI#8)
    """

    def generate(
        self,
        lwl: float,
        beam: float,
        depth: float,
        draft: float,
        vessel_type: str = "patrol",
        crew_size: int = 6,
        range_nm: float = 500,
        installed_power_kw: float = 1000,
        endurance_days: float = 3.0,
        services: Optional[VesselServiceProfile] = None,
    ) -> GeneralArrangement:
        """
        Generate complete arrangement.

        Args:
            lwl: Waterline length (m)
            beam: Beam (m)
            depth: Depth (m)
            draft: Draft (m)
            vessel_type: Type of vessel
            crew_size: Number of crew
            range_nm: Design range (nm)
            installed_power_kw: Installed power (kW)
            endurance_days: Endurance in days
            services: Optional service profile. If None, derived from vessel_type.

        Returns:
            GeneralArrangement with all components
        """
        # Derive service profile if not provided
        if services is None:
            services = VesselServiceProfile.from_vessel_type(vessel_type, endurance_days)

        arrangement = GeneralArrangement(
            lwl_m=lwl,
            beam_m=beam,
            depth_m=depth,
        )

        # Generate decks
        arrangement.decks = self._generate_decks(lwl, beam, depth)

        # Generate bulkheads
        arrangement.bulkheads = self._generate_bulkheads(lwl, depth, vessel_type)

        # Generate compartments
        arrangement.compartments = self._generate_compartments(
            lwl, beam, depth, draft, vessel_type, arrangement.bulkheads
        )

        # Generate tanks (with service profile)
        arrangement.tanks = self._generate_tanks(
            lwl, beam, depth, draft,
            range_nm, installed_power_kw, crew_size, endurance_days,
            services,
        )

        logger.debug(
            f"Generated arrangement: {len(arrangement.decks)} decks, "
            f"{len(arrangement.bulkheads)} bulkheads, "
            f"{len(arrangement.compartments)} compartments, "
            f"{len(arrangement.tanks)} tanks"
        )

        return arrangement

    def _generate_decks(self, lwl: float, beam: float, depth: float) -> List[DeckDefinition]:
        """Generate deck definitions."""
        decks = []

        # Main deck
        decks.append(DeckDefinition(
            deck_id="DK-01",
            name="Main Deck",
            deck_type=DeckType.MAIN_DECK,
            height_above_baseline_m=depth,
            fwd_extent_m=0.0,
            aft_extent_m=lwl,
            is_freeboard_deck=True,
            has_camber=True,
            camber_mm=beam * 1000 / 50,
            area_m2=lwl * beam * 0.75,
        ))

        # Tank top
        tank_top_height = depth * 0.25
        decks.append(DeckDefinition(
            deck_id="DK-02",
            name="Tank Top",
            deck_type=DeckType.TANK_TOP,
            height_above_baseline_m=tank_top_height,
            fwd_extent_m=lwl * 0.1,
            aft_extent_m=lwl * 0.9,
            is_freeboard_deck=False,
        ))

        # Wheelhouse deck (if vessel large enough)
        if lwl > 15:
            decks.append(DeckDefinition(
                deck_id="DK-03",
                name="Wheelhouse Deck",
                deck_type=DeckType.SUPERSTRUCTURE,
                height_above_baseline_m=depth + 2.2,
                fwd_extent_m=lwl * 0.15,
                aft_extent_m=lwl * 0.45,
                is_freeboard_deck=False,
            ))

        return decks

    def _generate_bulkheads(
        self, lwl: float, depth: float, vessel_type: str
    ) -> List[BulkheadDefinition]:
        """Generate bulkhead definitions."""
        bulkheads = []

        # Collision bulkhead
        collision_pos = max(lwl * 0.05, 2.0)
        bulkheads.append(BulkheadDefinition(
            bulkhead_id="BHD-01",
            name="Collision Bulkhead",
            bulkhead_type=BulkheadType.COLLISION,
            position_m=collision_pos,
            is_transverse=True,
            bottom_m=0.0,
            top_m=depth,
            is_watertight=True,
            is_collision_bulkhead=True,
        ))

        # Engine room forward bulkhead
        er_fwd = lwl * 0.55
        bulkheads.append(BulkheadDefinition(
            bulkhead_id="BHD-02",
            name="Engine Room FWD",
            bulkhead_type=BulkheadType.WATERTIGHT,
            position_m=er_fwd,
            is_transverse=True,
            bottom_m=0.0,
            top_m=depth,
            is_watertight=True,
        ))

        # Engine room aft bulkhead
        er_aft = lwl * 0.85
        bulkheads.append(BulkheadDefinition(
            bulkhead_id="BHD-03",
            name="Engine Room AFT",
            bulkhead_type=BulkheadType.WATERTIGHT,
            position_m=er_aft,
            is_transverse=True,
            bottom_m=0.0,
            top_m=depth,
            is_watertight=True,
        ))

        # Transom
        bulkheads.append(BulkheadDefinition(
            bulkhead_id="BHD-04",
            name="Transom",
            bulkhead_type=BulkheadType.STRUCTURAL,
            position_m=lwl,
            is_transverse=True,
            bottom_m=0.0,
            top_m=depth,
            is_watertight=True,
        ))

        return bulkheads

    def _generate_compartments(
        self,
        lwl: float,
        beam: float,
        depth: float,
        draft: float,
        vessel_type: str,
        bulkheads: List[BulkheadDefinition],
    ) -> List[Compartment]:
        """Generate compartment definitions."""
        compartments = []

        collision_pos = bulkheads[0].position_m
        er_fwd = bulkheads[1].position_m
        er_aft = bulkheads[2].position_m

        # Forepeak
        compartments.append(Compartment(
            compartment_id="COMP-01",
            name="Forepeak",
            space_type=SpaceType.CHAIN_LOCKER,
            fwd_bulkhead_m=0.0,
            aft_bulkhead_m=collision_pos,
            bottom_m=0.0,
            top_m=depth,
            port_m=-beam / 2 * 0.3,
            starboard_m=beam / 2 * 0.3,
            permeability=0.60,
        ))

        # Forward stores
        compartments.append(Compartment(
            compartment_id="COMP-02",
            name="Forward Stores",
            space_type=SpaceType.STORES,
            fwd_bulkhead_m=collision_pos,
            aft_bulkhead_m=er_fwd,
            bottom_m=depth * 0.25,
            top_m=depth,
            port_m=-beam / 2 * 0.9,
            starboard_m=beam / 2 * 0.9,
            permeability=0.60,
        ))

        # Engine room
        compartments.append(Compartment(
            compartment_id="COMP-03",
            name="Engine Room",
            space_type=SpaceType.ENGINE_ROOM,
            fwd_bulkhead_m=er_fwd,
            aft_bulkhead_m=er_aft,
            bottom_m=0.0,
            top_m=depth,
            port_m=-beam / 2 * 0.95,
            starboard_m=beam / 2 * 0.95,
            permeability=0.85,
        ))

        # Steering gear
        compartments.append(Compartment(
            compartment_id="COMP-04",
            name="Steering Gear",
            space_type=SpaceType.STEERING_GEAR,
            fwd_bulkhead_m=er_aft,
            aft_bulkhead_m=lwl,
            bottom_m=0.0,
            top_m=depth * 0.6,
            port_m=-beam / 2 * 0.8,
            starboard_m=beam / 2 * 0.8,
            permeability=0.85,
        ))

        return compartments

    def _generate_tanks(
        self,
        lwl: float,
        beam: float,
        depth: float,
        draft: float,
        range_nm: float,
        installed_power_kw: float,
        crew_size: int,
        endurance_days: float,
        services: VesselServiceProfile,
    ) -> List[Tank]:
        """
        Generate tank definitions.

        FIX v1.1: Respects service profile for conditional generation (CI#4).
        """
        tanks = []

        # Double bottom height
        db_height = depth * 0.20

        # === FUEL TANKS ===
        if services.fuel:
            # Calculate fuel requirement
            cruise_hours = range_nm / 10.0  # Assume ~10 knots cruise
            fuel_kg = installed_power_kw * 0.7 * 0.21 * cruise_hours  # 70% load, 210 g/kWh
            fuel_m3 = fuel_kg / FLUID_DENSITIES[FluidType.FUEL_MGO] * 1.1  # 10% reserve

            tank_length = lwl * 0.25
            tank_breadth = (beam * 0.4) / 2
            tank_height = db_height

            # Port fuel tank
            tanks.append(Tank(
                tank_id="TK-FO-01P",
                name="Fuel Oil Tank #1 Port",
                fluid_type=FluidType.FUEL_MGO,
                length_m=tank_length,
                breadth_m=tank_breadth,
                height_m=tank_height,
                lcg_m=lwl * 0.55,
                vcg_m=tank_height / 2,
                tcg_m=-beam * 0.2,
                fill_percent=1.0,
            ))

            # Starboard fuel tank
            tanks.append(Tank(
                tank_id="TK-FO-01S",
                name="Fuel Oil Tank #1 Stbd",
                fluid_type=FluidType.FUEL_MGO,
                length_m=tank_length,
                breadth_m=tank_breadth,
                height_m=tank_height,
                lcg_m=lwl * 0.55,
                vcg_m=tank_height / 2,
                tcg_m=beam * 0.2,
                fill_percent=1.0,
            ))

            # Day tank
            tanks.append(Tank(
                tank_id="TK-FO-DAY",
                name="Fuel Day Tank",
                fluid_type=FluidType.FUEL_MGO,
                length_m=1.5,
                breadth_m=1.0,
                height_m=0.8,
                lcg_m=lwl * 0.60,
                vcg_m=depth * 0.4,
                tcg_m=0.0,
                fill_percent=0.8,
            ))

        # === FRESHWATER TANK ===
        if services.freshwater:
            fw_m3 = crew_size * 0.1 * endurance_days
            tanks.append(Tank(
                tank_id="TK-FW-01",
                name="Freshwater Tank",
                fluid_type=FluidType.FRESHWATER,
                length_m=2.0,
                breadth_m=1.5,
                height_m=1.0,
                capacity_m3=fw_m3,
                lcg_m=lwl * 0.40,
                vcg_m=depth * 0.3,
                tcg_m=0.0,
                fill_percent=1.0,
            ))

        # === LUBE OIL TANK ===
        if services.lube_oil:
            tanks.append(Tank(
                tank_id="TK-LO-01",
                name="Lube Oil Tank",
                fluid_type=FluidType.LUBE_OIL,
                length_m=1.0,
                breadth_m=0.8,
                height_m=0.6,
                lcg_m=lwl * 0.62,
                vcg_m=depth * 0.35,
                tcg_m=0.0,
                fill_percent=1.0,
            ))

        # === SEWAGE TANK ===
        if services.sewage:
            tanks.append(Tank(
                tank_id="TK-SEW-01",
                name="Sewage Holding Tank",
                fluid_type=FluidType.SEWAGE,
                length_m=1.5,
                breadth_m=1.0,
                height_m=0.8,
                lcg_m=lwl * 0.45,
                vcg_m=depth * 0.25,
                tcg_m=0.0,
                fill_percent=0.0,
            ))

        # === HYDRAULIC OIL TANK ===
        if services.hydraulic_oil:
            tanks.append(Tank(
                tank_id="TK-HYD-01",
                name="Hydraulic Oil Tank",
                fluid_type=FluidType.HYDRAULIC_OIL,
                length_m=0.8,
                breadth_m=0.6,
                height_m=0.5,
                lcg_m=lwl * 0.58,
                vcg_m=depth * 0.40,
                tcg_m=0.0,
                fill_percent=1.0,
            ))

        # === BALLAST TANKS ===
        if services.ballast:
            # Forward ballast
            tanks.append(Tank(
                tank_id="TK-BW-01",
                name="Forward Ballast Tank",
                fluid_type=FluidType.SEAWATER,
                length_m=lwl * 0.08,
                breadth_m=beam * 0.6,
                height_m=db_height,
                lcg_m=lwl * 0.10,
                vcg_m=db_height / 2,
                tcg_m=0.0,
                fill_percent=0.0,
            ))

            # Aft ballast
            tanks.append(Tank(
                tank_id="TK-BW-02",
                name="Aft Ballast Tank",
                fluid_type=FluidType.SEAWATER,
                length_m=lwl * 0.08,
                breadth_m=beam * 0.6,
                height_m=db_height,
                lcg_m=lwl * 0.90,
                vcg_m=db_height / 2,
                tcg_m=0.0,
                fill_percent=0.0,
            ))

        return tanks
