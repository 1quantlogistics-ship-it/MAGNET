"""
performance/envelope.py - Operational envelope definitions
BRAVO OWNS THIS FILE.

Section 40: Operational Envelope
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class OperationalLimit:
    """Single operational limit."""

    limit_id: str = ""
    limit_type: str = ""
    value: float = 0.0
    unit: str = ""
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "limit_id": self.limit_id,
            "limit_type": self.limit_type,
            "value": self.value,
            "unit": self.unit,
            "source": self.source,
        }


@dataclass
class SpeedSeaStatePoint:
    """Speed limit at a sea state."""

    sea_state: int = 0
    hs_m: float = 0.0
    max_speed_kts: float = 0.0
    limiting_factor: str = ""
    fuel_rate_l_hr: float = 0.0
    range_nm: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sea_state": self.sea_state,
            "hs_m": self.hs_m,
            "max_speed_kts": round(self.max_speed_kts, 1),
            "limiting_factor": self.limiting_factor,
            "range_nm": round(self.range_nm, 0),
        }


@dataclass
class OperationalEnvelope:
    """Complete operational envelope."""

    envelope_id: str = ""

    limits: List[OperationalLimit] = field(default_factory=list)
    speed_sea_state: List[SpeedSeaStatePoint] = field(default_factory=list)

    design_speed_kts: float = 0.0
    design_sea_state: int = 3
    max_operational_sea_state: int = 4

    endurance_at_cruise_hr: float = 0.0
    range_at_cruise_nm: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "envelope_id": self.envelope_id,
            "limits": [l.to_dict() for l in self.limits],
            "speed_sea_state": [p.to_dict() for p in self.speed_sea_state],
            "design_speed_kts": self.design_speed_kts,
            "design_sea_state": self.design_sea_state,
            "max_operational_sea_state": self.max_operational_sea_state,
            "endurance_at_cruise_hr": round(self.endurance_at_cruise_hr, 1),
            "range_at_cruise_nm": round(self.range_at_cruise_nm, 0),
        }
