"""
performance/resistance.py - Resistance prediction
BRAVO OWNS THIS FILE.

Section 39: Performance Prediction
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ResistanceComponents:
    """Resistance breakdown at a speed."""

    speed_kts: float = 0.0

    frictional_kn: float = 0.0
    residuary_kn: float = 0.0
    appendage_kn: float = 0.0
    air_kn: float = 0.0
    spray_kn: float = 0.0

    @property
    def total_kn(self) -> float:
        return (self.frictional_kn + self.residuary_kn +
                self.appendage_kn + self.air_kn + self.spray_kn)

    @property
    def total_kw(self) -> float:
        speed_m_s = self.speed_kts * 0.5144
        return self.total_kn * 1000 * speed_m_s / 1000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "speed_kts": self.speed_kts,
            "frictional_kn": round(self.frictional_kn, 2),
            "residuary_kn": round(self.residuary_kn, 2),
            "appendage_kn": round(self.appendage_kn, 2),
            "air_kn": round(self.air_kn, 2),
            "total_kn": round(self.total_kn, 2),
            "effective_power_kw": round(self.total_kw, 1),
        }


@dataclass
class SpeedPowerPoint:
    """Speed-power curve point."""

    speed_kts: float = 0.0
    resistance_kn: float = 0.0
    effective_power_kw: float = 0.0
    delivered_power_kw: float = 0.0
    shaft_power_kw: float = 0.0
    brake_power_kw: float = 0.0
    froude_number: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "speed_kts": self.speed_kts,
            "froude_number": round(self.froude_number, 3),
            "resistance_kn": round(self.resistance_kn, 2),
            "effective_power_kw": round(self.effective_power_kw, 0),
            "delivered_power_kw": round(self.delivered_power_kw, 0),
            "brake_power_kw": round(self.brake_power_kw, 0),
        }


@dataclass
class PropulsiveEfficiency:
    """Propulsive efficiency breakdown."""

    hull_efficiency: float = 1.0
    relative_rotative: float = 1.0
    propeller_efficiency: float = 0.65
    transmission_efficiency: float = 0.97

    @property
    def propulsive_coefficient(self) -> float:
        return self.hull_efficiency * self.relative_rotative * self.propeller_efficiency

    @property
    def overall_efficiency(self) -> float:
        return self.propulsive_coefficient * self.transmission_efficiency

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hull_efficiency": round(self.hull_efficiency, 3),
            "propeller_efficiency": round(self.propeller_efficiency, 3),
            "propulsive_coefficient": round(self.propulsive_coefficient, 3),
            "overall_efficiency": round(self.overall_efficiency, 3),
        }
