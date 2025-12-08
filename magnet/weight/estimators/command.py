"""
MAGNET Command & Surveillance Estimator (Group 400)

Module 07 v1.1 - Production-Ready

Estimates navigation and communication equipment weight using vessel type ratios.
"""

from __future__ import annotations
from typing import List
import logging

from ..items import SWBSGroup, WeightItem, WeightConfidence

logger = logging.getLogger(__name__)


# =============================================================================
# VESSEL TYPE FACTORS
# =============================================================================

# Base electronics weight by vessel type (kg per meter of length)
VESSEL_TYPE_FACTORS = {
    "commercial": 15.0,       # Basic navigation package
    "passenger": 20.0,        # Enhanced comms, PA systems
    "patrol": 35.0,           # Radar, sensors, communications
    "military": 50.0,         # Full C4I suite
    "workboat": 12.0,         # Minimal electronics
    "yacht": 25.0,            # Navigation, entertainment
    "research": 40.0,         # Scientific instruments
    "offshore": 30.0,         # DP systems, comms
}


# =============================================================================
# COMMAND & SURVEILLANCE ESTIMATOR
# =============================================================================

class CommandSurveillanceEstimator:
    """
    Group 400 - Command & Surveillance weight estimator.

    Uses vessel type-based ratios for navigation and communication equipment.

    Produces weight items for:
    - Navigation systems (radar, GPS, AIS)
    - Communication systems
    - Bridge consoles
    - Control systems
    - Safety/alarm systems
    """

    def estimate(
        self,
        lwl: float,
        depth: float,
        vessel_type: str = "commercial",
    ) -> List[WeightItem]:
        """
        Estimate command and surveillance weight.

        Args:
            lwl: Waterline length (m)
            depth: Vessel depth (m)
            vessel_type: Type of vessel operation

        Returns:
            List of WeightItem for Group 400 components
        """
        # Get base factor for vessel type
        base_factor = VESSEL_TYPE_FACTORS.get(vessel_type, 15.0)

        # Total electronics weight
        total_weight_kg = base_factor * lwl

        items = []

        # Navigation systems (radar, GPS, AIS, ECDIS)
        nav_weight_kg = total_weight_kg * 0.35
        items.append(WeightItem(
            name="Navigation Systems",
            weight_kg=nav_weight_kg,
            lcg_m=lwl * 0.15,           # Forward, bridge area
            vcg_m=depth * 1.10,         # Above main deck
            tcg_m=0.0,
            group=SWBSGroup.GROUP_400,
            subgroup=410,
            confidence=WeightConfidence.HIGH,
            notes="Radar, GPS, AIS, ECDIS, compass (parametric)",
        ))

        # Communication systems
        comm_weight_kg = total_weight_kg * 0.25
        items.append(WeightItem(
            name="Communication Systems",
            weight_kg=comm_weight_kg,
            lcg_m=lwl * 0.18,
            vcg_m=depth * 1.05,        # Mast-mounted
            tcg_m=0.0,
            group=SWBSGroup.GROUP_400,
            subgroup=420,
            confidence=WeightConfidence.MEDIUM,
            notes="VHF, HF, satellite, intercom (parametric)",
        ))

        # Bridge consoles and displays
        bridge_weight_kg = total_weight_kg * 0.20
        items.append(WeightItem(
            name="Bridge Consoles",
            weight_kg=bridge_weight_kg,
            lcg_m=lwl * 0.12,
            vcg_m=depth * 0.95,
            tcg_m=0.0,
            group=SWBSGroup.GROUP_400,
            subgroup=430,
            confidence=WeightConfidence.HIGH,
            notes="Helm station, displays, controls (parametric)",
        ))

        # Control systems (engine room monitoring, alarms)
        control_weight_kg = total_weight_kg * 0.12
        items.append(WeightItem(
            name="Control Systems",
            weight_kg=control_weight_kg,
            lcg_m=lwl * 0.50,
            vcg_m=depth * 0.40,
            tcg_m=0.0,
            group=SWBSGroup.GROUP_400,
            subgroup=440,
            confidence=WeightConfidence.LOW,
            notes="Engine monitoring, automation (parametric)",
        ))

        # Safety and alarm systems
        safety_weight_kg = total_weight_kg * 0.08
        items.append(WeightItem(
            name="Safety & Alarm Systems",
            weight_kg=safety_weight_kg,
            lcg_m=lwl * 0.30,           # Distributed
            vcg_m=depth * 0.80,
            tcg_m=0.0,
            group=SWBSGroup.GROUP_400,
            subgroup=450,
            confidence=WeightConfidence.MEDIUM,
            notes="Fire detection, bilge alarms, GMDSS (parametric)",
        ))

        logger.debug(
            f"Command/surveillance estimate: {sum(i.weight_kg for i in items)/1000:.2f} MT "
            f"(vessel_type={vessel_type})"
        )

        return items
