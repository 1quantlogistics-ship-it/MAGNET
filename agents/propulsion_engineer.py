"""
MAGNET Propulsion Engineer Agent
=================================

The Propulsion Engineer agent designs propulsion systems based on hull parameters
and mission requirements.

Responsibilities:
- Read hull_params and mission from memory
- Calculate required power using resistance data
- Select appropriate engines (initially hardcoded, later from database)
- Size propellers or waterjets
- Calculate range and endurance
- Write propulsion_config.json to memory

Communication Flow (from Operations Guide):
1. Naval Architect writes hull_params.json with resistance data
2. Orchestrator triggers Propulsion Engineer
3. Propulsion Engineer proposes propulsion config → propulsion_config.json
4. Downstream agents use propulsion data for weight, arrangement, etc.
"""

import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base import BaseAgent, AgentResponse
from memory.file_io import MemoryFileIO
from memory.schemas import DesignPhase

# Import ALPHA's resistance module
try:
    from physics.resistance import (
        calculate_total_resistance,
        ResistanceResult,
    )
    ALPHA_RESISTANCE_AVAILABLE = True
except ImportError:
    ALPHA_RESISTANCE_AVAILABLE = False
    ResistanceResult = None


# Engine database (simplified - would be in databases/ for production)
ENGINE_DATABASE = [
    {
        "manufacturer": "MTU",
        "model": "12V2000 M96L",
        "power_kw": 1432,
        "weight_kg": 2380,
        "length_mm": 2147,
        "width_mm": 1214,
        "height_mm": 1264,
        "fuel_consumption_full_lph": 340,
        "fuel_consumption_75_lph": 255,
        "rpm_rated": 2450,
        "classification": ["ABS", "DNV", "Lloyds"],
    },
    {
        "manufacturer": "MTU",
        "model": "16V2000 M96",
        "power_kw": 1939,
        "weight_kg": 2870,
        "length_mm": 2450,
        "width_mm": 1214,
        "height_mm": 1264,
        "fuel_consumption_full_lph": 460,
        "fuel_consumption_75_lph": 345,
        "rpm_rated": 2450,
        "classification": ["ABS", "DNV", "Lloyds"],
    },
    {
        "manufacturer": "MAN",
        "model": "D2862 LE463",
        "power_kw": 1213,
        "weight_kg": 2150,
        "length_mm": 1950,
        "width_mm": 1150,
        "height_mm": 1200,
        "fuel_consumption_full_lph": 290,
        "fuel_consumption_75_lph": 220,
        "rpm_rated": 2300,
        "classification": ["ABS", "DNV"],
    },
    {
        "manufacturer": "Caterpillar",
        "model": "C32",
        "power_kw": 1417,
        "weight_kg": 2680,
        "length_mm": 2230,
        "width_mm": 1240,
        "height_mm": 1320,
        "fuel_consumption_full_lph": 335,
        "fuel_consumption_75_lph": 250,
        "rpm_rated": 2300,
        "classification": ["ABS", "DNV", "Lloyds"],
    },
    {
        "manufacturer": "Volvo Penta",
        "model": "D13-1000",
        "power_kw": 736,
        "weight_kg": 1320,
        "length_mm": 1580,
        "width_mm": 980,
        "height_mm": 1050,
        "fuel_consumption_full_lph": 180,
        "fuel_consumption_75_lph": 135,
        "rpm_rated": 2200,
        "classification": ["ABS", "DNV"],
    },
    {
        "manufacturer": "Cummins",
        "model": "QSK38-M",
        "power_kw": 1119,
        "weight_kg": 2950,
        "length_mm": 2100,
        "width_mm": 1350,
        "height_mm": 1450,
        "fuel_consumption_full_lph": 265,
        "fuel_consumption_75_lph": 200,
        "rpm_rated": 1900,
        "classification": ["ABS", "DNV", "Lloyds"],
    },
]


