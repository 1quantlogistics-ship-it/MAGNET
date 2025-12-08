"""
MAGNET Arrangement Models (v1.1)

General arrangement data structures with fixes.

Version 1.1 Fixes:
- to_dict() now includes geometry fields for reconstruction (CI#3)
- Fixed get_tank_by_id/get_compartment_by_id logic (CI#5)
- Added determinize_dict utility (CI#8)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import json
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# DETERMINIZATION UTILITY
# =============================================================================

def determinize_dict(data: Dict[str, Any], precision: int = 6) -> Dict[str, Any]:
    """
    Make a dictionary deterministic for hashing and caching.

    - Sorts all keys recursively
    - Rounds floats to consistent precision
    - Ensures consistent JSON serialization
    """
    def _process(obj):
        if isinstance(obj, float):
            return round(obj, precision)
        elif isinstance(obj, dict):
            return {k: _process(v) for k, v in sorted(obj.items())}
        elif isinstance(obj, list):
            return [_process(item) for item in obj]
        elif isinstance(obj, Enum):
            return obj.value
        return obj

    processed = _process(data)
    return json.loads(json.dumps(processed, sort_keys=True))


# =============================================================================
# ENUMERATIONS
# =============================================================================

class FluidType(Enum):
    """Types of tank fluids."""
    SEAWATER = "seawater"
    FRESHWATER = "freshwater"
    FUEL_MGO = "fuel_mgo"
    FUEL_MDO = "fuel_mdo"
    FUEL_HFO = "fuel_hfo"
    LUBE_OIL = "lube_oil"
    HYDRAULIC_OIL = "hydraulic_oil"
    SEWAGE = "sewage"


FLUID_DENSITIES = {
    FluidType.SEAWATER: 1025.0,
    FluidType.FRESHWATER: 1000.0,
    FluidType.FUEL_MGO: 850.0,
    FluidType.FUEL_MDO: 870.0,
    FluidType.FUEL_HFO: 950.0,
    FluidType.LUBE_OIL: 900.0,
    FluidType.HYDRAULIC_OIL: 870.0,
    FluidType.SEWAGE: 1010.0,
}


class SpaceType(Enum):
    """Types of spaces/compartments."""
    VOID = "void"
    BALLAST_TANK = "ballast_tank"
    FUEL_TANK = "fuel_tank"
    FRESHWATER_TANK = "freshwater_tank"
    LUBE_OIL_TANK = "lube_oil_tank"
    SEWAGE_TANK = "sewage_tank"
    ENGINE_ROOM = "engine_room"
    ACCOMMODATION = "accommodation"
    CARGO_HOLD = "cargo_hold"
    STORES = "stores"
    CHAIN_LOCKER = "chain_locker"
    STEERING_GEAR = "steering_gear"
    COFFERDAM = "cofferdam"


STANDARD_PERMEABILITIES = {
    SpaceType.VOID: 0.95,
    SpaceType.BALLAST_TANK: 0.95,
    SpaceType.FUEL_TANK: 0.95,
    SpaceType.FRESHWATER_TANK: 0.95,
    SpaceType.LUBE_OIL_TANK: 0.95,
    SpaceType.ENGINE_ROOM: 0.85,
    SpaceType.ACCOMMODATION: 0.95,
    SpaceType.CARGO_HOLD: 0.70,
    SpaceType.STORES: 0.60,
    SpaceType.CHAIN_LOCKER: 0.60,
    SpaceType.STEERING_GEAR: 0.85,
    SpaceType.COFFERDAM: 0.95,
}


class DeckType(Enum):
    """Types of decks."""
    WEATHER_DECK = "weather_deck"
    MAIN_DECK = "main_deck"
    LOWER_DECK = "lower_deck"
    TANK_TOP = "tank_top"
    PLATFORM = "platform"
    SUPERSTRUCTURE = "superstructure"


class BulkheadType(Enum):
    """Types of bulkheads."""
    COLLISION = "collision"
    WATERTIGHT = "watertight"
    STRUCTURAL = "structural"
    TANK = "tank"
    ACCOMMODATION = "accommodation"


# =============================================================================
# TANK DEFINITION (FIXED v1.1)
# =============================================================================

@dataclass
class Tank:
    """
    Tank definition with sounding/ullage calculations.

    Version 1.1 Fixes:
    - to_dict() now includes geometry fields for reconstruction (CI#3)
    """
    tank_id: str
    name: str
    fluid_type: FluidType

    # Geometry (rectangular approximation)
    length_m: float
    breadth_m: float
    height_m: float

    # Position (centroid when full)
    lcg_m: float
    vcg_m: float
    tcg_m: float = 0.0

    # Capacity (optional override)
    capacity_m3: Optional[float] = None

    # Current state
    fill_percent: float = 0.0

    # Sounding reference
    sounding_pipe_height_m: Optional[float] = None

    @property
    def fluid_density_kg_m3(self) -> float:
        """Get fluid density in kg/m³."""
        return FLUID_DENSITIES.get(self.fluid_type, 1000.0)

    @property
    def total_capacity_m3(self) -> float:
        """Get total tank capacity."""
        if self.capacity_m3 is not None:
            return self.capacity_m3
        return self.length_m * self.breadth_m * self.height_m

    @property
    def current_volume_m3(self) -> float:
        """Get current volume of fluid."""
        return self.total_capacity_m3 * self.fill_percent

    @property
    def current_weight_mt(self) -> float:
        """Get current weight of fluid in metric tons."""
        return self.current_volume_m3 * self.fluid_density_kg_m3 / 1000.0

    @property
    def current_weight_kg(self) -> float:
        """Get current weight of fluid in kg."""
        return self.current_volume_m3 * self.fluid_density_kg_m3

    @property
    def inertia_m4(self) -> float:
        """Free surface moment of inertia: i = (1/12) * L * B³"""
        return (1.0 / 12.0) * self.length_m * self.breadth_m**3

    @property
    def has_free_surface(self) -> bool:
        """Check if tank has free surface (not full or nearly empty)."""
        return 0.05 < self.fill_percent < 0.95

    @property
    def free_surface_moment_t_m(self) -> float:
        """Free surface moment: FSM = ρ * i / 1000 [t-m]"""
        if not self.has_free_surface:
            return 0.0
        return self.fluid_density_kg_m3 * self.inertia_m4 / 1000.0

    def get_vcg_at_fill(self, fill_percent: float) -> float:
        """Get VCG at a given fill percentage."""
        tank_bottom = self.vcg_m - self.height_m / 2
        fluid_height = fill_percent * self.height_m
        return tank_bottom + fluid_height / 2

    def get_current_vcg_m(self) -> float:
        """Get VCG at current fill level."""
        return self.get_vcg_at_fill(self.fill_percent)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize tank for storage.

        FIX v1.1: Includes geometry fields for reconstruction (CI#3).
        """
        return {
            "tank_id": self.tank_id,
            "name": self.name,
            "fluid_type": self.fluid_type.value,

            # GEOMETRY (REQUIRED FOR RECONSTRUCTION - v1.1 fix)
            "length_m": round(self.length_m, 3),
            "breadth_m": round(self.breadth_m, 3),
            "height_m": round(self.height_m, 3),

            # Position
            "lcg_m": round(self.lcg_m, 3),
            "vcg_m": round(self.vcg_m, 3),
            "tcg_m": round(self.tcg_m, 3),

            # Capacity & state
            "capacity_m3": round(self.total_capacity_m3, 3),
            "current_fill_percent": round(self.fill_percent * 100, 1),
            "current_weight_mt": round(self.current_weight_mt, 3),

            # FSM
            "has_free_surface": self.has_free_surface,
            "fsm_t_m": round(self.free_surface_moment_t_m, 3),
        }


# =============================================================================
# DECK DEFINITION
# =============================================================================

@dataclass
class DeckDefinition:
    """Deck definition."""
    deck_id: str
    name: str
    deck_type: DeckType
    height_above_baseline_m: float
    fwd_extent_m: float
    aft_extent_m: float
    is_freeboard_deck: bool = False
    has_camber: bool = False
    camber_mm: float = 0.0
    area_m2: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize deck definition."""
        return {
            "deck_id": self.deck_id,
            "name": self.name,
            "deck_type": self.deck_type.value,
            "height_m": round(self.height_above_baseline_m, 3),
            "fwd_extent_m": round(self.fwd_extent_m, 3),
            "aft_extent_m": round(self.aft_extent_m, 3),
            "is_freeboard_deck": self.is_freeboard_deck,
        }


# =============================================================================
# BULKHEAD DEFINITION
# =============================================================================

@dataclass
class BulkheadDefinition:
    """Bulkhead definition."""
    bulkhead_id: str
    name: str
    bulkhead_type: BulkheadType
    position_m: float
    is_transverse: bool = True
    bottom_m: float = 0.0
    top_m: float = 0.0
    is_watertight: bool = True
    is_structural: bool = True
    is_collision_bulkhead: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize bulkhead definition."""
        return {
            "bulkhead_id": self.bulkhead_id,
            "name": self.name,
            "type": self.bulkhead_type.value,
            "position_m": round(self.position_m, 3),
            "is_transverse": self.is_transverse,
            "is_watertight": self.is_watertight,
            "is_collision_bulkhead": self.is_collision_bulkhead,
        }


# =============================================================================
# COMPARTMENT DEFINITION
# =============================================================================

@dataclass
class Compartment:
    """Compartment definition."""
    compartment_id: str
    name: str
    space_type: SpaceType
    fwd_bulkhead_m: float
    aft_bulkhead_m: float
    bottom_m: float
    top_m: float
    port_m: float = 0.0
    starboard_m: float = 0.0
    volume_m3: Optional[float] = None
    lcg_m: Optional[float] = None
    vcg_m: Optional[float] = None
    tcg_m: float = 0.0
    permeability: float = 0.95
    contents: Optional[FluidType] = None
    capacity_m3: Optional[float] = None

    @property
    def length_m(self) -> float:
        """Get compartment length."""
        return abs(self.fwd_bulkhead_m - self.aft_bulkhead_m)

    @property
    def height_m(self) -> float:
        """Get compartment height."""
        return self.top_m - self.bottom_m

    @property
    def breadth_m(self) -> float:
        """Get compartment breadth."""
        return abs(self.starboard_m - self.port_m)

    def compute_volume(self) -> float:
        """Compute volume from dimensions."""
        if self.volume_m3 is not None:
            return self.volume_m3
        return self.length_m * self.breadth_m * self.height_m

    def compute_centroid(self) -> Tuple[float, float, float]:
        """Compute centroid (LCG, VCG, TCG)."""
        lcg = (self.fwd_bulkhead_m + self.aft_bulkhead_m) / 2
        vcg = (self.bottom_m + self.top_m) / 2
        tcg = (self.port_m + self.starboard_m) / 2
        return lcg, vcg, tcg

    def to_dict(self) -> Dict[str, Any]:
        """Serialize compartment."""
        return {
            "compartment_id": self.compartment_id,
            "name": self.name,
            "space_type": self.space_type.value,
            "fwd_bulkhead_m": round(self.fwd_bulkhead_m, 3),
            "aft_bulkhead_m": round(self.aft_bulkhead_m, 3),
            "bottom_m": round(self.bottom_m, 3),
            "top_m": round(self.top_m, 3),
            "volume_m3": round(self.compute_volume(), 3),
            "lcg_m": round(self.lcg_m or self.compute_centroid()[0], 3),
            "vcg_m": round(self.vcg_m or self.compute_centroid()[1], 3),
            "tcg_m": round(self.tcg_m, 3),
            "permeability": self.permeability,
        }


# =============================================================================
# GENERAL ARRANGEMENT (FIXED v1.1)
# =============================================================================

@dataclass
class GeneralArrangement:
    """
    Complete general arrangement definition.

    Version 1.1 Fixes:
    - Fixed get_tank_by_id logic (CI#5)
    - Fixed get_compartment_by_id logic (CI#5)
    """
    lwl_m: float
    beam_m: float
    depth_m: float

    decks: List[DeckDefinition] = field(default_factory=list)
    bulkheads: List[BulkheadDefinition] = field(default_factory=list)
    compartments: List[Compartment] = field(default_factory=list)
    tanks: List[Tank] = field(default_factory=list)

    version: str = "1.1"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def get_tank_by_id(self, tank_id: str) -> Optional[Tank]:
        """
        Find tank by ID.

        FIX v1.1: Corrected loop logic (CI#5).
        """
        for tank in self.tanks:
            if tank.tank_id == tank_id:
                return tank
        return None

    def get_compartment_by_id(self, comp_id: str) -> Optional[Compartment]:
        """
        Find compartment by ID.

        FIX v1.1: Corrected loop logic (CI#5).
        """
        for comp in self.compartments:
            if comp.compartment_id == comp_id:
                return comp
        return None

    def get_tanks_by_type(self, fluid_type: FluidType) -> List[Tank]:
        """Get all tanks of a specific fluid type."""
        return [t for t in self.tanks if t.fluid_type == fluid_type]

    def get_total_capacity(self, fluid_type: FluidType) -> float:
        """Get total capacity for a fluid type."""
        return sum(t.total_capacity_m3 for t in self.get_tanks_by_type(fluid_type))

    def get_collision_bulkhead(self) -> Optional[BulkheadDefinition]:
        """Get collision bulkhead."""
        for bhd in self.bulkheads:
            if bhd.is_collision_bulkhead:
                return bhd
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize with determinization."""
        data = {
            "lwl_m": self.lwl_m,
            "beam_m": self.beam_m,
            "depth_m": self.depth_m,
            "decks": [d.to_dict() for d in self.decks],
            "bulkheads": [b.to_dict() for b in self.bulkheads],
            "compartments": [c.to_dict() for c in self.compartments],
            "tanks": [t.to_dict() for t in self.tanks],
            "version": self.version,
        }
        return determinize_dict(data)
