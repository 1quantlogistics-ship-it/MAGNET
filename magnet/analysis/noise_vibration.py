"""
analysis/noise_vibration.py - Noise and vibration analysis definitions
BRAVO OWNS THIS FILE.

Section 34: Noise & Vibration
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List
import math


@dataclass
class NoiseSource:
    """Noise source definition."""

    source_id: str = ""
    source_type: str = ""
    sound_power_level_dba: float = 0.0

    location_x: float = 0.0
    location_y: float = 0.0
    location_z: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "sound_power_level_dba": round(self.sound_power_level_dba, 1),
        }


def estimate_engine_swl(power_kw: float) -> float:
    """Estimate engine sound power level."""
    return 93 + 10 * math.log10(max(1, power_kw))


def estimate_generator_swl(power_kw: float) -> float:
    """Estimate generator sound power level."""
    return 85 + 10 * math.log10(max(1, power_kw))


# IMO A.468(XII) Noise Limits
IMO_NOISE_LIMITS = {
    "wheelhouse": 65,
    "navigation_bridge": 65,
    "radio_room": 60,
    "crew_cabin": 60,
    "officer_cabin": 55,
    "passenger_cabin": 55,
    "mess": 65,
    "recreation": 65,
    "galley": 75,
    "engine_room": 110,
    "machinery_workshop": 85,
}


@dataclass
class SpaceNoiseLevel:
    """Predicted noise level in a space."""

    space_id: str = ""
    space_type: str = ""

    predicted_level_dba: float = 0.0
    limit_dba: float = 0.0

    @property
    def compliant(self) -> bool:
        return self.predicted_level_dba <= self.limit_dba

    @property
    def margin_dba(self) -> float:
        return self.limit_dba - self.predicted_level_dba

    def to_dict(self) -> Dict[str, Any]:
        return {
            "space_id": self.space_id,
            "space_type": self.space_type,
            "predicted_level_dba": round(self.predicted_level_dba, 1),
            "limit_dba": self.limit_dba,
            "compliant": self.compliant,
            "margin_dba": round(self.margin_dba, 1),
        }


@dataclass
class IsolationMount:
    """Vibration isolation mount."""

    mount_type: str = "rubber"
    static_deflection_mm: float = 0.0
    natural_frequency_hz: float = 0.0
    isolation_efficiency: float = 0.0

    @classmethod
    def design_for_isolation(cls, disturbing_freq_hz: float, target_efficiency: float = 0.9) -> 'IsolationMount':
        """Design mount for target isolation."""
        fn = disturbing_freq_hz / 3
        delta = 25 / (fn ** 2)

        r = disturbing_freq_hz / fn
        eta = 1 - 1 / (r ** 2 - 1) if r > 1 else 0

        mount_type = "rubber" if delta < 5 else "spring"

        return cls(
            mount_type=mount_type,
            static_deflection_mm=delta,
            natural_frequency_hz=fn,
            isolation_efficiency=eta,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mount_type": self.mount_type,
            "static_deflection_mm": round(self.static_deflection_mm, 2),
            "natural_frequency_hz": round(self.natural_frequency_hz, 1),
            "isolation_efficiency": round(self.isolation_efficiency, 3),
        }


@dataclass
class NoiseVibrationResults:
    """Complete noise/vibration analysis results."""

    sources: List[NoiseSource] = field(default_factory=list)
    space_levels: List[SpaceNoiseLevel] = field(default_factory=list)
    isolation_mounts: List[Dict] = field(default_factory=list)

    @property
    def compliant(self) -> bool:
        return all(s.compliant for s in self.space_levels)

    @property
    def max_level_dba(self) -> float:
        return max((s.predicted_level_dba for s in self.space_levels), default=0)

    @property
    def spaces_exceeding(self) -> int:
        return sum(1 for s in self.space_levels if not s.compliant)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sources": [s.to_dict() for s in self.sources],
            "space_levels": [s.to_dict() for s in self.space_levels],
            "isolation_mounts": self.isolation_mounts,
            "compliant": self.compliant,
            "max_level_dba": round(self.max_level_dba, 1),
            "spaces_exceeding": self.spaces_exceeding,
        }
