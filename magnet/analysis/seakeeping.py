"""
analysis/seakeeping.py - Seakeeping analysis definitions
BRAVO OWNS THIS FILE.

Section 35: Seakeeping Analysis
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List


# Douglas Sea Scale
SEA_STATES = {
    0: {"name": "Calm (glassy)", "hs_m": 0.0},
    1: {"name": "Calm (rippled)", "hs_m": 0.1},
    2: {"name": "Smooth", "hs_m": 0.5},
    3: {"name": "Slight", "hs_m": 1.25},
    4: {"name": "Moderate", "hs_m": 2.5},
    5: {"name": "Rough", "hs_m": 4.0},
    6: {"name": "Very rough", "hs_m": 6.0},
}


# NORDFORSK Criteria for HSC
NORDFORSK_CRITERIA = {
    "bridge_vertical_accel_g": 0.20,
    "bridge_lateral_accel_g": 0.10,
    "passenger_vertical_accel_g": 0.15,
    "passenger_lateral_accel_g": 0.07,
    "roll_amplitude_deg": 8.0,
    "pitch_amplitude_deg": 5.0,
    "msi_percent": 20.0,
    "bow_vertical_accel_g": 0.40,
}


@dataclass
class MotionResponse:
    """Motion response at a point."""

    location: str = ""

    heave_amplitude_m: float = 0.0
    pitch_amplitude_deg: float = 0.0
    roll_amplitude_deg: float = 0.0

    vertical_accel_g: float = 0.0
    lateral_accel_g: float = 0.0
    longitudinal_accel_g: float = 0.0

    msi_percent: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "location": self.location,
            "heave_amplitude_m": round(self.heave_amplitude_m, 3),
            "pitch_amplitude_deg": round(self.pitch_amplitude_deg, 2),
            "roll_amplitude_deg": round(self.roll_amplitude_deg, 2),
            "vertical_accel_g": round(self.vertical_accel_g, 3),
            "lateral_accel_g": round(self.lateral_accel_g, 3),
            "msi_percent": round(self.msi_percent, 1),
        }


@dataclass
class OperabilityResult:
    """Operability assessment result."""

    sea_state: int = 0
    hs_m: float = 0.0
    criteria_met: Dict[str, bool] = field(default_factory=dict)

    @property
    def operable(self) -> bool:
        return all(self.criteria_met.values())

    @property
    def percent_met(self) -> float:
        if not self.criteria_met:
            return 0
        return sum(self.criteria_met.values()) / len(self.criteria_met) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sea_state": self.sea_state,
            "hs_m": self.hs_m,
            "criteria_met": self.criteria_met,
            "operable": self.operable,
            "percent_met": round(self.percent_met, 1),
        }


@dataclass
class SeakeepingResults:
    """Complete seakeeping analysis results."""

    roll_period_s: float = 0.0
    pitch_period_s: float = 0.0
    heave_period_s: float = 0.0

    responses: List[MotionResponse] = field(default_factory=list)
    operability_by_ss: List[OperabilityResult] = field(default_factory=list)

    max_operational_ss: int = 0
    operability_index: float = 0.0
    limiting_criterion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "roll_period_s": round(self.roll_period_s, 2),
            "pitch_period_s": round(self.pitch_period_s, 2),
            "heave_period_s": round(self.heave_period_s, 2),
            "responses": [r.to_dict() for r in self.responses],
            "operability_by_ss": [o.to_dict() for o in self.operability_by_ss],
            "max_operational_ss": self.max_operational_ss,
            "operability_index": round(self.operability_index, 1),
            "limiting_criterion": self.limiting_criterion,
        }
