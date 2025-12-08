"""
systems/propulsion/propulsors.py - Propulsor definitions
ALPHA OWNS THIS FILE.

Section 26: Propulsion System
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict
import math


@dataclass
class PropellerSpecification:
    """Propeller specification."""

    propeller_id: str = ""
    prop_type: str = "fpp"

    # === GEOMETRY ===
    diameter_mm: float = 0.0
    pitch_mm: float = 0.0
    pitch_ratio: float = 0.0
    blade_area_ratio: float = 0.0
    num_blades: int = 4

    material: str = "nibral"

    # === PERFORMANCE ===
    design_rpm: float = 0.0
    design_speed_kts: float = 0.0
    design_power_kw: float = 0.0
    efficiency: float = 0.0

    weight_kg: float = 0.0

    @classmethod
    def estimate_from_power(
        cls,
        power_kw: float,
        rpm: float,
        speed_kts: float,
        num_props: int = 2,
    ) -> 'PropellerSpecification':
        """Estimate propeller size from power requirements."""
        power_per_prop = power_kw / num_props

        # Taylor wake fraction estimate for high-speed craft
        w = 0.10
        Va = speed_kts * 0.5144 * (1 - w)

        # Simplified diameter estimate (Bp-delta method)
        n_rps = rpm / 60
        D_m = 1.2 * (power_per_prop ** 0.2) / (n_rps ** 0.6) if n_rps > 0 else 1.0
        D_m = min(D_m, 2.0)

        # Pitch ratio
        pd_ratio = 1.0 + 0.1 * (speed_kts / 30)
        pd_ratio = min(pd_ratio, 1.4)

        # Blade area ratio
        bar = 0.45 + 0.05 * (power_per_prop / 500)
        bar = min(bar, 0.85)

        # Efficiency estimate
        eta = 0.65 + 0.05 * (D_m / 1.0)
        eta = min(eta, 0.72)

        # Weight estimate (NiBrAl)
        weight = 0.012 * (D_m * 1000) ** 2.5 / 1000

        return cls(
            propeller_id=f"PROP-{int(power_per_prop)}KW",
            prop_type="fpp",
            diameter_mm=D_m * 1000,
            pitch_mm=D_m * 1000 * pd_ratio,
            pitch_ratio=pd_ratio,
            blade_area_ratio=bar,
            num_blades=4 if power_per_prop < 1500 else 5,
            material="nibral",
            design_rpm=rpm,
            design_speed_kts=speed_kts,
            design_power_kw=power_per_prop,
            efficiency=eta,
            weight_kg=weight,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "propeller_id": self.propeller_id,
            "prop_type": self.prop_type,
            "diameter_mm": round(self.diameter_mm, 0),
            "pitch_mm": round(self.pitch_mm, 0),
            "pitch_ratio": round(self.pitch_ratio, 3),
            "blade_area_ratio": round(self.blade_area_ratio, 3),
            "num_blades": self.num_blades,
            "material": self.material,
            "efficiency": round(self.efficiency, 3),
            "weight_kg": round(self.weight_kg, 1),
        }


@dataclass
class WaterjetSpecification:
    """Waterjet specification."""

    waterjet_id: str = ""
    manufacturer: str = ""
    model: str = ""

    max_power_kw: float = 0.0
    max_rpm: float = 0.0
    design_speed_kts: float = 0.0

    inlet_diameter_mm: float = 0.0
    nozzle_diameter_mm: float = 0.0

    length_mm: float = 0.0
    width_mm: float = 0.0
    height_mm: float = 0.0

    dry_weight_kg: float = 0.0
    efficiency_design: float = 0.0

    @classmethod
    def estimate_from_power(
        cls,
        power_kw: float,
        speed_kts: float,
    ) -> 'WaterjetSpecification':
        """Estimate waterjet size from power."""

        inlet_d = 180 * (power_kw / 1000) ** 0.5
        inlet_d = max(300, min(inlet_d, 800))

        length = inlet_d * 3.5
        width = inlet_d * 1.5
        height = inlet_d * 1.8

        weight = 0.8 * power_kw

        eta = 0.55 + 0.005 * (speed_kts - 25)
        eta = max(0.50, min(eta, 0.72))

        return cls(
            waterjet_id=f"WJ-{int(power_kw)}KW",
            max_power_kw=power_kw,
            design_speed_kts=speed_kts,
            inlet_diameter_mm=inlet_d,
            nozzle_diameter_mm=inlet_d * 0.6,
            length_mm=length,
            width_mm=width,
            height_mm=height,
            dry_weight_kg=weight,
            efficiency_design=eta,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "waterjet_id": self.waterjet_id,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "max_power_kw": self.max_power_kw,
            "design_speed_kts": self.design_speed_kts,
            "inlet_diameter_mm": round(self.inlet_diameter_mm, 0),
            "efficiency_design": round(self.efficiency_design, 3),
            "dry_weight_kg": round(self.dry_weight_kg, 0),
        }
