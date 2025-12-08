"""
MAGNET Loading Models (v1.1)

Loading condition data structures.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMERATIONS
# =============================================================================

class LoadingConditionType(Enum):
    """Types of loading conditions."""
    LIGHTSHIP = "lightship"
    FULL_LOAD_DEPARTURE = "full_load_departure"
    FULL_LOAD_ARRIVAL = "full_load_arrival"
    MINIMUM_OPERATING = "minimum_operating"
    BALLAST = "ballast"
    CUSTOM = "custom"


# =============================================================================
# TANK LOAD
# =============================================================================

@dataclass
class TankLoad:
    """Tank loading state for a condition."""
    tank_id: str
    fill_percent: float
    weight_mt: float
    lcg_m: float
    vcg_m: float
    tcg_m: float = 0.0
    fsm_t_m: float = 0.0  # Free surface moment

    def to_dict(self) -> Dict[str, Any]:
        """Serialize tank load."""
        return {
            "tank_id": self.tank_id,
            "fill_percent": round(self.fill_percent * 100, 1),
            "weight_mt": round(self.weight_mt, 3),
            "lcg_m": round(self.lcg_m, 3),
            "vcg_m": round(self.vcg_m, 3),
            "tcg_m": round(self.tcg_m, 3),
            "fsm_t_m": round(self.fsm_t_m, 3),
        }


# =============================================================================
# DEADWEIGHT ITEM
# =============================================================================

@dataclass
class DeadweightItem:
    """Deadweight item (crew, stores, cargo, etc.)."""
    item_id: str
    name: str
    category: str  # crew, stores, cargo, passengers, etc.
    weight_mt: float
    lcg_m: float
    vcg_m: float
    tcg_m: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize deadweight item."""
        return {
            "item_id": self.item_id,
            "name": self.name,
            "category": self.category,
            "weight_mt": round(self.weight_mt, 3),
            "lcg_m": round(self.lcg_m, 3),
            "vcg_m": round(self.vcg_m, 3),
            "tcg_m": round(self.tcg_m, 3),
        }


# =============================================================================
# LOADING CONDITION RESULT
# =============================================================================

@dataclass
class LoadingConditionResult:
    """
    Complete loading condition calculation result.

    Contains displacement, draft, trim, stability data, and limit checks.
    """
    condition_name: str
    condition_type: LoadingConditionType

    # Weight breakdown
    lightship_mt: float = 0.0
    deadweight_mt: float = 0.0
    displacement_mt: float = 0.0

    # Centers of gravity
    lcg_m: float = 0.0
    vcg_m: float = 0.0
    tcg_m: float = 0.0

    # Draft and trim
    draft_m: float = 0.0
    draft_fwd_m: float = 0.0
    draft_aft_m: float = 0.0
    trim_m: float = 0.0

    # Freeboard
    freeboard_m: float = 0.0

    # Stability
    km_m: float = 0.0
    gm_solid_m: float = 0.0
    fsc_m: float = 0.0  # Free surface correction
    gm_fluid_m: float = 0.0

    # Tank loads
    tank_loads: List[TankLoad] = field(default_factory=list)

    # Deadweight items
    deadweight_items: List[DeadweightItem] = field(default_factory=list)

    # Validation
    passes_all_criteria: bool = True
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    # Timestamp
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_fsm(self) -> float:
        """Get total free surface moment."""
        return sum(tl.fsm_t_m for tl in self.tank_loads)

    @property
    def is_stable(self) -> bool:
        """Check if condition has positive GM."""
        return self.gm_fluid_m > 0

    @property
    def meets_imo_gm(self) -> bool:
        """Check if GM meets IMO minimum (0.15m)."""
        return self.gm_fluid_m >= 0.15

    def to_dict(self) -> Dict[str, Any]:
        """Serialize loading condition result."""
        return {
            "condition_name": self.condition_name,
            "condition_type": self.condition_type.value,

            # Weight
            "lightship_mt": round(self.lightship_mt, 3),
            "deadweight_mt": round(self.deadweight_mt, 3),
            "displacement_mt": round(self.displacement_mt, 3),

            # Centers
            "lcg_m": round(self.lcg_m, 3),
            "vcg_m": round(self.vcg_m, 3),
            "tcg_m": round(self.tcg_m, 3),

            # Draft
            "draft_m": round(self.draft_m, 3),
            "draft_fwd_m": round(self.draft_fwd_m, 3),
            "draft_aft_m": round(self.draft_aft_m, 3),
            "trim_m": round(self.trim_m, 3),

            # Freeboard
            "freeboard_m": round(self.freeboard_m, 3),

            # Stability
            "km_m": round(self.km_m, 3),
            "gm_solid_m": round(self.gm_solid_m, 3),
            "fsc_m": round(self.fsc_m, 3),
            "gm_fluid_m": round(self.gm_fluid_m, 3),
            "total_fsm_t_m": round(self.total_fsm, 3),

            # Status
            "is_stable": self.is_stable,
            "meets_imo_gm": self.meets_imo_gm,
            "passes_all_criteria": self.passes_all_criteria,

            # Messages
            "warnings": self.warnings,
            "errors": self.errors,

            # Details
            "tank_loads": [tl.to_dict() for tl in self.tank_loads],
            "deadweight_items": [di.to_dict() for di in self.deadweight_items],
        }