class PropulsionEngineerAgent(BaseAgent):
    """
    Propulsion Engineer Agent - Propulsion System Design.

    Selects engines, gearboxes, and propellers based on hull and mission requirements.
    Uses resistance data to size propulsion system.
    """

    PROPULSION_PROMPT = """You are the Propulsion Engineer Agent for MAGNET (Multi-Agent Guided Naval Engineering Testbed).

Your role is to design propulsion systems based on hull parameters and mission requirements.

## Your Responsibilities:
1. Read hull parameters and mission requirements
2. Calculate required power from resistance data
3. Select appropriate main engines
4. Size transmission (gearbox ratio)
5. Size propellers (diameter, pitch, blades)
6. Calculate range and endurance at various speeds
7. Verify propulsion meets mission requirements

## Input Context:
You will receive:
- Hull parameters with resistance calculations
- Mission requirements (speed, range, fuel capacity)
- Classification requirements

## Output Format:
Respond with reasoning followed by JSON with PROPULSION_JSON: marker.

Example output:
```
Based on the resistance data and mission requirements:
- Required power at design speed: 2,864 kW (with 15% sea margin)
- Selected twin MTU 12V2000 M96L engines (1,432 kW each)
- ZF 3050 gearboxes at 1.75:1 ratio
- 5-blade fixed pitch propellers, 850mm diameter

PROPULSION_JSON:
{
  "propulsion_type": "diesel_mechanical",
  "num_engines": 2,
  "num_shafts": 2,
  "main_engines": {
    "manufacturer": "MTU",
    "model": "12V2000 M96L",
    "power_kw_each": 1432,
    "total_power_kw": 2864
  },
  "gearbox": {
    "model": "ZF 3050",
    "ratio": 1.75
  },
  "propellers": {
    "type": "fixed_pitch",
    "diameter_mm": 850,
    "pitch_mm": 1020,
    "blades": 5
  },
  "performance": {
    "design_speed_kts": 35,
    "cruise_speed_kts": 25,
    "range_at_cruise_nm": 312
  }
}
```

## Design Guidelines:

### Engine Selection:
- Total installed power = required power × 1.15 (sea margin)
- Select engines with good power density for high-speed craft
- Consider fuel consumption at cruise speed for range

### Propeller Sizing:
- Diameter limited by draft (typically D ≤ 0.7 × draft)
- Pitch/Diameter ratio: 0.9-1.3 typical for high-speed
- 4-5 blades for patrol vessels
- Consider cavitation at high speeds

### Range Calculation:
- Range = (fuel capacity / consumption rate) × cruise speed
- Include 10% reserve in calculations
"""

    def __init__(
        self,
        agent_id: str = "propulsion_engineer_001",
        memory_path: str = "memory",
        **kwargs
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="propulsion_engineer",
            memory_path=memory_path,
            **kwargs
        )

    @property
    def system_prompt(self) -> str:
        return self.PROPULSION_PROMPT

    def _read_design_data(self) -> tuple[Optional[Dict], Optional[Dict]]:
        """Read hull_params and mission from memory."""
        hull_params = self.memory.read("hull_params")
        mission = self.memory.read("mission")
        return hull_params, mission

    def _select_engines(
        self,
        required_power_kw: float,
        num_engines: int = 2
    ) -> Optional[Dict[str, Any]]:
        """
        Select engines from database.

        Args:
            required_power_kw: Total required power in kW
            num_engines: Number of engines (typically 2)

        Returns:
            Selected engine data or None if no suitable engine found
        """
        power_per_engine = required_power_kw / num_engines

        # Find engines that can provide required power with some margin
        suitable_engines = []
        for engine in ENGINE_DATABASE:
            if engine["power_kw"] >= power_per_engine * 0.85:  # Allow slight underpower
                margin = (engine["power_kw"] * num_engines - required_power_kw) / required_power_kw
                suitable_engines.append({
                    **engine,
                    "margin": margin,
                    "total_power": engine["power_kw"] * num_engines,
                })

        if not suitable_engines:
            return None

        # Sort by closest match (smallest positive margin preferred)
        suitable_engines.sort(key=lambda e: (abs(e["margin"]), e["weight_kg"]))

        return suitable_engines[0]

    def _calculate_propeller_size(
        self,
        shaft_power_kw: float,
        rpm: float,
        draft_m: float,
        speed_kts: float
    ) -> Dict[str, Any]:
        """
        Size propeller based on power and geometry constraints.

        Returns:
            Propeller specification dictionary
        """
        # Maximum diameter from draft (70% of draft is typical limit)
        max_diameter_m = draft_m * 0.7

        # Optimal diameter estimation (simplified Bp-delta method)
        # D = K * (P/N^2)^0.5 where K is empirical constant
        # For high-speed craft, K ≈ 0.5-0.7
        optimal_diameter_m = 0.6 * ((shaft_power_kw / (rpm ** 2)) ** 0.5) * 10

        # Use smaller of optimal and maximum
        diameter_m = min(optimal_diameter_m, max_diameter_m)
        diameter_mm = max(500, diameter_m * 1000)  # Minimum 500mm

        # Pitch/Diameter ratio (higher for faster vessels)
        froude_factor = speed_kts / 20  # Rough Froude proxy
        pd_ratio = min(1.3, max(0.9, 0.9 + froude_factor * 0.1))
        pitch_mm = diameter_mm * pd_ratio

        # Blade count (5 for high-speed, 4 for medium)
        blades = 5 if speed_kts > 30 else 4

        return {
            "type": "fixed_pitch",
            "diameter_mm": round(diameter_mm, 0),
            "pitch_mm": round(pitch_mm, 0),
            "pd_ratio": round(pd_ratio, 2),
            "blades": blades,
            "material": "NiBrAl",
        }

    def _calculate_range(
        self,
        fuel_capacity_l: float,
        consumption_lph: float,
        speed_kts: float,
        reserve_fraction: float = 0.10
    ) -> Dict[str, float]:
        """Calculate range and endurance."""
        usable_fuel = fuel_capacity_l * (1 - reserve_fraction)
        endurance_hrs = usable_fuel / consumption_lph if consumption_lph > 0 else 0
        range_nm = endurance_hrs * speed_kts

        return {
            "fuel_capacity_l": fuel_capacity_l,
            "usable_fuel_l": usable_fuel,
            "consumption_lph": consumption_lph,
            "endurance_hrs": round(endurance_hrs, 1),
            "range_nm": round(range_nm, 0),
            "reserve_fraction": reserve_fraction,
        }

    def design_propulsion(
        self,
        hull_params: Optional[Dict[str, Any]] = None,
        mission: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Design propulsion system based on hull and mission.

        Args:
            hull_params: Hull parameters (reads from memory if not provided)
            mission: Mission data (reads from memory if not provided)

        Returns:
            AgentResponse with propulsion configuration
        """
        # Read from memory if not provided
        if hull_params is None or mission is None:
            stored_hull, stored_mission = self._read_design_data()
            hull_params = hull_params or stored_hull
            mission = mission or stored_mission

        # Check prerequisites
        if hull_params is None:
            return AgentResponse(
                agent_id=self.agent_id,
                content="No hull parameters found. Naval Architect must design hull first.",
                confidence=0.0,
                concerns=["Hull parameters not defined"],
            )

        if mission is None:
            return AgentResponse(
                agent_id=self.agent_id,
                content="No mission data found. Director must create mission first.",
                confidence=0.0,
                concerns=["Mission not defined"],
            )

        concerns = []

        # Get resistance data from hull_params
        resistance = hull_params.get("resistance", {})
        design_speed = mission.get("design_speed_kts") or mission.get("speed_max_kts", 25)
        cruise_speed = mission.get("cruise_speed_kts", design_speed * 0.7)

        # Get required power
        if resistance:
            delivered_power_kw = resistance.get("delivered_power_kW", 0)
        else:
            # Estimate from displacement if no resistance data
            displacement = hull_params.get("displacement_tonnes", 100)
            # Rough estimate: 50-100 kW per tonne at high speed
            delivered_power_kw = displacement * 60 * (design_speed / 30) ** 3
            concerns.append("No resistance data - power estimated from displacement")

        # Add sea margin (15%)
        required_power_kw = delivered_power_kw * 1.15

        # Select engines
        num_engines = 2  # Twin engine default for patrol vessels
        selected_engine = self._select_engines(required_power_kw, num_engines)

        if selected_engine is None:
            return AgentResponse(
                agent_id=self.agent_id,
                content=f"No suitable engines found for {required_power_kw:.0f} kW requirement",
                confidence=0.0,
                concerns=["Engine selection failed - required power exceeds available options"],
            )

        # Calculate total installed power
        installed_power_kw = selected_engine["power_kw"] * num_engines

        # Size propellers
        draft = hull_params.get("draft", 2.0)
        propeller = self._calculate_propeller_size(
            shaft_power_kw=installed_power_kw / num_engines,
            rpm=selected_engine["rpm_rated"] / 1.75,  # Assume 1.75:1 reduction
            draft_m=draft,
            speed_kts=design_speed
        )

        # Calculate range
        fuel_capacity = mission.get("fuel_capacity_l", 4500)  # Default 4500L
        range_at_cruise = self._calculate_range(
            fuel_capacity_l=fuel_capacity,
            consumption_lph=selected_engine["fuel_consumption_75_lph"] * num_engines,
            speed_kts=cruise_speed
        )

        range_at_design = self._calculate_range(
            fuel_capacity_l=fuel_capacity,
            consumption_lph=selected_engine["fuel_consumption_full_lph"] * num_engines,
            speed_kts=design_speed
        )

        # Check range against mission requirements
        required_range = mission.get("endurance_nm") or mission.get("range_nm", 300)
        if range_at_cruise["range_nm"] < required_range:
            concerns.append(
                f"Range at cruise ({range_at_cruise['range_nm']:.0f} nm) "
                f"< mission requirement ({required_range} nm)"
            )

        # Build propulsion config
        propulsion_config = {
            "propulsion_type": "diesel_mechanical",
            "num_engines": num_engines,
            "num_shafts": num_engines,  # One shaft per engine
            "main_engines": {
                "manufacturer": selected_engine["manufacturer"],
                "model": selected_engine["model"],
                "power_kw_each": selected_engine["power_kw"],
                "total_power_kw": installed_power_kw,
                "weight_kg_each": selected_engine["weight_kg"],
                "total_weight_kg": selected_engine["weight_kg"] * num_engines,
                "rpm_rated": selected_engine["rpm_rated"],
                "fuel_consumption_full_lph": selected_engine["fuel_consumption_full_lph"],
                "fuel_consumption_75_lph": selected_engine["fuel_consumption_75_lph"],
            },
            "gearbox": {
                "type": "reduction",
                "ratio": 1.75,
                "estimated_weight_kg": 400 * num_engines,
            },
            "propellers": propeller,
            "performance": {
                "required_power_kw": round(required_power_kw, 0),
                "installed_power_kw": installed_power_kw,
                "power_margin_pct": round((installed_power_kw - required_power_kw) / required_power_kw * 100, 1),
                "design_speed_kts": design_speed,
                "cruise_speed_kts": cruise_speed,
                "range_at_cruise_nm": range_at_cruise["range_nm"],
                "range_at_design_nm": range_at_design["range_nm"],
                "endurance_at_cruise_hrs": range_at_cruise["endurance_hrs"],
            },
            "fuel_system": {
                "capacity_l": fuel_capacity,
                "consumption_at_cruise_lph": selected_engine["fuel_consumption_75_lph"] * num_engines,
                "consumption_at_design_lph": selected_engine["fuel_consumption_full_lph"] * num_engines,
            },
            "proposed_by": self.agent_id,
            "timestamp": datetime.now().isoformat(),
        }

        # Write to memory
        self.memory.write("propulsion_config", propulsion_config, validate=False)

        # Update system state
        self.memory.update_system_state(
            current_phase=DesignPhase.PROPULSION,
            status="propulsion_proposed",
        )

        # Log decision
        self.log_decision({
            "action": "propulsion_proposed",
            "engine_selection": f"{num_engines}x {selected_engine['manufacturer']} {selected_engine['model']}",
            "installed_power_kw": installed_power_kw,
            "range_at_cruise_nm": range_at_cruise["range_nm"],
        })

        # Calculate confidence
        confidence = 0.8
        if concerns:
            confidence -= 0.1 * min(len(concerns), 3)
        if selected_engine["margin"] < 0.1:
            concerns.append("Tight power margin - consider larger engines")
            confidence -= 0.1

        # Build response content
        content = (
            f"Propulsion: {num_engines}x {selected_engine['manufacturer']} {selected_engine['model']} "
            f"({installed_power_kw} kW) | "
            f"Range={range_at_cruise['range_nm']:.0f}nm @ {cruise_speed}kts"
        )

        return AgentResponse(
            agent_id=self.agent_id,
            content=content,
            confidence=max(0.1, confidence),
            reasoning=f"Selected engines based on {required_power_kw:.0f}kW requirement with sea margin",
            proposals=[propulsion_config],
            concerns=concerns,
            metadata={
                "installed_power_kw": installed_power_kw,
                "range_nm": range_at_cruise["range_nm"],
                "engine": f"{selected_engine['manufacturer']} {selected_engine['model']}",
            },
        )

    def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Process input - main entry point.

        Args:
            input_data: Optional hull_params/mission or empty to read from memory

        Returns:
            AgentResponse with propulsion design proposal
        """
        hull_params = input_data.get("hull_params") if input_data else None
        mission = input_data.get("mission") if input_data else None
        return self.design_propulsion(hull_params, mission)


# Convenience function
def create_propulsion_engineer(memory_path: str = "memory", **kwargs) -> PropulsionEngineerAgent:
    """Create a Propulsion Engineer agent instance."""
    return PropulsionEngineerAgent(memory_path=memory_path, **kwargs)
