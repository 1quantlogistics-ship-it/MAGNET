"""
MAGNET Propulsion Plant Estimator (Group 200)

Module 07 v1.1 - Production-Ready

Estimates propulsion system weight using specific weight method.
"""

from __future__ import annotations
from typing import List, Dict, Any
import math
import logging

from ..items import SWBSGroup, WeightItem, WeightConfidence

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Specific weight by engine type (kg per kW)
ENGINE_SPECIFIC_WEIGHTS = {
    "high_speed_diesel": 4.0,      # MTU, Caterpillar, etc.
    "medium_speed_diesel": 12.0,   # MAN, Wartsila
    "low_speed_diesel": 25.0,      # Large two-stroke
    "gas_turbine": 1.5,            # LM2500, etc.
    "outboard": 2.5,               # Yamaha, Mercury
    "electric": 3.0,               # Electric motors
    "hybrid": 5.0,                 # Diesel-electric
}

# Propulsion type factors (relative to conventional propeller)
PROPULSION_FACTORS = {
    "propeller": 1.0,
    "waterjet": 1.15,              # Heavier ducting, impeller
    "surface_drive": 0.85,        # Lighter than conventional
    "pod": 1.30,                  # Azipod, etc.
    "stern_drive": 0.90,
    "outboard": 0.70,             # Integrated with engine
}

# Transmission weight factor (per engine)
GEARBOX_FACTORS = {
    "high_speed_diesel": 0.15,    # Reduction gearbox
    "medium_speed_diesel": 0.20,
    "gas_turbine": 0.25,          # High-reduction gearbox
    "outboard": 0.0,              # Integrated
    "electric": 0.05,             # Minimal reduction
}


# =============================================================================
# PROPULSION PLANT ESTIMATOR
# =============================================================================

class PropulsionPlantEstimator:
    """
    Group 200 - Propulsion Plant weight estimator.

    Uses specific weight method based on engine type:
        W_engine = P_kW × specific_weight_kg_per_kW

    Produces weight items for:
    - Main engines
    - Gearboxes/transmissions
    - Shafting
    - Propulsors (propellers, waterjets)
    - Exhaust system
    - Engine room auxiliaries
    """

    def estimate(
        self,
        installed_power_kw: float,
        num_engines: int,
        engine_type: str = "high_speed_diesel",
        propulsion_type: str = "propeller",
        lwl: float = 30.0,
    ) -> List[WeightItem]:
        """
        Estimate propulsion plant weight.

        Args:
            installed_power_kw: Total installed power (kW)
            num_engines: Number of main engines
            engine_type: Type of main engines
            propulsion_type: Type of propulsion system
            lwl: Waterline length for positioning (m)

        Returns:
            List of WeightItem for Group 200 components
        """
        if installed_power_kw <= 0:
            return []
        if num_engines <= 0:
            num_engines = 2  # Default twin-engine

        # Get specific weight
        specific_weight = ENGINE_SPECIFIC_WEIGHTS.get(engine_type, 4.0)
        prop_factor = PROPULSION_FACTORS.get(propulsion_type, 1.0)
        gearbox_factor = GEARBOX_FACTORS.get(engine_type, 0.15)

        # Power per engine
        power_per_engine = installed_power_kw / num_engines

        items = []

        # Main engines
        engine_weight_kg = power_per_engine * specific_weight
        for i in range(num_engines):
            # Position engines side by side
            tcg = 0.0 if num_engines == 1 else (1.5 if i % 2 == 0 else -1.5)

            items.append(WeightItem(
                name=f"Main Engine {i+1}",
                weight_kg=engine_weight_kg,
                lcg_m=lwl * 0.60,        # Engine room ~60% from FP
                vcg_m=1.0,               # Above baseline
                tcg_m=tcg,
                group=SWBSGroup.GROUP_200,
                subgroup=210,
                confidence=WeightConfidence.HIGH,
                notes=f"{engine_type} {power_per_engine:.0f}kW (specific weight)",
            ))

        # Gearboxes (one per engine)
        if gearbox_factor > 0:
            gearbox_weight_kg = power_per_engine * specific_weight * gearbox_factor
            for i in range(num_engines):
                tcg = 0.0 if num_engines == 1 else (1.5 if i % 2 == 0 else -1.5)

                items.append(WeightItem(
                    name=f"Gearbox {i+1}",
                    weight_kg=gearbox_weight_kg,
                    lcg_m=lwl * 0.65,    # Aft of engine
                    vcg_m=0.8,
                    tcg_m=tcg,
                    group=SWBSGroup.GROUP_200,
                    subgroup=220,
                    confidence=WeightConfidence.HIGH,
                    notes="Reduction gearbox (parametric)",
                ))

        # Shafting (scales with power and length)
        shaft_length_m = lwl * 0.3  # Typical shaft length
        shaft_weight_kg = shaft_length_m * (installed_power_kw / 1000) * 50  # ~50 kg/m per MW
        items.append(WeightItem(
            name="Propeller Shafts",
            weight_kg=shaft_weight_kg,
            lcg_m=lwl * 0.75,        # Aft section
            vcg_m=0.5,               # Below waterline
            tcg_m=0.0,
            group=SWBSGroup.GROUP_200,
            subgroup=230,
            confidence=WeightConfidence.HIGH,
            notes=f"{num_engines} shafts (parametric)",
        ))

        # Propulsors
        propulsor_weight_kg = (installed_power_kw / num_engines) * 0.8 * prop_factor
        for i in range(num_engines):
            tcg = 0.0 if num_engines == 1 else (1.2 if i % 2 == 0 else -1.2)

            prop_name = "Propeller" if propulsion_type == "propeller" else propulsion_type.title()
            items.append(WeightItem(
                name=f"{prop_name} {i+1}",
                weight_kg=propulsor_weight_kg,
                lcg_m=lwl * 0.95,    # At stern
                vcg_m=0.3,           # Below waterline
                tcg_m=tcg,
                group=SWBSGroup.GROUP_200,
                subgroup=240,
                confidence=WeightConfidence.MEDIUM,
                notes=f"{propulsion_type} (parametric)",
            ))

        # Exhaust system
        exhaust_weight_kg = installed_power_kw * 0.2  # ~0.2 kg/kW
        items.append(WeightItem(
            name="Exhaust System",
            weight_kg=exhaust_weight_kg,
            lcg_m=lwl * 0.55,       # Above engine room
            vcg_m=2.5,              # High up
            tcg_m=0.0,
            group=SWBSGroup.GROUP_200,
            subgroup=250,
            confidence=WeightConfidence.MEDIUM,
            notes="Exhaust piping and silencers (parametric)",
        ))

        # Engine room auxiliaries (cooling, fuel systems)
        aux_weight_kg = installed_power_kw * 0.3  # ~0.3 kg/kW
        items.append(WeightItem(
            name="Engine Room Auxiliaries",
            weight_kg=aux_weight_kg,
            lcg_m=lwl * 0.58,
            vcg_m=1.2,
            tcg_m=0.0,
            group=SWBSGroup.GROUP_200,
            subgroup=260,
            confidence=WeightConfidence.LOW,
            notes="Cooling, fuel systems, controls (parametric)",
        ))

        logger.debug(
            f"Propulsion estimate: {sum(i.weight_kg for i in items)/1000:.2f} MT "
            f"({num_engines}x {engine_type} @ {power_per_engine:.0f}kW)"
        )

        return items
