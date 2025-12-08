"""
systems/electrical/generator.py - Electrical system generation
ALPHA OWNS THIS FILE.

Section 27: Electrical System
"""

from typing import Dict, Any, List

from magnet.core.state_manager import StateManager
from .schema import ElectricalSystem, ElectricalLoad, GeneratorSet, BatteryBank


class ElectricalSystemGenerator:
    """Generate electrical system from requirements."""

    LOAD_TEMPLATES = {
        "navigation": [
            ("Radar", 0.5, 0.45),
            ("GPS/Chartplotter", 0.05, 0.05),
            ("AIS", 0.02, 0.02),
            ("VHF Radio", 0.025, 0.02),
            ("Compass", 0.01, 0.01),
            ("Depth Sounder", 0.02, 0.02),
            ("Autopilot", 0.15, 0.10),
        ],
        "lighting": [
            ("Navigation Lights", 0.1, 0.1),
            ("Interior Lighting", 0.5, 0.3),
            ("Deck Lights", 0.3, 0.15),
            ("Searchlight", 1.0, 0.2),
        ],
        "safety": [
            ("Fire Detection", 0.05, 0.05),
            ("Bilge Alarm", 0.02, 0.02),
            ("Emergency Lighting", 0.2, 0.05),
        ],
    }

    def __init__(self, state: StateManager):
        self.state = state

    def generate(self) -> ElectricalSystem:
        """Generate complete electrical system."""

        loa = self.state.get("hull.loa", 25)
        crew = self.state.get("mission.crew_berthed", 5)
        passengers = self.state.get("mission.passengers", 0)

        system = ElectricalSystem(
            system_id=f"ELEC-{self.state.get('metadata.design_id', 'UNKNOWN')}",
        )

        system.loads = self._generate_loads(loa, crew, passengers)

        total_demand = sum(l.demand_load_kw for l in system.loads)

        gen_power = total_demand / 2 * 1.25

        system.generators = [
            GeneratorSet.estimate_from_power(gen_power),
            GeneratorSet.estimate_from_power(gen_power),
        ]
        system.generators[0].genset_id = "GEN-1"
        system.generators[1].genset_id = "GEN-2"

        system.batteries = [
            BatteryBank(
                bank_id="START-BANK",
                battery_type="agm",
                nominal_voltage_v=24,
                capacity_ah=200,
                num_batteries=4,
                weight_per_battery_kg=65,
            ),
            BatteryBank(
                bank_id="EMERG-BANK",
                battery_type="agm",
                nominal_voltage_v=24,
                capacity_ah=100,
                num_batteries=2,
                weight_per_battery_kg=35,
            ),
        ]

        system.shore_power_kw = max(50, total_demand * 0.8)

        system.calculate_totals()
        return system

    def _generate_loads(
        self,
        loa: float,
        crew: int,
        passengers: int,
    ) -> List[ElectricalLoad]:
        """Generate electrical loads based on vessel size."""
        loads = []
        load_counter = 1

        for category, templates in self.LOAD_TEMPLATES.items():
            for name, rated, running in templates:
                loads.append(ElectricalLoad(
                    load_id=f"LOAD-{load_counter:03d}",
                    load_name=name,
                    category=category,
                    rated_power_kw=rated,
                    running_power_kw=running,
                    diversity_factor=0.8 if category == "lighting" else 1.0,
                ))
                load_counter += 1

        total_persons = crew + passengers
        hotel_load = total_persons * 0.1
        loads.append(ElectricalLoad(
            load_id=f"LOAD-{load_counter:03d}",
            load_name="Hotel Services",
            category="hotel",
            rated_power_kw=hotel_load,
            running_power_kw=hotel_load * 0.6,
            diversity_factor=0.7,
        ))
        load_counter += 1

        hvac_load = self.state.get("hvac.total_power_kw", loa * 0.5)
        loads.append(ElectricalLoad(
            load_id=f"LOAD-{load_counter:03d}",
            load_name="HVAC System",
            category="hvac",
            rated_power_kw=hvac_load,
            running_power_kw=hvac_load * 0.7,
            diversity_factor=0.8,
        ))

        return loads
