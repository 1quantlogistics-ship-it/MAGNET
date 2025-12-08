"""
systems/safety/generator.py - Safety system generation.

BRAVO OWNS THIS FILE.

Module 30 v1.0 - Safety System Generator.
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

from .schema import (
    FireZone, FirefightingAgent, FireZoneDefinition,
    FirePump, LifeSavingAppliance, BilgeSystem, SafetySystem,
)

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class SafetySystemGenerator:
    """Generate safety systems for vessel."""

    # Fire zone definitions by area type
    ZONE_CONFIGS = {
        FireZone.ENGINE_ROOM: {
            "fire_rating_minutes": 60,
            "has_a60_boundaries": True,
            "has_smoke_detection": True,
            "has_heat_detection": True,
            "suppression_agent": FirefightingAgent.CO2,
            "has_fixed_system": True,
        },
        FireZone.ACCOMMODATION: {
            "fire_rating_minutes": 30,
            "has_a60_boundaries": False,
            "has_smoke_detection": True,
            "has_heat_detection": False,
            "suppression_agent": FirefightingAgent.WATER,
            "has_sprinklers": True,
        },
        FireZone.CARGO: {
            "fire_rating_minutes": 60,
            "has_a60_boundaries": True,
            "has_smoke_detection": True,
            "has_heat_detection": True,
            "suppression_agent": FirefightingAgent.CO2,
            "has_fixed_system": True,
        },
        FireZone.GALLEY: {
            "fire_rating_minutes": 30,
            "has_a60_boundaries": False,
            "has_smoke_detection": True,
            "has_heat_detection": True,
            "suppression_agent": FirefightingAgent.DRY_CHEMICAL,
            "has_sprinklers": True,
        },
        FireZone.MACHINERY: {
            "fire_rating_minutes": 60,
            "has_a60_boundaries": True,
            "has_smoke_detection": True,
            "has_heat_detection": True,
            "suppression_agent": FirefightingAgent.CO2,
            "has_fixed_system": True,
        },
        FireZone.CONTROL: {
            "fire_rating_minutes": 30,
            "has_a60_boundaries": False,
            "has_smoke_detection": True,
            "has_heat_detection": False,
            "suppression_agent": FirefightingAgent.CLEAN_AGENT,
            "has_fixed_system": True,
        },
        FireZone.SERVICE: {
            "fire_rating_minutes": 30,
            "has_a60_boundaries": False,
            "has_smoke_detection": True,
            "has_heat_detection": False,
            "suppression_agent": FirefightingAgent.WATER,
            "has_sprinklers": False,
        },
    }

    def __init__(self, state: 'StateManager'):
        self.state = state

        # Get vessel parameters
        self.loa = state.get("hull.loa", 26)
        self.beam = state.get("hull.beam", 6)
        self.depth = state.get("hull.depth", 3)
        self.crew = state.get("mission.crew", 4)
        self.passengers = state.get("mission.passengers", 12)
        self.total_persons = self.crew + self.passengers

    def generate_fire_zones(self) -> List[FireZoneDefinition]:
        """Generate fire zone definitions."""
        zones = []

        # Engine room zone
        er_volume = self.loa * 0.25 * self.beam * self.depth * 0.8
        er_config = self.ZONE_CONFIGS[FireZone.ENGINE_ROOM]
        zones.append(FireZoneDefinition(
            zone_id="FZ-001",
            zone_type=FireZone.ENGINE_ROOM,
            zone_name="Main Engine Room",
            volume_m3=er_volume,
            floor_area_m2=self.loa * 0.25 * self.beam,
            detector_count=max(4, int(er_volume / 50)),
            **er_config,
        ))

        # Accommodation zone
        accom_volume = self.loa * 0.35 * self.beam * self.depth * 0.6
        accom_config = self.ZONE_CONFIGS[FireZone.ACCOMMODATION]
        zones.append(FireZoneDefinition(
            zone_id="FZ-002",
            zone_type=FireZone.ACCOMMODATION,
            zone_name="Accommodation Spaces",
            volume_m3=accom_volume,
            floor_area_m2=self.loa * 0.35 * self.beam,
            detector_count=max(6, int(accom_volume / 30)),
            **accom_config,
        ))

        # Galley zone
        galley_volume = self.beam * 3 * self.depth * 0.4
        galley_config = self.ZONE_CONFIGS[FireZone.GALLEY]
        zones.append(FireZoneDefinition(
            zone_id="FZ-003",
            zone_type=FireZone.GALLEY,
            zone_name="Galley",
            volume_m3=galley_volume,
            floor_area_m2=self.beam * 3,
            detector_count=2,
            **galley_config,
        ))

        # Control/wheelhouse zone
        control_volume = self.beam * 4 * 2.5
        control_config = self.ZONE_CONFIGS[FireZone.CONTROL]
        zones.append(FireZoneDefinition(
            zone_id="FZ-004",
            zone_type=FireZone.CONTROL,
            zone_name="Wheelhouse",
            volume_m3=control_volume,
            floor_area_m2=self.beam * 4,
            detector_count=2,
            **control_config,
        ))

        # Service spaces
        service_volume = self.loa * 0.1 * self.beam * self.depth * 0.5
        service_config = self.ZONE_CONFIGS[FireZone.SERVICE]
        zones.append(FireZoneDefinition(
            zone_id="FZ-005",
            zone_type=FireZone.SERVICE,
            zone_name="Service Spaces",
            volume_m3=service_volume,
            floor_area_m2=self.loa * 0.1 * self.beam,
            detector_count=max(2, int(service_volume / 50)),
            **service_config,
        ))

        return zones

    def generate_fire_pumps(self) -> List[FirePump]:
        """Generate fire pump specifications per SOLAS."""
        pumps = []

        # Calculate required capacity (SOLAS II-2)
        # Q = 0.15 * sqrt(LOA * (B + D)) m³/h
        q_required = 0.15 * (self.loa * (self.beam + self.depth)) ** 0.5
        q_required = max(25.0, q_required)  # Minimum 25 m³/h

        # Main fire pump
        main_power = q_required * 0.5  # Approximate power requirement
        pumps.append(FirePump(
            pump_id="FP-001",
            pump_type="main",
            capacity_m3h=q_required * 1.1,  # 10% margin
            pressure_bar=7.0,
            power_kw=main_power,
            location="Engine Room",
            is_emergency=False,
            is_portable=False,
        ))

        # Emergency fire pump (required for vessels > 500 GT)
        if self.loa > 20:
            pumps.append(FirePump(
                pump_id="FP-002",
                pump_type="emergency",
                capacity_m3h=q_required * 0.8,
                pressure_bar=6.0,
                power_kw=main_power * 0.8,
                location="Forepeak",
                is_emergency=True,
                is_portable=False,
            ))

        # Portable fire pump
        pumps.append(FirePump(
            pump_id="FP-003",
            pump_type="portable",
            capacity_m3h=15.0,
            pressure_bar=4.0,
            power_kw=5.0,
            location="Main Deck",
            is_emergency=False,
            is_portable=True,
        ))

        return pumps

    def generate_life_saving_appliances(self) -> List[LifeSavingAppliance]:
        """Generate life saving appliances per SOLAS III."""
        appliances = []

        # Liferafts - 100% capacity on each side
        raft_capacity = min(25, max(6, self.total_persons))
        num_rafts = max(2, (self.total_persons + raft_capacity - 1) // raft_capacity)

        for i in range(num_rafts):
            side = "Port" if i % 2 == 0 else "Starboard"
            appliances.append(LifeSavingAppliance(
                appliance_id=f"LR-{i+1:03d}",
                appliance_type="liferaft",
                capacity=raft_capacity,
                location=f"{side} Main Deck",
                solas_compliant=True,
                msc_circular="MSC.81(70)",
            ))

        # Lifejackets - 100% + 5% extra for visitors
        lifejacket_count = int(self.total_persons * 1.05)
        appliances.append(LifeSavingAppliance(
            appliance_id="LJ-001",
            appliance_type="lifejacket",
            capacity=lifejacket_count,
            location="Various",
            solas_compliant=True,
            msc_circular="MSC.81(70)",
        ))

        # Children's lifejackets (10% if passengers)
        if self.passengers > 0:
            child_jackets = max(2, int(self.passengers * 0.1))
            appliances.append(LifeSavingAppliance(
                appliance_id="LJ-002",
                appliance_type="lifejacket",
                capacity=child_jackets,
                location="Accommodation",
                solas_compliant=True,
                msc_circular="MSC.81(70)",
            ))

        # Lifebuoys - minimum based on length
        num_lifebuoys = 4 if self.loa < 30 else 6 if self.loa < 60 else 8
        appliances.append(LifeSavingAppliance(
            appliance_id="LB-001",
            appliance_type="lifebuoy",
            capacity=num_lifebuoys,
            location="Various",
            solas_compliant=True,
            msc_circular="MSC.81(70)",
        ))

        # Immersion suits for crew
        appliances.append(LifeSavingAppliance(
            appliance_id="IS-001",
            appliance_type="immersion_suit",
            capacity=self.crew,
            location="Emergency Storage",
            solas_compliant=True,
            msc_circular="MSC.81(70)",
        ))

        # EPIRB
        appliances.append(LifeSavingAppliance(
            appliance_id="EPIRB-001",
            appliance_type="EPIRB",
            capacity=1,
            location="Wheelhouse",
            solas_compliant=True,
            msc_circular="MSC.81(70)",
        ))

        # SART
        appliances.append(LifeSavingAppliance(
            appliance_id="SART-001",
            appliance_type="SART",
            capacity=1,
            location="Wheelhouse",
            solas_compliant=True,
            msc_circular="MSC.81(70)",
        ))

        return appliances

    def generate_bilge_system(self) -> BilgeSystem:
        """Generate bilge system per SOLAS II-1."""
        # Calculate required pump capacity
        # Q = d² * sqrt(LOA) / 10 liters/min (d = pipe diameter mm)
        # For HSLC, minimum 50mm main suction

        main_diameter = 50 if self.loa < 30 else 65
        branch_diameter = 40 if self.loa < 30 else 50

        # Calculate capacity from pipe diameter
        q_lpm = main_diameter ** 2 * (self.loa ** 0.5) / 10
        q_m3h = q_lpm * 60 / 1000

        # Bilge compartments for alarms
        compartments = [
            "Engine Room",
            "Forepeak",
            "Chain Locker",
            "Void Spaces",
        ]
        if self.loa > 25:
            compartments.append("Aft Peak")

        return BilgeSystem(
            main_pump_capacity_m3h=max(15.0, q_m3h),
            emergency_pump_capacity_m3h=max(10.0, q_m3h * 0.7),
            pump_count=2 if self.loa < 30 else 3,
            main_diameter_mm=main_diameter,
            branch_diameter_mm=branch_diameter,
            has_high_level_alarm=True,
            alarm_locations=compartments,
        )

    def generate_safety_system(self) -> SafetySystem:
        """Generate complete safety system."""
        system = SafetySystem(
            system_id=f"SAFETY-{self.loa:.0f}M",
            fire_zones=self.generate_fire_zones(),
            fire_pumps=self.generate_fire_pumps(),
            fire_extinguisher_count=self._calculate_extinguisher_count(),
            life_saving_appliances=self.generate_life_saving_appliances(),
            bilge_system=self.generate_bilge_system(),
            has_ais=True,
            has_epirb=True,
            has_sart=True,
        )

        # Calculate totals
        system.calculate_totals()

        return system

    def _calculate_extinguisher_count(self) -> int:
        """Calculate portable fire extinguisher count."""
        # Based on SOLAS and deck area
        deck_area = self.loa * self.beam
        base_count = max(4, int(deck_area / 50))

        # Additional for engine room and galley
        return base_count + 3
