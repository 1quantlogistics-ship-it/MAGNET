"""
systems/propulsion/generator.py - Propulsion system generation
ALPHA OWNS THIS FILE.

Section 26: Propulsion System
"""

from typing import Dict, Any, List
import math

from magnet.core.state_manager import StateManager
from .system import PropulsionSystem, GearboxSpecification, ShaftLine
from .engines import EngineSpecification, EngineLibrary
from .propulsors import PropellerSpecification, WaterjetSpecification


class PropulsionSystemGenerator:
    """Generate propulsion system from requirements."""

    def __init__(self, state: StateManager):
        self.state = state

    def generate(self) -> PropulsionSystem:
        """Generate complete propulsion system."""

        required_power = self.state.get("propulsion.required_power_kw", 0)
        if required_power <= 0:
            required_power = self._estimate_required_power()

        max_speed = self.state.get("mission.max_speed_kts", 30)
        propulsor_type = self.state.get("propulsion.propulsion_type", "fpp")
        num_engines = self.state.get("propulsion.num_engines", 2)

        # v1.1 FIX: Use metadata.design_id
        system = PropulsionSystem(
            system_id=f"PROP-{self.state.get('metadata.design_id', 'UNKNOWN')}",
            num_engines=num_engines,
            num_shafts=num_engines,
            propulsor_type=propulsor_type,
        )

        # Select engines
        power_per_engine = required_power / num_engines * 1.15
        system.engines = self._select_engines(power_per_engine, num_engines)

        actual_power = sum(e.mcr_kw for e in system.engines)
        power_per_shaft = actual_power / num_engines

        # Select gearboxes
        engine_rpm = system.engines[0].mcr_rpm if system.engines else 2000
        prop_rpm = self._estimate_prop_rpm(max_speed, propulsor_type)
        ratio = engine_rpm / prop_rpm if prop_rpm > 0 else 2.5

        for i in range(num_engines):
            gearbox = GearboxSpecification(
                gearbox_id=f"GB-{i+1}",
                ratio=ratio,
                max_input_power_kw=power_per_shaft,
                weight_kg=power_per_shaft * 0.3,
            )
            system.gearboxes.append(gearbox)

        # Generate shafts
        shaft_length = self.state.get("hull.lwl", 24) * 0.15
        for i in range(num_engines):
            shaft = ShaftLine.estimate_from_power(
                power_per_shaft,
                prop_rpm,
                shaft_length,
            )
            shaft.shaft_id = f"SHAFT-{i+1}"
            system.shafts.append(shaft)

        # Generate propulsors
        if propulsor_type in ["fpp", "cpp"]:
            for i in range(num_engines):
                prop = PropellerSpecification.estimate_from_power(
                    actual_power,
                    prop_rpm,
                    max_speed,
                    num_engines,
                )
                prop.propeller_id = f"PROP-{i+1}"
                system.propellers.append(prop)

        elif propulsor_type == "waterjet":
            for i in range(num_engines):
                wj = WaterjetSpecification.estimate_from_power(
                    power_per_shaft,
                    max_speed,
                )
                wj.waterjet_id = f"WJ-{i+1}"
                system.waterjets.append(wj)

        system.calculate_totals()

        return system

    def _estimate_required_power(self) -> float:
        """Estimate required power from hull and speed."""
        displacement_mt = self.state.get("weight.displacement_mt", 100)
        speed_kts = self.state.get("mission.max_speed_kts", 30)
        lwl = self.state.get("hull.lwl", 24)

        k = 0.015
        power_kw = k * (displacement_mt * 1000) ** 0.67 * speed_kts ** 3 / lwl ** 0.5
        power_kw = max(power_kw, 200)

        return power_kw

    def _estimate_prop_rpm(self, speed_kts: float, propulsor_type: str) -> float:
        """Estimate propeller/impeller RPM."""
        if propulsor_type == "waterjet":
            return 1500 + speed_kts * 20
        else:
            return 600 + speed_kts * 10

    def _select_engines(
        self,
        power_per_engine: float,
        num_engines: int,
    ) -> List[EngineSpecification]:
        """Select engines from library."""
        candidates = EngineLibrary.find_by_power(
            power_per_engine * 0.9,
            power_per_engine * 1.5,
            "diesel_high_speed",
        )

        if candidates:
            selected = min(candidates, key=lambda e: abs(e.mcr_kw - power_per_engine))
            return [selected] * num_engines

        # Create generic engine if no match
        generic = EngineSpecification(
            engine_id=f"GENERIC-{int(power_per_engine)}KW",
            manufacturer="Generic",
            model=f"{int(power_per_engine)} kW Diesel",
            engine_type="diesel_high_speed",
            mcr_kw=power_per_engine,
            mcr_rpm=2000,
            service_power_kw=power_per_engine * 0.85,
            sfoc_g_kwh=215,
            dry_weight_kg=power_per_engine * 1.5,
            wet_weight_kg=power_per_engine * 1.7,
        )
        return [generic] * num_engines
